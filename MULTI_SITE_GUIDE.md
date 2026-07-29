# Multi-Site Architectuur: Hetzner Server
# sleepai.be/eu (v6) + slaapkliniek.be (v7.5)

## Overzicht

```
Hetzner Server (1 machine)
├── Host Nginx (poort 80/443 + Let's Encrypt SSL)
│   ├── sleepai.be / sleepai.eu    → 127.0.0.1:8060
│   └── slaapkliniek.be            → 127.0.0.1:8071
│
├── /data/sleepai/        ← v6 Docker stack
│   └── docker-compose.yml (Redis + App + Worker)
│       app exposed: 127.0.0.1:8060
│
└── /data/slaapkliniek/   ← v7.5 Docker stack
    └── docker-compose.yml (Redis + App + Worker)
        app exposed: 127.0.0.1:8071
```

> **Twee betekenissen van "site".** Hierboven gaat het over **hostingstacks**:
> twee losse Docker-stacks met eigen database en eigen volumes op één machine.
> Daarnaast kent één stack **klinische sites** (de `site`-tabel): meerdere
> centra binnen dezelfde installatie, die elkaars studies niet mogen zien. Dat
> tweede model staat hieronder en is puur applicatielogica.

## Toegangsmodel (klinische sites binnen één stack)

Elke studie heeft een `job_id`. Wie die mag openen wordt bepaald door de
**`job`-tabel in de database** — niet langer door de JSON-bestanden op schijf.

### De regel

Toegang tot een `job_id` als **één** van deze klopt:

| Voorwaarde | Toegang |
|---|---|
| `current_user.role == "admin"` | ja — alle sites |
| `job.owner_username == current_user.username` | ja — ook als de job bij een andere site hoort |
| `job.site_id == current_user.site_id` (en niet `None`) | ja — zelfde centrum |
| geen van bovenstaande | nee |

De eigenaar behoudt dus toegang tot zijn eigen studies, ook na een overstap
naar een andere site. Dat sluit aan bij wat het dashboard altijd al toonde
(`_filter_studies_for_user`); vóór deze wijziging kon een studie wél in de
lijst staan maar 403 geven bij openen.

### Waar het wordt afgedwongen

Elke route met een `<job_id>` draagt `@job_access_required`:

```python
@app.route("/results/<job_id>")
@login_required
@job_access_required
def show_results(job_id):
    ...
```

Dat zijn ze **alle 30** — niet alleen de routes die het rapport tonen, maar ook
`/channel-select/`, `/status/`, de scoring-API's en de EDF-browser-endpoints.
Een testcase loopt over `app.url_map` en faalt zodra er een `<job_id>`-route
bijkomt zonder de decorator, zodat dit niet stil kan wegzakken.

### Waarom een tabel en niet de JSON

`_get_job_site_id()` opende `{job_id}_results.json`, parste JSON en had een
`except Exception: pass` die stil `None` teruggaf. Elke controle was daarmee
best-effort: onleesbare of ontbrekende metadata leidde niet tot weigeren maar
tot een onbepaalde uitkomst. De JSON-velden blijven bestaan (de workers
schrijven ze), maar autorisatie hangt er niet meer aan.

De `job`-rij wordt **alleen door de webapp** geschreven — bij `parse_file()`
(zodra het `job_id` ontstaat) en bijgewerkt bij `/analyze`. De RQ-workers raken
de database niet aan; dat voorkomt SQLite-lockcontentie met 8 workers.

### JOB_ACCESS_STRICT

Overgangsvlag in `instance/config.json` (of als `YASAFLASKIFIED_JOB_ACCESS_STRICT`):

| Waarde | Job zonder rij in de `job`-tabel |
|---|---|
| `"0"` (default) | terugvallen op de JSON-bestanden, mét een `job access fallback`-waarschuwing in het log |
| `"1"` | `404` |

De volgorde is: deployen → backfill draaien → logs volgen tot er geen
fallback-waarschuwingen meer zijn → pas dán `"1"`. De fallback gebruikt exact
dezelfde toegangsregel, dus de overgang maakt geen gat: hij is permissief over
het *bestaan* van de rij, niet over wie er binnen mag.

```bash
# resterende legacy studies zichtbaar maken
docker compose logs app | grep 'job access fallback'

# ontbrekende rijen alsnog aanmaken (idempotent)
docker compose exec app python -m backfill_jobs
```

## Stap 1: Directory structuur

```bash
sudo mkdir -p /data/sleepai /data/slaapkliniek
sudo chown $USER:$USER /data/sleepai /data/slaapkliniek
```

## Stap 2: v6 (sleepai.be) docker-compose aanpassen

`/data/sleepai/docker-compose.yml` — verwijder Nginx service, expose app op 8060:

