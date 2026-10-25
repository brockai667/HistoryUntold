# -*- coding: utf-8 -*-
"""PriceTrap – zvukové efekty syntetizované z kódu (numpy): bez sťahovania, bez licencií, vždy rovnaké.

Udalosti sa odvodia z úderov episode.json (čo sa v danom údere objaví) a časy sedia s animáciami šablóny:
nová scéna = šuch tesne pred strihom, nová karta = pop (useEnter delay 2), pečiatka = úder (Stamp delay 6,
dopad ~5 snímok), prechod do blueprintu = hlboký „bum“, nový odznak v Compare = cinknutie pokladne, Outro = pečiatka,
veľký text cez obrazovku (insert) = šuch + údar, bodky v Crowd = cvakanie korálok pri každom dopade,
gulička v cenníku = pop pri objavení, šuch pri skoku, pop pri dopade, cinknutie pri „=“.
"""
import numpy as np

SR = 44100
_rng = np.random.default_rng(7)


def _t(dur):
    return np.arange(int(SR * dur)) / SR


def _lowpass(x, a):
    """jednopólový dolný priepust s premenlivým koeficientom a (0..1)"""
    y, acc = np.empty_like(x), 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def _norm(y, peak):
    return peak * y / (np.abs(y).max() + 1e-9)


def whoosh(dur=0.42):
    t = _t(dur)
    s = t / dur
    y = _lowpass(_rng.standard_normal(len(t)), 0.03 + 0.3 * np.sin(np.pi * s) ** 2)
    y -= np.convolve(y, np.ones(48) / 48, "same")      # bez hukotu (horný priepust)
    return _norm(y * np.sin(np.pi * s) ** 1.6, 0.20)


def pop(dur=0.09):
    t = _t(dur)
    f = 1000 * np.exp(-t * 28) + 380
    return _norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 48), 0.30)


def stamp(dur=0.4):
    t = _t(dur)
    f = 150 * np.exp(-t * 20) + 48
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 13)
    slap = np.convolve(_rng.standard_normal(len(t)) * np.exp(-t * 95), np.ones(5) / 5, "same")
    return _norm(0.85 * body + 0.45 * slap, 0.62)


def boom(dur=0.9):
    t = _t(dur)
    f = 62 * np.exp(-t * 3) + 36
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.5) * (1 - np.exp(-t * 90))
    air = _lowpass(_rng.standard_normal(len(t)), np.full(len(t), 0.02)) * np.exp(-t * 6)
    return _norm(body + 0.6 * _norm(air, 1), 0.42)


def ding(dur=0.9):
    t = _t(dur)

    def bell(f0, t0):
        tt = np.clip(t - t0, 0, None)
        on = t >= t0
        return on * sum(a * np.sin(2 * np.pi * f0 * m * tt) * np.exp(-tt * (5 + 2 * m))
                        for m, a in ((1, 1.0), (2.76, 0.35), (5.4, 0.15)))

    cha = _rng.standard_normal(len(t)) * np.exp(-t * 70) * 0.35
    return _norm(0.6 * bell(1318.5, 0.0) + bell(1975.5, 0.085) + cha, 0.26)


def hit(dur=0.22):
    """krátky údar (kopák + klik) pod veľký text cez celú obrazovku"""
    t = _t(dur)
    f = 140 * np.exp(-t * 30) + 52
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16)
    click = _rng.standard_normal(len(t)) * np.exp(-t * 400)
    return _norm(body + 0.25 * click, 0.45)


def tick(f0=2400, dur=0.05):
    """tiché cvaknutie korálky (dopad jednej bodky v Crowd)"""
    t = _t(dur)
    body = np.sin(2 * np.pi * f0 * t) * np.exp(-t * 160)
    click = _rng.standard_normal(len(t)) * np.exp(-t * 900)
    return _norm(body + 0.4 * click, 0.09)


SOUNDS = {"whoosh": whoosh, "pop": pop, "stamp": stamp, "boom": boom, "ding": ding, "hit": hit}
SOUNDS.update({f"tick{k}": (lambda f=f: tick(f)) for k, f in enumerate((2100, 2500, 2900, 3300))})

# časovanie z Crowd.tsx a Scenes.tsx (BALL) v snímkach
CROWD_DELAY, CROWD_SPREAD, CROWD_FLY = 6, 44, 16
CROWD_MOVE_DELAY, CROWD_MOVE_SPREAD, CROWD_MOVE_FLY = 14, 36, 18
BALL_APPEAR, BALL_START, BALL_LAND = 10, 22, 40


def _opts(p):
    return [o for o in (p.get("options") or []) if o and o.get("label")]


