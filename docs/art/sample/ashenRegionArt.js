// 灰燼荒原區域插畫（俯視彩繪風，B 案）。要先載入 regionArt.js。全部程式繪製。
// 地點座標照 content/world/maps/ashen_waste.yaml 的 pos，連線照同檔 edges。
(function () {
  const RA = window.RegionArt, W = RA.W, H = RA.H, P = RA.P;
  const LOC = [
    { id: "ember_market", name: "餘燼集", kind: "town", lv: "", pos: [15, 80] },
    { id: "ash_ferry", name: "灰渡口", kind: "gate", lv: "", pos: [5, 95] },
    { id: "scorched_outskirts", name: "焦土外圍", kind: "camp", lv: "5", pos: [32, 72] },
    { id: "old_iron_post", name: "舊鐵哨站", kind: "village", lv: "5", pos: [20, 56] },
    { id: "deadwood_forest", name: "枯木林", kind: "camp", lv: "5～6", pos: [48, 62] },
    { id: "red_sand_village", name: "赤沙村", kind: "village", lv: "6", pos: [40, 88] },
    { id: "ash_mire", name: "灰泥沼", kind: "camp", lv: "6", pos: [12, 40] },
    { id: "cooling_well", name: "冷卻井", kind: "ruin", lv: "6", pos: [34, 44] },
    { id: "gang_convoy_road", name: "斷崖幫運輸道", kind: "camp", lv: "6", pos: [64, 70] },
    { id: "ash_well_village", name: "灰井村", kind: "village", lv: "7", pos: [8, 24] },
    { id: "tar_pits", name: "焦油坑", kind: "camp", lv: "7", pos: [46, 30] },
    { id: "overseer_camp", name: "熔爐督工營", kind: "elite_lair", lv: "7", pos: [80, 78] },
    { id: "iron_forge_village", name: "鐵爐村", kind: "village", lv: "8", pos: [94, 90] },
    { id: "obsidian_valley", name: "黑曜谷", kind: "secret", lv: "8", pos: [30, 12], hidden: true },
    { id: "lava_cave", name: "熔岩洞窟", kind: "camp", lv: "7～8", pos: [62, 34] },
    { id: "horned_altar", name: "角魔古祭壇", kind: "altar", lv: "7", pos: [84, 44] },
    { id: "ruined_fortress", name: "廢墟要塞", kind: "ruin", lv: "8", pos: [66, 14] },
    { id: "molten_heart_pit", name: "熔心坑", kind: "boss", lv: "9", pos: [90, 8] },
  ];
  const EDGES = [
    ["ash_ferry", "ember_market"], ["ember_market", "scorched_outskirts"], ["ember_market", "old_iron_post"],
    ["scorched_outskirts", "deadwood_forest"], ["scorched_outskirts", "red_sand_village"], ["old_iron_post", "ash_mire"],
    ["old_iron_post", "cooling_well"], ["deadwood_forest", "gang_convoy_road"], ["ash_mire", "ash_well_village"],
    ["cooling_well", "tar_pits"], ["gang_convoy_road", "overseer_camp"], ["tar_pits", "lava_cave"],
    ["tar_pits", "obsidian_valley"], ["overseer_camp", "iron_forge_village"], ["lava_cave", "horned_altar"],
    ["lava_cave", "ruined_fortress"], ["ruined_fortress", "molten_heart_pit"],
  ];
  const STATE = {
    visited: ["ember_market", "ash_ferry", "scorched_outskirts", "old_iron_post", "deadwood_forest", "red_sand_village",
      "cooling_well", "gang_convoy_road"],
    cleared: ["scorched_outskirts", "red_sand_village", "old_iron_post"],
    here: "deadwood_forest",
    quests: ["old_iron_post", "overseer_camp"],
    stones: [["ember_market", true], ["old_iron_post", true], ["tar_pits", false]],
    trail: ["scorched_outskirts", "deadwood_forest"],
  };
  const LAVA = [[89, 11], [86, 20], [80, 30], [74, 40], [72, 52], [78, 60], [90, 62], [102, 60]];

  function base(ctx) {
    const g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, "#3d302b"); g.addColorStop(0.4, "#6b5848"); g.addColorStop(0.8, "#94714f"); g.addColorStop(1, "#b07a4c");
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    const r = RA.rng(201);
    for (let i = 0; i < 300; i++) {
      const x = r() * W, y = r() * H, rad = 15 + r() * 60;
      ctx.fillStyle = ["rgba(30,22,18,0.12)", "rgba(150,110,80,0.12)", "rgba(120,60,30,0.10)"][i % 3];
      ctx.beginPath(); ctx.ellipse(x, y, rad, rad * 0.6, r() * 3, 0, Math.PI * 2); ctx.fill();
    }
    // 地面裂縫：暗的和發光的
    for (let i = 0; i < 26; i++) {
      let x = r() * W, y = r() * H;
      const glow = i % 3 === 0;
      ctx.save();
      ctx.strokeStyle = glow ? "#ff7a1a" : "rgba(30,20,15,0.6)"; ctx.lineWidth = glow ? 2 : 1.5;
      if (glow) { ctx.shadowColor = "#ff6a1a"; ctx.shadowBlur = 8; }
      ctx.beginPath(); ctx.moveTo(x, y);
      for (let k = 0; k < 4; k++) { x += (r() - 0.5) * 40; y += (r() - 0.3) * 20; ctx.lineTo(x, y); }
      ctx.stroke(); ctx.restore();
    }
  }

  function ashRiver(ctx) {
    const pts = [[-2, 85], [7, 89], [12, 95], [16, 103]].map((p) => P(p[0], p[1]));
    ctx.lineCap = "round"; ctx.lineJoin = "round";
    RA.pathThrough(ctx, pts); ctx.strokeStyle = "#4a3e36"; ctx.lineWidth = 36; ctx.stroke();
    RA.pathThrough(ctx, pts); ctx.strokeStyle = "#5f7178"; ctx.lineWidth = 26; ctx.stroke();
    RA.pathThrough(ctx, pts); ctx.strokeStyle = "#8a9ca2"; ctx.lineWidth = 10; ctx.stroke();
  }

  function lavaRiver(ctx) {
    const pts = LAVA.map((p) => P(p[0], p[1]));
    ctx.lineCap = "round"; ctx.lineJoin = "round";
    ctx.save();
    RA.pathThrough(ctx, pts); ctx.strokeStyle = "#2a1610"; ctx.lineWidth = 42; ctx.stroke();
    ctx.shadowColor = "#ff6a1a"; ctx.shadowBlur = 24;
    RA.pathThrough(ctx, pts); ctx.strokeStyle = "#c2410c"; ctx.lineWidth = 28; ctx.stroke();
    RA.pathThrough(ctx, pts); ctx.strokeStyle = "#ff7a1a"; ctx.lineWidth = 16; ctx.stroke();
    ctx.shadowBlur = 0;
    RA.pathThrough(ctx, pts); ctx.strokeStyle = "#ffd36b"; ctx.lineWidth = 4; ctx.stroke();
    ctx.restore();
    // 熔岩表面的硬殼
    const r = RA.rng(207);
    for (let i = 0; i < pts.length - 1; i++) {
      for (let t = 0.2; t < 1; t += 0.3) {
        const x = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t + (r() - 0.5) * 10, y = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t + (r() - 0.5) * 8;
        ctx.fillStyle = "rgba(50,25,15,0.75)";
        ctx.beginPath(); ctx.ellipse(x, y, 5 + r() * 5, 3 + r() * 2, r() * 3, 0, Math.PI * 2); ctx.fill();
      }
    }
    // 熔岩洞窟－角魔古祭壇之間的石橋
    const [bx, by] = P(75, 39);
    ctx.save(); ctx.translate(bx, by); ctx.rotate(0.25);
    ctx.fillStyle = "#6e6258"; ctx.fillRect(-34, -8, 68, 16);
    ctx.strokeStyle = "#2b221d"; ctx.lineWidth = 2; ctx.strokeRect(-34, -8, 68, 16);
    for (let k = -26; k <= 26; k += 13) { ctx.beginPath(); ctx.moveTo(k, -8); ctx.lineTo(k, 8); ctx.stroke(); }
    ctx.restore();
  }

  function volcanoShape(ctx) {
    const [x, y] = P(89, 26), h = 190, w = 170;
    ctx.fillStyle = "#5a4a42";
    ctx.beginPath(); ctx.moveTo(x - w, y); ctx.lineTo(x - 34, y - h); ctx.lineTo(x, y - h + 6); ctx.lineTo(x + 4, y); ctx.closePath(); ctx.fill();
    ctx.fillStyle = "#33281f";
    ctx.beginPath(); ctx.moveTo(x, y - h + 6); ctx.lineTo(x + 34, y - h); ctx.lineTo(x + w, y); ctx.lineTo(x + 4, y); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = "rgba(25,18,14,0.8)"; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(x - w, y); ctx.lineTo(x - 34, y - h); ctx.moveTo(x + 34, y - h); ctx.lineTo(x + w, y); ctx.stroke();
    // 火口
    ctx.save();
    ctx.shadowColor = "#ff6a1a"; ctx.shadowBlur = 30;
    ctx.fillStyle = "#ff8a2a"; ctx.beginPath(); ctx.ellipse(x, y - h + 2, 36, 9, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#ffd36b"; ctx.beginPath(); ctx.ellipse(x, y - h + 2, 20, 4, 0, 0, Math.PI * 2); ctx.fill();
    // 流下來的熔岩
    ctx.strokeStyle = "#ff7a1a"; ctx.lineWidth = 4;
    ctx.beginPath(); ctx.moveTo(x - 12, y - h + 8); ctx.quadraticCurveTo(x - 30, y - h * 0.5, x - 20, y - 4); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x + 16, y - h + 8); ctx.quadraticCurveTo(x + 40, y - h * 0.55, x + 70, y - 30); ctx.stroke();
    ctx.restore();
    return [x, y - h];
  }
  function plume(ctx, x, y) {
    const r = RA.rng(211);
    for (let i = 0; i < 14; i++) {
      const t = i / 14;
      RA.puff(ctx, x - t * 160 + (r() - 0.5) * 20, y - 20 - t * 60 + (r() - 0.5) * 16, 18 + t * 30, 0.55 - t * 0.25, [92, 80, 74]);
    }
  }

  function ridges(ctx) {
    const r = RA.rng(223);
    const list = [];
    for (let gx = -4; gx <= 76; gx += 6.5) {
      for (let gy = 4; gy <= 22; gy += 6) {
        const px = gx + (r() - 0.5) * 4, py = gy + (r() - 0.5) * 3;
        if (LOC.some((l) => Math.hypot(l.pos[0] - px, (l.pos[1] - py) * 1.3) < 5.5)) continue;
        list.push([px, py, 40 + (24 - py) * 2 + r() * 22]);
      }
    }
    // 東側和南邊的岩台
    for (let i = 0; i < 6; i++) list.push([92 + r() * 10, 36 + r() * 16, 36 + r() * 20]);
    for (let i = 0; i < 4; i++) list.push([62 + r() * 10, 86 + r() * 8, 26 + r() * 12]);
    list.sort((a, b) => a[1] - b[1]).forEach(([px, py, h]) => {
      const [x, y] = P(px, py);
      RA.mountain(ctx, "painted", x, y, h, r, false, ["#7a685c", "#43372f"]);
    });
  }

  function deadTree(ctx, x, y, k, r) {
    ctx.strokeStyle = "#2e2420"; ctx.lineCap = "round";
    ctx.lineWidth = 3 * k; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, y - 22 * k); ctx.stroke();
    ctx.lineWidth = 1.6 * k;
    for (const [sx, sy, ex, ey] of [[0, -12, -9, -20], [0, -16, 8, -26], [0, -22, -4, -30], [-5, -17, -10, -16]]) {
      ctx.beginPath(); ctx.moveTo(x + sx * k, y + sy * k); ctx.lineTo(x + (ex + (r() - 0.5) * 3) * k, y + ey * k); ctx.stroke();
    }
  }
  function deadwood(ctx) {
    const r = RA.rng(227);
    const [cx, cy] = P(48, 62);
    const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, 130);
    g.addColorStop(0, "rgba(60,52,48,0.45)"); g.addColorStop(1, "rgba(60,52,48,0)");
    ctx.fillStyle = g; ctx.fillRect(cx - 140, cy - 140, 280, 280);
    const items = [];
    for (let i = 0; i < 60; i++) {
      const a = r() * Math.PI * 2, d = Math.sqrt(r()) * 12;
      const px = 48 + Math.cos(a) * d * 1.3, py = 62 + Math.sin(a) * d * 0.8;
      if (LOC.some((l) => Math.hypot(l.pos[0] - px, l.pos[1] - py) < 4.5)) continue;
      items.push([...P(px, py), 0.8 + r() * 0.5]);
    }
    items.sort((a, b) => a[1] - b[1]).forEach(([x, y, k]) => deadTree(ctx, x, y, k, r));
  }

  function mire(ctx) {
    const [x, y] = P(12, 40);
    ctx.fillStyle = "#4e4a3c"; ctx.beginPath(); ctx.ellipse(x + 10, y + 6, 92, 50, 0.1, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#666049"; ctx.beginPath(); ctx.ellipse(x + 18, y + 2, 64, 32, 0.1, 0, Math.PI * 2); ctx.fill();
    const r = RA.rng(229);
    ctx.strokeStyle = "rgba(200,190,160,0.6)"; ctx.lineWidth = 1.2;
    for (let i = 0; i < 12; i++) { ctx.beginPath(); ctx.arc(x + (r() - 0.4) * 120, y + (r() - 0.5) * 60, 2 + r() * 4, 0, Math.PI * 2); ctx.stroke(); }
    ctx.strokeStyle = "#6f6a3a"; ctx.lineWidth = 1.6;
    for (let i = 0; i < 18; i++) {
      const rx = x - 70 + r() * 170, ry = y - 40 + r() * 90;
      ctx.beginPath(); ctx.moveTo(rx, ry); ctx.lineTo(rx + (r() - 0.5) * 4, ry - 10 - r() * 8); ctx.stroke();
    }
  }

  function tarPits(ctx) {
    const [x, y] = P(46, 30);
    for (const [ox, oy, rx, ry] of [[-60, 10, 34, 16], [50, 18, 30, 14], [-10, -34, 26, 12], [30, -20, 18, 9], [-50, -24, 16, 8]]) {
      ctx.fillStyle = "#0f0c0b"; ctx.beginPath(); ctx.ellipse(x + ox, y + oy, rx, ry, 0, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = "#3a2e28"; ctx.lineWidth = 3; ctx.stroke();
      ctx.fillStyle = "rgba(170,160,200,0.35)"; ctx.beginPath(); ctx.ellipse(x + ox - rx * 0.3, y + oy - ry * 0.3, rx * 0.35, ry * 0.25, 0, 0, Math.PI * 2); ctx.fill();
    }
  }

  function coolingWells(ctx) {
    const [x, y] = P(34, 44);
    for (const [ox, oy] of [[-46, -18], [46, -18], [-50, 22], [50, 22]]) {
      ctx.fillStyle = "#8a8078"; ctx.beginPath(); ctx.arc(x + ox, y + oy, 11, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = "#2b221d"; ctx.lineWidth = 1.6; ctx.stroke();
      ctx.fillStyle = "#4aa3d8"; ctx.beginPath(); ctx.arc(x + ox, y + oy, 6.5, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "rgba(220,245,255,0.8)"; ctx.beginPath(); ctx.arc(x + ox - 2, y + oy - 2, 2, 0, Math.PI * 2); ctx.fill();
    }
  }

  function redSand(ctx) {
    const r = RA.rng(233);
    for (let i = 0; i < 26; i++) {
      const [x, y] = P(24 + r() * 40, 80 + r() * 18);
      ctx.fillStyle = i % 2 ? "rgba(196,112,63,0.55)" : "rgba(214,138,82,0.5)";
      ctx.beginPath(); ctx.ellipse(x, y, 40 + r() * 30, 10 + r() * 6, 0, Math.PI, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = "rgba(255,210,160,0.45)"; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.ellipse(x, y, 30, 7, 0, Math.PI * 1.15, Math.PI * 1.85); ctx.stroke();
    }
  }

  function fortress(ctx) {
    const [x, y] = P(66, 14);
    ctx.fillStyle = "#6e6258"; ctx.strokeStyle = "#2b221d"; ctx.lineWidth = 1.6;
    for (const [ox, oy, w, h] of [[-60, 10, 40, 12], [-10, 24, 50, 10], [40, 6, 14, 30], [-64, -20, 12, 30]]) {
      ctx.fillRect(x + ox, y + oy, w, h); ctx.strokeRect(x + ox, y + oy, w, h);
    }
  }

  function settlements(ctx) {
    // 餘燼集旁的小屋（帳篷布＋鐵皮頂）
    const [tx, ty] = P(15, 80);
    for (const [ox, oy] of [[-48, 6], [42, 12], [-30, -30], [36, -26]]) {
      const x = tx + ox, y = ty + oy;
      ctx.fillStyle = "#c9b79a"; ctx.fillRect(x - 7, y - 6, 14, 9);
      ctx.fillStyle = "#8a4a2a"; ctx.beginPath(); ctx.moveTo(x - 10, y - 5); ctx.lineTo(x, y - 13); ctx.lineTo(x + 10, y - 5); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = "#27303a"; ctx.lineWidth = 1; ctx.strokeRect(x - 7, y - 6, 14, 9);
    }
  }

  function embers(ctx) {
    const r = RA.rng(239);
    ctx.save(); ctx.shadowColor = "#ff8a2a"; ctx.shadowBlur = 6;
    for (let i = 0; i < 90; i++) {
      ctx.fillStyle = `rgba(255,${140 + Math.floor(r() * 80)},60,${0.4 + r() * 0.5})`;
      ctx.beginPath(); ctx.arc(r() * W, r() * H, 1 + r() * 1.6, 0, Math.PI * 2); ctx.fill();
    }
    ctx.restore();
  }

  function labels(ctx) {
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.font = `italic 15px ${RA.PAL.painted.font}`; ctx.fillStyle = "rgba(255,236,210,0.8)";
    for (const [t, px, py] of [["赤　沙", 52, 95], ["灰　河", 13, 99], ["焦　土", 28, 64], ["熔岩河", 80, 66]]) {
      const [x, y] = P(px, py); ctx.fillText(t, x, y);
    }
  }

  function terrain(ctx) {
    base(ctx);
    redSand(ctx);
    ashRiver(ctx);
    mire(ctx);
    tarPits(ctx);
    coolingWells(ctx);
    lavaRiver(ctx);
    deadwood(ctx);
    settlements(ctx);
    fortress(ctx);
    ridges(ctx);
    volcanoShape(ctx);
    embers(ctx);
    labels(ctx);
  }

  // 煙霧上方仍看得到火山口和噴煙（只是地景，不洩漏地點）
  function afterFog(ctx) {
    const [x, y] = P(89, 26);
    ctx.save(); ctx.globalAlpha = 0.85;
    ctx.beginPath(); ctx.rect(0, 0, W, y - 120); ctx.clip();
    const top = volcanoShape(ctx);
    ctx.restore();
    plume(ctx, top[0], top[1]);
  }

  RA.register("ashen_waste", {
    title: "灰燼荒原", lv: "5～9", loc: LOC, edges: EDGES, state: STATE, terrain, afterFog,
    fog: { base: "#7d736b", puff: [176, 166, 156], shade: "60,50,44" },
  });
})();
