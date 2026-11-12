// Phase QI-2c：Q 版技能圖示前端接線（規格 docs/phases/PhaseQI-2計畫.md 第 7 節 T-C1～T-C5、T-C7；T-C6 在 qi2cStatusUnchanged.test.ts）。
// 資料一律用實際內容（skill_icons.json、glossary.json）。Q 版圖樣另建畫布，用 test/fakeCanvas.ts 的假畫布。
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import icons from "./fixtures/skill_icons.json";
import type { SkillIconData } from "../api/types";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { fakeCanvasFactory, fakeCtx, type FakeCanvasLog } from "../test/fakeCanvas";
import { ICON_RES, setQCanvasFactory } from "./qIcon/core";
import { clearQSkillDefs } from "./qIcon/skills";
import { clearQWeaponDefs, qResolve, qWeaponDef } from "./qIcon/weapons";
import * as QP from "./qIcon/parts";
import { toQParts, type SkillArt } from "./qIcon/partsAdapter";
import { resolveGear, onDevicePixel, pixelSnapNudge } from "./gearIcon";
import {
  cardGlyphCanvas,
  clearSkillIconCache,
  defaultIconLevel,
  effectGlyphTint,
  iconCacheKey,
  optionTile,
  paintSkillIcon,
  partsOf,
  SKILL_CARD_ICON_LEVEL,
  skillIconCanvas,
  surfaceTile,
  tileCanvas,
  type AssemblyTile,
} from "./skillIcon";

type Icon = SkillIconData & { art?: SkillArt | null };
const FIX = icons as unknown as { skills: Record<string, Icon>; random: Icon[]; workshop: Record<string, Icon[]> };
const IDS = Object.keys(FIX.skills).sort();
const ALL: Array<[string, Icon]> = [...IDS.map((id): [string, Icon] => [id, FIX.skills[id] as Icon]), ...FIX.random.map((i, n): [string, Icon] => [`random#${n}`, i]), ...Object.values(FIX.workshop).flat().map((i, n): [string, Icon] => [`workshop#${n}`, i])];

const log: FakeCanvasLog = { calls: null };
beforeAll(() => {
  clearQSkillDefs();
  clearQWeaponDefs();
  clearSkillIconCache();
  setQCanvasFactory(fakeCanvasFactory(log));
});
afterAll(() => {
  setQCanvasFactory(null);
  clearQSkillDefs();
  clearQWeaponDefs();
  clearSkillIconCache();
});

describe("T-C1 級別", () => {
  it("不填級別依邊長：≤40 main、其餘 full；技能卡 56／compact 48 都是 mid（D5）", () => {
    for (const s of [24, 28, 40]) expect(defaultIconLevel(s)).toBe("main");
    for (const s of [41, 48, 56, 96]) expect(defaultIconLevel(s)).toBe("full");
    expect(SKILL_CARD_ICON_LEVEL).toBe("mid");
    const card = readFile(SRC_DIR, "ui/SkillCardView.tsx");
    expect(card).toContain("<SkillIconView icon={card.icon} size={compact ? 48 : 56} level={SKILL_CARD_ICON_LEVEL}");
    expect(readFile(SRC_DIR, "ui/VariantList.tsx")).toMatch(/<SkillIconView icon=\{v\.icon\} size=\{28\} level="main"/);
  });

  it("沒有地方再傳舊的 small（level 取代 small）", () => {
    for (const f of ["ui/SkillCardView.tsx", "ui/VariantList.tsx", "ui/SkillBar.tsx", "ui/SkillTile.tsx", "ui/SummonPanel.tsx", "ui/workshop/CheckPanel.tsx", "run/LoadoutEditor.tsx", "world/PartyPanel.tsx", "world/RangeClassPick.tsx"]) {
      expect(readFile(SRC_DIR, f), f).not.toMatch(/<SkillIconView[^>]*\bsmall\b/);
    }
    expect(readFile(SRC_DIR, "ui/SkillIconView.tsx")).not.toMatch(/small\?: boolean/);
  });

  it("快取鍵含級別、內部解析度與 art 每一欄", () => {
    const a = FIX.skills["skill_fire_bolt"] as Icon;
    const keys = new Set([iconCacheKey(a, 56, "main"), iconCacheKey(a, 56, "mid"), iconCacheKey(a, 56, "full"), iconCacheKey(a, 56, "mid", 1)]);
    expect(keys.size).toBe(4);
    const art = a.art as SkillArt;
    for (const [k, v] of [["prop", "w:axe"], ["motion", "spin"], ["act", "push"], ["tint", "ice"], ["spark", "fire"]] as const) {
      expect(iconCacheKey({ ...a, art: { tint: null, spark: null, ...art, [k]: v } } as Icon, 56, "mid"), k).not.toBe(iconCacheKey(a, 56, "mid"));
    }
  });
});

