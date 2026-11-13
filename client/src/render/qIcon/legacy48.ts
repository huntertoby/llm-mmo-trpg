// Q 版小圖示：風格樣張 docs/art/sample/qIcons.js 裡、第 3、4 批（`skills.ts`、`parts.ts`）用到但 QI-1a 沒搬的片段（Phase QI-2b，逐行搬）。
// 都畫在 48 格（中心 24,24）：
// - `drop`（樣張 H.drop）：水滴外形。
// - `totemPole`（樣張 W.totemPole＝SKILL_V1.skill_plant_totem.d）：第 3 批「圖騰」召喚物道具的柱子。
// - `ART.status`：第 4 批狀態圓片包一層 from48() 呼叫的四款（倒地、冰凍、加速、恐懼）。
// - `ART.hud`：第 4 批卡片小圖、靴子用到的四款（AP、法力、耐力、移動）；QI-5 加第⑦批 HUD 的離開 `exit`、背包 `bag`。
// - `ART.event`（QI-6）：第⑧批事件卡用到的四款（戰鬥、說服、調查、交易）＋它們的 `eventSword`、`crossSword`、`heart`（樣張 qIcons.js 原樣；
//   `heart` 和 `parts.ts` 那份相同，但 `parts.ts` 匯入本檔、這裡不能反過來匯入，照樣張在本檔另存一份）。劍的材質色照 `core.ts` 的 `M`（＝material.ts）。
// - `ART.item`（QI-7）：第⑥批物品沿用的四款（小回復藥、回魔藥、火瓶、精料）＋它們的 `GLASS`、`liquid`（樣張 qIcons.js 284～305 行原樣；
//   `items.ts` 的中回復藥也用這裡的 `GLASS`、`liquid`，同一份）。都是字面色，不經過 `M`。
// 材質色（木）用 `core.ts` 的 `M`（照 material.ts，QI-1 第 0.0 節第 3 點）；其餘照樣張字面色。
import { ci, el, f, flame, glow, halo, HI, HI2, ln, M, OUT, poly, rr, sparkle, starPts, TAU, type Ctx, type QOpts } from "./core";

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
  /* QI-5（第⑦批 HUD 用到）：離開、背包，照樣張 qIcons.js 的 ART.hud.exit／bag 逐行搬（木色照樣張字面色 #a06a36，不換 M.wood） */
  exit: { zh: "離開", d: (c: Ctx, o: QOpts) => { rr(c, "#5a3e28", 5.5, 4.5, 23, 39.5, 2.4); poly(c, "#a06a36", [[8, 7], [20, 11], [20, 43.6], [8, 41.4]], 0.6); ci(c, "#e8bb48", 16.6, 26.5, 2);
      halo(c, o, (x) => { poly(x, "#f2e6c8", [[23.5, 20], [33.5, 20], [33.5, 13.5], [45, 24], [33.5, 34.5], [33.5, 28], [23.5, 28]], 0.8); f(x, HI2, () => x.rect(24.5, 20.4, 8.6, 1.6)); }); } },
  bag: { zh: "背包",
    // 第 2 版重畫：正面的冒險者後背包——頂上橫綁一捲米色鋪蓋（兩道束帶）、圓肩的袋身、淺色翻蓋、正中一條束帶加金扣、兩側鼓出的側袋、底下一個前袋。
    // 第 1 版頂上的提把弧線讓整體讀成掛鎖，拿掉；≤24px 省掉扣眼與鋪蓋的暗面，零件照留。
    d: (c: Ctx, o: QOpts) => { rr(c, "#7e5229", 2.5, 23.5, 9, 15.5, 3.4); rr(c, "#7e5229", 36.5, 23.5, 9, 15.5, 3.4);
      f(c, "#a06a36", () => c.roundRect(7.5, 10.5, 33, 34, [9, 9, 6, 6]));
      f(c, "#c08a4e", () => c.roundRect(7.5, 10.5, 33, 17, [9, 9, 9, 9])); f(c, HI, () => c.rect(12.5, 14, 9, 1.8));
      rr(c, "#7e5229", 13.5, 33, 21, 8.6, 2.6);
      rr(c, "#5e3b1f", 21.6, 10.5, 4.8, 20, 1); rr(c, "#e8bb48", 20, 24.6, 8, 7.6, 1.8); if (!o.small) f(c, "#9c7420", () => c.rect(22.8, 26.8, 2.4, 3.2));
      halo(c, o, (x) => { rr(x, "#e6d8b0", 8, 3, 32, 10.5, 5.2); if (!o.small) f(x, "rgba(120,90,40,0.28)", () => x.roundRect(8, 8.6, 32, 4.9, [0, 0, 5.2, 5.2])); f(x, "#5e3b1f", () => x.rect(14, 3, 3.4, 10.5)); f(x, "#5e3b1f", () => x.rect(30.6, 3, 3.4, 10.5)); }); } },
} satisfies Record<string, Art48>;

