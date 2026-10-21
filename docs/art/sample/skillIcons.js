// 技能圖示自動生成（美術樣張）：只看技能卡的資料欄位——元素、形狀（shape.type）、射程、骨架、稀有度——
// 就組出一個圖示，所以 LLM 生成的新技能也自動有圖。不認得的元素／形狀／骨架都有預設，不會出錯。
// 圖層：① 元素底色與紋理 ② 形狀主圖（飛行物、揮砍、光束、扇形、範圍格、連鎖、地面、自身光環…）
//       ③ 左上元素標誌 ④ 右下骨架徽章 ⑤ 稀有度外框。全部在 100×100 的座標系畫，再縮放到任意大小。
window.SkillIcon = (() => {
  const TAU = Math.PI * 2;
  // 與 client/src/battle/vfxPalette.ts 的主色一致，另加底色深淺
  const EL = {
    physical: { name: "物理", accent: "#e8ebf0", dark: "#2c313b", light: "#7d8798" },
    fire: { name: "火", accent: "#ffb23a", dark: "#4a1104", light: "#e8541a" },
    ice: { name: "冰", accent: "#d8f6ff", dark: "#0b2f4e", light: "#3fa6d8" },
    lightning: { name: "雷", accent: "#fff36b", dark: "#1d1d4a", light: "#5a5ac8" },
    poison: { name: "毒", accent: "#b6f06a", dark: "#12320c", light: "#4f9a28" },
    wind: { name: "風", accent: "#dcfff1", dark: "#0b3f3a", light: "#3fb59a" },
    earth: { name: "大地", accent: "#f0c890", dark: "#2e1d0e", light: "#9a6a36" },
    holy: { name: "聖光", accent: "#fff6c8", dark: "#5a3a06", light: "#e7b23a" },
    shadow: { name: "暗影", accent: "#d2b0ff", dark: "#10071e", light: "#5a3590" },
    default: { name: "（無）", accent: "#e8e0ff", dark: "#221c44", light: "#6a5ad0" },
  };
  const RARITY = { common: "#9aa0a6", rare: "#4da3ff", epic: "#b06cff", legendary: "#ffbf3a" };
  const SHAPE_NAME = {
    single: "單體", line: "直線", cone: "錐形", cross: "十字", square3: "方陣", ring: "環形", chain: "連鎖",
    ground_tile: "指定格", self: "自身", allies_in_radius: "友軍範圍", object_then_tile: "物件→格", unit_then_tile: "單位→格", unit_pair: "兩單位",
  };
  const SKELETON_NAME = {
    strike: "打擊", area: "範圍", control: "控制", aura: "增益", summon: "召喚", trap: "陷阱", displace: "位移",
    consume_status: "引爆狀態", builder_finisher: "累積終結", stance: "姿態", reaction: "反應", modifier: "改造", passive: "被動", combo: "連段",
  };

  // ---- 小工具 ----
  function star(ctx, cx, cy, n, ro, ri, rot = -Math.PI / 2) {
    ctx.beginPath();
    for (let i = 0; i < n * 2; i++) {
      const r = i % 2 === 0 ? ro : ri;
      const a = rot + (i / (n * 2)) * TAU;
      ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
    }
    ctx.closePath();
  }
  function figure(ctx, cx, cy, k, color) {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(cx, cy - 9 * k, 6 * k, 0, TAU);
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(cx - 11 * k, cy + 12 * k);
    ctx.quadraticCurveTo(cx - 11 * k, cy - 2 * k, cx, cy - 1 * k);
    ctx.quadraticCurveTo(cx + 11 * k, cy - 2 * k, cx + 11 * k, cy + 12 * k);
    ctx.closePath();
    ctx.fill();
  }
  function outlined(ctx, fn, color, width = 5) {
    // 先畫深色描邊再畫本體，縮小時仍清楚
    ctx.save();
    ctx.strokeStyle = "rgba(0,0,0,0.55)";
    ctx.lineWidth = width;
    ctx.lineJoin = "round";
    fn();
    ctx.stroke();
    ctx.restore();
    ctx.fillStyle = color;
    fn();
    ctx.fill();
  }

  // ---- 元素標誌（也用在飛行物的彈頭）----
  function elementGlyph(ctx, el, cx, cy, k, color) {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(k, k);
    ctx.fillStyle = color;
    ctx.strokeStyle = color;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    switch (el) {
      case "fire":
        ctx.beginPath();
        ctx.moveTo(0, -10);
        ctx.bezierCurveTo(7, -3, 8, 3, 0, 9);
        ctx.bezierCurveTo(-8, 3, -6, -2, -2, -4);
        ctx.bezierCurveTo(-2, -1, 0, 0, 0, -10);
        ctx.fill();
        break;
      case "ice":
        ctx.lineWidth = 2.4;
        ctx.beginPath();
        for (let i = 0; i < 3; i++) {
          const a = (i / 3) * Math.PI + Math.PI / 2;
          ctx.moveTo(Math.cos(a) * 9, Math.sin(a) * 9);
          ctx.lineTo(-Math.cos(a) * 9, -Math.sin(a) * 9);
        }
        for (let i = 0; i < 6; i++) {
          const a = (i / 6) * TAU + Math.PI / 2;
          const bx = Math.cos(a) * 5.5;
          const by = Math.sin(a) * 5.5;
          ctx.moveTo(bx, by);
          ctx.lineTo(bx + Math.cos(a + 0.8) * 3.5, by + Math.sin(a + 0.8) * 3.5);
          ctx.moveTo(bx, by);
          ctx.lineTo(bx + Math.cos(a - 0.8) * 3.5, by + Math.sin(a - 0.8) * 3.5);
        }
        ctx.stroke();
        break;
      case "lightning":
        ctx.beginPath();
        ctx.moveTo(3, -11); ctx.lineTo(-6, 1); ctx.lineTo(0, 1); ctx.lineTo(-3, 11); ctx.lineTo(7, -2); ctx.lineTo(1, -2); ctx.lineTo(5, -11);
        ctx.closePath();
        ctx.fill();
        break;
      case "poison":
        ctx.beginPath();
        ctx.moveTo(0, -10);
        ctx.bezierCurveTo(8, -1, 8, 8, 0, 8);
        ctx.bezierCurveTo(-8, 8, -8, -1, 0, -10);
        ctx.fill();
        ctx.fillStyle = "rgba(0,0,0,0.35)";
        ctx.beginPath();
        ctx.arc(-2, 2, 2.2, 0, TAU);
        ctx.arc(2.5, 4.5, 1.4, 0, TAU);
        ctx.fill();
        break;
      case "wind":
        ctx.lineWidth = 2.6;
        ctx.beginPath();
        ctx.moveTo(-10, -4); ctx.lineTo(4, -4); ctx.arc(4, -7.5, 3.5, Math.PI / 2, -Math.PI * 0.9, true);
        ctx.moveTo(-10, 2); ctx.lineTo(7, 2); ctx.arc(7, 6, 4, -Math.PI / 2, Math.PI * 0.9);
        ctx.moveTo(-7, 8); ctx.lineTo(-1, 8);
        ctx.stroke();
        break;
      case "earth":
        ctx.beginPath();
        ctx.moveTo(-11, 8); ctx.lineTo(-4, -6); ctx.lineTo(0, 0); ctx.lineTo(4, -9); ctx.lineTo(11, 8);
        ctx.closePath();
        ctx.fill();
        break;
      case "holy":
        star(ctx, 0, 0, 4, 11, 3.2);
        ctx.fill();
        star(ctx, 0, 0, 4, 6, 2, -Math.PI / 4);
        ctx.fill();
        break;
      case "shadow":
        ctx.beginPath();
        ctx.arc(0, 0, 9, 0, TAU);
        ctx.arc(4, -3, 7.5, 0, TAU, true);
        ctx.fill("evenodd");
        break;
      case "physical":
        star(ctx, 0, 0, 4, 10, 2.6, 0);
        ctx.fill();
        break;
      default:
        ctx.beginPath();
        for (let i = 0; i < 6; i++) ctx.lineTo(Math.cos((i / 6) * TAU) * 8, Math.sin((i / 6) * TAU) * 8);
        ctx.closePath();
        ctx.fill();
        ctx.fillStyle = "rgba(255,255,255,0.6)";
        ctx.fillRect(-2, -5, 3, 10);
        break;
    }
    ctx.restore();
  }

  // ---- 元素紋理（底圖，淡淡的）----
  function texture(ctx, el, P) {
    ctx.save();
    ctx.globalAlpha = 0.18;
    ctx.strokeStyle = P.accent;
    ctx.fillStyle = P.accent;
    ctx.lineWidth = 2;
    switch (el) {
      case "fire":
        for (let i = 0; i < 5; i++) elementGlyph(ctx, "fire", 10 + i * 20, 96, 1.3 + (i % 2) * 0.5, P.accent);
        break;
      case "ice":
        ctx.beginPath();
        ctx.moveTo(0, 30); ctx.lineTo(30, 0); ctx.moveTo(60, 100); ctx.lineTo(100, 55); ctx.moveTo(0, 70); ctx.lineTo(45, 100); ctx.moveTo(70, 0); ctx.lineTo(100, 25);
        ctx.stroke();
        break;
      case "lightning":
        ctx.beginPath();
        ctx.moveTo(0, 20); ctx.lineTo(20, 32); ctx.lineTo(12, 40); ctx.lineTo(36, 54);
        ctx.moveTo(100, 60); ctx.lineTo(82, 70); ctx.lineTo(90, 78); ctx.lineTo(66, 96);
        ctx.stroke();
        break;
      case "poison":
        for (const [x, y, r] of [[14, 30, 6], [86, 40, 8], [28, 88, 5], [74, 86, 4], [60, 12, 3]]) {
          ctx.beginPath();
          ctx.arc(x, y, r, 0, TAU);
          ctx.stroke();
        }
        break;
      case "wind":
        for (let i = 0; i < 3; i++) {
          ctx.beginPath();
          ctx.arc(50, 50, 22 + i * 14, -0.4 + i, 1.4 + i);
          ctx.stroke();
        }
        break;
      case "earth":
        ctx.beginPath();
        ctx.moveTo(0, 78); ctx.lineTo(30, 72); ctx.lineTo(60, 80); ctx.lineTo(100, 70);
        ctx.moveTo(0, 90); ctx.lineTo(40, 86); ctx.lineTo(100, 92);
        ctx.stroke();
        break;
      case "holy":
        for (let i = 0; i < 12; i++) {
          const a = (i / 12) * TAU;
          ctx.beginPath();
          ctx.moveTo(50, 50);
          ctx.lineTo(50 + Math.cos(a - 0.08) * 80, 50 + Math.sin(a - 0.08) * 80);
          ctx.lineTo(50 + Math.cos(a + 0.08) * 80, 50 + Math.sin(a + 0.08) * 80);
          ctx.fill();
        }
        break;
      case "shadow":
        ctx.globalAlpha = 0.25;
        for (const [x, y, r] of [[10, 90, 26], [90, 10, 22], [95, 85, 16]]) {
          ctx.fillStyle = "#000";
          ctx.beginPath();
          ctx.arc(x, y, r, 0, TAU);
          ctx.fill();
        }
        break;
      case "physical":
        ctx.beginPath();
        for (let i = -100; i < 100; i += 9) {
          ctx.moveTo(i, 100);
          ctx.lineTo(i + 100, 0);
        }
        ctx.globalAlpha = 0.07;
        ctx.stroke();
        break;
      default:
        break;
    }
    ctx.restore();
  }

  // ---- 形狀主圖 ----
  function projectile(ctx, el, P) {
    const x0 = 22, y0 = 78, x1 = 64, y1 = 36;
    const g = ctx.createLinearGradient(x0, y0, x1, y1);
    g.addColorStop(0, "rgba(255,255,255,0)");
    g.addColorStop(1, P.accent);
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x1 - 6, y1 - 6);
    ctx.lineTo(x1 + 6, y1 + 6);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = P.accent;
    ctx.globalAlpha = 0.5;
    ctx.beginPath();
    ctx.arc(x1, y1, 17, 0, TAU);
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.save();
    ctx.translate(x1, y1);
    ctx.rotate(Math.PI / 4);
    ctx.translate(-x1, -y1);
    elementGlyph(ctx, el, x1, y1, 1.55, "#ffffff");
    ctx.restore();
  }
  function slash(ctx, el, P) {
    // 揮砍弧（近戰單體）：粗月牙
    const crescent = (dx, dy) => {
      ctx.beginPath();
      ctx.moveTo(24 + dx, 24 + dy);
      ctx.quadraticCurveTo(90 + dx, 12 + dy, 78 + dx, 80 + dy);
      ctx.quadraticCurveTo(70 + dx, 34 + dy, 24 + dx, 24 + dy);
      ctx.closePath();
    };
    crescent(3, 3);
    ctx.fillStyle = "rgba(0,0,0,0.4)";
    ctx.fill();
    crescent(0, 0);
    const g = ctx.createLinearGradient(24, 24, 80, 80);
    g.addColorStop(0, P.accent);
    g.addColorStop(0.5, "#ffffff");
    g.addColorStop(1, P.accent);
    ctx.fillStyle = g;
    ctx.fill();
    elementGlyph(ctx, el, 40, 62, 1.3, P.accent);
  }
  function buffTarget(ctx, el, P) {
    // 對單一友軍的增益：目標身影＋上升箭頭
    ctx.fillStyle = P.accent;
    ctx.globalAlpha = 0.35;
    ctx.beginPath();
    ctx.ellipse(46, 78, 24, 8, 0, 0, TAU);
    ctx.fill();
    ctx.globalAlpha = 1;
    figure(ctx, 46, 64, 1.25, "#ffffff");
    ctx.strokeStyle = P.accent;
    ctx.lineWidth = 4.5;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    for (const y of [36, 48]) {
      ctx.beginPath();
      ctx.moveTo(64, y + 8); ctx.lineTo(72, y); ctx.lineTo(80, y + 8);
      ctx.stroke();
    }
    elementGlyph(ctx, el, 46, 30, 0.9, P.accent);
  }
  function beam(ctx, el, P) {
    ctx.save();
    ctx.translate(50, 50);
    ctx.rotate(-Math.PI / 4);
    ctx.fillStyle = P.accent;
    ctx.globalAlpha = 0.45;
    ctx.fillRect(-42, -12, 84, 24);
    ctx.globalAlpha = 1;
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(-42, -5, 84, 10);
    ctx.fillStyle = "rgba(0,0,0,0.35)";
    for (let i = -1; i <= 1; i++) ctx.fillRect(i * 24 - 5, -5, 10, 10);
    ctx.restore();
    elementGlyph(ctx, el, 74, 26, 1.0, P.accent);
  }
  function fan(ctx, el, P) {
    const ox = 22, oy = 78;
    const a = -Math.PI / 4;
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(ox, oy);
    ctx.arc(ox, oy, 66, a - 0.55, a + 0.55);
    ctx.closePath();
    const g = ctx.createRadialGradient(ox, oy, 4, ox, oy, 66);
    g.addColorStop(0, "#ffffff");
    g.addColorStop(1, P.accent);
    ctx.fillStyle = g;
    ctx.globalAlpha = 0.9;
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.strokeStyle = "rgba(0,0,0,0.3)";
    ctx.lineWidth = 2;
    for (const rr of [30, 48]) {
      ctx.beginPath();
      ctx.arc(ox, oy, rr, a - 0.55, a + 0.55);
      ctx.stroke();
    }
    ctx.restore();
    elementGlyph(ctx, el, 60, 42, 1.3, "rgba(0,0,0,0.45)");
  }
  const GRID = {
    square3: [1, 1, 1, 1, 1, 1, 1, 1, 1],
    cross: [0, 1, 0, 1, 1, 1, 0, 1, 0],
    ring: [1, 1, 1, 1, 0, 1, 1, 1, 1],
  };
  function grid(ctx, el, P, shape) {
    const cells = GRID[shape];
    const cs = 19, gap = 3, ox = 50 - (cs * 3 + gap * 2) / 2, oy = 50 - (cs * 3 + gap * 2) / 2;
    for (let i = 0; i < 9; i++) {
      const x = ox + (i % 3) * (cs + gap);
      const y = oy + Math.floor(i / 3) * (cs + gap);
      ctx.beginPath();
      ctx.roundRect(x, y, cs, cs, 3);
      if (cells[i]) {
        ctx.fillStyle = P.accent;
        ctx.globalAlpha = 0.85;
        ctx.fill();
        ctx.globalAlpha = 1;
      } else {
        ctx.strokeStyle = "rgba(255,255,255,0.45)";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    }
    if (shape === "ring") figure(ctx, 50, 52, 0.62, "#ffffff");
    else {
      outlined(ctx, () => star(ctx, 50, 50, 8, 17, 8), "#ffffff", 4);
      elementGlyph(ctx, el, 50, 50, 0.9, P.dark);
    }
  }
  function chain(ctx, el, P) {
    const pts = [[22, 72], [48, 30], [78, 62]];
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 3;
    ctx.lineJoin = "round";
    ctx.beginPath();
    for (let i = 0; i < pts.length - 1; i++) {
      const [ax, ay] = pts[i];
      const [bx, by] = pts[i + 1];
      ctx.moveTo(ax, ay);
      for (let k = 1; k < 5; k++) {
        const t = k / 5;
        const nx = -(by - ay), ny = bx - ax;
        const len = Math.hypot(nx, ny);
        const off = (k % 2 ? 5 : -5) / len;
        ctx.lineTo(ax + (bx - ax) * t + nx * off, ay + (by - ay) * t + ny * off);
      }
      ctx.lineTo(bx, by);
    }
    ctx.stroke();
    for (const [x, y] of pts) {
      ctx.fillStyle = P.accent;
      ctx.beginPath();
      ctx.arc(x, y, 9, 0, TAU);
      ctx.fill();
      ctx.strokeStyle = "rgba(0,0,0,0.4)";
      ctx.lineWidth = 2;
      ctx.stroke();
    }
    elementGlyph(ctx, el, 48, 30, 0.6, P.dark);
  }
  function groundMarker(ctx, P) {
    ctx.save();
    for (const [rx, a] of [[30, 0.35], [22, 0.6], [13, 0.9]]) {
      ctx.strokeStyle = P.accent;
      ctx.globalAlpha = a;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.ellipse(50, 70, rx, rx * 0.4, 0, 0, TAU);
      ctx.stroke();
    }
    ctx.restore();
  }
  function ground(ctx, el, P, skeleton) {
    groundMarker(ctx, P);
    if (skeleton === "summon") {
      // 召喚：從地面升起的身影
      ctx.save();
      ctx.beginPath();
      ctx.rect(0, 0, 100, 70);
      ctx.clip();
      figure(ctx, 50, 54, 1.25, "#ffffff");
      ctx.restore();
      elementGlyph(ctx, el, 50, 42, 0.7, P.dark);
    } else if (skeleton === "trap") {
      // 陷阱：張開的夾子
      for (const [base, tip, color] of [[50, 62, "#ffffff"], [76, 64, "#d8dce4"]]) {
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.moveTo(26, base);
        for (let i = 0; i < 6; i++) {
          ctx.lineTo(26 + i * 8 + 4, tip);
          ctx.lineTo(26 + (i + 1) * 8, base);
        }
        ctx.lineTo(74, base + (base < tip ? -4 : 4));
        ctx.lineTo(26, base + (base < tip ? -4 : 4));
        ctx.closePath();
        ctx.fill();
      }
      elementGlyph(ctx, el, 50, 28, 1.0, P.accent);
    } else {
      // 其他：元素從上方落下（例如位移的落點、指定格）
      ctx.fillStyle = P.accent;
      ctx.beginPath();
      ctx.moveTo(50, 60); ctx.lineTo(40, 46); ctx.lineTo(60, 46);
      ctx.closePath();
      ctx.fill();
      elementGlyph(ctx, el, 50, 32, 1.4, "#ffffff");
    }
  }
  function selfAura(ctx, el, P, skeleton) {
    for (const [r, a] of [[36, 0.25], [28, 0.45], [20, 0.7]]) {
      ctx.strokeStyle = P.accent;
      ctx.globalAlpha = a;
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.arc(50, 52, r, 0, TAU);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
    figure(ctx, 50, 56, 1.0, "#ffffff");
    if (skeleton === "stance") {
      outlined(ctx, () => {
        ctx.beginPath();
        ctx.moveTo(50, 40); ctx.lineTo(62, 45); ctx.lineTo(60, 60); ctx.lineTo(50, 68); ctx.lineTo(40, 60); ctx.lineTo(38, 45);
        ctx.closePath();
      }, P.accent, 4);
    }
  }
  function alliesRadius(ctx, el, P) {
    ctx.strokeStyle = P.accent;
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.arc(50, 72, 38, Math.PI, 0);
    ctx.stroke();
    ctx.globalAlpha = 0.2;
    ctx.fillStyle = P.accent;
    ctx.fill();
    ctx.globalAlpha = 1;
    figure(ctx, 28, 66, 0.7, "rgba(255,255,255,0.75)");
    figure(ctx, 72, 66, 0.7, "rgba(255,255,255,0.75)");
    figure(ctx, 50, 60, 1.0, "#ffffff");
    elementGlyph(ctx, el, 50, 30, 0.9, P.accent);
  }
  function hurl(ctx, el, P) {
    ctx.strokeStyle = P.accent;
    ctx.setLineDash([5, 4]);
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(24, 76);
    ctx.quadraticCurveTo(50, 8, 76, 70);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#c8894a";
    ctx.fillRect(40, 22, 20, 20);
    ctx.strokeStyle = "#5a3412";
    ctx.lineWidth = 2;
    ctx.strokeRect(40, 22, 20, 20);
    elementGlyph(ctx, el, 76, 70, 1.0, "#ffffff");
  }
  function pair(ctx, el, P) {
    figure(ctx, 30, 58, 0.85, "#ffffff");
    figure(ctx, 70, 58, 0.85, P.accent);
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(36, 30); ctx.quadraticCurveTo(50, 20, 64, 30);
    ctx.moveTo(64, 30); ctx.lineTo(57, 27); ctx.moveTo(64, 30); ctx.lineTo(60, 23);
    ctx.stroke();
  }

  // ---- 骨架徽章 ----
  function skeletonGlyph(ctx, sk, cx, cy) {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.strokeStyle = "#ffffff";
    ctx.fillStyle = "#ffffff";
    ctx.lineWidth = 2.2;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    switch (sk) {
      case "strike":
        ctx.beginPath();
        ctx.moveTo(-6, 6); ctx.lineTo(6, -6); ctx.moveTo(-6, 1); ctx.lineTo(-1, 6); ctx.stroke();
        break;
      case "area":
        star(ctx, 0, 0, 6, 7.5, 3.5);
        ctx.fill();
        break;
      case "control":
        ctx.beginPath();
        ctx.arc(0, -2, 4, Math.PI, 0);
        ctx.stroke();
        ctx.fillRect(-5.5, -1.5, 11, 8);
        break;
      case "aura":
        ctx.beginPath();
        ctx.moveTo(-5, 1); ctx.lineTo(0, -4); ctx.lineTo(5, 1); ctx.moveTo(-5, 6); ctx.lineTo(0, 1); ctx.lineTo(5, 6);
        ctx.stroke();
        break;
      case "summon":
        ctx.beginPath();
        ctx.moveTo(0, -6); ctx.lineTo(0, 6); ctx.moveTo(-6, 0); ctx.lineTo(6, 0);
        ctx.stroke();
        break;
      case "trap":
        ctx.beginPath();
        ctx.moveTo(-7, -1); ctx.lineTo(-4, 4); ctx.lineTo(-1, -1); ctx.lineTo(2, 4); ctx.lineTo(5, -1); ctx.lineTo(7, 3);
        ctx.stroke();
        break;
      case "displace":
        ctx.beginPath();
        ctx.moveTo(-7, 0); ctx.lineTo(7, 0); ctx.moveTo(3, -4); ctx.lineTo(7, 0); ctx.lineTo(3, 4); ctx.moveTo(-3, -4); ctx.lineTo(-7, 0); ctx.lineTo(-3, 4);
        ctx.stroke();
        break;
      case "consume_status":
        star(ctx, 0, 0, 5, 7, 3);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(0, 0, 1.8, 0, TAU);
        ctx.fill();
        break;
      case "builder_finisher":
        for (let i = 0; i < 3; i++) ctx.fillRect(-6 + i * 4.5, 4 - i * 4, 3, 3 + i * 4);
        break;
      case "stance":
        ctx.beginPath();
        ctx.moveTo(0, -7); ctx.lineTo(6, -4); ctx.lineTo(5, 3); ctx.lineTo(0, 7); ctx.lineTo(-5, 3); ctx.lineTo(-6, -4);
        ctx.closePath();
        ctx.stroke();
        break;
      case "reaction":
        ctx.beginPath();
        ctx.arc(0, 0, 5.5, -2.6, 1.4);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(-6, -6); ctx.lineTo(-5, -1); ctx.lineTo(-1, -3.5);
        ctx.stroke();
        break;
      default:
        ctx.beginPath();
        ctx.arc(0, 0, 5, 0, TAU);
        ctx.stroke();
        break;
    }
    ctx.restore();
  }

  // ---- 組合 ----
  function isRanged(skill) {
    const r = skill.range;
    if (typeof r === "number") return r >= 2;
    return (skill.tags ?? []).some((t) => ["bow", "ranged", "arrow"].includes(t));
  }
  function draw(canvas, skill, size = 96) {
    const dpr = 2;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = `${size}px`;
    canvas.style.height = `${size}px`;
    const ctx = canvas.getContext("2d");
    ctx.scale((size * dpr) / 100, (size * dpr) / 100);
    const el = EL[skill.element] ? skill.element : "default";
    const P = EL[el];
    const rarity = RARITY[skill.rarity] ?? RARITY.common;
    // ① 底
    ctx.save();
    ctx.beginPath();
    ctx.roundRect(2, 2, 96, 96, 16);
    ctx.clip();
    const bg = ctx.createRadialGradient(38, 30, 4, 50, 50, 78);
    bg.addColorStop(0, P.light);
    bg.addColorStop(1, P.dark);
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, 100, 100);
    texture(ctx, el, P);
    // ② 形狀主圖
    const shape = skill.shape;
    if (shape === "single" && skill.skeleton === "aura") buffTarget(ctx, el, P);
    else if (shape === "single") (isRanged(skill) ? projectile : slash)(ctx, el, P);
    else if (shape === "line") beam(ctx, el, P);
    else if (shape === "cone") fan(ctx, el, P);
    else if (GRID[shape]) grid(ctx, el, P, shape);
    else if (shape === "chain") chain(ctx, el, P);
    else if (shape === "ground_tile") ground(ctx, el, P, skill.skeleton);
    else if (shape === "allies_in_radius") alliesRadius(ctx, el, P);
    else if (shape === "object_then_tile") hurl(ctx, el, P);
    else if (shape === "unit_pair" || shape === "unit_then_tile") pair(ctx, el, P);
    else selfAura(ctx, el, P, skill.skeleton); // self 與不認得的形狀
    ctx.restore();
    // ③ 左上元素標誌
    ctx.fillStyle = "rgba(8,10,16,0.75)";
    ctx.beginPath();
    ctx.arc(19, 19, 12, 0, TAU);
    ctx.fill();
    elementGlyph(ctx, el, 19, 19, 0.8, P.accent);
    // ④ 右下骨架徽章
    ctx.fillStyle = "rgba(8,10,16,0.85)";
    ctx.beginPath();
    ctx.arc(81, 81, 13, 0, TAU);
    ctx.fill();
    ctx.strokeStyle = rarity;
    ctx.lineWidth = 2;
    ctx.stroke();
    skeletonGlyph(ctx, skill.skeleton, 81, 81);
    // ⑤ 稀有度外框
    ctx.beginPath();
    ctx.roundRect(2, 2, 96, 96, 16);
    ctx.lineWidth = skill.rarity === "legendary" ? 5 : 3.5;
    ctx.strokeStyle = rarity;
    ctx.stroke();
    if (skill.rarity === "legendary" || skill.rarity === "epic") {
      ctx.beginPath();
      ctx.roundRect(7, 7, 86, 86, 12);
      ctx.lineWidth = 1;
      ctx.strokeStyle = rarity;
      ctx.globalAlpha = 0.6;
      ctx.stroke();
      ctx.globalAlpha = 1;
    }
  }
  return { draw, EL, RARITY, SHAPE_NAME, SKELETON_NAME, isRanged };
})();
