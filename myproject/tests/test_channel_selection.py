"""Regressie: het kanaaloverzicht en het formulier moeten hetzelfde kanaal aanwijzen.

Tot v0.18.1 kreeg in channel_select.html elk matchend kanaal het attribuut
`checked` binnen één radiogroep. Bij radio's met dezelfde `name` wint de
laatste, terwijl de auto-detect-tabel erboven de eerste match toonde. Bij een
montage met EMG1/EMG2/EMG3 stond er dus "EMG1" in het overzicht (en in het
rapport) terwijl EMG3 de slaapstaging voedde. Twee runs van dezelfde nacht met
een iets andere exportmontage kregen daardoor een ander hypnogram — en dus een
andere TST en AHI — zonder dat er iets in de scoring veranderd was.

De tests renderen het echte template en tellen aangevinkte radio's.
"""

import os
import re
import sys

import pytest
from jinja2 import ChainableUndefined, ChoiceLoader, DictLoader, Environment, FileSystemLoader

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates"
)

# Somnomedics-achtige montage: drie submentale EMG-elektroden en twee
# been-EMG's, waarbij de been-kanalen ACHTER de kin-kanalen staan — precies de
# volgorde waarin "de laatste wint" de verkeerde kant op valt.
SOMNO = [
    "C3:A2", "C4:A1", "F3:A2", "F4:A1",
    "EOG1:A2", "EOG2:A1",
    "EMG1", "EMG2", "EMG3",
    "ECG II", "Flow Th.", "Pressure Flow", "RIP Thora", "RIP Abdom",
    "SpO2", "Pulse", "Pos.", "Snore",
    "PLMl", "PLMr",
]


def _render(channels):
    env = Environment(
        loader=ChoiceLoader([
            # base.html vervangen door een romp: we testen alleen het content-blok.
            DictLoader({"base.html": "{% block content %}{% endblock %}"}),
            FileSystemLoader(TEMPLATE_DIR),
        ]),
        autoescape=True,
        # Alles wat we niet meegeven rendert als leeg; het gaat hier puur om
        # de radio's, niet om de rest van het formulier.
        undefined=ChainableUndefined,
    )
    env.filters["channel_type_badge"] = lambda ch: ""
    tpl = env.get_template("channel_select.html")
    return tpl.render(
        t=lambda key, *a, **kw: key,
        csrf_token=lambda: "test-token",
        job_id="test-job",
        filename="test.edf",
        sfreq=256,
        channels=channels,
        best_eeg="C4:A1",
        pneumo_auto={},
        pneumo_channels={},
        available_profiles={},
        active_profile="aasm_v3_rec",
    )


def _checked_values(html, name):
    """Alle radio's met dit name-attribuut die `checked` dragen, in DOM-volgorde."""
    out = []
    for tag in re.findall(r"<input[^>]*>", html):
        if f'name="{name}"' not in tag:
            continue
        if "checked" not in tag:
            continue
        m = re.search(r'value="([^"]*)"', tag)
        out.append(m.group(1) if m else "")
    return out


def _summary_value(html, label_key):
    """De waarde die de auto-detect-tabel toont voor een rij."""
    m = re.search(
        re.escape(label_key)
        + r".*?autodetect-table__value\">\s*([^<]*?)\s*</span>",
        html,
        re.S,
    )
    return m.group(1) if m else None


@pytest.mark.parametrize("group", ["eeg_ch", "eog_ch", "emg_ch"])
def test_exactly_one_radio_is_checked_per_group(group):
    """Meerdere `checked` in één radiogroep is stil gedrag: de laatste wint."""
    checked = _checked_values(_render(SOMNO), group)
    assert len(checked) == 1, f"{group}: {len(checked)} aangevinkt -> {checked}"


def test_the_form_submits_the_channel_the_summary_shows():
    """Het overzicht en het formulier mogen niet uit elkaar lopen."""
    html = _render(SOMNO)
    assert _checked_values(html, "emg_ch")[0] == _summary_value(html, "channel_emg_chin")
    assert _checked_values(html, "eog_ch")[0] == _summary_value(html, "channel_eog")


def test_leg_emg_is_never_auto_selected_for_staging():
    """Been-EMG is geen kin-EMG: YASA's REM-detectie steunt op kin-atonie."""
    # Been-kanalen die 'EMG' in de naam dragen en achteraan staan — het geval
    # waarin de oude "laatste wint"-logica gegarandeerd de tibialis koos.
    montage = ["C4:A1", "EOG1:A2", "EMG Chin", "EMG Tib L", "EMG Tib R"]
    assert _checked_values(_render(montage), "emg_ch") == ["EMG Chin"]


def test_an_explicit_chin_channel_wins_from_a_generic_emg():
    montage = ["C4:A1", "EMG1", "EMG2", "Chin1-Chin2", "PLMl"]
    assert _checked_values(_render(montage), "emg_ch") == ["Chin1-Chin2"]


def test_without_a_usable_emg_the_none_option_stays_selected():
    """Geen EMG in de montage -> 'niet beschikbaar', niet een willekeurig kanaal."""
    montage = ["C4:A1", "C3:A2", "SpO2", "Pulse", "PLMl", "PLMr"]
    assert _checked_values(_render(montage), "emg_ch") == [""]


def test_without_an_eog_the_none_option_stays_selected():
    montage = ["C4:A1", "EMG Chin", "SpO2"]
    assert _checked_values(_render(montage), "eog_ch") == [""]
