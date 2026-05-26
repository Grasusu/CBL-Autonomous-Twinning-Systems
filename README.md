# TurtleBot3 Pesticide Inspection Digital Twin

ROS 2 Jazzy proof of concept for the final 2IRR10 digital twin demo.

The robot autonomously drives to predefined plant zones, waits to simulate inspection, asks the digital twin for a simulated hyperspectral pesticide-residue result, logs `OK` or `OVERUSE`, then continues to the next zone. Motion commands still pass through the scanner mini-project safety pattern:

```text
plant_mission_node -> /cmd_vel_raw -> twin_safety_node -> /cmd_vel and /sim/cmd_vel
```

## Course Rubric Mapping

1. **Bidirectional pub/sub**
   - Physical/source side to digital side: `/dt/physical/mission_state`, `/dt/physical/inspection_request`
   - Digital side to physical/source side: `/dt/digital/mission_state`, `/dt/digital/inspection_result`

2. **State synchronization beyond motion**
   - Mission mode, current plant zone, camera health, behavior speed scale, and inspection result are mirrored in `/dt/physical/mission_state` and `/dt/digital/mission_state`.
   - Demo state change: `ros2 param set /inspection_twin_node camera_health degraded`

3. **Environmental interaction**
   - The robot reaches plant-zone locations in the arena, waits, and records a plant condition.
   - The safety node also mirrors obstacle interaction through `/dt/safety_state`.

## Nodes

- `plant_mission_node`: odometry-based autonomous route controller.
- `inspection_twin_node`: digital twin entity that mirrors state, simulates the hyperspectral camera, publishes RViz plant markers, and returns inspection results.
- `twin_safety_node`: scanner-based safety bridge from the previous mini-project pattern.

All DT data uses standard ROS messages. Structured payloads are JSON in `std_msgs/String`, so no custom message package is needed.

## Install In The Course Workspace

From the Docker/WSL TurtleBot workspace used in the course:

```bash
cd /ws/src
git clone <YOUR_GITHUB_REPO_URL> tb3_pesticide_dt
cd /ws
source /opt/ros/jazzy/setup.bash
source /opt/turtlebot3_ws/install/setup.bash
colcon build --packages-select tb3_pesticide_dt --symlink-install
source install/setup.bash
```

If you are copying from this local folder before pushing to GitHub, place the whole `tb3_pesticide_dt` folder in `/ws/src/` or `~/turtlebot3_ws/src/`, then run the same build commands.

## Run: Option A, Physical Robot + Gazebo Twin

Terminal 1, on the robot through SSH:

```bash
source /opt/ros/jazzy/setup.bash
export TURTLEBOT3_MODEL=burger
export LDS_MODEL=LDS-02
ros2 launch turtlebot3_bringup robot.launch.py
```

Terminal 2, start the Gazebo twin from the scanner mini-project or course world:

```bash
cd /ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 launch tb3_safety_stop gazebo_twin.launch.py
```

Terminal 3, start this final-demo system:

```bash
cd /ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch tb3_pesticide_dt pesticide_dt.launch.py
```

Do not run teleop at the same time as the mission node. The mission node is the command source.

## Run: Simulation-Only Rehearsal

Start the course Gazebo world:

```bash
cd /ws
source /opt/ros/jazzy/setup.bash
source /opt/turtlebot3_ws/install/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 launch my_tb3_world new_world.launch.py
```

In another terminal:

```bash
cd /ws
source install/setup.bash
ros2 launch tb3_pesticide_dt pesticide_dt.launch.py \
  params_file:=/ws/src/tb3_pesticide_dt/config/sim_only.yaml \
  use_sim_time:=true
```

## Evidence Commands For The Presentation

```bash
ros2 topic list | grep /dt
ros2 topic echo /dt/physical/mission_state
ros2 topic echo /dt/digital/mission_state
ros2 topic echo /dt/physical/inspection_request
ros2 topic echo /dt/digital/inspection_result
ros2 topic echo /dt/physical/inspection_log
ros2 topic echo /dt/safety_state
```

Optional state-sync proof:

```bash
ros2 param set /inspection_twin_node camera_health degraded
ros2 topic echo /dt/digital/mission_state
ros2 topic echo /dt/physical/mission_state
ros2 param set /inspection_twin_node camera_health healthy
```

See `docs/demo_evidence_checklist.md` for a short recording checklist.

## Tune Plant Zones

Edit `config/plant_zones.yaml` for the real + twin demo, or `config/sim_only.yaml` for Gazebo-only rehearsal.

Keep these arrays the same length:

```yaml
zone_ids: [plant_a, plant_b, plant_c]
zone_names: [North bed, Center bed, South bed]
zone_x: [0.65, 0.65, 0.00]
zone_y: [0.00, 0.75, 0.75]
zone_yaw: [0.00, 1.57, 3.14]
zone_residue_indices: [0.18, 0.74, 0.31]
zone_expected_statuses: [OK, OVERUSE, OK]
```

Coordinates are relative to the robot odometry frame when the robot starts. Put the robot at a consistent start pose in the wooden arena before launching the mission.

## GitHub Setup

This folder is intended to be the repo root.

```bash
git status
git add .
git commit -m "Initial pesticide inspection digital twin demo"
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

