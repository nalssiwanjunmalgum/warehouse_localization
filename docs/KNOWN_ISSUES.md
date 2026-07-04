# 알려진 이슈 · 빠른 대처법

재발 가능성이 있는 이슈와 즉시 적용할 대처를 요약합니다. 상세 경위는 [SETUP_HISTORY.md](./SETUP_HISTORY.md) 참조.

---

## 1. 로봇(waffle)이 스폰되지 않음 / `/spawn_entity` 서비스 타임아웃
**증상**
```
[spawn_entity.py] ERROR Service /spawn_entity unavailable. Was Gazebo started with GazeboRosFactory?
```
월드(벽·기둥)는 보이는데 로봇만 안 뜸.

**대처 (권장 순서)**
```bash
# 1) 모든 gazebo/ros 프로세스 완전 정리
pkill -9 -f gzserver; pkill -9 -f gzclient; pkill -9 -f robot_state_publisher; pkill -9 -f spawn_entity
sleep 2
# 2) 로봇 모델 지정 후 재실행
export TURTLEBOT3_MODEL=waffle
ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py
```
성공 로그: `SpawnEntity: Successfully spawned entity [waffle]`

> 핵심은 **깨끗한 재시작**. 잔여 프로세스가 남아 있으면 반복 실패할 수 있음.

---

## 2. 빌드 시 베이스 이미지 다운로드가 매우 느림/정체
**대처**
- 빌드 중단 후 네트워크 변경 → `docker compose build` 재시작 (완료 레이어는 캐시 재사용).
- 필요 시 Docker Hub 로그인으로 익명 pull 제한 완화: `docker login` 후 재빌드.

---

## 3. 네트워크 변경 직후 `lookup auth.docker.io: no such host`
**원인**: Docker Desktop VM이 새 네트워크 DNS를 아직 못 잡음.
**대처**: 잠시 후 재시도. 지속되면 **Docker Desktop 재시작**.

---

## 4. (✅ 대체로 해결) 멀티 터미널 DDS 디스커버리
**현황**: 깨끗하게 재시작된 sim에서는 멀티 터미널 통신 **정상** 확인됨(2026-07-04, teleop/topic pub로 로봇 이동 성공). 초기 "고립"은 지저분한 `/dev/shm` 상태에서 뜬 특정 인스턴스의 문제였음.

**만약 새 터미널에서 sim 토픽이 안 보이면**(`/parameter_events`, `/rosout`만):
```bash
# 모든 ROS/gazebo 프로세스 종료 상태에서 FastDDS 잔여 공유메모리 정리
pkill -9 -f gazebo; pkill -9 -f gzserver; pkill -9 -f gzclient
fastdds shm clean          # 또는: rm -f /dev/shm/fastrtps_* /dev/shm/sem.fastrtps_*
# 이후 sim 재실행 → 다른 터미널도 정상 합류
```
- 영구화 옵션(재발 잦으면): CycloneDDS 도입(`RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`, 패키지 설치+재빌드).

---

## 5. teleop로 로봇이 안 움직임
대개 DDS 문제 아님. 확인 순서:
1. teleop 터미널을 **클릭해 포커스** 상태로.
2. **W를 15~20번 연타** (1회 +0.01 m/s). teleop 화면 `currently: linear velocity` 값 확인.
3. sim이 느리면(RTF<1) 작은 속도는 거의 안 보임 → 값을 더 올리거나 직접 명령 사용.
4. 그래도 안 되면 직접 명령으로 파이프라인 확인:
   `ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.3}}" -r 10`
   그리고 `ros2 topic info /cmd_vel` 로 Publisher/Subscription 각각 1인지 확인.

---

## 무해한 로그 (무시)
- `ALSA lib ... cannot find card '0'`, `ALCplaybackAlsa_open` → 사운드카드 없음. 영향 없음.
- Gazebo `end-of-life in January 2025` 배너 → Gazebo Classic EOL 안내. 현재 용도엔 무방.
