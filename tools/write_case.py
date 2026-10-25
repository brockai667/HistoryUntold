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
from lint import SCENES, lint, lint_story, load_icons, read_icon_names  # noqa: E402

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
ATTEMPTS = 4          # pokusy stavby props (kazdy dalsi so zoznamom chyb)
STORY_ATTEMPTS = 3    # pokusy pribehu (krok 1)
SCENE_BY_LOWER = {s.lower(): s for s in SCENES}
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

# Autor pise v dvoch krokoch: 1) PRIBEH = len hlas po uderoch + plan (model sa sustredi na rozpravanie, lint_story ho
# skontroluje), 2) STAVBA = props k schvalenemu hlasu (texty `say` sa po odpovedi prepisu schvalenym znenim).
HEAD = '''You write one episode of "PLAIN SIGHT": a 50–65 second vertical video (TikTok/Reels). Calm male voice, short spoken
sentences, dry wit. The screen is a paper price report: price cards on beige paper and one dark-blue "blueprint" moment
when the trick is exposed. THE SCREEN SHOWS THE DATA (cards, prices, tags). THE VOICE TELLS A STORY ABOUT IT.

CASE: {case}   TRICK: {trick}
SUBJECT: {subject}
FACTS (the only facts, names and numbers you may use – quote numbers exactly as written, never add others):
{facts}
LESSON: {lesson}
SOURCE: {source}
'''

STORY_GUIDE = '''
== WHAT MAKES AN EPISODE GOOD ==
It is a tiny mystery with a payoff, not a list of facts. In the first 3 seconds the viewer thinks "wait, why?", and
gets the answer by second 30. Every beat moves the story one step forward. The voice never reads a card aloud –
the card is already on screen; the voice says what it MEANS, what is strange about it, or what happens next.

BAD (reads the cards, narrates the screen, numbers without context, repeats itself – all of this was rejected):
  "The basic plan costs $20 a month for one user."   "First, a basic plan appears. Next, a pro plan shows up."
  "Basic 32, pro 68."   "Bundles push choices." ... "Bundles push choices. Follow for more."
GOOD: see the gold example.

== GOLD EXAMPLE (a different case – copy its rhythm and story moves, never its content) ==
Hero      | This car flies. And it isn't for sale.
PriceList | But it's the first thing on the price list.
PriceList | No price. Invite only. Below it, a race version you can only reserve.
PriceList | And at the bottom, the one you can actually buy.
PriceList | Nobody owns the flying one. Looks useless.
PriceList | But it does a job. It's a decoy.
Statement | Actually, it has two jobs.
Views     | Job one: get watched. A flying car pulls a million views, free ads for the whole lineup.
Anchor    | Job two: it moves the anchor. Alone, $50,000 feels expensive.
Anchor    | Float a flying car above it, and the same price starts to sound reasonable.
Compare   | You see it everywhere. A bakery adds a $1,900 cake for two hundred guests.
Compare   | A coach adds a VIP plan, by application only.
Compare   | Suddenly, $300 a month isn't pricey. It's the smart choice.
Outro     | If something isn't for sale, ask what it's selling. Follow for more.
Why it works: the hook is a paradox without numbers; each card gets its own beat and the voice comments on it ("the
one you can actually buy") instead of reading it; "Looks useless." sets up the twist "But it does a job."; the
mechanism gets its own beats and names the cause (the flying car above it); the transfer starts with "You see it
everywhere."; the final rule is said once, at the end.

== STORY SKELETON – fill it with THIS case (12 to 15 beats in this order) ==
1. HOOK (Hero, 1 beat): the paradox of THIS case in at most 12 words and at most one number. Shape: "<thing> <does
   something strange>. And <the strange part>." No intro, no question, no "today", do not name the trick yet.
2. THE PRICE LIST (PriceList, 3–4 beats): the seller's real options, one per beat, the odd/bait option first.
   NO NUMBERS AND NO PRICES IN ANY PriceList BEAT – the cards show them. For each option say in your own words what
   you get, what is missing or how it relates to the others ("Same money, half the stuff." / "The one you can
   actually buy."), never "<title>, <price>, <feature>." The prices are spoken later, in the mechanism.
3. THE ODD PART (PriceList, 1 beat): the fact from FACTS that makes no sense, then a 2–3 word verdict
   ("Looks useless." / "Looks like a mistake." / "Sounds generous.").
4. THE TWIST (PriceList, 1 beat, shown in blueprint): "But it does a job." or similar + name the trick in plain words.
5. THE MECHANISM (2–3 beats; Statement, Anchor and/or Views): WHY it works, in the viewer's language. Name the real
   cause – exactly WHICH option creates the effect and how. The evidence numbers from FACTS belong here.
6. EVERYWHERE (Compare, 2–3 beats): "You see it everywhere." (or similar), then one or two everyday businesses
   (bakery, gym, café, cinema, barber, app, hotel...) using EXACTLY THE SAME TRICK with invented, realistic prices
   that make the trick work. The last Compare beat says why the pushed option now feels smart.
7. RULE (Outro, last beat): one short rule the viewer can use next time + "Follow for more." Said only here.

== NARRATION RULES ==
- Never repeat yourself: no sentence, no phrase of 4 or more words and no idea appears twice. A number may be spoken
  in at most 2 beats – the card keeps showing it, the voice does not need to say it again.
- Every number needs its context in the same sentence (who did what): not "Basic 32, pro 68." but "Take the odd
  option away, and only 32 still choose the bundle."
- Do not narrate the screen ("First, X appears. Next, Y shows up. Finally..."). Talk about the options themselves.
- Length: 95 to 135 spoken words in total. Reach it with story steps, never with repetition or padding.
- One beat = 1–2 short sentences, 3–20 words; numbers as digits with $ or %.
- Numbers, names and years only from FACTS (invented prices only in the everyday Compare beats). Never invent how the
  seller presented it (no made-up badges, labels, slogans, colours, "most popular" tags or quotes).
- Everyday prices must make the trick work: the odd option is clearly worse than the pushed option for the same or
  almost the same money (decoy), or far more expensive (anchor); the cheap option stays clearly cheaper. Never give
  all options the same price.
- Capitalized names only as they appear in FACTS. Second person, present tense, no filler, no "imagine", no emoji,
  straight quotes only.
'''

