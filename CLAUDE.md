# CLAUDE.md

이 파일은 Claude Code(claude.ai/code)가 이 저장소에서 작업할 때 참고하는 프로젝트 컨텍스트입니다.
목적은 **"이 토이 프로젝트가 무엇을, 왜 하려는지"를 잃지 않고 작업을 추적**하는 것입니다.

---

## 1. 프로젝트 한 줄 정의

> **특이점(feature)이 부족한 공장/창고 개활지에서 물류 로봇의 Localization(자기 위치 추정)을 확보하는 방법을,
> ROS2 시뮬레이션 위에서 단계적으로 구현·시각화·정량 평가하는 토이 프로젝트.**

산업용 결과물이 아니라 **개념 검증(PoC) + 학습**이 목적. "가볍게" 돌아가면서 알고리즘이 실제로 동작하는지를
눈(RViz)과 숫자(오차 지표)로 보여주는 것이 핵심 산출물.

---

## 2. 왜 어려운 문제인가 (문제의 본질)

일반 실내 로봇 Localization은 **AMCL**(Adaptive Monte Carlo Localization)을 쓴다.
사전 지도(occupancy grid) + 2D LiDAR 스캔 + 오도메트리를 파티클 필터로 정합해 위치를 추정한다.
→ 이 방식은 **LiDAR가 주변의 구별되는 기하학적 특징을 봐야** 위치를 보정할 수 있다.

그런데 대상 환경은:

- **기둥 간격 20m** → LiDAR 유효 range(본 프로젝트는 12m로 설정) 밖이라 대부분 구간에서 기둥이 안 잡힘
  *(참고: waffle 기본 LiDAR는 max 3.5m로 매우 짧음 → 산업용 수준인 12m로 상향. 상세: [docs/M2_WORLD_DESIGN.md](docs/M2_WORLD_DESIGN.md))*
- **적재물이 기둥을 가림** → 있어도 안 보임
- **사방이 뚫린 개활지** → 스캔이 다 비슷하게 생김 (특징 부재 = perceptual aliasing)

결과: 파티클 필터가 수렴하지 못하고, **오도메트리 드리프트**(바퀴 미끄러짐·누적 오차)를 잡아줄 근거가 없어
위치가 서서히 어긋난다. **이 실패를 먼저 눈으로 보여주는 것**이 프로젝트의 출발점(= 문제 제기)이다.

---

## 3. 접근 전략 — 3단계 비교 실험

같은 시뮬레이션 환경에서 지표만 갈아끼우며 비교한다. feature가 없을 때 길은 두 가지뿐:
**(1) 센서 융합으로 추측항법을 강화**하거나, **(2) 환경에 인공 특징을 심어 절대 위치를 보정**한다.
실제 산업용 AGV/AMR은 (2)를 쓴다.

| 단계 | 구성 | 기대 결과 | 역할 |
|------|------|-----------|------|
| **Baseline** | AMCL only | 개활지에서 드리프트/수렴 실패 | 문제 제기 |
| **+ EKF 융합** | 바퀴 오도메트리 + IMU를 `robot_localization` EKF로 융합 | 드리프트가 늦춰지지만 여전히 누적 오차 | 완화(근본 해결 아님) |
| **+ 랜드마크 보정** | 반사판(retro-reflector)을 알려진 좌표에 설치 → LiDAR intensity 튀는 지점 검출 → 3개 이상 보이면 삼각측량으로 절대 위치 확정 | 절대 위치가 잡히며 오차 급감 | 해결 |

**접근법 메뉴 (참고):**
- **A. 센서 융합 (EKF)** — 어떤 조합에도 깔고 가는 기반. 보정 없이 버티는 시간을 늘림.
- **B. 리플렉터/랜드마크 기반 (산업 표준)** — SICK·Kollmorgen 등 실제 창고 AGV 방식. 2D LiDAR 스택과 가장 잘 맞음. **← 본 프로젝트의 핵심 해결책.**
- **C. AprilTag(피듀셜 마커) + 카메라** — 시뮬레이션에 얹기 가장 쉬우나 카메라를 스택에 추가해야 함. (대안/확장)

---

## 4. 시각화 & 정량 지표

시뮬레이션의 최대 강점 = **Ground Truth(정답 위치)를 공짜로 얻는다**(Gazebo가 실제 좌표를 알려줌).
추정값 vs 정답을 비교해 오차를 수치화한다.

