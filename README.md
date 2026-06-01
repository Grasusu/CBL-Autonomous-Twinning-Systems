# TurtleBot3 Pesticide Inspection Digital Twin

ROS 2 Jazzy proof of concept for the 2IRR10 final digital twin demo.

The robot autonomously visits predefined plant zones in the arena, waits to simulate an inspection, asks a digital twin node for a simulated hyperspectral pesticide-residue result, logs each plant as `OK` or `OVERUSE`, then returns to the calibrated home/start location.

The final tested demo uses Nav2 for the full route:

```text
plant_nav2_mission_node -> NavigateToPose goals -> Nav2 -> /cmd_vel -> Gazebo TurtleBot3
inspection_twin_node     -> simulated hyperspectral camera results
arena_map_node           -> optional RViz/digital arena markers
```

For the physical robot lab, Gazebo can also run as a live visual digital twin:

```text
real TurtleBot3 /odom or /amcl_pose -> gazebo_pose_mirror_node -> Gazebo burger model pose
```

## What This Demonstrates

- Autonomous navigation through 8 plant inspection zones.
- A digital twin entity synchronized with the physical/simulation side.
- Bidirectional pub/sub between physical and digital sides.
- Simulated hyperspectral pesticide-residue classification.
- Inspection logs with `OK` and `OVERUSE` results.
- A final autonomous return to a calibrated `plant_home` waypoint.
- Optional live Gazebo pose mirroring for the physical robot demo.
- Reuse of the course scanner/safety-node idea through the included `twin_safety_node` and hybrid fallback code.

## Rubric Mapping

1. **Bidirectional pub/sub**
   - Physical to digital: `/dt/physical/mission_state`, `/dt/physical/inspection_request`
   - Digital to physical: `/dt/digital/mission_state`, `/dt/digital/inspection_result`

2. **State synchronization**
   - Mission mode, active plant zone, digital camera health, inspection result, and final status are mirrored through `/dt/physical/mission_state` and `/dt/digital/mission_state`.
   - For the physical robot demo, `gazebo_pose_mirror_node` can mirror the real robot pose into Gazebo so the digital robot follows the real one visually.

3. **Environmental interaction**
   - The robot moves through the arena, reaches plant zones, waits at each plant, receives a residue classification, and returns home.

4. **Evidence/logging**
   - `/dt/physical/inspection_log` publishes per-plant logs and the final mission summary.

## Package Contents

- `plant_nav2_mission_node`: final full-Nav2 mission controller.
- `inspection_twin_node`: digital twin that simulates the hyperspectral camera.
- `gazebo_pose_mirror_node`: copies real robot pose into the Gazebo model for live digital-twin visualization.
- `arena_map_node`: publishes optional digital markers for the arena.
- `twin_safety_node`: scanner-based safety bridge from the earlier mini-project pattern.
- `plant_mission_node`: hybrid/fallback mission controller.
- `config/nav2_plant_zones.yaml`: final full-Nav2 plant route and calibrated `plant_home`.
- `maps/map.yaml`: Nav2 map used by the Gazebo demo.
- `launch/pesticide_world_visual_twin.launch.py`: Gazebo arena plus visual robot only, without fake ROS `/scan` or `/odom` bridge.

## Install / Build

Inside the course Docker workspace:

```bash
cd /ws/src
git clone https://github.com/Grasusu/CBL-Autonomous-Twinning-Systems.git tb3_pesticide_dt

cd /ws
source /opt/ros/jazzy/setup.bash
source /opt/turtlebot3_ws/install/setup.bash
colcon build --packages-select my_tb3_world tb3_pesticide_dt --symlink-install
source install/setup.bash
```

If the package is already copied into `/ws/src/tb3_pesticide_dt`, only run the build commands.

On a lab laptop without Docker, put the project inside the `src` folder of a ROS 2 workspace:

```bash
mkdir -p ~/turtlebot3_ws/src
cd ~/turtlebot3_ws/src
git clone https://github.com/Grasusu/CBL-Autonomous-Twinning-Systems.git tb3_pesticide_dt

cd ~/turtlebot3_ws
source /opt/ros/jazzy/setup.bash
source /opt/turtlebot3_ws/install/setup.bash
colcon build --packages-select tb3_pesticide_dt --symlink-install
source install/setup.bash
```

