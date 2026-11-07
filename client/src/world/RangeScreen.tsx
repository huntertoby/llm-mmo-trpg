// 主城工坊靶場（Phase TR-1，#134；21 21.5、09 9.6.9、06 6.27.3）：新角色在這裡試武器、選武器與 2 個關鍵字，按「確定出發」才算完成開局。
// - 武器架照近戰、遠程、法器排（伺服器給順序）；點武器看介紹與該大類的 2 招示範招，「拿起試打」開一場沙盒（既有戰鬥畫面，打完回到這裡）。
// - 關鍵字：每個都能「看示範」（用選的武器施放那招起始技能的沙盒）；選滿 2 個顯示兩招與觸發關係、推薦配法。
// - 「確定出發」前都能改；中途離開（關掉、去試打）回來時接著選（本機草稿，`range.ts`）。
// - 人物一律 Q 版：預覽用建角同一套 `LookPreview`（拿著選的武器）。文字與規則都來自伺服器（`WorldView.opening`、開局預覽）。
import { useEffect, useMemo, useRef } from "react";
import type { RangeView, StartKeywordOption, WorldView } from "../api/types";
import { LookPreview } from "../run/LookPicker";
import { startLinksText, useStartPicker } from "../run/StartPicker";
import { keywordAvailable, toggleKeyword } from "../run/startFlow";
import { KeywordIcon } from "../ui/CreateIcons";
import { EntryPanel, EntryPlaque, EntryShell } from "../ui/EntryShell";
import { DialogFrame } from "../ui/DialogFrame";
import { ErrorBanner } from "../ui/ErrorBanner";
import { Hint } from "../ui/Hint";
import { SkillCardView } from "../ui/SkillCardView";
import { WeaponIcon } from "../ui/WeaponIcon";
import { CLASS_LABELS, demoKeywords, groupRacks, readDraft, writeDraft } from "./range";

interface Props {
  view: WorldView;
  range: RangeView;
  busy: boolean;
  error: string | null;
  onCloseError(): void;
  /** 開一場沙盒試打（`keywords` 空＝普攻＋示範招）。 */
  onTrial(weapon: string, keywords: string[]): void;
  /** 確定出發（送 `opening_confirm`）。 */
  onConfirm(weapon: string, keywords: string[]): void;
  onHome(): void;
}

export const CONFIRM_LABEL = "確定出發";

