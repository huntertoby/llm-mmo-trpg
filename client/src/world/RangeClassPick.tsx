// 工坊靶場「選大類」（OB-5，#150 第 1 點；樣張 docs/art/sample/ob-range-class.html、docs/art/OB與PR樣張.md 第 1、6 節）：
// 新角色醒來先選近戰、遠程或法器。三張大類卡（Q 版人物拿入門武器、入門武器、2 招入門招與一句說明、代價）、下方一列「試其他武器」
// （按了在同頁展開整個武器架，架上每把都能試打；確定出發只記大類）、確認列（未選時停用；窄版黏在底部）。
// 入門武器、入門招、台詞、頭像全部來自伺服器（`RangeView`：`racks`、`intro`、`loan`、`keeper`），這裡不寫死技能 ID 或招名。
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import type { RangeView, StartOptions, WorldView } from "../api/types";
import { LookPreview } from "../run/LookPicker";
import { weaponIconItem } from "../render/weaponIcon";
import { EntryPanel, EntryPlaque, EntryShell } from "../ui/EntryShell";
import { ErrorBanner } from "../ui/ErrorBanner";
import { GearIcon } from "../ui/GearIcon";
import { PopupFrame } from "../ui/PopupFrame";
import { SkillIconView } from "../ui/SkillIconView";
import { RangeRackList, RangeSpeaker, RangeWeaponCard } from "./RangeParts";
import { CLASS_PLAQUE_SUB, CLASS_TAGS, CONFIRM_EMPTY, CONFIRM_LABEL, LOAN_NOTE, RACK_NOTE, TRY_LABEL, confirmParts, costLine, groupRacks, readClassDraft, trialNote, writeClassDraft } from "./range";

type RackDemo = RangeView["racks"][number];

interface Props {
  view: WorldView;
  range: RangeView;
  busy: boolean;
  error: string | null;
  onCloseError(): void;
  /** 開一場沙盒試打（普攻＋該大類 2 招入門招）。 */
  onTrial(weapon: string): void;
  /** 確定出發（送 `opening_class`）。 */
  onConfirm(weaponClass: string): void;
  onHome(): void;
}

interface CardProps {
  rack: RackDemo;
  view: WorldView;
  selected: boolean;
  busy: boolean;
  onPick(): void;
  onTrial(): void;
}

