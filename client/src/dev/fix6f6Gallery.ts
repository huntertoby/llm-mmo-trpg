// 開發用：6F-6 戰鬥介面小修的固定狀態（開 `client/dev/fix6f6-gallery.html`，pnpm dev 後 /dev/fix6f6-gallery.html）。不屬於正式 build。
// 全部走正式的播放流程（battle/playback.ts 的 playbackPlan → frameOps）與繪製器（BattleRenderer），只是事件是假的。
// 一張畫布一個場景，每 3 秒重播一次：
// 1. 陷阱夾住：擊倒＋暴擊 −9＋＋倒地同一步（巡檢 bug 8）；接著下一步同一格「＋11盾」和「閃避」；
// 2. 同一步先沒打中、後面才被凍住：照打的那一刻寫「閃避」（6N-6 規則逐處檢查）；本來就暈眩：「失手」；
// 3. 聖光爆發打在地圖左上角：光柱與範圍預覽不畫到地圖外（巡檢 bug 13）；
// 4. 倒地的我方（可復活，綠色愛心）與倒地的敵人（6F-6 起不畫愛心，巡檢 bug 14）。
// `?cell=72` 放大格子；`?once=1` 只播一次（截圖用）。
import type { BattleResponse, BattleView, Glossary, SkillCard, StepOut, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { frameOps, playbackPlan } from "../battle/playback";
import { tile, unit } from "../battle/testFixtures";
import type { VfxCards } from "../battle/vfx";
import { BattleRenderer } from "../render/BattleRenderer";

setGlossary(glossary as unknown as Glossary);

const params = new URLSearchParams(location.search);
const CELL = Number(params.get("cell") ?? "64") || 64;
const ONCE = params.get("once") === "1";
const HERO = "u_hero";

declare global {
  interface Window {
    __f6Done?: boolean;
  }
}

const wait = (ms: number) => new Promise<void>((r) => window.setTimeout(r, ms));

function grid(w: number, h: number): TileView[] {
  const tiles: TileView[] = [];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) tiles.push(tile(x, y, { terrain: (x + y) % 5 === 0 ? "dirt" : "grass" } as Partial<TileView>));
  return tiles;
}

function battle(units: UnitView[], w: number, h: number): BattleView {
  return {
    team: "ally", map_id: "fix6f6", map_name_zh: "6F-6", width: w, height: h, tiles: grid(w, h), objects: [], units, traps: [],
    turn_order: [HERO], active_unit: HERO, round: 2, max_rounds: 30, weather_id: null, weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null,
    source_wells: [], zones: [], runes: [],
  } as unknown as BattleView;
}

const st = (ids: string[]) => ids.map((status_id) => ({ status_id, remaining: 1 })) as unknown as UnitView["statuses"];
const heroAt = (x: number, y: number, over: Partial<UnitView> = {}) => unit(HERO, "ally", x, y, { name_zh: "主角", template_id: "hero_fighter", weapon_id: "one_handed_sword", facing: "east", ...over });
const foeAt = (id: string, x: number, y: number, over: Partial<UnitView> = {}) => unit(id, "enemy", x, y, { name_zh: "盜賊", template_id: "bandit", facing: "west", ...over });

function caption(text: string): void {
  const h = document.createElement("h2");
  h.textContent = text;
  document.body.appendChild(h);
}

async function show(v: BattleView): Promise<BattleRenderer> {
  const box = document.createElement("div");
  box.className = "scene";
  document.body.appendChild(box);
  const r = new BattleRenderer();
  await r.init(box);
  r.setScale(CELL / 48);
  r.setIdle(false);
  r.draw(buildDrawModel(v, HERO));
  return r;
}

/** 照正式流程播一串步驟（playbackPlan → frameOps）：移動、特效、換畫面、浮動字、停頓。 */
async function play(r: BattleRenderer, initial: BattleView, steps: StepOut[], cards: VfxCards = {}): Promise<void> {
  const last = steps[steps.length - 1]?.view ?? initial;
  const plan = playbackPlan({ steps, initial_view: initial, view: last } as unknown as BattleResponse, HERO, "normal", cards, new Set(), (id) => r.weaponClassOf(id));
  r.draw(buildDrawModel(plan.initialView, HERO));
  for (const frame of plan.frames) {
    for (const op of frameOps(frame)) {
      if (op.op === "move") await r.animate([op.anim], () => false);
      else if (op.op === "vfx") {
        const origins = op.skill === undefined ? undefined : r.playSkill(op.skill);
        r.playVfx(op.vfx, op.impactMs, false, origins);
        await wait(op.vfx.leadMs);
      } else if (op.op === "view") r.draw(buildDrawModel(op.view, HERO));
      else if (op.op === "feedback") r.playFeedback(op.items, op.durationMs);
      else if (op.op === "pause") await wait(Math.min(op.ms, 250));
    }
  }
}

const step = (actor: string, events: Record<string, unknown>[], view: BattleView, type = "attack"): StepOut => ({ actor_id: actor, events, view, step: { type } }) as unknown as StepOut;

