// 精英單挑插圖（RG-4，A 暮色對峙 320×120）：遇敵卡單挑段標題下面那張圖。資料由 `duelArtPlan.ts` 從 WorldView 算出，
// 畫法在 `render/duelArt.ts`。畫一次就快取（同一組外觀、區域、解析度），之後只貼上。沒有 DOM（測試）時只留同大小的空畫布。
import { useEffect, useRef } from "react";
import { qResolve, qWeaponDef } from "../render/qIcon/weapons";
import { resolveGear } from "../render/gearResolve";
import { BEAST_CLAW } from "../render/qIcon/beastClaw";
import { DUEL_H, DUEL_W, duelCanvas, type DuelSpec, type DuelWeapon } from "../render/duelArt";
import { qUnitOf } from "../render/qSpec";
import { weaponIconDef } from "../render/weaponIcon";
import type { DuelPlan, DuelWeaponPlan } from "./duelArtPlan";

function weaponOf(w: DuelWeaponPlan): DuelWeapon | null {
  if (w.kind === BEAST_CLAW) return { kind: BEAST_CLAW };
  const def = w.kind === "gear" ? qWeaponDef(qResolve(resolveGear(w.look, "main_hand"), w.look.element)) : weaponIconDef(w.item);
  return def === null ? null : { kind: "icon", def };
}

/** 計畫 → 畫法要的輸入（遊戲色 GAME_HOOKS）。 */
export function duelSpecOf(plan: DuelPlan): DuelSpec {
  return {
    hero: { unit: qUnitOf(plan.hero), weapon: weaponOf(plan.heroWeapon) },
    elite: {
      figure: plan.elite.kind === "creature" ? { kind: "creature", creature: plan.elite.creature, k: plan.elite.k } : { kind: "doll", unit: qUnitOf(plan.elite.spec) },
      weapon: weaponOf(plan.eliteWeapon),
    },
    region: plan.region,
  };
}

/** 內部解析度：裝置像素比（1～2；DPR 2 時整張 2 倍）。 */
const resOf = (): number => (typeof window === "undefined" ? 1 : Math.min(2, Math.max(1, window.devicePixelRatio || 1)));

const cache = new Map<string, HTMLCanvasElement | null>();

export function DuelArt({ plan }: { plan: DuelPlan }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const res = resOf();
  useEffect(() => {
    const cv = ref.current;
    if (cv === null) return;
    const key = `${plan.key}|${res}`;
    let art = cache.get(key);
    if (art === undefined) {
      try {
        art = duelCanvas(duelSpecOf(plan), res);
      } catch {
        art = null; // 沒有 2D 畫布的環境
      }
      cache.set(key, art);
    }
    const g = cv.getContext("2d");
    if (art === null || g === null) return;
    g.clearRect(0, 0, cv.width, cv.height);
    g.drawImage(art, 0, 0);
  }, [plan, res]);
  return <canvas ref={ref} className="duel-art" width={Math.round(DUEL_W * res)} height={Math.round(DUEL_H * res)} aria-hidden="true" data-testid="world-duel-art" data-region={plan.region} />;
}
