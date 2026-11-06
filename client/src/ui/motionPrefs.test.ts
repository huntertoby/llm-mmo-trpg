// 6H-1：遊戲內「減少動態」開關（跟系統／開／關）：三個值都生效、能存讀、壞掉的儲存不出錯；
// 畫面端（frameLoop、震動預設）讀有效值；CSS 屬性；設定區塊的三個選項。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { loadShake } from "../battle/vfxPrefs";
import { prefersReducedMotion, subscribeReducedMotion } from "../world/frameLoop";
import { MotionSettingsSection } from "./MotionSettingsSection";
import { applyMotionAttr, effectiveReduced, loadMotionPref, MOTION_ATTR, MOTION_KEY, reducedMotion, resetMotionPrefMemo, saveMotionPref } from "./motionPrefs";

function fakeWindow(system: boolean, store: Record<string, string> = {}, broken = false) {
  const storage = {
    getItem: (k: string) => {
      if (broken) throw new Error("denied");
      return k in store ? store[k]! : null;
    },
    setItem: (k: string, v: string) => {
      if (broken) throw new Error("denied");
      store[k] = v;
    },
    removeItem: (k: string) => {
      if (broken) throw new Error("denied");
      delete store[k];
    },
  };
  vi.stubGlobal("window", {
    localStorage: storage,
    matchMedia: (q: string) => ({ matches: system && q === "(prefers-reduced-motion: reduce)", addEventListener: () => undefined, removeEventListener: () => undefined }),
  });
  return store;
}

afterEach(() => {
  vi.unstubAllGlobals();
  resetMotionPrefMemo();
});

describe("in-game reduced motion switch (6H-1)", () => {
  it("effective value: on → reduce, off → no, system → follows the OS", () => {
    expect(effectiveReduced("on", false)).toBe(true);
    expect(effectiveReduced("off", true)).toBe(false);
    expect(effectiveReduced("system", true)).toBe(true);
    expect(effectiveReduced("system", false)).toBe(false);
  });

  it("all three values take effect through frameLoop (every caller of prefersReducedMotion)", () => {
    fakeWindow(true);
    expect(loadMotionPref()).toBe("system");
    expect(prefersReducedMotion()).toBe(true);
    saveMotionPref("off");
    expect(prefersReducedMotion()).toBe(false);
    expect(reducedMotion()).toBe(false);
    saveMotionPref("on");
    expect(prefersReducedMotion()).toBe(true);
    fakeWindow(false);
    resetMotionPrefMemo();
    expect(prefersReducedMotion()).toBe(false);
  });

  it("saves and loads (system = nothing stored); unknown stored values fall back to system", () => {
    const store = fakeWindow(false);
    saveMotionPref("on");
    expect(store[MOTION_KEY]).toBe("on");
    resetMotionPrefMemo();
    expect(loadMotionPref()).toBe("on");
    saveMotionPref("off");
    resetMotionPrefMemo();
    expect(loadMotionPref()).toBe("off");
    saveMotionPref("system");
    expect(MOTION_KEY in store).toBe(false);
    resetMotionPrefMemo();
    expect(loadMotionPref()).toBe("system");
    fakeWindow(false, { [MOTION_KEY]: "maybe" });
    expect(loadMotionPref()).toBe("system");
  });

  it("broken storage does not throw; the choice still holds for this session", () => {
    fakeWindow(true, {}, true);
    expect(loadMotionPref()).toBe("system");
    expect(() => saveMotionPref("off")).not.toThrow();
    expect(reducedMotion()).toBe(false);
  });

  it("subscribers hear in-game changes (the renderer re-reads on change)", () => {
    fakeWindow(false);
    const seen: boolean[] = [];
    const off = subscribeReducedMotion(() => seen.push(prefersReducedMotion()));
    saveMotionPref("on");
    saveMotionPref("off");
    off();
    saveMotionPref("on");
    expect(seen).toEqual([true, false]);
  });

  it("the shake default follows the effective value", () => {
    fakeWindow(false);
    saveMotionPref("on");
    expect(loadShake()).toBe(false);
    saveMotionPref("off");
    expect(loadShake()).toBe(true);
  });

  it("writes <html data-reduced-motion> for CSS", () => {
    fakeWindow(false);
    const attrs: Record<string, string> = {};
    const doc = { documentElement: { setAttribute: (k: string, v: string) => (attrs[k] = v) } } as unknown as Document;
    applyMotionAttr(doc);
    expect(attrs[MOTION_ATTR]).toBe("false");
    saveMotionPref("on");
    applyMotionAttr(doc);
    expect(attrs[MOTION_ATTR]).toBe("true");
  });

  it("the settings section shows the three choices with system as the default", () => {
    const html = renderToStaticMarkup(createElement(MotionSettingsSection, { value: "system" }));
    expect(html).toContain("減少動態");
    expect(html).toContain("跟系統（預設）");
    expect(html.match(/type="radio"/g)).toHaveLength(3);
    const checkedOf = (h: string) => h.split("<input").filter((x) => /checked/.test(x.split(">")[0]!)).map((x) => /value="([a-z]+)"/.exec(x)?.[1]);
    expect(checkedOf(html)).toEqual(["system"]);
    expect(html).not.toContain("title=");
    const on = renderToStaticMarkup(createElement(MotionSettingsSection, { value: "on" }));
    expect(checkedOf(on)).toEqual(["on"]);
  });

  it("CSS: every reduced-motion block also looks at the attribute", async () => {
    // 沒有 @types/node：用變數名載入 node:fs（同 render/fontLoad.test.ts）
    const nodeFs = "node:fs";
    const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };
    for (const f of ["src/styles/skill-bar.css", "src/ui/uiMotion.css", "src/world/fieldPeople.css"]) {
      const css = readFileSync(f, "utf-8");
      expect(css).toContain(':root[data-reduced-motion="true"]');
      expect(css).toContain(":root:not([data-reduced-motion])");
    }
  });
});
