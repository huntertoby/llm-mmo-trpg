// 選移動時的路徑提示（Phase 6A-4c，`docs/art/戰鬥D版樣張.md` 第 3 節）：把伺服器的路徑預覽
// （`POST /api/battles/{id}/path-preview`）轉成畫面要畫的東西——分段顏色、每格的點、特殊格外框、結果小牌、
// 實際停點的驚嘆號、到不了的終點。規則判斷全部來自伺服器（每格的表面、陷阱、事件、走不走得到），這裡只決定畫法。
import type { components } from "../api/schema";
import type { BattleView, MoveAction, Pos } from "../api/types";
import { posKey } from "./geometry";
import { reactionName, statusName } from "./glossary";

type Schemas = components["schemas"];
export type PathPreview = Schemas["PathPreviewOut"];
export type PathStep = Schemas["PathStepOut"];
export type PathEvent = Schemas["PathEventOut"];
export type PathPreviewRequest = Schemas["PathPreviewRequest"];

/** 路徑一段的種類：一般、冰面（滑倒有機率）、陷阱或火、到不了。 */
export type SegKind = "normal" | "ice" | "danger" | "unreachable";

export const PATH_COLORS: Readonly<Record<SegKind, number>> = {
  normal: 0xffffff,
  ice: 0x1e78d0,
  danger: 0xff6a50,
  unreachable: 0xc8c8c8,
};

/** 虛線的段（冰面、到不了）。 */
export const PATH_DASHED: Readonly<Record<SegKind, boolean>> = {
  normal: false,
  ice: true,
  danger: false,
  unreachable: true,
};

export interface PathSeg {
  from: Pos;
  to: Pos;
  kind: SegKind;
  /** 只在骰子有利／不利其中一邊走得到（畫淡一點）。 */
  possible: boolean;
}

/** 經過的特殊格外框：冰（藍）、陷阱或火（紅）、油（油色）。 */
export type FrameKind = "ice" | "danger" | "oil";

export const FRAME_COLORS: Readonly<Record<FrameKind, number>> = {
  ice: 0x78dcff,
  danger: 0xff6e50,
  oil: 0xe0a040,
};

export type TagIcon = "ice" | "trap" | "fire" | "water" | "hit" | "status";

export const TAG_COLORS: Readonly<Record<TagIcon, number>> = {
  ice: 0x1e78d0,
  trap: 0xff6a50,
  fire: 0xff8a3a,
  water: 0x4aa8ff,
  hit: 0xff6a50,
  status: 0xc8b8ff,
};

/** 路徑旁的預估結果小牌：圖示加一兩個詞。 */
export interface PathTag {
  pos: Pos;
  icon: TagIcon;
  text: string;
}

export interface PathDraw {
  segments: PathSeg[];
  /** 每經過一格，格子中心一個點（不含起點）。 */
  dots: Array<{ pos: Pos; kind: SegKind }>;
  frames: Array<{ pos: Pos; kind: FrameKind }>;
  tags: PathTag[];
  /** 實際會停下的格子（被陷阱定住、被打斷）：紅色驚嘆號泡泡。冰面滑倒不放。 */
  bangs: Pos[];
  /** 原定的終點走不到：虛線框＋淡影，標「到不了」。 */
  missEnd: Pos | null;
}

export const EMPTY_PATH_DRAW: PathDraw = { segments: [], dots: [], frames: [], tags: [], bangs: [], missEnd: null };

const toPos = (xy: readonly number[]): Pos => ({ x: xy[0] as number, y: xy[1] as number });

function adjacent(a: Pos, b: Pos): boolean {
  return Math.abs(a.x - b.x) + Math.abs(a.y - b.y) === 1;
}

/** 這一格走不到（超出合法前段，或一定會在之前被打斷）。 */
export function stepMissed(step: PathStep): boolean {
  return step.reach === "unreachable" || step.reach === "interrupted";
}

const hasTrap = (step: PathStep): boolean => step.trap || step.events.some((e) => e.kind === "trap");

/** 走進第 `step` 格的那一段的顏色。 */
export function stepKind(step: PathStep): SegKind {
  if (stepMissed(step)) return "unreachable";
  if (step.surface === "ice") return "ice";
  if (hasTrap(step) || step.surface === "fire" || step.events.some((e) => e.kind === "deadly")) return "danger";
  return "normal";
}

