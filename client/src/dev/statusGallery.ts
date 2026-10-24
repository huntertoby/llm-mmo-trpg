// 開發用：狀態圖示與身上特效一覽（Phase 3-36a）。開 `client/status-gallery.html`（pnpm dev 後 /status-gallery.html）。
// 不屬於正式 build；供美術 PM 驗收與截圖。上：32 個狀態＋不認得的值（對照 docs/art/status-icons.png）；下：用真正的 BattleRenderer
// 畫的 9×6 戰場（頭頂狀態列、+N、冰凍／暈眩／護盾／定身／持續傷害、隱蔽、上下相鄰單位的血條、倒下、灌注召喚物）。
import type { BattleView, Glossary, StatusView, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { buildDrawModel } from "../battle/drawModel";
import { setGlossary, statusName } from "../battle/glossary";
import { tile, unit } from "../battle/testFixtures";
import { BattleRenderer } from "../render/BattleRenderer";
import { waitForFonts } from "../render/fontLoad";
import { paintStatusIcon } from "../render/statusIcon";

const real = glossary as unknown as Glossary;
setGlossary(real);
await waitForFonts();

const HERO = "unit_0001";

function iconGrid(): void {
  const box = document.createElement("div");
  box.className = "scene";
  box.appendChild(Object.assign(document.createElement("h2"), { textContent: "32 個狀態＋不認得的值（圓＝增益、方＝減益、六角＝中性）" }));
  const grid = document.createElement("div");
  grid.className = "grid";
  const ids = [...real.statuses.map((s) => s.id), "brand_new_status", ""];
  for (const id of ids) {
    const cell = document.createElement("div");
    const canvas = document.createElement("canvas");
    canvas.width = 120;
    canvas.height = 120;
    const ctx = canvas.getContext("2d");
    if (ctx !== null) {
      ctx.scale(2, 2);
      paintStatusIcon(ctx, id, 30, 30, 52);
    }
    cell.append(canvas, Object.assign(document.createElement("span"), { textContent: id === "" ? "(空字串)" : id === "brand_new_status" ? "不認得" : statusName(id) }));
    grid.appendChild(cell);
  }
  box.appendChild(grid);
  document.body.appendChild(box);
}

const st = (...ids: string[]): StatusView[] => ids.map((status_id) => ({ status_id, remaining: 2, source_id: null, amount: null, charge_tiles: [], cost_status: false }));

function board(): BattleView {
  const tiles: TileView[] = [];
  for (let y = 0; y < 6; y++) for (let x = 0; x < 9; x++) tiles.push(tile(x, y));
  const u = (id: string, team: "ally" | "enemy", x: number, y: number, statuses: StatusView[], over: Partial<UnitView> = {}): UnitView =>
    unit(id, team, x, y, { statuses, name_zh: id, ...over });
  const units: UnitView[] = [
    u(HERO, "ally", 1, 1, st("hasted", "empowered"), { template_id: "hero_fighter" }),
    u("unit_0002", "enemy", 3, 1, st("frozen")),
    u("unit_0003", "enemy", 5, 1, st("stun")),
    u("unit_0004", "ally", 7, 1, st("shielded", "regenerating")),
    u("unit_0005", "enemy", 1, 3, st("root", "slow")),
    u("unit_0006", "enemy", 3, 3, st("burning", "poison", "bleed")),
    u("unit_0007", "ally", 5, 3, st("concealed")),
    u("unit_0008", "enemy", 7, 3, st("stun", "burning", "poison", "weaken", "hasted", "empowered", "stance_fury")),
    // 上下相鄰：上面的單位血條不該被下面的單位狀態列蓋住
    u("unit_0009", "ally", 1, 4, st("guarded"), { hp: 6 }),
    u("unit_0010", "enemy", 1, 5, st("marked", "revealed", "time_bomb"), { hp: 8 }),
    u("unit_0011", "enemy", 3, 4, st("stun"), { downed: true, hp: 0 }),
    u("unit_0012", "ally", 5, 5, st("stun", "shielded", "poison"), { owner_id: HERO, summon_expires_round: 5, infused_skill_id: "x" } as Partial<UnitView>),
    u("unit_0013", "enemy", 7, 5, st("brand_new_status")),
  ];
  return {
    team: "ally",
    map_id: "status_gallery",
    map_name_zh: "狀態一覽",
    width: 9,
    height: 6,
    tiles,
    objects: [],
    units,
    traps: [],
    turn_order: [HERO],
    active_unit: HERO,
    round: 2,
    max_rounds: 30,
    weather_id: null,
    weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null },
    ended: false,
    winner: null,
    end_reason: null,
    pending: null,
    source_wells: [],
    zones: [],
    runes: [],
  } as unknown as BattleView;
}

iconGrid();
const box = document.createElement("div");
box.className = "scene";
box.appendChild(Object.assign(document.createElement("h2"), { textContent: "戰場（9×6）：冰凍、暈眩、護盾、定身、燃燒／中毒、隱蔽、+N、上下相鄰、倒下、灌注召喚物" }));
document.body.appendChild(box);
const renderer = new BattleRenderer();
await renderer.init(box);
renderer.setScale(2);
renderer.draw(buildDrawModel(board(), HERO));
