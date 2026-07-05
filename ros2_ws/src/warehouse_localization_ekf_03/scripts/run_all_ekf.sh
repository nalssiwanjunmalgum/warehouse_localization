#!/usr/bin/env bash
# run_all_ekf.sh — M5 C1~C5 를 노이즈만(N)·노이즈+EKF(E) 두 구성으로 순차 실행.
# 같은 노이즈(seed 고정)에서 EKF on/off 만 바꿔 완화 효과를 정량 비교.
# 사용: bash run_all_ekf.sh [OUTDIR] [MODES]
#   OUTDIR 기본 /home/ubuntu/ros2_ws/outputs/ekf
#   MODES  기본 "both" (noise 와 ekf 모두). "ekf" 또는 "noise" 로 한쪽만도 가능.
OUT="${1:-/home/ubuntu/ros2_ws/outputs/ekf}"
MODES="${2:-both}"
RS=/home/ubuntu/ros2_ws/install/warehouse_localization_ekf_03/lib/warehouse_localization_ekf_03/run_scenario_ekf.sh
mkdir -p "$OUT"

# 시나리오 주행 타임아웃(s). MAXT_OVERRIDE 환경변수를 주면 전 시나리오 일괄 적용(예: 180=3분).
mt() { [ -n "${MAXT_OVERRIDE:-}" ] && echo "$MAXT_OVERRIDE" || echo "$1"; }

# SCEN ROUTE INIT_X INIT_Y INIT_YAW(rad) MAXTIME  (baseline 과 동일 시나리오)
run_mode() {  # $1 = USE_EKF(0/1)
  bash "$RS" C1 c1 -24 -24  1.571 "$(mt 170)" "$OUT" "$1"
  bash "$RS" C2 c2 -24   8  0.000 "$(mt 150)" "$OUT" "$1"
  bash "$RS" C3 c3 -22 -22  1.710 "$(mt 260)" "$OUT" "$1"
  bash "$RS" C4 c4 -24   0 -1.571 "$(mt 130)" "$OUT" "$1"
  bash "$RS" C5 c5  24 -24  3.142 "$(mt 220)" "$OUT" "$1"
}

if [ "$MODES" = "both" ] || [ "$MODES" = "noise" ]; then
  echo "===== 구성 N: 노이즈만 (EKF 없음) ====="; run_mode 0
fi
if [ "$MODES" = "both" ] || [ "$MODES" = "ekf" ]; then
  echo "===== 구성 E: 노이즈 + EKF ====="; run_mode 1
fi

echo "=== 전체 완료. 결과: $OUT ==="
ls -la "$OUT"
