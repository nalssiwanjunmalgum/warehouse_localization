#!/usr/bin/env python3
"""
baseline.launch.py  (M3)
개활 창고 sim + AMCL 로컬라이제이션 + RViz 를 한 번에 실행.
RViz 에서: 초록 화살표=진짜 위치(ground truth), 빨강 화살표+주황 타원=AMCL 추정+공분산.
로봇이 중앙 개활지로 가면 주황 공분산 타원이 커지고 추정이 진짜에서 벗어나는 것을 관찰.

주행/기록은 별도 터미널에서:
  ros2 run warehouse_localization_sim_01 auto_drive_demo.py --ros-args -p route:=demo
  ros2 run warehouse_localization_baseline_02 metrics_recorder.py --ros-args -p out_csv:=/tmp/m3.csv
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    pkg_this = get_package_share_directory('warehouse_localization_baseline_02')
    pkg_sim = get_package_share_directory('warehouse_localization_sim_01')

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_sim, 'launch', 'warehouse_world.launch.py')),
    )

    # sim(gazebo) 가 /scan·TF 를 낼 시간을 준 뒤 AMCL 기동
    localization = TimerAction(period=6.0, actions=[
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_this, 'launch', 'localization.launch.py'))),
    ])

    rviz = Node(
        package='rviz2', executable='rviz2', name='rviz2',
        arguments=['-d', os.path.join(pkg_this, 'config', 'baseline.rviz')],
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    ld = LaunchDescription()
    ld.add_action(sim)
    ld.add_action(localization)
    ld.add_action(rviz)
    return ld
