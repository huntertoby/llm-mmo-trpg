// 大世界圖（M），俯視彩繪風（B 案）第 2 版：加光影、雲層明暗、島的岩層與瀑布、正式字牌。
// 要先載入 regionArt.js。全部程式繪製。
// 方位照 6D-5（6D-4 的浮橋）：西雲嶺、南荒原、北晶冠、東樞市、東南霜潮；主城「樞島」在中央。
(function () {
  const RA = window.RegionArt, W = 1280, H = 860, TAU = Math.PI * 2;
  const FONT = RA.PAL.painted.font;
  const SERIF = '"Noto Serif TC","PMingLiU","MingLiU",serif';
  // 光從左上來
  const LIGHT = [-0.6, -0.8];
  // state：open＝已開放；locked＝有地點圖但還沒亮起；later＝之後的賽季
  const ISLANDS = [
    { id: "capital", name: "主城", town: "樞島", state: "open", x: 650, y: 350, rx: 125, ry: 66, kind: "capital" },
    { id: "cloud_ridge", name: "雲嶺", town: "霧渡鎮", lv: "1～6", state: "open", x: 260, y: 360, rx: 185, ry: 98, kind: "cloud", here: true },
    { id: "ashen_waste", name: "灰燼荒原", town: "餘燼集", lv: "5～9", state: "open", x: 610, y: 600, rx: 180, ry: 84, kind: "ashen" },
    { id: "crystal_crown", name: "晶冠城邦", state: "later", x: 660, y: 112, rx: 120, ry: 48, kind: "crown" },
    { id: "arcane_hub", name: "魔導樞市", state: "later", x: 1050, y: 300, rx: 135, ry: 58, kind: "arcane" },
    { id: "frost_tide", name: "霜潮海境", state: "later", x: 1030, y: 590, rx: 135, ry: 58, kind: "frost" },
  ];
  const COND = { later: "之後的賽季", locked: "世界事件：霧潮入侵" };

  // ---------- 雲 ----------
  // 有明暗的雲團：上亮下暗
  function cloudPuff(ctx, x, y, r, a, tint = [255, 255, 255], shade = [176, 190, 214], sy = 1) {
    ctx.save(); ctx.translate(x, y); ctx.scale(1, sy); x = 0; y = 0;
    const g = ctx.createRadialGradient(x - r * 0.25, y - r * 0.45, r * 0.1, x, y, r);
    g.addColorStop(0, `rgba(${tint},${a})`);
    g.addColorStop(0.55, `rgba(${tint.map((v, i) => Math.round(v * 0.6 + shade[i] * 0.4))},${a})`);
    g.addColorStop(0.9, `rgba(${shade},${a * 0.9})`);
    g.addColorStop(1, `rgba(${shade},0)`);
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill();
    ctx.restore();
  }
  function cloudBank(ctx, y, count, rMin, rMax, a, seed, tint, shade, spread = 30, sy = 0.62) {
    const r = RA.rng(seed), items = [];
    for (let i = 0; i < count; i++) items.push([(i / count) * (W + 200) - 100 + (r() - 0.5) * 60, y + (r() - 0.5) * spread, rMin + r() * (rMax - rMin)]);
    items.sort((p, q) => p[1] - q[1]).forEach(([x, yy, rr]) => cloudPuff(ctx, x, yy, rr, a, tint, shade, sy));
  }

  function sky(ctx) {
    const g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, "#36507f"); g.addColorStop(0.35, "#6f93c4"); g.addColorStop(0.62, "#c7cfe0"); g.addColorStop(0.85, "#f2d6b0"); g.addColorStop(1, "#f6e2c4");
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    // 太陽光暈（左上）
    const s = ctx.createRadialGradient(150, 70, 10, 150, 70, 520);
    s.addColorStop(0, "rgba(255,240,205,0.85)"); s.addColorStop(0.25, "rgba(255,226,170,0.35)"); s.addColorStop(1, "rgba(255,226,170,0)");
    ctx.fillStyle = s; ctx.fillRect(0, 0, W, H);
    // 光束
    ctx.save(); ctx.globalCompositeOperation = "lighter";
    for (let i = 0; i < 6; i++) {
      const a0 = 0.15 + i * 0.13;
      ctx.fillStyle = `rgba(255,236,190,${0.035 + (i % 2) * 0.02})`;
      ctx.beginPath(); ctx.moveTo(150, 70);
      ctx.lineTo(150 + Math.cos(a0) * 1600, 70 + Math.sin(a0) * 1600);
      ctx.lineTo(150 + Math.cos(a0 + 0.05) * 1600, 70 + Math.sin(a0 + 0.05) * 1600); ctx.closePath(); ctx.fill();
    }
    ctx.restore();
    // 碎界：天上幾道很淡的發光裂痕
    ctx.save(); ctx.strokeStyle = "rgba(210,195,255,0.55)"; ctx.lineWidth = 1.2; ctx.shadowColor = "#b9a4ff"; ctx.shadowBlur = 10;
    const r = RA.rng(401);
    for (let i = 0; i < 4; i++) {
      let x = 380 + r() * 760, y = 30 + r() * 140; ctx.beginPath(); ctx.moveTo(x, y);
      for (let k = 0; k < 5; k++) { x += 20 + r() * 40; y += (r() - 0.5) * 30; ctx.lineTo(x, y); }
      ctx.stroke();
    }
    ctx.restore();
    // 遠方雲層（偏藍、淡）
    cloudBank(ctx, 230, 26, 30, 60, 0.35, 403, [236, 240, 250], [150, 168, 200], 30);
    cloudBank(ctx, 330, 22, 40, 80, 0.45, 405, [245, 244, 248], [160, 172, 202], 40);
  }

  function lowerClouds(ctx) {
    cloudBank(ctx, 520, 20, 50, 95, 0.55, 407, [255, 250, 244], [178, 182, 206], 60);
    cloudBank(ctx, 690, 24, 50, 90, 0.7, 409, [255, 248, 236], [200, 190, 200], 50, 0.55);
  }
  // 最前面一排雲，蓋住島的下緣，做出深度
  function frontClouds(ctx) {
    cloudBank(ctx, 845, 22, 50, 90, 0.85, 411, [255, 246, 232], [214, 196, 190], 24, 0.5);
  }

  // ---------- 小浮石 ----------
  function islet(ctx, x, y, s, r, haze) {
    ctx.save(); ctx.globalAlpha = haze;
    const g = ctx.createLinearGradient(x - s, 0, x + s, 0);
    g.addColorStop(0, "#9a7f62"); g.addColorStop(1, "#4a3828");
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.moveTo(x - s, y); ctx.lineTo(x - s * 0.4, y + s * 1.3); ctx.lineTo(x + s * 0.15, y + s * 1.9); ctx.lineTo(x + s * 0.6, y + s * 1.1); ctx.lineTo(x + s, y); ctx.closePath(); ctx.fill();
    ctx.fillStyle = "#6d9a4c"; ctx.beginPath(); ctx.ellipse(x, y, s, s * 0.38, 0, 0, TAU); ctx.fill();
    ctx.fillStyle = "rgba(255,255,220,0.35)"; ctx.beginPath(); ctx.ellipse(x - s * 0.3, y - s * 0.12, s * 0.45, s * 0.15, 0, 0, TAU); ctx.fill();
    if (r() < 0.5) RA.pine(ctx, "painted", x + s * 0.2, y + 1, s / 14);
    ctx.restore();
  }
  function islets(ctx) {
    const r = RA.rng(421);
    for (const [x, y, s, h] of [[470, 220, 9, 0.7], [860, 190, 7, 0.6], [880, 450, 10, 0.85], [420, 520, 8, 0.8], [130, 560, 12, 0.85], [1180, 150, 8, 0.6], [820, 720, 11, 0.9], [1200, 440, 7, 0.6], [330, 140, 6, 0.55]]) islet(ctx, x, y, s, r, h);
  }

  // ---------- 島 ----------
  function blob(cx, cy, rx, ry, seed) {
    const r = RA.rng(seed), p = new Path2D(), n = 30, pts = [];
    for (let i = 0; i < n; i++) {
      const a = (i / n) * TAU, k = 0.9 + r() * 0.15;
      pts.push([cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k]);
    }
    pts.forEach((q, i) => {
      const nx = pts[(i + 1) % n], mx = (q[0] + nx[0]) / 2, my = (q[1] + nx[1]) / 2;
      if (i === 0) p.moveTo(mx, my); else p.quadraticCurveTo(q[0], q[1], mx, my);
    });
    p.quadraticCurveTo(pts[0][0], pts[0][1], (pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2);
    p.closePath();
    return p;
  }
  const ROCK = {
    cloud: ["#a08466", "#7a6048", "#5a4434", "#3a2a20"],
    capital: ["#b8a688", "#8e7c62", "#66563f", "#3e3326"],
    ashen: ["#6e4e40", "#54382c", "#3e2820", "#241612"],
    grey: ["#8c90a0", "#6c7080", "#4e5262", "#33364a"],
  };
  const LIP = { cloud: "#5e8a3e", capital: "#a69878", ashen: "#4a3028", grey: "#7c8090" };

  function shadowBelow(ctx, is) {
    const g = ctx.createRadialGradient(is.x + 30, is.y + is.ry * 3.2, 10, is.x + 30, is.y + is.ry * 3.2, is.rx * 1.1);
    g.addColorStop(0, "rgba(70,70,110,0.22)"); g.addColorStop(1, "rgba(70,70,110,0)");
    ctx.fillStyle = g; ctx.beginPath(); ctx.ellipse(is.x + 30, is.y + is.ry * 3.2, is.rx * 1.1, is.ry * 0.5, 0, 0, TAU); ctx.fill();
  }

  function underside(ctx, is, pal) {
    const { x, y, rx, ry } = is, depth = ry * 0.42, r = RA.rng(x * 5 + y);
    // 倒錐：多個尖端
    const cone = new Path2D();
    cone.moveTo(x - rx * 0.9, y + depth * 0.5);
    const tips = 7;
    for (let k = 0; k <= tips * 2; k++) {
      const t = k / (tips * 2), xx = x - rx * 0.9 + t * rx * 1.8;
      const base = Math.sin(t * Math.PI);
      const yy = y + depth + (k % 2 ? base * ry * (1.2 + r() * 0.5) : base * ry * (0.55 + r() * 0.3));
      cone.lineTo(xx, yy);
    }
    cone.lineTo(x + rx * 0.9, y + depth * 0.5); cone.closePath();
    // 岩層：由上到下四色
    ctx.save(); ctx.clip(cone);
    const bandH = ry * 0.55;
    for (let i = 0; i < 4; i++) {
      ctx.fillStyle = pal[i];
      ctx.beginPath(); ctx.moveTo(x - rx, y + depth + i * bandH);
      for (let k = 0; k <= 12; k++) ctx.lineTo(x - rx + (k / 12) * rx * 2, y + depth + i * bandH + Math.sin(k * 1.7 + i) * 5);
      ctx.lineTo(x + rx, y + ry * 4); ctx.lineTo(x - rx, y + ry * 4); ctx.closePath(); ctx.fill();
    }
    // 光從左邊來：右側壓暗
    const lg = ctx.createLinearGradient(x - rx, 0, x + rx, 0);
    lg.addColorStop(0, "rgba(255,240,210,0.18)"); lg.addColorStop(0.45, "rgba(0,0,0,0)"); lg.addColorStop(1, "rgba(10,10,30,0.45)");
    ctx.fillStyle = lg; ctx.fillRect(x - rx, y, rx * 2, ry * 4);
    // 裂縫
    ctx.strokeStyle = "rgba(20,14,10,0.35)"; ctx.lineWidth = 1.4;
    for (let i = 0; i < 9; i++) {
      let cx = x - rx * 0.7 + r() * rx * 1.4, cy = y + depth + r() * ry * 0.4;
      ctx.beginPath(); ctx.moveTo(cx, cy);
      for (let k = 0; k < 4; k++) { cx += (r() - 0.5) * 10; cy += 8 + r() * 12; ctx.lineTo(cx, cy); }
      ctx.stroke();
    }
    ctx.restore();
    ctx.strokeStyle = "rgba(20,14,10,0.55)"; ctx.lineWidth = 1.5; ctx.stroke(cone);
    // 垂下來的根
    if (is.kind === "cloud" || is.kind === "capital") {
      ctx.strokeStyle = "rgba(60,44,30,0.7)"; ctx.lineWidth = 1.2;
      for (let i = 0; i < 10; i++) {
        const sx = x - rx * 0.8 + r() * rx * 1.6, sy = y + depth + 4, len = 16 + r() * 26;
        ctx.beginPath(); ctx.moveTo(sx, sy); ctx.quadraticCurveTo(sx + (r() - 0.5) * 12, sy + len * 0.6, sx + (r() - 0.5) * 8, sy + len); ctx.stroke();
      }
    }
  }

  // 島緣厚度：頂面往下一點的同形狀，左亮右暗
  function lip(ctx, is, top, col) {
    const depth = is.ry * 0.42;
    ctx.save(); ctx.translate(0, depth);
    ctx.fillStyle = col; ctx.fill(top);
    ctx.restore();
    ctx.save(); ctx.translate(0, depth); ctx.clip(top); ctx.translate(0, -depth);
    const lg = ctx.createLinearGradient(is.x - is.rx, 0, is.x + is.rx, 0);
    lg.addColorStop(0, "rgba(255,240,210,0.2)"); lg.addColorStop(1, "rgba(0,0,30,0.35)");
    ctx.fillStyle = lg; ctx.fillRect(is.x - is.rx, is.y, is.rx * 2, is.ry * 2);
    ctx.restore();
  }

  // 頂面的立體感：內緣陰影＋左上邊緣高光
  function topShade(ctx, is, top) {
    ctx.save(); ctx.clip(top);
    ctx.lineWidth = 22; ctx.strokeStyle = "rgba(20,20,40,0.22)"; ctx.stroke(top);
    ctx.lineWidth = 8; ctx.strokeStyle = "rgba(20,20,40,0.2)"; ctx.stroke(top);
    const g = ctx.createLinearGradient(is.x + LIGHT[0] * is.rx, is.y + LIGHT[1] * is.ry, is.x - LIGHT[0] * is.rx, is.y - LIGHT[1] * is.ry);
    g.addColorStop(0, "rgba(255,240,200,0.14)"); g.addColorStop(0.5, "rgba(255,240,200,0)"); g.addColorStop(1, "rgba(20,20,50,0.22)");
    ctx.fillStyle = g; ctx.fillRect(is.x - is.rx, is.y - is.ry, is.rx * 2, is.ry * 2);
    ctx.restore();
    ctx.strokeStyle = "rgba(30,24,18,0.55)"; ctx.lineWidth = 1.5; ctx.stroke(top);
  }

  function fall(ctx, x, y, len, lava) {
    ctx.save();
    if (lava) { ctx.shadowColor = "#ff6a1a"; ctx.shadowBlur = 14; }
    const g = ctx.createLinearGradient(0, y, 0, y + len);
    g.addColorStop(0, lava ? "rgba(255,150,60,0.95)" : "rgba(230,245,255,0.95)");
    g.addColorStop(1, lava ? "rgba(255,90,20,0)" : "rgba(200,225,245,0)");
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.moveTo(x - 5, y); ctx.lineTo(x + 5, y); ctx.lineTo(x + 9, y + len); ctx.lineTo(x - 9, y + len); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = lava ? "rgba(255,230,150,0.8)" : "rgba(255,255,255,0.9)"; ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.moveTo(x - 1, y); ctx.lineTo(x - 2, y + len * 0.7); ctx.stroke();
    ctx.restore();
    if (!lava) for (let i = 0; i < 3; i++) cloudPuff(ctx, x + (i - 1) * 12, y + len * 0.8, 14, 0.6);
    else for (let i = 0; i < 3; i++) RA.puff(ctx, x + (i - 1) * 12, y + len * 0.7, 14, 0.4, [120, 100, 90]);
  }

  // ---------- 各島頂面 ----------
  function topCloud(ctx, is) {
    const { x, y, rx, ry } = is, r = RA.rng(311);
    ctx.fillStyle = "#7fa65a"; ctx.fillRect(x - rx, y - ry, rx * 2, ry * 2);
    for (let i = 0; i < 60; i++) {
      ctx.fillStyle = i % 2 ? "rgba(60,100,40,0.16)" : "rgba(190,210,120,0.16)";
      ctx.beginPath(); ctx.ellipse(x + (r() - 0.5) * rx * 2, y + (r() - 0.5) * ry * 2, 14 + r() * 22, 8 + r() * 8, r() * 3, 0, TAU); ctx.fill();
    }
    // 河
    ctx.lineCap = "round";
    ctx.strokeStyle = "#356b94"; ctx.lineWidth = 11;
    ctx.beginPath(); ctx.moveTo(x - rx * 1.05, y + ry * 0.5); ctx.bezierCurveTo(x - 60, y + ry * 0.95, x + 40, y + ry * 0.2, x + rx * 1.05, y + ry * 0.45); ctx.stroke();
    ctx.strokeStyle = "#5c9cc8"; ctx.lineWidth = 6; ctx.stroke();
    ctx.strokeStyle = "rgba(255,255,255,0.6)"; ctx.lineWidth = 1.2; ctx.setLineDash([6, 10]); ctx.stroke(); ctx.setLineDash([]);
    // 梯田
    for (let i = 5; i >= 0; i--) {
      ctx.beginPath(); ctx.ellipse(x + 20, y + 34, 18 + i * 7, 10 + i * 4, 0, Math.PI * 1.05, Math.PI * 1.95);
      ctx.strokeStyle = i % 2 ? "#93c466" : "#b6dc87"; ctx.lineWidth = 4.5; ctx.stroke();
      ctx.strokeStyle = "rgba(225,240,250,0.8)"; ctx.lineWidth = 1; ctx.stroke();
    }
    // 竹林、松林
    for (let i = 0; i < 34; i++) {
      const bx = x - rx * 0.62 + r() * 80, by = y + 4 + r() * 46;
      ctx.strokeStyle = "#5c9c48"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(bx, by); ctx.lineTo(bx + 1, by - 13); ctx.stroke();
      ctx.fillStyle = ["#2f6b34", "#4f9a44", "#6cb455"][i % 3];
      ctx.beginPath(); ctx.ellipse(bx + 3, by - 12, 4.5, 1.6, -0.5, 0, TAU); ctx.fill();
    }
    const trees = [];
    for (let i = 0; i < 22; i++) trees.push([x + rx * 0.15 + r() * rx * 0.7, y - ry * 0.05 + r() * ry * 0.4]);
    trees.sort((a, b) => a[1] - b[1]).forEach(([tx, ty]) => RA.pine(ctx, "painted", tx, ty, 0.6));
    // 小鎮
    for (const [ox, oy] of [[-rx * 0.55, ry * 0.32], [-rx * 0.45, ry * 0.4], [-rx * 0.62, ry * 0.45]]) {
      const hx = x + ox, hy = y + oy;
      ctx.fillStyle = "#efe4cc"; ctx.fillRect(hx - 5, hy - 4, 10, 7);
      ctx.fillStyle = "#c0503a"; ctx.beginPath(); ctx.moveTo(hx - 7, hy - 3); ctx.lineTo(hx, hy - 9); ctx.lineTo(hx + 7, hy - 3); ctx.fill();
    }
    // 雪頂群山（北側）
    const pk = [];
    for (let i = 0; i < 12; i++) pk.push([x - rx * 0.78 + i * rx * 0.14 + (r() - 0.5) * 10, y - ry * 0.22 + (r() - 0.5) * 16, 32 + r() * 30 + (i > 7 ? 14 : 0)]);
    pk.sort((a, b) => a[1] - b[1]).forEach(([px, py, h]) => RA.mountain(ctx, "painted", px, py, h, r, true));
    // 山腰的雲霧
    for (let i = 0; i < 5; i++) cloudPuff(ctx, x - rx * 0.55 + i * rx * 0.28, y - 2 + (r() - 0.5) * 8, 13, 0.55);
  }

  function topAshen(ctx, is) {
    const { x, y, rx, ry } = is, r = RA.rng(313);
    const g = ctx.createLinearGradient(0, y - ry, 0, y + ry);
    g.addColorStop(0, "#3e302a"); g.addColorStop(0.5, "#6b5240"); g.addColorStop(1, "#a7744a");
    ctx.fillStyle = g; ctx.fillRect(x - rx, y - ry, rx * 2, ry * 2);
    for (let i = 0; i < 50; i++) {
      ctx.fillStyle = i % 2 ? "rgba(25,18,14,0.16)" : "rgba(210,130,70,0.14)";
      ctx.beginPath(); ctx.ellipse(x + (r() - 0.5) * rx * 2, y + (r() - 0.5) * ry * 2, 12 + r() * 18, 6 + r() * 6, r() * 3, 0, TAU); ctx.fill();
    }
    // 發光裂縫
    ctx.save(); ctx.strokeStyle = "#ff7a1a"; ctx.lineWidth = 1.4; ctx.shadowColor = "#ff6a1a"; ctx.shadowBlur = 6;
    for (let i = 0; i < 8; i++) {
      let cx = x + (r() - 0.5) * rx * 1.6, cy = y + (r() - 0.3) * ry; ctx.beginPath(); ctx.moveTo(cx, cy);
      for (let k = 0; k < 3; k++) { cx += (r() - 0.5) * 22; cy += (r() - 0.5) * 10; ctx.lineTo(cx, cy); }
      ctx.stroke();
    }
    ctx.restore();
    // 赤沙
    for (let i = 0; i < 8; i++) {
      ctx.fillStyle = "rgba(220,140,80,0.6)";
      ctx.beginPath(); ctx.ellipse(x - rx * 0.55 + i * 26, y + ry * 0.62 + (i % 2) * 6, 18, 6, 0, Math.PI, TAU); ctx.fill();
      ctx.strokeStyle = "rgba(255,210,160,0.5)"; ctx.lineWidth = 1; ctx.beginPath(); ctx.ellipse(x - rx * 0.55 + i * 26, y + ry * 0.62 + (i % 2) * 6, 13, 4, 0, Math.PI * 1.15, Math.PI * 1.85); ctx.stroke();
    }
    // 熔岩河
    ctx.save(); ctx.lineCap = "round"; ctx.shadowColor = "#ff6a1a"; ctx.shadowBlur = 16;
    ctx.beginPath(); ctx.moveTo(x + rx * 0.38, y - ry * 0.2); ctx.bezierCurveTo(x + 10, y + 10, x + rx * 0.5, y + ry * 0.5, x + rx * 1.05, y + ry * 0.3);
    ctx.strokeStyle = "#2a1610"; ctx.lineWidth = 14; ctx.stroke();
    ctx.strokeStyle = "#c2410c"; ctx.lineWidth = 10; ctx.stroke();
    ctx.strokeStyle = "#ff8a2a"; ctx.lineWidth = 5; ctx.stroke();
    ctx.strokeStyle = "#ffd36b"; ctx.lineWidth = 1.5; ctx.stroke();
    ctx.restore();
    // 枯木林
    for (let i = 0; i < 24; i++) {
      const tx = x - rx * 0.45 + r() * 100, ty = y + r() * 34 - 6;
      ctx.strokeStyle = "#241a16"; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(tx, ty); ctx.lineTo(tx, ty - 11); ctx.moveTo(tx, ty - 6); ctx.lineTo(tx - 4, ty - 10); ctx.moveTo(tx, ty - 8); ctx.lineTo(tx + 4, ty - 13); ctx.stroke();
    }
    // 岩山
    const pk = [];
    for (let i = 0; i < 8; i++) pk.push([x - rx * 0.72 + i * 30, y - ry * 0.32 + (r() - 0.5) * 12, 24 + r() * 16]);
    pk.sort((a, b) => a[1] - b[1]).forEach(([px, py, h]) => RA.mountain(ctx, "painted", px, py, h, r, false, ["#86705f", "#40332b"]));
  }
  function volcano(ctx, is) {
    const vx = is.x + is.rx * 0.4, vy = is.y + is.ry * 0.02;
    ctx.fillStyle = "#5e4c42"; ctx.beginPath(); ctx.moveTo(vx - 52, vy + 8); ctx.lineTo(vx - 12, vy - 56); ctx.lineTo(vx + 2, vy + 8); ctx.fill();
    ctx.fillStyle = "#2f241c"; ctx.beginPath(); ctx.moveTo(vx - 12, vy - 56); ctx.lineTo(vx + 12, vy - 56); ctx.lineTo(vx + 52, vy + 8); ctx.lineTo(vx + 2, vy + 8); ctx.fill();
    ctx.strokeStyle = "rgba(20,14,10,0.6)"; ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.moveTo(vx - 52, vy + 8); ctx.lineTo(vx - 12, vy - 56); ctx.lineTo(vx + 12, vy - 56); ctx.lineTo(vx + 52, vy + 8); ctx.stroke();
    ctx.save(); ctx.shadowColor = "#ff6a1a"; ctx.shadowBlur = 20;
    ctx.fillStyle = "#ff8a2a"; ctx.beginPath(); ctx.ellipse(vx, vy - 56, 13, 4, 0, 0, TAU); ctx.fill();
    ctx.strokeStyle = "#ff7a1a"; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.moveTo(vx - 4, vy - 54); ctx.quadraticCurveTo(vx - 18, vy - 30, vx - 10, vy + 4); ctx.stroke();
    ctx.restore();
    for (let i = 0; i < 9; i++) RA.puff(ctx, vx - i * 12, vy - 66 - i * 7, 10 + i * 2.4, 0.5 - i * 0.04, [96, 84, 78]);
  }

  function topCapital(ctx, is) {
    const { x, y, rx, ry } = is, r = RA.rng(317);
    ctx.fillStyle = "#ddd2b8"; ctx.fillRect(x - rx, y - ry, rx * 2, ry * 2);
    // 草地與花圃
    for (const [ox, oy] of [[-72, -30], [72, -30], [-74, 30], [74, 30]]) {
      ctx.fillStyle = "#86b862"; ctx.beginPath(); ctx.ellipse(x + ox, y + oy, 28, 15, 0, 0, TAU); ctx.fill();
      for (let k = 0; k < 5; k++) { ctx.fillStyle = ["#f2c230", "#e06a8a", "#ffffff"][k % 3]; ctx.beginPath(); ctx.arc(x + ox + (r() - 0.5) * 36, y + oy + (r() - 0.5) * 16, 1.6, 0, TAU); ctx.fill(); }
    }
    // 石板路
    ctx.fillStyle = "#c6b693"; ctx.fillRect(x - rx, y - 7, rx * 2, 14); ctx.fillRect(x - 7, y - ry, 14, ry * 2);
    ctx.strokeStyle = "rgba(110,95,70,0.35)"; ctx.lineWidth = 1;
    for (let k = -rx; k < rx; k += 10) { ctx.beginPath(); ctx.moveTo(x + k, y - 7); ctx.lineTo(x + k, y + 7); ctx.stroke(); }
    // 廣場
    ctx.fillStyle = "#e8dfc8"; ctx.beginPath(); ctx.ellipse(x, y, 30, 17, 0, 0, TAU); ctx.fill();
    ctx.strokeStyle = "#a99a78"; ctx.lineWidth = 1.5; ctx.stroke();
    // 房屋（有陰影的白牆藍頂）
    const houses = [[-92, -6], [-56, -40], [-40, 22], [-100, 22], [46, -42], [88, -10], [44, 26], [96, 24], [-18, -48], [20, -50]];
    houses.sort((a, b) => a[1] - b[1]).forEach(([ox, oy]) => {
      const hx = x + ox, hy = y + oy;
      ctx.fillStyle = "rgba(40,40,60,0.25)"; ctx.fillRect(hx - 8, hy + 4, 20, 4);
      ctx.fillStyle = "#faf4e6"; ctx.fillRect(hx - 9, hy - 6, 18, 11);
      ctx.fillStyle = "#e4dccb"; ctx.fillRect(hx + 3, hy - 6, 6, 11);
      ctx.fillStyle = "#3a5ad0"; ctx.beginPath(); ctx.moveTo(hx - 12, hy - 5); ctx.lineTo(hx, hy - 15); ctx.lineTo(hx + 12, hy - 5); ctx.closePath(); ctx.fill();
      ctx.fillStyle = "#2a43a6"; ctx.beginPath(); ctx.moveTo(hx, hy - 15); ctx.lineTo(hx + 12, hy - 5); ctx.lineTo(hx + 2, hy - 5); ctx.closePath(); ctx.fill();
      ctx.fillStyle = "#4a6a8a"; ctx.fillRect(hx - 5, hy - 2, 3, 3);
    });
    // 城牆
    ctx.save(); ctx.strokeStyle = "#f2ead6"; ctx.lineWidth = 5;
    ctx.beginPath(); ctx.ellipse(x, y, rx * 0.86, ry * 0.82, 0, 0, TAU); ctx.stroke();
    ctx.strokeStyle = "rgba(120,105,80,0.6)"; ctx.lineWidth = 1; ctx.stroke(); ctx.restore();
  }
  function tower(ctx, is) {
    const { x, y } = is;
    const g = ctx.createRadialGradient(x, y - 60, 0, x, y - 60, 90);
    g.addColorStop(0, "rgba(180,160,255,0.55)"); g.addColorStop(1, "rgba(180,160,255,0)");
    ctx.fillStyle = g; ctx.fillRect(x - 90, y - 150, 180, 180);
    ctx.fillStyle = "#f6efe0"; ctx.strokeStyle = "#3a3550"; ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.ellipse(x, y, 18, 9, 0, 0, TAU); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#e4dccb"; ctx.fillRect(x - 12, y - 10, 24, 10); ctx.strokeRect(x - 12, y - 10, 24, 10);
    // 晶塔：左亮右暗兩面
    ctx.fillStyle = "#e8e0ff"; ctx.beginPath(); ctx.moveTo(x - 10, y - 10); ctx.lineTo(x, y - 96); ctx.lineTo(x, y - 10); ctx.closePath(); ctx.fill();
    ctx.fillStyle = "#9d8ef0"; ctx.beginPath(); ctx.moveTo(x, y - 96); ctx.lineTo(x + 10, y - 10); ctx.lineTo(x, y - 10); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = "#3a3550"; ctx.beginPath(); ctx.moveTo(x - 10, y - 10); ctx.lineTo(x, y - 96); ctx.lineTo(x + 10, y - 10); ctx.stroke();
    // 繞著塔的小晶片
    for (const [ox, oy, s] of [[-26, -70, 5], [24, -58, 4], [-18, -40, 3.5], [30, -86, 3]]) {
      ctx.fillStyle = "#cfc4ff"; ctx.beginPath(); ctx.moveTo(x + ox, y + oy - s * 1.6); ctx.lineTo(x + ox + s, y + oy); ctx.lineTo(x + ox, y + oy + s * 1.6); ctx.lineTo(x + ox - s, y + oy); ctx.closePath(); ctx.fill();
    }
  }

  // 未開放的區：真的畫出地景，再整個去色、罩霧
  function topLater(ctx, is) {
    const { x, y, rx, ry, kind } = is, r = RA.rng(x);
    ctx.fillStyle = { crown: "#d8ccb0", arcane: "#5a5248", frost: "#cfe0ea" }[kind]; ctx.fillRect(x - rx, y - ry, rx * 2, ry * 2);
    if (kind === "crown") {
      for (let i = 0; i < 9; i++) {
        const cx = x - rx * 0.65 + i * rx * 0.16, h = 16 + r() * 26;
        ctx.fillStyle = "#b9a4ff"; ctx.beginPath(); ctx.moveTo(cx - 6, y + 8); ctx.lineTo(cx, y + 8 - h); ctx.lineTo(cx + 6, y + 8); ctx.fill();
        ctx.fillStyle = "#e8e0ff"; ctx.beginPath(); ctx.moveTo(cx - 6, y + 8); ctx.lineTo(cx, y + 8 - h); ctx.lineTo(cx, y + 8); ctx.fill();
      }
    } else if (kind === "arcane") {
      for (let i = 0; i < 9; i++) {
        const tx = x - rx * 0.62 + i * rx * 0.15, h = 18 + r() * 22;
        ctx.fillStyle = "#8a7a66"; ctx.fillRect(tx, y - h, 12, h + 6);
        ctx.fillStyle = "#4ad6c8"; ctx.fillRect(tx + 3, y - h + 4, 3, 3);
      }
    } else {
      ctx.fillStyle = "#4f8fb8"; ctx.beginPath(); ctx.ellipse(x + 20, y + 8, rx * 0.6, ry * 0.5, 0, 0, TAU); ctx.fill();
      for (let i = 0; i < 6; i++) { ctx.fillStyle = "#f2f8ff"; ctx.beginPath(); ctx.ellipse(x - rx * 0.4 + i * 30, y + (r() - 0.5) * 30, 10, 5, 0, 0, TAU); ctx.fill(); }
    }
  }

  function medallion(ctx, x, y) {
    ctx.save();
    const g = ctx.createRadialGradient(x - 4, y - 4, 2, x, y, 17);
    g.addColorStop(0, "#5b6378"); g.addColorStop(1, "#2a2f3e");
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, 16, 0, TAU); ctx.fill();
    ctx.strokeStyle = "#d8b860"; ctx.lineWidth = 2; ctx.stroke();
    ctx.strokeStyle = "rgba(216,184,96,0.5)"; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(x, y, 12.5, 0, TAU); ctx.stroke();
    ctx.strokeStyle = "#e9d9a6"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(x, y - 3, 4.5, Math.PI, 0); ctx.stroke();
    ctx.fillStyle = "#e9d9a6"; ctx.fillRect(x - 6, y - 3, 12, 9);
    ctx.fillStyle = "#2a2f3e"; ctx.fillRect(x - 1, y, 2, 4);
    ctx.restore();
  }

  function drawIsland(ctx, is) {
    const later = is.state !== "open";
    // 未開放的島畫在離屏，再去色、加霧感
    const target = later ? document.createElement("canvas") : null;
    let c = ctx;
    if (later) { target.width = W; target.height = H; c = target.getContext("2d"); }
    else { c.save(); c.filter = "saturate(1.15) contrast(1.06)"; }
    const top = blob(is.x, is.y, is.rx, is.ry, is.x * 3 + is.y);
    const pal = later ? ROCK.grey : ROCK[is.kind];
    underside(c, is, pal);
    lip(c, is, top, later ? LIP.grey : LIP[is.kind]);
    c.save(); c.clip(top);
    if (later) topLater(c, is);
    else ({ cloud: topCloud, ashen: topAshen, capital: topCapital })[is.kind](c, is);
    c.restore();
    topShade(c, is, top);
    if (!later) {
      if (is.kind === "capital") tower(c, is);
      if (is.kind === "ashen") volcano(c, is);
      // 從島緣厚度的下緣流出去
      if (is.kind === "cloud") fall(c, is.x + is.rx * 0.8, is.y + is.ry * 0.5, 150, false);
      if (is.kind === "ashen") fall(c, is.x + is.rx * 0.82, is.y + is.ry * 0.4, 110, true);
    }
    if (!later) c.restore();
    if (later) {
      ctx.save(); ctx.filter = "grayscale(0.85) brightness(0.92) contrast(0.85)"; ctx.globalAlpha = 0.82;
      ctx.drawImage(target, 0, 0); ctx.restore();
      // 霧纏住
      const r = RA.rng(is.x + 7);
      const hz = ctx.createRadialGradient(is.x, is.y, is.rx * 0.2, is.x, is.y, is.rx * 1.2);
      hz.addColorStop(0, "rgba(236,240,248,0.45)"); hz.addColorStop(1, "rgba(236,240,248,0)");
      ctx.fillStyle = hz; ctx.beginPath(); ctx.ellipse(is.x, is.y + is.ry * 0.3, is.rx * 1.25, is.ry * 1.6, 0, 0, TAU); ctx.fill();
      for (let i = 0; i < 16; i++) cloudPuff(ctx, is.x - is.rx * 1.05 + r() * is.rx * 2.1, is.y + is.ry * (0.35 + r() * 0.8), 20 + r() * 20, 0.7, [246, 246, 250], [176, 184, 206], 0.5);
      for (let i = 0; i < 5; i++) cloudPuff(ctx, is.x - is.rx * 0.9 + r() * is.rx * 1.8, is.y - is.ry * 0.1 + r() * is.ry * 0.4, 16 + r() * 12, 0.45, [246, 246, 250], [176, 184, 206], 0.45);
      if (!BACKDROP) medallion(ctx, is.x, is.y - 2);
    }
  }

  function bridge(ctx, a, b, open) {
    const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy), ux = dx / len, uy = dy / len;
    const x1 = a.x + ux * a.rx * 0.82, y1 = a.y + uy * a.ry * 0.82, x2 = b.x - ux * b.rx * 0.82, y2 = b.y - uy * b.ry * 0.82;
    const mx = (x1 + x2) / 2, my = (y1 + y2) / 2 + 22;
    const at = (t) => { const q = (1 - t) * (1 - t), m = 2 * t * (1 - t), u = t * t; return [q * x1 + m * mx + u * x2, q * y1 + m * my + u * y2]; };
    ctx.save();
    if (!open) {
      // 未開放：一串淡淡的光點
      for (let t = 0.08; t < 0.95; t += 0.06) {
        const [cx, cy] = at(t);
        const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, 5);
        g.addColorStop(0, "rgba(255,250,230,0.7)"); g.addColorStop(1, "rgba(255,250,230,0)");
        ctx.fillStyle = g; ctx.fillRect(cx - 5, cy - 5, 10, 10);
      }
      ctx.restore(); return;
    }
    const nx = -uy, ny = ux;
    // 橋板（有陰影）
    for (let t = 0.02; t < 0.99; t += 0.035) {
      const [cx, cy] = at(t);
      ctx.strokeStyle = "rgba(40,30,20,0.35)"; ctx.lineWidth = 4.5;
      ctx.beginPath(); ctx.moveTo(cx - nx * 7, cy - ny * 7 + 2); ctx.lineTo(cx + nx * 7, cy + ny * 7 + 2); ctx.stroke();
      ctx.strokeStyle = (Math.round(t * 100) % 2) ? "#c49a62" : "#b08452"; ctx.lineWidth = 3.5;
      ctx.beginPath(); ctx.moveTo(cx - nx * 7, cy - ny * 7); ctx.lineTo(cx + nx * 7, cy + ny * 7); ctx.stroke();
    }
    // 繩索與欄柱
    for (const off of [-8, 8]) {
      ctx.strokeStyle = "#3e2c1c"; ctx.lineWidth = 1.6;
      ctx.beginPath(); ctx.moveTo(x1 + nx * off, y1 + ny * off - 6); ctx.quadraticCurveTo(mx + nx * off, my + ny * off - 10, x2 + nx * off, y2 + ny * off - 6); ctx.stroke();
    }
    for (const [px, py] of [[x1, y1], [x2, y2]]) {
      for (const off of [-8, 8]) {
        ctx.fillStyle = "#4a3523"; ctx.fillRect(px + nx * off - 2, py + ny * off - 10, 4, 12);
        ctx.fillStyle = "#e0c27a"; ctx.beginPath(); ctx.arc(px + nx * off, py + ny * off - 11, 2.2, 0, TAU); ctx.fill();
      }
    }
    ctx.restore();
  }

  // ---------- 字牌 ----------
  function plaque(ctx, is, ly) {
    const later = is.state !== "open";
    ctx.font = `bold 19px ${SERIF}`;
    const nameW = ctx.measureText(is.name).width;
    const sub = later ? COND[is.state] : is.lv ? `Lv ${is.lv}` : is.town;
    ctx.font = `bold 12px ${FONT}`;
    const subW = ctx.measureText(sub).width;
    const w = Math.max(nameW, subW) + 44, h = 50, x = is.x - w / 2, y = ly;
    ctx.save();
    ctx.shadowColor = "rgba(0,0,0,0.35)"; ctx.shadowBlur = 8; ctx.shadowOffsetY = 3;
    const g = ctx.createLinearGradient(0, y, 0, y + h);
    g.addColorStop(0, later ? "#4a4e5c" : "#2c3550"); g.addColorStop(1, later ? "#33363f" : "#1b2136");
    ctx.fillStyle = g; RA.roundRect(ctx, x, y, w, h, 6); ctx.fill();
    ctx.restore();
    ctx.strokeStyle = later ? "#9a9ca6" : "#d8b860"; ctx.lineWidth = 1.6; RA.roundRect(ctx, x, y, w, h, 6); ctx.stroke();
    ctx.strokeStyle = later ? "rgba(154,156,166,0.45)" : "rgba(216,184,96,0.45)"; ctx.lineWidth = 1; RA.roundRect(ctx, x + 3, y + 3, w - 6, h - 6, 4); ctx.stroke();
    // 兩側小菱形
    for (const sx of [x, x + w]) {
      ctx.fillStyle = later ? "#9a9ca6" : "#d8b860";
      ctx.beginPath(); ctx.moveTo(sx, y + h / 2 - 6); ctx.lineTo(sx + 5, y + h / 2); ctx.lineTo(sx, y + h / 2 + 6); ctx.lineTo(sx - 5, y + h / 2); ctx.closePath(); ctx.fill();
    }
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.font = `bold 19px ${SERIF}`; ctx.fillStyle = later ? "#d6d8de" : "#fbf3dc"; ctx.fillText(is.name, is.x, y + 18);
    ctx.font = `bold 12px ${FONT}`; ctx.fillStyle = later ? "#a8acb6" : "#f2c96a"; ctx.fillText(sub, is.x, y + 37);
    return y + h;
  }
  function teleportButton(ctx, text, x, y) {
    ctx.font = `bold 13px ${FONT}`;
    const w = ctx.measureText(text).width + 40, h = 26, bx = x - w / 2;
    ctx.save(); ctx.shadowColor = "rgba(40,140,220,0.6)"; ctx.shadowBlur = 10;
    const g = ctx.createLinearGradient(0, y, 0, y + h);
    g.addColorStop(0, "#6fd0ff"); g.addColorStop(1, "#2a8fd6");
    ctx.fillStyle = g; RA.roundRect(ctx, bx, y, w, h, 13); ctx.fill(); ctx.restore();
    ctx.strokeStyle = "#0f3a5a"; ctx.lineWidth = 1.4; RA.roundRect(ctx, bx, y, w, h, 13); ctx.stroke();
    const cx = bx + 14, cy = y + h / 2;
    ctx.fillStyle = "#e9fbff"; ctx.beginPath(); ctx.moveTo(cx, cy - 7); ctx.lineTo(cx + 4.5, cy); ctx.lineTo(cx, cy + 7); ctx.lineTo(cx - 4.5, cy); ctx.closePath(); ctx.fill();
    ctx.fillStyle = "#082a40"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(text, x + 8, y + h / 2 + 1);
  }
  function hereTag(ctx, text, x, y) {
    ctx.font = `bold 12px ${FONT}`;
    const w = ctx.measureText(text).width + 30, h = 22;
    ctx.fillStyle = "rgba(20,30,50,0.75)"; RA.roundRect(ctx, x - w / 2, y, w, h, 11); ctx.fill();
    ctx.strokeStyle = "#5fb0ff"; ctx.lineWidth = 1.2; ctx.stroke();
    ctx.fillStyle = "#2f8cff"; ctx.strokeStyle = "#fff"; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(x - w / 2 + 12, y + h / 2, 4.5, 0, TAU); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#e6f2ff"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(text, x + 6, y + h / 2 + 1);
  }

  function titlePlaque(ctx) {
    const x = 44, y = 38, w = 330, h = 62;
    ctx.save(); ctx.shadowColor = "rgba(0,0,0,0.35)"; ctx.shadowBlur = 10; ctx.shadowOffsetY = 3;
    const g = ctx.createLinearGradient(0, y, 0, y + h); g.addColorStop(0, "#2c3550"); g.addColorStop(1, "#1b2136");
    ctx.fillStyle = g; RA.roundRect(ctx, x, y, w, h, 8); ctx.fill(); ctx.restore();
    ctx.strokeStyle = "#d8b860"; ctx.lineWidth = 1.8; RA.roundRect(ctx, x, y, w, h, 8); ctx.stroke();
    ctx.strokeStyle = "rgba(216,184,96,0.45)"; ctx.lineWidth = 1; RA.roundRect(ctx, x + 4, y + 4, w - 8, h - 8, 5); ctx.stroke();
    ctx.textAlign = "left"; ctx.textBaseline = "middle";
    ctx.font = `bold 30px ${SERIF}`; ctx.fillStyle = "#fbf3dc"; ctx.fillText("大世界", x + 20, y + h / 2 + 1);
    ctx.font = `bold 13px ${FONT}`; ctx.fillStyle = "#f2c96a"; ctx.fillText("在城鎮裡：點城鎮直接傳送", x + 132, y + h / 2 + 1);
  }
  function legend(ctx) {
    const w = 330, h = 40, x = 44, y = H - 44 - h;
    ctx.fillStyle = "rgba(27,33,54,0.85)"; RA.roundRect(ctx, x, y, w, h, 8); ctx.fill();
    ctx.strokeStyle = "rgba(216,184,96,0.7)"; ctx.lineWidth = 1.2; ctx.stroke();
    ctx.font = `13px ${FONT}`; ctx.textAlign = "left"; ctx.textBaseline = "middle";
    const cy = y + h / 2;
    ctx.fillStyle = "#86b862"; ctx.strokeStyle = "#d8b860"; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.arc(x + 20, cy, 6.5, 0, TAU); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#f2f4f7"; ctx.fillText("已開放（點了看區域圖）", x + 32, cy);
    ctx.save(); ctx.translate(x + 206, cy); ctx.scale(0.55, 0.55); medallion(ctx, 0, 0); ctx.restore();
    ctx.fillStyle = "#f2f4f7"; ctx.fillText("未開放", x + 220, cy);
    ctx.fillStyle = "#2f8cff"; ctx.strokeStyle = "#fff"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(x + 280, cy, 5.5, 0, TAU); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#f2f4f7"; ctx.fillText("自己", x + 291, cy);
  }
  function frame(ctx) {
    // 外圍暗角
    const v = ctx.createRadialGradient(W / 2, H / 2, H * 0.45, W / 2, H / 2, W * 0.7);
    v.addColorStop(0, "rgba(0,0,0,0)"); v.addColorStop(1, "rgba(20,10,30,0.28)");
    ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = "#4a3020"; ctx.lineWidth = 24; ctx.strokeRect(12, 12, W - 24, H - 24);
    const g = ctx.createLinearGradient(0, 0, W, H); g.addColorStop(0, "#8a5f38"); g.addColorStop(1, "#5a3c24");
    ctx.strokeStyle = g; ctx.lineWidth = 8; ctx.strokeRect(20, 20, W - 40, H - 40);
    ctx.strokeStyle = "#d8b860"; ctx.lineWidth = 1.6; ctx.strokeRect(26, 26, W - 52, H - 52);
    // 四角金飾
    for (const [cx, cy, sx, sy] of [[26, 26, 1, 1], [W - 26, 26, -1, 1], [26, H - 26, 1, -1], [W - 26, H - 26, -1, -1]]) {
      ctx.save(); ctx.translate(cx, cy); ctx.scale(sx, sy);
      ctx.strokeStyle = "#e6c878"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(0, 34); ctx.lineTo(0, 0); ctx.lineTo(34, 0); ctx.stroke();
      ctx.beginPath(); ctx.arc(10, 10, 6, 0, TAU); ctx.stroke();
      ctx.fillStyle = "#e6c878"; ctx.beginPath(); ctx.arc(10, 10, 2.5, 0, TAU); ctx.fill();
      ctx.restore();
    }
  }

  function draw(canvas) {
    canvas.width = W; canvas.height = H;
    const ctx = canvas.getContext("2d");
    sky(ctx);
    islets(ctx);
    lowerClouds(ctx);
    const order = ISLANDS.slice().sort((a, b) => a.y - b.y);
    for (const is of order) shadowBelow(ctx, is);
    const cap = ISLANDS[0];
    for (const is of ISLANDS.slice(1)) if (is.state !== "open") bridge(ctx, cap, is, false);
    for (const is of order) drawIsland(ctx, is);
    for (const is of ISLANDS.slice(1)) if (is.state === "open") bridge(ctx, cap, is, true);
    frontClouds(ctx);
    for (const is of ISLANDS) {
      if (is.here) RA.selfMark(ctx, "painted", is.x - is.rx * 0.55, is.y + is.ry * 0.3 - 10);
      const ly = is.y + is.ry + is.ry * 0.42 + 12;
      const bottom = plaque(ctx, is, ly);
      if (is.state === "open") {
        if (is.here) hereTag(ctx, `你在${is.town}`, is.x, bottom + 6);
        else teleportButton(ctx, `傳送到${is.town}`, is.x, bottom + 6);
      }
    }
    titlePlaque(ctx);
    legend(ctx);
    frame(ctx);
  }

  // 背景版（首頁、建角用）：同一套天空、浮島、岩層、瀑布、雲層，不畫字牌、按鈕、圖例、外框、鎖頭徽章。
  // t：毫秒，給每座島 ±3px 的漂浮（同 6F-ART1b）；減少動態時傳 0。
  let BACKDROP = false;
  function drawBackdrop(canvas, t = 0) {
    canvas.width = W; canvas.height = H;
    const ctx = canvas.getContext("2d");
    BACKDROP = true;
    sky(ctx);
    islets(ctx);
    lowerClouds(ctx);
    const order = ISLANDS.slice().sort((a, b) => a.y - b.y);
    for (const is of order) shadowBelow(ctx, is);
    const cap = ISLANDS[0];
    for (const is of ISLANDS.slice(1)) if (is.state !== "open") bridge(ctx, cap, is, false);
    for (const is of order) {
      const dy = 3 * Math.sin((t / (5000 + (is.x % 1000))) * TAU + is.y);
      ctx.save(); ctx.translate(0, dy); drawIsland(ctx, is); ctx.restore();
    }
    for (const is of ISLANDS.slice(1)) if (is.state === "open") bridge(ctx, cap, is, true);
    frontClouds(ctx);
    BACKDROP = false;
  }

  window.WorldPaintedArt = { draw, drawBackdrop, W, H, ISLANDS };
})();
