// 滑過格子的資訊卡內容（Phase 3-15，純函式）：地形與高度、表面、物件、可見陷阱，
// 以及呼叫端傳入的持續區域與環境預告文字。靜態說明（「會怎樣」）來自 /api/glossary 的 rules_zh
// （後端 trpg.narrative.tile_info 由內容資料產生）；動態部分（剩餘回合、HP）從視圖組合。
import type { BattleView, Pos, TileView } from "../api/types";
import type { SkillNames } from "./actions";
import { glossaryEntry, glossaryName } from "./glossary";
import { markerCard } from "./objective";

// 與圖例（legend.ts）共用的用語；測試比對兩邊一致。
export const LABEL_DEADLY = "致命地形";
export const LABEL_BURNING = "燃燒中";
export const LABEL_TRAP = "陷阱";
export const LABEL_ZONE = "持續區域";

export type TileSectionKind = "terrain" | "surface" | "object" | "trap" | "zone" | "objective";

export interface TileSection {
  kind: TileSectionKind;
  /** 標題列（名稱與動態資訊）；規則只有一句時併在標題後面。 */
  title: string;
  /** 逐行規則（兩句以上才列）。 */
  lines: string[];
}

function section(kind: TileSectionKind, head: string, rules: readonly string[]): TileSection {
  if (rules.length <= 1) return { kind, title: [head, ...rules].join("・"), lines: [] };
  return { kind, title: head, lines: [...rules] };
}

function tileAt(view: BattleView, pos: Pos): TileView | undefined {
  return view.tiles.find((t) => t.x === pos.x && t.y === pos.y);
}

function rulesOf(category: "terrain" | "surfaces" | "objects", id: string): readonly string[] {
  return glossaryEntry(category, id)?.rules_zh ?? [];
}

/** 持續時間那一行（表面規則「由技能產生時持續 N 回合…」）；沒有剩餘回合的永久表面不寫。 */
const DURATION_RULE = /^由技能產生時持續/;

/**
 * 物件的規則前 `tagCount` 行是標籤短句（後端 `OBJECT_TAG_TEXT`，一個標籤一行）：濃縮成一行，
 * 去掉括號補充、用「・」連接（「不可通行・半掩護・可推動」）；其餘（欄位說明、互動結果）照舊逐行。
 */
export function condenseObjectRules(rules: readonly string[], tagCount: number): string[] {
  const tags = rules.slice(0, tagCount).map((r) => r.replace(/（.*?）/g, "").trim());
  return [...(tags.length > 0 ? [tags.join("・")] : []), ...rules.slice(tagCount)];
}

function objectSection(view: BattleView, tile: TileView): TileSection | null {
  const obj =
    view.objects.find((o) => o.id === tile.object_id) ??
    view.objects.find((o) => o.pos.x === tile.x && o.pos.y === tile.y);
  if (obj === undefined) return null;
  const head = [glossaryName("objects", obj.kind)];
  if (obj.hp !== null) head.push(`HP ${obj.hp}/${obj.max_hp ?? obj.hp}`);
  if (obj.burning !== null && obj.burning > 0) head.push(LABEL_BURNING);
  if (obj.expires_in != null) head.push(`剩 ${obj.expires_in} 回合消失`);
  return section("object", head.join("・"), condenseObjectRules(rulesOf("objects", obj.kind), glossaryEntry("objects", obj.kind)?.tags.length ?? 0));
}

/**
 * 格子資訊卡的各段；`extra` 是這一格涉及的持續區域與環境預告文字（已組好的句子）。
 * 視圖沒有這一格時回傳空陣列。
 */
export function tileSections(
  view: BattleView,
  pos: Pos | null,
  skills: SkillNames,
  extra: readonly string[] = [],
): TileSection[] {
  if (pos === null) return [];
  const tile = tileAt(view, pos);
  if (tile === undefined) return [];
  const out: TileSection[] = [
    section("terrain", `${glossaryName("terrain", tile.terrain)}・高度 ${tile.height}`, rulesOf("terrain", tile.terrain)),
  ];
  if (tile.surface !== "none") {
    const left = tile.surface_remaining === null ? "" : `・剩 ${tile.surface_remaining} 回合`;
    const rules = rulesOf("surfaces", tile.surface).filter((r) => tile.surface_remaining !== null || !DURATION_RULE.test(r));
    out.push(section("surface", `${glossaryName("surfaces", tile.surface)}${left}`, rules));
  }
  const obj = objectSection(view, tile);
  if (obj !== null) out.push(obj);
  const goal = markerCard(view, pos);
  if (goal !== null) out.push(section("objective", goal.title, goal.lines));
  for (const t of view.traps.filter((x) => x.pos.x === pos.x && x.pos.y === pos.y)) {
    out.push({
      kind: "trap",
      title: `${LABEL_TRAP}：${skills[t.skill_id] ?? t.skill_id}・剩 ${t.remaining} 回合`,
      lines: [],
    });
  }
  if (extra.length > 0) out.push({ kind: "zone", title: `${LABEL_ZONE}與預告`, lines: [...extra] });
  return out;
}

/** 收起的資訊卡（格子上有單位時，使用者選擇收起）：只留地形那一行標題。 */
export function collapseSections(sections: readonly TileSection[]): TileSection[] {
  const first = sections[0];
  return first === undefined ? [] : [{ ...first, lines: [] }];
}
