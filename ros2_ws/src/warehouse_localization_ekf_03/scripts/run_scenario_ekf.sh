#!/usr/bin/env bash
# run_scenario_ekf.sh — M5 시나리오 하나를 헤드리스로 실행. 노이즈 주입 + (선택)EKF.
# 사용: bash run_scenario_ekf.sh <SCEN> <ROUTE> <INIT_X> <INIT_Y> <INIT_YAW> <MAXTIME> <OUTDIR> <USE_EKF>
#   USE_EKF: 1 → 구성 E(noise+EKF, 완화) / 0 → 구성 N(noise만)
#   출력 파일 접미사: USE_EKF=1 → _ekf, 0 → _noise  (예: C1_ekf.csv / C1_noise.csv)
#
# baseline run_scenario.sh 와 동일 골격. 차이:
#  - EKF 모델 변형(warehouse_waffle_ekf, diff_drive TF off) 스폰
#  - noise_injector 로 드리프트 주입 (E: TF off / N: TF on)
#  - E 에선 robot_localization ekf_node 가 odom→base TF 발행
#  - 지표 기록·요약·플롯은 baseline_02 스크립트 재사용
#
# 주의: 반드시 '파일'로 실행(bash <파일>). inline(-c)은 pkill 이 자기 자신을 죽인다.
SCEN="$1"; ROUTE="$2"; IX="$3"; IY="$4"; IYAW="$5"; MAXT="$6"; OUT="$7"; USE_EKF="${8:-1}"

source /opt/ros/humble/setup.bash
source /home/ubuntu/ros2_ws/install/setup.bash
export TURTLEBOT3_MODEL=waffle
SIM=/home/ubuntu/ros2_ws/install/warehouse_localization_sim_01/share/warehouse_localization_sim_01
BL=/home/ubuntu/ros2_ws/install/warehouse_localization_baseline_02
EK=/home/ubuntu/ros2_ws/install/warehouse_localization_ekf_03
mkdir -p "$OUT"

if [ "$USE_EKF" = "1" ]; then MODE="ekf"; PUB_TF="false"; else MODE="noise"; PUB_TF="true"; fi

clean() {
  pkill -9 -f "[g]zserver"; pkill -9 -f "[g]zclient"; pkill -9 -f "[r]obot_state_pub"
  pkill -9 -f "[s]pawn_entity"; pkill -9 -f "[a]mcl"; pkill -9 -f "[m]ap_server"
  pkill -9 -f "[l]ifecycle_manager"; pkill -9 -f "[m]etrics_recorder"; pkill -9 -f "[a]uto_drive"
  pkill -9 -f "[n]oise_injector"; pkill -9 -f "[e]kf_node"
}

echo "[$SCEN/$MODE] 정리 + sim 기동 (init=$IX,$IY,$IYAW)"
clean; sleep 2; fastdds shm clean >/dev/null 2>&1

setsid gzserver "$SIM/worlds/warehouse/warehouse_open.world" \
  -slibgazebo_ros_init.so -slibgazebo_ros_factory.so -slibgazebo_ros_force_system.so \
  >/tmp/gz.log 2>&1 </dev/null &
sleep 8
ros2 run gazebo_ros spawn_entity.py -entity waffle \
  -file "$SIM/models/warehouse_waffle_ekf/model.sdf" \
  -x "$IX" -y "$IY" -z 0.01 -Y "$IYAW" >/tmp/spawn.log 2>&1
setsid ros2 launch turtlebot3_gazebo robot_state_publisher.launch.py use_sim_time:=true \
  >/tmp/rsp.log 2>&1 </dev/null &
sleep 4

echo "[$SCEN/$MODE] 노이즈 주입 (publish_tf=$PUB_TF)"
setsid ros2 run warehouse_localization_ekf_03 noise_injector.py --ros-args \
  -p use_sim_time:=true -p publish_tf:=$PUB_TF -p seed:=0 \
  >/tmp/noise.log 2>&1 </dev/null &
sleep 2

if [ "$USE_EKF" = "1" ]; then
  echo "[$SCEN/$MODE] EKF 기동 (odom→base TF)"
  setsid ros2 run robot_localization ekf_node --ros-args \
    --params-file "$EK/share/warehouse_localization_ekf_03/config/ekf.yaml" \
    >/tmp/ekf.log 2>&1 </dev/null &
  sleep 3
fi

echo "[$SCEN/$MODE] AMCL 기동"
setsid ros2 launch warehouse_localization_baseline_02 localization.launch.py \
  >/tmp/amcl.log 2>&1 </dev/null &
sleep 12

echo "[$SCEN/$MODE] 초기 포즈 설정"
read -r QZ QW < <(python3 -c "import math;y=$IYAW;print(math.sin(y/2), math.cos(y/2))")
ros2 topic pub --once /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \
  "{header: {frame_id: map}, pose: {pose: {position: {x: $IX, y: $IY, z: 0.0}, orientation: {z: $QZ, w: $QW}}, covariance: [0.25,0,0,0,0,0, 0,0.25,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0.068]}}" \
  >/dev/null 2>&1
sleep 3

CSV="$OUT/${SCEN}_${MODE}.csv"
echo "[$SCEN/$MODE] 기록 + 주행 (route=$ROUTE, ${MAXT}s)"
setsid ros2 run warehouse_localization_baseline_02 metrics_recorder.py \
  --ros-args -p out_csv:="$CSV" >/tmp/rec.log 2>&1 </dev/null &
sleep 2
setsid ros2 run warehouse_localization_sim_01 auto_drive_demo.py \
  --ros-args -p route:="$ROUTE" -p loop:=false >/tmp/drive.log 2>&1 </dev/null &

sleep "$MAXT"

echo "[$SCEN/$MODE] 정지 + 저장"
pkill -INT -f "[m]etrics_recorder"; sleep 5
pkill -9 -f "[a]uto_drive"

echo "[$SCEN/$MODE] 요약 + 플롯"
python3 "$BL/lib/warehouse_localization_baseline_02/summarize.py" \
  "$CSV" --scenario "${SCEN}_${MODE}" --out "$OUT/${SCEN}_${MODE}.summary.json" 2>&1 | tail -20
python3 "$BL/lib/warehouse_localization_baseline_02/plot_metrics.py" \
  "$CSV" "$OUT/${SCEN}_${MODE}.plot.png" 2>&1 | tail -1

clean; sleep 1
echo "[$SCEN/$MODE] 완료 → $OUT/${SCEN}_${MODE}.{csv,summary.json,plot.png}"
