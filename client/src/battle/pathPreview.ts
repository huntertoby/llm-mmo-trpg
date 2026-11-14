// 選移動時的路徑提示（Phase 6A-4c，`docs/archive/art/戰鬥D版樣張.md` 第 3 節）：把伺服器的路徑預覽
// （`POST /api/battles/{id}/path-preview`）轉成畫面要畫的東西——分段顏色、每格的點、特殊格外框、結果小牌、
// 實際停點的驚嘆號、到不了的終點。規則判斷全部來自伺服器（每格的表面、陷阱、事件、走不走得到），這裡只決定畫法。
import type { components } from "../api/schema";
import type { BattleView, MoveAction, Pos } from "../api/types";
import { standingAtTile } from "./footprint";
import { posKey } from "./geometry";
import { reactionName, statusName, surfaceName } from "./glossary";

type Schemas = components["schemas"];
export type PathPreview = Schemas["PathPreviewOut"];
export type PathStep = Schemas["PathStepOut"];
export type PathEvent = Schemas["PathEventOut"];
export type PathPreviewRequest = Schemas["PathPreviewRequest"];
export type SlipRun = Schemas["SlipRunOut"];

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
  /** 畫虛線：冰面、到不了，以及冰面後面的陷阱段（前面可能先滑倒停下；6A-4f）。 */
  dashed: boolean;
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
  /** 冰面滑倒時的停點（#123，6E-2）：畫 ◆；`slide` 是滑行路徑（含起點）。 */
  slipStops: Array<{ pos: Pos; slide: Pos[] }>;
  /** 原定的終點走不到：虛線框＋淡影，標「到不了」。 */
  missEnd: Pos | null;
}

export const EMPTY_PATH_DRAW: PathDraw = { segments: [], dots: [], frames: [], tags: [], bangs: [], slipStops: [], missEnd: null };

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

/** 這一格在某段連續冰面的第一格之後（前面可能先滑倒停下；6A-4f）。 */
export function afterIce(pv: PathPreview, step: PathStep): boolean {
  return pv.slip_runs.some((r) => r.start < step.index);
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
    const kind = stepKind(step);
    const dashed = PATH_DASHED[kind] || (kind === "danger" && afterIce(pv, step));
    out.push({ from, to, kind, possible: step.reach === "possible", dashed });
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

/** 連續冰面一段的小牌文字（6A-4f；#123 只在第一格擲一次，失敗沿方向滑到停點 ◆ 倒地）：有百分比就不加「（可能）」。
 * 一格都沒滑（下一格就擋住）時寫「失敗就地倒地」。 */
export function slipRunText(run: SlipRun): string {
  if (run.immune) return `冰 ${run.tiles} 格・不會滑倒`;
  const pct = Math.round(run.chance_permille / 10);
  const fail = run.slide_path.length > 1 ? "失敗滑到 ◆ 倒地" : "失敗就地倒地";
  return `冰 ${run.tiles} 格・滑倒 ${pct}%・${fail}${slipLanding(run)}`;
}

/** 停點上有陷阱或表面時的附註（05 5.10）：「（滑到陷阱）」「（滑到火焰）」。 */
function slipLanding(run: SlipRun): string {
  if (run.stop_trap) return "（滑到陷阱）";
  if (run.stop_surface !== null) return `（滑到${surfaceName(run.stop_surface)}）`;
  return "";
}

/** 每段冰面滑倒時的停點 ◆（停在別處的才畫；就地倒地時停點就是小牌那格；不會滑倒的段不畫）。 */
export function slipStops(pv: PathPreview): Array<{ pos: Pos; slide: Pos[] }> {
  return pv.slip_runs
    .filter((r) => !r.immune && !(r.fail_stop[0] === r.start_pos[0] && r.fail_stop[1] === r.start_pos[1]))
    .map((r) => ({ pos: toPos(r.fail_stop), slide: r.slide_path.map(toPos) }));
}

/** 一格的事件 → 小牌的各段（依序：滑倒、陷阱、點燃、其他狀態、潮濕、反應、墜落、致命、其餘傷害）。
 * 滑倒由連續冰面的段（`slip_runs`）合成一張，放在段的第一格（`run`）；段內其他格不再寫。
 * `iced`：這一格在冰面之後，陷阱是否發生取決於前面有沒有滑倒，字上不加「（可能）」，改畫紅色虛線。 */
function stepParts(step: PathStep, run: SlipRun | undefined, iced: boolean): Part[] {
  const parts: Part[] = [];
  const used = new Set<PathEvent>();
  const take = (pred: (e: PathEvent) => boolean): PathEvent[] => {
    const hit = step.events.filter((e) => !used.has(e) && pred(e));
    for (const e of hit) used.add(e);
    return hit;
  };
  if (run !== undefined) parts.push({ icon: "ice", text: slipRunText(run) });
  for (const e of take((x) => x.kind === "slip_check")) {
    take((x) => x.kind === "status" && x.status_id === e.status_id); // 滑倒的倒地已經寫在「失敗滑到 ◆ 倒地」
  }
  take((x) => x.kind === "displaced" && x.detail === "slide"); // 滑行的每一格由 ◆ 表示
  const trapMaybe = (certain: boolean): string => (iced ? "" : maybe(certain));
  for (const trap of take((x) => x.kind === "trap")) {
    const dmg = damageText(take((x) => x.kind === "damage" && x.other_id === trap.other_id));
    const statuses = take((x) => x.kind === "status" && x.status_id !== "burning").map(
      (s) => `${statusWord(s.status_id ?? "")}${trapMaybe(s.certain)}`,
    );
    const head = `陷阱${dmg === "" ? "" : ` ${dmg}`}${trapMaybe(trap.certain)}`;
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

/** 一格的小牌（沒有可說的事時 `null`）；圖示取第一段的。`pv` 給連續冰面的段（6A-4f）。 */
export function stepTag(step: PathStep, pv?: PathPreview): PathTag | null {
  if (stepMissed(step) || step.index === 0) return null;
  const run = pv?.slip_runs.find((r) => r.start === step.index);
  const iced = pv !== undefined && hasTrap(step) && afterIce(pv, step);
  const parts = stepParts(step, run, iced);
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
      const tag = stepTag(s, pv);
      return tag === null ? [] : [tag];
    }),
    bangs: stopBangs(pv),
    slipStops: slipStops(pv),
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
  if (standingAtTile(view.units, hover) !== undefined) return null;
  const move = i.moves.get(posKey(hover));
  return pathQuery(move?.path ?? null, hover);
}

export function pathQuery(path: readonly Pos[] | null, dest: Pos): PathQuery {
  if (path !== null && path.length > 0) {
    return { key: `p:${path.map((p) => `${p.x},${p.y}`).join(";")}`, body: { path: path.map((p) => ({ x: p.x, y: p.y })) } };
  }
  return { key: `d:${dest.x},${dest.y}`, body: { dest: { x: dest.x, y: dest.y } } };
}
