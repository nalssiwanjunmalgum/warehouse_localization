#!/usr/bin/env bash
# run_all_landmark.sh — M6 C1~C5 를 순차 실행. 결과는 OUT(기본 outputs/landmark).
OUT="${1:-/home/ubuntu/ros2_ws/outputs/landmark}"
RS=/home/ubuntu/ros2_ws/install/warehouse_localization_landmark_04/lib/warehouse_localization_landmark_04/run_scenario_landmark.sh
mkdir -p "$OUT"

# SCEN ROUTE INIT_X INIT_Y INIT_YAW(rad) MAXTIME  (baseline·EKF 와 동일 시나리오)
bash "$RS" C1 c1 -24 -24  1.571 170 "$OUT"
bash "$RS" C2 c2 -24   8  0.000 150 "$OUT"
bash "$RS" C3 c3 -22 -22  1.710 260 "$OUT"
bash "$RS" C4 c4 -24   0 -1.571 130 "$OUT"
bash "$RS" C5 c5  24 -24  3.142 220 "$OUT"

echo "=== 전체 완료. 결과: $OUT ==="
ls -la "$OUT"
