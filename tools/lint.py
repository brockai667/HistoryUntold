# -*- coding: utf-8 -*-
"""Mechanicka kontrola story JSON podla SPEC.md (sekcia Lint). Pouziva ju autor (write_case.py) aj v opravnom kole.
    python tools/lint.py episodes/001-economist-decoy/story.json [--case-file pripad.json]
lint(story, case, icons) -> zoznam retazcov typu "beat 4 PriceList: card 2 title too long (23 > 18)"; prazdny = OK.
Rovnaka chyba vo viacerych uderoch sa spoji do jednej ("beats 5,6 PriceList: ..."). CLI: vypise chyby, exit 1 ak su."""
import argparse
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import REMOTION, case_by_id, case_from_file, load  # noqa: E402

SCENES = ("Hero", "PriceList", "Views", "Anchor", "Compare", "Statement", "Outro", "Crowd")
TONES = ("plain", "dark", "blue", "yellow", "red", "green")
SPECIAL_ICONS = ("car", "car-red", "car-fly", "none")
TOP_KEYS = {"id", "case", "title", "caption", "source", "beats"}
BEAT_KEYS = {"say", "scene", "props", "mode", "hold"}
CARD_KEYS = {"title", "sub", "price", "priceRed", "tags", "art", "stamp", "badge", "top"}
SCENE_KEYS = {
    "Hero": {"art", "tag", "title", "sub"},
    "PriceList": {"slots", "cards", "point"},
    "Views": {"job", "label", "value", "from", "prefix", "suffix", "grid", "thumbLabel", "art"},
    "Anchor": {"job", "price", "at", "split", "art", "anchor"},
    "Compare": {"before", "after", "labels"},
    "Statement": {"kicker", "text", "tags"},
    "Outro": {"art"},
    "Crowd": {"job", "options", "total"},
}
NUM_FREE_KEYS = {"slots", "grid", "at", "split", "from", "hold", "point", "total"}   # cisla v tychto props sa nekontroluju
BRANDS = ["Apple", "Starbucks", "Netflix", "Amazon", "Nike", "Tesla", "McDonald's", "Costco", "IKEA", "Gillette", "Disney",
          "Uber", "Spotify", "Rolex", "Hermès", "Supreme", "Google", "Microsoft", "Samsung"]
# "bezne slova": velke pismeno uprostred vety, ktore nie je meno (skratky, mesiace, dni, sviatky)
COMMON = set("""i ok okay tv vip ai ceo diy atm gps usb suv pc id wifi wi-fi mr mrs ms dr
january february march april may june july august september october november december
monday tuesday wednesday thursday friday saturday sunday christmas easter halloween thanksgiving""".split())
STOP = {"the", "and", "of", "for", "inc", "co", "ltd", "corp", "company"}

_NUM = re.compile(r"(?<![\w.])\$?\d[\d,]*(?:\.\d+)?%?(?!\w)")
_TOK = re.compile(r"[A-Za-zÀ-ɏ][A-Za-zÀ-ɏ'\-]*")
_EMOJI = re.compile("[\U0001F000-\U0001FAFF←-⇿⌀-⏿■-➿⤀-⥿⬀-⯿️‍⃣]")
_CURLY = re.compile("[‘’‚‛“”„«»′″]")
_MD = re.compile(r"[*#`_~\[\]<>|]|^\s*(?:[-+>]\s|\d+[.)]\s)", re.M)


# ---------- pomocne ----------
def _fold(s):
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(ch for ch in s if not unicodedata.combining(ch)).lower().replace("’", "'")


def _stem(w):
    w = _fold(w).strip("-'")
    return w[:-2] if w.endswith("'s") else w


BRAND_STEMS = {_stem(b) for b in BRANDS}


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def nums(text):
    """Cisla v texte, normalizovane (bez $ , % a medzier): "$1,500" -> "1500"."""
    return [re.sub(r"[$,%\s]", "", t) for t in _NUM.findall(str(text))]


def _diffs(pn):
    """rozdiely cien na kartách Compare („only 50 cents more“, „$3 more“) ako normalizované čísla"""
    vals = sorted({float(x) for x in pn if re.fullmatch(r"\d+(?:\.\d+)?", x)})
    out = set()
    for i, a in enumerate(vals):
        for b in vals[i + 1:]:
            d = round(b - a, 2)
            out |= {f"{d:g}", f"{d:.2f}"} | ({str(round(d * 100))} if d < 1 else set())
    return out


def _exempt(n):
    return n in ("0", "1", "2", "3")


