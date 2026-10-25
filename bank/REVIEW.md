# Recenzia skriptu Plain Sight (brána pred pushom)

Tento súbor dostane **nezávislý recenzent** (agent `setrny-recenzent`, Opus, len číta). Autor skriptu sa
neposudzuje sám: recenzent nevidí autorov plán ani jeho zdôvodnenie, iba súbory nižšie. Push do cloudu ide len
so skriptom, ktorý dostal `PASS`.

## Čo recenzent dostane

- cestu k skriptu `bank/scripts/<súbor>.json` (lint už prešiel)
- `id` prípadu → záznam v `bank/cases.json` (jediný zdroj faktov)
- `SCRIPT_GUIDE.md` (sekcia 5 Checklist je záväzná), `SPEC.md` sekcia „Scény a props“, `remotion/icons.json`
- vzor schváleného dielu: `bank/scripts/used/*economist-decoy.json` (alebo `bank/scripts/2026-10-25-01-economist-decoy.json`)

## Kritériá (každé musí byť ÁNO, inak FAIL)

1. **Fakty.** Každé číslo, meno, rok a tvrdenie o prípade je v `facts`/`names` prípadu. Nič navyše,
   nič zaokrúhlené ani prehodené (kto, kedy, koľko ľudí, aké ceny). Výnimky: čísla 1–3 a ceny v bežnom príklade.
2. **Checklist zo `SCRIPT_GUIDE.md`**, otázky 1–10: každá ÁNO.
3. **Hák.** Otázka o divákovom živote („Ever…?“, „Have you ever…?“, „Why does…?“), do 12 slov, bez čísla,
   značky a názvu triku. Jeden úder neskôr na ňu priamo odpovedá.
4. **Pohyb.** Aspoň 1× `Crowd` (ak fakty majú počty ľudí) alebo `PriceList` s `point`. Žiadny `Statement`
   dlhší ako ~14 slov. Žiadne dva rovnaké statické zábery za sebou.
5. **Obraz = reč.** Každý úder ukazuje presne to, čo hovorí (karta, nádoba, číslo, cena). Ikony `art` existujú
   v `remotion/icons.json` a sedia k veci.
6. **Zrozumiteľnosť.** Po jednom pozretí vie 12-ročný povedať trik jednou vetou. Žiadna veta nepotrebuje
   pretočiť video späť. Žiadne opakovanie tej istej myšlienky inými slovami.
7. **Popisok.** `caption` 1–2 krátke vety po anglicky, bez hashtagov (pridá ich `brand.json`), bez emoji spamu,
   bez nepravdy a clickbaitu, ktorý video nesplní.
8. **Bezpečnosť.** Nič urážlivé, žiadne finančné rady, žiadne meno súkromnej osoby, žiadne tvrdenie, ktoré
   by ohrozilo kanál (zdravie, politika).

## Výstup recenzenta (presne takto)

```
VERDIKT: PASS | FAIL
PROBLÉMY:
- <úder N / pole>: <čo je zle> → <ako to opraviť>
```

Pri `PASS` môže zoznam obsahovať len drobnosti, ktoré nebránia pushu. Pri pochybnosti o fakte = `FAIL`.
