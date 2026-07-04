# 실행 명령어 모음 (Runbook)

자주 쓰는 명령어를 상황별로 정리합니다. 복사해서 바로 사용하세요.

- **호스트(맥)** = 프로젝트 폴더 `~/Desktop/warehouse_localization` 에서 실행
- **컨테이너 안** = VNC 데스크톱 터미널 또는 `docker exec` 로 들어간 셸에서 실행

---

## 1. 이미지 빌드 / 컨테이너 관리 (호스트에서)

```bash
cd ~/Desktop/warehouse_localization

# 이미지 빌드 (최초 1회, 베이스 이미지 다운로드로 시간 소요)
docker compose build

# 컨테이너 시작 (백그라운드)
docker compose up -d

# 상태 확인
docker compose ps

# 로그 보기
docker compose logs -f

# 컨테이너 중지 / 종료(컨테이너 삭제)
docker compose stop
docker compose down

# 컨테이너 안으로 들어가기 (bash 셸)
docker exec -it warehouse_localization bash
```

브라우저 데스크톱 접속: <http://localhost:6080> → 「연결」 클릭

---

## 2. 시뮬레이션 실행 (컨테이너 안 / VNC 터미널에서)

```bash
# 로봇 모델 지정 (이미지 기본값으로 이미 설정돼 있지만, 새 셸이면 확인)
export TURTLEBOT3_MODEL=waffle

# TurtleBot3 창고(월드) + 로봇 스폰
ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py

# (참고) 다른 월드 예시
ros2 launch turtlebot3_gazebo turtlebot3_house.launch.py
ros2 launch turtlebot3_gazebo empty_world.launch.py
```

### 우리 커스텀 개활 창고 월드 (M2)
> 참고: `~/.bashrc`(및 Dockerfile)에 `source ~/ros2_ws/install/setup.bash` 자동 소싱을 넣어둠 →
> **새로 여는 터미널은 자동으로 패키지 인식**. 단, 소싱 추가 이전에 열려있던 터미널은 `source ~/.bashrc` 한 번 필요.
> 빌드 직후엔 새 패키지 반영 위해 `source ~/ros2_ws/install/setup.bash` (또는 새 터미널).
```bash
# 워크스페이스 빌드 (빌드 후 새 패키지는 재소싱 또는 새 터미널)
cd ~/ros2_ws && colcon build --packages-select warehouse_localization_sim_01
source ~/ros2_ws/install/setup.bash

# 개활 창고 월드 + waffle 스폰 (구석 -24,-24 에서 시작)
ros2 launch warehouse_localization_sim_01 warehouse_world.launch.py

# 월드 + RViz 한 번에 (RViz에서 /scan 빨간 점으로 featureless core 관찰)
ros2 launch warehouse_localization_sim_01 display.launch.py
#   → RViz: 벽 근처엔 빨간 스캔 점, 중앙 개활지로 가면 점이 사라짐
#   → 주행은 별도 터미널에서 teleop / cmd_vel / 자동 데모 중 택1

# 자동 주행 데모 (중앙<->특징 순회, 키보드 불필요) — 별도 터미널
ros2 run warehouse_localization_sim_01 auto_drive_demo.py
#   → RViz로 보면 중앙에서 빨간 점이 사라지고(스캔 빔) 특징 근처서 다시 찍힘. Ctrl+C로 정지.

# 월드만 헤드리스로 문법/로드 검증
gz sdf --check ~/ros2_ws/install/warehouse_localization_sim_01/share/warehouse_localization_sim_01/worlds/warehouse/warehouse_open.world
```

> 참고: `TURTLEBOT3_MODEL=waffle` 은 이미지 bashrc에 전역 설정되어 모든 터미널에 자동 적용되고,
> launch 파일도 자체적으로 이 값을 설정하므로(방탄), `source setup.bash` 후 바로 launch 해도 됩니다.
> (`ROS_LOCALHOST_ONLY` 는 원래 필요 없었음 — 스폰 실패의 진짜 원인은 "잔여 프로세스 정리 후 재시작".)

성공 판단 로그:
```
SpawnEntity: Successfully spawned entity [waffle]
[turtlebot3_diff_drive]: Advertise odometry on [/odom]
```

### 로봇 조종 (텔레옵) — 새 터미널에서
```bash
export TURTLEBOT3_MODEL=waffle
ros2 run turtlebot3_teleop teleop_keyboard
```
> **teleop 함정 주의**: (1) teleop 터미널을 **클릭해 포커스**해야 키가 먹음, (2) **W 1회=+0.01 m/s**라
> 눈에 보이려면 W를 15~20번 연타(teleop 화면의 `currently: linear velocity` 확인), (3) sim이 느리면
> (RTF<1) 작은 속도는 거의 안 보임.

### 로봇 조종 (직접 명령) — 포커스 불필요, 가장 확실
```bash
# 전진 0.3 m/s (Ctrl+C 로 중단)
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.3}}" -r 10
# 정지
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}}"
# 제자리 회전 (angular.z)
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{angular: {z: 0.5}}" -r 10
```

---

## 3. 동작 점검 (컨테이너 안)

```bash
# ROS2 기본
source /opt/ros/humble/setup.bash   # 새 셸이면 (bashrc에서 자동 source 됨)
ros2 node list
ros2 topic list

# 로컬라이제이션 관련 핵심 토픽 확인
ros2 topic list | grep -E "scan|odom|imu|cmd_vel|tf|clock"

# 실제 데이터 수신 확인
ros2 topic echo /scan --once
ros2 topic echo /odom --once
ros2 topic hz /scan          # 발행 주기 확인

# TF 트리 확인
ros2 run tf2_tools view_frames        # frames.pdf 생성
ros2 run tf2_ros tf2_echo odom base_footprint

# 설치 패키지 확인
ros2 pkg prefix turtlebot3_gazebo
ros2 pkg prefix nav2_bringup
ros2 pkg prefix robot_localization
```

---

## 4. 트러블슈팅 명령어

### 로봇이 안 뜰 때 → 깨끗한 재시작
```bash
pkill -9 -f gzserver; pkill -9 -f gzclient
pkill -9 -f robot_state_publisher; pkill -9 -f spawn_entity
sleep 2
export TURTLEBOT3_MODEL=waffle
ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py
```

### DDS 디스커버리 이상(새 터미널이 sim 토픽 못 봄) — ⚠️ 검증 후 사용
```bash
# 모든 ROS/gazebo 프로세스 종료 상태에서:
fastdds shm clean
# 또는 수동:
rm -f /dev/shm/fastrtps_* /dev/shm/sem.fastrtps_*
# 이후 시뮬레이션 재실행
```

### 현재 실행 중인 프로세스 확인
```bash
ps -eo user,pid,args | grep -iE "gzserver|gzclient|ros2 launch|robot_state" | grep -v grep
```

### 무해한 로그 (무시)
- `ALSA lib ... cannot find card '0'` → 사운드카드 없음, 영향 없음
- Gazebo `end-of-life in January 2025` 배너 → EOL 안내, 무방

---

## 5. 워크스페이스 빌드 (향후 ros2_ws/src 에 패키지 추가 후)

```bash
cd ~/ros2_ws          # 컨테이너 안 경로 (호스트의 ./ros2_ws 와 마운트됨)
colcon build --symlink-install
source install/setup.bash
```
