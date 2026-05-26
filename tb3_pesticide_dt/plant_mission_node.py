#!/usr/bin/env python3
"""Autonomous route node for the pesticide inspection demo.

The node drives through predefined plant zones using odometry feedback, waits at
each zone to simulate inspection, asks the digital twin for a hyperspectral
classification, then logs the result before moving to the next zone.
"""

import json
import math
import time
from typing import Dict, Optional

import rclpy
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String

from tb3_pesticide_dt.pesticide_logic import (
    build_zones,
    clamp,
    normalize_angle,
    quaternion_to_yaw,
)


DEFAULT_ZONE_IDS = [
    "plant_a",
    "plant_b",
    "plant_c",
    "plant_d",
    "plant_e",
    "plant_f",
    "plant_g",
    "plant_h",
]
DEFAULT_ZONE_NAMES = [
    "Start bed",
    "North inner bed",
    "East row",
    "Far east bed",
    "South east bed",
    "South center bed",
    "West lower bed",
    "West return bed",
]
DEFAULT_ZONE_X = [0.30, 0.80, 1.35, 1.85, 1.75, 1.10, 0.35, -0.35]
DEFAULT_ZONE_Y = [-0.20, -0.45, -0.45, -0.90, -1.65, -2.20, -2.20, -1.45]
DEFAULT_ZONE_YAW = [0.0, -0.30, -0.50, -1.57, -2.20, 3.14, 2.70, 1.57]
DEFAULT_RESIDUES = [0.18, 0.74, 0.31, 0.56, 0.22, 0.81, 0.44, 0.63]
DEFAULT_STATUSES = ["OK", "OVERUSE", "OK", "OVERUSE", "OK", "OVERUSE", "OK", "OVERUSE"]


