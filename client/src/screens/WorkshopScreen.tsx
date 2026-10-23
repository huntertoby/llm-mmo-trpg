// 技能工坊：一步步組技能 → 即時檢查 → 隨機一個／匯出 YAML／裝上試玩。
import { useCallback, useEffect, useReducer, useState } from "react";
import { api } from "../api/client";
import type { BattleResponse, Choice } from "../api/types";
import { CheckPanel } from "../ui/workshop/CheckPanel";
import { ErrorBanner } from "../ui/ErrorBanner";
import { StepView } from "../ui/workshop/StepView";
import { GearScreen } from "./GearScreen";
import { ExportPanel, RandomPanel, YamlPanel } from "../ui/workshop/ToolPanels";
import { TryoutPanel } from "../ui/workshop/TryoutPanel";
import { isDevMode } from "../run/startFlow";
import { resetStep, type Json } from "../workshop/draft";
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
  /** 開發者模式（網址 `?dev=1`）：顯示種子、可匯出不合法的技能；預設是玩家模式。 */
  dev?: boolean;
}

const OPTIONS_DELAY_MS = 120;
const CHECK_DELAY_MS = 250;

function message(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

const TAB_KEY = "trpg-workshop-tab";

function readTab(): "skills" | "gear" {
  try {
    return typeof localStorage !== "undefined" && localStorage.getItem(TAB_KEY) === "gear" ? "gear" : "skills";
  } catch {
    return "skills";
  }
}

/** 工坊：「技能」與「裝備」兩個分頁（裝備測試，Phase 3G-G4）；分頁記在瀏覽器，從戰鬥回來時停在原處。 */
export function WorkshopScreen(props: Props) {
  const [tab, setTab] = useState<"skills" | "gear">(readTab);
  const choose = (next: "skills" | "gear") => {
    setTab(next);
    try {
      localStorage.setItem(TAB_KEY, next);
    } catch {
      // 存不進去就略過
    }
  };
  if (tab === "gear") {
    return <GearScreen onHome={props.onHome} onSkills={() => choose("skills")} onStartBattle={props.onStartBattle} />;
  }
  const dev = props.dev ?? (typeof window !== "undefined" && isDevMode(window.location.search));
  return <SkillWorkshop {...props} dev={dev} onGear={() => choose("gear")} />;
}

function SkillWorkshop({ onHome, onStartBattle, onGear, store, dev = false }: Props & { onGear(): void }) {
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

  // 清空重來：有內容時先在頁內問一次（尚未匯出的內容會消失），草稿被別處改了就作廢
  const [confirmingReset, setConfirmingReset] = useState(false);
  useEffect(() => setConfirmingReset(false), [draft]);
  function reset() {
    if (resetStep(draft, confirmingReset) === "ask") {
      setConfirmingReset(true);
      return;
    }
    setConfirmingReset(false);
    dispatch({ type: "replace", draft: {} });
  }

  return (
    <div className="workshop-screen">
      <header className="ws-header">
        <h1>技能工坊</h1>
        <nav className="ws-tabs" aria-label="工坊分頁">
          <button type="button" className="active" aria-current="page">
            技能
          </button>
          <button type="button" onClick={onGear}>
            裝備
          </button>
        </nav>
        <span className="muted">一步步組出自己的技能，檢查強度，再裝上主角試玩。</span>
        <span className="ws-header-tools">
          {confirmingReset && (
            <span className="ws-reset-ask muted small">清空目前編輯中的技能？（尚未匯出的內容會消失）</span>
          )}
          <button type="button" className={confirmingReset ? "danger" : ""} onClick={reset}>
            {confirmingReset ? "確定清空" : "清空重來"}
          </button>
          {confirmingReset && (
            <button type="button" onClick={() => setConfirmingReset(false)}>
              取消
            </button>
          )}
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
          <RandomPanel dev={dev} skeletons={skeletons} draft={draft} onResult={(d) => dispatch({ type: "replace", draft: d })} />
          <YamlPanel draft={draft} onDraft={setDraft} />
        </div>
        <div className="ws-col ws-col-side">
          <CheckPanel check={state.check} pending={checking} dev={dev} />
          <TryoutPanel check={state.check} pending={checking} prefs={prefs} onPrefs={setPrefs} onStart={onStartBattle} />
          <ExportPanel draft={draft} check={state.check} dev={dev} />
        </div>
      </div>
    </div>
  );
}
