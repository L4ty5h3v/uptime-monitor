from prometheus_client import Counter, Gauge, Histogram

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

UPTIME_TARGETS_ENABLED = Gauge(
    "uptime_targets_enabled",
    "Number of enabled targets",
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