class PlantMissionNode(Node):
    def __init__(self):
        super().__init__("plant_mission_node")

        self._declare_parameters()
        self.zones = self._load_zones()

        self.odom_topic = str(self.get_parameter("odom_topic").value)
        self.cmd_topic = str(self.get_parameter("cmd_topic").value)
        self.state_topic = str(self.get_parameter("state_topic").value)
        self.request_topic = str(self.get_parameter("inspection_request_topic").value)
        self.result_topic = str(self.get_parameter("inspection_result_topic").value)
        self.digital_state_topic = str(self.get_parameter("digital_state_topic").value)
        self.log_topic = str(self.get_parameter("inspection_log_topic").value)

        self.pose = None
        self.mode = "WAITING_FOR_ODOM" if bool(self.get_parameter("start_automatically").value) else "IDLE"
        self.current_index = 0
        self.current_result: Optional[Dict] = None
        self.last_result: Optional[Dict] = None
        self.request_id = 0
        self.request_sent = False
        self.inspection_started_at: Optional[float] = None
        self.hold_until: Optional[float] = None
        self.mission_started_at = time.monotonic()
        self.summary = []
        self.digital_camera_health = "unknown"
        self.digital_mode = "unknown"
        self.last_state_publish_at = 0.0
        self.last_summary_publish_at = 0.0

        self.create_subscription(Odometry, self.odom_topic, self.on_odom, 10)
        self.create_subscription(String, self.result_topic, self.on_inspection_result, 10)
        self.create_subscription(String, self.digital_state_topic, self.on_digital_state, 10)

        self.pub_cmd = self.create_publisher(TwistStamped, self.cmd_topic, 10)
        self.pub_state = self.create_publisher(String, self.state_topic, 10)
        self.pub_request = self.create_publisher(String, self.request_topic, 10)
        self.pub_log = self.create_publisher(String, self.log_topic, 10)

        period = float(self.get_parameter("control_period_s").value)
        self.create_timer(period, self.tick)

        self.get_logger().info(
            f"PlantMissionNode started with {len(self.zones)} zones. "
            f"Commands -> {self.cmd_topic}; inspection requests -> {self.request_topic}"
        )

    def _declare_parameters(self):
        self.declare_parameter("start_automatically", True)
        self.declare_parameter("source_entity", "physical_robot")

        self.declare_parameter("odom_topic", "/odom")
        self.declare_parameter("cmd_topic", "/cmd_vel_raw")
        self.declare_parameter("state_topic", "/dt/physical/mission_state")
        self.declare_parameter("inspection_request_topic", "/dt/physical/inspection_request")
        self.declare_parameter("inspection_result_topic", "/dt/digital/inspection_result")
        self.declare_parameter("digital_state_topic", "/dt/digital/mission_state")
        self.declare_parameter("inspection_log_topic", "/dt/physical/inspection_log")

        self.declare_parameter("zone_ids", DEFAULT_ZONE_IDS)
        self.declare_parameter("zone_names", DEFAULT_ZONE_NAMES)
        self.declare_parameter("zone_x", DEFAULT_ZONE_X)
        self.declare_parameter("zone_y", DEFAULT_ZONE_Y)
        self.declare_parameter("zone_yaw", DEFAULT_ZONE_YAW)
        self.declare_parameter("zone_residue_indices", DEFAULT_RESIDUES)
        self.declare_parameter("zone_expected_statuses", DEFAULT_STATUSES)

        self.declare_parameter("control_period_s", 0.10)
        self.declare_parameter("arrival_tolerance_m", 0.12)
        self.declare_parameter("yaw_tolerance_rad", 0.25)
        self.declare_parameter("max_linear_speed", 0.16)
        self.declare_parameter("max_angular_speed", 0.85)
        self.declare_parameter("linear_gain", 0.65)
        self.declare_parameter("angular_gain", 1.80)
        self.declare_parameter("heading_slowdown_rad", 0.75)
        self.declare_parameter("inspection_duration_s", 3.0)
        self.declare_parameter("inspection_result_timeout_s", 8.0)
        self.declare_parameter("overuse_alert_hold_s", 2.0)
        self.declare_parameter("overuse_next_speed_scale", 0.70)
        self.declare_parameter("degraded_camera_speed_scale", 0.75)
        self.declare_parameter("summary_republish_period_s", 5.0)
        self.declare_parameter("frame_id", "base_link")

    def _load_zones(self):
        return build_zones(
            self.get_parameter("zone_ids").value,
            self.get_parameter("zone_names").value,
            self.get_parameter("zone_x").value,
            self.get_parameter("zone_y").value,
            self.get_parameter("zone_yaw").value,
            self.get_parameter("zone_residue_indices").value,
            self.get_parameter("zone_expected_statuses").value,
        )

    def on_odom(self, msg: Odometry):
        q = msg.pose.pose.orientation
        self.pose = {
            "x": float(msg.pose.pose.position.x),
            "y": float(msg.pose.pose.position.y),
            "yaw": quaternion_to_yaw(q.x, q.y, q.z, q.w),
        }

    def on_inspection_result(self, msg: String):
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().warn(f"Ignoring malformed inspection result: {msg.data}")
            return

        if self.current_index >= len(self.zones):
            return
        zone = self.zones[self.current_index]
        if data.get("zone_id") != zone.zone_id:
            return
        self.current_result = data
        self.get_logger().info(
            f"Digital twin inspection result for {zone.zone_id}: "
            f"{data.get('status')} residue={data.get('residue_index')}"
        )

    def on_digital_state(self, msg: String):
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        self.digital_camera_health = str(data.get("camera_health", self.digital_camera_health))
        self.digital_mode = str(data.get("mode", self.digital_mode))

    def tick(self):
        now = time.monotonic()

        if self.mode == "IDLE":
            self.publish_state(force=False)
            self.publish_stop()
            return

        if self.mode == "WAITING_FOR_ODOM":
            self.publish_stop()
            if self.pose is not None:
                self.mode = "NAVIGATING"
                self.get_logger().info(f"Starting route toward {self.zones[0].zone_id}")
            self.publish_state(force=True)
            return

        if self.mode == "NAVIGATING":
            self.handle_navigation()
            self.publish_state(force=False)
            return

        if self.mode == "INSPECTING":
            self.handle_inspection(now)
            self.publish_state(force=False)
            return

        if self.mode == "HOLDING_ALERT":
            self.publish_stop()
            if self.hold_until is not None and now >= self.hold_until:
                self.advance_zone()
            self.publish_state(force=False)
            return

        if self.mode == "COMPLETE":
            self.publish_stop()
            self.republish_summary_if_due(now)
            self.publish_state(force=False)
            return

    def handle_navigation(self):
        if self.pose is None:
            self.publish_stop()
            self.mode = "WAITING_FOR_ODOM"
            return

        zone = self.zones[self.current_index]
        dx = zone.x - self.pose["x"]
        dy = zone.y - self.pose["y"]
        distance = math.hypot(dx, dy)

        if distance <= float(self.get_parameter("arrival_tolerance_m").value):
            yaw_error = normalize_angle(zone.yaw - self.pose["yaw"])
            if abs(yaw_error) <= float(self.get_parameter("yaw_tolerance_rad").value):
                self.begin_inspection()
                return
            self.publish_cmd(0.0, self.angular_control(yaw_error))
            return

        target_heading = math.atan2(dy, dx)
        heading_error = normalize_angle(target_heading - self.pose["yaw"])
        heading_limit = float(self.get_parameter("heading_slowdown_rad").value)
        heading_scale = clamp(1.0 - abs(heading_error) / max(heading_limit, 0.01), 0.0, 1.0)

        max_linear = float(self.get_parameter("max_linear_speed").value) * self.behavior_speed_scale()
        linear = clamp(
            float(self.get_parameter("linear_gain").value) * distance * heading_scale,
            0.0,
            max_linear,
        )
        angular = self.angular_control(heading_error)
        self.publish_cmd(linear, angular)

    def angular_control(self, error: float) -> float:
        max_angular = float(self.get_parameter("max_angular_speed").value)
        angular = float(self.get_parameter("angular_gain").value) * error
        return clamp(angular, -max_angular, max_angular)

    def behavior_speed_scale(self) -> float:
        scale = 1.0
        if self.last_result and self.last_result.get("status") == "OVERUSE":
            scale *= float(self.get_parameter("overuse_next_speed_scale").value)
        if self.digital_camera_health.lower() == "degraded":
            scale *= float(self.get_parameter("degraded_camera_speed_scale").value)
        if self.digital_camera_health.lower() == "failed":
            scale = 0.0
        return scale

    def begin_inspection(self):
        zone = self.zones[self.current_index]
        self.publish_stop()
        self.mode = "INSPECTING"
        self.current_result = None
        self.inspection_started_at = time.monotonic()
        self.request_sent = False
        self.get_logger().info(f"Arrived at {zone.zone_id}; starting simulated inspection")

    def handle_inspection(self, now: float):
        self.publish_stop()
        zone = self.zones[self.current_index]

        if not self.request_sent:
            self.request_id += 1
            payload = {
                "event": "INSPECT_PLANT",
                "request_id": self.request_id,
                "zone_id": zone.zone_id,
                "zone_name": zone.name,
                "source_entity": str(self.get_parameter("source_entity").value),
                "simulated_sensor": "hyperspectral_camera",
                "pose": {"x": zone.x, "y": zone.y, "yaw": zone.yaw},
                "sent_at_monotonic_s": now,
            }
            self.pub_request.publish(String(data=json.dumps(payload, sort_keys=True)))
            self.request_sent = True
            self.get_logger().info(f"Inspection request sent for {zone.zone_id}")

        elapsed = now - (self.inspection_started_at or now)
        min_wait = float(self.get_parameter("inspection_duration_s").value)
        timeout = float(self.get_parameter("inspection_result_timeout_s").value)

        if self.current_result is not None and elapsed >= min_wait:
            self.finish_inspection(self.current_result)
            return

        if elapsed >= timeout:
            timeout_result = {
                "zone_id": zone.zone_id,
                "zone_name": zone.name,
                "status": "SENSOR_TIMEOUT",
                "residue_index": None,
                "confidence": 0.0,
                "camera_health": self.digital_camera_health,
            }
            self.finish_inspection(timeout_result)

    def finish_inspection(self, result: Dict):
        zone = self.zones[self.current_index]
        self.last_result = result
        entry = {
            "event": "INSPECTION_LOG",
            "zone_id": zone.zone_id,
            "zone_name": zone.name,
            "status": result.get("status", "UNKNOWN"),
            "residue_index": result.get("residue_index"),
            "confidence": result.get("confidence"),
            "camera_health": result.get("camera_health", self.digital_camera_health),
            "mission_index": self.current_index,
        }
        self.summary.append(entry)
        self.pub_log.publish(String(data=json.dumps(entry, sort_keys=True)))

        status = entry["status"]
        if status == "OVERUSE":
            hold_s = float(self.get_parameter("overuse_alert_hold_s").value)
            self.hold_until = time.monotonic() + hold_s
            self.mode = "HOLDING_ALERT"
            self.get_logger().warn(
                f"{zone.zone_id} classified as OVERUSE. Holding {hold_s:.1f}s before next zone."
            )
            return

        self.get_logger().info(f"{zone.zone_id} inspection complete: {status}")
        self.advance_zone()

    def advance_zone(self):
        self.current_index += 1
        self.current_result = None
        self.request_sent = False
        self.inspection_started_at = None
        self.hold_until = None

        if self.current_index >= len(self.zones):
            self.mode = "COMPLETE"
            self.publish_summary()
            self.get_logger().info("Plant inspection route complete")
        else:
            zone = self.zones[self.current_index]
            self.mode = "NAVIGATING"
            self.get_logger().info(f"Continuing route toward {zone.zone_id}")

    def publish_cmd(self, linear_x: float, angular_z: float):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = str(self.get_parameter("frame_id").value)
        msg.twist.linear.x = float(linear_x)
        msg.twist.angular.z = float(angular_z)
        self.pub_cmd.publish(msg)

    def publish_stop(self):
        self.publish_cmd(0.0, 0.0)

    def publish_state(self, force: bool):
        now = time.monotonic()
        if not force and (now - self.last_state_publish_at) < 0.5:
            return
        self.last_state_publish_at = now

        zone = self.zones[self.current_index] if self.current_index < len(self.zones) else None
        payload = {
            "entity": str(self.get_parameter("source_entity").value),
            "mode": self.mode,
            "current_zone_id": zone.zone_id if zone else None,
            "current_zone_name": zone.name if zone else None,
            "mission_index": self.current_index,
            "zone_count": len(self.zones),
            "pose": self.pose,
            "digital_camera_health": self.digital_camera_health,
            "digital_mode": self.digital_mode,
            "behavior_speed_scale": self.behavior_speed_scale(),
            "last_result": self.last_result,
            "completed_inspections": len(self.summary),
            "uptime_s": round(now - self.mission_started_at, 2),
        }
        self.pub_state.publish(String(data=json.dumps(payload, sort_keys=True)))

    def publish_summary(self):
        payload = {
            "event": "MISSION_SUMMARY",
            "total_zones": len(self.zones),
            "inspections": self.summary,
        }
        self.pub_log.publish(String(data=json.dumps(payload, sort_keys=True)))

    def republish_summary_if_due(self, now: float):
        period = float(self.get_parameter("summary_republish_period_s").value)
        if period <= 0.0:
            return
        if (now - self.last_summary_publish_at) >= period:
            self.last_summary_publish_at = now
            self.publish_summary()


def main(args=None):
    rclpy.init(args=args)
    node = PlantMissionNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if rclpy.ok():
            node.publish_stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
