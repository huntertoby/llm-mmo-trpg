// 開發用：召喚物外觀一覽（Phase 3-33h1）。開 `client/summon-gallery.html`（pnpm dev 後 /summon-gallery.html）。
// 不屬於正式 build；供美術 PM 驗收與截圖。用真正的 BattleRenderer 畫：17 種 × 4 朝向、整格抬高與遮擋剪影、不認得的值。
// `#名稱` 只顯示該段（south／north／east／west／height／unknown）。
import { parse } from "yaml";
import type { BattleView, Glossary, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { tile, unit } from "../battle/testFixtures";
import { BattleRenderer } from "../render/BattleRenderer";

setGlossary(glossary as unknown as Glossary);

const files = import.meta.glob("../../../content/summon_looks.yaml", { query: "?raw", import: "default", eager: true }) as Record<string, string>;
const raw = Object.values(files)[0] ?? "";
interface Look {
  zh: string;
  body: string;
  variant?: string;
  element?: string;
  size?: string;
  trait?: string;
}
const LOOKS = Object.entries((parse(raw) as { looks: Record<string, Look> }).looks);

const ONLY = decodeURIComponent(location.hash.slice(1));
const COLS = 6;
const HERO = "unit_0001";

function baseView(width: number, height: number, tiles: TileView[], units: UnitView[]): BattleView {
  return {
    team: "ally",
    map_id: "gallery",
    map_name_zh: "召喚物一覽",
    width,
    height,
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

function summonUnit(i: number, x: number, y: number, l: Look, facing: UnitView["facing"]): UnitView {
  return unit(`unit_${String(10 + i).padStart(4, "0")}`, "ally", x, y, {
    template_id: `gallery_${i}`,
    name_zh: l.zh,
    owner_id: HERO,
    summon_expires_round: 5,
    facing,
    weapon_id: "one_handed_sword",
    summon_look: { body: l.body, variant: l.variant ?? null, element: l.element ?? null, size: l.size ?? "medium", trait: l.trait ?? null },
  });
}

function hero(x: number, y: number, facing: UnitView["facing"]): UnitView {
  return unit(HERO, "ally", x, y, { template_id: "hero_fighter", name_zh: "戰士", facing });
}

async function scene(title: string, key: string, view: BattleView, names: string[] = []): Promise<void> {
  if (ONLY !== "" && ONLY !== key) return;
  const box = document.createElement("div");
  box.className = "scene";
  const h = document.createElement("h2");
  h.textContent = title;
  box.appendChild(h);
  document.body.appendChild(box);
  const renderer = new BattleRenderer();
  await renderer.init(box);
  renderer.setScale(2.8);
  renderer.draw(buildDrawModel(view, HERO));
  if (names.length > 0) {
    const row = document.createElement("div");
    row.className = "names";
    for (const n of names) row.appendChild(Object.assign(document.createElement("span"), { textContent: n }));
    box.appendChild(row);
  }
}

function flat(rows: number): TileView[] {
  const tiles: TileView[] = [];
  for (let y = 0; y < rows; y++) for (let x = 0; x < COLS; x++) tiles.push(tile(x, y));
  return tiles;
}

async function facingScene(facing: UnitView["facing"]): Promise<void> {
  const rows = Math.ceil((LOOKS.length + 1) / COLS);
  const units: UnitView[] = [hero(0, 0, facing)];
  LOOKS.forEach(([, l], i) => units.push(summonUnit(i, (i + 1) % COLS, Math.floor((i + 1) / COLS), l, facing)));
  const names = ["戰士（對照）", ...LOOKS.map(([, l]) => l.zh)];
  await scene(`17 種外觀・朝向 ${facing}`, facing, baseView(COLS, rows, flat(rows), units), names);
}

async function heightScene(): Promise<void> {
  // 第 0 排平地（被第 1 排的高台擋住 → 畫剪影）、第 1 排高 2 的高台（單位一起抬高）、第 2 排平地
  const tiles = flat(3);
  for (const t of tiles) if (t.y === 1) t.height = 2;
  const ids = ["golem", "hawk", "war_wolf", "war_totem", "fire_spirit", "shade"];
  const look = (id: string): Look => LOOKS.find(([k]) => k === id)?.[1] ?? { zh: id, body: "" };
  const units: UnitView[] = [hero(5, 2, "north")];
  ids.forEach((id, i) => units.push(summonUnit(i, i, 0, look(id), "south")));
  ids.forEach((id, i) => units.push(summonUnit(i + 6, i, 1, look(id), "south")));
  ids.slice(0, 5).forEach((id, i) => units.push(summonUnit(i + 12, i, 2, look(id), "south")));
  await scene("整格抬高與遮擋剪影（上排被高台擋住、中排站在高台上、下排平地）", "height", baseView(COLS, 3, tiles, units));
}

async function unknownScene(): Promise<void> {
  const bad: Look[] = [
    { zh: "未知體型", body: "dragon" },
    { zh: "未知款式", body: "beast", variant: "dragon" },
    { zh: "未知元素", body: "spirit", element: "plasma" },
    { zh: "未知大小", body: "construct", variant: "golem", size: "gigantic" },
    { zh: "未知特徵", body: "totem", variant: "war", trait: "weird" },
    { zh: "空體型", body: "" },
  ];
  const units: UnitView[] = [hero(0, 1, "east")];
  bad.forEach((l, i) => units.push(summonUnit(i, i, 0, l, "south")));
  units.push(unit("unit_0099", "ally", 1, 1, { template_id: "summon_skeleton_warrior", name_zh: "沒有外觀欄位", owner_id: HERO, summon_expires_round: 5 }));
  await scene("不認得的值與沒有外觀欄位的召喚物（第二排第二格）", "unknown", baseView(COLS, 2, flat(2), units), bad.map((l) => l.zh));
}

for (const f of ["south", "north", "east", "west"] as const) await facingScene(f);
await heightScene();
await unknownScene();
