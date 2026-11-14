// 戰鬥畫面的格子互動（由 BattleScreen 抽出，Phase 3T-7）：滑過（預覽與資訊卡）、點擊（規則在 `battle/tileClick.ts`，
// 這裡執行它回傳的動作）、浮動資訊卡顯示的內容（單位與地形區段、是否收合）。
// 資訊卡的釘住／滑過寬限由 `ui/hoverCard.ts` 的控制器負責（6.5.1：格子資訊卡不能滑進，只能點擊釘住）。
// PB-1c：點有部位的頭目時打開選部位小選單（`partMenu`）；按下滑鼠那一刻（`onBoardPointerDown`，捕獲階段，比選單的「點外面關」早）
// 記下開著的選單目標，交給點擊規則判斷「再點同一個頭目＝本體」。

import { useCallback, useEffect, useRef, useState } from "react";
import type { Action, BattleView, OrderSet, PartActionOptions, Pos, UnitView } from "../../api/types";
import type { ClassifiedActions } from "../../battle/actions";
import { giantAimLine, unitAtTile } from "../../battle/footprint";
import { posKey } from "../../battle/geometry";
import { withOrder, type OrderKind } from "../../battle/orders";
import type { CommandSession } from "../../battle/summonControl";
import type { ActionMode } from "../../battle/targeting";
import type { TelegraphMark } from "../../battle/telegraph";
import { marksTextAt } from "../../battle/telegraph";
import { collapseSections, tileSections, type TileSection } from "../../battle/tileInfo";
import { loadTileCollapse, saveTileCollapse } from "../../battle/tileCardPrefs";
import { decideTileClick, giantAimAt, hoverActionAt } from "../../battle/tileClick";
import type { UnitNames } from "../../battle/units";
import { zoneLinesAt } from "../../battle/zones";
import { type TileCardApi, useTileCard } from "../../ui/useTileCard";
import { withTargetPart, type PartMenuState } from "../../ui/PartMenu";

export function unitAt(view: BattleView, tile: Pos | null): UnitView | undefined {
  return unitAtTile(view.units, tile);
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
  /** 開著的選部位小選單（PB-1c）；沒開為 `null`。 */
  partMenu: PartMenuState | null;
  closePartMenu(): void;
  /** 選單選了（`null`＝本體）：照原本的送出方式送出。 */
  pickPart(part: string | null): void;
  /** 掛在 `.battle-board` 的 `onPointerDownCapture`。 */
  onBoardPointerDown(): void;
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
  /** 伺服器的 `part_options`（PB-1c）。 */
  partActions?: readonly PartActionOptions[] | null;
}

export function useTileInteraction(c: TileClickContext): TileInteraction {
  const tileCard = useTileCard();
  const [hover, setHover] = useState<Pos | null>(null);
  const [collapseTile, setCollapseTileState] = useState<boolean>(loadTileCollapse);
  const { view, shown, hero, canAct, copying, canOrder, orderPick, command, mode, hurlPick, classified } = c;
  const { act, decideCopy, issueOrders, setCommand, setHurlPick, setHint, orders } = c;
  const partActions = c.partActions ?? null;
  const [partMenu, setPartMenu] = useState<PartMenuState | null>(null);
  const partMenuRef = useRef<PartMenuState | null>(null);
  partMenuRef.current = partMenu;
  /** 按下滑鼠那一刻開著的選單目標（PB-1c）。 */
  const menuAtDown = useRef<string | null>(null);
  const closePartMenu = useCallback(() => setPartMenu(null), []);
  // 回應、選取模式換了（換人、送出、取消瞄準）就關掉選單
  useEffect(() => setPartMenu(null), [view, mode, canAct]);
  const onBoardPointerDown = useCallback(() => {
    menuAtDown.current = partMenuRef.current?.targetId ?? null;
  }, []);
  const send = useCallback(
    (action: Action, submit: boolean) => {
      if (submit && copying) decideCopy(action);
      else act(action);
    },
    [act, copying, decideCopy],
  );
  const pickPart = useCallback(
    (part: string | null) => {
      const m = partMenuRef.current;
      if (m === null) return;
      setPartMenu(null);
      if (m.dismissPin) tileCard.ctl.dismiss();
      send(withTargetPart(m.action, part), m.submit);
    },
    [send, tileCard],
  );

  const onTileClick = useCallback(
    (tile: Pos, shift: boolean) => {
      // 規則在 battle/tileClick.ts（純函式、有表格測試）；這裡只執行它回傳的動作。
      // 資訊卡釘住（3-40，使用者選 C）：沒有動作的格子左鍵點就釘；已釘住時點同一格取消；有動作的點擊照常行動並關掉釘住的卡。
      const pin = tileCard.ctl;
      const partMenuTarget = menuAtDown.current;
      menuAtDown.current = null;
      const result = decideTileClick(
        { shift, pinned: pin.pinned, view, hero, canAct, copying, canOrder, orderPick, command, mode, hurlPick, classified, partActions, partMenuTarget },
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
        case "part_menu":
          setPartMenu({ targetId: result.targetId, tile: result.tile, action: result.action, options: result.options, submit: result.submit, dismissPin: result.dismissPin });
          return;
        case "act":
        case "submit":
          setPartMenu(null);
          if (result.dismissPin) pin.dismiss();
          send(result.action, result.kind === "submit");
          return;
      }
    },
    [
      canAct,
      command,
      copying,
      partActions,
      send,
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
  const baseSections = hoverUnit !== null && collapseTile ? collapseSections(fullTileSections) : fullTileSections;
  // GB-4a：滑過巨型頭目的格子時，資訊卡多一行「這一格會打到什麼」（打不到的部位寫原因；收起時也留著）
  const cardAction = hoverActionAt({ view, hero, canAct, copying, command, mode, hurlPick, classified }, cardTile);
  const cardAim = giantAimAt(view, partActions, cardAction, cardTile);
  const tileCardSections: TileSection[] =
    cardAim === null ? baseSections : [...baseSections, { kind: "part", title: giantAimLine(cardAim), lines: [] }];
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
    partMenu,
    closePartMenu,
    pickPart,
    onBoardPointerDown,
  };
}
