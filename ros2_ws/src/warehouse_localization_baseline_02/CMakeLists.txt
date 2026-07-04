cmake_minimum_required(VERSION 3.8)
project(warehouse_localization_baseline_02)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS
    scripts/metrics_recorder.py
    scripts/plot_metrics.py
    scripts/summarize.py
    scripts/run_scenario.sh
    scripts/run_all_baseline.sh
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
