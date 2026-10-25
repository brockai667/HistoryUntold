// Scény = rozloženia, ktoré volá story JSON cez "scene": "<Názov>".
// Každá scéna dostane props z JSON (p) a props minulého úderu, ak bol rovnakej scény (prev).
// Čo bolo v minulom údere, ostane stáť; animuje sa len to, čo pribudlo alebo sa zmenilo.
// Text sa nikdy nevyleje: dlhší text zmenší písmo (fit.ts), nezalamuje sa mimo.
import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { CAPTION_Y, CONTENT_TOP, COL_W, COL_X, MONO, SANS, TagT, useEp, useTheme, ACCENT } from "./theme";
import { Art, Counter, Tag, fmt, useEnter, usePop, useRoll } from "./Paper";
import { AnchorSlider, BeforeAfter, EmptySlot, LogoOutro, ProductCard, ThumbGrid, priceAnchor } from "./Blocks";
import { Crowd } from "./Crowd";
import { fitInter, fitMono, monoEm, wrapLines } from "./fit";

type P = { p: any; prev?: any };
const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);
const str = (v: unknown) => (v == null ? "" : String(v));

const Area: React.FC<{ children: React.ReactNode; justify?: React.CSSProperties["justifyContent"] }> = ({ children, justify = "center" }) => (
  <div
    style={{
      position: "absolute", top: CONTENT_TOP, left: COL_X, width: COL_W, height: CAPTION_Y - 120 - CONTENT_TOP,
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: justify,
    }}
  >
    {children}
  </div>
);

const JobTag: React.FC<{ tag: TagT; fresh: boolean }> = ({ tag, fresh }) => {
  const pop = usePop(2, fresh);
  return (
    <div style={{ ...pop, marginBottom: 34 }}>
      <Tag tag={typeof tag === "string" ? { text: tag, tone: "dark" } : tag} size={26} maxWidth={COL_W} />
    </div>
  );
};

/* Hero: veľký objekt + červený štítok. props: art, tag, title, sub */
const Hero: React.FC<P> = ({ p, prev }) => {
  const pal = useTheme();
  const car = useEnter(0, !prev || prev.art !== p.art, 50, 16);
  const tag = usePop(10, !same(prev?.tag, p.tag));
  const txt = useEnter(14, !prev || prev.title !== p.title, 24);
  const titleS = fitInter(str(p.title), COL_W, 84, 40, 900, -3 / 84);
  const subS = fitMono(str(p.sub), COL_W, 46, 14, 4 / 46, 0.1); // druhá polovica háku: veľká a červená (test bez zvuku)
  return (
    <Area>
      <div style={{ position: "relative", width: COL_W, display: "flex", flexDirection: "column", alignItems: "center" }}>
        {p.tag && (
          <div style={{ ...tag, alignSelf: "flex-start", marginBottom: 30, marginLeft: 20 }}>
            <Tag tag={p.tag} size={34} maxWidth={COL_W - 20} />
          </div>
        )}
        <div style={car}>
          <Art kind={p.art ?? "car-fly"} width={720} draw={!prev || prev.art !== p.art ? 2 : undefined} idle={0} />
        </div>
        {p.title && (
          <div style={{ ...txt, marginTop: 90, textAlign: "center" }}>
            <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: titleS, letterSpacing: titleS * (-3 / 84), color: pal.ink, lineHeight: 1, whiteSpace: "nowrap" }}>{p.title}</div>
            {p.sub && (
              <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: subS, letterSpacing: subS * (4 / 46), color: ACCENT.red, marginTop: 20, whiteSpace: "nowrap" }}>{p.sub}</div>
            )}
          </div>
        )}
      </div>
    </Area>
  );
};

/* PriceList: karty pribúdajú zhora nadol, prázdne sloty čakajú. props: cards[], slots, point: [a, b]
   point = gulička skočí z ceny karty a na cenu karty b (a „=“, keď sú ceny rovnaké): divák vidí, čo s čím porovnať. */
