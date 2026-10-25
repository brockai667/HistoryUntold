// Crowd: bodky = ľudia, ktorí si vyberajú. props: job, options[{label, art, value, bait}], total
// Prvý úder: dav bodiek hore (total, predvolene 100) sa rozbehne do nádob možností, počítadlá rastú s dopadmi.
// Ďalší úder tej istej scény so zmenenými hodnotami: možnosť, ktorá zmizla, vybledne (nová sa objaví), nádoby sa preskupia a prebytočné
// bodky preskáču oblúkom do nádoby, ktorá rastie. Bodky sú rovnaké, takže stav nádoby = len počet (sloty 0..value-1 zdola).
// Časovanie dopadov musí sedieť s tools/sfx.py (CROWD_*): zvuk korálok padá presne s bodkami.
import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { ACCENT, CAPTION_Y, COL_W, COL_X, CONTENT_TOP, SANS, TagT, useTheme } from "./theme";
import { Art, Tag, fmt, usePop } from "./Paper";
import { fitInter } from "./fit";

type Opt = { label: string; art?: string; value: number; bait?: boolean };
type P = { p: any; prev?: any };

// časovanie v snímkach (rovnaké čísla v sfx.py)
export const CROWD_DELAY = 6; // odchod prvej bodky
export const CROWD_SPREAD = 44; // za koľko snímok odíde posledná bodka
export const CROWD_FLY = 16; // let jednej bodky z davu do nádoby
export const CROWD_MOVE_DELAY = 14; // pri zmene: prvý preskok (po vyblednutí a preskupení nádob)
export const CROWD_MOVE_SPREAD = 36;
export const CROWD_MOVE_FLY = 18;

// rozloženie v súradniciach plochy scény (šírka COL_W, začiatok CONTENT_TOP)
const AREA_H = CAPTION_Y - 120 - CONTENT_TOP; // 970
const POOL_COLS = 20, POOL_GAP = 34, POOL_TOP = 92, POOL_DOT = 20;
const BIN_TOP = 372, BIN_H = 350, BIN_GAP = 30, SLOT = 24, DOT = 18;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const inOut = Easing.inOut(Easing.cubic);

const optsOf = (p: any): Opt[] =>
  (Array.isArray(p?.options) ? p.options : [])
    .filter((o: any) => o && o.label)
    .map((o: any) => ({ ...o, label: String(o.label), value: Math.max(0, Math.round(Number(o.value) || 0)) }));

const binLayout = (n: number) => {
  const w = (COL_W - (n - 1) * BIN_GAP) / Math.max(1, n);
  return { w, x: (k: number) => k * (w + BIN_GAP), cols: Math.max(1, Math.floor((w - 16) / SLOT)) };
};
/** stred slotu s (zdola, po riadkoch) v nádobe k z n */
const slotPos = (n: number, k: number, s: number) => {
  const L = binLayout(n);
  const r = Math.floor(s / L.cols), c = s % L.cols;
  const x0 = L.x(k) + (L.w - L.cols * SLOT) / 2;
  return { x: x0 + c * SLOT + SLOT / 2, y: BIN_TOP + BIN_H - 12 - r * SLOT - SLOT / 2 };
};
const poolPos = (id: number) => {
  const x0 = (COL_W - (POOL_COLS - 1) * POOL_GAP) / 2;
  return { x: x0 + (id % POOL_COLS) * POOL_GAP, y: POOL_TOP + Math.floor(id / POOL_COLS) * POOL_GAP };
};

