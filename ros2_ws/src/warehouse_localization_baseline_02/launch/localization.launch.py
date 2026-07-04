#!/usr/bin/env python3
"""
localization.launch.py  (M3 Baseline)
map_server(우리 창고 맵) + nav2 amcl + lifecycle_manager 를 띄운다.
sim(월드+로봇)은 별도로 실행돼 있어야 함 (/scan, /odom, TF odom->base_footprint 제공).

기본 초기 포즈는 amcl.yaml 의 (-24,-24,0) = C1 시작점.
맵 경로는 map 인자로 오버라이드 가능.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_this = get_package_share_directory('warehouse_localization_baseline_02')
    pkg_sim = get_package_share_directory('warehouse_localization_sim_01')
    amcl_params = os.path.join(pkg_this, 'config', 'amcl.yaml')
    default_map = os.path.join(pkg_sim, 'maps', 'warehouse', 'warehouse_map.yaml')

    map_yaml = LaunchConfiguration('map', default=default_map)

    map_server = Node(
        package='nav2_map_server', executable='map_server', name='map_server',
        output='screen',
        parameters=[{'use_sim_time': True, 'yaml_filename': map_yaml}],
    )

    amcl = Node(
        package='nav2_amcl', executable='amcl', name='amcl', output='screen',
        parameters=[amcl_params],
    )

    lifecycle = Node(
        package='nav2_lifecycle_manager', executable='lifecycle_manager',
        name='lifecycle_manager_localization', output='screen',
        parameters=[{'use_sim_time': True, 'autostart': True,
                     'node_names': ['map_server', 'amcl']}],
    )

    ld = LaunchDescription()
    ld.add_action(DeclareLaunchArgument('map', default_value=default_map))
    ld.add_action(map_server)
    ld.add_action(amcl)
    ld.add_action(lifecycle)
    return ld