export function RangeScreen({ view, range, busy, error, onCloseError, onTrial, onConfirm, onHome }: Props) {
  const charId = view.character.character_id;
  const picker = useStartPicker(range.seed, false);
  const { options, weapon, selected, count, previewOptions, weaponDef } = picker;
  const restored = useRef(false);
  // 回到靶場：一進畫面就接著上次選到一半的（不等選項載入，免得玩家先點的被蓋掉；關鍵字等預覽回來再由 `keepAvailable` 濾掉不能用的）
  useEffect(() => {
    if (restored.current) return;
    restored.current = true;
    const draft = readDraft(charId);
    if (draft === null) return;
    picker.setWeapon(draft.weapon);
    picker.setSelected(() => draft.keywords.slice(0, count));
  }, [charId, count, picker]);
  // 草稿裡的武器這一季沒有了：換回第一把
  useEffect(() => {
    if (options !== null && weapon !== "" && !options.weapons.some((w) => w.id === weapon)) picker.setWeapon(options.weapons[0]?.id ?? "");
  }, [options, weapon, picker]);
  useEffect(() => {
    if (restored.current && weapon !== "") writeDraft(charId, { weapon, keywords: selected });
  }, [charId, weapon, selected]);

  const racks = useMemo(() => groupRacks(options?.weapons ?? [], range.racks.map((r) => r.weapon_class)), [options, range.racks]);
  const demo = range.racks.find((r) => r.weapon_class === weaponDef?.weapon_class);
  const chosen = selected.map((id) => previewOptions.find((o) => o.keyword.id === id)).filter((o): o is StartKeywordOption => o !== undefined && o.skill != null);
  const ready = picker.body !== null && !busy;
  const race = view.character.race ?? null;

  return (
    <EntryShell className="world-range" testId="world-range">
      <EntryPlaque heading="工坊靶場" sub="主城・選好兵器再出發" />
      <ErrorBanner message={error ?? picker.error} onClose={onCloseError} />
      <EntryPanel className="range-keeper" testId="range-keeper">
        {range.intro.map((line, i) => (
          <p key={i} className="world-opening-line">
            <b>{line.speaker_zh}</b>：{line.text_zh}
          </p>
        ))}
        <p className="muted small range-sandbox-note">
          試打是沙盒：不算勝負、不給經驗與掉落、不耗 HP 與法力。木樁 {range.dummies.length} 個：{range.dummies.map((d) => d.label_zh).join("、")}。按「{CONFIRM_LABEL}」前都能改。
        </p>
      </EntryPanel>
      <div className="range-body">
        <EntryPanel className="range-preview" testId="range-preview">
          <div className="section-title">{view.character.name}</div>
          <div className="range-preview-slot">
            {race !== null ? <LookPreview race={race} choice={view.character.look ?? {}} weaponId={weapon === "" ? null : weapon} height={200} /> : <span className="muted small">（沒有種族）</span>}
          </div>
          <div className="range-preview-weapon small">{weaponDef === undefined ? "還沒拿武器" : `手上：${weaponDef.name_zh}（${CLASS_LABELS[weaponDef.weapon_class] ?? weaponDef.weapon_class}）`}</div>
        </EntryPanel>
        <EntryPanel className="range-racks" testId="range-racks">
          <div className="section-title">武器架</div>
          {racks.map((rack) => (
            <div key={rack.weaponClass} className="range-rack" data-rack={rack.weaponClass}>
              <div className="range-rack-name small">{rack.name}</div>
              <div className="run-weapon-list">
                {rack.weapons.map((w) => (
                  <Hint key={w.id} text={w.traits_zh.join("\n")}>
                    <button type="button" className={`run-weapon${weapon === w.id ? " primary selected" : ""}`} disabled={busy} onClick={() => picker.setWeapon(w.id)} data-testid={`range-weapon-${w.id}`}>
                      <WeaponIcon weaponId={w.id} weaponClass={w.weapon_class} size={20} />
                      {w.name_zh}
                    </button>
                  </Hint>
                ))}
              </div>
            </div>
          ))}
          {weaponDef !== undefined && (
            <div className="range-weapon-card" data-testid="range-weapon-card">
              <div>
                <b>{weaponDef.name_zh}</b>
                <span className="muted small">　{CLASS_LABELS[weaponDef.weapon_class] ?? weaponDef.weapon_class}・HP {weaponDef.hp}・法力 {weaponDef.mana}</span>
              </div>
              {weaponDef.traits_zh.length > 0 && <div className="small">{weaponDef.traits_zh.join("；")}</div>}
              {demo !== undefined && (
                <div className="small muted">
                  試打用：普攻＋{demo.name_zh}示範招 {demo.skills.map((s) => s.name_zh).join("、")}（選完收回、不進技能庫）
                </div>
              )}
              <button type="button" className="primary range-try" disabled={busy} onClick={() => onTrial(weapon, [])} data-testid="range-try">
                拿起試打
              </button>
            </div>
          )}
        </EntryPanel>
        <EntryPanel className="range-keywords" testId="range-keywords">
          <div className="section-title">
            選 {count} 個關鍵字（{selected.length}/{count}）
          </div>
          <div className="muted small">每個關鍵字給 1 招起始技能；第 2 招優先挑能利用第 1 個關鍵字的招。都能先「看示範」。</div>
          <div className="range-keyword-list" data-testid="range-keyword-list">
            {previewOptions.map((o) => {
              const on = selected.includes(o.keyword.id);
              const available = keywordAvailable(o);
              return (
                <div key={o.keyword.id} className={`range-keyword${on ? " selected" : ""}`} data-keyword={o.keyword.id}>
                  <Hint text={o.keyword.description_zh}>
                    <button
                      type="button"
                      className={`run-keyword${on ? " primary selected" : ""}${available ? "" : " unavailable"}`}
                      disabled={busy || !available || (!on && selected.length >= count)}
                      onClick={() => picker.setSelected((cur) => toggleKeyword(cur, o.keyword.id, count))}
                    >
                      <KeywordIcon id={o.keyword.id} />
                      <b>{o.keyword.name_zh}</b>
                      <span className="small">　{available ? o.skill?.name_zh : `${weaponDef?.name_zh ?? "這把武器"}沒有起始技能`}</span>
                    </button>
                  </Hint>
                  <button type="button" className="small-button range-demo" disabled={busy || !available || weapon === ""} onClick={() => onTrial(weapon, demoKeywords(selected, o.keyword.id, count))} data-testid={`range-demo-${o.keyword.id}`}>
                    看示範
                  </button>
                </div>
              );
            })}
          </div>
          {chosen.length >= count && (
            <div className={`small run-start-links${picker.links.length === 0 ? " muted" : ""}`} data-testid="range-links">
              {startLinksText(picker.links)}
            </div>
          )}
          {chosen.length > 0 && (
            <div className="run-start-preview" data-testid="range-starters">
              {chosen.map((o) =>
                o.skill == null ? null : (
                  <div key={o.keyword.id} className="run-start-preview-card">
                    <div className="small muted">「{o.keyword.name_zh}」給的起始技能</div>
                    <SkillCardView card={o.skill} compact />
                  </div>
                ),
              )}
            </div>
          )}
          <div className="small entry-note" data-testid="range-attrs">
            {picker.recommendedZh === "" ? "屬性：選完武器和兩個關鍵字後，開局 4 點照推薦配法自動配好。" : `屬性：${picker.recommendedZh}（照推薦配法自動配好）。`}
            <span className="muted">之後導師會教你自己配。</span>
          </div>
          <div className="run-actions entry-actions">
            <button data-sfx="ui_cancel" type="button" onClick={onHome}>
              先離開（下次回到靶場）
            </button>
            <button
              type="button"
              className="primary entry-create-go"
              disabled={!ready}
              onClick={() => {
                if (picker.body === null) return;
                onConfirm(weapon, selected);
              }}
              data-testid="range-confirm"
            >
              {CONFIRM_LABEL}
            </button>
          </div>
        </EntryPanel>
      </div>
    </EntryShell>
  );
}

/** 確定出發之後守印人說的話（`range.done`）：接回主城廣場，指示去霧渡鎮找渡婆婆。 */
export function rangeDoneLines(range: RangeView | null | undefined): { speaker_zh: string; text_zh: string }[] {
  return range == null ? [] : [...range.done];
}

/** 清掉這個角色的草稿（確定出發之後）。 */
export function clearRangeDraft(characterId: string): void {
  writeDraft(characterId, null);
}

/** 確定出發之後（回到主城廣場）守印人那段話：共用彈窗外框（DialogFrame），按「出發」關掉。 */
export function RangeDoneDialog({ lines, onClose }: { lines: readonly { speaker_zh: string; text_zh: string }[]; onClose(): void }) {
  return (
    <DialogFrame label="靶場" title="工坊靶場">
      <div className="world-opening" data-testid="range-done">
        {lines.map((line, i) => (
          <p key={i} className="world-opening-line">
            <b>{line.speaker_zh}</b>：{line.text_zh}
          </p>
        ))}
      </div>
      <div className="modal-buttons">
        <button type="button" className="primary" onClick={onClose} data-testid="range-done-close" autoFocus>
          出發
        </button>
      </div>
    </DialogFrame>
  );
}