/** poradie bodiek pri odchode z davu: deterministicky zamiešané (vyzerá prirodzene, render je vždy rovnaký) */
const shuffled = (n: number) => {
  const a = Array.from({ length: n }, (_, i) => i);
  let s = 7;
  for (let i = n - 1; i > 0; i--) {
    s = (s * 1103515245 + 12345) % 2147483648;
    const j = s % (i + 1);
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
};
/** k-ta odchádzajúca bodka ide do nádoby, ktorej chýba najväčší podiel -> všetky nádoby sa plnia naraz a skončia spolu */
const fillOrder = (values: number[]) => {
  const got = values.map(() => 0);
  const out: number[] = [];
  const sum = values.reduce((a, b) => a + b, 0);
  for (let k = 0; k < sum; k++) {
    let best = -1, bestR = -1;
    values.forEach((v, b) => {
      const r = v > 0 ? (v - got[b]) / v : -1;
      if (r > bestR || (r === bestR && v > values[best])) { best = b; bestR = r; }
    });
    got[best]++;
    out.push(best);
  }
  return out;
};

type Dot = { x: number; y: number; o?: number };

export const Crowd: React.FC<P> = ({ p, prev }) => {
  const pal = useTheme();
  const f = useCurrentFrame();
  const total = Math.max(1, Math.round(Number(p.total) || 100));
  const cur = optsOf(p);
  const old = prev ? optsOf(prev) : null;
  const changed = !!old && JSON.stringify(old) !== JSON.stringify(cur);
  const jobPop = usePop(2, !prev || JSON.stringify(prev.job) !== JSON.stringify(p.job));
  const n = cur.length;
  const L = binLayout(n);
  const dots: Dot[] = [];
  const count = cur.map((o) => o.value); // čo ukazujú počítadlá v tejto snímke
  const binX = cur.map((_, k) => L.x(k)); // poloha nádob v tejto snímke (pri zmene sa posúvajú)
  const gone: { o: Opt; x: number; w: number; a: number }[] = []; // nádoby, ktoré zmizli (blednú)
  const binA = cur.map(() => 1); // nová nádoba (pri zmene) sa objaví počas preskupenia

  if (!old) {
    // prvý úder: dav -> nádoby
    const order = shuffled(total);
    const seq = fillOrder(cur.map((o) => o.value));
    const filled = cur.map(() => 0);
    count.fill(0);
    const leaving = new Set<number>();
    seq.forEach((b, k) => {
      const id = order[k];
      leaving.add(id);
      const s = filled[b]++;
      const start = CROWD_DELAY + (k * CROWD_SPREAD) / Math.max(1, seq.length);
      const t = interpolate(f - start, [0, CROWD_FLY], [0, 1], clamp);
      const a = poolPos(id), z = slotPos(n, b, s);
      let y = a.y + (z.y - a.y) * t * t - 110 * t * (1 - t);
      const g = f - start - CROWD_FLY;
      if (g >= 0) {
        count[b]++;
        if (g < 8) y -= 9 * Math.sin((Math.PI * g) / 8) * (1 - g / 8); // odskok pri dopade
      }
      dots.push({ x: a.x + (z.x - a.x) * inOut(t), y });
    });
    for (let id = 0; id < total; id++) if (!leaving.has(id)) dots.push({ ...poolPos(id), o: 0.3 }); // nikto z nich nevolil
  } else {
    // zmena: zmiznuté nádoby blednú, ostatné sa presunú na nové miesta, prebytok preskáče
    const oldN = old.length;
    const oldIdx = new Map(old.map((o, k) => [o.label, k]));
    const curIdx = new Map(cur.map((o, k) => [o.label, k]));
    const lay = changed ? inOut(interpolate(f, [6, 20], [0, 1], clamp)) : 1;
    const fade = changed ? interpolate(f, [0, 10], [1, 0], clamp) : 0;
    const LO = binLayout(oldN);
    cur.forEach((o, k) => {
      const j = oldIdx.get(o.label);
      if (j != null) binX[k] = LO.x(j) + (L.x(k) - LO.x(j)) * lay;
      else binA[k] = lay;
    });
    old.forEach((o, j) => {
      if (!curIdx.has(o.label)) gone.push({ o, x: LO.x(j), w: LO.w, a: fade });
    });
    // kto ostáva sedieť, kto odchádza (zhora) a kam pribúda
    const movers: { x: number; y: number }[] = [];
    const targets: { k: number; s: number }[] = [];
    old.forEach((o, j) => {
      const k = curIdx.get(o.label);
      const keep = k == null ? 0 : Math.min(o.value, cur[k].value);
      for (let s = o.value - 1; s >= keep; s--) movers.push(slotPos(oldN, j, s));
    });
    cur.forEach((o, k) => {
      const j = oldIdx.get(o.label);
      const was = j == null ? 0 : old[j].value;
      for (let s = was; s < o.value; s++) targets.push({ k, s });
      count[k] = was; // počítadlo začína starou hodnotou a mení sa s každým dopadom
      // sediace bodky sa posúvajú spolu s nádobou
      for (let s = 0; s < Math.min(was, o.value); s++) {
        const a = slotPos(oldN, j as number, s), z = slotPos(n, k, s);
        dots.push({ x: a.x + (z.x - a.x) * lay, y: a.y + (z.y - a.y) * lay });
      }
    });
    const m = Math.max(movers.length, targets.length);
    for (let i = 0; i < m; i++) {
      const from = movers[i] ?? poolPos(i % total); // viac cieľov ako bodiek: noví prídu z davu
      const to = targets[i];
      const start = CROWD_MOVE_DELAY + (i * CROWD_MOVE_SPREAD) / Math.max(1, m);
      const t = changed ? interpolate(f - start, [0, CROWD_MOVE_FLY], [0, 1], clamp) : 1;
      if (to) {
        const z = slotPos(n, to.k, to.s);
        const arc = 150 * Math.sin(Math.PI * t);
        dots.push({ x: from.x + (z.x - from.x) * inOut(t), y: from.y + (z.y - from.y) * t - arc });
        if (t >= 1) count[to.k]++;
      } else {
        dots.push({ x: from.x, y: from.y - 160 * t, o: 1 - t }); // menej cieľov: bodka odletí a zmizne
      }
    }
    // počítadlo nádoby, z ktorej bodky odchádzajú, klesá s každým odletom
    old.forEach((o, j) => {
      const k = curIdx.get(o.label);
      if (k == null) return;
      const leave = Math.max(0, o.value - cur[k].value);
      if (!leave) return;
      let before = 0;
      for (let jj = 0; jj < j; jj++) {
        const kk = curIdx.get(old[jj].label);
        before += Math.max(0, old[jj].value - (kk == null ? 0 : cur[kk].value));
      }
      let left = 0;
      for (let i = before; i < before + leave; i++) {
        const start = CROWD_MOVE_DELAY + (i * CROWD_MOVE_SPREAD) / Math.max(1, m);
        if (!changed || f >= start) left++;
      }
      count[k] -= left;
    });
  }

  const ink = pal.name === "blueprint" ? pal.cardLine : pal.ink;
  const lead = Math.max(...cur.map((o) => o.value));
  return (
    <div style={{ position: "absolute", top: CONTENT_TOP, left: COL_X, width: COL_W, height: AREA_H }}>
      {p.job && (
        <div style={{ ...jobPop, position: "absolute", top: 0, left: 0, width: COL_W, display: "flex", justifyContent: "center" }}>
          <Tag tag={typeof p.job === "string" ? ({ text: p.job, tone: "dark" } as TagT) : p.job} size={26} maxWidth={COL_W} />
        </div>
      )}
      {gone.map((g, i) => (
        <Bin key={`g${i}`} o={g.o} x={g.x} w={g.w} count={0} opacity={g.a} lead={false} />
      ))}
      {cur.map((o, k) => (
        <Bin key={o.label} o={o} x={binX[k]} w={L.w} count={count[k]} opacity={binA[k]} lead={o.value === lead && lead > 0} />
      ))}
      {dots.map((d, i) => (
        <div
          key={i}
          style={{
            position: "absolute", left: d.x - DOT / 2, top: d.y - DOT / 2, width: d.y < BIN_TOP - 40 ? POOL_DOT : DOT, height: d.y < BIN_TOP - 40 ? POOL_DOT : DOT,
            borderRadius: "50%", background: ink, opacity: d.o ?? 1,
            boxShadow: pal.name === "blueprint" ? `0 0 8px ${pal.glow}` : "0 2px 0 rgba(0,0,0,0.18)",
          }}
        />
      ))}
    </div>
  );
};

/** nádoba: počítadlo nad ňou, otvorená zhora, pod ňou ikona + názov možnosti; návnada má červený čiarkovaný obrys */
const Bin: React.FC<{ o: Opt; x: number; w: number; count: number; opacity: number; lead: boolean }> = ({ o, x, w, count, opacity, lead }) => {
  const pal = useTheme();
  const line = o.bait ? ACCENT.red : pal.cardLine;
  const labelS = fitInter(o.label, w - 76, 34, 18, 900, -0.02);
  const numS = 92;
  return (
    <div style={{ position: "absolute", left: x, top: 0, width: w, height: AREA_H, opacity }}>
      <div
        style={{
          position: "absolute", top: BIN_TOP - numS - 6, width: w, textAlign: "center", fontFamily: SANS, fontWeight: 900, fontSize: numS,
          letterSpacing: numS * -0.03, lineHeight: 1, fontVariantNumeric: "tabular-nums",
          color: o.bait ? ACCENT.red : pal.name === "blueprint" ? (lead ? ACCENT.gold : pal.ink) : pal.ink,
        }}
      >
        {fmt(count)}
      </div>
      <div
        style={{
          position: "absolute", top: BIN_TOP, left: 0, width: w, height: BIN_H, boxSizing: "border-box",
          borderLeft: `${lead ? 5 : 3}px ${o.bait ? "dashed" : "solid"} ${line}`, borderRight: `${lead ? 5 : 3}px ${o.bait ? "dashed" : "solid"} ${line}`,
          borderBottom: `${lead ? 5 : 3}px ${o.bait ? "dashed" : "solid"} ${line}`, borderRadius: "0 0 28px 28px",
          background: pal.name === "blueprint" ? "rgba(70,120,190,0.12)" : "rgba(248,247,243,0.7)",
        }}
      />
      <div style={{ position: "absolute", top: BIN_TOP + BIN_H + 18, width: w, display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}>
        {o.art && o.art !== "none" && <Art kind={o.art} width={62} />}
        <span style={{ fontFamily: SANS, fontWeight: 900, fontSize: labelS, letterSpacing: labelS * -0.02, color: o.bait ? ACCENT.red : pal.ink, whiteSpace: "nowrap" }}>
          {o.label}
        </span>
      </div>
    </div>
  );
};
