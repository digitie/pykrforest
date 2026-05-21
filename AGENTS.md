# AGENTS.md

이 문서는 `python-krforest-api`에서 Codex/agent가 작업할 때 따라야 할 최소 지침입니다.
작업 방식은 `pykma`, `pyopinet`, `pykex`의 패턴을 따른다.

## 우선순위

1. 사용자 요청
2. 이 `AGENTS.md`
3. `docs/forest-api.md`
4. `README.md`
5. 기존 코드와 테스트 패턴
6. 최소 범위의 되돌리기 쉬운 변경

문서끼리 충돌하면 더 높은 우선순위 문서를 따르고, 필요하면 낮은 우선순위 문서를
같은 변경 안에서 갱신한다.

## 프로젝트 기준

- `python-krforest-api`는 산림청 및 data.go.kr 산림 관련 공개 데이터 중 여행과 안전에
  직접 관련된 API/파일데이터만 다루는 비공식 Python 클라이언트다.
- 넓은 생물 표본, 임업경제, 법령해석, 사업자 등록, 행정 통계 데이터는 기본
  범위에서 제외한다.
- Python 지원 기준은 `pyproject.toml`의 `requires-python`을 따른다.
- HTTP 의존성은 `httpx`와 `asyncio`, 공개 반환 모델은 `pydantic` 기반 frozen 모델을
  사용한다.
- 기본 단위 테스트는 네트워크를 호출하지 않아야 한다.

## 절대 규칙

- 외부 API 관련 작업은 다른 구현보다 먼저 wrapper/adapter/gateway 지양 원칙을 확인하고 문서/코드에 반영한 뒤 진행한다.
- downstream이 직접 사용할 안정된 public client, typed model, enum, helper를 제공한다.
- 단순 전달용 wrapper, 장기 호환 alias, 임시 facade를 만들지 않는다.
- TripMate나 `python-krtour-map`에서 필요한 endpoint, pagination, cursor, exception, raw payload 계약이 부족하면 이 저장소의 public API를 먼저 안정화한다.
- 다른 라이브러리에 검증된 구현이 있으면 wrapper로 감싸지 말고 라이선스와 출처를 확인한 뒤 현재 구조에 직접 반영한다.
- API 키를 커밋하지 않는다. data.go.kr 주소의 endpoint에 쓰는 서비스키는
  `DATA_GO_KR_SERVICE_KEY` 환경변수 하나로만 로컬에서 사용한다.
- `KRFOREST_SERVICE_KEY`, `KFS_SERVICE_KEY`, `FOREST_SERVICE_KEY`,
  `DATA_GO_SERVICE_KEY`, `TRIPMATE_DATA_GO_SERVICE_KEY` 같은 서비스키 환경변수
  fallback은 만들지 않는다.
- API 키를 로그, fixture, 예외 메시지, repr, 문서에 남기지 않는다.
- 문서에서 파일 위치를 쓸 때는 프로젝트 루트 기준 상대 경로만 쓴다.
  예: `src/krforest/client.py`, `docs/forest-api.md`.
- 로컬 절대 경로는 실행 결과 설명에 일시적으로 필요할 때만 쓰고, 저장소 문서에는
  남기지 않는다.
- Python 내부 문서, 즉 모듈/클래스/함수/메서드 docstring과 설명 주석은 한글로
  작성한다. 단, API 필드명, provider 원문, 코드 식별자는 원문을 보존한다.
- data.go.kr/forest.go.kr 응답은 단일 dict와 list 형태가 모두 올 수 있으므로 둘
  다 처리한다.
- HTTP 200이어도 body-level `resultCode`를 확인한다.
- `api.forest.go.kr` legacy endpoint와 `apis.data.go.kr` endpoint의 인증 파라미터
  이름 차이를 임의로 합치지 않는다.

## 모듈 소유권

- `src/krforest/client.py`: 사용자 진입점, 여행/안전/파일데이터 namespace, pagination.
- `src/krforest/_http.py`: transport, 응답 envelope 정규화, 오류 매핑, 키 마스킹.
- `src/krforest/_convert.py`: 응답 경계에서 쓰는 작은 변환 helper.
- `src/krforest/catalog.py`: 구현 대상 API와 파일데이터의 curated catalog.
- `src/krforest/models.py`: 공개 Pydantic 모델.
- `src/krforest/exceptions.py`: 예외 계층.
- `tests/`: 네트워크 없는 단위 테스트와 opt-in live 테스트.
- `docs/forest-api.md`: 구현 범위와 제외 범위의 기준 문서.
- `docs/development-notes.md`: 로컬 개발 환경, 반복 이슈, 명령 실행 주의사항.
- `docs/live-test-notes.md`: live test 키와 승인 상태 기록.

## 문서 규칙

- 사용자 사용법 변경은 `README.md`를 갱신한다.
- 구현 범위, 데이터셋, endpoint 변경은 `docs/forest-api.md`를 갱신한다.
- live test 동작이나 승인 상태가 바뀌면 `docs/live-test-notes.md`를 갱신한다.
- 로컬 개발 환경에서 반복되는 도구/인코딩 이슈는 `docs/development-notes.md`와
  이 파일을 함께 갱신한다.
