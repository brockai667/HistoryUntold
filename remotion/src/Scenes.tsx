// Scény = rozloženia, ktoré volá story JSON cez "scene": "<Názov>".
// Každá scéna dostane props z JSON (p) a props minulého úderu, ak bol rovnakej scény (prev).
// Čo bolo v minulom údere, ostane stáť; animuje sa len to, čo pribudlo alebo sa zmenilo.
// Text sa nikdy nevyleje: dlhší text zmenší písmo (fit.ts), nezalamuje sa mimo.
import React from "react";
import { CAPTION_Y, CONTENT_TOP, COL_W, COL_X, MONO, SANS, TagT, useEp, useTheme, ACCENT } from "./theme";
import { Art, Counter, Tag, fmt, useEnter, usePop } from "./Paper";
import { AnchorSlider, BeforeAfter, EmptySlot, LogoOutro, ProductCard, ThumbGrid } from "./Blocks";
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
  const subS = fitMono(str(p.sub), COL_W, 26, 14, 6 / 26);
  return (
    <Area>
      <div style={{ position: "relative", width: COL_W, display: "flex", flexDirection: "column", alignItems: "center" }}>
        {p.tag && (
          <div style={{ ...tag, alignSelf: "flex-start", marginBottom: 30, marginLeft: 20 }}>
            <Tag tag={p.tag} size={34} maxWidth={COL_W - 20} />
          </div>
        )}
        <div style={car}>
          <Art kind={p.art ?? "car-fly"} width={720} />
        </div>
        {p.title && (
          <div style={{ ...txt, marginTop: 90, textAlign: "center" }}>
            <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: titleS, letterSpacing: titleS * (-3 / 84), color: pal.ink, lineHeight: 1, whiteSpace: "nowrap" }}>{p.title}</div>
            {p.sub && (
              <div style={{ fontFamily: MONO, fontSize: subS, letterSpacing: subS * (6 / 26), color: pal.muted, marginTop: 16, whiteSpace: "nowrap" }}>{p.sub}</div>
            )}
          </div>
        )}
      </div>
    </Area>
  );
};

/* PriceList: karty pribúdajú zhora nadol, prázdne sloty čakajú. props: cards[], slots */
const PriceList: React.FC<P> = ({ p, prev }) => {
  const cards = p.cards ?? [];
  const slots = Math.max(p.slots ?? 3, cards.length);
  return (
    <Area justify="flex-start">
      <div style={{ display: "flex", flexDirection: "column", gap: 28, marginTop: 10 }}>
        {Array.from({ length: slots }).map((_, i) =>
          cards[i] ? (
            <ProductCard key={i} card={cards[i]} prev={prev?.cards?.[i]} fresh={!prev?.cards?.[i] || prev.cards[i].title !== cards[i].title} delay={2} />
          ) : (
            <EmptySlot key={i} />
          ),
        )}
      </div>
    </Area>
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
              <Art kind={p.anchor.art ?? "car-fly"} width={280} />
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

/* Statement: krátka veta / zoznam štítkov. props: kicker, text, tags[] */
const Statement: React.FC<P> = ({ p, prev }) => {
  const pal = useTheme();
  const k = useEnter(0, !prev || prev.kicker !== p.kicker, 20);
  const t = useEnter(4, !prev || prev.text !== p.text);
  const text = str(p.text);
  const kickS = fitMono(str(p.kicker), COL_W, 28, 14, 8 / 28);
  // veta sa zalamuje po slovách: najdlhšie slovo sa musí zmestiť do stĺpca a riadkov má byť najviac 4
  let textS = 96;
  for (const w of text.split(/\s+/)) textS = Math.min(textS, fitInter(w, COL_W, 96, 40, 900, -3 / 96));
  while (textS > 56 && wrapLines(text, textS, COL_W, 900, -3 / 96) > 4) textS *= 0.94;
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

export const SCENES: Record<string, React.FC<P>> = { Hero, PriceList, Views, Anchor, Compare, Statement, Outro };
