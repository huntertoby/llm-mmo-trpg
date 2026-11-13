// 玩家兩種大盾的 Q 版圖示（RG-5，#163 護陣；docs/art/RG樣張.md 10.1、10.3、10.4）：雲紋碑盾 sect_great、熔殼塔盾 molten_shell。
// 照樣張 docs/art/sample/rgPlayerShield.js 第 3 節的 sectIcon／shellIcon 原樣移植（48 格、直立；外框由 render 包、≤24px 省小零件）。
// 配色和紙娃娃同一套規則：碑盾 sectPalOf（盾邊照材質本色亮度，審查 P-1）、熔殼 shellPalOf（殼板混玄武岩 0.35、殼縫紅光固定）；
// 殼縫用紙娃娃同一張偏移表（qMoltenShell.crack，審查 P-2）。混色一律用 qCore.mix（和樣張同一種四捨五入）。
import { mix, TAU } from "../qCore";
import { crack, line, shellPath, SHELL_FIX, type ShellPal } from "../qMoltenShell";
import type { SectPal } from "../qSectShield";
import type { Ctx, QOpts } from "./core";

const MOON = "#dfe4e2";
const QING = "#5f8f8a";
const RED = "#c0392b";
const HI = "rgba(255,255,255,0.45)";
const HI2 = "rgba(255,255,255,0.8)";
const SH = "rgba(0,0,0,0.22)";
const dk = (c: string, t = 0.25): string => mix(c, "#000000", t);
function fill(c: Ctx, col: string, path: () => void): void {
  c.fillStyle = col;
  c.beginPath();
  path();
  c.fill();
}

/** 雲紋碑盾圖示：碑形（拱頂、直邊、下緣小圓角）、盾邊 2.4（盾寬 29 的 8%）、盾心大雲紋章、兩道盾骨、四顆銅釘（>24px）。 */
export function sectIcon(c: Ctx, o: QOpts, pal: SectPal): void {
  const L = 9.5;
  const R = 38.5;
  const T = 15;
  const B = 44;
  const a = 9;
  const body = (i: number): void => {
    const l = L + i;
    const r = R - i;
    const t = T + i * 0.7;
    const b = B - i;
    const aa = a - i * 0.35;
    const cx = 24;
    const rx = (r - l) / 2;
    c.moveTo(l, b - 2.4);
    c.lineTo(l, t);
    c.ellipse(cx, t, rx, aa, 0, Math.PI, 0);
    c.lineTo(r, b - 2.4);
    c.quadraticCurveTo(r, b, r - 2.4, b);
    c.lineTo(l + 2.4, b);
    c.quadraticCurveTo(l, b, l, b - 2.4);
    c.closePath();
  };
  fill(c, pal.rim, () => body(0));
  fill(c, pal.face, () => body(2.4));
  c.save();
  c.beginPath();
  body(2.4);
  c.clip();
  fill(c, mix(pal.face, "#ffffff", 0.18), () => c.rect(L, 0, 5.6, 48));
  fill(c, SH, () => c.rect(R - 7.6, 0, 8, 48));
  if (!o.small) for (const y of [18.4, 37.2]) fill(c, dk(pal.rim, 0.1), () => c.rect(L, y, R - L, 1.8));
  c.restore();
  // 雲紋章：月白圓章、青色三峰（中峰最高）、山腰月白雲、峰頂朱紅點；≤24px 省雲與紅點
  const r = o.small ? 8 : 7.2;
  const cy = 27.6;
  c.save();
  c.translate(24, cy);
  if (pal.ring !== null) fill(c, pal.ring, () => c.arc(0, 0, r + 1.2, 0, TAU));
  fill(c, MOON, () => c.arc(0, 0, r, 0, TAU));
  fill(c, dk(QING, 0.15), () => {
    c.moveTo(-r * 0.8, r * 0.46);
    c.lineTo(-r * 0.38, -r * 0.16);
    c.lineTo(-r * 0.1, r * 0.1);
    c.lineTo(r * 0.22, -r * 0.66);
    c.lineTo(r * 0.8, r * 0.46);
    c.closePath();
  });
  if (!o.small) {
    line(c, MOON, r * 0.18, [
      [-r * 0.62, r * 0.2],
      [-r * 0.12, r * 0.32],
      [r * 0.38, r * 0.12],
    ]);
    fill(c, RED, () => c.arc(r * 0.22, -r * 0.66, r * 0.17, 0, TAU));
    fill(c, HI2, () => c.ellipse(-r * 0.42, -r * 0.5, r * 0.22, r * 0.12, -0.6, 0, TAU));
  }
  c.restore();
  fill(c, HI, () => c.roundRect(L + 4, T - 2.4, 1.6, 12, 0.8));
  if (!o.small) {
    const nails: ReadonlyArray<readonly [number, number]> = [
      [L + 5.2, T + 0.8],
      [R - 5.2, T + 0.8],
      [L + 5.2, B - 4.8],
      [R - 5.2, B - 4.8],
    ];
    for (const [x, y] of nails) {
      fill(c, dk(pal.rivet, 0.4), () => c.arc(x + 0.3, y + 0.4, 1.6, 0, TAU));
      fill(c, pal.rivet, () => c.arc(x, y, 1.35, 0, TAU));
    }
  }
}

/** 熔殼塔盾圖示：正面的蛋形殼（模型座標橫 ×1.75、縱 ×1.42，中心 (24, 31.2)）、殼緣暗一圈、右緣內面、三道殼縫（≤24px 加粗）。 */
export function shellIcon(c: Ctx, o: QOpts, pal: ShellPal): void {
  const SX = 1.75;
  const SY = 1.42;
  const S = [SX, SY] as const;
  const OX = 24;
  const OY = 31.2;
  fill(c, pal.edge, () => shellPath(c, S, OX, OY));
  fill(c, pal.plate, () => shellPath(c, S, OX, OY, 1.25));
  c.save();
  c.beginPath();
  shellPath(c, S, OX, OY, 1.25);
  c.clip();
  fill(c, pal.lit, () => c.rect(0, 0, 48, OY - 11 * SY));
  fill(c, pal.low, () => c.rect(0, OY + 3.2 * SY, 48, 20));
  fill(c, pal.inner, () => {
    c.moveTo(OX + 5.4 * SX, OY - 16 * SY);
    c.quadraticCurveTo(OX + 9.4 * SX, OY - 4 * SY, OX + 6.2 * SX, OY + 10 * SY);
    c.lineTo(48, 48);
    c.lineTo(48, 0);
    c.closePath();
  });
  fill(c, HI, () => c.ellipse(OX - 4.4 * SX, OY - 13 * SY, 1.9, 4.4, 0.5, 0, TAU));
  c.restore();
  const w = o.small ? 3 : 2.6;
  const h = o.small ? 2.4 : 2.6;
  const lit = mix(pal.plate, "#ffffff", 0.32);
  for (let v = 0; v < 3; v++)
    crack(
      v,
      h,
      (x) => OX + x * SX,
      (y) => OY + y * SY,
    ).forEach((pts) => {
      line(
        c,
        lit,
        w * 0.6,
        pts.map(([x, yy]) => [x, yy + w * 0.75] as const),
      );
      line(c, SHELL_FIX.glow, w, pts);
      line(c, SHELL_FIX.core, w * 0.4, pts);
    });
}
