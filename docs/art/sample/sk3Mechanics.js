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
    redT: { face: "#ff8a8a", dk: "#a82434", hi: "#ffffff", ink: "#5a1020" }, /* 第 2 版：≤14 的紅骰（暗面深一階、亮面純白） */
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
      const k = opt.hiK ?? 1; /* 第 2 版（可修 3）：≤14 的紅骰把中央白三角放大，多面體的切面才留得下來 */
      poly(q, pal.hi, [[0, -6.2 * k], [5.8 * k, 4], [-5.8 * k, 4]], 0.4);
      if (opt.face != null) { const s = String(opt.face); q.fillStyle = pal.ink; q.font = `900 ${s.length > 1 ? 7.2 : 8.4}px Arial, sans-serif`; q.textAlign = "center"; q.textBaseline = "middle"; q.fillText(s, 0, 1.4); }
    }, opt.rot ?? 0);
  }

  // =====================================================================
  // 2. 重擲（效果部件 reroll）。第 2 版（必修 M1）：主體換成骰子，拿掉圈狀箭頭（第 1 版的金色 ↻ 和骨架徽章「反應」的回轉箭頭同題材，
  //    而重擲只能是反應技的效果，兩個一定同框）。前景一顆淡紫二十面骰（右下、大），後面一顆往左上退、縮小、變灰的骰子（DIE.dim＝演出裡被換掉的那一顆），
  //    前景那顆用 halo() 包一圈，兩顆之間留底色縫（第一次試在灰骰左上加兩道灰白短動線，30 的圖裡讀成一塊碎片，拿掉）。
  //    和「擲出自然 20」（一顆大骰子寫 20）、「賭注」（白色方骰）、「反應」（綠色回轉箭頭）分：兩顆骰子一前一後、一亮一灰。
  //    ≤14px（18 的圓片）兩顆都留（只剩一顆就是自然 20／賭注），灰骰縮小、往角落推，縫拉開。
  // =====================================================================
  const GOLD = { body: "#ffc23a", hi: "#fff0a8" };
  function rerollArt(c, o) {
    const t = o.tiny;
    d20(c, t ? -5.0 : -4.8, t ? -5.0 : -4.8, t ? 5.0 : 5.6, DIE.dim);
    halo(c, o, (q) => d20(q, t ? 2.4 : 2.4, t ? 2.4 : 2.4, t ? 8.0 : 7.6, DIE.lav)); /* 前景骰包自己的一圈，和灰骰之間留一道底色縫 */
  }
  const EFFECT = {
    reroll: {
      zh: "重擲", topic: "前景一顆淡紫二十面骰（右下、大），後面一顆往左上退、縮小、變灰的骰子（同演出裡被換掉的那一顆）。不用圈狀箭頭",
      d: (c, o) => at(c, 0, 0, 0.98, (q) => rerollArt(q, o)),
    },
  };

  // =====================================================================
  // 3. 觸發三個（開發頁實際用到的；TRIG_ALIAS 暫借 on_status_applied、ally_hit_adjacent、hit_by_attack）。
  //    家族照第④批：「施加狀態後」＝淡紫小旗；「身旁隊友受擊時」＝綠人形＋右上記號；「被攻擊時」＝左上大的來襲物＋右下小藍盾。
  // =====================================================================
  /** 別人的手（第 2 版必修 M2）：膚色（同第④批「激昂」的手臂 #f0c49a／亮 #ffe8d0／暗 #c8885a），從右邊伸進來、食指朝左指。
   *  原點＝食指指尖，手往 +x 長（指頭 → 握起來的三指與手背）。≤14 只留食指＋手掌一塊。 */
  const SKIN = { body: "#f0c49a", hi: "#ffe8d0", dk: "#c8885a" };
  function hand(c, o) {
    rr(c, SKIN.body, -0.2, -1.5, 7.4, 3.0, 1.5); /* 食指 */
    rr(c, SKIN.body, 4.6, -2.6, 6.6, 7.4, 2.6); /* 手背＋握起來的三指 */
    el(c, SKIN.body, 6.4, -2.4, 2.4, 1.4, -0.2); /* 拇指（壓在食指根上） */
    if (!o.tiny) {
      for (const y of [1.4, 3.4]) ln(c, SKIN.dk, 0.8, [[5.2, y], [7.4, y]]); /* 握起來的指節縫 */
      el(c, SKIN.hi, 2.6, -0.7, 2.0, 0.5); el(c, SKIN.hi, 8.2, -1.4, 1.8, 0.7, -0.2);
    }
  }
  /** 碰觸點的短亮線（金，不是星形、不是火花）：從 (x,y) 往左上、左、左下各一道短線，外框色墊底；≤14 一道。 */
  function touchLines(c, o, x, y) {
    const L = o.tiny ? [[-0.7, -0.7]] : [[-0.6, -1.0], [-1.0, 0.05], [-0.6, 1.0]];
    for (const [dx, dy] of L) { const a = [x + dx * 1.6, y + dy * 1.6], b = [x + dx * (o.tiny ? 4.4 : 4.0), y + dy * (o.tiny ? 4.4 : 4.0)]; ln(c, OUT, o.tiny ? 2.8 : 2.6, [a, b]); ln(c, "#ffd23f", o.tiny ? 1.6 : 1.3, [a, b]); }
  }
  const TRIG = {
    on_keyword_exploited: {
      /* 第 2 版（必修 M2）：拿掉閃電（＝元素「雷」）。小旗不再縮到 0.84、左下不被蓋；右邊伸進來一隻別人的手，食指碰到旗的右緣，碰觸點三道短金線（亮起來）。 */
      zh: "你造的關鍵字被利用時", topic: "淡紫小旗（同「施加狀態後」＝你造的關鍵字），右邊伸進來一隻膚色的手、食指碰到旗的右緣，碰觸點三道短金色亮線（別人拿你的東西去用）",
      d: (c, o) => at(c, 0, 0, 0.98, (u) => {
        at(u, -2.7, 1.1, 0.88, (q) => banner(q, { ...o, tiny: true })); /* 旗上的白星拿掉（金色亮線落在星的位置會疊成一團），其他照「施加狀態後」 */
        halo(u, o, (q) => at(q, 3.0, -3.3, 0.72, (p) => hand(p, o), 0.1)); /* 0.72：手腕收進色環 */
        touchLines(u, o, 2.9, -3.5);
      }),
    },
    ally_missed_roll: {
      /* 第 2 版（必修 M3）：人形照「身旁隊友受擊時」完整畫（同位置、同大小）；骰子縮小推到右上角、換成灰骰（DIE.dim＝演出裡被劃掉的那一顆）加紅斜槓，和人頭之間留縫。 */
      zh: "隊友擲失手時", topic: "綠色人形（同「身旁隊友受擊時」，完整），右上角一顆小的灰色二十面骰被一道紅斜槓劃掉（同演出裡失敗的那一顆、同「沒有」的語言）",
      d: (c, o) => { bust(c, ALLY, -3.4, 1.4, 0.92); halo(c, o, (q) => { d20(q, 5.4, -5.2, o.tiny ? 4.6 : 4.3, DIE.dim); const S = [[2.8, -2.6], [8.0, -7.8]]; if (o.tiny) ln(q, OUT, 3.6, S); ln(q, "#ff4a5a", o.tiny ? 2.0 : 1.8, S); }); },
    },
    enemy_hit_roll: {
      zh: "敵人擲中你時", topic: "左上一顆大的紅色二十面骰（佔一半、微斜），砸向右下的小藍盾（同「被攻擊時」的家族）",
      /* 第 2 版（可修 3）：≤14 中央白三角放大 1.3 倍、暗面深一階（#a82434）、亮面純白，切面留得下來 */
      d: (c, o) => at(c, 0, 0, 0.94, (u) => { shieldAt(u, o); halo(u, o, (q) => d20(q, -3.2, -3.2, 7.4, o.tiny ? DIE.redT : DIE.red, { rot: -0.26, hiK: o.tiny ? 1.3 : 1 })); }),
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
        for (const [x, y] of o.tiny ? [[-0.47, -2.07]] : [[-1.36, -1.61], [0.42, -2.53]]) ci(c, "#ffd23f", x, y, o.tiny ? 2.0 : 1.15); /* 人形頭緣到靶緣之間的縫（約 5.2 單位）裡等距；第 2 版（可修 5）：≤14 半徑 1.5 → 2.0（16 的真 1 倍約 2 px） */
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
  // 5. 戰場：重擲的骰子層（模型像素，1 格 48）。演出只畫骰子、金色引線、敲一下的短亮線、比較箭頭、「採用」字；單位與身體動作照現行。
  //    MK＝畫面下限的倍率（同 SK-2 的鎖鏈：骰子外接半徑 ≥ 9 畫面 px → MK＝max(1, 9 ÷ (DIE_R × 地圖縮放))）。
  //    第 2 版（必修 M4，美術 PM 裁定）：骰子不再放頭頂上方（腳底往上 60 會蓋到上一排的血條與腳），改在擲骰者自己那一格「頭頂到血條之間」：
  //    骰子整組的上緣（採用時金環的外框）收在上一排血條下緣再往下 1；第一次的骰子往左（同一排）退，不往左上。
  //    人形的頭頂（unitSprite.ts unitTopY＝FEET − 38 × (T/52) × 1.06）在格子中心往上 26.1，上一排血條下緣在往上 25.7，兩者幾乎同高，
  //    頭頂上方沒有放骰子的空間，所以骰子蓋在擲骰者自己的身上（臉與胸口），1.45 秒後淡出、接現行的命中／失手。
  // =====================================================================
  const DIE_R = 11, DIE_MIN_PX = 9; let MK = 1, MAP_S = 1;
  const setMapScale = (S) => { MAP_S = S; MK = Math.max(1, DIE_MIN_PX / (DIE_R * S)); return MK; };
  const KEEP_K = 1.1, RING_K = 1.2; /* 採用的那顆放大 1.1；金環半徑 1.2R（第 1 版 1.32，收小才放得進一格） */
  const UPPER_HP_BOTTOM = -48 + 48 * 0.36 + 5; /* 上一排血條的下緣（相對擲骰者格子中心；HP 條在 c.y＋0.36T、高 5） */
  /** 骰子整組的「上半徑」：採用時的金環外框（R × 1.1 × 1.2 ＋ 外框色線寬的一半）。 */
  const envelope = () => DIE_R * MK * KEEP_K * RING_K + 2.1 * MK;
  /** 骰子中心相對擲骰者格子中心的 y（往下為正）。1600 寬（MK 1）＝−8.1，800 寬（MK 1.54）＝＋0.9。 */
  const dieDy = () => UPPER_HP_BOTTOM + 1 + envelope();
  /** 第一次的骰子退到哪（相對骰子原位）：往左 30、往下 2（× MK），同一排、不往上。 */
  const oldOff = () => ({ x: -30 * MK, y: 2 * MK });
  /** 新骰子跳起來最多多高：不超過採用時的上緣（不碰上一排）。 */
  const jumpMax = () => envelope() - DIE_R * MK;
  /** 戰場上的一顆骰子：中心 (x,y)；k 縮放（彈出、落地壓扁用 sy）；a 透明度；pal；face 數字；ring＝外面一圈「採用」的金環（0～1）；cross＝紅斜槓（0～1）。
   *  第 2 版（可修 2）：被劃掉的那顆淡到 70%（第 1 版 45%），點數在紅斜槓之上再描一次，19 → 2 的 19 讀得出。 */
  function fieldDie(g, x, y, opt = {}) {
    const R = DIE_R * MK * (opt.k ?? 1), a = opt.a ?? 1; if (R < 0.5 || a <= 0) return;
    const pal = opt.pal ?? DIE.lav;
    g.save(); g.globalAlpha *= a; g.translate(x, y); g.scale(1, opt.sy ?? 1);
    if (opt.ring > 0) { g.save(); g.globalAlpha *= opt.ring; Q.H.glow(g, 0, 0, R * 1.9, "#ffe066", 0.5); g.beginPath(); g.arc(0, 0, R * RING_K, 0, TAU); g.lineWidth = 4.2 * MK; g.strokeStyle = OUT; g.stroke(); g.lineWidth = 2.2 * MK; g.strokeStyle = "#ffd23f"; g.stroke(); g.restore(); }
    d20(g, 0, 0, R, pal, { rot: opt.rot ?? 0, face: opt.face, ink: 1.6 * 10.6 / R * MK });
    if (opt.flash > 0) { g.save(); g.globalAlpha *= opt.flash; at(g, 0, 0, R / 10.6, (q) => poly(q, "#ffffff", HEX, 0.5), opt.rot ?? 0); g.restore(); } /* 白閃：一般疊色（不用 lighter，淡紫加白會整顆變白、看不到點數） */
    if (opt.cross > 0) {
      const L = R * 0.95 * opt.cross; g.lineCap = "round";
      for (const [w, col] of [[3.8 * MK, OUT], [2.0 * MK, "#ff4a5a"]]) { g.beginPath(); g.moveTo(-R * 0.95, R * 0.95); g.lineTo(-R * 0.95 + 2 * L, R * 0.95 - 2 * L); g.lineWidth = w; g.strokeStyle = col; g.stroke(); }
      if (opt.face != null) at(g, 0, 0, R / 10.6, (q) => { const s = String(opt.face); q.font = `900 ${s.length > 1 ? 7.2 : 8.4}px Arial, sans-serif`; q.textAlign = "center"; q.textBaseline = "middle"; q.lineJoin = "round"; q.lineWidth = 1.6; q.strokeStyle = pal.face; q.strokeText(s, 0, 1.4); q.fillStyle = pal.ink; q.fillText(s, 0, 1.4); }, opt.rot ?? 0);
    }
    g.restore();
  }
  /** 敲一下（第 2 版：取代第 1 版的金色 ↻，和新部件同一個說法＝這一顆要被換掉）：骰子左右各兩道短金線往外彈、淡出；只往左右，不往上（不碰上一排）。p＝0～1。 */
  function fieldKnock(g, x, y, p) {
    if (p <= 0 || p >= 1) return;
    const R = DIE_R * MK, e = ease(p), a = 1 - p;
    g.save(); g.globalAlpha *= a; g.lineCap = "round";
    for (const ang of [-0.32, 0.32, PI - 0.32, PI + 0.32]) {
      const c0 = Math.cos(ang), s0 = Math.sin(ang), r0 = R * (1.15 + 0.35 * e), r1 = r0 + R * (0.55 - 0.15 * e);
      for (const [w, col] of [[3.6 * MK, OUT], [1.8 * MK, "#ffd23f"]]) { g.beginPath(); g.moveTo(x + c0 * r0, y + s0 * r0); g.lineTo(x + c0 * r1, y + s0 * r1); g.lineWidth = w; g.strokeStyle = col; g.stroke(); }
    }
    g.restore();
  }
  /** 「採用」（玩法 PM 定案的字；字型照現行浮字：Noto Sans TC 700、黑邊、金色 #ffe066〔浮字 good 色〕）：壓在算數的那一顆下半（點數下面）。
   *  字級 12 模型 px，畫面下限 10 px（800 寬放大到 18.9）。a＝0～1（淡入、跟著整組淡出）。 */
  const ADOPT = "採用";
  function fieldAdopt(g, x, y, k, a) {
    if (a <= 0) return;
    const R = DIE_R * MK * k, px = Math.max(12, 10 / MAP_S), cy = y + R * 0.5 + px * 0.55;
    g.save(); g.globalAlpha *= a; g.font = `700 ${px}px 'Noto Sans TC','Microsoft JhengHei',sans-serif`; g.textAlign = "center"; g.textBaseline = "middle";
    g.lineJoin = "round"; g.strokeStyle = "#000"; g.lineWidth = Math.max(3, px * 0.24); g.strokeText(ADOPT, x, cy); g.fillStyle = "#ffe066"; g.fillText(ADOPT, x, cy);
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

  return { DIE, d20, EFFECT, TRIG, COND, LIVE, install, setMapScale, mk: () => MK, dieDy, oldOff, jumpMax, envelope, KEEP_K, ADOPT, fieldDie, fieldKnock, fieldAdopt, fieldBeam, fieldPulse, fieldCmp, placeMark, placeBurst, PLACE, ease, span, lerp, clamp, GOLD };
})();
