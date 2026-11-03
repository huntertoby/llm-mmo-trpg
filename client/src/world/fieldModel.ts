// 實地地圖（Phase 6B-3；docs/phases/Phase6計畫.md 第 5 節）的純函式：`WorldView.field` → 戰鬥渲染器的 `DrawModel`、
// 出口／門／傳送石的標示、前端的 BFS 路徑、方向鍵、相鄰的設施與 NPC。規則以伺服器為準（`walk` 回來的位置），
// 這裡的可站格與爬升上限都由伺服器下發（`FieldTileView.walkable`、`FieldView.max_climb`）。
// Phase 6C-1：看得見的敵人畫成敵方紙娃娃，視野（前方扇形 4 格）畫淡紅；開不開打由伺服器判定。
// Phase 6C-5：地圖上的東西——事件「！」、營火、情境物件、朋友的腳印、留言石碑（標記與滑過說明；
// 碰到「！」開卡、站營火紮營、點物件開卡都由伺服器判定）。
import type { BattleView, Facing, FieldView, ObjectView, Pos, Surface, TileView, UnitView } from "../api/types";
import { buildDrawModel, type DrawModel } from "../battle/drawModel";
import { HIGHLIGHT } from "../battle/glossary";
import type { Highlights } from "../render/BattleRenderer";
import type { TelegraphMark } from "../battle/telegraph";
import { npcFieldLook } from "./npcLook";

/** 主角在實地地圖上的單位 ID（動畫用）。 */
export const FIELD_HERO = "field_hero";
/** 一次 `walk` 最多幾格（伺服器 `WalkAction` 的上限）。 */
export const WALK_MAX = 30;
/** 走一格的動畫時間（同 6A-4d，約 0.12 秒）。 */
export const STEP_MS = 120;
/** 換地圖時地名停留的時間。 */
export const PLACE_NAME_MS = 2000;

const FACING: Readonly<Record<FieldView["me"]["facing"], Facing>> = { n: "north", e: "east", s: "south", w: "west" };

const DIRS: ReadonlyArray<readonly [number, number]> = [
  [0, -1],
  [1, 0],
  [0, 1],
  [-1, 0],
];

export type Direction = "up" | "down" | "left" | "right";

const DIR_DELTA: Readonly<Record<Direction, readonly [number, number]>> = {
  up: [0, -1],
  down: [0, 1],
  left: [-1, 0],
  right: [1, 0],
};

/** 鍵盤 → 方向（方向鍵與 WASD）；其他鍵 `null`。 */
export function keyDirection(key: string): Direction | null {
  switch (key) {
    case "ArrowUp":
    case "w":
    case "W":
      return "up";
    case "ArrowDown":
    case "s":
    case "S":
      return "down";
    case "ArrowLeft":
    case "a":
    case "A":
      return "left";
    case "ArrowRight":
    case "d":
    case "D":
      return "right";
    default:
      return null;
  }
}

const key = (p: Pos): string => `${p.x},${p.y}`;

function inBounds(field: FieldView, p: Pos): boolean {
  return p.x >= 0 && p.y >= 0 && p.x < field.width && p.y < field.height;
}

function tileOf(field: FieldView, p: Pos): FieldView["tiles"][number] | undefined {
  return inBounds(field, p) ? field.tiles[p.y * field.width + p.x] : undefined;
}

/** 從 `from` 走一步到 `to` 合不合法（四方向相鄰、可站、往上不超過 `max_climb`；往下不限，同伺服器）。 */
export function canStep(field: FieldView, from: Pos, to: Pos): boolean {
  if (Math.abs(from.x - to.x) + Math.abs(from.y - to.y) !== 1) return false;
  const a = tileOf(field, from);
  const b = tileOf(field, to);
  if (a === undefined || b === undefined || !b.walkable) return false;
  return b.height - a.height <= field.max_climb;
}

/** 出口、門、傳送石所在的格子（伺服器走到這些格子就停下並觸發）。 */
export function portalCells(field: FieldView): Set<string> {
  const out = new Set<string>();
  for (const e of field.exits) for (const [x, y] of e.cells) out.add(`${x},${y}`);
  for (const d of field.doors) out.add(`${d.x},${d.y}`);
  for (const s of field.stones) out.add(`${s.x},${s.y}`);
  return out;
}

