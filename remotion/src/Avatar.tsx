// Avatar kanála 1080x1080 (TikTok/IG/YT orežú do kruhu -> všetko v strede). npx remotion still Avatar ../output/avatar.png
import React from "react";
import { AbsoluteFill } from "remotion";
import { PaperBackground } from "./Paper";
import { ACCENT, PAPER, SANS } from "./theme";

// oko podľa lucide "eye" (ISC), dúhovka v žltej farbe štítkov
const Eye: React.FC<{ width: number }> = ({ width }) => (
  <svg width={width} height={width * 0.713} viewBox="0.5 3.8 23 16.4" fill="none" stroke={PAPER.ink} strokeWidth={1.7}
    strokeLinecap="round" strokeLinejoin="round">
    <path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0" />
    <circle cx="12" cy="12" r="3.6" fill={ACCENT.yellow} />
    <circle cx="12" cy="12" r="1.5" fill={PAPER.ink} stroke="none" />
    <circle cx="13.1" cy="10.9" r="0.55" fill="#fff" stroke="none" />
  </svg>
);

export const Avatar: React.FC = () => (
  <AbsoluteFill>
    <PaperBackground />
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 34, paddingBottom: 10 }}>
      <Eye width={380} />
      <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: 168, lineHeight: 0.9, letterSpacing: -4,
        color: PAPER.ink, textAlign: "center" }}>
        PLAIN<br />SIGHT
      </div>
    </AbsoluteFill>
  </AbsoluteFill>
);
