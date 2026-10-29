// 營火換裝（Phase 3-26a）：卸下的技能進備用（等級保留），備用技能可以換回來（欄位上限同升級）。
import { useState } from "react";
import type { RunHero } from "../api/types";
import { SLOT_LABELS, SLOT_LIMITS, type SlotKind } from "./flow";
import { canEquip, loadoutChanged, loadoutUsage, ownedCards } from "./loadout";
import { Hint } from "../ui/Hint";

interface Props {
  hero: RunHero;
  disabled?: boolean;
  /** 套用換裝：新的裝備清單（技能 ID，順序即技能列順序）。 */
  onApply(ids: readonly string[]): void;
}

export function LoadoutEditor({ hero, disabled = false, onApply }: Props) {
  const [ids, setIds] = useState<readonly string[]>(() => hero.skills.map((s) => s.id));
  const cards = ownedCards(hero);
  const benched = [...cards.keys()].filter((id) => !ids.includes(id));
  const usage = loadoutUsage(hero, ids);
  const kinds = Object.keys(SLOT_LIMITS) as SlotKind[];
  return (
    <div className="loadout-editor" data-testid="loadout-editor">
      <div className="section-title">
        換裝
        <span className="muted small">
          {kinds.map((k) => `${SLOT_LABELS[k]} ${usage[k]}/${SLOT_LIMITS[k]}`).join("・")}　卸下的技能等級會保留
        </span>
      </div>
      <ul className="loadout-list">
        {ids.map((id) => {
          const card = cards.get(id);
          if (card === undefined) return null;
          return (
            <li key={id}>
              <span>
                {card.name_zh}
              </span>
              <button type="button" disabled={disabled} onClick={() => setIds(ids.filter((x) => x !== id))}>
                卸下
              </button>
            </li>
          );
        })}
      </ul>
      {benched.length > 0 && (
        <>
          <div className="muted small">備用</div>
          <ul className="loadout-list bench">
            {benched.map((id) => {
              const card = cards.get(id);
              if (card === undefined) return null;
              const ok = canEquip(hero, ids, id);
              return (
                <li key={id}>
                  <span>
                    {card.name_zh}
                      </span>
                  <Hint text={ok ? undefined : "這種欄位已滿，先卸下一個"}>
                  <button
                    type="button"
                    disabled={disabled || !ok}
                    onClick={() => setIds([...ids, id])}
                  >
                    裝備
                  </button>
                  </Hint>
                </li>
              );
            })}
          </ul>
        </>
      )}
      <div className="run-actions">
        <button type="button" disabled={disabled || !loadoutChanged(hero, ids)} onClick={() => onApply(ids)}>
          套用換裝
        </button>
      </div>
    </div>
  );
}
