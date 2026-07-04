# 창고(warehouse) 맵

`warehouse_open.world`(개활 창고)의 점유 격자 지도.

## 파일
- `warehouse_map.pgm` — 점유 격자 이미지 (1280x1280 @ 0.05 m/cell, 64x64m 커버)
- `warehouse_map.yaml` — 메타데이터 (origin [-32,-32,0], occupied_thresh 0.65, free_thresh 0.25)

## 생성 방식 (P2 맵 전략 결정: SLAM 대신 ground-truth 기반)
`scripts/map_builder.py` 로 **2D 라이다 스캔을 로봇의 진짜 위치(`/ground_truth`)에 누적**해 생성.
추정 위치가 아닌 ground-truth 를 쓰므로 **드리프트 0의 정확한 기준 지도**.
(개활지에서 SLAM이 뒤틀리는 문제를 회피 — 시뮬레이션의 ground-truth 강점 활용)

재생성:
```bash
# 터미널1: 헤드리스 sim + 로봇(ground_truth 포함)
# 터미널2: 지도 빌더
ros2 run warehouse_localization_sim_01 map_builder.py --ros-args \
  -p out_dir:=<이 폴더 절대경로> -p name:=warehouse_map
# 터미널3: 매핑 주행 (외벽·기둥 훑기)
ros2 run warehouse_localization_sim_01 auto_drive_demo.py --ros-args -p route:=perimeter
# 충분히 돌면 터미널2에서 Ctrl+C → 저장
```

## 특징
- 외벽 4면 + 구조 기둥 8개(20m 격자) + 적재 랙이 정확히 반영됨.
- **중앙 개활 구역 일부는 미관측(unknown)** — featureless core라 특징이 없어 매핑할 것도 없음.
  AMCL 실험엔 무방. nav2 경로계획에 필요하면 내부를 free로 채우는 후처리 가능.
