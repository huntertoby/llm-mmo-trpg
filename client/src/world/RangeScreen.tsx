// 工坊靶場（Phase TR-1，#134；OB-5，#150；21 21.5、09 9.6.9、06 6.27.3）。三個模式（`range.ts` 的 `rangeMode`）：
// - `class`＝選大類（未完成開局，整頁；`RangeClassPick`）：三張大類卡，按「確定出發」送 `opening_class`。
// - `choose`＝正式選定（入門期打完新手前兩步；霧渡鎮導師堂的葛蘭與主城工坊靶場開同一個整頁）：選自己的武器與 2 個關鍵字，
//   按「確定選這套」送 `opening_confirm`。版面照 TR-1 的靶場（左預覽、中武器架、右關鍵字），多了「推薦」小牌、說話的人的頭像、
//   窄版黏底列。「拿起試打」帶普攻＋該大類 2 招示範招；每個關鍵字的「看示範」放那個關鍵字給的起始技能。
// - `reselect`＝4 級前的免費重選：畫面屬 OB-6，這裡只留位置（不畫）。
// 人物一律 Q 版（建角同一套 `LookPreview`）。文字與規則都來自伺服器（`WorldView.opening`、開局預覽、推薦查詢）。
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
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
import { RangeClassPick } from "./RangeClassPick";
import { RangeRackList, RangeSpeaker, RangeWeaponCard } from "./RangeParts";
import {
  ATTR_NOTE,
  CHOOSE_LABEL,
  CHOOSE_LATER,
  CHOOSE_WAIT,
  CLASS_LABELS,
  DEMO_LABEL,
  KEYWORD_NOTE,
  REC_LABEL,
  REC_NOTE,
  TRY_LABEL,
  chooseBarParts,
  choosePlaqueSub,
  demoKeywords,
  groupRacks,
  keywordState,
  readDraft,
  trialNote,
  writeClassDraft,
  writeDraft,
  type RangeMode,
} from "./range";

export { CONFIRM_LABEL } from "./range";

interface Props {
  view: WorldView;
  range: RangeView;
  mode: RangeMode;
  busy: boolean;
  error: string | null;
  onCloseError(): void;
  /** 開一場沙盒試打（`keywords` 空＝普攻＋示範招）。 */
  onTrial(weapon: string, keywords: string[]): void;
  /** 選大類的「確定出發」（送 `opening_class`）。 */
  onClass(weaponClass: string): void;
  /** 正式選定的「確定選這套」（送 `opening_confirm`）。 */
  onConfirm(weapon: string, keywords: string[]): void;
  /** 選大類的「先離開」。 */
  onHome(): void;
  /** 正式選定的「之後再選」（關掉這一頁，回到世界畫面）。 */
  onLater(): void;
}

export function RangeScreen(props: Props) {
  const { view, range, mode, busy, error, onCloseError } = props;
  if (mode === "class") {
    return <RangeClassPick view={view} range={range} busy={busy} error={error} onCloseError={onCloseError} onTrial={(w) => props.onTrial(w, [])} onConfirm={props.onClass} onHome={props.onHome} />;
  }
  // 重選（OB-6）還沒有畫面：不畫
  if (mode === "reselect") return null;
  return <RangeChoose {...props} />;
}

/** 照玩家當下選的那把武器查推薦的關鍵字（OB-3 的帶武器查詢）；查不到或還沒回來時用畫面資料裡那一份（入門武器的）。 */
function useRecommended(characterId: string, weapon: string, fallback: readonly string[]): readonly string[] {
  const [found, setFound] = useState<{ weapon: string; keywords: string[] } | null>(null);
  useEffect(() => {
    if (weapon === "") return undefined;
    let cancelled = false;
    api.worldRangeRecommend(characterId, weapon).then(
      (res) => !cancelled && setFound({ weapon: res.weapon, keywords: res.keywords }),
      () => !cancelled && setFound(null),
    );
    return () => {
      cancelled = true;
    };
  }, [characterId, weapon]);
  return found !== null && found.weapon === weapon ? found.keywords : fallback;
}

