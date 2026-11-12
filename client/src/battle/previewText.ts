// 預覽結果 → 顯示文字（純函式）。機率以千分比（‰）、期望傷害以 ×1000 傳來，這裡轉成百分比與小數。
import { asEvent, isPartBroken, isPartDamaged, type BattleView, type PreviewOut } from "../api/types";
import { bombLines, reviveLines } from "./bombs";
import { heightNote } from "./elevation";
import { grantLines } from "./granted";
import { gambleLines } from "./gamble";
import { objectName, statusName, surfaceName } from "./glossary";
import { sceneLines } from "./scenePreview";
import { previewVariantLine } from "./variants";
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
    case "form":
      return `${who} 進入形態`;
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
 * 6F-18（美術 PM 6F-17 檢查第 2 節）：目標站在高地時寫「名字：高地 ▲N」（站著的人那一格地圖上不畫「▲N」）。
 * 照目標的順序；同一個單位只寫一次；平地不寫。
 */
export function targetHeightLines(p: Pick<PreviewOut, "targets"> & Partial<Pick<PreviewOut, "affected_units" | "action">>, names: UnitNames, view: BattleView): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  // 6F-19：單一目標的預覽（例如普攻）`targets` 是空的，目標在 `affected_units`（施放者自己不寫）
  const actor = (p.action as { unit_id?: string } | undefined)?.unit_id;
  const ids = [...p.targets.map((t) => t.unit_id), ...(p.affected_units ?? []).filter((id) => id !== actor)];
  for (const id of ids) {
    if (seen.has(id)) continue;
    seen.add(id);
    const t = { unit_id: id };
    const u = view.units.find((x) => x.id === t.unit_id);
    const tile = u === undefined ? undefined : view.tiles.find((x) => x.x === u.pos.x && x.y === u.pos.y);
    const note = tile === undefined ? null : heightNote(tile.height);
    if (note !== null) out.push(`${names.label(t.unit_id)}：${note}`);
  }
  return out;
}

/**
 * PB-1c：選了部位的預覽多一行（規格第 7 節第 5 點）——「拂塵還剩 12」；最少、最多不同時「拂塵還剩 6～12」；
 * 最少的後果就會破時「會打破拂塵」；只有最多的後果會破時「拂塵還剩 0～12（可能打破）」。
 * 部位剩餘血量被藏起來（頭目資訊被隱藏，`hp_after` 為 null）或沒有打部位時不寫。
 */
export function partPreviewLines(p: Pick<PreviewOut, "min_events" | "max_events">): string[] {
  const low = p.min_events.map((raw) => asEvent(raw));
  const high = p.max_events.map((raw) => asEvent(raw));
  const ids: string[] = [];
  for (const e of [...low, ...high]) if (isPartDamaged(e) && !ids.includes(e.part_id)) ids.push(e.part_id);
  const out: string[] = [];
  for (const id of ids) {
    const dmgLow = low.filter(isPartDamaged).filter((e) => e.part_id === id);
    const dmgHigh = high.filter(isPartDamaged).filter((e) => e.part_id === id);
    const name = (dmgLow[0] ?? dmgHigh[0])?.name_zh ?? id;
    if (low.some((e) => isPartBroken(e) && e.part_id === id)) {
      out.push(`會打破${name}`);
      continue;
    }
    const most = dmgLow[dmgLow.length - 1]?.hp_after ?? dmgHigh[0]?.hp_before ?? null; // 最少後果剩最多
    const least = dmgHigh[dmgHigh.length - 1]?.hp_after ?? most; // 最多後果剩最少
    if (most === null || least === null) continue;
    const breaks = high.some((e) => isPartBroken(e) && e.part_id === id);
    const range = least === most ? `${most}` : `${least}～${most}`;
    out.push(breaks ? `${name}還剩 ${range}（可能打破）` : `${name}還剩 ${range}`);
  }
  return out;
}

/**
 * DD-2（#153）：拿雙匕首瞄準單體武器技，伺服器的 `strikes` ≥ 2 時列一行「打 2 下」。
 * `targets[].damage` 已是幾下的合計（最少＝只中第一下、最多＝每下都暴擊、期望＝每下期望 × 下數）；
 * 命中率是每一下的。只有一個目標（單體）時才走這裡；`strikes` 1（其他技能）不出這一行，原本的輸出逐字不變。
 */
export function strikeLines(p: Pick<PreviewOut, "targets"> & Partial<Pick<PreviewOut, "strikes">>, names: UnitNames): string[] {
  const n = p.strikes ?? 1;
  if (n <= 1) return [];
  return p.targets
    .filter((t) => !t.ally && t.damage !== null)
    .map((t) => `${names.label(t.unit_id)}：打 ${n} 下，每下命中 ${percent(t.hit_permille)}，傷害合計 ${damageText(t.damage!)}`);
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
  const form = previewVariantLine(p);
  if (form !== null) lines.push(form);
  const head: string[] = [];
  if (p.hit_permille != null) head.push(`命中 ${percent(p.hit_permille)}`);
  if (p.crit_permille != null) head.push(`暴擊 ${percent(p.crit_permille)}`);
  if (p.damage !== null) head.push(`傷害 ${damageText(p.damage)}`);
  if (head.length > 0) lines.push(head.join("　"));
  lines.push(...partPreviewLines(p)); // PB-1c：選了部位
  if (p.cover !== null) lines.push(`目標有${p.cover.name_zh}掩護（命中 −${p.cover.penalty}）`);
  lines.push(...targetHeightLines(p, names, view));
  if (p.targets.length > 1 || p.targets.some((t) => t.ally)) {
    for (const t of p.targets) {
      const bits = [`命中 ${percent(t.hit_permille)}`];
      if (t.damage !== null) bits.push(`傷害 ${damageText(t.damage)}`);
      lines.push(`${t.ally ? "（友軍）" : ""}${names.label(t.unit_id)}：${bits.join("，")}`);
    }
  } else {
    lines.push(...strikeLines(p, names));
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
  lines.push(...gambleLines(p, names)); // 賭注的兩個分支（Phase 3D-7a）
  for (const n of p.miss_notes ?? []) lines.push(n); // 失手反噬（Phase 3D-7a）
  lines.push(...sceneLines(p, names, view)); // 穿透、推倒、投擲（Phase 3C-5b）
  lines.push(...summonLines(p, names)); // 召喚位置、持續與被擠掉的舊召喚物（Phase 3D-4b）
  lines.push(...zonePreviewLines(p.min_events)); // 建立的持續區域（Phase 3D-5）
  lines.push(...bombLines(p, names)); // 綁上的定時炸彈：倒數與爆炸範圍（Phase 3D-8b）
  lines.push(...reviveLines(p, names)); // 復活：站起來的單位與位置（Phase 3D-8b）
  lines.push(...grantLines(p, names)); // 暫時獲得技能（Phase 3D-8c）
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
