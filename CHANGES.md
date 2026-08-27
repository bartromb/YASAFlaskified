# v0.36.7 — 2026-08-27 — een verse installatie weigerde een gewone BDF

Pin ongewijzigd (`psgscoring[ml]==0.30.0`); geen gescoorde waarde verandert.
Raakt alleen `deploy.sh` en het runbook.

## `deploy.sh` zette de uploadgrens op 520M

De app staat sinds 0.34.9 **2 GB** toe, juist omdat een BDF ruim de helft groter
is dan dezelfde nacht in EDF. `deploy.sh` schreef nog
`client_max_body_size 520M` in de nginx-configuratie.

Een verse installatie weigerde daardoor een BDF van **553 MB** — één gewone
nacht — met een 413, vóórdat de app het bestand ooit zag. De gebruiker krijgt
dan een foutmelding die niets over zijn bestand zegt, op precies het
bestandstype waarvoor de grens verhoogd was.

Nu `2G`, met `client_body_timeout 600s` erbij. Een test koppelt de nginx-grens
aan `MAX_CONTENT_LENGTH` zodat ze niet opnieuw uit elkaar kunnen lopen.

## Waarom dit nergens opviel

**Productie gebruikt geen host-nginx.** Poort 80/443 worden bediend door
`nginx-proxy-manager` in een container; `systemctl is-active nginx` geeft
`inactive`. Het runbook beweerde het tegendeel.

Het gat bestond dus uitsluitend voor NIEUWE installaties — en dat is precies de
weg waarlangs een ander slaapcentrum binnenkomt. Het runbook is gecorrigeerd,
met de aantekening dat een proxy-instelling op productie in nginx-proxy-manager
hoort en niet in `/etc/nginx/`.

# v0.36.6 — 2026-08-27 — de eenheid volgt de taal van het rapport

Pin ongewijzigd (`psgscoring[ml]==0.30.0`); geen gescoorde waarde verandert.

## `/u` is Nederlands, en stond in elk rapport

`/u` betekent "per uur". Het stond op **37 plaatsen hardgecodeerd** in de
rapportcode, dus ook in Engelse, Franse en Duitse rapporten. De vertaalde
strings deden het wél goed (`"nl": "< 10–15/u", "fr": "< 10–15/h"`), zodat één
Engels rapport beide vormen droeg.

Het viel op doordat een zin die ik zelf had toegevoegd eruit kwam als:

    Severe OSAS without CPAP (AHI 83.5/u ...). On CPAP 1.1/h ...

Twee eenheden in één zin. Nu komt de eenheid uit `unit_per_hour` (nl `/u`, de
rest `/h`). Gemeten op een gerenderd rapport: Engels 40× `/h` en 0× `/u`,
Nederlands 39× `/u` en 0× `/h`.

## Niet aangeraakt: het Nederlandstalige PSG-rapport

`generate_psg_report.py` is één rapport met hardgecodeerde Nederlandse labels
("Drempel", "Ernst", "Bespreking PLM"). Daar is `/u` juist; alleen de eenheden
vertalen zou het inconsistent maken. Een test legt die grens vast.

## Bijvangst: "None %·min/u" in een klinisch rapport

De hypoxic-burden-regel gebruikte `ss.get("hypoxic_burden", "—")`. Die default
komt er NIET als de sleutel bestaat met waarde `None` — en dat is precies wat
het burden-plafond van 0.28.0 doet boven 150. Het rapport toonde dan letterlijk
`None %·min/u`.

Gevonden door het gerenderde rapport op `None` en `nan` te doorzoeken in plaats
van de code te lezen.

# v0.36.5 — 2026-08-27 — de split-notitie stond bij de verkeerde index

Pin ongewijzigd (`psgscoring[ml]==0.30.0`); geen gescoorde waarde verandert.

## De notitie hing achter de OAHI

0.36.4 zette `[split-night — zonder CPAP 83,5/u]` in de classificatiebalk, maar
achter de OAHI in plaats van achter de AHI:

    AHI = 13,7/u -> Mild OSAS | OAHI = 7,8/u -> Mild OSA [split-night — zonder CPAP 83,5/u]

83,5 is een AHI. Zo gelezen is het een obstructieve index, en dat is een ander
getal. De notitie staat nu achter het AHI-label. Een test pint de volgorde vast
in plaats van alleen te controleren dat de notitie ergens staat.

## De criteriatabel classificeerde nog het nachtgemiddelde

`AHI volgens hypopneu-criterium` toont per regel een AHI met een ernstkolom
ernaast. Op een split-night stond daar tweemaal "Mild OSAS" op het
nachtgemiddelde — de derde plek waar hetzelfde gemiddelde als ernstklasse werd
gepresenteerd.

De tabel blijft zoals ze is: ze vergelijkt hypopneucriteria, en daarvoor zijn de
nachtcijfers de juiste. Er staat nu een voetnoot onder die zegt dat deze AHI's
de uren onder CPAP meetellen, met de waarde zonder CPAP erbij.

# v0.36.4 — 2026-08-27 — de samenvatting sprak de kop tegen

Pin ongewijzigd (`psgscoring[ml]==0.30.0`); geen gescoorde waarde verandert.

## Dezelfde fout, één laag dieper

0.36.3 haalde het nachtgemiddelde uit de kop, de studielijst en de grafieken.
De geautomatiseerde samenvatting onderaan bleef `ahi_total` lezen. Op de
aanleidende opname stond daar **"Mild OSAS (AHI 13,7/u)"** terwijl de kop van
hetzelfde rapport 83,5/u zonder CPAP meldde — één rapport dat zichzelf
tegensprak, en de zin die een arts het snelst overneemt.

De samenvatting rust nu op het diagnostische deel:
*"Severe OSAS without CPAP (AHI 83,5/u, significant nocturnal hypoxemia). On
CPAP 1,1/u (split-night; the whole-night average combines both parts)."*

## De ondergrens moest mee

`ahi < 5` gaf "geen significante slaapapneu" en keerde meteen terug — op het
NACHTgemiddelde. Een split-night die gemiddeld onder 5/u uitkomt maar vóór CPAP
zwaar is, werd zo als normaal gerapporteerd. Een test pint dat vast: met een
diagnostisch deel van 60/u naast een nachtgemiddelde van 4,2/u mag daar niet
"no significant sleep apnea" staan.

## De classificatiebalk is gekwalificeerd

`AHI = 13,7/u → Mild OSAS` classificeert een gemiddelde van twee
onvergelijkbare helften. Het getal blijft — AASM schrijft het voor — maar er
staat nu `[split-night — zonder CPAP 83,5/u]` achter.

## Aangetroffen, niet gerepareerd

Het rapport schrijft op **48 plaatsen** een hardgecodeerde `/u`, ook in Engelse,
Franse en Duitse rapporten, en er is geen eenheidssleutel in `i18n`. Mijn nieuwe
zinnen volgen die conventie zodat er niet twee eenheden in één zin staan. De
rapportbrede reparatie is een eigen ingreep en is bewust niet hier meegenomen.

# v0.36.3 — 2026-08-27 — split-night: het gemiddelde uit de kop, de grens op de grafiek

Pin ongewijzigd (`psgscoring[ml]==0.30.0`); geen gescoorde waarde verandert.
Dit gaat over wat het rapport TOONT.

## Eén AHI over een split-night is een gemiddelde van twee onvergelijkbare helften

De kop droeg de nacht-AHI als tweede tegel. Op de casus die dit aanleiding gaf
stond daar eerst "Mild SAS, AHI 10,1/u" terwijl het diagnostische deel op
83,5/u lag. Dat getal is niet zozeer fout als wel betekenisloos: het telt de
uren vóór de titratie samen met de uren eronder, en juist het eerste deel
draagt de diagnose.

De kop toont nu **AHI zonder CPAP** en **AHI met CPAP** naast elkaar. Het
nachtgemiddelde is niet verdwenen — het staat in de split-nightsectie, waar de
context erbij staat.

## Hetzelfde in de studielijst

De lijst toonde per studie één AHI met een ernstbalk. Op een split-night stond
daar het gemiddelde, en de balk kleurde ernaar. Nu staan beide helften er, en
de balk volgt het deel zonder therapie.

Ook `data-sev` volgt dat deel. Anders filtert de lijst op een getal dat nergens
op het scherm staat: een studie die rood oplicht zou uit een filter op "severe"
vallen.

## Een markering waar het tweede deel begint

Op elk nachtpaneel — hypnogram, events, positie, snurken, saturatie — staat nu
een verticale streep op het breekpunt, met het label "start CPAP".

Zonder die streep is een saturatiecurve die halverwege herstelt niet te
onderscheiden van een patiënt die vanzelf beter wordt. De streep loopt via
`_ov_setup`, dat alle vijf de panelen aanmaakt, zodat er geen paneel kan
achterblijven; een test controleert dat alle vijf hem doorgeven.

# v0.36.2 — 2026-08-26 — de pin haalt de segmentreparatie op

**Pin naar `psgscoring[ml]==0.30.0`** (was 0.29.0). Geen wijziging in deze
repo; de reden voor de release zit in de bibliotheek.

## Waarom dit een eigen versie is

0.36.1 stond klaar met een pin op 0.29.0. Die pin dateert van vóór psgscoring
0.30.0, en 0.30.0 bevat de reparatie waar de split-nightsegmenten de
DEFINITIEVE eventlijst tellen in plaats van de lijst zoals die halverwege de
pijplijn was — op de aanleidende opname 108 events in plaats van 71, een
segment-AHI van 127,1/u in plaats van 83,5/u.

Uitrollen met de oude pin zou een release zijn die zijn eigen changelog niet
waarmaakt: het rapport toont dan nog steeds het verkeerde segmentgetal. Een
veld dat de bibliotheek produceert is niet geleverd tot de pin het ophaalt.

# v0.36.1 — 2026-08-26 — het breath-by-breath-paneel is geen referentie

Pin ongewijzigd (`psgscoring[ml]==0.29.0`); geen gescoorde waarde verandert.

## Wat er veranderde

Het paneel "Breath-by-breath analyse" toonde zijn tellingen zonder uitleg,
vlak onder de gescoorde events. Op de Thaise casus stond er **190 apneus**
naast **nul** gescoorde apneus, en dat werd gelezen als bewijs van
onderdetectie — ook door mij, een dag lang.

Gemeten op dertig gewone MESA-opnames loopt de verhouding tussen die telling en
de gescoorde events van **0 % tot 173 %**: op één opname werden er méér events
gescoord dan de ademteller er vond. De twee rekenen per ademteug tegen
verschillende basislijnen; ze meten niet hetzelfde.

Onder het paneel staat nu, in vier talen, dat het een ander instrument is, met
dat gemeten bereik erbij — een waarschuwing zonder getal is een mening, met
0–173 % kan de lezer zelf wegen. En met wat het paneel wél doet: signaalkwaliteit
beoordelen, niet de AHI controleren.

## Ook

`DEPLOY_RUNBOOK` §2 heeft nu een hertrylus om de build. Een net op PyPI gezette
versie is niet meteen op elke CDN-rand aanwezig, en pip faalt dan met een fout
die eruitziet als een echte fout; op 26-08 gebeurde dat drie keer, elke keer
opgelost door opnieuw te bouwen. Met de waarschuwing erbij die er het meest toe
doet: **`up -d` na een gefaalde build herstart de oude image onder een nieuw
`APP_VERSION`** — dan ziet `docker compose ps` er gezond uit terwijl de uitrol
niet gebeurd is.

605 tests.

---

# v0.36.0 — 2026-08-26 — bij een split-night is het diagnostische deel de kop

Pins `psgscoring[ml]==0.29.0`.

**Reported values change** op opnames waar een split-night gedetecteerd of
opgegeven is: de kop-KPI toont dan het **diagnostische deel** met zijn eigen
ernstklasse en kleur, met de nacht-AHI ernaast. Op opnames zonder split
verandert er niets aan de kop.

## Waarom

De nacht-AHI telt diagnostiek én titratie samen en verdunt daarmee precies wat
er gediagnosticeerd moet worden. Op de casus die dit aanleiding gaf stond in de
kop "Mild SAS, AHI 10,1/u" bij een patiënt die de verwijzer als ernstig kende;
het diagnostische deel lag op **44,7/u** — een factor vier.

De nacht-AHI verdwijnt niet: hij komt als tweede tegel te staan, want AASM
schrijft hem voor. Maar de tegel die de ernstklasse draagt, hoort het deel te
tonen waarop de diagnose rust.

## Ook

- **Aandachtspunt bovenaan.** Wie alleen de eerste bladzijde leest, zag geen
  enkel teken dat de nacht in tweeën viel: de split-nightsectie stond pagina's
  verderop. Nu staat er bij de aandachtspunten: "Split-night gedetecteerd
  (therapie vanaf 2:15): de nacht-AHI van 10,1/u telt diagnostiek én titratie
  samen. Diagnostisch deel 44,7/u, onder therapie 3,8/u."
- **De eerlijke AHI wordt gekozen.** Boven een vijfde ongetypeerde events is
  `ahi_total` een onvolledige telling en zegt alleen `ahi_incl_uncertain` iets;
  kop en aandachtspunt kiezen dan die tweede. Een kop die 1,2/u meldt terwijl
  er 70 ongetypeerde apneus onder liggen, is misleidender dan geen kop.
- Een segment met minder dan een half uur slaap draagt de kop niet; dan blijft
  de nacht-AHI leidend.

602 tests.

---

# v0.35.1 — 2026-08-26 — de segment-AHI's staan nu ín het rapport, en een heranalyse geeft een nieuw PDF

Pins `psgscoring[ml]==0.28.1`.

## Split-night: de twee AHI's naast elkaar

De vorige release detecteerde de split en zette het breekpunt in het
provenanceblok, maar de kop bleef "Mild SAS, AHI 10,1/u" terwijl het
diagnostische deel op **83,5/u** lag. Nieuwe sectie in het rapport:

| | Slaap | AHI | AHI incl. ongetypeerd |
|---|---|---|---|
| Diagnostisch deel (vóór therapie) | 51 min | 1,2 /u | **83,5 /u** |
| Onder therapie | 281 min | 0,6 /u | 1,1 /u |

Met twee kwalificaties eronder wanneer ze van toepassing zijn: te weinig slaap
in een segment, en welk aandeel van de events niet getypeerd kon worden (hier
99 % in het diagnostische deel, omdat beide effort-banden waren afgekeurd).

De nacht-AHI blijft in de kop staan zoals AASM hem voorschrijft — maar niet
langer als enige waarheid.

## Heranalyse gaf het OUDE rapport terug

Een heranalyse draait op hetzelfde `job_id` en herschrijft `_results.json`. De
downloadroute regenereert dan en stuurt no-cache-headers, maar de URL blijft
identiek en Firefox serveert een bijlage van een identieke URL uit zijn eigen
cache. Daarvoor bestaat `report_ver()`: de mtime van results.json als `?v=`.

`results_extended.html` linkte als enige zonder die parameter — wie vanaf die
pagina downloadde, kreeg na een heranalyse het vorige rapport. Beide links
(PDF en Excel) zijn gerepareerd, en een test pint het patroon voor álle
sjablonen: de volgende die het vergeet levert precies dezelfde stille fout op.

602 tests.

---

# v0.35.0 — 2026-08-26 — split-night als keuze, en twee montagevlaggen

Pins `psgscoring[ml]==0.28.0`.

**Reported values change** op de profielen die de arousal-classifier draaien:
psgscoring 0.28.0 verschuift arousal-onsets standaard 2,0 s. De indices
veranderen niet (AHI- en RDI-ernstklasse 0/30 op MESA), de getoonde tijdstippen
wel — het provenanceblok meldt dat met "Arousal-onsets verschoven: +2.0 s".

## Split-night is nu een keuze

Op de kanaalpagina: **uit** (default), **automatisch detecteren**, of
**handmatig** met het tijdstip van therapiestart in minuten na opnamestart. De
handmatige waarde wint altijd van de detector — wie erbij was, weet het beter.
Het breekpunt staat in het provenanceblok.

Waarom dit nodig was: één AHI over diagnostiek én titratie verdunt de diagnose.
Op de casus die dit aanleiding gaf las het rapport "Mild SAS, AHI 10,1/u" bij
een patiënt die de verwijzer als ernstig kende; het diagnostische deel had
ODI3 ~60/u.

## Twee vlaggen die een montageprobleem zichtbaar maken

**EEG-topografie.** Spindels horen frontocentraal maximaal, trage golven
frontaal dominant. Staat het dubbel omgekeerd — trage golven occipitaal én
spindels frontaal, elk met een factor 3 — dan komt er een aandachtspunt:
"controleer de kanaallabels en de montage". Alleen vlaggen, nooit corrigeren:
welke twee kanalen verwisseld zijn is van buitenaf niet vast te stellen, en een
gok verplaatst de fout. Op de aanleidende casus was het spindels F4 804 / F3 521
tegen C3 14 / C4 36, en trage golven O1/O2 elk 276 tegen F3 3 — terwijl de
slaapstadiëring op een van die kanalen draaide.

**Positiecodering.** Is `position_mapping_method` niet "coded", dan is de
labelvolgorde een aanname. De positie-AHI-tabel blijft staan, maar met een
voorbehoud eronder en zonder POSA-fenotype. Op die casus lag de patiënt
"vrijwel de hele nacht PRO" met AHI Prone 18,8 tegen Left 8,2 — getallen die
niet te weerleggen zijn.

597 tests.

---

# v0.34.9 — 2026-08-26 — uploadgrens op 2 GB, uit één bron

Pins `psgscoring[ml]==0.27.7` (ongewijzigd). Geen enkele gescoorde waarde
verandert.

## Wat er mis was

`upload.html` droeg zijn eigen `const MAX_SIZE_MB = 500`, volledig los van
`MAX_CONTENT_LENGTH`. Twee getallen die hetzelfde horen te zijn maar apart
onderhouden worden, lopen uiteen: de browser weigerde een bestand dat de server
had aangenomen. Een gebruiker liep er tegenaan met een BDF van 528 MB.

Beide staan nu op **2 GB**, en de uploadpagina's halen de waarde uit de
serverconfiguratie (`MAX_UPLOAD_MB`, afgeleid van `MAX_CONTENT_LENGTH`) in
plaats van uit een eigen getal.

BDF is 24-bit tegen 16-bit voor EDF, dus dezelfde nacht is er ruwweg anderhalf
keer zo groot in. Een opname van 11 uur met 27 kanalen komt op ~550 MB — precies
wat de oude grens weigerde.

## Ook

`index.html` (de klassieke, níét-gechunkte upload) controleert de bestandsgrootte
nu ook in de browser. Zonder die controle merkt de gebruiker de grens daar pas
als een 413, ná het versturen van gigabytes.

De gechunkte uploadpagina verstuurt 2 MB per verzoek, dus `MAX_CONTENT_LENGTH`
en de `client_max_body_size` van de proxy zien daar nooit het hele bestand: de
client-side controle is er de enige echte poort. Op de klassieke pagina geldt
`MAX_CONTENT_LENGTH` wél. Vandaar dat beide dezelfde bron moeten gebruiken.

## Bij het bijwerken van een bestaande installatie

`YASAFLASKIFIED_MAX_CONTENT_LENGTH` in `.env` **overrulet de default**. Staat
daar nog een oude waarde, dan blijft de server op die grens staan en verandert er
niets voor de gebruiker.

581 tests.

---

# v0.34.8 — 2026-08-26 — BDF wordt natief gelezen, en gelijkspanning gaat eruit

Pins `psgscoring[ml]==0.27.7` (ongewijzigd).

**Geen enkele gescoorde waarde verandert op een gewone opname.** Alle drie de
wijzigingen raken alleen bestanden die tot nu toe niet of verkeerd verwerkt
werden, plus het briefhoofd van installaties die er geen hebben ingesteld.

## 1. BDF wordt natief gelezen

BDF is 24-bit, EDF is 16-bit. Een centrum dat zijn BDF eerst naar EDF
exporteerde om te kunnen uploaden, scoorde daarna de conversie mee. `.bdf` mag
nu rechtstreeks; `myproject/signal_io.py` kiest de lezer op de extensie, en de
extensie **blijft behouden** bij upload en anonimisering — een BDF die als
`.edf` aankomt zou als 16-bit gelezen worden en plausibele maar onjuiste
amplitudes geven, en dat is een stille fout in plaats van een luide.

De browser-anonimiseerder werkt ongewijzigd op BDF: de header heeft dezelfde
indeling, alleen byte 0 is `0xFF BIOSEMI`. Geverifieerd dat de magic intact
blijft en de signaaldata byte-identiek. De uitvoer blijft EDF+.

## 2. Gelijkspanning-gekoppelde opnames worden hoogdoorgelaten

Een BioSemi-achtige versterker neemt gelijkspanning mee op. Op de opname die dit
aan het licht bracht droeg F3 een staande offset van 145 mV met het EEG er in
microvolts bovenop:

| kanaal | p95 vóór | p95 ná (0,3 Hz) |
|---|---:|---:|
| F3 | 144.629 µV | **24,2 µV** |
| C4 | 20.403 µV | 125,5 µV |
| Lt Leg | 14.666 µV | 205,4 µV |

Eén feit verklaarde drie klachten: **vlakke lijnen in de viewer** (de schaal
volgde de offset; gain hielp niet), een **"discontinuous" EDF na conversie**
(16-bit kan 145 mV en microvoltdetail niet tegelijk dragen), en **100 % van de
samples boven de 500 µV-artefactregel** — dus geen bruikbare uitkomst. Na
filtering: 0,0 %. Herrefereren op A1/A2 werkt níét; elk kanaal draagt zijn eigen
offset.

Drempel is dezelfde 500 µV als de artefactregel, kantelfrequentie 0,3 Hz. De
viewer krijgt een eigen behandeling omdat die lui per venster leest. Er komt een
melding in het rapport én een regel in het provenanceblok.

**Waarom dit automatisch gebeurt** terwijl gedragswijzigingen hier normaal
achter een vlag gaan: een kanaal met een offset boven 500 µV wordt nu al
volledig als artefact weggegooid. Er is geen bestaande bruikbare uitkomst om te
breken, en een test bewaakt dat een gewone opname byte-identiek blijft.

SpO2, hartslag, positie, flow, thermistor en ademhalingsbanden worden **nooit**
gefilterd: daar is het gelijkspanningsniveau juist de meting, en een ademhaling
van 12/min ligt op 0,2 Hz — vlak onder de kantelfrequentie. De uitsluitlijst
gaat daarom vóór de naamherkenning: `EMG/Piezo` draagt "EMG" maar meet
ademhaling.

## 3. Geen instellingsnaam meer in de code

Tot nu toe stond "Slaapkliniek AZORG" hardgecodeerd in twee rapportgenerators
én in `config.json.example`, dat de Dockerfile als `config.json` in het image
zet. Gemeten in productie: het site-blok wérd gelezen, maar kwam uit dat
voorbeeldbestand. **Elke installatie kreeg dus het briefhoofd van een ander
centrum op zijn rapport.**

De code draagt nu geen naam en geen logo meer. De site-configuratie komt uit
`instance/config.json` — host-lokaal, bind-gemount en uitgesloten van rsync, dus
het overleeft zowel een deploy als een image-rebuild. Zonder configuratie blijft
het briefhoofd leeg.

De studiecode is uit de twee publieke teksten gehaald; **de validatiecaveat zelf
blijft staan** — die bestaat om eerlijk te zijn over de validatiestand.

**Bij het bijwerken van een bestaande installatie:** zet uw gegevens in
`instance/config.json` vóór u uitrolt, anders verliest het rapport zijn
briefhoofd.

## Overig

`--exclude='config.json'` toegevoegd aan de rsync in DEPLOY_RUNBOOK §2: zonder
die regel zou een lokaal aangemaakte `config.json` de instellingsgegevens van
productie overschrijven.

576 tests.

---

# v0.34.7 — 2026-08-26 — een verschoven arousal-onset staat nu in het rapport

Pins `psgscoring[ml]==0.27.7`.

**Geen enkele gerapporteerde waarde verandert** bij de huidige profielen: de
nieuwe psgscoring-vlag `arousal_onset_offset_s` staat overal op 0,0. Deze
release zorgt ervoor dat je het zíet als iemand hem aanzet.

## Wat erbij komt

Het provenanceblok krijgt een regel **"Arousal-onsets verschoven: +2.0 s"**
zodra psgscoring een verschuiving heeft toegepast. Staat de vlag op 0, ontbreekt
het veld (oudere psgscoring) of is de waarde onleesbaar, dan komt er géén regel
— een tabel die op elk rapport "0,0 s" zet, verdrinkt de regels die er wel toe
doen. Label in nl/fr/en/de.

## Waarom dit erin moet

Met de vlag aan liggen de arousal-onsets in het rapport ergens anders dan de
detector ze vond, en zijn AHI en RDI met die verschoven arousals berekend. Twee
rapporten van dezelfde nacht zouden dan verschillende onsets tonen zonder dat er
iets op de bladzijde staat dat het verschil verklaart — precies de fout waarvoor
dat blok gebouwd is.

Dit is ook het patroon waarop de REM-AHI-caveat eerder strandde: de bibliotheek
produceerde een veld, het rapport las het nooit, en niemand merkte het tot er
naar gevraagd werd.

## Hoe het geverifieerd is

Niet alleen op een handgebouwd fixture — dat slaagt ook als het de verkeerde
vorm heeft, terwijl de regel in het echte rapport onzichtbaar blijft. De
controle draait de volle arousalstap op een echte opname (PSG-IPA SN2) en geeft
de ECHTE psgscoring-uitvoer aan `provenance_rows()`: `+2.0 s` zichtbaar bij
offset 2, geen regel bij 0.

546 tests.

---

# v0.34.6 — 2026-08-25 — de arousal-analyse krijgt alle drie de hersenregio's

Pins `psgscoring[ml]==0.27.6`.

**Reported values change** op montages die meer EEG-afleidingen dragen dan er
tot nu toe werden ingelezen — de gangbare klinische montage.

De pneumo-raw werd gebouwd uit `detect_channels`, dat **één kanaal per rol**
teruggeeft. Op de klinische montage stonden daar `C3` en `C4` in — twee kanalen
uit **dezelfde regio** — terwijl hetzelfde EDF ook `O1`/`O2` en `F3`/`F4` droeg.
De arousalstap kiest zijn afleidingen uit wat er ÍS, dus frontaal en occipitaal
bereikten hem nooit. AASM V.A Note 1 schrijft alle drie voor.

Gemeten op PSG-IPA (n=5, 12 scoorders), arousal-F1 bij IoU 0,20:

| combinatie | regio's | F1 |
|---|---:|---:|
| **F+C+O** | 3 | **0,514** |
| F+C | 2 | 0,501 |
| C+O | 2 | 0,460 |
| beste enkele | 1 | 0,442 |

Eén → twee regio's is **+0,06**, de derde nog **+0,013**, tegen een menselijk
plafond van 0,679. Geen enkele regio wint overal: op SN4 wint occipitaal waar
hij gemiddeld de zwakste is, op SN5 centraal, op SN2 frontaal.

**Welke kanalen dat zijn beslist psgscoring**, via de nieuwe publieke
`arousal_derivation_channels()`. Deze app raadt niet welke afleidingen de
detector straks kiest — dat is precies wat er met de SpO2-afleiding misging.
Een test faalt zodra de opgevraagde set en de gebruikte set uiteenlopen.

De pneumo-raw blijft uitgekleed: alleen de respiratoire kanalen, de kin-EMG en
deze EEG-afleidingen. Een ongefilterde preload kost op een MESA-opname 5,1 GiB.

