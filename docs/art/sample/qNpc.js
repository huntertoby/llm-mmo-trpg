// qNpc.js：NPC、人形敵人用的 Q 版新部件（畫圖 agent，2026-11-07）。
// 不改 qDoll.js：本體照 QDoll.stamp 畫（opts.outline:false 只取填色），新部件畫在本體後面（B 層）或前面（C 層），
// 三層合起來再做一次和 qDoll 同一套的「圓盤膨脹」剪影外框（1.3 單位），所以新部件和本體是同一圈外框、身上不多出內框線。
// 細線（傀儡線）、半透明（白紗）畫在外框之後（D 層），不被外框加粗。
// 座標：和 qDoll 同一套（腳底中心 (0,0)、頭心 (0,−29)、半徑 8.5、身高約 46）；先套種族 build（stout 1.12×0.88、tall 0.96×1.1），
//   側面一律用朝東畫、朝西鏡像，但「左右手、左右腰」照朝西換邊（朝西時左手、左腰在近側）。
// 手持物（拂塵、符紙、傀儡線）掛在 qDoll 回報的手的位置（setPose({hands})），四指橫過握柄、柄從拳頭上下穿出；劍穗掛在劍柄尾（setPose({probe})）。
// 確定性：沒有亂數。
window.QNpc = (() => {
  const TAU = Math.PI * 2, OUT = "#16121a", BOX = { W: 128, H: 112, FOOT: 14 };
  const Q = () => window.QDoll;
  const BUILD = { stout: [1.12, 0.88], tall: [0.96, 1.1] };
  const mix = (a, b, t) => { const p = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)); const A = p(a), B = p(b); return "#" + A.map((v, i) => Math.round(v + (B[i] - v) * t).toString(16).padStart(2, "0")).join(""); };
  const dk = (c, t = 0.3) => mix(c, "#000000", t);
  function fill(ctx, c, path) { ctx.fillStyle = c; ctx.beginPath(); path(); ctx.fill(); }
  function line(ctx, c, w, pts) { ctx.strokeStyle = c; ctx.lineWidth = w; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.stroke(); }
  const rr = (ctx, x, y, w, h, r) => ctx.roundRect(x, y, w, h, r);

  // ---------- 資料：content 的 snake_case → qDoll 的 camelCase；擴充 kind → 部件 ----------
  const CAMEL = { hair_color: "hairColor", bun_band: "bunBand", mark_color: "markColor", horn_color: "hornColor", eye_style: "eyeStyle", beard_style: "beardStyle" };
  function normLook(look) { if (!look) return {}; const o = {}; for (const [k, v] of Object.entries(look)) o[CAMEL[k] ?? k] = v; return o; }
  const HELD = ["whisk", "talisman", "puppet_strings"]; // qDoll 的手持物（新 gear kind，照持武器規則畫在手上）
  /** unit：{look, gear, extras?, parts?}。回傳 qDoll 認得的 unit 與新部件清單。portrait：頭像用（護目鏡戴在眼睛上，不推到額上）。 */
  function prep(unit, portrait = false) {
    const look = normLook(unit.look), gear = { ...(unit.gear ?? {}) }, parts = [...(unit.parts ?? [])];
    const P = (k, o = {}) => parts.push({ k, ...o });
    const b = gear.body;
    if (b?.apron) { gear.body = { ...gear.body }; P("apron", { color: b.apron }); }
    if (gear.back && ["gourd", "puppet_box", "mailbag"].includes(gear.back.kind)) { P(gear.back.kind, { color: gear.back.color }); delete gear.back; }
    if (gear.waist?.kind === "talismans") { P("talismans", { color: gear.waist.color }); delete gear.waist; }
    if (gear.head?.kind === "gauze") { P("gauze", { color: gear.head.color }); gear.head = { kind: "hood", color: gear.head.color ?? "#eef2f2" }; }
    if (gear.head?.kind === "douli") { P("douli", { color: gear.head.color }); delete gear.head; }
    // 白羽披肩：qDoll 的頸飾 neck feathers（畫在身體上、手臂與胸前武器下面）；不再另畫披風
    if (gear.cloak?.form === "feather") { gear.neck = { kind: "feathers", color: gear.cloak.color }; delete gear.cloak; }
    if (gear.main_hand?.tassel) P("tassel", { color: gear.main_hand.tassel });
    const skin = gear.hands && gear.hands.kind !== "bracers" ? null : look.skin;
    for (const slot of ["main_hand", "off_hand"]) {
      let it = gear[slot]; if (!it) continue;
      if (it.kind === "puppet_cross") it = { ...it, kind: "puppet_strings" };
      if (HELD.includes(it.kind)) { gear[slot] = { ...it, skin: it.skin ?? skin ?? "#f1c9a5" }; if (it.kind === "puppet_strings") P("strings", { who: slot }); }
    }
    // 頭像配件在全身上的對應（NPC頭像.md 4-5 表；Q 版補畫斗笠、頭帶、額上護目鏡、毛領，其他太小不畫）
    for (const e of unit.extras ?? []) {
      if (e === "wide_hat" && !gear.head) P("douli");
      else if (e === "headband" && !gear.head) P("headband");
      else if (e === "goggles_up") P("goggles_up", { cap: !!gear.head });
      else if (e === "goggles" && !gear.head) gear.head = { kind: "goggles" };
      else if (e === "goggles" && !portrait) P("goggles"); // 戴帽子時：護目鏡照樣戴在眼睛上（和頭像、content 一致），帽子照舊
      else if (e === "cap" && !gear.head) gear.head = { kind: "cap", color: "#3a2a1a" };
      else if (e === "bandana" && !gear.head) gear.head = { kind: "bandana", color: "#a83a2a" };
      else if (e === "fur_collar" && !gear.neck) gear.neck = { kind: "fur_collar" };
      else if (e === "mustache" && !look.beard) look.beardStyle = "mustache";
    }
    return { q: { look, gear, rarity: unit.rarity }, parts };
  }

  // ---------- 部件：每個都分 front / side（朝東座標）/ back；layer：B＝本體後、C＝本體前、D＝外框後（不描外框） ----------
  // near：側面時這個部件在近側嗎（左邊的東西朝東在遠側、朝西在近側）
  const headClip = (ctx) => { ctx.beginPath(); ctx.rect(-80, -120, 160, 200); ctx.arc(0, -29, 8.7, 0, TAU); ctx.clip("evenodd"); }; // 頭下面的部件：挖掉頭
  const PART = {
    // 圍裙（煉丹師；樣張建議：鐵匠皮圍裙、酒館老闆白圍裙）：正面胸到膝、頸帶；側面在前緣；背面只看到腰後的綁帶十字
    apron: { C(ctx, v, p) {
      const c = p.color ?? "#e8dcc0", d = dk(c, 0.25), e = p.edge ?? d; // edge：亮一階的邊（皮圍裙和深色皮衣分得開）
      if (v === "front") {
        fill(ctx, e, () => { ctx.moveTo(-4.3, -19.2); ctx.lineTo(4.3, -19.2); ctx.lineTo(5.1, -11); ctx.lineTo(6.3, -2.4); ctx.lineTo(-6.3, -2.4); ctx.lineTo(-5.1, -11); ctx.closePath(); });
        fill(ctx, c, () => { ctx.moveTo(-3.6, -18.6); ctx.lineTo(3.6, -18.6); ctx.lineTo(4.4, -11); ctx.lineTo(5.6, -3); ctx.lineTo(-5.6, -3); ctx.lineTo(-4.4, -11); ctx.closePath(); });
        line(ctx, e, 0.7, [[-3.6, -18.8], [-2.6, -20.8]]); line(ctx, e, 0.7, [[3.6, -18.8], [2.6, -20.8]]);
        if (p.pocket !== false) fill(ctx, d, () => rr(ctx, -2.2, -8, 4.4, 2.6, 0.6));
      } else if (v === "side") { // 側面：貼著身體前緣的一條（不凸出），腰後一個結
        fill(ctx, e, () => { ctx.moveTo(4.1, -18.8); ctx.lineTo(5.6, -18.8); ctx.lineTo(6.3, -9.6); ctx.lineTo(6.9, -2.8); ctx.lineTo(5.2, -2.8); ctx.lineTo(4.6, -9.6); ctx.closePath(); });
        fill(ctx, c, () => { ctx.moveTo(4.3, -18.4); ctx.lineTo(5.2, -18.4); ctx.lineTo(5.8, -9.6); ctx.lineTo(6.4, -3.2); ctx.lineTo(5.5, -3.2); ctx.lineTo(4.9, -9.6); ctx.closePath(); });
        line(ctx, e, 0.6, [[-5, -9.4], [4.6, -9.4]]); line(ctx, e, 0.6, [[4.6, -18.6], [1.6, -21]]);
      } else { // 背面：和正面同一種掛脖式，後面只看到脖子一條帶子與腰後的結
        line(ctx, e, 0.7, [[-3, -20.8], [0, -21.6], [3, -20.8]]);
        line(ctx, e, 0.7, [[-5.4, -9.4], [5.4, -9.4]]); fill(ctx, e, () => ctx.ellipse(0, -9.4, 1.2, 0.8, 0, 0, TAU)); line(ctx, e, 0.6, [[0, -9], [-0.8, -6.4]]); line(ctx, e, 0.6, [[0, -9], [0.9, -6.6]]);
      }
    } },
    // 背葫蘆：斜綁在背上，正面從左肩（畫面右）上方露出葫蘆口；背面整顆在背上；側面在背後凸出
    gourd: {
      B(ctx, v, p) { if (v === "back") return; const c = p.color ?? "#c8903a"; ctx.save(); if (v === "front") { ctx.translate(7.2, -24.6); ctx.rotate(0.45); } else { ctx.translate(-8.4, -15); ctx.rotate(-0.35); } gourdShape(ctx, c); ctx.restore(); },
      C(ctx, v, p) { if (v === "front") { line(ctx, "#8a3a2a", 0.9, [[6.4, -20.8], [-5.6, -10]]); return; } if (v === "side") { line(ctx, "#8a3a2a", 0.9, [[-1.6, -20.8], [4.6, -10.6]]); return; } const c = p.color ?? "#c8903a"; ctx.save(); headClip(ctx); ctx.translate(-3.2, -13.6); ctx.rotate(-0.42); gourdShape(ctx, c); ctx.restore(); line(ctx, "#8a3a2a", 0.9, [[-6.4, -20.8], [5.2, -9.6]]); }, /* 背面：左肩（畫面左）→ 右腰（畫面右），和正面同一條帶子 */
    },
    // 木偶箱：背上的方箱；正面箱頂兩角從肩後露出，背面整個箱子（箱門、朱紅繩），側面在背後
    puppet_box: { // 箱頂四面一致在 y −26
      B(ctx, v, p) { const c = p.color ?? "#8a6a48"; if (v === "front") { fill(ctx, c, () => rr(ctx, -11.6, -26, 23.2, 7, 1.2)); fill(ctx, dk(c), () => ctx.rect(-11.6, -26, 23.2, 1.4)); fill(ctx, "#c0392b", () => ctx.rect(-11.6, -22.6, 23.2, 0.9)); } else if (v === "side") { fill(ctx, c, () => rr(ctx, -15, -26, 9.4, 20, 1.2)); fill(ctx, dk(c), () => ctx.rect(-15, -26, 9.4, 1.4)); fill(ctx, "#c0392b", () => ctx.rect(-15, -22.6, 9.4, 0.9)); } },
      C(ctx, v, p) { const c = p.color ?? "#8a6a48", d = dk(c);
        if (v === "back") { ctx.save(); headClip(ctx); fill(ctx, c, () => rr(ctx, -9.6, -26, 19.2, 21, 1.2)); fill(ctx, d, () => ctx.rect(-9.6, -26, 19.2, 1.4)); fill(ctx, "#c0392b", () => ctx.rect(-9.6, -22.6, 19.2, 0.9)); line(ctx, d, 0.7, [[0, -21.6], [0, -6]]); fill(ctx, "#e8bb48", () => ctx.arc(-1.3, -14, 0.7, 0, TAU)); fill(ctx, "#e8bb48", () => ctx.arc(1.3, -14, 0.7, 0, TAU)); ctx.restore(); }
        else for (const s of v === "front" ? [-1, 1] : [1]) line(ctx, "#5a3a22", 1.1, v === "front" ? [[s * 4.6, -21], [s * 4.8, -11]] : [[-0.8, -21], [-0.6, -11]]); },
    },
    // 郵袋（郵寄外觀.md：米色帆布、斜背帶、黑扣）：左肩斜背到右腰，袋掛在右腰側後方。
    //   正面：袋在畫面左腰後，只從身體外側露一角；背面：袋在畫面右腰、看得到整個；朝東右腰在近側（腰後）；朝西右腰在遠側（身後露一點）
    mailbag: {
      B(ctx, v, p, u, W) { if (v === "front") bagShape(ctx, -12.6, -12.2, p.color, true); else if (v === "side" && W) bagShape(ctx, -11.2, -12.4, p.color, true); },
      C(ctx, v, p, u, W) { const s = "#6a4a2a";
        if (v === "front") line(ctx, s, 1.3, [[6.2, -20.6], [-6.4, -9.6]]);
        else if (v === "back") { line(ctx, s, 1.3, [[-6.2, -20.6], [4.6, -10]]); bagShape(ctx, 2.2, -12, p.color); }
        else if (!W) { line(ctx, s, 1.3, [[2.6, -20.8], [-3.6, -10.4]]); bagShape(ctx, -8.4, -12.2, p.color); }
        else line(ctx, s, 1.3, [[-1.6, -20.8], [4.8, -11]]); },
    },
    // 腰掛黃符：左腰三張黃符垂下（正面畫面右、背面畫面左；側面朝東在遠側被擋住、朝西在近側）
    talismans: { C(ctx, v, p, u, W) { const c = p.color ?? "#f2d860";
      const xs = v === "front" ? [2.8, 4.6, 6.4] : v === "back" ? [-6.4, -4.6, -2.8] : W ? [-3.8, -2, -0.2] : null; if (!xs) return;
      xs.forEach((x, i) => { const L = 5.6 - Math.abs(i - 1) * 0.9; fill(ctx, c, () => rr(ctx, x - 0.8, -8.4, 1.6, L, 0.3)); if (v !== "back") line(ctx, "#c0392b", 0.4, [[x, -7.6], [x, -8.4 + L - 1]]); });
    } },
    // 白紗面罩（霧行者）：qDoll 畫白兜帽，這裡加半透明面罩（眼睛以下），背面看不到
    gauze: { D(ctx, v, p) { if (v === "back") return; ctx.save(); ctx.globalAlpha = 0.78; const c = p.color ?? "#f4f6f6";
      if (v === "front") fill(ctx, c, () => { ctx.moveTo(-6.6, -26.6); ctx.lineTo(6.6, -26.6); ctx.quadraticCurveTo(6.4, -21.4, 0, -20.6); ctx.quadraticCurveTo(-6.4, -21.4, -6.6, -26.6); ctx.closePath(); });
      else fill(ctx, c, () => { ctx.moveTo(1.6, -26.6); ctx.lineTo(9.8, -26.6); ctx.quadraticCurveTo(9.4, -22, 4.6, -20.8); ctx.lineTo(1.6, -22); ctx.closePath(); });
      ctx.restore(); } },
    // 斗笠（斷崖幫、疤面）：草編圓錐，帽緣在眉毛上，四面都畫
    douli: { C(ctx, v, p) { const c = p.color ?? "#c8b07a", d = dk(c, 0.22);
      if (v === "side") { fill(ctx, c, () => { ctx.moveTo(-12.6, -33.8); ctx.quadraticCurveTo(0, -36, 12.4, -32.8); ctx.lineTo(0.8, -43.4); ctx.closePath(); }); line(ctx, d, 0.5, [[0.8, -43], [-5.4, -34.8]]); line(ctx, d, 0.5, [[0.8, -43], [6.6, -33.8]]); fill(ctx, d, () => rr(ctx, -8.6, -35.8, 16.8, 1.2, 0.6)); return; }
      fill(ctx, c, () => { ctx.moveTo(-12.6, -33); ctx.quadraticCurveTo(0, -31.6, 12.6, -33); ctx.lineTo(0, -43.6); ctx.closePath(); });
      for (const x of [-6.6, 0, 6.6]) line(ctx, d, 0.5, [[0, -43.2], [x, -32.4]]);
      line(ctx, d, 0.7, [[-12.6, -33], [12.6, -33]]);
      if (v === "front") line(ctx, "#6a4a2a", 0.6, [[-6.4, -31.8], [-5.2, -24.6]]), line(ctx, "#6a4a2a", 0.6, [[6.4, -31.8], [5.2, -24.6]]); // 下巴綁繩只在臉兩側
    } },
    // 頭帶（青鋒、石師傅）：額前一圈，結在後腦正中（四面一致），兩條帶尾垂在後頸
    headband: { C(ctx, v, p) { const c = p.color ?? "#b8432f", d = dk(c, 0.25);
      if (v === "side") { fill(ctx, c, () => { ctx.moveTo(8.6, -34.2); ctx.lineTo(8.9, -32.2); ctx.lineTo(-9.4, -31.4); ctx.lineTo(-9.2, -33.4); ctx.closePath(); }); fill(ctx, d, () => ctx.arc(-9.4, -32.4, 1.3, 0, TAU)); fill(ctx, c, () => { ctx.moveTo(-9.6, -32); ctx.lineTo(-13.2, -27.4); ctx.lineTo(-11.6, -26.8); ctx.lineTo(-9, -31); ctx.closePath(); }); return; }
      fill(ctx, c, () => { ctx.moveTo(-8.9, -33.6); ctx.quadraticCurveTo(0, -35.4, 8.9, -33.6); ctx.lineTo(8.7, -31.6); ctx.quadraticCurveTo(0, -33.2, -8.7, -31.6); ctx.closePath(); });
      if (v === "back") { fill(ctx, d, () => ctx.arc(0, -33.2, 1.4, 0, TAU)); for (const s of [-1, 1]) fill(ctx, c, () => { ctx.moveTo(0, -33); ctx.lineTo(s * 2.6, -25.6); ctx.lineTo(s * 0.8, -25.2); ctx.closePath(); }); }
    } },
    // 戴在眼睛上的護目鏡（已經戴帽子、不能用 qDoll head goggles 時；造型同 qDoll 的 goggles）
    goggles: { C(ctx, v) { const st = "#3a3a44";
      if (v === "back") { line(ctx, st, 1.4, [[-8.8, -30], [8.8, -30]]); return; }
      if (v === "side") { line(ctx, st, 1.2, [[6, -30], [-8.8, -30.6]]); fill(ctx, "#8d969f", () => ctx.ellipse(7.2, -29.5, 2, 2.6, 0, 0, TAU)); fill(ctx, "rgba(160,220,255,0.7)", () => ctx.ellipse(7.8, -29.5, 1.2, 1.9, 0, 0, TAU)); return; }
      line(ctx, st, 1.3, [[-8.8, -29.6], [8.8, -29.6]]);
      for (const x of [-3, 3]) { fill(ctx, "#8d969f", () => ctx.ellipse(x, -29.5, 3, 2.6, 0, 0, TAU)); fill(ctx, "rgba(160,220,255,0.7)", () => ctx.ellipse(x, -29.5, 2.2, 1.9, 0, 0, TAU)); }
    } },
    // 推到額上的護目鏡（工坊師傅、爐叔）：正面兩片在額頭上（眉毛以上），側面一片在額前，背面只看到帶子
    goggles_up: { C(ctx, v, p) { const st = "#3a3a44"; if (p.cap) ctx.translate(0, -1.6); // 戴帽子時架在帽沿上
      if (v === "back") { line(ctx, st, 1.3, [[-8.8, -33.6], [8.8, -33.6]]); return; }
      if (v === "side") { line(ctx, st, 1.2, [[6, -34.6], [-9, -33.4]]); fill(ctx, "#8d969f", () => ctx.ellipse(6.6, -35.4, 2, 2.2, 0, 0, TAU)); fill(ctx, "rgba(160,220,255,0.85)", () => ctx.ellipse(7.2, -35.4, 1.1, 1.5, 0, 0, TAU)); return; }
      line(ctx, st, 1.3, [[-8.8, -34.4], [8.8, -34.4]]);
      for (const x of [-3.2, 3.2]) { fill(ctx, "#8d969f", () => ctx.ellipse(x, -35, 2.8, 2.3, 0, 0, TAU)); fill(ctx, "rgba(160,220,255,0.85)", () => ctx.ellipse(x, -35, 1.9, 1.5, 0, 0, TAU)); }
    } },
  };
  function gourdShape(ctx, c) { fill(ctx, c, () => { ctx.arc(0, 2.6, 3.4, 0, TAU); }); fill(ctx, c, () => ctx.arc(0, -2.4, 2.3, 0, TAU)); fill(ctx, "#c0392b", () => rr(ctx, -1.8, -0.6, 3.6, 1, 0.4)); fill(ctx, "#6a4a2a", () => rr(ctx, -0.8, -5.6, 1.6, 1.6, 0.4)); fill(ctx, "rgba(255,255,255,0.35)", () => ctx.arc(-1.2, 1.6, 0.9, 0, TAU)); }
  function bagShape(ctx, x, y, col, back = false) { const c = col ?? "#d8c8a0", d = dk(c, 0.25); fill(ctx, c, () => rr(ctx, x, y, 6, 5.6, 1.2)); fill(ctx, d, () => rr(ctx, x, y, 6, 2.4, 1)); if (!back) fill(ctx, "#2a2420", () => rr(ctx, x + 2.4, y + 1.8, 1.2, 1.4, 0.3)); }

  // ---------- 外框：和 qDoll stamp 同一套（12 方向短線段膨脹 ≈ 半徑 k 的圓盤） ----------
  function dilate(src, r) {
    const cw = src.width, ch = src.height, mk = () => { const c = document.createElement("canvas"); c.width = cw; c.height = ch; return c.getContext("2d"); };
    const N = 12, a = (r * Math.PI) / (2 * N), P = [mk(), mk()]; let cur = src, n = 0;
    for (let i = 0; i < N; i++) { const t = (Math.PI * i) / N, ux = Math.cos(t) * a, uy = Math.sin(t) * a, c = P[n++ % 2]; c.clearRect(0, 0, cw, ch); for (const f of [-1, -0.5, 0, 0.5, 1]) c.drawImage(cur, ux * f, uy * f); cur = c.canvas; }
    return cur;
  }
  /** 把一個「填色層」描上 qDoll 的剪影外框後貼到 ctx（dx,dy＝畫布左上；w,h＝貼上大小）。
   *  close：拿弓的單位（第 11 版）「膨脹後再閉合」：外框做好後，把比 2×1.5 單位窄的背景縫填成外框色（r＝1.5 單位的像素數）。 */
  function outlineOnto(ctx, layer, k, dx, dy, w, h, close = 0) {
    const cw = layer.width, ch = layer.height, mk = () => { const c = document.createElement("canvas"); c.width = cw; c.height = ch; return c.getContext("2d"); };
    const s = mk(); s.drawImage(layer, 0, 0); s.globalCompositeOperation = "source-in"; s.fillStyle = OUT; s.fillRect(0, 0, cw, ch);
    const O = dilate(s.canvas, k), oc = mk();
    if (close) {
      const inv = (src) => { const c = mk(); c.fillStyle = "#000"; c.fillRect(0, 0, cw, ch); c.globalCompositeOperation = "destination-out"; c.drawImage(src, 0, 0); return c.canvas; };
      const O2 = mk(); O2.drawImage(O, 0, 0); const Oc = O2.canvas;
      oc.drawImage(inv(dilate(inv(dilate(Oc, close)), close)), 0, 0); oc.drawImage(Oc, 0, 0);
    } else oc.drawImage(O, 0, 0);
    oc.globalCompositeOperation = "source-in"; oc.fillStyle = OUT; oc.fillRect(0, 0, cw, ch);
    ctx.drawImage(oc.canvas, dx, dy, w, h); ctx.drawImage(layer, dx, dy, w, h);
  }
  /** 臉的皮膚區域：本體填色層裡和膚色相近的像素（頭圓扣掉頭髮、帽、頭巾、鏡片、鬍子；腮紅、眼睛也扣掉）。 */
  function skinMask(A, hex, lim = 26) {
    const cw = A.canvas.width, ch = A.canvas.height, d = A.getImageData(0, 0, cw, ch), q = d.data, r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16);
    for (let i = 0; i < q.length; i += 4) { const ok = q[i + 3] > 200 && Math.abs(q[i] - r) + Math.abs(q[i + 1] - g) + Math.abs(q[i + 2] - b) < lim; q[i] = q[i + 1] = q[i + 2] = 0; q[i + 3] = ok ? 255 : 0; }
    const c = document.createElement("canvas"); c.width = cw; c.height = ch; c.getContext("2d").putImageData(d, 0, 0); return c;
  }

  /** 畫一隻 NPC／人形敵人。參數同 QDoll.stamp。
   *  opts.extraC(ctx, view, q)：和本體一起描外框的配件；opts.extraSkin：裁在臉的皮膚區域裡（疤、煤灰）；opts.extraD：不描外框、蓋在最上面（表情、義眼）。 */
  function stamp(ctx, unit, view, cx, cy, size = 1, west = false, opts = {}) {
    const QD = Q(), dpr = opts.dpr ?? 3, { W, H, FOOT } = BOX, pw = Math.round(W * size * dpr), ph = Math.round(H * size * dpr);
    const { q, parts } = prep(unit, !!opts.portrait), S = view === "side", WW = S && west;
    const mk = () => { const c = document.createElement("canvas"); c.width = pw; c.height = ph; return c.getContext("2d", { willReadFrequently: true }); };
    // A：本體（不描外框），同時拿到每把武器／手持物的變換（qDoll 的 probe）
    const A = mk(), pose = { hands: {}, wms: {} };
    pose.probe = (kind, g, t, v, o, m) => { (pose.wms[kind] ??= []).push(m); };
    A.save(); A.scale(dpr, dpr); QD.setPose(pose);
    try { QD.stamp(A, q, view, (W / 2) * size, (H - FOOT) * size, size, west, { dpr, outline: false }); } finally { QD.setPose(null); }
    A.restore();
    const [bx, by] = BUILD[q.look.build] ?? [1, 1], fr = q.look.frame === "slim" ? [0.92, 1.02] : q.look.frame === "broad" ? [1.08, 0.98] : [1, 1];
    const frame = (c) => { c.setTransform(1, 0, 0, 1, 0, 0); c.scale(dpr * size, dpr * size); c.translate(W / 2, H - FOOT); if (WW) c.scale(-1, 1); c.scale(bx * fr[0], by * fr[1]); };
    const L = { B0: mk(), B: mk(), C: mk(), D: mk() };
    for (const p of parts) for (const ly of ["B", "C", "D"]) { const f = PART[p.k]?.[ly]; if (!f) continue; const c = L[ly]; c.save(); frame(c); f(c, view, p, q, WW); c.restore(); }
    const at = (m, x, y, c) => { const pt = m.transformPoint(new DOMPoint(x, y)); c.setTransform(1, 0, 0, 1, 0, 0); c.translate(pt.x, pt.y); c.scale(dpr * size * bx, dpr * size * by); };
    // 劍穗：掛在劍柄尾（武器座標 (0, 2.2)），往下垂；朝西劍在遠側，劍穗也在身體後面（B 層）
    const ts = parts.find((p) => p.k === "tassel"), sw = ts && pose.wms[q.gear.main_hand?.kind]?.[0];
    if (sw) { const c = L[WW ? "B" : "C"]; c.save(); at(sw, 0, 2.2, c); line(c, ts.color, 0.6, [[0, 0], [0.4, 2.6]]); fill(c, "#e8bb48", () => c.arc(0.4, 2.8, 0.6, 0, TAU)); fill(c, ts.color, () => { c.moveTo(-0.6, 3.2); c.lineTo(1.4, 3.2); c.lineTo(1.8, 6.6); c.lineTo(-1, 6.6); c.closePath(); }); c.restore(); }
    // 傀儡線：十字架三個點往下垂的細線（不描外框）。遠側的手（朝西主手）在身體後面（B0：外框之下）
    for (const p of parts.filter((p) => p.k === "strings")) {
      const m = (pose.wms.puppet_strings ?? [])[p.who === "off" && q.gear.main_hand?.kind === "puppet_strings" ? 1 : 0]; if (!m) continue;
      const far = S && ((p.who === "main_hand") === WW), c = L[far ? "B0" : "D"], tops = [[-4, 0], [4, 0], [0, 3.6]].map(([x, y]) => m.transformPoint(new DOMPoint(x, y)));
      c.save(); c.setTransform(1, 0, 0, 1, 0, 0); c.strokeStyle = "rgba(240,236,220,0.9)"; c.lineWidth = 0.4 * dpr * size; const k = dpr * size * by, bot = Math.max(...tops.map((t) => t.y)) + 10 * k, mx = tops.reduce((a, t) => a + t.x, 0) / 3;
      for (const t of tops) { c.beginPath(); c.moveTo(t.x, t.y); c.lineTo(mx + (t.x - mx) * 0.4, bot); c.stroke(); }
      c.fillStyle = "#c0392b"; c.beginPath(); c.arc(mx, bot + 0.6 * k, 0.7 * k, 0, TAU); c.fill(); c.restore();
    }
    if (opts.extraC) { L.C.save(); frame(L.C); opts.extraC(L.C, view, q); L.C.restore(); }
    if (opts.extraSkin) { const E = mk(); E.save(); frame(E); opts.extraSkin(E, view, q); E.restore(); E.globalCompositeOperation = "destination-in"; E.drawImage(skinMask(A, q.look.skin), 0, 0); L.D.drawImage(E.canvas, 0, 0); }
    if (opts.extraD) { L.D.save(); frame(L.D); opts.extraD(L.D, view, q); L.D.restore(); }
    // 合成：B → A → C，描一圈外框（拿弓的單位正面、側面做閉合），B0 在外框之下，D 在最上面
    const comb = mk(); comb.drawImage(L.B.canvas, 0, 0); comb.drawImage(A.canvas, 0, 0); comb.drawImage(L.C.canvas, 0, 0);
    const dx0 = cx - (W / 2) * size, dy0 = cy - (H - FOOT) * size, bow = q.gear.main_hand?.kind === "bow" && view !== "back";
    ctx.save(); ctx.imageSmoothingEnabled = true;
    if (opts.glow) { ctx.save(); ctx.shadowColor = opts.glow; ctx.shadowBlur = 14 * size; ctx.drawImage(comb.canvas, dx0, dy0, W * size, H * size); ctx.restore(); }
    ctx.drawImage(L.B0.canvas, dx0, dy0, W * size, H * size);
    outlineOnto(ctx, comb.canvas, 1.3 * size * dpr, dx0, dy0, W * size, H * size, bow ? 1.5 * size * dpr : 0);
    ctx.drawImage(L.D.canvas, dx0, dy0, W * size, H * size);
    ctx.restore();
    return { hands: pose.hands };
  }

  // ---------- 修士（敵人外觀.md 2 節；色票 代決 7）與盜賊三套（代決 9） ----------
  const C = { gray: "#8a9aa0", qing: "#5f8f8a", moon: "#dfe4e2", ink: "#3c4248", red: "#c0392b", bamboo: "#4f8a6a" }, sk = "#f1c9a5", sk2 = "#d9a47a";
  const MONKS = [
    ["青霧道童", "補師（小，0.9）", { look: { skin: sk, hair: "bun", hairColor: "#1c1c22" }, gear: { body: { kind: "robe", color: C.gray, trim: C.moon }, main_hand: { kind: "staff", material: "wood", element: "nature" } } }, { k: 0.9 }],
    ["持劍弟子", "近戰", { look: { skin: sk2, hair: "bun", hairColor: "#1c1c22" }, gear: { body: { kind: "robe", color: C.qing, trim: C.moon }, main_hand: { kind: "sword", material: "steel" } } }],
    ["符籙師", "控制（雷）", { look: { skin: sk, hair: "long", hairColor: "#1c1c22" }, gear: { body: { kind: "robe", color: C.qing, trim: C.red }, waist: { kind: "talismans" }, main_hand: { kind: "talisman" } } }],
    ["煉丹師", "補師（先打）", { look: { skin: sk2, hair: "bun", hairColor: "#2a2a30" }, gear: { body: { kind: "robe", color: C.bamboo, trim: C.moon, apron: "#e8dcc0" }, back: { kind: "gourd" }, main_hand: { kind: "whisk" } } }],
    ["護法武僧", "坦", { look: { skin: "#c08050", hair: "none", build: "stout", pants: "#d8a030" }, gear: { body: { kind: "bare", color: "#d8a030" }, neck: { kind: "beads", color: "#6a3a22" } } }],
    ["劍陣弟子", "近戰（三人一組）", { look: { skin: sk, hair: "bun", hairColor: "#1c1c22" }, gear: { body: { kind: "robe", color: C.moon, trim: C.qing }, main_hand: { kind: "sword", material: "steel", tassel: C.red } } }],
    ["霧行者", "刺客", { look: { skin: sk, hair: "short", hairColor: "#2a2a30" }, gear: { body: { kind: "robe", color: "#e8ecee", trim: "#b8c4cc" }, head: { kind: "gauze", color: "#eef2f2" }, main_hand: { kind: "dagger", material: "steel" } } }],
    ["雲鶴使", "遠程", { look: { skin: sk2, hair: "bun", hairColor: "#1c1c22" }, gear: { body: { kind: "robe", color: C.moon, trim: C.ink }, cloak: { kind: "cape", form: "feather", color: "#f2f0ea" }, main_hand: { kind: "bow", material: "wood" } } }],
    ["傀儡師", "召喚", { look: { skin: sk, hair: "long", hairColor: "#3a2a20" }, gear: { body: { kind: "robe", color: C.ink, trim: C.red }, back: { kind: "puppet_box" }, main_hand: { kind: "puppet_strings" } } }],
    ["青霧執事", "精英（補師）", { look: { skin: sk2, hair: "bun", hairColor: "#2a2a30", beard: true }, gear: { body: { kind: "robe", color: C.bamboo, trim: "#e8bb48", apron: "#f2e8c8" }, back: { kind: "gourd", color: "#e8bb48" }, main_hand: { kind: "whisk" } } }, { elite: true }],
    ["霧鎖真人", "頭目", { look: { skin: sk, hair: "long", hairColor: "#f0f0f0", beard: true }, gear: { body: { kind: "robe", color: C.moon, trim: "#e8bb48" }, cloak: { kind: "cape", color: C.qing }, main_hand: { kind: "sword", material: "steel" }, off_hand: { kind: "whisk" } } }, { glow: "#ffbf3a" }],
  ];
  const it = (kind, material, extra = {}) => ({ kind, material, ...extra });
  const STRAW = "#c8b07a", HEMP = "#b8ab90", HEMP_D = "#8a7e66", RUST = "#8a6a52";
  const BANDITS = {
    base: ["盜賊（原版）：皮甲、紅頭巾", [
      ["盜賊", "近戰", { look: { skin: "#a8724c", hair: "short", hairColor: "#2a1c14" }, gear: { body: it("leather", "leather"), feet: it("boots", "leather"), head: it("bandana", "cloth", { color: "#b33a3a" }), main_hand: it("dagger", "iron") } }],
      ["盜賊弓手", "遠程", { look: { skin: "#d9a47a", hair: "short", hairColor: "#3a2414" }, gear: { body: it("leather", "leather"), feet: it("boots", "leather"), head: it("hood", "cloth", { color: "#6a4a2a" }), main_hand: it("bow", "wood") } }],
      ["盾衛", "坦", { look: { skin: "#a8724c", hair: "short", hairColor: "#2a1c14" }, gear: { body: it("leather", "leather"), feet: it("boots", "leather"), head: it("bandana", "cloth", { color: "#b33a3a" }), main_hand: it("axe", "iron"), off_hand: it("shield_round", "wood") } }],
      ["隊長", "精英", { look: { skin: "#a8724c", hair: "short", hairColor: "#1c1410" }, gear: { body: it("leather", "iron"), feet: it("boots", "leather"), head: it("bandana", "cloth", { color: "#a32a2a" }), cloak: it("cape", "cloth", { color: "#a32a2a" }), main_hand: it("sword", "iron") } }, { elite: true }],
      ["頭目", "頭目", { look: { skin: "#a8724c", hair: "short", hairColor: "#1c1410" }, gear: { body: it("mail", "iron"), feet: it("greaves", "steel"), hands: it("gauntlets", "steel"), head: it("horned_helm", "iron"), cloak: it("cape", "cloth", { color: "#a32a2a" }), main_hand: it("axe", "iron") } }, { glow: "#b06aff" }],
    ]],
    cliff: ["斷崖幫（雲嶺）：斗笠、麻布、綁腿", [
      ["斷崖幫", "近戰", { look: { skin: "#d9a47a", hair: "short", hairColor: "#1c1c22" }, gear: { head: { kind: "douli", color: STRAW }, body: it("coat", "cloth", { color: HEMP }), feet: it("shoes", "cloth", { color: HEMP_D }), main_hand: it("dagger", "iron") } }],
      ["斷崖幫弓手", "遠程", { look: { skin: "#d9a47a", hair: "short", hairColor: "#1c1c22" }, gear: { head: { kind: "douli", color: STRAW }, body: it("coat", "cloth", { color: HEMP_D }), feet: it("shoes", "cloth", { color: HEMP_D }), main_hand: it("bow", "wood") } }],
      ["斷崖幫盾衛", "坦", { look: { skin: "#a8724c", hair: "short", hairColor: "#1c1c22" }, gear: { head: { kind: "douli", color: STRAW }, body: it("leather", "leather"), feet: it("shoes", "cloth", { color: HEMP_D }), main_hand: it("axe", "iron"), off_hand: it("shield_round", "wood") } }],
      ["斷崖幫隊長", "精英", { look: { skin: "#a8724c", hair: "long", hairColor: "#1c1c22" }, gear: { head: { kind: "douli", color: "#3c4248" }, body: it("coat", "cloth", { color: "#3c4248" }), cloak: it("cape", "cloth", { color: "#c0392b" }), feet: it("boots", "leather"), main_hand: it("saber", "steel") } }, { elite: true }],
      ["斷崖幫頭目", "頭目", { look: { skin: "#a8724c", hair: "short", hairColor: "#1c1c22" }, gear: { head: { kind: "douli", color: "#3c4248" }, body: it("mail", "iron"), hands: it("bracers", "leather"), cloak: it("cape", "cloth", { color: "#c0392b" }), feet: it("boots", "leather"), main_hand: it("greatsword", "steel") } }, { glow: "#b06aff" }],
    ]],
    ash: ["荒原盜賊（灰燼荒原）：鏽色舊鐵、破布兜帽、舊槍、火斧", [
      ["荒原盜賊", "近戰", { look: { skin: "#7a4e32", hair: "short", hairColor: "#1c1410" }, gear: { head: it("bandana", "cloth", { color: "#5a4a3e" }), body: it("leather", "leather", { color: "#5a4030" }), feet: it("boots", "leather"), main_hand: it("axe", "iron", { element: "fire" }) } }],
      ["荒原槍手", "遠程", { look: { skin: "#a8724c", hair: "short", hairColor: "#1c1410" }, gear: { head: it("hood", "cloth", { color: "#6a5a4a" }), body: it("coat", "leather", { color: "#5a4030" }), feet: it("boots", "leather"), main_hand: it("pistol", "iron") } }],
      ["荒原盾衛", "坦", { look: { skin: "#7a4e32", hair: "short", hairColor: "#1c1410" }, gear: { head: it("helmet", "iron", { color: RUST }), body: it("mail", "iron", { color: RUST }), feet: it("iron_boots", "iron", { color: RUST }), main_hand: it("hammer", "iron"), off_hand: it("shield_round", "iron", { color: RUST }) } }],
      ["荒原隊長", "精英", { look: { skin: "#a8724c", hair: "short", hairColor: "#1c1410" }, gear: { head: it("bandana", "cloth", { color: "#ff6a1a" }), body: it("mail", "iron", { color: RUST }), cloak: it("cape", "cloth", { color: "#5a4a3e" }), feet: it("boots", "leather"), main_hand: it("shotgun", "iron") } }, { elite: true }],
      ["荒原頭目", "頭目", { look: { skin: "#7a4e32", hair: "none" }, gear: { head: it("greathelm", "iron", { color: RUST }), body: it("plate", "iron", { color: RUST }), hands: it("gauntlets", "iron", { color: RUST }), cloak: it("cape", "cloth", { color: "#ff6a1a" }), feet: it("iron_boots", "iron", { color: RUST }), main_hand: it("axe", "iron", { element: "fire" }) } }, { glow: "#b06aff" }],
    ]],
  };
  const PARTS_LIST = ["髮髻（qDoll bun）", "赤膊（qDoll body bare）", "念珠（qDoll beads）", "圍裙 apron", "背葫蘆 gourd", "木偶箱 puppet_box", "黃符 talismans", "白紗面罩 gauze", "白羽披肩（qDoll neck feathers）", "劍穗 tassel", "拂塵、符紙、傀儡線（qDoll 手持物 whisk／talisman／puppet_strings）", "斗笠 douli", "頭帶 headband", "額上護目鏡 goggles_up", "毛領（qDoll neck fur_collar）", "郵袋 mailbag"];
  return { stamp, prep, normLook, PART, MONKS, BANDITS, PARTS_LIST, BOX, BUILD, outlineOnto, dilate };
})();