def _prop_numbers(v):
    """Cisla v props (retazce aj ciselne hodnoty) okrem `NUM_FREE_KEYS`, ikon a tonov."""
    out = []
    if isinstance(v, dict):
        for k, x in v.items():
            if k not in ("art", "tone") and k not in NUM_FREE_KEYS:
                out += _prop_numbers(x)
    elif isinstance(v, list):
        for x in v:
            out += _prop_numbers(x)
    elif isinstance(v, bool) or v is None:
        pass
    elif isinstance(v, (int, float)):
        out.append(str(int(v)) if float(v).is_integer() else str(v))
    elif isinstance(v, str):
        out += nums(v)
    return out


def _strings(v):
    """Vsetky textove hodnoty v props (bez ikon a tonov)."""
    out = []
    if isinstance(v, dict):
        for k, x in v.items():
            if k not in ("art", "tone"):
                out += _strings(x)
    elif isinstance(v, list):
        for x in v:
            out += _strings(x)
    elif isinstance(v, str):
        out.append(v)
    return out


def _fact_nums(case):
    return {n for f in (case.get("facts") or []) for n in nums(f)}


def _allowed_caps(case, story=None):
    """Velke slova povolene uprostred vety: `names` prilezitosti + bezne slova + vsetky slova z dat pripadu
    (fakty, predmet, zdroj, trik, poucenie) + slova z props pribehu (nazvy kariet, tagy). Vymyslene vlastne mena
    (ludia, firmy, miesta) sa nikde z toho nevyskytuju, preto ich kontrola stale zachyti."""
    ok = set(COMMON)
    for n in case.get("names") or []:
        ok |= {_stem(w) for w in re.findall(r"[\w'’\-]+", str(n))}
    for key in ("facts", "subject", "source", "trick", "lesson", "case"):
        v = case.get(key)
        for s in (v if isinstance(v, list) else [v]):
            ok |= {_stem(w) for w in _TOK.findall(str(s or ""))}
    for b in (story or {}).get("beats") or []:
        if isinstance(b, dict) and isinstance(b.get("props"), dict):
            ok |= {_stem(w) for s in _strings(b["props"]) for w in _TOK.findall(str(s))}
    return ok


def _cap_words(text):
    """Slova s velkym pismenom, ktore NIE su na zaciatku vety (citovane useky sa preskakuju)."""
    t = re.sub(r'"([^"]*)"', lambda m: " . " if re.search(r"[.!?]\s*$", m.group(1)) else " _ ", text)
    t = re.sub(r"(?<![A-Za-z])'([^'\n]*)'(?![A-Za-z])", lambda m: " . " if re.search(r"[.!?]\s*$", m.group(1)) else " _ ", t)
    out = []
    for m in _TOK.finditer(t):
        w = m.group(0).strip("-'")
        if len(w) < 2 or not w[0].isupper():
            continue
        before = t[:m.start()].rstrip()
        if not before or before[-1] in ".!?:":
            continue
        out.append(w)
    return out


def _unknown_names(say, allowed):
    out = []
    for w in _cap_words(say):
        s = _stem(w)
        if s in allowed or ("-" in s and all(p in allowed for p in s.split("-") if p)):
            continue
        out.append(w)
    return list(dict.fromkeys(out))


def _compare_hits(texts, case):
    """Znacky z blacklistu a mena prilezitosti v texte scény Compare."""
    phrase, words = [], []
    for text in texts:
        toks = _TOK.findall(text)
        for t in toks:
            t = t.strip("-'")
            if t[:1].isupper() and _stem(t) in BRAND_STEMS:
                phrase.append(t)
        for name in case.get("names") or []:
            n = str(name).strip()
            if n and re.search(r"(?<![\w])" + re.escape(n) + r"(?![\w])", text, re.I):
                phrase.append(n)
            for w in re.findall(r"[A-Za-zÀ-ɏ][\w'’\-]*", n):
                ws = _stem(w)
                if len(ws) >= 4 and ws not in STOP and ws not in COMMON \
                        and any(_stem(t) == ws and t[:1].isupper() for t in toks):
                    words.append(w)
    phrase = list(dict.fromkeys(phrase))
    inside = " ".join(p.lower() for p in phrase)
    return phrase + [w for w in dict.fromkeys(words) if w.lower() not in inside]


class _Errs:
    """Zbiera chyby; rovnaka chyba vo viacerych uderoch sa spoji do jednej."""

    def __init__(self):
        self.items = []

    def beat(self, no, scene, msg):
        self.items.append((no, scene, msg))

    def top(self, msg):
        self.items.append((None, None, msg))

    def result(self):
        order, groups = [], {}
        for no, scene, msg in self.items:
            key = (scene, msg)
            if key not in groups:
                groups[key] = []
                order.append(key)
            if no is not None and no not in groups[key]:
                groups[key].append(no)
        out = []
        for scene, msg in order:
            nos = groups[(scene, msg)]
            if scene is None:
                out.append(msg)
            elif len(nos) == 1:
                out.append(f"beat {nos[0]} {scene}: {msg}")
            else:
                out.append(f"beats {','.join(map(str, nos))} {scene}: {msg}")
        return out


