#!/usr/bin/env python3
"""
landmark.launch.py  (M6)
반사판 오버레이 월드 + 노이즈 + EKF + 반사판 절대보정(landmark_localizer) + RViz.
AMCL·map_server 없음 — 위치추정은 반사판 삼각측량(/landmark_pose)이 담당.

인자: init_x, init_y, init_yaw (부트스트랩 초기 pose, 기본 C1 시작).
주행/기록은 별도 터미널:
  ros2 run warehouse_localization_sim_01 auto_drive_demo.py --ros-args -p route:=c1 -p loop:=false
  ros2 run warehouse_localization_baseline_02 metrics_recorder.py --ros-args \
    -p out_csv:=/tmp/m6.csv -p est_topic:=/landmark_pose
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_this = get_package_share_directory('warehouse_localization_landmark_04')
    pkg_ekf = get_package_share_directory('warehouse_localization_ekf_03')
    pkg_base = get_package_share_directory('warehouse_localization_baseline_02')
    pkg_sim = get_package_share_directory('warehouse_localization_sim_01')

    ix = LaunchConfiguration('init_x', default='-24.0')
    iy = LaunchConfiguration('init_y', default='-24.0')
    iyaw = LaunchConfiguration('init_yaw', default='1.571')
    landmarks = os.path.join(pkg_this, 'config', 'landmarks.yaml')
    ekf_yaml = os.path.join(pkg_ekf, 'config', 'ekf.yaml')

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_sim, 'launch', 'warehouse_world.launch.py')),
        launch_arguments={'model': 'warehouse_waffle_ekf',
                          'world': 'warehouse_reflectors.world',
                          'x_pose': ix, 'y_pose': iy}.items(),
    )

    noise = Node(
        package='warehouse_localization_ekf_03', executable='noise_injector.py',
        name='noise_injector', output='screen',
        parameters=[{'use_sim_time': True, 'publish_tf': False}],
    )
    ekf = Node(
        package='robot_localization', executable='ekf_node', name='ekf_filter_node',
        output='screen', parameters=[ekf_yaml],
    )
    localizer = Node(
        package='warehouse_localization_landmark_04', executable='landmark_localizer.py',
        name='landmark_localizer', output='screen',
        parameters=[{'use_sim_time': True, 'landmarks_yaml': landmarks,
                     'init_x': ix, 'init_y': iy, 'init_yaw': iyaw}],
    )
    rviz = Node(
        package='rviz2', executable='rviz2', name='rviz2',
        arguments=['-d', os.path.join(pkg_base, 'config', 'baseline.rviz')],
        parameters=[{'use_sim_time': True}], output='screen',
    )

    ld = LaunchDescription()
    ld.add_action(DeclareLaunchArgument('init_x', default_value='-24.0'))
    ld.add_action(DeclareLaunchArgument('init_y', default_value='-24.0'))
    ld.add_action(DeclareLaunchArgument('init_yaw', default_value='1.571'))
    ld.add_action(sim)
    ld.add_action(noise)
    ld.add_action(ekf)
    ld.add_action(localizer)
    ld.add_action(rviz)
    return ld
