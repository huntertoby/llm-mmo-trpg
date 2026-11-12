// 主角狀態卡與單位小卡共用的零件（Phase 6A-2）：條、圖示＋數字、狀態／層數／表面圖示。
// 每個零件滑過都有說明卡（名稱、現值、一句說明）：條與圖示用 `Hint`（本身沒有動作，觸控點一下開說明，6A-1 規則），
// 狀態、層數、表面用 `PartTip`（點一下釘住）。畫法移植自 docs/art/sample/textless.html 的 symbol。
import type { SkillCard, StatusView } from "../api/types";
import { SOURCE_PIP_PX, sourcePipId, STAT_ICON_ID } from "../render/hudIcon";
import { statusIconTile, surfaceTile } from "../render/skillIcon";
import { CARD_GLYPH_PX, ChipGlyph, EffectGlyph } from "./SkillCardGlyphs";
import { HudGlyph } from "./HudGlyph";
import { Hint } from "./Hint";
import { DelayTrail } from "./MotionBits";
import { PartTip } from "./PartTip";
import { TileCanvas } from "./SkillIconView";
import { StackTip } from "./StackTip";
import { barFill, statusCorner, type BarData, type StatChip, type StatIcon } from "./statusCard";

/** 條：三條一樣粗，條上寫「HP 41 / 50」；HP 條上疊淺藍的護盾段。 */
export function StatBar({ bar }: { bar: BarData }) {
  const { fill, shieldLeft, shieldWidth } = barFill(bar.value, bar.max, bar.shield);
  return (
    <Hint text={bar.hint}>
      <div className={`stat-bar ${bar.kind}${bar.unknown === true ? " unknown" : ""}`} data-testid="stat-bar" role="img" aria-label={bar.text}>
        {bar.kind === "hp" && <DelayTrail ratio={fill} />}
        <i className="stat-bar-fill" style={{ width: `${fill * 100}%` }} />
        {bar.shield > 0 && <i className="stat-bar-shield" style={{ left: `${shieldLeft * 100}%`, width: `${shieldWidth * 100}%` }} />}
        <span className="stat-bar-text">{bar.text}</span>
      </div>
    </Hint>
  );
}

/** 資源小圖（16px）：AP、法力、源力、反應＝第④批卡片小圖（`ChipGlyph`）；移動、護盾、武器、彈藥＝第⑦批 Q 版（QI-5，`render/qIcon/hud.ts`，同一條卡片小圖路徑）。 */
export function StatGlyph({ icon }: { icon: StatIcon }) {
  if (icon === "ap" || icon === "mana" || icon === "source" || icon === "reaction") return <ChipGlyph icon={icon} />;
  return <HudGlyph id={STAT_ICON_ID[icon]} px={CARD_GLYPH_PX.chip} className="skill-chip-glyph" />;
}

/** 一個資源圓點：源力（QI-5）是 9px 小晶石 canvas（亮＝晶石、暗＝同形紫框深底）；AP、彈藥照舊是 CSS 的圓點。 */
function StatPip({ icon, on }: { icon: StatIcon; on: boolean }) {
  if (icon === "source") return <HudGlyph id={sourcePipId(on)} px={SOURCE_PIP_PX} className={`stat-pip source${on ? " on" : ""}`} />;
  return <span className={`stat-pip ${icon}${on ? " on" : ""}`} />;
}

/** 圖示＋數字（或圓點）；用過或沒有了變灰。 */
export function StatChipView({ chip }: { chip: StatChip }) {
  return (
    <Hint text={chip.hint}>
      <span className={`stat-chip${chip.dim ? " dim" : ""}`} data-testid={`stat-chip-${chip.key}`} aria-label={chip.hint.split("\n")[0]}>
        <StatGlyph icon={chip.icon} />
        {chip.pips !== null && (
          <span className="stat-pips">
            {chip.pips.map((on, i) => (
              <StatPip key={i} icon={chip.icon} on={on} />
            ))}
          </span>
        )}
        {chip.label !== "" && <b>{chip.label}</b>}
      </span>
    </Hint>
  );
}

/** 狀態圖示，右下角寫回合數或數值；滑過看「狀態句＋說明」。 */
export function StatusBadge({ status, text }: { status: StatusView; text: string }) {
  const tile = statusIconTile(status.status_id);
  const corner = statusCorner(status);
  return (
    <PartTip cat="狀態" label={text} tip={tile.tip} className="stat-badge status-badge">
      <TileCanvas tile={tile} px={20} />
      {corner !== "" && <b className="stat-corner">{corner}</b>}
    </PartTip>
  );
}

/** 層數圖示，右下角寫層數；滑過看層數說明（`StackTip`）。 */
export function StackBadge({ id, count, cards, owned }: { id: string; count: number; cards?: Readonly<Record<string, SkillCard | undefined>>; owned: readonly string[] | null }) {
  return (
    <StackTip id={id} cards={cards} owned={owned}>
      <span className="stat-badge stack-badge" data-stack={id}>
        <EffectGlyph icon="stack" element={null} />
        <b className="stat-corner">{count}</b>
      </span>
    </StackTip>
  );
}

/** 腳下的表面圖示；滑過看「名稱（剩餘輪數）＋規則」。 */
export function SurfaceBadge({ surface, text }: { surface: string; text: string }) {
  const tile = surfaceTile(surface);
  return (
    <PartTip cat="腳下表面" label={text} tip={tile.tip} className="stat-badge surface-badge">
      <TileCanvas tile={tile} px={20} />
    </PartTip>
  );
}
