// 技能工坊：一步步組技能 → 即時檢查 → 隨機一個／匯出 YAML／裝上試玩。
import { useCallback, useEffect, useReducer, useState } from "react";
import { api } from "../api/client";
import type { BattleResponse, Choice } from "../api/types";
import { CheckPanel } from "../ui/workshop/CheckPanel";
import { ErrorBanner } from "../ui/ErrorBanner";
import { StepView } from "../ui/workshop/StepView";
import { ExportPanel, RandomPanel, YamlPanel } from "../ui/workshop/ToolPanels";
import { TryoutPanel } from "../ui/workshop/TryoutPanel";
import type { Json } from "../workshop/draft";
import {
  browserStore,
  editorReducer,
  initialState,
  loadSaved,
  save,
  type KeyValueStore,
  type TryoutPrefs,
} from "../workshop/state";

interface Props {
  onHome(): void;
  onStartBattle(response: BattleResponse): void;
  /** 測試或特殊環境可換掉儲存位置；預設用瀏覽器的 localStorage。 */
  store?: KeyValueStore | null;
}

const OPTIONS_DELAY_MS = 120;
const CHECK_DELAY_MS = 250;

function message(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

export function WorkshopScreen({ onHome, onStartBattle, store }: Props) {
  const storage = store === undefined ? browserStore() : store;
  const [state, dispatch] = useReducer(editorReducer, undefined, () => {
    const saved = loadSaved(storage);
    return initialState(saved?.draft ?? {}, saved?.step ?? null);
  });
  const [prefs, setPrefs] = useState<TryoutPrefs>(() => loadSaved(storage)?.tryout ?? {});
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { draft } = state;

  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(() => {
      api
        .workshopOptions(draft)
        .then((options) => {
          if (!cancelled) dispatch({ type: "options", options });
        })
        .catch((e: unknown) => {
          if (!cancelled) setError(message(e));
        });
    }, OPTIONS_DELAY_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [draft]);

  useEffect(() => {
    let cancelled = false;
    setChecking(true);
    const timer = setTimeout(() => {
      api
        .workshopCheck(draft)
        .then((check) => {
          if (cancelled) return;
          dispatch({ type: "check", check });
          setChecking(false);
        })
        .catch((e: unknown) => {
          if (cancelled) return;
          setError(message(e));
          setChecking(false);
        });
    }, CHECK_DELAY_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [draft]);

  // 瀏覽器暫存：重新整理、進戰鬥再回來都不會遺失。
  useEffect(() => {
    save(storage, { draft, step: state.step, tryout: prefs });
  }, [storage, draft, state.step, prefs]);

  const setDraft = useCallback((next: Json) => dispatch({ type: "edit", draft: next }), []);
  const skeletons: readonly Choice[] = state.options?.steps[0]?.fields[0]?.choices ?? [];

  function reset() {
    if (Object.keys(draft).length > 0 && !window.confirm("清空目前編輯中的技能，從頭開始？（尚未匯出的內容會消失）")) return;
    dispatch({ type: "replace", draft: {} });
  }

  return (
    <div className="workshop-screen">
      <header className="ws-header">
        <h1>技能工坊</h1>
        <span className="muted">一步步組出自己的技能，檢查強度，再裝上主角試玩。</span>
        <span className="ws-header-tools">
          <button type="button" onClick={reset}>
            清空重來
          </button>
          <button type="button" onClick={onHome}>
            回首頁
          </button>
        </span>
      </header>
      <ErrorBanner message={error} onClose={() => setError(null)} />
      <div className="ws-layout">
        <div className="ws-col">
          <StepView
            state={state}
            onDraft={setDraft}
            onGoto={(step) => dispatch({ type: "goto", step })}
            onBack={() => dispatch({ type: "back" })}
            onNext={() => dispatch({ type: "next" })}
          />
          <RandomPanel skeletons={skeletons} draft={draft} onResult={(d) => dispatch({ type: "replace", draft: d })} />
          <YamlPanel draft={draft} onDraft={setDraft} />
        </div>
        <div className="ws-col ws-col-side">
          <CheckPanel check={state.check} pending={checking} />
          <TryoutPanel check={state.check} pending={checking} prefs={prefs} onPrefs={setPrefs} onStart={onStartBattle} />
          <ExportPanel draft={draft} />
        </div>
      </div>
    </div>
  );
}