# ---------- ikony ----------
def read_icon_names():
    """Zoznam ikon z remotion/icons.json (pole alebo objekt) alebo None, ak subor este neexistuje."""
    try:
        data = load(REMOTION / "icons.json")
    except (OSError, ValueError):
        return None
    if isinstance(data, dict):
        data = data.get("icons", data)
    names = [str(x) for x in data]
    return names + [x for x in SPECIAL_ICONS if x not in names]


def load_icons(warn=True):
    """Mnozina platnych `art`; None = subor chyba, `art` sa potom nekontroluje (varovanie na stderr)."""
    names = read_icon_names()
    if names is None and warn:
        print("lint: remotion/icons.json este neexistuje - 'art' sa nekontroluje", file=sys.stderr)
    return set(names) if names is not None else None


# ---------- kontroly poli ----------
def _text(err, where, v, maxlen, required=False):
    if v is None:
        if required:
            err(f"{where} is missing")
        return None
    if not isinstance(v, str):
        err(f"{where} must be a string")
        return None
    if required and not v.strip():
        err(f"{where} is empty")
        return None
    if maxlen and len(v) > maxlen:
        err(f"{where} too long ({len(v)} > {maxlen})")
    return v


def _tag(err, where, tag, maxlen):
    """TagT = retazec alebo {"text","tone"}; vrati (text, tone)."""
    if isinstance(tag, str):
        text, tone = tag, None
    elif isinstance(tag, dict):
        for k in tag:
            if k not in ("text", "tone"):
                err(f"{where}: unknown key '{k}'")
        text, tone = tag.get("text"), tag.get("tone")
        if tone is not None and tone not in TONES:
            err(f"{where} tone '{tone}' is not one of {'/'.join(TONES)}")
    else:
        err(f'{where} must be a string or {{"text", "tone"}}')
        return None, None
    if not isinstance(text, str) or not text.strip():
        err(f"{where} text is missing")
        return None, tone
    if len(text) > maxlen:
        err(f"{where} too long ({len(text)} > {maxlen})")
    return text, tone


def _art(err, where, v, icons, required=False):
    if v is None:
        if required:
            err(f"{where} is missing (use an icon name)")
        return
    if not isinstance(v, str):
        err(f"{where} must be an icon name")
        return
    if icons is None:
        return
    if v not in icons and (not v.endswith("-red") or v[:-4] not in icons):
        err(f"{where} '{v}' is not an available icon")


def _card(err, where, c, icons, tmax, pmax, art_required):
    if not isinstance(c, dict):
        err(f"{where} must be an object")
        return
    for k in c:
        if k not in CARD_KEYS:
            err(f"{where}: unknown key '{k}'")
    _text(err, f"{where} title", c.get("title"), tmax, required=True)
    _text(err, f"{where} sub", c.get("sub"), 22)
    _text(err, f"{where} price", c.get("price"), pmax)
    if "priceRed" in c and not isinstance(c["priceRed"], bool):
        err(f"{where} priceRed must be true or false")
    tags = c.get("tags")
    if tags is not None:
        if not isinstance(tags, list):
            err(f"{where} tags must be a list")
        else:
            if len(tags) > 3:
                err(f"{where} has {len(tags)} tags (max 3)")
            for j, t in enumerate(tags, 1):
                _tag(err, f"{where} tag {j}", t, 16)
    if c.get("badge") is not None:
        text, tone = _tag(err, f"{where} badge", c["badge"], 14)
        if text and text.strip().upper() == "SMART CHOICE" and tone != "green":
            err(f"{where} badge SMART CHOICE must have tone green")
    if c.get("top") is not None:
        _tag(err, f"{where} top", c["top"], 10)
    _text(err, f"{where} stamp", c.get("stamp"), 8)
    _art(err, f"{where} art", c.get("art"), icons, art_required)


def _is_red(c):
    """Karta s cervenou: priceRed, tone red (tag/badge/top) alebo stamp."""
    if not isinstance(c, dict):
        return False
    if c.get("priceRed") is True or (isinstance(c.get("stamp"), str) and c["stamp"].strip()):
        return True
    tags = c.get("tags") if isinstance(c.get("tags"), list) else []
    return any(isinstance(t, dict) and t.get("tone") == "red" for t in tags + [c.get("badge"), c.get("top")])


