// 開發用：武器小圖示一覽（Phase 3T-4b）。開 `client/weaponicon-gallery.html`（pnpm dev 後 /weaponicon-gallery.html）。
// `?px=28` 改圖示邊長（預設 96，供截圖對照；英雄面板實際是 28）。不屬於正式 build。
import type { GearItem } from "../render/appearance";
import { weaponItemIconCanvas } from "../render/weaponIcon";

const M = (kind: string, material: string, rest: Partial<GearItem> = {}): GearItem => ({ kind, material, ...rest });
/** 全部武器 kind 與主要形制。 */
const WEAPONS: readonly (readonly [string, GearItem])[] = [
  ["sword", M("sword", "steel")], ["arcane", M("sword", "steel", { form: "arcane" })], ["greatsword", M("greatsword", "steel")],
  ["dagger", M("dagger", "steel")], ["axe", M("axe", "steel")], ["hammer", M("hammer", "iron")], ["mace", M("hammer", "iron", { form: "mace" })],
  ["spear", M("spear", "steel")], ["halberd", M("spear", "steel", { form: "halberd" })], ["bow", M("bow", "wood")],
  ["crossbow", M("crossbow", "wood")], ["longgun", M("longgun", "iron")], ["staff", M("staff", "wood")],
  ["fire_staff", M("staff", "wood", { element: "fire" })], ["scepter", M("staff", "wood", { form: "scepter" })],
  ["totem", M("staff", "wood", { form: "totem" })], ["pistol", M("pistol", "iron")], ["shotgun", M("shotgun", "iron")],
  ["fist", M("fist", "iron")], ["scythe", M("scythe", "steel")], ["whip", M("whip", "leather")], ["ice_sword", M("sword", "steel", { element: "ice" })],
];

const px = Number(new URLSearchParams(location.search).get("px") ?? 96);
const row = document.createElement("div");
row.className = "row";
for (const [id, item] of WEAPONS) {
  const box = document.createElement("div");
  box.className = "cell";
  const art = weaponItemIconCanvas(item, px);
  if (art !== null) {
    const c = document.createElement("canvas");
    c.width = px * 2;
    c.height = px * 2;
    c.style.width = `${px}px`;
    c.style.height = `${px}px`;
    c.getContext("2d")?.drawImage(art, 0, 0);
    box.appendChild(c);
  }
  const t = document.createElement("div");
  t.textContent = id;
  box.appendChild(t);
  row.appendChild(box);
}
document.body.appendChild(row);
