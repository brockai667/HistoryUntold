# PriceTrap Script Guide

How to write the spoken narration for one PriceTrap episode (TikTok / Reels / Shorts, 1080x1920, 40-55 s,
voice: Groq Orpheus "troy"). Followed by the Claude routine and by the free-model fallback. Every rule is meant to be
checked, not interpreted. Scene props and card limits live in `SPEC.md`; this file is only about the words.

Scenes you can use: `Hero`, `PriceList`, `Crowd`, `Anchor`, `Compare`, `Statement`, `Outro`.

---

## 1. Audience

- **Who:** English-speaking viewers aged 16-30 (core 18-25). Students and people in their first jobs, spending their own
  money on coffee, cinema, fast food, phone plans, apps, streaming, gym, sneakers, tickets, delivery and flights.
- **Situation:** scrolling in spare minutes (bus, queue, bed). Half watch muted at first. They leave in 2 seconds if the
  first frame and first line are not about them.
- **What they know:** prices, sizes, combos, "sale" stickers, subscriptions, checkout screens. They do NOT know any
  marketing or psychology words (decoy, anchoring, charm pricing, bundling, loss leader).
- **What they care about:** not getting ripped off, feeling smart, a few dollars saved, and a fact they can tell friends.
- **Reading level:** a 12-year-old. Short everyday words. If a kid would not say it, do not write it.
- **The one feeling they leave with:** "Wait, that happened to me. Now I can see the trick." (Caught it. Not scammed,
  not lectured. Ready to spot it next time.)

These are assumptions. Check them after 10 episodes against 3-second hold, average % viewed and comments.

---

## 2. Voice rules

1. **Talk to "you".** The viewer is the main character. The company is only the place where it happened.
2. **Short sentences.** One idea per sentence. Every sentence 12 words or fewer. Every spoken line (beat) 3-24 words.
3. **Concrete objects.** Popcorn, a coffee cup, the paper version, a checkout screen. Never "a product", "an offering",
   "consumers", "value".
4. **Plain words first, the name after.** Describe the trick in plain words before you ever name it, and name it once:
   "a fake option" ... later "That's the decoy effect." Never use a term the viewer has not just heard explained.

   | Never say first | Say this instead |
   |---|---|
   | decoy | a fake option / a useless option |
   | anchor, anchoring | a high price shown first, so the next one looks cheap |
   | charm pricing | prices that end in 99 |
   | bundle, combo, package | the option's real name from the facts ("print plus web") |
   | loss leader | sold cheap, even at a loss, to get you in the door |
   | perceived value | how good it feels |
   | tier, plan, SKU | option |
   | upsell | pushing you to the bigger one |
   | drip pricing, junk fees | fees added at checkout |

5. **One name per thing.** Call each option exactly what the facts call it, every time. "Print plus web" stays
   "print plus web". No swapping to "the bundle" or "the combo".
6. **Clear "it".** "It" must point to the last thing named. If two things were just named, repeat the name.
7. **No hype words:** insane, crazy, mind-blowing, shocking, genius, literally, unbelievable, game-changer, hack, secret,
   epic, wild.
8. **No filler:** "Here's the thing", "Let that sink in", "Believe it or not", "It turns out", "The truth is", "Did you
   know", "Fun fact", "Imagine", "Today", "In this video", "Let's dive in", "Simply put", "At the end of the day",
   "And that's not all", "Follow for more" (the on-screen outro already says it).
9. **Written for the voice:** numbers as digits with `$` (`$59`, `$7.50`), cents only as `.50`. No parentheses, em dashes,
   semicolons, slashes, `&`, `+` or "vs" in spoken lines (say "plus", "or"). No ALL CAPS words. At most 2 "!" per script.
   Every line ends with `.` `?` or `!`.
10. **Fun = surprise and callbacks, not jokes.** A short reaction line is fine ("Large, obviously.", "Nobody."). The
    last beats reuse the hook's object or word.

### Facts and numbers

- Use only the names and numbers in the case facts. Numbers 1-3 are free.
- Exception: the everyday example (`Compare` beats) uses invented, simple prices (whole dollars or .50, under $20)
  and no brand names.
