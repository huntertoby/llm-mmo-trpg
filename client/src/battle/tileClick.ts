// 點擊戰場格子要做什麼（由 `BattleScreen` 的 `onTileClick` 抽出的純函式，Phase 3T-7）。
//
// 輸入是「點擊當下的畫面狀態」與被點的格子，輸出是一個「要做的事」（判別聯集），由呼叫端依結果執行
// （送出動作、釘住資訊卡、提示文字……）。不碰 React、不碰 DOM，所以能用表格測試逐條驗證點擊規則：
//
// 1. Shift＋左鍵：任何格子都釘住資訊卡（3-40，使用者選 C）。
// 2. 指揮召喚物中（3-33c）：點藍格選終點；選好終點後點紅框的敵人 ＝ 移動並攻擊。
// 3. 等待隊友指令的目標（orderPick）：點目標送出指令。
// 4. 不是自己的回合（也不是複製／複合技能第二段）：點任何格子都釘住。
// 5. 有選取的模式：撥開要用面板選方向；投擲分兩段（落點優先，再點別的物件改選，點同一個取消）；
//    點得到動作就行動（並關掉釘住的卡）；被擋住的推擊顯示原因；其餘釘住。
// 6. 沒有選取模式：點敵人＝普攻、點藍格＝移動；其餘（沒有動作的格子）釘住。
// 7. 頭目部位（PB-1c，05 5.12.3、R1、R6）：要送出的普攻或單體技能的目標有部位（伺服器給了 `part_options`）時，
//    不直接送出，改成打開選部位小選單（`part_menu`）。選單開著時（以按下滑鼠那一刻為準）再點同一個頭目＝打本體；
//    點別的地方只關選單（選單在按下時已經關了），不做別的事。沒有部位的單位所有分支和改前相同。
// 8. 巨型頭目（GB-4a，T12）：不跳選單，由點的那一格推出部位（`footprint.giantAim`）；打不到的部位格只提示原因。

import type { Action, BattleView, PartActionOptions, PartOption, Pos, TacticalOrder, UnitView } from "../api/types";
import { actionForClick, type ClassifiedActions } from "./actions";
import { giantAim, isGiant, occupies, standingAtTile, type GiantAim } from "./footprint";
import type { OrderKind } from "./orders";
import { orderFromTile } from "./orders";
import { blockedPushAt } from "./pushReasons";
import { commandAction, optionAt, type CommandSession } from "./summonControl";
import { actionAtTile, hurlObjectAt, isHurlMode, type ActionMode } from "./targeting";

/** 點擊當下的畫面狀態（只列規則會看的欄位）。 */
export interface TileClickState {
  /** 是否按著 Shift。 */
  shift: boolean;
  /** 資訊卡目前是否釘住。 */
  pinned: boolean;
  view: BattleView;
  hero: UnitView | null;
  /** 輪到自己且沒有在播放或送出中。 */
  canAct: boolean;
  /** 複製技能或複合技能第二段暫停中（選目標）。 */
  copying: boolean;
  /** 可以下隊友指令。 */
  canOrder: boolean;
  orderPick: OrderKind | null;
  command: CommandSession | null;
  mode: ActionMode | null;
  hurlPick: string | null;
  classified: ClassifiedActions;
  /** 伺服器的 `part_options`（PB-1c）：目標有部位的普攻與單體技能；省略或 `null`＝沒有。 */
  partActions?: readonly PartActionOptions[] | null;
  /** 按下滑鼠那一刻開著的選部位小選單的目標（PB-1c）；沒開為 `null`。 */
  partMenuTarget?: string | null;
}

