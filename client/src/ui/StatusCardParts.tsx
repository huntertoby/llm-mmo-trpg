// 主角狀態卡與單位小卡共用的零件（Phase 6A-2）：條、圖示＋數字、狀態／層數／表面圖示。
// 每個零件滑過都有說明卡（名稱、現值、一句說明）：條與圖示用 `Hint`（本身沒有動作，觸控點一下開說明，6A-1 規則），
// 狀態、層數、表面用 `PartTip`（點一下釘住）。畫法移植自 docs/art/sample/textless.html 的 symbol。
import { useEffect, useRef } from "react";
import type { SkillCard, StatusView } from "../api/types";
import { SOURCE_PIP_PX, sourcePipId, STAT_ICON_ID } from "../render/hudIcon";
import { statusIconTile, surfaceTile } from "../render/skillIcon";
import { CARD_PAD, spreadMarkCardCanvas } from "../render/spreadMark";
import { iconCanvasPx } from "../render/weaponIcon";
import { CARD_GLYPH_PX, ChipGlyph, EffectGlyph } from "./SkillCardGlyphs";
import { HudGlyph } from "./HudGlyph";
import { Hint } from "./Hint";
import { DelayTrail } from "./MotionBits";
import { PartTip } from "./PartTip";
import { TileCanvas } from "./SkillIconView";
import { StackTip } from "./StackTip";
import { barFill, statusCorner, type ApPip, type ApRow, type BarData, type StatChip, type StatIcon } from "./statusCard";

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

/** AP 列的一顆圓點（AP-1）：每顆有自己的說明卡。 */
function ApPipView({ pip }: { pip: ApPip }) {
  const cls = ["stat-pip", "ap", pip.kind === "ap" ? "" : pip.kind, pip.on ? "on" : "", pip.keep ? "keep" : "", pip.fresh === true ? "fresh" : ""];
  return (
    <Hint text={pip.hint}>
      <span className={cls.filter((c) => c !== "").join(" ")} data-ap-pip={pip.kind} aria-label={pip.hint.split("\n")[0]} />
    </Hint>
  );
}

/**
 * AP 列（AP-1，docs/art/AP-1-AP列畫法.md）：`[這回合] ｜ [下回合會少的]`。整格不包一層說明卡（每顆圓點各有說明，
 * 外層再包會兩張卡打架），圖示自己帶 AP 的說明。
 */
function ApChipView({ chip, row }: { chip: StatChip; row: ApRow }) {
  return (
    <span className={`stat-chip ap-row${chip.dim ? " dim" : ""}`} data-testid={`stat-chip-${chip.key}`} aria-label={chip.hint.split("\n")[0]}>
      <Hint text={chip.hint}>
        <span className="ap-row-glyph">
          <StatGlyph icon={chip.icon} />
        </span>
      </Hint>
      <span className="stat-pips">
        {row.now.map((p, i) => (
          <ApPipView key={`n${i}`} pip={p} />
        ))}
        {row.next.length > 0 && <i className="stat-pip-sep" aria-hidden="true" />}
        {row.next.map((p, i) => (
          <ApPipView key={`x${i}`} pip={p} />
        ))}
      </span>
    </span>
  );
}

/** 圖示＋數字（或圓點）；用過或沒有了變灰。 */
export function StatChipView({ chip }: { chip: StatChip }) {
  if (chip.apRow !== undefined) return <ApChipView chip={chip} row={chip.apRow} />;
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

/** AR-SK2：狀態帶「會擴散」時，狀態卡的標籤與多一行的說明（玩法 PM 定案，交接 4.1.28 第 6 點）。 */
export const SPREAD_TAG = "會擴散";
export const SPREAD_NOTE = "會擴散：帶著這個狀態倒下時，以剩下的回合傳給身邊 1 格內的一名同伴；身上有好幾種時只傳一種，傳過去的仍會擴散。";

/** 狀態圖示，右下角寫回合數或數值；滑過看「狀態句＋說明」。帶「會擴散」時框頂上方疊記號、說明多一行。 */
export function StatusBadge({ status, text }: { status: StatusView; text: string }) {
  const tile = statusIconTile(status.status_id);
  const corner = statusCorner(status);
  const spread = status.contagious === true;
  const tip = spread ? (tile.tip === "" ? SPREAD_NOTE : `${tile.tip}
${SPREAD_NOTE}`) : tile.tip;
  return (
    <PartTip cat="狀態" label={text} tip={tip} className="stat-badge status-badge" {...(spread ? { tags: [SPREAD_TAG] } : {})}>
      <TileCanvas tile={tile} px={20} />
      {spread && <SpreadMark px={20} />}
      {corner !== "" && <b className="stat-corner">{corner}</b>}
    </PartTip>
  );
}

/** AR-SK2：狀態卡 20 的「會擴散」記號：圖示四周各多 `CARD_PAD`，疊在圖示上、不裁切（往上凸出約 7 px）。 */
function SpreadMark({ px }: { px: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    const src = spreadMarkCardCanvas(px);
    if (canvas == null || ctx == null || src === null) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(src, 0, 0);
  }, [px]);
  const side = px + 2 * CARD_PAD;
  return <canvas ref={ref} className="stat-spread" width={iconCanvasPx(side)} height={iconCanvasPx(side)} style={{ width: side, height: side }} aria-hidden="true" />;
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