- agent 작업 규칙이나 반복 실수 방지 규칙은 이 파일을 갱신한다.
- 문서의 파일 위치 정보는 항상 프로젝트 기준 상대 경로로 작성한다.
- 문서 예제의 API 키는 실제 값처럼 보이지 않는 placeholder만 사용한다.

## 로컬 환경 반복 이슈

- 이 환경에서는 `rg` 실행이 권한 문제로 실패할 수 있다. `rg`가 막히면 반복해서
  재시도하지 말고 PowerShell 기본 명령으로 우회한다.
- 파일 목록은 `Get-ChildItem -Recurse -File`, 파일명 필터는
  `Get-ChildItem -Recurse -File -Filter *.py`, 텍스트 검색은
  `Select-String -Path ... -Pattern ...`을 사용한다.
- 문서는 UTF-8로 저장되어 있어도 PowerShell 기본 출력 인코딩 때문에 한글이 깨져
  보일 수 있다. 문서가 깨졌다고 판단하기 전에 `Get-Content -Encoding utf8 <path>`로
  다시 읽는다.
- UTF-8 문서를 PowerShell로 쓰거나 변환해야 할 때는 `Set-Content -Encoding utf8`처럼
  인코딩을 명시한다. 단순 코드 수정은 가능하면 `apply_patch`를 사용한다.
- 한글 표시 검증이 필요하면 Python의 `Path.read_text(encoding="utf-8")`로 읽어
  실제 파일 내용과 터미널 표시 문제를 구분한다.
- 이 WSL/Windows 마운트 환경에서는 `python -m pytest`가 기본 `testpaths` 실행에서
  0개 테스트를 수집한 뒤 capture 정리 중 `FileNotFoundError`를 낼 수 있다. 이때는
  `python -m pytest -s tests`처럼 수집 대상을 명시해서 재실행한다.

## 구현 규칙

- 불필요한 thin wrapper나 호환 계층을 새로 만들지 않는다. `pykma`, `pyopinet`,
  `pykex` 등 유사 라이브러리에 이미 검증된 구현이 있으면 최소 수정 원칙과
  방향이 다르더라도 필요한 구조와 동작을 직접 적용해 프로젝트 간 일관성을 맞춘다.
- 다른 라이브러리의 구현을 가져올 때도 `python-krforest-api`의 여행/안전/파일데이터 범위를
  벗어나는 endpoint나 데이터셋은 함께 추가하지 않는다.
- 새 endpoint wrapper는 `catalog.py`에 metadata를 먼저 추가하고 `client.py`에서
  namespace 메서드를 제공한다.
- public method는 안정적인 의미가 있는 값을 typed 모델이나 raw mapping으로 일관되게
  반환한다. 아직 스키마가 안정적이지 않은 endpoint는 `RawRecord`를 유지한다.
- 응답 parser는 원본 값을 `raw`에 보존한다.
- 페이지네이션은 `Page.total_count`, `Page.page_no`, `Page.num_of_rows`를 기준으로
  판단한다.
- data.go.kr 파일데이터는 상세 페이지의 JSON-LD `contentUrl`을 우선 사용한다.
- `https://www.data.go.kr` 상세 페이지가 TLS 연결을 끊는 환경에서는
  `http://www.data.go.kr` fallback을 허용한다.
- 새로운 예외는 `ForestApiError` 하위로 만들고 `failure_kind`를 채운다.

## 테스트 기준

새 wrapper나 transport 변경에는 가능한 한 다음 테스트를 포함한다.

- 요청 URL과 query parameter 이름.
- 단일 dict와 list 응답 정규화.
- body-level API 오류 매핑.
- HTTP 인증/권한 오류에서 키가 가려지는지.
- 페이지네이션 메타데이터.
- 파일데이터 URL 발견 실패와 성공 경로.

기본 검증:

```bash
python -m compileall src/krforest tests
python -m pytest
python -m ruff check .
python -m mypy src/krforest
```

live 검증은 명시적으로 키를 넣을 때만 수행한다.

```powershell
$env:DATA_GO_KR_SERVICE_KEY = "..."
python -m pytest -m live
```

일부 `apis.data.go.kr/1400000` 산불/산사태 endpoint는 키별 활용신청 상태에 따라
HTTP 403을 반환할 수 있다. 이 경우 live test는 승인 필요 상태를 명확히 드러내는
`xfail`로 둔다.

## 커밋과 푸시

- `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.coverage`, `__pycache__`,
  가상환경, 로컬 `.env` 파일은 커밋하지 않는다.
- 변경은 되돌리기 쉬운 단위로 커밋한다.
- 푸시 전 `git status --short`로 의도하지 않은 파일을 확인한다.
- 원격 저장소에 기존 커밋이 있으면 먼저 fetch/rebase로 맞춘다. 강제 푸시는 사용자가
  명시적으로 요청한 경우에만 한다.
