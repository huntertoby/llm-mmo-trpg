// 開發用：SK-3 的新觸發「你造的關鍵字被利用時」與重擲反應的戰鬥演出。開 `client/dev/sk3-gallery.html`
// （pnpm dev 後 /dev/sk3-gallery.html）；不屬於正式 build。
// 事件是真引擎跑出來的（`dev/fixtures/sk3Events.json`，產生方式見 docs/phases/PhaseSK-3報告.md），走正式的
// playbackPlan → frameOps → BattleRenderer；畫面資料照產生事件的測試戰場手抄（寫法同 sk2Gallery）。
//   ?case=exploit|reroll_worse|reroll_better（預設 exploit）
//   &freeze=<毫秒>  中間那格停在演出開始後第幾毫秒
//   &scale=<倍率>   畫面縮放（預設 1.2）
// 每列三格：動作前、演出中（停格，浮字看得到）、結算後。畫好後 `document.body.dataset.ready = "1"`。
import type { Application } from "pixi.js";
import type { BattleResponse, BattleView, Glossary, SkillCard, StatusView, StepOut, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import fixture from "./fixtures/sk3Events.json";
import { buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { frameOps, playbackPlan } from "../battle/playback";
import { tile, unit } from "../battle/testFixtures";
import { attackFamilyInView, creatureStrikeInView, weaponClassInView } from "../battle/viewGrip";
import { BattleRenderer } from "../render/BattleRenderer";
import { waitForFonts } from "../render/fontLoad";

setGlossary(glossary as unknown as Glossary);
await waitForFonts();

const HERO = "unit_0001";
const W = 9;
const H = 7;
const params = new URLSearchParams(location.search);
const caseId = params.get("case") ?? "exploit";
const scale = Number(params.get("scale") ?? "1.2");

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
      } else if (op.op === "view") r.draw(buildDrawModel(op.view, HERO));
      else if (op.op === "pause") await wait(op.ms);
    }
}

const c = CASES[caseId] ?? CASES.exploit!;
const data = DATA[caseId in CASES ? caseId : "exploit"]!;
const freeze = Number(params.get("freeze") ?? String(c.freeze));
document.body.appendChild(Object.assign(document.createElement("h2"), { textContent: c.title }));
document.body.appendChild(Object.assign(document.createElement("p"), { className: "log", textContent: data.log.join("\n") }));
const row = document.createElement("div");
row.className = "row";
document.body.appendChild(row);
const before = view(c.before, c.surfaces ?? {}, c.actor);
const after = view(afterUnits(c, data), c.surfaces ?? {}, c.actor);
(await cell(row, "動作前")).draw(buildDrawModel(before, HERO));
const mid = await cell(row, `演出中（第 ${freeze} ms 停格）`);
const step = { actor_id: c.actor, events: data.events, view: after, step: { ...c.step, unit_id: c.actor } } as unknown as StepOut;
const res = { steps: [step], initial_view: before, view: after } as unknown as BattleResponse;
const done = play(mid, res, c, freeze);
(await cell(row, "結算後")).draw(buildDrawModel(after, HERO));
await Promise.race([done, wait(freeze + 1500)]);
const app = (mid as unknown as { app: Application }).app;
app.render();
document.body.dataset.ready = "1";
