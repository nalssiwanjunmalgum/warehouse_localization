# M2 — 개활지 창고 월드 설계

> 상태: **설계 확정 중** · 관련 기획: CLAUDE.md §8 ①월드설계 / ③센서·랜드마크
> 목적: "특징 없는 개활 창고"를 시뮬레이션으로 구현해 **AMCL이 실패하는 조건**을 만든다.

---

## 핵심 원리
우리 문제의 본질은 *"LiDAR가 보정에 쓸 기하학적 특징이 없다"*이며, 이는
**[LiDAR 유효 거리] vs [특징(기둥/벽) 간격]** 의 관계로 결정된다.
→ 개활 구간에서 **어떤 벽·기둥도 LiDAR 범위 밖**에 있어야 문제가 성립한다.

## 확정된 결정 (2026-07-04)

| 항목 | 결정 | 근거 |
|------|------|------|
| **LiDAR 유효 거리** | 기본 3.5m → **12m로 상향** (커스텀 waffle 모델) | 실제 창고 AGV(SICK 등) 수준. 개활지에서 "간헐적 관측" 규제 → 3단계 차이가 선명 |
| **외곽/경계** | **외벽 있는 실내 창고** (건물이 충분히 커서 내부 개활 구간은 벽이 12m 밖) | 공장·창고는 실내 건물. 단, 중앙부는 벽도 안 보이는 featureless core 확보 |
| **기둥 간격** | **20m 격자** | CLAUDE.md §2/§8 명시. 12m LiDAR로는 격자 중앙(≈14m)에서 안 보임 |
| **반사판(reflector)** | **M2에는 미포함** → M6에서 오버레이로 추가 | 베이스라인은 특징이 없어야 실패가 재현됨. 로봇/경로/기둥은 동일 유지해 공정 비교 |

> ⚠️ CLAUDE.md §5에 "LiDAR 8~12m"로 적혀 있었으나, **기본 waffle LiDAR 실측 max=3.5m**임을 확인. 위와 같이 12m로 상향하기로 결정.

## 스트로우맨 레이아웃 (60m × 60m 실내 창고)

```
   60m × 60m 실내, 외벽(───), 구조 기둥(●) 20m 격자(중앙 비움), 적재 랙(▓)
   ┌──────────────────────────────────────┐
   │  ●            ●            ●          │  기둥 8개:
   │        ▓▓                             │   (-20,-20)(0,-20)(20,-20)
   │                        ▓▓             │   (-20, 0)        (20, 0)
   │  ●                        ●   ← 랙이  │   (-20,20)(0,20)(20,20)
   │                              기둥 가림 │   ※ 중앙(0,0)은 비움
   │              ★ featureless core       │
   │         (반경 ~8m: 기둥·벽 모두 12m 밖) │  ★에서: 가장 가까운 기둥 20m,
   │  ●            ●            ●          │        가장 가까운 벽 30m
   │     ▓▓                                │        → 12m LiDAR로 아무것도 안 보임
   │                    ▓▓                 │
   │  ●            ●            ●          │
   └──────────────────────────────────────┘
```

**요소 스펙(초안, 조정 가능)**
- **바닥**: 평평한 ground_plane (60×60)
- **외벽**: 높이 ~2.5m, 두께 0.2m, 사방 폐쇄 (건물 경계 = ±30)
- **구조 기둥(●)**: 지름 ~0.4m(또는 0.4m 각) 원기둥 8개, 20m 격자, 중앙 비움
- **적재 랙(▓)**: 팔레트 박스 더미(약 2×1×1.5m) 3~4개, 일부 기둥을 특정 각도에서 가림 → "있어도 안 보임" 재현
- **로봇 시작/경로**: 루프 경로 권장(드리프트 누적 관찰). 상세는 P5(검증 시나리오)에서

## 산출물 — `ros2_ws/src/warehouse_localization_sim_01`
**환경(공장/창고)을 구조적으로 분리** (2026-07-04 결정: "지금은 구조만 분리", 공장 월드 제작은 추후):
```
warehouse_localization_sim_01/
├── worlds/
│   ├── warehouse/warehouse_open.world   # 창고 (제작 완료)
│   └── factory/  (README 자리표시자)     # 공장 (추후)
├── maps/
│   ├── warehouse/  (자리표시자)          # 창고 맵 (P2에서)
│   └── factory/    (자리표시자)          # 공장 맵 (추후)
├── launch/warehouse_world.launch.py     # gazebo + 월드 + waffle 스폰
├── CMakeLists.txt / package.xml
└── (추후) models/ · config/             # 커스텀 LiDAR 로봇 · AMCL/EKF/Nav2 파라미터
```
> 공장(factory)과 창고(warehouse)는 "특징 없는 개활지" 문제는 공유하되 장애물 성격이 다름
> (창고=팔레트 랙/선반 통로, 공장=생산 설비/넓은 작업 플로어). 지금은 디렉토리·네이밍만 분리.

