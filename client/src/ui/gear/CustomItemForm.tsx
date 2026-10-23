// 手動組一件物品（Phase 3G-G4）：選名稱／武器，從白名單掛 1～4 條詞條，數值限制在初值範圍內。
// 這裡只能「提議」：不合法的組合會顯示原因，真正的裁決在伺服器（沿用引擎的驗證）。
import { useState } from "react";
import type { GearCatalog, GearSlotInfo } from "../../api/types";
import appearance from "../../render/gearAppearance.json";
import {
  affixOptions,
  affixText,
  clampValue,
  defaultValue,
  draftLook,
  draftProblems,
  rangeText,
  weaponOptionText,
  type CustomDraft,
} from "../../gear/gearDraft";
import { GearIcon } from "../GearIcon";

interface Props {
  catalog: GearCatalog;
  slot: GearSlotInfo;
  draft: CustomDraft;
  onChange(draft: CustomDraft): void;
  onEquip(): void;
  /** 目前這個欄位已經穿著的是自訂物品。 */
  equipped: boolean;
}

interface KindEntry {
  id: string;
  slotType: string;
  zh: string;
  paired: boolean;
}
const KINDS = appearance.kinds as unknown as KindEntry[];

export function CustomItemForm({ catalog, slot, draft, onChange, onEquip, equipped }: Props) {
  const [adding, setAdding] = useState("");
  const options = affixOptions(catalog, slot.slot_type, draft);
  const problems = draftProblems(draft, slot.slot_type, catalog);
  const used = new Set(draft.affixes.map((a) => a.affix));
  const full = draft.affixes.length >= catalog.max_affixes_per_item;
  const kinds = KINDS.filter((k) => k.slotType === slot.slot_type && (slot.slot_type !== "weapon" || k.paired === draft.paired));
  const isWeapon = slot.slot_type === "weapon";

  const patch = (p: Partial<CustomDraft>) => onChange({ ...draft, ...p });
  const addAffix = (id: string) => {
    const info = catalog.affixes.find((a) => a.id === id);
    if (info === undefined || full) return;
    onChange({ ...draft, affixes: [...draft.affixes, { affix: id, value: defaultValue(info) }] });
    setAdding("");
  };

  return (
    <div className="gear-custom">
      <div className="gear-custom-head">
        <GearIcon look={draftLook(draft, catalog)} slot={slot.slot} size={64} />
        <div className="gear-custom-fields">
          <label>
            名稱
            <input value={draft.name} maxLength={20} onChange={(e) => patch({ name: e.target.value })} />
          </label>
          {isWeapon && (
            <label>
              武器
              <select value={draft.weapon} onChange={(e) => patch({ weapon: e.target.value, kind: "" })}>
                <option value="">（選一種武器）</option>
                {catalog.weapons.map((w) => (
                  <option key={w.id} value={w.id}>
                    {weaponOptionText(w)}
                  </option>
                ))}
              </select>
            </label>
          )}
          {isWeapon && (
            <label className="gear-check">
              <input type="checkbox" checked={draft.paired} onChange={(e) => patch({ paired: e.target.checked, kind: "" })} />
              成對武器（占用副手）
            </label>
          )}
          {slot.slot_type === "offhand" && (
            <label className="gear-check">
              <input type="checkbox" checked={draft.shield} onChange={(e) => patch({ shield: e.target.checked })} />
              是盾（才能掛「限盾」詞條）
            </label>
          )}
          <label className="gear-check">
            <input type="checkbox" checked={draft.legendary} onChange={(e) => patch({ legendary: e.target.checked })} />
            傳說物品（才能掛改變規則類詞條）
          </label>
          <label>
            外觀造型（只影響圖示）
            <select value={draft.kind} onChange={(e) => patch({ kind: e.target.value })}>
              <option value="">{draft.weapon === "" ? "依欄位預設" : "依所選武器"}</option>
              {kinds.map((k) => (
                <option key={k.id} value={k.id}>
                  {k.zh}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="gear-affix-list">
        <div className="section-title">
          詞條（{draft.affixes.length} / {catalog.max_affixes_per_item}，只能從白名單選）
        </div>
        {draft.affixes.length === 0 && <div className="muted small">還沒有詞條。</div>}
        {draft.affixes.map((pick, index) => {
          const info = catalog.affixes.find((a) => a.id === pick.affix);
          if (info === undefined) return null;
          return (
            <div key={`${pick.affix}:${index}`} className="gear-affix-row">
              <span className="gear-affix-cat">{info.category_zh}</span>
              <span className="gear-affix-text">{affixText(info, pick.value)}</span>
              {info.value_min != null && (
                <label className="gear-affix-value">
                  <span className="muted small">數值 {rangeText(info)}</span>
                  <input
                    type="number"
                    min={info.value_min}
                    max={info.value_max ?? undefined}
                    step={1}
                    value={pick.value ?? info.value_min}
                    aria-label={`${info.name_zh} 的數值`}
                    onChange={(e) => {
                      const next = [...draft.affixes];
                      next[index] = { ...pick, value: clampValue(info, e.target.valueAsNumber) };
                      onChange({ ...draft, affixes: next });
                    }}
                  />
                  {info.value_unit === "permille" && <span className="muted small">（千分比，100 ＝ 10%）</span>}
                </label>
              )}
              <button type="button" onClick={() => onChange({ ...draft, affixes: draft.affixes.filter((_, i) => i !== index) })} aria-label={`移除 ${info.name_zh}`}>
                移除
              </button>
            </div>
          );
        })}
        <div className="gear-affix-add">
          <select value={adding} disabled={full} onChange={(e) => setAdding(e.target.value)} aria-label="從白名單選詞條">
            <option value="">{full ? `已達上限（${catalog.max_affixes_per_item} 條）` : "從白名單選一條詞條……"}</option>
            {options
              .filter((o) => !used.has(o.info.id))
              .map(({ info, blocked }) => (
                <option key={info.id} value={info.id} disabled={blocked !== null}>
                  {info.category_zh}｜{info.name_zh.replace("{n}", "N")}
                  {blocked !== null ? `（${blocked}）` : ""}
                </option>
              ))}
          </select>
          <button type="button" disabled={adding === "" || full} onClick={() => addAffix(adding)}>
            加入詞條
          </button>
        </div>
      </div>

      {problems.length > 0 && (
        <ul className="gear-problems" role="alert">
          {problems.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      )}
      <div className="ws-row">
        <button type="button" className="primary" disabled={problems.length > 0} onClick={onEquip}>
          {equipped ? "更新並穿上" : `穿到${slot.name_zh}`}
        </button>
        {problems.length === 0 && <span className="muted small">穿上後由伺服器再檢查一次整組裝備。</span>}
      </div>
    </div>
  );
}
