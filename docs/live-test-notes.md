# Live test 메모

실행:

```powershell
$env:DATA_GO_KR_SERVICE_KEY = "<data.go.kr key>"
pytest -m live
```

2026-05-08 기준 TripMate key로 기대한 결과:

- `api.forest.go.kr/openapi/service/trailInfoService/getforestservice`: 통과
- data.go.kr file dataset `15112801` download URL discovery: 통과
- `apis.data.go.kr/1400000/forestStusService/getfirestatsservice`: 해당 API 승인 전까지 HTTP 403 가능

## 2026-05-19 async/httpx migration 확인

- Local environment에서 `python -m pytest -m live`를 실행했다.
- 지원 service-key 환경 변수가 없어서 7개 live test가 선택 후 skip됐다.

## 2026-05-20 service-key live 확인

- 당시 지원하던 service-key 변수를 담은 local `.env`를 사용했다. Key 값은 commit하지 않는다.
- `api.forest.go.kr` legacy trail service와 data.go.kr 국립자연휴양림 예약 API는 정상 payload를 반환했지만, 이전 20초 timeout을 간헐적으로 넘길 만큼 느렸다.
- `tests/test_live.py`는 opt-in live client에 60초 timeout을 사용하므로 public API 지연이 client 계약을 가리지 않는다.
- `/tmp/krforest-live-venv/bin/python -m pytest -s -m live tests/test_live.py`는 47.28초에 5 passed, 2 xfailed로 완료됐다.
- Xfailed endpoint는 `apis.data.go.kr/1400000/forestStusService` 산불 통계와 `apis.data.go.kr/1400377/mtweather` 산악기상이며, 둘 다 이 key에 대해 per-API approval이 필요한 기존 경로를 보고했다.

## 2026-05-21 service-key 환경 변수 정리

- `ForestClient.from_env()`와 live test는 이제 `DATA_GO_KR_SERVICE_KEY`만 읽는다.
- `KRFOREST_SERVICE_KEY`, `KFS_SERVICE_KEY`, `FOREST_SERVICE_KEY`, `DATA_GO_SERVICE_KEY`, `TRIPMATE_DATA_GO_SERVICE_KEY` 같은 legacy fallback name은 더 이상 지원하지 않는다.

## 2026-08-20 C05B~C05D live gate

- typed 산악기상·산불위험 V2·산사태 예보발령 live test를 추가했다.
- 현재 worktree에는 `DATA_GO_KR_SERVICE_KEY`가 없어 live 11건이 skip되었다.
- key가 설정된 환경에서는 승인되지 않은 API가 HTTP/body-level 인증 오류를 내더라도
  예외 메시지와 response에 key가 남지 않는지 함께 확인한다.