/** 路徑的各段；伺服器回傳「完全沒有路」（起點＋終點不相鄰）時不畫線。 */
export function pathSegments(pv: PathPreview): PathSeg[] {
  const out: PathSeg[] = [];
  for (let i = 1; i < pv.steps.length; i++) {
    const prev = pv.steps[i - 1] as PathStep;
    const step = pv.steps[i] as PathStep;
    const from = toPos(prev.pos);
    const to = toPos(step.pos);
    if (!adjacent(from, to)) return [];
    out.push({ from, to, kind: stepKind(step), possible: step.reach === "possible" });
  }
  return out;
}

function frameOf(step: PathStep): FrameKind | null {
  if (step.surface === "ice") return "ice";
  if (hasTrap(step) || step.surface === "fire") return "danger";
  if (step.surface === "oil") return "oil";
  return null;
}

const maybe = (certain: boolean): string => (certain ? "" : "（可能）");

/** 傷害的數字：「−8」「−6～8」；只在骰子不利時才受傷的寫最大值。 */
export function damageText(events: readonly PathEvent[]): string {
  let min = 0;
  let max = 0;
  let unsure = false;
  for (const e of events) {
    max += e.amount_max ?? 0;
    if (e.amount_min === null) unsure = true;
    else min += e.amount_min;
  }
  if (max <= 0) return "";
  if (unsure) return `−${max}`;
  return min === max ? `−${max}` : `−${min}～${max}`;
}

/** 狀態的短名（「點燃」「定身」；其餘用對照表的名稱）。 */
export function statusWord(id: string): string {
  if (id === "burning") return "點燃";
  if (id === "root" || id === "rooted") return "定身";
  return statusName(id);
}

interface Part {
  icon: TagIcon;
  text: string;
}

/** 一格的事件 → 小牌的各段（依序：滑倒、陷阱、點燃、其他狀態、潮濕、反應、墜落、致命、其餘傷害）。 */
function stepParts(step: PathStep): Part[] {
  const parts: Part[] = [];
  const used = new Set<PathEvent>();
  const take = (pred: (e: PathEvent) => boolean): PathEvent[] => {
    const hit = step.events.filter((e) => !used.has(e) && pred(e));
    for (const e of hit) used.add(e);
    return hit;
  };
  for (const e of take((x) => x.kind === "slip_check")) {
    const pct = Math.round((e.chance_permille ?? 0) / 10);
    parts.push({ icon: "ice", text: `滑倒 ${pct}%・失敗停在這格${maybe(e.certain)}` });
    take((x) => x.kind === "status" && x.status_id === e.status_id); // 滑倒的倒地已經寫在「失敗停在這格」
  }
  for (const trap of take((x) => x.kind === "trap")) {
    const dmg = damageText(take((x) => x.kind === "damage" && x.other_id === trap.other_id));
    const statuses = take((x) => x.kind === "status" && x.status_id !== "burning").map(
      (s) => `${statusWord(s.status_id ?? "")}${maybe(s.certain)}`,
    );
    const head = `陷阱${dmg === "" ? "" : ` ${dmg}`}${maybe(trap.certain)}`;
    parts.push({ icon: "trap", text: [head, ...statuses].join("・") });
  }
  for (const s of take((x) => x.kind === "status" && x.status_id === "burning")) {
    parts.push({ icon: "fire", text: `點燃${maybe(s.certain)}` });
  }
  for (const s of take((x) => x.kind === "status")) {
    parts.push({ icon: "status", text: `${statusWord(s.status_id ?? "")}${maybe(s.certain)}` });
  }
  if (step.surface === "water") parts.push({ icon: "water", text: "潮濕" });
  for (const r of take((x) => x.kind === "reaction")) {
    const dmg = damageText(take((x) => x.kind === "damage" && x.other_id === r.other_id));
    const name = r.detail === null ? "反應" : reactionName(r.detail);
    parts.push({ icon: "hit", text: `${name}${dmg === "" ? "" : ` ${dmg}`}${maybe(r.certain)}` });
  }
  for (const e of take((x) => x.kind === "fell")) parts.push({ icon: "hit", text: `墜落${maybe(e.certain)}` });
  for (const e of take((x) => x.kind === "deadly")) parts.push({ icon: "hit", text: `致命地形${maybe(e.certain)}` });
  const rest = take((x) => x.kind === "damage");
  if (rest.length > 0) {
    const dmg = damageText(rest);
    if (dmg !== "") parts.push({ icon: "hit", text: `${dmg}${maybe(rest.every((e) => e.certain))}` });
  }
  for (const e of take((x) => x.kind === "downed")) parts.push({ icon: "hit", text: `倒下${maybe(e.certain)}` });
  return parts;
}

