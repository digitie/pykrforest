# Live Test Notes

Run with:

```powershell
$env:TRIPMATE_DATA_GO_SERVICE_KEY = "<tripmate key>"
pytest -m live
```

Expected outcomes with the checked tripmate key on 2026-05-08:

- `api.forest.go.kr/openapi/service/trailInfoService/getforestservice`: passes
- `data.go.kr` file dataset `15112801` download URL discovery: passes
- `apis.data.go.kr/1400000/forestStusService/getfirestatsservice`: may return
  HTTP 403 until the key is approved for that specific API
