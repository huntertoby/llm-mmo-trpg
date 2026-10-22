// 視圖 → 繪製模型（純函式；PixiJS 只負責照著畫）。
import type { BattleView, Facing, Pos, Surface } from "../api/types";
import type { DollInput } from "../render/appearance";
import type { GearLook } from "../render/gearIcon";
import type { SummonLookDraw } from "../render/summonArt";
import {
  HIGHLIGHT,
  SURFACES,
  TEAM_COLORS,
  objectStyle,
  surfaceName,
  terrainStyle,
} from "./glossary";
import { bombCountdown } from "./bombs";
import { objectiveMarkers, type ObjectiveMarker } from "./objective";
import { chargeCountdown } from "./followup";
import { auraTiles, isTotem, remainingRounds } from "./summons";
import { onField, unitMarkers } from "./units";
import { runeDraws, type RuneDraw } from "./runes";
import { zoneDraws, type ZoneDraw } from "./zones";

/** 殘影分身（外觀款式 afterimage）複製召喚者的外觀：回傳召喚者的紙娃娃輸入；其他單位或找不到召喚者為 `undefined`。 */
function copyTarget(view: BattleView, u: BattleView["units"][number]): DollInput | undefined {
  if (u.summon_look?.variant !== "afterimage") return undefined;
  const owner = view.units.find((x) => x.id === u.owner_id);
  if (owner === undefined) return undefined;
  return {
    template: owner.template_id,
    team: owner.team,
    summon: false,
    weaponId: owner.weapon_id,
    weaponClass: owner.weapon_class,
    equipment: (owner.equipment ?? []).map((e) => ({ slot: e.slot, appearance: e.appearance })),
  };
}

export interface TileDraw {
  x: number;
  y: number;
  height: number;
  /** 地形色 ＋ 表面色 ＋ 高度明暗之後的填色。 */
  fill: number;
  /** 角落的高度數字（高度 0 也顯示，方便比較）。 */
  heightLabel: string;
  terrain: string;
  /** 表面（火、油、冰……）；前端美術在圖塊上疊半透明表面色。 */
  surface: Surface;
  terrainName: string;
  surfaceName: string | null;
  blocked: boolean;
  deadly: boolean;
  wall: boolean;
}

export interface ObjectDraw {
  id: string;
  /** 物件種類（美術對照用）。 */
  kind: string;
  x: number;
  y: number;
  name: string;
  glyph: string;
  fill: number;
  flammable: boolean;
  burning: boolean;
  /** 暫時障礙（Phase 3-11）還剩幾次環境回合；永久為 `null`。 */
  expiresIn: number | null;
  floor: boolean;
  /** 0–1；沒有耐久的物件為 `null`。 */
  hpRatio: number | null;
}

export interface UnitDraw {
  id: string;
  x: number;
  y: number;
  marker: string;
  /** 單位範本 ID（美術對照用）。 */
  template: string;
  name: string;
  team: "ally" | "enemy";
  fill: number;
  hpRatio: number;
  shieldRatio: number;
  active: boolean;
  hero: boolean;
  downed: boolean;
  /** 召喚物（Phase 3D-4b）：畫成菱形加外框，不分陣營。 */
  summon: boolean;
  /** 圖騰：不移動、不攻擊的召喚物，角落標「圖」。 */
  totem: boolean;
  /** 召喚物還能行動的輪數（含本輪）；一般單位為 `null`。 */
  remaining: number | null;
  /** 倒下而且可以被復活（Phase 3D-8b）。 */
  revivable: boolean;
  /** 身上定時炸彈還要幾次環境回合爆炸（Phase 3D-8b）；沒有炸彈為 `null`。 */
  bomb: number | null;
  /** 延遲段（蓄力，Phase 3F-4b）還要幾回合釋放；沒有蓄力為 `null`。 */
  charge?: number | null;
  /** 召喚物身上有待施放的灌注技能（Phase 3-33d，頭上畫「灌」）。 */
  infused?: boolean;
  /** 朝向（Phase 3D-8d）：圖示外緣畫小箭頭；背後格站著近戰敵人時會被背刺。 */
  facing: Facing;
  /** 武器 ID（紙娃娃主手外觀用）。 */
  weaponId: string;
  /** 武器大類（melee、ranged、focus）：不認得 `weaponId` 時依此退回武器圖。 */
  weaponClass: string;
  /** 召喚物外觀（Phase 3-33h1）：沒有時（一般單位、舊資料）為 `null`，召喚物退回人形骷髏。 */
  summonLook?: SummonLookDraw | null;
  /** 殘影分身複製的對象（召喚者）的紙娃娃輸入（Phase 3-33h1）；其他單位為 `undefined`。 */
  copyOf?: DollInput | undefined;
  /** 身上穿的裝備（Phase 3G-G5b，紙娃娃依各欄位外觀畫）；舊資料沒有時視為沒穿。 */
  equipment?: ReadonlyArray<{ slot: string; appearance?: GearLook | null }>;
}

