// 預覽結果 → 顯示文字（純函式）。機率以千分比（‰）、期望傷害以 ×1000 傳來，這裡轉成百分比與小數。
import { asEvent, type BattleView, type PreviewOut } from "../api/types";
import { objectName, statusName, surfaceName } from "./glossary";
import { sceneLines } from "./scenePreview";
import { summonLines } from "./summons";
import { zonePreviewLines } from "./zones";
import type { UnitNames } from "./units";

type Outcome = PreviewOut["certain"][number];
type Damage = NonNullable<PreviewOut["damage"]>;

/** 千分比 → 「87%」（整數；有小數時保留一位）。 */
export function percent(permille: number | null | undefined): string {
  if (permille == null) return "—";
  const p = permille / 10;
  return `${Number.isInteger(p) ? p : p.toFixed(1)}%`;
}

function fixed1(milli: number): string {
  const v = milli / 1000;
  return Number.isInteger(v) ? String(v) : v.toFixed(1);
}

export function damageText(d: Damage): string {
  const range = d.minimum === d.maximum ? `${d.minimum}` : `${d.minimum}–${d.maximum}`;
  return `${range}（期望 ${fixed1(d.expected_milli)}）`;
}

function objectLabel(view: BattleView, id: string | null | undefined): string {
  const obj = view.objects.find((o) => o.id === id);
  return obj === undefined ? (id ?? "物件") : objectName(obj.kind);
}

function posText(o: Outcome): string {
  return o.pos == null ? "" : ` (${o.pos[0]}, ${o.pos[1]})`;
}

/** 一個連鎖結果的一行中文。 */
export function outcomeText(o: Outcome, names: UnitNames, view: BattleView): string {
  const who = o.unit_id == null ? "" : names.label(o.unit_id);
  const obj = () => `${objectLabel(view, o.object_id)}${posText(o)}`;
  switch (o.kind) {
    case "damaged":
      return `${who} 受到傷害`;
    case "shield":
      return `${who} 護盾吸收`;
    case "downed":
      return `${who} 倒下`;
    case "moved":
      return `${who} 移動到${posText(o)}`;
    case "fell":
      return `${who} 墜落`;
    case "deadly_terrain":
      return `${who} 掉進致命地形${posText(o)}`;
    case "escaped":
      return `${who} 撤離`;
    case "status":
      return `${who} 獲得「${statusName(o.detail ?? "")}」`;
    case "surface":
      return `${posText(o).trim()} 變成${surfaceName(o.detail ?? "")}`;
    case "terrain":
      return `${posText(o).trim()} 地形改變`;
    case "object_damaged":
      return `${obj()} 受損`;
    case "object_destroyed":
      return `${obj()} 被摧毀`;
    case "object_exploded":
      return `${obj()} 爆炸`;
    case "object_ignited":
      return `${obj()} 被點燃`;
    case "object_moved":
      return `${obj()} 被推動`;
    case "reaction":
      return `${who} 觸發反應`;
    case "intercepted":
      return `${who} 攔截攻擊`;
    case "stacks":
      return `${who} 層數變化`;
    case "trap_placed":
      return `放置陷阱${posText(o)}`;
    case "trap_triggered":
      return `${who} 觸發陷阱${posText(o)}`;
    default:
      return o.kind;
  }
}

/** 連鎖事件的類型（油桶爆炸、點燃、表面與地形變化、墜落、致命地形、陷阱觸發）。 */
export const CHAIN_EVENT_TYPES: ReadonlySet<string> = new Set([
  "object_exploded",
  "object_ignited",
  "object_destroyed",
  "surface_changed",
  "terrain_changed",
  "unit_fell",
  "collided",
  "entered_deadly_terrain",
  "trap_triggered",
]);

/** 與 CHAIN_EVENT_TYPES 對應的 certain／possible 結果類型（有連鎖事件文字時不重複列出）。 */
const CHAIN_OUTCOME_KINDS: ReadonlySet<string> = new Set([
  "object_exploded",
  "object_ignited",
  "object_destroyed",
  "surface",
  "terrain",
  "fell",
  "deadly_terrain",
  "trap_triggered",
]);

