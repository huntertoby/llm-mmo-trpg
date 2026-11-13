// 地圖上的戰鬥回饋（Phase 3-9a，純函式）：一步的事件 → 回饋項目（浮動數字、字樣、行動連線、狀態彈出）。
// 畫布（`render/BattleRenderer.ts`）只負責把項目畫出來；位置一律由該步的 `view` 取得單位所在格。
// 位移（推、拉、衝鋒、跳躍、傳送、交換）不在這裡，見 `animation.ts`。
import { asEvent, type BattleView, type EventBase, type Pos } from "../api/types";
import { posKey, samePos } from "./geometry";
import { statusLook, statusName } from "./glossary";

/** 浮動文字的語氣（決定顏色）：傷害紅、治療綠、護盾淺藍、字樣白、壞字樣橘、好字樣黃。 */
export type FloatTone = "damage" | "heal" | "shield" | "text" | "bad" | "good";

export interface FloatItem {
  kind: "float";
  pos: Pos;
  text: string;
  tone: FloatTone;
  /** 暴擊等要放大的數字。 */
  big: boolean;
  /** 同一格同一步的第幾個（0 起）；畫布依序往上錯開並延後出現，避免重疊。 */
  slot: number;
}

export interface LineItem {
  kind: "line";
  from: Pos;
  to: Pos;
}

export interface StatusItem {
  kind: "status";
  pos: Pos;
  /** 狀態的中文名稱。 */
  text: string;
  slot: number;
}

/** RG-3：敵人放陷阱時「看那一格一眼」（放置者頭上的小泡泡，0.6 秒）。 */
export interface GlanceItem {
  kind: "glance";
  /** 放置者所在格。 */
  pos: Pos;
  unitId: string;
  /** 陷阱那一格。 */
  to: Pos;
}

export type FeedbackItem = FloatItem | LineItem | StatusItem | GlanceItem;

/** 事件型別 → 固定字樣（對照表放這一處；有條件的字樣在 `textFor` 內判斷）。 */
export const EVENT_WORDS: Readonly<Record<string, { text: string; tone: FloatTone }>> = {
  collided: { text: "撞擊！", tone: "bad" },
  unit_fell: { text: "墜落", tone: "bad" },
  entered_deadly_terrain: { text: "致命地形", tone: "bad" },
  status_resisted: { text: "抵抗", tone: "text" },
  push_resisted: { text: "抵抗", tone: "text" },
  unit_downed: { text: "擊倒", tone: "bad" },
  death_cheated: { text: "死裡逃生", tone: "good" },
  unit_revived: { text: "復活", tone: "good" },
  turn_skipped: { text: "無法行動", tone: "bad" },
  attack_intercepted: { text: "攔截", tone: "good" },
};

/** 特殊結果的字樣（6N-5；去文字化原則：之後有圖示時可換掉，現在先寫字）。 */
export const WORD_CRIT = "暴擊";
export const WORD_BLOCK = "格擋";
export const WORD_DODGE = "閃避";
/** 目標不能動（冰凍、暈眩、倒地、定身）時沒打中的字樣（6N-6，美術 PM 6N-5 驗收）：不是閃開的，照舊寫「失手」。 */
export const WORD_MISS = "失手";
/** RG-3：瞄準預告落空（目標倒下、出射程、斷視線、隱蔽）、被隊友擋下、瞄準中被近戰打斷（美術 PM：三個都用 good 黃）。 */
export const WORD_LOCK_MISS = "落空";
export const WORD_LOCK_BLOCKED = "被擋下";
export const WORD_LOCK_INTERRUPTED = "被打斷";
/** 頭目部位破了（PB-1c 占位演出，T16）：「{部位} 破！」。 */
export const partBrokenWord = (name: string): string => `${name} 破！`;

/**
 * 躺在地上的姿勢（6R-F）：`prone` 在狀態資料裡沒有「不能動」的標記（倒地只是移動前要先站起來），
 * 但小人畫成躺著（`unitSprite.PRONE`，畫法用的姿勢 ID），閃不開。資料沒有可用標記，先照畫法留這一個（見 6R-F 報告待決）。
 */
export const IMMOBILE_POSTURES: readonly string[] = ["prone"];

