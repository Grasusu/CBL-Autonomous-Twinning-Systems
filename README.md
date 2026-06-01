# TurtleBot3 Pesticide Inspection Digital Twin

ROS 2 Jazzy proof of concept for the 2IRR10 final digital twin demo.

The robot autonomously visits predefined plant zones in the arena, waits to simulate an inspection, asks a digital twin node for a simulated hyperspectral pesticide-residue result, logs each plant as `OK` or `OVERUSE`, then returns to the calibrated home/start location.

The final tested demo uses Nav2 for the full route:

```text
plant_nav2_mission_node -> NavigateToPose goals -> Nav2 -> /cmd_vel -> Gazebo TurtleBot3
inspection_twin_node     -> simulated hyperspectral camera results
arena_map_node           -> optional RViz/digital arena markers
```

## What This Demonstrates

- Autonomous navigation through 8 plant inspection zones.
- A digital twin entity synchronized with the physical/simulation side.
- Bidirectional pub/sub between physical and digital sides.
- Simulated hyperspectral pesticide-residue classification.
- Inspection logs with `OK` and `OVERUSE` results.
- A final autonomous return to a calibrated `plant_home` waypoint.
- Reuse of the course scanner/safety-node idea through the included `twin_safety_node` and hybrid fallback code.

## Rubric Mapping

1. **Bidirectional pub/sub**
   - Physical to digital: `/dt/physical/mission_state`, `/dt/physical/inspection_request`
   - Digital to physical: `/dt/digital/mission_state`, `/dt/digital/inspection_result`

2. **State synchronization**
   - Mission mode, active plant zone, digital camera health, inspection result, and final status are mirrored through `/dt/physical/mission_state` and `/dt/digital/mission_state`.

3. **Environmental interaction**
   - The robot moves through the arena, reaches plant zones, waits at each plant, receives a residue classification, and returns home.

4. **Evidence/logging**
   - `/dt/physical/inspection_log` publishes per-plant logs and the final mission summary.

## Package Contents

- `plant_nav2_mission_node`: final full-Nav2 mission controller.
- `inspection_twin_node`: digital twin that simulates the hyperspectral camera.
- `arena_map_node`: publishes optional digital markers for the arena.
- `twin_safety_node`: scanner-based safety bridge from the earlier mini-project pattern.
- `plant_mission_node`: hybrid/fallback mission controller.
- `config/nav2_plant_zones.yaml`: final full-Nav2 plant route and calibrated `plant_home`.
- `maps/map.yaml`: Nav2 map used by the Gazebo demo.

## Install / Build

Inside the course Docker workspace:

```bash
cd /ws/src
git clone <YOUR_GITHUB_REPO_URL> tb3_pesticide_dt

cd /ws
source /opt/ros/jazzy/setup.bash
source /opt/turtlebot3_ws/install/setup.bash
colcon build --packages-select my_tb3_world tb3_pesticide_dt --symlink-install
source install/setup.bash
```

If the package is already copied into `/ws/src/tb3_pesticide_dt`, only run the build commands.

## Final Tested Gazebo Demo

Important: run each launch only once. If the robot behaves strangely, restart the container first:

```bash
docker restart turtlebot3_container
```

Open 4 Docker terminals:

```bash
docker exec -it turtlebot3_container bash
```

### Terminal 1: Gazebo

```bash
cd /ws
source /opt/ros/jazzy/setup.bash
source /opt/turtlebot3_ws/install/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger

ros2 launch tb3_pesticide_dt pesticide_world.launch.py gui:=true
```

### Terminal 2: Nav2

```bash
cd /ws
source /opt/ros/jazzy/setup.bash
source /opt/turtlebot3_ws/install/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger

ros2 launch turtlebot3_navigation2 navigation2.launch.py \
  use_sim_time:=true \
  map:=/ws/src/tb3_pesticide_dt/maps/map.yaml \
  rviz:=false
```

Wait 10 to 15 seconds before starting the mission.

### Terminal 3: Evidence Logs

Start this before the mission:

```bash
cd /ws
source /opt/ros/jazzy/setup.bash
source /opt/turtlebot3_ws/install/setup.bash
source install/setup.bash

ros2 topic echo /dt/physical/inspection_log std_msgs/msg/String --full-length
```

### Terminal 4: Mission

```bash
cd /ws
source /opt/ros/jazzy/setup.bash
source /opt/turtlebot3_ws/install/setup.bash
source install/setup.bash

ros2 launch tb3_pesticide_dt pesticide_nav2_dt.launch.py \
  params_file:=/ws/src/tb3_pesticide_dt/config/nav2_plant_zones.yaml \
  use_sim_time:=true
```

Expected final lines:

```text
Route waypoint 9 is plant_home
Sent Nav2 return goal plant_home: Home / Start at {'x': -0.8, 'y': -0.07, 'yaw': 0.0}
Plant inspection route complete: RETURNED_HOME
```

Check the final Gazebo pose:

```bash
gz model -m burger -p
```

It should be close to Gazebo/world `x=0`, `y=0`. The Nav2 `plant_home` is `x=-0.80`, `y=-0.07` because the Nav2 map frame and Gazebo world frame have a small offset.

## Useful Evidence Commands

```bash
ros2 topic list | grep /dt
ros2 topic echo /dt/physical/mission_state std_msgs/msg/String --full-length
ros2 topic echo /dt/digital/mission_state std_msgs/msg/String --full-length
ros2 topic echo /dt/physical/inspection_request std_msgs/msg/String --full-length
ros2 topic echo /dt/digital/inspection_result std_msgs/msg/String --full-length
ros2 topic echo /dt/physical/inspection_log std_msgs/msg/String --full-length
```

Optional camera-health state sync demo:

```bash
ros2 param set /inspection_twin_node camera_health degraded
ros2 topic echo /dt/digital/mission_state std_msgs/msg/String --full-length
ros2 param set /inspection_twin_node camera_health healthy
```

## Changing Plant Zones

Edit:

```text
config/nav2_plant_zones.yaml
```

The first 8 entries are inspected plants. The 9th entry, `plant_home`, is the final return waypoint and is not inspected.

Keep all arrays the same length:

```yaml
zone_ids
zone_names
zone_x
zone_y
zone_yaw
zone_residue_indices
zone_expected_statuses
```

## Will This Work On The Real Robot?

The ROS nodes are written with standard ROS 2 topics/actions, so the architecture can run on a real TurtleBot3. However, the current working demo is calibrated for the Gazebo world and the provided Nav2 map.

For a real robot, it will not be plug-and-play. You must:

- Run the real TurtleBot3 bringup on the robot.
- Run Nav2 with a map of the real arena, or create one with SLAM.
- Recalibrate every plant waypoint in the real map frame.
- Recalibrate the final `plant_home` coordinate.
- Use `use_sim_time:=false`.
- Keep the hyperspectral camera as simulated unless real camera hardware is integrated.

Robot bringup example:

```bash
source /opt/ros/jazzy/setup.bash
export TURTLEBOT3_MODEL=burger
export LDS_MODEL=LDS-02
ros2 launch turtlebot3_bringup robot.launch.py
```

Then run Nav2 and the mission on the laptop/desktop connected to the same ROS domain, using real-map coordinates. In short: the concept and nodes can transfer to the robot, but the coordinates and Nav2 map must be redone for the real arena.

## GitHub Setup

From this package folder:

```bash
cd /Users/alexandrubogdan/turtlebot3_ws/src/tb3_pesticide_dt
git status
git add .
git commit -m "Add TurtleBot3 pesticide inspection digital twin demo"
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

If `origin` already exists:

```bash
git remote set-url origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```
