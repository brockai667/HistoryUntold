// Väčšie stavebné bloky: ProductCard, AnchorSlider, BeforeAfter, ThumbGrid, LogoOutro.
// Pravidlo: text sa nikdy nevyleje z karty ani nezalomí mimo – dlhší text zmenší písmo (fit.ts), štítky sa pri
// nutnosti zalomia do ďalšieho riadka, riadky v Compare narastú.
import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { ACCENT, CardT, COL_W, MONO, SANS, TagT, useTheme } from "./theme";
import { Art, Stamp, Tag, tagOf, useEnter, usePop } from "./Paper";
import { fitInter, fitMono, interEm, layoutTags, tagH, tagW } from "./fit";

const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);
const str = (v: unknown) => (v == null ? "" : String(v));
const tagTexts = (tags?: TagT[]) => (tags ?? []).map((t) => str(tagOf(t).text));

/* ---------- ProductCard (veľká karta v cenníku) ---------- */
const ART_COL = 360; // ľavý stĺpec karty (ikona / auto)
const TXT_W = COL_W - 6 - ART_COL - 30; // 444: šírka textového stĺpca (rámik 2 × 3, odsadenie vpravo 30)

export const ProductCard: React.FC<{ card: CardT; prev?: CardT; fresh: boolean; delay?: number; height?: number }> = ({
  card, prev, fresh, delay = 0, height = 250,
}) => {
  const pal = useTheme();
  const enter = useEnter(delay, fresh);
  const priceIn = useEnter(delay + 6, fresh || prev?.price !== card.price, 16);
  // každý text sa zmestí do stĺpca zmenšením písma (žiadne ellipsis, žiadne zalomenie)
  const titleS = fitInter(str(card.title), TXT_W, 50, 24, 900, -0.03);
  const subS = fitMono(str(card.sub), TXT_W, 20, 12, 0.2);
  const priceS = fitInter(str(card.price), TXT_W, 62, 26, 900, -2 / 62);
  const tl = layoutTags(tagTexts(card.tags), TXT_W, 18, 15, 10);
  return (
    <div
      style={{
        ...enter, position: "relative", width: COL_W, height, borderRadius: 22, background: pal.card,
        border: `3px solid ${pal.cardLine}`, boxShadow: pal.cardShadow, display: "flex", alignItems: "center", boxSizing: "border-box",
      }}
    >
      <div style={{ width: ART_COL, display: "flex", justifyContent: "center", alignItems: "center", paddingTop: card.badge ? 0 : 20, paddingBottom: card.badge ? 28 : 0 }}>
        <Art kind={card.art ?? "car"} width={300} />
      </div>
      <div style={{ flex: 1, paddingRight: 30, minWidth: 0 }}>
        <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: titleS, color: pal.ink, letterSpacing: titleS * -0.03, lineHeight: 1, whiteSpace: "nowrap" }}>
          {card.title}
        </div>
        {card.sub && (
          <div style={{ fontFamily: MONO, fontSize: subS, letterSpacing: subS * 0.2, color: pal.muted, marginTop: 8, fontWeight: 500, whiteSpace: "nowrap" }}>
            {card.sub}
          </div>
        )}
        {card.price && (
          <div
            style={{
              ...priceIn, fontFamily: SANS, fontWeight: 900, fontSize: priceS, letterSpacing: priceS * (-2 / 62), lineHeight: 1.05, marginTop: 6,
              color: card.priceRed ? ACCENT.red : pal.ink, whiteSpace: "nowrap",
            }}
          >
            {card.price}
          </div>
        )}
        {card.tags && card.tags.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px 10px", marginTop: 12 }}>
            {card.tags.map((t, i) => (
              <PopTag key={i} tag={t} size={tl.size} delay={delay + 10 + i * 4} fresh={fresh || !prev?.tags?.[i] || !same(prev.tags[i], t)} />
            ))}
          </div>
        )}
      </div>
      {card.stamp && (
        <div style={{ position: "absolute", left: 26, top: 22 }}>
          <Stamp text={card.stamp} size={34} maxWidth={ART_COL - 26 - 24} rotate={-10} delay={delay + 4} fresh={fresh || prev?.stamp !== card.stamp} />
        </div>
      )}
      {card.badge && (
        // pod ikonou v ľavom stĺpci: tam nikdy nekoliduje s názvom ani cenou (aj pri najdlhších textoch)
        <div style={{ position: "absolute", left: 0, bottom: 16, width: ART_COL, display: "flex", justifyContent: "center" }}>
          <PopTag tag={card.badge} size={18} maxWidth={ART_COL - 40} delay={delay + 8} fresh={fresh || !same(prev?.badge, card.badge)} />
        </div>
      )}
    </div>
  );
};

