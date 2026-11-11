// HUD 浮動面板裡的小元件（Phase 6B-5）：技能（K）、影子（Y）、留言（N）、這裡（點地名條）。
// 內容都是原本右側長條側欄的元件（`LoadoutEditor`、`PartyPanel`、`MyShadowPanel`、`NotesPanel`、`HerePanel`、`NpcPanel`），
// 只是改成點了才打開；面板內部的去文字化另外排（HUD版面.md 第 6 節）。
import type { ReactNode } from "react";
import type { WorldAction, WorldView } from "../api/types";
import { LoadoutEditor } from "../run/LoadoutEditor";
import { SkillTile } from "../ui/SkillTile";
import { MyShadowPanel, PartyPanel } from "./PartyPanel";
import { limitOf } from "./limits";

export function HudSkillsPanel({ view, busy, onAct }: { view: WorldView; busy: boolean; onAct(action: WorldAction): void }) {
  const c = view.character;
  return (
    <div className="panel world-hud-skills" data-testid="world-hud-skills">
      <div className="section-title">
        技能　<span className="muted small">{c.slots_zh}</span>
      </div>
      {c.weapon_blocked_zh != null && (
        <div className="mail-warn small" data-testid="world-weapon-blocked">
          {c.weapon_blocked_zh}
        </div>
      )}
      {/* UI-E3（巡檢 #8、G3）：技能卡縮小版，和戰鬥底列同一張；滑過看完整技能卡（UI-E3c 小修 5：優先開在下方，不蓋主角卡） */}
      <div className="world-skill-tiles" data-testid="world-skill-tiles">
        {c.skills.map((s) => (
          <SkillTile
            key={s.id}
            card={s}
            blockedReason={(c.weapon_blocked ?? []).includes(s.id) ? "主手別大類，暫時不能用" : null}
            testId={`world-skill-${s.id}`}
            prefer="below"
          />
        ))}
        {c.skills.length === 0 && <span className="muted small">（無）</span>}
      </div>
      {c.bench.length > 0 && (
        <>
          <div className="muted small">備用</div>
          <div className="world-skill-tiles bench" data-testid="world-skill-bench">
            {c.bench.map((s) => (
              <SkillTile key={s.id} card={s} testId={`world-bench-${s.id}`} prefer="below" />
            ))}
          </div>
        </>
      )}
      {view.here.can_loadout ? (
        <LoadoutEditor
          key={c.skills.map((s) => s.id).join(",")}
          hero={c}
          disabled={busy}
          onApply={(ids) => onAct({ kind: "loadout", skills: [...ids] })}
        />
      ) : (
        <div className="muted small" data-testid="world-loadout-locked">
          {limitOf(view, "loadout") ?? "換技能只在城鎮與營火。"}
        </div>
      )}
    </div>
  );
}

export function HudShadowPanel({ view, busy, onAct }: { view: WorldView; busy: boolean; onAct(action: WorldAction): void }) {
  return (
    <div className="world-hud-stack" data-testid="world-hud-shadow">
      {view.party != null && <PartyPanel party={view.party} />}
      {view.my_shadow != null && <MyShadowPanel shadow={view.my_shadow} choices={view.party?.ai_choices ?? []} busy={busy} onAct={onAct} />}
    </div>
  );
}

/** 留言面板：地點留言（原本的 `NotesPanel`）＋完整的「最近發生的事」（浮動提示淡出後在這裡看）。 */
export function HudNotesPanel({ notes, log }: { notes: ReactNode; log: readonly string[] }) {
  return (
    <div className="world-hud-stack" data-testid="world-hud-notes">
      {notes}
      <div className="panel world-log" data-testid="world-log">
        <div className="section-title">最近發生的事</div>
        {log.length === 0 ? (
          <div className="muted small">還沒有。</div>
        ) : (
          <ul>
            {log.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
