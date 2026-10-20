// 屬性配點：每項可加減，總點數固定（開局 4 點、每級 2 點；可全部點在同一項）。
import type { AttributeId } from "../api/types";
import { adjustAllocation, allocationTotal, ATTRIBUTES, conHpGain, hpDeltaText, type Allocation } from "./flow";

interface Props {
  /** 目前的屬性值（配點前）。 */
  base: Readonly<Record<string, number>>;
  points: number;
  alloc: Allocation;
  onChange(next: Allocation): void;
  disabled?: boolean;
  /** 每點體質的最大 HP（有值時，體質旁即時顯示配點帶來的「＋N HP」）。 */
  hpPerCon?: number;
}

export function AttributeAllocator({ base, points, alloc, onChange, disabled = false, hpPerCon }: Props) {
  const left = points - allocationTotal(alloc);
  return (
    <div className="run-alloc">
      <div className="section-title">
        屬性配點
        <span className="muted small">
          剩餘 {left} / {points} 點（可全部加在同一項）
        </span>
      </div>
      <div className="run-alloc-grid">
        {ATTRIBUTES.map((a) => {
          const add = alloc[a.id] ?? 0;
          return (
            <div key={a.id} className="run-alloc-row">
              <span className="run-alloc-name">{a.label}</span>
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
              {a.id === "con" && hpPerCon !== undefined && add > 0 && (
                <span className="run-alloc-hp small" data-testid="con-hp-preview">
                  最大 HP {hpDeltaText(conHpGain(alloc, hpPerCon))}
                </span>
              )}
              <button
                type="button"
                aria-label={`${a.label} 加一點`}
                disabled={disabled || left <= 0}
                onClick={() => onChange(adjustAllocation(alloc, a.id as AttributeId, 1, points))}
              >
                ＋
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