# ---------- scény ----------
def _hero(err, p, icons):
    _art(err, "art", p.get("art"), icons, required=True)
    if p.get("tag") is not None:
        _tag(err, "tag", p["tag"], 16)
    _text(err, "title", p.get("title"), 16)
    _text(err, "sub", p.get("sub"), 28)   # sablona dlhsi text zmensi (fit.ts)


def _pricelist(err, p, icons):
    cards, slots = p.get("cards"), p.get("slots")
    if not isinstance(cards, list) or not 1 <= len(cards) <= 3:
        err("cards must be a list of 1-3 cards")
        cards = cards if isinstance(cards, list) else []
    if slots is not None:
        if not _is_int(slots) or not 2 <= slots <= 3:
            err(f"slots must be 2 or 3 (got {slots!r})")
        elif slots < len(cards):
            err(f"slots ({slots}) is less than the number of cards ({len(cards)})")
    for i, c in enumerate(cards, 1):
        _card(err, f"card {i}", c, icons, 18, 12, True)
    pt = p.get("point")
    if pt is not None:
        if not (isinstance(pt, list) and len(pt) == 2 and all(_is_int(k) for k in pt) and pt[0] != pt[1]):
            err("point must be two different card indexes, e.g. [1, 2]")
        elif not all(0 <= k < len(cards) and isinstance(cards[k], dict) and cards[k].get("price") for k in pt):
            err(f"point {pt} must name two cards that have a price (indexes from 0)")


def _crowd(err, p, icons):
    """bodky = ludia v nadobach moznosti (Crowd.tsx): 2-3 moznosti, hodnoty = pocty z faktov"""
    if p.get("job") is not None:
        _tag(err, "job", p["job"], 28)
    total = p.get("total", 100)
    if not _is_int(total) or not 10 <= total <= 100:
        err(f"total must be a whole number 10-100 (got {total!r})")
        total = 100
    opts = p.get("options")
    if not isinstance(opts, list) or not 2 <= len(opts) <= 3:
        err("options must be a list of 2-3 options")
        return
    labels = []
    for i, o in enumerate(opts, 1):
        if not isinstance(o, dict):
            err(f"option {i} must be an object")
            continue
        for k in o:
            if k not in ("label", "art", "value", "bait"):
                err(f"option {i}: unknown key '{k}'")
        _text(err, f"option {i} label", o.get("label"), 14, required=True)
        labels.append(o.get("label"))
        _art(err, f"option {i} art", o.get("art"), icons)
        v = o.get("value")
        if not _is_int(v) or v < 0:
            err(f"option {i} value must be a whole number >= 0")
        if o.get("bait") is not None and not isinstance(o["bait"], bool):
            err(f"option {i} bait must be true or false")
    if len(set(map(str, labels))) != len(labels):
        err("option labels must be different")
    vals = [o.get("value") for o in opts if isinstance(o, dict) and _is_int(o.get("value"))]
    if sum(vals) > total:
        err(f"option values add up to {sum(vals)}, more than total {total}")


def _views(err, p, icons):
    if p.get("job") is not None:
        _tag(err, "job", p["job"], 26)
    _text(err, "label", p.get("label"), 12)
    if not _is_int(p.get("value")):
        err("value must be an integer")
    if p.get("from") is not None and not _is_int(p["from"]):
        err("from must be an integer")
    _text(err, "prefix", p.get("prefix"), 0)
    _text(err, "suffix", p.get("suffix"), 2)
    g = p.get("grid")
    if g is not None and (not _is_int(g) or not 0 <= g <= 8):
        err("grid must be an integer 0-8")
    _text(err, "thumbLabel", p.get("thumbLabel"), 8)
    _art(err, "art", p.get("art"), icons)


def _anchor(err, p, icons):
    if p.get("job") is not None:
        _tag(err, "job", p["job"], 26)   # limit 26 prevzaty z Views (rovnaky stitok)
    _text(err, "price", p.get("price"), 12, required=True)
    for k in ("at", "split"):
        v = p.get(k)
        if v is not None and (not _is_num(v) or not 0 <= v <= 1):
            err(f"{k} must be a number 0-1")
    _art(err, "art", p.get("art"), icons)
    a = p.get("anchor")
    if a is not None:
        if not isinstance(a, dict):
            err('anchor must be an object {"label", "art"}')
        else:
            for k in a:
                if k not in ("label", "art"):
                    err(f"anchor: unknown key '{k}'")
            _text(err, "anchor label", a.get("label"), 24)
            _art(err, "anchor art", a.get("art"), icons)


