// 持續區域（Phase 3D-5）：整塊區域的繪圖資料（3-36b）、HUD 清單、滑過格子的說明（純函式）。
import type { BattleView, Pos, ZoneView } from "../api/types";
import type { FxSkills } from "./fxSkills";
import type { UnitNames } from "./units";

export type ZoneSide = "n" | "s" | "w" | "e";

/** 區域對某陣營的影響（3-37b 起分三種樣式）。 */
export type ZoneEffect = "harm" | "help" | "none";

/** 一整塊區域（同一個區域編號的格子一組）。 */
export interface ZoneDraw {
  id: number;
  /** 依 `(y, x)` 排序。 */
  cells: Pos[];
  /** 對「目前玩家陣營」有害（會打到我方）：實線＋斜紋。 */
  harmful: boolean;
  /** 對目前玩家陣營的影響：有害（實線＋斜紋）、有益（虛線＋光點）、不影響（虛線＋淡底色，不畫紋理）。 */
  effect: ZoneEffect;
  /** 區域效果的元素；查不到為 `null`（顏色退回表面色、再退回灰色）。 */
  element: string | null;
  /** 區域產生的表面（元素色的備案）；沒有為 `null`。 */
  surface: string | null;
  anchor: ZoneView["anchor"];
  /** 移動型的前進方向；其他為 `null`。 */
  side: ZoneSide | null;
  /** 跟隨型：施放者目前所在的格子；其他或不在場為 `null`。 */
  caster: Pos | null;
  /** 剩餘輪數（含本輪）。 */
  turns: number;
}

/** 區域單格的繪圖規格：要描外框的邊、移動型的箭頭側、斜紋相位。 */
export interface ZoneCellSpec {
  x: number;
  y: number;
  sides: ZoneSide[];
  arrow: ZoneSide | null;
  phase: number;
}

const SIDE_OF: Readonly<Record<string, ZoneSide>> = { north: "n", east: "e", south: "s", west: "w" };
const SIDE_VEC: Readonly<Record<ZoneSide, readonly [number, number]>> = { n: [0, -1], s: [0, 1], w: [-1, 0], e: [1, 0] };
const DIRECTION_TEXT: Readonly<Record<string, string>> = { north: "北", east: "東", south: "南", west: "西" };
const AFFECTS_TEXT: Readonly<Record<ZoneView["affects"], string>> = {
  enemies: "影響施放者的敵人",
  allies: "影響施放者的友方",
  all: "影響所有人",
};
const WHEN_TEXT: Readonly<Record<ZoneView["when"], string>> = {
  enter: "進入時結算",
  turn_start: "回合開始時站在裡面才結算",
  both: "進入或回合開始時結算",
};

/**
 * 區域還在場的輪數（含本輪）：到第 `expires_round` 輪施放者的回合結束時消失，
 * 所以這一輪起算還有 `expires − 目前輪數 + 1` 輪（同召喚物）。
 */
export function zoneRemaining(view: BattleView, z: ZoneView): number {
  return Math.max(0, z.expires_round - view.round + 1);
}

/** 移動型區域的前進方向（不認得的方向為 `null`）。 */
export function zoneSide(z: ZoneView): ZoneSide | null {
  return z.anchor === "moving" && z.direction !== null ? (SIDE_OF[z.direction] ?? null) : null;
}

/**
 * 區域對「目前玩家陣營」的影響：不會影響到我方單位 → `none`（例：我方的火牆只打敵人、敵方的增益區）；
 * 會影響，且有傷害或有害狀態 → `harm`；只有治療、護盾或增益 → `help`。
 * 影響施放者的敵人 → 施放者是敵方才會打到我方；影響施放者的友方 → 施放者是我方才會影響我方；
 * 影響所有人 → 一定影響我方，看伺服器的 `harmful`。
 */
export function zoneEffectOn(z: ZoneView, viewerTeam: string): ZoneEffect {
  if (z.affects === "enemies") return z.team !== viewerTeam ? "harm" : "none";
  if (z.affects === "allies") return z.team === viewerTeam ? (z.harmful ? "harm" : "help") : "none";
  return z.harmful ? "harm" : "help";
}

/** 區域對「目前玩家陣營」是不是有害（會打到我方）。 */
export function zoneHarmfulTo(z: ZoneView, viewerTeam: string): boolean {
  return zoneEffectOn(z, viewerTeam) === "harm";
}

