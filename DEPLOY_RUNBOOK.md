# Deploy Runbook — YASAFlaskified

Authoritative operational guide for deploying YASAFlaskified (the Flask app
wrapping `psgscoring` + YASA). Three environments, three methods. This supersedes
the older `DEPLOY.md` for day-to-day operations.

> ⚠️ **Production is a live clinical app.** Production-server operations require
> **explicit per-command authorization** every time. A generic "deploy it" is not
> enough. Never put PHI in git, logs, or chat.

---

## 0. Environments at a glance

| Env | SSH target | App dir | Managed by | Auth gate |
|---|---|---|---|---|
| **Production** | `root@65.108.230.243` (https://slaapkliniek.be) | `/data/slaapkliniek` — **NOT a git checkout** | **rsync** from local repo | **explicit per-command** |
| **Test VM** | `bart@192.168.1.253` (`us01`) | `/data/slaapkliniek` — **git checkout**, owned by `bart` (in `docker` group) | **git fetch + reset** | none (throwaway) |
| **Fresh server** | new Ubuntu 22.04+/Debian | created by the script | **`deploy.sh`** (bootstrap) | — |

Common to all: host **nginx** terminates TLS and reverse-proxies to the app on
`127.0.0.1:8071`; stack = `kliniek_app` (gunicorn) + `kliniek_worker1..8` (RQ) +
`kliniek_redis`. Persistent host dirs: `/data/slaapkliniek/{uploads,processed,logs,instance}`.
Secrets in `/data/slaapkliniek/.env` (never committed). Admin login lives in
`instance/users.db` (the `ADMIN_PASSWORD` in `instance/config.json` is only the
first-init seed).

---

## 1. Pre-flight (every deploy)

1. **Cut the version on `main` first.** Bump `myproject/version.py`
   (`__version__` **and** `PSGSCORING_VERSION`) + add a `CHANGES.md` entry on a
   branch → PR → CI green → merge. `pyproject`-style version drift is caught by
   `deploy.sh` (it syncs `APP_VERSION` to `version.py`).
2. **If the `psgscoring` pin changed:** that version must be **live on PyPI before
   you deploy** — the Docker build does `pip install psgscoring[ml]==X.Y.Z` from
   PyPI. Confirm: `pip index versions psgscoring` or https://pypi.org/project/psgscoring/.
3. **Clinical scoring changes** must pass the psgscoring golden harness + cohort
   validation (q7 + PSG-IPA) **before** they reach production. A pure dependency
   bump where clinical output is byte-identical is safe to ship directly.
4. **Cut a GitHub Release + bump the README release badge.** Create the release
   so it shows up as *Latest*:
   `gh release create vX.Y.Z --target main --title "..." --notes "..."` (notes
   from `CHANGES.md`). Then **update the version in the static release badge** in
   `README.md` — it is intentionally static (`img.shields.io/badge/release-vX.Y.Z-blue`)
   because the dynamic `github/v/release` endpoint intermittently fails with
   *"Unable to select next GitHub token from pool"* (shields.io token-pool rate
   limit). The static badge needs a manual bump per release; an HTML comment next
   to it in `README.md` flags this.

---

## 2. Production deploy (Hetzner) — rsync

Live clinical app. `~10–30 s` downtime at `up -d`. **`.env`, `instance/`,
`uploads/`, `processed/`, `logs/` are never overwritten** (excluded). Run from the
local repo on `main` after the merge.

**Step 1 — dry-run first (no changes; confirm only code files change):**
```bash
cd ~/CODE/YASAFlaskified
rsync -rlptz --checksum --no-owner --no-group --dry-run --itemize-changes \
  --exclude='.git' --exclude='.env' --exclude='instance' --exclude='uploads' \
  --exclude='processed' --exclude='logs' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='.venv' --exclude='*.log' --exclude='node_modules' --exclude='.pytest_cache' \
  --exclude='.ruff_cache' --exclude='.hypothesis' --exclude='.mypy_cache' \
  ~/CODE/YASAFlaskified/ root@65.108.230.243:/data/slaapkliniek/
```
Inspect the list. Expect only code/docs to change — **never** `app.py`/compose/
Dockerfile/nginx unintentionally, and **never** a data dir.

> **Never add `--delete`.** The server holds files that are deliberately absent
> from the repo — `.env` and `myproject/.env` (gitignored), `logs/`,
> `processed/`, and the `myproject_v*_backup/` directories. `--delete` removes
> every one of them, and the stack will not start: `docker compose` fails with
> `env file /data/slaapkliniek/.env not found` and leaves the *previous*
> containers running, so `docker compose ps` still looks healthy while the
> deploy has silently not happened. This occurred on 2026-08-08 during the
> 0.19.11 deploy; recovery was `tar xzf` of the pre-deploy backup, which is
> exactly why step 0 takes one. Copy the command above verbatim rather than
> retyping a shorter one.

**Step 2 — real rsync (drop `--dry-run --itemize-changes`).**

**Step 3 — verify the critical files transferred (md5, both sides):**
```bash
md5sum requirements.txt myproject/version.py myproject/generate_pdf_report.py
ssh root@65.108.230.243 'cd /data/slaapkliniek && md5sum requirements.txt myproject/version.py myproject/generate_pdf_report.py'
```

**Step 4 — on the server: sync APP_VERSION, clear caches, rebuild, restart:**
```bash
ssh root@65.108.230.243 'set -e
cd /data/slaapkliniek
NEWV=$(grep -oE "\"[0-9][^\"]*\"" myproject/version.py | head -1 | tr -d "\"")
sed -i -E "s|^APP_VERSION=.*|APP_VERSION=${NEWV}|" .env && grep ^APP_VERSION= .env
find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
docker compose build          # pulls the pinned psgscoring from PyPI
docker compose up -d          # brief downtime while containers recreate
'
```

**Step 5 — verify (see §5). Step 6 — remove the old image** once healthy:
```bash
ssh root@65.108.230.243 'docker rmi yasaflaskified:<OLD_VERSION>'
```

---

## 3. Test VM deploy (192.168.1.253) — git

Sudo-free (`bart` owns the checkout and is in the `docker` group). Use this to
test a branch end-to-end before merging it.

```bash
ssh bart@192.168.1.253 'set -e
cd /data/slaapkliniek
git fetch -q origin
git checkout -B <branch-or-main> origin/<branch-or-main>   # e.g. main, or perf/...
NEWV=$(grep -oE "\"[0-9][^\"]*\"" myproject/version.py | head -1 | tr -d "\"")
sed -i -E "s|^APP_VERSION=.*|APP_VERSION=${NEWV}|" .env && grep ^APP_VERSION= .env
find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
docker compose build
docker compose up -d
'
ssh bart@192.168.1.253 'docker rmi yasaflaskified:<OLD_VERSION> 2>/dev/null || true'
```
Note: the VM may sit on an **unmerged branch** while testing — remember to put it
back on `main` after the change is merged.

---

## 4. Fresh server / purge — `deploy.sh` & `redeploy.sh`

**Fresh install (bootstrap):** creates the app user, installs Docker/nginx/certbot,
clones the repo, generates `.env` + `instance/config.json` (random admin password,
printed once), builds and starts. Version-agnostic (installs whatever
`version.py` declares).
```bash
curl -sSL https://raw.githubusercontent.com/bartromb/YASAFlaskified/main/deploy.sh \
  | sudo YASA_USER=<user> bash
```
**Purge + reinstall (TEST/throwaway only — destructive, wipes all data + admin pw):**
```bash
curl -sSL https://raw.githubusercontent.com/bartromb/YASAFlaskified/main/redeploy.sh \
  | sudo YASA_USER=<user> YASA_PURGE_CONFIRM=yes bash
```

---

## 5. Verify (every deploy)

```bash
docker compose ps                                              # all "healthy"/"Up"
docker compose exec -T app python -c "import version,psgscoring; \
  print('app',version.__version__,'| psgscoring',psgscoring.__version__)"
curl -fsS localhost:8071/          -o /dev/null -w '/          -> %{http_code}\n'   # 200
curl -s   localhost:8071/dashboard -o /dev/null -w '/dashboard -> %{http_code}\n'   # 302 (login-gated = registered)
```
Production also: `curl -fsS https://slaapkliniek.be/ -o /dev/null -w '%{http_code}\n'` → `200`.
Expected route codes: `/`=200, login-gated routes=302, POST-only routes=405 on GET.
(`404` ⇒ wrong port or route missing — `curl localhost/` hits nginx, not the app.)

---

## 5b. The job registry: history, and what is still open

Steps 1–3 are **history** — the `job` table shipped in v0.17.0 and the backfill
has run. They stay here because they document why the table exists and what
`deploy.sh` still does idempotently on every deploy.

Steps 4–6 and the cookie note at the end are **still open on production**; see
`docs/opm20260809.txt` §D2.

The order matters: the access check is only as good as the table it reads, and
the table starts empty.

1. **Back up before anything else** — this release adds a table and starts
   writing to it:
   ```bash
   ssh root@65.108.230.243 'cd /data/slaapkliniek && \
     cp instance/users.db instance/users.db.bak-$(date +%F) && \
     tar czf /root/uploads-$(date +%F).tgz uploads'
   ```
2. **Deploy** as in §2. `initialize_database()` runs at container start and
   `db.create_all()` creates the `job` table; no manual migration, no Alembic.
3. **Run the backfill** and keep the output — it lists exactly which studies had
   no traceable owner:
   ```bash
   cd /data/slaapkliniek && docker compose exec -T app python -m backfill_jobs
   ```
   (`python -m backfill_jobs`, not `-m myproject.backfill_jobs` — the image's
   WORKDIR is `/data/slaapkliniek/myproject` and there is no `myproject` package
   inside it.)
4. **Watch the logs for a few days.** Every job still falling back to the JSON
   logs a warning with its `job_id`:
   ```bash
   docker compose logs app | grep 'job access fallback'
   ```
   Re-running the backfill is safe and fixes anything that appears here.
5. **Only when that stays empty**, tighten: set `"JOB_ACCESS_STRICT": "1"` in
   `instance/config.json` and `docker compose restart app`. From then on an
   unknown `job_id` is a `404`.
6. **Rollback** for this step alone: set it back to `"0"` and restart — the JSON
   fallback resumes immediately. No data change is involved either way.

**Known edge case:** a study that was uploaded but not yet submitted for
analysis at the moment of the restart has no `job` row *and* no config JSON yet,
so its owner is denied on `/channel-select/<job_id>`. The backfill cannot repair
this (there is nothing on disk to read). The window is the restart itself; the
fix is to upload again.

**Unrelated but worth doing in the same maintenance window:**
`instance/config.json` on production likely has `"SESSION_COOKIE_SECURE": true`
(a JSON boolean copied from the old template). The app tests
`_cfg("SESSION_COOKIE_SECURE", "0") == "1"`, so a boolean leaves the secure flag
**off**. Change it to the string `"1"` and restart. `deploy.sh` never overwrites
an existing `instance/config.json`, so shipping code does not fix this.

---

## 6. Rollback

The previous image is kept until you `docker rmi` it. To roll back:
- **Prod:** rsync the previous code (or restore the previous `version.py`), set
  `.env APP_VERSION` to the previous tag, `docker compose build && up -d`. Or, if
  the old image is still present, just point `APP_VERSION` at it and `up -d`.
- **Test VM:** `git checkout <previous-commit>` + bump `.env` + rebuild + up.
- Patient data is untouched by any of this (data dirs are not part of the deploy).

---

## 7. Gotchas (why each step exists)

- **Rebuild after ANY Python change.** Python files are `COPY`'d at image-build
  time, not bind-mounted; `restart`/`up` alone keeps the OLD code. `docker cp` is
  not durable (overwritten on next build).
- **Clear `__pycache__`** — stale `.pyc` survive container restarts.
- **`APP_VERSION` must equal `version.py`** or compose builds/starts the wrong
  image tag and the update silently doesn't take effect. `deploy.sh` auto-syncs
  this; the manual rsync/git paths must `sed` it (done in the steps above).
- **`psgscoring` is installed from PyPI at build time** → publish it first.
- **rsync:** always `--checksum` (the default size+mtime heuristic silently skips
  changed files of equal size+mtime), `--no-owner --no-group` (uid/gid differ),
  **never `--delete`**, always exclude the data dirs + `.env`, and md5-verify.
- **Admin login** is in `instance/users.db`; `config.json`'s `ADMIN_PASSWORD` is
  only the init seed. To reset: update the `user` table with a `werkzeug`
  `generate_password_hash` (parameterised `sqlite3`, never string-interpolate the
  `$`-laden hash into SQL).
- **Reading patient data over SSH** (DB rows, uploads) is a separate action that
  needs its own explicit authorization — it is not covered by a deploy go-ahead.
