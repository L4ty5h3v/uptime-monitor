import time
import httpx

async def probe(url: str, timeout_ms: int) -> dict:
    timeout = timeout_ms / 1000.0
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            resp = await client.get(url)
        latency_ms = int((time.perf_counter() - start) * 1000)
        ok = 200 <= resp.status_code < 500  # 5xx считаем падением, 4xx — “ответ есть”
        return {
            "ok": ok,
            "status_code": resp.status_code,
            "latency_ms": latency_ms,
            "error": None,
        }
    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "ok": False,
            "status_code": None,
            "latency_ms": latency_ms,
            "error": str(e),
        }