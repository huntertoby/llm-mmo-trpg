// 鐵匠與附魔台（Phase 5D-3；docs/phases/Phase5計畫.md 30.5）。
// 5D-4（33.2）：改成大世界左欄的完整畫面（`WorldSmithyScreen`），上方分頁「打造」「配方碼」「強化與分解」「附魔台」：
// 打造表單、輸入配方碼照打（不在配方表上的舊碼也照送，後端裁決）與世界的配方表（每件裝備只列最新一筆、首位發現者）、
// 每件裝備的強化與分解、附魔台的重骰與指定。說明與停用原因一律用共用 <Hint>；費用、候選與能不能做都由後端算好。
import { useState } from "react";
import type { WorldAction, WorldCraftGear, WorldCrafting, WorldView } from "../api/types";
import { Hint } from "../ui/Hint";
import { ItemListIcon } from "../ui/ItemIcon";
import { codeProblem, normalizeCode } from "./bagView";
import { craftAction, draftProblem, initialDraft, toggleMaterial, withSlot, type CraftDraft } from "./crafting";
import { walletLine } from "./economy";
import { LimitNote, limitOf } from "./limits";

interface ActProps {
  busy: boolean;
  onAct(action: WorldAction): void;
}

export type SmithyTab = "craft" | "code" | "gear" | "enchant";

const TABS: { id: SmithyTab; label: string }[] = [
  { id: "craft", label: "打造" },
  { id: "code", label: "配方碼" },
  { id: "gear", label: "強化與分解" },
  { id: "enchant", label: "附魔台" },
];

/** 這裡有的分頁：沒有鐵匠就沒有打造、配方碼、強化；沒有附魔台就沒有附魔台。 */
export function smithyTabs(crafting: Pick<WorldCrafting, "smithy" | "enchanter">): SmithyTab[] {
  return TABS.map((t) => t.id).filter((id) => (id === "enchant" ? crafting.enchanter != null : crafting.smithy != null));
}

function CraftForm({ crafting, busy, onAct, armorOnly = false }: ActProps & { crafting: WorldCrafting; armorOnly?: boolean }) {
  const [draft, setDraft] = useState<CraftDraft>(() => initialDraft(crafting, armorOnly));
  const slot = crafting.slots.find((s) => s.slot_type === draft.slot);
  const grades = crafting.materials.filter((m) => m.grade);
  const flavors = crafting.materials.filter((m) => !m.grade);
  const rarity = crafting.rarities.find((r) => r.rarity === draft.rarity);
  const problem = !crafting.can_use ? crafting.problem_zh ?? "現在不能打造" : draftProblem(draft);
  const station = crafting.smithy ?? "";
  return (
    <div className="world-craft-form small" data-testid="world-craft-form">
      <div className="muted">指定部位＋1 條詞條；其餘詞條的傾向由特色材料決定。同一份配方一定打出同一件。</div>
      <div className="world-form-grid">
        <label>
          部位
          <select value={draft.slot} disabled={busy} onChange={(e) => setDraft(withSlot(draft, crafting, e.target.value))} data-testid="world-craft-slot">
            {crafting.slots.map((s) => (
              <option key={s.slot_type} value={s.slot_type}>
                {s.name_zh}（通用料 ×{s.grade_amount}）
              </option>
            ))}
          </select>
        </label>
        <label>
          稀有度
          <select value={draft.rarity} disabled={busy} onChange={(e) => setDraft({ ...draft, rarity: e.target.value })} data-testid="world-craft-rarity">
            {crafting.rarities.map((r) => (
              <option key={r.rarity} value={r.rarity}>
                {r.name_zh}
              </option>
            ))}
          </select>
        </label>
        <label>
          詞條
          <select value={draft.affix} disabled={busy} onChange={(e) => setDraft({ ...draft, affix: e.target.value })} data-testid="world-craft-affix">
            {(slot?.affixes ?? []).map((a) => (
              <option key={a.id} value={a.id}>
                {a.text_zh}
              </option>
            ))}
          </select>
        </label>
        <label>
          通用料
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
      {rarity != null && <div className="muted">費用：{rarity.cost_zh}</div>}
      <div className="section-title small">特色材料（最多 {crafting.flavor_max} 種，每種用 1 個；滑過看傾向）</div>
      <div className="world-craft-materials">
        {flavors.length === 0 && <span className="muted">背包裡沒有特色材料（打倒敵人會掉）。</span>}
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
              <ItemListIcon id={m.item} />
              {m.name_zh} ×{m.count}
            </label>
          </Hint>
        ))}
      </div>
      <div className="run-actions">
        <Hint text={problem ?? crafting.note_zh}>
          <span className="world-shop-buy">
            <button
              type="button"
              className="primary"
              disabled={busy || problem !== null}
              onClick={() => onAct(craftAction(draft, station))}
              data-testid="world-craft-submit"
            >
              打造
            </button>
          </span>
        </Hint>
      </div>
    </div>
  );
}

