// 大世界圖（M），俯視彩繪風（B 案）。要先載入 regionArt.js。全部程式繪製。
// 方位照 6D-5（6D-4 的浮橋）：西雲嶺、南荒原、北晶冠、東樞市、東南霜潮；主城「樞島」在中央。
(function () {
  const RA = window.RegionArt, W = 1280, H = 860, TAU = Math.PI * 2;
  const FONT = RA.PAL.painted.font;
  // state：open＝已開放；locked＝有地點圖但還沒亮起；later＝之後的賽季
  const ISLANDS = [
    { id: "capital", name: "主城", town: "樞島", state: "open", x: 650, y: 360, rx: 120, ry: 66, kind: "capital" },
    { id: "cloud_ridge", name: "雲嶺", town: "霧渡鎮", lv: "1～6", state: "open", x: 250, y: 380, rx: 185, ry: 100, kind: "cloud", here: true },
    { id: "ashen_waste", name: "灰燼荒原", town: "餘燼集", lv: "5～9", state: "open", x: 600, y: 615, rx: 185, ry: 84, kind: "ashen" },
    { id: "crystal_crown", name: "晶冠城邦", state: "later", x: 650, y: 120, rx: 125, ry: 50, kind: "crown" },
    { id: "arcane_hub", name: "魔導樞市", state: "later", x: 1060, y: 330, rx: 140, ry: 62, kind: "arcane" },
    { id: "frost_tide", name: "霜潮海境", state: "later", x: 1030, y: 640, rx: 140, ry: 62, kind: "frost" },
  ];
  const COND = { later: "之後的賽季", locked: "世界事件：霧潮入侵" };

  function sky(ctx) {
    const g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, "#5b79b0"); g.addColorStop(0.55, "#a9c1df"); g.addColorStop(1, "#f0dcc0");
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    // 碎界光帶
    ctx.save(); ctx.globalAlpha = 0.22; ctx.strokeStyle = "#b9a4ff"; ctx.lineWidth = 34;
    ctx.beginPath(); ctx.ellipse(W / 2, H / 2 + 30, W * 0.42, H * 0.36, -0.08, 0, TAU); ctx.stroke();
    ctx.globalAlpha = 0.35; ctx.lineWidth = 3; ctx.stroke(); ctx.restore();
    // 雲海
    const r = RA.rng(301);
    for (let i = 0; i < 260; i++) {
      const y = H * 0.35 + Math.pow(r(), 0.7) * H * 0.7;
      RA.puff(ctx, r() * W, y, 30 + r() * 60, 0.25 + (y / H) * 0.45);
    }
    // 漂浮碎石
    for (let i = 0; i < 22; i++) {
      const x = r() * W, y = r() * H, s = 4 + r() * 9;
      ctx.fillStyle = "#6a6070"; ctx.strokeStyle = "rgba(30,30,40,0.6)"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x - s, y); ctx.lineTo(x, y - s * 0.6); ctx.lineTo(x + s, y); ctx.lineTo(x, y + s * 1.2); ctx.closePath(); ctx.fill(); ctx.stroke();
    }
  }

  function blob(cx, cy, rx, ry, seed) {
    const r = RA.rng(seed), p = new Path2D(), n = 28, pts = [];
    for (let i = 0; i < n; i++) {
      const a = (i / n) * TAU, k = 0.9 + r() * 0.16;
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

  function underside(ctx, is, grey) {
    const { x, y, rx, ry } = is, depth = ry * 0.45;
    const r = RA.rng(x + y);
    // 倒錐岩塊
    const g = ctx.createLinearGradient(0, y, 0, y + ry + depth + ry * 1.1);
    g.addColorStop(0, grey ? "#7c7c84" : is.kind === "ashen" ? "#5a4038" : "#7a6450");
    g.addColorStop(1, grey ? "#3c3c44" : "#2c2018");
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.moveTo(x - rx * 0.86, y + depth * 0.6);
    for (let k = 0; k <= 10; k++) {
      const t = k / 10, xx = x - rx * 0.86 + t * rx * 1.72;
      const yy = y + depth + Math.sin(t * Math.PI) * ry * (1.0 + r() * 0.35) + (k % 2) * 10;
      ctx.lineTo(xx, yy);
    }
    ctx.lineTo(x + rx * 0.86, y + depth * 0.6); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = "rgba(25,20,18,0.7)"; ctx.lineWidth = 1.5; ctx.stroke();
    // 岩層紋
    ctx.strokeStyle = "rgba(0,0,0,0.18)"; ctx.lineWidth = 2;
    for (let k = 1; k <= 3; k++) {
      ctx.beginPath(); ctx.ellipse(x, y + depth + k * 16, rx * (0.9 - k * 0.15), ry * 0.25, 0, 0.15, Math.PI - 0.15); ctx.stroke();
    }
    // 島緣的厚度
    ctx.save(); ctx.translate(0, depth);
    ctx.fillStyle = grey ? "#6c6c74" : is.kind === "ashen" ? "#6a4a3c" : "#8a7058";
    ctx.fill(blob(x, y, rx, ry, x * 3 + y)); ctx.restore();
  }

  // ---------- 各島頂面 ----------
  function topCloud(ctx, is) {
    const { x, y, rx, ry } = is, r = RA.rng(311);
    ctx.fillStyle = "#7fa65a"; ctx.fillRect(x - rx, y - ry, rx * 2, ry * 2);
    for (let i = 0; i < 40; i++) {
      ctx.fillStyle = i % 2 ? "rgba(60,100,40,0.18)" : "rgba(180,200,120,0.18)";
      ctx.beginPath(); ctx.ellipse(x + (r() - 0.5) * rx * 2, y + (r() - 0.5) * ry * 2, 18 + r() * 20, 10 + r() * 8, 0, 0, TAU); ctx.fill();
    }
    // 河
    ctx.strokeStyle = "#3f7fb0"; ctx.lineWidth = 9; ctx.lineCap = "round";
    ctx.beginPath(); ctx.moveTo(x - rx, y + ry * 0.55); ctx.quadraticCurveTo(x - 20, y + ry * 0.8, x + rx, y + ry * 0.35); ctx.stroke();
    ctx.strokeStyle = "#69a8d4"; ctx.lineWidth = 4; ctx.stroke();
    // 梯田
    for (let i = 5; i >= 0; i--) {
      ctx.beginPath(); ctx.ellipse(x + 10, y + 30, 18 + i * 7, 10 + i * 4, 0, Math.PI * 1.05, Math.PI * 1.95);
      ctx.strokeStyle = i % 2 ? "#9ccc6e" : "#b6dc87"; ctx.lineWidth = 4; ctx.stroke();
    }
    // 竹林
    for (let i = 0; i < 26; i++) {
      const bx = x - rx * 0.55 + r() * 70, by = y + 10 + r() * 40;
      ctx.strokeStyle = "#4f9a44"; ctx.lineWidth = 1.6; ctx.beginPath(); ctx.moveTo(bx, by); ctx.lineTo(bx + 1, by - 12); ctx.stroke();
      ctx.fillStyle = "#2f6b34"; ctx.beginPath(); ctx.ellipse(bx + 3, by - 12, 4, 1.5, -0.5, 0, TAU); ctx.fill();
    }
    // 雪頂群山（北側）
    const pk = [];
    for (let i = 0; i < 11; i++) pk.push([x - rx * 0.75 + i * rx * 0.15 + (r() - 0.5) * 10, y - ry * 0.25 + (r() - 0.5) * 14, 34 + r() * 26]);
    pk.sort((a, b) => a[1] - b[1]).forEach(([px, py, h]) => RA.mountain(ctx, "painted", px, py, h, r, true));
    // 雲霧
    for (let i = 0; i < 4; i++) RA.puff(ctx, x - rx * 0.5 + i * rx * 0.33, y - 8 + (r() - 0.5) * 8, 16, 0.4);
  }

  function topAshen(ctx, is) {
    const { x, y, rx, ry } = is, r = RA.rng(313);
    const g = ctx.createLinearGradient(0, y - ry, 0, y + ry);
    g.addColorStop(0, "#4a3a32"); g.addColorStop(1, "#a0724c");
    ctx.fillStyle = g; ctx.fillRect(x - rx, y - ry, rx * 2, ry * 2);
    for (let i = 0; i < 30; i++) {
      ctx.fillStyle = i % 2 ? "rgba(30,22,18,0.18)" : "rgba(200,120,70,0.15)";
      ctx.beginPath(); ctx.ellipse(x + (r() - 0.5) * rx * 2, y + (r() - 0.5) * ry * 2, 16 + r() * 18, 8 + r() * 6, 0, 0, TAU); ctx.fill();
    }
    // 熔岩河
    ctx.save(); ctx.lineCap = "round"; ctx.shadowColor = "#ff6a1a"; ctx.shadowBlur = 14;
    ctx.strokeStyle = "#c2410c"; ctx.lineWidth = 11;
    ctx.beginPath(); ctx.moveTo(x + rx * 0.45, y - ry * 0.35); ctx.quadraticCurveTo(x + 10, y + 10, x + rx, y + ry * 0.3); ctx.stroke();
    ctx.strokeStyle = "#ff8a2a"; ctx.lineWidth = 5; ctx.stroke(); ctx.restore();
    // 枯木
    for (let i = 0; i < 18; i++) {
      const tx = x - rx * 0.5 + r() * 90, ty = y + r() * 40 - 10;
      ctx.strokeStyle = "#2e2420"; ctx.lineWidth = 1.6;
      ctx.beginPath(); ctx.moveTo(tx, ty); ctx.lineTo(tx, ty - 10); ctx.moveTo(tx, ty - 6); ctx.lineTo(tx - 4, ty - 10); ctx.moveTo(tx, ty - 8); ctx.lineTo(tx + 4, ty - 13); ctx.stroke();
    }
    // 岩山
    for (let i = 0; i < 6; i++) RA.mountain(ctx, "painted", x - rx * 0.7 + i * 34, y - ry * 0.35 + (r() - 0.5) * 10, 26 + r() * 14, r, false, ["#7a685c", "#43372f"]);
    // 火山
    const vx = x + rx * 0.4, vy = y + ry * 0.05;
    ctx.fillStyle = "#5a4a42"; ctx.beginPath(); ctx.moveTo(vx - 46, vy + 10); ctx.lineTo(vx - 10, vy - 46); ctx.lineTo(vx, vy + 10); ctx.fill();
    ctx.fillStyle = "#33281f"; ctx.beginPath(); ctx.moveTo(vx - 10, vy - 46); ctx.lineTo(vx + 10, vy - 46); ctx.lineTo(vx + 46, vy + 10); ctx.lineTo(vx, vy + 10); ctx.fill();
    ctx.save(); ctx.shadowColor = "#ff6a1a"; ctx.shadowBlur = 16; ctx.fillStyle = "#ff8a2a";
    ctx.beginPath(); ctx.ellipse(vx, vy - 46, 11, 3.5, 0, 0, TAU); ctx.fill(); ctx.restore();
    // 赤沙
    for (let i = 0; i < 6; i++) {
      ctx.fillStyle = "rgba(214,138,82,0.55)";
      ctx.beginPath(); ctx.ellipse(x - rx * 0.4 + i * 30, y + ry * 0.6 + (i % 2) * 6, 20, 6, 0, Math.PI, TAU); ctx.fill();
    }
  }

  function topCapital(ctx, is) {
    const { x, y, rx, ry } = is;
    ctx.fillStyle = "#d9cdb2"; ctx.fillRect(x - rx, y - ry, rx * 2, ry * 2);
    // 石板路十字
    ctx.fillStyle = "#c2b494"; ctx.fillRect(x - rx, y - 6, rx * 2, 12); ctx.fillRect(x - 6, y - ry, 12, ry * 2);
    // 草地角落
    for (const [ox, oy] of [[-70, -34], [70, -34], [-70, 34], [70, 34]]) {
      ctx.fillStyle = "#8fbf6a"; ctx.beginPath(); ctx.ellipse(x + ox, y + oy, 26, 14, 0, 0, TAU); ctx.fill();
    }
    // 白牆藍頂
    for (const [ox, oy] of [[-80, -10], [-50, -36], [-36, 20], [44, -38], [70, -8], [40, 24], [-84, 26], [84, 22]]) {
      const hx = x + ox, hy = y + oy;
      ctx.fillStyle = "#f6efe0"; ctx.fillRect(hx - 9, hy - 6, 18, 12);
      ctx.strokeStyle = "#27303a"; ctx.lineWidth = 1; ctx.strokeRect(hx - 9, hy - 6, 18, 12);
      ctx.fillStyle = "#3a5ad0"; ctx.beginPath(); ctx.moveTo(hx - 12, hy - 5); ctx.lineTo(hx, hy - 15); ctx.lineTo(hx + 12, hy - 5); ctx.closePath(); ctx.fill(); ctx.stroke();
    }
  }
  function tower(ctx, is) {
    const { x, y } = is;
    const g = ctx.createRadialGradient(x, y - 50, 0, x, y - 50, 70);
    g.addColorStop(0, "rgba(160,140,255,0.6)"); g.addColorStop(1, "rgba(160,140,255,0)");
    ctx.fillStyle = g; ctx.fillRect(x - 70, y - 120, 140, 140);
    ctx.fillStyle = "#f6efe0"; ctx.strokeStyle = "#27303a"; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.ellipse(x, y, 16, 8, 0, 0, TAU); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#c8bcff";
    ctx.beginPath(); ctx.moveTo(x - 9, y - 2); ctx.lineTo(x, y - 82); ctx.lineTo(x + 9, y - 2); ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#eee8ff"; ctx.beginPath(); ctx.moveTo(x - 2, y - 4); ctx.lineTo(x, y - 82); ctx.lineTo(x + 3, y - 4); ctx.closePath(); ctx.fill();
  }

  function topLocked(ctx, is) {
    const { x, y, rx, ry, kind } = is, r = RA.rng(x);
    ctx.fillStyle = "#9a9ca4"; ctx.fillRect(x - rx, y - ry, rx * 2, ry * 2);
    ctx.fillStyle = "rgba(70,72,82,0.45)";
    if (kind === "crown") {
      for (let i = 0; i < 7; i++) { const cx = x - rx * 0.6 + i * rx * 0.2, h = 18 + r() * 22; ctx.beginPath(); ctx.moveTo(cx - 7, y + 8); ctx.lineTo(cx, y + 8 - h); ctx.lineTo(cx + 7, y + 8); ctx.fill(); }
    } else if (kind === "arcane") {
      for (let i = 0; i < 8; i++) ctx.fillRect(x - rx * 0.6 + i * rx * 0.17, y - 10 - r() * 18, 14, 24 + r() * 10);
    } else {
      for (let i = 0; i < 5; i++) { ctx.beginPath(); ctx.ellipse(x - rx * 0.5 + i * rx * 0.25, y + (r() - 0.5) * 20, 20, 8, 0, 0, TAU); ctx.fill(); }
    }
  }

  function lock(ctx, x, y) {
    ctx.fillStyle = "#e4e6ea"; ctx.strokeStyle = "#2b3038"; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.arc(x, y - 9, 8, Math.PI, 0); ctx.stroke();
    RA.roundRect(ctx, x - 12, y - 9, 24, 19, 4); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#2b3038"; ctx.beginPath(); ctx.arc(x, y, 2.5, 0, TAU); ctx.fill();
  }

  function bridge(ctx, a, b, open) {
    const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy), ux = dx / len, uy = dy / len;
    const x1 = a.x + ux * a.rx * 0.85, y1 = a.y + uy * a.ry * 0.85, x2 = b.x - ux * b.rx * 0.85, y2 = b.y - uy * b.ry * 0.85;
    const mx = (x1 + x2) / 2, my = (y1 + y2) / 2 + 24;
    ctx.save();
    if (!open) {
      ctx.setLineDash([6, 8]); ctx.strokeStyle = "rgba(255,255,255,0.55)"; ctx.lineWidth = 2.5;
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.quadraticCurveTo(mx, my, x2, y2); ctx.stroke();
      ctx.restore(); return;
    }
    const nx = -uy, ny = ux;
    for (const off of [-6, 6]) {
      ctx.strokeStyle = "#4a3523"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(x1 + nx * off, y1 + ny * off); ctx.quadraticCurveTo(mx + nx * off, my + ny * off, x2 + nx * off, y2 + ny * off); ctx.stroke();
    }
    ctx.strokeStyle = "#b08a5a"; ctx.lineWidth = 3.5;
    for (let t = 0.03; t < 1; t += 0.045) {
      const q = (1 - t) * (1 - t), m = 2 * t * (1 - t), u = t * t;
      const cx = q * x1 + m * mx + u * x2, cy = q * y1 + m * my + u * y2;
      ctx.beginPath(); ctx.moveTo(cx - nx * 6, cy - ny * 6); ctx.lineTo(cx + nx * 6, cy + ny * 6); ctx.stroke();
    }
    ctx.restore();
  }

  function button(ctx, text, x, y) {
    ctx.font = `bold 13px ${FONT}`;
    const w = ctx.measureText(text).width + 22;
    ctx.fillStyle = "#3fb4f0"; RA.roundRect(ctx, x - w / 2, y - 12, w, 24, 12); ctx.fill();
    ctx.strokeStyle = "#1b2a38"; ctx.lineWidth = 1.5; ctx.stroke();
    ctx.fillStyle = "#08263a"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(text, x, y + 1);
  }

  function legend(ctx) {
    const w = 360, h = 44, x = 40, y = H - 40 - h;
    ctx.fillStyle = "rgba(35,42,51,0.82)"; RA.roundRect(ctx, x, y, w, h, 10); ctx.fill();
    ctx.font = `13px ${FONT}`; ctx.textAlign = "left"; ctx.textBaseline = "middle";
    const cy = y + h / 2;
    ctx.fillStyle = "#7fa65a"; ctx.beginPath(); ctx.arc(x + 22, cy, 7, 0, TAU); ctx.fill();
    ctx.fillStyle = "#f2f4f7"; ctx.fillText("已開放（點了看區域圖）", x + 34, cy);
    ctx.save(); ctx.translate(x + 210, cy + 3); ctx.scale(0.6, 0.6); lock(ctx, 0, 0); ctx.restore();
    ctx.fillStyle = "#f2f4f7"; ctx.fillText("未開放", x + 224, cy);
    ctx.fillStyle = "#2f8cff"; ctx.strokeStyle = "#fff"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(x + 292, cy, 6, 0, TAU); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#f2f4f7"; ctx.fillText("自己", x + 304, cy);
  }

  function draw(canvas) {
    canvas.width = W; canvas.height = H;
    const ctx = canvas.getContext("2d");
    sky(ctx);
    const cap = ISLANDS[0];
    for (const is of ISLANDS.slice(1)) bridge(ctx, cap, is, is.state === "open");
    for (const is of ISLANDS.slice().sort((a, b) => a.y - b.y)) {
      const grey = is.state !== "open";
      underside(ctx, is, grey);
      const p = blob(is.x, is.y, is.rx, is.ry, is.x * 3 + is.y);
      ctx.save(); ctx.clip(p);
      ({ cloud: topCloud, ashen: topAshen, capital: topCapital })[is.kind]?.(ctx, is);
      if (grey) topLocked(ctx, is);
      ctx.restore();
      ctx.strokeStyle = "rgba(30,26,22,0.75)"; ctx.lineWidth = 2; ctx.stroke(p);
      if (is.kind === "capital") tower(ctx, is);
      if (grey) {
        // 雲纏著、上鎖
        const r = RA.rng(is.x + 7);
        for (let i = 0; i < 9; i++) RA.puff(ctx, is.x - is.rx + r() * is.rx * 2, is.y + (r() - 0.3) * is.ry, 26 + r() * 20, 0.7);
        lock(ctx, is.x, is.y - 4);
      } else {
        const g = ctx.createRadialGradient(is.x, is.y, is.rx * 0.6, is.x, is.y, is.rx * 1.25);
        g.addColorStop(0, "rgba(255,240,200,0)"); g.addColorStop(1, "rgba(255,240,200,0)");
      }
      if (is.here) {
        const [hx, hy] = [is.x - is.rx * 0.55, is.y + is.ry * 0.35];
        RA.selfMark(ctx, "painted", hx, hy - 10);
      }
      // 名字、等級、城鎮傳送
      const ly = is.y + is.ry + is.ry * 0.45 + 18;
      RA.label(ctx, "painted", is.name, is.x, ly, { grey });
      if (grey) {
        ctx.font = `bold 12px ${FONT}`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
        const t = COND[is.state], w = ctx.measureText(t).width + 14;
        ctx.fillStyle = "rgba(35,42,51,0.7)"; RA.roundRect(ctx, is.x - w / 2, ly + 13, w, 18, 9); ctx.fill();
        ctx.fillStyle = "#d8dce2"; ctx.fillText(t, is.x, ly + 23);
      } else {
        if (is.lv) RA.lvTag(ctx, "painted", is.lv, is.x, ly + 21, false);
        if (!is.here) button(ctx, `傳送到${is.town}`, is.x, ly + (is.lv ? 46 : 26));
        else {
          ctx.font = `bold 12px ${FONT}`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
          const t = `你在${is.town}`, w = ctx.measureText(t).width + 16;
          ctx.fillStyle = "#2f8cff"; RA.roundRect(ctx, is.x - w / 2, ly + 34, w, 20, 10); ctx.fill();
          ctx.fillStyle = "#ffffff"; ctx.fillText(t, is.x, ly + 45);
        }
      }
    }
    // 標題
    ctx.font = `bold 28px ${FONT}`;
    ctx.fillStyle = "rgba(35,42,51,0.82)"; RA.roundRect(ctx, 40, 34, 300, 60, 12); ctx.fill();
    ctx.strokeStyle = "#e0c27a"; ctx.lineWidth = 2; ctx.stroke();
    ctx.fillStyle = "#ffffff"; ctx.textAlign = "left"; ctx.textBaseline = "middle"; ctx.fillText("大世界", 58, 65);
    ctx.font = `bold 13px ${FONT}`; ctx.fillStyle = "#ffe08a"; ctx.fillText("在城鎮裡：點城鎮直接傳送", 160, 66);
    legend(ctx);
    // 外框
    ctx.strokeStyle = "#5a3c24"; ctx.lineWidth = 22; ctx.strokeRect(11, 11, W - 22, H - 22);
    ctx.strokeStyle = "#8a5f38"; ctx.lineWidth = 6; ctx.strokeRect(19, 19, W - 38, H - 38);
    ctx.strokeStyle = "#e0c27a"; ctx.lineWidth = 2; ctx.strokeRect(25, 25, W - 50, H - 50);
  }

  window.WorldPaintedArt = { draw, W, H, ISLANDS };
})();
