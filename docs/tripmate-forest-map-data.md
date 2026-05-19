# TripMate 산림복지·산림재난 여행지도 활용 메모

검토일: 2026-05-19

## 목적

TripMate 여행지도 앱에서 산림청 공공데이터를 단순 POI 목록이 아니라 방문 결정을 돕는
현장 정보 레이어로 쓰기 위한 적용안을 정리한다. `python-krforest-api`는
`httpx`/`asyncio` 기반 클라이언트로 전환되어, TripMate 쪽에서는 별도 wrapper보다
`await client.travel...`, `await client.safety...` 공개 API를 직접 사용하는 형태로
연동하는 것이 적합하다.

## 바로 활용 가능한 데이터

| 축 | 데이터 | 구현 경로 | 여행지도 활용 |
| --- | --- | --- | --- |
| 산악기상 | 산림청 국립산림과학원 산악기상정보 | `await client.travel.mountain_weather()` | 산행 전 기온, 습도, 풍속, 강수량, 지면온도 상태 카드 |
| 등산로 | 등산로정보 ZIP, 등산로 OpenAPI | `await client.travel.forest_trail_file_features()`, `await client.travel.forest_spatial_trails()` | 지도 위 등산로 geometry, 코스명, 주변 POI 연결 |
| 둘레길 | 둘레길정보 ZIP, 숲길 서비스 API | `await client.travel.dulle_trail_features()`, `await client.travel.forest_services()` | 걷기 코스 경로, 거리, 예상 소요시간 카드 |
| 명산 | 산 정보, 명산등산로, 100대명산 파일데이터 | `await client.travel.mountain_stories()`, `await client.travel.famous_mountain_trails()` | 산 상세, 접근성, 추천 코스, 주변 콘텐츠 연결 |
| 휴양림·수목원 | 휴양림 표준데이터, 휴양림 파일데이터, 수목원 위치 | `await client.travel.standard_recreation_forests()`, `await client.travel.recreation_forests()`, `await client.travel.recreation_forest_arboretums()` | 숙박·휴식 POI, 주소, 연락처, 홈페이지, 예약 보조 |
| 교육·체험 | 산림교육센터, 유아숲체험원 | `await client.travel.forest_education_centers()`, `await client.travel.kid_forest_centers()` | 가족 여행, 체험형 일정 추천, 연령대 필터 |
| 전통마을숲 | 전통마을숲 위치 | `await client.travel.traditional_village_forests()` | 문화·마을 산책 POI와 주변 코스 연결 |
| 산불 위험 | 산불위험예보, 산불 발생 통계 | `await client.safety.wildfire_risk_forecast()`, `await client.safety.wildfire_stats()` | 위험 등급 배지, 고위험 지역 안내, 과거 이력 참고 |
| 산사태 위험 | 산사태위험지도, 산사태 예측·예보·이력 | `await client.safety.landslide_risk_map_files()`, `await client.safety.landslide_predictions()`, `await client.safety.landslide_forecast_issues()` | 산행·드라이브 경로 주변 위험도 경고 |
| 대응 시설 | 사방댐, 산불소화시설, 진화대원 대기장소 등 | `await client.safety.erosion_control_dams()`, 파일데이터 카탈로그 | 내부 운영 지도, 관리자용 안전 레이어 |

## TripMate 기능 제안

1. 기본 지도는 `산림복지` 레이어와 `산림재난` 레이어를 분리한다. 사용자는 여행 목적에
   맞춰 복지 정보만 보거나, 출발 전 안전 정보만 빠르게 확인할 수 있다.
2. 산행 상세 화면에는 산악기상 관측시각, 기온, 습도, 풍속, 강수량, 지면온도를 작은
   상태 카드로 표시한다. 관측 지점이 제한적이라는 문구도 함께 보여준다.
3. 등산로·둘레길 geometry는 경로 탐색 엔진의 원천이 아니라 참고 레이어로 먼저 노출한다.
   원천 데이터의 정확도와 갱신주기가 일정하지 않을 수 있으므로 내비게이션 대체 문구를 둔다.
4. 가족 여행 추천에는 유아숲체험원, 산림교육센터, 휴양림·수목원을 묶어
   `체험`, `숙박`, `산책` 필터를 제공한다.
5. 산불·산사태 데이터는 공포를 키우는 표현보다 행동을 유도하는 표현을 쓴다.
   예: `확인 필요`, `주의`, `경보`, `방문 전 최신 공지 확인`.
6. 산사태위험지도는 원본 TIF를 모바일 클라이언트에 직접 내려주는 방식보다 서버에서
   타일 또는 요약 레이어로 전처리한 뒤 제공하는 구조가 적합하다.

## 구현 반영 사항

- `15084696` 산악기상정보는 구현되어 있으며 live test 대상에 포함되어 있다.
- forest.go.kr 산림복지 다운로드 항목 중 등산로정보, 둘레길정보, 산림교육센터 현황,
  유아숲체험원 현황, 전통마을숲 위치도, 휴양림수목원 위치도를 직접 ZIP 다운로드 대상으로
  정리했다.
- forest.go.kr 산림재난 다운로드 항목 중 산사태위험지도 ZIP을 추가했다.
- SHP/GeoJSON/GPX처럼 record-shaped vector로 읽을 수 있는 파일은
  `ForestSpatialFeature` 또는 `ForestSpatialPoint`로 반환하고, 산사태위험지도처럼
  TIF/XML/PDF로 구성된 raster ZIP은 파일명 key를 갖는 `dict[str, bytes]`로 반환한다.
- 클라이언트 API는 `ForestClient(api_key=...)`, `ForestClient.from_env()`,
  `async with ...`, `await client.travel...` 형태로 정리했다.

## 운영 주의사항

- data.go.kr `apis.data.go.kr/1400000` 및 `1400377` 일부 endpoint는 서비스별 활용신청
  상태에 따라 HTTP 403을 반환할 수 있다. 앱에서는 인증 실패와 실제 데이터 없음 상태를
  구분해야 한다.
- 산악기상은 실시간 데이터에 가깝지만 관측 지점이 제한적이다. 특정 산 전체의 안전 판정처럼
  표현하지 말고 관측 지점 기준 정보임을 UI에 드러낸다.
- 산사태위험지도 원본은 대용량 raster 파일이므로 모바일 앱에 직접 내려주지 않는다.
- 파일데이터 다운로드 결과의 갱신일을 추적하고, 캐시 갱신 실패 시 이전 데이터의 최신성
  문구를 함께 보여준다.

## 참고 URL

- https://www.data.go.kr/data/15084696/openapi.do
- https://www.forest.go.kr/kfsweb/opda/dataMng/selectPblicDataList.do?mn=NKFS_06_08_02&tabs=3
- https://www.forest.go.kr/kfsweb/opda/dataMng/selectPblicDataList.do?mn=NKFS_06_08_02&tabs=4