// ---- T-C2：樣張 qIconsParts.js 427–436 行的 partsOf（只在測試檔）----
interface SampleItem { cat: string; id: string; seg: number }
const effKey = (e: { type: string; status?: string | null; surface?: string | null }): string => (e.type === "apply_status" && e.status ? "status:" + e.status : e.type === "create_surface" && e.surface ? "surface:" + e.surface : e.type);
function samplePartsOf(icon: Icon) {
  const kind = icon.kind || "active", segs = icon.segments ?? [], seen = new Set<string>();
  let list: SampleItem[] = [];
  segs.forEach((s, si) => { for (const e of s.effects ?? []) { const key = effKey(e); if (!seen.has(key)) { seen.add(key); list.push({ cat: "effect", id: key, seg: si }); } } });
  if (icon.modifier) list = icon.modifier.changes.map((ch) => ({ cat: "change", id: ch.key, seg: 0 }));
  const ci0 = list.findIndex((e) => e.id !== "damage"), core = list.length ? list[ci0 === -1 ? 0 : ci0] : null;
  if (core) list = [core, ...list.filter((e) => e !== core)];
  const row = list.slice(0, 4), cond = icon.condition ? { cat: "condition", id: icon.condition.id === "target_has_status" && icon.condition.status ? "target_has_status:" + icon.condition.status : icon.condition.id } : null;
  return { kind, rarity: icon.rarity, el: icon.elements?.[0] ?? null, skeleton: segs[0]?.skeleton ?? null, trigger: (kind === "reaction" || kind === "passive") && icon.trigger ? icon.trigger : null, link: icon.link ?? null, cond, costs: icon.costs ?? [], row, core, shape: segs.map((s) => s.shape_id) };
}

describe("T-C2 partsOf 和樣張相同", () => {
  it("402 招＋隨機 50＋工坊示範：核心、效果列（鍵、順序、段號）、條件、代價、觸發、接續、骨架都相同", () => {
    expect(ALL.length).toBeGreaterThan(452);
    for (const [id, icon] of ALL) {
      const ours = toQParts(icon, partsOf(icon));
      const s = samplePartsOf(icon);
      const strip = (r: { cat: string; id: string; seg: number } | null | undefined) => (r == null ? null : { cat: r.cat, id: r.id, seg: r.seg });
      expect(ours.row.map(strip), id).toEqual(s.row.map(strip));
      expect(strip(ours.core), id).toEqual(strip(s.core));
      expect(ours.cond, id).toEqual(s.cond);
      expect(ours.costs, id).toEqual(s.costs);
      expect(ours.trigger, id).toEqual(s.trigger);
      expect(ours.link, id).toEqual(s.link);
      expect(ours.skeleton, id).toEqual(s.skeleton);
      expect(ours.kind, id).toBe(s.kind);
      // 元素：草稿的中性（undefined）當成沒有元素（2b 報告待決 9），其餘相同
      expect(ours.el, id).toEqual(s.el);
    }
  });
});

// ---- T-C3：三處改動接上了 ----
const arcs = (calls: string[]): string[] => calls.filter((c) => c.startsWith("arc("));
const fullCalls = (icon: Icon): string[] => {
  const l: FakeCanvasLog = { calls: [] };
  paintSkillIcon(fakeCtx(l, 192, 192), icon, "full", 96, ICON_RES);
  return l.calls ?? [];
};
const has = (calls: string[], x: number, y: number, r: number): boolean => arcs(calls).some((c) => c.startsWith(`arc(${x.toFixed(3)},${y.toFixed(3)},${r.toFixed(3)},`));
const pick = (ok: (i: Icon) => boolean): Icon => {
  const id = IDS.find((x) => ok(FIX.skills[x] as Icon));
  if (id === undefined) throw new Error("no skill");
  return FIX.skills[id] as Icon;
};

