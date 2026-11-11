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
import { useCallback, useEffect, useMemo, useReducer, useRef, useState, type CSSProperties, type ReactNode } from "react";
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
import { DialogHudBox } from "../ui/DialogFrame";
import { primeSkillCard } from "../ui/useSkillCards";
import { WorldCharacterPicker } from "../world/WorldCharacterPicker";
import { WorldMap } from "../world/WorldMap";
import { battleFrame } from "../world/battlefield";
import { WorldField } from "../world/WorldField";
import { mapPaneKind, PLACE_NAME_MS, placeBanner, type FieldTarget } from "../world/fieldModel";
import { EncounterPanel, HerePanel, WorldPanel } from "../world/WorldPanel";
import { WorldHud } from "../world/WorldHud";
import { RegionMap } from "../world/RegionMap";
import { AtlasMap } from "../world/AtlasMap";
import { atlasMapOf, nextMapLayer, objectHud } from "../world/atlasModel";
import { PavilionPanel, SteleMenu } from "../world/CapitalPanels";
import { HudNotesPanel, HudShadowPanel, HudSkillsPanel } from "../world/HudPanels";
import {
  addToasts,
  dialogBox,
  fadedBlocks,
  HUD_BUTTONS,
  hudKey,
  hudLayout,
  isNarrow,
  liveHudToasts,
  mateCards,
  hudInsets,
  nextHudToastChange,
  NOT_OPEN_ZH,
  panelAvailable,
  readTrackerCollapsed,
  restrictions,
  shownPanel,
  sneakState,
  togglePanel,
  writeTrackerCollapsed,
  type HudButtonId,
  type HudPanel,
  type HudToast,
} from "../world/hud";
import { useHudStage } from "../world/useHudStage";
import { FieldObjectCard } from "../world/FieldThings";
import { exitViewRects, FIELD_SCALE, followCamera, sameCamera, visibleTiles, type Camera } from "../world/camera";
import { WorldFlashPending, WorldGrowth } from "../world/WorldGrowth";
import { leftPane, togglePane, worldActionOf, type WantPane } from "../world/growth";
import { WorldBagScreen } from "../world/BagScreen";
import { WorldShopScreen } from "../world/ShopScreen";
import { WorldSmithyScreen } from "../world/SmithyPanel";
import { EventCard, SituationResultCard } from "../world/EventCard";
import { AbsenceDialog } from "../world/AbsenceDialog";
import { AllocateLessonDialog, AwakenDialog, LessonDialog, LevelUpDialog, OpeningDialog, allocateSeenIds, lessonShown, shouldShowOpening } from "../world/OpeningDialog";
import { heroDoll, openingStage, splitOpening, takeAtlasRise } from "../world/opening";
import { hudAvoidRects, hudColumnRects, hudReach } from "../world/hudAvoid";
import type { GuideLines } from "../world/fieldPeople";
import { openRegionsOf } from "../world/fieldScenery";
import { HINTS_OFF_ACTION, HINTS_RESET_ACTION, OPENING_SEEN, hintSeenAction, hintsOf, lessonSeenId } from "../world/battleHints";
import { newsSeenAction, shouldShowAbsence } from "../world/absence";
import { BoardPanel } from "../world/BoardPanel";
import { LeaguePanel } from "../world/LeaguePanel";
import { MailPanel, type MailApi } from "../world/MailPanel";
import { replayNotes } from "../world/league";
import { NotesPanel } from "../world/NotesPanel";
import { NpcPanel } from "../world/NpcPanel";
import { FriendCard, HudHirePanel, HudNpcPanel } from "../world/FieldPanels";
import { QuestLog, WorldOfferPending } from "../world/QuestLog";
import { useWorldSounds } from "../world/useWorldSounds";
import { appendChat, dialogByNpc, dialogEntries, narratorResting, type ChatEntry } from "../world/story";
import { readWorldChar, writeWorldChar } from "../world/mapView";
import { BattleScreen } from "./BattleScreen";
import { battleSummary } from "../world/battleSummary";
import { isDevMode } from "../run/startFlow";
import { worldPlaceName } from "../battle/placeName";
import { useRegionTheme, worldRegion } from "../ui/regionTheme";
import { PREGEN_HINT_DELAY_MS, pregenRequestId, pregenWaitBody, pregenWaitText } from "../world/pregen";
import { WAIT_DONE_MS, type WaitStatus } from "../render/waitArt";
import { reducedMotion } from "../ui/motionPrefs";
import { PregenWaitDialog } from "../world/PregenWaitDialog";
import { RangeDoneDialog, RangeScreen, chooseDoneLines, clearRangeDraft, rangeDoneLines } from "../world/RangeScreen";
import { CHOOSE_OPEN_LABEL, SANDBOX_NOTE, choosePageShown, opensChoose, rangeMode, rangePlaceName, type ChoosePage } from "../world/range";

