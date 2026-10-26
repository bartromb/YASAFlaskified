"""De codetabel van het houdingskanaal bereikt psgscoring: per job of via de
installatie-env (18-10-2026)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tasks import _position_code_map  # noqa: E402


def test_zonder_config_geen_tabel(monkeypatch):
    monkeypatch.delenv("YASAFLASKIFIED_POSITION_CODE_MAP", raising=False)
    assert _position_code_map({}) is None


def test_jobconfig_wint_en_wordt_genormaliseerd(monkeypatch):
    monkeypatch.setenv("YASAFLASKIFIED_POSITION_CODE_MAP", json.dumps({"1": "Prone"}))
    m = _position_code_map({"position_code_map": {"2": "Supine", 3: "Left"}})
    assert m == {2: "Supine", 3: "Left"}


def test_env_json_wordt_gelezen(monkeypatch):
    monkeypatch.setenv("YASAFLASKIFIED_POSITION_CODE_MAP",
                       '{"1": "Upright", "2": "Supine", "3": "Left", "4": "Right", "6": "Prone"}')
    assert _position_code_map({}) == {1: "Upright", 2: "Supine", 3: "Left", 4: "Right", 6: "Prone"}


def test_onleesbare_env_wordt_genegeerd(monkeypatch, caplog):
    monkeypatch.setenv("YASAFLASKIFIED_POSITION_CODE_MAP", "{dit is geen json")
    assert _position_code_map({}) is None