export type PortalHit =
  | { kind: "exit"; to: string; name: string }
  | { kind: "door"; to: string; name: string }
  | { kind: "stone"; id: string };

export function portalAt(field: FieldView, p: Pos): PortalHit | null {
  const exit = field.exits.find((e) => e.cells.some(([x, y]) => x === p.x && y === p.y));
  if (exit !== undefined) return { kind: "exit", to: exit.to, name: exit.to_name_zh };
  const door = field.doors.find((d) => d.x === p.x && d.y === p.y);
  if (door !== undefined) return { kind: "door", to: door.to, name: door.to_name_zh };
  const stone = field.stones.find((s) => s.x === p.x && s.y === p.y);
  if (stone !== undefined) return { kind: "stone", id: stone.id };
  return null;
}

/**
 * 四方向 BFS：`from` → `to` 的路徑（不含起點；到不了或原地為 `null`）。
 * 路上避開出口、門、傳送石（伺服器踩到就停下），只有終點可以是它們；避不開時才允許穿過。
 * 鄰格順序固定（北、東、南、西），同樣的地圖與起訖點一定得到同一條路。
 */
export function findPath(field: FieldView, from: Pos, to: Pos): Pos[] | null {
  if (from.x === to.x && from.y === to.y) return null;
  const target = tileOf(field, to);
  if (target === undefined || !target.walkable) return null;
  const portals = portalCells(field);
  return bfs(field, from, to, portals) ?? bfs(field, from, to, new Set());
}

function bfs(field: FieldView, from: Pos, to: Pos, avoid: ReadonlySet<string>): Pos[] | null {
  const prev = new Map<string, Pos | null>([[key(from), null]]);
  const queue: Pos[] = [from];
  for (let i = 0; i < queue.length; i++) {
    const here = queue[i]!;
    if (here.x === to.x && here.y === to.y) return unwind(prev, here);
    if (i > 0 && avoid.has(key(here))) continue; // 不從出口、門、傳送石繼續往外走
    for (const [dx, dy] of DIRS) {
      const next = { x: here.x + dx, y: here.y + dy };
      if (prev.has(key(next)) || !canStep(field, here, next)) continue;
      prev.set(key(next), here);
      queue.push(next);
    }
  }
  return null;
}

function unwind(prev: Map<string, Pos | null>, end: Pos): Pos[] {
  const path: Pos[] = [];
  let cur: Pos | null = end;
  while (cur !== null) {
    const back: Pos | null = prev.get(key(cur)) ?? null;
    if (back === null) break; // 起點不放進路徑
    path.push(cur);
    cur = back;
  }
  return path.reverse();
}

/** 超過 30 格的路徑切成好幾段（每段一次 `walk`）。 */
export function chunkPath(path: readonly Pos[], max = WALK_MAX): Pos[][] {
  const out: Pos[][] = [];
  for (let i = 0; i < path.length; i += max) out.push(path.slice(i, i + max));
  return out;
}

/** 方向鍵的下一格；走不過去為 `null`（不送請求）。 */
export function stepTarget(field: FieldView, dir: Direction): Pos | null {
  const [dx, dy] = DIR_DELTA[dir];
  const next = { x: field.me.x + dx, y: field.me.y + dy };
  return canStep(field, field.me, next) ? next : null;
}

/** 路徑 → `walk` 動作。 */
export function walkAction(path: readonly Pos[]): { kind: "walk"; path: [number, number][] } {
  return { kind: "walk", path: path.map((p) => [p.x, p.y] as [number, number]) };
}

/**
 * 伺服器回來之後，這一段實際走了哪些格子（動畫用）：
 * - 同一張地圖：走到伺服器回報的位置為止（中途碰到出口、門、傳送石會提早停）；
 * - 換了地圖（或離開實地地圖）：走到第一個出口、門或傳送石為止。
 */
export function walkedCells(before: FieldView, sent: readonly Pos[], after: FieldView | null | undefined): Pos[] {
  if (after != null && after.map_id === before.map_id) {
    const end = sent.findIndex((p) => p.x === after.me.x && p.y === after.me.y);
    return end < 0 ? [] : sent.slice(0, end + 1);
  }
  const portals = portalCells(before);
  const end = sent.findIndex((p) => portals.has(key(p)));
  return end < 0 ? [...sent] : sent.slice(0, end + 1);
}

