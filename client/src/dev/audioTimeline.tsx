// 開發頁的「戰鬥時間軸試聽」（AU-3）：選一招，聽整段起手 → 出招 → 命中 → 結果。
// 走正式的推導：`playbackPlan`（vfxFor → skillTimeline → withSpecials → withImpact，含音效）→ `cueRealMs`（停頓、最後一擊放慢）
// → `CueScheduler`（和戰鬥畫面同一套排程；可以試按住 2 倍速、播放中跳過）。下方列出每個音效在效果時鐘與實際時間的位置。
import { useEffect, useMemo, useRef, useState } from "react";
import type { BattleResponse, BattleView, SkillCard, UnitView } from "../api/types";
import { audio } from "../audio";
import { ambienceFor, type AmbiencePlace } from "../audio/ambience";
import { cueRealMs, type SfxCue } from "../audio/battleSfx";
import { ambienceDirector, loopDeck } from "../audio/scene";
import { SFX_TABLE } from "../audio/sfxLibrary";
import { CueScheduler } from "../audio/sfxScheduler";
import { playbackPlan, type Frame, type PlaySpeed } from "../battle/playback";
import { tile, unit } from "../battle/testFixtures";
import type { WeaponClass } from "../render/skillClips";

const HERO = "u_hero";

interface Demo {
  id: string;
  zh: string;
  weapon: WeaponClass;
  /** 技能卡：形狀、射程、元素、部件。 */
  shape: string;
  range: number;
  effects: string[];
  element: string;
  /** 打幾個人（直線）。 */
  targets: number;
  crit?: boolean;
  /** 打倒最後一個敵人（最後一擊放慢＋勝利）。 */
  finisher?: boolean;
  status?: string;
  /** 對自己人（治療、護盾）。 */
  ally?: boolean;
}

const DEMOS: readonly Demo[] = [
  { id: "slash", zh: "劍・揮砍（近身）", weapon: "blade", shape: "single", range: 1, effects: ["damage"], element: "physical", targets: 1 },
  { id: "thrust", zh: "長槍・突刺", weapon: "spear", shape: "single", range: 1, effects: ["damage"], element: "physical", targets: 1 },
  { id: "punch", zh: "拳套・重拳", weapon: "fist", shape: "single", range: 1, effects: ["damage"], element: "physical", targets: 1 },
  { id: "bow", zh: "弓・射擊（拉弓 → 放箭 → 命中）", weapon: "bow", shape: "single", range: 5, effects: ["damage"], element: "physical", targets: 1 },
  { id: "gun", zh: "火槍・射擊（上膛 → 槍響）", weapon: "gun", shape: "single", range: 5, effects: ["damage"], element: "physical", targets: 1 },
  { id: "fireball", zh: "法杖・火球（詠唱 → 火）", weapon: "staff", shape: "single", range: 5, effects: ["damage"], element: "fire", targets: 1 },
  { id: "sigil", zh: "魔導劍・畫符雷擊", weapon: "arcane", shape: "single", range: 5, effects: ["damage"], element: "lightning", targets: 1 },
  { id: "frost", zh: "法球・冰凍術（冰＋冰凍上身）", weapon: "orb", shape: "single", range: 4, effects: ["damage", "apply_status"], element: "ice", targets: 1, status: "frozen" },
  { id: "sweep", zh: "劍・橫掃 5 人（同一刻合併）", weapon: "blade", shape: "line", range: 1, effects: ["damage"], element: "physical", targets: 5 },
  { id: "crit", zh: "劍・暴擊（停頓 100 ms）", weapon: "blade", shape: "single", range: 1, effects: ["damage"], element: "physical", targets: 1, crit: true },
  { id: "final", zh: "劍・最後一擊（擊殺、放慢、倒下）", weapon: "blade", shape: "single", range: 1, effects: ["damage"], element: "physical", targets: 1, finisher: true },
  { id: "heal", zh: "法杖・治療隊友", weapon: "staff", shape: "single", range: 4, effects: ["heal"], element: "support", targets: 1, ally: true },
];

