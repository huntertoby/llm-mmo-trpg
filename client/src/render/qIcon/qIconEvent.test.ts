// Phase QI-6：事件卡的 Q 版小圖示（第⑧批）與頭頂泡泡（第⑧b 批，`qIcon/event.ts`）與接線（`storyIconArt.ts`、`eventArtParts.ts`、`eventArt.ts`、`eventArtAwaken.ts`）。
// 需求 docs/art/Q版小圖示-事件卡移植需求.md；和樣張逐像素（指紋）比對在開發頁 `event-gallery.html?set=hash`（報告第 4 節），這裡鎖住結構與接線。
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { fakeCanvasFactory, fakeCtx, type FakeCanvasLog } from "../../test/fakeCanvas";
import { readFile, SRC_DIR } from "../../test/sourceScan";
import { EVENT_ART_W, eventArtScale, SCENES } from "../eventArt";
import * as parts from "../eventArtParts";
import { setQCanvasFactory } from "./core";
import * as QE from "./event";

const log: FakeCanvasLog = { calls: null };
beforeAll(() => setQCanvasFactory(fakeCanvasFactory(log)));
afterAll(() => {
  setQCanvasFactory(null);
  log.calls = null;
});
/** 在假畫布上畫一次，回傳外層 ctx 的呼叫紀錄。 */
function outer(fn: (c: CanvasRenderingContext2D) => void): string[] {
  const own: FakeCanvasLog = { calls: [] };
  fn(fakeCtx(own));
  return own.calls ?? [];
}
/** 全域 `log` 在 fn 期間的紀錄（`render` 另建的畫布都記在這裡）。 */
function inner(fn: () => void): string[] {
  log.calls = [];
  try {
    fn();
    return log.calls;
  } finally {
    log.calls = null;
  }
}
/** 一次 `render` 有沒有包外框：包外框時會多畫一張剪影並 `globalCompositeOperation=source-in` 染外框色。 */
const outlined = (calls: string[]): boolean => calls.includes("globalCompositeOperation=source-in");

describe("T1 清單（需求 1.1、2.1、2.2）", () => {
  it("28 個：選項 8、其他 5、六屬性 6、d20 1、小牌 8；順序照樣張；泡泡 9（用到 3 種 4 個、備用 6）", () => {
    const n = (g: QE.EventGroup) => QE.list(g).length;
    expect(QE.list().length).toBe(28);
    expect([n("sol"), n("misc"), n("attr"), n("d20"), n("badge")]).toEqual([8, 5, 6, 1, 8]);
    expect(QE.list().map((e) => e.id).slice(0, 8)).toEqual(["combat", "persuade", "sneak", "investigate", "force", "chance", "leave", "trade"]);
    const bu = QE.bubbleList();
    expect(bu.map((b) => b.id)).toEqual(["bang", "coin", "scroll", "sword", "ask", "rest", "portal", "notes", "warn"]);
    expect(bu.filter((b) => b.entry.use.length > 0).map((b) => b.id)).toEqual(["bang", "coin", "scroll"]);
    expect(bu.reduce((s, b) => s + b.entry.use.length, 0)).toBe(4);
  });
  it("同題材直接呼叫前幾批（src、需求 3 第 9 點）", () => {
    const src = (id: string) => QE.ICON[id]?.src;
    expect([src("sneak"), src("str"), src("con"), src("wis"), src("leave")]).toEqual(["b4:status.concealed", "b4:status.empowered", "b4:card.hp", "b4:effect.reveal", "style:hud.exit"]);
    expect([src("b_sword"), src("b_warn"), src("b_portal"), src("b_notes"), src("b_coin")]).toEqual(["b4:skeleton.strike", "b7:warn", "b4:card.source", "b7:bar_N", "b7:coin"]);
    expect([src("combat"), src("persuade"), src("investigate"), src("trade"), src("force")]).toEqual(["style:event.combat", "style:event.persuade", "style:event.investigate", "style:event.trade", "b1:fist"]);
    expect(QE.BUBBLE.coin?.base).toBe("b_coin");
    for (const id of ["sword", "rest", "portal", "notes", "warn"]) expect(QE.BUBBLE[id]?.base, id).toBe("b_" + id);
  });
  it("圓環色照現行（框不動）", () => {
    const ring = (id: string) => QE.ICON[id]?.ring;
    expect([ring("combat"), ring("persuade"), ring("sneak"), ring("investigate"), ring("force"), ring("chance"), ring("leave"), ring("trade")]).toEqual(["#d0503a", "#e8bb48", "#8a7ab8", "#4ab0d0", "#e07a4a", "#6aa84a", "#9a8e7c", "#e8bb48"]);
    expect([ring("clue"), ring("model_off"), ring("narrator"), ring("info"), ring("thread")]).toEqual(["#e8bb48", "#9a8e7c", "#a898ff", "#4ab0d0", "#e8bb48"]);
    expect([ring("str"), ring("dex"), ring("con"), ring("int"), ring("wis"), ring("wil")]).toEqual(["#e07a4a", "#6ac0a0", "#d04a5a", "#7a8aff", "#4ab0d0", "#e8bb48"]);
    expect(QE.ICON.d20?.ring).toBeUndefined();
  });
});

