# AGENTS.md

## 목표

`python-krforest-api`(Python 패키지 `krforest`)는 산림청과 `data.go.kr`이 공개하는 여행·안전 관련 산림 데이터만 다루는 비공식 async Python client다. `ForestClient`는 `travel`/`safety`/`files` namespace로 OpenAPI와 파일데이터를 함께 제공하며, 좌표·주소는 외부 도메인 패키지 없이 `latitude: float | None`, `longitude: float | None`, `address: str | None` 원시 필드로 노출한다.

## Think Before Coding

- 요청이 모호할 때는 해석을 조용히 정하지 말 것
- endpoint를 travel/safety 어느 namespace에 둘지, OpenAPI인지 file dataset인지 애매하면 먼저 확인할 것
- 좌표·주소 결측 sentinel(-99, -999, 0) 처리 방식이 새 데이터에도 그대로 맞는지 가정하지 말고 확인할 것
- 안전하게 진행하기 어려울 정도로 혼란스러우면 추측하지 말고 확인할 것

## Simplicity First

- 요청을 완전히 해결하는 최소한의 코드만 작성할 것
- `pykma`, `pyopinet`, `pykex` 같은 자매 라이브러리에 검증된 패턴이 있으면 새로 설계하지 말고 그대로 가져와 맞출 것
- 일회성 용도를 위해 추상화를 만들지 말 것
- 장기 호환 alias나 임시 facade를 만들지 말 것

## Surgical Changes

- 요청을 처리하는 데 필요한 코드만 변경할 것
- `parser.py`(단일 row → 모델), `processor.py`(다중 파일 join), `spatial.py`(SHP/GeoJSON/GPX 변환)의 책임 경계를 넘나들지 말 것
- 관련 없는 코드의 포맷, 이름, 스타일을 건드리지 말 것
- 관련 없는 문제를 발견하면 패치에 섞지 말고 따로 언급할 것

## Goal-Driven Execution

- 모호한 요청을 구체적이고 검증 가능한 결과로 바꿀 것
- 새 endpoint를 추가하면 `tests/test_catalog.py`와 replay fixture로 검증할 것
- provider 응답 변경(HTTP 200이어도 body-level 오류 코드 포함)을 가정 없이 실제 응답으로 확인할 것
- 완전한 검증이 불가능하면(live test 등) 무엇이 아직 미검증인지 밝힐 것

## Practical Bias

- 비단순 작업에서는 성급함보다 신중함을 우선할 것
- 변경 내역은 리뷰 가능한 범위와 요청 범위에 가깝게 유지할 것
- 아주 단순하고 명백한 한 줄 작업은 과하게 무겁게 다루지 말 것

## 문서 언어 정책

이 저장소의 모든 Markdown/RST 문서는 한글로 작성한다. 공식 API 필드명, 코드 식별자, 명령어, URL, provider 원문처럼 그대로 보존해야 하는 값만 영어를 유지한다.

## 식별자 표

| 항목 | 값 |
|------|----|
| GitHub 저장소 | `python-krforest-api` |
| Python import | `from krforest import ForestClient` |
| 환경변수 키 | `DATA_GO_KR_SERVICE_KEY` (유일) |
| 데이터 제공처 | `data.go.kr`, `forest.go.kr` |

## 읽어야 할 문서 (순서대로)

1. `SKILL.md` — 정체성, 빠른 시작, 절대 규칙(DO NOT), 책임 모듈 경계, 작업 후 체크리스트
2. `docs/resume.md` — 현재 진척도와 이어서 해야 할 "다음 작업"
3. `docs/tasks.md` — 프로젝트 백로그(TODO/DONE)
4. `docs/decisions.md` — ADR 표준 형식과 누적 의사결정
5. `docs/journal.md` — 작업 변경 이력(역시간순)
6. `README.md` — 사용자 가이드 및 패키지 개요

## 지시 우선순위

사용자 요청 > AGENTS.md/SKILL.md의 절대 규칙 > `docs/decisions.md`의 ADR > README/기존 코드와 테스트.

## 절대 하지 말 것 (DO NOT)

`SKILL.md` §4에 전체 목록이 있다. 핵심만 다시 적는다:

1. **얇은 래퍼(Thin Wrapper) 생성 금지** — 자매 라이브러리(`pykma`, `pyopinet`, `pykex`)에 검증된 구현이 있으면 구조와 동작을 직접 가져와 맞춘다. 장기 호환 alias나 임시 facade를 만들지 않는다.
2. **다중 키 fallback 금지** — 서비스 키는 `DATA_GO_KR_SERVICE_KEY` 단일 환경변수만 사용한다.
3. **API 키 평문 노출 금지** — 로그, 픽스처, 예외 메시지, `request_params` 어디에도 키가 남아서는 안 된다.
4. **응답 body 확인 누락 금지** — HTTP 200이어도 body-level `resultCode`/`returnReasonCode`를 반드시 확인한다.
5. **외부 도메인 패키지 의존 금지** — 좌표·주소를 위해 `python-kraddr-base` 같은 패키지를 다시 도입하지 않는다(ADR-008).
6. **동기 인터페이스 추가 금지** — `ForestClient`는 async-only다.

## 검증

```bash
python -m pytest
python -m ruff check .
python -m mypy src/krforest
```

세부 개발 규칙, 도메인 어휘, 자주 묻는 작업, 로컬 환경 이슈는 `SKILL.md`를 최우선으로 따른다.