# v0.34.5 — 2026-08-25 — de provenance toont de afleidingsSET

Pins `psgscoring[ml]==0.27.5`.

**Geen enkele gescoorde waarde verandert.** Eén rapportregel wordt eerlijker.

Het klinische rapport toonde "Arousal-analyse — EEG: **C3**" terwijl de analyse
**C3 ∪ C4** draaide — twee afleidingen met allebei events (142 en 115).
`channels_used["eeg"]` is element 0 van de afleidingsset, niet de set. Onder
diezelfde tabel staat dat de kanaalkeuze de uitkomst bepaalt; hij deed dat niet.

Niet cosmetisch: legt iemand dit rapport naast het vorige, dan staat er twee
keer "C3" terwijl de arousal-index van 19,5 naar 24,5 ging. De verklaring van
dat verschil — een tweede afleiding die er eerst niet was — stond nergens.

**Tweede reparatie, onderweg gevonden:** de rij verscheen alléén wanneer het
arousal-EEG AFWEEK van het stagingkanaal. Draaide er een union op `C4 ∪ O2`
terwijl de staging ook C4 gebruikte, dan verdween de hele rij en zag niemand
dat er twee afleidingen liepen.

psgscoring 0.27.5 voegt `arousal_event_locked_threshold` toe — gebouwd,
gemeten, **default uit**, en dus zonder gevolg voor het rapport. Zie de
psgscoring-changelog voor de meting en waarom hij uit blijft.

# v0.34.4 — 2026-08-25 — de tweede EEG-afleiding was de saturatiecurve

Pins `psgscoring[ml]==0.27.4`.

**Reported values change** op montages met een SpO2-kanaal en een tweede
centrale EEG-afleiding — de gangbare klinische montage. De arousal-union
draaide daar op de saturatiecurve in plaats van op het tweede EEG.

Op een klinische opname (AHI 64) meldde de provenance:

```
derivations: ['C3', 'SpO2']   n_per_derivation: {'C3': 142, 'SpO2': 0}
```

`C4` stond in dezelfde raw en werd nooit overwogen. Ná de reparatie:
afleidingen `C3 + C4`, arousal-index 19,5 → **24,5**, en het aandeel
respiratoire events dat in een arousal eindigt 0,204 → **0,257**.

**Het werkpunt blijft 0,80** en is daarvoor opnieuw geijkt op de gerepareerde
configuratie, op twee cohorten met vooraf vastgelegde beslisregel: PSG-IPA
(12 scoorders) geeft count-ratio 1,01 en 4/5 binnen de scoordersspreiding,
MESA (n=20) geeft 0,78 — beide binnen de grens. Een eerdere sweep op één
afleiding wees 0,50 aan; op de gerepareerde configuratie is dat juist de
slechtste optie. De drempel stond goed, hij kreeg de verkeerde invoer.

Geen enkele andere gedragswijziging: beide default-uit vlaggen blijven uit.

# v0.34.3 — 2026-08-24 — een montage met één beenkanaal kan dat nu kiezen

Pins `psgscoring[ml]==0.27.3`.

psgscoring kent sinds 0.27.3 een rol `leg` voor een beenkanaal zonder
zijde-aanduiding — MESA's kale `Leg`, of een klinische montage die één
tibialiskanaal exporteert. Zonder die rol in de kanaalpagina moest de gebruiker
het aan `leg_l` of `leg_r` toewijzen, en dat is dezelfde onwaarheid die de rol
juist vermijdt: de bilaterale ontdubbeling hoort niet te draaien alsof er twee
kanalen zijn.

De keuze staat nu in de kanaalpagina en in de route die het formulier uitleest
(een `pneumo_leg` werd daarvoor stil weggegooid), met labels in alle vier de
talen.

# v0.34.2 — 2026-08-24 — vier getallen die geen getal hoorden te zijn

Pins `psgscoring[ml]==0.27.2`.

**Reported values change**: de positie-AHI van een houding waarin te kort
geslapen is, de FRI-index in twee secties, de kanaalkolom van de spindel- en
SW-tabel, en drie nieuwe aandachtspunten.

## De positie-AHI

psgscoring geeft sinds 0.27.2 `None` zodra er minder dan 15 min in een houding
geslapen is — de tabel toonde daarvoor "AHI Supine 120,0/u" uit één event in
0,5 min. De rapportlaag sloeg elke `None` over, en dan staat er **niets**: niet
te onderscheiden van een houding waarin de patiënt nooit gelegen heeft. Drie
gevallen, drie weergaven: het getal, `— (0,5 min, < 15)`, of geen rij.

## De FRI-index

44,3/u in de RERA-sectie en 43,2/u in sectie 8d, over dezelfde nacht en
dezelfde teller. Beide secties lezen nu `rsum["fri_index"]` uit psgscoring.
Voor resultaten van vóór dat veld reconstrueert `_fri_index()` de noemer uit
`n_rera / rera_index` — dezelfde noemer — en pas als laatste redmiddel de TST
uit de slaapstatistiek.

## De kanaalkolom van de spindel- en SW-tabel

Die toonde `—` op elke rij, en dat kwam niet uit de rapportlaag.
`sp.summary(grp_chan=True, ...)` zet het KANAAL in de index, en
`to_dict(orient="records")` gooit de index weg. Het label was dus al verdwenen
voordat het rapport ernaar kon kijken — een tabel met zes rijen waarvan niet te
zien was waar ze bij horen. `reset_index()` erbij, en het label draagt kanaal
én stadium wanneer de detector op allebei gegroepeerd heeft.

## Drie aandachtspunten uit de twee motiverende rapporten

1. **Desaturatielast disproportioneel** t.o.v. de gescoorde events
   (`ODI3 ≥ 3 × AHI`, of `T90 ≥ 10 %` bij `AHI < 5`). Rapport 1 toonde AHI 3,1
   naast ODI3 14,1 en T90 28 %: de hypoxemie werd gevlagd, de discrepantie
   niet — terwijl die de klinische boodschap is.
2. **Arousal-index onwaarschijnlijk laag** (`AHI ≥ 15` en `AI < AHI/2`).
   Rapport 2 toonde AI 3,5/u bij AHI 42 met 217 events. Deze regel had de
   EMG-transportregressie in één oogopslag zichtbaar gemaakt.
3. **Gemiddelde hartfrequentie < 50 bpm.** Beide rapporten toonden 43,8 bpm
   náást hun eigen referentie "60–100", zonder vlag, terwijl verderop al een
   bradycardie-telling staat.

Beschrijvend, geen advies — dezelfde stijl als de bestaande vlaggen, in alle
vier de talen.

# v0.34.1 — 2026-08-24 — de kin-EMG bereikt de arousalanalyse nu werkelijk

Pins `psgscoring[ml]==0.27.1`.

**Reported values change** op opnames **zonder bruikbaar kin-EMG**: de
arousalstap valt daar terug op de regelgebaseerde detectie in plaats van door
een model te gaan dat op een constant-nul feature draait. Op opnames mét
kin-EMG verandert er niets — behalve dat het kanaal er nu ook echt komt.

## Het transportprobleem

De LightGBM-arousalclassifier van psgscoring splitst 486 keer op een
EMG-feature (4e op gain, alle drempels boven nul). Het werkpunt 0,80 uit
v0.34.0 is gekozen op MESA-runs die het EDF **volledig** inlezen — met
chin-EMG. Deze keten leverde het kanaal **nooit** aan:

1. `pneumo_needed = pneumo_ch_list + [eeg_ch]` — de geconfigureerde `emg_ch`
   stond er niet bij, dus `raw_pneumo` bevatte het kanaal per constructie niet.
2. `run_pneumo_analysis(..., channel_map=pneumo_channels)` — de respiratoire
   map, zonder sleutel `"emg"`.
3. Het foutpad (`raw_pneumo = raw_staging`) had de EMG juist wél: de classifier
   kreeg zijn features alléén na een mislukte load.

Twee klinische AZORG-opnames gingen daardoor van AI 23,0 naar 4,9 en van 11,0
naar 3,5 /u — die laatste bij AHI 42 met 217 respiratoire events.

## Wat er verandert

- `_pneumo_load_plan()` — de pneumo-raw draagt nu ook `emg_ch`. Alleen het EEG
  en de kin-EMG komen erbij; de rest van de montage blijft eruit, want dáárom
  bestaat die raw (een ongefilterde preload kost op een MESA-opname 5,1 GiB).
- `_pneumo_channel_map()` — de sleutel `"emg"` gaat mee naar psgscoring, maar
  alleen als het kanaal werkelijk in de raw zit. Een naam meegeven die er niet
  is zou erger zijn: psgscoring valt dan terug op zijn eigen zoektocht en de
  provenance zou een ander kanaal noemen dan de map.
- **Het studievergelijkingspad** (`run_profile_comparison`) laadde alléén
  pneumo-kanalen — geen `eeg_ch`, geen `emg_ch`. De arousal/RDI-arm van elk
  profielrapport draaide dus zonder EMG en mogelijk zonder arousal-EEG, terwijl
  vergelijkbaarheid met de klinische run het enige doel van die functie is.
  Beide worden nu meegeladen en doorgegeven.
- **Een ontbrekend EMG- of EOG-kanaal is zichtbaar.** `_validate_channels`
  gooide bij ontbrekend EEG, maar meldde ontbrekend EMG/EOG alleen met een
  `logger.warning` in de workerlog — niets in `analysis_warnings`, niets in het
  rapport, niets in de UI. Precies daardoor bleef maandenlang onzichtbaar dat
  de classifier zonder kin-EMG draaide. De functie geeft nu waarschuwingen
  terug (`emg_channel_missing`, `eog_channel_missing`) die in
  `analysis_warnings` terechtkomen.
- **`analysis_warnings` werd geschreven en door niemand gelezen.** Een grep
  door de codebase leverde één schrijver en **nul lezers** op: geen PDF-sectie,
  geen sjabloon, geen route. De blokkerende "alle epochs als artefact"-melding
  stond er sinds v0.31 in en is nooit ergens getoond. Dat is dezelfde fout als
  de regressie die deze release repareert, één laag hoger. De lijst komt nu in
  het aandachtspuntenkader op pagina 1, met een vertaalsleutel per code in alle
  vier de talen; een code zonder sleutel valt terug op zijn eigen tekst, zodat
  een nieuwe waarschuwing niet stil verdwijnt.
- Het log meldt op welke raw de respiratoire analyse draait (normaal pad of
  terugval), zodat dat verschil achteraf leesbaar is.
- `CH_TYPE_PATTERNS["emg"]` en `_identify_emg_channels` kenden de kin-labels
  `Menton`, `Kinn` en `Submental` niet — die vielen door naar type "other" met
  schaal 1,0 in plaats van 150 µV in het signaalpaneel. LEG/TIBIAL blijven er
  bewust in staan: dat is een weergavetype, geen rol, en de kin-keuze gebeurt
  elders.

## Niet geclaimd

Dat dit de klinische −80 % verklaart. Op MESA n=10 kost het EMG-loos draaien
ongeveer **−14 %** van de mediane arousal-index (16,65 → 14,30 /u), lager op 7
van de 10 opnames en hóger op 3. De richting klopt, de grootte niet. Het
restant blijft open. Zie `docs/arousal_emg_transport_bevinding.md` in
psgscoring.

Los van code: de twee AZORG-exports bevatten géén kin-EMG terwijl de montage
die normaal heeft. Controleer het exportprofiel van de recorder — geen enkele
reparatie hierboven raakt die schakel.

# v0.34.0 — 2026-08-23 — psgscoring 0.27.0: the classifier now runs where the RDI lives

Pins `psgscoring[ml]==0.27.0`.

**Reported values change** on `aasm_v3_breath`, `aasm_v3_prob` and their
`_dual` variants: the arousal classifier runs there too, at operating point
0.80. The arousal index and the RDI move; the AHI barely does. The other twelve
v3 profiles are unchanged and the five reproduction profiles stay
byte-identical.

Measured before deciding, paired on MESA n=30: the RDI median falls 34.25 →
28.70 and its severity class moves on 11 of 30, while the respiratory event-F1
rises 0.44 → 0.48 (p = 5.5e-04). What decided it is that the arousal count —
unlike the RDI — has a human reference: the previous setting counted 212
against a reference of 128, the classifier gives 107, and the deviation from a
clean count falls 0.58 → 0.26.

Not claimed: that the resulting RDI is more correct. There is no RERA
reference, so a lower RDI is a shift rather than a correction.

**The provenance line is now reliable.** psgscoring stamps the version that
produced the result into its output, and the report reads that first. It
previously came from a `comparison` block that a normal single-profile run
never creates, so reports carried a permanent `(?)` instead of a version.

# v0.33.1 — 2026-08-23 — the report names the psgscoring that actually scored

No scored value changes. `psgscoring[ml]==0.26.0` unchanged.

`PSGSCORING_VERSION` was a hand-maintained literal in `version.py` and had
fallen two releases behind: reports said `psgscoring 0.24.0` while 0.26.0 had
done the scoring. A clinical report states its own provenance, so it was
naming a library it had not used.

Reading the installed version at render time would be wrong for a different
reason — a report can be produced later than the analysis ran, and would then
be stamped with today's software. `tasks.py` already captures
`psgscoring.__version__` at scoring time into `comparison._meta`; the report
now reads that. Older jobs without the field fall back to the installed
version, marked `(?)` rather than presented as fact.

Three tests pin it: the value must match what scored, the assignment must not
become a hardcoded literal again, and a fallback must be marked as an
approximation.

# v0.33.0 — 2026-08-23 — psgscoring 0.26.0: arousals no longer lose a fifth of the night

Pins `psgscoring[ml]==0.26.0`.

**Reported values change** on the sixteen v3 profiles: the arousal index moves,
and on `aasm_v3_breath`, `aasm_v3_prob` and their `_dual` variants the RDI
moves with it. The AHI is untouched, and the five profiles reproducing an
external rule set or a published dataset analysis are byte-identical.

Two causes, both in defaults rather than in the algorithm. The artefact list
that this app computes — an epoch flagged at a peak above 500 µV — was
removing the arousals: on MESA it discards a median 19.9 % of the night, and
ignoring it in the arousal step is better on 30 of 30 recordings. And the
classifier operating point had never been independently validated; 0.80
replaces 0.60, chosen over 0.90 because it keeps the arousal index unbiased
while 0.90 would put it a third too low.

Combined, arousal event-F1 on MESA goes 0.338 → 0.543.

`yasa.art_detect` is now available as an alternative artefact method behind
`YASAFLASKIFIED_ARTIFACT_METHOD`, default unchanged at `amplitude`. It is not
rejected as an artefact detector — there is no artefact reference to judge that
— only as a fix for this problem: it discards 2.1 % instead of 19.9 % and still
scores no better.

Reports produced under YF 0.32.0 carry the higher arousal index and RDI.

# v0.32.0 — 2026-08-22 — psgscoring 0.25.0: the RDI returns on four profiles

Pins `psgscoring[ml]==0.25.0`.

**Reported values change back** on `aasm_v3_breath`, `aasm_v3_prob` and their
`_dual` variants: the arousal classifier is off there again, so the RDI
returns to its v0.30.0 value. The AHI barely moves (median −0.4/h) and the
other twelve v3 profiles are untouched.

The reason is in the psgscoring 0.25.0 notes: on MESA n=50 the classifier
moved the RDI severity class on 14 of 50 recordings (28 %), and no dataset
available to us carries a RERA reference that could say which RDI is closer
to truth — MESA annotates none, and PSG-IPA holds 3 in its entire manual set
despite allowing the label. A shift that reclassifies a quarter of patients
without a reference is not booked as a correction.

Reports produced under YF 0.31.0 carry the lower RDI. Nothing else changes.

## v0.31.0 — 2026-08-22

Dependency bump to **psgscoring 0.24.0**: arousal detection moves from the
rule-based path to the MESA-trained classifier.

**The arousal index and the RDI change on every report.** Measured on PSG-IPA
against twelve scorers, in the multi-derivation mode the clinical profiles
run: event-F1 **0.326 -> 0.505** (scorers reach 0.692 among themselves),
precision 0.248 -> 0.425, better on 5 of 5 recordings.

The clearest illustration of what this fixes: one recording reported an
arousal index of 55.1/h against a scorer median of 8.5 -- a factor 6.47, at
precision 0.090. It now reports 15.7. Across the five, the ratio to the scorer
median goes from 1.59 (range 0.95-6.47) to 1.47 (range 0.94-1.85).

Another recording shows why the index alone never revealed this: the old path
reported 17.2 against a scorer 18.0, which looks perfect, while event-F1 sat
at 0.152. The right count at the wrong moments -- the same pattern as the PLM
time-base error in v0.30.0.

**AHI moves only where a profile confirms hypopnoeas on arousal.** MESA n=150,
paired: `aasm_v3_rec` identical on all 150, `aasm_v3_breath` bias -5.13 ->
-5.28 and F1 0.510 -> 0.514. Severity class shifts on 13 of 150.

**Not established, stated rather than left implicit:** the RDI impact is
unmeasured (`_compute_rera_rdi` reads the arousal list directly); the
multi-derivation evidence is n = 5; and the psgscoring golden harness no
longer exercises the classifier, because its fixtures carry EEG at 32 Hz and
a sampling-rate guard routes them to the rule path.

### Changed

- `myproject/version.py` — `__version__` 0.31.0, `PSGSCORING_VERSION` 0.24.0.
- `requirements.txt` — `psgscoring[ml]==0.24.0`.
- `README.md` — release badge.

## v0.30.0 — 2026-08-21

Dependency bump to **psgscoring 0.23.0**, plus one report change.

**Scored values change for PLM.** psgscoring 0.23.0 repairs the time base of
the limb-movement detector: it computed RMS over windows of `int(sf * 0.1)`
SAMPLES and converted the window index back with `idx * 0.1`. At 256 Hz a
window is 0.09766 s, so every reported time ran 2.3% fast — accumulating to
+620 s at the end of a 7.4 h night. Event times move and the count moves with
them, because the duration filter now works on the real duration. Event-F1
against twelve scorers on PSG-IPA: median 0.038 -> 0.692 (scorer against
scorer 0.820).

This reaches YASAFlaskified in three places: `/review/<job_id>` draws the
markers at the right time, the EDF+ export carries the corrected onsets
(`generate_edfplus.py:155`), and `plm_arousal_index` in the PDF — which
couples a PLM onset to an arousal within -0.5..+3 s — is no longer coupling
on drifted times.

**AHI, ODI, RDI and every respiratory index are untouched.** Verified rather
than assumed: MESA n=150, seed 20260801, reproduces the August measurement to
three decimals (`aasm_v3_rec` F1 0.438 bias -5.26; `aasm_v3_breath` F1 0.510
bias -5.13). Golden 9/9.

### Changed

- `myproject/version.py` — `__version__` 0.30.0, `PSGSCORING_VERSION` 0.23.0.
- `requirements.txt` — `psgscoring[ml]==0.23.0`.
- `myproject/generate_pdf_report.py` — the hypoxic-burden reference range
  `< 20` now appears only when the value came from the published Azarbarzin
  definition; otherwise the label carries the method, e.g. `Hypoxic burden
  (percentile)`. psgscoring can compute the burden several ways and on the
  same recording those differ by a factor 0.29 to 2.34, so a literature
  threshold printed beside a number from another definition implies a
  comparability that is not there. See
  psgscoring/docs/hypoxic_burden_bevinding.md.
- `README.md` — release badge to v0.30.0.

# Changelog — YASAFlaskified

## v0.29.0 — 2026-08-19  *(the RIP block shipped into dead code)*

The block added in v0.27.0 sat inside `if has_sq:`, and `has_sq` has been
hard-coded `False` since v0.15.0 — the signal-quality section was removed from
the clinical PDF then. So it could never render. On a real recording with
energy ratio 1186× and `pair_gate_suspect=True`, the report said nothing.

**The test that was supposed to guard it read the source** for
`pair_gate_suspect` and passed. Presence is not reachability. The replacement
renders a report and reads the PDF back, and it fails against the v0.27.0 code
— verified, not assumed.

`psgscoring` unchanged at 0.22.0; no scored value moves.

## v0.28.0 — 2026-08-19  *(psgscoring 0.22.0: scored values change)*

⚠️ **This is the first release today that changes scored values.** Everything
before it was behaviour-identical — flags that stayed off, warnings, reporting.
`psgscoring` moves 0.21.0 → **0.22.0**, and on the four v3 clinical profiles,
wherever the effort classification falls back to a single band:

* apnoeas that were `uncertain` now carry a subtype, so **`ahi_total` rises** —
  bare `uncertain` fell outside that index;
* **OAHI and CAHI shift**, predominantly from central to obstructive;
* recordings where bilateral analysis works are unchanged.

The same EDF therefore yields different indices than the report currently on
file. That is intended and evidenced, but it is worth knowing before anyone
places two reports of the same patient side by side.

### Why

With one usable effort band the classifier had a single axis: median event
envelope against the baseline P75, with everything between 0.20 and 0.50
landing on `uncertain`. That conflates a band that gets *smaller* — under
obstruction thorax and abdomen move in antiphase, so volume shifts and one band
drops while effort continues — with a band that is *absent*.

Two cohorts, two references, same sign. **PSG-IPA**, twelve human scorers per
recording: rhythm 0.586–0.592 against 0.609 bilateral, where the amplitude rule
reaches 0.140–0.199 and leaves 52–63 % of apnoeas undecided. **MESA** against
NSRR, criterion registered blind beforehand: median Δ +0.236 and +0.336,
p = 0.002 on both belts.

Human-versus-human subtype agreement on PSG-IPA is 0.883 over 181 scorer pairs,
which is the scale these numbers should be read against.

### No YASAFlaskified code changed

Only the pin. The registry gained a profile (`aasm_v3_amplitude`, which
preserves the pre-0.22 behaviour) and lost none, and the dropdown, the profile
matrix and the study-set validation all read the registry rather than a
hard-coded list — the fix shipped in v0.22.0 of this app. Nothing here needed
adapting, which is what that fix was for.

## v0.27.0 — 2026-08-19  *(the RIP pair gate finally reaches the report)*

**No scored value changes.** `psgscoring` moves 0.20.0 → **0.21.0**, which adds
a warning and a flag that is off on every profile. Every index stays what it
was; what changes is what the report tells you about how it was produced.

### The pair gate was invisible in the report

`pneumo.signal_quality` — the RIP pair quality, including
`recommended_mode`, `working_channel` and the warning "thorax likely
disconnected" — appeared **only as a badge in the web interface**. It was never
in the PDF. A clinician therefore read "89 central apnoeas" with no indication
that bilateral analysis was off and that the obstructive/central distinction
rested on a single belt.

That is the same pattern as `ahi_rem_caveat`: the library produces it, the
report never reads it.

The report now carries a block whenever the mode is not bilateral, with the
mode, the channel actually used, the energy ratio and the gate's own warnings —
and a red heading instead of an orange one when the rejection is **doubtful**,
that is, when the rejected channel passed its own quality test.

### Why that distinction matters

On a clinical recording the gate reported a ratio of 1186× and dropped the
thorax as "likely disconnected" — while its own per-channel test gave that
thorax `status=ok` and `breath_fraction` 0.740, and the belt was visibly
moving. Rescoring with only that decision changed produced 142 events both
times (Jaccard 1.000, so no detection moved) but relabelled 73 of them: 49
central→obstructive, 16 uncertain→obstructive. `ahi_total` went 20.0 → 23.9,
because bare `uncertain` falls outside that index.

psgscoring 0.21.0 carries the repair behind `rip_pair_scale_free`, **off on
every profile**: a scan of 150 MESA recordings found the gate firing on 6 and
the flag changing exactly 1, so the pre-registered criterion cannot be met on
that cohort. What ships here is the visibility, which changes nothing that is
scored.

### Tests

Two read the report source, so the block cannot quietly disappear again. One of
them pins that every local in it carries a `_rip_` prefix — renaming a local to
`_hdr` in that same function previously caused an `UnboundLocalError` on *every*
report.

## v0.26.0 — 2026-08-19  *(the profile report: a second PDF, on its own queue, only when asked)*

**No clinical report changes.** `psgscoring` stays at 0.20.0. The clinical PDF,
the indices and the decision text are untouched; everything here is a separate
research document plus the queue that produces it.

### A comparison is a batch job, never a button

Seven profiles cost a measured **45:59**, and only 3 % of that is shared work.
RQ has no priority within a queue, so protecting clinical turnaround is
entirely a matter of which workers listen where: comparisons go to a new
`study` queue, workers 1–6 listen only on `default`, workers 7–8 on
`default study` — and that order means they drain clinical work first. At most
two of eight workers can sit in a comparison.

The clinical report is written before anything is enqueued. The hypnogram is
passed through: re-staging costs 90 s and risks different sleep stages than the
report used, which would compare against something the report does not contain.

### Two ways to ask, both opt-in

A checkbox at upload — default **off**, shown only when the site has a study
profile set, and it names what would run. And a button on the results page, for
whoever did not know the question would come up.

The gate sits in two places on purpose: the template hides the checkbox, but a
form can be posted without it, so `app.py` only fills `study_profile_set` when
the field is present. Hiding a control is not access control.

### The document

Four sections, A4 portrait, research marking on **every** page and a filename
that repeats it. §A the index matrix (reusing `profile_matrix`, registry-driven,
"—" and never 0.0, CAI not CAHI). §B the event agreement. §C sensor provenance
from `meta.flow_channels`, quoting the thermistor gate's own reason — absent is
not the same as present-but-rejected. §D provenance, per-profile wall clock and
the caveats.

Unlike the other derived artifacts the download does not generate on the fly:
that would be a request stalling for tens of minutes. Missing means no
comparison was run, and that is the honest answer.

### A Jaccard needs a scale, so the report carries one

PSG-IPA has twelve independently scored files per recording. Through the same
matcher at the same threshold, 66 pairs per recording, the human median is
**0.385** (0.026–0.965 across pairs). Two profiles at 0.513 therefore agree
*more* than two humans do — without that reference the number reads as a
shortcoming of the algorithm.

Agreement also tracks event density: 273–339 events give 0.902, while 1–38
events give 0.382. With few events one disagreement dominates, so Jaccards from
different recordings are not comparable without the event count beside them.
The report says both, and frames the reference as context rather than a norm.

### End-to-end, on the test VM

A real job through the real queue: picked up by worker7 within a second,
**884.9 s** for two profiles, reproducing the workstation measurement to the
digit (n=98, shared 76, Jaccard 0.5135, median IoU 1.000) on a different
machine and a different psgscoring version.

**Deploy note:** `docker-compose.yml` changes, so this deploy recreates the
whole stack rather than only the app.

## v0.25.0 — 2026-08-19  *(§B: the events are kept, and compared against the primary profile)*

**No clinical report changes.** `psgscoring` moves from 0.19.1 to **0.20.0**,
which adds the agreement matcher and a wavelet option that is off on every
profile — no scored value changes. The pin moves, so a report generated after
this deploy cites a different library version than one from before it.

### The events are no longer discarded

`run_profile_comparison` kept only `respiratory.summary`, so the one question a
comparison raises — *are two equally large event sets the same set?* — had no
input to answer it. It now keeps the full event dicts and attaches
`agreement_vs_primary` to every non-primary row, computed by
`psgscoring.agreement.compare_event_sets`: shared / only-a / only-b, Jaccard,
median and minimum IoU, per-category counts, and events that matched but carry
a different label.

