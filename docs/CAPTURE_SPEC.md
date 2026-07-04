# 시나리오별 결과 캡처 규격 (baseline / proposed 공통)

> M3(baseline)·M5·M6(proposed)를 **공정 비교**하기 위해, 시나리오마다 무엇을·어느 순간에
> 이미지/수치로 남길지 통일한다. 시나리오 정의는 [P5_SCENARIOS.md](./P5_SCENARIOS.md).

## 공통 산출물 (모든 실행)
| 산출물 | 내용 | 생성 |
|--------|------|------|
| `Cx_<method>.csv` | per-timestep 원자료 (t·gt·est·pos_err·yaw_err·cov·가시빔) | metrics_recorder |
| `Cx_<method>.plot.png` | 3패널: 오차 vs 시간 / 공분산 vs 시간 / 궤적 오버레이 | plot_metrics |
| `Cx_<method>.summary.json` | per-run 수치 (ATE·RPE·max·loop·goal·reconv 등) | summarize |
| `Cx_<method>.snap.png` | RViz "결정적 순간" 스냅 (수동/선택) | 수동 |

`<method>` = `baseline` | `ekf` | `reflector`. 파일은 `results/` 에 저장.

## 시나리오별 핵심 지점 & 값
| 케이스 | 겨냥 실패모드 | 📸 이미지(순간/장면) | 🔢 핵심 수치 |
|--------|--------------|---------------------|-------------|
| **C1** 대각 횡단 | 지속 발산 | 중앙 관통 순간(공분산 최대) + 궤적 오버레이 | ATE, 최대오차, 최대 공분산, 개활구간 오차 증가율(m/m) |
| **C2** 오프셋 측면 | 간헐 관측 | 오차 vs 시간(톱니) + 가시빔 겹침 | 오차 진동 진폭, 재관측 회복 횟수, 평균오차 |
| **C3** 폐루프 | 루프 클로저 오차 | 궤적 오버레이(출발=도착 gap 강조) | 루프 클로저 오차 ‖est_end−gt_end‖, 누적 드리프트 |
| **C4** core 종착 | 정지 정확도 | 목표점 정지 순간(최종 pose+타원+GT) | goal 오차 ‖est_final−gt_final‖, 최종 공분산 |
| **C5** 지그재그 | 재수렴 시간 | 공분산 vs 시간(스파이크+회복 음영) | 재수렴 latency, 발산/재수렴 사이클 수 |

## "개선 여지" 3값 (baseline에서 확보 → proposed가 줄일 대상)
1. **보정 간 잔여 드리프트** — C1/C3 (baseline은 보정 없어 계속 증가)
2. **최대 불확실성(공분산 장축)** — C1/C4 (proposed는 반사판으로 억제)
3. **재수렴 latency** — C5 (proposed는 절대보정으로 즉시 회복)

## per-run 수치 정의 (summarize.py)
- **ATE** = RMS(pos_err)  ·  **max_err** = max(pos_err)  ·  **max_cov** = max(cov_major)
- **RPE** = 고정 구간 Δ 상대 이동 오차의 RMS (드리프트/구간)
- **final_err / goal_err** = 마지막 pos_err (C4 핵심)
- **loop_err** = ‖est_end − est_start‖ (C3 핵심; 시작=도착일 때)
- **drift_rate** = 개활구간 pos_err 선형 증가 기울기 (m/m 또는 m/s)
- **reconv** = cov_major 가 임계 상회 후 하회까지 걸린 시간들(C5 핵심)

## 시나리오 파라미터 (init/goal, 기둥 회피 오프셋 반영)
| 케이스 | init (x,y,yaw) | 경로(route) 요지 | 비고 |
|--------|----------------|------------------|------|
| C1 | (-24,-24, 45°) | →(0,0)→(24,24) | 대각, 기둥은 안전회피 |
| C2 | (-24, 8, -18°) | →(0,0)→(24,-8) | core 슬라이스 |
| C3 | (-22,-22, 45°) | →(0,0)→(22,22)→(0,0)→(-22,-22) | 폐루프(코어 2회 통과) |
| C4 | (-24, 0, 0°) | →(0,0) 에서 정지 | 최악 지점 종착 |
| C5 | (24,-24, 135°) | 지그재그 →(-18,18) | 관측 단절 반복 |
> P5 원안의 (-20,±20)·(0,-20) 등은 기둥 좌표라, 충돌 회피 위해 근처 개활점으로 오프셋함.
