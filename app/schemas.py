from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime

class TargetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    url: HttpUrl
    interval_sec: int = Field(default=30, ge=5, le=3600)
    timeout_ms: int = Field(default=3000, ge=200, le=30000)
    enabled: bool = True

class TargetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    url: HttpUrl | None = None
    interval_sec: int | None = Field(default=None, ge=5, le=3600)
    timeout_ms: int | None = Field(default=None, ge=200, le=30000)
    enabled: bool | None = None

class TargetOut(BaseModel):
    id: int
    name: str
    url: str
    interval_sec: int
    timeout_ms: int
    enabled: bool
    created_at: datetime

class LastStatus(BaseModel):
    target_id: int
    ts: datetime
    ok: bool
    status_code: int | None = None
    latency_ms: int | None = None
    error: str | None = None