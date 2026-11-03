// 地點留言的純函式（Phase 5E-3）。
import { describe, expect, it } from "vitest";
import { NOTE_MAX, noteDeleteLabel, noteProblem, noteTime, remainingLabel } from "./notes";

describe("noteProblem", () => {
  it("accepts up to 50 characters after trimming", () => {
    expect(noteProblem("  霧裡有狼  ")).toBeNull();
    expect(noteProblem("字".repeat(NOTE_MAX))).toBeNull();
  });
  it("rejects empty, too long and multi-line text", () => {
    expect(noteProblem("   ")).toBe("留言不能是空的");
    expect(noteProblem("字".repeat(NOTE_MAX + 1))).toBe("最多 50 字");
    expect(noteProblem("第一行\n第二行")).toBe("留言不能換行");
  });
});

describe("remainingLabel", () => {
  it("counts characters, not bytes", () => {
    expect(remainingLabel("")).toBe("還可以打 50 字");
    expect(remainingLabel("霧裡")).toBe("還可以打 48 字");
    expect(remainingLabel("字".repeat(52))).toBe("超過 2 字");
  });
});

describe("noteDeleteLabel", () => {
  it("自己的留言與管理者刪別人的", () => {
    expect(noteDeleteLabel(true)).toBe("刪除我的留言");
    expect(noteDeleteLabel(false)).toContain("管理者");
  });
});

describe("noteTime", () => {
  it("shows Taipei time", () => {
    // 2026-11-03 06:05（UTC+8）
    expect(noteTime(1793657100)).toBe("11/03 06:05");
  });
});