## 진행 (2026-07-04)
- [x] 패키지 이름 확정: **`warehouse_localization_sim_01`** — 생성 순서 넘버링 접미사(`_01`, 이후 `_02`…)로 제작 흐름 파악
- [x] `worlds/warehouse_open.world` 작성 (외벽 4면 + 기둥 8개 + 랙 4개, 전부 static, 인라인 SDF)
- [x] `launch/warehouse_world.launch.py` 작성 (gazebo + 월드 + waffle 스폰 @ (-24,-24))
- [x] colcon 빌드 성공 + `gz sdf --check` → "Check complete" (문법 유효)
- [ ] **GUI 육안 확인 대기** (VNC에서 launch 실행) ← 다음
- [ ] 로봇을 중앙 core로 주행시켜 **LiDAR 스캔이 실제로 비는지** 확인

## LiDAR 12m 상향 (2026-07-04 완료)
- 방식: **커스텀 waffle 모델 복제** (스폰 인자로는 센서 range 변경 불가).
- `models/warehouse_waffle_lidar12/` 에 원본 waffle `model.sdf` 복사 후 라이다 `<max>3.5</max>`→`<max>12.0</max>` 만 변경. 메시는 `model://turtlebot3_common` 참조 그대로.
- `launch/warehouse_world.launch.py` 가 이 커스텀 모델을 스폰하도록 수정.
- CMake `models/` 설치 추가. colcon 빌드 + `gz sdf --check` 통과.
- ✅ **런타임 확인**: 재시작 후 `/scan` **range_max=12.0 확인**. 구석(-24,-24)에서 360빔 중 215빔이 벽 감지(5.5~11.9m).
- 중앙 core 스캔 비움은 **RViz로 직접 관찰**하기로 (아래). ※ 텍스트 자동주행 시도는 실패(조잡한 go-to-goal 컨트롤러가 벽 충돌+제자리 회전 유발) → 폐기.

## RViz 시각화 추가 (2026-07-04)
- `config/warehouse.rviz`: Grid + TF + **LaserScan(/scan, best_effort, 빨간 점)** + RobotModel + Odometry. Fixed frame=odom.
- `launch/display.launch.py`: `warehouse_world.launch.py` + RViz 통합 실행.
- 사용: `ros2 launch warehouse_localization_sim_01 display.launch.py` → 주행하며 중앙에서 스캔 점이 사라지는지 관찰.

## 자동 주행 데모 + featureless core 실증 (2026-07-04)
- `scripts/auto_drive_demo.py` (`ros2 run warehouse_localization_sim_01 auto_drive_demo.py`):
  중앙 ↔ 특징(랙/기둥) 근처를 자동 순회. 부드러운 비례 제어 + LiDAR 전방 안전정지로 **제자리 회전/벽 충돌 없음**.
- **핵심 발견**: 이 waffle의 diff_drive는 odom을 **스폰 world 좌표에서 시작해 적산**(기본 ENCODER, `<odometry_source>` 미지정).
  즉 `odom.position ≈ world`(초기 -24,-24)라 웨이포인트를 world 좌표 그대로 목표로 씀. (드리프트는 존재 → 우리 문제에 적합. 단 sim 오도메트리가 너무 정확하면 P4 노이즈 주입 필요.)
- **✅ 실증 결과**: 헤드리스 테스트에서 로봇이 중앙으로 갈수록 **스캔 유효빔 215(구석) → ~14(개활지)로 붕괴**.
  "특징 없는 개활지에서 LiDAR가 아무것도 못 봄"이 수치로 확인됨 = M2 목표 달성.
- 알려진 사소한 이슈: 개활지에서 간헐적으로 전방 0.1m 스푸리어스 리딩 → 순간 안전회전 유발(주행엔 지장 없음). 추후 필요시 range 필터 보강.

## 맵 전략(P2) — 결정·완료 (2026-07-04)
- **결정: SLAM 대신 "2D 라이다 + ground-truth 위치" 방식.** 개활지는 SLAM에게도 어려워(같은 특징 부재)
  지도가 뒤틀림 → 비교 실험의 confound. 시뮬레이션은 ground-truth를 공짜로 주므로, 라이다 스캔을
  **진짜 위치에 누적**하면 드리프트 0의 정확한 기준 지도가 나옴. (M4 평가용 ground-truth도 동시 확보)
- 구현: 로봇에 `libgazebo_ros_p3d`(→ `/ground_truth`) 추가 + `scripts/map_builder.py`(빔 ray-casting 누적)
  + `auto_drive_demo.py route:=perimeter`(외벽·기둥 훑기).
- 산출: `maps/warehouse/warehouse_map.{pgm,yaml}` (1280x1280 @0.05m). 외벽 4면 + 기둥 8개 + 랙 반영,
  중앙 featureless core 일부 미관측(특징 없어 무방).

## 미결/다음 결정
- [ ] 로봇 경로·시작/목표점(P5) — 검증 시나리오
- [ ] (선택) 맵 중앙 미관측 영역 free 채우기 (nav2 경로계획 필요 시)
