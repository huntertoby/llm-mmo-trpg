// 這一季的免費換種族（Phase 6R-1，#138：狐族改成獸耳族，本季開放一次；不佔 #108 那一次）。
// 不另做新畫面：在世界側欄的角色狀態下面加一行（伺服器說還能換才出現，`free_race_change`），
// 選種族、按「換種族」送 `change_race`。不在主城等原因（`free_race_change_zh`）照字顯示、按鈕灰掉。
import { useState } from "react";
import type { WorldAction, WorldView } from "../api/types";
import { RACE_NAMES } from "../run/createTexts";

/** 純函式：可以換成的種族（資料順序，去掉目前的種族）。 */
export function raceChangeOptions(current: string | null, names: readonly { id: string; name: string }[] = RACE_NAMES): { id: string; name: string }[] {
  return names.filter((r) => r.id !== current);
}

/** 純函式：換種族的世界動作。 */
export function raceChangeAction(race: string): WorldAction {
  return { kind: "change_race", race };
}

interface Props {
  character: WorldView["character"];
  busy: boolean;
  onAct(action: WorldAction): void;
}

export function RaceChangeLine({ character, busy, onAct }: Props) {
  const options = raceChangeOptions(character.race ?? null);
  const [pick, setPick] = useState(options[0]?.id ?? "");
  const reason = character.free_race_change_zh ?? null;
  const blocked = busy || reason !== null || pick === "";
  const go = () => {
    const name = options.find((o) => o.id === pick)?.name ?? pick;
    if (typeof window === "undefined" || window.confirm(`換成${name}？這一季的免費換種族只有一次。`)) onAct(raceChangeAction(pick));
  };
  return (
    <div className="small world-race-change" data-testid="world-race-change">
      本季可以免費換一次種族：
      <select value={pick} disabled={busy || reason !== null} onChange={(e) => setPick(e.target.value)} aria-label="新種族">
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.name}
          </option>
        ))}
      </select>{" "}
      <button type="button" disabled={blocked} onClick={go}>
        換種族
      </button>
      {reason !== null && <span className="muted">（{reason}）</span>}
    </div>
  );
}
