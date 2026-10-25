# Rutina „PriceTrap – banka skriptov“ (Claude, každé 3 dni)

Cieľ: v `bank/scripts/` je vždy **5 nepoužitých skriptov** (hotové story.json), ktoré denný beh v cloude
(`tools/run.py`) premení na video. Free model píše len vtedy, keď je banka prázdna. Rutina beží v Claude
desktop appke (ak bola appka zavretá, spustí sa pri najbližšom otvorení). Video sa tu **nerenderuje** a hlas sa
tu **negeneruje** (šetrí PC aj dennú kvótu Orpheus).

## Postup

1. Repo: `C:\Users\damia\PriceTrap`. Prečítaj `state.json` (`used` = použité prípady) a zoznam
   `bank/scripts/*.json` (len priamo v priečinku, nie `used/`). Nepoužitý skript = jeho `id` nie je v `used`.
2. Ak je nepoužitých skriptov ≥ 5: nič nepíš, vypíš „banka plná (N)“ a skonči.
3. Inak doplň na 5. Pre každý chýbajúci vyber ďalší prípad z `bank/cases.json` (v poradí banky), ktorý nie je
   v `used` a nemá skript v banke. Prípad s `confidence` iným ako `high` preskoč.
4. Pred písaním si prečítaj: `SCRIPT_GUIDE.md` (publikum, háky, štruktúra, checklist – záväzné),
   `SPEC.md` sekcie „Scény a props“ a „Lint“, vzor `episodes/001-economist-decoy/story.json`
   (alebo `bank/scripts/used/*economist-decoy.json`) a `remotion/icons.json` (mená ikon pre `art`).
5. Napíš skript ako story.json (rovnaké kľúče ako vzor: `id` = id prípadu, `case`, `title`, `caption`,
   `source`, `beats`). Pravidlá navyše:
   - Najprv plán (hook, hook_answer, odd_fact, twist, comparison, proof, everyday, rule) – nepíš ho do súboru.
   - Hák v angličtine, otázka o divákovom živote („Ever…?“, „Have you ever…?“, „Why does…?“), šablóny v guide.
   - Pohyb namiesto slajdov: v každom skripte aspoň 1× `Crowd` (ak fakty majú čísla ľudí/predajov) alebo
     `PriceList` s `point` (gulička medzi dvoma cenami), žiadny `Statement` dlhší ako ~14 slov.
   - Každý úder ukazuje presne to, čo hovorí (karta, nádoba, číslo, cena). Čísla len z faktov prípadu.
   - 13–17 úderov, 115–135 slov (s automatickými pauzami ≈ 60–62 s), najviac 850 znakov reči (Orpheus kvóta).
6. Ulož ako `bank/scripts/<YYYY-MM-DD>-<NN>-<id>.json` (dnešný dátum, NN = 01, 02… v rámci dňa).
7. Kontrola: `python -I -X utf8 tools/lint.py bank/scripts/<súbor>` musí vypísať `OK`. Opravuj podľa chýb,
   najviac 3 kolá; ak stále neprejde, súbor zmaž a prípad preskoč (zapíš do správy prečo).
8. Potom checklist zo `SCRIPT_GUIDE.md` (10 otázok) – každá odpoveď ÁNO, inak oprav.
9. Ak ostáva < 10 nepoužitých prípadov v `bank/cases.json`, len to napíš do správy (nové prípady pridáva
   Damián s Claude ručne, s overenými zdrojmi – rutina si fakty nevymýšľa).
10. Git: `git add bank/scripts` a `git commit -m "bank: +N skriptov (<id>, …)"`.
    **PUSH: ZAKÁZANÝ** – kým tu nebude napísané „PUSH: POVOLENÝ (dátum, Damián)“. Bez pushu cloud skripty nevidí.
11. Správa (po slovensky, 2–4 riadky): koľko skriptov bolo, koľko pribudlo (id + hák), čo neprešlo, koľko
    prípadov ostáva, či sa pushlo.

## Zákazy

Žiadne kľúče/heslá/tokeny (neotvárať ani nevypisovať `.env`), žiadne platené služby, žiadne volania TTS
ani renderu, nemazať nič mimo vlastných nových súborov v `bank/scripts/`, nemeniť kód ani `state.json`.
