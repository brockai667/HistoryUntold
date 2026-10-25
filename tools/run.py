# -*- coding: utf-8 -*-
"""Denny beh PriceTrap fabriky (GitHub Actions, bez PC, 0 Claude tokenov):
  1) skript: najstarsi z bank/scripts/ (pise ho Claude rutina kazde 3 dni, musi prejst lintom);
     ak je banka skriptov prazdna, fallback: Groq napise story.json k prvemu nepouzitemu pripadu (write_case.py)
  2) prep (hlas Orpheus troy, inak edge-tts) + Remotion render  3) obal a popisok
  4) GitHub Release ep-NNN (video + popisok; Damian nahra z mobilu)  5) stav do state.json, skript do bank/scripts/used/
    python tools/run.py [--case ID] [--no-post] [--force]
--case ID  = konkretny pripad cez autora (bez --case: banka skriptov, potom prvy nepouzity pripad; max 2 pokusy autora)
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
from common import EPISODES, OUTPUT, REMOTION, REPO, SCRIPTS, bank, case_by_id, load, save_state, state  # noqa: E402

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
    loudness(mp4)
    return mp4


def loudness(mp4):
    """Hlasitost na -14 LUFS (mix z Remotionu ma ~-21, na mobile je potichu). Obraz sa len kopiruje. Nie je kriticke."""
    tmp = mp4.with_name(mp4.stem + "-loud.mp4")
    rc = sh(shutil.which("ffmpeg") or "ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-c:v", "copy",
            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", tmp)
    if rc == 0 and tmp.exists() and tmp.stat().st_size > 10_000:
        tmp.replace(mp4)
    else:
        print("loudnorm zlyhal - video ostáva s pôvodnou hlasitosťou")


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


def bank_script(st):
    """Najstarsi nepouzity skript z bank/scripts/*.json, ktory prejde lintom -> (cesta, id pripadu) alebo None."""
    for p in sorted(SCRIPTS.glob("*.json")):
        try:
            cid = load(p).get("id")
        except (OSError, ValueError, AttributeError):
            cid = None
        if not cid or cid in st["used"]:
            continue
        if sh(PY, "tools/lint.py", p.relative_to(REPO).as_posix()) == 0:
            return p, cid
        print(f"{p.name} neprešiel lintom - preskakujem", file=sys.stderr)
    return None


def main():
    ap = argparse.ArgumentParser(description="Denný beh PriceTrap: prípad -> story -> video -> GitHub Release -> stav.",
                                 epilog="Bez --case sa berie prvý nepoužitý prípad z bank/cases.json.")
    ap.add_argument("--case", metavar="ID", help="konkrétny prípad z banky")
    ap.add_argument("--no-post", action="store_true", help="len vyrobí video a popisok (Release ani stav sa nemení)")
    ap.add_argument("--force", action="store_true", help="povolí už použitý prípad (--case) a prepíše existujúci story.json")
    a = ap.parse_args()

    st = state()
    n = st["next_ep"]
    chosen, script = None, None
    if a.case:
        c = case_by_id(a.case)
        if not c:
            sys.exit(f"prípad '{a.case}' nie je v bank/cases.json")
        if c["id"] in st["used"] and not a.force:
            sys.exit(f"prípad '{a.case}' už bol použitý (--force = použiť znova)")
        todo = [c]
    else:
        bs = bank_script(st)
        if bs:
            script, cid = bs
            ep = f"{n:03d}-{cid}"
            (EPISODES / ep).mkdir(parents=True, exist_ok=True)
            shutil.copyfile(script, EPISODES / ep / "story.json")
            print(f"skript z banky: {script.name}")
            chosen = (case_by_id(cid) or {"id": cid}, ep)
            todo = []
        else:
            print("banka skriptov je prázdna - píše free model (fallback)")
            todo = [c for c in bank() if c["id"] not in st["used"]][:MAX_CASES]
            if not todo:
                sys.exit("banka je vyčerpaná - treba doplniť bank/cases.json")

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
    if script:   # pouzity skript z banky -> bank/scripts/used/ (rutina vidi, kolko ostava)
        (SCRIPTS / "used").mkdir(exist_ok=True)
        shutil.move(str(script), str(SCRIPTS / "used" / script.name))
    if c["id"] not in st["used"]:
        st["used"].append(c["id"])
    st["episodes"][str(n)] = {"id": c["id"], "title": title, "posted_at": now().isoformat(timespec="seconds"), "release": tag,
                              "author": "claude-bank" if script else "free-model"}
    st["next_ep"] = n + 1
    save_state(st)
    print(f"HOTOVO: ep {n:03d}")


if __name__ == "__main__":
    main()
