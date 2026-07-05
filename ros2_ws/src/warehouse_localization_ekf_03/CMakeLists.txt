cmake_minimum_required(VERSION 3.8)
project(warehouse_localization_ekf_03)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS
    scripts/noise_injector.py
    scripts/plot_ekf_compare.py
    scripts/run_scenario_ekf.sh
    scripts/run_all_ekf.sh
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
