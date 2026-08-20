# 작업 일지 (Journal)

역시간순(최근 작업이 위로)으로 작업 사항을 기록합니다. 작업이 완료되면 이 문서에 기록을 추가하세요.

## [2026-08-20] C05A 중첩 SHP 등산로 파서·source natural key 보강
- **작업자**: Codex
- **내용**:
  - `PBD0000041`의 지역별 중첩 ZIP 안 canonical SHP를 재귀 파싱하고, 동일 노선의
    `_geojson.zip`·`_gpx.zip` 형제 사본은 건너뛰도록 했다.
  - `ForestSpatialFeature.source_id`를 추가해 `PMNTN_SN`·`Name` 등 원천 식별자를
    `source_file`과 결합하고, 식별자가 없을 때만 raw/geometry SHA-1을 사용한다.
  - 산 이름·구간 이름을 결합한 표시명과 WGS84 route geometry를 보존한다.
  - CRS transformer 캐시로 수천 개 SHP layer의 반복 초기화 비용을 제거했다.
  - 실측 저메모리 census: 265,601,808 bytes / nested SHP ZIP 2,932개 / 원천 피처
    164,185개 / LineString 56,869개 / MultiLineString 191개. 동일 필드·geometry의
    완전 중복 3건은 parser에서 first-wins 제거한다.
  - route-only live parse는 Point를 제외하고 57,060개(LineString 56,869 /
    MultiLineString 191)를 반환했으며, 이름·geometry·source_id와 source_id 유일성을
    모두 확인했다.
- **검증**: 중첩 SHP 단위 테스트 2 passed, `ruff check .` 통과. 서비스키가 없는
  환경에서는 data.go.kr live API 테스트를 실행하지 않았고, 산림 파일 census는
  forest.go.kr에서 별도 완료했다.

## [2026-06-07] 로컬 저장 시 rustfs 동시 저장 및 전용 함수 추가
- **작업자**: Antigravity (AI Agent)
- **내용**:
  - `src/krforest/debug.py`의 `save_fixture` 함수 개선: 파일 저장 시 기존의 로컬 저장과 함께 `rustfs`에도 저장하도록 로직 추가.
  - 호환성 확보를 위해 내장 `open()` 함수 외에 `rustfs` 호출을 전담할 예비 함수 `save_to_rustfs`를 선언함.
  - 로컬 저장이 성공한 뒤 `rustfs` 저장 시도 중 발생한 예외는 무시하도록 처리하여 로컬 저장 안정성 유지.
- **결과**: `python -m pytest` 36 passed / `ruff check` clean / `mypy --strict` clean. 기존 테스트 모두 통과.

## [2026-05-31] Windows Git 사용 원칙 명시 및 `.codegraph` gitignore 재고정
- **작업자**: Codex (AI Agent)
- **내용**:
  - `AGENTS.md`의 개발 환경 정책에 git 관련 명령은 Windows Git(`C:\Program Files\Git\cmd\git.exe`)를 사용한다는 원칙을 추가.
  - `SKILL.md`의 로컬 환경 반복 이슈에 WSL `git`이 worktree의 Windows 경로 `.git`를 오해해 실패할 수 있다는 배경과 함께 동일 원칙을 추가.
  - `.gitignore`의 CodeGraph ignore 패턴을 `.codegraph`로 명시해 디렉터리 이름 자체가 무시되도록 재고정.
  - `docs/resume.md`를 현재 상태에 맞게 갱신하고 다음 작업에 PR/머지 항목을 반영.
- **결과**: 에이전트가 이 worktree에서 git 명령을 실행할 때 Windows Git 사용 기준이 문서화되었고, `.codegraph`는 ignore 대상임을 명확히 유지.

## [2026-05-27] `python-kraddr-base` 의존성 완전 제거 및 좌표·주소 평탄화
- **작업자**: Antigravity (AI Agent)
- **내용**:
  - `pyproject.toml`의 `dependencies`에서 `python-kraddr-base>=0.1.5` 항목 제거. `tool.mypy.mypy_path`도 함께 제거.
  - `src/krforest/_convert.py`에 `extract_coordinate(row)` / `extract_address(row)` 헬퍼와 결측 sentinel 처리(-99, -999, 0) 추가.
  - `models.py`의 좌표·주소 필드를 다음과 같이 평탄화:
    - `coordinate: PlaceCoordinate | None` → `latitude: float | None`, `longitude: float | None`
    - `address: Address | None` → `address: str | None`
  - `parser.py`, `processor.py`, `spatial.py`가 더 이상 `kraddr.base`를 import하지 않도록 재작성. `spatial._place_coordinate`/`_shape_centroid`/`_geometry_centroid`는 `(lat, lon)` 튜플 반환으로 변경.
  - `__init__.py`의 `Address`/`PlaceCoordinate` 재노출 제거. `__version__`을 `0.2.0`으로 올림(파괴적 변경).
  - `tests/test_client.py`, `tests/test_live.py`에서 외부 클래스 import 및 `.coordinate`/`.address.display_address` 단언을 새 평탄 필드 기준으로 갱신.
  - `README.md`, `SKILL.md`, `docs/forest-api.md`, `docs/decisions.md`에서 `kraddr.base` 언급 제거 및 새 모델 인터페이스 반영.
  - `docs/decisions.md`에 ADR-008 추가 (`python-kraddr-base` 의존 제거 및 좌표·주소 평탄화 결정).
- **결과**: `python -m pytest` 36 passed / `ruff check` clean / `mypy --strict` clean. 외부 도메인 패키지 의존 없이 동작.

## [2026-05-24] 코드 리뷰 반영 및 문서 체계 확장
- **작업자**: Antigravity (AI Agent)
- **내용**:
  - `src/krforest` 전체 코드 리뷰 수행. 다음 사항 반영:
    - `spatial._member_by_suffix` 죽은 helper 제거.
    - `config.py` 모듈 함수 사이 공백 보정.
    - `client._page`의 `pageNo`/`numOfRows` 폴백을 가독성 좋게 재작성.
    - `client.recreation_forest_reservations`에서 endpoint 카탈로그가 이미 정의한 `response_format="xml"` 인자를 제거(중복).
    - `_forest_go_request_with_retry`에 지수 백오프(0.5 * 2^attempt) 추가 — 무지연 3연속 재시도를 회피.
    - `models.CallContext.provider`/`CatalogEntry.provider`에서 `Provider | str` 중복을 `str`로 단순화.
  - `SKILL.md`/`docs/decisions.md`/`AGENTS.md`/`docs/resume.md`/`docs/journal.md`/`docs/tasks.md` 갱신.
- **결과**: `python -m pytest` 36 passed / `ruff check` clean / `mypy --strict` clean. 회귀 없음.

## [2026-05-24] 문서화 전략 개편 진입
- **작업자**: Antigravity (AI Agent)
- **내용**: `python-kraddr-geo`를 참조하여 `SKILL.md`, `resume.md`, `tasks.md`, `decisions.md` 등 문서 체계 도입. `AGENTS.md`를 진입점으로 축소.
- **결과**: PR 브랜치(`docs/methodology-and-refactor`) 생성 및 기반 작업 완료.
