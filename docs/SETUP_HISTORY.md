# 셋업 · 트러블슈팅 이력 로그

> 날짜순으로 계속 추가합니다. 각 항목: **증상 → 원인 → 조치 → 검증 상태**.

---

## 2026-07-04 — 초기 Docker 환경 빌드 및 시뮬레이션 최초 구동

### 환경 개요
- **베이스 이미지**: `tiryoh/ros2-desktop-vnc:humble` (브라우저 접속 VNC 데스크톱 포함 ROS2 Humble)
- **구성 파일**: `Dockerfile`, `docker-compose.yml`, `.devcontainer/devcontainer.json`
- **추가 설치 패키지**: turtlebot3, turtlebot3-msgs, turtlebot3-simulations, navigation2, nav2-bringup, robot-localization, gazebo-ros-pkgs, colcon
- **접속**: 브라우저에서 `http://localhost:6080` → noVNC → 「연결」 → Ubuntu 데스크톱
- **워크스페이스 마운트**: `./ros2_ws` → 컨테이너 `/home/ubuntu/ros2_ws` (현재 `src/` 비어 있음)
- **기본 로봇 모델**: `TURTLEBOT3_MODEL=waffle`

### 1) 빌드 이슈 — 베이스 이미지 다운로드 매우 느림
- **증상**: `docker compose build`가 `FROM tiryoh/ros2-desktop-vnc:humble` 단계에서 40분 이상 정체. 특정 레이어(752MB, 1.3GB)가 수십 KB/s로 사실상 멈춤.
- **원인**: 네트워크 대역폭 병목(또는 Docker Hub 익명 pull 제한 추정). 이미지 총량 ≈ 압축 2.6GB.
- **조치**: 빌드 중단 → **네트워크 변경 후 재시작**. 완료된 레이어는 로컬 캐시로 재사용되어 이어받기됨.
- **결과**: 재시작 후 정상 완료. 최종 이미지 `warehouse-localization:humble` (약 12.1GB).
- **참고**: 네트워크 변경 직후 첫 시도에서 `dial tcp: lookup auth.docker.io: no such host` (DNS 일시 실패) 발생 → 재시도로 해소. (Docker Desktop VM이 새 네트워크 DNS를 잡는 데 잠깐 지연될 수 있음. 지속되면 Docker Desktop 재시작)

### 2) 실행 검증 — 컨테이너/ROS2/패키지 정상
- `docker compose up -d` → 컨테이너 `warehouse_localization` 기동, 포트 `6080:80` 매핑.
- ROS2 Humble, `TURTLEBOT3_MODEL=waffle` 자동 설정 확인.
- 핵심 패키지 존재 확인: `turtlebot3_gazebo`, `nav2_bringup`, `robot_localization`, `turtlebot3_navigation2`.
- noVNC 웹 데스크톱 `http://localhost:6080` → HTTP 200.

### 3) 시뮬레이션 최초 구동 실패 → 재시작으로 해결 (핵심 이슈)

실행 명령:
```bash
ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py
```

- **증상 (1차 실행)**: Gazebo 월드(육각형 벽 + 기둥)는 로드되지만 **로봇(waffle)이 스폰되지 않음**. 로그:
  ```
  [spawn_entity.py-4] [ERROR] Service /spawn_entity unavailable. Was Gazebo started with GazeboRosFactory?
  [spawn_entity.py-4] [ERROR] Spawn service failed. Exiting.
  ```
  → `spawn_entity`가 30초간 `/spawn_entity` 서비스를 못 찾고 종료. 월드는 `.world` 파일에서 gzserver가 직접 로드하므로 보이지만, 로봇은 서비스로 스폰되므로 안 뜸.

- **조치**: 잔여 프로세스 정리 후 **깨끗하게 재시작**.
  ```bash
  pkill -9 -f gzserver; pkill -9 -f gzclient; pkill -9 -f robot_state_publisher; pkill -9 -f spawn_entity
  sleep 2
  export ROS_LOCALHOST_ONLY=1
  export TURTLEBOT3_MODEL=waffle
  ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py
  ```