/** 點擊要做的事。 */
export type TileClickResult =
  /** 什麼都不做。 */
  | { kind: "ignore" }
  /** 釘住（或取消釘住同一格的）資訊卡。 */
  | { kind: "pin"; tile: Pos }
  /** 指揮召喚物：記下選的終點。 */
  | { kind: "command_dest"; dest: Pos }
  /** 送出動作（一般送出，不經複製暫停）；`dismissPin` ＝ 同時關掉釘住的卡。 */
  | { kind: "act"; action: Action; dismissPin: boolean }
  /** 送出動作；複製／複合技能第二段暫停中改走「決定」，否則一般送出。 */
  | { kind: "submit"; action: Action; dismissPin: boolean }
  /** 下隊友指令。 */
  | { kind: "order"; order: TacticalOrder }
  /** 投擲第一段：選（或取消）舉起的物件。 */
  | { kind: "hurl_pick"; pick: string | null }
  /** 顯示一則提示（例如推不動的原因）。 */
  | { kind: "hint"; text: string }
  /**
   * 打開選部位小選單（PB-1c）：`action` 是不帶部位的動作（＝打本體）；選了部位就在它上面加 `target_part` 送出。
   * `submit`：照原本會走 `submit`（有選取模式）還是 `act`；`dismissPin` 照原本的值。
   */
  | { kind: "part_menu"; targetId: string; tile: Pos; action: Action; options: readonly PartOption[]; submit: boolean; dismissPin: boolean };

const IGNORE: TileClickResult = { kind: "ignore" };

/** 動作的部位選項（同一種動作、同一招、同一個目標）；目標沒有部位或不是普攻、技能時為 `null`。 */
export function partOptionsFor(list: readonly PartActionOptions[] | null | undefined, action: Action): PartActionOptions | null {
  if (list == null || list.length === 0) return null;
  if (action.type !== "attack" && action.type !== "use_skill") return null;
  const target = action.target_id ?? null;
  if (target === null) return null;
  const skill = action.type === "use_skill" ? action.skill_id : null;
  return list.find((o) => o.type === action.type && (o.skill_id ?? null) === skill && o.target_id === target) ?? null;
}

/**
 * 要送出的動作碰到有部位的目標（PB-1c）：選單開著時（按下時）再點同一個頭目＝本體（照原本送出），
 * 否則打開選部位小選單。目標沒有部位時照原本的結果。
 */
function withPartMenu(s: TileClickState, tile: Pos, sent: Extract<TileClickResult, { kind: "act" | "submit" }>): TileClickResult {
  const found = partOptionsFor(s.partActions, sent.action);
  if (found === null) return sent;
  const boss = s.view.units.find((u) => u.id === found.target_id);
  if (boss !== undefined && isGiant(boss)) return giantClick(boss, found.options, tile, sent);
  if (s.partMenuTarget === found.target_id) return sent;
  return { kind: "part_menu", targetId: found.target_id, tile, action: sent.action, options: found.options, submit: sent.kind === "submit", dismissPin: sent.dismissPin };
}

/**
 * 點巨型頭目的某一格（GB-4a，T12）：不跳選單，由那一格推出部位——打得到就帶 `target_part` 照原本送出；
 * 前殼、已破、還沒露出的部位格＝本體；打不到的部位格不送出，提示原因。
 */
function giantClick(boss: UnitView, options: readonly PartOption[], tile: Pos, sent: Extract<TileClickResult, { kind: "act" | "submit" }>): TileClickResult {
  const aim = giantAim(boss, options, sent.action, tile);
  if (aim.kind === "blocked") return { kind: "hint", text: `打不到${aim.part.name_zh}：${aim.reason}` };
  return { ...sent, action: aim.action };
}

/**
 * `action`（不帶部位）打的是巨型頭目、而且 `tile` 是它的佔格時，這一格會打到什麼（GB-4a）；其他情況 `null`。
 * 滑過預覽與資訊卡用，和點擊同一套判斷（`giantAim`）。
 */
export function giantAimAt(view: BattleView, list: readonly PartActionOptions[] | null | undefined, action: Action | null, tile: Pos | null): GiantAim | null {
  if (action === null || tile === null) return null;
  const found = partOptionsFor(list, action);
  if (found === null) return null;
  const boss = view.units.find((u) => u.id === found.target_id);
  if (boss === undefined || !isGiant(boss) || !occupies(boss, tile)) return null;
  return giantAim(boss, found.options, action, tile);
}