function viewOf(units: UnitView[]): BattleView {
  const tiles = [];
  for (let y = 0; y < 7; y++) for (let x = 0; x < 8; x++) tiles.push(tile(x, y, { terrain: "grass" }));
  return {
    team: "ally",
    map_id: "dev_audio",
    map_name_zh: "試聽",
    width: 8,
    height: 7,
    tiles,
    objects: [],
    units,
    traps: [],
    turn_order: units.map((u) => u.id),
    active_unit: HERO,
    round: 1,
    max_rounds: 30,
    weather_id: null,
    weather_name_zh: null,
    objective: { kind: "eliminate" },
    ended: false,
    winner: null,
    end_reason: null,
    pending: null,
    source_wells: [],
    zones: [],
    runes: [],
    summon_command_ap_cost: 1,
    summon_infuse_ap_cost: 1,
  } as unknown as BattleView;
}

/** 一招的回應（只有一步）：正式的事件格式。 */
function demoResponse(d: Demo): { res: BattleResponse; cards: Record<string, SkillCard> } {
  const far = d.range > 1;
  const hx = far ? 1 : 3;
  const targets = Array.from({ length: d.targets }, (_, i) => (d.ally ? unit(`u_ally${i}`, "ally", 5, 3, { hp: 40, max_hp: 100 }) : unit(`u_foe${i}`, "enemy", 4 + (far ? 2 : 0), d.targets === 1 ? 3 : 1 + i, { hp: 100, max_hp: 100 })));
  const others = d.finisher === true ? [] : d.ally ? [unit("u_foe9", "enemy", 7, 6, { hp: 100, max_hp: 100 })] : [];
  const hero = unit(HERO, "ally", hx, 3, { hp: 100, max_hp: 100 });
  const before = viewOf([hero, ...targets, ...others]);
  const card = { id: "sk", shape: d.shape === "line" ? "直線" : "單體", skeleton: "strike", effect_ids: d.effects, icon: { segments: [{ skeleton: "strike", shape_id: d.shape, range: d.range, element: d.element, effects: d.effects.map((type) => ({ type })) }] } } as unknown as SkillCard;
  const tiles = targets.map((t) => t.pos);
  const events: Record<string, unknown>[] = [{ seq: 1, round: 1, type: "skill_used", unit_id: HERO, skill_id: "sk", tiles }];
  let seq = 2;
  for (const t of targets) {
    if (d.ally) events.push({ seq: seq++, round: 1, type: "healed", target_id: t.id, source_id: HERO, amount: 30 });
    else {
      const amount = d.finisher === true ? 100 : 30;
      events.push({ seq: seq++, round: 1, type: "damage_dealt", target_id: t.id, source_id: HERO, element: d.element, amount, hp_before: 100, hp_after: 100 - amount, crit: d.crit === true });
      if (d.status !== undefined) events.push({ seq: seq++, round: 1, type: "status_applied", target_id: t.id, source_id: HERO, status_id: d.status });
      if (d.finisher === true) events.push({ seq: seq++, round: 1, type: "unit_downed", unit_id: t.id });
    }
  }
  if (d.finisher === true) events.push({ seq: seq++, round: 1, type: "battle_ended", winner: "ally" });
  const after = viewOf(before.units.map((u) => (d.finisher === true && u.team === "enemy" ? { ...u, hp: 0, downed: true } : u)));
  const res = { battle_id: "dev", hero_id: HERO, initial_view: before, view: after, steps: [{ actor_id: HERO, events, view: after, step: { type: "use_skill" } }] } as unknown as BattleResponse;
  return { res, cards: { sk: card } };
}

interface Row extends SfxCue {
  realMs: number;
}

function rowsOf(frame: Frame | undefined, reduced: boolean): Row[] {
  if (frame === undefined) return [];
  return (frame.sfx ?? []).map((c) => ({ ...c, realMs: Math.round(cueRealMs(c.atMs, frame.vfx, reduced)) }));
}

const SCENES: ReadonlyArray<{ zh: string; place: AmbiencePlace }> = [
  { zh: "雲嶺（風）", place: { region: "cloud_ridge", interior: false, facilities: [], rain: false } },
  { zh: "雲嶺下雨（風＋雨＋遠雷）", place: { region: "cloud_ridge", interior: false, facilities: [], rain: true } },
  { zh: "荒原（熱風＋火）", place: { region: "ashen_waste", interior: false, facilities: [], rain: false } },
  { zh: "主城（遠處鐘聲）", place: { region: "capital", interior: false, facilities: [], rain: false } },
  { zh: "鐵匠鋪（爐火＋打鐵）", place: { region: "cloud_ridge", interior: true, facilities: ["smithy"], rain: false } },
  { zh: "酒館（爐火）", place: { region: "cloud_ridge", interior: true, facilities: ["tavern"], rain: false } },
  { zh: "導師殿（安靜）", place: { region: "capital", interior: true, facilities: ["mentor"], rain: false } },
];

