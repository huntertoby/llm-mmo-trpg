// 反應設定面板：主角的每條反應規則一個三段切換（自動／詢問／關閉）。
// 切換用 `set_reaction_mode` 動作（0 AP、不結束回合），只能在自己的回合；預設維持內容的設定。
import type { ReactionMode, UnitView } from "../api/types";
import { REACTION_MODES, REACTION_MODE_LABELS, ruleSummary, uniqueRules } from "../battle/reactions";

interface Props {
  hero: UnitView | null;
  /** 現在能不能送動作（自己的回合、沒有在播放）。 */
  enabled: boolean;
  /** 「之後都自動」已記下、輪到主角時會送出的反應。 */
  queued: readonly string[];
  onSet(reaction: string, mode: ReactionMode): void;
}

export function ReactionPanel({ hero, enabled, queued, onSet }: Props) {
  if (hero === null) return null;
  const rules = uniqueRules(hero);
  if (rules.length === 0) return <div className="panel reaction-panel muted">主角沒有可設定的反應。</div>;
  return (
    <div className="panel reaction-panel" aria-label="反應設定">
      <div className="section-title">反應設定</div>
      {rules.map((rule) => (
        <div className="reaction-row" key={rule.reaction} title={rule.description_zh}>
          <div className="reaction-info">
            <div className="reaction-name">{rule.name_zh}</div>
            <div className="small muted">
              {ruleSummary(rule)}
              {queued.includes(rule.reaction) && "（下回合改為自動）"}
            </div>
          </div>
          <div className="segmented" role="group" aria-label={`${rule.name_zh}模式`}>
            {REACTION_MODES.map((mode) => (
              <button
                key={mode}
                type="button"
                className={rule.mode === mode ? "selected" : ""}
                aria-pressed={rule.mode === mode}
                disabled={!enabled || rule.mode === mode}
                onClick={() => onSet(rule.reaction, mode)}
              >
                {REACTION_MODE_LABELS[mode]}
              </button>
            ))}
          </div>
        </div>
      ))}
      {!enabled && <div className="small muted">只能在自己的回合切換。</div>}
    </div>
  );
}
