// 數值工坊（NW-1b B4；NW-2b B6 加地圖戰）：小模擬。情境「頭目戰／地圖戰」→「N 場、預估 X 秒」→ 開始／取消、進度 →
// 結果表（改前／改後／差值，每格附分子分母、分母 < 30 標「樣本小」）與勝負翻轉場數。
// 地圖戰：地圖（1～3 張）、我方（地圖預設陣容或 build）、受測招（預設＝草稿改到的技能）、「裝到 build」（只影響模擬）；
// 結果加單招施放率（施放次數／裝了這招的單位的行動回合）與每場平均次數。
// NW-2c：情境「比值」（1 階武器技的每 AP 傷害 ÷ 普攻每 AP；改前改後並排、參考線、匯入基準）。
import { useState } from "react";
import type { TuningMapSimResult, TuningRatioPlan, TuningSimInject, TuningSimJob, TuningSimOptions, TuningSimResult } from "../api/types";
import { battleCount, estimateText, flipsText, scaleProblem, secondsText, SIM_SCALES, simRows, type SimCell, type SimRow } from "./model";
import { DEFAULT_RATIO_FORM, ratioEstimate, type RatioForm } from "./ratioModel";
import { RatioResultTable, RatioSimForm } from "./RatioView";
import { MAP_SCALES, mapScaleProblem, mapSeedsFor, mapSimRows, MAX_MAPS, unusedProbes } from "./skillModel";

export type SimScenario = "boss" | "map" | "ratio";

export interface SimForm {
  boss: string;
  builds: readonly string[];
  seedsText: string;
  /** NW-2b：情境（沒給＝頭目戰）。 */
  scenario?: SimScenario;
  map?: MapForm;
  /** NW-2c：比值情境。 */
  ratio?: RatioForm;
}

export interface MapForm {
  maps: readonly string[];
  /** 每張地圖的種子數。 */
  seedsText: string;
  /** 我方 build（空＝地圖預設陣容）。 */
  allies: readonly string[];
  /** 受測招；`null` ＝ 用草稿改到的技能。 */
  probe: readonly string[] | null;
  inject: readonly TuningSimInject[];
}

export const DEFAULT_MAP_FORM: MapForm = { maps: [], seedsText: "24", allies: [], probe: null, inject: [] };

interface Props {
  options: TuningSimOptions;
  form: SimForm;
  job: TuningSimJob | null;
  /** 不能開始的原因（例如草稿驗證沒過）；`null` ＝ 可以。 */
  blocked: string | null;
  error: string | null;
  skillName(id: string): string;
  onForm(next: SimForm): void;
  onStart(): void;
  onCancel(): void;
  /** 地圖戰：草稿改到的技能（受測招的預設）。 */
  edited?: readonly string[];
  /** 地圖戰：可選的受測招（技能 ID → 中文名）。 */
  skillChoices?: readonly { id: string; name_zh: string }[];
  /** 比值：後端算的規模（`POST /skills/ratio-plan`；還沒算好是 `null`）。 */
  ratioPlan?: TuningRatioPlan | null;
  /** 比值：匯入基準的狀態文字。 */
  baselineNote?: string | null;
  onImport?(text: string): void;
}

export function seedsOf(text: string): number {
  return /^\d+$/.test(text.trim()) ? Number(text.trim()) : NaN;
}

function Cell({ cell }: { cell: SimCell }) {
  return (
    <td>
      <span className="tn-num">{cell.text}</span> <span className="muted small">（{cell.frac}）</span>
      {cell.small && <span className="tn-small">樣本小</span>}
    </td>
  );
}

export function SimResultTable({ result, skillName, buildName }: { result: TuningSimResult; skillName(id: string): string; buildName(id: string): string }) {
  return <ResultTable rows={simRows(result, skillName, buildName)} flips={flipsText(result)} cached={result.before_cached} />;
}

