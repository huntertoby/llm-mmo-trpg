// 大世界的介面音（AU-2；docs/art/音效與音樂方案.md 2.2）：只看前後兩次伺服器畫面的差，不改任何東西。
// 一次更新只放一聲（優先：升級 → 任務完成 → 任務更新 → 拿到物品 → 金幣）；換角色時不出聲。
// 等待伺服器（說書人／LLM）超過一下子時，每隔一段時間放很輕的墨痕筆刷聲。
import { useEffect, useRef } from "react";
import type { WorldView } from "../api/types";
import { uiSound, type UiSound } from "../audio/uiSounds";
import { gainedItems, levelUp } from "./gainFx";

type QuestLike = { id: string; done: boolean; steps: readonly { done: boolean }[] };

function questProgress(quests: readonly QuestLike[] | undefined): Map<string, { done: boolean; steps: number }> {
  const m = new Map<string, { done: boolean; steps: number }>();
  for (const q of quests ?? []) m.set(q.id, { done: q.done, steps: q.steps.filter((s) => s.done).length });
  return m;
}

/** 前後兩次畫面 → 這次要放的介面音（沒有就 null）。純函式。 */
export function worldSoundFor(prev: WorldView | null, next: WorldView): UiSound | null {
  if (prev === null || prev.character.character_id !== next.character.character_id) return null;
  if (levelUp(prev, next) !== null) return "ui_levelup";
  const a = questProgress(prev.quests);
  const b = questProgress(next.quests);
  let updated = false;
  for (const [id, q] of b) {
    const old = a.get(id);
    if (q.done && old?.done !== true) return "ui_quest_done";
    if (old === undefined || q.steps > old.steps) updated = true;
  }
  if (updated) return "ui_quest_update";
  if (gainedItems(prev.inventory ?? null, next.inventory ?? null).length > 0) return "ui_item";
  if ((next.wallet?.gold ?? 0) > (prev.wallet?.gold ?? 0)) return "ui_coin";
  return null;
}

export function useWorldSounds(view: WorldView | null): void {
  const prev = useRef<WorldView | null>(null);
  useEffect(() => {
    if (view === null) return;
    const id = worldSoundFor(prev.current, view);
    prev.current = view;
    if (id !== null) uiSound(id);
  }, [view]);
}

/** 等待超過這麼久才開始放墨痕聲（毫秒；一般動作很快就回來，不出聲）。 */
export const INK_WAIT_DELAY_MS = 700;
export const INK_WAIT_EVERY_MS = 1600;

export function useInkWaitSound(busy: boolean): void {
  useEffect(() => {
    if (!busy) return undefined;
    let every: number | undefined;
    const first = window.setTimeout(() => {
      uiSound("ui_ink_wait");
      every = window.setInterval(() => uiSound("ui_ink_wait"), INK_WAIT_EVERY_MS);
    }, INK_WAIT_DELAY_MS);
    return () => {
      window.clearTimeout(first);
      if (every !== undefined) window.clearInterval(every);
    };
  }, [busy]);
}
