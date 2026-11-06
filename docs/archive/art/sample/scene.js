// 對比用的展示場景（美術樣張，不接進遊戲）：一張 12×9 的地圖，盡量把所有地形、表面、高度、物件與單位種類放進來。
// 三種畫法（目前色塊、Kenney 資源包、程式繪製）都讀這一份資料，確保是「同一個戰鬥畫面」。
window.SCENE = {
  w: 12,
  h: 9,
  // . 石地  g 草地  d 泥土  # 牆  C 深淵  L 岩漿  I 冰窟（水）
  terrain: [
    "gggg...##...",
    "ggg....##...",
    "gg..dd......",
    "g..ddCC..LL.",
    ".....CC..LL.",
    "..II.CC.....",
    "..II....dd..",
    "g.......dd.g",
    "gg........gg",
  ],
  heights: [
    "000000000233",
    "000000000223",
    "000000000222",
    "000000000001",
    "000000000001",
    "000000000000",
    "000000000000",
    "110000000000",
    "111000000000",
  ],
  legend: { ".": "stone", g: "grass", d: "dirt", "#": "wall", C: "chasm", L: "lava", I: "ice_hole" },
  surfaces: [
    { x: 3, y: 1, s: "oil" }, { x: 4, y: 1, s: "oil" }, { x: 4, y: 2, s: "oil" },
    { x: 5, y: 1, s: "fire" }, { x: 5, y: 2, s: "fire" },
    { x: 0, y: 4, s: "water" }, { x: 1, y: 4, s: "water" }, { x: 1, y: 5, s: "water" },
    { x: 6, y: 6, s: "ice" }, { x: 7, y: 6, s: "ice" }, { x: 7, y: 7, s: "ice" },
    { x: 10, y: 6, s: "poison" }, { x: 10, y: 7, s: "poison" },
  ],
  objects: [
    { x: 5, y: 4, kind: "wooden_bridge" }, { x: 6, y: 4, kind: "wooden_bridge" },
    { x: 2, y: 2, kind: "crate" }, { x: 4, y: 6, kind: "crate" },
    { x: 6, y: 1, kind: "oil_barrel" }, { x: 4, y: 0, kind: "oil_barrel" },
    { x: 8, y: 5, kind: "stone_pillar" }, { x: 2, y: 7, kind: "stone_pillar" },
    { x: 9, y: 5, kind: "low_wall" }, { x: 10, y: 5, kind: "low_wall" },
    { x: 1, y: 1, kind: "fallen_log" },
    { x: 6, y: 7, kind: "earth_wall" },
    { x: 0, y: 0, kind: "dead_tree" },
  ],
  units: [
    { id: "A", marker: "A", template: "hero_mage", team: "ally", x: 2, y: 4, facing: "east", hp: 0.85, hero: true, active: true },
    { id: "B", marker: "B", template: "hero_fighter", team: "ally", x: 4, y: 4, facing: "east", hp: 0.6 },
    { id: "C", marker: "C", template: "hero_archer", team: "ally", x: 1, y: 7, facing: "north", hp: 1 },
    { id: "S", marker: "骷", template: "summon_skeleton_warrior", team: "ally", x: 3, y: 3, facing: "east", hp: 0.7, summon: true },
    { id: "a", marker: "a", template: "bandit", team: "enemy", x: 7, y: 4, facing: "west", hp: 0.45 },
    { id: "b", marker: "b", template: "bandit_archer", team: "enemy", x: 10, y: 1, facing: "west", hp: 1 },
    { id: "c", marker: "c", template: "bandit_boss", team: "enemy", x: 9, y: 7, facing: "west", hp: 0.9 },
    { id: "d", marker: "d", template: "bandit_shieldbearer", team: "enemy", x: 7, y: 2, facing: "south", hp: 0.75 },
  ],
};

window.SCENE_UTIL = (() => {
  const S = window.SCENE;
  const terrainAt = (x, y) => (x < 0 || y < 0 || x >= S.w || y >= S.h ? null : S.legend[S.terrain[y][x]]);
  const heightAt = (x, y) => (x < 0 || y < 0 || x >= S.w || y >= S.h ? 0 : Number(S.heights[y][x]));
  const surfaceAt = (x, y) => S.surfaces.find((s) => s.x === x && s.y === y)?.s ?? null;
  const objectAt = (x, y) => S.objects.find((o) => o.x === x && o.y === y) ?? null;
  const BLOCKED = new Set(["wall", "chasm", "lava", "ice_hole"]);
  const DEADLY = new Set(["chasm", "lava", "ice_hole"]);
  const FLAMMABLE = new Set(["crate", "oil_barrel", "fallen_log", "wooden_bridge", "dead_tree"]);
  const FACING = { north: [0, -1], east: [1, 0], south: [0, 1], west: [-1, 0] };
  // 與 client/src/battle/facing.ts 的 facingArrow 相同
  function facingArrow(facing, r, size = 6) {
    const [dx, dy] = FACING[facing];
    const tip = { x: dx * (r + size), y: dy * (r + size) };
    const base = { x: dx * (r - 1), y: dy * (r - 1) };
    const side = { x: -dy * size, y: dx * size };
    return [tip.x, tip.y, base.x + side.x, base.y + side.y, base.x - side.x, base.y - side.y];
  }
  const hex = (n) => "#" + n.toString(16).padStart(6, "0");
  function hpColor(r) {
    return r > 0.5 ? "#4caf50" : r > 0.25 ? "#e0a030" : "#e04040";
  }
  return { terrainAt, heightAt, surfaceAt, objectAt, BLOCKED, DEADLY, FLAMMABLE, FACING, facingArrow, hex, hpColor };
})();
