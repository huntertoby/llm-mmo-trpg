// AR-SK4（美術 PM 驗收）：戰前佈置的說明句自己計「前 3 次」，不和一般選目標共用次數。
import { describe, expect, it } from "vitest";
import type { PrepOut } from "../api/types";
import { modeHintKind } from "../ui/ActionPanel";
import { bumpOpHint, OP_HINT_LIMIT, opHintCount, showOpHint, type HintStore } from "./opHints";
import { prepMode } from "./prep";

const PREP: PrepOut = {
  unit_id: "unit_0001",
  zone: [[1, 0]],
  options: [{ skill_id: "skill_bear_trap", kind: "trap", tiles: [[1, 0]] }],
};

function memoryStore(): HintStore {
  const m = new Map<string, string>();
  return {
    getItem: (k) => m.get(k) ?? null,
    setItem: (k, v) => void m.set(k, v),
    removeItem: (k) => void m.delete(k),
  };
}

describe("AR-SK4 佈置說明句的次數", () => {
  it("佈置選格的說明句種類是 prep；同一招換成一般選目標仍是 target", () => {
    const mode = prepMode(PREP, "skill_bear_trap", "捕獸夾")!;
    expect(modeHintKind(mode)).toBe("prep");
    expect(modeHintKind({ ...mode, key: "skill:skill_bear_trap" })).toBe("target");
  });

  it("選過 3 次目標以後，第一次佈置的說明句仍完整顯示", () => {
    const store = memoryStore();
    for (let i = 0; i < OP_HINT_LIMIT; i++) bumpOpHint("target", store);
    expect(showOpHint("target", store)).toBe(false);
    expect(opHintCount("prep", store)).toBe(0);
    expect(showOpHint("prep", store)).toBe(true);
  });

  it("佈置 3 次以後，一般選目標的說明句不受影響", () => {
    const store = memoryStore();
    for (let i = 0; i < OP_HINT_LIMIT; i++) bumpOpHint("prep", store);
    expect(showOpHint("prep", store)).toBe(false);
    expect(opHintCount("target", store)).toBe(0);
    expect(showOpHint("target", store)).toBe(true);
  });
});