export interface TrapDraw {
  x: number;
  y: number;
  color: number;
  /** 被揭露的敵方陷阱（Phase 3C-6a；和我方陷阱用不同記號與顏色）。 */
  revealed: boolean;
}

/** 尚未被取用的源泉格（Phase 3C-4a；3C-6a 畫在地圖上）。 */
export interface WellDraw {
  x: number;
  y: number;
}

export interface AuraDraw {
  x: number;
  y: number;
}

export interface DrawModel {
  width: number;
  height: number;
  tiles: TileDraw[];
  objects: ObjectDraw[];
  /** 倒下的單位在前（先畫，壓在下面）。 */
  units: UnitDraw[];
  traps: TrapDraw[];
  /** 在場圖騰的光環涵蓋的格子（淡色底，Phase 3D-4b）。 */
  auras: AuraDraw[];
  /** 持續區域的格子（半透明底色，移動型附方向箭頭；Phase 3D-5）。 */
  zones: ZoneDraw[];
  /** 格子上的符文（施放者陣營色外框＋元素色內紋；Phase 3-23）。 */
  runes: RuneDraw[];
  /** 尚未被取用的源泉格（我方單位進入時 +1 源力）。 */
  wells: WellDraw[];
  /** 勝利條件的目標格（撤離的出口格、守點的守點格；Phase 3-22）。 */
  markers: ObjectiveMarker[];
}

export const MAX_HEIGHT = 3;

function channel(color: number, shift: number): number {
  return (color >> shift) & 0xff;
}

function rgb(r: number, g: number, b: number): number {
  const c = (v: number) => Math.max(0, Math.min(255, Math.round(v)));
  return (c(r) << 16) | (c(g) << 8) | c(b);
}

/** 把 `over` 以 `alpha` 疊在 `base` 上。 */
export function blend(base: number, over: number, alpha: number): number {
  const mix = (s: number) => channel(base, s) * (1 - alpha) + channel(over, s) * alpha;
  return rgb(mix(16), mix(8), mix(0));
}

/** 高度明暗：高度 0 稍暗、每高一層更亮（越高越亮）。 */
export function shadeForHeight(color: number, height: number): number {
  const h = Math.max(0, Math.min(MAX_HEIGHT, height));
  const factor = 0.78 + 0.12 * h;
  return rgb(channel(color, 16) * factor, channel(color, 8) * factor, channel(color, 0) * factor);
}

export function tileFill(terrain: string, surface: keyof typeof SURFACES, height: number): number {
  const t = terrainStyle(terrain);
  const s = SURFACES[surface];
  const base = s === null ? t.color : blend(t.color, s.color, s.alpha);
  // 深淵等不可站立的地形不做高度明暗（一眼看得出是洞）。
  return t.blocked && !t.wall ? base : shadeForHeight(base, height);
}

function ratio(value: number, max: number): number {
  return max <= 0 ? 0 : Math.max(0, Math.min(1, value / max));
}