So yes: on the lab laptop, clone/copy this repository into `~/turtlebot3_ws/src/tb3_pesticide_dt` unless your course uses a different workspace name.

For Gazebo visualization, this project also expects the course `my_tb3_world` package in the same workspace, because that package contains `new_world.world`. The structure should be:

```text
~/turtlebot3_ws/src/
  my_tb3_world/
  tb3_pesticide_dt/
```

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

## Real Robot Lab Setup

The ROS nodes are written with standard ROS 2 topics/actions, so the architecture can run on a real TurtleBot3. The Gazebo arena was modeled after the real arena, so the route should transfer conceptually. However, the real robot still needs its own localization/map frame and waypoint calibration.

Do not use the Gazebo-calibrated coordinates blindly on the robot. For the real robot you must:

- Run the real TurtleBot3 bringup on the robot.
- Run Nav2 with a map of the real arena, or create one with SLAM.
- Recalibrate every plant waypoint in the real map frame.
- Recalibrate the final `plant_home` coordinate.
- Use `use_sim_time:=false`.
- Keep the hyperspectral camera as simulated unless real camera hardware is integrated.

### 1. Put The Repo On The Lab Laptop

On the lab laptop:

```bash
mkdir -p ~/turtlebot3_ws/src
cd ~/turtlebot3_ws/src
git clone https://github.com/Grasusu/CBL-Autonomous-Twinning-Systems.git tb3_pesticide_dt

cd ~/turtlebot3_ws
source /opt/ros/jazzy/setup.bash
source /opt/turtlebot3_ws/install/setup.bash
colcon build --packages-select tb3_pesticide_dt --symlink-install
source install/setup.bash
```

If the lab already has a workspace, use that workspace's `src` folder instead. The important structure is:

```text
<workspace>/
  src/
    tb3_pesticide_dt/
  build/
  install/
  log/
```

### 2. Start The Real Robot

On the TurtleBot3 through SSH:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=30
export ROS_LOCALHOST_ONLY=0
export TURTLEBOT3_MODEL=burger
export LDS_MODEL=LDS-02
ros2 launch turtlebot3_bringup robot.launch.py
```

Use the `ROS_DOMAIN_ID` required by your course if it is not `30`. The robot and lab laptop must use the same value.

### 3. Verify Laptop To Robot Communication

On the lab laptop:

```bash
source /opt/ros/jazzy/setup.bash
source /opt/turtlebot3_ws/install/setup.bash
source ~/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=30
export ROS_LOCALHOST_ONLY=0
export TURTLEBOT3_MODEL=burger

ros2 topic list
ros2 topic echo /scan
ros2 topic echo /odom
```

If `/scan` and `/odom` do not appear, fix networking/ROS domain before running the mission.

### 4. Use Or Create A Real Arena Map

If the lab already has a Nav2 map of the real arena, use that map file.

If not, create one with SLAM. On the lab laptop while the robot bringup is running:

```bash
source /opt/ros/jazzy/setup.bash
source /opt/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=30
export ROS_LOCALHOST_ONLY=0
export TURTLEBOT3_MODEL=burger

ros2 launch turtlebot3_cartographer cartographer.launch.py use_sim_time:=false
```

In another terminal, teleoperate slowly around the arena:

```bash
source /opt/ros/jazzy/setup.bash
source /opt/turtlebot3_ws/install/setup.bash
export TURTLEBOT3_MODEL=burger

ros2 run turtlebot3_teleop teleop_keyboard
```

Save the map:

```bash
ros2 run nav2_map_server map_saver_cli -f ~/arena_map
```

This creates:

```text
~/arena_map.yaml
~/arena_map.pgm
```

### 5. Start Nav2 On The Real Robot Map

On the lab laptop:

```bash
source /opt/ros/jazzy/setup.bash
source /opt/turtlebot3_ws/install/setup.bash
source ~/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=30
export ROS_LOCALHOST_ONLY=0
export TURTLEBOT3_MODEL=burger

ros2 launch turtlebot3_navigation2 navigation2.launch.py \
  use_sim_time:=false \
  map:=$HOME/arena_map.yaml
