// 戰鬥畫面（6A-4e 起是 HUD 版面 A 的戰鬥版；docs/archive/art/戰鬥D版樣張.md 第 5 節）：戰場用滿整個畫面，HUD 疊在四周——
// 左上主角卡（HP、法力、耐力三條；下面接選取面板）、上方中央行動順序、右上地名＋回合＋天氣＋勝利條件與工具鈕
// （環境預告、反應設定、隊友指令、圖例、版面、存檔、離開）、底部技能列與回合操作、左下紀錄浮動提示。
// 地圖照可用區域（只扣掉底部列，上、左、右鋪滿；6A-4g、6C-8）自動填滿，HUD 塊底下有單位或可點格子時變半透明（`useHudFade`）；字母標記只在滑過單位與行動順序列上顯示。
// 每次送出動作或決定：鎖住操作 → 收到回應 → 先畫 `initial_view`，再依 `steps` 一步一步播放
// （標示行動者 → 移動動畫 → 該步的 `view` → 紀錄 → 停頓）→ 最後以 `res.view` 為準。
//
// Phase 3T-7：主元件只負責組裝；狀態與邏輯在 `screens/battle/` 的自訂 hook，點擊規則在 `battle/tileClick.ts`：
//   usePlayback（播放與送出）、useBattleData（派生資料）、useSelection（選取狀態）、useBattleActions（送出動作）、
//   useSelectionCommands（選取操作）、useBattleKeys（鍵盤）、useTileInteraction（格子互動與資訊卡）、
//   useHighlights（預覽與高亮）、useBoardViewport（版面與縮放）；子元件 ZoomControls、BattleBottomBar、BattleDialogs。
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { BattleResponse, SkillCard } from "../api/types";
import { withInfusion } from "../battle/infusion";
import { cardPlacement } from "../battle/stageLayout";
import { BattleBanner } from "../ui/BattleBanner";
import { orderButton, withOrder } from "../battle/orders";
import { togglePopup, type TopPopup } from "../battle/skillTray";
import { BattleCanvas } from "../ui/BattleCanvas";
import { BattleLogDock } from "../ui/BattleLogDock";
import { BattleStatusBox } from "../ui/BattleStatusBox";
import { BattleTopBar } from "../ui/BattleTopBar";
import { ModePanel } from "../ui/ActionPanel";
import type { EndSummary } from "../ui/EndPanel";
import { ErrorBanner } from "../ui/ErrorBanner";
import { HoverFloat } from "../ui/HoverFloat";
import { Hud } from "../ui/Hud";
import { NoticeBanner } from "../ui/NoticeBanner";
import { BattleHints, type BattleHintSet } from "../ui/BattleHints";
import { PinnedUnitDock } from "../ui/PinnedUnitDock";
import { PartMenu } from "../ui/PartMenu";
import { phaseNotices } from "../battle/bossPhase";
import { hudInsetStyle } from "../battle/hudLayout";
import { useElementSize } from "../ui/useLayout";
import { SummonPanel } from "../ui/SummonPanel";
import { TelegraphPanel } from "../ui/TelegraphPanel";
import { TileCard } from "../ui/TileCard";
import { PracticeBar, TurnBar } from "../ui/TurnBar";
import { practiceRoundLines } from "../battle/logGroups";
import { UnitInfo } from "../ui/UnitInfo";
import { pinnedUnitOf, togglePin } from "../ui/statusCard";
import { BattleBottomBar } from "./battle/BattleBottomBar";
import { BattleDialogs } from "./battle/BattleDialogs";
import { battleTools } from "./battle/battleTools";
import { useBattleActions } from "./battle/useBattleActions";
import { useBattleData } from "./battle/useBattleData";
import { useBattleAmbience, useBurnLoop } from "../audio/scene";
import { useBattleKeys } from "./battle/useBattleKeys";
import { useBoardViewport } from "./battle/useBoardViewport";
import { useHighlights } from "./battle/useHighlights";
import { useHudFade } from "./battle/useHudFade";
import { useLogRoom } from "./battle/useLogRoom";
import { errorText, usePlayback } from "./battle/usePlayback";
import { useSelection } from "./battle/useSelection";
import { useSelectionCommands } from "./battle/useSelectionCommands";
import { useTileInteraction } from "./battle/useTileInteraction";
import { ZoomControls } from "./battle/ZoomControls";
import { useRegionTheme } from "../ui/regionTheme";

