// AU-3 的全站共用物件與 React hook：戰鬥音效排程、循環槽（環境音、燃燒）、環境音導演。
// - `useWorldAmbience(view)`：大世界（由 AU-2 已經掛在 WorldScreen 的 `useWorldSounds` 呼叫，不用改 WorldScreen）；
// - `useBattleAmbience(view)`：戰鬥畫面（優先於大世界；戰鬥結束回到大世界的場景）；
// - `useBurnLoop(view)`：畫面上有人在燃燒時，全場只放一條劈啪循環（音效軌）。
import { useEffect, useRef } from "react";
import type { BattleView, WorldView } from "../api/types";
import { AmbienceDirector, ambienceFor, battlePlace, worldPlace, type AmbienceScene, type Owner } from "./ambience";
import { burnLoopOn } from "./battleSfx";
import { audio } from "./index";
import { LoopDeck } from "./loops";
import { CueScheduler } from "./sfxScheduler";

let deck: LoopDeck | null = null;
let director: AmbienceDirector | null = null;
let scheduler: CueScheduler | null = null;

export function loopDeck(): LoopDeck {
  deck ??= new LoopDeck(audio);
  return deck;
}

export function ambienceDirector(): AmbienceDirector {
  director ??= new AmbienceDirector(audio, loopDeck());
  return director;
}

export function battleScheduler(): CueScheduler {
  scheduler ??= new CueScheduler(audio);
  return scheduler;
}

/** 燃燒循環的槽與音量。 */
export const BURN_SLOT = "status:burn";
export const BURN_GAIN = 0.55;

function useAmbience(owner: Owner, scene: AmbienceScene | null): void {
  const latest = useRef(scene);
  latest.current = scene;
  const key = scene?.key ?? null;
  useEffect(() => {
    ambienceDirector().set(owner, latest.current);
  }, [owner, key]);
  useEffect(() => () => ambienceDirector().set(owner, null), [owner]);
}

export function useWorldAmbience(view: WorldView | null): void {
  useAmbience("world", view === null ? null : ambienceFor(worldPlace(view)));
}

export function useBattleAmbience(view: BattleView | null): void {
  useAmbience("battle", view === null ? null : ambienceFor(battlePlace(view)));
}

export function useBurnLoop(view: BattleView | null): void {
  const on = view !== null && !view.ended && burnLoopOn(view);
  useEffect(() => {
    loopDeck().set(BURN_SLOT, on ? { id: "status_burn", track: "sfx", gain: BURN_GAIN } : null);
  }, [on]);
  useEffect(() => () => loopDeck().set(BURN_SLOT, null), []);
}