describe("T-C3 三處改動（觸發左上、元素片讓位、接續進效果列、物理與沒有元素不畫元素片）", () => {
  it("被動、反應：觸發在 (15,15) 半徑 12.5；有元素時元素片讓到 (12,39) 半徑 8", () => {
    for (const kind of ["passive", "reaction"]) {
      const withEl = pick((i) => i.kind === kind && i.trigger != null && i.elements[0] !== undefined && i.elements[0] !== "physical");
      const c = fullCalls(withEl);
      expect(has(c, 15, 15, 12.5), kind).toBe(true);
      expect(has(c, 12, 39, 8), kind).toBe(true);
      expect(has(c, 15, 15, 11), kind).toBe(false);
    }
  });

  it("主動技有元素：元素片在 (15,15) 半徑 11；物理與沒有元素都沒有元素片", () => {
    const fire = pick((i) => i.kind === "active" && i.elements[0] === "fire" && i.costs.length === 0);
    expect(has(fullCalls(fire), 15, 15, 11)).toBe(true);
    const phys = pick((i) => i.kind === "active" && i.elements[0] === "physical");
    const none = pick((i) => i.kind === "active" && i.elements.length === 0);
    for (const i of [phys, none]) {
      const c = fullCalls(i);
      expect(has(c, 15, 15, 11)).toBe(false);
      expect(has(c, 12, 39, 8)).toBe(false);
    }
  });

  it("複合技：接續記號排進效果列（y 87、半徑 9 以內）且色環 #7fd8ff，不在斜切線中央 (50,50)", () => {
    const combo = pick((i) => i.link != null && i.segments.length > 1 && i.modifier == null);
    const c = fullCalls(combo);
    expect(c).toContain("strokeStyle=#7fd8ff");
    expect(arcs(c).some((a) => a.startsWith("arc(50.000,50.000,"))).toBe(false);
    // 接續圓片的 strokeStyle 前面一個 arc 在效果列（y＝87）
    const i = c.indexOf("strokeStyle=#7fd8ff");
    const lastArc = c.slice(0, i).reverse().find((x) => x.startsWith("arc(")) ?? "";
    expect(lastArc).toMatch(/^arc\([\d.]+,87\.000,/);
  });

  it("骨架徽章 (86,86) 半徑 11；mid 是 (83,83) 半徑 15", () => {
    const icon = FIX.skills["skill_fire_bolt"] as Icon;
    expect(has(fullCalls(icon), 86, 86, 11)).toBe(true);
    const l: FakeCanvasLog = { calls: [] };
    paintSkillIcon(fakeCtx(l, 112, 112), icon, "mid", 56, ICON_RES);
    expect(has(l.calls ?? [], 83, 83, 15)).toBe(true);
  });
});

describe("T-C4 畫布尺寸＝顯示 × ICON_RES", () => {
  it("技能圖示、組裝列方塊、卡片小圖的畫布寬高", () => {
    const icon = FIX.skills["skill_fire_bolt"] as Icon;
    for (const s of [24, 28, 40, 48, 56, 96]) {
      const cv = skillIconCanvas(icon, s);
      expect([cv.width, cv.height], String(s)).toEqual([s * ICON_RES, s * ICON_RES]);
    }
    const tile = optionTile("effects", "damage") as AssemblyTile;
    for (const px of [18, 20, 22, 26, 30]) expect(tileCanvas(tile, px).width).toBe(px * ICON_RES);
    for (const [id, px] of [["ap", 16], ["damage", 18], ["pin", 13]] as const) expect(cardGlyphCanvas(id, px).width).toBe(px * ICON_RES);
  });

  it("元件的畫布寬高用 iconCanvasPx（原始碼掃描）", () => {
    const view = readFile(SRC_DIR, "ui/SkillIconView.tsx");
    expect(view).toContain("width={iconCanvasPx(size)}");
    expect(view).toContain("width={iconCanvasPx(px)}");
    expect(view).not.toMatch(/width=\{(size|px) \* 2\}/);
    expect(readFile(SRC_DIR, "ui/SkillCardGlyphs.tsx")).toContain("const cv = iconCanvasPx(px);");
  });
});

describe("T-C5 圖釘", () => {
  it("PinGlyph 收 pinned（預設 true），三處呼叫傳實際狀態", () => {
    expect(readFile(SRC_DIR, "ui/SkillCardGlyphs.tsx")).toContain("export function PinGlyph({ pinned = true }: { pinned?: boolean })");
    expect(readFile(SRC_DIR, "ui/BattleLogDock.tsx")).toContain("<PinGlyph pinned={pinned} />");
    expect(readFile(SRC_DIR, "ui/UnitInfo.tsx")).toContain("<PinGlyph pinned={pinned} />");
    expect(readFile(SRC_DIR, "ui/SkillCardView.tsx")).toContain("<PinGlyph pinned={pin.pinned} />");
  });

  it("未釘畫 55% 不透明的灰鋼色、已釘是紅頭", () => {
    const draw = (pinned: boolean): string[] => {
      const l: FakeCanvasLog = { calls: [] };
      QP.CARD.pin!.d(fakeCtx(l), { small: true, tiny: true, owPx: 0, badge: false, u: 1 }, null, { pinned });
      return l.calls ?? [];
    };
    expect(draw(false)).toContain("globalAlpha=0.550");
    expect(draw(true)).not.toContain("globalAlpha=0.550");
    expect(draw(true).join(";")).toContain("#f05a48");
    expect(draw(false).join(";")).toContain("#b4bcc6");
  });

  it("傷害小圖的染色照現行 SVG 的元素色（物理或沒有元素 #e8eef4）；其他效果不染", () => {
    expect(effectGlyphTint("damage", null)).toEqual(["#e8eef4", "#ffffff"]);
    expect(effectGlyphTint("damage", "physical")).toEqual(["#e8eef4", "#ffffff"]);
    expect(effectGlyphTint("damage", "fire")?.[0]).not.toBe("#e8eef4");
    expect(effectGlyphTint("heal", "fire")).toBeNull();
  });
});

// ---- T-C7：表面與工坊選項走 Q 版 ----
/** 一塊方塊畫在假 ctx 上的呼叫紀錄（含另建畫布的全域紀錄）。 */
function tileLog(draw: (ctx: CanvasRenderingContext2D) => void): string {
  const l: FakeCanvasLog = { calls: [] };
  log.calls = l.calls;
  draw(fakeCtx(l));
  log.calls = null;
  return (l.calls ?? []).join(";");
}
const chipLog = (cat: string, id: string, r: number, ring: string): string => tileLog((c) => QP.chip(c, cat, id, 50, 50, r, { ring, unitPx: 0.3, res: 2 }));
const FAINT = "rgba(255,255,255,0.3)";

describe("T-C7 表面與工坊選項換 Q 版", () => {
  it("8 種表面畫的是 Q 版圓片（油是 oilPool），和 QP.chip 呼叫紀錄相同", () => {
    expect(Object.keys(QP.SURFACE).sort()).toHaveLength(8);
    for (const id of Object.keys(QP.SURFACE)) {
      clearQSkillDefs();
      const a = tileLog((c) => surfaceTile(id).draw(c, 0.3, 2));
      clearQSkillDefs();
      expect(a, id).toBe(chipLog("surface", id, 42, FAINT));
      expect(a, id).toContain("drawImage(");
    }
    expect(QP.SURFACE["oil"]?.topic ?? "").toContain("琥珀");
  });

  it("工坊選項 status／surface／element／shape／skeleton／effects／condition／event 都畫 Q 版", () => {
    const cases: Array<[string, string, string, string]> = [
      ["status", "burning", "status", "burning"],
      ["status", "armor_broken", "status", "armor_broken"],
      ["element", "ice", "element", "ice"],
      ["shape", "cone", "shape", "cone"],
      ["effects", "damage", "effect", "damage"],
      ["condition", "flanked", "condition", "flanked"],
      ["event", "on_kill", "trigger", "on_kill"],
    ];
    for (const [field, value, cat, id] of cases) {
      const tile = optionTile(field, value) as AssemblyTile;
      clearQSkillDefs();
      const a = tileLog((c) => tile.draw(c, 0.3, 2));
      clearQSkillDefs();
      expect(a, `${field}:${value}`).toBe(chipLog(cat, id, 46, FAINT));
    }
    // 骨架：深色圓底 r40、沒有色環、圖樣 62（同 QP.chipCanvas("skeleton")）
    const sk = tileLog((c) => (optionTile("skeleton", "strike") as AssemblyTile).draw(c, 0.3, 2));
    expect(sk).toContain("fillStyle=#14161c");
    expect(sk).toContain("drawImage(");
    clearQSkillDefs();
    const want = tileLog((c) => {
      c.fillStyle = "#14161c";
      c.beginPath();
      c.arc(50, 50, 40, 0, Math.PI * 2);
      c.fill();
      QP.paint(c, "skeleton", "strike", 50, 50, 62, 0.3, 2);
    });
    clearQSkillDefs();
    expect(tileLog((c) => (optionTile("skeleton", "strike") as AssemblyTile).draw(c, 0.3, 2))).toBe(want);
    // 表面選項＝surfaceTile
    expect(tileLog((c) => (optionTile("surface", "oil") as AssemblyTile).draw(c, 0.3, 2))).toBe(tileLog((c) => surfaceTile("oil").draw(c, 0.3, 2)));
  });

  it("32 種以外的狀態（例：armor_broken）經 hooks.status 畫現行圖樣；不認得的值照舊回 null 或「?」", () => {
    expect(QP.STATUS["armor_broken"]).toBeUndefined();
    expect(QP.hooks.status).not.toBeNull();
    expect(QP.entry("status", "armor_broken").live).toBe(true);
    expect(optionTile("name_zh", "震地重擊")).toBeNull();
    expect(optionTile("shape", 3)).toBeNull();
    expect(optionTile("cost.mana", "x")).toBeNull();
    expect(optionTile("condition", "")).toBeNull();
    expect(QP.entry("effect", "totally_unknown").unknown).toBe(true);
    expect(QP.entry("surface", "jelly").unknown).toBe(true);
  });
});

describe("QI-2c 追加：技能主圖的錘照樣張暗柄、裝備圖示仍是亮柄", () => {
  it("qWeaponDef(r) 預設亮柄 #a06a36；qWeaponDef(r, false) 是 M.shaft #6a4420", () => {
    for (const form of ["warhammer", "mace"]) {
      const r = qResolve(resolveGear({ kind: "hammer", form }));
      const draw = (icon: boolean): string => {
        const l: FakeCanvasLog = { calls: [] };
        qWeaponDef(r, icon)?.d(fakeCtx(l), { small: false, tiny: false, owPx: 0, badge: false, u: 1 });
        return (l.calls ?? []).join(";");
      };
      expect(draw(true), form).toContain("fillStyle=#a06a36");
      expect(draw(false), form).not.toContain("fillStyle=#a06a36");
      expect(draw(false), form).toContain("fillStyle=#6a4420");
    }
  });
});

describe("QI-2c 追加：身上裝備格對齊裝置像素", () => {
  it("pixelSnapNudge 把左上角挪到 round(x × dpr) / dpr", () => {
    for (const [x, dpr] of [[10.25, 1], [10.5, 1], [7.3, 2], [33.37, 1.25], [12, 1.5]] as const) {
      const n = pixelSnapNudge(x, dpr);
      expect(Math.abs(n)).toBeLessThanOrEqual(0.5 / dpr + 1e-9);
      expect(onDevicePixel(x + n, dpr), `${x}@${dpr}`).toBe(true);
    }
    expect(pixelSnapNudge(12, 1)).toBe(0);
    expect(onDevicePixel(10.25, 1)).toBe(false);
    expect(onDevicePixel(10.5, 2)).toBe(true);
  });
});
