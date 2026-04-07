import asyncio
from datetime import datetime, timezone

from prometheus_client import start_http_server

import time
from .metrics import (
    UPTIME_CHECKS_TOTAL,
    UPTIME_CHECK_DURATION_SECONDS,
    UPTIME_WORKER_CYCLE_DURATION_SECONDS,
    UPTIME_TARGETS_ENABLED,
    UPTIME_WORKER_TARGETS_PER_CYCLE,
    UPTIME_WORKER_DB_ERRORS_TOTAL,
    UPTIME_WORKER_REDIS_ERRORS_TOTAL,
    UPTIME_CACHE_UPDATES_TOTAL,
    UPTIME_FAILCOUNT_INCREMENTS_TOTAL,
    UPTIME_FAILCOUNT_RESETS_TOTAL,
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import Target, Check
from .checker import probe
from .redis_cache import (
    get_redis_master, cache_set_last,
    failcount_inc, failcount_reset
)
from .config import settings

def utcnow():
    return datetime.now(timezone.utc)

async def run_once(db: Session, r):
    targets = db.execute(select(Target).where(Target.enabled == True)).scalars().all()

    UPTIME_TARGETS_ENABLED.set(len(targets))
    UPTIME_WORKER_TARGETS_PER_CYCLE.set(len(targets))

    sem = asyncio.Semaphore(20)

    async def check_target(t: Target):
        async with sem:
            try:
                result = await probe(t.url, t.timeout_ms)
            except Exception:
                UPTIME_CHECKS_TOTAL.labels(result="failure").inc()
                return

        UPTIME_CHECK_DURATION_SECONDS.observe((result["latency_ms"] or 0) / 1000)

        if result["ok"]:
            UPTIME_CHECKS_TOTAL.labels(result="success").inc()
        else:
            UPTIME_CHECKS_TOTAL.labels(result="failure").inc()

        try:
            c = Check(
                target_id=t.id,
                ok=result["ok"],
                status_code=result["status_code"],
                latency_ms=result["latency_ms"],
                error=result["error"],
            )
            db.add(c)
            db.commit()
            db.refresh(c)
        except Exception:
            db.rollback()
            UPTIME_WORKER_DB_ERRORS_TOTAL.inc()
            return

        payload = {
            "target_id": t.id,
            "ts": c.ts.isoformat(),
            "ok": c.ok,
            "status_code": c.status_code,
            "latency_ms": c.latency_ms,
            "error": c.error,
        }

        try:
            cache_set_last(r, t.id, payload)
            UPTIME_CACHE_UPDATES_TOTAL.inc()

            if c.ok:
                failcount_reset(r, t.id)
                UPTIME_FAILCOUNT_RESETS_TOTAL.inc()
            else:
                failcount_inc(r, t.id)
                UPTIME_FAILCOUNT_INCREMENTS_TOTAL.inc()
        except Exception:
            UPTIME_WORKER_REDIS_ERRORS_TOTAL.inc()

    await asyncio.gather(*[check_target(t) for t in targets])

async def loop():
    r = get_redis_master()
    while True:
        started = time.perf_counter()
        db = SessionLocal()
        try:
            await run_once(db, r)
        finally:
            db.close()

        UPTIME_WORKER_CYCLE_DURATION_SECONDS.observe(
            time.perf_counter() - started
        )

        await asyncio.sleep(settings.worker_tick_sec)

def main():
    start_http_server(9101)
    asyncio.run(loop())

if __name__ == "__main__":
    main()