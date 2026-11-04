// 開發用：技能片段（Phase 6N-1／6N-2）。開 `client/skill-gallery.html`（pnpm dev 後 /skill-gallery.html）。不屬於正式 build。
// 全部走正式的串接器（battle/skillSequence.ts）與繪製器（BattleRenderer.playSkill／playVfx），只是事件是假的。
// `#openers`：13 種武器 × 一種施放方式（`?mode=melee|ranged|self|ground`，`?dir=west` 朝西），一直循環，火元素；
// `#prims`：6N-2 上半的原語片段（劍＋近身起手，接原語片段）；
// `#order`：樣張第 5 區的三組（砍＋跳、跳＋砍、衝刺＋砍）照卡上的順序播（走 playbackPlan → frameOps，同正式播放）；
// `#perf`：12×12 戰場 8 人輪流放技能 6 秒，和靜止 3 秒比 FPS、記下貼圖數。
// `?anim=0.1` 慢動作（playback.ts 的 devAnimFactor）；`?cell=88` 放大格子。
import type { BattleResponse, BattleView, Glossary, Pos, SkillCard, StepOut, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { frameOps, playbackPlan, SPEED_SCALE } from "../battle/playback";
import { scaleRows, skillTimeline } from "../battle/skillSequence";
import { tile, unit } from "../battle/testFixtures";
import { scaleVfx, vfxFor, VFX_TIMING, type VfxCards } from "../battle/vfx";
import { BattleRenderer } from "../render/BattleRenderer";
import { CAST_MODES, type CastMode } from "../render/skillClips";

setGlossary(glossary as unknown as Glossary);

const params = new URLSearchParams(location.search);
const MODE = decodeURIComponent(location.hash.slice(1)) || "openers";
const CAST: CastMode = (CAST_MODES as readonly string[]).includes(params.get("mode") ?? "") ? (params.get("mode") as CastMode) : "ranged";
const WEST = params.get("dir") === "west";
const CELL = Number(params.get("cell") ?? "52") || 52;
const SCALE = SPEED_SCALE.normal;
const HERO = "u_00";

declare global {
  interface Window {
    __skillStart?: number;
    __skillDone?: boolean;
  }
}

/** 13 種武器（起手對照表的列）的代表武器 ID。 */
const WEAPONS: ReadonlyArray<[string, string]> = [
  ["劍", "one_handed_sword"],
  ["魔導劍", "arcane_blade"],
  ["成對", "dual_dagger"],
  ["槍", "spear"],
  ["鐮", "scythe"],
  ["鞭", "whip"],
  ["拳套", "fist"],
  ["法杖", "fire_staff"],
  ["法球", "__orb"],
  ["弓", "bow"],
  ["弩", "crossbow"],
  ["火槍", "longgun"],
  ["空手", "__bare"],
];

function grid(w: number, h: number): TileView[] {
  const tiles: TileView[] = [];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) tiles.push(tile(x, y, { height: 0, terrain: (x + y) % 7 === 0 ? "dirt" : "stone" } as Partial<TileView>));
  return tiles;
}

function battle(units: UnitView[], w: number, h: number): BattleView {
  return {
    team: "ally", map_id: "skill_gallery", map_name_zh: "技能片段", width: w, height: h, tiles: grid(w, h), objects: [], units, traps: [],
    turn_order: [HERO], active_unit: HERO, round: 1, max_rounds: 30, weather_id: null, weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null,
    source_wells: [], zones: [], runes: [],
  } as unknown as BattleView;
}

