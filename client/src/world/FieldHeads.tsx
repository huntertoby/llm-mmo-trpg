// 實地地圖上人物頭頂的圖示層（Phase 6B-4；21.5、21.7）：疊在畫布上（跟著鏡頭一起平移），NPC 頭上畫好感表情、
// 有新傳聞或可接任務時多一個「！」、說了話時一個 1～2 句的對話泡泡；朋友（影子）頭上一個小名牌。
// 點圖示＝點那個人（同點格子：NPC 走過去開面板、朋友直接開名片）。純顯示：資料都來自伺服器的 `FieldView`。
import type { HeightGrid } from "../battle/elevation";
import { Hint } from "../ui/Hint";
import "./fieldPeople.css";
import { headAnchor, RANK_FACE, type HeadMark, type Rank } from "./fieldPeople";
import type { Rect } from "./hud";
import { placeTag, steleRect, tagSize } from "./hudAvoid";
import { EDGE_ARROW, guideAnchor, type SteleTag, type ViewBox } from "./opening";

/** 小鎖頭（灰色；沒開放的石碑小牌，RT-5）。 */
function LockGlyph() {
  return (
    <svg width="9" height="11" viewBox="0 0 9 11" aria-hidden="true" className="field-stele-lock">
      <path d="M2 5 V3.4 a2.5 2.5 0 0 1 5 0 V5" fill="none" stroke="currentColor" strokeWidth="1.3" />
      <rect x="0.8" y="4.8" width="7.4" height="5.6" rx="1.2" fill="currentColor" />
    </svg>
  );
}

/**
 * 橋頭石碑上方的小牌（RT-5 ②）：已開放寫區名（該區顏色的細框）；沒開放的灰色加鎖，第二行「尚未開放」或「之後的賽季」。
 * 只畫、不接滑鼠（點石碑照舊開那一區的傳送選單）。開放狀態照大世界圖（`steleTags`）。
 * RT-5b（必修 1、2）：預設在石碑上方；壓到 HUD（`avoid`，舞台座標；`cam`、`view`＝鏡頭與舞台大小）時換到石碑的左、右或下方。
 */
export function FieldSteleTags({
  tags,
  grid,
  scale,
  colors,
  cam = null,
  view = null,
  avoid = [],
}: {
  tags: readonly SteleTag[];
  grid: HeightGrid;
  scale: number;
  colors: Readonly<Record<string, string>>;
  cam?: { x: number; y: number } | null;
  view?: { width: number; height: number } | null;
  avoid?: readonly Rect[];
}) {
  if (tags.length === 0) return null;
  return (
    <div className="field-heads field-steles" data-testid="field-stele-tags">
      {tags.map((t) => {
        const at = placeTag(steleRect(grid, { x: t.x, y: t.y }, scale), tagSize(t.name, t.sub), cam, view, avoid);
        const style = { left: at.left, top: at.top, ...(t.status === "open" ? { borderColor: colors[t.region] ?? "#c8a868" } : {}) };
        return (
          <div key={t.id} className={`field-stele-tag ${t.status}`} style={style} data-testid="field-stele-tag" data-region={t.region} data-status={t.status} data-side={at.side}>
            <span className="field-stele-name">{t.name}</span>
            {t.sub !== "" && (
              <span className="field-stele-sub">
                <LockGlyph />
                {t.sub}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

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
  /** 點了收起來的開場指示（只剩「！」）：再展開整句（RT-5b 必修 6）；省略＝照 `onPick`。 */
  onExpand?(mark: HeadMark): void;
  /** 畫面上看得到的範圍（畫布座標）：開場說話的人在畫面外時，「！」和泡泡夾到畫面邊上（RT-5）；省略＝照原位。 */
  view?: ViewBox | null;
  /** 整個可視區（判斷人在不在畫面裡；省略＝用 `view`）。 */
  visible?: ViewBox | null;
}

export function FieldHeads({ marks, grid, scale, onPick, onExpand, view = null, visible = null }: Props) {
  return (
    <div className="field-heads" data-testid="field-heads">
      {marks.map((m) => {
        const head = headAnchor(grid, m.pos, scale);
        const guide = m.kind === "figure" ? guideAnchor(head, view, visible) : null;
        const at = guide ?? head;
        const hint =
          m.kind === "npc"
            ? [m.name, `好感：${m.rankZh}`, m.alertZh].filter(Boolean).join("・")
            : m.kind === "figure"
              ? [m.name, m.alertZh, m.folded ? "點了看指示" : null].filter(Boolean).join("・")
              : `${m.name}・點了看名片`;
        const edge = guide !== null && guide.edge !== "" ? (EDGE_ARROW[guide.edge] ?? "") : "";
        return (
          <div
            key={m.key}
            className={`field-head ${m.kind}${guide !== null && guide.edge !== "" ? " edge" : ""}`}
            style={{ left: at.left, top: at.top }}
            data-testid="field-head"
            data-head={m.key}
            data-edge={guide?.edge || undefined}
            data-guide={m.kind === "figure" ? (m.folded ? "folded" : "open") : undefined}
          >
            {m.bubble !== null && (
              <div className={`field-bubble${guide !== null ? ` guide ${guide.side}` : ""}`} data-testid="field-bubble">
                {guide !== null && (
                  <b className="field-bubble-name">
                    {m.name}
                    {edge !== "" && <span className="field-bubble-edge">{edge}</span>}
                  </b>
                )}
                {m.bubble}
              </div>
            )}
            <Hint text={hint}>
              <button type="button" className="field-head-icons" onClick={() => (m.folded && onExpand !== undefined ? onExpand(m) : onPick(m))} aria-label={hint}>
                {m.alert !== null && (
                  <span className={`field-alert ${m.alert}${m.main ? " main" : ""}`} data-testid="field-alert" data-alert={m.alert} data-main={m.main ? "1" : undefined}>
                    ！
                  </span>
                )}
                {m.folded && edge !== "" && <span className="field-bubble-edge folded">{edge}</span>}
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