- **ATE** (Absolute Trajectory Error): 추정 경로 vs 실제 경로의 RMSE — 전체 정확도 대표 지표
- **RPE** (Relative Pose Error): 구간별 드리프트(m당 오차)
- **AMCL 공분산(covariance)**: 로봇의 확신도 — 개활지에서 폭발하는 걸 시각화
- **가시 랜드마크 수 vs 시점별 오차**: 랜드마크가 안 보일 때 오차가 커지는 상관관계
- **목표점 최종 도달 오차 / 성공률**: Nav2로 목표까지 갔을 때 실제로 얼마나 정확히 섰는가
- **수렴 시간, CPU 사용률/업데이트 주기**: "가볍게" 돌아가는지

**도구**: RViz2에 추정 위치·파티클·실제 위치를 겹쳐 표시 / 오차는 `rosbag` 기록 후 Python(matplotlib, [evo](https://github.com/MichaelGrupp/evo)) 플롯.

---

## 5. 기술 스택

- **ROS2 Humble** (베이스 이미지: `tiryoh/ros2-desktop-vnc:humble`, 브라우저 VNC 데스크톱)
- **TurtleBot3** (모델: `waffle`) — 시뮬레이션 로봇 플랫폼
- **Gazebo** — 물리 시뮬레이터 + Ground Truth 제공
- **2D LiDAR** — 주 센서(랜드마크 intensity 검출에도 사용)
- **IMU** — EKF 융합용 관성 센서 *(초안의 "IMV"는 IMU의 오기)*
- **Nav2** — 경로 계획·주행
- **robot_localization** — EKF 센서 융합
- **AMCL** — 파티클 필터 Localization(베이스라인)

---

## 6. 개발 환경 (현재 구성)

Docker 기반. 호스트(macOS)에서 컨테이너를 띄워 브라우저로 GUI에 접속한다.

```bash
docker compose up -d --build      # 최초 빌드 & 실행
# 브라우저에서 http://localhost:6080 접속 → ROS2 데스크톱
```

- `Dockerfile` — Humble + TurtleBot3 + Nav2 + robot_localization + Gazebo 설치. 컨테이너 진입 시 ROS 환경·`TURTLEBOT3_MODEL=waffle` 자동 source.
- `docker-compose.yml` — 포트 `6080`(VNC), `ros2_ws`를 호스트에 볼륨 마운트, `shm_size: 1gb`(Gazebo 화면 검게 나오면 2gb로).
- `.devcontainer/devcontainer.json` — VS Code Dev Container로 컨테이너에 직접 붙어 작업(Python/ROS/Docker 확장 포함).
- `ros2_ws/` — colcon 워크스페이스. `src/`에 프로젝트 패키지를 만든다. **현재 비어 있음.**

**워크스페이스 빌드(컨테이너 내부):**
```bash
cd ~/ros2_ws && colcon build --symlink-install && source install/setup.bash
```

---

## 7. 진행 현황 & 로드맵

> 상세 작업 상태는 [.claude/TASKS.md](.claude/TASKS.md), 단계별 문서는 [docs/](docs/) 참조.

### 완료
- [x] Docker/devcontainer 기반 ROS2 Humble 환경 구성 (VNC 데스크톱) + 패키지 설치
- [x] **M1. 환경 검증** — Gazebo + TurtleBot3 구동, DDS/스폰 이슈 해결
- [x] **M2. 개활지 월드** — 외벽 60×60 + 기둥 8개(20m 격자) + 랙 + 12m LiDAR + RViz + 자동주행 (`warehouse_localization_sim_01`)
- [x] **P2. 맵 전략** — SLAM 대신 "라이다+ground-truth"로 드리프트-0 기준 지도
- [x] **P5. 검증 시나리오** — C1~C5 + 캡처 규격 (docs/P5_SCENARIOS, CAPTURE_SPEC)
- [x] **M4. 지표 파이프라인** — ground-truth + CSV 기록 + summarize(ATE/RPE/공분산) + plot
- [x] **M3. Baseline (AMCL)** — 개활지 실패 재현·시각화, C1~C5 정량 결과 (`warehouse_localization_baseline_02`). 개활 횡단 ATE 24~34m(aliasing으로 회복 불가). 분석: docs/M3_ANALYSIS
- [x] **④ 노이즈 주입 + M5. +EKF 융합** — 바퀴 오도에 헤딩 바이어스 드리프트 주입 후 `robot_localization` EKF(오도 속도+IMU 절대 yaw)로 완화 (`warehouse_localization_ekf_03`, 모델 `warehouse_waffle_ekf`, 결과 `outputs/ekf/`). **혼합 결과가 핵심**: 드리프트 지배 국면(C4)에선 EKF가 ATE 10.5→2.3m 완전 복구, 그러나 풀 개활 횡단은 aliasing 대재앙이 지배해 효과가 묻히고 **cov(확신도)는 세 구성 모두 불변** = 절대위치 실패는 못 고침 → 완화≠해결. 설계: docs/M5_EKF, 분석: docs/M5_ANALYSIS

- [x] **P3. 센서·랜드마크 설계** — 반사판 16개 좌표·불규칙 배치(중앙 개활 ≥3 within 12m, core 4개)·landmarks DB 포맷 확정. **intensity 검출은 이 환경서 막힘**(CPU ray는 laser_retro 무시→intensities 0, gpu_ray는 헤드리스 렌더 불가) → **기하 검출+성좌매칭**으로 결정. 설계: docs/P3_SENSOR_LANDMARK
- [x] **M6. +랜드마크 보정 (해결)** — 반사판 기하 검출 + 성좌 연관 + 2D Procrustes 삼각측량 → map→odom 절대보정 (`warehouse_localization_landmark_04`, 반사판 오버레이 월드, AMCL 없음·EKF 유지). **C1~C5 ATE 24~34m → 0.13~0.32m (~100~200×), cov·aliasing 점프 소멸**. 개활지 절대위치 문제 해결. 결과 `outputs/landmark/`. 분석: docs/M6_ANALYSIS
- [x] **M7. 종합 비교** — 3단계(Baseline→+EKF→+Landmark) 동일 시나리오·지표 비교. `plot_final_compare.py` → `outputs/landmark/final_compare_{bars,curves}.png`(ATE 로그축+cov). 요약표: docs/M6_ANALYSIS §4.

> **프로젝트 결론(3단계 완성)**: 개활 창고에서 AMCL은 aliasing으로 실패(M3), EKF는 드리프트만 완화(M5), 반사판 절대보정이 문제를 해결(M6). = 실제 산업용 AGV가 반사판을 쓰는 이유의 정량 재현.

---

## 8. 작업 기획 체크리스트

3단계 비교 실험(§3)을 제대로 굴리기 위해 기획 단계에서 결정·설계해야 하는 항목들.
"환경"과 "지도"는 다른 물건이라는 점에 유의(월드 = 로봇이 실제로 굴러다니는 3D 공간 / 맵 = 로봇에게 주는 점유격자).

| # | 항목 | 무엇을 정하나 | 비고 |
|---|------|--------------|------|
| ① | **월드 설계** | Gazebo `.world`: 기둥 20m 간격 + 적재물로 기둥 가림 | 문제를 만드는 공간 |
| ② | **맵 전략** | SLAM으로 뜰지 / 수동 제작 | 개활지라 맵 대부분이 비어 있음 = 문제의 본질 |
| ③ | **센서·랜드마크 설계** | LiDAR range, IMU 노이즈, 반사판 개수·좌표·배치 | 랜드마크는 §3-B의 핵심 |
| ④ | **노이즈 주입 설계** ★ | 바퀴 미끄러짐·IMU 바이어스 주입 | 시뮬 오도메트리가 너무 정확하면 드리프트가 재현 안 됨 → 문제 성립 안 함 *(추후 작업)* |
| ⑤ | **검증 시나리오** | 경로 형태(직진/왕복/루프), 시작·목표점, 기둥 안 보이는 스트레스 구간 | 루프 경로가 드리프트 누적 관찰에 유리 |
| ⑥ | **비교 실험 프로토콜** ★ | 통제 변수(월드·경로·시작포즈·seed 고정), 반복 횟수 | Localization 방법만 바꿔 공정 비교 *(추후 작업)* |
| ⑦ | **성공 기준/가설** | "baseline ATE는 X 이상 터지고, 랜드마크는 Y 이하로 잡힌다"를 실험 전에 숫자로 | 결과 해석을 명확하게 |
| ⑧ | **지표 수집·시각화** | Ground Truth → rosbag → ATE/RPE/공분산 플롯 | §4 참조 |

> ④ 노이즈 주입, ⑥ 실험 설계는 **추후 상세화 예정**. 현재는 나머지를 우선 진행.

작업 항목의 진행 상태(할 일 / 진행 중 / 완료)는 [.claude/TASKS.md](.claude/TASKS.md)에서 관리한다.

---

## 9. 작업 원칙 (Claude 참고)

- 사용자는 **이 도메인이 처음**이다. 새 개념·용어는 짧게 왜 필요한지 곁들여 설명한다.
- "가볍게" 돌리는 게 목표다. 과한 실사양 구성보다 **개념이 드러나는 최소 구성**을 우선한다.
- 각 단계는 **같은 환경에서 지표만 바꿔 비교**할 수 있게 재현 가능하게 유지한다.
- 새 패키지/런치/월드를 추가하면 이 파일의 **7. 진행 현황**을 갱신한다.
