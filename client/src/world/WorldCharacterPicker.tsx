// 大世界的角色畫面（Phase 5A-5）：列出既有角色、建立新角色（07 7.6 創角：起始武器＋2 個關鍵字；種族與出身同一輪開局）。
// 帳號是 5E-1：這裡不登入，角色以伺服器產生的 ID 存取。
import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { WorldCharacterSummary, WorldView } from "../api/types";
import { RaceOriginPicker } from "../run/RaceOriginPicker";
import { raceOriginBody, raceOriginDone, type RaceOriginChoice } from "../run/raceOrigin";
import { StartPickerView, useStartPicker } from "../run/StartPicker";
import { ErrorBanner } from "../ui/ErrorBanner";
import { randomSeed } from "../screens/StartScreen";
import { NAME_MAX, nameProblem } from "./mapView";

interface Props {
  onEnter(characterId: string, first?: WorldView): void;
  onHome(): void;
}

export function WorldCharacterPicker({ onEnter, onHome }: Props) {
  const [chars, setChars] = useState<WorldCharacterSummary[] | null>(null);
  const [name, setName] = useState("");
  const [seed] = useState(() => randomSeed());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const picker = useStartPicker(seed, false);
  const [raceOrigin, setRaceOrigin] = useState<RaceOriginChoice>({ race: "", origin: "" });

  useEffect(() => {
    let cancelled = false;
    api.worldCharacters().then(
      (list) => !cancelled && setChars(list),
      (e: unknown) => !cancelled && setError(e instanceof Error ? e.message : String(e)),
    );
    return () => {
      cancelled = true;
    };
  }, []);

  const problem = nameProblem(name);
  const ready = problem === null && picker.body !== null && raceOriginDone(picker.options, raceOrigin);

  async function create(e: FormEvent) {
    e.preventDefault();
    if (!ready) return;
    setBusy(true);
    setError(null);
    try {
      const view = await api.createWorldCharacter({
        name: name.trim(),
        weapon: picker.weapon,
        keywords: picker.selected,
        seed,
        race: null,
        origin: null,
        ...raceOriginBody(raceOrigin),
      });
      onEnter(view.character.character_id, view);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  return (
    <div className="start-screen world-pick">
      <h1>大世界（測試）</h1>
      <ErrorBanner message={error ?? picker.error} onClose={() => setError(null)} />
      <div className="panel">
        <div className="section-title">我的角色</div>
        {chars === null && <div className="muted small">載入中……</div>}
        {chars !== null && chars.length === 0 && <div className="muted small">還沒有角色，先在下面建立一個。</div>}
        {chars?.map((c) => (
          <div key={c.character_id} className="run-save-row" data-testid="world-char-row">
            <span>
              {c.name}・Lv {c.level}
              <span className="muted small">　{c.region_name_zh}・{c.location_name_zh}</span>
            </span>
            <button type="button" className="primary" onClick={() => onEnter(c.character_id)}>
              進入
            </button>
          </div>
        ))}
      </div>
      <form className="panel start-form" onSubmit={(e) => void create(e)}>
        <div className="section-title">建立新角色</div>
        <label>
          名稱
          <input
            value={name}
            maxLength={NAME_MAX}
            onChange={(e) => setName(e.target.value)}
            aria-invalid={problem !== null}
            data-testid="world-name"
          />
        </label>
        <RaceOriginPicker options={picker.options} choice={raceOrigin} onChoice={setRaceOrigin} disabled={busy} />
        <StartPickerView picker={picker} disabled={busy} />
        <div className="muted small">
          屬性點照預設（全部點在起始技能最常用的屬性）；角色從雲嶺的霧渡鎮出發。隊友：一開始帶系統傭兵鐵壁、回春，可以在城鎮免費改成別的傭兵、借朋友的影子（最多 2 名）或獨行。
        </div>
        <div className="run-actions">
          <button type="submit" className="primary" disabled={busy || !ready}>
            {busy ? "建立中……" : "建立並進入"}
          </button>
          <button type="button" onClick={onHome}>
            返回首頁
          </button>
          {name !== "" && problem !== null && <span className="error-text small">{problem}</span>}
        </div>
      </form>
    </div>
  );
}
