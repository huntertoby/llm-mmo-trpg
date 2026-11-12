// OB-5（#150 第 7、9 點）入門期的限制提示：原因由伺服器給（`WorldView.limits`），面板只負責顯示；
// 正式選定後的配點教學照 OB-3 的約定記紀錄；三選一換一組時清掉上一組的選擇。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { WorldCrafting, WorldLesson, WorldView } from "../api/types";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { LimitNote, limitOf } from "./limits";
import { ALLOCATE_ATTRS_NOTE_ZH, AllocateLessonDialog, allocateSeenIds, allocateTotalText, lessonShown } from "./OpeningDialog";
import { OFFER_WAIT, scrollToTop } from "./QuestLog";
import { ARMOR_SLOT_TYPES, initialDraft } from "./crafting";
import { wornTipLines } from "./BagScreen";

const lesson = (over: Partial<WorldLesson>): WorldLesson => ({ kind: "allocate", lines: [], ...over }) as WorldLesson;

describe("入門期的限制提示", () => {
  it("原因照伺服器給的字；沒有＝開放", () => {
    const view = { limits: { flash: "到 4 級才能閃現", loadout: "入門期不能換技能" } } as unknown as WorldView;
    expect(limitOf(view, "flash")).toBe("到 4 級才能閃現");
    expect(limitOf(view, "hire")).toBeNull();
    expect(limitOf({ limits: {} }, "flash")).toBeNull();
    expect(limitOf(null, "flash")).toBeNull();
  });

  it("面板上緣的一行說明；沒有原因就不畫", () => {
    expect(renderToStaticMarkup(createElement(LimitNote, { reason: null }))).toBe("");
    const html = renderToStaticMarkup(createElement(LimitNote, { reason: "入門期的打造、強化、重骰、指定詞條只限防具" }));
    expect(html).toContain('data-testid="world-limit-note"');
    expect(html).toContain("入門期的打造、強化、重骰、指定詞條只限防具");
  });

  it("前端不自己寫限制的原因：成長、換技能、鐵匠面板都讀 view.limits", () => {
    expect(readFile(SRC_DIR, "world/WorldGrowth.tsx")).toMatch(/limitOf\(view, "flash"\)[\s\S]*limitOf\(view, "dissolve"\)[\s\S]*limitOf\(view, "oath"\)/);
    expect(readFile(SRC_DIR, "world/HudPanels.tsx")).toContain('limitOf(view, "loadout")');
    expect(readFile(SRC_DIR, "world/SmithyPanel.tsx")).toContain('limitOf(view, "smith")');
    for (const file of ["world/limits.tsx", "world/WorldGrowth.tsx", "world/HudPanels.tsx", "world/SmithyPanel.tsx"]) expect(readFile(SRC_DIR, file)).not.toMatch(/["'`>]入門期/);
  });
});

describe("正式選定後的配點教學（OB-3 的約定）", () => {
  it("共幾點那一句：正式選定後＝全部已照推薦配好；舊角色照舊", () => {
    expect(allocateTotalText({ points: 8, start_points: 0, respec: true })).toBe("你的 8 點已經全部照推薦配好；想自己分，就到成長面板按「重配」再分。");
    expect(allocateTotalText({ points: 2, start_points: 4, respec: false })).toBe("開局的 4 點已經照推薦配好，加上這次升級的 2 點，共 6 點。");
  });

  it("關掉時記的紀錄：略過與上完分開記；再提示出過就記", () => {
    expect(allocateSeenIds({ respec: false, reminder: false }, "skip")).toEqual(["lesson:allocate"]);
    expect(allocateSeenIds({ respec: true, reminder: false }, "skip")).toEqual(["lesson:allocate_skip"]);
    expect(allocateSeenIds({ respec: true, reminder: false }, "recommended")).toEqual(["lesson:allocate"]);
    expect(allocateSeenIds({ respec: true, reminder: false }, "self")).toEqual(["lesson:allocate"]);
    expect(allocateSeenIds({ respec: true, reminder: true }, "skip")).toEqual(["lesson:allocate_again"]);
    expect(allocateSeenIds({ respec: true, reminder: true }, "recommended")).toEqual(["lesson:allocate_again", "lesson:allocate"]);
  });

  it("要不要出：略過之後當下不再出；再提示有自己的紀錄；「選定」不走教學彈窗（開整頁）", () => {
    const none = new Set<string>();
    expect(lessonShown(null, none)).toBe(false);
    expect(lessonShown(lesson({ kind: "choose" }), none)).toBe(false);
    expect(lessonShown(lesson({ kind: "flash" }), none)).toBe(true);
    expect(lessonShown(lesson({ kind: "flash" }), new Set(["lesson:flash"]))).toBe(false);
    expect(lessonShown(lesson({ respec: true }), none)).toBe(true);
    expect(lessonShown(lesson({ respec: true }), new Set(["lesson:allocate_skip"]))).toBe(false);
    expect(lessonShown(lesson({ respec: true, reminder: true }), new Set(["lesson:allocate_skip"]))).toBe(true);
    expect(lessonShown(lesson({ respec: true, reminder: true }), new Set(["lesson:allocate_skip", "lesson:allocate_again"]))).toBe(false);
  });
});

describe("延後的三選一", () => {
  it("換一組時清掉上一組的選擇；送出後等伺服器有提示", () => {
    const src = readFile(SRC_DIR, "world/QuestLog.tsx");
    // OB-6（美術追蹤①）：同一個 effect 裡也捲回最上面
    expect(src).toMatch(/useEffect\(\(\) => \{\s*setPick\(null\);\s*setReplace\(null\);\s*scrollToTop\(top\.current\);\s*\}, \[groupKey\]\);/);
    expect(src).toContain('data-testid="world-offer-wait"');
    expect(OFFER_WAIT).toContain("稍等一下");
  });

  it("開啟（含換下一組）時把自己與外面捲動的容器都捲回最上面", () => {
    const outer = { scrollTop: 300, parentElement: null };
    const mid = { scrollTop: 0, parentElement: outer };
    const panel = { scrollTop: 40, parentElement: mid };
    expect(scrollToTop(panel)).toBe(2);
    expect([panel.scrollTop, mid.scrollTop, outer.scrollTop]).toEqual([0, 0, 0]);
    expect(scrollToTop(null)).toBe(0);
  });
});

describe("OB-6 字串收尾與美術追蹤", () => {
  const slot = (slot_type: string) => ({ slot_type, name_zh: slot_type, grade_amount: 1, affixes: [{ id: `a_${slot_type}`, name_zh: "詞條" }] });
  const crafting = { slots: [slot("weapon"), slot("offhand"), slot("head"), slot("body")], rarities: [{ rarity: "rare", name_zh: "稀有" }], materials: [] } as unknown as WorldCrafting;

  it("鐵匠：入門期（伺服器限制資料有 smith）部位預設第一個防具；其他時候照舊", () => {
    expect(initialDraft(crafting).slot).toBe("weapon");
    expect(initialDraft(crafting, true).slot).toBe("head");
    expect(ARMOR_SLOT_TYPES).toContain(initialDraft(crafting, true).slot);
    const src = readFile(SRC_DIR, "world/SmithyPanel.tsx");
    expect(src).toContain('armorOnly={limitOf(view, "smith") !== null}');
  });

  it("穿戴中的卡：伺服器給的入門武器／起始武器那一行放最前面", () => {
    const entry = { slot: "main_hand", slot_zh: "主手", item: null, opening_note_zh: "入門配備是借的，正式選定時會換成你自己的。不能賣、寄、分解。" };
    expect(wornTipLines(entry as never)).toEqual([{ text: entry.opening_note_zh, note: null }]);
    expect(wornTipLines({ ...entry, opening_note_zh: null } as never)).toEqual([]);
  });

  it("選定後的配點教學（不列六顆屬性）補一句屬性在哪裡看", () => {
    expect(ALLOCATE_ATTRS_NOTE_ZH).toBe("每顆屬性管什麼，成長面板上都有寫。");
    const lesson = { kind: "allocate", lines: [], points: 8, respec: true, notes: [] } as unknown as WorldLesson;
    const html = renderToStaticMarkup(createElement(AllocateLessonDialog, { lesson, affects: [], onRecommended: () => undefined, onSelf: () => undefined, onSkip: () => undefined }));
    expect(html).toContain(ALLOCATE_ATTRS_NOTE_ZH);
  });

  it("成長面板第一行：入門期在服務說明後面接伺服器給的那一句", () => {
    expect(readFile(SRC_DIR, "world/WorldGrowth.tsx")).toContain("{view.growth.starter_note_zh ?? \"\"}");
  });
});
