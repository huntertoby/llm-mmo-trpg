// 營火的技能整理（Phase 3W-6）：重閃、溶掉、傳承。重閃與溶掉／傳承只在營火（06 6.34.3）。
// 溶掉與傳承是處理「舊技能」的二選一：選一招舊技能，再決定溶掉（退回花費的一半）或把小變化傳給新技能（舊技能消失、不退點）。
import { useState } from "react";
import type { RunChoice, RunHero } from "../api/types";
import { Hint } from "../ui/Hint";
import { SkillFlashInfo } from "../ui/SkillFlashInfo";
import { FlashChooser } from "./FlashChooser";
import {
  carryable,
  dissolveChoice,
  dissolveConfirm,
  INHERIT_RULE_TEXT,
  inheritChoice,
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

interface Props {
  runId: string;
  hero: RunHero;
  busy: boolean;
  onChoose(choice: RunChoice): Promise<number | null>;
}

export function CampfireSkillCare({ runId, hero, busy, onChoose }: Props) {
  return (
    <div className="campfire-care" data-testid="campfire-care">
      <ReflashSection runId={runId} hero={hero} busy={busy} onChoose={onChoose} />
      <OldSkillSection hero={hero} busy={busy} onChoose={onChoose} />
    </div>
  );
}

// ---- 重閃 --------------------------------------------------------------------------------

function ReflashSection({ runId, hero, busy, onChoose }: Props) {
  const [target, setTarget] = useState<{ id: string; slot: number } | null>(null);
  const list = reflashable(hero);
  const chosen = target === null ? undefined : list.find((s) => s.card.id === target.id);
  const slotLabel = chosen === undefined || target === null ? undefined : reflashSlots(chosen.flash, hero.flash_rules).find((s) => s.slot === target.slot)?.label;
  return (
    <div className="panel campfire-reflash" data-testid="campfire-reflash">
      <div className="section-title">重閃（只在營火）</div>
      <p className="small muted">
        把一招以前某一次的變化換掉，價格和閃現相同（{rulesOf(hero.flash_rules).open_cost} 點出 {rulesOf(hero.flash_rules).open_options} 個；指定類別
        {" "}{rulesOf(hero.flash_rules).focused_cost} 點出 {rulesOf(hero.flash_rules).focused_options} 個）。不需要先上場用過，也不增加閃現次數；新選項不會比被換掉的更弱。
      </p>
      {chosen !== undefined && target !== null && (
        <FlashChooser
          key={`${target.id}:${target.slot}`}
          runId={runId}
          hero={hero}
          skillId={target.id}
          skillName={chosen.card.name_zh}
          slot={target.slot}
          slotLabel={slotLabel}
          busy={busy}
          onChoose={async (c) => {
            const status = await onChoose(c);
            if (status === null) setTarget(null);
            return status;
          }}
          onCancel={() => setTarget(null)}
        />
      )}
      {list.length === 0 && <div className="muted small">還沒有可以重閃的技能（要先閃現過，或有完整技能）。</div>}
      <ul className="flash-skill-list" data-testid="reflash-list">
        {list.map(({ card, flash }) => (
          <li key={card.id} className="reflash-row">
            <div>
              <b>{card.name_zh}</b>
              <SkillFlashInfo flash={flash} rules={hero.flash_rules} brief />
            </div>
            <div className="reflash-slots">
              {reflashSlots(flash, hero.flash_rules).map((s) => (
                <button
                  key={s.slot}
                  type="button"
                  className={target?.id === card.id && target.slot === s.slot ? "primary" : ""}
                  disabled={busy || (hero.insight ?? 0) < rulesOf(hero.flash_rules).open_cost}
                  data-testid={`reflash-${card.id}-${s.slot}`}
                  onClick={() => setTarget({ id: card.id, slot: s.slot })}
                >
                  重閃　{s.label}
                  {s.transformHint && <span className="skill-flash-transform small">　{TRANSFORM_HINT}</span>}
                </button>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ---- 溶掉／傳承 --------------------------------------------------------------------------

type Mode = "dissolve" | "inherit";

function OldSkillSection({ hero, busy, onChoose }: Omit<Props, "runId">) {
  const [oldId, setOldId] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode | null>(null);
  const skills = ownedSkills(hero);
  const old = skills.find((s) => s.card.id === oldId);
  function pickOld(id: string) {
    setOldId(oldId === id ? null : id);
    setMode(null);
  }
  return (
    <div className="panel campfire-old" data-testid="campfire-old">
      <div className="section-title">溶掉或傳承（二選一，只在營火）</div>
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
  const carry = carryable(source?.flash).length;
  const targets = inheritTargets(hero).filter((t) => t.card.id !== oldId);
  const reason = carry === 0 ? "這招沒有可以帶走的小變化（大變化、轉型、完整技能的調整欄不能傳承）" : targets.length === 0 ? "沒有還沒閃過的新技能可以接受傳承" : undefined;
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
        <button type="button" disabled={busy} onClick={onCancel}>
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
        <button type="button" disabled={busy} onClick={onCancel}>
          取消
        </button>
      </div>
    </div>
  );
}