interface Props {
  initial: BattleResponse;
  onExit(): void;
  /** 有值時顯示「離開」按鈕（可隨時離開），結束面板的主按鈕也用這個文字；省略為一般戰鬥。 */
  exitLabel?: string;
  /** 從一輪（roguelite）進入時：顯示「存檔」按鈕與主角倒下提示（Phase 3-5c-1）。 */
  runMode?: RunMode;
  /** 開場說明（大世界 5A-7：先手、開場狀態、增援）；開場橫幅下顯示，另在畫面上留一則可關的提示。 */
  openingNotes?: readonly string[];
  /** 結束面板取代「勝利！／敗北……」的中性文字（循環賽重播「某某 勝」，5F-4b）。 */
  endTitle?: string;
  /** 右上顯示的地名（6A-4e：大世界的戰鬥由世界畫面帶入地點名）；省略用戰場地圖名（一輪照舊）。 */
  placeName?: string | null;
  /** 戰鬥結束（播放完）時呼叫一次（6F-1：大世界去取戰後結算）。 */
  onEnded?(): void;
  /** 結束面板的戰後結算（6F-1）；`null` ＝ 結算中，省略不顯示。 */
  endSummary?: EndSummary | null;
  /** 戰鬥短提示（6F-2，#99；大世界戰鬥才有）。 */
  hints?: BattleHintSet;
  /** 主角的出身區（QK-2b：主角卡 Q 版頭像的框色）；省略＝傭兵金。 */
  heroOrigin?: string | null;
}

export interface RunMode {
  /** 存檔，回傳要顯示的訊息。 */
  onSave(): Promise<string>;
}

