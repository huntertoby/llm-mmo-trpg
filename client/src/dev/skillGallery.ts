// 開發用：技能片段（Phase 6N-1／6N-2／6N-3）。開 `client/skill-gallery.html`（pnpm dev 後 /skill-gallery.html）。不屬於正式 build。
// 全部走正式的串接器（battle/skillSequence.ts）與繪製器（BattleRenderer.playSkill／playVfx），只是事件是假的。
// `#openers`：13 種武器 × 一種施放方式（`?mode=melee|ranged|self|ground`，`?dir=west` 朝西），一直循環，火元素；
// `#prims`：6N-2 上半的原語片段（劍＋近身起手，接原語片段）；
// `#lower`：6N-3 下半的原語片段（`?group=world` 召喚、地表、地形、物件、符文；`?group=rules` 形態、防護、給予、退還、層數、規則類，含兩組多原語）；
// `#order`：樣張第 5 區的三組（砍＋跳、跳＋砍、衝刺＋砍）照卡上的順序播（走 playbackPlan → frameOps，同正式播放）；
// `#moves`：位移類原語（衝刺、跳躍、傳送、瞬步、交換）與被推、被拉；
// `#perf`：12×12 戰場 8 人輪流放技能 6 秒，和靜止 3 秒比 FPS、記下貼圖數（`?react=1`：6N-4 目標輪流受擊、格擋、閃避）；
// `#react`：6N-4 受擊與結果（受擊、重擊、閃避、格擋三種、倒下、異形）＋陷阱夾住、冰面滑倒；
// `#variants`：6N-6 近戰＋6N-7 遠程、拳套空手的攻擊變體，受擊、閃避的變體（每種的全部變體＋連續 8 次挑到的變體；`?crit=1` 暴擊）；
// `#result`：6N-5 特殊結果（暴擊、擊殺、格擋成功、閃避成功、Boss 大招；停頓）＋復活、勝利；
// `#skillvar`：6N-8 技能變體（三層各自的全部變體、同一個火球放 3 次、同一招放 5 次）。
// `?anim=0.1` 慢動作（playback.ts 的 devAnimFactor）；`?cell=88` 放大格子。
import type { BattleResponse, BattleView, Glossary, MoveMode, Pos, SkillCard, StepOut, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { FEEDBACK_MS, frameOps, playbackPlan, SPEED_SCALE } from "../battle/playback";
import { feedbackFor } from "../battle/feedback";
import { stopHoldMs, victoryOf, VICTORY_HOLD_MS, VICTORY_MS, withSpecials } from "../battle/specials";
import { scaleRows, skillTimeline, variantFor } from "../battle/skillSequence";
import { tile, unit } from "../battle/testFixtures";
import { scaleVfx, vfxFor, VFX_TIMING, type VfxCards } from "../battle/vfx";
import { BattleRenderer } from "../render/BattleRenderer";
import { ATTACK_FAMILIES, ATTACK_VARIANTS, FAMILY_ZH, RANGED_FAMILIES, type AttackFamily } from "../render/attackVariants";
import { DODGE_VARIANTS, HIT_VARIANTS, reactVariant } from "../render/reactClips";
import { CAST_MODES, type CastMode, type PrimitiveClipId } from "../render/skillClips";
import { BURST_SHAPES, CAST_OPENERS, CHARGE_POSES, DASH_ROUTES, HEAL_STYLES, LEAP_ARCS, OPENER_SETS, pickSkillVariant, skillVariantKey, SPREADS, STAFF_CHANTS, SUMMON_CIRCLES, TRAILS, type DashRoute, type LeapArc, type OpenerSet } from "../render/skillVariants";
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
      const vfx = scaleVfx(withSpecials(tl.vfx, events, before, after), SCALE);
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
  fist: { weapon_id: "fist" },
  bow: { weapon_id: "bow" },
  crossbow: { weapon_id: "crossbow" },
  gun: { weapon_id: "longgun" },
};

