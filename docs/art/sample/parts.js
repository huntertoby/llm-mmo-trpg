// 技能部件圖示庫（美術樣張）：效果原語、狀態、表面、條件、代價、觸發、修正的對象與改變內容。
// 每個圖示畫在以 (0, 0) 為中心、半徑約 10 的範圍內，顏色由呼叫端給；圖示庫與狀態列、表面說明共用。
// 不認得的部件：狀態用「名稱第一個字」，其他用問號，永遠畫得出來。
window.Parts = (() => {
  const TAU = Math.PI * 2;
  const SI = () => window.SkillIcon;

  // ---- 小工具 ----
  function arrow(ctx, x0, y0, x1, y1, head = 4) {
    const a = Math.atan2(y1 - y0, x1 - x0);
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x1, y1);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x1 + Math.cos(a) * 1, y1 + Math.sin(a) * 1);
    ctx.lineTo(x1 - Math.cos(a - 0.6) * head, y1 - Math.sin(a - 0.6) * head);
    ctx.lineTo(x1 - Math.cos(a + 0.6) * head, y1 - Math.sin(a + 0.6) * head);
    ctx.closePath();
    ctx.fill();
  }
  function dot(ctx, x, y, r) {
    ctx.beginPath();
    ctx.arc(x, y, r, 0, TAU);
    ctx.fill();
  }
  function ring(ctx, x, y, r) {
    ctx.beginPath();
    ctx.arc(x, y, r, 0, TAU);
    ctx.stroke();
  }
  function person(ctx, x, y, k = 1) {
    dot(ctx, x, y - 5 * k, 2.6 * k);
    ctx.beginPath();
    ctx.moveTo(x - 4.5 * k, y + 5 * k);
    ctx.quadraticCurveTo(x - 4.5 * k, y - 1.5 * k, x, y - 1.5 * k);
    ctx.quadraticCurveTo(x + 4.5 * k, y - 1.5 * k, x + 4.5 * k, y + 5 * k);
    ctx.closePath();
    ctx.fill();
  }
  function shieldPath(ctx, k = 1) {
    ctx.beginPath();
    ctx.moveTo(0, -9 * k); ctx.lineTo(7.5 * k, -6 * k); ctx.lineTo(7 * k, 2 * k); ctx.lineTo(0, 9 * k); ctx.lineTo(-7 * k, 2 * k); ctx.lineTo(-7.5 * k, -6 * k);
    ctx.closePath();
  }
  function heart(ctx, k = 1) {
    ctx.beginPath();
    ctx.moveTo(0, 8 * k);
    ctx.bezierCurveTo(-11 * k, 0, -6 * k, -10 * k, 0, -4 * k);
    ctx.bezierCurveTo(6 * k, -10 * k, 11 * k, 0, 0, 8 * k);
    ctx.closePath();
  }
  function drop(ctx, x, y, k = 1) {
    ctx.beginPath();
    ctx.moveTo(x, y - 8 * k);
    ctx.bezierCurveTo(x + 6.5 * k, y, x + 5.5 * k, y + 6 * k, x, y + 6 * k);
    ctx.bezierCurveTo(x - 5.5 * k, y + 6 * k, x - 6.5 * k, y, x, y - 8 * k);
    ctx.fill();
  }
  function hourglass(ctx) {
    ctx.beginPath();
    ctx.moveTo(-6, -8); ctx.lineTo(6, -8); ctx.lineTo(0, 0); ctx.lineTo(6, 8); ctx.lineTo(-6, 8); ctx.lineTo(0, 0);
    ctx.closePath();
    ctx.fill();
  }
  function text(ctx, s, size = 11) {
    ctx.font = `800 ${size}px "Noto Sans TC","Microsoft JhengHei",sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(s, 0, 0.5);
  }
  function eye(ctx, slash) {
    ctx.beginPath();
    ctx.moveTo(-9, 0);
    ctx.quadraticCurveTo(0, -9, 9, 0);
    ctx.quadraticCurveTo(0, 9, -9, 0);
    ctx.stroke();
    dot(ctx, 0, 0, 2.6);
    if (slash) {
      ctx.beginPath();
      ctx.moveTo(-8, 7); ctx.lineTo(8, -7);
      ctx.stroke();
    }
  }
  function footprints(ctx) {
    for (const [x, y, r] of [[-4, 4, -0.3], [3, -3, 0.3]]) {
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(r);
      ctx.beginPath();
      ctx.ellipse(0, 0, 2.6, 4, 0, 0, TAU);
      ctx.fill();
      dot(ctx, 0, -5.5, 1.3);
      ctx.restore();
    }
  }
  function chevrons(ctx, dir) {
    for (const o of [-4, 2]) {
      ctx.beginPath();
      if (dir === "right") { ctx.moveTo(o - 2, -6); ctx.lineTo(o + 4, 0); ctx.lineTo(o - 2, 6); }
      else if (dir === "up") { ctx.moveTo(-6, -o + 2); ctx.lineTo(0, -o - 4); ctx.lineTo(6, -o + 2); }
      else { ctx.moveTo(-6, o - 2); ctx.lineTo(0, o + 4); ctx.lineTo(6, o - 2); }
      ctx.stroke();
    }
  }
  function dice(ctx) {
    ctx.beginPath();
    ctx.roundRect(-7.5, -7.5, 15, 15, 3);
    ctx.stroke();
    for (const [x, y] of [[-3.5, -3.5], [3.5, 3.5], [0, 0], [3.5, -3.5], [-3.5, 3.5]]) dot(ctx, x, y, 1.4);
  }
  function card(ctx, x, y) {
    ctx.beginPath();
    ctx.roundRect(x - 4.5, y - 6.5, 9, 13, 1.5);
    ctx.fill();
  }
  function star(ctx, n, ro, ri) {
    SI().star(ctx, 0, 0, n, ro, ri);
    ctx.fill();
  }

  // ---- 狀態（顏色：負面偏紅紫、正面偏綠金藍）----
  const STATUS = {
    burning: ["#ff8a2a", (c) => SI().elementGlyph(c, "fire", 0, 0, 0.95, c.fillStyle)],
    frozen: ["#9fe6ff", (c) => SI().elementGlyph(c, "ice", 0, 0, 0.95, c.fillStyle)],
    poison: ["#8fdc4a", (c) => SI().elementGlyph(c, "poison", 0, 0, 0.95, c.fillStyle)],
    bleed: ["#ff5a5a", (c) => { drop(c, -3, -1, 0.75); drop(c, 4, 3, 0.6); }],
    root: ["#b8d07a", (c) => { c.beginPath(); c.moveTo(0, -8); c.lineTo(0, 4); c.moveTo(0, 4); c.lineTo(-6, 8); c.moveTo(0, 4); c.lineTo(6, 8); c.moveTo(0, 0); c.lineTo(-5, 3); c.stroke(); }],
    slow: ["#a8b4ff", (c) => { ring(c, 0, 0, 8); c.beginPath(); c.moveTo(0, -5); c.lineTo(0, 0); c.lineTo(3.5, 3); c.stroke(); }],
    stun: ["#ffe14d", (c) => { for (const [x, y] of [[-5, -3], [5, -3], [0, 5]]) { c.save(); c.translate(x, y); star(c, 5, 4, 1.7); c.restore(); } }],
    prone: ["#e0c49a", (c) => { dot(c, -7, 2, 2.6); c.fillRect(-4, 0, 12, 4.5); }],
    blinded: ["#c8c8d8", (c) => eye(c, true)],
    vulnerable: ["#ff6a6a", (c) => { shieldPath(c); c.stroke(); c.beginPath(); c.moveTo(-2, -8); c.lineTo(2, -2); c.lineTo(-2, 2); c.lineTo(1, 8); c.stroke(); }],
    weaken: ["#e09a9a", (c) => { c.beginPath(); c.moveTo(-6, -7); c.lineTo(4, 3); c.stroke(); arrow(c, 6, -6, 6, 6, 3.5); }],
    feared: ["#c890ff", (c) => text(c, "!", 15)],
    taunted: ["#ff7a4a", (c) => { ring(c, 0, 0, 7.5); ring(c, 0, 0, 3.5); dot(c, 0, 0, 1.4); }],
    silenced: ["#d0a0ff", (c) => { c.beginPath(); c.roundRect(-8, -7, 16, 11, 4); c.moveTo(-3, 4); c.lineTo(-5, 8); c.lineTo(1, 4); c.stroke(); c.beginPath(); c.moveTo(-4, -4); c.lineTo(4, 2); c.moveTo(4, -4); c.lineTo(-4, 2); c.stroke(); }],
    marked: ["#ff5a5a", (c) => { ring(c, 0, 0, 7); c.beginPath(); c.moveTo(-10, 0); c.lineTo(-4, 0); c.moveTo(4, 0); c.lineTo(10, 0); c.moveTo(0, -10); c.lineTo(0, -4); c.moveTo(0, 4); c.lineTo(0, 10); c.stroke(); }],
    concealed: ["#a0a8b8", (c) => { c.globalAlpha *= 0.55; person(c, 0, 0, 1.4); c.globalAlpha /= 0.55; c.beginPath(); c.arc(0, 0, 9, -2.4, -0.7); c.stroke(); }],
    hasted: ["#7dffb0", (c) => chevrons(c, "right")],
    empowered: ["#ffb03a", (c) => chevrons(c, "up")],
    guarded: ["#7fc0ff", (c) => { shieldPath(c); c.fill(); }],
    defending: ["#7fc0ff", (c) => { shieldPath(c); c.stroke(); }],
    regenerating: ["#7cf29a", (c) => { ring(c, 0, 0, 8.5); c.fillRect(-1.5, -5, 3, 10); c.fillRect(-5, -1.5, 10, 3); }],
    overwatch: ["#ffd04a", (c) => eye(c, false)],
  };
  function statusGlyph(ctx, id) {
    const s = STATUS[id];
    if (s) return s[1](ctx);
    if (id?.startsWith("stance_")) {
      ctx.beginPath();
      for (let i = 0; i < 6; i++) ctx.lineTo(Math.cos((i / 6) * TAU) * 8, Math.sin((i / 6) * TAU) * 8);
      ctx.closePath();
      ctx.stroke();
      return;
    }
    const zh = window.NAMES_ZH?.status?.[id] ?? "?";
    text(ctx, zh.slice(0, 1), 12);
  }
  const statusColor = (id) => STATUS[id]?.[0] ?? (id?.startsWith("stance_") ? "#ffd04a" : "#d8d8e0");

  // ---- 表面：落在地上的一滴，顏色是表面色 ----
  const SURFACE = { fire: "#ff7a1a", ice: "#cdeeff", oil: "#5a4a30", water: "#4a9af0", holy: "#ffe58a", darkness: "#8a5ad0", smoke: "#c0c0c8", poison: "#86d84a" };
  function surfaceGlyph(ctx, id) {
    const col = SURFACE[id] ?? "#c8c8c8";
    ctx.save();
    ctx.fillStyle = col;
    drop(ctx, 0, -2, 0.9);
    ctx.globalAlpha = 0.85;
    ctx.beginPath();
    ctx.ellipse(0, 7, 9, 2.6, 0, 0, TAU);
    ctx.fill();
    ctx.restore();
  }

  // ---- 效果原語 ----
  const EFFECT = {
    damage: ["#ffffff", (c) => star(c, 8, 9.5, 4)],
    heal: ["#7cf29a", (c) => { c.fillRect(-2.5, -8, 5, 16); c.fillRect(-8, -2.5, 16, 5); }],
    shield: ["#8fd0ff", (c) => { shieldPath(c); c.fill(); }],
    cleanse: ["#bfffe8", (c) => { star(c, 4, 9, 2.4); }],
    push: ["#ffffff", (c) => { dot(c, -6, 0, 3.4); arrow(c, -1, 0, 9, 0, 4.5); }],
    pull: ["#ffffff", (c) => { dot(c, -7, 0, 3.4); arrow(c, 9, 0, -1, 0, 4.5); }],
    knock_prone: ["#e0c49a", (c) => STATUS.prone[1](c)],
    teleport: ["#d8b8ff", (c) => { c.setLineDash([2.5, 2]); ring(c, -3, 2, 6); c.setLineDash([]); dot(c, 5, -4, 3.2); }],
    dash: ["#ffffff", (c) => { c.beginPath(); c.moveTo(-9, -4); c.lineTo(-1, -4); c.moveTo(-9, 4); c.lineTo(-1, 4); c.stroke(); arrow(c, -3, 0, 9, 0, 4.5); }],
    charge_through: ["#ffffff", (c) => { c.fillRect(-1.5, -9, 3, 18); arrow(c, -9, 0, 9, 0, 4.5); }],
    shadowstep: ["#c8a0ff", (c) => { c.beginPath(); c.arc(-2, 0, 7, 0.6, TAU - 0.6); c.stroke(); arrow(c, 0, 0, 9, 0, 4); }],
    leap: ["#ffffff", (c) => { c.beginPath(); c.moveTo(-9, 6); c.quadraticCurveTo(0, -14, 7, 4); c.stroke(); arrow(c, 5, 0, 8, 6, 4); }],
    swap: ["#ffffff", (c) => { arrow(c, -8, -3, 8, -3, 3.5); arrow(c, 8, 3, -8, 3, 3.5); }],
    apply_status: ["#ffffff", (c) => ring(c, 0, 0, 7)],
    create_surface: ["#ffffff", (c) => surfaceGlyph(c, null)],
    destroy_object: ["#e0c49a", (c) => { c.strokeRect(-7, -7, 14, 14); c.beginPath(); c.moveTo(-2, -7); c.lineTo(1, -1); c.lineTo(-2, 3); c.lineTo(1, 7); c.stroke(); }],
    create_obstacle: ["#d8c0a0", (c) => { for (let r = 0; r < 3; r++) for (let i = 0; i < 2; i++) c.fillRect(-8 + i * 8 + (r % 2) * 4 - (r % 2 && i === 1 ? 4 : 0), -7 + r * 5, 7, 4); }],
    raise_terrain: ["#e0c49a", (c) => { c.fillRect(-8, 2, 16, 6); arrow(c, 0, 1, 0, -9, 4); }],
    lower_terrain: ["#e0c49a", (c) => { c.fillRect(-8, 2, 16, 6); arrow(c, 0, -9, 0, 0, 4); }],
    intercept: ["#8fd0ff", (c) => { person(c, -3, 1, 1.1); c.save(); c.translate(5, 0); shieldPath(c, 0.6); c.fill(); c.restore(); }],
    add_stack: ["#ffd04a", (c) => { for (let i = 0; i < 3; i++) dot(c, -6 + i * 6, 3, 2.4); c.fillRect(-1, -9, 2, 7); c.fillRect(-3.5, -6.5, 7, 2); }],
    consume_stack: ["#ffd04a", (c) => { for (let i = 0; i < 3; i++) dot(c, -6 + i * 6, 3, 2.4); c.fillRect(-3.5, -6.5, 7, 2); }],
    consume_status: ["#ffb03a", (c) => { star(c, 6, 9, 4.5); c.save(); c.fillStyle = "#1a1420"; dot(c, 0, 0, 2.6); c.restore(); }],
    place_trap: ["#e0e0e0", (c) => { for (const [b, t] of [[-2, -8], [2, 8]]) { c.beginPath(); c.moveTo(-8, b); for (let i = 0; i < 4; i++) { c.lineTo(-8 + i * 4 + 2, t * 0.6 + b * 0.4); c.lineTo(-8 + (i + 1) * 4, b); } c.closePath(); c.fill(); } }],
    grant_ap: ["#ffe14d", (c) => { ring(c, -2, 0, 6.5); text(c, "+", 12); }],
    reset_cooldown: ["#a8e0ff", (c) => { c.beginPath(); c.arc(0, 0, 7.5, -1.2, 4.2); c.stroke(); arrow(c, -6.5, -4, -3.5, -8, 3.5); }],
    cheat_death: ["#ff7a7a", (c) => { heart(c); c.fill(); }],
    redirect_damage: ["#ffffff", (c) => { c.beginPath(); c.moveTo(-8, 7); c.lineTo(0, -1); c.stroke(); arrow(c, 0, -1, 8, 7, 4); }],
    copy_skill: ["#d8c8ff", (c) => { c.globalAlpha *= 0.6; card(c, -3, -2); c.globalAlpha /= 0.6; card(c, 3, 2); }],
    extra_reaction: ["#8fd0ff", (c) => { shieldPath(c, 0.9); c.stroke(); SI().elementGlyph(c, "lightning", 0, 0, 0.55, c.fillStyle); }],
    hurl_object: ["#e0b080", (c) => { c.fillRect(-9, 1, 7, 7); c.beginPath(); c.moveTo(-5, 0); c.quadraticCurveTo(0, -12, 7, 2); c.stroke(); arrow(c, 5, -2, 8, 4, 3.5); }],
    topple: ["#c8c0b0", (c) => { c.save(); c.rotate(0.6); c.fillRect(-2.5, -9, 5, 16); c.restore(); c.fillRect(-9, 7, 18, 2); }],
    restore_resource: ["#c89cff", (c) => { c.beginPath(); c.moveTo(-2, -8); c.lineTo(4, -2); c.lineTo(-2, 4); c.lineTo(-8, -2); c.closePath(); c.fill(); c.fillRect(4, 2, 2, 7); c.fillRect(1.5, 4.5, 7, 2); }],
    steal_buff: ["#c8a0ff", (c) => { c.beginPath(); c.moveTo(-8, 6); c.lineTo(-8, -2); c.quadraticCurveTo(-8, -8, -2, -8); c.lineTo(6, -8); c.stroke(); arrow(c, 0, 0, -8, 6, 0.01); chevrons(c, "up"); }],
    dispel: ["#d8d0ff", (c) => { c.beginPath(); c.moveTo(-7, -7); c.lineTo(7, 7); c.moveTo(7, -7); c.lineTo(-7, 7); c.stroke(); }],
    reveal: ["#ffffff", (c) => eye(c, false)],
    revive: ["#ffd75e", (c) => { heart(c); c.fill(); c.save(); c.fillStyle = "#1a1420"; c.fillRect(-1.2, -4, 2.4, 8); c.fillRect(-4, -1.2, 8, 2.4); c.restore(); }],
    delayed_damage: ["#ffb03a", (c) => { c.save(); c.scale(0.75, 0.75); c.translate(-4, 0); hourglass(c); c.restore(); c.save(); c.translate(5, -3); star(c, 6, 5, 2.4); c.restore(); }],
    summon: ["#8ff0e2", (c) => { person(c, -2, 1, 1.25); c.fillRect(5, -9, 2, 7); c.fillRect(2.5, -6.5, 7, 2); }],
    zone: ["#ffd04a", (c) => { c.setLineDash([3, 2]); ring(c, 0, 0, 8); c.setLineDash([]); dot(c, 0, 0, 2.5); }],
    rule_change: ["#ffd75e", (c) => { c.beginPath(); c.roundRect(-7, -8, 14, 16, 2); c.stroke(); c.fillRect(-4, -4, 8, 1.6); c.fillRect(-4, 0, 8, 1.6); c.fillRect(-4, 4, 5, 1.6); }],
    gamble: ["#ffffff", (c) => dice(c)],
    grant_skill: ["#d8c8ff", (c) => { card(c, -2, 1); c.fillRect(5, -9, 2, 7); c.fillRect(2.5, -6.5, 7, 2); }],
  };
  EFFECT.teleport_target = EFFECT.swap;
  EFFECT.swap_any = EFFECT.swap;

  /** 效果原語 → 部件（狀態與表面用各自的圖示）。 */
  function effectPart(e) {
    const NZ = window.NAMES_ZH ?? {};
    if (e.type === "apply_status" && e.status) {
      return { cat: "effect", key: `status:${e.status}`, color: statusColor(e.status), draw: (c) => statusGlyph(c, e.status), label: NZ.status?.[e.status] ?? e.status, note: "附加狀態" };
    }
    if (e.type === "create_surface" && e.surface) {
      return { cat: "effect", key: `surface:${e.surface}`, color: SURFACE[e.surface] ?? "#ccc", draw: (c) => surfaceGlyph(c, e.surface), label: `${NZ.surface?.[e.surface] ?? e.surface}表面`, note: "產生表面" };
    }
    const g = EFFECT[e.type];
    return { cat: "effect", key: e.type, color: g?.[0] ?? "#d8d8e0", draw: g ? g[1] : (c) => text(c, "?", 13), label: NZ.primitive?.[e.type] ?? e.type, note: "效果原語" };
  }

  // ---- 條件 ----
  const COND = {
    height_advantage: (c) => { c.beginPath(); c.moveTo(-9, 8); c.lineTo(0, -4); c.lineTo(9, 8); c.closePath(); c.fill(); dot(c, 0, -7.5, 2.6); },
    target_hp_below: (c) => { heart(c); c.stroke(); c.save(); c.beginPath(); c.rect(-10, 1, 20, 10); c.clip(); heart(c); c.fill(); c.restore(); },
    self_hp_below: (c) => { heart(c, 0.85); c.stroke(); c.save(); c.beginPath(); c.rect(-10, 1, 20, 10); c.clip(); heart(c, 0.85); c.fill(); c.restore(); person(c, 7, -5, 0.5); },
    target_has_status: (c) => { ring(c, -2, 1, 6); text(c, "?", 9); },
    target_on_surface: (c) => { drop(c, -2, 0, 0.75); c.save(); c.translate(6, -5); text(c, "?", 9); c.restore(); },
    from_behind: (c) => { person(c, 3, 0, 1.1); arrow(c, -9, 0, -3, 0, 3.5); },
    flanked: (c) => { dot(c, 0, 0, 3); arrow(c, -9, 0, -4.5, 0, 3.5); arrow(c, 9, 0, 4.5, 0, 3.5); },
    target_isolated: (c) => { c.setLineDash([2.5, 2]); ring(c, 0, 0, 8); c.setLineDash([]); dot(c, 0, 0, 3); },
    moved_this_turn: (c) => footprints(c),
    first_round: (c) => text(c, "1", 14),
    cast_tag_this_turn: (c) => { card(c, -3, 0); arrow(c, 1, 0, 9, 0, 3.5); },
    self_concealed: (c) => STATUS.concealed[1](c),
    adjacent_ally: (c) => { person(c, -4, 1, 0.85); person(c, 4, 1, 0.85); },
  };
  function conditionPart(id, statusId) {
    if (!id) return null;
    const NZ = window.NAMES_ZH ?? {};
    let draw = COND[id] ?? ((c) => text(c, "?", 13));
    if (id === "target_has_status" && statusId) draw = (c) => { c.save(); c.scale(0.85, 0.85); statusGlyph(c, statusId); c.restore(); c.save(); c.translate(6.5, 5.5); text(c, "?", 8); c.restore(); };
    return { cat: "condition", key: id, color: "#ffe9a8", draw, label: NZ.condition?.[id] ?? id, note: "條件" };
  }

  // ---- 代價 ----
  function costParts(skill) {
    const out = [];
    const c = skill.cost ?? {};
    if (c.source) out.push({ cat: "cost", key: "source", color: "#c89cff", draw: (x) => { x.beginPath(); x.moveTo(0, -9); x.lineTo(7, 0); x.lineTo(0, 9); x.lineTo(-7, 0); x.closePath(); x.fill(); }, label: `源力 ${c.source}`, note: "特殊代價" });
    if (c.gamble) out.push({ cat: "cost", key: "gamble", color: "#ffffff", draw: (x) => dice(x), label: "賭注", note: "特殊代價" });
    if (c.on_miss || c.self_status) out.push({ cat: "cost", key: "self", color: "#ff6a6a", draw: (x) => { heart(x); x.fill(); x.save(); x.strokeStyle = "#1a1420"; x.lineWidth = 1.6; x.beginPath(); x.moveTo(-1, -4); x.lineTo(2, 0); x.lineTo(-1, 3); x.stroke(); x.restore(); }, label: c.on_miss ? "失手自傷" : "自身代價", note: "特殊代價" });
    if (c.stacks) out.push({ cat: "cost", key: "stacks", color: "#ffd04a", draw: EFFECT.consume_stack[1], label: `消耗 ${c.stacks} 層`, note: "特殊代價" });
    if (c.uses_per_battle || skill.activation === "battle") out.push({ cat: "cost", key: "once", color: "#ffd75e", draw: (x) => { ring(x, 0, 0, 8.5); text(x, "1", 11); }, label: "每場一次", note: "特殊代價" });
    if (skill.activation === "timed" || skill.followup?.when === "delayed") out.push({ cat: "cost", key: "delay", color: "#a8e0ff", draw: hourglass, label: "延遲", note: "特殊代價" });
    return out;
  }

  // ---- 觸發（被動、反應的主圖）----
  const TRIG = {
    on_hit: EFFECT.damage[1],
    on_kill: (c) => { dot(c, 0, -2, 7); c.fillRect(-4, 2, 8, 6); c.save(); c.fillStyle = "#1a1420"; dot(c, -2.8, -2, 2); dot(c, 2.8, -2, 2); c.restore(); },
    on_crit: (c) => { star(c, 4, 10, 2.6); text(c, "", 1); },
    on_natural_20: (c) => { c.beginPath(); for (let i = 0; i < 6; i++) c.lineTo(Math.cos((i / 6) * TAU - Math.PI / 2) * 9.5, Math.sin((i / 6) * TAU - Math.PI / 2) * 9.5); c.closePath(); c.stroke(); text(c, "20", 8); },
    on_move: footprints,
    on_damaged: STATUS.vulnerable[1],
    on_status_applied: (c) => { ring(c, 0, 0, 8); dot(c, 0, 0, 3); },
    on_cast_tag: (c) => card(c, 0, 0),
    on_collision: (c) => { arrow(c, -9, 0, -2, 0, 3.5); arrow(c, 9, 0, 2, 0, 3.5); },
    on_turn_start: (c) => { c.beginPath(); c.arc(0, 4, 7, Math.PI, 0); c.fill(); c.fillRect(-10, 4, 20, 1.8); arrow(c, 0, -2, 0, -9, 3); },
    on_turn_end: (c) => { c.beginPath(); c.arc(0, 4, 7, Math.PI, 0); c.fill(); c.fillRect(-10, 4, 20, 1.8); arrow(c, 0, -10, 0, -3, 3); },
    on_enter_surface: (c) => { drop(c, 0, 0, 0.9); },
    every_n_hits: (c) => { for (let i = 0; i < 3; i++) dot(c, -6 + i * 6, 0, 2.6); },
    enemy_enters_adjacent: (c) => { ring(c, 2, 0, 6); arrow(c, -10, 0, -3, 0, 3.5); },
    enemy_leaves_adjacent: (c) => { ring(c, -2, 0, 6); arrow(c, 2, 0, 10, 0, 3.5); },
    hit_by_spell: (c) => { shieldPath(c); c.stroke(); c.save(); c.scale(0.5, 0.5); star(c, 5, 9, 4); c.restore(); },
    hit_by_attack: (c) => { shieldPath(c); c.stroke(); c.beginPath(); c.moveTo(-9, -9); c.lineTo(-2, -2); c.stroke(); },
    hit_by_melee: (c) => { shieldPath(c); c.stroke(); c.beginPath(); c.moveTo(-9, -9); c.lineTo(-2, -2); c.moveTo(-9, -4); c.lineTo(-5, -8); c.stroke(); },
    ally_targeted: (c) => { person(c, 0, 1, 1.1); c.save(); c.globalAlpha *= 0.9; STATUS.marked[1](c); c.restore(); },
    ally_downed: (c) => STATUS.prone[1](c),
    ally_hit_adjacent: (c) => { person(c, -4, 1, 0.9); c.save(); c.translate(5, -3); star(c, 6, 5, 2.2); c.restore(); },
  };
  function triggerPart(id, isReaction) {
    if (!id) return null;
    const NZ = window.NAMES_ZH ?? {};
    const REACT_ZH = {
      enemy_enters_adjacent: "敵人靠近時", enemy_leaves_adjacent: "敵人離開時", hit_by_spell: "被法術擊中時", hit_by_attack: "被攻擊時",
      hit_by_melee: "被近戰擊中時", ally_targeted: "隊友被瞄準時", ally_downed: "隊友倒下時", ally_hit_adjacent: "身旁隊友受擊時",
    };
    return { cat: "trigger", key: id, color: "#ffffff", draw: TRIG[id] ?? ((c) => text(c, "?", 13)), label: (isReaction ? REACT_ZH[id] : NZ.trigger?.[id]) ?? id, note: isReaction ? "反應時機" : "觸發時機" };
  }

  // ---- 複合技能的接續記號 ----
  const LINK = {
    after_action: ["接著做", (c) => arrow(c, -7, 0, 7, 0, 5)],
    on_hit: ["命中才觸發", (c) => { c.beginPath(); c.moveTo(-7, 0); c.lineTo(-2, 5); c.lineTo(7, -6); c.stroke(); }],
    on_kill: ["擊殺才觸發", TRIG.on_kill],
    delayed: ["延遲觸發", hourglass],
    after_move: ["移動後觸發", (c) => { c.save(); c.scale(0.85, 0.85); footprints(c); c.restore(); }],
    after_gather: ["聚集後觸發", (c) => { arrow(c, -9, 0, -3, 0, 3); arrow(c, 9, 0, 3, 0, 3); }],
  };
  function linkPart(when) {
    const l = LINK[when] ?? LINK.after_action;
    return { cat: "link", key: when, color: "#ffffff", draw: l[1], label: l[0], note: "接續" };
  }

  // ---- 修正：被改造的對象、改變的內容 ----
  const TAG_TARGET = { push: "push", heal: "heal", control: "apply_status", ranged: "dash", shout: "damage", area: "damage" };
  function modifierTargetPart(applies) {
    const a = applies ?? {};
    let draw = EFFECT.damage[1];
    let label = "所有技能";
    if (a.all_skills) { draw = (c) => { c.globalAlpha *= 0.6; card(c, -3, -2); c.globalAlpha /= 0.6; card(c, 3, 2); }; label = "所有技能"; }
    else if (a.all_attacks || a.actions?.includes("attack")) { draw = (c) => { c.beginPath(); c.moveTo(-7, 7); c.lineTo(7, -7); c.moveTo(-7, 2); c.lineTo(-2, 7); c.stroke(); }; label = a.all_attacks ? "所有攻擊" : "普通攻擊"; }
    else if (a.skill_tags?.length) {
      const t = a.skill_tags[0];
      draw = t === "ranged" ? (c) => { c.beginPath(); c.arc(-4, 0, 9, -1.1, 1.1); c.stroke(); arrow(c, -6, 0, 9, 0, 3.5); } : (EFFECT[TAG_TARGET[t]] ?? EFFECT.damage)[1];
      const TAG_ZH = { push: "推擊", heal: "治療", control: "控制", ranged: "遠程", shout: "吼叫", area: "範圍" };
      label = `${a.skill_tags.map((x) => TAG_ZH[x] ?? x).join("／")}技能`;
    }
    return { cat: "target", key: "target", color: "#ffffff", draw, label, note: "被改造的對象" };
  }
  function modifierChangeParts(change) {
    const out = [];
    for (const [k, v] of Object.entries(change ?? {})) {
      let draw;
      let label;
      let color = "#ffe14d";
      if (k === "add_element") { color = SI().EL[v]?.accent ?? "#fff"; draw = (c) => { SI().elementGlyph(c, v, -1, 1, 0.75, color); c.save(); c.fillStyle = "#ffffff"; c.fillRect(5, -9, 2, 7); c.fillRect(2.5, -6.5, 7, 2); c.restore(); }; label = `加上${SI().EL[v]?.name ?? v}元素`; }
      else if (k === "damage_permille") { draw = (c) => { c.save(); c.translate(-2, 2); c.scale(0.7, 0.7); star(c, 8, 9.5, 4); c.restore(); arrow(c, 6, 6, 6, -8, 3.5); }; label = `傷害 ${v > 0 ? "+" : ""}${v / 10}%`; }
      else if (k === "cooldown_delta") { draw = (c) => { ring(c, -2, 1, 7); c.beginPath(); c.moveTo(-2, -3); c.lineTo(-2, 1); c.lineTo(1, 3); c.stroke(); c.fillRect(4, -9, 6, 2); }; label = `冷卻 ${v}`; }
      else if (k === "area_delta") { draw = (c) => { arrow(c, -2, -2, -9, -9, 3.5); arrow(c, 2, 2, 9, 9, 3.5); c.strokeRect(-4, -4, 8, 8); }; label = `範圍 +${v}`; }
      else if (k === "push_distance_delta") { draw = (c) => { EFFECT.push[1](c); }; label = `推距 +${v}`; }
      else if (k === "ap_delta") { draw = (c) => { ring(c, -2, 0, 6.5); c.fillRect(4, -9, 6, 2); }; label = `AP ${v}`; }
      else if (k === "shape_to") { draw = (c) => { c.beginPath(); c.moveTo(-9, 6); c.lineTo(9, -6); c.stroke(); }; label = `形狀改為${window.NAMES_ZH?.shape?.[v] ?? v}`; }
      else if (k === "allow_self_target") { draw = (c) => { person(c, 0, 1, 1.2); ring(c, 0, 0, 9.5); }; label = "可以對自己用"; }
      else if (k === "grant_pierce") { draw = (c) => { c.fillRect(-1.5, -9, 3, 18); arrow(c, -9, 0, 9, 0, 4); }; label = "穿透"; }
      else { draw = (c) => text(c, "?", 13); label = k; }
      out.push({ cat: "change", key: k, color, draw, label, note: "改變的內容" });
    }
    return out;
  }

  /** 在 (x, y) 畫一個部件小圓片：深色底＋外圈＋圖示。 */
  function chip(ctx, part, x, y, r, opts = {}) {
    ctx.save();
    ctx.translate(x, y);
    ctx.fillStyle = opts.bg ?? "rgba(10,12,18,0.85)";
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, TAU);
    ctx.fill();
    if (opts.ring !== false) {
      ctx.strokeStyle = opts.ring ?? "rgba(255,255,255,0.35)";
      ctx.lineWidth = Math.max(1, r * 0.12);
      ctx.stroke();
    }
    const k = (r * 0.78) / 10;
    ctx.scale(k, k);
    ctx.fillStyle = part.color;
    ctx.strokeStyle = part.color;
    ctx.lineWidth = 2.2;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    part.draw(ctx);
    ctx.restore();
  }

  return { effectPart, conditionPart, costParts, triggerPart, linkPart, modifierTargetPart, modifierChangeParts, statusGlyph, surfaceGlyph, chip };
})();
