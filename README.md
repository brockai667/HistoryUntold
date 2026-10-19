# PriceTrap

Fabrika č. 4: denne jedno video 1080×1920 (55–75 s) o skutočnom, zdokumentovanom cenovom triku (návnada, kotva,
charm pricing, bundling...) a o tom istom triku v bežnom živote. Všetko zadarmo a bez PC:

GitHub Actions cron → bezplatný model (Cloudflare Workers AI `gpt-oss-120b`, záloha Groq) ako autor → edge-tts (hlas) → Remotion (render) → GitHub Release `ep-NNN`
(video + popisok, Damián nahrá z mobilu). Buffer zatiaľ nie (kanály neexistujú, v `tools/run.py` je stub `publish_buffer()`).

Celý kontrakt (formát story, scény, pravidlá lintu, prompt autora) je v `SPEC.md`.

## Súbory

- `bank/cases.json` – banka prípadov (poradie = poradie výroby)
- `tools/write_case.py` – autor (reťazec free modelov Cloudflare → Groq + kontrola `tools/lint.py`, max 4 pokusy,
  každý pokus v `episodes/NNN-id/attempts/`) → `episodes/NNN-id/story.json`
- `tools/run.py` – denný beh: výber prípadu → autor → prep + render → obal → Release → `state.json`
- `remotion/` – šablóna videa a `remotion/tools/prep.py` (hlas, hudba, `episode.json`)
- `state.json` – `next_ep`, použité prípady, zoznam epizód (commitne ho workflow)

## Ako pridať prípad do banky

Do poľa `cases` v `bank/cases.json` pridaj objekt (najlepšie prípady hore):

```json
{ "id": "economist-decoy", "case": "THE USELESS OPTION", "trick": "decoy effect",
  "subject": "...", "year": 2008, "names": ["The Economist", "Dan Ariely", "MIT"],
  "facts": ["3–6 faktov, každý ≤ 25 slov, čísla presne podľa zdroja"],
  "lesson": "...", "icons": { "hero": "newspaper", "bait": "newspaper", "real": "laptop" },
  "source": "Dan Ariely, Predictably Irrational (2008)", "confidence": "high" }
```

Len dobre zdokumentované prípady, `confidence` high/medium, `source` ≤ 60 znakov, ikony z `remotion/icons.json`.
Autor smie použiť iba čísla a mená z `facts`/`names` – lint ostatné odmietne.

## Ručný beh lokálne

Potrebuje Python 3.12+, Node 20, ffmpeg a kľúče v prostredí alebo v `.env` (`REPO/.env`, `~/.config/watch/.env`;
kľúč nikdy nepatrí do repa ani do logov): `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` (Workers AI, hlavný autor,
10 000 neurónov/deň ≈ 25 volaní) a `GROQ_API_KEY` (záloha; kľúč zdieľaný s ostatnými fabrikami má 200k tokenov/deň,
býva plný). Poradie modelov prepíše `MODELS_CHAIN="cloudflare:@cf/openai/gpt-oss-120b,groq:openai/gpt-oss-120b"`.

```
pip install edge-tts numpy soundfile requests
npm ci --prefix remotion
python tools/write_case.py <id> --out episodes/900-test/story.json   # len autor
python tools/lint.py episodes/900-test/story.json                     # len kontrola
python tools/run.py --no-post [--case ID]                             # video do output/, bez Release a bez zmeny stavu
python tools/run.py [--case ID] [--force]                             # ostrý beh: GitHub Release ep-NNN + state.json (treba gh)
```

Offline test opravného kola: `python tools/write_case.py <id> --case-file x.json --fake zla.json dobra.json --out ...`.

## Beh v GitHub Actions

Workflow `PriceTrap Daily` beží denne o 06:10 UTC. Ručne: Actions → PriceTrap Daily → Run workflow
(`case` = id prípadu, `no_post` = len vyrobiť video). Výsledok je v Releases (`ep-NNN`: video, popisok, obal) a ako
artefakt 7 dní. Secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `GROQ_API_KEY` (záloha), voliteľne `GEMINI_API_KEY`
(`GITHUB_TOKEN` dodá GitHub). Buffer zatiaľ netreba.
