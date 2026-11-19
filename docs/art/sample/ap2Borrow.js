// ap2Borrow.js：AP-2「預支」三樣暫借美術的正式樣張（畫圖 agent，2026-11-19；紀錄 docs/art/AP-2-美術.md）。
// 範圍（PhaseAP-2報告 第 7 節第 6 點）：
//   ① 狀態「預支」borrowed_ap（取代 client/src/render/qIcon/status.ts 暫借透支的閃電＋橘色減號）；
//   ② 效果原語「預支」borrow_ap 的 Q 版部件（取代 parts.ts EFFECT_ALIAS 暫借的 grant_ap）與施放演出（取代 skillClips.ts 暫借的 shoulder_tap）；
//   ③ 觸發「這回合用完所有 AP 時」on_ap_spent_all 的 Q 版部件（取代 TRIG_ALIAS 暫借的 on_turn_end）。
// 畫法語言照第④批部件（qIconsParts.js）：±10 單位、平塗三階、剪影外框、後畫的那件用 halo() 自己再包一圈；≤14px（o.tiny）不包外框、省小零件。
// 題材：AP 列（AP-1-AP列畫法.md 第 2 節）已經有「預支來的那格＝橘色菱形 #ff9a3a／框 #b8641a」「下回合會少的那格＝空心圓＋紅斜線 #e05a4a、灰框 #8a7a5a」，
//   狀態、效果、演出都用這一對（玩家施放後在 AP 列看到的就是這兩樣）；觸發用「卡片 AP 的閃電」變成用掉的灰色。
// 不改任何過審的畫法檔：新圖樣只在頁面呼叫 install() 時塞進 QIconsParts.CATS、QIconsStatus.NEW 與樣張端的名詞表（同 SK-3、KW 的作法）。
// 確定性：沒有 Math.random；演出只吃 t（毫秒）。
window.AP2Borrow = (() => {
  const Q = window.QIcons, QP = window.QIconsParts, QST = window.QIconsStatus;
  const { mix, f, rr, ci, el, poly, ln, starPts, halo } = Q.H;
  const TAU = Math.PI * 2, OUT = "#16121a";
  const at = (c, x, y, k, fn, rot = 0) => { c.save(); c.translate(x, y); c.rotate(rot); c.scale(k, k); fn(c); c.restore(); }; /* 照抄 qIconsParts.js（沒有匯出） */
  const star4 = (c, col, x, y, R, core = "#ffffff") => { poly(c, col, starPts(x, y, R, R * 0.36, 4), 0.3); if (core) poly(c, core, starPts(x, y, R * 0.55, R * 0.2, 4)); }; /* 照抄 qIconsParts.js */
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const ease = (t) => { t = clamp(t); return t * t * (3 - 2 * t); };
  const span = (t, a, b) => clamp((t - a) / (b - a));
  const lerp = (a, b, t) => a + (b - a) * t;

  // =====================================================================
  // 色票：全部是現有的色（AP 列、SK-3 灰骰、第④批金），亮面照規則 2.1 混白。
  // =====================================================================
  const BORROW = { body: "#ff9a3a", dk: "#b8641a", hi: mix("#ff9a3a", "#ffffff", 0.45), glint: "#ffffff" }; /* AP 列預支菱形：實心橘＋框色；亮面＝本色混白 45%（HI） */
  const SLOT = { ring: "#8a7a5a", slash: "#e05a4a" }; /* AP 列「下回合會少的那格」：空心圓的灰框＋紅斜線（戰場演出照這一組） */
  const SLOT_ICON = { ring: mix("#8a7a5a", "#ffffff", 0.35), slash: "#ff4a5a" }; /* 圖示裡：灰框在深底上亮一階（規則 6：暗色零件換亮一階的同類色）；紅斜線用第④批「沒有」的紅 */
  const SPENT = { body: "#a9a6bc", dk: "#6e6a84", hi: "#dcdae6" }; /* SK-3 的灰骰（DIE.dim）＝「用掉、被換掉」；這裡給用完的 AP 閃電 */
  const SPARK = "#ffd23f";

  /** 圖樣本身的 CSS px（render 給的 o.u＝48 格裡 1 CSS px 是幾單位；圖樣本身＝48 格的 1/BOX）。 */
  const cpxOf = (o) => 36 / (o.u || 2);

  // =====================================================================
  // 1. 預支的兩個零件
  // =====================================================================
  /** 預支來的那格：橘色寶石菱形（中心 x,y、半對角 R）。一般：四個斜面（左上亮、右下暗）＋中間的桌面＋左上一點白；tiny：左上亮半、右下暗半兩階。 */
  function gem(c, o, x, y, R) {
    const T = [x, y - R], Rt = [x + R, y], B = [x, y + R], L = [x - R, y];
    poly(c, BORROW.body, [T, Rt, B, L], 0.5);
    if (o.tiny) { poly(c, BORROW.hi, [T, L, [x - R * 0.12, y - R * 0.12]]); poly(c, BORROW.dk, [Rt, B, [x + R * 0.12, y + R * 0.12]]); return; }
    const k = 0.46, t = [x, y - R * k], rt = [x + R * k, y], b = [x, y + R * k], l = [x - R * k, y];
    poly(c, BORROW.hi, [T, L, l, t]); /* 左上斜面（亮） */
    poly(c, BORROW.dk, [Rt, B, b, rt]); /* 右下斜面（暗＝AP 列菱形的框色） */
    poly(c, mix(BORROW.body, "#ffffff", 0.18), [t, rt, b, l]); /* 桌面：本色稍亮一點 */
    el(c, BORROW.glint, x - R * 0.42, y - R * 0.36, R * 0.16, R * 0.09, -0.78); /* 左上一點白 */
  }
  /** 下回合會少的那格：深色圓洞、灰框、裡面一道紅斜線（左下到右上；AP 列同一個寫法）。洞用外框色＝自查不算進亮度。 */
  function slot(c, o, x, y, r) {
    ci(c, SLOT_ICON.ring, x, y, r);
    ci(c, OUT, x, y, r - (o.tiny ? 1.7 : 1.35));
    const d = r * 0.6, S = [[x - d, y + d], [x + d, y - d]];
    ln(c, SLOT_ICON.slash, o.tiny ? 2.3 : 1.9, S);
  }
  /** 預支（狀態與效果同一個圖：名詞表兩個都叫「預支」）：左上一顆大的橘色菱形（預支來的那格），右下一個小的「下回合會少的那格」。
   *  狀態頭頂 11（圖樣本身 <8 px）只留菱形、放大置中、中間挖一個深色小菱形（規則 8：只留一個主體）。 */
  function borrowArt(c, o) {
    if (cpxOf(o) < 8) { gem(c, o, 0, 0, 10.2); poly(c, OUT, [[0, -3.4], [3.4, 0], [0, 3.4], [-3.4, 0]]); return; } /* 頭頂 11：中間挖一個深色小菱形（同 AP 列菱形的框形），實心一團會和「燃燒」的橘火在紅框裡分不開 */
    if (o.tiny) { gem(c, o, -2.8, -2.8, 7.8); halo(c, o, (q) => slot(q, o, 5.0, 5.0, 4.9)); return; } /* tiny：菱形小一點、那格大一點（真 1 倍要看得到圈與斜線） */
    gem(c, o, -2.5, -2.5, 8.3);
    halo(c, o, (q) => slot(q, o, 5.3, 5.3, 4.3));
  }

  // =====================================================================
  // 2. 觸發：這回合用完所有 AP 時
  // =====================================================================
  /** 卡片 AP 的閃電（qIconsParts.js bolt 的外形原樣），換成用掉的灰色三階；右側下半一塊暗面。 */
  function spentBolt(c, o) {
    poly(c, SPENT.body, [[1.6, -10.6], [-7.6, 1.6], [-1.6, 1.6], [-4.2, 10.6], [7, -2.6], [1, -2.6], [4.2, -10.6]], 0.5);
    poly(c, SPENT.dk, [[7, -2.6], [1, -2.6], [-0.2, 0.2], [2.2, 0.2], [-4.2, 10.6]]); /* 下半右側的暗面 */
    if (!o.tiny) poly(c, SPENT.hi, [[1.8, -9.4], [-5.6, 0.6], [-3.4, 0.6], [3.2, -9.4]]); /* 同 bolt 的亮條 */
  }
  /** 這回合用完所有 AP 時：灰色的閃電（AP 用光了），左下尖端掉出最後一顆金色火花。tiny：灰閃電＋一顆不帶白芯的金火花。 */
  function spentAll(c, o) {
    at(c, 0.8, 0, 0.9, (q) => spentBolt(q, o));
    halo(c, o, (q) => star4(q, SPARK, -5.6, 6.0, o.tiny ? 3.9 : 3.7, o.tiny ? null : "#ffffff"));
  }

  const ENTRY = {
    effect: { borrow_ap: { zh: "預支", topic: "左上一顆大的橘色寶石菱形（AP 列「預支來的那格」），右下一個深色小圓洞、灰框裡一道紅斜線（AP 列「下回合會少的那格」）", d: (c, o) => borrowArt(c, o) } },
    trigger: { on_ap_spent_all: { zh: "這回合用完所有 AP 時", topic: "卡片 AP 的閃電換成用掉的灰色，左下尖端掉出最後一顆金色四芒火花", d: (c, o) => spentAll(c, o) } },
    status: { borrowed_ap: { zh: "預支", topic: "同效果「預支」：橘色寶石菱形＋右下的「下回合會少的那格」；頭頂 11 只留菱形", d: (c, o) => borrowArt(c, o) } },
  };
  /** 現行（暫借）：效果、觸發畫被借的那個；狀態畫遊戲端 client/src/render/qIcon/status.ts 第 122 行的暫用圖（透支的黃閃電＋橘色減號，原樣抄）。 */
  const boltY = (c, o) => { poly(c, "#ffd23a", [[1.6, -10.6], [-7.6, 1.6], [-1.6, 1.6], [-4.2, 10.6], [7, -2.6], [1, -2.6], [4.2, -10.6]], 0.5); if (!o.tiny) poly(c, "#fff6b0", [[1.8, -9.4], [-5.6, 0.6], [-3.4, 0.6], [3.2, -9.4]]); }; /* qIconsStatus.js bolt 原樣 */
  const LIVE_STATUS = { zh: "預支（現行暫用）", topic: "黃閃電（同卡片 AP），右下一個橘色減號（status.ts 第 122 行）", d: (c, o) => { at(c, -1.6, -0.6, 0.95, (q) => boltY(q, o)); halo(c, o, (q) => rr(q, "#ff9a3a", 2.6, 5.4, 8.6, 3.4, 1.2)); } };
  const LIVE = { "effect:borrow_ap": ["effect", "grant_ap"], "trigger:on_ap_spent_all": ["trigger", "on_turn_end"], "status:borrowed_ap": ["status", "borrowed_ap__live"] };
  /** 名詞表（client/src/battle/fixtures/glossary.json）的 borrowed_ap：樣張端的 qPartsData.js 還沒有，狀態框的極性靠它（debuff＝圓角方框、紅框）。 */
  const GLOSS = { id: "borrowed_ap", name_zh: "預支", description_zh: "這回合預支了 AP，下一個回合開始時 AP 少同樣的數量。", tags: [], status_look: { polarity: "debuff", control_group: null, dot_element: null, skip_turn: false, removed_by_element: [], absorbs_damage: false, prevents_move: false }, rules_zh: [] };

  function install() {
    QP.CATS.effect.borrow_ap = { ...ENTRY.effect.borrow_ap, src: "new:ap2" };
    QP.CATS.trigger.on_ap_spent_all = { ...ENTRY.trigger.on_ap_spent_all, src: "new:ap2" };
    QST.NEW.borrowed_ap = { ...ENTRY.status.borrowed_ap };
    QST.NEW.borrowed_ap__live = { ...LIVE_STATUS };
    const G = window.QPARTS_GLOSSARY.statuses;
    if (!G.some((s) => s.id === "borrowed_ap")) G.push(GLOSS, { ...GLOSS, id: "borrowed_ap__live", name_zh: "預支（現行暫用）" });
  }

  // =====================================================================
  // 3. 施放演出（戰場，模型像素，一格 48）：只對自己、0 AP、≤ 320 ms（同現行給予 AP 的拍肩 shoulder_tap 320 ms）。
  //    身體：伸出另一隻手往前上方一抓、再拉回胸前（照 SK-2 已過審的 CASTER_POSE：cast＝前伸、pull＝後拉）。
  //    特效：施放者面前、胸口前方（手持武器的外側）浮出「下回合的那格」（灰框空心圓，不透明度 0.8，同 AP 列），裡面一顆橘色菱形；
  //          菱形被拉出來、沿短弧飛進施放者胸口，留下的空格畫上紅斜線（＝下回合會少的那格）、淡出；菱形到胸口時一圈橘色光圈。
  //    沒有別的單位、沒有從外面飛進來的東西：來源是自己面前、自己的手拉回來。
  // =====================================================================
  const GEM_R = 5, SLOT_R = 6.5, MIN_GEM_PX = 4.5; let MK = 1;
  /** 畫面下限：菱形半對角 ≥ 4.5 畫面 px（＝畫面上 9 px，同 AP 列的菱形）。1600 寬（地圖縮放 1.31）＝1，800 寬（0.53）＝1.70。 */
  const setMapScale = (S) => { MK = Math.max(1, MIN_GEM_PX / (GEM_R * S)); return MK; };
  const TIMES = { slotIn: [0, 90], pull: [100, 230], slash: [150, 220], arrive: [215, 320], slotOut: [230, 320], ms: 320 };
  const UPPER_HP_BOTTOM = -48 + 48 * 0.36 + 5; /* 上一排血條下緣（相對格子中心）；同 sk3Mechanics.js */
  /** 「下回合的那格」相對施放者格子中心的位置（dir＝面向 ±1）：胸口前方 17＋(MK−1)×8（在手杖、劍的外側；第一次放臉前方會疊在杖頭上）、格子中心往上 9；整顆上緣不高於上一排血條下緣再往下 1。 */
  function slotAt(dir) {
    const rOut = (SLOT_R + 1.9) * MK, y = Math.max(-9, UPPER_HP_BOTTOM + 1 + rOut), x = 17 + (MK - 1) * 8; /* 800 寬（MK 1.7）那格變大，往前推到 22.6（外緣超出格子約 11，到右邊那格單位身體的左緣），不然整顆蓋在施放者身上 */
    return { x: dir * x, y };
  }
  /** 菱形（模型 px）：gem 的戰場版（外框色描一圈 1.2×MK）。 */
  function fieldGem(g, x, y, k = 1, a = 1) {
    const R = GEM_R * MK * k; if (R < 0.3 || a <= 0) return;
    g.save(); g.globalAlpha *= a; g.lineJoin = "round";
    g.beginPath(); g.moveTo(x, y - R); g.lineTo(x + R, y); g.lineTo(x, y + R); g.lineTo(x - R, y); g.closePath(); g.strokeStyle = OUT; g.lineWidth = 2.4 * MK; g.stroke();
    at(g, x, y, R / 10, (q) => gem(q, { tiny: R * 2 < 14 }, 0, 0, 10));
    g.restore();
  }
  /** 「下回合的那格」（模型 px）：灰框空心圓（洞是半透明深色）、不透明度 0.8；slash＝紅斜線畫到哪（0～1）。 */
  function fieldSlot(g, x, y, k, a, slash) {
    const r = SLOT_R * MK * k; if (r < 0.3 || a <= 0) return;
    g.save(); g.globalAlpha *= a * 0.8;
    g.beginPath(); g.arc(x, y, r, 0, TAU); g.fillStyle = "rgba(10,12,18,0.55)"; g.fill(); g.lineWidth = 3.8 * MK; g.strokeStyle = OUT; g.stroke(); g.lineWidth = 2.0 * MK; g.strokeStyle = SLOT_ICON.ring /* 地面上灰框 #8a7a5a 看不出來（石板、草地都是中灰），換圖示用的亮一階 */; g.stroke();
    if (slash > 0) { const d = r * 0.62, x0 = x - d, y0 = y + d, x1 = lerp(x0, x + d, slash), y1 = lerp(y0, y - d, slash); g.lineCap = "round"; for (const [w, col] of [[3.6 * MK, OUT], [2.0 * MK, SLOT_ICON.slash]]) { g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y1); g.lineWidth = w; g.strokeStyle = col; g.stroke(); } }
    g.restore();
  }
  /** 菱形到胸口的一下：一圈橘色光圈往外擴、淡出（p＝0～1）。 */
  function fieldArrive(g, x, y, p) {
    if (p <= 0 || p >= 1) return; const e = ease(p), r = (4 + 7 * e) * MK;
    g.save(); g.globalAlpha *= 1 - p; g.beginPath(); g.arc(x, y, r, 0, TAU); g.lineWidth = 3 * MK; g.strokeStyle = OUT; g.stroke(); g.lineWidth = 1.6 * MK; g.strokeStyle = BORROW.body; g.stroke(); g.restore();
  }
  /** 演出的特效層：c＝施放者格子中心、chest＝胸口（模型 px）、dir＝面向、t 毫秒。 */
  function borrowFx(g, t, c, chest, dir) {
    if (t < 0 || t > TIMES.ms) return;
    const s = slotAt(dir), sx = c.x + s.x, sy = c.y + s.y;
    const sIn = ease(span(t, ...TIMES.slotIn)), sOut = span(t, ...TIMES.slotOut);
    const sk = t < TIMES.slotIn[1] ? 0.6 + 0.4 * sIn : 1;
    fieldSlot(g, sx, sy, sk, sIn * (1 - sOut), ease(span(t, ...TIMES.slash)));
    const p = ease(span(t, ...TIMES.pull));
    /* 短弧：從那格往施放者胸口，中點往上拱 6×MK（不往下穿過身體） */
    const mx = (sx + chest.x) / 2, my = Math.min(sy, chest.y) - 6 * MK, u = 1 - p;
    const gx = u * u * sx + 2 * u * p * mx + p * p * chest.x, gy = u * u * sy + 2 * u * p * my + p * p * chest.y;
    const arr = span(t, ...TIMES.arrive), gk = (t < TIMES.pull[0] ? 0.72 * (0.6 + 0.4 * sIn) : lerp(0.72, 1, ease(span(t, TIMES.pull[0], 170)))) * (1 - 0.35 * ease(arr)); /* 在那格裡是 0.72（框看得到），拉出來長到 1 */
    fieldArrive(g, chest.x, chest.y, arr);
    fieldGem(g, gx, gy, gk, (t < 40 ? sIn * 1.6 : 1) * (1 - ease(span(t, 260, 320))));
  }
  /** 身體姿勢（樣張端 QDoll 的 pose；照 SK-2 sk2-primitives.html 的 CASTER_POSE）：0–110 前伸、110–240 拉回、240 以後回到站姿。 */
  const POSE = { cast: { lean: 0.1, armL: -0.9 }, pull: { lean: -0.18, armL: -0.5 } };
  const poseAt = (t) => (t < 0 || t >= 240 ? null : t < 110 ? POSE.cast : POSE.pull);

  return { ENTRY, LIVE, GLOSS, BORROW, SLOT, SPENT, install, gem, slot, borrowArt, spentBolt, spentAll, cpxOf, setMapScale, mk: () => MK, slotAt, fieldGem, fieldSlot, fieldArrive, borrowFx, poseAt, POSE, TIMES, GEM_R, SLOT_R, ease, span, lerp, clamp };
})();
