// 開發用：技能片段（Phase 6N-1／6N-2／6N-3）。開 `client/skill-gallery.html`（pnpm dev 後 /skill-gallery.html）。不屬於正式 build。
// 全部走正式的串接器（battle/skillSequence.ts）與繪製器（BattleRenderer.playSkill／playVfx），只是事件是假的。
// `#openers`：13 種武器 × 一種施放方式（`?mode=melee|ranged|self|ground`，`?dir=west` 朝西），一直循環，火元素；
// `#prims`：6N-2 上半的原語片段（劍＋近身起手，接原語片段）；
// `#lower`：6N-3 下半的原語片段（`?group=world` 召喚、地表、地形、物件、符文；`?group=rules` 形態、防護、給予、退還、層數、規則類，含兩組多原語）；
// `#order`：樣張第 5 區的三組（砍＋跳、跳＋砍、衝刺＋砍）照卡上的順序播（走 playbackPlan → frameOps，同正式播放）；
// `#moves`：位移類原語（衝刺、跳躍、傳送、瞬步、交換）與被推、被拉；
// `#perf`：12×12 戰場 8 人輪流放技能 6 秒，和靜止 3 秒比 FPS、記下貼圖數（`?react=1`：6N-4 目標輪流受擊、格擋、閃避）；
// `#react`：6N-4 受擊與結果（受擊、重擊、閃避、格擋三種、倒下、異形）＋陷阱夾住、冰面滑倒；
// `#variants`：6N-6 近戰攻擊變體（每種武器的全部變體＋連續 8 次普攻挑到的變體；`?crit=1` 暴擊）；
// `#result`：6N-5 特殊結果（暴擊、擊殺、格擋成功、閃避成功、Boss 大招；停頓）＋復活、勝利。
// `?anim=0.1` 慢動作（playback.ts 的 devAnimFactor）；`?cell=88` 放大格子。
import type { BattleResponse, BattleView, Glossary, MoveMode, Pos, SkillCard, StepOut, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { FEEDBACK_MS, frameOps, playbackPlan, SPEED_SCALE } from "../battle/playback";
import { feedbackFor } from "../battle/feedback";
import { newSpecialMemo, stopHoldMs, victoryOf, VICTORY_HOLD_MS, VICTORY_MS, withSpecials } from "../battle/specials";
import { scaleRows, skillTimeline, variantFor } from "../battle/skillSequence";
import { tile, unit } from "../battle/testFixtures";
import { scaleVfx, vfxFor, VFX_TIMING, type VfxCards } from "../battle/vfx";
import { BattleRenderer } from "../render/BattleRenderer";
import { ATTACK_FAMILIES, ATTACK_VARIANTS, FAMILY_ZH, type AttackFamily } from "../render/attackVariants";
import { CAST_MODES, type CastMode, type PrimitiveClipId } from "../render/skillClips";
import { moveAnimOf } from "../battle/animation";

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
    if (clock() - t0 >= freeze) {
      r.setBoost(1e-6);
      frozen = true; // 停格後不再放下一輪（不然新的一輪會從頭蓋掉停住的姿勢）
    } else requestAnimationFrame(check);
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

/** `?freeze=` 停格後為真：不再放新的一輪、不重畫場景。 */
let frozen = false;

/** 一個施放者放一次（直接走串接器＋繪製器）；回傳這一招的長度。 */
function castOnce(r: BattleRenderer, v: BattleView, caster: string, target: Pos, cards: VfxCards, more: Record<string, unknown>[] = [], hurt = true): number {
  if (frozen) return 0;
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
  lastLead = vfx.leadMs;
  return end + Math.round(VFX_TIMING.impact * SCALE);
}

/** 上一次 `castOnce` 的命中點（毫秒；正式播放在這一刻以結果重畫）。 */
let lastLead = 0;

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
    if (!frozen) r.draw(buildDrawModel(v, HERO)); // 倒地的木樁站回來
    window.__skillDone = true;
  }
}

/**
 * 6N-3 下半的原語（方案 2.3 (1) 的表順序）。`world`：召喚、地表地形、物件符文；`rules`：形態、防護、給予、退還、層數、規則類。
 * 每格：名稱、原語（卡上順序）、目標陣營。
 */
