// 公告板分頁版的純函式（PNL-1b；docs/art/資訊面板-移植需求.md 3.3「公告板」、4.1 #1～#12、#37～#39、#42、#44）：
// 分頁定義的字與記號、固定區的「下一個」、賽季時間軸的格子（樣張 `infoPanels.js` 的 `timeline()`）。元件在 `BoardPanes.tsx`、`SeasonTimeline.tsx`。
import type {
  BoardBountyView,
  BoardGoalView,
  BoardMilestoneView,
  BoardPhaseView,
  BoardSeasonBossView,
  BoardWorldEventView,
  SeasonInfoView,
} from "../api/types";
import type { TabBadgeSpec } from "../ui/panelTabRules";

// ---------------- 新字（4.1） ----------------

/** 五個分頁：全名沿用原區塊名，短名是 #37 新字。 */
export const BOARD_TABS = {
  goals: { label: "今日目標", short: "目標" },
  bounty: { label: "懸賞板", short: "懸賞" },
  sched: { label: "賽季時程", short: "時程" },
  events: { label: "世界事件", short: "事件" },
  boss: { label: "賽季頭目", short: "頭目" },
} as const;
export type BoardTabId = keyof typeof BOARD_TABS;

export const BOARD_ZH = {
  title: "公告板",
  next: "下一個", // #3
  goalLinePrefix: "完成一條", // #5（＋代幣圖示＋「+N」）
  bountyFirst: "先搶先贏", // #6
  bountyCols: ["目標・地點", "建議等級", "獎勵", "狀態"] as const, // #7
  eventsLine: "全服一起推進", // #9
  bossRules: "挑戰規則與評分榜", // #12
  bossNobody: "還沒有人打倒", // #12（摺起來右邊）
  timelineRows: ["時間點", "天", "階段", "世界事件"] as const, // #4
  cleared: "已清空",
  worldChanges: "世界變化",
} as const;

/** 懸賞第一行右邊「每天 06:00 換一批」（#6）。 */
export const bountyRefreshText = (season: Pick<SeasonInfoView, "refresh_time_zh">): string =>
  season.refresh_time_zh != null && season.refresh_time_zh !== "" ? `每天 ${season.refresh_time_zh} 換一批` : "每天換一批";

/** 懸賞的規則句（字不變，進 (i)）。 */
export const bountyRuleText = (season: Pick<SeasonInfoView, "next_refresh_zh">): string => `先打倒的人拿走當天的懸賞（${season.next_refresh_zh}）。`;

/** 完整日程摺疊的標題（#3），例「完整日程（6 個時間點、5 個階段）」。 */
export const fullScheduleText = (season: Pick<SeasonInfoView, "milestones" | "phases">): string =>
  `完整日程（${(season.milestones ?? []).length} 個時間點、${(season.phases ?? []).length} 個階段）`;

/** 「（明天）」「（N 天後）」（#3）；今天或已過＝空字串。 */
export function daysAwayText(day: number, today: number): string {
  const n = day - today;
  if (n <= 0) return "";
  return n === 1 ? "（明天）" : `（${n} 天後）`;
}

// ---------------- 分頁記號（#38、#39、#42） ----------------

/** 今日目標：細框「完成幾條／總條數」（#38），滑過「今日目標完成 0／3」。沒有目標＝不掛。 */
export function goalsBadge(goals: readonly BoardGoalView[]): TabBadgeSpec | null {
  if (goals.length === 0) return null;
  const text = `${goals.filter((g) => g.done).length}／${goals.length}`;
  return { kind: "p", value: text, hint: `${BOARD_TABS.goals.label}完成 ${text}` };
}

/** 懸賞：金底「還能搶的條數」（#39），滑過「懸賞中 3」；0 條＝不掛。 */
export function bountyBadge(bounties: readonly BoardBountyView[]): TabBadgeSpec | null {
  const n = bounties.filter((b) => b.open).length;
  return n === 0 ? null : { kind: "n", value: n, hint: `懸賞中 ${n}` };
}

/** 世界事件：有進行中的掛綠點，滑過「霧潮入侵 進行中」（多個用「、」接）。 */
export function eventsBadge(events: readonly BoardWorldEventView[]): TabBadgeSpec | null {
  const live = events.filter((e) => e.status === "active");
  if (live.length === 0) return null;
  return { kind: "live", hint: `${live.map((e) => e.name_zh).join("、")} ${live[0]!.status_zh}` };
}

/** 賽季頭目：封印中掛金鎖（滑過「封印中」）；其他狀態不掛（純資訊）。 */
export function bossBadge(boss: Pick<BoardSeasonBossView, "status" | "status_zh">): TabBadgeSpec | null {
  return boss.status === "sealed" ? { kind: "lock", hint: boss.status_zh } : null;
}

// ---------------- 標籤的樣子 ----------------

/** 懸賞狀態標籤：懸賞中＝實心金、自己搶下＝正面綠細框、被別人搶下＝淡灰。 */
export function bountyTone(b: Pick<BoardBountyView, "open" | "claimed_by" | "status_zh">): "open" | "mine" | "dim" {
  if (b.open) return "open";
  return b.claimed_by == null || b.status_zh === "你搶下了" ? "mine" : "dim";
}

/** 世界事件狀態標籤：進行中＝綠底、成功＝綠細框、尚未開始與失敗＝淡灰。 */
export function eventTone(status: BoardWorldEventView["status"]): "live" | "mine" | "dim" {
  if (status === "active") return "live";
  return status === "succeeded" ? "mine" : "dim";
}