Keeping the full dict rather than a projection is measured, not assumed: 810
events across seven profiles is 0.76 MiB in RAM and 0.35 MiB on disk, 0.013 %
of a 5.30 GiB peak. A projection saves 0.6 MiB and costs every field that later
turns out to matter. The lists go to their own `profile_events.json` so
`profile_comparison.json` stays readable.

### What it says about the seven clinical profiles

Against the measured event sets, primary `aasm_v3_rec` (126 events):

| profile | n | shared | Jaccard | relabelled |
|---|---:|---:|---:|---:|
| `aasm_v3_pressure` | 126 | 126 | **1.000** | 0 |
| `aasm_v2_rec` | 126 | 126 | **1.000** | 0 |
| `aasm_v1_rec` | 100 | 100 | 0.794 | 0 |
| `cms_medicare` | 100 | 100 | 0.794 | 0 |
| `aasm_v3_dual` | 134 | 110 | 0.733 | **8** |
| `aasm_v3_breath` | 98 | 76 | **0.513** | 0 |

Three profiles are the same scoring under three names — seventeen minutes of
compute for three copies. Two are `rec` minus 26 events rather than a different
detection: their AHI of 14.5 against 19.6 is a subset, not a disagreement. One
is genuinely different. None of that is visible in an AHI column.

### Ten tests that call the function itself

The 22 tests shipped with v0.23.0 were green while `run_profile_comparison`
crashed on its third line, because they exercised the pure module and none of
them called it. Two of the new ones failed first and taught something: the
summary-key guard rejected `rdi` and `rera_index`, which are real but added
after `_compute_summary` returns — the summary has more than one writer. And
the agreement test failed on the old pin, which is why a missing matcher is now
reported through `_meta["agreement_error"]` rather than reading as "no
differences".

## v0.24.0 — 2026-08-19  *(the comparison function could not run; now it can, and we know what it costs)*

**No clinical report changes.** The corrected CAI column lives in the
study-gated profile matrix; the `compute_osas_score` fix is in a block that has
not rendered since v0.15.0. `psgscoring` stays pinned at 0.19.1.

### `run_profile_comparison` never ran

It crashed on its third line — `run_sleep_staging(raw)` against a signature
that needs `eeg_ch`. `git blame` dates that to 6 April, the original v0.9.0
code; the function has been dead since, so nobody met it. v0.23.0 shipped it
parametrised with 22 new tests, and those tests exercise `profile_matrix.py`,
the pure module, not this line. A green suite over a broken entry point.

Channels are parameters now, the way the clinical path gets them from the job
config. No EEG auto-detection was invented — this project has none, and one
here would sit beside the user's channel choice as a second truth. A caller
that has already staged can pass `hypno=`, which is what `hypnogram_shared`
was always supposed to mean.

The unfiltered `preload=True` is gone, replaced by the selective load the rest
of `tasks.py` uses: 175 s and 5.09 GiB become 0.5 s for the channels that
matter. At eight RQ workers that is the difference between ~40 GiB and a
handful.

### Five wrong summary keys

`_compute_summary` returns 68 fields and `cahi`, `n_apneas`, `n_hypopneas` are
not among them, so all three came back `null` and the matrix columns "CAHI"
and "n events" rendered `—` for every profile — which reads as "not available"
when it means "wrong key".

CAHI is **corrected, not renamed**: `central_index` is the central *apnoea*
index and central hypopnoeas are not in it, so presenting it as CAHI
understates the index. Nothing computes a CAHI in the reporting layer; that
would give one index two definitions. A real CAHI belongs in `_compute_summary`
in psgscoring.

The same bug sat in `batch_analyse.py` and in `compute_osas_score`, where the
central `'c'` modifier could never fire — `cai` read two nonexistent keys and
`csr_detected` lives in `results["cheyne_stokes"]`, not the summary. The `'r'`
modifier beside it works, which is why it went unnoticed.

### What a comparison actually costs

Seven clinical profiles on a 12 h recording: **45:59**, 5.89 GiB peak. Shared
load and staging are 90.3 s — **3 %** of the run. One more profile costs 345 s
median, not the "half a minute to two minutes" the docstring estimated.
Nineteen profiles is roughly two hours per recording.

That number decides the shape of the feature: a profile comparison is a batch
job with an explicit profile set, never a synchronous button.

## v0.23.0 — 2026-08-18  *(a profile matrix for studies; the clinical report is untouched)*

**No scored value moves.** `psgscoring` stays pinned at 0.19.1, no profile
changes, and the clinical PDF a patient's report renders is byte-for-byte the
report 0.22.0 rendered. Everything below is study reporting, plus one database
column.

### What this adds

When a study runs through YF, the report can now show a **profile matrix** —
the compared profiles as rows, with AHI, OAHI/CAHI, event count, RDI, severity,
and the signed delta against the profile the researcher designated as primary.
Row labels and the rule-set column are read from the psgscoring registry, so a
profile added to the library cannot appear here under a label invented in this
repo. A test rejects the return of hard-coded profile parameters.

`run_profile_comparison` is parametrised (`profiles=`, `primary=`) and writes a
`_meta` block: which profiles were compared, the psgscoring version, and
`wall_clock_s` per profile — the number study planning needs and the one figure
the sweep runs never recorded. It refuses an unknown profile name rather than
skipping it: a comparison quietly containing fewer profiles than the study
believes is worse than an error.

The primary profile runs along with the rest, and the report layer asserts its
row matches the head result to the decimal. A mismatch logs at ERROR and puts a
visible warning in the matrix footnotes — the report is still generated. That
assert is a free regression test on determinism between the two code paths.

### Three premises behind this work did not hold

Recorded because each one changed what got built:

1. `run_profile_comparison` was described as running the whole registry since
   v0.9.0. It never ran at all — the function occurred exactly once in the
   codebase, its own `def`. `profile_comparison.json` was never written.
2. The hard-coded three-profile table in the PDF was described as rendered. It
   is not: `# story.append(_prof_tbl)   # intentionally not rendered`, removed
   from the clinical report in v0.15.0 because it was never validated as a
   severity instrument.
3. What the report actually read came from the library, not from this repo:
   `pipeline.py` fills `respiratory["profile_comparison"]` and `ahi_interval`
   with three interval arms it rescores per recording.

So the matrix renders as a **study** artefact — when a full comparison exists or
a study profile set is configured — and leaves the clinical report alone
otherwise. Reversing a considered clinical decision from v0.15.0 as a side
effect of a reporting request would have been the wrong call.

### Database

New column `site.study_profile_set` (TEXT, nullable), holding the study's
primary profile and comparison set as JSON. A SQLite migration adds it at
startup: `db.create_all()` creates missing *tables*, not missing *columns*, so
without it an existing production database would never get the column and every
query touching it would fail. Frozen families (`dataset`, `legacy`) can never be
primary; experimental profiles need an explicit flag; an explicit comparison
list is never filtered behind the researcher's back.

### Deliberately not done

Nothing wires the 19-profile comparison into the clinical job path. Each profile
is a full `run_pneumo_analysis`, so running the registry on every upload would
multiply clinical turnaround by an order of magnitude for output no clinician
reads.

### Note on the release badge

The static README release badge still read v0.21.0 — it was missed at the
0.22.0 release. It now reads v0.23.0. The badge is static on purpose (the
dynamic shields.io endpoint fails intermittently on its token pool), which is
exactly why it needs the manual bump the runbook asks for.

## v0.22.0 — 2026-08-17  *(psgscoring 0.19.1, and a dropdown that separates research from clinical)*

**Scoring changes for the first time since 0.19.x of the library.** `psgscoring`
goes from 0.17.0 to **0.19.1**. Every profile a clinician can select scores
identically — the envelope axis added in 0.19.0 is off on all of them — but the
version pin moves, so a report generated after this deploy cites a different
library version than one from before it. That matters for anything being
compared across the boundary.

0.19.1 rather than 0.19.0 because it is the same scoring code with the PyPI
README links repaired; there is no reason to pin the version with the broken
project page.

### The dropdown separates research profiles from clinical ones

The scoring-profile dropdown on the channel-selection page grouped profiles by
the **AASM-version string** and applied no family filter at all. Every
exploratory profile therefore sat among the clinical ones, in the same optgroup,
visually indistinguishable — and any profile added to psgscoring landed there
automatically, with nobody deciding it should.

That was already true before this release; what made it urgent is what the pin
bump would have done with it. psgscoring 0.19.0 adds four envelope arms, and
they would have appeared in the group labelled "AASM v3 (2023, current)" right
next to `aasm_v3_rec`. One of them, `aasm_v3_env_breath`, was measured against
human scoring on **two independent cohorts and rejected** (PSG-IPA bias +3.19/h
against +1.69/h; MESA n=150 paired ΔF1 −0.021, p = 2.4·10⁻⁶). A clinician had no
way to tell it apart from the recommended profile.

Now there are four groups, built from the `family` field psgscoring itself
exposes and pins with a test:

| group | contents |
|---|---|
| AASM v3 (2023) — clinical | `aasm_v3_rec`, `_breath`, `_dual`, `_pressure`, `cms_medicare` |
| Historical AASM versions | `aasm_v2_rec`, `aasm_v1_rec` |
| Dataset reproduction (frozen) | `mesa_shhs`, `chicago_1999` |
| ⚠ Experimental — not for clinical use | the ten exploratory profiles |

The experimental group sits last, each of its options carries a ⚠ in its own
label, and a warning below the select is visible **without opening the list** —
an optgroup heading alone is too easy to scroll past.

`aasm_v3_strict` and `aasm_v3_sensitive` land in the experimental group. That is
deliberate and it is a change in how they are presented: they are the bounds of
the AHI confidence interval, intentionally too strict and too permissive, and
they were never meant as a standalone choice for a report. A test pins that
placement so promoting them later is a decision rather than a side effect.

### A help section, next to the choice rather than on another page

A collapsible "Which profile should I choose?" under the dropdown explains what
distinguishes the four families, in all four languages. Someone unsure about a
profile is unsure at that moment, not later on a documentation page.

It says plainly that the experimental profiles are either unvalidated or
measured-and-rejected, that they exist so a negative result stays reproducible,
and that what you pick there belongs in the methods section of a study rather
than in a patient record. It also states that a profile name alone is not enough
to make figures comparable over time — the library version has to be pinned too.

### Also

* `myproject/tests/test_profile_dropdown.py` (17 tests) renders the real select
  fragment out of the real template, so it tests the Jinja conditions rather
  than a copy of them. It fails if an exploratory profile reaches a clinical
  group (verified by removing the filter), if a profile lands in no group or in
  two, or if psgscoring introduces a family the template does not render — in
  which case those profiles would vanish from the dropdown without a word.
* Two tests now pin `requirements.txt`, the installed library and
  `version.py:PSGSCORING_VERSION` to each other. The local dev venv had drifted
  to psgscoring 0.14.4 while requirements pinned 0.17.0, which is exactly how a
  dropdown gets tested in a configuration that never ships.
* `run_profile_comparison` in `tasks.py` iterates every profile in the registry
  and is **dead code** — nothing calls it. Left in place, but noted: were it
  live, this pin bump would have taken it from 15 to 19 full pipeline runs per
  job, one of them on a rejected arm.

## v0.21.0 — 2026-08-15  *(landing page: an invitation to other sleep centres)*

**No change to scoring.** `psgscoring` stays pinned at 0.17.0 and no report
field, index or profile moves. This release is documentation and the landing
page.

**An invitation to other sleep centres, with the caveats attached to it.**
A new `#invite` section on the front page invites other centres to install,
modify and test the software, and lists three routes: an account on this
instance, self-hosting via `deploy.sh`, or `pip install psgscoring` inside
their own pipeline. Six caveats sit directly beneath the invitation rather
than behind a link — not a medical device, validated on five recordings and
one external cohort, test it against your own scoring first, the AHI is an
estimate with an interval, personal data stays the centre's responsibility,
and there is no support SLA. A centre that adopts this inherits every one of
them, and the ones that matter most are exactly the ones a page like this
tends to bury. Translated in full to NL/FR/EN/DE (31 keys).

`test_frontpage_invite.py` guards the parts that rot silently: that all four
languages render *their own* text rather than falling back to English (a
fallback still returns HTTP 200, so status alone proves nothing), that six
caveats are present, and that the install command on the page matches the one
in `DEPLOY_RUNBOOK.md`.

**The `deploy.sh` reference was spelled two ways.** The script's own usage
header said `bartromb/yasaflaskified`, every document said
`bartromb/YASAFlaskified`. Both resolve, because GitHub redirects raw requests
case-insensitively — which is why it survived: nothing broke, so nothing
flagged it. That is undocumented third-party behaviour to rest on, and a
reader comparing the header to the repository name gets two answers. One
spelling now, pinned across README, runbook, script header and landing page by
`test_deploy_sh_links.py`.

The README's Self-hosting section never mentioned `deploy.sh` at all — it
offered only the manual `git clone` + `docker compose` route, so the
one-command installer was undiscoverable from the front door. Both routes are
now listed.

**Stale numbers on the README.** Validation quoted mean |ΔAHI| = 2.0/h from an
older harness; it is bias +1.69/h, MAE 1.76/h, r 0.997, weighted κ 0.839, and
MESA n=150 is now quoted too. The paper title matched neither the manuscript
nor the psgscoring README; all three now carry the v38 title.

**The stack tile said `psgscoring 0.12`** — five minor versions stale, because
it was hand-typed. It renders `PSGSCORING_VERSION` now, which the app already
exposes to every template, so it cannot drift again.

## v0.20.0 — 2026-08-13  *(psgscoring 0.17.0: twee sensorpoorten gerepareerd)*

Een dependency-bump, maar **geen byte-identieke**: psgscoring 0.17.0 zet twee
gerepareerde sensorpoorten default aan op dertien van de vijftien profielen.
Gerapporteerde AHI's veranderen. `mesa_shhs` en `chicago_1999` blijven gepind.

**De RIP-kwaliteitspoort mat de eenhedendeclaratie, niet de sensor.**
`assess_rip_channel` keurde effortkanalen af op absolute drempels
(`MAD < 0.005`), terwijl EDF-eenheden per kanaal vrij zijn. Een opname die RIP
in mV declareert komt na omrekening naar V ~150x te laag binnen met een
volstrekt normaal signaal. Op MESA viel daardoor 52 van de 52 opnames af en
kwam 100 % van de apneus uit als `uncertain`; op een klinische opname valt het
thoraxkanaal af met de béste signaalvorm van het hele stel, waarna de opname
stil naar `single-channel` degradeert — zonder paradoxale fasedetectie, precies
de grootheid voor obstructief/centraal.

Kale `uncertain` valt buiten `ahi_total`, dus dit is een INDEXwijziging.
Tegen de NSRR-referentie (n=40) halveert de bias: `aasm_v3_rec` −9,48 → −5,14,
`aasm_v3_breath` −11,93 → −5,33, met op `breath` identieke F1, precisie en
recall — zelfde events, andere boekhouding.

**Wat dit voor bestaande rapporten betekent.** Een opname met RIP in mV kreeg
tot nu toe apneus zonder subtype, en die telden niet mee in `ahi_total`. Dezelfde
opname opnieuw analyseren geeft nu een hogere AHI en wél een obstructief/
centraal-onderscheid. Reeds uitgeleverde rapporten worden niet met terugwerkende
kracht herrekend.

**Tweede poort: het stabiele-ademhalingsfilter draaide half.** Het vergeleek het
eventtype exact met `"hypopnea"`, waardoor `hypopnea_central`, `_mixed` en
`_uncertain` eraan ontsnapten. Op PSG-IPA dekte het 96 % van de hypopneus, op
MESA met dichte poort nul. Nu dekt het alle subtypes.

Volledige verantwoording, inclusief de vooraf vastgelegde beslisregel voor de
drempel, staat in de psgscoring-CHANGELOG bij v0.17.0.

## v0.19.16 — 2026-08-08  *(oordeel vastleggen; deeplink naar de PSG Editor)*

**De PSG Editor kon dit al.** Bij het uitwerken van "afgekeurde events alsnog
kunnen scoren" bleek `event_api.toggle_event_at` events al toe te voegen en te
verwijderen — en verder te gaan dan gedacht: hij herberekent de statistieken en
schrijft ze terug in `results.json` met `manually_corrected: True`. De AHI
verandert daar dus wél.

Een tweede scoormechanisme in de controlepagina bouwen zou "één grootheid, twee
definities" hebben opgeleverd, met verschillende semantiek — dezelfde klasse
fout als de twee RDI's en de twee REM-AHI's eerder deze week. Daarom een andere
verdeling:

- **de controlepagina** vindt de gevallen (dat kan de editor niet: die toont de
  nacht, niet "deze twaalf") en legt een **mening** vast;
- **de PSG Editor** is waar je écht corrigeert, met het signaal erbij en een
  echte onset en duur;
- **een deeplink** verbindt ze. De editor opende altijd op epoch 1, dus vanaf
  een paneel op t=8439 s moest je met de hand naar epoch 282 bladeren.
  `/score_v12/<job>?t=<seconden>` springt er nu heen.

**Oordelen.** Drie knoppen per paneel, opgeslagen in `{job_id}_review.json`.
Een oordeel **verandert de AHI niet** — daar staat een toets op. Dat is een
bewuste beperking: een klinisch rapport waarvan het hoofdgetal verschuift omdat
iemand op een knop drukt is niet meer te reconstrueren, en dan valt niet te
zeggen welke AHI in het dossier stond toen de brief werd geschreven.

Opgeslagen wordt de **bedoelde uitkomst** ("hoort gescoord"), niet
"eens/oneens" — met daarnaast wat het algoritme deed, plus profiel en
psgscoring-versie. Bij eens/oneens weet je later niet meer waarmee iemand het
eens was; nu blijft het label leesbaar wanneer een volgende versie hetzelfde
event anders behandelt. `agrees_with_algorithm()` leidt de overeenstemming af
in plaats van hem op te slaan. Dat maakt de verzameling bruikbaar als
gelabelde dataset.

Het endpoint is **niet** van CSRF vrijgesteld, anders dan de oudere API-routes
hier: de pagina stuurt de token in de `X-CSRFToken`-header.

**Een toetssuite die de gelukkige weg niet dekte.** De fixture van
`test_event_review_route.py` had geen EDF, dus viel het hele
`{% if panels %}`-blok weg — de knoppen, de editor-link en zelfs het renderen
van panelen waren ongedekt terwijl de suite groen stond. De fixture schrijft nu
een echte kleine EDF, met een toets die afdwingt dat er panelen verschijnen.

368 tests groen (was 340).

## v0.19.15 — 2026-08-08  *(buurevents zichtbaar; regel B en duidelijke gevallen)*

**Reparatie — afwezigheid van een markering betekende niets.** De panelen
markeerden andere gescoorde events in blauw, maar sloegen alles over waarvoor
`oe_onset < t_start + 2 or oe_end > t_end - 2` gold. Dat filterde juist de
half-zichtbare buren weg, de meest voorkomende soort. Aangetoond op PSG-IPA
SN3: in het venster rond de obstructieve apneu bij t=316,6 s staat een tweede
apneu op 359,4–371,1 s die in beeld is maar 8,5 s over de rand loopt — en dus
onbemarkeerd bleef.

De weergave was daarmee dubbelzinnig op de ergst mogelijke manier: geen blauw
betekende niet "hier is niets gescoord" maar "misschien wel, misschien niet".
Voor een controle-instrument is dat fataal, want de lezer kan een gemist event
niet onderscheiden van een gemarkeerd event.

Nu wordt elk OVERLAPPEND event gemarkeerd, afgeknipt op de vensterrand. De
grenslijnen worden alleen getekend waar de grens écht ligt — een lijn op de
afgeknipte rand zou een begin of einde suggereren dat er niet is, en dan lijkt
een doorlopend event kort. De arcering ging van alpha 0,10 naar 0,15, want ze
was nauwelijks zichtbaar.

**Twee nieuwe selectiecategorieën.**

- **Regel B** (paars): hypopneeën die via een AROUSAL kwalificeerden in plaats
  van via desaturatie. Daar zit de meeste subjectiviteit en de grootste
  spreiding tussen menselijke scoorders. De vlag stond al op het event
  (`rule1a_arousal`, met `rule1b` als historische alias die oudere resultaten
  dragen); beide worden gelezen.
- **Duidelijke gevallen** (groen): de hoogste confidence. Niet om na te kijken
  maar om te IJKEN — je moet kunnen zien hoe een onbetwist event eruitziet. En
  methodologisch belangrijker: zonder deze categorie bestaat de verzameling
  uitsluitend uit grensgevallen, en dan is ze scheef en ongeschikt om later een
  model op te trainen.

De specifieke categorieën claimen nu vóór de brede. Een regel-B-geval heeft
doorgaans ook een lage confidence; als de twijfelcategorie hem eerst opeist,
verdwijnt juist de informatie waaróm hij lastig is. Bij weinig panelen
verdwijnen `rule_b` en `easy` vanzelf (quota `n//6`), zodat de moeilijke
gevallen dan overheersen.

De inleiding legt nu ook uit wat blauw betekent, in vier talen.

**Een toets die leeg slaagde.** `axvspan` geeft in matplotlib 3.11 een
`Rectangle` terug, geen `Polygon`. Mijn eerste hulpfunctie herkende alleen
Polygon, gaf dus altijd een lege lijst, en twee toetsen die de AFWEZIGHEID van
een markering controleerden kregen hun resultaat gratis. Elke buurtoets begint
nu met `_assert_event_span()`: valt de hulpfunctie stil, dan faalt álles in
plaats van stilletjes groen te blijven.

340 tests groen (was 330): vijf voor de buurmarkering, vijf voor de nieuwe categorieën.

## v0.19.14 — 2026-08-08  *(telt dit event mee in de AHI?)*

De visuele eventcontrole toonde het TYPE van een event maar niet of het in het
hoofdgetal zat. Juist bij "uncertain" is dat contra-intuïtief, want er zijn
**twee** labels die zo lezen en ze gedragen zich tegengesteld:

| type | betekenis | `ahi_total` | `ahi_incl_uncertain` |
|---|---|---|---|
| `uncertain` | een APNEU die de effort-classificatie niet kon onderverdelen (meestal een aangetast RIP-signaal) | **nee** | ja |
| `hypopnea_uncertain` | een HYPOPNEE waarvan het subtype onbepaald bleef | **ja** | ja |

De asymmetrie is geen ontwerpkeuze maar een gevolg van de telling:
`respiratory.py` doet `hypopneas = [e for e in events if "hypopnea" in
e["type"]]` — substring-matching, dus `hypopnea_uncertain` glijdt er vanzelf
in. De kale `uncertain` staat in een eigen lijst en wordt bewust weggelaten uit
`ahi_total` (conservatief, bedoeld om na te kijken). `ahi_incl_uncertain` is
tegen scoorders geijkt op ~0 bias; `ahi_total` ligt ~1,5/u lager.

Elk paneel draagt nu een label. **Vier** toestanden, niet drie:

- `telt in AHI`
- `niet in AHI · wel in AHI incl. onbepaald` — de kale `uncertain`
- `gescoord, niet in AHI` — een RERA zit in de RDI, niet in de AHI
- `niet gescoord` — een afgewezen kandidaat werd nooit een event

De laatste twee waren in de eerste versie één label. Dat wiste een verschil dat
er voor de beoordelaar juist toe doet: een RERA is wél gescoord.

**Drift-bescherming.** `ahi_membership()` herhaalt een regel die in psgscoring
inline in `_compute_summary` staat en niet als functie beschikbaar is.
`test_ahi_membership_matches_psgscoring` laat psgscoring daarom ZELF tellen —
één event per type — en controleert of `ahi_total` en `ahi_incl_uncertain`
bewegen zoals het label belooft. Verandert psgscoring de regel, dan valt die
toets om in plaats van dat de pagina stil gaat liegen.

330 tests groen (was 314).

## v0.19.13 — 2026-08-08  *(eventcontrole werkte op geen enkele echte montage)*

**Reparatie — "Geen enkel paneel kon getekend worden".** De visuele
eventcontrole uit 0.19.12 faalde op élke klinische opname, niet op een
randgeval. Op een montage met één druksensor wijzen de rollen `flow` en
`flow_pressure` naar hetzelfde fysieke kanaal, en `raw.pick()` weigert een
selectie met dubbels:

    need = ['Pressure Flow', 'Pressure Flow', 'Flow Th.', 'RIP Thora', ...]
    ValueError: Found 6 / 7 unique names, sel is not unique

`load_panel_raw` ontdubbelt nu op kanaalnaam met behoud van volgorde, en de
tekenfunctie zet één rij per FYSIEK kanaal in plaats van per rol — dezelfde
curve twee keer onder twee labels suggereert twee sensoren die het eens zijn,
wat in een controle-instrument precies de verkeerde indruk wekt. De
detectiemarkering (`◀`) volgt mee naar de rij die het kanaal wél tekent.

**En de reden was onzichtbaar.** `load_panel_raw` ving elke uitzondering af en
gaf stil `None` terug, waarna de pagina alleen meldde dat er niets getekend
kon worden. De fout stond in geen enkel log; hij moest van de server gevist
worden. Er is nu een logger in `generate_pdf_report.py` en beide terugvallen
schrijven weg wat er misging.

Waarom de tests dit niet zagen: mijn fixture had toevallig uitsluitend unieke
kanaalnamen. `test_epoch_panel_alignment.py` heeft er nu een montage bij waar
twee rollen één kanaal delen — vier nieuwe toetsen, waaronder één op
`load_panel_raw` zelf, want daar knapte het en niet in het tekenen.

### Opruiming van de repository

Verwijderd: `myproject/.hypothesis/` (27 bestanden testcache die bij elke run
veranderen), `myproject/templates/dashboard.html.pre_v0841_bak` (het patroon
`*.bak` in `.gitignore` ving `_bak` niet, en al getrackte bestanden negeert
`.gitignore` sowieso), de wortelkopie `logo.png` (byte-identiek aan
`myproject/static/logo.png`; de Dockerfile kopieert alleen `myproject/`),
`upgrade_v0822.sh` en `upgrade_v0825.sh` (eenmalige migraties naar v0.8.22 en
v0.8.30), en `RELEASE_v0.17.0.md` (eenmalige checklist).

`.gitignore` uitgebreid met `.hypothesis/`, `.ruff_cache/`, `.mypy_cache/` en
`*.log`.

De release-badge in de README stond hardgecodeerd op v0.19.10 en liep dus elke
release achter; hij leest nu de laatste release via de GitHub-API.

Sectie 5b van `DEPLOY_RUNBOOK.md` verwees naar het verwijderde
`RELEASE_v0.17.0.md`. Die sectie is NIET geschrapt: stap 4–6
(`JOB_ACCESS_STRICT`) en de `SESSION_COOKIE_SECURE`-noot staan nog open op
productie. Alleen de dode link is weg en er staat nu bij wat historie is en
wat niet.

314 tests groen (was 310).

## v0.19.12 — 2026-08-08  *(visuele eventcontrole voor beheerders; psgscoring 0.15.2)*

**Nieuw: `/review/<job_id>`** — een weergave die de gescoorde respiratoire
events tekent, met een knop op de resultatenpagina die alleen voor beheerders
verschijnt. Een AHI is één getal en verbergt hoe het tot stand kwam; dit toont
de signalen.