/** 環境音試聽：用正式的 `ambienceFor` 與導演（放在環境軌；減少刺耳音效開著時遠雷、打鐵不出聲）。 */
export function AmbiencePreview() {
  const [on, setOn] = useState<string | null>(null);
  useEffect(() => () => ambienceDirector().set("world", null), []);
  const pick = (zh: string | null, place: AmbiencePlace | null) => {
    audio.unlock();
    setOn(zh);
    ambienceDirector().set("world", place === null ? null : ambienceFor(place));
  };
  const scene = on === null ? null : ambienceFor(SCENES.find((s) => s.zh === on)?.place ?? SCENES[0]!.place);
  return (
    <div>
      <div className="ag-buttons">
        {SCENES.map((s) => (
          <button key={s.zh} type="button" data-sfx="none" aria-pressed={on === s.zh} onClick={() => pick(s.zh, s.place)}>
            {s.zh}
          </button>
        ))}
        <button type="button" data-sfx="none" onClick={() => pick(null, null)}>
          停止
        </button>
      </div>
      <div className="ag-log" data-testid="ag-amb">
        {scene === null ? "沒有環境音" : `底聲：${scene.beds.map((b) => `${b.id}×${b.gain}`).join("、") || "無"}；點綴：${scene.accents.map((a) => `${a.id}（約每 ${a.everyMs / 1000} 秒）`).join("、") || "無"}；在放：${loopDeck().playing().join("、") || "無"}`}
      </div>
    </div>
  );
}

const CAT_COLOR: Record<string, string> = { windup: "#8fb3ff", swing: "#e8bb48", hit: "#e07a5a", element: "#e07a5a", result: "#c78cf2", primitive: "#7cf29a", status: "#7cd8f2", surface: "#a8c070", system: "#f2a07c", explosion: "#ff6040" };

