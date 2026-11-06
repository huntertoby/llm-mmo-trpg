// 入口畫面的外殼（UI-E1；docs/art/shots/misc/home-v2.png、entry-screens.png）：浮島天空背景＋標題牌＋內容。
// 首頁、開發選單、角色列表與建角、開新一輪、一輪路線圖共用同一套背景、框（共用彈窗元件 PopupFrame 的 inline，
// 深藍底、金框、RT-1 四角飾件）與按鈕（CSS `.entry-skin`）。只換外觀，內容與流程照舊。
import type { ReactNode } from "react";
import { EntryBackdrop } from "./EntryBackdrop";
import { PopupFrame } from "./PopupFrame";

interface PlaqueProps {
  heading: ReactNode;
  sub?: ReactNode;
  /** 首頁的大標題牌：放遊戲名稱。 */
  big?: boolean;
  children?: ReactNode;
}

/** 標題牌：照大世界字牌（深藍底、金框、襯線字）。 */
export function EntryPlaque({ heading, sub, big = false, children }: PlaqueProps) {
  return (
    <PopupFrame placement={{ kind: "inline" }} className={`entry-plaque${big ? " big" : ""}`} testId="entry-plaque">
      <h1 className="entry-plaque-title">{heading}</h1>
      {sub !== undefined && sub !== "" && <div className="entry-plaque-sub">{sub}</div>}
      {children}
    </PopupFrame>
  );
}

interface PanelProps {
  className?: string;
  testId?: string;
  children: ReactNode;
}

/** 入口畫面的一塊框（共用彈窗元件的 inline）。 */
export function EntryPanel({ className, testId, children }: PanelProps) {
  return (
    <PopupFrame placement={{ kind: "inline" }} className={`entry-panel${className !== undefined ? ` ${className}` : ""}`} testId={testId}>
      {children}
    </PopupFrame>
  );
}

interface ShellProps {
  /** 外層額外的 class（例如 `entry-home`、`world-pick`）。 */
  className?: string;
  testId?: string;
  children: ReactNode;
}

export function EntryShell({ className, testId, children }: ShellProps) {
  return (
    <div className={`entry-skin${className !== undefined ? ` ${className}` : ""}`} data-testid={testId}>
      <EntryBackdrop />
      <div className="entry-page">{children}</div>
    </div>
  );
}