def _compare(err, p, icons):
    before, after = p.get("before"), p.get("after")
    if not isinstance(before, list) or not isinstance(after, list):
        err("before and after must be lists")
        return
    if not (2 <= len(before) <= 3 and len(before) == len(after)):
        err(f"before ({len(before)}) and after ({len(after)}) need the same number of items, 2-3")
    for i, c in enumerate(before, 1):
        if c is not None:
            _card(err, f"before card {i}", c, icons, 20, 8, False)   # titul sa zmensi (fit.ts)
    reveal = all(c is None for c in after)   # najprv len BEFORE, AFTER príde v ďalšom údere
    for i, c in enumerate(after, 1):
        if c is None:
            if not reveal:
                err(f"after card {i} must not be null (null is only for before, or all after null = reveal later)")
        else:
            _card(err, f"after card {i}", c, icons, 20, 8, False)
    lab = p.get("labels")
    if lab is not None and not (isinstance(lab, list) and len(lab) == 2 and all(isinstance(x, str) for x in lab)):
        err("labels must be a list of 2 strings")
    prices = [tuple(nums(c.get("price") or "")) for c in after if isinstance(c, dict) and nums(c.get("price") or "")]
    if len(prices) >= 3 and len(set(prices)) == 1:
        err("all after options cost the same - the trick needs different prices (the cheap option stays cheaper)")


def _statement(err, p, icons=None):
    _text(err, "kicker", p.get("kicker"), 28)
    t, tags = p.get("text"), p.get("tags")
    if t is not None:
        if not isinstance(t, str):
            err("text must be a string")
        else:
            if len(t.split()) > 7:
                err(f"text has {len(t.split())} words (max 7)")
            if len(t) > 40:
                err(f"text too long ({len(t)} > 40)")
    if tags is not None:
        if not isinstance(tags, list):
            err("tags must be a list")
        else:
            if len(tags) > 3:
                err(f"{len(tags)} tags (max 3)")
            for j, tg in enumerate(tags, 1):
                _tag(err, f"tag {j}", tg, 28)
    if not t and not tags:
        err("needs text or tags")


def _outro(err, p, icons):
    _art(err, "art", p.get("art"), icons)


CHECKS = {"Hero": _hero, "PriceList": _pricelist, "Views": _views, "Anchor": _anchor, "Compare": _compare,
          "Statement": _statement, "Outro": _outro, "Crowd": _crowd}


# ---------- nadvaznost (pravidlo 5) ----------
def _titles(cards):
    return [c.get("title") if isinstance(c, dict) else None for c in cards] if isinstance(cards, list) else []


def _strip(c):
    return {k: v for k, v in c.items() if k not in ("badge", "top")} if isinstance(c, dict) else c


def _cont_pricelist(E, no, pa, pb):
    ta, tb = _titles(pa.get("cards")), _titles(pb.get("cards"))
    for i, t in enumerate(ta):
        if i >= len(tb):
            E.beat(no, "PriceList", f'card {i + 1} ("{t}") of the previous beat is missing - cards must stay in place')
        elif tb[i] != t:
            E.beat(no, "PriceList", f'card {i + 1} title changed from "{t}" to "{tb[i]}" - cards must stay in place')


def _cont_compare(E, no, pa, pb):
    ba, bb, aa, ab = pa.get("before"), pb.get("before"), pa.get("after"), pb.get("after")
    if not all(isinstance(x, list) for x in (ba, bb, aa, ab)):
        return
    ta, tb = _titles(ba), _titles(bb)
    if not any(t is not None and i < len(tb) and tb[i] == t for i, t in enumerate(ta)):
        return   # ina firma = novy zaciatok transferu
    if ba != bb:
        E.beat(no, "Compare", "before changed since the previous Compare beat (it must stay identical)")
    if len(aa) != len(ab):
        E.beat(no, "Compare", "number of after cards changed since the previous Compare beat")
    if all(x is None for x in aa):
        return   # AFTER sa práve odhalil
    for i, (x, y) in enumerate(zip(aa, ab), 1):
        if _strip(x) != _strip(y):
            E.beat(no, "Compare", f"after card {i} changed (between Compare beats only badge and top may change)")


# ---------- pribeh (pravidlo 8) ----------
def _words(s):
    return re.findall(r"[a-z0-9$%]+(?:[.,][0-9]+)*", re.sub(r"(?<=\w)'(?=\w)", "", _fold(s)).replace("-", " "))


