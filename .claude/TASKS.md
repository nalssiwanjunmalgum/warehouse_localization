# TASKS — warehouse_localization 작업 보드

이 파일은 프로젝트 작업을 **3단계**로 관리하는 칸반 보드입니다.
프로젝트 배경·목표는 루트 [CLAUDE.md](../CLAUDE.md) 참조.

## 관리 규칙
- 작업은 아래 3개 섹션을 **위→아래로 이동**시키며 관리한다: `📋 앞으로 진행` → `🔨 진행 중` → `✅ 처리됨`.
- 표기: `- [ ] (ID) 제목 — 한 줄 설명`. 완료 항목은 `- [x]`로.
- `ID` 규칙: 마일스톤은 `M#`, 기획 항목은 `P#`(CLAUDE.md §8의 ①~⑧에 대응), 그 외 잡작업은 `T#`.
- 상태가 바뀌면 이 파일과 CLAUDE.md §7(진행 현황)을 함께 갱신한다.
- `🔨 진행 중`에는 되도록 1~2개만 둔다(집중).

---

## 📋 앞으로 진행 (Backlog)

- [ ] (M1) 환경 검증 — 컨테이너 기동 후 Gazebo에서 TurtleBot3 기본 월드 주행 확인
- [ ] (P1) 월드 설계 — 기둥 20m 간격 + 적재물 가림 Gazebo `.world` 작성 (→ M2)
- [ ] (P2) 맵 전략 결정 — SLAM으로 뜰지 / 수동 제작할지
- [ ] (M3) Baseline(AMCL) — 맵 작성 후 AMCL 주행, 드리프트/수렴 실패 재현·시각화
- [ ] (P8/M4) 지표 파이프라인 — Ground Truth 취득 + rosbag 기록 + Python(ATE/RPE/공분산) 플롯
- [ ] (P5) 검증 시나리오 설계 — 경로 형태·시작·목표점·스트레스 구간 정의
- [ ] (P3) 센서·랜드마크 설계 — LiDAR range, 반사판 개수·좌표·배치
- [ ] (M5) +EKF 융합 — robot_localization으로 오도메트리+IMU 융합, 완화 정량화
- [ ] (M6) +랜드마크 보정 — 반사판 intensity 검출 + 삼각측량 절대위치 보정
- [ ] (M7) 종합 비교 — 3단계를 동일 지표로 비교하는 리포트/시각화
- [ ] (P7) 성공 기준/가설 정의 — 단계별 기대 오차를 실험 전 숫자로 명시

### 추후 상세화 (Deferred)
- [ ] (P4) 노이즈 주입 설계 — 바퀴 미끄러짐·IMU 바이어스로 드리프트 재현
- [ ] (P6) 비교 실험 프로토콜 — 통제 변수·seed 고정·반복 횟수

---

## 🔨 진행 중 (In Progress)

- [ ] (T1) 개발 환경 다운로드/빌드 대기 — Docker 이미지 pull & build 진행 중

---

## ✅ 처리됨 (Done)

- [x] (T0) 프로젝트 목표·구조 정리 및 CLAUDE.md 작성
- [x] (T0) Docker/devcontainer 기반 ROS2 Humble 환경 파일 구성 (Dockerfile, docker-compose.yml, .devcontainer)
