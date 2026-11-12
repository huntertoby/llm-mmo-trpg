// PB-1c：選部位小選單與角色卡部位列（規格 docs/phases/PhasePB-1計畫.md 第 7 節第 3、4、8 點；美術移植需求 2.1～2.2、3.1）。
// 排序（本體第一、之後照部位 ID）、灰掉原因、破掉打叉、看不到資訊時不寫數字、`aria-expanded`。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { PartOption, PartView, UnitView } from "../api/types";
import { breakLine, moveSelection, partBarState, partMenuRows, partMenuSubtitle, pickedPart } from "../battle/partMenu";
import { unit } from "../battle/testFixtures";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { PartMenu, withTargetPart } from "./PartMenu";
import { UnitParts } from "./UnitInfo";

const part = (id: string, over: Partial<PartView> = {}): PartView => ({
  id,
  name_zh: { whisk: "拂塵", dantian: "氣海", sword: "長劍" }[id] ?? id,
  hp: 26,
  max_hp: 26,
  broken: false,
  exposed: true,
  reach: id === "dantian" ? "behind" : "any",
  break_lines_zh: [`${id} 破掉的效果`],
  ...over,
});
const boss = (parts: PartView[], over: Partial<UnitView> = {}): UnitView =>
  unit("unit_0002", "enemy", 3, 3, { name_zh: "霧鎖真人", hp: 90, max_hp: 132, parts, boss_phase: { index: 2, total: 3, name_zh: "鎖霧" }, ...over });
const OPTIONS: PartOption[] = [
  { part_id: "dantian", name_zh: "氣海", ok: false, reason_zh: "要從背後近戰才打得到" },
  { part_id: "sword", name_zh: "長劍", ok: false, reason_zh: "這個階段還沒露出" },
  { part_id: "whisk", name_zh: "拂塵", ok: true, reason_zh: null },
];
const PARTS = [part("dantian"), part("sword", { exposed: false }), part("whisk", { hp: 12 })];

describe("選單的列（battle/partMenu.ts）", () => {
  it("本體第一、預設選中；之後照伺服器的部位 ID 順序", () => {
    const rows = partMenuRows(boss(PARTS), OPTIONS);
    expect(rows.map((r) => r.id)).toEqual(["body", "dantian", "sword", "whisk"]);
    expect(rows[0]).toMatchObject({ name: "本體", ok: true, bar: { kind: "body", hp: 90, max: 132 } });
    expect(pickedPart(rows[0])).toBeNull(); // 預設（Enter）＝本體
  });

  it("打不到的灰掉並寫原因；「從背後」的原因前面加背刺小圖", () => {
    const rows = partMenuRows(boss(PARTS), OPTIONS);
    const by = Object.fromEntries(rows.map((r) => [r.id, r]));
    expect(by["dantian"]).toMatchObject({ ok: false, reason: "要從背後近戰才打得到", back: true });
    expect(by["sword"]).toMatchObject({ ok: false, reason: "這個階段還沒露出", back: false, bar: { kind: "hidden" } });
    expect(by["whisk"]).toMatchObject({ ok: true, reason: null, bar: { kind: "ok", hp: 12, max: 26 } });
    expect(pickedPart(by["dantian"])).toBeUndefined(); // 打不到的不送出
    expect(pickedPart(by["whisk"])).toBe("whisk");
  });

  it("已破壞：打叉、不能選、「已破：……」", () => {
    const rows = partMenuRows(boss([part("whisk", { hp: 0, broken: true })]), [{ part_id: "whisk", name_zh: "拂塵", ok: false, reason_zh: "已經破了" }]);
    expect(rows[1]).toMatchObject({ broken: true, ok: false, bar: { kind: "broken" }, back: false });
    expect(breakLine(rows[1]!)).toBe("已破：whisk 破掉的效果");
    expect(breakLine(rows[0]!)).toBeNull();
  });

  it("看不到資訊（hp、max_hp 為 null）時部位條一律畫「未露出」、本體不寫數字", () => {
    const hidden = boss([part("whisk", { hp: null, max_hp: null })], { hp: null, hidden_info: true });
    const rows = partMenuRows(hidden, [OPTIONS[2]!]);
    expect(rows[0]!.bar).toEqual({ kind: "body", hp: null, max: 132 });
    expect(rows[1]!.bar).toEqual({ kind: "hidden" });
    expect(partBarState(part("whisk", { hp: null, max_hp: null }))).toEqual({ kind: "hidden" });
  });

  it("方向鍵上下循環；標題寫階段", () => {
    expect(moveSelection(4, 0, 1)).toBe(1);
    expect(moveSelection(4, 3, 1)).toBe(0);
    expect(moveSelection(4, 0, -1)).toBe(3);
    expect(partMenuSubtitle(boss(PARTS))).toBe("選部位・鎖霧");
  });

  it("選了部位就在動作上加 target_part；本體原樣", () => {
    const a = { type: "attack", unit_id: "unit_0001", target_id: "unit_0002" } as const;
    expect(withTargetPart(a, "whisk")).toEqual({ ...a, target_part: "whisk" });
    expect(withTargetPart(a, null)).toBe(a);
  });
});

