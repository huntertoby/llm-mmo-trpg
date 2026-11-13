// 釘選的單位小卡（6A-2 起放在戰場右上；6A-3：視窗寬度不到 1000 時收成精簡版，只留名稱、HP 條、耐力條，
// 滑鼠移到小卡上才展開，觸控是點一下開關）。精簡與否的判斷是純函式 `pinnedCompact`。
import { useState, type ComponentProps } from "react";
import { pinnedCompact } from "./statusCard";
import { UnitInfo } from "./UnitInfo";
import { useViewportSize } from "./useLayout";

type Props = Omit<ComponentProps<typeof UnitInfo>, "compact" | "pinned">;

export function PinnedUnitDock(props: Props) {
  const { width } = useViewportSize();
  const [expanded, setExpanded] = useState(false);
  const compact = pinnedCompact(width, expanded);
  return (
    <div
      className={`unit-pin-dock${compact ? " compact" : ""}`}
      aria-label="釘選的單位"
      onMouseEnter={() => setExpanded(true)}
      onMouseLeave={() => setExpanded(false)}
      onPointerUp={(e) => {
        // PB-1f（e3q）：裡面的說明卡 portal 到 body，點說明卡經 React 元件樹冒泡上來的不算點了停靠區
        if (e.pointerType === "touch" && e.target instanceof Node && e.currentTarget.contains(e.target)) setExpanded((v) => !v);
      }}
    >
      <UnitInfo {...props} pinned compact={compact} />
    </div>
  );
}
