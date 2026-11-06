// 實地地圖的出口路牌（UI-E4；docs/art/全遊戲一致性巡檢.md #11、偷懶自查 G6）：拿掉亮綠色的「出」方框，
// 改成地上的路牌（木牌加箭頭，指向出口方向）＋淡淡的地面光圈；滑過（觸控：點一下）才出現綠框和目的地名。
// 只畫，不影響走路與換地圖（出口格照舊由 `portalAt` 判斷）。室內的出口已經有門墊與入口光（`interiorArt.drawExitCell`），不另畫路牌。
// 座標是格子的左上角（TILE_SIZE 一格）；線條照墨線繪本畫法：深棕墨線＋木色填色。
import type { Graphics } from "pixi.js";

export type ExitDir = "n" | "e" | "s" | "w";

interface Pos {
  x: number;
  y: number;
}

/** 一個出口（伺服器的一筆 `exits`）畫成：每一格一個地面光圈，路牌只插在 `sign` 那一格。 */
export interface ExitSignDraw {
  id: string;
  dir: ExitDir;
  cells: readonly Pos[];
  sign: Pos;
  /** 目的地名（滑過時的小牌：「往霧渡鎮」）。 */
  name: string;
  /** 室內的出口：不畫路牌與光圈（已經有門墊與入口光），滑過照樣出現綠框和目的地名。 */
  bare: boolean;
}

/** 墨線、木色、光圈色。 */
export const SIGN_INK = 0x281e14;
export const SIGN_WOOD = 0xa8743e;
export const SIGN_WOOD_DARK = 0x7a5230;
export const SIGN_PAINT = 0xf2e2bc;
export const GLOW_COLOR = 0xfff0b8;
/** 地面光圈的不透明度（外圈、內圈）：淡淡的，不像按鈕。 */
export const GLOW_ALPHA: readonly [number, number] = [0.16, 0.14];

/**
 * 出口朝哪一邊：出口格都在地圖的某一邊上就是那一邊；不在邊上時照出口格的中心相對地圖中心，取差得多的那一軸。
 * 同分時照 南＞東＞北＞西 的順序（固定，同一張地圖一定得到同一個方向）。
 */
export function exitDir(cells: readonly (readonly [number, number])[], width: number, height: number): ExitDir {
  if (cells.length === 0) return "s";
  const all = (f: (c: readonly [number, number]) => boolean) => cells.every(f);
  if (all(([, y]) => y === height - 1)) return "s";
  if (all(([x]) => x === width - 1)) return "e";
  if (all(([, y]) => y === 0)) return "n";
  if (all(([x]) => x === 0)) return "w";
  const cx = cells.reduce((s, [x]) => s + x, 0) / cells.length - (width - 1) / 2;
  const cy = cells.reduce((s, [, y]) => s + y, 0) / cells.length - (height - 1) / 2;
  if (Math.abs(cy) >= Math.abs(cx)) return cy >= 0 ? "s" : "n";
  return cx >= 0 ? "e" : "w";
}

/** 路牌插在哪一格：出口格依 (y, x) 排序後的第一格（多格的出口只插一塊）。 */
export function signCell(cells: readonly (readonly [number, number])[]): Pos {
  const sorted = [...cells].sort((a, b) => a[1] - b[1] || a[0] - b[0]);
  const [x, y] = sorted[0] ?? [0, 0];
  return { x, y };
}

/** 實地地圖的出口 → 路牌資料（室內的標 `bare`）。 */
export function exitSigns(
  field: { width: number; height: number; interior: boolean; exits: readonly { id: string; cells: readonly (readonly [number, number])[]; to_name_zh: string }[] },
): ExitSignDraw[] {
  return field.exits
    .filter((e) => e.cells.length > 0)
    .map((e) => ({
      id: e.id,
      dir: exitDir(e.cells, field.width, field.height),
      cells: e.cells.map(([x, y]) => ({ x, y })).sort((a, b) => a.y - b.y || a.x - b.x),
      sign: signCell(e.cells),
      name: e.to_name_zh,
      bare: field.interior,
    }));
}

/** 一格的地面光圈（扁橢圓兩層，格子中下方）。 */
export function drawExitGlow(g: Graphics, ox: number, oy: number, T: number): void {
  g.ellipse(ox + T / 2, oy + T * 0.62, T * 0.46, T * 0.26).fill({ color: GLOW_COLOR, alpha: GLOW_ALPHA[0] });
  g.ellipse(ox + T / 2, oy + T * 0.62, T * 0.28, T * 0.15).fill({ color: GLOW_COLOR, alpha: GLOW_ALPHA[1] });
}

/** 木牌的外形（相對木牌中心，寬 w、高 h）：東西向是一頭尖的箭頭牌，南北向是方牌（箭頭畫在牌面上）。 */
export function plankShape(dir: ExitDir, w: number, h: number): number[] {
  const hw = w / 2;
  const hh = h / 2;
  const tip = h * 0.55;
  if (dir === "e") return [-hw, -hh, hw - tip, -hh, hw, 0, hw - tip, hh, -hw, hh];
  if (dir === "w") return [hw, -hh, -hw + tip, -hh, -hw, 0, -hw + tip, hh, hw, hh];
  return [-hw, -hh, hw, -hh, hw, hh, -hw, hh];
}

