// 技能名稱快取：缺的技能 ID 以 /api/skills/{id} 取得（失敗時以 ID 當名稱）。
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { SkillNames } from "../battle/actions";

const cache = new Map<string, string>();

export function useSkillNames(ids: readonly string[]): SkillNames {
  const [names, setNames] = useState<SkillNames>(() => Object.fromEntries(cache));
  const key = ids.join(",");
  useEffect(() => {
    const missing = key === "" ? [] : key.split(",").filter((id) => !cache.has(id));
    if (missing.length === 0) return undefined;
    let cancelled = false;
    void Promise.all(
      missing.map(async (id) => {
        try {
          cache.set(id, (await api.skill(id)).name_zh);
        } catch {
          cache.set(id, id);
        }
      }),
    ).then(() => {
      if (!cancelled) setNames(Object.fromEntries(cache));
    });
    return () => {
      cancelled = true;
    };
  }, [key]);
  return names;
}
