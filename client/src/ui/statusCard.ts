// 戰鬥的主角狀態卡與單位小卡（Phase 6A-2，去文字化③；docs/archive/art/去文字化移植需求.md 第 3 節）：
// 條（HP、法力、耐力）與一排「圖示＋數字」的資料。純函式，不碰 React；元件在 `StatusCardParts.tsx`、`Hud.tsx`、`UnitInfo.tsx`。
// 說明卡文字一律用現有的句子（`actionCardText`、HUD 原本的提示、武器特性、狀態句……），第一行是「名稱 現值」。
import type { BattleView, StatusView, UnitView } from "../api/types";
import { actionCardText } from "../battle/actionInfo";
import { ammoPips, ammoText, hasMagazine } from "../battle/ammo";
import { HIDDEN_INFO_HINT, UNKNOWN_MARK } from "../battle/hiddenInfo";
import { sourcePips } from "../battle/source";

export type BarKind = "hp" | "mana" | "stamina";

export interface BarData {
  kind: BarKind;
  /** 條上的字：「HP 41 / 50」。 */
  text: string;
  value: number;
  max: number;
  /** 護盾（只有 HP 條）：疊一段淺藍，數字只在說明卡。 */
  shield: number;
  hint: string;
  /** HID-1：看不到 HP（隱蔽中的敵人）：條畫灰色整條、字寫「HP ？ / 最大」。 */
  unknown?: boolean;
}

const BAR_NAME: Readonly<Record<BarKind, string>> = { hp: "HP", mana: "法力", stamina: "耐力" };

/**
 * HP、法力、護盾的說明句（6A-3；玩法 PM 給的文字，一字不改）。主角狀態卡與單位小卡共用。
 * 伺服器的名詞對照表沒有這三項，所以放在前端。
 */
export const RESOURCE_TEXT = {
  hp: "生命值，歸零就會倒下；靠治療、藥水或營火回復。",
  mana: "施放法術要花法力，戰鬥中不會自然回復；在營火或城鎮回滿。",
  shield: "受到傷害時先扣護盾、再扣生命值；時間到就消失，重複獲得只保留較大的一層。",
} as const;

const lines = (...parts: (string | null | undefined)[]): string => parts.filter((p): p is string => p != null && p !== "").join("\n");

export function barData(kind: BarKind, unit: UnitView): BarData {
  if (kind === "hp" && unit.hp === null) {
    const text = `HP ${UNKNOWN_MARK} / ${unit.max_hp}`;
    return { kind, text, value: unit.max_hp, max: unit.max_hp, shield: 0, hint: lines(text, HIDDEN_INFO_HINT, RESOURCE_TEXT.hp), unknown: true };
  }
  const value = kind === "hp" ? (unit.hp ?? 0) : kind === "mana" ? unit.mana : unit.stamina;
  const max = kind === "hp" ? unit.max_hp : kind === "mana" ? unit.max_mana : unit.max_stamina;
  const text = `${BAR_NAME[kind]} ${value} / ${max}`;
  const shield = kind === "hp" ? (unit.shield ?? 0) : 0;
  const hint =
    kind === "hp"
      ? lines(text, RESOURCE_TEXT.hp, shield > 0 ? `護盾 ${shield}` : null, shield > 0 ? RESOURCE_TEXT.shield : null)
      : kind === "stamina"
        ? lines(text, actionCardText("stamina"))
        : lines(text, RESOURCE_TEXT.mana);
  return { kind, text, value, max, shield, hint };
}

/** 條的填滿比例與護盾段（0..1）：護盾接在 HP 後面，超出時靠右疊在 HP 上。 */
export function barFill(value: number, max: number, shield = 0): { fill: number; shieldLeft: number; shieldWidth: number } {
  const ratio = (v: number) => (max <= 0 ? 0 : Math.max(0, Math.min(1, v / max)));
  const fill = ratio(value);
  const shieldWidth = ratio(shield);
  return { fill, shieldLeft: Math.min(fill, 1 - shieldWidth), shieldWidth };
}

export type StatIcon = "ap" | "move" | "reaction" | "source" | "shield" | "mana" | "weapon" | "ammo";

export interface StatChip {
  key: string;
  icon: StatIcon;
  /** 圖示旁的數字或短字；空字串＝只有圖示（圓點另外畫）。 */
  label: string;
  /** 圓點：`true` 實心、`false` 空心；`null`＝不畫圓點。 */
  pips: boolean[] | null;
  /** 用過、沒有了：變灰。 */
  dim: boolean;
  hint: string;
}

