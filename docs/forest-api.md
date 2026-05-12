# Korea Forest Service Travel and Safety Data Scope

This document records the implemented scope. The initial data.go.kr search for
`산림청` returned hundreds of datasets; python-krforest-api narrows that to travel,
outdoor recreation, wildfire, landslide, and forest safety data.

## Implemented OpenAPI Endpoints

| Key | Category | Provider | data.go.kr | Operation |
| --- | --- | --- | --- | --- |
| `forest_trail_services` | travel | forest.go.kr | 15002725 | `trailInfoService/getforestservice` |
| `mountain_stories` | travel, safety | forest.go.kr | 15058682 | `trailInfoService/getforeststoryservice` |
| `forest_spatial_trails` | travel | forest.go.kr | 15002734 | `trailInfoService/getforestspatialdataservice` |
| `baekdu_trails` | travel | forest.go.kr | 15002731 | `trailInfoService/gettrailservice` |
| `famous_mountain_trails` | travel | forest.go.kr | 3071170 | `cultureInfoService/gdTrailInfoImgOpenAPI` |
| `mountain_weather` | travel, safety | data.go.kr | 15084696 | `1400377/mtweather/mountListSearch` |
| `national_recreation_forest_reservations` | travel | data.go.kr | 15134227 | `1400000/nationalRecreationForestReservationService/nationalRecreationForestReservationList` |
| `wildfire_risk_forecast` | safety | data.go.kr | 15084817 | `1400377/forestPoint/forestPointListGeongugSearch` |
| `wildfire_stats` | safety | data.go.kr | 3070842 | `1400000/forestStusService/getfirestatsservice` |
| `past_landslides` | safety | data.go.kr | 15074816 | `1400000/pastLndslInfoService/pastLndslInfoList` |
| `landslide_predictions` | safety | data.go.kr | 15074800 | `1400000/predictionInfoService/predictionInfoList` |
| `landslide_forecast_issues` | safety | data.go.kr | 15074798 | `1400000/forecastIssueService/forecastIssueList` |
| `roadside_landslides` | safety | data.go.kr | 15074812 | `1400000/roadsideLndslInfoService/roadsideLndslInfoList` |
| `erosion_control_dams` | safety | data.go.kr | 15074803 | `1400000/ecndmInfoService/ecndmInfoList` |

Notes:

- `forest.go.kr` legacy endpoints currently return XML and work with the
  tripmate data.go.kr key.
- Some `apis.data.go.kr/1400000` and `1400377` endpoints returned HTTP 403 with
  the checked tripmate key on 2026-05-08. The client still implements them
  because they are public endpoints, but live tests mark missing approval
  cleanly as authorization xfail.
- `national_recreation_forest_reservations` uses the official
  `serviceKey` query parameter name and returns XML reservation status items
  with institution, goods, stay date, and status fields.
- `client.travel.recreation_forests()` combines the national recreation forest
  promotion, facility, reservation policy, and reservation file datasets into a
  high-level detail record with `kraddr.base.Address` and
  `kraddr.base.PlaceCoordinate`.

## Implemented File Datasets

| data.go.kr | Category | Format | Dataset |
| --- | --- | --- | --- |
| 15112801 | travel | CSV | 산림청 국립자연휴양림관리소_숲나들e 숲길 100대명산 정보 |
| 3034022 | travel | SHP | 산림청_등산로(산림문화·휴양정보) |
| 3034163 | travel | SHP | 산림청_숲길(산림문화·휴양정보) |
| 15098177 | travel | GPX | 한국등산트레킹지원센터_산림청 100대명산 |
| 15041973 | travel | SHP | 산림청_휴양림수목원 위치도 |
| 15064415 | travel | CSV | 국립자연휴양림 홍보 |
| 15064419 | travel | CSV | 국립자연휴양림 시설관련 정보 |
| 15064416 | travel | CSV | 국립자연휴양림 예약 정책 |
| 15064418 | travel | CSV | 국립자연휴양림 예약 정보 |
| 15113956 | travel | CSV | 명품숲길정보 |
| 15113562 | travel | CSV | 숲나들e 숲길정보 |
| 15110618 | travel | CSV | 국가숲길 이용등급 데이터 |
| 15141659 | travel | SHP | 국가숲길 노선도 데이터(한라산둘레길) |
| 15141660 | travel | SHP | 국가숲길 노선도 데이터(속리산둘레길) |
| 15074817 | safety | IMG, XML | 산사태위험지도 |
| 15121380 | safety | CSV | 산불통계데이터 |
| 15125006 | safety | CSV | 최근 5년간 전국 산사태 발생 이력 |
| 15072172 | safety | XLS | 산사태예보발령 |
| 15120930 | safety | CSV | 산사태정보 실황정보 |
| 15092027 | safety | CSV | 대형산불위험예보목록정보 |
| 15092032 | safety | CSV | 동해안산불위험예보정보 |
| 15125648 | safety | PNG | 산불위험예보분석이미지 |
| 15125640 | safety | PNG | 산불위험실황분석이미지 |
| 15121208 | safety | CSV | 산불신고 유형별 위험지수 |
| 15144785 | safety | CSV | 산불소화시설 |
| 15144788 | safety | CSV | 진화대원대기장소 |
| 15144784 | safety | CSV | 담수용사방댐 |

## Exclusions

Excluded examples include pure biology/specimen catalogs, forestry economics,
legal interpretation, business registration, and local-government datasets that
only mention 산림청 in their descriptions. The GPX 100대명산 file dataset is
included because it directly supports hiking/travel use.
