// 修士用的紙娃娃新部件（Phase 5A-ART3；移植自 docs/art/sample/storyDoll.js「敵人家族用的小部件」，需求 docs/art/敵人外觀.md 第 3 節第 3 段）。
// 髮髻、赤膊、念珠、圍裙、背物（藥葫蘆、木偶箱）、腰掛黃符、白紗面罩、白羽披肩、劍穗（inkGear 的劍）、拂塵／符紙／傀儡線。
// 不認得的 kind／form 一律不畫、不出錯。座標同 inkDoll.ts（腳底 (0,0)、頭心 (0,-42)）。
import type { Ctx } from "./artDraw";
import type { GearItem, Look } from "./appearance";
import { darken } from "./color";
import { dot, ellPts, ink, INK, MAT, stroke, type Pt, type View } from "./inkStyle";
import { orientWeapon, restLean, type WeaponPoseOpt } from "./inkWeaponFrame";

const RED = "#c0392b";
const HAIR_FALLBACK = "#6a3a1e";

// ============================== 頭髮：髮髻 ==============================
/** 髮髻（`hair: "bun"`）的正面、側面：短髮＋頭頂一顆髻＋髮帶。回傳 false ＝ 不是髮髻。 */
export function drawBunHair(ctx: Ctx, look: Look, view: View): boolean {
  if (look.hair !== "bun") return false;
  const c = look.hairColor ?? HAIR_FALLBACK;
  if (view === "back") return true; // 背面的髮髻另外畫（drawBunBack）
  if (view === "front") ink(ctx, "hair-bun-f", [[-9.6, -42], [-10, -48], [-5, -52.5], [5, -52.5], [10, -48], [9.6, -42], [6, -46.4], [0, -47.4], [-6, -46.4]], c);
  else ink(ctx, "hair-bun-s", [[-9.2, -38], [-9.4, -47], [-4, -52.5], [3, -52.6], [8.6, -48.5], [7, -46.4], [2, -46], [-1.4, -43], [-3, -38], [-6, -36]], c);
  const [bx, by] = view === "front" ? [0, -55.4] : [-2.6, -55];
  drawBun(ctx, view, bx, by, c, look.bunBand);
  return true;
}

function drawBun(ctx: Ctx, view: View, bx: number, by: number, c: string, band: string | undefined): void {
  ink(ctx, `bun-${view}`, ellPts(bx, by, 3.4, 3, 12), c);
  stroke(ctx, `bun-band-${view}`, [[bx - 2.6, by + 2.2], [bx + 2.6, by + 2.2]], 1, band ?? RED);
}

/** 背面頭頂的髮髻（頭髮已照短髮畫好；帽子蓋頭頂時不畫）。 */
export function drawBunBack(ctx: Ctx, look: Look, coveredTop: boolean): void {
  if (look.hair !== "bun" || coveredTop) return;
  drawBun(ctx, "back", 0, -55.4, look.hairColor ?? HAIR_FALLBACK, look.bunBand);
}

// ============================== 身體：赤膊、圍裙 ==============================
const TORSO: Record<View, Pt[]> = {
  front: [[-7, -33], [7, -33], [6, -23], [8, -14], [0, -12.5], [-8, -14], [-6, -23]],
  side: [[-4, -33], [3.4, -33], [5, -27], [4, -22], [5.2, -14], [-1, -12.5], [-5.6, -14], [-4.2, -22]],
  back: [[-7, -33], [7, -33], [6, -23], [8, -14], [0, -12.5], [-8, -14], [-6, -23]],
};

/** 赤膊（body `kind: "bare"`，護法武僧）：膚色軀幹＋胸線，腰間一條布帶（布帶色＝裝備色）。 */
export function drawBareBody(ctx: Ctx, view: View, skin: string, sash: string): void {
  const F = view !== "side";
  ink(ctx, `torso-bare-${view}`, TORSO[view], skin);
  if (view === "front") {
    stroke(ctx, "pec-l", [[-5, -28.6], [-1.6, -27.4]], 0.45, darken(skin, 0.35));
    stroke(ctx, "pec-r", [[5, -28.6], [1.6, -27.4]], 0.45, darken(skin, 0.35));
  }
  const line: Pt[] = F ? [[-6.4, -22.6], [6.4, -22.6]] : [[-4.2, -22.6], [4.4, -22.6]];
  stroke(ctx, `sash-bare-${view}`, line, 2.4, INK);
  stroke(ctx, `sash-bare2-${view}`, line, 1.6, sash);
}

