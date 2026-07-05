#!/usr/bin/env bash
# run_scenario.sh — P5 시나리오 하나를 헤드리스로 실행하고 결과(CSV·summary·plot)를 저장.
# 사용: bash run_scenario.sh <SCEN> <ROUTE> <INIT_X> <INIT_Y> <INIT_YAW> <MAXTIME> <OUTDIR>
# 예:   bash run_scenario.sh C1 c1 -24 -24 0.785 120 /home/ubuntu/results
#
# 주의: 반드시 '파일'로 실행할 것(bash <파일>). inline(-c)로 실행하면 스크립트 본문의
#       프로세스명이 argv 에 들어가 pkill 이 자기 자신을 죽인다.
# (set -u 는 ROS setup.bash 의 미설정 변수와 충돌하므로 쓰지 않음)
SCEN="$1"; ROUTE="$2"; IX="$3"; IY="$4"; IYAW="$5"; MAXT="$6"; OUT="$7"

source /opt/ros/humble/setup.bash
source /home/ubuntu/ros2_ws/install/setup.bash
export TURTLEBOT3_MODEL=waffle
SIM=/home/ubuntu/ros2_ws/install/warehouse_localization_sim_01/share/warehouse_localization_sim_01
BL=/home/ubuntu/ros2_ws/install/warehouse_localization_baseline_02
mkdir -p "$OUT"

clean() {
  pkill -9 -f "[g]zserver"; pkill -9 -f "[g]zclient"; pkill -9 -f "[r]obot_state_pub"
  pkill -9 -f "[s]pawn_entity"; pkill -9 -f "[a]mcl"; pkill -9 -f "[m]ap_server"
  pkill -9 -f "[l]ifecycle_manager"; pkill -9 -f "[m]etrics_recorder"; pkill -9 -f "[a]uto_drive"
}

echo "[$SCEN] 정리 + sim 기동 (init=$IX,$IY,$IYAW)"
clean; sleep 2; fastdds shm clean >/dev/null 2>&1

setsid gzserver "$SIM/worlds/warehouse/warehouse_open.world" \
  -slibgazebo_ros_init.so -slibgazebo_ros_factory.so -slibgazebo_ros_force_system.so \
  >/tmp/gz.log 2>&1 </dev/null &
sleep 8
ros2 run gazebo_ros spawn_entity.py -entity waffle \
  -file "$SIM/models/warehouse_waffle_lidar12/model.sdf" \
  -x "$IX" -y "$IY" -z 0.01 -Y "$IYAW" >/tmp/spawn.log 2>&1
setsid ros2 launch turtlebot3_gazebo robot_state_publisher.launch.py use_sim_time:=true \
  >/tmp/rsp.log 2>&1 </dev/null &
sleep 4

echo "[$SCEN] AMCL 기동"
# AMCL_PARAMS 환경변수로 파라미터 파일 오버라이드 가능(기본 amcl.yaml). z_hit 실험 등에 사용.
AMCL_ARG=""; [ -n "${AMCL_PARAMS:-}" ] && AMCL_ARG="amcl_params:=$AMCL_PARAMS"
setsid ros2 launch warehouse_localization_baseline_02 localization.launch.py $AMCL_ARG \
  >/tmp/amcl.log 2>&1 </dev/null &
sleep 12

echo "[$SCEN] 초기 포즈 설정"
read -r QZ QW < <(python3 -c "import math;y=$IYAW;print(math.sin(y/2), math.cos(y/2))")
ros2 topic pub --once /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \
  "{header: {frame_id: map}, pose: {pose: {position: {x: $IX, y: $IY, z: 0.0}, orientation: {z: $QZ, w: $QW}}, covariance: [0.25,0,0,0,0,0, 0,0.25,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0.068]}}" \
  >/dev/null 2>&1
sleep 3

CSV="$OUT/${SCEN}_baseline.csv"
echo "[$SCEN] 기록 + 주행 (route=$ROUTE, ${MAXT}s)"
setsid ros2 run warehouse_localization_baseline_02 metrics_recorder.py \
  --ros-args -p out_csv:="$CSV" >/tmp/rec.log 2>&1 </dev/null &
sleep 2
setsid ros2 run warehouse_localization_sim_01 auto_drive_demo.py \
  --ros-args -p route:="$ROUTE" -p loop:=false >/tmp/drive.log 2>&1 </dev/null &

sleep "$MAXT"

echo "[$SCEN] 정지 + 저장"
pkill -INT -f "[m]etrics_recorder"; sleep 5
pkill -9 -f "[a]uto_drive"

echo "[$SCEN] 요약 + 플롯"
python3 "$BL/lib/warehouse_localization_baseline_02/summarize.py" \
  "$CSV" --scenario "$SCEN" --out "$OUT/${SCEN}_baseline.summary.json" 2>&1 | tail -20
python3 "$BL/lib/warehouse_localization_baseline_02/plot_metrics.py" \
  "$CSV" "$OUT/${SCEN}_baseline.plot.png" 2>&1 | tail -1

clean; sleep 1
echo "[$SCEN] 완료 → $OUT/${SCEN}_baseline.{csv,summary.json,plot.png}"
