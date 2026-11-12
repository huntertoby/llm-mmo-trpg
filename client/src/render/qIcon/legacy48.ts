// Q 版小圖示：風格樣張 docs/art/sample/qIcons.js 裡、第 3、4 批（`skills.ts`、`parts.ts`）用到但 QI-1a 沒搬的片段（Phase QI-2b，逐行搬）。
// 都畫在 48 格（中心 24,24）：
// - `drop`（樣張 H.drop）：水滴外形。
// - `totemPole`（樣張 W.totemPole＝SKILL_V1.skill_plant_totem.d）：第 3 批「圖騰」召喚物道具的柱子。
// - `ART.status`：第 4 批狀態圓片包一層 from48() 呼叫的四款（倒地、冰凍、加速、恐懼）。
// - `ART.hud`：第 4 批卡片小圖、靴子用到的四款（AP、法力、耐力、移動）。
// 材質色（木）用 `core.ts` 的 `M`（照 material.ts，QI-1 第 0.0 節第 3 點）；其餘照樣張字面色。
import { ci, el, f, halo, HI, ln, M, OUT, poly, rr, starPts, TAU, type Ctx, type QOpts } from "./core";

/** 水滴外形：中心 (x,y)、高 20s、寬 14s，尖端朝上（樣張 H.drop）。 */
export function drop(c: Ctx, col: string, x: number, y: number, s: number): void { c.save(); c.translate(x, y); c.scale(s, s); c.beginPath(); c.moveTo(0, -10); c.bezierCurveTo(4, -4, 7, 0, 7, 4); c.bezierCurveTo(7, 8, 3.5, 10, 0, 10); c.bezierCurveTo(-3.5, 10, -7, 8, -7, 4); c.bezierCurveTo(-7, 0, -4, -4, 0, -10); c.closePath(); c.fillStyle = col; c.fill(); c.restore(); }

/** 一根插在土堆上的木雕圖騰柱：頂上一對紅翅、兩張臉（樣張 SKILL_V1.skill_plant_totem.d）。 */
export function totemPole(c: Ctx, o: QOpts): void {
  el(c, "#6a4a2e", 24, 41.5, 14.5, 3.6); poly(c, "#c0392b", [[17, 9], [5, 6], [8, 11.5], [4.5, 13], [9.5, 15], [17, 15.5]], 0.5); poly(c, "#c0392b", [[31, 9], [43, 6], [40, 11.5], [43.5, 13], [38.5, 15], [31, 15.5]], 0.5);
  rr(c, M.wood, 16.5, 5, 15, 36.5, 3.4); f(c, "#b98048", () => c.roundRect(16.5, 5, 4.4, 36.5, [3.4, 0, 0, 3.4])); f(c, M.woodD, () => c.rect(16.5, 21.4, 15, 1.7));
  for (const y of [11, 28]) { rr(c, "#fff6c8", 19, y, 3.6, 3.6, 0.8); rr(c, "#fff6c8", 25.4, y, 3.6, 3.6, 0.8); if (!o.small) { f(c, OUT, () => c.rect(20.3, y + 1, 1.5, 1.8)); f(c, OUT, () => c.rect(26.7, y + 1, 1.5, 1.8)); } }
  rr(c, M.woodD, 20.6, 16.6, 6.8, 2.4, 1); poly(c, "#e8bb48", [[20, 34.5], [22, 37.5], [24, 34.5], [26, 37.5], [28, 34.5], [28, 36], [26, 39], [24, 36], [22, 39], [20, 36]]);
}

export interface Art48 { zh: string; d: (c: Ctx, o: QOpts) => void }

