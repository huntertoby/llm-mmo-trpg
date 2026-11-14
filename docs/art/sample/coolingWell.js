// 冷卻井 cooling_well（灰燼荒原／熔心坑；docs/design/20 灰燼之心那列、docs/art/冷卻井-移植需求.md）。畫圖 agent，2026-11-14。
// 畫法照遊戲端現行灰燼物件（client/src/render/ashenObjects.ts）：52 單位一格、外框 ASH.outline、灰褐石（ruinTop／ruinFace）、
// 鐵箍照鐵油桶（#3a3c3e 箍、#9a4a20 鏽點）、「打破會怎樣」的記號照油桶的危險記號（畫在物件身上，黑框實心小圖形）：這裡是藍色水滴。
// 換皮不換功能：不擋視線、不是掩護 → 井圈要矮（面高 11 單位 ≈ 0.21 T，低於矮牆的 0.3 T），沒有高的轆轤架（舊樣張 ashenTiles.js coolingWell 有，拿掉）。
// 由 ashenTiles.js coolingWell（石井圈＋藍水＋鐵轆轤）出發；藍水在灰燼區要醒目（四區移植需求 第 2 節：藍色最醒目、一眼看出是冷卻井）。
// 介面：CoolingWell.draw(ctx, { x, y, hpStage, flash })、rubble(ctx, { x, y }, k)、breakFx(ctx, { x, y }, k)、spillMask(ctx, k)、FRAMES；全部在 52 單位格內座標畫（呼叫端 translate＋scale(T/52)）。
(function () {
  const T = 52, TAU = Math.PI * 2, OUT = "#1c1712";
  const C = {
    top: "#7a6e64", // ASH.ruinTop
    face: "#5a4e44", // ASH.ruinFace
    mortar: "#2e2620", // 荒原矮牆的灰縫
    crack: "#1a1410",
    iron: "#3a3c3e", rust: "#9a4a20", // 鐵油桶的箍與鏽點
    inner: "#231c17", // 井壁（井口裡看得到的深色）
    water: "#3a8ee0", waterHi: "#8fd4ff", waterDeep: "#1f5a9a", // 井水：比荒原水表面（#45627a）亮，灰褐裡一眼看到
    drop: "#4aa8ff", ink: "#1a1208", // 水滴記號：元素水色 palette.ts／危險記號的黑框色
    steam: "rgba(232,242,250,0.42)",
  };
  /** 井圈幾何：頂面橢圓中心 (26, 21)、半徑 20×11.5、正面高 11 → 最低點 43.5（物件耐久條在 0.84 T＝43.7，不蓋到井身與水滴記號）；井口 13.5×7。 */
  const G = { cx: 26, ty: 21, rx: 20, ry: 11.5, face: 11, irx: 13.5, iry: 7 };
  /** 破壞演出時間表（ms，事件到達起算）：K 0 裂、1 爆開、2 漫出、3 鋪滿、4 留下（＝靜態的打破後）。 */
  const FRAMES = [
    { k: 0, ms: 0, zh: "裂：井圈白閃＋裂縫亮、水從裂縫噴" },
    { k: 1, ms: 90, zh: "爆開：井圈碎成 7 塊往外飛、中央水柱、水面從井心長到半格" },
    { k: 2, ms: 200, zh: "漫出：碎塊落地、水花往外、水面長到十字 4 格" },
    { k: 3, ms: 340, zh: "鋪滿：水面長到 3×3 的角、漣漪一圈" },
    { k: 4, ms: 520, zh: "留下：3×3 水表面（現行畫法）＋碎石圈" },
  ];
  /** 水面遮罩半徑（52 單位，從井心算；k 4＝整個 3×3）。 */
  const MASK_R = [0, 30, 60, 92, Infinity];

  function rng(x, y, salt) { // 格子座標雜湊（同 artRandom.ts 的用法：同格同結果）
    let a = (Math.imul(x | 0, 374761393) + Math.imul(y | 0, 668265263) + Math.imul(salt | 0, 1274126177)) | 0;
    return () => { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  const yTop = (x) => G.ty + G.ry * Math.sqrt(Math.max(0, 1 - ((x - G.cx) / G.rx) ** 2)); // 頂面橢圓前緣在 x 的 y
  function shadowEllipse(ctx, cx, cy, rx, ry) { ctx.fillStyle = "rgba(0,0,0,0.28)"; ctx.beginPath(); ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU); ctx.fill(); }
  function facePath(ctx) {
    const { cx, ty, rx, ry, face } = G;
    ctx.beginPath(); ctx.moveTo(cx - rx, ty); ctx.lineTo(cx - rx, ty + face);
    ctx.ellipse(cx, ty + face, rx, ry, 0, Math.PI, 0, true); ctx.lineTo(cx + rx, ty);
    ctx.ellipse(cx, ty, rx, ry, 0, 0, Math.PI, false); ctx.closePath();
  }
  function line(ctx, pts, color, w) { ctx.strokeStyle = color; ctx.lineWidth = w; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.stroke(); }

  /** 水滴記號（打破會漏水；照油桶 hazardMark 的做法：黑框實心小圖形畫在物件正面）。中心 (cx, cy)。 */
  function spillMark(ctx, cx, cy, s = 6.5) {
    ctx.beginPath(); ctx.moveTo(cx, cy - s);
    ctx.bezierCurveTo(cx + s * 0.35, cy - s * 0.45, cx + s * 0.72, cy - s * 0.05, cx + s * 0.72, cy + s * 0.32);
    ctx.arc(cx, cy + s * 0.32, s * 0.72, 0, Math.PI, false);
    ctx.bezierCurveTo(cx - s * 0.72, cy - s * 0.05, cx - s * 0.35, cy - s * 0.45, cx, cy - s); ctx.closePath();
    ctx.fillStyle = C.drop; ctx.fill(); ctx.lineWidth = 1.6; ctx.strokeStyle = C.ink; ctx.stroke();
    ctx.fillStyle = "rgba(255,255,255,0.8)"; ctx.beginPath(); ctx.ellipse(cx - s * 0.3, cy + s * 0.18, s * 0.17, s * 0.3, 0.3, 0, TAU); ctx.fill();
  }

  /** 井水與井口（頂面橢圓之後畫）。 */
  function water(ctx, stage) {
    const { cx, ty, irx, iry } = G;
    ctx.save(); ctx.beginPath(); ctx.ellipse(cx, ty + 0.5, irx, iry, 0, 0, TAU); ctx.clip();
    ctx.fillStyle = C.inner; ctx.fillRect(cx - irx, ty - iry, irx * 2, iry * 2 + 1);
    const wy = ty + 2.6 + (stage === 2 ? 1 : 0); // 破很重時水位低一點（在漏）
    ctx.beginPath(); ctx.ellipse(cx, wy, irx - 0.8, iry - 1.4, 0, 0, TAU); ctx.fillStyle = C.water; ctx.fill();
    ctx.fillStyle = "rgba(0,0,0,0.22)"; ctx.beginPath(); ctx.ellipse(cx + 4, wy + 2, irx - 4, iry - 3, 0, 0, TAU); ctx.fill(); // 暗面（右下）
    ctx.fillStyle = C.waterHi; ctx.beginPath(); ctx.ellipse(cx - 4, wy - 1.6, 5.5, 1.8, -0.08, 0, TAU); ctx.fill(); // 亮面（左上）
    line(ctx, [[cx + 2, wy + 1.2], [cx + 8, wy + 0.8]], "rgba(255,255,255,0.75)", 1.1);
    ctx.restore();
    ctx.lineWidth = 1.4; ctx.strokeStyle = OUT; ctx.beginPath(); ctx.ellipse(cx, ty + 0.5, irx, iry, 0, 0, TAU); ctx.stroke();
  }

  /** 熱氣：兩縷白煙從井水往上（坑是火場、井水是冷的）。半透明細線，不加高剪影。 */
  function steam(ctx) {
    const { cx, ty } = G; ctx.save(); ctx.lineCap = "round"; ctx.strokeStyle = C.steam; ctx.lineWidth = 2.2;
    ctx.beginPath(); ctx.moveTo(cx - 4, ty); ctx.bezierCurveTo(cx - 9, ty - 4, cx - 1, ty - 8, cx - 6, ty - 14); ctx.stroke();
    ctx.lineWidth = 1.8; ctx.beginPath(); ctx.moveTo(cx + 5, ty - 1); ctx.bezierCurveTo(cx + 9, ty - 5, cx + 3, ty - 8, cx + 7, ty - 12); ctx.stroke();
    ctx.restore();
  }

  /** 完好／受損的冷卻井。s＝{ x, y, hpStage 0｜1｜2, flash（破壞演出 K0 白閃）}。受損級距自己畫（同薄冰；不套通用 cracks）。 */
  function draw(ctx, s) {
    const st = s.hpStage ?? 0, { cx, ty, rx, ry, face } = G, r = rng(s.x ?? 0, s.y ?? 0, 241);
    shadowEllipse(ctx, cx + 3, ty + face + 5, rx + 3, ry - 2);
    if (st === 2) { // 前面一灘漏出來的水（被正面蓋住上緣）
      ctx.fillStyle = "rgba(58,142,224,0.6)"; ctx.beginPath(); ctx.ellipse(cx + 4, ty + face + ry - 0.5, 13, 3.6, 0, 0, TAU); ctx.fill();
    }
    // 正面（石塊兩層＋鐵箍）
    facePath(ctx); ctx.fillStyle = C.face; ctx.fill();
    ctx.save(); facePath(ctx); ctx.clip();
    ctx.fillStyle = "rgba(0,0,0,0.22)"; ctx.fillRect(cx + 7, 0, T, T); // 暗面（右）
    ctx.strokeStyle = C.mortar; ctx.lineWidth = 1.1;
    ctx.beginPath(); ctx.ellipse(cx, ty + face * 0.55, rx, ry, 0, 0.05, Math.PI - 0.05); ctx.stroke(); // 兩層石塊的橫縫
    for (const x of [13, 25, 37]) { const y0 = yTop(x); ctx.beginPath(); ctx.moveTo(x, y0 + 3.2); ctx.lineTo(x, y0 + face * 0.55); ctx.stroke(); }
    for (const x of [8, 19, 31, 42]) { const y0 = yTop(x); ctx.beginPath(); ctx.moveTo(x, y0 + face * 0.55); ctx.lineTo(x, y0 + face); ctx.stroke(); }
    ctx.restore();
    ctx.strokeStyle = C.iron; ctx.lineWidth = 2.4; ctx.beginPath(); ctx.ellipse(cx, ty + 2.4, rx, ry, 0, 0.02, Math.PI - 0.02); ctx.stroke(); // 鐵箍（貼頂緣）
    for (const x of [10, 26, 42]) { ctx.fillStyle = "#6a6e70"; ctx.beginPath(); ctx.arc(x, yTop(x) + 2.4, 1.1, 0, TAU); ctx.fill(); }
    for (const [x, dy, rad] of [[17, 2.6, 1.6], [34, 2.8, 1.3]]) { ctx.fillStyle = C.rust; ctx.beginPath(); ctx.arc(x, yTop(x) + dy, rad, 0, TAU); ctx.fill(); }
    facePath(ctx); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    // 頂面井圈（石塊）
    ctx.beginPath(); ctx.ellipse(cx, ty, rx, ry, 0, 0, TAU); ctx.fillStyle = C.top; ctx.fill();
    ctx.strokeStyle = C.mortar; ctx.lineWidth = 1.1; ctx.beginPath();
    for (const a of [0.3, 1.15, 1.95, 2.8, 3.55, 4.35, 5.15, 5.85]) { ctx.moveTo(cx + Math.cos(a) * G.irx, ty + 0.5 + Math.sin(a) * G.iry); ctx.lineTo(cx + Math.cos(a) * rx, ty + Math.sin(a) * ry); }
    ctx.stroke();
    ctx.strokeStyle = "rgba(255,255,255,0.4)"; ctx.lineWidth = 1.6; ctx.beginPath(); ctx.ellipse(cx, ty, rx - 2, ry - 1.6, 0, Math.PI * 1.08, Math.PI * 1.42); ctx.stroke(); // 亮面（左上）
    ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.beginPath(); ctx.ellipse(cx, ty, rx, ry, 0, 0, TAU); ctx.stroke();
    water(ctx, st);
    if (st === 2) { // 井圈前右缺一塊（看得到裡面的水）
      ctx.beginPath(); ctx.moveTo(cx + 9, ty + 5.6); ctx.lineTo(cx + 12.5, ty + 10.8); ctx.lineTo(cx + 16.5, ty + 7.6); ctx.lineTo(cx + 13.2, ty + 3.6); ctx.closePath();
      ctx.fillStyle = C.water; ctx.fill(); ctx.lineWidth = 1.4; ctx.strokeStyle = OUT; ctx.stroke();
    }
    if (st >= 1) { // 裂縫＋從裂縫流下的水
      const k = (r() - 0.5) * 2;
      line(ctx, [[15, yTop(15) - 0.5], [16.5 + k, yTop(15) + 3.5], [14.5, yTop(15) + 7], [16 + k, yTop(15) + face]], C.crack, 1.5);
      line(ctx, [[16 + k, yTop(15) + face - 1], [15.5 + k, yTop(15) + face + 3.5]], C.water, 1.8);
      ctx.fillStyle = "rgba(58,142,224,0.55)"; ctx.beginPath(); ctx.ellipse(15.5 + k, yTop(15) + face + 3.8, 4.2, 1.6, 0, 0, TAU); ctx.fill();
    }
    if (st === 2) {
      line(ctx, [[37, yTop(37)], [35.5, yTop(37) + 4], [38, yTop(37) + 7.5], [36.5, yTop(37) + face]], C.crack, 1.5);
      line(ctx, [[cx - 6, ty - 9.5], [cx - 4, ty - 7], [cx - 6.5, ty - 5.6]], C.crack, 1.3); // 頂面後側的裂
      line(ctx, [[36.5, yTop(37) + face - 1], [37.5, yTop(37) + face + 3]], C.water, 1.8);
    }
    if (s.flash) { // 破壞演出 K0：井圈白閃（同受擊白閃的做法：蓋一層白）＋裂縫亮
      ctx.save(); ctx.fillStyle = "rgba(255,255,255,0.5)"; facePath(ctx); ctx.fill();
      ctx.beginPath(); ctx.ellipse(cx, ty, rx, ry, 0, 0, TAU); ctx.ellipse(cx, ty + 0.5, G.irx, G.iry, 0, 0, TAU); ctx.fill("evenodd"); ctx.restore();
      for (const pts of [[[15, yTop(15)], [16.5, yTop(15) + 4], [14.5, yTop(15) + 7.5], [16, yTop(15) + face]], [[37, yTop(37)], [35.5, yTop(37) + 4], [38, yTop(37) + 8], [36.5, yTop(37) + face]], [[cx + 1, ty + 7.6], [cx + 2.5, ty + 10], [cx, ty + 14]]]) { line(ctx, pts, C.crack, 2.6); line(ctx, pts, C.waterHi, 1.2); }
      for (const [x0, y0, dx, dy] of [[16, yTop(15) + 6, -6, -2], [36.5, yTop(37) + 6, 6, -2.5], [cx + 1.5, ty + 12, 0.5, 4]]) line(ctx, [[x0, y0], [x0 + dx, y0 + dy]], C.waterHi, 2); // 裂縫噴水
    } else if (st < 2) steam(ctx);
    spillMark(ctx, cx, ty + ry + face * 0.5 - 0.5, 6.2);
  }

  // ---- 碎石圈（打破後殘留；裝飾、不擋路）與破壞演出 ----
  /** 7 塊碎石：k 1 往外飛（抬高）、k 2 快落地、k ≥ 3 落定（＝碎石圈）。回傳 [{ x, y, lift, pts, rot }]。 */
  function chunks(s, k) {
    const r = rng(s.x ?? 0, s.y ?? 0, 242), out = [];
    const spread = [0, 6, 10, 4, 4][Math.min(4, k)], lift = [0, 9, 4, 0, 0][Math.min(4, k)];
    for (let i = 0; i < 7; i++) {
      const a = (i / 7) * TAU + 0.35 + (r() - 0.5) * 0.3, rad = 4.2 + r() * 1.6, n = 6, pts = [];
      for (let j = 0; j < n; j++) { const b = (j / n) * TAU + r() * 0.5; const q = rad * (0.78 + r() * 0.3); pts.push([Math.cos(b) * q, Math.sin(b) * q * 0.66]); }
      out.push({ a, x: G.cx + Math.cos(a) * (15 + spread), y: RUB_Y + Math.sin(a) * (8.5 + spread * 0.6), lift: lift * (0.7 + r() * 0.6), pts });
    }
    return out.sort((p, q) => p.y - q.y);
  }
  const RUB_Y = 28; // 碎石圈中心（井圈落地處）
  function chunk(ctx, c) {
    const th = 3; // 厚度（碎石很矮：比井圈正面 11 低很多）
    if (c.lift < 1) { ctx.fillStyle = "rgba(0,0,0,0.3)"; ctx.beginPath(); ctx.ellipse(c.x + 1.2, c.y + th + 0.8, 5, 1.8, 0, 0, TAU); ctx.fill(); }
    else { ctx.fillStyle = "rgba(0,0,0,0.2)"; ctx.beginPath(); ctx.ellipse(c.x, c.y + th, 3.6, 1.3, 0, 0, TAU); ctx.fill(); } // 在空中：地上的影子小一點
    const path = (dy) => { ctx.beginPath(); c.pts.forEach(([px, py], i) => (i ? ctx.lineTo(c.x + px, c.y - c.lift + py + dy) : ctx.moveTo(c.x + px, c.y - c.lift + py + dy))); ctx.closePath(); };
    // 外框：每一層都描粗線（剪影＝頂面＋往下擠出 th）；再填側面、頂面
    ctx.lineJoin = "round"; ctx.strokeStyle = OUT; ctx.lineWidth = 3;
    for (let dy = 0; dy <= th; dy += 1) { path(dy); ctx.stroke(); }
    ctx.fillStyle = C.face; for (let dy = 1; dy <= th; dy += 1) { path(dy); ctx.fill(); }
    path(0); ctx.fillStyle = C.top; ctx.fill(); ctx.lineWidth = 1; ctx.strokeStyle = "rgba(28,23,18,0.6)"; ctx.stroke();
    ctx.fillStyle = "rgba(255,255,255,0.35)"; ctx.beginPath(); ctx.ellipse(c.x - 1.2, c.y - c.lift - 0.8, 2, 0.8, -0.2, 0, TAU); ctx.fill();
  }
  /** 打破後殘留：舊井口的深水影（水表面之上）＋一圈 7 塊碎石。k 預設 4（靜態）。 */
  function rubble(ctx, s, k = 4) {
    if (k >= 3) { ctx.fillStyle = "rgba(16,40,72,0.5)"; ctx.beginPath(); ctx.ellipse(G.cx, RUB_Y, 10, 5.6, 0, 0, TAU); ctx.fill(); }
    for (const c of chunks(s, k)) chunk(ctx, c);
  }
  function drops(ctx, list) {
    for (const [x, y, rad] of list) { ctx.beginPath(); ctx.arc(x, y, rad, 0, TAU); ctx.fillStyle = C.waterHi; ctx.fill(); ctx.lineWidth = 1; ctx.strokeStyle = OUT; ctx.stroke(); }
  }
  /** 破壞演出的特效。layer "air"（物件層、碎石之上）＝水柱、水花、水珠；"ground"（地面層、單位之下，接在新水面後）＝漣漪。k 1～3。 */
  function breakFx(ctx, s, k, layer = "air") {
    if ((layer === "ground") !== (k === 3)) return;
    const { cx } = G, r = rng(s.x ?? 0, s.y ?? 0, 243), cy = RUB_Y - 2;
    if (k === 1) { // 中央水柱（冠狀），四周水珠
      const pts = [[-12, 0], [-11, -6], [-8, -3], [-6, -14], [-3, -7], [0, -20], [3, -8], [6, -15], [8, -4], [11, -8], [12, 0]];
      ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(cx + x, cy + y) : ctx.moveTo(cx + x, cy + y))); ctx.ellipse(cx, cy, 12, 4, 0, 0, Math.PI, false); ctx.closePath();
      ctx.fillStyle = C.waterHi; ctx.fill(); ctx.lineWidth = 1.5; ctx.strokeStyle = OUT; ctx.lineJoin = "round"; ctx.stroke();
      ctx.fillStyle = "rgba(255,255,255,0.7)"; ctx.beginPath(); ctx.moveTo(cx - 4, cy - 2); ctx.lineTo(cx - 1, cy - 14); ctx.lineTo(cx + 1, cy - 2); ctx.closePath(); ctx.fill();
      const d = []; for (let i = 0; i < 9; i++) { const a = (i / 9) * TAU + r() * 0.4, q = 17 + r() * 8; d.push([cx + Math.cos(a) * q, cy + Math.sin(a) * q * 0.55 - 10 - r() * 6, 1.8 + r() * 0.8]); } drops(ctx, d);
    } else if (k === 2) { // 水花往外一圈、水珠落下
      for (let i = 0; i < 8; i++) {
        const a = (i / 8) * TAU + 0.2, x = cx + Math.cos(a) * 30, y = cy + Math.sin(a) * 17;
        ctx.beginPath(); ctx.moveTo(x - 4, y); ctx.quadraticCurveTo(x, y - 7 - r() * 3, x + 4, y); ctx.closePath(); ctx.fillStyle = C.waterHi; ctx.fill(); ctx.lineWidth = 1.2; ctx.strokeStyle = OUT; ctx.stroke();
      }
      const d = []; for (let i = 0; i < 7; i++) { const a = (i / 7) * TAU + r() * 0.5, q = 38 + r() * 8; d.push([cx + Math.cos(a) * q, cy + Math.sin(a) * q * 0.55 - 3, 1.5 + r() * 0.5]); } drops(ctx, d);
    } else if (k === 3) { // 漣漪
      ctx.save(); ctx.strokeStyle = "rgba(235,248,255,0.6)"; ctx.lineWidth = 1.6;
      for (const q of [44, 74]) { ctx.beginPath(); ctx.ellipse(cx, cy, q, q * 0.92, 0, 0, TAU); ctx.stroke(); } // 地面是俯視：漣漪近乎正圓
      ctx.restore();
    }
  }
  /** 水面遮罩（新的 3×3 水表面從井心往外長；邊緣微微不規則）。在 52 單位格座標建 path，呼叫端 clip。k 4 不用遮罩。 */
  function spillMask(ctx, k) {
    const R = MASK_R[Math.min(4, k)], cx = G.cx, cy = T / 2; ctx.beginPath(); // 從格子中心長（3×3 對稱）
    if (!Number.isFinite(R)) { ctx.rect(-T, -T, 3 * T, 3 * T); return; }
    if (R <= 0) { ctx.rect(0, 0, 0, 0); return; }
    for (let i = 0; i <= 32; i++) { const a = (i / 32) * TAU, q = R * (1 + 0.07 * Math.sin(a * 5 + 1.3) + 0.04 * Math.sin(a * 9)); const x = cx + Math.cos(a) * q, y = cy + Math.sin(a) * q; i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }
    ctx.closePath();
  }

  window.CoolingWell = { T, C, G, FRAMES, MASK_R, draw, rubble, breakFx, spillMask, spillMark, chunks };
})();