PROPS_GUIDE = '''
ICONS you may use as "art": {icons}   Suggested: hero {icon_hero}, bait/odd card {icon_bait}, real choice {icon_real}

== HOW THE SCENES ARE BUILT ==
- Hero: "title" = 2–3 words of the paradox, "tag" = a short label, "art" = icon.
- PriceList: cards appear top-down, one new card per beat; every beat repeats the full previous state and adds one
  thing (a card, a tag); never reorder, rename or remove a card. The odd/bait card is first with "priceRed": true.
  The twist beat has "mode": "blueprint" and "stamp": "<ONE WORD FOR THE TRICK>" on the odd card.
- Statement: "kicker" + 1–2 tags "JOB 1 · ..." (≤ 28 chars), or a short "text" (≤ 7 words). May use "mode": "blueprint".
- Anchor = the same price first feels expensive, then reasonable. Beat A: {"price": X, "at": 0.6, "split": 0.4}
  (EXPENSIVE side). Beat B: same price and "at", "split": 0.8 and "anchor": {"label": "what moved it", "art": icon}
  (now REASONABLE). Only for a price – never for percentages or counts.
- Views = one number counting up from "from" to "value" (counts, shares, people, views from FACTS).
- Compare: before = [null, option, option]; after = [odd option on top with "top": {"text": "<DECOY, BAIT, EXTREME or
  another word that fits THIS trick>", "tone": "red"}, the same two options]. Keep before/after identical between
  Compare beats of the same business; only "badge" and "top" may change. The last Compare beat gives the pushed
  option "badge": {"text": "SMART CHOICE", "tone": "green"}. No brand names.
- Outro: props {}.
- RED only for the odd/bait card (priceRed, stamp) and the red "top" tag in Compare. Everything else plain, dark,
  blue, yellow or green. Tags on the real case's cards only when FACTS mention them.
- Card text limits: title ≤ 18 chars, sub ≤ 22, price ≤ 12, tag ≤ 16, ≤ 3 tags; in Compare title ≤ 16, price ≤ 8.

Scene props (JSON shapes):
{schemas}
'''