/**
 * 不能動的狀態（6R-F 起讀資料，守則 4）：glossary 的 `status_look` 有 `skip_turn`（冰凍、暈眩、石化…）或
 * `prevents_move`（定身…），再加上躺著的姿勢。這些人沒被打中時不播閃避片段、字樣寫「失手」。
 */
export function isImmobileStatus(statusId: string): boolean {
  if (IMMOBILE_POSTURES.includes(statusId)) return true;
  const look = statusLook(statusId);
  return look?.skip_turn === true || look?.prevents_move === true;
}

/** 畫面資料裡這個人身上有不能動的狀態。 */
export function immobileIn(view: BattleView): (id: unknown) => boolean {
  const stuck = new Set(view.units.filter((u) => (u.statuses ?? []).some((x) => isImmobileStatus(x.status_id))).map((u) => u.id));
  return (id) => typeof id === "string" && stuck.has(id);
}

/** 某個事件發生的那一刻，某人能不能動（6F-6）。 */
export type Immobility = (e: EventBase, id: unknown) => boolean;

/** 只看一張畫面資料（6N-6 的做法；沒有步前畫面時的退路）。 */
export function immobilityIn(view: BattleView): Immobility {
  const still = immobileIn(view);
  return (_e, id) => still(id);
}

/**
 * 照事件順序判斷「打的那一刻」能不能動（6F-6，巡檢 bug 9 的逐處檢查）：從步前的畫面資料開始，
 * 一路套上這一步的 `status_applied`、`status_removed`、`status_converted`。只看步後畫面會判錯兩種情況：
 * 同一步先沒打中、後面才被打倒或凍住（寫成失手，應該是閃避）；同一步先站起來或解凍、後面才沒打中（反過來）。
 * 查詢用事件的 `seq`（停頓時已跳過的事件從清單拿掉後仍查得到）；查不到 `seq` 時用步後的狀態。
 */
export function immobilityOf(events: readonly Record<string, unknown>[], before: BattleView): Immobility {
  const has = new Map<string, Set<string>>(before.units.map((u) => [u.id, new Set((u.statuses ?? []).map((s) => s.status_id))]));
  const stuck = () => new Set([...has.entries()].filter(([, ids]) => [...ids].some(isImmobileStatus)).map(([id]) => id));
  const bySeq = new Map<number, Set<string>>();
  let now = stuck();
  for (const raw of events) {
    const e = asEvent(raw);
    if (typeof e.seq === "number") bySeq.set(e.seq, now);
    const target = typeof e.target_id === "string" ? e.target_id : null;
    if (target === null) continue;
    const ids = has.get(target) ?? new Set<string>();
    if (e.type === "status_applied") ids.add(String(e.status_id));
    else if (e.type === "status_removed") ids.delete(String(e.status_id));
    else if (e.type === "status_converted") ids.add(String(e.to_status));
    else continue;
    has.set(target, ids);
    now = stuck();
  }
  const last = now;
  return (e, id) => typeof id === "string" && (typeof e.seq === "number" ? (bySeq.get(e.seq) ?? last) : last).has(id);
}

interface Spot {
  pos: Pos | null;
  text: string;
  tone: FloatTone;
  big?: boolean;
}

type Locate = (id: unknown) => Pos | null;

const num = (v: unknown): number => (typeof v === "number" ? v : 0);

function posOf(v: unknown): Pos | null {
  if (typeof v === "object" && v !== null && "x" in v && "y" in v) return v as Pos;
  return null;
}

function attackSpots(e: EventBase, at: Locate, immobile: (id: unknown) => boolean): Spot[] {
  const target = at(e.target_id);
  // 6N-5：閃避成功寫「閃避」（之前是攻擊者角度的「失手」；之後有圖示時可換掉）
  if (e.hit !== true) return [{ pos: target, text: immobile(e.target_id) ? WORD_MISS : WORD_DODGE, tone: "text" }];
  const spots: Spot[] = [];
  if (num(e.backstab) > 0) spots.push({ pos: target, text: "背刺！", tone: "good", big: true });
  if (num(e.ambush) > 0) spots.push({ pos: target, text: "伏擊！", tone: "good", big: true });
  return spots;
}