/** 地圖戰的結果表（含單招施放率）；受測招在改前改後都沒人用時提示「裝到 build」。 */
export function MapResultTable({ result, probes, skillName, mapName }: { result: TuningMapSimResult; probes: readonly string[]; skillName(id: string): string; mapName(id: string): string }) {
  const unused = unusedProbes(result, probes);
  const flips = flipsText(result);
  return (
    <>
      {unused.length > 0 && (
        <div className="tn-warn" role="alert">
          {unused.map(skillName).join("、")}：改前改後都沒有人用（裝了的單位行動 0 回合）。這招多半只在 build 上，請用「裝到 build」再跑一次。
        </div>
      )}
      <ResultTable rows={mapSimRows(result, skillName, mapName)} flips={flips} cached={result.before_cached} testid="tuning-map-result" />
    </>
  );
}

function ResultTable({ rows, flips, cached, testid = "tuning-sim-result" }: { rows: readonly SimRow[]; flips: string; cached: boolean; testid?: string }) {
  let lastGroup = "";
  return (
    <div className="tn-sim-result" data-testid={testid}>
      <div className="tn-flips">{flips}</div>
      {cached && <div className="muted small">改前結果用的是快取（同一份內容、同樣情境跑過）。</div>}
      <div className="tn-table-wrap">
        <table className="tn-table">
          <thead>
            <tr>
              <th>項目</th>
              <th>改前</th>
              <th>改後</th>
              <th>差值</th>
            </tr>
          </thead>
          <tbody>
            {rows.flatMap((r) => {
              const out = [];
              if (r.group !== lastGroup) {
                lastGroup = r.group;
                out.push(
                  <tr key={`g-${r.group}`} className="tn-group-row">
                    <th colSpan={4}>{r.group}</th>
                  </tr>,
                );
              }
              out.push(
                <tr key={`${r.group}-${r.label}`}>
                  <td>{r.label}</td>
                  <Cell cell={r.before} />
                  <Cell cell={r.after} />
                  <td className="tn-delta">{r.delta}</td>
                </tr>,
              );
              return out;
            })}
          </tbody>
        </table>
      </div>
      <div className="muted small">括號是分子／分母（場數或回合數）；分母小於 30 標「樣本小」，數字容易跳，想確定請改用「中」或加種子數再跑。</div>
    </div>
  );
}

function Progress({ job, unit, onCancel }: { job: TuningSimJob; unit: string; onCancel(): void }) {
  const pct = job.total > 0 ? Math.round((job.done / job.total) * 100) : 0;
  return (
    <div className="tn-progress" data-state={job.state}>
      <div className="tn-bar" role="progressbar" aria-valuemin={0} aria-valuemax={job.total} aria-valuenow={job.done} aria-label="模擬進度">
        <span style={{ width: `${pct}%` }} />
      </div>
      <span className="small">
        {job.done}/{job.total} {unit}・已過 {secondsText(job.elapsed_s)}・預估共 {secondsText(job.estimate_s)}
      </span>
      <button type="button" className="danger" onClick={onCancel}>
        取消模擬
      </button>
    </div>
  );
}

function BossForm({ options, form, running, onForm }: { options: TuningSimOptions; form: SimForm; running: boolean; onForm(next: SimForm): void }) {
  const seeds = seedsOf(form.seedsText);
  const toggle = (id: string) => {
    const has = form.builds.includes(id);
    const next = has ? form.builds.filter((b) => b !== id) : options.builds.map((b) => b.id).filter((b) => b === id || form.builds.includes(b));
    onForm({ ...form, builds: next });
  };
  return (
    <div className="tn-sim-form">
      <label>
        頭目
        <select value={form.boss} disabled={running} onChange={(e) => onForm({ ...form, boss: e.target.value })}>
          {options.bosses.map((b) => (
            <option key={b.key} value={b.key}>
              {b.name_zh}
            </option>
          ))}
        </select>
      </label>
      <div className="tn-scale" role="group" aria-label="規模">
        <span>規模</span>
        {SIM_SCALES.map((s) => (
          <button
            key={s.key}
            type="button"
            disabled={running}
            className={seeds === s.seeds ? "active" : ""}
            aria-pressed={seeds === s.seeds}
            onClick={() => onForm({ ...form, seedsText: String(s.seeds) })}
          >
            {s.label}（每個 build {s.seeds} 種子）
          </button>
        ))}
        <label className="tn-seeds">
          種子數
          <input value={form.seedsText} inputMode="numeric" disabled={running} onChange={(e) => onForm({ ...form, seedsText: e.target.value })} />
        </label>
      </div>
      <fieldset className="tn-builds" disabled={running}>
        <legend>
          我方 build（{form.builds.length}/{options.builds.length}）
          <button type="button" className="small-button" onClick={() => onForm({ ...form, builds: options.builds.map((b) => b.id) })}>
            全選
          </button>
        </legend>
        {options.builds.map((b) => (
          <label key={b.id} className="tn-build">
            <input type="checkbox" checked={form.builds.includes(b.id)} onChange={() => toggle(b.id)} />
            {b.name_zh}
          </label>
        ))}
      </fieldset>
    </div>
  );
}

