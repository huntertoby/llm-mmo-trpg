// 層數名稱的說明框（Phase 3-41c）：滑過層數（狀態列、單位資訊、技能卡）顯示一般說明，
// 有持有者時再列出你的技能中會累積／消耗它的。浮動卡用共用的 <Hint>（規則見 docs/開發PM交接.md 6.5.1）。
import type { ReactNode } from "react";
import type { SkillCard } from "../api/types";
import { stackName } from "../battle/glossary";
import { stackHintText } from "../battle/stackInfo";
import { Hint } from "./Hint";

interface Props {
  id: string;
  /** 顯示的內容；省略時為層數名稱。 */
  children?: ReactNode;
  /** 技能卡（技能 ID → 卡片），用來列出「你的技能」。 */
  cards?: Readonly<Record<string, SkillCard | undefined>>;
  /** 持有者的技能 ID；`null`（工坊、沒有持有者）只寫一般說明。 */
  owned?: readonly string[] | null;
}

export function StackTip({ id, children, cards = {}, owned = null }: Props) {
  return (
    <Hint text={stackHintText(id, cards, owned)}>
      <span className="stack-tip">{children ?? stackName(id)}</span>
    </Hint>
  );
}