/** 心形（樣張 qIcons.js 的 heart）：中心 (x,y)、尖端在 +7s。 */
function heart(c: Ctx, col: string, x: number, y: number, s: number): void { c.save(); c.translate(x, y); c.scale(s, s); c.beginPath(); c.moveTo(0, 7); c.bezierCurveTo(-11, -1, -7, -10, 0, -4.5); c.bezierCurveTo(7, -10, 11, -1, 0, 7); c.closePath(); c.fillStyle = col; c.fill(); c.restore(); }
/** 事件卡「戰鬥」用的劍：和武器圖示同一把單手劍的零件（直刃長劍尖、橫護手、短柄、圓柄頭），但圖在深底圓裡、最小 18px：
 *  刃拉長（兩把在刃的下段交叉，X 形才明顯）、亮面佔左半；護手與柄頭用金色（#d8b04a）、握柄用皮色（#8a5a32）——深底上的深褐握柄與暗銅護手會整個消失（規則 6）。 */
function eventSword(c: Ctx, _o: QOpts): void {
  poly(c, M.steel, [[-3.9, 6.5], [-3.9, -15.5], [0, -23], [3.9, -15.5], [3.9, 6.5]]);
  f(c, "#f4f8fc", () => { c.moveTo(-3.9, 6.5); c.lineTo(-3.9, -15.5); c.lineTo(0, -23); c.lineTo(0, 6.5); c.closePath(); });
  rr(c, M.gold, -8.6, 5.6, 17.2, 4.6, 2.2);
  rr(c, M.leather, -2.3, 10, 4.6, 7.6, 1.2);
  ci(c, M.gold, 0, 19.2, 3.1);
}
const crossSword = (c: Ctx, o: QOpts, s: number): void => { c.save(); c.translate(24, 24); c.scale(s, 1); c.rotate(Math.PI / 4); c.scale(1.05, 1.05); eventSword(c, o); c.restore(); };
/** 事件卡選項的四款（樣張 qIcons.js 的 EVENT；`meta`（圓環色、fill）在 `event.ts` 的 ICON 表，這裡只留畫法）。 */
const EVENT = {
  combat: { zh: "戰鬥", /* 兩把劍撐滿圓（圖樣佔圓的 96%，其他三個是 80%）；前面那把包一圈亮邊（#fff6d8），和後面那把的交界才分得開 */
    d: (c: Ctx, o: QOpts) => { crossSword(c, o, -1); halo(c, o, (x) => crossSword(x, o, 1), "#fff6d8", 0.55); } },
  persuade: { zh: "說服", d: (c: Ctx, o: QOpts) => { poly(c, "#f2e6c8", [[15, 30], [11.5, 42.5], [25, 31.5]], 0.8); rr(c, "#f2e6c8", 5, 7, 38, 25.5, 9.5); heart(c, "#e05a6a", 24, 19.8, 1.22); if (!o.small) el(c, "#ffb0b8", 19.6, 16.4, 1.6, 2.2, -0.5); } },
  investigate: { zh: "調查", d: (c: Ctx, o: QOpts) => { c.save(); c.translate(31, 31); c.rotate(Math.PI / 4); rr(c, "#6a4028", -2, 0, 17.5, 6.4, 2.6); c.restore(); ci(c, "#d8a040", 19.5, 19.5, 14); ci(c, "#bfe4f2", 19.5, 19.5, 9.8); el(c, "#ffffff", 15.6, 15.4, 2.6, 4.4, 0.7); if (!o.small) f(c, "rgba(40,110,150,0.3)", () => { c.arc(19.5, 19.5, 9.8, 0.1, Math.PI * 0.75); c.closePath(); }); } },
  trade: { zh: "交易", d: (c: Ctx, o: QOpts) => { poly(c, "#b08a5a", [[15.5, 9], [19, 12], [24, 9.5], [29, 12], [32.5, 9], [28.5, 18.5], [39.5, 30.5], [36.5, 42], [11.5, 42], [8.5, 30.5], [19.5, 18.5]], 1.4); rr(c, "#6a4028", 17, 16.4, 14, 3.6, 1.6); if (!o.small) f(c, "rgba(255,255,255,0.25)", () => c.ellipse(15.5, 32, 2.6, 5.6, 0.3, 0, TAU));
      halo(c, o, (x) => { ci(x, "#ffd23a", 35, 35.5, 8); ci(x, "#fff0a0", 35, 35.5, 5.4); f(x, "#b8862a", () => x.rect(34, 32.5, 2, 6)); }); } },
} satisfies Record<string, Art48>;