/** 一格的小牌（沒有可說的事時 `null`）；圖示取第一段的。 */
export function stepTag(step: PathStep): PathTag | null {
  if (stepMissed(step) || step.index === 0) return null;
  const parts = stepParts(step);
  const first = parts[0];
  if (first === undefined) return null;
  return { pos: toPos(step.pos), icon: first.icon, text: parts.map((p) => p.text).join("・") };
}

/** 停在這一格是冰面滑倒造成的（不放驚嘆號）。 */
function slipStop(step: PathStep, reason: string | null): boolean {
  if (reason !== "prone") return false;
  return step.events.some((e) => e.kind === "slip_check");
}

/** 實際會停下的格子：有 `stopped` 事件、不是冰面滑倒、也不是撤離。被移走的停在新位置。 */
export function stopBangs(pv: PathPreview): Pos[] {
  const out: Pos[] = [];
  for (const step of pv.steps) {
    for (const e of step.events) {
      if (e.kind !== "stopped" || e.detail === "escaped" || slipStop(step, e.detail)) continue;
      const moved = e.detail === "displaced" ? step.events.find((x) => x.kind === "displaced" && x.pos !== null) : undefined;
      const at = moved?.pos != null ? toPos(moved.pos) : toPos(step.pos);
      if (!out.some((p) => p.x === at.x && p.y === at.y)) out.push(at);
    }
  }
  return out;
}

/** 原定的終點走不到時回傳終點。 */
export function missedEnd(pv: PathPreview): Pos | null {
  const last = pv.steps[pv.steps.length - 1];
  if (last === undefined || last.index === 0) return null;
  return stepMissed(last) || !pv.reachable ? toPos(last.pos) : null;
}

/** 路徑預覽 → 畫面要畫的全部東西。 */
export function pathDraw(pv: PathPreview | null): PathDraw {
  if (pv === null || pv.steps.length < 2) return EMPTY_PATH_DRAW;
  const segments = pathSegments(pv);
  const drawn = segments.length > 0;
  const steps = pv.steps.slice(1);
  return {
    segments,
    dots: drawn ? steps.map((s) => ({ pos: toPos(s.pos), kind: stepKind(s) })) : [],
    frames: steps.flatMap((s) => {
      const kind = stepMissed(s) ? null : frameOf(s);
      return kind === null ? [] : [{ pos: toPos(s.pos), kind }];
    }),
    tags: steps.flatMap((s) => {
      const tag = stepTag(s);
      return tag === null ? [] : [tag];
    }),
    bangs: stopBangs(pv),
    missEnd: missedEnd(pv),
  };
}

/** 請求與快取的鍵：走已知的路徑（`path`）或只給終點（`dest`）。 */
export interface PathQuery {
  key: string;
  body: PathPreviewRequest;
}

export interface HoverPathInput {
  /** 選移動中（主角回合、沒有選技能、指揮或隊友指令、沒有滑過面板按鈕）。 */
  moving: boolean;
  hover: Pos | null;
  hero: { pos: Pos } | null;
  view: Pick<BattleView, "width" | "height" | "units">;
  /** 本回合走得到的格子 → 那一格的移動動作（`classifyActions` 的 `moves`）。 */
  moves: ReadonlyMap<string, MoveAction>;
}

/** 滑過的格子要預覽哪條路徑：走得到的用移動動作的路徑；走不到的空格只給終點（伺服器標出到不了）。
 * 滑過自己、單位或地圖外不預覽。 */
export function hoverPathQuery(i: HoverPathInput): PathQuery | null {
  const { hover, hero, view } = i;
  if (!i.moving || hover === null || hero === null) return null;
  if (hover.x < 0 || hover.y < 0 || hover.x >= view.width || hover.y >= view.height) return null;
  if (hover.x === hero.pos.x && hover.y === hero.pos.y) return null;
  const onTile = view.units.some((u) => !u.downed && !u.escaped && !u.dismissed && u.pos.x === hover.x && u.pos.y === hover.y);
  if (onTile) return null;
  const move = i.moves.get(posKey(hover));
  return pathQuery(move?.path ?? null, hover);
}

export function pathQuery(path: readonly Pos[] | null, dest: Pos): PathQuery {
  if (path !== null && path.length > 0) {
    return { key: `p:${path.map((p) => `${p.x},${p.y}`).join(";")}`, body: { path: path.map((p) => ({ x: p.x, y: p.y })) } };
  }
  return { key: `d:${dest.x},${dest.y}`, body: { dest: { x: dest.x, y: dest.y } } };
}
