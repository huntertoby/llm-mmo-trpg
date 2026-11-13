// Q 版手持物（QK-8；照 docs/art/sample/qDoll.js 11-07 新增的 QW whisk／talisman／puppet_strings 改寫）。
// 修士用：拂塵、符紙、傀儡線的十字木架。照持武器規則（6M-2）：握把在原點、作用端朝 −y；
// 四指（手的顏色 `skin`）橫過握柄，柄從拳頭上下穿出。傀儡線本身（垂下的細線）不在這裡畫：
// 由 qNpc 在外框之後畫（不描外框）。確定性：沒有亂數。
import type { Ctx } from "./artDraw";
import { fill, mix, type QItem } from "./qCore";

/** 手持物：`skin`＝握著它的手的顏色（qNpc.npcPrep 依手套或膚色補上）。 */
export type QHeldItem = QItem & { skin?: string };

/** 武器表的一項（同 qWeapons 的 QWeaponDef）。 */
export interface QHeldDef {
  len: number;
  hold: { side: number; front: number };
  draw: (c: Ctx, it: QItem | undefined) => void;
}

/** 修士手持物的 kind（qDoll 照持武器規則畫在手上）。 */
export const HELD_KINDS: readonly string[] = ["whisk", "talisman", "puppet_strings"];
/** 副手拿這些時畫成對應物件（不是書；樣張 HELD_OFF）。 */
export const HELD_OFF: readonly string[] = ["orb", "whisk", "talisman", "puppet_strings"];
export const isHeldOff = (it: QItem | null | undefined): boolean => !!it && HELD_OFF.includes(it.kind);

/** 四指：橫過握柄的一條（和手同色）＋一條指縫。 */
function heldFingers(c: Ctx, it: QItem | undefined): void {
  const k = (it as QHeldItem | undefined)?.skin ?? "#f1c9a5";
  fill(c, k, () => c.roundRect(-2.3, -1.1, 4.6, 2.2, 1));
  c.strokeStyle = mix(k, "#000000", 0.3);
  c.lineWidth = 0.35;
  c.beginPath();
  c.moveTo(-1.6, 0.05);
  c.lineTo(1.6, 0.05);
  c.stroke();
}

/** PB-1e：剪剩的短毛（武器座標：金箍下面三撮 1.7～2.4 長的亂毛＋灰剪口；照 `docs/art/sample/bossParts.js` 的 whiskStub 原樣搬）。 */
export function whiskStub(c: Ctx): void {
  c.fillStyle = "#f2f0ea";
  for (const [x0, a, l] of [
    [-0.6, 2.5, 2.4],
    [-0.1, 2.1, 1.7],
    [0.4, 2.8, 2.0],
  ] as const) {
    c.save();
    c.translate(x0, -6.6);
    c.rotate(a);
    c.beginPath();
    c.moveTo(-0.45, 0);
    c.lineTo(0.45, 0);
    c.lineTo(0.15, l);
    c.lineTo(-0.2, l * 0.8);
    c.closePath();
    c.fill();
    c.restore();
  }
  c.fillStyle = "#c8c4b8";
  c.beginPath();
  c.moveTo(-0.9, -6.2);
  c.lineTo(0.2, -6.1);
  c.lineTo(-0.5, -5.2);
  c.closePath();
  c.fill();
}

export const QW_HELD: Readonly<Record<string, QHeldDef>> = {
  whisk: {
    len: 7,
    hold: { side: 0.3, front: 0 },
    draw: (c, it) => {
      fill(c, "#8a5a2a", () => c.roundRect(-0.65, -6.6, 1.3, 9.4, 0.6));
      fill(c, "#e8bb48", () => c.roundRect(-0.9, -7.2, 1.8, 1.2, 0.5));
      if (it?.cut === true) {
        // PB-1e：拂塵破了（樣張 bossParts.js whiskStub）：白毛剪掉，金箍下剩三撮短毛＋剪口（一起描外框）
        whiskStub(c);
        heldFingers(c, it);
        return;
      }
      fill(c, it?.color ?? "#f2f0ea", () => {
        c.moveTo(-0.9, -7);
        c.quadraticCurveTo(-5.6, -7.6, -6.4, 1.6);
        c.quadraticCurveTo(-4.6, 3.2, -3.2, 0.6);
        c.quadraticCurveTo(-2.4, -4.4, 0.9, -6.6);
        c.closePath();
      });
      heldFingers(c, it);
    },
  },
  talisman: {
    len: 9,
    hold: { side: 0.25, front: 0.15 },
    draw: (c, it) => {
      fill(c, it?.color ?? "#f2d860", () => c.roundRect(-1.5, -9.4, 3, 8.4, 0.3));
      c.strokeStyle = "#c0392b";
      c.lineWidth = 0.45;
      c.lineCap = "round";
      c.beginPath();
      c.moveTo(0, -8.6);
      c.lineTo(-0.7, -7.2);
      c.lineTo(0.7, -5.8);
      c.lineTo(-0.5, -4.4);
      c.lineTo(0.3, -3.2);
      c.stroke();
      heldFingers(c, it);
    },
  },
  puppet_strings: {
    len: 4,
    hold: { side: 0, front: 0 },
    draw: (c, it) => {
      fill(c, "#8a6a48", () => c.roundRect(-4.4, -0.6, 8.8, 1.3, 0.5));
      fill(c, "#8a6a48", () => c.roundRect(-0.65, -3.6, 1.3, 7.6, 0.5));
      heldFingers(c, it);
    },
  },
};
