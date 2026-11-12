// QI-4a T-A8：部件圓片 `statusTile` 其餘 86 種換 Q 版（規格 docs/phases/PhaseQI-4計畫.md A3、A4、第 0 節第 9、10、12 列）。
// `skillParts.ts` 掛的 `QP.hooks.status` 改成：`qIcon/status.ts` 認得的畫 `entry(id).d`；不認得的照 QI-2c 的現行圖樣（`statusGlyph`＋`statusColor`）。
// 資料一律用名詞表快照 battle/fixtures/glossary.json（118 個狀態）。
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import glossary from "../battle/fixtures/glossary.json";
import { fakeCanvasFactory, type FakeCanvasLog } from "../test/fakeCanvas";
import { setQCanvasFactory, type Ctx, type QOpts } from "./qIcon/core";
import * as QP from "./qIcon/parts";
import * as QT from "./qIcon/status";
import { clearSkillIconCache, statusTile, tileCanvas } from "./skillIcon";
import { STATUS_TILE_FIT, statusColor, statusGlyph, statusTileFits } from "./skillParts";

const IDS = (glossary as unknown as { statuses: { id: string }[] }).statuses.map((s) => s.id).sort();
const OTHER = IDS.filter((id) => QP.STATUS[id] === undefined);
const FAINT_RING = "rgba(255,255,255,0.3)";

let log: FakeCanvasLog = { calls: [] };
function rec(draw: () => HTMLCanvasElement | null): string {
  log = { calls: [] };
  const make = fakeCanvasFactory(log);
  setQCanvasFactory(make);
  (globalThis as { document?: unknown }).document = { createElement: () => make(0, 0) };
  const cv = draw();
  return `${cv ? `${cv.width}x${cv.height}` : "-"}|${(log.calls ?? []).join(";")}`;
}
/** 掛鉤暫時換成 `hook` 畫一次 `statusTile(id)` 24px（參考畫法；畫完換回）。 */
function withHook(hook: (c: Ctx, o: QOpts, id: string) => void, id: string): string {
  const orig = QP.hooks.status;
  QP.hooks.status = hook;
  try {
    clearSkillIconCache();
    return rec(() => tileCanvas(statusTile(id), 24));
  } finally {
    QP.hooks.status = orig;
    clearSkillIconCache();
  }
}
/** QI-2c～QI-3b 的掛鉤本體（現行圖樣），照 skillParts.ts 改前的那一段。 */
const legacyHook = (c: Ctx, _o: QOpts, id: string): void => {
  c.save();
  c.fillStyle = c.strokeStyle = statusColor(id);
  c.lineWidth = 2.2;
  c.lineCap = c.lineJoin = "round";
  statusGlyph(c, id);
  c.restore();
};

let savedDoc: unknown;
beforeEach(() => {
  savedDoc = (globalThis as { document?: unknown }).document;
  clearSkillIconCache();
});
afterEach(() => {
  (globalThis as { document?: unknown }).document = savedDoc;
  setQCanvasFactory(null);
  clearSkillIconCache();
});

describe("T-A8 statusTile 其餘 86 種＝Q 版圓片＋qIcon/status.ts 的圖樣", () => {
  it("名詞表 118 個：32 種是第④批 STATUS、86 種 status.ts 都認得", () => {
    expect(IDS).toHaveLength(118);
    expect(OTHER).toHaveLength(86);
    for (const id of IDS) expect(QT.entry(id), id).not.toBeNull();
  });

  // QI-4b 改寫（美術 PM QI-4a 驗收可修 1）：舊＝86 種都＝掛鉤直接畫 entry(id).d → 新＝六角臂章 `stance_*`（48 個）照舊直接畫，
  // 其他 38 個＝第④批同一個 `fit()`（k＝0.86）包住 entry(id).d；兩種都不經 statusGlyph。
  it("86 種的呼叫紀錄＝掛鉤畫 status.ts 的 entry(id).d（stance_* 直接畫、其他經 fit 0.86 縮進色環；不經 statusGlyph），而且和現行圖樣不同", () => {
    const fitted = OTHER.filter(statusTileFits);
    expect(STATUS_TILE_FIT).toBe(0.86);
    expect(fitted).toHaveLength(38);
    expect(OTHER.filter((id) => !statusTileFits(id)).every((id) => id.startsWith("stance_"))).toBe(true);
    for (const id of OTHER) {
      clearSkillIconCache();
      const now = rec(() => tileCanvas(statusTile(id), 24));
      const direct = withHook((c, o, x) => QT.entry(x)!.d(c, o), id);
      const viaFit = withHook((c, o, x) => QP.fit((q, p) => QT.entry(x)!.d(q, p), 0.86)(c, o), id);
      expect(now, id).toBe(statusTileFits(id) ? viaFit : direct);
      if (statusTileFits(id)) expect(now, id).not.toBe(direct);
      expect(now, id).not.toBe(withHook(legacyHook, id));
    }
  });

  it("第④批 32 種不經掛鉤：換掉掛鉤呼叫紀錄不變", () => {
    for (const id of IDS.filter((x) => QP.STATUS[x] !== undefined)) {
      clearSkillIconCache();
      const now = rec(() => tileCanvas(statusTile(id), 24));
      expect(withHook(legacyHook, id), id).toBe(now);
    }
  });

  it("不認得的狀態（brand_new_status）照舊畫現行圖樣（名稱第一個字）", () => {
    expect(QT.entry("brand_new_status")).toBeNull();
    clearSkillIconCache();
    const now = rec(() => tileCanvas(statusTile("brand_new_status"), 24));
    expect(now).toBe(withHook(legacyHook, "brand_new_status"));
    expect(now).toContain("fillText(");
  });

  it("色環仍是 FAINT_RING（白 30%，第 0 節第 9 列），圓片半徑 42", () => {
    for (const id of IDS) {
      clearSkillIconCache();
      const now = rec(() => tileCanvas(statusTile(id), 24));
      expect(now, id).toContain(`strokeStyle=${FAINT_RING}`);
      expect(now, id).toContain("arc(50.000,50.000,42.000,0.000,6.283)");
    }
  });

  it("qi2dBaseline 的部件（全部 CATS × 18、30 × res 1、2）沒有任何一筆經 hooks.status（A4 名單為空，基準不變）", () => {
    const hit: string[] = [];
    const orig = QP.hooks.status;
    QP.hooks.status = (c, o, id) => {
      hit.push(id);
      orig?.(c, o, id);
    };
    try {
      setQCanvasFactory(fakeCanvasFactory({ calls: null }));
      for (const [cat, T] of Object.entries(QP.CATS)) for (const id of Object.keys(T ?? {})) for (const px of [18, 30]) for (const res of [1, 2]) {
        if (cat === "card") QP.cardCanvas(id, px, 1, { res });
        else QP.chipCanvas(cat, id, px, 1, { res });
      }
    } finally {
      QP.hooks.status = orig;
    }
    expect(hit).toEqual([]);
  });
});
