// Episode: číta public/<ep>/episode.json (cez Root) a skladá údery za sebou.
import React from "react";
import { AbsoluteFill, Audio, Easing, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { ACCENT, BLUEPRINT, Beat, CAPTION_Y, ClockCtx, COL_W, COL_X, CONTENT_TOP, Ep, EpCtx, H, PAPER, SANS, ThemeCtx, W } from "./theme";
import { BlueprintSection, CaptionPill, Footer, PaperBackground, ReportHeader } from "./Paper";
import { SCENES } from "./Scenes";
import { fitInter, wrapLines } from "./fit";

const Missing: React.FC<{ name: string }> = ({ name }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", fontSize: 50, color: "#E5383B", fontFamily: "monospace" }}>
    unknown scene: {name}
  </AbsoluteFill>
);

export const Episode: React.FC<{ ep: string; data?: Ep }> = ({ ep, data }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  if (!data || !data.beats.length) return <PaperBackground />;
  const t = frame / fps;
  const beats = data.beats;
  const idx = Math.max(0, beats.findIndex((b, i) => t >= b.t0 && (i === beats.length - 1 || t < beats[i + 1].t0)));
  const cur = beats[idx];
  const isBP = (i: number) => beats[i]?.mode === "blueprint";

  // blueprint prelínanie: 0.3 s na začiatku úderu, keď sa mení režim
  const target = isBP(idx) ? 1 : 0;
  const before = idx > 0 && isBP(idx - 1) ? 1 : 0;
  const k = interpolate(t - cur.t0, [0, 0.3], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const bp = before + (target - before) * k;
  const pal = bp > 0.5 ? BLUEPRINT : PAPER;
  const outro = cur.scene === "Outro";
  const headerOpacity = outro ? 1 - k : 1;
  const dir = ep ? `${ep}/` : "";
  const ins = cur.insert;
  const insOn = !!ins && t - cur.t0 >= ins.t && t - cur.t0 < ins.t + ins.d;

  return (
    <EpCtx.Provider value={data}>
    <ClockCtx.Provider value={frame}>
    <ThemeCtx.Provider value={pal}>
      <AbsoluteFill>
        <PaperBackground />
        <BlueprintSection amount={bp} />
        <ReportHeader header={data.header || data.brand} caseName={data.case} opacity={headerOpacity} />
        <Footer source={data.source} t={t} duration={data.duration} opacity={headerOpacity} />
        <AbsoluteFill style={WINDOW}>
        <AbsoluteFill style={camera(beats, idx, t)}>
        {beats.map((b, i) => {
          const from = Math.round(b.t0 * fps);
          const to = i === beats.length - 1 ? durationInFrames : Math.round(beats[i + 1].t0 * fps);
          const Scene = SCENES[b.scene];
          const prevB = beats[i - 1];
          const prev = prevB && prevB.scene === b.scene ? prevB.props ?? {} : undefined;
          const from0 = !prev && b.scene === "Crowd" ? lastCrowd(beats, i) : undefined; // Crowd pokračuje z minulého stavu
          // nová scéna = krátky fade celej scény; rovnaká scéna = plynulé pokračovanie
          return (
            <Sequence key={i} from={from} durationInFrames={Math.max(1, to - from)} layout="none">
              <SceneWrap fade={!prev}>{Scene ? <Scene p={b.props ?? {}} prev={prev ?? from0} /> : <Missing name={b.scene} />}</SceneWrap>
            </Sequence>
          );
        })}
        </AbsoluteFill>
        </AbsoluteFill>
        {insOn && ins ? <InsertCard text={ins.text} u={t - cur.t0 - ins.t} d={ins.d} blueprint={cur.mode === "blueprint"} /> : <CaptionPill words={data.words} t={t} />}
        <Audio src={staticFile(dir + data.voice)} />
        {data.music && <Audio src={staticFile(dir + data.music)} volume={data.music_gain ?? 0.12} />}
        {data.sfx && <Audio src={staticFile(dir + data.sfx)} />}
      </AbsoluteFill>
    </ThemeCtx.Provider>
    </ClockCtx.Provider>
    </EpCtx.Provider>
  );
};

// Veľký text cez celú obrazovku (insert z prep.py): tvrdý strih preč zo scény na ~1 s, keď hlas povie krátku pointu.
// Papier -> čierna plocha s bielym textom, blueprint -> papier s čiernym. Text dopadne (zväčšený -> 1), červená čiara
// sa podčiarkne, potom pomalý nájazd. Titulky sa medzitým skryjú (text na obrazovke je to, čo hlas práve hovorí).
const InsertCard: React.FC<{ text: string; u: number; d: number; blueprint: boolean }> = ({ text, u, d, blueprint }) => {
  const T = text.toUpperCase();
  let size = 200;
  for (const w of T.split(/\s+/)) size = Math.min(size, fitInter(w, COL_W, 200, 60, 900, -0.035));
  while (size > 80 && wrapLines(T, size, COL_W, 900, -0.035) > 3) size *= 0.94;
  const hitIn = 1 + 0.22 * Math.exp(-u / 0.06);
  const push = 1 + (0.05 * u) / Math.max(0.5, d);
  const bar = interpolate(u, [0.1, 0.32], [0, 1], { ...clamp, easing: ease });
  const bg = blueprint ? PAPER.bg : "#111113";
  const ink = blueprint ? PAPER.ink : "#FFFFFF";
  return (
    <AbsoluteFill style={{ background: bg, alignItems: "center", justifyContent: "center" }}>
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(${blueprint ? PAPER.grid : "rgba(255,255,255,0.05)"} 2px, transparent 2px), linear-gradient(90deg, ${blueprint ? PAPER.grid : "rgba(255,255,255,0.05)"} 2px, transparent 2px)`,
          backgroundSize: "54px 54px",
        }}
      />
      <div style={{ transform: `scale(${hitIn * push}) rotate(-2deg)`, width: COL_W, display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: size, letterSpacing: size * -0.035, lineHeight: 0.96, color: ink, textAlign: "center", textWrap: "balance" }}>
          {T}
        </div>
        <div style={{ alignSelf: "center", width: `${bar * 70}%`, height: Math.max(10, size * 0.1), background: ACCENT.red, marginTop: size * 0.16, borderRadius: 6 }} />
      </div>
    </AbsoluteFill>
  );
};

// Okno kamery: obsah priblížený nad hlavičku alebo pod titulky mäkko zmizne (maska stojí, nehýbe sa s kamerou).
// Okno je tesné: pri detaile by inak pod hlavičkou a nad titulkom trčali okraje susedných kariet či stĺpcov.
const MASK = `linear-gradient(to bottom, transparent ${CONTENT_TOP - 35}px, black ${CONTENT_TOP - 5}px, black ${CAPTION_Y - 140}px, transparent ${CAPTION_Y - 90}px)`;
const WINDOW: React.CSSProperties = { maskImage: MASK, WebkitMaskImage: MASK };

// Karty v cenníku (PriceList): rovnaká geometria ako ProductCard (výška 250, medzera 28, odsadenie 10).
const CARD_H = 250, CARD_GAP = 28, CARD_TOP = CONTENT_TOP + 10;
const FOCUS_Y = 820; // kam na obrazovke príde stred detailu
const ORIGIN_Y = H * 0.46; // okolo tohto bodu sa zoomuje celkový záber

/** index karty, ktorá sa v tomto údere objavila alebo zmenila (pečiatka, štítok, cena); inak null */
const focusCard = (b: Beat, prev?: Beat): number | null => {
  if (b.scene !== "PriceList") return null;
  const cards: unknown[] = b.props?.cards ?? [];
  const pc: unknown[] = prev?.scene === "PriceList" ? prev.props?.cards ?? [] : [];
  let k: number | null = null;
  cards.forEach((c, i) => {
    if (JSON.stringify(c) !== JSON.stringify(pc[i])) k = i;
  });
  return k;
};

// Detaily (x, y = bod rozloženia, ktorý príde do stredu; z = priblíženie). Súradnice z rozložení v Scenes/Blocks
// (overené na snímkach 20. 10.). Prvok na celú šírku stĺpca (840 px) znesie najviac z 1.24, inak ho orežú okraje.
// Cenník: karta, ktorá sa zmenila. Outro nemá detaily (má vlastnú pečiatku).
type Focus = { x: number; y: number; z: number };
const cardFocus = (k: number): Focus => ({ x: W / 2, y: CARD_TOP + CARD_H / 2 + k * (CARD_H + CARD_GAP), z: 1.22 });
const FOCI: Record<string, Focus[]> = {
  Hero: [{ x: W / 2, y: 740, z: 1.16 }, { x: W / 2, y: 1060, z: 1.2 }], // objekt, nadpis
  PriceList: [cardFocus(0), cardFocus(2)],
  Statement: [{ x: W / 2, y: 790, z: 1.3 }],
  Anchor: [{ x: 700, y: 560, z: 1.25 }, { x: W / 2, y: 900, z: 1.22 }], // kotva vpravo hore, cena na posuvníku
  Views: [{ x: W / 2, y: 480, z: 1.24 }, { x: W / 2, y: 800, z: 1.2 }], // počítadlo, mriežka
  Compare: [{ x: 757, y: 812, z: 1.45 }, { x: 323, y: 812, z: 1.45 }], // stĺpec AFTER, BEFORE
  Outro: [],
};
// Cenník s guličkou (props.point = [a, b]): obe karty naraz, nech je vidieť celý skok.
const pointFocus = (b: Beat, prev?: Beat): Focus | null => {
  const pt = b.props?.point;
  if (b.scene !== "PriceList" || !Array.isArray(pt) || pt.length !== 2) return null;
  if (prev?.scene === "PriceList" && JSON.stringify(prev.props?.point) === JSON.stringify(pt)) return null;
  const [a, c] = pt.map(Number);
  const span = Math.abs(a - c) * (CARD_H + CARD_GAP) + CARD_H;
  return { x: W / 2, y: CARD_TOP + CARD_H / 2 + ((a + c) / 2) * (CARD_H + CARD_GAP), z: Math.min(1.2, 980 / span) };
};
// Crowd (rozloženie v Crowd.tsx: počítadlá + nádoby + názvy = y 606..1130): všetky nádoby, víťazná nádoba a na
// poslednom zábere pointa úderu = nádoba návnady (nikto ju nechce) alebo pri zmene nádoba, ktorá najviac stratila.
/** props posledného úderu Crowd pred úderom i (Crowd pokračuje tam, kde skončil, aj keď sú medzi nimi iné scény) */
export const lastCrowd = (beats: Beat[], i: number) => {
  for (let j = i - 1; j >= 0; j--) if (beats[j].scene === "Crowd") return beats[j].props ?? {};
  return undefined;
};
const crowdFoci = (b: Beat, prev?: any): { all: Focus; lead: Focus; point: Focus } => {
  const o: any[] = (b.props?.options ?? []).filter((x: any) => x && x.label);
  const all = { x: W / 2, y: 868, z: 1.2 };
  if (o.length < 2) return { all, lead: all, point: all };
  const vals = o.map((x) => Number(x.value) || 0);
  const w = (COL_W - (o.length - 1) * 30) / o.length;
  const bin = (k: number): Focus => ({ x: COL_X + k * (w + 30) + w / 2, y: 868, z: 1.6 });
  const lead = vals.indexOf(Math.max(...vals));
  let point = o.findIndex((x) => x.bait);
  if (point < 0 && Math.min(...vals) < Math.max(...vals)) point = vals.indexOf(Math.min(...vals)); // „Nobody.“ = prázdna nádoba
  const was = new Map<string, number>((prev?.options ?? []).filter((x: any) => x && x.label).map((x: any) => [x.label, Number(x.value) || 0]));
  if (prev && was.size) {
    const loss = o.map((x, k) => (was.get(x.label) ?? vals[k]) - vals[k]);
    point = Math.max(...loss) > 0 ? loss.indexOf(Math.max(...loss)) : -1;
  }
  return { all, lead: bin(lead), point: bin(point >= 0 ? point : lead) };
};

// Kamera nad scénami (hlavička, päta a titulky stoja). Úder sa delí na zábery strihmi zo shots (prep.py, hranice viet
// a čiarok, ~každé 2 s); zábery sa striedajú detail <-> celok, detaily idú po rade z FOCI. Nová scéna začne celkom
// (divák najprv vidí celé rozloženie), pokračovanie tej istej scény detailom; cenník vždy detailom karty, ktorá sa zmenila.
// Medzi zábermi rýchly presun 0,22 s, v zábere pomalý nájazd, na začiatku úderu „cvak“, pri pečiatke otras.
const ease = Easing.out(Easing.cubic);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
type Frame = { s: number; tx: number; ty: number };
const wide = (s: number): Frame => ({ s, tx: (W / 2) * (1 - s), ty: ORIGIN_Y * (1 - s) });
const close = (f: Focus, s: number): Frame => ({ s, tx: W / 2 - f.x * s, ty: FOCUS_Y - f.y * s });
const camera = (beats: Beat[], i: number, t: number): React.CSSProperties => {
  const b = beats[i];
  const u = Math.max(0, t - b.t0);
  const d = Math.max(0.6, b.t1 - b.t0);
  const newScene = i === 0 || beats[i - 1].scene !== b.scene;
  const fk = focusCard(b, beats[i - 1]);
  const pf = pointFocus(b, beats[i - 1]);
  const afterEmpty = b.scene === "Compare" && (b.props?.after ?? []).every((x: unknown) => x == null); // AFTER príde až v ďalšom údere
  const foci = pf ? [pf] : fk != null ? [cardFocus(fk)] : afterEmpty ? [FOCI.Compare[1]] : FOCI[b.scene] ?? [];
  const cuts = [0, ...(b.shots ?? []), d];
  const startClose = foci.length > 0 && (pf != null || fk != null || !newScene);
  // Crowd: celok (nová scéna), potom len detaily: všetky nádoby, víťaz, ...; posledný záber = pointa
  const cf = b.scene === "Crowd" ? crowdFoci(b, lastCrowd(beats, i)) : null;
  const crowdShot = (k: number): Focus | null => {
    if (!cf) return null;
    if (k === 0) return newScene ? null : cf.all;
    if (k === cuts.length - 2) return cf.point;
    return k % 2 ? cf.all : cf.lead;
  };
  // záber k: detail (ktorý z foci) alebo celok; drift = pomalý nájazd počas záberu
  const shot = (k: number, v: number): Frame => {
    const len = Math.max(0.5, cuts[k + 1] - cuts[k]);
    const drift = interpolate(v / len, [0, 1], [0, 1], { ...clamp, easing: Easing.inOut(Easing.quad) });
    const f = cf ? crowdShot(k) : foci.length > 0 && (k % 2 === 0) === startClose ? foci[Math.floor(k / 2) % foci.length] : null;
    if (!f) return wide(1 + 0.025 * drift);
    return close(f, f.z + 0.04 * drift);
  };
  let k = 0;
  while (k < cuts.length - 2 && u >= cuts[k + 1]) k++;
  let fr = shot(k, u - cuts[k]);
  if (k > 0) {
    const m = interpolate(u - cuts[k], [0, 0.22], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
    if (m < 1) {
      const a = shot(k - 1, cuts[k] - cuts[k - 1]);
      fr = { s: a.s + (fr.s - a.s) * m, tx: a.tx + (fr.tx - a.tx) * m, ty: a.ty + (fr.ty - a.ty) * m };
    }
  }
  // „cvak“ na začiatku úderu: krátke priblíženie okolo stredu obrazovky, ktoré odznie za ~0,3 s
  const snap = 1 + (newScene ? 0.06 : 0.025) * Math.exp(-u / 0.12);
  let sx = 0, sy = 0;
  if (b.shake != null && u > b.shake) {
    const a = 9 * Math.exp(-(u - b.shake) / 0.09);
    sx = a * Math.sin((u - b.shake) * 95);
    sy = a * Math.cos((u - b.shake) * 70);
  }
  const s = fr.s * snap;
  const tx = (fr.tx - W / 2) * snap + W / 2 + sx;
  const ty = (fr.ty - ORIGIN_Y) * snap + ORIGIN_Y + sy;
  return { transform: `translate(${tx}px, ${ty}px) scale(${s})`, transformOrigin: "0 0" };
};

const SceneWrap: React.FC<{ fade: boolean; children: React.ReactNode }> = ({ fade, children }) => {
  const f = useCurrentFrame();
  const o = fade ? interpolate(f, [0, 2], [0, 1], { extrapolateRight: "clamp" }) : 1;  // takmer tvrdý strih
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};
