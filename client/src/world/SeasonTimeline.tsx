// 賽季時間軸（PNL-1b；docs/art/資訊面板-移植需求.md 2.2 `SeasonTimeline`、3.3「賽季時程」；樣張 `infoPanels.js` 的 `timeline()`、`.ip-tl`）：
// 橫 N 格（賽季天數）× 5 列——第 1 列時間點釘（下一個加亮金圈；滑過說明卡寫「第 N 天 名稱」）、第 2 列天（今天亮金膠囊）、
// 第 3 列階段（今天所在段金色；滑過寫說明）、第 4～5 列世界事件（重疊的排第二列、進行中綠底）；列名 L3。格子算法在 `boardTabs.ts`。
import type { BoardWorldEventView, SeasonInfoView } from "../api/types";
import { crestId } from "../render/qIcon/hud";
import { Hint } from "../ui/Hint";
import { EventBare, HudBare, LockGlyph } from "../ui/PanelKit";
import { BOARD_ZH, dayColumns, pinIcon, timelineLayout, type MilestoneKind } from "./boardTabs";

/** 釘裡的小圖（2.3；說書人放大一號，提案第 2 版複審可修 2）。 */
function PinGlyph({ kind }: { kind: MilestoneKind }) {
  const icon = pinIcon(kind);
  if (icon === "narrator") return <EventBare id="narrator" px={17} />;
  if (icon === "lock") return <LockGlyph px={16} />;
  if (icon === "shadow") return <HudBare id="bar_Y" px={15} />;
  return <HudBare id="t_telegraph" px={15} />;
}

/** 世界事件條上的紋章（2.3）：區域紋章，沒有區域＝源晶。 */
export function EventCrest({ region, px }: { region: string | null | undefined; px: number }) {
  return <HudBare id={region != null && region !== "" ? crestId(region) : "r_source"} px={px} />;
}

export function SeasonTimeline({ season, events }: { season: SeasonInfoView; events: readonly BoardWorldEventView[] }) {
  const t = timelineLayout(season, events);
  const [rowPins, rowDays, rowPhases, rowEvents] = BOARD_ZH.timelineRows;
  const evRow0 = 4;
  return (
    <div className="pnl-tl" style={{ ["--days" as string]: t.days }} role="group" aria-label={BOARD_ZH.timelineRows.join("、")} data-testid="world-board-timeline">
      <span className="pnl-tl-lab" style={{ gridRow: 1 }}>
        {rowPins}
      </span>
      {t.pins.map((p) => (
        <span key={`pin-${p.day}`} className="pnl-tl-mk" style={{ gridColumn: String(p.day + 1), gridRow: 1 }}>
          <Hint text={`第 ${p.day} 天　${p.names.join("；")}`}>
            <span className={`pnl-tl-pin${p.next ? " next" : ""}${p.past ? " past" : ""}`} tabIndex={0} role="img" aria-label={`第 ${p.day} 天 ${p.names.join("；")}`} data-day={p.day} data-kinds={p.kinds.join(" ")}>
              {p.kinds.map((k) => (
                <PinGlyph key={k} kind={k} />
              ))}
            </span>
          </Hint>
        </span>
      ))}
      <span className="pnl-tl-lab" style={{ gridRow: 2 }}>
        {rowDays}
      </span>
      {Array.from({ length: t.days }, (_, i) => i + 1).map((d) => (
        <span key={`day-${d}`} className={d === t.today ? "pnl-tl-day today" : "pnl-tl-day"} style={{ gridColumn: String(d + 1), gridRow: 2 }} data-today={d === t.today ? "1" : undefined}>
          {d}
        </span>
      ))}
      <span className="pnl-tl-lab" style={{ gridRow: 3 }}>
        {rowPhases}
      </span>
      {t.segs.map((s) => (
        <Hint key={`seg-${s.phase.id}`} text={`第 ${s.phase.start_day}～${s.phase.end_day} 天　${s.phase.name_zh}${s.phase.text_zh !== "" ? `：${s.phase.text_zh}` : ""}`}>
          <span className={`pnl-tl-seg${s.now ? " now" : ""}${s.alt ? " c2" : ""}`} style={{ gridColumn: dayColumns(s.phase.start_day, s.phase.end_day), gridRow: 3 }} tabIndex={0} data-phase={s.phase.id}>
            {s.phase.name_zh}
          </span>
        </Hint>
      ))}
      <span className="pnl-tl-lab" style={{ gridRow: `${evRow0} / ${evRow0 + t.lanes}` }}>
        {rowEvents}
      </span>
      {t.events.map((e) => (
        <Hint key={`ev-${e.event.event}`} text={`${e.event.name_zh}　${e.event.days_zh}・${e.event.status_zh}`}>
          <span className={e.now ? "pnl-tl-ev now" : "pnl-tl-ev"} style={{ gridColumn: dayColumns(e.event.start_day, e.event.end_day), gridRow: evRow0 + e.lane }} tabIndex={0} data-event={e.event.event} data-lane={e.lane}>
            <EventCrest region={e.event.region} px={13} />
            <span className="nm">{e.event.name_zh}</span>
          </span>
        </Hint>
      ))}
    </div>
  );
}
