// 開局選擇（Phase 3-24b2／3-28）：起始武器 ＋ 2 個關鍵字（每個關鍵字的池各給 1 招起始技能）。
// 一輪開局、首頁單場戰鬥、技能工坊試玩、裝備測試共用。遊戲不定義流派：這裡不出現任何流派名稱。
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { DevPack, SkillCard, StartOptions, StartPreview, StartWeaponOption, StartKeywordOption } from "../api/types";
import { SkillCardView } from "../ui/SkillCardView";
import { canStart, keepAvailable, keywordAvailable, startBody, toggleKeyword, type StartChoiceBody } from "./startFlow";
import { Hint } from "../ui/Hint";

const CLASS_LABELS: Record<string, string> = { melee: "近戰", ranged: "遠程", focus: "法器" };

export interface StartPicker {
  options: StartOptions | null;
  weapon: string;
  setWeapon(id: string): void;
  selected: string[];
  setSelected(fn: (cur: string[]) => string[]): void;
  count: number;
  weaponDef: StartWeaponOption | undefined;
  previewOptions: StartKeywordOption[];
  packs: DevPack[];
  packId: string;
  setPackId(id: string): void;
  dev: boolean;
  /** 送給後端的開局欄位；還沒選完整時為 `null`。開發者模式選了起始包時用起始包。 */
  body: StartChoiceBody | null;
  /** 開局給的技能卡（依選擇順序）；開發者起始包時為空（起始技能由後端決定）。 */
  skills: SkillCard[];
  error: string | null;
}

/** 載入開局選項與預覽；`seed` 不合法（`null`）時暫停預覽。 */
export function useStartPicker(seed: number | null, dev: boolean, useDevPack = false): StartPicker {
  const [options, setOptions] = useState<StartOptions | null>(null);
  const [preview, setPreview] = useState<StartPreview | null>(null);
  const [weapon, setWeapon] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [packs, setPacks] = useState<DevPack[]>([]);
  const [packId, setPackId] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const fail = (e: unknown) => {
      if (!cancelled) setError(e instanceof Error ? e.message : String(e));
    };
    api.startOptions().then((o) => {
      if (cancelled) return;
      setOptions(o);
      setWeapon((cur) => cur || (o.weapons[0]?.id ?? ""));
    }, fail);
    if (dev) {
      api.devPacks().then((p) => {
        if (cancelled) return;
        setPacks(p);
        setPackId((cur) => cur || (p[0]?.id ?? ""));
      }, fail);
    }
    return () => {
      cancelled = true;
    };
  }, [dev]);

  const selectedKey = selected.join(",");
  useEffect(() => {
    if (weapon === "" || seed === null) return;
    let cancelled = false;
    api.startPreview(weapon, seed, selectedKey === "" ? [] : selectedKey.split(",")).then(
      (p) => {
        if (cancelled) return;
        setPreview(p);
        setSelected((cur) => {
          const kept = keepAvailable(cur, p.options);
          return kept.length === cur.length ? cur : kept;
        });
      },
      (e: unknown) => !cancelled && setError(e instanceof Error ? e.message : String(e)),
    );
    return () => {
      cancelled = true;
    };
  }, [weapon, seed, selectedKey]);

  const count = options?.keyword_count ?? 2;
  const previewOptions = preview !== null && preview.weapon === weapon ? preview.options : [];
  const weaponDef = options?.weapons.find((w) => w.id === weapon);
  const skills = selected
    .map((id) => previewOptions.find((o) => o.keyword.id === id)?.skill)
    .filter((s): s is SkillCard => s !== null && s !== undefined);
  const complete = canStart(weapon, selected, count, previewOptions);
  const body = useDevPack ? (packId === "" ? null : startBody({ devPack: packId })) : complete ? startBody({ weapon, keywords: selected }) : null;
  return {
    options,
    weapon,
    setWeapon: (id) => setWeapon(id),
    selected,
    setSelected: (fn) => setSelected(fn),
    count,
    weaponDef,
    previewOptions,
    packs,
    packId,
    setPackId: (id) => setPackId(id),
    dev,
    body,
    skills: useDevPack ? [] : skills,
    error,
  };
}