const PopTag: React.FC<{ tag: TagT; delay: number; fresh: boolean; size?: number; maxWidth?: number }> = ({ tag, delay, fresh, size = 18, maxWidth }) => {
  const pop = usePop(delay, fresh);
  return (
    <span style={{ display: "inline-block", ...pop }}>
      <Tag tag={tag} size={size} maxWidth={maxWidth} />
    </span>
  );
};

/** Prázdny slot (čiarkovaný rámik), kým karta nepríde. */
export const EmptySlot: React.FC<{ height?: number; width?: number | string }> = ({ height = 250, width = COL_W }) => {
  const pal = useTheme();
  return <div style={{ width, height, borderRadius: 22, border: `3px dashed ${pal.dashed}`, boxSizing: "border-box" }} />;
};

/* ---------- AnchorSlider: REASONABLE <-> EXPENSIVE ---------- */
export const AnchorSlider: React.FC<{
  at: number; // poloha objektu 0..1
  split: number; // kde končí zelená
  fromSplit?: number; // odkiaľ sa hranica posúva (z minulého úderu)
  price?: string;
  art?: string;
  left?: string;
  right?: string;
  delay?: number;
}> = ({ at, split, fromSplit, price, art = "car-red", left = "REASONABLE", right = "EXPENSIVE", delay = 8 }) => {
  const f = useCurrentFrame();
  const pal = useTheme();
  const s0 = fromSplit ?? split;
  const p = interpolate(f - delay, [0, 36], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  const sp = s0 + (split - s0) * p;
  const barW = COL_W;
  // cenovka sa zmenší podľa dĺžky a objekt (cenovka + ikona) sa nikdy nevysunie za okraj stĺpca
  const priceS = fitInter(str(price), 440, 50, 26, 900, -0.03);
  const priceBoxW = price ? interEm(str(price), 900, -0.03) * priceS + 38 : 0;
  const isCar = /^car(-red|-fly)?$/.test(art);
  const half = Math.max(priceBoxW / 2, isCar ? 130 : 72);
  const objX = Math.min(Math.max(at * barW, half), barW - half);
  const lblS = Math.min(fitMono(left, barW / 2 - 20, 24, 14, 4 / 24), fitMono(right, barW / 2 - 20, 24, 14, 4 / 24));
  return (
    <div style={{ position: "relative", width: barW, height: 420 }}>
      <div style={{ position: "absolute", left: objX, bottom: 120, transform: "translateX(-50%)", display: "flex", flexDirection: "column", alignItems: "center" }}>
        {price && (
          <div
            style={{
              fontFamily: SANS, fontWeight: 900, fontSize: priceS, letterSpacing: priceS * -0.03, color: pal.ink, background: pal.card,
              border: `3px solid ${pal.cardLine}`, borderRadius: 12, padding: "2px 16px", marginBottom: 6, whiteSpace: "nowrap",
            }}
          >
            {price}
          </div>
        )}
        <div style={{ width: 3, height: 24, background: pal.cardLine, marginBottom: -6 }} />
        <Art kind={art} width={260} />
      </div>
      <div
        style={{
          position: "absolute", left: 0, right: 0, bottom: 64, height: 34, borderRadius: 17, overflow: "hidden",
          border: `3px solid ${pal.cardLine}`, display: "flex",
        }}
      >
        <div style={{ width: `${sp * 100}%`, background: ACCENT.green }} />
        <div style={{ flex: 1, background: ACCENT.red }} />
        <div
          style={{
            position: "absolute", left: 12, right: 12, top: "50%", height: 0, borderTop: "3px dashed rgba(255,255,255,0.85)",
          }}
        />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 14, display: "flex", justifyContent: "space-between", fontFamily: MONO, fontWeight: 700, fontSize: lblS, letterSpacing: lblS * (4 / 24), whiteSpace: "nowrap" }}>
        <span style={{ color: ACCENT.green }}>{left}</span>
        <span style={{ color: ACCENT.red }}>{right}</span>
      </div>
    </div>
  );
};

