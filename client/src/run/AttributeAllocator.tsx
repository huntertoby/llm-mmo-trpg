// 屬性配點：每項可加減，總點數固定（開局 4 點、每級 2 點；可全部點在同一項）。
import type { AttributeId } from "../api/types";
import {
  adjustAllocation,
  affectsOf,
  affectsText,
  allocationTotal,
  ATTRIBUTES,
  suggestionText,
  type Allocation,
} from "./flow";

interface Props {
  /** 目前的屬性值（配點前）。 */
  base: Readonly<Record<string, number>>;
  points: number;
  alloc: Allocation;
  onChange(next: Allocation): void;
  disabled?: boolean;
  /** 配點後最大 HP、法力、耐力的變化文字（後端算，Phase 3H-5）；空字串或省略時不顯示。 */
  preview?: string;
  /** 建議的主屬性（開局，Phase 3H-3）。 */
  suggestion?: { attr: string; reason_zh: string } | null;
  /** 每個屬性影響你的哪些招（Phase 3H-3）。 */
  affects?: readonly { attr: string; lines_zh: readonly string[] }[];
  heading?: string;
}

export function AttributeAllocator({ base, points, alloc, onChange, disabled = false, preview, suggestion, affects, heading = "屬性配點" }: Props) {
  const left = points - allocationTotal(alloc);
  return (
    <div className="run-alloc">
      <div className="section-title run-alloc-title">
        <span>{heading}</span>
        <span className="muted small">
          剩餘 {left} / {points} 點（可全部加在同一項）
        </span>
      </div>
      {suggestionText(suggestion) !== null && (
        <div className="small run-alloc-suggestion" data-testid="attr-suggestion">
          {suggestionText(suggestion)}
        </div>
      )}
      {(preview ?? "") !== "" && (
        <div className="small run-alloc-preview" data-testid="alloc-preview">
          配點後：{preview}
        </div>
      )}
      <div className="run-alloc-grid">
        {ATTRIBUTES.map((a) => {
          const add = alloc[a.id] ?? 0;
          const affected = affectsText(affectsOf(affects, a.id));
          return (
            <div key={a.id} className={`run-alloc-row${suggestion?.attr === a.id ? " suggested" : ""}`}>
              <span className="run-alloc-name">
                {a.label}
                {suggestion?.attr === a.id && <span className="run-alloc-star"> ★建議</span>}
              </span>
              <button
                type="button"
                aria-label={`${a.label} 減一點`}
                disabled={disabled || add <= 0}
                onClick={() => onChange(adjustAllocation(alloc, a.id as AttributeId, -1, points))}
              >
                −
              </button>
              <span className="run-alloc-value">
                {base[a.id] ?? 10}
                {add > 0 && <span className="run-alloc-add"> +{add}</span>}
              </span>
              <button
                type="button"
                aria-label={`${a.label} 加一點`}
                disabled={disabled || left <= 0}
                onClick={() => onChange(adjustAllocation(alloc, a.id as AttributeId, 1, points))}
              >
                ＋
              </button>
              {affected !== null && (
                <span className="run-alloc-affects muted small" data-testid={`attr-affects-${a.id}`}>
                  {affected}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
