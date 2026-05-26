# Demo Evidence Checklist

Use this during the Week 8/final demo recording.

## 1. Bidirectional Pub/Sub

Show `ros2 topic list | grep /dt`.

Physical/source side to digital side:

```bash
ros2 topic echo /dt/physical/mission_state
ros2 topic echo /dt/physical/inspection_request
```

Digital side to physical/source side:

```bash
ros2 topic echo /dt/digital/mission_state
ros2 topic echo /dt/digital/inspection_result
```

## 2. State Synchronization

Show that mission state is mirrored:

```bash
ros2 topic echo /dt/physical/mission_state
ros2 topic echo /dt/digital/mission_state
```

Optional live state-change demo:

```bash
ros2 param set /inspection_twin_node camera_health degraded
ros2 topic echo /dt/digital/mission_state
ros2 topic echo /dt/physical/mission_state
```

Set it back after showing the state:

```bash
ros2 param set /inspection_twin_node camera_health healthy
```

## 3. Environmental Interaction

Show the robot reaching plant zones, waiting, and receiving inspection results:

```bash
ros2 topic echo /dt/physical/inspection_log
```

For the safety part inherited from the scanner mini-project:

```bash
ros2 topic echo /dt/safety_state
```

Place an obstacle in front of the real robot or Gazebo robot and show `blocked: true`.

