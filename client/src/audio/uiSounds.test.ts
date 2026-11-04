import { describe, expect, it } from "vitest";
import type { WorldView } from "../api/types";
import { worldSoundFor } from "../world/useWorldSounds";
import { AudioEngine } from "./engine";
import { FakeAudioContext } from "./fakeAudio";
import { DEFAULT_AUDIO_SETTINGS, normalizeSettings } from "./settings";
import { registerSfxLibrary, SFX_TABLE } from "./sfxLibrary";
import { clickSoundFor, installUiSounds, setUiTurnScheduler, UI_SOUNDS, uiSound, type ElLike } from "./uiSounds";

/** 假元素：`closest` 只認自己符不符合（測試裡元素就是可點的那個）。 */
function el(tag: string, attrs: Record<string, string> = {}, text = "", className = ""): ElLike {
  const self: ElLike = {
    tagName: tag.toUpperCase(),
    textContent: text,
    className,
    getAttribute: (n) => attrs[n] ?? null,
    closest: () => self,
  };
  return self;
}

const none: ElLike = { tagName: "DIV", textContent: "", getAttribute: () => null, closest: () => null };

describe("介面音清單（2.2）", () => {
  it("20 個介面音都在參數表裡", () => {
    expect(UI_SOUNDS).toHaveLength(20);
    for (const id of UI_SOUNDS) expect(SFX_TABLE.defs[id]?.cat, id).toBe("ui");
  });
});

describe("點擊挑音", () => {
  it("依元素挑介面音", () => {
    expect(clickSoundFor(el("button", {}, "前往"))).toBe("ui_tap");
    expect(clickSoundFor(el("button", { "data-sfx": "ui_coin" }, "買"))).toBe("ui_coin");
    expect(clickSoundFor(el("button", { "data-sfx": "none" }, "x"))).toBeNull();
    expect(clickSoundFor(el("input", { type: "checkbox" }))).toBe("ui_toggle");
    expect(clickSoundFor(el("button", { role: "tab" }, "技能"))).toBe("ui_toggle");
    expect(clickSoundFor(el("button", { "aria-pressed": "false" }, "地圖"))).toBe("ui_toggle");
    expect(clickSoundFor(el("button", { "data-state": "disabled" }, "背包"))).toBe("ui_error");
    expect(clickSoundFor(el("button", { "aria-disabled": "true" }, "火球"))).toBe("ui_error");
    expect(clickSoundFor(el("button", { type: "submit" }, "送出"))).toBe("ui_confirm");
    expect(clickSoundFor(el("button", {}, "接受", "primary"))).toBe("ui_confirm");
    expect(clickSoundFor(el("button", { "aria-label": "關閉" }, "×"))).toBe("ui_cancel");
    expect(clickSoundFor(el("button", {}, "取消"))).toBe("ui_cancel");
    expect(clickSoundFor(el("button", {}, "下一頁 ▶"))).toBe("ui_page");
    expect(clickSoundFor(el("button", {}, "學會這招"))).toBe("ui_learn");
    expect(clickSoundFor(el("div", { role: "option" }, "火球"))).toBe("ui_select");
    expect(clickSoundFor(none)).toBeNull();
    expect(clickSoundFor(null)).toBeNull();
  });

  it("一下點擊只放一聲：已經有事件音（例如打開面板）就不疊輕觸", () => {
    const turns: (() => void)[] = [];
    const endTurn = () => {
      for (const f of turns.splice(0)) f();
    };
    setUiTurnScheduler((cb) => turns.push(cb)); // 一輪要手動結束
    const ctx = new FakeAudioContext();
    const engine = new AudioEngine({ createContext: () => ctx, settings: normalizeSettings(DEFAULT_AUDIO_SETTINGS) });
    engine.unlock();
    registerSfxLibrary(engine);
    let fn: ((e: Event) => void) | null = null;
    const deferred: (() => void)[] = [];
    const remove = installUiSounds({ addEventListener: (_t, f) => (fn = f), removeEventListener: () => (fn = null) }, engine, (f) => deferred.push(f));
    const click = (target: ElLike) => fn?.({ target } as unknown as Event);
    // 按鈕打開面板：事件音先到，輕觸取消
    click(el("button", {}, "背包"));
    expect(uiSound("ui_panel_open", engine)).toBe("played");
    for (const f of deferred.splice(0)) f();
    expect(engine.activeVoices("ui_tap")).toBe(0);
    expect(engine.activeVoices("ui_panel_open")).toBe(1);
    // 同一輪的第二個事件音不疊
    expect(uiSound("ui_panel_close", engine)).toBe("skipped");
    // 新的一輪：一般按鈕只有輕觸
    endTurn();
    click(el("button", {}, "前往"));
    for (const f of deferred.splice(0)) f();
    expect(engine.activeVoices("ui_tap")).toBe(1);
    remove();
    expect(fn).toBeNull();
    setUiTurnScheduler((cb) => cb());
  });
});

function view(p: { char?: string; level?: number; gold?: number; quests?: { id: string; done: boolean; steps: boolean[] }[]; items?: number }): WorldView {
  return {
    character: { character_id: p.char ?? "c1", level: p.level ?? 1 },
    wallet: { gold: p.gold ?? 0, quest_coins: 0 },
    quests: (p.quests ?? []).map((q) => ({ id: q.id, done: q.done, steps: q.steps.map((d) => ({ done: d, current: false, text_zh: "" })) })),
    inventory: { bag: Array.from({ length: p.items ?? 0 }, (_, i) => ({ item: `it${i}`, name_zh: "x", count: 1, gear: false })), pouch: [], equipment: [] },
  } as unknown as WorldView;
}

describe("大世界事件音（只看前後兩次畫面）", () => {
  it("依變化挑一聲，優先：升級 → 任務完成 → 任務更新 → 物品 → 金幣", () => {
    const a = view({ gold: 5, quests: [{ id: "q", done: false, steps: [false, false] }] });
    expect(worldSoundFor(null, a)).toBeNull();
    expect(worldSoundFor(a, a)).toBeNull();
    expect(worldSoundFor(a, view({ gold: 9, quests: [{ id: "q", done: false, steps: [false, false] }] }))).toBe("ui_coin");
    expect(worldSoundFor(a, view({ gold: 5, quests: [{ id: "q", done: false, steps: [true, false] }] }))).toBe("ui_quest_update");
    expect(worldSoundFor(a, view({ gold: 5, quests: [{ id: "q", done: false, steps: [false, false] }, { id: "r", done: false, steps: [false] }] }))).toBe("ui_quest_update");
    expect(worldSoundFor(a, view({ gold: 9, quests: [{ id: "q", done: true, steps: [true, true] }] }))).toBe("ui_quest_done");
    expect(worldSoundFor(a, view({ level: 2, gold: 9, quests: [{ id: "q", done: true, steps: [true, true] }] }))).toBe("ui_levelup");
    expect(worldSoundFor(a, view({ gold: 9, items: 1, quests: [{ id: "q", done: false, steps: [false, false] }] }))).toBe("ui_item");
    expect(worldSoundFor(a, view({ char: "c2", level: 5 }))).toBeNull(); // 換角色
    expect(worldSoundFor(a, view({ gold: 1, quests: [{ id: "q", done: false, steps: [false, false] }] }))).toBeNull(); // 花錢不出聲
  });
});
