// BM-1（GB-4b 待決 9）：開場的第一次播放不在 effect 裡同步呼叫 flushSync（React 開發模式警告「flushSync was called from inside a lifecycle method」）。
import { describe, expect, it } from "vitest";
import { readFile, SRC_DIR } from "../../test/sourceScan";

describe("usePlayback 開場播放", () => {
  it("effect 先讓出一個微任務才呼叫 play（play 開頭就 flushSync）", () => {
    const s = readFile(SRC_DIR, "screens/battle/usePlayback.ts");
    const at = s.indexOf("await play(initial, true);");
    expect(at).toBeGreaterThan(0);
    expect(s.slice(Math.max(0, at - 300), at)).toContain("await Promise.resolve();");
  });
});
