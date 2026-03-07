#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/var/backups/uptime"
DB_NAME="uptime"
DB_USER="uptime"
DB_HOST="127.0.0.1"
TS="$(date +%F_%H-%M-%S)"

OUT="${BACKUP_DIR}/${DB_NAME}_${TS}.dump"

# 1) Снимаем дамп в custom-формате (лучше для pg_restore)
pg_dump -h "${DB_HOST}" -U "${DB_USER}" -Fc "${DB_NAME}" -f "${OUT}"

# 2) Проверка целостности: pg_restore должен уметь прочитать архив
pg_restore -l "${OUT}" > /dev/null

# 3) Сжимаем
gzip -f "${OUT}"

# 4) Ретеншн: удаляем старше 7 дней
find "${BACKUP_DIR}" -type f -name "*.dump.gz" -mtime +7 -delete

echo "OK: ${OUT}.gz"