function hero(id: string, x: number, y: number, weaponId: string, facing: "east" | "west"): UnitView {
  // 正式資料裡主手一定有武器（沒有時畫劍）：空手列用表上沒有的符紙代表，法球列＝符紙＋副手法球
  const extra: Partial<UnitView> =
    weaponId === "__orb"
      ? ({ template_id: "hero_mage", doll_look: { main_kind: "talisman", gear: { off_hand: { kind: "orb", material: "crystal" } } } } as unknown as Partial<UnitView>)
      : weaponId === "__bare"
        ? ({ template_id: "hero_fighter", doll_look: { main_kind: "talisman" } } as unknown as Partial<UnitView>)
        : { template_id: "hero_fighter", weapon_id: weaponId };
  return unit(id, "ally", x, y, { name_zh: id, facing, ...extra });
}

function card(shapeId: string, range: number, effects: string[], extra: Record<string, unknown> = {}): SkillCard {
  return { id: "sk", shape: "單體", skeleton: "strike", effect_ids: effects, icon: { segments: [{ skeleton: "strike", shape_id: shapeId, range, effects: effects.map((type) => ({ type })) }] }, ...extra } as unknown as SkillCard;
}

const MODE_CARD: Readonly<Record<CastMode, [string, number]>> = { melee: ["single", 1], ranged: ["single", 6], self: ["self", 0], ground: ["ground_tile", 5] };

async function show(v: BattleView): Promise<BattleRenderer> {
  const box = document.createElement("div");
  box.className = "scene";
  document.body.appendChild(box);
  const r = new BattleRenderer();
  await r.init(box);
  r.setScale(CELL / 48);
  r.setIdle(false);
  (window as unknown as { __r: BattleRenderer }).__r = r; // 主控台除錯用
  r.draw(buildDrawModel(v, HERO));
  return r;
}

/**
 * 動畫開始：記下時間；`?freeze=毫秒` 時，第一輪開始後那麼久把畫布時間停住（截圖用）。
 * 停的方法是把 ticker 速度降到幾乎 0（`setBoost`），畫面停在那一格。
 */
function started(r: BattleRenderer): void {
  if (window.__skillStart !== undefined) return;
  window.__skillStart = performance.now();
  const freeze = Number(params.get("freeze") ?? "");
  if (!Number.isFinite(freeze) || freeze <= 0) return;
  // 用畫布自己的時鐘（第一幀卡頓時 ticker 會限制每幀的時間，牆上時間不準）
  const clock = () => (r as unknown as { effectClock: number }).effectClock;
  const t0 = clock();
  const check = () => {
    if (clock() - t0 >= freeze) r.setBoost(1e-6);
    else requestAnimationFrame(check);
  };
  requestAnimationFrame(check);
}

function caption(text: string): void {
  const h = document.createElement("h2");
  h.textContent = text;
  document.body.prepend(h);
}

function labels(items: ReadonlyArray<[string, Pos]>): void {
  const box = document.querySelector(".scene") as HTMLElement;
  box.style.position = "relative";
  for (const [text, p] of items) {
    const d = document.createElement("div");
    d.textContent = text;
    d.style.cssText = `position:absolute;left:${p.x * CELL + 2}px;top:${p.y * CELL + 1}px;font:11px sans-serif;color:#ffe9a8;text-shadow:0 0 2px #000;pointer-events:none`;
    box.appendChild(d);
  }
}

const wait = (ms: number) => new Promise<void>((r) => window.setTimeout(r, ms));

/** 一個施放者放一次（直接走串接器＋繪製器）；回傳這一招的長度。 */
function castOnce(r: BattleRenderer, v: BattleView, caster: string, target: Pos, cards: VfxCards, more: Record<string, unknown>[] = [], hurt = true): number {
  const from = v.units.find((u) => u.id === caster)!.pos;
  const tiles = cards["sk"]?.icon?.segments[0]?.shape_id === "self" ? [from] : [target];
  const tgt = v.units.find((u) => u.pos.x === target.x && u.pos.y === target.y && u.id !== caster);
  const events: Record<string, unknown>[] = [
    { seq: 1, round: 1, type: "skill_used", unit_id: caster, skill_id: "sk", tiles },
    ...(tgt === undefined || !hurt ? [] : [{ seq: 2, round: 1, type: "damage_dealt", target_id: tgt.id, source_id: caster, element: "fire", amount: 5 }]),
    ...more,
  ];
  const raw = vfxFor(events, v, cards);
  const tl = skillTimeline(events, v, cards, raw, (id) => r.weaponClassOf(id));
  if (tl === null) return 0;
  const vfx = scaleVfx(tl.vfx, SCALE);
  const origins = r.playSkill(scaleRows(tl.rows, SCALE));
  r.playVfx(vfx, Math.round(VFX_TIMING.impact * SCALE), false, origins);
  const end = Math.max(...scaleRows(tl.rows, SCALE).map((x) => x.startMs + x.ms), vfx.leadMs);
  return end + Math.round(VFX_TIMING.impact * SCALE);
}

