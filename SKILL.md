---
name: python-krforest-api
description: 산림청 및 data.go.kr 산림 관련 여행/안전 비공식 Python 클라이언트 작업 가이드
---

# SKILL.md

이 문서는 `python-krforest-api` 개발에 참여하는 에이전트(Codex/AI)가 지켜야 할 상세 지침입니다.

## 1. 우선순위
1. 사용자 요청
2. `AGENTS.md` 및 `SKILL.md`
3. `docs/forest-api.md`, `docs/decisions.md`
4. `README.md`
5. 기존 코드와 테스트 패턴
6. 최소 범위의 되돌리기 쉬운 변경

## 2. 프로젝트 기준
- `python-krforest-api`는 산림청 및 data.go.kr 산림 관련 공개 데이터 중 **여행과 안전에 직접 관련된 API/파일데이터**만 다루는 비공식 Python 클라이언트다.
- 넓은 생물 표본, 임업경제, 법령해석, 사업자 등록, 행정 통계 데이터는 기본 범위에서 제외한다.
- Python 지원 기준은 `pyproject.toml`의 `requires-python`을 따른다.
- HTTP 의존성은 `httpx`와 `asyncio`, 공개 반환 모델은 `pydantic` 기반 frozen 모델을 사용한다.
- 기본 단위 테스트는 네트워크를 호출하지 않아야 한다.

## 3. 절대 규칙 (DO NOT)
- **얇은 래퍼(Thin Wrapper) 생성 금지**: 외부 API 관련 작업은 다른 구현보다 먼저 wrapper/adapter/gateway 지양 원칙을 확인하고 직접 반영한다. 장기 호환 alias나 임시 facade를 만들지 않는다.
- **API 키 평문 커밋 금지**: 서비스키는 `DATA_GO_KR_SERVICE_KEY` 환경변수 하나로만 로컬에서 사용한다. 로그, 픽스처, 예외 메시지, repr 등에 키를 남기지 않는다.
- **다중 키 fallback 금지**: `KRFOREST_SERVICE_KEY` 등 여러 서비스키 환경변수를 허용하지 않는다.
- **응답 body 확인 누락 금지**: HTTP 200이어도 body-level `resultCode`를 반드시 확인해야 한다.
- **절대 경로 사용 금지**: 문서에서 파일 위치를 쓸 때는 프로젝트 루트 기준 상대 경로만 쓴다.

## 4. 모듈 소유권
- `src/krforest/client.py`: 사용자 진입점, 여행/안전/파일데이터 namespace, pagination.
- `src/krforest/_http.py`: transport, 응답 envelope 정규화, 오류 매핑, 키 마스킹.
- `src/krforest/_convert.py`: 응답 경계에서 쓰는 작은 변환 helper.
- `src/krforest/catalog.py`: 구현 대상 API와 파일데이터의 curated catalog.
- `src/krforest/models.py`: 공개 Pydantic 모델.
- `src/krforest/exceptions.py`: 예외 계층.
- `tests/`: 네트워크 없는 단위 테스트와 opt-in live 테스트.

## 5. 구현 규칙
- 불필요한 thin wrapper나 호환 계층을 새로 만들지 않는다. `pykma`, `pyopinet`, `pykex` 등 유사 라이브러리에 검증된 구현이 있으면 구조와 동작을 직접 가져와 맞춘다.
- 새로운 예외는 `ForestApiError` 하위로 만들고 `failure_kind`를 채운다.
- 응답 parser는 원본 값을 `raw`에 보존한다.
- data.go.kr 파일데이터는 상세 페이지의 JSON-LD `contentUrl`을 우선 사용한다.
- 페이지네이션은 `Page.total_count`, `Page.page_no`, `Page.num_of_rows`를 기준으로 판단한다.

## 6. 로컬 환경 반복 이슈
- `rg` 실행 권한 문제 발생 시 PowerShell 기본 명령(`Select-String`)으로 우회한다.
- 파일 목록은 `Get-ChildItem -Recurse -File`을 사용한다.
- PowerShell 출력 시 UTF-8 한글 깨짐에 주의하고, 필요한 경우 `Path.read_text(encoding="utf-8")`로 확인한다.
- `python -m pytest`가 capture 정리 중 오류를 내면 `python -m pytest -s tests`로 실행한다.

## 7. 문서 관리 규칙
- 작업 후 `docs/journal.md`에 작업 항목을 기록하고, `docs/resume.md`의 진척도를 갱신한다.
- 의사결정이 있었다면 `docs/decisions.md`에 ADR을 추가한다.
- 사용자 가시 변경이면 `CHANGELOG.md` 또는 `README.md`를 갱신한다.

## 8. 테스트 및 검증
- 네트워크 요청/응답은 네트워크 없는 단위 테스트로 철저히 분리/검증한다.
- live 검증은 `$env:DATA_GO_KR_SERVICE_KEY = "..."`로 명시적 실행 시에만 수행한다. (`python -m pytest -m live`)
- 제출 전 반드시 `python -m pytest`, `python -m ruff check .`, `python -m mypy src/krforest`를 통과해야 한다.
