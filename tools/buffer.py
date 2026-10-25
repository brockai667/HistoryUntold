# -*- coding: utf-8 -*-
"""Plain Sight -> Buffer (TikTok, Instagram Reels, YouTube Shorts). Port z NextByte push_to_buffer.py.
Video sa neprenasa: Buffer si ho stiahne z GitHub Release ep-NNN (verejne repo, octet-stream Buffer berie).
Token len z env BUFFER_TOKEN (GitHub secret, plati 90 dni, obnovuje Damian), nikdy sa nevypisuje.
    python tools/buffer.py --check      # len over token (nic nepostne)"""
import argparse
import datetime as dt
import os
import random
import sys

import requests

API = "https://api.buffer.com"
# kanaly byvalej NextByte (Buffer ucet +history, handle historyuntold667 -> plainsight667); ID nie su tajne
CHANNELS = [
    {"id": "6a3f7eef5ab6d2f106797a72", "service": "tiktok"},
    {"id": "6a3f7ec15ab6d2f1067979fd", "service": "instagram"},
    {"id": "6a3f7ed05ab6d2f106797a1d", "service": "youtube"},
]
SLOT_HOUR = 8           # Europe/Bratislava rano (Damian 25.10.; USA je vtedy v noci), jeden post denne
YT_CATEGORY = "27"      # Education


class BufferAuthError(RuntimeError):
    pass


def tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Europe/Bratislava")
    except Exception:   # Windows bez tzdata: priblizne (zimny cas)
        return dt.timezone(dt.timedelta(hours=1))


def gql(query, variables=None):
    token = os.environ.get("BUFFER_TOKEN", "").strip()
    if not token:
        raise BufferAuthError("BUFFER_TOKEN chýba")
    for attempt in (1, 2):   # opakuje sa len nepripojenie (poziadavka neodisla) - inak hrozi dvojity post
        try:
            r = requests.post(API, json={"query": query, "variables": variables or {}}, timeout=(10, 60),
                              headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
            break
        except requests.exceptions.ConnectTimeout:
            if attempt == 2:
                raise
    if r.status_code in (401, 403):
        raise BufferAuthError(f"Buffer odmietol token (HTTP {r.status_code}) - obnov BUFFER_TOKEN")
    r.raise_for_status()
    data = r.json()
    errs = data.get("errors") or []
    if errs and not any((data.get("data") or {}).values()):
        msg = "; ".join(str(e.get("message", e)) for e in errs)[:300]
        codes = {str((e.get("extensions") or {}).get("code", "")).upper() for e in errs if isinstance(e, dict)}
        auth_words = ("unauthorized", "unauthenticated", "authentication", "expired")
        if codes & {"UNAUTHENTICATED", "UNAUTHORIZED"} or any(w in msg.lower() for w in auth_words):
            raise BufferAuthError(f"Buffer: {msg}")
        raise RuntimeError(f"Buffer: {msg}")
    return data.get("data") or {}


def check():
    """Token platny? Vola sa pred renderom, aby beh s prepadnutym tokenom nespotreboval pripad."""
    gql("query { account { id } }")


def mutation(service):
    title_var = ", $title: String!" if service in ("youtube", "tiktok") else ""
    meta = {
        "instagram": "{ instagram: { type: reel, shouldShareToFeed: true } }",
        "youtube": f'{{ youtube: {{ title: $title, categoryId: "{YT_CATEGORY}", privacy: public }} }}',
        "tiktok": "{ tiktok: { title: $title } }",
    }[service]
    return f"""mutation($channelId: ChannelId!, $text: String!, $url: String!, $dueAt: DateTime!{title_var}) {{
  createPost(input: {{ channelId: $channelId, text: $text, schedulingType: automatic, mode: customScheduled,
    dueAt: $dueAt, assets: [{{ video: {{ url: $url }} }}], metadata: {meta} }}) {{
    ... on PostActionSuccess {{ post {{ id }} }}
    ... on MutationError {{ message }}
  }}
}}"""


def next_slot(after=None):
    """Najblizsi den o SLOT_HOUR (+2-27 min), aspon 30 min od teraz a neskor nez `after` (iny den nez posledny post)."""
    now = dt.datetime.now(tz())
    day = now.date()
    if after:
        day = max(day, after.astimezone(tz()).date() + dt.timedelta(days=1))
    while True:
        due = dt.datetime.combine(day, dt.time(SLOT_HOUR, random.randint(2, 27)), tzinfo=tz())
        if due >= now + dt.timedelta(minutes=30):
            return due.astimezone(dt.timezone.utc)
        day += dt.timedelta(days=1)


def post(url, title, text, due, skip=()):
    """Naplanuje video na vsetky kanaly okrem `skip`. Vrati zoznam sluzieb, kde to preslo; chyby len vypise
    (aj prepadnuty token - uz naplanovane siete sa tak nestratia a dalsi beh ich neposle znova)."""
    done = []
    iso = due.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    for ch in CHANNELS:
        s = ch["service"]
        if s in skip:
            continue
        v = {"channelId": ch["id"], "text": text, "url": url, "dueAt": iso}
        if s in ("youtube", "tiktok"):
            v["title"] = title[:100]
        try:
            res = gql(mutation(s), v).get("createPost") or {}
        except BufferAuthError as e:
            print(e)
            break
        except Exception as e:   # bez opakovania: post mohol vzniknut aj pri timeoute
            print(f"Buffer {s}: zlyhalo: {str(e)[:200]}")
            continue
        if res.get("post"):
            print(f"Buffer {s}: naplánované {iso} (post {res['post']['id']})")
            done.append(s)
        else:
            print(f"Buffer {s}: {res.get('message', res)}")
    return done


def main():
    ap = argparse.ArgumentParser(description="Plain Sight -> Buffer")
    ap.add_argument("--check", action="store_true", help="len over token")
    a = ap.parse_args()
    if a.check:
        try:
            check()
        except Exception as e:
            sys.exit(f"Buffer: {e}")
        print("Buffer token OK")


if __name__ == "__main__":
    main()
