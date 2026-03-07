import json
from datetime import datetime, timezone

from redis.sentinel import Sentinel
from redis import Redis

from .config import settings

def _sentinel_hosts():
    parts = [p.strip() for p in settings.redis_sentinel_hosts.split(",") if p.strip()]
    out = []
    for p in parts:
        host, port = p.split(":")
        out.append((host.strip(), int(port)))
    return out

def get_redis_master() -> Redis:
    sentinel = Sentinel(
        _sentinel_hosts(),
        socket_timeout=0.5,
        password=settings.redis_password,
        db=settings.redis_db,
    )
    return sentinel.master_for(settings.redis_master_name, socket_timeout=0.5)

def key_last(target_id: int) -> str:
    return f"target:last:{target_id}"

def key_failcount(target_id: int) -> str:
    return f"target:failcount:{target_id}"

def cache_set_last(r: Redis, target_id: int, payload: dict):
    r.set(key_last(target_id), json.dumps(payload, ensure_ascii=False), ex=settings.ttl_last_status_sec)

def cache_get_last(r: Redis, target_id: int) -> dict | None:
    raw = r.get(key_last(target_id))
    if not raw:
        return None
    return json.loads(raw)

def failcount_inc(r: Redis, target_id: int) -> int:
    k = key_failcount(target_id)
    n = r.incr(k)
    r.expire(k, settings.ttl_failcount_sec)
    return int(n)

def failcount_reset(r: Redis, target_id: int):
    r.delete(key_failcount(target_id))

def now_iso():
    return datetime.now(timezone.utc).isoformat()