describe("PartMenu 的輸出", () => {
  const html = renderToStaticMarkup(
    createElement(PartMenu, {
      menu: { targetId: "unit_0002", tile: { x: 3, y: 3 }, action: { type: "attack", unit_id: "unit_0001", target_id: "unit_0002" }, options: [OPTIONS[0]!, OPTIONS[1]!, { part_id: "whisk", name_zh: "拂塵", ok: false, reason_zh: "已經破了" }], submit: false, dismissPin: false },
      boss: boss([part("dantian"), part("sword", { exposed: false }), part("whisk", { hp: 0, broken: true })]),
      model: { width: 8, height: 8, tiles: [] } as never,
      scale: 1,
      boardRef: { current: null },
      onPick: () => undefined,
      onClose: () => undefined,
      onPreview: () => undefined,
    }),
  );

  it("共用外框、role=menu、列的順序", () => {
    expect(html).toContain("popup-menu part-menu");
    expect(html).toContain("ui-popup");
    expect(html).toContain('role="menu"');
    const order = [...html.matchAll(/data-testid="part-menu-row-(\w+)"/g)].map((m) => m[1]);
    expect(order).toEqual(["body", "dantian", "sword", "whisk"]);
  });

  it("本體預設選中；打不到的列 aria-disabled、寫原因", () => {
    expect(html).toMatch(/aria-selected="true"[^>]*data-part="body"/);
    expect(html).toMatch(/aria-disabled="true"[^>]*data-part="dantian"/);
    expect(html).toContain("要從背後近戰才打得到");
    expect(html).toContain("這個階段還沒露出");
  });

  it("已破壞的列寫「已破壞」", () => {
    expect(html).toMatch(/class="part-menu-row off broken"/);
    expect(html).toContain("已破壞");
  });
});

describe("角色卡部位列（UnitInfo）", () => {
  it("每個部位一列：完好畫米白條＋數字、破掉打叉、未露出不寫數字", () => {
    const html = renderToStaticMarkup(createElement(UnitParts, { unit: boss([part("dantian"), part("sword", { exposed: false }), part("whisk", { hp: 0, broken: true })]) }));
    expect(html).toContain('data-testid="unit-parts"');
    expect(html).toMatch(/data-part="dantian" data-state="ok"/);
    expect(html).toContain("26/26");
    expect(html).toMatch(/data-part="whisk" data-state="broken"/);
    expect(html).toContain("part-bar-x");
    expect(html).toMatch(/data-part="sword" data-state="hidden"/);
    expect(html).toContain("未露出");
  });

  it("看不到資訊時不寫任何部位數字", () => {
    const html = renderToStaticMarkup(createElement(UnitParts, { unit: boss([part("whisk", { hp: null, max_hp: null })], { hp: null, hidden_info: true }) }));
    expect(html).not.toMatch(/\d+\/\d+/);
    expect(html).toMatch(/data-state="hidden"/);
  });

  it("沒有部位不畫", () => {
    expect(renderToStaticMarkup(createElement(UnitParts, { unit: unit("unit_0003", "enemy", 1, 1) }))).toBe("");
  });

  it("CSS：條米白 #f2e6c8、已破壞暗紅底、紅「×」#ff5a4a、未露出幾乎黑、空槽灰紫（移植需求 2.2）", () => {
    const css = readFile(SRC_DIR, "styles/float-card.css");
    expect(css).toMatch(/\.part-bar-fill \{[^}]*background: #f2e6c8/);
    expect(css).toMatch(/\.part-bar \{[^}]*background: #4a4252/);
    expect(css).toMatch(/\.part-bar\.broken \{[^}]*background: #5a1a1a/);
    expect(css).toMatch(/\.part-bar\.hidden \{[^}]*background: #0e0e14/);
    expect(readFile(SRC_DIR, "ui/PartBar.tsx")).toContain('stroke="#ff5a4a"');
  });
});

describe("aria-expanded 標在觸發元素（戰場）上", () => {
  it("BattleCanvas 收 menuOpen 標 aria-expanded；BattleScreen 傳選單開著沒", () => {
    expect(readFile(SRC_DIR, "ui/BattleCanvas.tsx")).toMatch(/aria-expanded=\{menuOpen\}/);
    expect(readFile(SRC_DIR, "screens/BattleScreen.tsx")).toMatch(/menuOpen=\{/);
  });
});
