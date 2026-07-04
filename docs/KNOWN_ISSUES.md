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

## 4. (⚠️ 검증 대기) 멀티 터미널 DDS 디스커버리 고립 가능성
**증상 후보**: 새 터미널에서 `ros2 topic list` 시 실행 중인 sim 토픽이 안 보이고 `/parameter_events`, `/rosout`만 표시.

**먼저 확인** (VNC 데스크톱 새 터미널에서):
```bash
ros2 topic list   # /scan, /odom, /cmd_vel, /tf 가 보이는지
```
- 보이면: 문제 없음.
- 안 보이면(2개만): 아래 대처.

**대처 후보 (확정 시 적용)**
```bash
# FastDDS 잔여 공유메모리 정리 (ROS 프로세스 모두 종료 상태에서)
fastdds shm clean          # 또는: rm -f /dev/shm/fastrtps_* /dev/shm/sem.fastrtps_*
```
- 영구화 옵션: CycloneDDS 도입(`RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`, 패키지 설치+재빌드 필요) 또는 셸 시작 시 자동 SHM 정리.

---

## 무해한 로그 (무시)
- `ALSA lib ... cannot find card '0'`, `ALCplaybackAlsa_open` → 사운드카드 없음. 영향 없음.
- Gazebo `end-of-life in January 2025` 배너 → Gazebo Classic EOL 안내. 현재 용도엔 무방.
