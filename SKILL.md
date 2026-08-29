---
name: python-krforest-api
description: 산림청 및 data.go.kr 산림 관련 여행/안전 비공식 Python 클라이언트 작업 가이드
---

# SKILL — python-krforest-api 에이전트 매뉴얼

> 이 파일은 당신(AI 에이전트)이 작업을 시작하기 전 반드시 읽어야 한다.
> 1회만 읽으면 30분 이상의 시행착오를 줄일 수 있다.

## 1. 정체성

이 저장소(GitHub 이름 `python-krforest-api`, Python 패키지 `krforest`)는 산림청과 `data.go.kr`이 공개하는 **여행·안전 관련 산림 데이터**만 다루는 비공식 async Python 클라이언트다. 생물 표본, 임업경제, 법령해석, 사업자 등록, 행정 통계 데이터는 의도적으로 범위에서 제외한다.

응답 모델은 외부 도메인 패키지 의존 없이 **`latitude: float | None`, `longitude: float | None`, `address: str | None`** 같은 원시 타입만 노출한다. 이 패키지는 **얇은 래퍼(thin wrapper)를 만들지 않는다**. `pykma`, `pyopinet`, `pykex`처럼 같은 계열의 검증된 라이브러리 구조와 동작을 가져와 맞춘다.

### 식별자 매핑

| 항목 | 값 |
|------|----|
| GitHub 저장소 | `python-krforest-api` |
| Python import | `from krforest import ForestClient` |
| 환경변수 키 | `DATA_GO_KR_SERVICE_KEY` (유일) |
| 데이터 제공처 | `data.go.kr`, `forest.go.kr` |
| 의존 라이브러리 | `httpx`, `pydantic`, `pyproj`, `pyshp` |

## 2. 빠른 시작

```powershell
# 설치
pip install -e ".[dev]"

# 환경 변수 설정 (PowerShell)
$env:DATA_GO_KR_SERVICE_KEY = "..."

# 단위 테스트 (네트워크 호출 없음)
python -m pytest

# 실서버 호출 테스트
python -m pytest -m live

# 린트와 타입 검사
python -m ruff check .
python -m mypy src/krforest

# 디버그 UI
pip install -e ".[debug-ui]"
streamlit run examples/streamlit_debug_ui.py
```

## 3. 디렉토리 지도

```
src/krforest/
  client.py     — 사용자 진입점, 여행/안전/파일데이터 namespace, pagination
  config.py     — DATA_GO_KR_SERVICE_KEY 단일 로드, timeout/max_rps 정규화
  _http.py      — transport, 응답 envelope 정규화, 오류 매핑, 키 마스킹
  _convert.py   — 응답 경계의 작은 변환 helper
  _ratelimit.py — 비동기 토큰 버킷 (max_rps)
  catalog.py    — 구현 대상 OpenAPI와 파일데이터의 curated catalog
  models.py     — 공개 Pydantic 모델 (frozen)
  parser.py     — 원격 row → 공개 모델 변환 (단일 row 책임)
  processor.py  — 다중 파일데이터 조합 (휴양림 CSV join 등)
  spatial.py    — SHP/GeoJSON/GPX ZIP → 좌표·도형 DTO 변환 (pyproj 변환)
  replay.py     — 저장된 fixture 검증 (snapshot, required_fields, count, schema_only)
  debug.py      — DebugRun + save_fixture + jsonable + redact_sensitive
  exceptions.py — ForestApiError 계층 (failure_kind 포함)
tests/
  네트워크 없는 단위 테스트 + opt-in live 테스트 (-m live)
docs/
  resume.md / tasks.md / decisions.md / journal.md / forest-api.md ...
```

의존 방향은 **models → exceptions/_convert → parser/processor/spatial → _http → client → examples/streamlit_debug_ui.py**. 역방향 import는 만들지 않는다.

## 4. 절대 하지 말 것 (DO NOT)

