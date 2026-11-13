// 大世界的角色畫面（Phase 5A-5）：列出既有角色、建立新角色（07 7.6 創角：起始武器＋2 個關鍵字；種族與出身同一輪開局）。
// 5E-1：已登入時只列自己的角色、顯示帳號與角色上限、可以登出；開發模式沒登入時照舊（全部角色），可以去登入。
// 5F-5：建角時可以沿用上季角色的名字與外觀（種族）；下方是編年史；管理者看得到季末重置。
// 6F-1：標題「建立角色」；「開發模式（不用登入）」與季末重置只在網址 `?dev=1` 顯示。
// UI-E1：換皮（docs/art/shots/misc/entry-screens.png）：浮島天空背景、深藍金框（共用彈窗元件）；角色列表每列加頭像（QK-2b 起是主角的 Q 版頭像 `HeroFace`）；
// 建角分成左邊「預覽」（人物要等 Q 版，這段只留位置，不畫人物）與右邊編號步驟（名字 → 種族 → 出身 → 武器 → 關鍵字）；
// 按鈕「建立並在主城醒來」（#125：新角色在主城醒來）。欄位、送出的資料與流程照舊。
// 6R-2（#137）：步驟改成 名字 → 種族 → 外觀 → 出身（→ 武器 → 關鍵字）；預覽框用現有紙娃娃部件畫人物（`LookPreview`），
// 外觀只送選項代碼（`look`），換種族時新種族沒有的選項清掉。
// TR-1（#134）：建角只選 名字 → 種族 → 外觀 → 出身；武器與 2 個關鍵字在主城工坊靶場試用後選（`RangeScreen`），
// 這裡不送 `weapon`／`keywords`（伺服器把角色建成「未完成開局」）。
import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { AuthStatus, LegacyHeroView, StartOptions, WorldCharacterSummary, WorldView } from "../api/types";
import { accountLine } from "../auth/auth";
import type { LookChoice } from "../api/types";
import { LookPicker, LookPreview, lookAfterRace } from "../run/LookPicker";
import { lookBody } from "../run/lookOptions";
import { RaceOriginPicker } from "../run/RaceOriginPicker";
import { raceOriginBody, raceOriginDone, type RaceOriginChoice } from "../run/raceOrigin";
import { isDevMode } from "../run/startFlow";
import { EntryPanel, EntryPlaque, EntryShell } from "../ui/EntryShell";
import { ErrorBanner } from "../ui/ErrorBanner";
import { randomSeed } from "../screens/StartScreen";
import { ChroniclePanel } from "./ChroniclePanel";
import { HeroFace, fieldHeroInput } from "../ui/heroFace";
import { HudPortrait } from "./HudIcons";
import { NAME_MAX, nameProblem } from "./mapView";
import { canAdmin, legacyLabel } from "./season";
import { SeasonResetPanel } from "./SeasonResetPanel";

/** 角色清單的頭像（QK-2b）：主角自己的 Q 版頭像（種族、外觀選項、裝備；框色＝出身區）；舊伺服器沒給外觀時退回通用頭像。 */
function CharFace({ c }: { c: WorldCharacterSummary }) {
  const input = fieldHeroInput(c.hero_look);
  if (input === null) return <HudPortrait size={40} ring="#e8bb48" />;
  return <HeroFace input={input} realm={c.origin_realm ?? null} size={40} label={c.name} />;
}

interface Props {
  onEnter(characterId: string, first?: WorldView): void;
  onHome(): void;
  onLogin?(): void;
  onLogout?(): void;
}

/** 建角按鈕的字（#125：新角色在主城醒來）。 */
export const CREATE_LABEL = "建立並在主城醒來";

/** 預覽框下方的一行摘要：「名字」／「種族・出身」（出身的名字本身已含「出身」）；沒選的略過。TR-1：武器在主城工坊靶場選。 */
export function previewLines(name: string, race: string | undefined, origin: string | undefined): { name: string; detail: string } {
  const parts = [race, origin].filter((p): p is string => p !== undefined && p !== "");
  return { name: name.trim() === "" ? "（還沒取名字）" : name.trim(), detail: parts.length === 0 ? "選種族與出身" : parts.join("・") };
}