/** 走一段的動畫計畫（逐格平移）。 */
export function walkPlan(from: Pos, cells: readonly Pos[], stepMs = STEP_MS) {
  const plan: Array<{ unitId: string; from: Pos; to: Pos; mode: "walk"; durationMs: number; style: "slide" }> = [];
  let here = from;
  for (const c of cells) {
    plan.push({ unitId: FIELD_HERO, from: here, to: c, mode: "walk", durationMs: stepMs, style: "slide" });
    here = c;
  }
  return plan;
}

// ---- 互動（設施與 NPC；6B-4 前的最小版）----

export type FieldTarget =
  | { kind: "facility"; facility: string; x: number; y: number }
  | { kind: "npc"; npc: string; name: string; x: number; y: number }
  /** 站在城裡的朋友（影子，6B-4）：點了直接開名片，不用走過去。 */
  | { kind: "friend"; owner: string; name: string; x: number; y: number }
  /** 情境物件（6C-5）：走到旁邊開說明卡，能用時卡上有按鈕送 `use_field_object`。 */
  | { kind: "object"; id: string; name: string; x: number; y: number }
  /** 留言石碑（6C-5）：走到旁邊開留言板。 */
  | { kind: "note_stone"; x: number; y: number };

export type FieldSituationObject = NonNullable<FieldView["situation_objects"]>[number];

/** 格子上的情境物件；沒有為 `null`。 */
export function objectAt(field: FieldView, p: Pos): FieldSituationObject | null {
  return (field.situation_objects ?? []).find((o) => o.x === p.x && o.y === p.y) ?? null;
}

export type FieldFriend = NonNullable<FieldView["friends"]>[number];
export type FieldNpc = FieldView["npcs"][number];

/** 格子上的朋友（影子）；沒有為 `null`。 */
export function friendAt(field: FieldView, p: Pos): FieldFriend | null {
  return (field.friends ?? []).find((f) => f.x === p.x && f.y === p.y) ?? null;
}

/** 格子上的 NPC、朋友或設施（NPC 優先，再來是朋友）。 */
export function targetAt(field: FieldView, p: Pos): FieldTarget | null {
  const npc = field.npcs.find((n) => n.x === p.x && n.y === p.y);
  if (npc !== undefined) return { kind: "npc", npc: npc.id, name: npc.name_zh, x: npc.x, y: npc.y };
  const friend = friendAt(field, p);
  if (friend !== null) return { kind: "friend", owner: friend.owner, name: friend.name_zh, x: friend.x, y: friend.y };
  const f = field.facilities.find((x) => x.x === p.x && x.y === p.y);
  if (f !== undefined) return { kind: "facility", facility: f.kind, x: f.x, y: f.y };
  const o = objectAt(field, p);
  if (o !== null) return { kind: "object", id: o.id, name: o.name_zh, x: o.x, y: o.y };
  const stone = field.note_stone;
  if (stone != null && stone.x === p.x && stone.y === p.y) return { kind: "note_stone", x: stone.x, y: stone.y };
  return null;
}

/** 站在 `me` 能不能和目標互動：站在它上面或四方向相鄰。 */
export function nearTarget(me: Pos, t: Pos): boolean {
  return Math.abs(me.x - t.x) + Math.abs(me.y - t.y) <= 1;
}

/** 按 E 時的目標：先看面向的那一格，再依北、東、南、西找相鄰的，最後是腳下。 */
export function interactTarget(field: FieldView): FieldTarget | null {
  const me = field.me;
  const ahead: Readonly<Record<FieldView["me"]["facing"], readonly [number, number]>> = { n: [0, -1], e: [1, 0], s: [0, 1], w: [-1, 0] };
  const [fx, fy] = ahead[me.facing];
  const order: Pos[] = [{ x: me.x + fx, y: me.y + fy }, ...DIRS.map(([dx, dy]) => ({ x: me.x + dx, y: me.y + dy })), { x: me.x, y: me.y }];
  for (const p of order) {
    const t = targetAt(field, p);
    if (t !== null) return t;
  }
  return null;
}

