// 戰鬥的主角狀態卡與單位小卡（Phase 6A-2，去文字化③；docs/archive/art/去文字化移植需求.md 第 3 節）：
// 條（HP、法力、耐力）與一排「圖示＋數字」的資料。純函式，不碰 React；元件在 `StatusCardParts.tsx`、`Hud.tsx`、`UnitInfo.tsx`。
// 說明卡文字一律用現有的句子（`actionCardText`、HUD 原本的提示、武器特性、狀態句……），第一行是「名稱 現值」。
import type { BattleView, SkillCard, StatusView, UnitView } from "../api/types";
import { actionCardText } from "../battle/actionInfo";
import { ammoPips, ammoText, hasMagazine } from "../battle/ammo";
import { HIDDEN_INFO_HINT, UNKNOWN_MARK } from "../battle/hiddenInfo";
import { sourcePips } from "../battle/source";
import { stackSkillNames } from "../battle/stackInfo";
import { GAUGE_MAX, hasGauge } from "../render/qIcon/stackGauge";

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
  /** AP 列（AP-1）：有的時候圓點照這裡畫（每顆有自己的說明、保留環、紅斜線、分隔線），`pips` 只是實心與否。 */
  apRow?: ApRow;
}

/**
 * AP 列的一顆圓點（AP-1，#168；畫法見 docs/art/AP-1-AP列畫法.md）：
 * `ap`＝一般 AP（實心金／用掉空心）；`kept`＝上回合保留的那格（多一圈米白環，用掉後環還在）；
 * `borrow`＝預支來的那格（AP-2：橘色菱形，用掉後變空心橘框）；
 * `lost`＝少掉的那格（空心＋紅斜線）。`keep`＝現在結束回合會被保留的那顆（滑過「結束回合」時閃米白環）。
 * `fresh`＝這回合預支剛畫上的菱形與下回合紅斜線（淡入 200 ms）。
 */
export interface ApPip {
  kind: "ap" | "kept" | "borrow" | "lost";
  on: boolean;
  keep: boolean;
  hint: string;
  fresh?: boolean;
}

/** AP 列：分隔線左邊是這回合（一般 AP、少掉的、保留的、預支的），右邊是下回合會少的。 */
export interface ApRow {
  now: ApPip[];
  next: ApPip[];
}

/** AP 圓點最多畫幾顆（含保留、少掉、預支、下回合會少的；4 金＋1 保留＋2 預支｜2 紅斜線也放得下），多了寫數字。 */
const AP_PIP_LIMIT = 9;

/** 菱形、紅斜線各最多畫幾個（AP-2，畫法文件第 3 節：預支一次 +2／−2 要能並排畫 2 顆；多的寫在說明裡）。 */
const AP_MARK_LIMIT = 2;

/** 玩家看得到的字（docs/art/AP-1-AP列畫法.md 第 5 節，玩法 PM 定案）。 */
export const AP_PIP_TEXT = {
  kept: "上回合保留的 AP",
  borrowed: (n: number) => `預支來的 AP（下回合 −${n}）`,
  /** 下回合只少 1 格時寫來源（HC-6b：格數照實際要少的數，不寫死）。 */
  overdraftNext: (n: number) => `透支：下回合少 ${n} AP`,
  borrowNext: (n: number) => `預支：下回合少 ${n} AP`,
  nextMany: (n: number) => `下回合少 ${n} AP`,
  /** 回合開始時已經扣掉的那格：只有透支、只有預支、兩者疊加（不寫原因）。 */
  lostNow: (n: number) => `透支：這回合少 ${n} AP`,
  lostNowBorrow: (n: number) => `預支：這回合少 ${n} AP`,
  lostNowMixed: (n: number) => `這回合少 ${n} AP`,
} as const;

/** 回合開始時已扣掉那格的說明（AP-2 用字）：只有透支、只有預支、兩者疊加。 */
function lostNowText(lost: number, borrowed: number): string {
  if (borrowed <= 0) return AP_PIP_TEXT.lostNow(lost);
  return borrowed >= lost ? AP_PIP_TEXT.lostNowBorrow(lost) : AP_PIP_TEXT.lostNowMixed(lost);
}

/** 下回合會少那格的說明：合計 2 格以上寫合計，1 格寫來源（預支或透支）。 */
function nextText(next: number, borrowed: number): string {
  if (next >= 2) return AP_PIP_TEXT.nextMany(next);
  return borrowed > 0 ? AP_PIP_TEXT.borrowNext(next) : AP_PIP_TEXT.overdraftNext(next);
}

/**
 * AP 列的圓點（AP-1、AP-2）：`[一般 AP][這回合少掉的][上回合保留的][預支來的] ｜ [下回合會少的]`。
 * 一般 AP＝每回合 AP − 這回合少掉的；AP 被給、被返還而多出來的接在一般 AP 後面。實心的是還沒用的
 * （從左數 `ap` 顆，所以預支、保留的那格最先變空心）。用了預支的回合不保留，所以沒有會被保留的那顆。
 */
