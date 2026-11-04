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
  // inHand(hand)：在手的座標系（含肩、肘旋轉）畫手上的東西，畫在手掌下面（握把被手蓋住）；handOnly＝只畫手上的東西（背面武器在身體後，手臂之後另外畫）
  function arm(ctx, unit, x, shoulderA, elbowA, side, inHand = null, handOnly = false) {
    const { look, gear } = unit, it = gear.body, kind = it?.kind ?? "shirt";
    const [c] = colors(it), sleeve = c;
    const [hc] = gear.hands ? colors(gear.hands) : [look.skin, look.skin];
    ctx.save();
    rotAt(ctx, x, -20, shoulderA);
    if (!handOnly) fill(ctx, sleeve, () => rr(ctx, x - 2, -21, 4, 6, 2));           // 上臂
    if (!handOnly && kind === "plate" && it?.form !== "half") fill(ctx, mix(c, "#ffffff", 0.25), () => { ctx.beginPath(); ctx.ellipse(x, -19.5, 3.5, 2.5, 0, 0, TAU); });
    rotAt(ctx, x, -15, elbowA);
    if (!handOnly) fill(ctx, sleeve, () => rr(ctx, x - 2, -15.5, 4, 5.5, 2));       // 前臂
    if (inHand) inHand([x, -9.5], ctx);
    if (!handOnly) fill(ctx, gear.hands && gear.hands.kind !== "bracers" ? hc : look.skin, () => { ctx.beginPath(); ctx.arc(x, -9.5, 2.4, 0, TAU); });
    const hand = [x, -9.5];
    ctx.restore();
    return hand;
  }
  // ---------- 頭：舊版 drawHead 原樣，加 bob／lean ----------
  // ---------- 可選外觀（11-04 晚，外觀變化方案 `docs/art/外觀變化方案.md`）：全部選填，不填＝舊版原樣 ----------
  //   face: round（預設）| oval 蛋臉 | square 方臉 | heart 尖下巴      eyeStyle: square（預設）| dot 圓點 | smile 笑眼 | big 大眼
  //   lashes: 睫毛   hair: short | long | bun | none（舊）＋ ponytail 馬尾 | twin 雙馬尾 | spiky 刺蝟 | bob 齊肩
  //   beardStyle: full 大鬍子（＝舊 beard）| short 短鬍渣 | goatee 山羊鬍 | mustache 八字鬍      frame: slim 纖細 | broad 壯碩（疊在種族 build 上）
  // 頭心一律在 (0,−29)、半寬約 8.5，所以種族的耳、角、紋路、頭盔照舊對得上。
  function headShape(ctx, look) {
    switch (look.face) {
      case "oval": ctx.ellipse(0, -29, 7.7, 9, 0, 0, TAU); break;
      case "square": ctx.roundRect(-8.3, -37.3, 16.6, 16.4, 4.6); break;
      case "heart": ctx.moveTo(0, -20.3); ctx.quadraticCurveTo(-8.7, -23.5, -8.6, -30); ctx.arc(0, -30, 8.6, Math.PI, 0); ctx.quadraticCurveTo(8.7, -23.5, 0, -20.3); ctx.closePath(); break;
      default: ctx.arc(0, -29, 8.5, 0, TAU);
    }
  }
  function eyes(ctx, look, side, ex) {
    const col = look.eyes ?? "#1d1a22", st = look.eyeStyle ?? "square", xs = [];
    if (side === 0 || side === 1) xs.push(ex + 2.9);
    if (side === 0 || side === -1) xs.push(ex - 2.9);
    for (const x of xs) {
      if (st === "dot") fill(ctx, col, () => ctx.ellipse(x, -28.6, 1.15, 1.45, 0, 0, TAU));
      else if (st === "smile") { ctx.strokeStyle = col; ctx.lineWidth = 1.05; ctx.lineCap = "round"; ctx.beginPath(); ctx.arc(x, -27.7, 1.5, Math.PI * 1.15, Math.PI * 1.85); ctx.stroke(); }
      else if (st === "big") { fill(ctx, col, () => ctx.roundRect(x - 1.3, -30.8, 2.6, 4, 1.2)); fill(ctx, "#ffffff", () => ctx.arc(x - 0.45, -29.7, 0.6, 0, TAU)); }
      else { ctx.fillStyle = col; ctx.fillRect(x - 0.9, -30, 1.8, 3); }
      if (look.lashes) { const o = x > ex ? 1 : -1; ctx.strokeStyle = col; ctx.lineWidth = 0.65; ctx.lineCap = "round"; ctx.beginPath(); ctx.moveTo(x + o * 0.8, -30.3 - (st === "big" ? 0.6 : 0)); ctx.lineTo(x + o * 2, -31.3 - (st === "big" ? 0.6 : 0)); ctx.stroke(); }
    }
  }
  function beard(ctx, look, side) {
    const st = look.beardStyle; if (!st || st === "full") return;
    const c = look.hairColor ?? "#5a3a22", ex = side * 2.6;
    if (st === "short") { ctx.save(); ctx.globalAlpha = 0.45; fill(ctx, c, () => { ctx.moveTo(ex - 6.9, -26); ctx.quadraticCurveTo(ex - 6, -20.6, ex, -20.4); ctx.quadraticCurveTo(ex + 6, -20.6, ex + 6.9, -26); ctx.quadraticCurveTo(ex, -23.4, ex - 6.9, -26); }); ctx.restore(); }
    if (st === "goatee") { fill(ctx, c, () => { ctx.moveTo(ex - 1.8, -23.6); ctx.lineTo(ex + 1.8, -23.6); ctx.lineTo(ex, -19.2); ctx.closePath(); }); fill(ctx, c, () => ctx.rect(ex - 1.8, -25.2, 3.6, 0.9)); }
    if (st === "mustache") for (const s2 of [-1, 1]) fill(ctx, c, () => { ctx.moveTo(ex, -25.6); ctx.quadraticCurveTo(ex + s2 * 2.8, -26.6, ex + s2 * 3.9, -24.1); ctx.quadraticCurveTo(ex + s2 * 2, -24.9, ex, -24.7); ctx.closePath(); });
  }
  // 頭後面的頭髮（馬尾、雙馬尾）：正面、側面畫在臉之前（被頭擋住一部分）
  function hairBehind(ctx, look, view, headgear) {
    if (!look.hair || look.skull || view === "back" || headgear?.kind === "hood") return;
    const c = look.hairColor ?? "#5a3a22", band = look.bunBand ?? "#d23c3c";
    if (look.hair === "twin") for (const s2 of view === "side" ? [-1] : [-1, 1]) {
      const x = view === "side" ? -6.5 : s2 * 9.6;
      fill(ctx, c, () => { ctx.moveTo(x - 1.6, -32); ctx.quadraticCurveTo(x + s2 * 3.4, -26, x + s2 * 1.6, -17.5); ctx.quadraticCurveTo(x - s2 * 0.6, -21, x - s2 * 2, -27); ctx.closePath(); });
      fill(ctx, band, () => ctx.arc(x, -30.6, 1.3, 0, TAU));
    }
    if (look.hair === "ponytail") {
      if (view === "side") { fill(ctx, c, () => { ctx.moveTo(-6, -34); ctx.quadraticCurveTo(-13.5, -32, -12, -20.5); ctx.quadraticCurveTo(-10, -26, -7, -28.5); ctx.closePath(); }); fill(ctx, band, () => ctx.arc(-7.4, -32.4, 1.3, 0, TAU)); }
      else fill(ctx, c, () => { ctx.moveTo(6.5, -35); ctx.quadraticCurveTo(12.5, -31, 10.5, -21); ctx.quadraticCurveTo(9.5, -27, 6, -30); ctx.closePath(); });
    }
  }
  // ---------- 頭：舊版 drawHead 原樣，加 bob／lean ----------
  function head(ctx, look, view, side, gear) {
    const skin = look.skin;
    hairBehind(ctx, look, view, gear.head);
    fill(ctx, skin, () => headShape(ctx, look));
    if (view === "back") { PD_hair(ctx, look, "back", gear.head); return; }
    const ex = side * 3.2;
    eyes(ctx, look, side, ex);
    ctx.fillStyle = "rgba(220,90,90,0.35)";
    if (side !== 1) ctx.fillRect(ex - 5, -26.5, 2, 1.2);
    if (side !== -1) ctx.fillRect(ex + 3, -26.5, 2, 1.2);
    // 表情：種族部件（raceArt）畫在臉上；鬍子樣式不是 full 時，種族的大鬍子換成選的樣式
    const L = look.beardStyle ? { ...look, beard: look.beardStyle === "full" } : look;
    if (window.RaceArt) window.RaceArt.face(ctx, L, view, side);
    beard(ctx, look, side);
    PD_hair(ctx, look, side ? "side" : "front", gear.head);
  }
  function PD_hair(ctx, look, view, headgear) {
    // 舊版 drawHair 照抄，加新髮型
    if (!look.hair || look.skull) return;
    const c = look.hairColor ?? "#5a3a22", band = look.bunBand ?? "#d23c3c";
    const covered = headgear && ["helmet", "hood", "wizard_hat", "horned_helm", "greathelm", "cap"].includes(headgear.kind);
    if (view === "back") {
      fill(ctx, c, () => { ctx.beginPath(); ctx.arc(0, -29, 8.8, 0, TAU); });
      if (look.hair === "long") fill(ctx, c, () => rr(ctx, -7, -29, 14, 10, 3));
      if (look.hair === "bob") fill(ctx, c, () => rr(ctx, -8.8, -30, 17.6, 8.5, 3.5));
      if (look.hair === "ponytail" && headgear?.kind !== "hood") { fill(ctx, c, () => rr(ctx, -2, -32, 4, 13, 2)); fill(ctx, band, () => rr(ctx, -2.3, -32, 4.6, 1.6, 0.8)); }
      if (look.hair === "twin" && headgear?.kind !== "hood") for (const s2 of [-1, 1]) { fill(ctx, c, () => { ctx.moveTo(s2 * 8, -32); ctx.quadraticCurveTo(s2 * 13, -26, s2 * 11, -17.5); ctx.quadraticCurveTo(s2 * 9.5, -22, s2 * 6.5, -28); ctx.closePath(); }); fill(ctx, band, () => ctx.arc(s2 * 8.6, -30.8, 1.3, 0, TAU)); }
      if (look.hair === "spiky" && !covered) fill(ctx, c, () => { for (let i = 0; i < 7; i++) { const a = Math.PI * (1.05 + i * 0.15); ctx.moveTo(Math.cos(a - 0.08) * 8.4, -29 + Math.sin(a - 0.08) * 8.4); ctx.lineTo(Math.cos(a) * 11.6, -29 + Math.sin(a) * 11.6); ctx.lineTo(Math.cos(a + 0.08) * 8.4, -29 + Math.sin(a + 0.08) * 8.4); } });
      return;
    }
    if (!covered) fill(ctx, c, () => { ctx.beginPath(); ctx.arc(0, -29.5, 8.8, Math.PI * 1.02, Math.PI * 1.98); ctx.quadraticCurveTo(4, -33, 0, -32.5); ctx.quadraticCurveTo(-5, -32, -8.8, -29); ctx.closePath(); });
    if (!covered && view === "side") fill(ctx, c, () => { ctx.beginPath(); ctx.arc(-1.5, -29.5, 8.8, Math.PI * 0.95, Math.PI * 1.6); ctx.lineTo(-6, -22); ctx.lineTo(-9.5, -24); ctx.closePath(); });
    if (look.hair === "long") { fill(ctx, c, () => rr(ctx, -9.5, -31, 3, 11, 1.5)); fill(ctx, c, () => rr(ctx, 6.5, -31, 3, 11, 1.5)); }
    if (look.hair === "bob") { if (view === "side") fill(ctx, c, () => rr(ctx, -9.6, -31, 4.2, 8.6, 2)); else { fill(ctx, c, () => rr(ctx, -9.6, -31.5, 3.4, 8.8, 1.7)); fill(ctx, c, () => rr(ctx, 6.2, -31.5, 3.4, 8.8, 1.7)); } }
    if (look.hair === "spiky" && !covered) fill(ctx, c, () => { for (let i = 0; i < 7; i++) { const a = Math.PI * (1.05 + i * 0.15); ctx.moveTo(Math.cos(a - 0.09) * 8.6, -29.5 + Math.sin(a - 0.09) * 8.6); ctx.lineTo(Math.cos(a) * 11.8, -29.5 + Math.sin(a) * 11.8); ctx.lineTo(Math.cos(a + 0.09) * 8.6, -29.5 + Math.sin(a + 0.09) * 8.6); } });
    if (look.hair === "bun") fill(ctx, look.bunBand ?? c, () => { ctx.beginPath(); ctx.arc(0, -37, 3, 0, TAU); });
  }

  // ---------- 武器（6M-2 規則）：握把在原點、作用端朝 −y；len＝原點到作用端；hold＝預設握法（側面相對手臂、正面絕對角度）----------
  // 造型照 paperdoll.js 的 drawWeapon／drawWeapon2（同尺寸同顏色），只拿掉它寫死在裡面的旋轉與位移，改由手決定角度。
  // 正面的 hold 照舊版的斜度（劍 −0.25、匕首 −0.6…），所以正面和舊版一模一樣；背面左右鏡像。
  const wc = (it, def) => (it && (it.color || it.material) ? colors(it) : PD.itemColors({ material: def, element: it?.element }));
  function sword(ctx, it, L, W) {
    const [c] = wc(it, "steel");
    fill(ctx, c, () => { ctx.moveTo(-W / 2, -3); ctx.lineTo(-W / 2, -L); ctx.lineTo(0, -L - 3); ctx.lineTo(W / 2, -L); ctx.lineTo(W / 2, -3); ctx.closePath(); });
    if (it?.form === "arcane") {
      const glow = "#9a86ff";
      ctx.save(); ctx.shadowColor = glow; ctx.shadowBlur = 4; ctx.fillStyle = glow; ctx.fillRect(-0.55, -L + 1, 1.1, L - 5); ctx.restore();
      ctx.fillStyle = "#e8e2ff"; for (const ry of [-6.5, -10, -13.5]) ctx.fillRect(-1.1, ry, 2.2, 0.8);
      fill(ctx, "#b08a4a", () => { for (let i = 0; i < 12; i++) { const a = (i / 12) * TAU, r = i % 2 ? 3.2 : 4.3; ctx.lineTo(Math.cos(a) * r, -3 + Math.sin(a) * r * 0.55); } ctx.closePath(); });
      fill(ctx, glow, () => ctx.arc(0, -3, 1.2, 0, TAU));
      fill(ctx, "#4a3020", () => ctx.rect(-1, -1.5, 2, 3.5));
      return;
    }
    fill(ctx, "rgba(255,255,255,0.45)", () => ctx.rect(-W / 2 + 0.6, -L, 0.9, L - 4));
    fill(ctx, it?.hilt ?? "#8a6a2a", () => ctx.roundRect(-4.5, -4, 9, 2, 1));
    fill(ctx, "#4a3020", () => ctx.rect(-1, -2, 2, L > 20 ? 8 : 4)); // 大劍握柄長到 +6，兩隻手疊著握
  }
  function dagger(ctx, it) {
    const [c] = wc(it, "iron");
    fill(ctx, c, () => { ctx.moveTo(-1.3, -2); ctx.lineTo(0, -10); ctx.lineTo(1.3, -2); ctx.closePath(); });
    fill(ctx, "#4a3020", () => ctx.rect(-2.5, -2.5, 5, 1.5));
    fill(ctx, "#4a3020", () => ctx.rect(-0.8, -1, 1.6, 3));
  }
  const QW = {
    sword: { len: 19, hold: { side: 0.75, front: -0.25 }, draw: (c, it) => sword(c, it, 16, 2.6) },
    greatsword: { len: 27, hold: { side: 0.75, front: -0.25 }, draw: (c, it) => sword(c, it, 24, 4) },
    arcane_blade: { len: 19, hold: { side: 0.75, front: -0.25 }, draw: (c, it) => sword(c, { ...it, form: "arcane" }, 16, 2.6) },
    saber: { len: 19, hold: { side: 0.75, front: -0.25 }, draw: (c, it) => {
      const [k] = wc(it, "steel");
      fill(c, k, () => { c.moveTo(-1.3, -3); c.quadraticCurveTo(-2.2, -12, 0.6, -19); c.lineTo(1.9, -18.4); c.quadraticCurveTo(0.6, -11, 1.3, -3); c.closePath(); });
      fill(c, "rgba(255,255,255,0.45)", () => { c.moveTo(-0.6, -4); c.quadraticCurveTo(-1.3, -11, 0.4, -16.5); c.lineTo(0.8, -16.3); c.quadraticCurveTo(-0.3, -11, 0.2, -4); c.closePath(); });
      fill(c, "#8a6a2a", () => c.ellipse(0, -3, 3.4, 1.4, 0, 0, TAU));
      fill(c, "#3a2a1a", () => c.rect(-1, -2, 2, 4.2));
    } },
    dagger: { len: 10, hold: { side: 0.75, front: -0.6 }, draw: dagger },
    paired: { len: 10, hold: { side: 0.75, front: -0.45 }, draw: (c, it) => { for (const [dx, r] of [[-1.4, -0.3], [1.4, 0.3]]) { c.save(); c.translate(dx, 0); c.rotate(r); dagger(c, it); c.restore(); } } },
    axe: { len: 18, hold: { side: 0.75, front: -0.3 }, draw: (c, it) => {
      const [k] = wc(it, "iron");
      fill(c, "#6a4420", () => c.rect(-1, -18, 2, 20));
      fill(c, k, () => { c.moveTo(1, -17); c.quadraticCurveTo(9, -18, 8, -10); c.lineTo(1, -12); c.closePath(); });
    } },
    hammer: { len: 22, hold: { side: 0.75, front: -0.25 }, draw: (c, it) => {
      const [k, d] = wc(it, "iron");
      fill(c, "#6a4420", () => c.rect(-1, -18, 2, 21));
      if (it?.form === "mace") fill(c, k, () => c.arc(0, -19, 4, 0, TAU)); else fill(c, k, () => c.roundRect(-5.5, -22, 11, 6, 1.2));
      fill(c, d, () => c.rect(-5.5, -19.5, 11, 1));
    } },
    spear: { len: 42, hold: { side: 0.15, front: 0 }, draw: (c, it) => {
      const [k] = wc(it, "steel");
      fill(c, "#6a4420", () => c.rect(-0.9, -34, 1.8, 42));
      fill(c, k, () => { c.moveTo(0, -42); c.lineTo(2.4, -34); c.lineTo(-2.4, -34); c.closePath(); });
      fill(c, "#8a6a2a", () => c.rect(-1.6, -34.5, 3.2, 1.4));
    } },
    scythe: { len: 26, hold: { side: 0.6, front: -0.15 }, draw: (c, it) => {
      const [k] = wc(it, "steel");
      fill(c, "#6a4420", () => c.rect(-1, -26, 2, 32));
      fill(c, k, () => { c.moveTo(0, -26); c.quadraticCurveTo(12, -28, 14, -18); c.quadraticCurveTo(8, -23, 0, -23); c.closePath(); });
    } },
    whip: { len: 18, hold: { side: 0.75, front: -0.25 }, draw: (c, it) => {
      fill(c, "#4a3020", () => c.roundRect(-1.1, -5, 2.2, 6.5, 0.8));
      c.strokeStyle = it?.color ?? "#5e3b1f"; c.lineWidth = 1.4; c.lineCap = "round";
      c.beginPath(); c.moveTo(0, -5); c.bezierCurveTo(4, -9, -4, -13, 1, -18); c.stroke();
      c.lineWidth = 0.8; c.beginPath(); c.moveTo(1, -18); c.quadraticCurveTo(3.5, -20, 2.2, -21.5); c.stroke();
    } },
    gauntlet: { len: 4, hold: { side: 1.0, front: 0 }, draw: (c, it) => {
      const [k, d] = wc(it, "steel");
      fill(c, k, () => c.roundRect(-2.8, -4, 5.6, 5.6, 1.6));
      fill(c, d, () => c.rect(-2.8, -4, 5.6, 1.1));
      if (it?.form === "katar" || it?.form === "claw") fill(c, k, () => { c.moveTo(-1.2, -4); c.lineTo(0, -10); c.lineTo(1.2, -4); c.closePath(); });
    } },
    staff: { len: 32, hold: { side: 0, front: 0 }, draw: (c, it) => {
      const orb = ({ fire: "#ff6a1a", water: "#4aa8ff", ice: "#8fe3ff", lightning: "#fff36b", poison: "#7ddc3a", wind: "#7fe0c0", earth: "#b0814a", holy: "#ffd75e", shadow: "#9a6ad8" })[it?.element] ?? "#c8bcff"; // 同 paperdoll 的 ELEMENT_TINT
      fill(c, "#6a4420", () => c.rect(-1.1, -30, 2.2, 34));
      c.save(); c.globalAlpha = 0.35; fill(c, orb, () => c.arc(0, -32, 6.5, 0, TAU)); c.restore();
      fill(c, orb, () => c.arc(0, -32, 3.6, 0, TAU));
      fill(c, "rgba(255,255,255,0.8)", () => c.arc(-1.2, -33.2, 1.1, 0, TAU));
    } },
    orb: { len: 6, hold: { side: 0.6, front: 0 }, draw: (c, it) => {
      const orb = it?.color ?? "#a898ff";
      c.save(); c.globalAlpha = 0.35; fill(c, orb, () => c.arc(0, -6, 6, 0, TAU)); c.restore();
      fill(c, orb, () => c.arc(0, -6, 3.6, 0, TAU));
      fill(c, "rgba(255,255,255,0.8)", () => c.arc(-1.2, -7.2, 1.1, 0, TAU));
    } },
    // 弓：弓臂橫在 x 軸、弓背朝 −y（＝箭的方向），弦在 +y；側面 hold π/2 讓箭朝前；正面 −π/2 弓背朝外（不蓋在身上）
    bow: { len: 6, hold: { side: Math.PI / 2, front: -Math.PI / 2 }, draw: (c, it) => {
      const [k] = wc(it, "wood"), pull = typeof POSE?.pull === "number" ? POSE.pull : 0, ex = Math.sin(1.2) * 13, ey = 9 - Math.cos(1.2) * 13;
      c.strokeStyle = "rgba(240,240,240,0.85)"; c.lineWidth = 0.8; c.beginPath(); c.moveTo(-ex, ey); c.lineTo(0, ey + pull); c.lineTo(ex, ey); c.stroke();
      c.strokeStyle = k; c.lineWidth = 2.2; c.lineCap = "round"; c.beginPath(); c.arc(0, 9, 13, -Math.PI / 2 - 1.2, -Math.PI / 2 + 1.2); c.stroke();
      fill(c, "#4a3020", () => c.rect(-1.4, -5.2, 2.8, 2.6));
      if (pull > 0.5) {
        c.strokeStyle = "#c8a070"; c.lineWidth = 0.9; c.beginPath(); c.moveTo(0, ey + pull); c.lineTo(0, -9); c.stroke();
        fill(c, "#c3ccd6", () => { c.moveTo(-1.2, -8.6); c.lineTo(0, -11); c.lineTo(1.2, -8.6); c.closePath(); });
      }
    } },
    crossbow: { len: 14, hold: { side: 2.2, front: Math.PI }, draw: (c, it) => {
      const [k] = wc(it, "iron");
      fill(c, "#7a5232", () => c.roundRect(-1.3, -12, 2.6, 16, 1));
      c.strokeStyle = "rgba(240,240,240,0.85)"; c.lineWidth = 0.7; c.beginPath(); c.moveTo(-8, -8); c.lineTo(0, -5.5); c.lineTo(8, -8); c.stroke();
      c.strokeStyle = k; c.lineWidth = 2; c.lineCap = "round"; c.beginPath(); c.moveTo(-8, -8); c.quadraticCurveTo(0, -13.5, 8, -8); c.stroke();
      c.strokeStyle = "#c8a070"; c.lineWidth = 0.9; c.beginPath(); c.moveTo(0, -5.5); c.lineTo(0, -14); c.stroke();
    } },
    gun: { len: 17, hold: { side: 2.3, front: Math.PI }, draw: (c, it) => {
      const form = it?.form ?? "rifle", L = { pistol: 7, rifle: 17, shotgun: 15, energy: 12 }[form] ?? 17, [k, d] = wc(it, "iron");
      if (form === "rifle" || form === "shotgun") fill(c, "#7a5232", () => c.roundRect(-1.8, 0, 3.6, 6.5, 1));
      fill(c, "#3a2a1c", () => c.roundRect(-1.2, -1, 2.4, 4, 0.8));
      fill(c, form === "energy" ? "#e8edf2" : k, () => c.roundRect(-1.3, -L, form === "shotgun" ? 3.2 : 2.6, L + 1, 1));
      fill(c, d, () => c.rect(-1.5, -L * 0.55, 3, 1.1));
    } },
  };
  const ALIAS = { fist: "gauntlet", longgun: "gun", shotgun: "gun", pistol: "gun", dual_dagger: "paired" };
  function qWeapon(it) {
    if (!it) return null;
    let kind = ALIAS[it.kind] ?? it.kind;
    if (kind === "sword" && it.form === "arcane") kind = "arcane_blade";
    const W = QW[kind];
    if (!W) return null;
    const item = ALIAS[it.kind] === "gun" ? { ...it, form: { longgun: "rifle", shotgun: "shotgun", pistol: "pistol" }[it.kind] } : it;
    return { W, item, kind };
  }
  /** 在手（座標 hand）畫主手武器；a＝武器角度。probe 回報握把與作用端的畫布座標（自測用）。 */
  function mainWeapon(ctx, it, hand, a, view) {
    const q = qWeapon(it);
    if (!q) { if (it) PD.drawWeapon(ctx, it, hand[0], view !== "back"); return; }
    ctx.save(); ctx.translate(hand[0], hand[1]); ctx.rotate(a); q.W.draw(ctx, q.item);
    if (POSE && POSE.probe) {
      const m = ctx.getTransform(), o = twoOff(q.kind, view);
      POSE.probe(q.kind, m.transformPoint(new DOMPoint(0, 0)), m.transformPoint(new DOMPoint(0, -q.W.len)), view, o ? m.transformPoint(new DOMPoint(o[0], o[1])) : null);
    }
    ctx.restore();
  }

  // ---------- 雙手武器（11-04 晚，使用者：「雙手武器 如弓等 有沒有概念演示圖 不然正面像一把弓懸浮」）----------
  // off＝副手握的點（武器座標：握把原點、作用端 −y）；front＝正面時武器角度（背面左右鏡像）；側面角度照 hold.side 或姿勢的 wpn。
  // 副手已經拿著東西（盾、書）時改回單手握（例：法師拿法杖＋書）。
  const TWO = {
    // pts：武器座標裡除了中軸以外會伸出去的點（弓臂兩端、鐮刃、護手、弩臂），擺位置時一起檢查不能蓋到臉
    greatsword: { off: [0, 4], front: -0.85, pts: [[-4.5, -3], [4.5, -3]], zh: "雙手疊握劍柄，劍斜在胸前、劍尖朝左上" },
    spear: { off: [0, 8], front: -0.75, pts: [], zh: "前後握槍桿，槍尖朝左上" },
    scythe: { off: [0, 6], front: -0.75, pts: [[14, -18], [12, -27]], zh: "前後握柄，刃在左上" },
    staff: { off: [0, 6], front: -0.75, pts: [[-6.5, -32], [6.5, -32]], zh: "一上一下握杖身，杖頭朝左上" },
    bow: { off: "string", offAt: -7, range: 1.1, front: -Math.PI / 2, pts: [[-12.1, 4.3], [12.1, 4.3], [-7, -2], [7, -2]], zh: "一手握弓身、一手搭弦" },
    crossbow: { off: [0, -6], front: Math.PI - 0.8, pts: [[-8, -8], [8, -8]], zh: "一手握把、一手托弩身，弩口朝右下" },
    gun: { off: [0, -8], front: Math.PI - 0.85, pts: [], zh: "一手握把、一手托槍管，槍口朝右下" },
  };
  const BOW_EY = 9 - Math.cos(1.2) * 13;
  // 弓：側面搭弦中央（拉弓時跟著 pull 往後）；正面、背面弓斜拿，副手搭在弦的下段（offAt），不然 Q 版短手臂下弓臂會碰到臉
  function twoOff(kind, view = "side") { const t = TWO[kind]; if (!t) return null; if (t.off !== "string") return t.off; return view === "side" ? [0, BOW_EY + (typeof POSE?.pull === "number" ? POSE.pull : 0)] : [view === "back" ? -t.offAt : t.offAt, BOW_EY]; } // 背面左右鏡像，弦上的握點也翻過來
  const twoKind = (gear) => { const q = qWeapon(gear.main_hand); return q && TWO[q.kind] && !gear.off_hand && twoPlace(q.kind) ? q.kind : null; }; // 找不到合法位置就退回單手（自測會標失敗）
  // 手臂兩節：肩 (x,−20) → 肘（+5）→ 手（+5.5）。fk：肩角 sA、肘角 eA → 手的位置；ik：反過來，out＝手肘往哪邊（+1 往 +x）
  const UA = 5, FA = 5.5, REACH = UA + FA - 0.1;
  const rot = (a, [x, y]) => [x * Math.cos(a) - y * Math.sin(a), x * Math.sin(a) + y * Math.cos(a)];
  function fk(x, sA, eA) { const e = [x - UA * Math.sin(sA), -20 + UA * Math.cos(sA)]; return [e[0] - FA * Math.sin(sA + eA), e[1] + FA * Math.cos(sA + eA)]; }
  function ik(x, t, out) {
    const dx = t[0] - x, dy = t[1] + 20, r0 = Math.hypot(dx, dy), r = Math.min(Math.max(r0, Math.abs(UA - FA) + 0.05), REACH);
    const phi = Math.atan2(-dx, dy), al = Math.acos((UA * UA + r * r - FA * FA) / (2 * UA * r)), be = Math.acos((UA * UA + FA * FA - r * r) / (2 * UA * FA));
    let best = null;
    for (const sg of [1, -1]) { const sA = phi + sg * al, eA = -sg * (Math.PI - be), sc = (x - UA * Math.sin(sA)) * out; if (!best || sc > best.sc) best = { sA, eA, sc }; }
    return { sA: best.sA, eA: best.eA, ok: r0 <= REACH };
  }
  // 正面雙手的位置：主手在畫面左肩 (−8.5,−20)、副手在右肩 (8.5,−20)；在兩隻手都搆得到、作用端露在身體外的位置裡，挑最接近腰前 (0,−12.5) 的
  const PLACE = {};
  function twoPlace(kind) {
    if (PLACE[kind] !== undefined) return PLACE[kind];
    const t = TWO[kind], len = QW[kind].len, off0 = twoOff(kind, "front"), R = t.range ?? 0.6;
    const inBody = ([x, y]) => (Math.abs(x) < 7.5 && y > -21 && y < 0) || Math.hypot(x, y + 29) < 8.5;
    let best = null;
    // 角度在偏好值 ±range（預設 0.6）內找（偏離越多分數越差），位置在腰前一帶找
    for (let da = -R; da <= R + 0.001; da += 0.05) {
      const a = t.front + da, o = rot(a, off0), tipDir = [Math.sin(a), -Math.cos(a)];
      for (let cx = -5; cx <= 5; cx += 0.25) for (let cy = -19; cy <= -5; cy += 0.25) {
        const m = [cx - o[0] / 2, cy - o[1] / 2], f = [cx + o[0] / 2, cy + o[1] / 2];
        if (Math.hypot(m[0] + 8.5, m[1] + 20) > REACH - 0.3 || Math.hypot(f[0] - 8.5, f[1] + 20) > REACH - 0.3) continue;
        if (inBody([m[0] + tipDir[0] * len, m[1] + tipDir[1] * len])) continue;
        // 不能經過臉：中軸每 1.5 單位取一點、加上 pts，都不能落在頭（含頭髮，半徑 9.8）裡
        const axis = []; for (let d = 0; d <= len; d += 1.5) axis.push([m[0] + tipDir[0] * d, m[1] + tipDir[1] * d]);
        const extra = (t.pts ?? []).map((q) => { const r = rot(a, q); return [m[0] + r[0], m[1] + r[1]]; });
        if ([...axis, ...extra].some(([x, y]) => Math.hypot(x, y + 29.3) < 9.8)) continue;
        const sc = (cy + 12.5) ** 2 + cx * cx + 40 * da * da;
        if (!best || sc < best.sc) best = { sc, main: m, off: f, a };
      }
    }
    return (PLACE[kind] = best);
  }
  const rec = (who) => (POSE && POSE.hands ? (hand, ctx) => { const q = ctx.getTransform().transformPoint(new DOMPoint(hand[0], hand[1])); POSE.hands[who] = [q.x, q.y]; } : null);
  const holdOf = (it, which) => { const q = qWeapon(it); return q ? q.W.hold[which] : which === "side" ? 0.75 : -0.25; };

  // ---------- 披風：正面（暗色、在身體後，舊版原樣）／側面（新：從肩膀垂到背後，在身體後）／背面（主色、蓋住背，舊版原樣＋褶） ----------
  function cloakFront(ctx, it) { const [, d] = colors(it); fill(ctx, d, () => { ctx.moveTo(-8, -21); ctx.lineTo(8, -21); ctx.lineTo(12, -2); ctx.quadraticCurveTo(0, 1, -12, -2); ctx.closePath(); }); }
  function cloakSide(ctx, it) {
    const [c, d] = colors(it);
    // 背後那片（主色）：肩膀 (−1.5..1.5, −21.5) 垂到小腿，下襬往後飄；身體在它前面
    fill(ctx, c, () => { ctx.moveTo(-1.5, -21.5); ctx.lineTo(1.5, -21.5); ctx.lineTo(-2.5, -6); ctx.quadraticCurveTo(-5.5, -1.8, -9.5, -3.2); ctx.lineTo(-8.2, -10); ctx.quadraticCurveTo(-6.5, -17, -4.5, -20.5); ctx.closePath(); });
    // 下襬翻起的裡襯（暗色），看得出是一片布
    fill(ctx, d, () => { ctx.moveTo(-3.2, -5.6); ctx.quadraticCurveTo(-5.8, -2.6, -9.5, -3.2); ctx.lineTo(-9, -5); ctx.quadraticCurveTo(-6, -4, -3.2, -7); ctx.closePath(); });
  }
  function cloakClasp(ctx, it, side) {
    if (!it) return;
    const [, d] = colors(it);
    fill(ctx, d, () => ctx.roundRect(side ? -2.5 : -6.5, -21.6, side ? 5 : 13, 1.8, 0.9));
    fill(ctx, "#e8bb48", () => ctx.arc(side ? 1.6 : 0, -20.7, 1.1, 0, TAU));
  }
  function cloakBack(ctx, it) {
    const [c, d] = colors(it);
    // 背面披風從肩膀披下來：上緣比舊版（±8, −21）高寬，圓肩蓋住肩甲（肩甲在 x ±8.5、y −22～−17）
    fill(ctx, c, () => { ctx.moveTo(-6.5, -23); ctx.lineTo(6.5, -23); ctx.quadraticCurveTo(11.2, -22.6, 11.4, -18); ctx.lineTo(12.6, -2); ctx.quadraticCurveTo(0, 1, -12.6, -2); ctx.lineTo(-11.4, -18); ctx.quadraticCurveTo(-11.2, -22.6, -6.5, -23); ctx.closePath(); });
    ctx.strokeStyle = d; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(-3, -18); ctx.lineTo(-5, -3); ctx.moveTo(3, -18); ctx.lineTo(5, -3); ctx.stroke();
  }
  // ---------- 盾：正面舊版原樣＋一圈鋼邊（和同色披風分得開）／側面（新：近乎側看的窄盾，在胸前）／背面（新：看到盾的背面＝木板＋皮帶） ----------
  const RIM = "#c3ccd6";
  function shieldFront(ctx, it, x) {
    PD.drawWeapon(ctx, it, x, true);
    if (it.kind === "shield_round") { ctx.strokeStyle = RIM; ctx.lineWidth = 0.9; ctx.beginPath(); ctx.arc(x, -13.5, 7.1, 0, TAU); ctx.stroke(); }
  }
  function shieldSide(ctx, it) {
    const [c, d] = colors(it), tower = it.kind === "shield_kite" && it.form === "tower";
    ctx.save(); ctx.translate(8.6, -13.5); // 拿在遠側手、舉在胸前：比身體前緣（x 5.4）再往前，近側手臂只蓋到盾的後緣
    if (it.kind === "shield_round") {
      fill(ctx, d, () => ctx.ellipse(0, 0, 2.9, 7.5, 0, 0, TAU));
      fill(ctx, c, () => ctx.ellipse(0.6, 0, 2.1, 6.2, 0, 0, TAU));
      ctx.strokeStyle = RIM; ctx.lineWidth = 0.9; ctx.beginPath(); ctx.ellipse(0.2, 0, 2.7, 7.2, 0, 0, TAU); ctx.stroke();
      fill(ctx, it.trim ?? "#e8bb48", () => ctx.ellipse(1.9, 0, 1.1, 2, 0, 0, TAU));
    } else {
      const top = tower ? -9 : -7, bot = tower ? 11 : 9;
      fill(ctx, d, () => { ctx.moveTo(-1.6, top); ctx.lineTo(2.2, top); ctx.lineTo(2.2, bot - 6); ctx.lineTo(0.6, bot); ctx.lineTo(-1.6, bot - 7); ctx.closePath(); });
      fill(ctx, c, () => { ctx.moveTo(-0.6, top + 1.2); ctx.lineTo(1.4, top + 1.2); ctx.lineTo(1.4, bot - 6.4); ctx.lineTo(0.5, bot - 2.4); ctx.lineTo(-0.6, bot - 7); ctx.closePath(); });
      fill(ctx, it.trim ?? "#e8e0c8", () => ctx.rect(1.3, top + 1, 1, bot - top - 4));
    }
    ctx.restore();
  }
  function shieldBack(ctx, it, x) {
    const [, d] = colors(it), wood = "#7a5232", strap = "#3a2414";
    ctx.save(); ctx.translate(x, -13.5);
    if (it.kind === "shield_round") {
      fill(ctx, d, () => ctx.arc(0, 0, 7.5, 0, TAU)); fill(ctx, wood, () => ctx.arc(0, 0, 6.2, 0, TAU));
      ctx.strokeStyle = RIM; ctx.lineWidth = 0.9; ctx.beginPath(); ctx.arc(0, 0, 7.1, 0, TAU); ctx.stroke();
    } else {
      fill(ctx, d, () => { ctx.moveTo(-7, -4); ctx.lineTo(7, -4); ctx.lineTo(6.5, 7); ctx.lineTo(0, 15); ctx.lineTo(-6.5, 7); ctx.closePath(); });
      fill(ctx, wood, () => { ctx.moveTo(-5.5, -2.5); ctx.lineTo(5.5, -2.5); ctx.lineTo(5, 6.5); ctx.lineTo(0, 12.8); ctx.lineTo(-5, 6.5); ctx.closePath(); });
    }
    fill(ctx, strap, () => ctx.rect(-4.5, -1.6, 9, 1.6)); fill(ctx, strap, () => ctx.rect(-4.5, 2.4, 9, 1.6));
    ctx.restore();
  }
  const isShield = (it) => !!it && String(it.kind).startsWith("shield");

  // ---------- 整隻：view = front | side | back；west 由 stamp 鏡像 ----------
  // 畫的順序（由後到前）
  //   正面：披風（暗）→ 尾巴 → 腿 → 身體 → 披風扣 → 副手臂＋副手 → 頭 → 主手臂＋武器（舊版順序）
  //   側面：披風（背後那片）→ 尾巴 → 遠側手臂（副手不是盾時拿在這隻手）→ 腿 → 身體 → 披風扣 → 盾（胸前）→ 頭 → 近側手臂＋武器
  //   背面（11-04 晚，使用者：「披風應該是最上層圖層對吧」）：主手武器（主手在畫面右）→ 盾背面（畫面左）→ 腿 → 身體 → 兩隻手臂（含肩甲）→ 披風（主色，蓋住肩甲、手、盾和武器重疊的部分）→ 尾巴（從披風下襬伸出）→ 頭、頭髮、頭盔
  //   側面的披風是背後那一片，在最底層；遠側手臂在它前面（手臂在身體側面，披風在背後）
  function draw(ctx, unit, view) {
    const { look, gear } = unit, F = view === "front", B = view === "back", S = view === "side";
    const side = S ? 1 : 0;
    const R = window.RaceArt;
    const mark = (n) => { if (POSE && POSE.layers) POSE.layers.push(n); }; // 自測用：記下圖層順序
    ctx.save();
    if (R) R.build(ctx, look);
    if (look.frame === "slim") ctx.scale(0.92, 1.02); else if (look.frame === "broad") ctx.scale(1.08, 0.98); // 可選體型，疊在種族 build 上
    ctx.translate(0, pz("bob"));
    if (S) rotAt(ctx, 0, -9, pz("lean"));
    // 影子已由呼叫端畫
    if (gear.cloak && F) cloakFront(ctx, gear.cloak);
    if (gear.cloak && S) { cloakSide(ctx, gear.cloak); mark("cloak"); }
    if (R && !B) R.tail(ctx, look, F ? "front" : "side", side);
    const two = twoKind(gear);
    if (B) {
      // 背面：手在身體前方，整隻手臂畫在身體後面（11-04 晚，使用者：「像法師那個拳頭應該看不到或者露一點邊緣而已」）；
      // 手臂往內收 0.3，肩膀的袖子露在身體兩側，手被身體擋住，最多露一點邊。
      if (two) {
        const P = twoPlace(two), mm = [-P.main[0], P.main[1]], ff = [-P.off[0], P.off[1]], im = ik(8.5, mm, 1), io = ik(-8.5, ff, -1);
        mainWeapon(ctx, gear.main_hand, mm, -P.a, "back"); mark("weapon");
        arm(ctx, unit, -8.5, io.sA, io.eA, 0, rec("off")); arm(ctx, unit, 8.5, im.sA, im.eA, 0, rec("main"));
      } else {
        ctx.save(); ctx.translate(0, pz("armR"));
        const rm = rec("main");
        arm(ctx, unit, 8.5, 0.3, 0, 0, (hand, c) => { mainWeapon(ctx, gear.main_hand, hand, -holdOf(gear.main_hand, "front") - 0.3, "back"); if (rm) rm(hand, c); });
        ctx.restore(); mark("weapon");
        ctx.save(); ctx.translate(0, pz("armL")); arm(ctx, unit, -8.5, -0.3, 0, 0, rec("off")); ctx.restore();
      }
      mark("arms");
      if (isShield(gear.off_hand)) { shieldBack(ctx, gear.off_hand, -8.5); mark("shield"); } else if (gear.off_hand) PD.drawWeapon(ctx, gear.off_hand, -8.5, false);
    }
    let sideW = 0;
    if (S) {
      // 側面雙手：近側手（主手）的位置和武器角度先算出來，遠側手（肩 (3,−20)，側看和近側肩幾乎重疊，在身體後）伸去握副手點；搆不到（出招伸太長）就放開
      const a = pz("arm"), eA = Math.min(0, a * 0.35);
      sideW = POSE && typeof POSE.wpn === "number" ? POSE.wpn : holdOf(gear.main_hand, "side");
      let done = false;
      if (two) {
        const h0 = fk(4.5, 0, eA), h = [4.5 + rot(a, [h0[0] - 4.5, h0[1] + 20])[0], -20 + rot(a, [h0[0] - 4.5, h0[1] + 20])[1]];
        const o = rot(a + eA + sideW, twoOff(two)), t = [h[0] + o[0], h[1] + o[1]], k = ik(3, t, -1);
        if (k.ok) { arm(ctx, unit, 3, k.sA, k.eA, side, rec("off")); done = true; }
      }
      if (!done) arm(ctx, unit, -4.5, pz("armL") * 0.6 - 0.1, 0.15, side, gear.off_hand && !isShield(gear.off_hand) ? (hand) => PD.drawWeapon(ctx, gear.off_hand, hand[0], true) : null);
    }
    leg(ctx, look, gear.feet, -1, pz("hipF"), pz("kneeF"), pz("liftL"), side);
    leg(ctx, look, gear.feet, 1, pz("hipN"), pz("kneeN"), pz("liftR"), side);
    body(ctx, gear.body, look, side); mark("body");
    if (S) { cloakClasp(ctx, gear.cloak, true); if (isShield(gear.off_hand)) shieldSide(ctx, gear.off_hand); }
    if (B) {
      if (gear.cloak) { cloakBack(ctx, gear.cloak); mark("cloak"); }
      if (R) R.tail(ctx, look, "back", 0);
    }
    if (F) {
      if (gear.cloak) cloakClasp(ctx, gear.cloak, false);
    }
    if (F && !two) {
      ctx.save(); ctx.translate(0, pz("armR")); arm(ctx, unit, 8.5, 0, 0, 0, rec("off"));
      if (isShield(gear.off_hand)) shieldFront(ctx, gear.off_hand, 8.5); else if (gear.off_hand) PD.drawWeapon(ctx, gear.off_hand, 8.5, true);
      ctx.restore();
    }
    mark("head");
    ctx.save(); rotAt(ctx, 0, -29, S ? pz("lean") * 0.3 : 0);
    head(ctx, look, F ? "front" : B ? "back" : "front", side, gear);
    if (R) R.ears(ctx, look, F ? "front" : "side", side, gear.head, "under");
    if (R) R.hat(ctx, look, gear.head, (it) => PD_headgear(ctx, it, B ? "back" : "front")); else PD_headgear(ctx, gear.head, B ? "back" : "front");
    if (R) R.ears(ctx, look, F ? "front" : "side", side, gear.head, "over");
    if (R) R.horns(ctx, look, F ? "front" : "side", side);
    ctx.restore();
    // 主手手臂＋武器：正面在畫面左（x −8.5）；側面在近側（x +4.5），手臂依 arm 轉、武器在手裡再依 wpn（或武器預設握法）轉
    if (F && two) {
      // 正面雙手：武器先畫，兩隻手臂蓋在武器上（手握住握把）
      const P = twoPlace(two), im = ik(-8.5, P.main, -1), io = ik(8.5, P.off, 1);
      mainWeapon(ctx, gear.main_hand, P.main, P.a, "front");
      arm(ctx, unit, 8.5, io.sA, io.eA, 0, rec("off")); arm(ctx, unit, -8.5, im.sA, im.eA, 0, rec("main"));
    } else if (F) {
      const rm = rec("main");
      ctx.save(); ctx.translate(0, pz("armL")); arm(ctx, unit, -8.5, 0, 0, 0, (hand, c) => { mainWeapon(ctx, gear.main_hand, hand, holdOf(gear.main_hand, "front"), "front"); if (rm) rm(hand, c); }); ctx.restore();
    } else if (S) {
      const a = pz("arm"), rm = rec("main");
      ctx.save(); rotAt(ctx, 4.5, -20, a);
      arm(ctx, unit, 4.5, 0, Math.min(0, a * 0.35), side, (hand, c) => { mainWeapon(ctx, gear.main_hand, hand, sideW, "side"); if (rm) rm(hand, c); });
      ctx.restore();
    }
    ctx.restore();
  }

  // ---------- 自測：13 種武器 × 4 方向（同 anim.js 的 6M-2 自測，再加靜止與背面）----------
  // 東／西出招：攻擊片段命中那一格，作用端在手的前方（朝面向）＞1.5 單位。
  // 東／西靜止：作用端不朝後（≥ −0.5；劍尖朝內就會失敗）。
  // 正面／背面：有畫到、作用端露在身體與頭的外面（背面武器在身體後，最容易被蓋掉）。
  // 全部 6 項都另外要求作用端在離屏畫布內（沒畫到或被切掉都算失敗，表上顯示「沒畫」）。
  function selfTest() {
    const A = window.Anim, C = document.createElement("canvas"); C.width = C.height = 4;
    const ctx = C.getContext("2d"), rows = [];
    const inBody = ([x, y]) => (Math.abs(x) < 7.5 && y > -21 && y < 0) || Math.hypot(x, y + 29) < 8.5;
    // 作用端要在離屏畫布裡（不然貼上時被切掉：第 2 版自己抓到的長槍、法杖出招）
    const inBox = (g) => !!g && Math.abs(g.tip[0]) < BOX.W / 2 - 1 && g.tip[1] > -(BOX.H - BOX.FOOT) + 1 && g.tip[1] < BOX.FOOT - 1;
    const probe = (kind, view, west, P) => {
      let got = null;
      ctx.setTransform(west ? -1 : 1, 0, 0, 1, 0, 0);
      const hands = {};
      POSE = { ...P, wpn: P.wpn === null ? undefined : P.wpn, hands, probe: (k, h, t, v, o) => { got = { hand: [h.x, h.y], tip: [t.x, t.y], off: o ? [o.x, o.y] : null }; } };
      draw(ctx, A.unit(kind), view); POSE = null;
      if (got) got.hands = hands;
      return got;
    };
    for (const kind of Object.keys(A.WEAPONS)) {
      const atk = A.CLIP[A.ATTACK[kind][1]].pose(1), r = { kind, zh: A.WEAPON_ZH[kind] };
      for (const [dir, west] of [["east", false], ["west", true]]) {
        const s = west ? -1 : 1, g = probe(kind, "side", west, atk), g0 = probe(kind, "side", west, A.REST);
        r[dir] = g && inBox(g) ? (g.tip[0] - g.hand[0]) * s : NaN; r[dir + "Rest"] = g0 && inBox(g0) ? (g0.tip[0] - g0.hand[0]) * s : NaN;
      }
      // 背面：手掌大小的單手武器（拳套、法球，len ≤ 6）跟手一起在身體前方，要被擋住；其他要從身體兩側露出
      const small = QW[kind].len <= 6 && !TWO[kind];
      for (const [dir, view] of [["south", "front"], ["north", "back"]]) { const g = probe(kind, view, false, A.REST); const hid = g ? inBody(g.tip) : false; r[dir] = g && inBox(g) ? ((dir === "north" && small ? hid : !hid) ? 1 : 0) : NaN; if (dir === "north") r.northSmall = small; }
      r.ok = { east: r.east > 1.5, west: r.west > 1.5, eastRest: r.eastRest >= -0.5, westRest: r.westRest >= -0.5, south: r.south === 1, north: r.north === 1 };
      r.pass = Object.values(r.ok).every(Boolean);
      rows.push(r);
    }
    rows.cloak = cloakTest();
    // 雙手武器：正面、背面兩隻手都在握把上（主手在握把原點、副手在副手握點，誤差 < 0.6）；側面靜止另外列出（只報告）
    const near = (a, b) => !!a && !!b && Math.hypot(a[0] - b[0], a[1] - b[1]) < 0.6;
    rows.two = [];
    for (const kind of [...Object.keys(A.WEAPONS).filter((k) => TWO[k]), "greatsword"]) {
      const r = { kind, zh: A.WEAPON_ZH[kind] ?? "雙手劍", how: TWO[kind].zh };
      for (const [dir, view, west] of [["south", "front", false], ["north", "back", false], ["east", "side", false]]) {
        const g = probe(kind, view, west, A.REST);
        r[dir] = !!g && near(g.hands.main, g.hand) && near(g.hands.off, g.off);
      }
      rows.two.push(r);
    }
    rows.hands = handTest();
    return rows;
  }
  // 背面的手：手在身體前方，畫面上被身體擋住；手心那一點和周圍 4 點（半徑 1.2）都不能是手的顏色（最多露一點邊）
  function handTest() {
    const TPL = PD.TEMPLATES, out = [];
    for (const [zh, tpl] of [["法師", "hero_mage"], ["劍盾", "hero_fighter"], ["弓手", "hero_archer"], ["盜賊", "bandit"], ["鳶盾", "bandit_shieldbearer"], ["頭目", "bandit_boss"]]) {
      const u = TPL[tpl], K = 4, C = document.createElement("canvas"); C.width = C.height = 256;
      const ctx = C.getContext("2d", { willReadFrequently: true });
      ctx.setTransform(K, 0, 0, K, 128, 220);
      const hands = {}; POSE = { hands }; draw(ctx, u, "back"); POSE = null;
      const hc = (u.gear.hands && u.gear.hands.kind !== "bracers" ? colors(u.gear.hands)[0] : u.look.skin).toLowerCase();
      const px = ([x, y]) => { const d = ctx.getImageData(Math.round(x), Math.round(y), 1, 1).data; return "#" + [d[0], d[1], d[2]].map((v) => v.toString(16).padStart(2, "0")).join(""); };
      const seen = [];
      for (const who of ["main", "off"]) {
        const h = hands[who]; if (!h) { seen.push(`${who}沒畫`); continue; }
        const n = [[0, 0], [1.2, 0], [-1.2, 0], [0, 1.2], [0, -1.2]].filter(([dx, dy]) => px([h[0] + dx * K, h[1] + dy * K]) === hc).length;
        if (n) seen.push(`${who === "main" ? "主手" : "副手"}露出 ${n}/5`);
      }
      out.push({ zh, ok: seen.length === 0, seen });
    }
    return out;
  }
  // 背面披風在最上層（頭除外）：圖層順序＋實際像素兩種檢查
  //   順序：武器、盾、身體、手臂（含肩甲）都在披風之前畫，頭在披風之後。
  //   像素：肩甲、盾、手和披風重疊的點，畫出來的顏色要是披風的顏色。
  function cloakTest() {
    const TPL = PD.TEMPLATES, out = [];
    for (const [zh, tpl] of [["劍盾＋藍披風", "hero_fighter"], ["大劍＋紅披風", "bandit_boss"]]) {
      const u = TPL[tpl], K = 4, C = document.createElement("canvas"); C.width = C.height = 256;
      const ctx = C.getContext("2d", { willReadFrequently: true });
      ctx.setTransform(K, 0, 0, K, 128, 220);
      POSE = { layers: [] }; draw(ctx, u, "back"); const L = POSE.layers; POSE = null;
      const at = (n) => L.indexOf(n), ci = at("cloak");
      const order = ci > 0 && ["weapon", "body", "arms"].every((n) => at(n) >= 0 && at(n) < ci) && (at("shield") < ci) && at("head") > ci;
      const want = colors(u.gear.cloak)[0].toLowerCase();
      const px = ([x, y]) => { const d = ctx.getImageData(128 + x * K, 220 + y * K, 1, 1).data; return "#" + [d[0], d[1], d[2]].map((v) => v.toString(16).padStart(2, "0")).join(""); };
      // 肩甲（左右）、手（主手）、盾和披風重疊處（只有帶盾的才測）
      const pts = [["左肩甲", [-6, -19.5]], ["右肩甲", [6, -19.5]], ["主手", [8.2, -9.5]]];
      if (isShield(u.gear.off_hand)) pts.push(["盾", [-7, -12]]);
      const bad = pts.filter(([, p]) => px(p) !== want).map(([n, p]) => `${n}${px(p)}`);
      out.push({ zh, order, pixels: bad.length === 0, bad, layers: L.join(">") });
    }
    return out;
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
  // 離屏畫布（單位）：舊版是 64×72、腳下留 6；出招時長槍、法杖伸出去會被切掉，放大到 128×112、腳下留 14（槍口朝下的正面也放得下）
  const BOX = { W: 128, H: 112, FOOT: 14 };
  // ---------- 貼上：舊版 stamp 原樣（離屏畫、剪影 8 方向偏移成外框、稀有度外光） ----------
  function stamp(ctx, unit, view, cx, cy, size = 1, west = false, opts = {}) {
    const dpr = opts.dpr ?? 3, { W, H, FOOT } = BOX;
    const off = document.createElement("canvas"); off.width = W * size * dpr; off.height = H * size * dpr;
    const o = off.getContext("2d"); o.scale(size * dpr, size * dpr); o.translate(W / 2, H - FOOT); if (west) o.scale(-1, 1);
    draw(o, unit, view);
    const sil = document.createElement("canvas"); sil.width = off.width; sil.height = off.height;
    const s = sil.getContext("2d"); s.drawImage(off, 0, 0); s.globalCompositeOperation = "source-in"; s.fillStyle = OUT; s.fillRect(0, 0, sil.width, sil.height);
    const k = 1.3 * size * dpr, dx0 = cx - (W / 2) * size, dy0 = cy - (H - FOOT) * size;
    ctx.save(); ctx.imageSmoothingEnabled = true;
    for (const [ox, oy] of [[k, 0], [-k, 0], [0, k], [0, -k], [k, k], [-k, k], [k, -k], [-k, -k]]) ctx.drawImage(sil, dx0 + ox / dpr, dy0 + oy / dpr, W * size, H * size);
    ctx.drawImage(off, dx0, dy0, W * size, H * size);
    ctx.restore();
  }
  return { draw, stamp, setPose: (p) => { POSE = p; }, selfTest, QW, TWO, twoPlace };
})();
