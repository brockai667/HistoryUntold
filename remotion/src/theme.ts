// Decoy Report – farby, fonty, typy. Farby a písmo meň TU, nič iné netreba.
import React from "react";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";

export const W = 1080;
export const H = 1920;
export const FPS = 30;

export const SANS = loadInter("normal", { weights: ["500", "600", "800", "900"], subsets: ["latin"] }).fontFamily;
export const MONO = loadMono("normal", { weights: ["500", "700", "800"], subsets: ["latin"] }).fontFamily;

// Layout: obsah žije v strednom stĺpci, titulky dole.
export const COL_X = 120; // ľavý okraj stĺpca
export const COL_W = W - 2 * COL_X; // šírka stĺpca (840)
export const CONTENT_TOP = 330; // pod hlavičkou
export const CAPTION_Y = 1420; // stred titulkovej pilulky
export const FOOTER_Y = 1556; // horný okraj pätky (progres + zdroj); titulková pilulka končí ~1470

// Spoločné akcenty (rovnaké na papieri aj v blueprinte).
export const ACCENT = {
  red: "#E5383B", // ČERVENÁ = len jedna vec: návnada (NOT FOR SALE, NO PRICE, DECOY, EXTREME)
  green: "#2DBE6C",
  yellow: "#F6D44A",
  blue: "#8CC8F0",
  gold: "#F4C542",
};

export type Palette = {
  name: "paper" | "blueprint";
  bg: string; // pozadie
  grid: string; // čiary mriežky
  vignette: string;
  card: string; // výplň karty
  cardLine: string; // obrys karty
  cardShadow: string;
  ink: string; // hlavný text
  muted: string; // podtitulky, hlavička
  dashed: string; // prázdny slot
  glow: string; // neónový obrys (len blueprint)
  carBody: string;
  carLine: string;
};

export const PAPER: Palette = {
  name: "paper",
  bg: "#EDECE7",
  grid: "rgba(40,40,60,0.045)",
  vignette: "rgba(0,0,0,0.10)",
  card: "#F8F7F3",
  cardLine: "#2A2A2E",
  cardShadow: "0 10px 0 rgba(0,0,0,0.10), 0 18px 40px rgba(0,0,0,0.10)",
  ink: "#17171A",
  muted: "#7C7B78",
  dashed: "rgba(40,40,50,0.28)",
  glow: "transparent",
  carBody: "#FFFFFF",
  carLine: "#2A2A2E",
};

export const BLUEPRINT: Palette = {
  name: "blueprint",
  bg: "#1D2A4C",
  grid: "rgba(140,200,255,0.07)",
  vignette: "rgba(0,0,0,0.35)",
  card: "rgba(70,120,190,0.18)",
  cardLine: "#8FD8FF",
  cardShadow: "0 0 18px rgba(120,210,255,0.55), inset 0 0 14px rgba(120,210,255,0.25)",
  ink: "#FFFFFF",
  muted: "rgba(170,200,240,0.65)",
  dashed: "rgba(140,210,255,0.35)",
  glow: "#8FD8FF",
  carBody: "rgba(120,190,255,0.10)",
  carLine: "#BFE8FF",
};

export const ThemeCtx = React.createContext<Palette>(PAPER);
export const useTheme = () => React.useContext(ThemeCtx);

// Farby štítkov (Tag tone).
export const TAG_TONES: Record<string, { bg: string; fg: string; line: string }> = {
  plain: { bg: "transparent", fg: "currentColor", line: "currentColor" },
  dark: { bg: "#1B1B1F", fg: "#FFFFFF", line: "#1B1B1F" },
  blue: { bg: "#D4ECFA", fg: "#1B1B1F", line: "#1B1B1F" },
  yellow: { bg: ACCENT.yellow, fg: "#1B1B1F", line: "#1B1B1F" },
  red: { bg: ACCENT.red, fg: "#FFFFFF", line: ACCENT.red },
  green: { bg: ACCENT.green, fg: "#FFFFFF", line: ACCENT.green },
};

/* ---------- typy dát z episode.json ---------- */
export type TagT = { text: string; tone?: keyof typeof TAG_TONES } | string;
export type CardT = {
  title: string;
  sub?: string;
  price?: string;
  priceRed?: boolean; // napr. NO PRICE
  tags?: TagT[];
  art?: string; // meno ikony z icons.json | car | car-red | car-fly | none (prípona -red = červený nádych)
  stamp?: string; // malá červená pečiatka v rohu karty (napr. DECOY)
  badge?: TagT; // pilulka pri cene (SMART CHOICE, PRICEY?)
  top?: TagT; // štítok na hornej hrane karty (EXTREME)
};
export type Beat = {
  say: string;
  scene: string;
  props?: Record<string, any>;
  mode?: "paper" | "blueprint";
  hold?: number;
  t0: number;
  t1: number;
};
export type Word = { w: string; s: number; e: number; b: number };
export type Ep = {
  case: string;
  brand: string;
  header?: string; // text hlavičky (fallback brand)
  source?: string; // zdroj v päte
  logo?: string; // outro (dopĺňa prep.py z brand.json)
  tagline?: string;
  stamp?: string;
  cta?: string;
  bait_stamp?: string;
  beats: Beat[];
  words: Word[];
  duration: number;
  voice: string;
  music?: string;
  music_gain?: number;
};

// Epizóda (episode.json) pre scény, ktoré berú značku z kódu (Outro s props {}).
export const EpCtx = React.createContext<Ep | null>(null);
export const useEp = () => React.useContext(EpCtx);
