// occludeOutline.js：被遮擋剪影外框（畫圖 agent，2026-11-12；使用者 11-12「做，現在排」）。
// 被前排（南邊、後畫的）單位擋住一定比例以上的單位，在「單位之上、特效之下」再畫一圈只有輪廓的陣營色外框；受擊時外框跟著閃白。
// 單位一律呼叫現行畫法：Q 版人物 QDoll.stamp（qDoll.js）、異形 QCreature.stamp（qCreature.js）、頭目 QBoss.stampField（qBoss.js）；
//   地面用 Regions4.tile（regions4.js）；特效用 QCreatureAnim.drawFx（qCreatureAnim.js）；狀態列用 QStatusLive（tools/qStatusLive.js，遊戲端原樣打包）。
// 遮擋比例＝「被擋單位的身體 alpha 遮罩」和「後畫的單位身體 alpha 遮罩的聯集」的交集像素數 ÷ 被擋單位身體像素數（alpha ≥ 0.5 才算）。
// 外框＝身體遮罩往內侵蝕 w 的那一圈（M − erode(M, w)，剛好落在 Q 版自己的黑外框上），預設只留被擋住的那一段（∩ 前排遮罩），上色、乘透明度。
// 確定性：不用 Math.random；排序照（排, 頭目先, 欄）。只讀別的畫法檔，不改它們。
window.OccludeOutline = (() => {
  const TAU = Math.PI * 2;
  // ---- 遊戲端常數（照抄；出處寫在右邊，改了要回頭對）----
  const T = 48; // client/src/battle/geometry.ts TILE_SIZE
  const K = (T / 52) * 1.06; // client/src/render/battle/rendererBase.ts DOLL_PX（paperdoll.ts DOLL_SCALE 1.06）
  const FEET = T * 0.23; // client/src/render/unitSprite.ts FEET
  const RAISE = 6; // client/src/battle/elevation.ts RAISE（每一階高度抬高的模型像素）
  /** 陣營底圈（client/src/render/artPalette.ts RING）：填色／外框。現有的遮擋剪影（heightArt.ts silhouette）用的是 stroke。 */
  const RING = {
    ally: { fill: "#2f6fd0", stroke: "#a9ccff" },
    enemy: { fill: "#c63b3b", stroke: "#ffb3a8" },
    third: { fill: "#8e44c9", stroke: "#dcb3ff" },
    summon: { fill: "#1f9e8f", stroke: "#8ff0e2" },
  };
  /** 陣營色（client/src/battle/glossary.ts TEAM_COLORS；drawModel 的單位底色）。 */
  const TEAM = { ally: "#2f7de1", enemy: "#d23c3c", third: "#9b4fd6", summon: "#1f9e8f" };
  const CLIFF_TOP = "#6b5236", CLIFF_BOTTOM = "#4a3824"; // client/src/render/heightShapes.ts
  const RIM = "rgba(255,248,215,0.8)"; // heightShapes.ts RIM（崖頂亮唇）
  const ACTIVE = "#ffe14d"; // battle/glossary.ts HIGHLIGHT.active（輪到誰的黃色虛線圈）
  const ELITE_INK = "#16121a", ELITE_GOLD = "#ffbf3a"; // unitSprite.ts eliteRing（同 qCreature ring）
  const hpColor = (r) => (r > 0.5 ? "#4cd964" : r > 0.25 ? "#ffcc00" : "#ff3b30"); // unitSprite.ts hpColor
  const BOSS_RING = { ah: 40, sl: 26 }; // unitSprite.ts BOSS_RING_UNITS
  const HUGE = 1.6; // qCreature SIZES.huge（頭目戰場倍率）

  /** 預設值（選定值；理由見 docs/art/被遮擋剪影外框.md）。第 3 版：bigFront＝只有身體面積 ≥ 4000 模型 px²（alpha ≥ 0.5）的「大型前排」參與遮擋（比例、前排遮罩、外框裁切都只用它們；現在等於只有頭目）。第 2 版：門檻 0.55 開始畫、降到 release 0.45 以下才拿掉（opt.was[id]＝上一次有畫）；透明度 0.8。
   *  遮擋比例一律在模型像素（1 格 48）算，不隨地圖縮放、畫面放大、裝置像素變。 */
  const DEF = { threshold: 0.55, release: 0.45, bigFront: 4000, width: 1.5, alpha: 0.8, tone: "stroke", clip: "hidden", ink: 0.75, inkAlpha: 1 };
  /** 各片段的受擊白閃峰值（外框閃白 k ＝ 當下白閃 ÷ 這個片段的峰值；不寫死人形的 0.85）。出處：
   *  人形受擊 client/src/render/motionClips.ts humanHit（0.85 → 0，90 ms 歸零）；人形重擊 reactClips.ts hit(heavy)（0.95 → 0，120 ms）；
   *  異形受擊 qCreatureAnim.ts hitCommon、creaturePose.ts hit（前 20% 固定 0.9，400 ms 片段＝80 ms）；異形重擊 reactClips.ts creatureReact heavy（×1.1，0.99）；
   *  頭目受擊 qBoss.ts bossPlan（前 20% 固定 0.9）。召喚物照它的身體走人形或異形那一列。 */
  const PEAK = { humanHit: 0.85, humanHeavy: 0.95, creatureHit: 0.9, creatureHeavy: 0.99, bossHit: 0.9 };

  const mk = (w, h) => { const c = document.createElement("canvas"); c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h)); return c; };
  const hex = (h) => { const n = parseInt(h.slice(1, 7), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
  const mix = (a, b, t) => { const A = hex(a), B = hex(b); return "#" + A.map((v, i) => Math.round(v + (B[i] - v) * t).toString(16).padStart(2, "0")).join(""); };
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));

  /** ctx 的代理：前 n 次「直接上色」（fill、stroke、fillRect）不畫，之後照常。用來拿掉樣張端異形、頭目自己畫的紅色地面環（ring 固定是最先畫的 2 筆；精英／頭目 7 筆），
   *  改畫遊戲端的陣營環。n＝Infinity：只留用 drawImage 貼上的身體圖層（QCreature.layer），地面環、影子、平塗光暈都不畫（身體遮罩用）。 */
  function skipPaint(ctx, n) {
    let left = n;
    const PAINT = new Set(["fill", "stroke", "fillRect", "strokeRect", "fillText", "strokeText"]);
    return new Proxy(ctx, {
      get(t, p) {
        if (PAINT.has(p)) return (...a) => { if (left > 0) { left -= 1; return undefined; } return t[p](...a); };
        const v = Reflect.get(t, p);
        return typeof v === "function" ? v.bind(t) : v;
      },
      set(t, p, v) { t[p] = v; return true; },
    });
  }

  // ---- 單位 ----
  // u = { id, kind: "doll"|"creature"|"boss", team, x, y（格）, h（高度階）, dx, dy（模型像素位移，受擊後彈）,
  //       doll（PaperDoll 範本）, view, west, scale（人形外觀大小）, spec（異形）, who／clip／t／st（頭目）,
  //       hp, marker, status:[id], flash（白閃 0～1）, active, hero }
  const feetOf = (u) => ({ x: (u.x + 0.5) * T + (u.dx ?? 0), y: (u.y + 0.5) * T + FEET - RAISE * (u.h ?? 0) + (u.dy ?? 0) });
  const centerOf = (u) => ({ x: (u.x + 0.5) * T, y: (u.y + 0.5) * T - RAISE * (u.h ?? 0) });
  const isElite = (u) => u.kind === "boss" || (u.kind === "creature" && (u.spec.elite || !!u.spec.glow));
  /** 環的半徑（照 unitSprite.ts：一般 T×0.36、T×0.15；頭目照 qBoss ring(40／26) × 1.6 × 戰場倍率、扁度 0.3）。 */
  function ringSize(u) {
    if (u.kind === "boss") { const rx = BOSS_RING[u.who] * HUGE * K; return { rx, ry: rx * 0.3, lk: HUGE }; }
    return { rx: T * 0.36, ry: T * 0.15, lk: 1 };
  }
  /** 腳下的陣營環（unitSprite.ts buildUnitSprite：填色 80%、外框 1.5；精英金環、金菱形照 eliteRing／bossRingFront；hero 白圈；active 黃虛線）。 */
  function drawRing(ctx, u) {
    const f = feetOf(u), { rx, ry, lk } = ringSize(u), ring = RING[u.team] ?? RING.enemy, cy = f.y - (u.dy ?? 0);
    ctx.save(); ctx.translate((u.x + 0.5) * T, cy);
    ctx.beginPath(); ctx.ellipse(0, 0, rx, ry, 0, 0, TAU); ctx.globalAlpha = 0.8; ctx.fillStyle = ring.fill; ctx.fill();
    ctx.globalAlpha = 1; ctx.lineWidth = 1.5 * lk; ctx.strokeStyle = ring.stroke; ctx.stroke();
    if (u.hero) { ctx.beginPath(); ctx.ellipse(0, 0, rx + 2.5, ry + 2, 0, 0, TAU); ctx.lineWidth = 2; ctx.strokeStyle = "#ffffff"; ctx.stroke(); }
    if (isElite(u)) {
      const s = ((T * 0.36) / 13) * lk, gx = rx + 2.2 * s, gy = ry * (gx / rx);
      ctx.beginPath(); ctx.ellipse(0, 0, gx, gy, 0, 0, TAU); ctx.lineWidth = 2.4 * s; ctx.strokeStyle = ELITE_INK; ctx.stroke(); ctx.lineWidth = 1.2 * s; ctx.strokeStyle = ELITE_GOLD; ctx.stroke();
      const top = gy - 0.4 * s; ctx.beginPath(); ctx.moveTo(0, top); ctx.lineTo(2.6 * s, top + 2.6 * s); ctx.lineTo(0, top + 5.2 * s); ctx.lineTo(-2.6 * s, top + 2.6 * s); ctx.closePath();
      ctx.lineJoin = "round"; ctx.lineWidth = 1.6 * s; ctx.strokeStyle = ELITE_INK; ctx.stroke(); ctx.fillStyle = ELITE_GOLD; ctx.fill();
    }
    if (u.active) { // dashedEllipse(cy, rx + 6, ry + 4, HIGHLIGHT.active)：28 段取一半
      ctx.strokeStyle = ACTIVE; ctx.lineWidth = 2.5; const n = 28, ex = rx + 6, ey = ry + 4;
      for (let i = 0; i < n; i += 2) { const a0 = (i / n) * TAU, a1 = ((i + 1) / n) * TAU; ctx.beginPath(); ctx.moveTo(Math.cos(a0) * ex, Math.sin(a0) * ey); ctx.lineTo(Math.cos(a1) * ex, Math.sin(a1) * ey); ctx.stroke(); }
    }
    ctx.restore();
  }
  /** 身體（含影子）。body＝true：只要身體（遮罩用，不含影子、光暈）。dpr＝目前裝置像素／模型像素。 */
  function drawBody(ctx, u, dpr, body = false) {
    const f = feetOf(u);
    if (u.kind === "doll") { QDoll.stamp(ctx, u.doll, u.view ?? "front", f.x, f.y, K * (u.scale ?? 1), !!u.west, { dpr: Math.max(1, dpr) }); return; }
    if (u.kind === "creature") { QCreature.stamp(body ? skipPaint(ctx, Infinity) : skipPaint(ctx, isElite(u) ? 7 : 2), u.spec, f.x, f.y, K, !!u.west); return; }
    const g = body ? skipPaint(ctx, Infinity) : skipPaint(ctx, 7);
    if (u.st) { g.save(); g.translate(f.x, f.y); g.scale((u.west ? -1 : 1) * K * HUGE, K * HUGE); (u.who === "ah" ? QBoss.drawAshenHeart : QBoss.drawShardLord)(g, u.st); g.restore(); }
    else QBoss.stampField(g, u.who, u.clip ?? "idle", u.t ?? 0, f.x, f.y, K, !!u.west);
  }
  /** 人形的代號小圓（unitSprite.ts：(-0.37T, 0.22T) 半徑 8、黑 78%、陣營外框 1.5、白字 12 粗）：跟著單位畫。 */
  function drawMarker(ctx, u) {
    if (!u.marker) return;
    const c = centerOf(u), ring = RING[u.team] ?? RING.enemy, x = c.x - T * 0.37, y = c.y + T * 0.22;
    ctx.save(); ctx.beginPath(); ctx.arc(x, y, 8, 0, TAU); ctx.globalAlpha = 0.78; ctx.fillStyle = "#000"; ctx.fill(); ctx.globalAlpha = 1; ctx.lineWidth = 1.5; ctx.strokeStyle = ring.stroke; ctx.stroke();
    ctx.fillStyle = "#fff"; ctx.font = "bold 12px 'Noto Sans TC','Microsoft JhengHei',sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(u.marker, x, y + 0.5); ctx.restore();
  }
  /** HP 條＋狀態列（畫在這一排的單位之後、南邊一排之前：rowLayers.ts RowLayer.marks）。頭目整組 HUD 搬到剪影上方（bossHudDy）：這裡用身體遮罩的頂端 − 8。 */
  function drawHud(ctx, u, top) {
    const c = centerOf(u), w = T * 0.8;
    let y = c.y + T * 0.36;
    if (u.kind === "boss" && top !== null) y = top - 8;
    if (u.hp !== undefined) {
      ctx.fillStyle = "#000"; ctx.fillRect(c.x - w / 2, y, w, 5);
      ctx.fillStyle = hpColor(u.hp); ctx.fillRect(c.x - w / 2, y, w * u.hp, 5);
    }
    if (u.status?.length && window.QStatusLive) { // 狀態列：圖示 11，下緣離 HP 條 4（unitSprite.ts ROW_Y_FEET），置中排
      const n = Math.min(3, u.status.length), px = 11, gap = 1, x0 = c.x - (n * px + (n - 1) * gap) / 2, yb = y - 4;
      u.status.slice(0, 3).forEach((id, i) => { const cv = statusIcon(id); if (cv) ctx.drawImage(cv, x0 + i * (px + gap), yb - px, px, px); });
    }
  }
  const STATUS = new Map();
  function statusIcon(id) {
    if (!STATUS.has(id)) { let cv = null; try { cv = window.QStatusLive.statusIconCanvas(id, 11); } catch (e) { cv = null; } STATUS.set(id, cv); }
    return STATUS.get(id);
  }

  // ---- 遮罩運算（裝置像素）----
  /** 圓盤膨脹（Minkowski 和）：把 src 在半徑 r（裝置像素）內每 0.5 像素各貼一次。 */
  function dilate(src, r) {
    const c = mk(src.width, src.height), x = c.getContext("2d");
    if (r <= 0) { x.drawImage(src, 0, 0); return c; }
    const st = 0.5;
    for (let dy = -r; dy <= r + 1e-6; dy += st) for (let dx = -r; dx <= r + 1e-6; dx += st) if (dx * dx + dy * dy <= r * r + 1e-6) x.drawImage(src, dx, dy);
    return c;
  }
  const alphaOf = (cv) => cv.getContext("2d", { willReadFrequently: true }).getImageData(0, 0, cv.width, cv.height).data;
  /** 遮擋比例：|M ∩ O| ÷ |M|（alpha ≥ 128 才算一個像素）。 */
  function coverRatio(M, O) {
    const a = alphaOf(M), b = O ? alphaOf(O) : null;
    let n = 0, hit = 0;
    for (let i = 3; i < a.length; i += 4) if (a[i] >= 128) { n += 1; if (b && b[i] >= 128) hit += 1; }
    return { n, hit, ratio: n ? hit / n : 0 };
  }
  /** 遮罩的上緣（裝置像素 y；沒有像素 → null）。 */
  function topOf(M) {
    const a = alphaOf(M), w = M.width;
    for (let i = 3; i < a.length; i += 4) if (a[i] >= 128) return Math.floor((i - 3) / 4 / w);
    return null;
  }
  /** 一圈色帶：從輪廓往外 a、往內 b（dilate(M, a) ∩ dilate(反 M, b)）；clip＝"hidden" 時再 ∩ O；上色。a＝0、b＝w 就是 M − erode(M, w)。 */
  function band(M, O, a, b, color, clip) {
    const W = M.width, H = M.height;
    const inv = mk(W, H), ic = inv.getContext("2d"); ic.fillStyle = "#000"; ic.fillRect(0, 0, W, H); ic.globalCompositeOperation = "destination-out"; ic.drawImage(M, 0, 0);
    const ring = dilate(inv, b), rc = ring.getContext("2d");
    rc.globalCompositeOperation = "destination-in"; rc.drawImage(a > 0 ? dilate(M, a) : M, 0, 0);
    if (clip === "hidden" && O) rc.drawImage(a > 0 ? dilate(O, a) : O, 0, 0);
    rc.globalCompositeOperation = "source-in"; rc.fillStyle = color; rc.fillRect(0, 0, W, H);
    return ring;
  }
  const outline = (M, O, w, color, clip) => band(M, O, 0, w, color, clip);
  /** 虛線（第 2 版的提案試做，預設不用）：以身體遮罩外接框中心為圓心切成等角度的扇形（弧長以 0.7 × 半對角線算），落在 gap 扇形的就挖掉。
   *  橫向走的輪廓約 dash 實、gap 空（裝置像素），和 6F-22 舊剪影的 setLineDash([3, 2]) 同一種語言；沿半徑方向走的一段會整段實線（試做的近似）。 */
  function dashMask(lay, M, dash, gap) {
    const a = alphaOf(M), W = M.width, H = M.height;
    let x0 = W, y0 = H, x1 = 0, y1 = 0;
    for (let i = 3; i < a.length; i += 4) if (a[i] >= 128) { const p = (i - 3) / 4, x = p % W, y = (p - x) / W; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, R = Math.max(1, Math.hypot(x1 - x0, y1 - y0) / 2), per = dash + gap, lc = lay.getContext("2d"), img = lc.getImageData(0, 0, W, H), d = img.data;
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const i = (y * W + x) * 4; if (!d[i + 3]) continue;
      const s = (Math.atan2(y + 0.5 - cy, x + 0.5 - cx) + Math.PI) * R * 0.7;
      if (s % per >= dash) d[i + 3] = 0;
    }
    lc.putImageData(img, 0, 0);
  }
  /** 白色剪影（silhouetteFlash.ts whiteCanvas：RGB 變白、alpha 不變）。 */
  function white(src) { const c = mk(src.width, src.height), x = c.getContext("2d"); x.drawImage(src, 0, 0); x.globalCompositeOperation = "source-in"; x.fillStyle = "#fff"; x.fillRect(0, 0, c.width, c.height); return c; }

  /** 畫的順序：由北到南一排一排；同一排頭目先（unitLayer.ts addChildAt 0），其餘由西到東。 */
  function order(units) {
    return [...units].sort((a, b) => a.y - b.y || (b.kind === "boss") - (a.kind === "boss") || a.x - b.x);
  }

  /** 舊的遮擋剪影（6F-22，heightArt.ts silhouette＋heightShapes.ts silhouetteLoops）：身體橢圓＋頭圓、2px 虛線 3/2、0.9、陣營 stroke 色（撞圖對照用）。 */
  function legacySilhouette(ctx, u) {
    const c = centerOf(u), fx = c.x, fy = c.y + T * 0.23, k = T / 48, ring = RING[u.team] ?? RING.enemy;
    ctx.save(); ctx.strokeStyle = ring.stroke; ctx.globalAlpha = 0.9; ctx.lineWidth = 2; ctx.setLineDash([3, 2]);
    ctx.beginPath(); ctx.ellipse(fx, fy - 13 * k, 10 * k, 13 * k, 0, 0, TAU); ctx.stroke();
    ctx.beginPath(); ctx.ellipse(fx, fy - 32 * k, 7 * k, 7 * k, 0, 0, TAU); ctx.stroke(); ctx.restore();
  }

  /**
   * 畫一個場景。scene＝{ cols, rows, ground(ctx, x, y, gx, gy)（一格地面，模型像素）, heights?[row][col], units, fx?(ctx), legacy?: [id], hover?: {x,y} }
   * view＝{ S（遊戲的地圖縮放：CSS px／模型 px）, zoom（另外放大給人看，向量重畫）, res（裝置像素／CSS px）, x0, y0, w, h（裁切，模型像素） }
   * opt＝外框參數（DEF 的欄位；outline:false 不畫外框；only:[id] 只給這些人畫；flash: {id: k} 外框閃白，k＝白閃 ÷ 該片段峰值 PEAK；
   *      was: {id: true} 上一次有畫（遲滯，用 release）；legacyAlways: 6F-22 舊剪影照畫）。單位 concealed:true（隱匿／資訊被隱藏）不畫外框。
   * 回傳 { canvas, stats: [{ id, ratio（大型前排）, raw（所有前排）, drawn, area（身體面積，模型 px²）}] }。外框線寬是「遊戲縮放下的螢幕 px」，跟著 zoom、res 放大。
   */
  function render(scene, view, opt = {}) {
    const o = { ...DEF, ...opt }, sc = view.S * (view.zoom ?? 1) * (view.res ?? 1);
    const W = Math.round(view.w * sc), H = Math.round(view.h * sc);
    const main = mk(W, H), g = main.getContext("2d");
    const xf = (c) => c.setTransform(sc, 0, 0, sc, -view.x0 * sc, -view.y0 * sc);
    xf(g);
    // 地面（含高度：頂面抬高 6／階、南邊較低時畫崖面；由北到南）
    const hts = scene.heights;
    const hAt = (x, y) => (hts && hts[y] && hts[y][x]) || 0;
    for (let y = 0; y < scene.rows; y++) for (let x = 0; x < scene.cols; x++) {
      const h = hAt(x, y), lift = h * RAISE;
      if (lift > 0) { const cg = g.createLinearGradient(0, (y + 1) * T - lift, 0, (y + 1) * T); cg.addColorStop(0, CLIFF_TOP); cg.addColorStop(1, CLIFF_BOTTOM); g.fillStyle = cg; g.fillRect(x * T, (y + 1) * T - lift, T, lift); }
      g.save(); g.beginPath(); g.rect(x * T, y * T - lift, T, T); g.clip(); scene.ground(g, x * T, y * T - lift, x, y); g.restore();
      if (lift > 0) { g.fillStyle = RIM; g.fillRect(x * T, (y + 1) * T - lift - 2, T, 2); }
    }
    if (scene.grid !== false) { g.save(); g.strokeStyle = "rgba(0,0,0,0.22)"; g.lineWidth = 1 / sc; for (let y = 0; y <= scene.rows; y++) { g.beginPath(); g.moveTo(0, y * T); g.lineTo(scene.cols * T, y * T); g.stroke(); } for (let x = 0; x <= scene.cols; x++) { g.beginPath(); g.moveTo(x * T, 0); g.lineTo(x * T, scene.rows * T); g.stroke(); } g.restore(); }
    // 每個單位：整張圖 F（貼到畫面）與身體遮罩 M（算比例、畫外框）
    // Mm：同一個身體遮罩在「模型像素」（1 格 48、不隨地圖縮放與放大）再畫一份，只用來算遮擋比例（第 2 版；第 1 版用畫面像素算，會隨解析度跳幾 %）
    //   原點對齊整數模型像素（floor），同一對單位放在哪一格、畫面怎麼裁，量出來都一樣
    const mx0 = Math.floor(view.x0), my0 = Math.floor(view.y0), MW = Math.ceil(view.x0 + view.w) - mx0, MH = Math.ceil(view.y0 + view.h) - my0;
    const list = order(scene.units).map((u) => {
      const F = mk(W, H), fc = F.getContext("2d"); xf(fc); drawBody(fc, u, sc, false);
      const M = mk(W, H), mc = M.getContext("2d"); xf(mc); drawBody(mc, u, sc, true);
      const Mm = mk(MW, MH), mm = Mm.getContext("2d"); mm.setTransform(1, 0, 0, 1, -mx0, -my0); drawBody(mm, u, 1, true);
      return { u, F, M, Mm, area: coverRatio(Mm, null).n };
    });
    // 遮擋比例與畫不畫（先算好：6F-22 舊剪影要看同一個單位有沒有新外框）
    const plan = list.map((e, k) => {
      const all = list.slice(k + 1), later = all.filter((l) => l.area >= (o.bigFront ?? 0)); // 只算大型前排
      let O = null, Om = null, raw = 0;
      if (all.length) { const Ra = mk(MW, MH), ra = Ra.getContext("2d"); for (const l of all) ra.drawImage(l.Mm, 0, 0); raw = coverRatio(e.Mm, Ra).ratio; } // 對照：所有前排都算時的比例
      if (later.length) {
        O = mk(W, H); Om = mk(MW, MH); const oc = O.getContext("2d"), om = Om.getContext("2d");
        for (const l of later) om.drawImage(l.Mm, 0, 0);
        // 外框裁切用的 O：照畫的順序疊，大型前排加進來、畫在它之後的小兵挖掉 → 只留「最上面是大型前排」的像素，外框不會落在小兵身上
        for (const l of all) { oc.globalCompositeOperation = l.area >= (o.bigFront ?? 0) ? "source-over" : "destination-out"; oc.drawImage(l.M, 0, 0); }
        oc.globalCompositeOperation = "source-over";
      }
      const r = coverRatio(e.Mm, Om);
      const want = o.outline !== false && (!o.only || o.only.includes(e.u.id)) && e.u.outline !== false && !e.u.concealed;
      const thr = (o.was ?? {})[e.u.id] ? o.release : o.threshold; // 遲滯：上一次有畫 → 降到 release 以下才拿掉
      return { ...e, O, ratio: r.ratio, raw, drawn: want && O !== null && r.ratio >= thr };
    });
    // 由北到南：環 → 身體（＋白閃）→ 代號；一排畫完畫那一排的 HUD
    let i = 0;
    while (i < list.length) {
      const row = list[i].u.y;
      const inRow = [];
      for (; i < list.length && list[i].u.y === row; i++) inRow.push(list[i]);
      for (const e of inRow) {
        xf(g); drawRing(g, e.u);
        g.setTransform(1, 0, 0, 1, 0, 0); g.drawImage(e.F, 0, 0);
        if (e.u.flash > 0) { g.globalAlpha = clamp(e.u.flash); g.drawImage(white(e.M), 0, 0); g.globalAlpha = 1; }
        xf(g); drawMarker(g, e.u);
      }
      for (const e of inRow) { xf(g); const t = e.u.kind === "boss" ? topOf(e.M) : null; drawHud(g, e.u, t === null ? null : t / sc + view.y0); }
    }
    // 舊的遮擋剪影（6F-22）：第 2 版起同一個單位有新外框時不畫（opt.legacyAlways＝第 1 版的「兩個都畫」對照）
    xf(g);
    for (const e of plan) if ((scene.legacy ?? []).includes(e.u.id) && (o.legacyAlways || !e.drawn)) legacySilhouette(g, e.u);
    // 外框圖層：單位之上、特效之下
    const stats = [];
    plan.forEach((e) => {
      const { O, drawn } = e;
      stats.push({ id: e.u.id, ratio: e.ratio, raw: e.raw, drawn, area: e.area });
      if (!drawn) return;
      const base = o.color ?? (o.tone === "fill" ? (RING[e.u.team] ?? RING.enemy).fill : o.tone === "team" ? TEAM[e.u.team] ?? TEAM.enemy : (RING[e.u.team] ?? RING.enemy).stroke);
      const fl = clamp((o.flash ?? {})[e.u.id] ?? 0);
      const col = fl > 0 ? mix(base, "#ffffff", fl) : base, al = o.alpha + (1 - o.alpha) * fl;
      const wd = o.width * (view.zoom ?? 1) * (view.res ?? 1);
      g.setTransform(1, 0, 0, 1, 0, 0);
      // 先在離屏疊好（不透明），整層再乘透明度貼上：襯邊不會讓色線變暗
      const lay = mk(W, H), lc = lay.getContext("2d");
      if (o.ink > 0) { // 襯黑邊：色線兩側各 ink px 的深色（#16121a，同 Q 版外框色），畫在色線底下
        const ik = o.ink * (view.zoom ?? 1) * (view.res ?? 1);
        lc.globalAlpha = o.inkAlpha ?? 1; lc.drawImage(band(e.M, O, ik, wd + ik, "#16121a", o.clip), 0, 0); lc.globalAlpha = 1;
      }
      lc.drawImage(outline(e.M, O, wd, col, o.clip), 0, 0);
      if (o.dash > 0) dashMask(lay, e.M, o.dash * (view.zoom ?? 1) * (view.res ?? 1), (o.gap ?? o.dash) * (view.zoom ?? 1) * (view.res ?? 1));
      g.globalAlpha = al; g.drawImage(lay, 0, 0); g.globalAlpha = 1;
    });
    // 特效圖層
    if (scene.fx) { xf(g); scene.fx(g); }
    if (scene.hover) { xf(g); g.strokeStyle = "rgba(255,255,255,0.9)"; g.lineWidth = 2; g.strokeRect(scene.hover.x * T + 1, scene.hover.y * T + 1, T - 2, T - 2); }
    g.setTransform(1, 0, 0, 1, 0, 0);
    return { canvas: main, stats };
  }

  return { render, order, coverRatio, outline, dilate, drawRing, drawBody, feetOf, centerOf, legacySilhouette, white, mix, DEF, PEAK, RING, TEAM, T, K, FEET, RAISE, HUGE };
})();
