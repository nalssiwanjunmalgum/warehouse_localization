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

## C1~C5 시나리오 정식 baseline (2026-07-04, `run_all_baseline.sh`)
결과: `results/Cx_baseline.{csv,summary.json,plot.png}`. 캡처 규격: [CAPTURE_SPEC.md](./CAPTURE_SPEC.md).

| 시나리오 | ATE | 최대오차 | 최종오차 | 최대공분산 | RPE(1s) | 재수렴 |
|---------|-----|---------|---------|-----------|---------|--------|
| C1 대각 횡단 | 34.2m | 60.4m | 60.1m | 17.1m | 2.24 | 없음 |
| C2 오프셋 슬라이스 | 23.9m | 58.7m | 32.7m | 24.6m | 11.3 | 없음 |
| C3 폐루프 | 32.4m | 59.1m | 35.3m | 24.9m | 4.72 | 196.8s |
| C4 core 종착 | **2.4m** | 3.1m | 2.7m | 9.7m | 0.34 | 없음 |
| C5 지그재그 | 27.0m | 62.0m | 45.3m | 21.6m | 10.8 | 없음 |

**해석**:
- **개활지 횡단(C1·C2·C3·C5)**: catastrophic 실패(ATE 24~34m). core 통과 중 AMCL 로스트 +
  **perceptual aliasing**(똑같은 기둥들에 오매칭)으로 회복 불가.
- **core 정지(C4)**: position 오차 2.4m로 온건하나 공분산 9.7m로 큼 → "평균은 우연히 가깝지만
  확신 없음"의 다른 실패 유형(짧은 경로라 aliasing 점프 미발생).
- C2·C5 RPE 높음(≈11) = 프레임간 aliasing 점프 잦음. C3 는 폐루프 복귀 시 1회 재수렴 후 재발산.
- → **"개활 창고에서 AMCL이 길을 잃고 반복 기둥 탓에 회복도 못 한다"**는 문제 제기가 정량 성립.
  제안 방식(고유 반사판)은 aliasing 을 없애 이를 해결할 것.

## 실행 방법 (헤드리스 배치)
```bash
# 단일 시나리오
bash <설치경로>/run_scenario.sh C1 c1 -24 -24 1.571 170 /home/ubuntu/results
# 전체 C1~C5
bash <설치경로>/run_all_baseline.sh /home/ubuntu/results
```
시나리오 파라미터(init/route/maxtime)는 `run_all_baseline.sh` 참조. 경로는 `auto_drive_demo.py` ROUTES(c1~c5).

## 한계 / 다음
- 단일 run 이라 실행 간 편차 큼(파티클 필터 확률성) → 정식 비교 땐 반복 평균(P6).
- 현재 실패는 **feature 부재 + aliasing** 주도(odom 노이즈 없이도 성립). P4 노이즈는 드리프트 성분 추가용(선택).
- 매핑 기준 지도 중앙 미관측 영역은 무방(featureless core).
- [ ] M5(EKF) / M6(반사판)에서 동일 시나리오·지표로 비교 → 개선 정량화.
- 참고: matplotlib 은 numpy 2.x 호환 위해 pip 업그레이드(Dockerfile 반영).
