# Demo-video-script — v0.38.x (najaar 2026)

Vervangt de v0.11.2-walkthrough. Zelfde vorm als toen: **±100 s
schermopname zonder audio**, ondertitels per taal in post (vier
exports: en/nl/fr/de), 1920×1080, H.264, doel ≤ 10 MB per taal.

## Voorbereiding (checklist)

- [ ] Schone browser, 1920×1080-venster, cursor zichtbaar, geen bladwijzers/extensies in beeld.
- [ ] Demo-account (geen echte gebruikersnaam in beeld; "demo" volstaat).
- [ ] Demo-opname: `python myproject/generate_demo_edf.py` → synthetische EDF,
      **géén patiëntdata in de video**. NB: de demo-EDF heeft geen
      Pleth-kanaal, dus de Herkomst-rij toont "Arousal re-ranking …:
      off — pleth ontbreekt". Dat is een bewust shot (scène 7c): het
      rapport zegt óók wat er níet draaide en waarom.
      *Optionele upgrade vóór opname:* Pleth + hartslagrespons toevoegen
      aan `generate_demo_edf.py` zodat de rij "active — …, k=…" toont —
      klein codewerk, apart te vragen.
- [ ] Taal van de sessie instellen per export (NL/FR/EN/DE) — de app en
      het rapport volgen mee, dus élke taalversie is echt die taal.
- [ ] Eén analyse vooraf al gedraaid (voor scène 6-8 zonder wachttijd).

## Scènes

Tijden zijn richtwaarden; knip strak, geen dode seconden.

| # | t | Beeld + handeling | Ondertitel NL |
|---|-----|---|---|
| 1 | 0–8 s | Landing slaapkliniek.be; traag scrollen langs hero → sectie **"Wat is nieuw (najaar 2026)"**, cursor wijst tegel 1 (autonome herordening) en 2 (FDA-valuta) aan | Automatische PSG-analyse — open source, en meetbaar eerlijk. |
| 2 | 8–13 s | Inloggen (demo-account) | Inloggen. Accounts gratis via de auteur. |
| 3 | 13–24 s | Upload: sleep de demo-EDF in het vak; wijs de **anonimiseren-in-de-browser**-optie aan; BDF-vermelding in beeld | EDF of BDF, geanonimiseerd vóór hij je computer verlaat. 24-bit blijft 24-bit. |
| 4 | 24–38 s | Kanaalkeuze: automatische herkenning; open de **twee flow-dropdowns** (thermistor én nasale druk apart); profiel-dropdown toont families met `aasm_v3_rec` bovenaan | Kanalen herkend, door jou te corrigeren. Thermistor en neusdruk apart — zoals de AASM het vraagt. |
| 5 | 38–44 s | Start analyse → voortgangsbalk (harde knip, geen echte wachttijd) | Volledige analyse in 5–10 minuten. Geen lokale software nodig. |
| 6 | 44–52 s | Dashboard: joblijst met AHI/ODI/PLMI-kolommen; klik het klare rapport open | Alle onderzoeken op één dashboard. |
| 7a | 52–60 s | PDF p. 1: KPI's + **Aandachtspunten**-kader (cursor volgt de bullets) | Het rapport benoemt zelf wat je aandacht vraagt. |
| 7b | 60–70 s | Scroll naar **Herkomst-tabel**; cursor op de rijen apneu/hypopneu-sensor en **"Arousal re-ranking (autonomic, Pleth/HR)"** | Elke analyse toont welk kanaal hem voedde — de kanaalkeuze bepaalt het resultaat. |
| 7c | 70–78 s | Zoom op die rerank-rij ("off — pleth ontbreekt" op de demo; "active — …, k=…" mét Pleth) + de **scoorderverwachting**-noot eronder | Draaide iets niet, dan staat er waarom. En het rapport zegt hoe eens twee ménselijke scoorders het hier zouden zijn. |
| 8 | 78–90 s | `/review/<job>`: eventcontrole met signaalpanelen; klik één event open, panel verschijnt | Elk gescoord event is controleerbaar op het signaal zelf. |
| 9 | 90–100 s | Terug naar landing; slotkaart (tekst in post): URL + disclaimer | slaapkliniek.be — screening en second reader. Vervangt geen manuele scoring of diagnose. |