```

In RViz, set the robot's initial pose on the map before sending goals.

### 6. Calibrate Real Plant Waypoints

Move the robot to each real plant/inspection location using RViz goals or teleop. At each desired location, run:

```bash
ros2 run tf2_ros tf2_echo map base_footprint
```

Record the `Translation: [x, y, z]` values. Put those `x` and `y` values into:

```text
~/turtlebot3_ws/src/tb3_pesticide_dt/config/nav2_plant_zones.yaml
```

Update:

```yaml
zone_x
zone_y
zone_yaw
home_x
home_y
home_yaw
```

The first 8 entries are plant inspection stops. The 9th entry, `plant_home`, is the final return location.

### 7. Run The Mission On The Real Robot

Start an evidence terminal first:

```bash
source /opt/ros/jazzy/setup.bash
source /opt/turtlebot3_ws/install/setup.bash
source ~/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=30
export ROS_LOCALHOST_ONLY=0

ros2 topic echo /dt/physical/inspection_log std_msgs/msg/String --full-length
```

Then start the mission:

```bash
cd ~/turtlebot3_ws
source /opt/ros/jazzy/setup.bash
source /opt/turtlebot3_ws/install/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=30
export ROS_LOCALHOST_ONLY=0
export TURTLEBOT3_MODEL=burger

ros2 launch tb3_pesticide_dt pesticide_nav2_dt.launch.py \
  params_file:=~/turtlebot3_ws/src/tb3_pesticide_dt/config/nav2_plant_zones.yaml \
  use_sim_time:=false
```

Expected final lines:

```text
Route waypoint 9 is plant_home
Sent Nav2 return goal plant_home
Plant inspection route complete: RETURNED_HOME
```

### 8. Optional: Run Gazebo As A Live Digital Robot

Use this when you want the Gazebo robot to move in sync with the real TurtleBot3.

Important: do not use `pesticide_world.launch.py` for this physical-robot sync demo. That launch starts simulated ROS `/scan`, `/odom`, and `/tf` bridges, which can conflict with the real robot. Use the visual-only launch below.

Terminal A, start the visual Gazebo arena on the lab laptop:

```bash
cd ~/turtlebot3_ws
source /opt/ros/jazzy/setup.bash
source /opt/turtlebot3_ws/install/setup.bash
source install/setup.bash
export TURTLEBOT3_MODEL=burger

ros2 launch tb3_pesticide_dt pesticide_world_visual_twin.launch.py gui:=true
```

Terminal B, mirror the real robot odometry into Gazebo:

```bash
cd ~/turtlebot3_ws
source /opt/ros/jazzy/setup.bash
source /opt/turtlebot3_ws/install/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=30
export ROS_LOCALHOST_ONLY=0

ros2 launch tb3_pesticide_dt gazebo_pose_mirror.launch.py \
  source_topic:=/odom \
  source_type:=odom \
  model_name:=burger \
  world_name:=default
```

Now when the real robot moves, the Gazebo `burger` model should follow. If your Nav2 map pose is better aligned than raw odometry, use AMCL instead:

```bash
ros2 launch tb3_pesticide_dt gazebo_pose_mirror.launch.py \
  source_topic:=/amcl_pose \
  source_type:=amcl_pose \
  model_name:=burger \
  world_name:=default
```

If the Gazebo robot follows with a constant offset, keep the same node and add offsets:

```bash
ros2 launch tb3_pesticide_dt gazebo_pose_mirror.launch.py \
  source_topic:=/odom \
  source_type:=odom \
  x_offset:=0.20 \
  y_offset:=-0.10 \
  yaw_offset:=0.0
```

Use the normal real-robot Nav2 and mission commands from sections 5 and 7 at the same time. Gazebo is only the visual twin; the real robot is still the one being controlled.

### Real Robot Safety Notes

- Test with only 1 or 2 waypoints first before running the whole route.
- Keep a hand near the robot or be ready to stop the launch with `Ctrl+C`.
- Run in a clear arena and keep people out of the robot path.
- Recheck localization in RViz if the robot starts navigating to the wrong place.
- The simulated hyperspectral camera result is still generated by `inspection_twin_node`; no real camera hardware is required for this proof of concept.

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
