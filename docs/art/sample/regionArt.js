// 雲嶺區域插畫樣張：兩種風格（scroll＝古地圖卷軸、painted＝俯視彩繪）。全部程式繪製。
// 地點座標照 content/world/maps/cloud_ridge.yaml 的 pos（0～100）。
(function () {
  const W = 1280, H = 860, MX = 80, MY = 70;
  const CLOUD_LOC = [
    { id: "mist_ferry", name: "霧渡鎮", kind: "town", lv: "", pos: [10, 80] },
    { id: "ferry_steps", name: "渡口石階", kind: "camp", lv: "1", pos: [25, 85] },
    { id: "bamboo_path", name: "竹林小徑", kind: "camp", lv: "1～2", pos: [30, 65] },
    { id: "rain_terraces", name: "雨中梯田", kind: "camp", lv: "2", pos: [45, 70] },
    { id: "mist_temple_gate", name: "青霧觀山門", kind: "village", lv: "2", pos: [50, 55] },
    { id: "hunter_hut", name: "獵戶小屋", kind: "village", lv: "2", pos: [15, 55] },
    { id: "cliff_gang_fort", name: "斷崖幫寨", kind: "camp", lv: "3", pos: [60, 80] },
    { id: "old_pine_altar", name: "古松祭壇", kind: "altar", lv: "3", pos: [35, 45] },
    { id: "cloud_sea_bridge", name: "雲海吊橋", kind: "camp", lv: "3～4", pos: [60, 45] },
    { id: "herb_valley", name: "藥師谷", kind: "ruin", lv: "4", pos: [75, 65] },
    { id: "elixir_cave", name: "丹爐洞", kind: "secret", lv: "5", pos: [90, 70], hidden: true },
    { id: "north_slope", name: "北坡獵場", kind: "elite_lair", lv: "4～5", pos: [25, 25] },
    { id: "winter_lake", name: "冬湖", kind: "camp", lv: "4", pos: [15, 40] },
    { id: "sword_tomb", name: "劍冢", kind: "ruin", lv: "5", pos: [70, 30] },
    { id: "crystal_rift", name: "源晶裂痕", kind: "anomaly", lv: "5", pos: [50, 20] },
    { id: "crane_cliff", name: "鶴歸崖", kind: "secret", lv: "6", pos: [30, 8], hidden: true },
    { id: "cloud_summit", name: "雲頂觀", kind: "boss", lv: "6", pos: [75, 10] },
    { id: "ashen_ferry", name: "往灰燼荒原的渡口", kind: "gate", lv: "", pos: [5, 95] },
  ];
  const CLOUD_EDGES = [
    ["mist_ferry", "ferry_steps"], ["mist_ferry", "hunter_hut"], ["mist_ferry", "ashen_ferry"],
    ["ferry_steps", "bamboo_path"], ["bamboo_path", "hunter_hut"], ["bamboo_path", "rain_terraces"],
    ["rain_terraces", "mist_temple_gate"], ["rain_terraces", "cliff_gang_fort"], ["rain_terraces", "old_pine_altar"],
    ["hunter_hut", "winter_lake"], ["old_pine_altar", "cloud_sea_bridge"], ["mist_temple_gate", "cloud_sea_bridge"],
    ["cliff_gang_fort", "herb_valley"], ["cloud_sea_bridge", "herb_valley"], ["cloud_sea_bridge", "sword_tomb"],
    ["herb_valley", "elixir_cave"], ["winter_lake", "north_slope"], ["north_slope", "crane_cliff"],
    ["north_slope", "crystal_rift"], ["sword_tomb", "crystal_rift"], ["crystal_rift", "cloud_summit"],
  ];
  // 樣張用的玩家狀態
  const CLOUD_STATE = {
    visited: ["mist_ferry", "ferry_steps", "bamboo_path", "rain_terraces", "cliff_gang_fort", "cloud_sea_bridge",
      "hunter_hut", "mist_temple_gate", "old_pine_altar", "sword_tomb"],
    cleared: ["ferry_steps", "bamboo_path", "rain_terraces", "cliff_gang_fort"],
    here: "rain_terraces",
    quests: ["mist_temple_gate", "sword_tomb"],
    stones: [["mist_ferry", true], ["rain_terraces", true], ["cloud_sea_bridge", false]],
    trail: ["rain_terraces", "mist_temple_gate"],
  };

  // 目前畫的區域；draw() 依 opts.region 換掉
  let LOC = CLOUD_LOC, EDGES = CLOUD_EDGES, STATE = CLOUD_STATE, REGION = null;
  let byId = Object.fromEntries(LOC.map((l) => [l.id, l]));
  const P = (x, y) => [MX + (x / 100) * (W - 2 * MX), MY + (y / 100) * (H - 2 * MY)];
  const LP = (l) => P(l.pos[0], l.pos[1]);
  function rng(seed) {
    return function () {
      seed = (seed + 0x6d2b79f5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function fogOf(id) {
    if (STATE.visited.includes(id)) return "visited";
    if (byId[id].hidden) return "hidden";
    const adj = EDGES.some(([a, b]) => (a === id && STATE.visited.includes(b)) || (b === id && STATE.visited.includes(a)));
    return adj ? "adjacent" : "far";
  }

  // ---------- 調色盤 ----------
  const PAL = {
    scroll: {
      ink: "#2a2218", base: "#ead9ae", fog: "#e2cf9e", road: "#8a2b1c", label: "#2a2218", halo: "#efe2bd",
      font: '"DFKai-SB","KaiTi","BiauKai",serif', grass: "rgba(110,140,90,0.18)",
    },
    painted: {
      ink: "#27303a", base: "#7fa65a", fog: "#eef1f4", road: "#d9b679", label: "#1d2530", halo: "#ffffff",
      font: '"Microsoft JhengHei","PingFang TC",sans-serif', grass: "#7fa65a",
    },
  };

  // ---------- 地景 ----------
  function base(ctx, s) {
    const r = rng(11);
    if (s === "scroll") {
      ctx.fillStyle = PAL.scroll.base;
      ctx.fillRect(0, 0, W, H);
      for (let i = 0; i < 70; i++) {
        const x = r() * W, y = r() * H, rad = 30 + r() * 140;
        const g = ctx.createRadialGradient(x, y, 0, x, y, rad);
        g.addColorStop(0, `rgba(150,110,60,${0.04 + r() * 0.06})`);
        g.addColorStop(1, "rgba(150,110,60,0)");
        ctx.fillStyle = g;
        ctx.fillRect(x - rad, y - rad, rad * 2, rad * 2);
      }
      ctx.strokeStyle = "rgba(120,90,50,0.08)";
      ctx.lineWidth = 1;
      for (let i = 0; i < 400; i++) {
        const x = r() * W, y = r() * H;
        ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + 6 + r() * 14, y + (r() - 0.5) * 3); ctx.stroke();
      }
      // 淡淡的青綠暈染：南方草地
      for (let i = 0; i < 40; i++) {
        const [x, y] = P(r() * 100, 45 + r() * 50), rad = 40 + r() * 90;
        const g = ctx.createRadialGradient(x, y, 0, x, y, rad);
        g.addColorStop(0, "rgba(120,150,95,0.10)");
        g.addColorStop(1, "rgba(120,150,95,0)");
        ctx.fillStyle = g; ctx.fillRect(x - rad, y - rad, rad * 2, rad * 2);
      }
    } else {
      const g = ctx.createLinearGradient(0, 0, 0, H);
      g.addColorStop(0, "#8e9a8c"); g.addColorStop(0.35, "#86a06a"); g.addColorStop(1, "#78a552");
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
      for (let i = 0; i < 260; i++) {
        const x = r() * W, y = r() * H, rad = 15 + r() * 60;
        ctx.fillStyle = r() < 0.5 ? "rgba(60,100,40,0.10)" : "rgba(180,200,120,0.10)";
        ctx.beginPath(); ctx.ellipse(x, y, rad, rad * 0.6, r() * 3, 0, Math.PI * 2); ctx.fill();
      }
    }
  }

  function pathThrough(ctx, pts) {
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length - 1; i++) {
      const mx = (pts[i][0] + pts[i + 1][0]) / 2, my = (pts[i][1] + pts[i + 1][1]) / 2;
      ctx.quadraticCurveTo(pts[i][0], pts[i][1], mx, my);
    }
    const l = pts[pts.length - 1];
    ctx.lineTo(l[0], l[1]);
  }

  function river(ctx, s) {
    const pts = [[-2, 91], [8, 90], [18, 92], [32, 94], [48, 91], [62, 90], [74, 86], [86, 80], [102, 77]].map((p) => P(p[0], p[1]));
    ctx.lineCap = "round"; ctx.lineJoin = "round";
    if (s === "scroll") {
      pathThrough(ctx, pts); ctx.strokeStyle = "rgba(110,150,170,0.35)"; ctx.lineWidth = 30; ctx.stroke();
      ctx.save(); ctx.translate(0, -12); pathThrough(ctx, pts); ctx.strokeStyle = PAL.scroll.ink; ctx.lineWidth = 1.8; ctx.stroke(); ctx.restore();
      ctx.save(); ctx.translate(0, 12); pathThrough(ctx, pts); ctx.strokeStyle = PAL.scroll.ink; ctx.lineWidth = 1.8; ctx.stroke(); ctx.restore();
      // 水波
      ctx.strokeStyle = "rgba(42,34,24,0.55)"; ctx.lineWidth = 1.2;
      for (let i = 0; i < pts.length - 1; i++) {
        const [x1, y1] = pts[i], [x2, y2] = pts[i + 1];
        for (let t = 0.2; t < 1; t += 0.4) {
          const x = x1 + (x2 - x1) * t, y = y1 + (y2 - y1) * t;
          ctx.beginPath(); ctx.arc(x, y + 2, 6, Math.PI * 1.1, Math.PI * 1.9); ctx.stroke();
        }
      }
    } else {
      pathThrough(ctx, pts); ctx.strokeStyle = "#5e8a4a"; ctx.lineWidth = 36; ctx.stroke();
      pathThrough(ctx, pts); ctx.strokeStyle = "#3f7fb0"; ctx.lineWidth = 26; ctx.stroke();
      pathThrough(ctx, pts); ctx.strokeStyle = "#69a8d4"; ctx.lineWidth = 14; ctx.stroke();
      ctx.setLineDash([10, 18]);
      pathThrough(ctx, pts); ctx.strokeStyle = "rgba(255,255,255,0.55)"; ctx.lineWidth = 2; ctx.stroke();
      ctx.setLineDash([]);
      // 河上的霧
      const r = rng(5);
      for (let i = 0; i < pts.length; i++) {
        const [x, y] = pts[i];
        const g = ctx.createRadialGradient(x, y, 0, x, y, 50);
        g.addColorStop(0, `rgba(255,255,255,${0.25 + r() * 0.2})`); g.addColorStop(1, "rgba(255,255,255,0)");
        ctx.fillStyle = g; ctx.fillRect(x - 60, y - 60, 120, 120);
      }
    }
  }

  function lake(ctx, s) {
    const [x, y] = P(14, 37);
    ctx.beginPath(); ctx.ellipse(x, y, 82, 46, -0.1, 0, Math.PI * 2);
    if (s === "scroll") {
      ctx.fillStyle = "rgba(140,170,180,0.25)"; ctx.fill();
      ctx.strokeStyle = PAL.scroll.ink; ctx.lineWidth = 1.8; ctx.stroke();
      ctx.lineWidth = 1; ctx.strokeStyle = "rgba(42,34,24,0.4)";
      for (let i = -2; i <= 2; i++) { ctx.beginPath(); ctx.moveTo(x - 50, y + i * 12); ctx.lineTo(x + 50, y + i * 12); ctx.stroke(); }
    } else {
      ctx.fillStyle = "#cfe4ee"; ctx.fill();
      ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 4; ctx.stroke();
      ctx.strokeStyle = "rgba(120,160,190,0.7)"; ctx.lineWidth = 1.2;
      const r = rng(9);
      for (let i = 0; i < 8; i++) {
        ctx.beginPath(); let px = x + (r() - 0.5) * 100, py = y + (r() - 0.5) * 50; ctx.moveTo(px, py);
        for (let k = 0; k < 3; k++) { px += (r() - 0.5) * 30; py += (r() - 0.5) * 16; ctx.lineTo(px, py); }
        ctx.stroke();
      }
    }
  }

  function terraces(ctx, s) {
    const [cx, cy] = P(46, 77);
    for (let i = 9; i >= 0; i--) {
      const rad = 26 + i * 11;
      ctx.beginPath(); ctx.ellipse(cx, cy, rad * 1.5, rad, 0, Math.PI * 1.02, Math.PI * 1.98);
      if (s === "scroll") {
        ctx.strokeStyle = PAL.scroll.ink; ctx.lineWidth = 1.3; ctx.stroke();
        ctx.strokeStyle = "rgba(110,150,90,0.25)"; ctx.lineWidth = 8; ctx.stroke();
      } else {
        ctx.strokeStyle = i % 2 ? "#9ccc6e" : "#b6dc87"; ctx.lineWidth = 10; ctx.stroke();
        ctx.strokeStyle = "rgba(210,235,245,0.9)"; ctx.lineWidth = 2; ctx.stroke();
      }
    }
  }

  function bambooCluster(ctx, s, x, y, r) {
    const n = 3 + Math.floor(r() * 3);
    for (let i = 0; i < n; i++) {
      const bx = x + (i - n / 2) * 5 + r() * 2, h = 26 + r() * 14;
      const sc = s === "scroll";
      ctx.strokeStyle = sc ? "#3b5a35" : "#7fb24e"; ctx.lineWidth = sc ? 1.6 : 2.2;
      ctx.beginPath(); ctx.moveTo(bx, y); ctx.lineTo(bx + 2, y - h); ctx.stroke();
      ctx.strokeStyle = sc ? "#3b5a35" : "#4d7f33"; ctx.lineWidth = sc ? 1.6 : 1.4;
      for (let k = 8; k < h; k += 8) { ctx.beginPath(); ctx.moveTo(bx - 2, y - k); ctx.lineTo(bx + 3, y - k); ctx.stroke(); }
      const nl = sc ? 3 : 5;
      for (let k = 0; k < nl; k++) {
        ctx.fillStyle = sc ? "rgba(59,90,53,0.8)" : ["#2f6b34", "#4f9a44", "#6cb455"][k % 3];
        ctx.save(); ctx.translate(bx + 2, y - h + k * 5); ctx.rotate(-0.6 + r() * 1.2 + (k % 2 ? 0.9 : -0.9));
        ctx.beginPath(); ctx.ellipse(6, 0, sc ? 7 : 8, sc ? 1.8 : 2.4, 0, 0, Math.PI * 2); ctx.fill(); ctx.restore();
      }
    }
  }
  function bamboo(ctx, s) {
    const r = rng(21);
    const items = [];
    for (let i = 0; i < 70; i++) {
      const a = r() * Math.PI * 2, d = Math.sqrt(r()) * 13;
      const px = 27 + Math.cos(a) * d * 1.3, py = 63 + Math.sin(a) * d * 0.8;
      if (Math.hypot(px - 30, py - 65) < 4.5) continue;
      items.push(P(px, py));
    }
    items.sort((a, b) => a[1] - b[1]).forEach(([x, y]) => bambooCluster(ctx, s, x, y, r));
  }

  function pine(ctx, s, x, y, k) {
    if (s === "scroll") {
      ctx.strokeStyle = PAL.scroll.ink; ctx.lineWidth = 1.3;
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, y - 18 * k); ctx.stroke();
      ctx.fillStyle = "rgba(60,90,70,0.55)";
      for (let i = 0; i < 3; i++) {
        const yy = y - 6 * k - i * 5 * k, w = (10 - i * 3) * k;
        ctx.beginPath(); ctx.moveTo(x - w, yy); ctx.lineTo(x, yy - 6 * k); ctx.lineTo(x + w, yy); ctx.closePath(); ctx.fill(); ctx.stroke();
      }
    } else {
      ctx.fillStyle = "#5a3c24"; ctx.fillRect(x - 1.5, y - 5, 3, 5);
      for (let i = 0; i < 3; i++) {
        const yy = y - 4 - i * 6 * k, w = (11 - i * 3) * k;
        ctx.fillStyle = i % 2 ? "#2f5a3a" : "#3b6d45";
        ctx.beginPath(); ctx.moveTo(x - w, yy); ctx.lineTo(x, yy - 10 * k); ctx.lineTo(x + w, yy); ctx.closePath(); ctx.fill();
      }
    }
  }
  function forests(ctx, s) {
    const r = rng(33);
    const spots = [[25, 28, 10], [35, 46, 7], [12, 52, 7], [48, 50, 6], [82, 60, 8], [22, 74, 6], [5, 68, 6], [66, 70, 6]];
    const items = [];
    for (const [cx, cy, rad] of spots) {
      for (let i = 0; i < 16; i++) {
        const a = r() * Math.PI * 2, d = Math.sqrt(r()) * rad;
        const px = cx + Math.cos(a) * d * 1.2, py = cy + Math.sin(a) * d * 0.7;
        if (LOC.some((l) => Math.hypot(l.pos[0] - px, l.pos[1] - py) < 4.5)) continue;
        items.push([...P(px, py), 0.8 + r() * 0.5]);
      }
    }
    items.sort((a, b) => a[1] - b[1]).forEach(([x, y, k]) => pine(ctx, s, x, y, k));
  }

  function mountain(ctx, s, x, y, h, r, snowy, col = ["#9aa596", "#68756a"]) {
    const w = h * (0.8 + r() * 0.3), px = x + (r() - 0.5) * w * 0.3;
    if (s === "scroll") {
      const g = ctx.createLinearGradient(0, y - h, 0, y);
      g.addColorStop(0, "rgba(90,140,125,0.55)"); g.addColorStop(1, "rgba(90,140,125,0)");
      ctx.fillStyle = PAL.scroll.base;
      ctx.beginPath(); ctx.moveTo(x - w, y); ctx.quadraticCurveTo(px - w * 0.3, y - h * 0.6, px, y - h);
      ctx.quadraticCurveTo(px + w * 0.35, y - h * 0.55, x + w, y); ctx.closePath(); ctx.fill();
      ctx.fillStyle = g; ctx.fill();
      ctx.strokeStyle = PAL.scroll.ink; ctx.lineWidth = 1.8; ctx.stroke();
      ctx.lineWidth = 1; ctx.strokeStyle = "rgba(42,34,24,0.55)";
      for (let i = 1; i <= 4; i++) {
        const t = i / 5;
        ctx.beginPath(); ctx.moveTo(px + w * 0.12 * t, y - h * (1 - t * 0.9)); ctx.lineTo(px + w * 0.45 * t, y - h * (1 - t) * 0.7); ctx.stroke();
      }
    } else {
      ctx.fillStyle = col[0];
      ctx.beginPath(); ctx.moveTo(x - w, y); ctx.lineTo(px, y - h); ctx.lineTo(px + w * 0.05, y); ctx.closePath(); ctx.fill();
      ctx.fillStyle = col[1];
      ctx.beginPath(); ctx.moveTo(px, y - h); ctx.lineTo(x + w, y); ctx.lineTo(px + w * 0.05, y); ctx.closePath(); ctx.fill();
      if (snowy) {
        const t = 0.38;
        ctx.fillStyle = "#f4f7fb";
        ctx.beginPath(); ctx.moveTo(px, y - h);
        ctx.lineTo(px - (px - (x - w)) * t, y - h + h * t); ctx.lineTo(px - w * 0.1, y - h + h * t * 0.7);
        ctx.lineTo(px + w * 0.1, y - h + h * t); ctx.lineTo(px + (x + w - px) * t, y - h + h * t * 0.9); ctx.closePath(); ctx.fill();
        ctx.fillStyle = "rgba(170,190,210,0.6)";
        ctx.beginPath(); ctx.moveTo(px, y - h); ctx.lineTo(px + (x + w - px) * t, y - h + h * t * 0.9); ctx.lineTo(px + w * 0.1, y - h + h * t); ctx.closePath(); ctx.fill();
      }
      ctx.strokeStyle = "rgba(40,48,58,0.7)"; ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.moveTo(x - w, y); ctx.lineTo(px, y - h); ctx.lineTo(x + w, y); ctx.stroke();
    }
  }
  function mountains(ctx, s) {
    const r = rng(47);
    const list = [];
    for (let gx = -4; gx <= 104; gx += 6.5) {
      for (let gy = 6; gy <= 38; gy += 7) {
        const px = gx + (r() - 0.5) * 4, py = gy + (r() - 0.5) * 4;
        const dSummit = Math.hypot(px - 75, py - 10);
        if (LOC.some((l) => Math.hypot(l.pos[0] - px, (l.pos[1] - py) * 1.3) < 5)) continue;
        if (px > 6 && px < 24 && py > 31) continue; // 冬湖
        if (Math.abs((px - 50) * 0.6 - (py - 28) * 0.4) < 2 && py > 26) continue; // 峽谷
        const h = 46 + (38 - py) * 1.6 + Math.max(0, 30 - dSummit) * 3 + r() * 20;
        list.push([px, py, h]);
      }
    }
    // 東側的崖、斷崖幫寨背後的石壁
    for (let i = 0; i < 9; i++) list.push([84 + r() * 18, 42 + r() * 22, 40 + r() * 25]);
    for (let i = 0; i < 4; i++) list.push([52 + r() * 6, 84 + r() * 3, 26 + r() * 10]);
    list.sort((a, b) => a[1] - b[1]).forEach(([px, py, h]) => {
      const [x, y] = P(px, py);
      mountain(ctx, s, x, y, h, r, py < 30);
    });
  }

  // 祥雲捲紋
  function curl(ctx, x, y, k, color, lw) {
    ctx.strokeStyle = color; ctx.lineWidth = lw;
    ctx.beginPath(); ctx.arc(x, y, 9 * k, Math.PI * 0.2, Math.PI * 1.9); ctx.stroke();
    ctx.beginPath(); ctx.arc(x + 2 * k, y + 1 * k, 4.5 * k, Math.PI * 0.9, Math.PI * 2.3); ctx.stroke();
    ctx.beginPath(); ctx.arc(x + 20 * k, y + 3 * k, 7 * k, Math.PI * 1.0, Math.PI * 2.4); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x - 10 * k, y + 7 * k); ctx.quadraticCurveTo(x + 10 * k, y + 14 * k, x + 34 * k, y + 8 * k); ctx.stroke();
  }
  function puff(ctx, x, y, rad, a, col = [255, 255, 255]) {
    const [r, g0, b] = col, c2 = `${r - 15},${g0 - 11},${b - 7}`, c3 = `${r - 25},${g0 - 19},${b - 13}`;
    const g = ctx.createRadialGradient(x, y - rad * 0.3, rad * 0.1, x, y, rad);
    g.addColorStop(0, `rgba(${r},${g0},${b},${a})`); g.addColorStop(0.7, `rgba(${c2},${a * 0.85})`); g.addColorStop(1, `rgba(${c3},0)`);
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, rad, 0, Math.PI * 2); ctx.fill();
  }

  function gorge(ctx, s) {
    const a = P(49, 27), b = P(71, 61);
    const dx = b[0] - a[0], dy = b[1] - a[1], len = Math.hypot(dx, dy), nx = -dy / len, ny = dx / len;
    const half = 34;
    const r = rng(57);
    const edge = (sign) => {
      const pts = [];
      for (let t = 0; t <= 1.0001; t += 0.04) {
        const wob = Math.sin(t * 9 + sign) * 9 + (r() - 0.5) * 10, taper = Math.min(1, t * 5, (1 - t) * 5) * 0.6 + 0.4;
        pts.push([a[0] + dx * t + nx * sign * (half + wob) * taper, a[1] + dy * t + ny * sign * (half + wob) * taper]);
      }
      return pts;
    };
    const L = edge(1), R = edge(-1);
    const gp = new Path2D();
    L.forEach((p, i) => (i ? gp.lineTo(p[0], p[1]) : gp.moveTo(p[0], p[1]))); R.slice().reverse().forEach((p) => gp.lineTo(p[0], p[1])); gp.closePath();
    if (s === "scroll") {
      ctx.fillStyle = "rgba(200,190,160,0.6)"; ctx.fill(gp);
      ctx.strokeStyle = PAL.scroll.ink; ctx.lineWidth = 2; ctx.stroke(gp);
      ctx.save(); ctx.clip(gp);
      for (let t = 0.05; t < 1; t += 0.12) curl(ctx, a[0] + dx * t - 14, a[1] + dy * t + (r() - 0.5) * 20, 0.9, "rgba(42,34,24,0.6)", 1.3);
      ctx.restore();
    } else {
      ctx.fillStyle = "#33404c"; ctx.fill(gp);
      ctx.save(); ctx.clip(gp);
      ctx.strokeStyle = "#6f6152"; ctx.lineWidth = 22; ctx.stroke(gp);
      ctx.strokeStyle = "#54493e"; ctx.lineWidth = 10; ctx.stroke(gp);
      for (let t = 0; t < 1.05; t += 0.035) puff(ctx, a[0] + dx * t + (r() - 0.5) * 22, a[1] + dy * t + (r() - 0.5) * 18, 16 + r() * 12, 0.75);
      ctx.restore();
      ctx.strokeStyle = "#3a2f25"; ctx.lineWidth = 2; ctx.stroke(gp);
    }
    // 吊橋：垂直穿過峽谷
    const [bx, by] = P(60, 45), bl = 74;
    const x1 = bx + nx * bl, y1 = by + ny * bl, x2 = bx - nx * bl, y2 = by - ny * bl;
    const sag = 14;
    ctx.lineCap = "round";
    for (const off of [-5, 5]) {
      ctx.strokeStyle = s === "scroll" ? PAL.scroll.ink : "#4a3523"; ctx.lineWidth = s === "scroll" ? 1.6 : 2.4;
      ctx.beginPath(); ctx.moveTo(x1 + dx / len * off, y1 + dy / len * off);
      ctx.quadraticCurveTo(bx + dx / len * off, by + dy / len * off + sag, x2 + dx / len * off, y2 + dy / len * off); ctx.stroke();
    }
    ctx.strokeStyle = s === "scroll" ? "rgba(42,34,24,0.8)" : "#b08a5a"; ctx.lineWidth = s === "scroll" ? 1.2 : 3;
    for (let t = 0.04; t < 1; t += 0.07) {
      const q = (1 - t) * (1 - t), m = 2 * t * (1 - t), u = t * t;
      const cx = q * x1 + m * bx + u * x2, cy = q * y1 + m * (by + sag) + u * y2;
      ctx.beginPath(); ctx.moveTo(cx - dx / len * 5, cy - dy / len * 5); ctx.lineTo(cx + dx / len * 5, cy + dy / len * 5); ctx.stroke();
    }
    for (const [px, py] of [[x1, y1], [x2, y2]]) {
      ctx.fillStyle = s === "scroll" ? PAL.scroll.ink : "#4a3523";
      ctx.fillRect(px - 3, py - 12, 6, 14);
    }
  }

  function smallTerrain(ctx, s) {
    const r = rng(71);
    // 藥師谷：藥圃
    const [hx, hy] = P(76, 66);
    for (let i = 0; i < 18; i++) {
      const x = hx + (r() - 0.5) * 120, y = hy + (r() - 0.5) * 60;
      if (Math.hypot(x - hx, y - hy) < 30) continue;
      ctx.fillStyle = s === "scroll" ? "rgba(90,120,70,0.5)" : ["#d65f8a", "#f0d060", "#b47ad8"][i % 3];
      ctx.beginPath(); ctx.arc(x, y, s === "scroll" ? 2.5 : 3, 0, Math.PI * 2); ctx.fill();
    }
    // 源晶裂痕
    const [rx, ry] = P(50, 21);
    ctx.strokeStyle = s === "scroll" ? "rgba(110,60,140,0.8)" : "#b77bff"; ctx.lineWidth = s === "scroll" ? 2 : 4;
    ctx.beginPath(); ctx.moveTo(rx - 70, ry + 10); ctx.lineTo(rx - 30, ry - 6); ctx.lineTo(rx - 5, ry + 8); ctx.lineTo(rx + 30, ry - 10); ctx.lineTo(rx + 70, ry + 4); ctx.stroke();
    // 斷崖：寨子南邊的崖線
    const [fx, fy] = P(60, 80);
    ctx.strokeStyle = s === "scroll" ? PAL.scroll.ink : "#5b4a3a"; ctx.lineWidth = s === "scroll" ? 1.6 : 3;
    ctx.beginPath(); ctx.moveTo(fx - 80, fy + 34);
    for (let i = 1; i <= 8; i++) ctx.lineTo(fx - 80 + i * 20, fy + 34 + (i % 2 ? 8 : -2));
    ctx.stroke();
    if (s === "painted") {
      ctx.fillStyle = "rgba(90,75,60,0.5)";
      for (let i = 0; i < 8; i++) ctx.fillRect(fx - 80 + i * 20, fy + 36, 14, 10 + (i % 3) * 4);
    }
    // 霧渡鎮旁的小屋
    const [tx, ty] = P(10, 80);
    for (const [ox, oy] of [[-46, 8], [40, 14], [-30, -30], [34, -24]]) {
      const x = tx + ox, y = ty + oy;
      ctx.fillStyle = s === "scroll" ? PAL.scroll.base : "#e8dcc4";
      ctx.fillRect(x - 7, y - 6, 14, 9);
      ctx.fillStyle = s === "scroll" ? "rgba(60,50,40,0.7)" : "#3d5f7a";
      ctx.beginPath(); ctx.moveTo(x - 10, y - 5); ctx.lineTo(x, y - 13); ctx.lineTo(x + 10, y - 5); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = PAL[s].ink; ctx.lineWidth = 1; ctx.strokeRect(x - 7, y - 6, 14, 9);
    }
  }

  function terrainLabels(ctx, s) {
    const items = [["霧　河", 36, 97.5], ["雲　海", 66, 55], ["梯　田", 40, 81.5], ["竹　林", 20, 70]];
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    for (const [t, px, py] of items) {
      const [x, y] = P(px, py);
      ctx.font = s === "scroll" ? `20px ${PAL.scroll.font}` : `italic 15px ${PAL.painted.font}`;
      ctx.fillStyle = s === "scroll" ? "rgba(42,34,24,0.45)" : "rgba(255,255,255,0.75)";
      ctx.fillText(t, x, y);
    }
  }

  // ---------- 迷霧 ----------
  function fog(ctx, s) {
    const fc = document.createElement("canvas");
    fc.width = W; fc.height = H;
    const f = fc.getContext("2d");
    const r = rng(91);
    if (s === "scroll") {
      f.fillStyle = PAL.scroll.fog; f.fillRect(0, 0, W, H);
      for (let i = 0; i < 50; i++) {
        const x = r() * W, y = r() * H, rad = 40 + r() * 120;
        const g = f.createRadialGradient(x, y, 0, x, y, rad);
        g.addColorStop(0, "rgba(150,115,65,0.07)"); g.addColorStop(1, "rgba(150,115,65,0)");
        f.fillStyle = g; f.fillRect(x - rad, y - rad, rad * 2, rad * 2);
      }
      for (let gy = 30; gy < H; gy += 58) {
        for (let gx = ((gy / 58) % 2) * 60; gx < W; gx += 120) {
          curl(f, gx + (r() - 0.5) * 30, gy + (r() - 0.5) * 16, 1.1 + r() * 0.4, "rgba(42,34,24,0.32)", 1.4);
        }
      }
    } else {
      const fp = REGION.fog;
      f.fillStyle = fp.base; f.fillRect(0, 0, W, H);
      for (let i = 0; i < 520; i++) puff(f, r() * W, r() * H, 30 + r() * 55, 0.55 + r() * 0.4, fp.puff);
      for (let i = 0; i < 160; i++) {
        const x = r() * W, y = r() * H, rad = 20 + r() * 40;
        const g = f.createRadialGradient(x, y + rad * 0.4, 0, x, y + rad * 0.4, rad);
        g.addColorStop(0, `rgba(${fp.shade},0.25)`); g.addColorStop(1, `rgba(${fp.shade},0)`);
        f.fillStyle = g; f.fillRect(x - rad, y - rad, rad * 2, rad * 2.4);
      }
    }
    // 去過＝撥開；相鄰沒去過＝薄霧
    f.globalCompositeOperation = "destination-out";
    const hole = (x, y, rad, a) => {
      const g = f.createRadialGradient(x, y, 0, x, y, rad);
      g.addColorStop(0, `rgba(0,0,0,${a})`); g.addColorStop(0.6, `rgba(0,0,0,${a * 0.85})`); g.addColorStop(1, "rgba(0,0,0,0)");
      f.fillStyle = g; f.fillRect(x - rad, y - rad, rad * 2, rad * 2);
    };
    for (const l of LOC) {
      const st = fogOf(l.id), [x, y] = LP(l);
      if (st === "visited") hole(x, y, 190, 1);
      if (st === "adjacent") hole(x, y, 105, 0.72);
    }
    for (const [a, b] of EDGES) {
      if (fogOf(a) === "visited" && fogOf(b) === "visited") {
        const [x1, y1] = LP(byId[a]), [x2, y2] = LP(byId[b]);
        for (let t = 0.25; t < 0.8; t += 0.25) hole(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, 120, 1);
      }
    }
    ctx.drawImage(fc, 0, 0);
    if (REGION.afterFog) { REGION.afterFog(ctx, s); return; }
    // 霧上露出的雪峰尖（只是地景，不洩漏地點）
    if (s === "painted") {
      const rr = rng(5);
      for (const [px, py, h] of [[72, 14, 120], [80, 16, 96], [64, 18, 80], [40, 12, 84], [18, 16, 72], [88, 22, 70]]) {
        const [x, y] = P(px, py);
        ctx.save(); ctx.globalAlpha = 0.75;
        ctx.beginPath(); ctx.rect(0, 0, W, y - h * 0.45); ctx.clip();
        mountain(ctx, "painted", x, y, h, rr, true); ctx.restore();
      }
    } else {
      const rr = rng(5);
      ctx.save(); ctx.globalAlpha = 0.35;
      for (const [px, py, h] of [[72, 14, 110], [80, 16, 86], [64, 18, 70], [40, 12, 76], [18, 16, 64]]) {
        const [x, y] = P(px, py);
        ctx.save(); ctx.beginPath(); ctx.rect(0, 0, W, y - h * 0.4); ctx.clip();
        mountain(ctx, "scroll", x, y, h, rr, true); ctx.restore();
      }
      ctx.restore();
    }
  }

  // ---------- 路與足跡 ----------
  function curveOf(a, b) {
    const [x1, y1] = LP(a), [x2, y2] = LP(b);
    const h = (a.id.length * 7 + b.id.length * 13) % 5 - 2;
    const mx = (x1 + x2) / 2, my = (y1 + y2) / 2, len = Math.hypot(x2 - x1, y2 - y1);
    const cx = mx + (-(y2 - y1) / len) * h * 9, cy = my + ((x2 - x1) / len) * h * 9;
    return [x1, y1, cx, cy, x2, y2];
  }
  function qpt(c, t) {
    const [x1, y1, cx, cy, x2, y2] = c, q = (1 - t) * (1 - t), m = 2 * t * (1 - t), u = t * t;
    return [q * x1 + m * cx + u * x2, q * y1 + m * cy + u * y2, 2 * (1 - t) * (cx - x1) + 2 * t * (x2 - cx), 2 * (1 - t) * (cy - y1) + 2 * t * (y2 - cy)];
  }
  function roads(ctx, s) {
    ctx.lineCap = "round";
    for (const [ia, ib] of EDGES) {
      const fa = fogOf(ia), fb = fogOf(ib);
      const vis = (f) => f === "visited" || f === "adjacent";
      if (!vis(fa) || !vis(fb) || (fa !== "visited" && fb !== "visited")) continue;
      const solid = fa === "visited" && fb === "visited";
      const c = curveOf(byId[ia], byId[ib]);
      const stroke = () => { ctx.beginPath(); ctx.moveTo(c[0], c[1]); ctx.quadraticCurveTo(c[2], c[3], c[4], c[5]); ctx.stroke(); };
      if (s === "scroll") {
        ctx.setLineDash(solid ? [10, 6] : [3, 8]);
        ctx.strokeStyle = solid ? PAL.scroll.road : "rgba(138,43,28,0.55)"; ctx.lineWidth = solid ? 3 : 2.4; stroke();
      } else {
        if (solid) {
          ctx.setLineDash([]);
          ctx.strokeStyle = "rgba(80,60,30,0.6)"; ctx.lineWidth = 9; stroke();
          ctx.strokeStyle = PAL.painted.road; ctx.lineWidth = 6; stroke();
        } else {
          ctx.setLineDash([8, 9]); ctx.strokeStyle = "rgba(255,255,255,0.85)"; ctx.lineWidth = 3.5; stroke();
        }
      }
    }
    ctx.setLineDash([]);
  }
  function footprints(ctx) {
    const [a, b] = STATE.trail.map((i) => byId[i]);
    const c = curveOf(a, b);
    let k = 0;
    for (let t = 0.22; t < 0.8; t += 0.075, k++) {
      const [x, y, tx, ty] = qpt(c, t), ang = Math.atan2(ty, tx), side = k % 2 ? 1 : -1;
      const ox = -Math.sin(ang) * 6 * side, oy = Math.cos(ang) * 6 * side;
      ctx.save(); ctx.translate(x + ox, y + oy); ctx.rotate(ang + Math.PI / 2);
      ctx.globalAlpha = 0.5 + 0.45 * (t - 0.2) / 0.6;
      ctx.fillStyle = "#f6f8ff"; ctx.strokeStyle = "rgba(30,36,50,0.8)"; ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.ellipse(0, 0, 3.6, 5.6, 0, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      ctx.beginPath(); ctx.arc(0, -8, 2.4, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      ctx.restore();
    }
  }

  // ---------- 地點圖示 ----------
  function icon(ctx, s, kind, x, y, grey) {
    ctx.save();
    ctx.translate(x, y);
    if (grey) ctx.filter = s === "scroll" ? "grayscale(1) opacity(0.6)" : "grayscale(1) brightness(1.15) opacity(0.8)";
    else if (s === "scroll") ctx.filter = "saturate(0.6) sepia(0.25)";
    ctx.lineJoin = "round";
    const ink = s === "scroll" ? PAL.scroll.ink : "#232a33";
    ctx.strokeStyle = ink; ctx.lineWidth = s === "scroll" ? 1.6 : 2;
    // 底座
    ctx.fillStyle = s === "scroll" ? "rgba(234,217,174,0.9)" : "rgba(255,255,255,0.85)";
    ctx.beginPath(); ctx.ellipse(0, 10, 20, 7, 0, 0, Math.PI * 2); ctx.fill();
    if (s === "painted") { ctx.strokeStyle = "rgba(35,42,51,0.5)"; ctx.stroke(); ctx.strokeStyle = ink; }
    const shape = (fill, pts) => { ctx.fillStyle = fill; ctx.beginPath(); pts.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]))); ctx.closePath(); ctx.fill(); ctx.stroke(); };
    switch (kind) {
      case "town":
        shape("#e8dcc4", [[-16, 10], [-16, -2], [-4, -2], [-4, 10]]);
        shape("#3d6f9c", [[-19, -1], [-10, -10], [-1, -1]]);
        shape("#efe4cc", [[-2, 10], [-2, -6], [14, -6], [14, 10]]);
        shape("#c0503a", [[-5, -5], [6, -17], [17, -5]]);
        ctx.fillStyle = "#5a3c24"; ctx.fillRect(3, 2, 5, 8);
        break;
      case "camp":
        shape("#d9a441", [[-14, 10], [0, -14], [14, 10]]);
        shape("#8a5a2a", [[-3, 10], [0, 0], [3, 10]]);
        ctx.beginPath(); ctx.moveTo(0, -14); ctx.lineTo(0, -22); ctx.stroke();
        shape("#c0392b", [[0, -22], [9, -19], [0, -16]]);
        break;
      case "village":
        shape("#e2cfa8", [[-12, 10], [-12, -2], [12, -2], [12, 10]]);
        shape("#a9813f", [[-16, -1], [0, -15], [16, -1]]);
        ctx.fillStyle = "#5a3c24"; ctx.fillRect(-3, 2, 6, 8);
        break;
      case "altar":
        shape("#a7a39a", [[-12, 10], [-10, 3], [10, 3], [12, 10]]);
        ctx.fillStyle = "#5a3c24"; ctx.fillRect(-2, -6, 4, 9);
        shape("#2f6a46", [[-14, -4], [0, -20], [14, -4]]);
        shape("#3b8055", [[-10, -12], [0, -24], [10, -12]]);
        break;
      case "ruin":
        shape("#c9c2b0", [[-14, 10], [-14, -10], [-8, -13], [-8, 10]]);
        shape("#c9c2b0", [[-3, 10], [-3, -4], [3, -2], [3, 10]]);
        shape("#c9c2b0", [[8, 10], [8, -15], [14, -15], [14, 10]]);
        shape("#a59e8c", [[-16, -12], [-6, -15], [-4, -12]]);
        break;
      case "elite_lair":
        ctx.fillStyle = "#7a2e2e"; ctx.beginPath(); ctx.arc(0, -2, 14, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        ctx.strokeStyle = "#f3e6d0"; ctx.lineWidth = 2.5;
        for (const o of [-6, 0, 6]) { ctx.beginPath(); ctx.moveTo(o - 3, -10); ctx.lineTo(o + 3, 6); ctx.stroke(); }
        break;
      case "anomaly":
        shape("#9b5de5", [[0, -20], [10, -4], [0, 10], [-10, -4]]);
        shape("#d3b5ff", [[0, -20], [4, -4], [0, 10], [-3, -4]]);
        break;
      case "boss":
        shape("#efe4cc", [[-10, 10], [-10, -4], [10, -4], [10, 10]]);
        shape("#7a2e2e", [[-18, -3], [0, -14], [18, -3]]);
        shape("#7a2e2e", [[-12, -12], [0, -22], [12, -12]]);
        break;
      case "gate":
        shape("#8a5a2a", [[-16, 2], [16, 2], [10, 10], [-10, 10]]);
        ctx.beginPath(); ctx.moveTo(0, 2); ctx.lineTo(0, -18); ctx.stroke();
        shape("#e9e2d0", [[1, -17], [12, -2], [1, -2]]);
        break;
      default:
        ctx.beginPath(); ctx.arc(0, -2, 12, 0, Math.PI * 2); ctx.stroke();
    }
    ctx.restore();
  }

  function label(ctx, s, text, x, y, opts) {
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    if (s === "scroll") {
      ctx.font = `${opts.grey ? 17 : 19}px ${PAL.scroll.font}`;
      ctx.lineWidth = 8; ctx.strokeStyle = PAL.scroll.halo; ctx.lineJoin = "round";
      ctx.strokeText(text, x, y);
      ctx.fillStyle = opts.grey ? "rgba(42,34,24,0.55)" : PAL.scroll.ink;
      ctx.fillText(text, x, y);
    } else {
      ctx.font = `bold ${opts.grey ? 13 : 14}px ${PAL.painted.font}`;
      const w = ctx.measureText(text).width + 14;
      ctx.fillStyle = opts.grey ? "rgba(70,78,90,0.75)" : "rgba(255,255,255,0.92)";
      roundRect(ctx, x - w / 2, y - 10, w, 20, 10); ctx.fill();
      if (!opts.grey) { ctx.strokeStyle = "rgba(35,42,51,0.6)"; ctx.lineWidth = 1; ctx.stroke(); }
      ctx.fillStyle = opts.grey ? "#e8ecf0" : PAL.painted.label;
      ctx.fillText(text, x, y + 1);
    }
  }
  function lvTag(ctx, s, lv, x, y, grey) {
    if (!lv) return;
    const t = `Lv ${lv}`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    if (s === "scroll") {
      ctx.font = `bold 12px ${PAL.painted.font}`;
      const w = ctx.measureText(t).width + 10;
      ctx.fillStyle = grey ? "rgba(140,60,45,0.55)" : "#a8322a";
      ctx.fillRect(x - w / 2, y - 8, w, 16);
      ctx.fillStyle = "#f6ead0"; ctx.fillText(t, x, y + 1);
    } else {
      ctx.font = `bold 11px ${PAL.painted.font}`;
      const w = ctx.measureText(t).width + 10;
      ctx.fillStyle = grey ? "rgba(40,48,58,0.6)" : "rgba(35,42,51,0.85)";
      roundRect(ctx, x - w / 2, y - 8, w, 16, 8); ctx.fill();
      ctx.fillStyle = "#ffe08a"; ctx.fillText(t, x, y + 1);
    }
  }
  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }
  function check(ctx, x, y) {
    ctx.fillStyle = "#2e9d57"; ctx.beginPath(); ctx.arc(x, y, 8, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = "#fff"; ctx.lineWidth = 2.2; ctx.beginPath(); ctx.moveTo(x - 4, y); ctx.lineTo(x - 1, y + 3); ctx.lineTo(x + 4, y - 3); ctx.stroke();
  }
  function quest(ctx, x, y) {
    ctx.fillStyle = "#f2c230"; ctx.strokeStyle = "#5a3a00"; ctx.lineWidth = 1.6;
    ctx.beginPath(); ctx.arc(x, y, 10, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x - 4, y + 8); ctx.lineTo(x, y + 15); ctx.lineTo(x + 3, y + 8); ctx.fill();
    ctx.fillStyle = "#3a2600"; ctx.font = `bold 15px ${PAL.painted.font}`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText("!", x, y + 1);
  }
  function stone(ctx, x, y, unlocked) {
    ctx.save();
    if (unlocked) {
      const g = ctx.createRadialGradient(x, y, 0, x, y, 18);
      g.addColorStop(0, "rgba(90,200,255,0.6)"); g.addColorStop(1, "rgba(90,200,255,0)");
      ctx.fillStyle = g; ctx.fillRect(x - 18, y - 18, 36, 36);
    }
    ctx.fillStyle = unlocked ? "#3fb4f0" : "#8d97a3"; ctx.strokeStyle = "#1b2a38"; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(x, y - 11); ctx.lineTo(x + 7, y); ctx.lineTo(x, y + 10); ctx.lineTo(x - 7, y); ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.fillStyle = unlocked ? "#c9f0ff" : "#c4cad2";
    ctx.beginPath(); ctx.moveTo(x, y - 11); ctx.lineTo(x + 2.5, y); ctx.lineTo(x, y + 10); ctx.lineTo(x - 2, y); ctx.closePath(); ctx.fill();
    if (!unlocked) {
      ctx.fillStyle = "#3a414a"; ctx.fillRect(x + 3, y + 2, 9, 7);
      ctx.strokeStyle = "#3a414a"; ctx.lineWidth = 1.6; ctx.beginPath(); ctx.arc(x + 7.5, y + 2, 3, Math.PI, 0); ctx.stroke();
    }
    ctx.restore();
  }
  function selfMark(ctx, s, x, y) {
    ctx.save();
    ctx.strokeStyle = "rgba(60,150,255,0.45)"; ctx.lineWidth = 6;
    ctx.beginPath(); ctx.ellipse(x, y + 10, 30, 12, 0, 0, Math.PI * 2); ctx.stroke();
    ctx.strokeStyle = "#2f8cff"; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.ellipse(x, y + 10, 30, 12, 0, 0, Math.PI * 2); ctx.stroke();
    // 小旗：自己的位置
    ctx.fillStyle = "#2f8cff"; ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(x - 28, y - 14, 8, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x - 32, y - 8); ctx.lineTo(x - 28, y + 2); ctx.lineTo(x - 24, y - 8); ctx.fill();
    ctx.restore();
  }

  function overlay(ctx, s) {
    const stones = Object.fromEntries(STATE.stones);
    for (const l of LOC) {
      const st = fogOf(l.id);
      if (st !== "visited" && st !== "adjacent") continue;
      const [x, y] = LP(l), grey = st === "adjacent";
      if (l.id === STATE.here) selfMark(ctx, s, x, y);
      icon(ctx, s, l.kind, x, y, grey);
      const name = grey ? "？？？" : l.name;
      label(ctx, s, name, x, y + 30, { grey });
      const lvShown = l.kind === "gate" && grey ? "" : l.lv;
      lvTag(ctx, s, lvShown, x, y + 50, grey);
      if (!grey && STATE.cleared.includes(l.id)) {
        ctx.font = s === "scroll" ? `19px ${PAL.scroll.font}` : `bold 14px ${PAL.painted.font}`;
        const w = ctx.measureText(name).width;
        check(ctx, x + w / 2 + (s === "scroll" ? 14 : 18), y + 30);
      }
      if (STATE.quests.includes(l.id)) quest(ctx, x + 18, y - 28);
      if (l.id in stones) stone(ctx, x + 28, y + 2, stones[l.id]);
    }
  }

  // ---------- 標題、圖例、外框 ----------
  function title(ctx, s) {
    const x = MX + 4, y = 34;
    if (s === "scroll") {
      ctx.fillStyle = "rgba(239,226,189,0.95)"; ctx.fillRect(x, y, 190, 74);
      ctx.strokeStyle = PAL.scroll.ink; ctx.lineWidth = 2; ctx.strokeRect(x, y, 190, 74);
      ctx.lineWidth = 1; ctx.strokeRect(x + 5, y + 5, 180, 64);
      ctx.fillStyle = PAL.scroll.ink; ctx.font = `38px ${PAL.scroll.font}`; ctx.textAlign = "left"; ctx.textBaseline = "middle";
      ctx.fillText(REGION.title, x + 18, y + 38);
      ctx.fillStyle = "#a8322a"; ctx.fillRect(x + 112, y + 16, 60, 42);
      ctx.fillStyle = "#f6ead0"; ctx.font = `bold 13px ${PAL.painted.font}`; ctx.textAlign = "center";
      ctx.fillText("建議", x + 142, y + 28); ctx.fillText(`Lv ${REGION.lv}`, x + 142, y + 46);
    } else {
      ctx.font = `bold 28px ${PAL.painted.font}`;
      const tw = ctx.measureText(REGION.title).width;
      ctx.fillStyle = "rgba(35,42,51,0.82)"; roundRect(ctx, x, y, tw + 150, 60, 12); ctx.fill();
      ctx.strokeStyle = "#e0c27a"; ctx.lineWidth = 2; ctx.stroke();
      ctx.fillStyle = "#ffffff"; ctx.textAlign = "left"; ctx.textBaseline = "middle";
      ctx.fillText(REGION.title, x + 18, y + 31);
      ctx.fillStyle = "#ffe08a"; ctx.font = `bold 15px ${PAL.painted.font}`;
      ctx.fillText(`建議 Lv ${REGION.lv}`, x + tw + 34, y + 32);
    }
  }
  function compass(ctx, s) {
    const x = W - MX - 40, y = 80;
    ctx.save(); ctx.translate(x, y);
    const ink = s === "scroll" ? PAL.scroll.ink : "#ffffff";
    ctx.strokeStyle = ink; ctx.fillStyle = s === "scroll" ? "#a8322a" : "#e05a4a"; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(0, -30); ctx.lineTo(7, 0); ctx.lineTo(-7, 0); ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.fillStyle = s === "scroll" ? PAL.scroll.base : "rgba(35,42,51,0.8)";
    ctx.beginPath(); ctx.moveTo(0, 30); ctx.lineTo(7, 0); ctx.lineTo(-7, 0); ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.arc(0, 0, 20, 0, Math.PI * 2); ctx.stroke();
    ctx.fillStyle = ink; ctx.font = s === "scroll" ? `18px ${PAL.scroll.font}` : `bold 14px ${PAL.painted.font}`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(s === "scroll" ? "北" : "N", 0, -42);
    ctx.restore();
  }
  function legend(ctx, s) {
    const w = 330, h = 86, x = W - MX - w + 10, y = H - 30 - h;
    if (s === "scroll") {
      ctx.fillStyle = "rgba(239,226,189,0.95)"; ctx.fillRect(x, y, w, h);
      ctx.strokeStyle = PAL.scroll.ink; ctx.lineWidth = 1.5; ctx.strokeRect(x, y, w, h);
    } else {
      ctx.fillStyle = "rgba(35,42,51,0.82)"; roundRect(ctx, x, y, w, h, 10); ctx.fill();
    }
    const tc = s === "scroll" ? PAL.scroll.ink : "#f2f4f7";
    const font = s === "scroll" ? `16px ${PAL.scroll.font}` : `13px ${PAL.painted.font}`;
    const cell = (cx, cy, draw, text) => {
      draw(cx, cy);
      ctx.fillStyle = tc; ctx.font = font; ctx.textAlign = "left"; ctx.textBaseline = "middle"; ctx.fillText(text, cx + 16, cy + 1);
    };
    const c1 = x + 22, c2 = x + 128, c3 = x + 232, r1 = y + 26, r2 = y + 60;
    cell(c1, r1, (cx, cy) => { ctx.fillStyle = "#2f8cff"; ctx.strokeStyle = "#fff"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(cx, cy, 7, 0, Math.PI * 2); ctx.fill(); ctx.stroke(); }, "自己");
    cell(c2, r1, (cx, cy) => { ctx.save(); ctx.translate(cx, cy); ctx.scale(0.75, 0.75); quest(ctx, 0, -2); ctx.restore(); }, "任務");
    cell(c3, r1, (cx, cy) => check(ctx, cx, cy), "已清空");
    cell(c1, r2, (cx, cy) => stone(ctx, cx, cy, true), "傳送石");
    cell(c2, r2, (cx, cy) => stone(ctx, cx - 3, cy, false), "未解鎖");
    cell(c3, r2, (cx, cy) => {
      ctx.fillStyle = "#f6f8ff"; ctx.strokeStyle = "rgba(30,36,50,0.8)"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.ellipse(cx - 3, cy + 2, 2.6, 4, -0.3, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      ctx.beginPath(); ctx.ellipse(cx + 4, cy - 3, 2.6, 4, -0.3, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    }, "朋友足跡");
  }
  function frame(ctx, s) {
    if (s === "scroll") {
      // 邊緣燒黃
      const g = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.45, W / 2, H / 2, Math.max(W, H) * 0.62);
      g.addColorStop(0, "rgba(120,80,30,0)"); g.addColorStop(1, "rgba(120,80,30,0.45)");
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
      // 上下滾軸
      for (const y of [0, H - 26]) {
        const gg = ctx.createLinearGradient(0, y, 0, y + 26);
        gg.addColorStop(0, "#3b2414"); gg.addColorStop(0.5, "#7a4a28"); gg.addColorStop(1, "#2e1b0e");
        ctx.fillStyle = gg; ctx.fillRect(14, y, W - 28, 26);
        ctx.fillStyle = "#c9a050";
        ctx.beginPath(); ctx.ellipse(10, y + 13, 12, 15, 0, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.ellipse(W - 10, y + 13, 12, 15, 0, 0, Math.PI * 2); ctx.fill();
      }
    } else {
      ctx.strokeStyle = "#5a3c24"; ctx.lineWidth = 22; ctx.strokeRect(11, 11, W - 22, H - 22);
      ctx.strokeStyle = "#8a5f38"; ctx.lineWidth = 6; ctx.strokeRect(19, 19, W - 38, H - 38);
      ctx.strokeStyle = "#e0c27a"; ctx.lineWidth = 2; ctx.strokeRect(25, 25, W - 50, H - 50);
    }
  }

  // opts.full：不蓋霧、不畫地點，只看整張地景（給使用者看全貌用）
  function cloudTerrain(ctx, s) {
    base(ctx, s);
    river(ctx, s);
    lake(ctx, s);
    terraces(ctx, s);
    smallTerrain(ctx, s);
    forests(ctx, s);
    bamboo(ctx, s);
    mountains(ctx, s);
    gorge(ctx, s);
    terrainLabels(ctx, s);
  }
  const REGIONS = {
    cloud_ridge: {
      title: "雲嶺", lv: "1～6", loc: CLOUD_LOC, edges: CLOUD_EDGES, state: CLOUD_STATE, terrain: cloudTerrain,
      fog: { base: "#e9edf1", puff: [255, 255, 255], shade: "170,182,198" },
    },
  };
  function setRegion(id) {
    REGION = REGIONS[id];
    LOC = REGION.loc; EDGES = REGION.edges; STATE = REGION.state;
    byId = Object.fromEntries(LOC.map((l) => [l.id, l]));
  }
  // 別的區域（ashenRegionArt.js）用這個登記自己的資料與地景
  function register(id, def) { REGIONS[id] = def; }

  function draw(canvas, s, opts = {}) {
    canvas.width = W; canvas.height = H;
    const ctx = canvas.getContext("2d");
    setRegion(opts.region || "cloud_ridge");
    REGION.terrain(ctx, s);
    if (!opts.full) {
      fog(ctx, s);
      roads(ctx, s);
      footprints(ctx);
      overlay(ctx, s);
    }
    title(ctx, s);
    compass(ctx, s);
    if (!opts.full) legend(ctx, s);
    frame(ctx, s);
  }

  window.RegionArt = {
    draw, register, W, H, fogOf,
    // 給其他區域與大世界圖共用的畫法
    P, rng, pathThrough, puff, pine, mountain, icon, label, lvTag, roundRect, stone, selfMark, quest, check, PAL,
  };
})();
