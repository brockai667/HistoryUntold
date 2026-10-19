# -*- coding: utf-8 -*-
"""Denny beh PriceTrap fabriky (GitHub Actions, bez PC, 0 Claude tokenov):
  1) vyber pripadu z banky  2) Groq napise story.json (write_case.py)  3) prep (hlas, edge-tts) + Remotion render
  4) obal a popisok  5) GitHub Release ep-NNN (video + popisok; Damian nahra z mobilu)  6) stav do state.json
    python tools/run.py [--case ID] [--no-post] [--force]
--case ID  = konkretny pripad (inak prvy nepouzity z banky; ak autor zlyha, skusi sa este jeden dalsi, max 2 za beh)
--no-post  = len vyrobi video a popisok (Release ani stav sa nemeni)
--force    = povoli uz pouzity pripad (--case) a prepise existujuci story.json"""
import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import EPISODES, OUTPUT, REMOTION, REPO, bank, case_by_id, load, save_state, state  # noqa: E402

PY = sys.executable
CHILD_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}
MAX_CASES = 2   # ak autor zlyha, skusi sa este jeden dalsi pripad


def now():
    return dt.datetime.now(dt.timezone.utc)


def sh(*cmd, cwd=REPO, quiet=False):
    """Spusti prikaz bez shellu (zoznam argumentov), vrati navratovy kod."""
    print("$", " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run([str(c) for c in cmd], cwd=str(cwd), shell=False, env=CHILD_ENV,
                       **({"capture_output": True} if quiet else {}))
    return r.returncode


def npx():
    return shutil.which("npx") or "npx"


def gh():
    return shutil.which("gh") or "gh"


def props_arg(ep):
    return "--props=" + json.dumps({"ep": ep}, separators=(",", ":"))


def render(ep):
    """prep (hlas, hudba, episode.json) + Remotion render -> output/<ep>.mp4"""
    OUTPUT.mkdir(exist_ok=True)
    if sh(PY, "remotion/tools/prep.py", f"episodes/{ep}/story.json"):
        sys.exit("prep zlyhal")
    mp4 = OUTPUT / f"{ep}.mp4"
    if sh(npx(), "remotion", "render", "Episode", f"../output/{ep}.mp4", props_arg(ep), "--crf=22", "--concurrency=100%",
          cwd=REMOTION):
        sys.exit("render zlyhal")
    if not mp4.exists() or mp4.stat().st_size < 10_000:
        sys.exit("render nevyrobil video")
    return mp4


def cover(ep):
    """Obal = still z druheho uderu + 1 s. Nie je kriticky (try/except) - epizoda ide aj bez neho."""
    out = OUTPUT / f"{ep}-cover.jpg"
    try:
        d = load(REMOTION / "public" / ep / "episode.json")
        beats = d.get("beats") or []
        frame = int(((beats[1]["t0"] if len(beats) > 1 else 0) + 1) * d.get("fps", 30))
        rc = sh(npx(), "remotion", "still", "Episode", f"../output/{ep}-cover.jpg", props_arg(ep), f"--frame={frame}",
                cwd=REMOTION)
        if rc:
            print("obal zlyhal (kod", rc, ")")
    except Exception as e:
        print("obal zlyhal:", e)
    return out if out.exists() else None


def release(n, ep, title, mp4, txt, cov):
    """Video + popisok do GitHub Release ep-NNN (repo je verejne -> stiahnutie z mobilu bez prihlasenia)."""
    tag = f"ep-{n:03d}"
    caption = txt.read_text(encoding="utf-8").split("\n", 1)[1].strip()
    notes = OUTPUT / f"{ep}-release-notes.md"
    notes.write_text("Popisok (skopíruj celý blok):\n\n```\n" + caption + "\n```\n\n"
                     f"Obal: súbor `{cov.name if cov else ep + '-cover.jpg'}` (TikTok > Vybrať obal > z galérie).\n",
                     encoding="utf-8")
    assets = [str(mp4), str(txt)] + ([str(cov)] if cov else [])
    rel_title = f"PRICE TRAP · {title}"
    if sh(gh(), "release", "view", tag, quiet=True) == 0:   # opakovany beh -> prepisat subory a text
        rc = sh(gh(), "release", "upload", tag, *assets, "--clobber") or \
            sh(gh(), "release", "edit", tag, "--title", rel_title, "--notes-file", str(notes))
    else:
        rc = sh(gh(), "release", "create", tag, *assets, "--title", rel_title, "--notes-file", str(notes))
    if rc:
        sys.exit("GitHub Release zlyhal")
    return tag


