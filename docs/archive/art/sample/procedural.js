// 程式繪製版（美術樣張）：不使用任何下載素材，全部用 Canvas 2D 的幾何圖形畫出。
// 風格：幾何扁平風（flat）＋ 少量明暗。地磚的紋理由「格子座標 → 種子」決定，所以每格不同、但每次畫都一樣（確定性）。
// 要接進遊戲時，可把每種地形 × 變體預先畫到離屏 canvas，再用 PixiJS 的 Texture.from(canvas) 當貼圖。
window.ProcRender = (() => {
  const S = window.SCENE;
  const U = window.SCENE_UTIL;
  const T = 52;
  const TAU = Math.PI * 2;

  // ---- 確定性亂數（格子座標＋用途 → 種子）----
  function hash(x, y, salt) {
    let h = 2166136261 ^ salt;
    h = Math.imul(h ^ (x + 374761393), 16777619);
    h = Math.imul(h ^ (y + 668265263), 16777619);
    h ^= h >>> 13;
    h = Math.imul(h, 1274126177);
    return (h ^ (h >>> 16)) >>> 0;
  }
  function rng(x, y, salt) {
    let a = hash(x, y, salt);
    return () => {
      a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // ---- 顏色工具 ----
  function hexRgb(h) {
    const n = parseInt(h.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function shade(h, f) {
    const [r, g, b] = hexRgb(h);
    const c = (v) => Math.max(0, Math.min(255, Math.round(v)));
    return `rgb(${c(r * f)},${c(g * f)},${c(b * f)})`;
  }
  function rgba(h, a) {
    const [r, g, b] = hexRgb(h);
    return `rgba(${r},${g},${b},${a})`;
  }

  // ---- 色票（一處統一；整體偏低彩度，讓陣營色與特效跳出來）----
  const PAL = {
    stone: "#8e8a80", stoneGap: "#6c685f",
    grass: "#6b9a4b", grassLight: "#8dbb62", grassDark: "#4f7a35",
    dirt: "#9a7650", dirtLight: "#b48f66", dirtDark: "#76593a",
    wallTop: "#5d554e", wallLine: "#3d3732", wallFace: "#2e2925",
    chasm: "#0d0d14", chasmLip: "#3b3742",
    lava: "#e2531d", lavaCrust: "#7c2a14", lavaGlow: "#ffd04a",
    deep: "#1c4a7c", deepLight: "#4f86c0",
    water: "#3a86d8", ice: "#d4f0ff", oil: "#211a10", fire: "#ff7a1a", poison: "#74c23c",
    wood: "#b77f3f", woodDark: "#6e4620", woodMid: "#8f5f2c",
    rock: "#a8a49a", rockDark: "#6c685f",
    ally: "#2f6fd0", allyRing: "#a9ccff", enemy: "#c63b3b", enemyRing: "#ffb3a8", summon: "#1f9e8f", summonRing: "#8ff0e2",
    active: "#ffe14d",
  };

  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, r);
  }

  // ==== 地形 ====
  function drawStone(ctx, x, y) {
    const r = rng(x, y, 1);
    ctx.fillStyle = PAL.stoneGap;
    ctx.fillRect(0, 0, T, T);
    // 每格切成 2–4 塊石板，切法依種子
    const slabs = [];
    const splitV = r() < 0.5;
    const cut = 0.35 + r() * 0.3;
    if (splitV) {
      slabs.push([0, 0, T * cut, T], [T * cut, 0, T * (1 - cut), T]);
    } else {
      slabs.push([0, 0, T, T * cut], [0, T * cut, T, T * (1 - cut)]);
    }
    if (r() < 0.6) {
      const [sx, sy, sw, sh] = slabs.pop();
      const c2 = 0.4 + r() * 0.2;
      if (splitV) slabs.push([sx, sy, sw, sh * c2], [sx, sy + sh * c2, sw, sh * (1 - c2)]);
      else slabs.push([sx, sy, sw * c2, sh], [sx + sw * c2, sy, sw * (1 - c2), sh]);
    }
    for (const [sx, sy, sw, sh] of slabs) {
      ctx.fillStyle = shade(PAL.stone, 0.94 + r() * 0.12);
      roundRect(ctx, sx + 1.5, sy + 1.5, sw - 3, sh - 3, 3);
      ctx.fill();
      ctx.fillStyle = "rgba(255,255,255,0.10)";
      ctx.fillRect(sx + 3, sy + 2, sw - 6, 2);
    }
    if (r() < 0.35) {
      ctx.strokeStyle = "rgba(60,56,50,0.55)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      let px = T * (0.2 + r() * 0.6);
      let py = T * (0.2 + r() * 0.2);
      ctx.moveTo(px, py);
      for (let i = 0; i < 3; i++) {
        px += (r() - 0.5) * 12;
        py += 5 + r() * 6;
        ctx.lineTo(px, py);
      }
      ctx.stroke();
    }
  }

  function drawGrass(ctx, x, y) {
    const r = rng(x, y, 2);
    ctx.fillStyle = shade(PAL.grass, 0.96 + r() * 0.08);
    ctx.fillRect(0, 0, T, T);
    // 柔和的深淺斑塊
    for (let i = 0; i < 3; i++) {
      ctx.fillStyle = r() < 0.5 ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)";
      ctx.beginPath();
      ctx.ellipse(r() * T, r() * T, 8 + r() * 10, 6 + r() * 8, r() * TAU, 0, TAU);
      ctx.fill();
    }
    // 草叢：小 V 字
    const n = 6 + Math.floor(r() * 4);
    for (let i = 0; i < n; i++) {
      const gx = 5 + r() * (T - 10);
      const gy = 7 + r() * (T - 12);
      ctx.strokeStyle = r() < 0.6 ? PAL.grassLight : PAL.grassDark;
      ctx.lineWidth = 1.6;
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(gx - 3, gy - 4);
      ctx.lineTo(gx, gy);
      ctx.lineTo(gx + 3, gy - 5);
      ctx.moveTo(gx, gy);
      ctx.lineTo(gx, gy - 6);
      ctx.stroke();
    }
    if (r() < 0.3) {
      ctx.fillStyle = r() < 0.5 ? "#f3e27a" : "#f0f0f0";
      ctx.beginPath();
      ctx.arc(6 + r() * (T - 12), 6 + r() * (T - 12), 2, 0, TAU);
      ctx.fill();
    }
  }

  function drawDirt(ctx, x, y) {
    const r = rng(x, y, 3);
    ctx.fillStyle = shade(PAL.dirt, 0.95 + r() * 0.1);
    ctx.fillRect(0, 0, T, T);
    const n = 5 + Math.floor(r() * 5);
    for (let i = 0; i < n; i++) {
      ctx.fillStyle = r() < 0.5 ? PAL.dirtDark : PAL.dirtLight;
      ctx.beginPath();
      ctx.ellipse(4 + r() * (T - 8), 4 + r() * (T - 8), 1.5 + r() * 2.5, 1.2 + r() * 1.8, r() * TAU, 0, TAU);
      ctx.fill();
    }
    ctx.strokeStyle = "rgba(90,66,40,0.35)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    const yy = T * (0.3 + r() * 0.4);
    ctx.moveTo(0, yy);
    ctx.bezierCurveTo(T * 0.3, yy - 6, T * 0.6, yy + 6, T, yy - 2);
    ctx.stroke();
  }

  function drawWall(ctx, x, y) {
    ctx.fillStyle = PAL.wallTop;
    ctx.fillRect(0, 0, T, T);
    const r = rng(x, y, 4);
    ctx.strokeStyle = PAL.wallLine;
    ctx.lineWidth = 2;
    const rows = 4;
    const rh = T / rows;
    for (let i = 0; i < rows; i++) {
      ctx.beginPath();
      ctx.moveTo(0, i * rh);
      ctx.lineTo(T, i * rh);
      ctx.stroke();
      const off = i % 2 === 0 ? 0 : T / 4;
      for (let bx = off; bx < T; bx += T / 2) {
        ctx.beginPath();
        ctx.moveTo(bx, i * rh);
        ctx.lineTo(bx, (i + 1) * rh);
        ctx.stroke();
      }
    }
    for (let i = 0; i < 3; i++) {
      ctx.fillStyle = `rgba(255,255,255,${0.04 + r() * 0.05})`;
      ctx.fillRect(Math.floor(r() * 2) * (T / 2) + 2, Math.floor(r() * rows) * rh + 2, T / 2 - 4, rh - 4);
    }
    // 牆面（下方不是牆時畫出立面，讓牆看起來是凸起的）
    if (U.terrainAt(x, y + 1) !== "wall") {
      ctx.fillStyle = PAL.wallFace;
      ctx.fillRect(0, T - 9, T, 9);
      ctx.fillStyle = "rgba(255,255,255,0.08)";
      ctx.fillRect(0, T - 9, T, 1.5);
    }
  }

  function drawChasm(ctx, x, y) {
    const r = rng(x, y, 5);
    const g = ctx.createLinearGradient(0, 0, 0, T);
    g.addColorStop(0, "#05050a");
    g.addColorStop(1, PAL.chasm);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, T, T);
    for (let i = 0; i < 4; i++) {
      ctx.fillStyle = `rgba(140,130,200,${0.15 + r() * 0.2})`;
      ctx.fillRect(r() * T, r() * T, 1.5, 1.5);
    }
    // 邊緣崖壁：相鄰不是深淵的方向畫出鋸齒岩緣
    const lip = (dx, dy) => U.terrainAt(x + dx, y + dy) !== "chasm";
    ctx.fillStyle = PAL.chasmLip;
    const jag = (x0, y0, x1, y1, nx, ny) => {
      ctx.beginPath();
      ctx.moveTo(x0, y0);
      const steps = 6;
      for (let i = 0; i <= steps; i++) {
        const t = i / steps;
        const d = 3 + r() * 5;
        ctx.lineTo(x0 + (x1 - x0) * t + nx * d, y0 + (y1 - y0) * t + ny * d);
      }
      ctx.lineTo(x1, y1);
      ctx.closePath();
      ctx.fill();
    };
    if (lip(0, -1)) {
      jag(0, 0, T, 0, 0, 1);
      // 上方崖壁：看得見的縱深
      const gg = ctx.createLinearGradient(0, 0, 0, 16);
      gg.addColorStop(0, "rgba(70,64,80,0.9)");
      gg.addColorStop(1, "rgba(70,64,80,0)");
      ctx.fillStyle = gg;
      ctx.fillRect(0, 0, T, 16);
      ctx.fillStyle = PAL.chasmLip;
    }
    if (lip(0, 1)) jag(0, T, T, T, 0, -1);
    if (lip(-1, 0)) jag(0, 0, 0, T, 1, 0);
    if (lip(1, 0)) jag(T, 0, T, T, -1, 0);
  }

  function drawLava(ctx, x, y) {
    const r = rng(x, y, 6);
    ctx.fillStyle = PAL.lava;
    ctx.fillRect(0, 0, T, T);
    const glow = ctx.createRadialGradient(T / 2, T / 2, 2, T / 2, T / 2, T * 0.7);
    glow.addColorStop(0, "rgba(255,210,80,0.55)");
    glow.addColorStop(1, "rgba(255,210,80,0)");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, T, T);
    // 冷卻的岩殼
    const n = 4 + Math.floor(r() * 3);
    for (let i = 0; i < n; i++) {
      const cx = r() * T;
      const cy = r() * T;
      const rad = 5 + r() * 7;
      ctx.fillStyle = PAL.lavaCrust;
      ctx.beginPath();
      for (let k = 0; k < 7; k++) {
        const a = (k / 7) * TAU;
        const rr = rad * (0.7 + r() * 0.4);
        const px = cx + Math.cos(a) * rr;
        const py = cy + Math.sin(a) * rr;
        if (k === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = "rgba(255,208,74,0.5)";
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }

  function drawDeepWater(ctx, x, y) {
    const r = rng(x, y, 7);
    ctx.fillStyle = PAL.deep;
    ctx.fillRect(0, 0, T, T);
    ctx.strokeStyle = rgba(PAL.deepLight, 0.6);
    ctx.lineWidth = 1.5;
    ctx.lineCap = "round";
    for (let i = 0; i < 3; i++) {
      const wx = 6 + r() * (T - 20);
      const wy = 8 + r() * (T - 16);
      ctx.beginPath();
      ctx.moveTo(wx, wy);
      ctx.quadraticCurveTo(wx + 4, wy - 3, wx + 8, wy);
      ctx.quadraticCurveTo(wx + 12, wy + 3, wx + 16, wy);
      ctx.stroke();
    }
    // 與陸地相接處的冰緣
    ctx.fillStyle = "rgba(220,240,255,0.55)";
    if (U.terrainAt(x, y - 1) !== "ice_hole") ctx.fillRect(0, 0, T, 4);
    if (U.terrainAt(x - 1, y) !== "ice_hole") ctx.fillRect(0, 0, 4, T);
    if (U.terrainAt(x + 1, y) !== "ice_hole") ctx.fillRect(T - 4, 0, 4, T);
    if (U.terrainAt(x, y + 1) !== "ice_hole") ctx.fillRect(0, T - 4, T, 4);
  }

  const TERRAIN_DRAW = {
    stone: drawStone, grass: drawGrass, dirt: drawDirt, wall: drawWall,
    chasm: drawChasm, lava: drawLava, ice_hole: drawDeepWater,
  };

  // 高度：越高越亮（與目前的色階規則一致），並在「下方較低」的邊畫出崖面，在較低的鄰格投下陰影
  function heightLight(ctx, h) {
    if (h <= 0) return;
    ctx.fillStyle = `rgba(255,248,230,${0.07 * h})`;
    ctx.fillRect(0, 0, T, T);
  }
  function cliffs(ctx, x, y) {
    const h = U.heightAt(x, y);
    if (h <= 0 || U.BLOCKED.has(U.terrainAt(x, y))) return;
    const below = U.heightAt(x, y + 1);
    if (y + 1 < S.h && below < h) {
      const d = (h - below) * 5;
      ctx.fillStyle = "#5b4a3a";
      ctx.fillRect(0, T - d, T, d);
      ctx.fillStyle = "rgba(0,0,0,0.25)";
      for (let i = 0; i < h - below; i++) ctx.fillRect(0, T - d + i * 5, T, 1);
      ctx.fillStyle = "rgba(255,255,255,0.25)";
      ctx.fillRect(0, T - d - 1, T, 1.5);
    }
    // 左右邊：細邊線
    ctx.fillStyle = "rgba(40,30,20,0.45)";
    if (U.heightAt(x - 1, y) < h) ctx.fillRect(0, 0, 2, T);
    if (U.heightAt(x + 1, y) < h) ctx.fillRect(T - 2, 0, 2, T);
  }
  function castShadow(ctx, x, y) {
    const h = U.heightAt(x, y);
    const above = U.heightAt(x, y - 1);
    const left = U.heightAt(x - 1, y);
    if (y > 0 && above > h) {
      const g = ctx.createLinearGradient(0, 0, 0, 8 + (above - h) * 4);
      g.addColorStop(0, "rgba(0,0,0,0.35)");
      g.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, T, 8 + (above - h) * 4);
    }
    if (x > 0 && left > h) {
      const g = ctx.createLinearGradient(0, 0, 10, 0);
      g.addColorStop(0, "rgba(0,0,0,0.25)");
      g.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, 10, T);
    }
  }
  function heightBadge(ctx, h) {
    if (h <= 0) return;
    // 左上角小標籤：▲＋數字（取代每格都寫 0 的數字）
    roundRect(ctx, 3, 3, 19, 13, 4);
    ctx.fillStyle = "rgba(30,24,18,0.7)";
    ctx.fill();
    ctx.fillStyle = "#fff3c4";
    ctx.beginPath();
    ctx.moveTo(6, 13);
    ctx.lineTo(9.5, 6);
    ctx.lineTo(13, 13);
    ctx.closePath();
    ctx.fill();
    ctx.font = '700 10px "Noto Sans TC","Microsoft JhengHei",sans-serif';
    ctx.textBaseline = "middle";
    ctx.fillText(String(h), 14, 10);
  }

  // ==== 表面：相鄰同種表面連成一片（像水窪），不是一格一格的方塊 ====
  function surfaceBlob(ctx, x, y, s, color, alpha) {
    const same = (dx, dy) => U.surfaceAt(x + dx, y + dy) === s;
    const inset = 4;
    ctx.fillStyle = rgba(color, alpha);
    const l = same(-1, 0) ? 0 : inset;
    const t = same(0, -1) ? 0 : inset;
    const rr = same(1, 0) ? 0 : inset;
    const b = same(0, 1) ? 0 : inset;
    ctx.beginPath();
    ctx.roundRect(l, t, T - l - rr, T - t - b, [
      l && t ? 12 : 0, rr && t ? 12 : 0, rr && b ? 12 : 0, l && b ? 12 : 0,
    ]);
    ctx.fill();
  }
  function drawSurface(ctx, x, y, s) {
    const r = rng(x, y, 20);
    if (s === "water") {
      surfaceBlob(ctx, x, y, s, PAL.water, 0.78);
      ctx.strokeStyle = "rgba(220,240,255,0.7)";
      ctx.lineWidth = 1.5;
      for (let i = 0; i < 2; i++) {
        const wx = 8 + r() * (T - 26);
        const wy = 12 + r() * (T - 22);
        ctx.beginPath();
        ctx.moveTo(wx, wy);
        ctx.quadraticCurveTo(wx + 5, wy - 4, wx + 10, wy);
        ctx.stroke();
      }
    } else if (s === "ice") {
      surfaceBlob(ctx, x, y, s, PAL.ice, 0.85);
      ctx.strokeStyle = "rgba(120,180,220,0.7)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      const cx = T * (0.3 + r() * 0.4);
      const cy = T * (0.3 + r() * 0.4);
      for (let i = 0; i < 4; i++) {
        const a = r() * TAU;
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(a) * 18, cy + Math.sin(a) * 18);
      }
      ctx.stroke();
      ctx.strokeStyle = "rgba(255,255,255,0.9)";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(10, T - 16);
      ctx.lineTo(18, T - 24);
      ctx.stroke();
    } else if (s === "oil") {
      surfaceBlob(ctx, x, y, s, PAL.oil, 0.85);
      const g = ctx.createLinearGradient(10, 10, 40, 30);
      g.addColorStop(0, "rgba(160,90,220,0.35)");
      g.addColorStop(0.5, "rgba(80,200,160,0.30)");
      g.addColorStop(1, "rgba(230,200,80,0.25)");
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.ellipse(T * (0.35 + r() * 0.3), T * (0.35 + r() * 0.3), 12, 6, r() * TAU, 0, TAU);
      ctx.fill();
    } else if (s === "fire") {
      surfaceBlob(ctx, x, y, s, "#7a2a10", 0.6);
      const glow = ctx.createRadialGradient(T / 2, T * 0.6, 2, T / 2, T * 0.6, T * 0.6);
      glow.addColorStop(0, "rgba(255,200,60,0.8)");
      glow.addColorStop(1, "rgba(255,90,20,0)");
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, T, T);
      for (let i = 0; i < 3; i++) flame(ctx, 10 + i * 15 + r() * 6, T - 8 - r() * 8, 9 + r() * 5);
    } else if (s === "poison") {
      surfaceBlob(ctx, x, y, s, PAL.poison, 0.7);
      for (let i = 0; i < 4; i++) {
        ctx.strokeStyle = "rgba(220,255,180,0.8)";
        ctx.fillStyle = "rgba(160,230,100,0.6)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(8 + r() * (T - 16), 8 + r() * (T - 16), 2 + r() * 3, 0, TAU);
        ctx.fill();
        ctx.stroke();
      }
    }
  }
  function flame(ctx, x, y, h) {
    const w = h * 0.55;
    ctx.fillStyle = "#ff8a1e";
    ctx.beginPath();
    ctx.moveTo(x, y - h);
    ctx.bezierCurveTo(x + w, y - h * 0.4, x + w, y, x, y);
    ctx.bezierCurveTo(x - w, y, x - w, y - h * 0.4, x, y - h);
    ctx.fill();
    ctx.fillStyle = "#ffe07a";
    ctx.beginPath();
    ctx.moveTo(x, y - h * 0.55);
    ctx.bezierCurveTo(x + w * 0.5, y - h * 0.2, x + w * 0.45, y, x, y);
    ctx.bezierCurveTo(x - w * 0.45, y, x - w * 0.5, y - h * 0.2, x, y - h * 0.55);
    ctx.fill();
  }

  // ==== 物件 ====
  function shadowEllipse(ctx, cx, cy, rx, ry) {
    ctx.fillStyle = "rgba(0,0,0,0.28)";
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU);
    ctx.fill();
  }
  function flammableMark(ctx) {
    // 右上角小火苗：可燃
    ctx.save();
    ctx.translate(T - 9, 12);
    ctx.fillStyle = "rgba(20,12,6,0.65)";
    ctx.beginPath();
    ctx.arc(0, -2, 6.5, 0, TAU);
    ctx.fill();
    flame(ctx, 0, 3, 9);
    ctx.restore();
  }
  const OBJECT_DRAW = {
    crate(ctx) {
      shadowEllipse(ctx, T / 2 + 3, T / 2 + 5, T * 0.34, T * 0.3);
      const s = T * 0.62;
      const o = (T - s) / 2;
      roundRect(ctx, o, o, s, s, 3);
      ctx.fillStyle = PAL.wood;
      ctx.fill();
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = PAL.woodDark;
      ctx.stroke();
      ctx.strokeStyle = PAL.woodMid;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      for (let i = 1; i < 3; i++) {
        ctx.moveTo(o + 2, o + (s * i) / 3);
        ctx.lineTo(o + s - 2, o + (s * i) / 3);
      }
      ctx.stroke();
      ctx.strokeStyle = PAL.woodDark;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(o + 3, o + 3);
      ctx.lineTo(o + s - 3, o + s - 3);
      ctx.stroke();
      ctx.fillStyle = "rgba(255,255,255,0.18)";
      ctx.fillRect(o + 2, o + 2, s - 4, 3);
    },
    oil_barrel(ctx) {
      shadowEllipse(ctx, T / 2 + 3, T / 2 + 5, T * 0.3, T * 0.28);
      const c = T / 2;
      const r = T * 0.29;
      // 桶身（略往下偏，露出一截側面）＋桶蓋
      ctx.fillStyle = "#4a2a12";
      roundRect(ctx, c - r, c - r + 4, r * 2, r * 2, r);
      ctx.fill();
      ctx.fillStyle = "#8a5228";
      ctx.beginPath();
      ctx.arc(c, c, r, 0, TAU);
      ctx.fill();
      ctx.strokeStyle = "rgba(60,32,12,0.55)";
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      for (let k = -2; k <= 2; k++) {
        ctx.moveTo(c + k * r * 0.36, c - Math.sqrt(r * r - (k * r * 0.36) ** 2) + 1);
        ctx.lineTo(c + k * r * 0.36, c + Math.sqrt(r * r - (k * r * 0.36) ** 2) - 1);
      }
      ctx.stroke();
      ctx.lineWidth = 3;
      ctx.strokeStyle = "#9aa0a8";
      ctx.beginPath();
      ctx.arc(c, c, r - 1.5, 0, TAU);
      ctx.stroke();
      // 警示：黃黑斜紋帶＋油滴
      ctx.save();
      ctx.beginPath();
      ctx.arc(c, c, r * 0.5, 0, TAU);
      ctx.clip();
      ctx.fillStyle = "#f2b33d";
      ctx.fillRect(c - r, c - r, r * 2, r * 2);
      ctx.fillStyle = "#1a120a";
      ctx.beginPath();
      ctx.moveTo(c, c - 5.5);
      ctx.bezierCurveTo(c + 5, c + 0.5, c + 4, c + 5, c, c + 5);
      ctx.bezierCurveTo(c - 4, c + 5, c - 5, c + 0.5, c, c - 5.5);
      ctx.fill();
      ctx.restore();
    },
    stone_pillar(ctx) {
      // 八角石柱：往右下拉長的影子表示「很高、擋視線」
      const c = T / 2;
      const r = T * 0.3;
      const oct = (cx, cy, rad) => {
        ctx.beginPath();
        for (let k = 0; k < 8; k++) {
          const a = (k / 8) * TAU + Math.PI / 8;
          ctx.lineTo(cx + Math.cos(a) * rad, cy + Math.sin(a) * rad);
        }
        ctx.closePath();
      };
      ctx.fillStyle = "rgba(0,0,0,0.3)";
      ctx.beginPath();
      ctx.moveTo(c - r * 0.7, c + r * 0.7);
      ctx.lineTo(c + r * 0.7, c - r * 0.7);
      ctx.lineTo(c + r * 0.7 + 12, c - r * 0.7 + 12);
      ctx.lineTo(c - r * 0.7 + 12, c + r * 0.7 + 12);
      ctx.fill();
      oct(c + 12, c + 12, r);
      ctx.fill();
      ctx.fillStyle = PAL.rockDark;
      oct(c, c + 5, r);
      ctx.fill();
      ctx.fillRect(c - r * 0.92, c, r * 1.84, 5);
      ctx.fillStyle = PAL.rock;
      oct(c, c, r);
      ctx.fill();
      ctx.fillStyle = "#bdb9af";
      oct(c, c, r * 0.62);
      ctx.fill();
      ctx.strokeStyle = "rgba(80,76,70,0.7)";
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(c - 3, c - r + 2);
      ctx.lineTo(c + 1, c - 5);
      ctx.lineTo(c - 2, c + 2);
      ctx.stroke();
    },
    low_wall(ctx, o) {
      const joinL = U.objectAt(o.x - 1, o.y)?.kind === "low_wall";
      const joinR = U.objectAt(o.x + 1, o.y)?.kind === "low_wall";
      const x0 = joinL ? 0 : 5;
      const x1 = joinR ? T : T - 5;
      const y0 = T * 0.36;
      const h = T * 0.3;
      ctx.fillStyle = "rgba(0,0,0,0.28)";
      ctx.fillRect(x0 + 3, y0 + h, x1 - x0, 6);
      ctx.fillStyle = "#6e675c";
      ctx.fillRect(x0, y0 + h - 5, x1 - x0, 5);
      ctx.fillStyle = "#9b9385";
      ctx.fillRect(x0, y0, x1 - x0, h - 5);
      ctx.strokeStyle = "#5c564c";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      for (let bx = x0 + 13; bx < x1 - 2; bx += 13) {
        ctx.moveTo(bx, y0);
        ctx.lineTo(bx, y0 + h - 5);
      }
      ctx.moveTo(x0, y0 + (h - 5) / 2);
      ctx.lineTo(x1, y0 + (h - 5) / 2);
      ctx.stroke();
    },
    wooden_bridge(ctx, o) {
      // 木橋：與鄰格相接，沿著橋的方向鋪板
      ctx.fillStyle = "#7a5028";
      ctx.fillRect(0, 7, T, T - 14);
      ctx.strokeStyle = "#4b2f15";
      ctx.lineWidth = 1.5;
      for (let px = 0; px <= T; px += T / 6) {
        ctx.beginPath();
        ctx.moveTo(px, 8);
        ctx.lineTo(px, T - 8);
        ctx.stroke();
      }
      const r = rng(o.x, o.y, 30);
      for (let px = 0; px < T; px += T / 6) {
        ctx.fillStyle = `rgba(255,220,170,${0.05 + r() * 0.12})`;
        ctx.fillRect(px + 1, 8, T / 6 - 2, T - 16);
      }
      ctx.fillStyle = "#4b2f15";
      ctx.fillRect(0, 4, T, 4);
      ctx.fillRect(0, T - 8, T, 4);
    },
    fallen_log(ctx) {
      ctx.save();
      ctx.translate(T / 2, T / 2);
      ctx.rotate(-0.5);
      ctx.fillStyle = "rgba(0,0,0,0.28)";
      roundRect(ctx, -T * 0.4 + 3, -7 + 6, T * 0.8, 15, 7);
      ctx.fill();
      ctx.fillStyle = "#7a5130";
      roundRect(ctx, -T * 0.4, -8, T * 0.8, 16, 8);
      ctx.fill();
      ctx.strokeStyle = "#4e3119";
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(-T * 0.3, -3);
      ctx.lineTo(T * 0.1, -3);
      ctx.moveTo(-T * 0.2, 3);
      ctx.lineTo(T * 0.2, 3);
      ctx.stroke();
      ctx.fillStyle = "#d1a86e";
      ctx.beginPath();
      ctx.ellipse(T * 0.36, 0, 5, 8, 0, 0, TAU);
      ctx.fill();
      ctx.strokeStyle = "#8a6038";
      ctx.beginPath();
      ctx.ellipse(T * 0.36, 0, 2.5, 4.5, 0, 0, TAU);
      ctx.stroke();
      ctx.restore();
    },
    earth_wall(ctx) {
      shadowEllipse(ctx, T / 2 + 3, T / 2 + 6, T * 0.42, T * 0.3);
      roundRect(ctx, 5, 9, T - 10, T - 16, 10);
      ctx.fillStyle = "#8a6a45";
      ctx.fill();
      ctx.fillStyle = "#a7845a";
      roundRect(ctx, 8, 9, T - 16, T * 0.35, 8);
      ctx.fill();
      ctx.strokeStyle = "#5e4529";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(9, T * 0.58);
      ctx.lineTo(T - 9, T * 0.55);
      ctx.moveTo(10, T * 0.7);
      ctx.lineTo(T - 12, T * 0.72);
      ctx.stroke();
    },
    dead_tree(ctx) {
      shadowEllipse(ctx, T / 2 + 4, T / 2 + 5, T * 0.36, T * 0.3);
      ctx.strokeStyle = "#4a3624";
      ctx.lineCap = "round";
      const branch = (x, y, a, len, w, depth) => {
        const x2 = x + Math.cos(a) * len;
        const y2 = y + Math.sin(a) * len;
        ctx.lineWidth = w;
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x2, y2);
        ctx.stroke();
        if (depth > 0) {
          branch(x2, y2, a - 0.5, len * 0.6, w * 0.6, depth - 1);
          branch(x2, y2, a + 0.6, len * 0.55, w * 0.6, depth - 1);
        }
      };
      for (let k = 0; k < 5; k++) branch(T / 2, T / 2, (k / 5) * TAU + 0.3, T * 0.2, 4, 1);
      ctx.fillStyle = "#5c4430";
      ctx.beginPath();
      ctx.arc(T / 2, T / 2, 6, 0, TAU);
      ctx.fill();
    },
  };
  function drawGenericObject(ctx) {
    // 沒有畫法的新物件：灰色六角形＋問號（不會出錯）
    ctx.fillStyle = "#888";
    ctx.beginPath();
    for (let k = 0; k < 6; k++) {
      const a = (k / 6) * TAU;
      ctx.lineTo(T / 2 + Math.cos(a) * 16, T / 2 + Math.sin(a) * 16);
    }
    ctx.fill();
  }

  // ==== 單位：棋子（token）。底盤是陣營色，尖角指向朝向；中央是依職業／武器的白色徽記 ====
  const ROLE = {
    hero_fighter: "sword", hero_mage: "staff", hero_archer: "bow", hero_stormcaller: "staff",
    bandit: "dagger", bandit_archer: "bow", bandit_shieldbearer: "shield", bandit_warlord: "axe", bandit_boss: "crown",
    summon_skeleton_warrior: "skull", summon_elemental_spirit: "flame", summon_war_totem: "totem", summon_afterimage: "ghost",
  };
  function emblem(ctx, kind, color) {
    ctx.save();
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.lineWidth = 2.6;
    switch (kind) {
      case "sword":
        ctx.beginPath();
        ctx.moveTo(0, -10); ctx.lineTo(0, 6);
        ctx.moveTo(-6, 4); ctx.lineTo(6, 4);
        ctx.moveTo(0, 6); ctx.lineTo(0, 10);
        ctx.stroke();
        break;
      case "dagger":
        ctx.beginPath();
        ctx.moveTo(-5, 8); ctx.lineTo(5, -6);
        ctx.moveTo(-6, 1); ctx.lineTo(1, 7);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(5, -6); ctx.lineTo(8, -9); ctx.lineTo(6, -4);
        ctx.fill();
        break;
      case "staff":
        ctx.beginPath();
        ctx.moveTo(-5, 10); ctx.lineTo(3, -4);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(5, -7, 4.5, 0, TAU);
        ctx.fill();
        break;
      case "bow":
        ctx.beginPath();
        ctx.arc(-3, 0, 10, -1.2, 1.2);
        ctx.stroke();
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(-3 + Math.cos(-1.2) * 10, Math.sin(-1.2) * 10);
        ctx.lineTo(-3 + Math.cos(1.2) * 10, Math.sin(1.2) * 10);
        ctx.moveTo(-6, 0); ctx.lineTo(10, 0);
        ctx.stroke();
        break;
      case "shield":
        ctx.beginPath();
        ctx.moveTo(0, -10); ctx.lineTo(8, -6); ctx.lineTo(7, 3); ctx.lineTo(0, 10); ctx.lineTo(-7, 3); ctx.lineTo(-8, -6);
        ctx.closePath();
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, -6); ctx.lineTo(0, 6);
        ctx.stroke();
        break;
      case "axe":
        ctx.beginPath();
        ctx.moveTo(-4, 10); ctx.lineTo(4, -8);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(2, -5); ctx.quadraticCurveTo(12, -6, 9, 4); ctx.lineTo(0, -1);
        ctx.fill();
        break;
      case "crown":
        ctx.beginPath();
        ctx.moveTo(-9, 6); ctx.lineTo(-9, -5); ctx.lineTo(-4.5, 0); ctx.lineTo(0, -8); ctx.lineTo(4.5, 0); ctx.lineTo(9, -5); ctx.lineTo(9, 6);
        ctx.closePath();
        ctx.fill();
        break;
      case "skull":
        ctx.beginPath();
        ctx.arc(0, -2, 8, 0, TAU);
        ctx.fill();
        ctx.fillRect(-5, 3, 10, 6);
        ctx.fillStyle = "#103c36";
        ctx.beginPath();
        ctx.arc(-3, -2, 2.4, 0, TAU);
        ctx.arc(3, -2, 2.4, 0, TAU);
        ctx.fill();
        break;
      case "flame":
        flame(ctx, 0, 9, 18);
        break;
      default:
        break;
    }
    ctx.restore();
  }
  function drawUnit(ctx, u) {
    const cx = u.x * T + T / 2;
    const cy = u.y * T + T / 2;
    const r = T * 0.33;
    const [dx, dy] = U.FACING[u.facing];
    const fill = u.summon ? PAL.summon : u.team === "ally" ? PAL.ally : PAL.enemy;
    const ring = u.summon ? PAL.summonRing : u.team === "ally" ? PAL.allyRing : PAL.enemyRing;
    ctx.save();
    ctx.translate(cx, cy);
    shadowEllipse(ctx, 3, 5, r + 2, r * 0.9);
    if (u.active) {
      ctx.setLineDash([6, 4]);
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = PAL.active;
      ctx.beginPath();
      ctx.arc(0, 0, r + 8, 0, TAU);
      ctx.stroke();
      ctx.setLineDash([]);
    }
    // 底盤＋朝向尖角（同一個形狀，像俯視的棋子）
    const a = Math.atan2(dy, dx);
    ctx.save();
    ctx.rotate(a);
    ctx.beginPath();
    if (u.summon) {
      // 召喚物：六角底盤
      for (let k = 0; k < 6; k++) {
        const ang = (k / 6) * TAU + Math.PI / 6;
        ctx.lineTo(Math.cos(ang) * r * 1.05, Math.sin(ang) * r * 1.05);
      }
      ctx.closePath();
    } else {
      ctx.arc(0, 0, r, 0.55, TAU - 0.55);
      ctx.lineTo(r + 9, 0);
      ctx.closePath();
    }
    ctx.fillStyle = fill;
    ctx.fill();
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = ring;
    ctx.stroke();
    if (u.summon) {
      ctx.beginPath();
      ctx.moveTo(r * 1.05, -6);
      ctx.lineTo(r + 10, 0);
      ctx.lineTo(r * 1.05, 6);
      ctx.closePath();
      ctx.fillStyle = ring;
      ctx.fill();
    }
    ctx.restore();
    // 內圈陰影，徽記更清楚
    ctx.fillStyle = "rgba(0,0,0,0.18)";
    ctx.beginPath();
    ctx.arc(0, 1.5, r * 0.72, 0, TAU);
    ctx.fill();
    if (u.hero) {
      ctx.strokeStyle = "rgba(255,255,255,0.9)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(0, 0, r * 0.8, 0, TAU);
      ctx.stroke();
    }
    emblem(ctx, ROLE[u.template] ?? "sword", "#ffffff");
    // 代號小標
    ctx.font = '700 11px "Noto Sans TC","Microsoft JhengHei",sans-serif';
    const tw = Math.max(13, ctx.measureText(u.marker).width + 6);
    roundRect(ctx, -T * 0.48, -T * 0.48, tw, 14, 4);
    ctx.fillStyle = "rgba(15,18,24,0.8)";
    ctx.fill();
    ctx.fillStyle = "#fff";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(u.marker, -T * 0.48 + tw / 2, -T * 0.48 + 7.5);
    // 血條：圓角
    const w = T * 0.78;
    roundRect(ctx, -w / 2, T * 0.38, w, 6, 3);
    ctx.fillStyle = "rgba(10,10,14,0.85)";
    ctx.fill();
    roundRect(ctx, -w / 2 + 1, T * 0.38 + 1, (w - 2) * u.hp, 4, 2);
    ctx.fillStyle = U.hpColor(u.hp);
    ctx.fill();
    ctx.restore();
  }

  // ==== 單位：紙娃娃小人（paperdoll.js）。腳下是陣營色底圈，圈上的尖角＝朝向 ====
  function drawUnitFigure(ctx, u) {
    const cx = u.x * T + T / 2;
    const cy = u.y * T + T / 2;
    const [dx, dy] = U.FACING[u.facing];
    const fill = u.summon ? PAL.summon : u.team === "ally" ? PAL.ally : PAL.enemy;
    const ring = u.summon ? PAL.summonRing : u.team === "ally" ? PAL.allyRing : PAL.enemyRing;
    const footY = T * 0.3;
    const rx = T * 0.36;
    const ry = T * 0.17;
    ctx.save();
    ctx.translate(cx, cy);
    // 底圈
    ctx.fillStyle = "rgba(0,0,0,0.3)";
    ctx.beginPath();
    ctx.ellipse(1.5, footY + 2, rx + 1, ry + 1, 0, 0, TAU);
    ctx.fill();
    ctx.fillStyle = rgba(fill, 0.55);
    ctx.strokeStyle = ring;
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    ctx.ellipse(0, footY, rx, ry, 0, 0, TAU);
    ctx.fill();
    ctx.stroke();
    // 朝向尖角（貼在底圈外緣）
    const ex = dx * rx;
    const ey = footY + dy * ry;
    ctx.beginPath();
    ctx.moveTo(ex + dx * 9, ey + dy * 6);
    ctx.lineTo(ex - dy * 5 + dx * 0, ey + dx * 4);
    ctx.lineTo(ex + dy * 5, ey - dx * 4);
    ctx.closePath();
    ctx.fillStyle = ring;
    ctx.fill();
    ctx.strokeStyle = "rgba(0,0,0,0.6)";
    ctx.lineWidth = 1;
    ctx.stroke();
    if (u.active) {
      ctx.setLineDash([5, 3]);
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = PAL.active;
      ctx.beginPath();
      ctx.ellipse(0, footY, rx + 5, ry + 4, 0, 0, TAU);
      ctx.stroke();
      ctx.setLineDash([]);
    }
    ctx.restore();
    const unit = PaperDoll.TEMPLATES[u.template] ?? PaperDoll.TEMPLATES.bandit;
    PaperDoll.stamp(ctx, unit, u.facing, cx, cy + footY + 1, 1.0);
    ctx.save();
    ctx.translate(cx, cy);
    // 代號小標與血條（與棋子版相同）
    ctx.font = '700 11px "Noto Sans TC","Microsoft JhengHei",sans-serif';
    const tw = Math.max(13, ctx.measureText(u.marker).width + 6);
    roundRect(ctx, -T * 0.5, -T * 0.5, tw, 14, 4);
    ctx.fillStyle = u.summon ? "rgba(18,80,72,0.9)" : u.team === "ally" ? "rgba(30,70,150,0.92)" : "rgba(150,30,30,0.92)";
    ctx.fill();
    ctx.fillStyle = "#fff";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(u.marker, -T * 0.5 + tw / 2, -T * 0.5 + 7.5);
    const w = T * 0.78;
    roundRect(ctx, -w / 2, T * 0.42, w, 6, 3);
    ctx.fillStyle = "rgba(10,10,14,0.85)";
    ctx.fill();
    roundRect(ctx, -w / 2 + 1, T * 0.42 + 1, (w - 2) * u.hp, 4, 2);
    ctx.fillStyle = U.hpColor(u.hp);
    ctx.fill();
    ctx.restore();
  }

  function render(canvas, scale = 2, opts = {}) {
    canvas.width = S.w * T * scale;
    canvas.height = S.h * T * scale;
    canvas.style.width = `${S.w * T}px`;
    canvas.style.height = `${S.h * T}px`;
    const ctx = canvas.getContext("2d");
    ctx.scale(scale, scale);
    const at = (x, y, fn) => {
      ctx.save();
      ctx.translate(x * T, y * T);
      ctx.beginPath();
      ctx.rect(0, 0, T, T);
      ctx.clip();
      fn();
      ctx.restore();
    };
    for (let y = 0; y < S.h; y++) {
      for (let x = 0; x < S.w; x++) {
        const t = U.terrainAt(x, y);
        at(x, y, () => {
          (TERRAIN_DRAW[t] ?? drawStone)(ctx, x, y);
          if (!U.BLOCKED.has(t)) heightLight(ctx, U.heightAt(x, y));
          const s = U.surfaceAt(x, y);
          if (s) drawSurface(ctx, x, y, s);
          castShadow(ctx, x, y);
          cliffs(ctx, x, y);
          // 細格線：只用很淡的線，讓地面連成一片又看得出格子
          ctx.strokeStyle = "rgba(0,0,0,0.14)";
          ctx.lineWidth = 1;
          ctx.strokeRect(0.5, 0.5, T - 1, T - 1);
        });
      }
    }
    for (const o of S.objects) {
      ctx.save();
      ctx.translate(o.x * T, o.y * T);
      (OBJECT_DRAW[o.kind] ?? drawGenericObject)(ctx, o);
      if (U.FLAMMABLE.has(o.kind) && o.kind !== "wooden_bridge") flammableMark(ctx);
      ctx.restore();
    }
    for (let y = 0; y < S.h; y++) {
      for (let x = 0; x < S.w; x++) {
        ctx.save();
        ctx.translate(x * T, y * T);
        heightBadge(ctx, U.heightAt(x, y));
        ctx.restore();
      }
    }
    const units = [...S.units].sort((a, b) => a.y - b.y);
    for (const u of units) (opts.units === "token" || !window.PaperDoll ? drawUnit : drawUnitFigure)(ctx, u);
  }

  return { render, flame, rng, PAL };
})();
