// 召喚物（Phase 3D-4b）：剩餘輪數、召喚物清單、技能預覽的召喚位置與圖騰光環範圍（純函式）。
import type { BattleView, Pos, PreviewOut, UnitView } from "../api/types";
import { isAlive, type UnitNames } from "./units";

export type SummonOut = NonNullable<PreviewOut["summons"]>[number];

/**
 * 召喚物還能行動幾輪（含本輪）：到第 `summon_expires_round` 輪召喚者的回合結束時消失，
 * 所以這一輪起算還有 `expires − 目前輪數 + 1` 輪。一般單位為 `null`。
 */
export function remainingRounds(view: BattleView, u: UnitView): number | null {
  if (u.owner_id === null || u.summon_expires_round === null) return null;
  return Math.max(0, u.summon_expires_round - view.round + 1);
}

export function isSummon(u: UnitView): boolean {
  return u.owner_id !== null;
}

export function isTotem(u: UnitView): boolean {
  return u.totem_radius !== null;
}

/** `ownerId`（通常是主角）目前在場上的召喚物，依單位 ID 排序。 */
export function summonsOf(view: BattleView, ownerId: string): UnitView[] {
  return view.units
    .filter((u) => u.owner_id === ownerId && isAlive(u))
    .sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}

/** HUD／單位資訊的一行：「骷髏戰士1　HP 20/20　剩 2 輪（第 5 輪結束時消失）」。 */
export function summonLine(view: BattleView, u: UnitView): string {
  const left = remainingRounds(view, u);
  const when = left === null ? "" : `　剩 ${left} 輪（第 ${u.summon_expires_round} 輪結束時消失）`;
  const kind = isTotem(u) ? `　圖騰：${u.totem_radius} 格內的友方獲得增益` : "";
  return `${u.name_zh}　HP ${u.hp}/${u.max_hp}${when}${kind}`;
}

/** 單位標籤用的簡稱：「召喚物」「圖騰」；一般單位為 `null`。 */
export function summonKind(u: UnitView): string | null {
  if (!isSummon(u)) return null;
  return isTotem(u) ? "圖騰" : "召喚物";
}

/** 圖騰光環涵蓋的格子（曼哈頓距離內，含圖騰所在格）。 */
export function auraTiles(center: Pos, radius: number, view: BattleView): Pos[] {
  const out: Pos[] = [];
  for (let y = 0; y < view.height; y++) {
    for (let x = 0; x < view.width; x++) {
      if (Math.abs(x - center.x) + Math.abs(y - center.y) <= radius) out.push({ x, y });
    }
  }
  return out;
}

/** 預覽的召喚說明（可能多行：召喚位置、持續、被擠掉的舊召喚物、圖騰的光環範圍）。 */
export function summonLines(p: PreviewOut, names: UnitNames): string[] {
  const lines: string[] = [];
  for (const s of p.summons ?? []) {
    const at = `(${s.pos[0]}, ${s.pos[1]})`;
    const base = `召喚：${s.name_zh}（HP ${s.max_hp}）出現在 ${at}，緊接在你之後行動，第 ${s.expires_round} 輪你的回合結束時消失`;
    const aura = s.totem_radius == null ? "" : `；圖騰不移動、不攻擊，每次行動開始時讓 ${s.totem_radius} 格內的友方獲得增益`;
    lines.push(base + aura);
    if (s.replaces.length > 0) {
      lines.push(`⚠ 同時存在的召喚物已達上限，${s.replaces.map((id) => names.label(id)).join("、")} 會消失`);
    }
  }
  return lines;
}
