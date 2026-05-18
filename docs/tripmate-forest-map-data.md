# Tripmate 산림복지·산림재난 지도 데이터 메모

검토일: 2026-05-17

## 목적

Tripmate 여행지도 앱에서 산림청 공개데이터를 쓸 때, 단순 POI 목록보다 중요한 것은
방문 결정을 돕는 레이어와 현장 안전 신호다. `python-krforest-api`는 여행·안전에
직접 도움이 되는 산림복지와 산림재난 데이터를 우선 연결하고, 생물 표본·임업경제·
행정통계처럼 여행지도와 거리가 먼 데이터는 제외한다.

## 바로 쓸 수 있는 앱 레이어

| 앱 레이어 | 데이터 | 구현 경로 | 활용 |
| --- | --- | --- | --- |
| 산악기상 | 산림청 국립산림과학원_산악기상정보 | `client.travel.mountain_weather()` | 산행 전 기온, 습도, 풍속, 강수량, 지면온도 확인 |
| 등산로 | 등산로정보 ZIP, 등산로 OpenAPI | `client.travel.forest_trail_file_features()`, `client.travel.forest_spatial_trails()` | 지도 위 등산로 geometry, 산 이름, 위치 노출 |
| 숲길·둘레길 | 숲길정보 ZIP, 숲서비스 및 둘레길 API | `client.travel.dulle_trail_features()`, `client.travel.forest_services()` | 코스 경로, 거리, 소요시간 카드 구성 |
| 산·명산 | 산 정보, 명산등산로, 100대명산 파일데이터 | `client.travel.mountain_stories()`, `client.travel.famous_mountain_trails()` | 산 상세, 교통, 선정이유, 추천 코스 |
| 휴양림·수목원 | 휴양림수목원 위치도, 전국휴양림표준데이터, 휴양림 파일데이터 | `client.travel.recreation_forest_arboretums()`, `client.travel.standard_recreation_forests()`, `client.travel.recreation_forests()` | 숙박·휴식 POI, 주소, 연락처, 홈페이지, 예약 보조 |
| 교육·체험 | 산림교육센터 현황, 유아숲체험원 현황 | `client.travel.forest_education_centers()`, `client.travel.kid_forest_centers()` | 가족 여행, 체험형 일정 추천 |
| 전통마을숲 | 전통마을숲 위치도 | `client.travel.traditional_village_forests()` | 문화·마을 산책 POI와 주변 코스 연결 |
| 산불 위험 | 산불위험예보정보, 산불통계, 산불 이미지·시설 파일데이터 | `client.safety.wildfire_risk_forecast()`, `client.safety.wildfire_stats()` | 위험등급 배지, 고위험 지역 안내, 과거 이력 참고 |
| 산사태 위험 | 산사태위험지도, 산사태 예측·예보·이력 | `client.safety.landslide_risk_map_files()`, `client.safety.landslide_predictions()`, `client.safety.landslide_forecast_issues()` | 산행·드라이브 경로 주변 위험도 경고 |
| 대응 시설 | 사방댐, 담수용사방댐, 진화대원대기장소, 산불소화시설 | `client.safety.erosion_control_dams()`, 파일데이터 카탈로그 | 내부 운영 지도, 관리자용 안전 레이어 |

## Tripmate 기능 제안

1. 지도 기본 레이어는 `산·숲길·휴양림`으로 구성하고, 안전 레이어는 사용자가 켤 수
   있는 토글로 둔다.
2. 산행 상세 화면에는 산악기상 관측시각, 강수량, 풍속, 습도, 지면온도를 짧은
   상태 카드로 보여준다.
3. 숲길·등산로 geometry는 경로 탐색용이 아니라 참고용으로 먼저 노출한다. 원천
   데이터의 정확도와 갱신주기가 일정하지 않을 수 있으므로 내비게이션 대체 문구는
   피한다.
4. 가족 여행 추천에는 유아숲체험원, 산림교육센터, 휴양림·수목원을 묶어
   `체험/숙박/산책` 필터를 제공한다.
5. 산불·산사태 데이터는 위험을 과장하지 않고 `확인 필요`, `주의`, `경보`처럼
   행동을 유도하는 문구로 표시한다.
6. 래스터형 산사태위험지도는 앱 서버에서 타일 또는 요약 폴리곤으로 전처리한 뒤
   내려주는 구조가 적절하다. 클라이언트가 원본 TIF를 직접 다루는 방식은 피한다.

## 구현 반영 사항

- `15084696` 산악기상정보는 이미 구현되어 있었고, 이번 검토에서 문서와 live test
  대상에 다시 고정했다.
- forest.go.kr 산림복지 다운로드 항목 중 등산로정보, 숲길정보, 산림교육센터 현황,
  유아숲체험원 현황, 전통마을숲 위치도, 휴양림·수목원 위치도를 직접 ZIP 다운로드
  대상으로 정리했다.
- forest.go.kr 산림재난 다운로드 항목 중 산사태위험지도 ZIP을 추가했다.
- SHP/GeoJSON/GPX처럼 record-shaped vector로 읽을 수 있는 파일은
  `ForestSpatialFeature` 또는 `ForestSpatialPoint`로 반환하고, 산사태위험지도처럼
  TIF/XML/PDF로 구성된 래스터 ZIP은 파일명 key를 갖는 `dict[str, bytes]`로 반환한다.

## 운영 주의사항

- data.go.kr `apis.data.go.kr/1400000`과 `1400377` 일부 endpoint는 서비스 키별
  활용신청 상태에 따라 HTTP 403을 반환할 수 있다. 앱에서는 승인 필요 상태와
  장애를 구분해야 한다.
- 산악기상은 실시간 데이터지만 관측 지점이 제한적이다. 산 전체 날씨처럼 표현하지
  말고, 관측 지점 기준 정보임을 UI에 드러낸다.
- 산사태위험지도는 대용량 래스터 파일이므로 원본을 모바일 앱에 직접 내려주지
  않는다.
- 파일데이터 다운로드 결과는 갱신일을 추적하고, 캐시 갱신 실패 시 이전 데이터와
  최신성 문구를 함께 보여준다.

## 참고 URL

- https://www.data.go.kr/data/15084696/openapi.do
- https://www.forest.go.kr/kfsweb/opda/dataMng/selectPblicDataList.do?mn=NKFS_06_08_02&tabs=3
- https://www.forest.go.kr/kfsweb/opda/dataMng/selectPblicDataList.do?mn=NKFS_06_08_02&tabs=4
