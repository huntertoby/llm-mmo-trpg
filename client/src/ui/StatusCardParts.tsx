// 主角狀態卡與單位小卡共用的零件（Phase 6A-2）：條、圖示＋數字、狀態／層數／表面圖示。
// 每個零件滑過都有說明卡（名稱、現值、一句說明）：條與圖示用 `Hint`（本身沒有動作，觸控點一下開說明，6A-1 規則），
// 狀態、層數、表面用 `PartTip`（點一下釘住）。畫法移植自 docs/art/sample/textless.html 的 symbol。
import type { ReactNode } from "react";
import type { SkillCard, StatusView } from "../api/types";
import { statusIconTile, surfaceTile } from "../render/skillIcon";
import { ChipGlyph, EffectGlyph } from "./SkillCardGlyphs";
import { Hint } from "./Hint";
import { DelayTrail } from "./MotionBits";
import { PartTip } from "./PartTip";
import { TileCanvas } from "./SkillIconView";
import { StackTip } from "./StackTip";
import { barFill, statusCorner, type BarData, type StatChip, type StatIcon } from "./statusCard";

const INK = "#1c1712";

/** 條：三條一樣粗，條上寫「HP 41 / 50」；HP 條上疊淺藍的護盾段。 */
export function StatBar({ bar }: { bar: BarData }) {
  const { fill, shieldLeft, shieldWidth } = barFill(bar.value, bar.max, bar.shield);
  return (
    <Hint text={bar.hint}>
      <div className={`stat-bar ${bar.kind}`} data-testid="stat-bar" role="img" aria-label={bar.text}>
        {bar.kind === "hp" && <DelayTrail ratio={fill} />}
        <i className="stat-bar-fill" style={{ width: `${fill * 100}%` }} />
        {bar.shield > 0 && <i className="stat-bar-shield" style={{ left: `${shieldLeft * 100}%`, width: `${shieldWidth * 100}%` }} />}
        <span className="stat-bar-text">{bar.text}</span>
      </div>
    </Hint>
  );
}

const STAT_PATHS: Partial<Readonly<Record<StatIcon, ReactNode>>> = {
  move: <path d="M6 2h5v9l6 2v4H6z" fill="#a07040" stroke={INK} strokeWidth="1.5" />,
  shield: <path d="M10 2l7 3v5c0 4-3 7-7 8-4-1-7-4-7-8V5z" fill="#9ab8d8" stroke={INK} strokeWidth="1.5" />,
  weapon: (
    <>
      <path d="M4 16L15 5" stroke={INK} strokeWidth="4" />
      <path d="M4 16L15 5" stroke="#dfe4ea" strokeWidth="2" />
      <path d="M3 11l6 6" stroke="#e8bb48" strokeWidth="2.5" />
    </>
  ),
  ammo: <rect x="7" y="3" width="6" height="14" rx="3" fill="#e8bb48" stroke={INK} strokeWidth="1.5" />,
};

export function StatGlyph({ icon }: { icon: StatIcon }) {
  if (icon === "ap" || icon === "mana" || icon === "source" || icon === "reaction") return <ChipGlyph icon={icon} />;
  return (
    <svg className="skill-chip-glyph" viewBox="0 0 20 20" width="16" height="16" aria-hidden="true">
      {STAT_PATHS[icon]}
    </svg>
  );
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
              <span key={i} className={`stat-pip ${chip.icon}${on ? " on" : ""}`} />
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