**De selectie is omgekeerd ten opzichte van het rapport.**
`_select_example_events` in de rapportgenerator kiest de hoogste confidence,
het langste event en de grootste desaturatie — de meest overtuigende
voorbeelden. Voor controle is dat waardeloos: wat het algoritme moeiteloos
goed doet hoef je niet na te kijken. Hier komt eerst de laagste confidence,
dan de afgewezen kandidaten die het dichtst bij de drempel kwamen, dan één
representant per type. Die nabijheid komt uit de reden zelf:
`local_reduction_19pct<20pct` scoort 0,95 en komt vooraan,
`local_reduction_2pct<20pct` scoort 0,10 en niet. De pagina zegt in vier talen
expliciet dat dit géén doorsnede van de nacht is.

**Twee poorten, in deze volgorde.** `job_access_required` eerst,
`requires_role("admin")` daarna. Toegang tot de uitslag is niet hetzelfde als
toegang tot de ruwe signalen: een technicus die zijn eigen job bekijkt wordt
hier geweigerd. De volgorde is niet vrijblijvend — andersom kreeg een
gebruiker van een andere site de rol-weigering in plaats van de gewone
job-weigering, en dat brak de gedeelde regel in `test_job_access.py`.

**Eén EDF-lezing per pagina, niet per paneel.** Gemeten op een nacht van 6,6
uur: header 1,0 s, vier kanalen laden 5,1 s en 194 MB, tegenover 0,18 s per
paneel. Panelen als losse verzoeken zou twintig events op twee minuten
brengen. Eén verzoek bouwt de hele set, begrensd op 24.

### Reparatie — de y-schaal van de signaalpanelen

De schaal was `median ± 4·MAD` over het hele venster. Een respiratoir event is
per definitie een stille periode, dus hoe overtuigender het event, hoe kleiner
de MAD en hoe strakker de schaal — precies omgekeerd aan wat de lezer nodig
heeft. Op een gemengde apneu (PSG-IPA SN3, t=436 s) bleef van het flowkanaal
een streep over en stond Abdomen op 20–40 terwijl de werkelijke excursies een
veelvoud zijn. Je kunt een reductie niet beoordelen als de ademhaling waartegen
je vergelijkt buiten beeld valt. Nu schaalt hij op de referentie-ademhaling
buiten het event, met het event erbij getrokken zodat een drukpiek bij
heropening zichtbaar blijft.

### De aantekening "epoch alignment nog niet correct" was verouderd

De sectie signaalvoorbeelden stond sinds v0.8.36 uit met die ene regel als
reden. Nagemeten, en de uitlijning klopt: op een synthetische mixed-rate EDF
met een dropout op een bekende plek, en op menselijk gescoorde events uit
PSG-IPA (SN3, obstructief t=316,6 s, centraal t=241,8 s) valt de band exact op
het event — mét het effort-gedrag dat bij het type hoort: thorax en abdomen
lopen door bij obstructief, staan stil bij centraal. Ook getoetst en verworpen:
dat de `exclude`-lezing in `tasks.py` (32 Hz) tegenover de tekenlezing (256 Hz)
de tijdas zou verschuiven — alle drie de leespaden vinden dezelfde seconde.

De PDF-sectie blijft niettemin uit: 400 events is ~73 s rendertijd en ~28 MB
aan panelen, en een rapport is het verkeerde omhulsel voor een volledige
eventcontrole.

### Tests

38 nieuw, 310 groen (was 272). `test_epoch_panel_alignment.py` gebruikt een
**piekerige** golfvorm, geen sinus: met een sinus is de MAD ongeveer de halve
amplitude, klemt de oude regel niet en zou de toets groen staan zonder iets te
meten. Er staat een toets in die de oude regel op dezelfde data toepast en
aantoont dat hij faalt, zodat het fixture niet stilletjes te braaf kan worden.

## v0.19.11 — 2026-08-08  *(de REM-AHI zegt waarop hij rust; psgscoring 0.15.2)*

**De REM-kwalificatie staat nu in het rapport.** psgscoring 0.15.1 leverde
`ahi_rem_reliable` en `ahi_rem_caveat`, maar de rapportgenerator las die velden
nergens. Op opname 62942a61 stond daardoor "REM AHI 64.2 /u" naast
"NREM AHI 38.6 /u" zonder één woord over de 22 minuten REM waarop de eerste
rustte — ongeveer 24 events. Dat leest als REM-predominante OSA, een patroon
met behandelconsequenties.

De bibliotheek levert het feit, dit rapport de formulering: de tekst in
psgscoring is eentalig en het rapport verschijnt in vier talen. Resultaten van
vóór 0.15.1 dragen het veld niet en krijgen geen kwalificatie — geen
kwalificatie is beter dan een verzonnen kwalificatie.

**Eén bron voor de REM-AHI.** psgscoring levert deze grootheid twee keer:
`ahi_rem` uit `respiratory.py` (via `is_rem()`, en het enige paar dat de
betrouwbaarheidsvelden draagt) en `rem_ahi` uit `pipeline.py` (via
`stage == "R"`, een eigen herberekening). §8c toonde de tweede, §8e de eerste,
onder labels die voor de lezer niet te scheiden zijn: "REM AHI" en "AHI REM".
Ze gaven op deze opname hetzelfde, maar bij divergentie zou de kwalificatie het
verkeerde getal betreffen. Het rapport leest nu `ahi_rem`, met `rem_ahi` als
terugval voor oudere resultaten. De duplicatie in psgscoring zelf blijft staan
en is genoteerd in `~/CODE/docs/openstaand_werk.md` (buiten deze repo).

**Geen waarschuwingsglyph.** De eerste versie zette ⚠ voor de kwalificatie. Dat
teken ontbreekt in het ingebedde lettertype en werd een zwart blokje — in dit
rapport bovendien al de legenda-kleurmarkering, dus het las als een tweede
betekenis van hetzelfde teken. Zelfde val als de ↳ in v0.17.2. Kleur en
cursief dragen de nadruk nu.

**Voetnoot bij de REM-tegels.** "8 perioden · 22,5 min REM · 3,69 min
gemiddeld" nodigt uit tot vermenigvuldigen (29,5) en straft dat af. Geen
rekenfout maar twee definities: `rem_duration_min` telt R-epochs, een periode
is een spanne die onderbrekingen tot 2 min overbrugt. De noot verschijnt alleen
wanneer de getallen zichtbaar uiteenlopen.

**Tests.** `tests/test_pdf_rem_caveat_render.py` rendert het rapport
daadwerkelijk en leest de tekstlaag terug. Dat is bewust: de oorspronkelijke
fout was dat de bibliotheek geverifieerd werd en het rapport niet, en een toets
op de helper zou hem niet gevangen hebben — de helper wérkte, alleen riep
niemand hem aan. 272 tests groen (was 251).

## v0.19.10 — 2026-08-08  *(afwijkende parameters zichtbaar; psgscoring 0.15.1)*

**Het herkomstblok toont nu actieve omgevingsparameters.** `PSGSCORING_BREATH_*`
overrulet profielwaarden — handig om te meten zonder profielen te muteren, maar
het betekent dat dezelfde profielnaam op twee machines iets anders kan
betekenen. Juist dat blok bestaat om de UITVOERING te tonen in plaats van de
keuze, en het zweeg erover. De regel verschijnt alleen wanneer er iets aan
staat.

**psgscoring 0.15.0 → 0.15.1.** De REM-AHI meldt nu op hoeveel REM hij rust: bij
22,5 minuten REM is één event al 2,7/u, wiskundig correct en klinisch
onbruikbaar. Nieuw in de samenvatting: `rem_min`, `nrem_min`,
`ahi_rem_reliable`, `ahi_rem_caveat`. Puur additief. Plus tests voor de dunst
gedekte modules, die een echt defect blootlegden: `_classify_plmi(None)` gaf
"normal" — een schone verklaring op grond van een ontbrekende meting.

## v0.19.9 — 2026-08-07  *(psgscoring 0.15.0)*

Geen YF-codewijziging. Pin naar psgscoring **0.15.0**.

**Zichtbaar voor de gebruiker:** het profiel `aasm_v3_prob` heet niet langer
"fully probabilistic" maar **"graded arousal axis"**. Dat was een naam die meer
beloofde dan hij waarmaakte: alleen de hypopnee-as is gegradeerd, apneus komen
uit dezelfde regelcascade als in elk ander profiel en hun confidence klemt vast
op 0,95 (obstructief) of 0,90 (centraal). De profielsleutel is ongewijzigd, dus
ingestelde standaardprofielen blijven werken.

**Nieuw achter een vlag, standaard uit:** `hypoxic_burden_local_baseline`. De
hypoxic burden bleek niet onderschat bij lage saturatie — een vlakke basislijn
van 85 % geeft dezelfde burden als 96 % — maar wél overschat bij drift: op een
nacht die van 94 % naar 82 % zakt bijna verdubbelt hij zonder dat de events
veranderen.

## v0.19.8 — 2026-08-07  *(psgscoring 0.14.9)*

Geen YF-codewijziging. Pin naar psgscoring **0.14.9**: de RERA-ontdubbeling
toetst nu intervaloverlap in plaats van onset-nabijheid.

De oude toets (`|onset_a − onset_b| < 5 s`) miste een kandidaat die zes seconden
later begint maar volledig binnen het event valt, en noemde twee dingen hetzelfde
wanneer ze toevallig vlak na elkaar begonnen zonder elkaar te raken. "Elke
overlap" bleek te grof: afgewezen hypopnee-kandidaten overlappen voor 0,83–1,00
(duplicaten), flattening-reeksen voor 0,06–0,22 (flow-limitatie náást een event).
De regel is nu "meer dan de helft van de kandidaat ligt binnen een gescoord
event", en die drempel ligt in het gemeten gat.

Alle AHI's onveranderd.

## v0.19.7 — 2026-08-07  *(psgscoring 0.14.8)*

Geen YF-codewijziging. Pin naar psgscoring **0.14.8**, dat twee indices
repareert die een andere opname beschreven dan het rapport:

- **Positionele AHI werd berekend vóór de events definitief waren.** De
  positieanalyse draait in stap 6; stap 7b vervangt daarna elke hypopnee. Elk
  `breath_graded`-profiel hield dus AHI-per-positie van de envelope-detector.
  Via `ahi_per_pos` reikte dat tot de positionele fenotypering, dus het oordeel
  "kandidaat voor positietherapie" stond op de verkeerde eventlijst.
- **"AHI excl. ruis" kon groter zijn dan de AHI.** Niet door de noemer — die is
  in beide dezelfde — maar doordat de gefilterde variant over álle events telde
  terwijl `ahi_total` `uncertain` uitsluit.

## v0.19.6 — 2026-08-07  *(één grootheid, één getal; psgscoring 0.14.7)*

Vier bevindingen uit de rapportvergelijking, alle vier eerst tegen de code
gehouden.

**De opnamedatum toonde de analysedatum.** Het veld las `analysis_timestamp`.
Een heranalyse verzette daarmee de datum van een onderzoek dat maanden eerder
plaatsvond, en twee runs van dezelfde nacht kregen twee verschillende
opnamedatums. Nu `recording_start`; ontbreekt die in oudere resultaten, dan een
streepje — eerlijker dan de verkeerde datum onder het juiste etiket. Het
handtekeningblok houdt bewust de rapportdatum, want dat is wat "Datum" daar
betekent.

**Twee RDI's in één rapport.** Sectie 8 leest `respiratory.summary` (gevuld
door `_compute_rera_rdi`); sectie 8b las `arousal.summary`, die de RERA's
onafhankelijk berekent en niet bijwerkt na RERA-promotie — 183 RERA's in
sectie 8 tegen 0 in 8b, met een eigen RDI ernaast. Die drie rijen zijn uit 8b
weg; die sectie gaat over arousal-etiologie, een andere vraag.

**De kolom "Index" droeg het aantal.** Bij 57 RERA's stond er "n=57 · Index 57";
alleen de totaalrij deelde door de tijd. Nu een echte index, met dezelfde
noemer als het totaal, afgeleid uit totaal en index zodat er geen tweede
TST-definitie bijkomt.

**Twee FRI-tellers.** Sectie 8 toont de flow-reducties die FRI BLEVEN; 8d telde
`len(rejected) − n_reinstated`, dus inclusief wat verderop RERA werd —
systematisch hoger, zelfde label. 8d leest nu dezelfde bron, met terugval voor
oudere resultaten.

**psgscoring 0.14.6 → 0.14.7:** dezelfde noemer-ondergrens stond op twaalf
plaatsen, niet één. Arousal-index, PLM-index, ODI, RERA-index en RDI waren nog
steeds het aantal maal duizend terwijl de AHI al gerepareerd was.

251 tests groen.

## v0.19.5 — 2026-08-07  *(het studietype bepaalt de kanaalkeuze, niet andersom)*

Geen psgscoring-wijziging (blijft 0.14.6).

De serverkant negeerde bij polygrafie al elk meegestuurd EEG-kanaal (0.19.3),
maar in het formulier stond de neusdruk nog steeds geselecteerd — en er was
geen manier om dat te veranderen.

**EEG heeft nu een "niet beschikbaar"-keuze.** EOG en EMG hadden die al; EEG
niet, en er stond `required` op. Een radiogroep zonder gekozen optie toont en
verstuurt bovendien de EERSTE optie, en dat is op een polygrafiemontage
`Pressure Flow`. Er was dus letterlijk geen manier om "geen EEG" te kiezen.
Zonder herkend EEG-kanaal staat "niet beschikbaar" nu aangevinkt.

**Het studietype staat bovenaan het formulier.** Het stond onder de
kanaalkeuze, dus je koos kanalen voordat je zei wat voor onderzoek het was. De
volgorde liep omgekeerd aan de afhankelijkheid.

**Kies je een polygrafie, dan gaan EEG, EOG en EMG op slot** en springen ze
terug naar "niet beschikbaar", met de reden eronder: *"Niet van toepassing bij
polygrafie: er is geen EEG, dus geen slaapstaging."* De server negeerde die
kanalen al; dit maakt zichtbaar waarom, in plaats van ze stil te laten
verdwijnen.

## v0.19.4 — 2026-08-07  *(de titel volgt het onderzoek)*

Geen psgscoring-wijziging (blijft 0.14.6). Kleine nalevering op 0.19.3, gezien op
een testrapport voordat die versie uitgerold was.

Boven een polygrafierapport stond **"Polysomnografie — Slaaprapport"**. Een
polygrafie is per definitie een onderzoek zónder EEG, dus dat is precies het
soort etiket dat 0.19.3 rechtzet — en het stond nog op de eerste regel. De titel
komt nu uit wat er werkelijk gedraaid heeft: **"Polygrafie — Slaaprapport"**,
in alle vier de talen.

## v0.19.3 — 2026-08-07  *(polygrafie: de opname beslist, en het rapport toont geen slaap meer)*

Geen psgscoring-wijziging (blijft 0.14.6).

Vervolg op 0.19.2, na een tweede blik op hetzelfde rapport. Twee dingen bleven
staan.

**Het EEG-veld vulde zichzelf met de neusdruk.** Niet via de patroonherkenning —
die weigert een flowkanaal correct als EEG — maar via een blinde terugval in
`app.py`: *"Ultieme fallback: eerste kanaal"*. Op een polygrafiemontage is het
eerste kanaal `Pressure Flow`, dus stond dat voorgeselecteerd en volstond één
klik op "start". Die terugval is weg: geen EEG in de montage betekent geen
voorselectie, niet "dan maar iets".

**De opname beslist nu, niet de keuzelijst.** Zonder EEG-kanaal wordt een run
als polygrafie behandeld, welk studietype er ook is aangevinkt. Dat vergeten was
precies wat er gebeurde: het studietype stond op PSG, de neusdruk stond als EEG
klaar, en er kwam een hypnogram uit een drukcurve. Bij polygrafie wordt de
staging-EDF niet meer geladen, YASA draait niet, en het EEG-artefactmasker
blijft leeg — dat oordeel kwam toch van een kanaal dat geen EEG is. Het rapport
leest `results["is_polygraphy"]`, dus het label volgt wat er werkelijk gedraaid
heeft: REI, niet AHI.

**Alles wat op staging berust verdwijnt bij polygrafie:** de hypnogram-grafiek,
sectie 1 Slaaparchitectuur, de stadiawissel-matrix en sectie 2 Slaapcycli. Ook
de KPI-tegels: TST, slaapefficiëntie, inslaaplatentie en WASO zijn
staging-uitkomsten en stonden er met TST 390 min en SE 72,3 % op grond van dat
hypnogram uit een drukcurve. Daar staan nu **registratietijd** en **REI-noemer**
— de twee getallen waarmee een lezer de REI kan narekenen.

Een hypnogram met 11 slaapcycli en REM-latentie 6 minuten, gescoord op een
drukcurve, is geen zwak hypnogram maar een betekenisloos hypnogram. Een grafiek
die eruitziet als een hypnogram nodigt uit om hem te lezen.

## v0.19.2 — 2026-08-07  *(polygrafie: REI over registratietijd; psgscoring 0.14.6)*

Aanleiding is één rapport met de kop **REI 81000,0/u — Ernstig SAS — therapie
CPAP** bij 81 hypopnees. Vijf defecten in één keten; de zesde schakel zat in
psgscoring en is daar gerepareerd (0.14.6).

**1. Polygrafie eist geen EEG-kanaal meer.** Zolang dat wel zo was, vulde de
gebruiker er iets anders in om verder te kunnen — hier de neusdruk. YASA
stageerde daarop, de artefactdetector keurde alle 1078 epochs af (terecht, hij
keek naar hetzelfde niet-EEG-kanaal), en daarmee viel de noemer van elke index
weg. En er WAS geen keuze "diagnostische polygrafie": wie er een deed moest
`diagnostic_psg` nemen, dat een EEG eist. Die optie staat er nu.

