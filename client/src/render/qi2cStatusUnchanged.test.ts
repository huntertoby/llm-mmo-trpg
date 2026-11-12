// QI-2c T-C6：「不動的確認」。單位頭頂狀態（`statusTile` 24px）與狀態卡狀態（`statusIconTile` 20px）的畫面不變（第⑤批 QI-3 才換）。
// 對名詞表全部狀態，經 `tileCanvas` 畫在假畫布上，呼叫紀錄（含畫布寬高）的雜湊要和 2c 開工前（2b 合併後的 main `a5825a77`）錄的基準完全相同。
// 基準檔 `fixtures/qi2cStatusBaseline.json` 由這個檔在 `QI2C_RECORD=1` 時寫出（只在開工前錄一次；之後不得重錄）。
import { writeFileSync } from "node:fs";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import glossary from "../battle/fixtures/glossary.json";
import { fakeCanvasFactory, type FakeCanvasLog } from "../test/fakeCanvas";
import baseline from "./fixtures/qi2cStatusBaseline.json";
import { statusIconTile, statusTile, tileCanvas } from "./skillIcon";
import { setQCanvasFactory } from "./qIcon/core";

/** FNV-1a 32 位元（確定性，不用內建 hash）。 */
function fnv(s: string): string {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h.toString(16).padStart(8, "0");
}

const STATUS_IDS = (glossary as unknown as { statuses: { id: string }[] }).statuses.map((s) => s.id).sort();

/** 用假畫布畫一塊，回傳「寬x高|呼叫紀錄」的雜湊。`document.createElement` 與 Q 版畫布工廠都接到同一份紀錄。 */
function record(draw: () => HTMLCanvasElement): string {
  const log: FakeCanvasLog = { calls: [] };
  const make = fakeCanvasFactory(log);
  (globalThis as { document?: unknown }).document = { createElement: () => make(0, 0) };
  setQCanvasFactory((w, h) => make(w, h));
  const cv = draw();
  return fnv(`${cv.width}x${cv.height}|${(log.calls ?? []).join(";")}`);
}

describe("QI-2c T-C6 狀態圖示不動", () => {
  let saved: unknown;
  beforeEach(() => {
    saved = (globalThis as { document?: unknown }).document;
  });
  afterEach(() => {
    (globalThis as { document?: unknown }).document = saved;
    setQCanvasFactory(null);
  });

  it("名詞表全部狀態的 statusTile(24)、statusIconTile(20) 呼叫紀錄和開工前相同", () => {
    const now: Record<string, string> = {};
    for (const id of STATUS_IDS) {
      // 每個 id、每個尺寸各畫一次（tileCanvas 有快取：鍵是 px|id，這裡每組只畫一次）
      now[`head|${id}`] = record(() => tileCanvas(statusTile(id), 24));
      now[`card|${id}`] = record(() => tileCanvas(statusIconTile(id), 20));
    }
    if (process.env["QI2C_RECORD"] === "1") writeFileSync(new URL("./fixtures/qi2cStatusBaseline.json", import.meta.url), `${JSON.stringify(now, null, 1)}\n`);
    expect(STATUS_IDS.length).toBeGreaterThan(100);
    expect(now).toEqual(baseline);
  });
});
