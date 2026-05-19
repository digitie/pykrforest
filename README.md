# python-krforest-api

Unofficial async Python client for Korea Forest Service public data focused on
travel and safety use cases.

The package intentionally excludes broad biology, research, forestry-business,
and unrelated administrative datasets. It covers:

- travel: forest trails, dulle-gil, Baekdu-daegan trails, famous mountains,
  mountain weather, recreation forest reservation API, national recreation forest
  standard data, recreation forest details, forest.go.kr SHP spatial datasets
- safety: wildfire risk/statistics, landslide prediction/history, erosion-control
  dams, mountain weather, safety file datasets

## Install

```bash
pip install -e ".[dev]"
```

## Service Key

`ForestClient` follows the `python-krheritage-api` shape: pass `api_key=...` or
let `ForestConfig.from_env()` load one of the supported environment variables.

- `KRFOREST_SERVICE_KEY`
- `KFS_SERVICE_KEY`
- `FOREST_SERVICE_KEY`
- `DATA_GO_SERVICE_KEY`
- `TRIPMATE_DATA_GO_SERVICE_KEY`

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

## API Examples

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

        try:
            fires = await client.safety.wildfire_stats(
                search_start_date="20240101",
                search_end_date="20241231",
                num_of_rows=5,
            )
        except Exception as exc:
            print(exc)

        print(trails.total_count, baekdu.total_count, len(reservations.items))
        print(standard_forests.context.request_params)  # service key is removed


asyncio.run(main())
```

Every paged API response is a `Page` with typed items or raw item mappings and a
safe call context. Coordinate- and address-bearing models use
`kraddr.base.Address` and `kraddr.base.PlaceCoordinate` directly.

```python
from kraddr.base import Address, PlaceCoordinate

weather = await client.travel.mountain_weather(num_of_rows=1)
point: PlaceCoordinate | None = weather.items[0].coordinate

dams = await client.safety.erosion_control_dams(num_of_rows=1)
forests = await client.travel.recreation_forests(name="덕유산")
address: Address | None = forests[0].address
coordinate: PlaceCoordinate | None = forests[0].coordinate

kid_forests = await client.travel.kid_forest_centers()
education_centers = await client.travel.forest_education_centers()
village_forests = await client.travel.traditional_village_forests()
huyang_points = await client.travel.recreation_forest_arboretums()
dulle_features = await client.travel.dulle_trail_features()
landslide_files = await client.safety.landslide_risk_map_files()
```

## File Datasets

The file-data namespace exposes a curated catalog and can discover direct
download URLs from data.go.kr detail pages.

```python
async with ForestClient.from_env() as client:
    for dataset in client.files.datasets("travel"):
        print(dataset.data_go_id, dataset.title, dataset.formats)

    url = await client.files.download_url("15112801")
    sample = await client.files.download("15112801", max_bytes=2048)
```

`15112801` is the national recreation forest “숲나들e 숲길 100대명산” file data.
`client.travel.recreation_forests()` combines the national recreation forest
promotion, facility, reservation policy, and reservation file datasets into
high-level detail records with `kraddr.base.Address` and
`kraddr.base.PlaceCoordinate`.

The forest.go.kr entries `PBD0000041`, `PBD0000031`, `PBD0000221`,
`PBD0000220`, `PBD0000077`, `PBD0000180`, and `PBD0000210` are direct ZIP
downloads. `await client.files.download(...)` opens the download popup flow and
submits the required purpose as personal-data use (`dnldPrps=3`) before fetching
the ZIP. Point SHP files are exposed as `ForestSpatialPoint`, vector trail files
as `ForestSpatialFeature`, and the landslide-risk-map archive as a
filename-keyed `dict[str, bytes]`.

## Debug Fixtures

The library includes Streamlit-free primitives that a separate debug UI can use
to create replay fixtures. `await ForestClient.debug_endpoint()` returns a
`DebugRun` with input, request, response, parsed result, processed result, trace,
and error sections. The run also contains `catalog`, a human-readable catalog
entry whose `dataset_name` and `display_name` are dataset titles.

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

Run the bundled development debug UI with Streamlit:

```bash
pip install -e ".[debug-ui]"
streamlit run debug_ui/app.py
```

## Live Tests

```powershell
$env:KRFOREST_SERVICE_KEY = "..."
pytest -m live
```

`api.forest.go.kr` trail endpoints are expected to pass with a data.go.kr key.
Some `apis.data.go.kr/1400000` safety APIs may return HTTP 403 unless the key
has service-specific approval; live tests report that as an expected
authorization xfail instead of hiding it.

## References

The curated scope was checked against public data.go.kr and forest.go.kr pages,
including `https://www.data.go.kr/data/15084696/openapi.do` and the
forest.go.kr public-data download lists for travel and safety tabs.
