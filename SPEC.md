# PriceTrap – fabrika č. 4 (formát „papierový cenník“) – KONTRAKT

Jedno video denne, 1080×1920, 55–75 s: jeden skutočný, zdokumentovaný cenový trik (návnada/decoy, kotva, charm
pricing, bundling, loss leader, ...) + prenos toho istého triku do bežného života diváka. Všetko **zadarmo, bez PC,
bez Claude tokenov v prevádzke**: GitHub Actions cron → free model (Cloudflare Workers AI `gpt-oss-120b`, záloha Groq) ako autor → edge-tts (hlas)
→ Remotion (render) → GitHub Release `ep-NNN` (video + popisok; Damián nahrá z mobilu) → neskôr Buffer.

Vzory, ktoré sa kopírujú: `C:\Users\damia\WealthFactory-vote\vote\tools\{common.py,write_part.py,run.py}`
(Groq volanie, mechanická kontrola s opravným kolom, Release cez `gh`), `C:\Users\damia\HiddenEarth-survey\.github\workflows\survey.yml`
(render Remotionu v Actions). Šablóna formátu: `remotion/` (kópia `D:\Praca\FactoryAnim\decoy-report`, README tam).

Zodpovednosti: **A** = `remotion/` (TSX, prep.py, brand.json, ikony). **B** = `tools/`, `.github/`, `README.md`, `state.json`.
**C** = `bank/cases.json`. Nikto nesiaha do cudzích súborov; rozhranie je tento súbor.

## Zakázané
- Žiadne kľúče/tokeny do repa, do logov ani do správ. Kľúče sa čítajú len z env / `.env` (poradie ako vo vote-story
  `common.py`: `REPO/.env`, `~/.config/watch/.env`, `~/FactoryAnim/.env`, `D:/Praca/FactoryAnim/.env`); nikdy sa nevypisujú.
- Nepushovať, nevytvárať repo na GitHube, nič nemazať mimo `C:\Users\damia\PriceTrap`.
- Žiadne platené služby. Cloudflare Workers AI free (10k neurónov/deň), Groq free, edge-tts, GitHub Actions, lucide ikony (ISC).

## Adresáre
```
PriceTrap/
  .github/workflows/daily.yml             (B)
  bank/cases.json                         (C)
  episodes/<NNN>-<id>/story.json          (výstup autora; commitne workflow)
  remotion/src/*.tsx, theme.ts, icons.ts  (A)   remotion/brand.json, icons.json (A)
  remotion/tools/prep.py                  (A)   remotion/story/showoff.json, stress.json (A, testy)
  remotion/public/<ep>/  (generované prep.py, ignorované)   remotion/out/ (stills, ignorované)
  tools/common.py lint.py write_case.py run.py   (B)
  assets/music/backed-vibes-clean.mp3     (hotové; Kevin MacLeod, CC BY 4.0)
  state.json  {"next_ep": 1, "used": [], "episodes": {}}   (B)
  output/  (mp4, txt, cover – ignorované)
  README.md (B, po slovensky, krátky)
```

## Značka – `remotion/brand.json` (A vytvorí, prep.py ho zlúči do episode.json)
```json
{
  "brand": "PRICE TRAP",
  "header": "PRICE TRAP",
  "logo": "PRICE TRAP",
  "tagline": "THE TRICKS BEHIND EVERY PRICE",
  "stamp": "TRAPPED",
  "bait_stamp": "BAIT",
  "cta": "FOLLOW FOR MORE →",
  "voice": "en-US-GuyNeural",
  "rate": "+4%",
  "hashtags": "#pricing #psychology #marketing #money #consumer",
  "music": "assets/music/backed-vibes-clean.mp3",
  "music_credit": "Music: \"Backed Vibes Clean\" - Kevin MacLeod (incompetech.com) · Licensed under CC BY 4.0",
  "music_gain": 0.10
}
```
Hlavička videa: `PRICE TRAP · CASE · <case>` (pôvodne `DECOY REPORT · CASE · ...`; slovo REPORT preč, text z `header`).
Pečiatka na karte návnady: `bait_stamp` (BAIT). Outro: `logo`, `tagline`, `stamp` (TRAPPED), `cta` – autor ich nepíše, dopĺňa kód.