/**
 * RG-3：瞄準預告落空（`effect_fizzled` 的 `lock_on_*`）。字一律不放在目標頭上（隱蔽造成的落空會洩漏位置）：
 * 「被擋下」在擋住的那個隊友頭上（伺服器 `lock_blocker_id`；找不到時退回弓手），其他「落空」在弓手頭上（`lock_caster_id`）。
 * RG-3b：AF-1 起擋在中間的人能選到時改打他（`lock_intercepted`，見 `interceptSpots`），這裡的 `lock_on_blocked`
 * 只剩「擋住的人本身選不到」（例如 2 格外的隱蔽）。
 */
function lockFizzleSpots(e: EventBase, at: Locate): Spot[] {
  if (typeof e.reason !== "string" || !e.reason.startsWith("lock_on")) return [];
  const caster = at(e.lock_caster_id);
  if (e.reason === "lock_on_blocked") return [{ pos: at(e.lock_blocker_id) ?? caster, text: WORD_LOCK_BLOCKED, tone: "good" }];
  return [{ pos: caster, text: WORD_LOCK_MISS, tone: "good" }];
}

/**
 * RG-3b：瞄準預告被隊友擋下、改打擋住的人（AF-1 的 `lock_intercepted`，事件自帶 `blocker_id`）→「被擋下」放在
 * 擋下的人頭上（緊接著是對他的命中與傷害浮字）。找不到擋下的人時不顯示（不退回目標頭上）。
 */
function interceptSpots(e: EventBase, at: Locate): Spot[] {
  const blocker = at(e.blocker_id);
  return blocker === null ? [] : [{ pos: blocker, text: WORD_LOCK_BLOCKED, tone: "good" }];
}

/** 一個事件 → 要在地圖上顯示的浮動文字（沒有對應回饋回傳空陣列）。 */
function textFor(e: EventBase, at: Locate, immobile: (id: unknown) => boolean): Spot[] {
  const amount = num(e.amount);
  switch (e.type) {
    case "attack_rolled":
      return attackSpots(e, at, immobile);
    case "damage_dealt": {
      // 6N-5：暴擊的數字放大、寫「暴擊」；格擋成功（`block_permille < 1000`）另跳「格擋」
      if (amount <= 0) return [];
      const crit = e.crit === true;
      const hit: Spot = { pos: at(e.target_id), text: crit ? `${WORD_CRIT} −${amount}` : `−${amount}`, tone: "damage", big: crit };
      const blocked = typeof e.block_permille === "number" && e.block_permille < 1000;
      return blocked ? [{ pos: at(e.target_id), text: WORD_BLOCK, tone: "good" }, hit] : [hit];
    }
    case "damage_redirected":
      return amount > 0 ? [{ pos: at(e.to_id), text: `−${amount}`, tone: "damage" }] : [];
    case "healed":
      return amount > 0 ? [{ pos: at(e.target_id), text: `＋${amount}`, tone: "heal" }] : [];
    case "shield_gained":
      return amount > 0 ? [{ pos: at(e.unit_id), text: `＋${amount}盾`, tone: "shield" }] : [];
    case "shield_absorbed":
      return num(e.absorbed) > 0 ? [{ pos: at(e.unit_id), text: `吸收 ${num(e.absorbed)}`, tone: "shield" }] : [];
    case "object_damaged":
      return amount > 0 ? [{ pos: posOf(e.pos), text: `−${amount}`, tone: "damage" }] : [];
    case "maneuver_rolled":
      return e.success === true ? [] : [{ pos: at(e.target_id), text: "抵抗", tone: "text" }];
    case "reaction_triggered":
      return e.reaction === "block" ? [{ pos: at(e.unit_id), text: WORD_BLOCK, tone: "good" }] : [];
    case "part_broken":
      // PB-1c（T16 占位）：部位破了跳「拂塵 破！」（放大、醒目）
      return typeof e.name_zh === "string" ? [{ pos: at(e.target_id), text: partBrokenWord(e.name_zh), tone: "bad", big: true }] : [];
    case "effect_fizzled":
      return lockFizzleSpots(e, at);
    case "lock_intercepted":
      return interceptSpots(e, at);
    case "followup_cancelled":
      // RG-3：瞄準中被近戰打中，瞄準取消（字在弓手頭上）
      return e.reason === "interrupted" ? [{ pos: at(e.unit_id), text: WORD_LOCK_INTERRUPTED, tone: "good" }] : [];
    case "unit_ran":
      // 跑步（UI-T1：使用者「啟用跑步應該要有 ui 文字跳」）：跑的人頭上跳「跑步 移動＋N」
      return [{ pos: at(e.unit_id), text: num(e.bonus) > 0 ? `跑步 移動＋${num(e.bonus)}` : "跑步", tone: "good" }];
    default: {
      const word = EVENT_WORDS[e.type];
      if (word === undefined) return [];
      return [{ pos: at(e.unit_id ?? e.target_id) ?? posOf(e.pos), ...word, big: e.type === "collided" }];
    }
  }
}

