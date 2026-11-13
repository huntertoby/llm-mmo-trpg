// 背包滿了：戰後結算選要丟哪件（Phase 5D-2b；最小介面，完整背包畫面在 5D-4）。
// 列出新拿到的與背包裡原本的；裝備用勾選、其他用個數；說明用共用 <Hint>，沿用商店與腰包的列樣式。
import { useState } from "react";
import type { WorldAction, WorldBagItem, WorldInventory, WorldPendingLoot } from "../api/types";
import { Hint } from "../ui/Hint";
import { ItemListIcon } from "../ui/ItemIcon";
import { type LootDraft, type LootSide, draftKey, lootChooseAction } from "./lootChoice";

interface Props {
  pending: WorldPendingLoot;
  inventory: WorldInventory | null | undefined;
  busy: boolean;
  onAct(action: WorldAction): void;
}

function itemHint(item: WorldBagItem): string {
  return [item.description_zh, item.battle_zh ?? ""].filter((s) => s !== "").join("　");
}

export function LootChoicePanel({ pending, inventory, busy, onAct }: Props) {
  const [draft, setDraft] = useState<LootDraft>({});
  const rows: { side: LootSide; item: WorldBagItem }[] = [
    ...pending.items.map((item) => ({ side: "new" as const, item })),
    ...(inventory?.bag ?? []).map((item) => ({ side: "bag" as const, item })),
  ];
  const set = (key: string, n: number) => setDraft({ ...draft, [key]: n });
  return (
    <div className="world-loot-choice small" data-testid="world-loot-choice">
      <div className="section-title small">背包滿了：選要丟哪件</div>
      <div className="muted">{pending.hint_zh}</div>
      <ul className="world-shop-list">
        {rows.map(({ side, item }) => {
          const key = draftKey(side, item.item);
          return (
            <li key={key} data-testid={`world-loot-row-${key}`}>
              <Hint text={itemHint(item)}>
                <span className="world-shop-thing">
                  <ItemListIcon id={item.item} gear={item.gear} color={item.color} rare={item.rare} />
                  <span className="world-shop-name">{item.name_zh}</span>
                </span>
              </Hint>
              <span className="muted">{side === "new" ? "新拿到" : "背包裡"}</span>
              {item.gear === true ? (
                <label>
                  <input
                    type="checkbox"
                    checked={(draft[key] ?? 0) > 0}
                    disabled={busy}
                    onChange={(e) => set(key, e.target.checked ? 1 : 0)}
                    data-testid={`world-loot-drop-${key}`}
                  />
                  丟掉
                </label>
              ) : (
                <label>
                  丟
                  <select
                    value={draft[key] ?? 0}
                    disabled={busy}
                    onChange={(e) => set(key, Number(e.target.value))}
                    data-testid={`world-loot-drop-${key}`}
                  >
                    {Array.from({ length: item.count + 1 }, (_, n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </select>
                  個（共 {item.count}）
                </label>
              )}
            </li>
          );
        })}
      </ul>
      <Hint text="丟掉勾選的，剩下的戰利品收進背包；還放不下會告訴你差幾格。">
        <button type="button" disabled={busy} onClick={() => onAct(lootChooseAction(draft, rows))} data-testid="world-loot-choose">
          決定
        </button>
      </Hint>
    </div>
  );
}
