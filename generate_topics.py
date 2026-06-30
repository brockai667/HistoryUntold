#!/usr/bin/env python3
"""Doplni banku tem cez GitHub Models (zadarmo). Nika: TECH & AI - zaujimave technologicke novinky."""
import json
import os
import re
import sys

import requests


try:
    import trends
except Exception:
    trends = None

# kde sa o technologiach a AI realne diskutuje / co je trending
TREND_SUBREDDITS = ['technology', 'artificial', 'Futurology', 'gadgets', 'singularity']
TREND_YT_QUERIES = ['tech news', 'ai news', 'new technology explained']


def _gather_trends():
    if trends is None:
        return []
    try:
        hl, meta = trends.gather(TREND_SUBREDDITS, TREND_YT_QUERIES, top=18, return_meta=True)
        if hl:
            print("Trendy: %d titulkov (Reddit=%d, YouTube=%d) -> temy z realneho dopytu." % (len(hl), meta["reddit"], meta["youtube"]))
        else:
            print("Trendy: zdroj nedostupny (Reddit=%d, YouTube=%d) -> klasicky." % (meta["reddit"], meta["youtube"]))
        return hl
    except Exception as e:
        print("Trendy preskocene:", str(e)[:120])
        return []


def _trend_block(trending):
    if not trending:
        return ""
    joined = "\n".join("- " + t for t in trending)
    return (
        "\nWHAT THE TECH WORLD IS TALKING ABOUT RIGHT NOW (live trending headlines from tech/AI "
        "communities and top tech YouTube videos - what people actually click on this week):\n"
        + joined + "\n"
        "IMPORTANT: at least HALF of the generated topics MUST be directly inspired by a specific, "
        "high-curiosity item above - take the most surprising/intriguing ones and turn them into "
        "original, scroll-stopping hooks. Do NOT copy a headline word-for-word, do NOT mention "
        "Reddit or YouTube, and stay accurate.\n"
    )


ROOT = os.path.dirname(os.path.abspath(__file__))
BANK = os.path.join(ROOT, "topics_bank.json")
STATE = os.path.join(ROOT, "used_topics.json")

TARGET = int(os.environ.get("TOPICS_TARGET", "15"))
MODEL = os.environ.get("MODELS_MODEL", "openai/gpt-4o-mini")
BASE = os.environ.get("MODELS_BASE_URL", "https://models.github.ai/inference")
TOKEN = os.environ.get("MODELS_TOKEN") or os.environ.get("GITHUB_TOKEN")

SYSTEM = ("You are a viral short-form scriptwriter for a TECH & AI brand that explains the most "
          "fascinating things in technology - new AI tools, breakthroughs, gadgets, how famous tech "
          "actually works, and mind-blowing true tech facts. Punchy, curious, hype-but-credible voice. "
          "ACCURACY MATTERS: use only real, widely-known, well-established tech facts and concepts. "
          "NEVER invent product names, specs, numbers, dates or fake 'news'; if unsure, pick a "
          "well-known true fact instead. No rumors stated as fact. You output strict JSON, nothing else. "
          "THE HOOK (segment 1) is the single most important line: it MUST stop the scroll in 2 seconds "
          "with a concrete, surprising claim - a number, a name, or a sharp contradiction - and open a "
          "curiosity gap that can only be closed by watching to the end. Lead with the most shocking part "
          "FIRST. Forbidden openers: 'Did you know', 'Have you ever', 'Imagine', 'Here are', 'In this video'.")

EXAMPLE = {
    "title": "The Tiny Chip Behind Every AI",
    "segments": [
        {"text": "Almost every AI you use runs on the same kind of chip.", "keywords": "computer chip processor macro"},
        {"text": "They're called GPUs, and they do billions of calculations at once.", "keywords": "circuit board glowing"},
        {"text": "They were first built to render video games.", "keywords": "gaming graphics card"},
        {"text": "But that same power turned out perfect for training AI.", "keywords": "data center servers"},
        {"text": "Now a single AI model can use thousands of them at once.", "keywords": "futuristic technology blue"},
        {"text": "Which made these chips some of the most valuable tech on Earth.", "keywords": "stock market technology"},
        {"text": "Follow for daily tech and AI news.", "keywords": "person using smartphone"},
    ],
    "description": "The chips behind modern AI were first built for gaming. Follow for daily tech news! 🤖",
    "hashtags": ["#technology", "#ai", "#tech", "#artificialintelligence", "#gadgets", "#technews", "#shorts", "#fyp"],
}


