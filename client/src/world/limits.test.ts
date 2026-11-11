// OB-5（#150 第 7、9 點）入門期的限制提示：原因由伺服器給（`WorldView.limits`），面板只負責顯示；
// 正式選定後的配點教學照 OB-3 的約定記紀錄；三選一換一組時清掉上一組的選擇。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { WorldLesson, WorldView } from "../api/types";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { LimitNote, limitOf } from "./limits";
import { allocateSeenIds, allocateTotalText, lessonShown } from "./OpeningDialog";
import { OFFER_WAIT } from "./QuestLog";

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
    const html = renderToStaticMarkup(createElement(LimitNote, { reason: "入門期的打造、強化、附魔只限防具" }));
    expect(html).toContain('data-testid="world-limit-note"');
    expect(html).toContain("入門期的打造、強化、附魔只限防具");
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
    expect(src).toMatch(/useEffect\(\(\) => \{\s*setPick\(null\);\s*setReplace\(null\);\s*\}, \[groupKey\]\);/);
    expect(src).toContain('data-testid="world-offer-wait"');
    expect(OFFER_WAIT).toContain("稍等一下");
  });
});
