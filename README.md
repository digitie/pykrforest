# python-krforest-api

Unofficial Python client for Korea Forest Service public data focused on travel
and safety use cases.

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

Pass a key explicitly or set one of these environment variables:

- `KRFOREST_SERVICE_KEY`
- `PYKRFOREST_SERVICE_KEY`
- `KFS_SERVICE_KEY`
- `FOREST_SERVICE_KEY`
- `DATA_GO_SERVICE_KEY`
- `TRIPMATE_DATA_GO_SERVICE_KEY`

```python
from krforest import ForestClient

client = ForestClient.from_env()
page = client.travel.forest_services(num_of_rows=1)

for item in page.items:
    print(item)
```

## API Examples

```python
from krforest import ForestClient

client = ForestClient("YOUR_DATA_GO_KR_KEY")

# api.forest.go.kr legacy XML endpoint
trails = client.travel.forest_services(num_of_rows=5)

# Baekdu-daegan trail records
baekdu = client.travel.baekdu_trails(num_of_rows=5)

# National recreation forest reservation status
reservations = client.travel.recreation_forest_reservations(
    goods_name="숲속의집",
    start_stay_date="20240228",
    end_stay_date="20240228",
    num_of_rows=5,
)

# National recreation forest standard data. Coordinates and addresses are parsed.
standard_forests = client.travel.standard_recreation_forests(
    sido_name="강원특별자치도",
    accommodation_available=True,
    num_of_rows=5,
)

# data.go.kr wildfire endpoint. Some keys need separate approval.
try:
    fires = client.safety.wildfire_stats(
        search_start_date="20240101",
        search_end_date="20241231",
        num_of_rows=5,
    )
except Exception as exc:
    print(exc)
```

Every response is a `Page` with raw item mappings and safe call context:

```python
print(trails.total_count)
print(trails.context.provider)
print(trails.context.request_params)  # service key is removed
```

Coordinate- and address-bearing models use `kraddr.base` public value objects
directly:

```python
from kraddr.base import Address, PlaceCoordinate

weather = client.travel.mountain_weather(num_of_rows=1)
point: PlaceCoordinate | None = weather.items[0].coordinate

dams = client.safety.erosion_control_dams(num_of_rows=1)
print(dams.items[0].coordinate)

forests = client.travel.recreation_forests(name="덕유산")
address: Address | None = forests[0].address
coordinate: PlaceCoordinate | None = forests[0].coordinate

kid_forests = client.travel.kid_forest_centers()
print(kid_forests[0].address, kid_forests[0].coordinate)

education_centers = client.travel.forest_education_centers()
print(education_centers[0].name, education_centers[0].phone_number)

village_forests = client.travel.traditional_village_forests()
print(village_forests[0].name, village_forests[0].coordinate)

huyang_points = client.travel.recreation_forest_arboretums()
print(huyang_points[0].name, huyang_points[0].phone_number)

dulle_features = client.travel.dulle_trail_features()
print(dulle_features[0].geometry_type, dulle_features[0].bbox)

landslide_files = client.safety.landslide_risk_map_files()
print(landslide_files.keys())
```

## File Datasets

The file-data namespace exposes a curated catalog and can discover direct
download URLs from data.go.kr detail pages.

```python
client = ForestClient.from_env()

for dataset in client.files.datasets("travel"):
    print(dataset.data_go_id, dataset.title, dataset.formats)

url = client.files.download_url("15112801")
sample = client.files.download("15112801", max_bytes=2048)
```

`15112801` is `산림청 국립자연휴양림관리소_숲나들e 숲길 100대명산 정보`.
`client.travel.recreation_forests()` combines the national recreation forest
promotion, facility, reservation policy, and reservation file datasets into
high-level detail records with `kraddr.base.Address` and
`kraddr.base.PlaceCoordinate`.

The forest.go.kr entries `PBD0000041`, `PBD0000031`, `PBD0000221`,
`PBD0000220`, `PBD0000077`, `PBD0000180`, and `PBD0000210` are direct ZIP
downloads. `client.files.download(...)` opens the download popup flow and submits
the required purpose as `개인자료용` (`dnldPrps=3`) before fetching the ZIP. Point
SHP files are exposed as `ForestSpatialPoint`, vector trail files as
`ForestSpatialFeature`, and the raster 산사태위험지도 archive as a filename-keyed
`dict[str, bytes]`.

## Debug Fixtures

