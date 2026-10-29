// 戰鬥畫面（Phase 3-8 版面）：頂端列（回合、行動順序、反應設定／隊友指令／圖例的彈出面板）、
// 中央放大的戰場（滑過單位顯示浮動資訊卡）、右側可收合的紀錄與預告、左下主角狀態、底部技能列、右下回合操作。
// 每次送出動作或決定：鎖住操作 → 收到回應 → 先畫 `initial_view`，再依 `steps` 一步一步播放
// （標示行動者 → 移動動畫 → 該步的 `view` → 紀錄 → 停頓）→ 最後以 `res.view` 為準。
//
// Phase 3T-7：主元件只負責組裝；狀態與邏輯在 `screens/battle/` 的自訂 hook，點擊規則在 `battle/tileClick.ts`：
//   usePlayback（播放與送出）、useBattleData（派生資料）、useSelection（選取狀態）、useBattleActions（送出動作）、
//   useSelectionCommands（選取操作）、useBattleKeys（鍵盤）、useTileInteraction（格子互動與資訊卡）、
//   useHighlights（預覽與高亮）、useBoardViewport（版面與縮放）；子元件 ZoomControls、BattleBottomBar、BattleDialogs。
import { useCallback, useRef, useState } from "react";
import type { BattleResponse, SkillCard } from "../api/types";
import { withInfusion } from "../battle/infusion";
import { cardPlacement } from "../battle/stageLayout";
import { DEFAULT_LAYOUT } from "../battle/layoutPrefs";
import { objectiveLine } from "../battle/objective";
import { orderButton, withOrder } from "../battle/orders";
import { togglePopup, type TopPopup } from "../battle/skillTray";
import { BattleCanvas } from "../ui/BattleCanvas";
import { BattleLog } from "../ui/BattleLog";
import { BattleTopBar } from "../ui/BattleTopBar";
import { ModePanel } from "../ui/ActionPanel";
import { ErrorBanner } from "../ui/ErrorBanner";
import { HoverFloat } from "../ui/HoverFloat";
import { NoticeBanner } from "../ui/NoticeBanner";
import { ResizeHandle } from "../ui/ResizeHandle";
import { SidePanel } from "../ui/SidePanel";
import { SummonPanel } from "../ui/SummonPanel";
import { TelegraphPanel } from "../ui/TelegraphPanel";
import { TileCard } from "../ui/TileCard";
import { TurnBar } from "../ui/TurnBar";
import { UnitInfo } from "../ui/UnitInfo";
import { BattleBottomBar } from "./battle/BattleBottomBar";
import { BattleDialogs } from "./battle/BattleDialogs";
import { battleTools } from "./battle/battleTools";
import { useBattleActions } from "./battle/useBattleActions";
import { useBattleData } from "./battle/useBattleData";
import { useBattleKeys } from "./battle/useBattleKeys";
import { useBoardViewport } from "./battle/useBoardViewport";
import { useHighlights } from "./battle/useHighlights";
import { errorText, usePlayback } from "./battle/usePlayback";
import { useSelection } from "./battle/useSelection";
import { useSelectionCommands } from "./battle/useSelectionCommands";
import { useTileInteraction } from "./battle/useTileInteraction";
import { ZoomControls } from "./battle/ZoomControls";

interface Props {
  initial: BattleResponse;
  onExit(): void;
  /** 有值時顯示「離開」按鈕（可隨時離開），結束面板的主按鈕也用這個文字；省略為一般戰鬥。 */
  exitLabel?: string;
  /** 從一輪（roguelite）進入時：顯示「存檔」按鈕與主角倒下提示（Phase 3-5c-1）。 */
  runMode?: RunMode;
}

export interface RunMode {
  /** 存檔，回傳要顯示的訊息。 */
  onSave(): Promise<string>;
}

