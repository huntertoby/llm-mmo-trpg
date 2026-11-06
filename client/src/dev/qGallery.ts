// 開發用：Q 版 3 倍特寫（QK-1；`doll-gallery.html?skin=q&set=key|parts[&only=r01,b]`）。
// 和 docs/art/sample/tools/closeups.html 同一組格子（key 95、parts 62）、同一個版面、同一套樣張顏色，
// 每格一張畫布，另輸出 `<pre data-file>` 的 data URL（無頭 Chrome --dump-dom ＋ closeups_save.py 存成 PNG），左右並排對照 docs/art/closeup/。
import type { QLook, QPose, QUnit, QView } from "../render/qCore";
import { Q_RACES } from "../render/qRace";
import { SAMPLE_HOOKS, SAMPLE_IDLE, SAMPLE_ITEMS as IT, SAMPLE_TEMPLATES as TPL, SAMPLE_WEAPON_ZH, sampleHitPose, sampleUnit as U } from "../render/qSample";
import { qStamp } from "../render/qStamp";
import type { Facing } from "../api/types";
import { gaitPose } from "../render/motionClips";
import { drawFigurePose } from "../render/paperdoll";
import { resolveDollT } from "../render/testDolls";
import type { DollSpec } from "../render/appearance";

const Z = 3;
const FONT = "'Noto Sans TC','Microsoft JhengHei',sans-serif";
interface Cell {
  file: string;
  title: string;
  u: QUnit;
  v?: QView;
  w?: boolean;
  p?: QPose | null;
  K: number;
  W: number;
  H: number;
  fy: number;
  cx?: number;
  row?: boolean;
}
const VZ: ReadonlyArray<readonly [QView, boolean, string, string]> = [
  ["front", false, "正面", "front"],
  ["back", false, "背面", "back"],
  ["side", false, "朝東", "east"],
  ["side", true, "朝西", "west"],
];
const REST: QPose = { bob: 0, lean: 0, hipN: 0, hipF: 0, kneeN: 0, kneeF: 0, arm: 0, liftL: 0, liftR: 0, armL: 0, armR: 0, pull: 0 };