/** 圍裙（robe 的 `apron`，煉丹師）：袍子前面一片；背面看不到。 */
export function drawApron(ctx: Ctx, it: GearItem, view: View): void {
  if (it.apron === undefined || view === "back") return;
  const pts: Pt[] = view === "front" ? [[-4.6, -24], [4.6, -24], [5.6, -6], [-5.6, -6]] : [[1.6, -24], [5, -24], [6.6, -6], [2.2, -6]];
  ink(ctx, `apron-${view}`, pts, it.apron, { w: 0.6 });
}

// ============================== 背物、腰掛、念珠、羽毛披肩 ==============================
/**
 * 背物（`back` 格：`gourd` 藥葫蘆、`puppet_box` 木偶箱）。正面、側面畫在身體後面（`onBody` ＝ false），
 * 背面畫在身體上（`onBody` ＝ true）；呼叫端在兩個時機各叫一次。
 */
export function drawBackItem(ctx: Ctx, it: GearItem | undefined, view: View, onBody: boolean): void {
  if (it === undefined) return;
  const BK = view === "back";
  if (onBody !== BK) return;
  const S = view === "side";
  if (it.kind === "gourd") {
    const c = it.color ?? "#c8843a";
    const [x, y] = BK ? [2, -24] : S ? [-7, -25] : [-10.6, -37];
    ink(ctx, `gourd-b-${view}`, ellPts(x, y, 4, 4.6, 14), c);
    ink(ctx, `gourd-t-${view}`, ellPts(x, y - 6.4, 2.6, 2.8, 12), c);
    stroke(ctx, `gourd-cord-${view}`, [[x - 2.4, y - 3.4], [x + 2.4, y - 3.4]], 0.9, RED);
    dot(ctx, x, y - 9.4, 0.9, 0.9, "#6a4224");
  } else if (it.kind === "puppet_box") {
    const c = it.color ?? MAT.wood;
    const [x0, y0, x1, y1] = BK ? [-8, -40, 8, -16] : S ? [-13, -45, -4, -17] : [-9.4, -50, 9.4, -30];
    ink(ctx, `pbox-${view}`, [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], c, { sharp: true });
    stroke(ctx, `pbox-band-${view}`, [[x0, (y0 + y1) / 2], [x1, (y0 + y1) / 2]], 0.6);
    if (!S) dot(ctx, (x0 + x1) / 2, (y0 + y1) / 2, 1.1, 1.1, MAT.gold);
  }
}

/** 腰掛（`waist` 格 `kind: "talismans"`）：黃符三張（側面兩張）；背面看不到。 */
export function drawWaist(ctx: Ctx, it: GearItem | undefined, view: View): void {
  if (it?.kind !== "talismans" || view === "back") return;
  const xs = view === "side" ? [1.6, 3.6] : [-5, -2.4, 4];
  xs.forEach((x, i) => {
    ink(ctx, `tal-${view}-${i}`, [[x - 1.1, -22.4], [x + 1.1, -22.4], [x + 1.3, -15.6], [x - 0.9, -15.4]], it.color ?? "#e8c84a", { shade: false, w: 0.45, sharp: true });
    stroke(ctx, `tal-m-${view}-${i}`, [[x - 0.3, -21], [x + 0.4, -19.4], [x - 0.3, -17.8]], 0.4, RED);
  });
}

/** 念珠（`neck` 格 `kind: "beads"`）；背面看不到。 */
export function drawBeads(ctx: Ctx, it: GearItem | undefined, view: View): void {
  if (it?.kind !== "beads" || view === "back") return;
  const c = it.color ?? "#6a3a1e";
  const pts: Pt[] = view === "side" ? [[-1, -33], [0.4, -30.6], [1.8, -28.4], [3, -26.6]] : [[-5, -33], [-4.4, -30.6], [-3, -28.6], [-1.4, -27.4], [0, -27], [1.4, -27.4], [3, -28.6], [4.4, -30.6], [5, -33]];
  for (const [x, y] of pts) {
    dot(ctx, x, y, 1.05, 1.05, INK);
    dot(ctx, x - 0.15, y - 0.15, 0.75, 0.75, c);
  }
}

/** 白羽披肩（cloak `form: "feather"`）：肩上一圈羽，畫在身體前面；背面不畫（同樣張）。 */
export function drawMantle(ctx: Ctx, it: GearItem | undefined, view: View): void {
  if (it?.form !== "feather" || view === "back") return;
  const c = it.color ?? "#f2f0ea";
  const pts: Pt[] = view === "side" ? [[-5, -34], [4, -34], [5.6, -28], [2, -29], [-1.6, -27.4], [-5.6, -28.6]] : [[-9, -34], [9, -34], [10.6, -28], [7, -29.4], [3.6, -27.6], [0, -29], [-3.6, -27.6], [-7, -29.4], [-10.6, -28]];
  ink(ctx, `mantle-${view}`, pts, c, { w: 0.7 });
  if (view === "front") for (const x of [-6, -2, 2, 6]) stroke(ctx, `mantle-f${x}`, [[x, -33], [x + 0.6, -29.6]], 0.4, "#b8b4aa");
}

