# Resume

현재 `python-krforest-api` 프로젝트의 진척도와 이어서 할 작업을 기록합니다. 새로운 세션을 시작하거나 작업을 재개할 때 이 문서를 먼저 확인하세요.

## 🚀 현재 진척도
- `kraddr-geo`의 문서화 전략(Methodology)을 도입하여, 에이전트 작업 지침과 기록물을 분리/구조화함.
- `AGENTS.md`를 진입점으로 만들고 상세 내용을 `SKILL.md`로 분리.
- `src/krforest` 내부 코드 리뷰 및 타입 힌트/docstring 상태 점검 완료 (오류 없음, 높은 유지보수성 확인).
- 테스트 및 린트(MyPy, Ruff) 파이프라인 완비 및 성공.

## 📋 다음 해야 할 작업 (Next Task)
- 향후 신규 OpenAPI/파일데이터 endpoint 연동 시 `SKILL.md`와 `docs/tasks.md` 기반으로 순차 반영.