function keyCells(): Cell[] {
  const out: Cell[] = [];
  const cell = (file: string, title: string, u: QUnit, v: QView, w: boolean, p: QPose | null, K: number, W: number, H: number, fy: number, cx?: number): void =>
    void out.push({ file, title, u, v, w, p, K, W, H, fy, cx: cx ?? W / 2 });
  const ROWS: ReadonlyArray<readonly [number, string, string, QUnit]> = [
    [1, "劍類：雙手劍・拄劍", "gs-plant", U("greatsword")],
    [3, "長柄：長槍", "spear", U("spear")],
    [4, "長柄：鐮", "scythe", U("scythe")],
    [5, "弓", "bow", U("bow")],
    [6, "弩與槍：弩", "crossbow", U("crossbow")],
    [7, "弩與槍：火槍", "gun", U("gun")],
    [8, "法杖（單手）", "staff", U("staff")],
    [9, "單手加副手：劍盾", "sword-shield", { look: TPL.hero_fighter.look, gear: { ...TPL.hero_fighter.gear, cloak: undefined } } as QUnit],
    [10, "單手加副手：杖＋書", "staff-book", TPL.hero_mage],
  ];
  for (const [r, zh, f, u] of ROWS) for (const [v, w, t, e] of VZ) cell(`r${String(r).padStart(2, "0")}_${f}_${e}`, `${zh}・${t}`, u, v, w, null, 3.4, 240, 224, 202);
  const BOWS: ReadonlyArray<readonly [string, QPose, string]> = [
    ["待機", { nock: 1 }, "idle"],
    ["待機・抬一下", { nock: 1, arm: -0.3, dw: -0.2 }, "idle-lift"],
    ["拉弓 1/3", { bowAim: 0.4, pull: 1 }, "draw1"],
    ["拉弓 2/3", { bowAim: 0.8, pull: 2.5 }, "draw2"],
    ["拉滿", { bowAim: 1, pull: 4 }, "full"],
    ["放箭", { bowAim: 1, pull: 0 }, "release"],
  ];
  BOWS.forEach(([t, p, f], i) => cell(`b${i + 1}_bow_${f}`, `弓・${t}（朝東）`, U("bow"), "side", false, { ...REST, ...p }, 3.4, 200, 230, 200));
  const AK = ["sword", "saber", "arcane_blade", "paired", "spear", "scythe", "whip", "gauntlet", "staff", "orb", "bow", "crossbow", "gun", "greatsword"];
  AK.forEach((k, i) => {
    const QATK = ["greatsword", "spear", "scythe", "gun", "crossbow"].includes(k);
    const P: QPose = k === "bow" ? { ...REST, bowAim: 1, pull: 4 } : QATK ? { ...REST, atk: 1, lean: 0.12, hipN: 0.4, hipF: -0.3 } : { ...REST, ...sampleHitPose(k) };
    cell(`a${String(i + 1).padStart(2, "0")}_${k}`, `出招・${SAMPLE_WEAPON_ZH[k]}（朝東）`, U(k), "side", false, P, 2.9, 248, 235, 205, 70);
  });
  const G: ReadonlyArray<readonly [string, number, string, string]> = [
    ["greatsword", 0, "雙手劍・蓄力", "gs-windup"],
    ["greatsword", 0.5, "雙手劍・舉到臉前上方", "gs-raise"],
    ["greatsword", 1, "雙手劍・命中", "gs-hit"],
    ["spear", 0, "長槍・收", "spear-ready"],
    ["spear", 1, "長槍・刺出", "spear-thrust"],
    ["scythe", 0, "鐮・舉起", "scythe-raise"],
    ["scythe", 1, "鐮・收割", "scythe-reap"],
    ["gun", 0, "火槍・持槍", "gun-ready"],
    ["gun", 1, "火槍・瞄準", "gun-aim"],
  ];
  G.forEach(([k, t, zh, f], i) => cell(`g${i + 1}_${f}`, `${zh}（朝東）`, U(k), "side", false, { ...REST, atk: t }, 2.9, 248, 225, 200, 70));
  const IK = ["sword", "sword_shield", "saber", "arcane_blade", "paired", "spear", "scythe", "whip", "gauntlet", "staff", "orb", "bow", "crossbow", "gun", "greatsword"];
  const IZ: Record<string, string> = { ...SAMPLE_WEAPON_ZH, sword_shield: "劍盾" };
  IK.forEach((k, i) => {
    const u: QUnit = k === "sword_shield" ? { look: U("sword").look, gear: { ...U("sword").gear, off_hand: IT.round_shield } } : U(k);
    const I = SAMPLE_IDLE[k]!;
    for (const [t, zh, f] of [[0, "開頭", "start"], [I.mid ?? 0.5, "中段", "mid"]] as const) {
      const p = I.pose(t);
      cell(`i${String(i + 1).padStart(2, "0")}_${k}_${f}`, `待機・${IZ[k]}・${zh}（朝東）`, u, "side", false, { ...REST, ...p }, 2.9, 190, 262, 238, 60);
    }
  });
  return out;
}