/** 地圖戰實際的受測招（沒有自己選＝草稿改到的技能）。 */
export function probesOf(map: MapForm, edited: readonly string[]): string[] {
  return [...(map.probe ?? edited)];
}

interface MapFormProps {
  options: TuningSimOptions;
  map: MapForm;
  running: boolean;
  edited: readonly string[];
  skillChoices: readonly { id: string; name_zh: string }[];
  skillName(id: string): string;
  onMap(next: MapForm): void;
}

function MapSimForm({ options, map, running, edited, skillChoices, skillName, onMap }: MapFormProps) {
  const maps = options.maps ?? [];
  const seeds = seedsOf(map.seedsText);
  const probes = probesOf(map, edited);
  const toggleMap = (id: string) => {
    const next = map.maps.includes(id) ? map.maps.filter((m) => m !== id) : maps.map((m) => m.id).filter((m) => m === id || map.maps.includes(m));
    onMap({ ...map, maps: next });
  };
  const toggleAlly = (id: string) => {
    const next = map.allies.includes(id) ? map.allies.filter((b) => b !== id) : options.builds.map((b) => b.id).filter((b) => b === id || map.allies.includes(b));
    onMap({ ...map, allies: next });
  };
  const firstBuild = options.builds[0]?.id ?? "";
  return (
    <div className="tn-sim-form">
      <fieldset className="tn-builds" disabled={running}>
        <legend>
          地圖（{map.maps.length}/{MAX_MAPS}，用地圖的預設遭遇）
        </legend>
        {maps.map((m) => (
          <label key={m.id} className="tn-build">
            <input type="checkbox" checked={map.maps.includes(m.id)} disabled={!map.maps.includes(m.id) && map.maps.length >= MAX_MAPS} onChange={() => toggleMap(m.id)} />
            {m.name_zh}
          </label>
        ))}
      </fieldset>
      <div className="tn-scale" role="group" aria-label="地圖戰規模">
        <span>規模</span>
        {MAP_SCALES.map((s) => {
          const per = mapSeedsFor(s.battles, map.maps.length);
          return (
            <button key={s.key} type="button" disabled={running} className={seeds === per ? "active" : ""} aria-pressed={seeds === per} onClick={() => onMap({ ...map, seedsText: String(per) })}>
              {s.label}（約 {s.battles} 場）
            </button>
          );
        })}
        <label className="tn-seeds">
          每張圖種子數
          <input value={map.seedsText} inputMode="numeric" disabled={running} aria-label="每張圖種子數" onChange={(e) => onMap({ ...map, seedsText: e.target.value })} />
        </label>
      </div>
      <fieldset className="tn-builds" disabled={running}>
        <legend>
          我方（{map.allies.length === 0 ? "地圖預設陣容" : `換成 ${map.allies.length} 個 build`}）
          {map.allies.length > 0 && (
            <button type="button" className="small-button" onClick={() => onMap({ ...map, allies: [] })}>
              改回預設陣容
            </button>
          )}
        </legend>
        {options.builds.map((b) => (
          <label key={b.id} className="tn-build">
            <input type="checkbox" checked={map.allies.includes(b.id)} onChange={() => toggleAlly(b.id)} />
            {b.name_zh}
          </label>
        ))}
      </fieldset>
      <fieldset className="tn-builds tn-probe" disabled={running}>
        <legend>受測招（{map.probe === null ? "草稿改到的技能" : "自己選的"}）</legend>
        {probes.length === 0 && <span className="muted small">還沒有：草稿沒改到技能時，請從下面加一招。</span>}
        {probes.map((id) => (
          <span key={id} className="tn-tag">
            {skillName(id)}
            <button type="button" className="small-button" aria-label={`不量${skillName(id)}`} onClick={() => onMap({ ...map, probe: probes.filter((p) => p !== id) })}>
              ✕
            </button>
          </span>
        ))}
        <select
          value=""
          aria-label="加一個受測招"
          onChange={(e) => e.target.value !== "" && onMap({ ...map, probe: [...new Set([...probes, e.target.value])].sort() })}
        >
          <option value="">加一招…</option>
          {skillChoices
            .filter((s) => !probes.includes(s.id))
            .map((s) => (
              <option key={s.id} value={s.id}>
                {s.name_zh}（{s.id}）
              </option>
            ))}
        </select>
        {map.probe !== null && (
          <button type="button" className="small-button" onClick={() => onMap({ ...map, probe: null })}>
            改回草稿改到的
          </button>
        )}
      </fieldset>
      <fieldset className="tn-builds tn-inject" disabled={running}>
        <legend>裝到 build（只在模擬裡把受測招裝到 build 英雄身上，不寫檔）</legend>
        <div className="muted small">玩家招多半只在 build 上；地圖的預設陣容沒有人裝時，施放率會是 0。沒選「我方」時，模擬會用這裡的 build。</div>
        {map.inject.map((it, i) => (
          <span key={`${it.build}|${it.skill}`} className="tn-tag">
            {options.builds.find((b) => b.id === it.build)?.name_zh ?? it.build} ← {skillName(it.skill)}
            <button type="button" className="small-button" aria-label="拿掉這筆" onClick={() => onMap({ ...map, inject: map.inject.filter((_, j) => j !== i) })}>
              ✕
            </button>
          </span>
        ))}
        {probes.length > 0 && firstBuild !== "" && (
          <InjectAdder builds={options.builds} probes={probes} skillName={skillName} onAdd={(it) => onMap({ ...map, inject: [...map.inject.filter((x) => !(x.build === it.build && x.skill === it.skill)), it] })} />
        )}
      </fieldset>
      <div className="muted small">
        場數＝地圖張數 × 每張圖種子數，一次最多 {options.max_battles} 場、{MAX_MAPS} 張圖。
      </div>
    </div>
  );
}

