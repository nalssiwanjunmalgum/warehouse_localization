# M6 분석 — +랜드마크(반사판) 절대보정 결과/해설 (해결 단계)

> 3단계 비교의 **3단계=해결**. 알려진 좌표의 반사판을 기하 검출·성좌매칭·삼각측량해 **절대 위치를 확정**,
> 개활지 perceptual aliasing 을 제거한다. C1~C5 를 baseline/EKF 와 동일 지표로 비교.
> 설계: [P3_SENSOR_LANDMARK](./P3_SENSOR_LANDMARK.md) · baseline [M3_ANALYSIS](./M3_ANALYSIS.md) · 완화 [M5_ANALYSIS](./M5_ANALYSIS.md)

---

## 0. 실험 구성 (baseline·EKF 에서 무엇이 바뀌었나)

**환경·시나리오는 M3/M5 와 동일**(60×60 개활 창고, 20m 격자 기둥, 중앙 core, 12m LiDAR, 노이즈 seed 고정).
바뀐 것: **① 반사판 16개(오버레이 월드)** + **② 절대보정 노드(landmark_localizer)** 로 위치추정 방식 자체가 바뀜.

### 구성 스택 (AMCL 없음)
```
반사판 오버레이 월드(warehouse_reflectors.world) + EKF 모델(diff_drive TF off)
  noise_injector(TF off) → /odom_noisy
  EKF(robot_localization) → odom→base_footprint TF           (M5 그대로 유지)
  landmark_localizer:  /scan → [검출] 가는 폴 클러스터
                              → [식별] 성좌 매칭(landmarks.yaml)
                              → [보정] ≥3 → Procrustes 삼각측량 → map→odom TF + /landmark_pose
```
- **AMCL·map_server 없음.** 절대 위치는 반사판 삼각측량이 직접 준다(실제 창고 AGV 방식). EKF 는
  **보정 사이 추측항법 안정화**로 유지.
- 최종 추정 = **`/landmark_pose`**. 지표 기록기를 `est_topic:=/landmark_pose` 로 → GT 와 비교(M3/M5 와 동일 파이프라인).

### 검출 방식 — intensity 대신 기하 (P3 결정)
`laser_retro` intensity 는 이 환경서 불가(CPU ray 무시, gpu_ray 헤드리스 불가) → **기하 검출**:
반사판을 **가는 폴(지름 0.16m)** 로 만들어 기둥(0.4m)·랙과 클러스터 **각폭**으로 구별. 식별은 **성좌**(상대 배치,
pose 불변)로 → 나쁜 prior(aliasing)에도 견고. 상세: [P3 §1·§5](./P3_SENSOR_LANDMARK.md).

### 공정성
반사판은 **오버레이 월드에만**, **occupancy 격자(AMCL 지도)에는 없음** → baseline/EKF 가 반사판 덕을 못 봄.

---

## 1. 지표 (M6 에서 무엇을 기대하나)

지표 정의는 [M3_ANALYSIS §1](./M3_ANALYSIS.md) 과 동일. M6 의 기대(가설 ⑦):
- **ATE**: 개활 전 구간에서 **수십 m → 수십 cm** (절대 위치 확정). = 해결의 핵심 증거.
- **cov_major**: 반사판 ≥3 보이는 구간에서 **~5cm 로 붕괴**(확신 회복). 반사판이 안 보이는 코너에선
  추측항법 불확실성으로 증가(정직하게 반영, 상한 15m).
- **drift_rate ≈ 0 · RPE 작음**: 절대보정이 드리프트를 주기적으로 리셋.
- **reconv_events**: 반사판 진입 시점에 즉시 재수렴(latency 거의 0).

---

## 2. 결과

### 전체 비교표 (ATE, m — 각 단일 런)

| SCN | Baseline(AMCL) | N(노이즈) | E(노이즈+EKF) | **Landmark(M6)** | 개선(vs Baseline) |
|-----|------|------|------|------|------|
| C1 대각 횡단 | 34.18 | 27.96 | 29.37 | **0.167** | **~205×** |
| C2 오프셋 | 23.95 | 31.92 | 27.65 | **0.157** | ~153× |
| C3 폐루프 | 32.39 | 35.35 | 33.13 | **0.315** | ~103× |
| C4 core 종착 | 2.39 | 10.54 | 2.27 | **0.127** | ~19× |
| C5 지그재그 | 26.98 | 17.18 | 31.44 | **0.165** | ~164× |

**Landmark 세부(모든 시나리오 sub-meter):** final_err 0.08~0.60m, RPE 0.07~0.09m(≈0),
drift_rate ≈ 0, cov_mean 0.76~5.86m(baseline 6.5~13.8 대비↓, 반사판 보이는 구간은 ~5cm).

