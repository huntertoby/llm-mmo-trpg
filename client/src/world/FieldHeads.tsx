// 實地地圖上人物頭頂的圖示層（Phase 6B-4；21.5、21.7）：疊在畫布上（跟著鏡頭一起平移），NPC 頭上畫好感表情、
// 有新傳聞或可接任務時多一個「！」、說了話時一個 1～2 句的對話泡泡；朋友（影子）頭上一個小名牌。
// 點圖示＝點那個人（同點格子：NPC 走過去開面板、朋友直接開名片）。純顯示：資料都來自伺服器的 `FieldView`。
import type { HeightGrid } from "../battle/elevation";
import { Hint } from "../ui/Hint";
import "./fieldPeople.css";
import { headAnchor, RANK_FACE, type HeadMark, type Rank } from "./fieldPeople";

/** 好感表情（圓臉＋眼睛＋依級別彎的嘴）。 */
export function RankFace({ rank, size = 18 }: { rank: Rank; size?: number }) {
  const face = RANK_FACE[rank];
  const m = face.mood;
  // 嘴：從 (6,12.5) 到 (14,12.5)，控制點往下（笑）或往上（不高興）
  const mouth = `M6 ${12.5 - m * 0.6} Q10 ${12.5 + m * 3.2} 14 ${12.5 - m * 0.6}`;
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" aria-hidden="true" className={`field-face rank-${rank}`}>
      <circle cx="10" cy="10" r="8.6" fill={face.color} stroke="#2b1e16" strokeWidth="1.4" />
      {rank === "hostile" && <path d="M5 6.2 L8.4 7.6 M15 6.2 L11.6 7.6" stroke="#2b1e16" strokeWidth="1.3" strokeLinecap="round" />}
      <circle cx="7.2" cy="8.6" r="1.15" fill="#2b1e16" />
      <circle cx="12.8" cy="8.6" r="1.15" fill="#2b1e16" />
      <path d={mouth} fill="none" stroke="#2b1e16" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

interface Props {
  marks: readonly HeadMark[];
  grid: HeightGrid;
  scale: number;
  onPick(mark: HeadMark): void;
}

export function FieldHeads({ marks, grid, scale, onPick }: Props) {
  return (
    <div className="field-heads" data-testid="field-heads">
      {marks.map((m) => {
        const at = headAnchor(grid, m.pos, scale);
        const hint = m.kind === "npc" ? [m.name, `好感：${m.rankZh}`, m.alertZh].filter(Boolean).join("・") : `${m.name}・點了看名片`;
        return (
          <div key={m.key} className={`field-head ${m.kind}`} style={{ left: at.left, top: at.top }} data-testid="field-head" data-head={m.key}>
            {m.bubble !== null && (
              <div className="field-bubble" data-testid="field-bubble">
                {m.bubble}
              </div>
            )}
            <Hint text={hint}>
              <button type="button" className="field-head-icons" onClick={() => onPick(m)} aria-label={hint}>
                {m.alert !== null && (
                  <span className={`field-alert ${m.alert}`} data-testid="field-alert" data-alert={m.alert}>
                    ！
                  </span>
                )}
                {m.rank !== null && (
                  <span data-testid="field-face" data-rank={m.rank}>
                    <RankFace rank={m.rank} />
                  </span>
                )}
                {m.kind === "friend" && (
                  <span className="field-friend-tag" data-testid="field-friend-tag">
                    影
                  </span>
                )}
              </button>
            </Hint>
          </div>
        );
      })}
    </div>
  );
}
