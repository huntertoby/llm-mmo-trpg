// 裝上試玩：選 build、要換掉哪一格、地圖與對手、種子 → 建立戰鬥並進入戰鬥畫面。
import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../../api/client";
import type { BattleResponse, BuildSummary, WorkshopArena, WorkshopCheck } from "../../api/types";
import type { TryoutPrefs } from "../../workshop/state";
import { buildTryoutRequest, isTrainingMap, manaNote, manaWarning } from "../../workshop/tryout";
import { parseSeed, randomSeed } from "../../screens/StartScreen";
import { ErrorBanner } from "../ErrorBanner";
import { primeSkillCard, useSkillCards } from "../useSkillCards";

interface Props {
  check: WorkshopCheck | null;
  /** 檢查還在更新時不能開始（避免用舊的檢查結果試玩）。 */
  pending: boolean;
  prefs: TryoutPrefs;
  onPrefs(prefs: TryoutPrefs): void;
  onStart(response: BattleResponse): void;
}

export function TryoutPanel({ check, pending, prefs, onPrefs, onStart }: Props) {
  const [builds, setBuilds] = useState<BuildSummary[]>([]);
  const [arena, setArena] = useState<WorkshopArena | null>(null);
  const [seedText, setSeedText] = useState(() => String(randomSeed()));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<{ text: string; response: BattleResponse } | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.builds(), api.workshopArena()])
      .then(([b, a]) => {
        if (cancelled) return;
        setBuilds(b);
        setArena(a);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const buildId = builds.some((b) => b.id === prefs.build) ? (prefs.build ?? "") : (builds[0]?.id ?? "");
  const build = builds.find((b) => b.id === buildId);
  const mapId = arena?.maps.some((m) => m.id === prefs.map) ? (prefs.map ?? "") : (arena?.default_map ?? "");
  const opponentId = arena?.opponents.some((o) => o.id === prefs.opponents) ? (prefs.opponents ?? "") : (arena?.opponents[0]?.id ?? "");
  const replaceId = build?.skills.includes(prefs.replace ?? "") ? (prefs.replace ?? "") : "";
  const cards = useSkillCards(useMemo(() => build?.skills ?? [], [build]));
  const training = isTrainingMap(arena, mapId);
  const opponent = arena?.opponents.find((o) => o.id === opponentId);
  const seed = parseSeed(seedText);
  const playable = check !== null && check.complete && check.legal && !pending;
  const ready = playable && buildId !== "" && mapId !== "" && seed !== null && !busy;

  const set = (patch: Partial<TryoutPrefs>) => onPrefs({ ...prefs, build: buildId, map: mapId, opponents: opponentId, replace: replaceId, ...patch });

  async function start() {
    if (!ready || seed === null || check === null) return;
    const body = buildTryoutRequest({ mapId, seed, buildId, replaceId, opponents: opponentId }, check, arena);
    if (body === null) return;
    setBusy(true);
    setError(null);
    try {
      const response = await api.createBattle(body);
      const text = manaWarning(check, response);
      if (check.card != null) primeSkillCard(check.card);
      if (text === null) onStart(response);
      else {
        setWarning({ text, response });
        setBusy(false);
      }
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  const note = manaNote(check);
  return (
    <div className="panel ws-panel">
      <div className="section-title">裝上試玩</div>
      <div className="muted small">把這個技能裝到主角身上，進入戰鬥畫面實際施放一次。戰鬥結束或中途都能回到工坊，技能不會遺失。</div>
      <ErrorBanner message={error} onClose={() => setError(null)} />
      <div className="ws-tryout-form">
        <label>
          主角 build
          <select value={buildId} onChange={(e) => set({ build: e.target.value, replace: "" })}>
            {builds.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name_zh}
              </option>
            ))}
          </select>
        </label>
        <label>
          要換掉哪一個技能
          <select value={replaceId} onChange={(e) => set({ replace: e.target.value })}>
            <option value="">不換（加在空格；主動技最多 6 個，滿了會被拒絕）</option>
            {(build?.skills ?? []).map((id) => (
              <option key={id} value={id}>
                {cards[id]?.name_zh ?? id}
              </option>
            ))}
          </select>
        </label>
        <label>
          地圖
          <select value={mapId} onChange={(e) => set({ map: e.target.value })}>
            {(arena?.maps ?? []).map((m) => (
              <option key={m.id} value={m.id}>
                {m.name_zh}
                {m.archetype === "training" ? "（試玩專用，預設）" : ""}
              </option>
            ))}
          </select>
        </label>
        {training && (
          <label>
            對手
            <select value={opponentId} onChange={(e) => set({ opponents: e.target.value })}>
              {(arena?.opponents ?? []).map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name_zh}
                </option>
              ))}
            </select>
          </label>
        )}
        {training && opponent !== undefined && <div className="muted small">{opponent.description_zh}</div>}
        {!training && <div className="muted small">一般地圖的敵人會正常行動；想安心練習請選「靶場」。</div>}
        <label>
          種子
          <span className="seed-row">
            <input value={seedText} inputMode="numeric" onChange={(e) => setSeedText(e.target.value)} aria-invalid={seed === null} />
            <button type="button" onClick={() => setSeedText(String(randomSeed()))}>
              隨機
            </button>
          </span>
        </label>
        {seed === null && <div className="error-text">種子必須是非負整數</div>}
      </div>
      {note !== null && <div className="ws-note">{note}</div>}
      {!playable && <div className="muted small">技能要先組完整、而且檢查合法（預算 70–100%、沒有違反規則）才能裝上試玩。</div>}
      {warning !== null && (
        <div className="ws-warning" role="alertdialog">
          <div>{warning.text}</div>
          <div className="ws-row">
            <button type="button" className="primary" onClick={() => onStart(warning.response)}>
              仍然進入戰鬥
            </button>
            <button type="button" onClick={() => setWarning(null)}>
              回去調整
            </button>
          </div>
        </div>
      )}
      <button type="button" className="primary" disabled={!ready || warning !== null} onClick={() => void start()}>
        {busy ? "建立中……" : "裝上試玩"}
      </button>
    </div>
  );
}