/** AP 圓點：5 點以內畫圓點，多了寫數字。 */
const AP_PIP_LIMIT = 5;

export function apChip(unit: UnitView): StatChip {
  const pips = unit.ap <= AP_PIP_LIMIT ? Array.from({ length: Math.max(1, unit.ap) }, () => unit.ap > 0) : null;
  const carry = unit.ap_carry > 0 ? `（下回合保留 +${unit.ap_carry}）` : null;
  return {
    key: "ap",
    icon: "ap",
    label: pips === null ? String(unit.ap) : "",
    pips,
    dim: unit.ap <= 0,
    hint: lines(`AP ${unit.ap}${carry ?? ""}`, "剩餘行動點數（自己的回合已含上回合保留的 AP）"),
  };
}

export function moveChip(unit: UnitView): StatChip {
  return {
    key: "move",
    icon: "move",
    label: String(unit.move_points),
    pips: null,
    dim: unit.move_points <= 0,
    hint: lines(`移動 ${unit.move_points}`, "剩餘移動點數", actionCardText("move")),
  };
}

export function reactionChip(unit: UnitView): StatChip {
  const on = unit.reaction_available;
  return {
    key: "reaction",
    icon: "reaction",
    label: "",
    pips: null,
    dim: !on,
    hint: lines(`反應 ${on ? "可用" : "已用"}`, "本輪還能反應嗎"),
  };
}

export function sourceChip(unit: UnitView): StatChip {
  return {
    key: "source",
    icon: "source",
    label: "",
    pips: sourcePips(unit.source, unit.source_max),
    dim: unit.source <= 0,
    hint: lines(`源力 ${unit.source}/${unit.source_max}`, "傳說技能的代價（跨戰鬥保留，每場至少 1 點；走上地圖上的「源」格 +1）"),
  };
}

export function ammoChip(unit: UnitView): StatChip | null {
  if (!hasMagazine(unit)) return null;
  return {
    key: "ammo",
    icon: "ammo",
    label: unit.ammo <= 0 ? "空膛" : "",
    pips: ammoPips(unit.ammo, unit.magazine),
    dim: unit.ammo <= 0,
    hint: `${ammoText(unit)}：開火一次用掉 1 發，空膛時從「更多動作」選單裝填`,
  };
}

/** 主角狀態卡的一排圖示（條以外）：AP、移動、彈匣、反應、源力。狀態、層數與腳下表面另外畫。 */
export function heroChips(hero: UnitView): StatChip[] {
  const ammo = ammoChip(hero);
  return [apChip(hero), moveChip(hero), ...(ammo === null ? [] : [ammo]), reactionChip(hero), sourceChip(hero)];
}

/** 單位小卡的一排圖示：護盾（有才畫）、法力（有上限才畫）、AP、移動、武器（、彈匣）。 */
export function unitChips(unit: UnitView): StatChip[] {
  const chips: StatChip[] = [];
  if (unit.shield === null) {
    // HID-1：看不到護盾（隱蔽中的敵人）
    chips.push({ key: "shield", icon: "shield", label: UNKNOWN_MARK, pips: null, dim: true, hint: lines(`護盾 ${UNKNOWN_MARK}`, HIDDEN_INFO_HINT) });
  } else if (unit.shield > 0) {
    chips.push({ key: "shield", icon: "shield", label: String(unit.shield), pips: null, dim: false, hint: lines(`護盾 ${unit.shield}`, RESOURCE_TEXT.shield) });
  }
  if (unit.max_mana > 0) {
    chips.push({ key: "mana", icon: "mana", label: String(unit.mana), pips: null, dim: unit.mana <= 0, hint: lines(`法力 ${unit.mana} / ${unit.max_mana}`, RESOURCE_TEXT.mana) });
  }
  chips.push({ ...apChip(unit), label: String(unit.ap), pips: null });
  chips.push(moveChip(unit));
  if (unit.weapon_name_zh !== "") {
    chips.push({
      key: "weapon",
      icon: "weapon",
      label: unit.weapon_name_zh,
      pips: null,
      dim: false,
      hint: lines(`武器 ${unit.weapon_name_zh}`, ...unit.weapon_traits_zh),
    });
  }
  const ammo = ammoChip(unit);
  if (ammo !== null) chips.push(ammo);
  return chips;
}

