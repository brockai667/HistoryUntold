# PriceTrap – fabrika č. 4 (formát „papierový cenník“) – KONTRAKT

Jedno video denne, 1080×1920, 55–75 s: jeden skutočný, zdokumentovaný cenový trik (návnada/decoy, kotva, charm
pricing, bundling, loss leader, ...) + prenos toho istého triku do bežného života diváka. Všetko **zadarmo, bez PC,
bez Claude tokenov v prevádzke**: GitHub Actions cron → najstarší skript z `bank/scripts/` (píše ho Claude rutina, záloha: free model
Cloudflare Workers AI `gpt-oss-120b` / Groq ako autor) → hlas Orpheus (Groq TTS, záloha edge-tts)
→ Remotion (render) → GitHub Release `ep-NNN` (video + popisok; Damián nahrá z mobilu) → neskôr Buffer.
Pravidlá slov a rozprávania (publikum, háky, štruktúra, checklist): `SCRIPT_GUIDE.md`.

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
  bank/scripts/YYYY-MM-DD-NN-<case-id>.json   (hotové story od Claude rutiny; použité → bank/scripts/used/)
  SCRIPT_GUIDE.md                         (pravidlá slov a rozprávania)
  episodes/<NNN>-<id>/story.json          (výstup autora; commitne workflow)
  remotion/src/*.tsx, theme.ts, icons.ts  (A)   remotion/brand.json, icons.json (A)
  remotion/tools/prep.py                  (A)   remotion/story/showoff.json, stress.json (A, testy)
  remotion/public/<ep>/  (generované prep.py, ignorované)   remotion/out/ (stills, ignorované)
  tools/common.py lint.py write_case.py run.py   (B)
  assets/music/cut-and-run.mp3            (hotové; Kevin MacLeod, CC BY 4.0)
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
  "voice": "orpheus:troy",
  "rate": "+20%",
  "hashtags": "#pricing #psychology #marketing #money #consumer",
  "music": "assets/music/cut-and-run.mp3",
  "music_credit": "Music: \"Cut and Run\" - Kevin MacLeod (incompetech.com) · Licensed under CC BY 4.0",
  "music_gain": 0.13
}
```
Hlas: `orpheus:troy` = Groq Orpheus TTS (kľúč `GROQ_API_KEY`, denný limit). Orpheus nemá parameter rýchlosti → `rate` `+20%` sa aplikuje
ako ffmpeg `atempo` (výška hlasu ostane). Keď Orpheus narazí na denný limit (alebo chýba kľúč/sieť), celý diel ide záložným edge-tts hlasom
(`FALLBACK_VOICE` v `prep.py`, `en-US-AndrewMultilingualNeural` `+6%`). Časy slov: faster-whisper zarovnaný na text scenára.
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
- `mode` voliteľné (`paper` | `blueprint`), `hold` voliteľné (s, ≤ 8), `pause` voliteľné (s ticha po hlase úderu; inak automaticky: 0,15 s v rámci scény,
  0,6 s pri zmene scény/režimu a po Statement, 0,8 s po Hero; vo vnútri hlasu ~0,38 s za koncom vety, 0,3 s za dvojbodkou). `voice`, `rate`, hudba, brand = z brand.json, autor ich nepíše.
- prep.py: `python remotion/tools/prep.py episodes/001-economist-decoy/story.json` → `remotion/public/001-economist-decoy/{episode.json,voice.mp3,music.mp3,caption.txt}` + `remotion/public/current.json`.
  **Názov epizódy = názov priečinka** (ak sa súbor volá story.json), inak basename. caption.txt = caption + prázdny riadok + hashtags + prázdny riadok + music_credit.
  episode.json navyše nesie `source`, `logo`, `tagline`, `stamp`, `cta`, `bait_stamp`, `header`.
- **Inserty** (veľký text cez celú obrazovku na ~1 s, `insert_at` v `prep.py`; kandidát = krátka posledná/úvodná veta alebo koniec za čiarkou):
  nie v `Hero`/`Statement`/`Outro`, nie v háku ani pri pečiatke; v `Crowd` úderoch nikdy; v úderoch s `point` až po 1,9 s od začiatku úderu;
  v `PriceList` sa kandidáti s číslicami zahadzujú (text by zakryl cenové karty).
- **SFX** (`remotion/tools/sfx.py`, syntéza v numpy, čas podľa animácií): `Crowd` = cvaknutie korálky pri každom dopade bodky
  (najviac jedno za 0,045 s) + whoosh pri migrácii; gulička `point` = pop pri objavení, whoosh pri štarte, pop pri dopade, ding ak sú ceny rovnaké.

## Scény a props (A renderuje v medziach, B lintuje presne tieto limity)
Spoločné: `TagT` = string alebo `{"text","tone"}`, tone ∈ `plain|dark|blue|yellow|red|green`, text ≤ 16 znakov.
`CardT` = `title` ≤ 18, `sub` ≤ 22, `price` ≤ 12, `priceRed` bool, `tags` ≤ 3 × TagT, `art` (ikona), `stamp` ≤ 8, `badge` TagT ≤ 14, `top` TagT ≤ 10.
`art` = meno z `remotion/icons.json` alebo `car` | `car-red` | `car-fly` | `none`. Prípona `-red` na ľubovoľnej ikone = ikona s červeným nádychom (ako `car-red`).

| scéna | props | limity |
|---|---|---|
| `Hero` | `art`, `tag` TagT, `title`, `sub` | title ≤ 16, sub ≤ 22 |
| `PriceList` | `slots` 2–3, `cards[]` CardT, voliteľne `point` [a, b] | 1–3 karty, `slots` ≥ počet kariet; `point` = dva rôzne indexy kariet (od 0), obe s `price` |
| `Views` | `job`, `label`, `value` int, `from` int, `prefix`, `suffix`, `grid` 0–8, `thumbLabel`, `art` | job ≤ 26, label ≤ 10, suffix ≤ 2, thumbLabel ≤ 8 |
| `Anchor` | `job`, `price`, `at` 0–1, `split` 0–1, `art`, `anchor` {`label` ≤ 24, `art`} | price ≤ 12 |
| `Compare` | `before[]`, `after[]` CardT (null = prázdny slot, v `after` len ak sú **všetky** `null`), `labels` [2] | 2–3 položky, rovnaký počet; v Compare title ≤ 16, price ≤ 8 |
| `Crowd` | `job` TagT, `options[]` 2–3 × {`label`, `art`, `value`, `bait`}, `total` | job ≤ 28; label ≤ 14 (povinný, unikátny), `art` ikona, `value` int ≥ 0, `bait` bool voliteľné; `total` int 10–100 (default 100), súčet `value` ≤ `total` |
| `Statement` | `kicker` ≤ 28, `text` ≤ 7 slov a ≤ 40 znakov, `tags[]` ≤ 3 × ≤ 28 znakov | |
| `Outro` | `{}` (kód doplní logo/stamp/tagline/cta), voliteľne `art` | posledný úder, práve raz |

Poznámky k scénam:
- **`Crowd`**: súbor 100 bodiek („ľudia“) letí do hore otvorených nádob s počítadlami (jedna nádoba na `options[]`). Ak mal predošlý Crowd úder
  (aj s inými scénami medzi nimi) rovnaké `label`y, bodky migrujú medzi nádobami (zaniknuté nádoby zbledú). Kamera: wide → všetky nádoby →
  vedúca nádoba → záver na „point“ nádobe (návnada = `bait`, inak najmenšia; pri zmene nádoba, ktorá stratila najviac). `value` sú čísla
  z faktov (lint pravidlo 3).
- **`PriceList.point` [a, b]**: žltá gulička skočí z ceny karty `a` na cenu karty `b`, odznak „=“ (žltý, rovnaká cena) alebo „≠“ (červený);
  ostatné karty zhasnú na 0,3; kamera zarámuje obe karty. Použi na vetu, ktorá porovnáva dve ceny.
- **`Compare.after`** môže byť celé `null` (odhalenie až v ďalšom údere); kamera sa potom zameria na stĺpec BEFORE.
- **Štítky na `PriceList` kartách** (`Blocks.tsx` `cardTags`): jeden riadok do 28 px, inak 18→15 px so zalomením.

## Lint (B, `tools/lint.py`, použije ho aj autor v opravnom kole)
1. 11–17 úderov; prvý `Hero`, posledný `Outro`, `Outro` práve raz; `scene` ∈ 8 scén (Hero, PriceList, Views, Anchor, Compare, Statement, Outro, Crowd); props len známe kľúče; limity vyššie.
2. `say`: 3–24 slov, bez emoji, len rovné úvodzovky `"` a `'`, žiadne `*`/`#`/markdown; spolu 85–150 slov (lint; cieľ 115–135, pauzy pridajú ~15 %).
3. **Čísla**: každé číslo (`$59`, `125`, `84`, `16%`, `1,000,000`, `2008`) v `say` a v props mimo scény `Compare` musí byť
   v textoch `facts` prípadu (porovnanie po odstránení `$ , %` a medzier; `1.5 million` ≈ `1,500,000` netreba riešiť – model má
   čísla citovať presne). Výnimka: čísla 0–3 (napr. „2 jobs“), `slots`, `grid`, `at`, `split`, `from`, `hold`, `point`, `total`.
   V scéne `Compare` smú byť v `say` aj rozdiely cien z kariet (napr. „50 cents more“ z $2.00 vs. $2.50; `_diffs`). V `Crowd` sa `value` kontroluje ako ostatné čísla v props.
4. **Mená** (veľké písmená mimo začiatku vety v `say`): povolené len `names` prípadu + bežné slová; v scéne `Compare`
   nesmie byť žiadne meno z `names` ani slovo z blacklistu značiek (Apple, Starbucks, Netflix, Amazon, Nike, Tesla,
   McDonald's, Costco, IKEA, Gillette, Disney, Uber, Spotify, Rolex, Hermès, Supreme, Google, Microsoft, Samsung).
5. **Nadväznosť**: dva po sebe idúce údery tej istej scény `PriceList`: karty predošlého úderu musia ostať na svojich
   pozíciách (rovnaké `title` na indexe i); `Compare`: `before` sa nemení, v `after` len pribúda/mení sa badge/top
   (ak je predošlé `after` celé `null` = odhalenie, kontrola `after` sa preskočí).
6. **Červená** len pre návnadu: `priceRed`, tone `red`, `stamp` smú byť najviac na 2 rôznych tituloch kariet v celej epizóde
   (karta návnady + `top: EXTREME` v Compare); `badge` SMART CHOICE je `green`.
7. `case` 1–3 slová UPPER; `title`, `caption`, `source` neprázdne a v limitoch.
8. `PriceList.point`: zoznam 2 rôznych celých indexov (od 0), obe karty existujú a majú `price`.
9. `Crowd`: `options` 2–3 objekty s kľúčmi len `label` (≤ 14, povinný, unikátny), `art` (ikona), `value` (int ≥ 0), `bait` (bool); `job` ≤ 28;
   `total` int 10–100 (default 100); súčet `value` ≤ `total`.
10. Príbeh (`_story_checks`): „veta číta kartu nahlas“ (názov karty + jej cena v tom istom `say`) sa kontroluje len pri kartách, ktoré boli
    už v predošlom údere `PriceList`; práve pribudnutá karta sa smie raz predstaviť menom a cenou.
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
Toto je **záloha** (fallback): bežne story píše Claude rutina do `bank/scripts/` (viď Beh) a free model sa použije len keď banka skriptov nie je použiteľná.

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
1. `state.json` → `N = next_ep`. Zdroj story (bez `--case`):
   a) **banka skriptov**: najstarší nepoužitý `bank/scripts/*.json` (zoradené podľa mena = najstarší prvý; názov `YYYY-MM-DD-NN-<case-id>.json`,
      pole `id` musí sedieť s prípadom v `bank/cases.json` a nesmie byť v `used`). Píše ich Claude rutina každé 3 dni, cieľ 5 na sklade;
      každý musí prejsť `tools/lint.py` (`bank_script()`), ten, čo neprejde, sa preskočí. Skript sa skopíruje do `episodes/NNN-<id>/story.json`.
   b) **záloha** len keď žiadny skript nie je použiteľný: free model (`write_case.py`) napíše story k prvému prípadu z `bank/cases.json`
      mimo `used` (poradie banky). Ak autor zlyhá, skús ešte jeden ďalší prípad (max 2 za beh), potom exit 1.
   `--case ID` = vždy cez autora (b) pre daný prípad.
2. `episodes/NNN-id/story.json` (NNN = 3 číslice); ak už existuje (opakovaný beh), autora preskoč.
3. `python remotion/tools/prep.py episodes/NNN-id/story.json`; render z `remotion/`:
   `npx remotion render Episode ../output/NNN-id.mp4 --props="{\"ep\":\"NNN-id\"}" --crf=22 --concurrency=100%`
   (kompozícia sa volá `Episode`, nie `Decoy`). Potom obal: `npx remotion still Episode ../output/NNN-id-cover.jpg --props=... --frame=F`,
   F = (t0 druhého úderu + 1 s) × 30; obal nie je kritický (try/except).
4. `output/NNN-id.txt` = `title` + prázdny riadok + obsah `caption.txt`.
5. `--no-post` → koniec. Inak GitHub Release `ep-NNN` (gh release create / upload --clobber, `--title "PRICE TRAP · <title>"`,
   notes = popisok v ``` bloku + poznámka o obale, presne ako `release()` vo vote-story `run.py`).
6. Stav: `used` += id, `episodes[N] = {id, title, posted_at, release, author}` (`author` = `"claude-bank"` | `"free-model"`), `next_ep = N+1`;
   použitý skript z banky sa po úspešnom Release presunie do `bank/scripts/used/` (rutina z toho vidí, koľko ostáva); vypíš `HOTOVO: ep NNN`.
Buffer: zatiaľ nie (kanály neexistujú). Nechaj funkciu `publish_buffer()` ako jasne označený stub s TODO.

## Workflow (B, `.github/workflows/daily.yml`)
`name: PriceTrap Daily`; `on: schedule: cron "10 6 * * *"` + `workflow_dispatch` inputs `case` (string, ""), `no_post` (boolean, false).
`permissions: contents: write`; `concurrency: group: pricetrap`; ubuntu-latest, timeout 45. Kroky ako v survey.yml:
checkout, setup-python 3.12, setup-node 20 (cache npm, `cache-dependency-path: remotion/package-lock.json`),
`sudo apt-get install -y ffmpeg libnss3 libatk-bridge2.0-0 libgbm1 libasound2t64 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2`,
`pip install edge-tts numpy soundfile requests faster-whisper`, `npm ci --no-audit --no-fund` v `remotion/`, `npx remotion browser ensure` v `remotion/`,
`python -u tools/run.py` s `--case`/`--no-post` podľa inputs, env `MODELS_TOKEN: ${{ secrets.GROQ_API_KEY }}`, `GROQ_API_KEY` (Orpheus hlas),
`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `GEMINI_API_KEY` (zo secrets), `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}`.
Potom upload-artifact `output/*` (7 dní, `if: always()`), a „Persist state“: `git add state.json episodes bank/scripts`, commit `pricetrap: ep $(date -u +%F)`, `git pull --rebase || true`, `git push || true`.

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
