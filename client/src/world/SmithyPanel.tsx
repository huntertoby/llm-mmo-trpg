// 鐵匠與附魔台（Phase 5D-3；docs/phases/Phase5計畫.md 28.5；最小可用，完整畫面在 5D-4）。
// 小鎮服務列「鐵匠」切換後於面板內展開（同商店）：打造表單、已知配方（配方碼、首位發現者）、
// 強化與分解、附魔台的重骰與指定。說明與停用原因一律用共用 <Hint>；費用、候選與能不能做都由後端算好。
import { useState } from "react";
import type { WorldAction, WorldCraftGear, WorldCrafting } from "../api/types";
import { Hint } from "../ui/Hint";
import { craftAction, draftProblem, initialDraft, toggleMaterial, withSlot, type CraftDraft } from "./crafting";

interface ActProps {
  busy: boolean;
  onAct(action: WorldAction): void;
}

function CraftForm({ crafting, busy, onAct }: ActProps & { crafting: WorldCrafting }) {
  const [draft, setDraft] = useState<CraftDraft>(() => initialDraft(crafting));
  const slot = crafting.slots.find((s) => s.slot_type === draft.slot);
  const grades = crafting.materials.filter((m) => m.grade);
  const flavors = crafting.materials.filter((m) => !m.grade);
  const rarity = crafting.rarities.find((r) => r.rarity === draft.rarity);
  const problem = !crafting.can_use ? crafting.problem_zh ?? "現在不能打造" : draftProblem(draft);
  const station = crafting.smithy ?? "";
  return (
    <div className="world-craft-form small" data-testid="world-craft-form">
      <div className="section-title small">打造（指定部位＋1 條詞條；其餘詞條的傾向由特色材料決定）</div>
      <label>
        部位{" "}
        <select value={draft.slot} disabled={busy} onChange={(e) => setDraft(withSlot(draft, crafting, e.target.value))} data-testid="world-craft-slot">
          {crafting.slots.map((s) => (
            <option key={s.slot_type} value={s.slot_type}>
              {s.name_zh}（通用料 ×{s.grade_amount}）
            </option>
          ))}
        </select>
      </label>{" "}
      <label>
        稀有度{" "}
        <select value={draft.rarity} disabled={busy} onChange={(e) => setDraft({ ...draft, rarity: e.target.value })} data-testid="world-craft-rarity">
          {crafting.rarities.map((r) => (
            <option key={r.rarity} value={r.rarity}>
              {r.name_zh}
            </option>
          ))}
        </select>
      </label>
      {rarity != null && <span className="muted">　{rarity.cost_zh}</span>}
      <div>
        <label>
          詞條{" "}
          <select value={draft.affix} disabled={busy} onChange={(e) => setDraft({ ...draft, affix: e.target.value })} data-testid="world-craft-affix">
            {(slot?.affixes ?? []).map((a) => (
              <option key={a.id} value={a.id}>
                {a.text_zh}
              </option>
            ))}
          </select>
        </label>{" "}
        <label>
          通用料{" "}
          <select value={draft.grade} disabled={busy} onChange={(e) => setDraft({ ...draft, grade: e.target.value })} data-testid="world-craft-grade">
            {grades.length === 0 && <option value="">（背包沒有）</option>}
            {grades.map((m) => (
              <option key={m.item} value={m.item}>
                {m.name_zh} ×{m.count}（物品等級最高 {m.level_cap}）
              </option>
            ))}
          </select>
        </label>
      </div>
      <div>
        特色材料（最多 {crafting.flavor_max} 種，每種用 1 個）：
        {flavors.length === 0 && <span className="muted">背包裡沒有</span>}
        {flavors.map((m) => (
          <Hint key={m.item} text={[m.leaning_zh, m.resonance_zh].filter((s) => s != null).join("　") || m.name_zh}>
            <label className="world-craft-material">
              <input
                type="checkbox"
                checked={draft.materials.includes(m.item)}
                disabled={busy}
                onChange={() => setDraft(toggleMaterial(draft, m.item, crafting.flavor_max))}
                data-testid={`world-craft-material-${m.item}`}
              />
              {m.name_zh} ×{m.count}
            </label>
          </Hint>
        ))}
      </div>
      <Hint text={problem ?? crafting.note_zh}>
        <span>
          <button type="button" disabled={busy || problem !== null} onClick={() => onAct(craftAction(draft, station))} data-testid="world-craft-submit">
            打造
          </button>
        </span>
      </Hint>
    </div>
  );
}