function partCells(): Cell[] {
  const out: Cell[] = [];
  let sec = 0;
  const section = (title: string, rows: ReadonlyArray<readonly [string, QUnit]>, K = 3.2): void => {
    sec++;
    const W = (1240 / 2 - 80) / 4;
    const RH = Math.round(66 * K);
    rows.forEach(([zh, u], i) => out.push({ file: `s${String(sec).padStart(2, "0")}_${String(i + 1).padStart(2, "0")}`, title: `${title.split(" ")[0]} ${zh}`, u, row: true, K, W, H: RH, fy: RH - 22 }));
  };
  const BASE: QLook = { skin: "#f1c9a5", hair: "short", hairColor: "#6a3d1e" };
  const SHIRT: QUnit["gear"] = { body: { kind: "shirt", color: "#4f7fbf" }, feet: { kind: "boots", material: "leather" } };
  const HAIRS = [["短髮", "short"], ["長髮", "long"], ["齊肩", "bob"], ["馬尾", "ponytail"], ["雙馬尾", "twin"], ["刺蝟", "spiky"], ["髮髻", "bun"], ["光頭", "none"]] as const;
  section("1. 髮型", HAIRS.map(([zh, h]) => [zh, { look: { ...BASE, hair: h, hairColor: h === "long" ? "#c8c0b0" : BASE.hairColor }, gear: SHIRT }]), 3.2);
  const HATS = [["兜帽", "hood", { color: "#3f6a32" }], ["頭盔", "helmet", { material: "steel" }], ["角盔", "horned_helm", { material: "iron" }], ["巫師帽", "wizard_hat", { color: "#5a3fa0" }], ["便帽", "cap", { color: "#6a4a2e" }], ["頭巾", "bandana", { color: "#b33a3a" }], ["頭冠", "circlet", { material: "gold" }], ["寬帽", "wide_hat", { color: "#8a6a3a" }], ["面紗", "veil", { color: "#d8d0c0" }], ["護目鏡", "goggles", {}], ["王冠", "crown", { material: "gold" }], ["全罩盔", "greathelm", { material: "steel" }]] as const;
  section("2. 頭飾", HATS.map(([zh, k, m]) => [zh, { look: { ...BASE, hair: k === "hood" ? "long" : "short" }, gear: { ...SHIRT, head: { slot: "head", kind: k, ...m } } }]), 3.2);
  const SH = (extra: QUnit["gear"] = {}): QUnit["gear"] => ({ ...SHIRT, ...extra });
  const RACE_GEAR: QUnit["gear"] = { body: { kind: "leather", color: "#6a5040" }, feet: { kind: "boots", material: "leather" } };
  section("3. 10 族", Q_RACES.map(([, zh, look]) => [zh, { look, gear: RACE_GEAR }]), 3.0);
  const fox = Q_RACES.find(([k]) => k === "fox")![2];
  const EARS = [["狐", "fox", "#d8762a"], ["貓", "cat", "#3a2a24"], ["狼", "wolf", "#8a8a94"], ["兔", "rabbit", "#e8e0c8"]] as const;
  section("4. 獸耳族", EARS.map(([zh, k, hc]) => [`${zh}耳・${zh}尾`, { look: { ...fox, beastEars: k, hairColor: hc }, gear: RACE_GEAR }]), 3.0);
  section(
    "5. 衣服前後片、腰帶與帶扣、胸前紋章",
    [
      ["襯衫＋腰帶扣", { look: BASE, gear: SH() }],
      ["皮甲（斜背帶）", { look: BASE, gear: SH({ body: { kind: "leather", material: "leather" } }) }],
      ["鎖甲＋紋章", { look: BASE, gear: SH({ body: { kind: "mail", material: "iron", crest: "#2f5fae" } }) }],
      ["板甲（肩甲、胸口高光）＋紋章", { look: BASE, gear: SH({ body: { kind: "plate", material: "steel", crest: "#a32a2a" } }) }],
      ["長袍（前襟）", { look: { ...BASE, trim: "#e8bb48" }, gear: SH({ body: { kind: "robe", color: "#5a3fa0" } }) }],
      ["外套（領口、扣子）", { look: BASE, gear: SH({ body: { kind: "coat", color: "#4a5058" } }) }],
    ],
    3.0,
  );
  section(
    "6. 護甲與手腳",
    [
      ["護腕＋皮靴", { look: BASE, gear: SH({ hands: { kind: "bracers", material: "leather" } }) }],
      ["手套", { look: BASE, gear: SH({ hands: IT.gloves }) }],
      ["鐵手套＋脛甲", { look: BASE, gear: SH({ body: { kind: "plate", material: "steel" }, hands: IT.gauntlets, feet: IT.greaves }) }],
      ["拳套（武器）", { look: BASE, gear: SH({ main_hand: { slot: "main_hand", kind: "gauntlet", material: "steel" } }) }],
    ],
    3.0,
  );
  section("7. 披風、斗篷", [["藍披風", { look: BASE, gear: SH({ cloak: IT.blue_cape }) }], ["紅披風＋鎖甲", { look: BASE, gear: SH({ body: { kind: "mail", material: "iron" }, cloak: IT.red_cape }) }]], 3.0);
  section(
    "8. 背掛：箭袋、背包、卷軸筒",
    [
      ["箭袋", { look: BASE, gear: SH({ back: { kind: "quiver", material: "leather" } }) }],
      ["背包", { look: BASE, gear: SH({ back: { kind: "backpack", material: "leather" } }) }],
      ["卷軸筒", { look: BASE, gear: SH({ back: { kind: "scroll_case", color: "#7a2a3a" } }) }],
    ],
    3.0,
  );
  section("9. 腰掛：劍鞘（左腰）、腰包（右腰）", [["劍鞘", { look: BASE, gear: SH({ waist: { kind: "scabbard", material: "leather" } }) }], ["腰包", { look: BASE, gear: SH({ waist: { kind: "pouch", material: "leather" } }) }]], 3.0);
  section("10. 頸飾：項鍊、念珠", [["項鍊", { look: BASE, gear: SH({ neck: { kind: "necklace", material: "gold" } }) }], ["念珠", { look: BASE, gear: SH({ neck: { kind: "beads", color: "#8a5a32" } }) }]], 3.0);
  section(
    "11. 副手物品：圓盾、鳶盾、聖盾、塔盾、書",
    [
      ["圓盾", { look: BASE, gear: SH({ main_hand: IT.sword, off_hand: IT.round_shield }) }],
      ["鳶盾", { look: BASE, gear: SH({ main_hand: IT.sword, off_hand: IT.kite_shield }) }],
      ["聖盾", { look: BASE, gear: SH({ main_hand: IT.sword, off_hand: IT.holy_shield }) }],
      ["塔盾", { look: BASE, gear: SH({ main_hand: IT.sword, off_hand: { slot: "off_hand", kind: "shield_kite", form: "tower", material: "wood", color: "#6a4a2e" } }) }],
      ["書", { look: BASE, gear: SH({ main_hand: IT.fire_staff, off_hand: IT.tome }) }],
    ],
    2.2,
  );
  section(
    "12. 鬍子、睫毛",
    [
      ["大鬍子", { look: { ...BASE, beardStyle: "full" }, gear: SH() }],
      ["山羊鬍", { look: { ...BASE, beardStyle: "goatee" }, gear: SH() }],
      ["八字鬍", { look: { ...BASE, beardStyle: "mustache" }, gear: SH() }],
      ["睫毛＋大眼", { look: { ...BASE, lashes: true, eyeStyle: "big", hair: "long" }, gear: SH() }],
    ],
    3.0,
  );
  return out;
}

