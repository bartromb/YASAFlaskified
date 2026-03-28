# YASAFlaskified v14 — Deploy Guide

## Nieuw in v13

- **Artefact-exclusie**: epochs met artefacten worden uitgesloten uit AHI/OAHI berekening
- **OAHI**: Obstructive AHI (obstructief + hypopnea, excl. centraal/gemengd)
- **Arousal module actief**: RERA detectie, arousal-index, RDI berekening
- **EDF patiëntgegevens**: geslacht, geboortedatum automatisch uit EDF header
- **PSG rapport fix**: SpO2 layout crash opgelost
- **Multi-site**: draait naast v6 op dezelfde Hetzner server

## Snel deployen (bestaande v13 server)

```bash
# 1. Bestanden uploaden
cd ~/YASAFlaskifiedv8
# (kopieer alle bestanden hierheen)

# 2. .env aanmaken (eenmalig)
cp .env.example .env
python3 -c "import secrets; print(f'SECRET_KEY={secrets.token_hex(32)}')" >> .env

# 3. Build en start
docker compose build
docker compose up -d

# 4. Logs volgen
docker compose logs -f worker --tail=30
```

## Multi-site deploy (v6 + v8 op Hetzner)

### Stap 1: Directory structuur
```bash
sudo mkdir -p /data/slaapkliniek
cd /data/slaapkliniek
# Kopieer alle v8 bestanden hierheen
```

### Stap 2: Host Nginx installeren
```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo cp nginx-host/slaapkliniek.conf /etc/nginx/sites-available/
sudo cp nginx-host/sleepai.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/slaapkliniek /etc/nginx/sites-enabled/
sudo ln -sf /etc/nginx/sites-available/sleepai /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx
```

### Stap 3: v8 starten
```bash
cd /data/slaapkliniek
cp .env.example .env
python3 -c "import secrets; print(f'SECRET_KEY={secrets.token_hex(32)}')" >> .env
docker compose up -d --build
```

### Stap 4: v6 aanpassen (als die ook Docker gebruikt)
v6 docker-compose moet:
- Poort 80 vrijgeven (host Nginx neemt over)
- App exposen op `127.0.0.1:8060`
- Eigen container/volume namen gebruiken (prefix `sleepai_`)

### Stap 5: SSL
```bash
sudo certbot --nginx -d slaapkliniek.be -d www.slaapkliniek.be
sudo certbot --nginx -d sleepai.be -d www.sleepai.be
```

### Stap 6: DNS
Bij Gandi: A-record voor slaapkliniek.be → Hetzner server IP

## Analyse volgen

```bash
# Volledige worker output
docker compose logs -f worker --tail=30

# Alleen voortgang (filter MNE warnings)
docker compose logs -f worker 2>&1 | grep -E "INFO|ERROR"
```

## Poorten overzicht

| Service | Poort | Doel |
|---------|-------|------|
| Host Nginx | 80/443 | Reverse proxy + SSL |
| v6 app | 127.0.0.1:8060 | sleepai.be/eu |
| v8 app | 127.0.0.1:8071 | slaapkliniek.be |
