cmake_minimum_required(VERSION 3.8)
project(warehouse_localization_sim_01)

find_package(ament_cmake REQUIRED)

# 월드 / 맵 / 런치 파일 설치 (worlds·maps 는 warehouse/factory 로 환경 분리)
install(
  DIRECTORY worlds maps launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
