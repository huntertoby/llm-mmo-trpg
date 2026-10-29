// 閃現選項畫面（Phase 3W-6）：點數已經扣了，一定要選一個。每個選項顯示類別標籤、變化說明、與原本比較的數字，
// 以及套用後的技能卡；轉型保底列在最後並標「轉型」。轉型換到已滿的欄位時，要先選卸下哪一招。
import { useState } from "react";
import type { RunChoice, RunResponse } from "../api/types";
import { SkillCardView } from "../ui/SkillCardView";
import { ownedCards } from "../run/loadout";
import { cardDiff, flashOf, optionTag, pendingTitle, pickChoice, pickReady, sortedOptions } from "../run/flash";

type Props = {
  run: RunResponse;
  busy: boolean;
  onChoose(choice: RunChoice): Promise<number | null>;
};

export function RunFlashPending({ run, busy, onChoose }: Props) {
  const pending = run.pending_flash;
  const [pick, setPick] = useState<number | null>(null);
  const [unequip, setUnequip] = useState<string | null>(null);
  if (pending === null || pending === undefined) return null;
  const before = ownedCards(run.hero).get(pending.skill_id);
  const options = sortedOptions(pending.options);
  const picked = options.find((o) => o.index === pick);
  return (
    <div className="panel run-flash-pending" data-testid="run-flash-pending">
      <h2>閃現！　選一個變化</h2>
      <div className="small">{pendingTitle(pending, before?.name_zh ?? pending.skill_id)}</div>
      <p className="muted small">點數已經扣了，一定要選一個。每個選項都不會讓這招變弱。</p>
      {before !== undefined && (
        <details className="flash-before">
          <summary className="small">看原本的技能</summary>
          <SkillCardView card={before} flash={flashOf(run.hero, before.id)} flashRules={run.hero.flash_rules} />
        </details>
      )}
      <div className="run-offer-cards flash-options">
        {options.map((o) => {
          const diff = cardDiff(before, o.card);
          const selected = pick === o.index;
          return (
            <div
              key={o.index}
              className={`run-offer-card flash-option${selected ? " selected" : ""}${o.transform ? " transform" : ""}`}
              data-testid={`flash-option-${o.index}`}
            >
              <div className={`flash-option-tag${o.transform ? " transform" : ""}`} data-testid="flash-option-tag">
                <b>{optionTag(o)}</b>
              </div>
              <div className="flash-option-summary">{o.summary_zh}</div>
              {diff.length > 0 && (
                <ul className="flash-diff small" data-testid="flash-diff">
                  {diff.map((line) => (
                    <li key={line} className={line.startsWith("原") ? "was" : line.startsWith("新") ? "now" : ""}>
                      {line}
                    </li>
                  ))}
                </ul>
              )}
              <SkillCardView card={o.card} />
              <button
                type="button"
                className={selected ? "primary" : ""}
                disabled={busy}
                onClick={() => {
                  setPick(selected ? null : o.index);
                  setUnequip(null);
                }}
              >
                {selected ? "已選這個（再按一次取消）" : "選這個"}
              </button>
            </div>
          );
        })}
      </div>
      {picked !== undefined && picked.unequip_candidates.length > 0 && (
        <div className="panel run-replace">
          <div className="section-title">轉型後的欄位已滿，請選一個要卸下（放回備用）的技能</div>
          <div className="run-replace-list">
            {picked.unequip_candidates.map((id) => (
              <button
                key={id}
                type="button"
                className={unequip === id ? "primary selected" : ""}
                disabled={busy}
                onClick={() => setUnequip(id)}
              >
                卸下「{ownedCards(run.hero).get(id)?.name_zh ?? id}」
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="run-actions">
        <button
          type="button"
          className="primary"
          data-testid="flash-pick-confirm"
          disabled={busy || !pickReady(picked, unequip)}
          onClick={() => picked !== undefined && void onChoose(pickChoice(picked, unequip))}
        >
          確定
        </button>
        <span className="muted small">{picked === undefined ? "請先選一個變化。" : ""}</span>
      </div>
    </div>
  );
}
