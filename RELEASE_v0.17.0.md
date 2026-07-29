# Release v0.17.0 — deploy checklist (job registry + upload/access hardening)

Eenmalige checklist voor **deze** release. De algemene procedure staat in
[DEPLOY_RUNBOOK.md](DEPLOY_RUNBOOK.md); hier staat wat er specifiek voor
v0.17.0 bij komt, in de volgorde waarin het moet gebeuren.

> ⚠️ **Productie is een draaiende klinische app.** Elke serveroperatie vraagt
> **expliciete toestemming per commando** — een algemeen "deploy maar" is niet
> genoeg (DEPLOY_RUNBOOK.md, kop). Nooit PHI in git, logs of chat.

---

## 0. Verandert deze release de scoring?

**Nee.** Belangrijk om vooraf vast te leggen, want het bepaalt hoe zwaar de
klinische verificatie achteraf moet zijn.

| | |
|---|---|
| `requirements.txt` | **ongewijzigd** — pin blijft `psgscoring[ml]==0.12.1`, exact wat productie nu draait |
| scoring-/rapport-/i18n-bestanden | **geen enkele aangeraakt** (`pneumo_analysis`, `yasa_analysis`, `tasks.py`, `generate_pdf_report`, `generate_psg_report`, `i18n`, `event_api`) |
| verwachte klinische output | **byte-identiek** — zelfde AHI, zelfde events, zelfde PDF's |

Wat wél verandert: wie een studie mag openen, en de validatie van uploads.

