// WL-1 b 第 1 項：骨架名稱改從資料讀（`/api/glossary` 的 `skeletons`＝`content/skeletons/*.yaml` 的 `name_zh`）；
// WL-1 c（玩法 PM 2026-11-22 第 1 題選 B）：前端的覆寫表整張拿掉，畫面的字就是資料的字；找不到時顯示「未知骨架」，玩家畫面不出現英文 id。
import { afterEach, describe, expect, it } from "vitest";
import type { Glossary, SkillIconData } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGlossary, skeletonName, UNKNOWN_SKELETON_NAME } from "../battle/glossary";
import { assemblyFormula } from "./skillIcon";

const real = glossary as unknown as Glossary;
afterEach(() => setGlossary(real));

/** WL-1 c 起組裝列骨架格顯示的字（＝`content/skeletons/*.yaml` 的 `name_zh`），逐字凍結；鍵照骨架的 `order`。 */
const NAMES: Readonly<Record<string, string>> = {
  strike: "打擊",
  area: "範圍",
  control: "控場",
  displace: "位移",
  builder_finisher: "蓄力與終結",
  combo: "連段",
  trap: "陷阱",
  aura: "光環",
  summon: "召喚",
  reaction: "反應技",
  stance: "姿態",
  passive: "被動",
  modifier: "修正",
  consume_status: "消耗狀態",
  rune: "刻印",
  sacrifice: "獻祭",
};

const iconWith = (skeleton: string | null): SkillIconData =>
  ({
    kind: "active",
    rarity: "common",
    elements: [],
    weapon_req: "any",
    segments: [{ skeleton, shape_id: "single", range: 3, elements: [], effects: [{ type: "damage" }] }],
    link: null,
    condition: null,
    costs: [],
    cost_values: {},
    trigger: null,
    modifier: null,
    partial: false,
  }) as unknown as SkillIconData;

/** 組裝列骨架格的字。 */
const tileLabel = (skeleton: string | null): string | undefined => assemblyFormula(iconWith(skeleton)).rows[0]?.find((t) => t.cat === "骨架")?.label;

const entry = (id: string, name_zh: string) => ({ id, name_zh, description_zh: null, tags: [], rules_zh: [], rules_dice: [], status_look: null });

describe("WL-1 b：骨架名稱從資料讀", () => {
  it("名詞表帶了全部骨架（照 order），名稱都不是空的", () => {
    expect(real.skeletons?.map((e) => e.id)).toEqual(Object.keys(NAMES));
    for (const e of real.skeletons ?? []) expect(e.name_zh, e.id).not.toBe("");
  });

  it("16 種骨架顯示的字和資料的 name_zh 逐字相同", () => {
    for (const [id, zh] of Object.entries(NAMES)) {
      expect(real.skeletons?.find((e) => e.id === id)?.name_zh, id).toBe(zh);
      expect(skeletonName(id), id).toBe(zh);
      expect(tileLabel(id), id).toBe(zh);
    }
  });

  it("新骨架只寫資料就顯示名詞表的中文名", () => {
    setGlossary({ ...real, skeletons: [...(real.skeletons ?? []), entry("brand_new_skeleton", "新骨架")] } as unknown as Glossary);
    expect(tileLabel("brand_new_skeleton")).toBe("新骨架");
  });

  it("aura 畫面是資料的「光環」，不再是前端表的「增益」", () => {
    expect(tileLabel("aura")).toBe("光環");
  });

  it("override 參數仍可覆寫（目前沒有呼叫端傳）", () => {
    expect(skeletonName("aura", { aura: "增益" })).toBe("增益");
  });

  it("兩邊都找不到、空字串、null、undefined 都顯示「未知骨架」，不出現英文 id", () => {
    expect(tileLabel("brand_new_skeleton")).toBe(UNKNOWN_SKELETON_NAME);
    expect(tileLabel("")).toBe(UNKNOWN_SKELETON_NAME);
    expect(skeletonName(null)).toBe(UNKNOWN_SKELETON_NAME);
    expect(skeletonName(undefined)).toBe(UNKNOWN_SKELETON_NAME);
    expect(skeletonName("")).toBe(UNKNOWN_SKELETON_NAME);
    // 名詞表的名稱是空字串也退回
    setGlossary({ ...real, skeletons: [entry("blank", "")] } as unknown as Glossary);
    expect(skeletonName("blank")).toBe(UNKNOWN_SKELETON_NAME);
    // 名詞表沒有 skeletons 欄位（舊伺服器）也不壞
    const { skeletons: _drop, ...old } = real;
    setGlossary(old as Glossary);
    expect(skeletonName("strike")).toBe(UNKNOWN_SKELETON_NAME);
    expect(skeletonName("brand_new_skeleton")).toBe(UNKNOWN_SKELETON_NAME);
  });

  it("原型鏈上的名字（toString、constructor）不會被當成覆寫", () => {
    expect(skeletonName("toString", {})).toBe(UNKNOWN_SKELETON_NAME);
    expect(skeletonName("constructor", {})).toBe(UNKNOWN_SKELETON_NAME);
  });
});
