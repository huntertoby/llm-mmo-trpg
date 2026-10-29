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

import type { Action, BattleView, Pos, TacticalOrder, UnitView } from "../api/types";
import { actionForClick, type ClassifiedActions } from "./actions";
import { samePos } from "./geometry";
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
  | { kind: "hint"; text: string };

const IGNORE: TileClickResult = { kind: "ignore" };

/** 指揮召喚物時的點擊：選好終點後點可打到的敵人 ＝ 移動並攻擊；否則點藍格選終點。 */
function commandClick(s: TileClickState, hero: UnitView, command: CommandSession, tile: Pos): TileClickResult {
  if (command.dest !== null) {
    const chosen = optionAt(command.options, command.dest);
    const foe = chosen?.targets.find((id) =>
      samePos(s.view.units.find((u) => u.id === id)?.pos ?? { x: -1, y: -1 }, tile),
    );
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
  if (action !== null) return { kind: "submit", action, dismissPin: s.pinned };
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
  if (s.mode !== null) return modeClick(s, s.hero, s.mode, tile);
  const action = actionForClick(s.classified, s.view, tile);
  return action !== null ? { kind: "act", action, dismissPin: s.pinned } : { kind: "pin", tile };
}
