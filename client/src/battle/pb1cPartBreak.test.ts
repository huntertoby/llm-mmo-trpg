// PB-1c：頭目部位破壞的占位演出（T16；規格第 7 節第 6 點）——該頭目一次重擊白閃（那一下的受擊升級成重擊片段）＋微震
// （重擊參數）＋浮動字「{部位} 破！」。不新增貼圖、不動 `render/battle/unitLayer.ts`。紀錄：`part_broken` 是醒目的一類（第 7 點）。
import { describe, expect, it } from "vitest";
import type { BattleView, Pos, SkillCard } from "../api/types";
import { feedbackFor, partBrokenWord } from "./feedback";
import { SHAKE_SPEC, shakesFor, withImpact } from "./impact";
import { logLines } from "./log";
import { groupLog } from "./logGroups";
import { unitNames } from "./units";
import { PART_BREAK_STOP_MS, specialsFor, withSpecials } from "./specials";
import { vfxFor } from "./vfx";
import { readFile, SRC_DIR } from "../test/sourceScan";

const HERO = "u_hero";
const BOSS = "u_boss";
const at = (x: number, y: number): Pos => ({ x, y });
const view = {
  map_id: "m1",
  team: "ally",
  round: 1,
  units: [
    { id: HERO, pos: at(2, 2), team: "ally", max_hp: 40, hp: 40, downed: false, tags: [], statuses: [] },
    { id: BOSS, pos: at(3, 2), team: "enemy", max_hp: 132, hp: 100, downed: false, tags: ["boss"], statuses: [] },
  ],
  tiles: [],
} as unknown as BattleView;
const cards = { sk: { id: "sk", shape: "單體", skeleton: "strike", effect_ids: ["damage"], icon: { segments: [{ skeleton: "strike", shape_id: "single", range: 1, effects: [{ type: "damage" }] }] } } as unknown as SkillCard };
const used = { seq: 1, round: 1, type: "skill_used", unit_id: HERO, skill_id: "sk", tiles: [at(3, 2)] };
const dmg = { seq: 2, round: 1, type: "damage_dealt", target_id: BOSS, source_id: HERO, element: "physical", amount: 5, hp_before: 100, hp_after: 95, crit: false };
const partDmg = { seq: 3, round: 1, type: "part_damaged", target_id: BOSS, part_id: "whisk", name_zh: "拂塵", amount: 5, hp_before: 5, hp_after: 0 };
const broke = { seq: 4, round: 1, type: "part_broken", target_id: BOSS, part_id: "whisk", name_zh: "拂塵", effects: ["seal_skill"], applied: true, text: "霧鎖真人的拂塵被打破了！" };
const events = [used, dmg, partDmg, broke];

describe("破壞演出（占位）", () => {
  it("浮動字「拂塵 破！」：放大、醒目，在頭目頭上", () => {
    const items = feedbackFor(events, view);
    const word = items.find((i) => i.kind === "float" && i.text === partBrokenWord("拂塵"));
    expect(word).toMatchObject({ kind: "float", text: "拂塵 破！", pos: at(3, 2), big: true, tone: "bad" });
  });

  it("特殊結果 part_break 在頭目受擊那一刻；停頓照重擊 70", () => {
    const vfx = vfxFor(events, view, cards);
    const s = specialsFor(vfx, events, view, view).filter((x) => x.kind === "part_break");
    const r = vfx.reactions?.find((x) => x.unitId === BOSS);
    expect(s).toEqual([{ kind: "part_break", pos: at(3, 2), unitId: BOSS, atMs: r!.atMs, partId: "whisk" }]); // PB-1e：帶部位（演出畫在那個部位上）
    expect(PART_BREAK_STOP_MS).toBe(70);
  });

  it("重擊白閃：那一下頭目的受擊升級成重擊片段（沒有部位破壞時照舊是一般受擊）", () => {
    const plain = withSpecials(vfxFor([used, dmg], view, cards), [used, dmg], view, view);
    expect(plain.reactions?.find((x) => x.unitId === BOSS)?.kind).toBe("hit");
    const out = withSpecials(vfxFor(events, view, cards), events, view, view);
    expect(out.reactions?.find((x) => x.unitId === BOSS)?.kind).toBe("heavy");
    expect(out.stops?.some((x) => x.ms === 70)).toBe(true);
  });

  it("微震：在那一刻加一次重擊的微震（重擊參數），目標是頭目那一格；沒有部位破壞時沒有", () => {
    const vfx = withSpecials(vfxFor(events, view, cards), events, view, view);
    const shakes = shakesFor(vfx, events, "m1");
    const at0 = vfx.specials?.find((x) => x.kind === "part_break")?.atMs;
    expect(shakes).toContainEqual(expect.objectContaining({ kind: "heavy", atMs: at0, px: SHAKE_SPEC.heavy.px, ms: SHAKE_SPEC.heavy.ms, targets: [at(3, 2)] }));
    const plain = withImpact(withSpecials(vfxFor([used, dmg], view, cards), [used, dmg], view, view), [used, dmg], view, view, HERO);
    expect(plain.shakes ?? []).toEqual([]);
  });

  it("PB-1e 起正式演出接在 resultEffects 的 part_break（PB-1c「不動 unitLayer」的限制解除）", () => {
    expect(readFile(SRC_DIR, "render/resultEffects.ts")).toMatch(/case "part_break": \{[\s\S]*?partBreakEffect\(host, s, at, o\.scale\)/);
  });
});

describe("紀錄（第 7 點）", () => {
  it("logGroups 不吞掉部位事件；part_broken 是醒目的一類（紅叉＋粗體）", () => {
    const steps = [{ events: [{ ...used, text: "勇者 使用 技能" }, { ...dmg, text: "霧鎖真人 受到 5 點傷害" }, { ...partDmg, text: "拂塵 −5（剩 0）" }, broke] }];
    const lines = logLines(steps as never, unitNames(view));
    expect(lines.map((l) => [l.type, l.tone])).toEqual([
      ["skill_used", undefined],
      ["damage_dealt", "damage"],
      ["part_damaged", "damage"],
      ["part_broken", "break"],
    ]);
    const groups = groupLog(lines);
    const texts = JSON.stringify(groups);
    expect(texts).toContain("拂塵 −5（剩 0）");
    expect(texts).toContain("霧鎖真人的拂塵被打破了！");
    expect(readFile(SRC_DIR, "styles/battle-log.css")).toMatch(/\.tone-break \.log-mark \{\s*color: #ff5a4a/);
  });
});