/** 地圖的兩層（6D-5）：區域圖、大世界圖。 */
type MapLayer = "region" | "atlas";

interface Props {
  onHome(): void;
  /** 開發模式下沒登入時：到登入畫面（5E-1）。 */
  onLogin?(): void;
  /** 已登入時：登出（5E-1）。 */
  onLogout?(): void;
}

const LOG_MAX = 12;
const NO_GUIDES: GuideLines = new Map();
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
  /** 開發模式（網址 `?dev=1`，6F-1）：頂列的「大世界（測試）」與本機模型勾選框只在這時顯示。 */
  const devMode = isDevMode(window.location.search);
  /** 循環賽的重播（5F-4）：開場說明（標題、重播驗證）；``null``＝一般戰鬥。 */
  const [replay, setReplay] = useState<string[] | null>(null);
  const [replayOutcome, setReplayOutcome] = useState<string | undefined>(undefined);
  /** 開發用 Boss 戰（6F-3）：和循環賽重播一樣不回寫世界，結束回地點圖。 */
  const [devFight, setDevFight] = useState(false);
  /** TR-1（#134）：主城工坊靶場的沙盒試打（不回寫世界；結束回到靶場）。 */
  const [rangeFight, setRangeFight] = useState(false);
  /** TR-1／OB-5：確定出發、正式選定之後說的話（關掉前顯示在世界畫面上）。 */
  const [rangeDone, setRangeDone] = useState<{ lines: { speaker_zh: string; text_zh: string }[]; chosen: boolean } | null>(null);
  /** OB-5：「正式選定」整頁的開關（`auto`＝到了葛蘭那裡或主城就開；`closed`＝按了「之後再選」；`open`＝點葛蘭或靶場再打開）。 */
  const [choosePage, setChoosePage] = useState<ChoosePage>("auto");
  /** 戰鬥播完後先同步回來的世界畫面（6F-1 戰後結算；回到地點圖時才 `show`，toast 不會丟）。 */
  const [ended, setEnded] = useState<{ view: WorldView | null } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasten, setHasten] = useState(false);
  const [log, setLog] = useState<string[]>([]);
  const [want, setWant] = useState<WantPane>("map");
  const [chats, setChats] = useState<Record<string, ChatEntry[]>>({});
  const [result, setResult] = useState<WorldSituationResult | null>(null);
  const [rumors, setRumors] = useState<{ at: string; lines: string[] } | null>(null);
  const [llm, setLlm] = useState<WorldLlmView | null>(null);
  const [pregenWait, setPregenWait] = useState<{ text: string; requestId: string; status: WaitStatus; cancel: () => void } | null>(null);
  const [absence, setAbsence] = useState<AbsenceView | null>(null);
  useRegionTheme(view !== null ? worldRegion(view) : null); // RT-1：實地地圖的區域（主城與室內是 capital；沒有＝hub）
  /** 開場、教學、升級畫面、戰鬥短提示看過了沒（6F-4，6F-2b：記在角色身上，`view.hints`）。這次畫面裡剛關掉的
   * 先在本機記一下（`closed`），等伺服器回來的紀錄蓋過去，不會因為送出中又跳一次。 */
  const [closed, setClosed] = useState<ReadonlySet<string>>(new Set());
  useEffect(() => setClosed(new Set()), [charId]);
  const hintState = hintsOf(view?.hints);
  const seenIds = new Set([...hintState.seen, ...closed]);
  function markSeen(ids: string[], level?: number) {
    setClosed((prev) => new Set([...prev, ...ids, ...(level === undefined ? [] : [`level:${level}`])]));
    act(hintSeenAction(ids, level));
  }
  // RT-5 主城開場四格：① 醒來（插圖卡、只有「站起來」）→ ② 守印人頭上「！」＋第一個指示、任務欄出現
  // → ③ 大世界圖（浮起只播一次）→ ④ 傳送到霧渡鎮（主題換雲嶺、渡婆婆頭上「！」）。句子全部來自 `view.guide.opening`。
  const opening = openingStage(view?.guide, seenIds.has(OPENING_SEEN));
  const openingSplit = useMemo(() => splitOpening(view?.guide?.opening ?? [], view?.field), [view?.guide, view?.field]);
  const guideLines = opening === "guide" ? openingSplit.spoken : NO_GUIDES;
  const awakenHero = useMemo(() => heroDoll(view?.field?.hero), [view?.field?.hero]);
  /** 大世界圖這次打開要不要播浮起（打開時決定一次）。 */
  const [atlasRise, setAtlasRise] = useState(false);
  const lesson = view?.lesson ?? null;
  const showLesson = charId !== null && lessonShown(lesson, seenIds);
  /** 配點教完接閃現時，葛蘭先說的那句（#133：「好。接下來看看你剛才用過的那一招。」）。 */
  const [lessonLead, setLessonLead] = useState<{ speaker_zh: string; text_zh: string } | null>(null);
  function closeLesson(open: boolean) {
    if (lesson === null || charId === null) return;
    markSeen([lessonSeenId(lesson.kind)]);
    setLessonLead(null);
    if (open) hudButton("growth");
  }
  /** 配點教學（#133）：推薦配法＝送 `allocate`；自己配＝打開成長面板；之後再說＝葛蘭說「隨時回來找我。」。 */
  function closeAllocate(how: "recommended" | "self" | "skip") {
    if (lesson === null || charId === null) return;
    const speaker = lesson.lines[0]?.speaker_zh ?? "導師";
    const said = how === "skip" ? lesson.skip_zh : lesson.done_zh;
    if (lesson.respec === true) {
      // OB-3／OB-5（#150）：正式選定之後點數已經全部照推薦配好——「維持推薦」不用送配點；略過與上完分開記。
      // 這條路後面不接閃現教學（4 級前不能閃現），葛蘭收尾的那句直接跳在畫面上
      if (said != null && said !== "") pushToast([`${speaker}：${said}`], false);
      markSeen(allocateSeenIds(lesson, how));
      if (how === "self") hudButton("growth");
      return;
    }
    if (said != null && said !== "") setLessonLead({ speaker_zh: speaker, text_zh: said });
    if (how === "recommended" && Object.keys(lesson.recommended ?? {}).length > 0) {
      setClosed((prev) => new Set([...prev, lessonSeenId("allocate")]));
      void run(async () => {
        await api.worldAct(charId, { kind: "allocate", attributes: lesson.recommended ?? {} });
        show(await api.worldAct(charId, hintSeenAction([lessonSeenId("allocate")])));
      });
      return;
    }
    markSeen([lessonSeenId("allocate")]);
    if (how === "self") hudButton("growth");
  }
  const levelUp = view?.level_up ?? null;
  const showLevelUp = levelUp !== null && !closed.has(`level:${levelUp.level}`);
  // OB-5（#150）：靶場整頁的模式——選大類（未完成開局）、正式選定（入門期打完新手前兩步，在葛蘭那裡或主城）
  const rangeKind = rangeMode(view?.opening);
  const choosing = rangeKind === "choose" && !showLevelUp && choosePageShown(choosePage, lesson?.kind === "choose");
  useEffect(() => {
    // 離開能選定的地方（或換角色、選完了）：下次到了再自動打開
    if (rangeKind !== "choose") setChoosePage("auto");
  }, [rangeKind, charId]);
  /** 設定裡的「重新顯示提示」（6F-2b）。 */
  function resetHints() {
    setClosed(new Set());
    act(HINTS_RESET_ACTION);
  }
  /** 戰鬥中出現的提示、「不再顯示提示」：只記紀錄，不更新畫面（戰後同步時一起回來）。 */
  function noteInBattle(action: WorldAction) {
    if (charId === null) return;
    void api.worldAct(charId, action).catch(() => undefined);
  }
  useWorldSounds(view); // AU-2：升級、任務、拿到物品、金幣的介面音
  /** 上一個畫面的實地地圖 ID（`undefined`＝這個角色第一次載入；6B-3 換地圖跳地名用）。 */
  const lastMap = useRef<string | null | undefined>(undefined);
  const [banner, setBanner] = useState<{ name: string; n: number } | null>(null);

  // ---- HUD（6B-5）：單一浮動面板、浮動提示、任務追蹤收合 ----
  const [hudPanel, setHudPanel] = useState<HudPanel | null>(null);
  /** `npc`／`friend` 面板的對象（NPC ID 或影子主人的角色 ID；6B-4）。 */
  const [hudWho, setHudWho] = useState<string | null>(null);
  /** 地圖（M）：區域圖（6C-6）或大世界圖（6D-5）的浮動全畫面面板，和 HUD 面板分開（關掉地圖不動面板）。
   * M 依序：區域圖 → 大世界圖 → 關閉（在主城裡直接開大世界圖）。 */
  const [mapLayer, setMapLayerState] = useState<MapLayer | null>(null);
  const regionRef = useRef<MapLayer | null>(null); // 同步的開關（連按 Esc、M 時不等重新繪製）
  /** 從大世界圖點進去看的別區（`null`＝所在區）。 */
  const [mapRegion, setMapRegion] = useState<string | null>(null);
  const charRef = useRef(charId);
  charRef.current = charId;
  const setMapLayer = useCallback((layer: MapLayer | null, region: string | null = null) => {
    // RT-5 ③：這個角色第一次打開大世界圖時五座島依序浮起（只播一次；減少動態時不播）
    if (layer === "atlas" && regionRef.current !== "atlas") setAtlasRise(takeAtlasRise(charRef.current, reducedMotion()));
    regionRef.current = layer;
    setMapLayerState(layer);
    setMapRegion(region);
  }, []);
  const regionOpen = mapLayer !== null;
  const setRegionOpen = useCallback((open: boolean) => setMapLayer(open ? "region" : null), [setMapLayer]);
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
    if (next.events.length > 0) {
      // 6E-1：走不過去的出口（霧牆）提示用警告框
      const blocked = new Set((next.field?.exits ?? []).map((e) => e.blocked_zh).filter((t): t is string => t != null));
      pushToast(next.events.filter((t) => !blocked.has(t)), false);
      pushToast(next.events.filter((t) => blocked.has(t)), true);
    }
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

  /** 6L-2：送出前等 LLM 的預先生成（閃現、機遇）；回傳 `false`＝玩家取消（不送動作）。 */
  async function waitPregen(id: string, action: WorldAction): Promise<boolean> {
    const body = pregenWaitBody(action);
    if (body === null || llm?.enabled !== true) return true;
    let cancel = () => undefined as void;
    const cancelled = new Promise<"cancel">((resolve) => {
      cancel = () => resolve("cancel");
    });
    let shown = false;
    const timer = window.setTimeout(() => {
      shown = true;
      setPregenWait({ text: pregenWaitText(body), requestId: pregenRequestId(body), status: "wait", cancel });
    }, PREGEN_HINT_DELAY_MS);
    try {
      const done = await Promise.race([api.worldPregenWait(id, body).catch(() => null), cancelled]);
      if (done === "cancel") return false;
      // RT-3：等待動畫有出現時，收成卡框、卡面淡入 0.3 秒再送出（減少動態時直接出卡）
      if (shown && !reducedMotion()) {
        setPregenWait((cur) => (cur === null ? cur : { ...cur, status: "done" }));
        await new Promise((resolve) => window.setTimeout(resolve, WAIT_DONE_MS));
      }
      return true;
    } finally {
      window.clearTimeout(timer);
      setPregenWait(null);
    }
  }

  const act = (action: WorldAction) =>
    void run(async () => {
      if (charId === null) return;
      if (action.kind === "travel") setResult(null);
      if (!(await waitPregen(charId, action))) return;
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
    // OB-5：可以正式選定時，點葛蘭（霧渡鎮）或主城的靶場、工坊師傅＝打開「正式選定」整頁
    if (rangeKind === "choose" && opensChoose(view?.opening?.choice, target.kind === "npc" ? { npc: target.npc } : target.kind === "object" ? { object: target.id } : {})) {
      setChoosePage("open");
      return;
    }
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
    if (target.kind === "object") {
      // 6D-5 主城：橋頭石碑開該區的傳送選單；功能型 NPC 與攤位開既有面板（其他照舊開說明卡）。
      // 6D-R2：照伺服器給的 `stele_region`／`panel`（內容檔），不再寫死物件 ID
      const obj = (view?.field?.situation_objects ?? []).find((o) => o.id === target.id) ?? null;
      const opens = objectHud(obj);
      if (opens !== null) {
        if (opens.who !== null) setHudWho(opens.who);
        setHudPanel(opens.panel);
      } else {
        setHudWho(target.id);
        setHudPanel("object");
      }
      return;
    }
    if (target.kind === "note_stone") {
      setHudPanel("notes");
      return;
    }
    const panel: Partial<Record<string, HudPanel>> = { shop: "shop", smithy: "smithy", enchanter: "smithy", notice_board: "board", mentor: "growth", post: "mail" };
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
    if (target.kind === "friend" || target.kind === "object" || target.kind === "note_stone") return; // 只在實地地圖（HUD 版面）上
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
      setEnded(null);
      setBattle(res.battle);
    });

  /** 開發用（6F-3，`?dev=1`）：Boss 戰直接開打（`&boss=地點`、`&bosslv=等級` 可換；預設雲頂觀、6 級；
   * `&bossai=charge|last`＝先讓 AI 代打到 Boss 蓄力中／剩最後一名敵人，再交給畫面，截圖用）。
   * QK-9b：`&bossregion=區域`（地點在別區）、`&bossface=north|east|south|west`（主角開場朝向，敵人排在那一側）、
   * `&bossopen=summon|form`（開場就放出召喚物／變身成形態）。 */
  const devBoss = () =>
    void run(async () => {
      if (charId === null) return;
      const q = new URLSearchParams(window.location.search);
      const lv = Number(q.get("bosslv") ?? "6");
      const more = { region: q.get("bossregion") ?? undefined, facing: q.get("bossface") ?? undefined, opening: q.get("bossopen") ?? undefined };
      const res = await api.worldDevBoss(charId, q.get("boss") ?? "cloud_summit", Number.isFinite(lv) ? lv : undefined, q.get("bossai") ?? undefined, more);
      setReplay([`${res.title_zh}（不回寫世界）`]);
      setReplayOutcome(undefined);
      setDevFight(true);
      setBattle(res.battle);
    });

  /** 開發用（QK-9b，`?dev=1`）：角色直接搬到某區的城鎮（`&tp=區域`，預設灰燼荒原；拍 NPC 用，主線限制不管）。 */
  const devTeleport = () =>
    void run(async () => {
      if (charId === null) return;
      const q = new URLSearchParams(window.location.search);
      show(await api.worldDevTeleport(charId, q.get("tp") ?? "ashen_waste"));
    });

  const watchReplay = (matchId: string) =>
    void run(async () => {
      if (charId === null) return;
      const res = await api.worldLeagueReplay(charId, matchId);
      setReplay(replayNotes(res));
      setReplayOutcome(res.outcome_zh);
      setBattle(res.battle);
    });

  /** TR-1（#134）：靶場試打（沙盒）——開一場不回寫世界的戰鬥，打完「回到靶場」。 */
  const rangeTrial = (weapon: string, keywords: string[]) =>
    void run(async () => {
      if (charId === null) return;
      const res = await api.worldRangeTrial(charId, weapon, keywords);
      setReplay([`${res.title_zh}＋${res.skills_zh.join("、")}`, SANDBOX_NOTE]);
      setReplayOutcome("試打結束");
      setRangeFight(true);
      setBattle(res.battle);
    });

  /** OB-5（#150 第 1 點）：選大類的「確定出發」（送 `opening_class`）；成功後守印人指示去霧渡鎮。 */
  const confirmClass = (weaponClass: string) =>
    void run(async () => {
      if (charId === null) return;
      const lines = rangeDoneLines(view?.opening);
      show(await api.worldAct(charId, { kind: "opening_class", weapon_class: weaponClass as "melee" | "ranged" | "focus" }));
      clearRangeDraft(charId);
      if (lines.length > 0) setRangeDone({ lines, chosen: false });
    });

  /** OB-5（#150 第 3 點）：正式選定的「確定選這套」（送 `opening_confirm`）；成功後葛蘭收回入門配備，接著出延後的三選一。
   * 被拒（背包放不下等）時原因留在這一頁上。 */
  const confirmChoose = (weapon: string, keywords: string[]) =>
    void run(async () => {
      if (charId === null) return;
      const lines = chooseDoneLines(view?.opening);
      show(await api.worldAct(charId, { kind: "opening_confirm", weapon, keywords }));
      clearRangeDraft(charId);
      setChoosePage("auto");
      if (lines.length > 0) setRangeDone({ lines, chosen: true });
    });

  async function backToMap() {
    setError(null);
    try {
      const synced = ended?.view ?? null;
      if (synced !== null) show(synced);
      else if (charId !== null) show(await api.world(charId));
      setBattle(null);
      setReplay(null);
      setEnded(null);
      setDevFight(false);
      setRangeFight(false);
    } catch (e) {
      setError(errorText(e));
    }
  }

  /** 戰鬥播完（6F-1）：同步一次拿戰後結算（經驗、戰利品、任務）；循環賽重播不用。失敗時回到地點圖再讀。 */
  const onBattleEnded = useCallback(() => {
    if (replay !== null || charId === null) return;
    setEnded({ view: null });
    api.world(charId).then(
      (v) => setEnded({ view: v }),
      () => setEnded(null),
    );
  }, [replay, charId]);

  // ---- 郵寄（6T-1b） ----
  const mailApi = useMemo<MailApi | null>(() => {
    if (charId === null) return null;
    return {
      mail: () => api.worldMail(charId),
      recipients: () => api.mailRecipients(charId),
      quote: (body) => api.mailQuote(charId, body),
      send: (body) => api.mailSend(charId, body),
      claim: (letter) => api.mailClaim(charId, letter),
      refuse: (letter) => api.mailRefuse(charId, letter),
    };
  }, [charId]);
  /** 郵寄之後重抓世界畫面（金幣、背包、郵差頭上的「✉」）。 */
  const refreshWorld = async () => {
    if (charId === null) return;
    try {
      show(await api.world(charId));
    } catch (e) {
      setError(errorText(e));
    }
  };

  // ---- HUD（6B-5） ----
  const hudMode = battle === null && view !== null && mapPaneKind(view) === "field";
  // TR-1：靶場畫面（未完成開局）時舞台不在畫面上，確定出發之後要重新量（`opening` 進 dep）
  const stage = useHudStage(hudMode, `${error ?? ""}|${llm?.notice_zh ?? ""}|${view === null ? "" : "v"}|${rangeKind === "class" || choosing ? "range" : ""}`);
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
    if (b.id === "sneak" && view !== null) {
      // 6C-5 潛行：按了就送（花補給，到下一張地圖為止）；不能開時說原因
      const s = sneakState(view);
      if (s.active || s.problem !== null) pushToast([`${b.name}：${s.status}`], s.problem !== null);
      else act({ kind: "sneak" });
      return;
    }
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
  const hudKeys = useRef({
    active: false,
    locked: false,
    button: hudButton,
    close: closeHud,
    map: () => undefined as void,
    closeRegion: () => undefined as void,
  });
  hudKeys.current = {
    active: hudMode,
    locked: panelLocked,
    button: hudButton,
    close: closeHud,
    map: () => {
      if (view === null) return;
      setMapLayer(nextMapLayer(regionRef.current, view.map));
    },
    closeRegion: () => setRegionOpen(false),
  };
  useEffect(() => {
    if (!hudMode && regionOpen) setRegionOpen(false); // 進戰鬥、離開實地地圖就收起區域圖
  }, [hudMode, regionOpen, setRegionOpen]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const h = hudKeys.current;
      if (!h.active) return;
      const k = hudKey(e, typingInto(e.target));
      if (k === null) return;
      if (k.kind === "escape") return; // 由下面的捕獲階段處理
      if (e.repeat) return;
      e.preventDefault();
      if (k.kind === "map") h.map();
      else if (!regionRef.current) h.button(k.id); // 區域圖開著時只認 M、Esc
    };
    // 6F-1（U16）：Esc 在捕獲階段處理。面板裡的按鈕說明卡（滑過顯示的浮動卡）會在 document 上吃掉 Esc，
    // 原本滑鼠停在「接任務」之類的按鈕上時 Esc 關不掉 NPC 對話框；釘住的浮動卡照舊先關卡片。
    const onEscape = (e: KeyboardEvent) => {
      const h = hudKeys.current;
      if (!h.active || e.key !== "Escape") return;
      if (document.querySelector(".float-card.pinned") !== null) return;
      if (regionRef.current) h.closeRegion();
      else if (!h.locked) h.close();
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("keydown", onEscape, true);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("keydown", onEscape, true);
    };
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
      case "object":
        return hudWho === null ? null : <FieldObjectCard key={hudWho} view={v} object={hudWho} busy={busy} onAct={act} onClose={closeHud} />;
      case "stele":
        return hudWho === null ? null : <SteleMenu key={hudWho} view={v} region={hudWho} busy={busy} onAct={act} onClose={closeHud} />;
      case "pavilion":
        return <PavilionPanel view={v} busy={busy} onAct={act} onPanel={(p) => setHudPanel(p)} />;
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
      case "mail":
        return mailApi === null ? null : <MailPanel key={charId} mailApi={mailApi} inventory={v.inventory ?? null} busy={busy} onChanged={() => void refreshWorld()} />;
      default:
        return null;
    }
  }

  function layoutOf(v: WorldView) {
    const folded = trackerFolded || (narrow && !narrowOpen);
    return { folded, layout: hudLayout(stage.width, stage.height, { mates: mateCards(v).length, narrow, collapsed: folded }) };
  }

  function renderHud(v: WorldView) {
    const field = v.field;
    if (field == null) return null;
    const { folded, layout } = layoutOf(v);
    const insets = hudInsets(layout, stage); // 6F-3：鏡頭避開 HUD
    const cam = fieldCam ?? followCamera(stage, field, field.me, FIELD_SCALE, insets);
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
          hud={{ width: stage.width, height: stage.height, frame: battleFrame(v), insets, onCamera: onFieldCamera, avoid: hudAvoidRects(layout, stage), reach: hudReach(layout, stage), columns: hudColumnRects(layout) }}
          guides={guideLines}
          hideMail={shown === "mail"}
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
          onPlace={() => setHudPanel((cur) => togglePanel(cur, "place"))}
          openPanel={shown}
          panel={shown === null ? null : hudPanelContent(v)}
          panelLocked={panelLocked}
          onClosePanel={closeHud}
          onResetHints={resetHints}
          mapOpen={regionOpen}
          onCloseMap={() => setRegionOpen(false)}
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
        {mapLayer === "region" && (
          <RegionMap
            map={(mapRegion !== null && v.atlas != null ? atlasMapOf(v.atlas, v.map, mapRegion) : null) ?? v.map}
            busy={busy}
            onTeleport={(to) => {
              setRegionOpen(false);
              act({ kind: "use_teleport_stone", to });
            }}
            onAtlas={v.atlas != null ? () => setMapLayer("atlas") : undefined}
            onClose={() => setRegionOpen(false)}
          />
        )}
        {mapLayer === "atlas" && v.atlas != null && (
          <AtlasMap
            atlas={v.atlas}
            map={v.map}
            busy={busy}
            rise={atlasRise}
            onOpenRegion={(r) => setMapLayer("region", r === v.map.region ? null : r)}
            onTeleport={(region) => {
              setRegionOpen(false);
              act({ kind: "teleport", region });
            }}
            onClose={() => setRegionOpen(false)}
          />
        )}
      </div>
    );
  }

  if (battle !== null) {
    return (
      <BattleScreen
        key={battle.battle_id}
        initial={battle}
        onExit={() => void backToMap()}
        exitLabel={rangeFight ? "回到靶場" : replay !== null && !devFight ? "回到循環賽" : "回到地點圖"}
        openingNotes={replay ?? view?.encounter?.opening_zh}
        endTitle={replay !== null ? replayOutcome : undefined}
        placeName={rangeFight ? rangePlaceName(view?.opening?.capital_zh) : replay !== null ? null : worldPlaceName(view)}
        onEnded={onBattleEnded}
        heroOrigin={replay !== null && !devFight ? null : (view?.character.origin_realm ?? null)}
        endSummary={replay !== null || ended === null ? undefined : ended.view === null ? null : battleSummary(ended.view)}
        hints={
          replay !== null || charId === null
            ? undefined
            : {
                characterId: charId,
                hints: view?.battle_hints ?? [],
                seen: [...seenIds],
                off: hintState.off,
                onSeen: (id) => noteInBattle(hintSeenAction([id])),
                onOff: () => noteInBattle(HINTS_OFF_ACTION),
              }
        }
      />
    );
  }
  if (charId === null) {
    return <WorldCharacterPicker onEnter={enter} onHome={onHome} onLogin={onLogin} onLogout={onLogout} />;
  }
  // TR-1（#134）／OB-5（#150）：還在選大類＝停在主城工坊靶場（醒來那張卡「站起來」之後；中途離開回來也停在這裡）；
  // 入門期可以正式選定時，葛蘭（霧渡鎮）與主城靶場開同一個整頁，按「之後再選」回到世界畫面
  if (view !== null && view.opening != null && !shouldShowOpening(view.guide, seenIds) && (rangeKind === "class" || choosing) && !shouldShowAbsence(absence)) {
    return (
      <RangeScreen
        view={view}
        range={view.opening}
        mode={rangeKind === "class" ? "class" : "choose"}
        busy={busy}
        error={error}
        onCloseError={() => setError(null)}
        onTrial={rangeTrial}
        onClass={confirmClass}
        onConfirm={confirmChoose}
        onHome={onHome}
        onLater={() => {
          setError(null);
          setChoosePage("closed");
        }}
      />
    );
  }
  return (
    <div className={`run-screen world-screen${hudMode ? " hud-mode" : ""}`}>
      <header className="run-header">
        {/* 6F-1：「大世界（測試）」與本機模型勾選框只在開發模式（`?dev=1`）；正式畫面標題是區域名 */}
        <h1>
          {devMode ? (
            <>
              大世界（測試）　<span className="muted small">{view === null ? "" : `${view.map.name_zh}（${view.map.level_zh}）`}</span>
            </>
          ) : (
            <>
              {view?.map.name_zh ?? ""}　<span className="muted small">{view === null ? "" : view.map.level_zh}</span>
            </>
          )}
        </h1>
        <div className="run-header-buttons">
          {narratorResting(llm) && (
            <span className="world-narrator-rest small" role="status" data-testid="world-narrator-rest">
              說書人休息中（使用固定文字）
            </span>
          )}
          {devMode && llm !== null && (
            <label className="world-llm small" data-testid="world-llm">
              <input type="checkbox" checked={llm.enabled} disabled={busy} onChange={(e) => toggleLlm(e.target.checked)} />
              說書人用本機模型
              <span className="muted">（伺服器預設{llm.default ? "開" : "關"}）</span>
            </label>
          )}
          {devMode && (
            <button type="button" onClick={devBoss} disabled={busy} data-testid="world-dev-boss">
              頭目戰（開發）
            </button>
          )}
          {devMode && (
            <button type="button" onClick={devTeleport} disabled={busy} data-testid="world-dev-teleport">
              傳送（開發）
            </button>
          )}
          {rangeKind === "choose" && !choosing && (
            // OB-5：按了「之後再選」之後，人還在葛蘭那裡或主城時，頂列留一顆鈕可以再打開（點葛蘭／靶場也行）
            <button type="button" className="primary" onClick={() => setChoosePage("open")} disabled={busy} data-testid="world-choose-open">
              {CHOOSE_OPEN_LABEL}
            </button>
          )}
          <button type="button" onClick={leaveChar} data-testid="world-switch-char">
            切換角色
          </button>
          <button type="button" onClick={onHome} data-testid="world-home">
            回到首頁
          </button>
        </div>
      </header>
      <ErrorBanner message={error} onClose={() => setError(null)} />
      {/* UI-E1 追加 2：有 HUD 時，詢問視窗照 6F-3 避開四角 HUD（上緣在主角卡下方、下緣停在功能列上方） */}
      <DialogHudBox.Provider value={view !== null && view.field != null && hudMode ? dialogBox(layoutOf(view).layout, stage.top) : null}>
      {view !== null && shouldShowAbsence(absence) && <AbsenceDialog view={absence} busy={busy} onClose={closeAbsence} />}
      {view !== null && !shouldShowAbsence(absence) && shouldShowOpening(view.guide, seenIds) &&
        (view.field != null ? (
          <AwakenDialog
            lines={openingSplit.narrator}
            hero={awakenHero}
            open={openRegionsOf(view.atlas)}
            place={view.field.name_zh}
            onStand={() => markSeen([OPENING_SEEN])}
          />
        ) : (
          <OpeningDialog guide={view.guide} onClose={() => markSeen([OPENING_SEEN])} />
        ))}
      {view !== null && rangeDone !== null && (
        <RangeDoneDialog lines={rangeDone.lines} heading={rangeDone.chosen ? "正式選定" : "工坊靶場"} closeLabel={rangeDone.chosen ? "好" : "出發"} onClose={() => setRangeDone(null)} />
      )}
      {view !== null && !shouldShowAbsence(absence) && !shouldShowOpening(view.guide, seenIds) && showLevelUp && levelUp !== null && (
        <LevelUpDialog levelUp={levelUp} onClose={() => markSeen([], levelUp.level)} />
      )}
      {view !== null && !shouldShowAbsence(absence) && !shouldShowOpening(view.guide, seenIds) && !showLevelUp && showLesson && lesson !== null && lesson.kind === "allocate" && (
        <AllocateLessonDialog
          lesson={lesson}
          affects={view.hero.attribute_affects ?? []}
          busy={busy}
          onRecommended={() => closeAllocate("recommended")}
          onSelf={() => closeAllocate("self")}
          onSkip={() => closeAllocate("skip")}
        />
      )}
      {view !== null && !shouldShowAbsence(absence) && !shouldShowOpening(view.guide, seenIds) && !showLevelUp && showLesson && lesson !== null && lesson.kind !== "allocate" && lesson.kind !== "choose" && (
        <LessonDialog lesson={lesson} lead={lessonLead} onOpen={() => closeLesson(true)} onSkip={() => closeLesson(false)} />
      )}
      {pregenWait !== null && <PregenWaitDialog text={pregenWait.text} requestId={pregenWait.requestId} status={pregenWait.status} waitedMs={PREGEN_HINT_DELAY_MS} onCancel={pregenWait.cancel} />}
      </DialogHudBox.Provider>
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
              <WorldField view={view} busy={busy} send={sendField} commit={show} onInteract={interact} guides={guideLines} />
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
