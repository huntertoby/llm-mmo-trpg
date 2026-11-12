// Phase QI-2b：遊戲端 `skillIcon.ts::partsOf` 的結果 → Q 版組裝要的純資料部件結構 `QParts`（`parts.ts`）。
// 拆解規則只留 `partsOf` 一份（規格 B2、需求 2.4 第 8 列）；這裡只換欄位，不另判斷核心效果、去重、最多 4 個。
// 樣張 `partsOf` 多出來的兩樣從原始資料補：每個效果列項目在第幾段（`seg`，接續記號要排在第二段第一個前面；規格第 0.1 節第 1 點），
// 修正內容的數值與 `on_hit_effects` 的底圖（`value`、`base`）。
// 只用型別匯入 `skillIcon.ts`（2c 讓 `skillIcon.ts` 匯入 Q 版畫法時才不會循環）。
import type { SkillIconData } from "../../api/types";
import type { IconParts } from "../skillIcon";
import { effectPart } from "../skillParts";
import { entry, type QPartItem, type QParts } from "./parts";
import type { SkillLook } from "./skills";

/** 後端 `SkillIcon.art`（QI-2a）。 */
export interface SkillArt { prop: string; motion: string; act: string; tint?: string | null; spark?: string | null }
/** 沒有 `art` 的舊資料畫什麼（規格第 0 節第 5 列、第 5 節 API 列：`none`／`aura`／`buff`）。 */
export const NO_ART: SkillArt = { prop: "none", motion: "aura", act: "buff", tint: null, spark: null };

/** 圖示資料 ＋ `art` → 主圖代碼（元素底 el／el2 直接用 `elements[0]`／`[1]`，需求 3.2）。 */
export function skillLook(icon: SkillIconData, art: SkillArt | null | undefined): SkillLook {
  const a = art ?? NO_ART;
  return { prop: a.prop, motion: a.motion, act: a.act, tint: a.tint ?? null, spark: a.spark ?? null, el: icon.elements[0] ?? null, el2: icon.elements[1] ?? null, kind: icon.kind, rarity: icon.rarity };
}

/** `partsOf(icon)` 的結果 → `QParts`。 */
export function toQParts(icon: SkillIconData, parts: IconParts): QParts {
  const segOf = (key: string): number => {
    const i = icon.segments.findIndex((s) => s.effects.some((e) => effectPart(e).key === key));
    return i === -1 ? 0 : i;
  };
  const changes = icon.modifier?.changes ?? [];
  const item = (key: string): QPartItem => {
    if (icon.modifier == null) return { cat: "effect", id: key, seg: segOf(key) };
    const ch = changes.find((c) => c.key === key);
    const first = ch?.part_ids?.[0];
    const value = ch?.value as QPartItem["value"];
    return { cat: "change", id: key, seg: 0, value, base: key === "on_hit_effects" && first ? (c, o) => entry("effect", first.replace(/^apply_status:/, "status:")).d(c, o) : undefined };
  };
  const row = parts.effects.map((p) => item(p.key));
  const coreKey = parts.core?.key;
  return {
    kind: parts.kind,
    rarity: parts.rarity,
    el: parts.el ?? null,
    skeleton: parts.segs[0]?.motif.skeleton ?? null,
    trigger: parts.trigger?.key ?? null,
    link: parts.link?.key ?? null,
    cond: parts.condition === null ? null : { cat: "condition", id: parts.condition.key },
    costs: parts.costs.map((c) => c.key),
    row,
    core: coreKey === undefined ? null : (row.find((r) => r.id === coreKey) ?? null),
    shape: icon.segments.map((s) => s.shape_id ?? ""),
  };
}
