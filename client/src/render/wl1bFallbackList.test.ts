// WL-1 b 第 3 項：美術的待畫清單＝目前走到退回畫法的 id（狀態、骨架、部件），存成快照 `__snapshots__/wl1bFallbackList.json`。
// 新內容進來、走到退回畫法時快照會變，美術就知道要補哪幾個圖；補了圖之後重產快照（`pnpm -C client exec vitest run src/render/wl1bFallbackList.test.ts -u`）。
// - 狀態：名詞表（`content/statuses.yaml`）裡 `qIcon/status.ts` 的 `entry(id)` 找不到的 → `paintUnknown`（框＋名稱第一個字）。
// - 骨架：`content/skeletons/*.yaml` 裡 `qIcon/parts.ts` 的 `entry("skeleton", id)` 是 `unknown`（Q 版問號）的。
// - 部件：內容資料的每個 id 照遊戲端的路（`skillParts.ts` 的 effectPart／conditionPart／triggerPart → `q`）查 `entry(cat, id)`，
//   加上 `render/fixtures/skill_icons.json` 全部技能、隨機與工坊示範實際畫到的部件（`partsOf` → `toQParts`：接續、代價、修正內容、改造對象、形狀、元素）。
import { describe, expect, it } from "vitest";
import { parse } from "yaml";
import type { SkillIconData } from "../api/types";
import { listFiles, readFile, SRC_DIR } from "../test/sourceScan";
import fixture from "./fixtures/skill_icons.json";
import * as QP from "./qIcon/parts";
import { toQParts } from "./qIcon/partsAdapter";
import * as QT from "./qIcon/status";
import { partsOf } from "./skillIcon";
import { conditionPart, effectPart, triggerPart, type QPartRef } from "./skillParts";

const CONTENT_DIR = new URL("../../content/", SRC_DIR);
const ids = (file: string, key: string): string[] => ((parse(readFile(CONTENT_DIR, file)) as Record<string, { id: string }[] | undefined>)[key] ?? []).map((r) => r.id);

const data = fixture as unknown as { skills: Record<string, SkillIconData>; random: SkillIconData[]; workshop: Record<string, SkillIconData[]> };
const ICONS: SkillIconData[] = [...Object.values(data.skills), ...data.random, ...Object.values(data.workshop).flat()];

/** 類別 → 走到 Q 版問號的 id（排序、不重複）。 */
function fallbackParts(): Record<string, string[]> {
  const out = new Map<string, Set<string>>();
  const check = (cat: string, id: string | null | undefined): void => {
    if (id == null || id === "") return;
    if (cat === "status") return; // 狀態圓片經 hooks.status 畫 qIcon/status.ts；算在下面的狀態清單
    if (cat === "effect" && id.startsWith("status:")) return; // 附加狀態：同上
    if (QP.entry(cat, id).unknown !== true) return;
    let set = out.get(cat);
    if (set === undefined) out.set(cat, (set = new Set()));
    set.add(id);
  };
  const ref = (q: QPartRef | undefined): void => {
    if (q !== undefined) check(q.cat, q.id);
  };
  // 內容資料的每個 id
  for (const id of ids("skill_primitives.yaml", "primitives")) ref(effectPart({ type: id }).q);
  for (const id of ids("surfaces.yaml", "surfaces")) ref(effectPart({ type: "create_surface", surface: id }).q);
  for (const id of ids("skill_conditions.yaml", "conditions")) ref(conditionPart(id)?.q);
  for (const id of ids("skill_triggers.yaml", "triggers")) ref(triggerPart(id, false)?.q);
  for (const id of ids("reactions.yaml", "events")) ref(triggerPart(id, true)?.q);
  for (const id of ids("skill_shapes.yaml", "shapes")) check("shape", id);
  for (const id of ids("elements.yaml", "elements")) check("element", id);
  // 技能實際畫到的部件
  for (const icon of ICONS) {
    const parts = partsOf(icon);
    const P = toQParts(icon, parts);
    check("trigger", P.trigger);
    check("link", P.link);
    if (P.cond !== null) check(P.cond.cat, P.cond.id);
    for (const c of P.costs) check("cost", c);
    for (const r of P.row) check(r.cat, r.id);
    for (const s of P.shape) check("shape", s);
    if (P.el !== null) check("element", P.el);
    if (parts.mod !== null) ref(parts.mod.target.q);
    for (const seg of parts.segs) for (const e of seg.effects) ref(e.q);
  }
  return Object.fromEntries([...out.entries()].sort(([a], [b]) => (a < b ? -1 : 1)).map(([cat, set]) => [cat, [...set].sort()]));
}

function fallbackList(): { statuses: string[]; skeletons: string[]; parts: Record<string, string[]> } {
  const statuses = ids("statuses.yaml", "statuses")
    .filter((id) => QT.entry(id) === null)
    .sort();
  const skeletonIds = listFiles(new URL("skeletons/", CONTENT_DIR), (p) => /^\w+\.yaml$/.test(p)).map((f) => f.replace(/\.yaml$/, ""));
  const used = ICONS.flatMap((i) => i.segments.map((s) => s.skeleton)).filter((s): s is string => s != null && s !== "");
  const skeletons = [...new Set([...skeletonIds, ...used])].filter((id) => QP.entry("skeleton", id).unknown === true).sort();
  return { statuses, skeletons, parts: fallbackParts() };
}

describe("WL-1 b：美術的待畫清單（走到退回畫法的 id）", () => {
  it("清單和快照相同（變了＝有新內容走到退回畫法，或美術補了圖）", async () => {
    const list = fallbackList();
    await expect(`${JSON.stringify(list, null, 1)}\n`).toMatchFileSnapshot("./__snapshots__/wl1bFallbackList.json");
  });

  it("檢查本身認得退回：不認得的 id 會被列進來", () => {
    expect(QT.entry("brand_new_status")).toBeNull();
    expect(QP.entry("skeleton", "brand_new_skeleton").unknown).toBe(true);
    expect(QP.entry("effect", "brand_new_effect").unknown).toBe(true);
    expect(QP.entry("skeleton", "strike").unknown).toBeUndefined();
  });

  it("每一類內容資料都讀到了（清單空的不是因為沒讀到資料）", () => {
    for (const [file, key] of [
      ["statuses.yaml", "statuses"],
      ["skill_primitives.yaml", "primitives"],
      ["surfaces.yaml", "surfaces"],
      ["skill_conditions.yaml", "conditions"],
      ["skill_triggers.yaml", "triggers"],
      ["reactions.yaml", "events"],
      ["skill_shapes.yaml", "shapes"],
      ["elements.yaml", "elements"],
    ] as const)
      expect(ids(file, key).length, file).toBeGreaterThan(3);
    expect(ICONS.length).toBeGreaterThan(400);
  });
});