/** 走到目標旁邊的路徑：可站的相鄰格（或目標本身可站時含本身）中路徑最短的；已經在旁邊為 `[]`、到不了為 `null`。 */
export function pathNextTo(field: FieldView, t: Pos): Pos[] | null {
  if (nearTarget(field.me, t)) return [];
  let best: Pos[] | null = null;
  const spots = [t, ...DIRS.map(([dx, dy]) => ({ x: t.x + dx, y: t.y + dy }))];
  for (const spot of spots) {
    const path = findPath(field, field.me, spot);
    if (path !== null && (best === null || path.length < best.length)) best = path;
  }
  return best;
}

// ---- 繪製 ----

function unitBase(id: string, x: number, y: number): UnitView {
  return {
    id,
    template_id: "npc",
    name_zh: "",
    team: "ally",
    pos: { x, y },
    hp: 1,
    max_hp: 1,
    shield: 0,
    mana: 0,
    max_mana: 0,
    stamina: 0,
    max_stamina: 0,
    ap: 0,
    move_points: 0,
    speed: 0,
    initiative: 0,
    weapon_name_zh: "",
    weapon_id: "unarmed",
    weapon_class: "melee",
    weapon_traits_zh: [],
    offhand_name_zh: "",
    offhand_traits_zh: [],
    traits_zh: [],
    ammo: 0,
    magazine: 0,
    tags: [],
    skills: [],
    statuses: [],
    stacks: {},
    cooldowns: {},
    reaction_available: false,
    reaction_rules: [],
    ap_carry: 0,
    source: 0,
    source_max: 0,
    downed: false,
    revivable: false,
    escaped: false,
    owner_id: null,
    summon_expires_round: null,
    dismissed: false,
    totem_radius: null,
    infusion: null,
    infusion_options: [],
    summon_mode: null,
    summon_target_id: null,
    commanded: false,
    infused: false,
    activations: [],
    granted_skills: [],
    facing: "south",
    equipment: [],
    gear_totals: [],
    charges: [],
    gear_skills: [],
    form: null,
    form_cooldowns: [],
  };
}

type FieldLook = NonNullable<FieldView["hero"]>;

/** 套上紙娃娃外觀（範本、`doll_look`、武器、裝備）；沒有外觀時保留 `base`（依陣營用預設外觀）。 */
function withLook(base: UnitView, look: FieldLook | null | undefined, fallbackTemplate: string): UnitView {
  return {
    ...base,
    template_id: look?.template_id ?? fallbackTemplate,
    weapon_id: look?.weapon_id ?? base.weapon_id,
    weapon_class: look?.weapon_class ?? base.weapon_class,
    doll_look: look?.doll_look ?? null,
    equipment: (look?.equipment ?? []).map((e) => ({ slot: e.slot, slot_zh: "", item_id: "", name_zh: "", affixes: [], appearance: e.appearance })),
  } as UnitView;
}

function heroUnit(field: FieldView, name: string): UnitView {
  const base = { ...unitBase(FIELD_HERO, field.me.x, field.me.y), name_zh: name, facing: FACING[field.me.facing] } as UnitView;
  return withLook(base, field.hero, "hero");
}

/** NPC 在渲染器裡的單位 ID。 */
export const npcUnitId = (id: string): string => `npc_${id}`;
/** 朋友（影子）在渲染器裡的單位 ID。 */
export const friendUnitId = (owner: string): string => `friend_${owner}`;

/** NPC → 我方紙娃娃（伺服器的外觀、沒有時照頭像換算〔6C-7〕、都沒有用預設；6B-4 不畫血條，見 `fieldDrawModel`）。 */
function npcUnit(n: FieldNpc): UnitView {
  const base = { ...unitBase(npcUnitId(n.id), n.x, n.y), name_zh: n.name_zh } as UnitView;
  return withLook(base, npcFieldLook(n), npcUnitId(n.id));
}

/** 朋友 → 我方紙娃娃（存影子時的外觀）。 */
function friendUnit(f: FieldFriend): UnitView {
  const base = { ...unitBase(friendUnitId(f.owner), f.x, f.y), name_zh: `${f.name_zh}的影子`, facing: FACING[f.facing ?? "s"] } as UnitView;
  return withLook(base, f.look, "hero");
}

export type FieldEnemy = FieldView["enemies"][number];

/** 敵群在渲染器裡的單位 ID。 */
export function enemyUnitId(enemy: FieldEnemy): string {
  return `enemy_${enemy.id}`;
}

