// qDoll.js：舊扁平版（paperdoll.js，10-29 以前）的 Q 版造型，重新掛上現行 6M／6N 骨架（美術 PM，2026-11-04）。
// 造型照 paperdoll.js 原封不動：身高約 46 單位、頭正圓 r 8.5 在 y −29（頭佔身高 37%）、身體 15 寬、腿 4×8、手臂 4×10、方形眼、腮紅方塊、
// 純色＋剪影外框（1.3 單位深色）。新加的只有：關節（髖、膝、肩、肘、手）、真側面（舊版沒有，用同一套 Q 語言補）、關節拆開後的接縫圓角。
// 姿勢物件和 storyDoll.js 完全同一份（bob、lean、hipN/F、kneeN/F、arm、wpn、armL/R、liftL/R、pull）。
window.QDoll = (() => {
  const TAU = Math.PI * 2, OUT = "#16121a";
  const PD = window.PaperDoll;
  let POSE = null;
  const pz = (k) => (POSE && POSE[k]) || 0;
  function rotAt(ctx, x, y, a) { if (!a) return; ctx.translate(x, y); ctx.rotate(a); ctx.translate(-x, -y); }
  function rr(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
  function fill(ctx, c, path) { ctx.beginPath(); ctx.fillStyle = c; path(); ctx.fill(); }
  function mix(a, b, t) { const p = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)); const A = p(a), B = p(b); return "#" + A.map((v, i) => Math.round(v + (B[i] - v) * t).toString(16).padStart(2, "0")).join(""); }
  const colors = (it) => (it ? PD.itemColors(it) : ["#d8cdb4", "#a89c80"]);

  // ---------- 腿：舊版 4×8 的方塊，拆成大腿（髖轉）＋小腿（膝轉）＋腳 ----------
  function leg(ctx, look, feet, sx, hip, knee, lift, side) {
    const pants = look.pants ?? "#4a4038";
    const [b, bd] = feet ? colors(feet) : ["#5a4030", "#3a281c"];
    const tall = { greaves: 4, boots: feet?.form === "tall" ? 4 : 2.5, iron_boots: 3, shoes: 0 }[feet?.kind] ?? 0;
    const x = side ? sx * 1.6 : sx * 3;
    ctx.save(); ctx.translate(0, -lift);
    rotAt(ctx, x, -9, hip * 1.6);
    fill(ctx, pants, () => rr(ctx, x - 2, -9.5, 4, 5, 1.2));          // 大腿
    rotAt(ctx, x, -5, knee * 1.6);
    fill(ctx, pants, () => rr(ctx, x - 2, -5.5, 4, 4.5, 1.2));         // 小腿
    if (tall) fill(ctx, b, () => rr(ctx, x - 2.2, -2 - tall, 4.4, tall + 1, 1));
    fill(ctx, bd, () => { ctx.beginPath(); ctx.ellipse(x + (side ? side * 0.8 : 0), -1.2, feet?.kind === "iron_boots" ? 3.6 : 3.2, 2, 0, 0, TAU); });
    ctx.restore();
  }
  // ---------- 身體：舊版 drawBody 原樣（去掉手臂那段，手臂改由 arm() 畫） ----------
  function body(ctx, it, look, side) {
    const kind = it?.kind ?? "shirt";
    const [c, d] = colors(it);
    ctx.save(); if (side) ctx.scale(0.72, 1);
    if (kind === "robe") {
      const hem = it?.form === "short" ? -6 : -1.5;
      fill(ctx, c, () => { ctx.beginPath(); ctx.moveTo(-7, -21); ctx.lineTo(7, -21); ctx.lineTo(10, hem); ctx.lineTo(-10, hem); ctx.closePath(); });
      if (!side) fill(ctx, look.trim ?? d, () => ctx.rect(-1.2, -20, 2.4, 18.5));
      fill(ctx, look.trim ?? d, () => ctx.rect(-10, hem - 1.5, 20, 1.6));
    } else if (kind === "coat") {
      fill(ctx, c, () => { ctx.beginPath(); ctx.moveTo(-7.5, -21); ctx.lineTo(7.5, -21); ctx.lineTo(8.5, -3); ctx.lineTo(1, -3); ctx.lineTo(0, -9); ctx.lineTo(-1, -3); ctx.lineTo(-8.5, -3); ctx.closePath(); });
      fill(ctx, d, () => { ctx.beginPath(); ctx.moveTo(-4, -21); ctx.lineTo(0, -15); ctx.lineTo(4, -21); ctx.closePath(); });
      for (const y of [-17, -14, -11]) fill(ctx, "#e8bb48", () => { ctx.beginPath(); ctx.arc(1.8, y, 0.7, 0, TAU); });
    } else {
      fill(ctx, c, () => rr(ctx, -7.5, -21, 15, 13.5, 3));
      if (kind === "plate") { fill(ctx, mix(c, "#ffffff", 0.35), () => rr(ctx, -5, -19.5, 4, 6, 1.5)); fill(ctx, d, () => ctx.rect(-7.5, -14, 15, 1.2)); }
      else if (kind === "mail") { ctx.fillStyle = d; for (let y = -19; y < -9; y += 2.4) for (let x = -6 + ((y | 0) % 2); x < 6.5; x += 2.4) ctx.fillRect(x, y, 1, 1); }
      else if (kind === "leather") { ctx.strokeStyle = d; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(-5, -20); ctx.lineTo(5, -11); ctx.stroke(); }
      fill(ctx, look.belt ?? "#3a2a1c", () => ctx.rect(-7.5, -9.5, 15, 2));
      fill(ctx, "#d8b04a", () => ctx.rect(-1, -9.5, 2, 2));
    }
    ctx.restore();
  }
  // ---------- 手臂：舊版 4×10 的方塊，拆成上臂（肩轉）＋前臂（肘轉）＋手 ----------
  function arm(ctx, unit, x, shoulderA, elbowA, side) {
    const { look, gear } = unit, it = gear.body, kind = it?.kind ?? "shirt";
    const [c] = colors(it), sleeve = c;
    const [hc] = gear.hands ? colors(gear.hands) : [look.skin, look.skin];
    ctx.save();
    rotAt(ctx, x, -20, shoulderA);
    fill(ctx, sleeve, () => rr(ctx, x - 2, -21, 4, 6, 2));           // 上臂
    if (kind === "plate" && it?.form !== "half") fill(ctx, mix(c, "#ffffff", 0.25), () => { ctx.beginPath(); ctx.ellipse(x, -19.5, 3.5, 2.5, 0, 0, TAU); });
    rotAt(ctx, x, -15, elbowA);
    fill(ctx, sleeve, () => rr(ctx, x - 2, -15.5, 4, 5.5, 2));       // 前臂
    fill(ctx, gear.hands && gear.hands.kind !== "bracers" ? hc : look.skin, () => { ctx.beginPath(); ctx.arc(x, -9.5, 2.4, 0, TAU); });
    const hand = [x, -9.5];
    ctx.restore();
    return hand;
  }
  // ---------- 頭：舊版 drawHead 原樣，加 bob／lean ----------
  function head(ctx, look, view, side, gear) {
    const F = view === "front";
    const skin = look.skin;
    fill(ctx, skin, () => { ctx.beginPath(); ctx.arc(0, -29, 8.5, 0, TAU); });
    if (view === "back") { PD_hair(ctx, look, "back", gear.head); return; }
    const ex = side * 3.2;
    ctx.fillStyle = look.eyes ?? "#1d1a22";
    if (side === 0 || side === 1) ctx.fillRect(ex + 2, -30, 1.8, 3);
    if (side === 0 || side === -1) ctx.fillRect(ex - 3.8, -30, 1.8, 3);
    ctx.fillStyle = "rgba(220,90,90,0.35)";
    if (side !== 1) ctx.fillRect(ex - 5, -26.5, 2, 1.2);
    if (side !== -1) ctx.fillRect(ex + 3, -26.5, 2, 1.2);
    // 表情：種族部件（raceArt）畫在臉上
    if (window.RaceArt) window.RaceArt.face(ctx, look, view, side);
    PD_hair(ctx, look, side ? "side" : "front", gear.head);
  }
  function PD_hair(ctx, look, view, headgear) {
    // 直接重用舊版 drawHair（透過 PaperDoll 內部的 drawFigure 不方便，這裡照抄）
    if (!look.hair || look.skull) return;
    const c = look.hairColor ?? "#5a3a22";
    const covered = headgear && ["helmet", "hood", "wizard_hat", "horned_helm", "greathelm", "cap"].includes(headgear.kind);
    if (view === "back") { fill(ctx, c, () => { ctx.beginPath(); ctx.arc(0, -29, 8.8, 0, TAU); }); if (look.hair === "long") fill(ctx, c, () => rr(ctx, -7, -29, 14, 10, 3)); return; }
    if (!covered) fill(ctx, c, () => { ctx.beginPath(); ctx.arc(0, -29.5, 8.8, Math.PI * 1.02, Math.PI * 1.98); ctx.quadraticCurveTo(4, -33, 0, -32.5); ctx.quadraticCurveTo(-5, -32, -8.8, -29); ctx.closePath(); });
    if (!covered && view === "side") fill(ctx, c, () => { ctx.beginPath(); ctx.arc(-1.5, -29.5, 8.8, Math.PI * 0.95, Math.PI * 1.6); ctx.lineTo(-6, -22); ctx.lineTo(-9.5, -24); ctx.closePath(); });
    if (look.hair === "long") { fill(ctx, c, () => rr(ctx, -9.5, -31, 3, 11, 1.5)); fill(ctx, c, () => rr(ctx, 6.5, -31, 3, 11, 1.5)); }
    if (look.hair === "bun") fill(ctx, look.bunBand ?? c, () => { ctx.beginPath(); ctx.arc(0, -37, 3, 0, TAU); });
  }

  // ---------- 整隻：view = front | side | back；west 由 stamp 鏡像 ----------
  function draw(ctx, unit, view) {
    const { look, gear } = unit, F = view === "front", B = view === "back", S = view === "side";
    const side = S ? 1 : 0;
    const R = window.RaceArt;
    ctx.save();
    if (R) R.build(ctx, look);
    ctx.translate(0, pz("bob"));
    if (S) rotAt(ctx, 0, -9, pz("lean"));
    // 影子已由呼叫端畫
    if (gear.cloak && !B) { const [c, d] = colors(gear.cloak); fill(ctx, d, () => { ctx.beginPath(); ctx.moveTo(-8, -21); ctx.lineTo(8, -21); ctx.lineTo(12, -2); ctx.quadraticCurveTo(0, 1, -12, -2); ctx.closePath(); }); }
    if (R && !B) R.tail(ctx, look, F ? "front" : "side", side);
    // 遠側手臂與武器（側面）先畫
    let farHand = null;
    if (S) farHand = arm(ctx, unit, -4.5, pz("armL") * 0.6 - 0.1, 0.15, side);     // 另一隻手（舊版沒有，補）
    // 腿
    leg(ctx, look, gear.feet, -1, pz("hipF"), pz("kneeF"), pz("liftL"), side);
    leg(ctx, look, gear.feet, 1, pz("hipN"), pz("kneeN"), pz("liftR"), side);
    body(ctx, gear.body, look, side);
    if (gear.cloak && B) { const [c] = colors(gear.cloak); fill(ctx, c, () => { ctx.beginPath(); ctx.moveTo(-8, -21); ctx.lineTo(8, -21); ctx.lineTo(12, -2); ctx.quadraticCurveTo(0, 1, -12, -2); ctx.closePath(); }); }
    // 正面：左右手臂各自上下（armL/armR）；副手盾
    if (F || B) {
      ctx.save(); ctx.translate(0, pz("armR")); arm(ctx, unit, 8.5, 0, 0, 0); if (gear.off_hand && !B) PD.drawWeapon(ctx, gear.off_hand, 8.5, true); ctx.restore();
    }
    ctx.save(); rotAt(ctx, 0, -29, S ? pz("lean") * 0.3 : 0);
    head(ctx, look, F ? "front" : B ? "back" : "front", side, gear);
    if (R) R.ears(ctx, look, F ? "front" : "side", side, gear.head, "under");
    if (R) R.hat(ctx, look, gear.head, (it) => PD_headgear(ctx, it, B ? "back" : "front")); else PD_headgear(ctx, gear.head, B ? "back" : "front");
    if (R) R.ears(ctx, look, F ? "front" : "side", side, gear.head, "over");
    if (R) R.horns(ctx, look, F ? "front" : "side", side);
    ctx.restore();
    // 主手手臂＋武器：正面在畫面左（x −8.5）；側面在近側（x +4.5），依 arm／wpn 旋轉
    if (F) { ctx.save(); ctx.translate(0, pz("armL")); arm(ctx, unit, -8.5, 0, 0, 0); PD.drawWeapon(ctx, gear.main_hand, -8.5, true); ctx.restore(); }
    else if (B) { arm(ctx, unit, -8.5, 0, 0, 0); PD.drawWeapon(ctx, gear.main_hand, 8.5, false); }
    else {
      const a = pz("arm");
      ctx.save(); rotAt(ctx, 4.5, -20, a);
      arm(ctx, unit, 4.5, 0, Math.min(0, a * 0.35), side);
      // 武器：握把在手心，作用端朝 −y；wpn 給相對角度（和 storyDoll 同規則），null＝照武器預設
      const w = POSE && POSE.wpn !== undefined && POSE.wpn !== null ? POSE.wpn : 0.75;
      ctx.save(); ctx.translate(4.5, -9.5); ctx.rotate(w - 0.75); ctx.translate(-4.5, 9.5); PD.drawWeapon(ctx, gear.main_hand, 4.5, true); ctx.restore();
      ctx.restore();
    }
    ctx.restore();
  }
  function PD_headgear(ctx, it, view) { if (!it) return; PD.drawHeadgearPublic ? PD.drawHeadgearPublic(ctx, it, view) : PD_fallbackHeadgear(ctx, it, view); }
  // paperdoll.js 沒有匯出 drawHeadgear；用它的 drawFigure 畫一次只留頭飾太貴，這裡照抄常用的幾種
  function PD_fallbackHeadgear(ctx, it, view) {
    const [c, d] = colors(it);
    switch (it.kind) {
      case "hood": ctx.fillStyle = c; ctx.beginPath(); ctx.arc(0, -29.5, 10, Math.PI * 0.85, Math.PI * 2.15); ctx.lineTo(9, -22); ctx.lineTo(-9, -22); ctx.closePath(); if (view !== "back") ctx.ellipse(0, -28, 6.5, 6, 0, 0, TAU); ctx.fill("evenodd"); fill(ctx, d, () => ctx.rect(-9, -23, 18, 1.5)); break;
      case "helmet": case "horned_helm": fill(ctx, c, () => { ctx.beginPath(); ctx.arc(0, -30, 9.4, Math.PI, 0); ctx.lineTo(9.4, -27); ctx.lineTo(-9.4, -27); ctx.closePath(); }); fill(ctx, d, () => ctx.rect(-9.4, -27.5, 18.8, 1.2)); if (it.kind === "horned_helm") for (const s of [-1, 1]) fill(ctx, "#e8d8b8", () => { ctx.beginPath(); ctx.moveTo(s * 8, -31); ctx.lineTo(s * 13, -40); ctx.lineTo(s * 10, -30); ctx.closePath(); }); break;
      case "wizard_hat": fill(ctx, c, () => { ctx.beginPath(); ctx.moveTo(-12, -34); ctx.lineTo(12, -34); ctx.lineTo(3, -37); ctx.lineTo(2, -52); ctx.lineTo(-4, -37); ctx.closePath(); }); fill(ctx, d, () => ctx.rect(-6, -36.5, 12, 1.4)); break;
      case "cap": fill(ctx, c, () => { ctx.beginPath(); ctx.arc(0, -31, 9, Math.PI, 0); ctx.closePath(); }); fill(ctx, d, () => rr(ctx, -9.5, -32, 19, 1.6, 0.8)); break;
      case "bandana": fill(ctx, c, () => { ctx.beginPath(); ctx.arc(0, -31, 9, Math.PI, 0); ctx.closePath(); }); fill(ctx, d, () => rr(ctx, 6, -31, 5, 2, 1)); break;
      case "circlet": fill(ctx, c, () => rr(ctx, -9, -34, 18, 1.6, 0.8)); fill(ctx, "#a898ff", () => { ctx.beginPath(); ctx.moveTo(0, -36.5); ctx.lineTo(1.8, -34); ctx.lineTo(0, -31.5); ctx.lineTo(-1.8, -34); ctx.closePath(); }); break;
      case "wide_hat": fill(ctx, c, () => { ctx.beginPath(); ctx.ellipse(0, -34, 14, 4, 0, 0, TAU); }); fill(ctx, d, () => { ctx.beginPath(); ctx.arc(0, -35, 8, Math.PI, 0); ctx.closePath(); }); break;
      case "veil": fill(ctx, c, () => rr(ctx, -9, -26, 18, 5, 2)); break;
      case "goggles": for (const x of [-3, 3]) { fill(ctx, "#8d969f", () => { ctx.beginPath(); ctx.ellipse(x, -29.5, 3, 2.6, 0, 0, TAU); }); fill(ctx, "rgba(160,220,255,0.7)", () => { ctx.beginPath(); ctx.ellipse(x, -29.5, 2.2, 1.9, 0, 0, TAU); }); } break;
    }
  }
  // ---------- 貼上：舊版 stamp 原樣（離屏畫、剪影 8 方向偏移成外框、稀有度外光） ----------
  function stamp(ctx, unit, view, cx, cy, size = 1, west = false, opts = {}) {
    const dpr = opts.dpr ?? 3, W = 64, H = 72;
    const off = document.createElement("canvas"); off.width = W * size * dpr; off.height = H * size * dpr;
    const o = off.getContext("2d"); o.scale(size * dpr, size * dpr); o.translate(W / 2, H - 6); if (west) o.scale(-1, 1);
    draw(o, unit, view);
    const sil = document.createElement("canvas"); sil.width = off.width; sil.height = off.height;
    const s = sil.getContext("2d"); s.drawImage(off, 0, 0); s.globalCompositeOperation = "source-in"; s.fillStyle = OUT; s.fillRect(0, 0, sil.width, sil.height);
    const k = 1.3 * size * dpr, dx0 = cx - (W / 2) * size, dy0 = cy - (H - 6) * size;
    ctx.save(); ctx.imageSmoothingEnabled = true;
    for (const [ox, oy] of [[k, 0], [-k, 0], [0, k], [0, -k], [k, k], [-k, k], [k, -k], [-k, -k]]) ctx.drawImage(sil, dx0 + ox / dpr, dy0 + oy / dpr, W * size, H * size);
    ctx.drawImage(off, dx0, dy0, W * size, H * size);
    ctx.restore();
  }
  return { draw, stamp, setPose: (p) => { POSE = p; } };
})();
