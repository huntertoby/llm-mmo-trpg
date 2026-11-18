// 開發用：SK-2 新原語的戰鬥演出（吸收表面、疾病擴散、鉤、推不動算撞擊）。開 `client/dev/sk2-gallery.html`
// （pnpm dev 後 /dev/sk2-gallery.html）；不屬於正式 build。
// 事件是真引擎跑出來的（`dev/fixtures/sk2Events.json`，產生方式見 docs/phases/PhaseSK-2報告.md），走正式的
// playbackPlan → frameOps → BattleRenderer；畫面資料（地圖、單位）照產生事件的測試戰場手抄。
//   ?case=absorb|contagion|hook|hook_lava|hook_giant（預設 absorb）
//   &freeze=<毫秒>  中間那格停在演出開始後第幾毫秒（預設照各案例）
//   &scale=<倍率>   畫面縮放（預設 1.2）
//   &strip=<毫秒,…> AR-SK2：只畫「演出中」一排關鍵影格（每格停在演出開始後第幾毫秒），不畫施放前、結算後
//   &w=1600|800     AR-SK2：畫面縮放照遊戲的地圖縮放（1600 寬 1.31、800 寬 0.53；真 1 倍看鎖鏈的畫面下限）
// 每列三格：施放前、演出中（停格，浮字看得到）、結算後。畫好後 `document.body.dataset.ready = "1"`。
import type { Application } from "pixi.js";
import type { BattleResponse, BattleView, Glossary, SkillCard, StatusView, StepOut, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import fixture from "./fixtures/sk2Events.json";
import looks from "./fixtures/moltenHeartUnits.json";
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
const caseId = params.get("case") ?? "absorb";
const WIDTH_SCALE: Readonly<Record<string, number>> = { "1600": 1.31, "800": 0.53 };
const scale = WIDTH_SCALE[params.get("w") ?? ""] ?? Number(params.get("scale") ?? "1.2");
const strip = (params.get("strip") ?? "").split(",").filter((x) => x !== "").map(Number);

type FixtureUnit = { pos: [number, number]; hp: number; downed: boolean; statuses: { status_id: string; remaining: number | null }[] };
type FixtureCase = { events: Record<string, unknown>[]; units: Record<string, FixtureUnit>; log: string[] };
const DATA = fixture as unknown as Record<string, FixtureCase>;

interface Case {
  title: string;
  skill: string;
  card: SkillCard;
  freeze: number;
  /** 施放前的單位（位置、HP、狀態）；結算後的照 fixture。 */
  before: UnitView[];
  surfaces?: Record<string, string>;
  lava?: string[];
}

const status = (id: string, remaining: number | null): StatusView => ({ status_id: id, remaining, source_id: HERO, amount: null, charge_tiles: [], cost_status: false }) as StatusView;
const hero = (): UnitView => unit(HERO, "ally", 1, 3, { template_id: "hero_mage", name_zh: "法師", weapon_id: "fire_staff", hp: 40, max_hp: 40, facing: "east" });
const foe = (id: string, name: string, x: number, y: number, hp = 40, statuses: StatusView[] = []): UnitView =>
  unit(id, "enemy", x, y, { template_id: "bandit", name_zh: name, hp, max_hp: 40, facing: "west", statuses });

function card(skill: string, shape: string, range: number, effects: string[]): SkillCard {
  return { id: skill, shape: "單體", skeleton: "strike", effect_ids: effects, icon: { segments: [{ skeleton: "strike", shape_id: shape, range, effects: effects.map((type) => ({ type })) }] } } as unknown as SkillCard;
}

const giant = (): UnitView => ({ ...(looks.ashen_heart as unknown as UnitView), id: "unit_0002", pos: { x: 5, y: 3 }, facing: "west" });

const CASES: Readonly<Record<string, Case>> = {
  absorb: {
    title: "吸收表面（gain: element）：吸走腳下的冰，這一招的火焰傷害改成冰霜",
    skill: "skill_sk2_absorb",
    card: card("skill_sk2_absorb", "single", 5, ["absorb_surface", "damage"]),
    freeze: 700,
    before: [hero(), foe("unit_0002", "盜賊", 5, 3)],
    surfaces: { "1,3": "ice" },
  },
  contagion: {
    title: "疾病擴散：帶著會擴散的燃燒的盜賊1倒下，燃燒以剩餘 2 回合傳給相鄰的盜賊2",
    skill: "skill_sk2_fire",
    card: card("skill_sk2_fire", "single", 5, ["damage"]),
    freeze: 900,
    before: [hero(), foe("unit_0002", "盜賊1", 5, 3, 1, [status("burning", 2)]), foe("unit_0003", "盜賊2", 5, 4)],
  },
  hook: {
    title: "鉤：直線 5 格，鉤住第一個敵人（盜賊1）拉 3 格到身邊，後面的盜賊2不受影響",
    skill: "skill_sk2_hook",
    card: card("skill_sk2_hook", "line", 5, ["hook"]),
    freeze: 650,
    before: [hero(), foe("unit_0002", "盜賊1", 5, 3), foe("unit_0003", "盜賊2", 6, 3)],
  },
  hook_lava: {
    title: "鉤：中間有岩漿 (3, 3)，拉到岩漿前一格停下，不拉進致命地形",
    skill: "skill_sk2_hook",
    card: card("skill_sk2_hook", "line", 5, ["hook"]),
    freeze: 650,
    before: [hero(), foe("unit_0002", "盜賊", 5, 3)],
    lava: ["3,3"],
  },
  hook_giant: {
    title: "鉤打到巨型頭目：拉不動，照撞牆算一次撞擊（推不動算撞擊，6.38 第 9 點）",
    skill: "skill_sk2_hook",
    card: card("skill_sk2_hook", "line", 5, ["hook"]),
    freeze: 700,
    before: [hero(), giant()],
  },
};

function tiles(c: Case, surfaces: Record<string, string>): TileView[] {
  const out: TileView[] = [];
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++) {
      const key = `${x},${y}`;
      out.push(tile(x, y, { terrain: c.lava?.includes(key) ? "lava" : (x + y) % 7 === 0 ? "dirt" : "stone", surface: (surfaces[key] ?? "none") as TileView["surface"] }));
    }
  return out;
}