```yaml
services:
  redis-v6:
    image: redis:7-alpine
    container_name: sleepai_redis
    restart: unless-stopped
    volumes:
      - sleepai_redis:/data
    networks:
      - sleepai_net

  app-v6:
    image: yasaflaskified-v6:latest
    container_name: sleepai_app
    restart: unless-stopped
    ports:
      - "127.0.0.1:8060:5000"    # ALLEEN lokaal bereikbaar
    env_file: .env
    environment:
      - YASAFLASKIFIED_REDIS_HOST=redis-v6
    volumes:
      - sleepai_uploads:/data/yasa/uploads
      - sleepai_db:/data/yasa/instance
      - sleepai_logs:/data/yasa/logs
    depends_on:
      - redis-v6
    networks:
      - sleepai_net

  worker-v6:
    image: yasaflaskified-v6:latest
    container_name: sleepai_worker
    restart: unless-stopped
    command: rq worker --url redis://redis-v6:6379 default
    env_file: .env
    environment:
      - YASAFLASKIFIED_REDIS_HOST=redis-v6
    volumes:
      - sleepai_uploads:/data/yasa/uploads
      - sleepai_db:/data/yasa/instance
      - sleepai_logs:/data/yasa/logs
    depends_on:
      - redis-v6
    networks:
      - sleepai_net

  # GEEN Nginx service — host Nginx doet dit

volumes:
  sleepai_redis:
  sleepai_uploads:
  sleepai_db:
  sleepai_logs:

networks:
  sleepai_net:
    driver: bridge
```

## Stap 3: v7.5 (slaapkliniek.be) docker-compose

`/data/slaapkliniek/docker-compose.yml`:

```yaml
services:
  redis-v75:
    image: redis:7-alpine
    container_name: kliniek_redis
    restart: unless-stopped
    volumes:
      - kliniek_redis:/data
    networks:
      - kliniek_net

  app-v75:
    image: yasaflaskified-v75:latest
    container_name: kliniek_app
    restart: unless-stopped
    ports:
      - "127.0.0.1:8071:5000"    # ALLEEN lokaal bereikbaar
    env_file: .env
    environment:
      - YASAFLASKIFIED_REDIS_HOST=redis-v75
    volumes:
      - kliniek_uploads:/data/yasa/uploads
      - kliniek_processed:/data/yasa/processed
      - kliniek_db:/data/yasa/instance
      - kliniek_logs:/data/yasa/logs
      - kliniek_mpl:/data/yasa/.mplconfig
      - kliniek_numba:/data/yasa/.numba_cache
    depends_on:
      - redis-v75
    networks:
      - kliniek_net

  worker-v75:
    image: yasaflaskified-v75:latest
    container_name: kliniek_worker
    restart: unless-stopped
    command: rq worker --url redis://redis-v75:6379 default
    env_file: .env
    environment:
      - YASAFLASKIFIED_REDIS_HOST=redis-v75
    volumes:
      - kliniek_uploads:/data/yasa/uploads
      - kliniek_processed:/data/yasa/processed
      - kliniek_db:/data/yasa/instance
      - kliniek_logs:/data/yasa/logs
      - kliniek_mpl:/data/yasa/.mplconfig
      - kliniek_numba:/data/yasa/.numba_cache
    depends_on:
      - redis-v75
    networks:
      - kliniek_net

volumes:
  kliniek_redis:
  kliniek_uploads:
  kliniek_processed:
  kliniek_db:
  kliniek_logs:
  kliniek_mpl:
  kliniek_numba:

networks:
  kliniek_net:
    driver: bridge
```

## Stap 4: Host Nginx installeren

```bash
sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx
```

## Stap 5: Nginx vhosts configureren

### sleepai.be + sleepai.eu

```bash
sudo tee /etc/nginx/sites-available/sleepai << 'EOF'
server {
    listen 80;
    server_name sleepai.be www.sleepai.be sleepai.eu www.sleepai.eu;

    client_max_body_size 520M;

    location / {
        proxy_pass http://127.0.0.1:8060;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
EOF
```

### slaapkliniek.be

```bash
sudo tee /etc/nginx/sites-available/slaapkliniek << 'EOF'
server {
    listen 80;
    server_name slaapkliniek.be www.slaapkliniek.be;

    client_max_body_size 520M;

    location / {
        proxy_pass http://127.0.0.1:8071;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
EOF
```

### Activeer en test

```bash
sudo ln -sf /etc/nginx/sites-available/sleepai /etc/nginx/sites-enabled/
sudo ln -sf /etc/nginx/sites-available/slaapkliniek /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

## Stap 6: SSL met Let's Encrypt

```bash
# DNS moet eerst wijzen naar de Hetzner server IP!
sudo certbot --nginx -d sleepai.be -d www.sleepai.be -d sleepai.eu -d www.sleepai.eu
sudo certbot --nginx -d slaapkliniek.be -d www.slaapkliniek.be

# Auto-renewal
sudo systemctl enable certbot.timer
```

## Stap 7: Starten

```bash
# v6
cd /data/sleepai
docker compose up -d --build

# v7.5
cd /data/slaapkliniek
docker compose up -d --build

# Check
curl -s -o /dev/null -w "%{http_code}" http://localhost:8060/login   # v6
curl -s -o /dev/null -w "%{http_code}" http://localhost:8071/login   # v7.5
```

## Geen conflicten

- Elke stack heeft eigen Redis (geen key-overlap)
- Elke stack heeft eigen Docker volumes (gescheiden data)
- Elke stack heeft eigen container-namen (geen Docker naamconflicten)
- Elke stack heeft eigen Docker netwerk (geen port-conflicten)
- Host Nginx routeert op basis van domeinnaam
- Let's Encrypt beheert SSL per domein

## Firewall

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

## Monitoring

```bash
# Logs v6
cd /data/sleepai && docker compose logs -f worker --tail=10

# Logs v7.5
cd /data/slaapkliniek && docker compose logs -f worker --tail=10

# Nginx
sudo tail -f /var/log/nginx/access.log
```
