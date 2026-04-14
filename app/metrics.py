from prometheus_client import Counter, Gauge, Histogram

# -------- API metrics --------

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests in progress",
    ["method", "path"],
)

UPTIME_CACHE_HITS_TOTAL = Counter(
    "uptime_cache_hits_total",
    "Total Redis cache hits for status endpoints",
)

UPTIME_CACHE_MISSES_TOTAL = Counter(
    "uptime_cache_misses_total",
    "Total Redis cache misses for status endpoints",
)

UPTIME_STATUS_FALLBACK_DB_TOTAL = Counter(
    "uptime_status_fallback_db_total",
    "Total fallback reads from Postgres when Redis cache missed",
)

UPTIME_TARGETS_TOTAL = Gauge(
    "uptime_targets_total",
    "Total number of monitoring targets",
)

UPTIME_TARGETS_ENABLED = Gauge(
    "uptime_targets_enabled",
    "Number of enabled monitoring targets",
)

# -------- Worker metrics --------

UPTIME_CHECKS_TOTAL = Counter(
    "uptime_checks_total",
    "Total number of target checks",
    ["result"],
)

UPTIME_CHECK_DURATION_SECONDS = Histogram(
    "uptime_check_duration_seconds",
    "Target check duration in seconds",
)

UPTIME_WORKER_CYCLE_DURATION_SECONDS = Histogram(
    "uptime_worker_cycle_duration_seconds",
    "Worker cycle duration in seconds",
)

UPTIME_WORKER_TARGETS_PER_CYCLE = Gauge(
    "uptime_worker_targets_per_cycle",
    "Number of targets processed in current worker cycle",
)

UPTIME_WORKER_DB_ERRORS_TOTAL = Counter(
    "uptime_worker_db_errors_total",
    "Total DB errors in worker",
)

UPTIME_WORKER_REDIS_ERRORS_TOTAL = Counter(
    "uptime_worker_redis_errors_total",
    "Total Redis errors in worker",
)

UPTIME_CACHE_UPDATES_TOTAL = Counter(
    "uptime_cache_updates_total",
    "Total Redis cache updates",
)

UPTIME_FAILCOUNT_INCREMENTS_TOTAL = Counter(
    "uptime_failcount_increments_total",
    "Total failcount increments",
)

UPTIME_FAILCOUNT_RESETS_TOTAL = Counter(
    "uptime_failcount_resets_total",
    "Total failcount resets",
)