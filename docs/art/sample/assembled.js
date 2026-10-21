// 組裝式技能圖示（美術樣張，玩法 #21）：圖示本身就看得出技能由哪些部件組成。
// 位置：元素＝底色與紋理、形狀＝主圖、效果原語＝底部一排、條件＝左下、骨架＝右下、特殊代價＝右上、
//       技能類型＝外框形狀、稀有度＝外框顏色、複合技能＝斜切兩半＋切線上的接續記號、修正＝主圖換成被改造的對象。
// 小圖（技能列 28–40px）只畫元素、形狀、核心效果與外框。`partsOf` 是唯一的拆解函式，圖示、組裝列、工坊都用它。
window.AssembledIcon = (() => {
  const TAU = Math.PI * 2;
  const SI = window.SkillIcon;
  const P = window.Parts;
  const KIND_ZH = { active: "主動", reaction: "反應", passive: "被動", stance: "姿態", modifier: "修正" };
  const RARITY_ZH = { common: "普通", rare: "稀有", epic: "史詩", legendary: "傳說" };
  const NEUTRAL = { name: "（未選）", accent: "#c8ccd4", dark: "#23262d", light: "#4a4f5a" };

  function palette(el) {
    if (el === undefined) return NEUTRAL;
    return SI.EL[el] ?? SI.EL.default;
  }

  /** 把一個技能拆成部件（資料 → 部件清單）。 */
  function partsOf(skill) {
    const el = skill.elements === undefined ? undefined : skill.elements[0] ?? null;
    const el2 = skill.elements?.[1];
    const segs = [{ skeleton: skill.skeleton, shape: skill.shape, range: skill.range, weapon_req: skill.weapon_req, el, effects: (skill.effects ?? []).map(P.effectPart) }];
    if (skill.followup) {
      const f = skill.followup;
      segs.push({ skeleton: f.skeleton, shape: f.shape, range: f.range, weapon_req: skill.weapon_req, el: f.elements?.[0] ?? el, effects: (f.effects ?? []).map(P.effectPart) });
    }
    const effCond = [...(skill.effects ?? []), ...(skill.followup?.effects ?? [])].find((e) => e.condition)?.condition;
    const condition = P.conditionPart(skill.condition ?? effCond, skill.conditionStatus);
    const trigger = skill.kind === "reaction" ? P.triggerPart(skill.reaction, true) : skill.kind === "passive" ? P.triggerPart(skill.trigger, false) : null;
    const mod = skill.modifiers?.length ? { target: P.modifierTargetPart(skill.modifiers[0].applies_to), changes: skill.modifiers.flatMap((m) => P.modifierChangeParts(m.change)) } : null;
    // 效果列：去重後，核心效果（第一個「不是單純傷害」的效果；沒有就是傷害）放第一個
    let effects = [];
    const seen = new Set();
    for (const s of segs) for (const e of s.effects) if (!seen.has(e.key)) { seen.add(e.key); effects.push(e); }
    if (mod) effects = mod.changes;
    const coreIdx = effects.findIndex((e) => e.key !== "damage");
    const core = effects.length === 0 ? null : effects[coreIdx === -1 ? 0 : coreIdx];
    if (core) effects = [core, ...effects.filter((e) => e !== core)];
    return {
      kind: skill.kind ?? "active", rarity: skill.rarity, el, el2, segs,
      link: skill.followup ? P.linkPart(skill.followup.when) : null,
      trigger, mod, condition, costs: skill.kind === undefined ? [] : P.costParts(skill),
      effects: effects.slice(0, 4), core,
    };
  }

  // ---- 外框形狀（技能類型）----
  function framePath(ctx, kind, inset = 0) {
    const i = inset;
    ctx.beginPath();
    switch (kind) {
      case "reaction":
        ctx.moveTo(8 + i, 6 + i);
        ctx.lineTo(92 - i, 6 + i);
        ctx.lineTo(92 - i, 50);
        ctx.quadraticCurveTo(92 - i, 82 - i, 50, 96 - i * 1.4);
        ctx.quadraticCurveTo(8 + i, 82 - i, 8 + i, 50);
        ctx.closePath();
        break;
      case "passive":
        ctx.arc(50, 50, 46 - i, 0, TAU);
        break;
      case "stance":
        for (let k = 0; k < 6; k++) {
          const a = (k / 6) * TAU;
          ctx.lineTo(50 + Math.cos(a) * (48 - i), 50 + Math.sin(a) * (48 - i));
        }
        ctx.closePath();
        break;
      case "modifier": {
        const teeth = 12;
        for (let k = 0; k < teeth * 4; k++) {
          const a = (k / (teeth * 4)) * TAU;
          const r = (k % 4 < 2 ? 48 : 43) - i;
          ctx.lineTo(50 + Math.cos(a) * r, 50 + Math.sin(a) * r);
        }
        ctx.closePath();
        break;
      }
      default:
        ctx.roundRect(4 + i, 4 + i, 92 - i * 2, 92 - i * 2, 14);
    }
  }

  function background(ctx, el) {
    const Pa = palette(el);
    const bg = ctx.createRadialGradient(38, 30, 4, 50, 50, 78);
    bg.addColorStop(0, Pa.light);
    bg.addColorStop(1, Pa.dark);
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, 100, 100);
    if (el !== undefined) SI.texture(ctx, el ?? "default", Pa);
  }

  function bigGlyph(ctx, part, cx, cy, k) {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(k, k);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    // 陰影
    ctx.save();
    ctx.translate(0.8, 1);
    ctx.fillStyle = "rgba(0,0,0,0.45)";
    ctx.strokeStyle = "rgba(0,0,0,0.45)";
    ctx.lineWidth = 2.4;
    part.draw(ctx);
    ctx.restore();
    ctx.fillStyle = "#ffffff";
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2.2;
    part.draw(ctx);
    ctx.restore();
  }

  function segMotif(ctx, seg, cx, cy, k) {
    if (!seg.shape) {
      ctx.save();
      ctx.setLineDash([6, 5]);
      ctx.strokeStyle = "rgba(255,255,255,0.45)";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(cx, cy, 22 * k, 0, TAU);
      ctx.stroke();
      ctx.restore();
      return;
    }
    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(k, k);
    ctx.translate(-50, -50);
    const el = seg.el === undefined ? "default" : seg.el ?? "default";
    SI.motif(ctx, seg, el, palette(seg.el));
    ctx.restore();
  }

  function mainArt(ctx, parts, small) {
    const ky = small ? 50 : 44;
    const k = small ? 1 : 0.8;
    if (parts.mod) {
      bigGlyph(ctx, parts.mod.target, 50, ky, small ? 3 : 2.4);
    } else if (parts.trigger) {
      bigGlyph(ctx, parts.trigger, 50, ky, small ? 3 : 2.4);
    } else if (parts.segs.length > 1) {
      // 複合：斜切兩半，左上第一段、右下第二段
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(0, 0); ctx.lineTo(100, 0); ctx.lineTo(0, 100);
      ctx.closePath();
      ctx.clip();
      segMotif(ctx, parts.segs[0], 30, 30, 0.52);
      ctx.restore();
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(100, 0); ctx.lineTo(100, 100); ctx.lineTo(0, 100);
      ctx.closePath();
      ctx.clip();
      if (parts.segs[1].el !== parts.segs[0].el) background(ctx, parts.segs[1].el);
      else {
        ctx.fillStyle = "rgba(0,0,0,0.22)";
        ctx.fillRect(0, 0, 100, 100);
      }
      segMotif(ctx, parts.segs[1], small ? 68 : 68, small ? 68 : 62, 0.52);
      ctx.restore();
      ctx.strokeStyle = "rgba(0,0,0,0.6)";
      ctx.lineWidth = 5;
      ctx.beginPath();
      ctx.moveTo(104, -4); ctx.lineTo(-4, 104);
      ctx.stroke();
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2.2;
      ctx.stroke();
      if (parts.link) P.chip(ctx, parts.link, 50, 50, small ? 13 : 10.5, { ring: "#ffffff" });
    } else {
      segMotif(ctx, parts.segs[0], 50, ky + (small ? 0 : 2), k);
    }
  }

  function elementChip(ctx, el, x, y, r) {
    ctx.fillStyle = "rgba(8,10,16,0.8)";
    ctx.beginPath();
    ctx.arc(x, y, r, 0, TAU);
    ctx.fill();
    SI.elementGlyph(ctx, el ?? "default", x, y, (r / 12) * 0.8, palette(el).accent);
  }

  /** 畫一個組裝式圖示。size ≤ 40 時自動用小圖（只畫元素、形狀、核心效果、外框）。 */
  function draw(canvas, skill, size = 96, opts = {}) {
    const dpr = 2;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = `${size}px`;
    canvas.style.height = `${size}px`;
    const ctx = canvas.getContext("2d");
    ctx.scale((size * dpr) / 100, (size * dpr) / 100);
    const parts = partsOf(skill);
    const small = opts.small ?? size <= 40;
    const rarity = SI.RARITY[parts.rarity] ?? "#6a6f7a";
    // ① 外框內：底色、紋理、主圖
    ctx.save();
    framePath(ctx, parts.kind);
    ctx.clip();
    background(ctx, parts.el);
    if (parts.el2) {
      // 第二元素：斜向色帶
      ctx.save();
      ctx.globalAlpha = 0.55;
      ctx.fillStyle = palette(parts.el2).light;
      ctx.beginPath();
      ctx.moveTo(62, 0); ctx.lineTo(80, 0); ctx.lineTo(0, 80); ctx.lineTo(0, 62);
      ctx.closePath();
      ctx.fill();
      ctx.restore();
    }
    mainArt(ctx, parts, small);
    ctx.restore();
    // ② 外框（形狀＝技能類型、顏色＝稀有度）
    framePath(ctx, parts.kind, 1);
    ctx.lineWidth = parts.rarity === "legendary" ? 5 : 3.5;
    ctx.strokeStyle = rarity;
    ctx.stroke();
    if (parts.rarity === "legendary" || parts.rarity === "epic") {
      framePath(ctx, parts.kind, 6);
      ctx.lineWidth = 1;
      ctx.globalAlpha = 0.6;
      ctx.stroke();
      ctx.globalAlpha = 1;
    }
    if (small) {
      if (parts.core) P.chip(ctx, parts.core, 79, 79, 18, { ring: rarity });
      return;
    }
    // ③ 角落：左上元素、右上代價、左下條件、右下骨架
    if (parts.el !== undefined) elementChip(ctx, parts.el, 15, 15, 11);
    if (parts.costs.length) {
      P.chip(ctx, parts.costs[0], 85, 15, 11, { ring: parts.costs[0].color });
      if (parts.costs.length > 1) P.chip(ctx, parts.costs[1], 85, 36, 8, { ring: parts.costs[1].color });
    }
    if (parts.condition) P.chip(ctx, parts.condition, 14, 86, 11, { ring: "#ffe9a8" });
    if (parts.segs[0].skeleton) {
      ctx.fillStyle = "rgba(8,10,16,0.88)";
      ctx.beginPath();
      ctx.arc(86, 86, 11, 0, TAU);
      ctx.fill();
      ctx.strokeStyle = rarity;
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.save();
      ctx.translate(86, 86);
      ctx.scale(0.85, 0.85);
      SI.skeletonGlyph(ctx, parts.segs[0].skeleton, 0, 0);
      ctx.restore();
    }
    // ④ 底部效果列：核心大、附帶小
    const list = parts.effects;
    if (list.length) {
      const L = parts.condition ? 26 : 5;
      const R = 75;
      const rc = 11.5;
      let ro = 8.5;
      const gap = 1.5;
      let total = rc * 2 + (list.length - 1) * (ro * 2 + gap);
      if (total > R - L) {
        ro = Math.max(4.5, ((R - L - rc * 2) / (list.length - 1) - gap) / 2);
        total = rc * 2 + (list.length - 1) * (ro * 2 + gap);
      }
      let x = (L + R) / 2 - total / 2;
      const y = 85;
      list.forEach((p, i) => {
        const r = i === 0 ? rc : ro;
        P.chip(ctx, p, x + r, y + (i === 0 ? 0 : 2), r, { ring: i === 0 ? p.color : "rgba(255,255,255,0.3)" });
        x += r * 2 + gap;
      });
    }
  }

  // ---- 組裝列：每個部件一個小方塊 ----
  function tileCanvas(drawFn, px = 44) {
    const c = document.createElement("canvas");
    c.width = px * 2;
    c.height = px * 2;
    c.style.width = `${px}px`;
    c.style.height = `${px}px`;
    const ctx = c.getContext("2d");
    ctx.scale((px * 2) / 100, (px * 2) / 100);
    drawFn(ctx);
    return c;
  }
  function tiles(skill) {
    const parts = partsOf(skill);
    const out = [];
    const add = (cat, label, drawFn, tip) => out.push({ cat, label, drawFn, tip });
    add("類型", KIND_ZH[parts.kind] ?? parts.kind, (ctx) => {
      ctx.save();
      ctx.translate(14, 14);
      ctx.scale(0.72, 0.72);
      framePath(ctx, parts.kind);
      ctx.fillStyle = "#3a3f4a";
      ctx.fill();
      ctx.lineWidth = 5;
      ctx.strokeStyle = SI.RARITY[parts.rarity] ?? "#9aa0a6";
      ctx.stroke();
      ctx.restore();
    }, "外框形狀：主動方形、反應盾形、被動圓形、姿態六角、修正齒輪");
    const segTiles = (seg, n) => {
      if (seg.skeleton) add(n ? "骨架（第二段）" : "骨架", SI.SKELETON_NAME[seg.skeleton] ?? seg.skeleton, (ctx) => {
        ctx.fillStyle = "#14161c";
        ctx.beginPath();
        ctx.arc(50, 50, 40, 0, TAU);
        ctx.fill();
        ctx.save();
        ctx.translate(50, 50);
        ctx.scale(3, 3);
        SI.skeletonGlyph(ctx, seg.skeleton, 0, 0);
        ctx.restore();
      }, "右下徽章");
      if (n === 0 || seg.el !== parts.segs[0].el) add("元素", palette(seg.el).name, (ctx) => {
        background(ctx, seg.el);
        SI.elementGlyph(ctx, seg.el ?? "default", 50, 50, 2.6, "#ffffff");
      }, "底色與紋理");
      if (seg.shape) add("形狀", window.NAMES_ZH?.shape?.[seg.shape] ?? seg.shape, (ctx) => {
        background(ctx, seg.el);
        segMotif(ctx, seg, 50, 50, 0.95);
      }, "中央主圖");
      for (const e of seg.effects.filter((x, i, a) => a.findIndex((y) => y.key === x.key) === i)) {
        add(e === parts.core ? "效果（核心）" : "效果", e.label, (ctx) => P.chip(ctx, e, 50, 50, 42, { ring: e.color }), e.note);
      }
    };
    if (parts.trigger) add("觸發", parts.trigger.label, (ctx) => P.chip(ctx, parts.trigger, 50, 50, 42, { ring: "#ffffff" }), parts.trigger.note);
    if (parts.mod) {
      add("改造對象", parts.mod.target.label, (ctx) => P.chip(ctx, parts.mod.target, 50, 50, 42, { ring: "#ffffff" }), "主圖");
      for (const c of parts.mod.changes) add("改變內容", c.label, (ctx) => P.chip(ctx, c, 50, 50, 42, { ring: c.color }), "底部符號");
    } else {
      segTiles(parts.segs[0], 0);
      if (parts.link) {
        add("接續", parts.link.label, (ctx) => P.chip(ctx, parts.link, 50, 50, 42, { ring: "#ffffff" }), "切線上的記號");
        segTiles(parts.segs[1], 1);
      }
    }
    if (parts.condition) add("條件", parts.condition.label, (ctx) => P.chip(ctx, parts.condition, 50, 50, 42, { ring: "#ffe9a8" }), "左下角");
    for (const c of parts.costs) add("代價", c.label, (ctx) => P.chip(ctx, c, 50, 50, 42, { ring: c.color }), "右上角");
    if (parts.rarity) add("稀有度", RARITY_ZH[parts.rarity] ?? parts.rarity, (ctx) => {
      ctx.fillStyle = SI.RARITY[parts.rarity];
      ctx.beginPath();
      ctx.moveTo(50, 12); ctx.lineTo(82, 42); ctx.lineTo(50, 88); ctx.lineTo(18, 42);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = "rgba(255,255,255,0.35)";
      ctx.beginPath();
      ctx.moveTo(50, 12); ctx.lineTo(82, 42); ctx.lineTo(50, 42);
      ctx.closePath();
      ctx.fill();
    }, "外框顏色");
    return out;
  }
  /** 技能卡上方的組裝列（DOM）。 */
  function assemblyRow(container, skill, px = 44) {
    const row = document.createElement("div");
    row.className = "asm";
    for (const t of tiles(skill)) {
      const cell = document.createElement("div");
      cell.className = `asm-tile asm-${t.cat === "接續" ? "link" : "part"}`;
      cell.title = `${t.cat}：${t.label}（${t.tip}）`;
      cell.innerHTML = `<div class="asm-cat">${t.cat}</div>`;
      cell.appendChild(tileCanvas(t.drawFn, px));
      cell.insertAdjacentHTML("beforeend", `<div class="asm-label">${t.label}</div>`);
      row.appendChild(cell);
    }
    container.appendChild(row);
    return row;
  }

  return { draw, partsOf, assemblyRow, tiles, tileCanvas, framePath, KIND_ZH, RARITY_ZH };
})();