STORY_OUT = '''
== OUTPUT ==
Write ONLY the narration now (no props yet). Fill "plan" first – it is your thinking, not shown in the video.
Return ONLY JSON:
{"plan": {"paradox": "the strange thing in one line", "odd_fact": "...", "twist": "what the odd option really does",
"cause": "which option creates the effect and how", "everyday": "business, its 3 options with prices, why the pushed
one wins", "rule": "..."},
"beats": [{"scene": "Hero", "say": "..."}, {"scene": "PriceList", "say": "..."}, ...]}
Scenes: Hero, PriceList, Views, Anchor, Compare, Statement, Outro (first Hero, last Outro, 12 to 15 beats).'''

BUILD_OUT = '''
== THE NARRATION IS WRITTEN AND APPROVED ==
{narration}
STORY PLAN: {plan}

Your job now is the props. Build exactly these beats in this order, with exactly these scenes and these "say" texts
copied word for word. Cards, prices and tags must match what the voice says in that beat.

== OUTPUT ==
Return ONLY JSON: {"case": "2-3 WORDS UPPER CASE", "title": "post title ≤ 60 chars", "caption": "1-2 lines for the post",
"source": "{source}", "beats": [ {"say": "...", "scene": "...", "props": {...}, "mode": "blueprint" (optional), "hold": 4 (optional)} ]}'''

STORY_PROMPT = HEAD + STORY_GUIDE + STORY_OUT
PROMPT = HEAD + PROPS_GUIDE + BUILD_OUT

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
FIX_PREV_MSG = ("Fix exactly these problems and return the complete corrected JSON (keep the story and the skeleton; if the "
                "total word count is too low, add a missing story step from the skeleton – never repeat a sentence, "
                "a phrase or a number):\n- ")

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
            "HTTP-Referer": "https://github.com/brockai667", "X-Title": "PlainSight"})
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


def build_prompt(case, icon_list, template=None, extra=None):
    ic = case.get("icons") or {}
    subs = {"schemas": SCHEMAS, "case": case.get("case", ""), "trick": case.get("trick", ""),
            "subject": case.get("subject", ""), "facts": "\n".join("- " + f for f in case.get("facts") or []),
            "lesson": case.get("lesson", ""), "source": case.get("source", ""), "icons": ", ".join(icon_list),
            "icon_hero": ic.get("hero", "none"), "icon_bait": ic.get("bait", "none"), "icon_real": ic.get("real", "none")}
    text = template or PROMPT
    for k, v in subs.items():
        text = text.replace("{" + k + "}", str(v))
    for k, v in (extra or {}).items():   # schvaleny hlas a plan az nakoniec (ich text sa uz nenahradza)
        text = text.replace("{" + k + "}", str(v))
    return text