def _story_checks(E, beats):
    """Kvalita rozpravania, ktoru free modely kazia: dlhy hak s cislami, opakovane vety/frazy/cisla, citanie kariet."""
    says = [(no, b.get("scene", "?"), b["say"]) for no, b in enumerate(beats, 1)
            if isinstance(b, dict) and isinstance(b.get("say"), str)]
    if says and says[0][0] == 1:
        no, sc, s = says[0]
        if len(s.split()) > 14:
            E.beat(no, sc, f"hook has {len(s.split())} words (max 14 - a short paradox, no explanation)")
        if len(set(nums(s))) > 1:
            E.beat(no, sc, "hook has more than one number (the numbers come later, the hook is the strange thing)")
    seen_sent, seen_gram, num_beats = {}, {}, {}
    for no, sc, s in says:
        for sent in re.split(r"(?<=[.!?])\s+", s):
            w = _words(sent)
            if len(w) >= 3 and w != ["follow", "for", "more"]:
                k = " ".join(w)
                if k in seen_sent:
                    E.beat(no, sc, f'repeats the sentence "{sent.strip()}" from beat {seen_sent[k]} - every beat must say something new')
                else:
                    seen_sent[k] = no
        w = [x for x in _words(s) if x not in ("follow", "more")]
        for i in range(len(w) - 4):
            g = " ".join(w[i:i + 5])
            if g in seen_gram and seen_gram[g] != no:
                E.beat(no, sc, f'repeats the phrase "{g}" from beat {seen_gram[g]}')
                break
            seen_gram.setdefault(g, no)
        for x in set(nums(s)):
            if not _exempt(x):
                num_beats.setdefault(x, []).append(no)
    for x, where in num_beats.items():
        if len(where) > 2:
            E.top(f"number {x} is spoken in {len(where)} beats ({', '.join(map(str, where))}) - max 2, the card already shows it")
    for no, b in enumerate(beats, 1):   # citanie karty: nazov karty + jej cena v tej istej vete
        if not (isinstance(b, dict) and b.get("scene") == "PriceList" and isinstance(b.get("say"), str)):
            continue
        cards = (b.get("props") or {}).get("cards") if isinstance(b.get("props"), dict) else None
        pb = beats[no - 2] if no > 1 and isinstance(beats[no - 2], dict) else {}
        shown = {c.get("title") for c in ((pb.get("props") or {}).get("cards") or []) if isinstance(c, dict)} if pb.get("scene") == "PriceList" else set()
        sw = " " + " ".join(_words(b["say"])) + " "
        for c in cards if isinstance(cards, list) else []:
            if not isinstance(c, dict) or c.get("title") not in shown:
                continue   # karta, ktora prave pribudla, sa smie predstavit menom a cenou (SCRIPT_GUIDE: cena raz, ked karta pride)
            t, pr = " ".join(_words(c.get("title") or "")), nums(c.get("price") or "")
            if t and f" {t} " in sw and pr and pr[0] in nums(b["say"]):
                E.beat(no, "PriceList", f'reads the card "{c.get("title")}" aloud (title + price) - the card shows it, say what it means')
                break
    for no, b in enumerate(beats, 1):
        if isinstance(b, dict) and b.get("scene") == "Anchor" and isinstance(b.get("props"), dict):
            if "%" in str(b["props"].get("price") or ""):
                E.beat(no, "Anchor", "Anchor price must be a price, not a percentage (use Views for shares)")


PLAN_KEYS = ("paradox", "odd_fact", "twist", "cause", "everyday", "rule")


def lint_story(st, case):
    """Krok 1 autora: len hlas po uderoch ({"plan", "beats": [{scene, say}]}) – dlzka, cisla a mena z faktov, pribeh."""
    E = _Errs()
    case = case if isinstance(case, dict) else {}
    plan = st.get("plan") if isinstance(st, dict) else None
    if not isinstance(plan, dict):
        E.top('"plan" is missing - fill it first: ' + ", ".join(PLAN_KEYS))
    else:
        miss = [k for k in PLAN_KEYS if not str(plan.get(k) or "").strip()]
        if miss:
            E.top("plan is missing: " + ", ".join(miss))
    beats = st.get("beats") if isinstance(st, dict) else None
    if not isinstance(beats, list) or not beats:
        E.top("beats must be a non-empty list of {scene, say}")
        return E.result()
    n = len(beats)
    if not 12 <= n <= 15:
        E.top(f"{n} beats, need 12-15")
    if beats[0].get("scene") != "Hero":
        E.beat(1, str(beats[0].get("scene")), "first beat must be scene Hero")
    outros = [i for i, b in enumerate(beats, 1) if b.get("scene") == "Outro"]
    if outros != [n]:
        E.top("scene Outro must be exactly once, as the last beat")
    facts, allowed, total = _fact_nums(case), _allowed_caps(case), 0
    for no, b in enumerate(beats, 1):
        sc, say = b.get("scene"), b.get("say") or ""
        if sc not in SCENES:
            E.beat(no, str(sc), f"unknown scene {sc!r} (use {', '.join(SCENES)})")
        nw = len(say.split())
        total += nw
        if not 2 <= nw <= 24:
            E.beat(no, str(sc), f"say has {nw} words (need 3-20)")
        if _EMOJI.search(say) or _MD.search(say):
            E.beat(no, str(sc), "say contains emoji, symbols or markdown")
        if sc == "Compare":
            for hit in _compare_hits([say], case):
                E.beat(no, sc, f'Compare must not mention "{hit}" (no brands, no case names)')
            continue
        for x in dict.fromkeys(nums(say)):
            if not _exempt(x) and x not in facts:
                E.beat(no, str(sc), f"number {x} is not in the case facts")
        if sc == "PriceList" and nums(say):
            E.beat(no, sc, "no numbers or prices in PriceList beats - the cards show them; say what the option means")
        for w in _unknown_names(say, allowed):
            E.beat(no, str(sc), f'name "{w}" is not one of the case names')
    if not 85 <= total <= 150:
        E.top(f"spoken words total {total}, need 85-150 (aim for 115-135; pauses add about 15%)")
    _story_checks(E, beats)
    return E.result()