/** 連續 8 次那幾排的施放者 ID（第 i 人；受擊、閃避的目標是 `rt_<i>`）。vitest 鎖住這組鍵連續 8 次至少 3 種。 */
const liveCaster = (i: number): string => `r_${i}`;

/** 遠程的列（弓、弩、火槍）目標放在 2 格外（遠程普攻才挑變體；近身時照舊用弓身敲）。 */
const reach = (f: AttackFamily): number => (RANGED_FAMILIES.includes(f) ? 2 : 1);

/** 讓受擊（`hit`；damage_dealt 的 seq ＝ 攻擊 seq＋1）或閃避（`dodge`）挑到第 `k` 個變體的攻擊 seq。 */
function reactSeqFor(clip: "hit" | "dodge", target: string, k: number): number {
  for (let seq = 1; seq < 5000; seq++) if (reactVariant("skill_gallery", clip === "hit" ? seq + 1 : seq, target, clip) === k) return seq;
  return 1;
}

const basicMiss = (seq: number, c: string, t: string): Record<string, unknown>[] => [{ seq, round: 1, type: "attack_rolled", attacker_id: c, target_id: t, hit: false }];

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
  /** `react`：6N-7 受擊、閃避的變體（施放者一律單手劍；`seq` 由 `reactSeqFor` 照受擊者的鍵找）。 */
  type Run = { caster: string; target: string; family: AttackFamily; k: number | null; react?: "hit" | "dodge" };
  const cast: Run[] = [];
  const W = 15;
  const dummy = (id: string, x: number, y: number) => unit(id, "enemy", x, y, { template_id: "t", name_zh: "木樁", facing: WEST ? "east" : "west", hp: 40, max_hp: 40 });
  const at = (x: number, d: number) => (WEST ? x - d : x + d);
  ATTACK_FAMILIES.forEach((f, row) => {
    const y = row * 2;
    ATTACK_VARIANTS[f].forEach((v, k) => {
      const x = WEST ? W - 1 - k * 3 : k * 3;
      const id = `u_${row}_${k}`;
      units.push({ ...hero(id, x, y, "one_handed_sword", facing), ...FAMILY_UNIT[f] } as UnitView);
      units.push(dummy(`t_${row}_${k}`, at(x, reach(f)), y));
      tags.push([`${k === 0 ? `${FAMILY_ZH[f]}・` : ""}${v.zh}`, { x: WEST ? x - reach(f) : x, y: y + 1 }]);
      cast.push({ caster: id, target: `t_${row}_${k}`, family: f, k });
    });
  });
  // 6N-7：受擊（3）、閃避（3）的變體，各一排
  const reactRows: Array<["hit" | "dodge", readonly { zh: string }[]]> = [["hit", HIT_VARIANTS], ["dodge", DODGE_VARIANTS]];
  reactRows.forEach(([clip, list], j) => {
    const y = (ATTACK_FAMILIES.length + j) * 2;
    list.forEach((rv, k) => {
      const x = WEST ? W - 1 - k * 4 : k * 4;
      const id = `q_${clip}_${k}`;
      units.push({ ...hero(id, x, y, "one_handed_sword", facing) } as UnitView);
      units.push({ ...hero(`qt_${clip}_${k}`, at(x, 1), y, "one_handed_sword", WEST ? "east" : "west"), team: "enemy", hp: 40, max_hp: 40 } as UnitView);
      tags.push([`${k === 0 ? (clip === "hit" ? "受擊・" : "閃避・") : ""}${rv.zh}`, { x: WEST ? x - 1 : x, y: y + 1 }]);
      cast.push({ caster: id, target: `qt_${clip}_${k}`, family: "sword", k, react: clip });
    });
  });
  // 連續 8 次：每種武器一人，加上受擊、閃避各一人
  const ry = (ATTACK_FAMILIES.length + reactRows.length) * 2;
  const live: Array<{ caster: string; target: string; family: AttackFamily; tag: Pos; react?: "hit" | "dodge" }> = [];
  const liveRows: Array<{ family: AttackFamily; react?: "hit" | "dodge" }> = [...ATTACK_FAMILIES.map((family) => ({ family })), { family: "sword", react: "dodge" }, { family: "sword", react: "hit" }];
  liveRows.forEach((lr, i) => {
    const col = i % 4;
    const y = ry + Math.floor(i / 4) * 2;
    const x = WEST ? W - 1 - col * 4 : col * 4;
    const id = liveCaster(i);
    const d = lr.react === undefined ? reach(lr.family) : 1;
    units.push({ ...hero(id, x, y, "one_handed_sword", facing), ...FAMILY_UNIT[lr.family] } as UnitView);
    if (lr.react === undefined) units.push(dummy(`rt_${i}`, at(x, d), y));
    else units.push({ ...hero(`rt_${i}`, at(x, d), y, "one_handed_sword", WEST ? "east" : "west"), team: "enemy", hp: 40, max_hp: 40 } as UnitView);
    live.push({ caster: id, target: `rt_${i}`, family: lr.family, tag: { x: WEST ? x - d : x, y: y + 1 }, ...(lr.react === undefined ? {} : { react: lr.react }) });
  });
  const v = battle(units, W, ry + Math.ceil(liveRows.length / 4) * 2);
  const r = await show(v);
  labels(tags);
  const liveName = (l: (typeof live)[number]) => (l.react === "hit" ? "受擊" : l.react === "dodge" ? "閃避" : FAMILY_ZH[l.family]);
  const liveTags = live.map((l) => {
    labels([[liveName(l), l.tag]]);
    return document.querySelector(".scene")!.lastElementChild as HTMLElement;
  });
  /** 連續 8 次的第 n 次挑到的變體名稱（受擊：damage_dealt 的 seq ＝ n＋1；閃避：attack_rolled 的 seq ＝ n；鍵用受擊者 ID）。 */
  const livePick = (l: (typeof live)[number], n: number): string =>
    l.react === "hit" ? HIT_VARIANTS[reactVariant("skill_gallery", n + 1, l.target, "hit")]!.zh
    : l.react === "dodge" ? DODGE_VARIANTS[reactVariant("skill_gallery", n, l.target, "dodge")]!.zh
    : ATTACK_VARIANTS[l.family][variantFor(l.family, "skill_gallery", n, l.caster).index]!.zh;
  caption(`6N-6／6N-7・攻擊、受擊、閃避的變體（${facing}${crit ? "，暴擊" : ""}）：上面每格固定一個變體（弓、弩、火槍的目標在 2 格外）；最後幾排每種武器、受擊、閃避各一人連續 8 次（seq 1～8，戰鬥鍵 skill_gallery）照雜湊挑`);
  const list = document.createElement("pre");
  list.id = "picks";
  list.textContent = live.map((l) => `${liveName(l)}（${l.react === undefined ? ATTACK_VARIANTS[l.family].length : 3} 種）連續 8 次：` + Array.from({ length: 8 }, (_, i) => livePick(l, i + 1)).join("、")).join("\n");
  list.style.cssText = "font:12px monospace;white-space:pre;margin-top:8px";
  document.body.appendChild(list);
  started(r);
  const attackOf = (id: string) => r.attackFamilyOf(id);
  for (let n = 1; ; n = (n % 8) + 1) {
    if (frozen) return;
    r.draw(buildDrawModel(v, HERO));
    const all: Record<string, unknown>[] = [];
    const runs = [
      ...cast.map((c) => ({ ...c, seq: c.react === undefined ? seqFor(c.family, c.caster, c.k!) : reactSeqFor(c.react, c.target, c.k!) })),
      ...live.map((l, i) => {
        liveTags[i]!.textContent = `${liveName(l)} 第 ${n} 次：${livePick(l, n)}`;
        return { caster: l.caster, target: l.target, family: l.family, k: null, seq: n, react: l.react }; // 第 n 次 ＝ seq n（每人的鍵含自己的 ID）
      }),
    ];
    let longest = 0;
    let leadFx = 0;
    const start = fxClock(r);
    for (const c of runs) {
      const events = c.react === "dodge" ? basicMiss(c.seq, c.caster, c.target) : basicHit(c.seq, c.caster, c.target, crit);
      all.push(...events);
      const raw = vfxFor(events, v, {});
      const tl = skillTimeline(events, v, {}, raw, (id) => r.weaponClassOf(id), attackOf);
      if (tl === null) continue;
      // 暴擊的閃白、停頓只給第一個（四十幾個同時暴擊時閃白會疊成一片白；正式戰鬥一步只有幾下）
      const vfx = scaleVfx(c === runs[0] ? withSpecials(tl.vfx, events, v, v) : tl.vfx, SCALE);
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

// ---- 6N-8 技能變體（#skillvar） ------------------------------------------------------

type Pick = ReturnType<typeof pickSkillVariant>;
type PickWant = Partial<Record<"opener" | "dash" | "leap" | "summon" | "heal" | "trail" | "burst" | "spread", number>>;

/** 讓正式的挑法（`pickSkillVariant`，鍵 ＝ skill_gallery:seq:施放者:skill:技能 ID）挑到想要的組合的 seq。 */
function skillSeqFor(caster: string, skill: string, set: OpenerSet | null, want: PickWant): number {
  for (let seq = 1; seq < 40000; seq += 2) {
    const p = pickSkillVariant(skillVariantKey("skill_gallery", seq, caster, skill), set);
    if (Object.entries(want).every(([k, i]) => (k === "opener" ? p.opener?.index === i : p[k as keyof PickWant] === i))) return seq;
  }
  return 1;
}

/** 挑到的變體寫成一行（起手／軌跡／爆發／粒子；有原語時加上原語）。 */
function pickText(p: Pick, prims: readonly ("dash" | "leap" | "summon" | "heal")[] = []): string {
  const o = p.opener === null ? "起手照舊" : OPENER_SETS[p.opener.set][p.opener.index]!.zh;
  const names = { dash: DASH_ROUTES, leap: LEAP_ARCS, summon: SUMMON_CIRCLES, heal: HEAL_STYLES } as const;
  const more = prims.map((k) => names[k][p[k]]!.zh);
  return [o, ...more, TRAILS[p.trail]!.zh, BURST_SHAPES[p.burst]!.zh, SPREADS[p.spread]!.zh].join("／");
}

/** 一個施放者在 `seq` 放一次（skill_used 的 seq；傷害 seq＋1），直接走串接器＋繪製器；回傳這一招的長度。 */
function castSeq(r: BattleRenderer, v: BattleView, caster: string, target: Pos, cards: VfxCards, seq: number, hurt = true): number {
  if (frozen) return 0;
  const from = v.units.find((u) => u.id === caster)!.pos;
  const sk = Object.keys(cards)[0]!;
  const tiles = cards[sk]?.icon?.segments[0]?.shape_id === "self" ? [from] : [target];
  const tgt = v.units.find((u) => u.pos.x === target.x && u.pos.y === target.y && u.id !== caster);
  const events: Record<string, unknown>[] = [
    { seq, round: 1, type: "skill_used", unit_id: caster, skill_id: sk, tiles },
    ...(tgt === undefined || !hurt ? [] : [{ seq: seq + 1, round: 1, type: "damage_dealt", target_id: tgt.id, source_id: caster, element: "fire", amount: 5 }]),
  ];
  const raw = vfxFor(events, v, cards);
  const tl = skillTimeline(events, v, cards, raw, (id) => r.weaponClassOf(id));
  if (tl === null) return 0;
  const vfx = scaleVfx(tl.vfx, SCALE);
  const rows = scaleRows(tl.rows, SCALE);
  const origins = r.playSkill(rows);
  r.playVfx(vfx, Math.round(VFX_TIMING.impact * SCALE), false, origins);
  return Math.max(...rows.map((x) => x.startMs + x.ms), vfx.leadMs) + Math.round(VFX_TIMING.impact * SCALE);
}

/** 場景上的小字（每個場景自己的框）。 */
function tagsIn(box: HTMLElement, items: ReadonlyArray<[string, Pos]>): HTMLElement[] {
  box.style.position = "relative";
  return items.map(([text, p]) => {
    const d = document.createElement("div");
    d.textContent = text;
    d.style.cssText = `position:absolute;left:${p.x * CELL + 2}px;top:${p.y * CELL + 1}px;font:11px sans-serif;color:#ffe9a8;text-shadow:0 0 2px #000;pointer-events:none;white-space:nowrap`;
    box.appendChild(d);
    return d;
  });
}

function heading(text: string): void {
  const h = document.createElement("h2");
  h.textContent = text;
  document.body.appendChild(h);
}

const fireCard = (id: string, shape: string, range: number, effects: string[]): VfxCards => ({ [id]: { ...card(shape, range, effects), id, element: "fire" } as unknown as SkillCard });

/** 一格「施放者 → 目標」的設定：哪一組起手、想要的變體、施放者武器、卡片、目標的距離、位移（衝刺、跳躍）。 */
interface VarCell {
  tag: string;
  weapon: string;
  set: OpenerSet | null;
  want: PickWant;
  cards: VfxCards;
  reach: number;
  prims?: readonly ("dash" | "leap" | "summon" | "heal")[];
  move?: { mode: "dash" | "leap"; clip: PrimitiveClipId; route?: DashRoute; hop?: LeapArc };
  hurt?: boolean;
}

/** 一排變體（一個場景裡的一列）。 */
function varRow(label: string, cells: VarCell[]): { label: string; cells: VarCell[] } {
  return { label, cells };
}

/**
 * `#skillvar`：6N-8 技能變體（方案 2.11）。上面一個大場景 ＝ 三層各自的全部變體（每格固定一個，照正式的挑法找 seq；
 * 其他層固定第一個）；接著「同一個火球放 3 次」（樣張第 10 區的三組：舉杖／微弧／放射、身前畫陣／直線／圓環、頓地捲火／螺旋／星形），
 * 最後「同一招放 5 次」（同一個施放者、seq 1、3、5、7、9，照雜湊挑）。顏色（火）、範圍（目標格）每一次都一樣。
 */
async function skillVariants(): Promise<void> {
  const ball = fireCard("fireball", "single", 5, ["damage"]);
  const rows = [
    varRow("詠唱", STAFF_CHANTS.map((c, k) => ({ tag: c.zh, weapon: "fire_staff", set: "chant_s", want: { opener: k, trail: 1, burst: 0, spread: 0 }, cards: ball, reach: 2 }))),
    varRow("施法起手", [
      ...CAST_OPENERS.map((c, k): VarCell => ({ tag: c.zh, weapon: "one_handed_sword", set: "cast", want: { opener: k, trail: 1, burst: 0, spread: 0 }, cards: ball, reach: 2 })),
      ...CHARGE_POSES.map((c, k): VarCell => ({ tag: k === 0 ? `蓄力・${c.zh}` : c.zh, weapon: "one_handed_sword", set: "charge", want: { opener: k, burst: 0, spread: 0 }, cards: fireCard("cleave", "single", 1, ["damage"]), reach: 1 })),
    ]),
    varRow("召喚法陣", [
      ...SUMMON_CIRCLES.map((c, k): VarCell => ({ tag: c.zh, weapon: "one_handed_sword", set: "cast", want: { opener: 0, summon: k }, cards: fireCard("summon", "ground_tile", 3, ["summon"]), reach: 2, prims: ["summon"], hurt: false })),
      ...HEAL_STYLES.map((c, k): VarCell => ({ tag: k === 0 ? `治療增益・${c.zh}` : c.zh, weapon: "one_handed_sword", set: "cast", want: { opener: 0, heal: k }, cards: fireCard("mend", "self", 0, ["heal"]), reach: 1, prims: ["heal"], hurt: false })),
    ]),
    varRow("衝刺", DASH_ROUTES.map((c): VarCell => ({ tag: c.zh, weapon: "one_handed_sword", set: null, want: {}, cards: {}, reach: 3, move: { mode: "dash", clip: "dash_lean", route: c.id } }))),
    varRow("跳躍", LEAP_ARCS.map((c): VarCell => ({ tag: c.zh, weapon: "one_handed_sword", set: null, want: {}, cards: {}, reach: 2, move: { mode: "leap", clip: "leap_air", hop: c.id } }))),
    varRow("軌跡", TRAILS.map((c, k): VarCell => ({ tag: c.zh, weapon: "fire_staff", set: "chant_s", want: { opener: 0, trail: k, burst: 0, spread: 0 }, cards: ball, reach: 4 }))),
    varRow("爆發", BURST_SHAPES.map((c, k): VarCell => ({ tag: c.zh, weapon: "fire_staff", set: "chant_s", want: { opener: 0, trail: 1, burst: k, spread: 0 }, cards: ball, reach: 4 }))),
    varRow("粒子", SPREADS.map((c, k): VarCell => ({ tag: c.zh, weapon: "fire_staff", set: "chant_s", want: { opener: 0, trail: 1, burst: 0, spread: k }, cards: ball, reach: 4 }))),
  ];
  const W = 16;
  const units: UnitView[] = [];
  const tags: Array<[string, Pos]> = [];
  const runs: Array<{ caster: string; target: Pos; cell: VarCell; seq: number }> = [];
  rows.forEach((row, ri) => {
    const y = ri * 2;
    let x = 0;
    row.cells.forEach((cell, k) => {
      const at0 = x;
      const id = `sv_${ri}_${k}`;
      const sk = Object.keys(cell.cards)[0] ?? "none";
      units.push(hero(id, x, y, cell.weapon, "east"));
      const target = { x: x + cell.reach, y };
      if (cell.hurt !== false && cell.move === undefined) units.push(unit(`svt_${ri}_${k}`, "enemy", target.x, y, { template_id: "t", name_zh: "木樁", facing: "west", hp: 40, max_hp: 40 }));
      const seq = cell.move === undefined ? skillSeqFor(id, sk, cell.set, cell.want) : 1;
      tags.push([`${k === 0 ? `${row.label}・` : ""}${cell.tag}`, { x: at0, y: y + 1 }]);
      runs.push({ caster: id, target, cell, seq });
      x += cell.reach + 1;
    });
  });
  heading("6N-8・技能變體（方案 2.11）：三層各自的全部變體（每格固定一個，照正式挑法找 seq；其他層固定第一個）。顏色照元素（火）、範圍照技能形狀，不會變");
  const v = battle(units, W, rows.length * 2);
  const r = await show(v);
  const box = document.querySelectorAll(".scene")[0] as HTMLElement;
  tagsIn(box, tags);

  // 同一個火球放 3 次（樣張第 10 區）
  heading("同一個火球放 3 次（同一個施放者 u_00、同一張卡 fireball，只有 seq 不同）：樣張第 10 區的三組");
  const sameCaster = "u_00";
  const sample = [0, 1, 2].map((k) => skillSeqFor(sameCaster, "fireball", "chant_s", { opener: k, trail: k, burst: k }));
  const triple: Array<{ r: BattleRenderer; v: BattleView; seq: number }> = [];
  for (const seq of sample) {
    const sv = battle([hero(sameCaster, 0, 0, "fire_staff", "east"), unit("u_t", "enemy", 4, 0, { template_id: "t", name_zh: "木樁", facing: "west", hp: 40, max_hp: 40 })], 6, 1);
    const sr = await show(sv);
    const p = pickSkillVariant(skillVariantKey("skill_gallery", seq, sameCaster, "fireball"), "chant_s");
    tagsIn(document.querySelectorAll(".scene")[document.querySelectorAll(".scene").length - 1] as HTMLElement, [[`seq ${seq}：${pickText(p)}`, { x: 0, y: 0 }]]);
    triple.push({ r: sr, v: sv, seq });
  }

  // 同一招放 5 次（照雜湊挑，不找 seq）
  heading("同一招放 5 次（u_00 的 fireball，seq 1、3、5、7、9 照雜湊挑）：顏色、範圍、落點、命中時間都一樣，姿勢和軌跡會變");
  const five: Array<{ r: BattleRenderer; v: BattleView; seq: number }> = [];
  for (const seq of [1, 3, 5, 7, 9]) {
    const sv = battle([hero(sameCaster, 0, 0, "fire_staff", "east"), unit("u_t", "enemy", 4, 0, { template_id: "t", name_zh: "木樁", facing: "west", hp: 40, max_hp: 40 })], 6, 1);
    const sr = await show(sv);
    const p = pickSkillVariant(skillVariantKey("skill_gallery", seq, sameCaster, "fireball"), "chant_s");
    tagsIn(document.querySelectorAll(".scene")[document.querySelectorAll(".scene").length - 1] as HTMLElement, [[`第 ${(seq + 1) / 2} 次（seq ${seq}）：${pickText(p)}`, { x: 0, y: 0 }]]);
    five.push({ r: sr, v: sv, seq });
  }
  const list = document.createElement("pre");
  list.id = "picks";
  list.textContent = [
    ...runs.filter((x) => x.cell.move === undefined).map((x) => `${x.cell.tag}：seq ${x.seq} → ${pickText(pickSkillVariant(skillVariantKey("skill_gallery", x.seq, x.caster, Object.keys(x.cell.cards)[0]!), x.cell.set), x.cell.prims)}`),
    ...[...triple, ...five].map((x) => `u_00 fireball seq ${x.seq} → ${pickText(pickSkillVariant(skillVariantKey("skill_gallery", x.seq, sameCaster, "fireball"), "chant_s"))}`),
  ].join("\n");
  list.style.cssText = "font:12px monospace;white-space:pre;margin-top:8px";
  document.body.appendChild(list);

  const all = [r, ...triple.map((x) => x.r), ...five.map((x) => x.r)];
  freezeAll(all);
  for (;;) {
    if (frozen) return;
    r.draw(buildDrawModel(v, HERO));
    for (const x of [...triple, ...five]) x.r.draw(buildDrawModel(x.v, HERO));
    let longest = 0;
    const moving: Promise<void>[] = [];
    for (const run of runs) {
      if (run.cell.move !== undefined) {
        const m = run.cell.move;
        const from = v.units.find((u) => u.id === run.caster)!.pos;
        const base = moveAnimOf({ seq: 1, round: 1, type: "unit_moved", unit_id: run.caster, from_pos: from, to_pos: run.target, mode: m.mode } as never, SCALE * 3);
        moving.push(r.animate([{ ...base, clip: m.clip, ...(m.route === undefined ? {} : { route: m.route }), ...(m.hop === undefined ? {} : { hop: m.hop }) }], () => false));
        continue;
      }
      longest = Math.max(longest, castSeq(r, v, run.caster, run.target, run.cell.cards, run.seq, run.cell.hurt !== false));
    }
    for (const x of [...triple, ...five]) longest = Math.max(longest, castSeq(x.r, x.v, sameCaster, { x: 4, y: 0 }, ball, x.seq));
    // 位移播完、特效也播完才重畫（重畫會換掉小人）
    await Promise.all([wait(longest + 600), ...moving.map((p) => p.then(() => wait(600)))]);
    window.__skillDone = true;
  }
}

/** `?freeze=毫秒`：第一輪開始後那麼久，所有場景一起停格（截圖用）。 */
function freezeAll(rs: readonly BattleRenderer[]): void {
  window.__skillStart = performance.now();
  const freeze = Number(params.get("freeze") ?? "");
  if (!Number.isFinite(freeze) || freeze <= 0) return;
  const t0 = fxClock(rs[0]!);
  const check = () => {
    if (fxClock(rs[0]!) - t0 >= freeze) {
      for (const x of rs) x.setBoost(1e-6);
      frozen = true;
    } else requestAnimationFrame(check);
  };
  requestAnimationFrame(check);
}

const MODES: Readonly<Record<string, () => Promise<void>>> = { openers, prims, lower: primsLower, order, moves, perf, react: reacts, result: results, variants, skillvar: skillVariants };
void (MODES[MODE] ?? openers)();