interface ViewProps {
  picker: StartPicker;
  disabled?: boolean;
}

/** 武器按鈕＋關鍵字按鈕＋起始技能預覽。 */
export function StartPickerView({ picker, disabled = false }: ViewProps) {
  const { options, weapon, selected, count, weaponDef, previewOptions } = picker;
  const chosen = selected
    .map((id) => previewOptions.find((o) => o.keyword.id === id))
    .filter((o) => o !== undefined && o.skill !== null && o.skill !== undefined);
  return (
    <>
      <div className="section-title">起始武器</div>
      <div className="run-weapon-list" data-testid="start-weapons">
        {options?.weapons.map((w) => (
          <Hint key={w.id} text={w.traits_zh.join("\n")}>
            <button
              type="button"
              className={`run-weapon${weapon === w.id ? " primary selected" : ""}`}
              disabled={disabled}
              onClick={() => picker.setWeapon(w.id)}
            >
              {w.name_zh}
              <span className="muted small">　{CLASS_LABELS[w.weapon_class] ?? w.weapon_class}</span>
            </button>
          </Hint>
        ))}
      </div>
      <div className="section-title">
        選 {count} 個關鍵字（{selected.length}/{count}）
      </div>
      <div className="muted small">每個關鍵字的技能池給你 1 招起始技能；技能之間靠「製造」與「利用」同一個關鍵字互相觸發。</div>
      <div className="run-keyword-list" data-testid="start-keywords">
        {previewOptions.map((o) => {
          const on = selected.includes(o.keyword.id);
          const available = keywordAvailable(o);
          return (
            <Hint key={o.keyword.id} text={o.keyword.description_zh}>
              <button
                type="button"
                className={`run-keyword${on ? " primary selected" : ""}${available ? "" : " unavailable"}`}
                disabled={disabled || !available || (!on && selected.length >= count)}
                onClick={() => picker.setSelected((cur) => toggleKeyword(cur, o.keyword.id, count))}
              >
                <b>{o.keyword.name_zh}</b>
                <span className="small">　{available ? o.skill?.name_zh : `${weaponDef?.name_zh ?? "這把武器"}沒有起始技能`}</span>
              </button>
            </Hint>
          );
        })}
      </div>
      {chosen.length > 0 && (
        <div className="run-start-preview" data-testid="start-preview">
          {chosen.map((o) =>
            o === undefined || o.skill === null || o.skill === undefined ? null : (
              <div key={o.keyword.id} className="run-start-preview-card">
                <div className="small muted">「{o.keyword.name_zh}」池的起始技能</div>
                <SkillCardView card={o.skill} compact />
              </div>
            ),
          )}
        </div>
      )}
    </>
  );
}

interface DevProps {
  picker: StartPicker;
  /** 有給 `onActive` 時顯示「改用起始包」勾選（工坊與裝備測試用）。 */
  active?: boolean;
  onActive?(on: boolean): void;
  disabled?: boolean;
  /** 有給時，起始包選單旁顯示「一鍵開局」按鈕。 */
  onGo?(): void;
}

/** 開發者起始包選單：只在 `?dev=1` 時存在。 */
export function DevPackSelect({ picker, active = false, onActive, disabled = false, onGo }: DevProps) {
  if (!picker.dev) return null;
  return (
    <div className="panel run-dev-packs" data-testid="dev-packs">
      <div className="section-title">開發者起始包（測試用，玩家看不到）</div>
      {onActive !== undefined && (
        <label>
          <input type="checkbox" checked={active} onChange={(e) => onActive(e.target.checked)} /> 改用起始包
        </label>
      )}
      <span className="seed-row">
        <select value={picker.packId} onChange={(e) => picker.setPackId(e.target.value)} disabled={disabled}>
          {picker.packs.map((p) => (
            <option key={p.id} value={p.id}>
              {p.label_zh}：{p.weapon_name_zh}＋{p.keywords.map((k) => k.name_zh).join("、")}
            </option>
          ))}
        </select>
        {onGo !== undefined && (
          <button type="button" disabled={disabled || picker.packId === ""} onClick={onGo}>
            一鍵開局
          </button>
        )}
      </span>
    </div>
  );
}
