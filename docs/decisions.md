# DECISIONS — Architecture Decision Records

본 문서는 `python-krforest-api` 프로젝트의 의사결정을 시간순으로 누적한다. 결정이 뒤집힐 때도 이전 기록은 지우지 않고 `superseded by ADR-XXX`로 표시한다.

## ADR 표준 형식

```
## ADR-NNN: <결정 요약>

- 상태: proposed | accepted | superseded by ADR-XXX
- 날짜: YYYY-MM-DD
- 결정자: <agent | human>

### 컨텍스트
<무엇이 문제였나. 어떤 제약·요구가 있었나.>

### 결정
<무엇을 정했는가. 한 문장으로.>

### 근거
-

### 결과(긍정)
-

### 결과(부정)
-

### 후속
- (open) 추가 검증 필요한 사항
```

---

## ADR-001: 에이전트 문서화 전략(Methodology) 도입

- 상태: accepted
- 날짜: 2026-05-24
- 결정자: human + agent

### 컨텍스트
에이전트가 코드를 관리하고 유지보수할 때 컨텍스트 유지와 일관성 확보가 필요했다. 기존 `AGENTS.md`는 항목이 너무 많아 진입점 역할을 못 했다.

### 결정
`python-kraddr-geo`의 문서화 구조를 차용하여, 에이전트 가이드(`SKILL.md`), 현재 상태 기록(`resume.md`), 일지(`journal.md`), 백로그(`tasks.md`), 의사결정(`decisions.md`)으로 분리한다.

### 근거
- 진입점(`AGENTS.md`)과 상세 규칙(`SKILL.md`)을 분리하면 새 에이전트가 첫 화면에서 압도되지 않는다.
- 작업 후 갱신 대상(journal/resume/decisions)을 명시해 컨텍스트 유실을 막을 수 있다.
- `kraddr-geo`에서 같은 구조가 이미 동작 검증됨.

### 결과(긍정)
- 새 작업 진입 비용 감소.
- 의사결정 근거가 누적되어 같은 논의를 다시 하지 않는다.

### 결과(부정)
- 작업 완료 시 문서 갱신 의무가 추가된다.

---

## ADR-002: 서비스 키는 `DATA_GO_KR_SERVICE_KEY` 단일 환경변수만 사용한다

- 상태: accepted
- 날짜: 2026-05-24
- 결정자: human

### 컨텍스트
초기 구현은 `KRFOREST_SERVICE_KEY` 등 별칭 환경변수를 fallback으로 허용했다. 키가 여러 곳에 흩어지면 어떤 키가 실제로 쓰였는지 추적이 어렵고, 유출 시 회수 범위가 모호해진다.

### 결정
키 로드는 `config.from_env`가 `DATA_GO_KR_SERVICE_KEY` **하나만** 읽도록 고정한다. 새 별칭은 도입하지 않는다.

### 근거
- 동일 키가 `data.go.kr` 게이트웨이와 `forest.go.kr` OpenAPI 모두에서 통과한다(live test로 확인).
- 키 마스킹/감사를 단순화한다.
- 같은 계열 라이브러리(`pykma`, `pykex`)의 키 관리 정책과 일관.

### 결과(긍정)
- 코드 경로 단일화, 키 유출 시 회수 표면 최소화.
- 테스트 fixture와 live test가 같은 환경변수를 공유.

### 결과(부정)
- 외부에서 다른 이름의 환경변수를 쓰던 사용자는 마이그레이션이 필요.

---

## ADR-003: 응답 envelope의 body-level `resultCode`를 반드시 검증한다

- 상태: accepted
- 날짜: 2026-05-24
- 결정자: agent

### 컨텍스트
data.go.kr 게이트웨이는 인증 실패, 쿼터 초과, 활용신청 미승인 같은 오류를 HTTP 200으로 반환하면서 body의 `response.header.resultCode`(또는 `OpenAPI_ServiceResponse.cmmMsgHeader.returnReasonCode`)에 코드를 담는다. HTTP 상태만 보면 오류를 놓친다.

### 결정
`_http._normalize_payload`와 `_http._raise_openapi_service_error`에서 정상 코드(`""`, `"00"`, `"0000"`, `"NORMAL_CODE"`)만 통과시키고, `"03"`(no data)은 빈 `Page`로 정상 처리한다. 나머지는 `failure_kind`가 부여된 `ForestApiError` 하위로 매핑한다.

### 근거
- 인증 오류와 데이터 없음을 명확히 구분해야 호출자가 재시도 정책을 정할 수 있다.
- envelope 차이는 상위 코드에서 신경 쓰지 않도록 transport 레이어에서 흡수.

### 결과(긍정)
- 호출자는 `ForestAuthError`/`ForestRateLimitError`/`ForestNoDataError`로 분기하면 된다.
- live test가 인증 미승인을 `xfail`로 분류 가능.

### 결과(부정)
- 새 코드값을 만날 때마다 매핑을 보완해야 한다.

