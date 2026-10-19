# -*- coding: utf-8 -*-
"""Autor epizody = bezplatny model (retazec: Cloudflare Workers AI gpt-oss-120b -> Groq gpt-oss-120b -> Cloudflare Gemma 4
-> Cloudflare Qwen 3.8 -> Groq gpt-oss-20b -> Gemini -> OpenRouter). Pripad z banky -> episodes/NNN-id/story.json.
Kontrola je mechanicka (lint.py), max 4 pokusy; po chybach dostane model zoznam chyb (Groq ma okno 8k tokenov/min,
preto sa predosly JSON neposiela a model pise znova; Cloudflare/Gemini/OpenRouter dostanu aj predosly JSON na opravu).
Kazdy pokus sa uklada do episodes/NNN-id/attempts/ (diagnostika).
    python tools/write_case.py economist-decoy --out episodes/001-economist-decoy/story.json
    python tools/write_case.py economist-decoy --case-file tools/tests/case_economist.json --out x/story.json
    ... --fake odpoved1.json odpoved2.json   (offline test: namiesto modelu sa citaju odpovede zo suborov v poradi)
Retazec modelov: env MODELS_CHAIN="cloudflare:@cf/openai/gpt-oss-120b,groq:openai/gpt-oss-120b" (backend:model, ciarkami).
Kluce: CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID (Cloudflare), MODELS_TOKEN alebo GROQ_API_KEY (Groq), GEMINI_API_KEY,
OPENROUTER_API_KEY; backend bez kluca sa preskoci. MODELS_MAX_WAIT = max cakanie v s na denny limit (900).
Navrat: 0 = ulozene (vypise cestu), 2 = zlyhanie."""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import case_by_id, case_from_file, save  # noqa: E402
from lint import lint, load_icons, read_icon_names  # noqa: E402

CF_ACC = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
BASES = {"cloudflare": f"https://api.cloudflare.com/client/v4/accounts/{CF_ACC}/ai/v1",
         "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
         "groq": "https://api.groq.com/openai/v1", "openrouter": "https://openrouter.ai/api/v1"}
