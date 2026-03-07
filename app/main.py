from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from .db import get_db
from .models import Target, Check
from .schemas import TargetCreate, TargetUpdate, TargetOut, LastStatus
from .redis_cache import get_redis_master, cache_get_last

app = FastAPI(title="Uptime Monitor")

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
    return t

@app.get("/targets", response_model=list[TargetOut])
def list_targets(db: Session = Depends(get_db)):
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
    return t

@app.delete("/targets/{target_id}")
def delete_target(target_id: int, db: Session = Depends(get_db)):
    t = db.get(Target, target_id)
    if not t:
        raise HTTPException(status_code=404, detail="target not found")
    db.delete(t)
    db.commit()
    return {"deleted": True}

@app.get("/status", response_model=list[LastStatus])
def status_all(db: Session = Depends(get_db)):
    r = get_redis_master()
    targets = db.execute(select(Target.id).where(Target.enabled == True)).scalars().all()

    out: list[LastStatus] = []
    for tid in targets:
        cached = cache_get_last(r, tid)
        if cached:
            out.append(LastStatus(**cached))
            continue

        # fallback: последний чек из Postgres
        row = db.execute(
            select(Check).where(Check.target_id == tid).order_by(desc(Check.ts)).limit(1)
        ).scalars().first()
        if row:
            out.append(LastStatus(
                target_id=tid, ts=row.ts, ok=row.ok,
                status_code=row.status_code, latency_ms=row.latency_ms, error=row.error
            ))
    return out

@app.get("/status/{target_id}", response_model=LastStatus)
def status_one(target_id: int, db: Session = Depends(get_db)):
    r = get_redis_master()
    cached = cache_get_last(r, target_id)
    if cached:
        return LastStatus(**cached)

    row = db.execute(
        select(Check).where(Check.target_id == target_id).order_by(desc(Check.ts)).limit(1)
    ).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="no checks yet")
    return LastStatus(
        target_id=target_id, ts=row.ts, ok=row.ok,
        status_code=row.status_code, latency_ms=row.latency_ms, error=row.error
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
        } for c in rows
    ]