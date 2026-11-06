// 紙娃娃「大改畫風」樣張：同一個角色（人類、短褐髮、綠皮甲、紅披風、劍＋圓盾、皮靴），四種畫風。
// 每種畫風都有 front(ctx)、side(ctx)：腳底在 (0,0)，往上是 -y；側面一律朝東（+x）。
// 這只是看畫風的樣張，不含裝備組合規則；採用後再把現有的「資料欄位 → 外觀」規則套到新畫法上。
window.Restyle = (() => {
  const C = {
    skin: "#eab48a", skinD: "#c4825c", hair: "#6a3a1e", hairD: "#3e2010",
    tunic: "#4f7a3a", tunicL: "#76a752", tunicD: "#35562a",
    belt: "#6b4426", gold: "#e8bb48", goldD: "#9c7420",
    cape: "#a83030", capeD: "#701c22", pants: "#3c3c52", pantsD: "#26263a",
    boot: "#6a4224", bootD: "#42281a", steel: "#dfe6ee", steelD: "#8e9aa8",
    shield: "#2f5fae", shieldD: "#1e3c80", iron: "#7a828b", ironD: "#4e555c", wood: "#8a5a30",
  };

  // ───────────────────────── A. 像素風（16-bit）─────────────────────────
  // 每張圖是 22×30 的像素格，整數倍放大、不做平滑。
  const PX = {
    ".": null, k: "#1a1420", s: "#f0b890", S: "#c8865e", h: "#7a4422", H: "#4a2412", e: "#1a1420", w: "#ffffff",
    g: "#5c9a3c", G: "#3a6a28", l: "#8cc456", b: "#6b4426", y: "#f0c040", Y: "#a87a20",
    r: "#c03434", R: "#7a1c22", p: "#45456a", P: "#2a2a42", o: "#7a4a26", O: "#4a2a16",
    m: "#e8eef6", M: "#98a6b6", u: "#3a6cc8", U: "#22448c", i: "#8a929c", I: "#565e68",
  };
  function mirrorRows(half) { return half.map((r) => r + [...r].reverse().join("")); }
  const A_BODY = mirrorRows([
    "..........",
    ".......kkk",
    ".....kkhhh",
    "....khhhhh",
    "...khhhhhh",
    "...khhhhhh",
    "..khhhhhHh",
    "..khhHhhhh",
    "..khhshhss",
    "..khssssss",
    "..kHsskkss",
    "..kssskwss",
    "..kSssssss",
    "...kSsssss",
    "....kkkkkk",
    "...kkgggll",
    "..kRkgglgg",
    "..kRgkgggg",
    "..kRgkgggg",
    "..kRgkgggG",
    "..kRskbbby",
    "..kRkkGggg",
    "..kRRkGggg",
    "..kRRkkkkk",
    "..kRRRkppk",
    "...kRRkppk",
    "...kkkkPPk",
    "....kooook",
    "....kOOOOk",
    ".....kkkkk",
  ]);
  const A_SWORD = [
    // [x, y, 列]：以 22×30 格為準
    [1, 2, "..k.."], [1, 3, ".kmk."], [1, 4, ".kmk."], [1, 5, ".kmk."], [1, 6, ".kmM."], [1, 7, ".kmMk"],
    [1, 8, ".kmMk"], [1, 9, ".kmMk"], [1, 10, ".kmMk"], [1, 11, ".kmMk"], [1, 12, ".kmMk"], [1, 13, ".kmMk"],
    [0, 14, "kyyyyk"], [0, 15, ".kYYk."], [1, 16, ".kbk"], [1, 17, ".kbk"], [1, 18, ".kbk"], [1, 19, ".kyk"], [1, 20, "..k."],
  ];
  const A_SHIELD = [
    "...kkkkk...",
    "..kiiiiik..",
    ".kiuuuuuik.",
    "kiuuuuuuUik",
    "kiuuuyuuUik",
    "kiuuyyyuUik",
    "kiuuuyuuUik",
    "kiuuuuuUUik",
    ".kiUUUUUik.",
    "..kiiiiIk..",
    "...kkkkk...",
  ];
  const A_SIDE = [
    "......................",
    "........kkkkkk........",
    "......kkhhhhhhkk......",
    ".....khhhhhhhhhhk.....",
    "....khhhhhhhhhhhhk....",
    "...khhhhhhhhhhhhhhk...",
    "...khhhhhhhhhhhhHhhk..",
    "...khhhhhhhhhhhhhhhk..",
    "...khhhhhhhhssssssssk.",
    "...khhhhhhhsssssskssk.",
    "...khhhhhhhssssssksssk",
    "...kHhhhhhhSssssssssk.",
    "....kHhhhhhSsssssssk..",
    ".....kHHhhhkSsssskk...",
    "......kkkkkkkkkkk.....",
    "......kRRkgggglgk.....",
    ".....kRRkggglgggk.....",
    ".....kRRkgggggggk.....",
    "....kRRRkgggggggk.....",
    "....kRRRkGgggggGk.....",
    "....kRRRkbbbbbbbk.....",
    "...kRRRRkGggggGGk.....",
    "...kRRRRRkkkkkkk......",
    "...kRRRRRkpppPk.......",
    "...kRRRRkppkppk.......",
    "....kRRRkpPkpPk.......",
    ".....kkkkkokkook......",
    "........koookoooook...",
    "........kOOOkkOOOOk...",
    ".........kkk..kkkkk...",
  ];
  // 遠側手的盾（側看是一條邊）→ 近側手臂 → 劍平舉朝前
  const A_SIDE_OVER = [
    [16, 13, ".kk"], [16, 14, "kiik"], [16, 15, "kiuk"], [16, 16, "kiuk"], [16, 17, "kiuk"], [16, 18, "kiUk"], [16, 19, "kiUk"],
    [16, 20, "kiUk"], [16, 21, "kiik"], [17, 22, "kk"],
    [10, 15, "kggk"], [11, 16, "kggk"], [12, 17, "kgssk"], [12, 18, "kkssk"],
    [16, 15, "k"], [16, 16, "ykkkk"], [16, 17, "ymmmmk"], [16, 18, "yMMMMk"], [16, 19, "ykkkk"], [16, 20, "k"],
  ];
  function pxPut(g, x, y, row) {
    for (let i = 0; i < row.length; i++) {
      const col = PX[row[i]];
      if (col) { g.fillStyle = col; g.fillRect(x + i, y, 1, 1); }
    }
  }
  function pxSprite(paint) {
    const c = document.createElement("canvas"); c.width = 22; c.height = 30;
    paint(c.getContext("2d")); return c;
  }
  function pxDraw(ctx, sprite) {
    ctx.imageSmoothingEnabled = false;
    // 22×30 像素 → 每像素 2 單位，腳底對齊 (0,0)
    ctx.drawImage(sprite, -22, -60, 44, 60);
    ctx.imageSmoothingEnabled = true;
  }
  const A_FRONT_SPRITE = pxSprite((g) => {
    A_BODY.forEach((r, y) => pxPut(g, 1, y, r));
    for (const [x, y, r] of A_SWORD) pxPut(g, x, y, r);
    A_SHIELD.forEach((r, y) => pxPut(g, 11, 14 + y, r));
  });
  const A_SIDE_SPRITE = pxSprite((g) => {
    A_SIDE.forEach((r, y) => pxPut(g, 0, y, r));
    for (const [x, y, r] of A_SIDE_OVER) pxPut(g, x, y, r);
  });
  const pixel = {
    front(ctx) { pxDraw(ctx, A_FRONT_SPRITE); },
    side(ctx) { pxDraw(ctx, A_SIDE_SPRITE); },
  };

  // ───────────────────────── 共用小工具 ─────────────────────────
  function ell(ctx, x, y, rx, ry, rot = 0) { ctx.beginPath(); ctx.ellipse(x, y, rx, ry, rot, 0, Math.PI * 2); }
  function poly(ctx, pts) { ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); }
  function lin(ctx, x0, y0, x1, y1, a, b) { const g = ctx.createLinearGradient(x0, y0, x1, y1); g.addColorStop(0, a); g.addColorStop(1, b); return g; }
  function rad(ctx, x, y, r, a, b, fx = -0.35, fy = -0.4) {
    const g = ctx.createRadialGradient(x + r * fx, y + r * fy, r * 0.05, x, y, r * 1.05);
    g.addColorStop(0, a); g.addColorStop(1, b); return g;
  }

  // ───────────────────────── B. 高頭身寫實（戰棋立繪風）─────────────────────────
  // 約 6 頭身、細的同色系描邊、左上光的柔和漸層，沒有粗黑外框。
  function bPaint(ctx, fillStyle, line, w = 0.6) {
    ctx.fillStyle = fillStyle; ctx.fill();
    ctx.strokeStyle = line; ctx.lineWidth = w; ctx.lineJoin = "round"; ctx.stroke();
  }
  function bLimb(ctx, x0, y0, x1, y1, w, a, b) {
    ctx.save(); ctx.lineCap = "round";
    ctx.strokeStyle = b; ctx.lineWidth = w + 1.1; ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
    ctx.strokeStyle = a; ctx.lineWidth = w; ctx.stroke(); ctx.restore();
  }
  function bShadow(ctx, rx = 9) { ell(ctx, 0, 0, rx, 2.4); ctx.fillStyle = "rgba(0,0,0,0.28)"; ctx.fill(); }
  const tall = {
    front(ctx) {
      bShadow(ctx);
      // 披風（身後）
      poly(ctx, [[-7.5, -50], [7.5, -50], [11, -10], [6, -8.5], [0, -10], [-6, -8.5], [-11, -10]]);
      bPaint(ctx, lin(ctx, -11, 0, 11, 0, C.cape, C.capeD), C.capeD);
      // 腿＋靴
      for (const sx of [-1, 1]) {
        poly(ctx, [[sx * 0.6, -28], [sx * 4.4, -28], [sx * 4.0, -9], [sx * 0.9, -9]]);
        bPaint(ctx, lin(ctx, -5, 0, 5, 0, C.pants, C.pantsD), C.pantsD);
        poly(ctx, [[sx * 0.7, -10], [sx * 4.3, -10], [sx * 4.6, -1.5], [sx * 5.4, 0], [sx * 0.4, 0]]);
        bPaint(ctx, lin(ctx, 0, -10, 0, 0, C.boot, C.bootD), C.bootD);
      }
      // 身體＋皮甲下擺
      poly(ctx, [[-6.8, -50], [6.8, -50], [5.2, -37], [6.8, -26], [0, -24.5], [-6.8, -26], [-5.2, -37]]);
      bPaint(ctx, lin(ctx, -7, -50, 7, -26, C.tunicL, C.tunicD), C.tunicD);
      ctx.strokeStyle = C.tunicD; ctx.lineWidth = 0.5; ctx.beginPath(); ctx.moveTo(0, -47); ctx.lineTo(0, -37); ctx.moveTo(-3.6, -44); ctx.lineTo(-2, -38); ctx.moveTo(3.6, -44); ctx.lineTo(2, -38); ctx.stroke();
      poly(ctx, [[-5.4, -37.5], [5.4, -37.5], [5.6, -35], [-5.6, -35]]); bPaint(ctx, C.belt, "#3e2614");
      poly(ctx, [[-1.2, -37.8], [1.2, -37.8], [1.2, -34.7], [-1.2, -34.7]]); bPaint(ctx, C.gold, C.goldD, 0.4);
      // 脖子＋頭
      poly(ctx, [[-1.6, -53], [1.6, -53], [1.8, -49.5], [-1.8, -49.5]]); bPaint(ctx, C.skinD, C.skinD);
      ell(ctx, 0, -57.5, 4.3, 5.2); bPaint(ctx, lin(ctx, -4, -62, 4, -53, C.skin, C.skinD), "#9a6040");
      ctx.fillStyle = "#2a1a14"; for (const sx of [-1.6, 1.6]) { ell(ctx, sx, -57.3, 0.55, 0.7); ctx.fill(); }
      ctx.strokeStyle = C.hairD; ctx.lineWidth = 0.45; ctx.beginPath(); ctx.moveTo(-2.4, -58.9); ctx.lineTo(-0.8, -58.6); ctx.moveTo(2.4, -58.9); ctx.lineTo(0.8, -58.6); ctx.stroke();
      ctx.strokeStyle = "#a8684a"; ctx.lineWidth = 0.4; ctx.beginPath(); ctx.moveTo(-0.9, -54.6); ctx.quadraticCurveTo(0, -54.1, 0.9, -54.6); ctx.stroke();
      // 頭髮（側分）
      ctx.beginPath(); ctx.moveTo(-4.6, -56.5); ctx.quadraticCurveTo(-5.2, -63.8, 0, -63.6); ctx.quadraticCurveTo(5.3, -63.6, 4.7, -56.8);
      ctx.quadraticCurveTo(3.6, -60.2, 1.2, -60.5); ctx.quadraticCurveTo(-1.5, -59.2, -3.6, -60); ctx.quadraticCurveTo(-4.2, -58.6, -4.6, -56.5); ctx.closePath();
      bPaint(ctx, lin(ctx, -4, -64, 4, -57, "#8a5230", C.hairD), C.hairD);
      // 右手（畫面左）垂下握劍、劍尖斜指地面
      bLimb(ctx, -6.4, -48.5, -8.6, -31, 2.8, C.tunic, C.tunicD);
      ctx.save(); ctx.translate(-8.9, -30); ctx.rotate(0.42);
      poly(ctx, [[-0.9, 2], [0.9, 2], [0.75, 21], [0, 23.5], [-0.75, 21]]); bPaint(ctx, lin(ctx, -1, 0, 1, 0, "#ffffff", C.steelD), "#6a7684", 0.45);
      poly(ctx, [[-3.2, 1.2], [3.2, 1.2], [3.2, 2.4], [-3.2, 2.4]]); bPaint(ctx, C.gold, C.goldD, 0.4);
      poly(ctx, [[-0.6, -2.6], [0.6, -2.6], [0.6, 1.2], [-0.6, 1.2]]); bPaint(ctx, C.belt, "#3e2614", 0.4);
      ctx.restore();
      ell(ctx, -8.8, -30.5, 1.5, 1.6); bPaint(ctx, C.skin, "#9a6040", 0.45);
      // 左手（畫面右）掛圓盾
      bLimb(ctx, 6.4, -48.5, 8, -36, 2.8, C.tunic, C.tunicD);
      ell(ctx, 9, -36, 6.2, 7.4); bPaint(ctx, rad(ctx, 9, -36, 7.4, "#4f80cc", C.shieldD), C.ironD, 0.7);
      ctx.lineWidth = 1.2; ctx.strokeStyle = C.iron; ell(ctx, 9, -36, 5.6, 6.8); ctx.stroke();
      ell(ctx, 9, -36, 1.8, 2); bPaint(ctx, rad(ctx, 9, -36, 2, "#fff0a0", C.goldD), C.goldD, 0.4);
    },
    side(ctx) {
      bShadow(ctx);
      // 披風往後飄
      poly(ctx, [[-2, -50], [1, -50], [-3.5, -12], [-9, -9], [-12, -11], [-8, -30]]);
      bPaint(ctx, lin(ctx, -12, 0, 1, 0, C.capeD, C.cape), C.capeD);
      // 遠側腿（暗一點）在後
      poly(ctx, [[-2.6, -28], [1.2, -28], [-0.6, -9], [-3.6, -9]]); bPaint(ctx, C.pantsD, "#1a1a2a");
      poly(ctx, [[-3.8, -10], [-0.4, -10], [0.6, -1.4], [1.6, 0], [-4, 0]]); bPaint(ctx, C.bootD, "#2a180e");
      // 近側腿往前一步
      poly(ctx, [[-1.2, -28], [2.8, -28], [3.6, -9], [0.6, -9]]); bPaint(ctx, lin(ctx, -1, 0, 4, 0, C.pants, C.pantsD), C.pantsD);
      poly(ctx, [[0.4, -10], [3.8, -10], [4.6, -1.6], [7, 0], [0.4, 0]]); bPaint(ctx, lin(ctx, 0, -10, 0, 0, C.boot, C.bootD), C.bootD);
      // 身體（側面較薄，胸口往前）
      poly(ctx, [[-3.6, -50], [2.6, -50], [4.4, -44], [3.4, -37], [4.4, -26], [-1, -24.5], [-4.6, -26], [-3.4, -37]]);
      bPaint(ctx, lin(ctx, -4, -50, 4, -26, C.tunicL, C.tunicD), C.tunicD);
      poly(ctx, [[-3.6, -37.5], [3.6, -37.5], [3.8, -35], [-3.8, -35]]); bPaint(ctx, C.belt, "#3e2614");
      // 遠側手的盾：側看是窄窄一片，在胸前
      ell(ctx, 6, -37, 1.9, 7.2); bPaint(ctx, lin(ctx, 4, 0, 8, 0, C.iron, C.shieldD), C.ironD, 0.6);
      // 脖子＋頭（側臉朝東）
      poly(ctx, [[-1.4, -53], [1.8, -53], [1.8, -49.5], [-1.4, -49.5]]); bPaint(ctx, C.skinD, C.skinD);
      ctx.beginPath(); ctx.moveTo(-3.8, -55); ctx.quadraticCurveTo(-4.6, -63, 0.4, -63); ctx.quadraticCurveTo(4.4, -63, 4.4, -58.6);
      ctx.lineTo(5.3, -56.6); ctx.lineTo(4.4, -56); ctx.quadraticCurveTo(4.3, -53, 1.6, -52.4); ctx.quadraticCurveTo(-2.4, -52.6, -3.8, -55); ctx.closePath();
      bPaint(ctx, lin(ctx, -4, -63, 5, -52, C.skin, C.skinD), "#9a6040");
      ctx.fillStyle = "#2a1a14"; ell(ctx, 2.7, -57.6, 0.5, 0.7); ctx.fill();
      ctx.strokeStyle = C.hairD; ctx.lineWidth = 0.45; ctx.beginPath(); ctx.moveTo(1.8, -59.1); ctx.lineTo(3.4, -59); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(-4.4, -54.6); ctx.quadraticCurveTo(-5.4, -64, 0.6, -63.7); ctx.quadraticCurveTo(4.8, -63.4, 4.6, -59.6);
      ctx.quadraticCurveTo(2.6, -61.2, 0.8, -60.4); ctx.quadraticCurveTo(0.2, -57.4, -1.2, -56.6); ctx.quadraticCurveTo(-2.4, -54.6, -4.4, -54.6); ctx.closePath();
      bPaint(ctx, lin(ctx, -4, -64, 4, -57, "#8a5230", C.hairD), C.hairD);
      ell(ctx, -0.6, -57, 0.9, 1.3); bPaint(ctx, C.skinD, "#9a6040", 0.4);
      // 近側手臂握劍，劍往前斜下
      bLimb(ctx, -0.6, -48.5, 2.6, -32, 2.8, C.tunic, C.tunicD);
      ctx.save(); ctx.translate(3.2, -31.2); ctx.rotate(-1.05);
      poly(ctx, [[-0.9, 2], [0.9, 2], [0.75, 21], [0, 23.5], [-0.75, 21]]); bPaint(ctx, lin(ctx, -1, 0, 1, 0, "#ffffff", C.steelD), "#6a7684", 0.45);
      poly(ctx, [[-3.2, 1.2], [3.2, 1.2], [3.2, 2.4], [-3.2, 2.4]]); bPaint(ctx, C.gold, C.goldD, 0.4);
      poly(ctx, [[-0.6, -2.6], [0.6, -2.6], [0.6, 1.2], [-0.6, 1.2]]); bPaint(ctx, C.belt, "#3e2614", 0.4);
      ctx.restore();
      ell(ctx, 3, -31.4, 1.5, 1.6); bPaint(ctx, C.skin, "#9a6040", 0.45);
    },
  };

  // ───────────────────────── C. 手繪墨線繪本 ─────────────────────────
  // 抖動的墨線、顏色像水彩一樣略微溢出線外、暗面用斜線排線。
  function rng(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
  function ellPts(cx, cy, rx, ry, n = 18) { return Array.from({ length: n }, (_, i) => [cx + Math.cos((i / n) * Math.PI * 2) * rx, cy + Math.sin((i / n) * Math.PI * 2) * ry]); }
  function wobble(pts, r, amt) { return pts.map(([x, y]) => [x + (r() - 0.5) * amt, y + (r() - 0.5) * amt]); }
  function smoothPath(ctx, pts) {
    ctx.beginPath();
    const n = pts.length; const mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
    const m0 = mid(pts[n - 1], pts[0]); ctx.moveTo(m0[0], m0[1]);
    for (let i = 0; i < n; i++) { const p = pts[i]; const m = mid(p, pts[(i + 1) % n]); ctx.quadraticCurveTo(p[0], p[1], m[0], m[1]); }
    ctx.closePath();
  }
  const INK = "#2b1e16";
  function ink(ctx, pts, color, seed, opt = {}) {
    const r = rng(seed);
    // 水彩：顏色往右下偏一點、邊緣深一圈
    ctx.save(); ctx.translate(0.5, 0.4);
    smoothPath(ctx, wobble(pts, r, 0.8)); ctx.globalAlpha = 0.92; ctx.fillStyle = color; ctx.fill();
    ctx.globalAlpha = 0.35; ctx.strokeStyle = opt.edge ?? "rgba(0,0,0,0.5)"; ctx.lineWidth = 0.9; ctx.stroke();
    ctx.restore();
    if (opt.hatch) {
      ctx.save(); smoothPath(ctx, pts); ctx.clip(); ctx.strokeStyle = "rgba(43,30,22,0.45)"; ctx.lineWidth = 0.35;
      const [x0, x1, y0, y1] = opt.hatch;
      ctx.beginPath(); for (let x = x0; x < x1 + (y1 - y0); x += 1.3) { ctx.moveTo(x, y0); ctx.lineTo(x - (y1 - y0), y1); } ctx.stroke(); ctx.restore();
    }
    // 墨線：描兩次、每次抖一點
    ctx.strokeStyle = INK; ctx.lineJoin = "round"; ctx.lineCap = "round";
    ctx.lineWidth = opt.w ?? 0.85; smoothPath(ctx, wobble(pts, r, 0.55)); ctx.stroke();
    ctx.lineWidth = (opt.w ?? 0.85) * 0.45; smoothPath(ctx, wobble(pts, r, 0.9)); ctx.stroke();
  }
  function inkLine(ctx, pts, seed, w = 0.7) {
    const r = rng(seed); ctx.strokeStyle = INK; ctx.lineWidth = w; ctx.lineCap = "round";
    ctx.beginPath(); wobble(pts, r, 0.4).forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.stroke();
  }
  function cShadow(ctx) {
    const r = rng(7); ctx.strokeStyle = "rgba(43,30,22,0.5)"; ctx.lineWidth = 0.5; ctx.beginPath();
    for (let i = 0; i < 9; i++) { const x = -9 + i * 2.2 + r(); ctx.moveTo(x, 1.2); ctx.lineTo(x + 2.4, -0.6); }
    ctx.stroke();
  }
  const story = {
    front(ctx) {
      cShadow(ctx);
      ink(ctx, [[-8, -33], [8, -33], [11, -8], [5, -6], [0, -7.5], [-5, -6], [-11, -8]], C.cape, 11, { hatch: [2, 11, -33, -6] });
      for (const sx of [-1, 1]) {
        ink(ctx, [[sx * 0.8, -15], [sx * 4.6, -15], [sx * 4.4, -6], [sx * 1, -6]], C.pants, 20 + sx);
        ink(ctx, [[sx * 0.6, -7], [sx * 4.8, -7], [sx * 5.6, -0.8], [sx * 0.4, -0.4]], C.boot, 30 + sx);
      }
      ink(ctx, [[-7, -33], [7, -33], [6, -23], [8, -14], [0, -12.5], [-8, -14], [-6, -23]], C.tunic, 40, { hatch: [1, 8, -33, -12] });
      inkLine(ctx, [[-6.2, -23], [6.2, -23]], 41, 1.6); inkLine(ctx, [[-6.2, -23], [6.2, -23]], 42, 0.5);
      ctx.fillStyle = C.gold; ctx.fillRect(-1.3, -24.4, 2.6, 2.8); inkLine(ctx, [[-1.3, -24.4], [1.3, -24.4], [1.3, -21.6], [-1.3, -21.6], [-1.3, -24.4]], 43, 0.5);
      ink(ctx, ellPts(0, -42, 9.2, 8.6), C.skin, 50, { w: 1 });
      ctx.fillStyle = INK; for (const sx of [-3.2, 3.2]) { ell(ctx, sx, -41, 0.9, 1.3); ctx.fill(); }
      ctx.fillStyle = "rgba(220,90,80,0.35)"; for (const sx of [-5.4, 5.4]) { ell(ctx, sx, -38.6, 1.6, 0.9); ctx.fill(); }
      inkLine(ctx, [[-1, -37.4], [0, -36.8], [1, -37.4]], 51, 0.5);
      ink(ctx, [[-9.6, -41], [-10, -48], [-5, -52.5], [2, -52.5], [8, -49.5], [10, -42], [8, -45], [5, -45.5], [2, -44], [-1, -46], [-4, -44.8], [-7, -45.5]], C.hair, 52, { hatch: [-2, 10, -53, -44] });
      // 右手握劍往上舉
      ink(ctx, [[-7, -31.5], [-4.8, -31], [-7.4, -22.5], [-9.8, -23.5]], C.tunic, 60);
      ink(ctx, [[-10.2, -26], [-9.4, -46], [-8.2, -48], [-7.6, -46], [-8.2, -26]], C.steel, 61, { w: 0.7 });
      ink(ctx, [[-12.6, -26.4], [-5.8, -26.6], [-5.8, -24.8], [-12.6, -24.6]], C.gold, 62, { w: 0.6 });
      ink(ctx, ellPts(-9, -23.2, 1.8, 1.8, 10), C.skin, 63, { w: 0.6 });
      // 左手的盾
      ink(ctx, ellPts(8.6, -21, 6.6, 7, 20), C.shield, 70, { hatch: [8, 16, -28, -14], w: 1 });
      inkLine(ctx, ellPts(8.6, -21, 5.2, 5.6, 20).concat([[13.8, -21]]), 71, 0.45);
      ink(ctx, ellPts(8.6, -21, 1.8, 1.8, 10), C.gold, 72, { w: 0.6 });
    },
    side(ctx) {
      cShadow(ctx);
      ink(ctx, [[-3, -33], [1, -33], [-4, -9], [-10, -6.5], [-13, -9], [-8, -22]], C.cape, 111, { hatch: [-13, -2, -33, -6] });
      ink(ctx, [[-3, -15], [0.6, -15], [-0.6, -6], [-3.8, -6]], C.pantsD, 120);
      ink(ctx, [[-4.2, -7], [-0.4, -7], [1, -0.6], [-4.4, -0.4]], C.bootD, 121);
      ink(ctx, [[-0.6, -15], [3.2, -15], [3.8, -6], [0.6, -6]], C.pants, 122);
      ink(ctx, [[0.4, -7], [4, -7], [7.4, -0.8], [0.4, -0.4]], C.boot, 123);
      ink(ctx, [[-4, -33], [3.4, -33], [5, -27], [4, -22], [5.2, -14], [-1, -12.5], [-5.6, -14], [-4.2, -22]], C.tunic, 140, { hatch: [-6, 0, -33, -12] });
      inkLine(ctx, [[-4.2, -23], [4.4, -23]], 141, 1.6);
      ink(ctx, ellPts(7, -23, 2, 7, 14), C.shield, 145, { w: 0.8 });
      ink(ctx, [[-8.6, -42], [-8, -49], [-2, -51.5], [5, -50], [8.4, -45], [8.2, -42], [9.6, -39.6], [8, -38.6], [6.6, -35], [0, -34], [-6.4, -36]], C.skin, 150, { w: 1 });
      ctx.fillStyle = INK; ell(ctx, 4.4, -41.4, 0.9, 1.3); ctx.fill();
      ctx.fillStyle = "rgba(220,90,80,0.35)"; ell(ctx, 3.2, -38.6, 1.6, 0.9); ctx.fill();
      ink(ctx, [[-9.2, -38], [-9.4, -47], [-4, -52.5], [3, -52.6], [8.6, -48.5], [9.4, -44.6], [6, -46], [3, -45.5], [1, -43], [-1.4, -41], [-2.6, -37], [-6, -35.4]], C.hair, 152, { hatch: [-10, 2, -53, -35] });
      ink(ctx, ellPts(-2.6, -40, 1.4, 1.9, 10), C.skin, 153, { w: 0.6 });
      // 近側手握劍往前上舉
      ink(ctx, [[-1.4, -31.5], [1.4, -31.8], [5, -25], [2.6, -23.6]], C.tunic, 160);
      ink(ctx, [[4.4, -26.2], [17.4, -40.6], [19.4, -41.4], [18.6, -39.2], [5.8, -24.6]], C.steel, 161, { w: 0.7 });
      ink(ctx, [[2.4, -28.6], [3.4, -29.6], [8, -22.8], [7, -21.8]], C.gold, 162, { w: 0.6 });
      ink(ctx, ellPts(4.6, -24, 1.8, 1.8, 10), C.skin, 163, { w: 0.6 });
    },
  };

  // ───────────────────────── D. 桌遊模型（立體公仔＋底座）─────────────────────────
  // 二頭身、像上了漆的塑膠模型：球形漸層、亮點高光、站在有隊伍色邊的圓底座上。
  function base(ctx, team = "#3f7fd8") {
    ell(ctx, 0, 1.8, 14, 4.6); ctx.fillStyle = "#16181e"; ctx.fill();
    ctx.fillStyle = "#2a2e38"; ctx.fillRect(-14, -1.2, 28, 3); ell(ctx, 0, 1.8, 14, 4.6); ctx.fill();
    ell(ctx, 0, -1.2, 14, 4.6); ctx.fillStyle = lin(ctx, 0, -6, 0, 3, "#59606e", "#3a3f4a"); ctx.fill();
    ctx.lineWidth = 1.4; ctx.strokeStyle = team; ell(ctx, 0, -1.2, 12.8, 4); ctx.stroke();
    ell(ctx, 0, -1.4, 7, 2.2); ctx.fillStyle = "rgba(0,0,0,0.35)"; ctx.fill();
  }
  function shine(ctx, x, y, r) { ell(ctx, x, y, r, r * 0.7, -0.5); ctx.fillStyle = "rgba(255,255,255,0.55)"; ctx.fill(); }
  function blob(ctx, x, y, r, a, b, ry = r) { ell(ctx, x, y, r, ry); ctx.fillStyle = rad(ctx, x, y, Math.max(r, ry), a, b); ctx.fill(); }
  const toy = {
    front(ctx) {
      base(ctx);
      ctx.translate(0, -2);
      // 披風
      poly(ctx, [[-7, -27], [7, -27], [9.5, -6], [-9.5, -6]]); ctx.fillStyle = lin(ctx, -9, 0, 9, 0, C.cape, C.capeD); ctx.fill();
      // 腳
      for (const sx of [-1, 1]) { blob(ctx, sx * 3.2, -2.6, 3.2, "#a06a3c", C.bootD, 2.6); blob(ctx, sx * 3, -7, 2.6, "#5a5a7e", C.pantsD, 3); }
      // 身體
      ctx.beginPath(); ctx.moveTo(-7.4, -24); ctx.quadraticCurveTo(-8.4, -9, -6, -8); ctx.lineTo(6, -8); ctx.quadraticCurveTo(8.4, -9, 7.4, -24); ctx.quadraticCurveTo(0, -29, -7.4, -24); ctx.closePath();
      ctx.fillStyle = rad(ctx, 0, -16, 11, "#8cc062", C.tunicD); ctx.fill();
      ctx.fillStyle = lin(ctx, 0, -13, 0, -10, "#8a5a32", "#4e301a"); ctx.fillRect(-7.6, -13.2, 15.2, 2.6);
      blob(ctx, 0, -11.9, 1.6, "#fff0a0", C.goldD, 1.4);
      // 頭（大）
      blob(ctx, 0, -38, 11, "#ffd2ae", "#c47e58");
      ctx.fillStyle = "#1e1418"; for (const sx of [-3.6, 3.6]) { ell(ctx, sx, -36.4, 1.4, 2); ctx.fill(); }
      ctx.fillStyle = "#ffffff"; for (const sx of [-3.2, 4]) { ell(ctx, sx, -37.2, 0.5, 0.6); ctx.fill(); }
      ctx.fillStyle = "rgba(240,110,100,0.4)"; for (const sx of [-6.2, 6.2]) { ell(ctx, sx, -33.4, 1.8, 1); ctx.fill(); }
      // 頭髮：一整塊像塑膠帽殼
      ctx.beginPath(); ctx.moveTo(-11.4, -36); ctx.quadraticCurveTo(-12.6, -50.6, 0, -50.4); ctx.quadraticCurveTo(12.6, -50.6, 11.4, -36);
      ctx.quadraticCurveTo(10, -42.6, 6, -42.4); ctx.quadraticCurveTo(3, -40.6, 0, -43.2); ctx.quadraticCurveTo(-3.4, -40.4, -6.4, -42.6); ctx.quadraticCurveTo(-10, -42.4, -11.4, -36); ctx.closePath();
      ctx.fillStyle = rad(ctx, 0, -44, 12, "#a4643a", C.hairD); ctx.fill();
      shine(ctx, -5, -46.6, 2.6); shine(ctx, -6.2, -40.6, 1.6);
      // 劍（右手、畫面左、豎起）
      ctx.save(); ctx.translate(-9.4, -13);
      ctx.fillStyle = lin(ctx, -1.4, 0, 1.4, 0, "#ffffff", C.steelD); poly(ctx, [[-1.3, -2], [1.3, -2], [1.3, -18], [0, -20.6], [-1.3, -18]]); ctx.fill();
      ctx.fillStyle = lin(ctx, 0, -2.6, 0, 0, "#ffe27a", C.goldD); ctx.fillRect(-3.6, -2.8, 7.2, 2.2);
      ctx.restore();
      blob(ctx, -9.4, -12.2, 2.4, "#ffd2ae", "#c47e58");
      // 盾（左手、畫面右）
      blob(ctx, 9.4, -16, 7, "#5e94e6", C.shieldD, 7.6);
      ctx.lineWidth = 1.5; ctx.strokeStyle = lin(ctx, 0, -24, 0, -8, "#c4ccd4", C.ironD); ell(ctx, 9.4, -16, 6.3, 6.9); ctx.stroke();
      blob(ctx, 9.4, -16, 2, "#fff0a0", C.goldD);
      shine(ctx, 6.4, -20.4, 1.8);
    },
    side(ctx) {
      base(ctx);
      ctx.translate(0, -2);
      poly(ctx, [[-3, -27], [2, -27], [-4, -6], [-12, -5], [-10, -16]]); ctx.fillStyle = lin(ctx, -12, 0, 2, 0, C.capeD, C.cape); ctx.fill();
      blob(ctx, -1.6, -2.6, 3.4, "#7a4e2c", C.bootD, 2.6); blob(ctx, -1.6, -7, 2.5, "#444466", C.pantsD, 3);
      blob(ctx, 2.6, -2.6, 3.8, "#a06a3c", C.bootD, 2.6); blob(ctx, 1.6, -7, 2.6, "#5a5a7e", C.pantsD, 3);
      ctx.beginPath(); ctx.moveTo(-5, -24); ctx.quadraticCurveTo(-6.4, -9, -4.4, -8); ctx.lineTo(4.4, -8); ctx.quadraticCurveTo(6.8, -9, 5.4, -24); ctx.quadraticCurveTo(0, -28, -5, -24); ctx.closePath();
      ctx.fillStyle = rad(ctx, 0, -16, 10, "#8cc062", C.tunicD); ctx.fill();
      ctx.fillStyle = lin(ctx, 0, -13, 0, -10, "#8a5a32", "#4e301a"); ctx.fillRect(-5.6, -13.2, 11.4, 2.6);
      // 遠側手的盾：側看是一片厚圓餅
      ell(ctx, 7.2, -16, 2.6, 7.4); ctx.fillStyle = lin(ctx, 5, 0, 10, 0, C.ironD, "#5e94e6"); ctx.fill();
      // 頭：側臉朝東、鼻子小凸起
      blob(ctx, 0.4, -38, 11, "#ffd2ae", "#c47e58");
      blob(ctx, 11, -36, 1.4, "#ffd2ae", "#d89070");
      ctx.fillStyle = "#1e1418"; ell(ctx, 6.6, -36.6, 1.3, 2); ctx.fill();
      ctx.fillStyle = "#ffffff"; ell(ctx, 7, -37.4, 0.45, 0.55); ctx.fill();
      ctx.fillStyle = "rgba(240,110,100,0.4)"; ell(ctx, 5.4, -33, 1.8, 1); ctx.fill();
      ctx.beginPath(); ctx.moveTo(-10.6, -32); ctx.quadraticCurveTo(-12.6, -50.6, 0.4, -50.4); ctx.quadraticCurveTo(11.8, -50.6, 11.2, -40.4);
      ctx.quadraticCurveTo(8, -43, 4.4, -42.6); ctx.quadraticCurveTo(2.4, -38, -0.6, -36.8); ctx.quadraticCurveTo(-3, -32, -6, -30.2); ctx.quadraticCurveTo(-9.6, -29.8, -10.6, -32); ctx.closePath();
      ctx.fillStyle = rad(ctx, 0, -44, 12, "#a4643a", C.hairD); ctx.fill();
      shine(ctx, -3, -46.8, 2.6);
      blob(ctx, -2.6, -36.4, 1.8, "#ffd2ae", "#c47e58", 2.4);
      // 近側手握劍朝前豎起
      ctx.save(); ctx.translate(6, -12); ctx.rotate(0.35);
      ctx.fillStyle = lin(ctx, -1.4, 0, 1.4, 0, "#ffffff", C.steelD); poly(ctx, [[-1.3, -2], [1.3, -2], [1.3, -18], [0, -20.6], [-1.3, -18]]); ctx.fill();
      ctx.fillStyle = lin(ctx, 0, -2.6, 0, 0, "#ffe27a", C.goldD); ctx.fillRect(-3.6, -2.8, 7.2, 2.2);
      ctx.restore();
      blob(ctx, 5.6, -11.4, 2.4, "#ffd2ae", "#c47e58");
    },
  };

  const STYLES = {
    pixel: { zh: "A 像素風（16-bit）", ...pixel },
    tall: { zh: "B 高頭身寫實（戰棋立繪）", ...tall },
    story: { zh: "C 手繪墨線繪本", ...story },
    toy: { zh: "D 桌遊模型（公仔＋底座）", ...toy },
  };
  // 在 (cx, cy) 畫腳底、k 倍；west 時左右翻轉
  function stamp(ctx, style, view, cx, cy, k = 1, west = false) {
    ctx.save(); ctx.translate(cx, cy); ctx.scale(west ? -k : k, k);
    STYLES[style][view](ctx);
    ctx.restore();
  }
  return { STYLES, stamp };
})();