/** 敵群 → 敵方單位（紙娃娃用陣容第一名的範本；朝向照伺服器）。 */
function enemyUnit(enemy: FieldEnemy): UnitView {
  const lead = enemy.units.find((u) => !u.third) ?? enemy.units[0];
  return {
    ...unitBase(enemyUnitId(enemy), enemy.x, enemy.y),
    name_zh: enemy.name_zh,
    team: "enemy",
    template_id: lead?.unit ?? enemy.group,
    facing: FACING[enemy.facing],
    tags: enemy.elite ? ["elite"] : [],
  } as UnitView;
}

/** 格子上的敵群（站的那一格）；沒有為 `null`。 */
export function enemyAt(field: FieldView, p: Pos): FieldEnemy | null {
  return (field.enemies ?? []).find((e) => e.x === p.x && e.y === p.y) ?? null;
}

/** 所有敵人看得到的格子（`x,y`）。走進去就開打、敵方先手。 */
export function sightCells(field: FieldView): Set<string> {
  const out = new Set<string>();
  for (const e of field.enemies ?? []) for (const [x, y] of e.sight) out.add(`${x},${y}`);
  return out;
}

/** 敵群的一行說明：名稱、精英、人數與巡邏／駐守。 */
export function enemyText(enemy: FieldEnemy): string {
  const foes = enemy.units.filter((u) => !u.third).length;
  const third = enemy.units.length - foes;
  const parts = [enemy.name_zh, enemy.elite ? "精英" : null, `${foes} 名`, third > 0 ? `另有第三方 ${third} 名` : null, enemy.patrol ? "巡邏" : "駐守"];
  return parts.filter((p) => p !== null).join("・");
}

/** `field` → 戰鬥渲染器吃的假 `BattleView`（地形、高低差、物件、表面照戰鬥畫法；主角、NPC、敵群是單位）。 */
export function fieldBattleView(field: FieldView, heroName = "你"): BattleView {
  const tiles: TileView[] = field.tiles.map((t) => ({
    x: t.x,
    y: t.y,
    height: t.height,
    terrain: t.terrain,
    surface: t.surface as Surface,
    surface_remaining: null,
    surface_team: null,
    surface_creator: null,
    object_id: null,
  }));
  const objects: ObjectView[] = field.objects.map((o) => ({ id: o.id, kind: o.kind, pos: { x: o.x, y: o.y }, hp: null, max_hp: null, burning: null }));
  const npcs: UnitView[] = [...field.npcs.map(npcUnit), ...(field.friends ?? []).map(friendUnit)];
  return {
    team: "ally",
    map_id: field.map_id,
    map_name_zh: field.name_zh,
    width: field.width,
    height: field.height,
    tiles,
    objects,
    units: [heroUnit(field, heroName), ...npcs, ...(field.enemies ?? []).map(enemyUnit)],
    traps: [],
    turn_order: [],
    active_unit: null,
    round: 1,
    max_rounds: 1,
    weather_id: null,
    weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null },
    ended: false,
    winner: null,
    end_reason: null,
    pending: null,
    source_wells: [],
    zones: [],
    runes: [],
    region: field.region,
    look: {},
  } as unknown as BattleView;
}

/** 不畫血條的單位（NPC 與朋友；6B-4）。 */
export function barlessIds(field: FieldView): Set<string> {
  return new Set([...field.npcs.map((n) => npcUnitId(n.id)), ...(field.friends ?? []).map((f) => friendUnitId(f.owner))]);
}

/** `field` → `DrawModel`：出口用戰鬥的出口格標記（淡綠框加「出」）；主角、NPC、朋友帶種族外觀；NPC 與朋友不畫血條。 */
export function fieldDrawModel(field: FieldView, heroName = "你"): DrawModel {
  const model = buildDrawModel(fieldBattleView(field, heroName), FIELD_HERO, null);
  const races = new Map<string, unknown>([[FIELD_HERO, field.hero?.race_look ?? null]]);
  for (const n of field.npcs) {
    const look = npcFieldLook(n);
    if (look != null) races.set(npcUnitId(n.id), look.race_look ?? null);
  }
  for (const f of field.friends ?? []) races.set(friendUnitId(f.owner), f.look.race_look ?? null);
  const barless = barlessIds(field);
  const units = model.units.map((u) => {
    let out = u;
    if (races.has(u.id)) out = { ...out, raceLook: (races.get(u.id) ?? null) as Readonly<Record<string, unknown>> | null };
    if (barless.has(u.id)) out = { ...out, noBar: true };
    return out;
  });
  const markers = field.exits.flatMap((e) => e.cells.map(([x, y]) => ({ x, y, kind: "exit" as const })));
  return { ...model, units, markers };
}