export function BattleScreen({ initial, onExit, exitLabel, runMode, openingNotes, endTitle, placeName, onEnded, endSummary, hints, heroOrigin = null }: Props) {
  const battleId = initial.battle_id;
  const heroId = initial.hero_id;
  const cardsRef = useRef<Readonly<Record<string, SkillCard | undefined>>>({});
  const resetSelectionRef = useRef<() => void>(() => undefined);
  const pb = usePlayback(initial, cardsRef, resetSelectionRef);
  const { response, shown, busy } = pb;
  useBattleAmbience(shown); // AU-3：戰場的環境音（區域、天氣、岩漿；優先於大世界）
  useBurnLoop(shown); // AU-3：有人在燃燒時全場一條劈啪循環
  useRegionTheme(shown.region); // RT-1：戰鬥是開戰地點的區域（沒有＝hub）
  const data = useBattleData(battleId, heroId, response, shown, pb.acting, busy);
  const { view, hero, cards, copying } = data;
  cardsRef.current = cards;
  const sel = useSelection(response, data.canAct, copying, data.copyPick, data.modes);
  resetSelectionRef.current = sel.resetOnRun;
  const { mode } = sel;
  /** 中性提示（例如灰掉技能的原因），幾秒後自動消失。 */
  const [hint, setHint] = useState<string | null>(null);
  const closeHint = useCallback(() => setHint(null), []);
  // Boss 進入新階段（Phase 5F-2）：播放完這次推進後，把轉換的紀錄文字留在提示列 15 秒
  const [phaseNotice, setPhaseNotice] = useState<string | null>(null);
  const closePhaseNotice = useCallback(() => setPhaseNotice(null), []);
  useEffect(() => {
    const notices = phaseNotices(response);
    if (notices.length > 0) setPhaseNotice(notices.join("　"));
  }, [response]);
  // 大世界開場說明（5A-7）：橫幅消失後仍留一則提示，玩家自己關或 15 秒後消失
  // 6F-3（巡檢 bug 10）：開場說明只在第 1 輪跳出（重新載入時已經第 2 輪以上，「敵方先手：第 1 輪…」不再跳出）
  const [opening, setOpening] = useState<string | null>(() =>
    (openingNotes ?? []).length > 0 && initial.view.round <= 1 ? (openingNotes ?? []).join("　") : null,
  );
  const closeOpening = useCallback(() => setOpening(null), []);
  // 戰鬥短提示（6F-2）看的事件：這次回應的每一步
  const hintEvents = useMemo(() => response.steps.flatMap((s) => s.events), [response]);
  const [saveNote, setSaveNote] = useState<string | null>(null);
  /** 頂端列開著的彈出面板（同時只開一個）。 */
  const [popup, setPopup] = useState<TopPopup | null>(null);
  /** 釘選的單位小卡（6A-2）：跟著單位（不是格子），敵人回合也一直顯示在戰場右上。 */
  const [pinnedUnit, setPinnedUnit] = useState<string | null>(null);
  const togglePinnedUnit = useCallback((id: string) => setPinnedUnit((cur) => togglePin(cur, id)), []);

  const actions = useBattleActions(
    battleId,
    heroId,
    hero,
    response,
    cards,
    cardsRef,
    pb.run,
    data.canAct,
    data.followPaused,
    sel.setOrderPick,
  );
  const cmds = useSelectionCommands(
    battleId,
    heroId,
    view,
    response.orders,
    data.modes,
    sel,
    actions.act,
    actions.issueOrders,
    pb.setError,
  );
  const { setInfusionPick } = actions;
  const closeInfusion = useCallback(() => setInfusionPick(null), [setInfusionPick]);
  useBattleKeys(actions.infusionPick !== null, closeInfusion, copying, actions.decideCopy, cmds.cancel);

  const tiles = useTileInteraction({
    view,
    shown,
    hero,
    canAct: data.canAct,
    copying,
    canOrder: data.canOrder,
    orderPick: sel.orderPick,
    command: sel.command,
    setCommand: sel.setCommand,
    mode,
    hurlPick: sel.hurlPick,
    setHurlPick: sel.setHurlPick,
    classified: data.classified,
    orders: response.orders,
    marks: data.marks,
    liveNames: data.liveNames,
    skillNames: data.skillNames,
    act: actions.act,
    decideCopy: actions.decideCopy,
    issueOrders: actions.issueOrders,
    setHint,
    partActions: response.part_options ?? null,
  });
  const hl = useHighlights({
    battleId,
    heroId,
    response,
    view,
    shown,
    hero,
    canAct: data.canAct,
    copying,
    canOrder: data.canOrder,
    classified: data.classified,
    mode,
    hurlPick: sel.hurlPick,
    command: sel.command,
    infuse: sel.infuse,
    orderPick: sel.orderPick,
    panelPreview: sel.panelPreview,
    hover: tiles.hover,
    marks: data.marks,
    focusTile: data.focusTile,
    model: data.model,
    cards,
  });
  const board = useBoardViewport(data.model);
  const boardRef = useRef<HTMLDivElement>(null);
  /** 底部列（技能列＋回合操作）的高度：地圖可用區域、左下紀錄、縮放鈕都讓開它。 */
  const bottomRef = useRef<HTMLDivElement>(null);
  const bottomSize = useElementSize(bottomRef);
  const { layout, narrow, collapsed, scale } = board;

  /** 浮動資訊卡：只在滑過單位時出現（取代固定的單位資訊欄，Phase 3-8）。 */
  const shownHero = shown.units.find((u) => u.id === heroId) ?? null;
  const ended = (response.awaiting === "ended" || response.awaiting === "stalled") && !busy;
  const endedRef = useRef(false);
  useEffect(() => {
    if (!ended || endedRef.current) return;
    endedRef.current = true;
    onEnded?.();
  }, [ended, onEnded]);

  async function saveRun() {
    if (runMode === undefined) return;
    try {
      setSaveNote(await runMode.onSave());
    } catch (e) {
      setSaveNote(null);
      pb.setError(errorText(e));
    }
  }

  const tools = battleTools({
    hero,
    heroId,
    canAct: data.canAct,
    canOrder: data.canOrder,
    autoQueue: actions.autoQueue,
    onSetReaction: actions.setReaction,
    orders: response.orders,
    ordersIgnored: response.orders_ignored,
    liveNames: data.liveNames,
    orderPick: sel.orderPick,
    onPickOrder: cmds.pickOrder,
    onCancelOrderPick: () => sel.setOrderPick(null),
    issueOrders: actions.issueOrders,
    legend: hl.legend,
    layout,
    scale,
    onLayoutChange: board.patchLayout,
    onLayoutReset: board.resetLayout,
    shake: pb.shake,
    onShake: pb.setShake,
    collapseTile: tiles.collapseTile,
    onCollapseTile: tiles.setCollapseTile,
  });

  // 選取時戰鬥紀錄縮短讓開選取面板（6A-4c）
  const selecting = mode !== null || (sel.orderPick !== null && data.canOrder);
  const logRoomPx = useLogRoom(boardRef, selecting, `${mode?.key ?? ""}|${sel.hurlPick ?? ""}|${sel.orderPick ?? ""}`);

  const { cardTile, hoverUnit, tileCardSections } = tiles;
  // PB-1c：選部位小選單的頭目（用目前的戰場）
  const partMenuBoss = tiles.partMenu === null ? null : (view.units.find((u) => u.id === tiles.partMenu?.targetId) ?? null);
  // 選移動時滑過空格、畫出路徑提示時不出格子資訊卡（會蓋住路徑與小牌；地表的效果已寫在小牌上）
  const pathShown = (hl.highlights.path?.segments.length ?? 0) > 0 || (hl.highlights.path?.missEnd ?? null) !== null;
  const dockUnit = pinnedUnitOf(shown, pinnedUnit);
  const telegraphOpen = !collapsed;
  // 6A-4g：地圖鋪滿、HUD 疊在上面；HUD 塊底下有單位或可點的格子時那一塊變半透明（滑上去恢復）
  const hudFaded = useHudFade(boardRef, board.scrollRef, data.model, hl.highlights);
  // PR-2b（#147 測試模式，`BattleView.practice`）：工坊靶場的戰鬥。實戰一律走原本的分支
  const practice = shown.practice;
  const logLines = useMemo(() => practiceRoundLines(pb.lines, practice), [pb.lines, practice]);
  return (
    <div className={`battle-screen hud-a${narrow ? " narrow" : ""}`} style={hudInsetStyle(bottomSize?.height ?? null)}>
      <div className="battle-board" ref={boardRef} data-hud-faded={hudFaded} onPointerDownCapture={tiles.onBoardPointerDown}>
        <div
          className={`board-scroll${board.panning ? " panning" : ""}`}
          ref={board.scrollRef}
          style={board.insets.left + board.insets.right + board.insets.top > 0 ? { paddingLeft: board.insets.left, paddingRight: board.insets.right, paddingTop: board.insets.top } : undefined}
          {...board.panHandlers}
        >
          <BattleCanvas
            model={data.model}
            highlights={hl.highlights}
            flameOn={hl.flameOn}
            scale={scale}
            onTileClick={tiles.onTileClick}
            onTileHover={tiles.onTileHover}
            onCancel={cmds.cancel}
            rendererRef={pb.rendererRef}
            menuOpen={(response.part_options ?? null) === null ? undefined : partMenuBoss !== null}
          >
            {cardTile !== null && tiles.partMenu === null && (hoverUnit !== null || (tileCardSections.length > 0 && !pathShown)) && (
              <HoverFloat placement={cardPlacement(cardTile, data.model, scale)} card={tiles.tileCard}>
                {hoverUnit !== null && (
                  <UnitInfo
                    unit={hoverUnit}
                    names={data.names}
                    heroId={heroId}
                    skills={data.skillNames}
                    cards={cards}
                    view={shown}
                    pinned={hoverUnit.id === pinnedUnit}
                    onTogglePin={() => togglePinnedUnit(hoverUnit.id)}
                  />
                )}
                <TileCard sections={tileCardSections} />
              </HoverFloat>
            )}
          </BattleCanvas>
        </div>
        {tiles.partMenu !== null && partMenuBoss !== null && (
          <PartMenu
            key={`${tiles.partMenu.targetId}|${tiles.partMenu.tile.x},${tiles.partMenu.tile.y}`}
            menu={tiles.partMenu}
            boss={partMenuBoss}
            model={data.model}
            scale={scale}
            boardRef={boardRef}
            onPick={tiles.pickPart}
            onClose={tiles.closePartMenu}
            onPreview={sel.setPanelPreview}
          />
        )}
        <ZoomControls
          zoom={layout.zoom}
          scale={scale}
          onZoomStep={board.zoomStep}
          onFill={() => board.patchLayout({ zoom: null })}
        />
        {pb.banner && <BattleBanner practice={practice} objective={shown.objective} notes={openingNotes} />}
        <div className="board-toasts">
          <ErrorBanner message={pb.error} onClose={() => pb.setError(null)} />
          <NoticeBanner message={hint} onClose={closeHint} />
          <NoticeBanner message={saveNote} onClose={() => setSaveNote(null)} autoCloseMs={6000} />
          <NoticeBanner message={phaseNotice} onClose={closePhaseNotice} autoCloseMs={15000} />
          <NoticeBanner message={opening} onClose={closeOpening} autoCloseMs={15000} />
          {hints !== undefined && hints.hints.length > 0 && <BattleHints set={hints} view={shown} heroId={heroId} events={hintEvents} />}
          {runMode !== undefined && shownHero?.downed === true && (
            <div className="hero-downed-notice" role="status">
              主角倒下，隊友繼續作戰
            </div>
          )}
        </div>
        <BattleLogDock lines={logLines} onHover={hl.setLogHover} room={logRoomPx} />
        {/* 版面 A 戰鬥版（6A-4e）：左上主角卡（下面接選取面板）、上方中央行動順序、右上戰況與工具鈕、底部技能列 */}
        <div className="bhud-left">
          <div className="bhud-hero">
            <Hud view={shown} hero={shownHero} skills={data.skillNames} cards={cards} heroOrigin={heroOrigin} />
          </div>
          <ModePanel
            enabled={data.canAct || copying}
            mode={mode}
            hurlPick={sel.hurlPick}
            onHurlReset={() => sel.setHurlPick(null)}
            preview={hl.preview}
            view={view}
            interactOptions={response.interact_options}
            names={data.liveNames}
            legend={hl.legend}
            orderHint={sel.orderPick !== null && data.canOrder ? orderButton(sel.orderPick).hint : null}
            onProtectHero={
              sel.orderPick === "protect" && data.canOrder
                ? () => actions.issueOrders(withOrder(response.orders, { kind: "protect", ward: heroId }))
                : null
            }
            cancellable={!copying}
            onCancel={cmds.cancel}
            onAction={copying ? actions.decideCopy : actions.act}
            onPreviewAction={sel.setPanelPreview}
          />
        </div>
        <div className="bhud-top">
          {/* PR-2b（#147）：測試模式不放行動順序，改放提示條 */}
          {practice ? <PracticeBar /> : <TurnBar view={shown} names={data.names} acting={pb.acting} />}
        </div>
        <div className="bhud-right">
          <div className="bhud-corner">
            <BattleStatusBox view={shown} placeName={placeName} />
            <BattleTopBar
              tools={tools}
              open={popup}
              onToggle={(id) => setPopup((cur) => togglePopup(cur, id))}
              exit={exitLabel !== undefined && !ended ? { label: exitLabel, onExit } : null}
              save={runMode !== undefined && !ended ? { busy, onSave: () => void saveRun() } : null}
              telegraph={{ open: telegraphOpen, onToggle: board.toggleSide }}
            />
          </div>
          {telegraphOpen && (
            <div className="bhud-telegraph">
              <TelegraphPanel
                telegraph={response.telegraph}
                marks={data.marks}
                hoverTexts={tiles.hoverTexts}
                view={view}
                onHoverTiles={hl.setTelegraphHover}
              />
            </div>
          )}
          {hero !== null && !view.ended && !copying && (
            <SummonPanel
              view={view}
              hero={hero}
              summons={cmds.summons}
              names={data.liveNames}
              enabled={data.canAct}
              command={sel.command}
              loadingCommand={sel.loadingCommand}
              onSetMode={actions.send}
              onStartCommand={cmds.startCommand}
              onPickDest={cmds.pickCommandDest}
              onCancelCommand={() => {
                sel.setCommand(null);
                sel.setPanelPreview(null);
              }}
              onCommand={actions.send}
              onPreviewAction={sel.setPanelPreview}
              infuse={sel.infuse}
              loadingInfuse={sel.loadingInfuse}
              onStartInfuse={cmds.startInfuse}
              onCancelInfuse={() => {
                sel.setInfuse(null);
                sel.setPanelPreview(null);
              }}
              onInfuse={actions.send}
              infusePreview={sel.infuse === null ? null : (hl.preview?.infusion ?? null)}
              cards={cards}
            />
          )}
          {dockUnit !== null && (
            <PinnedUnitDock
              unit={dockUnit}
              names={data.names}
              heroId={heroId}
              skills={data.skillNames}
              cards={cards}
              view={shown}
              onTogglePin={() => setPinnedUnit(null)}
            />
          )}
        </div>
        <BattleBottomBar
          rootRef={bottomRef}
          response={response}
          view={view}
          hero={hero}
          cards={cards}
          narrow={narrow}
          classified={data.classified}
          basic={data.basic}
          raceModeList={data.raceModeList}
          buttons={data.buttons}
          fallback={data.fallback}
          mode={mode}
          canAct={data.canAct}
          copying={copying}
          ended={ended}
          exitLabel={exitLabel}
          endTitle={endTitle}
          endSummary={endSummary}
          onExit={onExit}
          speed={pb.speed}
          playing={pb.playing}
          onSpeed={pb.setSpeed}
          onSkipNow={pb.skipNow}
          onPickMode={cmds.pickMode}
          onPickSkill={cmds.pickSkill}
          onHint={setHint}
          onCancel={cmds.cancel}
          onAct={actions.act}
          onPreviewAction={sel.setPanelPreview}
        />
      </div>
      <BattleDialogs
        response={response}
        hero={hero}
        busy={busy}
        copying={copying}
        copyPaused={data.copyPaused}
        followPaused={data.followPaused}
        copyName={data.copyName}
        skillNames={data.skillNames}
        liveNames={data.liveNames}
        focusTile={data.focusTile}
        model={data.model}
        oathWarning={actions.oathPending?.warning ?? null}
        onConfirmOath={actions.confirmOath}
        onCancelOath={actions.cancelOath}
        infusionPick={actions.infusionPick}
        infusionOptions={actions.infusionOptions}
        onCancelInfusion={closeInfusion}
        onPickInfusion={(a, id) => {
          actions.send(withInfusion(a, id));
          closeInfusion();
        }}
        onDecideCopy={actions.decideCopy}
        onDecide={actions.decideWith}
      />
    </div>
  );
}