export function BattleScreen({ initial, onExit, exitLabel, runMode }: Props) {
  const battleId = initial.battle_id;
  const heroId = initial.hero_id;
  const cardsRef = useRef<Readonly<Record<string, SkillCard | undefined>>>({});
  const resetSelectionRef = useRef<() => void>(() => undefined);
  const pb = usePlayback(initial, cardsRef, resetSelectionRef);
  const { response, shown, busy } = pb;
  const data = useBattleData(battleId, heroId, response, shown, pb.acting, busy);
  const { view, hero, cards, copying } = data;
  cardsRef.current = cards;
  const sel = useSelection(response, data.canAct, copying, data.copyPick, data.modes);
  resetSelectionRef.current = sel.resetOnRun;
  const { mode } = sel;
  /** 中性提示（例如灰掉技能的原因），幾秒後自動消失。 */
  const [hint, setHint] = useState<string | null>(null);
  const closeHint = useCallback(() => setHint(null), []);
  const [saveNote, setSaveNote] = useState<string | null>(null);
  /** 頂端列開著的彈出面板（同時只開一個）。 */
  const [popup, setPopup] = useState<TopPopup | null>(null);

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
  const { layout, narrow, collapsed, scale } = board;

  /** 浮動資訊卡：只在滑過單位時出現（取代固定的單位資訊欄，Phase 3-8）。 */
  const shownHero = shown.units.find((u) => u.id === heroId) ?? null;
  const ended = (response.awaiting === "ended" || response.awaiting === "stalled") && !busy;

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
    limits: board.limits,
    scale,
    narrow,
    onLayoutChange: board.patchLayout,
    onLayoutReset: board.resetLayout,
    shake: pb.shake,
    onShake: pb.setShake,
    collapseTile: tiles.collapseTile,
    onCollapseTile: tiles.setCollapseTile,
  });

  const { cardTile, hoverUnit, tileCardSections } = tiles;
  return (
    <div className={`battle-screen${collapsed ? " side-collapsed" : ""}${narrow ? " narrow" : ""}`} style={board.layoutStyle}>
      <BattleTopBar
        turnBar={<TurnBar view={shown} names={data.names} acting={pb.acting} />}
        tools={tools}
        open={popup}
        onToggle={(id) => setPopup((cur) => togglePopup(cur, id))}
        exit={exitLabel !== undefined && !ended ? { label: exitLabel, onExit } : null}
        save={runMode !== undefined && !ended ? { busy, note: saveNote, onSave: () => void saveRun() } : null}
      />
      <div className="battle-board">
        <div className={`board-scroll${board.panning ? " panning" : ""}`} ref={board.scrollRef} {...board.panHandlers}>
          <BattleCanvas
            model={data.model}
            highlights={hl.highlights}
            flameOn={hl.flameOn}
            scale={scale}
            onTileClick={tiles.onTileClick}
            onTileHover={tiles.onTileHover}
            onCancel={cmds.cancel}
            rendererRef={pb.rendererRef}
          >
            {cardTile !== null && (hoverUnit !== null || tileCardSections.length > 0) && (
              <HoverFloat placement={cardPlacement(cardTile, data.model, scale)} card={tiles.tileCard}>
                {hoverUnit !== null && (
                  <UnitInfo unit={hoverUnit} names={data.names} heroId={heroId} skills={data.skillNames} cards={cards} view={view} />
                )}
                <TileCard sections={tileCardSections} />
              </HoverFloat>
            )}
          </BattleCanvas>
        </div>
        <ZoomControls
          zoom={layout.zoom}
          scale={scale}
          onZoomStep={board.zoomStep}
          onFill={() => board.patchLayout({ zoom: null })}
        />
        {!collapsed && !narrow && (
          <ResizeHandle
            orientation="vertical"
            direction={-1}
            value={layout.sideWidth}
            range={board.limits.side}
            label="調整右側窄欄寬度"
            onChange={(v) => board.patchLayout({ sideWidth: v })}
            onReset={() => board.patchLayout({ sideWidth: DEFAULT_LAYOUT.sideWidth })}
          />
        )}
        {!narrow && (
          <ResizeHandle
            orientation="horizontal"
            direction={-1}
            value={layout.bottomHeight}
            range={board.limits.bottom}
            label="調整底部列高度"
            onChange={(v) => board.patchLayout({ bottomHeight: v })}
            onReset={() => board.patchLayout({ bottomHeight: DEFAULT_LAYOUT.bottomHeight })}
          />
        )}
        {pb.banner && (
          <div className="battle-banner">
            戰鬥開始
            <div className="battle-banner-goal">{objectiveLine(shown.objective)}</div>
          </div>
        )}
        <div className="board-toasts">
          <ErrorBanner message={pb.error} onClose={() => pb.setError(null)} />
          <NoticeBanner message={hint} onClose={closeHint} />
          {runMode !== undefined && shownHero?.downed === true && (
            <div className="hero-downed-notice" role="status">
              主角倒下，隊友繼續作戰
            </div>
          )}
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
      </div>
      <SidePanel
        collapsed={collapsed}
        onToggle={board.toggleSide}
        telegraph={
          <TelegraphPanel
            telegraph={response.telegraph}
            marks={data.marks}
            hoverTexts={tiles.hoverTexts}
            view={view}
            onHoverTiles={hl.setTelegraphHover}
          />
        }
        log={<BattleLog lines={pb.lines} onHover={hl.setLogHover} />}
      />
      <BattleBottomBar
        response={response}
        view={view}
        shown={shown}
        shownHero={shownHero}
        hero={hero}
        cards={cards}
        skillNames={data.skillNames}
        layout={layout}
        limits={board.limits}
        narrow={narrow}
        onLayoutChange={board.patchLayout}
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
