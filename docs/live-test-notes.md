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