export interface ChainLines {
  /** 最少後果的模擬中也會發生的連鎖（確定）。 */
  certain: string[];
  /** 只在最多後果的模擬中發生的連鎖（可能）。 */
  possible: string[];
}

function chainTexts(events: readonly Record<string, unknown>[]): string[] {
  const texts: string[] = [];
  for (const raw of events) {
    const e = asEvent(raw);
    if (!CHAIN_EVENT_TYPES.has(e.type) || e.text === undefined) continue;
    const text = e.text.trim();
    if (!texts.includes(text)) texts.push(text);
  }
  return texts;
}

/** 預覽的連鎖事件（伺服器過濾後的 min_events／max_events 的中文 text）。 */
export function chainLines(p: PreviewOut): ChainLines {
  const certain = chainTexts(p.min_events);
  const possible = chainTexts(p.max_events).filter((t) => !certain.includes(t));
  return { certain, possible };
}

/**
 * 預覽的顯示行（依序：總覽、各目標、治療、確定的後果、可能的後果、備註）。
 * skipChain：連鎖類的結果由 chainLines 另外列出時不重複。
 */
export function previewLines(
  p: PreviewOut,
  names: UnitNames,
  view: BattleView,
  skipChain = false,
): string[] {
  const lines: string[] = [];
  const head: string[] = [];
  if (p.hit_permille != null) head.push(`命中 ${percent(p.hit_permille)}`);
  if (p.crit_permille != null) head.push(`暴擊 ${percent(p.crit_permille)}`);
  if (p.damage !== null) head.push(`傷害 ${damageText(p.damage)}`);
  if (head.length > 0) lines.push(head.join("　"));
  if (p.cover !== null) lines.push(`目標有${p.cover.name_zh}掩護（命中 −${p.cover.penalty}）`);
  if (p.targets.length > 1 || p.targets.some((t) => t.ally)) {
    for (const t of p.targets) {
      const bits = [`命中 ${percent(t.hit_permille)}`];
      if (t.damage !== null) bits.push(`傷害 ${damageText(t.damage)}`);
      lines.push(`${t.ally ? "（友軍）" : ""}${names.label(t.unit_id)}：${bits.join("，")}`);
    }
  }
  for (const t of p.targets) {
    for (const s of t.status_chances) {
      const dim = s.diminished ? "（遞減）" : "";
      lines.push(`${names.label(t.unit_id)}：${statusName(s.status_id)} ${percent(s.apply_permille)}${dim}`);
    }
    if (t.knock_permille != null && t.knock_permille > 0) {
      lines.push(`${names.label(t.unit_id)}：擊倒機率 ${percent(t.knock_permille)}`);
    }
  }
  for (const h of p.healed) {
    lines.push(`治療 ${names.label(h.unit_id)} ${h.minimum}–${h.maximum}`);
  }
  for (const c of p.collisions ?? []) {
    lines.push(`撞擊傷害 ${names.label(c.unit_id)} 最多 ${c.maximum}`);
  }
  lines.push(...sceneLines(p, names, view)); // 穿透、推倒、投擲（Phase 3C-5b）
  lines.push(...summonLines(p, names)); // 召喚位置、持續與被擠掉的舊召喚物（Phase 3D-4b）
  lines.push(...zonePreviewLines(p.min_events)); // 建立的持續區域（Phase 3D-5）
  const shown = (o: Outcome) => !skipChain || !CHAIN_OUTCOME_KINDS.has(o.kind);
  for (const o of p.certain.filter(shown)) lines.push(`確定：${outcomeText(o, names, view)}`);
  for (const o of p.possible.filter(shown)) lines.push(`可能：${outcomeText(o, names, view)}`);
  for (const n of p.notes) lines.push(n);
  const cost = costLine(p);
  if (cost !== null) lines.push(cost);
  return lines;
}

/** 動作的 AP 與射程（含修正規則，Phase 3C-2）；伺服器沒有給時為 null。 */
export function costLine(p: PreviewOut): string | null {
  if (p.ap_cost == null) return null;
  return p.reach == null ? `AP ${p.ap_cost}` : `AP ${p.ap_cost}　射程 ${p.reach}`;
}
