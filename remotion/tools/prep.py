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

Hlas = edge-tts (zadarmo), jeden mp3 na úder, WordBoundary = časy slov pre titulky.
Dĺžka úderu = dĺžka hlasu + gap; "hold" (sekundy) predĺži úder na aspoň túto dĺžku.
"""
import asyncio, hashlib, json, os, re, shutil, subprocess, sys, time
import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)  # koreň repa (C:\Users\damia\PriceTrap), odtiaľ sa berú relatívne cesty (hudba)
BRAND_FILE = os.path.join(ROOT, "brand.json")
STORY_OVERRIDES = ("voice", "rate", "music", "music_gain", "music_credit")  # len tieto kľúče smie prepísať story
FF = shutil.which("ffmpeg") or "ffmpeg"
SR = 24000


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


def tts(text, voice, rate, cache):
    h = hashlib.md5((voice + rate + text).encode()).hexdigest()[:16]
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


def main():
    spec_path = sys.argv[1]
    spec = json.load(open(spec_path, encoding="utf-8"))
    name = episode_name(spec_path)
    cfg = load_cfg(spec)
    voice, rate = cfg.get("voice", "en-US-GuyNeural"), cfg.get("rate", "+0%")
    gap, tail = spec.get("gap", 0.25), spec.get("tail", 1.5)
    out = os.path.join(ROOT, "public", name); os.makedirs(out, exist_ok=True)
    cache = os.path.join(ROOT, "tts_cache"); os.makedirs(cache, exist_ok=True)

    parts, words, beats, cur = [], [], [], 0.0
    for i, b in enumerate(spec["beats"]):
        b = dict(b)
        b["t0"] = round(cur, 3)
        say = b.get("say", "").strip()
        x = np.zeros(0)
        if say:
            mp3, w = tts(say, voice, rate, cache)
            wav = os.path.join(cache, "tmp.wav")
            subprocess.run([FF, "-y", "-loglevel", "error", "-i", mp3, "-ar", str(SR), "-ac", "1", wav], check=True)
            x, _ = sf.read(wav)
            if x.ndim > 1:
                x = x.mean(axis=1)
            nz = np.nonzero(np.abs(x) > 0.01)[0]  # orež ticho na začiatku a konci
            off = 0.0
            if len(nz):
                a0 = max(0, nz[0] - int(0.03 * SR))
                x = x[a0: nz[-1] + int(0.10 * SR)]
                off = a0 / SR
            for ww in punct(w, say):
                words.append({"w": ww["w"], "s": round(cur + ww["s"] - off, 3),
                              "e": round(cur + min(ww["e"] - off, len(x) / SR), 3), "b": i})
        dur = len(x) / SR + gap
        dur = max(dur, float(b.get("hold", 0)), 0.6)
        parts.append(x); parts.append(np.zeros(int(round(dur * SR)) - len(x)))
        cur += dur
        b["t1"] = round(cur, 3)
        beats.append(b)

    # Outro bez "art" by kreslilo auto -> vezmi ikonu prveho Hero uderu (ikona pripadu)
    hero_art = next((b.get("props", {}).get("art") for b in beats if b.get("scene") == "Hero"), None)
    for b in beats:
        if b.get("scene") == "Outro" and hero_art and not (b.get("props") or {}).get("art"):
            b["props"] = {**(b.get("props") or {}), "art": hero_art}

    sf.write(os.path.join(cache, "voice.wav"), np.concatenate(parts), SR)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", os.path.join(cache, "voice.wav"), "-b:a", "160k",
                    os.path.join(out, "voice.mp3")], check=True)

    brand = cfg.get("brand", "PRICE TRAP")
    ep = {"brand": brand, "header": cfg.get("header") or brand, "case": spec.get("case", ""),
          "source": spec.get("source", ""), "logo": cfg.get("logo", brand), "tagline": cfg.get("tagline", ""),
          "stamp": cfg.get("stamp", ""), "cta": cfg.get("cta", ""), "bait_stamp": cfg.get("bait_stamp", ""),
          "beats": beats, "words": words, "fps": 30, "duration": round(cur + tail, 2), "voice": "voice.mp3"}
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
    print(f"{name}: hlas {cur:.1f}s, {len(beats)} úderov, {len(words)} slov, video {ep['duration']}s -> public/{name}/")


if __name__ == "__main__":
    main()
