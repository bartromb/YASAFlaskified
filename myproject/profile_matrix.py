"""
profile_matrix.py — de profielmatrix voor het rapport, en de studieprofiel-set.

Pure functies, geen Flask en geen ReportLab: de rapportlaag en de webweergave
lezen hier hetzelfde uit, en de tests draaien zonder een PDF te bouwen.

WAT HIER GEMETEN IS EN WAT DE SPEC AANNAM
-----------------------------------------
`YF_PROFIELMATRIX_SPEC.md` opent met: "`run_profile_comparison` (tasks.py) draait
sinds v0.9.0 de hele registry (nu 19 profielen)". Dat is niet zo. Die functie
komt in de hele codebase exact één keer voor — haar eigen `def`. Ze wordt nooit
aangeroepen, niet ge-enqueued en niet via een string gedispatcht, en
`profile_comparison.json` wordt dus nooit geschreven.

Wat de PDF wél leest komt uit **psgscoring**, niet uit tasks.py:
`pipeline.py` vult `respiratory["profile_comparison"]` met drie arms
(`strict`/`standard`/`sensitive`, uitsluitend `oahi`) en `output["ahi_interval"]`
met dezelfde drie arms mét `ahi`, `oahi` en `severity`. Dat zijn de
intervalarmen die de pijplijn toch al draait voor de robustheidsgraad.

Twee gevolgen voor deze module:

1. De matrix heeft **twee mogelijke bronnen** en zegt welke ze gebruikte. Een
   volledige vergelijking mét `_meta` als iemand `run_profile_comparison`
   inschakelt; anders de drie intervalarmen die elke job al oplevert. Een matrix
   die stilzwijgend leeg blijft omdat de bron niet bestaat, zou de spec
   "uitgevoerd" laten lijken zonder iets te tonen.
2. Kolommen die de bron niet heeft — CAI, eventaantal, RDI bij de
   intervalbron — worden **"—"**, nooit 0,0. Dat is de regel die de spec zelf
   voor de RDI-cel stelt, hier consequent toegepast: een 0,0 in een rapport is
   een meting, en een streepje is een ontbrekende meting.

De rijlabels en de regelset komen uit de registry. De tabel die dit vervangt had
hard-coded parameterkolommen ("70% (≥30%)", "30s", "3s", "15s") die uit geen
enkele bron kwamen en dus een tweede waarheid waren — precies het defect dat de
dropdown-fix van v0.22.0 elders al opruimde.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

FROZEN_FAMILIES = ("dataset", "legacy")
CLINICAL = "clinical"
EXPLORATORY = "exploratory"

#: De drie intervalarmen zoals psgscoring ze in `ahi_interval` benoemt, met de
#: canonieke registry-naam ernaast. De legacy-aliassen zijn de sleutels in die
#: dict; de registry kent alleen de canonieke namen.
INTERVAL_ALIASES = {
    "strict": "aasm_v3_strict",
    "standard": "aasm_v3_rec",
    "sensitive": "aasm_v3_sensitive",
}

MISSING = "—"


def _registry():
    try:
        from psgscoring.profiles import PROFILES
        return PROFILES
    except Exception as exc:                                  # pragma: no cover
        logger.warning("profielregistry niet beschikbaar: %s", exc)
        return {}


# ─────────────────────────────────────────────────────────────────────────
# 1. Studieprofiel-set
# ─────────────────────────────────────────────────────────────────────────

def validate_study_set(cfg: dict | None, registry: dict | None = None) -> tuple[dict, list[str]]:
    """Valideer een studieprofiel-set tegen de registry.

    Returns ``(resolved, errors)``. Bij fouten is `resolved` de veilige
    terugval (huidig gedrag) en bevat `errors` leesbare meldingen; de aanroeper
    beslist of hij weigert of doorgaat. Nooit stil corrigeren: een studie die
    denkt op `mesa_shhs` te draaien moet dat te horen krijgen, niet een ander
    profiel toegewezen krijgen.

    De bevroren families zijn **nooit** primair. Ze reproduceren gepubliceerde
    cijfers en zijn afgeschermd tegen reparaties die elk ander profiel wél
    krijgt; een klinisch hoofdresultaat daarop baseren is geen keuze maar een
    misverstand.
    """
    reg = registry if registry is not None else _registry()
    errors: list[str] = []
    cfg = dict(cfg or {})

    include_exp = bool(cfg.get("include_experimental", False))

    primary = cfg.get("primary_profile") or None
    if primary is not None:
        if primary not in reg:
            errors.append(
                f"primary_profile '{primary}' bestaat niet in psgscoring "
                f"{_version()}. Beschikbaar: {', '.join(sorted(reg))}")
            primary = None
        else:
            fam = reg[primary].family
            if fam in FROZEN_FAMILIES:
                errors.append(
                    f"primary_profile '{primary}' hoort tot de bevroren familie "
                    f"'{fam}': dat profiel reproduceert gepubliceerde cijfers en "
                    f"mag geen hoofdresultaat dragen. Zet het desgewenst in "
                    f"comparison_profiles.")
                primary = None
            elif fam == EXPLORATORY and not include_exp:
                errors.append(
                    f"primary_profile '{primary}' is experimenteel; zet "
                    f"include_experimental aan als dat de bedoeling is.")
                primary = None

    explicit = cfg.get("comparison_profiles") or None
    group = cfg.get("comparison_group") or None
    profiles: list[str] | None = None

    if explicit:
        unknown = [p for p in explicit if p not in reg]
        if unknown:
            errors.append(f"onbekende comparison_profiles: {', '.join(unknown)}")
        profiles = [p for p in explicit if p in reg]
    elif group:
        try:
            from psgscoring.profiles import PROFILE_GROUPS
            if group not in PROFILE_GROUPS:
                errors.append(
                    f"comparison_group '{group}' bestaat niet. Beschikbaar: "
                    f"{', '.join(sorted(PROFILE_GROUPS))}")
            else:
                profiles = [p for p in PROFILE_GROUPS[group] if p in reg]
        except Exception as exc:                              # pragma: no cover
            errors.append(f"profielgroepen niet beschikbaar: {exc}")

    if profiles is not None and not include_exp:
        # Alleen filteren wat NIET expliciet gevraagd is: een expliciete lijst is
        # een keuze van de onderzoeker en die overrulen we niet stil.
        if not explicit:
            profiles = [p for p in profiles
                        if reg[p].family != EXPLORATORY]

    return ({"primary_profile": primary,
             "comparison_profiles": profiles,
             "include_experimental": include_exp}, errors)


def _version() -> str:
    try:
        import psgscoring
        return psgscoring.__version__
    except Exception:                                         # pragma: no cover
        return "?"


# ─────────────────────────────────────────────────────────────────────────
# 2. De matrix
# ─────────────────────────────────────────────────────────────────────────

def _num(v):
    """Getal of None. Een lege string, None of een niet-getal wordt None, zodat
    de formatter er '—' van maakt in plaats van 0,0."""
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def fmt(v, decimals: int = 1) -> str:
    """Eén formatter voor de hele matrix, zodat een ontbrekende waarde overal
    hetzelfde streepje krijgt en nergens per ongeluk als 0,0 verschijnt."""
    n = _num(v)
    return MISSING if n is None else f"{n:.{decimals}f}"


def fmt_delta(v) -> str:
    """Getekend, één decimaal. 0,0 is een echte uitkomst hier (identiek aan het
    primaire profiel) en krijgt dus '+0.0', geen streepje."""
    n = _num(v)
    if n is None:
        return MISSING
    return f"{n:+.1f}"


def _row_for(name: str, data: dict, reg: dict, primary: str | None) -> dict:
    p = reg.get(name)
    fam = p.family if p else "?"
    display = p.display_name if p else name
    ruleset = f"{p.aasm_version} · {p.aasm_rule}" if p else MISSING
    return {
        "name": name,
        "display_name": display,
        "family": fam,
        "ruleset": ruleset,
        "is_primary": name == primary,
        "is_frozen": fam in FROZEN_FAMILIES,
        "is_experimental": fam == EXPLORATORY,
        "ahi": _num(data.get("ahi") if "ahi" in data else data.get("ahi_total")),
        "oahi": _num(data.get("oahi")),
        # CAI, niet CAHI: psgscoring levert `central_index` (centrale apneus),
        # geen centrale apneu-hypopneu-index. Beide oude sleutels bestonden
        # nergens, dus deze kolom was altijd leeg.
        "cai": _num(data.get("central_index")),
        "rdi": _num(data.get("rdi")),
        "n_events": _num(data.get("n_events") if "n_events" in data
                         else data.get("n_ah_total")),
        "severity": data.get("severity") or MISSING,
    }


def _sort_key(row: dict) -> tuple:
    """Primair bovenaan, dan klinisch, dan exploratief, dan bevroren."""
    if row["is_primary"]:
        bucket = 0
    elif row["is_frozen"]:
        bucket = 3
    elif row["is_experimental"]:
        bucket = 2
    else:
        bucket = 1
    return (bucket, row["display_name"])


def build_matrix(pneumo: dict, comparison: dict | None = None,
                 registry: dict | None = None) -> dict:
    """Bouw de profielmatrix uit wat er werkelijk gemeten is.

    Bronvoorkeur:
      1. `comparison` mét `_meta` — een volledige vergelijking.
      2. `pneumo["ahi_interval"]` — de drie intervalarmen die elke job levert.
      3. Alleen het primaire profiel.

    Returns een dict met `rows`, `primary`, `source`, `footnotes` en
    `primary_mismatch`.
    """
    reg = registry if registry is not None else _registry()
    meta = (pneumo.get("meta") or {})
    resp = (pneumo.get("respiratory") or {})
    summary = (resp.get("summary") or {})
    primary = meta.get("scoring_profile") or None
    # Legacy-alias in oude jobs: 'standard' bestaat niet in de registry.
    primary = INTERVAL_ALIASES.get(primary, primary)

    rows: list[dict] = []
    source = "primary_only"
    pre_config = False

    if comparison and any(k != "_meta" for k in comparison):
        cmeta = comparison.get("_meta") or {}
        source = "full_comparison"
        pre_config = not cmeta
        primary = INTERVAL_ALIASES.get(cmeta.get("primary_profile") or primary,
                                       cmeta.get("primary_profile") or primary)
        for name, data in comparison.items():
            if name == "_meta" or not isinstance(data, dict):
                continue
            canon = INTERVAL_ALIASES.get(name, name)
            rows.append(_row_for(canon, data, reg, primary))
    else:
        interval = pneumo.get("ahi_interval") or {}
        arms = {k: v for k, v in interval.items()
                if k in INTERVAL_ALIASES and isinstance(v, dict)}
        if arms:
            source = "ahi_interval"
            for alias, data in arms.items():
                rows.append(_row_for(INTERVAL_ALIASES[alias], data, reg, primary))
        elif primary:
            rows.append(_row_for(primary, summary, reg, primary))

    # De primair-assert. De spec vraagt expliciet om de vorm waarin het primaire
    # profiel MEEdraait in de vergelijking en de rapportlaag controleert dat het
    # met het hoofdresultaat overeenkomt: die assert is een gratis
    # regressietest op determinisme, en een mismatch verraadt precies het soort
    # cache-, env- of versieverschil tussen twee codepaden dat je wilt zien.
    primary_mismatch = None
    head_ahi = _num(summary.get("ahi_total"))
    prow = next((r for r in rows if r["is_primary"]), None)
    if prow is not None and head_ahi is not None and prow["ahi"] is not None:
        if abs(prow["ahi"] - head_ahi) >= 0.05:
            primary_mismatch = {"matrix": prow["ahi"], "head": head_ahi,
                                "profile": prow["name"]}
            logger.error(
                "profielmatrix: primaire rij (%s) geeft AHI %.2f terwijl het "
                "hoofdresultaat %.2f geeft. Twee codepaden zijn uit de pas — "
                "verdenk de voorbewerkingscache, een env-override of een "
                "versieverschil.", prow["name"], prow["ahi"], head_ahi)

    # Delta ten opzichte van het primaire profiel.
    base = prow["ahi"] if prow else None
    for r in rows:
        r["delta_ahi"] = (None if base is None or r["ahi"] is None
                          else r["ahi"] - base)

    rows.sort(key=_sort_key)

    footnotes = {
        "primary": bool(prow),
        "rdi_missing": any(r["rdi"] is None for r in rows),
        "frozen_present": any(r["is_frozen"] for r in rows),
        "experimental_present": any(r["is_experimental"] for r in rows),
        "pre_config": pre_config,
        "source": source,
    }
    return {"rows": rows, "primary": primary, "source": source,
            "footnotes": footnotes, "primary_mismatch": primary_mismatch}
