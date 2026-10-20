// 開始畫面：選地圖、主角 build、種子 → 建立戰鬥。
import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { BattleResponse, BuildSummary, MapSummary, RunResponse, RunSaveSummary } from "../api/types";
import { saveLabel } from "../run/flow";
import { ErrorBanner } from "../ui/ErrorBanner";

interface Props {
  onStart(response: BattleResponse): void;
  /** 進入技能工坊（Phase 3F）。 */
  onWorkshop(): void;
  /** 開新一輪（roguelite，Phase 3-5c-1）。 */
  onNewRun(): void;
  /** 讀取存檔後進入該輪。 */
  onLoadRun(run: RunResponse): void;
  /** 首頁頂端的提示（例如上次的一輪無法讀回的原因）。 */
  notice?: string | null;
  onCloseNotice?(): void;
}

/** 隨機種子（只用於開新戰鬥；引擎的亂數由種子決定，這裡不影響重播）。 */
export function randomSeed(): number {
  return Math.floor(Math.random() * 2 ** 31);
}

/** 種子輸入 → 非負整數；不合法時 `null`。 */
export function parseSeed(text: string): number | null {
  const t = text.trim();
  if (!/^\d+$/.test(t)) return null;
  const n = Number(t);
  return Number.isSafeInteger(n) ? n : null;
}

export function StartScreen({ onStart, onWorkshop, onNewRun, onLoadRun, notice = null, onCloseNotice }: Props) {
  const [maps, setMaps] = useState<MapSummary[]>([]);
  const [builds, setBuilds] = useState<BuildSummary[]>([]);
  const [mapId, setMapId] = useState("");
  const [buildId, setBuildId] = useState("");
  const [seedText, setSeedText] = useState(() => String(randomSeed()));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saves, setSaves] = useState<RunSaveSummary[]>([]);

  useEffect(() => {
    let cancelled = false;
    api
      .runSaves()
      .then((s) => {
        if (!cancelled) setSaves(s);
      })
      .catch(() => {
        // 存檔列表失敗不影響其他功能。
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function loadSave(runId: string) {
    setError(null);
    try {
      onLoadRun(await api.loadRun(runId));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.maps(), api.builds()])
      .then(([m, b]) => {
        if (cancelled) return;
        setMaps(m);
        setBuilds(b);
        setMapId((cur) => cur || (m[0]?.id ?? ""));
        setBuildId((cur) => cur || (b[0]?.id ?? ""));
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const seed = parseSeed(seedText);
  const ready = mapId !== "" && buildId !== "" && seed !== null && !busy;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!ready || seed === null) return;
    setBusy(true);
    setError(null);
    try {
      onStart(await api.createBattle({ map_id: mapId, seed, hero_build: buildId }));
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  const build = builds.find((b) => b.id === buildId);
  return (
    <div className="start-screen">
      <h1>LLM-MMO-TRPG 戰鬥原型</h1>
      <ErrorBanner message={notice} onClose={() => onCloseNotice?.()} />
      <ErrorBanner message={error} onClose={() => setError(null)} />
      <div className="panel start-run">
        <div className="section-title">roguelite 一輪</div>
        <div className="muted small">5 場戰鬥加 Boss：打贏升級、營火回滿，一路帶著同一個主角。</div>
        <button type="button" className="primary" onClick={onNewRun}>
          開新一輪
        </button>
        {saves.length > 0 && (
          <div className="run-saves">
            <div className="section-title">繼續一輪</div>
            {saves.map((s) => (
              <div key={s.run_id} className="run-save-row">
                <span>
                  {s.build_id}・種子 {s.seed}
                  <span className="muted small">　{saveLabel(s)}</span>
                </span>
                <button type="button" disabled={s.node === "ended"} onClick={() => void loadSave(s.run_id)}>
                  讀取
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
      <form className="panel start-form" onSubmit={(e) => void submit(e)}>
        <label>
          地圖
          <select value={mapId} onChange={(e) => setMapId(e.target.value)}>
            {maps.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name_zh}（{m.width}×{m.height}・{m.archetype}）
              </option>
            ))}
          </select>
        </label>
        <label>
          主角 build
          <select value={buildId} onChange={(e) => setBuildId(e.target.value)}>
            {builds.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name_zh}
              </option>
            ))}
          </select>
        </label>
        {build !== undefined && <div className="muted small">{build.theme_zh}</div>}
        <label>
          種子
          <span className="seed-row">
            <input
              value={seedText}
              inputMode="numeric"
              onChange={(e) => setSeedText(e.target.value)}
              aria-invalid={seed === null}
            />
            <button type="button" onClick={() => setSeedText(String(randomSeed()))}>
              隨機
            </button>
          </span>
        </label>
        {seed === null && <div className="error-text">種子必須是非負整數</div>}
        <button type="submit" className="primary" disabled={!ready}>
          {busy ? "建立中……" : "開始戰鬥"}
        </button>
        <div className="muted small">隊友由 AI 控制（標準隊友補到 3 人）；你操控主角。</div>
      </form>
      <div className="panel start-workshop">
        <div className="section-title">技能工坊</div>
        <div className="muted small">自己一步步組技能、看強度檢查，再裝到主角身上試玩，也能匯出成 YAML。</div>
        <button type="button" onClick={onWorkshop}>
          進入技能工坊
        </button>
      </div>
    </div>
  );
}