## Story JSON = výstup autora (B) = vstup `remotion/tools/prep.py` (A)
```json
{
  "id": "economist-decoy",
  "case": "THE USELESS OPTION",
  "title": "The subscription nobody picked",
  "caption": "One line hook for the post. Second line optional.",
  "source": "Dan Ariely, Predictably Irrational (2008)",
  "beats": [
    { "say": "Spoken sentence.", "scene": "Hero", "props": { "...": "..." }, "mode": "blueprint", "hold": 4 }
  ]
}
```
- `id` = id prípadu z banky (dopĺňa kód). `case` ≤ 3 slová UPPER (hlavička). `title` ≤ 60 znakov. `source` ≤ 60 znakov (päta videa).
- `mode` voliteľné (`paper` | `blueprint`), `hold` voliteľné (s, ≤ 8). `voice`, `rate`, hudba, brand = z brand.json, autor ich nepíše.
- prep.py: `python remotion/tools/prep.py episodes/001-economist-decoy/story.json` → `remotion/public/001-economist-decoy/{episode.json,voice.mp3,music.mp3,caption.txt}` + `remotion/public/current.json`.
  **Názov epizódy = názov priečinka** (ak sa súbor volá story.json), inak basename. caption.txt = caption + prázdny riadok + hashtags + prázdny riadok + music_credit.
  episode.json navyše nesie `source`, `logo`, `tagline`, `stamp`, `cta`, `bait_stamp`, `header`.

## Scény a props (A renderuje v medziach, B lintuje presne tieto limity)
Spoločné: `TagT` = string alebo `{"text","tone"}`, tone ∈ `plain|dark|blue|yellow|red|green`, text ≤ 16 znakov.
`CardT` = `title` ≤ 18, `sub` ≤ 22, `price` ≤ 12, `priceRed` bool, `tags` ≤ 3 × TagT, `art` (ikona), `stamp` ≤ 8, `badge` TagT ≤ 14, `top` TagT ≤ 10.
`art` = meno z `remotion/icons.json` alebo `car` | `car-red` | `car-fly` | `none`. Prípona `-red` na ľubovoľnej ikone = ikona s červeným nádychom (ako `car-red`).

| scéna | props | limity |
|---|---|---|
| `Hero` | `art`, `tag` TagT, `title`, `sub` | title ≤ 16, sub ≤ 22 |
| `PriceList` | `slots` 2–3, `cards[]` CardT | 1–3 karty, `slots` ≥ počet kariet |
| `Views` | `job`, `label`, `value` int, `from` int, `prefix`, `suffix`, `grid` 0–8, `thumbLabel`, `art` | job ≤ 26, label ≤ 10, suffix ≤ 2, thumbLabel ≤ 8 |
| `Anchor` | `job`, `price`, `at` 0–1, `split` 0–1, `art`, `anchor` {`label` ≤ 24, `art`} | price ≤ 12 |
| `Compare` | `before[]`, `after[]` CardT (null = prázdny slot, len v `before`), `labels` [2] | 2–3 položky, rovnaký počet; v Compare title ≤ 16, price ≤ 8 |
| `Statement` | `kicker` ≤ 28, `text` ≤ 7 slov a ≤ 40 znakov, `tags[]` ≤ 3 × ≤ 28 znakov | |
| `Outro` | `{}` (kód doplní logo/stamp/tagline/cta), voliteľne `art` | posledný úder, práve raz |

## Lint (B, `tools/lint.py`, použije ho aj autor v opravnom kole)
1. 11–17 úderov; prvý `Hero`, posledný `Outro`, `Outro` práve raz; `scene` ∈ 7 scén; props len známe kľúče; limity vyššie.
2. `say`: 3–24 slov, bez emoji, len rovné úvodzovky `"` a `'`, žiadne `*`/`#`/markdown; spolu 100–190 slov.
3. **Čísla**: každé číslo (`$59`, `125`, `84`, `16%`, `1,000,000`, `2008`) v `say` a v props mimo scény `Compare` musí byť
   v textoch `facts` prípadu (porovnanie po odstránení `$ , %` a medzier; `1.5 million` ≈ `1,500,000` netreba riešiť – model má
   čísla citovať presne). Výnimka: čísla 1–3 (napr. „2 jobs“), `slots`, `grid`, `at`, `split`, `from`, `hold`.
