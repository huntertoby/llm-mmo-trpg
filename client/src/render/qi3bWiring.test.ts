// QI-3b 接線（規格 docs/phases/PhaseQI-3計畫.md 第 7 節 T-B1～T-B3、T-B7，0.0 第 7 點 statusTile）。
// 資料一律用名詞表快照 battle/fixtures/glossary.json（118 個狀態），不手寫清單。
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import glossary from "../battle/fixtures/glossary.json";
import { readSources } from "../test/sourceScan";
import { fakeCanvasFactory, fakeCtx, type FakeCanvasLog } from "../test/fakeCanvas";
import { ICON_RES, setQCanvasFactory } from "./qIcon/core";
import * as QP from "./qIcon/parts";
import * as QT from "./qIcon/status";
import { clearSkillIconCache, STATUS_CARD_PX, statusIconTile, statusTile, tileCanvas, tileKey } from "./skillIcon";
import { statusColor } from "./skillParts";
import { clearStatusIconCache, glyphColor, paintStatusIcon, statusIconCanvas, statusIconKey } from "./statusIcon";

const srcOf = (path: string): string => readSources().find(([p]) => p.replace(/\\/g, "/").endsWith(path))?.[1] ?? "";
const IDS = (glossary as unknown as { statuses: { id: string }[] }).statuses.map((s) => s.id);

let log: FakeCanvasLog = { calls: [] };
/** 重設紀錄、掛假畫布（Q 版畫布工廠與 document 都接同一份）。 */
function reset(): FakeCanvasLog {
  log = { calls: [] };
  const make = fakeCanvasFactory(log);
  setQCanvasFactory(make);
  (globalThis as { document?: unknown }).document = { createElement: () => make(0, 0) };
  return log;
}
function rec(draw: () => HTMLCanvasElement | null | void): string {
  reset();
  const cv = draw();
  return `${cv ? `${cv.width}x${cv.height}` : "-"}|${(log.calls ?? []).join(";")}`;
}

let savedDoc: unknown;
beforeEach(() => {
  savedDoc = (globalThis as { document?: unknown }).document;
  clearSkillIconCache();
  clearStatusIconCache();
});
afterEach(() => {
  (globalThis as { document?: unknown }).document = savedDoc;
  setQCanvasFactory(null);
  clearSkillIconCache();
  clearStatusIconCache();
});

describe("T-B1 paintStatusIcon 換成 Q 版", () => {
  it("名詞表全部 × 狀態卡／頭頂／52 × res 1、2：呼叫紀錄＝直接呼叫 qIcon/status.ts 的 paint", () => {
    const cases: [number, number, number, number][] = [
      [50, 84, 0.2, 2], // 狀態卡 20
      [50, 84, 0.2, 1],
      [5.5, 9, 1, 2], // 頭頂 11
      [5.5, 9, 1, 1],
      [30, 52, 1, 2], // 開發頁 52
    ];
    for (const id of IDS)
      for (const [c, size, u, res] of cases) {
        const a = rec(() => paintStatusIcon(fakeCtx(log), id, c, c, size, u, res));
        const b = rec(() => QT.paint(fakeCtx(log), id, c, c, size, u, res));
        expect(a, `${id} ${size} ${res}`).toBe(b);
      }
  });

  it("預設 unitPx 1、res ICON_RES（舊呼叫 paintStatusIcon(ctx, id, cx, cy, size) 照樣成立）", () => {
    for (const id of ["stun", "burning", "hasted", "stance_fire_3"]) expect(rec(() => paintStatusIcon(fakeCtx(log), id, 7, 7, 14))).toBe(rec(() => QT.paint(fakeCtx(log), id, 7, 7, 14, 1, ICON_RES)));
  });

  it("外層 ctx 不再設 glyphColor 的顏色（圖樣自帶本色，貼成一張畫布）", () => {
    for (const id of IDS) {
      reset();
      const outer: FakeCanvasLog = { calls: [] };
      paintStatusIcon(fakeCtx(outer), id, 50, 50, 84, 0.2, 2);
      const cols = (outer.calls ?? []).filter((c) => c.startsWith("fillStyle=") || c.startsWith("strokeStyle=")).map((c) => c.split("=")[1]);
      const g = glyphColor(id);
      // 例外：glyphColor 剛好等於框色或類別底色的不算（目前沒有）
      expect(cols.includes(g), `${id} ${g} in ${cols.join(",")}`).toBe(false);
      expect(outer.calls?.some((c) => c.startsWith("fillText")), id).toBe(false);
    }
  });
});

