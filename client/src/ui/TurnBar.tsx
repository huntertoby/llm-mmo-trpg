// 行動順序列（6A-4e 起放在戰鬥版 HUD 的上方中央）：每個單位一顆圓形小章（陣營底色、字母標記、HP 小條），
// 目前行動者亮金框。字母標記只在這裡與滑過單位的資訊卡上顯示（戰場上不畫）。回合、天氣、勝利條件移到右上 `BattleStatusBox`。
import type { BattleView } from "../api/types";
import { remainingRounds, summonKind } from "../battle/summons";
import { HIDDEN_INFO_HINT, hpValueText } from "../battle/hiddenInfo";
import { PRACTICE_BAR_ZH } from "../battle/skillTray";
import type { UnitNames } from "../battle/units";
import { Hint } from "./Hint";
import { TestModeBadge } from "./TestModeBadge";

interface Props {
  view: BattleView;
  names: UnitNames;
  /** 逐步播放時指定的行動者；省略時用 `view.active_unit`。 */
  acting?: string | null;
}

/**
 * PR-2b（#147 測試模式；樣張 `docs/art/OB與PR樣張.md` 第 3 節）：上方中央不放行動順序，改放這條提示——
 * 「測試模式」徽章（`TestModeBadge`，原樣重用）＋一句說明。`BattleScreen` 依 `view.practice` 二選一。
 */
export function PracticeBar() {
  return (
    <div className="practice-bar" role="status" data-testid="practice-bar">
      <TestModeBadge />
      <span className="practice-bar-text">{PRACTICE_BAR_ZH}</span>
    </div>
  );
}

export function TurnBar({ view, names, acting }: Props) {
  const byId = new Map(view.units.map((u) => [u.id, u]));
  const activeId = acting === undefined || acting === null ? view.active_unit : acting;
  return (
    <div className="turn-bar">
      <ol className="turn-order" aria-label={`行動順序（行動中：${activeId === null ? "—" : names.label(activeId)}）`}>
        {view.turn_order.map((id) => {
          const u = byId.get(id);
          const gone = u === undefined || u.downed || u.escaped || u.dismissed;
          const unknown = u !== undefined && u.hp === null; // HID-1：隱蔽敵人看不到 HP，條畫灰色整條
          const ratio = u === undefined || u.max_hp <= 0 ? 0 : u.hp === null ? 1 : Math.max(0, Math.min(1, u.hp / u.max_hp));
          const cls = [
            "turn-chip",
            u?.team ?? "",
            id === activeId ? "active" : "",
            gone ? "gone" : "",
            u?.owner_id == null ? "" : "summon",
            unknown ? "unknown" : "",
          ].join(" ");
          const kind = u === undefined ? null : summonKind(u);
          const left = u === undefined ? null : remainingRounds(view, u);
          const note =
            kind === null || u === undefined || u.owner_id === null
              ? ""
              : `　${kind}（${names.name(u.owner_id)}召喚${left === null ? "" : `，剩 ${left} 輪`}）`;
          const now = id === activeId ? "（行動中）" : "";
          return (
            <Hint key={id} text={`${names.label(id)}${now}　HP ${u === undefined ? 0 : hpValueText(u)} / ${u?.max_hp ?? 0}${note}${unknown ? `\n${HIDDEN_INFO_HINT}` : ""}`}>
              <li className={cls}>
                <span className="turn-chip-marker">{names.marker(id)}</span>
                {left !== null && <span className="turn-chip-left">{left}</span>}
                <span className="turn-chip-hp">
                  <span style={{ width: `${ratio * 100}%` }} />
                </span>
              </li>
            </Hint>
          );
        })}
      </ol>
    </div>
  );
}