/** 元素架勢的 ID 樣式（同 `render/qIcon/status.ts` 的 `entry` 與樣張）：`stance_<元素>_<級>`，級數 1～5。 */
export const ELEMENT_STANCE_RE = /^stance_(physical|fire|ice|lightning|poison|wind|earth|holy|shadow)_([1-5])$/;

/**
 * 晶能湧動／晶能狂湧的階（QI-3b，D3）：前端名單（比照 `CREATURE_CHARGE_SKILLS`；後端不帶欄位）。
 * 兩個 ID 在名詞表快照裡（`ui/qi3bStatusCorner.test.ts` 擋改名）。
 */
export const CRYSTAL_SURGE_TIER: Readonly<Record<string, number | undefined>> = { crystal_surge: 1, crystal_surge_2: 2 };

/** 狀態本身的級數（元素架勢 1～5、晶能湧動／狂湧 1／2）；沒有回 null。 */
export function statusTier(id: string): number | null {
  const m = ELEMENT_STANCE_RE.exec(id);
  if (m !== null) return Number(m[2]);
  return CRYSTAL_SURGE_TIER[id] ?? null;
}

/**
 * 狀態圖示右下角的數字：級數（元素架勢、晶能湧動／狂湧；QI-3b D2、D3，優先於回合數與數值）→ 剩餘回合 →
 * 數值（層數、蓄力段數……）→ 都沒有時不寫。
 */
export function statusCorner(s: StatusView): string {
  const tier = statusTier(s.status_id);
  if (tier !== null) return String(tier);
  if (s.remaining !== null) return String(s.remaining);
  if (s.amount !== null) return String(s.amount);
  return "";
}

/** 層數（`stacks`）：大於 0 的，依 ID 排序。 */
export function activeStacks(unit: UnitView): [string, number][] {
  return Object.entries(unit.stacks)
    .filter(([, n]) => n > 0)
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
}

/** 單位腳下的表面 ID；沒有表面時 `null`。 */
export function surfaceAt(view: BattleView, unit: UnitView): string | null {
  const tile = view.tiles.find((t) => t.x === unit.pos.x && t.y === unit.pos.y);
  return tile === undefined || tile.surface === "none" ? null : tile.surface;
}

/** 圖釘：點同一個單位取消，點別的單位改釘它（同時只釘一張）。 */
export function togglePin(current: string | null, id: string): string | null {
  return current === id ? null : id;
}

/**
 * 釘選小卡要顯示的單位：用畫面上正在播放的視圖（敵人回合也跟著更新）；單位不在戰場上了就不畫。
 * 倒下的單位仍在 `units` 裡，照常顯示。
 */
export function pinnedUnitOf(view: BattleView, id: string | null): UnitView | null {
  return id === null ? null : (view.units.find((u) => u.id === id) ?? null);
}

/** 釘選小卡收成精簡版的視窗寬度門檻（6A-3；美術 PM 6A-2 檢查第 2 項）。 */
export const PIN_COMPACT_WIDTH = 1000;

/**
 * 釘住的小卡要不要收成精簡版（只留名稱、HP 條、耐力條）：視窗寬度不到 1000 時收起，
 * 滑鼠移到小卡上（觸控是點一下）才展開。
 */
export function pinnedCompact(viewportWidth: number, expanded: boolean): boolean {
  return viewportWidth < PIN_COMPACT_WIDTH && !expanded;
}

export interface AffixBadge {
  /** 徽章上的字：「狂暴」。 */
  label: string;
  /** 說明卡：特性欄那一整句。 */
  hint: string;
}

const AFFIX_LINE = /^精英詞綴「([^」]+)」/;

/**
 * 名稱旁的金色徽章：精英詞綴（特性欄「精英詞綴「X」：…」那一句，滑過看整句）；
 * 有 `elite` 標籤但沒有詞綴句時一個「精英」徽章。
 */
export function affixBadges(unit: UnitView): AffixBadge[] {
  const badges = (unit.traits_zh ?? []).flatMap((line): AffixBadge[] => {
    const m = AFFIX_LINE.exec(line);
    return m === null ? [] : [{ label: m[1] ?? "", hint: line }];
  });
  if (badges.length === 0 && unit.tags.includes("elite")) return [{ label: "精英", hint: "精英" }];
  return badges;
}