KEYS = {"cloudflare": ("CLOUDFLARE_API_TOKEN",), "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "groq": ("MODELS_TOKEN", "GROQ_API_KEY"), "openrouter": ("OPENROUTER_API_KEY",)}
# poradie: Cloudflare Workers AI gpt-oss-120b (vlastna kvota 10k neuronov/den ~ 25 volani, velke okno)
# -> Groq 120b (kluc zdielany s inymi fabrikami, 200k/den) -> Cloudflare Gemma 4 / Qwen 3.8 (ta ista kvota, iny model)
# -> Groq 20b -> Gemini (iba ak projekt nie je blokovany) -> OpenRouter (len ak je kluc)
DEFAULT_CHAIN = ("cloudflare:@cf/openai/gpt-oss-120b,groq:openai/gpt-oss-120b,cloudflare:@cf/google/gemma-4-26b-a4b-it,"
                 "cloudflare:@cf/qwen/qwen3.8-27b,groq:openai/gpt-oss-20b,gemini:gemini-3.8-flash,"
                 "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free")
CHAIN = [tuple(m.strip().split(":", 1)) for m in os.environ.get("MODELS_CHAIN", DEFAULT_CHAIN).split(",") if ":" in m]
ATTEMPTS = 4          # pokusy autora (kazdy dalsi so zoznamom chyb)
MAX_TOKENS = 5000
MAX_WAIT = int(os.environ.get("MODELS_MAX_WAIT", "900"))   # max cakanie (s) na denny limit, ked server povie "try again in"
# Groq free: prompt + max_tokens <= TPM okno (gpt-oss 8k, qwen ~6k); Gemini/OpenRouter bez takeho okna
WINDOWS = {"gpt-oss": 7850, "qwen": 5900}
BIG_WINDOW = 60000

DEFAULT_ICONS = """coffee cup-soda popcorn pizza sandwich cake cake-slice ice-cream-cone candy wine beer apple egg utensils
smartphone laptop tv headphones watch camera gamepad-2 printer plane bike bus train-front fuel house hotel bed
armchair lamp sofa dumbbell pill stethoscope scissors shirt gem crown gift ticket clapperboard book-open
graduation-cap shopping-cart shopping-bag store package truck tag receipt credit-card banknote coins piggy-bank
wallet key lock percent trophy star newspaper mail droplets zap wifi flame rocket glasses footprints umbrella
phone refrigerator washing-machine microwave bath baby dog cat flower-2 trees tent ship sailboat anchor scale
hammer wrench paintbrush palette briefcase landmark shield heart car car-red car-fly none""".split()

PROMPT = '''You write one episode of "PRICE TRAP" – a vertical explainer video (TikTok/Reels, 55–75 seconds) in the style of a
paper price report: calm male voice, short punchy sentences, dry wit, every sentence = one visual change on beige paper
with price cards. Each episode exposes ONE pricing trick from a real, documented case, then shows the viewer the same
trick in everyday life.

CASE: {case}   TRICK: {trick}
SUBJECT: {subject}
FACTS (the only facts, names and numbers you may use – quote numbers exactly as written, never add others):
{facts}
LESSON: {lesson}
SOURCE: {source}
ICONS you may use as "art": {icons}   Suggested: hero {icon_hero}, bait {icon_bait}, real choice {icon_real}

STRUCTURE – 12 to 16 beats. One beat = 1–2 spoken sentences (6 to 22 words, numbers as digits with $ or %).
TOTAL spoken words across all beats: 110 to 170 (count them – a 55–75 second voice-over). Short beats are fine,
but never fewer than 110 words in total:
1. HOOK (beats 1–2, scene Hero): the surprising thing in the first 3 seconds. No intro, no "today", no question.
2. THE LIST (beats 3–6, scene PriceList, 2–3 cards): cards appear top-down, one new card per beat. Repeat the full
   previous state and add one thing per beat (a card, a tag, a price). Every card keeps its position and title in all
   later PriceList beats – never reorder, rename or remove a card. The bait card is first: red price text
   ("NO PRICE", "$17,000"...) via "priceRed": true, tags like INVITE ONLY / LIMITED / SOLD OUT. Real choices below it.
3. THE REVEAL (1–2 beats, "mode": "blueprint"): the same PriceList with "stamp": "BAIT" on the bait card; then scene
   Statement with kicker "WHAT THE BAIT DOES" and 2 tags "JOB 1 · ..." / "JOB 2 · ..." (each ≤ 28 characters).
4. THE MECHANISM (2–3 beats): scene Anchor (the real price with "split" moving right when the "anchor" appears) and/or
   scene Views (only if FACTS contain attention, sales or views numbers). Teach the numbers from FACTS here.
5. THE TRANSFER (2–3 beats, scene Compare, props "before"/"after"): the same trick in 1–2 everyday businesses (bakery,
   gym, coach, café, app, hotel, barber...). Invented but realistic prices are allowed ONLY here. No brand names here.
   before = [null, option, option]; after = [bait on top with "top": {"text": "EXTREME", "tone": "red"}, same options];
   last Compare beat gives the middle option "badge": {"text": "SMART CHOICE", "tone": "green"}.
6. THE RULE (1 beat, scene Statement): "text" = a 4–7 word rule (e.g. "Ask what it's selling."), spoken as advice.
7. OUTRO (last beat, scene Outro, props {}): say the rule in one line + "Follow for more."

STYLE: second person, present tense, concrete nouns, no filler, no "imagine", no emoji, straight quotes only.
Numbers exactly as in FACTS. Never invent statistics, studies, names, years or prices for the real case, and never
invent how the seller presented it (no made-up badges, labels, slogans, colours, "most popular" tags or quotes) –
if FACTS do not say it, it did not happen. Badges and tags on the real case's cards only when FACTS mention them.
Capitalized names in the narration only as they appear in FACTS; everything else lower case.
RED is only for the bait: exactly ONE card in the whole episode may carry priceRed, a red tag or a stamp (the bait),
plus the EXTREME top tag of the bait card in Compare. Everything else plain, dark, blue, yellow or green.
Card text limits: title ≤ 18 chars, sub ≤ 22, price ≤ 12, tag ≤ 16, ≤ 3 tags; in Compare title ≤ 16, price ≤ 8.
Scene props (JSON shapes):
{schemas}
Return ONLY JSON: {"case": "2-3 WORDS UPPER CASE", "title": "post title ≤ 60 chars", "caption": "1-2 lines for the post",
"source": "{source}", "beats": [ {"say": "...", "scene": "...", "props": {...}, "mode": "blueprint" (optional), "hold": 4 (optional)} ]}'''

# JSON ukazky scen z tabulky v SPEC (limity v zatvorkach)
SCHEMAS = '''Hero: {"art": "<icon>", "tag": TAG, "title": "≤16 chars", "sub": "≤22 chars"}
PriceList: {"slots": 2 or 3, "cards": [CARD, ...]}   (1-3 cards, slots ≥ number of cards)
Views: {"job": "JOB 1 · ... (≤26 chars)", "label": "≤10 chars", "value": <int>, "from": <int>, "prefix": "", "suffix": "≤2 chars", "grid": 0-8, "thumbLabel": "≤8 chars", "art": "<icon>"}
Anchor: {"job": "JOB 2 · ... (≤26 chars)", "price": "≤12 chars", "at": 0-1, "split": 0-1, "art": "<icon>", "anchor": {"label": "≤24 chars", "art": "<icon>"}}
Compare: {"before": [null, CARD, CARD], "after": [CARD, CARD, CARD], "labels": ["BEFORE", "AFTER"]}   (2-3 items, same count in both; null only in before)
Statement: {"kicker": "≤28 chars", "text": "≤7 words, ≤40 chars", "tags": ["≤28 chars", "≤28 chars"]}
Outro: {}
CARD = {"title": "...", "sub": "...", "price": "...", "priceRed": true, "tags": ["TEXT", {"text": "TEXT", "tone": "yellow"}], "art": "<icon>", "stamp": "BAIT", "badge": TAG, "top": TAG}   (all fields except title are optional)
TAG = "TEXT" or {"text": "TEXT", "tone": "plain|dark|blue|yellow|red|green"}'''

USER_MSG = "Write the episode now. Return ONLY the JSON object."
FIX_MSG = ("Write the episode now. Return ONLY the JSON object.\n\nA previous attempt had these problems – "
           "write the whole episode again and avoid every one of them:\n- ")
FIX_PREV_MSG = ("Fix exactly these problems and return the complete corrected JSON (if the total word count is too low, "
                "expand the \"say\" of most beats to one or two full sentences of 8-16 words; keep scenes and props):\n- ")

CURLY = str.maketrans({"‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'",
                       "“": '"', "”": '"', "„": '"', "«": '"', "»": '"', "″": '"',
                       "‐": "-", "‑": "-", "‒": "-", "–": " - ", "—": " - ", "―": " - ",
                       "…": "...", " ": " ", " ": " ", " ": " "})


class ModelError(RuntimeError):
    def __init__(self, msg, code=0, fatal=False):
        super().__init__(msg)
        self.code, self.fatal = code, fatal


def api_key(backend):
    if backend == "cloudflare" and not CF_ACC:
        return None
    for k in KEYS[backend]:
        if os.environ.get(k):
            return os.environ[k]
    return None


def window(backend, model):
    if backend != "groq":
        return BIG_WINDOW
    return next((w for k, w in WINDOWS.items() if k in model), 7850)


def body_for(backend, model, messages, max_tokens, reasoning=True):
    b = {"model": model, "messages": messages, "temperature": 0.8, "max_tokens": max_tokens}
    if backend == "openrouter":   # mysliace modely nesmu minat vystup na skryte uvahy; JSON sa vyberie z textu
        b["reasoning"] = {"enabled": False, "exclude": True}
        return b
    b["response_format"] = {"type": "json_object"}
    if not reasoning:
        return b
    if backend == "gemini" or "gpt-oss" in model:
        b["reasoning_effort"] = "medium" if backend == "cloudflare" else "low"   # Groq: low kvoli oknu 8k TPM
    elif "qwen" in model and backend == "groq":
        b["reasoning_effort"] = "none"   # Groq: vypne thinking, inak zje okno TPM
    return b


def retry_in(msg):
    """Sekundy z hlasky 'try again in 1m30.72s' / 'retry in 23.5s' / retryDelay: "23s"; None ak chyba."""
    m = re.search(r"(?:try again|retry) in (?:(\d+)h)?(?:(\d+)m)?([\d.]+)s", msg, re.I)
    if m:
        return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + float(m.group(3))
    m = re.search(r'retryDelay"?:\s*"?([\d.]+)s', msg)
    return float(m.group(1)) if m else None


def call(backend, model, messages, max_tokens):
    """Jedno volanie modelu. Pri 413/429 (minutovy limit) a 5xx caka 65 s (5x); pri dennom limite s kratkym
    'try again' caka raz-dvakrat, inak nechava dalsi model. Vrati (text, finish_reason)."""
    key = api_key(backend)
    if not key:
        raise ModelError(f"{backend}: chyba kluc ({' / '.join(KEYS[backend])})", 0, True)
    waits, daywaits, reasoning = 0, 0, True
    while True:
        body = json.dumps(body_for(backend, model, messages, max_tokens, reasoning)).encode()
        req = urllib.request.Request(BASES[backend] + "/chat/completions", data=body, headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "PriceTrap/1.0",
            "HTTP-Referer": "https://github.com/brockai667", "X-Title": "PriceTrap"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                ch = json.loads(r.read())["choices"][0]
            return ch["message"].get("content") or "", ch.get("finish_reason")
        except urllib.error.HTTPError as e:
            msg = e.read()[:700].decode(errors="replace")
            lim = re.search(r"Limit (\d+), Requested (\d+)", msg)
            if e.code in (413, 429) and lim and int(lim.group(2)) > int(lim.group(1)) and "per day" not in msg:
                # poziadavka je vacsia nez limit okna -> cakanie nepomoze, skratime max_tokens
                new = max_tokens - (int(lim.group(2)) - int(lim.group(1))) - 150
                if new < 1500:
                    raise ModelError(f"{backend} {e.code}: poziadavka {lim.group(2)} > limit {lim.group(1)} tokenov", e.code)
                print(f"{backend} {e.code}: poziadavka {lim.group(2)} > limit {lim.group(1)}, max_tokens {max_tokens} -> {new} "
                      f"({msg[:160]})", file=sys.stderr)
                max_tokens = new
                continue
            if e.code == 400 and reasoning and "reasoning" in msg:
                reasoning = False   # model/backend nepozna reasoning_effort -> bez neho
                continue
            if e.code == 400 and "json_validate_failed" in msg:
                raise ModelError(f"{backend} 400: model nevratil platny JSON", 400)
            if e.code == 429 and (backend != "groq" or re.search(r"per day|TPD|RPD", msg)):
                wait = retry_in(msg)
                if wait is not None and wait <= MAX_WAIT and daywaits < 2:
                    daywaits += 1
                    print(f"{backend} 429 (denny limit / RPM), cakam {wait:.0f} s", file=sys.stderr)
                    time.sleep(wait + 3)
                    continue
                used = re.search(r"Limit \d+, Used \d+, Requested \d+", msg)
                raise ModelError(f"{backend} 429 denny limit ({used.group(0) if used else msg[:160]}; "
                                 f"skus za {int(wait) if wait is not None else '?'} s)", 429)
            if e.code in (401, 403):
                raise ModelError(f"{backend} {e.code}: kluc odmietnuty", e.code, fatal=True)
            if e.code not in (413, 429, 500, 502, 503) or waits >= 4:
                raise ModelError(f"{backend} {e.code}: {msg[:300]}", e.code)
            waits += 1
            print(f"{backend} {e.code}, cakam 65 s", file=sys.stderr)
            time.sleep(65)
        except (urllib.error.URLError, OSError) as e:   # siet / timeout
            if waits >= 4:
                raise ModelError(f"{backend} siet: {str(e)[:150]}", 0)
            waits += 1
            print(f"{backend} siet ({str(e)[:80]}), cakam 15 s", file=sys.stderr)
            time.sleep(15)


def est_tokens(msgs):
    return int(sum(len(m["content"]) for m in msgs) / 3.0) + 20


def ask(base, prev, errs):
    """Prejde retazec modelov. Groq (male okno) dostane len zoznam chyb, OpenRouter aj predosly JSON.
    Vrati (surovy text, "backend:model")."""
    last, skip = None, set()
    for backend, model in CHAIN:
        if backend in skip:
            continue
        if backend not in BASES:
            print(f"  neznamy backend {backend}", file=sys.stderr)
            continue
        win = window(backend, model)
        msgs = list(base)
        if errs and prev is not None and win > 20000:
            msgs += [{"role": "assistant", "content": json.dumps(prev, ensure_ascii=False, separators=(",", ":"))},
                     {"role": "user", "content": FIX_PREV_MSG + "\n- ".join(errs[:20])}]
        elif errs:
            msgs[-1] = {"role": "user", "content": FIX_MSG + "\n- ".join(errs[:20])}
        max_tokens = max(1800, min(MAX_TOKENS if backend == "groq" else 12000, win - est_tokens(msgs)))
        try:
            raw, fin = call(backend, model, msgs, max_tokens)
            if fin == "length":
                print(f"  {backend}:{model}: odpoved odrezana (max_tokens {max_tokens})")
            return raw, f"{backend}:{model}"
        except ModelError as e:
            last = e
            print(f"  {backend}:{model}: {e}", file=sys.stderr)
            if e.fatal:
                skip.add(backend)
    raise last or ModelError("ziadny model v retazci", 0, True)


def build_prompt(case, icon_list):
    ic = case.get("icons") or {}
    subs = {"schemas": SCHEMAS, "case": case.get("case", ""), "trick": case.get("trick", ""),
            "subject": case.get("subject", ""), "facts": "\n".join("- " + f for f in case.get("facts") or []),
            "lesson": case.get("lesson", ""), "source": case.get("source", ""), "icons": ", ".join(icon_list),
            "icon_hero": ic.get("hero", "none"), "icon_bait": ic.get("bait", "none"), "icon_real": ic.get("real", "none")}
    text = PROMPT
    for k, v in subs.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def parse_json(raw):
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        return json.loads(t)
    except ValueError:
        i, j = t.find("{"), t.rfind("}")
        if i < 0 or j <= i:
            raise ValueError("no JSON object found")
        return json.loads(t[i:j + 1])


def _walk(v, fn):
    if isinstance(v, str):
        return fn(v)
    if isinstance(v, list):
        return [_walk(x, fn) for x in v]
    if isinstance(v, dict):
        return {k: _walk(x, fn) for k, x in v.items()}
    return v


def normalize(story, case):
    """Mechanicke upravy pred lintom: rovne uvodzovky, source z banky, CASE velkymi, chybajuce ikony z pripadu."""
    story = _walk(story, lambda s: s.translate(CURLY))
    story.pop("id", None)
    story["source"] = case.get("source", "")
    if isinstance(story.get("case"), str):
        story["case"] = " ".join(story["case"].upper().split())
    ic = case.get("icons") or {}
    hero, bait, real = ic.get("hero", "none"), ic.get("bait", "none"), ic.get("real", "none")
    for b in story.get("beats") or []:
        if not isinstance(b, dict):
            continue
        if isinstance(b.get("say"), str):
            b["say"] = " ".join(b["say"].split())
        if b.get("scene") == "Outro" and b.get("props") is None:
            b["props"] = {}
        p = b.get("props")
        if not isinstance(p, dict):
            continue
        if b.get("scene") == "Hero" and not p.get("art"):
            p["art"] = hero
        if b.get("scene") == "PriceList" and isinstance(p.get("cards"), list):
            for i, c in enumerate(p["cards"]):
                if isinstance(c, dict) and not c.get("art"):
                    c["art"] = bait if i == 0 else real
        for c in _cards(p):
            if "tag" in c and "tags" not in c:          # casta chyba modelov: tag namiesto tags
                t = c.pop("tag")
                c["tags"] = t if isinstance(t, list) else [t]
            if isinstance(c.get("tags"), (str, dict)):
                c["tags"] = [c["tags"]]
            for k in ("tags", "top", "badge", "stamp"):   # stitky su v dizajne vzdy VERZALKAMI (sablona ich nemeni)
                if k in c:
                    c[k] = _upper(c[k])
            sub, price = str(c.get("sub") or ""), str(c.get("price") or "")
            if sub and price and re.sub(r"\W", "", sub).lower() == re.sub(r"\W", "", price).lower():
                c.pop("sub")                                 # podtitulok = cena by bol na karte dvakrat
        for k in ("tag", "kicker", "job", "stamp", "labels", "tags", "thumbLabel", "label"):
            if k in p:
                p[k] = _upper(p[k])
    return story


def _upper(v):
    """Verzalky pre stitok: retazec, {"text": ..} alebo zoznam takych."""
    if isinstance(v, str):
        return v.upper()
    if isinstance(v, list):
        return [_upper(x) for x in v]
    if isinstance(v, dict) and isinstance(v.get("text"), str):
        return {**v, "text": v["text"].upper()}
    return v


def _cards(p):
    """Vsetky karty v props (PriceList cards, Compare before/after)."""
    out = []
    for key in ("cards", "before", "after"):
        out += [c for c in (p.get(key) or []) if isinstance(c, dict)]
    return out


def main():
    ap = argparse.ArgumentParser(description="Napise story.json pre jeden prípad z banky (free modely + lint, max 4 pokusy).")
    ap.add_argument("case_id")
    ap.add_argument("--out", required=True, help="napr. episodes/001-economist-decoy/story.json")
    ap.add_argument("--case-file", help="JSON s prípadom namiesto bank/cases.json")
    ap.add_argument("--fake", nargs="+", metavar="JSON", help="offline: odpovede modelu zo suborov (v poradi pokusov)")
    a = ap.parse_args()
    case = case_from_file(a.case_file, a.case_id) if a.case_file else case_by_id(a.case_id)
    if not case:
        print(f"prípad '{a.case_id}' sa nenašiel", file=sys.stderr)
        return 2
    icon_list = read_icon_names() or DEFAULT_ICONS
    icons = load_icons()   # None = icons.json chyba (varovanie na stderr), `art` sa nekontroluje
    system = build_prompt(case, icon_list)
    base = [{"role": "system", "content": system}, {"role": "user", "content": USER_MSG}]
    print(f"prípad {a.case_id}: prompt ~{est_tokens(base)} tokenov, faktov {len(case.get('facts') or [])}, "
          f"retazec {', '.join(b + ':' + m for b, m in CHAIN)}")
    prev, errs = None, []
    for attempt in range(1, ATTEMPTS + 1):
        try:
            if a.fake:
                f = Path(a.fake[min(attempt - 1, len(a.fake) - 1)])
                raw, model = f.read_text(encoding="utf-8"), "fake:" + f.name
            else:
                raw, model = ask(base, prev, errs)
        except ModelError as e:
            print(f"pokus {attempt}/{ATTEMPTS}: ziadny model nie je dostupny: {e}")
            return 2
        try:
            story = parse_json(raw)
            if not isinstance(story, dict):
                raise ValueError("JSON is not an object")
        except ValueError as ex:
            prev, errs = None, ["Your previous reply was not valid or complete JSON. Return the complete JSON object only; keep props minimal."]
            print(f"pokus {attempt}/{ATTEMPTS} model={model}: neplatny JSON ({str(ex)[:80]})")
            continue
        story = normalize(story, case)
        prev = story
        full = {"id": a.case_id, **story}   # id dopĺňa kod
        errs = lint(full, case, icons)
        print(f"pokus {attempt}/{ATTEMPTS} model={model}: {len(errs)} chyb")
        for e in errs:
            print("  -", e)
        if not a.fake:   # kazdy pokus ostane vedla story.json na diagnostiku (v cloude ide do artefaktu)
            save(str(Path(a.out).parent / "attempts" / f"{attempt}-{model.split(':')[0]}.json"),
                 {"model": model, "errors": errs, **full})
        if not errs:
            save(a.out, full)
            beats = full["beats"]
            print(f"{len(beats)} uderov, {sum(len(b['say'].split()) for b in beats)} slov")
            print("ULOZENE:", a.out)
            return 0
    print(f"autor nezvladol lint ani na {ATTEMPTS}. pokus", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