1. **얇은 래퍼(Thin Wrapper) 생성 금지**: 외부 API 작업은 다른 구현보다 먼저 wrapper/adapter/gateway 지양 원칙을 확인하고 직접 반영한다. 장기 호환 alias나 임시 facade를 만들지 않는다. `pykma`, `pyopinet`, `pykex` 등 유사 라이브러리에 검증된 구현이 있으면 구조와 동작을 직접 가져와 맞춘다.
2. **다중 키 fallback 금지**: 서비스 키는 `DATA_GO_KR_SERVICE_KEY` **단일 환경변수**만 사용한다. `KRFOREST_SERVICE_KEY`처럼 별칭 환경변수를 추가하지 않는다.
3. **API 키 평문 노출 금지**: 로그, 픽스처, 예외 메시지, repr, `request_params`, `mask_params` 결과 어디에도 키가 남아서는 안 된다. `_convert.mask_params` / `public_params` / `redact_secret`을 거치지 않은 채 query를 출력하지 않는다.
4. **응답 body 확인 누락 금지**: HTTP 200이어도 body-level `resultCode`/`returnReasonCode`를 반드시 확인해야 한다. 정상 코드는 `""`, `"00"`, `"0000"`, `"NORMAL_CODE"`만 허용한다. `"03"`(no data)은 빈 `Page`로 정상 처리한다.
5. **절대 경로 사용 금지**: 문서에서 파일 위치를 쓸 때는 프로젝트 루트 기준 상대 경로만 쓴다.
6. **외부 도메인 패키지 의존 금지**: 좌표·주소를 위해 `python-kraddr-base` 같은 외부 도메인 패키지를 다시 도입하지 않는다. 좌표는 `latitude: float | None`, `longitude: float | None`, 주소는 `address: str | None`로 평탄하게 노출한다.
7. **동기 인터페이스 추가 금지**: `ForestClient`는 async-only다. 동기가 필요하면 호출자가 `asyncio.run`으로 감싼다.
8. **`response.json()` 결과를 dict로 단정 금지**: `_decode_payload`는 root가 dict인지 검증하고, 아니면 `ForestParseError`를 던진다. 새 endpoint에서도 같은 검증 경로를 유지한다.
9. **파일데이터 다운로드 URL 하드코드 회피**: data.go.kr 파일데이터는 상세 페이지의 JSON-LD `contentUrl`을 우선 사용한다. forest.go.kr 파일데이터는 popup → history → ZIP 흐름을 따른다(개인 사용 목적 코드 `dnldPrps=3`).
10. **공간 좌표 순서 혼동 금지**: 모델에는 `latitude`, `longitude` 두 필드로 따로 노출한다. GeoJSON `coordinates`는 표준대로 `[lon, lat]`을 유지한다. SHP의 EPSG:5179 등 투영좌표는 `_coordinate_transformer`로 WGS84로 변환한 뒤 노출한다.
11. **상위 모듈 import 역행 금지**: 위 디렉토리 지도의 의존 방향을 거꾸로 import하지 않는다. (예: `models.py`가 `client.py`를 import하면 안 됨)
12. **레코드 단위 책임 혼동 금지**: 단일 row → 모델 변환은 `parser.py`. 여러 파일·여러 row를 join해 단일 객체로 만드는 것은 `processor.py`. SHP/GeoJSON 등 공간 파일은 `spatial.py`. 새 변환을 추가할 때 이 경계를 지키고, `parser.py`에 join 로직을 두지 않는다.

## 5. 자주 묻는 작업

| 작업 | 시작 파일 |
|------|-----------|
| 새 OpenAPI endpoint 추가 | `catalog.py`에 `ApiEndpoint` 추가 → `parser.py`에 row → 모델 변환 → `client.py` namespace 메서드 |
| 새 파일데이터 추가 | `catalog.py`에 `FileDataset` 추가 → 필요시 `processor.py`/`spatial.py`에 변환 |
| 새 예외 타입 추가 | `exceptions.py`에 `ForestApiError` 하위 클래스 추가, `failure_kind` 부여 |
| 응답 envelope 차이 처리 | `_http.py`의 `_normalize_payload` / `_raise_result_code` |
| 응답에 좌표·주소 노출 | `_convert.extract_coordinate(row)`, `_convert.extract_address(row)` 헬퍼 사용. 모델은 `latitude`/`longitude`/`address` 평탄 필드 |
| 디버그 fixture 저장 | `await client.debug_endpoint(...)` → `save_fixture(...)` |
| replay 테스트 추가 | `tests/test_replay.py`, `tests/test_generated_fixtures.py` 참조 |
| 한도 안전한 동시 호출 | `_ratelimit.AsyncTokenBucket` (기본 5 RPS) |

