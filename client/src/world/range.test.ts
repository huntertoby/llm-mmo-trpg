// TR-1（#134）主城工坊靶場：武器架分組、「看示範」送的關鍵字、本機草稿、畫面結構（武器架三大類、看示範、確定出發）、
// 建角頁不再選武器、未完成開局時世界畫面改畫靶場、試打結束「回到靶場」。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { parse } from "yaml";
import type { RangeView, StartWeaponOption, WorldView } from "../api/types";
import newcomerYaml from "../../../content/world/newcomer.yaml?raw";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { CLASS_LABELS, demoKeywords, groupRacks, readDraft, writeDraft } from "./range";
import { CONFIRM_LABEL, RangeDoneDialog, RangeScreen, rangeDoneLines } from "./RangeScreen";

const weapon = (id: string, cls: string): StartWeaponOption => ({ id, name_zh: id, weapon_class: cls, traits_zh: [], hp: 30, mana: 10 });

const RANGE: RangeView = {
  seed: 7,
  stage: "pick_class",
  weapon_class: null,
  recommended_keywords: [],
  racks: [
    { weapon_class: "melee", name_zh: "近戰", skills: [], starter_weapon: "one_handed_sword", starter_weapon_zh: "單手劍" },
    { weapon_class: "ranged", name_zh: "遠程", skills: [], starter_weapon: "bow", starter_weapon_zh: "弓" },
    { weapon_class: "focus", name_zh: "法器", skills: [], starter_weapon: "fire_staff", starter_weapon_zh: "火焰法杖" },
  ],
  dummies: [{ label_zh: "會動的木樁" }, { label_zh: "站在水上的木樁" }, { label_zh: "普通的木樁" }],
  intro: [{ speaker_zh: "守印人", text_zh: "這裡是工坊靶場。" }],
  done: [{ speaker_zh: "守印人", text_zh: "去霧渡鎮找渡婆婆。" }],
};

function memoryStorage(): Storage {
  const map = new Map<string, string>();
  return {
    get length() {
      return map.size;
    },
    clear: () => map.clear(),
    getItem: (k) => map.get(k) ?? null,
    key: (i) => [...map.keys()][i] ?? null,
    removeItem: (k) => void map.delete(k),
    setItem: (k, v) => void map.set(k, v),
  };
}

afterEach(() => vi.unstubAllGlobals());

describe("TR-1 靶場的畫面邏輯", () => {
  it("武器架照伺服器的大類順序分組（近戰、遠程、法器）", () => {
    const racks = groupRacks([weapon("bow", "ranged"), weapon("dagger", "melee"), weapon("fire_staff", "focus"), weapon("axe", "melee")], ["melee", "ranged", "focus"]);
    expect(racks.map((r) => r.name)).toEqual(["近戰", "遠程", "法器"]);
    expect(racks[0]?.weapons.map((w) => w.id)).toEqual(["dagger", "axe"]);
    expect(CLASS_LABELS.focus).toBe("法器");
  });

  it("看示範：已選的看那組；沒選的接在後面；選滿了換掉第 2 個", () => {
    expect(demoKeywords([], "burning", 2)).toEqual(["burning"]);
    expect(demoKeywords(["burning"], "charged", 2)).toEqual(["burning", "charged"]);
    expect(demoKeywords(["burning", "charged"], "charged", 2)).toEqual(["burning", "charged"]);
    expect(demoKeywords(["burning", "charged"], "frozen", 2)).toEqual(["burning", "frozen"]);
  });

  it("草稿存在本機（中途離開回來接著選）；讀不到或壞掉時 null", () => {
    vi.stubGlobal("window", { localStorage: memoryStorage() });
    expect(readDraft("c1")).toBeNull();
    writeDraft("c1", { weapon: "bow", keywords: ["burning"] });
    expect(readDraft("c1")).toEqual({ weapon: "bow", keywords: ["burning"] });
    writeDraft("c1", null);
    expect(readDraft("c1")).toBeNull();
    window.localStorage.setItem("trpg.rangeDraft.c2", "{oops");
    expect(readDraft("c2")).toBeNull();
    vi.stubGlobal("window", {});
    expect(readDraft("c1")).toBeNull(); // 沒有 localStorage（封鎖儲存）也不壞
    expect(() => writeDraft("c1", { weapon: "bow", keywords: [] })).not.toThrow();
  });

  it("內容檔有靶場：三大類各 2 招示範招、3 個木樁、守印人的話", () => {
    const data = parse(newcomerYaml) as { range: { racks: string[]; demos: Record<string, string[]>; dummies: unknown[]; intro: unknown[]; done: unknown[] } };
    expect(data.range.racks).toEqual(["melee", "ranged", "focus"]);
    for (const cls of data.range.racks) expect(data.range.demos[cls]).toHaveLength(2);
    expect(data.range.dummies).toHaveLength(3);
    expect(data.range.intro.length).toBeGreaterThan(0);
    expect(data.range.done.length).toBeGreaterThan(0);
  });

  it("靶場畫面：守印人的話、沙盒說明、確定出發（還沒選完時不能按）", () => {
    const view = { character: { character_id: "c1", name: "小靶", race: "human", look: null } } as unknown as WorldView;
    const html = renderToStaticMarkup(
      createElement(RangeScreen, { view, range: RANGE, busy: false, error: null, onCloseError: () => undefined, onTrial: () => undefined, onConfirm: () => undefined, onHome: () => undefined }),
    );
    expect(html).toContain("工坊靶場");
    expect(html).toContain("這裡是工坊靶場。");
    expect(html).toContain("不算勝負、不給經驗與掉落、不耗 HP 與法力");
    expect(html).toContain("會動的木樁、站在水上的木樁、普通的木樁");
    expect(html).toMatch(new RegExp(`data-testid="range-confirm"[^>]*>${CONFIRM_LABEL}`));
    expect(html).toMatch(/disabled=""[^>]*data-testid="range-confirm"/);
    expect(html).toContain("先離開（下次回到靶場）");
  });

  it("確定出發之後：守印人指示去霧渡鎮（共用彈窗外框）", () => {
    const html = renderToStaticMarkup(createElement(RangeDoneDialog, { lines: rangeDoneLines(RANGE), onClose: () => undefined }));
    expect(html).toContain("去霧渡鎮找渡婆婆。");
    expect(html).toContain("出發");
    expect(rangeDoneLines(null)).toEqual([]);
  });

  it("接線：建角不送武器；未完成開局畫靶場；試打不回寫、結束回到靶場", () => {
    const pick = readFile(SRC_DIR, "world/WorldCharacterPicker.tsx");
    expect(pick).not.toMatch(/weapon: picker/);
    const screen = readFile(SRC_DIR, "screens/WorldScreen.tsx");
    expect(screen).toMatch(/view\.opening != null && !shouldShowOpening/);
    expect(screen).toContain('"回到靶場"');
    expect(screen).toContain("api.worldRangeTrial");
    expect(screen).toContain('kind: "opening_confirm"');
  });
});
