// 「製造：點燃｜利用：倒地」一行（Phase 3-24b1）：每個關鍵字都是 PartTip，滑過或點一下看說明。
// 技能卡、技能列的浮動卡、技能工坊的即時檢查共用。
// Phase 3-41a：只由通用規則推導的關鍵字標灰，說明附上歸類理由（暫定的由後端過濾，不會出現）。
import type { KeywordRef, SkillKeywords } from "../api/types";
import { noKeywords } from "./keywords";
import { PartTip } from "./PartTip";

function Side({ label, refs }: { label: string; refs: readonly KeywordRef[] }) {
  return (
    <span className="keyword-side">
      {label}：
      {refs.length === 0 && <span className="muted">無</span>}
      {refs.map((k, i) => (
        <span key={k.id}>
          {i > 0 && "、"}
          <PartTip
            cat={k.general === true ? "關鍵字（通用歸類）" : "關鍵字"}
            label={k.name_zh}
            tip={k.general === true && k.reason_zh != null ? `${k.description_zh}（通用歸類：${k.reason_zh}）` : k.description_zh}
            className={k.general === true ? "keyword-chip general" : "keyword-chip"}
          >
            {k.name_zh}
            {k.variant === true && <span className="muted small">（特定地形）</span>}
          </PartTip>
        </span>
      ))}
    </span>
  );
}

interface Props {
  keywords: SkillKeywords;
  /** 沒有任何關鍵字時顯示的字（工坊草稿剛開始）；省略就整行不顯示。 */
  empty?: string;
}

export function KeywordLine({ keywords, empty }: Props) {
  if (noKeywords(keywords)) {
    return empty === undefined ? null : <div className="small muted keyword-line">{empty}</div>;
  }
  return (
    <div className="small keyword-line" aria-label="關鍵字">
      <Side label="製造" refs={keywords.makes} />
      <span className="keyword-sep">｜</span>
      <Side label="利用" refs={keywords.uses} />
    </div>
  );
}
