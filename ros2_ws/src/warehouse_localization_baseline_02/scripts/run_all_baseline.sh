#!/usr/bin/env bash
# run_all_baseline.sh — C1~C5 baseline 시나리오를 순차 실행. 결과는 OUT 디렉토리에.
# 사용: bash run_all_baseline.sh [OUTDIR]   (기본 /home/ubuntu/results)
# 각 시나리오: SCEN ROUTE INIT_X INIT_Y INIT_YAW(rad) MAXTIME
OUT="${1:-/home/ubuntu/ros2_ws/outputs}"    # 생성물 전용 폴더(호스트 마운트, git 제외)
RS=/home/ubuntu/ros2_ws/install/warehouse_localization_baseline_02/lib/warehouse_localization_baseline_02/run_scenario.sh
mkdir -p "$OUT"

bash "$RS" C1 c1 -24 -24  1.571 170 "$OUT"
bash "$RS" C2 c2 -24   8  0.000 150 "$OUT"
bash "$RS" C3 c3 -22 -22  1.710 260 "$OUT"
bash "$RS" C4 c4 -24   0 -1.571 130 "$OUT"
bash "$RS" C5 c5  24 -24  3.142 220 "$OUT"

echo "=== 전체 완료. 결과: $OUT ==="
ls -la "$OUT"