const PRIMS_LOWER: Readonly<Record<string, ReadonlyArray<[string, string[], "ally" | "enemy"]>>> = {
  world: [
    ["summon", ["summon"], "enemy"],
    ["sacrifice_summon", ["sacrifice_summon"], "ally"],
    ["create_surface", ["create_surface"], "enemy"],
    ["zone", ["zone"], "enemy"],
    ["blow_surface", ["blow_surface"], "enemy"],
    ["clear_surface", ["clear_surface"], "enemy"],
    ["create_obstacle", ["create_obstacle"], "enemy"],
    ["raise_terrain", ["raise_terrain"], "enemy"],
    ["lower_terrain", ["lower_terrain"], "enemy"],
    ["topple", ["topple"], "enemy"],
    ["hurl_object", ["hurl_object"], "enemy"],
    ["place_trap", ["place_trap"], "enemy"],
    ["inscribe", ["inscribe"], "enemy"],
    ["detonate_runes", ["detonate_runes"], "enemy"],
    ["destroy_object", ["destroy_object"], "enemy"],
  ],
  rules: [
    ["enter_form", ["enter_form"], "enemy"],
    ["leave_form", ["leave_form"], "enemy"],
    ["intercept／redirect（共用）", ["intercept"], "ally"],
    ["cheat_death", ["cheat_death"], "enemy"],
    ["reveal", ["reveal"], "enemy"],
    ["copy_skill", ["copy_skill"], "enemy"],
    ["grant_skill（共用）", ["grant_skill"], "ally"],
    ["grant_ap（共用）", ["grant_ap"], "ally"],
    ["extra_reaction（共用）", ["extra_reaction"], "ally"],
    ["refund_ap（無動作）", ["damage", "refund_ap"], "enemy"],
    ["refund_cd／reset_cd（無動作）", ["damage", "reset_cooldown"], "enemy"],
    ["add_stack（無動作）", ["damage", "add_stack"], "enemy"],
    ["consume_*（無動作）", ["damage", "consume_stack"], "enemy"],
    ["gamble", ["gamble"], "enemy"],
    ["rule_change", ["rule_change"], "enemy"],
    ["self_damage_of_hit", ["damage", "self_damage_of_hit"], "enemy"],
    ["多原語：砍＋刻符＋引爆", ["damage", "inscribe", "detonate_runes"], "enemy"],
    ["多原語：召喚＋層數＋退還", ["summon", "add_stack", "refund_ap"], "enemy"],
  ],
};

