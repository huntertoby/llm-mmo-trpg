// 中性的提示（不是錯誤）：例如點到灰掉的技能時說明原因。可關閉，幾秒後自動消失。
import { useEffect } from "react";

interface Props {
  message: string | null;
  onClose(): void;
  /** 幾毫秒後自動關閉；預設 5 秒。 */
  autoCloseMs?: number;
}

export const NOTICE_MS = 5000;

export function NoticeBanner({ message, onClose, autoCloseMs = NOTICE_MS }: Props) {
  useEffect(() => {
    if (message === null) return undefined;
    const timer = window.setTimeout(onClose, autoCloseMs);
    return () => window.clearTimeout(timer);
  }, [message, onClose, autoCloseMs]);
  if (message === null) return null;
  return (
    <div className="notice-banner" role="status">
      <span>{message}</span>
      <button type="button" onClick={onClose} aria-label="關閉">
        ×
      </button>
    </div>
  );
}
