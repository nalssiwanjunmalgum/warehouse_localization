cmake_minimum_required(VERSION 3.8)
project(warehouse_localization_sim_01)

find_package(ament_cmake REQUIRED)

# 월드 / 맵 / 모델 / 런치 / RViz 설정 설치 (worlds·maps 는 warehouse/factory 로 환경 분리)
install(
  DIRECTORY worlds maps models launch config
  DESTINATION share/${PROJECT_NAME}
)

# 자동 주행 데모 노드 (ros2 run 으로 실행)
install(
  PROGRAMS scripts/auto_drive_demo.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
