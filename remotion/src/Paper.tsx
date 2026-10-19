// Základné prvky: pozadie, hlavička, pätka, štítok, pečiatka, počítadlo, titulky, auto a ikony (Art).
import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import {
  ACCENT, BLUEPRINT, CAPTION_Y, COL_W, COL_X, FOOTER_Y, MONO, PAPER, Palette, SANS, TAG_TONES, TagT, Word, useTheme,
} from "./theme";
import { ICONS } from "./icons";
import { fitInter, fitMono, fitTag } from "./fit";

/* ---------- pohyb: málo a presne ---------- */
const easeOut = Easing.bezier(0.16, 1, 0.3, 1);

/** Posun + fade. fresh=false => prvok tu už bol v minulom údere, nehýbe sa. */
export const useEnter = (delay = 0, fresh = true, dist = 36, dur = 12) => {
  const f = useCurrentFrame();
  if (!fresh) return { opacity: 1, transform: "translateY(0px)" };
  const p = interpolate(f - delay, [0, dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOut });
  return { opacity: p, transform: `translateY(${(1 - p) * dist}px)` };
};

/** Malé „pop" pre štítky a pilulky. */
export const usePop = (delay = 0, fresh = true) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (!fresh) return { opacity: 1, transform: "scale(1)" };
  const s = spring({ frame: f - delay, fps, config: { damping: 14, stiffness: 180 } });
  return { opacity: Math.min(1, s * 1.5), transform: `scale(${0.6 + 0.4 * s})` };
};