async function openers(): Promise<void> {
  const facing = WEST ? "west" : "east";
  const units: UnitView[] = [];
  const tags: Array<[string, Pos]> = [];
  WEAPONS.forEach(([name, id], i) => {
    const col = i < 7 ? 0 : 1;
    const y = (i % 7) * 2;
    const x = WEST ? 11 - col * 6 : 1 + col * 6;
    units.push(hero(`u_${String(i).padStart(2, "0")}`, x, y, id, facing));
    units.push(unit(`t_${i}`, "enemy", WEST ? x - 3 : x + 3, y, { template_id: "t", name_zh: "木樁", facing: WEST ? "east" : "west" }));
    tags.push([name, { x: x - (WEST ? 0 : 1) + (WEST ? 0.1 : 0.1), y }]);
  });
  const v = battle(units, 12, 14);
  const r = await show(v);
  labels(tags);
  caption(`6N-1・起手對照表：13 種武器 × ${CAST}（${facing}）；火元素`);
  const [shape, range] = MODE_CARD[CAST];
  const cards = { sk: card(shape, range, ["damage"]) };
  started(r);
  for (;;) {
    let longest = 0;
    WEAPONS.forEach((_, i) => {
      const caster = `u_${String(i).padStart(2, "0")}`;
      const t = v.units.find((u) => u.id === `t_${i}`)!.pos;
      const target = CAST === "self" ? v.units.find((u) => u.id === caster)!.pos : CAST === "melee" ? { x: t.x + (WEST ? 2 : -2), y: t.y } : t;
      longest = Math.max(longest, castOnce(r, v, caster, target, cards));
    });
    await wait(longest + 400);
    window.__skillDone = true;
  }
}

/** 6N-2 上半的原語（方案 2.3 (1) 的表順序）。 */
const PRIMS: ReadonlyArray<[string, string[]]> = [
  ["damage", ["damage"]],
  ["damage_multiplier", ["damage_multiplier", "damage"]],
  ["delayed_damage", ["delayed_damage"]],
  ["heal", ["heal"]],
  ["shield", ["shield"]],
  ["cleanse", ["cleanse"]],
  ["revive", ["revive"]],
  ["restore_resource", ["restore_resource"]],
  ["apply_status 增益", ["apply_status"]],
  ["apply_status 減益", ["apply_status"]],
  ["dispel", ["dispel"]],
  ["steal_buff", ["steal_buff"]],
  ["teleport_target", ["teleport_target"]],
  ["push", ["push"]],
  ["pull", ["pull"]],
  ["knock_prone", ["damage", "knock_prone"]],
  ["shockwave", ["shockwave"]],
];