function RangeChoose({ view, range, busy, error, onCloseError, onTrial, onConfirm, onLater }: Props) {
  const charId = view.character.character_id;
  const choice = range.choice ?? null;
  const picker = useStartPicker(range.seed, false);
  const { options, weapon, selected, count, previewOptions, weaponDef } = picker;
  const restored = useRef(false);
  // 回到這一頁：一進畫面就接著上次選到一半的（不等選項載入，免得玩家先點的被蓋掉；關鍵字等預覽回來再由 `keepAvailable` 濾掉不能用的）
  useEffect(() => {
    if (restored.current) return;
    restored.current = true;
    const draft = readDraft(charId);
    if (draft === null) {
      // 第一次打開：先拿著手上的入門武器（玩家前兩場用的那一把），不是武器架的第一把
      const starter = range.racks.find((r) => r.weapon_class === range.weapon_class)?.starter_weapon;
      if (starter !== undefined) picker.setWeapon(starter);
      return;
    }
    picker.setWeapon(draft.weapon);
    picker.setSelected(() => draft.keywords.slice(0, count));
  }, [charId, count, picker, range.racks, range.weapon_class]);
  // 草稿裡的武器這一季沒有了：換回第一把
  useEffect(() => {
    if (options !== null && weapon !== "" && !options.weapons.some((w) => w.id === weapon)) picker.setWeapon(options.weapons[0]?.id ?? "");
  }, [options, weapon, picker]);
  useEffect(() => {
    if (restored.current && weapon !== "") writeDraft(charId, { weapon, keywords: selected });
  }, [charId, weapon, selected]);

  const recommended = useRecommended(charId, weapon, range.recommended_keywords ?? []);
  const racks = useMemo(() => groupRacks(options?.weapons ?? [], range.racks.map((r) => r.weapon_class)), [options, range.racks]);
  const demo = range.racks.find((r) => r.weapon_class === weaponDef?.weapon_class);
  const chosen = selected.map((id) => previewOptions.find((o) => o.keyword.id === id)).filter((o): o is StartKeywordOption => o !== undefined && o.skill != null);
  const ready = picker.body !== null && !busy;
  const race = view.character.race ?? null;
  // 等待提示只在按了「確定選這套」之後出（去試打的等待不算）；伺服器回來（成功或被拒）就收掉
  const [confirming, setConfirming] = useState(false);
  useEffect(() => {
    if (!busy) setConfirming(false);
  }, [busy]);
  const waiting = busy && confirming;
  const confirm = () => {
    if (picker.body === null) return;
    setConfirming(true);
    onConfirm(weapon, selected);
  };
  const tryButton = (primary: boolean) => (
    <button type="button" className={`${primary ? "primary " : ""}range-try`} disabled={busy || weapon === ""} onClick={() => onTrial(weapon, [])} data-testid={primary ? "range-try" : "range-bar-try"}>
      {TRY_LABEL}
    </button>
  );
  const laterButton = (testId: string) => (
    <button data-sfx="ui_cancel" type="button" disabled={busy} onClick={onLater} data-testid={testId}>
      {CHOOSE_LATER}
    </button>
  );
  const goButton = (testId: string) => (
    <button type="button" className="primary entry-create-go" disabled={!ready} onClick={confirm} data-testid={testId}>
      {CHOOSE_LABEL}
    </button>
  );
  const pickedNames = selected.map((id) => previewOptions.find((o) => o.keyword.id === id)?.keyword.name_zh ?? id);
  const bar = chooseBarParts(weaponDef?.name_zh ?? "", pickedNames, count);
  const problem = error ?? picker.error;

  return (
    <EntryShell className="world-range ob-choose-page" testId="world-range">
      <EntryPlaque heading="正式選定" sub={choosePlaqueSub(choice?.place_zh ?? "", count)} />
      <ErrorBanner message={problem} onClose={onCloseError} />
      <EntryPanel className="range-keeper" testId="range-keeper">
        <RangeSpeaker speaker={choice?.speaker} lines={choice?.lines ?? []} />
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
          <RangeRackList racks={racks} weapon={weapon} busy={busy} onPick={(id) => picker.setWeapon(id)} />
          {weaponDef !== undefined && (
            <RangeWeaponCard weapon={weaponDef} stats note={demo === undefined ? null : trialNote(demo.name_zh, demo.skills, false)}>
              <span className="ob-wide-only">{tryButton(true)}</span>
            </RangeWeaponCard>
          )}
        </EntryPanel>
        <EntryPanel className="range-keywords" testId="range-keywords">
          <div className="section-title">
            選 {count} 個關鍵字（{selected.length}/{count}）
          </div>
          <div className="muted small" data-testid="range-keyword-note">
            {KEYWORD_NOTE}
            {recommended.length > 0 && REC_NOTE}
          </div>
          <div className="range-keyword-list" data-testid="range-keyword-list">
            {previewOptions.map((o) => {
              const on = selected.includes(o.keyword.id);
              const available = keywordAvailable(o);
              const rec = recommended.includes(o.keyword.id);
              return (
                <div key={o.keyword.id} className={`range-keyword${on ? " selected" : ""}`} data-keyword={o.keyword.id} data-state={`${keywordState(on, rec)}${available ? "" : "-off"}`}>
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
                      {rec && (
                        <span className="ob-rec" data-testid="range-rec">
                          {REC_LABEL}
                        </span>
                      )}
                    </button>
                  </Hint>
                  <button type="button" className="small-button range-demo" disabled={busy || !available || weapon === ""} onClick={() => onTrial(weapon, demoKeywords(selected, o.keyword.id, count))} data-testid={`range-demo-${o.keyword.id}`}>
                    {DEMO_LABEL}
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
            {ATTR_NOTE}
          </div>
          {problem !== null && (
            <div className="small range-problem" role="alert" data-testid="range-problem">
              {problem}
            </div>
          )}
          {waiting && (
            <div className="small range-wait" role="status" data-testid="range-wait">
              {CHOOSE_WAIT}
            </div>
          )}
          <div className="run-actions entry-actions ob-wide-only">
            {laterButton("range-later")}
            {goButton("range-confirm")}
          </div>
        </EntryPanel>
      </div>
      {/* 窄版（< 1040）：三塊直排後很長，「拿起試打」與兩顆確認鈕收進黏底列，不用捲過整個武器架 */}
      <EntryPanel className="ob-choose-bar ob-narrow-only" testId="range-choose-bar">
        <div className={`ob-bar-text small${!waiting && problem !== null ? " ob-bar-problem" : ""}`} data-testid="range-bar-text">
          <b>{bar[0]}</b>　{waiting ? CHOOSE_WAIT : (problem ?? bar[1])}
        </div>
        <div className="ob-bar-actions">
          {tryButton(false)}
          {laterButton("range-bar-later")}
          {goButton("range-bar-confirm")}
        </div>
      </EntryPanel>
    </EntryShell>
  );
}

/** 確定出發之後守印人說的話（`range.done`）：接回主城廣場，指示去霧渡鎮找渡婆婆。 */
export function rangeDoneLines(range: RangeView | null | undefined): { speaker_zh: string; text_zh: string }[] {
  return range == null ? [] : [...(range.done ?? [])];
}

/** 正式選定完成之後說的話（`range.choice.done`：葛蘭收回入門配備；在主城選時是守印人那一句）。 */
export function chooseDoneLines(range: RangeView | null | undefined): { speaker_zh: string; text_zh: string }[] {
  return [...(range?.choice?.done ?? [])];
}

/** 清掉這個角色的草稿（確定出發、正式選定之後）。 */
export function clearRangeDraft(characterId: string): void {
  writeDraft(characterId, null);
  writeClassDraft(characterId, null);
}

/** 確定出發、正式選定之後那段話：共用彈窗外框（DialogFrame），按鈕關掉。 */
export function RangeDoneDialog({ lines, heading = "工坊靶場", closeLabel = "出發", onClose }: { lines: readonly { speaker_zh: string; text_zh: string }[]; heading?: string; closeLabel?: string; onClose(): void }) {
  return (
    <DialogFrame label="靶場" title={heading}>
      <div className="world-opening" data-testid="range-done">
        {lines.map((line, i) => (
          <p key={i} className="world-opening-line">
            <b>{line.speaker_zh}</b>：{line.text_zh}
          </p>
        ))}
      </div>
      <div className="modal-buttons">
        <button type="button" className="primary" onClick={onClose} data-testid="range-done-close" autoFocus>
          {closeLabel}
        </button>
      </div>
    </DialogFrame>
  );
}
