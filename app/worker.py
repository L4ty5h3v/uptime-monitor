import asyncio
from datetime import datetime, timezone

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

    sem = asyncio.Semaphore(20)

    async def check_target(t: Target):
        async with sem:
            result = await probe(t.url, t.timeout_ms)

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

        payload = {
            "target_id": t.id,
            "ts": c.ts.isoformat(),
            "ok": c.ok,
            "status_code": c.status_code,
            "latency_ms": c.latency_ms,
            "error": c.error,
        }
        cache_set_last(r, t.id, payload)

        if c.ok:
            failcount_reset(r, t.id)
        else:
            n = failcount_inc(r, t.id)


    await asyncio.gather(*[check_target(t) for t in targets])

async def loop():
    r = get_redis_master()
    while True:
        db = SessionLocal()
        try:
            await run_once(db, r)
        finally:
            db.close()
        await asyncio.sleep(settings.worker_tick_sec)

def main():
    asyncio.run(loop())

if __name__ == "__main__":
    main()