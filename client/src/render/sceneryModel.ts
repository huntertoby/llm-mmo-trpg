// 實地地圖的「只畫」外觀（Phase 6B-ART1）：建築、門、室內外框、家具。純資料與純函式，畫法在 townArt.ts／interiorArt.ts，
// 放進場景在 sceneryLayer.ts。全部只換外觀：不影響走路、視線與戰鬥（規則照伺服器的地形與物件）。
import type { Pos } from "../api/types";
import { roofRows, type BuildingSpec, type DoorStyle } from "./townArt";
import type { FurnitureSpec, RoomPalette, RugCell, WallDecor, WallHanging } from "./interiorArt";

export interface BuildingScene {
  spec: BuildingSpec;
  /** 範圍的左上角（格）。 */
  x: number;
  y: number;
}

/** 畫在建築正面的門（門格在建築範圍內；隱藏門揭露前伺服器不給，所以不畫）。 */
export interface DoorScene {
  x: number;
  y: number;
  style: DoorStyle;
  /**
   * 側牆的門（6D-ART2：主城酒館的東牆、鐵匠鋪的西牆）：門板畫在建築正面同一欄（`drawY` ＝ 建築最下一列），
   * 入口光圈畫在門外側那一格（`side` 那一邊）。最下一列的門沒有這兩個欄位。
   */
  side?: "w" | "e";
  drawY?: number;
}

/** 主城的中央傳送陣（6D-ART2）：傳送石那一格；`open` ＝ 已開放的區（大世界圖的 `atlas.regions`，依區域 ID 排序）。 */
export interface PlazaScene {
  x: number;
  y: number;
  open: readonly string[];
}

export interface InteriorScene {
  palette: RoomPalette;
  decor: WallDecor[];
  /** 後牆上半段的掛件（6V-3：工具、掛燈、小窗；沒有＝空）。 */
  hangings?: WallHanging[];
  /** 紅地毯（導師殿）：左上與寬高（格）；沒有＝`null`。 */
  rug: { x: number; y: number; w: number; h: number } | null;
  /** 出口格（下牆中間）。 */
  exits: Pos[];
}

export interface FieldScenery {
  buildings: BuildingScene[];
  doors: DoorScene[];
  interior: InteriorScene | null;
  /** 格子（`x,y`）→ 家具外觀。 */
  furniture: Readonly<Record<string, FurnitureSpec>>;
  /** 主城的中央傳送陣與五面區旗；其他地圖沒有（省略或 `null`）。 */
  plaza?: PlazaScene | null;
}

export const EMPTY_SCENERY: FieldScenery = { buildings: [], doors: [], interior: null, furniture: {} };

/** 室內一格的畫法：後牆那一列（y＝0）由後牆整張畫，不在這裡。 */
export type InteriorPiece =
  | { kind: "floor"; x: number; y: number; rug: RugCell | null }
  | { kind: "wall"; x: number; y: number; side: { n: boolean; e: boolean; w: boolean } }
  | { kind: "exit"; x: number; y: number };

const key = (x: number, y: number): string => `${x},${y}`;

/**
 * 室內每一格（y ≥ 1）的畫法：出口格、牆格（靠房間那幾邊畫牆邊）、其他是地板（地毯範圍內鋪地毯）。
 * `walls` ＝ 牆地形的格子（`x,y`）。依座標排序（逐列、由左到右）。
 */
export function interiorPieces(room: InteriorScene, width: number, height: number, walls: ReadonlySet<string>): InteriorPiece[] {
  const exits = new Set(room.exits.map((p) => key(p.x, p.y)));
  const inside = (x: number, y: number) => x >= 0 && y >= 1 && x < width && y < height && !walls.has(key(x, y));
  const out: InteriorPiece[] = [];
  for (let y = 1; y < height; y++) {
    for (let x = 0; x < width; x++) {
      if (exits.has(key(x, y))) out.push({ kind: "exit", x, y });
      else if (walls.has(key(x, y))) out.push({ kind: "wall", x, y, side: { n: inside(x, y - 1) && y - 1 >= 1, e: inside(x + 1, y), w: inside(x - 1, y) } });
      else out.push({ kind: "floor", x, y, rug: rugCell(room.rug, x, y) });
    }
  }
  return out;
}

function rugCell(rug: InteriorScene["rug"], x: number, y: number): RugCell | null {
  if (rug === null) return null;
  if (x < rug.x || y < rug.y || x >= rug.x + rug.w || y >= rug.y + rug.h) return null;
  return { n: y === rug.y, s: y === rug.y + rug.h - 1, w: x === rug.x, e: x === rug.x + rug.w - 1 };
}

/**
 * 這一格的人會被建築的屋頂蓋住（站在屋後那一列，屋頂往上多蓋的 1 格）；渲染器替他另外畫虛線剪影（同被高格擋住）。
 * 頭頂圖示是 DOM，不受影響。
 */
export function roofCovers(scenery: FieldScenery | undefined, p: Pos): boolean {
  if (scenery === undefined) return false;
  return scenery.buildings.some((b) => roofRows(b.spec) > 0 && p.y === b.y - 1 && p.x >= b.x && p.x < b.x + b.spec.w);
}
