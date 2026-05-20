# Live Test Notes

Run with:

```powershell
$env:KRFOREST_SERVICE_KEY = "<data.go.kr key>"
pytest -m live
```

Expected outcomes with the checked tripmate key on 2026-05-08:

- `api.forest.go.kr/openapi/service/trailInfoService/getforestservice`: passes
- `data.go.kr` file dataset `15112801` download URL discovery: passes
- `apis.data.go.kr/1400000/forestStusService/getfirestatsservice`: may return
  HTTP 403 until the key is approved for that specific API

2026-05-19 async/httpx migration check:

- `python -m pytest -m live` was executed in the local environment.
- No supported service-key environment variable was set, so all 7 live tests
  were selected and skipped with `no Korea public-data service key environment
  variable is set`.

2026-05-20 service-key live check:

- A local `.env` with `KRFOREST_SERVICE_KEY` was used. Do not commit the key
  value.
- `api.forest.go.kr` legacy trail service and the data.go.kr national recreation
  forest reservation API both returned normal payloads, but were slow enough to
  intermittently exceed the previous 20 second live-test timeout.
- `tests/test_live.py` now uses a 60 second timeout for opt-in live clients so
  transient public API latency does not mask the client contract.
- `/tmp/krforest-live-venv/bin/python -m pytest -s -m live tests/test_live.py`
  completed with 5 passed and 2 xfailed in 47.28 seconds.
- The xfailed endpoints were `apis.data.go.kr/1400000/forestStusService`
  wildfire stats and `apis.data.go.kr/1400377/mtweather` mountain weather, both
  reporting the existing per-API approval-needed path for this key.