/** 6R-2b（美術 PM）：外觀選單捲到畫面上半部時算「在外觀步驟」（窄版 < 1040 的預覽縮小、固定在上方，
 * 點選項時看得到預覽）；捲走就恢復原版面。沒有 IntersectionObserver（測試環境）時一律 false。 */
function useInLookStep(target: HTMLElement | null): boolean {
  const [inside, setInside] = useState(false);
  useEffect(() => {
    if (target === null || typeof IntersectionObserver === "undefined") return undefined;
    const observer = new IntersectionObserver((entries) => setInside(entries.some((e) => e.isIntersecting)), { rootMargin: "0px 0px -40% 0px" });
    observer.observe(target);
    return () => observer.disconnect();
  }, [target]);
  return inside;
}

export function WorldCharacterPicker({ onEnter, onHome, onLogin, onLogout }: Props) {
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [chars, setChars] = useState<WorldCharacterSummary[] | null>(null);
  const [name, setName] = useState("");
  const [seed] = useState(() => randomSeed());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  /** 種族與出身的選項（同一輪開局的 `start-options`；TR-1 起建角不選武器與關鍵字）。 */
  const [options, setOptions] = useState<StartOptions | null>(null);
  const [raceOrigin, setRaceOrigin] = useState<RaceOriginChoice>({ race: "", origin: "" });
  const [look, setLook] = useState<LookChoice>({});
  const [legacy, setLegacy] = useState<LegacyHeroView[]>([]);
  const [legacyId, setLegacyId] = useState("");
  const [reload, setReload] = useState(0);
  const [lookArea, setLookArea] = useState<HTMLDivElement | null>(null);
  const inLookStep = useInLookStep(lookArea) && raceOrigin.race !== "";
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
    api.startOptions().then(
      (o) => !cancelled && setOptions(o),
      (e: unknown) => !cancelled && setError(e instanceof Error ? e.message : String(e)),
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
    setLook({}); // 沿用上季：沒有另外選就照上季的外觀（伺服器處理）
  }

  function pickRaceOrigin(next: RaceOriginChoice) {
    if (next.race !== raceOrigin.race) setLook((l) => lookAfterRace(l, next.race));
    setRaceOrigin(next);
  }

  const problem = nameProblem(name);
  const full = auth?.account != null && !auth.account.can_create;
  const ready = !full && problem === null && raceOriginDone(options, raceOrigin);

  async function create(e: FormEvent) {
    e.preventDefault();
    if (!ready) return;
    setBusy(true);
    setError(null);
    try {
      const view = await api.createWorldCharacter({
        name: name.trim(),
        seed,
        race: null,
        origin: null,
        ...raceOriginBody(raceOrigin),
        ...(lookBody(look) === null ? {} : { look: lookBody(look) }),
        ...(legacyId === "" ? {} : { legacy_character: legacyId }),
      });
      onEnter(view.character.character_id, view);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  const preview = previewLines(
    name,
    options?.races?.find((r) => r.id === raceOrigin.race)?.name_zh,
    options?.origins?.find((o) => o.id === raceOrigin.origin)?.name_zh,
  );

  return (
    <EntryShell className="world-pick">
      <EntryPlaque heading="建立角色" sub="選一個角色進入，或在下面建立新角色" />
      <ErrorBanner message={error} onClose={() => setError(null)} />
      {auth !== null && (auth.account != null || dev || onLogin !== undefined) && (
        <EntryPanel className="world-account" testId="world-account">
          <div className="world-account-row">
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
        </EntryPanel>
      )}
      <EntryPanel className="entry-chars" testId="world-chars">
        <div className="section-title">我的角色</div>
        {chars === null && <div className="muted small">載入中……</div>}
        {chars !== null && chars.length === 0 && <div className="muted small">還沒有角色，先在下面建立一個。</div>}
        {chars?.map((c) => (
          <div key={c.character_id} className="run-save-row entry-char-row" data-testid="world-char-row">
            <span className="entry-char-face">
              <CharFace c={c} />
            </span>
            <span className="entry-char-text">
              <b>{c.name}</b>・Lv {c.level}
              <span className="muted small">　{c.region_name_zh}・{c.location_name_zh}</span>
            </span>
            <button type="button" className="primary" onClick={() => onEnter(c.character_id)}>
              進入
            </button>
          </div>
        ))}
      </EntryPanel>
      <form className={`entry-create${inLookStep ? " entry-look-step" : ""}`} data-look-step={inLookStep ? "1" : undefined} onSubmit={(e) => void create(e)}>
        <EntryPanel className="entry-preview" testId="create-preview">
          <div className="section-title">預覽</div>
          <div className="entry-preview-slot" data-testid="create-preview-slot">
            {raceOrigin.race === "" ? (
              <>
                <span className="muted small">人物預覽</span>
                <span className="muted small">選了種族就會顯示</span>
              </>
            ) : (
              <LookPreview race={raceOrigin.race} choice={look} weaponId={null} />
            )}
          </div>
          <div className="entry-preview-name">{preview.name}</div>
          <div className="entry-preview-detail small">{preview.detail}</div>
        </EntryPanel>
        <EntryPanel className="entry-steps start-form" testId="create-steps">
          <div className="section-title">名字</div>
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
          <label className="entry-name">
            <input
              value={name}
              maxLength={NAME_MAX}
              onChange={(e) => setName(e.target.value)}
              aria-invalid={problem !== null}
              aria-label="名稱"
              placeholder="角色名稱"
              readOnly={legacyId !== ""}
              data-testid="world-name"
            />
          </label>
          {legacyId !== "" && <div className="muted small">沿用上季的名字與紙娃娃；種族預設帶上季的，可以免費改。等級、技能、裝備從頭開始。</div>}
          <RaceOriginPicker
            options={options}
            choice={raceOrigin}
            onChoice={pickRaceOrigin}
            disabled={busy}
            afterRace={
              <>
                <div className="section-title">外觀</div>
                <div ref={setLookArea} data-testid="create-look-area">
                  {raceOrigin.race === "" ? (
                    <div className="muted small">先選種族，再挑臉型、髮型與顏色；不想捏臉可以直接下一步（照種族預設）。</div>
                  ) : (
                    <LookPicker race={raceOrigin.race} choice={look} onChoice={setLook} disabled={busy} seed={`create-${seed}`} />
                  )}
                </div>
              </>
            }
          />
          <div className="small entry-note" data-testid="world-start-range">
            武器與兩個關鍵字：醒來後守印人帶你到<b>主城工坊靶場</b>，三大類武器都能拿起來打木樁、每個關鍵字都能先看示範，選好再按「確定出發」。屬性照推薦配法自動配好，之後導師會教你自己配。
          </div>
          <div className="muted small entry-note">
            角色在主城樞島醒來，再傳送到雲嶺的霧渡鎮（第一次免費）。出發時，守印人會派盾衛賽倫陪你同行。正式選定武器後，可以在城鎮換隊友，或獨自上路。
          </div>
          <div className="run-actions entry-actions">
            <button data-sfx="ui_cancel" type="button" onClick={onHome}>
              返回首頁
            </button>
            {full && <span className="error-text small">角色已達上限（{auth?.account?.max_characters} 個）</span>}
            {!full && name !== "" && problem !== null && <span className="error-text small">{problem}</span>}
            <button type="submit" className="primary entry-create-go" disabled={busy || !ready} data-testid="world-create">
              {busy ? "建立中……" : CREATE_LABEL}
            </button>
          </div>
        </EntryPanel>
      </form>
      <div className="entry-extras">
        <ChroniclePanel refresh={reload} />
        {dev && canAdmin(auth) && <SeasonResetPanel onDone={() => setReload((n) => n + 1)} />}
      </div>
    </EntryShell>
  );
}
