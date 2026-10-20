// 技能卡片快取：缺的技能 ID 以 /api/skills/{id} 取得（失敗時沒有卡片，畫面退回顯示 ID）。
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { SkillCard } from "../api/types";
import type { SkillNames } from "../battle/actions";

const cache = new Map<string, SkillCard | null>();

function snapshot(): Record<string, SkillCard | undefined> {
  const out: Record<string, SkillCard | undefined> = {};
  for (const [id, card] of cache) if (card !== null) out[id] = card;
  return out;
}

/** `battleId`：戰鬥內的自訂技能（工坊試玩、一輪生成技能）要靠它查；重新整理後快取是空的。 */
export function useSkillCards(
  ids: readonly string[],
  battleId?: string,
): Readonly<Record<string, SkillCard | undefined>> {
  const [cards, setCards] = useState(snapshot);
  const key = ids.join(",");
  useEffect(() => {
    const missing = key === "" ? [] : key.split(",").filter((id) => !cache.has(id));
    if (missing.length === 0) return undefined;
    let cancelled = false;
    void Promise.all(
      missing.map(async (id) => {
        try {
          cache.set(id, await api.skill(id, battleId));
        } catch {
          cache.set(id, null);
        }
      }),
    ).then(() => {
      if (!cancelled) setCards(snapshot());
    });
    return () => {
      cancelled = true;
    };
  }, [key, battleId]);
  return cards;
}

/** 技能 ID → 中文名。 */
export function skillNamesOf(cards: Readonly<Record<string, SkillCard | undefined>>): SkillNames {
  return Object.fromEntries(Object.entries(cards).flatMap(([id, c]) => (c === undefined ? [] : [[id, c.name_zh]])));
}

export function useSkillNames(cards: Readonly<Record<string, SkillCard | undefined>>): SkillNames {
  return useMemo(() => skillNamesOf(cards), [cards]);
}

/** 先把已知的卡片放進快取：工坊的自訂技能不在 `/api/skills`，戰鬥畫面要靠這裡才認得出名稱。 */
export function primeSkillCard(card: SkillCard): void {
  cache.set(card.id, card);
}
