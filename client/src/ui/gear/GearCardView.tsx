// 一件可以換上的裝備卡（戰後三選一的候選、營火的背包；Phase 3K-2）：圖示、名稱、部位・稀有度・物品等級、
// 基礎加成與詞條，下方和該欄位目前的裝備比較（目前的裝備圖示可滑過看說明，共用浮動卡 `PartTip`）。
import type { GearCandidate } from "../../api/types";
import { compareText, compareTone, itemLines, itemSubtitle, itemTipLines, noteLines, rarityClass } from "../../run/gearOffer";
import { GearIcon } from "../GearIcon";
import { PartTip } from "../PartTip";

export function GearCardView({ cand }: { cand: GearCandidate }) {
  const { item, current } = cand;
  const lines = itemLines(item);
  const now = current == null ? [] : itemLines(current);
  return (
    <div className={`gear-card ${rarityClass(item)}`} data-testid="gear-card" data-slot={cand.slot}>
      <div className="gear-card-head">
        <GearIcon look={item.appearance} slot={cand.slot} size={64} label={item.name_zh} />
        <div className="gear-card-headtext">
          <div className="gear-card-title">
            {item.name_zh}
            {item.rarity_zh != null && <span className="gear-rarity-badge"> {item.rarity_zh}</span>}
          </div>
          <div className="small muted" data-testid="gear-card-sub">
            {cand.slot_zh}・{itemSubtitle(item)}
          </div>
        </div>
      </div>
      <ul className="gear-card-lines" data-testid="gear-card-lines">
        {lines.length === 0 ? (
          <li className="muted">沒有詞條</li>
        ) : (
          lines.map((text, i) => <li key={`${i}:${text}`}>{text}</li>)
        )}
      </ul>
      {noteLines(cand).map((note) => (
        <div key={note} className="gear-card-note small" data-testid="gear-card-note">
          {note}
        </div>
      ))}
      <div className={`gear-card-compare tone-${compareTone(cand)}`} data-testid="gear-card-compare">
        <div className="gear-card-current">
          {current == null ? (
            <span className="muted">目前的{cand.slot_zh}：空</span>
          ) : (
            <>
              <PartTip
                cat={`目前的${cand.slot_zh}`}
                label={current.name_zh}
                tip=""
                lines={itemTipLines(current)}
              >
                <GearIcon look={current.appearance} slot={cand.slot} size={32} label={current.name_zh} />
              </PartTip>
              <span>
                目前：{current.name_zh}
                <span className="muted small"> {itemSubtitle(current)}</span>
              </span>
            </>
          )}
        </div>
        {now.length > 0 && <div className="small muted">{now.join("；")}</div>}
        <div className="small gear-card-score">{compareText(cand)}</div>
      </div>
    </div>
  );
}