const STATUS = {
  prone: { zh: "倒地",
    // 第 2 版換題材：一個臉朝下趴在地上的人形剪影（單色米白，不畫臉、不分衣服色——第 1 版的藍身體加閉眼臉讀成「睡著」）：圓頭在左、身體平貼地面線、兩條腿在右邊微微分開；背上一顆黃色撞擊星（被打倒）。
    // ≤14px 只留人形（大圓頭＋粗身體）與地面線，放大撐滿框；星省掉。
    d: (c: Ctx, o: QOpts) => { const k = "#f2e6c8";
      if (o.tiny) { rr(c, "#a89878", 1.5, 39.5, 45, 5.5, 2); rr(c, k, 17, 19.5, 29.5, 15.5, 6.5); ci(c, k, 12.5, 25, 11.5); f(c, "#ffffff", () => c.ellipse(9, 20.6, 4, 2.8, -0.5, 0, TAU)); return; }
      // 第 3 版：頭放大並抬高（頭頂高過背）、軀幹縮短、兩條腿分開成 V（一條平貼地面、一條屈膝翹起），1 倍下不再是一條長條加星
      halo(c, o, (x) => { poly(x, "#ffd23f", starPts(24, 11, 10.5, 4.8, 7, -1.2), 0.5); poly(x, "#ffffff", starPts(24, 11, 4.8, 2.3, 7, -1.2)); });
      rr(c, "#8a7a6a", 2.5, 40.8, 43, 4, 2);
      halo(c, o, (x) => { ln(x, k, 6, [[30, 36.2], [43, 36.6]]); ln(x, k, 6, [[30, 33], [39.5, 25.5]]); rr(x, k, 17, 28.4, 16.5, 11.2, 5); ci(x, k, 11.5, 29.6, 9.6); f(x, "#ffffff", () => x.ellipse(8.6, 26, 3.2, 2.2, -0.5, 0, TAU)); f(x, "rgba(120,90,50,0.3)", () => x.rect(19, 37, 13, 2.6)); }); } },
  frozen: { zh: "冰凍",
    // 一叢冰晶（三根冰柱），不是雪花線條；和「緩速」的時鐘分得開
    d: (c: Ctx, o: QOpts) => { poly(c, "#8fe3ff", [[12, 17], [17.5, 25], [16.5, 42], [7, 42], [6, 26]], 0.8); poly(c, "#8fe3ff", [[36.5, 20], [42, 28], [41, 42], [32, 42], [31, 28]], 0.8); poly(c, "#b8efff", [[24, 4.5], [31.5, 17], [29.5, 42], [18.5, 42], [16.5, 17]], 0.8);
      poly(c, "#ffffff", [[24, 7], [24, 40.5], [19.6, 40.5], [18, 17.4]]); if (!o.tiny) { poly(c, "#3fa6d8", [[29.2, 20], [30.4, 17.6], [28.6, 41], [26.4, 41]]); poly(c, "#e8fbff", [[11.6, 20], [11.6, 41], [8.4, 41], [7.6, 26.4]]); poly(c, "#e8fbff", [[36, 23], [36, 41], [33.2, 41], [32.6, 28.4]]); } } },
  hasted: { zh: "加速",
    // 兩個並排往右的胖箭頭（上半亮、下半暗）；≤14px 兩個箭頭收窄、中間留空隙（約 2.5px），不黏在一起
    d: (c: Ctx, o: QOpts) => { if (o.tiny) { for (const dx of [0.5, 23.5]) { poly(c, "#7dffb0", [[dx, 6], [dx + 11, 6], [dx + 23, 24], [dx + 11, 42], [dx, 42], [dx + 12, 24]]); poly(c, "#e2fff0", [[dx, 6], [dx + 11, 6], [dx + 23, 24], [dx + 12, 24]]); } return; } /* 第 3 版：箭頭加粗（8→11 單位），11px 時不再比 20px 暗一階；兩個箭頭之間仍留約 1.8px 的空隙 */
      for (const dx of [3, 20]) { poly(c, "#7dffb0", [[dx, 9], [dx + 10, 9], [dx + 22, 24], [dx + 10, 39], [dx, 39], [dx + 12, 24]], 0.9); poly(c, "#d6ffe6", [[dx + 1, 10], [dx + 9.6, 10], [dx + 20.6, 24], [dx + 12, 24]]); } } },
  feared: { zh: "恐懼",
    // 一隻淡紫白色的小幽靈：圓頭、波浪下襬、兩個深色眼洞、張開的嘴
    d: (c: Ctx, o: QOpts) => { f(c, "#ece4ff", () => { c.moveTo(6, 43); c.lineTo(6, 23); c.bezierCurveTo(6, 0, 42, 0, 42, 23); c.lineTo(42, 43); c.lineTo(36, 37.5); c.lineTo(30, 43); c.lineTo(24, 37.5); c.lineTo(18, 43); c.lineTo(12, 37.5); c.closePath(); });
      if (!o.tiny) f(c, "rgba(120,90,200,0.3)", () => { c.moveTo(33, 7.5); c.bezierCurveTo(40, 12, 42, 18, 42, 23); c.lineTo(42, 43); c.lineTo(36.4, 37.8); c.lineTo(36.4, 22); c.bezierCurveTo(36.4, 16, 35.4, 11, 33, 7.5); c.closePath(); });
      el(c, OUT, 17.5, 21, o.tiny ? 4 : 3.3, o.tiny ? 5.6 : 4.8); el(c, OUT, 30.5, 21, o.tiny ? 4 : 3.3, o.tiny ? 5.6 : 4.8); if (!o.tiny) el(c, OUT, 24, 31, 3.2, 2.6); } },
} satisfies Record<string, Art48>;

