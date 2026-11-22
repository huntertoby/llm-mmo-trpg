// E3b：種族被動加註（HUD 種族那行、角色面板「▸ 詳細」的種族列共用）：「被動「流線身形」・水的部分被身體的「〇〇」蓋過，其他有作用」。
// 灰色（`race-off`）只套在沒有作用的那一段（美術 E3 驗收小修 1）。
import type { RaceView } from "../api/types";
import { passiveSegments } from "../battle/race";

export function RacePassive({ race }: { race: RaceView }) {
  const segments = passiveSegments(race);
  return (
    <span className="race-passive">
      被動「{race.passive_name_zh}」
      {segments.length > 0 && "・"}
      {segments.map((p, i) =>
        p.off ? (
          <span key={i} className="race-off">
            {p.text}
          </span>
        ) : (
          <span key={i}>{p.text}</span>
        ),
      )}
    </span>
  );
}

/** 角色面板「▸ 詳細」的種族列：「鱗族・種族技「潮息」・被動「流線身形」・……」。 */
export function RaceDetail({ race }: { race: RaceView }) {
  return (
    <span className="race-detail">
      {race.name_zh}・種族技「{race.skill_name_zh}」・<RacePassive race={race} />
    </span>
  );
}
