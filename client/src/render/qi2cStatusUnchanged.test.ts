// QI-2c T-C6 →（QI-3b T-B4 改寫）狀態圖示的畫面基準。
// QI-2c 時鎖「單位頭頂狀態（`statusTile` 24px）與狀態卡狀態（`statusIconTile` 20px）的畫面不變」（基準 `fixtures/qi2cStatusBaseline.json`，
// 2c 開工前 commit ef1f178a 錄的）。QI-3b（第⑤批）把兩個都換成 Q 版（規格 docs/phases/PhaseQI-3計畫.md 0.0 第 7 點、B1～B3），所以：
// - 現行畫面＝QI-3b 基準 `fixtures/qi3bStatusBaseline.json`（同一段 `record()`，3b 改完後錄一次；之後不得整批重錄）；
// - 舊基準留著：236 組全部和舊基準不同（兩半都換了），而且差異只來自本段——拿掉 3b 對 `skillIcon.ts`／`statusIcon.ts` 的改動，舊基準照樣全過
//   （報告 docs/phases/PhaseQI-3b報告.md 第 3 節）；
// - 換成什麼：`statusTile` ＝ Q 版部件圓片（`QP.chip("status", id, 50, 50, 42)`）、`statusIconTile` ＝ `qIcon/status.ts` 的 `cardCanvas`，逐筆呼叫紀錄相同。
// QI-4a（規格 docs/phases/PhaseQI-4計畫.md A3、A4）：`statusTile` 裡第④批 32 種以外的 86 種經 `hooks.status` 改畫 `qIcon/status.ts` 的圖樣，
// 所以 `qi3bStatusBaseline.json` 逐筆重錄：只有那 86 個 `head|<id>` 變（32 個 `head|` 與 118 個 `card|` 不變；名單與「拿掉改動回到舊值」的證明見
// docs/phases/PhaseQI-4a報告.md 第 3 節）。之後同樣不得整批重錄。
// QI-4b（美術 PM QI-4a 驗收可修 1）：掛鉤的圖樣套第④批 `fit()`（0.86）縮進色環、六角臂章 `stance_*` 不縮，再逐筆重錄：
// 只有 86 種裡非 `stance_*` 的 38 個 `head|<id>` 變（名單見 docs/phases/PhaseQI-4b報告.md 第 3 節）。
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import glossary from "../battle/fixtures/glossary.json";
import { fakeCanvasFactory, type FakeCanvasLog } from "../test/fakeCanvas";
import oldBaseline from "./fixtures/qi2cStatusBaseline.json";
import baseline from "./fixtures/qi3bStatusBaseline.json";
import { blank, ctxOf, setQCanvasFactory } from "./qIcon/core";
import * as QP from "./qIcon/parts";
import * as QT from "./qIcon/status";
import { clearSkillIconCache, statusIconTile, statusTile, tileCanvas } from "./skillIcon";

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
function record(draw: () => HTMLCanvasElement | null): string {
  const log: FakeCanvasLog = { calls: [] };
  const make = fakeCanvasFactory(log);
  (globalThis as { document?: unknown }).document = { createElement: () => make(0, 0) };
  setQCanvasFactory((w, h) => make(w, h));
  const cv = draw();
  if (cv === null) throw new Error("no canvas");
  return fnv(`${cv.width}x${cv.height}|${(log.calls ?? []).join(";")}`);
}

const ELEMENT_STANCE = /^stance_(\w+)_[1-5]$/;

describe("QI-2c T-C6（QI-3b 改寫）狀態圖示的畫面基準", () => {
  let saved: unknown;
  beforeEach(() => {
    saved = (globalThis as { document?: unknown }).document;
    clearSkillIconCache();
  });
  afterEach(() => {
    (globalThis as { document?: unknown }).document = saved;
    setQCanvasFactory(null);
    clearSkillIconCache();
  });

  it("名詞表全部狀態的 statusTile(24)、statusIconTile(20) 呼叫紀錄＝QI-3b 基準，且 236 組都和 QI-2c 舊基準不同", () => {
    const now: Record<string, string> = {};
    for (const id of STATUS_IDS) {
      // 每個 id、每個尺寸各畫一次（tileCanvas 有快取：鍵是 px|res|id，這裡每組只畫一次）
      now[`head|${id}`] = record(() => tileCanvas(statusTile(id), 24));
      now[`card|${id}`] = record(() => tileCanvas(statusIconTile(id), 20));
    }
    expect(STATUS_IDS.length).toBe(118); // 名詞表快照 118 個（需求 1.1）
    expect(now).toEqual(baseline);
    const old = oldBaseline as Record<string, string>;
    expect(Object.keys(old).sort()).toEqual(Object.keys(now).sort());
    expect(Object.keys(now).filter((k) => now[k] === old[k])).toEqual([]);
  });

  // QI-4a 改寫（規格 T-A8、第 8.2 節「元素架勢 45 個會是 9 組同圖」）：舊＝同雜湊只有 `card|stance_`、部件圓片 118 個兩兩不同
  // → 新＝部件圓片的元素架勢也走 status.ts（各級同圖），同雜湊是 `card|` 或 `head|` 的同元素 5 級（不跨卡／圓片）、部件圓片 118 − 9 × 4 ＝ 82 種。
  it("基準裡相同的雜湊只有元素架勢同元素的各級（狀態卡與部件圓片各自同圖，需求 2.4 第 3 列）；部件圓片 82 種", () => {
    const b = baseline as Record<string, string>;
    const groups = new Map<string, string[]>();
    for (const [k, v] of Object.entries(b)) groups.set(v, [...(groups.get(v) ?? []), k]);
    for (const keys of groups.values()) {
      if (keys.length === 1) continue;
      const els = new Set(keys.map((k) => ELEMENT_STANCE.exec(k.slice(5))?.[1] ?? "x"));
      const kind = keys[0]!.slice(0, 5);
      expect(kind === "card|" || kind === "head|", keys.join(",")).toBe(true);
      expect(keys.every((k) => k.startsWith(kind + "stance_")), keys.join(",")).toBe(true);
      expect(els.size, keys.join(",")).toBe(1);
      expect(keys).toHaveLength(5);
    }
    expect(new Set(STATUS_IDS.map((id) => b[`head|${id}`])).size).toBe(82); // 118 − 9 元素 × (5 − 1)
  });

  it("換成什麼：statusTile＝Q 版部件圓片（半徑 42、淡色環）、statusIconTile＝qIcon/status.ts 的 cardCanvas（逐筆紀錄相同）", () => {
    for (const id of STATUS_IDS) {
      clearSkillIconCache();
      const head = record(() => tileCanvas(statusTile(id), 24));
      const headRef = record(() => {
        const cv = blank(48);
        const x = ctxOf(cv);
        x.scale(0.48, 0.48);
        x.beginPath();
        x.arc(50, 50, 49, 0, Math.PI * 2);
        x.clip();
        QP.chip(x, "status", id, 50, 50, 42, { ring: "rgba(255,255,255,0.3)", unitPx: 0.24, res: 2 });
        return cv;
      });
      expect(head, id).toBe(headRef);
      const card = record(() => tileCanvas(statusIconTile(id), 20));
      expect(card, id).toBe(record(() => QT.cardCanvas(id, 20, 1, { res: 2 })));
    }
  });
});
