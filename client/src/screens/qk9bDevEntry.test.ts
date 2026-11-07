// QK-9b 第 3 項：開發入口（開場朝向、開場召喚物／形態、傳送到某區城鎮）只在開發模式（`?dev=1`）看得到；
// 伺服器端另外只在開發模式掛、要 `TRPG_DEV_ROUTES=1`（tests/api/test_world_dev_boss.py）。
import { describe, expect, it } from "vitest";
import { devMoreQuery } from "../api/client";
import { isDevMode } from "../run/startFlow";
import { readFile, SRC_DIR, stripTsComments } from "../test/sourceScan";

const SRC = stripTsComments(readFile(SRC_DIR, "screens/WorldScreen.tsx"), "screens/WorldScreen.tsx");

describe("QK-9b 開發入口", () => {
  it("查詢參數：只帶有給的，順序固定（區域、朝向、開場）", () => {
    expect(devMoreQuery({})).toBe("");
    expect(devMoreQuery({ facing: "north" })).toBe("&facing=north");
    expect(devMoreQuery({ opening: "summon", region: "ashen_waste", facing: "west" })).toBe("&region=ashen_waste&facing=west&opening=summon");
    expect(devMoreQuery({ region: "", facing: undefined })).toBe("");
  });

  it("正式模式不可達：開發按鈕（頭目戰、傳送）都包在 `devMode &&` 裡；沒有 `?dev=1` 就不是開發模式", () => {
    const ids = [...SRC.matchAll(/data-testid="(world-dev-[a-z-]+)"/g)].map((m) => m[1]);
    expect(ids).toEqual(["world-dev-boss", "world-dev-teleport"]);
    for (const id of ids) {
      const at = SRC.indexOf(`data-testid="${id}"`);
      const before = SRC.slice(Math.max(0, at - 220), at);
      expect(before.lastIndexOf("{devMode && ("), id).toBeGreaterThan(-1);
      expect(before.slice(before.lastIndexOf("{devMode && (")).includes(")}"), id).toBe(false);
    }
    expect(isDevMode("")).toBe(false);
    expect(isDevMode("?boss=x&bossface=north&tp=ashen_waste")).toBe(false);
    expect(isDevMode("?dev=1")).toBe(true);
  });

  it("參數名：`bossface`、`bossopen`、`bossregion`、`tp`（預設灰燼荒原）", () => {
    for (const key of ['q.get("bossface")', 'q.get("bossopen")', 'q.get("bossregion")', 'q.get("tp") ?? "ashen_waste"']) expect(SRC).toContain(key);
  });
});