/* ---------- BeforeAfter: dva stĺpce mini kariet ---------- */
const COL_GAP = 28;
const COL_IN = (COL_W - COL_GAP) / 2 - 6; // 400: vnútro stĺpca (rámik 2 × 3)
const CARD_W = COL_IN - 32; // 368: mini karta (odsadenie stĺpca 16 + 16)
const MINI_TXT = CARD_W - 6 - 36; // 326: šírka textu v mini karte (rámik 2 × 3, padding 2 × 18)
const MINI_MIN_H = 170;

type MiniLayout = { titleS: number; subS: number; priceS: number; tagS: number; badgeS: number; h: number };

/** Veľkosti písma a potrebná výška mini karty. Odznak (badge) sedí vpravo dole, preto sa spodný riadok o jeho šírku skráti. */
const miniLayout = (c: CardT): MiniLayout => {
  const tags = tagTexts(c.tags);
  const bottom = c.price ? "price" : tags.length ? "tags" : c.sub ? "sub" : "title";
  // spodný riadok (cena / štítky / podtitul / názov) sa zmestí vedľa odznaku v základnej veľkosti?
  const fits = (room: number) => {
    if (bottom === "price") return fitInter(str(c.price), room, 46, 24, 900, -1.5 / 46) >= 46;
    if (bottom === "tags") {
      const l = layoutTags(tags, room, 15, 13, 8);
      return l.rows === 1 && l.size >= 15;
    }
    if (bottom === "sub") return fitMono(str(c.sub), room, 17, 11, 3 / 17) >= 17;
    return fitInter(str(c.title), room, 30, 18, 800, -0.017) >= 30;
  };
  // odznak sa zmenšuje (16 -> 12 px) len keď by inak musel schudnúť spodný riadok; až potom sa zmenšuje ten
  const badgeText = c.badge ? str(tagOf(c.badge).text) : "";
  let badgeS = 16;
  if (c.badge) while (badgeS > 12 && !fits(MINI_TXT - (tagW(badgeText, badgeS) + 8))) badgeS -= 1;
  const reserve = c.badge ? tagW(badgeText, badgeS) + 8 : 0;
  const avail = (el: string) => MINI_TXT - (bottom === el ? reserve : 0);
  const titleS = fitInter(str(c.title), avail("title"), 30, 18, 800, -0.017);
  const subS = fitMono(str(c.sub), avail("sub"), 17, 11, 3 / 17);
  const priceS = fitInter(str(c.price), avail("price"), 46, 24, 900, -1.5 / 46);
  const tl = layoutTags(tags, avail("tags"), 15, 13, 8);
  const content =
    titleS * 1.05 +
    (c.sub ? 4 + subS * 1.32 : 0) +
    (tags.length ? 8 + tl.rows * tagH(tl.size) + (tl.rows - 1) * 8 : 0) +
    (c.price ? 4 + priceS * 1.05 : 0);
  return { titleS, subS, priceS, tagS: tl.size, badgeS, h: Math.ceil(content + 2 * 16 + 6) };
};

