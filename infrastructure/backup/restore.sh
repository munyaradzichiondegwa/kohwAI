#!/usr/bin/env bash
# Restore an encrypted backup into a database.
#   restore.sh <backup.dump.age> <identity-file> <target-database> [--yes]
# The identity file is the PRIVATE age key (kept offline). The target database is DROPPED and recreated:
# pass --yes to confirm. NEVER point this at the live database without stopping the app first.
set -euo pipefail
file="${1:?usage: restore.sh <backup.dump.age> <identity-file> <target-database> [--yes]}"
identity="${2:?identity file required}"
target="${3:?target database required}"
[ "${4:-}" = "--yes" ] || { echo "restore: this DROPS and recreates '$target'. Re-run with --yes to confirm." >&2; exit 2; }

if [ -f "$file.sha256" ]; then
  ( cd "$(dirname "$file")" && sha256sum -c "$(basename "$file").sha256" ) || { echo "restore: checksum mismatch — file is corrupt or was altered" >&2; exit 3; }
else
  echo "restore: WARNING no .sha256 next to the backup; skipping integrity check" >&2
fi

# Prove we can decrypt BEFORE dropping anything: a wrong key must never leave you with an empty database.
# (head closes the pipe early, so age may exit with SIGPIPE: capture the bytes and ignore the pipeline status)
magic="$( { age -d -i "$identity" "$file" 2>/dev/null | head -c 5; } || true )"
if [ "$magic" != "PGDMP" ]; then
  echo "restore: cannot decrypt this backup with that key (or it is not a pg_dump archive); nothing was changed" >&2
  exit 4
fi

echo "restore: recreating $target"
psql -v ON_ERROR_STOP=1 -d postgres -c "DROP DATABASE IF EXISTS \"$target\"" -c "CREATE DATABASE \"$target\""
age -d -i "$identity" "$file" | pg_restore --no-owner --no-privileges --exit-on-error -d "$target"
echo "restore: done"
