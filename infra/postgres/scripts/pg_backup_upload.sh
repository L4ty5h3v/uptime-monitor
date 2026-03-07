#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/var/backups/uptime"
REMOTE="yadisk:uptime-backups"

LATEST=$(ls -1t "${BACKUP_DIR}"/*.dump.gz | head -n 1)

rclone mkdir "${REMOTE}" || true
rclone copy "${LATEST}" "${REMOTE}" --progress

echo "OK uploaded: ${LATEST}"