function GearRow({ gear, crafting, busy, onAct }: ActProps & { gear: WorldCraftGear; crafting: WorldCrafting }) {
  const [imbue, setImbue] = useState<Record<number, string>>({});
  const smithy = crafting.smithy ?? "";
  const enchanter = crafting.enchanter;
  return (
    <li data-testid={`world-craft-gear-${gear.item}`}>
      <div>
        <span className="world-shop-name">{gear.name_zh}</span>
        {gear.enhance > 0 && <span> +{gear.enhance}</span>}
        {gear.worn && <span className="muted">（穿戴中）</span>}
        {gear.code != null && <span className="muted">　配方碼 {gear.code}</span>}
      </div>
      <div className="run-actions">
        <Hint text={gear.enhance_zh ?? "強化"}>
          <span>
            <button type="button" disabled={busy || !gear.can_enhance} onClick={() => onAct({ kind: "enhance", station: smithy, item: gear.item })} data-testid={`world-enhance-${gear.item}`}>
              強化
            </button>
          </span>
        </Hint>
        <Hint text={gear.salvage_zh ?? "分解"}>
          <span>
            <button type="button" disabled={busy || !gear.can_salvage} onClick={() => onAct({ kind: "salvage", station: smithy, item: gear.item })} data-testid={`world-salvage-${gear.item}`}>
              分解
            </button>
          </span>
        </Hint>
      </div>
      {enchanter != null && (
        <ul className="small">
          {(gear.affixes ?? []).map((a) => (
            <li key={a.index}>
              {a.text_zh}{" "}
              <Hint text={a.can_change ? `重骰：${gear.reroll_zh ?? ""}` : "這條不能換"}>
                <span>
                  <button
                    type="button"
                    disabled={busy || !a.can_change || !crafting.can_use}
                    onClick={() => onAct({ kind: "reroll", station: enchanter, item: gear.item, index: a.index })}
                    data-testid={`world-reroll-${gear.item}-${a.index}`}
                  >
                    重骰
                  </button>
                </span>
              </Hint>
              {a.can_change && (a.choices ?? []).length > 0 && (
                <>
                  {" "}
                  <select value={imbue[a.index] ?? ""} disabled={busy} onChange={(e) => setImbue({ ...imbue, [a.index]: e.target.value })}>
                    <option value="">指定成…</option>
                    {(a.choices ?? []).map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.text_zh}
                      </option>
                    ))}
                  </select>{" "}
                  <Hint text={`指定：${gear.imbue_zh ?? ""}`}>
                    <span>
                      <button
                        type="button"
                        disabled={busy || (imbue[a.index] ?? "") === "" || !crafting.can_use}
                        onClick={() => onAct({ kind: "imbue", station: enchanter, item: gear.item, index: a.index, affix: imbue[a.index] ?? "" })}
                        data-testid={`world-imbue-${gear.item}-${a.index}`}
                      >
                        指定
                      </button>
                    </span>
                  </Hint>
                </>
              )}
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

export function SmithyPanel({ crafting, busy, onAct }: ActProps & { crafting: WorldCrafting }) {
  const smithy = crafting.smithy;
  return (
    <div className="world-shop" data-testid="world-smithy">
      <div className="section-title small">
        {crafting.stations.map((s) => s.name_zh + (s.npc_name_zh != null ? `（${s.npc_name_zh}）` : "")).join("・")}
        <span className="muted">　精華 ×{crafting.essence}</span>
      </div>
      {!crafting.can_use && crafting.problem_zh != null && <div className="muted small">{crafting.problem_zh}</div>}
      <div className="muted small">{crafting.note_zh}</div>
      {smithy != null && <CraftForm crafting={crafting} busy={busy} onAct={onAct} />}
      {crafting.recipes.length > 0 && (
        <>
          <div className="section-title small">已發現的配方</div>
          <ul className="world-shop-list small" data-testid="world-recipes">
            {crafting.recipes.map((r) => (
              <li key={r.code}>
                <span className="world-shop-name">{r.name_zh}</span>
                <span className="muted">
                  {r.code}・{r.summary_zh}・首位發現者 {r.discoverer_name}
                  {r.mine ? "（你）" : ""}
                </span>
                <Hint text={r.can_craft ? "用自己的材料照這份配方打一件" : r.problem_zh ?? "不能打"}>
                  <span>
                    <button
                      type="button"
                      disabled={busy || !r.can_craft || smithy == null}
                      onClick={() => onAct({ kind: "craft", station: smithy ?? "", code: r.code })}
                      data-testid={`world-recipe-${r.code}`}
                    >
                      照配方打造
                    </button>
                  </span>
                </Hint>
              </li>
            ))}
          </ul>
        </>
      )}
      {crafting.gear.length > 0 && (
        <>
          <div className="section-title small">裝備：強化、分解{crafting.enchanter != null ? "、重骰、指定" : ""}</div>
          <ul className="world-shop-list small">
            {crafting.gear.map((g) => (
              <GearRow key={g.item} gear={g} crafting={crafting} busy={busy} onAct={onAct} />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
