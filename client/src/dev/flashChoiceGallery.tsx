// 靈感閃現「選變體」畫面（FL-1b）的開發頁：`client/dev/flash-choice.html`。
// 資料是伺服器同一套函式算的夾具（`scripts/export_flash_choice_fixture.py` → `dev/fixtures/flashChoice.json`），不是手寫：
// - `?set=base`（預設；點燃斬第 1 次，使用者截圖那四個）、`rows`（雙槍連射，列數多＋一升一降）、`transform`（第 3 次，轉成反應、
//   被動欄滿了＝卸下選單；卸下的三招是示意）、`stance`（轉成姿態，姿態欄自動換下、不出選單）、`llm`（LF-3：第 3 次大變化，
//   本機模型取的名稱＋一句話描述；第 3 個只有描述、名稱是組合式）；
// - `?mode=world`（預設：大世界 HUD 面板，外框照正式 `popupBox`、`PopupFrame slots`，帶鎖住提示）、`?mode=run`（一輪：頁面捲、
//   下固定區 sticky；上面墊一段營火的字，讓頁面要捲）；
// - `&pick=0～3`：開好後點第幾張（照畫面順序）；`&scroll=end`：捲到選項區底。
import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import type { PendingFlash, RunHero, SkillCard } from "../api/types";
import { FlashPendingPanel } from "../screens/RunFlashPending";
import { FLASH_LOCK_NOTE_ZH } from "../run/flashChoice";
import { PopupFrame } from "../ui/PopupFrame";
import { useRegionTheme } from "../ui/regionTheme";
import { hudLayout, isNarrow, popupBox } from "../world/hud";
import data from "./fixtures/flashChoice.json";
import "../styles/index.css";

type Fixture = { hero: RunHero; sets: Record<string, PendingFlash>; bases?: Record<string, SkillCard> };
const FIXTURE = data as unknown as Fixture;
const noop = async () => null;

function heroFor(set: string): RunHero {
  const base = FIXTURE.bases?.[set];
  if (base === undefined) return FIXTURE.hero;
  return { ...FIXTURE.hero, skills: [base, ...FIXTURE.hero.skills.slice(1)] };
}

function useWindowSize(): { width: number; height: number } {
  const [size, setSize] = useState(() => ({ width: window.innerWidth, height: window.innerHeight }));
  useEffect(() => {
    const onResize = () => setSize({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  return size;
}

function useAutoPick(pick: string | null, scroll: string | null): void {
  useEffect(() => {
    const t = window.setTimeout(() => {
      if (scroll === "end") {
        const body = document.querySelector<HTMLElement>(".world-hud-panel > .ui-popup-body");
        if (body !== null) body.scrollTop = body.scrollHeight;
      }
      if (pick === null) return;
      const cards = document.querySelectorAll<HTMLElement>(".fc-opt");
      cards[Number(pick)]?.click();
    }, 400);
    return () => window.clearTimeout(t);
  }, [pick, scroll]);
}

function WorldScene({ set }: { set: string }) {
  useRegionTheme("cloud_ridge");
  const { width: W, height: H } = useWindowSize();
  const layout = hudLayout(W, H - 60, { mates: 2, narrow: isNarrow(W), collapsed: false });
  const pending = FIXTURE.sets[set] ?? FIXTURE.sets.base!;
  return (
    <div className="world-hud-stage" style={{ position: "relative", marginTop: 60, height: H - 60, background: "#20283a" }} data-scene="flash">
      <PopupFrame placement={{ kind: "hud", box: popupBox(layout, 720) }} className="world-hud-panel" label="面板" testId="world-hud-panel" slots>
        <div className="world-growth" data-testid="world-flash-pending">
          <FlashPendingPanel pending={pending} hero={heroFor(set)} busy={false} onChoose={noop} lockNote={FLASH_LOCK_NOTE_ZH} />
        </div>
      </PopupFrame>
    </div>
  );
}

function RunScene({ set }: { set: string }) {
  const pending = FIXTURE.sets[set] ?? FIXTURE.sets.base!;
  return (
    <div className="run-screen" style={{ padding: 16 }}>
      <div className="run-main" style={{ maxWidth: 980, margin: "0 auto" }}>
        <div className="panel">
          <h2>營火</h2>
          <p className="muted small">（開發頁：上面墊一段營火的字，讓頁面要捲；實機的營火在這裡有休息、整備、重閃等區塊）</p>
          <div style={{ height: 260 }} />
        </div>
        <FlashPendingPanel pending={pending} hero={heroFor(set)} busy={false} onChoose={noop} />
      </div>
    </div>
  );
}

function App() {
  const q = new URLSearchParams(location.search);
  const set = q.get("set") ?? "base";
  useAutoPick(q.get("pick"), q.get("scroll"));
  return q.get("mode") === "run" ? <RunScene set={set} /> : <WorldScene set={set} />;
}

createRoot(document.getElementById("root") as HTMLElement).render(<App />);
