// 介面小動畫（Phase 6N-10；動畫方案 2.8）：延遲血條、數字翻動。只讀伺服器畫面的數值，不改任何東西。
// - 延遲血條（`DelayTrail`）：放在血條裡、填色的下面。掉血時填色馬上變短，白色殘量停 0.35 秒再用 0.6 秒縮回；
//   補血時殘量也慢慢變長，但被填色蓋住看不到。純 CSS 轉場（uiMotion.css），沒有計時器。
// - 數字翻動（`FlipNumber`）：值變了才翻一下（第一次畫出來不翻），例如升級時 HUD 的 Lv。
// - 系統設定減少動態時：CSS 媒體查詢把轉場、翻動關掉，直接顯示新的值。
import { useRef } from "react";
import "./uiMotion.css";

/** 殘量的寬度（0～1；超出範圍或不是數字時夾住）。 */
export function trailWidth(ratio: number): string {
  const r = Number.isFinite(ratio) ? Math.max(0, Math.min(1, ratio)) : 0;
  return `${Math.round(r * 1000) / 10}%`;
}

export function DelayTrail({ ratio }: { ratio: number }) {
  return <i className="delay-trail" data-testid="delay-trail" style={{ width: trailWidth(ratio) }} aria-hidden="true" />;
}

export function FlipNumber({ value, children }: { value: number | string; children?: React.ReactNode }) {
  const first = useRef(value);
  const changed = value !== first.current;
  return (
    <span key={String(value)} className={`flip-num${changed ? " flip" : ""}`} data-flip={changed ? "1" : "0"}>
      {children ?? value}
    </span>
  );
}
