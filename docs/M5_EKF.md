# M5 — +EKF 센서 융합 (④ 노이즈 주입 포함)

> 3단계 비교 실험의 **2단계: 완화(mitigation)**.
> 바퀴 오도메트리에 드리프트를 주입(④)하고, `robot_localization` EKF로 오도메트리+IMU를 융합해
> **드리프트가 얼마나 늦춰지는지**를 정량화한다. 근본 해결(랜드마크, M6)이 아니라 "버티는 시간 늘리기".

관련: [M3_ANALYSIS.md](M3_ANALYSIS.md)(baseline) · CLAUDE.md §3(3단계 전략), §8-④(노이즈), §8-⑦(가설)

---

## 0. 왜 이 단계가 필요한가 — 그리고 왜 ④ 노이즈가 선행인가

baseline(M3)의 실패(ATE 24~34m)는 **오도메트리 드리프트가 아니라 AMCL의 perceptual aliasing**에서 온다.
즉 지금 시뮬 오도메트리는 **거의 완벽**(diff_drive 플러그인, 바퀴 슬립 0)해서, EKF를 얹어도 **보정할 대상이 없다.**

→ EKF의 "완화" 효과를 보이려면 먼저 **오도메트리에 현실적인 드리프트를 만들어야** 한다(④).
그래야 "드리프트가 있다 → EKF가 IMU로 헤딩을 잡아 드리프트를 줄인다"는 인과가 성립한다.

**핵심 통찰 (TF vs 토픽):**
AMCL의 모션 모델은 `/odom` **토픽이 아니라 `odom → base_footprint` TF**를 읽어 추측항법을 한다.
따라서 노이즈를 `/odom` 토픽에만 실으면 AMCL엔 아무 영향이 없다. **노이즈는 반드시 TF에 실려야 한다.**
그러려면 diff_drive 플러그인의 TF 발행을 끄고(그 자리를) 다른 노드/EKF가 채워야 한다.

---

## 1. 아키텍처

### 현재 (baseline)
```
map --(AMCL)--> odom --(diff_drive 플러그인, 완벽)--> base_footprint --> base_link --> 센서
       ^                                                    ^
    /scan 정합                                     추측항법(perfect) — 드리프트 없음
```
- `/odom`(diff_drive): 사실상 ground-truth 수준. TF `odom→base_footprint`도 diff_drive가 발행.

### M5 — 두 구성(config)을 같은 노이즈로 비교
diff_drive의 **`publish_odom_tf=false`** 로 바꾼 모델 변형(`warehouse_waffle_ekf`)을 쓴다.
diff_drive는 여전히 `/odom`(깨끗한 바퀴 운동학) 토픽만 낸다 → 이게 노이즈 주입기의 입력.

**(N) 노이즈만 (EKF 없음)** — "baseline + 드리프트"
```
map --(AMCL)--> odom --(noise_injector, TF)--> base_footprint
                         └ /odom(clean) 적분 + 오차 주입 → 드리프트하는 추측항법 TF
```

**(E) 노이즈 + EKF** — M5의 해법
```
map --(AMCL)--> odom --(EKF, TF)--> base_footprint
   noise_injector: /odom → /odom_noisy(토픽만, TF 없음)
   EKF(robot_localization): /odom_noisy(속도) + /imu(절대 yaw + 각속도) 융합
                            → odom→base_footprint TF + /odometry/filtered
```
IMU의 정확한 헤딩이 바퀴 헤딩 드리프트를 잡아준다 → (N)보다 드리프트 완화.

> AMCL은 두 구성 모두에서 그대로 돈다. EKF는 **AMCL을 대체하지 않고**, AMCL이 쓰는
> `odom→base` 추측항법을 개선할 뿐. 최종 위치추정 출력은 여전히 AMCL(`/amcl_pose`).
> → 지표 기록기(metrics_recorder)·평가 파이프라인은 baseline과 **동일하게 재사용**.

---

## 2. ④ 노이즈 모델 (noise_injector)

깨끗한 `/odom`의 속도(v, ω)를 읽어 **오차를 실은 속도**를 적분, 드리프트하는 포즈를 만든다.

