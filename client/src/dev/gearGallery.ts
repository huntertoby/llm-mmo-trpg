// 開發用：裝備圖示一覽（Phase 3G-G5a）。開 `client/gear-gallery.html`（pnpm dev 後 /gear-gallery.html）。
// 不屬於正式 build（vite build 只打包 index.html）；供美術 PM 驗收與截圖。
import appearance from "../render/gearAppearance.json";
import { gearIconCanvas, gearKinds, type GearLook } from "../render/gearIcon";

function cell(look: GearLook, px: number, label: string): HTMLElement {
  const box = document.createElement("div");
  box.className = "cell";
  const art = gearIconCanvas(look, px);
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
  t.textContent = label;
  box.appendChild(t);
  return box;
}

function section(title: string, cells: HTMLElement[]): void {
  const h = document.createElement("h2");
  h.textContent = title;
  const row = document.createElement("div");
  row.className = "row";
  for (const c of cells) row.appendChild(c);
  document.body.append(h, row);
}

const SLOT_TITLE: Record<string, string> = { weapon: "主手", offhand: "副手", body: "身體", head: "頭", hands: "手", feet: "腳", neck: "項鍊", ring: "戒指" };
for (const slot of Object.keys(SLOT_TITLE)) {
  const cells: HTMLElement[] = [];
  for (const k of gearKinds().filter((x) => x.slotType === slot)) {
    for (const f of k.forms) cells.push(cell({ kind: k.id, form: f.id }, 64, `${k.zh}・${f.zh}`));
  }
  section(`① ${SLOT_TITLE[slot]}（預設材質）`, cells);
}
section("② 材質 10 種（劍／匕首／短袍）", appearance.materials.flatMap((m) => [cell({ kind: "sword", material: m }, 64, `劍 ${m}`), cell({ kind: "dagger", material: m }, 64, `匕首 ${m}`)]));
section("③ 染色 8 種（皮背心／布袍／鐵劍不變色）", appearance.dyes.flatMap((d) => [cell({ kind: "leather", dye: d }, 64, `皮 ${d}`), cell({ kind: "robe", dye: d }, 64, `布 ${d}`), cell({ kind: "sword", dye: d }, 64, `鐵 ${d}`)]));
section("④ 關鍵字 10 種（劍／圓盾；晶石匕首遇元素換色）", appearance.keywords.flatMap((k) => [cell({ kind: "sword", keywords: [k] }, 64, `劍 ${k}`), cell({ kind: "round_shield", keywords: [k] }, 64, `盾 ${k}`), cell({ kind: "dagger", material: "crystal", keywords: [k] }, 64, `晶 ${k}`)]));
section("④b 兩個關鍵字各畫一處", [cell({ kind: "sword", keywords: ["ignite", "marked"] }, 64, "劍 ignite+marked"), cell({ kind: "staff", form: "scepter", keywords: ["frozen", "summon"] }, 64, "權杖 frozen+summon"), cell({ kind: "mail", keywords: ["wet", "high_ground"] }, 64, "鎖甲 wet+high_ground")]);
section("⑤ 稀有度 5 種", appearance.rarities.flatMap((r) => [cell({ kind: "axe", rarity: r }, 64, `斧 ${r}`), cell({ kind: "axe", rarity: r }, 32, `32px ${r}`)]));
section("⑥ 成對武器與特殊", [cell({ kind: "dual_dagger" }, 64, "雙匕首"), cell({ kind: "dual_pistol", form: "revolver" }, 64, "雙手槍"), cell({ kind: "longgun", form: "sniper" }, 64, "狙擊火槍"), cell({ kind: "staff", form: "totem", material: "wood" }, 64, "圖騰杖"), cell({ kind: "???" }, 64, "不認得→劍")]);
const mixed: GearLook = { kind: "plate", form: "full", material: "steel", rarity: "epic", keywords: ["ignite", "prone"] };
const mixed2: GearLook = { kind: "bow", form: "recurve", rarity: "rare", keywords: ["charged"] };
const mixed3: GearLook = { kind: "robe", dye: "purple", rarity: "legendary", keywords: ["frozen", "summon"] };
section("⑦ 三種尺寸（64／48／32px；≤36px 不畫小圖樣）", [mixed, mixed2, mixed3].flatMap((l) => [64, 48, 32].map((px) => cell(l, px, `${l.kind} ${px}px`))));
