// 大世界的角色畫面（Phase 5A-5）：列出既有角色、建立新角色（07 7.6 創角：起始武器＋2 個關鍵字；種族與出身同一輪開局）。
// 5E-1：已登入時只列自己的角色、顯示帳號與角色上限、可以登出；開發模式沒登入時照舊（全部角色），可以去登入。
// 5F-5：建角時可以沿用上季角色的名字與外觀（種族）；下方是編年史；管理者看得到季末重置。
// 6F-1：標題「建立角色」；「開發模式（不用登入）」與季末重置只在網址 `?dev=1` 顯示。
import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { AuthStatus, LegacyHeroView, WorldCharacterSummary, WorldView } from "../api/types";
import { accountLine } from "../auth/auth";
import { RaceOriginPicker } from "../run/RaceOriginPicker";
import { raceOriginBody, raceOriginDone, type RaceOriginChoice } from "../run/raceOrigin";
import { StartPickerView, useStartPicker } from "../run/StartPicker";
import { isDevMode } from "../run/startFlow";
import { ErrorBanner } from "../ui/ErrorBanner";
import { randomSeed } from "../screens/StartScreen";
import { ChroniclePanel } from "./ChroniclePanel";
import { NAME_MAX, nameProblem } from "./mapView";
import { canAdmin, legacyLabel } from "./season";
import { SeasonResetPanel } from "./SeasonResetPanel";

interface Props {
  onEnter(characterId: string, first?: WorldView): void;
  onHome(): void;
  onLogin?(): void;
  onLogout?(): void;
}

export function WorldCharacterPicker({ onEnter, onHome, onLogin, onLogout }: Props) {
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [chars, setChars] = useState<WorldCharacterSummary[] | null>(null);
  const [name, setName] = useState("");
  const [seed] = useState(() => randomSeed());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const picker = useStartPicker(seed, false);
  const [raceOrigin, setRaceOrigin] = useState<RaceOriginChoice>({ race: "", origin: "" });
  const [legacy, setLegacy] = useState<LegacyHeroView[]>([]);
  const [legacyId, setLegacyId] = useState("");
  const [reload, setReload] = useState(0);
  /** 6F-1：「開發模式（不用登入）」與季末重置（管理者）只在網址 `?dev=1` 顯示。 */
  const dev = isDevMode(window.location.search);

  useEffect(() => {
    let cancelled = false;
    api.worldCharacters().then(
      (list) => !cancelled && setChars(list),
      (e: unknown) => !cancelled && setError(e instanceof Error ? e.message : String(e)),
    );
    api.authStatus().then(
      (s) => !cancelled && setAuth(s),
      () => undefined,
    );
    api.worldLegacy().then(
      (list) => !cancelled && setLegacy(list),
      () => undefined,
    );
    return () => {
      cancelled = true;
    };
  }, [reload]);

  function pickLegacy(id: string) {
    setLegacyId(id);
    const hero = legacy.find((h) => h.character_id === id);
    if (hero === undefined) return;
    setName(hero.name);
    setRaceOrigin((c) => ({ ...c, race: hero.race ?? "" }));
  }

  const problem = nameProblem(name);
  const full = auth?.account != null && !auth.account.can_create;
  const ready = !full && problem === null && picker.body !== null && raceOriginDone(picker.options, raceOrigin);

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
        ...(legacyId === "" ? {} : { legacy_character: legacyId }),
      });
      onEnter(view.character.character_id, view);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  return (
    <div className="start-screen world-pick">
      <h1>建立角色</h1>
      <ErrorBanner message={error ?? picker.error} onClose={() => setError(null)} />
      {auth !== null && (auth.account != null || dev || onLogin !== undefined) && (
        <div className="panel world-account" data-testid="world-account">
          {(auth.account != null || dev) && <span>{accountLine(auth)}</span>}
          {onLogin !== undefined && (
            <button type="button" onClick={onLogin} data-testid="world-login">
              登入帳號
            </button>
          )}
          {onLogout !== undefined && (
            <button type="button" onClick={onLogout} data-testid="world-logout">
              登出
            </button>
          )}
        </div>
      )}
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
        {legacy.length > 0 && (
          <label>
            沿用上季角色的名字與外觀
            <select value={legacyId} onChange={(e) => pickLegacy(e.target.value)} disabled={busy} data-testid="world-legacy">
              <option value="">不沿用（新的名字）</option>
              {legacy.map((h) => (
                <option key={`${h.season_id}-${h.character_id}`} value={h.character_id}>
                  {legacyLabel(h)}
                </option>
              ))}
            </select>
          </label>
        )}
        <label>
          名稱
          <input
            value={name}
            maxLength={NAME_MAX}
            onChange={(e) => setName(e.target.value)}
            aria-invalid={problem !== null}
            readOnly={legacyId !== ""}
            data-testid="world-name"
          />
        </label>
        {legacyId !== "" && <div className="muted small">沿用上季的名字與紙娃娃；種族預設帶上季的，可以免費改。等級、技能、裝備從頭開始。</div>}
        <RaceOriginPicker options={picker.options} choice={raceOrigin} onChoice={setRaceOrigin} disabled={busy} />
        <StartPickerView picker={picker} disabled={busy} />
        <div className="muted small">
          屬性點照預設（全部點在起始技能最常用的屬性）；角色從雲嶺的霧渡鎮出發。隊友：一開始帶系統傭兵賽倫、回春，可以在城鎮免費改成別的傭兵、借朋友的影子（最多 2 名）或獨行。
        </div>
        <div className="run-actions">
          <button type="submit" className="primary" disabled={busy || !ready}>
            {busy ? "建立中……" : "建立並進入"}
          </button>
          <button type="button" onClick={onHome}>
            返回首頁
          </button>
          {full && <span className="error-text small">角色已達上限（{auth?.account?.max_characters} 個）</span>}
          {!full && name !== "" && problem !== null && <span className="error-text small">{problem}</span>}
        </div>
      </form>
      <ChroniclePanel refresh={reload} />
      {dev && canAdmin(auth) && <SeasonResetPanel onDone={() => setReload((n) => n + 1)} />}
    </div>
  );
}
