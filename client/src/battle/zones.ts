// 持續區域（Phase 3D-5）：格子上的半透明底色與方向箭頭、HUD 清單、滑過格子的說明（純函式）。
import type { BattleView, Pos, ZoneView } from "../api/types";
import { HIGHLIGHT } from "./glossary";
import type { UnitNames } from "./units";

export interface ZoneDraw {
  x: number;
  y: number;
  color: number;
  /** 移動型區域的方向箭頭（每格都畫）；其他區域為 `null`。 */
  arrow: string | null;
}

const ARROWS: Readonly<Record<string, string>> = { north: "↑", east: "→", south: "↓", west: "←" };
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

export function zoneColor(z: ZoneView): number {
  return z.harmful ? HIGHLIGHT.zone_harmful : HIGHLIGHT.zone_helpful;
}

export function zoneArrow(z: ZoneView): string | null {
  return z.anchor === "moving" && z.direction !== null ? (ARROWS[z.direction] ?? null) : null;
}

/** 視圖的區域；舊的錄製回應（3D-5 之前）沒有 `zones` 欄位，視為沒有區域。 */
export function zonesOf(view: BattleView): readonly ZoneView[] {
  return view.zones ?? [];
}

/** 每個區域格一筆（同一格有多個區域時各畫一層，依區域編號）。 */
export function zoneDraws(view: BattleView): ZoneDraw[] {
  const out: ZoneDraw[] = [];
  for (const z of zonesOf(view)) {
    const color = zoneColor(z);
    const arrow = zoneArrow(z);
    for (const c of z.cells) out.push({ x: c.x, y: c.y, color, arrow });
  }
  return out;
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
