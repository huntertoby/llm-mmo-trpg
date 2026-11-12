// PR-2d（#147 靶場測試模式收尾）行為一致測試 D 組：每項都以 `view.practice`（或 `DrawModel.practice`）分支，
// 實戰（不帶旗標）的輸出和改前逐字相同（改前的字直接寫在表裡）；測試模式才換。
// D1 高亮格貼水池內縮、不壓石條；D2 工坊選單的木樁小圖重用 `drawTrainingDummy`；D3 靶場「測試模式」徽章的說明卡；
// D4 開場橫幅；D5 指揮召喚物面板「敵人」→「木樁」。
import { createElement, type ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { Pos } from "../api/types";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { drawSoftCells, MOVE_SOFT, HIT_SOFT, RANGE_SOFT, type Pen, type TileGeo } from "../render/pathArt";
import { PRACTICE_SCENES, poolGeometry, poolInsets, slabWidth, type Rect } from "../render/practiceRange";
import { DUMMY_ICON_VIEW, DUMMY_SCALE, drawTrainingDummyIcon } from "../render/trainingDummy";
import { BattleBanner } from "../ui/BattleBanner";
import { CommandBox } from "../ui/SummonPanel";
import { TEST_MODE_BADGE_HINT_ZH, TestModeBadge } from "../ui/TestModeBadge";
import { PracticeBar } from "../ui/TurnBar";
import { DUMMY_ICON_PX, WorkshopPanel, type WorkshopData } from "../world/WorkshopPanel";
import { TILE_SIZE } from "./geometry";
import { objectiveLine } from "./objective";
import { PRACTICE_BADGE_HINT_ZH, PRACTICE_BANNER_ZH } from "./skillTray";
import { smallView, unit } from "./testFixtures";
import { unitNames } from "./units";

const T = TILE_SIZE;
const O = slabWidth(T);
const noop = () => undefined;
/** React 在相鄰文字節點之間插的 `<!-- -->`（畫面上看不到）。比「畫面上的字」時拿掉。 */
const visible = (html: string) => html.replaceAll("<!-- -->", "");

// training_range：12×10，水池 (6,8)、(7,8)、(6,9)（L 形，南緣貼地圖下緣）
const SCENE = PRACTICE_SCENES.training_range!;
const W = 12;
const H = 10;

/** 紀錄 Pen 呼叫的假畫筆。 */
function recorder(): { pen: Pen; log: unknown[][] } {
  const log: unknown[][] = [];
  const rec =
    (name: string) =>
    (...args: unknown[]) => {
      log.push([name, ...args]);
      return undefined;
    };
  const pen: Pen = { moveTo: rec("moveTo"), lineTo: rec("lineTo"), roundRect: rec("roundRect"), circle: rec("circle"), closePath: rec("closePath"), fill: rec("fill"), stroke: rec("stroke") };
  return { pen, log };
}
const flat: TileGeo = { origin: (p) => ({ x: p.x * T, y: p.y * T }), center: (p) => ({ x: p.x * T + T / 2, y: p.y * T + T / 2 }) };

const overlap = (a: Rect, b: Rect) => Math.min(a.x1, b.x1) - Math.max(a.x0, b.x0) > 1e-9 && Math.min(a.y1, b.y1) - Math.max(a.y0, b.y0) > 1e-9;

describe("D1 高亮格貼水池往內縮一個石條寬（樣張 boardCanvas「貼著水池的藍格往內縮 9」）", () => {
  const insetOf = poolInsets(SCENE, W, H, T)!;

  it("實戰、技能工坊（沒有 DrawModel.practice）與沒有水池的地圖：不給內縮", () => {
    expect(poolInsets(undefined, W, H, T)).toBeUndefined();
    expect(poolInsets({ rails: [], pool: [] }, W, H, T)).toBeUndefined();
  });

  it("training_range：池外貼水池那一邊縮、池格貼地圖下緣那一邊縮；不貼的格子回 null", () => {
    expect(insetOf({ x: 5, y: 8 })).toEqual({ n: 0, s: 0, w: 0, e: O });
    expect(insetOf({ x: 8, y: 8 })).toEqual({ n: 0, s: 0, w: O, e: 0 });
    expect(insetOf({ x: 6, y: 7 })).toEqual({ n: 0, s: O, w: 0, e: 0 });
    expect(insetOf({ x: 7, y: 9 })).toEqual({ n: O, s: 0, w: O, e: 0 }); // L 形內角那一格：兩邊都縮
    expect(insetOf({ x: 6, y: 9 })).toEqual({ n: 0, s: O, w: 0, e: 0 }); // 池格，南緣貼地圖下緣（石條在水面裡）
    expect(insetOf({ x: 6, y: 8 })).toBeNull(); // 池格中間
    expect(insetOf({ x: 5, y: 7 })).toBeNull(); // 斜對角：照樣張讓石條的角蓋一小角
    expect(insetOf({ x: 2, y: 2 })).toBeNull();
  });

  it("縮過的可走格不壓到「這一格上」的石條（斜對角外伸的角除外）", () => {
    const geom = poolGeometry(SCENE.pool, () => true, W, H, T);
    const { pen, log } = recorder();
    const cells: Pos[] = [];
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (insetOf({ x, y }) !== null) cells.push({ x, y });
    drawSoftCells(pen, cells, flat, MOVE_SOFT, insetOf);
    const rects = log.filter((c) => c[0] === "roundRect").map((c) => {
      const [, x, y, w, h] = c as [string, number, number, number, number];
      return { x0: x, y0: y, x1: x + w, y1: y + h };
    });
    expect(rects).toHaveLength(cells.length);
    rects.forEach((r, i) => {
      const cell = cells[i]!;
      const box = { x0: cell.x * T, y0: cell.y * T, x1: cell.x * T + T, y1: cell.y * T + T };
      for (const s of geom.slabs) {
        // 只看石條落在這一格裡、且不是外角外伸的那一段
        const part = { x0: Math.max(s.rect.x0, box.x0), y0: Math.max(s.rect.y0, box.y0), x1: Math.min(s.rect.x1, box.x1), y1: Math.min(s.rect.y1, box.y1) };
        if (part.x1 <= part.x0 || part.y1 <= part.y0) continue;
        const ownSide = (s.side === "n" || s.side === "s" ? s.tile.x === cell.x : s.tile.y === cell.y) || (s.tile.x === cell.x && s.tile.y === cell.y);
        if (!ownSide) continue;
        expect(overlap(r, part), `(${cell.x},${cell.y}) 壓到 ${s.side} 石條`).toBe(false);
      }
    });
  });

  it("沒給內縮（實戰）與內縮全回 null：每一筆畫筆呼叫和改前相同（改前的數字直接寫在這裡）", () => {
    const cells: Pos[] = [
      { x: 5, y: 8 },
      { x: 5, y: 7 },
    ];
    for (const style of [MOVE_SOFT, RANGE_SOFT, HIT_SOFT]) {
      const a = recorder();
      drawSoftCells(a.pen, cells, flat, style);
      const b = recorder();
      drawSoftCells(b.pen, cells, flat, style, () => null);
      expect(b.log).toEqual(a.log);
    }
    const a = recorder();
    drawSoftCells(a.pen, cells, flat, MOVE_SOFT);
    // 改前 drawSoftCells：每格 roundRect(o+3, o+3, T-6, T-6, 8)；外緣線在 o+2／o+T-2
    expect(a.log.filter((c) => c[0] === "roundRect")).toEqual([
      ["roundRect", 5 * T + 3, 8 * T + 3, T - 6, T - 6, 8],
      ["roundRect", 5 * T + 3, 7 * T + 3, T - 6, T - 6, 8],
    ]);
    const pts = a.log.filter((c) => c[0] === "moveTo" || c[0] === "lineTo").map((c) => c.slice(1) as [number, number]);
    expect(pts.length).toBeGreaterThan(0);
    for (const [x, y] of pts) {
      expect([5 * T + 2, 5 * T + T - 2]).toContain(x);
      expect([7 * T + 2, 7 * T + T - 2, 8 * T + 2, 8 * T + T - 2]).toContain(y);
    }
  });

  it("測試模式：貼水池那一格的方塊與外緣線都讓出石條", () => {
    const { pen, log } = recorder();
    drawSoftCells(pen, [{ x: 5, y: 8 }], flat, MOVE_SOFT, insetOf);
    expect(log.find((c) => c[0] === "roundRect")).toEqual(["roundRect", 5 * T + 3, 8 * T + 3, T - 6 - O, T - 6, 8]);
    const lines = log.filter((c) => c[0] === "moveTo" || c[0] === "lineTo").map((c) => c[1] as number);
    expect(Math.max(...lines)).toBeCloseTo(6 * T - 2 - O); // 東邊外緣線往內移到石條外
  });

  it("接線：高亮層的可走、範圍、預覽與紅框都經過 poolInsets（只看 model.practice）", () => {
    const src = readFile(SRC_DIR, "render/battle/highlightLayer.ts");
    expect(src).toContain("drawSoftCells(pen.at(h.moves[0] ?? { x: 0, y: 0 }), h.moves, geo, MOVE_SOFT, insetOf);");
    expect(src).toContain("drawSoftCells(pen.at(range[0] ?? { x: 0, y: 0 }), range, geo, RANGE_SOFT, insetOf);");
    expect(src).toContain("drawSoftCells(pen.at(h.preview[0] ?? { x: 0, y: 0 }), h.preview, geo, HIT_SOFT, insetOf);");
    expect(src).toContain("poolInsets(m.practice, m.width, m.height, T)");
    expect(src).toContain("roundRect(o.x + 2 + i.w, o.y + 2 + i.n, T - 4 - i.w - i.e, T - 4 - i.n - i.s, 8)");
  });
});

describe("D2 工坊師傅選單：木樁小圖重用 drawTrainingDummy，改造技能照舊是 WeaponIcon 的錘子", () => {
  const w: WorkshopData = {
    seen_id: "ws",
    title_zh: "樞島工坊・靶場與改造",
    line: { speaker_zh: "工坊師傅", text_zh: "木樁隨你打，打壞了我再釘。試試你現在的本事。" },
    practice_zh: "靶場試玩",
    practice_note_zh: "用你現在的技能與裝備打木樁，不耗任何資源",
    practice_available: true,
    practice_new: false,
    rework_zh: "改造技能",
    rework_note_zh: "之後開放",
    footer_zh: "靶場裡技能沒有冷卻，每次出手後自動過一輪，資源立刻補滿。",
    capital_zh: "樞島",
  } as unknown as WorkshopData;

  it("選單列是木樁畫布（原尺寸 ×2、CSS 不縮放），沒有內嵌 SVG；錘子不變", () => {
    const html = renderToStaticMarkup(createElement(WorkshopPanel, { workshop: w, busy: false, seen: false, onPractice: noop }));
    expect(html).toContain('data-testid="workshop-dummy-icon"');
    expect(html).toContain(`width="${DUMMY_ICON_PX * 2}" height="${DUMMY_ICON_PX * 2}" style="width:${DUMMY_ICON_PX}px;height:${DUMMY_ICON_PX}px"`);
    expect(html).not.toContain("<svg");
    expect(html).toMatch(/workshop-menu-icon rework"><canvas class="weapon-icon" width="60" height="60" style="width:30px;height:30px"/);
    const src = readFile(SRC_DIR, "world/WorkshopPanel.tsx");
    expect(src).toContain("drawTrainingDummyIcon(ctx, DUMMY_ICON_PX, DUMMY_ICON_RES)");
    expect(src).toContain('<WeaponIcon weaponId="hammer" weaponClass="melee" size={30} />');
  });

  it("drawTrainingDummyIcon：取景照原本 SVG 的 viewBox（-31 -55 62 62），腳底在畫布下緣往上 7/62", () => {
    const calls: unknown[][] = [];
    const ctx = new Proxy(
      {},
      {
        get: (_t, k) => (k === "canvas" ? { width: 64, height: 64 } : (...a: unknown[]) => calls.push([k, ...a])),
        set: () => true,
      },
    ) as unknown as CanvasRenderingContext2D;
    drawTrainingDummyIcon(ctx, 32, 2);
    const set = calls.find((c) => c[0] === "setTransform") as number[] | undefined;
    expect(set).toBeDefined();
    const k = 64 / (DUMMY_ICON_VIEW.size * DUMMY_SCALE);
    expect(set!.slice(1)).toEqual([k, 0, 0, k, 32, 64 * (55 / 62)].map((v, i) => (i === 4 || i === 5 ? expect.closeTo(v as number, 9) : v)));
    // 畫的是戰場上同一個木樁（drawTrainingDummy 會先 scale 0.86）
    expect(calls.some((c) => c[0] === "scale" && c[1] === DUMMY_SCALE)).toBe(true);
  });
});

describe("D3 靶場「測試模式」徽章的說明卡換成定稿句；其他地方的徽章原字不動", () => {
  it("定稿原字", () => {
    expect(PRACTICE_BADGE_HINT_ZH).toBe("靶場測試模式：技能沒有冷卻、資源每次出手後補滿、木樁必中也不會倒。不算勝負，不給經驗與掉落。");
    expect(TEST_MODE_BADGE_HINT_ZH).toBe("測試模式：戰後回滿，不計入任何統計"); // 改前原字
  });

  it("不帶參數：說明卡是改前原字；靶場提示條帶定稿句", () => {
    const plain = TestModeBadge({}) as ReactElement<{ text: string }>;
    expect(plain.props.text).toBe("測試模式：戰後回滿，不計入任何統計");
    const bar = PracticeBar() as ReactElement<{ children: ReactElement<{ hint?: string }>[] }>;
    const badge = bar.props.children[0]!;
    expect(badge.type).toBe(TestModeBadge);
    expect(badge.props.hint).toBe(PRACTICE_BADGE_HINT_ZH);
    expect((TestModeBadge({ hint: PRACTICE_BADGE_HINT_ZH }) as ReactElement<{ text: string }>).props.text).toBe(PRACTICE_BADGE_HINT_ZH);
    // 外觀（徽章本身的 HTML）兩邊相同
    expect(renderToStaticMarkup(createElement(TestModeBadge, { hint: PRACTICE_BADGE_HINT_ZH }))).toBe(renderToStaticMarkup(createElement(TestModeBadge)));
  });

  it("一輪測試模式的三處（進度、結束摘要、存檔列表）不傳 hint", () => {
    for (const f of ["screens/RunEnded.tsx", "screens/RunScreen.tsx", "screens/StartScreen.tsx"]) {
      const src = readFile(SRC_DIR, f);
      expect(src).toContain("<TestModeBadge />");
      expect(src).not.toContain("<TestModeBadge hint");
    }
  });
});

describe("D4 開場橫幅：測試模式拿掉「戰鬥開始＋勝利條件」，改成定稿的一行", () => {
  const objective = smallView().objective;

  it("實戰：和改前（BattleScreen 內嵌的橫幅）逐字相同", () => {
    const before = (notes: string[]) =>
      `<div class="battle-banner">戰鬥開始<div class="battle-banner-goal">${objectiveLine(objective)}</div>${notes.map((n) => `<div class="battle-banner-note">${n}</div>`).join("")}</div>`;
    expect(visible(renderToStaticMarkup(createElement(BattleBanner, { practice: false, objective })))).toBe(before([]));
    expect(visible(renderToStaticMarkup(createElement(BattleBanner, { practice: false, objective, notes: ["甲", "乙"] })))).toBe(before(["甲", "乙"]));
  });

  it("測試模式：只有定稿那一行（開場訊息照舊接在下面）", () => {
    expect(PRACTICE_BANNER_ZH).toBe("靶場：打木樁試招，按右上的離開鈕結束");
    const html = renderToStaticMarkup(createElement(BattleBanner, { practice: true, objective, notes: ["靶場試玩：長劍"] }));
    expect(html).toContain(PRACTICE_BANNER_ZH);
    expect(html).not.toContain("戰鬥開始");
    expect(html).not.toContain(objectiveLine(objective));
    expect(html).toContain("靶場試玩：長劍");
  });

  it("接線：BattleScreen 以 shown.practice 分支", () => {
    expect(readFile(SRC_DIR, "screens/BattleScreen.tsx")).toContain("<BattleBanner practice={practice} objective={shown.objective} notes={openingNotes} />");
  });
});

describe("D5 指揮召喚物面板：測試模式「敵人」→「木樁」，實戰不變", () => {
  const hero = unit("unit_0001", "ally", 1, 1);
  const summon = unit("unit_0009", "ally", 2, 1, { owner_id: "unit_0001", name_zh: "骷髏戰士" });
  const names = unitNames(smallView({ units: [hero, summon] }));
  const empty = { summonId: summon.id, dest: { x: 2, y: 1 }, options: { summon_id: summon.id, ap_cost: 1, options: [{ dest: { x: 2, y: 1 }, path: [{ x: 2, y: 1 }], targets: [] }] } };
  const box = (practice: boolean) =>
    visible(
      renderToStaticMarkup(
        createElement(CommandBox, { session: empty, summon, hero, names, enabled: true, practice, onPickDest: noop, onCancelCommand: noop, onCommand: noop, onPreviewAction: noop }),
      ),
    );

  it("實戰：改前原字", () => {
    const live = box(false);
    expect(live).toContain("點地圖上的藍格，或從清單選終點；再選要打的敵人（也可以只移動）。花 1 AP。");
    expect(live).toContain("原地沒有打得到的敵人，請改選終點。");
    expect(live).not.toContain("木樁");
  });

  it("測試模式：寫「木樁」，其餘相同", () => {
    const test = box(true);
    expect(test).toContain("點地圖上的藍格，或從清單選終點；再選要打的木樁（也可以只移動）。花 1 AP。");
    expect(test).toContain("原地沒有打得到的木樁，請改選終點。");
    expect(test).not.toContain("敵人");
    expect(test.replaceAll("木樁", "敵人")).toBe(box(false));
  });

  it("接線：面板說明、模式說明、集火清單的字都經過 practiceWording(…, view.practice)", () => {
    const src = readFile(SRC_DIR, "ui/SummonPanel.tsx");
    expect(src).toContain("tip={practiceWording(TIP_TEXT, view.practice)}");
    expect(src).toContain("tip={practiceWording(b.hint, view.practice)}");
    expect(src).toContain('practiceWording("選一個敵人集火（0 AP）：", view.practice)');
    expect(src).toContain("practice={view.practice}");
  });
});