async function prims(): Promise<void> {
  const units: UnitView[] = [];
  const tags: Array<[string, Pos]> = [];
  PRIMS.forEach(([name], i) => {
    const col = i % 3;
    const y = Math.floor(i / 3) * 2;
    const x = col * 4;
    units.push(hero(`u_${String(i).padStart(2, "0")}`, x, y, "one_handed_sword", "east"));
    units.push(unit(`t_${i}`, name.includes("增益") ? "ally" : "enemy", x + 1, y, { template_id: "t", name_zh: "木樁", facing: "west" }));
    tags.push([name, { x, y: y + 1 }]);
  });
  const v = battle(units, 12, 12);
  const r = await show(v);
  labels(tags);
  caption("6N-2・原語片段（上）：劍＋近身起手，接原語片段（位移類見 #order）");
  started(r);
  for (;;) {
    let longest = 0;
    PRIMS.forEach(([name, effects], i) => {
      const caster = `u_${String(i).padStart(2, "0")}`;
      const tgt = `t_${i}`;
      const pos = v.units.find((u) => u.id === tgt)!.pos;
      const more: Record<string, unknown>[] = [];
      if (name.startsWith("apply_status")) more.push({ seq: 3, round: 1, type: "status_applied", target_id: tgt, source_id: caster, status_id: "haste" });
      if (name === "knock_prone") more.push({ seq: 3, round: 1, type: "status_applied", target_id: tgt, source_id: caster, status_id: "prone" });
      longest = Math.max(longest, castOnce(r, v, caster, pos, { sk: card("single", 1, effects) }, more, effects.includes("damage")));
    });
    await wait(longest + 600);
    r.draw(buildDrawModel(v, HERO)); // 倒地的木樁站回來
    window.__skillDone = true;
  }
}

/** 照正式流程播一個回應（playbackPlan → frameOps），只接畫布要的幾種。 */
async function playResponse(r: BattleRenderer, res: BattleResponse): Promise<void> {
  const plan = playbackPlan(res, HERO, "normal", { sk: res.steps[0] ? cardOf(res) : undefined } as VfxCards, new Set(), (id) => r.weaponClassOf(id));
  r.draw(buildDrawModel(plan.initialView, HERO));
  for (const frame of plan.frames) {
    for (const op of frameOps(frame)) {
      if (op.op === "move") await r.animate([op.anim], () => false);
      else if (op.op === "vfx") {
        const origins = op.skill === undefined ? undefined : r.playSkill(op.skill);
        r.playVfx(op.vfx, op.impactMs, false, origins);
        await wait(op.vfx.leadMs);
      } else if (op.op === "view") r.draw(buildDrawModel(op.view, HERO));
      else if (op.op === "pause") await wait(op.ms);
    }
  }
}

let ORDER_CARD: SkillCard = card("single", 1, ["damage"]);
const cardOf = (_: BattleResponse) => ORDER_CARD;

async function order(): Promise<void> {
  const rowsY = [1, 5, 9];
  const names = ["砍＋跳", "跳＋砍", "衝刺＋砍"];
  const start = (i: number): Pos => ({ x: 2, y: rowsY[i]! });
  const foe = (i: number): Pos => ({ x: i === 0 ? 3 : 6, y: rowsY[i]! });
  const base = () =>
    battle(
      rowsY.flatMap((y, i) => [hero(`u_0${i}`, start(i).x, y, "one_handed_sword", "east"), unit(`t_${i}`, "enemy", foe(i).x, y, { template_id: "t", name_zh: "木樁", facing: "west" })]),
      12,
      12,
    );
  const r = await show(base());
  labels(names.map((n, i) => [n, { x: 0, y: rowsY[i]! }]));
  caption("6N-1・照卡上的順序：砍＋跳（砍完往後跳開）、跳＋砍（跳到身前再砍）、衝刺＋砍");
  started(r);
  for (;;) {
    const only = params.get("only"); // `?only=0|1|2`：只播其中一組（截圖用）
    for (let i = 0; i < 3; i++) {
      if (only !== null && String(i) !== only) continue;
      const v0 = base();
      const id = `u_0${i}`;
      const moveTo = i === 0 ? { x: 0, y: rowsY[i]! } : { x: 5, y: rowsY[i]! };
      const v1 = { ...v0, units: v0.units.map((u) => (u.id === id ? { ...u, pos: moveTo } : u)) } as BattleView;
      ORDER_CARD = card("single", 1, i === 0 ? ["damage", "leap"] : i === 1 ? ["leap", "damage"] : ["dash", "damage"]);
      const mode = i === 2 ? "dash" : "leap";
      const steps = i === 2 ? [{ x: 3, y: rowsY[i]! }, { x: 4, y: rowsY[i]! }, moveTo] : [moveTo];
      let prev = start(i);
      const moves = steps.map((p, k) => {
        const e = { seq: 10 + k, round: 1, type: "unit_moved", unit_id: id, from_pos: prev, to_pos: p, mode };
        prev = p;
        return e;
      });
      const events = [
        { seq: 1, round: 1, type: "skill_used", unit_id: id, skill_id: "sk", tiles: [foe(i)] },
        ...(i === 0 ? [] : moves),
        { seq: 2, round: 1, type: "damage_dealt", target_id: `t_${i}`, source_id: id, element: "physical", amount: 5 },
        ...(i === 0 ? moves : []),
      ];
      const step = { actor_id: id, events, view: v1, step: { type: "skill" } } as unknown as StepOut;
      await playResponse(r, { steps: [step], initial_view: v0, view: v1 } as unknown as BattleResponse);
      await wait(500);
    }
    window.__skillDone = true;
  }
}

