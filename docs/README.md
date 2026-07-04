# 문서 관리 (docs/)

이 디렉토리는 `warehouse_localization` 프로젝트의 **셋업 이력·트러블슈팅·의사결정**을 지속적으로 기록하는 공간입니다.
코드나 git 히스토리만으로는 알 수 없는 "왜 이렇게 했는지 / 무엇이 막혔고 어떻게 풀었는지"를 남기는 것이 목적입니다.

## 문서 목록

| 파일 | 내용 |
|------|------|
| [COMMANDS.md](./COMMANDS.md) | 자주 쓰는 실행 명령어 모음 (빌드·실행·점검·트러블슈팅) |
| [CONCEPTS.md](./CONCEPTS.md) | 도메인 개념·용어 정리 (LiDAR 스캔, TF/odom 등) |
| [SETUP_HISTORY.md](./SETUP_HISTORY.md) | Docker 빌드 · 실행 · 트러블슈팅 이력 로그 (날짜순, 계속 추가) |
| [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) | 미해결/재발 가능 이슈와 대처법 요약 |
| [M2_WORLD_DESIGN.md](./M2_WORLD_DESIGN.md) | M2 개활지 창고 월드 설계 결정·레이아웃 |

## 기록 방침

- **이력 로그**는 날짜별 항목으로 **위에서 아래로 계속 append** 합니다. 과거 항목은 지우지 않습니다.
- 각 항목에는 **증상 → 원인 → 조치 → 검증 상태**를 남깁니다.
- 아직 확정되지 않은 결론은 `⚠️ 검증 필요`로 명시하고, 나중에 확인되면 항목을 업데이트합니다.
- 재발하는 이슈는 [KNOWN_ISSUES.md](./KNOWN_ISSUES.md)에 요약해 빠르게 참조할 수 있게 합니다.
