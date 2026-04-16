# Uptime Monitor

Uptime Monitor — сервис для мониторинга доступности сайтов и HTTP-эндпоинтов.  

## Что умеет проект

- хранит цели мониторинга в `PostgreSQL`
- периодически проверяет их фоновым `worker`
- сохраняет историю проверок
- кэширует актуальный статус в `Redis` через `Redis Sentinel`
- отдаёт HTTP API для управления целями и просмотра статусов
- экспортирует метрики в `Prometheus`
- централизованно собирает логи в `Elasticsearch`
- визуализирует метрики и логи в `Grafana`
- считает `SLA / SLO / Error Budget`

## Архитектура

```text
                           +-------------------+
                           |      Grafana      |
                           | метрики, логи,    |
                           | SLO, алерты       |
                           +---------+---------+
                                     |
                  +------------------+------------------+
                  |                                     |
                  v                                     v
          +-------+--------+                    +-------+--------+
          |   Prometheus   |                    | Elasticsearch  |
          |   метрики      |                    |    логи        |
          +-------+--------+                    +-------+--------+
                  |                                     ^
                  |                                     |
      +-----------+------------+                +-------+--------+
      |           |            |                |    Logstash    |
      v           v            v                +-------+--------+
  API /metrics  Worker      Exporters                   ^
                           node/postgres/redis          |
                                                        |
                                                +-------+--------+
                                                | Filebeat       |
                                                | + rsyslog      |
                                                +-------+--------+
                                                        |
                         +------------------------------+------------------------------+
                         |                                                             |
                         v                                                             v
                  app / backup / redis logs                                  syslog / service logs
```

## Основные компоненты

### Приложение

- `app/main.py` — API на `FastAPI`
- `app/worker.py` — фоновый процесс выполнения проверок
- `app/checker.py` — HTTP-проверка целевых URL
- `app/metrics.py` — метрики API и worker для `Prometheus`
- `app/redis_cache.py` — работа с `Redis` и `Sentinel`

### Хранение данных

- `PostgreSQL` — постоянное хранилище целей и истории проверок
- `Redis + Redis Sentinel` — кэш последнего статуса и счётчиков ошибок
- `Alembic` — миграции схемы БД

### Инфраструктура

- `Ansible` — деплой и эксплуатационные playbook'и
- `systemd` — управление сервисами
- `Prometheus` — сбор метрик
- `Grafana` — дашборды и алерты
- `Elasticsearch` — хранение и поиск логов
- `Logstash` — маршрутизация и индексация логов
- `Filebeat` — сбор файловых логов
- `node_exporter`, `postgres_exporter`, `redis_exporter` — системные и инфраструктурные метрики

## Наблюдаемость

### Метрики

Проект экспортирует и собирает:

- HTTP-метрики API
- метрики worker по успехам и ошибкам проверок
- latency проверок
- метрики `Redis`, `PostgreSQL` и хоста
- метрики `PostgreSQL` backup через `node_exporter textfile collector`

`Prometheus` опрашивает:

- `127.0.0.1:8000/metrics` — API
- `127.0.0.1:9101/metrics` — worker
- `127.0.0.1:9100` — `node_exporter`
- `127.0.0.1:9121` — `redis_exporter`
- `127.0.0.1:9187` — `postgres_exporter`

### Логи

Собираются следующие логи:

- `/var/log/uptime/*.log`
- `/var/log/postgres-backup/*.log`
- `/var/log/redis/redis-*.log`
- `/var/log/redis/sentinel-*.log`
- системные события через `syslog -> Logstash -> Elasticsearch`

Логи индексируются в `Elasticsearch` по схеме:

- `uptime-logs-app-YYYY.MM.DD`
- `uptime-logs-backup-YYYY.MM.DD`
- `uptime-logs-redis-YYYY.MM.DD`
- `uptime-logs-sentinel-YYYY.MM.DD`
- `uptime-logs-syslog-YYYY.MM.DD`

Для индексов `uptime-logs-*` применяется `ILM policy`, которая удаляет старые индексы через `7` дней.

### SLA / SLO / Error Budget

В проекте используется простой контракт доступности:

- `SLI` — доля успешных проверок
- `SLO` — не менее `90%` успешных проверок за последние `24h`
- `Error Budget` — не более `10%` неуспешных проверок за те же `24h`

В `Grafana` для этого вынесен отдельный дашборд с панелями:

- `Availability 24h`
- `Failure Rate 24h`
- `Budget Consumed`
- `Error Budget Remaining`

## Структура репозитория

```text
app/                 код приложения и worker
ansible/             inventory, роли и playbook'и
infra/               systemd, Redis, Prometheus и служебные конфиги
migrations/          миграции Alembic
scripts/             вспомогательные скрипты
snapshots/           экспортированные артефакты и снимки
requirements.txt     Python-зависимости
README.md            описание проекта
```

## Важные playbook'и

Из директории `ansible/`:

- `playbooks/deploy_app.yml` — деплой приложения
- `playbooks/migration.yml` — применение миграций
- `playbooks/monitoring.yml` — `Prometheus`, `Grafana`, exporters
- `playbooks/elasticsearch_install.yml` — `Elasticsearch` cluster и `Filebeat`
- `playbooks/logstash.yml` — `Logstash`
- `playbooks/site.yml` — базовая инфраструктура

## Основные сервисы

- `uptime-api`
- `uptime-worker`
- `uptime-migrate`
- `redis@6379`
- `redis@6380`
- `redis-sentinel@26379`
- `redis-sentinel@26380`
- `redis-sentinel@26381`

## Быстрые команды API

### Проверка health

```bash
curl http://127.0.0.1:8000/health
```

### Swagger UI

```text
http://127.0.0.1:8000/docs
```

### Создание цели мониторинга

```bash
curl -X POST http://127.0.0.1:8000/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Example",
    "url": "https://example.com",
    "interval_sec": 30,
    "timeout_ms": 3000,
    "enabled": true
  }'
```

### Получение списка целей

```bash
curl http://127.0.0.1:8000/targets
```

### Получение текущего статуса

```bash
curl http://127.0.0.1:8000/status
curl http://127.0.0.1:8000/status/1
```

### Получение истории проверок

```bash
curl http://127.0.0.1:8000/history/1
curl "http://127.0.0.1:8000/history/1?limit=10"
```

### Обновление цели

```bash
curl -X PATCH http://127.0.0.1:8000/targets/1 \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

### Удаление цели

```bash
curl -X DELETE http://127.0.0.1:8000/targets/1
```

## Что уже реализовано в модуле 2

- экспорт метрик приложения через `/metrics`
- отдельные метрики worker на `9101`
- `Prometheus` + `Grafana`
- `node_exporter`, `postgres_exporter`, `redis_exporter`
- логирование через `Filebeat / rsyslog -> Logstash -> Elasticsearch`
- кластер `Elasticsearch` из трёх нод
- индексация логов и `ILM`
- логовые и метрик-дашборды в `Grafana`
- расчёт `Availability`, `Failure Rate` и `Error Budget`

## Полезные артефакты

Экспорт настроек `Grafana` сохраняется в:

- `snapshots/grafana-export/`

Там лежат:

- JSON дашбордов
- список datasources
- alert rules
- contact points
- notification policies

## Итог

Этот репозиторий содержит не только код самого `uptime-monitor`, но и полноценную инфраструктуру для деплоя, мониторинга, логирования, визуализации, алертинга и расчёта бюджета ошибок.  