def write_story(case, icon_list, out_dir, fake=None):
    """Krok 1: len hlas po uderoch + plan. Vrati (beats [{scene, say}], plan) alebo (None, None)."""
    base = [{"role": "system", "content": build_prompt(case, icon_list, STORY_PROMPT)},
            {"role": "user", "content": "Write the narration now. Return ONLY the JSON object."}]
    prev, errs = None, []
    for attempt in range(1, STORY_ATTEMPTS + 1):
        try:
            raw, model = (Path(fake).read_text(encoding="utf-8"), "fake") if fake else ask(base, prev, errs)
            st = parse_json(raw)
            if not isinstance(st, dict):
                raise ValueError("JSON is not an object")
        except ModelError as e:
            print(f"pribeh {attempt}/{STORY_ATTEMPTS}: ziadny model nie je dostupny: {e}")
            return None, None
        except ValueError as ex:
            prev, errs = None, ["Your previous reply was not valid or complete JSON. Return the complete JSON object only."]
            print(f"pribeh {attempt}/{STORY_ATTEMPTS}: neplatny JSON ({str(ex)[:80]})")
            continue
        st = _walk(st, lambda s: s.translate(CURLY))
        beats = [{"scene": _scene(b.get("scene")), "say": re.sub(r"(\d) %", r"\1%", " ".join(str(b.get("say") or "").split()))}
                 for b in st.get("beats") or [] if isinstance(b, dict)]
        st["beats"] = beats
        prev = st
        errs = lint_story(st, case)
        print(f"pribeh {attempt}/{STORY_ATTEMPTS} model={model}: {len(errs)} chyb")
        for e in errs:
            print("  -", e)
        if not fake:
            save(str(out_dir / "attempts" / f"story-{attempt}-{model.split(':')[0]}.json"), {"model": model, "errors": errs, **st})
        if not errs:
            return beats, st.get("plan")
    return None, None


def _scene(v):
    """Nazov sceny bez ohladu na velkost pismen (model obcas pise "priceList")."""
    return SCENE_BY_LOWER.get(v.lower(), v) if isinstance(v, str) else v


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
        b["scene"] = _scene(b.get("scene"))
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
    ap.add_argument("--fake-story", metavar="JSON", help="offline: odpoved modelu pre krok 1 (pribeh)")
    a = ap.parse_args()
    case = case_from_file(a.case_file, a.case_id) if a.case_file else case_by_id(a.case_id)
    if not case:
        print(f"prípad '{a.case_id}' sa nenašiel", file=sys.stderr)
        return 2
    icon_list = read_icon_names() or DEFAULT_ICONS
    icons = load_icons()   # None = icons.json chyba (varovanie na stderr), `art` sa nekontroluje
    print(f"prípad {a.case_id}: faktov {len(case.get('facts') or [])}, retazec {', '.join(b + ':' + m for b, m in CHAIN)}")
    out_dir = Path(a.out).parent
    lines, plan = write_story(case, icon_list, out_dir, a.fake_story)
    if lines is None:
        print(f"autor nenapisal pribeh ani na {STORY_ATTEMPTS}. pokus", file=sys.stderr)
        return 2
    narration = "\n".join(f"{i}. {b['scene']} | {b['say']}" for i, b in enumerate(lines, 1))
    system = build_prompt(case, icon_list, PROMPT, {"narration": narration,
                                                    "plan": json.dumps(plan, ensure_ascii=False)})
    base = [{"role": "system", "content": system}, {"role": "user", "content": USER_MSG}]
    print(f"stavba: prompt ~{est_tokens(base)} tokenov, {len(lines)} uderov")
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
        story.pop("plan", None)
        story = normalize(story, case)
        sb = story.get("beats")
        if isinstance(sb, list) and len(sb) == len(lines):   # schvaleny hlas vyhrava nad prepisom modelu
            for b, ln in zip(sb, lines):
                if isinstance(b, dict):
                    b["say"], b["scene"] = ln["say"], ln["scene"]
        prev = story
        full = {"id": a.case_id, **story}   # id dopĺňa kod
        errs = lint(full, case, icons)
        if not isinstance(sb, list) or len(sb) != len(lines):
            errs.insert(0, f"beats must be exactly the {len(lines)} approved beats in order (got {len(sb) if isinstance(sb, list) else 0})")
        print(f"pokus {attempt}/{ATTEMPTS} model={model}: {len(errs)} chyb")
        for e in errs:
            print("  -", e)
        if not a.fake:   # kazdy pokus ostane vedla story.json na diagnostiku (v cloude ide do artefaktu)
            save(str(Path(a.out).parent / "attempts" / f"{attempt}-{model.split(':')[0]}.json"),
                 {"model": model, "errors": errs, "plan": plan, **full})
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