def crowd_landings(p, pp, fps=30):
    """časy dopadov bodiek od začiatku úderu (s); pp = props minulého úderu Crowd alebo None"""
    cur = {o["label"]: max(0, round(float(o.get("value") or 0))) for o in _opts(p)}
    if not pp:
        n = sum(cur.values())
        return [(CROWD_DELAY + k * CROWD_SPREAD / max(1, n) + CROWD_FLY) / fps for k in range(n)]
    old = {o["label"]: max(0, round(float(o.get("value") or 0))) for o in _opts(pp)}
    if old == cur:
        return []
    movers = sum(max(0, v - min(v, cur.get(l, 0))) for l, v in old.items())
    targets = sum(max(0, v - old.get(l, 0)) for l, v in cur.items())
    m = max(movers, targets)
    return [(CROWD_MOVE_DELAY + i * CROWD_MOVE_SPREAD / max(1, m) + CROWD_MOVE_FLY) / fps for i in range(targets)]


def _changed(a, b):
    return (a or None) != (b or None)


def events(beats, fps=30):
    """[(druh, čas v s)] z úderov; rovnaké pravidlá ako animácie v Scenes/Blocks."""
    ev = []
    for i, b in enumerate(beats):
        t0, p = b["t0"], b.get("props") or {}
        prev = beats[i - 1] if i else None
        same = prev is not None and prev.get("scene") == b.get("scene")
        pp = (prev.get("props") or {}) if same else {}
        if i and not same:
            ev.append(("whoosh", t0 - 0.16))
        if b.get("mode") == "blueprint" and not (prev and prev.get("mode") == "blueprint"):
            ev.append(("boom", t0))
        sc = b.get("scene")
        if sc == "Hero" and p.get("tag") and _changed(p.get("tag"), pp.get("tag")):
            ev.append(("pop", t0 + 12 / fps))
        if sc == "PriceList":
            cards, pcards = p.get("cards") or [], pp.get("cards") or []
            for k, c in enumerate(cards):
                pc = pcards[k] if k < len(pcards) else None
                if not pc or pc.get("title") != c.get("title"):
                    ev.append(("pop", t0 + 4 / fps))
                if c.get("stamp") and (not pc or pc.get("stamp") != c.get("stamp")):
                    ev.append(("stamp", t0 + 11 / fps))
        if sc == "Compare":
            after, pafter = p.get("after") or [], pp.get("after") or []
            for k, c in enumerate(after):
                pc = pafter[k] if k < len(pafter) else None
                if c and c.get("badge") and _changed(c.get("badge"), (pc or {}).get("badge")):
                    ev.append(("ding", t0 + 14 / fps))
        if sc == "PriceList":
            pt = p.get("point")
            if isinstance(pt, list) and len(pt) == 2 and pt != pp.get("point"):
                ev += [("pop", t0 + BALL_APPEAR / fps), ("whoosh", t0 + BALL_START / fps - 0.06), ("pop", t0 + BALL_LAND / fps)]
                cards = p.get("cards") or []
                if all(0 <= int(k) < len(cards) for k in pt) and cards[int(pt[0])].get("price") == cards[int(pt[1])].get("price"):
                    ev.append(("ding", t0 + (BALL_LAND + 4) / fps))
        if sc == "Crowd":
            pc = pp if same else next((x.get("props") or {} for x in reversed(beats[:i]) if x.get("scene") == "Crowd"), None)
            lands = crowd_landings(p, pc, fps)
            if pc and lands:
                ev.append(("whoosh", t0 + CROWD_MOVE_DELAY / fps - 0.1))
            for k, u in enumerate(lands):
                ev.append((f"tick{k % 4}", t0 + u))
        if sc == "Outro":
            ev.append(("stamp", t0 + 13 / fps))
        if b.get("insert"):
            ti = t0 + b["insert"]["t"]
            ev += [("whoosh", ti - 0.2), ("hit", ti)]
    out = []  # rovnaký zvuk dvakrát do 0,2 s (strih scény + insert hneď na začiatku úderu) = len raz
    for kind, t in sorted(ev, key=lambda e: e[1]):
        if kind.startswith("tick"):  # korálky: najviac jedno cvaknutie za 0,045 s (pri 100 bodkách by sa zliali)
            if not any(k.startswith("tick") and abs(t - u) < 0.045 for k, u in out):
                out.append((kind, t))
            continue
        if not any(k == kind and abs(t - u) < 0.2 for k, u in out):
            out.append((kind, t))
    return out


def stamp_time(b, prev, fps=30):
    """čas dopadu pečiatky od začiatku úderu (pre otras kamery), alebo None"""
    ev = events([prev, b] if prev else [b], fps)
    t0 = b["t0"]
    hits = [t - t0 for k, t in ev if k == "stamp" and t >= t0]
    return round(hits[0], 3) if hits else None


def track(beats, duration):
    """mono stopa efektov dĺžky duration (s)"""
    out = np.zeros(int(duration * SR) + SR)
    cache = {}
    for kind, t in events(beats):
        s = cache.get(kind)
        if s is None:
            s = cache[kind] = SOUNDS[kind]()
        i = max(0, int(t * SR))
        n = min(len(s), len(out) - i)
        if n > 0:
            out[i:i + n] += s[:n]
    return np.clip(out[: int(duration * SR)], -1, 1)