- **결과 (재시작)**: **로봇 스폰 성공.**
  ```
  [spawn_entity.py-4] Spawn status: SpawnEntity: Successfully spawned entity [waffle]
  [gzserver-1] [turtlebot3_diff_drive]: Subscribed to [/cmd_vel]
  [gzserver-1] [turtlebot3_diff_drive]: Advertise odometry on [/odom]
  [gzserver-1] [turtlebot3_diff_drive]: Publishing odom transforms between [odom] and [base_footprint]
  ```
  Gazebo 육각형 월드 중앙에 TurtleBot3 Waffle 로봇 정상 배치, 시뮬레이션 실행(FPS ~60).

> **⚠️ 원인에 대한 정확한 기록 (중요)**
> 재시작 시 `export ROS_LOCALHOST_ONLY=1`을 함께 넣었지만, 이후 조사에서 **실제 실행된 launch 프로세스에는 `ROS_LOCALHOST_ONLY`가 설정돼 있지 않았음(기본값 0)**을 확인했다. 즉 스폰 성공의 실제 원인은 `ROS_LOCALHOST_ONLY`가 아니라 **"잔여 프로세스/공유메모리 정리 후의 깨끗한 재시작"**일 가능성이 높다. (1차 실패는 최초 실행 시 오염된 상태 또는 타이밍 문제로 추정.)
> → 재발 시: `export`에 의존하기보다 **모든 gzserver/gzclient/ros2 프로세스를 완전히 정리하고 재시작**하는 것을 우선 시도할 것.

### 4) DDS 디스커버리 관련 관찰 (⚠️ 검증 필요 — 미확정)
- `docker exec`로 컨테이너에 들어가 `ros2 topic list` 시 **실행 중인 sim의 토픽(/scan, /odom 등)이 안 보이는** 현상 관찰.
- 반면 새로 띄운 두 프로세스(probe) 간에는 디스커버리 정상 동작.
- RMW: 기본 `rmw_fastrtps_cpp`. `~/.bashrc`·`/etc/bash.bashrc`에 별도 DDS 설정 없음(순수 기본).
- **가설**: FastDDS가 프로세스 비정상 종료 시 `/dev/shm/fastrtps_*` 잔재를 남기고, 누적되면 신규 노드 디스커버리가 깨질 수 있음.
- **미확정 이유**: 위 관찰은 전부 `docker exec` 기반이라, sim이 실행 중인 **VNC 데스크톱 내부의 새 터미널**에서도 동일하게 재현되는지 아직 확인하지 못함. 실제 문제인지, 진입 방식(docker exec) 차이로 인한 착시인지 **결론 보류**.
- **다음에 할 검증**: VNC 데스크톱에서 새 터미널을 열고 sim 실행 중 `ros2 topic list` 실행 →
  - `/scan`, `/odom`, `/cmd_vel`, `/tf`가 보이면 → 문제 없음(멀티 터미널 정상).
  - `/parameter_events`, `/rosout` 2개만 보이면 → 고립 확정 → 영구 대책 적용.

### 5) 무해한 로그 (무시해도 됨)
- `ALSA lib ... cannot find card '0'` / `ALCplaybackAlsa_open: Could not open playback device 'default'`
  → 컨테이너에 사운드카드가 없어 Gazebo(OpenAL)가 오디오 장치를 못 여는 것. **시뮬레이션 동작에 영향 없음.**
- Gazebo 상단 `This version of Gazebo reaches end-of-life in January 2025` 배너
  → Gazebo Classic 11 EOL 안내. 현재 학습/시뮬레이션 용도에는 문제 없음.

### 현재 상태 요약 (2026-07-04 기준)
- ✅ Docker 빌드 / 컨테이너 실행 / VNC 데스크톱
- ✅ Gazebo + turtlebot3_world + 로봇(waffle) 스폰 + 센서 플러그인(/scan, /odom, /imu, /cmd_vel) 동작
- ⚠️ 멀티 터미널 DDS 디스커버리: **VNC 터미널 기준 검증 대기**
- ⬜ 다음 단계: `ros2_ws/src`에 창고 로컬라이제이션 패키지 작성 (Nav2 + AMCL 또는 robot_localization EKF)
