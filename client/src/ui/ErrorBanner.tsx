// 錯誤提示（400／409／500 的 detail）；可關閉，不會卡住畫面。
interface Props {
  message: string | null;
  onClose(): void;
}

export function ErrorBanner({ message, onClose }: Props) {
  if (message === null) return null;
  return (
    <div className="error-banner" role="alert">
      <span>{message}</span>
      <button type="button" onClick={onClose} aria-label="關閉">
        ×
      </button>
    </div>
  );
}
