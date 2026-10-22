// 一句話說明（Phase 3-32b）：取代原生 `title=` 的共用浮動卡。包住任何一個元素（按鈕、標籤、晶片……），
// 滑過／取得鍵盤焦點時顯示一張只有文字的浮動卡，規則與技能卡、部件說明框相同（`useFloatCard`：延遲、橋接、Esc 關閉、貼齊、不出畫面、
// 超高時卡內捲動、portal 到 body）。按鈕本身有動作，所以不做「點一下釘住」（`pinOn: "never"`，同 `PartTip` 的 `pin={false}`）。
//
//   <Hint text="縮小（Ctrl＋滾輪）"><button …>－</button></Hint>
//
// 外框用 `display: contents`，不影響版面；卡片貼齊的是它的第一個子元素。`text` 為空就只渲染子元素。
import { useLayoutEffect, useRef, type ReactNode } from "react";
import { FloatCard, useFloatCard } from "./useFloatCard";

interface Props {
  text: string | null | undefined;
  children: ReactNode;
}

export function Hint({ text, children }: Props) {
  const f = useFloatCard({ pinOn: "never" });
  const wrap = useRef<HTMLSpanElement | null>(null);
  const { ref: _ref, ...handlers } = f.triggerProps;
  void _ref;
  useLayoutEffect(() => {
    const first = wrap.current?.firstElementChild;
    f.triggerRef.current = first instanceof HTMLElement ? first : wrap.current;
  });
  const shown = text !== null && text !== undefined && text !== "";
  return (
    <span ref={wrap} className="hint-tip" {...(shown ? handlers : {})}>
      {children}
      {shown && f.open && (
        <FloatCard float={f} className="part-tip-box hint-tip-box" align="center" role="tooltip">
          <div className="hint-tip-text">{text}</div>
        </FloatCard>
      )}
    </span>
  );
}
