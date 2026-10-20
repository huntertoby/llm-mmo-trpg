// 開新一輪：選 build（起始技能組）、配 4 點屬性、種子。
import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { BuildSummary, RunResponse, RunRules } from "../api/types";
import { AttributeAllocator } from "../run/AttributeAllocator";
import { allocationComplete, baseAttributes, cleanAllocation, conHpGain, type Allocation } from "../run/flow";
import { useSkillCards, useSkillNames } from "../ui/useSkillCards";
import { ErrorBanner } from "../ui/ErrorBanner";
import { parseSeed, randomSeed } from "./StartScreen";

interface Props {
  onCreated(run: RunResponse): void;
  onHome(): void;
}

export function RunNewScreen({ onCreated, onHome }: Props) {
  const [builds, setBuilds] = useState<BuildSummary[]>([]);
  /** 開局規則（配點數）由伺服器提供，載入前為 `null`。 */
  const [rules, setRules] = useState<RunRules | null>(null);
  const [buildId, setBuildId] = useState("");
  const [alloc, setAlloc] = useState<Allocation>({});
  const [seedText, setSeedText] = useState(() => String(randomSeed()));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .runRules()
      .then((r) => {
        if (!cancelled) setRules(r);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    api
      .builds()
      .then((b) => {
        if (cancelled) return;
        setBuilds(b);
        setBuildId((cur) => cur || (b[0]?.id ?? ""));
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const build = builds.find((b) => b.id === buildId);
  const names = useSkillNames(useSkillCards(build?.skills ?? []));
  const seed = parseSeed(seedText);
  const points = rules?.start_points ?? 0;
  const complete = rules !== null && allocationComplete(alloc, points);

  async function create(auto: boolean) {
    if (buildId === "" || seed === null || (!auto && !complete)) return;
    setBusy(true);
    setError(null);
    try {
      const body = { build: buildId, seed, ...(auto ? {} : { attributes: cleanAllocation(alloc) }) };
      onCreated(await api.createRun(body));
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
      <ErrorBanner message={error} onClose={() => setError(null)} />
      <form className="panel start-form" onSubmit={submit}>
        <label>
          起始 build（主角的武器與起始技能組）
          <select value={buildId} onChange={(e) => setBuildId(e.target.value)}>
            {builds.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name_zh}
              </option>
            ))}
          </select>
        </label>
        {build !== undefined && (
          <div className="muted small">
            {build.theme_zh}
            <br />
            主角：HP {build.max_hp + (rules === null ? 0 : conHpGain(alloc, rules.hp_per_con_point))}・法力 {build.max_mana}・武器 {build.weapon_name_zh}
            <br />
            起始技能：{build.skills.map((id) => names[id] ?? id).join("、")}
          </div>
        )}
        {rules !== null && (
          <>
            <div className="muted small">
              六項屬性起始都是 {rules.base_attribute}；另有 {rules.start_points} 點自由分配。
            </div>
            <AttributeAllocator base={baseAttributes(rules.base_attribute)} points={points} alloc={alloc} onChange={setAlloc} disabled={busy} hpPerCon={rules.hp_per_con_point} />
          </>
        )}
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
          <button type="submit" className="primary" disabled={busy || buildId === "" || seed === null || !complete}>
            {busy ? "建立中……" : "開始這一輪"}
          </button>
          <button type="button" disabled={busy || rules === null || buildId === "" || seed === null} onClick={() => void create(true)}>
            自動配點並開始
          </button>
          <button type="button" onClick={onHome}>
            返回
          </button>
        </div>
        <div className="muted small">
          共 5 場戰鬥加 Boss；HP、法力不會在戰鬥之間回復，只有營火（中段與 Boss 前）會回滿。隊友為 2 名標準隊友。
        </div>
      </form>
    </div>
  );
}