export function qCells(set: string): Cell[] {
  return set === "parts" ? partCells() : keyCells();
}

/** 畫一格（版面同 closeups.html）。 */
export function renderCell(c: Cell, noline = false): HTMLCanvasElement {
  const views: ReadonlyArray<readonly [QView, boolean, string]> = c.row ? VZ.map(([v, w, t]) => [v, w, t] as const) : [[c.v ?? "front", c.w ?? false, ""]];
  const W = (c.row ? c.W * 4 + 40 : c.W) * Z;
  const H = c.H * Z + 28;
  const cv = document.createElement("canvas");
  cv.width = W;
  cv.height = H;
  const x = cv.getContext("2d")!;
  x.fillStyle = "#2a2e40";
  x.fillRect(0, 0, W, H);
  x.fillStyle = "#e8bb48";
  x.font = `26px ${FONT}`;
  x.fillText(c.title, 12, 32);
  views.forEach(([v, w, t], j) => {
    const cx = (c.row ? 20 + c.W * j + c.W / 2 : (c.cx ?? c.W / 2)) * Z;
    const fy = c.fy * Z;
    x.beginPath();
    x.ellipse(cx, fy, (38 * Z * c.K) / 3.4, 7 * Z, 0, 0, Math.PI * 2);
    x.fillStyle = "rgba(0,0,0,0.25)";
    x.fill();
    qStamp(x, c.u, v, cx, fy, c.K * Z, w, SAMPLE_HOOKS, c.p ?? null, noline ? { outline: false } : {});
    if (t) {
      x.fillStyle = "#b8ab96";
      x.font = `22px ${FONT}`;
      x.textAlign = "center";
      x.fillText(t, cx, H - 8);
      x.textAlign = "left";
    }
  });
  return cv;
}