// ============================== 頭：白紗面罩 ==============================
/** 白紗兜帽＋面罩（head `kind: "veil"`，霧行者）：兜帽 70% 半透明。回傳 false ＝ 不是面罩。 */
export function drawVeil(ctx: Ctx, it: GearItem, view: View): boolean {
  if (it.kind !== "veil") return false;
  const vc = it.color ?? "#f2f2f0";
  ctx.save();
  ctx.globalAlpha = 0.7;
  if (view === "back") ink(ctx, "veil-b", [[-11, -36], [-11.4, -48], [-5, -55], [5, -55], [11.4, -48], [11, -30], [0, -27], [-11, -30]], vc);
  else if (view === "front") ink(ctx, "veil", [[-11, -32], [-11.4, -48], [-5, -55], [5, -55], [11.4, -48], [11, -32], [7.6, -36.6], [8.4, -45], [0, -48], [-8.4, -45], [-7.6, -36.6]], vc);
  else ink(ctx, "veil-s", [[-12, -30], [-11.4, -46], [-5, -55], [4, -54.4], [9.6, -48.6], [9.4, -45], [4, -46.6], [0.6, -42], [-1.6, -36], [-7, -30]], vc);
  ctx.restore();
  if (view !== "back") ink(ctx, `mask-${view}`, view === "front" ? [[-8, -40], [8, -40], [6.6, -34.6], [-6.6, -34.6]] : [[2.4, -40], [9.6, -40], [8, -34.8], [2.4, -34.8]], "#d8dcdc", { w: 0.6 });
  return true;
}

// ============================== 手持：拂塵、符紙、傀儡線 ==============================

/** 修士的手持物（主手或副手）：拂塵 `whisk`、符紙 `talisman`、傀儡線 `puppet_cross`。回傳 false ＝ 不是這一層的 kind。 */
export function drawSectHeld(ctx: Ctx, it: GearItem, key: string, x: number, y: number, o: { mirror: boolean; side: boolean } & WeaponPoseOpt): boolean {
  if (it.kind !== "whisk" && it.kind !== "talisman" && it.kind !== "puppet_cross") return false;
  ctx.save();
  ctx.translate(x, y);
  if (o.mirror) ctx.scale(-1, 1);
  orientWeapon(ctx, it, o, restLean(ctx, it, o)); // 拂塵側面往前上斜；符紙、傀儡線不轉（inkWeaponFrame.ts）
  if (it.kind === "whisk") {
    ink(ctx, `${key}-handle`, [[-0.8, 4], [0.8, 4], [0.8, -10], [-0.8, -10]], MAT.wood, { shade: false, w: 0.6 });
    ink(ctx, `${key}-hair`, [[-1.4, -10], [1.4, -10], [3.6, -16], [2.4, -22], [0, -19], [-2, -23], [-3.4, -16]], "#f4f0e6", { w: 0.6 });
  } else if (it.kind === "talisman") {
    ink(ctx, `${key}-paper`, [[-2, -2], [2, -2], [2.4, -11], [-1.6, -11.4]], it.color ?? "#e8c84a", { shade: false, w: 0.5, sharp: true });
    stroke(ctx, `${key}-mark`, [[0, -10], [0.8, -8], [-0.6, -6.4], [0.6, -4]], 0.5, RED);
  } else {
    ink(ctx, `${key}-bar`, [[-4.4, -1], [4.4, -1], [4.4, 0.6], [-4.4, 0.6]], MAT.wood, { shade: false, w: 0.5, sharp: true });
    for (const sx of [-4, 0, 4]) stroke(ctx, `${key}-str${sx}`, [[sx, 0.6], [sx * 0.6, 11]], 0.3, "#e8e0d0");
  }
  ctx.restore();
  return true;
}

/** 劍穗（sword／dagger 的 `tassel`，劍陣弟子）：在護手下方垂一條；呼叫端已移到手的位置並轉好角度。 */
export function drawTassel(ctx: Ctx, it: GearItem, key: string): void {
  if (it.tassel === undefined) return;
  const pts: Pt[] = [[0, 0.6], [0.8, 4], [0.2, 7]];
  stroke(ctx, `${key}-tassel`, pts, 1.6, INK);
  stroke(ctx, `${key}-tassel2`, pts, 1, it.tassel);
}