def publish_buffer(n, ep, title, mp4, txt):
    """TODO(Buffer) - ZATIAL STUB: kanaly pre PriceTrap este neexistuju, video ide len do GitHub Release a Damian
    ho nahra z mobilu. Az budu kanaly: poslat mp4 + popisok cez push_to_buffer.py (vzor: WealthFactory-vote / HiddenEarth),
    token do secrets (BUFFER_TOKEN) a do env v .github/workflows/daily.yml. Vrati zoznam sluzieb, kam sa naplanovalo."""
    print("Buffer: zatiaľ nepripojený (TODO) - preskakujem")
    return []


def main():
    ap = argparse.ArgumentParser(description="Denný beh PriceTrap: prípad -> story -> video -> GitHub Release -> stav.",
                                 epilog="Bez --case sa berie prvý nepoužitý prípad z bank/cases.json.")
    ap.add_argument("--case", metavar="ID", help="konkrétny prípad z banky")
    ap.add_argument("--no-post", action="store_true", help="len vyrobí video a popisok (Release ani stav sa nemení)")
    ap.add_argument("--force", action="store_true", help="povolí už použitý prípad (--case) a prepíše existujúci story.json")
    a = ap.parse_args()

    st = state()
    n = st["next_ep"]
    if a.case:
        c = case_by_id(a.case)
        if not c:
            sys.exit(f"prípad '{a.case}' nie je v bank/cases.json")
        if c["id"] in st["used"] and not a.force:
            sys.exit(f"prípad '{a.case}' už bol použitý (--force = použiť znova)")
        todo = [c]
    else:
        todo = [c for c in bank() if c["id"] not in st["used"]][:MAX_CASES]
        if not todo:
            sys.exit("banka je vyčerpaná - treba doplniť bank/cases.json")

    chosen = None
    for c in todo:
        ep = f"{n:03d}-{c['id']}"
        story = EPISODES / ep / "story.json"
        if story.exists() and not a.force:
            print(f"{story.relative_to(REPO)} už existuje - autora preskakujem")
            chosen = (c, ep)
            break
        if sh(PY, "-u", "tools/write_case.py", c["id"], "--out", f"episodes/{ep}/story.json") == 0:
            chosen = (c, ep)
            break
        print(f"autor zlyhal pre prípad {c['id']}", file=sys.stderr)
    if not chosen:
        sys.exit("autor zlyhal pre všetky skúšané prípady")
    c, ep = chosen

    title = load(EPISODES / ep / "story.json")["title"]
    mp4 = render(ep)
    cov = cover(ep)
    caption = (REMOTION / "public" / ep / "caption.txt").read_text(encoding="utf-8").strip()
    txt = OUTPUT / f"{ep}.txt"
    txt.write_text(f"{title}\n\n{caption}\n", encoding="utf-8")
    print("video:", mp4, round(mp4.stat().st_size / 1e6, 1), "MB")
    if a.no_post:
        print("--no-post: nezverejňujem")
        return

    tag = release(n, ep, title, mp4, txt, cov)
    publish_buffer(n, ep, title, mp4, txt)
    if c["id"] not in st["used"]:
        st["used"].append(c["id"])
    st["episodes"][str(n)] = {"id": c["id"], "title": title, "posted_at": now().isoformat(timespec="seconds"), "release": tag}
    st["next_ep"] = n + 1
    save_state(st)
    print(f"HOTOVO: ep {n:03d}")


if __name__ == "__main__":
    main()
