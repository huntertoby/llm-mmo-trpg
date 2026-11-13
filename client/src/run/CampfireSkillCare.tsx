// 營火的技能整理（Phase 3W-6）：重閃、溶掉、傳承。重閃與溶掉／傳承只在營火（06 6.34.3）。
// 溶掉與傳承是處理「舊技能」的二選一：選一招舊技能，再決定溶掉（退回花費的一半）或把小變化傳給新技能（舊技能消失、不退點）。
import { useState } from "react";
import type { RunChoice, RunHero } from "../api/types";
import { Hint } from "../ui/Hint";
import { EmptyNote, KeepNum } from "../ui/PanelKit";
import { SkillFlashInfo } from "../ui/SkillFlashInfo";
import { NoBreakText } from "./FlashChoiceParts";
import { FlashChooser, type FlashPreviewLoader } from "./FlashChooser";
import {
  carryable,
  dissolveChoice,
  dissolveConfirm,
  INHERIT_RULE_TEXT,
  inheritChoice,
  inheritProblem,
  inheritTargets,
  maxCarry,
  ownedSkills,
  recordLine,
  reflashable,
  reflashSlots,
  rulesOf,
  toggleCarry,
  TRANSFORM_HINT,
} from "./flash";
import { weakerSlot } from "./reflashWeaker";

interface Props {
  runId: string;
  hero: RunHero;
  busy: boolean;
  onChoose(choice: RunChoice): Promise<number | null>;
  /** 閃現預覽的來源（大世界）；省略 ＝ 一輪的端點。 */
  previewFlash?: FlashPreviewLoader;
  /** 標題裡的地點說明（大世界：「只在城鎮與營火」）；省略 ＝「只在營火」。 */
  place?: string;
  /** PNL-2：放進資訊面板的摺疊裡（摺疊列就是標題）：不畫 `.panel` 外框與區塊標題，原段落照舊。省略＝一輪營火的排法。 */
  bare?: boolean;
}

export function CampfireSkillCare({ runId, hero, busy, onChoose, previewFlash, place = "只在營火" }: Props) {
  return (
    <div className="campfire-care" data-testid="campfire-care">
      <ReflashSection runId={runId} hero={hero} busy={busy} onChoose={onChoose} previewFlash={previewFlash} place={place} />
      <OldSkillSection hero={hero} busy={busy} onChoose={onChoose} place={place} />
    </div>
  );
}

// ---- 重閃 --------------------------------------------------------------------------------

/**
 * 重閃清單空的時候（PNL-2 美術驗收可修 1）：虛線空狀態 `EmptyNote`。成長面板（`bare`，摺疊右邊已有「還沒有可以重閃的技能」標籤）
 * 只寫原因；一輪營火（沒有標籤）照原句。
 */
export function reflashEmptyText(bare: boolean): string {
  return bare ? "要先閃現過，或有完整技能。" : "還沒有可以重閃的技能（要先閃現過，或有完整技能）。";
}

/** 重閃說明（字照原句；PNL-4 起經 `KeepNum`，「點出 4 個」這類數字不和前面的詞分開）。 */
export function reflashNoteText(flashRules: RunHero["flash_rules"]): string {
  const r = rulesOf(flashRules);
  return `把一招以前某一次的變化換掉，價格和閃現相同（${r.open_cost} 點出 ${r.open_options} 個；指定類別 ${r.focused_cost} 點出 ${r.focused_options} 個）。不需要先上場用過，也不增加閃現次數；新選項整招不會比現在弱（轉型除外）；標 ▼ 的是換掉後變小的地方。`;
}

