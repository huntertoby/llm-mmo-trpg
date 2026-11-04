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
  // 只該出現在正面的配件（腰帶扣、外套領口與扣子、長袍前襟）：側面轉到身體前緣，背面不畫（11-04 晚，使用者：「皮帶為什麼在側面」）
  function body(ctx, it, look, side, back = false) {
    const kind = it?.kind ?? "shirt";
    const [c, d] = colors(it);
    ctx.save(); if (side) ctx.scale(0.72, 1);
    if (kind === "robe") {
      const hem = it?.form === "short" ? -6 : -1.5;
      fill(ctx, c, () => { ctx.beginPath(); ctx.moveTo(-7, -21); ctx.lineTo(7, -21); ctx.lineTo(10, hem); ctx.lineTo(-10, hem); ctx.closePath(); });
      if (!side && !back) fill(ctx, look.trim ?? d, () => ctx.rect(-1.2, -20, 2.4, 18.5));
      else if (side) fill(ctx, look.trim ?? d, () => ctx.rect(7.2, -20.5, 1.8, 19)); // 側面：前襟在身體前緣
      fill(ctx, look.trim ?? d, () => ctx.rect(-10, hem - 1.5, 20, 1.6));
    } else if (kind === "coat") {
      fill(ctx, c, () => { ctx.beginPath(); ctx.moveTo(-7.5, -21); ctx.lineTo(7.5, -21); ctx.lineTo(8.5, -3); ctx.lineTo(1, -3); ctx.lineTo(0, -9); ctx.lineTo(-1, -3); ctx.lineTo(-8.5, -3); ctx.closePath(); });
      if (!side && !back) {
        fill(ctx, d, () => { ctx.beginPath(); ctx.moveTo(-4, -21); ctx.lineTo(0, -15); ctx.lineTo(4, -21); ctx.closePath(); });
        for (const y of [-17, -14, -11]) fill(ctx, "#e8bb48", () => { ctx.beginPath(); ctx.arc(1.8, y, 0.7, 0, TAU); });
      } else if (side) {
        fill(ctx, d, () => { ctx.beginPath(); ctx.moveTo(5.5, -21); ctx.lineTo(7.5, -16); ctx.lineTo(7.5, -21); ctx.closePath(); });
        for (const y of [-17, -14, -11]) fill(ctx, "#e8bb48", () => { ctx.beginPath(); ctx.arc(6.6, y, 0.7, 0, TAU); });
      }
    } else {
      fill(ctx, c, () => rr(ctx, -7.5, -21, 15, 13.5, 3));
      // 胸口高光：側面在胸前那半邊，背面不畫
      if (kind === "plate") { if (!back) fill(ctx, mix(c, "#ffffff", 0.35), () => rr(ctx, side ? 1.5 : -5, -19.5, 4, 6, 1.5)); fill(ctx, d, () => ctx.rect(-7.5, -14, 15, 1.2)); }
      else if (kind === "mail") { ctx.fillStyle = d; for (let y = -19; y < -9; y += 2.4) for (let x = -6 + ((y | 0) % 2); x < 6.5; x += 2.4) ctx.fillRect(x, y, 1, 1); }
      else if (kind === "leather") { ctx.strokeStyle = d; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(-5, -20); ctx.lineTo(5, -11); ctx.stroke(); }
      fill(ctx, look.belt ?? "#3a2a1c", () => ctx.rect(-7.5, -9.5, 15, 2));
      if (!side && !back) fill(ctx, "#d8b04a", () => ctx.rect(-1, -9.5, 2, 2));
      else if (side) fill(ctx, "#d8b04a", () => ctx.rect(6.2, -9.5, 1.3, 2)); // 側面：帶扣轉到身體前緣，只露一點
    }
    ctx.restore();
  }
  // ---------- 手臂：舊版 4×10 的方塊，拆成上臂（肩轉）＋前臂（肘轉）＋手 ----------
  // inHand(hand)：在手的座標系（含肩、肘旋轉）畫手上的東西，畫在手掌下面（握把被手蓋住）；handOnly＝只畫手上的東西（背面武器在身體後，手臂之後另外畫）
  function arm(ctx, unit, x, shoulderA, elbowA, side, inHand = null, handOnly = false) {
    const { look, gear } = unit, it = gear.body, kind = it?.kind ?? "shirt";
    const [c] = colors(it), sleeve = TINT ?? c;
    const [hc] = gear.hands ? colors(gear.hands) : [look.skin, look.skin];
    ctx.save();
    rotAt(ctx, x, -20, shoulderA);
    if (!handOnly) fill(ctx, sleeve, () => rr(ctx, x - 2, -21, 4, 6, 2));           // 上臂
    if (!handOnly && kind === "plate" && it?.form !== "half") fill(ctx, mix(c, "#ffffff", 0.25), () => { ctx.beginPath(); ctx.ellipse(x, -19.5, 3.5, 2.5, 0, 0, TAU); });
    rotAt(ctx, x, -15, elbowA);
    if (!handOnly) fill(ctx, sleeve, () => rr(ctx, x - 2, -15.5, 4, 5.5, 2));       // 前臂
    if (inHand) inHand([x, -9.5], ctx);
    if (!handOnly) fill(ctx, TINT ?? (gear.hands && gear.hands.kind !== "bracers" ? hc : look.skin), () => { ctx.beginPath(); ctx.arc(x, -9.5, 2.4, 0, TAU); });
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
      ctx.save(); ctx.shadowColor = glow; ctx.shadowBlur = 4 + 8 * pz("glow"); ctx.fillStyle = glow; ctx.fillRect(-0.55, -L + 1, 1.1, L - 5); ctx.restore();
      ctx.fillStyle = "#e8e2ff"; for (const ry of [-6.5, -10, -13.5]) ctx.fillRect(-1.1, ry, 2.2, 0.8);
      fill(ctx, "#b08a4a", () => { for (let i = 0; i < 12; i++) { const a = (i / 12) * TAU, r = i % 2 ? 3.2 : 4.3; ctx.lineTo(Math.cos(a) * r, -3 + Math.sin(a) * r * 0.55); } ctx.closePath(); });
      fill(ctx, glow, () => ctx.arc(0, -3, 1.2, 0, TAU));
      fill(ctx, "#4a3020", () => ctx.rect(-1, -1.5, 2, 3.5));
      return;
    }
    fill(ctx, "rgba(255,255,255,0.45)", () => ctx.rect(-W / 2 + 0.6, -L, 0.9, L - 4));
    fill(ctx, it?.hilt ?? "#8a6a2a", () => ctx.roundRect(-4.5, -4, 9, 2, 1));
    fill(ctx, "#4a3020", () => ctx.rect(-1, -2, 2, W >= 4 ? 8 : 4)); // 雙手劍（寬 4）握柄長到 +6，兩隻手疊著握
  }
  function dagger(ctx, it) {
    const [c] = wc(it, "iron");
    fill(ctx, c, () => { ctx.moveTo(-1.3, -2); ctx.lineTo(0, -10); ctx.lineTo(1.3, -2); ctx.closePath(); });
    fill(ctx, "#4a3020", () => ctx.rect(-2.5, -2.5, 5, 1.5));
    fill(ctx, "#4a3020", () => ctx.rect(-0.8, -1, 1.6, 3));
  }
  // Q 版短弓：弧半徑 8.5、張角 ±1.2 → 弓高約 16、弦離弓把 5.4（原尺寸 24 高的弓，正面搭弦時上弓臂一定碰到臉；Q 版身高 46）
  const BOW_R = 8.5, BOW_A = 1.2, BOW_EY = BOW_R - Math.cos(BOW_A) * BOW_R;
  const QW = {
    sword: { len: 19, hold: { side: 0.75, front: -0.25 }, draw: (c, it) => sword(c, it, 16, 2.6) },
    greatsword: { len: 27, hold: { side: 0.75, front: -0.25 }, draw: (c, it) => sword(c, it, 24, 4) },
    // 拄劍用的雙手劍：劍身短 5（Q 版身高 46，原長劍尖會穿過地面太多；使用者：「垂直 劍尖指地也可以但可能長度或高度不構」）
    // 拄劍（關鍵姿勢）用的雙手劍：劍身 14，劍尖剛好點在兩腳之間
    greatsword_k: { len: 17, hold: { side: 0.75, front: -0.25 }, draw: (c, it) => sword(c, it, 14, 4) },
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
      fill(c, "#6a4420", () => c.rect(-0.9, -34, 1.8, 45)); // 槍桿到 +11，後手握在 +8
      fill(c, k, () => { c.moveTo(0, -42); c.lineTo(2.4, -34); c.lineTo(-2.4, -34); c.closePath(); });
      fill(c, "#8a6a2a", () => c.rect(-1.6, -34.5, 3.2, 1.4));
    } },
    scythe: { len: 26, hold: { side: 0.6, front: -0.15 }, draw: (c, it) => {
      const [k] = wc(it, "steel");
      fill(c, "#6a4420", () => c.rect(-1, -26, 2, 35)); // 柄到 +9，後手握在 +6
      fill(c, k, () => { c.moveTo(0, -26); c.quadraticCurveTo(12, -28, 14, -18); c.quadraticCurveTo(8, -23, 0, -23); c.closePath(); });
    } },
    whip: { len: 18, hold: { side: 0.75, front: -0.25 }, draw: (c, it) => {
      fill(c, "#4a3020", () => c.roundRect(-1.1, -5, 2.2, 6.5, 0.8));
      c.strokeStyle = it?.color ?? "#5e3b1f"; c.lineWidth = 1.4; c.lineCap = "round";
      if (POSE && typeof POSE.wpn === "number") {
        // 出招（6M／6N 片段）：鞭身拉直往前抽出去，梢端一點彎（11-04 晚看出招特寫：命中格鞭子往下垂，不像抽出去）
        c.beginPath(); c.moveTo(0, -5); c.quadraticCurveTo(1.2, -15, 0, -24); c.stroke();
        c.lineWidth = 0.8; c.beginPath(); c.moveTo(0, -24); c.quadraticCurveTo(-1.5, -27, 0.6, -29); c.stroke();
      } else {
        const w = Math.sin(pz("lash") * TAU) * 2.5; // 待機：鞭梢甩動
        c.beginPath(); c.moveTo(0, -5); c.bezierCurveTo(4 + w, -9, -4 - w, -13, 1 + w, -18); c.stroke();
        c.lineWidth = 0.8; c.beginPath(); c.moveTo(1 + w, -18); c.quadraticCurveTo(3.5 + 1.6 * w, -20, 2.2 + 2 * w, -21.5); c.stroke();
      }
    } },
    gauntlet: { len: 4, hold: { side: 1.0, front: 0 }, draw: (c, it) => {
      const [k, d] = wc(it, "steel");
      fill(c, k, () => c.roundRect(-2.8, -4, 5.6, 5.6, 1.6));
      fill(c, d, () => c.rect(-2.8, -4, 5.6, 1.1));
      if (it?.form === "katar" || it?.form === "claw") fill(c, k, () => { c.moveTo(-1.2, -4); c.lineTo(0, -10); c.lineTo(1.2, -4); c.closePath(); });
    } },
    staff: { len: 32, hold: { side: 0, front: 0 }, draw: (c, it) => {
      const orb = ({ fire: "#ff6a1a", water: "#4aa8ff", ice: "#8fe3ff", lightning: "#fff36b", poison: "#7ddc3a", wind: "#7fe0c0", earth: "#b0814a", holy: "#ffd75e", shadow: "#9a6ad8" })[it?.element] ?? "#c8bcff"; // 同 paperdoll 的 ELEMENT_TINT
      fill(c, "#6a4420", () => c.rect(-1.1, -30, 2.2, 39)); // 杖身到 +9，下手握在 +6
      const g = pz("glow"); // 待機的光脈動（idleWeapons.js）：0～1
      c.save(); c.globalAlpha = 0.35 + 0.35 * g; fill(c, orb, () => c.arc(0, -32, 6.5 + 2 * g, 0, TAU)); c.restore();
      fill(c, orb, () => c.arc(0, -32, 3.6, 0, TAU));
      fill(c, "rgba(255,255,255,0.8)", () => c.arc(-1.2, -33.2, 1.1, 0, TAU));
    } },
    orb: { len: 6, hold: { side: 0.6, front: 0 }, draw: (c, it) => {
      const orb = it?.color ?? "#a898ff";
      // 法球托在掌心：球心 −3.4，球底貼著手
      const g = pz("glow"), oy = -3.4 + pz("orbY"); // 待機：法球在掌上浮沉（orbY）、光脈動（glow）
      c.save(); c.globalAlpha = 0.35 + 0.35 * g; fill(c, orb, () => c.arc(0, oy, 6 + 2 * g, 0, TAU)); c.restore();
      fill(c, orb, () => c.arc(0, oy, 3.6, 0, TAU));
      fill(c, "rgba(255,255,255,0.8)", () => c.arc(-1.2, oy - 1.2, 1.1, 0, TAU));
    } },
    // 弓：弓把在原點（持弓手包住它），弓臂往 ±x 彎、弓背朝 −y（＝箭的方向），弦在 +y；側面 hold π/2 讓箭朝前；正面 −π/2 弓背朝外
    // 第 3 版前弧心在 (0,9)，弓把其實在 y −4，手離弓身 4 單位（使用者：「弓左邊這隻手沒抓著弓身」）；改成弧心 (0,13)、弓把在原點
    bow: { len: 4, hold: { side: Math.PI / 2, front: -Math.PI / 2 }, draw: (c, it) => {
      const [k] = wc(it, "wood"), pull = typeof POSE?.pull === "number" ? POSE.pull : 0, ex = Math.sin(BOW_A) * BOW_R, ey = BOW_EY;
      c.strokeStyle = "rgba(240,240,240,0.85)"; c.lineWidth = 0.8; c.beginPath(); c.moveTo(-ex, ey); c.lineTo(0, ey + pull); c.lineTo(ex, ey); c.stroke();
      c.strokeStyle = k; c.lineWidth = 2.2; c.lineCap = "round"; c.beginPath(); c.arc(0, BOW_R, BOW_R, -Math.PI / 2 - BOW_A, -Math.PI / 2 + BOW_A); c.stroke();
      fill(c, "#4a3020", () => c.roundRect(-1.6, -1.6, 3.2, 3.2, 0.8)); // 弓把（皮纏）
      if (pull > 0.5) {
        c.strokeStyle = "#c8a070"; c.lineWidth = 0.9; c.beginPath(); c.moveTo(0, ey + pull); c.lineTo(0, -6); c.stroke();
        fill(c, "#c3ccd6", () => { c.moveTo(-1.2, -5.6); c.lineTo(0, -8); c.lineTo(1.2, -5.6); c.closePath(); });
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
  /** 武器掛在手上：在主手手掌（hand）畫武器，a＝武器的世界角度。short：雙手劍用拄劍長度。offL：副手握點（武器座標，自測用）。 */
  function mainWeapon(ctx, it, hand, a, view, short = false, offL = null) {
    const q0 = qWeapon(it), q = q0 && short && q0.kind === "greatsword" ? { ...q0, W: QW.greatsword_k } : q0;
    if (!q) { if (it) PD.drawWeapon(ctx, it, hand[0], view !== "back"); return; }
    ctx.save(); ctx.translate(hand[0], hand[1]); ctx.rotate(a);
    q.W.draw(ctx, q.item);
    if (POSE && POSE.probe) {
      const m = ctx.getTransform(), o = offL;
      POSE.probe(q.kind, m.transformPoint(new DOMPoint(0, 0)), m.transformPoint(new DOMPoint(0, -q.W.len)), view, o ? m.transformPoint(new DOMPoint(o[0], o[1])) : null, m, q.W);
    }
    ctx.restore();
  }

  // ---------- 雙手武器（11-04 晚，使用者：「雙手武器 如弓等 有沒有概念演示圖 不然正面像一把弓懸浮」）----------
  // off＝副手握的點（武器座標：握把原點、作用端 −y）；front＝正面時武器角度（背面左右鏡像）；側面角度照 hold.side 或姿勢的 wpn。
  // 副手已經拿著東西（盾、書）時改回單手握（例：法師拿法杖＋書）。
  const TWO = {
    // pts：武器座標裡除了中軸以外會伸出去的點（弓臂兩端、鐮刃、護手、弩臂），擺位置時一起檢查不能蓋到臉
    greatsword: { off: [0, 4], front: -0.85, pts: [[-4.5, -3], [4.5, -3]], edge: -3, zh: "雙手疊握劍柄" },
    spear: { off: [0, 8], front: -0.75, pts: [], edge: -34, zh: "前後握槍桿，槍尖朝左上" },
    scythe: { off: [0, 6], front: -0.75, pts: [[14, -18], [12, -27], [8, -23.5], [4, -24]], edge: -23, zh: "前後握柄，刃在左上" },
    staff: { off: [0, 6], front: -0.75, pts: [[-6.5, -32], [6.5, -32]], zh: "一上一下握杖身，杖頭朝左上" },
    bow: { off: "string", offAt: -7, range: 1.1, front: -Math.PI / 2, pts: [[-12.1, 8.3], [12.1, 8.3], [-7, 2], [7, 2], [-10, 4.6], [10, 4.6]], zh: "持弓手包住弓把、搭弦手在弦上" },
    crossbow: { off: [0, -6], front: Math.PI - 0.8, pts: [[-8, -8], [8, -8]], zh: "一手握把、一手托弩身，弩口朝右下" },
    gun: { off: [0, -8], front: Math.PI - 0.85, pts: [], zh: "一手握把、一手托槍管，槍口朝右下" },
  };
  // （第 3～4 版的自動擺位求解器 twoPlace 與雙手劍三種姿勢 GSV 已刪掉：武器擺在固定位置、手另外移動，畫面是錯的；改用下面的關鍵姿勢 KEY。）
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
    ctx.save(); ctx.translate(0, -pz("shieldUp")); // 待機：舉盾
    PD.drawWeapon(ctx, it, x, true);
    if (it.kind === "shield_round") { ctx.strokeStyle = RIM; ctx.lineWidth = 0.9; ctx.beginPath(); ctx.arc(x, -13.5, 7.1, 0, TAU); ctx.stroke(); }
    ctx.restore();
  }
  function shieldSide(ctx, it) {
    const [c, d] = colors(it), tower = it.kind === "shield_kite" && it.form === "tower";
    ctx.save(); ctx.translate(8.6, -13.5 - pz("shieldUp")); // 拿在遠側手、舉在胸前：比身體前緣（x 5.4）再往前，近側手臂只蓋到盾的後緣
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
    ctx.save(); ctx.translate(x - 1, -16.5); // 往上、往外移，蓋住副手的袖子與手（背面手在盾的內側）
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

  // ---------- 關鍵姿勢（11-04 晚，使用者：「我不懂ㄟ有這麼難嗎」；專案 PM：武器掛在手上、姿勢不靠 IK 自動解）----------
  // 每一大類、每個方向手調一個關鍵姿勢（像畫 sprite 一樣擺好）：主手的肩角、肘角 m＝[sA, eA]，武器相對手掌的角度 g。
  // 武器的位置與角度一律由主手手掌決定：武器變換 ＝ 主手手掌位置＋旋轉（sA＋eA＋g）。副手再去握第二個握點 og（武器座標），搆不到就放開。
  // 數字是美術 PM 先定好兩手要在哪（例：雙手劍兩手疊在胸前、劍垂直往下），離線算出關節角度後寫死；背面＝正面左右鏡像。
  //   正面肩：主手 (−8.5,−20)、副手 (8.5,−20)；側面肩：近側（主手）(4.5,−20)、遠側（副手）(3,−20)
  const CLASS_OF = { greatsword: "greatsword", spear: "polearm", scythe: "polearm", bow: "bow", crossbow: "gun", gun: "gun", staff: "staff" };
  const KEY = {
    // 劍類（雙手劍）：雙手疊握劍柄在胸前，劍垂直往下，劍尖點在兩腳之間（劍身短 5，Q 版身高 46 原長會插進地面）
    greatsword: { zh: "雙手疊握劍柄在胸前，劍垂直往下、劍尖點在兩腳之間",
      front: { m: [-0.534, -0.91], g: 4.586, og: [0, 3.5] },      // 主手 (−0.5,−15)，副手在上 (−0.5,−18.5)
      side: { m: [0.734, -2.068], g: 4.476, og: [0, 3.5] } },     // 手在胸前 (6.5,−15)，劍尖點在腳前 (6.5,+2)
    // 長柄（長槍、鐮）：正面斜持在胸前，槍尖朝左上越過肩外；側面直立，前手在下、後手在上
    polearm: { zh: "正面斜持：上手在左胸、下手在右腰，槍尖朝左上；側面直立在身前",
      front: { m: [-0.17, -1.963], g: 1.347, og: [0, 9.9] },      // 主手 (−3,−18)、副手 (4,−11)
      side: { m: [0.053, -0.808], g: 0.815, og: [0, -8] } },      // 槍在身前 x 8：近側手 (8,−11)、遠側手在上 (8.5,−19)，在近側手臂外側露得出來
    // 弓：正面持弓手伸向側前方握弓身中段，弓直立偏外側，搭弦手在胸前；側面持弓手垂在身側，弓直立、朝下斜，弦放鬆
    bow: { zh: "正面：持弓手在側前方握弓身中段，搭弦手在胸前；側面：持弓手垂在身側，弓直立朝下斜",
      front: { m: [0.141, -1.01], g: -0.701, og: "string" },       // 持弓手 (−5,−11.5) 握弓身中段、弓直立在身前偏左；搭弦手在胸前 (0.4,−14.5)
      side: { m: [0.247, -0.605], g: 2.278 },                     // 持弓手 (5.2,−10)，弓口朝前下 0.35
      aim: { m: [-1.9, 0], g: Math.PI / 2 + 1.9 } },              // 拉弓：持弓手伸到肩高 (14.4,−23.4)，弓直立，箭水平在下巴高度
    // 弩與槍：正面橫持在胸前、口朝右下，一手握把、一手托；側面口朝前上（持槍待命）
    gun: { zh: "正面橫持在胸前、口朝右下；側面持槍待命、口朝前上，一手握把一手托",
      front: { m: [0, -1.571], g: 3.441, og: [0, -6.8] },          // 握把 (−3,−15)、托在 (3.5,−13)
      side: { m: [0.38, -1.037], g: 1.556, og: [0, -7] } },       // 握把 (6,−11)、托在前上 7
    // 法杖：單手直立握在身側，杖頭在頭旁（副手空著或拿書）
    staff: { zh: "單手握杖直立在身側，杖頭在頭旁",
      front: { m: [0.67, -1.063], g: 0.293 },                      // 手 (−9.5,−11)，杖頭略往外
      side: { m: [-0.3, 0], g: 0.55 } },                           // 手往前 (7.6,−10)，杖身微向前傾，杖身在臉前方外側、不蓋住臉
  };
  function keyOf(gear) {
    const q = qWeapon(gear.main_hand); if (!q) return null;
    const c = CLASS_OF[q.kind]; if (!c) return null;
    if (c !== "staff" && gear.off_hand) return null; // 雙手武器副手有東西就改單手（舊做法）
    return { c, K: KEY[c], kind: q.kind };
  }
  const offLocal = (kind, og) => (og === "string" ? [0, BOW_EY + (typeof POSE?.pull === "number" ? POSE.pull : 0)] : og);
  const frontOffLocal = (og) => (og === "string" ? [3, BOW_EY] : og); // 正面搭弦手握在弦的中段偏下
  let TINT = null; // 自測用：把某一隻手臂塗成指定色，算它露出多少

  // ---------- 整隻：view = front | side | back；west 由 stamp 鏡像 ----------
  // 畫的順序（由後到前）
  //   正面：披風（暗）→ 尾巴 → 腿 → 身體 → 披風扣 → 副手臂＋副手（單手時）→ 頭 → 武器（掛在主手）→ 副手臂 → 主手臂（手蓋住握把）
  //   側面：披風（背後那片）→ 尾巴 → 遠側手臂（握第二握點，或拿書）→ 腿 → 身體 → 披風扣 → 盾 → 頭 → 武器 → 近側手臂
  //   背面：武器與兩隻手臂（都在身體前方＝畫面後）→ 副手物品（盾背、書：蓋住副手的手與袖子）→ 腿 → 身體 → 披風 → 尾巴 → 頭
  function draw(ctx, unit, view) {
    const { look, gear } = unit, F = view === "front", B = view === "back", S = view === "side";
    const side = S ? 1 : 0;
    const R = window.RaceArt;
    const mark = (n) => { if (POSE && POSE.layers) POSE.layers.push(n); };
    const key = keyOf(gear), anim = POSE && typeof POSE.wpn === "number"; // 6M／6N 的攻擊片段給了 wpn：走舊的骨架路徑
    ctx.save();
    if (R) R.build(ctx, look);
    if (look.frame === "slim") ctx.scale(0.92, 1.02); else if (look.frame === "broad") ctx.scale(1.08, 0.98);
    ctx.translate(0, pz("bob"));
    if (S) rotAt(ctx, 0, -9, pz("lean"));
    if (gear.cloak && F) cloakFront(ctx, gear.cloak);
    if (gear.cloak && S) { cloakSide(ctx, gear.cloak); mark("cloak"); }
    if (R && !B) R.tail(ctx, look, F ? "front" : "side", side);
    const short = key && key.c === "greatsword";
    if (B) {
      if (key && key.K.front.og) {
        // 背面雙手：正面左右鏡像，武器和兩隻手都在身體前方（畫在身體後面），只露出伸出身體外的部分
        const k = key.K.front, sA = -k.m[0], eA = -k.m[1], h = fk(8.5, sA, eA), a = -(k.m[0] + k.m[1] + k.g);
        const ol = frontOffLocal(k.og), o = rot(a, [-ol[0], ol[1]]), t = [h[0] + o[0], h[1] + o[1]], io = ik(-8.5, t, -1);
        mainWeapon(ctx, gear.main_hand, h, a, "back", short, [-ol[0], ol[1]]); mark("weapon");
        arm(ctx, unit, -8.5, io.sA, io.eA, 0, rec("off")); arm(ctx, unit, 8.5, sA, eA, 0, rec("main"));
      } else {
        // 背面單手：手在身體前方，手臂往內收 0.3 畫在身體後面，手被擋住（使用者：「拳頭應該看不到或者露一點邊緣」）
        ctx.save(); ctx.translate(0, pz("armR"));
        const rm = rec("main");
        arm(ctx, unit, 8.5, 0.3, 0, 0, (hand, c) => { mainWeapon(ctx, gear.main_hand, hand, -(key && key.c === "staff" ? -0.18 : holdOf(gear.main_hand, "front")) - 0.3, "back"); if (rm) rm(hand, c); });
        ctx.restore(); mark("weapon");
        ctx.save(); ctx.translate(0, pz("armL")); TINT = POSE && POSE.tintOff ? POSE.tintOff : null; arm(ctx, unit, -8.5, gear.off_hand && !isShield(gear.off_hand) ? -0.5 : -0.3, 0, 0, rec("off")); TINT = null; ctx.restore(); // 拿書的手再往內收，前臂藏在身體後面
      }
      mark("arms");
      // 副手物品在手的外側：盾背往上移到蓋住副手的袖子與手；書大部分藏在身體後面，只露一角（使用者：「手又在副武器前面了」）
      if (isShield(gear.off_hand)) { shieldBack(ctx, gear.off_hand, -8.5); mark("shield"); }
      else if (gear.off_hand) { PD.drawWeapon(ctx, gear.off_hand, -5.2, false); mark("shield"); }
    }
    // 側面：先決定近側手（主手）的關節與武器角度，遠側手照著去握第二握點
    let SP = null;
    if (S) {
      if (key && !anim) {
        const aimT = key.c === "bow" ? Math.max(0, Math.min(1, pz("bowAim"))) : 0, k = key.K.side, A2 = key.K.aim;
        const sA = (aimT ? k.m[0] + (A2.m[0] - k.m[0]) * aimT : k.m[0]) + pz("arm"), eA = aimT ? k.m[1] + (A2.m[1] - k.m[1]) * aimT : k.m[1];
        const g = (aimT ? k.g + (A2.g - k.g) * aimT : k.g) + pz("dw");
        SP = { sA, eA, a: sA + eA + g, og: key.c === "bow" ? (aimT > 0.5 || pz("pull") > 0.5 ? "string" : null) : k.og };
      } else {
        const a = pz("arm"), eA = Math.min(0, a * 0.35), w = anim ? POSE.wpn : holdOf(gear.main_hand, "side");
        // 6M／6N 片段的規則：武器角度 ＝ 手臂角度＋wpn（同 C 版 storyDoll），手肘彎曲不影響武器朝向
        //   （第 2～4 版把肘角也加進去，弩、火槍瞄準時槍口往上翹約 26°，11-04 晚看出招特寫時抓到）
        SP = { sA: a, eA, a: a + w, og: null };
      }
      SP.h = fk(4.5, SP.sA, SP.eA);
      let done = false;
      if (SP.og) {
        const ol = offLocal(key.kind, SP.og), o = rot(SP.a, ol), t = [SP.h[0] + o[0], SP.h[1] + o[1]], k = ik(3, t, -1);
        if (k.ok) { arm(ctx, unit, 3, k.sA, k.eA, side, rec("off")); if (POSE && POSE.hands) POSE.hands.offTwo = true; SP.ol = ol; done = true; }
      }
      if (!done) arm(ctx, unit, -4.5, pz("armL") * 0.6 - 0.1, 0.15, side, gear.off_hand && !isShield(gear.off_hand) ? (hand) => PD.drawWeapon(ctx, gear.off_hand, hand[0], true) : null);
    }
    leg(ctx, look, gear.feet, -1, pz("hipF"), pz("kneeF"), pz("liftL"), side);
    leg(ctx, look, gear.feet, 1, pz("hipN"), pz("kneeN"), pz("liftR"), side);
    body(ctx, gear.body, look, side, B); mark("body");
    if (S) { cloakClasp(ctx, gear.cloak, true); if (isShield(gear.off_hand)) shieldSide(ctx, gear.off_hand); }
    if (B) {
      if (gear.cloak) { cloakBack(ctx, gear.cloak); mark("cloak"); }
      if (R) R.tail(ctx, look, "back", 0);
    }
    if (F && gear.cloak) cloakClasp(ctx, gear.cloak, false);
    const twoF = F && key && key.K.front.og;
    if (F && !twoF) {
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
    if (F && key) {
      // 正面關鍵姿勢：武器掛在主手手掌，副手臂、主手臂蓋在武器上（手握住握把）
      const k = key.K.front, h = fk(-8.5, k.m[0], k.m[1]), a = k.m[0] + k.m[1] + k.g, ol = k.og ? frontOffLocal(k.og) : null;
      mainWeapon(ctx, gear.main_hand, h, a, "front", short, ol);
      if (ol) { const o = rot(a, ol), io = ik(8.5, [h[0] + o[0], h[1] + o[1]], 1); arm(ctx, unit, 8.5, io.sA, io.eA, 0, rec("off")); }
      arm(ctx, unit, -8.5, k.m[0], k.m[1], 0, rec("main"));
    } else if (F) {
      const rm = rec("main");
      ctx.save(); ctx.translate(0, pz("armL")); arm(ctx, unit, -8.5, 0, 0, 0, (hand, c) => { mainWeapon(ctx, gear.main_hand, hand, holdOf(gear.main_hand, "front"), "front"); if (rm) rm(hand, c); }); ctx.restore();
    } else if (S) {
      // 近側手：武器掛在手掌（武器先畫，手臂蓋上去）
      mainWeapon(ctx, gear.main_hand, SP.h, SP.a, "side", short, SP.ol ?? null);
      arm(ctx, unit, 4.5, SP.sA, SP.eA, side, rec("main"));
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
    // 雙手武器：正面、背面兩隻手都在握把上（主手在握把原點、副手在副手握點，誤差 < 0.6）；側面靜止另外列出（只報告）。只當輔助，畫面要放大親眼看
    const near = (a, b) => !!a && !!b && Math.hypot(a[0] - b[0], a[1] - b[1]) < 0.6;
    rows.two = [];
    for (const kind of [...Object.keys(A.WEAPONS).filter((k) => CLASS_OF[k] && KEY[CLASS_OF[k]].front.og), "greatsword"]) {
      const r = { kind, zh: A.WEAPON_ZH[kind] ?? "雙手劍", how: KEY[CLASS_OF[kind]].zh };
      for (const [dir, view, west] of [["south", "front", false], ["north", "back", false], ["east", "side", false]]) {
        const g = probe(kind, view, west, A.REST);
        r[dir] = !!g && near(g.hands.main, g.hand) && near(g.hands.off, g.off);
      }
      rows.two.push(r);
    }
    rows.hands = handTest();
    rows.grip = gripTest();
    rows.cross = crossTest();
    rows.offArm = offArmTest();
    return rows;
  }
  // 手在握把上（像素）：把武器單獨畫一次（同一個變換），手心 ±1 單位內要有武器的像素；主手、雙手武器的副手都查
  //   （第 3 版弓的手離弓把 4 單位，這項會抓到；只查圖層或座標抓不到）
  const K_T = 4, O_T = [160, 240];
  function weaponOnly(W, item, m, pull = 0) {
    const C = document.createElement("canvas"); C.width = 320; C.height = 320;
    const c = C.getContext("2d", { willReadFrequently: true });
    c.setTransform(K_T, 0, 0, K_T, O_T[0], O_T[1]); c.transform(m.a, m.b, m.c, m.d, m.e, m.f);
    const keep = POSE; POSE = { pull }; W.draw(c, item); POSE = keep;
    return c;
  }
  const alphaAt = (c, [x, y]) => c.getImageData(Math.round(O_T[0] + x * K_T), Math.round(O_T[1] + y * K_T), 1, 1).data[3];
  const touches = (c, h) => !!h && [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1], [0.7, 0.7], [-0.7, 0.7], [0.7, -0.7], [-0.7, -0.7]].some(([dx, dy]) => alphaAt(c, [h[0] + dx, h[1] + dy]) > 0);
  function gripTest() {
    const A = window.Anim, C0 = document.createElement("canvas"), ctx = C0.getContext("2d"), out = [];
    const kinds = [...Object.keys(A.WEAPONS), "greatsword"];
    for (const k of kinds) {
      const kind = k;
      const r = { kind: k, zh: A.WEAPON_ZH[kind] ?? "雙手劍" };
      for (const [dir, view] of [["south", "front"], ["north", "back"], ["east", "side"]]) {
        let got = null; const hands = {};
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        POSE = { ...A.REST, wpn: undefined, hands, probe: (kk, h, tp, vv, o, m, W) => { got = { m, W }; } };
        draw(ctx, A.unit(kind), view); POSE = null;
        if (!got) { r[dir] = { ok: false, t: "沒畫" }; continue; }
        const q = qWeapon({ kind }), wc2 = weaponOnly(got.W, q.item, got.m);
        const kc = CLASS_OF[kind], twoKey = kc && KEY[kc].front.og;
        const okM = touches(wc2, hands.main), twoHere = twoKey && hands.off && (view !== "side" || hands.offTwo);
        const okO = twoHere ? touches(wc2, hands.off) : true;
        r[dir] = { ok: okM && okO, t: `主手${okM ? "握住" : "沒握到"}${twoHere ? `・副手${okO ? "握住" : "沒握到"}` : ""}` };
      }
      r.pass = r.south.ok && r.north.ok && r.east.ok;
      out.push(r);
    }
    return out;
  }
  // 刃不被手臂蓋住（像素，正面）：只畫刃（握柄以外），再和整隻畫出來的圖比，刃的像素被別的顏色蓋掉 ≤ 3%
  function crossTest() {
    const out = [];
    for (const kind of ["greatsword", "spear", "scythe"]) out.push(crossOne(kind));
    return out;
  }
  function crossOne(kind) {
    const A = window.Anim;
    const C = document.createElement("canvas"); C.width = 320; C.height = 320;
    const ctx = C.getContext("2d", { willReadFrequently: true });
    ctx.setTransform(K_T, 0, 0, K_T, O_T[0], O_T[1]);
    let got = null;
    POSE = { ...A.REST, wpn: undefined, probe: (kk, h, tp, vv, o, m, W) => { got = { m, W }; } };
    draw(ctx, A.unit(kind), "front"); POSE = null;
    const edge = TWO[kind].edge, zh = A.WEAPON_ZH[kind] ?? "雙手劍";
    if (!got) return { zh, ok: false, t: "沒畫" };
    // 只畫刃：在武器座標裡把 y > edge 的部分（握柄、桿）裁掉
    const m = got.m, B = document.createElement("canvas"); B.width = 320; B.height = 320;
    const b = B.getContext("2d", { willReadFrequently: true });
    b.setTransform(m.a, m.b, m.c, m.d, m.e, m.f); // probe 的矩陣已含放大與位移
    b.beginPath(); b.rect(-30, -60, 60, 60 + edge); b.clip();
    got.W.draw(b, qWeapon({ kind }).item);
    const bd = b.getImageData(0, 0, 320, 320).data, fd = ctx.getImageData(0, 0, 320, 320).data;
    let n = 0, cov = 0;
    for (let i = 0; i < bd.length; i += 4) if (bd[i + 3] === 255) { n++; if (Math.abs(bd[i] - fd[i]) + Math.abs(bd[i + 1] - fd[i + 1]) + Math.abs(bd[i + 2] - fd[i + 2]) > 30) cov++; }
    const pct = n ? (cov / n) * 100 : 100;
    return { zh, ok: n > 0 && pct <= 3, t: `刃被蓋 ${pct.toFixed(1)}%` };
  }
  // 背面副手手臂（像素）：把副手那隻手臂塗成洋紅，整隻畫完後數手肘（y −16）以下還看得到的洋紅像素：前臂和手露出 ≤ 2 單位²（最多一點指節）。
  //   拿盾時整隻手臂都算（盾要蓋住）；拿書時肩頭不算：兩邊肩頭是身體輪廓，主手那側也一樣露著
  //   （11-04 晚：使用者「手又在副武器前面了」；舊的「背面手被擋住」只查手心，沒查整隻手臂，所以沒抓到）
  function offArmTest() {
    const TPL = PD.TEMPLATES, IT = PD.ITEMS, out = [];
    const cases = [["劍盾（圓盾）", TPL.hero_fighter], ["鳶盾", TPL.bandit_shieldbearer], ["法師（書）", TPL.hero_mage], ["聖盾", { look: TPL.hero_fighter.look, gear: { ...TPL.hero_fighter.gear, off_hand: IT.holy_shield, cloak: undefined } }], ["塔盾", { look: TPL.bandit.look, gear: { ...TPL.bandit.gear, off_hand: { slot: "off_hand", kind: "shield_kite", form: "tower", material: "wood", color: "#6a4a2e" } } }], ["劍盾（無披風）", { look: TPL.hero_fighter.look, gear: { ...TPL.hero_fighter.gear, cloak: undefined } }]];
    for (const [zh, u] of cases) {
      const K = 4, C = document.createElement("canvas"); C.width = C.height = 256;
      const ctx = C.getContext("2d", { willReadFrequently: true });
      ctx.setTransform(K, 0, 0, K, 128, 220);
      POSE = { tintOff: "#ff00ff" }; draw(ctx, u, "back"); POSE = null;
      // 拿盾：盾要蓋住整隻副手（整隻手臂都算）；拿書：書小，只算手肘以下（前臂與手）
      const sh = isShield(u.gear.off_hand), y0 = sh ? 0 : Math.round(220 - 16 * K), d = ctx.getImageData(0, y0, 256, 256 - y0).data; let n = 0;
      for (let i = 0; i < d.length; i += 4) if (d[i] === 255 && d[i + 1] === 0 && d[i + 2] === 255) n++;
      const area = n / (K * K);
      out.push({ zh, ok: area <= 2, t: `${sh ? "整隻副手" : "前臂與手"}露出 ${area.toFixed(1)} 單位²` });
    }
    return out;
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
  return { draw, stamp, setPose: (p) => { POSE = p; }, selfTest, QW, TWO, KEY, CLASS_OF, fk, rot, BOW_EY };
})();
