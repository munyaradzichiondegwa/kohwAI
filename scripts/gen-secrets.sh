#!/usr/bin/env bash
# Creates the secret files used by docker-compose.prod.yml. Never overwrites an existing file.
#   ./scripts/gen-secrets.sh
# Files go in ./secrets (dir mode 0700, git-ignored). The files themselves are 0444 ON PURPOSE: Docker Compose bind-mounts
# them with their host permissions (it ignores uid/mode outside Swarm) and the app runs as a non-root user, so 0600
# root-owned files would be unreadable by the app. The 0700 directory is what keeps other host users out.
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
mkdir -p secrets && chmod 0700 secrets

make_secret() {            # name, generator-command
  local f="secrets/$1"
  if [ -e "$f" ]; then echo "keep    $f (already exists)"; return; fi
  eval "$2" > "$f"
  chmod 0444 "$f"
  echo "created $f"
}

make_secret SECRET_KEY        'openssl rand -base64 48 | tr -d "\n"'
make_secret POSTGRES_PASSWORD 'openssl rand -hex 32 | tr -d "\n"'
make_secret REDIS_PASSWORD    'openssl rand -hex 32 | tr -d "\n"'
make_secret GRAFANA_PASSWORD  'openssl rand -hex 16 | tr -d "\n"'
make_secret AT_API_KEY        ': '        # empty placeholder: paste your Africa'"'"'s Talking API key into this file

if [ -e secrets/BACKUP_AGE_RECIPIENT ]; then
  echo "keep    secrets/BACKUP_AGE_RECIPIENT (already exists)"
elif command -v age-keygen >/dev/null 2>&1; then
  mkdir -p offline && chmod 0700 offline
  age-keygen -o offline/backup-identity.txt >/dev/null 2>&1
  chmod 0600 offline/backup-identity.txt
  grep "public key" offline/backup-identity.txt | sed 's/.*: //' | tr -d '\n' > secrets/BACKUP_AGE_RECIPIENT
  chmod 0444 secrets/BACKUP_AGE_RECIPIENT
  echo "created secrets/BACKUP_AGE_RECIPIENT (public key) and offline/backup-identity.txt (PRIVATE KEY)"
  echo
  echo "  !! MOVE offline/backup-identity.txt OFF THIS SERVER NOW (password manager + a second safe place)."
  echo "  !! Without it your backups cannot be restored. With it on this server, a break-in could read them."
else
  echo "age-keygen not found: install 'age', run: age-keygen -o backup-identity.txt, then put ONLY the public key"
  echo "(the line 'Public key: age1...') into secrets/BACKUP_AGE_RECIPIENT and keep the identity file offline."
  : > secrets/BACKUP_AGE_RECIPIENT; chmod 0444 secrets/BACKUP_AGE_RECIPIENT
fi
echo
echo "Next: put your Africa's Talking API key in secrets/AT_API_KEY, then edit .env.prod."