/** 賽季頭目狀態標籤：封印中＝鎖住色（帶金鎖）、開放＝實心金、其他＝淡灰。 */
export function bossTone(status: BoardSeasonBossView["status"]): "lock" | "open" | "dim" {
  if (status === "sealed") return "lock";
  return status === "open" ? "open" : "dim";
}

/** 世界事件的紋章（2.3）：有區域＝那一區的 HUD 紋章（`crestId`），沒有（封印共鳴）＝源晶 `r_source`。 */
export const eventCrestRegion = (e: Pick<BoardWorldEventView, "region">): string | null => (e.region != null && e.region !== "" ? e.region : null);

// ---------------- 固定區：下一個 ----------------

/** 「下一個」：今天以後最近的一天（同一天有幾個時間點就全部列，名字用「；」接）；沒有＝null。 */
export function nextMilestone(season: Pick<SeasonInfoView, "day" | "milestones">): { day: number; names: string[] } | null {
  const later = (season.milestones ?? []).filter((m) => m.day > season.day);
  if (later.length === 0) return null;
  const day = Math.min(...later.map((m) => m.day));
  return { day, names: later.filter((m) => m.day === day).map((m) => m.name_zh) };
}

/** 賽季進行中才有「第 N 天」大字（開賽前、季末照舊寫 `status_zh`）。 */
export const seasonRunning = (season: Pick<SeasonInfoView, "status">): boolean => season.status === "running";

// ---------------- 賽季時間軸（樣張 `timeline()`：14 格 × 5 列） ----------------

export type MilestoneKind = BoardMilestoneView["kind"];

/** 一天的釘：那天全部時間點的種類（去重、照出現順序）與名字。 */
export interface TimelinePin {
  day: number;
  kinds: MilestoneKind[];
  names: string[];
  /** 下一個（亮金圈）。 */
  next: boolean;
  past: boolean;
}

export interface TimelineSeg {
  phase: BoardPhaseView;
  now: boolean;
  /** 隔一段換淡一點的底（樣張 `c2`）。 */
  alt: boolean;
}

export interface TimelineEvent {
  event: BoardWorldEventView;
  /** 第幾列（0 起；重疊的排到下一列）。 */
  lane: number;
  now: boolean;
}

export interface TimelineLayout {
  days: number;
  today: number | null;
  pins: TimelinePin[];
  segs: TimelineSeg[];
  events: TimelineEvent[];
  /** 世界事件佔幾列（至少 1）。 */
  lanes: number;
}

const kindsOf = (m: BoardMilestoneView): MilestoneKind[] => (m.kinds != null && m.kinds.length > 0 ? [...m.kinds] : [m.kind ?? "other"]);

/** 釘的圖示（第 5 節第 7 點，美術建議）：劇情技能＝說書人、頭目解鎖＝金鎖、循環賽＝影子；沒對照的＝沙漏。 */
export function pinIcon(kind: MilestoneKind): "narrator" | "lock" | "shadow" | "hourglass" {
  if (kind === "story_skill") return "narrator";
  if (kind === "boss_unlock") return "lock";
  if (kind === "league") return "shadow";
  return "hourglass";
}

/**
 * 時間軸的格子：釘（每天一個，圖示＝那天全部種類）、今天、階段（今天所在的金色）、世界事件（依開始天、ID 排，
 * 和前一列重疊的排到下一列；進行中＝綠底）。世界事件的「進行中」看伺服器的 `status`，不自己用天數算。
 */
export function timelineLayout(season: Pick<SeasonInfoView, "day" | "days" | "status" | "milestones" | "phases">, worldEvents: readonly BoardWorldEventView[]): TimelineLayout {
  const days = Math.max(1, season.days);
  const running = seasonRunning(season);
  const today = running && season.day >= 1 && season.day <= days ? season.day : null;
  const next = running ? nextMilestone(season) : null;
  const byDay = new Map<number, TimelinePin>();
  for (const m of [...(season.milestones ?? [])].sort((a, b) => a.day - b.day)) {
    if (m.day < 1 || m.day > days) continue;
    const pin = byDay.get(m.day) ?? { day: m.day, kinds: [], names: [], next: next?.day === m.day, past: today !== null && m.day < today };
    for (const k of kindsOf(m)) if (!pin.kinds.includes(k)) pin.kinds.push(k);
    pin.names.push(m.name_zh);
    byDay.set(m.day, pin);
  }
  const segs = (season.phases ?? []).map((phase, i) => ({ phase, now: today !== null && phase.start_day <= today && today <= phase.end_day, alt: i % 2 === 1 }));
  const sorted = [...worldEvents]
    .filter((e) => e.start_day >= 1 && e.end_day >= e.start_day)
    .sort((a, b) => a.start_day - b.start_day || (a.event < b.event ? -1 : a.event > b.event ? 1 : 0));
  const laneEnd: number[] = [];
  const events = sorted.map((event) => {
    let lane = laneEnd.findIndex((end) => end < event.start_day);
    if (lane === -1) {
      lane = laneEnd.length;
      laneEnd.push(0);
    }
    laneEnd[lane] = event.end_day;
    return { event, lane, now: event.status === "active" };
  });
  return { days, today, pins: [...byDay.values()], segs, events, lanes: Math.max(1, laneEnd.length) };
}

/** CSS grid 的欄（第 0 欄是列名，第 d 天在第 d + 1 欄）：`a / b` 跨到 b 天（含）。 */
export const dayColumns = (from: number, to: number): string => `${from + 1} / ${to + 2}`;
