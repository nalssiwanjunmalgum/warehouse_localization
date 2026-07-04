#!/usr/bin/env python3
"""
display.launch.py  (M2)
개활 창고 sim(warehouse_world.launch.py) + RViz 를 한 번에 실행.
RViz 에서 /scan(빨간 점)을 보며 로봇을 몰면, 중앙 개활지(featureless core)로 갈수록
스캔 점이 사라지는 것을 눈으로 확인할 수 있다.

주행은 별도 터미널에서:
  ros2 run turtlebot3_teleop teleop_keyboard
  또는  ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.3}}" -r 10
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    pkg_this = get_package_share_directory('warehouse_localization_sim_01')

    world_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_this, 'launch', 'warehouse_world.launch.py')),
    )

    rviz_config = os.path.join(pkg_this, 'config', 'warehouse.rviz')
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    ld = LaunchDescription()
    ld.add_action(world_launch)
    ld.add_action(rviz)
    return ld
