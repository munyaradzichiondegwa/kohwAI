#!/usr/bin/env bash
# Restore drill: prove the newest backup is actually restorable and sane. Run it monthly (see DEPLOYMENT.md).
#   verify.sh <backup-dir> <identity-file> [scratch-database]
# Restores into a scratch database, checks the schema/migration state and the append-only audit trigger, then drops it.
set -euo pipefail
dir="${1:?usage: verify.sh <backup-dir> <identity-file> [scratch-database]}"
identity="${2:?identity file required}"
scratch="${3:-kohwai_restore_check}"
here="$(cd "$(dirname "$0")" && pwd)"

latest="$(ls -1t "$dir"/*.dump.age 2>/dev/null | head -1 || true)"
[ -n "$latest" ] || { echo "verify: no backups found in $dir" >&2; exit 2; }
age_s=$(( $(date +%s) - $(stat -c %Y "$latest") ))
echo "verify: newest backup $(basename "$latest") is $((age_s / 3600))h old"
[ "$age_s" -lt $(( ${VERIFY_MAX_AGE_HOURS:-30} * 3600 )) ] || { echo "verify: newest backup is too old" >&2; exit 4; }

"$here/restore.sh" "$latest" "$identity" "$scratch" --yes >/dev/null
q() { psql -At -d "$scratch" -c "$1"; }

tables="$(q "select count(*) from information_schema.tables where table_schema='public'")"
rev="$(q "select version_num from alembic_version")"
trig="$(q "select count(*) from pg_trigger where tgname in ('audit_logs_no_update_delete','audit_logs_no_truncate')")"
users="$(q "select count(*) from users")"
echo "verify: tables=$tables alembic=$rev audit_triggers=$trig users=$users"

fail=0
[ "$tables" -ge 20 ] || { echo "verify: too few tables" >&2; fail=1; }
[ -n "$rev" ] || { echo "verify: no alembic revision" >&2; fail=1; }
[ "$trig" -eq 2 ] || { echo "verify: audit-log immutability triggers are missing" >&2; fail=1; }
psql -d postgres -qc "DROP DATABASE IF EXISTS \"$scratch\""
[ "$fail" -eq 0 ] && echo "verify: OK — backup is restorable" || { echo "verify: FAILED" >&2; exit 1; }
