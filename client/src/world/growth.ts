// 大世界成長畫面的純函式（Phase 5A-7；docs/phases/Phase5計畫.md 13.3）。規則與可用狀態都由後端
// `WorldView.growth`／`oath` 下發，這裡只把一輪元件送出的選擇轉成世界動作、決定畫面顯示什麼。
import type { RunChoice, WorldAction, WorldOathTemplate, WorldView } from "../api/types";

/** 一輪元件（配點、閃現、重閃、溶掉、傳承）送出的選擇 → 世界動作；大世界沒有的選擇為 `null`。 */
export function worldActionOf(choice: RunChoice): WorldAction | null {
  switch (choice.kind) {
    case "allocate":
      return { kind: "allocate", attributes: choice.attributes ?? {} };
    case "respec_attributes":
      return { kind: "respec" };
    case "flash":
      return { kind: "flash", skill: choice.skill, slot: choice.slot ?? null, category: choice.category ?? null };
    case "flash_pick":
      return { kind: "flash_pick", pick: choice.pick, unequip: choice.unequip ?? null };
    case "dissolve":
      return { kind: "dissolve", skill: choice.skill };
    case "inherit":
      return { kind: "inherit", skill: choice.skill, source: choice.source, records: choice.records };
    default:
      return null;
  }
}

/** 左欄顯示：閃現待選時固定是選項畫面、任務三選一待選時固定是三選一（閃現優先，5B-5）；
 * 否則照玩家切換（地點圖、成長、任務與線頭；5D-4 加背包、商店、鐵匠）。`want` 給布林時＝舊的「成長／地點圖」切換。
 * 商店、鐵匠只在這裡有店或設施時才開得了（離開城鎮就回到地點圖）；背包要有經濟資料。 */
export type LeftPane = "map" | "growth" | "pending" | "offer" | "quests" | "bag" | "shop" | "smithy";
export type WantPane = "map" | "growth" | "quests" | "bag" | "shop" | "smithy";

export function leftPane(view: WorldView, want: boolean | WantPane): LeftPane {
  if (view.pending_flash != null) return "pending";
  if (view.pending_offer != null) return "offer";
  if (typeof want === "boolean") return want ? "growth" : "map";
  if (want === "shop" && view.shop == null) return "map";
  if (want === "smithy" && view.crafting == null) return "map";
  if (want === "bag" && view.inventory == null) return "map";
  return want;
}

/** 左欄切換鈕：再點同一個回到地點圖。 */
export function togglePane(current: WantPane, clicked: WantPane): WantPane {
  return current === clicked ? "map" : clicked;
}

/** 「成長與技能」按鈕上的小字：有可用的點數時提醒。 */
export function growthBadge(view: WorldView): string {
  const parts: string[] = [];
  if (view.character.attribute_points > 0) parts.push(`屬性點 ${view.character.attribute_points}`);
  if (view.growth.insight > 0) parts.push(`靈感 ${view.growth.insight}`);
  return parts.join("・");
}

/** 花靈感與重配被擋住的原因（可以時為 `null`）：不在城鎮或營火、有遭遇、待選、戰鬥中。 */
export function spendLock(view: WorldView): string | null {
  return view.growth.can_spend ? null : (view.growth.blocked_zh ?? "現在不能花點");
}

/** 立誓按鈕的文字與停用原因。 */
export function oathButton(view: WorldView): { label: string; reason: string | null } {
  const oath = view.oath;
  if (!oath.available) return { label: `立誓（${oath.unavailable_zh ?? "尚未開放"}）`, reason: oath.unavailable_zh ?? "尚未開放" };
  return { label: "立誓", reason: oath.can_swear ? null : oath.swear_problem_zh };
}

/** 模板參數的初值：選單取第一個、數字取最小值。 */
export function defaultParams(template: WorldOathTemplate): Record<string, string | number> {
  const out: Record<string, string | number> = {};
  for (const p of template.params ?? []) out[p.id] = p.kind === "choice" ? (p.choices?.[0] ?? "") : (p.min ?? 0);
  return out;
}

type OathParam = NonNullable<WorldOathTemplate["params"]>[number];

/** 參數的中文名（5C-3；沒有時退回 ID）。 */
export function paramLabel(param: OathParam): string {
  return param.name_zh !== undefined && param.name_zh !== "" ? param.name_zh : param.id;
}

/** 選單值的中文名（5C-3；沒有時退回原值）。 */
export function choiceLabel(param: OathParam, value: string): string {
  return param.choice_names_zh?.[value] ?? value;
}

/** 立誓的世界動作（來源一律是模板選單，代決 5A7-4）。 */
export function swearAction(template: string, params: Record<string, string | number>, text: string): WorldAction {
  return { kind: "swear_oath", proposal: { template, params }, player_text: text.trim() };
}
