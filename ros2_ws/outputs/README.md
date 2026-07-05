# outputs/ — 생성물 전용 폴더 (git 제외)

시각화·결과 도출물을 모아두는 폴더. **이 README 외 내용은 git에 올리지 않는다**(`.gitignore`).
모두 코드/스크립트로 재생성 가능하므로 저장소엔 코드만 두고, 산출물은 여기에 로컬 보관.

호스트에서도 바로 보임(`ros2_ws`가 컨테이너에 마운트됨 → `ros2_ws/outputs/`).

## 폴더 구조 (단계별로 분리)
| 폴더 | 내용 |
|------|------|
| `baseline/` | **M3 Baseline (AMCL only)** — C1~C5 결과·플롯·개요 그림 |
| `ekf/` | **M5 +EKF** — C1~C5 를 N(노이즈만)·E(노이즈+EKF) 두 구성으로. `Cx_{noise,ekf}.{csv,summary.json,plot.png}` + `ekf_compare_{bars,curves}.png`(baseline 대비 3-way) |
| (추후) `landmark/` | M6 +랜드마크 보정 결과 |

## baseline/ 안에 무엇이 들어오나
| 파일 | 생성 |
|------|------|
| `Cx_baseline.csv` | metrics_recorder (per-timestep 원자료) |
| `Cx_baseline.summary.json` | summarize (per-run 지표) |
| `Cx_baseline.plot.png` | plot_metrics (3패널: 오차·공분산·궤적) |
| `scenarios_overview.png` | plot_scenarios (맵+경로) |
| `failure_overview.png` | plot_scenarios (GT vs AMCL) |

## 재생성
```bash
# C1~C5 배치 (결과 CSV/summary/plot 이 baseline 폴더로)
bash <install>/run_all_baseline.sh /home/ubuntu/ros2_ws/outputs/baseline
# 개요 그림
python3 <install>/plot_scenarios.py /home/ubuntu/ros2_ws/outputs/baseline <map.pgm> <map.yaml>
```
> 맵 이미지(`warehouse_map.pgm`)는 launch 가 참조하므로 패키지(`sim_01/maps/warehouse/`)에 두되 git 제외. 재생성: `map_builder.py` + `clean_map.py`.