![3단계 종합: ATE(로그축) + cov](../ros2_ws/outputs/landmark/final_compare_bars.png)

![시점별 위치오차: Baseline/EKF/Landmark](../ros2_ws/outputs/landmark/final_compare_curves.png)

**맵 위에서 보기 (GT vs Landmark 추정)** — 초록=진짜 경로, 빨강 점선=Landmark 추정. **전 시나리오에서
둘이 거의 완전히 겹친다**(baseline·EKF 의 폭주와 극명한 대비). = 반사판 절대보정으로 위치가 진실에 고정.

![C1~C5 GT(초록) vs Landmark(빨강) on map](../ros2_ws/outputs/landmark/failure_overview.png)

### 읽는 법
- **ATE 가 수십 m → 수십 cm** 로 전 시나리오 붕괴(로그축 그림에서 파랑만 바닥). aliasing 킬러였던
  C1·C3·C5(개활 횡단)도 **0.16~0.32m**. = **개활지 절대위치 문제 해결**.
- **cov_major 도 낮게**(C4 0.76m, C2 1.48m). C3(폐루프)가 5.86m 로 상대적으로 큼 = 루프 중 반사판
  저밀도 구간(코너)에서 추측항법 의존 → 그 구간 cov 상승(정직). 그래도 baseline(9.34)보다 낮음.
- **RPE·drift ≈ 0**: 절대보정이 매 스캔 드리프트를 리셋 → 국소 튐 없음.
- 곡선 그림: 파랑(Landmark)은 시종 바닥(~0.2m), 회색(Baseline)·초록(EKF)은 수십 m 로 폭주.

---

## 3. 메커니즘 — 왜 aliasing 을 해결하나

**M3·M5 가 못 한 것 = 절대 위치.** AMCL 은 똑같은 기둥에 오매칭(aliasing), EKF 는 상대 드리프트만 완화.
M6 는 **고유하고 절대적인 관측**을 추가해 이를 정면 해결:

1. **절대 관측**: 반사판은 **알려진 map 좌표**에 있다. 3개 이상의 (range,bearing)↔known-point 대응이면
   2D 절대 pose(x,y,θ)가 **과결정**된다 → Procrustes 최소자승으로 한 방에 확정. 드리프트든 aliasing 이든
   과거 오차와 무관하게 매 fix 가 절대 위치를 새로 찍는다.
2. **성좌로 aliasing 회피**: 기둥은 20m 격자로 똑같아 못 구별하지만, 반사판은 **불규칙 배치**(P3)라
   보이는 3~5개의 **상대 성좌가 국소적으로 고유**. → 반복 패턴에 속지 않음.
3. **연속 보정 + EKF**: 반사판 ≥3 구간에선 매 스캔 절대보정 → estimate 가 진실에 고정.
   반사판이 잠깐 끊겨도(코너) EKF 추측항법이 이어받아 다음 fix 까지 위치를 유지 → 연관 prior 도 안정.

**degrade 조건(정직)**: 반사판 <3 인 구역(벽 코너)에선 절대보정이 멈추고 추측항법에 의존 → 그 구간 cov 증가.
개활 핵심 구역은 ≥3 커버(P3 98%)라 문제 없음. 시작은 알려진 초기 pose 에서 부트스트랩.

---

## 4. 한계 & 결론 (3단계 완성)

**한계**
- **커버리지 의존**: 반사판 ≥3 보여야 절대보정. 코너·저밀도 구간은 추측항법(EKF)에 기대므로 반사판 밀도가
  개선 축(P3). 단일 런.
- **검출은 기하(폭)·식별은 성좌**: intensity(ID) 가 있으면 더 단순·견고했을 것(이 환경 한계로 기하 채택).
  시작은 알려진 pose 부트스트랩(kidnapped-robot 전역 재국소화는 범위 밖).

**결론 — 3단계 이야기 완성**
| 단계 | 방법 | 개활 ATE | 확신도(cov) | 결과 |
|------|------|---------|------------|------|
| M3 Baseline | AMCL | 24~34m | 폭발 | **문제**: aliasing 으로 절대위치 실패 |
| M5 +EKF | +오도/IMU 융합 | 여전히 큼 | 여전히 큼 | **완화**: 드리프트만, aliasing 못 고침 |
| **M6 +Landmark** | +반사판 삼각측량 | **~0.2m** | **붕괴(~5cm)** | **해결**: 절대위치 확정, aliasing 제거 |

feature 가 없거나 반복되는 개활 창고에서 **스캔·융합만으로는 부족하고, 알려진 인공 특징(반사판)의 절대
관측이 있어야 localization 이 성립**한다 — 이 프로젝트가 처음 제기한 문제에 대한 정량적 답. (실제 산업용
AGV 가 반사판을 쓰는 이유와 일치.)