const MiniCard: React.FC<{ card: CardT | null; prev?: CardT | null; delay: number; height: number }> = ({ card, prev, delay, height }) => {
  const pal = useTheme();
  const strip = (c?: CardT | null) => (c ? { ...c, badge: undefined } : c);
  const fresh = !same(strip(card), strip(prev));
  const enter = useEnter(delay, fresh, 24);
  const badgePop = usePop(delay + 8, fresh || !same(card?.badge, prev?.badge));
  if (!card) return <EmptySlot height={height} width="100%" />;
  const L = miniLayout(card);
  const green = card.badge && tagOf(card.badge).tone === "green";
  return (
    <div
      style={{
        ...enter, position: "relative", height, borderRadius: 16, background: pal.card, boxSizing: "border-box",
        border: `3px solid ${green ? ACCENT.green : pal.cardLine}`, padding: "16px 18px", display: "flex", flexDirection: "column", justifyContent: "flex-end",
        boxShadow: green ? `0 0 0 4px rgba(45,190,108,0.25)` : "none",
      }}
    >
      {card.top && (
        <div style={{ position: "absolute", left: 14, top: -16 }}>
          <Tag tag={card.top} size={16} maxWidth={CARD_W - 28} />
        </div>
      )}
      <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: L.titleS, color: pal.ink, letterSpacing: L.titleS * -0.017, lineHeight: 1.05, whiteSpace: "nowrap" }}>{card.title}</div>
      {card.sub && (
        <div style={{ fontFamily: MONO, fontSize: L.subS, letterSpacing: L.subS * (3 / 17), color: pal.muted, marginTop: 4, lineHeight: 1.32, whiteSpace: "nowrap" }}>{card.sub}</div>
      )}
      {card.tags && card.tags.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
          {card.tags.map((t, i) => (
            <Tag key={i} tag={t} size={L.tagS} />
          ))}
        </div>
      )}
      {card.price && (
        <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: L.priceS, color: pal.ink, letterSpacing: L.priceS * (-1.5 / 46), lineHeight: 1.05, marginTop: 4, whiteSpace: "nowrap" }}>{card.price}</div>
      )}
      {card.badge && (
        <div style={{ position: "absolute", right: 14, bottom: 22, ...badgePop }}>
          <Tag tag={card.badge} size={L.badgeS} maxWidth={CARD_W - 40} />
        </div>
      )}
    </div>
  );
};

export const BeforeAfter: React.FC<{
  before: (CardT | null)[];
  after: (CardT | null)[];
  prev?: { before?: (CardT | null)[]; after?: (CardT | null)[] };
  labels?: [string, string];
}> = ({ before, after, prev, labels = ["BEFORE", "AFTER"] }) => {
  const pal = useTheme();
  const colW = (COL_W - COL_GAP) / 2;
  // obe karty v jednom riadku majú rovnakú výšku; riadok narastie, len keď to obsah (štítky, cena, odznak) naozaj vyžaduje
  const rows = Math.max(before.length, after.length);
  const rowH = Array.from({ length: rows }, (_, i) =>
    Math.max(MINI_MIN_H, before[i] ? miniLayout(before[i] as CardT).h : 0, after[i] ? miniLayout(after[i] as CardT).h : 0),
  );
  const col = (cards: (CardT | null)[], prevCards: (CardT | null)[] | undefined, label: string, dark: boolean, d0: number) => {
    const lblS = fitMono(str(label), COL_IN - 24, 26, 14, 8 / 26);
    return (
      <div
        style={{
          width: colW, boxSizing: "border-box", borderRadius: 20, border: `3px solid ${pal.cardLine}`, background: pal.name === "paper" ? "#F2F1EC" : "rgba(70,120,190,0.12)",
          overflow: "visible", boxShadow: pal.cardShadow,
        }}
      >
        <div
          style={{
            height: 64, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: MONO, fontWeight: 800, fontSize: lblS, letterSpacing: lblS * (8 / 26),
            background: dark ? "#1B1B1F" : "#E2E1DB", color: dark ? "#FFFFFF" : pal.ink, borderRadius: "17px 17px 0 0", whiteSpace: "nowrap",
          }}
        >
          {label}
        </div>
        <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 22, paddingTop: 26 }}>
          {cards.map((c, i) => (
            <MiniCard key={i} card={c} prev={prevCards ? prevCards[i] : undefined} delay={d0 + i * 5} height={rowH[i] ?? MINI_MIN_H} />
          ))}
        </div>
      </div>
    );
  };
  return (
    <div style={{ display: "flex", gap: COL_GAP, width: COL_W }}>
      {col(before, prev?.before, labels[0], false, 2)}
      {col(after, prev?.after, labels[1], true, 8)}
    </div>
  );
};