| 성분 | 수식 | 의미 | EKF가 잡나? |
|------|------|------|-------------|
| 병진 스케일 바이어스 | `v' = v·(1+k_v)` | 바퀴 지름 오차 등 계통 오차 | 부분적 |
| 병진 랜덤 | `+ N(0, σ_v·|v|)` | 노면 슬립 랜덤 | 아니(속도 융합으로 평활만) |
| **회전 바이어스** ★ | `ω' = ω·(1+k_ω) + b_ω` | 좌우 바퀴 미세 불일치 → **헤딩이 서서히 틀어짐** | **예 (IMU 절대 yaw)** |
| 회전 랜덤 | `+ N(0, σ_ω·|ω| + σ_ω0)` | 회전 슬립 랜덤 | 부분적 |

- **회전 바이어스 `b_ω`가 킬러**다. 헤딩이 느리게 돌아가면 추측항법 경로가 통째로 휘어 ATE가 급증.
  IMU는 헤딩(각속도)을 정확히 재므로, EKF가 이 바이어스를 상쇄 → **(E)에서 ATE가 크게 준다.** = EKF의 존재 이유를 명확히 드러내는 설계.
- 적분: `θ += ω'·dt; x += v'·cos θ·dt; y += v'·sin θ·dt`. 결과를 `/odom_noisy`(+구성 N에선 TF)로.

**초기 파라미터(튜닝 대상):** `k_v=0.02, σ_v=0.02, k_ω=0.03, b_ω=0.02 rad/s, σ_ω=0.02, σ_ω0=0.005`.
드리프트가 **눈에 보이되(수 m/분) 비현실적으로 크지 않게** 튜닝한다(작업 8).

---

## 3. EKF 설정 (robot_localization, 2D)

- `two_d_mode: true`, `world_frame: odom`, `odom_frame: odom`, `base_link_frame: base_footprint`, `publish_tf: true`
- `odom0: /odom_noisy` → 융합 `[vx, vyaw]`(**속도만**; 드리프트하는 절대 x,y,yaw를 융합하면 드리프트 재주입)
- `imu0: /imu` → 융합 `[yaw, vyaw]`(**절대 yaw** = 헤딩 앵커 + 각속도). `imu0_differential:false`, `imu0_remove_gravitational_acceleration:true`
- 결과: `odom→base_footprint` TF(드리프트 완화됨) + `/odometry/filtered`.

> 왜 속도만 융합? 바퀴 오도메트리의 절대 위치는 이미 드리프트했으니, 그 절대값을 믿으면 안 된다.
> 속도(증분)만 쓰고 헤딩은 IMU 절대값으로 앵커 → 드리프트의 주원인(헤딩)을 IMU가 지속 교정.

---

## 4. 실험 프로토콜 & 가설 (⑦ — 숫자를 먼저)

- **통제 변수**: 동일 월드/맵/시나리오(C1~C5)/시작포즈/노이즈 파라미터. **오직 EKF on/off만** 변경.
- **비교**: 각 시나리오마다 (N) noise-only vs (E) noise+EKF. baseline(M3, 무노이즈)은 참조로 병기.
- **지표**: baseline과 동일 — ATE(RMS), RPE, drift_rate, cov_major, (신규) 헤딩오차.
- **결과 저장**: `ros2_ws/outputs/ekf/` (git 제외, baseline과 동일 규칙).

**가설 (실험 전 선언):**
1. (N) noise-only 는 baseline보다 ATE가 **더 크다**(aliasing + 추측항법 드리프트 중첩).
2. (E) noise+EKF 는 (N) 대비 ATE가 **뚜렷이 감소**(특히 헤딩오차·drift_rate). 목표: **drift_rate 최소 30%↓**.
3. 그러나 (E)도 **aliasing은 못 고쳐** 중앙 core에서 여전히 절대위치는 못 잡는다 → **완화이지 해결 아님**.
   = M6(랜드마크)의 필요성으로 자연스럽게 연결.

---

## 5. 구성 파일 / 산출물 (예정)

| 항목 | 위치 |
|------|------|
| EKF 모델 변형 | `warehouse_localization_sim_01/models/warehouse_waffle_ekf/` |
| 노이즈 주입기 | `warehouse_localization_ekf_03/scripts/noise_injector.py` |
| EKF 파라미터 | `warehouse_localization_ekf_03/config/ekf.yaml` |
| 런치(use_ekf 인자) | `warehouse_localization_ekf_03/launch/ekf.launch.py` |
| 실행 스크립트 | `warehouse_localization_ekf_03/scripts/run_all_ekf.sh` |
| 결과 | `ros2_ws/outputs/ekf/` |

> 지표 기록·요약·플롯은 `warehouse_localization_baseline_02`의 스크립트를 재사용(출력만 EKF 폴더로).