/** 視圖的區域；舊的錄製回應（3D-5 之前）沒有 `zones` 欄位，視為沒有區域。 */
export function zonesOf(view: BattleView): readonly ZoneView[] {
  return view.zones ?? [];
}

/** 每個區域一筆（依區域編號）。`skills` 查區域技能的元素與表面；沒有時顏色退回灰色。 */
export function zoneDraws(view: BattleView, skills?: FxSkills): ZoneDraw[] {
  return zonesOf(view).map((z) => {
    const fx = skills?.(z.skill_id);
    const owner = view.units.find((u) => u.id === z.owner_id);
    return {
      id: z.id,
      cells: [...z.cells].sort((a, b) => a.y - b.y || a.x - b.x).map((c) => ({ x: c.x, y: c.y })),
      harmful: zoneHarmfulTo(z, view.team),
      effect: zoneEffectOn(z, view.team),
      element: fx?.zoneElement ?? fx?.element ?? null,
      surface: fx?.surface ?? null,
      anchor: z.anchor,
      side: zoneSide(z),
      caster: z.anchor === "caster" && owner !== undefined && !owner.downed ? { x: owner.pos.x, y: owner.pos.y } : null,
      turns: zoneRemaining(view, z),
    };
  });
}

/** 區域每格的繪圖規格：只描外緣（鄰格同區域的邊不描）、移動型在前進側沒有鄰格的格子畫箭頭。 */
export function zoneCellSpecs(z: ZoneDraw): ZoneCellSpec[] {
  const has = new Set(z.cells.map((c) => `${c.x},${c.y}`));
  const isIn = (x: number, y: number): boolean => has.has(`${x},${y}`);
  return z.cells.map((c) => {
    const sides = (["n", "s", "w", "e"] as const).filter((s) => !isIn(c.x + SIDE_VEC[s][0], c.y + SIDE_VEC[s][1]));
    const arrow = z.side !== null && sides.includes(z.side) ? z.side : null;
    return { x: c.x, y: c.y, sides, arrow, phase: (((-(c.x + c.y) * 2) % 10) + 10) % 10 };
  });
}

/** 剩餘回合徽章所在的格子：區域最左上那一格。 */
export function zoneBadgeCell(z: ZoneDraw): Pos | null {
  return z.cells[0] ?? null;
}

function anchorText(z: ZoneView): string {
  if (z.anchor === "caster") return "跟著施放者移動";
  if (z.anchor === "moving" && z.direction !== null) {
    return `每次環境回合向${DIRECTION_TEXT[z.direction] ?? z.direction}前進 ${z.speed} 格`;
  }
  return "固定不動";
}

/** 一個區域的說明：「火牆（召喚師英雄）：影響施放者的敵人，進入或回合開始時結算，每次環境回合向北前進 1 格，剩 2 輪（第 3 輪結束時消失）」。 */
export function zoneLine(view: BattleView, z: ZoneView, names: UnitNames): string {
  const left = zoneRemaining(view, z);
  return (
    `${z.name_zh}（${names.label(z.owner_id)}）：${AFFECTS_TEXT[z.affects]}，${WHEN_TEXT[z.when]}，` +
    `${anchorText(z)}，剩 ${left} 輪（第 ${z.expires_round} 輪結束時消失）`
  );
}

/** 移動型區域本輪結束時會移到哪裡（沒有時空字串）。 */
export function zoneNextText(z: ZoneView): string {
  if (z.next_cells === null) return "";
  if (z.next_cells.length === 0) return "本輪結束時撞上牆壁而消失";
  const cells = z.next_cells.map((c) => `(${c.x}, ${c.y})`).join("、");
  return `本輪結束時移到 ${cells}`;
}

/** 技能預覽建立的持續區域（最少後果模擬的 `zone_created` 事件文字）：「區域：…」。 */
export function zonePreviewLines(events: readonly Record<string, unknown>[]): string[] {
  const lines: string[] = [];
  for (const e of events) {
    if (e.type !== "zone_created" || typeof e.text !== "string") continue;
    lines.push(`區域：${e.text.trim()}`);
  }
  return lines;
}

/** 滑過格子時的說明：涵蓋這一格的每個區域一行。 */
export function zoneLinesAt(view: BattleView, tile: Pos | null, names: UnitNames): string[] {
  if (tile === null) return [];
  return zonesOf(view)
    .filter((z) => z.cells.some((c) => c.x === tile.x && c.y === tile.y))
    .map((z) => {
      const next = zoneNextText(z);
      return `區域 ${zoneLine(view, z, names)}${next === "" ? "" : `；${next}`}`;
    });
}
