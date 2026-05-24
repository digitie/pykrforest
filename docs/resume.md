# Resume

현재 `python-krforest-api` 프로젝트의 진척도와 이어서 할 작업을 기록합니다. 새 세션이나 작업 재개 시 이 문서를 가장 먼저 확인하세요.

## 현재 진척도 (2026-05-24)

- `python-kraddr-geo`의 문서화 전략을 도입하여, 에이전트 가이드(`SKILL.md`), 결정 기록(`docs/decisions.md`), 작업 일지(`docs/journal.md`), 진척도(`docs/resume.md`), 백로그(`docs/tasks.md`)를 분리/구조화함.
- `AGENTS.md`를 진입점(읽어야 할 문서 목록)으로 축소하고 상세 규칙을 `SKILL.md`로 이관함.
- `docs/decisions.md`에 ADR 표준 형식과 ADR-001 ~ ADR-007을 정리함.
  - 키 정책(`DATA_GO_KR_SERVICE_KEY` 단일), 응답 envelope 검증, thin wrapper 금지, async-only, 변환 모듈 분리, 파일데이터 contentUrl 우선 사용.
- `src/krforest` 전체 코드 리뷰를 수행하고 다음을 반영함.
  - `spatial._member_by_suffix` 죽은 코드 제거.
  - `config.py` PEP 8 공백 보정.
  - `client._page`의 페이지·행수 폴백 표현 단순화 (ternary 중첩 제거).
  - `client.recreation_forest_reservations`에서 endpoint catalog가 이미 정의한 `response_format="xml"` 중복 인자 제거.
  - `_forest_go_request_with_retry`에 지수 백오프 추가 (0.5s → 1.0s).
  - `models.CallContext.provider` / `CatalogEntry.provider`의 `Provider | str` 중복 표기를 `str`로 단순화 (Literal는 str을 흡수).
- 단위 테스트(36 passed) / `ruff check` / `mypy strict` 모두 통과.

## 다음 해야 할 작업 (Next Task)

- [ ] PR 본문에 ADR 링크와 코드 리뷰 변경 요약을 정리해서 main에 머지 요청.
- [ ] (백로그) 데이터 반환 스키마 최적화 및 fixture 보강 — `docs/tasks.md` 참조.
- [ ] (백로그) 신규 파일데이터 endpoint 카탈로그 등록.