/* ---------- ThumbGrid: mriežka miniatúr (videá, posty) ---------- */
export const ThumbGrid: React.FC<{ n?: number; label?: string; art?: string; fresh: boolean }> = ({ n = 8, label = "♥ 12K", art = "car-fly", fresh }) => {
  const pal = useTheme();
  const w = (COL_W - 3 * 18) / 4;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 18, width: COL_W }}>
      {Array.from({ length: n }).map((_, i) => (
        <Thumb key={i} w={w} delay={14 + i * 3} fresh={fresh} label={label} art={art} pal={pal} />
      ))}
    </div>
  );
};

const Thumb: React.FC<{ w: number; delay: number; fresh: boolean; label: string; art: string; pal: ReturnType<typeof useTheme> }> = ({ w, delay, fresh, label, art, pal }) => {
  const pop = usePop(delay, fresh);
  return (
    <div
      style={{
        ...pop, width: w, height: w * 0.95, borderRadius: 14, border: `3px solid ${pal.cardLine}`, background: pal.card, boxShadow: pal.cardShadow,
        position: "relative", display: "flex", alignItems: "flex-end", justifyContent: "center", paddingBottom: 14, boxSizing: "border-box",
      }}
    >
      <div style={{ position: "absolute", left: 10, top: 8, fontFamily: MONO, fontSize: 15, fontWeight: 700, color: pal.name === "blueprint" ? ACCENT.gold : pal.muted, whiteSpace: "nowrap" }}>{label}</div>
      <Art kind={art} width={w * 0.78} />
    </div>
  );
};

/* ---------- LogoOutro ---------- */
export const LogoOutro: React.FC<{ stamp?: string; logo: string; tagline: string; cta: string; art?: string }> = ({
  stamp, logo, tagline, cta, art = "car",
}) => {
  const pal = useTheme();
  const a = useEnter(0, true);
  const b = useEnter(16, true, 24);
  const c = usePop(26, true);
  // logo, slogan aj výzva sa zmestia do stĺpca zmenšením písma (napr. "PRICE TRAP" je oveľa širšie než "DECOY")
  const logoS = fitInter(str(logo), COL_W, 230, 60, 900, -10 / 230);
  const tagS = fitMono(str(tagline), COL_W, 28, 14, 9 / 28);
  const ctaS = fitMono(str(cta), COL_W - 68, 32, 16, 5 / 32);
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: "100%" }}>
      <div style={{ ...a, position: "relative", height: 230, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Art kind={art} width={420} />
        {stamp && (
          <div style={{ position: "absolute", left: 0, right: 0, top: 40, display: "flex", justifyContent: "center" }}>
            <Stamp text={stamp} size={96} maxWidth={COL_W - 40} delay={8} />
          </div>
        )}
      </div>
      <div style={{ ...b, fontFamily: SANS, fontWeight: 900, fontSize: logoS, letterSpacing: logoS * (-10 / 230), color: pal.ink, lineHeight: 1, marginTop: 30, whiteSpace: "nowrap" }}>{logo}</div>
      <div style={{ ...b, fontFamily: MONO, fontSize: tagS, letterSpacing: tagS * (9 / 28), color: pal.muted, marginTop: 14, whiteSpace: "nowrap" }}>{tagline}</div>
      <div
        style={{
          ...c, marginTop: 46, background: "#1B1B1F", color: "#FFFFFF", fontFamily: MONO, fontWeight: 800, fontSize: ctaS, letterSpacing: ctaS * (5 / 32),
          padding: "16px 34px", borderRadius: 10, whiteSpace: "nowrap",
        }}
      >
        {cta}
      </div>
    </div>
  );
};
