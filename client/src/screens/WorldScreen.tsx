// 大世界（測試）畫面（Phase 5A-5；docs/phases/Phase5計畫.md 10.5）：角色畫面 → 地點圖（點相鄰地點移動、遇敵看陣容、
// 開戰或撤退、小鎮休息／換技能／傳送、野外紮營）。戰鬥沿用戰鬥畫面；結束或離開後重新讀地點圖（勝負已由後端回寫）。
import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { BattleResponse, WorldAction, WorldView } from "../api/types";
import { ErrorBanner } from "../ui/ErrorBanner";
import { primeSkillCard } from "../ui/useSkillCards";
import { WorldCharacterPicker } from "../world/WorldCharacterPicker";
import { WorldMap } from "../world/WorldMap";
import { WorldPanel } from "../world/WorldPanel";
import { readWorldChar, writeWorldChar } from "../world/mapView";
import { BattleScreen } from "./BattleScreen";

interface Props {
  onHome(): void;
}

const LOG_MAX = 12;

function errorText(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

export function WorldScreen({ onHome }: Props) {
  const [charId, setCharId] = useState<string | null>(() => readWorldChar());
  const [view, setView] = useState<WorldView | null>(null);
  const [battle, setBattle] = useState<BattleResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasten, setHasten] = useState(false);
  const [log, setLog] = useState<string[]>([]);

  const show = useCallback((next: WorldView) => {
    for (const card of [...next.character.skills, ...next.character.bench]) primeSkillCard(card);
    setView(next);
    if (next.events.length > 0) setLog((cur) => [...next.events, ...cur].slice(0, LOG_MAX));
  }, []);

  useEffect(() => {
    if (charId === null || view !== null) return undefined;
    let cancelled = false;
    api.world(charId).then(
      (v) => !cancelled && show(v),
      (e: unknown) => {
        if (cancelled) return;
        // 角色不見了（存檔被刪）：回角色畫面
        if (e instanceof ApiError && e.status === 404) {
          writeWorldChar(null);
          setCharId(null);
        }
        setError(errorText(e));
      },
    );
    return () => {
      cancelled = true;
    };
  }, [charId, view, show]);

  function enter(id: string, first?: WorldView) {
    writeWorldChar(id);
    setLog([]);
    setError(null);
    setCharId(id);
    if (first !== undefined) show(first);
    else setView(null);
  }

  function leaveChar() {
    writeWorldChar(null);
    setCharId(null);
    setView(null);
    setLog([]);
  }

  async function run(task: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await task();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  const act = (action: WorldAction) =>
    void run(async () => {
      if (charId !== null) show(await api.worldAct(charId, action));
    });

  const travel = (to: string) => act({ kind: "travel", to, hasten });

  const fight = () =>
    void run(async () => {
      if (charId === null) return;
      const res = await api.worldBattle(charId);
      show(res.world);
      setBattle(res.battle);
    });

  async function backToMap() {
    setError(null);
    try {
      if (charId !== null) show(await api.world(charId));
      setBattle(null);
    } catch (e) {
      setError(errorText(e));
    }
  }

  if (battle !== null) {
    return <BattleScreen key={battle.battle_id} initial={battle} onExit={() => void backToMap()} exitLabel="回到地點圖" />;
  }
  if (charId === null) {
    return <WorldCharacterPicker onEnter={enter} onHome={onHome} />;
  }
  return (
    <div className="run-screen world-screen">
      <header className="run-header">
        <h1>
          大世界（測試）　<span className="muted small">{view === null ? "" : `${view.map.name_zh}（${view.map.level_zh}）`}</span>
        </h1>
        <div className="run-header-buttons">
          <button type="button" onClick={leaveChar}>
            換角色
          </button>
          <button type="button" onClick={onHome}>
            回首頁
          </button>
        </div>
      </header>
      <ErrorBanner message={error} onClose={() => setError(null)} />
      {view === null ? (
        <div className="muted">載入中……</div>
      ) : (
        <div className="world-layout">
          <WorldMap view={view} busy={busy} onTravel={travel} />
          <WorldPanel
            view={view}
            busy={busy}
            hasten={hasten}
            onHasten={setHasten}
            onAct={act}
            onBattle={fight}
            log={log}
          />
        </div>
      )}
    </div>
  );
}
