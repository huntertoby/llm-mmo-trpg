// sk3Mechanics.js：SK-3 新機制的美術樣張（畫圖 agent，2026-11-19；紀錄 docs/art/SK-3-美術.md）。
// 範圍：① 重擲 reroll 的 Q 版部件（取代 client/src/render/qIcon/parts.ts EFFECT_ALIAS 暫借的 intercept）；
//       ② 三個觸發圖樣（開發實際用到的三個：on_keyword_exploited、ally_missed_roll、enemy_hit_roll；取代 TRIG_ALIAS 的暫借）；
//       ③ 條件「貼身」point_blank、「遠距」long_range（現行沒有圖、畫「?」）；
//       ④ 重擲的戰鬥演出（canvas，時間 t 毫秒 → 一格畫面上的骰子層）；⑤ 戰前佈置的格子標記（取代暫借的選目標紅框）。
// 畫法語言照第④批部件（qIconsParts.js）：±10 單位、平塗三階、剪影外框、後畫的那件用 halo() 自己再包一圈。
// 不改任何過審的畫法檔：新圖樣只在呼叫 install() 的頁面塞進 QIconsParts.CATS（同 KW 段、SK-2 的作法）。
// 確定性：沒有 Math.random；動畫只吃 t。
window.SK3Mech = (() => {
  const Q = window.QIcons, QS = window.QIconsSkills, QP = window.QIconsParts;
  const { f, rr, ci, el, poly, ln, starPts, halo } = Q.H;
  const TAU = Math.PI * 2, PI = Math.PI, OUT = "#16121a";
  /* 以下幾個小工具與色照抄 qIconsParts.js（檔內沒有匯出；第 10～49 行），值不改。 */
  const CREAM = "#f2e6c8", ALLY = "#7de0a8", ENEMY = "#ff5a5a", LILAC = "#c8a0d8";
  const st = (c, col, w, fn, cap = "round") => { c.beginPath(); fn(c); c.strokeStyle = col; c.lineWidth = w; c.lineCap = cap; c.lineJoin = "round"; c.stroke(); };
  const at = (c, x, y, k, fn, rot = 0) => { c.save(); c.translate(x, y); c.rotate(rot); c.scale(k, k); fn(c); c.restore(); };
  const bust = (c, col, x, y, k = 1) => { ci(c, col, x, y - 4.6 * k, 3.7 * k); f(c, col, () => { c.moveTo(x - 6.2 * k, y + 7 * k); c.quadraticCurveTo(x - 6.2 * k, y - 0.4 * k, x, y - 0.4 * k); c.quadraticCurveTo(x + 6.2 * k, y - 0.4 * k, x + 6.2 * k, y + 7 * k); c.closePath(); }); };
  const star4 = (c, col, x, y, R, core = "#ffffff") => { poly(c, col, starPts(x, y, R, R * 0.36, 4), 0.3); if (core) poly(c, core, starPts(x, y, R * 0.55, R * 0.2, 4)); };
  const banner = (c, o) => { rr(c, "#9a6ab8", -8.6, -10.6, 17.2, 3.6, 1.6); poly(c, LILAC, [[-6.6, -8], [6.6, -8], [6.6, 9.6], [0, 4.4], [-6.6, 9.6]], 0.8); f(c, "#eed8f6", () => c.rect(-6.6, -7, 3, 13)); if (!o.tiny) star4(c, "#ffffff", 1.2, -1.4, 4.4, null); };
  const shieldAt = (c, o) => at(c, 4.6, 4.6, 0.56, (q) => QS.ACT.shield.d(q, o, QS.ACT.shield.def));
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const ease = (t) => { t = clamp(t); return t * t * (3 - 2 * t); };
  const span = (t, a, b) => clamp((t - a) / (b - a));
  const lerp = (a, b, t) => a + (b - a) * t;

  // =====================================================================
  // 1. 二十面骰：照第④批觸發「擲出自然 20 時」的畫法（六角外形、右側與左下兩塊暗面、中央白三角），只把半徑與三個色換成參數。
  //    同一個骰子用在重擲部件、隊友擲失手、敵人擲中你、戰場上的重擲演出，四處和「擲出自然 20」是同一個家族。
  // =====================================================================
  const DIE = {
    lav: { face: "#cfc4ff", dk: "#8a76d8", hi: "#ffffff", ink: "#3a2a7a" }, /* 同「擲出自然 20 時」 */
    red: { face: "#ff8a8a", dk: "#d23c4c", hi: "#ffe4e4", ink: "#5a1020" }, /* 敵人的骰子：ENEMY 紅系 */
    dim: { face: "#a9a6bc", dk: "#6e6a84", hi: "#dcdae6", ink: "#2a2838" }, /* 戰場：被換掉的那一次 */
  };
  const HEX = [0, 1, 2, 3, 4, 5].map((i) => [Math.cos((i / 6) * TAU - PI / 2) * 10.6, Math.sin((i / 6) * TAU - PI / 2) * 10.6]);
  /** 二十面骰（中心 x,y、外接半徑 R）。opt.rot 旋轉；opt.face＝骰面數字（只在戰場用，字型照「擲出自然 20 時」）；opt.ink＝外框那一遍的加粗（戰場用）。 */
  function d20(c, x, y, R, pal, opt = {}) {
    at(c, x, y, R / 10.6, (q) => {
      if (opt.ink) poly(q, OUT, HEX.map(([a, b]) => [a * (1 + opt.ink / 10.6), b * (1 + opt.ink / 10.6)]), 0.5 + opt.ink);
      poly(q, pal.face, HEX, 0.5);
      poly(q, pal.dk, [[9.2, -5.3], [9.2, 5.3], [0, 10.6], [5.6, 4]]);
      poly(q, pal.dk, [[-9.2, 5.3], [0, 10.6], [-5.6, 4]]);
      poly(q, pal.hi, [[0, -6.2], [5.8, 4], [-5.8, 4]], 0.4);
      if (opt.face != null) { const s = String(opt.face); q.fillStyle = pal.ink; q.font = `900 ${s.length > 1 ? 7.2 : 8.4}px Arial, sans-serif`; q.textAlign = "center"; q.textBaseline = "middle"; q.fillText(s, 0, 1.4); }
    }, opt.rot ?? 0);
  }

  // =====================================================================
  // 2. 重擲（效果部件 reroll）：一顆淡紫二十面骰，外面繞一圈順時針的金色回轉箭頭（↻），缺口在下、箭頭在右下。
  //    和骨架徽章「反應」（綠色逆時針回轉箭頭、沒有骰子）、代價「賭注」（白色方骰）、觸發「擲出自然 20」（大骰子寫 20、沒有箭頭）分開。
  //    ≤14px（18 的圓片）骰子與箭頭都留（箭頭是「重」的意思，拿掉就是一顆骰子＝賭注／自然 20）：當成一個「骰子回轉」記號，加粗、拉開縫。
  // =====================================================================
  const GOLD = { body: "#ffc23a", hi: "#fff0a8" };
  /** 回轉箭頭：圓心 (x,y)、半徑 R、線寬 w；順時針從 a0 掃到 a1，箭頭在 a1。 */
  function cwArrow(c, o, x, y, R, w, a0, a1, col = GOLD) {
    st(c, col.body, w, (p) => p.arc(x, y, R, a0, a1), "butt");
    const px = x + Math.cos(a1) * R, py = y + Math.sin(a1) * R, tx = -Math.sin(a1), ty = Math.cos(a1), nx = Math.cos(a1), ny = Math.sin(a1), L = w * 1.35, B = w * 0.98;
    poly(c, col.body, [[px + tx * L, py + ty * L], [px + nx * B - tx * 0.4, py + ny * B - ty * 0.4], [px - nx * B - tx * 0.4, py - ny * B - ty * 0.4]], 0.3);
    if (!o.tiny) st(c, col.hi, w * 0.32, (p) => p.arc(x, y, R + w * 0.18, PI * 1.08, PI * 1.62), "butt"); /* 亮面：左上一段細亮弧 */
  }
  function rerollArt(c, o) {
    const t = o.tiny, R = t ? 8.2 : 8.4, w = t ? 3.6 : 3.2;
    cwArrow(c, o, 0, 0.6, R, w, PI * 0.82, PI * 2.18);
    halo(c, o, (q) => d20(q, -0.2, 1.2, t ? 5.0 : 5.4, DIE.lav)); /* 骰子包自己的一圈，和箭頭之間留一道底色縫 */
  }
  const EFFECT = {
    reroll: {
      zh: "重擲", topic: "一顆淡紫二十面骰（同「擲出自然 20」的畫法、沒有字），外面一圈順時針的金色回轉箭頭（缺口在下、箭頭在右下）",
      d: (c, o) => at(c, 0, -0.3, 0.92, (q) => rerollArt(q, o)), /* 縮到 0.92：箭頭尖收在色環內 */
    },
  };

  // =====================================================================
  // 3. 觸發三個（開發頁實際用到的；TRIG_ALIAS 暫借 on_status_applied、ally_hit_adjacent、hit_by_attack）。
  //    家族照第④批：「施加狀態後」＝淡紫小旗；「身旁隊友受擊時」＝綠人形＋右上記號；「被攻擊時」＝左上大的來襲物＋右下小藍盾。
  // =====================================================================
  /** 一道往左下劈的黃色閃電（白芯），尖端在 (x1,y1)。 */
  function bolt(c, o) {
    poly(c, "#ffd23f", [[3.8, -11], [10.6, -11], [6.6, -5.4], [10, -5.4], [-0.4, 4.6], [3.2, -2.6], [-0.2, -2.6]], 0.4);
    if (!o.tiny) poly(c, "#fffbe0", [[5.2, -9.8], [8.4, -9.8], [4.6, -4.4], [7, -4.4], [1.8, 0.6], [3.8, -3.8], [1.8, -3.8]]);
  }
  const TRIG = {
    on_keyword_exploited: {
      zh: "你造的關鍵字被利用時", topic: "淡紫小旗（同「施加狀態後」＝你造的關鍵字），右上一道黃色閃電（白芯）劈在旗上（被引發）",
      d: (c, o) => at(c, 0, 0.4, 0.82, (u) => { at(u, -2.8, 1.6, 0.84, (q) => banner(q, o)); halo(u, o, (q) => bolt(q, o)); }), /* 縮到 0.82：閃電頂角與旗桿兩端收進色環 */
    },
    ally_missed_roll: {
      zh: "隊友擲失手時", topic: "綠色人形（同「身旁隊友受擊時」），右上一顆淡紫二十面骰被一道紅斜槓劃掉（左下到右上，同「沒有」的語言）",
      d: (c, o) => at(c, 0, 0.3, 0.92, (u) => { const c = u; bust(c, ALLY, -3.8, 2.4, 0.86); halo(c, o, (q) => { d20(q, 4.2, -3.8, 6.4, DIE.lav); if (o.tiny) ln(q, OUT, 4.2, [[-0.6, 0.8], [9, -8.4]]); ln(q, "#ff4a5a", o.tiny ? 2.4 : 2.2, [[-0.6, 0.8], [9, -8.4]]); }); }),
    },
    enemy_hit_roll: {
      zh: "敵人擲中你時", topic: "左上一顆大的紅色二十面骰（佔一半、微斜），砸向右下的小藍盾（同「被攻擊時」的家族）",
      d: (c, o) => at(c, 0, 0, 0.94, (u) => { shieldAt(u, o); halo(u, o, (q) => d20(q, -3.2, -3.2, 7.4, DIE.red, { rot: -0.26 })); }),
    },
  };

  // =====================================================================
  // 4. 條件兩個：貼身、遠距。同一組「我（米白人形）＋目標（紅白靶）」，靠距離分：貼身＝人形在左下、大靶在右上貼著；遠距＝小人形在左下、
  //    小一號的靶在右上、中間兩顆金點（≤14 一顆）。兩個都排在左下到右上的同一條斜線：貼身＝一團（靶大、貼著），遠距＝兩團中間有縫。
//    和「身旁有友方」（兩個人形橫排）、「夾擊」（人形＋兩側紅三角）、「每一下都命中」（靶＋兩把匕首）的剪影分開。
  // =====================================================================
  /** 紅白靶（目標）：紅外圈、白圈、紅心；≥26 左上一點亮面。 */
  function target(c, o, x, y, R) {
    ci(c, ENEMY, x, y, R); ci(c, "#ffffff", x, y, R * 0.64); ci(c, ENEMY, x, y, R * 0.3);
    if (!o.tiny) el(c, "#ffd0cc", x - R * 0.5, y - R * 0.55, R * 0.22, R * 0.14, -0.7);
  }
  const COND = {
    point_blank: {
      zh: "貼身", topic: "左下米白人形（我），右上一面大的紅白靶貼著人形的頭與前肩（目標，距離 1、中間沒有縫）",
      d: (c, o) => at(c, 0, 0, 0.94, (u) => { bust(u, CREAM, -4.2, 2.8, 0.92); halo(u, o, (q) => target(q, o, 4.4, -2.0, 5.9)); }), /* 縮到 0.94：人形的肩角收進色環。排法和遠距同一條斜線，靶貼著人形的頭與前肩（沒有縫） */
    },
    long_range: {
      zh: "遠距", topic: "左下一個小的米白人形（我），右上一面小一號的紅白靶（目標，遠），中間兩顆金點連成一條虛線（≤14 一顆）",
      d: (c, o) => at(c, 0, -0.2, 0.95, (c) => {
        bust(c, CREAM, -5.0, 3.4, 0.68);
        for (const [x, y] of o.tiny ? [[-0.47, -2.07]] : [[-1.36, -1.61], [0.42, -2.53]]) ci(c, "#ffd23f", x, y, o.tiny ? 1.5 : 1.15); /* 人形頭緣到靶緣之間的縫（約 5.2 單位）裡等距 */
        halo(c, o, (q) => target(q, o, 5.6, -5.2, 4.2));
      }),
    },
  };

  /** 塞進第④批的表（只在呼叫的頁面；qIconsParts.js 原檔不動）。trigger 是 TRIG 表本身，entry() 先查 TRIG，查到就不走別名。 */
  function install() {
    for (const [id, e] of Object.entries(EFFECT)) QP.CATS.effect[id] = { ...e, src: "new:sk3" };
    for (const [id, e] of Object.entries(TRIG)) QP.CATS.trigger[id] = { ...e, src: "new:sk3" };
    for (const [id, e] of Object.entries(COND)) QP.CATS.condition[id] = { ...e, src: "new:sk3" };
  }
  /** 現行（遊戲端）畫的是誰：暫借的對象；條件現行沒有圖（entry 走「不認得」的問號）。 */
  const LIVE = { "effect:reroll": ["effect", "intercept"], "trigger:on_keyword_exploited": ["trigger", "on_status_applied"], "trigger:ally_missed_roll": ["trigger", "ally_hit_adjacent"], "trigger:enemy_hit_roll": ["trigger", "hit_by_attack"], "condition:point_blank": ["condition", "__none_point_blank"], "condition:long_range": ["condition", "__none_long_range"] };

  // =====================================================================
  // 5. 戰場：重擲的骰子層（模型像素，1 格 48）。演出只畫骰子、回轉箭頭、金色引線、比較箭頭；單位與身體動作照現行。
  //    MK＝畫面下限的倍率（同 SK-2 的鎖鏈：骰子外接半徑 ≥ 9 畫面 px → MK＝max(1, 9 ÷ (DIE_R × 地圖縮放))）。
  // =====================================================================
  const DIE_R = 11, DIE_MIN_PX = 9; let MK = 1;
  const setMapScale = (S) => { MK = Math.max(1, DIE_MIN_PX / (DIE_R * S)); return MK; };
  /** 戰場上的一顆骰子：中心 (x,y)；k 縮放（彈出、落地壓扁用 sy）；a 透明度；pal；face 數字；ring＝外面一圈「採用」的金環（0～1）；cross＝紅斜槓（0～1）。 */
  function fieldDie(g, x, y, opt = {}) {
    const R = DIE_R * MK * (opt.k ?? 1), a = opt.a ?? 1; if (R < 0.5 || a <= 0) return;
    g.save(); g.globalAlpha *= a; g.translate(x, y); g.scale(1, opt.sy ?? 1);
    if (opt.ring > 0) { g.save(); g.globalAlpha *= opt.ring; Q.H.glow(g, 0, 0, R * 2.1, "#ffe066", 0.55); g.beginPath(); g.arc(0, 0, R * 1.32, 0, TAU); g.lineWidth = 4.2 * MK; g.strokeStyle = OUT; g.stroke(); g.lineWidth = 2.2 * MK; g.strokeStyle = "#ffd23f"; g.stroke(); g.restore(); }
    d20(g, 0, 0, R, opt.pal ?? DIE.lav, { rot: opt.rot ?? 0, face: opt.face, ink: 1.6 * 10.6 / R * MK });
    if (opt.flash > 0) { g.save(); g.globalAlpha *= opt.flash; at(g, 0, 0, R / 10.6, (q) => poly(q, "#ffffff", HEX, 0.5), opt.rot ?? 0); g.restore(); } /* 白閃：一般疊色（不用 lighter，淡紫加白會整顆變白、看不到點數） */
    if (opt.cross > 0) { const L = R * 0.95 * opt.cross; g.lineCap = "round"; for (const [w, col] of [[4.4 * MK, OUT], [2.4 * MK, "#ff4a5a"]]) { g.beginPath(); g.moveTo(-R * 0.95, R * 0.95); g.lineTo(-R * 0.95 + 2 * L, R * 0.95 - 2 * L); g.lineWidth = w; g.strokeStyle = col; g.stroke(); } }
    g.restore();
  }
  /** 戰場上的回轉箭頭（同部件的金色 ↻，外框色墊底）：繞 (x,y)，半徑 R，旋轉 rot，掃 sweep（0～1 長出來）。 */
  function fieldSpin(g, x, y, rot, sweep = 1, a = 1) {
    const R = DIE_R * MK * 1.5, w = 3 * MK; if (sweep <= 0) return;
    g.save(); g.globalAlpha *= a; g.translate(x, y); g.rotate(rot);
    const a0 = PI * 0.82, a1 = a0 + PI * 1.36 * sweep;
    for (const [ww, col, head] of [[w + 2.4 * MK, OUT, 1.24 * MK], [w, GOLD.body, 0]]) {
      st(g, col, ww, (p) => p.arc(0, 0, R, a0, a1), "butt");
      const px = Math.cos(a1) * R, py = Math.sin(a1) * R, tx = -Math.sin(a1), ty = Math.cos(a1), nx = Math.cos(a1), ny = Math.sin(a1), L = w * 1.5 + head, B = w * 1.1 + head;
      poly(g, col, [[px + tx * L, py + ty * L], [px + nx * B - tx * head, py + ny * B - ty * head], [px - nx * B - tx * head, py - ny * B - ty * head]], 0.2);
    }
    st(g, GOLD.hi, w * 0.34, (p) => p.arc(0, 0, R + w * 0.16, a0 + 0.2, Math.min(a1, a0 + 1.1)), "butt");
    g.restore();
  }
  /** 金色引線（施放反應的人 → 骰子）：二次曲線往旁邊拱（控制點＝中點沿法線外推 0.35 倍長＋10；兩條法線取較往上的那條，一樣高時取往左〔遠離敵方那一側〕），
   *  上下對齊時（反應者在擲骰者正下方）才不會直直穿過擲骰者的身體。p＝0～1 長到哪裡；頭上一顆金光點。 */
  function fieldBeam(g, from, to, p, a = 1) {
    if (p <= 0 || a <= 0) return;
    const dx = to.x - from.x, dy = to.y - from.y, len = Math.hypot(dx, dy) || 1; let nx = -dy / len, ny = dx / len; if (ny > 1e-6 || (Math.abs(ny) <= 1e-6 && nx > 0)) { nx = -nx; ny = -ny; }
    const bow = 0.35 * len + 10, cx = (from.x + to.x) / 2 + nx * bow, cy = (from.y + to.y) / 2 + ny * bow, pt = (q) => { const u = 1 - q; return { x: u * u * from.x + 2 * u * q * cx + q * q * to.x, y: u * u * from.y + 2 * u * q * cy + q * q * to.y }; };
    g.save(); g.globalAlpha *= a; g.lineCap = "round"; g.lineJoin = "round";
    for (const [w, col] of [[4.2 * MK, OUT], [2.2 * MK, "#ffd23f"], [0.9 * MK, "#fff6d0"]]) { g.beginPath(); for (let q = 0; q <= p + 1e-6; q += 0.04) { const s = pt(Math.min(q, p)); q ? g.lineTo(s.x, s.y) : g.moveTo(s.x, s.y); } g.strokeStyle = col; g.lineWidth = w; g.stroke(); }
    if (p < 1) { const h = pt(p); Q.H.glow(g, h.x, h.y, 9 * MK, "#ffe066", 0.8); g.beginPath(); g.arc(h.x, h.y, 2.6 * MK, 0, TAU); g.fillStyle = "#ffffff"; g.fill(); }
    g.restore();
  }
  /** 反應者腳下的金色光圈（腳底橢圓往外擴、淡出），p＝0～1。 */
  function fieldPulse(g, feet, p) {
    if (p <= 0 || p >= 1) return;
    g.save(); g.globalAlpha = 1 - p; g.beginPath(); g.ellipse(feet.x, feet.y, 14 + 12 * ease(p), (14 + 12 * ease(p)) * 0.42, 0, 0, TAU); g.lineWidth = 3 * MK; g.strokeStyle = "#ffd23f"; g.stroke(); g.restore();
  }
  /** 比較箭頭（舊 → 新）：往上（變大，綠）或往下（變小，紅）的粗箭頭，外框色墊底；中心 (x,y)。 */
  function fieldCmp(g, x, y, up, a = 1) {
    if (a <= 0) return;
    const col = up ? ["#5ad06a", "#c8f8d0"] : ["#ff5a5a", "#ffc0b8"], s = MK * 0.62;
    g.save(); g.globalAlpha *= a; g.translate(x, y); g.scale(s, up ? s : -s);
    const P = [[-2.8, 9], [-2.8, -1], [-7.4, -1], [0, -9.6], [7.4, -1], [2.8, -1], [2.8, 9]];
    poly(g, OUT, P.map(([px, py]) => [px * 1.25, py * 1.18]), 0.6); poly(g, col[0], P, 0.4); poly(g, col[1], [[0, -9.6], [-7.4, -1], [-2.8, -1], [-2.8, 9], [-0.8, 9], [-0.8, -6.6]]);
    g.restore();
  }

  // =====================================================================
  // 6. 戰前佈置：起始區裡放得下的格子（取代暫借的選目標紅框）。畫在畫面 px（s＝一格的畫面邊長）。
  //    待放：金色四角括號＋淡金底＋中央一顆金菱形（同戰鬥紀錄「◆ 戰前佈置」的菱形），括號 1.2 秒一次往內收 1 px（t 毫秒）。
  //    指著：整圈金框＋較亮的底＋要放的東西的半透明預覽（ghost，取代菱形）。放下：0～420 ms 金框往外擴、淡出＋四顆金火花。
  // =====================================================================
  const PLACE = { gold: "#ffd23f", hi: "#fff3b0", fill: "255,210,63" };
  function placeMark(g, x, y, s, opt = {}) {
    const state = opt.state ?? "idle", t = opt.t ?? 0, pulse = 0.5 - 0.5 * Math.cos((t % 1200) / 1200 * TAU), w = Math.max(2, s * 0.06), i = s * 0.09 + pulse * Math.max(1, s * 0.02), L = s * 0.27, r = s * 0.12;
    g.save();
    g.fillStyle = `rgba(${PLACE.fill},${state === "hover" ? 0.3 : 0.13 + 0.05 * pulse})`; g.beginPath(); g.roundRect(x + s * 0.06, y + s * 0.06, s * 0.88, s * 0.88, r); g.fill();
    const corner = (col, ww) => { g.strokeStyle = col; g.lineWidth = ww; g.lineCap = "round"; g.lineJoin = "round"; for (const [sx, sy] of [[0, 0], [1, 0], [1, 1], [0, 1]]) { const cx = sx ? x + s - i : x + i, cy = sy ? y + s - i : y + i, dx = sx ? -1 : 1, dy = sy ? -1 : 1; g.beginPath(); g.moveTo(cx, cy + dy * L); g.lineTo(cx, cy + dy * r * 0.5); g.quadraticCurveTo(cx, cy, cx + dx * r * 0.5, cy); g.lineTo(cx + dx * L, cy); g.stroke(); } };
    if (state === "hover") { g.beginPath(); g.roundRect(x + i, y + i, s - 2 * i, s - 2 * i, r); g.strokeStyle = OUT; g.lineWidth = w + 2; g.stroke(); g.strokeStyle = PLACE.gold; g.lineWidth = w; g.stroke(); g.strokeStyle = PLACE.hi; g.lineWidth = Math.max(1, w * 0.3); g.beginPath(); g.roundRect(x + i + w * 0.15, y + i + w * 0.15, s - 2 * i - w * 0.3, s - 2 * i - w * 0.3, r); g.stroke(); }
    else { corner(OUT, w + 2); corner(PLACE.gold, w); }
    if (state === "hover" && opt.ghost) { g.globalAlpha = 0.68; opt.ghost(g, x + s / 2, y + s / 2, s); g.globalAlpha = 1; }
    else if (state !== "hover") { const d = Math.max(3, s * 0.1); g.beginPath(); g.moveTo(x + s / 2, y + s / 2 - d - 1.2); g.lineTo(x + s / 2 + d + 1.2, y + s / 2); g.lineTo(x + s / 2, y + s / 2 + d + 1.2); g.lineTo(x + s / 2 - d - 1.2, y + s / 2); g.closePath(); g.fillStyle = OUT; g.fill(); g.beginPath(); g.moveTo(x + s / 2, y + s / 2 - d); g.lineTo(x + s / 2 + d, y + s / 2); g.lineTo(x + s / 2, y + s / 2 + d); g.lineTo(x + s / 2 - d, y + s / 2); g.closePath(); g.fillStyle = PLACE.gold; g.fill(); g.beginPath(); g.moveTo(x + s / 2, y + s / 2 - d); g.lineTo(x + s / 2 - d, y + s / 2); g.lineTo(x + s / 2, y + s / 2); g.closePath(); g.fillStyle = PLACE.hi; g.fill(); }
    g.restore();
  }
  /** 放下的一下（p＝0～1，420 ms）：金框從格子往外擴 25%、淡出；四角各一顆金四芒火花往外飛。 */
  function placeBurst(g, x, y, s, p) {
    if (p <= 0 || p >= 1) return; const e = ease(p), k = 1 + 0.25 * e, cx = x + s / 2, cy = y + s / 2, h = (s * 0.44) * k, w = Math.max(2, s * 0.06);
    g.save(); g.globalAlpha = 1 - e; g.beginPath(); g.roundRect(cx - h, cy - h, 2 * h, 2 * h, s * 0.14); g.strokeStyle = OUT; g.lineWidth = w + 2; g.stroke(); g.strokeStyle = PLACE.gold; g.lineWidth = w; g.stroke();
    for (const [sx, sy] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) star4(g, PLACE.gold, cx + sx * (h + s * 0.08 * e), cy + sy * (h + s * 0.08 * e), Math.max(3, s * 0.1) * (1 - 0.4 * e), "#ffffff");
    g.restore();
  }

  return { DIE, d20, EFFECT, TRIG, COND, LIVE, install, setMapScale, mk: () => MK, fieldDie, fieldSpin, fieldBeam, fieldPulse, fieldCmp, placeMark, placeBurst, PLACE, ease, span, lerp, clamp, GOLD };
})();
