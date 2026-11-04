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
      else if (kind === "leather") { const k = back ? -1 : 1; ctx.strokeStyle = d; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(-5 * k, -20); ctx.lineTo(5 * k, -11); ctx.stroke(); } // 斜背帶：右肩到左腰；背面右肩在畫面右，斜向和正面相反（第 7 版）
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
    if (!handOnly && gear.hands && gear.hands.kind === "bracers") { const [bc, bd] = colors(gear.hands); fill(ctx, TINT ?? bc, () => rr(ctx, x - 2.3, -12.6, 4.6, 2.4, 0.8)); fill(ctx, TINT ?? bd, () => ctx.rect(x - 2.3, -11.2, 4.6, 0.6)); } // 護腕：四方向都跟著前臂
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
    if (st === "mustache") for (const s2 of side ? [1] : [-1, 1]) fill(ctx, c, () => { ctx.moveTo(ex, -25.6); ctx.quadraticCurveTo(ex + s2 * 2.8, -26.6, ex + s2 * 3.9, -24.1); ctx.quadraticCurveTo(ex + s2 * 2, -24.9, ex, -24.7); ctx.closePath(); });
  }
  // 頭後面的頭髮（長髮後片、馬尾、雙馬尾）：正面、側面畫在臉之前（被頭擋住一部分）
  // 側面（朝東）：長髮只從耳後往後垂，不在臉前面（11-04 晚，使用者：「我快哭了 這頭髮還要我講」）
  function hairBehind(ctx, look, view, headgear) {
    if (!look.hair || look.hair === "none" || look.skull || view === "back" || headgear?.kind === "hood") return;
    const c = look.hairColor ?? "#5a3a22", band = look.bunBand ?? "#d23c3c", S = view === "side";
    if (S && look.hair === "long") fill(ctx, c, () => rr(ctx, -10, -32, 7.2, 14.5, 2.6)); // 側面長髮：後腦垂到肩後
    if (look.hair === "twin") for (const s2 of S ? [-1] : [-1, 1]) {
      const x = S ? -6.5 : s2 * 9.6;
      fill(ctx, c, () => { ctx.moveTo(x - 1.6, -32); ctx.quadraticCurveTo(x + s2 * 3.4, -26, x + s2 * 1.6, -17.5); ctx.quadraticCurveTo(x - s2 * 0.6, -21, x - s2 * 2, -27); ctx.closePath(); });
      fill(ctx, band, () => ctx.arc(x, -30.6, 1.3, 0, TAU));
    }
    if (look.hair === "ponytail") {
      if (S) { fill(ctx, c, () => { ctx.moveTo(-6, -34); ctx.quadraticCurveTo(-13.5, -32, -12, -20.5); ctx.quadraticCurveTo(-10, -26, -7, -28.5); ctx.closePath(); }); fill(ctx, band, () => ctx.arc(-7.4, -32.4, 1.3, 0, TAU)); }
      else fill(ctx, c, () => { ctx.moveTo(6.5, -35); ctx.quadraticCurveTo(12.5, -31, 10.5, -21); ctx.quadraticCurveTo(9.5, -27, 6, -30); ctx.closePath(); });
    }
  }
  // ---------- 頭：正面照舊版；側面是側臉（前半臉：一隻眼、鼻尖、腮紅；後半與後腦是頭髮，後腦露出耳朵）；背面整顆是頭髮 ----------
  function head(ctx, look, view, side, gear) {
    const skin = look.skin, S = view === "side";
    hairBehind(ctx, look, view, gear.head);
    fill(ctx, skin, () => headShape(ctx, look));
    if (view === "back") { PD_hair(ctx, look, "back", gear.head); return; }
    if (S) {
      // 側臉：鼻尖（往前凸一點，剪影外框會描出鼻子）、耳朵在後腦（頭髮會蓋住上緣）
      fill(ctx, skin, () => ctx.ellipse(8.45, -27.1, 1.25, 1.05, 0, 0, TAU));
      fill(ctx, skin, () => ctx.ellipse(-1.2, -28.2, 1.7, 2.3, 0, 0, TAU));
      fill(ctx, mix(skin, "#000000", 0.18), () => ctx.ellipse(-1.0, -28.1, 0.7, 1.2, 0, 0, TAU));
    }
    const ex = side * 3.2;
    eyes(ctx, look, side, ex);
    ctx.fillStyle = "rgba(220,90,90,0.35)";
    if (S) ctx.fillRect(3.4, -26.3, 2.2, 1.2); // 側面腮紅在眼睛下方偏後
    else { ctx.fillRect(ex - 5, -26.5, 2, 1.2); ctx.fillRect(ex + 3, -26.5, 2, 1.2); }
    const L = look.beardStyle ? { ...look, beard: look.beardStyle === "full" } : look;
    if (window.RaceArt) window.RaceArt.face(ctx, L, S ? "side" : view, side, S && WEST);
    beard(ctx, look, side);
    PD_hair(ctx, look, S ? "side" : "front", gear.head);
  }
  function PD_hair(ctx, look, view, headgear) {
    if (!look.hair || look.hair === "none" || look.skull) return; // 光頭：不畫頭髮（舊版把 "none" 當成有頭髮）
    const c = look.hairColor ?? "#5a3a22", band = look.bunBand ?? "#d23c3c";
    const covered = headgear && ["helmet", "hood", "wizard_hat", "horned_helm", "greathelm", "cap"].includes(headgear.kind);
    if (view === "back") {
      fill(ctx, c, () => { ctx.beginPath(); ctx.arc(0, -29, 8.8, 0, TAU); });
      if (look.hair === "long") fill(ctx, c, () => rr(ctx, -7, -29, 14, 10, 3));
      if (look.hair === "bob") fill(ctx, c, () => rr(ctx, -8.8, -30, 17.6, 8.5, 3.5));
      if (look.hair === "ponytail" && headgear?.kind !== "hood") { fill(ctx, c, () => rr(ctx, -2, -32, 4, 17.5, 2)); /* 第 7 版：馬尾垂過後頸，背面看得到 */ fill(ctx, band, () => rr(ctx, -2.3, -32, 4.6, 1.6, 0.8)); }
      if (look.hair === "twin" && headgear?.kind !== "hood") for (const s2 of [-1, 1]) { fill(ctx, c, () => { ctx.moveTo(s2 * 8, -32); ctx.quadraticCurveTo(s2 * 13, -26, s2 * 11, -17.5); ctx.quadraticCurveTo(s2 * 9.5, -22, s2 * 6.5, -28); ctx.closePath(); }); fill(ctx, band, () => ctx.arc(s2 * 8.6, -30.8, 1.3, 0, TAU)); }
      if (look.hair === "spiky" && !covered) fill(ctx, c, () => { for (let i = 0; i < 7; i++) { const a = Math.PI * (1.05 + i * 0.15); ctx.moveTo(Math.cos(a - 0.08) * 8.4, -29 + Math.sin(a - 0.08) * 8.4); ctx.lineTo(Math.cos(a) * 11.6, -29 + Math.sin(a) * 11.6); ctx.lineTo(Math.cos(a + 0.08) * 8.4, -29 + Math.sin(a + 0.08) * 8.4); } });
      if (look.hair === "bun" && !covered) fill(ctx, look.bunBand ?? c, () => ctx.arc(0, -37, 3, 0, TAU));
      return;
    }
    if (view === "side") {
      // 側面（朝東）：頭髮蓋住頭頂和後半顆頭，前緣在額頭；耳朵前面不畫頭髮（短髮露耳）
      if (!covered) fill(ctx, c, () => {
        ctx.moveTo(8.3, -32.6); ctx.quadraticCurveTo(6.2, -38.8, -0.8, -38.6); ctx.quadraticCurveTo(-9.4, -37.6, -9.3, -29.2);
        ctx.quadraticCurveTo(-9.2, -24, -6.4, -21.6); ctx.lineTo(-3.4, -22.6); ctx.quadraticCurveTo(-3.6, -27.5, -2.6, -31.2);
        ctx.quadraticCurveTo(2.5, -33.6, 6.2, -32.4); ctx.lineTo(7.4, -31.2); ctx.closePath();
      });
      if (covered) fill(ctx, c, () => { ctx.moveTo(-9.3, -29); ctx.quadraticCurveTo(-9.2, -24, -6.4, -21.6); ctx.lineTo(-3.4, -22.6); ctx.quadraticCurveTo(-4, -26, -4, -29); ctx.closePath(); }); // 帽子下露出的後髮
      if (look.hair === "long") fill(ctx, c, () => { ctx.moveTo(-3.4, -31); ctx.quadraticCurveTo(-1.5, -24, -3.2, -19.5); ctx.lineTo(-9.6, -19.5); ctx.lineTo(-9.4, -30); ctx.closePath(); }); // 長髮蓋住耳朵、垂在耳後
      if (look.hair === "bob") fill(ctx, c, () => { ctx.moveTo(-2.4, -31.5); ctx.quadraticCurveTo(-0.6, -25.5, -1.8, -22); ctx.lineTo(-9.4, -22.4); ctx.lineTo(-9.4, -30); ctx.closePath(); });
      if (look.hair === "spiky" && !covered) fill(ctx, c, () => { for (let i = 0; i < 6; i++) { const a = Math.PI * (1.0 + i * 0.13); ctx.moveTo(Math.cos(a - 0.09) * 8.6 - 0.8, -29.8 + Math.sin(a - 0.09) * 8.6); ctx.lineTo(Math.cos(a) * 12 - 1.6, -29.8 + Math.sin(a) * 12); ctx.lineTo(Math.cos(a + 0.09) * 8.6 - 0.8, -29.8 + Math.sin(a + 0.09) * 8.6); } });
      if (look.hair === "bun" && !covered) fill(ctx, look.bunBand ?? c, () => ctx.arc(-5.6, -36, 3, 0, TAU));
      // 雙馬尾側面（第 7 版）：近側那束從耳後上方綁起、往後下垂，髮圈露在外面（和長髮分得開）
      if (look.hair === "twin" && headgear?.kind !== "hood") { fill(ctx, c, () => { ctx.moveTo(-7.6, -33); ctx.quadraticCurveTo(-14, -29, -12.4, -19); ctx.quadraticCurveTo(-10.6, -24, -8.2, -28.6); ctx.closePath(); }); fill(ctx, look.bunBand ?? "#d23c3c", () => ctx.arc(-8.4, -31.4, 1.4, 0, TAU)); }
      return;
    }
    if (!covered) fill(ctx, c, () => { ctx.beginPath(); ctx.arc(0, -29.5, 8.8, Math.PI * 1.02, Math.PI * 1.98); ctx.quadraticCurveTo(4, -33, 0, -32.5); ctx.quadraticCurveTo(-5, -32, -8.8, -29); ctx.closePath(); });
    if (look.hair === "long") { fill(ctx, c, () => rr(ctx, -9.5, -31, 3, 11, 1.5)); fill(ctx, c, () => rr(ctx, 6.5, -31, 3, 11, 1.5)); }
    if (look.hair === "bob") { fill(ctx, c, () => rr(ctx, -9.6, -31.5, 3.4, 8.8, 1.7)); fill(ctx, c, () => rr(ctx, 6.2, -31.5, 3.4, 8.8, 1.7)); }
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
    sword: { len: 19, hold: { side: 0.75, front: -0.12 }, draw: (c, it) => sword(c, it, 16, 2.6) },
    greatsword: { len: 27, hold: { side: 0.75, front: -0.25 }, draw: (c, it) => sword(c, it, 24, 4) },
    // 拄劍用的雙手劍：劍身短 5（Q 版身高 46，原長劍尖會穿過地面太多；使用者：「垂直 劍尖指地也可以但可能長度或高度不構」）
    // 拄劍（關鍵姿勢）用的雙手劍：劍身 14，劍尖剛好點在兩腳之間
    greatsword_k: { len: 17, hold: { side: 0.75, front: -0.25 }, draw: (c, it) => sword(c, it, 14, 4) },
    arcane_blade: { len: 19, hold: { side: 0.75, front: -0.12 }, draw: (c, it) => sword(c, { ...it, form: "arcane" }, 16, 2.6) },
    saber: { len: 19, hold: { side: 0.75, front: -0.12 }, draw: (c, it) => {
      const [k] = wc(it, "steel");
      fill(c, k, () => { c.moveTo(-1.3, -3); c.quadraticCurveTo(-2.2, -12, 0.6, -19); c.lineTo(1.9, -18.4); c.quadraticCurveTo(0.6, -11, 1.3, -3); c.closePath(); });
      fill(c, "rgba(255,255,255,0.45)", () => { c.moveTo(-0.6, -4); c.quadraticCurveTo(-1.3, -11, 0.4, -16.5); c.lineTo(0.8, -16.3); c.quadraticCurveTo(-0.3, -11, 0.2, -4); c.closePath(); });
      fill(c, "#8a6a2a", () => c.ellipse(0, -3, 3.4, 1.4, 0, 0, TAU));
      fill(c, "#3a2a1a", () => c.rect(-1, -2, 2, 4.2));
    } },
    dagger: { len: 10, hold: { side: 0.75, front: -0.6 }, draw: dagger },
    paired: { len: 10, hold: { side: 0.75, front: -0.45 }, draw: dagger }, // 成對武器：一手一把（第二把在副手，offDagger）
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
        // 待機（第 7 版）：鞭身從握把頂端垂下來（照畫面的「下」，不跟著握把的角度往上翹；審查：「鞭身往上翹，沒有垂下來」），鞭梢在腳邊小幅甩動
        // 畫布方向 → 握把座標：下＝(0,1)；角色前方＝朝東 (1,0)、朝西 (−1,0)（stamp 鏡像）
        const m = c.getTransform(), det = m.a * m.d - m.b * m.c, loc = (x, y) => { const v = [(m.d * x - m.c * y) / det, (-m.b * x + m.a * y) / det], l = Math.hypot(v[0], v[1]) || 1; return [v[0] / l, v[1] / l]; };
        const D = loc(0, 1), N = loc(WEST ? -1 : 1, 0); // 鞭身先垂下，鞭梢在腳前的地上往前捲
        const w = Math.sin(pz("lash") * TAU) * 2.2, at = (u, v) => [u * D[0] + v * N[0], -5 + u * D[1] + v * N[1]];
        const p1 = at(-1.5, 1), p2 = at(7, -1 + w * 0.3), p3 = at(13, 1.5 + w * 0.5), p4 = at(14.5, 6 + w);
        c.beginPath(); c.moveTo(0, -5); c.bezierCurveTo(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1]); c.stroke();
        c.lineWidth = 0.8; c.beginPath(); c.moveTo(p3[0], p3[1]); c.quadraticCurveTo(...at(14.8, 3.5 + w), p4[0], p4[1]); c.stroke();
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
      if (pull > 0.5 || pz("nock") > 0) { // 拉弓，或待機時箭搭在弦上
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
  function mainWeapon(ctx, it, hand, a, view, short = false, offL = null, mg = 0) {
    const q0 = qWeapon(it), q = q0 && short && q0.kind === "greatsword" ? { ...q0, W: QW.greatsword_k } : q0;
    if (!q) { if (it) PD.drawWeapon(ctx, it, hand[0], view !== "back"); return; }
    ctx.save(); ctx.translate(hand[0], hand[1]); ctx.rotate(a);
    if (mg) ctx.translate(0, -mg); // 主手握在武器座標 (0,mg)（扛肩握柄尾）
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
    } else if (it.form === "tower") {
      // 塔盾背面：高的長方形（第 7 版；審查：「塔盾背面畫成鳶盾」）
      fill(ctx, d, () => rr(ctx, -7, -6, 14, 22, 1.5)); fill(ctx, wood, () => rr(ctx, -5.6, -4.6, 11.2, 19.2, 1));
    } else {
      fill(ctx, d, () => { ctx.moveTo(-7, -4); ctx.lineTo(7, -4); ctx.lineTo(6.5, 7); ctx.lineTo(0, 15); ctx.lineTo(-6.5, 7); ctx.closePath(); });
      fill(ctx, wood, () => { ctx.moveTo(-5.5, -2.5); ctx.lineTo(5.5, -2.5); ctx.lineTo(5, 6.5); ctx.lineTo(0, 12.8); ctx.lineTo(-5, 6.5); ctx.closePath(); });
    }
    fill(ctx, strap, () => ctx.rect(-4.5, -1.6, 9, 1.6)); fill(ctx, strap, () => ctx.rect(-4.5, 2.4, 9, 1.6));
    ctx.restore();
  }
  const isShield = (it) => !!it && String(it.kind).startsWith("shield");

  // ---------- 配件 × 四方向（11-04 晚，使用者：「還有其他物件都要考慮4面」；對照表 docs/art/部件四方向清單.md）----------
  // 座標：正面、背面照畫面；側面一律用「朝東」的座標畫（朝西由 stamp 鏡像），但左右手、左右腰的「近側／遠側」照真人互換（WEST）。
  //   角色的右手、右肩、右腰：正面在畫面左、背面在畫面右、朝東在近側、朝西在遠側。
  // 背掛（gear.back）：quiver 箭袋（右肩出口，斜背到左腰）、backpack 背包、scroll_case 卷軸筒
  function backItem(ctx, it, view, layer) {
    if (!it) return;
    const [c, d] = colors(it), S = view === "side", B = view === "back", F = view === "front";
    const strap = it.strap ?? "#4a3020";
    if (it.kind === "quiver" || it.kind === "scroll_case") {
      const tube = it.kind === "scroll_case";
      if (F) {
        if (layer === "behind") { // 正面：箭袋在背後，只露出右肩（畫面左）上方的箭羽／筒蓋
          ctx.save(); ctx.translate(-5.5, -23); ctx.rotate(-0.5);
          if (tube) fill(ctx, d, () => rr(ctx, -2, -4, 4, 4, 1.2));
          else for (const [x, col] of [[-1.4, "#e8e0c8"], [0.2, "#d23c3c"], [1.6, "#e8e0c8"]]) fill(ctx, col, () => { ctx.moveTo(x - 0.7, 0); ctx.lineTo(x, -4.2); ctx.lineTo(x + 0.7, 0); ctx.closePath(); });
          ctx.restore();
        } else { ctx.strokeStyle = strap; ctx.lineWidth = 1.3; ctx.beginPath(); ctx.moveTo(-6.2, -20.6); ctx.lineTo(6.6, -9.8); ctx.stroke(); } // 胸前斜背帶（右肩到左腰）
        return;
      }
      if (B) {
        if (layer !== "over") return; // 背面：整個箭袋在背上，右肩（畫面右）是出口
        ctx.save(); ctx.translate(1.5, -15); ctx.rotate(0.5);
        fill(ctx, c, () => rr(ctx, -2.6, -9, 5.2, 15, 1.8)); fill(ctx, d, () => ctx.rect(-2.6, -2, 5.2, 1.2)); fill(ctx, d, () => ctx.rect(-2.6, 3, 5.2, 1.2));
        if (tube) fill(ctx, d, () => rr(ctx, -3, -11, 6, 3, 1.2));
        else for (const [x, col] of [[-1.4, "#e8e0c8"], [0.2, "#d23c3c"], [1.6, "#e8e0c8"]]) fill(ctx, col, () => { ctx.moveTo(x - 0.7, -9); ctx.lineTo(x, -13.5); ctx.lineTo(x + 0.7, -9); ctx.closePath(); });
        ctx.restore();
        return;
      }
      if (S && layer === "behind") { // 側面：箭袋在背後，出口在肩後上方，箭羽露在後腦旁
        ctx.save(); ctx.translate(-5.6, -15.5); ctx.rotate(WEST ? -0.35 : -0.55);
        fill(ctx, c, () => rr(ctx, -2.4, -9, 4.8, 14, 1.8)); fill(ctx, d, () => ctx.rect(-2.4, -1.5, 4.8, 1.2));
        if (tube) fill(ctx, d, () => rr(ctx, -2.8, -11, 5.6, 3, 1.2));
        else for (const [x, col] of [[-1.3, "#e8e0c8"], [0.2, "#d23c3c"], [1.5, "#e8e0c8"]]) fill(ctx, col, () => { ctx.moveTo(x - 0.7, -9); ctx.lineTo(x, -13.2); ctx.lineTo(x + 0.7, -9); ctx.closePath(); });
        ctx.restore();
      }
      if (S && layer === "over") { ctx.strokeStyle = strap; ctx.lineWidth = 1.3; ctx.beginPath(); ctx.moveTo(WEST ? 1.5 : -1.5, -20.8); ctx.lineTo(WEST ? -3.5 : 4.6, -11); ctx.stroke(); } // 朝東：背帶從近側右肩斜過胸前；朝西：遠側，只看到背帶從後肩繞過
      return;
    }
    if (it.kind === "backpack") {
      if (F) { if (layer === "over") for (const x of [-4.8, 4.8]) fill(ctx, strap, () => rr(ctx, x - 0.9, -21, 1.8, 10, 0.8)); return; } // 正面：兩條肩帶
      if (B) { if (layer === "over") { fill(ctx, c, () => rr(ctx, -6, -20.5, 12, 11, 2.5)); fill(ctx, d, () => rr(ctx, -6, -20.5, 12, 4, 2)); fill(ctx, "#d8b04a", () => ctx.rect(-0.8, -17, 1.6, 1.6)); } return; } // 背面：背包本體＋蓋
      if (S && layer === "behind") { fill(ctx, c, () => rr(ctx, -9.6, -20.5, 5.6, 11, 2)); fill(ctx, d, () => rr(ctx, -9.6, -20.5, 5.6, 3.5, 1.6)); } // 側面：背包在背後凸出
      if (S && layer === "over") fill(ctx, strap, () => rr(ctx, -1.6, -21, 1.8, 9, 0.8)); // 側面：肩帶在肩上
    }
  }
  // 腰掛（gear.waist）：scabbard 劍鞘（左腰，斜往後下）、pouch 腰包（右腰）
  function waistItem(ctx, it, view, layer) {
    if (!it) return;
    const [c, d] = colors(it), S = view === "side", B = view === "back", F = view === "front";
    const left = it.kind === "scabbard"; // 劍鞘在左腰，腰包在右腰
    // 這一側在畫面的哪裡：正面左腰＝畫面右；背面左腰＝畫面左；側面朝東左腰在遠側、朝西左腰在近側
    const near = S ? (left ? WEST : !WEST) : true;
    if (S && (layer === "behind") !== !near) return; // 遠側的畫在身體前（被擋），近側的畫在身體後（蓋在上面）
    if (!S && layer !== "over") return;
    const x = F ? (left ? 7.2 : -7.2) : B ? (left ? -7.2 : 7.2) : 0;
    if (it.kind === "scabbard") {
      ctx.save();
      // 第 7 版：側面鞘口在腰側、鞘尖往後下（審查：「鞘尖朝前」）；正面、背面鞘尖斜往外下、不壓在腿上，也不穿過地面（長 11）
      if (S) { ctx.translate(-0.5, -9.5); ctx.rotate(0.95); } else { ctx.translate(x, -9.5); ctx.rotate((F ? -1 : 1) * (left ? 0.45 : -0.45)); }
      fill(ctx, c, () => rr(ctx, -1.5, 0, 3, 11, 1.4)); fill(ctx, d, () => ctx.rect(-1.5, 8.5, 3, 2.5)); fill(ctx, "#d8b04a", () => ctx.rect(-1.7, 0, 3.4, 1.4)); // 鞘身、鞘尾、鞘口
      ctx.restore();
      return;
    }
    if (it.kind === "pouch") {
      const px = S ? 0.2 : x * 0.64; // 第 7 版：往腰帶中間移，不被垂下的手臂整個蓋住（正面、背面在 ±4.6，側面在腰側）
      fill(ctx, c, () => rr(ctx, px - 2.2, -9.2, 4.4, 4.6, 1.4)); fill(ctx, d, () => rr(ctx, px - 2.2, -9.2, 4.4, 1.8, 1));
    }
  }
  // 頸飾（gear.neck）：necklace 項鍊（墜子在胸前）、beads 念珠
  function neckItem(ctx, it, view) {
    if (!it) return;
    const [c] = colors(it), S = view === "side", B = view === "back";
    const bead = it.kind === "beads";
    if (B) { ctx.strokeStyle = c; ctx.lineWidth = 0.8; ctx.beginPath(); ctx.moveTo(-3.5, -20.8); ctx.quadraticCurveTo(0, -20.2, 3.5, -20.8); ctx.stroke(); return; } // 背面：只看到頸後一小段
    if (S) {
      ctx.strokeStyle = c; ctx.lineWidth = 0.8; ctx.beginPath(); ctx.moveTo(-1.5, -20.8); ctx.quadraticCurveTo(3.8, -17.6, 5.4, -18.4); ctx.stroke();
      fill(ctx, bead ? c : "#e8bb48", () => ctx.ellipse(5.4, -17.4, 1, 1.3, 0, 0, TAU)); // 墜子在胸前前緣
      return;
    }
    if (bead) for (let i = 0; i <= 6; i++) { const t = i / 6, bx = -4.5 + 9 * t, by = -20.5 + 4.2 * Math.sin(t * Math.PI); fill(ctx, c, () => ctx.arc(bx, by, 0.9, 0, TAU)); }
    else { ctx.strokeStyle = c; ctx.lineWidth = 0.8; ctx.beginPath(); ctx.moveTo(-4.5, -20.6); ctx.quadraticCurveTo(0, -14.5, 4.5, -20.6); ctx.stroke(); fill(ctx, "#e8bb48", () => { ctx.moveTo(0, -17.8); ctx.lineTo(1.4, -16.2); ctx.lineTo(0, -14.4); ctx.lineTo(-1.4, -16.2); ctx.closePath(); }); }
  }
  // 胸前紋章（body.crest：顏色）：正面在胸口；側面只在胸前前緣露一條；背面不畫
  function crest(ctx, it, view) {
    if (!it?.crest) return;
    const S = view === "side";
    if (view === "back") return;
    if (S) { fill(ctx, it.crest, () => rr(ctx, 4.4, -18.5, 1.6, 5, 0.6)); return; }
    fill(ctx, it.crest, () => { ctx.moveTo(-2.6, -18.8); ctx.lineTo(2.6, -18.8); ctx.lineTo(2.6, -15.4); ctx.lineTo(0, -13.2); ctx.lineTo(-2.6, -15.4); ctx.closePath(); });
    fill(ctx, "#e8bb48", () => ctx.rect(-0.6, -18.2, 1.2, 4));
  }

  // ---------- 關鍵姿勢 第 6 版（11-04 晚）----------
  // 武器掛在主手手掌：武器變換 ＝ 主手手掌位置＋旋轉；副手去握第二個握點，搆不到就改單手。
  // 每一類、每個方向（正面、背面、側面）各自手調「兩手的位置與武器角度」後寫死；手臂兩節的關節角度照手的位置算（肩→肘→手）。
  // 背面不是正面鏡像（11-04 晚，專案 PM：「四面都要分別畫」）：背面時手和胸前握的部分被身體擋住，往外伸的部分（槍尖、槍口、弓身）、背上的東西（箭袋、披風）露出來。
  // 側面朝西不是朝東鏡像：朝東時右手（主手）在近側，朝西時右手在遠側、左手（盾、書）在近側（WEST）。
  //   正面肩：主手 (−8.5,−20)、副手 (8.5,−20)；背面肩：主手 (8.5,−20)、副手 (−8.5,−20)；側面肩：近側 (4.5,−20)、遠側 (3,−20)
  // 格式：hand＝主手手掌位置、a＝武器角度（作用端方向，0＝朝上、順時針為正）、og＝副手握點（武器座標）、mg＝主手握在武器座標的哪一點（扛肩握柄尾）
  const CLASS_OF = { greatsword: "greatsword", spear: "polearm", scythe: "polearm", bow: "bow", crossbow: "gun", gun: "gun", staff: "staff" };
  let GS = "plant"; // 雙手劍正面姿勢：plant 拄劍、shoulder 扛肩（使用者選）
  // 雙手劈（第 7 版）：蓄力＝劍扛到肩上（劍柄在胸前、兩手都在柄上、劍身沿肩往後伸，從頭後面露出）→ 舉到臉前上方（劍從臉的前方外側往上）→ 往前下方劈。
  //   副手在主手下方 4.5（靠劍柄尾）；命中時主手往前伸，副手才不會縮到身體後面（審查：「命中只畫一隻手」）
  const GS_ATK = { from: { hand: [6, -18], a: -1.2 }, mid: { hand: [11, -22], a: 0.45 }, to: { hand: [10.5, -12], a: 1.9, elbow: 1 }, og: [0, 4.5] };
  const KEY = {
    greatsword: { zh: "拄劍：雙手疊握劍柄在胸前，劍垂直往下，劍尖點在兩腳之間",
      front: { hand: [-0.5, -15], a: Math.PI, og: [0, 3.5], short: true },            // 副手在上 (−0.5,−18.5)
      back: { hand: [0.5, -15], a: Math.PI, og: [0, 3.5], short: true },              // 手和劍柄在身前被擋住，只在兩腳之間露出劍尖
      side: { hand: [7.4, -13.6], a: Math.PI + 0.06, og: [0, 5.5], short: true },     // 兩手前後分開握（使用者看出「兩手疊成一團」）：下手 (7.4,−13.6)、上手在上 5.5
      atk: GS_ATK,
    },
    greatsword_shoulder: { zh: "扛肩：雙手握柄在胸前、兩手之間露出劍柄，劍身靠在右肩上往後伸",
      front: { hand: [-2.7, -17.7], a: -0.9, og: [0, 3.5] },                           // 上手近護手在左胸、下手 (0,−15.5)；劍身越過畫面左側的右肩
      back: { hand: [2.7, -17.7], a: 0.9, og: [0, 3.5], behind: true },               // 背面：手和劍柄在身前，只畫肩線以上：劍身從右肩（畫面右）斜到背後上方
      side: { hand: [5.8, -17.2], a: -1.2, og: [0, 5.5], layer: "head" },              // 第 7 版：右手（主手）靠護手、左手（副手）握柄尾在更前面，兩手之間看得到劍柄；劍身沿肩膀往後、從頭後面伸出（審查：「後腦只露出一截劍尖，手什麼都沒握到」）
      atk: GS_ATK,
    },
    polearm: { zh: "正面斜持：上手在左胸、下手在右腰，槍尖朝左上；側面直立、槍桿在臉的前方外側",
      front: { hand: [-3, -18], a: -Math.PI / 4, og: [0, 9.9] },
      back: { hand: [3.2, -17], a: Math.PI / 4 + 0.08, og: [0, 9.9] },               // 背面：槍尖從右肩外上方露出；兩手和槍尾在身體前方，被身體擋住
      side: { hand: [10.5, -12.5], a: 0.15, og: [0, -8] },                            // 第 7 版：手往前移、槍桿前傾，槍桿在鼻尖前方外側（審查：「槍桿壓在臉的前緣，把鼻子蓋掉」）
      atk: { from: { hand: [2, -14], a: 1.25 }, to: { hand: [6, -17.5], a: Math.PI / 2 + 0.03 }, og: [0, -6] },   // 雙手刺（第 7 版）：主手是後手、副手是前手（在主手前 6），兩手都在槍桿上、都在身體前方
      atkScythe: { from: { hand: [7, -15], a: 0.45 }, to: { hand: [5, -17], a: 2.0 }, og: [0, -6] } },               // 鐮：舉起（刃在頭的前上方）→ 往前下方收割（刃口朝自己），兩手在柄上
    bow: { zh: "左手持弓、右手拉弦。正面弓在畫面右身側；背面弓在畫面左身側、背上箭袋；側面弓在身前、箭搭在弦上",
      // 第 7 版：左手（副手）持弓、右手（主手）拉弦（右撇子弓手的常識；審查與專案 PM 同意）
      front: { wh: "off", hand: [9.6, -11.5], a: -Math.PI / 2 },                      // 正面：左手（畫面右）在身側握弓把，弓直立；弦在外側，不壓在身上；右手垂著
      back: { wh: "off", hand: [-9.6, -11.5], a: Math.PI / 2 },                       // 背面：左手在畫面左、身側，弓直立在身旁（上下弓梢都露出），弦在外側、不壓在身上；背上箭袋
      side: { hand: [7.8, -12.5], a: Math.PI / 2 + 0.1 },                             // 側面待機：持弓手在身前腰高、弓直立；右手手指扣在弦上（箭搭著、未拉）
      aim: { hand: [13.2, -21], a: Math.PI / 2 } },                                   // 拉弓：持弓手往前伸到肩高、弓直立；右手把弦拉到下巴下（弦在臉後面，不壓眼睛），箭與視線平行
    gun: { zh: "正面橫持在胸前、口朝右下；背面口從左腰外露出；側面持槍待命、口朝前上",
      front: { hand: [-3, -15], a: 1.87, og: [0, -6.8] },
      back: { hand: [3, -15], a: -1.87, og: [0, -6.8] },
      side: { hand: [6, -11], a: 0.9, og: [0, -7] },
      atk: { from: { hand: [6, -11], a: 0.9 }, to: { hand: [7.5, -21], a: Math.PI / 2 }, og: [0, -5] } },  // 瞄準：槍托靠肩、扳機手在下巴旁，托槍手在前，槍管水平
    staff: { zh: "單手握杖：正面杖在畫面左、背面在畫面右（都在身側、手看得到）；側面杖往前傾",
      front: { hand: [-9.5, -11], a: -0.1 },
      back: { hand: [9.6, -11], a: 0.1 },                                             // 第 7 版：背面杖在畫面右（右手在身側），手和杖都看得到（審查：「杖畫在背上、握杖的手卻被擋住」）
      side: { hand: [9.1, -10.6], a: 0.4 } },
  };
  function keyOf(gear) {
    const q = qWeapon(gear.main_hand); if (!q) return null;
    let c = CLASS_OF[q.kind]; if (!c) return null;
    if (c !== "staff" && gear.off_hand) return null; // 雙手武器副手有東西就改單手
    if (c === "greatsword" && GS === "shoulder") c = "greatsword_shoulder";
    return { c, K: KEY[c], kind: q.kind };
  }
  const ogLocal = (og) => (og ? [og[0], og[1] === "EY" ? BOW_EY : og[1]] : null);
  // 主手的關節：肩 sx、手掌目標 hand、手肘往哪邊
  const armTo = (sx, hand, out) => ik(sx, hand, out);
  let TINT = null; // 自測用：把副手臂塗成指定色，算它露出多少
  let WEST = false; // 側面朝西（stamp 設定）：左右手互換
  // 弓手預設背箭袋（使用者看背面：「弓被擋住」；專案 PM：箭袋在背上）
  const backOf = (gear) => gear.back ?? (qWeapon(gear.main_hand)?.kind === "bow" ? { slot: "back", kind: "quiver", material: "leather" } : null);

  // ---------- 側面的兩隻手（第 7 版，11-04 深夜，獨立審查退回後重寫）----------
  // 朝東：近側＝主手（右），肩 x 4.5；遠側＝副手（左），肩 x 3。朝西相反（座標一律用朝東畫，stamp 再鏡像）。
  // 武器掛在「持武器的手」：一般是主手；弓是副手（左手持弓、右手拉弦，右撇子弓手的常識）。另一隻手去握第二握點，搆不到就放開。
  // 圖層：遠側的手在身體前方（x > 4.6）時畫在身體之後、頭之前，並裁掉肩膀那段；在身旁或身後就畫在身體之前（被擋）。
  //   武器 layer：head＝身體之後、頭之前（扛肩、蓄力的劍身在頭後；弓的弦在臉後）；front＝頭之後；back＝身體之前（遠側單手、手在身旁）。
  const clamp01 = (t) => Math.max(0, Math.min(1, t));
  function sidePlan(unit, key, anim, W) {
    const { gear } = unit, SX = { main: W ? 3 : 4.5, off: W ? 4.5 : 3 }, nearWho = W ? "off" : "main";
    let P;
    if (key && !anim) {
      const ks = key.K.side, bow = key.c === "bow";
      let hand = ks.hand, a = ks.a, og = ks.og ?? null, mg = ks.mg ?? 0, short = !!ks.short, layer = ks.layer ?? null, elbow = -1;
      const AK = (key.kind === "scythe" && key.K.atkScythe) || key.K.atk;
      if (AK && typeof POSE?.atk === "number") {
        const t = clamp01(POSE.atk), [P0, P1, tt] = AK.mid ? (t < 0.5 ? [AK.from, AK.mid, t * 2] : [AK.mid, AK.to, t * 2 - 1]) : [AK.from, AK.to, t];
        const L = (p, q) => p + (q - p) * tt;
        hand = [L(P0.hand[0], P1.hand[0]), L(P0.hand[1], P1.hand[1])]; a = L(P0.a, P1.a); og = AK.og; mg = 0; short = false; elbow = tt > 0.5 ? P1.elbow ?? -1 : P0.elbow ?? -1;
        layer = Math.sin(a) < -0.3 ? "head" : null; // 劍尖朝後（蓄力）：劍身在頭後、劍柄在胸前
      }
      if (bow) {
        const t = clamp01(pz("bowAim")), A2 = key.K.aim;
        if (t) { hand = [hand[0] + (A2.hand[0] - hand[0]) * t, hand[1] + (A2.hand[1] - hand[1]) * t]; a += (A2.a - a) * t; }
        og = "string"; layer = "head"; // 弦在臉後面（朝東拉弦手在下巴、近側；朝西拉弦手在臉的另一側）
      }
      const wh = bow ? "off" : "main", k = ik(SX[wh], hand, elbow); // elbow：手肘往後（−1）或往前上（+1，命中時前臂不蓋住後面那隻手）
      P = { wh, sA: k.sA + pz("arm"), eA: k.eA, a: a + pz("arm") + pz("dw"), og, mg, short, layer };
    } else {
      // 6M／6N 片段或沒有關鍵姿勢的武器：主手臂角度 arm、武器角度 arm＋wpn；雙手武器出招時副手去握 og
      const sA = pz("arm"), eA = Math.min(0, sA * 0.35), w = anim ? POSE.wpn : holdOf(gear.main_hand, "side");
      const kc2 = key && key.c !== "bow" && key.c !== "staff" ? key.K.side.og : null;
      P = { wh: "main", sA, eA, a: sA + w, og: kc2 && anim ? kc2 : null, mg: key?.K.side.mg ?? 0, short: false, layer: null };
    }
    P.h = fk(SX[P.wh], P.sA, P.eA);
    const who2 = P.wh === "main" ? "off" : "main";
    const A = { [P.wh]: { who: P.wh, sx: SX[P.wh], sA: P.sA, eA: P.eA } };
    P.ol = null;
    const released = P.og === "string" && pz("bowAim") > 0.9 && !(pz("pull") > 0.5); // 放箭那一格
    if (released) P.og = null;
    if (P.og) {
      const ol = P.og === "string" ? [0, BOW_EY + (pz("pull") || 0)] : P.og, o = rot(P.a, [ol[0], ol[1] - P.mg]), t = [P.h[0] + o[0], P.h[1] + o[1]], k = ik(SX[who2], t, -1);
      if (k.ok) { A[who2] = { who: who2, sx: SX[who2], sA: k.sA, eA: k.eA }; P.ol = ol; if (POSE && POSE.hands) POSE.hands.offTwo = true; }
    }
    if (!A[who2] && released) {
      // 放箭：弦彈回弓上，拉弦手留在下巴下（不跟著弦往前）
      const k = ik(SX[who2], [3.6, -21.5], -1); A[who2] = { who: who2, sx: SX[who2], sA: k.sA, eA: k.eA };
    }
    if (!A[who2]) {
      // 空出來的副手：成對武器拿第二把匕首（跟著主手出招，慢一點、低一點）；拿書、盾或垂著
      const paired = qWeapon(gear.main_hand)?.kind === "paired";
      if (paired) {
        // 第二把匕首在副手：出招時收在胸前護身；待機、站著時舉在腰前、刃朝前上（遠側手在身體前方，和主手分開、看得到，不會像兩把都在同一隻手）
        const att = anim && POSE.wpn !== undefined && !POSE.idle, k = ik(SX.off, att ? [7.6, -15.5] : [7.8, -14.2], -1);
        const sA = k.sA, eA = k.eA, da = att ? 0.55 : 0.85;
        A.off = { who: "off", sx: SX.off, sA, eA, item: (hand) => offDagger(ctx0(), gear.main_hand, hand, da - sA - eA) };
      } else if (W) A.off = { who: "off", sx: SX.off, sA: -0.15, eA: 0.1, item: gear.off_hand && !isShield(gear.off_hand) ? (hand) => PD.drawWeapon(ctx0(), gear.off_hand, hand[0] + 1, true) : null };
      else A.off = { who: "off", sx: -4.5, sA: pz("armL") * 0.6 - 0.1, eA: 0.15, item: gear.off_hand && !isShield(gear.off_hand) ? (hand) => PD.drawWeapon(ctx0(), gear.off_hand, hand[0], true) : null };
    }
    const farWho = nearWho === "main" ? "off" : "main";
    P.near = A[nearWho]; P.far = A[farWho];
    P.far.front = fk(P.far.sx, P.far.sA, P.far.eA)[0] > 4.6 && P.far.sx > 0;
    if (!P.layer) P.layer = P.wh === farWho && !P.far.front ? "back" : "front";
    return P;
  }
  let CTX = null; const ctx0 = () => CTX; // 畫手上的東西時用的畫布（arm 的 inHand 回呼在手的座標系裡）
  // 副手的匕首：在手的座標系裡畫，角度相對手臂
  function offDagger(ctx, it, hand, a) { ctx.save(); ctx.translate(hand[0], hand[1]); ctx.rotate(a); dagger(ctx, it); ctx.restore(); }
  // ---------- 整隻：view = front | side | back ----------
  // 畫的順序（由後到前；部件的圖層見 docs/art/部件四方向清單.md）
  //   正面：披風（暗）→ 背掛（露在肩上的部分）→ 尾巴 → 腿 → 身體 → 紋章、頸飾、背帶、腰掛 → 披風扣 → 副手臂＋副手 → 頭 → 武器 → 副手臂 → 主手臂
  //   側面：披風（背後那片）→ 背掛 → 尾巴 → 遠側手臂（朝東：副手；朝西：主手＋單手武器）→ 遠側腰掛 → 腿 → 身體 → 紋章、頸飾、背帶、近側腰掛 → 盾（朝東）→ 頭 → 武器 → 近側手臂（朝東：主手；朝西：副手＋盾、書）
  //   背面：武器與兩隻手臂（在身體前方＝畫面後）→ 副手物品 → 腿 → 身體 → 腰掛 → 披風 → 背掛 → 尾巴 → 扛肩的劍身 → 頭
  function draw(ctx, unit, view) {
    const { look, gear } = unit, F = view === "front", B = view === "back", S = view === "side";
    CTX = ctx;
    const side = S ? 1 : 0, W = S && WEST;
    const R = window.RaceArt;
    const mark = (n) => { if (POSE && POSE.layers) POSE.layers.push(n); };
    const key = keyOf(gear), anim = POSE && typeof POSE.wpn === "number";
    const bk = backOf(gear);
    ctx.save();
    if (R) R.build(ctx, look);
    if (look.frame === "slim") ctx.scale(0.92, 1.02); else if (look.frame === "broad") ctx.scale(1.08, 0.98);
    ctx.translate(0, pz("bob"));
    if (S) rotAt(ctx, 0, -9, pz("lean"));
    if (gear.cloak && F) cloakFront(ctx, gear.cloak);
    if (F) backItem(ctx, bk, "front", "behind");
    if (gear.cloak && S) { cloakSide(ctx, gear.cloak); mark("cloak"); }
    if (S) backItem(ctx, bk, "side", "behind");
    if (R && !B) R.tail(ctx, look, F ? "front" : "side", side);
    // ---- 背面：武器與手臂在身體前方（先畫，被身體擋住）----
    if (B) {
      // 背面（第 7 版）：拿在身體前方的東西（雙手武器、盾、書）連手一起被身體擋住；
      //   垂在身側的手（空手、單手武器、成對匕首、法杖、弓）不在身體前方，畫在身體之後、看得到（審查：「背面垂在身側的手都消失了」）
      const kb = key && key.K.back;
      if (kb && kb.og) {
        const k0 = armTo(8.5, kb.hand, 1), h = fk(8.5, k0.sA, k0.eA), ol = ogLocal(kb.og);
        if (!kb.behind) { mainWeapon(ctx, gear.main_hand, h, kb.a, "back", !!kb.short, ol); mark("weapon"); }
        const o = rot(kb.a, ol), io = ik(-8.5, [h[0] + o[0], h[1] + o[1]], -1); arm(ctx, unit, -8.5, io.sA, io.eA, 0, rec("off"));
        arm(ctx, unit, 8.5, k0.sA, k0.eA, 0, rec("main"));
      } else {
        // 單手武器（劍、刀、匕首、鎚……）：正面拿在身側，背面也在身側（畫面右），身體之後畫、手和武器都看得到，見下面
        if (gear.off_hand) {
          ctx.save(); ctx.translate(0, pz("armL")); TINT = POSE && POSE.tintOff ? POSE.tintOff : null;
          const oa = gear.off_hand && !isShield(gear.off_hand) ? -0.5 : -0.3;
          arm(ctx, unit, -8.5, oa, 0, 0, rec("off"));
          TINT = null; ctx.restore();
        }
      }
      mark("arms");
      if (isShield(gear.off_hand)) { shieldBack(ctx, gear.off_hand, -8.5); mark("shield"); }
      else if (gear.off_hand) { PD.drawWeapon(ctx, gear.off_hand, -5.2, false); mark("shield"); }
    }
    // ---- 側面（第 7 版）：兩隻手的位置、武器在哪隻手、各畫在哪一層（sidePlan）----
    const SP = S ? sidePlan(unit, key, anim, W) : null;
    const sideArm = (A, clip) => {
      ctx.save();
      if (clip) { ctx.beginPath(); ctx.rect(3.2, -80, 80, 120); ctx.clip(); } // 遠側手伸到身體前方：只露出胸前那段前臂與手
      arm(ctx, unit, A.sx, A.sA, A.eA, side, A.item ? (hand, c) => { A.item(hand, c); const r = rec(A.who); if (r) r(hand, c); } : rec(A.who));
      ctx.restore();
    };
    const sideWeapon = () => { mainWeapon(ctx, gear.main_hand, SP.h, SP.a, "side", SP.short, SP.ol, SP.mg); mark("weapon"); };
    if (S) {
      if (!SP.far.front) sideArm(SP.far, false);
      if (SP.layer === "back") sideWeapon();
    }
    if (S) waistItem(ctx, gear.waist, "side", "behind");
    leg(ctx, look, gear.feet, -1, pz("hipF"), pz("kneeF"), pz("liftL"), side);
    leg(ctx, look, gear.feet, 1, pz("hipN"), pz("kneeN"), pz("liftR"), side);
    body(ctx, gear.body, look, side, B); mark("body");
    crest(ctx, gear.body, F ? "front" : B ? "back" : "side");
    neckItem(ctx, gear.neck, F ? "front" : B ? "back" : "side");
    waistItem(ctx, gear.waist, F ? "front" : B ? "back" : "side", "over");
    if (!B) backItem(ctx, bk, F ? "front" : "side", "over");
    if (B) {
      // 背面垂在身側、看得到的手：法杖在畫面右（右手）、弓在畫面左（左手）、空手
      const kb = key && key.K.back, paired = qWeapon(gear.main_hand)?.kind === "paired";
      if (key && (key.c === "bow" || key.c === "staff")) {
        const who = kb.wh ?? "main", sx = who === "main" ? 8.5 : -8.5, k0 = armTo(sx, kb.hand, who === "main" ? 1 : -1), h = fk(sx, k0.sA, k0.eA);
        mainWeapon(ctx, gear.main_hand, h, kb.a, "back"); mark("weapon");
        arm(ctx, unit, sx, k0.sA, k0.eA, 0, rec(who));
        if (who === "off") arm(ctx, unit, 8.5, 0, 0, 0, rec("main"));
      } else if (!(kb && kb.og)) {
        // 空手或單手武器：右手垂在身側（畫面右），單手武器握在手裡、刃往外斜（正面的鏡像位置；審查：「背面垂在身側的手都消失了」）
        const rm = rec("main");
        ctx.save(); ctx.translate(0, pz("armR"));
        arm(ctx, unit, 8.5, 0, 0, 0, gear.main_hand ? (hand, c) => { mainWeapon(ctx, gear.main_hand, hand, -holdOf(gear.main_hand, "front"), "back"); mark("weapon"); if (rm) rm(hand, c); } : rm);
        ctx.restore();
      }
      // 左手：空手垂在身側；成對武器的第二把在左手（畫面左），刃往外斜
      if (!gear.off_hand && !(kb && kb.og) && key?.c !== "bow") arm(ctx, unit, -8.5, 0, 0, 0, paired ? (hand, c) => { offDagger(ctx, gear.main_hand, hand, holdOf(gear.main_hand, "front")); const r = rec("off"); if (r) r(hand, c); } : rec("off"));
    }
    if (S) { cloakClasp(ctx, gear.cloak, true); if (!W && isShield(gear.off_hand)) shieldSide(ctx, gear.off_hand); }
    if (B) {
      if (gear.cloak) { cloakBack(ctx, gear.cloak); mark("cloak"); }
      backItem(ctx, bk, "back", "over");
      if (R) R.tail(ctx, look, "back", 0);
      const kb = key && key.K.back;
      if (kb && kb.behind) { const k0 = armTo(8.5, kb.hand, 1), h = fk(8.5, k0.sA, k0.eA); ctx.save(); ctx.beginPath(); ctx.rect(-40, -80, 80, 59.5); ctx.clip(); mainWeapon(ctx, gear.main_hand, h, kb.a, "back", false, ogLocal(kb.og)); ctx.restore(); mark("weapon"); }
    }
    if (F && gear.cloak) cloakClasp(ctx, gear.cloak, false);
    const twoF = F && key && (key.K.front.og || key.K.front.wh === "off");
    if (F && !twoF) {
      const pairedF = qWeapon(gear.main_hand)?.kind === "paired"; // 成對武器：第二把匕首在左手（畫面右），刃朝外上
      ctx.save(); ctx.translate(0, pz("armR")); arm(ctx, unit, 8.5, 0, 0, 0, pairedF ? (hand, c) => { offDagger(ctx, gear.main_hand, hand, -holdOf(gear.main_hand, "front")); const r = rec("off"); if (r) r(hand, c); } : rec("off"));
      if (isShield(gear.off_hand)) shieldFront(ctx, gear.off_hand, 8.5); else if (gear.off_hand) PD.drawWeapon(ctx, gear.off_hand, 8.5, true);
      ctx.restore();
    }
    if (S) {
      if (SP.layer === "head") sideWeapon();
      if (SP.far.front && SP.layer !== "front") sideArm(SP.far, true); // 遠側手握在武器上：手畫在握把上面（不然被劍柄、弓把蓋掉，看起來沒握）
    }
    mark("head");
    ctx.save(); rotAt(ctx, 0, -29, S ? pz("lean") * 0.3 : 0);
    head(ctx, look, F ? "front" : B ? "back" : "side", side, gear);
    if (R) R.ears(ctx, look, F ? "front" : B ? "back" : "side", side, gear.head, "under");
    if (R) R.hat(ctx, look, gear.head, (it) => PD_headgear(ctx, it, F ? "front" : B ? "back" : "side")); else PD_headgear(ctx, gear.head, F ? "front" : B ? "back" : "side");
    if (R) R.ears(ctx, look, F ? "front" : B ? "back" : "side", side, gear.head, "over");
    if (R) R.horns(ctx, look, F ? "front" : B ? "back" : "side", side);
    ctx.restore();
    if (F && key) {
      const k = key.K.front, who = k.wh ?? "main", sx = who === "main" ? -8.5 : 8.5, k0 = armTo(sx, k.hand, who === "main" ? -1 : 1), h = fk(sx, k0.sA, k0.eA), ol = ogLocal(k.og);
      mainWeapon(ctx, gear.main_hand, h, k.a, "front", !!k.short, ol);
      if (ol) { const o = rot(k.a, ol), io = ik(8.5, [h[0] + o[0], h[1] + o[1]], 1); arm(ctx, unit, 8.5, io.sA, io.eA, 0, rec("off")); }
      arm(ctx, unit, sx, k0.sA, k0.eA, 0, rec(who));
      if (who === "off") arm(ctx, unit, -8.5, 0, 0, 0, rec("main")); // 弓：右手垂在身側
    } else if (F) {
      const rm = rec("main");
      ctx.save(); ctx.translate(0, pz("armL")); arm(ctx, unit, -8.5, 0, 0, 0, (hand, c) => { mainWeapon(ctx, gear.main_hand, hand, holdOf(gear.main_hand, "front"), "front"); if (rm) rm(hand, c); }); ctx.restore();
    } else if (S) {
      if (SP.layer === "front") { sideWeapon(); if (SP.far.front) sideArm(SP.far, true); } // 武器在頭之後畫時，遠側握著的手也在武器之後
      sideArm(SP.near, false); // 近側手最上層（朝東：主手；朝西：副手，盾蓋在手上）
      if (W && isShield(gear.off_hand)) shieldSide(ctx, gear.off_hand);
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
      ctx.setTransform(west ? -1 : 1, 0, 0, 1, 0, 0); WEST = !!west && view === "side";
      const hands = {};
      POSE = { ...P, wpn: P.wpn === null ? undefined : P.wpn, hands, probe: (k, h, t, v, o) => { got = { hand: [h.x, h.y], tip: [t.x, t.y], off: o ? [o.x, o.y] : null }; } };
      draw(ctx, A.unit(kind), view); POSE = null; WEST = false;
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
      const small = false; // 第 7 版：背面的單手武器跟手一起垂在身側（畫面右），拳套、法球也要露出來
      // 弓（第 7 版）：正面、背面弓在身側、弦朝外；「作用端」改查弓把在身體外（弓臂、弓梢跟著在外面）
      for (const [dir, view] of [["south", "front"], ["north", "back"]]) { const g = probe(kind, view, false, A.REST); const hid = g ? inBody(kind === "bow" ? g.hand : g.tip) : false; r[dir] = g && inBox(g) ? ((dir === "north" && small ? hid : !hid) ? 1 : 0) : NaN; if (dir === "north") r.northSmall = small; }
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
        // 背面的關鍵姿勢沒有副手握點（弓：持弓手往外伸、搭弦手放開）時，只查主手
        const kk = KEY[CLASS_OF[kind]], needOff = dir === "north" ? !!kk.back.og : dir === "south" ? !!kk.front.og : true;
        r[dir] = !!g && near(g.hands.main, g.hand) && (!needOff || near(g.hands.off, g.off));
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
        const kc = CLASS_OF[kind], twoKey = kc && KEY[kc][view === "back" ? "back" : "front"].og;
        const wOff = kc && KEY[kc][view === "back" ? "back" : view === "side" ? "side" : "front"].wh === "off" || (kc === "bow" && view === "side"); // 弓：左手（副手）持弓
        const okM = touches(wc2, wOff ? hands.off : hands.main), twoHere = twoKey && hands.off && (view !== "side" || hands.offTwo);
        const okO = twoHere ? touches(wc2, hands.off) : true;
        r[dir] = { ok: okM && okO, t: `${wOff ? "持弓手（左）" : "主手"}${okM ? "握住" : "沒握到"}${twoHere ? `・副手${okO ? "握住" : "沒握到"}` : ""}` };
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
        // 第 7 版：只查「拿在身體前方」的手；垂在身側的手（空手、法杖、弓）背面本來就看得到（審查：「背面垂在身側的手都消失了」）
        const kq = qWeapon(u.gear.main_hand), front = who === "main" ? !!kq && !!CLASS_OF[kq.kind] && !["staff", "bow"].includes(kq.kind) && !u.gear.off_hand : !!u.gear.off_hand;
        if (!front) { seen.push(`${who === "main" ? "主手" : "副手"}垂在身側（看得到，設計）`); continue; }
        const n = [[0, 0], [1.2, 0], [-1.2, 0], [0, 1.2], [0, -1.2]].filter(([dx, dy]) => px([h[0] + dx * K, h[1] + dy * K]) === hc).length;
        if (n) seen.push(`${who === "main" ? "主手" : "副手"}露出 ${n}/5`);
      }
      out.push({ zh, ok: seen.every((t) => t.includes("設計")), seen });
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
  function PD_headgear(ctx, it, view) { if (!it) return; Q_headgear(ctx, it, view); }
  // 頭飾 × 四方向（11-04 晚，使用者：「還有其他物件都要考慮4面」）：正面照舊版；側面（朝東）各自轉成側面；背面看不到臉前的東西（帽簷、面紗、護目鏡鏡片、頭冠寶石）
  function Q_headgear(ctx, it, view) {
    const [c, d] = colors(it), S = view === "side", B = view === "back";
    switch (it.kind) {
      case "hood":
        if (S) {
          // 側面：兜帽包住頭頂與後腦、垂到後頸；臉的開口在前面，邊緣一道深色
          ctx.fillStyle = c; ctx.beginPath(); ctx.arc(-0.6, -29.6, 10.2, 0, TAU); ctx.ellipse(4.4, -28.2, 4.6, 6.4, 0.12, 0, TAU); ctx.fill("evenodd");
          fill(ctx, c, () => { ctx.moveTo(-10.6, -29); ctx.quadraticCurveTo(-11, -22, -6, -20.6); ctx.lineTo(1, -21); ctx.lineTo(-3, -25); ctx.closePath(); });
          ctx.strokeStyle = d; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.ellipse(4.4, -28.2, 4.6, 6.4, 0.12, -1.9, 1.9); ctx.stroke();
          break;
        }
        ctx.fillStyle = c; ctx.beginPath(); ctx.arc(0, -29.5, 10, Math.PI * 0.85, Math.PI * 2.15); ctx.lineTo(9, -22); ctx.lineTo(-9, -22); ctx.closePath(); if (!B) ctx.ellipse(0, -28, 6.5, 6, 0, 0, TAU); ctx.fill("evenodd");
        fill(ctx, d, () => ctx.rect(-9, -23, 18, 1.5));
        if (B) { ctx.strokeStyle = d; ctx.lineWidth = 0.8; ctx.beginPath(); ctx.moveTo(0, -38); ctx.lineTo(0, -24); ctx.stroke(); } // 背面：兜帽的縫線
        break;
      case "helmet": case "horned_helm":
        if (S) {
          fill(ctx, c, () => { ctx.moveTo(8.8, -31.6); ctx.quadraticCurveTo(8, -40.2, -0.6, -40); ctx.quadraticCurveTo(-9.8, -39.4, -9.8, -29); ctx.lineTo(-9.4, -24.5); ctx.lineTo(-5, -25.5); ctx.lineTo(-4.5, -31.4); ctx.lineTo(8.8, -31.6); ctx.closePath(); }); // 圓頂＋後護頸（第 7 版：前緣抬到眉毛上，不蓋眼睛）
          fill(ctx, d, () => ctx.rect(-4.5, -32.6, 13.6, 1.2)); fill(ctx, d, () => ctx.rect(8.2, -32.6, 1.6, 1.8)); // 帽緣＋前緣
          if (it.kind === "horned_helm") fill(ctx, "#e8d8b8", () => { ctx.moveTo(-2, -38); ctx.quadraticCurveTo(-6, -46, -11, -46); ctx.quadraticCurveTo(-6, -42, -4.5, -36.5); ctx.closePath(); });
          break;
        }
        // 第 7 版：正面帽緣在眉毛上（y −31.6），眼睛露出來；兩側護頰只蓋到臉的外緣（審查：「帽緣蓋住眼睛，臉只剩腮紅」）
        if (B) { fill(ctx, c, () => { ctx.beginPath(); ctx.arc(0, -30, 9.4, Math.PI, 0); ctx.lineTo(9.4, -27); ctx.lineTo(-9.4, -27); ctx.closePath(); }); fill(ctx, d, () => ctx.rect(-9.4, -27.5, 18.8, 1.2)); fill(ctx, c, () => rr(ctx, -8.6, -27, 17.2, 3, 1)); } // 背面：整個後腦＋後護頸
        else {
          fill(ctx, c, () => { ctx.beginPath(); ctx.arc(0, -31, 9.4, Math.PI, 0); ctx.lineTo(9.4, -25.5); ctx.lineTo(7.2, -25.5); ctx.lineTo(7.2, -31); ctx.lineTo(-7.2, -31); ctx.lineTo(-7.2, -25.5); ctx.lineTo(-9.4, -25.5); ctx.closePath(); });
          fill(ctx, d, () => ctx.rect(-9.4, -32.2, 18.8, 1.2));
        }
        if (it.kind === "horned_helm") for (const s of [-1, 1]) fill(ctx, "#e8d8b8", () => { ctx.beginPath(); ctx.moveTo(s * 8, -31); ctx.lineTo(s * 13, -40); ctx.lineTo(s * 10, -30); ctx.closePath(); });
        break;
      case "wizard_hat":
        if (S) {
          fill(ctx, c, () => { ctx.ellipse(-0.5, -34.2, 12.5, 2.6, -0.04, 0, TAU); }); // 帽簷側看是扁的
          fill(ctx, c, () => { ctx.moveTo(-6.5, -35.5); ctx.lineTo(5.5, -35.5); ctx.quadraticCurveTo(1, -44, -6, -51); ctx.quadraticCurveTo(-4, -44, -6.5, -35.5); ctx.closePath(); }); // 帽尖往後倒
          fill(ctx, d, () => ctx.rect(-6.3, -37.2, 11.6, 1.4));
          break;
        }
        fill(ctx, c, () => { ctx.beginPath(); ctx.moveTo(-12, -34); ctx.lineTo(12, -34); ctx.lineTo(3, -37); ctx.lineTo(2, -52); ctx.lineTo(-4, -37); ctx.closePath(); }); fill(ctx, d, () => ctx.rect(-6, -36.5, 12, 1.4));
        break;
      case "cap":
        if (S) { fill(ctx, c, () => { ctx.moveTo(-9, -31); ctx.quadraticCurveTo(-8.6, -39.6, 0, -39.6); ctx.quadraticCurveTo(7.6, -39.4, 8.6, -32); ctx.closePath(); }); fill(ctx, d, () => rr(ctx, 4, -32.6, 9.2, 1.8, 0.9)); break; } // 帽舌朝前
        fill(ctx, c, () => { ctx.beginPath(); ctx.arc(0, -31, 9, Math.PI, 0); ctx.closePath(); });
        if (!B) fill(ctx, d, () => rr(ctx, -9.5, -32, 19, 1.6, 0.8)); // 背面看不到帽舌
        break;
      case "bandana":
        if (S) { fill(ctx, c, () => { ctx.moveTo(-9, -30); ctx.quadraticCurveTo(-8.6, -39.6, 0, -39.6); ctx.quadraticCurveTo(7.6, -39.4, 8.4, -32.6); ctx.lineTo(-9, -30); ctx.closePath(); }); fill(ctx, c, () => { ctx.moveTo(-8.4, -31); ctx.lineTo(-13, -28); ctx.lineTo(-12, -25.5); ctx.lineTo(-8.2, -29); ctx.closePath(); }); fill(ctx, d, () => ctx.arc(-8.6, -30.6, 1.3, 0, TAU)); break; } // 結在後腦、尾巴往後飄
        fill(ctx, c, () => { ctx.beginPath(); ctx.arc(0, -31, 9, Math.PI, 0); ctx.closePath(); });
        if (B) { fill(ctx, d, () => ctx.arc(0, -31.5, 1.6, 0, TAU)); for (const s of [-1, 1]) fill(ctx, c, () => { ctx.moveTo(0, -31.5); ctx.lineTo(s * 3, -25); ctx.lineTo(s * 1, -24.6); ctx.closePath(); }); } // 背面：結和兩條尾巴
        else fill(ctx, d, () => rr(ctx, 6, -31, 5, 2, 1));
        break;
      case "circlet":
        if (S) { fill(ctx, c, () => ctx.rect(-8.6, -34.6, 17, 1.6)); fill(ctx, "#a898ff", () => { ctx.moveTo(8.6, -36.6); ctx.lineTo(9.8, -34); ctx.lineTo(8.6, -31.8); ctx.lineTo(7.6, -34); ctx.closePath(); }); break; } // 寶石在額前
        fill(ctx, c, () => rr(ctx, -9, -34, 18, 1.6, 0.8));
        if (!B) fill(ctx, "#a898ff", () => { ctx.beginPath(); ctx.moveTo(0, -36.5); ctx.lineTo(1.8, -34); ctx.lineTo(0, -31.5); ctx.lineTo(-1.8, -34); ctx.closePath(); });
        break;
      case "wide_hat":
        if (S) { fill(ctx, c, () => ctx.ellipse(0, -34, 14.5, 2.4, 0, 0, TAU)); fill(ctx, d, () => { ctx.arc(-0.5, -35, 8, Math.PI, 0); ctx.closePath(); }); break; }
        fill(ctx, c, () => { ctx.beginPath(); ctx.ellipse(0, -34, 14, 4, 0, 0, TAU); }); fill(ctx, d, () => { ctx.beginPath(); ctx.arc(0, -35, 8, Math.PI, 0); ctx.closePath(); });
        break;
      case "veil":
        if (S) { fill(ctx, c, () => { ctx.moveTo(2.8, -26.6); ctx.lineTo(9.4, -26.2); ctx.lineTo(8.6, -21); ctx.lineTo(3.6, -20.8); ctx.closePath(); }); ctx.strokeStyle = d; ctx.lineWidth = 0.6; ctx.beginPath(); ctx.moveTo(2.8, -26.4); ctx.lineTo(-2, -28.4); ctx.stroke(); break; } // 面紗在臉前、綁帶到耳後
        if (B) { ctx.strokeStyle = d; ctx.lineWidth = 0.7; ctx.beginPath(); ctx.moveTo(-7.5, -26.5); ctx.lineTo(7.5, -26.5); ctx.stroke(); break; } // 背面只看到綁帶
        fill(ctx, c, () => rr(ctx, -9, -26, 18, 5, 2));
        break;
      case "goggles":
        if (S) { ctx.strokeStyle = "#3a3a44"; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.moveTo(6, -30); ctx.lineTo(-8.8, -30.6); ctx.stroke(); fill(ctx, "#8d969f", () => ctx.ellipse(7.2, -29.5, 2, 2.6, 0, 0, TAU)); fill(ctx, "rgba(160,220,255,0.7)", () => ctx.ellipse(7.8, -29.5, 1.2, 1.9, 0, 0, TAU)); break; } // 一個鏡片朝前、帶子繞到後腦
        if (B) { ctx.strokeStyle = "#3a3a44"; ctx.lineWidth = 1.4; ctx.beginPath(); ctx.moveTo(-8.8, -30); ctx.lineTo(8.8, -30); ctx.stroke(); break; } // 背面只看到帶子
        for (const x of [-3, 3]) { fill(ctx, "#8d969f", () => { ctx.beginPath(); ctx.ellipse(x, -29.5, 3, 2.6, 0, 0, TAU); }); fill(ctx, "rgba(160,220,255,0.7)", () => { ctx.beginPath(); ctx.ellipse(x, -29.5, 2.2, 1.9, 0, 0, TAU); }); }
        break;
      case "crown":
        fill(ctx, c, () => rr(ctx, S ? -6.6 : -7.4, -36, S ? 13.2 : 14.8, 3, 0.8));
        for (const x of S ? [-4.5, 0.5, 5.5] : [-6, 0, 6]) fill(ctx, c, () => { ctx.moveTo(x - 1.6, -35.6); ctx.lineTo(x, -39.6); ctx.lineTo(x + 1.6, -35.6); ctx.closePath(); });
        if (!B) fill(ctx, "#d23c3c", () => ctx.arc(S ? 5 : 0, -34.5, 1, 0, TAU)); // 寶石在正前方，背面看不到
        break;
      case "greathelm":
        fill(ctx, c, () => rr(ctx, -9.6, -39.6, 19.2, 18.6, 4.5)); // 整顆罩住
        if (S) { fill(ctx, d, () => ctx.rect(4.6, -30.6, 5, 1.4)); fill(ctx, d, () => ctx.rect(-9.6, -27, 19.2, 1)); }
        else if (!B) { fill(ctx, d, () => ctx.rect(-6.5, -30.6, 13, 1.4)); fill(ctx, d, () => ctx.rect(-0.6, -30, 1.2, 6)); } // 正面視縫＋鼻樑；背面平的
        break;
    }
  }
  // 離屏畫布（單位）：舊版是 64×72、腳下留 6；出招時長槍、法杖伸出去會被切掉，放大到 128×112、腳下留 14（槍口朝下的正面也放得下）
  const BOX = { W: 128, H: 112, FOOT: 14 };
  // ---------- 貼上：舊版 stamp 原樣（離屏畫、剪影 8 方向偏移成外框、稀有度外光） ----------
  function stamp(ctx, unit, view, cx, cy, size = 1, west = false, opts = {}) {
    const dpr = opts.dpr ?? 3, { W, H, FOOT } = BOX;
    const off = document.createElement("canvas"); off.width = W * size * dpr; off.height = H * size * dpr;
    const o = off.getContext("2d"); o.scale(size * dpr, size * dpr); o.translate(W / 2, H - FOOT); if (west) o.scale(-1, 1);
    WEST = !!west && view === "side"; draw(o, unit, view); WEST = false;
    const sil = document.createElement("canvas"); sil.width = off.width; sil.height = off.height;
    const s = sil.getContext("2d"); s.drawImage(off, 0, 0); s.globalCompositeOperation = "source-in"; s.fillStyle = OUT; s.fillRect(0, 0, sil.width, sil.height);
    const k = 1.3 * size * dpr, dx0 = cx - (W / 2) * size, dy0 = cy - (H - FOOT) * size;
    ctx.save(); ctx.imageSmoothingEnabled = true;
    for (const [ox, oy] of [[k, 0], [-k, 0], [0, k], [0, -k], [k, k], [-k, k], [k, -k], [-k, -k]]) ctx.drawImage(sil, dx0 + ox / dpr, dy0 + oy / dpr, W * size, H * size);
    ctx.drawImage(off, dx0, dy0, W * size, H * size);
    ctx.restore();
  }
  return { draw, stamp, setPose: (p) => { POSE = p; }, selfTest, QW, TWO, KEY, CLASS_OF, fk, rot, BOW_EY, setGreatsword: (v) => { GS = v; }, getGreatsword: () => GS };
})();
