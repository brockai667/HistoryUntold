import React from "react";
import { Composition, staticFile } from "remotion";
import { Avatar } from "./Avatar";
import { Episode } from "./Episode";
import { Ep, FPS, H, W } from "./theme";

// ep = názov dielu (priečinok public/<ep>/). Prázdne = posledný diel z prep.py (public/current.json).
export const RemotionRoot: React.FC = () => (
  <>
  <Composition
    id="Episode"
    component={Episode}
    width={W}
    height={H}
    fps={FPS}
    durationInFrames={60}
    defaultProps={{ ep: "" } as { ep: string; data?: Ep }}
    calculateMetadata={async ({ props }) => {
      let ep = props.ep;
      if (!ep) ep = (await fetch(staticFile("current.json")).then((r) => r.json())).ep;
      const data: Ep = await fetch(staticFile(`${ep}/episode.json`)).then((r) => r.json());
      return { props: { ep, data }, durationInFrames: Math.ceil(data.duration * FPS) };
    }}
  />
  <Composition id="Avatar" component={Avatar} width={1080} height={1080} fps={FPS} durationInFrames={1} />
  </>
);
