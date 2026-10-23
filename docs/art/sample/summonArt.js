// 召喚物外觀（美術樣張，06-技能.md 6.29.5 的 17 種）：體型 × 元素配色 × 大小 × 特徵。
// 座標和紙娃娃相同：腳底中心為原點，往上是負，身高約 46。人形體型直接用紙娃娃；其他體型在這裡畫。
// 不認得的體型退回人形骷髏，不會出錯。
// 注意（3-33h1 檢查）：地面影子不要畫進加外框的那一層，否則會變成實心黑橢圓；正式版要把影子分開畫。
window.SummonArt = (() => {
  const TAU = Math.PI * 2;
  const D = window.PaperDoll;
  const INK = "#16121a";
  // 關鍵字色票（和技能圖示、裝備共用）
  const KW = { ignite: "#ff6a1a", wet: "#4aa8ff", shock: "#fff36b", freeze: "#8fe3ff", prone: "#e0b080", impact: "#ff9a4a", mark: "#d06aff", high: "#ffe9a8", hidden: "#a0a0c8", summon: "#7dffb0" };
  const SIZE = { small: 0.8, medium: 1, large: 1.25 };

  // ---- 17 種召喚物 → 外觀資料（正式版放 content/，這裡是樣張的對照）----
  const SUMMONS = {
    fire_spirit: { zh: "火靈", body: "spirit", element: "ignite", size: "medium" },
    ice_spirit: { zh: "冰靈", body: "spirit", element: "freeze", size: "medium" },
    thunder_spirit: { zh: "雷靈", body: "spirit", element: "shock", size: "medium" },
    water_sprite: { zh: "水精", body: "spirit", element: "wet", size: "small", trait: "puddle" },
    skeleton_warrior: { zh: "骷髏戰士", body: "humanoid", variant: "skeleton", element: "prone", size: "medium", trait: "shield" },
    golem: { zh: "石像", body: "construct", variant: "golem", element: "impact", size: "large" },
    shade: { zh: "影魅", body: "humanoid", variant: "shade", element: "hidden", size: "medium", trait: "translucent" },
    hawk: { zh: "鷹隼", body: "beast", variant: "bird", element: "mark", size: "small", trait: "flying" },
    war_totem: { zh: "戰意圖騰", body: "totem", variant: "war", element: "summon", size: "medium", trait: "aura" },
    afterimage: { zh: "殘影分身", body: "humanoid", variant: "afterimage", element: "hidden", size: "medium", trait: "translucent" },
    bomb_puppet: { zh: "爆裂傀儡", body: "construct", variant: "bomb", element: "ignite", size: "small", trait: "fuse" },
    vine: { zh: "藤蔓", body: "plant", element: "prone", size: "medium" },
    earth_wall: { zh: "土牆", body: "construct", variant: "wall", element: "impact", size: "medium" },
    war_wolf: { zh: "戰狼", body: "beast", variant: "wolf", element: "prone", size: "medium" },
    guardian_spirit: { zh: "守護靈", body: "humanoid", variant: "guardian", element: "summon", size: "medium", trait: "glow" },
    pull_totem: { zh: "吸引圖騰", body: "totem", variant: "pull", element: "impact", size: "medium" },
    plateau_totem: { zh: "高台圖騰", body: "totem", variant: "plateau", element: "high", size: "medium" },
  };

  function mix(a, b, t) {
    const pa = parseInt(a.slice(1), 16), pb = parseInt(b.slice(1), 16);
    const m = (s) => Math.round(((pa >> s) & 255) * (1 - t) + ((pb >> s) & 255) * t);
    return `#${((m(16) << 16) | (m(8) << 8) | m(0)).toString(16).padStart(6, "0")}`;
  }
  function fill(ctx, c, path) { ctx.fillStyle = c; ctx.beginPath(); path(); ctx.fill(); }
  function shadow(ctx, rx, ry = rx * 0.35, y = -1, a = 0.3) { fill(ctx, `rgba(0,0,0,${a})`, () => ctx.ellipse(0, y, rx, ry, 0, 0, TAU)); }
  function eyes(ctx, side, y, c = "#ffffff", gap = 3) {
    if (side === null) return; // 背面不畫眼睛
    const x = side * 2.4;
    fill(ctx, c, () => { ctx.arc(x - gap, y, 1.6, 0, TAU); ctx.arc(x + gap, y, 1.6, 0, TAU); });
  }

  // ---- 漂浮靈：水滴身體＋元素邊緣＋粒子；底下只有小影子 ----
  function spirit(ctx, s, facing, side) {
    const c = KW[s.element] ?? "#c8ccd4";
    const lift = -8;
    shadow(ctx, 8, 3, -1, 0.25);
    if (s.trait === "puddle") fill(ctx, "rgba(74,168,255,0.45)", () => ctx.ellipse(0, -1, 13, 4, 0, 0, TAU));
    ctx.save(); ctx.translate(0, lift);
    // 外光
    const g = ctx.createRadialGradient(0, -14, 2, 0, -14, 18); g.addColorStop(0, c + "99"); g.addColorStop(1, c + "00");
    fill(ctx, g, () => ctx.arc(0, -14, 18, 0, TAU));
    // 身體（水滴）
    const body = () => { ctx.moveTo(0, -30); ctx.quadraticCurveTo(11, -18, 9, -9); ctx.quadraticCurveTo(0, 0, -9, -9); ctx.quadraticCurveTo(-11, -18, 0, -30); };
    fill(ctx, mix(c, "#ffffff", 0.25), body);
    fill(ctx, mix(c, "#ffffff", 0.7), () => ctx.ellipse(-3, -16, 3, 5, -0.3, 0, TAU));
    // 元素邊緣
    ctx.fillStyle = c; ctx.strokeStyle = c;
    if (s.element === "ignite") for (const [x, h] of [[-5, 9], [0, 12], [5, 8]]) fill(ctx, c, () => { ctx.moveTo(x - 3, -24); ctx.quadraticCurveTo(x, -24 - h, x + 1, -26 - h); ctx.quadraticCurveTo(x + 3, -24 - h / 2, x + 3, -24); });
    if (s.element === "freeze") for (const [x, y, a] of [[-8, -20, -0.6], [8, -20, 0.6], [0, -31, 0]]) { ctx.save(); ctx.translate(x, y); ctx.rotate(a); fill(ctx, mix(c, "#ffffff", 0.4), () => { ctx.moveTo(0, -6); ctx.lineTo(2.5, 0); ctx.lineTo(0, 3); ctx.lineTo(-2.5, 0); ctx.closePath(); }); ctx.restore(); }
    if (s.element === "shock") { ctx.lineWidth = 1.6; for (const sx of [-1, 1]) { ctx.beginPath(); ctx.moveTo(sx * 8, -26); ctx.lineTo(sx * 12, -21); ctx.lineTo(sx * 9, -18); ctx.lineTo(sx * 14, -12); ctx.stroke(); } }
    if (s.element === "wet") for (const [x, y] of [[-10, -12], [10, -16], [7, -27]]) fill(ctx, c, () => { ctx.moveTo(x, y - 3); ctx.quadraticCurveTo(x + 2.5, y + 1, x, y + 2); ctx.quadraticCurveTo(x - 2.5, y + 1, x, y - 3); });
    eyes(ctx, side, -17, "#1d1a22", 2.6);
    ctx.restore();
  }

  // ---- 構造體 ----
  function construct(ctx, s, facing, side) {
    const c = KW[s.element] ?? "#ffffff";
    if (s.variant === "wall") {
      shadow(ctx, 15, 4);
      fill(ctx, "#6e5a40", () => ctx.roundRect(-15, -24, 30, 23, 2));
      fill(ctx, "#8c7350", () => ctx.roundRect(-15, -26, 30, 6, 2));
      ctx.strokeStyle = "#4a3a28"; ctx.lineWidth = 1;
      for (const [x0, y0, x1, y1] of [[-15, -14, 15, -14], [-5, -20, -5, -14], [6, -14, 6, -2], [-10, -14, -10, -2]]) { ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke(); }
      return;
    }
    if (s.variant === "bomb") {
      shadow(ctx, 9);
      for (const sx of [-1, 1]) fill(ctx, "#5a4a3a", () => ctx.roundRect(sx * 4 - 2, -6, 4, 6, 1));
      fill(ctx, "#6a5a4a", () => ctx.arc(0, -15, 10, 0, TAU));
      ctx.strokeStyle = c; ctx.lineWidth = 1.6; ctx.shadowColor = c; ctx.shadowBlur = 4;
      for (const pts of [[[-6, -20], [-2, -15], [-5, -10]], [[4, -22], [2, -16], [7, -12]]]) { ctx.beginPath(); ctx.moveTo(...pts[0]); for (const p of pts.slice(1)) ctx.lineTo(...p); ctx.stroke(); }
      ctx.shadowBlur = 0;
      ctx.strokeStyle = "#3a2a1c"; ctx.lineWidth = 1.4; ctx.beginPath(); ctx.moveTo(3, -24); ctx.quadraticCurveTo(7, -30, 4, -33); ctx.stroke();
      fill(ctx, "#ffe14d", () => ctx.arc(4, -34, 2.2, 0, TAU)); fill(ctx, c, () => ctx.arc(4, -34, 1.2, 0, TAU));
      eyes(ctx, side, -15, c, 3);
      return;
    }
    // 石像：方塊堆疊
    shadow(ctx, 13);
    const st = "#9a968c", sd = "#6c685f";
    for (const sx of [-1, 1]) fill(ctx, sd, () => ctx.roundRect(sx * 6 - 3.5, -9, 7, 9, 1.5));
    fill(ctx, st, () => ctx.roundRect(-10, -26, 20, 18, 3));
    for (const sx of [-1, 1]) fill(ctx, sd, () => ctx.roundRect(sx * 14 - 3.5, -25, 7, 16, 2));
    fill(ctx, st, () => ctx.roundRect(-6, -36, 12, 10, 2.5));
    ctx.strokeStyle = sd; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(-10, -17); ctx.lineTo(10, -17); ctx.moveTo(0, -26); ctx.lineTo(0, -17); ctx.stroke();
    ctx.shadowColor = c; ctx.shadowBlur = 4; eyes(ctx, side, -31, c, 2.4); ctx.shadowBlur = 0;
  }

  // ---- 野獸（側面骨架；朝南北時用左右鏡像的側面）----
  function beast(ctx, s, facing, side) {
    const dir = side === -1 ? -1 : 1;
    ctx.save(); ctx.scale(dir, 1);
    if (s.variant === "bird") {
      shadow(ctx, 7, 2.5, -1, 0.22); // 飛行：影子留在地上、身體往上
      ctx.translate(0, -22);
      const c = "#8a6a48", d = "#5e4430";
      fill(ctx, d, () => { ctx.moveTo(-2, -2); ctx.quadraticCurveTo(-12, -14, -20, -8); ctx.quadraticCurveTo(-12, -4, -4, 2); });
      fill(ctx, d, () => { ctx.moveTo(2, -2); ctx.quadraticCurveTo(10, -16, 18, -12); ctx.quadraticCurveTo(12, -4, 4, 2); });
      fill(ctx, c, () => ctx.ellipse(0, 0, 8, 4.5, 0, 0, TAU));
      fill(ctx, "#e6dcc8", () => ctx.ellipse(1, 1.5, 5, 2.4, 0, 0, TAU));
      fill(ctx, c, () => ctx.arc(8, -2, 3.5, 0, TAU));
      fill(ctx, "#e8bb48", () => { ctx.moveTo(11, -3); ctx.lineTo(14, -1.5); ctx.lineTo(11, -0.5); ctx.closePath(); });
      fill(ctx, d, () => { ctx.moveTo(-8, 0); ctx.lineTo(-14, -2); ctx.lineTo(-14, 3); ctx.closePath(); });
      if (side !== null) fill(ctx, "#1d1a22", () => ctx.arc(9, -2.6, 0.9, 0, TAU));
      fill(ctx, KW.mark, () => ctx.arc(8, -9, 1.6, 0, TAU));
      ctx.restore();
      return;
    }
    if (s.variant === "bear") {
      // 熊（形態 #48）：厚重、圓背、粗腿、圓耳；熊爪露在前腳
      shadow(ctx, 17, 5);
      const c = "#6a4a32", d = "#4a3222";
      for (const x of [-10, -5, 6, 11]) fill(ctx, x < 0 ? d : c, () => ctx.roundRect(x - 2.6, -11, 5.2, 11, 2));
      for (const x of [6, 11]) fill(ctx, "#e8e0d0", () => { ctx.moveTo(x - 2, 0); ctx.lineTo(x - 1, 2); ctx.lineTo(x, 0); ctx.lineTo(x + 1, 2); ctx.lineTo(x + 2, 0); ctx.closePath(); });
      fill(ctx, c, () => { ctx.moveTo(-15, -9); ctx.quadraticCurveTo(-16, -26, -2, -27); ctx.quadraticCurveTo(12, -27, 14, -12); ctx.lineTo(14, -8); ctx.lineTo(-15, -8); ctx.closePath(); });
      fill(ctx, "#8a6648", () => ctx.ellipse(1, -11, 10, 3, 0, 0, TAU));
      fill(ctx, c, () => ctx.ellipse(15, -19, 7, 6, 0, 0, TAU));
      fill(ctx, "#a08060", () => ctx.ellipse(20, -17.5, 3.5, 2.6, 0, 0, TAU));
      fill(ctx, "#1d1a22", () => ctx.arc(23, -18, 1.1, 0, TAU));
      for (const x of [11, 17]) fill(ctx, d, () => ctx.arc(x, -25, 2.6, 0, TAU));
      if (side !== null) fill(ctx, "#1d1a22", () => ctx.arc(17, -21, 1, 0, TAU));
      ctx.restore();
      return;
    }
    if (s.variant === "cat") {
      // 貓（形態 #48）：細長、低姿態、長尾上翹、尖耳、亮黃眼
      shadow(ctx, 14, 3.5);
      const c = "#3a3440", d = "#26222c";
      for (const x of [-9, -5, 7, 10]) fill(ctx, x < 0 ? d : c, () => ctx.roundRect(x - 1.3, -7, 2.6, 7, 1));
      fill(ctx, c, () => ctx.ellipse(0, -9, 12, 4, -0.05, 0, TAU));
      ctx.strokeStyle = c; ctx.lineWidth = 2.6; ctx.lineCap = "round"; ctx.beginPath(); ctx.moveTo(-11, -10); ctx.quadraticCurveTo(-20, -12, -18, -22); ctx.stroke(); ctx.lineCap = "butt";
      fill(ctx, c, () => ctx.ellipse(13, -12, 4.6, 4, 0, 0, TAU));
      for (const x of [11, 15]) fill(ctx, c, () => { ctx.moveTo(x - 2, -14.5); ctx.lineTo(x, -20); ctx.lineTo(x + 2, -14.5); ctx.closePath(); });
      if (side !== null) fill(ctx, "#ffe14d", () => { ctx.ellipse(15, -12.5, 1.3, 0.9, 0, 0, TAU); });
      for (const x of [7, 10]) fill(ctx, "#e8e0d0", () => { ctx.moveTo(x - 1.2, 0); ctx.lineTo(x, 1.6); ctx.lineTo(x + 1.2, 0); ctx.closePath(); });
      ctx.restore();
      return;
    }
    // 狼
    shadow(ctx, 15, 4);
    const c = "#7a7a82", d = "#55555c";
    for (const x of [-9, -5, 6, 10]) fill(ctx, x < 0 ? d : c, () => ctx.roundRect(x - 1.6, -10, 3.2, 10, 1.2));
    fill(ctx, c, () => ctx.ellipse(0, -13, 13, 6, 0, 0, TAU));
    fill(ctx, "#b8b8be", () => ctx.ellipse(2, -10, 8, 2.5, 0, 0, TAU));
    fill(ctx, d, () => { ctx.moveTo(-12, -15); ctx.quadraticCurveTo(-20, -20, -22, -12); ctx.quadraticCurveTo(-17, -14, -12, -11); });
    fill(ctx, c, () => ctx.ellipse(13, -19, 6, 5, -0.3, 0, TAU));
    fill(ctx, c, () => { ctx.moveTo(16, -20); ctx.lineTo(23, -17); ctx.lineTo(16, -15); ctx.closePath(); });
    for (const x of [10, 14]) fill(ctx, d, () => { ctx.moveTo(x - 2, -23); ctx.lineTo(x, -28); ctx.lineTo(x + 2, -23); ctx.closePath(); });
    if (side !== null) fill(ctx, "#ffe14d", () => ctx.arc(16, -20, 1.1, 0, TAU));
    fill(ctx, "#b83a3a", () => ctx.roundRect(8, -16, 6, 2, 1)); // 戰狼的項圈
    ctx.restore();
  }

  // ---- 植物：藤蔓貼地、捲曲＋刺＋葉 ----
  function plant(ctx, s) {
    fill(ctx, "rgba(40,70,30,0.45)", () => ctx.ellipse(0, -2, 18, 6, 0, 0, TAU));
    ctx.lineCap = "round";
    for (const [a, len] of [[-2.6, 16], [-1.9, 18], [-1.2, 15], [-0.5, 17], [0.2, 14], [-3.2, 13]]) {
      ctx.strokeStyle = "#3f6a2a"; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(0, -3);
      const x = Math.cos(a) * len, y = -3 + Math.sin(a) * len * 0.55 - 6;
      ctx.quadraticCurveTo(x * 0.5, y - 8, x, y); ctx.stroke();
      fill(ctx, "#5f9a3c", () => ctx.ellipse(x, y, 3.2, 1.8, a, 0, TAU));
      fill(ctx, "#d0c8a0", () => { ctx.moveTo(x * 0.6, y * 0.7 - 3); ctx.lineTo(x * 0.6 + 2, y * 0.7 - 6); ctx.lineTo(x * 0.6 + 3, y * 0.7 - 3); ctx.closePath(); });
    }
    ctx.lineCap = "butt";
    fill(ctx, "#2f5020", () => ctx.ellipse(0, -4, 6, 3, 0, 0, TAU));
  }

  // ---- 圖騰：柱子＋頂端符號 ----
  function totem(ctx, s, facing, side) {
    const c = KW[s.element] ?? "#ffffff";
    shadow(ctx, 8);
    if (s.trait === "aura") { ctx.strokeStyle = c + "aa"; ctx.lineWidth = 1.4; ctx.setLineDash([3, 2]); ctx.beginPath(); ctx.ellipse(0, -1, 20, 6, 0, 0, TAU); ctx.stroke(); ctx.setLineDash([]); }
    const wood = s.variant === "plateau" ? "#9a968c" : "#8a5a32", wd = s.variant === "plateau" ? "#6c685f" : "#5e3b1f";
    fill(ctx, wood, () => ctx.roundRect(-4.5, -34, 9, 34, 2));
    for (const y of [-27, -16]) { fill(ctx, wd, () => ctx.rect(-4.5, y, 9, 2)); if (side !== null) fill(ctx, INK, () => { ctx.rect(-2.6, y - 4, 1.8, 1.8); ctx.rect(0.8, y - 4, 1.8, 1.8); }); }
    if (s.variant === "war") {
      fill(ctx, "#5e3b1f", () => ctx.rect(-0.8, -46, 1.6, 13));
      fill(ctx, "#c03030", () => { ctx.moveTo(0.8, -46); ctx.lineTo(12, -43); ctx.lineTo(0.8, -39); ctx.closePath(); });
      fill(ctx, c, () => ctx.arc(0, -36, 2.4, 0, TAU));
    } else if (s.variant === "pull") {
      fill(ctx, "#5a3f80", () => ctx.arc(0, -39, 7, 0, TAU));
      ctx.strokeStyle = "#d06aff"; ctx.lineWidth = 1.5; ctx.beginPath();
      for (let t = 0; t < 4 * Math.PI; t += 0.2) { const r = 6 - t * 0.45; ctx.lineTo(Math.cos(t) * r, -39 + Math.sin(t) * r); } ctx.stroke();
    } else {
      fill(ctx, "#b8b4aa", () => { ctx.moveTo(-9, -36); ctx.lineTo(9, -36); ctx.lineTo(6, -41); ctx.lineTo(-6, -41); ctx.closePath(); });
      fill(ctx, c, () => { ctx.moveTo(0, -47); ctx.lineTo(4, -43); ctx.lineTo(-4, -43); ctx.closePath(); });
    }
  }

  // ---- 人形：沿用紙娃娃，依 variant 選範本與修飾 ----
  function humanoidUnit(s) {
    const T = D.TEMPLATES;
    if (s.variant === "shade") return { look: { skin: "#3a3448", eyes: "#d06aff", hair: "none" }, gear: { body: { kind: "leather", material: "leather", color: "#2a2632" }, head: { kind: "hood", material: "cloth", color: "#1f1c26" }, main_hand: { kind: "dagger", material: "steel" }, off_hand: { kind: "dagger", material: "steel" }, feet: { kind: "boots", material: "leather", color: "#1f1c26" } } };
    if (s.variant === "guardian") return { look: { skin: "#f4ecd0", hair: "long", hairColor: "#fff3c4", eyes: "#fffbe6" }, gear: { body: { kind: "robe", material: "cloth", color: "#f2e6c8" }, off_hand: { kind: "shield_round", material: "gold" }, feet: { kind: "shoes", material: "cloth", color: "#e8dcc0" } } };
    if (s.variant === "afterimage") return T.hero_fighter;
    if (s.variant === "demon") return { look: { skin: "#5a3a6a", eyes: "#ff5a8a", hair: "none" }, gear: { body: { kind: "leather", material: "leather", color: "#2a1a30" }, head: { kind: "horned_helm", material: "iron", color: "#2a1a2a" }, main_hand: { kind: "sword", material: "steel", color: "#6a5a8a" }, off_hand: { kind: "dagger", material: "steel", color: "#6a5a8a" }, feet: { kind: "boots", material: "leather", color: "#1f1426" } } };
    const sk = T.summon_skeleton_warrior;
    return s.trait === "shield" ? { ...sk, gear: { ...sk.gear, off_hand: { kind: "shield_round", material: "wood", color: "#6a5a4a" } } } : sk;
  }
  const HUMANOID_STYLE = {
    shade: { alpha: 0.72, glow: "#7a4ab0" },
    guardian: { alpha: 0.8, glow: "#ffe9a8" },
    afterimage: { alpha: 0.5, tint: "#8fc8ff", glow: "#8fc8ff" },
    demon: { alpha: 1, glow: "#a77bff" },
  };

  const BODY = { spirit, construct, beast, plant, totem };
  /** 驗證＋補預設：任何輸入都回傳畫得出來的外觀。 */
  function resolve(spec) {
    const s = typeof spec === "string" ? SUMMONS[spec] ?? {} : spec;
    const body = BODY[s.body] || s.body === "humanoid" ? s.body : "humanoid";
    return { ...s, body, variant: s.variant ?? (body === "humanoid" ? "skeleton" : undefined), size: SIZE[s.size] ? s.size : "medium" };
  }

  /** 把一個召喚物畫到 ctx（cx, cy＝腳底）；k＝額外縮放。 */
  function stamp(ctx, spec, facing, cx, cy, k = 1) {
    const s = resolve(spec);
    const size = SIZE[s.size] * k;
    const side = facing === "north" ? null : facing === "east" ? 1 : facing === "west" ? -1 : 0;
    if (s.body === "humanoid") {
      const st = HUMANOID_STYLE[s.variant] ?? {};
      // 先畫到離屏，再依 alpha、tint、glow 合成
      const L = 64 * size, off = document.createElement("canvas"); off.width = L * 2; off.height = L * 2;
      const o2 = off.getContext("2d"); o2.scale(2, 2);
      D.stamp(o2, humanoidUnit(s), facing, L / 2, L - 6 * size, size, { dpr: 2 });
      if (st.tint) { o2.globalCompositeOperation = "source-atop"; o2.fillStyle = st.tint + "88"; o2.fillRect(0, 0, L, L); }
      ctx.save();
      if (st.glow) { ctx.shadowColor = st.glow; ctx.shadowBlur = 8 * size; }
      ctx.globalAlpha = st.alpha ?? 1;
      ctx.drawImage(off, cx - L / 2, cy - (L - 6 * size), L, L);
      ctx.restore();
      return;
    }
    // 其他體型：畫到離屏 → 深色外框 → 合成
    const S = 72, dpr = 2, off = document.createElement("canvas"); off.width = S * size * dpr; off.height = S * size * dpr;
    const o = off.getContext("2d"); o.scale(size * dpr, size * dpr); o.translate(S / 2, S - 8);
    BODY[s.body](o, s, facing, side);
    const sil = document.createElement("canvas"); sil.width = off.width; sil.height = off.height;
    const sc = sil.getContext("2d"); sc.drawImage(off, 0, 0); sc.globalCompositeOperation = "source-in"; sc.fillStyle = INK; sc.fillRect(0, 0, sil.width, sil.height);
    const dx = cx - (S / 2) * size, dy = cy - (S - 8) * size, kk = 1.3 * size;
    ctx.save(); ctx.globalAlpha = s.body === "plant" ? 0.9 : 1;
    for (const [ox, oy] of [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [1, -1], [-1, 1], [1, 1]]) ctx.drawImage(sil, dx + ox * kk, dy + oy * kk, S * size, S * size);
    ctx.drawImage(off, dx, dy, S * size, S * size);
    ctx.restore();
  }
  return { stamp, resolve, SUMMONS, KW, SIZE };
})();
