// 異形精英的「武器」：三道骨白彎弧爪痕（RG-4；照 docs/art/sample/rgUnits.js 的 beastClaw 第 3 版逐行搬，docs/art/RG樣張.md 9.8 第 4 條）。
// 只給精英單挑插圖（`render/duelArt.ts`）用：不進武器圖示表（`weapons.ts` 的 BUILD／Q_WEAPON_KINDS）、不進任何 list()／指紋清單。
// 48 格畫法：外框 #16121a（寬 2.4）、骨 #e9e3cf、凹側暗面 #a8a08a、凸側亮線白 75%。三道平行、入爪端粗、尾端尖，中間那道最長；
// 方向和 Q 版劍圖示同一條斜線（左下－右上），插圖裡鏡像後和主角的劍交叉。確定性：沒有亂數。
import { OUT, type Ctx } from "./core";

/** 插圖裡代表「獸爪」的武器 kind（只在 duelArt 裡認得）。 */
export const BEAST_CLAW = "beast_claw";

/** 三道爪痕的軸 x、上下端、最寬、彎度（第 3 版：間距 9；最靠劍尖那道兩端收短，不出 48 格；中心 −8＝劍身中段）。 */
const OX = [-17, -8, 1] as const;
const LN: ReadonlyArray<readonly [number, number]> = [
  [-14.5, 15],
  [-21, 21],
  [-17, 17],
];
const WD = [2.7, 3.1, 2.7] as const;
const BD = [3.4, 4, 3.4] as const;
/** 凹側暗面往 −x 的位移。 */
const SHADE_DX = [2, 2.4, 2] as const;

function fillPath(g: Ctx, c: string, path: () => void): void {
  g.fillStyle = c;
  g.beginPath();
  path();
  g.fill();
}

/** 一道爪痕的路徑：軸 x＝ox，從 (ox, top) 到 (ox, bot)，往 +x 彎 b；sc 是寬度倍率。 */
function slash(g: Ctx, ox: number, top: number, bot: number, w: number, b: number): (sc?: number) => void {
  const L = bot - top;
  const y1 = top + L * 0.3;
  const y2 = top + L * 0.68;
  return (sc = 1) => {
    const ww = w * sc;
    g.moveTo(ox + 0.2, top);
    g.bezierCurveTo(ox + b + ww * 0.9, y1, ox + b + ww * 0.55, y2, ox, bot);
    g.bezierCurveTo(ox + b - ww * 0.35, y2, ox + b - ww * 0.55, y1, ox - 0.2, top);
    g.closePath();
  };
}

/** 在 (0,0)～(px,px) 畫爪痕（ctx 目前的座標系；無框）。 */
export function paintBeastClaw(g: Ctx, px: number): void {
  g.save();
  g.scale(px / 48, px / 48);
  g.translate(24, 24);
  g.rotate(Math.PI / 4); // 軸線＝劍圖示的斜線；−y＝右上
  const S3 = OX.map((ox, i) => slash(g, ox, LN[i]![0], LN[i]![1], WD[i]!, BD[i]!));
  g.lineJoin = "round";
  g.strokeStyle = OUT;
  g.lineWidth = 2.4;
  for (const t of S3) {
    g.beginPath();
    t();
    g.stroke();
  }
  for (const t of S3) fillPath(g, "#e9e3cf", () => t());
  // 凹側暗面：同一道往 −x 縮一半寬
  S3.forEach((t, i) => {
    g.save();
    g.beginPath();
    t();
    g.clip();
    g.translate(-SHADE_DX[i]!, 0);
    fillPath(g, "#a8a08a", () => t(0.75));
    g.restore();
  });
  // 凸側亮線
  OX.forEach((ox, i) => {
    const [top, bot] = LN[i]!;
    const b = BD[i]!;
    const L = bot - top;
    g.save();
    g.strokeStyle = "rgba(255,255,255,0.75)";
    g.lineWidth = 0.9;
    g.lineCap = "round";
    g.beginPath();
    g.moveTo(ox + 1.3, top + L * 0.14);
    g.quadraticCurveTo(ox + b + 1.4, top + L * 0.42, ox + 1.2, top + L * 0.66);
    g.stroke();
    g.restore();
  });
  g.restore();
}
