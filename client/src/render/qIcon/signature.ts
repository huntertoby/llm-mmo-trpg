// 招牌效果的類型小圖示（E6-b2；美術移植需求 `docs/art/E6-招牌-移植需求.md` 第 1 節第 2 項，樣張 `docs/art/sample/e6Signature.js` 第 2、3 節）。
// - 新動作、新反應、行為改寫、改寫規則：直接用第④批部件圖（`effect.grant_skill`、`effect.extra_reaction`、`skeleton.modifier`、`effect.rule_change`）。
// - 地形規則：新圖「地格」，照樣張 `terrainArt` 逐行搬（草地格＋側面土層＋一對霜白腳印；≤14 走 tiny）。樣張是 install() 時塞進部件表，
//   這裡不改過審的部件表 `parts.ts`，另外用同一個 `def`／`glyph` 的算法畫（±10 單位放大 1.8 倍畫在 48 格、≤14px 不包外框）。
// - 尺寸：類型牌 18、角色面板 16、戰利品小牌 14（圖樣本身＝格子 ×0.75，全部走 tiny）。標灰的灰階、半透明由 CSS 做（`.off .sig-ico`）。
// 確定性：沒有亂數。
import { el, outlinePx, poly, render, type Ctx, type QOpts } from "./core";
import { BOX, glyph } from "./parts";

export type SignatureKind = "action" | "reaction" | "terrain" | "behavior" | "rule";

/** 五種招牌用哪個部件圖（`terrain` 是這裡的新圖）。 */
export const SIGNATURE_ART: Readonly<Record<SignatureKind, { cat: string; id: string }>> = {
  action: { cat: "effect", id: "grant_skill" },
  reaction: { cat: "effect", id: "extra_reaction" },
  terrain: { cat: "effect", id: "e6_terrain" },
  behavior: { cat: "skeleton", id: "modifier" },
  rule: { cat: "effect", id: "rule_change" },
};

export const isSignatureKind = (k: string | null | undefined): k is SignatureKind => k != null && k in SIGNATURE_ART;

const GRASS = "#7cbf5a", GRASS_HI = "#b4e48c", DIRT = "#a06a36", DIRT_D = "#6a4420", FROST = "#eef8ff";

function foot(c: Ctx, o: QOpts, x: number, y: number, rot: number): void {
  c.save();
  c.translate(x, y);
  c.rotate(rot);
  if (o.tiny) el(c, FROST, 0, 0, 1.7, 2.7);
  else {
    el(c, FROST, 0, -0.9, 1.6, 2.5);
    el(c, FROST, 0, 2.6, 1.15, 1.2);
  }
  c.restore();
}

/** 地形規則（±10 單位）：一塊草地格（3/4 俯視的菱形格，側面露出土層）＋一對霜白腳印。 */
export function terrainArt(c: Ctx, o: QOpts): void {
  c.save();
  c.translate(0, -1.2);
  poly(c, DIRT, [[-10.4, 0], [0, 5.4], [0, 10.4], [-10.4, 5]], 0.4); /* 左側面：土 */
  poly(c, DIRT_D, [[0, 5.4], [10.4, 0], [10.4, 5], [0, 10.4]], 0.4); /* 右側面：暗一階 */
  poly(c, GRASS, [[-10.4, 0], [0, -5.4], [10.4, 0], [0, 5.4]], 0.4); /* 上面：草 */
  if (!o.tiny) poly(c, GRASS_HI, [[-10.4, 0], [0, -5.4], [1.8, -4.4], [-7.6, 0.4]]); /* 左上緣亮面 */
  foot(c, o, -3.4, 0.9, -1.05);
  foot(c, o, 3.4, -1.1, -1.05); /* 一前一後，沿菱形斜邊的方向走 */
  c.restore();
}

/** 地形規則的圖樣 canvas（同 `parts.glyph` 的算法：cpx＝圖樣本身的 CSS px）。 */
function terrainGlyph(cpx: number, res: number): HTMLCanvasElement | null {
  const d = (c: Ctx, o: QOpts): void => {
    c.save();
    c.translate(24, 24);
    c.scale(1.8, 1.8);
    terrainArt(c, { ...o, small: cpx <= 24, tiny: cpx <= 14 });
    c.restore();
  };
  return render({ d }, cpx * BOX, res, { ow: cpx <= 14 ? 0 : outlinePx(cpx) });
}

/** 一個招牌小圖示：`box`＝格子邊長（CSS px：18、16、14），圖樣本身＝box×0.75；`res`＝內部解析度（DOM 用 2，真 1 倍傳 1）。
 *  回傳的 canvas 邊長＝round(box×res)；沒有畫布時 null。 */
export function signatureGlyph(kind: SignatureKind, box: number, res = 2): HTMLCanvasElement | null {
  const cpx = box * 0.75;
  if (kind === "terrain") return terrainGlyph(cpx, res);
  const art = SIGNATURE_ART[kind];
  return glyph(art.cat, art.id, cpx, res);
}
