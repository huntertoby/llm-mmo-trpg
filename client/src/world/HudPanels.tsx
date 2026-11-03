// HUD 浮動面板裡的小元件（Phase 6B-5）：技能（K）、影子（Y）、留言（N）、這裡（點地名條）。
// 內容都是原本右側長條側欄的元件（`LoadoutEditor`、`PartyPanel`、`MyShadowPanel`、`NotesPanel`、`HerePanel`、`NpcPanel`），
// 只是改成點了才打開；面板內部的去文字化另外排（HUD版面.md 第 6 節）。
import type { ReactNode } from "react";
import type { WorldAction, WorldView } from "../api/types";
import { LoadoutEditor } from "../run/LoadoutEditor";
import { MyShadowPanel, PartyPanel } from "./PartyPanel";

export function HudSkillsPanel({ view, busy, onAct }: { view: WorldView; busy: boolean; onAct(action: WorldAction): void }) {
  const c = view.character;
  return (
    <div className="panel world-hud-skills" data-testid="world-hud-skills">
      <div className="section-title">
        技能　<span className="muted small">{c.slots_zh}</span>
      </div>
      <ul className="small">
        {c.skills.map((s) => (
          <li key={s.id}>{s.name_zh}</li>
        ))}
        {c.skills.length === 0 && <li className="muted">（無）</li>}
      </ul>
      {c.bench.length > 0 && <div className="muted small">備用：{c.bench.map((s) => s.name_zh).join("、")}</div>}
      {view.here.can_loadout ? (
        <LoadoutEditor
          key={c.skills.map((s) => s.id).join(",")}
          hero={c}
          disabled={busy}
          onApply={(ids) => onAct({ kind: "loadout", skills: [...ids] })}
        />
      ) : (
        <div className="muted small">換技能只在城鎮與營火。</div>
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
