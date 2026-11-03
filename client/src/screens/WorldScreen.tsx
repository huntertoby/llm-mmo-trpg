// 大世界（測試）畫面（Phase 5A-5；docs/phases/Phase5計畫.md 11.5）：角色畫面 → 地點圖（點相鄰地點移動、遇敵看陣容、
// 開戰或撤退、小鎮休息／換技能／傳送、野外紮營）。戰鬥沿用戰鬥畫面；結束或離開後重新讀地點圖（勝負已由後端回寫）。
// 5A-7（13.3）：左欄可切換到「成長與技能」（配點、閃現、重閃、溶掉、傳承、誓約）；閃現待選時左欄固定顯示選項。
// 5B-5（18.6）：事件卡（旁白、多講一點、解法）、情境判定（引用線索、第一次送出即定案）、判定結果、這裡的人（好感度、
// 說話、聊天、接任務）、酒館傳聞、任務與線頭（左欄）、任務三選一（左欄固定）、說書人的 LLM 開關（標頭）。
// 5D-4（33.2）：左欄加背包與裝備、商店、鐵匠與附魔台的完整畫面（右側背包摘要、服務列的「商店」「鐵匠」切換）。
// 5F-1b：進入角色時讀「你不在的時候」摘要，有新消息就跳一則（DialogFrame）；按「知道了」送 `news_seen`。
// 6B-3：所在地點有實地地圖（`view.field`）時，左欄改成可走動畫面（`WorldField`）；換地圖時上方只跳一行地名。
// 6B-5：有實地地圖時改用網遊式 HUD（版面 A，`WorldHud`）取代右側長條側欄：可走動畫面用滿整個舞台，
// 各面板點圖示或按快捷鍵才打開（同時只開一個，再按、Esc 或點空白關閉）；沒有實地地圖的地點照舊用節點圖＋側欄。
import { useCallback, useEffect, useReducer, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { api, ApiError } from "../api/client";
import type {
  AbsenceView,
  BattleResponse,
  RunChoice,
  WorldAction,
  WorldLlmView,
  WorldSituationResult,
  WorldView,
} from "../api/types";
import { ErrorBanner } from "../ui/ErrorBanner";
import { primeSkillCard } from "../ui/useSkillCards";
import { WorldCharacterPicker } from "../world/WorldCharacterPicker";
import { WorldMap } from "../world/WorldMap";
import { WorldField } from "../world/WorldField";
import { mapPaneKind, PLACE_NAME_MS, placeBanner, type FieldTarget } from "../world/fieldModel";
import { EncounterPanel, HerePanel, WorldPanel } from "../world/WorldPanel";
import { WorldHud } from "../world/WorldHud";
import { HudNotesPanel, HudShadowPanel, HudSkillsPanel } from "../world/HudPanels";
import {
  addToasts,
  fadedBlocks,
  HUD_BUTTONS,
  hudKey,
  hudLayout,
  isNarrow,
  liveHudToasts,
  mateCards,
  nextHudToastChange,
  NOT_OPEN_ZH,
  panelAvailable,
  readTrackerCollapsed,
  restrictions,
  shownPanel,
  togglePanel,
  writeTrackerCollapsed,
  type HudButtonId,
  type HudPanel,
  type HudToast,
} from "../world/hud";
import { useHudStage } from "../world/useHudStage";
import { exitViewRects, followCamera, sameCamera, visibleTiles, type Camera } from "../world/camera";
import { WorldFlashPending, WorldGrowth } from "../world/WorldGrowth";
import { leftPane, togglePane, worldActionOf, type WantPane } from "../world/growth";
import { WorldBagScreen } from "../world/BagScreen";
import { WorldShopScreen } from "../world/ShopScreen";
import { WorldSmithyScreen } from "../world/SmithyPanel";
import { EventCard, SituationResultCard } from "../world/EventCard";
import { AbsenceDialog } from "../world/AbsenceDialog";
import { newsSeenAction, shouldShowAbsence } from "../world/absence";
import { BoardPanel } from "../world/BoardPanel";
import { LeaguePanel } from "../world/LeaguePanel";
import { replayNotes } from "../world/league";
import { NotesPanel } from "../world/NotesPanel";
import { NpcPanel } from "../world/NpcPanel";
import { FriendCard, HudHirePanel, HudNpcPanel } from "../world/FieldPanels";
import { QuestLog, WorldOfferPending } from "../world/QuestLog";
import { appendChat, dialogByNpc, dialogEntries, narratorResting, type ChatEntry } from "../world/story";
import { readWorldChar, writeWorldChar } from "../world/mapView";
import { BattleScreen } from "./BattleScreen";

interface Props {
  onHome(): void;
  /** 開發模式下沒登入時：到登入畫面（5E-1）。 */
  onLogin?(): void;
  /** 已登入時：登出（5E-1）。 */
  onLogout?(): void;
}

const LOG_MAX = 12;
/** 重讀大世界 LLM 開關與健康檢查結果的間隔（同伺服器健康檢查的預設 60 秒；5E-3b）。 */
const LLM_REFRESH_MS = 60_000;

/** 把右欄的某個元素捲到畫面裡並給焦點（NPC 卡片、雇用按鈕；6B-3 互動的最小版）。 */
function revealInPanel(selector: string): void {
  const el = document.querySelector<HTMLElement>(selector);
  if (el === null) return;
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  el.focus({ preventScroll: true });
  el.classList.remove("world-flash");
  void el.offsetWidth; // 重新觸發閃一下的動畫
  el.classList.add("world-flash");
}

function typingInto(target: EventTarget | null): boolean {
  if (typeof HTMLElement === "undefined" || !(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

/** 側欄的切換（商店、鐵匠、公告板……）→ HUD 面板；「回到地點圖」＝關掉。 */
function wantToHud(p: WantPane): HudPanel | null {
  return p === "map" ? null : p;
}

function errorText(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

export function WorldScreen({ onHome, onLogin, onLogout }: Props) {
  const [charId, setCharId] = useState<string | null>(() => readWorldChar());
  const [view, setView] = useState<WorldView | null>(null);
  const [battle, setBattle] = useState<BattleResponse | null>(null);
  /** 循環賽的重播（5F-4）：開場說明（標題、重播驗證）；``null``＝一般戰鬥。 */
  const [replay, setReplay] = useState<string[] | null>(null);
  const [replayOutcome, setReplayOutcome] = useState<string | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasten, setHasten] = useState(false);
  const [log, setLog] = useState<string[]>([]);
  const [want, setWant] = useState<WantPane>("map");
  const [chats, setChats] = useState<Record<string, ChatEntry[]>>({});
  const [result, setResult] = useState<WorldSituationResult | null>(null);
  const [rumors, setRumors] = useState<{ at: string; lines: string[] } | null>(null);
  const [llm, setLlm] = useState<WorldLlmView | null>(null);
  const [absence, setAbsence] = useState<AbsenceView | null>(null);
  /** 上一個畫面的實地地圖 ID（`undefined`＝這個角色第一次載入；6B-3 換地圖跳地名用）。 */
  const lastMap = useRef<string | null | undefined>(undefined);
  const [banner, setBanner] = useState<{ name: string; n: number } | null>(null);

  // ---- HUD（6B-5）：單一浮動面板、浮動提示、任務追蹤收合 ----
  const [hudPanel, setHudPanel] = useState<HudPanel | null>(null);
  /** `npc`／`friend` 面板的對象（NPC ID 或影子主人的角色 ID；6B-4）。 */
  const [hudWho, setHudWho] = useState<string | null>(null);
  const [toasts, setToasts] = useState<HudToast[]>([]);
  const toastSeq = useRef(0);
  /** 這次進入角色後已經到過的地點（第一次進入有限制的地點時跳紅框提示）。 */
  const seenPlaces = useRef(new Set<string>());
  const [trackerFolded, setTrackerFolded] = useState(() => readTrackerCollapsed());
  /** 窄視窗時任務追蹤自動收合；玩家點開後這次先展開（不寫進本機）。 */
  const [narrowOpen, setNarrowOpen] = useState(false);
  // 6B-6：實地地圖的鏡頭（`WorldField` 逐格回報）：小地圖的框、出口半透明以畫面上的出口位置判斷
  const [fieldCam, setFieldCam] = useState<Camera | null>(null);
  const onFieldCamera = useCallback((cam: Camera) => setFieldCam((cur) => (cur !== null && sameCamera(cur, cam) ? cur : cam)), []);
  const [, tick] = useReducer((n: number) => n + 1, 0);
  const pushToast = useCallback((texts: readonly string[], warn: boolean) => {
    if (texts.length === 0) return;
    const seq = toastSeq.current;
    toastSeq.current += texts.length;
    setToasts((cur) => addToasts(cur, texts, warn, Date.now(), seq));
  }, []);

  const show = useCallback((next: WorldView, mine: ChatEntry | null = null) => {
    for (const card of [...next.character.skills, ...next.character.bench]) primeSkillCard(card);
    setView(next);
    const place = placeBanner(lastMap.current, next.field);
    lastMap.current = next.field?.map_id ?? null;
    if (place !== null) setBanner((b) => ({ name: place, n: (b?.n ?? 0) + 1 }));
    if (next.events.length > 0) setLog((cur) => [...next.events, ...cur].slice(0, LOG_MAX));
    if (next.events.length > 0) pushToast(next.events, false);
    if (next.field != null && !seenPlaces.current.has(next.here.location)) {
      seenPlaces.current.add(next.here.location);
      const limits = restrictions(next);
      if (limits.length > 0) pushToast([limits.join(" ")], true);
    }
    if (next.situation_result != null) setResult(next.situation_result);
    if ((next.rumors ?? []).length > 0) setRumors({ at: next.here.location, lines: [...(next.rumors ?? [])] });
    const grouped = dialogByNpc(next.dialog ?? []);
    if (mine !== null || Object.keys(grouped).length > 0) {
      setChats((cur) => {
        let out = cur;
        for (const [npc, lines] of Object.entries(grouped)) {
          const head = mine !== null && mine.speaker === npc ? [{ ...mine, speaker: "你" }] : [];
          out = appendChat(out, npc, [...head, ...dialogEntries(lines)]);
        }
        return out;
      });
    }
  }, [pushToast]);

  // 地名約 2 秒後淡出（21.7）
  useEffect(() => {
    if (banner === null) return undefined;
    const timer = window.setTimeout(() => setBanner(null), PLACE_NAME_MS);
    return () => window.clearTimeout(timer);
  }, [banner]);

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      api.worldLlm().then(
        (v) => !cancelled && setLlm(v),
        () => undefined,
      );
    void load();
    // 健康檢查每 60 秒一次（伺服器端）；這裡跟著重讀，讓「說書人休息中」標示出現／消失（5E-3b）
    const timer = window.setInterval(() => void load(), LLM_REFRESH_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (charId === null || view !== null) return undefined;
    let cancelled = false;
    api.world(charId).then(
      (v) => !cancelled && show(v),
      (e: unknown) => {
        if (cancelled) return;
        // 角色不見了（存檔被刪）：回角色畫面
        if (e instanceof ApiError && e.status === 404) {
          writeWorldChar(null);
          setCharId(null);
        }
        setError(errorText(e));
      },
    );
    return () => {
      cancelled = true;
    };
  }, [charId, view, show]);

  // 「你不在的時候」（5F-1b）：每次進入角色讀一次；讀不到就算了（不擋畫面）。
  useEffect(() => {
    setAbsence(null);
    if (charId === null) return undefined;
    let cancelled = false;
    api.worldAbsence(charId).then(
      (v) => !cancelled && setAbsence(v),
      () => undefined,
    );
    return () => {
      cancelled = true;
    };
  }, [charId]);

  function closeAbsence() {
    if (absence === null) return;
    const action = newsSeenAction(absence);
    setAbsence(null);
    act(action);
  }

  function enter(id: string, first?: WorldView) {
    writeWorldChar(id);
    lastMap.current = undefined;
    setBanner(null);
    setLog([]);
    setToasts([]);
    setHudPanel(null);
    seenPlaces.current = new Set();
    setChats({});
    setResult(null);
    setRumors(null);
    setError(null);
    setCharId(id);
    if (first !== undefined) show(first);
    else setView(null);
  }

  function leaveChar() {
    writeWorldChar(null);
    lastMap.current = undefined;
    setCharId(null);
    setView(null);
    setLog([]);
  }

  async function run(task: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await task();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  const act = (action: WorldAction) =>
    void run(async () => {
      if (charId === null) return;
      if (action.kind === "travel") setResult(null);
      show(await api.worldAct(charId, action));
    });

  const openSituation = (template: string) =>
    void run(async () => {
      if (charId !== null) show(await api.worldSituation(charId, template));
    });

  const solve = (solution: number, useThread: string | null) =>
    act({ kind: "event_solve", solution, use_thread: useThread });

  const answer = (template: string, text: string, cite: string[]) =>
    void run(async () => {
      if (charId !== null) show(await api.worldAnswer(charId, template, text, cite));
    });

  /** 聊天：成功回傳 `true`（清掉輸入框）；玩家說的話先記進紀錄（`speaker` 暫放 NPC ID）。 */
  async function chat(npc: string, text: string): Promise<boolean> {
    if (charId === null) return false;
    setBusy(true);
    setError(null);
    try {
      show(await api.worldChat(charId, npc, text), { speaker: npc, text, mine: true });
      return true;
    } catch (e) {
      setError(errorText(e));
      return false;
    } finally {
      setBusy(false);
    }
  }

  const toggleLlm = (on: boolean) =>
    void run(async () => {
      setLlm(await api.setWorldLlm(on));
    });

  /** 送一個世界動作；回傳失敗時的 HTTP 狀態（成功為 `null`），給一輪元件判斷要不要收起表單。 */
  async function actStatus(action: WorldAction): Promise<number | null> {
    if (charId === null) return 0;
    setBusy(true);
    setError(null);
    try {
      show(await api.worldAct(charId, action));
      return null;
    } catch (e) {
      setError(errorText(e));
      window.scrollTo({ top: 0, behavior: "smooth" });
      return e instanceof ApiError ? e.status : 0;
    } finally {
      setBusy(false);
    }
  }

  function choose(choice: RunChoice): Promise<number | null> {
    const action = worldActionOf(choice);
    if (action === null) {
      setError("大世界沒有這個選項");
      return Promise.resolve(0);
    }
    return actStatus(action);
  }

  const travel = (to: string) => act({ kind: "travel", to, hasten });

  /** 實地地圖的動作（走路、傳送石）：只送不套用，給可走動畫面先播動畫再套用；失敗時顯示錯誤、回傳 `null`。 */
  async function sendField(action: WorldAction): Promise<WorldView | null> {
    if (charId === null) return null;
    try {
      const next = await api.worldAct(charId, action);
      setError(null);
      return next;
    } catch (e) {
      setError(errorText(e));
      return null;
    }
  }

  /** HUD 版面：互動改成開對應的浮動面板（同時只開一個）；NPC、雇用、朋友各有自己的面板（6B-4），不再捲動整頁。 */
  function interactHud(target: FieldTarget) {
    if (target.kind === "npc") {
      setHudWho(target.npc);
      setHudPanel("npc");
      return;
    }
    if (target.kind === "friend") {
      setHudWho(target.owner);
      setHudPanel("friend");
      return;
    }
    const panel: Partial<Record<string, HudPanel>> = { shop: "shop", smithy: "smithy", enchanter: "smithy", notice_board: "board", mentor: "growth" };
    const to = panel[target.facility];
    if (to !== undefined) {
      setHudPanel(to);
      return;
    }
    if (target.facility === "tavern") {
      act({ kind: "tavern" });
      setHudPanel("place");
    } else if (target.facility === "hire") setHudPanel("hire");
  }

  /** 走到設施或 NPC 旁邊互動：開原本的面板（6B-4 前的最小版）。 */
  function interact(target: FieldTarget) {
    if (view !== null && mapPaneKind(view) === "field") {
      interactHud(target);
      return;
    }
    if (target.kind === "npc") {
      revealInPanel(`[data-npc="${target.npc}"]`);
      return;
    }
    if (target.kind === "friend") return; // 朋友只站在實地地圖（HUD 版面）上
    switch (target.facility) {
      case "shop":
        setWant("shop");
        return;
      case "smithy":
      case "enchanter":
        setWant("smithy");
        return;
      case "notice_board":
        setWant("board");
        return;
      case "mentor":
        setWant("growth");
        return;
      case "tavern":
        act({ kind: "tavern" });
        return;
      case "hire":
        revealInPanel('[data-testid="world-hire-toggle"]');
        return;
      default:
        return;
    }
  }

  const fight = () =>
    void run(async () => {
      if (charId === null) return;
      const res = await api.worldBattle(charId);
      show(res.world);
      setReplay(null);
      setBattle(res.battle);
    });

  const watchReplay = (matchId: string) =>
    void run(async () => {
      if (charId === null) return;
      const res = await api.worldLeagueReplay(charId, matchId);
      setReplay(replayNotes(res));
      setReplayOutcome(res.outcome_zh);
      setBattle(res.battle);
    });

  async function backToMap() {
    setError(null);
    try {
      if (charId !== null) show(await api.world(charId));
      setBattle(null);
      setReplay(null);
    } catch (e) {
      setError(errorText(e));
    }
  }

  // ---- HUD（6B-5） ----
  const hudMode = battle === null && view !== null && mapPaneKind(view) === "field";
  const stage = useHudStage(hudMode, `${error ?? ""}|${llm?.notice_zh ?? ""}|${view === null ? "" : "v"}`);
  const narrow = isNarrow(stage.viewport);
  const nowMs = Date.now();
  const liveToasts = hudMode ? liveHudToasts(toasts, nowMs, narrow ? 1 : undefined) : [];
  const toastWait = nextHudToastChange(liveToasts, nowMs);
  useEffect(() => {
    if (toastWait === null) return undefined;
    const id = window.setTimeout(tick, toastWait + 16);
    return () => window.clearTimeout(id);
  });
  const shown = view === null ? null : shownPanel(view, hudPanel);
  const panelLocked = shown === "pending" || shown === "offer";

  function hudButton(id: HudButtonId) {
    const b = HUD_BUTTONS.find((x) => x.id === id);
    if (b === undefined) return;
    if (b.panel === null) {
      pushToast([`${b.name}：${NOT_OPEN_ZH}`], false);
      return;
    }
    if (view !== null && !panelAvailable(view, b.panel)) {
      pushToast([`${b.name}：現在沒有資料`], false);
      return;
    }
    const panel = b.panel;
    setHudPanel((cur) => togglePanel(cur, panel));
  }
  const closeHud = () => setHudPanel(null);
  const hudKeys = useRef({ active: false, locked: false, button: hudButton, close: closeHud, map: () => undefined as void });
  hudKeys.current = {
    active: hudMode,
    locked: panelLocked,
    button: hudButton,
    close: closeHud,
    map: () => pushToast([`大地圖：${NOT_OPEN_ZH}`], false),
  };
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const h = hudKeys.current;
      if (!h.active) return;
      const k = hudKey(e, typingInto(e.target));
      if (k === null) return;
      if (k.kind === "escape") {
        if (!h.locked) h.close();
        return;
      }
      if (e.repeat) return;
      e.preventDefault();
      if (k.kind === "map") h.map();
      else h.button(k.id);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  /** 現在要開的 HUD 面板內容（沿用原本側欄、左欄的元件）。 */
  function hudPanelContent(v: WorldView): ReactNode {
    switch (shown) {
      case "pending":
        return <WorldFlashPending view={v} busy={busy} onChoose={choose} />;
      case "offer":
        return <WorldOfferPending view={v} busy={busy} onAct={act} />;
      case "bag":
        return <WorldBagScreen view={v} busy={busy} onAct={act} onClose={closeHud} />;
      case "skills":
        return <HudSkillsPanel view={v} busy={busy} onAct={act} />;
      case "growth":
        return <WorldGrowth view={v} busy={busy} onChoose={choose} onAct={actStatus} onClose={closeHud} />;
      case "quests":
        return <QuestLog view={v} onClose={closeHud} />;
      case "shadow":
        return <HudShadowPanel view={v} busy={busy} onAct={act} />;
      case "notes":
        return (
          <HudNotesPanel notes={charId !== null && <NotesPanel characterId={charId} location={v.here.location} busy={busy} />} log={log} />
        );
      case "place":
        return (
          <div className="world-hud-stack" data-testid="world-hud-place">
            <HerePanel
              view={v}
              busy={busy}
              hasten={false}
              onHasten={() => undefined}
              onAct={act}
              rumors={rumors !== null && rumors.at === v.here.location ? rumors.lines : []}
              onPane={(p) => setHudPanel(wantToHud(p))}
              hideHasten
            />
            <NpcPanel view={v} busy={busy} chats={chats} onAct={act} onChat={chat} />
          </div>
        );
      case "npc":
        return hudWho === null ? null : <HudNpcPanel key={hudWho} view={v} npc={hudWho} busy={busy} chats={chats} onAct={act} onChat={chat} />;
      case "hire":
        return <HudHirePanel view={v} busy={busy} onAct={act} />;
      case "friend":
        return hudWho === null ? null : <FriendCard key={hudWho} view={v} owner={hudWho} />;
      case "shop":
        return <WorldShopScreen view={v} busy={busy} onAct={act} onClose={closeHud} />;
      case "smithy":
        return <WorldSmithyScreen view={v} busy={busy} onAct={act} onClose={closeHud} />;
      case "board":
        return charId === null ? null : <BoardPanel characterId={charId} view={v} busy={busy} onAct={act} onClose={closeHud} />;
      case "league":
        return charId === null ? null : (
          <LeaguePanel characterId={charId} view={v} busy={busy} onAct={act} onReplay={watchReplay} onClose={closeHud} />
        );
      default:
        return null;
    }
  }

  function renderHud(v: WorldView) {
    const field = v.field;
    if (field == null) return null;
    const folded = trackerFolded || (narrow && !narrowOpen);
    const layout = hudLayout(stage.width, stage.height, { mates: mateCards(v).length, narrow, collapsed: folded });
    const cam = fieldCam ?? followCamera(stage, field, field.me);
    const faded = fadedBlocks(layout, exitViewRects(field, cam, stage));
    const hasCenter = v.encounter !== null || result !== null || v.event != null;
    const style = { height: stage.height, "--hud-s": layout.scale } as CSSProperties;
    return (
      <div className="world-hud-stage" ref={stage.ref} style={style} data-testid="world-hud-stage">
        <WorldField
          view={v}
          busy={busy}
          send={sendField}
          commit={show}
          onInteract={interact}
          hud={{ width: stage.width, height: stage.height, onCamera: onFieldCamera }}
        />
        <WorldHud
          view={v}
          viewTiles={visibleTiles(stage, field, cam)}
          layout={layout}
          faded={faded}
          toasts={liveToasts}
          trackerCollapsed={folded}
          onTracker={(c) => {
            if (narrow) setNarrowOpen(!c);
            else {
              setTrackerFolded(c);
              writeTrackerCollapsed(c);
            }
          }}
          onButton={hudButton}
          onMap={() => hudKeys.current.map()}
          onSettings={() => pushToast([`設定：${NOT_OPEN_ZH}`], false)}
          onPlace={() => setHudPanel((cur) => togglePanel(cur, "place"))}
          openPanel={shown}
          panel={shown === null ? null : hudPanelContent(v)}
          panelLocked={panelLocked}
          onClosePanel={closeHud}
          center={
            hasCenter ? (
              <>
                <EncounterPanel view={v} busy={busy} onAct={act} onBattle={fight} />
                {result !== null && <SituationResultCard result={result} onClose={() => setResult(null)} />}
                {v.event != null && <EventCard event={v.event} busy={busy} onOpen={openSituation} onSolve={solve} onAnswer={answer} />}
              </>
            ) : null
          }
        />
      </div>
    );
  }

  if (battle !== null) {
    return (
      <BattleScreen
        key={battle.battle_id}
        initial={battle}
        onExit={() => void backToMap()}
        exitLabel={replay !== null ? "回到循環賽" : "回到地點圖"}
        openingNotes={replay ?? view?.encounter?.opening_zh}
        endTitle={replay !== null ? replayOutcome : undefined}
      />
    );
  }
  if (charId === null) {
    return <WorldCharacterPicker onEnter={enter} onHome={onHome} onLogin={onLogin} onLogout={onLogout} />;
  }
  return (
    <div className={`run-screen world-screen${hudMode ? " hud-mode" : ""}`}>
      <header className="run-header">
        <h1>
          大世界（測試）　<span className="muted small">{view === null ? "" : `${view.map.name_zh}（${view.map.level_zh}）`}</span>
        </h1>
        <div className="run-header-buttons">
          {narratorResting(llm) && (
            <span className="world-narrator-rest small" role="status" data-testid="world-narrator-rest">
              說書人休息中（使用固定文字）
            </span>
          )}
          {llm !== null && (
            <label className="world-llm small" data-testid="world-llm">
              <input type="checkbox" checked={llm.enabled} disabled={busy} onChange={(e) => toggleLlm(e.target.checked)} />
              說書人用本機模型
              <span className="muted">（伺服器預設{llm.default ? "開" : "關"}）</span>
            </label>
          )}
          <button type="button" onClick={leaveChar}>
            換角色
          </button>
          <button type="button" onClick={onHome}>
            回首頁
          </button>
        </div>
      </header>
      <ErrorBanner message={error} onClose={() => setError(null)} />
      {view !== null && shouldShowAbsence(absence) && <AbsenceDialog view={absence} busy={busy} onClose={closeAbsence} />}
      {llm?.notice_zh != null && <div className="muted small world-llm-notice">{llm.notice_zh}</div>}
      {banner !== null && (
        <div key={banner.n} className="world-place-banner" role="status" data-testid="world-place-banner">
          {banner.name}
        </div>
      )}

      {view === null ? (
        <div className="muted">載入中……</div>
      ) : hudMode ? (
        renderHud(view)
      ) : (
        <div className="world-layout">
          {leftPane(view, want) === "pending" && <WorldFlashPending view={view} busy={busy} onChoose={choose} />}
          {leftPane(view, want) === "offer" && <WorldOfferPending view={view} busy={busy} onAct={act} />}
          {leftPane(view, want) === "growth" && (
            <WorldGrowth view={view} busy={busy} onChoose={choose} onAct={actStatus} onClose={() => setWant("map")} />
          )}
          {leftPane(view, want) === "quests" && <QuestLog view={view} onClose={() => setWant("map")} />}
          {leftPane(view, want) === "board" && charId !== null && (
            <BoardPanel characterId={charId} view={view} busy={busy} onAct={act} onClose={() => setWant("map")} />
          )}
          {leftPane(view, want) === "league" && charId !== null && (
            <LeaguePanel
              characterId={charId}
              view={view}
              busy={busy}
              onAct={act}
              onReplay={watchReplay}
              onClose={() => setWant("map")}
            />
          )}
          {leftPane(view, want) === "bag" && <WorldBagScreen view={view} busy={busy} onAct={act} onClose={() => setWant("map")} />}
          {leftPane(view, want) === "shop" && <WorldShopScreen view={view} busy={busy} onAct={act} onClose={() => setWant("map")} />}
          {leftPane(view, want) === "smithy" && <WorldSmithyScreen view={view} busy={busy} onAct={act} onClose={() => setWant("map")} />}
          {leftPane(view, want) === "map" &&
            (mapPaneKind(view) === "field" ? (
              <WorldField view={view} busy={busy} send={sendField} commit={show} onInteract={interact} />
            ) : (
              <WorldMap view={view} busy={busy} onTravel={travel} />
            ))}
          <WorldPanel
            view={view}
            busy={busy}
            hasten={hasten}
            onHasten={setHasten}
            onAct={act}
            onBattle={fight}
            log={log}
            pane={leftPane(view, want)}
            onPane={(p) => setWant((v) => togglePane(v, p))}
            growthOpen={leftPane(view, want) === "growth" || leftPane(view, want) === "pending"}
            onGrowth={() => setWant((v) => (v === "growth" ? "map" : "growth"))}
            questsOpen={leftPane(view, want) === "quests"}
            onQuests={() => setWant((v) => (v === "quests" ? "map" : "quests"))}
            rumors={rumors !== null && rumors.at === view.here.location ? rumors.lines : []}
            eventSlot={
              <>
                {result !== null && <SituationResultCard result={result} onClose={() => setResult(null)} />}
                {view.event != null && <EventCard event={view.event} busy={busy} onOpen={openSituation} onSolve={solve} onAnswer={answer} />}
              </>
            }
            peopleSlot={
              <>
                <NpcPanel view={view} busy={busy} chats={chats} onAct={act} onChat={chat} />
                {charId !== null && <NotesPanel characterId={charId} location={view.here.location} busy={busy} />}
              </>
            }
          />
        </div>
      )}
    </div>
  );
}