function RecipeCodes({ crafting, busy, onAct }: ActProps & { crafting: WorldCrafting }) {
  const [text, setText] = useState("");
  const smithy = crafting.smithy;
  const problem = smithy == null ? "這裡沒有鐵匠" : !crafting.can_use ? crafting.problem_zh ?? "現在不能打造" : codeProblem(text);
  return (
    <div className="world-recipe-codes small" data-testid="world-recipe-codes">
      <div className="muted">朋友分享的配方碼：用自己的材料照打一件（重骰過的也照序列重現，費用照付）。舊碼不在表上也照樣能打。</div>
      <div className="run-actions">
        <input
          type="text"
          className="world-code-input"
          value={text}
          maxLength={14}
          placeholder="例：ABCDEF0123"
          aria-label="配方碼"
          disabled={busy}
          onChange={(e) => setText(e.target.value)}
          data-testid="world-code-input"
        />
        <Hint text={problem ?? "照這個配方碼打造"}>
          <span className="world-shop-buy">
            <button
              type="button"
              className="primary"
              disabled={busy || problem !== null}
              onClick={() => onAct({ kind: "craft", station: smithy ?? "", code: normalizeCode(text) })}
              data-testid="world-code-submit"
            >
              照配方打造
            </button>
          </span>
        </Hint>
      </div>
      <div className="section-title small">世界的配方表（每件裝備只列最新一筆）</div>
      {crafting.recipes.length === 0 ? (
        <div className="muted">還沒有人打造過。第一個打出某份配方的人會成為它的首位發現者。</div>
      ) : (
        <ul className="world-shop-list world-recipe-list" data-testid="world-recipes">
          {crafting.recipes.map((r) => (
            <li key={r.code}>
              <span className="world-shop-name">{r.name_zh}</span>
              <span className="world-recipe-code">{r.code}</span>
              <span className="muted world-recipe-summary">
                {r.summary_zh}・首位發現者 {r.discoverer_name}
                {r.mine ? "（你）" : ""}
              </span>
              <Hint text={r.can_craft ? "用自己的材料照這份配方打一件" : r.problem_zh ?? "不能打"}>
                <span className="world-shop-buy">
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
      )}
    </div>
  );
}

function GearHead({ gear }: { gear: WorldCraftGear }) {
  return (
    <div className="world-craft-gear-head">
      <Hint text={gear.description_zh}>
        <span className="world-shop-name">{gear.name_zh}</span>
      </Hint>
      {gear.enhance > 0 && <span className="world-enhance-tag">+{gear.enhance}</span>}
      {gear.worn && <span className="muted">（穿戴中）</span>}
      {gear.code != null && <span className="muted world-recipe-code">配方碼 {gear.code}</span>}
    </div>
  );
}

function EnhanceRow({ gear, crafting, busy, onAct }: ActProps & { gear: WorldCraftGear; crafting: WorldCrafting }) {
  const smithy = crafting.smithy ?? "";
  return (
    <li className="world-craft-gear" data-testid={`world-craft-gear-${gear.item}`}>
      <GearHead gear={gear} />
      <div className="run-actions">
        <Hint text={gear.enhance_zh ?? "強化"}>
          <span className="world-shop-buy">
            <button
              type="button"
              disabled={busy || !gear.can_enhance}
              onClick={() => onAct({ kind: "enhance", station: smithy, item: gear.item })}
              data-testid={`world-enhance-${gear.item}`}
            >
              強化
            </button>
          </span>
        </Hint>
        <Hint text={gear.salvage_zh ?? "分解"}>
          <span className="world-shop-buy">
            <button
              type="button"
              disabled={busy || !gear.can_salvage}
              onClick={() => onAct({ kind: "salvage", station: smithy, item: gear.item })}
              data-testid={`world-salvage-${gear.item}`}
            >
              分解
            </button>
          </span>
        </Hint>
      </div>
    </li>
  );
}

function EnchantRow({ gear, crafting, busy, onAct }: ActProps & { gear: WorldCraftGear; crafting: WorldCrafting }) {
  const [imbue, setImbue] = useState<Record<number, string>>({});
  const enchanter = crafting.enchanter ?? "";
  return (
    <li className="world-craft-gear" data-testid={`world-enchant-gear-${gear.item}`}>
      <GearHead gear={gear} />
      <div className="muted">重骰：{gear.reroll_zh ?? "—"}　指定：{gear.imbue_zh ?? "—"}</div>
      <ul className="world-affix-rows">
        {(gear.affixes ?? []).map((a) => (
          <li key={a.index}>
            <span className="world-affix-text">{a.text_zh}</span>
            <Hint text={a.can_change ? `重骰這條：${gear.reroll_zh ?? ""}` : "這條不能換（獨特詞條或沒有候選）"}>
              <span className="world-shop-buy">
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
                <select
                  value={imbue[a.index] ?? ""}
                  disabled={busy}
                  aria-label="指定成"
                  onChange={(e) => setImbue({ ...imbue, [a.index]: e.target.value })}
                  data-testid={`world-imbue-pick-${gear.item}-${a.index}`}
                >
                  <option value="">指定成…</option>
                  {(a.choices ?? []).map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.text_zh}
                    </option>
                  ))}
                </select>
                <Hint text={(imbue[a.index] ?? "") === "" ? "先選要指定成哪一條" : `指定：${gear.imbue_zh ?? ""}`}>
                  <span className="world-shop-buy">
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
    </li>
  );
}

export function SmithyPanel({ crafting, busy, onAct, initialTab, armorOnly = false }: ActProps & { crafting: WorldCrafting; initialTab?: SmithyTab; armorOnly?: boolean }) {
  const tabs = smithyTabs(crafting);
  const [picked, setTab] = useState<SmithyTab | null>(initialTab ?? null);
  const tab = picked !== null && tabs.includes(picked) ? picked : (tabs[0] ?? null);
  return (
    <div className="world-smithy" data-testid="world-smithy">
      <div className="section-title small">
        {crafting.stations.map((s) => s.name_zh + (s.npc_name_zh != null ? `（${s.npc_name_zh}）` : "")).join("・")}
        <span className="muted">　精華 ×{crafting.essence}</span>
      </div>
      {!crafting.can_use && crafting.problem_zh != null && <div className="muted small">{crafting.problem_zh}</div>}
      <div className="world-tabs" role="tablist" aria-label="鐵匠與附魔台">
        {TABS.filter((t) => tabs.includes(t.id)).map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={tab === t.id ? "primary" : ""}
            onClick={() => setTab(t.id)}
            data-testid={`world-smithy-tab-${t.id}`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tab === "craft" && <CraftForm crafting={crafting} busy={busy} onAct={onAct} armorOnly={armorOnly} />}
      {tab === "code" && <RecipeCodes crafting={crafting} busy={busy} onAct={onAct} />}
      {(tab === "gear" || tab === "enchant") &&
        (crafting.gear.length === 0 ? (
          <div className="muted small">沒有可以處理的裝備（打造品與掉落的裝備才有物品等級）。</div>
        ) : (
          <ul className="world-shop-list small world-craft-gears" data-testid={`world-${tab}-list`}>
            {crafting.gear.map((g) =>
              tab === "gear" ? (
                <EnhanceRow key={g.item} gear={g} crafting={crafting} busy={busy} onAct={onAct} />
              ) : (
                <EnchantRow key={g.item} gear={g} crafting={crafting} busy={busy} onAct={onAct} />
              ),
            )}
          </ul>
        ))}
      <div className="muted small">{crafting.note_zh}</div>
    </div>
  );
}

export function WorldSmithyScreen({ view, busy, onAct, onClose }: ActProps & { view: WorldView; onClose(): void }) {
  return (
    <div className="panel world-screen-pane world-smithy-screen" data-testid="world-smithy-screen">
      <div className="world-quest-head">
        <h2>鐵匠與附魔台</h2>
        <span className="muted small">{view.wallet != null ? walletLine(view.wallet) : ""}</span>
        <button type="button" onClick={onClose} data-testid="world-smithy-close">
          回到地點圖
        </button>
      </div>
      <LimitNote reason={limitOf(view, "smith")} />
      {view.crafting == null ? (
        <div className="muted small">這裡沒有鐵匠或附魔台。</div>
      ) : (
        // OB-6（美術追蹤②）：入門期（伺服器的限制資料有「只限防具」）部位下拉預設防具
        <SmithyPanel crafting={view.crafting} busy={busy} onAct={onAct} armorOnly={limitOf(view, "smith") !== null} />
      )}
    </div>
  );
}