---

## ADR-004: 얇은 래퍼 대신 검증된 자매 라이브러리 구조를 그대로 가져온다

- 상태: accepted
- 날짜: 2026-05-24
- 결정자: human

### 컨텍스트
공공데이터 클라이언트는 패턴이 비슷하다(`ServiceKey`, `pageNo`, `numOfRows`, XML/JSON envelope). 새 wrapper/adapter/gateway 레이어를 만들면 호출 경로만 늘고 유지보수 비용이 커진다.

### 결정
`pykma`, `pyopinet`, `pykex` 등 자매 라이브러리에 검증된 구현 패턴이 있으면 구조와 동작을 그대로 가져와 맞춘다. 장기 호환 alias나 임시 facade는 만들지 않는다.

### 근거
- 검증된 패턴 재사용은 버그 표면을 줄인다.
- 사용자(다른 클라이언트도 함께 쓰는 개발자)에게 일관된 API 표면 제공.

### 결과(긍정)
- `ForestClient(api_key=..., timeout=..., max_rps=...)` 형태와 namespace 패턴이 자매 라이브러리와 동일.

### 결과(부정)
- 자매 라이브러리의 결함도 함께 가져올 수 있어, 한쪽 수정 시 다른 쪽도 점검해야 한다.

---

## ADR-005: 라이브러리 API는 async-only로 둔다

- 상태: accepted
- 날짜: 2026-05-24
- 결정자: human

### 컨텍스트
공공데이터 호출은 페이지네이션·다중 dataset 결합·rate limit 동시 제어가 잦다. 동기/비동기를 모두 제공하면 코드 경로가 두 배가 되고 mypy strict 통과가 어려워진다.

### 결정
`ForestClient`는 async-only다. 동기 컨텍스트(Jupyter, 단순 스크립트)에서는 호출자가 `asyncio.run`으로 감싼다.

### 근거
- `httpx.AsyncClient`, `kraddr.base` async API와 자연스럽게 결합.
- `_ratelimit.AsyncTokenBucket`으로 동시성·RPS 제어 단순.
- `pytest-asyncio`로 테스트 일원화.

### 결과(긍정)
- 코드 경로 단순화, mypy strict 통과 용이.
- 페이지 순회(`iter_pages`)와 다중 파일데이터 결합 시 동시성 제어가 자연스러움.

### 결과(부정)
- 단순 동기 환경에서는 한 줄 래퍼가 필요.

---

## ADR-006: 레코드 변환의 책임을 parser / processor / spatial로 분리한다

- 상태: accepted
- 날짜: 2026-05-24
- 결정자: agent

### 컨텍스트
공공데이터는 단일 row → 모델 변환, 여러 CSV/Excel join → 단일 객체 생성, SHP/GeoJSON/GPX → 공간 DTO 변환 등 변환 유형이 서로 다르다. 한 파일에 모두 두면 모듈 책임이 빠르게 무너진다.

### 결정
- `parser.py`: **단일 row → 공개 모델** (예: `parse_mountain_weather`).
- `processor.py`: **여러 파일·여러 row를 join해 단일 객체 생성** (예: `build_recreation_forests`).
- `spatial.py`: **SHP/GeoJSON/GPX → 좌표·도형 DTO** (예: `forest_spatial_points`).

### 근거
- 호출 위치만 봐도 책임이 짐작된다.
- 테스트 fixture가 모듈 단위로 분리되어 회귀가 명확.

### 결과(긍정)
- 새 변환 추가 시 어느 파일에 넣을지 즉시 결정 가능.

### 결과(부정)
- 세 모듈이 모두 같은 row key 셋(`_INSTITUTION_ID_KEYS` 등)을 참조해야 할 때 중복이 생긴다.

---

## ADR-007: data.go.kr 파일데이터는 JSON-LD `contentUrl`을 우선 사용한다

- 상태: accepted
- 날짜: 2026-05-24
- 결정자: human

### 컨텍스트
data.go.kr 파일 상세 페이지는 다운로드 URL을 HTML/JS로 동적 구성한다. URL을 하드코드하면 사이트 개편 시 한꺼번에 깨진다.

### 결정
파일데이터 다운로드 URL은 상세 페이지의 JSON-LD(`type=application/ld+json`) 안의 `contentUrl`을 우선 탐색하고, 폴백으로 `"contentUrl": "..."` 정규식을 사용한다. forest.go.kr는 별도 popup → history → ZIP 흐름을 유지한다.

### 근거
- JSON-LD는 검색엔진·메타데이터 표준이라 페이지 개편 시에도 비교적 안정.
- 폴백 정규식으로 JSON-LD가 일시 누락된 경우에도 동작.

### 결과(긍정)
- data.go.kr 페이지 구조 변경 영향이 줄어듦.

### 결과(부정)
- forest.go.kr는 별도 흐름이라 두 가지 경로를 모두 유지해야 한다.
