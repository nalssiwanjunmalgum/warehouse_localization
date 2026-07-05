#!/usr/bin/env python3
"""
warehouse_world.launch.py  (M2)
개활 창고 월드(warehouse_open.world)를 Gazebo에 띄우고 TurtleBot3(waffle)를 스폰한다.
로봇은 건물 구석(-24, -24)에서 시작 → 중앙 featureless core로 주행하며 드리프트 관찰 예정.

참고: LiDAR 12m 상향(커스텀 모델)은 다음 단계에서 반영. 현재는 기본 waffle(3.5m)로 월드 확인용.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    IncludeLaunchDescription, DeclareLaunchArgument, SetEnvironmentVariable)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_gazebo_ros = get_package_share_directory('gazebo_ros')
    pkg_tb3_gazebo = get_package_share_directory('turtlebot3_gazebo')
    pkg_this = get_package_share_directory('warehouse_localization_sim_01')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    x_pose = LaunchConfiguration('x_pose', default='-24.0')
    y_pose = LaunchConfiguration('y_pose', default='-24.0')
    # 로봇 모델 선택: 기본 lidar12(baseline). M5(+EKF)는 warehouse_waffle_ekf
    # (diff_drive publish_odom_tf=false — TF 를 noise_injector/EKF 가 대신 발행).
    model = LaunchConfiguration('model', default='warehouse_waffle_lidar12')
    # 월드 파일명 선택: 기본 개활 창고. M6 는 반사판 오버레이(warehouse_reflectors.world).
    world_name = LaunchConfiguration('world', default='warehouse_open.world')

    world = [os.path.join(pkg_this, 'worlds', 'warehouse'), '/', world_name]
    # 커스텀 waffle: LiDAR 최대거리 12m (원본 3.5m). 메시는 turtlebot3_common 참조 유지.
    waffle_sdf = [os.path.join(pkg_this, 'models'), '/', model, '/model.sdf']

    gzserver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, 'launch', 'gzserver.launch.py')),
        launch_arguments={'world': world}.items(),
    )

    gzclient = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, 'launch', 'gzclient.launch.py')),
    )

    robot_state_publisher = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_tb3_gazebo, 'launch', 'robot_state_publisher.launch.py')),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
    )

    spawn_robot = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-entity', 'waffle',
            '-file', waffle_sdf,
            '-x', x_pose, '-y', y_pose, '-z', '0.01',
        ],
        output='screen',
    )

    ld = LaunchDescription()
    # 셸 env에 의존하지 않도록 launch 자체가 로봇 모델을 고정 (방탄)
    ld.add_action(SetEnvironmentVariable('TURTLEBOT3_MODEL', 'waffle'))
    ld.add_action(DeclareLaunchArgument('use_sim_time', default_value='true'))
    ld.add_action(DeclareLaunchArgument('x_pose', default_value='-24.0'))
    ld.add_action(DeclareLaunchArgument('y_pose', default_value='-24.0'))
    ld.add_action(DeclareLaunchArgument('model', default_value='warehouse_waffle_lidar12'))
    ld.add_action(DeclareLaunchArgument('world', default_value='warehouse_open.world'))
    ld.add_action(gzserver)
    ld.add_action(gzclient)
    ld.add_action(robot_state_publisher)
    ld.add_action(spawn_robot)
    return ld
