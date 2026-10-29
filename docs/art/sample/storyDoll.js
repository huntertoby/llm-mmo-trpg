// C 手繪墨線繪本畫風（使用者 10-29 選 C：「C畫風擴畫參考」）的擴畫樣張：參數化紙娃娃＋三種形態。
// 外觀仍由資料欄位決定（沿用 raceArt.js 的 look 欄位、paperdoll.js 的裝備 kind／color）；不認得的值＝不畫，不出錯。
// 座標：腳底在 (0,0)，往上是 -y；view = "front"（朝南）或 "side"（朝東，朝西由呼叫端鏡像）。
// 畫法共用一層：ink() = 水彩填色（略溢出、邊緣深一圈）＋兩次抖動墨線＋暗面斜排線。抖動用固定種子，同一部件每次畫都一樣。
window.StoryDoll = (() => {
  const TAU = Math.PI * 2;
  const INK = "#2b1e16";
  function hexRgb(h) { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
  function mix(a, b, t) {
    const [r1, g1, b1] = hexRgb(a), [r2, g2, b2] = hexRgb(b);
    const m = (x, y) => Math.round(x * (1 - t) + y * t);
    return `#${((m(r1, r2) << 16) | (m(g1, g2) << 8) | m(b1, b2)).toString(16).padStart(6, "0")}`;
  }
  const dark = (c, t = 0.3) => mix(c, "#000000", t);
  const light = (c, t = 0.3) => mix(c, "#ffffff", t);

  // ---- 畫法層 ----
  function seedOf(s) { let h = 2166136261; for (const ch of s) h = Math.imul(h ^ ch.charCodeAt(0), 16777619); return h >>> 0; }
  function rng(seed) { let s = seed >>> 0; return () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296); }
  function ellPts(cx, cy, rx, ry, n = 18) { return Array.from({ length: n }, (_, i) => [cx + Math.cos((i / n) * TAU) * rx, cy + Math.sin((i / n) * TAU) * ry]); }
  function wobble(pts, r, amt) { return pts.map(([x, y]) => [x + (r() - 0.5) * amt, y + (r() - 0.5) * amt]); }
  function smooth(ctx, pts, closed = true) {
    ctx.beginPath();
    const n = pts.length, mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
    if (!closed) { ctx.moveTo(...pts[0]); for (let i = 1; i < n - 1; i++) { const m = mid(pts[i], pts[i + 1]); ctx.quadraticCurveTo(pts[i][0], pts[i][1], m[0], m[1]); } ctx.lineTo(...pts[n - 1]); return; }
    const m0 = mid(pts[n - 1], pts[0]); ctx.moveTo(m0[0], m0[1]);
    for (let i = 0; i < n; i++) { const p = pts[i], m = mid(p, pts[(i + 1) % n]); ctx.quadraticCurveTo(p[0], p[1], m[0], m[1]); }
    ctx.closePath();
  }
  function outline(ctx, pts, sharp) {
    if (!sharp) return smooth(ctx, pts);
    ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath();
  }
  let SHADE = 1; // 1：暗面在右（正面，光從左上）；-1：暗面在左（側面朝東，背面較暗）
  function ink(ctx, key, pts, color, opt = {}) {
    const r = rng(seedOf(key));
    ctx.save(); ctx.translate(0.45, 0.35);
    outline(ctx, wobble(pts, r, 0.7), opt.sharp); ctx.globalAlpha = opt.alpha ?? 0.94; ctx.fillStyle = color; ctx.fill();
    ctx.globalAlpha = 0.35; ctx.strokeStyle = "rgba(0,0,0,0.55)"; ctx.lineWidth = 0.9; ctx.stroke();
    ctx.restore();
    if (opt.shade !== false) {
      let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
      for (const [x, y] of pts) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
      const w = x1 - x0, h = y1 - y0;
      if (w > 3 && h > 3) {
        ctx.save(); outline(ctx, pts, opt.sharp); ctx.clip();
        const a = SHADE > 0 ? x0 + w * 0.6 : x0 - h, b = SHADE > 0 ? x1 + h : x0 + w * 0.4;
        ctx.strokeStyle = "rgba(43,30,22,0.42)"; ctx.lineWidth = 0.35; ctx.beginPath();
        for (let x = a; x < b; x += 1.3) { ctx.moveTo(x, y0); ctx.lineTo(x - h * 0.9, y1); }
        ctx.stroke(); ctx.restore();
      }
    }
    if (opt.line === false) return;
    const w = opt.w ?? 0.85;
    ctx.strokeStyle = INK; ctx.lineJoin = "round"; ctx.lineCap = "round";
    ctx.lineWidth = w; outline(ctx, wobble(pts, r, 0.5), opt.sharp); ctx.stroke();
    ctx.lineWidth = w * 0.45; outline(ctx, wobble(pts, r, 0.85), opt.sharp); ctx.stroke();
  }
  function stroke(ctx, key, pts, w = 0.7, color = INK) {
    const r = rng(seedOf(key)); ctx.strokeStyle = color; ctx.lineWidth = w; ctx.lineCap = "round"; ctx.lineJoin = "round";
    smooth(ctx, wobble(pts, r, 0.35), false); ctx.stroke();
  }
  function limb(ctx, key, pts, w, color) { stroke(ctx, key, pts, w + 1.4, INK); stroke(ctx, key, pts, w, color); }
  function dot(ctx, x, y, rx, ry, c) { ctx.fillStyle = c; ctx.beginPath(); ctx.ellipse(x, y, rx, ry, 0, 0, TAU); ctx.fill(); }
  function shadow(ctx, rx = 9) {
    const r = rng(7); ctx.strokeStyle = "rgba(43,30,22,0.5)"; ctx.lineWidth = 0.5; ctx.beginPath();
    for (let x = -rx; x < rx; x += 2.2) { const j = r(); ctx.moveTo(x + j, 1.2); ctx.lineTo(x + j + 2.4, -0.6); }
    ctx.stroke();
  }
  const mirror = (pts) => pts.map(([x, y]) => [-x, y]);

  // ---- 材質色（沿用 paperdoll.js 的色票） ----
  const MAT = { cloth: "#8a8f99", leather: "#8a5a32", iron: "#8d969f", steel: "#c3ccd6", gold: "#e8bb48", wood: "#a06a36" };
  const colorOf = (it, fallback) => (it ? it.color ?? MAT[it.material] ?? fallback : fallback);
  const SKIN_LINE = (look) => look.skin ?? "#eab48a";

  // ============================== 尾巴 ==============================
  // 正面：從腰側往畫面右邊伸出；側面：往身後（西）伸出。畫在身體之前（身體會蓋住根部）。
  function tail(ctx, look, view) {
    const k = look.tail; if (!k) return;
    const s = view === "side" ? -1 : 1;
    const P = (pts) => pts.map(([x, y]) => [x * s, y]);
    if (k === "fox") {
      const c = look.tailColor ?? look.hairColor ?? "#d8762a";
      ink(ctx, `tail-fox-${view}`, P([[2, -16], [10, -17], [16, -10], [17, -3], [12, -1], [9, -8], [2, -11]]), c);
      ink(ctx, `tail-foxtip-${view}`, P([[14.6, -5], [17.4, -3.6], [15.6, -0.6], [12.4, -1.4]]), "#f4ece0", { shade: false, w: 0.6 });
    } else if (k === "demon") {
      const c = look.tailColor ?? dark(look.skin ?? "#b07a7a", 0.3);
      stroke(ctx, `tail-dm-${view}`, P([[2, -13], [9, -12], [13, -6], [13.6, -1.6]]), 1.9, INK);
      stroke(ctx, `tail-dm2-${view}`, P([[2, -13], [9, -12], [13, -6], [13.6, -1.6]]), 1.1, c);
      ink(ctx, `tail-dmtip-${view}`, P([[13.6, -2.4], [11.2, 0.6], [13.8, 3.2], [16, 0.4]]), c, { shade: false, w: 0.6 });
    } else {
      // scaled／dragon：粗尾巴，龍裔另有背刺
      const c = look.tailColor ?? look.scaleColor ?? dark(look.skin ?? "#a8784a", 0.15);
      const thick = k === "dragon" ? 1.35 : 1;
      ink(ctx, `tail-sc-${view}`, P([[1, -17 * thick + 1], [10, -14], [17, -5], [21, 0.6], [15, 0], [8, -6], [1, -9]]), c);
      if (k === "dragon" || look.spines) for (const t of [0.25, 0.48, 0.7]) {
        const x = 2 + 16 * t, y = -15 + 13 * t;
        ink(ctx, `spine-${t}-${view}`, P([[x - 1.6, y - 0.4], [x + 0.2, y - 4.2], [x + 1.8, y + 0.2]]), light(c, 0.35), { shade: false, w: 0.5 });
      }
    }
  }

  // ============================== 腿、身體 ==============================
  function legs(ctx, unit, view) {
    const { look, gear } = unit, pants = look.pants ?? "#3c3c52", boot = colorOf(gear.feet, "#6a4224");
    const heavy = gear.body?.kind === "plate";
    const greave = heavy ? MAT.steel : boot;
    if (view !== "side") {
      for (const sx of [-1, 1]) {
        ink(ctx, `leg-${sx}`, [[sx * 0.8, -15], [sx * 4.6, -15], [sx * 4.4, -6], [sx * 1, -6]], heavy ? MAT.iron : pants);
        ink(ctx, `boot-${sx}`, [[sx * 0.6, heavy ? -9 : -7], [sx * 4.8, heavy ? -9 : -7], [sx * 5.6, -0.8], [sx * 0.4, -0.4]], greave);
      }
    } else {
      ink(ctx, "leg-far", [[-3, -15], [0.6, -15], [-0.6, -6], [-3.8, -6]], dark(heavy ? MAT.iron : pants, 0.25));
      ink(ctx, "boot-far", [[-4.2, heavy ? -9 : -7], [-0.4, heavy ? -9 : -7], [1, -0.6], [-4.4, -0.4]], dark(greave, 0.25));
      ink(ctx, "leg-near", [[-0.6, -15], [3.2, -15], [3.8, -6], [0.6, -6]], heavy ? MAT.iron : pants);
      ink(ctx, "boot-near", [[0.4, heavy ? -9 : -7], [4, heavy ? -9 : -7], [7.4, -0.8], [0.4, -0.4]], greave);
    }
  }
  const TORSO = {
    front: [[-7, -33], [7, -33], [6, -23], [8, -14], [0, -12.5], [-8, -14], [-6, -23]],
    side: [[-4, -33], [3.4, -33], [5, -27], [4, -22], [5.2, -14], [-1, -12.5], [-5.6, -14], [-4.2, -22]],
  };
  const ROBE = {
    front: [[-7, -33], [7, -33], [6, -23], [10, -1.6], [0, -0.6], [-10, -1.6], [-6, -23]],
    side: [[-4, -33], [3.4, -33], [5, -27], [4, -22], [7.4, -1.6], [-1, -0.8], [-7.6, -1.6], [-4.2, -22]],
  };
  TORSO.back = TORSO.front; ROBE.back = ROBE.front;
  function body(ctx, unit, view) {
    const it = unit.gear.body, kind = it?.kind ?? "shirt", F = view !== "side", BK = view === "back";
    const c = colorOf(it, "#4f7fbf");
    if (kind === "robe") {
      ink(ctx, `robe-${view}`, ROBE[view], c);
      const trim = it.trim ?? MAT.gold;
      if (BK) stroke(ctx, "robe-hem-b", [[-9.6, -3.2], [0, -2.2], [9.6, -3.2]], 1.2, trim);
      else if (F) {
        stroke(ctx, "robe-mid", [[0, -31], [0, -1.4]], 1.4, trim); stroke(ctx, "robe-mid2", [[0, -31], [0, -1.4]], 0.4);
        stroke(ctx, "robe-hem", [[-9.6, -3.2], [0, -2.2], [9.6, -3.2]], 1.2, trim);
      } else {
        stroke(ctx, "robe-hem-s", [[-7.2, -3.2], [-1, -2.4], [7, -3.2]], 1.2, trim);
      }
      stroke(ctx, `sash-${view}`, F ? [[-6.2, -23], [6.2, -23]] : [[-4.2, -23], [4.4, -23]], 1.8, dark(c, 0.4));
      return;
    }
    ink(ctx, `torso-${view}`, TORSO[view], kind === "plate" ? MAT.steel : kind === "mail" ? MAT.iron : c);
    if (kind === "leather") {
      if (!BK) stroke(ctx, `stitch-${view}`, F ? [[-3.6, -31], [-2.4, -24]] : [[0.6, -31], [1.6, -24]], 0.4);
      if (F && !BK) stroke(ctx, "stitch2", [[3.6, -31], [2.4, -24]], 0.4);
    }
    if (kind === "plate") {
      if (F) {
        stroke(ctx, "plate-c", [[0, -32], [0, -24]], 0.5); stroke(ctx, "plate-f", [[-7.4, -18.6], [0, -17.4], [7.4, -18.6]], 0.5);
        for (const sx of [-1, 1]) ink(ctx, `pauldron-${sx}`, ellPts(sx * 7.2, -31.4, 3.6, 2.8, 12), MAT.steel, { w: 0.7 });
      } else {
        stroke(ctx, "plate-fs", [[-5, -18.6], [5, -18.6]], 0.5);
        ink(ctx, "pauldron-s", ellPts(-0.4, -31.4, 3.8, 2.9, 12), MAT.steel, { w: 0.7 });
      }
    }
    if (kind === "shirt" && F && !BK) stroke(ctx, "collar", [[-2.4, -33], [0, -30.4], [2.4, -33]], 0.5);
    // 腰帶
    const bx = F ? 6.2 : 4.3;
    stroke(ctx, `belt-${view}`, [[F ? -bx : -4.2, -23], [bx, -23]], 1.7, INK);
    stroke(ctx, `belt2-${view}`, [[F ? -bx : -4.2, -23], [bx, -23]], 0.9, "#6b4426");
    if (F && !BK) { ctx.fillStyle = MAT.gold; ctx.fillRect(-1.2, -24.3, 2.4, 2.6); stroke(ctx, "buckle", [[-1.2, -24.3], [1.2, -24.3], [1.2, -21.7], [-1.2, -21.7], [-1.2, -24.3]], 0.4); }
  }
  function cloak(ctx, unit, view) {
    const it = unit.gear.cloak; if (!it) return;
    const c = colorOf(it, "#a83030");
    if (view !== "side") ink(ctx, `cloak-${view}`, [[-8, -33], [8, -33], [11, -8], [5, -6], [0, -7.5], [-5, -6], [-11, -8]], c);
    else ink(ctx, "cloak-s", [[-3, -33], [1, -33], [-4, -9], [-10, -6.5], [-13, -9], [-8, -22]], c);
  }

  // ============================== 武器 ==============================
  // 主手：正面在畫面左手 (-9,-23.2)；側面在近側手 (4.6,-24)。
  function weapon(ctx, it, key, view, hand) {
    if (!it) return;
    const [hx, hy] = hand, F = view !== "side";
    const metal = colorOf(it.material === "wood" ? null : it, MAT.steel);
    ctx.save(); ctx.translate(hx, hy);
    // 正面武器豎起；側面往前上斜（劍、斧、匕首）或直立（法杖、弓）
    // 正面匕首往外斜 0.5 rad，刀身落在身體外（C-1b 驗收：板甲上看不到）
    const tilt = F ? (it.kind === "dagger" ? -0.5 : 0) : 0.75;
    switch (it.kind) {
      case "sword": case "dagger": {
        const L = it.kind === "sword" ? 21 : 10;
        ctx.rotate(tilt);
        ink(ctx, `${key}-blade`, [[-1.1, -2], [-1, -L + 1.6], [0, -L], [1, -L + 1.6], [1.1, -2]], metal, { shade: false, w: 0.7 });
        ink(ctx, `${key}-guard`, [[-3.4, -3.2], [3.4, -3.2], [3.4, -1.6], [-3.4, -1.6]], MAT.gold, { shade: false, w: 0.6 });
        break;
      }
      case "axe": {
        ctx.rotate(tilt * 0.8);
        if (F) ctx.scale(-1, 1); // 正面大刃朝外，不蓋到臉（C-1b 驗收）
        ink(ctx, `${key}-haft`, [[-0.8, 9], [0.8, 9], [0.8, -24], [-0.8, -24]], MAT.wood, { shade: false, w: 0.6 });
        ink(ctx, `${key}-head`, [[0.6, -23], [7.6, -27], [9.4, -20.6], [7.6, -14], [0.6, -18]], metal, { w: 0.8 });
        ink(ctx, `${key}-head2`, [[-0.6, -22.4], [-4.6, -24.4], [-5.2, -20.4], [-4.6, -16.6], [-0.6, -18.6]], metal, { w: 0.7 });
        break;
      }
      case "staff": {
        ink(ctx, `${key}-pole`, [[-0.8, 22], [0.8, 22], [0.9, -27], [-0.9, -27]], MAT.wood, { shade: false, w: 0.6 });
        const glow = it.glow ?? "#8fe3ff";
        const g = ctx.createRadialGradient(0, -30, 0.5, 0, -30, 8); g.addColorStop(0, glow); g.addColorStop(1, "rgba(143,227,255,0)");
        ctx.fillStyle = g; ctx.globalAlpha = 0.55; ctx.beginPath(); ctx.arc(0, -30, 8, 0, TAU); ctx.fill(); ctx.globalAlpha = 1;
        ink(ctx, `${key}-claw`, [[-3, -27], [-2.6, -33.4], [0, -29], [2.6, -33.4], [3, -27]], MAT.wood, { shade: false, w: 0.6 });
        ink(ctx, `${key}-orb`, ellPts(0, -30.4, 2.4, 2.4, 10), glow, { shade: false, w: 0.6 });
        break;
      }
      case "bow": {
        const s = F ? 1 : 1;
        stroke(ctx, `${key}-string`, [[2 * s, -15], [2 * s, 14]], 0.35, "#e8e0d0");
        ink(ctx, `${key}-limb`, [[1.6, -15], [-2.4, -9], [-3.6, 0], [-2.4, 8], [1.6, 14], [0.4, 14.4], [-4.4, 8], [-5.8, 0], [-4.4, -9], [0.4, -15.4]], MAT.wood, { shade: false, w: 0.6 });
        break;
      }
    }
    ctx.restore();
  }
  function offhand(ctx, it, view, behind) {
    if (!it) return;
    const F = view === "front";
    if (it.kind === "shield_round" || it.kind === "shield") {
      if (behind) return;
      const c = colorOf(it, "#2f5fae");
      if (F) {
        ink(ctx, "shield", ellPts(8.6, -21, 6.6, 7, 20), c, { w: 1 });
        stroke(ctx, "shield-rim", ellPts(8.6, -21, 5.2, 5.6, 20).concat([[13.8, -21]]), 0.45);
        ink(ctx, "shield-boss", ellPts(8.6, -21, 1.8, 1.8, 10), MAT.gold, { shade: false, w: 0.6 });
      } else ink(ctx, "shield-s", ellPts(7, -23, 2, 7, 14), c, { w: 0.8 });
      return;
    }
    // 成對武器：副手拿同類武器。正面在畫面右手鏡像；側面在遠側手，畫在身體後面、往前上錯開
    if (F) {
      if (behind) return;
      ctx.save(); ctx.scale(-1, 1); weapon(ctx, it, "off", view, [-9, -23.2]); ctx.restore();
    } else if (behind) {
      weapon(ctx, it, "off-s", view, [5.6, -27]);
      dot(ctx, 5.6, -27, 1.7, 1.7, dark(SKIN_LINE({}), 0.2));
    }
  }

  // ============================== 頭 ==============================
  const HEAD_SIDE = [[-8.6, -42], [-8, -49], [-2, -51.5], [5, -50], [8.4, -45], [8.2, -42], [9.6, -39.6], [8, -38.6], [6.6, -35], [0, -34], [-6.4, -36]];
  function hairBack(ctx, look, view) {
    if (look.hair !== "long") return;
    const c = look.hairColor ?? "#6a3a1e";
    if (view === "front") ink(ctx, "hair-back", [[-10, -44], [-9.6, -30], [-5, -29], [5, -29], [9.6, -30], [10, -44], [0, -52]], dark(c, 0.15));
    else ink(ctx, "hair-back-s", [[-9.6, -44], [-10.6, -29], [-5, -28.4], [-2, -34], [0, -46]], dark(c, 0.15));
  }
  function ears(ctx, look, view, stage) {
    const k = look.ears; if (!k) return;
    const c = look.skin ?? "#eab48a", F = view !== "side";
    if (k === "pointed" && stage === "under") {
      if (F) for (const sx of [-1, 1]) ink(ctx, `ear-p-${sx}`, [[sx * 8, -44], [sx * 15.6, -48.6], [sx * 9, -39.6]], c, { w: 0.7 });
    }
    if (k === "pointed" && stage === "over" && !F) ink(ctx, "ear-p-s", [[-1, -43.6], [-9.6, -48.6], [-1.6, -39.2]], c, { w: 0.7 });
    if (k === "fin" && stage === "under" && F) for (const sx of [-1, 1]) ink(ctx, `ear-f-${sx}`, [[sx * 8.4, -45], [sx * 14, -47.6], [sx * 13, -42], [sx * 14.4, -38.6], [sx * 8.4, -39]], light(c, 0.15), { w: 0.7 });
    if (k === "fin" && stage === "over" && !F) ink(ctx, "ear-f-s", [[-0.6, -45], [-7.4, -48.6], [-6, -42.4], [-7.8, -38.4], [-0.6, -39]], light(c, 0.15), { w: 0.7 });
    if (k === "beast" && stage === "top") {
      const hc = look.hairColor ?? "#d8762a";
      const pos = F ? [[-1, -5.6], [1, 5.6]] : [[-1, -5], [1, 0]];
      for (const [i, x] of pos) {
        const far = !F && i < 0;
        ink(ctx, `ear-b-${view}-${i}`, [[x - 3.6, -48.6], [x + (F ? i * 1.2 : -1.4), -57.6], [x + 3.4, -49]], far ? dark(hc, 0.2) : hc, { w: 0.8 });
        ink(ctx, `ear-bi-${view}-${i}`, [[x - 1.8, -49.4], [x + (F ? i * 0.8 : -1), -55], [x + 1.6, -49.6]], "#f2c4b8", { shade: false, line: false });
      }
    }
  }
  function face(ctx, look, view) {
    const F = view === "front";
    const eyes = F ? [-3.2, 3.2] : [4.4];
    for (const x of eyes) {
      if (look.slitEyes) { dot(ctx, x, -41, 1.3, 1.5, "#e8b830"); dot(ctx, x, -41, 0.35, 1.3, INK); }
      else dot(ctx, x, -41, 0.9, 1.3, look.eyes ?? INK);
    }
    ctx.fillStyle = "rgba(220,90,80,0.32)";
    for (const x of F ? [-5.4, 5.4] : [3.2]) { ctx.beginPath(); ctx.ellipse(x, -38.6, 1.6, 0.9, 0, 0, TAU); ctx.fill(); }
    if (!look.beard) stroke(ctx, `mouth-${view}`, F ? [[-1, -37.4], [0, -36.8], [1, -37.4]] : [[6.4, -37], [7.4, -36.6]], 0.5);
    const pc = look.scaleColor ?? look.markColor ?? dark(look.skin ?? "#eab48a", 0.25);
    if (look.pattern === "scales" || look.pattern === "dragonscale") {
      const at = F ? [[-6.6, -43.6], [-7.4, -41], [6.6, -43.6], [7.4, -41], [0, -48]] : [[1.6, -44], [0.4, -41.4], [2.6, -47.6]];
      for (const [x, y] of at) stroke(ctx, `scale-${x}-${y}`, [[x - 1.2, y], [x, y + 1], [x + 1.2, y]], 0.6, pc);
    } else if (look.pattern === "marks") {
      for (const sx of F ? [-1, 1] : [1]) { const x = F ? sx * 6 : 2.6; stroke(ctx, `mark-${sx}`, [[x - 1.4, -40.4], [x + 1.4, -39.4]], 0.8, pc); stroke(ctx, `mark2-${sx}`, [[x - 1.4, -38.6], [x + 1.4, -37.6]], 0.8, pc); }
    } else if (look.pattern === "circuit") {
      const x = F ? 5 : 1.4, cc = "#3ad0e8";
      stroke(ctx, "circ-1", [[x, -46], [x, -42.6], [x + 2.4, -41]], 0.6, cc); dot(ctx, x + 2.4, -41, 0.6, 0.6, cc); dot(ctx, x, -46, 0.6, 0.6, cc);
    }
    if (look.tusks) for (const x of F ? [-1.8, 1.8] : [6.6]) ink(ctx, `tusk-${x}`, [[x - 0.7, -36.4], [x, -39.2], [x + 0.7, -36.4]], "#f4ecd8", { shade: false, w: 0.45 });
    if (look.beard) {
      const c = look.hairColor ?? "#a8481e";
      if (F) ink(ctx, "beard", [[-7.6, -40], [-4, -37.6], [0, -38.2], [4, -37.6], [7.6, -40], [6.4, -32], [2.4, -28.6], [-2.4, -28.6], [-6.4, -32]], c);
      else ink(ctx, "beard-s", [[1, -38.6], [9, -37], [8, -32], [4.4, -28.8], [0.4, -31]], c);
    }
  }
  function hair(ctx, look, view, cover) {
    if (look.hair === "none" || !look.hair) return;
    if (cover.top) return; // 帽子蓋住頭頂：只留後髮（hairBack）
    const c = look.hairColor ?? "#6a3a1e";
    if (view === "front") ink(ctx, "hair-f", [[-9.6, -41], [-10, -48], [-5, -52.5], [2, -52.5], [8, -49.5], [10, -42], [8, -45], [5, -45.5], [2, -44], [-1, -46], [-4, -44.8], [-7, -45.5]], c);
    else ink(ctx, "hair-s", [[-9.2, -38], [-9.4, -47], [-4, -52.5], [3, -52.6], [8.6, -48.5], [9.4, -44.6], [6, -46], [3, -45.5], [1, -43], [-1.4, -41], [-2.6, -37], [-6, -35.4]], c);
  }
  function horns(ctx, look, view) {
    const k = look.horns; if (!k) return;
    const c = look.hornColor ?? "#e8d8b8", F = view !== "side";
    const one = (key, s, far) => {
      const P = (pts) => pts.map(([x, y]) => [x * s, y]);
      const col = far ? dark(c, 0.25) : c;
      if (k === "small") ink(ctx, key, P(F ? [[3, -50], [5.4, -56.4], [6.4, -49.4]] : [[0.6, -50.6], [-2, -57], [-2.6, -50]]), col, { w: 0.7 });
      else if (k === "curved") ink(ctx, key, P(F ? [[7.6, -48.6], [10.8, -51.8], [12.8, -55.4], [12.6, -59], [10.2, -55.6], [7.8, -53.4], [5, -52.4], [3.2, -50.4]] : [[-3.6, -49.4], [-7.2, -52], [-9.6, -55.2], [-10, -58.8], [-7.6, -55.2], [-5.2, -53.4], [-2.2, -52.8], [1, -51]]), col, { w: 0.7 });
      else ink(ctx, key, P(F ? [[3.4, -49.4], [8, -57], [14.4, -61.6], [10.6, -54.6], [7.2, -49]] : [[1.6, -49.6], [-4, -56.6], [-12.4, -60.6], [-7.6, -53], [-2, -47.6]]), col, { w: 0.8 });
    };
    if (F) { one("horn-l", -1, false); one("horn-r", 1, false); }
    else { one("horn-far", 1, true); ctx.save(); ctx.translate(2.2, 0.6); one("horn-near", 1, false); ctx.restore(); }
  }
  // 頭部裝備；回傳遮蓋範圍（同 raceArt.js 的 COVERS）
  const COVERS = { helmet: { top: true, side: true }, hood: { top: true, side: true }, wizard_hat: { top: true } };
  function headgear(ctx, it, view) {
    if (!it) return;
    const F = view !== "side", BK = view === "back", c = colorOf(it, "#7a5a3a");
    if (it.kind === "helmet") {
      const m = colorOf(it, MAT.steel);
      if (F) {
        ink(ctx, "helm", [[-10, -42], [-9.6, -49], [-4.6, -53.6], [4.6, -53.6], [9.6, -49], [10, -42], [10.4, -40], [-10.4, -40]], m);
        stroke(ctx, "helm-band", [[-10, -44.6], [10, -44.6]], 0.6);
        if (!BK) ink(ctx, "helm-nose", [[-0.9, -45], [0.9, -45], [0.7, -38.6], [-0.7, -38.6]], m, { shade: false, w: 0.5 });
      } else {
        ink(ctx, "helm-s", [[-9.8, -36], [-10, -47], [-4.6, -53.6], [3.6, -53.4], [8.8, -48.6], [9.6, -44], [6, -44.4], [2, -43], [0.4, -38.6], [-4, -36.4]], m);
        stroke(ctx, "helm-band-s", [[-9.8, -44.4], [9.4, -44.6]], 0.6);
      }
    } else if (it.kind === "hood") {
      if (BK) ink(ctx, "hood-b", [[-11, -36], [-11.4, -48], [-5, -55], [5, -55], [11.4, -48], [11, -36], [6, -33], [-6, -33]], c);
      else if (F) ink(ctx, "hood", [[-11, -36], [-11.4, -48], [-5, -55], [5, -55], [11.4, -48], [11, -36], [7.6, -36.6], [8.4, -45], [0, -48], [-8.4, -45], [-7.6, -36.6]], c);
      else ink(ctx, "hood-s", [[-11, -33], [-11.4, -46], [-5, -55], [4, -54.4], [9.6, -48.6], [9.4, -45], [4, -46.6], [0.6, -42], [-1.6, -36], [-6, -33.4]], c);
    } else if (it.kind === "wizard_hat") {
      if (F) {
        ink(ctx, "hat-brim", [[-14, -47], [-6, -50.6], [6, -50.6], [14, -47], [6, -45.4], [-6, -45.4]], c);
        ink(ctx, "hat-cone", [[-6.6, -49], [-2, -60], [4, -70], [3.6, -63], [6.6, -49]], c);
        stroke(ctx, "hat-band", [[-6.4, -50], [6.4, -50]], 1.4, it.trim ?? MAT.gold);
      } else {
        ink(ctx, "hat-brim-s", [[-13, -47.6], [-6, -51], [6, -51], [13, -47.6], [6, -46], [-6, -46]], c);
        ink(ctx, "hat-cone-s", [[-6, -49.6], [-4, -60], [-10, -69.6], [-2.4, -63], [6.4, -49.6]], c);
        stroke(ctx, "hat-band-s", [[-6, -50.4], [6.2, -50.4]], 1.4, it.trim ?? MAT.gold);
      }
    }
  }

  // ============================== 組合 ==============================
  function armFront(ctx, unit, sx) {
    const c = unit.gear.body?.kind === "plate" ? MAT.steel : colorOf(unit.gear.body, "#4f7fbf");
    ink(ctx, `arm-${sx}`, sx < 0 ? [[-7, -31.5], [-4.8, -31], [-7.4, -22.5], [-9.8, -23.5]] : [[7, -31.5], [4.8, -31], [7.4, -22.5], [9.8, -23.5]], c);
  }
  function hand(ctx, look, x, y, key) { ink(ctx, key, ellPts(x, y, 1.8, 1.8, 10), look.skin ?? "#eab48a", { shade: false, w: 0.6 }); }
  // 背面（朝北）：左右對調（主手在畫面右），看不到臉；披風、尾巴蓋在身體上，武器在身體後面
  function drawBack(ctx, unit) {
    const look = unit.look ?? {}, gear = unit.gear ?? {}, V = "back";
    const cover = COVERS[gear.head?.kind] ?? (gear.head ? { top: true } : {});
    ctx.scale(-1, 1);
    weapon(ctx, gear.main_hand, "main-b", V, [-9, -23.2]);
    const off = gear.off_hand, shield = off && off.kind.startsWith("shield");
    if (off && !shield) { ctx.save(); ctx.scale(-1, 1); weapon(ctx, off, "off-b", V, [-9, -23.2]); ctx.restore(); }
    legs(ctx, unit, V);
    body(ctx, unit, V);
    armFront(ctx, unit, -1); armFront(ctx, unit, 1);
    hand(ctx, look, -9, -23.2, "hand-bl"); hand(ctx, look, 9, -23.2, "hand-br");
    cloak(ctx, unit, V);
    tail(ctx, look, V);
    if (shield) {
      ink(ctx, "shield-b", ellPts(8.6, -21, 6.6, 7, 20), MAT.wood, { w: 1 });
      stroke(ctx, "shield-strap", [[5, -24], [12.2, -18]], 1.2, "#5a3a1e");
    }
    if (!cover.side) ears(ctx, look, V, "under");
    ink(ctx, "head-b", ellPts(0, -42, 9.2, 8.6), look.skin ?? "#eab48a", { w: 1 });
    if (look.hair && look.hair !== "none") { // 背面：帽子只蓋頭頂，後腦頭髮照畫
      const c = look.hairColor ?? "#6a3a1e";
      ink(ctx, "hair-b", look.hair === "long" ? [[-9.8, -44], [-6, -51.8], [6, -51.8], [9.8, -44], [9.6, -30], [0, -28.6], [-9.6, -30]] : [[-9.6, -42], [-6, -51.8], [6, -51.8], [9.6, -42], [8, -36], [0, -34.4], [-8, -36]], c);
    }
    if (!cover.top) ears(ctx, look, V, "top");
    headgear(ctx, gear.head, V);
    horns(ctx, look, V);
  }
  function draw(ctx, unit, view) {
    const look = unit.look ?? {}, gear = unit.gear ?? {}, F = view === "front";
    if (view === "back") { SHADE = -1; ctx.save(); if (look.build === "stout") ctx.scale(1.12, 0.88); else if (look.build === "tall") ctx.scale(0.96, 1.1); shadow(ctx); drawBack(ctx, unit); ctx.restore(); return; }
    SHADE = F ? 1 : -1;
    ctx.save();
    if (look.build === "stout") ctx.scale(1.12, 0.88); else if (look.build === "tall") ctx.scale(0.96, 1.1);
    shadow(ctx);
    const cover = COVERS[gear.head?.kind] ?? (gear.head ? { top: true } : {});
    cloak(ctx, unit, view);
    tail(ctx, look, view);
    hairBack(ctx, look, view);
    if (!F) offhand(ctx, gear.off_hand, view, true);
    legs(ctx, unit, view);
    body(ctx, unit, view);
    if (F) { armFront(ctx, unit, 1); offhand(ctx, gear.off_hand, view, false); if (gear.off_hand && gear.off_hand.kind !== "shield_round") hand(ctx, look, 9, -23.2, "hand-r"); else if (!gear.off_hand) hand(ctx, look, 9, -23.2, "hand-r"); }
    else offhand(ctx, gear.off_hand, view, false);
    if (!cover.side) ears(ctx, look, view, "under");
    ink(ctx, `head-${view}`, F ? ellPts(0, -42, 9.2, 8.6) : HEAD_SIDE, look.skin ?? "#eab48a", { w: 1 });
    if (!F) ink(ctx, "ear-s", ellPts(-2.6, -40, 1.4, 1.9, 10), look.skin ?? "#eab48a", { shade: false, w: 0.6 });
    face(ctx, look, view);
    hair(ctx, look, view, cover);
    if (!cover.side) ears(ctx, look, view, "over");
    if (!cover.top) ears(ctx, look, view, "top");
    headgear(ctx, gear.head, view);
    horns(ctx, look, view);
    // 主手手臂＋武器
    if (F) {
      armFront(ctx, unit, -1);
      weapon(ctx, gear.main_hand, "main", view, [-9, -23.2]);
      hand(ctx, look, -9, -23.2, "hand-l");
    } else {
      const c = gear.body?.kind === "plate" ? MAT.steel : colorOf(gear.body, "#4f7fbf");
      ink(ctx, "arm-s", [[-1.4, -31.5], [1.4, -31.8], [5, -25], [2.6, -23.6]], c);
      weapon(ctx, gear.main_hand, "main-s", view, [4.6, -24]);
      hand(ctx, look, 4.6, -24, "hand-s");
    }
    ctx.restore();
  }

  // ============================== 形態（側面朝東） ==============================
  // 規則沿用 formArt.js：另畫、帶主角主色（hero）、比召喚物大一號，腳下形態光環由這裡一起畫。
  function aura(ctx, color, rx) {
    ctx.save(); ctx.globalAlpha = 0.85; ctx.setLineDash([2.4, 1.6]);
    stroke(ctx, `aura-${rx}`, ellPts(0, 0, rx, rx * 0.3, 24).concat([[rx, 0]]), 1.1, color);
    ctx.restore(); ctx.save(); ctx.globalAlpha = 0.18; ctx.fillStyle = color; ctx.beginPath(); ctx.ellipse(0, 0, rx, rx * 0.3, 0, 0, TAU); ctx.fill(); ctx.restore();
  }
  const FORMS = {
    bear: { zh: "熊", size: 1.3, draw(ctx, h) {
      const c = mix("#6a4a32", h, 0.3);
      for (const [x, far] of [[-11, 1], [6, 1]]) ink(ctx, `bear-legf-${x}`, [[x - 2.8, -12], [x + 2.8, -12], [x + 3, 0], [x - 3, 0]], dark(c, 0.25 * far));
      ink(ctx, "bear-body", [[-17, -9], [-17, -22], [-8, -29.6], [4, -29], [14, -22], [15, -9], [-2, -7]], c);
      for (const x of [-8, -2, 4]) stroke(ctx, `bear-stripe-${x}`, [[x, -28], [x + 2, -21]], 2, h);
      for (const x of [-6, 11]) ink(ctx, `bear-leg-${x}`, [[x - 3, -12], [x + 3, -12], [x + 3.4, 0], [x - 3.2, 0]], c);
      ink(ctx, "bear-head", [[9, -26], [14, -31], [21, -29.4], [25.6, -23], [23.6, -19.6], [16, -18], [10, -20]], c);
      ink(ctx, "bear-ear", ellPts(13.6, -30.6, 2.2, 2.2, 10), c, { shade: false, w: 0.7 });
      ink(ctx, "bear-snout", ellPts(23.4, -22.2, 2.6, 2, 10), light(c, 0.3), { shade: false, w: 0.6 });
      dot(ctx, 25.2, -23, 0.9, 0.8, INK); dot(ctx, 18.6, -25.6, 0.8, 1.1, INK);
    } },
    werewolf: { zh: "狼人", size: 1.25, draw(ctx, h) {
      const c = mix("#5a5a66", h, 0.25);
      ink(ctx, "ww-legfar", [[-5, -16], [-1, -16], [-2, -6], [-6, 0], [-9.6, 0], [-5.6, -6]], dark(c, 0.25));
      ink(ctx, "ww-tail", [[-7, -18], [-16, -17], [-21, -11], [-17, -11.4], [-8, -13]], c);
      ink(ctx, "ww-body", [[-8, -18], [-7, -32], [0, -40], [8, -37], [8, -26], [4, -16], [-4, -14]], c);
      ink(ctx, "ww-chest", [[1, -36], [7, -34], [6.4, -24], [2, -22]], light(c, 0.35), { shade: false, w: 0.6 });
      for (const y of [-33, -29]) stroke(ctx, `ww-band-${y}`, [[-6, y], [-1, y - 1]], 1.6, h);
      ink(ctx, "ww-leg", [[-1, -16], [4, -16], [5, -6], [9.6, 0], [3, 0], [0, -6]], c);
      ink(ctx, "ww-ear", [[3, -45], [3.4, -53.6], [8, -46.6]], dark(c, 0.15), { w: 0.7, sharp: true });
      ink(ctx, "ww-head", [[0.6, -40], [2.6, -46.4], [8, -48.4], [12.6, -46], [20.6, -43.4], [21, -40.4], [14.6, -39], [12.4, -36.6], [6, -34.6]], c);
      ink(ctx, "ww-ear2", [[6.4, -46.6], [8.6, -54.6], [11.4, -46]], c, { w: 0.7, sharp: true });
      ink(ctx, "ww-jaw", [[12.6, -39], [19, -39.2], [14.6, -36.4], [11.6, -36.6]], light(c, 0.3), { shade: false, w: 0.5 });
      ink(ctx, "ww-fang", [[17, -39.2], [17.6, -37.4], [18.2, -39.2]], "#f4ecd8", { shade: false, w: 0.35, sharp: true });
      dot(ctx, 11.6, -43.6, 1, 0.75, "#ffd23a"); dot(ctx, 11.8, -43.6, 0.3, 0.6, INK); dot(ctx, 20.4, -42.4, 0.9, 0.8, INK);
      ink(ctx, "ww-arm", [[2, -34], [6, -36], [12, -27], [12.4, -22], [9.6, -23], [8, -27]], c);
      for (const d of [0, 1.4, 2.8]) stroke(ctx, `ww-claw-${d}`, [[10 + d * 0.6, -22.2], [10.6 + d * 0.6, -19.6]], 0.6, "#f4ecd8");
    } },
    dragon: { zh: "龍", size: 1.5, draw(ctx, h, el) {
      const c = mix("#8a3a2a", h, 0.3), e = { fire: "#ff7a1a", ice: "#8fe3ff", lightning: "#ffe14a" }[el] ?? "#ff7a1a";
      ink(ctx, "dr-wingfar", [[10, -29], [7, -40], [2, -49], [-7, -54], [-4.6, -46.4], [-6.4, -38.6], [-2, -40.4], [-1.6, -32.6], [2, -34], [2, -28]], dark(c, 0.3));
      for (const x of [-13, 4]) ink(ctx, `dr-legfar-${x}`, [[x - 2.6, -12], [x + 2.6, -12], [x + 2.4, 0], [x - 3, 0]], dark(c, 0.25));
      ink(ctx, "dr-tail", [[-14, -14], [-26, -12], [-34, -4], [-28, -4.6], [-14, -8]], c);
      ink(ctx, "dr-body", [[-17, -10], [-16, -22], [-6, -28], [8, -27], [16, -20], [14, -10], [0, -7.6]], c);
      ink(ctx, "dr-belly", [[-12, -10], [10, -10], [8, -15], [-10, -15]], light(c, 0.4), { shade: false, w: 0.5 });
      for (const x of [-10, -3, 4]) ink(ctx, `dr-spine-${x}`, [[x - 1.8, -27], [x, -31.4], [x + 1.8, -27]], h, { shade: false, w: 0.5 });
      for (const x of [-9, 9]) ink(ctx, `dr-leg-${x}`, [[x - 3, -12], [x + 3, -12], [x + 3.4, 0], [x - 3.4, 0]], c);
      ink(ctx, "dr-neck", [[8, -25], [14, -38], [19, -38], [16, -22]], c);
      ink(ctx, "dr-head", [[12, -38], [16, -44], [22, -43], [29, -39], [28, -35.6], [19, -34.4], [13.6, -35]], c);
      ink(ctx, "dr-horn", [[15, -42.6], [11, -50], [18, -43.6]], "#e8d8b8", { shade: false, w: 0.6 });
      dot(ctx, 20.4, -40.4, 1.1, 0.8, "#ffd23a"); dot(ctx, 20.4, -40.4, 0.3, 0.7, INK);
      ink(ctx, "dr-wing", [[6, -27], [2, -38], [-4, -48], [-14, -52], [-11, -44], [-13, -35.6], [-8, -37.6], [-8.4, -29.6], [-4, -31.6], [-4, -27]], c, { alpha: 0.96 });
      for (const [i, p] of [[-11, -44], [-8, -37.6], [-4, -31.6]].entries()) stroke(ctx, `dr-wing-bone${i}`, [[2, -38], p], 0.5);
      ctx.save(); ctx.globalAlpha = 0.85;
      ink(ctx, "dr-breath", [[29, -37.6], [36, -40.6], [34, -37.4], [38, -36], [33.6, -35.4], [36, -32.6], [29, -35.6]], e, { shade: false, w: 0.5 });
      ctx.restore();
    } },
    cat: { zh: "貓", size: 1.25, draw(ctx, h) {
      const c = mix("#3a3440", h, 0.35), d = dark(c, 0.3);
      for (const x of [-8, 10]) ink(ctx, `cat-legfar-${x}`, [[x - 1.6, -9], [x + 1.6, -9], [x + 1.8, 0], [x - 1.8, 0]], d, { shade: false, w: 0.6 });
      ink(ctx, "cat-tail", [[-12, -12.4], [-21, -14.6], [-23.6, -22], [-21.6, -25.4], [-19.4, -22.6], [-18.6, -16.6], [-12, -9]], c);
      ink(ctx, "cat-tailtip", [[-23.4, -21.6], [-21.6, -25.4], [-19.4, -22.6], [-21.2, -20.6]], h, { shade: false, w: 0.6 });
      ink(ctx, "cat-body", ellPts(0, -11, 14, 5, 20), c);
      for (const x of [-8, -3, 2]) stroke(ctx, "cat-spot" + x, [[x, -15], [x + 1.5, -10]], 1.6, h);
      for (const x of [-11, 7]) ink(ctx, "cat-leg" + x, [[x - 1.7, -9], [x + 1.7, -9], [x + 2, 0], [x - 2, 0]], c, { shade: false, w: 0.6 });
      for (const x of [13, 17.4]) ink(ctx, "cat-ear" + x, [[x - 2.2, -16.6], [x, -22.6], [x + 2.2, -16.6]], c, { w: 0.6, sharp: true });
      ink(ctx, "cat-head", ellPts(15, -14.5, 5.4, 4.6, 16), c);
      ink(ctx, "cat-muzzle", ellPts(19.2, -13, 2.2, 1.6, 10), light(c, 0.35), { shade: false, w: 0.5 });
      dot(ctx, 17.2, -15.4, 1.3, 0.9, "#ffe14d"); dot(ctx, 17.3, -15.4, 0.3, 0.8, INK); dot(ctx, 21, -13.4, 0.6, 0.5, INK);
    } },
    roc: { zh: "鳥", size: 1.2, draw(ctx, h) {
      const c = "#a07a4a", d = dark(c, 0.3);
      ctx.save(); ctx.translate(0, -16);
      ink(ctx, "roc-wingfar", [[-2, -4], [-12, -26], [-20, -30], [-16, -22], [-22, -24], [-14, -12], [-4, 2]], d, { sharp: true });
      ink(ctx, "roc-wingfar-tip", [[-12, -26], [-20, -30], [-16, -22], [-22, -24], [-17, -18]], dark(h, 0.2), { sharp: true, shade: false, w: 0.6 });
      ink(ctx, "roc-tail", [[-8, 2], [-18, 8], [-16, 2], [-20, 4], [-9, -1]], h, { sharp: true, shade: false, w: 0.6 });
      ink(ctx, "roc-body", ellPts(0, 0, 9, 6, 16), c);
      ink(ctx, "roc-belly", ellPts(1.5, 2, 6, 3, 12), "#f0e6d0", { shade: false, w: 0.5 });
      ink(ctx, "roc-wing", [[2, -4], [10, -28], [18, -34], [15, -24], [22, -27], [14, -12], [4, 2]], c, { sharp: true });
      ink(ctx, "roc-wing-tip", [[10, -28], [18, -34], [15, -24], [22, -27], [16, -19]], h, { sharp: true, shade: false, w: 0.6 });
      ink(ctx, "roc-crest", [[6, -7], [4, -12], [8, -8.4], [9, -13], [10, -7.5]], h, { sharp: true, shade: false, w: 0.5 });
      ink(ctx, "roc-head", ellPts(9, -4, 4.2, 4.2, 12), c);
      ink(ctx, "roc-beak", [[12.5, -5.2], [17, -3], [12.5, -1]], "#e8bb48", { sharp: true, shade: false, w: 0.5 });
      dot(ctx, 10.6, -5, 0.9, 0.9, INK);
      for (const x of [-2, 3]) { stroke(ctx, "roc-claw" + x, [[x, 5], [x, 9]], 1.4, "#e8bb48"); stroke(ctx, "roc-claw2" + x, [[x - 1.2, 9.6], [x, 8.6], [x + 1.2, 9.6]], 0.6); }
      ctx.restore();
    } },
    demon: { zh: "惡魔", size: 1.2, draw(ctx, h) {
      const skin = "#6a3a7a", wing = "#3a1a40";
      ink(ctx, "dm-wing-l", [[-3, -30], [-20, -42], [-17, -34], [-22, -32], [-16, -26], [-18, -20], [-4, -22]], wing, { sharp: true });
      ink(ctx, "dm-wing-r", [[3, -30], [18, -44], [16, -36], [21, -33], [15, -27], [17, -21], [4, -22]], wing, { sharp: true });
      limb(ctx, "dm-tail", [[-2, -14], [-8, -6], [-6, -2]], 1.4, skin);
      for (const x of [-3, 3]) ink(ctx, "dm-leg" + x, [[x - 1.8, -14], [x + 1.8, -14], [x + 2, 0], [x - 2, 0]], skin, { w: 0.6 });
      ink(ctx, "dm-torso", [[-7, -30], [7, -30], [7.4, -13], [-7.4, -13]], h);
      ink(ctx, "dm-hem", [[-7, -15], [7, -15], [5, -11], [-5, -11]], dark(h, 0.35), { shade: false, w: 0.6 });
      limb(ctx, "dm-arm-l", [[-7, -28], [-10, -19]], 2.6, skin); limb(ctx, "dm-arm-r", [[7, -28], [11, -20]], 2.6, skin);
      ink(ctx, "dm-blade-l", [[-10.6, -19], [-14.6, -33.6], [-13, -33.2], [-9.4, -19.6]], "#c8c0e0", { shade: false, w: 0.5, sharp: true });
      ink(ctx, "dm-blade-r", [[10.4, -20.4], [17.6, -33.6], [16, -33.4], [11.6, -19.6]], "#c8c0e0", { shade: false, w: 0.5, sharp: true });
      ink(ctx, "dm-head", ellPts(0, -36, 6, 6, 14), skin);
      for (const s of [-1, 1]) ink(ctx, "dm-horn" + s, [[s * 4, -40], [s * 8.6, -44], [s * 7, -50.4], [s * 6, -45], [s * 2, -41.4]], "#2a1a2a", { shade: false, w: 0.6 });
      for (const x of [-2.2, 2.2]) dot(ctx, x, -36, 1.1, 1.1, "#ff5a8a");
    } },
    giant: { zh: "巨人", size: 1.45, draw(ctx, h) {
      const skin = "#c89a78", sd = dark(skin, 0.25);
      for (const x of [-5, 5]) ink(ctx, "gi-leg" + x, [[x - 3, -16], [x + 3, -16], [x + 3.2, 0], [x - 3.2, 0]], sd, { w: 0.7 });
      limb(ctx, "gi-arm-far", [[-10, -35], [-13, -22]], 4.2, sd);
      ink(ctx, "gi-torso", [[-10, -38], [10, -38], [10.4, -18], [-10.4, -18]], skin);
      ink(ctx, "gi-cloth", [[-9, -20], [9, -20], [8, -12], [3, -14], [0, -11], [-4, -14], [-8, -12]], h);
      ink(ctx, "gi-pauldron", ellPts(-9, -36, 4.5, 3, 12), h, { w: 0.7 });
      ink(ctx, "gi-club", [[13, -21], [20, -38], [24.6, -40], [25.6, -46.4], [21, -47.6], [17.6, -40], [15.4, -23]], "#8a847e");
      limb(ctx, "gi-arm", [[10, -35], [14, -24]], 4.2, skin);
      ink(ctx, "gi-head", ellPts(0, -43, 6, 6, 14), skin);
      stroke(ctx, "gi-band", [[-6, -46.4], [6, -46.4]], 2.4, "#5a3a20");
      for (const x of [-2.2, 2.2]) dot(ctx, x, -43, 0.9, 1.2, INK);
    } },
    avatar: { zh: "元素化身", size: 1.2, draw(ctx, h, el) {
      const [ec, el2] = { fire: ["#ff7a1a", "#ffd04a"], ice: ["#8fe3ff", "#e8fbff"], lightning: ["#ffe14a", "#fff7c0"] }[el] ?? ["#ff7a1a", "#ffd04a"];
      ctx.save(); ctx.globalAlpha = 0.8;
      for (const [x, y, s] of [[-6, -4, 3], [5, -2, 2.5], [0, 1, 2]]) ink(ctx, "av-wisp" + x, ellPts(x, y, s, s, 10), ec, { shade: false, w: 0.5 });
      ctx.restore();
      ink(ctx, "av-body", [[-8, -32], [-9.6, -20], [-6, -9], [-3, -4.6], [0, -2], [3, -5], [6, -9], [9.6, -20], [8, -32]], ec);
      ink(ctx, "av-glow", [[-5, -30], [-5.6, -20], [-2, -12], [2, -12], [5.6, -20], [5, -30]], el2, { shade: false, line: false, alpha: 0.6 });
      limb(ctx, "av-arm-l", [[-8, -30], [-13, -20]], 3, ec); limb(ctx, "av-arm-r", [[8, -30], [13, -20]], 3, ec);
      if (el === "ice") for (const x of [-4, 0, 4]) ink(ctx, "av-ice" + x, [[x - 1.5, -42], [x, -48], [x + 1.5, -42]], "#ffffff", { sharp: true, shade: false, w: 0.5 });
      else for (const x of [-3, 0, 3]) ink(ctx, "av-flame" + x, [[x - 2, -42], [x, -49.6], [x + 2, -42]], ec, { sharp: true, shade: false, w: 0.5 });
      ink(ctx, "av-head", ellPts(0, -38, 6, 6, 14), el2);
      ink(ctx, "av-core", [[0, -27], [3.5, -23], [0, -19], [-3.5, -23]], h, { sharp: true, shade: false, w: 0.6 });
      for (const x of [-2.2, 2.2]) dot(ctx, x, -38, 1.1, 1.1, "#ffffff");
    } },
    shadow: { zh: "暗影形態", size: 1.2, draw(ctx, h) {
      const c = "#3a3248";
      ctx.save(); ctx.globalAlpha = 0.9;
      ink(ctx, "sh-body", [[-9, -34], [-11, -20], [-7.6, -8], [-4, -2], [0, -5], [3, -1], [6.6, -6], [11, -20], [9, -34]], c);
      ctx.restore();
      for (const s of [-1, 1]) ink(ctx, "sh-spike" + s, [[s * 9, -34], [s * 14, -38], [s * 6, -36]], c, { sharp: true, shade: false, w: 0.6 });
      limb(ctx, "sh-arm-l", [[-9, -30], [-14, -20], [-16, -14]], 2.4, c); limb(ctx, "sh-arm-r", [[9, -30], [14, -20], [17, -15]], 2.4, c);
      stroke(ctx, "sh-rib-l", [[-2, -26], [-6, -16], [-3, -8], [-8, -2]], 1.8, h);
      stroke(ctx, "sh-rib-r", [[2, -26], [5, -15], [2, -8], [6, -3]], 1.8, h);
      ink(ctx, "sh-head", ellPts(0, -39, 6, 6.5, 14), c);
      ctx.save(); ctx.shadowColor = h; ctx.shadowBlur = 3;
      for (const x of [-2.4, 2.4]) dot(ctx, x, -39, 1.6, 0.9, light(h, 0.5));
      ctx.restore();
    } },
    treant: { zh: "樹人", size: 1.3, draw(ctx, h) {
      const bark = "#6a4a2a", bd = dark(bark, 0.3), leaf = mix("#4a8a3a", h, 0.35);
      for (const x of [-5, 5]) ink(ctx, "tr-root" + x, [[x - 3, -14], [x + 3, -14], [x + 4, 0], [x + 1, -1.4], [x - 1.6, 0], [x - 4, 0]], bd, { w: 0.7 });
      ink(ctx, "tr-trunk", [[-8, -38], [8, -38], [8.6, -12], [-8.6, -12]], bark);
      for (const y of [-32, -25, -18]) stroke(ctx, "tr-bark" + y, [[-5, y], [-2, y + 3]], 0.6);
      limb(ctx, "tr-arm-l", [[-8, -32], [-15, -26], [-16, -18]], 2.8, bark); limb(ctx, "tr-arm-r", [[8, -32], [15, -27], [17, -20]], 2.8, bark);
      for (const [x, y, r] of [[-14, -28, 4], [16, -29, 4], [-6, -44, 7], [5, -45, 7.5], [0, -50, 6.5]]) ink(ctx, "tr-leaf" + x, ellPts(x, y, r, r * 0.92, 14), leaf);
      for (const x of [-2.4, 2.4]) dot(ctx, x, -32, 1.2, 1.2, "#ffe9a0");
    } },
  };
  function drawForm(ctx, id, spec) {
    const f = FORMS[id]; if (!f) return false;
    SHADE = -1;
    aura(ctx, spec.auraColor ?? "#9a86ff", spec.auraR ?? 20);
    shadow(ctx, 14);
    f.draw(ctx, spec.hero ?? "#4f7fbf", spec.element);
    return true;
  }

  function stamp(ctx, unit, view, cx, cy, k = 1, west = false) {
    ctx.save(); ctx.translate(cx, cy); ctx.scale(west ? -k : k, k); draw(ctx, unit, view); ctx.restore();
  }
  function stampForm(ctx, id, spec, cx, cy, k = 1, west = false) {
    ctx.save(); ctx.translate(cx, cy); ctx.scale(west ? -k : k, k); const ok = drawForm(ctx, id, spec); ctx.restore(); return ok;
  }
  return { draw, stamp, stampForm, FORMS, COVERS };
})();