## 6. 도메인 어휘

| 약어/용어 | 의미 |
|----------|------|
| 서비스키 / ServiceKey | data.go.kr 인증 키. `DATA_GO_KR_SERVICE_KEY` 환경변수에서 로드 |
| resultCode | data.go.kr OpenAPI body header의 결과 코드. `00`/`0000`이 정상, `03`은 데이터 없음 |
| returnReasonCode | data.go.kr `OpenAPI_ServiceResponse` envelope의 오류 코드 |
| failure_kind | `ForestApiError`의 분류 라벨 (`auth`/`rate_limit`/`request`/`server`/`parse`/`no_data`/`network`) |
| pageNo / numOfRows | 페이지네이션 파라미터. `Page.has_next_page`는 `page_no * num_of_rows < total_count` |
| dnldPrps | forest.go.kr 파일 다운로드 목적 코드. 개인 사용은 `3` |
| pblicDataId | forest.go.kr 파일데이터 식별자 (예: `PBD0000041`) |
| data_go_id | data.go.kr 파일/OpenAPI 식별자 (숫자, 예: `15084696`) |
| EPSG:5179 | 산림청 SHP가 자주 쓰는 GRS80 UTM-K 투영. WGS84(EPSG:4326)로 변환해 노출 |
| `DebugRun` | input/request/response/parsed/processed/trace/catalog/error를 담는 디버그 실행 결과 객체 |

## 7. 로컬 환경 반복 이슈

- `rg` 실행 권한 문제 발생 시 PowerShell `Select-String`으로 우회한다.
- 파일 목록은 `Get-ChildItem -Recurse -File`을 사용한다.
- git 상태 조회, 브랜치 생성, 커밋, push, PR 작업은 WSL `git` 대신 Windows Git(`C:\Program Files\Git\cmd\git.exe`)를 사용한다. 현재 worktree의 `.git` 파일이 Windows 경로를 가리켜 WSL `git`이 `not a git repository`로 실패할 수 있다.
- PowerShell 출력에서 한글이 깨질 때는 `Path.read_text(encoding="utf-8")`로 직접 확인한다.
- `python -m pytest`가 capture 정리 중 오류를 내면 `python -m pytest -s tests`로 실행한다.
- forest.go.kr 다운로드 흐름은 401/403 대신 HTML 응답을 줄 때가 있다. `_forest_go_request_with_retry`가 지수 백오프로 3회 재시도한다.

## 8. 테스트 및 검증

- **단위 테스트는 네트워크를 호출하지 않는다.** `tests/conftest.py`가 제공하는 fake transport를 사용한다.
- **live 테스트는 명시적 실행**이다. `$env:DATA_GO_KR_SERVICE_KEY = "..."`로 설정한 뒤 `python -m pytest -m live`로만 돈다.
- **fixture 기반 replay**: `tests/fixtures/<function>/<case>.json`을 `replay.assert_case`로 검증한다. 새 fixture는 `client.debug_endpoint(...)` + `save_fixture(...)`로 만든다.
- 제출 전 다음 셋이 모두 통과해야 한다.
  - `python -m pytest`
  - `python -m ruff check .`
  - `python -m mypy src/krforest`

## 9. 작업 후 체크리스트

- [ ] `pytest` / `ruff` / `mypy` 모두 통과
- [ ] `docs/journal.md`에 작업 항목을 **역시간순(최근이 위)** 으로 추가
- [ ] `docs/resume.md`의 진척도/다음 작업 갱신
- [ ] 의사결정이 있었다면 `docs/decisions.md`에 ADR 형식으로 추가
- [ ] 사용자 가시 변경이면 `README.md`(또는 `CHANGELOG.md` 도입 시 그것)를 갱신
- [ ] 새 endpoint/dataset이면 `catalog.py`에 등록되고 `tests/test_catalog.py`가 통과