export function ReflashSection({ runId, hero, busy, onChoose, previewFlash, place = "只在營火", bare = false }: Props) {
  const [target, setTarget] = useState<{ id: string; slot: number } | null>(null);
  const list = reflashable(hero);
  const chosen = target === null ? undefined : list.find((s) => s.card.id === target.id);
  const slotLabel = chosen === undefined || target === null ? undefined : reflashSlots(chosen.flash).find((s) => s.slot === target.slot)?.label;
  return (
    <div className={bare ? "campfire-reflash" : "panel campfire-reflash"} data-testid="campfire-reflash">
      {!bare && <div className="section-title">重閃（{place}）</div>}
      <p className="small muted">
        <KeepNum text={reflashNoteText(hero.flash_rules)} />
      </p>
      {chosen !== undefined && target !== null && (
        <FlashChooser
          key={`${target.id}:${target.slot}`}
          runId={runId}
          previewFlash={previewFlash}
          hero={hero}
          skillId={target.id}
          skillName={chosen.card.name_zh}
          slot={target.slot}
          slotLabel={slotLabel}
          weaker={weakerSlot(chosen.flash, target.slot)}
          busy={busy}
          onChoose={async (c) => {
            const status = await onChoose(c);
            if (status === null) setTarget(null);
            return status;
          }}
          onCancel={() => setTarget(null)}
        />
      )}
      {list.length === 0 && <EmptyNote testId="reflash-empty">{reflashEmptyText(bare)}</EmptyNote>}
      <ul className="flash-skill-list" data-testid="reflash-list">
        {list.map(({ card, flash }) => (
          <li key={card.id} className="reflash-row">
            <div>
              <b>{card.name_zh}</b>
              <SkillFlashInfo flash={flash} rules={hero.flash_rules} brief />
            </div>
            <div className="reflash-slots">
              {reflashSlots(flash).map((s) => (
                <button
                  key={s.slot}
                  type="button"
                  className={target?.id === card.id && target.slot === s.slot ? "primary" : ""}
                  disabled={busy || s.none || (hero.insight ?? 0) < rulesOf(hero.flash_rules).open_cost}
                  data-testid={`reflash-${card.id}-${s.slot}`}
                  data-reflash-none={s.none ? 1 : undefined}
                  data-reflash-weaker={weakerSlot(flash, s.slot) !== null ? 1 : undefined}
                  onClick={() => setTarget({ id: card.id, slot: s.slot })}
                >
                  重閃　{s.label}
                  {s.transformHint && (
                    <span className="skill-flash-transform small">
                      {"　"}
                      <NoBreakText text={TRANSFORM_HINT} />
                    </span>
                  )}
                  <WeakerNote warn={weakerSlot(flash, s.slot)?.warn} testId={`reflash-weaker-${card.id}-${s.slot}`} />
                  {s.problem !== null && (
                    <span className="flash-none-note small" data-testid={`reflash-none-${card.id}-${s.slot}`}>
                      {s.problem}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** RR-2（#160）：較弱重閃格入口的提醒字（變弱樣式：無底無框＋▼）；不是較弱的格子不佔位。 */
function WeakerNote({ warn, testId }: { warn: string | undefined; testId: string }) {
  if (warn === undefined) return null;
  return (
    <span className="reflash-weaker-note" data-testid={testId}>
      <i className="fc-down" aria-label="變弱" />
      {warn}
    </span>
  );
}

// ---- 溶掉／傳承 --------------------------------------------------------------------------

type Mode = "dissolve" | "inherit";

export function OldSkillSection({ hero, busy, onChoose, place = "只在營火", bare = false }: Omit<Props, "runId">) {
  const [oldId, setOldId] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode | null>(null);
  const skills = ownedSkills(hero);
  const old = skills.find((s) => s.card.id === oldId);
  function pickOld(id: string) {
    setOldId(oldId === id ? null : id);
    setMode(null);
  }
  return (
    <div className={bare ? "campfire-old" : "panel campfire-old"} data-testid="campfire-old">
      {!bare && <div className="section-title">溶掉或傳承（二選一，{place}）</div>}
      <p className="small muted">
        選一招舊技能，然後二選一：<b>溶掉</b>（退回花在它身上的靈感點的一半）或<b>傳承</b>（把它的小變化帶給另一招新技能）。兩種都會讓舊技能消失。
      </p>
      <ul className="flash-skill-list" data-testid="old-skill-list">
        {skills.map(({ card, flash, equipped }) => (
          <li key={card.id} className="reflash-row">
            <div>
              <b>{card.name_zh}</b>
              {!equipped && <span className="muted small">（備用）</span>}
              <span className="muted small">　花費 {flash?.spent ?? 0} 點</span>
              <SkillFlashInfo flash={flash} rules={hero.flash_rules} brief />
            </div>
            <button
              type="button"
              className={oldId === card.id ? "primary" : ""}
              disabled={busy}
              data-testid={`old-pick-${card.id}`}
              onClick={() => pickOld(card.id)}
            >
              {oldId === card.id ? "已選（再按取消）" : "選這招"}
            </button>
          </li>
        ))}
      </ul>
      {old !== undefined && (
        <div className="old-actions" data-testid="old-actions">
          <div className="small">
            處理「<b>{old.card.name_zh}</b>」：
          </div>
          <div className="run-actions">
            <button type="button" className={mode === "dissolve" ? "primary" : ""} disabled={busy} data-testid="old-mode-dissolve" onClick={() => setMode("dissolve")}>
              溶掉（退 {old.flash?.dissolve_refund ?? 0} 點）
            </button>
            <InheritModeButton hero={hero} oldId={old.card.id} mode={mode} busy={busy} onMode={setMode} />
          </div>
          {mode === "dissolve" && (
            <DissolveConfirm
              hero={hero}
              oldId={old.card.id}
              busy={busy}
              onCancel={() => setMode(null)}
              onChoose={async (c) => {
                const status = await onChoose(c);
                if (status === null) {
                  setOldId(null);
                  setMode(null);
                }
                return status;
              }}
            />
          )}
          {mode === "inherit" && (
            <InheritForm
              hero={hero}
              sourceId={old.card.id}
              busy={busy}
              onCancel={() => setMode(null)}
              onChoose={async (c) => {
                const status = await onChoose(c);
                if (status === null) {
                  setOldId(null);
                  setMode(null);
                }
                return status;
              }}
            />
          )}
        </div>
      )}
    </div>
  );
}

function InheritModeButton({ hero, oldId, mode, busy, onMode }: { hero: RunHero; oldId: string; mode: Mode | null; busy: boolean; onMode(m: Mode): void }) {
  const source = ownedSkills(hero).find((s) => s.card.id === oldId);
  const reason = inheritProblem(source?.flash);
  return (
    <Hint text={reason}>
      <button type="button" className={mode === "inherit" ? "primary" : ""} disabled={busy || reason !== undefined} data-testid="old-mode-inherit" onClick={() => onMode("inherit")}>
        傳承給另一招
      </button>
    </Hint>
  );
}

function DissolveConfirm({ hero, oldId, busy, onCancel, onChoose }: { hero: RunHero; oldId: string; busy: boolean; onCancel(): void; onChoose(c: RunChoice): Promise<number | null> }) {
  const s = ownedSkills(hero).find((x) => x.card.id === oldId);
  if (s === undefined) return null;
  const lines = dissolveConfirm(s.card.name_zh, s.flash);
  return (
    <div className="panel dissolve-confirm" role="alertdialog" aria-label="溶掉確認" data-testid="dissolve-confirm">
      <div className="section-title">確認溶掉</div>
      {lines.map((l) => (
        <div key={l} className="small">
          {l}
        </div>
      ))}
      <div className="small muted">欄位會空出來，可以從技能庫換上別招；退回的點數照常可以存，之後閃現仍要先上場用過。</div>
      <div className="run-actions">
        <button type="button" className="danger primary" disabled={busy} data-testid="dissolve-yes" onClick={() => void onChoose(dissolveChoice(oldId))}>
          確定溶掉
        </button>
        <button data-sfx="ui_cancel" type="button" disabled={busy} onClick={onCancel}>
          取消
        </button>
      </div>
    </div>
  );
}

function InheritForm({ hero, sourceId, busy, onCancel, onChoose }: { hero: RunHero; sourceId: string; busy: boolean; onCancel(): void; onChoose(c: RunChoice): Promise<number | null> }) {
  const [targetId, setTargetId] = useState<string | null>(null);
  const [picked, setPicked] = useState<number[]>([]);
  const source = ownedSkills(hero).find((x) => x.card.id === sourceId);
  const limit = maxCarry(hero.flash_rules);
  const targets = inheritTargets(hero).filter((t) => t.card.id !== sourceId);
  const carry = carryable(source?.flash);
  const target = targets.find((t) => t.card.id === targetId);
  const ready = target !== undefined && picked.length > 0;
  return (
    <div className="panel inherit-form" data-testid="inherit-form">
      <div className="section-title">傳承</div>
      <p className="small muted">{INHERIT_RULE_TEXT}</p>
      <div className="small">1. 帶走哪些小變化（最多 {limit} 個，依序成為新技能的第 1、2 次）</div>
      <ul className="inherit-records">
        {carry.map((r) => (
          <li key={r.nth}>
            <label>
              <input type="checkbox" checked={picked.includes(r.nth)} disabled={busy || (!picked.includes(r.nth) && picked.length >= limit)} onChange={() => setPicked(toggleCarry(picked, r.nth, limit))} />
              {recordLine(r)}
            </label>
          </li>
        ))}
      </ul>
      <div className="small">2. 傳給哪一招（還沒閃過的新技能）</div>
      <div className="run-replace-list" data-testid="inherit-targets">
        {targets.map((t) => (
          <button key={t.card.id} type="button" className={targetId === t.card.id ? "primary selected" : ""} disabled={busy} onClick={() => setTargetId(t.card.id)}>
            {t.card.name_zh}
          </button>
        ))}
      </div>
      <div className="run-actions">
        <button
          type="button"
          className="primary"
          disabled={busy || !ready}
          data-testid="inherit-yes"
          onClick={() => target !== undefined && void onChoose(inheritChoice(target.card.id, sourceId, picked))}
        >
          確定傳承（「{source?.card.name_zh}」會消失，不退點）
        </button>
        <button data-sfx="ui_cancel" type="button" disabled={busy} onClick={onCancel}>
          取消
        </button>
      </div>
    </div>
  );
}
