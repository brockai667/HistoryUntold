#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PriceTrap – príprava dielu pre Remotion.

    python tools/prep.py story/showoff.json                                  (z priečinka remotion/)
    python remotion/tools/prep.py episodes/001-economist-decoy/story.json    (z koreňa repa)
      -> remotion/public/<názov>/{episode.json, voice.mp3, music.mp3, caption.txt} + public/current.json

Názov dielu = názov priečinka, ak sa súbor volá story.json, inak názov súboru bez .json.
Značka (brand, header, logo, tagline, stamp, cta, bait_stamp, hashtags) a voice, rate, music, music_gain,
music_credit sa zlúčia z remotion/brand.json; story smie prepísať voice, rate, music (aj music_gain, music_credit).
Cesta k hudbe je relatívna ku koreňu repa (rodič priečinka remotion). caption.txt = caption + hashtagy + kredit hudby.

Hlas: voice "orpheus:<hlas>" = Groq Orpheus TTS (zadarmo so zdieľaným Groq kľúčom, 100 požiadaviek/deň, 1 200 tokenov/min),
časy slov z faster-whisper zarovnané na text scenára; keď Groq nejde, celý diel ide hlasom FALLBACK_VOICE (edge-tts).
Inak voice = edge-tts hlas, WordBoundary = časy slov. Jeden zvuk na úder.
Dĺžka úderu = dĺžka hlasu + pauza (pause_after: gap 0,15 s v rámci časti, break 0,6 s pri novej časti príbehu,
hook_break 0,8 s po háku; úder smie mať vlastné "pause"); "hold" (sekundy) predĺži úder na aspoň túto dĺžku.
Navyše: sfx.mp3 (efekty zo sfx.py) a pri úderoch "punch" (druhý zoom kamery) a "shake" (otras pri pečiatke).
"""
import asyncio, difflib, hashlib, json, os, re, shutil, subprocess, sys, time, urllib.error, urllib.request
import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)  # koreň repa (C:\Users\damia\PriceTrap), odtiaľ sa berú relatívne cesty (hudba)
BRAND_FILE = os.path.join(ROOT, "brand.json")
STORY_OVERRIDES = ("voice", "rate", "music", "music_gain", "music_credit")  # len tieto kľúče smie prepísať story
FF = shutil.which("ffmpeg") or "ffmpeg"
SR = 24000
ORPHEUS_URL = "https://api.groq.com/openai/v1/audio/speech"
ORPHEUS_MODEL = "canopylabs/orpheus-v1-english"
FALLBACK_VOICE, FALLBACK_RATE = "en-US-AndrewMultilingualNeural", "+6%"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfx  # noqa: E402
try:  # kľúče z .env (tools/common.py dáva hodnoty len do os.environ, nikdy ich nevypisuje)
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import common  # noqa: F401,E402
except Exception:
    pass


class TTSFatal(RuntimeError):
    """Groq TTS sa nedá použiť (kľúč, denný limit, sieť) -> celý diel záložným hlasom"""


def _orpheus(text, out, voice):
    key = os.environ.get("GROQ_API_KEY") or os.environ.get("MODELS_TOKEN")
    if not key:
        raise TTSFatal("chýba GROQ_API_KEY")
    body = json.dumps({"model": ORPHEUS_MODEL, "voice": voice, "input": text, "response_format": "wav"}).encode()
    for a in range(6):
        req = urllib.request.Request(ORPHEUS_URL, data=body, headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "PriceTrap/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                open(out, "wb").write(r.read())
            return
        except urllib.error.HTTPError as e:
            msg = e.read()[:300].decode("utf-8", "replace")
            if e.code == 429 and "per day" not in msg.lower() and a < 5:   # minútové okno -> počkaj
                wait = min(60.0, float(e.headers.get("retry-after") or 10))
                print(f"orpheus 429, čakám {wait:.0f} s"); time.sleep(wait + 1)
                continue
            raise TTSFatal(f"Groq TTS HTTP {e.code}: {msg}")
        except (urllib.error.URLError, TimeoutError) as e:
            if a < 5:
                time.sleep(4 + 4 * a); continue
            raise TTSFatal(f"Groq TTS sieť: {e}")


_WHISPER = None


def _heard(wav):
    """časy slov z faster-whisper (base.en, CPU)"""
    global _WHISPER
    if _WHISPER is None:
        from faster_whisper import WhisperModel
        _WHISPER = WhisperModel("base.en", device="cpu", compute_type="int8")
    segs, _ = _WHISPER.transcribe(wav, language="en", word_timestamps=True, beam_size=5)
    return [{"w": w.word.strip(), "s": w.start, "e": w.end} for s in segs for w in (s.words or [])]


def align(text, heard, dur):
    """slová scenára s časmi z prepisu; slovo, ktoré whisper počul inak, dostane čas medzi susedmi (podľa dĺžky)"""
    toks = text.split()
    norm = lambda s: re.sub(r"[^\w]", "", s).lower()
    sm = difflib.SequenceMatcher(None, [norm(t) for t in toks], [norm(w["w"]) for w in heard], autojunk=False)
    tm = [None] * len(toks)
    for i, j, n in sm.get_matching_blocks():
        for k in range(n):
            tm[i + k] = (heard[j + k]["s"], heard[j + k]["e"])
    i = 0
    while i < len(toks):
        if tm[i]:
            i += 1; continue
        j = i
        while j < len(toks) and not tm[j]:
            j += 1
        a = tm[i - 1][1] if i else (heard[0]["s"] if heard else 0.0)
        b = tm[j][0] if j < len(toks) else (heard[-1]["e"] if heard else dur)
        b = max(a, b)
        lens = [len(t) + 1 for t in toks[i:j]]
        s = a
        for k, ln in zip(range(i, j), lens):
            e = s + (b - a) * ln / sum(lens)
            tm[k] = (s, e); s = e
        i = j
    return [{"w": t, "s": round(s, 3), "e": round(e, 3)} for t, (s, e) in zip(toks, tm)]


async def _edge(text, out, voice, rate):
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words = []
    with open(out, "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                words.append({"w": ch["text"], "s": ch["offset"] / 1e7, "e": (ch["offset"] + ch["duration"]) / 1e7})
    return words


def punct(words, text):
    """edge-tts vracia slová bez interpunkcie a so zmenenými číslami; vráť im pôvodný tvar z textu."""
    split = []  # edge-tts občas spojí "$250,000 reservation" do jednej hranice -> rozdeľ podľa dĺžky
    for w in words:
        parts = w["w"].split()
        if len(parts) < 2:
            split.append(w); continue
        tot, s = sum(len(p) for p in parts), w["s"]
        for p in parts:
            e = s + (w["e"] - w["s"]) * len(p) / tot
            split.append({"w": p, "s": s, "e": e}); s = e
    words = split
    toks = text.split()
    norm = lambda s: re.sub(r"[^\w']", "", s).lower()
    j = 0
    for w in words:
        nw = norm(w["w"])
        for k in range(j, min(j + 3, len(toks))):
            nt = norm(toks[k])
            if nt == nw or (nw and nt.startswith(nw)):
                w["w"] = toks[k]; j = k + 1; break
    return words


DIRECTION = re.compile(r"\s*\[[^\]]{1,40}\]\s*")


def spoken(text):
    """text bez hlasových pokynov Orphea ([dramatic] ...) = to, čo sa naozaj vysloví (titulky, zarovnanie)"""
    return DIRECTION.sub(" ", text).strip()


def direct(beats):
    """Hlasové pokyny pre Orpheus: len zvrat (vstup do blueprintu) dostane [dramatic] – hlas klesne nižšie a odlíši ho.
    Meranie 20. 10.: [intrigued] / [building suspense] spomalili hák o 40–100 % bez väčšieho rozptylu výšky,
    [deadpan] nezmenil nič. Pokyny stoja tokeny z denného limitu (3 600/deň), preto len tam, kde niečo robia."""
    out = []
    for i, b in enumerate(beats):
        say, prev = b.get("say", "").strip(), beats[i - 1] if i else {}
        twist = b.get("mode") == "blueprint" and prev.get("mode") != "blueprint"
        line = f"[dramatic] {say}" if twist and say else say
        out.append(line if len(line) <= 200 else say)  # Orpheus berie najviac 200 znakov
    return out


def tts(text, voice, rate, cache):
    """-> (zvukový súbor, slová s časmi); výsledok sa ukladá do cache podľa hlasu a textu.
    Orpheus dostane text aj s pokynmi v [ ], časy slov sa zarovnajú len na vyslovený text."""
    h = hashlib.md5((voice + rate + text).encode()).hexdigest()[:16]
    if voice.startswith("orpheus:"):
        wav, js = os.path.join(cache, h + ".wav"), os.path.join(cache, h + ".json")
        if not os.path.exists(js):
            _orpheus(text, wav, voice.split(":", 1)[1])
            if os.path.getsize(wav) < 2000:
                raise TTSFatal("Groq TTS: prázdny výstup")
            json.dump(align(spoken(text), _heard(wav), sf.info(wav).duration), open(js, "w", encoding="utf-8"))
        return wav, json.load(open(js, encoding="utf-8"))
    text = spoken(text)
    mp3, js = os.path.join(cache, h + ".mp3"), os.path.join(cache, h + ".json")
    if not os.path.exists(js):
        for a in range(4):
            try:
                w = asyncio.run(_edge(text, mp3, voice, rate))
                if not w or os.path.getsize(mp3) < 2000:
                    raise RuntimeError("prázdny výstup")
                json.dump(w, open(js, "w", encoding="utf-8"))
                break
            except Exception as e:
                print("tts retry", e); time.sleep(4 + 4 * a)
        else:
            sys.exit("TTS zlyhalo (edge-tts potrebuje internet)")
    return mp3, json.load(open(js, encoding="utf-8"))


def episode_name(spec_path):
    """Názov dielu = názov priečinka, ak sa súbor volá story.json, inak názov súboru bez prípony."""
    ap = os.path.abspath(spec_path)
    if os.path.basename(ap).lower() == "story.json":
        return os.path.basename(os.path.dirname(ap))
    return os.path.splitext(os.path.basename(ap))[0]


def load_cfg(spec):
    """brand.json + povolené prepisy zo story (voice, rate, music, ...)."""
    cfg = {}
    if os.path.exists(BRAND_FILE):
        cfg = json.load(open(BRAND_FILE, encoding="utf-8"))
    for k in STORY_OVERRIDES:
        if k in spec:
            cfg[k] = spec[k]
    return cfg


def squeeze(x, ws, max_pause=0.22, sent_pause=0.38, colon_pause=0.3):
    """Vnútorné pauzy v reči: za koncom vety (. ? !) presne sent_pause (kratšiu predĺži, aby sa vety neliali do seba),
    za dvojbodkou colon_pause, inde najviac max_pause (Orpheus pri čiarkach čaká aj 1 s). Posunie časy slov."""
    win = int(0.01 * SR)
    loud = [np.abs(x[k * win:(k + 1) * win]).max() > 0.01 for k in range(len(x) // win)]
    gaps, k, n = [], 0, len(loud)
    while k < n:
        if loud[k]:
            k += 1; continue
        j = k
        while j < n and not loud[j]:
            j += 1
        if 0 < k and j < n:   # len vnútorné pauzy
            gaps.append((k * win, j * win))
        k = j
    target = {}   # medzi vetami len najdlhšia tichá medzera v rozpätí dvoch slov (nie mikroticho vnútri slova)
    for a, b in zip(ws, ws[1:]):
        end = a["w"].rstrip("\"')")[-1:]
        if end not in ".?!:":
            continue
        cand = [m for m, (g0, g1) in enumerate(gaps) if a["s"] * SR <= g0 and g1 <= b["e"] * SR]
        if cand:
            target[max(cand, key=lambda m: gaps[m][1] - gaps[m][0])] = colon_pause if end == ":" else sent_pause
    edits = []   # (od, do, vložené ticho): x[od:do] sa vyreže a vloží sa toľko núl
    for m, (g0, g1) in enumerate(gaps):
        d = (g1 - g0) / SR
        want = target.get(m, min(d, max_pause))
        if want < d - 0.01:
            half = int(want / 2 * SR)
            edits.append((g0 + half, g1 - half, 0))
        elif want > d + 0.01:
            mid = (g0 + g1) // 2
            edits.append((mid, mid, int((want - d) * SR)))
    if not edits:
        return x, ws
    keep, last = [], 0
    for c0, c1, add in edits:
        keep.append(x[last:c0]); keep.append(np.zeros(add)); last = c1
    keep.append(x[last:])

    def shift(t):
        s = int(t * SR); out = s
        for c0, c1, add in edits:
            if s >= c1:
                out += add - (c1 - c0)
            elif s > c0:
                out -= s - c0
        return out / SR

    return np.concatenate(keep), [{**w, "s": shift(w["s"]), "e": shift(w["e"])} for w in ws]


def pause_after(beats, i, gap, brk, hook):
    """Ticho po hlase úderu: "pause" v údere vyhrá; po háku (Hero) hook; pri zmene scény alebo režimu a po Statement
    brk (nová časť príbehu – divák si to stihne spracovať); medzi údermi tej istej scény len gap."""
    b = beats[i]
    if "pause" in b:
        return float(b["pause"])
    if i + 1 >= len(beats):
        return gap
    nxt = beats[i + 1]
    if b.get("scene") == "Hero":
        return hook
    if b.get("scene") == "Statement" or b.get("scene") != nxt.get("scene") or b.get("mode") != nxt.get("mode"):
        return brk
    return gap


def punch_at(bw, t0, t1):
    """druhý zoom v úderi (s od začiatku): prvé slovo novej vety, inak slovo v strede; krátke údery bez neho"""
    if t1 - t0 < 2.6 or len(bw) < 4:
        return None
    for a, b in zip(bw, bw[1:]):
        if a["w"][-1:] in ".!?" and b["s"] - t0 > 0.9 and t1 - b["s"] > 0.9:
            return round(b["s"] - t0, 3)
    mid = (t0 + t1) / 2
    return round(min(bw[1:-1], key=lambda w: abs(w["s"] - mid))["s"] - t0, 3)


def shots_at(bw, t0, t1):
    """Časy strihov záberu v údere (s od začiatku; kamera strieda detail a celok, Episode.tsx).
    Strih na začiatku slova po konci vety, inak po čiarke, inak slovo najbližšie k +2,1 s; záber 1,3–2,6 s,
    posledný záber aspoň 0,9 s."""
    end = t1 - t0
    pairs = [(a["w"][-1:], b["s"] - t0) for a, b in zip(bw, bw[1:])]
    cuts, last = [], 0.0
    while True:
        win = lambda c: last + 1.3 <= c <= last + 2.6 and end - c >= 0.9
        sent = [c for p, c in pairs if p in ".!?" and win(c)]
        comma = [c for p, c in pairs if p in ",;:" and win(c)]
        near = [c for _, c in pairs if last + 1.6 <= c <= last + 2.6 and end - c >= 0.9]
        if sent or comma:
            c = (sent or comma)[0]
        elif near:
            c = min(near, key=lambda c: abs(c - last - 2.1))
        else:
            break
        cuts.append(round(c, 3)); last = c
    return cuts


def insert_at(b, bw, i, prev):
    """Veľký text cez celú obrazovku (strih preč zo scény na ~1 s), keď hlas povie krátku pointu:
    posledná krátka veta (≤ 3 slová, „Looks useless.“), krátka posledná časť za čiarkou bez čísel („no web“),
    alebo krátka úvodná veta (≤ 4 slová, „You see it everywhere.“). Nie v háku, Statement (sám je veľký text),
    závere ani pri pečiatke (tá je hviezda úderu). V Crowd a pri guličke (PriceList point) až po dobehnutí animácie,
    inak by text zakryl práve to, čo vysvetľuje (Crowd nikdy: pointu ukáže kamera na nádobe). -> {"text", "t" (s od začiatku úderu), "d"} alebo None"""
    if i == 0 or b.get("scene") in ("Hero", "Statement", "Outro") or len(bw) < 4:
        return None
    if b.get("mode") == "blueprint" and (prev or {}).get("mode") != "blueprint":
        return None
    ends = [k for k, w in enumerate(bw) if w["w"][-1:] in ".!?"]
    sents, s0 = [], 0
    for k in ends:
        sents.append((s0, k)); s0 = k + 1
    if s0 < len(bw):
        sents.append((s0, len(bw) - 1))
    cands = []
    if len(sents) > 1 and sents[-1][1] - sents[-1][0] < 3:
        cands.append(sents[-1])
    a, z = sents[-1]
    commas = [k for k in range(a, z) if bw[k]["w"].endswith(",")]
    if commas and z - commas[-1] <= 3 and not any(re.search(r"\d", bw[k]["w"]) for k in range(commas[-1] + 1, z + 1)):
        cands.append((commas[-1] + 1, z))
    if len(sents) > 1 and sents[0][1] - sents[0][0] < 4:
        cands.append(sents[0])
    busy = 99.0 if b.get("scene") == "Crowd" else 1.9 if (b.get("props") or {}).get("point") else 0.0
    cands = [c for c in cands if bw[c[0]]["s"] - b["t0"] >= busy]
    if b.get("scene") == "PriceList":   # „Web-only: $59.“ = to isté, čo ukazuje karta; text by ju len zakryl
        cands = [c for c in cands if not any(re.search(r"\d", bw[k]["w"]) for k in range(c[0], c[1] + 1))]
    if not cands:
        return None
    a, z = cands[0]
    t = max(0.0, bw[a]["s"] - b["t0"] - 0.04)
    d = min(max(0.75, bw[z]["e"] - bw[a]["s"] + 0.35), b["t1"] - b["t0"] - t)
    text = " ".join(w["w"] for w in bw[a:z + 1]).rstrip(",;:")
    return {"text": text, "t": round(t, 3), "d": round(d, 3)} if d >= 0.5 else None


def build(spec, voice, rate, pauses, cache):
    # Orpheus nemá parameter rýchlosti -> rate ("+12%") sa použije ako ffmpeg atempo (výška hlasu ostane)
    orpheus = voice.startswith("orpheus:")
    m = re.fullmatch(r"([+-]\d+)%", rate.strip()) if orpheus else None
    tempo = 1 + int(m.group(1)) / 100 if m else 1.0
    parts, words, beats, cur = [], [], [], 0.0
    lines = direct(spec["beats"]) if orpheus else [b.get("say", "") for b in spec["beats"]]
    for i, b in enumerate(spec["beats"]):
        b = dict(b)
        b["t0"] = round(cur, 3)
        say = b.get("say", "").strip()
        x = np.zeros(0)
        if say:
            mp3, w = tts(lines[i], voice, "+0%" if orpheus else rate, cache)
            wav = os.path.join(cache, "tmp.wav")
            af = ["-af", f"atempo={tempo:.3f}"] if tempo != 1 else []
            subprocess.run([FF, "-y", "-loglevel", "error", "-i", mp3, *af, "-ar", str(SR), "-ac", "1", wav], check=True)
            x, _ = sf.read(wav)
            if x.ndim > 1:
                x = x.mean(axis=1)
            nz = np.nonzero(np.abs(x) > 0.01)[0]  # orež ticho na začiatku a konci
            off = 0.0
            if len(nz):
                a0 = max(0, nz[0] - int(0.03 * SR))
                x = x[a0: nz[-1] + int(0.10 * SR)]
                off = a0 / SR
            ws = [{**ww, "s": ww["s"] / tempo - off, "e": ww["e"] / tempo - off} for ww in punct(w, say)]
            x, ws = squeeze(x, ws)
            end = len(x) / SR
            for ww in ws:  # whisper dáva prvému slovu začiatok aj pred zvukom -> orež do úderu
                s = min(max(0.0, ww["s"]), end)
                words.append({"w": ww["w"], "s": round(cur + s, 3), "e": round(cur + min(max(ww["e"], s), end), 3), "b": i})
        dur = len(x) / SR + pause_after(spec["beats"], i, *pauses)
        dur = max(dur, float(b.get("hold", 0)), 0.6)
        parts.append(x); parts.append(np.zeros(int(round(dur * SR)) - len(x)))
        cur += dur
        b["t1"] = round(cur, 3)
        bw = [w for w in words if w["b"] == i]
        p = punch_at(bw, b["t0"], b["t1"])
        if p is not None:
            b["punch"] = p
        b["shots"] = shots_at(bw, b["t0"], b["t1"])
        ins = insert_at(b, bw, i, beats[-1] if beats else None)
        if ins:
            b["insert"] = ins
        beats.append(b)
    return parts, words, beats, cur


def main():
    spec_path = sys.argv[1]
    spec = json.load(open(spec_path, encoding="utf-8"))
    name = episode_name(spec_path)
    cfg = load_cfg(spec)
    voice, rate = cfg.get("voice", "en-US-GuyNeural"), cfg.get("rate", "+0%")
    pauses = (spec.get("gap", 0.15), spec.get("break", 0.6), spec.get("hook_break", 0.8))
    tail = spec.get("tail", 1.5)
    out = os.path.join(ROOT, "public", name); os.makedirs(out, exist_ok=True)
    cache = os.path.join(ROOT, "tts_cache"); os.makedirs(cache, exist_ok=True)

    try:
        parts, words, beats, cur = build(spec, voice, rate, pauses, cache)
    except TTSFatal as e:
        print(f"VAROVANIE: {e} -> celý diel hlasom {FALLBACK_VOICE}")
        voice, rate = FALLBACK_VOICE, FALLBACK_RATE
        parts, words, beats, cur = build(spec, voice, rate, pauses, cache)
    for i, b in enumerate(beats):
        s = sfx.stamp_time(b, beats[i - 1] if i else None)
        if s is not None:
            b["shake"] = s

    # Outro bez "art" by kreslilo auto -> vezmi ikonu prveho Hero uderu (ikona pripadu)
    hero_art = next((b.get("props", {}).get("art") for b in beats if b.get("scene") == "Hero"), None)
    for b in beats:
        if b.get("scene") == "Outro" and hero_art and not (b.get("props") or {}).get("art"):
            b["props"] = {**(b.get("props") or {}), "art": hero_art}

    sf.write(os.path.join(cache, "voice.wav"), np.concatenate(parts), SR)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", os.path.join(cache, "voice.wav"), "-b:a", "160k",
                    os.path.join(out, "voice.mp3")], check=True)

    brand = cfg.get("brand", "PLAIN SIGHT")
    ep = {"brand": brand, "header": cfg.get("header") or brand, "case": spec.get("case", ""),
          "source": spec.get("source", ""), "logo": cfg.get("logo", brand), "tagline": cfg.get("tagline", ""),
          "stamp": cfg.get("stamp", ""), "cta": cfg.get("cta", ""), "bait_stamp": cfg.get("bait_stamp", ""),
          "beats": beats, "words": words, "fps": 30, "duration": round(cur + tail, 2), "voice": "voice.mp3"}
    sf.write(os.path.join(cache, "sfx.wav"), sfx.track(beats, cur + tail), sfx.SR)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", os.path.join(cache, "sfx.wav"), "-b:a", "128k",
                    os.path.join(out, "sfx.mp3")], check=True)
    ep["sfx"] = "sfx.mp3"
    music_used = False
    if cfg.get("music"):
        music_src = os.path.join(REPO, cfg["music"])  # relatívna cesta = od koreňa repa
        if os.path.isfile(music_src):
            shutil.copy(music_src, os.path.join(out, "music.mp3"))
            ep.update({"music": "music.mp3", "music_gain": cfg.get("music_gain", 0.12)})
            music_used = True
        else:
            print(f"VAROVANIE: hudba {cfg['music']} sa nenašla ({music_src}), diel bude bez hudby")
    # popisok: caption + prázdny riadok + hashtagy + prázdny riadok + kredit hudby (kredit len keď hudba hrá)
    parts = [str(spec.get("caption", "")).strip(), str(cfg.get("hashtags", "")).strip()]
    if music_used:
        parts.append(str(cfg.get("music_credit", "")).strip())
    caption = "\n\n".join(p for p in parts if p)
    json.dump(ep, open(os.path.join(out, "episode.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    if caption:
        open(os.path.join(out, "caption.txt"), "w", encoding="utf-8").write(caption + "\n")
    json.dump({"ep": name}, open(os.path.join(ROOT, "public", "current.json"), "w", encoding="utf-8"))
    print(f"{name}: hlas {voice} {cur:.1f}s, {len(beats)} úderov, {len(words)} slov, video {ep['duration']}s -> public/{name}/")


if __name__ == "__main__":
    main()
