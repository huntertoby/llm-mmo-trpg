// 「碎界」五區的世界觀比較（美術樣張，2026-10-23）：每區一套色票＋地板畫法＋2～3 個專屬物件＋2 個當地服裝的單位。
// 全部程式繪製；畫法（光從左上、深色外框、紙娃娃比例）五區共用，只換配色與造型。
// 52px 虛擬格。正式版的做法：地圖加 region 欄位 → 換 artPalette 與物件造型；沒指定時用預設（現在的配色）。
window.Realms = (() => {
  const T = 52;
  const TAU = Math.PI * 2;
  function rng(seed) {
    let a = seed | 0;
    return () => {
      a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const R = (gx, gy, s) => rng((gx * 73856093) ^ (gy * 19349663) ^ (s * 83492791));
  function hexRgb(h) {
    const n = parseInt(h.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  const rgba = (h, a) => { const [r, g, b] = hexRgb(h); return `rgba(${r},${g},${b},${a})`; };
  function shade(h, f) {
    const [r, g, b] = hexRgb(h);
    const c = (v) => Math.max(0, Math.min(255, Math.round(v)));
    return `rgb(${c(r * f)},${c(g * f)},${c(b * f)})`;
  }
  const OUT = "#1c1712";
  function shadow(ctx, cx, cy, rx, ry, a = 0.35) {
    ctx.fillStyle = `rgba(0,0,0,${a})`;
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU);
    ctx.fill();
  }
  function glow(ctx, cx, cy, r, color, a = 0.55) {
    const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
    g.addColorStop(0, rgba(color, a));
    g.addColorStop(1, rgba(color, 0));
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, TAU);
    ctx.fill();
  }
  function poly(ctx, pts, fill, stroke = OUT, lw = 2) {
    ctx.beginPath();
    pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
    ctx.closePath();
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.lineWidth = lw; ctx.strokeStyle = stroke; ctx.stroke(); }
  }
  function rect(ctx, x, y, w, h, fill, stroke = OUT, lw = 2, r = 2) {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, r);
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.lineWidth = lw; ctx.strokeStyle = stroke; ctx.stroke(); }
  }

  // ---- 地板 ----
  /** 石板：每格 2～4 塊，色差由座標決定。 */
  function slabs(ctx, x, y, gx, gy, p) {
    const r = R(gx, gy, 1);
    ctx.fillStyle = p.joint;
    ctx.fillRect(x, y, T, T);
    const split = r() < 0.5;
    const blocks = split ? [[0, 0, 0.55, 0.5], [0.55, 0, 0.45, 0.5], [0, 0.5, 1, 0.5]] : [[0, 0, 1, 0.45], [0, 0.45, 0.4, 0.55], [0.4, 0.45, 0.6, 0.55]];
    for (const [bx, by, bw, bh] of blocks) {
      ctx.fillStyle = shade(p.floor, 0.92 + r() * 0.16);
      ctx.beginPath();
      ctx.roundRect(x + bx * T + 1.5, y + by * T + 1.5, bw * T - 3, bh * T - 3, 3);
      ctx.fill();
      ctx.fillStyle = rgba("#ffffff", 0.12);
      ctx.fillRect(x + bx * T + 2, y + by * T + 2, bw * T - 4, 2);
    }
    if (p.moss && r() < 0.45) {
      ctx.fillStyle = rgba(p.moss, 0.75);
      for (let i = 0; i < 4; i++) ctx.beginPath(), ctx.arc(x + r() * T, y + r() * T, 2 + r() * 3, 0, TAU), ctx.fill();
    }
  }
  /** 金屬板：鉚釘＋接縫，可選發光線。 */
  function plates(ctx, x, y, gx, gy, p) {
    const r = R(gx, gy, 2);
    ctx.fillStyle = shade(p.floor, 0.95 + r() * 0.1);
    ctx.fillRect(x, y, T, T);
    ctx.strokeStyle = p.joint;
    ctx.lineWidth = 2;
    ctx.strokeRect(x + 1, y + 1, T - 2, T - 2);
    ctx.fillStyle = p.rivet;
    for (const [dx, dy] of [[5, 5], [T - 5, 5], [5, T - 5], [T - 5, T - 5]]) ctx.beginPath(), ctx.arc(x + dx, y + dy, 1.8, 0, TAU), ctx.fill();
    if (p.line && (gx + gy * 2) % 3 === 0) {
      const horiz = (gx + gy) % 2 === 0;
      ctx.save();
      ctx.shadowColor = p.line;
      ctx.shadowBlur = 6;
      ctx.strokeStyle = p.line;
      ctx.lineWidth = 2;
      ctx.beginPath();
      if (horiz) { ctx.moveTo(x, y + T / 2); ctx.lineTo(x + T * 0.4, y + T / 2); ctx.lineTo(x + T * 0.5, y + T * 0.38); ctx.lineTo(x + T, y + T * 0.38); }
      else { ctx.moveTo(x + T / 2, y); ctx.lineTo(x + T / 2, y + T * 0.6); ctx.lineTo(x + T * 0.62, y + T * 0.7); ctx.lineTo(x + T * 0.62, y + T); }
      ctx.stroke();
      ctx.restore();
    }
    if (p.line2 && (gx * 3 + gy) % 4 === 1) {
      ctx.save();
      ctx.shadowColor = p.line2;
      ctx.shadowBlur = 6;
      ctx.strokeStyle = p.line2;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x + 8, y + T - 10);
      ctx.lineTo(x + T - 8, y + T - 10);
      ctx.stroke();
      ctx.restore();
    }
  }
  /** 焦土：深褐裂地，裂縫透出熔岩光。 */
  function ash(ctx, x, y, gx, gy, p) {
    const r = R(gx, gy, 3);
    ctx.fillStyle = shade(p.floor, 0.9 + r() * 0.2);
    ctx.fillRect(x, y, T, T);
    ctx.fillStyle = rgba("#000000", 0.18);
    for (let i = 0; i < 5; i++) ctx.beginPath(), ctx.arc(x + r() * T, y + r() * T, 3 + r() * 5, 0, TAU), ctx.fill();
    if (r() < 0.35) {
      ctx.save();
      ctx.shadowColor = p.lava;
      ctx.shadowBlur = 5;
      ctx.strokeStyle = p.lava;
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      let px = x + r() * T, py = y;
      ctx.moveTo(px, py);
      for (let s = 0; s < 5; s++) { px += (r() - 0.5) * 16; py += T / 5; ctx.lineTo(px, py); }
      ctx.stroke();
      ctx.restore();
    }
    ctx.strokeStyle = rgba("#000000", 0.25);
    ctx.strokeRect(x + 0.5, y + 0.5, T - 1, T - 1);
  }
  /** 沙岸／淺水／冰面：依格子類型。 */
  function shore(ctx, x, y, gx, gy, p, kind) {
    const r = R(gx, gy, 4);
    if (kind === "water") {
      ctx.fillStyle = p.water;
      ctx.fillRect(x, y, T, T);
      ctx.strokeStyle = rgba("#ffffff", 0.45);
      ctx.lineWidth = 1.5;
      for (let i = 0; i < 2; i++) {
        const wy = y + 12 + i * 22 + r() * 6;
        ctx.beginPath();
        ctx.moveTo(x + 8, wy);
        ctx.quadraticCurveTo(x + 18, wy - 5, x + 28, wy);
        ctx.stroke();
      }
    } else if (kind === "ice") {
      ctx.fillStyle = p.ice;
      ctx.fillRect(x, y, T, T);
      ctx.strokeStyle = rgba("#5a8aa8", 0.6);
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(x + r() * T, y);
      ctx.lineTo(x + T * 0.5, y + T * 0.5);
      ctx.lineTo(x + T, y + r() * T);
      ctx.stroke();
      ctx.fillStyle = rgba("#ffffff", 0.35);
      ctx.fillRect(x + 6, y + 6, 14, 3);
    } else {
      ctx.fillStyle = shade(p.floor, 0.94 + r() * 0.12);
      ctx.fillRect(x, y, T, T);
      ctx.fillStyle = rgba("#7a6a48", 0.45);
      for (let i = 0; i < 9; i++) ctx.fillRect(x + r() * T, y + r() * T, 1.6, 1.6);
    }
    ctx.strokeStyle = rgba("#000000", 0.12);
    ctx.strokeRect(x + 0.5, y + 0.5, T - 1, T - 1);
  }

  // ---- 物件（座標為格子左上角）----
  const OBJ = {
    crystal(ctx, x, y, c = "#8f7bff") {
      shadow(ctx, x + T / 2 + 3, y + T * 0.82, 15, 5);
      glow(ctx, x + T / 2, y + T * 0.45, 26, c, 0.45);
      poly(ctx, [[x + 26, y + 2], [x + 35, y + 16], [x + 33, y + 44], [x + 26, y + 48], [x + 19, y + 44], [x + 17, y + 16]], "#c8bcff");
      poly(ctx, [[x + 26, y + 2], [x + 35, y + 16], [x + 33, y + 44], [x + 26, y + 48]], shade(c, 0.85), null);
      poly(ctx, [[x + 26, y + 2], [x + 35, y + 16], [x + 33, y + 44], [x + 26, y + 48], [x + 19, y + 44], [x + 17, y + 16]], null);
      poly(ctx, [[x + 13, y + 30], [x + 18, y + 24], [x + 21, y + 46], [x + 14, y + 46]], "#a898ff");
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(x + 21, y + 14, 2, 18);
    },
    magicCircle(ctx, x, y, c = "#8f7bff") {
      ctx.save();
      ctx.shadowColor = c;
      ctx.shadowBlur = 8;
      ctx.strokeStyle = c;
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.ellipse(x + T / 2, y + T / 2, 21, 19, 0, 0, TAU); ctx.stroke();
      ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.ellipse(x + T / 2, y + T / 2, 14, 12.5, 0, 0, TAU); ctx.stroke();
      ctx.beginPath();
      for (let i = 0; i < 6; i++) { const a = (i / 6) * TAU; ctx.lineTo(x + T / 2 + Math.cos(a) * 14, y + T / 2 + Math.sin(a) * 12.5); }
      ctx.closePath(); ctx.stroke();
      ctx.restore();
    },
    cityWall(ctx, x, y) {
      shadow(ctx, x + T / 2 + 4, y + T * 0.8, 24, 6, 0.4);
      rect(ctx, x + 2, y + 18, T - 4, 26, "#cbbb98");
      ctx.strokeStyle = "#8a7a5c"; ctx.lineWidth = 1.2; ctx.beginPath();
      ctx.moveTo(x + 2, y + 31); ctx.lineTo(x + T - 2, y + 31);
      for (const bx of [14, 30, 44]) { ctx.moveTo(x + bx, y + 18); ctx.lineTo(x + bx, y + 31); }
      for (const bx of [8, 22, 38]) { ctx.moveTo(x + bx, y + 31); ctx.lineTo(x + bx, y + 44); }
      ctx.stroke();
      for (const bx of [2, 18, 34]) rect(ctx, x + bx, y + 9, 14, 10, "#e2d4b2", OUT, 2, 1);
      ctx.fillStyle = "#3a5ad0"; ctx.fillRect(x + 22, y + 22, 8, 14);
      ctx.fillStyle = "#e8bb48"; ctx.fillRect(x + 22, y + 22, 8, 2);
    },
    bamboo(ctx, x, y) {
      const r = R(x, y, 9);
      shadow(ctx, x + T / 2 + 3, y + T * 0.86, 18, 5);
      for (let i = 0; i < 4; i++) {
        const bx = x + 10 + i * 10 + r() * 3;
        const top = y + 2 + r() * 8;
        ctx.fillStyle = i % 2 ? "#4f8a3a" : "#6aa84a";
        ctx.fillRect(bx, top, 5, y + T * 0.86 - top);
        ctx.strokeStyle = OUT; ctx.lineWidth = 1.5; ctx.strokeRect(bx, top, 5, y + T * 0.86 - top);
        ctx.fillStyle = "#2f5a22";
        for (let k = top + 9; k < y + T * 0.8; k += 10) ctx.fillRect(bx - 1, k, 7, 2);
        ctx.fillStyle = "#7cc05a";
        ctx.beginPath(); ctx.ellipse(bx + 9, top + 6 + r() * 6, 7, 2.5, -0.5, 0, TAU); ctx.fill();
      }
    },
    stoneLantern(ctx, x, y) {
      shadow(ctx, x + T / 2 + 3, y + T * 0.86, 13, 4);
      const g = "#9aa39c";
      rect(ctx, x + 18, y + 38, 16, 7, shade(g, 0.85));
      rect(ctx, x + 23, y + 26, 6, 12, g);
      rect(ctx, x + 17, y + 16, 18, 11, g);
      glow(ctx, x + 26, y + 21, 14, "#ffcf6a", 0.6);
      ctx.fillStyle = "#ffcf6a"; ctx.fillRect(x + 22, y + 18, 8, 6);
      poly(ctx, [[x + 12, y + 16], [x + 26, y + 6], [x + 40, y + 16]], shade(g, 0.75));
      rect(ctx, x + 24, y + 2, 4, 5, g, OUT, 1.5, 1);
    },
    pavilionPillar(ctx, x, y) {
      shadow(ctx, x + T / 2 + 4, y + T * 0.86, 22, 5);
      rect(ctx, x + 8, y + 14, 7, 32, "#b8432f");
      rect(ctx, x + 37, y + 14, 7, 32, "#b8432f");
      rect(ctx, x + 4, y + 16, 44, 5, "#8a2f20");
      poly(ctx, [[x - 2, y + 12], [x + 6, y + 4], [x + 46, y + 4], [x + 54, y + 12], [x + 46, y + 10], [x + 6, y + 10]], "#3c4a48");
      ctx.fillStyle = "#e8bb48"; ctx.fillRect(x + 22, y + 22, 8, 10);
    },
    brassPipe(ctx, x, y, c = "#4ae0d0") {
      shadow(ctx, x + T / 2 + 3, y + T * 0.84, 22, 5);
      rect(ctx, x + 2, y + 26, T - 4, 12, "#b08a4a", OUT, 2, 5);
      ctx.fillStyle = "#e0bf7a"; ctx.fillRect(x + 4, y + 28, T - 8, 2.5);
      for (const bx of [10, 38]) rect(ctx, x + bx, y + 23, 5, 18, "#8a6a34", OUT, 1.5, 1);
      // 晶能閥：發光的晶球
      glow(ctx, x + 26, y + 22, 16, c, 0.6);
      rect(ctx, x + 20, y + 18, 12, 14, "#5a4628", OUT, 2, 3);
      ctx.fillStyle = c; ctx.beginPath(); ctx.arc(x + 26, y + 18, 5.5, 0, TAU); ctx.fill();
      ctx.lineWidth = 1.5; ctx.strokeStyle = OUT; ctx.stroke();
      ctx.fillStyle = "#ffffff"; ctx.fillRect(x + 24, y + 15, 2, 2);
    },
    gearMachine(ctx, x, y, c = "#4ae0d0") {
      shadow(ctx, x + T / 2 + 3, y + T * 0.86, 18, 5);
      rect(ctx, x + 10, y + 20, 32, 26, "#6a5a42");
      // 齒輪
      const cx = x + 26, cy = y + 16;
      ctx.beginPath();
      for (let i = 0; i < 16; i++) { const a = (i / 16) * TAU; const rr = i % 2 ? 9 : 12; ctx.lineTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr); }
      ctx.closePath(); ctx.fillStyle = "#c89a4a"; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
      ctx.beginPath(); ctx.arc(cx, cy, 4, 0, TAU); ctx.fillStyle = "#5a4628"; ctx.fill();
      // 符文面板
      ctx.save(); ctx.shadowColor = c; ctx.shadowBlur = 6; ctx.strokeStyle = c; ctx.lineWidth = 1.6;
      ctx.beginPath(); ctx.moveTo(x + 16, y + 32); ctx.lineTo(x + 22, y + 38); ctx.lineTo(x + 28, y + 30); ctx.lineTo(x + 34, y + 38); ctx.stroke();
      ctx.restore();
    },
    terminal(ctx, x, y, c = "#39e0ff") {
      shadow(ctx, x + T / 2 + 3, y + T * 0.86, 15, 5);
      rect(ctx, x + 14, y + 10, 24, 36, "#2a3040", "#05070c");
      glow(ctx, x + 26, y + 20, 18, c, 0.45);
      rect(ctx, x + 17, y + 13, 18, 14, "#0c2a38", c, 1.5, 1);
      ctx.fillStyle = c; for (let i = 0; i < 3; i++) ctx.fillRect(x + 19, y + 16 + i * 3.5, 6 + i * 3, 1.5);
      ctx.fillStyle = "#ff3fa8"; ctx.fillRect(x + 19, y + 33, 14, 2);
    },
    neonBarrier(ctx, x, y) {
      shadow(ctx, x + T / 2 + 3, y + T * 0.82, 22, 5);
      for (const bx of [6, 40]) rect(ctx, x + bx, y + 14, 6, 30, "#3a4258", "#05070c");
      ctx.save(); ctx.shadowColor = "#ff3fa8"; ctx.shadowBlur = 8; ctx.strokeStyle = "#ff3fa8"; ctx.lineWidth = 2.5;
      for (const ly of [20, 28, 36]) { ctx.beginPath(); ctx.moveTo(x + 12, y + ly); ctx.lineTo(x + 40, y + ly); ctx.stroke(); }
      ctx.restore();
    },
    ruinWall(ctx, x, y) {
      shadow(ctx, x + T / 2 + 4, y + T * 0.82, 22, 6, 0.45);
      poly(ctx, [[x + 4, y + 44], [x + 4, y + 18], [x + 14, y + 12], [x + 20, y + 22], [x + 30, y + 16], [x + 36, y + 28], [x + 48, y + 26], [x + 48, y + 44]], "#6a5e54");
      ctx.strokeStyle = "#3a322c"; ctx.lineWidth = 1.2; ctx.beginPath();
      ctx.moveTo(x + 4, y + 32); ctx.lineTo(x + 48, y + 34); ctx.moveTo(x + 18, y + 32); ctx.lineTo(x + 18, y + 44); ctx.moveTo(x + 34, y + 34); ctx.lineTo(x + 34, y + 44); ctx.stroke();
      ctx.fillStyle = rgba("#1a0a04", 0.5); ctx.fillRect(x + 6, y + 20, 8, 10);
      rect(ctx, x + 38, y + 40, 9, 6, "#5a4e44", OUT, 1.5, 1);
    },
    deadTree(ctx, x, y) {
      shadow(ctx, x + T / 2 + 3, y + T * 0.86, 14, 4);
      ctx.strokeStyle = OUT; ctx.lineCap = "round"; ctx.lineWidth = 7;
      const br = [[[26, 46], [26, 22]], [[26, 30], [14, 16]], [[26, 26], [38, 12]], [[38, 12], [44, 8]], [[14, 16], [10, 8]]];
      for (const [[a, b], [c, d]] of br) { ctx.beginPath(); ctx.moveTo(x + a, y + b); ctx.lineTo(x + c, y + d); ctx.stroke(); }
      ctx.strokeStyle = "#3e3028"; ctx.lineWidth = 4;
      for (const [[a, b], [c, d]] of br) { ctx.beginPath(); ctx.moveTo(x + a, y + b); ctx.lineTo(x + c, y + d); ctx.stroke(); }
      ctx.fillStyle = "#ff7a1a"; ctx.fillRect(x + 25, y + 36, 2, 4);
    },
    lavaPool(ctx, x, y) {
      ctx.save();
      ctx.beginPath(); ctx.roundRect(x + 3, y + 3, T - 6, T - 6, 14);
      const g = ctx.createRadialGradient(x + T / 2, y + T / 2, 2, x + T / 2, y + T / 2, 26);
      g.addColorStop(0, "#ffd04a"); g.addColorStop(0.5, "#ff7a1a"); g.addColorStop(1, "#a02a0a");
      ctx.fillStyle = g; ctx.fill(); ctx.lineWidth = 3; ctx.strokeStyle = "#2a1208"; ctx.stroke();
      ctx.fillStyle = "#5a1a08"; for (const [dx, dy] of [[14, 16], [34, 30], [22, 36]]) ctx.beginPath(), ctx.ellipse(x + dx, y + dy, 5, 3, 0.4, 0, TAU), ctx.fill();
      ctx.restore();
    },
    reef(ctx, x, y) {
      shadow(ctx, x + T / 2 + 3, y + T * 0.8, 20, 6, 0.3);
      poly(ctx, [[x + 6, y + 42], [x + 10, y + 24], [x + 22, y + 16], [x + 36, y + 20], [x + 46, y + 34], [x + 44, y + 44]], "#6a7a80");
      ctx.fillStyle = "#e8807a"; for (const [dx, dy] of [[18, 26], [30, 24], [36, 34]]) ctx.beginPath(), ctx.arc(x + dx, y + dy, 3, 0, TAU), ctx.fill();
      ctx.strokeStyle = rgba("#ffffff", 0.75); ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(x + 2, y + 46); ctx.quadraticCurveTo(x + 26, y + 40, x + 50, y + 46); ctx.stroke();
    },
    wreck(ctx, x, y) {
      shadow(ctx, x + T / 2 + 3, y + T * 0.82, 22, 6, 0.35);
      poly(ctx, [[x + 2, y + 34], [x + 50, y + 28], [x + 46, y + 44], [x + 8, y + 46]], "#7a5232");
      ctx.strokeStyle = "#4e321c"; ctx.lineWidth = 1.4; ctx.beginPath(); ctx.moveTo(x + 4, y + 39); ctx.lineTo(x + 48, y + 35); ctx.stroke();
      // 斷桅
      ctx.save(); ctx.translate(x + 30, y + 32); ctx.rotate(-0.35);
      rect(ctx, -3, -28, 6, 30, "#8a6240"); rect(ctx, -12, -24, 18, 3, "#8a6240", OUT, 1.5, 1);
      ctx.fillStyle = "#d8ccb0"; ctx.beginPath(); ctx.moveTo(-10, -21); ctx.lineTo(4, -21); ctx.lineTo(-2, -8); ctx.closePath(); ctx.fill();
      ctx.restore();
    },
  };

  // ---- 五區（＋科技城另一個方向）----
  // 單位：PaperDoll 的 look ＋ gear（kind／material／color／element，紙娃娃既有的部件）
  const SKIN = ["#f1c9a5", "#d9a47a", "#a8724c", "#7a4e32"];
  const REALMS = [
    {
      id: "crystal_crown", name: "晶冠城邦", style: "奇幻",
      line: "白石城牆、晶柱與法陣。現在的紙娃娃（板甲、法袍）直接適用，是基準風格。",
      swatch: [["#d8ccb0", "石板"], ["#a89a7c", "接縫"], ["#8f7bff", "晶光"], ["#3a5ad0", "旗藍"], ["#e8bb48", "金飾"]],
      floor: (ctx, x, y, gx, gy) => slabs(ctx, x, y, gx, gy, { floor: "#d8ccb0", joint: "#a89a7c" }),
      objects: [[1, 0, "cityWall"], [2, 0, "cityWall"], [4, 1, "crystal"], [2, 2, "magicCircle"], [5, 3, "crystal"]],
      units: [
        [1, 2, { skin: SKIN[0], hair: "short", hairColor: "#6a3d1e" }, { body: { kind: "plate", material: "steel" }, main_hand: { kind: "sword", material: "steel" }, off_hand: { kind: "shield_kite", material: "steel", color: "#3a5ad0" }, cloak: { kind: "cape", color: "#3a5ad0" }, feet: { kind: "greaves", material: "steel" } }],
        [3, 3, { skin: SKIN[1], hair: "long", hairColor: "#c8c0b0", trim: "#e8bb48" }, { body: { kind: "robe", color: "#5a3a9a" }, head: { kind: "wizard_hat", color: "#5a3a9a" }, main_hand: { kind: "staff", material: "wood", element: "shadow" } }],
      ],
    },
    {
      id: "cloud_ridge", name: "雲嶺", style: "東方",
      line: "青石階、竹林、朱紅樑柱、石燈籠。低彩度的青綠墨灰，點一點朱紅。",
      swatch: [["#7d8c84", "青石"], ["#56645c", "墨灰"], ["#6aa84a", "竹青"], ["#b8432f", "朱紅"], ["#e8e8e0", "霧白"]],
      floor: (ctx, x, y, gx, gy) => slabs(ctx, x, y, gx, gy, { floor: "#7d8c84", joint: "#56645c", moss: "#5a8a3a" }),
      objects: [[0, 0, "bamboo"], [1, 0, "bamboo"], [3, 0, "pavilionPillar"], [5, 1, "stoneLantern"], [0, 3, "bamboo"]],
      mist: true,
      units: [
        [2, 2, { skin: SKIN[0], hair: "long", hairColor: "#1a1a1a" }, { body: { kind: "robe", color: "#2f5a5a" }, head: { kind: "wide_hat", material: "wood", color: "#c8a868" }, main_hand: { kind: "sword", material: "steel" }, feet: { kind: "shoes", color: "#2a2a2a" } }],
        [4, 3, { skin: SKIN[1], hair: "short", hairColor: "#1a1a1a" }, { body: { kind: "coat", color: "#8a2f20" }, main_hand: { kind: "spear", material: "steel" }, feet: { kind: "shoes", color: "#2a2a2a" } }],
      ],
    },
    {
      id: "arcane_hub", name: "魔導樞市", style: "魔導科技",
      line: "黃銅管線、齒輪機關、晶能燈。槍和機械都有，但仍是「魔法驅動」，和奇幻、東方放一起不突兀。",
      swatch: [["#4a4238", "鐵板"], ["#b08a4a", "黃銅"], ["#4ae0d0", "晶能"], ["#e8a040", "符文"], ["#2a241e", "煤黑"]],
      floor: (ctx, x, y, gx, gy) => plates(ctx, x, y, gx, gy, { floor: "#4a4238", joint: "#2a241e", rivet: "#b08a4a", line: "#4ae0d0" }),
      objects: [[1, 0, "brassPipe"], [2, 0, "brassPipe"], [4, 0, "gearMachine"], [0, 2, "gearMachine"], [5, 3, "brassPipe"]],
      units: [
        [2, 2, { skin: SKIN[0], hair: "short", hairColor: "#8a4a20" }, { body: { kind: "coat", color: "#6a4a2a" }, head: { kind: "cap", color: "#3a2a1a" }, main_hand: { kind: "gun", form: "rifle", material: "copper", element: "lightning" }, hands: { kind: "gauntlets", material: "copper" }, feet: { kind: "boots", material: "leather" } }],
        [4, 3, { skin: SKIN[2], hair: "long", hairColor: "#e8e0d0" }, { body: { kind: "plate", material: "copper" }, main_hand: { kind: "orb", element: "ice" }, feet: { kind: "greaves", material: "copper" } }],
      ],
    },
    {
      id: "ashen_waste", name: "灰燼荒原", style: "災變",
      line: "焦土裂地、熔岩池、殘牆枯木。拾荒者混搭破布與舊槍，色調最暗，熔岩橘當重點。",
      swatch: [["#4a3a30", "焦土"], ["#2a1e18", "炭黑"], ["#ff6a1a", "熔岩"], ["#6a5e54", "殘牆"], ["#c8b08a", "破布"]],
      floor: (ctx, x, y, gx, gy) => ash(ctx, x, y, gx, gy, { floor: "#4a3a30", lava: "#ff6a1a" }),
      objects: [[1, 0, "ruinWall"], [4, 0, "deadTree"], [3, 1, "lavaPool"], [0, 3, "ruinWall"], [5, 2, "deadTree"]],
      units: [
        [2, 2, { skin: SKIN[2], hair: "short", hairColor: "#2a1c14" }, { body: { kind: "leather", material: "leather", color: "#6a5040" }, head: { kind: "hood", color: "#8a7a5a" }, main_hand: { kind: "gun", form: "pistol", material: "iron" }, feet: { kind: "boots", material: "leather" } }],
        [4, 3, { skin: SKIN[3], hair: "short", hairColor: "#1a1a1a" }, { body: { kind: "leather", material: "leather", color: "#4a3a2a" }, head: { kind: "bandana", color: "#a83a2a" }, main_hand: { kind: "axe", material: "iron", element: "fire" }, feet: { kind: "boots", material: "leather" } }],
      ],
    },
    {
      id: "frost_tide", name: "霜潮海境", style: "海境",
      line: "沙岸、淺灘、浮冰、礁石與沉船。冰藍與沙色，潮汐可以沿用整格升降。",
      swatch: [["#d8c89a", "沙岸"], ["#3f8ac8", "淺海"], ["#cdeeff", "浮冰"], ["#6a7a80", "礁石"], ["#e8807a", "珊瑚"]],
      floor: (ctx, x, y, gx, gy) => shore(ctx, x, y, gx, gy, { floor: "#d8c89a", water: "#3f8ac8", ice: "#cdeeff" }, gx >= 4 && gy <= 1 ? "ice" : gx + gy >= 6 ? "water" : "sand"),
      objects: [[1, 0, "wreck"], [3, 3, "reef"], [5, 1, "reef"]],
      units: [
        [2, 2, { skin: SKIN[0], hair: "long", hairColor: "#d8e8f0" }, { body: { kind: "mail", material: "steel", color: "#5a8aa8" }, main_hand: { kind: "spear", material: "steel", element: "ice" }, feet: { kind: "boots", material: "leather" } }],
        [4, 2, { skin: SKIN[1], hair: "short", hairColor: "#3a2a1a" }, { body: { kind: "coat", color: "#2a4a6a" }, head: { kind: "wide_hat", color: "#3a3a3a" }, main_hand: { kind: "gun", form: "rifle", material: "wood" }, feet: { kind: "boots", material: "leather" } }],
      ],
    },
    {
      id: "neon_hub", name: "（另案）霓虹樞市", style: "賽博科技",
      line: "深色金屬、青與洋紅的發光線、終端機。最「未來」，但和中世紀小人落差最大，要補的服裝與特效最多。",
      swatch: [["#1a2030", "深藍黑"], ["#3a4258", "槍鐵"], ["#39e0ff", "青光"], ["#ff3fa8", "洋紅"], ["#e8f0ff", "冷白"]],
      floor: (ctx, x, y, gx, gy) => plates(ctx, x, y, gx, gy, { floor: "#1a2030", joint: "#0a0e18", rivet: "#3a4258", line: "#39e0ff", line2: "#ff3fa8" }),
      objects: [[1, 0, "terminal"], [3, 0, "neonBarrier"], [4, 0, "neonBarrier"], [0, 2, "terminal"], [5, 3, "terminal"]],
      units: [
        [2, 2, { skin: SKIN[0], hair: "short", hairColor: "#ff3fa8" }, { body: { kind: "coat", color: "#1e2638" }, main_hand: { kind: "gun", form: "energy", material: "steel", element: "lightning" }, feet: { kind: "boots", material: "leather", color: "#1a1a1a" } }],
        [4, 3, { skin: SKIN[1], hair: "short", hairColor: "#1a1a1a" }, { body: { kind: "plate", material: "steel", color: "#2a3040" }, head: { kind: "helmet", material: "steel" }, main_hand: { kind: "gun", form: "rifle", material: "steel", element: "ice" }, feet: { kind: "greaves", material: "steel" } }],
      ],
    },
  ];

  /** 畫一張 W×H 的小戰場。 */
  function scene(ctx, realm, W = 6, H = 4) {
    for (let gy = 0; gy < H; gy++) for (let gx = 0; gx < W; gx++) realm.floor(ctx, gx * T, gy * T, gx, gy);
    for (let gy = 0; gy < H; gy++) {
      for (const [ox, oy, kind] of realm.objects) if (oy === gy) (OBJ[kind] ?? (() => {}))(ctx, ox * T, oy * T);
      for (const [ux, uy, look, gear] of realm.units) {
        if (uy !== gy) continue;
        const cx = ux * T + T / 2;
        ctx.save();
        ctx.beginPath(); ctx.ellipse(cx, uy * T + T * 0.8, T * 0.34, T * 0.12, 0, 0, TAU);
        ctx.fillStyle = "#5aa0ff55"; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = "#5aa0ff"; ctx.stroke();
        ctx.restore();
        PaperDoll.stamp(ctx, { look, gear }, "south", cx, uy * T + T * 0.82, 0.78, { dpr: 3 });
      }
    }
    if (realm.mist) {
      const r = rng(5);
      for (let i = 0; i < 7; i++) {
        const px = r() * W * T, py = r() * H * T, rad = 30 + r() * 30;
        const g = ctx.createRadialGradient(px, py, 0, px, py, rad);
        g.addColorStop(0, "rgba(232,232,224,0.32)"); g.addColorStop(1, "rgba(232,232,224,0)");
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(px, py, rad, 0, TAU); ctx.fill();
      }
    }
  }

  return { T, REALMS, OBJ, scene };
})();
