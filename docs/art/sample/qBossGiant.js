// qBossGiant.js：灰燼之心 3×3 巨型版（Phase GB 美術 A1 立繪＋A2 部位格標示，畫圖 agent，2026-11-14）。
// 紀錄：docs/art/GB巨型頭目-美術.md 第 3 節；樣張頁：giant-boss.html；重拍：tools/giant_boss_shots.py。
//
// 造型照 qBoss.js 的灰燼之心（Q 版）擴成佔 3 格寬的正面（朝南）造型；qBoss.js 原檔不動（殼片的 FNV-1a 雜湊照抄同一個函式、同一組殼片名稱）。
//   畫法語言同 qBoss.js：純色平塗、部件細縫線、整隻剪影粗外框（QCreature.layer），頭目外光＝剪影膨脹的平塗金光（QK-4b）。
//   線寬、外框、外光照 qBoss 在戰場上的倍率換成模型像素（G＝qBoss 1 單位在戰場上的模型像素＝K×1.6），所以外框和現在的 1 格灰燼之心一樣粗。
// 座標：模型像素（1 格 48），原點＝錨點＝3×3 南排的南緣中點（中心格中心往南 72）；y 往上是負。
//   佔格 x −72～72、y −144～0；北排（噴口）y −144～−96，中排（殼縫｜核心｜殼縫）y −96～−48，南排（前殼）y −48～0。
// 部件（由北往南、由後往前畫）：
//   噴口 vent：北排三格各一支熔岩煙囪（x −47、0、47），口裡是熔岩；中間那支最高。
//   背殼 dome：整座熔岩甲蟲殼堆成的岩丘（本體，不是部位），後高前低。
//   殼縫 seam：中排東、西兩側殼上的熔岩裂縫（兩格同一個部位）；從側面看得到，算「從背後」。
//   核心 core：中心格的殼窩裡；第 1 階段被兩片殼蓋（lid）合起來，只從中縫透光；第 2 階段起殼蓋往兩側掀開、核心露出呼吸。
//   前殼 front：南排三隻熔岩甲蟲的背殼（本體），頭朝南、兩點火眼。
//   熔殼 plates（狀態 molten_shell）：qBoss 的 10 片殼片放大圍住殼窩；不在＝依名稱雜湊（FNV-1a）飛出、落在兩側前角，變暗。
// 確定性：沒有 Math.random；動畫只吃 st.t。
window.QBossGiant = (() => {
  const QC = window.QCreature, { mix, light, dark, OUT, layer } = QC;
  const TAU = Math.PI * 2;
  const T = 48; // client/src/battle/geometry.ts TILE_SIZE
  const K = (T / 52) * 1.06; // rendererBase.ts DOLL_PX
  const G = K * QC.SIZES.huge; // qBoss 1 單位在戰場上的模型像素（stampField：K × SIZES.huge）≈ 1.566
  const OW = 1.3 * G, GLOW_W = 2.2 * G, GLOW_A = 0.8, GOLD = "#ffbf3a"; // 外框、頭目外光（qBoss GLOW_W 2.2、GLOW_A 0.8，換成模型像素）
  const BOX = [-96, -214, 96, 16]; // 圖層範圍（模型像素）
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const num = (v, d) => (typeof v === "number" && Number.isFinite(v) ? v : d);
  // FNV-1a（照抄 qBoss.js seedOf／rnd，同 inkStyle.seedOf）
  function seedOf(s) { let h = 2166136261; for (const ch of s) h = Math.imul(h ^ (ch.codePointAt(0) ?? 0), 16777619); return h >>> 0; }
  const rnd = (key, k = 0) => (seedOf(`${key}:${k}`) % 10000) / 10000;

  // ---- 色（照 qBoss.js 灰燼之心；沒有新色票） ----
  const BASALT = "#4a3b36", BASALT_L = "#6a5a52", LAVA = "#ff6a1a", LAVA_HOT = "#ffd23a", CORE = "#ffb23a", EMBER = "#7a2a08";
  const CAVE = mix(BASALT, OUT, 0.55), COOL = "#2a221e", PLUG = "#3e332e"; // PLUG：A4 噴口封住的冷殼塞（比口裡的黑亮一階，讀成「塞了東西」不是空洞）

  // ---- 部位遮罩用的記號色：KEY＝部位 id 時，那個部位的所有色塊換成洋紅（兩張相減＝部位實際露出的像素，同 bossParts.js 的做法） ----
  let KEY = null;
  const KEYC = "#ff00ff";
  const kc = (part, c) => (KEY && KEY === part ? KEYC : c);

  const seamOf = (c) => (c === KEYC ? KEYC : mix(c, OUT, 0.55));
  const LW = 0.6 * G; // 部件細縫線（qBoss 0.6 單位）
  function path(g, pts) { g.beginPath(); pts.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y))); g.closePath(); }
  function poly(g, pts, c, opt = {}) { path(g, pts); g.fillStyle = c; g.fill(); if (opt.line !== false) { g.strokeStyle = seamOf(c); g.lineWidth = opt.lw ?? LW; g.lineJoin = "round"; g.stroke(); } }
  function ell(g, x, y, rx, ry, c, opt = {}) { g.beginPath(); g.ellipse(x, y, rx, ry, opt.rot ?? 0, 0, TAU); g.fillStyle = c; g.fill(); if (opt.line !== false) { g.strokeStyle = seamOf(c); g.lineWidth = opt.lw ?? LW; g.stroke(); } }
  function line(g, pts, w, c) { g.save(); g.strokeStyle = c; g.lineWidth = w; g.lineCap = "round"; g.lineJoin = "round"; g.beginPath(); pts.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y))); g.stroke(); g.restore(); }
  /** 破壞演出第 2 格「裂開」：部位上的亮金白裂紋（畫在本體圖層上、包在外框裡；同段 1 的裂紋色）。 */
  function crackLines(g, list, k = 1) { for (const pts of list) { line(g, pts, 2.2 * k, "#ffe08a"); line(g, pts, 0.9 * k, "#ffffff"); } }
  /** 平塗光暈：3 圈半透明同心圓（qBoss flatGlow）。 */
  function flatGlow(ctx, x, y, r, c, a, ry = r) { ctx.save(); ctx.fillStyle = c; for (const [k, al] of [[1, 0.16], [0.72, 0.2], [0.46, 0.26]]) { ctx.globalAlpha = al * a; ctx.beginPath(); ctx.ellipse(x, y, r * k, ry * k, 0, 0, TAU); ctx.fill(); } ctx.restore(); }

  // ---- 佔格與部位綁格（PhaseGB 計畫 D15、T11、T20） ----
  /** 3×3 每一格屬於哪個部位：[列（0 北、1 中、2 南）][欄（0 西、1 中、2 東）]。body＝前殼（本體，沒有部位）。 */
  const TILE_PART = [["vent", "vent", "vent"], ["seam", "core", "seam"], ["body", "body", "body"]];
  const PART_ZH = { vent: "熔岩噴口", seam: "殼縫", core: "核心", body: "前殼（本體）" };
  /** 一格的左上角（模型像素、相對錨點）。 */
  const tileXY = (row, col) => [(col - 1) * T - T / 2, -3 * T + row * T];

  // ---- 噴口（北排） ----
  // 第 2 版（審查必修 1）：錐身落在北排內（y −144～−96），兩側口在北排上緣內、中間口緣只探出北緣一點；背殼頂壓到 y −110，北排三格看得到三支錐身。
  const VENTS = [
    { x: -46, base: -90, top: -136, bw: 23, tw: 10, tilt: -0.16 },
    { x: 46, base: -90, top: -136, bw: 23, tw: 10, tilt: 0.16 },
    { x: 0, base: -96, top: -148, bw: 25, tw: 11, tilt: 0 },
  ];
  function vent(g, v, S, idx) {
    const h = v.base - v.top, sealed = S.ventSealed, P = "vent";
    g.save(); g.translate(v.x, v.base); g.rotate(v.tilt);
    const bw = v.bw, tw = v.tw;
    // 煙囪本體：圓錐形的噴氣丘（下寬上窄、兩側微鼓），外面一片片甲蟲殼像屋瓦往上疊
    const body = (q) => { q.beginPath(); q.moveTo(-bw, 6); q.quadraticCurveTo(-tw * 0.95, -h * 0.3, -tw, -h); q.lineTo(tw, -h); q.quadraticCurveTo(tw * 0.95, -h * 0.3, bw, 6); q.closePath(); }; // 火山錐：底外擴、腰內凹
    body(g); g.fillStyle = kc(P, BASALT); g.fill(); g.strokeStyle = seamOf(kc(P, BASALT)); g.lineWidth = LW; g.stroke();
    g.save(); body(g); g.clip();
    g.fillStyle = kc(P, light(BASALT, 0.12)); g.beginPath(); g.moveTo(-bw - 2, 6); g.quadraticCurveTo(-tw * 1.2, -h * 0.3, -tw + 2, -h); g.lineTo(-tw * 0.15, -h); g.quadraticCurveTo(-tw * 0.4, -h * 0.4, -bw * 0.3, 6); g.closePath(); g.fill(); // 左側亮面
    g.restore();
    const wAt = (yy) => { const t = Math.min(1, Math.max(0, -yy / h)), u = 1 - t; return u * u * bw + 2 * u * t * tw * 0.95 + t * t * tw; }; // 那個高度的半寬（同輪廓的二次曲線，近似）
    for (const [yy, n] of [[-h * 0.14, 3], [-h * 0.46, 2]]) { // 兩排殼瓦（突出輪廓一點，剪影不是直線）
      const hw = wAt(yy);
      for (let k = 0; k < n; k++) {
        const x = n === 1 ? 0 : -hw + (2 * hw * (k + 0.5)) / n, rx = hw / n + 2.2, ry = 5.2 - n * 0.4;
        ell(g, x, yy, rx, ry, kc(P, BASALT_L));
        g.save(); g.beginPath(); g.ellipse(x, yy, rx, ry, 0, 0, TAU); g.clip(); ell(g, x - rx * 0.3, yy - ry * 0.35, rx * 0.36, ry * 0.3, kc(P, light(BASALT_L, 0.22)), { line: false }); ell(g, x + rx * 0.3, yy + ry * 0.55, rx * 0.6, ry * 0.4, kc(P, dark(BASALT_L, 0.14)), { line: false }); g.restore();
      }
    }
    // 口緣與熔岩
    ell(g, 0, -h, tw + 2.6, 5.8, kc(P, BASALT_L));
    for (const [dx, r] of [[-tw - 1, 2.6], [tw + 0.6, 2.2], [-tw * 0.3, 2]]) ell(g, dx, -h - 3.6 + Math.abs(dx) * 0.08, r + 0.6, r, kc(P, BASALT_L)); // 口緣的疙瘩
    if (sealed) { // 破＝封住（A4 定稿）：冷殼塞住口、頂出口緣一點（鼓成一個黑殼塞），兩道灰裂；口緣溢出的熔岩也冷成黑色的硬流痕
      ell(g, 0, -h + 0.4, tw - 0.6, 3.6, kc(P, COOL));
      g.fillStyle = kc(P, PLUG); g.beginPath(); g.moveTo(-tw + 1.2, -h + 0.8); g.quadraticCurveTo(-tw * 0.55, -h - 4.6, 0, -h - 4.4); g.quadraticCurveTo(tw * 0.6, -h - 4.4, tw - 1.2, -h + 0.8); g.closePath(); g.fill();
      g.strokeStyle = seamOf(kc(P, PLUG)); g.lineWidth = LW; g.stroke();
      ell(g, -tw * 0.32, -h - 2.4, tw * 0.3, 1.1, kc(P, "#6e6259"), { line: false }); // 殼塞左上亮面
      line(g, [[-tw * 0.55, -h - 0.4], [-tw * 0.15, -h - 2.6], [tw * 0.05, -h - 0.6], [tw * 0.4, -h - 2.8]], 0.9, kc(P, "#7a706a"));
      for (const [dx, len] of [[-tw * 0.55, 7], [tw * 0.35, 10]]) { // 冷掉的溢流痕（同溢流的形，短一點）
        g.fillStyle = kc(P, COOL); g.beginPath(); g.moveTo(dx - 2, -h + 2.5); g.quadraticCurveTo(dx - 2.4, -h + 2.5 + len * 0.6, dx, -h + 2.5 + len * 0.85); g.quadraticCurveTo(dx + 2.4, -h + 2.5 + len * 0.6, dx + 2, -h + 2.5); g.closePath(); g.fill();
        g.fillStyle = kc(P, "#5a504a"); g.fillRect(dx - 0.5, -h + 3, 1, len * 0.45);
      }
    } else {
      const hot = S.ventFlare ? 1 : clamp(0.55 + 0.45 * S.breath * (S.phase === 1 ? 0.6 : 1));
      ell(g, 0, -h + 0.4, tw - 0.6, 3.6, kc(P, LAVA));
      ell(g, 0, -h + 0.1, tw - 5, 1.8, kc(P, mix(LAVA, LAVA_HOT, hot)), { line: false });
      // 口緣溢出的熔岩（熔毀階段流得長）
      const L = S.phase === 3 ? 1.9 : 1;
      for (const [dx, len] of [[-tw * 0.55, 7], [tw * 0.35, 10]]) {
        g.fillStyle = kc(P, LAVA); g.beginPath(); g.moveTo(dx - 2, -h + 2.5); g.quadraticCurveTo(dx - 2.4, -h + 2.5 + len * L * 0.7, dx, -h + 2.5 + len * L); g.quadraticCurveTo(dx + 2.4, -h + 2.5 + len * L * 0.7, dx + 2, -h + 2.5); g.closePath(); g.fill();
        g.fillStyle = kc(P, LAVA_HOT); g.fillRect(dx - 0.5, -h + 3, 1, len * L * 0.55);
      }
    }
    if (!sealed && S.spout > 0) { // 熔岩噴發時口上冒熔岩柱（qBoss spout 放大）
      const s = S.spout, H = 26 + 34 * s;
      g.fillStyle = kc(P, LAVA); g.beginPath(); g.moveTo(-tw + 3, -h); g.quadraticCurveTo(-tw - 2, -h - H * 0.6, 0, -h - H); g.quadraticCurveTo(tw + 2, -h - H * 0.6, tw - 3, -h); g.closePath(); g.fill();
      ell(g, 0, -h - H * 0.45, 3.4, H * 0.3, kc(P, LAVA_HOT), { line: false });
    }
    if (S.crackPart === "vent") crackLines(g, [[[-tw * 0.3, -h + 3], [-tw * 0.75, -h * 0.74], [-tw * 0.2, -h * 0.52], [-bw * 0.4, -h * 0.24]], [[tw * 0.45, -h + 3], [tw * 0.8, -h * 0.66], [tw * 0.3, -h * 0.42]]]);
    g.restore();
  }

  // ---- 背殼（岩丘，本體） ----
  // 第 2 版：頂壓到 y −110（北排留給噴口）；兩側不再是直線（可修 3）：輪廓微微起伏，另外兩側各貼兩隻探出輪廓的側甲蟲背（SIDE_SHELLS）。
  const DOME = [[-70, -3], [-73, -18], [-69, -36], [-72, -56], [-69, -76], [-60, -94], [-42, -106], [-20, -111], [0, -112], [20, -111], [42, -106], [60, -94], [69, -76], [72, -56], [69, -36], [73, -18], [70, -3]];
  function domePath(g) { g.beginPath(); g.moveTo(...DOME[0]); for (let i = 1; i < DOME.length - 1; i++) { const [x, y] = DOME[i], [nx, ny] = DOME[i + 1]; g.quadraticCurveTo(x, y, (x + nx) / 2, (y + ny) / 2); } g.lineTo(...DOME[DOME.length - 1]); g.closePath(); }
  function dome(g, S) {
    domePath(g); g.fillStyle = BASALT; g.fill();
    g.save(); domePath(g); g.clip();
    ell(g, -30, -100, 36, 12, light(BASALT, 0.12), { rot: -0.22, line: false }); // 左上亮面
    ell(g, 46, -52, 30, 44, dark(BASALT, 0.16), { rot: 0.1, line: false }); // 右下暗面
    // 岩丘上的甲蟲背（不會掉；qBoss 底座 4 隻甲蟲背的放大）。第 2 版：頂上兩隻跟著背殼壓低；殼縫格內側上半補一隻（可修 3，不壓裂縫、不碰內側下角的背刺小圖）
    for (const [x, y, rx, ry, r] of DOME_SHELLS) smallShell(g, x, y, rx, ry, r);
    g.restore();
    // 兩側探出輪廓的側甲蟲背（可修 3：剪影兩側不是直線）；在殼縫外側下方，不碰裂縫
    for (const s of [-1, 1]) smallShell(g, s * 67, -67, 6, 10, s * -0.12);
  }
  const DOME_SHELLS = [[-24, -101, 12, 6.5, -0.3], [24, -101, 12, 6.5, 0.3], [-44, -78, 6.5, 8.5, -0.2], [44, -78, 6.5, 8.5, 0.2]];
  /** 小甲蟲背（qBoss 底座甲蟲背）：圓背甲＋中線＋左上亮面。 */
  function smallShell(g, x, y, rx, ry, r) {
    ell(g, x, y, rx, ry, BASALT_L, { rot: r });
    g.save(); g.translate(x, y); g.rotate(r); line(g, [[0, -ry + 1], [0, ry - 1]], 0.9 * G * 0.7, OUT); ell(g, -rx * 0.35, -ry * 0.35, rx * 0.3, ry * 0.25, light(BASALT_L, 0.22), { line: false }); g.restore();
  }

  // ---- 殼縫（中排東西，兩格同一個部位） ----
  const SEAM = [[54, -93], [58, -83], [55, -72], [60, -62], [57, -52], [61, -44]];
  function seam(g, s, S) {
    // A4：cool＝冷掉的程度（0 熱、1＝破掉定稿），hot＝破壞演出第 2 格的過熱（縫發白）
    const P = "seam", pts = SEAM.map(([x, y]) => [s * x, y]), cool = S.seamCool, hot = S.crackPart === "seam";
    const heat = clamp(0.45 + 0.55 * S.breath);
    const oc = cool > 0 ? mix(EMBER, SEAM_COLD[0], cool) : EMBER, ic = hot ? LAVA_HOT : cool > 0 ? mix(LAVA, SEAM_COLD[1], cool) : LAVA;
    if (cool < 1) { g.save(); g.globalAlpha = 0.22 * (1 - cool) * (hot ? 1.8 : 1); line(g, pts, hot ? 13 : 10, kc(P, hot ? LAVA_HOT : LAVA)); g.restore(); } // 縫邊的熱光（平塗一圈）
    for (const [a, b] of [[1, [s * 64, -88]], [3, [s * 52, -60]]]) { line(g, [pts[a], b], 3.4, kc(P, oc)); line(g, [pts[a], b], 1.5, kc(P, ic)); }
    line(g, pts, 6.4, kc(P, oc));
    line(g, pts, 3.8, kc(P, ic));
    if (cool <= 0) line(g, pts, 1.5, kc(P, hot ? "#ffffff" : mix(LAVA, LAVA_HOT, heat)));
    else if (cool < 1) { g.save(); g.globalAlpha = 1 - cool; line(g, pts, 1.5, kc(P, mix(LAVA, LAVA_HOT, heat))); g.restore(); }
    else { // 破掉定稿：縫裡凝成黑殼，受光那側（左上）一條灰白的冷殼邊，讀成「硬掉了」而不只是一條黑線
      line(g, pts.map(([x, y]) => [x - 1.1, y - 0.4]), 0.9, kc(P, SEAM_COLD[2]));
      for (const [x, y] of [[58, -78], [57, -56]]) ell(g, s * x, y, 1.3, 1, kc(P, SEAM_COLD[2]), { line: false }); // 兩粒冷渣
    }
  }
  const SEAM_COLD = ["#1a1310", "#2e2420", "#7a6e66"]; // 冷掉的縫：外緣、縫心、冷殼邊

  // ---- 殼窩、殼蓋、核心（中心格） ----
  // 第 2 版（審查必修 1）：殼窩整個退回中排（y −96～−48）：中心 −72、半高 24；核心縮到 1.05 倍（上緣 −96.7，呼吸放大後最多再超 1.5 px）。
  const CX = 0, CY = -72, CAV_RX = 28, CAV_RY = 24;
  const CORE_PTS = [[0, -15], [10, -8], [11, 4], [4, 13], [-6, 12], [-11, 3], [-9, -9]]; // qBoss core() 的形
  const CK = G * 1.05; // 核心比 1 格版大 1.05 倍（第 1 版 1.45，長進北排）
  function cavity(g, S) {
    ell(g, CX, CY, CAV_RX + 3.5, CAV_RY + 3.5, BASALT_L); // 窩緣
    ell(g, CX, CY, CAV_RX, CAV_RY, CAVE);
    g.save(); g.beginPath(); g.ellipse(CX, CY, CAV_RX, CAV_RY, 0, 0, TAU); g.clip();
    ell(g, CX, CY + 18, 20, 8, mix(CAVE, LAVA, 0.55), { line: false }); // 窩底的熔岩光
    if (S.phase >= 2) flatGlow(g, CX, CY, 28, CORE, (0.55 + 0.45 * S.breath) * (1 - S.die) * S.coreLight);
    if (S.charge > 0) flatGlow(g, CX, CY - 2, 30, LAVA_HOT, 0.7 * S.charge); // A4：蓄力光（熔心爆蓄力、吸氣中；核心破＝熄掉）
    g.restore();
  }
  function core(g, S) {
    const P = "core", s = (1 + 0.06 * S.breath) * (1 - 0.55 * S.die) * S.coreScale;
    g.save(); g.translate(CX, CY - S.inhale * 2); g.scale(CK * s, CK * s);
    let c = mix(CORE, "#fff4d0", 0.35 * S.breath + 0.4 * S.crack);
    if (S.die > 0) c = mix(c, "#5a4a44", S.die);
    if (S.coreDull > 0) c = mix(c, CORE_DEAD, S.coreDull); // A4：核心破＝光熄、晶體變暗
    const lw = LW / CK;
    poly(g, CORE_PTS, kc(P, c), { lw });
    g.save(); path(g, CORE_PTS); g.clip();
    poly(g, [[0, -15], [-9, -9], [-11, 3], [1, 0]], kc(P, light(c, 0.35)), { line: false });
    poly(g, [[11, 4], [4, 13], [1, 0]], kc(P, dark(c, 0.12)), { line: false });
    g.restore();
    g.fillStyle = kc(P, S.coreDull > 0 ? mix("#ffffff", light(CORE_DEAD, 0.3), 0.6 * S.coreDull) : "#ffffff"); g.fillRect(-5, -9, 2.2, 4.4); g.fillRect(-2, -10.4, 1.4, 1.4);
    if (S.crackPart === "core") crackLines(g, [[[-2, -13], [2, -5], [-1, 2], [3, 10]], [[9, -6], [4, -1], [8, 5]], [[-9, -2], [-4, 1], [-7, 8]]], 0.8 / CK * G);
    if (S.coreBroken) { // 破掉定稿：三道深色裂痕（同熔毀的裂紋位置，換成冷掉的暗色）＋裂縫裡一點餘燼
      for (const pts of [[[-2, -12], [2, -4], [-1, 3], [3, 10]], [[8, -6], [3, -2], [7, 6]], [[-9, -3], [-4, 0], [-6, 7]]]) line(g, pts, 1.6, kc(P, "#2a1a14"));
      g.fillStyle = kc(P, LAVA); g.fillRect(1.2, -3.6, 1.6, 1.6);
    }
    if (S.crack > 0 && !S.coreBroken) { g.save(); g.globalAlpha = clamp(S.crack); line(g, [[-2, -12], [2, -4], [-1, 3], [3, 10]], 1.6 * 0.8, kc(P, "#ffffff")); line(g, [[8, -6], [3, -2], [7, 6]], 1.3 * 0.8, kc(P, "#fff4c0")); g.restore(); }
    g.restore();
  }
  /** 殼蓋：兩片甲蟲殼在殼窩前合起來（第 1 階段），中縫透出核心的光；第 2 階段起往兩側掀開（窄成側邊的兩片）。open 0～1。 */
  function lid(g, S, open) {
    const glow = mix(LAVA, LAVA_HOT, clamp(0.3 + 0.7 * S.breath));
    if (open < 1) { // 中縫的光（合著時）
      g.save(); g.globalAlpha = 1 - open; line(g, [[CX, CY - CAV_RY + 4], [CX - 1.5, CY - 6], [CX + 1.2, CY + 7], [CX, CY + CAV_RY - 5]], 5, glow); g.restore();
    }
    for (const s of [-1, 1]) {
      g.save(); g.translate(CX + s * (CAV_RX + 1), CY); g.scale(1 - 0.62 * open, 1); g.translate(-s * (CAV_RX + 1), 0);
      const half = [];
      for (let i = 0; i <= 12; i++) { const a = -Math.PI / 2 + (i / 12) * Math.PI; half.push([s * Math.cos(a) * (CAV_RX + 1.5), Math.sin(a) * (CAV_RY + 1.5)]); }
      half.push([s * 2.2, CY - CY + CAV_RY - 4], [s * 1.2, 7], [s * 3.2, -6], [s * 2, -CAV_RY + 5]);
      poly(g, half, BASALT_L);
      g.save(); path(g, half); g.clip();
      ell(g, s * 14, -9, 8, 9, s < 0 ? light(BASALT_L, 0.2) : dark(BASALT_L, 0.1), { line: false, rot: s * 0.3 });
      for (const yy of [-8, 7]) line(g, [[s * 4, yy], [s * 25, yy + 3]], 0.9 * G * 0.7, OUT); // 殼片分節
      g.restore();
      g.restore();
    }
  }

  // ---- 前殼（南排三隻熔岩甲蟲，本體） ----
  const BEETLES = [{ x: -47, y: -36, rx: 25, ry: 20, rot: -0.1 }, { x: 47, y: -36, rx: 25, ry: 20, rot: 0.1 }, { x: 0, y: -35, rx: 27, ry: 21, rot: 0 }];
  function beetle(g, b, S) {
    g.save(); g.translate(b.x, b.y); g.rotate(b.rot);
    // 背殼：兩片翅鞘＋中線＋左上亮面＋一道熔岩鋸齒縫
    ell(g, 0, 0, b.rx, b.ry, BASALT_L);
    g.save(); g.beginPath(); g.ellipse(0, 0, b.rx, b.ry, 0, 0, TAU); g.clip();
    ell(g, -b.rx * 0.36, -b.ry * 0.4, b.rx * 0.36, b.ry * 0.26, light(BASALT_L, 0.22), { line: false, rot: -0.3 });
    ell(g, b.rx * 0.4, b.ry * 0.45, b.rx * 0.5, b.ry * 0.35, dark(BASALT_L, 0.14), { line: false });
    g.restore();
    line(g, [[0, -b.ry + 1.2], [0, b.ry - 1.2]], 0.9 * G, OUT);
    const z = [[-b.rx * 0.62, 6], [-b.rx * 0.32, 2.5], [-b.rx * 0.08, 7], [b.rx * 0.2, 3], [b.rx * 0.48, 7.5], [b.rx * 0.66, 4]];
    const heat = S.phase === 3 ? 0.6 + 0.4 * S.breath : 0.15 + 0.2 * S.breath;
    line(g, z, 2 * G, EMBER); line(g, z, 1 * G, mix(LAVA, LAVA_HOT, heat));
    // 頭（朝南，從殼下緣探出來）：兩點火眼、一對短顎
    const hy = b.ry + 1;
    for (const s of [-1, 1]) poly(g, [[s * 4.6, hy + 3.6], [s * 9.4, hy + 7.6], [s * 6.6, hy + 9], [s * 2.8, hy + 5.6]], dark(BASALT, 0.1));
    ell(g, 0, hy, 10.5, 6.4, BASALT);
    ell(g, -3.4, hy - 2.6, 3.6, 1.6, light(BASALT, 0.16), { line: false });
    for (const s of [-1, 1]) { g.fillStyle = OUT; g.fillRect(s * 4.2 - 2, hy - 1.4, 4, 3.6); g.fillStyle = mix(LAVA, LAVA_HOT, 0.5 + 0.5 * S.breath); g.fillRect(s * 4.2 - 1.3, hy - 0.7, 2.6, 2.4); }
    g.restore();
  }

  // ---- 熔殼殼片（狀態 molten_shell）：名稱和 qBoss.js PLATES 同一組（雜湊一樣）；位置放大圍住殼窩 ----
  /** [名稱, x, y, 旋轉, 寬, 高]（模型像素）。第 2 版：跟著殼窩退回中排（中心 −72），整組縮 0.85。 */
  const PLATES = [
    ["p-back-l", -24, -89, -0.5, 26, 17], ["p-back-r", 24, -89, 0.5, 26, 17], ["p-top", 0, -92, 0, 28, 16],
    ["p-left", -31, -72, -0.9, 22, 19], ["p-right", 31, -72, 0.9, 22, 19],
    ["p-low-l", -20, -54, -0.3, 26, 16], ["p-low-r", 20, -54, 0.3, 26, 16], ["p-front", 0, -59, 0, 29, 16],
    ["p-mid-l", -13, -79, -0.2, 21, 16], ["p-mid-r", 13, -79, 0.2, 21, 16],
  ];
  /** 一片殼片（qBoss plate() 換成模型像素）：圓背甲＋中線＋鋸齒熔岩縫（熱度越高越黃）＋左上亮面。 */
  function plate(g, w, h, heat) {
    ell(g, 0, 0, w / 2, h / 2, BASALT_L);
    g.save(); g.beginPath(); g.ellipse(0, 0, w / 2, h / 2, 0, 0, TAU); g.clip();
    ell(g, -w * 0.16, -h * 0.18, w * 0.22, h * 0.16, light(BASALT_L, 0.22), { line: false, rot: -0.3 });
    g.restore();
    line(g, [[0, -h / 2 + 1.2], [0, h / 2 - 1.2]], 0.9 * G, OUT);
    const z = [[-w * 0.34, 0.9], [-w * 0.17, -1.8], [0, 1.5], [w * 0.17, -1.5], [w * 0.34, 1.2]];
    line(g, z, 2 * G, EMBER); line(g, z, 1 * G, mix(LAVA, LAVA_HOT, clamp(heat)));
  }
  /** 殼片的掛點：熔殼在＝貼著（第 2、3 階段＝往外撐開、露出核心），隨呼吸張開；
   *  不在＝第 2 版（美術 PM 3.2 第 5 項）：依名稱雜湊往北彈起、飛過噴口落進北邊岩漿（y −160～−180），後 40% 邊縮小邊淡出；脫落完（breakT ≥ 1）就不畫，南排不留殼片。回傳 null＝不畫。 */
  function plateAnchor(p, shell, bt, breath, open) {
    const [key, x, y, r] = p;
    if (shell > 0) {
      const o = 0.6 * breath, k = open ? 1.42 : 1, px = CX + (x - CX) * k, py = CY + (y - CY) * (open ? 1.2 : 1);
      return { x: px * (1 + 0.02 * o), y: py - o * 0.9, r: r * (open ? 1.25 : 1), a: 1, s: 1 };
    }
    if (bt >= 1) return null;
    const dir = Math.sign(x || rnd(key) - 0.5) || 1, spin = (rnd(key, 3) - 0.5) * 6;
    const fx = x * 1.15 + dir * (4 + 14 * rnd(key, 1)), fy = -162 - 18 * rnd(key, 4), hop = 22 + 18 * rnd(key, 2);
    const u = clamp(bt), fade = clamp((u - 0.6) / 0.4);
    return { x: x + (fx - x) * u, y: y + (fy - y) * u - hop * Math.sin(Math.PI * u), r: r + spin * u, a: 1 - fade, s: 1 - 0.4 * fade };
  }

  /** A4（GB巨型頭目-審查.md 第 5 節可修 B）：殼片中心離開佔格（北緣 y −144 以北、或兩側 |x| > 72）＝已經不是頭目身上的東西：
   *  不畫在本體圖層裡（不吃頭目金外光），改在 draw() 裡一片一片自己包黑外框、照自己的透明度淡出（外框跟著淡）。 */
  const plateFree = (A) => A.y < -144 || Math.abs(A.x) > 72;
  function freePlates(ctx, S) {
    if (S.shell > 0 || S.bt >= 1) return;
    const list = [...PLATES].sort((a, b) => plateAnchor(a, 0, S.bt, 0).y - plateAnchor(b, 0, S.bt, 0).y);
    for (const p of list) {
      const A = plateAnchor(p, 0, S.bt, 0, false);
      if (!A || A.a <= 0 || !plateFree(A)) continue;
      layer(ctx, BOX, (g) => { g.translate(A.x, A.y); g.rotate(A.r); g.scale(A.s, A.s); plate(g, p[4], p[5], 0.12); }, { ow: OW, alpha: A.a });
    }
  }
  /** 狀態：st＝{ phase: 1|2|3, shell: 0～1（熔殼在不在；預設第 1 階段在、其他不在）, breakT: 0～1（脫落進度）, t: 毫秒, spout, inhale, dieT, broken: { vent, seam } } */
  function stateOf(st = {}) {
    const t = num(st.t, 0), phase = [1, 2, 3].includes(st.phase) ? st.phase : 1;
    const shell = clamp(num(st.shell, phase === 1 ? 1 : 0)), bt = clamp(num(st.breakT, shell > 0 ? 0 : 1));
    const broken = st.broken ?? {}, fx = fxOf(st), K = fx ? fx.k : 0, is = (p) => !!fx && fx.part === p;
    const coreTab = (row, done, base) => (is("core") ? row[K] : broken.core ? done : base);
    return {
      t, phase, shell, bt, breath: 0.5 + 0.5 * Math.sin(t / 420), crack: phase === 3 ? 0.6 + 0.4 * Math.sin(t / 160) : 0,
      inhale: is("core") ? BRK.inhale[K] : clamp(num(st.inhale, 0)), spout: clamp(num(st.spout, 0)), die: clamp(num(st.dieT, 0)), broken,
      // A4 破壞演出（fx＝{ part, k 0～4, side }）與破壞後外觀（broken.vent｜seam｜core）；都沒有時全部是中性值，A1～A3 的圖不變
      fx, crackPart: fx && K === 1 ? fx.part : null, ventSealed: !!broken.vent || (is("vent") && K >= 2), ventFlare: is("vent") && K === 1,
      seamCool: broken.seam ? 1 : is("seam") ? BRK.seamCool[K] : 0,
      coreBroken: !!broken.core || (is("core") && K >= 3), coreScale: coreTab(BRK.coreScale, BRK.coreScale[4], 1), coreDull: coreTab(BRK.coreDull, BRK.coreDull[4], 0),
      coreLight: coreTab(BRK.coreLight, BRK.coreLight[4], 1), charge: is("core") ? BRK.charge[K] : clamp(num(st.charge, 0)),
    };
  }
  /** A4 破壞演出的五格（k：0 命中 80 ms、1 裂開 80 ms、2 斷開 160 ms、3 落地 160 ms、4 定格）；每列是那個量在五格的值，第 5 格＝破壞後定稿。 */
  const BRK = {
    ms: [80, 80, 160, 160, 0],
    seamCool: [0, 0, 0.6, 1, 1], // 殼縫：0 熱 → 1 冷黑（第 2 格過熱發白另用 crackPart）
    coreScale: [1, 0.88, 0.7, 0.86, 0.92], coreDull: [0, 0.15, 0.55, 0.7, 0.7], coreLight: [1, 0.7, 0.3, 0.25, 0.25], // 核心光一縮：縮到 0.7 再回 0.92，變暗、窩裡的光剩 25%
    charge: [1, 0.6, 0.15, 0, 0], inhale: [1, 0.6, 0, 0, 0], // 蓄力光、吸氣火星：第 3 格起熄
  };
  const CORE_DEAD = "#7a5a46";
  function fxOf(st) {
    const f = st.fx;
    if (!f || !["vent", "seam", "core"].includes(f.part)) return null;
    return { part: f.part, k: Math.max(0, Math.min(4, Math.round(num(f.k, 0)))), side: f.side === -1 ? -1 : 1 };
  }
  /** 本體（全部平塗部件；給 layer 包外框）。 */
  function bodyLayer(g, S) {
    for (const v of VENTS) vent(g, v, S);
    dome(g, S);
    seam(g, -1, S); seam(g, 1, S);
    cavity(g, S);
    core(g, S);
    lid(g, S, S.phase >= 2 ? 1 : 0);
    for (const b of BEETLES) beetle(g, b, S);
    if (S.phase === 3) for (const [x, len, w] of [[-14, 20, 4.2], [3, 27, 5], [17, 16, 3.6]]) { // 熔毀：熔岩從殼窩下緣漫出、流過中間那隻甲蟲
      const y0 = CY + CAV_RY - 2, L = len * (0.85 + 0.15 * Math.sin(S.t / 300 + x));
      g.fillStyle = LAVA; g.beginPath(); g.moveTo(x - w, y0); g.quadraticCurveTo(x - w * 0.9, y0 + L * 0.7, x, y0 + L); g.quadraticCurveTo(x + w * 0.9, y0 + L * 0.7, x + w, y0); g.closePath(); g.fill();
      g.strokeStyle = EMBER; g.lineWidth = LW; g.stroke(); g.fillStyle = LAVA_HOT; g.fillRect(x - 0.8, y0 + 1, 1.6, L * 0.6);
    }
    const open = S.phase >= 2;
    const order = S.shell > 0 ? PLATES : S.bt >= 1 ? [] : [...PLATES].sort((a, b) => plateAnchor(a, 0, S.bt, 0).y - plateAnchor(b, 0, S.bt, 0).y); // 飛走時北邊（遠）的先畫
    for (const p of order) { const A = plateAnchor(p, S.shell, S.bt, S.breath, open); if (!A || A.a <= 0 || (S.shell <= 0 && !S.legacyPlates && plateFree(A))) continue; g.save(); g.globalAlpha = A.a; g.translate(A.x, A.y); g.rotate(A.r); g.scale(A.s, A.s); plate(g, p[4], p[5], S.shell > 0 ? S.breath : 0.12); g.restore(); }
  }

  /** 地面：3×3 陣營環（提案 A：圓角方框貼佔格內 3）＋精英金框＋南緣中點金菱形＋影子。opt.ring＝"rect"（預設）｜"ellipse"（提案 B）｜false。 */
  function groundRing(ctx, opt = {}) {
    const mode = opt.ring ?? "rect";
    ctx.save();
    ctx.fillStyle = "rgba(10,8,14,0.35)"; ctx.beginPath(); ctx.ellipse(0, -30, 74, 26, 0, 0, TAU); ctx.fill();
    if (mode === "rect") {
      const r = { x: -69, y: -141, w: 138, h: 138 };
      // 第 2 版（可修 4）：紅底只在中、南兩排填 80%；北排（噴口之間露出來的那條）減到 35%，不讀成一塊紅布
      ctx.save(); ctx.beginPath(); ctx.roundRect(r.x, r.y, r.w, r.h, 14); ctx.clip(); ctx.fillStyle = "#c63b3b";
      ctx.globalAlpha = 0.35; ctx.fillRect(r.x, r.y, r.w, -96 - r.y); ctx.globalAlpha = 0.8; ctx.fillRect(r.x, -96, r.w, r.y + r.h + 96); ctx.restore();
      ctx.beginPath(); ctx.roundRect(r.x, r.y, r.w, r.h, 14); ctx.lineWidth = 1.5 * 1.6; ctx.strokeStyle = "#ffb3a8"; ctx.stroke();
      ctx.beginPath(); ctx.roundRect(r.x - 2.5, r.y - 2.5, r.w + 5, r.h + 5, 16); ctx.lineWidth = 3.6; ctx.strokeStyle = OUT; ctx.stroke(); ctx.lineWidth = 1.8; ctx.strokeStyle = GOLD; ctx.stroke();
      gem(ctx, 0, -5.5, 1.6);
    } else if (mode === "ellipse") {
      const rx = 70, ry = 21, cy = -16;
      ctx.beginPath(); ctx.ellipse(0, cy, rx, ry, 0, 0, TAU); ctx.globalAlpha = 0.8; ctx.fillStyle = "#c63b3b"; ctx.fill(); ctx.globalAlpha = 1; ctx.lineWidth = 2.4; ctx.strokeStyle = "#ffb3a8"; ctx.stroke();
      ctx.beginPath(); ctx.ellipse(0, cy, rx + 3.5, ry + 3.5 * 0.3, 0, 0, TAU); ctx.lineWidth = 3.8; ctx.strokeStyle = OUT; ctx.stroke(); ctx.lineWidth = 1.9; ctx.strokeStyle = GOLD; ctx.stroke();
      gem(ctx, 0, cy + ry + 0.6, 1.6);
    }
    ctx.restore();
  }
  function gem(ctx, x, y0, s) { // 金菱形（qCreature ring 的精英記號，放大 s 倍）
    ctx.save(); ctx.beginPath(); ctx.moveTo(x, y0); ctx.lineTo(x + 2.6 * s, y0 + 2.6 * s); ctx.lineTo(x, y0 + 5.2 * s); ctx.lineTo(x - 2.6 * s, y0 + 2.6 * s); ctx.closePath();
    ctx.lineJoin = "round"; ctx.strokeStyle = OUT; ctx.lineWidth = 1.6 * s; ctx.stroke(); ctx.fillStyle = GOLD; ctx.fill(); ctx.fillStyle = "#fff2c0"; ctx.fillRect(x - 0.5 * s, y0 + 1.2 * s, s, s); ctx.restore();
  }

  /** 第 3 階段坑底發紅（第 2 版，審查必修 3）：屬地面層，和地格一起、在所有單位之前畫；draw() 不再畫它。ctx 座標同 draw（原點＝錨點）。 */
  function groundGlow(ctx, st = {}) {
    const S = stateOf(st);
    if (S.phase === 3) flatGlow(ctx, 0, -50, 112, "#ff6e1e", 1 - S.die, 92);
  }

  /**
   * 畫灰燼之心（3×3）。ctx 目前座標＝模型像素、原點＝錨點（南排南緣中點）。st 見 stateOf；opt：
   *   glow（頭目外光色，預設傳說金；false＝不畫）、ring（"rect"｜"ellipse"｜false）、flash（受擊白閃 0～1）、key（部位 id：那個部位換記號色，遮罩用）。
   */
  function draw(ctx, st = {}, opt = {}) {
    const S = stateOf(st);
    S.legacyPlates = !!opt.legacyPlates; // 對照用：第 2 版的飛行殼片（帶金外光）
    if (opt.ring !== false) groundRing(ctx, opt);
    KEY = opt.key ?? null;
    try {
      layer(ctx, BOX, (g) => bodyLayer(g, S), { ow: OW, glow: opt.glow === false || S.die > 0 ? null : (opt.glow ?? GOLD), glowW: GLOW_W, glowA: GLOW_A, flash: num(opt.flash, 0) });
    } finally { KEY = null; }
    if (!opt.key && !opt.mask && !S.legacyPlates) freePlates(ctx, S);
    // 小粒子（吸氣的火星、熔毀滴落）：細外框（qBoss 同）
    const parts = [];
    if (S.inhale > 0) for (let k = 0; k < 16; k++) { const a = rnd("in", k) * TAU, d = 96 * (1 - ((S.t / 600 + rnd("in2", k)) % 1)); parts.push([CX + Math.cos(a) * d, CY + Math.sin(a) * d * 0.6, 2.8, LAVA_HOT]); }
    // 熔毀的滴落改成殼窩下緣的熔岩流（畫在本體裡），不另外畫粒子（粒子落在甲蟲臉上會讀成鼻子）
    if (parts.length && !opt.key && !opt.mask) layer(ctx, BOX, (g) => { for (const [x, y, r, c] of parts) { g.fillStyle = c; g.beginPath(); g.arc(x, y, r, 0, TAU); g.fill(); } }, { ow: 0.8 * G, alpha: S.inhale > 0 && S.phase !== 3 ? Math.max(0.3, S.inhale) : 1 });
  }

  // ---------------- 部位遮罩與滑過亮起（bossParts.js 的 HOVER 同一套） ----------------
  const mk = (w, h) => { const c = document.createElement("canvas"); c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h)); return c; };
  function diffMask(a, b, thr = 40) {
    const w = a.width, h = a.height, da = a.getContext("2d", { willReadFrequently: true }).getImageData(0, 0, w, h).data, db = b.getContext("2d", { willReadFrequently: true }).getImageData(0, 0, w, h).data;
    const out = mk(w, h), oc = out.getContext("2d"), img = oc.createImageData(w, h), d = img.data;
    for (let i = 0; i < da.length; i += 4) { const s = Math.abs(da[i] - db[i]) + Math.abs(da[i + 1] - db[i + 1]) + Math.abs(da[i + 2] - db[i + 2]) + Math.abs(da[i + 3] - db[i + 3]); if (s > thr) { d[i] = d[i + 1] = d[i + 2] = 255; d[i + 3] = 255; } }
    oc.putImageData(img, 0, 0); return out;
  }
  function tint(src, col) { const c = mk(src.width, src.height), x = c.getContext("2d"); x.drawImage(src, 0, 0); x.globalCompositeOperation = "source-in"; x.fillStyle = col; x.fillRect(0, 0, c.width, c.height); return c; }
  function dilate(src, r, N = 16) { const c = mk(src.width, src.height), g = c.getContext("2d"); for (const f of [1, 0.66, 0.33]) for (let i = 0; i < N; i++) { const a = (i / N) * TAU; g.drawImage(src, Math.cos(a) * r * f, Math.sin(a) * r * f); } g.drawImage(src, 0, 0); return c; }
  /** 部位遮罩：w×h 的 canvas、變換 m（模型像素 → canvas 像素，原點＝錨點）。回傳實際露出的部位像素（白）。 */
  function partMask(w, h, m, st, part) {
    const one = (key) => { const c = mk(w, h), g = c.getContext("2d", { willReadFrequently: true }); g.setTransform(m); draw(g, st, { glow: false, ring: false, key, mask: true }); return c; }; // mask：兩張都不畫本體以外的東西（吸氣火星、離開佔格的殼片），差只剩部位
    return diffMask(one(null), one(part));
  }
  /** 亮起：亮青白 #a8f4ff 描邊＋外框色襯邊＋部位上 35% 同色（bossParts HOVER；線寬照模型像素，跟著地圖縮放，畫面上至少 minPx）。 */
  const HOVER = { color: "#a8f4ff", ink: OUT, width: 2.0, inkW: 1.3, fill: 0.35, minPx: 1.5 };
  function glowPart(ctx, w, h, m, st, part, opt = {}) {
    const o = { ...HOVER, ...opt }, mask = partMask(w, h, m, st, part), px = Math.hypot(m.a, m.b);
    const wp = Math.max(o.width * px, o.minPx * (o.dpr ?? 1)), ip = Math.max(o.inkW * px, 1 * (o.dpr ?? 1));
    const outer = dilate(mask, wp + ip), mid = dilate(mask, wp), lay = mk(w, h), l = lay.getContext("2d");
    l.drawImage(tint(outer, o.ink), 0, 0); l.drawImage(tint(mid, o.color), 0, 0);
    l.globalCompositeOperation = "destination-out"; l.drawImage(mask, 0, 0); l.globalCompositeOperation = "source-over";
    l.globalAlpha = o.fill; l.drawImage(tint(mask, o.color), 0, 0);
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.drawImage(lay, 0, 0); ctx.restore();
  }

  // ---------------- A4 破壞演出（5 格約 0.6 秒；沿用段 1：白閃＋微震＋「破」字記號，不出「○○ 破！」浮字） ----------------
  /** 第 1 格「命中」：部位整塊白閃（遮罩＝partMask，和滑過亮起同一份），a＝0.9（段 1 同值）。 */
  function flashPart(ctx, w, h, m, st, part, a = 0.9) {
    const mask = partMask(w, h, m, st, part);
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = a; ctx.drawImage(tint(mask, "#ffffff"), 0, 0); ctx.restore();
  }
  const mouthOf = (v) => { const h = v.base - v.top; return [v.x + Math.sin(v.tilt) * h, v.base - Math.cos(v.tilt) * h]; };
  /** 「破」字記號的位置（模型 px，相對錨點；掛在被破的部位上方）。殼縫掛在被打中的那一側（side −1 西、1 東）。 */
  const POP = { vent: [0, -168], seam: [57, -106], core: [0, -114] };
  const popAt = (part, side = 1) => { const [x, y] = POP[part]; return [part === "seam" ? side * x : x, y]; };
  /** 「破」：預告格一字記號放大（段 1：黑圓 72%、半徑 10、外圈紅 1.5、字 14 粗亮黃）；畫面上字 ≥ 12 px：整個記號 × max(1, 12／(14 × 地圖縮放))（PB-1e 裁定）。 */
  const POP_STYLE = { r: 10, ring: 1.5, font: 14, minPx: 12, bg: "rgba(0,0,0,0.72)", ringC: "#ff5a4a", text: "#ffd23f", ch: "破" };
  const popScale = (S) => Math.max(1, POP_STYLE.minPx / (POP_STYLE.font * S));
  function pop(ctx, x, y, a, S) {
    const P = POP_STYLE, f = popScale(S);
    ctx.save(); ctx.globalAlpha = a; ctx.beginPath(); ctx.arc(x, y, P.r * f, 0, TAU); ctx.fillStyle = P.bg; ctx.fill(); ctx.lineWidth = P.ring * f; ctx.strokeStyle = P.ringC; ctx.stroke();
    ctx.font = `bold ${P.font * f}px 'Noto Sans TC','Microsoft JhengHei',sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillStyle = P.text; ctx.fillText(P.ch, x, y + 0.5 * f); ctx.restore();
  }
  /** 黑煙（噴口封住的專屬特效）：四團平塗煙（暗灰＋左上一點亮灰），整團包細外框、一起淡（不疊出深淺）。 */
  const SMOKE = ["#2c272b", "#5a5357"];
  function smoke(ctx, x, y, r, a) {
    const lobes = [[0, 0, 1], [-0.75, 0.3, 0.72], [0.75, 0.25, 0.78], [0.1, -0.68, 0.8]];
    layer(ctx, [x - 2.5 * r, y - 2.5 * r, x + 2.5 * r, y + 2.5 * r], (g) => {
      g.fillStyle = SMOKE[0]; for (const [dx, dy, s] of lobes) { g.beginPath(); g.arc(x + dx * r, y + dy * r, s * r, 0, TAU); g.fill(); }
      g.fillStyle = SMOKE[1]; for (const [dx, dy, s] of [lobes[3], lobes[1]]) { g.beginPath(); g.ellipse(x + (dx - 0.28 * s) * r, y + (dy - 0.3 * s) * r, 0.42 * s * r, 0.28 * s * r, -0.4, 0, TAU); g.fill(); }
    }, { ow: 0.6 * G, alpha: a });
  }
  /** 火星四散（核心破的專屬特效）：12 顆火星從核心往外噴（短拖尾指回核心），第 4 格飛遠、往下掉、變小變淡。細外框（同吸氣火星）。 */
  function sparks(ctx, k) {
    const far = k >= 3, list = [];
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * TAU + (rnd("spk", i) - 0.5) * 0.4, d = far ? 46 + 16 * rnd("spk-d", i) : 22 + 10 * rnd("spk-d", i), fall = far ? 10 + 6 * rnd("spk-f", i) : 0;
      list.push([Math.cos(a), Math.sin(a) * 0.75, d, fall, i % 3 === 2 ? LAVA : LAVA_HOT]);
    }
    layer(ctx, BOX, (g) => {
      for (const [cx, cy, d, fall, c] of list) {
        const x = CX + cx * d, y = CY + cy * d + fall, tail = far ? 4 : 7, w = far ? 2 : 2.8;
        line(g, [[x - cx * tail, y - cy * tail - (far ? 3 : 0)], [x, y]], w, c);
        g.fillStyle = "#fff4c0"; g.beginPath(); g.arc(x, y, w * 0.32, 0, TAU); g.fill();
      }
    }, { ow: 0.8 * G, alpha: far ? 0.75 : 1 });
  }
  /**
   * 破壞演出的特效層（白閃之外的東西）：畫在所有單位之上（同段 1；「破」不能被南邊的人或浮字蓋住）。ctx 座標＝模型像素、原點＝錨點；
   * st.fx＝{ part: "vent"|"seam"|"core", k: 0～4, side }；o.S＝地圖縮放（「破」800 反向放大用）。burst／shard／ring／dust／puff 照 QCreatureAnim.drawFx。
   */
  function breakFx(ctx, st, o = {}) {
    const S = stateOf(st), f = S.fx; if (!f || f.k >= 4) return;
    const QA = window.QCreatureAnim, k = f.k, D = (x, y, list) => { ctx.save(); ctx.translate(x, y); QA.drawFx(ctx, list, {}, [-40, -40, 40, 40]); ctx.restore(); };
    const burst = (r, c = "#ffffff", c2 = "#ffe08a", a = 1) => ({ k: "burst", x: 0, y: 0, r, c, c2, a });
    const shards = (c, s = 2.2, list = [[-9, -6, 0.6], [9, -8, -0.8], [6, 6, 2.2]]) => list.map(([x, y, rot], i) => ({ k: "shard", x, y, rot, s, c: Array.isArray(c) ? c[i % c.length] : c }));
    const [px, py] = popAt(f.part, f.side);
    if (f.part === "vent") {
      const M = VENTS.map(mouthOf), mid = M[2];
      if (k === 0) M.forEach(([x, y], i) => D(x, y, [burst(i === 2 ? 10 : 8)]));
      if (k === 1) { D(...mid, [burst(7, "#ffe08a", "#ffffff", 0.8), ...shards("#9a8a7e", 2.4, [[-10, -7, 0.6], [10, -10, -0.8], [4, -16, 2.2]])]); D(...M[0], [burst(5, "#ffe08a", "#ffffff", 0.8)]); D(...M[1], [burst(5, "#ffe08a", "#ffffff", 0.8)]); }
      if (k === 2) { M.forEach(([x, y], i) => smoke(ctx, x, y - 7, i === 2 ? 9 : 8, 0.95)); D(...mid, [burst(15, "#ffd23f", "#ffffff"), { k: "ring", x: 0, y: 2, rx: 20, c: "#ffe08a", w: 1.6 }]); }
      if (k === 3) { M.forEach(([x, y], i) => { smoke(ctx, x - 2, y - 17, i === 2 ? 10 : 9, 0.9); smoke(ctx, x + 3, y - 32, i === 2 ? 12 : 10.5, 0.65); D(x, y + 1, [{ k: "dust", x: 0, y: 0, r: 5, c: "#8a807a", a: 0.9 }]); }); }
    } else if (f.part === "seam") {
      const sx = f.side * 57, sy = -68;
      if (k === 0) D(sx, sy, [burst(9)]);
      if (k === 1) D(sx, sy, [burst(6, "#ffe08a", "#ffffff", 0.8), ...shards(["#9a8a7e", LAVA, "#9a8a7e"], 2.4)]);
      if (k === 2) { D(sx, sy, [burst(14, "#ffd23f", "#ffffff"), { k: "ring", x: 0, y: 4, rx: 16, c: "#ffe08a", w: 1.6 }]); for (const s of [-1, 1]) D(s * 58, -70, [{ k: "puff", x: 0, y: -10, r: 5, c: "#d8d0c8" }, { k: "puff", x: s * 2, y: 10, r: 4.2, c: "#d8d0c8" }]); }
      if (k === 3) for (const s of [-1, 1]) D(s * 59, -46, [{ k: "dust", x: 0, y: 0, r: 5, c: "#8a807a", a: 0.9 }, { k: "puff", x: -s * 2, y: -34, r: 5.5, c: "#d8d0c8", a: 0.5 }]);
    } else if (f.part === "core") {
      if (k === 0) D(CX, CY, [burst(10)]);
      if (k === 1) D(CX, CY, [burst(7, "#ffe08a", "#ffffff", 0.8), ...shards("#ffd98a", 2.2)]);
      if (k === 2) { sparks(ctx, 2); D(CX, CY, [burst(15, "#ffd23f", "#ffffff"), { k: "ring", x: 0, y: 6, rx: 22, c: "#ffe08a", w: 1.6 }]); }
      if (k === 3) { sparks(ctx, 3); D(CX, CY, [{ k: "puff", x: 0, y: -16, r: 5, c: "#6a6064", a: 1 }, { k: "dust", x: 0, y: 20, r: 5, c: "#8a807a", a: 0.9 }]); }
    }
    if (k === 2) pop(ctx, px, py, 1, o.S ?? 1);
    if (k === 3) pop(ctx, px, py - 3, 0.55, o.S ?? 1);
  }
  /** 本體填色層（不描外框、不帶外光）：給選單「本體」列的頭像（qBossGiantIcons.js GLYPH.body）。z＝每模型 px 幾個 canvas px；原點＝錨點在 (ox, oy)。 */
  function fill(st, z) {
    const S = stateOf(st), c = mk((BOX[2] - BOX[0]) * z, (BOX[3] - BOX[1]) * z), g = c.getContext("2d");
    g.setTransform(z, 0, 0, z, -BOX[0] * z, -BOX[1] * z); bodyLayer(g, S);
    return { canvas: c, ox: -BOX[0] * z, oy: -BOX[1] * z, z };
  }

  // ---------------- A2 部位格標示（3×3 地面格；畫在單位之上：同 highlightLayer 的 marks） ----------------
  // 和霧鎖真人頭頂部位小格同一套語言（頭目部位-移植需求.md 2.1～2.4）：完好＝米白、滑過＝亮青白 #a8f4ff、打不到＝去色＋原因小圖、破掉＝暗紅＋紅×、未露出＝幾乎黑。
  const MARK = {
    cream: "#f2e6c8", hover: "#a8f4ff", dimLine: "#8a8690", broken: "#5a1a1a", x: "#ff5a4a", hidden: "#0e0e14", body: "#ff4040",
    inset: 7, arm: 10, w: 2.2, inkW: 1.8, minW: 1.5, xSize: 18, xMin: 6, chipR: 8, chipMin: 7,
  };
  /** 打不到的原因 → 小圖（QIconsParts）。字待玩法 PM 確認。 */
  const REASON = {
    ranged: { cat: "target", id: "tag_ranged", zh: "要遠程才打得到" },
    range: { cat: "card", id: "range", zh: "射程不夠" },
    sight: { cat: "status", id: "blinded", zh: "看不到這一格" },
  };
  const BACK_CHIP = { cat: "condition", id: "from_behind", zh: "打這裡算從背後（近戰）" };
  /** 每格的狀態 → 畫標示。ctx 座標＝模型像素、原點＝錨點；S＝畫面 px／模型 px（地圖縮放×放大）；res＝裝置像素／畫面 px。
   *  parts：{ vent|seam|core: { state: "ok"|"off"|"broken"|"hidden", why: "ranged"|"range"|"sight" } }；hover：部位 id 或 "body"；melee：攻擊者是近戰（殼縫顯示背刺小圖）。 */
  /** 標示的「區塊」：同一個部位、相鄰的格合成一塊（噴口北排 3 格一塊；殼縫東西不相鄰，各一塊；核心一塊）。[部位, 列, 起欄, 欄數, 背刺小圖放哪一側]。 */
  const REGIONS = [["vent", 0, 0, 3, 0], ["seam", 1, 0, 1, -1], ["core", 1, 1, 1, 0], ["seam", 1, 2, 1, 1]];
  function drawMarks(ctx, parts, o = {}) {
    const S = o.S ?? 1, res = o.res ?? 1, hover = o.hover ?? null, melee = o.melee !== false;
    const W = (w, min) => Math.max(w, min / S);
    const compact = T * S < 40; // 800 寬（一格 25.5 px）：第 2 版拿掉原因小圓片（美術 PM 3.2 第 3 項），打不到改靠更暗＋不透明灰括號
    for (const [part, row, c0, n, side] of REGIONS) {
      const st = parts[part] ?? { state: "ok" }, [x0, y0] = tileXY(row, c0), w = n * T;
      let state = st.state;
      if (state === "ok" && hover === part) state = "hover";
      const ins = MARK.inset, inner = [x0 + ins - 1, y0 + ins - 1, w - 2 * ins + 2, T - 2 * ins + 2];
      ctx.save();
      // 800 殼縫有背刺記號時，記號佔掉內側下角那個括號（不畫那一角，記號不貼米白括號；複審可修 A）
      const skip = compact && part === "seam" && melee ? (side < 0 ? 2 : 3) : -1;
      if (state === "ok") brackets(ctx, x0, y0, w, MARK.cream, W(MARK.w, MARK.minW), W(MARK.inkW, 1), skip);
      else if (state === "hover") {
        const lw = W(2.6, 2);
        ctx.fillStyle = MARK.hover; ctx.globalAlpha = 0.14; ctx.fillRect(...inner); ctx.globalAlpha = 1;
        ctx.beginPath(); ctx.roundRect(...inner, 5); ctx.lineWidth = lw + 2 * W(MARK.inkW, 1); ctx.strokeStyle = OUT; ctx.stroke(); ctx.lineWidth = lw; ctx.strokeStyle = MARK.hover; ctx.stroke();
      } else if (state === "off") {
        ctx.fillStyle = compact ? "rgba(10,8,14,0.55)" : "rgba(10,8,14,0.34)"; ctx.fillRect(...inner); // 800：暗化 34% → 55%（可修 1）
        ctx.globalAlpha = compact ? 1 : 0.75; brackets(ctx, x0, y0, w, MARK.dimLine, W(1.8, 1.5), W(1.4, 1)); ctx.globalAlpha = 1;
        if (!compact) { const R = REASON[st.why] ?? REASON.range; chip(ctx, R, x0 + w / 2, y0 + T / 2, W(MARK.chipR, MARK.chipMin), S, res, { ring: "rgba(255,255,255,0.35)", gray: true }); }
      } else if (state === "broken") {
        ctx.fillStyle = MARK.broken; ctx.globalAlpha = 0.55; ctx.fillRect(...inner); ctx.globalAlpha = 1;
        const r = W(MARK.xSize, MARK.xMin) / 2, lw = W(3, 1.5);
        ctx.lineCap = "round";
        for (let k = 0; k < n; k++) { const cx = x0 + k * T + T / 2, cy = y0 + T / 2; for (const [c, lww] of [[OUT, lw + W(2.4, 1.2)], [MARK.x, lw]]) { ctx.strokeStyle = c; ctx.lineWidth = lww; ctx.beginPath(); ctx.moveTo(cx - r, cy - r); ctx.lineTo(cx + r, cy + r); ctx.moveTo(cx + r, cy - r); ctx.lineTo(cx - r, cy + r); ctx.stroke(); } }
      } else if (state === "hidden") {
        // 第 2 版（可修 2）：線至少 1.5 px、段長至少 3 px、不透明（800 第 1 版只剩斷續暗點）
        ctx.setLineDash([W(4, 3.5), W(3, 2.5)]); ctx.beginPath(); ctx.roundRect(...inner, 5);
        ctx.lineWidth = W(1.6, 1.5) + 2 * W(1, 0.8); ctx.strokeStyle = OUT; ctx.stroke(); ctx.lineWidth = W(1.6, 1.5); ctx.strokeStyle = MARK.dimLine; ctx.stroke(); ctx.setLineDash([]);
      }
      // 殼縫：近戰時一顆背刺小圖（「算從背後」；R4 遠程不算，不畫）。第 2 版（審查必修 2）：改放「內側」下角（靠核心那側，背殼平塗處），不蓋住貼外側的熔岩裂縫；
      // 800（compact）不用 14 px 的圖樣小圓片（只剩一團白），改畫加粗的「往回彎的箭頭」記號（黃環 2 px）。
      if (part === "seam" && melee && (state === "ok" || state === "hover")) {
        const r = W(MARK.chipR, MARK.chipMin), e = compact ? W(1, 1.5) : W(1, 0.5), cx = side < 0 ? x0 + T - r - e : x0 + r + e, cy = y0 + T - r - e; // 800 往格內多縮 1 px
        if (compact) backMark(ctx, cx, cy, r, S, side); else chip(ctx, BACK_CHIP, cx, cy, r, S, res, { ring: "#ffe9a8" });
      }
      ctx.restore();
    }
    if (hover === "body") { // 前殼（本體）：整個 3×3 外緣的攻擊紅框（同現行目標紅框 #ff4040）
      ctx.save(); const lw = W(2, 1.5); ctx.lineWidth = lw + W(1.6, 1); ctx.strokeStyle = OUT; ctx.strokeRect(-72 + 2, -144 + 2, 140, 140); ctx.lineWidth = lw; ctx.strokeStyle = MARK.body; ctx.strokeRect(-72 + 2, -144 + 2, 140, 140); ctx.restore();
    }
  }
  /** 800 寬的背刺記號（A3 時改，複審可修 A）：深底圓＋2 px 條件黃環 #ffd75e＋米白 U 形迴轉箭頭「∩」：外側那隻腳往上、繞過頂、從內側那隻腳往下，箭頭朝下＝「繞到背後」；
   *  第 2 版的箭頭幾乎繞成一整圈（讀成 @、重新整理），環色又接近米白括號。side＝殼縫在哪一側。 */
  const BACK_RING = "#ffd75e";
  function backMark(ctx, x, y, r, S, side) {
    const px = 1 / S, ring = 2 * px, a = r * 0.34, lw = Math.max(2 * px, r * 0.24), hw = r * 0.3, sx = -side; // sx：箭頭那隻腳在哪一側（內側）
    ctx.save(); ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fillStyle = "rgba(10,12,18,0.92)"; ctx.fill();
    ctx.lineWidth = ring; ctx.strokeStyle = BACK_RING; ctx.beginPath(); ctx.arc(x, y, r - ring / 2, 0, TAU); ctx.stroke();
    const top = y - r * 0.06, xo = x - sx * a, xi = x + sx * a; // 頂上半圓的圓心高度、外側腳、內側腳
    ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.strokeStyle = MARK.cream; ctx.lineWidth = lw;
    ctx.beginPath(); ctx.moveTo(xo, y + r * 0.46); ctx.lineTo(xo, top); ctx.arc(x, top, a, sx > 0 ? Math.PI : 0, sx > 0 ? 0 : Math.PI, sx < 0); ctx.lineTo(xi, y + r * 0.12); ctx.stroke();
    ctx.fillStyle = MARK.cream; ctx.beginPath(); ctx.moveTo(xi - hw, y + r * 0.1); ctx.lineTo(xi + hw, y + r * 0.1); ctx.lineTo(xi, y + r * 0.58); ctx.closePath(); ctx.fill();
    ctx.restore();
  }
  /** 區塊四角的 L 形括號（米白＋外框色襯邊）；x0、y0 是區塊左上，寬 w、高 1 格。 */
  function brackets(ctx, x0, y0, w, col, lw, ink, skip = -1) {
    const i = MARK.inset, a = MARK.arm, x1 = x0 + w - i, y1 = y0 + T - i, xa = x0 + i, ya = y0 + i;
    const segs = [[[xa, ya + a], [xa, ya], [xa + a, ya]], [[x1 - a, ya], [x1, ya], [x1, ya + a]], [[x1, y1 - a], [x1, y1], [x1 - a, y1]], [[xa + a, y1], [xa, y1], [xa, y1 - a]]].filter((_, k) => k !== skip); // skip：不畫的角（0 左上、1 右上、2 右下、3 左下）
    ctx.lineCap = "round"; ctx.lineJoin = "round";
    for (const [c, ww] of [[OUT, lw + 2 * ink], [col, lw]]) { ctx.strokeStyle = c; ctx.lineWidth = ww; for (const sg of segs) { ctx.beginPath(); sg.forEach(([x, y], k) => (k ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.stroke(); } }
  }
  /** 小圓片：深底＋色環＋Q 版圖樣（QIconsParts.chip；貼整數裝置像素）。gray＝圖樣去色（打不到的原因，同部位選單的灰原因小圖）。 */
  function chip(ctx, R, x, y, r, S, res, o = {}) {
    const QP = window.QIconsParts;
    if (!o.gray) { QP.chip(ctx, R.cat, R.id, x, y, r, { ring: o.ring, unitPx: S, res, bg: "rgba(10,12,18,0.88)" }); return; }
    ctx.save(); ctx.fillStyle = "rgba(10,12,18,0.88)"; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill(); ctx.strokeStyle = o.ring; ctx.lineWidth = Math.max(1 / S, r * 0.12); ctx.stroke();
    const cpx = r * 1.56 * S, gcv = QP.glyph(R.cat, R.id, cpx, res), gg = mk(gcv.width, gcv.height), gx = gg.getContext("2d"); gx.filter = "grayscale(1) brightness(1.05)"; gx.drawImage(gcv, 0, 0);
    const a = r * 1.56 * (48 / 36); window.QIconsWeapons.blit(ctx, gg, x - a / 2, y - a / 2, a, S * res); ctx.restore();
  }

  return { draw, groundGlow, stateOf, partMask, glowPart, flashPart, breakFx, popAt, popScale, POP, POP_STYLE, BRK, fill, drawMarks, groundRing, TILE_PART, PART_ZH, REASON, BACK_CHIP, MARK, HOVER, PLATES, VENTS, BEETLES, SEAM, tileXY, plateAnchor, seedOf, T, K, G, BOX, mk, tint, dilate };
})();