describe("T2 大小與外框（需求 3 第 1 點）", () => {
  it("圖樣本身＝圓環 × fill；>14 包外框 outlinePx(圓環)，≤14 不包；d20 撐滿、小牌 14 不包", () => {
    expect(QE.glyphPx("combat", 24)).toBeCloseTo(23.04);
    expect(QE.glyphPx("str", 18)).toBeCloseTo(15.48);
    expect(QE.glyphPx("clue", 16)).toBeCloseTo(13.76);
    expect(QE.glyphPx("d20", 16)).toBe(16);
    for (const [id, px, ow] of [["combat", 24, true], ["str", 20, true], ["str", 18, true], ["clue", 16, false], ["narrator", 16, false], ["info", 12, false], ["b_coin", 14, false], ["d20", 16, true], ["d20", 64, true]] as const)
      expect(outlined(inner(() => QE.glyph(id, px, 2))), `${id} ${px}`).toBe(ow);
  });
  it("d20 外框 16→1、24→1.2、64→1.6（res 2 的裝置像素 ×2）", () => {
    for (const [px, ow] of [[16, 1], [24, 1.2], [64, 1.6]] as const) {
      const calls = inner(() => QE.glyph("d20", px, 2));
      const S = Math.round(px * 2);
      expect(calls.some((c) => c === `drawImage(canvas(${S}x${S}),${(ow * 2).toFixed(3)},0.000)`), String(px)).toBe(true);
    }
  });
});

