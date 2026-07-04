# M3 — Baseline (AMCL) 로컬라이제이션 & 지표

> 목적(문제 제기): 개활 창고에서 **AMCL 단독**으로 로컬라이제이션 시 **드리프트/공분산 폭발**을
> 재현·시각화하고, ground-truth 대비 오차를 수치로 남긴다. 이후 M5/M6와 동일 지표로 비교할 기준선.
> 패키지: `warehouse_localization_baseline_02`.

## 구성
- `config/amcl.yaml` — AMCL(likelihood_field, laser_max_range 12m) + lifecycle 파라미터. 초기포즈 기본 (-24,-24,0)=C1.
- `launch/localization.launch.py` — map_server(창고 맵) + amcl + lifecycle_manager.
- `launch/baseline.launch.py` — sim + localization + RViz 통합.
- `config/baseline.rviz` — Map + LaserScan(빨강) + **AMCL pose+공분산 타원(주황)** + Ground truth(초록) + RobotModel. Fixed frame=map.
- `scripts/metrics_recorder.py` — `/amcl_pose` ↔ `/ground_truth` 비교 → per-timestep CSV.
- `scripts/plot_metrics.py` — CSV → 3패널 플롯(오차·공분산·궤적).

## 실행
```bash
# A) 통합 실행 (VNC): sim + AMCL + RViz
ros2 launch warehouse_localization_baseline_02 baseline.launch.py
# B) 주행 (별도 터미널)
ros2 run warehouse_localization_sim_01 auto_drive_demo.py --ros-args -p route:=demo
# C) 지표 기록 (별도 터미널) — Ctrl+C 시 CSV 저장 + ATE 요약
ros2 run warehouse_localization_baseline_02 metrics_recorder.py --ros-args -p out_csv:=/tmp/m3.csv
# D) 플롯
python3 <plot_metrics.py 경로> /tmp/m3.csv /tmp/m3.png
```
RViz 관찰: 초록 화살표(진짜) vs 빨강 화살표+주황 타원(AMCL). 중앙 개활지로 갈수록 **타원이 커지고 추정이 진짜에서 벗어남**.

## 시각화 & 수치 지표 (P5/M4 지표에 대응)
- **시각화**: (RViz) 공분산 타원 폭발 + est/GT 간극 + 스캔 소멸 / (플롯) 오차·공분산 vs 시간, 궤적 오버레이.
- **per-timestep**: 위치오차, 헤딩오차, 공분산(trace·장축), 가시빔 수.
- **per-run**: ATE(RMS), 최대오차, 평균 공분산. (RPE·goal오차·수렴시간은 시나리오별 확장.)

## 최초 검증 결과 (2026-07-04, demo 경로: 구석→중앙→복귀)
중앙 featureless core 진입 시 AMCL 붕괴가 수치·그림으로 확인됨:

| 시점 | 가시빔 | 위치오차 | 공분산 장축(1σ) |
|------|--------|----------|-----------------|
| 시작(특징 풍부) | ~214 | 0.05 m | 0.08 m |
| 개활지 진입 | 57→13 | 0.3→0.4 m | 0.5→0.8 m |
| **featureless core (빔 0)** | **0** | **~1.7 m** | **~3.0 m** 💥 |

- 전체: **ATE(RMS) 0.69 m, 최대 1.77 m, 평균 공분산 1.07 m**.
- 가시빔 ↔ 오차 역상관 뚜렷. 불확실성 약 **37배** 증가.

## 한계 / 다음
- 현재 sim odom ≈ ground-truth(노이즈 없음) → **평균 드리프트는 P4 노이즈 주입 후 더 커짐**.
  지금은 파티클 확산·공분산 폭발이 주된 실패 신호(그래도 오차 1.7m 발생).
- [ ] C1~C5 시나리오별 실행([P5_SCENARIOS.md](./P5_SCENARIOS.md))로 정식 baseline 수집.
- [ ] (선택) P4 노이즈 주입으로 드리프트 강화.
- 참고: matplotlib 은 numpy 2.x 호환 위해 pip 업그레이드 필요(Dockerfile 반영).
