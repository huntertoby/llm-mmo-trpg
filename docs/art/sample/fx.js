// 戰場效果與狀態圖示的提案畫法（美術樣張，2026-10-23）。
// 全部是程式繪製；座標以 52px 的虛擬格為單位（同 terrainArt／objectArt）。
// 規則優先於圖：每個畫法都由資料欄位決定（狀態的 polarity、control_group、on_turn_start_damage…；
// 物件的 HP 比例、剩餘回合；陷阱的 trigger、陣營；區域的 affects、元素、anchor），不認得的值一律退回預設。
window.FX = (() => {
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
  const seedOf = (x, y, salt) => (x * 73856093) ^ (y * 19349663) ^ (salt * 83492791);
  function hexRgb(h) {
    const n = parseInt(h.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function rgba(h, a) {
    const [r, g, b] = hexRgb(h);
    return `rgba(${r},${g},${b},${a})`;
  }

  // ---- 元素色票（與技能圖示、召喚物共用的關鍵字色）----
  const ELEMENT = {
    fire: "#ff7a1a",
    ice: "#9fe6ff",
    lightning: "#ffe14a",
    poison: "#8fdc4a",
    holy: "#ffe9a0",
    shadow: "#a77bff",
    physical: "#e05050",
    earth: "#c8a060",
    wind: "#bff0d8",
    water: "#4aa3ff",
    none: "#d8d8e0",
  };
  const elementColor = (el) => ELEMENT[el] ?? ELEMENT.none;
  const TEAM = { player: "#5aa0ff", enemy: "#ff5a5a" };
  const GOOD = "#5fd07a";
  const BAD = "#ff5a5a";

  // =====================================================================
  // ② 戰場效果
  // =====================================================================

  /** 擋視線的表面（煙霧、黑暗）：畫在單位「之上」的半透明上層，蓋住單位下半身。 */
  function sightVeil(ctx, x, y, surface, gx, gy, t = 0) {
    const r = rng(seedOf(gx, gy, 7));
    const color = surface === "darkness" ? "#2a1640" : "#c9ccd2";
    const alpha = surface === "darkness" ? 0.55 : 0.5;
    ctx.save();
    for (let i = 0; i < 5; i++) {
      const px = x + 8 + r() * (T - 16) + Math.sin(t + i) * 2;
      const py = y + T * 0.45 + r() * T * 0.45;
      const rad = 9 + r() * 8;
      const g = ctx.createRadialGradient(px, py, 1, px, py, rad);
      g.addColorStop(0, rgba(color, alpha));
      g.addColorStop(1, rgba(color, 0));
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(px, py, rad, 0, TAU);
      ctx.fill();
    }
    if (surface === "darkness") {
      // 黑暗：幾點紫色微光，和煙霧分開
      ctx.fillStyle = rgba("#c9a0ff", 0.8);
      for (let i = 0; i < 3; i++) ctx.fillRect(x + 6 + r() * (T - 12), y + 6 + r() * (T - 12), 2, 2);
    }
    ctx.restore();
  }

  /** 物件受損的裂痕（breakable 物件共用）：HP ≤ 66% 細裂、≤ 33% 粗裂。 */
  function cracks(ctx, x, y, hpRatio, color = "#1a1a1a", box = [0.25, 0.2, 0.75, 0.75]) {
    if (hpRatio > 0.66) return;
    const heavy = hpRatio <= 0.33;
    const r = rng(seedOf(x, y, 11));
    const [x0, y0, x1, y1] = box.map((v, i) => (i % 2 === 0 ? x : y) + v * T);
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineCap = "round";
    ctx.lineWidth = heavy ? 2 : 1.3;
    const lines = heavy ? 3 : 1;
    for (let k = 0; k < lines; k++) {
      let px = x0 + r() * (x1 - x0);
      let py = y0 + r() * (y1 - y0) * 0.3;
      ctx.beginPath();
      ctx.moveTo(px, py);
      for (let s = 0; s < 4; s++) {
        px += (r() - 0.5) * 10;
        py += 4 + r() * 5;
        ctx.lineTo(Math.min(x1, Math.max(x0, px)), Math.min(y1, py));
      }
      ctx.stroke();
    }
    ctx.restore();
  }

  /** 剩餘回合的小徽章（暫時物件、區域、陷阱共用）：黑底圓、白字；最後一回合改橘色。 */
  function turnsBadge(ctx, cx, cy, n) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, 7.5, 0, TAU);
    ctx.fillStyle = "rgba(0,0,0,0.78)";
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = n <= 1 ? "#ffb03a" : "#e8e8ea";
    ctx.stroke();
    ctx.fillStyle = n <= 1 ? "#ffb03a" : "#ffffff";
    ctx.font = "bold 10px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(String(n), cx, cy + 0.5);
    ctx.restore();
  }

  function shadow(ctx, cx, cy, rx, ry, a = 0.32) {
    ctx.fillStyle = `rgba(0,0,0,${a})`;
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU);
    ctx.fill();
  }

  /** 冰牆：半透明的冰晶塊（有高度、擋視線）；最後一回合開始融化（滴水、變透明、頂部變圓）。 */
  function iceWall(ctx, x, y, o = {}) {
    const melting = (o.turns ?? 3) <= 1;
    const hp = o.hp ?? 1;
    shadow(ctx, x + T / 2 + 3, y + T * 0.82, T * 0.38, T * 0.12, 0.35);
    const a = melting ? 0.62 : 0.85;
    const top = y + (melting ? T * 0.14 : T * 0.04);
    const base = y + T * 0.84;
    const l = x + T * 0.12;
    const rr = x + T * 0.88;
    // 晶體外形：三根高低不一的冰柱連成一塊
    const pts = melting
      ? [[l, base], [l, top + 16], [l + 8, top + 6], [x + T * 0.42, top + 2], [x + T * 0.6, top + 8], [rr - 6, top + 10], [rr, top + 20], [rr, base]]
      : [[l, base], [l, top + 14], [l + 6, top + 4], [x + T * 0.34, top + 12], [x + T * 0.5, top], [x + T * 0.66, top + 10], [rr - 5, top + 6], [rr, top + 16], [rr, base]];
    ctx.save();
    ctx.beginPath();
    pts.forEach(([px, py], i) => (i ? ctx.lineTo(px, py) : ctx.moveTo(px, py)));
    ctx.closePath();
    const g = ctx.createLinearGradient(l, top, rr, base);
    g.addColorStop(0, rgba("#e8fbff", a));
    g.addColorStop(0.5, rgba("#8fd8f0", a));
    g.addColorStop(1, rgba("#3f9cc8", a));
    ctx.fillStyle = g;
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#163a52";
    ctx.stroke();
    ctx.clip();
    // 晶面：亮色斜線
    ctx.strokeStyle = rgba("#ffffff", 0.75);
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(l + 7, base - 6);
    ctx.lineTo(l + 13, top + 14);
    ctx.moveTo(x + T * 0.5, base - 4);
    ctx.lineTo(x + T * 0.47, top + 8);
    ctx.stroke();
    ctx.strokeStyle = rgba("#1d5f86", 0.5);
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(x + T * 0.34, top + 12);
    ctx.lineTo(x + T * 0.36, base);
    ctx.moveTo(x + T * 0.66, top + 10);
    ctx.lineTo(x + T * 0.64, base);
    ctx.stroke();
    ctx.restore();
    cracks(ctx, x, y, hp, "#123048", [0.2, 0.15, 0.8, 0.8]);
    if (melting) {
      // 水滴與底部水窪
      ctx.fillStyle = rgba("#4aa3ff", 0.55);
      ctx.beginPath();
      ctx.ellipse(x + T / 2, base + 2, T * 0.42, 4, 0, 0, TAU);
      ctx.fill();
      ctx.fillStyle = "#bfefff";
      for (const [dx, dy] of [[0.2, 0.62], [0.55, 0.7], [0.8, 0.58]]) {
        ctx.beginPath();
        ctx.ellipse(x + dx * T, y + dy * T, 1.6, 2.6, 0, 0, TAU);
        ctx.fill();
      }
    }
    if (o.turns != null) turnsBadge(ctx, x + T - 8, y + 8, o.turns);
  }

  /** 荊棘叢：一團交纏的藤蔓＋尖刺；最後一回合枯萎（褐色、刺變少）。 */
  function thornWall(ctx, x, y, o = {}) {
    const dry = (o.turns ?? 2) <= 1;
    const r = rng(seedOf(x, y, 3));
    shadow(ctx, x + T / 2 + 2, y + T * 0.74, T * 0.4, T * 0.14);
    const vine = dry ? "#7a5a30" : "#3f6a26";
    const vineHi = dry ? "#a07a44" : "#6aa040";
    // 底下一團暗色輪廓（讓荊棘從地面分出來）
    ctx.fillStyle = dry ? "#3a2a16" : "#1e3412";
    ctx.beginPath();
    ctx.ellipse(x + T / 2, y + T * 0.56, T * 0.42, T * 0.24, 0, 0, TAU);
    ctx.fill();
    ctx.lineCap = "round";
    for (let i = 0; i < 7; i++) {
      const sx = x + 6 + r() * (T - 12);
      const sy = y + T * 0.72;
      const ex = x + 6 + r() * (T - 12);
      const ey = y + T * 0.3 + r() * 8;
      ctx.strokeStyle = i % 2 ? vine : vineHi;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.quadraticCurveTo(x + r() * T, y + T * (0.2 + r() * 0.3), ex, ey);
      ctx.stroke();
      // 尖刺
      const n = dry ? 1 : 3;
      for (let k = 0; k < n; k++) {
        const tt = 0.25 + k * 0.25;
        const px = sx + (ex - sx) * tt;
        const py = sy + (ey - sy) * tt;
        ctx.fillStyle = dry ? "#d8c8a0" : "#f2ecd0";
        ctx.beginPath();
        ctx.moveTo(px - 2, py);
        ctx.lineTo(px, py - 6);
        ctx.lineTo(px + 2, py);
        ctx.fill();
      }
    }
    if (!dry) {
      ctx.fillStyle = "#c84a6a";
      for (let i = 0; i < 2; i++) {
        ctx.beginPath();
        ctx.arc(x + 12 + r() * (T - 24), y + T * 0.38 + r() * 10, 2.4, 0, TAU);
        ctx.fill();
      }
    }
    cracks(ctx, x, y, o.hp ?? 1, "#140c06");
    if (o.turns != null) turnsBadge(ctx, x + T - 8, y + 8, o.turns);
  }

  /** 倒塌物：大小石塊堆成的一堆（深色外框＋頂面亮色），一看就是「擋路、可躲」。 */
  function rubble(ctx, x, y, o = {}) {
    const r = rng(seedOf(x, y, 5));
    shadow(ctx, x + T / 2 + 3, y + T * 0.74, T * 0.42, T * 0.15, 0.4);
    const rocks = [
      [0.3, 0.62, 11], [0.62, 0.64, 12], [0.46, 0.46, 12], [0.76, 0.5, 8], [0.2, 0.46, 8], [0.5, 0.7, 7],
    ];
    for (const [rx, ry, s] of rocks) {
      const cx = x + rx * T;
      const cy = y + ry * T;
      const n = 5 + Math.floor(r() * 2);
      const pts = [];
      for (let i = 0; i < n; i++) {
        const ang = (i / n) * TAU + r() * 0.5;
        const rad = s * (0.75 + r() * 0.3);
        pts.push([cx + Math.cos(ang) * rad, cy + Math.sin(ang) * rad * 0.8]);
      }
      ctx.beginPath();
      pts.forEach(([px, py], i) => (i ? ctx.lineTo(px, py) : ctx.moveTo(px, py)));
      ctx.closePath();
      ctx.fillStyle = "#8d8376";
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = "#2a241d";
      ctx.stroke();
      // 頂面亮色
      ctx.fillStyle = "#b9ae9c";
      ctx.beginPath();
      ctx.ellipse(cx - s * 0.15, cy - s * 0.3, s * 0.5, s * 0.28, -0.3, 0, TAU);
      ctx.fill();
    }
    // 碎屑
    ctx.fillStyle = "#6e665b";
    for (let i = 0; i < 6; i++) ctx.fillRect(x + 6 + r() * (T - 12), y + T * 0.72 + r() * 8, 2.5, 2);
    cracks(ctx, x, y, o.hp ?? 1, "#1a1612");
  }

  /** 薄冰：架在冰窟上的冰板；裂痕隨 HP 增加，最後露出底下的黑水。 */
  function thinIce(ctx, x, y, o = {}) {
    const hp = o.hp ?? 1;
    ctx.fillStyle = "#0e2a44";
    ctx.fillRect(x, y, T, T);
    const r = rng(seedOf(x, y, 9));
    ctx.beginPath();
    ctx.roundRect(x + 3, y + 3, T - 6, T - 6, 8);
    ctx.fillStyle = rgba("#cdeeff", hp <= 0.33 ? 0.62 : 0.85);
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#e8fbff";
    ctx.stroke();
    // 冰下的暗影（看得出下面是冰窟）
    ctx.fillStyle = rgba("#0e2a44", 0.25);
    ctx.beginPath();
    ctx.ellipse(x + T / 2, y + T / 2, T * 0.26, T * 0.2, 0.3, 0, TAU);
    ctx.fill();
    // 裂痕：從中心放射
    const rays = hp > 0.66 ? 2 : hp > 0.33 ? 4 : 7;
    ctx.strokeStyle = hp <= 0.33 ? "#0e2a44" : "#4a7a9a";
    ctx.lineWidth = hp <= 0.33 ? 2 : 1.3;
    ctx.beginPath();
    for (let i = 0; i < rays; i++) {
      const ang = (i / rays) * TAU + r();
      let px = x + T / 2;
      let py = y + T / 2;
      ctx.moveTo(px, py);
      for (let s = 0; s < 3; s++) {
        px += Math.cos(ang + (r() - 0.5) * 0.8) * 7;
        py += Math.sin(ang + (r() - 0.5) * 0.8) * 7;
        ctx.lineTo(px, py);
      }
    }
    ctx.stroke();
    if (hp <= 0.33) {
      // 破洞：露出黑水
      ctx.fillStyle = "#081a2c";
      ctx.beginPath();
      ctx.moveTo(x + T * 0.44, y + T * 0.42);
      ctx.lineTo(x + T * 0.58, y + T * 0.44);
      ctx.lineTo(x + T * 0.56, y + T * 0.58);
      ctx.lineTo(x + T * 0.42, y + T * 0.55);
      ctx.fill();
    }
  }

  /**
   * 陷阱：地上一個圓形踏板。
   * - 外圈＝放置者陣營色（我方藍、被揭露的敵方紅）；敵方陷阱沒被揭露時不畫。
   * - 中央＝陷阱的元素色＋觸發方式：enter（踩到觸發）畫鋸齒夾、delay（倒數爆發）畫沙漏＋剩餘回合。
   * - 被揭露的敵方陷阱外圈改虛線＋右上「!」。
   */
  function trap(ctx, x, y, o = {}) {
    const team = o.team ?? "player";
    if (team !== "player" && !o.revealed) return;
    const col = TEAM[team] ?? TEAM.enemy;
    const el = elementColor(o.element ?? "none");
    const cx = x + T / 2;
    const cy = y + T / 2 + 2;
    const R = T * 0.3;
    ctx.save();
    // 踏板
    ctx.beginPath();
    ctx.ellipse(cx, cy, R, R * 0.78, 0, 0, TAU);
    ctx.fillStyle = "rgba(20,18,16,0.55)";
    ctx.fill();
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = col;
    if (team !== "player") ctx.setLineDash([5, 3]);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.strokeStyle = el;
    ctx.fillStyle = el;
    ctx.lineWidth = 2;
    if ((o.trigger ?? "enter") === "enter") {
      // 捕獸夾：上下兩排三角齒，咬向中線
      for (const sgn of [-1, 1]) {
        for (let i = 0; i < 4; i++) {
          const px = cx - R * 0.6 + (i * R * 1.2) / 3;
          ctx.beginPath();
          ctx.moveTo(px - 3.5, cy + sgn * 8);
          ctx.lineTo(px + 3.5, cy + sgn * 8);
          ctx.lineTo(px, cy + sgn * 1.5);
          ctx.closePath();
          ctx.fill();
        }
        ctx.beginPath();
        ctx.moveTo(cx - R * 0.75, cy + sgn * 8);
        ctx.lineTo(cx + R * 0.75, cy + sgn * 8);
        ctx.stroke();
      }
    } else {
      // 沙漏
      ctx.beginPath();
      ctx.moveTo(cx - 6, cy - 8);
      ctx.lineTo(cx + 6, cy - 8);
      ctx.lineTo(cx - 6, cy + 8);
      ctx.lineTo(cx + 6, cy + 8);
      ctx.closePath();
      ctx.fill();
    }
    if (o.turns != null && (o.trigger ?? "enter") === "delay") turnsBadge(ctx, x + T - 9, y + 10, o.turns);
    if (team !== "player") {
      ctx.fillStyle = BAD;
      ctx.font = "bold 14px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.lineWidth = 3;
      ctx.strokeStyle = "#000";
      ctx.strokeText("!", x + T - 9, y + 10);
      ctx.fillText("!", x + T - 9, y + 10);
    }
    ctx.restore();
  }

  /**
   * 持續區域：整塊區域只描「外框」（相鄰格同區域的邊不畫），底下鋪紋理。
   * - 顏色＝區域的元素色（沒有元素時用表面色，再沒有用灰）。
   * - 對「看的人」有害（會打我方）：實線外框＋斜線紋；有益（只幫我方）：虛線外框＋光點。
   * - anchor：caster 在施放者腳下加一圈虛線環；moving 在前進方向那一側的外框上畫箭頭。
   * - 剩餘回合：區域最左上那一格的左上角。
   */
  function zone(ctx, cells, o = {}) {
    const col = elementColor(o.element ?? "none");
    const harmful = o.harmful ?? true;
    const key = (cx, cy) => `${cx},${cy}`;
    const set = new Set(cells.map(([cx, cy]) => key(cx, cy)));
    ctx.save();
    for (const [cx, cy] of cells) {
      const x = cx * T;
      const y = cy * T;
      ctx.fillStyle = rgba(col, harmful ? 0.2 : 0.16);
      ctx.fillRect(x, y, T, T);
      ctx.save();
      ctx.beginPath();
      ctx.rect(x, y, T, T);
      ctx.clip();
      if (harmful) {
        ctx.strokeStyle = rgba(col, 0.45);
        ctx.lineWidth = 2;
        ctx.beginPath();
        for (let d = -T; d < T * 2; d += 10) {
          ctx.moveTo(x + d, y + T);
          ctx.lineTo(x + d + T, y);
        }
        ctx.stroke();
      } else {
        ctx.fillStyle = rgba(col, 0.7);
        for (let i = 0; i < 3; i++)
          for (let j = 0; j < 3; j++) {
            ctx.beginPath();
            ctx.arc(x + 9 + i * 17 + (j % 2) * 8, y + 9 + j * 17, 1.6, 0, TAU);
            ctx.fill();
          }
      }
      ctx.restore();
    }
    // 外框：只畫鄰格不在同一區域的邊
    ctx.strokeStyle = col;
    ctx.lineWidth = 2.5;
    ctx.lineCap = "round";
    if (!harmful) ctx.setLineDash([6, 4]);
    ctx.beginPath();
    const inset = 1.5;
    for (const [cx, cy] of cells) {
      const x = cx * T;
      const y = cy * T;
      if (!set.has(key(cx, cy - 1))) { ctx.moveTo(x, y + inset); ctx.lineTo(x + T, y + inset); }
      if (!set.has(key(cx, cy + 1))) { ctx.moveTo(x, y + T - inset); ctx.lineTo(x + T, y + T - inset); }
      if (!set.has(key(cx - 1, cy))) { ctx.moveTo(x + inset, y); ctx.lineTo(x + inset, y + T); }
      if (!set.has(key(cx + 1, cy))) { ctx.moveTo(x + T - inset, y); ctx.lineTo(x + T - inset, y + T); }
    }
    ctx.stroke();
    ctx.setLineDash([]);
    // 移動型：前進方向的外緣畫箭頭
    if (o.anchor === "moving" && o.dir) {
      const [dx, dy] = o.dir;
      for (const [cx, cy] of cells) {
        if (set.has(key(cx + dx, cy + dy))) continue;
        const ax = cx * T + T / 2 + dx * T * 0.36;
        const ay = cy * T + T / 2 + dy * T * 0.36;
        ctx.save();
        ctx.translate(ax, ay);
        ctx.rotate(Math.atan2(dy, dx));
        ctx.beginPath();
        ctx.moveTo(8, 0);
        ctx.lineTo(-4, -7);
        ctx.lineTo(-4, 7);
        ctx.closePath();
        ctx.fillStyle = col;
        ctx.fill();
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = "#000";
        ctx.stroke();
        ctx.restore();
      }
    }
    if (o.anchor === "caster" && o.caster) {
      const [px, py] = o.caster;
      ctx.setLineDash([4, 3]);
      ctx.lineWidth = 2;
      ctx.strokeStyle = col;
      ctx.beginPath();
      ctx.ellipse(px * T + T / 2, py * T + T * 0.8, T * 0.36, T * 0.13, 0, 0, TAU);
      ctx.stroke();
      ctx.setLineDash([]);
    }
    if (o.turns != null) {
      const first = [...cells].sort((a, b) => a[1] - b[1] || a[0] - b[0])[0];
      turnsBadge(ctx, first[0] * T + 9, first[1] * T + 9, o.turns);
    }
    ctx.restore();
  }

  // =====================================================================
  // ③ 狀態圖示
  // =====================================================================

  // 狀態資料（照 content/statuses.yaml 抄；正式版直接讀 glossary 的欄位）
  const STATUS = {
    defending: { pol: "buff", zh: "守護" },
    prone: { pol: "debuff", zh: "倒地" },
    burning: { pol: "debuff", zh: "燃燒", dot: "fire" },
    concealed: { pol: "neutral", zh: "隱蔽" },
    revealed: { pol: "debuff", zh: "被揭露" },
    overwatch: { pol: "buff", zh: "監視" },
    time_bomb: { pol: "debuff", zh: "定時炸彈" },
    charging: { pol: "neutral", zh: "蓄力" },
    slow: { pol: "debuff", zh: "緩速", ctrl: "movement" },
    root: { pol: "debuff", zh: "定身", ctrl: "movement", noMove: true },
    stun: { pol: "debuff", zh: "暈眩", ctrl: "hard", skip: true },
    frozen: { pol: "debuff", zh: "冰凍", ctrl: "hard", skip: true, thaw: "fire" },
    weaken: { pol: "debuff", zh: "虛弱" },
    vulnerable: { pol: "debuff", zh: "易傷" },
    armor_broken: { pol: "debuff", zh: "破甲" },
    bleed: { pol: "debuff", zh: "流血", dot: "physical" },
    poison: { pol: "debuff", zh: "中毒", dot: "poison" },
    guarded: { pol: "buff", zh: "護衛" },
    empowered: { pol: "buff", zh: "強化" },
    rallied: { pol: "buff", zh: "戰意" },
    hasted: { pol: "buff", zh: "加速" },
    regenerating: { pol: "buff", zh: "再生" },
    shielded: { pol: "buff", zh: "護盾", absorb: true },
    undying: { pol: "neutral", zh: "不死" },
    soul_link: { pol: "neutral", zh: "靈魂連結" },
    taunted: { pol: "debuff", zh: "嘲諷", ctrl: "mental" },
    feared: { pol: "debuff", zh: "恐懼", ctrl: "mental" },
    silenced: { pol: "debuff", zh: "沉默", ctrl: "mental" },
    blinded: { pol: "debuff", zh: "致盲" },
    marked: { pol: "debuff", zh: "被標記" },
    stance_fury: { pol: "neutral", zh: "狂怒姿態", stance: true },
    stance_bulwark: { pol: "neutral", zh: "堅壁姿態", stance: true },
  };

  // 圖樣色：控制類依 control_group、持續傷害依元素，其餘依 polarity。
  const CTRL_COLOR = { hard: "#ffd84a", movement: "#6ac8ff", mental: "#c890ff" };
  const POL_COLOR = { buff: "#7dffb0", debuff: "#ff8a8a", neutral: "#e8d8a8" };
  const FRAME_COLOR = { buff: "#3fbf6a", debuff: "#e04848", neutral: "#c8a048" };

  function glyphColor(id, s) {
    if (s.ctrl) return CTRL_COLOR[s.ctrl];
    if (s.dot) return elementColor(s.dot);
    // 少數有自己的顏色（保留原本的辨識度）
    return { time_bomb: "#ffb03a", shielded: "#8ac8ff", guarded: "#8ac8ff", defending: "#8ac8ff", regenerating: "#7dffb0", undying: "#ff8a9a", soul_link: "#c8a0ff", revealed: "#ffd04a", marked: "#ff6a4a", overwatch: "#ffd04a" }[id] ?? POL_COLOR[s.pol] ?? POL_COLOR.neutral;
  }

  /** 外框形狀：buff 圓、debuff 圓角方、neutral（含姿態）六角。邊長約 2r。 */
  function framePath(ctx, pol, r) {
    ctx.beginPath();
    if (pol === "buff") ctx.arc(0, 0, r, 0, TAU);
    else if (pol === "debuff") ctx.roundRect(-r * 0.9, -r * 0.9, r * 1.8, r * 1.8, r * 0.35);
    else for (let i = 0; i < 6; i++) ctx.lineTo(Math.cos((i / 6) * TAU + TAU / 12) * r, Math.sin((i / 6) * TAU + TAU / 12) * r);
    ctx.closePath();
  }

  // ---- 圖樣（中心 (0,0)、半徑約 10；顏色已設在 fill/stroke）----
  function line(c, pts) {
    c.beginPath();
    pts.forEach(([px, py], i) => (i ? c.lineTo(px, py) : c.moveTo(px, py)));
    c.stroke();
  }
  function shield(c, filled) {
    c.beginPath();
    c.moveTo(0, -9);
    c.lineTo(8, -6);
    c.quadraticCurveTo(8, 5, 0, 10);
    c.quadraticCurveTo(-8, 5, -8, -6);
    c.closePath();
    filled ? c.fill() : c.stroke();
  }
  function arrow(c, x, y, up) {
    const s = up ? -1 : 1;
    line(c, [[x, y - 5 * s], [x, y + 5 * s]]);
    line(c, [[x - 4, y - 1 * s], [x, y - 5 * s], [x + 4, y - 1 * s]]);
  }
  function eye(c, open) {
    c.beginPath();
    c.moveTo(-10, 0);
    c.quadraticCurveTo(0, -9, 10, 0);
    c.quadraticCurveTo(0, 9, -10, 0);
    c.stroke();
    if (open) {
      c.beginPath();
      c.arc(0, 0, 3.5, 0, TAU);
      c.fill();
    }
  }
  function star(c, x, y, r) {
    c.beginPath();
    for (let i = 0; i < 10; i++) {
      const rad = i % 2 ? r * 0.45 : r;
      const a = (i / 10) * TAU - Math.PI / 2;
      c.lineTo(x + Math.cos(a) * rad, y + Math.sin(a) * rad);
    }
    c.closePath();
    c.fill();
  }
  function flame(c, x, y, h) {
    c.beginPath();
    c.moveTo(x, y - h);
    c.quadraticCurveTo(x + h * 0.6, y - h * 0.2, x + h * 0.35, y + h * 0.3);
    c.quadraticCurveTo(x, y + h * 0.5, x - h * 0.35, y + h * 0.3);
    c.quadraticCurveTo(x - h * 0.6, y - h * 0.2, x, y - h);
    c.fill();
  }
  function drop(c, x, y, s) {
    c.beginPath();
    c.moveTo(x, y - s);
    c.quadraticCurveTo(x + s * 0.8, y + s * 0.2, x, y + s * 0.7);
    c.quadraticCurveTo(x - s * 0.8, y + s * 0.2, x, y - s);
    c.fill();
  }
  function sword(c) {
    line(c, [[-6, 7], [6, -7]]);
    line(c, [[-7, 2], [-2, 7]]);
  }

  const GLYPH = {
    defending: (c) => shield(c, false),
    guarded: (c) => { shield(c, false); arrow(c, 0, 0.5, false); }, // 盾＋↓（受傷減少）
    shielded: (c) => { c.beginPath(); c.arc(0, 0, 9, 0, TAU); c.stroke(); c.globalAlpha *= 0.35; c.fill(); c.globalAlpha /= 0.35; c.beginPath(); c.arc(0, 0, 5, Math.PI * 1.1, Math.PI * 1.55); c.strokeStyle = "#ffffff"; c.stroke(); }, // 泡泡（吸收量）
    prone: (c) => { c.beginPath(); c.arc(-6, 3, 3, 0, TAU); c.fill(); line(c, [[-2, 4], [9, 4]]); line(c, [[-10, 8], [10, 8]]); },
    burning: (c) => { flame(c, 0, 1, 10); },
    poison: (c) => { drop(c, 0, 0, 10); c.fillStyle = "#1a2a10"; c.beginPath(); c.arc(-2, 2, 2, 0, TAU); c.arc(3, -1, 1.4, 0, TAU); c.fill(); },
    bleed: (c) => { drop(c, -3, -1, 7); drop(c, 5, 3, 5); },
    concealed: (c) => { c.globalAlpha *= 0.55; c.beginPath(); c.arc(0, -4, 4, 0, TAU); c.fill(); c.beginPath(); c.moveTo(-8, 9); c.quadraticCurveTo(0, -2, 8, 9); c.fill(); c.globalAlpha /= 0.55; line(c, [[-9, 9], [9, -9]]); },
    revealed: (c) => { eye(c, true); line(c, [[-9, -9], [-5, -6]]); line(c, [[9, -9], [5, -6]]); line(c, [[0, -10], [0, -7]]); },
    overwatch: (c) => { c.beginPath(); c.arc(0, 0, 7, 0, TAU); c.stroke(); line(c, [[0, -10], [0, -4]]); line(c, [[0, 4], [0, 10]]); line(c, [[-10, 0], [-4, 0]]); line(c, [[4, 0], [10, 0]]); c.beginPath(); c.arc(0, 0, 1.8, 0, TAU); c.fill(); }, // 狙擊鏡
    marked: (c) => { line(c, [[-7, -7], [7, 7]]); line(c, [[7, -7], [-7, 7]]); c.beginPath(); c.arc(0, 0, 9, 0, TAU); c.stroke(); }, // 靶心叉
    time_bomb: (c) => { c.beginPath(); c.arc(-1, 2, 7, 0, TAU); c.fill(); line(c, [[3, -4], [7, -9]]); c.fillStyle = "#fff"; star(c, 8, -9, 3); },
    charging: (c) => { c.beginPath(); c.arc(0, 0, 8, 0, TAU); c.stroke(); c.beginPath(); c.arc(0, 0, 3.5, 0, TAU); c.fill(); },
    slow: (c) => { c.beginPath(); c.arc(0, 0, 8.5, 0, TAU); c.stroke(); line(c, [[0, 0], [0, -6]]); line(c, [[0, 0], [4, 3]]); },
    root: (c) => { line(c, [[0, -9], [0, 4]]); line(c, [[0, 4], [-7, 9]]); line(c, [[0, 4], [7, 9]]); line(c, [[0, 1], [-5, -3]]); },
    stun: (c) => { star(c, -5, -3, 5); star(c, 5, -3, 5); star(c, 0, 5, 5); },
    frozen: (c) => { for (let i = 0; i < 3; i++) { const a = (i / 3) * Math.PI; line(c, [[Math.cos(a) * -10, Math.sin(a) * -10], [Math.cos(a) * 10, Math.sin(a) * 10]]); } c.beginPath(); c.arc(0, 0, 2.5, 0, TAU); c.fill(); },
    weaken: (c) => { sword(c); arrow(c, 6, 3, false); },
    empowered: (c) => { line(c, [[-8, 0], [0, -8], [8, 0]]); line(c, [[-8, 8], [0, 0], [8, 8]]); }, // 雙箭頭↑（全屬性提升）
    rallied: (c) => { line(c, [[-6, 10], [-6, -9]]); c.beginPath(); c.moveTo(-6, -9); c.lineTo(8, -5); c.lineTo(-6, -1); c.closePath(); c.fill(); }, // 戰旗
    vulnerable: (c) => { shield(c, false); line(c, [[-2, -8], [2, -2], [-2, 2], [2, 9]]); }, // 裂開的盾
    armor_broken: (c) => { c.beginPath(); c.moveTo(-8, -6); c.lineTo(0, -9); c.lineTo(8, -6); c.lineTo(8, 1); c.lineTo(0, 9); c.lineTo(-8, 1); c.closePath(); c.stroke(); arrow(c, 0, 0, false); }, // 胸甲＋↓
    hasted: (c) => { line(c, [[-8, -7], [-1, 0], [-8, 7]]); line(c, [[1, -7], [8, 0], [1, 7]]); },
    regenerating: (c) => { c.fillRect(-2.5, -9, 5, 18); c.fillRect(-9, -2.5, 18, 5); },
    undying: (c) => { c.beginPath(); c.moveTo(0, 9); c.bezierCurveTo(-12, 0, -6, -10, 0, -4); c.bezierCurveTo(6, -10, 12, 0, 0, 9); c.fill(); c.fillStyle = "#000"; c.fillRect(-1, -4, 2, 9); c.fillRect(-3.5, -1.5, 7, 2); },
    soul_link: (c) => { c.beginPath(); c.arc(-4, 0, 5.5, 0, TAU); c.stroke(); c.beginPath(); c.arc(4, 0, 5.5, 0, TAU); c.stroke(); },
    taunted: (c) => { c.beginPath(); c.arc(0, 0, 9, 0, TAU); c.stroke(); c.beginPath(); c.arc(0, 0, 4.5, 0, TAU); c.stroke(); c.beginPath(); c.arc(0, 0, 1.5, 0, TAU); c.fill(); },
    feared: (c) => { c.font = "bold 17px sans-serif"; c.textAlign = "center"; c.textBaseline = "middle"; c.fillText("!", 0, 1); line(c, [[-8, -6], [-5, -3]]); line(c, [[8, -6], [5, -3]]); },
    silenced: (c) => { c.beginPath(); c.roundRect(-9, -7, 18, 12, 4); c.stroke(); c.beginPath(); c.moveTo(-3, 5); c.lineTo(-6, 10); c.lineTo(2, 5); c.stroke(); line(c, [[-10, 9], [10, -9]]); },
    blinded: (c) => { eye(c, false); line(c, [[-9, 7], [9, -7]]); },
    stance_fury: (c) => { for (const dx of [-5, 0, 5]) line(c, [[dx - 3, 8], [dx + 3, -8]]); }, // 爪痕
    stance_bulwark: (c) => { c.fillRect(-8, -2, 16, 10); for (const dx of [-8, -2, 4]) c.fillRect(dx, -7, 4, 5); }, // 城垛
  };

  /** 未知狀態：polarity 決定外框（未知 polarity 當 neutral），中間畫名稱第一個字。 */
  function statusIcon(ctx, id, cx, cy, size, o = {}) {
    const s = STATUS[id] ?? { pol: o.pol ?? "neutral", zh: o.zh ?? id ?? "?" };
    const pol = FRAME_COLOR[s.pol] ? s.pol : "neutral";
    const r = size / 2;
    const k = size / 26;
    ctx.save();
    ctx.translate(cx, cy);
    framePath(ctx, pol, r);
    ctx.fillStyle = "rgba(12,12,16,0.88)";
    ctx.fill();
    ctx.lineWidth = Math.max(1.5, size * 0.09);
    ctx.strokeStyle = FRAME_COLOR[pol];
    ctx.stroke();
    ctx.scale(k * 0.95, k * 0.95);
    const col = glyphColor(id, s);
    ctx.fillStyle = col;
    ctx.strokeStyle = col;
    ctx.lineWidth = size <= 18 ? 3 : 2.4;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    const g = GLYPH[id];
    if (g) g(ctx);
    else {
      ctx.font = "bold 13px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText([...s.zh][0] ?? "?", 0, 1);
    }
    ctx.restore();
  }

  /** 戰場上的排序：硬控 → 移動／心智控制 → 持續傷害 → 其他減益 → 增益 → 中性。同級依 ID 排序（確定性）。 */
  function statusRank(id) {
    const s = STATUS[id] ?? { pol: "neutral" };
    if (s.ctrl === "hard") return 0;
    if (s.ctrl) return 1;
    if (s.dot) return 2;
    if (s.pol === "debuff") return 3;
    if (s.pol === "buff") return 4;
    return 5;
  }
  function sortStatuses(ids) {
    return [...ids].sort((a, b) => statusRank(a) - statusRank(b) || (a < b ? -1 : a > b ? 1 : 0));
  }

  /** 頭頂的狀態列：最多 3 個圖示，多的畫「+N」。cx 為格子中心、top 為圖示列中心 y。 */
  function statusRow(ctx, ids, cx, top, size = 14) {
    const sorted = sortStatuses(ids);
    const shown = sorted.slice(0, sorted.length > 3 ? 2 : 3);
    const extra = sorted.length - shown.length;
    const gap = size + 1;
    const n = shown.length + (extra > 0 ? 1 : 0);
    let x = cx - ((n - 1) * gap) / 2;
    for (const id of shown) {
      statusIcon(ctx, id, x, top, size);
      x += gap;
    }
    if (extra > 0) {
      ctx.save();
      ctx.beginPath();
      ctx.roundRect(x - size / 2, top - size / 2, size, size, 4);
      ctx.fillStyle = "rgba(12,12,16,0.88)";
      ctx.fill();
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = "#9aa0aa";
      ctx.stroke();
      ctx.fillStyle = "#fff";
      ctx.font = `bold ${size <= 14 ? 9 : 11}px sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(`+${extra}`, x, top + 0.5);
      ctx.restore();
    }
  }

  /**
   * 身上特效（只給最需要一眼看懂的 5 類，依欄位決定，不寫死 ID）：
   * - skip_turn 且 removed_by_element 有 fire → 冰凍：冰塊罩住全身
   * - skip_turn → 暈眩：頭上三顆轉圈星星
   * - absorbs_damage → 護盾：淡藍泡泡
   * - prevents_move → 定身：腳下纏繞
   * - on_turn_start_damage → 持續傷害：腳邊元素色小粒子（火苗、毒泡、血滴）
   * 其餘狀態只靠頭頂圖示。cx 為格子中心、feet 為腳底 y。
   */
  function bodyUnder(ctx, ids, cx, feet) {
    const list = ids.map((id) => [id, STATUS[id] ?? {}]);
    if (list.some(([, s]) => s.noMove)) {
      ctx.save();
      ctx.strokeStyle = "#6ac8ff";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.ellipse(cx, feet - 2, 13, 4.5, 0, 0, TAU);
      ctx.stroke();
      ctx.strokeStyle = "#3d8a2a";
      ctx.lineWidth = 2.5;
      for (const s of [-1, 1]) {
        ctx.beginPath();
        ctx.moveTo(cx + s * 12, feet);
        ctx.quadraticCurveTo(cx + s * 14, feet - 10, cx + s * 5, feet - 13);
        ctx.stroke();
      }
      ctx.restore();
    }
  }
  function bodyOver(ctx, ids, cx, feet, t = 0) {
    const list = ids.map((id) => [id, STATUS[id] ?? {}]);
    const head = feet - 34;
    const frozen = list.some(([, s]) => s.skip && s.thaw === "fire");
    const stunned = !frozen && list.some(([, s]) => s.skip);
    if (frozen) {
      ctx.save();
      ctx.beginPath();
      ctx.roundRect(cx - 15, head - 6, 30, feet - head + 8, 5);
      ctx.fillStyle = rgba("#9fe6ff", 0.42);
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = "#e8fbff";
      ctx.stroke();
      ctx.strokeStyle = rgba("#ffffff", 0.8);
      ctx.beginPath();
      ctx.moveTo(cx - 10, feet - 4);
      ctx.lineTo(cx - 6, head);
      ctx.stroke();
      ctx.restore();
    }
    if (stunned) {
      ctx.save();
      ctx.strokeStyle = rgba("#ffd84a", 0.7);
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.ellipse(cx, head - 2, 14, 4, 0, 0, TAU);
      ctx.stroke();
      ctx.fillStyle = "#ffd84a";
      for (let i = 0; i < 3; i++) {
        const a = t + (i / 3) * TAU;
        star(ctx, cx + Math.cos(a) * 14, head - 2 + Math.sin(a) * 4, 3.6);
      }
      ctx.restore();
    }
    if (list.some(([, s]) => s.absorb)) {
      ctx.save();
      ctx.beginPath();
      ctx.ellipse(cx, feet - 20, 19, 24, 0, 0, TAU);
      const g = ctx.createRadialGradient(cx - 6, feet - 30, 2, cx, feet - 20, 24);
      g.addColorStop(0, rgba("#ffffff", 0.18));
      g.addColorStop(1, rgba("#8ac8ff", 0.22));
      ctx.fillStyle = g;
      ctx.fill();
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = rgba("#bfe2ff", 0.85);
      ctx.stroke();
      ctx.restore();
    }
    const dots = list.filter(([, s]) => s.dot).map(([, s]) => s.dot);
    dots.slice(0, 2).forEach((el, k) => {
      const side = k === 0 ? 1 : -1;
      ctx.save();
      ctx.fillStyle = elementColor(el);
      ctx.strokeStyle = "#1a0e06";
      ctx.lineWidth = 1;
      for (let i = 0; i < 2; i++) {
        const px = cx + side * (11 + i * 5);
        const py = feet - 4 - i * 9;
        if (el === "fire") { flame(ctx, px, py, 5.5); }
        else if (el === "poison") { ctx.beginPath(); ctx.arc(px, py, 2.6 - i * 0.6, 0, TAU); ctx.fill(); ctx.stroke(); }
        else { drop(ctx, px, py, 4); }
      }
      ctx.restore();
    });
  }

  return {
    T, ELEMENT, TEAM, STATUS, FRAME_COLOR, CTRL_COLOR,
    sightVeil, cracks, turnsBadge, iceWall, thornWall, rubble, thinIce, trap, zone,
    statusIcon, statusRow, sortStatuses, bodyUnder, bodyOver, elementColor,
  };
})();
