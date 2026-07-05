#!/usr/bin/env bash
# run_scenario_landmark.sh — M6 시나리오 하나를 헤드리스 실행. 노이즈+EKF+반사판 절대보정.
# 사용: bash run_scenario_landmark.sh <SCEN> <ROUTE> <INIT_X> <INIT_Y> <INIT_YAW> <MAXTIME> <OUTDIR>
#   출력: ${SCEN}_landmark.{csv,summary.json,plot.png}
#
# 스택: 반사판 오버레이 월드 + EKF 모델(diff_drive TF off) + noise_injector(TF off)
#       + EKF(odom→base) + landmark_localizer(map→odom, 반사판 삼각측량). **AMCL·map_server 없음.**
#   → 최종 추정 = /landmark_pose. metrics_recorder 를 est_topic:=/landmark_pose 로.
#
# 주의: 반드시 '파일'로 실행(inline -c 금지). 정리 pkill 은 대괄호형.
SCEN="$1"; ROUTE="$2"; IX="$3"; IY="$4"; IYAW="$5"; MAXT="$6"; OUT="$7"
# rclpy 는 파라미터 타입 엄격 — init 값을 DOUBLE 로 강제(정수 -24 → -24.000)
IXF=$(printf '%.4f' "$IX"); IYF=$(printf '%.4f' "$IY"); IYAWF=$(printf '%.4f' "$IYAW")

source /opt/ros/humble/setup.bash
source /home/ubuntu/ros2_ws/install/setup.bash
export TURTLEBOT3_MODEL=waffle
SIM=/home/ubuntu/ros2_ws/install/warehouse_localization_sim_01/share/warehouse_localization_sim_01
BL=/home/ubuntu/ros2_ws/install/warehouse_localization_baseline_02
EK=/home/ubuntu/ros2_ws/install/warehouse_localization_ekf_03
LM=/home/ubuntu/ros2_ws/install/warehouse_localization_landmark_04
LANDMARKS="$LM/share/warehouse_localization_landmark_04/config/landmarks.yaml"
mkdir -p "$OUT"

clean() {
  pkill -9 -f "[g]zserver"; pkill -9 -f "[g]zclient"; pkill -9 -f "[r]obot_state_pub"
  pkill -9 -f "[s]pawn_entity"; pkill -9 -f "[m]etrics_recorder"; pkill -9 -f "[a]uto_drive"
  pkill -9 -f "[n]oise_injector"; pkill -9 -f "[e]kf_node"; pkill -9 -f "[l]andmark_localizer"
}

echo "[$SCEN/landmark] 정리 + 반사판 월드 기동 (init=$IX,$IY,$IYAW)"
clean; sleep 2; fastdds shm clean >/dev/null 2>&1

setsid gzserver "$SIM/worlds/warehouse/warehouse_reflectors.world" \
  -slibgazebo_ros_init.so -slibgazebo_ros_factory.so -slibgazebo_ros_force_system.so \
  >/tmp/gz.log 2>&1 </dev/null &
sleep 8
ros2 run gazebo_ros spawn_entity.py -entity waffle \
  -file "$SIM/models/warehouse_waffle_ekf/model.sdf" \
  -x "$IX" -y "$IY" -z 0.01 -Y "$IYAW" >/tmp/spawn.log 2>&1
setsid ros2 launch turtlebot3_gazebo robot_state_publisher.launch.py use_sim_time:=true \
  >/tmp/rsp.log 2>&1 </dev/null &
sleep 4

echo "[$SCEN/landmark] 노이즈 주입(TF off) + EKF(odom→base)"
setsid ros2 run warehouse_localization_ekf_03 noise_injector.py --ros-args \
  -p use_sim_time:=true -p publish_tf:=false -p seed:=0 >/tmp/noise.log 2>&1 </dev/null &
sleep 2
setsid ros2 run robot_localization ekf_node --ros-args \
  --params-file "$EK/share/warehouse_localization_ekf_03/config/ekf.yaml" \
  >/tmp/ekf.log 2>&1 </dev/null &
sleep 4

echo "[$SCEN/landmark] 반사판 절대보정 노드 (map→odom)"
setsid ros2 run warehouse_localization_landmark_04 landmark_localizer.py --ros-args \
  -p use_sim_time:=true -p landmarks_yaml:="$LANDMARKS" \
  -p init_x:="$IXF" -p init_y:="$IYF" -p init_yaw:="$IYAWF" >/tmp/landmark.log 2>&1 </dev/null &
sleep 5

CSV="$OUT/${SCEN}_landmark.csv"
echo "[$SCEN/landmark] 기록 + 주행 (route=$ROUTE, ${MAXT}s)"
setsid ros2 run warehouse_localization_baseline_02 metrics_recorder.py \
  --ros-args -p out_csv:="$CSV" -p est_topic:=/landmark_pose >/tmp/rec.log 2>&1 </dev/null &
sleep 2
setsid ros2 run warehouse_localization_sim_01 auto_drive_demo.py \
  --ros-args -p route:="$ROUTE" -p loop:=false >/tmp/drive.log 2>&1 </dev/null &

sleep "$MAXT"

echo "[$SCEN/landmark] 정지 + 저장"
pkill -INT -f "[m]etrics_recorder"; sleep 5
pkill -9 -f "[a]uto_drive"

echo "[$SCEN/landmark] 요약 + 플롯"
python3 "$BL/lib/warehouse_localization_baseline_02/summarize.py" \
  "$CSV" --scenario "${SCEN}_landmark" --out "$OUT/${SCEN}_landmark.summary.json" 2>&1 | tail -20
python3 "$BL/lib/warehouse_localization_baseline_02/plot_metrics.py" \
  "$CSV" "$OUT/${SCEN}_landmark.plot.png" 2>&1 | tail -1

clean; sleep 1
echo "[$SCEN/landmark] 완료 → $OUT/${SCEN}_landmark.{csv,summary.json,plot.png}"