const DOOR_COLOR = 0xe0b060;
const STONE_COLOR = 0x7fd8ff;
/** 6C-5 地圖上的東西的標記顏色。 */
export const THING_COLOR = { event: 0xffc83a, campfire: 0xff8a3a, object: 0xe8d27a, note: 0x9fb0c8, footprint: 0xb8a07a, noteStone: 0xa0c4ff } as const;

/** 6C-5：事件「！」、營火、情境物件、朋友的腳印、留言石碑的標記（同一格只畫優先的一個：「！」＞物件＞營火＞石碑＞腳印）。 */
export function thingMarks(field: FieldView): TelegraphMark[] {
  const out: TelegraphMark[] = [];
  const taken = new Set<string>([...field.doors.map((d) => `${d.x},${d.y}`), ...field.stones.map((s) => `${s.x},${s.y}`)]);
  const add = (m: TelegraphMark) => {
    const k = key(m.pos);
    if (taken.has(k)) return;
    taken.add(k);
    out.push(m);
  };
  const ev = field.event_mark;
  if (ev != null) add({ pos: { x: ev.x, y: ev.y }, kind: "event", glyph: "！", color: THING_COLOR.event, texts: [EVENT_MARK_ZH] });
  for (const o of field.situation_objects ?? []) {
    const color = o.usable ? THING_COLOR.object : THING_COLOR.note;
    add({ pos: { x: o.x, y: o.y }, kind: "object", glyph: "◎", color, texts: [objectText(o)] });
  }
  for (const c of field.campfires ?? []) add({ pos: { x: c.x, y: c.y }, kind: "campfire", glyph: "火", color: THING_COLOR.campfire, texts: [CAMPFIRE_ZH] });
  const stone = field.note_stone;
  if (stone != null) add({ pos: { x: stone.x, y: stone.y }, kind: "note_stone", glyph: "碑", color: THING_COLOR.noteStone, texts: [noteStoneText(stone.count)] });
  for (const f of field.footprints ?? []) add({ pos: { x: f.x, y: f.y }, kind: "footprint", glyph: "足", color: THING_COLOR.footprint, texts: [`${f.name_zh}走過這裡`] });
  return out;
}

export const EVENT_MARK_ZH = "有事情發生：走過去看看";
export const CAMPFIRE_ZH = "營火：站上去可以紮營";

export function noteStoneText(count: number): string {
  return `留言石碑：${count} 則留言（走過去看）`;
}

/** 情境物件的一行說明：名稱與能做什麼。 */
export function objectText(o: FieldSituationObject): string {
  if (o.use === "note") return o.name_zh;
  if (!o.usable) return `${o.name_zh}（${o.problem_zh ?? "現在不能用"}）`;
  return `${o.name_zh}（${o.use === "encounter" ? "走過去挑戰" : "走過去調查"}）`;
}

/** 朋友的腳印（格子上的第一個）；沒有為 `null`。 */
export function footprintAt(field: FieldView, p: Pos): NonNullable<FieldView["footprints"]>[number] | null {
  return (field.footprints ?? []).find((f) => f.x === p.x && f.y === p.y) ?? null;
}
/** 敵人視野的淡紅（同 HUD 的 HP 紅）。 */
export const SIGHT_COLOR = 0xe04a3a;

/** 敵人視野的格子（門與傳送石那格不算，它們有自己的標示），依座標排序。 */
export function sightRegion(field: FieldView): Pos[] {
  const marked = new Set<string>([...field.doors.map((d) => `${d.x},${d.y}`), ...field.stones.map((s) => `${s.x},${s.y}`)]);
  return [...sightCells(field)]
    .filter((c) => !marked.has(c))
    .map((c) => {
      const [x, y] = c.split(",").map(Number) as [number, number];
      return { x, y };
    })
    .sort((a, b) => a.y - b.y || a.x - b.x);
}

