// 行動列的操作說明句（Phase 6A-3，去文字化④）：每一種只在前 3 次完整出現，之後收進「?」圖示，滑過或點一下才看。
// 次數與讀寫規則在 `battle/opHints.ts`（本機儲存，失敗時當作 0 次）。
// 「一次」＝進入一次選取（`token` 換了才算新的一次，例如換了技能）；同一次選取中途不會從句子變成「?」。
import { useEffect, useRef } from "react";
import { bumpOpHint, showOpHint, type OpHintKind } from "../battle/opHints";
import { PartTip } from "./PartTip";

interface Props {
  kind: OpHintKind;
  /** 這一次選取的識別（技能或動作的 key、隊友指令的種類……）。 */
  token: string;
  /** 說明卡的標題（選取面板的標題，例如技能名稱）。 */
  label: string;
  text: string;
}

/** 這一次選取要不要完整顯示說明句；要的話記一次。 */
export function useOpHintFull(kind: OpHintKind, token: string): boolean {
  const decided = useRef<{ kind: OpHintKind; token: string; full: boolean } | null>(null);
  const cur = decided.current;
  if (cur === null || cur.token !== token || cur.kind !== kind) {
    decided.current = { kind, token, full: showOpHint(kind) };
  }
  const full = decided.current?.full ?? true;
  const counted = useRef<string | null>(null);
  useEffect(() => {
    const id = `${kind}:${token}`;
    if (!full || counted.current === id) return;
    counted.current = id; // StrictMode 的重跑 effect 不會多記一次
    bumpOpHint(kind);
  }, [kind, token, full]);
  return full;
}

/** 完整句子或「?」。 */
export function OpHintView({ full, label, text }: { full: boolean; label: string; text: string }) {
  if (full) return <div className="small muted op-hint">{text}</div>;
  return (
    <div className="small muted op-hint collapsed">
      <PartTip cat="操作說明" label={label} tip={text}>
        <span className="op-hint-q" data-testid="op-hint-q">
          ?
        </span>
      </PartTip>
    </div>
  );
}

export function OpHint({ kind, token, label, text }: Props) {
  const full = useOpHintFull(kind, token);
  return <OpHintView full={full} label={label} text={text} />;
}