**2. Bij polygrafie gaat de index over registratietijd.** De staging wordt
overgeslagen en elke epoch telt mee, zodat de noemer de registratietijd ís. Dat
is wat het rapport altijd al beweerde te tonen ("events per uur registratietijd
(TIB) i.p.v. TST") maar nergens berekende. Voor deze opname: 81 / 8,98 u =
**9,0/u — mild**.

**3. 100 % artefact is een blokkerende bevinding.** Bij polygrafie wordt het
EEG-artefactmasker genegeerd — dat oordeel komt niet van een EEG. Keurt de
detector op een echte PSG alles af, dan komt er een `blocking`-waarschuwing in
`analysis_warnings` in plaats van een voetnoot onderaan het rapport.

**4. Het herkomstblok toetst zichzelf.** Het toonde `EOG1` en `EMG1` terwijl die
kanalen niet in het EDF zaten: het rapporteerde de KEUZE uit de jobconfig, niet
de UITVOERING — precies de fout waartegen het blok bestaat. Kanalen die niet in
het bestand voorkomen worden nu als zodanig gemarkeerd. En het arousal-EEG komt
erbij te staan wanneer het afwijkt van het staging-EEG: op deze opname C3 tegen
C4, twee EEG-kanalen in één run waarvan het rapport er één toonde.

**5. Eén gedeelde regel voor het studietype.** `"_pg_" in study_type` stond op
drie plaatsen en mist `diagnostic_pg` — geen sluitende underscore. Nu
`myproject/study_type.py`, met een toets op hele woorden en een test dat
`titration_psg_cpap` niet per ongeluk als polygrafie gelezen wordt.

234 tests groen.

## v0.19.1 — 2026-08-06  *(de A/B/C-graad eruit; psgscoring 0.14.5)*

**Verwijderd: de A/B/C-robuustheidsgraad**, uit de studielijst en uit de
FHIR-export.

Die graad telde hoeveel van `strict`, `standard` en `sensitive` dezelfde
ernstklasse gaven, en veronderstelde daarmee dat die drie een ordening vormen:
`strict <= standard <= sensitive`. Die ordening bestaat niet. Gemeten op
PSG-IPA met een manueel hypnogram geeft `sensitive` op **5 van de 5** opnames
minder events dan `standard`, en `strict` op **2 van de 5** meer — op SN2 17,1
tegen 9,3. De oorzaak is aanwijsbaar: `strict` draait met
`breath_level_detection=False`, en `sensitive` draagt `flow_smoothing_s=5.0`,
dezelfde parameter die in v0.2.8 uit de standaard verdween omdat hij op SN1
+54 valse hypopnees veroorzaakte. De namen beschrijven de bedoeling, niet het
gedrag.

Uit het PDF-rapport was hij al weg (v0.15.0). Hij bleef staan op precies de
twee plekken waar een lezer hem niet kan wegen: een gekleurd bolletje in de
studielijst, dat leest als een kwaliteitsoordeel, en een letter in de
FHIR-conclusie die een ontvangend systeem overneemt.

**Het AHI-interval blijft.** Dat is `min()`/`max()` van drie getallen en
veronderstelt geen volgorde; alleen de graad rustte op die aanname. psgscoring
blijft `robustness_grade` gewoon berekenen — wie het wil gebruiken haalt het
uit `pneumo.ahi_interval`.

Negen regressietests voeren een resultaat *met* `robustness_grade: "C"` aan en
controleren dat er niets van in de lijst of de bundel opduikt, dat AHI en OAHI
blijven staan, en dat de vertaalsleutels weg zijn — dode labels zijn hoe een
verwijderde kolom stilletjes terugkeert.

**psgscoring 0.14.4 -> 0.14.5.** Twee nieuwe exploratieve profielen
(`aasm_v3_breath_dual`, `aasm_v3_prob_dual`) en een per-kanaal thermistorpoort
die alleen op die twee aanstaat. Elk klinisch profiel is byte-identiek. De
profielkeuzelijst gaat van 13 naar 15, de per-gebruiker-standaard van 11 naar
13.

218 tests groen.

## v0.19.0 — 2026-08-05  *(scoringsprofiel per gebruiker)*

Geen psgscoring-wijziging (blijft 0.14.4).

De slaaptechnici gaan profielen naast elkaar testen. Zonder dit moet ieder van
hen bij élke opname dezelfde dropdown opnieuw goed zetten, en één vergeten klik
maakt een vergelijking stil ongeldig — precies het soort fout dat je pas ziet
als je twee rapporten naast elkaar legt.

**Nieuw:** `User.default_profile`. Een admin of site-manager zet per gebruiker
welk profiel voorgeselecteerd staat; in de gebruikersbeheerpagina staat er een
kolom bij en een eigen formulier per rij.

**De keuze blijft een keuze.** Er verschuift alleen het `selected`-attribuut;
de dropdown op de kanaalkeuzepagina bevat onverkort alle profielen en de
technicus kan per opname iets anders kiezen. Vier tests dwingen dat af,
waaronder één die controleert dat er precies één optie voorgeselecteerd staat —
meerdere `selected` in één `<select>` is stil gedrag waarbij de browser de
laatste houdt, en dat was de radiogroep-bug van 4 augustus.

**Terugvallen doet het naar de applicatiestandaard**, niet naar niets: leeg
gelaten of een profiel dat niet meer in de psgscoring-registry zit geeft
`aasm_v3_rec`. De keuzelijst komt uit die registry, dus een nieuw profiel
verschijnt vanzelf en een verdwenen profiel valt vanzelf weg.
`mesa_shhs` en `chicago_1999` staan er niet in — die bestaan om gepubliceerde
cijfers te reproduceren, niet om patiënten mee te scoren.

**Toegang** volgt de bestaande regel: een site-manager mag alleen zijn eigen
site-gebruikers aanpassen, net als bij wachtwoord resetten en verwijderen.

**Migratie.** De kolom komt er via het bestaande lichte SQLite-migratiepad bij
het opstarten, zonder default — NULL betekent applicatiestandaard, en dat is
exact het gedrag van vóór deze versie. Vooraf drooggedraaid op een kopie van de
productiedatabase: 6 gebruikers, 3 sites en 15 jobs behouden, alle bestaande
gebruikers op NULL, wachtwoordhashes ongemoeid.

15 nieuwe tests, 209 groen.

## v0.18.5 — 2026-08-05  *(het herkomstblok sprak zichzelf tegen)*

Geen psgscoring-wijziging (blijft 0.14.4).

Het herkomstblok kende drie thermistor-gevallen — afwezig, afgekeurd, bruikbaar
— en er zijn er vier. Bij een **additief** profiel (`aasm_v3_dual`,
`aasm_v3_fusion`) wordt een thermistor die de kwaliteitstoets níet haalt tóch
behouden, omdat de tweede detectiepas hem onschadelijk maakt vóór de
apneutelling. Het blok noemde hem dan "bruikbaar".

Gevonden door twee rapporten van één opname naast elkaar te leggen. Het blok
meldde *"Flow Th. — bruikbaar (0.23)"* terwijl de drempel op 0,40 ligt en de
corroboratiekolom twee bladzijden verderop toonde dat diezelfde sensor **0 van
de 95 apneus** had bijgedragen. Het rapport sprak zichzelf tegen — precies het
soort tegenspraak dat dit blok moest wegnemen.

Nu vier gevallen, met het getal erbij zodat de lezer ziet hoe zwak de steun is:

| situatie | tekst |
|---|---|
| geen thermistor | *niet in montage* |
| afgekeurd, vervangen door de neusdruk | *afgekeurd door kwaliteitscontrole (0.32)* |
| onder de drempel, additief behouden | *onder de kwaliteitsdrempel, additief gebruikt — mag events toevoegen, niet afwijzen (0.23)* |
| boven de drempel | *bruikbaar (0.71)* |

Drie nieuwe tests, waaronder één die afdwingt dat de vier gevallen verschillende
tekst opleveren. 194 tests groen.

## v0.18.4 — 2026-08-05  *(twee experimentele profielen erbij)*

`psgscoring[ml]` 0.14.3 → **0.14.4**. Geen YF-codewijziging.

Twee nieuwe profielen verschijnen in de v3-groep van de dropdown, allebei met
**(experimental)** in hun naam omdat ze dat zijn:

- **`aasm_v3_prob`** — de arousal-as van de ademteug-detector was als enige nog
  een drempel: `p_arousal` sprong naar 0,90 zodra er een arousal in het venster
  lag, waardoor de bevestiging nooit onder 0,90 kwam hoe klein de desaturatie
  ook was. Nu gewogen (0,70) en gegradeerd op koppelingslatentie. Op PSG-IPA
  (n = 5): F1 0,453 tegen 0,434, precisie 0,72 → 0,79, en het aantal events dat
  géén van de twaalf scoorders markeerde daalt van 69 naar 47.
- **`aasm_v3_fusion`** — de sensorovereenstemming tussen thermistor en neusdruk
  telt als gewicht in plaats van als poort. Elke apneu draagt
  `sensor_agreement`, en een apneu waarvan de thermistor de enige steun is
  krijgt zijn confidence daarmee geschaald. **Niet gevalideerd**: die as is op
  PSG-IPA principieel niet te meten, want die montage heeft één flowkanaal.

Beide staan in de familie `exploratory` en veranderen niets tenzij iemand ze
kiest. Elk bestaand profiel is byte-identiek.

## v0.18.3 — 2026-08-04  *(platform en rapport — punt 3 uit het backlog)*

### EDF anoniem verwerken via de GUI — twee routes

Het verschil tussen de twee zit in waar de identificeerbare header terechtkomt.

**Anoniem opladen.** De browser herschrijft de header vóór verzenden
(`static/edf_anonymize.js`). Naam, geboortedatum, patiënt-ID, ziekenhuis en
technicus verlaten die computer niet. De signaaldata blijft ongemoeid: er wordt
een Blob gebouwd van `[nieuwe header, file.slice(256)]`, en die slice is een
luie verwijzing — er wordt niets van de gigabytes gekopieerd. De bestandsnaam
gaat mee, want die draagt in de praktijk vaker een naam dan de header.

**Anonimiseren na het opladen.** Op de kanaalkeuzepagina staat een paneel met
de headervelden zoals ze nu zijn, en een knop die ze ter plekke wist
(`POST /anonymize/<job_id>`). Wie ziet dat de naam van zijn patiënt in het
bestand staat, doet het de volgende keer vooraf.

Beide routes laten een eigen **studienummer of label** toe. Leeg gelaten valt
het terug op een deterministisch pseudoniem, zodat twee analyses van dezelfde
nacht koppelbaar blijven zonder de naam terug te halen. Het patiëntnummerveld op
de kanaalkeuzepagina leest daarna gewoon die code uit de header.

Twee implementaties van dezelfde regels is een uitnodiging om uiteen te lopen,
en het gevolg zou onzichtbaar zijn: dezelfde opname zou via de twee routes een
andere code krijgen en de analyses zouden niet meer aan elkaar te koppelen zijn,
terwijl beide resultaten op zichzelf correct ogen. Daarom draait er een test die
het echte JavaScript in Node uitvoert en de uitvoer veld voor veld met Python
vergelijkt. Zonder Node wordt die overgeslagen — met een skip-reden die zegt dat
de gelijkheid dan onbewaakt is.

De harde eis staat apart vastgelegd: de header is een blok van vaste lengte, en
één byte erbij verschuift elke sample-offset in het bestand.

### Landingspagina zonder superlatieven

"Heruitgevonden" is een claim die niemand kan nakijken. De titel zegt nu wat het
doet en meteen de belangrijkste beperking: *Automatische slaapanalyse, door de
arts nagekeken*. "AASM v3-compliant" — een conformiteitsclaim die hier niemand
heeft getoetst — werd "scoring volgens AASM v3". "State-of-the-art" verdween uit
de YASA-beschrijving. En "rapporten binnen seconden" was gewoon onjuist: een
volledige PSG-analyse duurt minuten.

Nieuw boven de vouw, niet alleen in de disclaimer onderaan: screeningsinstrument
en second opinion, geen medisch hulpmiddel, geen diagnose — elke uitkomst is een
voorstel dat een arts moet nakijken. Voor een externe onderzoeker is dat
bovendien geloofwaardiger dan een superlatief.

### Geschiedenis en overzicht samengevoegd

Er waren twee views op dezelfde studies met net andere kolommen: de geschiedenis
had OAHI, centrale index en het OSAS/CSAS-onderscheid, het overzicht had grade,
ODI, PLMi, signaalkwaliteit, archief en het site-filter. Wie een getal zocht
moest weten in welke van de twee het stond.

Eén chronologische lijst nu, met beide kolomsets. `/results` blijft bestaan als
doorverwijzing — er staan bladwijzers naar die URL en de sneltoets `g h` gaat
erheen — en de navigatie heeft één ingang in plaats van twee. `results_history.html`
en de bijbehorende directory-scan zijn verwijderd; zodra de `Job`-tabel de scan
vervangt, is deze lijst een query.

### BMI

Rekent zichzelf uit lengte en gewicht, en wijkt voor een handmatige invoer.
Buiten 10–80 kg/m² blijft het veld leeg — dan is er vrijwel zeker een eenheid
verwisseld.

**45 nieuwe tests, 191 groen.**

## v0.18.2 — 2026-08-04  *(het rapport zei de methode, niet de uitvoering)*

`psgscoring[ml]` 0.14.1 → **0.14.2**.

De YF-wijzigingen hieronder lezen alleen data die psgscoring al meelevert en
raken de scoring niet. **Wat wél verschuift, komt uit psgscoring 0.14.2:** de
samenvatting wordt herberekend ná de CSR-herklassificatie, dus `oahi` en de
apneutype-tellingen kunnen afwijken van een rapport op 0.14.1 — en daarmee de
OSAS-gradatie — zonder dat er één event verschoven is. `ahi_total`, de
eventtelling en alle andere indices blijven gelijk. Zie de psgscoring-changelog
(issue #18).

### De kanaalkeuze in de UI was niet wat het overzicht toonde

In `channel_select.html` kreeg binnen één radiogroep **elk** matchend kanaal het
attribuut `checked` — bij EOG (`'EOG' in naam`) en bij EMG (`'EMG'` of
`'CHIN'`). Bij radio's met dezelfde `name` wint de laatste, terwijl de
auto-detect-tabel erboven de **eerste** match toont. Op een montage met
EMG1/EMG2/EMG3 stond er dus "EMG1" in het overzicht terwijl **EMG3** de
slaapstaging voedde; bij twee EOG-kanalen idem.

Dat is niet cosmetisch. De staging leest precies drie kanalen
(`tasks.py:166-170`), dus wie het EMG of EOG verschuift, verschuift het
hypnogram — en daarmee TST, en daarmee de AHI. Twee runs van dezelfde nacht met
een iets andere exportmontage kregen zo verschillende getallen zonder dat er
iets aan de scoring veranderd was.

Nu vinken het overzicht en het formulier hetzelfde kanaal aan (één bron:
`_eog_auto` / `_emg_auto`), wordt been-EMG (`PLM`, `LEG`, `TIB`, `BEIN`,
`JAMBE`) uitgesloten van de EMG-autokeuze — YASA's REM-detectie steunt op
kin-atonie, en tibialis anterior is daar geen vervanging voor — en wint een
expliciet kin-kanaal van een generiek EMG-kanaal.

### Nieuw: herkomstblok onder de kanaallijst

Welk kanaal welke analyse voedde: staging-EEG/EOG/EMG, apneu- en
hypopneukanaal, de flow-referentie van de vijf afgeleide analyses (alleen
getoond wanneer die afwijkt), thermistorstatus met de overeenstemmingswaarde,
profiel en beide softwareversies. Daarmee is een rapport zonder logs te
reproduceren en zijn twee runs mechanisch te vergelijken — en het is de
provenance die de externe centra vragen.

### De sensornoot volgt nu de feiten, niet het profiel

Drie gevallen in plaats van twee. Nieuw is het middelste: een thermistor die
wél in het bestand zit maar de kwaliteitstoets niet haalt. Het rapport meldde
dan "één flowkanaal beschikbaar" terwijl de kanaallijst erboven er twee
toonde — het sprak zichzelf tegen. Afwezig en afgekeurd is niet hetzelfde, en
de lezer hoort het verschil te zien, inclusief de envelope-overeenstemming die
tot de afwijzing leidde.

Bij twee bruikbare sensoren komt er een waarschuwing bij wanneer de duale pas
liep en **geen enkele** apneu door de thermistor bevestigd is: de noot claimt
"apneu op thermistor", en de corroboratiekolom sprak dat in een echt rapport
tegen.

De keuze zit nu in `flow_sensor_notes()` en `provenance_rows()` — losse
functies met eigen tests, niet meer verstopt in de PDF-opbouw.

### Minimale hartfrequentie wordt niet meer getoond als hij de filtergrens is

Drie opnames rapporteerden een minimum van 20,2 · 32,6 · 20,0 bpm. Twee daarvan
liggen exact op de ondergrens van het plausibiliteitsfilter in psgscoring — de
signatuur van een oximeter die even loslaat, niet van bradycardie. Markeert
psgscoring de hartfrequentie als onbetrouwbaar, dan toont het rapport de 1e en
99e percentiel in plaats van de extremen, met de reden erbij.

### Noot bij de hypoxic burden boven T90 > 30%

HB meet event-gerelateerde desaturatie *ten opzichte van de baseline*. Bij
aanhoudende hypoxemie ligt die baseline al laag en ogen de dips klein: één
patiënt zat 94,6% van de nacht tussen 80 en 90% met een baseline van 85% en
kreeg HB 21,6 — net boven de laagrisicodrempel. Het getal klopt, de indruk niet.

29 nieuwe tests; 142 in totaal groen.

## v0.18.1 — 2026-08-03  *(twee rapportgetallen die het verkeerde lazen)*

`psgscoring[ml]` 0.14.0 → **0.14.1**. Geen template- of routewijziging; de
scoringprofiel-dropdown vult zich uit de psgscoring-registry, dus het nieuwe
profiel verschijnt vanzelf in de v3-groep.

Beide fouten kwamen aan het licht door twee rapporten van één opname naast
elkaar te leggen — `aasm_v3_rec` op v0.13.1 tegen `aasm_v3_dual` op v0.14.0.
**De kop was in beide runs stabiel** (severe CSAS, mild OSA, hetzelfde
automatische besluit). Dit zijn de getallen eronder.

### De rij "Rule 1B / CMS — ≥30% flow + ≥4% desat" was geen 4%-getal

Dat veld vulde zich met de AHI van de `strict`-arm uit de robuustheidssweep.
Maar `aasm_v3_strict` is een *conservatieve variant van Rule 1A*: het houdt
`desat_or_arousal` met een drempel van 3% aan en verschilt in het
stabiliteitsfilter, breath-level-detectie en het nadirvenster. Er is dus
**nooit een 4%-criterium toegepast** op het getal onder die kop — in geen enkel
rapport sinds het veld in v0.15.0 verscheen.

Het oude getal kon beide kanten op fout zijn: op de aanleidende opname stond er
10,3/u terwijl er 78 apneus waren (apneu-index 21,2/u), en op een testgeval
37,9/u tegenover Rule 1A 31,6/u — méér events onder een strenger criterium.
Rule 1B komt nu uit de eventlijst zelf en kan noch boven Rule 1A, noch onder de
apneu-index uitkomen. Zonder geslaagde SpO₂-analyse verdwijnt de rij in plaats
van te vervallen tot "alleen apneus".

**Dit verandert geen scoring** — de kop-AHI, de OAHI, de ernstgradatie, het
automatische besluit en de eventtellingen lezen dit veld niet. Het is één rij.

### Vijf analyses lazen het apneukanaal terwijl ze flow wilden

De AHI-sweep, de anker-basislijn, de arousal/RERA-koppeling, de
Cheyne-Stokes-detectie en de ventilatory burden nemen alle vijf een flowsignaal
zonder apneus te detecteren — en namen alle vijf het *apneukanaal*. Onder
`aasm_v3_dual` is dat de thermistor, bewust ook wanneer die de kwaliteitstoets
niet haalt, omdat de tweede detectiepas hem onschadelijk maakt vóór de
apneutelling. Die vijf kennen die tweede pas niet.

Op de aanleidende opname las de ventilatory burden daardoor **20,4% in plaats
van 42,6%** — onder de ≤25%-referentie — bij een patiënt die 94,7% van de nacht
onder 90% saturatie lag.

### Nieuw in de dropdown: `AASM v3 — Rule 1A, nasal-pressure reference`

Dezelfde correctie als los kiesbaar algoritme, zodat je op een echte opname
kunt zien wat de referentiekeuze doet los van de dual-sensordetectie.

| profiel | apneus | afgeleide analyses |
|---|---|---|
| `AASM v3 — Recommended` | thermistor¹ | thermistor¹ |
| **`AASM v3 — nasal-pressure reference`** | thermistor¹ | **neusdruk** |
| `AASM v3 — dual-sensor apneas` | **beide, samengevoegd** | neusdruk |

¹ als die de kwaliteitstoets haalt; anders neusdruk.

Identiek aan `Recommended` op elke montage zonder bruikbare thermistor — dat
zijn de meeste klinische montages, en alle Somnomedics-opnames waarop dit
gevonden is.

## v0.18.0 — 2026-08-03  *(the dual-sensor profile, and what it did or did not use)*

`psgscoring[ml]` 0.13.1 → **0.14.0**.

**v0.17.5 was rolled back on 2026-08-02.** It shipped psgscoring 0.13.2, which
scored apneas on the thermistor wherever one was detected. On a real recording
with human scoring apneas went from 93 to 0, AHI from 26.2 to 8.6, and the
conclusion from *moderate CSAS* — confirmed by the human scorer — to *mild SAS*.
Production and the VM were returned to v0.17.4 / psgscoring 0.13.1 the same day.

**Default scoring in this release is that rolled-back-to behaviour, unchanged.**
`aasm_v3_rec` stays the default profile and is byte-identical. What is new is a
second algorithm you can *choose*.

### Choosing the algorithm and the channels

- **`AASM v3 — Rule 1A, dual-sensor apneas` appears in the scoring-profile
  dropdown.** It detects apneas on *both* flow sensors and merges them, so
  neither channel can veto the other. The list is built from
  `psgscoring.list_profiles()`, so it populated itself.
- The two flow channels each keep their own dropdown — `🌡️ Thermistor (apnea)`
  and `🌬️ Nasal pressure (hypopnea)` — with auto-detection as the default and a
  ★ marking what was detected. Same recording, two algorithms, from the web UI.

### What the report now says

- **Corroboration columns.** Under the dual profile each apnea shows whether it
  was seen by both sensors, the thermistor only, or nasal pressure only. The
  note under the table states plainly that single-sensor events are **not
  rejected** — the column is information, not a filter. The columns stay away
  from single-sensor runs, where they would be three empty columns.
- **Dual scoring requested but not performed** now lands in the *Aandachtspunten*
  box, naming the channel that was used instead. A silently single-sensor run was
  the failure mode that made v0.17.5 hard to see.
- The single-flow-channel note names the channel and says apneas on nasal
  pressure over-detect relative to the thermistor.

Translations for all of it in nl/fr/en/de. 113 tests pass, including ones that
render the PDF and read the text back.

## v0.17.5 — 2026-08-02  *(both AASM flow sensors, selectable and shown)*

`psgscoring[ml]` 0.13.1 → **0.13.2**, which makes the AASM two-sensor rule
fire: **apneas on the oronasal thermistor, hypopneas on nasal pressure.**

**This changes scoring on any recording carrying a thermistor the previous
version did not recognise** — Somnomedics `Flow Th.` in particular. Apneas
were being scored on nasal pressure, which drops more readily on partial
obstruction and mouth breathing and therefore over-detects; the AASM
specifies the thermistor for apneas to avoid exactly that. Existing reports
are unaffected, but re-running an EDF will give different apnea counts than
before.

**The two sensors are now selectable and visible.** The channel form offered
only a generic `flow`; the two AASM roles came purely from auto-detection and
could not be corrected when it failed. Now:

- `🌡️ Thermistor (apnea)` and `🌬️ Nasal pressure (hypopnea)` are their own
  fields, with the generic `flow` beneath them relabelled as what it is — a
  fallback when both are missing.
- Both appear in the auto-detected overview at the top, so a missing
  thermistor is visible before the analysis starts rather than inferable from
  the report afterwards.

**The single-sensor case no longer stays silent.** When only one flow channel
is available the report now names it and states the consequence, mirroring
the existing dual-sensor note:

> *One flow channel available: apnea and hypopnea both scored on {channel}.
> The AASM specifies apnea on the oronasal thermistor and hypopnea on nasal
> pressure; scoring apneas on nasal pressure may over-detect.*

That note previously appeared only for the two-sensor case, and it appeared
wrongly — psgscoring's `dual_sensor` flag meant "a hypopnea channel exists",
not "two sensors", so the report claimed AASM dual-sensor methodology on
single-channel studies. Fixed in 0.13.2.

All new strings in nl/fr/en/de.

## v0.17.4 — 2026-08-02  *(fix: the subtype row printed a black box)*

The `↳` introduced in v0.17.3 is not in the report font, so ReportLab
substituted a black box. That is worse than a missing character here: `■` is
this report's legend swatch (`■ W ■ N1`, `■ OA obstructief`), so the row read
as a third meaning of the same mark. Replaced with `·`, which the report
already uses elsewhere. Caught on a real study, not in review.

`test_subtype_rows_use_a_glyph_the_font_actually_has` now asserts the
rendered line contains neither `■` nor `↳` — it catches any glyph that
triggers the font fallback, not just this one.

## v0.17.3 — 2026-08-02  *(the restored event fields now reach the report)*

v0.17.2 restored `min_spo2` and the hypopnea subtyping to the *event records*
but not to the PDF. This puts them in the report, where they are of use to
whoever signs it. No scoring change.

- **"Lowest SpO₂ during an event"** joins the saturation table. It is
  deliberately a separate line from the night minimum directly above it:
  that minimum can come from an artefact or from a dip outside every event,
  while this value is attributable to a scored event. Shown only when at
  least one event carries a nadir.
- **Hypopnea subtyping** appears as indented `↳ of which central` /
  `↳ of which mixed` rows beneath the hypopnea row, with the same star
  columns. Shown only when such events exist — in a purely obstructive study
  they would be two zero rows of noise, and in a central picture they are the
  most interesting thing in the table.

Both in nl/fr/en/de.

**How this was verified**, because the previous release claimed a rendering
that did not exist: `myproject/tests/test_pdf_event_fields.py` generates the
actual PDF, reads its text layer back, and asserts each row is present when
it should be *and absent when it should not*. It also pins the confidence-band
caption. The same test would have caught the v0.17.2 mis-statement.

## v0.17.2 — 2026-08-02  *(psgscoring 0.13.1 + honest labelling of the confidence bands)*

Dependency bump: `psgscoring[ml]` 0.13.0 → **0.13.1**. **No scoring change** —
every profile is byte-identical, verified by the psgscoring golden harness.

**The ★ columns in the respiratory table now carry a caption**, and that is
the point of this release. The header reads `★★★ ≥0.85`, a bare number that a
reader naturally takes for a percentage. It is not one. Measured against the
twelve independent scorers of PSG-IPA, the score correlates with the fraction
of scorers marking an event at only **r = 0.19**, and sits over 30 percentage
points too high — an event shown as `★★★ ≥0.85` is marked by about 44% of
scorers. The caption now states what the score is: a ranking of events by how
well they satisfy the AASM criteria, not a probability. Added in nl/fr/en/de.

Two **event-record** fields return from psgscoring 0.13.1, both of which the
breath-graded profile silently dropped:

- **`min_spo2`** — the saturation nadir per event, previously blank.
- **`hypopnea_central` / `hypopnea_mixed`** — hypopnea subtyping. The
  breath detector does no effort-based classification of its own; the label is
  now inherited from the overlapping envelope event, which was classified on
  the same window using effort, ECG and flattening.

**Correction to how this was first written.** These reach the *event records*
— the EDF viewer and the `/api/edf/<job_id>/events/…` endpoints — and **not
the PDF report**. The PDF's "min SpO₂" is the whole-night minimum from the
SpO₂ summary, a different quantity, and the respiratory table has no subtype
rows for hypopneas. Verified by regenerating a real study on 0.17.2: the only
textual change anywhere in the six-page report is the two-line caption above.
Every clinical value — AHI 32.5, Rule 1B 13.0, RERA 75, RDI 52.0, REM/NREM
AHI, artefact count — is identical to the 0.17.1 output, which is the
byte-identity claim holding on real data.

## v0.17.1 — 2026-08-01  *(psgscoring 0.13.0 — breath-graded profile selectable)*

Dependency bump: `psgscoring[ml]` 0.12.1 → **0.13.0**.

**New in the scoring-profile menu: “AASM v3 — Rule 1A, breath-graded”.**
It scores hypopneas with the *breath* as the unit rather than the sample,
calibrates the baseline and that patient's own SpO₂ delay in two passes, and
grades the AASM criteria instead of applying them as hard thresholds. Every
event it produces carries the contribution of each criterion.

**It is not selected by default.** This application passes
`scoring_profile="standard"` explicitly, so unless a user picks the new
profile the analysis is unchanged. No template or route change was needed —
`channel_select.html` builds the menu from the psgscoring registry.

**Scoring changes to be aware of when comparing to earlier runs:**

- **Nasal-pressure sensor assignment is corrected.** A channel named `Pres`
  (NSRR/MESA convention) was claimed by the `pulse` role, so hypopneas were
  scored from the thermistor. It is now recognised as nasal pressure.
  Recordings whose channels were already resolved correctly are unaffected;
  ordinary clinical PSGs without a channel called `Pres` see no change.
  NSRR/MESA recordings do change (mesa-sleep-2408: AHI 30.4 → 22.0).
- **Arousals reach the EDF+ export and the event API again** (psgscoring
  issue #16 — they were detected but never surfaced). This is additive:
  scoring for existing profiles is byte-identical, because *acting* on the
  repaired arousal list is a per-profile choice that only the new profile
  enables.

## v0.17.0 — 2026-07-29  *(job registry + upload/access hardening)*

Security and architecture. **No scoring change: AHI, events and every reported
value are identical.** The `psgscoring` pin is unchanged (0.12.1).

- **Path traversal in the chunked upload closed.** `file_id` came straight from
  the browser and was interpolated into filenames with an f-string, so it was
  never a separate `os.path.join` component and `../` escaped the upload
  directory (`file_id="../../../tmp/evil"` → `/tmp/evil_chunk_0`). Verified
  exploitable by any logged-in user. `file_id` is now restricted to
  `[A-Za-z0-9_-]{1,64}` (which covers both shapes the frontend generates), and
  every derived path — chunks, `_assembled.edf`, the final filename, the
  collision rename and the cleanup unlink — is resolved against
  `realpath(upload_dir)` and rejected if it lands outside.
- **Job access control moved to the database.** Authorisation used to be read
  from `{job_id}_results.json` with an `except Exception: pass` that silently
  returned `None`, which made every check best-effort. A new `job` table
  (`job_id`, owner, `site_id`, filename, status, timestamps) is now the source,
  and `@job_access_required` is applied to **all 30** `<job_id>` routes — eight
  of which had no check at all (`api_get_conclusion`, `api_save_conclusion`,
  `api_save_scoring`, `score_editor`, `channel_select`, `api_scoring_status`,
  `job_status`, `api_job_status`). A test over `app.url_map` fails if a new job
  route ever ships without it.
- **Access rule.** Admin, or the owner, or the same `site_id`. The owner rule now
  also applies cross-site, matching what the dashboard listing always did — a
  study could previously appear in someone's list and still 403 on opening.
- **Transition.** `JOB_ACCESS_STRICT` (default `"0"`) lets a job without a row
  fall back to the JSON while logging `job access fallback` with its `job_id`;
  `"1"` makes it a 404. `backfill_jobs.py` imports existing studies and is
  idempotent, and `deploy.sh` runs it on every deploy (new step 10/11).
- **`SESSION_COOKIE_SECURE`** in `config.json.example` was the JSON boolean
  `true` while the app tests `== "1"`, so the secure flag was silently off. The
  template is now the string `"1"`. **Existing installations must change this in
  their own `instance/config.json`** — `deploy.sh` never overwrites it.

## v0.16.5 — 2026-07-26  *(hide VB reference for central-dominant studies)*

Content-only. The ventilatory-burden reference (≤ 25 %) is now hidden when > 50 % of
apneic events are central (CSAS / Cheyne-Stokes). The VB norm (AJRCCM 2023) is derived
and validated in OBSTRUCTIVE OSA cohorts and is inherently very high in central apnea by
morphology, so comparing against ≤ 25 % would mislead. The VB value itself stays shown.
Applies to the PDF and web reports. No scoring change.

## v0.16.4 — 2026-07-26  *(de-detail ML tooltip)*

Content-only. Removed the internal manuscript reference ("paper v35 §3.6.1") and model
version tag from the `ml_help` scoring-profile tooltip — now simply "LightGBM candidate
classifier (enabled by default only on mesa_shhs)". No scoring change.

## v0.16.3 — 2026-07-26  *(disclaimer fix + landing-page publication wording)*

Content-only. No scoring or pin change.

- **PDF disclaimer**: fixed "Vallat \& Walker" → "Vallat & Walker" (`\&` → `&amp;`, was
  rendering a literal backslash) and dropped the internal "(paper v35)" version tag.
- **Landing page**: the peer-reviewed-publication item no longer names the target journal,
  manuscript version, or co-authors — now simply "a peer-reviewed publication … is in
  preparation".
- **Landing page roadmap**: removed the "Update to AASM Manual v3.0" card — that work is
  done and already listed under "What's New".

## v0.16.2 — 2026-07-26  *(landing page refreshed with current feature set)*

Content-only (public landing page at `/`). No scoring or pin change.

- **"What's New" section rewritten** to the current clinical highlights: AASM v3-compliant
  scoring, dual AHI (Rule 1A vs 4 %/CMS), ventilatory + hypoxic burden, clinical phenotypes
  (POSA / REM-predominant), the clinician-focused report, and arousal aetiology + OSAS/CSAS
  typing. Removed the now-obsolete "OAHI 3-point sweep" item (that feature was dropped from
  the report in v0.15.0).
- Hero badge → "AASM v3 · …"; AASM stat pill → "AASM v3-compliant"; tech stack now shows
  `psgscoring 0.12` (was 0.6). All copy in NL/FR/EN/DE.

## v0.16.1 — 2026-07-26  *(ventilatory burden made breath-based)*

Requires **psgscoring 0.12.1** (pin bumped). No report-code change — VB already renders
as a bounded `%` with reference ≤ 25 %.

- **Ventilatory burden is now breath-based** (psgscoring 0.12.1): the proportion of
  breaths whose peak amplitude is < 50 % of the eupneic baseline. v0.16.0 showed the
  time-fraction over the flow envelope, which over-counted inter-breath troughs and gave
  implausible values (e.g. 82.9 % on a severe recording). The displayed `%` is now the
  correct, bounded metric.

## v0.16.0 — 2026-07-26  *(VB recalibration + saturation bands + arousal-aetiology fix)*

Requires **psgscoring 0.12.0** (pin bumped). Three fixes found while verifying a real
v0.15.0 report; no change to AHI/OSAS numerics.

- **Ventilatory burden** is now the validated metric — **% of sleep with airflow < 50%
  of the eupneic baseline** (proportion of "small breaths"; AJRCCM 2023) — shown as a
  bounded `%` with reference **≤ 25%** in the PDF + web report (was an unbounded
  `%·min/h` value marked *experimental*, which produced implausible numbers, e.g. ~1074).
- **Time-in-saturation-bands table is populated.** psgscoring 0.12.0 now emits the band
  keys the table reads (`time_95_100_min` … `time_below_70_min`); previously all rows
  showed 0.0%. No YF code change — the reader already expected these keys.
- **Arousal-aetiology indices reconcile with the arousal index** (psgscoring 0.12.0):
  respiratory + spontaneous arousal indices now sum to the arousal index (were computed
  against a different TST); PLM arousal index reported as a subset of spontaneous.

## v0.15.0 — 2026-07-26  *(clinician-focused PDF report; AASM v3 enrichments; removals)*

Requires **psgscoring 0.11.0** (pin bumped). PDF report reworked for the clinician;
no change to scoring numerics.

**Added (PDF report)**
- **Auto-generated conclusion** (informational; never overrides the physician's manual
  diagnosis) — one structured sentence: severity + syndrome + phenotype + burden qualifiers.
- **Dual AHI** table — AASM v3 Rule 1A (≥3% desat *or* arousal) vs Rule 1B / CMS (≥4% desat),
  side by side with per-rule severity (from psgscoring `summary["ahi_dual"]`).
- **AASM AHI severity reference scale** (&lt;5 / 5–15 / 15–30 / &gt;30) under the AHI bar.
- **Page-1 phenotype line** (POSA / REM-predominant) and a **"Aandachtspunten" box**
  (descriptive attention points — explicitly *not* medical advice).
- **Arousal aetiology** as per-hour indices (respiratory / spontaneous / PLM arousal index).
- **Ventilatory burden** now labelled *experimental — scale not yet calibrated*.

**Removed (from the clinical PDF, per site request)**
- **Signal-quality & confidence-review section** (7b) and the page-1 warning banners
  (near-constantly graded "unusable"; still available in the web app).
- **OSAS severity profile** — the strict/standard/sensitive scoring-profile comparison
  table, the AHI-robustness interval, the OAHI 3-point confidence sweep, and the O-S-A-S
  severity-score table (not validated as severity instruments). ESS is kept.

**Fixed**
- KPI syndrome label + apnea-type breakdown line resolved to an empty summary
  (`results["respiratory"]` never existed → generic "SAS"); now read the canonical
  `pneumo["respiratory"]["summary"]`, so the header shows OSAS/CSAS correctly.

## v0.14.0 — 2026-07-25  *(clinical phenotypes + ventilatory burden in the report)*

- **New clinical findings in the report** (from psgscoring 0.10.0; pin `0.9.0 → 0.10.0`):
  - **Positional OSA (POSA)** and **REM-predominant OSA** phenotype flags — shown in
    the PDF (a "Clinical phenotypes" block) and the web report, with the supine /
    non-supine and REM / NREM AHI and, for POSA, positional-therapy candidacy. POSA
    needs a body-position channel; both render only when the criteria are met.
  - **Ventilatory burden** (%·min/h) shown next to the hypoxic burden — a
    cardiovascular-risk pair beyond the AHI. ⚠️ Scale to be calibrated against
    Labarca 2023; no reference range shown yet.
- 7 new NL/FR/EN/DE translation keys. **No AHI / OSAS-CSAS-grade change**; the new
  fields render conditionally (graceful when absent).

## v0.13.0 — 2026-07-25  *(arousal & RERA detection moved to psgscoring; multi-derivation arousals by default)*

- **Arousal & RERA detection now live in `psgscoring` (v0.9.0), not in
  YASAFlaskified.** `myproject/arousal_analysis.py` is now a thin compatibility
  shim that re-exports `psgscoring.arousal`; the detector code moved to the library
  so it is self-contained and versioned. Pin bumped `psgscoring[ml]==0.7.6 → 0.9.0`.
- **Arousals are now scored multi-derivation by default** (central + occipital +
  frontal, event-level union + EOG-reject) for clinical scoring — a more sensitive,
  more human-like operating point (a scorer scans the whole montage). Set
  `PSGSCORING_AROUSAL_DERIVATION=single` to restore single-channel behaviour.
- **Clinical impact:** the **AHI / OSAS-CSAS grade is unchanged** (arousals
  contribute no arousal-only events on the validation cohort; psgscoring's golden
  regression passes). The **arousal index in reports rises** (multi is more
  sensitive) — a deliberate, validated sensitivity-first choice. Validated on
  PSG-IPA (5 recordings × 12 scorers).
- No UI change; PDF/Excel/FHIR reports unchanged in structure.

## v0.12.8 — 2026-07-22  *(analysis history now distinguishes OSAS vs CSAS)*

- **The analysis-history list (`/results`) now shows the apnea *type* and the
  central component, not just a bare AHI.** Two columns were added between OAHI
  and Severity:
  - **Centr.** — the central apnea index (CAI, `central_index`, /h), so a
    central-driven study is visible at a glance.
  - **Type** — an **OSAS** / **CSAS** badge. A study is labelled **CSAS**
    (central-predominant) when the central events make up **≥ 50 % of the AHI**
    (AASM convention), otherwise **OSAS**; below AHI 5 no type is shown. The
    badge carries a tooltip with the full syndrome name.
- The **Severity** badge is now localised (`Mild` / `Matig` / `Ernstig` in NL,
  with FR/EN equivalents) instead of the raw English word, so a row reads e.g.
  *AHI 51.3 · OAHI 6.9 · Centr. 44.5 · **CSAS** · **Ernstig*** — an *Ernstig
  CSAS* at a glance, no longer indistinguishable from an obstructive study.
- Classification is a list-level heuristic in `_sas_type()` (`app.py`); the PDF
  report remains the source of truth for the full event breakdown. No scoring
  change; new NL/FR/EN i18n keys (`resp_type`, `osas`, `csas`, `central_ahi_*`,
  `osas_full`, `csas_full`); NL `sev_mild` label aligned to "Mild".
- **Terminology harmonised:** the Dutch conclusion/diagnosis texts for mild OSAS
  now read **"Mild OSAS"** instead of "Licht OSAS" (`STANDARD_CONCLUSIONS`,
  `concl_mild_title`/`concl_mild_body`, `dx_mild_osas`, and the arousal-latency
  note), matching the new history badge. FR ("léger") / EN ("mild") / DE
  ("leichtes") were already correct and are unchanged; the N1 sleep-stage label
  "Licht" (= light sleep) is a different concept and stays.

## v0.12.7 — 2026-07-22  *(fix: browser served a stale report from cache after re-analysis)*

- Follow-up to v0.12.6. Even with `no-cache` response headers, a browser that
  had **already** cached `/results/<job_id>/pdf` (from an earlier, pre-fix visit)
  kept serving the old attachment — a re-analysis reuses the same `job_id`, so
  the download URL was unchanged and the browser never re-fetched. Users saw the
  pre-fix report (e.g. a Cheyne-Stokes study with RDI=0) despite the server
  holding the corrected one.
- **Fix:** the PDF/Excel download links now carry a `?v=<results.json mtime>`
  cache-buster (`report_ver()` Jinja global). A re-analysis rewrites
  `results.json`, so the link changes and the browser fetches the fresh report.
  Server-side content was already correct; this makes the client always request
  it. No scoring change.

## v0.12.6 — 2026-07-22  *(fix: re-analysis served a stale cached report)*

- **A re-analysis now always yields the up-to-date PDF/Excel.** After
  re-analysing an existing study, the download could still hand back the
  *previous* report: the download URL (`/results/<job_id>/pdf`) is identical
  across re-analyses, so the browser served its cached copy, and the on-the-fly
  fallback only regenerated when the file was *missing* — not when it was
  *older than the fresh results*. Concretely, a study re-scored on psgscoring
  0.7.6 (e.g. a Cheyne-Stokes patient whose RDI/REM-NREM AHI were restored)
  could still download the pre-fix PDF.
- **Fix** (`app.py`): report downloads now (a) regenerate the PDF/Excel when the
  artifact is older than `{job_id}_results.json`, and (b) send
  `Cache-Control: no-cache, no-store, must-revalidate` so the browser always
  fetches the current file. `/psg` redirects to `/pdf` and is covered too.
- No scoring change; server-side results were already correct after re-analysis.

## v0.12.5 — 2026-07-22  *(psgscoring 0.7.6 — RERA/CSR + hypoxic-burden fixes)*

Bumps the pinned scoring library to **psgscoring 0.7.6** (`requirements.txt`,
`version.py`). No YASAFlaskified code change.

- **RDI/RERA now appear on Cheyne-Stokes reports.** psgscoring 0.7.6 fixes a bug
  where the RERA index, RDI and REM/NREM AHI were silently dropped from the
  respiratory summary on CSR-positive recordings — so the PDF/Excel reports
  showed a blank RDI for those patients. They now render correctly.
- **Hypoxic burden corrected on sensor-dropout recordings** (invalid in-sleep
  SpO2 samples excluded from the TST denominator; de Chazal `calcHB.m` reference).
- **No AHI / OSAS-severity change for any patient.** Validated on a real MESA
  A/B (16 recordings): `ahi_total` byte-identical, RERA restored on 9 CSR
  recordings, HB raised on 5 dropout recordings. Also includes psgscoring's
  output-preserving robustness hardening (graceful per-channel degradation).

## v0.12.4 — 2026-06-07  *(PDF epoch-example efficiency — inert in current reports)*

Code efficiency only — no behaviour or output change.

### Changed
- `generate_pdf_report.py` — `_build_epoch_examples` / `_plot_epoch_example` now read +
  load the EDF **once** (only the needed channels) instead of once per example event
  (~2.4× faster for that routine in isolation: 27.9 s → 11.6 s on a full-night MESA
  recording; byte-identical — same channels / sfreq / full `load_data`). A
  partial/cropped read was rejected because it changes the mixed-sample-rate
  upsampled-channel values.

  **Note:** the epoch-example panels are currently **disabled** at the call site
  (commented out since v0.8.22), so `_build_epoch_examples` is not invoked during
  report generation. This change therefore does **not** reduce actual
  report-generation time — it only takes effect if the panels are re-enabled.
  (The real per-recording speed-up in this version range is the scoring engine:
  psgscoring 0.7.2, bumped in v0.12.3.)

## v0.12.3 — 2026-06-07  *(bump psgscoring to 0.7.2)*

Dependency bump only — no UI, route, or behavior changes in
YASAFlaskified itself.

### Changed
- `requirements.txt` — pin `psgscoring[ml]==0.7.2` (was 0.6.1).
  Brings in: v0.6.2 dual AHI reporting (`ahi_incl_uncertain`, additive),
  v0.7.0 Tier-1 scoring-accuracy fixes (validated byte-identical on the
  clinical AASM-v3 path), v0.7.1 docs, and v0.7.2 a ~1.8–2.0× speed-up of
  the respiratory analysis (shared preprocessing across the 3-profile AHI
  interval — validated byte-identical on the MESA q7 holdout + PSG-IPA).
  Clinical scoring output is unchanged.

## v0.12.2 — 2026-06-03  *(bump psgscoring to 0.6.1)*

Dependency bump only — no UI, route, or behavior changes in
YASAFlaskified itself.

### Changed
- `requirements.txt` — pin `psgscoring[ml]==0.6.1` (was 0.6.0).
  v0.6.1 fixes two POOR-quality scoring crashes that could abort a
  patient's analysis: the Rule 1B `KeyError: 'stage'` (any recording
  with EEG arousal detection, where a stable-breathing-rejected
  hypopnea coincides with an arousal) and the ML `KeyError: 'type'`.
  Clinical AASM profiles are unchanged. See the psgscoring v0.6.1
  changelog for details.
- `myproject/version.py` — `PSGSCORING_VERSION` 0.6.0 → 0.6.1.

## v0.12.1 — 2026-05-28  *(harden bulk maintenance)*

Robustness fixes for the v0.12.0 bulk-maintenance feature. Behavior
only — no new UI, routes, or settings.

### Fixed
- `myproject/app.py` `dashboard()` — the archived-study count behind the
  "Show archived" toggle is now site-filtered. Site-managers no longer
  see other sites' archived studies reflected in the badge. The 300-study
  display cap is now applied *after* the site filter, so a site-manager
  sees up to 300 of their own studies instead of 300 raw files that then
  get filtered down.
- `myproject/app.py` `studies_bulk()` — bulk delete now counts studies
  with leftover file-removal errors as *skipped* rather than reporting
  them as deleted, matching the per-row `delete_study` behavior.
- `myproject/app.py` `studies_bulk()` — bulk archive verifies the study's
  results file exists before writing the `.archived` marker, preventing
  stray marker files for non-existent studies.

### Changed
- `myproject/version.py` — `__version__ = "0.12.1"`.

## v0.12.0 — 2026-05-27  *(dashboard bulk maintenance + archiving)*

Multi-select maintenance on the dashboard so admins and site-managers can
archive or delete several studies at once. Archiving uses a lightweight
marker file (`{job_id}.archived`) — reversible and without moving large
EDF files.

### Added
- `myproject/app.py` — archiving helpers `_archive_marker_path`,
  `_is_archived`, `_can_modify_job`, `_delete_job_files`, and a new
  `POST /studies/bulk` route (`studies_bulk`) gated to admin + site-manager,
  enforcing `_can_modify_job` per study with path-safety filtering.
  Supported actions: `archive`, `unarchive`, `delete`.
- `myproject/templates/dashboard.html` — checkbox column + select-all,
  a floating bulk-action bar, hidden bulk-submit form, per-row
  archive/restore button, and an "Show archived / Back to active" toggle
  with an archived-count badge. Selection logic is filter-aware (ignores
  rows hidden by search/severity/status filters).
- `myproject/i18n.py` — 17 maintenance/archiving keys in NL / FR / EN / DE.

### Changed
- `myproject/app.py` `dashboard()` — splits studies on the archive marker;
  `?archived=1` shows the archived view.
- `myproject/app.py` `results()` — archived studies are hidden from the
  history list.
- `myproject/app.py` `delete_study()` — refactored onto the shared
  `_can_modify_job` + `_delete_job_files` helpers.
- `myproject/version.py` — `__version__ = "0.12.0"`.

## v0.11.7 — 2026-05-23  *(fix header Upload link)*

### Fixed
- `myproject/templates/base.html` — the header "Upload" link sent
  authenticated admin / site-manager users to `/dashboard` (because `/`
  redirects them there) instead of the upload page. It now uses
  `url_for('upload_file')`. The "New analysis" button was already
  correct, so only the header was affected.

## v0.11.6 — 2026-05-14  *(faster EDF viewer start-up)*

### Changed
- `myproject/edf_api.py` — open EDF recordings with `preload=False`
  instead of `preload=True`. The first `/api/edf/<job>/info` call
  previously blocked 20–60 s on long PSGs while 1–2 GB loaded into RAM;
  per-epoch reads now pull only the visible 30 s slice (~1 MB from
  disk), dropping time-to-first-signal from ~30 s to ~1–2 s. The
  per-worker LRU cache still holds the raw object across requests, so
  navigation within a job avoids repeated file opens.

## v0.11.5 — 2026-05-14  *(hotfix — viewer constant clash)*

### Fixed
- `myproject/static/edf_viewer_v12.js` — production had been broken
  since v0.11.3: both `scorer_v12.js` and `edf_viewer_v12.js` declared a
  top-level `const STAGE_COLORS`. Because sibling `<script>` tags share
  one lexical scope, the second declaration threw "Identifier already
  declared" at parse time, so `EdfViewer` was never defined and the
  viewer / event-sidebar never initialised. The viewer copy is renamed
  `EDF_STAGE_COLORS`.

## v0.11.4 — 2026-05-14  *(hypnogram navigation + render perf)*

### Added
- `myproject/static/scorer_v12.js`, `myproject/templates/scorer_v12.html`
  — hypnogram navigation for long recordings: mouse-wheel horizontal
  scroll (Shift = 4×), Shift+←/→ = ±10 epochs (5 min), Ctrl+←/→ = jump
  to previous / next stage transition, Home / End = first / last epoch,
  a jump-to-epoch input (# + Enter), and stage-jump buttons (→ W,
  → N3, → R).

### Changed
- `myproject/static/scorer_v12.js` — `_draw()` throttled via
  `requestAnimationFrame` to coalesce redraws per frame (was laggy
  during key-repeat and drag on long recordings).
- `myproject/i18n.py` — full German entry added (was falling back to
  NL); new keys `kbd_jump10`, `kbd_jump_transition`.

### Fixed
- `myproject/static/scorer_v12.js` — scorer no longer reacts to
  W / 1 / 2 / 3 / R keys while focus is inside an input (added a focus
  guard).

## v0.11.3 — 2026-05-14  *(EDF browser improvements)*

### Added
- `myproject/static/edf_viewer_v12.js`,
  `myproject/templates/scorer_v12.html` — sleep-stage colour strip above
  the signal traces, jump-to-epoch input (# + Enter), N / P hotkeys for
  next / previous event in the active sidebar filter, and event-count
  badges on the sidebar filter buttons (auto-refreshed via a new
  `onEventsChanged` hook).

### Fixed
- `myproject/static/edf_viewer_v12.js` — multi-epoch time-axis tick
  labels now scale with the visible span (were hardcoded 0–30 s
  regardless of 2× / 5× / 10× zoom).

### Changed
- `myproject/i18n.py` — channel-panel strings (previously hardcoded
  Dutch) moved into the language dict; full German entry added; new key
  `kbd_next_prev_event` (NL / FR / EN / DE).

## v0.11.2 — 2026-05-12  *(frontpage content refresh)*

### Changed
- `myproject/templates/frontpage.html` — dropped the hard "AASM"
  claim in the hero (now generic "AASM-compliant scoring"), since the
  PDF generator still cites Berry 2020 / Manual 2.6 while v3.0 is the
  current edition; v3.0 work moved to a new roadmap section. Added a
  "What's new in v0.11" section (6 cards) and an "On the roadmap"
  section (6 cards: AZORG-YASA-2026-001 validation study, paper v36 at
  *Physiological Measurement*, MESA-SHHS external validation, FHIR
  export, AASM Manual v3.0, browser scorer / viewer), a work-in-progress
  chip in the hero, and nav links to both sections.
- `myproject/i18n.py` — +33 keys (1007 → 1040), all four languages.

## v0.11.1 — 2026-05-12  *(login redirect + credits trim)*

### Changed
- `myproject/app.py` — `GET /login` now redirects to `/` (the landing
  page already embeds the login form), so old bookmarks land on the new
  page; `POST /login` is unchanged.
- `myproject/templates/frontpage.html` — removed the "thanks to Raphael
  Vallat" box from the credits section.

## v0.11.0 — 2026-05-12  *(light-themed frontpage with embedded login)*

### Changed
- `myproject/templates/frontpage.html` — replaced the dark `/about`
  marketing page plus separate `/login` screen with a single
  light-themed landing page at `/`: hero with brand / tagline / stats
  beside an inline login card (flash messages render above the form), a
  language picker (NL / FR / EN / DE) in the top nav, 9 feature cards
  reflecting v0.10.x capabilities (per-channel signal quality, staging
  confidence, OAHI 3-point sweep / robustness grade), and tech-stack
  pills (psgscoring v0.6, LightGBM, ReportLab).
- `myproject/app.py` — `/` renders `frontpage.html` for unauthenticated
  visitors instead of redirecting to `/login`.
- `myproject/i18n.py` — +14 keys for the new hero copy and feature cards
  (991 → 1007), all four languages.

## v0.10.5 — 2026-05-12  *(template translation sweep)*

### Changed
- `myproject/i18n.py` plus six templates (`dashboard.html`, `index.html`,
  `report_editor.html`, `results_extended.html`, `scorer_v12.html`,
  `upload.html`) — final sweep of all 24 templates: 21 remaining
  hardcoded Dutch strings replaced with `t()` calls (upload-landing
  feature cards, "Mislukt" status badge, institution-name placeholder,
  partial-save warning, "no events" empty state, upload-flow JS
  messages). `i18n.py` 970 → 991 keys, all four languages. A focused
  Dutch-string detector then reported zero hits across every template.

## v0.10.4 — 2026-05-12  *(translate edit-report page)*

### Changed
- `myproject/templates/report_editor.html`, `myproject/i18n.py` —
  remaining Dutch in the edit-report page routed through `t()`:
  verification card, report-header card, logo upload / remove, diagnosis
  quick-add buttons, and the save-flow JS messages. `i18n.py` 942 → 970
  keys, all four languages.

## v0.10.3 — 2026-05-12  *(translate analysis workflow)*

### Changed
- `myproject/i18n.py` plus templates (`channel_select.html`, `index.html`,
  `job_status.html`, `report_editor.html`, `results_extended.html`,
  `scorer_v12.html`, `upload.html`) — channel-selection labels and
  adjacent screens (leg / position / snore / pulse / ECG channel labels
  and descriptions, upload card, job-status retry / timeout, the 15
  keyboard-shortcut rows, artifact-table headers) now flow through
  `t()`. `i18n.py` 887 → 942 keys, all four languages.

## v0.10.2 — 2026-05-12  *(full 4-language coverage; default English)*

### Changed
- `myproject/i18n.py` — 707 → 887 keys, now complete in NL / FR / EN / DE
  (one DE entry was missing). New keys cover error pages, admin-sites
  columns, dashboard buttons, channel-select ML help, base footer +
  session warning, the full `disclaimer.html` and `frontpage.html`
  marketing copy, and the PDF-report hardcoded NL strings.
- `myproject/app.py` — `DEFAULT_LANG` changed `"nl"` → `"en"` (affects
  new user / site defaults and the `session.get("lang", ...)` fallbacks
  in 50+ flash sites); `STANDARD_CONCLUSIONS` gains German entries;
  flash messages and the 413 "file too large" response routed through
  i18n instead of mixing Dutch fragments.
- `myproject/generate_pdf_report.py`, `myproject/generate_psg_report.py`,
  `myproject/tasks.py`, and templates (`404`, `500`, `admin_sites`,
  `base`, `channel_select`, `dashboard`, `disclaimer`, `frontpage`) —
  hardcoded strings moved into the language dict.

## v0.10.1 — 2026-05-11  *(fix config.json load path)*

### Fixed
- `myproject/app.py` — on a fresh deploy the admin login was always
  `admin/admin` instead of the random password `deploy.sh` prints:
  `deploy.sh` writes the generated SECRET_KEY / ADMIN_PASSWORD to
  `/data/slaapkliniek/instance/config.json`, but `app.py` opened a
  relative `config.json` from the working dir and only saw the baked-in
  template with `VERANDER_DIT_*` placeholders, silently falling through
  to defaults. `config.json` is now resolved in order:
  (1) `/data/slaapkliniek/instance/config.json`,
  (2) `instance/config.json` (local dev),
  (3) the baked-in template — and a template whose `ADMIN_PASSWORD`
  still starts with `VERANDER_DIT_` is discarded in favour of env vars /
  safe defaults. Existing installs keep their current admin password
  (the bcrypt hash in `users.db` is not reset).

## v0.10.0 — 2026-05-10  *(UI overhaul)*

End-to-end visual / interaction refresh aimed at clinical density.
Five interlocking changes; backward-compatible with all v0.9.x routes
and JSON contracts. Backup of pre-v0.10.0 source tree:
`/home/bart/CODE/YASAFlaskified.backup-pre-v010-…`.

### Added
- `myproject/static/styles_v010.css` — typographic + density layer
  loaded on top of Bootstrap 5. Defines:
  * Display font Newsreader (serif), body IBM Plex Sans, mono IBM Plex
    Mono for tabular numerics.
  * `card-quiet` variant: hairline border + 2 px accent rule, no
    shadow, in navy / ochre / claret / teal.
  * `mono-letter` chip used in card headers in place of emoji.
  * `sev-strip` component: 64 px AASM severity strip (Normal / Mild /
    Moderate / Severe) with cut-off ticks at 5 / 15 / 30 /h and a
    triangular marker on the patient value.
  * Auto-detect summary table (channel-select page).
  * Visual focus ring (a11y).
  * `@media print` stylesheet for clinical paper print-out.
  * `.presentation-mode` body class for projected meetings.

### Changed
- `myproject/templates/base.html` — Newsreader / Plex Sans / Plex Mono
  font imports; navbar emoji 🌐 replaced by `bi-globe2`; new
  presentation-toggle button (`bi-display`) + keyboard-help button
  (`bi-question-circle`) in the navbar; global keyboard handler
  (`n`, `g d`, `g h`, `/`, `j` / `k`, `Enter`, `p`, `?`, `Esc`);
  full-screen kbd-help overlay.
- `myproject/templates/dashboard.html` — header gets a monogram
  letter `D`; stat-cards collapsed from 4 to 3 quiet cards with
  monogram letters; AHI / ODI / PLMi pills replaced by `sev_strip`
  macro (severity bar + tabular-numeric value); table tagged
  `kbd-nav-table` for j / k navigation.
- `myproject/templates/channel_select.html` — auto-detected channel
  summary added at the top; existing EEG / EOG / EMG / Extra-EEG /
  Pneumo cards collapsed under a single "Override manually" toggle;
  card-headers use `mono-letter` instead of emoji; `card-quiet`
  variants in navy / ochre / claret / teal; submit button uses
  `bi-play-fill`.
- `myproject/i18n.py` — keys for the keyboard-help overlay
  (NL / FR / EN / DE), the auto-detect summary labels, and the
  dashboard stat-card labels.
- `myproject/version.py` — `__version__ = "0.10.0"`.

### Visual deltas a clinical user notices
1. Numerics in the dashboard table are now monospaced and aligned —
   AHI 8.1 vs 53.98 line up correctly.
2. Each AHI / ODI / PLMi cell is a coloured strip with the value
   marker at the patient's position; severity is visible at-a-glance
   without reading any pill.
3. Channel-select shows one auto-detected summary instead of four
   colourful cards; one click on "Override manually" opens the old
   per-channel layout when needed.
4. `Ctrl/Cmd-P` (browser print) now produces a clinical-dossier
   layout (no nav, A4 margins, B/W badges, severity prefixes).
5. `?` from any list page shows the shortcut help; `j`/`k` navigates
   table rows, `Enter` opens the selected study.

## v0.9.9 — 2026-05-10

UI exposure of the ML arousal re-classifier shipped in v0.9.8.

### Added
- Checkbox "Use ML arousal re-classifier (preview)" on the
  channel-select page (NL/FR/EN/DE), right under the scoring
  profile dropdown. Decoupled from the scoring profile because
  arousal detection is a separate concern from respiratory event
  scoring.

### Changed
- `myproject/templates/channel_select.html` — added the checkbox
  block + i18n hint string.
- `myproject/i18n.py` — `arousal_lgbm_label` and
  `arousal_lgbm_hint` keys (NL/FR/EN/DE).
- `myproject/app.py` — channel-select POST handler stores
  `arousal_lgbm` boolean in the per-job config.
- `myproject/tasks.py` — RQ worker reads `cfg["arousal_lgbm"]`
  and sets the `YASAFLASKIFIED_AROUSAL_LGBM` env var around the
  `run_pneumo_analysis` call (with try/finally restore so the
  flag does not leak across jobs in the same worker process).
- `myproject/version.py` — `__version__ = "0.9.9"`.

## v0.9.8 — 2026-05-10

Optional candidate-level LightGBM EEG-arousal re-classifier shipped
behind the `YASAFLASKIFIED_AROUSAL_LGBM` env-var feature flag. With
the flag unset the detector behaves bit-identically to v0.8.40
rule-based; with the flag set to `1` the candidate stage runs at
permissive thresholds (ratio=1.2, abrupt=1.0) and surviving
candidates are filtered by a LightGBM model trained on MESA
q∈{5,6} (n_subj=653, n_candidates=562k) at probability threshold
`AROUSAL_LGBM_THRESHOLD` (default `0.60`). On the q=7 honest
holdout the hybrid achieves Pearson r 0.66 between automatic and
NSRR-scored arousal-indices (vs 0.08 rule-based) and reduces
|Δn_arousals| from 71 to 45. Cross-cohort validation on PSG-IPA
(no retraining) gives Pearson r 0.84 between algorithmic and
scorer-mean AI across 60 (recording, scorer) cells. See paper v37
§5.5 + Online Supplement §S7.5 for full results.

### Changed
- `myproject/arousal_analysis.py` — added LGBM helper block,
  feature extraction (50 features per candidate), filter wrapper,
  summary recomputation, and dispatch in `detect_arousals`.
  Backward-compat preserved: env var unset = bit-identical to
  v0.8.40 rule-based output.
- `myproject/version.py` — `__version__ = "0.9.8"`.

### Added
- `myproject/data/arousal_classifier_v3.txt` — bundled MESA-trained
  LightGBM model (1.7 MB).

## v0.9.7 — 2026-05-05

i18n strings updated to reflect the v0.6.0 architecture: the
`analysis_description` and `pdf_disc_auto` keys (NL/FR/EN/DE) now
distinguish between YASA AI sleep staging (the historical
"LightGBM, ~85% epoch agreement" credit, attributed to
Vallat \& Walker 2021) and the new v0.6.0 LightGBM
candidate-classifier on `mesa_shhs` (psgscoring v0.6, paper v35).
The fixed `5–10 min` analysis-duration claim was relaxed to
`3–10 min` since the actual time depends on profile choice.
HETZNER_CURRENT_STATE.md cleaned of stale `APP_VERSION=0.8.39`
follow-up (resolved since 2026-05-03 deploys) and updated to
reflect `psgscoring[ml]==0.6.0` pin.

### Changed
- `myproject/i18n.py` — NL/FR/EN/DE for `analysis_description`,
  `analysis_duration`, `pdf_disc_auto`. Header version banner
  updated to v0.9.6 → v0.9.7.
- `HETZNER_CURRENT_STATE.md` — current-state table cleanup,
  stale APP_VERSION follow-up moved to Resolved section,
  example deploy commands updated to v0.9.6+.

## v0.9.6 — 2026-05-05

UI annotation for ML-augmented profiles. The scoring-profile
dropdown on the channel-select page now appends a "🤖 ML" suffix to
profile labels whose `post_processing.ml_classifier_path` is set,
making it visible at a glance which profiles run the
`psgscoring`~v0.6.0 candidate-level LightGBM re-classifier (default
only `mesa_shhs`). A short legend below the dropdown explains the
marker. No changes to scoring behaviour or routine clinical output.

### Changed
- `myproject/app.py` — appends `🤖 ML` to `display_name` for profiles
  with an ML classifier configured.
- `myproject/templates/channel_select.html` — added one-line legend
  beneath the profile select.

## v0.9.5 — 2026-05-05

Bumped `psgscoring` pin from 0.5.1 to **0.6.0** with the new `[ml]`
extra (installs `lightgbm>=3.0`). The 0.6.0 release adds an optional
LightGBM candidate-level re-classifier that ships in the package and
is consumed by the `mesa_shhs` profile by default; clinical profiles
(used by every routine YASAFlaskified analysis) leave the
classifier disabled and remain bit-identical to v0.5.x output.

### Changed
- `requirements.txt` — `psgscoring==0.5.1` → `psgscoring[ml]==0.6.0`
- `myproject/version.py` — `__version__` 0.9.4 → 0.9.5;
  `PSGSCORING_VERSION` 0.5.1 → 0.6.0
- `INSTALL.md`, `HETZNER_CURRENT_STATE.md` — version references updated

## v0.9.4 — 2026-05-03

Bumped `psgscoring` pin from 0.4.3 to **0.5.1**. The 0.5.x series adds
profile-tunable thresholds and metadata corrections to the `mesa_shhs`
profile (paper v34 §S5.6 + research-driven additions); see the
`psgscoring` CHANGELOG for details. PSG-IPA reproducibility 10/10 pass
on both versions; clinical AHI for routine recordings is unchanged
because clinical profiles (`aasm_v3_*`, `aasm_v2_rec`, `aasm_v1_rec`,
`cms_medicare`, `chicago_1999`) keep their released defaults.

### Changed
- `requirements.txt` — `psgscoring==0.4.3` → `psgscoring==0.5.1`
- `myproject/version.py` — `__version__` 0.9.3 → 0.9.4;
  `PSGSCORING_VERSION` 0.4.3 → 0.5.1
- `INSTALL.md`, `HETZNER_CURRENT_STATE.md` — version references updated

## v0.9.3 — 2026-05-01

### Changed
- Bumped `psgscoring` pin from `0.4.2` (bundled patch) to `0.4.3` from PyPI.
  No public-API changes; psgscoring v0.4.3 ships the paper-faithful
  `validate_psgipa.py` rewrite and a reproducibility regression test.
- `version.py` updated to `0.9.3` and `PSGSCORING_VERSION = "0.4.3"`
  (was missed in the v0.9.2 and earlier v0.9.3 git tags; v0.9.3 tag
  re-pointed at this commit).

### Notes
- INSTALL.md: 4 references to `psgscoring 0.4.2` updated to `0.4.3`.
- Production deployed to Hetzner on 2026-05-01.

---

## v0.9.2 — 2026-05-01

### Removed
- **Bundled `myproject/psgscoring/`** (8.1k LOC, 20 files). psgscoring
  is now installed from PyPI via `requirements.txt`. Bumps to newer
  psgscoring releases are now a one-line change.

### Fixed
- **CI on `main` was red since 2026-04-12** because ruff flagged 429
  issues in `myproject/`. Three were real bugs:
  - `generate_psg_report.py:985,1001` — undefined `site` and `pneumo`
    should be `institution` and `pneumo_results`; would crash code
    paths that hit them
  - `generate_pdf_report.py:116,123` — loop variable `t` shadowed the
    imported translation function `t` in `_sev` and `_sev_clr`,
    silently breaking translations in those branches
- The remaining 426 issues were stylistic / import-sort / whitespace;
  ruff `--fix` handled 90, the rest are now suppressed by a pragmatic
  ruff config (`select = ["F", "W", "I"]`, ignoring opinionated
  pycodestyle / bugbear / pyupgrade rules on this established
  scientific-Flask codebase).

### Added
- New smoke test `myproject/tests/test_psgscoring_from_pypi.py` that
  asserts `import psgscoring` does not resolve under `myproject/psgscoring/`
  and that the loaded version meets the requirements.txt minimum.
- CI workflow (`.github/workflows/ci.yml`): ruff lint + pytest +
  Docker build smoke.
- Repo hygiene: `.env.example`, `Makefile`, `pyproject.toml` with
  ruff/pytest config.
- `pythonpath = ["myproject"]` in pytest config so top-level imports
  resolve when pytest runs from the repo root.

### Deferred
- 27 duplicate translation keys (F601) in `myproject/i18n.py` silently
  shadow earlier values; deferred with per-file ignore + TODO comment.
  Deduplication needs care to preserve the right variant.

---

## v0.9.1 — 2026-04-29

### Fixed
- **Blank page in PDF** between "Visueel overzicht" and "1. Slaaparchitectuur"
  caused by an explicit `PageBreak()` after the position legend. With short
  recordings (e.g., PSG-IPA SN3 ~6h) section 1 fits on the visual overview
  page, and the explicit page break forced an empty intermediate page.
  Replaced with `sp(0.3)` to let ReportLab handle pagination naturally.

### Changed
- Bundled psgscoring 0.3.1 → 0.4.2 (profile-aware local baseline validation)
- Removed confidence-sweep card from results page (clinically misleading)
- Removed confidence-sweep table from PDF report

### Notes
- AHI Interval banner on page 1 retained (profile-comparison sweep)
- PSG-IPA aggregate validation: r=0.994, κ=0.800, F1 SN3=0.860

## v0.9.0 — April 2026 (transitional)

### Added
- **3-point confidence-sweep card** on results page (DEPRECATED in v0.9.1):
  showed clinically misleading discrete values for borderline patients.
- Bundled psgscoring 0.3.1 → 0.4.1 (parameter integration fix)

# Changelog — YASAFlaskified

## v0.19.0 — 2026-08-05  *(scoringsprofiel per gebruiker)*

Geen psgscoring-wijziging (blijft 0.14.4).

De slaaptechnici gaan profielen naast elkaar testen. Zonder dit moet ieder van
hen bij élke opname dezelfde dropdown opnieuw goed zetten, en één vergeten klik
maakt een vergelijking stil ongeldig — precies het soort fout dat je pas ziet
als je twee rapporten naast elkaar legt.

**Nieuw:** `User.default_profile`. Een admin of site-manager zet per gebruiker
welk profiel voorgeselecteerd staat; in de gebruikersbeheerpagina staat er een
kolom bij en een eigen formulier per rij.

**De keuze blijft een keuze.** Er verschuift alleen het `selected`-attribuut;
de dropdown op de kanaalkeuzepagina bevat onverkort alle profielen en de
technicus kan per opname iets anders kiezen. Vier tests dwingen dat af,
waaronder één die controleert dat er precies één optie voorgeselecteerd staat —
meerdere `selected` in één `<select>` is stil gedrag waarbij de browser de
laatste houdt, en dat was de radiogroep-bug van 4 augustus.

**Terugvallen doet het naar de applicatiestandaard**, niet naar niets: leeg
gelaten of een profiel dat niet meer in de psgscoring-registry zit geeft
`aasm_v3_rec`. De keuzelijst komt uit die registry, dus een nieuw profiel
verschijnt vanzelf en een verdwenen profiel valt vanzelf weg.
`mesa_shhs` en `chicago_1999` staan er niet in — die bestaan om gepubliceerde
cijfers te reproduceren, niet om patiënten mee te scoren.

**Toegang** volgt de bestaande regel: een site-manager mag alleen zijn eigen
site-gebruikers aanpassen, net als bij wachtwoord resetten en verwijderen.

**Migratie.** De kolom komt er via het bestaande lichte SQLite-migratiepad bij
het opstarten, zonder default — NULL betekent applicatiestandaard, en dat is
exact het gedrag van vóór deze versie. Vooraf drooggedraaid op een kopie van de
productiedatabase: 6 gebruikers, 3 sites en 15 jobs behouden, alle bestaande
gebruikers op NULL, wachtwoordhashes ongemoeid.

15 nieuwe tests, 209 groen.

## v0.18.5 — 2026-08-05  *(het herkomstblok sprak zichzelf tegen)*

Geen psgscoring-wijziging (blijft 0.14.4).

Het herkomstblok kende drie thermistor-gevallen — afwezig, afgekeurd, bruikbaar
— en er zijn er vier. Bij een **additief** profiel (`aasm_v3_dual`,
`aasm_v3_fusion`) wordt een thermistor die de kwaliteitstoets níet haalt tóch
behouden, omdat de tweede detectiepas hem onschadelijk maakt vóór de
apneutelling. Het blok noemde hem dan "bruikbaar".

Gevonden door twee rapporten van één opname naast elkaar te leggen. Het blok
meldde *"Flow Th. — bruikbaar (0.23)"* terwijl de drempel op 0,40 ligt en de
corroboratiekolom twee bladzijden verderop toonde dat diezelfde sensor **0 van
de 95 apneus** had bijgedragen. Het rapport sprak zichzelf tegen — precies het
soort tegenspraak dat dit blok moest wegnemen.

Nu vier gevallen, met het getal erbij zodat de lezer ziet hoe zwak de steun is:

| situatie | tekst |
|---|---|
| geen thermistor | *niet in montage* |
| afgekeurd, vervangen door de neusdruk | *afgekeurd door kwaliteitscontrole (0.32)* |
| onder de drempel, additief behouden | *onder de kwaliteitsdrempel, additief gebruikt — mag events toevoegen, niet afwijzen (0.23)* |
| boven de drempel | *bruikbaar (0.71)* |

Drie nieuwe tests, waaronder één die afdwingt dat de vier gevallen verschillende
tekst opleveren. 194 tests groen.

## v0.18.4 — 2026-08-05  *(twee experimentele profielen erbij)*

`psgscoring[ml]` 0.14.3 → **0.14.4**. Geen YF-codewijziging.

Twee nieuwe profielen verschijnen in de v3-groep van de dropdown, allebei met
**(experimental)** in hun naam omdat ze dat zijn:

- **`aasm_v3_prob`** — de arousal-as van de ademteug-detector was als enige nog
  een drempel: `p_arousal` sprong naar 0,90 zodra er een arousal in het venster
  lag, waardoor de bevestiging nooit onder 0,90 kwam hoe klein de desaturatie
  ook was. Nu gewogen (0,70) en gegradeerd op koppelingslatentie. Op PSG-IPA
  (n = 5): F1 0,453 tegen 0,434, precisie 0,72 → 0,79, en het aantal events dat
  géén van de twaalf scoorders markeerde daalt van 69 naar 47.
- **`aasm_v3_fusion`** — de sensorovereenstemming tussen thermistor en neusdruk
  telt als gewicht in plaats van als poort. Elke apneu draagt
  `sensor_agreement`, en een apneu waarvan de thermistor de enige steun is
  krijgt zijn confidence daarmee geschaald. **Niet gevalideerd**: die as is op
  PSG-IPA principieel niet te meten, want die montage heeft één flowkanaal.

Beide staan in de familie `exploratory` en veranderen niets tenzij iemand ze
kiest. Elk bestaand profiel is byte-identiek.

## v0.8.39 (2026-04-19)

### Dashboard
- Added 3 new columns after AHI in Patiëntenoverzicht:
  - **Grade** (A/B/C): AHI robustness from confidence interval
  - **ODI₃**: Oxygen Desaturation Index 3%
  - **PLMi**: Periodic Limb Movement Index
- FHD-compatible 12-column layout with compact padding
- Backward compatible: shows "—" if backend data unavailable
- Backend wiring for s.grade/s.odi/s.plmi: TBD separate commit

### i18n
- Added 4 new keys × 4 languages (NL/FR/EN/DE):
  - grade, grade_tooltip, odi_tooltip, plmi_tooltip
- Uses _DASHBOARD_V0839 sub-dict pattern consistent with _PDF_KEYS

All notable changes documented per [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.8.37] — April 2026

### Added — Page 1 robustness + OSAS score fix
- **AHI Robustness grade on page 1**: compact coloured banner showing `AHI Interval: [strict – standard – sensitive] /u · Robustness: A/B/C` directly below the confidence warning. Green (A), amber (B), red (C). Clinician sees at a glance whether diagnosis is robust.
- **OSAS code without ESS**: when ESS is not provided, the OSAS code now shows `O0S2A0S— (subtotaal: 2/9, ESS niet ingevuld)` instead of the misleading `(totaal: 2/12)`. New i18n key `ESS not provided` in NL/FR/EN/DE.
- Epoch signal examples (section 8e) remain disabled pending alignment fix.

### Changed
- psgscoring bumped to v0.2.951
- All version strings updated to v0.8.37

## [0.8.36] — April 2026

### Added — PDF report Medatec parity + OSAS severity score
- **Position × stage cross-table**: respiratory events by NREM/REM × supine/non-supine with sleep time, event count, mean duration, and AHI per cell; auto-detects supine-dominant and REM-dominant OSA
- **Snoring cross-table**: snoring percentage by position × stage (NREM-rug, NREM-zij, REM-rug, REM-zij)
- **Stage-specific sleep latencies**: N1, N2, N3, REM latency table in sleep architecture section
- **SpO₂ saturation bands**: time in 95–100%, 90–95%, 80–90%, 70–80%, <70% ranges
- **OSAS severity profile**: multi-dimensional O-S-A-S score (Oxygen deficit / Sleep disruption / Apnea frequency / Symptoms) with modifiers (p=positional, r=REM-dominant, c=central component). ESS input for symptom dimension.
- **`pdf_report_additions.py`** (748 lines, 14 functions): standalone module, also usable outside PDF (`compute_osas_score()`, `compute_position_stage_crosstab()`, `compute_stage_latencies()`)
- ~37 new i18n keys (NL/FR/EN/DE)

### Changed
- psgscoring bumped to v0.2.93
- All version strings updated to v0.8.36

## [0.8.35] — April 2026

### Added — Hypoxic burden + post-processing
- **Hypoxic burden** (Azarbarzin et al., AJRCCM 2019): per-event SpO₂ desaturation area, normalised %·min/h — displayed in PDF SpO₂ section
- **CSR-aware central reclassification**: CSR-flagged obstructive/mixed events → reclassified as central (addresses cardiac pulsation artifact in heart failure)
- **Mixed apnea decomposition**: central portion ≥10 s → reclassified as central; reports `cai_decomposed`
- **Central instability index**: quantifies profile-dependent O/C uncertainty (0–1 scale)
- **Bundled psgscoring v0.2.92** with 42 public exports (was 38)
- **New postprocess.py module** in psgscoring (CSR reclassification + mixed decomposition + CII)

### Changed
- Pipeline: 11 steps (was 9) — added step 10 (hypoxic burden) and step 11 (post-processing)
- PDF report: SpO₂ table now includes hypoxic burden row with clinical reference (<20 %·min/h)
- PDF report: corrections table shows CSR reclassification and mixed decomposition counts
- All version strings updated to v0.8.35 across all files

## [0.8.34] — April 2026

### Added — External validation + AHI confidence interval
- **PSG-IPA validation**: bias +1.6/h, r=0.990, 60 scorer sessions
- **iSLEEPS validation**: n=39 stroke patients, MAE 3.3/h normal/mild
- **ECG-derived effort**: TECG method (Berry 2019) + spectral classifier
- **Calibration module**: scorer-adaptive parameter optimisation (experimental)
- Bundled psgscoring v0.2.91

## [0.8.33] — April 2026

### Fixed — FHIR export + PDF event plots
- **FHIR: sleep stage values were minutes, not percentages** — N1/N2/N3/REM observations now correctly exported as % of TST (e.g., REM=140.5 min → 39.9%)
- **PDF event plots: SpO2 label** — was literal HTML `SpO<sub>2</sub>` in matplotlib; now uses LaTeX `$SpO_2$`
- **PDF event plots: artefact-resistant scaling** — replaced P1/P99 with median ± 4×MAD; prevents artefact spikes from hiding flow reductions
- **PDF event plots: detection channel highlighted** — thicker line + ◀ marker on the channel where the event was actually detected (thermistor for apnea, nasal pressure for hypopnea); detection channel name shown in title
- 47 tests passing, 619 i18n keys

## [0.8.31] — April 2026

### Fixed — PDF report bugs
- **Removed duplicate executive summary** that overlapped with existing KPI boxes on page 1
- **Fixed SpO2 subscript rendering**: Unicode ₂ → ReportLab `<sub>2</sub>` (was rendering as black boxes ■)
- **Fixed stage transition matrix**: was showing all dots — now correctly reads `timeline[i]["stage"]` instead of the raw dict
- **Fixed signal quality table**: field name mismatch (`quality_grade` vs `quality`, `flat_pct` vs `flatline_pct`) — was showing "?" for all channels
- 619 i18n keys, 47 tests passing

## [0.8.30] — April 2026

### Improved — Clinical PDF report layout (AASM-compliant)
- **Executive Summary box** on page 1: AHI (large font, severity-colored), OAHI, CAI, SpO₂ baseline/nadir, arousal index, PLMI — all critical numbers visible at a glance
- **Sleep stage transition matrix**: compact 5×5 table (W/N1/N2/N3/R) with transition counts after sleep architecture
- **HR/ECG summary section** (§10c): mean/min/max HR, bradycardia/tachycardia episodes
- **Spacing reduction**: 40–60% less whitespace for denser clinician-friendly layout

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.28] — April 2026

### Fixed — Central and mixed apnea under-classification
- **Rule 5 (central) thresholds relaxed**: `raw_var_ratio` 0.15→0.25, `quarters_absent` 3→2, `phase_angle` 20°→30°, `paradox_corr` 0.0→−0.10 — accounts for cardiac pulsation artefact on RIP bands that inflates effort metrics without true respiratory effort
- **New Rule 5a (probable central)**: catches events with effort_ratio 0.20–0.40 (gray zone between absent and present) when no paradoxical breathing or phase signal is detected — previously these all defaulted to obstructive via Rule 6
- **Rule 5b (ECG reclassification) relaxed**: effort threshold from 1.5× to 2× EFFORT_PRESENT_RATIO, allowing reclassification of more borderline events
- **Rule 3 (mixed) relaxed**: first-half effort threshold 0.20→0.35 to detect mixed apneas with gradual (not binary) effort onset
- **Rule 6 (borderline default) split**: events with low effort + no obstructive evidence now classified as central (not obstructive); obstructive default only when effort is ambiguous or movement is present

## [0.8.27] — April 2026

### Fixed — PDF multilingual + breath snap fix + OAHI per profile
- **f-string syntax error fixed**: nested double quotes `f"{t("key")}"` → `f"{t('key')}"` (6 occurrences causing worker crash on v0.8.26)
- **Breath boundary snapping OFF by default**: `USE_BREATH_SNAP` added to scoring profiles — `False` for strict/standard, `True` for sensitive only. Fixes unintended OAHI drop (~4.5/h) caused by snapped boundaries shifting SpO₂ coupling and local baseline validation windows.
- **OAHI per profile in PDF table**: scoring profile comparison table now shows OAHI column — active profile marked with ▶, other profiles shown if comparison data available
- **36+ new i18n keys** for PDF: fix table (Fix 1–6 + ECG), apnea types, severity grades, signal quality, profile headers, RERA, disclaimers, spindle/slow wave counts
- **All hardcoded Dutch removed** from `generate_pdf_report.py` — all user-facing strings via `t()` calls
- **606 total i18n keys**, 100% NL/FR/EN/DE coverage

## [0.8.26] — April 2026

### Fixed — Multilingual & clinical display
- **German (DE) as language choice**: added to `SUPPORTED_LANGS`, `LANG_NAMES`, `LANG_FLAGS`, and all HTML dropdown selectors (`base.html`, `admin_sites.html`, `admin_users.html`)
- **Scoring profile in AHI classification bar**: PDF now shows `Profile: Standard (AASM)` alongside AHI/OAHI values
- **Severity labels multilingual**: `Normaal/Mild/Matig/Ernstig` → language-dependent via `_SEV_LABELS` dict (NL/FR/EN/DE)
- **Hardcoded Dutch in PDF report**: `Niet beschikbaar`, `Overschatting-correctie` replaced with `t()` i18n calls
- **5 new i18n keys**: `pdf_not_available`, `pdf_overcounting_corrections`, `pdf_correction`, `pdf_impact`, `pdf_explanation` (all 4 languages)
- **568 total i18n keys**, 100% coverage NL/FR/EN/DE

## [0.8.25] — April 2026

### Added — Platform improvements (items 9–18)

**Clinical workflow:**
- **Batch analysis CLI** (`batch_analyse.py`): process entire directories of EDFs with parallel workers, outputs summary CSV with AHI, fix counters, staging stats per study. Supports multiple scoring profiles in one run.
- **Event-level comparison tool** (`validation_metrics.py`): `compare_respiratory_events()` performs temporal matching (±5s tolerance) between manual and automated events, reports TP/FP/FN, per-type confusion matrix, sensitivity, PPV, F1. `compute_event_type_confusion()` adds obstructive/central/mixed breakdown.
- **Scoring profile comparison** (`tasks.py`): `run_profile_comparison()` runs strict/standard/sensitive on the same EDF and outputs a comparison table with AHI, OAHI, severity per profile.
- **ECG reclassification in PDF fix table** (`generate_pdf_report.py`): `n_ecg_reclassified_central` now shown in the over-counting correction summary.
- **U-Sleep integration stub** (`yasa_analysis.py`): `run_sleep_staging(backend="usleep"|"both")` provides a clean integration point for U-Sleep. `backend="both"` runs YASA+U-Sleep and adds epoch-level agreement to the result dict.
- **Demo EDF generator** (`generate_demo_edf.py`): creates a synthetic 30-min PSG with visible OA/CA/hypopneas, desaturations, position changes, and stage-appropriate EEG — no patient data, GDPR-safe.

**Technical/infrastructure:**
- **VERSION constant** (`version.py`): single source of truth for version strings, imported by `app.py`.
- **German (DE) translations**: 563/563 i18n keys now have DE translations (auto-generated from EN with medical term mapping). Full NL/FR/EN/DE coverage.
- **LRU cache** (`edf_api.py`): already implemented as `_LRUCache` (max 3 EDF files per worker) — verified present.
- **ProxyFix** (`app.py`): already implemented at startup — verified present.

### Changed
- `README.md`: version badge, citation, deploy instructions updated to 0.8.25
- `CHANGES.md`: full changelog for v0.8.24 and v0.8.25
- `i18n.py`: 563 DE translation keys added via post-init `_DE_PATCH` block

## [0.8.24] — psgscoring v0.2.5

### Added — Scoring improvements (items 4–8)
- **Adaptive cardiac frequency band** (ecg_effort.py): `compute_adaptive_cardiac_band()` derives the patient's actual heart rate from R-R intervals and adjusts the spectral classifier's cardiac band accordingly. Prevents misclassification in bradycardic patients (athletes, beta-blocker users) where the cardiac fundamental overlaps the respiratory band.
- **Flattening index in apnea type classification** (classify.py): `classify_apnea_type()` now accepts an optional `flattening_index` parameter. High flattening (>0.30) boosts obstructive confidence; low flattening (<0.10) with absent effort supports central classification.
- **SpO₂ low baseline warning** (spo2.py): flags studies with baseline SpO₂ < 88% (`low_baseline_warning`, `low_baseline_note`), alerting to possible COPD/OHS overlap where the 3% desaturation criterion is less meaningful.
- **Breath boundary snapping** (respiratory.py): `_snap_to_breath_boundaries()` adjusts algorithmically detected event onset/end to the nearest zero-crossing of the bandpass-filtered flow signal, improving per-event concordance with manual scorers.
- **ECG effort test suite**: 13 new tests covering R-peak detection, TECG computation, adaptive cardiac band, spectral classifier, and combined assessment. Total test count: 37.

### Changed
- `spectral_effort_classifier()` now accepts optional `cardiac_band_hz` parameter
- `ecg_effort_assessment()` uses adaptive cardiac band by default
- `_detect_apneas()` and `_detect_hypopneas()` accept `flow_filt` for boundary snapping

### Verified — Items 1–3 already present
- Standalone psgscoring is byte-identical to embedded version (no divergence)
- Position-change baseline reset: `detect_position_changes()` + `reset_baseline_at_position_changes()` fully wired in respiratory.py
- Stage-specific baseline blending: `compute_stage_baseline()` with NREM/REM separation and 5s cosine-ramp smoothing fully operational

## [0.8.23]

### Added
- **ECG-derived effort classification (TECG)**: Transformed ECG method (Berry et al., JCSM 2019) for improved central vs. obstructive apnea differentiation
- **Spectral effort classifier**: cardiac (0.8–2.5 Hz) vs. respiratory (0.1–0.5 Hz) power analysis on RIP bands during apnea events
- **Combined reclassification logic**: events reclassified as central when both TECG (no inspiratory bursts) and spectral analysis (cardiac dominance) agree
- New output field `n_ecg_reclassified_central` in respiratory results
- New module `psgscoring/ecg_effort.py` with `compute_tecg()`, `detect_r_peaks()`, `qrs_blanking()`, `detect_inspiratory_bursts()`, `spectral_effort_classifier()`, `ecg_effort_assessment()`

### Changed
- `pipeline.py`: ECG channel now extracted and passed to respiratory scoring
- `respiratory.py`: TECG computed once per recording; ECG assessment passed to both apnea and hypopnea `classify_apnea_type()` calls
- `classify.py`: ECG-based reclassification integrated into 7-rule classification (Rule 5b)

## [0.8.22]

### Fixed — PDF rapport inconsistenties & klinische correctheid

**Lokale basislijn-validatie (klinisch kritiek — v0.8.22):**
- FIX: False-positive hypopneeën door opgeblazen rollende basislijn (post-apnea recovery hyperpnea)
- NIEUW: `_validate_local_reduction()` — vergelijkt event-amplitude met de directe pre-event ademhaling (30s venster), exact zoals een menselijke scorer doet
- Events met <20% lokale reductie worden afgewezen met reden `local_reduction_Xpct<20pct`
- Voorkomt 60–80+ seconden "hypopneeën" waar visueel geen flow-reductie zichtbaar is
- PDF: "Fix 6 — Lokale basislijn" in overschatting-correctie tabel toont aantal afgewezen events

**Hypopnea/Apnea max-duur splitting (klinisch kritiek):**
- FIX: Hypopneeën van 60–80+ seconden werden als één event gescoord — klinisch onrealistisch
- NIEUW: `HYPOPNEA_MAX_DUR_S = 60s`, `APNEA_MAX_DUR_S = 90s` (configureerbaar per scoring profiel)
- NIEUW: `_split_long_region()` splitst te lange events op het punt van maximale flow-recovery (partiële herstel-ademhaling)
- Recursief: sub-regio's die nog te lang zijn worden opnieuw gesplitst
- Elk sub-event krijgt eigen desaturatie-berekening, classificatie en confidence
- Profiel-afhankelijk: strict=60/90s, standard=60/90s, sensitive=90/120s

**SpO2 sectie (kritiek):**
- FIX: `mean_spo2` key mismatch — PDF gebruikte `mean_spo2` maar SpO2 module retourneerde `avg_spo2` → Gemiddelde SpO2 toonde altijd "—"
- FIX: ODI 3% en ODI 4% werden nooit berekend — PDF verwees naar `odi_3pct`/`odi_4pct` maar `analyze_spo2()` berekende deze niet → altijd "—"
- NIEUW: ODI 3% en ODI 4% worden nu correct berekend via `detect_desaturations()` met respectievelijk `drop_pct=3.0` en `drop_pct=4.0`
- NIEUW: Baseline SpO2 (P90) nu ook zichtbaar in SpO2-tabel
- NIEUW: `mean_spo2` alias toegevoegd voor backward-compatibiliteit
- NIEUW: `n_desat_3pct` en `n_desat_4pct` tellingen in summary dict

**Slaapcycli (klinisch misleidend):**
- FIX: Cycle-detectie herschreven — oude algoritme maakte nieuwe cyclus bij elke REM→NREM transitie, zonder minimale duur. Produceerde 33 micro-cycli (0.5–3.0 min) i.p.v. verwachte 4–6 cycli
- NIEUW: Feinberg & Floyd criteria: minimaal 15 min NREM (30 epochs) vereist voor geldige cyclus
- NIEUW: REM-consolidatie: korte N1/W onderbrekingen (≤2 min) breken REM-periode niet

**REM-detectie (klinisch misleidend):**
- FIX: REM-perioden werden gefragmenteerd geteld — elke R→non-R transitie was een "periode"
- NIEUW: Geconsolideerde REM-perioden met gap-tolerantie (≤4 epochs N1/W)
- Realistische n_rem_periods, mean_rem_period_min, longest_rem_period_min

**Spindle & Slow Wave tabellen:**
- FIX: "Stadium" kolom toonde altijd "—" — YASA summary met `grp_chan=True, grp_stage=False` heeft `Channel` key, niet `Stage`
- FIX: Kolomheader veranderd van "Stadium" naar "Kanaal" (i18n: NL/FR/EN)
- FIX: Row lookup zoekt nu Channel→channel→Stage→stage fallback chain

**Signaal kwaliteit & confidence waarschuwing:**
- NIEUW: Rode banner bovenaan rapport wanneer signaalkwaliteit "poor" is met onbruikbare kanalen
- NIEUW: Rode banner wanneer ≥20% epochs AI-confidence <70% — "Manuele verificatie aanbevolen"
- Waarschuwingen verschijnen direct na de KPI-balk, vóór de slaaparchitectuur

**Signaalvoorbeelden in PDF (sectie 8e):**
- NIEUW: Tot 3 representatieve respiratoire events als gestapelde signaalplots
- Selectie: hoogste confidence, langste event, grootste desaturatie (gededupliceerd)
- Per event: 15s pre + event + 30s post, alle beschikbare pneumokanalen (Flow, Nasal P., Thorax, Abdomen, SpO₂, Snore)
- Rode band markeert event-duur, titel toont type/duur/desaturatie/confidence/slaapstadium
- i18n: sectieheader en intro-tekst in NL/FR/EN
- `edf_path` en `pneumo_channels` worden nu meegegeven via combined dict (tasks.py)

### Changed
- Versienummer: 0.8.19 → 0.8.22 in alle bestanden (app.py, i18n.py, generate_pdf_report.py, signal_quality.py, README.md, DISCLAIMER.md)

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.19]

### Added — Study types, position legend, titration support

**Study type support (v0.8.19):**
- UI dropdown: Diagnostic PSG / Titration PSG CPAP / Titration PG CPAP / Titration PG MRA
- Study type flows through config → results → PDF
- PDF title: "Slaaprapport" vs "Titratierapport — CPAP" vs "Titratierapport — MRA"
- Titration: "Residueel AHI" / "Residueel OAHI" labels + therapy note
- Polygraphy: "REI" instead of "AHI", sections 2-7 + 8b arousals skipped
- Polygraphy: "Geen slaapstaging" notice in section 1
- 13 new i18n keys NL/FR/EN

**Position legend in visual overview (v0.8.19):**
- POS legend line added under EVENT/SpO2/PHONO legends

### Fixed

**EDF → header auto-fill (v0.8.18→0.8.19):**
- Eigen EDF parser bij kanaalkeuz (MNE subject_info onbetrouwbaar)
- EDF patient fields auto-populate PDF header + formulier
- Numerieke naam (patiëntcode) wordt vervangen door EDF-naam
- Duplicate "Patiëntgegevens (uit EDF)" tabel verwijderd
- Heranalyse: slimme merge detecteert code vs naam

---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.17]

