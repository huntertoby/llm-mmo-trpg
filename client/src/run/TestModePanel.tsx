// 一輪開局的「測試模式」區（Phase 3-39）：勾選後戰後 HP、法力回滿，並可從現有測試物品為各部位挑裝備。
// 重用裝備測試頁的元件（欄位格、物品清單、英雄面板）；不挑也可以（只要回滿）。標記為測試模式的一輪不計入任何統計。
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import type { GearCatalog, GearCheck } from "../api/types";
import { occupiesOffHand, toEquipment, type Selection } from "../gear/gearDraft";
import { HeroGearPanel } from "../ui/gear/HeroGearPanel";
import { ItemList } from "../ui/gear/ItemList";
import { SlotGrid } from "../ui/gear/SlotGrid";
import type { StartChoiceBody } from "./startFlow";
import { keepPickable, pickableCatalog } from "./testMode";

const CHECK_DELAY_MS = 200;

interface Props {
  enabled: boolean;
  onEnabled(on: boolean): void;
  selection: Selection;
  onSelection(next: Selection): void;
  /** 目前的開局欄位（武器＋關鍵字）；還沒選完整時為 `null`。 */
  start: StartChoiceBody | null;
  /** 這組裝備是否合法（沒挑裝備、或伺服器檢查通過）；給開始按鈕用。 */
  onLegal(ok: boolean): void;
  disabled?: boolean;
}

function message(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

export function TestModePanel({ enabled, onEnabled, selection, onSelection, start, onLegal, disabled = false }: Props) {
  const [catalog, setCatalog] = useState<GearCatalog | null>(null);
  const [slotId, setSlotId] = useState("main_hand");
  const [check, setCheck] = useState<GearCheck | null>(null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);
  const weapon = start?.weapon ?? "";

  useEffect(() => {
    if (!enabled || catalog !== null) return undefined;
    let cancelled = false;
    api.gearCatalog().then(
      (c) => !cancelled && setCatalog(c),
      (e: unknown) => !cancelled && setError(message(e)),
    );
    return () => {
      cancelled = true;
    };
  }, [enabled, catalog]);

  const pickable = useMemo(() => (catalog === null ? null : pickableCatalog(catalog, weapon)), [catalog, weapon]);

  // 換武器後，主手已經不能挑的武器物品要拿掉。
  useEffect(() => {
    if (pickable === null) return;
    const kept = keepPickable(selection, pickable);
    if (Object.keys(kept).length !== Object.keys(selection).length) onSelection(kept);
  }, [pickable, selection, onSelection]);

  const equipment = useMemo(() => (pickable === null ? {} : toEquipment(selection, pickable)), [pickable, selection]);
  const hasGear = Object.keys(equipment).length > 0;

  // 整組裝備交給伺服器裁決（防抖，只採用最後一次請求的結果）；沒挑裝備時不需要檢查。
  const startKey = JSON.stringify(start);
  useEffect(() => {
    const body = (JSON.parse(startKey) as StartChoiceBody | null) ?? null;
    if (!enabled || !hasGear || body === null) {
      setCheck(null);
      setChecking(false);
      return undefined;
    }
    const id = ++requestId.current;
    setChecking(true);
    const timer = setTimeout(() => {
      api
        .gearCheck({ ...body, equipment })
        .then((result) => {
          if (id !== requestId.current) return;
          setCheck(result);
          setChecking(false);
        })
        .catch((e: unknown) => {
          if (id !== requestId.current) return;
          setError(message(e));
          setChecking(false);
        });
    }, CHECK_DELAY_MS);
    return () => clearTimeout(timer);
  }, [enabled, hasGear, startKey, equipment]);

  const legal = !enabled || !hasGear || (check !== null && check.legal && !checking);
  useEffect(() => onLegal(legal), [legal, onLegal]);

  const slot = pickable?.slots.find((s) => s.slot === slotId) ?? pickable?.slots[0];
  const problems = check !== null && !check.legal ? [...check.problems] : [];
  const setPick = (slot: string, itemId: string | null) => {
    const next = { ...selection };
    if (itemId === null) delete next[slot];
    else next[slot] = { item_id: itemId };
    onSelection(next);
  };

  return (
    <div className="panel run-test-mode" data-testid="test-mode">
      <label className="run-test-mode-toggle">
        <input type="checkbox" checked={enabled} disabled={disabled} onChange={(e) => onEnabled(e.target.checked)} /> 測試模式
      </label>
      <div className="muted small">每場戰鬥結束後 HP、法力自動回滿，並可從現有測試物品為各部位挑裝備（可以不挑）。這一輪會標記為測試模式，不計入任何統計。</div>
      {enabled && error !== null && <div className="error-text">{error}</div>}
      {enabled && pickable !== null && slot !== undefined && (
        <div className="run-test-gear gear-layout">
          <section className="gear-left">
            <div className="section-title">主角裝備（點格子選欄位）</div>
            <SlotGrid
              catalog={pickable}
              selection={selection}
              selected={slot.slot}
              offHandBlocked={occupiesOffHand(selection, pickable)}
              onSelect={setSlotId}
            />
            {problems.length > 0 && (
              <ul className="gear-problems" role="alert" aria-label="不合法的原因">
                <li className="gear-problems-title">這組裝備不合法：</li>
                {problems.map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
            )}
            {hasGear && <HeroGearPanel hero={check?.legal === true ? check.hero : null} pending={checking} />}
          </section>
          <section className="gear-right">
            <div className="section-title">
              {slot.name_zh}（{slot.slot_type_zh}類）
            </div>
            <ItemList catalog={pickable} slot={slot} selection={selection} onPick={(id) => setPick(slot.slot, id)} />
            {Object.keys(selection).length > 0 && (
              <button type="button" className="gear-unequip" onClick={() => onSelection({})}>
                全部卸下
              </button>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
