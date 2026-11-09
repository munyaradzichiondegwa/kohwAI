# KohwAI — Production Deployment Runbook

Target: **one Linux VPS** running `docker-compose.prod.yml` (Caddy → web + API; PostgreSQL, Redis, Celery worker/beat and an
encrypted-backup job on a private network). Good for a pilot of several thousand farmers; see "Scaling" at the end.

> **Status of this document.** The scripts (secrets generator, backup/restore/restore-drill) and the app's configuration
> checks are covered by automated tests. The Docker images and `docker-compose.prod.yml` were validated statically and the web
> build was exercised outside Docker, but **nobody has yet run `docker compose up` on a real server**. Treat the first
> deployment as a rehearsal on a throw-away VPS, then repeat on the real one.

## 0. Before you touch a server — non-code blockers

| Item | Why it blocks launch |
|---|---|
| Africa's Talking account, **USSD shortcode** + SMS sender, and their callback **source IPs** | No SMS = no login codes and no alerts; empty `USSD_ALLOWED_IPS` rejects all USSD (by design) |
| Real **Agritex / Veterinary Services helpline numbers** | Emergency advice says "your nearest office" until set (`VET_SERVICES_CONTACT`, `AGRITEX_CONTACT`) |
| **Agritex / Vet sign-off on the triage rules** (`backend/app/modules/ussd/rules_engine.py`) | Content has not been clinically/agronomically reviewed; coverage is maize, sorghum, cattle, poultry only |
| **Legal text** for Terms of Use + Privacy Policy (`TERMS_URL`, `PRIVACY_URL`) and a decision on whether you must register as a data controller (Zimbabwe's Cyber and Data Protection Act — confirm with a lawyer) | Consent screens link to these; they are summaries, not legal text |
| A **licensed underwriter** before enabling drought-cover enrolment (`musika_insurance_enrollment` flag stays OFF) | The product moves money; payouts are manual and recorded, not automatic |
| A **map-tile provider** (`TILE_URL`) | openstreetmap.org's public tile servers are not for production traffic |

## 1. Server

* Ubuntu 22.04/24.04 LTS, 2 vCPU / 4 GB RAM / 40 GB SSD minimum. A **separate volume or second disk** for `/var/lib/docker`
  or at least for backups is strongly recommended.
* A DNS **A (and AAAA) record** for your domain pointing at the server **before** first start (Let's Encrypt needs it).
* Harden the host:
  ```bash
  adduser deploy && usermod -aG sudo deploy          # then disable root + password SSH in /etc/ssh/sshd_config
  ufw default deny incoming && ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp && ufw allow 443/udp && ufw enable
  apt install -y unattended-upgrades fail2ban
  curl -fsSL https://get.docker.com | sh && usermod -aG docker deploy
  ```
  > Docker publishes container ports by editing iptables **around ufw**. This stack publishes only 80/443 (and loopback-only
  > monitoring ports) so that is fine; if you ever add a `ports:` entry, assume it is public.

## 2. Configure

```bash
git clone https://github.com/<you>/kohwAI.git && cd kohwAI && git checkout <release-tag>
cp .env.prod.example .env.prod && nano .env.prod       # DOMAIN, ACME_EMAIL, AT_*, USSD_ALLOWED_IPS, helplines, TERMS_URL...
./scripts/gen-secrets.sh                                # creates ./secrets/* and an age key pair
```

1. Put your Africa's Talking API key in `secrets/AT_API_KEY` (no quotes, no newline needed).
2. **Move `offline/backup-identity.txt` off the server** (password manager *and* a second safe place) and delete it from the
   server. It is the only way to decrypt backups; the server holds just the public key, so a break-in cannot read old backups.
3. `secrets/` is `0700` and git-ignored; the files inside are `0444` on purpose (Compose ignores uid/mode outside Swarm and the
   app runs as a non-root user). Do not "fix" this to 0600 — the app will fail to start.

## 3. First deploy

```bash
export DC="docker compose -f docker-compose.prod.yml --env-file .env.prod"
$DC config >/dev/null && echo "compose file valid"
$DC up -d --build
$DC ps                                   # all 'healthy'; 'migrate' exited 0
$DC logs api | grep -i "config warning"  # read every warning
curl -fsS https://$DOMAIN/health/ready   # {"status":"ready","database":"ok","redis":"ok"}
```

The API **refuses to start** (and tells you why in its log) if `SECRET_KEY` is weak, debug or the OTP echo is on, the database
uses a default password, or CORS allows localhost. Fix the cause; do not work around it.

Create the first admin (the person must have logged in once, or this creates the account):
```bash
$DC run --rm api python scripts/seed_admin.py 07XXXXXXXX
```
Then log in at `https://$DOMAIN`, open **Admin → Validators** and appoint district validators.

### Smoke test checklist
- [ ] `https://$DOMAIN` loads; HTTP redirects to HTTPS; certificate is valid
- [ ] You receive a login SMS on a real phone; registration shows the consent screen
- [ ] `curl -I https://$DOMAIN/metrics` → 404, `https://$DOMAIN/docs` → 404
- [ ] Africa's Talking USSD callback set to `https://$DOMAIN/api/v1/ussd/callback`; dialling the shortcode shows the menu;
      a request from any other IP is rejected (`curl -X POST .../ussd/callback` → 403)
- [ ] Create a test alert (Admin) for your own district → real-time push in the app, then an SMS
- [ ] `$DC exec backup /opt/backup/backup.sh` succeeds and `ls /backups` (in the container) shows a `.dump.age` file
- [ ] **Restore drill** (section 5) passes

## 4. Operating

| Task | Command |
|---|---|
| Logs | `$DC logs -f --tail=100 api worker beat caddy` |
| Update to a new release | `git fetch && git checkout <tag>`; set `KOHWAI_VERSION=<tag>` in `.env.prod`; **run a backup first** (`$DC exec backup /opt/backup/backup.sh`); `$DC up -d --build` (migrations run automatically before the app starts) |
| Roll back the *code* | `git checkout <previous-tag>`, `KOHWAI_VERSION=<previous-tag>`, `$DC up -d --build`. Migrations are forward-only: if the release included a migration that the old code cannot live with, restore the pre-deploy backup instead (section 5) |
| Run a Python shell / one-off | `$DC run --rm api python ...` |
| Monitoring (optional) | `$DC --profile monitoring up -d`, then SSH-tunnel: `ssh -L 3001:127.0.0.1:3001 -L 9090:127.0.0.1:9090 deploy@server` |
| Alert dispatch status | `$DC exec db psql -U kohwai -c "select status,count(*) from alert_deliveries group by 1"` |

**Never run more than one `beat` container** (every scheduled job would fire twice). Multiple `worker` containers are fine.

### Rotating secrets
* `SECRET_KEY`: replace the file, `$DC up -d` → **everyone is logged out** (tokens signed with the old key are void) and **all PINs stop working** (PINs are keyed with this secret — users reset via *Account → Set a PIN* in the app). Plan it.
* `POSTGRES_PASSWORD`: `ALTER USER kohwai PASSWORD '...'` inside the db container, replace the file, `$DC up -d`.
* `REDIS_PASSWORD` / `AT_API_KEY`: replace the file, `$DC up -d`.

## 5. Backups and restore

* The `backup` container takes an encrypted `pg_dump` daily (02:30 UTC; `BACKUP_CRON`), keeps 14 daily files plus the first of
  each month for 6 months, and takes one immediately on first start. Its healthcheck turns **unhealthy if there has been no
  successful backup in 26 hours**.
* Backups live in the `backups` Docker volume **on the same server**. That protects against mistakes, not against losing the
  server. Set `BACKUP_UPLOAD_CMD` to copy each file off-site (e.g. `aws s3 cp "$1" s3://bucket/kohwai/`) and/or snapshot the
  VPS. The files are encrypted, so storing them anywhere is safe.

### Monthly restore drill (do this; an untested backup is a hope)
```bash
# on your own machine (needs age + postgresql-client), with a copy of a backup file and your PRIVATE key
infrastructure/backup/verify.sh ./backups ./backup-identity.txt        # restores into a scratch DB, checks schema, migration
                                                                         # version and the audit-log triggers, then drops it
```
Expected last line: `verify: OK — backup is restorable`.

### Disaster recovery (new server)
1. Sections 1–2 on the new server; **restore your saved `secrets/` files** (especially `SECRET_KEY` and `POSTGRES_PASSWORD`).
2. `$DC up -d db`, wait for healthy.
3. Copy the newest `.dump.age` + `.sha256` to the server; with the private key available temporarily:
   `infrastructure/backup/restore.sh <file> <identity> kohwai --yes` (run with `PGHOST/PGUSER/PGPASSWORD` pointing at the db).
4. `$DC up -d` (the migrate job brings the schema to the current version), run the smoke tests, **delete the private key from the server**.

Expected data loss: up to 24 hours (since the last backup). Run `pg_dump` more often (change `BACKUP_CRON`) if that is too much.

## 6. Security notes and known gaps (be honest with your board)

* Login codes and alert SMS rely on SMS, which is vulnerable to SIM-swap; USSD identity is the phone number + 4-digit PIN
  (the PIN travels in the USSD session text, which the operator may log). Neither is suitable for moving money — and nothing here
  moves money automatically.
* **Admin accounts have no 2FA yet** (the `totp_secret` column exists; no endpoint). Restrict who is an admin; consider
  putting `/api/v1/*` admin routes behind your VPN until built.
* No WAF, no Caddy-level rate limiting (the app limits OTP requests per phone). Add Cloudflare or the Caddy rate-limit module if
  you see abuse. No Content-Security-Policy header yet.
* Refresh tokens are not rotated or revocable yet; an account deletion/`is_active=false` does stop them working.
* Redis and PostgreSQL are unreachable from outside Docker, but **inside the host** anyone in the `docker` group is effectively root.

## 7. Scaling beyond one server

Split PostgreSQL to a managed database (set `POSTGRES_HOST` and remove the `db` service), run API/worker replicas behind your
own load balancer (Redis is already the shared state; the WebSocket uses Redis pub/sub), keep exactly one `beat`, and move
backups to the provider's snapshots plus the encrypted dumps.