describe("T-B2 頭頂 statusIconCanvas", () => {
  it("statusIconCanvas(id, 11)：畫布 22 × 22、框 9、unitPx 1、res 2；res 1 時 11 × 11；紀錄＝qIcon/status.ts 的 headCanvas", () => {
    for (const id of IDS) {
      for (const res of [2, 1]) {
        clearStatusIconCache();
        const a = rec(() => statusIconCanvas(id, 11, res));
        expect(a.startsWith(res === 2 ? "22x22|" : "11x11|"), id).toBe(true);
        expect(a, `${id} res ${res}`).toBe(rec(() => QT.headCanvas(id, 11, 1, { res })));
      }
      clearStatusIconCache();
      expect(rec(() => statusIconCanvas(id, 11)), id).toBe(rec(() => QT.headCanvas(id, 11, 1, { res: 2 }))); // 預設 res＝ICON_RES
    }
  });

  it("statusIconKey 含 res：不同 res 不同鍵、不同快取", () => {
    expect(statusIconKey("stun", 11, 1)).not.toBe(statusIconKey("stun", 11, 2));
    expect(statusIconKey("stun", 11)).toBe(statusIconKey("stun", 11, ICON_RES));
    reset();
    const a = statusIconCanvas("stun", 11, 1);
    const b = statusIconCanvas("stun", 11, 2);
    expect(a).not.toBe(b);
    expect(statusIconCanvas("stun", 11, 2)).toBe(b);
  });

  it("沒有畫布時回 null（同 3a 以前沒有 DOM 的行為）", () => {
    setQCanvasFactory(null);
    (globalThis as { document?: unknown }).document = undefined;
    expect(statusIconCanvas("stun", 11)).toBeNull();
  });

  it("頭頂框 9 的線寬 1.5、染底的 7 個不包外框、留 1 裝置像素底色圈（fitK 用 inset 0.5 那筆）", () => {
    reset();
    statusIconCanvas("burning", 11);
    expect(log.calls).toContain("lineWidth=1.500");
    for (const id of ["stun", "frozen", "slow", "root", "taunted", "feared", "silenced"]) expect(QT.fitK(id, 9, 0.5), id).toBe(QT.fitK(id, 9, QT.tintInset(9, 2, QT.clsOf(id))));
  });
});

describe("T-B3 狀態卡 statusIconTile＋tileCanvas", () => {
  it("tileCanvas(statusIconTile(id), 20)：畫布 40 × 40、紀錄＝qIcon/status.ts 的 cardCanvas（paint 收 unitPx 0.2、res 2，blit 單位 0.4）", () => {
    for (const id of IDS) {
      clearSkillIconCache();
      const a = rec(() => tileCanvas(statusIconTile(id), 20));
      expect(a.startsWith("40x40|"), id).toBe(true);
      expect(a, id).toBe(rec(() => QT.cardCanvas(id, 20, 1, { res: 2 })));
      expect(a, id).toContain("lineWidth=7.560"); // max(1.5, 16.8 × 0.09) / 0.2
      clearSkillIconCache();
      expect(rec(() => tileCanvas(statusIconTile(id), 20, 1)), id).toBe(rec(() => QT.cardCanvas(id, 20, 1, { res: 1 })));
    }
  });

  it("paint 收到的 unitPx／res：tileCanvas 傳 px/100 與 res；直接呼叫 draw 時退回 20px（0.2）與 ICON_RES", () => {
    const seen: number[][] = [];
    const tile = statusIconTile("stun");
    const spy = { ...tile, draw: (ctx: CanvasRenderingContext2D, u?: number, res?: number) => (seen.push([u ?? -1, res ?? -1]), tile.draw(ctx, u, res)) };
    reset();
    tileCanvas(spy, 20);
    tileCanvas(spy, 24, 1);
    expect(seen).toEqual([
      [0.2, 2],
      [0.24, 1],
    ]);
    expect(STATUS_CARD_PX).toBe(20);
    expect(rec(() => tile.draw(fakeCtx(log)))).toBe(rec(() => paintStatusIcon(fakeCtx(log), "stun", 50, 50, 84, 0.2, ICON_RES)));
  });

  it("tileKey 含 res；TileCanvas 的畫布＝顯示 × ICON_RES（iconCanvasPx）", () => {
    const t = statusIconTile("stun");
    expect(tileKey(t, 20, 1)).not.toBe(tileKey(t, 20, 2));
    expect(tileKey(t, 20)).toBe(tileKey(t, 20, ICON_RES));
    const src = srcOf("ui/SkillIconView.tsx");
    expect(src).toMatch(/export function TileCanvas[\s\S]*?width=\{iconCanvasPx\(px\)\} height=\{iconCanvasPx\(px\)\}/);
    expect(src).toMatch(/ctx\.drawImage\(tileCanvas\(tile, px\), 0, 0\)/);
  });
});

describe("statusTile（部件圓片，0.0 第 7 點）", () => {
  it("第④批 STATUS 32 種畫 Q 版圖樣；其餘經 QP.hooks.status（skillParts.ts 載入時掛的現行圖樣）", () => {
    const hooked: string[] = [];
    const orig = QP.hooks.status;
    expect(orig).not.toBeNull();
    QP.hooks.status = (c, o, id) => {
      hooked.push(id);
      orig?.(c, o, id);
    };
    try {
      for (const id of IDS) {
        reset();
        tileCanvas(statusTile(id), 24);
      }
    } finally {
      QP.hooks.status = orig;
    }
    const q = IDS.filter((id) => QP.STATUS[id] !== undefined);
    expect(q).toHaveLength(32); // 第④批 STATUS（需求 1.1）
    expect([...new Set(hooked)].sort()).toEqual(IDS.filter((id) => QP.STATUS[id] === undefined).sort());
    expect(new Set(hooked).size).toBe(86); // 118 − 32
  });

  it("unitSprite.statusTexture 仍是 tileCanvas(statusTile(id), 24)（定時炸彈、蓄力徽章跟著換）", () => {
    const src = srcOf("render/unitSprite.ts");
    expect(src).toContain("Texture.from(tileCanvas(statusTile(statusId), 24))");
  });
});

describe("T-B7 部件圓片與召喚物不受影響", () => {
  it("skillParts.statusColor() 仍等於 glyphColor()（名詞表全部＋不認得）", () => {
    for (const id of [...IDS, "brand_new_status"]) expect(statusColor(id), id).toBe(glyphColor(id));
  });
});
