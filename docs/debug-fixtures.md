# Debug UI Fixture Workflow

이 문서는 디버그 Web UI가 생성할 fixture와 `python-krforest-api`의 replay 테스트
구조를 정리한다. Web UI는 별도 프로젝트에서 Streamlit으로 구현하고, 이 라이브러리는
Streamlit에 의존하지 않는 debug 실행 객체, fixture 저장 도구, replay 검증 도구만
제공한다.

## 역할 분리

- `src/krforest/client.py`: API 호출과 namespace 진입점.
- `src/krforest/debug.py`: `DebugRun`, `jsonable`, 민감정보 마스킹, fixture 저장.
- `src/krforest/parser.py`: 원격 응답 레코드를 공개 Pydantic 모델로 파싱.
- `src/krforest/processor.py`: 파일데이터와 파싱 결과를 사용자용 결과로 가공.
- `src/krforest/replay.py`: 저장된 fixture의 assertion mode 검증.
- `tests/fixtures/**/*.json`: 디버그 UI 또는 수동으로 저장한 replay fixture.
- `tests/test_generated_fixtures.py`: fixture를 자동 수집해 외부 API 호출 없이 검증.

## DebugRun

디버그 UI는 `ForestClient.debug_endpoint()`를 호출해 한 번의 실행 결과를 받는다.
반환 객체는 `DebugRun`이며 입력, 요청, 원격 응답, parsed, processed, trace, error를
분리해서 담는다.

```python
from krforest import ForestClient, jsonable

client = ForestClient.from_env()
run = client.debug_endpoint(
    "national_recreation_forest_reservations",
    {"goodsNm": "숲속의집"},
    num_of_rows=1,
)

print(jsonable(run)["response"])
```

`DebugRun.request["query"]`에는 서비스키가 들어가지 않는다. 저장 전에는
`redact_sensitive()`가 `serviceKey`, `Authorization`, `x-api-key`, token류 필드를
재귀적으로 `<REDACTED>`로 바꾼다.

`DebugRun.catalog`에는 현재 실행한 endpoint의 카탈로그 항목이 들어간다. Streamlit
디버그 UI의 Debug Trace 탭은 이 값을 그대로 표나 JSON으로 보여줄 수 있다.

```python
from krforest import jsonable

trace_data = {
    "trace": run.trace,
    "catalog": run.catalog,
}
st.json(jsonable(trace_data))
```

카탈로그 선택 목록이 필요하면 라이브러리의 human-readable 카탈로그 함수를 사용한다.
`dataset_name`과 `display_name`은 data.go.kr id가 아니라 데이터셋명이다.
OpenAPI 항목의 `service_key_url`은 서비스키 발급과 활용신청에 쓰는 data.go.kr 상세
페이지를 가리킨다.
`service_key_account_url`은 발급된 인증키를 확인하는 data.go.kr 계정 화면을 가리킨다.

```python
from krforest import catalog_entries

catalog_rows = [entry.model_dump(mode="json") for entry in catalog_entries("travel")]
st.dataframe(catalog_rows)
```

## Fixture 저장

디버그 UI는 실행 결과를 다음 경로에 저장한다.

```text
tests/fixtures/{function_name}/{case_name}.json
```

`save_fixture()`는 같은 파일명이 있으면 기본적으로 덮어쓰지 않는다.

```python
from krforest import save_fixture

path = save_fixture(
    base_dir="tests/fixtures",
    function_name=run.function,
    case_name="reservation_available",
    description="예약 가능 상태",
    input_data=run.input,
    request_data=run.request,
    response_data=run.response,
    parsed_result=run.parsed,
    processed_result=run.processed,
    overwrite=False,
)
```

## Assertion Mode

초기 replay runner는 다음 mode를 지원한다.

| Mode | 의미 |
| --- | --- |
| `snapshot` | `processed` 전체를 비교하되 `exclude_fields`를 제거한다. |
| `schema_only` | 파싱/가공 결과가 `None`이 아니면 통과한다. |
| `required_fields` | `required_fields`에 지정한 필드 경로가 존재하는지 확인한다. |
| `count` | list 길이 또는 `items` 길이, `count` 값을 비교한다. |

외부 API를 호출하는 live/integration 테스트는 `tests/test_live.py`처럼 별도 marker로
분리하고, 기본 테스트는 `tests/fixtures/**/*.json`을 replay하는 방식으로 유지한다.
