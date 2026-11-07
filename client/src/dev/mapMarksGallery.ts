// 開發用：實地地圖標記（Phase 6C-8b）——情境物件提示（主角在 1 格內時金色虛線呼吸光＋小手）與敵群頭上的眼睛
// （放在單位圖實際頂端再往上 6px）。開 `client/dev/mapmarks-gallery.html`（pnpm dev 後 /dev/mapmarks-gallery.html）；不屬於正式 build。
// 用真正的 BattleRenderer、`fieldDrawModel`、`fieldHighlights` 畫；伺服器目前不給實地敵群外觀（`doll_look`），
// 所以大型異形與頭目的場景在這裡把外觀補到敵方單位上驗證眼睛高度。
import type { FieldView, Glossary } from "../api/types";
import type { DrawModel, UnitDraw } from "../battle/drawModel";

type DollLook = NonNullable<UnitDraw["dollLook"]>;
import glossary from "../battle/fixtures/glossary.json";
import { setGlossary } from "../battle/glossary";
import { BattleRenderer } from "../render/BattleRenderer";
import { waitForFonts } from "../render/fontLoad";
import { enemyUnitId, fieldDrawModel, fieldHighlights } from "../world/fieldModel";

setGlossary(glossary as unknown as Glossary);
await waitForFonts();

type Enemy = FieldView["enemies"][number];

function field(over: Partial<FieldView>): FieldView {
  const w = 9;
  const h = 6;
  const tiles = Array.from({ length: w * h }, (_, i) => ({ x: i % w, y: Math.floor(i / w), height: 0, terrain: "grass", surface: "none", walkable: true }));
  return {
    map_id: "gallery",
    name_zh: "標記",
    region: "frost",
    location: "gallery",
    interior: false,
    width: w,
    height: h,
    tiles,
    objects: [],
    exits: [],
    doors: [],
    stones: [],
    npcs: [],
    facilities: [],
    me: { x: 0, y: 0, facing: "e" },
    max_climb: 1,
    stone_targets: [],
    enemies: [],
    friends: [],
    campfires: [],
    event_mark: null,
    situation_objects: [],
    sneaking: false,
    sneak_cost: 1,
    sneak_problem_zh: null,
    footprints: [],
    note_stone: null,
    ...over,
  } as FieldView;
}

const enemy = (id: string, x: number, y: number, sight: Array<[number, number]>): Enemy => ({
  id,
  x,
  y,
  facing: "w",
  patrol: false,
  group: "g",
  name_zh: id,
  elite: false,
  units: [{ unit: id, name_zh: id, affix: null, elite: false, third: false }],
  sight,
});

const look = (creature: Record<string, unknown> | null): DollLook =>
  ({ skin: "#f1c9a5", skull: false, gear: {}, beard: false, affixes: [], traits: [], ...(creature === null ? {} : { creature: { traits: [], ...creature } }) }) as unknown as DollLook;

interface Scene {
  title: string;
  field: FieldView;
  looks?: Record<string, DollLook>;
}

const crate = (id: string, x: number, y: number) => ({ id, kind: "crate", x, y });
const sobj = (id: string, name: string, x: number, y: number) => ({ id, name_zh: name, x, y, use: "event", usable: true, note_zh: "", problem_zh: null });

const SCENES: Scene[] = [
  {
    title: "靠近情境物件：主角在木箱旁邊（左）有金色虛線圈＋小手；右邊的木箱離得遠，不畫",
    field: field({
      me: { x: 2, y: 3, facing: "e" },
      objects: [crate("o1", 3, 3), crate("o2", 7, 1)],
      situation_objects: [sobj("crate_near", "舊木箱", 3, 3), sobj("crate_far", "另一個木箱", 7, 1)],
    } as Partial<FieldView>),
  },
  {
    title: "敵群頭上的眼睛：人形、大型異形（傀儡 large）、頭目（熊 huge）、軟泥——都在單位圖頂端再往上 6px",
    field: field({
      me: { x: 0, y: 5, facing: "e" },
      enemies: [
        enemy("human", 1, 2, [[1, 3], [1, 4]]),
        enemy("golem", 3, 2, [[3, 3], [3, 4]]),
        enemy("bear", 5, 2, [[5, 3], [5, 4]]),
        enemy("ooze", 7, 2, [[7, 3], [7, 4]]),
      ],
    }),
    looks: {
      golem: look({ body: "golem", size: "large" }),
      bear: look({ body: "bear", size: "huge" }),
      ooze: look({ body: "ooze", size: "medium" }),
    },
  },
];

function withLooks(model: DrawModel, scene: Scene): DrawModel {
  const looks = scene.looks ?? {};
  const byUnit = new Map((scene.field.enemies ?? []).map((e) => [enemyUnitId(e), looks[e.id]]));
  return { ...model, units: model.units.map((u) => (byUnit.get(u.id) === undefined ? u : { ...u, dollLook: byUnit.get(u.id) ?? null })) };
}

const box = document.createElement("div");
document.body.appendChild(box);
for (const scene of SCENES) {
  const section = document.createElement("section");
  section.appendChild(Object.assign(document.createElement("h2"), { textContent: scene.title }));
  box.appendChild(section);
  const renderer = new BattleRenderer();
  await renderer.init(section);
  renderer.setScale(1.5);
  renderer.draw(withLooks(fieldDrawModel(scene.field), scene));
  renderer.setHighlights(fieldHighlights(scene.field, null));
}
