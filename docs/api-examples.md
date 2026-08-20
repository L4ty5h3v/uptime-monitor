# API Examples

This file keeps the README short while preserving the most useful request patterns for local exploration.

## Health Check

```bash
curl http://127.0.0.1:8000/health
```

## Create a Target

```bash
curl -X POST http://127.0.0.1:8000/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Example",
    "url": "https://example.com",
    "interval_sec": 30,
    "timeout_ms": 3000,
    "enabled": true
  }'
```

## List Targets

```bash
curl http://127.0.0.1:8000/targets
```

## Read Status

```bash
curl http://127.0.0.1:8000/status
curl http://127.0.0.1:8000/status/1
```

## Read History

```bash
curl http://127.0.0.1:8000/history/1
curl "http://127.0.0.1:8000/history/1?limit=10"
```

## Update a Target

```bash
curl -X PATCH http://127.0.0.1:8000/targets/1 \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

## Delete a Target

```bash
curl -X DELETE http://127.0.0.1:8000/targets/1
```