### Added — Signal quality, flattening RERA, montage checks

**Signal quality assessment (v0.8.19):**
- New module `psgscoring/signal_quality.py`
- Per-channel: flat-line %, clipping %, line-noise %, disconnect count
- Channel grade: good / acceptable / poor; overall recording grade
- PDF Section 7b: table per channel with quality metrics

**Montage plausibility checks (v0.8.19):**
- Cross-correlation EEG↔EOG (r>0.95 = shared reference warning)
- Cross-correlation thorax↔abdomen (r>0.98 = duplication warning)
- Cross-correlation flow↔effort (r>0.95 = duplication warning)
- Warnings displayed prominently in PDF report

**Flattening-based RERA detection (v0.8.19):**
- Dual-source RERA: FRI-RERA (amplitude) + Flattening-RERA (shape)
- Hosselet et al. (AJRCCM 1998) flattening index >0.30 = flow limitation
- ≥3 consecutive flat breaths, ≥10s, + arousal = flattening-RERA
- RDI = AHI + (FRI-RERA + Flattening-RERA) / TST
- PDF shows both RERA sources separately

### Changed
- Pipeline: 11 steps (added 1b: signal quality)
- RERA table in PDF: two rows (FRI vs flattening source)

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.16]

### Added — RERA/RDI, REM/NREM AHI, clinical indices

