// 戰鬥畫面的格子互動（由 BattleScreen 抽出，Phase 3T-7）：滑過（預覽與資訊卡）、點擊（規則在 `battle/tileClick.ts`，
// 這裡執行它回傳的動作）、浮動資訊卡顯示的內容（單位與地形區段、是否收合）。
// 資訊卡的釘住／滑過寬限由 `ui/hoverCard.ts` 的控制器負責（6.5.1：格子資訊卡不能滑進，只能點擊釘住）。

import { useCallback, useState } from "react";
import type { Action, BattleView, OrderSet, Pos, UnitView } from "../../api/types";
import type { ClassifiedActions } from "../../battle/actions";
import { posKey, samePos } from "../../battle/geometry";
import { withOrder, type OrderKind } from "../../battle/orders";
import type { CommandSession } from "../../battle/summonControl";
import type { ActionMode } from "../../battle/targeting";
import type { TelegraphMark } from "../../battle/telegraph";
import { marksTextAt } from "../../battle/telegraph";
import { collapseSections, tileSections, type TileSection } from "../../battle/tileInfo";
import { loadTileCollapse, saveTileCollapse } from "../../battle/tileCardPrefs";
import { decideTileClick } from "../../battle/tileClick";
import type { UnitNames } from "../../battle/units";
import { zoneLinesAt } from "../../battle/zones";
import { type TileCardApi, useTileCard } from "../../ui/useTileCard";

export function unitAt(view: BattleView, tile: Pos | null): UnitView | undefined {
  if (tile === null) return undefined;
  const here = view.units.filter((u) => !u.escaped && !u.dismissed && samePos(u.pos, tile));
  return here.find((u) => !u.downed) ?? here[0];
}

export interface TileInteraction {
  tileCard: TileCardApi;
  /** 滑鼠目前所在的格子（預覽與高亮用）。 */
  hover: Pos | null;
  onTileHover(tile: Pos | null): void;
  onTileClick(tile: Pos, shift: boolean): void;
  /** 浮動資訊卡顯示的格子（寬限期內可能與 `hover` 不同）、卡上的單位與區段。 */
  cardTile: Pos | null;
  hoverUnit: UnitView | null;
  tileCardSections: TileSection[];
  /** 滑過格子的區域與環境預告文字（右側預告欄顯示）。 */
  hoverTexts: string[];
  /** 單位資訊卡是否把地形區段收合（「版面」面板的選項）。 */
  collapseTile: boolean;
  setCollapseTile(on: boolean): void;
}

export interface TileClickContext {
  view: BattleView;
  shown: BattleView;
  hero: UnitView | null;
  canAct: boolean;
  copying: boolean;
  canOrder: boolean;
  orderPick: OrderKind | null;
  command: CommandSession | null;
  setCommand(c: CommandSession | null | ((cur: CommandSession | null) => CommandSession | null)): void;
  mode: ActionMode | null;
  hurlPick: string | null;
  setHurlPick(id: string | null): void;
  classified: ClassifiedActions;
  orders: OrderSet;
  marks: readonly TelegraphMark[];
  liveNames: UnitNames;
  skillNames: Readonly<Record<string, string>>;
  act(a: Action): void;
  decideCopy(pick: Action | null): void;
  issueOrders(orders: OrderSet): void;
  setHint(text: string): void;
}

export function useTileInteraction(c: TileClickContext): TileInteraction {
  const tileCard = useTileCard();
  const [hover, setHover] = useState<Pos | null>(null);
  const [collapseTile, setCollapseTileState] = useState<boolean>(loadTileCollapse);
  const { view, shown, hero, canAct, copying, canOrder, orderPick, command, mode, hurlPick, classified } = c;
  const { act, decideCopy, issueOrders, setCommand, setHurlPick, setHint, orders } = c;

  const onTileClick = useCallback(
    (tile: Pos, shift: boolean) => {
      // 規則在 battle/tileClick.ts（純函式、有表格測試）；這裡只執行它回傳的動作。
      // 資訊卡釘住（3-40，使用者選 C）：沒有動作的格子左鍵點就釘；已釘住時點同一格取消；有動作的點擊照常行動並關掉釘住的卡。
      const pin = tileCard.ctl;
      const result = decideTileClick(
        { shift, pinned: pin.pinned, view, hero, canAct, copying, canOrder, orderPick, command, mode, hurlPick, classified },
        tile,
      );
      switch (result.kind) {
        case "ignore":
          return;
        case "pin":
          pin.pinAt(result.tile);
          return;
        case "command_dest":
          setCommand((cur) => (cur === null ? cur : { ...cur, dest: result.dest }));
          return;
        case "hurl_pick":
          setHurlPick(result.pick);
          return;
        case "hint":
          setHint(result.text);
          return;
        case "order":
          issueOrders(withOrder(orders, result.order));
          return;
        case "act":
        case "submit":
          if (result.dismissPin) pin.dismiss();
          if (result.kind === "submit" && copying) decideCopy(result.action);
          else act(result.action);
          return;
      }
    },
    [
      act,
      canAct,
      command,
      copying,
      decideCopy,
      canOrder,
      classified,
      hero,
      hurlPick,
      issueOrders,
      mode,
      orderPick,
      orders,
      setCommand,
      setHint,
      setHurlPick,
      tileCard,
      view,
    ],
  );

  const onTileHover = useCallback(
    (tile: Pos | null) => {
      tileCard.ctl.setHover(tile);
      setHover((prev) => {
        if (prev === null || tile === null) return tile;
        return posKey(prev) === posKey(tile) ? prev : tile;
      });
    },
    [tileCard],
  );

  // 浮動資訊卡顯示的格子（3-30 起寬限期內可能與滑鼠所在格不同，見 ui/hoverCard.ts）
  const sectionsAt = (tile: Pos | null) =>
    tileSections(shown, tile, c.skillNames, [...zoneLinesAt(shown, tile, c.liveNames), ...marksTextAt(c.marks, tile)]);
  tileCard.ctl.hasContent = (tile) => unitAt(shown, tile) !== undefined || sectionsAt(tile).length > 0;
  const cardTile = tileCard.ctl.visible ? tileCard.ctl.shown : null;
  const hoverTexts = [...zoneLinesAt(shown, hover, c.liveNames), ...marksTextAt(c.marks, hover)];
  const hoverUnit = unitAt(shown, cardTile) ?? null;
  const fullTileSections = sectionsAt(cardTile);
  const tileCardSections = hoverUnit !== null && collapseTile ? collapseSections(fullTileSections) : fullTileSections;
  const setCollapseTile = (on: boolean) => {
    setCollapseTileState(on);
    saveTileCollapse(on);
  };

  return {
    tileCard,
    hover,
    onTileHover,
    onTileClick,
    cardTile,
    hoverUnit,
    tileCardSections,
    hoverTexts,
    collapseTile,
    setCollapseTile,
  };
}