**psgscoring 0.12.3 (PR #17) hoort hier NIET bij.** Die zit in een aparte PR en
bereikt productie alleen als de pin bewust wordt opgehoogd. Die fix verandert
welk signaal aan welke AASM-sensorrol hangt en kán dus resultaten wijzigen op
opnames met een kanaal dat `pres` bevat (wordt dan hypopneesensor in plaats van
pulse) of dat op `pr` matchte als pulse-kanaal. Op PSG-IPA is de output
byte-identiek geverifieerd; **op AZORG-opnames is dat niet gecontroleerd**.
Doe die controle (alleen kanaalnamen van één recente EDF — geen patiëntdata
nodig) vóór de pin ooit omhoog gaat.

---

## 1. Poort: CI groen en gemerged

Niet deployen vanaf de branch.

```bash
gh pr checks 18 --repo bartromb/YASAFlaskified     # Lint / pytest / Docker build
```

Pas na groen mergen naar `main`, dan lokaal `git checkout main && git pull`.
De rsync in stap 3 draait vanuit de lokale repo op `main` — staat die op de
branch, dan zet je ongemergede code op productie.

---

## 2. Back-up eerst

Deze release maakt een tabel aan en begint erin te schrijven. Back-up vóór
alles, niet erna.

```bash
ssh root@65.108.230.243 'cd /data/slaapkliniek && \
  cp instance/users.db instance/users.db.bak-$(date +%F) && \
  tar czf /root/uploads-$(date +%F).tgz uploads && \
  ls -la instance/users.db.bak-* /root/uploads-*.tgz'
```

---

## 3. Deploy (rsync) — zie DEPLOY_RUNBOOK.md §2

Volledige commando's staan daar; kort:

1. **dry-run** met `--itemize-changes` en de lijst nakijken — enkel code/docs,
   nooit een datamap, nooit `.env` of `instance/`
2. echte rsync (zonder `--dry-run`)
3. md5 aan beide kanten vergelijken
4. op de server: `APP_VERSION` synchroniseren naar **0.17.0**, `__pycache__`
   wissen, `docker compose build && up -d`

`initialize_database()` draait bij het opstarten en maakt de `job`-tabel
vanzelf aan — `db.create_all()`, geen handmatige migratie, geen Alembic.

---

## 4. Backfill

Vult de `job`-tabel met de bestaande studies. Idempotent, dus herhalen mag.
`deploy.sh` doet dit automatisch (stap 10/11); bij een rsync-deploy handmatig:

```bash
ssh root@65.108.230.243 'cd /data/slaapkliniek && \
  docker compose exec -T app python -m backfill_jobs'
```

**Bewaar de output.** Hij noemt precies welke studies geen herleidbare
eigenaar hebben.

> `python -m backfill_jobs` — **niet** `-m myproject.backfill_jobs`. De image
> heeft WORKDIR `/data/slaapkliniek/myproject` en daarbinnen bestaat geen
> `myproject`-package; de dotted vorm geeft `ModuleNotFoundError`.

---

## 5. Verifiëren

```bash
ssh root@65.108.230.243 'cd /data/slaapkliniek && docker compose ps'
ssh root@65.108.230.243 'cd /data/slaapkliniek && docker compose exec -T app \
  python -c "import version,psgscoring; print(version.__version__, psgscoring.__version__)"'
# verwacht: 0.17.0 0.12.1
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8071/dashboard   # 302 = geregistreerd
curl -fsS https://slaapkliniek.be/ -o /dev/null -w "%{http_code}\n"        # 200
```

Verwachte codes: `/`=200, login-gated=302, POST-only=405 op GET. Een `404`
betekent verkeerde poort of ontbrekende route.

---

## 6. Meekijken, dagen — niet meteen dichtzetten

Elke job die nog op de JSON-fallback terugvalt logt een waarschuwing met zijn
`job_id`:

```bash
ssh root@65.108.230.243 'cd /data/slaapkliniek && \
  docker compose logs app | grep "job access fallback"'
```

Blijft er iets opduiken, draai de backfill opnieuw (veilig, idempotent).

---

## 7. Pas als het stil blijft: strict zetten

```bash
ssh root@65.108.230.243 'cd /data/slaapkliniek && \
  sed -i "s/\"JOB_ACCESS_STRICT\":.*/\"JOB_ACCESS_STRICT\": \"1\",/" instance/config.json && \
  grep JOB_ACCESS_STRICT instance/config.json && docker compose restart app'
```

Vanaf dan is een onbekend `job_id` een **404**.

**Rollback voor deze stap alleen:** terug op `"0"` en herstarten — de fallback
treedt meteen weer in werking. Geen datawijziging, in geen van beide richtingen.

---

## 8. Handmatig, los van de deploy: SESSION_COOKIE_SECURE

`instance/config.json` op productie heeft vermoedelijk `"SESSION_COOKIE_SECURE": true`
(JSON-boolean, overgenomen uit de oude template). De app test
`_cfg("SESSION_COOKIE_SECURE", "0") == "1"`, dus een boolean laat de vlag
**uit** staan. `deploy.sh` overschrijft een bestaande `instance/config.json`
nooit, dus **geen enkele deploy repareert dit**.

```bash
ssh root@65.108.230.243 'cd /data/slaapkliniek && \
  grep SESSION_COOKIE_SECURE instance/config.json'
# staat er `true` of `1` (zonder aanhalingstekens) -> wijzig naar de STRING "1"
# en daarna: docker compose restart app
```

Zelfde klasse fout als `ENABLE_RATE_LIMITING`: `_cfg()` geeft ruwe
JSON-types of env-strings terug en de vergelijkingen zijn ad hoc. Een
`_cfg_bool()`-helper zou de hele klasse opruimen — aparte taak.

---

## 9. Na afloop

- `HETZNER_CURRENT_STATE.md` bijwerken naar de draaiende versie en de stand van
  `JOB_ACCESS_STRICT`. Dat bestand beschrijft de werkelijkheid op de server en
  wordt bewust **pas na** een echte deploy aangepast.
- Oude image opruimen zodra alles gezond is: `docker rmi yasaflaskified:0.16.5`.
- GitHub Release `v0.17.0` aanmaken (notes uit `CHANGES.md`); de statische
  README-badge staat al op v0.17.0.

---

## Bekende randgevallen

**Upload in de lucht tijdens de herstart.** Een studie die wel geüpload maar
nog niet ingediend was, heeft noch een `job`-rij noch een config-JSON, dus de
eigenaar wordt geweigerd op `/channel-select/<job_id>` en moet opnieuw
uploaden. Het venster is de herstart zelf. De backfill kan dit niet repareren —
er staat niets op schijf om te lezen.

**Toegangsregel is bewust verruimd.** Admin, óf eigenaar, óf zelfde site. Vroeger
telde eigenaar-match alleen als de job géén `site_id` had, terwijl het dashboard
(`_filter_studies_for_user`) eigenaar-match altijd al toestond — een studie kon
dus in iemands lijst staan en 403 geven bij openen. Nu wint de eigenaar in
beide. Bevestigd vóór implementatie.

---

## Alternatief: eerst repeteren op de test-VM

De test-VM (`bart@192.168.1.253`, DEPLOY_RUNBOOK.md §3) is een wegwerpinstantie
en vraagt **geen** productietoestemming. Daar kan de volledige volgorde —
inclusief backfill en `JOB_ACCESS_STRICT=1` — één keer echt doorlopen worden
voordat productie aan de beurt is. Aan te raden bij deze release, omdat het de
eerste is die de toegangscontrole wijzigt.