- Say each fact number in at most 2 beats. Say each price once, when its card appears. After that say "the same price".
- At most 1 number per sentence ("84 of 100" counts as one).
- Never add what the facts do not say: no badges, slogans, colors, dates, company reasons, "most people" claims.
  Do not say people "switched" unless the facts say the same people changed their minds. ("Without the fake option,
  68 picked web-only" is safe. "68 students switched" is not.)

---

## 3. Hooks

### Rules (all must pass)

1. It is beat 1 and the first words of the video. No intro before it.
2. 12 words or fewer.
3. About the viewer's own life: contains "you"/"your" or starts with "Ever" / "Have you" / "Why does". It describes
   something they really did or saw (cinema, coffee shop, fast food, supermarket, phone plan, app, gym, checkout,
   tickets, delivery, hotel, flight).
4. A question, at least 3 times out of 4. The one allowed non-question form: "You've fallen for this at ___."
5. No digits, no number words (except "one"), no brand names, no trick names, no hype words.
6. It opens exactly one question that the video answers. Before writing beats, write `hook_answer`: one line from the
   twist or mechanism beat that answers the hook. If you cannot point to that line, rewrite the hook.
7. It asks, it does not tell. The hook never states the lesson.
8. Silent test: the `Hero` title (16 chars) and sub (22 chars) show the same tension with the sound off
   (e.g. "WHAT A STEAL?" / "OR A TRAP?").

### Templates (fill the blanks with the viewer's everyday objects)

| # | Template | Example fill | Fits |
|---|---|---|---|
| 1 | Ever wondered why the ___ costs almost the same as the ___? | ...the medium costs almost the same as the large? | decoy, sizes |
| 2 | Ever picked the ___ because the ___ looked silly? | ...the large because the medium looked silly? | decoy |
| 3 | Ever picked the bigger ___ because it felt like a steal? | ...the bigger size because it felt like a steal? | decoy, sizes |
| 4 | Have you ever ___ and then ___? | Have you ever booked a cheap flight and then hated checkout? | hidden fees |
| 5 | Have you ever paid more for ___ and still felt smart? | ...paid more for the combo and still felt smart? | bundling |
| 6 | Why does ___ always ___? | Why does the fancy one always sit at the top? | anchor, menus |
| 7 | You've fallen for this at ___. Probably this week. | You've fallen for this at the coffee shop. Probably this week. | any |
| 8 | Ever noticed the ___ is never ___? | Ever noticed the cheapest wine is never at the top? | menu design |
| 9 | Why do so many ___ end the same way? | Why do so many price tags end the same way? | charm pricing |
| 10 | Ever bought ___ just to get ___? | Ever bought extra stuff just to get free shipping? | thresholds |
| 11 | Why is the ___ so cheap when everything else ___? | Why is the hot dog so cheap when everything else costs more? | loss leader |
| 12 | Have you ever kept paying for ___ you forgot about? | Have you ever kept paying for an app you forgot about? | subscription traps |
| 13 | Ever wondered why every ___ shows a crossed-out price? | Ever wondered why every sale tag shows a crossed-out price? | reference prices |
| 14 | Why do ___ get pricier the longer you ___? | Why do tickets get pricier the longer you wait? | surge, scarcity |
| 15 | Ever grabbed the ___ because it was almost the same price? | Ever grabbed the bigger one because it was almost the same price? | decoy, sizes |
| 16 | Why does the shop show you the ___ first? | Why does the shop show you the most expensive one first? | anchor |

### Bad hooks (do not write these)

1. **"A bundle wins even though a cheaper plan looks cheaper."** A tautology (cheaper looks cheaper), no question,
   about a product instead of the viewer, uses jargon ("bundle"), nothing to picture.
2. **"The Economist tricked 100 MIT students with the decoy effect."** Brand, number and trick name in one line: it
   gives the answer away, it is about a company, and the viewer has no question left to stay for.
3. **"This pricing trick is honestly insane."** Hype word, no object to picture, no question the video can answer.
   Every channel says this.

---

## 4. Story structure

Plan first, then write lines. Plan fields: `hook`, `hook_answer`, `odd_fact`, `twist`, `comparison`, `proof`,
`everyday` (cheap option, fake option, target option, prices), `rule`.

Target: **13-17 beats, 115-135 words total, at most 850 spoken characters.** Troy at `+20%` with pauses was measured
on episode 001: 149 words (many prices and numbers) = 68 s of video, about 0.46 s per word, so 135 words = about
62 s. Prices and numbers are slow to say ("$125" = "one hundred twenty-five dollars"), so fewer of them = more room.
The character cap also keeps one episode under a quarter of the Orpheus daily limit (3,600). Each beat = one spoken
line of 3-24 words + one scene. More, shorter beats look better than long ones: the picture changes with every line.

**Pauses are automatic** (prep.py), so the viewer can follow: about 0.4 s after every sentence end, 0.6 s when the
story moves to a new part (the scene or mode changes, or after a `Statement`), 0.8 s after the hook, only 0.15 s
between beats of the same scene. Use the scene changes to mark the parts of the story. A beat may set its own
`"pause"` (seconds after its line) when a part ends inside one scene, e.g. `"pause": 0.6`.

| # | Beat | Purpose | Scene | Words |
|---|---|---|---|---|
| 1 | HOOK | A question about the viewer's own life (section 3). | Hero | 8-12 |
| 2 | YOUR MOMENT | The everyday scene they recognize. Same object as the hook. It comes back in beat 8. | Statement | 5-12 |
| 3 | THE CASE | Who tested what, on whom, and the options. One card per beat. Each price said once. Name the person and place from the facts. | PriceList (2-3 beats) | 20-32 |
| 4 | THE STRANGE DETAIL | The thing that makes no sense: nobody picks it / it loses money / the price is odd. | Crowd or PriceList | 8-14 |
| 5 | TWIST (dark blueprint) | Why it exists, in plain words: "It's a fake option, never meant to sell." | PriceList, mode blueprint | 8-16 |
| 6 | THE MECHANISM | Why it works, with ONE comparison or analogy the viewer can picture. Then the question the trick makes you skip. | PriceList ball hop or Anchor (2 beats) | 20-30 |
| 7 | PROOF + NAME | The numbers that show choices change. Then the lesson in plain words over moving dots (bring the fake option back: dots fly back), then the trick's name once in a short `Statement`. | Crowd + Crowd + Statement (3 beats) | 20-28 |
| 8 | WHERE YOU'LL MEET IT | The same trick in an everyday purchase, BEFORE then AFTER. No brands. The fake option must be obviously worse value: it costs at least 90% of the target's price and gives clearly less. End on a callback to the hook. | Compare (2 beats) | 18-28 |
| 9 | RULE + CTA | One rule the viewer can use at the counter (10 words or fewer), then one question they can answer in the comments. | Statement + Outro | 12-20 |

If the facts have no "people choosing" numbers, use the fact's own numbers as proof in `Statement` (one big number) or
`Anchor`. If the total runs over 135 words, cut in beats 3, 6 and 8 first, never the twist or the proof.

### Gold example (episode 001, decoy)

- Hook: "Ever picked the bigger size because it felt like a steal?"
- Strange detail: "84 picked print plus web. 16, web-only. Print-only? Nobody."
- Twist: "Why offer it? It's a fake option, never meant to sell."
- Mechanism: "Next to it, print plus web feels like getting the website free." / "So you forget the real
  question: do I need the paper?"
- Proof: "Without the fake option, 68 picked web-only. Only 32 picked print plus web."
- Everyday: "Add a $7 medium. Now large is only 50 cents more. What a steal!"
- Rule: "Silly option? It's selling the one next to it."

---

## 5. Checklist (every answer must be YES)

1. Is the hook a question about something the viewer did, 12 words or fewer, with no number, brand or trick name?
2. Does one line in the twist or mechanism beat answer the hook's question directly?
3. Could a 12-year-old explain the trick back in one sentence after one watch? (Write that sentence, using only words
   from the script.)
4. Is the trick described in plain words ("a fake option") before its name is said?
5. Does every number appear in the case facts (except 1-3 and the everyday prices), and is each said in at most 2 beats?
6. Is every sentence new? No line repeats or restates another line in different words.
7. Does each option keep one name all the way through, and does every "it" point to one clear thing?
8. In the everyday example: no brands, simple prices, and the fake option costs at least 90% of the target but gives
   clearly less?
9. Counts: 13-17 beats, each line 3-24 words, each sentence 12 words or fewer, 115-135 words and at most 850
   characters in total, no hype or filler word?
10. Does each beat's scene show exactly what its line says (the card, bin, number or price named in the line)?
