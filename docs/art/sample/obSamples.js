// #150（開局先玩再定）與 #147（工坊靶場測試模式）三項介面樣張的共用畫法與資料。
// 給 ob-range-class.html、ob-range-entry.html、practice-battle.html 用；紀錄在 docs/art/OB與PR樣張.md。
// 框、按鈕、字級直接載入現行的 client/src/styles/index.css（只讀），這裡只補樣張新增的 ob-* 元件與圖。
// 人物 QDoll.stamp／QNpc.stamp，頭像 QPortrait.portrait，武器 GearArt.draw，技能 SkillIcon.draw，
// 背景 WorldPaintedArt.drawBackdrop、TownTiles、CUR.drawTile；木樁、滑軌、水池石緣、武器架照 range.html（#134 已定案）。
window.OB = (() => {
  const TAU = Math.PI * 2, DPR = 3;
  const QS = new URLSearchParams(location.search);

  // ---------------- 區域主題（照 client/src/ui/regionCorners.ts 與 content/ui/region_themes.yaml） ----------------
  const THEMES = {
    capital: { accent: "#a898ff", corner: "filigree", ring: "#a898ff", ink: "#22305a", seal: "#7a5ad0", top: "#2a2a5a", bottom: "#1a1a3a" },
    cloud_ridge: { accent: "#6aa84a", corner: "cloud", ring: "#6aa84a", ink: "#1c1712", seal: "#b8432f", top: "#2f4a3a", bottom: "#1f3428" },
  };
  function cornerShapes(kind, c) {
    if (kind === "cloud") return `<path d="M4 10A6 6 0 0 1 15.4 7.4" fill="none" stroke="${c.accent}" stroke-width="1.6" stroke-linecap="round"/><path d="M12 5A3 3 0 0 1 17.5 4" fill="none" stroke="${c.accent}" stroke-width="1.6" stroke-linecap="round"/><path d="M6 14A3 3 0 0 1 6 8" fill="none" stroke="${c.accent}" stroke-width="1.2" stroke-linecap="round"/><circle cx="4" cy="4" r="2.5" fill="${c.seal}"/>`;
    return `<path d="M0 16Q0 0 16 0" fill="none" stroke="#e8bb48" stroke-width="1.6"/><path d="M7 2L10 7L7 12L4 7Z" fill="${c.accent}" stroke="#f2eaff" stroke-width="0.6"/>`;
  }
  function cornerLayers(kind, c, scale = 1) {
    const S = 18, size = Math.round(S * scale * 10) / 10;
    const POS = { tl: "left 2px top 2px", tr: "right 2px top 2px", bl: "left 2px bottom 2px", br: "right 2px bottom 2px" };
    return Object.keys(POS).map((at) => {
      const sx = at === "tr" || at === "br" ? -1 : 1, sy = at === "bl" || at === "br" ? -1 : 1;
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}" viewBox="0 0 ${S} ${S}"><g transform="translate(${sx < 0 ? S : 0} ${sy < 0 ? S : 0}) scale(${sx} ${sy})">${cornerShapes(kind, c)}</g></svg>`;
      return `url("data:image/svg+xml,${encodeURIComponent(svg)}") ${POS[at]} / ${size}px ${size}px no-repeat`;
    }).join(", ");
  }
  function applyTheme(id, el = document.documentElement) {
    const t = THEMES[id];
    const vars = { "--rt-accent": t.accent, "--rt-ring": t.ring, "--rt-ink": t.ink, "--rt-seal": t.seal, "--rt-plaque-top": t.top, "--rt-plaque-bottom": t.bottom, "--rt-corners": cornerLayers(t.corner, t), "--rt-corners-small": cornerLayers(t.corner, t, 0.7) };
    for (const [k, v] of Object.entries(vars)) el.style.setProperty(k, v);
    if (el === document.documentElement) el.dataset.region = id;
  }

  // ---------------- DOM 小工具 ----------------
  function h(tag, attrs = {}, ...kids) {
    const [name, ...cls] = tag.split(".");
    const el = document.createElement(name || "div");
    if (cls.length) el.className = cls.join(" ");
    for (const [k, v] of Object.entries(attrs ?? {})) {
      if (v == null || v === false) continue;
      if (k === "class") el.className += (el.className ? " " : "") + v;
      else if (k === "style") el.style.cssText = v;
      else if (k === "html") el.innerHTML = v;
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat(Infinity)) if (kid != null && kid !== false) el.append(kid);
    return el;
  }
  function cv(w, hh, draw, cls) {
    const c = document.createElement("canvas");
    c.width = Math.round(w * DPR); c.height = Math.round(hh * DPR); c.style.width = w + "px"; c.style.height = hh + "px";
    if (cls) c.className = cls;
    const x = c.getContext("2d"); x.scale(DPR, DPR); draw(x, w, hh); return c;
  }
  // 共用彈窗元件 PopupFrame（inline）與入口畫面的框
  const popup = (cls, ...kids) => h("div.ui-popup.rt-frame.ui-popup-inline", { class: cls, "data-popup": "inline" }, h("div.ui-popup-body", {}, ...kids));
  const entryPanel = (cls, ...kids) => popup("entry-panel " + (cls ?? ""), ...kids);
  const entryPlaque = (heading, sub) => popup("entry-plaque", h("h1.entry-plaque-title", {}, heading), sub ? h("div.entry-plaque-sub", {}, sub) : null);
  function entryShell(cls, ...kids) {
    const back = document.createElement("canvas"); back.className = "entry-backdrop-layer"; WorldPaintedArt.drawBackdrop(back, 0);
    return h("div.entry-skin", { class: cls }, h("div.entry-backdrop", { "aria-hidden": "true" }, h("div.entry-backdrop-sticky", {}, back, h("div.entry-backdrop-veil"))), h("div.entry-page", {}, ...kids));
  }
  const line = (who, text) => h("p.world-opening-line", {}, h("b", {}, who), "：" + text);

  // ---------------- 圖：人物、頭像、武器、技能 ----------------
  const HERO_LOOK = { skin: "#f1c9a5", hair: "short", hairColor: "#3a2414" };
  const HERO_GEAR = { body: { kind: "leather", color: "#2f5a5a" }, feet: { kind: "boots", material: "leather" } };
  // 入門武器（content/world/newcomer.yaml range.starters；外觀照 content/weapons.yaml 的 look）
  const WEAPON = {
    one_handed_sword: { name: "單手劍", look: { kind: "sword", material: "steel" }, icon: { kind: "sword", material: "steel" } },
    bow: { name: "弓", look: { kind: "bow", material: "wood" }, icon: { kind: "bow", material: "wood" } },
    fire_staff: { name: "火焰法杖", look: { kind: "staff", material: "wood", element: "fire" }, icon: { kind: "staff", material: "wood", keywords: ["ignite"] } },
  };
  const hero = (weaponId) => ({ look: HERO_LOOK, gear: weaponId ? { ...HERO_GEAR, main_hand: WEAPON[weaponId].look } : HERO_GEAR });
  /** Q 版人物（QDoll.stamp）。view：front｜side｜back；west＝朝西。腳底在畫布下緣上方 foot px。 */
  function doll(unit, view, size, w, hh, opt = {}) {
    return cv(w, hh, (x) => {
      const cx = w / 2 + (opt.dx ?? 0), cy = hh - (opt.foot ?? 10);
      x.fillStyle = "rgba(0,0,0,0.28)"; x.beginPath(); x.ellipse(cx, cy, 11 * size, 3.2 * size, 0, 0, TAU); x.fill();
      (opt.npc ? QNpc : QDoll).stamp(x, unit, view, cx, cy, size, !!opt.west, { dpr: DPR });
    }, opt.cls ?? "ob-doll");
  }
  const npcRow = (id) => QPortrait.N.find((n) => n[0] === id);
  const npcUnit = (id) => QPortrait.bodyUnit(npcRow(id));
  /** NPC 頭像（QPortrait.portrait，框色＝區域色）。 */
  const portrait = (id, size) => cv(size, size, (x) => QPortrait.portrait(x, 0, 0, size, npcRow(id)), "ob-portrait");
  /** 武器圖示（GearArt.draw，64 單位座標）。 */
  const gearIcon = (item, size) => cv(size, size, (x) => { x.scale(size / 64, size / 64); GearArt.draw(x, item, size <= 36); }, "ob-gear-icon");
  // 示範招＝入門招（content/world/newcomer.yaml range.demos）。圖示規格照 tools/export_skills.py 的格式，內容讀自 content/skills/*.yaml。
  const SK = (id, name, rarity, weapon_req, elements, skeleton, shape, range, effects, tags) => ({ id, name, kind: "active", rarity, weapon_req, elements, element: elements[0], skeleton, shape, range, effects, condition: null, cost: {}, activation: null, trigger: null, reaction: null, tags });
  const SKILL = {
    skill_shadow_backstab: SK("skill_shadow_backstab", "瞬步背刺", "rare", "melee", ["physical"], "strike", "single", 4, [{ type: "shadowstep" }, { type: "damage" }, { type: "damage", condition: "from_behind" }], ["physical", "melee", "mobility", "stealth"]),
    skill_tower_slam: SK("skill_tower_slam", "塔盾猛擊", "rare", "melee", ["physical"], "strike", "single", "weapon", [{ type: "damage" }, { type: "knock_prone", condition: "wielding_weapon" }], ["physical", "melee", "knockdown"]),
    skill_scatter_shot: SK("skill_scatter_shot", "散彈驅離", "rare", "ranged", ["physical"], "strike", "single", "weapon", [{ type: "damage" }, { type: "push", condition: "wielding_weapon" }], ["physical", "ranged", "displace"]),
    skill_suppressing_fire: SK("skill_suppressing_fire", "壓制射擊", "rare", "ranged", ["physical"], "strike", "single", "weapon", [{ type: "damage" }, { type: "apply_status", status: "slow", condition: "wielding_weapon" }], ["physical", "ranged", "control"]),
    skill_fire_bolt: SK("skill_fire_bolt", "火焰箭", "common", "focus", ["fire"], "strike", "single", 5, [{ type: "damage" }, { type: "apply_status", status: "burning" }], ["fire", "spell", "burn"]),
    skill_spark_chain: SK("skill_spark_chain", "火花連鎖", "rare", "focus", ["lightning"], "area", "chain", 4, [{ type: "damage" }], ["lightning", "spell", "chain"]),
  };
  /** 技能圖示（SkillIcon.draw，現行 C 墨線圖示，不改畫）。 */
  function skillIcon(id, size) {
    const c = document.createElement("canvas"); SkillIcon.draw(c, SKILL[id], size * 1.5);
    c.style.width = size + "px"; c.style.height = size + "px"; c.className = "ob-skill-icon"; return c;
  }

  // ---------------- 內容（武器、招名讀自 content；台詞照玩法 PM 的「台詞-150與147.md」） ----------------
  // 說明句（desc）與一句定位（tag）是樣張暫寫，待玩法 PM 定稿；入門武器下塔盾猛擊、散彈驅離、壓制射擊只剩傷害（盤點第 0 節），所以不寫擊倒、推開、緩速。
  const CLASSES = [
    { id: "melee", name: "近戰", tag: "貼身打", weapon: "one_handed_sword", skills: [["skill_shadow_backstab", "閃到目標背後再刺，從背後打更痛", "AP 2・耐力 10"], ["skill_tower_slam", "重重砸一下，傷害高", "AP 2・耐力 8"]] },
    { id: "ranged", name: "遠程", tag: "遠遠射", weapon: "bow", skills: [["skill_scatter_shot", "一發重擊，傷害高", "AP 2・耐力 8"], ["skill_suppressing_fire", "瞄準再射，傷害高", "AP 2・耐力 8"]] },
    { id: "focus", name: "法器", tag: "施法", weapon: "fire_staff", skills: [["skill_fire_bolt", "一道火箭，讓目標燃燒", "AP 1・法力 5"], ["skill_spark_chain", "電弧打中後，再跳到旁邊一個目標", "AP 1・法力 5"]] },
  ];
  const LINES = {
    intro: ["醒了？先別急著走。空手出去，雲嶺的霧會把你吞掉。", "這裡是工坊靶場。架上的武器隨便拿，打打木樁。想貼身打、遠遠射，還是施法？先挑一條路。"],
    loan: "手上這套是借你的。等你摸清路數，葛蘭會幫你換上真正順手的。",
    done: "好，先走這條路試試。站上傳送陣，去雲嶺的霧渡鎮找渡婆婆——第一趟不收錢。",
    back: "木樁隨你打，傷不了你，也不收錢。看看你現在的本事。",
    gran1: "竹林那一仗打得不錯。來，該挑你自己的兵器了。",
    gran2: "架上的都能拿，再選兩個路數。我標了適合你的，不照著選也行。",
  };

  // ---------------- 靶場的物件：木樁、滑軌、水池石緣（照 range.html，#134 已定案的畫法，原樣搬過來） ----------------
  const glow = (x, cx, cy, r, col, a = 1) => { const g = x.createRadialGradient(cx, cy, 0, cx, cy, r); g.addColorStop(0, col); g.addColorStop(1, "rgba(0,0,0,0)"); x.save(); x.globalAlpha = a; x.fillStyle = g; x.beginPath(); x.arc(cx, cy, r, 0, TAU); x.fill(); x.restore(); };
  /** 木樁 training_dummy：底座、木樁、橫臂、麻布身、布頭；hit＝被打中閃白。 */
  function dummy(c, cx, cy, k = 1, hit = false) {
    const { ink, stroke, ellPts } = StoryDoll.H;
    c.save(); c.translate(cx, cy); c.scale(k, k);
    c.fillStyle = "rgba(0,0,0,0.25)"; c.beginPath(); c.ellipse(0, 2, 16, 5, 0, 0, TAU); c.fill();
    ink(c, "dm-base", [[-12, 0], [12, 0], [9, -6], [-9, -6]], "#6a4a2a", { w: 0.9 });
    ink(c, "dm-post", [[-3, -6], [3, -6], [3, -34], [-3, -34]], "#9a7046", { w: 0.9 });
    ink(c, "dm-arm", [[-16, -30], [16, -30], [16, -26], [-16, -26]], "#8a6038", { w: 0.8 });
    ink(c, "dm-body", [[-9, -34], [9, -34], [10, -16], [-10, -16]], "#c8b080", { w: 0.9 });
    for (const y of [-30, -24, -19]) stroke(c, "dm-rope" + y, [[-9, y], [9, y]], 0.6, "#7a5a32");
    ink(c, "dm-head", ellPts(0, -42, 8, 8, 14), "#d8c49a", { w: 0.9 }); stroke(c, "dm-x1", [[-3, -45], [-1, -43]], 0.8, "#5a3a20"); stroke(c, "dm-x2", [[1, -45], [3, -43]], 0.8, "#5a3a20");
    if (hit) glow(c, 0, -30, 24, "rgba(220,245,255,0.75)");
    c.restore();
  }
  /** 滑軌：兩條鐵軌加枕木，從 (x0, y) 到 (x1, y)（像素）。 */
  function rail(c, x0, x1, y) {
    const { ink, stroke } = StoryDoll.H;
    for (let x = x0 + 8; x < x1 - 4; x += 26) ink(c, "tie" + x, [[x - 4, y - 12], [x + 4, y - 12], [x + 4, y + 12], [x - 4, y + 12]], "#7a5a38", { w: 0.6, shade: false, sharp: true });
    for (const dy of [-6, 6]) stroke(c, "rail" + dy, [[x0, y + dy], [x1, y + dy]], 2.4, "#5a5a64");
  }
  /** 水池石緣：水面 (x, y, w, h)（像素）外圍一圈石條（四條，各自墨線描邊，接縫用短線）。 */
  function poolRim(c, x, y, w, hh) {
    const { ink, stroke } = StoryDoll.H, o = 9, COL = "#b8b0a0", HI = "#d0c8b8";
    const slab = (id, x0, y0, x1, y1, col) => ink(c, "pool-" + id, [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], col, { w: 0.8, shade: false, sharp: true });
    slab("n", x - o, y - o, x + w + o, y, HI); slab("s", x - o, y + hh, x + w + o, y + hh + o, COL);
    slab("w", x - o, y, x, y + hh, COL); slab("e", x + w, y, x + w + o, y + hh, COL);
    for (let k = 1; k < 4; k++) { const px = x - o + ((w + 2 * o) * k) / 4; stroke(c, "pool-jn" + k, [[px, y - o + 1.5], [px, y - 1.5]], 0.7, "#6a6458"); stroke(c, "pool-js" + k, [[px, y + hh + 1.5], [px, y + hh + o - 1.5]], 0.7, "#6a6458"); }
    for (let k = 1; k < 3; k++) { const py = y + (hh * k) / 3; stroke(c, "pool-jw" + k, [[x - o + 1.5, py], [x - 1.5, py]], 0.7, "#6a6458"); stroke(c, "pool-je" + k, [[x + w + 1.5, py], [x + w + o - 1.5, py]], 0.7, "#6a6458"); }
  }

  // ---------------- ③ 測試模式的戰場（現行地磚 CUR.drawTile＋Q 版主角＋木樁三種） ----------------
  const BOARD = { cols: 12, rows: 8, T: 52, hero: [3, 4], rail: { y: 2, x0: 6, x1: 10 }, pool: { x: 8, y: 4, w: 2, h: 2 }, dummies: [{ at: [8, 2], kind: "rail" }, { at: [9, 5], kind: "pool" }, { at: [6, 6], kind: "plain" }] };
  function boardCanvas(scale, opt = {}) {
    const B = BOARD, T = B.T, W = B.cols * T, H = B.rows * T;
    return cv(W * scale, H * scale, (x) => {
      x.scale(scale, scale);
      const inPool = (gx, gy) => gx >= B.pool.x && gx < B.pool.x + B.pool.w && gy >= B.pool.y && gy < B.pool.y + B.pool.h;
      const terr = (gx, gy) => (gy === 0 ? "wall" : "stone"), surf = (gx, gy) => (inPool(gx, gy) ? "water" : "none");
      for (let gy = 0; gy < B.rows; gy++) for (let gx = 0; gx < B.cols; gx++) {
        const t = terr(gx, gy), s = surf(gx, gy), same = (a, b) => surf(a, b) === s, diff = (a, b) => a >= 0 && a < B.cols && b >= 0 && b < B.rows && terr(a, b) !== t;
        x.save(); x.translate(gx * T, gy * T);
        CUR.drawTile(x, { terrain: t, x: gx, y: gy, height: 0, surface: s, surfSame: { n: same(gx, gy - 1), s: same(gx, gy + 1), w: same(gx - 1, gy), e: same(gx + 1, gy) }, lip: { n: diff(gx, gy - 1), s: diff(gx, gy + 1), w: diff(gx - 1, gy), e: diff(gx + 1, gy) }, wallFace: t === "wall", blocked: t === "wall", tint: null });
        x.restore();
      }
      rail(x, B.rail.x0 * T + 6, (B.rail.x1 + 1) * T - 6, (B.rail.y + 0.62) * T);
      poolRim(x, B.pool.x * T, B.pool.y * T, B.pool.w * T, B.pool.h * T);
      // 可攻擊的目標：紅框（現行戰場的畫法：圓角紅框）；hover 的那個加粗加亮
      const frame = (gx, gy, hot) => { x.save(); x.lineJoin = "round"; x.strokeStyle = "rgba(20,10,10,0.7)"; x.lineWidth = hot ? 6 : 4.6; x.beginPath(); x.roundRect(gx * T + 3, gy * T + 3, T - 6, T - 6, 7); x.stroke(); x.strokeStyle = hot ? "#ff5a4a" : "#e0483c"; x.lineWidth = hot ? 3.6 : 2.6; x.stroke(); if (hot) { x.fillStyle = "rgba(255,90,74,0.16)"; x.fill(); } x.restore(); };
      if (opt.targets) B.dummies.forEach((d) => frame(d.at[0], d.at[1], opt.hover === d.kind));
      // 依 y 排序畫單位
      const units = [...B.dummies.map((d) => ({ y: d.at[1], draw: () => dummy(x, (d.at[0] + 0.5) * T, (d.at[1] + 0.86) * T, 0.86, opt.hit === d.kind) })),
        { y: B.hero[1], draw: () => {
          const cx = (B.hero[0] + 0.5) * T, cy = (B.hero[1] + 0.84) * T;
          x.fillStyle = "rgba(47,125,225,0.32)"; x.strokeStyle = "#2f7de1"; x.lineWidth = 2; x.beginPath(); x.ellipse(cx, cy, 17, 6.5, 0, 0, TAU); x.fill(); x.stroke();
          x.fillStyle = "#fff"; x.strokeStyle = "#16121a"; x.lineWidth = 1; x.beginPath(); x.moveTo(cx + 25, cy); x.lineTo(cx + 19, cy - 4); x.lineTo(cx + 19, cy + 4); x.closePath(); x.fill(); x.stroke();
          QDoll.stamp(x, hero(opt.weapon ?? "bow"), "side", cx, cy, 1.12, false, { dpr: DPR * Math.max(1, scale) });
          x.fillStyle = "#16121a"; x.beginPath(); x.roundRect(cx - 19, cy + 9, 38, 6, 2); x.fill(); x.fillStyle = "#3ad06a"; x.beginPath(); x.roundRect(cx - 18, cy + 10, 36, 4, 1.5); x.fill();
        } }].sort((a, b) => a.y - b.y);
      units.forEach((u) => u.draw());
      if (opt.dmg) { const d = B.dummies.find((q) => q.kind === opt.dmg[0]); x.save(); x.lineJoin = "round"; x.font = "bold 20px 'Noto Sans TC','Microsoft JhengHei',sans-serif"; x.textAlign = "center"; x.strokeStyle = "#2b1e16"; x.lineWidth = 4; x.fillStyle = "#ff5a5a"; const tx = (d.at[0] + 0.5) * T, ty = (d.at[1] - 0.12) * T; x.strokeText(opt.dmg[1], tx, ty); x.fillText(opt.dmg[1], tx, ty); x.restore(); }
    }, "ob-board");
  }

  // ---------------- ② 兩個場景：主城工坊靶場（城鎮圖庫 TownTiles，照 range.html 的擺法）、霧渡鎮導師堂（照 gran-doll.html） ----------------
  const RACKS = [["近戰", [{ kind: "sword", material: "steel" }, { kind: "axe", material: "steel" }, { kind: "spear", material: "iron" }, { kind: "hammer", material: "iron" }]],
    ["遠程", [{ kind: "bow", material: "wood" }, { kind: "crossbow", material: "wood" }, { kind: "gun", material: "steel" }]],
    ["法器", [{ kind: "staff", material: "wood" }, { kind: "staff", material: "crystal" }, { kind: "orb" }]]];
  /** 人物站在格子 (gx, gy)（腳底在格子下緣上方一點），Q 版。 */
  function person(c, T, gx, gy, unit, view, west, npc, k = 1.25) {
    const cx = (gx + 0.5) * T, cy = (gy + 0.86) * T;
    c.fillStyle = "rgba(0,0,0,0.26)"; c.beginPath(); c.ellipse(cx, cy, 12 * k, 3.6 * k, 0, 0, TAU); c.fill();
    (npc ? QNpc : QDoll).stamp(c, unit, view, cx, cy, k, !!west, { dpr: DPR });
  }
  /** 主城工坊靶場（23×12 格，T＝52）：白石地磚、工坊、三座武器架、滑軌、水池、木樁三個；工坊師傅與主角。回傳畫好的 canvas（寬 w、高 hh，置中裁切）。 */
  function capitalScene(w, hh, opt = {}) {
    const TT = TownTiles, E = Explore, T = 52, COLS = 23, ROWS = 12, k = Math.max(w / (COLS * T), hh / (ROWS * T)), { ink } = StoryDoll.H;
    return cv(w, hh, (c) => {
      c.translate((w - COLS * T * k) / 2, (hh - ROWS * T * k) / 2); c.scale(k, k);
      for (let gy = 0; gy < ROWS; gy++) for (let gx = 0; gx < COLS; gx++) TT.plaza(c, gx, gy);
      TT.stoneHall(c, 1, -1, 7, 3, { door: 3.5, windows: [1.2, 5.8], sign: "anvil" });
      rail(c, 12.4 * T, 18.6 * T, 10.5 * T);
      for (let gy = 6; gy < 8; gy++) for (let gx = 17; gx < 19; gx++) E.ground(c, "w", gx, gy);
      poolRim(c, 17 * T, 6 * T, 2 * T, 2 * T);
      RACKS.forEach(([zh, ws], i) => {
        const X = 1.2 * T, Y = (4.6 + i * 3) * T;
        c.fillStyle = "rgba(0,0,0,0.22)"; c.fillRect(X + 4, Y + 4, T * 3.8, 10);
        ink(c, "rk-top" + i, [[X, Y - 62], [X + T * 3.8, Y - 62], [X + T * 3.8, Y - 55], [X, Y - 55]], "#8a6038", { w: 0.9, shade: false, sharp: true });
        ink(c, "rk-bot" + i, [[X, Y - 6], [X + T * 3.8, Y - 6], [X + T * 3.8, Y], [X, Y]], "#7a5030", { w: 0.9, shade: false, sharp: true });
        for (const px of [X + 3, X + T * 3.8 - 8]) ink(c, "rk-leg" + px + i, [[px, Y - 66], [px + 5, Y - 66], [px + 5, Y + 4], [px, Y + 4]], "#6a4a2a", { w: 0.7, shade: false, sharp: true });
        ws.forEach((wp, j) => { c.save(); c.translate(X + 34 + j * T * 0.9, Y - 8); c.scale(2.4, 2.4); PaperDoll.drawWeapon(c, { slot: "main_hand", ...wp }, 0, true); c.restore(); });
        c.fillStyle = "rgba(16,18,34,0.88)"; c.beginPath(); c.roundRect(X + T * 1.3, Y + 8, 56, 22, 5); c.fill(); c.strokeStyle = "#c8a868"; c.lineWidth = 1; c.stroke();
        c.fillStyle = "#f2e6c8"; c.font = "bold 13px 'Noto Sans TC','Microsoft JhengHei',sans-serif"; c.textAlign = "center"; c.fillText(zh, X + T * 1.3 + 28, Y + 24); c.textAlign = "left";
      });
      dummy(c, 15.5 * T, 10.8 * T, 1.5); dummy(c, 18.5 * T, 7.7 * T, 1.5); dummy(c, 14.4 * T, 7.9 * T, 1.5);
      person(c, T, 9.2, 7.2, npcUnit("workshop_master"), "side", false, true, 1.5);
      person(c, T, 10.8, 7.2, hero(opt.weapon ?? "bow"), "side", true, false, 1.5);
    }, "ob-scene");
  }
  /** 霧渡鎮導師堂室內（12×8 格）：書架、石像、地毯、燭台；葛蘭與主角。 */
  function mentorScene(w, hh) {
    const TT = TownTiles, T = 52, COLS = 12, ROWS = 8, k = Math.max(w / (COLS * T), hh / (ROWS * T));
    return cv(w, hh, (c) => {
      c.fillStyle = "#14161c"; c.fillRect(0, 0, w, hh);
      c.translate((w - COLS * T * k) / 2, (hh - ROWS * T * k) / 2); c.scale(k, k);
      TT.room(c, 1, 0, 10, 7, "#3c4a48", "#b8aa8a"); TT.P.shelf(c, 2, 0, 2, ["#5a3a9a", "#3a5ad0", "#c83a2a", "#e8bb48"]); TT.P.shelf(c, 8, 0, 2, ["#3a5ad0", "#5a3a9a", "#6aa84a", "#e8bb48"]); TT.P.statue(c, 5.5, -0.4);
      TT.P.rug(c, 5, 2, 2, 4); for (const [gx, gy] of [[2, 3], [9, 3]]) TT.P.candle(c, gx, gy);
      person(c, T, 5.5, 2.9, npcUnit("gran"), "front", false, true, 1.3);
      person(c, T, 5.5, 5.4, hero("bow"), "back", false, false, 1.3);
    }, "ob-scene");
  }
  // 12 個關鍵字的小圖示（照 range.html／建角樣張那一組）
  const KW_COL = { 冰凍: "#8ad8ff", 點燃: "#ff8a3a", 帶電: "#ffe05a", 潮濕: "#4a9ae8", 中毒: "#7ac83a", 倒地: "#c8a868", 撞擊: "#d0d0d8", 標記: "#e05a5a", 高處: "#a8c8a8", 隱蔽: "#8a7ab8", 召喚物: "#a898ff", 形態: "#e8bb48" };
  function kwIcon(k, size = 22) {
    return cv(size, size, (x) => {
      const C = KW_COL[k]; x.translate(size / 2, size / 2); x.scale(size / 24, size / 24);
      x.fillStyle = "#161a2a"; x.beginPath(); x.arc(0, 0, 11, 0, TAU); x.fill(); x.strokeStyle = C; x.lineWidth = 1.6; x.stroke(); x.fillStyle = C; x.lineWidth = 1.5;
      ({ 冰凍: () => { for (let i = 0; i < 3; i++) { x.save(); x.rotate((i * Math.PI) / 3); x.beginPath(); x.moveTo(0, -6); x.lineTo(0, 6); x.stroke(); x.restore(); } },
        點燃: () => { x.beginPath(); x.moveTo(0, -7); x.quadraticCurveTo(6, 0, 3, 6); x.quadraticCurveTo(0, 8, -3, 6); x.quadraticCurveTo(-6, 0, 0, -7); x.fill(); },
        帶電: () => { x.beginPath(); x.moveTo(2, -7); x.lineTo(-3, 1); x.lineTo(1, 1); x.lineTo(-2, 7); x.lineTo(4, -1); x.lineTo(0, -1); x.closePath(); x.fill(); },
        潮濕: () => { x.beginPath(); x.moveTo(0, -7); x.quadraticCurveTo(6, 2, 0, 6); x.quadraticCurveTo(-6, 2, 0, -7); x.fill(); },
        中毒: () => { [[-2, 2, 3], [3, -1, 2.2], [0, -5, 1.6]].forEach(([a, b, r]) => { x.beginPath(); x.arc(a, b, r, 0, TAU); x.fill(); }); },
        倒地: () => { x.beginPath(); x.moveTo(-6, 4); x.lineTo(6, 4); x.stroke(); x.beginPath(); x.arc(-3, 0, 2.4, 0, TAU); x.fill(); x.fillRect(-1, -1, 7, 3); },
        撞擊: () => { for (let i = 0; i < 6; i++) { const a = (i / 6) * TAU; x.beginPath(); x.moveTo(Math.cos(a) * 2, Math.sin(a) * 2); x.lineTo(Math.cos(a) * 7, Math.sin(a) * 7); x.stroke(); } },
        標記: () => { x.beginPath(); x.arc(0, 0, 5.5, 0, TAU); x.stroke(); x.beginPath(); x.arc(0, 0, 1.8, 0, TAU); x.fill(); },
        高處: () => { x.beginPath(); x.moveTo(-6, 5); x.lineTo(0, -6); x.lineTo(6, 5); x.closePath(); x.fill(); },
        隱蔽: () => { x.beginPath(); x.ellipse(0, 0, 7, 4, 0, 0, TAU); x.stroke(); x.beginPath(); x.moveTo(-6, 5); x.lineTo(6, -5); x.stroke(); },
        召喚物: () => { x.beginPath(); x.arc(0, 0, 6, 0, TAU); x.stroke(); x.beginPath(); x.moveTo(0, -4); x.lineTo(3.5, 2); x.lineTo(-3.5, 2); x.closePath(); x.fill(); },
        形態: () => { x.beginPath(); x.moveTo(-6, 3); x.quadraticCurveTo(-3, -6, 0, 0); x.quadraticCurveTo(3, 6, 6, -3); x.stroke(); } })[k]();
    }, "keyword-icon");
  }
  /** 選單項目的小圖：木樁（靶場試玩用）。 */
  const dummyIcon = (size) => cv(size, size, (x) => { x.fillStyle = "#161a2a"; x.beginPath(); x.roundRect(0, 0, size, size, 8); x.fill(); x.strokeStyle = "rgb(200 168 104 / 55%)"; x.lineWidth = 1; x.beginPath(); x.roundRect(0.5, 0.5, size - 1, size - 1, 8); x.stroke(); dummy(x, size / 2, size * 0.9, size / 62); }, "ob-menu-icon");

  /** 樣張頁共用：依網址 ?state= 取狀態；頁面畫完在 <html> 標 data-ready，給截圖工具等。 */
  const param = (k, d) => QS.get(k) ?? d;
  function ready() { document.documentElement.dataset.ready = "1"; document.documentElement.dataset.h = String(Math.ceil(document.documentElement.scrollHeight)); }

  return { TAU, DPR, h, cv, popup, entryPanel, entryPlaque, entryShell, line, applyTheme, hero, doll, dummy, rail, poolRim, glow, boardCanvas, BOARD, capitalScene, mentorScene, kwIcon, dummyIcon, RACKS, npcUnit, npcRow, portrait, gearIcon, skillIcon, WEAPON, SKILL, CLASSES, LINES, HERO_LOOK, HERO_GEAR, param, ready };
})();