The library includes Streamlit-free primitives that a separate debug UI can use
to create replay fixtures. `ForestClient.debug_endpoint()` returns a `DebugRun`
with input, request, response, parsed result, processed result, trace, and error
sections. The run also contains `catalog`, a human-readable catalog entry whose
`dataset_name` and `display_name` are dataset titles, not raw data.go.kr ids.
`save_fixture()` writes that run into `tests/fixtures/**/*.json` after redacting
service keys and auth tokens.

```python
from krforest import ForestClient, save_fixture

client = ForestClient.from_env()
run = client.debug_endpoint(
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

For a debug UI selector or Debug Trace tab, use the catalog helpers directly:

```python
from krforest import catalog_entries

catalog_rows = [entry.model_dump(mode="json") for entry in catalog_entries("travel")]
```

For OpenAPI entries, `service_key_url` points to the data.go.kr detail page used
for service-key/application access. `service_key_account_url` points to the
data.go.kr account page for checking issued keys.

Run the bundled development debug UI with Streamlit:

```bash
pip install -e ".[debug-ui]"
streamlit run debug_ui/app.py
```

`tests/test_generated_fixtures.py` replays saved fixtures without calling the
external API. See `docs/debug-fixtures.md` for the fixture schema and assertion
modes.

## Live Tests

```powershell
$env:KRFOREST_SERVICE_KEY = "..."
pytest -m live
```

`api.forest.go.kr` trail endpoints are expected to pass with the tripmate
data.go.kr key. Some `apis.data.go.kr/1400000` safety APIs may return HTTP 403
unless the key has service-specific approval; live tests report that as an
expected authorization xfail instead of hiding it.

## Development Notes

프로젝트와 agent 작업 규칙은 `AGENTS.md`에 정리한다. 로컬 개발 환경에서 반복된
`rg` 권한 문제와 PowerShell UTF-8 출력 문제는 `docs/development-notes.md`를 따른다.
문서에서 파일 위치를 언급할 때는 `src/krforest/client.py`, `docs/forest-api.md`처럼
프로젝트 루트 기준 상대 경로를 쓴다. Python 내부 문서, 즉 모듈/클래스/함수/메서드
docstring과 설명 주석은 provider 원문이나 코드 식별자를 보존해야 하는 경우를
제외하고 한글로 작성한다.

## References

The curated scope was checked against public data.go.kr pages, including:

- https://www.data.go.kr/data/15002725/openapi.do
- https://www.data.go.kr/data/15058682/openapi.do
- https://www.data.go.kr/data/15002734/openapi.do
- https://www.data.go.kr/data/15002731/openapi.do
- https://www.data.go.kr/data/3071170/openapi.do
- https://www.data.go.kr/data/15084696/openapi.do
- https://www.data.go.kr/data/15134227/openapi.do
- https://www.data.go.kr/data/15013111/standard.do
- https://www.data.go.kr/data/15084817/openapi.do
- https://www.data.go.kr/data/3070842/openapi.do
- https://www.data.go.kr/data/15074816/openapi.do
- https://www.data.go.kr/data/15074800/openapi.do
- https://www.data.go.kr/data/15074798/openapi.do
- https://www.data.go.kr/data/15074812/openapi.do
- https://www.data.go.kr/data/15074803/openapi.do
- https://www.forest.go.kr/kfsweb/opda/dataMng/selectPblicDataList.do?mn=NKFS_06_08_02&tabs=3
- https://www.forest.go.kr/kfsweb/opda/dataMng/selectPblicDataList.do?mn=NKFS_06_08_02&tabs=4
- https://www.forest.go.kr/kfsweb/kfi/kfs/trail/trailInformation.do?pblicDataId=PBD0000041&tabs=3&mn=NKFS_06_08_02
- https://www.forest.go.kr/kfsweb/kfi/kfs/trail/treeRoad.do?pblicDataId=PBD0000031&tabs=3&mn=NKFS_06_08_02
- https://www.forest.go.kr/kfsweb/kfi/kfs/trail/sanrimEdu.do?pblicDataId=PBD0000221&tabs=3&mn=NKFS_06_08_02
- https://www.forest.go.kr/kfsweb/kfi/kfs/trail/kidForest.do?mn=NKFS_06_08_02
- https://www.forest.go.kr/kfsweb/kfi/kfs/nwopapi/traVllgFrstInfo.do?pblicDataId=PBD0000077&tabs=3&mn=NKFS_06_08_02
- https://www.forest.go.kr/kfsweb/kfi/kfs/trail/huyang.do?pblicDataId=PBD0000180&tabs=3&mn=NKFS_06_08_02
- https://www.forest.go.kr/kfsweb/kfi/kfs/trail/sanSaTae.do?pblicDataId=PBD0000210&tabs=4&mn=NKFS_06_08_02
