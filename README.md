# Uptime Monitor

Uptime Monitor — это небольшое веб-приложение на FastAPI для мониторинга доступности сайтов и HTTP-эндпоинтов.

Приложение позволяет:

- добавлять цели для мониторинга
- хранить список целей в Postgres
- периодически проверять их отдельным worker-процессом
- сохранять историю проверок в Postgres
- кэшировать последний статус в Redis через Redis Sentinel
- быстро получать текущий статус и историю проверок через HTTP API

## Стек

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis + Redis Sentinel
- Alembic

---

## Как это работает

Проект состоит из двух основных частей:

### API
API отвечает за управление целями мониторинга и просмотр результатов проверок.

Основные функции API:

- создать цель
- получить список целей
- обновить цель
- удалить цель
- получить текущий статус
- получить историю проверок

### Worker
Worker работает в цикле и:

- берёт все `enabled=true` цели из базы
- отправляет HTTP-запросы к их URL
- сохраняет результат проверки в таблицу `checks`
- записывает последний статус в Redis
- хранит счётчик неудачных проверок в Redis

---

## Архитектура хранения данных

### PostgreSQL
Postgres используется как основное постоянное хранилище:

- таблица `targets` — список целей
- таблица `checks` — история проверок

### Redis
Redis используется как кэш:

- `target:last:{id}` — последний статус цели
- `target:failcount:{id}` — счётчик подряд идущих неудачных проверок

TTL задаётся через настройки приложения.

---

## Структура проекта

```text
app/
  main.py           # FastAPI API
  worker.py         # background worker
  checker.py        # HTTP-проверка цели
  db.py             # подключение к БД
  models.py         # SQLAlchemy модели
  schemas.py        # Pydantic схемы
  redis_cache.py    # работа с Redis/Sentinel
  config.py         # настройки из .env

migrations/         # Alembic миграции
scripts/            # backup-скрипты Postgres
infra/              # инфраструктурные конфиги
requirements.txt


# Как пользоваться приложением

## 1. Проверить, что API работает

```bash
curl http://127.0.0.1:8000/health
```

Ожидаемый ответ:

```json
{"ok": true}
```

---

## 2. Открыть Swagger UI

FastAPI автоматически предоставляет интерфейс для тестирования API:

```
http://127.0.0.1:8000/docs
```

Через него можно отправлять запросы и смотреть ответы без использования curl.

---

## 3. Добавить цель для мониторинга

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

---

## 4. Получить список целей

```bash
curl http://127.0.0.1:8000/targets
```

---

## 5. Получить текущий статус всех целей

```bash
curl http://127.0.0.1:8000/status
```

---

## 6. Получить текущий статус одной цели

```bash
curl http://127.0.0.1:8000/status/1
```

Пример ответа:

```json
{
  "target_id": 1,
  "ts": "2026-03-11T10:05:00Z",
  "ok": true,
  "status_code": 200,
  "latency_ms": 120,
  "error": null
}
```

---

## 7. Получить историю проверок

```bash
curl http://127.0.0.1:8000/history/1
```

С ограничением количества записей:

```bash
curl "http://127.0.0.1:8000/history/1?limit=10"
```

---

## 8. Обновить цель

Например выключить мониторинг:

```bash
curl -X PATCH http://127.0.0.1:8000/targets/1 \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": false
  }'
```

Изменить URL:

```bash
curl -X PATCH http://127.0.0.1:8000/targets/1 \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://google.com"
  }'
```

Изменить интервал проверки и таймаут:

```bash
curl -X PATCH http://127.0.0.1:8000/targets/1 \
  -H "Content-Type: application/json" \
  -d '{
    "interval_sec": 60,
    "timeout_ms": 5000
  }'
```

---

## 9. Удалить цель

```bash
curl -X DELETE http://127.0.0.1:8000/targets/1
```

Ответ:

```json
{"deleted": true}
```

---

## Пример типичного сценария использования

### Шаг 1 — проверить API

```bash
curl http://127.0.0.1:8000/health
```

### Шаг 2 — добавить цель

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

### Шаг 3 — посмотреть список целей

```bash
curl http://127.0.0.1:8000/targets
```

### Шаг 4 — подождать пока worker выполнит проверки

### Шаг 5 — получить текущий статус

```bash
curl http://127.0.0.1:8000/status/1
```

### Шаг 6 — посмотреть историю проверок

```bash
curl "http://127.0.0.1:8000/history/1?limit=5"
```
