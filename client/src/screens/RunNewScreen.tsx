// 開新一輪（Phase 3-24b2，06 6.27.3）：自選起始武器 ＋ 選 2 個關鍵字（每個關鍵字的池各給 1 招起始技能）、配 4 點屬性、種子。
// 遊戲不定義流派：這個畫面不出現任何流派名稱。開發者起始包（12 個測試組合）只在網址帶 ?dev=1 時顯示。
import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { RunResponse, RunRules } from "../api/types";
import { AttributeAllocator } from "../run/AttributeAllocator";
import { DevPackSelect, StartPickerView, useStartPicker } from "../run/StartPicker";
import { RaceOriginPicker } from "../run/RaceOriginPicker";
import { raceOriginBody, raceOriginDone, type RaceOriginChoice } from "../run/raceOrigin";
import { allocationComplete, baseAttributes, cleanAllocation, type Allocation } from "../run/flow";
import { resourceText, useStartResources } from "../run/startResources";
import { isDevMode } from "../run/startFlow";
import { TestModePanel } from "../run/TestModePanel";
import { withTestMode } from "../run/testMode";
import type { Selection } from "../gear/gearDraft";
import { LLM_TOGGLE_HINT, LLM_TOGGLE_LABEL, withLlm } from "../run/llmFlow";
import { ErrorBanner } from "../ui/ErrorBanner";
import { Hint } from "../ui/Hint";
import { parseSeed, randomSeed } from "./StartScreen";

interface Props {
  onCreated(run: RunResponse): void;
  onHome(): void;
}

export function RunNewScreen({ onCreated, onHome }: Props) {
  /** 開局規則（配點數）由伺服器提供，載入前為 `null`。 */
  const [rules, setRules] = useState<RunRules | null>(null);
  const [alloc, setAlloc] = useState<Allocation>({});
  const [seedText, setSeedText] = useState(() => String(randomSeed()));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testMode, setTestMode] = useState(false);
  const [gear, setGear] = useState<Selection>({});
  const [gearLegal, setGearLegal] = useState(true);
  const [llm, setLlm] = useState(false);
  const dev = isDevMode(window.location.search);
  const seed = parseSeed(seedText);
  const picker = useStartPicker(seed, dev);
  const [raceOrigin, setRaceOrigin] = useState<RaceOriginChoice>({ race: "", origin: "" });

  useEffect(() => {
    let cancelled = false;
    api.runRules().then(
      (r) => !cancelled && setRules(r),
      (e: unknown) => !cancelled && setError(e instanceof Error ? e.message : String(e)),
    );
    return () => {
      cancelled = true;
    };
  }, []);

  const { weapon, selected, weaponDef } = picker;
  const resources = useStartResources(weapon, alloc);
  const points = rules?.start_points ?? 0;
  const complete = rules !== null && allocationComplete(alloc, points);
  const ready = seed !== null && picker.body !== null && gearLegal && raceOriginDone(picker.options, raceOrigin);

  async function create(auto: boolean) {
    if (!ready || seed === null || (!auto && !complete)) return;
    setBusy(true);
    setError(null);
    try {
      const base = { weapon, keywords: selected, seed, ...raceOriginBody(raceOrigin), ...(auto ? {} : { attributes: cleanAllocation(alloc) }) };
      const body = withLlm(withTestMode(base, testMode, gear), llm);
      onCreated(await api.createRun(body));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  async function createDev() {
    if (picker.packId === "" || seed === null) return;
    setBusy(true);
    setError(null);
    try {
      onCreated(await api.createRun(withLlm({ dev_pack: picker.packId, seed, ...raceOriginBody(raceOrigin) }, llm)));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    void create(false);
  }

  return (
    <div className="start-screen run-new">
      <h1>開新一輪</h1>
      <ErrorBanner message={error ?? picker.error} onClose={() => setError(null)} />
      <form className="panel start-form" onSubmit={submit}>
        <RaceOriginPicker options={picker.options} choice={raceOrigin} onChoice={setRaceOrigin} disabled={busy} />
        <StartPickerView picker={picker} disabled={busy} />
        {weaponDef !== undefined && (
          <div className="muted small">
            <span data-testid="start-resources">主角：{resourceText(resources)}</span>・武器 {weaponDef.name_zh}
            {weaponDef.traits_zh.length > 0 && <span data-testid="start-weapon-traits">（{weaponDef.traits_zh.join("；")}）</span>}
          </div>
        )}
        {rules !== null && (
          <>
            <div className="muted small">
              六項屬性起始都是 {rules.base_attribute}；另有 {rules.start_points} 點自由分配。
            </div>
            <AttributeAllocator base={baseAttributes(rules.base_attribute)} points={points} alloc={alloc} onChange={setAlloc} disabled={busy} suggestion={picker.suggestion} affects={picker.attributeAffects} />
          </>
        )}
        <TestModePanel
          enabled={testMode}
          onEnabled={setTestMode}
          selection={gear}
          onSelection={setGear}
          start={picker.body}
          onLegal={setGearLegal}
          disabled={busy}
        />
        <Hint text={LLM_TOGGLE_HINT}>
          <label className="run-llm-toggle" data-testid="llm-toggle">
            <input type="checkbox" checked={llm} disabled={busy} onChange={(e) => setLlm(e.target.checked)} /> {LLM_TOGGLE_LABEL}
          </label>
        </Hint>
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
        <div className="run-actions">
          <button type="submit" className="primary" disabled={busy || !ready || !complete}>
            {busy ? "建立中……" : "開始這一輪"}
          </button>
          <button type="button" disabled={busy || rules === null || !ready} onClick={() => void create(true)}>
            自動配點並開始
          </button>
          <button type="button" onClick={onHome}>
            返回
          </button>
        </div>
        <div className="muted small">
          共 5 場戰鬥加 Boss；
          {testMode ? "測試模式：每場戰鬥結束後 HP、法力、耐力自動回滿。" : "HP、法力、耐力不會在戰鬥之間回復，只有營火（中段與 Boss 前）會回滿。"}
          隊友為 2 名標準隊友。
        </div>
      </form>
      <DevPackSelect picker={picker} disabled={busy || seed === null} onGo={() => void createDev()} />
    </div>
  );
}