async function perf(): Promise<void> {
  const ids = ["one_handed_sword", "fire_staff", "bow", "longgun", "spear", "arcane_blade", "whip", "fist"];
  const units: UnitView[] = [];
  ids.forEach((w, i) => {
    const y = 1 + (i % 4) * 3;
    const x = i < 4 ? 1 : 6;
    units.push(hero(`u_0${i}`, x, y, w, "east"));
    units.push(unit(`t_${i}`, "enemy", x + 4, y, { template_id: "t", name_zh: "木樁", facing: "west" }));
  });
  const v = battle(units, 12, 12);
  const r = await show(v);
  caption("6N-1・12×12 戰場 FPS（靜止 3 秒 vs. 8 人輪流放技能 6 秒）");
  const out = document.createElement("div");
  out.id = "perf";
  document.body.appendChild(out);
  const count = (ms: number) =>
    new Promise<{ fps: number; p95Ms: number; over50: number }>((resolve) => {
      const gaps: number[] = [];
      let last = performance.now();
      const t0 = last;
      const tick = (now: number) => {
        gaps.push(now - last);
        last = now;
        if (now - t0 < ms) {
          requestAnimationFrame(tick);
          return;
        }
        const sorted = [...gaps].sort((x, y) => x - y);
        resolve({ fps: Number(((gaps.length * 1000) / (now - t0)).toFixed(1)), p95Ms: Number((sorted[Math.floor(sorted.length * 0.95)] ?? 0).toFixed(1)), over50: gaps.filter((g) => g > 50).length });
      };
      requestAnimationFrame(tick);
    });
  await count(1000);
  const idle = await count(3000);
  const t0 = r.textureCount();
  let on = true;
  const loop = async (i: number) => {
    const cards = { sk: card("single", i % 2 === 0 ? 1 : 4, ["damage"]) };
    while (on) {
      const t = v.units.find((u) => u.id === `t_${i}`)!.pos;
      const target = i % 2 === 0 ? { x: t.x - 3, y: t.y } : t;
      await wait(castOnce(r, v, `u_0${i}`, target, cards) + 100);
    }
  };
  ids.forEach((_, i) => void wait(i * 150).then(() => loop(i)));
  const casting = await count(6000);
  on = false;
  out.textContent = JSON.stringify({ grid: "12x12", cell: CELL, dpr: window.devicePixelRatio, idle, casting8: casting, textures: { before: t0, after: r.textureCount() } });
  window.__skillDone = true;
}

const MODES: Readonly<Record<string, () => Promise<void>>> = { openers, prims, order, perf };
void (MODES[MODE] ?? openers)();
