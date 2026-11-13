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
  const CAVE = mix(BASALT, OUT, 0.55), COOL = "#2a221e";

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
  /** 平塗光暈：3 圈半透明同心圓（qBoss flatGlow）。 */
  function flatGlow(ctx, x, y, r, c, a, ry = r) { ctx.save(); ctx.fillStyle = c; for (const [k, al] of [[1, 0.16], [0.72, 0.2], [0.46, 0.26]]) { ctx.globalAlpha = al * a; ctx.beginPath(); ctx.ellipse(x, y, r * k, ry * k, 0, 0, TAU); ctx.fill(); } ctx.restore(); }

  // ---- 佔格與部位綁格（PhaseGB 計畫 D15、T11、T20） ----
  /** 3×3 每一格屬於哪個部位：[列（0 北、1 中、2 南）][欄（0 西、1 中、2 東）]。body＝前殼（本體，沒有部位）。 */
  const TILE_PART = [["vent", "vent", "vent"], ["seam", "core", "seam"], ["body", "body", "body"]];
  const PART_ZH = { vent: "熔岩噴口", seam: "殼縫", core: "核心", body: "前殼（本體）" };
  /** 一格的左上角（模型像素、相對錨點）。 */
  const tileXY = (row, col) => [(col - 1) * T - T / 2, -3 * T + row * T];

  // ---- 噴口（北排） ----
  const VENTS = [
    { x: -46, base: -96, top: -146, bw: 23, tw: 10, tilt: -0.2 },
    { x: 46, base: -96, top: -146, bw: 23, tw: 10, tilt: 0.2 },
    { x: 0, base: -110, top: -172, bw: 26, tw: 11, tilt: 0 },
  ];
  function vent(g, v, S, idx) {
    const h = v.base - v.top, sealed = !!S.broken.vent, P = "vent";
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
    if (sealed) { // 破＝封住（暫定，A4 再定）：冷掉的黑殼塞住口，兩道灰裂
      ell(g, 0, -h + 0.4, tw - 0.6, 3.6, kc(P, COOL));
      line(g, [[-tw * 0.5, -h - 0.6], [-tw * 0.1, -h + 0.6], [tw * 0.3, -h - 0.4]], 0.9, kc(P, "#6a605a"));
    } else {
      const hot = clamp(0.55 + 0.45 * S.breath * (S.phase === 1 ? 0.6 : 1));
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
    g.restore();
  }

  // ---- 背殼（岩丘，本體） ----
  const DOME = [[-70, -4], [-72, -34], [-67, -64], [-57, -90], [-43, -112], [-22, -129], [0, -133], [22, -129], [43, -112], [57, -90], [67, -64], [72, -34], [70, -4]];
  function domePath(g) { g.beginPath(); g.moveTo(...DOME[0]); for (let i = 1; i < DOME.length - 1; i++) { const [x, y] = DOME[i], [nx, ny] = DOME[i + 1]; g.quadraticCurveTo(x, y, (x + nx) / 2, (y + ny) / 2); } g.lineTo(...DOME[DOME.length - 1]); g.closePath(); }
  function dome(g, S) {
    domePath(g); g.fillStyle = BASALT; g.fill();
    g.save(); domePath(g); g.clip();
    ell(g, -28, -118, 40, 15, light(BASALT, 0.12), { rot: -0.28, line: false }); // 左上亮面
    ell(g, 46, -60, 30, 50, dark(BASALT, 0.16), { rot: 0.1, line: false }); // 右下暗面
    // 岩丘上的甲蟲背（不會掉；qBoss 底座 4 隻甲蟲背的放大）
    for (const [x, y, rx, ry, r] of [[-25, -119, 13, 7.5, -0.35], [25, -119, 13, 7.5, 0.35], [-45, -101, 11, 7, -0.75], [45, -101, 11, 7, 0.75], [-60, -62, 7, 11, 0.15], [60, -62, 7, 11, -0.15]]) {
      ell(g, x, y, rx, ry, BASALT_L, { rot: r });
      g.save(); g.translate(x, y); g.rotate(r); line(g, [[0, -ry + 1], [0, ry - 1]], 0.9 * G * 0.7, OUT); ell(g, -rx * 0.35, -ry * 0.35, rx * 0.3, ry * 0.25, light(BASALT_L, 0.22), { line: false }); g.restore();
    }
    g.restore();
  }

  // ---- 殼縫（中排東西，兩格同一個部位） ----
  const SEAM = [[54, -93], [58, -83], [55, -72], [60, -62], [57, -52], [61, -44]];
  function seam(g, s, S) {
    const P = "seam", pts = SEAM.map(([x, y]) => [s * x, y]), br = !!S.broken.seam;
    const heat = br ? 0 : clamp(0.45 + 0.55 * S.breath);
    if (!br) { g.save(); g.globalAlpha = 0.22; line(g, pts, 10, kc(P, LAVA)); g.restore(); } // 縫邊的熱光（平塗一圈）
    for (const [a, b] of [[1, [s * 64, -88]], [3, [s * 52, -60]]]) { line(g, [pts[a], b], 3.4, kc(P, br ? "#1e1612" : EMBER)); line(g, [pts[a], b], 1.5, kc(P, br ? "#4a2a1c" : LAVA)); }
    line(g, pts, 6.4, kc(P, br ? "#1e1612" : EMBER));
    line(g, pts, 3.8, kc(P, br ? "#4a2a1c" : LAVA));
    if (!br) line(g, pts, 1.5, kc(P, mix(LAVA, LAVA_HOT, heat)));
  }

  // ---- 殼窩、殼蓋、核心（中心格） ----
  const CX = 0, CY = -88, CAV_RX = 30, CAV_RY = 35;
  const CORE_PTS = [[0, -15], [10, -8], [11, 4], [4, 13], [-6, 12], [-11, 3], [-9, -9]]; // qBoss core() 的形
  const CK = G * 1.45; // 核心比 1 格版大 1.45 倍
  function cavity(g, S) {
    ell(g, CX, CY, CAV_RX + 3.5, CAV_RY + 3.5, BASALT_L); // 窩緣
    ell(g, CX, CY, CAV_RX, CAV_RY, CAVE);
    g.save(); g.beginPath(); g.ellipse(CX, CY, CAV_RX, CAV_RY, 0, 0, TAU); g.clip();
    ell(g, CX, CY + 26, 24, 10, mix(CAVE, LAVA, 0.55), { line: false }); // 窩底的熔岩光
    if (S.phase >= 2) flatGlow(g, CX, CY, 34, CORE, (0.55 + 0.45 * S.breath) * (1 - S.die));
    g.restore();
  }
  function core(g, S) {
    const P = "core", s = (1 + 0.06 * S.breath) * (1 - 0.55 * S.die);
    g.save(); g.translate(CX, CY - S.inhale * 2); g.scale(CK * s, CK * s);
    let c = mix(CORE, "#fff4d0", 0.35 * S.breath + 0.4 * S.crack);
    if (S.die > 0) c = mix(c, "#5a4a44", S.die);
    const lw = LW / CK;
    poly(g, CORE_PTS, kc(P, c), { lw });
    g.save(); path(g, CORE_PTS); g.clip();
    poly(g, [[0, -15], [-9, -9], [-11, 3], [1, 0]], kc(P, light(c, 0.35)), { line: false });
    poly(g, [[11, 4], [4, 13], [1, 0]], kc(P, dark(c, 0.12)), { line: false });
    g.restore();
    g.fillStyle = kc(P, "#ffffff"); g.fillRect(-5, -9, 2.2, 4.4); g.fillRect(-2, -10.4, 1.4, 1.4);
    if (S.crack > 0) { g.save(); g.globalAlpha = clamp(S.crack); line(g, [[-2, -12], [2, -4], [-1, 3], [3, 10]], 1.6 * 0.8, kc(P, "#ffffff")); line(g, [[8, -6], [3, -2], [7, 6]], 1.3 * 0.8, kc(P, "#fff4c0")); g.restore(); }
    g.restore();
  }
  /** 殼蓋：兩片甲蟲殼在殼窩前合起來（第 1 階段），中縫透出核心的光；第 2 階段起往兩側掀開（窄成側邊的兩片）。open 0～1。 */
  function lid(g, S, open) {
    const glow = mix(LAVA, LAVA_HOT, clamp(0.3 + 0.7 * S.breath));
    if (open < 1) { // 中縫的光（合著時）
      g.save(); g.globalAlpha = 1 - open; line(g, [[CX, CY - CAV_RY + 4], [CX - 1.5, CY - 8], [CX + 1.2, CY + 10], [CX, CY + CAV_RY - 5]], 5, glow); g.restore();
    }
    for (const s of [-1, 1]) {
      g.save(); g.translate(CX + s * (CAV_RX + 1), CY); g.scale(1 - 0.62 * open, 1); g.translate(-s * (CAV_RX + 1), 0);
      const half = [];
      for (let i = 0; i <= 12; i++) { const a = -Math.PI / 2 + (i / 12) * Math.PI; half.push([s * Math.cos(a) * (CAV_RX + 1.5), Math.sin(a) * (CAV_RY + 1.5)]); }
      half.push([s * 2.2, CY - CY + CAV_RY - 4], [s * 1.2, 10], [s * 3.2, -8], [s * 2, -CAV_RY + 5]);
      poly(g, half, BASALT_L);
      g.save(); path(g, half); g.clip();
      ell(g, s * 16, -14, 9, 13, s < 0 ? light(BASALT_L, 0.2) : dark(BASALT_L, 0.1), { line: false, rot: s * 0.3 });
      for (const yy of [-12, 10]) line(g, [[s * 4, yy], [s * 27, yy + 3]], 0.9 * G * 0.7, OUT); // 殼片分節
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
  /** [名稱, x, y, 旋轉, 寬, 高]（模型像素） */
  const PLATES = [
    ["p-back-l", -30, -118, -0.5, 30, 20], ["p-back-r", 30, -118, 0.5, 30, 20], ["p-top", 0, -127, 0, 32, 19],
    ["p-left", -38, -86, -0.9, 26, 22], ["p-right", 38, -86, 0.9, 26, 22],
    ["p-low-l", -24, -63, -0.3, 30, 18], ["p-low-r", 24, -63, 0.3, 30, 18], ["p-front", 0, -72, 0, 34, 19],
    ["p-mid-l", -16, -100, -0.2, 24, 18], ["p-mid-r", 16, -100, 0.2, 24, 18],
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
  /** 殼片的掛點：熔殼在＝貼著（第 2、3 階段＝往外撐開、露出核心），隨呼吸張開；不在＝依名稱雜湊飛出、落在兩側前角（南排外側兩格的外半邊），不出佔格。 */
  function plateAnchor(p, shell, bt, breath, open) {
    const [key, x, y, r] = p;
    if (shell > 0) {
      const o = 0.6 * breath, k = open ? 1.42 : 1, px = CX + (x - CX) * k, py = CY + (y - CY) * (open ? 1.2 : 1);
      return { x: px * (1 + 0.02 * o), y: py - o * 0.9, r: r * (open ? 1.25 : 1), a: 1, s: 1 };
    }
    const dir = Math.sign(x || rnd(key) - 0.5) || 1, spin = (rnd(key, 3) - 0.5) * 6;
    const fx = dir * (36 + 24 * rnd(key, 1)), fy = -15 - 32 * rnd(key, 4), hop = 30 + 24 * rnd(key, 2);
    if (bt >= 1) return { x: fx, y: fy, r: r + spin * 0.8, a: 0.85, s: 0.74 };
    const u = clamp(bt);
    return { x: x + (fx - x) * u, y: y + (fy - y) * u * u - hop * Math.sin(Math.PI * u), r: r + spin * 0.8 * u, a: 1, s: 1 - 0.26 * u };
  }

  /** 狀態：st＝{ phase: 1|2|3, shell: 0～1（熔殼在不在；預設第 1 階段在、其他不在）, breakT: 0～1（脫落進度）, t: 毫秒, spout, inhale, dieT, broken: { vent, seam } } */
  function stateOf(st = {}) {
    const t = num(st.t, 0), phase = [1, 2, 3].includes(st.phase) ? st.phase : 1;
    const shell = clamp(num(st.shell, phase === 1 ? 1 : 0)), bt = clamp(num(st.breakT, shell > 0 ? 0 : 1));
    return { t, phase, shell, bt, breath: 0.5 + 0.5 * Math.sin(t / 420), crack: phase === 3 ? 0.6 + 0.4 * Math.sin(t / 160) : 0, inhale: clamp(num(st.inhale, 0)), spout: clamp(num(st.spout, 0)), die: clamp(num(st.dieT, 0)), broken: st.broken ?? {} };
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
    const order = S.shell > 0 ? PLATES : [...PLATES].sort((a, b) => plateAnchor(a, 0, S.bt, 0).y - plateAnchor(b, 0, S.bt, 0).y);
    for (const p of order) { const A = plateAnchor(p, S.shell, S.bt, S.breath, open); g.save(); g.globalAlpha = A.a; g.translate(A.x, A.y); g.rotate(A.r); g.scale(A.s, A.s); plate(g, p[4], p[5], S.shell > 0 ? S.breath : 0.12); g.restore(); }
  }

  /** 地面：3×3 陣營環（提案 A：圓角方框貼佔格內 3）＋精英金框＋南緣中點金菱形＋影子。opt.ring＝"rect"（預設）｜"ellipse"（提案 B）｜false。 */
  function groundRing(ctx, opt = {}) {
    const mode = opt.ring ?? "rect";
    ctx.save();
    ctx.fillStyle = "rgba(10,8,14,0.35)"; ctx.beginPath(); ctx.ellipse(0, -30, 74, 26, 0, 0, TAU); ctx.fill();
    if (mode === "rect") {
      const r = { x: -69, y: -141, w: 138, h: 138 };
      ctx.beginPath(); ctx.roundRect(r.x, r.y, r.w, r.h, 14); ctx.globalAlpha = 0.8; ctx.fillStyle = "#c63b3b"; ctx.fill(); ctx.globalAlpha = 1; ctx.lineWidth = 1.5 * 1.6; ctx.strokeStyle = "#ffb3a8"; ctx.stroke();
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

  /**
   * 畫灰燼之心（3×3）。ctx 目前座標＝模型像素、原點＝錨點（南排南緣中點）。st 見 stateOf；opt：
   *   glow（頭目外光色，預設傳說金；false＝不畫）、ring（"rect"｜"ellipse"｜false）、flash（受擊白閃 0～1）、key（部位 id：那個部位換記號色，遮罩用）。
   */
  function draw(ctx, st = {}, opt = {}) {
    const S = stateOf(st);
    if (opt.ring !== false) groundRing(ctx, opt);
    if (S.phase === 3 && opt.pitGlow !== false) flatGlow(ctx, 0, -50, 112, "#ff6e1e", 1 - S.die, 92); // 熔毀：坑底發紅（地面的光，不算外接框）
    KEY = opt.key ?? null;
    try {
      layer(ctx, BOX, (g) => bodyLayer(g, S), { ow: OW, glow: opt.glow === false || S.die > 0 ? null : (opt.glow ?? GOLD), glowW: GLOW_W, glowA: GLOW_A, flash: num(opt.flash, 0) });
    } finally { KEY = null; }
    // 小粒子（吸氣的火星、熔毀滴落）：細外框（qBoss 同）
    const parts = [];
    if (S.inhale > 0) for (let k = 0; k < 16; k++) { const a = rnd("in", k) * TAU, d = 96 * (1 - ((S.t / 600 + rnd("in2", k)) % 1)); parts.push([CX + Math.cos(a) * d, CY + Math.sin(a) * d * 0.6, 2.8, LAVA_HOT]); }
    // 熔毀的滴落改成殼窩下緣的熔岩流（畫在本體裡），不另外畫粒子（粒子落在甲蟲臉上會讀成鼻子）
    if (parts.length && !opt.key) layer(ctx, BOX, (g) => { for (const [x, y, r, c] of parts) { g.fillStyle = c; g.beginPath(); g.arc(x, y, r, 0, TAU); g.fill(); } }, { ow: 0.8 * G, alpha: S.inhale > 0 && S.phase !== 3 ? Math.max(0.3, S.inhale) : 1 });
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
    const one = (key) => { const c = mk(w, h), g = c.getContext("2d", { willReadFrequently: true }); g.setTransform(m); draw(g, st, { glow: false, ring: false, key }); return c; };
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
    for (const [part, row, c0, n, side] of REGIONS) {
      const st = parts[part] ?? { state: "ok" }, [x0, y0] = tileXY(row, c0), w = n * T;
      let state = st.state;
      if (state === "ok" && hover === part) state = "hover";
      const ins = MARK.inset, inner = [x0 + ins - 1, y0 + ins - 1, w - 2 * ins + 2, T - 2 * ins + 2];
      ctx.save();
      if (state === "ok") brackets(ctx, x0, y0, w, MARK.cream, W(MARK.w, MARK.minW), W(MARK.inkW, 1));
      else if (state === "hover") {
        const lw = W(2.6, 2);
        ctx.fillStyle = MARK.hover; ctx.globalAlpha = 0.14; ctx.fillRect(...inner); ctx.globalAlpha = 1;
        ctx.beginPath(); ctx.roundRect(...inner, 5); ctx.lineWidth = lw + 2 * W(MARK.inkW, 1); ctx.strokeStyle = OUT; ctx.stroke(); ctx.lineWidth = lw; ctx.strokeStyle = MARK.hover; ctx.stroke();
      } else if (state === "off") {
        ctx.fillStyle = "rgba(10,8,14,0.34)"; ctx.fillRect(...inner);
        ctx.globalAlpha = 0.75; brackets(ctx, x0, y0, w, MARK.dimLine, W(1.8, 1), W(1.4, 1)); ctx.globalAlpha = 1;
        const R = REASON[st.why] ?? REASON.range; chip(ctx, R, x0 + w / 2, y0 + T / 2, W(MARK.chipR, MARK.chipMin), S, res, { ring: "rgba(255,255,255,0.35)", gray: true });
      } else if (state === "broken") {
        ctx.fillStyle = MARK.broken; ctx.globalAlpha = 0.55; ctx.fillRect(...inner); ctx.globalAlpha = 1;
        const r = W(MARK.xSize, MARK.xMin) / 2, lw = W(3, 1.5);
        ctx.lineCap = "round";
        for (let k = 0; k < n; k++) { const cx = x0 + k * T + T / 2, cy = y0 + T / 2; for (const [c, lww] of [[OUT, lw + W(2.4, 1.2)], [MARK.x, lw]]) { ctx.strokeStyle = c; ctx.lineWidth = lww; ctx.beginPath(); ctx.moveTo(cx - r, cy - r); ctx.lineTo(cx + r, cy + r); ctx.moveTo(cx + r, cy - r); ctx.lineTo(cx - r, cy + r); ctx.stroke(); } }
      } else if (state === "hidden") {
        ctx.setLineDash([W(4, 2.5), W(3, 2)]); ctx.beginPath(); ctx.roundRect(...inner, 5);
        ctx.lineWidth = W(1.6, 1) + 2 * W(1, 0.8); ctx.strokeStyle = OUT; ctx.globalAlpha = 0.8; ctx.stroke(); ctx.lineWidth = W(1.6, 1); ctx.strokeStyle = MARK.dimLine; ctx.stroke(); ctx.setLineDash([]); ctx.globalAlpha = 1;
      }
      // 殼縫：近戰時外側下角一顆背刺小圖（「算從背後」；R4 遠程不算，不畫）。放外側下角，避開預告格右上角的字
      if (part === "seam" && melee && (state === "ok" || state === "hover")) {
        const r = W(MARK.chipR, MARK.chipMin), cx = side < 0 ? x0 + r + W(1, 0.5) : x0 + T - r - W(1, 0.5), cy = y0 + T - r - W(1, 0.5);
        chip(ctx, BACK_CHIP, cx, cy, r, S, res, { ring: "#ffe9a8" });
      }
      ctx.restore();
    }
    if (hover === "body") { // 前殼（本體）：整個 3×3 外緣的攻擊紅框（同現行目標紅框 #ff4040）
      ctx.save(); const lw = W(2, 1.5); ctx.lineWidth = lw + W(1.6, 1); ctx.strokeStyle = OUT; ctx.strokeRect(-72 + 2, -144 + 2, 140, 140); ctx.lineWidth = lw; ctx.strokeStyle = MARK.body; ctx.strokeRect(-72 + 2, -144 + 2, 140, 140); ctx.restore();
    }
  }
  /** 區塊四角的 L 形括號（米白＋外框色襯邊）；x0、y0 是區塊左上，寬 w、高 1 格。 */
  function brackets(ctx, x0, y0, w, col, lw, ink) {
    const i = MARK.inset, a = MARK.arm, x1 = x0 + w - i, y1 = y0 + T - i, xa = x0 + i, ya = y0 + i;
    const segs = [[[xa, ya + a], [xa, ya], [xa + a, ya]], [[x1 - a, ya], [x1, ya], [x1, ya + a]], [[x1, y1 - a], [x1, y1], [x1 - a, y1]], [[xa + a, y1], [xa, y1], [xa, y1 - a]]];
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

  return { draw, stateOf, partMask, glowPart, drawMarks, groundRing, TILE_PART, PART_ZH, REASON, BACK_CHIP, MARK, HOVER, PLATES, VENTS, BEETLES, SEAM, tileXY, plateAnchor, seedOf, T, K, G, BOX, mk, tint, dilate };
})();