const PriceList: React.FC<P> = ({ p, prev }) => {
  const cards = p.cards ?? [];
  const slots = Math.max(p.slots ?? 3, cards.length);
  const pt = Array.isArray(p.point) && p.point.length === 2 && cards[p.point[0]] && cards[p.point[1]] ? p.point : null;
  const ptFresh = !same(prev?.point, p.point);
  const f = useCurrentFrame();
  // karty mimo porovnania stmavnú, keď sa gulička objaví: divák vie, ktoré dve ceny má porovnať
  const dim = pt ? (ptFresh ? interpolate(f, [BALL.appear - 2, BALL.appear + 6], [1, 0.3], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0.3) : 1;
  return (
    <Area justify="flex-start">
      {pt && <PointBall cards={cards} a={pt[0]} b={pt[1]} fresh={ptFresh} />}
      <div style={{ display: "flex", flexDirection: "column", gap: 28, marginTop: 10 }}>
        {Array.from({ length: slots }).map((_, i) =>
          cards[i] ? (
            <div key={i} style={{ opacity: pt && !pt.includes(i) ? dim : 1 }}>
              <ProductCard card={cards[i]} prev={prev?.cards?.[i]} fresh={!prev?.cards?.[i] || prev.cards[i].title !== cards[i].title} delay={2} idle={i} />
            </div>
          ) : (
            <EmptySlot key={i} />
          ),
        )}
      </div>
    </Area>
  );
};

// gulička: objaví sa pri cene karty a, oblúkom vpravo preskočí na cenu karty b, za sebou nechá bodkovanú stopu
export const BALL = { appear: 10, start: 22, land: 40 }; // snímky úderu (rovnaké v sfx.py)
const ROW = 250 + 28; // výška karty + medzera v cenníku
const PointBall: React.FC<{ cards: any[]; a: number; b: number; fresh: boolean }> = ({ cards, a, b, fresh }) => {
  const pal = useTheme();
  const f0 = useCurrentFrame();
  const f = fresh ? f0 : 1000;
  const A0 = priceAnchor(cards[a]), B0 = priceAnchor(cards[b]);
  if (!A0 || !B0) return null;
  const R = 32;
  const A = { x: A0.x + 30 + R, y: 10 + a * ROW + A0.y }, B = { x: B0.x + 30 + R, y: 10 + b * ROW + B0.y };
  const C = { x: Math.min(Math.max(A.x, B.x) + 230, COL_W - 20), y: (A.y + B.y) / 2 };
  const at = (t: number) => ({
    x: (1 - t) ** 2 * A.x + 2 * t * (1 - t) * C.x + t * t * B.x,
    y: (1 - t) ** 2 * A.y + 2 * t * (1 - t) * C.y + t * t * B.y,
  });
  const t = Easing.inOut(Easing.cubic)(interpolate(f, [BALL.start, BALL.land], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  const pos = at(t);
  const born = interpolate(f, [BALL.appear, BALL.appear + 5, BALL.appear + 9], [0, 1.18, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const g = f - BALL.land; // dopad: sploštenie a odskok
  const squash = g >= 0 && g < 8 ? 1 + 0.28 * Math.sin((Math.PI * g) / 8) * (1 - g / 8) : 1;
  const bob = g >= 8 ? Math.sin((g - 8) / 9) * 4 : 0;
  const equal = str(cards[a].price) === str(cards[b].price);
  const mid = at(0.5);
  const badge = interpolate(f, [BALL.land + 2, BALL.land + 7, BALL.land + 11], [0, 1.2, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const line = pal.name === "blueprint" ? pal.cardLine : pal.ink;
  const trail = Array.from({ length: 11 }, (_, i) => (i + 1) / 12).filter((u) => u <= t);
  return (
    <div style={{ position: "absolute", left: 0, top: 0, width: COL_W, height: "100%", pointerEvents: "none", zIndex: 5 }}>
      {trail.map((u, i) => {
        const q = at(u);
        return <div key={i} style={{ position: "absolute", left: q.x - 8, top: q.y - 8, width: 16, height: 16, borderRadius: "50%", background: line, opacity: 0.6 }} />;
      })}
      {badge > 0 && (
        <div
          style={{
            position: "absolute", left: Math.min(mid.x + 30, COL_W - 110), top: mid.y - 62, width: 124, height: 124, borderRadius: "50%",
            background: equal ? ACCENT.yellow : ACCENT.red, border: "4px solid #151517",
            display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${badge})`,
            fontFamily: SANS, fontWeight: 900, fontSize: 92, lineHeight: 1, color: "#151517", boxShadow: "0 6px 0 rgba(0,0,0,0.2)",
          }}
        >
          {equal ? "=" : "≠"}
        </div>
      )}
      <div
        style={{
          position: "absolute", left: pos.x - R, top: pos.y - R + bob, width: 2 * R, height: 2 * R, borderRadius: "50%",
          background: `radial-gradient(circle at 35% 30%, #FFF7C9 0 18%, ${ACCENT.yellow} 45%, #E0B21C 100%)`,
          border: "4px solid #151517", boxSizing: "border-box",
          transform: `scale(${born * squash}, ${born / squash})`, boxShadow: "0 6px 0 rgba(0,0,0,0.18)",
        }}
      />
    </div>
  );
};

/* Views: JOB štítok + počítadlo + mriežka miniatúr. props: job, label, value, from, prefix, suffix, grid, thumbLabel, art */
const Views: React.FC<P> = ({ p, prev }) => {
  const pal = useTheme();
  const fresh = !prev;
  const box = useEnter(4, fresh);
  // písmo počítadla sa určí z koncovej hodnoty (je najširšia), aby sa pri počítaní nič nehýbalo ani nepretieklo
  const label = str(p.label ?? "VIEWS");
  const labelS = fitMono(label, 300, 26, 16, 6 / 26);
  const labelW = monoEm(label, 6 / 26) * labelS;
  const big = Math.max(Math.abs(Number(p.value) || 0), Math.abs(Number(p.from) || 0));
  const finalText = `${str(p.prefix)}${fmt(big)}${str(p.suffix)}`;
  const counterS = fitInter(finalText, COL_W - 6 - 68 - labelW - 28, 92, 36, 900, -3 / 92, true);
  return (
    <Area justify="flex-start">
      {p.job && <JobTag tag={p.job} fresh={!same(prev?.job, p.job)} />}
      <div
        style={{
          ...box, width: COL_W, height: 150, borderRadius: 20, border: `3px solid ${pal.cardLine}`, background: pal.card, boxShadow: pal.cardShadow,
          display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 34px", boxSizing: "border-box", marginBottom: 30,
        }}
      >
        <span style={{ fontFamily: MONO, fontSize: labelS, letterSpacing: labelS * (6 / 26), color: pal.muted, fontWeight: 700, whiteSpace: "nowrap" }}>{label}</span>
        <Counter
          from={p.from ?? 0} to={p.value} prefix={p.prefix} suffix={p.suffix} fresh={!prev || prev.value !== p.value}
          style={{ fontFamily: SANS, fontWeight: 900, fontSize: counterS, letterSpacing: counterS * (-3 / 92), color: pal.name === "blueprint" ? ACCENT.gold : pal.ink, whiteSpace: "nowrap" }}
        />
      </div>
      {(p.grid ?? 8) > 0 && <ThumbGrid n={p.grid ?? 8} label={p.thumbLabel} art={p.art} fresh={fresh} />}
    </Area>
  );
};

/* Anchor: posuvník kotvy. props: job, price, at, split, art, anchor:{label, art} */
const Anchor: React.FC<P> = ({ p, prev }) => {
  const anchorIn = useEnter(0, !prev?.anchor, -60, 18);
  return (
    <Area justify="flex-start">
      {p.job && <JobTag tag={p.job} fresh={!same(prev?.job, p.job)} />}
      <div style={{ position: "relative", width: COL_W, height: 300 }}>
        {p.anchor && (
          <div style={{ ...anchorIn, position: "absolute", right: 0, top: 10, display: "flex", flexDirection: "column", alignItems: "flex-end" }}>
            <Tag tag={p.anchor.label ? { text: p.anchor.label, tone: "blue" } : "THE ANCHOR"} size={22} maxWidth={COL_W} />
            <div style={{ marginTop: 10, marginRight: 10 }}>
              <Art kind={p.anchor.art ?? "car-fly"} width={280} idle={1} />
            </div>
          </div>
        )}
      </div>
      <AnchorSlider at={p.at ?? 0.6} split={p.split ?? 0.45} fromSplit={prev?.split} price={p.price} art={p.art} left={p.left} right={p.right} delay={p.anchor && !prev?.anchor ? 16 : 6} />
    </Area>
  );
};

/* Compare: BEFORE | AFTER. props: before[], after[] (null = prázdny slot), labels */
const Compare: React.FC<P> = ({ p, prev }) => (
  <Area>
    <BeforeAfter before={p.before ?? []} after={p.after ?? []} prev={prev} labels={p.labels} />
  </Area>
);

/* Statement: krátka veta / zoznam štítkov. props: kicker, text, tags[]
   Bez vety sa hlavnou stane nadpisová línia (kicker): číslo na začiatku veľké a napočíta sa, zvyšok veľkým písmom. */
const Statement: React.FC<P> = ({ p, prev }) => {
  const pal = useTheme();
  const kFresh = !prev || prev.kicker !== p.kicker;
  const bigKick = !p.text && !!p.kicker;
  // veľké číslo naskočí až po prepnutí farieb z blueprintu (Episode prepína paletu v 0,15 s úderu), inak by bliklo zlaté
  const k = useEnter(bigKick ? 5 : 0, kFresh, 20);
  const t = useEnter(bigKick ? 9 : 4, !prev || prev.text !== p.text);
  const km = bigKick ? str(p.kicker).match(/^(\d[\d,.]*%?)\s+(.*)$/) : null;
  const num = useRoll(km?.[1], 5, kFresh, 18);
  const text = bigKick ? (km ? km[2] : str(p.kicker)) : str(p.text);
  const kickS = fitMono(str(p.kicker), COL_W, 28, 14, 8 / 28);
  // veta sa zalamuje po slovách: najdlhšie slovo sa musí zmestiť do stĺpca a riadkov má byť najviac 4
  let textS = 96;
  for (const w of text.split(/\s+/)) textS = Math.min(textS, fitInter(w, COL_W, 96, 40, 900, -3 / 96));
  while (textS > 56 && wrapLines(text, textS, COL_W, 900, -3 / 96) > 4) textS *= 0.94;
  const numS = km ? fitInter(km[1], COL_W, 300, 120, 900, -3 / 96, true) : 0;
  if (bigKick) {
    return (
      <Area>
        {km && (
          <div style={{ ...k, fontFamily: SANS, fontWeight: 900, fontSize: numS, letterSpacing: numS * (-3 / 96), color: pal.name === "blueprint" ? ACCENT.gold : pal.ink, lineHeight: 0.9, fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" }}>
            {num}
          </div>
        )}
        <div style={{ ...t, fontFamily: SANS, fontWeight: 900, fontSize: textS, letterSpacing: textS * (-3 / 96), color: pal.ink, lineHeight: 1.02, textAlign: "center", textWrap: "balance", maxWidth: COL_W, marginTop: km ? 18 : 0 }}>
          {text}
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 26, marginTop: 50 }}>
          {(p.tags ?? []).map((tag: TagT, i: number) => (
            <StatTag key={i} tag={tag} delay={12 + i * 8} fresh={!prev?.tags?.[i] || !same(prev.tags[i], tag)} />
          ))}
        </div>
      </Area>
    );
  }
  return (
    <Area>
      {p.kicker && (
        <div style={{ ...k, fontFamily: MONO, fontSize: kickS, letterSpacing: kickS * (8 / 28), color: pal.muted, marginBottom: 24, whiteSpace: "nowrap" }}>{p.kicker}</div>
      )}
      {p.text && (
        <div
          style={{
            ...t, fontFamily: SANS, fontWeight: 900, fontSize: textS, letterSpacing: textS * (-3 / 96), color: pal.ink, lineHeight: 1.02, textAlign: "center",
            textWrap: "balance", maxWidth: COL_W,
          }}
        >
          {p.text}
        </div>
      )}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 26, marginTop: p.text ? 50 : 0 }}>
        {(p.tags ?? []).map((tag: TagT, i: number) => (
          <StatTag key={i} tag={tag} delay={6 + i * 8} fresh={!prev?.tags?.[i] || !same(prev.tags[i], tag)} />
        ))}
      </div>
    </Area>
  );
};
const StatTag: React.FC<{ tag: TagT; delay: number; fresh: boolean }> = ({ tag, delay, fresh }) => {
  const e = useEnter(delay, fresh, 24);
  return (
    <div style={e}>
      <Tag tag={typeof tag === "string" ? { text: tag, tone: "dark" } : tag} size={34} maxWidth={COL_W} />
    </div>
  );
};

/* Outro: logo. props: stamp, logo, tagline, cta, art – čo chýba (props {}), vezme sa z episode.json (brand.json cez prep.py) */
const Outro: React.FC<P> = ({ p }) => {
  const ep = useEp();
  return (
    <Area>
      <LogoOutro
        stamp={p.stamp ?? ep?.stamp}
        logo={p.logo ?? ep?.logo ?? ep?.brand ?? ""}
        tagline={p.tagline ?? ep?.tagline ?? ""}
        cta={p.cta ?? ep?.cta ?? "FOLLOW FOR MORE →"}
        art={p.art}
      />
    </Area>
  );
};

export const SCENES: Record<string, React.FC<P>> = { Hero, PriceList, Views, Anchor, Compare, Statement, Outro, Crowd };
