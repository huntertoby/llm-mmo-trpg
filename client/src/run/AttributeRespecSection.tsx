// 營火的免費屬性重配與重配後的分配（Phase 3H-3）：和技能點重配放在同一個畫面。
// 重配把分配出去的屬性點全部退回；退回的點數（`attribute_points`）可以在營火或下一場戰鬥前慢慢分配。
import { useState } from "react";
import type { RunChoice, RunHero } from "../api/types";
import { AttributeAllocator } from "./AttributeAllocator";
import { useAllocationPreview } from "./allocationPreview";
import { allocationTotal, cleanAllocation, type Allocation } from "./flow";

interface Props {
  hero: RunHero;
  busy: boolean;
  /** 送出選擇；回傳失敗時的 HTTP 狀態（成功為 `null`）。 */
  onChoose(choice: RunChoice): Promise<number | null>;
  /** 營火：多了「免費重配屬性點」。 */
  campfire?: boolean;
  /** 這一輪的編號（配點預覽用；省略時不顯示預覽）。 */
  runId?: string;
}

export function AttributeRespecSection({ hero, busy, onChoose, campfire = false, runId }: Props) {
  const [alloc, setAlloc] = useState<Allocation>({});
  const preview = useAllocationPreview(runId, alloc);
  const points = hero.attribute_points ?? 0;
  const spent = Object.values(hero.attribute_spent ?? {}).reduce((a, b) => a + (b ?? 0), 0);
  if (points <= 0 && !(campfire && spent > 0)) return null;

  async function allocate() {
    const status = await onChoose({ kind: "allocate", attributes: cleanAllocation(alloc) });
    if (status === null) setAlloc({});
  }

  return (
    <div className="run-attr-respec" data-testid="attr-respec">
      {campfire && (
        <div className="run-actions">
          <button
            type="button"
            disabled={busy || spent <= 0}
            data-testid="attr-respec-button"
            onClick={() => {
              setAlloc({});
              void onChoose({ kind: "respec_attributes" });
            }}
          >
            免費重配屬性點（退回 {spent} 點）
          </button>
          <span className="muted small">分配出去的屬性點全部退回，再重新分配；不花任何東西。</span>
        </div>
      )}
      {points > 0 && (
        <>
          <AttributeAllocator
            heading="分配屬性點"
            base={hero.attributes}
            points={points}
            alloc={alloc}
            onChange={setAlloc}
            disabled={busy}
            preview={preview}
            affects={hero.attribute_affects}
          />
          <div className="run-actions">
            <button
              type="button"
              className="primary"
              disabled={busy || allocationTotal(alloc) <= 0}
              data-testid="attr-allocate-button"
              onClick={() => void allocate()}
            >
              確認分配屬性點
            </button>
            <span className="muted small">還沒分配的點數可以之後再分（營火或下一場戰鬥前）。</span>
          </div>
        </>
      )}
    </div>
  );
}
