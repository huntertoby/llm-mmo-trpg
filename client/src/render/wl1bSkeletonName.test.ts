// WL-1 b 第 1 項：骨架名稱改從資料讀（`/api/glossary` 的 `skeletons`＝`content/skeletons/*.yaml` 的 `name_zh`）；
// 前端的 `SKELETON_NAME` 只用來覆寫；兩邊都找不到時顯示「未知骨架」，玩家畫面不出現英文 id。
import { afterEach, describe, expect, it } from "vitest";
import type { Glossary, SkillIconData } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGlossary, skeletonName, UNKNOWN_SKELETON_NAME } from "../battle/glossary";
import { SKELETON_NAME } from "./skillGlyphs";
import { assemblyFormula } from "./skillIcon";

const real = glossary as unknown as Glossary;
afterEach(() => setGlossary(real));

/** WL-1 b 以前組裝列骨架格顯示的字（`SKELETON_NAME[id]`），逐字凍結；鍵照骨架的 `order`。 */
const BEFORE: Readonly<Record<string, string>> = {
  strike: "打擊",
  area: "範圍",
  control: "控制",
  displace: "位移",
  builder_finisher: "累積終結",
  combo: "連段",
  trap: "陷阱",
  aura: "增益",
  summon: "召喚",
  reaction: "反應",
  stance: "姿態",
  passive: "被動",
  modifier: "改造",
  consume_status: "引爆狀態",
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
    expect(real.skeletons?.map((e) => e.id)).toEqual(Object.keys(BEFORE));
    for (const e of real.skeletons ?? []) expect(e.name_zh, e.id).not.toBe("");
  });

  it("目前 16 種骨架顯示的字和 WL-1 b 以前逐字相同", () => {
    for (const [id, zh] of Object.entries(BEFORE)) {
      expect(skeletonName(id, SKELETON_NAME), id).toBe(zh);
      expect(tileLabel(id), id).toBe(zh);
    }
  });

  it("前端表沒有的骨架顯示名詞表的中文名", () => {
    setGlossary({ ...real, skeletons: [...(real.skeletons ?? []), entry("brand_new_skeleton", "新骨架")] } as unknown as Glossary);
    expect(tileLabel("brand_new_skeleton")).toBe("新骨架");
  });

  it("前端表優先於名詞表（只用來覆寫）", () => {
    expect(real.skeletons?.find((e) => e.id === "aura")?.name_zh).not.toBe(SKELETON_NAME["aura"]);
    expect(tileLabel("aura")).toBe(SKELETON_NAME["aura"]);
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
    expect(skeletonName("strike", SKELETON_NAME)).toBe("打擊");
    expect(skeletonName("brand_new_skeleton", SKELETON_NAME)).toBe(UNKNOWN_SKELETON_NAME);
  });

  it("原型鏈上的名字（toString、constructor）不會被當成覆寫", () => {
    expect(skeletonName("toString", SKELETON_NAME)).toBe(UNKNOWN_SKELETON_NAME);
    expect(skeletonName("constructor", SKELETON_NAME)).toBe(UNKNOWN_SKELETON_NAME);
  });
});
