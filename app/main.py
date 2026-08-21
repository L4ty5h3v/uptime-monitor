import time
import logging

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func

from .db import get_db
from .models import Target, Check
from .schemas import TargetCreate, TargetUpdate, TargetOut, LastStatus
from .redis_cache import get_redis_master, cache_get_last
from .metrics import (
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
    UPTIME_CACHE_HITS_TOTAL,
    UPTIME_CACHE_MISSES_TOTAL,
    UPTIME_STATUS_FALLBACK_DB_TOTAL,
    UPTIME_TARGETS_TOTAL,
    UPTIME_TARGETS_ENABLED,
)

app = FastAPI(title="Uptime Monitor")
logger = logging.getLogger(__name__)


def normalize_path(path: str) -> str:
    if path.startswith("/targets/"):
        return "/targets/{target_id}"
    if path.startswith("/status/"):
        return "/status/{target_id}"
    if path.startswith("/history/"):
        return "/history/{target_id}"
    return path


def refresh_target_metrics(db: Session) -> None:
    total = db.execute(select(func.count()).select_from(Target)).scalar_one()
    enabled = db.execute(
        select(func.count()).select_from(Target).where(Target.enabled.is_(True))
    ).scalar_one()

    UPTIME_TARGETS_TOTAL.set(total)
    UPTIME_TARGETS_ENABLED.set(enabled)


def load_cached_last_status(r, target_id: int):
    try:
        return cache_get_last(r, target_id)
    except Exception:
        logger.warning(
            "cache lookup failed for target_id=%s; falling back to database",
            target_id,
            exc_info=True,
        )
        return None


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    path = normalize_path(request.url.path)
    method = request.method

    if path == "/metrics":
        return await call_next(request)

    HTTP_REQUESTS_IN_PROGRESS.labels(method=method, path=path).inc()
    started = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration = time.perf_counter() - started
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(duration)
        HTTP_REQUESTS_TOTAL.labels(
            method=method,
            path=path,
            status_code=str(status_code),
        ).inc()
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, path=path).dec()


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/targets", response_model=TargetOut)
def create_target(data: TargetCreate, db: Session = Depends(get_db)):
    t = Target(
        name=data.name,
        url=str(data.url),
        interval_sec=data.interval_sec,
        timeout_ms=data.timeout_ms,
        enabled=data.enabled,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    refresh_target_metrics(db)
    return t


@app.get("/targets", response_model=list[TargetOut])
def list_targets(db: Session = Depends(get_db)):
    refresh_target_metrics(db)
    return db.execute(select(Target).order_by(Target.id)).scalars().all()


@app.patch("/targets/{target_id}", response_model=TargetOut)
def update_target(target_id: int, data: TargetUpdate, db: Session = Depends(get_db)):
    t = db.get(Target, target_id)
    if not t:
        raise HTTPException(status_code=404, detail="target not found")

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(t, k, str(v) if k == "url" and v is not None else v)

    db.commit()
    db.refresh(t)
    refresh_target_metrics(db)
    return t


@app.delete("/targets/{target_id}")
def delete_target(target_id: int, db: Session = Depends(get_db)):
    t = db.get(Target, target_id)
    if not t:
        raise HTTPException(status_code=404, detail="target not found")

    db.delete(t)
    db.commit()
    refresh_target_metrics(db)
    return {"deleted": True}


@app.get("/status", response_model=list[LastStatus])
def status_all(db: Session = Depends(get_db)):
    r = get_redis_master()
    targets = db.execute(
        select(Target.id).where(Target.enabled.is_(True))
    ).scalars().all()

    out: list[LastStatus] = []
    for tid in targets:
        cached = load_cached_last_status(r, tid)
        if cached:
            UPTIME_CACHE_HITS_TOTAL.inc()
            out.append(LastStatus(**cached))
            continue

        UPTIME_CACHE_MISSES_TOTAL.inc()
        UPTIME_STATUS_FALLBACK_DB_TOTAL.inc()

        row = db.execute(
            select(Check).where(Check.target_id == tid).order_by(desc(Check.ts)).limit(1)
        ).scalars().first()

        if row:
            out.append(
                LastStatus(
                    target_id=tid,
                    ts=row.ts,
                    ok=row.ok,
                    status_code=row.status_code,
                    latency_ms=row.latency_ms,
                    error=row.error,
                )
            )

    return out


@app.get("/status/{target_id}", response_model=LastStatus)
def status_one(target_id: int, db: Session = Depends(get_db)):
    r = get_redis_master()
    cached = load_cached_last_status(r, target_id)

    if cached:
        UPTIME_CACHE_HITS_TOTAL.inc()
        return LastStatus(**cached)

    UPTIME_CACHE_MISSES_TOTAL.inc()
    UPTIME_STATUS_FALLBACK_DB_TOTAL.inc()

    row = db.execute(
        select(Check).where(Check.target_id == target_id).order_by(desc(Check.ts)).limit(1)
    ).scalars().first()

    if not row:
        raise HTTPException(status_code=404, detail="no checks yet")

    return LastStatus(
        target_id=target_id,
        ts=row.ts,
        ok=row.ok,
        status_code=row.status_code,
        latency_ms=row.latency_ms,
        error=row.error,
    )


@app.get("/history/{target_id}")
def history(target_id: int, limit: int = 100, db: Session = Depends(get_db)):
    limit = max(1, min(limit, 1000))
    rows = db.execute(
        select(Check).where(Check.target_id == target_id).order_by(desc(Check.ts)).limit(limit)
    ).scalars().all()

    return [
        {
            "id": c.id,
            "ts": c.ts,
            "ok": c.ok,
            "status_code": c.status_code,
            "latency_ms": c.latency_ms,
            "error": c.error,
        }
        for c in rows
    ]
