#!/usr/bin/env python3
"""
ekf.launch.py  (M5)
개활 창고 sim(EKF 모델 변형) + 노이즈 주입 + [EKF] + AMCL + RViz 를 한 번에 실행.

인자:
  use_ekf:=true   → 구성 E: noise_injector(TF 미발행) + robot_localization EKF(TF 발행). 드리프트 완화.
  use_ekf:=false  → 구성 N: noise_injector(TF 발행). 노이즈만, 완화 없음(baseline+드리프트).

관찰: use_ekf 를 껐다 켜며 같은 노이즈에서 추정이 얼마나 덜 어긋나는지 비교. (설계: docs/M5_EKF.md)

주행/기록은 별도 터미널:
  ros2 run warehouse_localization_sim_01 auto_drive_demo.py --ros-args -p route:=c1 -p loop:=false
  ros2 run warehouse_localization_baseline_02 metrics_recorder.py --ros-args -p out_csv:=/tmp/m5.csv
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    IncludeLaunchDescription, DeclareLaunchArgument, TimerAction)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_this = get_package_share_directory('warehouse_localization_ekf_03')
    pkg_base = get_package_share_directory('warehouse_localization_baseline_02')
    pkg_sim = get_package_share_directory('warehouse_localization_sim_01')

    use_ekf = LaunchConfiguration('use_ekf', default='true')
    ekf_yaml = os.path.join(pkg_this, 'config', 'ekf.yaml')

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_sim, 'launch', 'warehouse_world.launch.py')),
        launch_arguments={'model': 'warehouse_waffle_ekf'}.items(),
    )

    # 구성 N: EKF 없음 → noise_injector 가 TF 발행
    noise_n = Node(
        package='warehouse_localization_ekf_03', executable='noise_injector.py',
        name='noise_injector', output='screen',
        parameters=[{'use_sim_time': True, 'publish_tf': True}],
        condition=UnlessCondition(use_ekf),
    )
    # 구성 E: EKF 있음 → noise_injector 는 토픽만, TF 는 EKF 가 발행
    noise_e = Node(
        package='warehouse_localization_ekf_03', executable='noise_injector.py',
        name='noise_injector', output='screen',
        parameters=[{'use_sim_time': True, 'publish_tf': False}],
        condition=IfCondition(use_ekf),
    )
    ekf = Node(
        package='robot_localization', executable='ekf_node', name='ekf_filter_node',
        output='screen', parameters=[ekf_yaml],
        condition=IfCondition(use_ekf),
    )

    # sim 이 /scan·/odom·TF 를 낼 시간을 준 뒤 AMCL 기동 (baseline localization 재사용)
    localization = TimerAction(period=6.0, actions=[
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_base, 'launch', 'localization.launch.py'))),
    ])

    rviz = Node(
        package='rviz2', executable='rviz2', name='rviz2',
        arguments=['-d', os.path.join(pkg_base, 'config', 'baseline.rviz')],
        parameters=[{'use_sim_time': True}], output='screen',
    )

    ld = LaunchDescription()
    ld.add_action(DeclareLaunchArgument('use_ekf', default_value='true'))
    ld.add_action(sim)
    ld.add_action(noise_n)
    ld.add_action(noise_e)
    ld.add_action(ekf)
    ld.add_action(localization)
    ld.add_action(rviz)
    return ld
