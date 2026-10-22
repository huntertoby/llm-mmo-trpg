// 一步步組：步驟列（可回上一步）＋ 目前這一步的說明與欄位。
import { useEffect, useState } from "react";
import type { DraftOptions, StepId, StepOptions } from "../../api/types";
import { autoSingles, changeSkeleton, getPath, type Json } from "../../workshop/draft";
import { availableSteps, canBack, canNext, currentStep, STEP_NAMES, type EditorState } from "../../workshop/state";
import { FieldList } from "./FieldEditor";
import { Hint } from "../Hint";

interface Props {
  state: EditorState;
  onDraft(draft: Json): void;
  onGoto(step: StepId): void;
  onBack(): void;
  onNext(): void;
}

const ALL_STEPS: readonly StepId[] = ["skeleton", "basics", "shape", "effects", "followup", "condition", "cost", "rarity", "variants"];

function StepBar({ state, onGoto }: { state: EditorState; onGoto(step: StepId): void }) {
  const open = availableSteps(state.options);
  const cur = currentStep(state);
  // 「動作段」只有位移技能（或草稿已經有動作段）才會出現；其他技能的步驟列不顯示它。
  const shown = ALL_STEPS.filter((id) => (id !== "followup" && id !== "variants") || open.includes(id));
  return (
    <ol className="ws-steps">
      {shown.map((id, i) => {
        const info = state.options?.steps.find((s) => s.id === id);
        const enabled = open.includes(id);
        const cls = ["ws-step", id === cur ? "current" : "", info?.complete === true ? "done" : "", enabled ? "" : "locked"].join(" ");
        return (
          <li key={id}>
            <Hint text={enabled ? (id === "followup" ? "可省略：不接第二段就是普通技能" : "") : "先完成前面的步驟"}>
              <button type="button" className={cls} disabled={!enabled} aria-current={id === cur ? "step" : undefined} onClick={() => onGoto(id)}>
                <span className="ws-step-no">{info?.complete === true ? "✓" : i + 1}</span>
                {STEP_NAMES[id]}
              </button>
            </Hint>
          </li>
        );
      })}
    </ol>
  );
}

interface BodyProps {
  step: StepOptions;
  draft: Json;
  options: DraftOptions;
  onDraft(d: Json): void;
}

function StepBody({ step, draft, options, onDraft }: BodyProps) {
  // 只有一個選項的必填欄位（例：被動技的形狀只能是「自己」）自動選好。
  useEffect(() => {
    const next = autoSingles(draft, step.fields);
    if (next !== draft) onDraft(next);
  }, [draft, step, onDraft]);

  // 換骨架會清掉其他欄位：先在頁內問一次（不用 window.confirm；內嵌瀏覽器會直接回傳否）
  const [pendingSkeleton, setPendingSkeleton] = useState<{ next: Json; after: string } | null>(null);
  useEffect(() => setPendingSkeleton(null), [step.id]);
  const onChange = (next: Json) => {
    const before = getPath(draft, "skeleton");
    const after = getPath(next, "skeleton");
    if (step.id === "skeleton" && typeof after === "string" && before !== after) {
      const filled = Object.keys(draft).filter((k) => k !== "skeleton" && k !== "name_zh").length;
      if (filled > 0) {
        setPendingSkeleton({ next, after });
        return;
      }
      onDraft(changeSkeleton(draft, after));
      return;
    }
    setPendingSkeleton(null);
    onDraft(next);
  };
  return (
    <div className="ws-step-body">
      <h3>{step.name_zh}</h3>
      <div className="muted">{step.description_zh}</div>
      {step.notes_zh.length > 0 && (
        <ul className="ws-notes" aria-label="這一步的限制">
          {step.notes_zh.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      )}
      <FieldList fields={step.fields} container={draft} base="" onChange={onChange} />
      {pendingSkeleton !== null && (
        <div className="ws-warning" role="alertdialog" data-testid="skeleton-confirm">
          <div>換骨架會清掉其他已填的欄位（名稱除外），確定要換嗎？</div>
          <div className="ws-row">
            <button
              type="button"
              className="danger"
              onClick={() => {
                onDraft(changeSkeleton(draft, pendingSkeleton.after));
                setPendingSkeleton(null);
              }}
            >
              確定換骨架
            </button>
            <button type="button" onClick={() => setPendingSkeleton(null)}>
              取消
            </button>
          </div>
        </div>
      )}
      {options.problems.length > 0 && (
        <div className="ws-problems" role="alert">
          <div className="section-title">已填的內容和選項不符</div>
          <ul>
            {options.problems.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function StepView({ state, onDraft, onGoto, onBack, onNext }: Props) {
  const cur = currentStep(state);
  const step = state.options?.steps.find((s) => s.id === cur);
  return (
    <div className="panel ws-panel">
      <StepBar state={state} onGoto={onGoto} />
      {state.options === null || step === undefined ? (
        <div className="muted">載入選項中……</div>
      ) : (
        <StepBody step={step} draft={state.draft} options={state.options} onDraft={onDraft} />
      )}
      <div className="ws-nav">
        <button type="button" onClick={onBack} disabled={!canBack(state)}>
          ← 上一步
        </button>
        <button type="button" className="primary" onClick={onNext} disabled={!canNext(state)}>
          下一步 →
        </button>
      </div>
      {step !== undefined && !step.complete && !canNext(state) && (
        <div className="muted small">這一步還有必填欄位（標 * ）沒填，填完後才會出現下一步。</div>
      )}
    </div>
  );
}
