# YASAFlaskified v0.8.23 — Installatiegids

> **Screeningtool — niet CE-gekeurd of FDA-cleared voor klinische diagnose.**
> Enkel voor onderzoek en screening.

---

## Inhoudsopgave

1. [Systeemvereisten](#1-systeemvereisten)
2. [Snelle installatie (Docker)](#2-snelle-installatie-docker)
3. [Stap-voor-stap: nieuwe server](#3-stap-voor-stap-nieuwe-server)
4. [Update naar v0.8.23](#4-update-van-update-naar-v0823)
5. [Nginx + SSL instellen](#5-nginx--ssl-instellen)
6. [Configuratie](#6-configuratie)
7. [Eerste login en gebruikersbeheer](#7-eerste-login-en-gebruikersbeheer)
8. [Dagelijks beheer](#8-dagelijks-beheer)
9. [Probleemoplossing](#9-probleemoplossing)
10. [Wat er veranderd is in v0.8.23](#10-wat-er-veranderd-is-in-v0823)

---

## 1. Systeemvereisten

| Component | Minimum | Aanbevolen |
|---|---|---|
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8 GB |
| Schijf | 40 GB | 100 GB SSD |
| Docker | 24.0+ | 27.0+ |
| Docker Compose | 2.20+ | 2.27+ |

**Python wordt NIET lokaal vereist** — alles draait in Docker-containers.

De `psgscoring library (v0.2.4) is meegeleverd in de zip als
`myproject/psgscoring/` en vereist geen aparte `pip install`.

---

## 2. Snelle installatie (Docker)

```bash
# 1. Uitpakken
unzip YASAFlaskified_0_8_5.zip
cd YASAFlaskified_v0_8_23

# 2. Configuratie aanmaken
cp config.json.example config.json
# Pas SECRET_KEY en ADMIN_PASSWORD aan in config.json (zie sectie 6)

# 3. Omgevingsvariabelen aanmaken
echo "SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')" > .env

# 4. Datamappen aanmaken
sudo mkdir -p /data/slaapkliniek/{uploads,processed,logs,instance}

# 5. Bouwen en starten
docker compose build
docker compose up -d

# 6. Status controleren
docker compose ps
docker compose logs app --tail=20
```

De app is bereikbaar op **http://localhost:8071**.

---

## 3. Stap-voor-stap: nieuwe server

### 3.1 Docker installeren (Ubuntu)

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) \
  signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
                    docker-buildx-plugin docker-compose-plugin

# Huidige gebruiker toevoegen aan docker-groep (herstart sessie nadien)
sudo usermod -aG docker $USER
```

Herstart je SSH-sessie of voer `newgrp docker` uit.

### 3.2 Bestanden plaatsen

```bash
# Maak werkmap aan
sudo mkdir -p /data/slaapkliniek
sudo chown $USER:$USER /data/slaapkliniek

# Kopieer de uitgepakte bestanden
cp -r YASAFlaskified_v0_8_23/* /data/slaapkliniek/
cd /data/slaapkliniek

# Datamappen aanmaken
mkdir -p uploads processed logs instance
```

### 3.3 Configuratie aanmaken

```bash
cp config.json.example config.json

# Genereer een veilige SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Pas `config.json` aan:

```json
{
  "SECRET_KEY": "plak hier de gegenereerde sleutel",
  "ADMIN_PASSWORD": "kies een sterk wachtwoord",

  "UPLOAD_FOLDER":           "/data/slaapkliniek/uploads",
  "PROCESSED_FOLDER":        "/data/slaapkliniek/processed",
  "SQLALCHEMY_DATABASE_URI": "sqlite:////data/slaapkliniek/instance/users.db",
  "LOG_FILE":                "/data/slaapkliniek/logs/app.log",

  "REDIS_HOST": "redis",
  "REDIS_PORT": 6379,

  "site": {
    "name":    "Naam van uw instelling",
    "address": "Adres",
    "phone":   "Telefoonnummer",
    "email":   "email@instelling.be",
    "url":     "https://uw-domein.be"
  }
}
```

Maak ook het `.env` bestand aan (vereist door docker-compose):

```bash
echo "SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')" > .env
```

### 3.4 Starten

```bash
cd /data/slaapkliniek

# Image bouwen (5-10 min bij eerste keer)
docker compose build

# Op de achtergrond starten
docker compose up -d

# Wachten tot app gezond is (kan 60s duren)
docker compose logs app -f --tail=30
```

Verwachte output:

```
kliniek_redis    running (healthy)
kliniek_app      running (healthy)
kliniek_worker   running
```

---

## 4. Update naar v0.8.23

**Geen database-migratie nodig.** De datastructuur is ongewijzigd.

```bash
cd /data/slaapkliniek

# 1. Containers stoppen (data blijft bewaard via volumes)
docker compose down

# 2. Nieuwe bestanden kopiëren
#    config.json en .env NIET overschrijven
cp -r /pad/naar/YASAFlaskified_v0_8_23/myproject ./
cp /pad/naar/YASAFlaskified_v0_8_23/docker-compose.yml ./
cp /pad/naar/YASAFlaskified_v0_8_23/Dockerfile ./
cp /pad/naar/YASAFlaskified_v0_8_23/requirements.txt ./

# 3. Nieuw image bouwen en starten
docker compose build
docker compose up -d

# 4. Controleer dat psgscoring geladen is
docker compose exec app python3 -c \
  "import psgscoring; print('psgscoring', psgscoring.__version__, 'OK')"
```

Verwachte output: `psgscoring 0.2.4 OK`

Uw `config.json`, `.env`, en alle data in `uploads/`, `processed/` en
`instance/` (database) blijven volledig intact bij een update.

---

## 5. Nginx + SSL instellen

### 5.1 Nginx installeren

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

### 5.2 Nginx-configuratie plaatsen

```bash
sudo cp nginx-host/slaapkliniek.conf /etc/nginx/sites-available/slaapkliniek
sudo ln -sf /etc/nginx/sites-available/slaapkliniek \
            /etc/nginx/sites-enabled/slaapkliniek
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

Pas de domeinnaam aan in `nginx-host/slaapkliniek.conf`:

```nginx
server_name uw-domein.be www.uw-domein.be;
```

### 5.3 SSL-certificaat (Let's Encrypt)

```bash
# DNS moet al naar uw server wijzen
sudo certbot --nginx -d uw-domein.be -d www.uw-domein.be

# Automatische vernieuwing testen
sudo certbot renew --dry-run
```

### 5.4 Firewall

```bash
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

Poort 8071 hoeft **niet** open te staan — Nginx routeert intern.

---

## 6. Configuratie

### Overzicht config.json opties

| Sleutel | Standaard | Beschrijving |
|---|---|---|
| `SECRET_KEY` | — | **Verplicht wijzigen.** Flask sessie-encryptie |
| `ADMIN_PASSWORD` | — | **Verplicht wijzigen.** Wachtwoord admin-account |
| `MAX_CONTENT_LENGTH` | 524288000 (500 MB) | Max EDF-bestandsgrootte |
| `SESSION_LIFETIME_HOURS` | 24 | Automatisch uitloggen na inactiviteit |
| `SESSION_COOKIE_SECURE` | true | HTTPS vereist (zet op `false` bij lokaal testen) |
| `JOB_TIMEOUT_SECONDS` | 900 | Max analysetijd per EDF (15 min) |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `site.name` | Slaapkliniek AZORG | Naam in rapporten en e-mails |
| `site.logo_path` | `AZORG_rood.png` | Logo in `static/logos/` |
| `site.url` | https://www.slaapkliniek.be | URL voor FHIR-exports |

### Lokaal testen (zonder HTTPS)

```json
"SESSION_COOKIE_SECURE": false,
"DEBUG": true
```

---

## 7. Eerste login en gebruikersbeheer

### Inloggen

- **Gebruikersnaam:** `admin`
- **Wachtwoord:** waarde van `ADMIN_PASSWORD` in `config.json`

### Rollen

| Rol | Bevoegdheden |
|---|---|
| `admin` | Alle data, alle gebruikers, alle sites |
| `site` | Eigen site beheren, gebruikers aanmaken voor eigen site |
| `user` | Eigen site: uploaden, analyseren, rapporten bekijken |

### EDF anonimiseren voor upload

```bash
# Via EDFbrowser: Patient -> Anonymize
# Of via Python:
python3 -c "
import mne
raw = mne.io.read_raw_edf('studie.edf', preload=False)
raw.anonymize()
raw.export('studie_anon.edf', overwrite=True)
"
```

---

## 8. Dagelijks beheer

```bash
cd /data/slaapkliniek

# Starten / stoppen
docker compose up -d
docker compose down
docker compose restart worker

# Logs bekijken
docker compose logs worker -f --tail=50
docker compose logs app -f --tail=30
docker compose logs worker 2>&1 | grep -E "ERROR|CRITICAL"

# Analyseresultaten opruimen (oudere dan 90 dagen)
find /data/slaapkliniek/processed -name "*.json" -mtime +90 -delete

# Schijfruimte
du -sh /data/slaapkliniek/uploads /data/slaapkliniek/processed

# Backup
cp /data/slaapkliniek/instance/users.db ~/backup/users_$(date +%Y%m%d).db
cp /data/slaapkliniek/config.json ~/backup/
```

---

## 9. Probleemoplossing

### App start niet op

```bash
docker compose logs app --tail=50
```

| Fout | Oplossing |
|---|---|
| `Address already in use` | `sudo lsof -i :8071` om te zien wat poort 8071 gebruikt |
| `No such file: config.json` | `cp config.json.example config.json` en invullen |
| `SECRET_KEY too short` | Minimaal 32 tekens vereist |
| `Permission denied /data/...` | `sudo chown -R $USER /data/slaapkliniek` |

### psgscoring niet gevonden

```bash
# Controleer in de container
docker compose exec app python3 -c \
  "import psgscoring; print(psgscoring.__version__)"

# Controleer PYTHONPATH
docker compose exec app env | grep PYTHONPATH

# Controleer of de map aanwezig is
docker compose exec app ls myproject/psgscoring/
```

De waarde `PYTHONPATH=/data/slaapkliniek/myproject` moet aanwezig zijn.
Zo niet: herbouw het image met `docker compose build`.

### Worker verwerkt geen jobs

```bash
docker compose logs worker --tail=30
docker compose exec worker redis-cli -h redis ping
# Verwacht: PONG
docker compose restart worker
```

### Analyse time-out (> 15 min EDF)

```json
"JOB_TIMEOUT_SECONDS": 1800
```

Herstart na wijziging: `docker compose restart app worker`

### Upload mislukt (413 error)

```json
"MAX_CONTENT_LENGTH": 1073741824
```

En in `nginx-host/slaapkliniek.conf`:
```nginx
client_max_body_size 1024M;
```

Herstart: `docker compose restart app && sudo systemctl reload nginx`

---

## 10. Wat er veranderd is in v0.8.23

De monolithische `pneumo_analysis.py` (2 439 regels) is gesplitst in het
modulaire `psgscoring`-pakket (`myproject/psgscoring/`):

```
constants.py  (76)   AASM-drempelwaarden, kanaalpatronen
utils.py     (134)   helpers, sleep mask, kanaaldetectie
signal.py    (307)   preprocessing: linearisatie, MMSD, envelopes, baselines
breath.py    (254)   breath-by-breath segmentatie, flattening index
classify.py  (228)   apnea-type classificatie (obstr/centraal/gemengd)
spo2.py      (218)   SpO2-koppeling Rule 1A, ODI, desaturatie-detectie
plm.py       (271)   PLM-detectie AASM 2.6
ancillary.py (277)   positie, hartritme, snurken, Cheyne-Stokes
respiratory.py(694)  event-detectie, Rule 1B, samenvatting
pipeline.py  (334)   MNE-facing master function
__init__.py  (110)   publieke API (33 symbolen)
```

**Backward compatibel:** alle bestaande `from pneumo_analysis import ...`
werken ongewijzigd. Geen database-migratie. Geen wijziging in analyses.

**psgscoring is geen pip-package** (nog niet gepubliceerd). De library
is gebundeld in `myproject/psgscoring/` en beschikbaar via
`PYTHONPATH=/data/slaapkliniek/myproject` (ingesteld in Dockerfile,
docker-compose.yml, wsgi.py en worker.py).

---

## Snelreferentie

```bash
docker compose up -d                          # starten
docker compose down                           # stoppen
docker compose logs worker -f --tail=50       # analyses volgen
docker compose ps                             # status
docker compose build && docker compose up -d  # herbouwen na update
docker compose exec app python3 -c \
  "import psgscoring; print(psgscoring.__version__)"  # versie controleren
du -sh /data/slaapkliniek/*/                  # schijfruimte
```

---

*YASAFlaskified v0.8.23 — Bart Rombaut MD, Slaapkliniek AZORG, Aalst*
*www.slaapkliniek.be — Niet CE-gekeurd. Enkel voor screening.*