/** `activeId` 省略時以 `view.active_unit` 為行動中的單位；逐步播放時由播放器指定。 */
export function buildDrawModel(
  view: BattleView,
  heroId: string,
  activeId: string | null | undefined = undefined,
): DrawModel {
  const acting = activeId === undefined ? view.active_unit : activeId;
  const tiles: TileDraw[] = view.tiles.map((t) => {
    const style = terrainStyle(t.terrain);
    const surface = SURFACES[t.surface];
    return {
      x: t.x,
      y: t.y,
      height: t.height,
      fill: tileFill(t.terrain, t.surface, t.height),
      heightLabel: String(t.height),
      terrain: t.terrain,
      surface: t.surface,
      terrainName: style.name,
      surfaceName: surface === null ? null : surfaceName(t.surface),
      blocked: style.blocked,
      deadly: style.deadly,
      wall: style.wall,
    };
  });
  const objects: ObjectDraw[] = view.objects.map((o) => {
    const style = objectStyle(o.kind);
    return {
      id: o.id,
      kind: o.kind,
      x: o.pos.x,
      y: o.pos.y,
      name: style.name,
      glyph: style.glyph,
      fill: style.color,
      flammable: style.flammable,
      burning: o.burning !== null && o.burning > 0,
      expiresIn: o.expires_in ?? null,
      floor: style.floor,
      hpRatio: o.hp === null || o.max_hp === null ? null : ratio(o.hp, o.max_hp),
    };
  });
  const markers = unitMarkers(view.units);
  const units: UnitDraw[] = view.units
    .filter(onField)
    .map((u) => ({
      id: u.id,
      x: u.pos.x,
      y: u.pos.y,
      marker: markers.get(u.id) ?? "?",
      template: u.template_id,
      name: u.name_zh,
      team: u.team,
      fill: TEAM_COLORS[u.team],
      hpRatio: ratio(u.hp, u.max_hp),
      shieldRatio: ratio(u.shield, u.max_hp),
      active: u.id === acting,
      hero: u.id === heroId,
      downed: u.downed,
      summon: u.owner_id !== null,
      totem: isTotem(u),
      remaining: remainingRounds(view, u),
      revivable: u.revivable,
      bomb: bombCountdown(u),
      charge: chargeCountdown(u.statuses),
      infused: u.infused_skill_id != null,
      facing: u.facing,
      weaponId: u.weapon_id,
      weaponClass: u.weapon_class,
      summonLook: u.summon_look ?? null,
      copyOf: copyTarget(view, u),
      equipment: (u.equipment ?? []).map((e) => ({ slot: e.slot, appearance: e.appearance })),
    }))
    // 倒下的先畫（在底層），其餘依 y 由上往下排序（下面的人蓋住上面的人）
    .sort((a, b) => Number(b.downed) - Number(a.downed) || a.y - b.y);
  const traps: TrapDraw[] = view.traps.map((t) => {
    const revealed = t.team !== view.team;
    return { x: t.pos.x, y: t.pos.y, color: revealed ? HIGHLIGHT.trap_revealed : HIGHLIGHT.trap, revealed };
  });
  const wells: WellDraw[] = (view.source_wells ?? []).map((p) => ({ x: p.x, y: p.y }));
  const seen = new Set<string>();
  const auras: AuraDraw[] = [];
  for (const u of view.units) {
    if (u.totem_radius === null || u.downed || !onField(u)) continue;
    for (const t of auraTiles(u.pos, u.totem_radius, view)) {
      const key = `${t.x},${t.y}`;
      if (!seen.has(key)) {
        seen.add(key);
        auras.push(t);
      }
    }
  }
  const zones = zoneDraws(view);
  const runes = runeDraws(view);
  const goalMarkers = objectiveMarkers(view.objective);
  return { width: view.width, height: view.height, tiles, objects, units, traps, auras, zones, runes, wells, markers: goalMarkers };
}

export function tileAt(model: DrawModel, p: Pos): TileDraw | undefined {
  return model.tiles[p.y * model.width + p.x];
}