export function BattleTimeline() {
  const [demoId, setDemoId] = useState(DEMOS[0]!.id);
  const [speed, setSpeed] = useState<PlaySpeed>("normal");
  const [boost, setBoost] = useState(false);
  const [reduced, setReduced] = useState(false);
  const [started, setStarted] = useState<number | null>(null);
  const [now, setNow] = useState(0);
  const sched = useRef<CueScheduler | null>(null);
  sched.current ??= new CueScheduler(audio, undefined, "dev_timeline");
  const demo = DEMOS.find((d) => d.id === demoId) ?? DEMOS[0]!;
  const plan = useMemo(() => {
    const { res, cards } = demoResponse(demo);
    return playbackPlan(res, HERO, speed, cards, new Set(), () => demo.weapon, () => null);
  }, [demo, speed]);
  const frame = plan.frames[0];
  const rows = rowsOf(frame, reduced);
  const total = Math.max(400, ...rows.map((r) => r.realMs + 300));
  const rate = boost ? 2 : 1;

  useEffect(() => {
    sched.current?.setBoost(rate);
  }, [rate]);
  // 播放頭（只畫畫面；聲音的時間由 AudioContext 排）
  useEffect(() => {
    if (started === null) return undefined;
    let raf = 0;
    const loop = () => {
      const p = (audio.now() - started) * 1000 * rate;
      setNow(p);
      if (p < total) raf = window.requestAnimationFrame(loop);
    };
    raf = window.requestAnimationFrame(loop);
    return () => window.cancelAnimationFrame(raf);
  }, [started, total, rate]);

  const play = () => {
    audio.unlock();
    sched.current?.cancelAll();
    sched.current?.setBoost(rate);
    sched.current?.start(rows.map((r) => ({ id: r.id, realMs: r.realMs, key: r.key, count: r.count })));
    setStarted(audio.now());
  };
  const skip = () => {
    sched.current?.cancelAll();
    setStarted(null);
    setNow(0);
  };
  const W = 760;
  const x = (ms: number) => 10 + (ms / total) * (W - 20);
  const stops = frame?.vfx?.stops ?? [];
  const slow = frame?.vfx?.slow;

  return (
    <div className="ag-timeline" data-testid="ag-timeline">
      <div className="ag-buttons">
        <label className="ag-num">
          招式
          <select value={demoId} onChange={(e) => setDemoId(e.target.value)} data-testid="ag-tl-demo">
            {DEMOS.map((d) => (
              <option key={d.id} value={d.id}>
                {d.zh}
              </option>
            ))}
          </select>
        </label>
        <label className="ag-num">
          速度
          <select value={speed} onChange={(e) => setSpeed(e.target.value as PlaySpeed)}>
            <option value="slow">慢（2 倍時間）</option>
            <option value="normal">正常</option>
            <option value="fast">快（一半）</option>
          </select>
        </label>
        <label className="ag-num">
          <input type="checkbox" checked={boost} onChange={(e) => setBoost(e.target.checked)} data-testid="ag-tl-boost" />
          按住 2 倍速（只改排程，不變調）
        </label>
        <label className="ag-num">
          <input type="checkbox" checked={reduced} onChange={(e) => setReduced(e.target.checked)} />
          減少動態（不停頓、不放慢）
        </label>
        <button type="button" className="primary" data-sfx="none" onClick={play} data-testid="ag-tl-play">
          播放整段
        </button>
        <button type="button" data-sfx="none" onClick={skip} data-testid="ag-tl-skip">
          跳過（取消還沒響的）
        </button>
      </div>
      <svg className="ag-tl-svg" viewBox={`0 0 ${W} 120`} width={W} height={120} role="img" aria-label="音效時間軸">
        <rect x={0} y={0} width={W} height={120} fill="#15171b" rx={4} />
        {stops.map((s) => (
          <rect key={`s${s.atMs}`} x={x(cueRealMs(s.atMs, frame?.vfx ?? null, reduced))} y={8} width={reduced ? 0 : Math.max(2, (s.ms / total) * (W - 20))} height={104} fill="#e8bb4833" />
        ))}
        {slow !== undefined && !reduced && <rect x={x(cueRealMs(slow.fromMs, frame?.vfx ?? null, false))} y={8} width={x(cueRealMs(slow.toMs, frame?.vfx ?? null, false)) - x(cueRealMs(slow.fromMs, frame?.vfx ?? null, false))} height={104} fill="#7cd8f222" />}
        {rows.map((r, i) => {
          const cat = SFX_TABLE.defs[r.id]?.cat ?? "hit";
          return (
            <g key={`${r.id}-${r.atMs}`}>
              <line x1={x(r.realMs)} x2={x(r.realMs)} y1={14} y2={106} stroke={CAT_COLOR[cat] ?? "#d8dbe0"} strokeWidth={2} />
              <text x={x(r.realMs) + 3} y={24 + (i % 6) * 15} fill={CAT_COLOR[cat] ?? "#d8dbe0"} fontSize={11}>
                {SFX_TABLE.defs[r.id]?.zh ?? r.id}
                {r.count > 1 ? ` ×${r.count}` : ""}
              </text>
            </g>
          );
        })}
        {started !== null && <line x1={x(Math.min(now, total))} x2={x(Math.min(now, total))} y1={4} y2={116} stroke="#ffffff" strokeWidth={1} />}
        <text x={W - 8} y={114} fill="#9aa3ad" fontSize={10} textAnchor="end">
          {Math.round(total)} ms
        </text>
      </svg>
      <table className="ag-tl-table">
        <thead>
          <tr>
            <th>音效</th>
            <th>id</th>
            <th>效果時鐘 ms</th>
            <th>實際 ms</th>
            <th>次數</th>
            <th>變體鍵（和動畫同一把）</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.id}-${r.atMs}`}>
              <td>{SFX_TABLE.defs[r.id]?.zh ?? r.id}</td>
              <td>
                <code>{r.id}</code>
              </td>
              <td>{r.atMs}</td>
              <td>{r.realMs}</td>
              <td>{r.count}</td>
              <td>
                <code>{r.key}</code>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="ag-log">
        停頓 {stops.map((s) => `${s.atMs}+${s.ms}`).join("、") || "無"}
        {slow !== undefined ? `；最後一擊放慢 ${slow.fromMs}～${slow.toMs} ms（0.4 倍）` : ""}；已交給引擎 {sched.current?.sent.filter((s) => s.at >= (started ?? 0)).length ?? 0} 筆
      </div>
    </div>
  );
}
