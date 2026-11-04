// 錯誤提示（400／409／500 的 detail）；可關閉，不會卡住畫面。
// AU-2：出現時放錯誤介面音。
import { useEffect } from "react";
import { uiSound } from "../audio/uiSounds";

interface Props {
  message: string | null;
  onClose(): void;
}

export function ErrorBanner({ message, onClose }: Props) {
  useEffect(() => {
    if (message !== null) uiSound("ui_error");
  }, [message]);
  if (message === null) return null;
  return (
    <div className="error-banner" role="alert">
      <span>{message}</span>
      <button data-sfx="ui_cancel" type="button" onClick={onClose} aria-label="關閉">
        ×
      </button>
    </div>
  );
}