**RERA index and RDI (v0.8.16):**
- RERA = flow-reduction events (≥30%, ≥10s) + arousal, without ≥3% desaturation
- Computed from remaining FRI events after Rule 1B reinstatement
- RDI = AHI + RERA index — clinically relevant for UARS diagnosis
- Displayed in PDF respiratory section with interpretation note

**REM vs NREM AHI (v0.8.16):**
- Stage-specific AHI (REM-AHI, NREM-AHI) in respiratory summary and PDF
- Clinically relevant for REM-dominant OSAS phenotype

**Positional AHI in PDF (v0.8.16):**
- AHI per body position (Supine, Left, Right, Prone, Upright) displayed
  in PDF alongside REM/NREM AHI
- Already computed in ancillary.py, now visible in report

**SpO2 samplerate check (v0.8.16):**
- Warning when SpO2 channel samplerate < 0.33 Hz (>3s averaging)
- AASM requires maximum 3-second signal averaging for pulse oximetry
- Flag `spo2_low_samplerate` stored in output; PDF shows warning banner

**Hypopnea subtype counts (v0.8.16):**
- `n_hypopnea_obstr`, `n_hypopnea_central`, `n_hypopnea_mixed` in summary
- Most commercial software does not differentiate hypopnea subtypes

**Cosmetisch (v0.8.16):**
- Logo: Concept C (EEG-trace + "YASAFlaskified" + slaapkliniek.be)
- Dubbele "Download PSG" knop verwijderd (was redirect naar PDF)
- Footer: referenties YASA, psgscoring, AASM
- EDF patient info (naam, geslacht, geboortedatum) in PDF