export function apRow(unit: UnitView, chipHint: string): ApRow {
  const lost = Math.max(0, unit.ap_lost);
  const kept = Math.max(0, unit.ap_carried_in);
  const borrowedAll = Math.max(0, unit.ap_borrowed);
  const borrowed = Math.min(borrowedAll, AP_MARK_LIMIT);
  const base = Math.max(0, unit.ap_per_turn - lost);
  const extra = Math.max(0, unit.ap - base - kept - borrowedAll) + (borrowedAll - borrowed);
  const fill = [
    ...Array<"ap">(base + extra).fill("ap"),
    ...Array<"kept">(kept).fill("kept"),
    ...Array<"borrow">(borrowed).fill("borrow"),
  ];
  const carryMax = borrowedAll > 0 ? 0 : Math.max(0, unit.ap_max - unit.ap_per_turn);
  const keepFrom = unit.ap - Math.min(unit.ap, carryMax); // 結束回合會保留的：還沒用的最後幾顆
  const borrowHint = AP_PIP_TEXT.borrowed(Math.max(borrowedAll, unit.ap_next_loss_borrowed));
  const hintOf = (kind: "ap" | "kept" | "borrow"): string =>
    kind === "kept" ? AP_PIP_TEXT.kept : kind === "borrow" ? borrowHint : chipHint;
  const gold: ApPip[] = fill.map((kind, i) => ({
    kind,
    on: i < unit.ap,
    keep: i < unit.ap && i >= keepFrom,
    hint: hintOf(kind),
    ...(kind === "borrow" ? { fresh: true } : {}),
  }));
  const slash = (hint: string, fresh = false): ApPip => ({ kind: "lost", on: false, keep: false, hint, ...(fresh ? { fresh } : {}) });
  const lostHint = lostNowText(lost, Math.max(0, unit.ap_lost_borrowed));
  const nowLost = Array.from({ length: Math.min(lost, AP_MARK_LIMIT) }, () => slash(lostHint));
  const nextN = Math.max(0, unit.ap_next_loss);
  const nextHint = nextText(nextN, Math.max(0, unit.ap_next_loss_borrowed));
  const next = Array.from({ length: Math.min(nextN, AP_MARK_LIMIT) }, () => slash(nextHint, borrowedAll > 0));
  return { now: [...gold.slice(0, base + extra), ...nowLost, ...gold.slice(base + extra)], next };
}

export function apChip(unit: UnitView): StatChip {
  const carry = unit.ap_carry > 0 ? `（下回合保留 +${unit.ap_carry}）` : null;
  const hint = lines(`AP ${unit.ap}${carry ?? ""}`, "剩餘行動點數（自己的回合已含上回合保留的 AP）");
  const row = apRow(unit, hint);
  const fits = row.now.length + row.next.length <= AP_PIP_LIMIT && row.now.length > 0;
  return {
    key: "ap",
    icon: "ap",
    label: fits ? "" : String(unit.ap),
    pips: fits ? row.now.map((p) => p.on) : null,
    dim: unit.ap <= 0,
    hint,
    ...(fits ? { apRow: row } : {}),
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
  const { apRow: _row, ...ap } = apChip(unit); // 小卡只寫數字（AP 列只畫在主角狀態卡）
  void _row;
  chips.push({ ...ap, label: String(unit.ap), pips: null });
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
 * 晶能湧動／晶能狂湧的階（QI-3b，D3）：照 ID 的樣式（同元素架勢）：`crystal_surge`＝第一階，`crystal_surge_<階>`
 * 是之後的階（HC-7 b：原本是前端寫死的對照表）。兩個 ID 在名詞表快照裡（`ui/qi3bStatusCorner.test.ts` 擋改名）。
 */
export const CRYSTAL_SURGE_RE = /^crystal_surge(?:_([2-9]))?$/;

/** 狀態本身的級數（元素架勢 1～5、晶能湧動／狂湧 1／2）；沒有回 null。 */
export function statusTier(id: string): number | null {
  const m = ELEMENT_STANCE_RE.exec(id);
  if (m !== null) return Number(m[2]);
  const surge = CRYSTAL_SURGE_RE.exec(id);
  if (surge === null) return null;
  return surge[1] === undefined ? 1 : Number(surge[1]);
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

/** HUD 的一個層數：`gauge`＝畫成格子計量（KW-3 的四種層數），否則照舊畫 `StackBadge`。 */
export interface HudStack {
  id: string;
  count: number;
  gauge: boolean;
}

/**
 * 主角 HUD 的層數列（KW-3）：大於 0 的層數依 ID 排序；有計量的四種（連擊點、怒氣、專注、氣）在 0 層時，
 * 主角有會累積或消耗它的技能（技能卡的 `stacks`，同說明框「你的技能」）才顯示空格，否則整條不顯示（開發 PM 決定）。
 */
export function hudStacks(unit: UnitView, cards: Readonly<Record<string, SkillCard | undefined>> = {}): HudStack[] {
  const owned = unit.skills ?? [];
  const ids = new Set(Object.keys(unit.stacks).filter((k) => (unit.stacks[k] ?? 0) > 0));
  for (const id of Object.keys(GAUGE_MAX).sort()) {
    if (ids.has(id)) continue;
    const { makes, uses } = stackSkillNames(id, cards, owned);
    if (makes.length + uses.length > 0) ids.add(id);
  }
  return [...ids].sort().map((id) => ({ id, count: unit.stacks[id] ?? 0, gauge: hasGauge(id) }));
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