describe("T3 框照現行、圖樣裁在圓環內緣、貼整數裝置像素（需求 3 第 2 點、1.3 第 8 點）", () => {
  it("深底 #2a241e＋圓環色、線寬 max(1.2, 6%)、clip 半徑 size/2 − 線寬/2，圖樣照原尺寸貼", () => {
    for (const [id, px] of [["combat", 24], ["clue", 16], ["info", 12], ["str", 18]] as const) {
      const calls = outer((c) => QE.paint(c, id, px, 2));
      const lw = Math.max(1.2, px * 0.06);
      expect(calls).toContain(`fillStyle=${QE.CHIP_BG}`);
      expect(calls).toContain(`strokeStyle=${QE.ICON[id]!.ring}`);
      expect(calls).toContain(`lineWidth=${lw.toFixed(3)}`);
      expect(calls).toContain(`arc(${(px / 2).toFixed(3)},${(px / 2).toFixed(3)},${(px / 2 - lw / 2).toFixed(3)},0.000,${(Math.PI * 2).toFixed(3)})`);
      const img = calls.find((c) => c.startsWith("drawImage("))!;
      const [, , x, , w] = img.match(/drawImage\(canvas\((\d+)x\d+\),([\d.-]+),([\d.-]+),([\d.-]+)/)!.map(String) as [string, string, string, string, string];
      expect(Number(x) * 2, `${id} 左上角對齊裝置像素`).toBeCloseTo(Math.round(Number(x) * 2), 6);
      expect(Number(w) * 2, `${id} 照原尺寸`).toBe(Number(img.match(/canvas\((\d+)x/)![1]));
    }
  });
  it("d20 沒有框：不畫深底圓與圓環；64 寫點數（描 #fff8e8 再寫字），≤28 不寫", () => {
    const big = inner(() => outer((c) => QE.paint(c, "d20", 64, 2, { value: 17 })));
    expect(big.some((c) => c.startsWith("strokeText(17,"))).toBe(true);
    const own = outer((c) => QE.paint(c, "d20", 24, 2));
    expect(own).not.toContain(`fillStyle=${QE.CHIP_BG}`);
  });
});

describe("T4 d20 四色階（需求 3 第 3 點，規則 2 例外）", () => {
  it("底＝混黑 15%、上／左下＝本色、右／下＝混黑 34%、中央＝混白 66%（綠骰）", () => {
    const calls = inner(() => QE.glyph("d20", 24, 2, { color: "#5ad06a" }));
    const fills = [...new Set(calls.filter((c) => c.startsWith("fillStyle=")).map((c) => c.slice(10)))];
    expect(fills).toContain("#5ad06a");
    expect(fills.length).toBeGreaterThanOrEqual(4);
  });
});

describe("T5 小牌、泡泡（需求 3 第 4～6 點、第 8 點；第 4 節第 1、3、4 點）", () => {
  it("小牌：BADGE_Q 對到 8 個 b_*；SCENES 的圖示都在表裡；舊 ICON 只剩地物營火的 rest", () => {
    for (const s of Object.values(SCENES)) expect(QE.BADGE_Q[s.icon], s.zh).toBe("b_" + s.icon);
    expect(Object.keys(parts.ICON)).toEqual(["rest"]);
    expect("BADGE_ICON_INK" in parts).toBe(false);
  });
  it("小牌：中心 (21,20)、邊長 14、ctx 每單位 res 個裝置像素；不包外框", () => {
    const calls = outer((c) => QE.drawBadge(c, "coin", 21, 20, 2));
    expect(calls).toContain("drawImage(canvas(28x28),14.000,13.000,14.000,14.000)");
    expect(outlined(inner(() => QE.drawBadge(fakeCtx({ calls: null }), "coin", 21, 20, 2)))).toBe(false);
    expect(QE.drawBadge(fakeCtx({ calls: null }), "scroll", 21, 20, 2)).toBe(false);
  });
  it("插圖照卡寬縮放：ctxRes 讀變換、glyph 照那個解析度出圖、左上角落在整數裝置像素（卡寬 354 × DPR 1）", () => {
    const k = eventArtScale(354, 1);
    expect(k * EVENT_ART_W).toBe(354);
    const ctx = fakeCtx({ calls: null });
    (ctx as unknown as { getTransform: () => object }).getTransform = () => ({ a: k, b: 0, c: 0, d: k, e: 0, f: 0 });
    expect(QE.ctxRes(ctx)).toBeCloseTo(k);
    const own: FakeCanvasLog = { calls: [] }, c2 = fakeCtx(own);
    (c2 as unknown as { getTransform: () => object }).getTransform = () => ({ a: k, b: 0, c: 0, d: k, e: 0, f: 0 });
    parts.drawBadgeIcon(c2, "bang", 21, 20);
    const img = own.calls!.find((c) => c.startsWith("drawImage("))!;
    const m = img.match(/canvas\((\d+)x\d+\),([\d.-]+),([\d.-]+),([\d.-]+)/)!;
    expect(Number(m[1])).toBe(Math.round(14 * k));
    expect(Number(m[2]) * k).toBeCloseTo(Math.round(Number(m[2]) * k), 2);
    expect(Number(m[4]) * k).toBeCloseTo(Number(m[1]), 2);
    expect(eventArtScale(0, 1)).toBe(2);
  });
  it("泡泡：驚嘆號、問號近黑墨 #16121a、不包外框、沒有亮條；彩色的圖包 1px 外框；卷軸三道字線 #5a4a30", () => {
    const bang = inner(() => QE.bubbleGlyph("bang", 2));
    expect(bang).toContain("fillStyle=#16121a");
    expect(bang).not.toContain("fillStyle=#fff3a0");
    expect(outlined(bang)).toBe(false);
    expect(outlined(inner(() => QE.bubbleGlyph("ask", 2)))).toBe(false);
    for (const id of ["coin", "scroll", "sword", "rest", "portal", "notes", "warn"]) {
      const calls = inner(() => QE.bubbleGlyph(id, 2));
      expect(outlined(calls), id).toBe(true);
      expect(calls.filter((c) => c.startsWith("drawImage(canvas(28x28),")).some((c) => c.endsWith(",2.000,0.000)")), `${id} 外框 1px×res 2`).toBe(true);
    }
    const scroll = inner(() => QE.bubbleGlyph("scroll", 2));
    expect(scroll.filter((c) => c === "fillStyle=#5a4a30").length).toBe(6); // 三道 × 2（包外框時量剪影那一遍再畫一次，上手筆記第 49 點）
    expect(scroll).not.toContain("fillStyle=#d83a2a");
  });
  it("bubble()：框照現行（26×22、2px 外框、四種底色），圖樣中心 (x, y−15)、邊長 14", () => {
    const calls = outer((c) => parts.bubble(c, 100, 60, "coin", "talk"));
    expect(calls).toContain("fillStyle=#ffffff");
    expect(calls).toContain("lineWidth=2.000");
    expect(calls.at(-1)).toBe("drawImage(canvas(14x14),93.000,38.000,14.000,14.000)");
  });
  it("接線：事件插圖與覺醒插圖的小牌、bubble() 都走 Q 版；campfire 照舊 ICON.rest(…, 22)", () => {
    const art = readFile(SRC_DIR, "render/eventArt.ts"), awaken = readFile(SRC_DIR, "render/eventArtAwaken.ts"), p = readFile(SRC_DIR, "render/eventArtParts.ts");
    expect(art).toContain("drawBadgeIcon(ctx, s.icon, 21, 20)");
    expect(awaken).toContain('drawBadgeIcon(ctx, "portal", 21, 20)');
    expect(p).toContain("QE.drawBubble(ctx, icon, x, y - 15, QE.ctxRes(ctx))");
    expect(p).toContain("ICON.rest(ctx, cx, cy - 8, 22)");
  });
});

describe("T6 給資訊面板的圖樣本身（需求 2.3）", () => {
  it("bareGlyph：不畫深底圓與圓環，撐滿 px（res 2 的畫布 round(px×2)）", () => {
    for (const id of ["narrator", "clue", "combat", "thread", "info", "b_rest", "b_portal"]) {
      const calls = inner(() => QE.bareGlyph(id, 18, 2));
      expect(calls, id).not.toContain(`fillStyle=${QE.CHIP_BG}`);
      expect(calls.some((c) => c.startsWith("drawImage(canvas(36x36),0.000,0.000,18.000,18.000)")), id).toBe(true);
    }
  });
});

describe("T7 死碼（需求 4 第 6 點）", () => {
  it("storyIconArt.ts 不再有墨線畫法（SOLUTION_ART、MISC_ART、ATTR_ART、drawD20、drawChip、inkStyle）", () => {
    const src = readFile(SRC_DIR, "render/storyIconArt.ts");
    for (const name of ["const SOLUTION_ART", "const MISC_ART", "const ATTR_ART", "function drawD20", "function drawChip", "inkStyle\""]) expect(src, name).not.toContain(name);
  });
});