function InjectAdder({ builds, probes, skillName, onAdd }: { builds: TuningSimOptions["builds"]; probes: readonly string[]; skillName(id: string): string; onAdd(it: TuningSimInject): void }) {
  const [build, setBuild] = useState(builds[0]?.id ?? "");
  const [picked, setPicked] = useState("");
  const skill = probes.includes(picked) ? picked : (probes[0] ?? "");
  return (
    <span className="tn-inject-add">
      <select aria-label="裝到哪個 build" value={build} onChange={(e) => setBuild(e.target.value)}>
        {builds.map((b) => (
          <option key={b.id} value={b.id}>
            {b.name_zh}
          </option>
        ))}
      </select>
      <select aria-label="裝哪一招" value={skill} onChange={(e) => setPicked(e.target.value)}>
        {probes.map((p) => (
          <option key={p} value={p}>
            {skillName(p)}
          </option>
        ))}
      </select>
      <button type="button" className="small-button" disabled={build === "" || skill === ""} onClick={() => onAdd({ build, skill })}>
        裝上
      </button>
    </span>
  );
}

/** 目前情境的「N 場、預估」或規模問題。 */
export function simEstimate(options: TuningSimOptions, form: SimForm, edited: readonly string[], ratioPlan: TuningRatioPlan | null = null): { problem: string | null; text: string } {
  if (form.scenario === "ratio") return ratioEstimate(ratioPlan, form.ratio ?? DEFAULT_RATIO_FORM, edited);
  if ((form.scenario ?? "boss") === "map") {
    const map = form.map ?? DEFAULT_MAP_FORM;
    const seeds = seedsOf(map.seedsText);
    const problem = mapScaleProblem(options, map.maps.length, seeds) ?? (probesOf(map, edited).length === 0 ? "至少要有一個受測招（草稿改到的技能，或自己加）" : null);
    return { problem, text: problem ?? estimateText(options, map.maps.length * seeds, options.map_seconds_per_battle) };
  }
  const seeds = seedsOf(form.seedsText);
  const problem = scaleProblem(options, form.builds.length, seeds);
  return { problem, text: problem ?? estimateText(options, battleCount(form.builds.length, seeds)) };
}