/** 範圍的中心格：各格座標的平均，取範圍內最靠近平均的一格。 */
export function areaCenter(tiles: readonly Pos[]): Pos {
  const n = tiles.length;
  const cx = tiles.reduce((s, p) => s + p.x, 0) / n;
  const cy = tiles.reduce((s, p) => s + p.y, 0) / n;
  let best = tiles[0] as Pos;
  let bestD = Infinity;
  for (const p of tiles) {
    const d = (p.x - cx) ** 2 + (p.y - cy) ** 2;
    if (d < bestD) {
      bestD = d;
      best = p;
    }
  }
  return best;
}

/** 行動連線：攻擊者 → 單體目標；範圍技能 → 範圍的中心格。 */
function linesFor(e: EventBase, at: Locate): Array<{ from: Pos; to: Pos }> {
  if (e.type === "attack_rolled") {
    const from = at(e.attacker_id);
    const to = at(e.target_id);
    return from !== null && to !== null ? [{ from, to }] : [];
  }
  if (e.type === "skill_used" && Array.isArray(e.tiles)) {
    const tiles = e.tiles.map(posOf).filter((p): p is Pos => p !== null);
    const from = at(e.unit_id);
    if (from === null || tiles.length === 0) return [];
    const to = areaCenter(tiles);
    return samePos(from, to) ? [] : [{ from, to }];
  }
  return [];
}

/** 一步的事件 → 回饋項目（依事件順序；重複的連線只留一條）。`immobility`：打的那一刻能不能動（6F-6 `immobilityOf`；省略時只看 `view`）。 */
export function feedbackFor(events: readonly Record<string, unknown>[], view: BattleView, immobility: Immobility = immobilityIn(view)): FeedbackItem[] {
  const positions = new Map(view.units.map((u) => [u.id, u.pos]));
  const at: Locate = (id) => (typeof id === "string" ? (positions.get(id) ?? null) : null);
  const items: FeedbackItem[] = [];
  const slots = new Map<string, number>();
  const nextSlot = (pos: Pos): number => {
    const k = posKey(pos);
    const n = slots.get(k) ?? 0;
    slots.set(k, n + 1);
    return n;
  };
  const lineKeys = new Set<string>();
  for (const raw of events) {
    const e = asEvent(raw);
    for (const line of linesFor(e, at)) {
      const k = `${posKey(line.from)}>${posKey(line.to)}`;
      if (lineKeys.has(k)) continue;
      lineKeys.add(k);
      items.push({ kind: "line", ...line });
    }
    for (const s of textFor(e, at, (id) => immobility(e, id))) {
      if (s.pos === null) continue;
      // 「格擋」同一格同一步只跳一次（反應的格擋和傷害的格擋比例可能同時出現）
      const p = s.pos;
      if (s.text === WORD_BLOCK && items.some((x) => x.kind === "float" && x.text === WORD_BLOCK && samePos(x.pos, p))) continue;
      items.push({ kind: "float", pos: s.pos, text: s.text, tone: s.tone, big: s.big === true, slot: nextSlot(s.pos) });
    }
    if (e.type === "trap_glance") {
      // RG-3：敵人放陷阱時看那一格一眼（放置者看不到時不演）
      const from = at(e.owner_id);
      const to = posOf(e.pos);
      if (from !== null && to !== null && typeof e.owner_id === "string") items.push({ kind: "glance", pos: from, unitId: e.owner_id, to });
    }
    if (e.type === "status_applied") {
      const pos = at(e.target_id);
      if (pos !== null) items.push({ kind: "status", pos, text: statusName(String(e.status_id)), slot: nextSlot(pos) });
    }
  }
  return items;
}