## Ondertitels — EN / FR / DE

| # | EN | FR | DE |
|---|---|---|---|
| 1 | Automated PSG analysis — open source, and measurably honest. | Analyse PSG automatisée — open source, et honnête de façon mesurable. | Automatisierte PSG-Analyse — Open Source, und messbar ehrlich. |
| 2 | Sign in. Accounts are free via the author. | Connexion. Comptes gratuits via l'auteur. | Anmelden. Konten kostenlos über den Autor. |
| 3 | EDF or BDF, anonymised before it leaves your computer. 24-bit stays 24-bit. | EDF ou BDF, anonymisé avant de quitter votre ordinateur. Le 24 bits reste du 24 bits. | EDF oder BDF, anonymisiert bevor es Ihren Rechner verlässt. 24 Bit bleibt 24 Bit. |
| 4 | Channels recognised, yours to correct. Thermistor and nasal pressure separately — as the AASM asks. | Canaux reconnus, corrigeables par vous. Thermistance et pression nasale séparément — comme le demande l'AASM. | Kanäle erkannt, von Ihnen korrigierbar. Thermistor und Nasendruck getrennt — wie es die AASM verlangt. |
| 5 | Full analysis in 5–10 minutes. No local software required. | Analyse complète en 5–10 minutes. Aucun logiciel local requis. | Vollständige Analyse in 5–10 Minuten. Keine lokale Software nötig. |
| 6 | Every study on one dashboard. | Chaque examen sur un seul tableau de bord. | Jede Untersuchung auf einem Dashboard. |
| 7a | The report itself flags what needs your attention. | Le rapport signale lui-même ce qui mérite votre attention. | Der Bericht benennt selbst, was Ihre Aufmerksamkeit braucht. |
| 7b | Every analysis shows which channel fed it — channel choice determines the result. | Chaque analyse montre quel canal l'a alimentée — le choix des canaux détermine le résultat. | Jede Analyse zeigt, welcher Kanal sie speiste — die Kanalwahl bestimmt das Ergebnis. |
| 7c | If something didn't run, it says why. And the report tells you how much two *human* scorers would agree here. | Si quelque chose n'a pas tourné, il dit pourquoi. Et le rapport indique à quel point deux cotateurs *humains* seraient d'accord ici. | Lief etwas nicht, steht da warum. Und der Bericht sagt, wie einig sich zwei *menschliche* Scorer hier wären. |
| 8 | Every scored event can be checked against the signal itself. | Chaque événement coté peut être vérifié sur le signal lui-même. | Jedes bewertete Ereignis ist am Signal selbst überprüfbar. |
| 9 | slaapkliniek.be — screening and second reader. Does not replace manual scoring or diagnosis. | slaapkliniek.be — dépistage et second lecteur. Ne remplace ni la cotation manuelle ni le diagnostic. | slaapkliniek.be — Screening und Zweitbefunder. Ersetzt weder manuelle Auswertung noch Diagnose. |

## Opname- en montagenotities

- **Wat NIET in beeld mag**: echte patiëntnamen/ID's, e-mailadressen,
  echte joblijsten van productie. Neem op tegen de VM (192.168.1.253) of
  een verse productie-demo-account met alleen de demo-opname.
- Cursor is de verteller: rustig bewegen, 1 s stilhouden op wat de
  ondertitel noemt; geen muisgezwaai.
- Knippen op de handeling (klik = knip), voortgang van scène 5 met één
  harde tijdsprong; geen versnelde weergave van scrollen in het rapport.
- Ondertitels onderin, één regel, max ~90 tekens; huisstijl van de
  landingspagina (donkerblauw op wit).
- Export per taal: neem de UI óók in die taal op (taalkeuze vooraf), niet
  alleen de ondertitel wisselen.
- Na afloop: mp4's als release-assets aan de actuele tag hangen en de
  vier links + poster in `README.md § Demo` bijwerken (staan nu nog op
  v0.11.2).
