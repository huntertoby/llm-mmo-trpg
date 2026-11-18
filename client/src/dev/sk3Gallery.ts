// 開發用：SK-3 的新觸發「你造的關鍵字被利用時」與重擲反應的戰鬥演出。開 `client/dev/sk3-gallery.html`
// （pnpm dev 後 /dev/sk3-gallery.html）；不屬於正式 build。
// 事件是真引擎跑出來的（`dev/fixtures/sk3Events.json`，產生方式見 docs/phases/PhaseSK-3報告.md），走正式的
// playbackPlan → frameOps → BattleRenderer；畫面資料照產生事件的測試戰場手抄（寫法同 sk2Gallery）。
//   ?case=exploit|reroll_worse|reroll_better（預設 exploit）
//        AR-SK3 另加 reroll_worseup（對方逼重擲、重擲反而比較好：6 → 15，算第一次）、reroll_keepfirst（沒比較好：12 → 5，算第一次）；
//        這兩個的事件是把真引擎的 reroll_worse／reroll_better 改點數與 `kept`（只換數字，演出走同一條路）
//   &freeze=<毫秒>  中間那格停在演出開始後第幾毫秒
//   &scale=<倍率>   畫面縮放（預設 1.2）
//   &w=1600|800     AR-SK3：畫面縮放照遊戲的地圖縮放（1600 寬 1.31、800 寬 0.53）
//   &strip=<毫秒,…> AR-SK3：只畫「演出中」一排關鍵影格（每格停在演出開始後第幾毫秒）
//   &upper=1        AR-SK3：上一排站人（擲骰者正上、左上、右上、再右），看骰子會不會蓋到他們的血條
//   &boss=giant|lord AR-SK3：擲骰的盜賊換成巨型頭目（灰燼之心 3×3）或頭目（碎晶之主），看骰子位置（移植需求第 6 項）
//   &slow=<倍數>    AR-SK3：動畫放慢幾倍（停格更準）
// 每列三格：動作前、演出中（停格，浮字看得到）、結算後。畫好後 `document.body.dataset.ready = "1"`。
import type { Application } from "pixi.js";
import type { BattleResponse, BattleView, Glossary, SkillCard, StatusView, StepOut, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import fixture from "./fixtures/sk3Events.json";
import looks from "./fixtures/moltenHeartUnits.json";
import { buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { frameOps, playbackPlan } from "../battle/playback";
import { tile, unit } from "../battle/testFixtures";
import { attackFamilyInView, creatureStrikeInView, weaponClassInView } from "../battle/viewGrip";
import { BattleRenderer } from "../render/BattleRenderer";
import { UNIT_DOLLS } from "../render/testDolls";
import { waitForFonts } from "../render/fontLoad";

setGlossary(glossary as unknown as Glossary);
await waitForFonts();

const HERO = "unit_0001";
const W = 9;
const H = 7;
const params = new URLSearchParams(location.search);
const caseId = params.get("case") ?? "exploit";
/** 遊戲的地圖縮放（AR-SK2 sk2-gallery 量的）：1600 寬 1.31、800 寬 0.53。 */
const WIDTH_SCALE: Readonly<Record<string, number>> = { "1600": 1.31, "800": 0.53 };
const scale = WIDTH_SCALE[params.get("w") ?? ""] ?? Number(params.get("scale") ?? "1.2");
const strip = (params.get("strip") ?? "").split(",").filter((x) => x !== "").map(Number);
const upper = params.get("upper") === "1";
const bossKind = params.get("boss");
const slow = Math.max(1, Number(params.get("slow") ?? "1"));

type FixtureUnit = { pos: [number, number]; hp: number; downed: boolean; statuses: { status_id: string; remaining: number | null }[] };
type FixtureCase = { events: Record<string, unknown>[]; units: Record<string, FixtureUnit>; log: string[] };
const DATA = fixture as unknown as Record<string, FixtureCase>;

interface Case {
  title: string;
  actor: string;
  step: Record<string, unknown>;
  skill: string | null;
  card: SkillCard | null;
  freeze: number;
  before: UnitView[];
  surfaces?: Record<string, string>;
}

const status = (id: string, remaining: number | null): StatusView => ({ status_id: id, remaining, source_id: HERO, amount: null, charge_tiles: [], cost_status: false }) as StatusView;
const ally = (id: string, name: string, x: number, y: number, template: string, weapon: string, hp = 40): UnitView =>
  unit(id, "ally", x, y, { template_id: template, name_zh: name, weapon_id: weapon, hp, max_hp: 40, facing: "east" });
const foe = (x: number, y: number): UnitView => unit("unit_0002", "enemy", x, y, { template_id: "bandit", name_zh: "盜賊", hp: 40, max_hp: 40, facing: "west" });

function card(skill: string, effects: string[]): SkillCard {
  return { id: skill, shape: "單體", skeleton: "strike", effect_ids: effects, icon: { segments: [{ skeleton: "strike", shape_id: "single", range: 5, effects: effects.map((type) => ({ type })) }] } } as unknown as SkillCard;
}

const CASES: Readonly<Record<string, Case>> = {
  exploit: {
    title: "你造的關鍵字被利用時：法師2 造的水，被法師1 的雷擊打到站在水裡的盜賊（導電）→ 法師2 的被動「潮汐共鳴」觸發，回血",
    actor: HERO,
    step: { type: "use_skill" },
    skill: "skill_sk3_bolt",
    card: card("skill_sk3_bolt", ["damage"]),
    freeze: 900,
    before: [ally(HERO, "法師1", 1, 3, "hero_mage", "fire_staff"), foe(5, 3), ally("unit_0003", "法師2", 1, 5, "hero_mage", "fire_staff", 30)],
    surfaces: { "5,3": "water" },
  },
  reroll_worse: {
    title: "重擲（敵人擲中你時）：盜賊擲 19 命中戰士，戰士的「厄運之眼」逼他重擲，取較差的 2 → 失手",
    actor: "unit_0002",
    step: { type: "attack" },
    skill: null,
    card: null,
    freeze: 500,
    before: [ally(HERO, "戰士", 4, 3, "hero_fighter", "longsword"), foe(5, 3), ally("unit_0003", "法師", 4, 4, "hero_mage", "fire_staff")],
  },
  reroll_better: {
    title: "重擲（隊友擲失手時）：戰士擲 1 失手，身旁法師的「鼓舞」讓他重擲，取較好的 18 → 命中",
    actor: HERO,
    step: { type: "attack" },
    skill: null,
    card: null,
    freeze: 500,
    before: [ally(HERO, "戰士", 4, 3, "hero_fighter", "longsword"), foe(5, 3), ally("unit_0003", "法師", 4, 4, "hero_mage", "fire_staff")],
  },
};

/** AR-SK3：另外兩種情況（只換點數與算哪一次；其他事件照真引擎）。 */
const VARIANTS: Readonly<Record<string, { from: string; title: string; first: number; second: number; kept: "first" | "second" }>> = {
  reroll_worseup: { from: "reroll_worse", title: "重擲（敵人擲中你時）：盜賊擲 6，戰士的「厄運之眼」逼他重擲 → 15，取較差的仍是第一次的 6（「採用」落在第一次）", first: 6, second: 15, kept: "first" },
  reroll_keepfirst: { from: "reroll_better", title: "重擲（隊友擲失手時）：戰士擲 12，法師的「鼓舞」讓他重擲 → 5，取較好的仍是第一次的 12（沒比較好）", first: 12, second: 5, kept: "first" },
};
function variantData(id: string): FixtureCase | undefined {
  const v = VARIANTS[id];
  if (v === undefined) return undefined;
  const base = DATA[v.from]!;
  const kept = v.kept === "first" ? v.first : v.second;
  const events = base.events.map((e) => (e.type === "attack_rerolled" ? { ...e, first_natural: v.first, second_natural: v.second, kept: v.kept } : e.type === "attack_rolled" ? { ...e, natural: kept, rolls: [kept] } : e));
  return { ...base, events };
}
/** AR-SK3：上一排站人。 */
const UPPER_ROW = (): UnitView[] => [
  ally("unit_0011", "弓手", 4, 2, "hero_archer", "longbow"),
  unit("unit_0012", "enemy", 5, 2, { template_id: "bandit_archer", name_zh: "盜賊弓手", hp: 40, max_hp: 40, facing: "west" }),
  unit("unit_0013", "enemy", 6, 2, { template_id: "bandit_shieldbearer", name_zh: "持盾弟子", hp: 40, max_hp: 40, facing: "west" }),
  ally("unit_0014", "法師2", 3, 2, "hero_mage", "fire_staff"),
];
/** AR-SK3：擲骰者換成巨型頭目（東移一格，佔 (5..7, 2..4)）或頭目。 */
function withBoss(units: UnitView[]): UnitView[] {
  if (bossKind === "giant") {
    const g = looks.ashen_heart as unknown as UnitView;
    const giant = { ...g, id: "unit_0002", pos: { x: 6, y: 3 }, tiles: (g.tiles ?? []).map((t) => ({ x: t.x + 1, y: t.y })), facing: "west" } as UnitView;
    return units.map((u) => (u.id === "unit_0002" ? giant : u));
  }
  if (bossKind === "lord") {
    // 同 oclGallery 的頭目：範本＋紙娃娃外觀（有的話）＋boss 標籤與階段
    const doll = UNIT_DOLLS["rift_shard_lord"];
    const lord = (u: UnitView): UnitView => ({ ...u, template_id: "rift_shard_lord", name_zh: "碎晶之主", tags: ["boss", "elite"], boss_phase: { index: 2, total: 4, name_zh: "第 2 階段" }, ...(doll === undefined ? {} : { doll_look: doll }) }) as unknown as UnitView;
    return units.map((u) => (u.id === "unit_0002" ? lord(u) : u));
  }
  return units;
}

function tiles(surfaces: Record<string, string>): TileView[] {
  const out: TileView[] = [];
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++)
      out.push(tile(x, y, { terrain: (x + y) % 7 === 0 ? "dirt" : "stone", surface: (surfaces[`${x},${y}`] ?? "none") as TileView["surface"] }));
  return out;
}

function view(units: UnitView[], surfaces: Record<string, string>, active: string): BattleView {
  return {
    team: "ally", map_id: "sk3_gallery", map_name_zh: "SK-3", width: W, height: H, tiles: tiles(surfaces), objects: [], units, traps: [],
    turn_order: [HERO, "unit_0002", "unit_0003"], active_unit: active, round: 1, max_rounds: 30, weather_id: null, weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null,
    source_wells: [], zones: [], runes: [],
  } as unknown as BattleView;
}

function afterUnits(c: Case, data: FixtureCase): UnitView[] {
  return c.before.map((u) => {
    const got = data.units[u.id];
    if (got === undefined) return u;
    const statuses = got.statuses.map((s) => status(s.status_id, s.remaining));
    return { ...u, pos: { x: got.pos[0], y: got.pos[1] }, hp: got.hp, downed: got.downed, statuses } as UnitView;
  });
}

async function cell(row: HTMLElement, caption: string): Promise<BattleRenderer> {
  const box = document.createElement("div");
  box.className = "cell";
  box.appendChild(Object.assign(document.createElement("h3"), { textContent: caption }));
  const frame = document.createElement("div");
  box.appendChild(frame);
  row.appendChild(box);
  const r = new BattleRenderer();
  await r.init(frame);
  r.setScale(scale);
  r.setIdle(false);
  if (slow > 1) r.setBoost(1 / slow);
  return r;
}

const wait = (ms: number) => new Promise<void>((done) => window.setTimeout(done, ms));

async function play(r: BattleRenderer, res: BattleResponse, c: Case, freeze: number): Promise<void> {
  const cards = c.skill === null || c.card === null ? {} : { [c.skill]: c.card };
  const plan = playbackPlan(res, HERO, "normal", cards, new Set(), weaponClassInView, attackFamilyInView, creatureStrikeInView, false);
  r.draw(buildDrawModel(plan.initialView, HERO));
  const clock = () => (r as unknown as { effectClock: number }).effectClock;
  const t0 = clock();
  let frozen = false;
  const check = () => {
    if (clock() - t0 >= freeze) {
      r.setBoost(1e-6);
      frozen = true;
    } else requestAnimationFrame(check);
  };
  requestAnimationFrame(check);
  for (const frame of plan.frames)
    for (const op of frameOps(frame)) {
      if (frozen) return;
      if (op.op === "move") await Promise.race([r.animate([op.anim], () => false), wait(3000)]);
      else if (op.op === "vfx") {
        const origins = op.skill === undefined ? undefined : r.playSkill(op.skill);
        r.playVfx(op.vfx, op.impactMs, false, origins);
        await wait(op.vfx.leadMs);
      } else if (op.op === "reroll") {
        // AR-SK3：骰子層；浮字「重擲！」照繪製器的時鐘在骰子比較完才出（停格時跟著停）
        const t1 = clock();
        r.playReroll(op.reroll.fx, op.reroll.scale);
        for (const f of op.reroll.floats) {
          while (!frozen && clock() - t1 < f.atMs) await new Promise((ok) => requestAnimationFrame(ok));
          if (frozen && clock() - t1 < f.atMs) return;
          r.playFeedback(f.items, op.reroll.feedbackMs);
        }
        while (!frozen && clock() - t1 < op.reroll.durationMs) await new Promise((ok) => requestAnimationFrame(ok));
      } else if (op.op === "view") r.draw(buildDrawModel(op.view, HERO));
      else if (op.op === "feedback") r.playFeedback(op.items, op.durationMs);
      else if (op.op === "pause") await wait(op.ms);
    }
}

const variant = VARIANTS[caseId];
const c0 = CASES[variant?.from ?? caseId] ?? CASES.exploit!;
const c: Case = { ...c0, ...(variant === undefined ? {} : { title: variant.title }), before: withBoss([...c0.before, ...(upper ? UPPER_ROW() : [])]) };
const data = variantData(caseId) ?? DATA[caseId in CASES ? caseId : "exploit"]!;
const freeze = Number(params.get("freeze") ?? String(c.freeze));
document.body.appendChild(Object.assign(document.createElement("h2"), { textContent: c.title }));
document.body.appendChild(Object.assign(document.createElement("p"), { className: "log", textContent: data.log.join("\n") }));
const row = document.createElement("div");
row.className = "row";
document.body.appendChild(row);
const before = view(c.before, c.surfaces ?? {}, c.actor);
const after = view(afterUnits(c, data), c.surfaces ?? {}, c.actor);
const step = { actor_id: c.actor, events: data.events, view: after, step: { ...c.step, unit_id: c.actor } } as unknown as StepOut;
const res = { steps: [step], initial_view: before, view: after } as unknown as BattleResponse;
if (strip.length > 0) {
  // AR-SK3：關鍵影格一排（每格各自一個繪製器，停在演出開始後第幾毫秒）
  row.style.flexWrap = "wrap";
  const cells: BattleRenderer[] = [];
  for (const ms of strip) cells.push(await cell(row, `${ms} ms`));
  await Promise.all(cells.map((r, i) => Promise.race([play(r, res, c, strip[i] as number), wait(((strip[i] as number) + 3000) * slow)])));
  await wait(200);
  for (const r of cells) (r as unknown as { app: Application }).app.render();
} else {
  (await cell(row, "動作前")).draw(buildDrawModel(before, HERO));
  const mid = await cell(row, `演出中（第 ${freeze} ms 停格）`);
  const done = play(mid, res, c, freeze);
  (await cell(row, "結算後")).draw(buildDrawModel(after, HERO));
  await Promise.race([done, wait((freeze + 1500) * slow)]);
  const app = (mid as unknown as { app: Application }).app;
  app.render();
}
document.body.dataset.ready = "1";