/* ---------- PaperBackground + BlueprintSection ---------- */
const Grid: React.FC<{ pal: Palette }> = ({ pal }) => (
  <AbsoluteFill
    style={{
      background: pal.bg,
      backgroundImage: `linear-gradient(${pal.grid} 2px, transparent 2px), linear-gradient(90deg, ${pal.grid} 2px, transparent 2px)`,
      backgroundSize: "54px 54px",
    }}
  >
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, transparent 55%, ${pal.vignette} 100%)` }} />
  </AbsoluteFill>
);

export const PaperBackground: React.FC = () => <Grid pal={PAPER} />;

/** Inverzná tmavomodrá pasáž. amount 0..1 = prelínanie cez papier. */
export const BlueprintSection: React.FC<{ amount: number }> = ({ amount }) =>
  amount <= 0 ? null : (
    <AbsoluteFill style={{ opacity: amount }}>
      <Grid pal={BLUEPRINT} />
    </AbsoluteFill>
  );

/* ---------- ReportHeader: "<header> · CASE · <case>" (jeden riadok, dlhší text zmenší písmo) ---------- */
export const ReportHeader: React.FC<{ header: string; caseName: string; opacity?: number }> = ({ header, caseName, opacity = 1 }) => {
  const pal = useTheme();
  const fs = fitMono(`${header} · CASE · ${caseName}`, COL_W, 24, 14, 1 / 6);
  return (
    <div
      style={{
        position: "absolute", top: 210, left: COL_X, width: COL_W, opacity, whiteSpace: "nowrap",
        fontFamily: MONO, fontSize: fs, letterSpacing: fs / 6, color: pal.muted, fontWeight: 500,
      }}
    >
      <b style={{ color: pal.ink, fontWeight: 800 }}>{header}</b> · CASE · {caseName}
    </div>
  );
};

/* ---------- Footer: tenký progres (t / duration) + "SOURCE · <source>" pod titulkami ---------- */
export const Footer: React.FC<{ source?: string; t: number; duration: number; opacity?: number }> = ({ source, t, duration, opacity = 1 }) => {
  const pal = useTheme();
  const p = duration > 0 ? Math.max(0, Math.min(1, t / duration)) : 0;
  const text = source && source.trim() ? `SOURCE · ${source.trim()}` : "";
  const fs = fitMono(text, COL_W, 22, 12, 0.05);
  return (
    <div style={{ position: "absolute", top: FOOTER_Y, left: COL_X, width: COL_W, opacity }}>
      <div style={{ height: 4, borderRadius: 2, background: pal.dashed, overflow: "hidden" }}>
        <div style={{ width: `${p * 100}%`, height: "100%", background: pal.muted }} />
      </div>
      {text && (
        <div
          style={{
            marginTop: 14, fontFamily: MONO, fontSize: fs, letterSpacing: fs * 0.05, color: pal.muted, fontWeight: 500,
            whiteSpace: "nowrap", lineHeight: 1.3,
          }}
        >
          {text}
        </div>
      )}
    </div>
  );
};

/* ---------- Tag (pilulka-štítok) ---------- */
export const tagOf = (t: TagT) => (typeof t === "string" ? { text: t, tone: "plain" as const } : { tone: "plain" as const, ...t });

/** maxWidth = najväčšia šírka štítka v px; dlhší text zmenší písmo (nikdy nezalomí ani neoreže). */
export const Tag: React.FC<{ tag: TagT; size?: number; maxWidth?: number; style?: React.CSSProperties }> = ({ tag, size: size0 = 20, maxWidth, style }) => {
  const pal = useTheme();
  const t = tagOf(tag);
  const size = maxWidth ? fitTag(t.text, maxWidth, size0, 10) : size0;
  let c = TAG_TONES[t.tone ?? "plain"] ?? TAG_TONES.plain;
  if (pal.name === "blueprint" && (t.tone === "plain" || t.tone === "blue" || t.tone === "dark"))
    c = { bg: "rgba(10,20,40,0.45)", fg: "#DFF4FF", line: pal.glow };
  return (
    <span
      style={{
        display: "inline-block", fontFamily: MONO, fontWeight: 700, fontSize: size, letterSpacing: size * 0.12,
        padding: `${size * 0.3}px ${size * 0.7}px`, borderRadius: 999, background: c.bg,
        color: c.fg === "currentColor" ? pal.ink : c.fg, border: `2px solid ${c.line === "currentColor" ? pal.ink : c.line}`,
        whiteSpace: "nowrap", lineHeight: 1, ...style,
      }}
    >
      {t.text}
    </span>
  );
};

/* ---------- Stamp: dopadne 1.4 -> 1 ---------- */
export const Stamp: React.FC<{ text: string; size?: number; maxWidth?: number; delay?: number; fresh?: boolean; rotate?: number; style?: React.CSSProperties }> = ({
  text, size: size0 = 120, maxWidth, delay = 0, fresh = true, rotate = -8, style,
}) => {
  const pal = useTheme();
  // maxWidth = šírka pečiatky aj s rámikom a natočením; dlhší text zmenší písmo
  const size = maxWidth ? fitInter(text, maxWidth, size0, 14, 900, 0.04, false, 0.8) : size0;
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = fresh ? spring({ frame: f - delay, fps, config: { damping: 11, stiffness: 160, mass: 0.8 } }) : 1;
  const scale = 1.4 - 0.4 * s;
  const opacity = fresh ? interpolate(f - delay, [0, 4], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 1;
  return (
    <div
      style={{
        display: "inline-block", transform: `rotate(${rotate}deg) scale(${scale})`, opacity: opacity * 0.92,
        border: `${Math.max(3, size * 0.07)}px solid ${ACCENT.red}`, borderRadius: size * 0.12, padding: `${size * 0.06}px ${size * 0.22}px`,
        color: ACCENT.red, fontFamily: SANS, fontWeight: 900, fontSize: size, letterSpacing: size * 0.04, lineHeight: 1,
        background: "rgba(229,56,59,0.10)", boxShadow: `inset 0 0 0 ${Math.max(2, size * 0.025)}px rgba(255,255,255,0.35)`,
        mixBlendMode: pal.name === "paper" ? "multiply" : "normal", ...style,
      }}
    >
      {text}
    </div>
  );
};

/* ---------- Counter: čísla naskakujú ---------- */
export const fmt = (n: number) => Math.round(n).toLocaleString("en-US");

export const Counter: React.FC<{ from?: number; to: number; prefix?: string; suffix?: string; delay?: number; dur?: number; fresh?: boolean; style?: React.CSSProperties }> = ({
  from = 0, to, prefix = "", suffix = "", delay = 4, dur = 40, fresh = true, style,
}) => {
  const f = useCurrentFrame();
  const p = fresh ? interpolate(f - delay, [0, dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) }) : 1;
  const v = from + (to - from) * p;
  return (
    <span style={{ fontVariantNumeric: "tabular-nums", ...style }}>
      {prefix}
      {fmt(v)}
      {p >= 1 ? suffix : ""}
    </span>
  );
};

/* ---------- CarArt: jednoduché SVG auto (čiarová kresba) ---------- */
export const CarArt: React.FC<{ kind?: string; width?: number; style?: React.CSSProperties }> = ({ kind = "car", width = 300, style }) => {
  const pal = useTheme();
  const f = useCurrentFrame();
  if (kind === "none") return null;
  const fly = kind === "car-fly";
  const body = kind === "car-red" ? (pal.name === "blueprint" ? "rgba(229,56,59,0.25)" : "#D93A3E") : pal.carBody;
  const line = pal.carLine;
  const bob = fly ? Math.sin(f / 9) * 4 : 0;
  const glow = pal.name === "blueprint" ? `drop-shadow(0 0 6px ${pal.glow})` : "none";
  return (
    <svg viewBox="0 0 300 170" width={width} height={(width * 170) / 300} style={{ overflow: "visible", filter: glow, ...style }}>
      <defs>
        <linearGradient id="beam" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#8FD3FF" stopOpacity="0.95" />
          <stop offset="1" stopColor="#8FD3FF" stopOpacity="0" />
        </linearGradient>
      </defs>
      {fly &&
        [70, 235].map((x, i) => (
          <rect key={x} x={x - 13} y={100 + bob} width={26} height={62 + 6 * Math.sin(f / 3 + i)} fill="url(#beam)" rx={8} />
        ))}
      {!fly && <ellipse cx={150} cy={104} rx={140} ry={6} fill="rgba(0,0,0,0.12)" />}
      <g transform={`translate(0 ${bob})`} stroke={line} strokeWidth={4} strokeLinejoin="round" strokeLinecap="round">
        <path d="M12 82 C12 70 24 64 42 62 L96 56 C118 40 142 31 176 31 C206 31 226 41 246 56 L276 62 C289 64 293 72 293 82 L293 88 L12 88 Z" fill={body} />
        <path d="M112 56 C127 44 147 38 172 38 C194 38 211 45 226 56 Z" fill={pal.name === "blueprint" ? "rgba(140,210,255,0.15)" : "#CFE3EE"} />
        <line x1={168} y1={38} x2={166} y2={56} />
        <line x1={150} y1={62} x2={150} y2={84} strokeWidth={2.5} />
        {[70, 235].map((x) => (
          <g key={x}>
            <circle cx={x} cy={88} r={19} fill={pal.name === "blueprint" ? "#1D2A4C" : "#2A2A2E"} />
            <circle cx={x} cy={88} r={8} fill={pal.name === "blueprint" ? "#1D2A4C" : "#BDBDBD"} />
          </g>
        ))}
      </g>
    </svg>
  );
};

/* ---------- IconArt: lucide ikona v rovnakom čiarovom "jazyku" ako auto ---------- */
// width = ten istý parameter ako pri CarArt (krabica 300×170), takže ikonu možno vymeniť za auto bez zmeny rozloženia.
// Ikona je v krabici vystredená, jej strana = ICON_K × width.
const ICON_K = 0.5;
const ICON_STROKE = 1.1; // hrúbka čiary v jednotkách 24×24 (auto má čiaru 4/300 šírky)
const RED_SCALE = 0.78; // červený podklad: ikona sa o kúsok zmenší, aby sa vošla do kruhu
const hasIcon = (n: string) => Object.prototype.hasOwnProperty.call(ICONS, n);

/** `name-red` = ikona s červeným nádychom ako `car-red` (červený kruh za čiarovou ikonou; v blueprinte priesvitný). */
export const IconArt: React.FC<{ name: string; width?: number; style?: React.CSSProperties }> = ({ name, width = 300, style }) => {
  const pal = useTheme();
  let n = name;
  let red = false;
  if (!hasIcon(n) && n.endsWith("-red")) {
    n = n.slice(0, -4);
    red = true;
  }
  if (!hasIcon(n)) return null; // neznáma ikona: nič sa nevykreslí, nič nespadne
  const bp = pal.name === "blueprint";
  const vw = 24 / ICON_K;
  const vh = (vw * 170) / 300;
  const glow = bp ? `drop-shadow(0 0 6px ${pal.glow})` : "none";
  const k = red ? RED_SCALE : 1;
  return (
    <svg
      viewBox={`${12 - vw / 2} ${12 - vh / 2} ${vw} ${vh}`} width={width} height={(width * 170) / 300}
      style={{ overflow: "visible", filter: glow, color: pal.carLine, ...style }}
    >
      {red && <circle cx={12} cy={12} r={11.6} fill={bp ? "rgba(229,56,59,0.25)" : "#D93A3E"} />}
      <g
        fill="none" stroke={pal.carLine} strokeWidth={ICON_STROKE / k} strokeLinecap="round" strokeLinejoin="round"
        transform={red ? `translate(12 12) scale(${k}) translate(-12 -12)` : undefined}
        dangerouslySetInnerHTML={{ __html: ICONS[n] }}
      />
    </svg>
  );
};

/** Dispatcher: car | car-red | car-fly -> CarArt, none -> nič, inak lucide ikona (IconArt). */
export const Art: React.FC<{ kind?: string; width?: number; style?: React.CSSProperties }> = ({ kind = "car", width = 300, style }) => {
  if (typeof kind !== "string" || kind === "none") return null;
  if (kind === "car" || kind === "car-red" || kind === "car-fly") return <CarArt kind={kind} width={width} style={style} />;
  return <IconArt name={kind} width={width} style={style} />;
};

/* ---------- CaptionPill: 2–3 slová, čierna pilulka ---------- */
const chunk = (words: Word[]) => {
  const out: Word[][] = [];
  let cur: Word[] = [];
  words.forEach((w, i) => {
    cur.push(w);
    const nx = words[i + 1];
    const len = cur.reduce((a, x) => a + x.w.length + 1, 0);
    const brk = /[.,!?:;]$/.test(w.w) || cur.length >= 3 || !nx || nx.b !== w.b || len + (nx ? nx.w.length : 0) > 20;
    if (brk) {
      out.push(cur);
      cur = [];
    }
  });
  return out;
};

export const CaptionPill: React.FC<{ words: Word[]; t: number }> = ({ words, t }) => {
  const cs = React.useMemo(() => chunk(words), [words]);
  const ci = cs.findIndex((c, i) => t >= c[0].s - 0.06 && t < (cs[i + 1] ? Math.min(cs[i + 1][0].s - 0.06, c[c.length - 1].e + 0.5) : c[c.length - 1].e + 0.5));
  if (ci < 0) return null;
  const ch = cs[ci];
  const pop = Math.min(1, (t - ch[0].s + 0.06) / 0.1);
  return (
    <div style={{ position: "absolute", top: CAPTION_Y, left: 0, right: 0, display: "flex", justifyContent: "center", transform: "translateY(-50%)" }}>
      <div
        style={{
          background: "#111113", borderRadius: 14, padding: "14px 28px 16px", fontFamily: SANS, fontWeight: 700, fontSize: 54,
          letterSpacing: -0.5, whiteSpace: "nowrap", boxShadow: "0 8px 0 rgba(0,0,0,0.18), 0 14px 30px rgba(0,0,0,0.25)",
          transform: `scale(${0.95 + 0.05 * pop})`, opacity: 0.4 + 0.6 * pop,
        }}
      >
        {ch.map((w, i) => (
          <span key={i} style={{ color: t >= w.s - 0.03 ? "#FFFFFF" : "#8C8C90", marginRight: i < ch.length - 1 ? 16 : 0 }}>
            {w.w.replace(/^["“]|["”]$/g, "")}
          </span>
        ))}
      </div>
    </div>
  );
};
