// 雇用面板的技能圖示列（UI-E3；docs/art/RT-2與RT-4與6H-1與AU-3檢查.md 第 20 行）：傭兵的技能從一長串文字改成圖示列，
// 最多 8 個，滑過看名字。伺服器的傭兵資料只給技能中文名（`skills_zh`）與 build 的主題句（`theme_zh`），不改伺服器：
// 用現有的 `GET /api/builds`（每個 build 的技能 ID 與主題句）找到同主題的 build，取它的技能卡（`GET /api/skills/{id}`，
// 有快取），再照名字一一對上。對不上的名字（例如內容改了）照舊寫字，不畫假圖示。
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { BuildSummary, SkillCard } from "../api/types";

/** 一列最多畫幾個圖示（多的寫「+N」，滑過看名字）。 */
export const HIRE_ICON_MAX = 8;

/** 傭兵（主題句）可能用到的技能 ID：同主題句的 build 的技能，照 build 順序、去重。 */
export function themeSkillIds(themes: readonly string[], builds: readonly Pick<BuildSummary, "theme_zh" | "skills">[]): string[] {
  const want = new Set(themes);
  const out: string[] = [];
  for (const b of builds) {
    if (!want.has(b.theme_zh)) continue;
    for (const id of b.skills) if (!out.includes(id)) out.push(id);
  }
  return out;
}

export type HireSkill = { name: string; card: SkillCard | null };

/** 技能名 → 卡片（同名的取第一張）；名字照傳入順序，最多 `max` 個，其餘回傳在 `rest`。 */
export function matchSkills(names: readonly string[], cards: readonly SkillCard[], max = HIRE_ICON_MAX): { shown: HireSkill[]; rest: string[] } {
  const byName = new Map<string, SkillCard>();
  for (const c of cards) if (!byName.has(c.name_zh)) byName.set(c.name_zh, c);
  return {
    shown: names.slice(0, max).map((name) => ({ name, card: byName.get(name) ?? null })),
    rest: names.slice(max),
  };
}

let buildsCache: BuildSummary[] | null = null;
let buildsWait: Promise<BuildSummary[]> | null = null;

/** 內容的 build 清單（整個頁面共用一份；失敗時當成空的）。 */
export function useBuilds(): readonly BuildSummary[] {
  const [builds, setBuilds] = useState<BuildSummary[]>(buildsCache ?? []);
  useEffect(() => {
    if (buildsCache !== null) return undefined;
    let alive = true;
    buildsWait ??= api.builds().then(
      (b) => (buildsCache = b),
      () => (buildsCache = []),
    );
    void buildsWait.then((b) => alive && setBuilds(b));
    return () => {
      alive = false;
    };
  }, []);
  return builds;
}