/** 牌面上的箭頭（相對木牌中心）：東西向是一條橫線＋箭頭，南北向是直的。 */
export function arrowShape(dir: ExitDir, s: number): number[] {
  const a = s * 0.5;
  const b = s * 0.3;
  const shaft = s * 0.12;
  // 指向 +x 的箭頭，再依方向旋轉
  const right = [-a, -shaft, a - b, -shaft, a - b, -b, a, 0, a - b, b, a - b, shaft, -a, shaft];
  const out: number[] = [];
  for (let i = 0; i < right.length; i += 2) {
    const x = right[i] as number;
    const y = right[i + 1] as number;
    if (dir === "e") out.push(x, y);
    else if (dir === "w") out.push(-x, y);
    else if (dir === "s") out.push(-y, x);
    else out.push(y, -x);
  }
  return out;
}

/**
 * 路牌（木樁＋木牌＋箭頭），立在格子中下方偏一側：南北向的出口靠格子左側（不擋住走道正中）、東西向靠上側。
 * 牌子比格子高，會蓋到上一排一點（畫在這一排的物件層，照 y 排序）。
 */
export function drawExitSign(g: Graphics, ox: number, oy: number, T: number, dir: ExitDir): void {
  const px = ox + (dir === "n" || dir === "s" ? T * 0.24 : T * 0.5);
  const base = oy + (dir === "e" || dir === "w" ? T * 0.66 : T * 0.8);
  const postW = T * 0.09;
  const postH = T * 0.62;
  // 地上的小影子
  g.ellipse(px, base, T * 0.14, T * 0.05).fill({ color: 0x000000, alpha: 0.22 });
  // 木樁
  g.rect(px - postW / 2, base - postH, postW, postH).fill({ color: SIGN_WOOD_DARK }).stroke({ width: 1.4, color: SIGN_INK });
  // 木牌
  const w = dir === "n" || dir === "s" ? T * 0.46 : T * 0.6;
  const h = T * 0.3;
  const cx = dir === "w" ? px - T * 0.05 : dir === "e" ? px + T * 0.05 : px + T * 0.06;
  const cy = base - postH + h * 0.55;
  const plank = plankShape(dir, w, h).map((v, i) => v + (i % 2 === 0 ? cx : cy));
  g.poly(plank).fill({ color: SIGN_WOOD }).stroke({ width: 1.6, color: SIGN_INK });
  // 木紋一條
  g.moveTo(cx - w * 0.32, cy + h * 0.18)
    .lineTo(cx + w * 0.18, cy + h * 0.18)
    .stroke({ width: 0.9, color: SIGN_WOOD_DARK, alpha: 0.9 });
  // 箭頭（淺色漆＋墨線）
  const arrow = arrowShape(dir, dir === "n" || dir === "s" ? h * 0.9 : h * 1.15).map((v, i) => v + (i % 2 === 0 ? cx - (dir === "e" ? w * 0.06 : dir === "w" ? -w * 0.06 : 0) : cy - h * 0.04));
  g.poly(arrow).fill({ color: SIGN_PAINT }).stroke({ width: 1, color: SIGN_INK, alpha: 0.85 });
}

/** 滑過時的綠框（原本的「出」框，只在滑過或觸控點一下時出現）。 */
export function drawExitFrame(g: Graphics, ox: number, oy: number, T: number, color: number): void {
  g.roundRect(ox + 3, oy + 3, T - 6, T - 6, 6).fill({ color, alpha: 0.12 }).stroke({ width: 3, color, alpha: 0.95 });
  g.roundRect(ox + 9, oy + 9, T - 18, T - 18, 4).stroke({ width: 1.5, color, alpha: 0.65 });
}

/**
 * 點到格子時要不要先「亮出口」（UI-E4 觸控：沒有滑過，點一下先顯示綠框和目的地名，再點一次同一個出口才走過去）。
 * 滑鼠、觸控筆照舊點了就走（滑過時已經看得到綠框）。回傳 `arm`＝這次亮起的出口 ID（`null`＝不亮、照常處理點擊）。
 */
export function exitTap(signs: readonly ExitSignDraw[], tile: Pos, pointer: string, armed: string | null): { arm: string | null } {
  const exit = exitAtCell(signs, tile);
  if (exit === null || pointer !== "touch" || armed === exit.id) return { arm: null };
  return { arm: exit.id };
}

/**
 * 出口的說明字：「往霧渡鎮」；地名本身已經是「往……」開頭（例「往灰燼荒原的渡口」）就不再加「往」。
 * UI-E3c 小修 7：「往」後面不空格（和「往灰燼荒原的渡口」統一）。
 */
export function exitLabel(name: string): string {
  return name.startsWith("往") ? name : `往${name}`;
}

/**
 * 滑鼠所在格要不要畫白框（UI-E3c 小修 6）：滑過的格子屬於正在亮的出口時只留綠框（不疊白框，
 * 白框的下緣也不會壓在下一格出口綠框的上緣多出一條線）。
 */
export function hoverFrameCell(hover: Pos | null, exit: ExitSignDraw | null | undefined): Pos | null {
  if (hover === null || exit == null) return hover;
  return exit.cells.some((c) => c.x === hover.x && c.y === hover.y) ? null : hover;
}

/** 滑過的那一格屬於哪個出口（沒有＝`null`）。 */
export function exitAtCell(signs: readonly ExitSignDraw[], p: Pos | null): ExitSignDraw | null {
  if (p === null) return null;
  return signs.find((s) => s.cells.some((c) => c.x === p.x && c.y === p.y)) ?? null;
}