function view(c: Case, units: UnitView[], surfaces: Record<string, string>): BattleView {
  return {
    team: "ally", map_id: "sk2_gallery", map_name_zh: "SK-2", width: W, height: H, tiles: tiles(c, surfaces), objects: [], units, traps: [],
    turn_order: [HERO], active_unit: HERO, round: 1, max_rounds: 30, weather_id: null, weather_name_zh: null,
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
  const plan = playbackPlan(res, HERO, "normal", { [c.skill]: c.card }, new Set(), weaponClassInView, attackFamilyInView, creatureStrikeInView, false);
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
  // AR-SK2：操作播完時效果可能還在播（擴散接在倒下之後）：等到停格那一刻（最多 4 秒）
  for (let i = 0; i < 80 && !frozen; i++) await wait(50);
}

const c = CASES[caseId] ?? CASES.absorb!;
const data = DATA[caseId in CASES ? caseId : "absorb"]!;
const freeze = Number(params.get("freeze") ?? String(c.freeze));
document.body.appendChild(Object.assign(document.createElement("h2"), { textContent: c.title }));
document.body.appendChild(Object.assign(document.createElement("p"), { className: "log", textContent: data.log.join("\n") }));
const row = document.createElement("div");
row.className = "row";
document.body.appendChild(row);
const before = view(c, c.before, c.surfaces ?? {});
const consumed = Object.fromEntries(Object.entries(c.surfaces ?? {}).filter(([k]) => !data.events.some((e) => e.type === "surface_changed" && `${(e.pos as { x: number }).x},${(e.pos as { y: number }).y}` === k)));
const after = view(c, afterUnits(c, data), consumed);
const step = { actor_id: HERO, events: data.events, view: after, step: { type: "use_skill" } } as unknown as StepOut;
const res = { steps: [step], initial_view: before, view: after } as unknown as BattleResponse;
if (strip.length > 0) {
  // AR-SK2：關鍵影格一排（每格各自一個繪製器，停在第幾毫秒）
  row.style.flexWrap = "wrap";
  const cells: BattleRenderer[] = [];
  for (const ms of strip) cells.push(await cell(row, `${ms} ms`));
  await Promise.all(cells.map((r, i) => Promise.race([play(r, res, c, strip[i] as number), wait((strip[i] as number) + 6000)])));
  for (const r of cells) (r as unknown as { app: Application }).app.render();
} else {
  (await cell(row, "施放前")).draw(buildDrawModel(before, HERO));
  const mid = await cell(row, `演出中（第 ${freeze} ms 停格）`);
  const done = play(mid, res, c, freeze);
  (await cell(row, "結算後")).draw(buildDrawModel(after, HERO));
  await Promise.race([done, wait(freeze + 1500)]);
  const app = (mid as unknown as { app: Application }).app;
  app.render();
}
document.body.dataset.ready = "1";