def build_prompt(n, existing_titles, trending=None):
    trend_block = _trend_block(trending)
    return (
        f"Generate {n} NEW faceless short-form video topics for a TECH & AI brand "
        "(TikTok / Reels / YouTube Shorts).\n"
        "Niche: fascinating technology and AI - new AI tools and breakthroughs, how famous tech actually "
        "works, jaw-dropping true tech facts, gadgets, the future of tech, big tech stories.\n"
        "Return ONLY a JSON array (no markdown). Each item EXACTLY this schema:\n"
        f"{json.dumps(EXAMPLE, ensure_ascii=False, indent=2)}\n\n"
        "Rules (make it feel PRO, VIRAL and genuinely informative):\n"
        "- title: punchy, curiosity-driven, e.g. 'The AI That Writes Its Own Code', 'Why Your Phone "
        "Charges Slower Over Time'.\n"
        "- 6 to 9 segments. Segment 1 is THE HOOK: a surprising true tech fact under 14 words that stops "
        "the scroll. Never start with 'Did you know'.\n"
        "- explain it clearly line by line; write for an energetic, clear SPOKEN voiceover: short sentences.\n"
        "- ACCURACY MATTERS: only real, established tech/AI facts. NEVER invent product names, specs, "
        "numbers or fake news. If unsure, choose a well-known true fact. No rumors as fact.\n"
        "- each segment 'keywords': 1-3 ENGLISH words for real Pexels footage that VISUALLY MATCHES the line "
        "(e.g. 'computer chip macro', 'data center servers', 'robot arm', 'smartphone screen', 'code on "
        "screen', 'futuristic technology', 'electric car'). Concrete and cinematic, never abstract.\n"
        "- the SECOND-TO-LAST segment should loop back to the opening hook so a rewatch feels seamless.\n"
        "- the LAST segment text MUST be exactly: 'Follow for daily tech and AI news.'\n"
        "- description: one punchy sentence ending with 'Follow for daily tech news!'.\n"
        "- About half the time, add ONE fitting emoji at the very END of the description (e.g. 🤖, ⚡, 📱, 🚀). "
        "Emoji ONLY in the description text, NEVER inside any segment 'text' (spoken captions).\n"
        "- hashtags: 6-8 tags including #technology #ai #tech #shorts #fyp.\n"
        f"- Do NOT reuse any of these existing titles: {existing_titles}\n"
        "- HOOK RULE (critical for retention): segment 1 must be the single most shocking, "
        "curiosity-gap opener that makes the viewer unable to scroll. Under 10 words, no "
        "setup, lead with the most surprising fact or claim.\n"
        + trend_block +
        "Return ONLY the JSON array."
    )


def call_model(user_text):
    r = requests.post(
        BASE.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        json={"model": MODEL, "temperature": 0.9,
              "messages": [{"role": "system", "content": SYSTEM},
                           {"role": "user", "content": user_text}]},
        timeout=180,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Models API {r.status_code}: {r.text[:500]}")
    return r.json()["choices"][0]["message"]["content"]


def extract_json(s):
    s = s.strip()
    s = re.sub(r"^```(?:json)?", "", s).strip()
    s = re.sub(r"```$", "", s).strip()
    a, b = s.find("["), s.rfind("]")
    if a != -1 and b != -1:
        s = s[a:b + 1]
    return json.loads(s)


def valid(t):
    if not isinstance(t, dict) or "title" not in t or "segments" not in t:
        return False
    if not isinstance(t["segments"], list) or len(t["segments"]) < 4:
        return False
    for seg in t["segments"]:
        if "text" not in seg or "keywords" not in seg:
            return False
    t.setdefault("description", t["title"] + " Follow for daily tech news!")
    t.setdefault("hashtags", ["#technology", "#ai", "#tech", "#shorts", "#fyp"])
    return True


def main():
    if not TOKEN:
        print("CHYBA: chyba MODELS_TOKEN/GITHUB_TOKEN"); sys.exit(1)
    bank = json.load(open(BANK, encoding="utf-8"))
    used = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else []
    titles = {t["title"] for t in bank}
    unused = [t for t in bank if t["title"] not in used]
    need = TARGET - len(unused)
    if need <= 0:
        print(f"Banka OK: {len(unused)} nepouzitych tem."); return
    print(f"Generujem ~{need} novych tem cez {MODEL}...")
    trending = _gather_trends()
    items = extract_json(call_model(build_prompt(need + 3, sorted(titles), trending)))
    added = 0
    for t in items:
        if not valid(t) or t["title"] in titles:
            continue
        bank.append(t); titles.add(t["title"]); added += 1
    json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Pridanych {added} tem. Banka ma {len(bank)} tem.")


if __name__ == "__main__":
    main()