const HUD = {
  ap: { zh: "AP（行動點）", d: (c: Ctx, o: QOpts) => { poly(c, "#ffd23a", [[27, 3.5], [9.5, 27], [21, 27], [16, 44.5], [38.5, 19.5], [27, 19.5], [33.5, 3.5]], 1); if (!o.tiny) poly(c, "#fff3a0", [[27.4, 5], [12.6, 25.6], [17, 25.6], [31, 5]]); } },
  mana: { zh: "法力", d: (c: Ctx, _o: QOpts) => { drop(c, "#4a8ae0", 24, 24.5, 2.1); c.save(); c.beginPath(); c.rect(0, 0, 48, 48); c.clip(); f(c, "rgba(20,40,110,0.38)", () => { c.moveTo(24, 45.5); c.bezierCurveTo(34, 45.5, 40, 38, 38.4, 29.5); c.bezierCurveTo(37, 37, 31, 41, 24, 41.5); c.closePath(); }); c.restore(); el(c, "#cfe4ff", 18, 28.5, 2.6, 5.6, 0.45); } },
  stamina: { zh: "耐力", d: (c: Ctx, o: QOpts) => { const P: [number, number][] = [[4.5, 26], [13.5, 26], [19, 11.5], [27.5, 37.5], [32.5, 24], [43.5, 24]]; ln(c, "#e8bb48", 6.4, P); if (!o.tiny) ln(c, "#fff0b0", 1.6, P.map(([x, y]) => [x - 0.6, y - 1.2])); } },
  move: { zh: "移動", d: (c: Ctx, o: QOpts) => { rr(c, "#a07040", 12.5, 5.5, 15.5, 30, 4); f(c, "#a07040", () => { c.moveTo(12.5, 24); c.lineTo(27, 24); c.quadraticCurveTo(41.5, 25.5, 42.5, 35.5); c.lineTo(42.5, 39); c.lineTo(12.5, 39); c.closePath(); });
      rr(c, "#5e3b1f", 11, 38, 33, 5.4, 2.2); rr(c, "#e0c088", 11, 4.5, 18.5, 7.6, 3.2); if (!o.tiny) { f(c, HI, () => c.rect(15, 13.5, 2.2, 20)); f(c, "rgba(0,0,0,0.2)", () => { c.moveTo(28, 26); c.quadraticCurveTo(39.5, 27.5, 41, 36); c.lineTo(28, 36); c.closePath(); }); } } },
} satisfies Record<string, Art48>;

/** 樣張 `QIcons.ART` 裡第 4 批用到的兩類（只搬用到的款）。 */
export const ART: { status: Readonly<Record<string, Art48 | undefined>> & typeof STATUS; hud: Readonly<Record<string, Art48 | undefined>> & typeof HUD } = { status: STATUS, hud: HUD };
