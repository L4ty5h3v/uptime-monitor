from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Postgres
    database_url: str

    # Redis Sentinel
    redis_sentinel_hosts: str = "127.0.0.1:26379,127.0.0.1:26380,127.0.0.1:26381"
    redis_master_name: str = "mymaster"
    redis_db: int = 0
    redis_password: str | None = None

    # Cache / TTL
    ttl_last_status_sec: int = 120
    ttl_failcount_sec: int = 300

    # Worker
    worker_tick_sec: int = 1  # частота цикла планировщика (не интервал чеков)
    default_slow_threshold_ms: int = 800

settings = Settings()