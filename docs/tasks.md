# 백로그 (Tasks)

추가할 기능, 버그 수정, 유지보수 내역을 추적합니다.

## TODO

- [ ] 데이터 반환 스키마 최적화: `parser.first_text` 키 셋이 `processor.py`, `spatial.py`와 일부 중복 — 공통 키 사전을 만들어 한 곳에서 관리할지 검토.
- [ ] 신규 파일데이터 endpoint 카탈로그 등록 (data.go.kr 산림 관련 신규 dataset 모니터링).
- [ ] `tests/fixtures/`에 missing-case fixture 보강 (resultCode "03" no-data, "99" server, OpenAPI_ServiceResponse envelope 등).
- [ ] `replay.assert_case`의 `count` 모드 응답이 dict가 아닌 list일 때의 동작을 fixture로 명시.
- [ ] `_http._decode_payload`가 fallback으로 XML을 파싱한 경우 trace에 표시되도록 (디버그 UI에서 확인 가능하도록) 보강.
- [ ] forest.go.kr 다운로드 흐름의 popup/history 호출 실패 시 진단 메시지 강화 (현재는 generic ForestRequestError).
- [ ] `_convert.extract_address`가 주소 문자열만 다루므로 도로명/지번 분리·BJD_CD 보조 정보가 필요한 시나리오 대응 검토.
- [ ] `CHANGELOG.md` 도입 시점 결정 (0.2.0 파괴적 변경을 계기로).

## DONE

- [x] (2026-05-27) `python-kraddr-base` 의존성 완전 제거 및 좌표·주소 평탄화 (ADR-008). `__version__` 0.2.0.
- [x] (2026-05-24) `python-kraddr-geo` 방법론 도입 — `SKILL.md` 구조 표준화, `docs/decisions.md` ADR 표준화.
- [x] (2026-05-24) `src/krforest` 전체 코드 리뷰 및 안전한 개선 반영 (죽은 코드 제거, 폴백 가독성, 지수 백오프, 타입 표기 단순화).
- [x] 기본 테스트 및 CI 파이프라인 설정 (pytest/ruff/mypy strict).
- [x] 문서 한글 작성 원칙 반영 (AGENTS.md / SKILL.md / docs/*).