/** 1. 陷阱夾住（擊倒＋暴擊＋倒地同一步），下一步同一格「＋11盾」＋「閃避」。 */
async function stackScene(): Promise<() => Promise<void>> {
  caption("1・浮動字錯開（巡檢 bug 8）：左＝陷阱夾住「擊倒／暴擊 −9／＋倒地」同一步；右＝「＋11盾」後接「閃避」");
  const v0 = battle([heroAt(1, 2), foeAt("u_a", 2, 2), foeAt("u_b", 4, 2, { hp: 20 }), unit("u_mate", "ally", 5, 2, { name_zh: "隊友", template_id: "hero_fighter", facing: "west" })], 7, 4);
  const r = await show(v0);
  return async () => {
    const downed = { ...v0, units: v0.units.map((u) => (u.id === "u_a" ? { ...u, hp: 0, downed: true, statuses: st(["prone"]) } : u)) } as BattleView;
    const trap = [
      { seq: 1, round: 2, type: "damage_dealt", target_id: "u_a", source_id: HERO, element: "physical", amount: 9, crit: true, hp_before: 9, hp_after: 0 },
      { seq: 2, round: 2, type: "unit_downed", unit_id: "u_a" },
      { seq: 3, round: 2, type: "status_applied", target_id: "u_a", status_id: "prone", duration: null, refreshed: false, source_id: HERO },
    ];
    const shield = [{ seq: 4, round: 2, type: "shield_gained", unit_id: "u_b", amount: 11 }];
    const dodge = [{ seq: 5, round: 2, type: "attack_rolled", attacker_id: "u_mate", target_id: "u_b", hit: false }];
    await Promise.all([play(r, v0, [step(HERO, trap, downed)]), (async () => {
      await play(r, v0, [step("u_b", shield, v0, "skill")]);
      await play(r, v0, [step("u_mate", dodge, v0)]);
    })()]);
  };
}

/** 2. 同一步先沒打中、後面才被凍住 → 閃避；本來就暈眩 → 失手。 */
async function missScene(): Promise<() => Promise<void>> {
  caption("2・閃避／失手照打的那一刻（6N-6 規則）：左＝沒打中之後同一步才被凍住（能動，寫閃避）；右＝本來就暈眩（不能動，寫失手）");
  const v0 = battle([heroAt(1, 2), foeAt("u_a", 2, 2), unit("u_c", "ally", 3, 2, { name_zh: "隊友", template_id: "hero_fighter", facing: "east" }), foeAt("u_b", 4, 2, { statuses: st(["stun"]) })], 6, 4);
  const r = await show(v0);
  return async () => {
    const frozen = { ...v0, units: v0.units.map((u) => (u.id === "u_a" ? { ...u, statuses: st(["frozen"]) } : u)) } as BattleView;
    const a = [
      { seq: 1, round: 2, type: "attack_rolled", attacker_id: HERO, target_id: "u_a", hit: false },
      { seq: 2, round: 2, type: "status_applied", target_id: "u_a", status_id: "frozen", duration: 1, refreshed: false, source_id: HERO },
    ];
    const b = [{ seq: 3, round: 2, type: "attack_rolled", attacker_id: "u_c", target_id: "u_b", hit: false }];
    await Promise.all([play(r, v0, [step(HERO, a, frozen)]), play(r, v0, [step("u_c", b, v0)])]);
  };
}

const HOLY_CARD = { id: "sk", shape: "方陣", skeleton: "area", effect_ids: ["damage"], icon: { segments: [{ skeleton: "area", shape_id: "square3", range: 4, effects: [{ type: "damage" }] }] } } as unknown as SkillCard;

/** 3. 聖光爆發打在左上角：光柱裁在地圖內；範圍預覽只畫地圖內的格子。 */
async function clipScene(): Promise<() => Promise<void>> {
  caption("3・範圍技裁在地圖內（巡檢 bug 13）：聖光爆發（方陣）打在左上角，光柱不畫到地圖外；橘色是範圍預覽（含地圖外的格子也只畫地圖內）");
  const v0 = battle([heroAt(2, 3), foeAt("u_a", 0, 0), foeAt("u_b", 1, 0)], 6, 5);
  const r = await show(v0);
  const preview = [-1, 0, 1].flatMap((dx) => [-1, 0, 1].map((dy) => ({ x: dx, y: dy })));
  const highlight = () =>
    r.setHighlights({ moves: [], attacks: [], directions: [], preview, telegraph: [], focus: null, hover: null, overlays: [], picked: [] });
  highlight();
  return async () => {
    const tiles = preview.filter((p) => p.x >= 0 && p.y >= 0);
    const events = [
      { seq: 1, round: 2, type: "skill_used", unit_id: HERO, skill_id: "sk", tiles },
      { seq: 2, round: 2, type: "damage_dealt", target_id: "u_a", source_id: HERO, element: "holy", amount: 14, hp_before: 20, hp_after: 6 },
      { seq: 3, round: 2, type: "damage_dealt", target_id: "u_b", source_id: HERO, element: "holy", amount: 12, hp_before: 20, hp_after: 8 },
    ];
    await play(r, v0, [step(HERO, events, v0, "skill")], { sk: HOLY_CARD });
    highlight();
  };
}

/** 4. 倒地的我方（可復活）與倒地的敵人。 */
async function heartScene(): Promise<() => Promise<void>> {
  caption("4・復活愛心只在我方（巡檢 bug 14）：左＝倒地的隊友（可復活，綠色愛心）；右＝倒地的敵人（伺服器 revivable 也是真，6F-6 起畫成救不回來）");
  const v0 = battle(
    [heroAt(0, 1), unit("u_mate", "ally", 1, 1, { name_zh: "隊友", template_id: "hero_fighter", hp: 0, downed: true, revivable: true }), foeAt("u_a", 3, 1, { hp: 0, downed: true, revivable: true }), foeAt("u_b", 4, 1)],
    6,
    3,
  );
  await show(v0);
  return async () => undefined;
}

async function main(): Promise<void> {
  const scenes = [await stackScene(), await missScene(), await clipScene(), await heartScene()];
  for (;;) {
    await Promise.all(scenes.map((s) => s()));
    window.__f6Done = true;
    if (ONCE) return;
    await wait(1800);
  }
}

void main();
