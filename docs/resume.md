# Resume

현재 `python-krforest-api` 프로젝트의 진척도와 이어서 할 작업을 기록합니다. 새 세션이나 작업 재개 시 이 문서를 가장 먼저 확인하세요.

## 현재 진척도 (2026-08-20)

- `T-VN-C05A`의 forest.go.kr `PBD0000041` 통합 ZIP을 구현 계약에 맞게 보강함.
  지역별 중첩 ZIP의 canonical SHP를 재귀적으로 읽고 `_geojson.zip`·`_gpx.zip` 형제
  사본은 중복 방지를 위해 건너뛴다.
- `ForestSpatialFeature.source_id`를 추가하고, 산행로는 `PMNTN_SN`, 둘레길은 원천
  세그먼트 식별자를 우선 사용한다. 산 이름과 구간 이름(`MNTN_NM`·`PMNTN_NM`)도
  표시명으로 결합한다.
- 실측 census(2026-08-20): PBD0000041 265,601,808 bytes, 중첩 SHP ZIP 2,932개,
  전체 피처 164,185개(Point 107,125 / LineString 56,869 / MultiLineString 191),
  `source_id` 고유값 164,182개. 지도 경로 승격 대상은 LineString/MultiLineString이다.
- 반복적인 CRS 생성 비용을 줄이기 위해 `_coordinate_transformer`를 캐시한다. 저메모리
  census는 완료했으며, 전체 DTO materialization은 지도 ETL에서 필요한 geometry gate와
  중복 제거를 먼저 확정한 뒤 별도 live 검증한다.
- 중첩 SHP 회귀 테스트와 `ruff check .`가 통과했다. 둘레길 source-id live test는
  서비스키가 있는 환경에서 실행한다.

## 다음 해야 할 작업 (Next Task)

- [ ] 전문 리뷰어 2명의 독립적 적대적 리뷰를 반영한 뒤 PR 생성·CI·머지.
- [ ] `kor-travel-map`에서 C05A route 변환과 월 1회 schedule을 구현.
- [ ] C05B~C05D typed API와 하루 6회 schedule을 순차 구현.

## 현재 진척도 (2026-06-07)

- `src/krforest/debug.py`의 `save_fixture`에서 파일을 저장할 때 로컬 저장과 함께 `rustfs`에도 저장할 수 있도록 코드를 개선함.
- 호환성 확보를 위해 기존 API 외에 `rustfs` 호출을 위한 전용 함수 `save_to_rustfs`를 추가함.
- **`python-kraddr-base` 의존성 완전 제거.** 좌표는 `latitude: float | None` / `longitude: float | None`, 주소는 `address: str | None`로 평탄화되어 외부 도메인 패키지 없이 동작함. ADR-008.
- `_convert.py`에 `extract_coordinate(row)` / `extract_address(row)` 헬퍼 추가. 결측 sentinel(-99, -999, 0)을 일관 처리.
- `__version__`을 `0.2.0`으로 올림(파괴적 변경). 호환성 부담 의도적으로 단절.
- `pytest` 36 passed / `ruff check` clean / `mypy --strict` clean. mypy 외부 경로 설정도 함께 제거.
- 이전 작업(2026-05-24)에서 정착한 문서 방법론(`SKILL.md`, ADR, journal, resume, tasks)은 그대로 유지하며 ADR-008 추가.
- 에이전트 작업 규칙에 Windows Git(`C:\Program Files\Git\cmd\git.exe`) 사용 원칙을 명시했고, `.codegraph`는 gitignore 대상임을 다시 고정했다.

## 다음 해야 할 작업 (Next Task)

- [ ] PR 본문에 ADR-008 링크와 마이그레이션 가이드(필드명 변경) 정리 후 main에 머지.
- [ ] (백로그) 데이터 반환 스키마 최적화 및 fixture 보강 — `docs/tasks.md` 참조.
- [ ] (백로그) 신규 파일데이터 endpoint 카탈로그 등록.
- [ ] (백로그) `_convert.extract_address`가 주소 문자열만 다루므로, 도로명/지번 분리가 필요한 사용자 시나리오가 생기면 별도 헬퍼 검토.