export function SimPanel({ options, form, job, blocked, error, skillName, onForm, onStart, onCancel, edited = [], skillChoices = [], ratioPlan = null, baselineNote = null, onImport }: Props) {
  const scenario = form.scenario ?? "boss";
  const map = form.map ?? DEFAULT_MAP_FORM;
  const { problem, text } = simEstimate(options, form, edited, ratioPlan);
  const running = job?.state === "running";
  const buildName = (id: string) => options.builds.find((b) => b.id === id)?.name_zh ?? id;
  const mapName = (id: string) => options.maps?.find((m) => m.id === id)?.name_zh ?? id;
  return (
    <section className="panel tn-sim" aria-label="小模擬">
      <div className="section-title">小模擬（改前 vs 改後）</div>
      <div className="tn-tabs" role="tablist" aria-label="模擬情境">
        {(
          [
            ["boss", "頭目戰"],
            ["map", "地圖戰"],
            ["ratio", "比值"],
          ] as const
        ).map(([key, label]) => (
          <button key={key} type="button" role="tab" aria-selected={scenario === key} className={scenario === key ? "active" : ""} disabled={running} onClick={() => onForm({ ...form, scenario: key })}>
            {label}
          </button>
        ))}
      </div>
      <div className="muted small">
        用目前的草稿（還沒寫回也可以）和現在的數值各打一次，同樣的種子配對比較。模擬不用重開伺服器。
        {scenario === "map" && "地圖戰看勝率與受測招的施放率；頭目招的施放率請用頭目戰。"}
        {scenario === "ratio" && "比值在主城靶場打木樁（BAL-21e 的量法）：技能每 AP 傷害 ÷ 普攻每 AP；只量 1 階主動武器技。"}
      </div>
      {scenario === "boss" ? (
        <BossForm options={options} form={form} running={running} onForm={onForm} />
      ) : scenario === "ratio" ? (
        <RatioSimForm
          form={form.ratio ?? DEFAULT_RATIO_FORM}
          running={running}
          edited={edited}
          skillChoices={skillChoices}
          skillName={skillName}
          baselineNote={baselineNote}
          onForm={(r) => onForm({ ...form, ratio: r })}
          onImport={(t) => onImport?.(t)}
        />
      ) : (
        <MapSimForm options={options} map={map} running={running} edited={edited} skillChoices={skillChoices} skillName={skillName} onMap={(m) => onForm({ ...form, map: m })} />
      )}
      <div className="tn-estimate" data-testid="tuning-sim-estimate">
        {text}
      </div>
      <div className="muted small">同時用 {options.workers} 個程序跑；PM 跑全量測試時會比較慢。</div>
      {blocked !== null && !running && <div className="tn-error">{blocked}</div>}
      {error !== null && (
        <div className="tn-error" role="alert">
          {error}
        </div>
      )}
      {running ? (
        <Progress job={job} unit={scenario === "ratio" ? "組" : "場"} onCancel={onCancel} />
      ) : (
        <button type="button" className="primary" disabled={problem !== null || blocked !== null} onClick={onStart}>
          開始模擬
        </button>
      )}
      {job !== null && job.state === "cancelled" && <div className="muted">模擬已取消。</div>}
      {job !== null && job.state === "failed" && <div className="tn-error">模擬失敗：{job.error_zh ?? "原因不明"}</div>}
      {job !== null && job.state === "done" && job.result != null && <SimResultTable result={job.result} skillName={skillName} buildName={buildName} />}
      {job !== null && job.state === "done" && job.map_result != null && <MapResultTable result={job.map_result} probes={probesOf(map, edited)} skillName={skillName} mapName={mapName} />}
      {job !== null && job.state === "done" && job.ratio_result != null && <RatioResultTable result={job.ratio_result} skillName={skillName} />}
    </section>
  );
}
