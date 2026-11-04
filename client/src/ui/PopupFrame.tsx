// 共用彈窗元件（UI-E2；docs/art/全遊戲一致性巡檢.md #6、#12）：深藍底、金框、RT-1 區域四角飾件、單層。
// 危險類（遇敵）只在上緣加一條紅色細帶和「！」，不換整個框色。點擊開關的面板／對話框，不是說明卡（說明卡用 Hint，6.5.1）。
// 位置三種：
// - `hud`：大世界彈窗（6F-3 的 `popupBox`）：水平置中、上緣在主角卡下方、寬度讓出左右兩欄、下緣停在功能列上方，太高就在框內捲；
// - `dialog`：戰鬥詢問視窗（3-8 的 `decision-card`）：水平置中、靠上或靠下，框內捲；
// - `inline`：疊在別的容器裡（中上方的遇敵卡、事件卡），位置由容器決定。
// 四角飾件畫在外框的 `::after`（`.rt-frame`），內容捲在 `.ui-popup-body` 裡，所以捲動時飾件不跟著跑。
import type { CSSProperties, ReactNode } from "react";

/** 6F-3 `popupBox()` 的結果（CSS 像素，相對 HUD 舞台）。 */
export interface PopupBoxLike {
  top: number;
  maxHeight: number;
  maxWidth: number;
}

export type PopupPlacement = { kind: "hud"; box: PopupBoxLike } | { kind: "dialog"; low: boolean } | { kind: "inline" };

export type PopupTone = "normal" | "danger";

/** 位置的內聯樣式（只有 `hud` 有；`dialog` 的位置在 CSS `.decision-card`）。 */
export function popupPlacementStyle(p: PopupPlacement): CSSProperties | undefined {
  if (p.kind !== "hud") return undefined;
  return { top: p.box.top, maxHeight: p.box.maxHeight, width: p.box.maxWidth, maxWidth: p.box.maxWidth };
}

interface Props {
  placement: PopupPlacement;
  tone?: PopupTone;
  /** 外框額外的 class（例如 `world-hud-panel`、`decision-card`、`world-encounter`）。 */
  className?: string;
  role?: "dialog" | "region";
  label?: string;
  testId?: string;
  /** 外框上的 `data-*`（例如 `data-panel`）。 */
  data?: Readonly<Record<string, string>>;
  /** 框頂端、不跟著捲的那一列（戰鬥詢問視窗的標題與「移到下方」）。 */
  head?: ReactNode;
  children: ReactNode;
}

export function PopupFrame({ placement, tone = "normal", className, role, label, testId, data, head, children }: Props) {
  const attrs = Object.fromEntries(Object.entries(data ?? {}).map(([k, v]) => [`data-${k}`, v]));
  const cls = ["ui-popup", "rt-frame", `ui-popup-${placement.kind}`, tone === "danger" ? "danger" : "", placement.kind === "dialog" && placement.low ? "low" : "", className ?? ""]
    .filter((c) => c !== "")
    .join(" ");
  return (
    <div className={cls} style={popupPlacementStyle(placement)} role={role} aria-label={label} data-testid={testId} data-popup={placement.kind} data-tone={tone} {...attrs}>
      {tone === "danger" && (
        <div className="ui-popup-band" aria-hidden="true">
          <span>！</span>
        </div>
      )}
      {head}
      <div className="ui-popup-body">{children}</div>
    </div>
  );
}
