// 部件說明框（Phase 3-18a；3-30 起與技能卡共用浮動卡規則 `useFloatCard`）：包住任何一個部件（技能圖示的小圓、狀態、表面……），
// 滑過顯示「類別、名稱、說明」，點一下釘住（觸控也能用），點外面或按 Esc 關閉。說明框用 portal 放在 body 上，不會被卡片裁掉，也不會超出視窗。
import type { ReactNode } from "react";
import { FloatCard, useFloatCard } from "./useFloatCard";

interface Props {
  /** 部件類別（骨架、形狀、效果、狀態……）。 */
  cat: string;
  label: string;
  /** 說明；空字串就不寫。 */
  tip: string;
  children: ReactNode;
  /** 包在可點選的東西裡面（例如工坊選項按鈕）時設為 false：只在滑過時顯示，不攔截點擊。 */
  pin?: boolean;
  className?: string;
}

export function PartTip({ cat, label, tip, children, pin = true, className }: Props) {
  const f = useFloatCard({ pinOn: pin ? "always" : "never" });
  const { onKeyDown: triggerKeyDown, ...trigger } = f.triggerProps;
  return (
    <span
      {...trigger}
      className={`part-tip${className === undefined ? "" : ` ${className}`}`}
      onKeyDown={(e) => {
        triggerKeyDown?.(e);
        if (f.inCard(e.target)) return;
        if (pin && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          f.ctl.click(true);
        }
      }}
      role={pin ? "button" : undefined}
      tabIndex={pin ? 0 : undefined}
      aria-label={`${cat}：${label}`}
      aria-expanded={pin ? f.open : undefined}
    >
      {children}
      {f.open && (
        <FloatCard float={f} className={`part-tip-box${pin ? "" : " no-bridge"}`} align="center" role="tooltip">
          <div className="part-tip-cat">{cat}</div>
          <div className="part-tip-name">{label}</div>
          {tip !== "" && <div className="part-tip-text">{tip}</div>}
        </FloatCard>
      )}
    </span>
  );
}