async function primsLower(): Promise<void> {
  const group = params.get("group") === "rules" ? "rules" : "world";
  const list = PRIMS_LOWER[group]!;
  const units: UnitView[] = [];
  const tags: Array<[string, Pos]> = [];
  list.forEach(([name, , team], i) => {
    const col = i % 3;
    const y = Math.floor(i / 3) * 2;
    const x = col * 4;
    units.push(hero(`u_${String(i).padStart(2, "0")}`, x, y, "one_handed_sword", "east"));
    units.push(unit(`t_${i}`, team, x + 2, y, { template_id: "t", name_zh: "木樁", facing: "west" }));
    tags.push([name, { x, y: y + 1 }]);
  });
  const rows = Math.ceil(list.length / 3) * 2;
  const v = battle(units, 12, rows);
  const r = await show(v);
  labels(tags);
  caption(`6N-3・原語片段（下）：${group === "world" ? "召喚、地表、地形、物件、符文" : "形態、防護、給予、退還、層數、規則類"}（劍＋射程 2 起手，接原語片段）`);
  started(r);
  for (;;) {
    let longest = 0;
    list.forEach(([, effects], i) => {
      const caster = `u_${String(i).padStart(2, "0")}`;
      const pos = v.units.find((u) => u.id === `t_${i}`)!.pos;
      const more: Record<string, unknown>[] = [];
      if (effects.includes("self_damage_of_hit")) more.push({ seq: 4, round: 1, type: "damage_dealt", target_id: caster, source_id: caster, cause: "backlash", element: "physical", amount: 2 });
      longest = Math.max(longest, castOnce(r, v, caster, pos, { sk: card("single", 2, effects) }, more, effects.includes("damage")));
    });
    await wait(longest + 600);
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

/** `#perf?lower=1` 輪流接在砍後面的下半原語（6N-3）。 */
const LOWER_MIX: readonly string[] = PRIMS_LOWER.world!.concat(PRIMS_LOWER.rules!).flatMap(([, effects]) => effects.filter((e) => e !== "damage"));

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
  caption("6N-1／6N-3・12×12 戰場 FPS（靜止 3 秒 vs. 8 人輪流放技能；`?secs=` 秒數、`?lower=1` 接下半原語）");
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
  let peak = t0;
  const watch = window.setInterval(() => (peak = Math.max(peak, r.textureCount())), 100);
  const loop = async (i: number) => {
    let n = i;
    while (on) {
      // `?lower=1`（6N-3）：每次換一個下半原語接在砍後面（召喚、刻符、層數…），姿勢種類更多
      const lower = params.get("lower") === "1" ? [LOWER_MIX[n % LOWER_MIX.length]!] : [];
      n += 1;
      const cards = { sk: card("single", i % 2 === 0 ? 1 : 4, ["damage", ...lower]) };
      const t = v.units.find((u) => u.id === `t_${i}`)!.pos;
      const target = i % 2 === 0 ? { x: t.x - 3, y: t.y } : t;
      if (params.get("react") === "1") {
        // 6N-4：目標輪流閃避、格擋、重擊（受擊者的身體片段、殘影、火花）
        const caster = `u_0${i}`;
        const tgt = `t_${i}`;
        const k = n % 3;
        const more: Record<string, unknown>[] = [{ seq: 2, round: 1, type: "attack_rolled", attacker_id: caster, target_id: tgt, hit: k !== 0, skill_id: "sk" }];
        if (k !== 0) more.push({ seq: 3, round: 1, type: "damage_dealt", target_id: tgt, source_id: caster, element: "fire", amount: 8, hp_before: 20, hp_after: 12, block_permille: k === 1 ? 500 : 1000 });
        await wait(castOnce(r, v, caster, target, cards, more, false) + 100);
        continue;
      }
      await wait(castOnce(r, v, `u_0${i}`, target, cards) + 100);
    }
  };
  ids.forEach((_, i) => void wait(i * 150).then(() => loop(i)));
  const secs = Number(params.get("secs") ?? "6") || 6; // `?secs=` 放技能的秒數（6N-3 量 LRU 上限用）
  const casting = await count(secs * 1000);
  on = false;
  window.clearInterval(watch);
  out.textContent = JSON.stringify({ grid: "12x12", cell: CELL, dpr: window.devicePixelRatio, secs, lower: params.get("lower") === "1", idle, casting8: casting, textures: { before: t0, after: r.textureCount(), peak } });
  window.__skillDone = true;
}

/** 位移類原語的片段（6N-2）：衝刺、肩撞、跳躍、傳送、瞬步、交換，和目標片段被推、被拉。每格放慢到 3 倍好看清楚。 */
const MOVES: ReadonlyArray<[string, PrimitiveClipId, MoveMode, number]> = [
  ["dash", "dash_lean", "dash", 3],
  ["charge_through", "shoulder_charge", "dash", 3],
  ["leap", "leap_air", "leap", 2],
  ["teleport", "warp_pose", "teleport", 3],
  ["shadowstep", "smoke_step", "shadowstep", 3],
  ["swap / swap_any", "swap_pose", "swap", 3],
  ["被推（目標）", "pushed", "forced", 2],
  ["被拉（目標）", "pulled", "forced", 2],
];

async function moves(): Promise<void> {
  const units: UnitView[] = MOVES.map((_, i) => hero(`u_0${i}`, 2, 1 + Math.round(i * 1.4), "one_handed_sword", "east"));
  const v = battle(units, 12, 12);
  const r = await show(v);
  labels(MOVES.map(([n], i) => [n, { x: 0, y: units[i]!.pos.y + 1 }]));
  caption("6N-2・位移類原語的片段（每格放慢）；被推往後仰、被拉往前傾");
  started(r);
  for (;;) {
    await Promise.all(
      MOVES.map(async ([, clip, mode, tiles], i) => {
        const u = units[i]!;
        const back = clip === "pulled";
        const from = back ? { x: u.pos.x + tiles, y: u.pos.y } : u.pos;
        const to = back ? u.pos : { x: u.pos.x + tiles, y: u.pos.y };
        const base = moveAnimOf({ seq: 1, round: 1, type: "unit_moved", unit_id: u.id, from_pos: from, to_pos: to, mode } as never, SCALE * 3);
        await r.animate([{ ...base, clip }], () => false);
      }),
    );
    await wait(600);
    if (!frozen) r.draw(buildDrawModel(v, HERO));
    window.__skillDone = true;
  }
}

/**
 * 6N-4 受擊與結果：每列「劍士 → 目標」，事件照正式規則的欄位（`attack_rolled` 的 `hit`、`damage_dealt` 的扣血與
 * `block_permille`、`unit_downed`），走 vfxFor → skillTimeline → playSkill／playVfx，命中後照正式播放重畫成結果
 * （倒下的人變成倒地圖示）。名稱、目標外觀、事件。
 */
type ReactCase = { name: string; look?: Partial<UnitView>; hit: boolean; lost?: number; block?: number; down?: boolean };
const REACTS: readonly ReactCase[] = [
  { name: "受擊", hit: true, lost: 3 },
  { name: "重擊（≥25%）", hit: true, lost: 12 },
  { name: "閃避（hit: false）", hit: false },
  { name: "格擋・盾", hit: true, lost: 3, block: 500, look: { equipment: [{ slot: "off_hand", appearance: { kind: "round_shield", material: "wood" } }] } as unknown as Partial<UnitView> },
  { name: "格擋・橫劍", hit: true, lost: 3, block: 500 },
  { name: "格擋・手臂", hit: true, lost: 3, block: 500, look: { template_id: "hero_fighter", doll_look: { main_kind: "talisman" } } as unknown as Partial<UnitView> },
  { name: "倒下", hit: true, lost: 20, down: true },
  { name: "倒下（可復活）", hit: true, lost: 20, down: true, look: { revivable: true } as Partial<UnitView> },
  { name: "異形受擊", hit: true, lost: 3, look: { doll_look: { creature: { body: "hound", material: "fur" } } } as unknown as Partial<UnitView> },
  { name: "異形閃避（輕版）", hit: false, look: { doll_look: { creature: { body: "hound", material: "fur" } } } as unknown as Partial<UnitView> },
  { name: "異形倒下", hit: true, lost: 20, down: true, look: { doll_look: { creature: { body: "golem", material: "stone" } } } as unknown as Partial<UnitView> },
];

async function reacts(): Promise<void> {
  const units: UnitView[] = [];
  const tags: Array<[string, Pos]> = [];
  REACTS.forEach((c, i) => {
    const col = i % 3;
    const y = Math.floor(i / 3) * 2;
    const x = col * 4;
    units.push(hero(`u_${String(i).padStart(2, "0")}`, x, y, "one_handed_sword", "east"));
    units.push(unit(`t_${i}`, "enemy", x + 1, y, { template_id: "hero_fighter", weapon_id: "one_handed_sword", name_zh: "對手", facing: "west", hp: 20, max_hp: 20, ...(c.look ?? {}) }));
    tags.push([c.name, { x, y: y + 1 }]);
  });
  // 陷阱、滑倒（走路途中；animateWalk 的停頓）：最後一排
  const walkY = Math.ceil(REACTS.length / 3) * 2;
  units.push(hero("w_trap", 0, walkY, "one_handed_sword", "east"));
  units.push(hero("w_slip", 6, walkY, "one_handed_sword", "east"));
  tags.push(["陷阱夾住", { x: 0, y: walkY + 1 }], ["冰面滑倒（踉蹌→滑行→倒地）", { x: 6, y: walkY + 1 }]);
  const v = battle(units, 12, walkY + 2);
  const after = {
    ...v,
    units: v.units.map((u) => {
      const i = Number(u.id.slice(2));
      const c = u.id.startsWith("t_") ? REACTS[i] : undefined;
      return c?.down === true ? { ...u, hp: 0, downed: true, revivable: (c.look as { revivable?: boolean } | undefined)?.revivable === true } : u;
    }),
  } as BattleView;
  const r = await show(v);
  labels(tags);
  caption("6N-4・受擊與結果：受擊、重擊、閃避、格擋（盾／劍／手臂）、倒下（接倒地圖示）、異形；陷阱夾住、冰面滑倒");
  started(r);
  const cards = { sk: card("single", 1, ["damage"]) };
  for (;;) {
    if (frozen) return;
    r.draw(buildDrawModel(v, HERO));
    let longest = 0;
    let lead = 0;
    REACTS.forEach((c, i) => {
      const caster = `u_${String(i).padStart(2, "0")}`;
      const tgt = `t_${i}`;
      const pos = v.units.find((u) => u.id === tgt)!.pos;
      const more: Record<string, unknown>[] = [{ seq: 2, round: 1, type: "attack_rolled", attacker_id: caster, target_id: tgt, hit: c.hit, skill_id: "sk" }];
      if (c.hit) more.push({ seq: 3, round: 1, type: "damage_dealt", target_id: tgt, source_id: caster, element: "physical", amount: c.lost, hp_before: 20, hp_after: 20 - (c.lost ?? 0), block_permille: c.block ?? 1000 });
      if (c.down === true) more.push({ seq: 4, round: 1, type: "unit_downed", unit_id: tgt });
      longest = Math.max(longest, castOnce(r, v, caster, pos, cards, more, false));
      lead = Math.max(lead, lastLead);
    });
    // 正式播放：命中那一刻以結果重畫（倒下的人變成倒地圖示；倒下片段接在上面播完）
    await wait(lead);
    if (!frozen) r.draw(buildDrawModel(after, HERO));
    void walkBeats(r); // 重畫之後才走（重畫會把小人放回格子）
    await wait(longest + 900);
    window.__skillDone = true;
  }
}

/** 陷阱、冰面滑倒（6A-4d／6E-2 的停頓，6N-4 加上夾住的身體反應）：照 animateWalk 的時間軸。 */
async function walkBeats(r: BattleRenderer): Promise<void> {
  const leg = (y: number, x0: number, x1: number) => ({ kind: "leg" as const, from: { x: x0, y }, to: { x: x1, y }, facing: "east" as const, durationMs: 120 * SCALE });
  const beat = (kind: "trap" | "stumble" | "slip", x: number, y: number, hold: number, fx: number) => ({ kind: "beat" as const, beat: kind, pos: { x, y }, holdMs: hold * SCALE, fxMs: fx * SCALE, feedback: [], feedbackMs: 0 });
  const y = Math.ceil(REACTS.length / 3) * 2;
  await Promise.all([
    r.animateWalk({ unitId: "w_trap", pieces: [leg(y, 0, 1), leg(y, 1, 2), beat("trap", 2, y, 400, 600)] }, () => frozen),
    r.animateWalk({ unitId: "w_slip", pieces: [leg(y, 6, 7), beat("stumble", 7, y, 220, 450), { kind: "skid", from: { x: 7, y }, to: { x: 8, y }, facing: "east", durationMs: 70 * SCALE }, { kind: "skid", from: { x: 8, y }, to: { x: 9, y }, facing: "east", durationMs: 70 * SCALE }, beat("slip", 9, y, 450, 600)] }, () => frozen),
  ]);
}

/**
 * 6N-5 特殊結果（選項 B：特效加停頓）＋6N-4 補做的復活、勝利：每格「施放者 → 目標」，事件照正式規則的欄位，
 * 走 vfxFor → skillTimeline → withSpecials → playSkill／playVfx（停頓由繪製器的效果時鐘處理），
 * 命中（加停頓）後照正式播放重畫成結果、跳浮動字樣，最後全隊播勝利。
 */
type ResultCase = {
  name: string;
  /** 目標的外觀與狀態（開始前）。 */
  look?: Partial<UnitView>;
  /** 施放者的外觀與狀態（開始前；Boss 大招＝帶 boss 標籤、蓄力中）。 */
  caster?: Partial<UnitView>;
  events: (caster: string, target: string) => Record<string, unknown>[];
  /** 結束時目標的樣子。 */
  after?: Partial<UnitView>;
  /** 第一個事件換成 `skill_followup`（Boss 放出蓄力的那一招）。 */
  followup?: boolean;
};
const HOUND = { doll_look: { creature: { body: "hound", material: "fur" } } } as unknown as Partial<UnitView>;
const atk = (c: string, t: string, hit: boolean): Record<string, unknown> => ({ seq: 2, round: 1, type: "attack_rolled", attacker_id: c, target_id: t, hit, skill_id: "sk" });
const dmgEv = (c: string, t: string, lost: number, more: Record<string, unknown> = {}): Record<string, unknown> => ({ seq: 3, round: 1, type: "damage_dealt", target_id: t, source_id: c, element: "physical", amount: lost, hp_before: 20, hp_after: 20 - lost, crit: false, block_permille: 1000, ...more });
const RESULTS: readonly ResultCase[] = [
  { name: "暴擊（停 0.1 秒、閃白、金弧）", events: (c, t) => [atk(c, t, true), dmgEv(c, t, 9, { crit: true })] },
  { name: "擊殺（停頓＋震動）", events: (c, t) => [atk(c, t, true), dmgEv(c, t, 20), { seq: 4, round: 1, type: "unit_downed", unit_id: t }], after: { hp: 0, downed: true } },
  { name: "格擋成功（停 0.06、大火花、彈開）", events: (c, t) => [atk(c, t, true), dmgEv(c, t, 3, { block_permille: 500 })] },
  { name: "閃避成功（殘影兩層）", events: (c, t) => [atk(c, t, false)] },
  { name: "暴擊＋擊殺（只停一次）", events: (c, t) => [atk(c, t, true), dmgEv(c, t, 20, { crit: true, round: 2 }), { seq: 4, round: 2, type: "unit_downed", unit_id: t }], after: { hp: 0, downed: true } },
  { name: "Boss 大招（四周變暗 0.3 秒）", caster: { tags: ["boss"], statuses: [{ status_id: "charging", remaining: 1 }] } as unknown as Partial<UnitView>, followup: true, events: (c, t) => [dmgEv(c, t, 6)] },
  { name: "復活（倒地站起、綠光）", look: { hp: 0, downed: true, revivable: true }, events: (c, t) => [{ seq: 2, round: 1, type: "unit_revived", unit_id: t, source_id: c, skill_id: "sk", hp: 5 }], after: { hp: 5, downed: false, revivable: false } },
  { name: "異形復活（通用片段）", look: { ...HOUND, hp: 0, downed: true, revivable: true } as Partial<UnitView>, events: (c, t) => [{ seq: 2, round: 1, type: "unit_revived", unit_id: t, source_id: c, skill_id: "sk", hp: 5 }], after: { hp: 5, downed: false, revivable: false } },
  { name: "異形格擋（彈開＝輕版受擊）", caster: HOUND, events: (c, t) => [atk(c, t, true), dmgEv(c, t, 3, { block_permille: 500 })] },
];

const fxClock = (r: BattleRenderer): number => (r as unknown as { effectClock: number }).effectClock;

/** 等畫布的效果時鐘走到 `until`，而且那一刻以前的停頓都用完（停頓時效果時鐘停住）。停格（`?freeze=`）時直接回來。 */
async function waitFx(r: BattleRenderer, until: number): Promise<void> {
  const freezes = () => (r as unknown as { freezes: Array<{ at: number }> }).freezes;
  while (!frozen && (fxClock(r) < until || freezes().some((f) => f.at <= until))) await wait(16);
}

async function results(): Promise<void> {
  const units: UnitView[] = [];
  const tags: Array<[string, Pos]> = [];
  RESULTS.forEach((c, i) => {
    const x = (i % 3) * 4;
    const y = Math.floor(i / 3) * 2;
    const caster = hero(`u_${String(i).padStart(2, "0")}`, x, y, "one_handed_sword", "east");
    units.push({ ...caster, ...(c.caster ?? {}) } as UnitView);
    // 目標：復活是倒地的友軍（同隊）；其他是敵人
    const ally = c.events("", "").some((e) => e.type === "unit_revived");
    units.push(unit(`t_${i}`, ally ? "ally" : "enemy", x + 1, y, { template_id: "hero_fighter", weapon_id: "one_handed_sword", name_zh: "對手", facing: "west", hp: 20, max_hp: 20, ...(c.look ?? {}) }));
    tags.push([c.name, { x, y: y + 1 }]);
  });
  // 勝利：最後一排我方三人（舉手、收刀照雜湊）＋一隻異形友軍
  const vy = Math.ceil(RESULTS.length / 3) * 2;
  ["v_0", "v_1", "v_2"].forEach((id, k) => units.push(hero(id, k * 2, vy, k === 1 ? "bow" : "one_handed_sword", "east")));
  units.push(unit("v_3", "ally", 6, vy, { ...HOUND, name_zh: "獵犬", facing: "east" }));
  tags.push(["勝利（battle_ended 我方勝：全隊舉手或收刀、浮出「勝利」）", { x: 0, y: vy + 1 }]);
  const before = battle(units, 12, vy + 2);
  const after = {
    ...before,
    units: before.units.map((u) => {
      const c = u.id.startsWith("t_") ? RESULTS[Number(u.id.slice(2))] : undefined;
      const cu = u.id.startsWith("u_") ? RESULTS[Number(u.id.slice(2))] : undefined;
      return { ...u, ...(c?.after ?? {}), ...(cu?.caster?.statuses !== undefined ? { statuses: [] } : {}) };
    }),
  } as BattleView;
  const r = await show(before);
  labels(tags);
  caption("6N-5・特殊結果（特效加停頓，不做慢動作、鏡頭）：暴擊、擊殺、格擋成功、閃避成功、Boss 大招；6N-4 補：復活、勝利");
  started(r);
  const cards = { sk: card("single", 1, ["damage"]) };
  for (;;) {
    if (frozen) return;
    r.draw(buildDrawModel(before, HERO));
    const memo = newSpecialMemo(); // 每一輪重新開始（擊殺同一輪只強化一次：「暴擊＋擊殺」那格在第 2 輪）
    let longest = 0;
    let lead = 0;
    let leadFx = 0;
    const start = fxClock(r);
    const allEvents: Record<string, unknown>[] = [];
    RESULTS.forEach((c, i) => {
      const caster = `u_${String(i).padStart(2, "0")}`;
      const tgt = `t_${i}`;
      const pos = before.units.find((u) => u.id === tgt)!.pos;
      const from = before.units.find((u) => u.id === caster)!.pos;
      const head = c.followup === true
        ? { seq: 1, round: 1, type: "skill_followup", unit_id: caster, skill_id: "sk", name_zh: "大招", when: "next_turn", origin: from, tiles: [pos] }
        : { seq: 1, round: 1, type: "skill_used", unit_id: caster, skill_id: "sk", tiles: [pos] };
      const events = [head, ...c.events(caster, tgt)];
      allEvents.push(...events);
      const raw = vfxFor(events, after, cards);
      const tl = skillTimeline(events, after, cards, raw, (id) => r.weaponClassOf(id));
      if (tl === null) return;
      const vfx = scaleVfx(withSpecials(tl.vfx, events, before, after, memo), SCALE);
      const origins = r.playSkill(scaleRows(tl.rows, SCALE));
      r.playVfx(vfx, Math.round(VFX_TIMING.impact * SCALE), true, origins);
      const hold = stopHoldMs(vfx);
      lead = Math.max(lead, vfx.leadMs + hold);
      leadFx = Math.max(leadFx, vfx.leadMs);
      longest = Math.max(longest, ...scaleRows(tl.rows, SCALE).map((x) => x.startMs + x.ms + hold), vfx.leadMs + hold);
    });
    // 正式播放：命中（加停頓）之後以結果重畫，跳浮動字樣（暴擊、格擋、閃避）。
    // 這頁照畫布的效果時鐘等（背景分頁的畫面更新被節流時，`?freeze=` 停格的時間和重畫仍對得上）
    await waitFx(r, start + leadFx);
    if (frozen) return;
    r.draw(buildDrawModel(after, HERO));
    r.playFeedback(feedbackFor(allEvents, after), Math.round(FEEDBACK_MS * SCALE));
    await wait(longest - lead + Math.round(VFX_TIMING.impact * SCALE) + 600);
    if (frozen) return;
    const won = victoryOf([{ seq: 99, round: 1, type: "battle_ended", winner: "ally", reason: "eliminated" }], after, HERO);
    if (won !== null) {
      const v = { ...won, unitIds: won.unitIds.filter((id) => id.startsWith("v_")), ms: Math.round(VICTORY_HOLD_MS * SCALE), clipMs: Math.round(VICTORY_MS * SCALE) };
      r.playVictory(v);
      await wait(v.ms + 600);
    }
    window.__skillDone = true;
  }
}

// ---- 6N-6：攻擊變體 ----------------------------------------------------------------

/** 每列（變體表）的代表武器：武器 ID，或主手的外觀（刀 ＝ 彎刀）。 */
const FAMILY_UNIT: Readonly<Record<AttackFamily, Partial<UnitView>>> = {
  sword: { weapon_id: "one_handed_sword" },
  saber: { weapon_id: "one_handed_sword", equipment: [{ slot: "main_hand", appearance: { kind: "sword", form: "curved", material: "steel" } }] } as unknown as Partial<UnitView>,
  arcane: { weapon_id: "arcane_blade" },
  heavy: { weapon_id: "axe" },
  pair: { weapon_id: "dual_dagger" },
  spear: { weapon_id: "spear" },
  scythe: { weapon_id: "scythe" },
  whip: { weapon_id: "whip" },
};

/** 讓正式的雜湊挑到第 `k` 個變體的 seq（dev 頁要固定每格的變體；仍走正式的 `variantFor`）。 */
function seqFor(family: AttackFamily, caster: string, k: number): number {
  for (let seq = 1; seq < 5000; seq++) if (variantFor(family, "skill_gallery", seq, caster).index === k) return seq;
  return 1;
}

const basicHit = (seq: number, c: string, t: string, crit: boolean): Record<string, unknown>[] => [
  { seq, round: 1, type: "attack_rolled", attacker_id: c, target_id: t, hit: true, crit },
  { seq: seq + 1, round: 1, type: "damage_dealt", target_id: t, source_id: c, element: "physical", amount: crit ? 18 : 6, hp_before: 40, hp_after: 40 - (crit ? 18 : 6), crit, block_permille: 1000 },
];

/**
 * `#variants`：每種近戰武器的全部變體（每格固定一個，一直循環）；最後一排每種武器一人，連續 8 次普攻（seq 1～8）照雜湊挑，
 * 格上寫目前是第幾次、挑到哪一個。`?crit=1` 全部暴擊（金色粗弧、「暴擊 −N」的大小）；`?dir=west` 朝西。
 */
async function variants(): Promise<void> {
  const crit = params.get("crit") === "1";
  const facing = WEST ? "west" : "east";
  const units: UnitView[] = [];
  const tags: Array<[string, Pos]> = [];
  const cast: Array<{ caster: string; target: string; family: AttackFamily; k: number | null }> = [];
  const W = 15;
  ATTACK_FAMILIES.forEach((f, row) => {
    const y = row * 2;
    ATTACK_VARIANTS[f].forEach((v, k) => {
      const x = WEST ? W - 1 - k * 3 : k * 3;
      const id = `u_${row}${k}`;
      units.push({ ...hero(id, x, y, "one_handed_sword", facing), ...FAMILY_UNIT[f] } as UnitView);
      units.push(unit(`t_${row}${k}`, "enemy", WEST ? x - 1 : x + 1, y, { template_id: "t", name_zh: "木樁", facing: WEST ? "east" : "west", hp: 40, max_hp: 40 }));
      tags.push([`${k === 0 ? `${FAMILY_ZH[f]}・` : ""}${v.zh}`, { x: WEST ? x - 1 : x, y: y + 1 }]);
      cast.push({ caster: id, target: `t_${row}${k}`, family: f, k });
    });
  });
  // 連續 8 次：每種武器一人
  const ry = ATTACK_FAMILIES.length * 2;
  const live: Array<{ caster: string; target: string; family: AttackFamily; tag: Pos }> = [];
  ATTACK_FAMILIES.forEach((f, i) => {
    const col = i % 4;
    const y = ry + Math.floor(i / 4) * 2;
    const x = WEST ? W - 1 - col * 4 : col * 4;
    const id = `r_${i}`;
    units.push({ ...hero(id, x, y, "one_handed_sword", facing), ...FAMILY_UNIT[f] } as UnitView);
    units.push(unit(`rt_${i}`, "enemy", WEST ? x - 1 : x + 1, y, { template_id: "t", name_zh: "木樁", facing: WEST ? "east" : "west", hp: 40, max_hp: 40 }));
    live.push({ caster: id, target: `rt_${i}`, family: f, tag: { x: WEST ? x - 1 : x, y: y + 1 } });
  });
  const v = battle(units, W, ry + 4);
  const r = await show(v);
  labels(tags);
  const liveTags = live.map((l) => {
    labels([[FAMILY_ZH[l.family], l.tag]]);
    return document.querySelector(".scene")!.lastElementChild as HTMLElement;
  });
  caption(`6N-6・近戰攻擊變體（${facing}${crit ? "，暴擊" : ""}）：上面每格固定一個變體；最後兩排每種武器連續 8 次普攻（seq 1～8，戰鬥鍵 skill_gallery）照雜湊挑`);
  const list = document.createElement("pre");
  list.id = "picks";
  list.textContent = ATTACK_FAMILIES.map((f) => `${FAMILY_ZH[f]}（${ATTACK_VARIANTS[f].length} 種）連續 8 次：` + Array.from({ length: 8 }, (_, i) => ATTACK_VARIANTS[f][variantFor(f, "skill_gallery", i + 1, live[ATTACK_FAMILIES.indexOf(f)]!.caster).index]!.zh).join("、")).join("\n");
  list.style.cssText = "font:12px monospace;white-space:pre;margin-top:8px";
  document.body.appendChild(list);
  started(r);
  const attackOf = (id: string) => r.attackFamilyOf(id);
  for (let n = 1; ; n = (n % 8) + 1) {
    if (frozen) return;
    r.draw(buildDrawModel(v, HERO));
    const all: Record<string, unknown>[] = [];
    const runs = [
      ...cast.map((c) => ({ ...c, seq: seqFor(c.family, c.caster, c.k!) })),
      ...live.map((l, i) => {
        const pick = variantFor(l.family, "skill_gallery", n, l.caster);
        liveTags[i]!.textContent = `${FAMILY_ZH[l.family]} 第 ${n} 次：${ATTACK_VARIANTS[l.family][pick.index]!.zh}`;
        return { caster: l.caster, target: l.target, family: l.family, k: null, seq: n }; // 第 n 次 ＝ seq n（每人的鍵含自己的 ID）
      }),
    ];
    let longest = 0;
    let leadFx = 0;
    const start = fxClock(r);
    for (const c of runs) {
      const events = basicHit(c.seq, c.caster, c.target, crit);
      all.push(...events);
      const raw = vfxFor(events, v, {});
      const tl = skillTimeline(events, v, {}, raw, (id) => r.weaponClassOf(id), attackOf);
      if (tl === null) continue;
      // 暴擊的閃白、停頓只給第一個（四十幾個同時暴擊時閃白會疊成一片白；正式戰鬥一步只有幾下）
      const vfx = scaleVfx(c === runs[0] ? withSpecials(tl.vfx, events, v, v, newSpecialMemo()) : tl.vfx, SCALE);
      const origins = r.playSkill(scaleRows(tl.rows, SCALE));
      r.playVfx(vfx, Math.round(VFX_TIMING.impact * SCALE), false, origins);
      leadFx = Math.max(leadFx, vfx.leadMs);
      longest = Math.max(longest, ...scaleRows(tl.rows, SCALE).map((x) => x.startMs + x.ms), vfx.leadMs + stopHoldMs(vfx));
    }
    await waitFx(r, start + leadFx);
    if (frozen) return;
    r.playFeedback(feedbackFor(all, v), Math.round(FEEDBACK_MS * SCALE));
    // `?floatAt=毫秒`：浮動字出現後那麼久停格（截「暴擊 −N」的大小用）
    const floatAt = Number(params.get("floatAt") ?? "");
    if (Number.isFinite(floatAt) && floatAt > 0) {
      const t0 = fxClock(r);
      while (fxClock(r) - t0 < floatAt) await wait(16);
      r.setBoost(1e-6);
      frozen = true;
      return;
    }
    await wait(longest - leadFx + Math.round(VFX_TIMING.impact * SCALE) + 700);
    window.__skillDone = true;
  }
}

const MODES: Readonly<Record<string, () => Promise<void>>> = { openers, prims, lower: primsLower, order, moves, perf, react: reacts, result: results, variants };
void (MODES[MODE] ?? openers)();
