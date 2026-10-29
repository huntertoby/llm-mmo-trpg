// 閃現／重閃的出題前畫面（Phase 3W-6）：先說清楚會扣點、一定要選一個，再選「不指定」或「指定類別」。
// 類別按鈕顯示每類目前的合法變化數量（例「連段（2）」），0 個的不能選；數量由後端 `flash-preview` 提供。
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { FlashPreview, RunChoice, RunHero } from "../api/types";
import { Hint } from "../ui/Hint";
import {
  categoryLabel,
  categorySelectable,
  costProblem,
  flashChoice,
  flashConfirmLabel,
  flashWarning,
  focusedMode,
  openMode,
  type FlashMode,
} from "./flash";

interface Props {
  runId: string;
  hero: RunHero;
  skillId: string;
  skillName: string;
  /** `null` ＝ 閃現；數字 ＝ 重閃第幾次（完整技能 0）。 */
  slot: number | null;
  /** 重閃時顯示被換掉的是哪一格。 */
  slotLabel?: string;
  busy: boolean;
  onChoose(choice: RunChoice): Promise<number | null>;
  onCancel(): void;
}

export function FlashChooser(props: Props) {
  const { runId, skillId, slot } = props;
  const [preview, setPreview] = useState<FlashPreview | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    setPreview(null);
    setLoadError(null);
    api.flashPreview(runId, skillId, slot).then(
      (out) => {
        if (!cancelled) setPreview(out);
      },
      (e: unknown) => {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : String(e));
      },
    );
    return () => {
      cancelled = true;
    };
  }, [runId, skillId, slot]);
  return <FlashChooserView {...props} preview={preview} loadError={loadError} />;
}

type ViewProps = Omit<Props, "runId"> & { preview: FlashPreview | null; loadError: string | null; initialCategory?: string | null };

/** 出題前畫面本體（預覽由外面載入；方便單元測試直接給預覽）。 */
export function FlashChooserView({ hero, skillId, skillName, slot, slotLabel, busy, onChoose, onCancel, preview, loadError, initialCategory = null }: ViewProps) {
  const [category, setCategory] = useState<string | null>(initialCategory);
  const rules = hero.flash_rules;

  const insight = hero.insight ?? 0;
  const open: FlashMode = preview !== null ? { category: null, cost: preview.open_cost, options: openMode(rules).options } : openMode(rules);
  const mode: FlashMode =
    category === null ? open : { ...focusedMode(rules, category), cost: preview?.focused_cost ?? focusedMode(rules, category).cost };
  const problem = preview?.problem_zh ?? null;
  const short = costProblem(insight, mode);
  const title = slot === null ? `閃現「${skillName}」` : `重閃「${skillName}」${slotLabel !== undefined ? `：${slotLabel}` : ""}`;
  const allowFocus = rules?.allow_focus ?? true;

  return (
    <div className="panel flash-chooser" data-testid="flash-chooser">
      <div className="section-title">
        {title}
        {preview !== null && (
          <span className="muted small">
            　{slot === null ? `第 ${preview.nth} 次${preview.major ? "（大變化）" : ""}` : preview.major ? "（大變化）" : ""}
          </span>
        )}
      </div>
      <p className="flash-warning small" data-testid="flash-warning">
        {flashWarning(mode)}
        {slot !== null && "重閃不增加閃現次數，也不需要先上場。"}
      </p>
      {loadError !== null && <div className="flash-problem small">{loadError}</div>}
      {preview === null && loadError === null && <div className="muted small">載入中……</div>}
      {problem !== null && <div className="flash-problem small" data-testid="flash-problem">{problem}</div>}
      {preview !== null && problem === null && (
        <>
          <div className="flash-modes">
            <button
              type="button"
              className={`flash-mode${category === null ? " selected primary" : ""}`}
              disabled={busy}
              data-testid="flash-mode-open"
              onClick={() => setCategory(null)}
            >
              <b>不指定</b>
              <span className="small">
                {open.cost} 點・{open.options} 選 1
              </span>
              <span className="muted small">混合各類變化，至少涵蓋 2 類</span>
            </button>
          </div>
          {allowFocus && (
            <>
              <div className="muted small flash-cat-title">
                指定類別（{focusedMode(rules, "x").cost} 點・{focusedMode(rules, "x").options} 選 1，只出該類）
              </div>
              <div className="flash-categories" data-testid="flash-categories">
                {preview.categories.map((c) => {
                  const ok = categorySelectable(c);
                  const button = (
                    <button
                      key={c.id}
                      type="button"
                      className={`flash-cat${category === c.id ? " selected primary" : ""}`}
                      disabled={busy || !ok}
                      data-testid={`flash-cat-${c.id}`}
                      onClick={() => setCategory(c.id)}
                    >
                      {categoryLabel(c)}
                    </button>
                  );
                  return ok ? button : (
                    <Hint key={c.id} text="這一類目前沒有合法的變化">
                      {button}
                    </Hint>
                  );
                })}
              </div>
              {preview.major && (
                <div className="muted small">第 3 次是大變化；指定類別時，轉型保底會另外列在最後並標「轉型」。</div>
              )}
            </>
          )}
        </>
      )}
      {short !== null && problem === null && <div className="flash-problem small" data-testid="flash-short">{short}</div>}
      <div className="run-actions">
        <button
          type="button"
          className="primary"
          data-testid="flash-confirm"
          disabled={busy || preview === null || problem !== null || short !== null}
          onClick={() => void onChoose(flashChoice(skillId, slot, category))}
        >
          {flashConfirmLabel(mode)}
        </button>
        <button type="button" disabled={busy} onClick={onCancel}>
          先不要
        </button>
        <span className="muted small">目前靈感點 {insight}</span>
      </div>
    </div>
  );
}
