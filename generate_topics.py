#!/usr/bin/env python3
"""Doplni banku tem cez GitHub Models (zadarmo). Nika: HISTORIA / historicke fakty."""
import json
import os
import re
import sys

import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
BANK = os.path.join(ROOT, "topics_bank.json")
STATE = os.path.join(ROOT, "used_topics.json")

TARGET = int(os.environ.get("TOPICS_TARGET", "15"))
MODEL = os.environ.get("MODELS_MODEL", "openai/gpt-4o-mini")
BASE = os.environ.get("MODELS_BASE_URL", "https://models.github.ai/inference")
TOKEN = os.environ.get("MODELS_TOKEN") or os.environ.get("GITHUB_TOKEN")

SYSTEM = ("You are a viral short-form scriptwriter for a HISTORY brand. You tell surprising, TRUE "
          "stories and facts from real history in a gripping, documentary voice. ACCURACY IS SACRED: "
          "use only real, widely-documented historical facts, events, people and dates. NEVER invent "
          "facts, quotes, dates or statistics; if you are not confident something is true, leave it out. "
          "No conspiracy theories presented as fact. You output strict JSON, nothing else.")

EXAMPLE = {
    "title": "The Library That Burned for Centuries",
    "segments": [
        {"text": "The Library of Alexandria didn't burn down in a single night.", "keywords": "ancient library ruins"},
        {"text": "It declined slowly over centuries, through fires, cuts and neglect.", "keywords": "old scrolls candlelight"},
        {"text": "At its peak it may have held hundreds of thousands of scrolls.", "keywords": "ancient egypt temple"},
        {"text": "Scholars from across the ancient world came to study there.", "keywords": "roman statue marble"},
        {"text": "When it was gone, knowledge that took centuries to gather was lost.", "keywords": "burning fire embers"},
        {"text": "And we still don't know everything it once contained.", "keywords": "ancient ruins sunset"},
        {"text": "Follow for history they never taught you.", "keywords": "old world map"},
    ],
    "description": "The Library of Alexandria didn't vanish in one fire - it faded over centuries. Follow for daily history!",
    "hashtags": ["#history", "#ancient", "#alexandria", "#historyfacts", "#didyouknow", "#shorts", "#fyp", "#learnontiktok"],
}


def build_prompt(n, existing_titles):
    return (
        f"Generate {n} NEW faceless short-form video topics for a HISTORY brand "
        "(TikTok / Reels / YouTube Shorts).\n"
        "Niche: surprising TRUE historical facts, forgotten events, wild real stories, ancient "
        "civilizations, historical figures, 'things they never taught you in school'.\n"
        "Return ONLY a JSON array (no markdown). Each item EXACTLY this schema:\n"
        f"{json.dumps(EXAMPLE, ensure_ascii=False, indent=2)}\n\n"
        "Rules (make it feel PRO, VIRAL and genuinely educational):\n"
        "- title: punchy and curiosity-driven, e.g. 'The Emperor Who Declared War on the Sea', "
        "'Why Romans Brushed Their Teeth With This'.\n"
        "- 6 to 9 segments. Segment 1 is THE HOOK: a surprising true fact under 14 words that stops the "
        "scroll. Never start with 'Did you know'.\n"
        "- build the story line by line; write for a deep, documentary SPOKEN voiceover: short, clear sentences.\n"
        "- ACCURACY IS SACRED: only real, widely-documented history. NEVER invent facts, dates, quotes or "
        "numbers. If unsure, pick a different well-known fact. No myths or conspiracies stated as fact.\n"
        "- each segment 'keywords': 1-3 ENGLISH words for real Pexels footage that VISUALLY MATCHES the line "
        "(e.g. 'ancient roman ruins', 'old map parchment', 'medieval castle', 'egyptian pyramids', "
        "'marble statue'). Cinematic and concrete, never abstract.\n"
        "- the SECOND-TO-LAST segment should loop back to the opening hook so a rewatch feels seamless.\n"
        "- the LAST segment text MUST be exactly: 'Follow for history they never taught you.'\n"
        "- description: one punchy sentence ending with 'Follow for daily history!'.\n"
        "- hashtags: 6-8 tags including #history #historyfacts #shorts #fyp.\n"
        f"- Do NOT reuse any of these existing titles: {existing_titles}\n"
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
    t.setdefault("description", t["title"] + " Follow for daily history!")
    t.setdefault("hashtags", ["#history", "#historyfacts", "#shorts", "#fyp"])
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
    items = extract_json(call_model(build_prompt(need + 3, sorted(titles))))
    added = 0
    for t in items:
        if not valid(t) or t["title"] in titles:
            continue
        bank.append(t); titles.add(t["title"]); added += 1
    json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Pridanych {added} tem. Banka ma {len(bank)} tem.")


if __name__ == "__main__":
    main()
