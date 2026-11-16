#!/bin/sh
# Container entrypoint: schedules backup.sh with cron (BACKUP_CRON, default 02:30 UTC daily) and runs one backup
# at start-up when none exists yet, so a fresh deployment is never unprotected for a day.
set -eu
export PGPASSWORD="$(cat /run/secrets/POSTGRES_PASSWORD)"
{
  echo "export PGHOST='${PGHOST:-db}' PGUSER='${PGUSER:-kohwai}' PGDATABASE='${PGDATABASE:-kohwai}' PGPASSWORD='$PGPASSWORD'"
  echo "export BACKUP_DIR='${BACKUP_DIR:-/backups}' BACKUP_AGE_RECIPIENT_FILE='/run/secrets/BACKUP_AGE_RECIPIENT'"
  echo "export BACKUP_KEEP_DAYS='${BACKUP_KEEP_DAYS:-14}' BACKUP_KEEP_MONTHS='${BACKUP_KEEP_MONTHS:-6}'"
  [ -n "${BACKUP_UPLOAD_CMD:-}" ] && echo "export BACKUP_UPLOAD_CMD='$BACKUP_UPLOAD_CMD'"
} > /etc/backup.env
chmod 600 /etc/backup.env
echo "${BACKUP_CRON:-30 2 * * *} . /etc/backup.env && /opt/backup/backup.sh >> /proc/1/fd/1 2>> /proc/1/fd/2" > /etc/crontabs/root
if ! ls "${BACKUP_DIR:-/backups}"/*.dump.age >/dev/null 2>&1; then
  ( . /etc/backup.env && /opt/backup/backup.sh ) || echo "initial backup failed (will retry on schedule)" >&2
fi
exec crond -f -l 8
