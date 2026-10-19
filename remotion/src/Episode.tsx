// Episode: číta public/<ep>/episode.json (cez Root) a skladá údery za sebou.
import React from "react";
import { AbsoluteFill, Audio, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { BLUEPRINT, Ep, EpCtx, PAPER, ThemeCtx } from "./theme";
import { BlueprintSection, CaptionPill, Footer, PaperBackground, ReportHeader } from "./Paper";
import { SCENES } from "./Scenes";

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

  return (
    <EpCtx.Provider value={data}>
    <ThemeCtx.Provider value={pal}>
      <AbsoluteFill>
        <PaperBackground />
        <BlueprintSection amount={bp} />
        <ReportHeader header={data.header || data.brand} caseName={data.case} opacity={headerOpacity} />
        <Footer source={data.source} t={t} duration={data.duration} opacity={headerOpacity} />
        {beats.map((b, i) => {
          const from = Math.round(b.t0 * fps);
          const to = i === beats.length - 1 ? durationInFrames : Math.round(beats[i + 1].t0 * fps);
          const Scene = SCENES[b.scene];
          const prevB = beats[i - 1];
          const prev = prevB && prevB.scene === b.scene ? prevB.props ?? {} : undefined;
          // nová scéna = krátky fade celej scény; rovnaká scéna = plynulé pokračovanie
          return (
            <Sequence key={i} from={from} durationInFrames={Math.max(1, to - from)} layout="none">
              <SceneWrap fade={!prev}>{Scene ? <Scene p={b.props ?? {}} prev={prev} /> : <Missing name={b.scene} />}</SceneWrap>
            </Sequence>
          );
        })}
        <CaptionPill words={data.words} t={t} />
        <Audio src={staticFile(dir + data.voice)} />
        {data.music && <Audio src={staticFile(dir + data.music)} volume={data.music_gain ?? 0.12} />}
      </AbsoluteFill>
    </ThemeCtx.Provider>
    </EpCtx.Provider>
  );
};

const SceneWrap: React.FC<{ fade: boolean; children: React.ReactNode }> = ({ fade, children }) => {
  const f = useCurrentFrame();
  const o = fade ? interpolate(f, [0, 6], [0, 1], { extrapolateRight: "clamp" }) : 1;
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};
