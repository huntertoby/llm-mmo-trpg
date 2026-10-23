// 側面畫法的比較樣張（2026-10-24；使用者：「所有側面完全都不像側面 重新設計側面 演示方式 多給我幾個樣本挑」）。
// 一個可調參數的側面畫法：bodyTurn（身體轉幾成：0＝正面、1＝90 度側身）、headTurn（頭轉幾成）、stride（跨步幅度）。
// 不同的參數組合＝不同的側面呈現方式。面向右（東）；朝西時呼叫端左右鏡像。
// 只支援樣張用到的裝備與種族部件（身體：shirt／plate／leather／robe；頭：helmet／hood；腳：boots／greaves；
// 主手：sword／bow／staff；副手：shield_round；披風；種族：角魔、狐族、龍裔）。座標同紙娃娃：腳底為原點、頭心 (0,-29)。
window.SideArt = (() => {
  const TAU = Math.PI * 2;
  const D = window.PaperDoll;
  const colors = (it) => (it ? D.itemColors(it) : ["#d8cdb4", "#a89c80"]);
  function fill(ctx, c, path) { ctx.fillStyle = c; ctx.beginPath(); path(); ctx.fill(); }
  function rr(ctx, x, y, w, h, r) { ctx.roundRect(x, y, w, h, r); }
  function hexRgb(h) { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
  function mix(a, b, t) {
    if (!a.startsWith("#")) return a;
    const [r1, g1, b1] = hexRgb(a), [r2, g2, b2] = hexRgb(b);
    const m = (x, y) => Math.round(x * (1 - t) + y * t);
    return `#${((m(r1, r2) << 16) | (m(g1, g2) << 8) | m(b1, b2)).toString(16).padStart(6, "0")}`;
  }
  const dark = (c, t = 0.3) => mix(c, "#000000", t);
  const lerp = (a, b, t) => a + (b - a) * t;

  // ---- 腿：bodyTurn 讓兩腿前後錯開、stride 讓兩腿張開 ----
  function leg(ctx, look, feet, x, ang, near, bt) {
    const pants = look.pants ?? "#4a4038";
    const [b, bd] = feet ? colors(feet) : ["#5a4030", "#3a281c"];
    ctx.save(); ctx.translate(x, -9); ctx.rotate(ang);
    fill(ctx, near ? pants : dark(pants, 0.25), () => rr(ctx, -2, 0, 4, 8.5, 1));
    const tall = { greaves: 4, boots: 2.5 }[feet?.kind] ?? 0;
    if (tall) fill(ctx, near ? b : dark(b, 0.2), () => rr(ctx, -2.2, 7.5 - tall, 4.4, tall + 1, 1));
    // 腳：側身時鞋尖朝前（變長、偏前）
    fill(ctx, near ? bd : dark(bd, 0.2), () => ctx.ellipse(lerp(0, 1.6, bt), 8, lerp(3.2, 3.8, bt), 2, 0, 0, TAU));
    ctx.restore();
  }
  // ---- 身體 ----
  function torso(ctx, it, look, bt) {
    const kind = it?.kind ?? "shirt";
    const [c, d] = colors(it);
    const w = lerp(15, 10, bt); // 側身時身體變薄
    const x0 = -w / 2 + lerp(0, -0.5, bt);
    if (kind === "robe") {
      fill(ctx, c, () => { ctx.moveTo(x0, -21); ctx.lineTo(x0 + w, -21); ctx.lineTo(x0 + w + lerp(3, 4, bt), -1.5); ctx.lineTo(x0 - lerp(3, 1.5, bt), -1.5); ctx.closePath(); });
      fill(ctx, look.trim ?? d, () => ctx.rect(lerp(-1.2, x0 + w - 2.6, bt), -20, 2.4, 18.5)); // 前襟跟著轉到前方
    } else {
      fill(ctx, c, () => rr(ctx, x0, -21, w, 13.5, 3));
      if (kind === "plate") fill(ctx, mix(c, "#ffffff", 0.35), () => rr(ctx, lerp(-5, x0 + w - 4.5, bt), -19.5, lerp(4, 3, bt), 6, 1.5));
      if (kind === "leather") { ctx.strokeStyle = d; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(x0 + 2, -20); ctx.lineTo(x0 + w - 2, -11); ctx.stroke(); }
      fill(ctx, look.belt ?? "#3a2a1c", () => ctx.rect(x0, -9.5, w, 2));
      fill(ctx, "#d8b04a", () => ctx.rect(lerp(-1, x0 + w - 2.5, bt), -9.5, 2, 2));
    }
    // 背側的暗面（看得出厚度）
    if (bt > 0.2) fill(ctx, "rgba(0,0,0,0.16)", () => rr(ctx, x0, -21, w * 0.32 * bt, kind === "robe" ? 19.5 : 13.5, 2));
    return { x0, w };
  }
  function arm(ctx, it, look, hands, sx, swing, near) {
    const [c] = colors(it);
    const [hc] = hands ? colors(hands) : [look.skin];
    ctx.save(); ctx.translate(sx, -20); ctx.rotate(swing);
    fill(ctx, near ? c : dark(c, 0.2), () => rr(ctx, -2, 0, 4, 10, 2));
    if (it?.kind === "plate") fill(ctx, mix(c, "#ffffff", 0.25), () => ctx.ellipse(0, 0.5, 3.2, 2.4, 0, 0, TAU));
    fill(ctx, near ? hc : dark(hc, 0.15), () => ctx.arc(0, 10.5, 2.4, 0, TAU));
    ctx.restore();
    return { x: sx + Math.sin(-swing) * 10.5, y: -20 + Math.cos(swing) * 10.5 };
  }
  // ---- 頭（headTurn：臉的五官往前移、遠側眼睛縮小或消失、出現鼻子；近側耳朵移到頭中後方）----
  function head(ctx, look, ht) {
    fill(ctx, look.skin, () => ctx.arc(0, -29, 8.5, 0, TAU));
    const fx = lerp(0, 4.2, ht); // 臉中心往前
    ctx.fillStyle = look.eyes ?? "#1d1a22";
    const nearEye = fx + lerp(2.6, 1.8, ht), farEye = fx - lerp(2.6, 3.2, ht);
    ctx.fillRect(nearEye, -30, 1.8, 3);
    if (ht < 0.85) ctx.fillRect(farEye, -30, lerp(1.8, 1.0, ht / 0.85), 3);
    if (ht > 0.35) fill(ctx, look.skin, () => { ctx.moveTo(lerp(6.5, 8, ht), -28.5); ctx.lineTo(lerp(8.2, 10.2, ht), -26.3); ctx.lineTo(lerp(6.8, 8.3, ht), -25.5); ctx.closePath(); }); // 鼻子
    ctx.fillStyle = "rgba(220,90,90,0.35)";
    ctx.fillRect(nearEye - 0.5, -26.5, 2, 1.2);
    if (ht > 0.25) fill(ctx, dark(look.skin, 0.15), () => ctx.ellipse(lerp(6, -1.5, ht), -28.5, 1.6, 2.4, 0, 0, TAU)); // 近側耳朵
    return fx;
  }
  function hair(ctx, look, ht, covered) {
    if (!look.hair || covered) return;
    const c = look.hairColor ?? "#5a3a22";
    // 頭髮往後偏：側面時後腦整片是頭髮、前面只剩瀏海
    fill(ctx, c, () => { ctx.arc(lerp(0, -1.5, ht), -29.5, 8.8, Math.PI * lerp(1.02, 0.75, ht), Math.PI * lerp(1.98, 1.85, ht)); ctx.quadraticCurveTo(lerp(4, 6, ht), -33, lerp(0, 3, ht), -32.5); ctx.closePath(); });
    if (look.hair === "long") fill(ctx, c, () => rr(ctx, lerp(-9.5, -8.5, ht), -31, lerp(3, 5, ht), 11, 1.5));
  }
  function headgear(ctx, it, ht) {
    if (!it) return;
    const [c, d] = colors(it);
    if (it.kind === "helmet") {
      fill(ctx, c, () => { ctx.arc(lerp(0, -0.8, ht), -30, 9.4, Math.PI, 0); ctx.lineTo(9.4, -27); ctx.lineTo(-9.4, -27); ctx.closePath(); });
      fill(ctx, d, () => ctx.rect(-9.4, -28, 18.8, 1.6));
      fill(ctx, d, () => ctx.rect(lerp(-1, 6.5, ht), -28, 2, 5)); // 護鼻片跟著臉轉
    } else if (it.kind === "hood") {
      ctx.fillStyle = c; ctx.beginPath();
      ctx.arc(lerp(0, -1.5, ht), -29.5, 10, Math.PI * 0.85, Math.PI * 2.15);
      ctx.lineTo(9, -22); ctx.lineTo(lerp(-9, -11, ht), -22); ctx.closePath();
      ctx.ellipse(lerp(0, 4.5, ht), -28, lerp(6.5, 4.6, ht), 6, 0, 0, TAU); // 臉的開口往前移、變窄
      ctx.fill("evenodd");
    }
  }
  // ---- 種族部件（樣張的三族）----
  function raceBack(ctx, look, bt) {
    // 尾巴從身後出來：側身時尾巴在背後（-x）
    const tx = lerp(4, -4, bt), dir = bt > 0.5 ? -1 : 1;
    const c = look.tailColor ?? look.hairColor ?? "#a8784a";
    ctx.save(); ctx.translate(tx, 0); ctx.scale(dir, 1);
    if (look.tail === "fox") { fill(ctx, c, () => { ctx.moveTo(0, -13); ctx.quadraticCurveTo(10, -14, 14, -6); ctx.quadraticCurveTo(17, 2, 11, 0); ctx.quadraticCurveTo(8, -6, 0, -9); }); fill(ctx, "#f4ece0", () => ctx.ellipse(13.5, -1.5, 3, 2.4, 0.4, 0, TAU)); }
    else if (look.tail === "demon") { ctx.strokeStyle = c; ctx.lineWidth = 1.8; ctx.lineCap = "round"; ctx.beginPath(); ctx.moveTo(0, -12); ctx.quadraticCurveTo(12, -10, 13, -2); ctx.stroke(); fill(ctx, c, () => { ctx.moveTo(13, -2); ctx.lineTo(10.5, 1.5); ctx.lineTo(13, 4.5); ctx.lineTo(15.5, 1.5); }); }
    else if (look.tail === "dragon") {
      fill(ctx, c, () => { ctx.moveTo(0, -15); ctx.quadraticCurveTo(12, -13, 17, -2); ctx.lineTo(20, 1); ctx.lineTo(15, 0); ctx.quadraticCurveTo(9, -6, 0, -8); });
      for (const t of [0.3, 0.55, 0.78]) fill(ctx, mix(c, "#ffffff", 0.3), () => { const x = 17 * t, y = -14 + 12 * t; ctx.moveTo(x - 1.5, y); ctx.lineTo(x + 0.5, y - 3.5); ctx.lineTo(x + 1.8, y + 0.5); });
    }
    ctx.restore();
    if (look.spines && bt > 0.3) for (const [x, y] of [[-4, -24], [-5.5, -20], [-6, -16]]) fill(ctx, mix(look.scaleColor ?? "#a8784a", "#ffffff", 0.2), () => { ctx.moveTo(x + 1, y - 2); ctx.lineTo(x - 3.5, y); ctx.lineTo(x + 1, y + 2); });
  }
  function raceHead(ctx, look, ht, headItem) {
    const covered = headItem && ["helmet", "hood"].includes(headItem.kind);
    if (look.pattern === "dragonscale") fill(ctx, look.scaleColor ?? "#a8784a", () => { for (const [x, y] of [[lerp(-6, 1, ht), -24.5], [lerp(-4.5, 3, ht), -22.5], [lerp(6, 2.5, ht), -26.5], [lerp(7, 0, ht), -30]]) { ctx.moveTo(x + 1.5, y); ctx.arc(x, y, 1.5, 0, Math.PI); } });
    if (look.slitEyes) { const ex = lerp(0, 4.2, ht) + lerp(2.6, 1.8, ht) + 0.9; fill(ctx, "#ffcf4a", () => ctx.ellipse(ex, -28.5, 1.4, 1.9, 0, 0, TAU)); fill(ctx, "#1d1a22", () => ctx.rect(ex - 0.35, -30.2, 0.7, 3.4)); }
    // 狐耳：兩隻都看得到，遠側那隻偏後、較暗
    if (look.ears === "beast" && !(headItem?.kind === "helmet")) {
      const c = headItem?.kind === "hood" ? colors(headItem)[0] : look.hairColor ?? "#d8762a";
      for (const [x, far] of [[lerp(-5, -4.5, ht), true], [lerp(5, 1.5, ht), false]]) fill(ctx, far ? dark(c, 0.2) : c, () => { ctx.moveTo(x - 2.5, -36); ctx.lineTo(x, -45); ctx.lineTo(x + 2.5, -35); });
    }
    // 角：側身時近側的角整支看得到（往後彎），遠側的角只露一截
    if (look.horns === "curved" || look.horns === "dragon") {
      const c = look.hornColor ?? "#3a2a2a";
      const big = look.horns === "dragon";
      for (const far of [true, false]) {
        const ox = far ? lerp(-5, -3, ht) : lerp(5, 1, ht), s = ht > 0.5 ? -1 : far ? -1 : 1; // 側身時兩支都往後彎
        fill(ctx, far ? dark(c, 0.25) : c, () => { ctx.moveTo(ox, -35); ctx.quadraticCurveTo(ox + s * (big ? 12 : 9), -38, ox + s * (big ? 12 : 7), big ? -46 : -47); ctx.quadraticCurveTo(ox + s * 5.5, -41, ox + s * 2.5, -38.5); ctx.quadraticCurveTo(ox + s * 1.5, -36, ox + s * 1.5, -33); });
      }
    }
    return covered;
  }
  // ---- 武器 ----
  function weapon(ctx, it, hx, hy, bt) {
    if (!it) return;
    const [c] = colors(it);
    ctx.save(); ctx.translate(hx, hy);
    if (it.kind === "sword") { ctx.rotate(lerp(-0.25, 0.9, bt)); fill(ctx, c, () => { ctx.moveTo(-1.3, -2); ctx.lineTo(-1.3, -16); ctx.lineTo(0, -19); ctx.lineTo(1.3, -16); ctx.lineTo(1.3, -2); }); fill(ctx, "#8a6a2a", () => rr(ctx, -4, -2.5, 8, 2, 1)); }
    else if (it.kind === "staff") { fill(ctx, "#7a5232", () => rr(ctx, -1, -26, 2, 30, 1)); fill(ctx, "#ff7a1a", () => ctx.arc(0, -27, 3.4, 0, TAU)); }
    else if (it.kind === "bow") { ctx.strokeStyle = "#7a5232"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(lerp(0, 2, bt), 0, 11, -1.2, 1.2); ctx.stroke(); ctx.strokeStyle = "#e8e0d0"; ctx.lineWidth = 0.6; ctx.beginPath(); ctx.moveTo(lerp(0, 2, bt) + Math.cos(-1.2) * 11, Math.sin(-1.2) * 11); ctx.lineTo(lerp(0, 2, bt) + Math.cos(1.2) * 11, Math.sin(1.2) * 11); ctx.stroke(); }
    ctx.restore();
  }
  function shield(ctx, it, bt, front) {
    if (!it) return;
    const [c, d] = colors(it);
    // 側身時盾牌轉成側邊（橢圓變窄），擋在身體前方
    const cx = lerp(front ? -8 : 8, 6.5, bt), rx = lerp(6, 2.6, bt);
    fill(ctx, c, () => ctx.ellipse(cx, -14, rx, 6.5, 0, 0, TAU));
    fill(ctx, d, () => ctx.ellipse(cx, -14, rx * 0.35, 2, 0, 0, TAU));
  }
  function cape(ctx, it, bt) {
    if (!it) return;
    const [c, d] = colors(it);
    // 側身時披風在背後垂下，往後飄一點
    fill(ctx, d, () => { ctx.moveTo(lerp(-8, -3, bt), -21); ctx.lineTo(lerp(8, 1, bt), -21); ctx.lineTo(lerp(12, -2, bt), -2); ctx.quadraticCurveTo(lerp(0, -8, bt), 1, lerp(-12, -12, bt), -2); ctx.closePath(); });
  }

  /** 畫一個人（面向右）；opt：{ bodyTurn, headTurn, stride } */
  function drawFigure(ctx, unit, opt) {
    const { look, gear } = unit;
    const bt = opt.bodyTurn, ht = opt.headTurn ?? bt, st = opt.stride ?? 0;
    const L = { ...look };
    if (window.RaceArt) window.RaceArt.build(ctx, L);
    cape(ctx, gear.cloak, bt);
    raceBack(ctx, L, bt);
    // 遠側的手（側身時藏在身後）與遠側的腿
    const farArmX = lerp(8.5, -1.5, bt), nearArmX = lerp(-8.5, 1.5, bt);
    const farLegX = lerp(3, 0.5, bt), nearLegX = lerp(-3, -0.5, bt);
    leg(ctx, L, gear.feet, farLegX, lerp(0, -0.35, st), false, bt);
    leg(ctx, L, gear.feet, nearLegX, lerp(0, 0.35, st), true, bt);
    if (bt > 0.5) arm(ctx, gear.body, L, gear.hands, farArmX, lerp(0, 0.5, st), false);
    torso(ctx, gear.body, L, bt);
    if (bt <= 0.5) arm(ctx, gear.body, L, gear.hands, farArmX, 0, false);
    shield(ctx, gear.off_hand, bt, false);
    const fx = head(ctx, L, ht);
    const covered = !!gear.head;
    hair(ctx, L, ht, covered);
    headgear(ctx, gear.head, ht);
    raceHead(ctx, L, ht, gear.head);
    const hand = arm(ctx, gear.body, L, gear.hands, nearArmX, lerp(0, -0.5, st), true);
    weapon(ctx, gear.main_hand, hand.x, hand.y, bt);
    return fx;
  }

  /** (cx, cy)＝腳底；k＝縮放；west＝鏡像。和紙娃娃一樣先畫離屏再描深色外框。 */
  function stamp(ctx, unit, opt, cx, cy, k = 1, west = false) {
    const S = 72, dpr = 3;
    const off = document.createElement("canvas"); off.width = S * k * dpr; off.height = S * k * dpr;
    const o = off.getContext("2d"); o.scale(k * dpr, k * dpr); o.translate(S / 2, S - 6); if (west) o.scale(-1, 1);
    drawFigure(o, unit, opt);
    const sil = document.createElement("canvas"); sil.width = off.width; sil.height = off.height;
    const sc = sil.getContext("2d"); sc.drawImage(off, 0, 0); sc.globalCompositeOperation = "source-in"; sc.fillStyle = "#16121a"; sc.fillRect(0, 0, sil.width, sil.height);
    const dx = cx - (S / 2) * k, dy = cy - (S - 6) * k, kk = 1.3 * k;
    for (const [ox, oy] of [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [1, -1], [-1, 1], [1, 1]]) ctx.drawImage(sil, dx + ox * kk, dy + oy * kk, S * k, S * k);
    ctx.drawImage(off, dx, dy, S * k, S * k);
  }
  return { stamp, drawFigure };
})();