### Changed
- Pipeline step numbering: 9 → 10 steps (added Step 8b: RERA/RDI)

---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.15]

### Added — Configurable scoring profiles

**Scoring profile system (strict / standard / sensitive):**
- Three predefined profiles controlling hypopnea threshold, SpO2 nadir
  window, flow smoothing, cross-contamination window, and peak detection
- `strict`: AASM exact (0.70 threshold, 30s window, no smoothing, envelope only)
- `standard`: recommended (0.70, 45s, 3s smoothing, peak+envelope) — default
- `sensitive`: RPSGT-like (0.75/25% reduction, 45s, 5s smoothing, no cross-contam)
- UI dropdown on channel-select page (NL/FR/EN translations)
- Profile label shown in PDF report subtitle
- Profile thresholds logged and stored in `result["scoring_thresholds"]`
- Pipeline parameter: `run_pneumo_analysis(..., scoring_profile="standard")`

### Changed
- `get_desaturation()` accepts `post_win_s` parameter (was hardcoded)
- `_detect_hypopneas()` accepts `desat_pct`, `contam_win_s`, `post_event_win_s`
- `constants.py`: `SCORING_PROFILES` dict, `POST_EVENT_WINDOW_S`, `CROSS_CONTAM_WINDOW_S`
- Version number updated to 0.8.15

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.14]

### Added — AASM-conforme peak-based hypopnea detection

**Peak signal excursion detection (AASM conformiteit):**
- AASM definieert hypopnea als "peak signal excursions drop by ≥30%"
  — dit verwijst naar **piek-amplitude per ademhaling**, niet naar de
  continue Hilbert-envelope
- Nieuwe detectielogica: per ademhaling (via `detect_breaths()` +
  `compute_breath_amplitudes()`) wordt de piek-dal-amplitude vergeleken
  met de lokale basislijn (mediaan voorgaande 10 ademhalingen)
- Ademhalingen met amplitude <70% baseline worden gemarkeerd als "reduced"
- Sample-level peak-mask wordt gecombineerd met envelope-mask via OR:
  events gevonden door **peak-methode óf envelope-methode** worden gescoord
- Verwacht effect: hogere sensitiviteit (minder onderschatting vs technicus),
  betere concordantie met menselijke RPSGT-scoring
- Toegepast op beide detectiepasses (initieel + post-recovery gecorrigeerd)
- Configureerbaar: `HYPOPNEA_THRESHOLD = 0.70` in `constants.py`

### Fixed — Hypopnea undercounting root causes

**SpO2 cross-contamination fix was too aggressive (CRITICAL):**
- Previous behavior: if next event starts within 30s of previous event end,
  SpO2 desaturation was set to `None` → Rule 1A always fails → event rejected
- At moderate OSAS (events 20–40s apart), this rejected **nearly all hypopneas**
- Fix: desaturation is ALWAYS computed; contamination flag is informational only
- Cross-contamination window reduced from 30s to 15s
- Expected impact: **major increase in OAHI** for patients with cluster events

**SpO2 nadir search window too short:**
- Increased POST_WIN_S from 30s to 45s in `get_desaturation()`
- Finger oximetry has 20–40s circulatory delay; nadirs at 30–45s were missed
- AASM inter-scorer reliability study recommends scoring desaturation
  within 30s of event end — but this is measured from the *oximeter reading*,
  not accounting for probe-to-finger delay

### Fixed — PDF visueel overzicht

**X-as uitlijning:**
- `bbox_inches="tight"` verwijderd uit `_ov_finish()` — dit verschoof marges
  per grafiek afhankelijk van y-label breedte
- Alle plots gebruiken nu vaste `subplots_adjust(left=0.09, right=0.98)`
- X-tick labels alleen op laatste plot (SpO2) — tussenliggende plots
  tonen alleen gridlijnen (compacter, beter uitgelijnd)

**Legende onderaan visueel overzicht:**
- Kleurcodering EVENT (OA/CA/MA/HYP/FR), SpO2 drempels, PHONO drempel

### Changed
- Version number updated to 0.8.14

---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.13]

### Added — Signal improvements and PDF fixes

**SpO2 timeseries in visual overview:**
- `analyze_spo2()` now saves 1 Hz downsampled timeseries in `result["timeseries"]`
- SpO2 curve renders in PDF section 0b alongside HYPNO, EVENT, POS, PHONO

**Position signal auto-mapping (`_map_position_signal()`):**
- Auto-detects whether position channel contains pre-coded 0–4 values
  or raw ADC/voltage data (e.g., 0–255 from SomnoMedics, Embla)
- Raw values → percentile-based quantization to 5 positions
- Fixes flat-line position plots on non-standard EDF recordings

**Hypopnea sensitivity improvement:**
- 3-second rolling mean (`uniform_filter1d`) applied to normalized flow
  before thresholding (`HYPOPNEA_SMOOTH_S = 3.0` in `constants.py`)
- Mimics human visual averaging: small oscillations above threshold
  no longer break events into fragments
- Reduces false negatives vs. technician scoring without lowering
  the AASM ≥30% amplitude criterion
- Applied to both initial detection and post-recovery corrected pass

### Changed
- Version number updated to 0.8.13

---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.12]

### Added — PSG overview page and clinical report improvements

**Visual overview page (PDF report):**
- Section 0a: EDF channel inventory table (all channels in recording)
- Section 0b: Stacked synced timeline plots — HYPNO, EVENT, POS, PHONO, SpO₂
- New plot functions: `_pos_img()` (body position), `_snore_img()` (snoring RMS),
  `_events_img()` (respiratory events timeline)
- Snore analysis now exposes `rms_1s` timeseries for plotting

**Ronchopathy section (10b):**
- Snoring duration (min), snoring % of TST, snoring index (/h)
- Always visible — shows "no snoring channel" if not available

**Flow Reduction Index — FRI (section 8d):**
- Counts rejected hypopneas (≥30% flow reduction, ≥10s) that meet neither
  ≥3% desaturation nor arousal criteria
- FRI = flow reductions per hour of sleep
- Clinically relevant for UARS / RDI evaluation
- Part of respiratory section (8d)

**Conclusion section (11) — manual only:**
- Auto-generated conclusions removed (`generate_conclusions()` no longer called)
- Empty conclusion shows: "To be completed by the treating physician"
- Manual diagnosis via report editor still works as before

**DISCLAIMER.md:**
- Full medical/clinical disclaimer (9 sections)
- Not a medical device, no CE/FDA, known limitations, data privacy,
  user responsibility, third-party components

### Changed
- Hypnogram moved into visual overview (0b) — separate section 2 removed
- All sections renumbered: 1–11 (was 1–12)
- Version number updated to 0.8.12 in app.py, PDF footer, i18n, DISCLAIMER
- NL docstrings added to all 80 functions in embedded `psgscoring/`

### Fixed
- **Numpy-unsafe `or` in `_resolve_flow_channels()`** — `flow_therm_data or
  flow_pressure_data` crashes with `ValueError: The truth value of an array
  with more than one element is ambiguous`. Replaced with explicit
  `is not None` ternary checks (3 lines in `psgscoring/pipeline.py`).

---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.11]

### Added — Signal processing and scoring improvements

**Phase-angle effort classification (`psgscoring/classify.py`):**
- New Rule 0: Hilbert instantaneous phase difference between thorax and abdomen
- Phase angle ≥45° → obstructive with confidence 0.75–0.97
- Fires before the 6 legacy rules; largely eliminates Rule-6 borderline defaults
  when RIP signals are adequate
- Minimum 5 s event duration required for reliable Hilbert estimate

**K-complex morphological exclusion (`arousal_analysis.py`):**
- Bipolar waveform check on first 1 s of each NREM arousal candidate
- Negative peak <−75 µV followed by positive peak >30 µV → K-complex suspected
- Local minimum arousal duration raised from 3.0 s to 5.0 s for that candidate
- Prevents K-complex trailing alpha-rebound from being scored as arousal

**CVR arousal confidence boost (`arousal_analysis.py`):**
- `_detect_cvr_confidence_boost()`: bradycardia (≥5 bpm dip) + tachycardia
  (≥10 bpm peak within 15 s) around borderline arousals → confidence +0.10–0.20
- No-op when no ECG/pulse channel is available
- Field `cvr_boost` stored per arousal event

**Patient-specific baseline anchoring (`psgscoring/signal.py`):**
- `compute_anchor_baseline()`: event-free N2 epochs → median RMS as
  patient-specific golden-standard baseline
- `mouth_breathing_suspected: True` when current signal RMS <60% of anchor
- Result in `output["anchor_baseline"]` via pipeline
- Requires ≥6 stable N2 epochs; `anchor_reliable: False` otherwise

**LightGBM confidence calibration (`psgscoring/classify.py`):**
- Optional 10-feature model via `PSGSCORING_LGBM_MODEL` environment variable
- Features: effort_ratio, raw_var_ratio, paradox_correlation, half/quarter efforts,
  phase_angle_deg, duration_s, rule_index
- Transparent fallback to rule-based confidence when model unavailable
- Field `lgbm_confidence` stored per event when model active

### Changed
- `detect_arousals()` now accepts `hr_data` and `sf_hr` parameters
- `run_arousal_respiratory_analysis()` passes `hr_data` through to `detect_arousals`
- `classify_apnea_type()` returns `phase_angle_deg` in detail dict
- Pipeline Step 7 passes `hr_data` and `sf_hr` to arousal analysis

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.10]

### Added — Five systematic over-counting corrections

**Fix 1 — Post-apnoea hyperpnoea baseline exclusion:**
- `_build_postapnea_recovery_mask()`: 30-s recovery window after each apnoea
- `_recompute_baseline_with_recovery_excluded()`: sparse cumsum loop (only recomputes
  anchor points where recovery mask covers >5% of 5-min window)
- Eliminates artificial baseline inflation from compensatory hyperventilation

**Fix 2 — SpO₂ cross-contamination:**
- `_spo2_cross_contaminated()`: checks if preceding event's 30-s post-event window
  is still active at candidate onset
- Suppresses SpO₂ coupling for contaminated candidates → field `spo2_cross_contaminated`
- Particularly relevant at AHI >60/h (inter-event interval <60 s)

**Fix 3 — Cheyne-Stokes AHI inflation:**
- `_flag_csr_events()`: after CSR detection, retroactively marks events whose
  inter-event interval matches detected periodicity (±12 s, up to 3× periodicity)
- Fields: `csr_flagged` per event, `n_csr_flagged`, `ahi_csr_corrected` in summary
- Applied in `pipeline.py` after Step 9 (CSR detection)

**Fix 4 — Borderline default confidence stratification:**
- Separate counts: `n_low_conf_borderline` (0.40–0.59), `n_low_conf_noise` (<0.40)
- Alternative index: `ahi_excl_noise` (AHI excluding confidence <0.40 events)
- Threshold sensitivity table in report: OAHI at ≥0.85 / ≥0.60 / ≥0.40 / all

**Fix 5 — Artefact-flank exclusion:**
- `_detect_signal_gaps()`: flatline/frozen segments ≥10 s → 15-s post-gap exclusion mask
- Applied to both apnoea and hypopnoea sleep masks
- Field `n_gap_excluded` in detection result

### Performance optimisations
- Replaced O(n×k) `np.where(labeled == i)` loops with O(n) `scipy.ndimage.find_objects()`
  (benchmark: 820 s extrapolated → 0.8 s for 350,000 candidate regions)
- `_setup_hypop_channel()`: reuses apnoea-channel baseline when sf equal, skipping
  duplicate `compute_dynamic_baseline()` call (+3–8 s saved)
- `compute_stage_baseline()`: vectorised epoch collection via `np.repeat()` instead of
  Python `list.extend()` loop; accepts `dynamic_baseline` parameter to avoid third call
- `_pre_event_baseline()`: replaced per-event `np.percentile` over 120-s window
  with O(1) lookup into precomputed dynamic baseline array
- Total overhead of 5 corrections: <1 s on 8-hour PSG at 256 Hz

### Report additions
- New section "Over-counting correction (v0.8.10)" in PDF and PSG reports
- Per-fix impact table + disclaimer that official AASM indices unchanged

---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.9]

### Added
- OAHI = all obstructive + hypopnoeas (AASM-conform); `oahi_conf60` supplementary
- Threshold sensitivity table in PDF report: OAHI at 0.85 / 0.60 / 0.40 / 0.00
- PSG report converted from landscape to portrait layout (matches PDF report)
- Confidence column per apnoea type in event table

### Changed
- Removed Cheyne-Stokes from section 9c → only in Conclusions via `conclusions.py`
- Removed orphan workers (kliniek_worker, worker9–worker16) via `--remove-orphans`

---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.8]

### Added
- OAHI confidence stratification: `oahi_conf60` (events with confidence >0.60)
- `confidence_bands` in summary: `{"high": N, "moderate": N, "borderline": N, "low": N}`
- Confidence breakdown table in PDF and PSG reports

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.7]

### Added
- 8 parallel RQ worker containers (`worker1`–`worker8`) via YAML anchor in docker-compose.yml
- Worker pool calibrated for Ryzen 9 5950X (16 real cores: 8 workers + OS headroom)

### Changed
- Single sequential worker replaced by parallel pool
- Estimated RAM usage: ~16 GB of 128 GB (2 GB per worker)

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.6]

### Fixed
- `_hypno_img()` in `generate_pdf_report.py`: `lang` was a free variable → `NameError`
- `build_hypnogram_figure()` in `generate_psg_report.py`: called before `lang` defined
- Hardcoded "Tijd (min)" → `t("pdf_time_axis", lang)`

---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.5]

### Added — Modular `psgscoring` package

- Monolithic `pneumo_analysis.py` (2,439 lines) split into 10 domain-specific submodules
- Strict one-directional dependency graph
- 112 unit tests across 6 test files (Python 3.9–3.12 CI matrix)
- Backward-compatible 81-line shim preserving all existing application imports
- Public API: 33 exported symbols in `psgscoring/__init__.py`

**Submodules:**

| Module | Lines | Responsibility |
|--------|-------|----------------|
| `constants.py` | 76 | Thresholds, band limits |
| `utils.py` | 134 | Sleep masks, helpers |
| `signal.py` | 307 | Linearisation, baseline, MMSD |
| `breath.py` | 254 | Breath-by-breath segmentation, flattening index |
| `classify.py` | 228 | Apnoea type classification |
| `spo2.py` | 218 | SpO₂ coupling, ODI |
| `plm.py` | 271 | PLM detection |
| `ancillary.py` | 277 | HR, snore, position, CSR |
| `respiratory.py` | 694 | Pipeline orchestration |
| `pipeline.py` | 334 | MNE-facing master function |

### Fixed
- PYTHONPATH guarantee: `ENV` in Dockerfile, `environment` in docker-compose.yml,
  `sys.path.insert()` guard in `wsgi.py` and `worker.py`

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.4]

### Fixed
- Language session/DB routing corrected for multi-language sites
- Redirect loop fixes (Flask `after_request` handler)

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.3]

### Added
- Full i18n coverage: 369 translation keys across NL/FR/EN/DE
- All UI, admin, and report text via `t(key, lang)` central function

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.2]

### Added
- Centralized `conclusions.py`: shared NL/FR/EN diagnostic text for PDF and PSG reports
- 7 standardised diagnostic conclusion templates per severity/type

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.1]

### Added
- Rolling 2-minute arousal baseline (replaces global baseline)
- Ratio-based spindle exclusion (sigma vs alpha+beta ratio)
- Rule 1B breath-cycle validation (reject if >1 complete breath between event and arousal)
- Clipping-to-artifact feedback: epochs with >5% clipped EEG → artifact mask
- FHIR R4 DiagnosticReport + Observation + CarePlan export

---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.8.0]

### Added — First public release

- EDF browser with channel-group filters (Neuro / Pneumo / Cardio)
- Role-based multi-site access control (admin / site_admin / user)
- Score editor: epoch-by-epoch manual correction
- Study deletion with full data cleanup
- Editable conclusions with PDF regeneration
- Interactive event list with jump-to-event navigation

---
---

## [0.8.29] — April 2026

### Added — Regression & property-based testing + flattening wiring
- **10 regression tests** (golden standard): obstructive/central/mixed classification on synthetic signals, dynamic baseline stability, SpO₂ desaturation detection, breath count, flattening passthrough
- **3 property-based tests** (Hypothesis): 500 random inputs to `classify_apnea_type()` verifying no crashes, valid output types, confidence bounds; low-effort signals verified to not produce high-confidence obstructive; short segments (2–100 samples) crash-free
- **Flattening index wired to hypopnea classification**: `_detect_hypopneas()` now computes mean flattening of overlapping breaths and passes it to `classify_apnea_type()` — high flattening boosts obstructive confidence, low flattening supports central
- **47 total tests**, all passing (37 unit + 10 regression/golden)


## [0.7.x] — Pre-public versions (internal)

> These versions were not published on GitHub. Documented here for completeness.

### [0.7.5] — v12: Event Editor & Production Polish

- Respiratory event overlay in EDF browser (OA/CA/MA/H/AR/RERA as colour-coded bars)
- Click-to-toggle event editor with real-time AHI recalculation
- Unified portrait A4 PDF report (12 sections, replaces separate landscape PSG report)
- EDF browser integrated across all result pages
- E-mail notification on analysis completion (optional SMTP)
- ProxyFix for Nginx Proxy Manager; all flash messages translated (NL/FR/EN)

### [0.7.0] — v11: EDF Signal Viewer

- Browser-based EDF visualisation with server-side epoch API
- Combined scorer + viewer (`scorer_v11.html`)
- Multi-epoch batch loading, channel selection, amplitude scaling

### [0.6.0] — v10: Interactive Epoch Scorer

- Click/keyboard (W/1/2/3/R) hypnogram editor
- Server-side sleep statistics recalculation after manual corrections
- PDF regeneration reflecting manual overrides

### [0.5.0] — v9: FHIR & Multi-site

- FHIR R4 DiagnosticReport export
- Multi-site configuration with site-specific settings
- Role-based access: admin / site_manager / user
- `/admin/sites` multi-tenant management

### [0.4.0] — v8: Clinical Scoring & Multi-language

- **Respiratory:** artifact exclusion from AHI/OAHI; OAHI definition; Rule 1B two-pass
- **Arousal:** EEG-based (alpha/theta/beta); respiratory coupling; RERA; RDI
- **PLM:** full AASM rewrite (amplitude threshold, bilateral merge, respiratory exclusion)
- **EDF+** export with scoring annotations
- Multi-language (NL/FR/EN) with 186+ translation keys via `i18n.py`
- Admin dashboard: user management, role-based menus
- Multi-site Docker architecture with Nginx Proxy Manager support

### [0.3.0] — v7: Pneumological Extension

- Channel selection UI (EEG, EOG, EMG)
- Apnoea/hypopnoea detection (AASM basis), AHI severity classification
- SpO₂, heart rate, body position, snoring, PLM (basic)
- Docker Compose: Redis + App + Worker (RQ task queue)
- PDF report expanded with respiratory, SpO₂, PLM sections

### [0.2.0] — v7.5: Performance & Compatibility

- `_hypno_to_list()` hang resolved
- `compute_dynamic_baseline()` optimised — 2500× speedup via `np.interp`
- YASA 0.7 compatibility fix (`sf_hypno` → `sf_hyp`)
- Headless rendering (`matplotlib.use('Agg')`), Redis `decode_responses` fix

### [0.1.0] — v6: Production Baseline

- Flask + Gunicorn + Docker (single container)
- YASA 0.7 LightGBM sleep staging (EEG + EOG + EMG)
- Basic PDF report with hypnogram and sleep statistics
- Deployment on Hetzner server (sleepai.be / sleepai.eu)
- Single-user login with password hashing

### [0.0.x] — v1–v5: Prototype

- Initial Flask webapp wrapping YASA
- Basic EDF upload and hypnogram generation
- Single-user, local execution
