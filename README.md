# python-krforest-api

Korea Forest Service 공개 데이터를 여행과 안전 use case 중심으로 다루는 비공식 async Python client다.

이 package는 생물학, 연구, 임업 사업, 관련 없는 행정 dataset을 넓게 감싸지 않는다. 현재 scope는 다음과 같다.

- 여행: 숲길, 둘레길, 백두대간 trail, 유명산, 산악기상, 숲나들e 예약 API, 국립자연휴양림 standard data, 휴양림 상세, forest.go.kr SHP 공간 dataset
- 안전: 산불 위험/통계, 산사태 예측/이력, 사방댐, 산악기상, 안전 file dataset

## 문서 언어 정책

이 저장소의 모든 Markdown/RST 문서는 한글로 작성한다. API field, code identifier, 명령어, URL, provider 원문은 필요한 경우 원문을 유지한다.

## 설치

```bash
pip install -e ".[dev]"
```

## Service key

`ForestClient`는 `python-krheritage-api`와 비슷한 형태를 따른다. `api_key=...`를 직접 넘기거나 `ForestConfig.from_env()`가 지원 환경 변수를 읽게 한다.

- `DATA_GO_KR_SERVICE_KEY`

```python
import asyncio

from krforest import ForestClient


async def main() -> None:
    async with ForestClient.from_env() as client:
        page = await client.travel.forest_services(num_of_rows=1)
        for item in page.items:
            print(item)


asyncio.run(main())
```

## API 예시

```python
import asyncio

from krforest import ForestClient


async def main() -> None:
    async with ForestClient(api_key="YOUR_DATA_GO_KR_KEY") as client:
        trails = await client.travel.forest_services(num_of_rows=5)
        baekdu = await client.travel.baekdu_trails(num_of_rows=5)
        reservations = await client.travel.recreation_forest_reservations(
            goods_name="숲속의집",
            start_stay_date="20240228",
            end_stay_date="20240228",
            num_of_rows=5,
        )
        standard_forests = await client.travel.standard_recreation_forests(
            sido_name="강원특별자치도",
            accommodation_available=True,
            num_of_rows=5,
        )
        print(trails.total_count, baekdu.total_count, len(reservations.items))
        print(standard_forests.context.request_params)  # service key는 제거된다.


asyncio.run(main())
```

Paged API 응답은 typed item 또는 raw item mapping을 담은 `Page`와 안전한 call context를 반환한다. 좌표·주소가 있는 모델은 외부 의존 없이 `latitude: float | None`, `longitude: float | None`, `address: str | None`을 직접 노출한다.

```python
weather = await client.travel.mountain_weather(num_of_rows=1)
lat: float | None = weather.items[0].latitude
lon: float | None = weather.items[0].longitude

forests = await client.travel.recreation_forests(name="덕유산")
address: str | None = forests[0].address
forest_lat: float | None = forests[0].latitude
forest_lon: float | None = forests[0].longitude

kid_forests = await client.travel.kid_forest_centers()
education_centers = await client.travel.forest_education_centers()
village_forests = await client.travel.traditional_village_forests()
huyang_points = await client.travel.recreation_forest_arboretums()
dulle_features = await client.travel.dulle_trail_features()
landslide_files = await client.safety.landslide_risk_map_files()
```

## File dataset

File-data namespace는 curated catalog를 제공하고 data.go.kr detail page에서 직접 download URL을 찾을 수 있다.

```python
async with ForestClient.from_env() as client:
    for dataset in client.files.datasets("travel"):
        print(dataset.data_go_id, dataset.title, dataset.formats)

    url = await client.files.download_url("15112801")
    sample = await client.files.download("15112801", max_bytes=2048)
```

`15112801`은 국립자연휴양림 "숲나들e 숲길 100대명산" file data다. `client.travel.recreation_forests()`는 국립자연휴양림 promotion, facility, reservation policy, reservation file dataset을 합쳐 `address`, `latitude`, `longitude`가 채워진 상세 record로 제공한다.

forest.go.kr의 `PBD0000041`, `PBD0000031`, `PBD0000221`, `PBD0000220`, `PBD0000077`, `PBD0000180`, `PBD0000210` entry는 직접 ZIP download다. `await client.files.download(...)`는 download popup 흐름을 열고 필요한 목적값(`dnldPrps=3`)을 제출한 뒤 ZIP을 가져온다.

## Debug fixture

Library는 별도 debug UI가 replay fixture를 만들 수 있도록 Streamlit-free primitive를 제공한다. `await ForestClient.debug_endpoint()`는 input, request, response, parsed result, processed result, trace, error, catalog를 담은 `DebugRun`을 반환한다.

```python
from krforest import ForestClient, save_fixture

async with ForestClient.from_env() as client:
    run = await client.debug_endpoint(
        "national_recreation_forest_reservations",
        {"goodsNm": "숲속의집"},
        num_of_rows=1,
    )

save_fixture(
    base_dir="tests/fixtures",
    function_name=run.function,
    case_name="reservation_available",
    description="예약 가능 상태",
    input_data=run.input,
    request_data=run.request,
    response_data=run.response,
    parsed_result=run.parsed,
    processed_result=run.processed,
)
```

Streamlit debug UI 실행:

```bash
pip install -e ".[debug-ui]"
streamlit run debug_ui/app.py
```

## Live test

```powershell
$env:DATA_GO_KR_SERVICE_KEY = "..."
pytest -m live
```

`api.forest.go.kr` trail endpoint는 data.go.kr key로 통과하는 것이 기대된다. 일부 `apis.data.go.kr/1400000` safety API는 service-specific approval이 없으면 HTTP 403을 반환할 수 있으며, live test는 이를 authorization xfail로 보고한다.

## 문서 지도

- [`SKILL.md`](SKILL.md) — 에이전트 작업 가이드라인 (절대 규칙, 구현 원칙, 로컬 환경 이슈 해결)
- [`AGENTS.md`](AGENTS.md) — 에이전트 문서 진입점(Entrypoint)
- [`docs/resume.md`](docs/resume.md) — 현재 진척도와 이어서 해야 할 "다음 작업"
- [`docs/tasks.md`](docs/tasks.md) — 프로젝트 백로그
- [`docs/decisions.md`](docs/decisions.md) — 프로젝트 기술 및 정책 의사결정(ADR)
- [`docs/journal.md`](docs/journal.md) — 작업 일지

## Reference

Curated scope는 data.go.kr와 forest.go.kr 공개 페이지를 기준으로 확인했다. 예시는 `https://www.data.go.kr/data/15084696/openapi.do`와 forest.go.kr public-data download list다.

