// Odhad šírky textu a zmenšovanie fontu podľa dĺžky. Pravidlo: text sa nikdy neorezáva (žiadne ellipsis)
// a nezalamuje mimo; keď sa nezmestí, zmenší sa písmo (po spodnú hranicu `min`).
// Šírky znakov Inter sú zmerané v Chromiu (fit-metrics.ts), JetBrains Mono má 0.6 em na znak.
import { INTER_ADV, INTER_TAB } from "./fit-metrics";

/** Rezerva 3 % (kerning, zaokrúhľovanie, iné prostredie ako merané). */
const SAFE = 0.97;
/** Šírka znaku mimo tabuľky (em) – konzervatívne. */
const DEF = 0.85;

export type InterW = 800 | 900;

const isDigit = (c: string) => c >= "0" && c <= "9";

/** Šírka textu v em (Inter) vrátane letterSpacing (lsEm × počet znakov). `tab` = tabular-nums. */
export const interEm = (text: string, weight: InterW = 900, lsEm = 0, tab = false): number => {
  const t = INTER_ADV[weight];
  let u = 0;
  let n = 0;
  for (const ch of text == null ? "" : String(text)) {
    n++;
    u += tab && isDigit(ch) ? INTER_TAB[weight] : t[ch] ?? DEF;
  }
  return u + n * lsEm;
};

/** Šírka textu v em (JetBrains Mono): 0.6 em na znak; znaky mimo latinky (→ ▶ …) berieme ako 1 em. */
export const monoEm = (text: string, lsEm = 0): number => {
  let u = 0;
  for (const ch of text == null ? "" : String(text)) u += (ch.codePointAt(0) ?? 0) <= 0x24f ? 0.6 + lsEm : 1 + lsEm;
  return u;
};

const solve = (em: number, avail: number, base: number, min: number) =>
  em > 0 ? Math.max(min, Math.min(base, (avail * SAFE) / em)) : base;

/** Veľkosť písma (px) pre Inter text, aby sa zmestil do `avail` px. `extraEm` = vodorovné odsadenie v em (padding). */
export const fitInter = (text: string, avail: number, base: number, min: number, weight: InterW = 900, lsEm = 0, tab = false, extraEm = 0) =>
  solve(interEm(text, weight, lsEm, tab) + extraEm, avail, base, min);

/** To isté pre JetBrains Mono. */
export const fitMono = (text: string, avail: number, base: number, min: number, lsEm = 0, extraEm = 0) =>
  solve(monoEm(text, lsEm) + extraEm, avail, base, min);

/* ---------- štítky (Tag: mono, letterSpacing 0.12 em, padding 0.7 em, rámik 2 × 2 px) ---------- */
export const TAG_LS = 0.12;
export const TAG_PADX = 0.7;
export const TAG_BORDER = 4;

export const tagW = (text: string, size: number) => (monoEm(text, TAG_LS) + 2 * TAG_PADX) * size + TAG_BORDER;
export const tagH = (size: number) => size * 1.6 + TAG_BORDER;

/** Veľkosť jedného štítka, aby sa zmestil do `avail` px. */
export const fitTag = (text: string, avail: number, size: number, min = 10) =>
  Math.max(min, Math.min(size, ((avail - TAG_BORDER) * SAFE) / (monoEm(text, TAG_LS) + 2 * TAG_PADX)));

/** Rozloženie riadka štítkov: najprv zmenšovanie (po `min`), potom zalomenie do viac riadkov pri veľkosti `min`. */
export const layoutTags = (texts: string[], avail: number, base: number, min: number, gap: number): { size: number; rows: number } => {
  const n = texts.length;
  if (!n) return { size: base, rows: 0 };
  const oneRow = (s: number) => texts.reduce((a, t) => a + tagW(t, s), 0) + gap * (n - 1);
  if (oneRow(base) <= avail) return { size: base, rows: 1 };
  const em = texts.reduce((a, t) => a + monoEm(t, TAG_LS) + 2 * TAG_PADX, 0);
  const shrunk = (avail * SAFE - TAG_BORDER * n - gap * (n - 1)) / em;
  if (shrunk >= min) return { size: shrunk, rows: 1 };
  const widest = texts.reduce((a, t) => (t.length > a.length ? t : a), "");
  const size = Math.min(min, fitTag(widest, avail, min, 8));
  let rows = 1;
  let x = 0;
  for (const t of texts) {
    const w = tagW(t, size);
    if (x === 0) x = w;
    else if (x + gap + w <= avail * SAFE) x += gap + w;
    else {
      rows++;
      x = w;
    }
  }
  return { size, rows };
};

/** Počet riadkov, na ktoré sa zalomí `text` (Inter) pri veľkosti `size` v šírke `avail` (hladové zalamovanie). */
export const wrapLines = (text: string, size: number, avail: number, weight: InterW = 900, lsEm = 0): number => {
  const space = (INTER_ADV[weight][" "] + lsEm) * size;
  let lines = 1;
  let x = 0;
  for (const w of String(text ?? "").split(/\s+/).filter(Boolean)) {
    const ww = interEm(w, weight, lsEm) * size;
    if (x === 0) x = ww;
    else if (x + space + ww <= avail * SAFE) x += space + ww;
    else {
      lines++;
      x = ww;
    }
  }
  return lines;
};