/** 滑過格子時，點下去會送出的動作（不帶部位）：有選取模式照模式，否則點敵人＝普攻。不能行動時 `null`。 */
export function hoverActionAt(
  s: Pick<TileClickState, "view" | "hero" | "canAct" | "copying" | "command" | "mode" | "hurlPick" | "classified">,
  tile: Pos | null,
): Action | null {
  if (!(s.canAct || s.copying) || tile === null || s.hero === null || s.command !== null) return null;
  if (s.mode !== null) return actionAtTile(s.mode, s.view, s.hero, tile, s.hurlPick);
  const target = standingAtTile(s.view.units, tile);
  return target === undefined ? null : (s.classified.attacks.get(target.id) ?? null);
}

/** 指揮召喚物時的點擊：選好終點後點可打到的敵人 ＝ 移動並攻擊；否則點藍格選終點。 */
function commandClick(s: TileClickState, hero: UnitView, command: CommandSession, tile: Pos): TileClickResult {
  if (command.dest !== null) {
    const chosen = optionAt(command.options, command.dest);
    const foe = chosen?.targets.find((id) => {
      const u = s.view.units.find((x) => x.id === id);
      return u !== undefined && occupies(u, tile);
    });
    if (chosen !== undefined && foe !== undefined) {
      const action = commandAction(hero.id, command.summonId, chosen, foe);
      return action === null ? IGNORE : { kind: "act", action, dismissPin: false };
    }
  }
  return optionAt(command.options, tile) !== undefined ? { kind: "command_dest", dest: tile } : IGNORE;
}

/** 有選取模式時的點擊。 */
function modeClick(s: TileClickState, hero: UnitView, mode: ActionMode, tile: Pos): TileClickResult {
  if (mode.kind === "shove_aside") return IGNORE; // 撥開要用面板選方向
  if (isHurlMode(mode)) {
    // 投擲物件：第 1 段選物件、第 2 段選落點（落點優先；再點別的物件改選，點同一個取消）
    const landing = actionAtTile(mode, s.view, hero, tile, s.hurlPick);
    if (landing !== null) return { kind: "submit", action: landing, dismissPin: false };
    const object = hurlObjectAt(mode, s.view, tile);
    return object === null ? IGNORE : { kind: "hurl_pick", pick: object === s.hurlPick ? null : object };
  }
  const action = actionAtTile(mode, s.view, hero, tile);
  if (action !== null) return withPartMenu(s, tile, { kind: "submit", action, dismissPin: s.pinned });
  const why = blockedPushAt(mode, s.view, tile);
  return why !== null ? { kind: "hint", text: why } : { kind: "pin", tile };
}

/** 決定點擊要做的事（純函式）。 */
export function decideTileClick(s: TileClickState, tile: Pos): TileClickResult {
  if (s.shift) return { kind: "pin", tile };
  if (s.command !== null && s.canAct && s.hero !== null) return commandClick(s, s.hero, s.command, tile);
  if (s.orderPick !== null && s.canOrder) {
    const order = orderFromTile(s.orderPick, s.view, tile);
    return order === null ? IGNORE : { kind: "order", order };
  }
  if (!((s.canAct || s.copying) && s.hero !== null)) return { kind: "pin", tile };
  const result = s.mode !== null ? modeClick(s, s.hero, s.mode, tile) : plainClick(s, tile);
  // PB-1c：選部位小選單開著時按下滑鼠，選單先關；這一下點的不是同一個頭目就只關選單
  if (s.partMenuTarget != null && result.kind !== "part_menu" && !reclicksMenuTarget(s, result)) return IGNORE;
  return result;
}

function plainClick(s: TileClickState, tile: Pos): TileClickResult {
  const action = actionForClick(s.classified, s.view, tile);
  return action !== null ? withPartMenu(s, tile, { kind: "act", action, dismissPin: s.pinned }) : { kind: "pin", tile };
}

/** 選單開著時再點同一個頭目（送出的是打本體的動作）。 */
function reclicksMenuTarget(s: TileClickState, result: TileClickResult): boolean {
  if (result.kind !== "act" && result.kind !== "submit") return false;
  return partOptionsFor(s.partActions, result.action)?.target_id === s.partMenuTarget;
}