/**
 * 門與傳送石的淡色標示（借用環境預告的半透明外框＋小圖示）、精英的「精」；`hover` 是滑鼠所在格。
 * 敵人的視野（6A-4g）照地表併塊畫成一塊：淡紅填色、只描外緣，不再每格紅框＋格角小圓（那個小圓是空字的徽章底，沒有意思）。
 */
export function fieldHighlights(field: FieldView, hover: Pos | null): Highlights {
  const telegraph: TelegraphMark[] = [
    ...field.doors.map((d) => ({ pos: { x: d.x, y: d.y }, kind: "door", glyph: "門", color: DOOR_COLOR, texts: [d.to_name_zh] })),
    ...field.stones.map((s) => ({ pos: { x: s.x, y: s.y }, kind: "stone", glyph: "◆", color: s.unlocked ? STONE_COLOR : HIGHLIGHT.well, texts: ["傳送石"] })),
    ...(field.enemies ?? [])
      .filter((e) => e.elite)
      .map((e) => ({ pos: { x: e.x, y: e.y }, kind: "elite", glyph: "精", color: SIGHT_COLOR, texts: [enemyText(e)] })),
    ...thingMarks(field),
  ];
  const sight = sightRegion(field);
  const regions = sight.length > 0 ? [{ cells: sight, color: SIGHT_COLOR }] : [];
  return { moves: [], attacks: [], directions: [], preview: [], telegraph, focus: null, hover, overlays: [], picked: [], regions };
}

/** 滑鼠所在格的一行說明（出口往哪、門通到哪、傳送石、設施、NPC）；沒有東西為 `null`。 */
export function hoverText(field: FieldView, p: Pos | null): string | null {
  if (p === null) return null;
  const portal = portalAt(field, p);
  if (portal?.kind === "exit") return `往 ${portal.name}`;
  if (portal?.kind === "door") return portal.name;
  if (portal?.kind === "stone") return "傳送石";
  const enemy = enemyAt(field, p);
  if (enemy !== null) return enemyText(enemy);
  const ev = field.event_mark;
  if (ev != null && ev.x === p.x && ev.y === p.y) return EVENT_MARK_ZH;
  if (sightCells(field).has(key(p))) return field.sneaking === true ? "敵人的視野（潛行中，減半）" : "敵人的視野";
  const t = targetAt(field, p);
  if (t?.kind === "npc") {
    const n = field.npcs.find((x) => x.id === t.npc);
    const extra = [n?.rank_zh ? `好感：${n.rank_zh}` : null, n?.alert_zh ?? null].filter((s) => s !== null);
    return extra.length > 0 ? `${t.name}（${extra.join("・")}）` : t.name;
  }
  if (t?.kind === "friend") return `${t.name}的影子（點了看名片）`;
  if (t?.kind === "facility") return FACILITY_ZH[t.facility] ?? t.facility;
  if (t?.kind === "object") {
    const o = objectAt(field, p);
    return o === null ? t.name : objectText(o);
  }
  if (t?.kind === "note_stone") return noteStoneText(field.note_stone?.count ?? 0);
  if ((field.campfires ?? []).some((c) => c.x === p.x && c.y === p.y)) return CAMPFIRE_ZH;
  const print = footprintAt(field, p);
  if (print !== null) return `${print.name_zh}走過這裡`;
  return null;
}

/** 地圖區畫什麼：有實地地圖畫可走動畫面，沒有就照舊畫地點節點圖（兩種方式並存）。 */
export function mapPaneKind(view: { field?: FieldView | null }): "field" | "nodes" {
  return view.field != null ? "field" : "nodes";
}

/**
 * 換地圖時跳的地名（21.7「只跳一行地名」）：`prev` 是上一個畫面的實地地圖 ID（`undefined`＝第一次載入、
 * `null`＝上一個地點沒有實地地圖）。第一次載入不跳；換到另一張實地地圖時回傳新地圖的名稱。
 */
export function placeBanner(prev: string | null | undefined, next: FieldView | null | undefined): string | null {
  if (prev === undefined || next == null) return null;
  return next.map_id === prev ? null : next.name_zh;
}

export const FACILITY_ZH:Readonly<Record<string, string>> = {
  shop: "商店",
  smithy: "鐵匠",
  tavern: "酒館",
  mentor: "導師",
  notice_board: "布告欄",
  hire: "傭兵",
  enchanter: "附魔台",
};
