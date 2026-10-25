# -*- coding: utf-8 -*-
"""Spolocne veci PriceTrap fabriky: cesty, stav, banka, nacitanie .env (kluce sa nikdy nevypisuju)."""
import json
import os
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):   # Windows konzola: "·" a "→" nesmu zhodit print
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[1]
BANK = REPO / "bank" / "cases.json"
SCRIPTS = REPO / "bank" / "scripts"   # hotove story.json od Claude rutiny (najstarsi ide prvy)
EPISODES = REPO / "episodes"
OUTPUT = REPO / "output"
REMOTION = REPO / "remotion"
STATE = REPO / "state.json"

# .env: hodnoty idu len do os.environ (setdefault = skutocne env a skorsi subor vyhravaju), nikdy sa nevypisuju
for _env in (REPO / ".env", Path.home() / ".config/watch/.env", Path.home() / "FactoryAnim/.env",
             Path("D:/Praca/FactoryAnim/.env")):
    try:
        if not _env.is_file():
            continue
        for _l in _env.read_text(encoding="utf-8-sig").splitlines():
            _l = _l.strip()
            if "=" in _l and not _l.startswith("#"):
                _k, _v = _l.split("=", 1)
                _k = _k.strip().removeprefix("export ").strip()
                _v = _v.strip().strip('"').strip("'")
                if _k and _v:
                    os.environ.setdefault(_k, _v)
    except OSError:
        pass


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def save(p, data):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")


def state():
    st = load(STATE) if STATE.exists() else {}
    st.setdefault("next_ep", 1)
    st.setdefault("used", [])
    st.setdefault("episodes", {})
    return st


def save_state(st):
    save(STATE, st)


def bank():
    """Zoznam pripadov z bank/cases.json (poradie banky = poradie vyroby)."""
    return load(BANK)["cases"] if BANK.exists() else []


def case_by_id(cid):
    return next((c for c in bank() if c.get("id") == cid), None)


def case_from_file(path, cid=None):
    """Pripad zo suboru: jeden objekt, zoznam alebo {"cases": [...]} (vtedy podla id)."""
    data = load(path)
    if isinstance(data, dict) and "cases" in data:
        data = data["cases"]
    if isinstance(data, list):
        data = next((c for c in data if cid is None or c.get("id") == cid), None)
    return data if isinstance(data, dict) else None
