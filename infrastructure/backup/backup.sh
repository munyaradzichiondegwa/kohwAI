#!/usr/bin/env bash
# Encrypted PostgreSQL backup.
#   * pg_dump (custom format) -> age (public-key encryption) -> file, written atomically
#   * only the PUBLIC key lives on the server (BACKUP_AGE_RECIPIENT_FILE); the private key stays with the operator,
#     so a compromised server cannot read old backups
#   * retention: BACKUP_KEEP_DAYS daily files + the first backup of each of the last BACKUP_KEEP_MONTHS months
#   * optional off-site copy: set BACKUP_UPLOAD_CMD (receives the file path as $1), e.g. 'aws s3 cp "$1" s3://bucket/kohwai/'
# Exit code != 0 on ANY failure, and a heartbeat file is only touched on success (the compose healthcheck reads it).
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
KEEP_MONTHS="${BACKUP_KEEP_MONTHS:-6}"
RECIPIENT_FILE="${BACKUP_AGE_RECIPIENT_FILE:?BACKUP_AGE_RECIPIENT_FILE (public key file) is required}"
: "${PGDATABASE:?PGDATABASE is required}"
[ -s "$RECIPIENT_FILE" ] || { echo "backup: recipient file $RECIPIENT_FILE is missing/empty" >&2; exit 2; }

mkdir -p "$BACKUP_DIR"
ts="$(date -u +%Y%m%dT%H%M%SZ)"
final="$BACKUP_DIR/${PGDATABASE}-${ts}.dump.age"
partial="$final.partial"
trap 'rm -f "$partial"' EXIT

echo "backup: dumping $PGDATABASE -> $final"
pg_dump --format=custom --no-owner --no-privileges "$PGDATABASE" | age -R "$RECIPIENT_FILE" > "$partial"
[ -s "$partial" ] || { echo "backup: produced an empty file" >&2; exit 3; }
mv "$partial" "$final"
( cd "$BACKUP_DIR" && sha256sum "$(basename "$final")" > "$(basename "$final").sha256" )
echo "backup: wrote $(du -h "$final" | cut -f1)"

# ── retention ──
# daily: delete older than KEEP_DAYS, unless it is the first backup of its month and within KEEP_MONTHS
find "$BACKUP_DIR" -maxdepth 1 -name "${PGDATABASE}-*.dump.age" -mtime +"$KEEP_DAYS" -print0 | sort -z | while IFS= read -r -d '' f; do
  month="$(basename "$f" | sed -E "s/^${PGDATABASE}-([0-9]{6})[0-9]{2}T.*/\1/")"
  first="$(ls "$BACKUP_DIR"/${PGDATABASE}-"${month}"*.dump.age 2>/dev/null | head -1)"
  cutoff="$(date -u -d "-${KEEP_MONTHS} months" +%Y%m)"
  if [ "$f" = "$first" ] && [ "$month" -ge "$cutoff" ]; then continue; fi
  rm -f "$f" "$f.sha256"
done

if [ -n "${BACKUP_UPLOAD_CMD:-}" ]; then
  echo "backup: uploading off-site"
  bash -c "$BACKUP_UPLOAD_CMD" _ "$final"
fi

touch "$BACKUP_DIR/.last_success"
echo "backup: done"
