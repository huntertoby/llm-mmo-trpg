// WL-1 c 第 2 項（玩法 PM 2026-11-22 第 2 題選 A）：狀態名稱找不到時顯示「未知狀態」，玩家畫面不出現英文 id。
// 會顯示狀態名稱的地方（實作前 grep `statusName(` 列出）：組裝列狀態圓片（`statusTile`，含說明框標題）、效果／條件部件的名稱、
// 狀態卡（`StatusBadge` 的文字與 aria-label，`Hud.statusLine`／`UnitInfo`）、戰場浮字（`feedback`）、預覽（`previewText`、`pathPreview.statusWord`）、
// 賭局結果（`gamble`）。圖示中間：有名稱畫第一個字，沒有名稱畫「?」（見 `wl1bFallbackPaths.test.ts`）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import type { Glossary, StatusView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGlossary, statusName, statusNameOrNull, UNKNOWN_STATUS_NAME } from "../battle/glossary";
import { statusWord } from "../battle/pathPreview";
import { statusLine } from "../ui/Hud";
import { StatusBadge } from "../ui/StatusCardParts";
import { statusTile, tileTitle } from "./skillIcon";
import { effectPart } from "./skillParts";
import { fakeCtx, type FakeCanvasLog } from "../test/fakeCanvas";
import * as QT from "./qIcon/status";
import { drawGlyph, statusIconKey } from "./statusIcon";

const real = glossary as unknown as Glossary;
afterEach(() => setGlossary(real));

const ID = "brand_new_status";
const sv = (status_id: string): StatusView => ({ status_id, remaining: 2, amount: null, cost_status: false }) as unknown as StatusView;

describe("WL-1 c：狀態名稱找不到時顯示「未知狀態」", () => {
  it("名詞表沒有、空字串、名詞表名稱是空字串都回「未知狀態」；有名稱照名詞表", () => {
    expect(statusName(ID)).toBe(UNKNOWN_STATUS_NAME);
    expect(statusName("")).toBe(UNKNOWN_STATUS_NAME);
    expect(statusName("burning")).toBe(real.statuses.find((e) => e.id === "burning")!.name_zh);
    setGlossary({ ...real, statuses: [...real.statuses, { id: "blank_status", name_zh: "", description_zh: null, tags: [], rules_zh: [], rules_dice: [], status_look: null }] } as unknown as Glossary);
    expect(statusName("blank_status")).toBe(UNKNOWN_STATUS_NAME);
    expect(statusNameOrNull("blank_status")).toBeNull();
    expect(statusNameOrNull(ID)).toBeNull();
    expect(statusNameOrNull(null)).toBeNull();
  });

  it("每個會顯示狀態名稱的地方都不出現英文 id", () => {
    const texts: string[] = [
      statusTile(ID).label,
      tileTitle(statusTile(ID)),
      effectPart({ type: "apply_status", status: ID }).label,
      statusLine(sv(ID)),
      statusWord(ID),
      renderToStaticMarkup(createElement(StatusBadge, { status: sv(ID), text: statusLine(sv(ID)) })),
    ];
    for (const t of texts) {
      expect(t).not.toContain(ID);
      expect(t).not.toMatch(/brand|new_status/);
    }
    expect(statusTile(ID).label).toBe(UNKNOWN_STATUS_NAME);
    expect(statusLine(sv(ID))).toBe(`${UNKNOWN_STATUS_NAME}（2 回合）`);
    expect(texts[5]).toContain(`狀態：${UNKNOWN_STATUS_NAME}`);
  });
});

describe("WL-1c 追加 3：名稱是退回用的字（未知狀態）時，圖示中間畫「?」不畫「未」", () => {
  const center = (fn: (ctx: CanvasRenderingContext2D) => void): string[] => {
    const log: FakeCanvasLog = { calls: [] };
    fn(fakeCtx(log));
    return (log.calls ?? []).filter((c) => c.startsWith("fillText(")).map((c) => c.slice("fillText(".length).split(",")[0]!);
  };
  it("狀態卡／頭頂（qIcon/status.ts 的 paintUnknown）、舊圖樣 drawGlyph、快取鍵都用「?」", () => {
    setGlossary({ ...real, statuses: [...real.statuses, { id: "named_new", name_zh: "怪異", description_zh: null, tags: [], rules_zh: [], rules_dice: [], status_look: null }] } as unknown as Glossary);
    for (const id of [ID, "another_new_status", ""]) {
      expect(center((ctx) => QT.paint(ctx, id, 10, 10, 16.8)), id).toEqual(["?"]);
      expect(center((ctx) => QT.paint(ctx, id, 10, 10, 9)), id).toEqual(["?"]);
      expect(center((ctx) => drawGlyph(ctx, id)), id).toEqual(["?"]);
    }
    expect(statusIconKey(ID, 20)).toContain("|?|");
    expect(statusIconKey(ID, 20)).not.toContain("未");
    // 名詞表有名稱、只是沒有 Q 版圖樣的，照舊畫名稱第一個字
    expect(center((ctx) => QT.paint(ctx, "named_new", 10, 10, 16.8))).toEqual(["怪"]);
    expect(center((ctx) => drawGlyph(ctx, "named_new"))).toEqual(["怪"]);
  });
});