# ---------- hlavna funkcia ----------
def lint(story, case, icons=None):
    """story = dict z JSON, case = prilezitost z banky, icons = mnozina platnych `art` (None = nekontrolovat)."""
    E = _Errs()
    top = E.top
    if not isinstance(story, dict):
        return ["story must be a JSON object"]
    case = case if isinstance(case, dict) else {}
    for k in story:
        if k not in TOP_KEYS:
            top(f"unknown top-level key '{k}' (the code adds voice, music and brand)")

    # 7. case / title / caption / source
    c = story.get("case")
    if not isinstance(c, str) or not c.strip():
        top("case is missing")
    elif not 1 <= len(c.split()) <= 3 or c != c.upper():
        top(f'case "{c}" must be 1-3 words in UPPER CASE')
    for key in ("title", "source"):
        v = story.get(key)
        if not isinstance(v, str) or not v.strip():
            top(f"{key} is missing")
        elif len(v) > 60:
            top(f"{key} too long ({len(v)} > 60)")
    cap = story.get("caption")
    if not isinstance(cap, str) or not cap.strip():
        top("caption is missing")
    elif len([ln for ln in cap.splitlines() if ln.strip()]) > 2:
        top("caption has more than 2 lines")

    beats = story.get("beats")
    if not isinstance(beats, list) or not beats:
        top("beats must be a non-empty list")
        return E.result()
    n = len(beats)
    if not 11 <= n <= 17:   # 1.
        top(f"{n} beats, need 11-17")

    facts = _fact_nums(case)
    allowed_caps = _allowed_caps(case, story)
    total = 0
    for no, b in enumerate(beats, 1):
        if not isinstance(b, dict):
            E.beat(no, "?", "beat must be an object")
            continue
        scene = b.get("scene")
        sc = scene if isinstance(scene, str) else "?"

        def err(m, no=no, sc=sc):
            E.beat(no, sc, m)

        try:
            for k in b:
                if k not in BEAT_KEYS:
                    err(f"unknown beat key '{k}'")
            if b.get("mode") is not None and b["mode"] not in ("paper", "blueprint"):
                err(f"mode must be paper or blueprint (got {b['mode']!r})")
            h = b.get("hold")
            if h is not None and (not _is_num(h) or not 0 < h <= 8):
                err("hold must be a number of seconds, 0-8")
            if no == 1 and scene != "Hero":
                err("first beat must be scene Hero")
            # 2. say
            say = b.get("say")
            if not isinstance(say, str) or not say.strip():
                err("say is missing")
                say = None
            else:
                nw = len(say.split())
                total += nw
                if not 2 <= nw <= 24:
                    err(f"say has {nw} words (need 2-24)")
                if _EMOJI.search(say):
                    err("say contains emoji or symbols")
                if _CURLY.search(say):
                    err("say has curly quotes - use only straight \" and '")
                if _MD.search(say):
                    err("say contains markdown (* # ` _ ~ [ ] < > | or list markers)")
            # scena a props
            if scene not in SCENES:
                err(f"unknown scene {scene!r} (use {', '.join(SCENES)})")
                continue
            props = b.get("props")
            if props is None and scene == "Outro":
                props = {}
            if not isinstance(props, dict):
                err("props must be an object")
                continue
            for k in props:
                if k not in SCENE_KEYS[scene]:
                    err(f"unknown prop '{k}'" + (" (the code fills logo, stamp, tagline and cta)" if scene == "Outro" else ""))
            CHECKS[scene](err, props, icons)
            # 3. cisla (Compare: vymyslene ceny na kartach su povolene, v say musia byt z faktov alebo z kariet)
            pnums = _prop_numbers(props)
            pool = facts | set(pnums) | _diffs(pnums) if scene == "Compare" else facts
            if say:
                for x in dict.fromkeys(nums(say)):
                    if not _exempt(x) and x not in pool:
                        err(f"number {x} in say is not in the case facts")
            if scene != "Compare":
                for x in dict.fromkeys(pnums):
                    if not _exempt(x) and x not in facts:
                        err(f"number {x} in props is not in the case facts")
            # 4. mena
            hit_stems = set()
            if scene == "Compare":
                for hit in _compare_hits(([say] if say else []) + _strings(props), case):
                    err(f'Compare must not mention "{hit}" (no brands, no case names)')
                    hit_stems |= {_stem(w) for w in hit.split()}
            if say:
                for w in _unknown_names(say, allowed_caps):
                    if _stem(w) not in hit_stems:
                        err(f'name "{w}" in say is not one of the case names')
        except Exception as ex:   # lint nesmie spadnut na zlom tvare JSON
            err(f"malformed beat ({type(ex).__name__}: {ex})")

    # 2. spolu slov
    if not 85 <= total <= 150:
        top(f"spoken words total {total}, need 85-150 (aim for 115-135; pauses add about 15%)")
    # 8. pribeh: hak, ziadne opakovanie, ziadne citanie kariet
    _story_checks(E, beats)
    # 1. Outro prave raz a posledny
    outros = [i for i, b in enumerate(beats, 1) if isinstance(b, dict) and b.get("scene") == "Outro"]
    if not outros:
        top("no Outro beat: the last beat must be scene Outro (exactly once)")
    else:
        if len(outros) > 1:
            top(f"Outro appears {len(outros)} times (exactly once, as the last beat)")
        if outros[-1] != n:
            last = beats[-1].get("scene") if isinstance(beats[-1], dict) else "?"
            E.beat(n, str(last), "last beat must be scene Outro")
    # 5. nadvaznost
    for i in range(1, n):
        a, b = beats[i - 1], beats[i]
        if not (isinstance(a, dict) and isinstance(b, dict) and a.get("scene") == b.get("scene")):
            continue
        pa, pb = a.get("props"), b.get("props")
        if isinstance(pa, dict) and isinstance(pb, dict):
            if b["scene"] == "PriceList":
                _cont_pricelist(E, i + 1, pa, pb)
            elif b["scene"] == "Compare":
                _cont_compare(E, i + 1, pa, pb)
    # 6. cervena
    reds = []
    for b in beats:
        if not isinstance(b, dict) or not isinstance(b.get("props"), dict):
            continue
        p, cards = b["props"], []
        if b.get("scene") == "PriceList" and isinstance(p.get("cards"), list):
            cards = p["cards"]
        elif b.get("scene") == "Compare":
            cards = [x for side in ("before", "after") if isinstance(p.get(side), list) for x in p[side]]
        for card in cards:
            if _is_red(card) and isinstance(card.get("title"), str) and card["title"] not in reds:
                reds.append(card["title"])
    if len(reds) > 2:
        top(f"red/stamp is used on {len(reds)} different cards (max 2, bait only): " + ", ".join(f'"{t}"' for t in reds))
    # cisla v title a caption (verejny text): fakty + rok a cisla zo zdroja prípadu (napr. "(2008)")
    pub = facts | set(nums(case.get("source", ""))) | ({str(case["year"])} if case.get("year") else set())
    for key in ("title", "caption"):
        v = story.get(key)
        if isinstance(v, str):
            for x in dict.fromkeys(nums(v)):
                if not _exempt(x) and x not in pub:
                    top(f"number {x} in {key} is not in the case facts")
    return E.result()


def main():
    ap = argparse.ArgumentParser(description="Lint story.json podla SPEC (exit 1 ak su chyby).")
    ap.add_argument("story", help="napr. episodes/001-economist-decoy/story.json")
    ap.add_argument("--case-file", help="JSON s pripadom (inak sa hlada podla id v bank/cases.json)")
    a = ap.parse_args()
    try:
        story = load(a.story)
    except (OSError, ValueError) as ex:
        print(f"lint: {a.story} sa nedá načítať: {ex}", file=sys.stderr)
        return 2
    cid = story.get("id") if isinstance(story, dict) else None
    case = case_from_file(a.case_file, cid) if a.case_file else case_by_id(cid)
    if not case:
        print(f"lint: prípad '{cid}' sa nenašiel (použi --case-file)", file=sys.stderr)
        return 2
    errs = lint(story, case, load_icons())
    for e in errs:
        print(e)
    print(f"{len(errs)} chýb" if errs else "OK")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