function ClassCard({ rack, view, selected, busy, onPick, onTrial }: CardProps) {
  const race = view.character.race ?? null;
  return (
    <PopupFrame placement={{ kind: "inline" }} className={`entry-panel ob-class-card${selected ? " selected" : ""}`} testId={`range-class-${rack.weapon_class}`}>
      <div
        className="ob-class-hit"
        role="button"
        tabIndex={0}
        aria-pressed={selected}
        data-class={rack.weapon_class}
        onClick={onPick}
        onKeyDown={(e) => {
          if (e.target === e.currentTarget && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            onPick();
          }
        }}
      >
        <div className="ob-class-head">
          <span className="ob-class-name">{rack.name_zh}</span>
          <span className="ob-class-tag">{CLASS_TAGS[rack.weapon_class] ?? ""}</span>
          {selected && <span className="ob-class-state">✓ 已選</span>}
        </div>
        <div className="ob-class-top">
          <div className="range-preview-slot">
            {race !== null ? <LookPreview race={race} choice={view.character.look ?? {}} weaponId={rack.starter_weapon} height={164} facings={false} /> : <span className="muted small">（沒有種族）</span>}
          </div>
          <div className="ob-kit">
            <div className="ob-kit-label">
              入門武器<span className="ob-loan">借</span>
            </div>
            <div className="ob-kit-row" data-testid="range-class-weapon">
              <GearIcon look={weaponIconItem(rack.starter_weapon, rack.weapon_class)} slot="main_hand" size={48} label={rack.starter_weapon_zh} />
              <div className="ob-kit-text">
                <b>{rack.starter_weapon_zh}</b>
              </div>
            </div>
            <div className="ob-kit-label">
              入門招<span className="ob-loan">借</span>
            </div>
            {rack.skills.map((s) => (
              <div key={s.id} className="ob-kit-row" data-testid="range-class-skill">
                <SkillIconView icon={s.icon} size={40} label={s.name_zh} />
                <div className="ob-kit-text">
                  <b>{s.name_zh}</b>
                  <span>{rack.blurbs_zh?.[s.id] ?? ""}</span>
                  <span className="ob-kit-cost-in">{costLine(s)}</span>
                </div>
                <span className="ob-kit-cost">{costLine(s)}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="ob-loan-note">{LOAN_NOTE}</div>
        <div className="ob-class-foot">
          <button
            type="button"
            className="range-try"
            disabled={busy}
            onClick={(e) => {
              e.stopPropagation();
              onTrial();
            }}
            data-testid={`range-class-try-${rack.weapon_class}`}
          >
            {TRY_LABEL}
          </button>
          <button
            type="button"
            className={`ob-pick${selected ? " selected" : ""}`}
            aria-pressed={selected}
            onClick={(e) => {
              e.stopPropagation();
              onPick();
            }}
            data-testid={`range-class-pick-${rack.weapon_class}`}
          >
            {selected ? "已選這條路" : "選這條路"}
          </button>
        </div>
      </div>
    </PopupFrame>
  );
}

export function RangeClassPick({ view, range, busy, error, onCloseError, onTrial, onConfirm, onHome }: Props) {
  const charId = view.character.character_id;
  const [picked, setPicked] = useState<string | null>(null);
  const [rackOpen, setRackOpen] = useState(false);
  const [rackWeapon, setRackWeapon] = useState("");
  const [options, setOptions] = useState<StartOptions | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const restored = useRef(false);
  // 去試打回來：接著上次選到一半的（本機草稿）
  useEffect(() => {
    if (restored.current) return;
    restored.current = true;
    const draft = readClassDraft(charId);
    if (draft === null) return;
    if (draft.picked !== null && range.racks.some((r) => r.weapon_class === draft.picked)) setPicked(draft.picked);
    setRackOpen(draft.rackOpen);
    setRackWeapon(draft.rackWeapon);
  }, [charId, range.racks]);
  useEffect(() => {
    if (restored.current) writeClassDraft(charId, { picked, rackOpen, rackWeapon });
  }, [charId, picked, rackOpen, rackWeapon]);
  // 武器架打開時才讀武器清單
  useEffect(() => {
    if (!rackOpen || options !== null) return;
    let cancelled = false;
    api.startOptions().then(
      (o) => !cancelled && setOptions(o),
      (e: unknown) => !cancelled && setLoadError(e instanceof Error ? e.message : String(e)),
    );
    return () => {
      cancelled = true;
    };
  }, [rackOpen, options]);

  const racks = useMemo(() => groupRacks(options?.weapons ?? [], range.racks.map((r) => r.weapon_class)), [options, range.racks]);
  const pickedRack = range.racks.find((r) => r.weapon_class === picked);
  const shownWeapon = options?.weapons.find((w) => w.id === rackWeapon);
  const shownDemo = range.racks.find((r) => r.weapon_class === shownWeapon?.weapon_class);
  const confirm = pickedRack === undefined ? null : confirmParts(pickedRack.name_zh, pickedRack.starter_weapon_zh, pickedRack.skills);

  return (
    <EntryShell className="world-range ob-class-pick" testId="world-range">
      <EntryPlaque heading="工坊靶場" sub={CLASS_PLAQUE_SUB} />
      <ErrorBanner message={error ?? loadError} onClose={onCloseError} />
      <EntryPanel className="range-keeper" testId="range-keeper">
        <RangeSpeaker speaker={range.keeper} lines={range.intro ?? []} extra={picked !== null ? (range.loan ?? []) : []} />
      </EntryPanel>
      <div className="ob-class-grid" data-testid="range-class-grid">
        {range.racks.map((rack) => (
          <ClassCard key={rack.weapon_class} rack={rack} view={view} selected={picked === rack.weapon_class} busy={busy} onPick={() => setPicked(rack.weapon_class)} onTrial={() => onTrial(rack.starter_weapon)} />
        ))}
      </div>
      <EntryPanel className={`ob-rack-panel${rackOpen ? " open" : ""}`} testId="range-rack-panel">
        <div className="ob-rack-head">
          <div className="ob-rack-text">
            <b>武器架</b>
            <span className="small muted">{RACK_NOTE}</span>
          </div>
          <button type="button" className={`ob-rack-toggle${rackOpen ? " selected" : ""}`} aria-expanded={rackOpen} onClick={() => setRackOpen((v) => !v)} data-testid="range-rack-toggle">
            {rackOpen ? "收起武器架" : "試其他武器"}
          </button>
        </div>
        {rackOpen && (
          <div className="ob-rack-body" data-testid="range-racks">
            {options === null ? <div className="muted small">讀取武器架……</div> : <RangeRackList racks={racks} weapon={rackWeapon} busy={busy} onPick={setRackWeapon} />}
            {shownWeapon !== undefined && (
              <RangeWeaponCard weapon={shownWeapon} stats={false} note={shownDemo === undefined ? null : trialNote(shownDemo.name_zh, shownDemo.skills, true)}>
                <button type="button" className="primary range-try" disabled={busy} onClick={() => onTrial(shownWeapon.id)} data-testid="range-try">
                  {TRY_LABEL}
                </button>
              </RangeWeaponCard>
            )}
          </div>
        )}
      </EntryPanel>
      <EntryPanel className="ob-confirm-panel" testId="range-confirm-panel">
        <div className="ob-confirm">
          <div className="ob-confirm-text small" data-testid="range-confirm-text">
            {confirm === null ? (
              <span className="muted">{CONFIRM_EMPTY}</span>
            ) : (
              <>
                <b>{confirm[0]}</b>　{confirm[1]}
              </>
            )}
          </div>
          <div className="ob-actions">
            <button data-sfx="ui_cancel" type="button" onClick={onHome} data-testid="range-leave">
              <span className="ob-leave-full">先離開（下次回到靶場）</span>
              <span className="ob-leave-short">先離開</span>
            </button>
            <button type="button" className="primary entry-create-go" disabled={picked === null || busy} onClick={() => picked !== null && onConfirm(picked)} data-testid="range-confirm">
              {CONFIRM_LABEL}
            </button>
          </div>
        </div>
      </EntryPanel>
    </EntryShell>
  );
}
