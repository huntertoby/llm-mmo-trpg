// 戰鬥版 HUD 右上工具鈕的程式繪製圖示（Phase 6A-4e）：24×24 的 SVG，顏色寫死在圖裡（深底金邊的 HUD 上用）。
// 反應設定、隊友指令、圖例、版面、存檔、離開、環境預告。名稱與說明在呼叫端的 `Hint`。
import type { ReactElement } from "react";

export type BattleToolIconName = "reactions" | "orders" | "legend" | "layout" | "save" | "exit" | "telegraph";

const GOLD = "#e8cf90";

const PATHS: Record<BattleToolIconName, ReactElement> = {
  // 盾牌＋閃電：反應
  reactions: (
    <>
      <path d="M12 2.5l8 3v6c0 5-3.6 8.6-8 10-4.4-1.4-8-5-8-10v-6z" fill="#3a3020" stroke={GOLD} strokeWidth="1.5" />
      <path d="M13 6l-4 7h3l-1 5 4-7h-3z" fill="#ffd23f" />
    </>
  ),
  // 旗子：隊友指令
  orders: (
    <>
      <path d="M6 21V3" stroke={GOLD} strokeWidth="1.8" strokeLinecap="round" />
      <path d="M6.5 4h11l-2.5 4 2.5 4h-11z" fill="#d85a48" stroke="#6a2018" strokeWidth="1" />
    </>
  ),
  // 打開的書：圖例
  legend: (
    <>
      <path d="M12 6c-2.5-1.6-5.5-2-8-1.5v14c2.5-.5 5.5-.1 8 1.5 2.5-1.6 5.5-2 8-1.5v-14c-2.5-.5-5.5-.1-8 1.5z" fill="#3a3020" stroke={GOLD} strokeWidth="1.4" />
      <path d="M12 6v14" stroke={GOLD} strokeWidth="1.2" />
      <path d="M6.5 9h3M6.5 12h3M14.5 9h3M14.5 12h3" stroke="#c8b888" strokeWidth="1" strokeLinecap="round" />
    </>
  ),
  // 齒輪：版面設定
  layout: (
    <>
      <path
        d="M12 2.8l1.6 2.4 2.8-.8.6 2.8 2.8.6-.8 2.8 2.4 1.6-2.4 1.6.8 2.8-2.8.6-.6 2.8-2.8-.8L12 21.2l-1.6-2.4-2.8.8-.6-2.8-2.8-.6.8-2.8L2.6 12 5 10.4l-.8-2.8 2.8-.6.6-2.8 2.8.8z"
        fill="#3a3020"
        stroke={GOLD}
        strokeWidth="1.3"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="12" r="3.2" fill="none" stroke={GOLD} strokeWidth="1.4" />
    </>
  ),
  // 磁片：存檔
  save: (
    <>
      <path d="M4 4h13l3 3v13H4z" fill="#2a4060" stroke="#a8c8f0" strokeWidth="1.4" strokeLinejoin="round" />
      <path d="M7 4h9v5H7z" fill="#a8c8f0" />
      <path d="M7 13h10v7H7z" fill="#e8eef8" />
    </>
  ),
  // 門＋箭頭：離開
  exit: (
    <>
      <path d="M13 3H5v18h8" fill="none" stroke={GOLD} strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M10 12h10M16.5 8l3.5 4-3.5 4" fill="none" stroke="#f0e6d0" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  // 沙漏：環境預告
  telegraph: (
    <>
      <path d="M6 3h12M6 21h12" stroke={GOLD} strokeWidth="1.8" strokeLinecap="round" />
      <path d="M7 3.5c0 5 10 5 10 8.5S7 15.5 7 20.5h10c0-5-10-5-10-8.5S17 8.5 17 3.5z" fill="#3a3020" stroke={GOLD} strokeWidth="1.2" />
      <path d="M9.5 19.5h5l-2.5-3z" fill="#e8bb48" />
    </>
  ),
};

export function BattleToolIcon({ name, size = 20 }: { name: BattleToolIconName; size?: number }) {
  return (
    <svg className="bhud-icon" viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" data-icon={name}>
      {PATHS[name]}
    </svg>
  );
}