/** 玻璃瓶身色（樣張 qIcons.js 的 GLASS）。 */
export const GLASS = "#dcebf0";
/** 瓶裡的液體：裁在 clipPath 裡，top 以下填 col、液面一道 surf（樣張 qIcons.js 的 liquid）。 */
export const liquid = (c: Ctx, clipPath: (x: Ctx) => void, col: string, top: number, surf: string): void => { c.save(); c.beginPath(); clipPath(c); c.clip(); f(c, col, () => c.rect(0, top, 48, 48)); f(c, surf, () => c.rect(0, top, 48, 2)); c.restore(); };
/** 圖樣：d 主體、pre 外框底下（光暈）。 */
export interface Art48Pre extends Art48 { pre?: (c: Ctx, o: QOpts) => void }
/** 第⑥批物品沿用的四款（樣張 qIcons.js 的 ITEM；`meta`（類別、品質）在 `items.ts` 的 ICON 表，這裡只留畫法）。 */
const ITEM = {
  item_hp_potion_small: { zh: "小回復藥",
    // 圓肚瓶、軟木塞、紅藥水，瓶身一個白色十字（回復）
    d: (c: Ctx, _o: QOpts) => { rr(c, GLASS, 20, 10, 8, 10, 1.5); rr(c, "#a06a36", 18.8, 4.6, 10.4, 6.6, 2.2); ci(c, GLASS, 24, 30, 13.4);
      liquid(c, (x) => x.arc(24, 30, 11.2, 0, TAU), "#e04a3a", 23.5, "#ff9a8a");
      rr(c, "#ffffff", 22.2, 26.6, 3.6, 10.4, 1); rr(c, "#ffffff", 18.8, 30, 10.4, 3.6, 1); el(c, HI2, 16.6, 24.5, 1.7, 3.6, 0.5); } },
  item_mana_potion: { zh: "回魔藥",
    // 菱形尖肚瓶、水晶瓶塞、藍藥水，瓶身一顆白色四芒星（法力）；瓶形和回復藥不同，不只換顏色
    d: (c: Ctx, _o: QOpts) => { rr(c, GLASS, 21, 9.5, 6, 8, 1.2); poly(c, "#c8bcff", [[24, 2.6], [28, 6.8], [24, 11], [20, 6.8]], 0.6);
      const body: [number, number][] = [[24, 14.5], [35.5, 27], [30.5, 42], [17.5, 42], [12.5, 27]]; poly(c, GLASS, body, 1.6);
      liquid(c, (x) => { x.moveTo(24, 16.5); x.lineTo(33.8, 27.2); x.lineTo(29.4, 40.4); x.lineTo(18.6, 40.4); x.lineTo(14.2, 27.2); x.closePath(); }, "#4a8ae0", 24.5, "#9ac4ff");
      sparkle(c, "#ffffff", 24, 32.5, 5.4); el(c, HI2, 18.6, 25.5, 1.3, 3, 0.7); } },
  item_fire_flask: { zh: "火瓶",
    // 方肩的投擲瓶、瓶口塞一條布、布頭點著火，瓶裡是橘色的油與火苗（丟出去會燒）；不靠右下角的小元素記號
    pre: (c: Ctx, _o: QOpts) => glow(c, 29, 6, 10, "#ffb23a", 0.6),
    d: (c: Ctx, o: QOpts) => { rr(c, GLASS, 20.2, 12, 7.6, 9, 1.4); poly(c, "#e8dcc0", [[21.4, 13.5], [26.4, 13.5], [29.6, 7.4], [25.6, 7.2]], 0.8); flame(c, "#ff6a1a", 28.6, 4.6, 0.4);
      rr(c, GLASS, 12.5, 19.5, 23, 23.5, 5.5);
      liquid(c, (x) => x.roundRect(14.3, 21.3, 19.4, 19.9, 4), "#ff7a2a", 25, "#ffc070");
      flame(c, "#ffd23f", 24, 33, 0.62); if (!o.small) flame(c, "#ffffff", 24.2, 35.4, 0.28); el(c, HI2, 16.6, 28, 1.2, 3.2, 0); } },
  item_fine_material: { zh: "精料",
    // 一塊藍灰礦石、三個切面（亮、中、暗），嵌兩顆亮晶
    d: (c: Ctx, o: QOpts) => { c.translate(24, 26.5); c.scale(1.22, 1.22); c.translate(-24.5, -26.5); const P: [number, number][] = [[9.5, 35], [13.5, 21], [23, 13.5], [35.5, 17.5], [39.5, 31], [31, 39.5], [16, 39.5]]; poly(c, "#8aa8c8", P, 1.4);
      poly(c, "#b4cbe2", [[13.5, 21], [23, 13.5], [35.5, 17.5], [25, 25.5]], 0.6); poly(c, "#6282a4", [[25, 25.5], [35.5, 17.5], [39.5, 31], [31, 39.5]], 0.6);
      poly(c, "#e8f8ff", [[17.5, 28], [20.3, 31.4], [17.5, 34.8], [14.7, 31.4]]); if (!o.small) poly(c, "#e8f8ff", [[29, 18.4], [31, 20.6], [29, 22.8], [27, 20.6]]); } },
} satisfies Record<string, Art48Pre>;

/** 樣張 `QIcons.ART` 裡第 4 批起用到的四類（只搬用到的款）。 */
export const ART: { status: Readonly<Record<string, Art48 | undefined>> & typeof STATUS; hud: Readonly<Record<string, Art48 | undefined>> & typeof HUD; event: Readonly<Record<string, Art48 | undefined>> & typeof EVENT; item: Readonly<Record<string, Art48Pre | undefined>> & typeof ITEM } = { status: STATUS, hud: HUD, event: EVENT, item: ITEM };