4. **Mená** (veľké písmená mimo začiatku vety v `say`): povolené len `names` prípadu + bežné slová; v scéne `Compare`
   nesmie byť žiadne meno z `names` ani slovo z blacklistu značiek (Apple, Starbucks, Netflix, Amazon, Nike, Tesla,
   McDonald's, Costco, IKEA, Gillette, Disney, Uber, Spotify, Rolex, Hermès, Supreme, Google, Microsoft, Samsung).
5. **Nadväznosť**: dva po sebe idúce údery tej istej scény `PriceList`: karty predošlého úderu musia ostať na svojich
   pozíciách (rovnaké `title` na indexe i); `Compare`: `before` sa nemení, v `after` len pribúda/mení sa badge/top.
6. **Červená** len pre návnadu: `priceRed`, tone `red`, `stamp` smú byť najviac na 2 rôznych tituloch kariet v celej epizóde
   (karta návnady + `top: EXTREME` v Compare); `badge` SMART CHOICE je `green`.
7. `case` 1–3 slová UPPER; `title`, `caption`, `source` neprázdne a v limitoch.
Výstup lintu: zoznam reťazcov `beat 4 PriceList: card 2 title too long (23 > 18)`; prázdny = OK.

## Autor (B, `tools/write_case.py <case-id> --out episodes/NNN-id/story.json [--fake odpoved.json]`)
Reťazec bezplatných modelov (`backend:model`, prepíše env `MODELS_CHAIN`), všetky cez OpenAI-kompatibilné `/chat/completions`:
1. `cloudflare:@cf/openai/gpt-oss-120b` – Workers AI, base `https://api.cloudflare.com/client/v4/accounts/<CLOUDFLARE_ACCOUNT_ID>/ai/v1`,
   kľúč `CLOUDFLARE_API_TOKEN`; vlastná kvóta 10 000 neurónov/deň (≈ 25 volaní), bez okna TPM → `reasoning_effort "medium"`,
   `max_tokens 12000`, opravné kolo dostane predošlý JSON + zoznam chýb.
2. `groq:openai/gpt-oss-120b` – `MODELS_TOKEN`/`GROQ_API_KEY`, base `https://api.groq.com/openai/v1`; kľúč je zdieľaný s inými
   fabrikami (200k tokenov/deň, býva plný), okno 8k TPM → `reasoning_effort "low"`, `max_tokens ≤ 5000`, prompt + max_tokens ≤ 7850,
   opravné kolo bez predošlého JSON (len zoznam chýb, model píše znova).
3. `cloudflare:@cf/google/gemma-4-26b-a4b-it`, 4. `cloudflare:@cf/qwen/qwen3.8-27b` (tá istá kvóta, iný model), 5. `groq:openai/gpt-oss-20b`,
6. `gemini:gemini-3.8-flash` (`GEMINI_API_KEY`; projekt bol 10/2026 blokovaný – 403), 7. `openrouter:...:free` (`OPENROUTER_API_KEY`).
Groq `qwen/qwen3.8-27b` nie: limit 1000 výstupných tokenov/min. Všade `temperature 0.8`, `response_format json_object`.
Chyby: 413/429 „Limit X, Requested Y“ → skrátiť max_tokens; 429 denný limit s „try again in ≤ MODELS_MAX_WAIT s“ (900) → počkať (2×),
inak ďalší model; ostatné 429/5xx → čakať 65 s (5×); 400 `json_validate_failed` → ďalší model; 401/403 → backend preskočiť; bez kľúča → preskočiť.
Pred lintom normalizácia v kóde: rovné úvodzovky a spojovníky (U+2011 → `-`), `source` z banky, `case` VERZALKAMI, chýbajúce `art`
z ikon prípadu, `tag`→`tags`, štítky (`tag`, `tags`, `top`, `badge`, `stamp`, `kicker`, `job`, `labels`) VERZALKAMI.
Najviac 4 pokusy („Fix exactly these problems and return the complete corrected JSON“); každý pokus sa uloží do
`episodes/NNN-id/attempts/N-backend.json`. `--fake súbor.json` = odpoveď zo súboru (offline test). Návrat 0 + cesta; 2 = zlyhanie.
Pred lintom kód doplní `id`; po úspechu uloží story.json (ensure_ascii=False, indent 1).

Systémový/užívateľský prompt (anglicky, presne tento obsah, doplň `{...}`; schému scén vlož z tabuľky vyššie ako JSON ukážky):
```
You write one episode of "PRICE TRAP" – a vertical explainer video (TikTok/Reels, 55–75 seconds) in the style of a
paper price report: calm male voice, short punchy sentences, dry wit, every sentence = one visual change on beige paper
with price cards. Each episode exposes ONE pricing trick from a real, documented case, then shows the viewer the same
trick in everyday life.

CASE: {case}   TRICK: {trick}
SUBJECT: {subject}
FACTS (the only facts, names and numbers you may use – quote numbers exactly as written, never add others):
{facts, one per line with "- "}
LESSON: {lesson}
SOURCE: {source}
ICONS you may use as "art": {icons}   Suggested: hero {icons.hero}, bait {icons.bait}, real choice {icons.real}

STRUCTURE – 12 to 16 beats. One beat = 1–2 spoken sentences (max 22 words, numbers as digits with $ or %):
1. HOOK (beats 1–2, scene Hero): the surprising thing in the first 3 seconds. No intro, no "today", no question.
2. THE LIST (beats 3–6, scene PriceList, 2–3 cards): cards appear top-down, one new card per beat. Repeat the full
   previous state and add one thing per beat (a card, a tag, a price). The bait card is first: red price text
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
Numbers exactly as in FACTS. Never invent statistics, studies, names, years or prices for the real case.
RED is only for the bait (priceRed, tone "red", stamps). Everything else plain, dark, blue, yellow or green.
Card text limits: title ≤ 18 chars, sub ≤ 22, price ≤ 12, tag ≤ 16, ≤ 3 tags; in Compare title ≤ 16, price ≤ 8.
Scene props (JSON shapes): {schémy}
Return ONLY JSON: {"case": "2-3 WORDS UPPER CASE", "title": "post title ≤ 60 chars", "caption": "1-2 lines for the post",
"source": "{source}", "beats": [ {"say": "...", "scene": "...", "props": {...}, "mode": "blueprint" (optional), "hold": 4 (optional)} ]}
```

## Beh (B, `tools/run.py [--case ID] [--no-post] [--force]`)
1. `state.json` → `N = next_ep`; prípad = `--case` alebo prvý z `bank/cases.json` mimo `used` (poradie banky). Ak autor zlyhá,
   skús ešte jeden ďalší prípad (max 2 za beh), potom exit 1.
2. `episodes/NNN-id/story.json` (NNN = 3 číslice); ak už existuje (opakovaný beh), autora preskoč.
3. `python remotion/tools/prep.py episodes/NNN-id/story.json`; render z `remotion/`:
   `npx remotion render Episode ../output/NNN-id.mp4 --props="{\"ep\":\"NNN-id\"}" --crf=22 --concurrency=100%`
   (kompozícia sa volá `Episode`, nie `Decoy`). Potom obal: `npx remotion still Episode ../output/NNN-id-cover.jpg --props=... --frame=F`,
   F = (t0 druhého úderu + 1 s) × 30; obal nie je kritický (try/except).
4. `output/NNN-id.txt` = `title` + prázdny riadok + obsah `caption.txt`.
5. `--no-post` → koniec. Inak GitHub Release `ep-NNN` (gh release create / upload --clobber, `--title "PRICE TRAP · <title>"`,
   notes = popisok v ``` bloku + poznámka o obale, presne ako `release()` vo vote-story `run.py`).
6. Stav: `used` += id, `episodes[N] = {id, title, posted_at, release}`, `next_ep = N+1`; vypíš `HOTOVO: ep NNN`.
Buffer: zatiaľ nie (kanály neexistujú). Nechaj funkciu `publish_buffer()` ako jasne označený stub s TODO.

## Workflow (B, `.github/workflows/daily.yml`)
`name: PriceTrap Daily`; `on: schedule: cron "10 6 * * *"` + `workflow_dispatch` inputs `case` (string, ""), `no_post` (boolean, false).
`permissions: contents: write`; `concurrency: group: pricetrap`; ubuntu-latest, timeout 45. Kroky ako v survey.yml:
checkout, setup-python 3.12, setup-node 20 (cache npm, `cache-dependency-path: remotion/package-lock.json`),
`sudo apt-get install -y ffmpeg libnss3 libatk-bridge2.0-0 libgbm1 libasound2t64 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2`,
`pip install edge-tts numpy soundfile requests`, `npm ci --no-audit --no-fund` v `remotion/`, `npx remotion browser ensure` v `remotion/`,
`python -u tools/run.py` s `--case`/`--no-post` podľa inputs, env `MODELS_TOKEN: ${{ secrets.GROQ_API_KEY }}`,
`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `GEMINI_API_KEY` (zo secrets), `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}`.
Potom upload-artifact `output/*` (7 dní, `if: always()`), a „Persist state“: `git add state.json episodes`, commit `pricetrap: ep $(date -u +%F)`, `git pull --rebase || true`, `git push || true`.

## Banka (C, `bank/cases.json`) – `{"cases": [ ... ]}`, 30 prípadov, najlepšie prvé
```json
{
  "id": "economist-decoy",
  "case": "THE USELESS OPTION",
  "trick": "decoy effect",
  "subject": "The Economist's three subscription options in Dan Ariely's MIT experiment",
  "year": 2008,
  "names": ["The Economist", "Dan Ariely", "MIT"],
  "facts": [
    "The Economist offered web-only for $59, print-only for $125 and print plus web for $125.",
    "With all three options, 84 of 100 MIT students picked print plus web, 16 picked web-only, nobody picked print-only.",
    "Without the print-only option, 68 picked web-only and only 32 picked print plus web."
  ],
  "lesson": "An option nobody picks can still change what everybody picks.",
  "icons": { "hero": "newspaper", "bait": "newspaper", "real": "laptop" },
  "source": "Dan Ariely, Predictably Irrational (2008)",
  "confidence": "high"
}
```
Pravidlá: len dobre zdokumentované prípady (knihy, veľké médiá, výročné správy, vlastné vyhlásenia firiem); čísla presne
podľa zdroja, 3–6 faktov, každý ≤ 25 slov, prostá angličtina, žiadne „approximately“ – ak si číslom nie si istý, vynechaj ho;
`confidence` high/medium (žiadne low); bez prípadov z roku 2026; nemiešať tú istú firmu dvakrát; mix trikov: decoy,
anchor, charm pricing, bundling, loss leader, razor-and-blades, scarcity/drops, subscription traps, unbundled fees,
reference („compare at“) prices, menu design, size tiers, premium halo, free trial, surge. `source` ≤ 60 znakov. Ikony len zo zoznamu nižšie.

## Ikony (A vendoruje, B číta `remotion/icons.json`, C používa mená)
lucide (ISC): A stiahne `https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/<name>.svg` do
`remotion/vendor/lucide/` (stiahnuté = len dáta, nič sa z nich nespúšťa), do `remotion/src/icons.ts` zapíše mapu
`name → vnútorný SVG obsah (path/circle/... elementy ako string)` a do `remotion/icons.json` pole dostupných mien
(+ `car`, `car-red`, `car-fly`, `none`). Chýbajúce mená vynechá a vypíše v správe. Priložiť `remotion/vendor/lucide/LICENSE`.
Mená: coffee cup-soda popcorn pizza sandwich cake cake-slice ice-cream-cone candy wine beer apple egg utensils
smartphone laptop tv headphones watch camera gamepad-2 printer plane bike bus train-front fuel house hotel bed
armchair lamp sofa dumbbell pill stethoscope scissors shirt gem crown gift ticket clapperboard music book-open
graduation-cap shopping-cart shopping-bag store package truck tag receipt credit-card banknote coins piggy-bank
wallet key lock percent trophy star newspaper mail droplets zap wifi flame rocket glasses footprints umbrella
phone refrigerator washing-machine microwave bath baby dog cat flower-2 trees tent ship sailboat anchor scale
hammer wrench paintbrush palette briefcase building-2 landmark shield heart