/** 走路四方向連拍（遊戲的畫法：drawFigurePose＋6M-3 走路片段 gaitPose）：4 種人 × 4 朝向 × 8 格，2 倍。 */
function walkSheet(): HTMLCanvasElement {
  const Zw = 2;
  const CW = 48;
  const CH = 64;
  const FR = 8;
  const base = (template: string): DollSpec => resolveDollT({ team: "ally", summon: false, template, weaponId: "one_handed_sword" });
  const withMain = (template: string, main: DollSpec["gear"]["main_hand"], off?: DollSpec["gear"]["off_hand"]): DollSpec => {
    const b = base(template);
    return { ...b, gear: { ...b.gear, main_hand: main, off_hand: off } };
  };
  const units: ReadonlyArray<readonly [string, DollSpec]> = [
    ["劍盾", base("hero_fighter")],
    ["法師", withMain("hero_mage", { kind: "staff", material: "wood", element: "fire" }, { kind: "tome", material: "leather", color: "#7a2a3a" })],
    ["弓手", withMain("hero_archer", { kind: "bow", material: "wood" })],
    ["雙手劍", withMain("hero_fighter", { kind: "greatsword", material: "steel" })],
  ];
  const facings: Facing[] = ["south", "north", "east", "west"];
  const cv = document.createElement("canvas");
  cv.width = (CW * FR + 60) * Zw;
  cv.height = CH * facings.length * units.length * Zw;
  const x = cv.getContext("2d")!;
  x.fillStyle = "#2a2e40";
  x.fillRect(0, 0, cv.width, cv.height);
  units.forEach(([zh, spec], ui) =>
    facings.forEach((f, fi) => {
      const row = ui * facings.length + fi;
      x.fillStyle = "#e8bb48";
      x.font = `${11 * Zw}px ${FONT}`;
      x.fillText(zh, 4 * Zw, (row * CH + 26) * Zw);
      x.fillStyle = "#b8ab96";
      x.fillText(f, 4 * Zw, (row * CH + 40) * Zw);
      for (let i = 0; i < FR; i++) {
        x.save();
        x.scale(Zw, Zw);
        x.translate(60 + CW * i + CW / 2, row * CH + CH - 10);
        drawFigurePose(x, spec, f, false, true, gaitPose((i / FR) * Math.PI * 2, "walk"));
        x.restore();
      }
    }),
  );
  return cv;
}

/** `doll-gallery.html?skin=q&set=key|parts|walk&only=r01,b&noline=1&dump=1`。 */
export function runQGallery(): void {
  const q = new URLSearchParams(location.search);
  const set = q.get("set") ?? "key";
  if (set === "walk") {
    const cv = walkSheet();
    const pre = document.createElement("pre");
    pre.dataset["file"] = "walk";
    pre.textContent = cv.toDataURL("image/png");
    document.body.appendChild(q.get("dump") === "1" ? pre : cv);
    const done = document.createElement("p");
    done.id = "done";
    document.body.appendChild(done);
    return;
  }
  const only = q.get("only");
  const noline = q.get("noline") === "1";
  const dump = q.get("dump") === "1";
  const h = document.createElement("h2");
  h.textContent = `Q 版 3 倍特寫（${set}）`;
  document.body.appendChild(h);
  const cells = qCells(set).filter((c) => !only || only.split(",").some((o) => c.file.startsWith(o)));
  for (const c of cells) {
    const cv = renderCell(c, noline);
    if (dump) {
      const pre = document.createElement("pre");
      pre.dataset["file"] = c.file;
      pre.textContent = cv.toDataURL("image/png");
      document.body.appendChild(pre);
    } else {
      cv.style.width = `${cv.width / 3}px`;
      cv.title = c.file;
      document.body.appendChild(cv);
    }
  }
  const done = document.createElement("p");
  done.id = "done";
  done.textContent = String(cells.length);
  document.body.appendChild(done);
}
