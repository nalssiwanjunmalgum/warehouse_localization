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

> **✅ 2026-07-04 후속 검증: 멀티 터미널 DDS 통신 정상으로 확정** — 아래 4) ⚠️ 항목 해소.
> M2 월드에서 teleop(별도 터미널)로 로봇 조종 시도 → `/cmd_vel` Publisher 1 + Subscription 1(gzserver)
> 로 정상 연결 확인. docker exec에서도 `/cmd_vel /odom /scan /imu` 모두 보임. 직접 `ros2 topic pub /cmd_vel`
> 로 로봇 이동 성공(x −24.00→−23.92). **초기 "고립"은 지저분한 shm 상태에서 뜬 특정 인스턴스의 문제였고,
> 깨끗하게 재시작된 sim에서는 멀티 터미널 통신이 정상**. → KNOWN_ISSUES #4 해결로 갱신.
>
> ※ 당시 teleop로 안 움직인 진짜 원인은 DDS가 아니라 teleop 사용법: (1) 터미널 키보드 포커스 필요,
> (2) W 1회=+0.01 m/s라 여러 번 연타 필요, (3) sim이 느려(RTF 0.41) 작은 속도는 거의 안 보임.

### 4) DDS 디스커버리 관련 관찰 (⚠️ → ✅ 위 후속 검증에서 해소)
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

---

## 2026-07-04 — Q&A: 지금 보이는 월드/로봇/맵 파일의 출처

**질문**: 아까 본 맵·waffle 로봇 파일은 어디에 있고 어떻게 생성된 것인가?

**답변**: **우리가 만든 게 아니라, Dockerfile의 `apt-get install`로 설치된 ROBOTIS TurtleBot3 공식 패키지에 원래 포함된 기본 예제 파일**이다. 전부 컨테이너 내부 `/opt/ros/humble/share/` 아래에 위치.

| 항목 | 경로 | 출처 패키지 |
|------|------|------------|
| 로봇 모델(waffle) | `/opt/ros/humble/share/turtlebot3_gazebo/models/turtlebot3_waffle/` (`model.sdf`) | ros-humble-turtlebot3-gazebo |
| 월드(.world) | `/opt/ros/humble/share/turtlebot3_gazebo/worlds/` (turtlebot3_world.world 등 8종) | ros-humble-turtlebot3-gazebo |
| 런치 | `/opt/ros/humble/share/turtlebot3_gazebo/launch/` (turtlebot3_world.launch.py 등) | ros-humble-turtlebot3-gazebo |
| 기본 맵 | `/opt/ros/humble/share/turtlebot3_navigation2/map/` (`map.pgm` + `map.yaml`) | ros-humble-turtlebot3-navigation2 |

**프로젝트 관점의 의미**:
- 지금 있는 육각형 월드 + waffle + 맵은 **"TurtleBot3 튜토리얼 기본 예제"** — 특징이 풍부해 AMCL이 잘 되는 환경. M1(스택 검증)엔 적합했으나 **우리 문제(특징 없는 개활지)와는 정반대**.
- 따라서 **M2에서 우리만의 개활지 `.world`를 새로 제작**해 `ros2_ws/src`에 넣어야 함. 기본 제공 파일은 건드리지 않고 우리 패키지에 별도 작성.
- 맵도 기본 `map.pgm`은 육각형 월드용이므로, 개활지 월드용 맵을 새로 떠야 함(맵 전략 P2에서 결정).
- `ros2_ws/src`는 현재 비어 있음 → 커스텀 월드/맵/런치/노드는 전부 여기에 신규 생성.

---

## 2026-07-04 — Q&A: `export`(TURTLEBOT3_MODEL) 없이 바로 launch 해도 되나?

**질문**: 이전에 export 안 해서 문제됐던 게 `install/setup.bash` 안에 있나? 바로 launch 하면 또 문제 생기지 않나?

**답변**: 문제없다. 두 가지를 구분해야 함.
- **`TURTLEBOT3_MODEL=waffle`**: 이미지 `/etc/bash.bashrc`에 `export`로 박혀 있어 **모든 터미널에 자동 적용**됨(확인 완료). `install/setup.bash`에는 없지만(그건 워크스페이스 패키지 경로만 추가) 전역 설정이 이미 잡아줌. 추가로 **launch 파일도 자체적으로 `SetEnvironmentVariable('TURTLEBOT3_MODEL','waffle')`로 고정**하도록 하드닝함 → 셸 env에 아예 비의존(방탄).
- **`ROS_LOCALHOST_ONLY`**: 애초에 스폰 실패의 원인이 아니었음(성공했던 launch에도 미설정). 진짜 원인은 "잔여 프로세스/SHM 정리 후 깨끗한 재시작". 따라서 이 export는 불필요.

**결론**: `source ~/ros2_ws/install/setup.bash && ros2 launch warehouse_localization_sim_01 warehouse_world.launch.py` 로 바로 실행 OK. 스폰 타임아웃이 재발하면 프로세스 정리 후 재시작(→ KNOWN_ISSUES #1).

---

## 2026-07-04 — 공장/창고 환경 구조 분리

- 결정: **지금은 구조(디렉토리·네이밍)만 분리**, 공장 월드 실제 제작은 추후. 창고 M2 계속.
- 패키지 `warehouse_localization_sim_01` 내부를 환경별로 재편:
  - `worlds/warehouse/warehouse_open.world` (창고, 제작 완료) / `worlds/factory/` (자리표시자)
  - `maps/warehouse/` · `maps/factory/` (자리표시자, 맵은 P2에서)
- 두 환경은 "특징 없는 개활지" 문제를 공유하되 장애물 성격이 다름(창고=랙/선반, 공장=생산 설비). 상세: [M2_WORLD_DESIGN.md](./M2_WORLD_DESIGN.md).
