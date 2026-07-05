cmake_minimum_required(VERSION 3.8)
project(warehouse_localization_landmark_04)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS
    scripts/gen_reflectors.py
    scripts/landmark_localizer.py
    scripts/plot_final_compare.py
    scripts/run_scenario_landmark.sh
    scripts/run_all_landmark.sh
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
