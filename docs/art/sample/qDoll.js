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
  let BARESKIN = null, EDGEK = null; /* EDGEK：赤膊時手臂內線、拳頭邊、側面描邊的加深量（膚色＋0.23，和胸肌線同色）；其他時候 null＝照舊 */ /* 畫圖 agent 11-07：body.kind "bare"（赤膊）時＝膚色；其他時候 null，不影響既有部件 */
  const colors = (it) => (it ? (it.kind === "bare" && BARESKIN ? [BARESKIN, mix(BARESKIN, "#000000", 0.25)] : PD.itemColors(it)) : ["#d8cdb4", "#a89c80"]);

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
    } else if (kind === "bare") {
      /* 畫圖 agent 11-07：赤膊（護法武僧、爐叔）：膚色軀幹；胸口一條肌肉線＋下巴下一道陰影分開頭和胸；腰帶色＝body.color；背面脊線 */
      const sh = mix(c, "#000000", 0.23);
      fill(ctx, c, () => { ctx.moveTo(-4.5, -21); ctx.lineTo(4.5, -21); ctx.quadraticCurveTo(7.5, -21, 7.5, -18); ctx.lineTo(7.5, -15); ctx.quadraticCurveTo(7, -12, 7, -9.5); ctx.lineTo(7, -7.5); ctx.lineTo(-7, -7.5); ctx.lineTo(-7, -9.5); ctx.quadraticCurveTo(-7, -12, -7.5, -15); ctx.lineTo(-7.5, -18); ctx.quadraticCurveTo(-7.5, -21, -4.5, -21); ctx.closePath(); }); /* 腰上方收窄 0.5 */
      if (!side) for (const s of [-1, 1]) fill(ctx, sh, () => ctx.ellipse(s * 6.4, -18.4, 1.1, 2, 0, 0, TAU)); /* 腋下陰影 */
      if (!side && !back) { fill(ctx, sh, () => ctx.ellipse(0, -20.6, 4.2, 1.1, 0, 0, TAU)); ctx.strokeStyle = sh; ctx.lineWidth = 0.7; ctx.lineCap = "round"; for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(s * 0.5, -17.4); ctx.quadraticCurveTo(s * 3, -15.4, s * 5.6, -17.2); ctx.stroke(); } fill(ctx, sh, () => ctx.ellipse(0, -11.4, 0.5, 0.7, 0, 0, TAU)); }
      else if (side) { fill(ctx, sh, () => ctx.ellipse(4.2, -20.4, 3.2, 1, 0, 0, TAU)); ctx.strokeStyle = sh; ctx.lineWidth = 0.7; ctx.lineCap = "round"; ctx.beginPath(); ctx.moveTo(2.4, -17.6); ctx.quadraticCurveTo(5.6, -15, 7.4, -16.8); ctx.stroke(); }
      else { ctx.strokeStyle = sh; ctx.lineWidth = 0.6; ctx.lineCap = "round"; ctx.beginPath(); ctx.moveTo(0, -19.8); ctx.lineTo(0, -12); ctx.stroke(); }
      fill(ctx, it?.color ?? look.belt ?? "#3a2a1c", () => ctx.rect(-7.5, -9.5, 15, 2));
      if (!side && !back) fill(ctx, "#d8b04a", () => ctx.rect(-1, -9.5, 2, 2));
    } else {
      fill(ctx, c, () => rr(ctx, -7.5, -21, 15, 13.5, 3));
      // 胸口高光：側面在胸前那半邊，背面不畫
      if (kind === "plate") { if (!back) fill(ctx, mix(c, "#ffffff", 0.35), () => rr(ctx, side ? 1.5 : -5, -19.5, 4, 6, 1.5)); fill(ctx, d, () => ctx.rect(-7.5, -14, 15, 1.2)); }
      else if (kind === "mail") { ctx.fillStyle = d; for (let y = -19; y < -9; y += 2.4) for (let x = -6 + ((y | 0) % 2); x < 6.5; x += 2.4) ctx.fillRect(x, y, 1, 1); }
      else if (kind === "leather") { const k = back ? -1 : 1; ctx.strokeStyle = d; ctx.lineWidth = 1; ctx.beginPath(); if (side) { ctx.moveTo((WEST ? 1.5 : -1.5) / 0.72, -20.8); ctx.lineTo((WEST ? -3.5 : 4.6) / 0.72, -11); } else { ctx.moveTo(-5 * k, -20); ctx.lineTo(5 * k, -11); } ctx.stroke(); } /* 第 10 版：側面照箭袋背帶（s08_01）的方向各自畫：朝東右肩在近側，從肩斜到胸前腰；朝西左腰在近側，從肩斜到背後腰（審查：「斜背帶朝東、朝西照抄」） */ // 斜背帶：右肩到左腰；背面右肩在畫面右，斜向和正面相反（第 7 版）
      fill(ctx, look.belt ?? "#3a2a1c", () => ctx.rect(-7.5, -9.5, 15, 2));
      if (!side && !back) fill(ctx, "#d8b04a", () => ctx.rect(-1, -9.5, 2, 2));
      else if (side && !NOBUCKLE) fill(ctx, "#d8b04a", () => ctx.rect(6.2, -9.5, 1.3, 2)); // 側面：帶扣轉到身體前緣，只露一點 /* 第 17 版 B 批：近側的手垂在腰前時不畫（審查：「腰帶金色尾端露出」，手下方露出一小塊零散的黃色） */
    }
    ctx.restore();
  }
  // ---------- 手臂：舊版 4×10 的方塊，拆成上臂（肩轉）＋前臂（肘轉）＋手 ----------
  // inHand(hand)：在手的座標系（含肩、肘旋轉）畫手上的東西，畫在手掌下面（握把被手蓋住）；handOnly＝只畫手上的東西（背面武器在身體後，手臂之後另外畫）
  // 第 9 版：len＝[上臂, 前臂] 長度（預設 5、5.5；正面弓手的右手要橫過腹前搆到左腰外的弦，手臂拉長）。
  //   SEAM：袖子畫在同色的身體上面時看不出手臂，手像浮在胸前（審查：「手浮在胸前」）；袖子描一圈深一點的邊，看得出手臂從肩膀連到手
  function arm(ctx, unit, x, shoulderA, elbowA, side, inHand = null, handOnly = false, len = null) {
    let SO = 0, SOd = 0; /* 審查小修（遠側拳頭位置，美術 PM 11-06）：肘角歸 0 時拳頭留在原處：用原本（肩角, 肘角）算出肩到拳頭的向量，肩角改成直指拳頭（SOd）、上臂＋前臂按比例縮成那段直線距離（拳頭位置誤差 0）；手上的東西轉回原本前臂的角度（武器角度不變）。原本直接把肘角歸 0，遠側垂手往身體內縮、拳頭被身體擋成一條細縫 */
    if (ARM.sideOne && side && elbowA && Math.abs(elbowA) <= 0.15) { const u0 = len ? len[0] : UA, f0 = len ? len[1] : FA, r = Math.hypot(f0 * Math.sin(elbowA), u0 + f0 * Math.cos(elbowA)); SO = elbowA; SOd = Math.atan2(f0 * Math.sin(elbowA), u0 + f0 * Math.cos(elbowA)); shoulderA += SOd; len = [u0 * r / (u0 + f0), f0 * r / (u0 + f0)]; elbowA = 0; } /* 2026-11-06 起 E 的預設（使用者：「5 欄」）；原為可行性樣張：ARM.sideOne＝側面打直或只彎一點（≤ 0.15）的手臂當成打直，袖子描邊和正面一樣只描一圈（見 ONE）；彎肘明顯的（IK 解出來的）照舊兩段 */
    if (ARM.elbow && !side && !elbowA && !EBOFF) return armBent(ctx, unit, x, shoulderA, inHand, handOnly, len); /* 可行性樣張（tools/elbow-compare.html，使用者第 17 版：「正面手臂單關節 側面雙關節」）：只有傳入 ARM.elbow 才走，預設不變 */
    const { look, gear } = unit, it = gear.body, kind = it?.kind ?? "shirt";
    const [c0] = colors(it), c = FAR ? mix(c0, "#000000", FAR) : c0, sleeve = TINT ?? (SEAMIN ? mix(c, "#000000", 0.15) : c), /* 第 17 版 B 批審查：正面、背面穿盔甲時袖子深一階（左右同色），手臂和同色胸甲分得開 */ /* 第 10 版：側面伸到身前的遠側手臂、背面持盾的手臂（FAR＝加深多少）畫暗一階，和近側手臂、盾緣分得開 */ ua = len ? len[0] : UA, fa = len ? len[1] : FA, hy = -20 + ua + fa;
    const [hc] = gear.hands ? colors(gear.hands) : [look.skin, look.skin];
    const seam = (path) => { if (!SEAM || TINT || handOnly) return; if (SEAMIN) { ctx.save(); ctx.beginPath(); path(); ctx.clip(); ctx.strokeStyle = mix(c, "#000000", 0.5); ctx.lineWidth = 1.6; ctx.beginPath(); path(); ctx.stroke(); ctx.restore(); return; } /* 第 17 版 B 批：正面、背面單手武器、空手、持盾正面的袖子（E 手臂貼近同色胸甲）描一圈深一點的內框，只畫在袖子裡面（輪廓不變寬；審查：「左臂和胸甲同色」） */ ctx.strokeStyle = mix(c, "#000000", EDGEK ?? 0.38); ctx.lineWidth = EDGEK ? 0.9 : 0.55; ctx.beginPath(); path(); ctx.stroke(); };
    ctx.save();
    if (ARM_DX && !side && !handOnly && Math.abs(Math.abs(x) - SHX) < 1e-9) { const s = Math.sign(x), X = Math.abs(x); fill(ctx, sleeve, () => { ctx.moveTo(s * 5.5, -21.2); ctx.quadraticCurveTo(s * (X - 1), -22.2, s * (X + 1.9), -19.6); ctx.lineTo(s * (X - 1.9), -17.4); ctx.quadraticCurveTo(s * (X - 3.2), -18.8, s * 7.4, -18.6); ctx.closePath(); }); } /* 第 17 版：肩膀外移時，斜肩接回軀幹（縫從腋下開始） */
    rotAt(ctx, x, -20, shoulderA);
    if (!handOnly) fill(ctx, sleeve, () => rr(ctx, x - 2, -21, 4, ua + 1, 2));       // 上臂
    const ONE = SEAM && !SEAMIN && (!side || ARM.sideOne) && !elbowA; /* 審查小修 B（美術 PM 11-06）：正面、背面打直的手臂（關鍵姿勢、背面持盾的布料袖）描邊也只描一圈，沿上臂＋前臂合成的一條，手肘沒有橫線（審查：「兩個相扣的鏈環」）；側面、彎肘照舊兩段 */
    if (!(SEAMIN && !elbowA) && !ONE) seam(() => ctx.roundRect(x - 2, -21, 4, ua + 1, 2));
    if (!handOnly && !NOPAD && kind === "plate" && it?.form !== "half") fill(ctx, mix(c, "#ffffff", 0.25), () => { ctx.beginPath(); ctx.ellipse(x, -19.5, 3.5, 2.5, 0, 0, TAU); });
    rotAt(ctx, x, -20 + ua, elbowA);
    if (!handOnly) fill(ctx, sleeve, () => rr(ctx, x - 2, -20.5 + ua, 4, fa, 2));    // 前臂
    if (!handOnly && (FILLARM || FREEARM) && !side && !elbowA) fill(ctx, sleeve, () => rr(ctx, x - 2, -21, 4, ua + fa + 0.5, 2)); /* 第 17 版 B 批審查：空手微微離開時，手肘和軀幹之間不留背景色小洞（上臂、前臂連成一條） */
    if (!handOnly && (FILLARM || FREEARM) && !side && !elbowA && !SEAM && !TINT && ARM.edge) armEdge(ctx, sleeve, x, ua + fa + 0.5); /* 第 17 版 B 批補修（美術 PM 11-06）：逐隻手臂判斷，FREEARM＝這隻手臂空著（主手拿武器時的另一隻手，例如正面持盾那隻）也畫 */ /* 可行性樣張（tools/arm-edge-compare.html）：布料類的空手、拳套手臂沿「上臂＋前臂合成的一條」描一條連續的邊線（手肘沒有橫線），和同色軀幹分得開；第 17 版 B 批補修起預設 E 帶 edge（inner 0.9／0.45）；已有 seam 描邊的情況（SEAM：側面、關鍵姿勢、背面持盾、盔甲類）不重畫 */
    if (ONE) { if (!handOnly && !TINT) { fill(ctx, sleeve, () => rr(ctx, x - 2, -21, 4, ua + fa + 0.5, 2)); seam(() => ctx.roundRect(x - 2, -21, 4, ua + fa + 0.5, 2)); if (!NOPAD && kind === "plate" && it?.form !== "half") fill(ctx, mix(c, "#ffffff", 0.25), () => { ctx.beginPath(); ctx.ellipse(x, -19.5, 3.5, 2.5, 0, 0, TAU); }); } } /* 先用袖色把上臂、前臂填成一條再描；肩甲蓋回上面 */
    else if (!(SEAMIN && !elbowA)) seam(() => ctx.roundRect(x - 2, -20.5 + ua, 4, fa, 2));
    else if (!handOnly && !TINT) { seam(() => ctx.roundRect(x - 2, -21, 4, ua + fa + 0.5, 2)); if (!NOPAD && kind === "plate" && it?.form !== "half") fill(ctx, mix(c, "#ffffff", 0.25), () => { ctx.beginPath(); ctx.ellipse(x, -19.5, 3.5, 2.5, 0, 0, TAU); }); } /* 第 17 版 B 批審查：打直的手臂（肘角 0）只描一圈，從肩到手腕連成一條，不再上下兩圈像鏈環；肩甲再蓋回上面 */
    if (!handOnly && gear.hands && gear.hands.kind === "bracers") { const [bc, bd] = colors(gear.hands); fill(ctx, TINT ?? bc, () => rr(ctx, x - 2.3, hy - 3.1, 4.6, 2.4, 0.8)); fill(ctx, TINT ?? bd, () => ctx.rect(x - 2.3, hy - 1.7, 4.6, 0.6)); } // 護腕：四方向都跟著前臂
    const fistC = TINT ?? ((k0) => (FARH ? mix(k0, "#000000", FARH) : k0))(gear.hands && gear.hands.kind !== "bracers" ? hc : look.skin);
    if (!handOnly) fill(ctx, fistC, () => { ctx.beginPath(); ctx.arc(x, hy, 2.4, 0, TAU); });
    if (!handOnly && (FILLARM || FREEARM) && !side && !elbowA && !SEAM && !TINT && ARM.edge && ARM.edge.fist && qWeapon(gear.main_hand)?.kind !== "gauntlet") fistEdge(ctx, sleeve, fistC, x, hy, ua, fa); /* 可行性樣張（tools/fist-edge-compare.html，使用者：「粗內線可以但拳頭也要有」）：空手的拳頭也描一條線，和袖子分得開；生效條件和 armEdge 相同，拳套（glove 整個蓋住拳頭、自己有護腕和指節板）不畫；第 17 版 B 批補修起預設 E 帶 edge.fist（ring 0.9／0.45） */
    // 第 8 版：拳套戴在手上，兩隻手都戴、包住整個拳頭，指節朝前臂的延長線（使用者：「拳套根本沒有套著」）
    if (!handOnly && !TINT && qWeapon(gear.main_hand)?.kind === "gauntlet") glove(ctx, gear.main_hand, x, hy);
    // 第 8 版：手上的東西（武器、匕首、書）畫在手的上面，握把從拳頭上穿過去（使用者：「法仗塗層要在最上面」）
    rotAt(ctx, x, hy, SO - SOd); /* sideOne：手的座標系轉回原本前臂的角度 */
    if (inHand) inHand([x, hy], ctx);
    const hand = [x, hy];
    ctx.restore();
    return hand;
  }
  /* 可行性樣張：ARM.elbow＝手肘彎多少（弧度）。正面、背面原本打直的手臂（肘角 0）改成兩段：上臂往外、前臂往內，手肘朝外側凸出。
     拳頭位置不變：肩到拳頭的距離固定（＝上臂＋前臂），兩段照比例拉長 s 倍才搆得到；IK 解出上臂角 sA − σα、肘角 σe（σ＝往外的方向）。
     手上的東西（inHand、拳套）在手的座標系畫，轉回原本的角度，武器角度不變。描邊（SEAM 一圈、盔甲內框、粗內線）沿兩段合成的一條外形描，手肘處轉折、沒有橫線。 */
  function armBent(ctx, unit, x, sA0, inHand, handOnly, len) {
    const { look, gear } = unit, it = gear.body, kind = it?.kind ?? "shirt";
    const [c] = colors(it), sleeve = TINT ?? (SEAMIN ? mix(c, "#000000", 0.15) : c), ua0 = len ? len[0] : UA, fa0 = len ? len[1] : FA, e = ARM.elbow;
    const r = ua0 + fa0, s = r / Math.sqrt(ua0 * ua0 + fa0 * fa0 + 2 * ua0 * fa0 * Math.cos(e)), ua = ua0 * s, fa = fa0 * s, hy = -20 + ua + fa;
    const al = Math.asin(Math.min(1, (fa * Math.sin(e)) / r)), sg = x > 0 ? 1 : -1, sA = sA0 - sg * al, eA = sg * e;
    const [hc] = gear.hands ? colors(gear.hands) : [look.skin, look.skin];
    ctx.save();
    const T0 = ctx.getTransform(); rotAt(ctx, x, -20, sA); const T1 = ctx.getTransform(); rotAt(ctx, x, -20 + ua, eA); const T2 = ctx.getTransform(); ctx.setTransform(T0);
    const seg = (i) => { ctx.setTransform(i === 1 ? T2 : T1); if (i === 2) { ctx.moveTo(x + 2, -20 + ua); ctx.arc(x, -20 + ua, 2, 0, TAU); } else if (i) ctx.roundRect(x - 2, -20.5 + ua, 4, fa + 0.5, 2); else ctx.roundRect(x - 2, -21, 4, ua + 1, 2); ctx.setTransform(T0); }; /* 0 上臂、1 前臂、2 手肘的圓（兩段在手肘處圓滑接起來，不凹一個角） */
    const both = () => { seg(0); seg(1); seg(2); };
    /* 只描合成外形：每段的邊只畫在另一段外面；inner＝線 clip 在手臂裡面；half＝只畫靠身體那半邊（armEdge 的 inner 模式，在各段自己的座標系裡切） */
    const outline = (col, w, inner, half) => { for (const i of [0, 1, 2]) { ctx.save(); if (inner) { ctx.beginPath(); both(); ctx.clip(); }
      for (const j of [0, 1, 2]) if (j !== i) { ctx.beginPath(); ctx.rect(-80, -120, 160, 200); seg(j); ctx.clip("evenodd"); }
      if (half) { ctx.setTransform(i === 1 ? T2 : T1); ctx.beginPath(); if (x > 0) ctx.rect(x - 2.5, -22, 2.5, 40); else ctx.rect(x, -22, 2.5, 40); ctx.setTransform(T0); ctx.clip(); }
      ctx.strokeStyle = col; ctx.lineWidth = w; ctx.beginPath(); seg(i); ctx.stroke(); ctx.restore(); } };
    const pad = () => { if (!NOPAD && kind === "plate" && it?.form !== "half") { ctx.setTransform(T1); fill(ctx, mix(c, "#ffffff", 0.25), () => { ctx.beginPath(); ctx.ellipse(x, -19.5, 3.5, 2.5, 0, 0, TAU); }); ctx.setTransform(T0); } };
    if (!handOnly) {
      fill(ctx, sleeve, both);
      if (!TINT) {
        if (SEAMIN) outline(mix(c, "#000000", 0.5), 1.6, true, false);
        else if (SEAM) outline(mix(c, "#000000", EDGEK ?? 0.38), EDGEK ? 0.9 : 0.55, false, false);
        else if ((FILLARM || FREEARM) && ARM.edge) { const E = ARM.edge; outline(mix(sleeve, "#000000", EDGEK ?? E.k ?? 0.38), E.w ?? 0.55, true, (E.mode ?? "ring") === "inner"); }
      }
      pad();
      ctx.setTransform(T2);
      if (gear.hands && gear.hands.kind === "bracers") { const [bc, bd] = colors(gear.hands); fill(ctx, TINT ?? bc, () => rr(ctx, x - 2.3, hy - 3.1, 4.6, 2.4, 0.8)); fill(ctx, TINT ?? bd, () => ctx.rect(x - 2.3, hy - 1.7, 4.6, 0.6)); }
      const fistC = TINT ?? (gear.hands && gear.hands.kind !== "bracers" ? hc : look.skin);
      fill(ctx, fistC, () => { ctx.beginPath(); ctx.arc(x, hy, 2.4, 0, TAU); });
      if ((FILLARM || FREEARM) && !SEAM && !TINT && ARM.edge && ARM.edge.fist && qWeapon(gear.main_hand)?.kind !== "gauntlet") fistEdge(ctx, sleeve, fistC, x, hy, ua, fa);
      if (!TINT && qWeapon(gear.main_hand)?.kind === "gauntlet") glove(ctx, gear.main_hand, x, hy);
    }
    ctx.setTransform(T2); rotAt(ctx, x, hy, sA0 - sA - eA); /* 手的座標系轉回打直時的角度：武器、書、匕首的角度不變 */
    if (inHand) inHand([x, hy], ctx);
    ctx.restore();
    return [x, hy];
  }
  /* 可行性樣張：ARM.edge = { mode: "ring" | "inner", w, k }。ring＝沿合成那條手臂描整圈；inner＝只畫靠身體那一側（朝 x=0 的半邊）。
     線 clip 在手臂形狀裡面（輪廓不變寬），顏色 mix(sleeve, 黑, k)，w 是線寬（畫布單位）。盔甲類（SEAMIN）不走這裡。 */
  function armEdge(ctx, sleeve, x, h) {
    const e = ARM.edge, w = e.w ?? 0.55, k = EDGEK ?? e.k ?? 0.38, mode = e.mode ?? "ring";
    ctx.save(); ctx.beginPath(); ctx.roundRect(x - 2, -21, 4, h, 2); ctx.clip();
    if (mode === "inner") { ctx.beginPath(); if (x > 0) ctx.rect(x - 2.5, -22, 2.5, h + 2); else ctx.rect(x, -22, 2.5, h + 2); ctx.clip(); }
    ctx.strokeStyle = mix(sleeve, "#000000", k); ctx.lineWidth = w; ctx.beginPath(); ctx.roundRect(x - 2, -21, 4, h, 2); ctx.stroke(); ctx.restore();
  }
  /* 可行性樣張：ARM.edge.fist = { mode: "ring" | "seam", w, k }。ring＝拳頭整圈描邊，clip 在拳頭圓裡再描（輪廓不變寬），顏色 mix(拳頭色, 黑, k)（拳頭色＝膚色或手套色）；
     seam＝只畫拳頭和袖子的交界：clip 到拳頭圓 ∩ 前臂，沿拳頭圓描，顏色和手臂粗內線同一色 mix(sleeve, 黑, k)。 */
  function fistEdge(ctx, sleeve, fistC, x, hy, ua, fa) {
    const f = ARM.edge.fist, w = f.w ?? 0.55, k = EDGEK ?? f.k ?? 0.45, mode = f.mode ?? "ring";
    ctx.save(); ctx.beginPath(); ctx.arc(x, hy, 2.4, 0, TAU); ctx.clip();
    if (mode === "seam") { ctx.beginPath(); ctx.roundRect(x - 2, -20.5 + ua, 4, fa, 2); ctx.clip(); }
    ctx.strokeStyle = mix(mode === "seam" ? sleeve : fistC, "#000000", k); ctx.lineWidth = w; ctx.beginPath(); ctx.arc(x, hy, 2.4, 0, TAU); ctx.stroke(); ctx.restore();
  }
  // 拳套（第 8 版）：鋼製拳套包住拳頭（比手大一圈），前臂那頭有護腕、指節那頭一道深色指節板；在手的座標系畫（+y＝指節方向）
  function glove(ctx, it, x, y) {
    const [k, d] = wc(it, "steel");
    fill(ctx, d, () => rr(ctx, x - 2.7, y - 4.4, 5.4, 2.4, 0.8));            // 護腕
    fill(ctx, k, () => ctx.arc(x, y, 2.9, 0, TAU));                           // 包住拳頭
    fill(ctx, d, () => rr(ctx, x - 2.5, y + 1.0, 5, 1.3, 0.6));               // 指節板
    fill(ctx, "rgba(255,255,255,0.35)", () => ctx.arc(x - 1, y - 0.8, 0.9, 0, TAU));
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
    fill(ctx, it?.hilt ?? (W >= 4 ? "#d8b04a" : "#8a6a2a"), () => ctx.roundRect(-4.5, -4, 9, 2, 1)); // 雙手劍：金色護手（第 8 版）
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
    greatsword_kf: { len: 14.7, hold: { side: 0.75, front: -0.25 }, draw: (c, it) => sword(c, it, 11.7, 4) }, /* 第 14 版：正面、背面拄劍（兩手較低），劍尖仍在地面線 */
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
      c.strokeStyle = it?.color ?? "#5e3b1f"; c.lineWidth = 1.4; c.lineCap = "round";
      if (POSE && typeof POSE.wpn === "number") {
        fill(c, "#4a3020", () => c.roundRect(-1.1, -5, 2.2, 6.5, 0.8));
        // 出招（6M／6N 片段）：鞭身拉直往前抽出去，梢端一點彎（11-04 晚看出招特寫：命中格鞭子往下垂，不像抽出去）
        c.beginPath(); c.moveTo(0, -5); c.quadraticCurveTo(1.2, -15, 0, -24); c.stroke();
        c.lineWidth = 0.8; c.beginPath(); c.moveTo(0, -24); c.quadraticCurveTo(-1.5, -27, 0.6, -29); c.stroke();
      } else {
        // 待機（第 7 版）：鞭身從握把頂端垂下來（照畫面的「下」，不跟著握把的角度往上翹；審查：「鞭身往上翹，沒有垂下來」），鞭梢在腳邊小幅甩動
        // 畫布方向 → 握把座標：下＝(0,1)；角色前方＝朝東 (1,0)、朝西 (−1,0)（stamp 鏡像）
        const m = c.getTransform(), det = m.a * m.d - m.b * m.c, loc = (x, y) => { const v = [(m.d * x - m.c * y) / det, (-m.b * x + m.a * y) / det], l = Math.hypot(v[0], v[1]) || 1; return [v[0] / l, v[1] / l]; };
        // 第 8 版：鞭柄握在拳頭裡、往下穿出拳頭，鞭身從拳頭下方的柄尾垂下（審查：「鞭身從手的右上方長出來」）
        const D = loc(0, 1), N = loc(WEST ? -1 : 1, 0);
        const E = [D[0] * 4.2, D[1] * 4.2], w = Math.sin(pz("lash") * TAU) * 1.6, at = (u, v) => [E[0] + u * D[0] + v * N[0], E[1] + u * D[1] + v * N[1]];
        c.save(); c.lineWidth = 2.2; c.strokeStyle = "#4a3020"; c.beginPath(); c.moveTo(-D[0] * 1.6, -D[1] * 1.6); c.lineTo(E[0], E[1]); c.stroke(); c.restore(); // 鞭柄（上端藏在拳頭裡）
        const p1 = at(2, 0.3), p2 = at(4, 0.8 + w * 0.3), p3 = at(5.4, 2.2 + w * 0.6), p4 = at(5.2, 6.5 + w);
        c.beginPath(); c.moveTo(E[0], E[1]); c.bezierCurveTo(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1]); c.stroke();
        c.lineWidth = 0.8; c.beginPath(); c.moveTo(p3[0], p3[1]); c.quadraticCurveTo(...at(5.8, 4.4 + w), p4[0], p4[1]); c.stroke(); // 鞭梢在腳前的地上往前捲
      }
    } },
    gauntlet: { len: 4, hold: { side: 1.0, front: 0 }, draw: (c, it) => {
      // 第 8 版：拳套戴在手上（arm() 畫拳套本體）；這裡只畫和手重疊的拳面，拳刃、爪從指節往前伸
      const [k] = wc(it, "steel");
      fill(c, k, () => c.arc(0, 0, 2.9, 0, TAU));
      if (it?.form === "katar" || it?.form === "claw") fill(c, k, () => { c.moveTo(-1.2, -2.6); c.lineTo(0, -9); c.lineTo(1.2, -2.6); c.closePath(); });
    } },
    staff: { len: 32, hold: { side: 0, front: 0 }, draw: (c, it) => {
      const orb = ({ fire: "#ff6a1a", water: "#4aa8ff", ice: "#8fe3ff", lightning: "#fff36b", poison: "#7ddc3a", wind: "#7fe0c0", earth: "#b0814a", holy: "#ffd75e", shadow: "#9a6ad8" })[it?.element] ?? "#c8bcff"; // 同 paperdoll 的 ELEMENT_TINT
      fill(c, "#6a4420", () => c.rect(-1.1, -30, 2.2, 39)); // 杖身到 +9，下手握在 +6
      const g = pz("glow"); // 待機的光脈動（idleWeapons.js）：0～1
      c.save(); c.globalAlpha = 0.35 + 0.35 * g; fill(c, orb, () => c.arc(0, -32, 6.5 + 2 * g, 0, TAU)); c.restore();
      fill(c, orb, () => c.arc(0, -32, 3.6, 0, TAU));
      fill(c, "rgba(255,255,255,0.8)", () => c.arc(-1.2, -33.2, 1.1, 0, TAU));
    } },
    /* 畫圖 agent 11-07：手持物（修士）。握把在原點、四指（it.skin）橫過握柄，柄從拳頭上下穿出；照持武器規則（手臂張開、不畫空手內線與拳頭圈） */
    whisk: { len: 7, hold: { side: 0.3, front: 0 }, draw: (c, it) => {
      fill(c, "#8a5a2a", () => c.roundRect(-0.65, -6.6, 1.3, 9.4, 0.6)); fill(c, "#e8bb48", () => c.roundRect(-0.9, -7.2, 1.8, 1.2, 0.5));
      fill(c, it?.color ?? "#f2f0ea", () => { c.moveTo(-0.9, -7); c.quadraticCurveTo(-5.6, -7.6, -6.4, 1.6); c.quadraticCurveTo(-4.6, 3.2, -3.2, 0.6); c.quadraticCurveTo(-2.4, -4.4, 0.9, -6.6); c.closePath(); });
      heldFingers(c, it);
    } },
    talisman: { len: 9, hold: { side: 0.25, front: 0.15 }, draw: (c, it) => {
      fill(c, it?.color ?? "#f2d860", () => c.roundRect(-1.5, -9.4, 3, 8.4, 0.3));
      c.strokeStyle = "#c0392b"; c.lineWidth = 0.45; c.lineCap = "round"; c.beginPath(); c.moveTo(0, -8.6); c.lineTo(-0.7, -7.2); c.lineTo(0.7, -5.8); c.lineTo(-0.5, -4.4); c.lineTo(0.3, -3.2); c.stroke();
      heldFingers(c, it);
    } },
    puppet_strings: { len: 4, hold: { side: 0, front: 0 }, draw: (c, it) => { // 十字木架（垂下的線由呼叫端在外框之後畫）
      fill(c, "#8a6a48", () => c.roundRect(-4.4, -0.6, 8.8, 1.3, 0.5)); fill(c, "#8a6a48", () => c.roundRect(-0.65, -3.6, 1.3, 7.6, 0.5));
      heldFingers(c, it);
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
      const [k] = wc(it, "wood"), pull = BOWP && BOWP.pull != null ? BOWP.pull : typeof POSE?.pull === "number" ? POSE.pull : 0, ex = Math.sin(BOW_A) * BOW_R, ey = BOW_EY;
      const st = () => { if (BOWM) { c.save(); c.setTransform(BOWM); c.stroke(); c.restore(); } else c.stroke(); }; /* 第 9 版：正面、背面的弓是斜看的（壓扁），線寬照畫面算 */
      c.strokeStyle = "#e8e8e8"; c.lineWidth = 0.8; c.beginPath(); c.moveTo(-ex, ey); c.lineTo(0, ey + pull); c.lineTo(ex, ey); st(); /* 第 9 版：弦不用半透明，剪影外框不會從弦透出來（審查：「放箭的弓和弦之間有暗色殘影」） */
      c.strokeStyle = k; c.lineWidth = 2.2; c.lineCap = "round"; c.beginPath(); c.arc(0, BOW_R, BOW_R, -Math.PI / 2 - BOW_A, -Math.PI / 2 + BOW_A); st();
      fill(c, "#4a3020", () => c.roundRect(-1.6, -1.6, 3.2, 3.2, 0.8)); // 弓把（皮纏）
      if (!(BOWP && BOWP.noArrow) && (pull > 0.5 || pz("nock") > 0 || (BOWP && BOWP.nock))) { // 拉弓，或待機時箭搭在弦上（第 8 版：關鍵姿勢一律搭箭）
        c.strokeStyle = "#c8a070"; c.lineWidth = 0.9; c.beginPath(); c.moveTo(0, ey + pull); c.lineTo(0, -6); st();
        if (BOWM) { // 斜看的弓：箭頭在畫面座標畫（不跟著壓扁）
          const m = c.getTransform(), inv = BOWM.inverse(), P = (x, y) => inv.transformPoint(m.transformPoint(new DOMPoint(x, y)));
          const a0 = P(0, ey), a1 = P(0, -8), l = Math.hypot(a1.x - a0.x, a1.y - a0.y) || 1, ux = (a1.x - a0.x) / l, uy = (a1.y - a0.y) / l;
          c.save(); c.setTransform(BOWM); fill(c, "#c3ccd6", () => { c.moveTo(a1.x - ux * 2.4 - uy * 1.2, a1.y - uy * 2.4 + ux * 1.2); c.lineTo(a1.x, a1.y); c.lineTo(a1.x - ux * 2.4 + uy * 1.2, a1.y - uy * 2.4 - ux * 1.2); c.closePath(); }); c.restore();
        } else fill(c, "#c3ccd6", () => { c.moveTo(-1.2, -5.6); c.lineTo(0, -8); c.lineTo(1.2, -5.6); c.closePath(); });
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
  function heldFingers(c, it) { const k = it?.skin ?? "#f1c9a5"; fill(c, k, () => c.roundRect(-2.3, -1.1, 4.6, 2.2, 1)); c.strokeStyle = mix(k, "#000000", 0.3); c.lineWidth = 0.35; c.beginPath(); c.moveTo(-1.6, 0.05); c.lineTo(1.6, 0.05); c.stroke(); }
  const HELD_OFF = ["orb", "whisk", "talisman", "puppet_strings"]; /* 畫圖 agent 11-07：副手拿這些時畫成對應物件（不是書）；只在這些 kind 出現時生效 */
  const offHeld = (gear) => (gear.off_hand && HELD_OFF.includes(gear.off_hand.kind) ? gear.off_hand : null);
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
  function mainWeapon(ctx, it, hand, a, view, short = false, offL = null, mg = 0, M = null) { /* 第 13 版：M＝自訂 2×2 變換（背面的弩朝前、縮短），取代旋轉 a */
    const q0 = qWeapon(it), q = q0 && short && q0.kind === "greatsword" ? { ...q0, W: short === "f" ? QW.greatsword_kf : QW.greatsword_k } : q0;
    if (!q) { if (it) PD.drawWeapon(ctx, it, hand[0], view !== "back"); return; }
    ctx.save(); ctx.translate(hand[0], hand[1]); if (M) ctx.transform(M[0], M[1], M[2], M[3], 0, 0); else ctx.rotate(a);
    if (mg) ctx.translate(0, -mg); /* 主手握在武器座標 (0,mg) */
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
  /* 第 15 版：OUTA＝持武器的手臂往外張開的角度（打直、不彎肘）；OH＝右肩打直張開時手的位置（正面左右對調） */
  /* 第 17 版第 2 項（使用者：「兩隻手太開了」）：手臂往外張開集中在 ARM_SPREAD 一個開關：a＝手臂往外的角度、dx＝肩膀往外移多少、tilt＝法杖和長柄往外傾多少。
     A＝第 16 版（預設）；D＝貼身直垂：肩膀不動，手臂從肩線直直垂下、描邊和身體相接，杖和長槍直立；E＝和 D 一樣，手臂微微往外，留 1～2px 背景色。
     （使用者：「BC都很醜整個看起來就是很寬沒有更貼的選項嗎」：肩膀外移的 B、C 已刪；dx、tilt、robe、hold 留著，D、E 都是 0）
     肩膀外移時，肩頭用一塊同色的肩頂接回軀幹（見 arm 的 ARM_DX）；杖、柄往外傾，桿子在手臂外側、不把上臂切斷，光暈離開頭。
     只有比較圖（tools/arm-spread-compare.html）在載入前設 window.QDOLL_ARM_SPREAD；其他頁一律用 A，使用者選定後（B 批）才改預設 */
  const ARM_SPREAD_SET = { A: { a: 0.7, dx: 0, tilt: 0, robe: 0, hold: 0, sw: 0, swa: 0 }, D: { a: 0, dx: 0, tilt: 0, robe: 0, hold: 0, sw: 1.6, swa: 0, bk: -1, shf: true, po: 1.6 }, E: { a: 0.325, dx: 0, tilt: 0, robe: 0, hold: 0, sw: 1, swa: 0, bk: -1, shf: true, po: 0, shA: 0.2, ea: 0.09, edge: { mode: "inner", w: 0.9, k: 0.45, fist: { mode: "ring", w: 0.9, k: 0.45 } }, sideOne: true } }; /* 側面打直手臂只描一圈（2026-11-06 使用者看 tools/elbow-compare.html 選第 5 欄：「5 欄」）：sideOne＝側面肘角 ≤ 0.15 的手臂當成打直、袖子描邊從肩到手腕只描一圈；彎肘（雙手劍、弓、弩、火槍、持盾的 IK 手臂）照舊兩段；正面、背面不變 */ /* 第 17 版 B 批補修（2026-11-06 使用者定案）：ea 0.09（「ea0.09不錯」）；edge＝布料類空手、拳套的手臂靠身體那側一條粗內線（「粗內線可以但拳頭也要有」）；edge.fist＝空手的拳頭整圈深色邊（「整圈粗」）；盔甲類維持袖子內框（SEAMIN），拳套本身不加拳頭圈 */ /* 第 17 版 B 批：E 的 sw 1＝單手劍在拳頭裡往外 1（握把仍在拳頭裡），金色護手不壓進軀幹；shA＝正面持盾的左手臂角度（手被盾擋住，少張開一點，盾心仍對準拳頭），輪廓不比第 15 版寬 */ /* sw＝單手劍在拳頭裡往外偏多少、swa＝劍身多往外傾多少（護手少壓進身體，手臂不動）；bk＝書心在拳頭外側多少（A 沒寫＝2，D、E 往內 1，輪廓不比第 15 版寬）；shf＝正面的盾心對準拳頭；po＝杖、長柄在拳頭裡往外偏多少（桿子仍在拳頭裡，少壓到臉）。B、C（肩膀外移）使用者不選，已刪 */
  const ARM = (typeof window.QDOLL_ARM_SPREAD === "object" && window.QDOLL_ARM_SPREAD) || ARM_SPREAD_SET[window.QDOLL_ARM_SPREAD] || ARM_SPREAD_SET.E; /* 第 17 版 B 批（使用者：「E」）：預設改成 E；比較圖的 A 欄另外設 "A" */
  const ARM_SPREAD = ARM.a, ARM_DX = ARM.dx, ARM_TILT = ARM.tilt, SHX = 8.5 + ARM_DX;
  const OUTA = ARM_SPREAD;
  /* 第 17 版第 3 項預覽（B 批才正式改）：QDOLL_SHIELD_CENTER＝背面持盾的左拳在盾的正中央握把上；只有比較圖會設 */
  const SHIELD_CENTER = window.QDOLL_SHIELD_CENTER !== false; /* 第 17 版 B 批第 3 項：正式套用，背面的左拳一律在盾的正中央握把上 */
  function fk(x, sA, eA, len = null) { const ua = len ? len[0] : UA, fa = len ? len[1] : FA, e = [x - ua * Math.sin(sA), -20 + ua * Math.cos(sA)]; return [e[0] - fa * Math.sin(sA + eA), e[1] + fa * Math.cos(sA + eA)]; }
  const OH = fk(SHX, -OUTA, 0), OH16 = fk(8.5, -ARM_SPREAD_SET.A.a, 0); /* OH16：第 16 版的手高，法杖握點照手高差補回，杖尾留在地面線（預設時差 0） */
  /* 第 16 版（使用者：「側面的那隻手的肩膀太左上了吧」）：側面兩邊肩膀都在軀幹上緣的肩線上（x SSH，軀幹前後 ±5.4 的中間偏前），不再放在身體前緣、臉頰下面。
     SIDEA＝側面持武器的手臂往前下方伸的角度（打直）；SHD＝打直時手的位置。tailG：握點，讓柄尾最低點落在鞋底的地面線（T＝柄尾在武器座標的 y、hw＝柄半寬） */
  const tiltG = (mg, T) => (ARM_TILT ? T - (T - mg) / Math.cos(ARM_TILT) : mg); /* 第 17 版：杖、柄往外傾時握點補回，柄尾仍在地面線（T＝柄尾在武器座標的 y） */
  const sxOf = (gear) => (outOf(gear) ? SHX : 8.5); /* 第 17 版：張開的手臂才跟著肩膀外移 */
  const robeX = (gear) => (ARM.robe && gear.body?.kind === "robe" ? ARM.robe : 0);
  const swOn = (gear) => ["sword", "arcane_blade", "saber"].includes(qWeapon(gear.main_hand)?.kind); /* 第 17 版 B 批：只有十字護手的劍類往外偏（拳套、匕首等不動，輪廓不變寬） */
  const swOff = (p, s, gear) => (ARM.sw && swOn(gear) ? [p[0] + s * ARM.sw, p[1]] : p); /* s：往外是 +x（背面右手）或 −x（正面右手） */
  const holdA = (gear) => (outOf(gear) ? outOf(gear) + ARM.hold + robeX(gear) : 0); /* 持單手武器的手臂角度 */
  const stK = (sx, k, out, gear) => { const r = armK(sx, k, out); if (k.st && robeX(gear)) r.sA += (sx > 0 ? -1 : 1) * robeX(gear); return r; }; /* 穿長袍時握杖的手臂也多往外 */
  const stMg = (sx, k, k0, mg, gear) => (k.st && robeX(gear) ? mg + (fk(sx, k0.sA, k0.eA)[1] - k.hand[1]) / Math.cos(k.a) : mg); /* 手變高時握點補回，杖尾仍在地面線 */
  const SSH = 2, SIDEA = 0.87, SHD = fk(SSH, -SIDEA, 0), SHP = fk(SSH, -1.07, 0); /* SHP：長柄側面的手（第 17 版 B 批審查，柄直一點時手往前，柄不碰鼻尖） */
  const tailG = (T, hw, a, hy = SHD[1]) => T - (0.85 - hy - hw * Math.sin(a)) / Math.cos(a);
  const BOOKA = OUTA; /* 第 16 版：拿書的左手臂和持武器的手一樣打直往外下方（正面、背面對稱，長袍下擺張開時也看得到空隙），書跟著手 */
  function ik(x, t, out, len = null) {
    const UA = len ? len[0] : 5, FA = len ? len[1] : 5.5, REACH = UA + FA - 0.1; /* 第 9 版：可指定手臂長度 */
    const dx = t[0] - x, dy = t[1] + 20, r0 = Math.hypot(dx, dy), r = Math.min(Math.max(r0, Math.abs(UA - FA) + 0.05), REACH);
    const phi = Math.atan2(-dx, dy), al = Math.acos((UA * UA + r * r - FA * FA) / (2 * UA * r)), be = Math.acos((UA * UA + FA * FA - r * r) / (2 * UA * FA));
    let best = null;
    for (const sg of [1, -1]) { const sA = phi + sg * al, eA = -sg * (Math.PI - be), sc = out === "down" ? -20 + UA * Math.cos(sA) : (x - UA * Math.sin(sA)) * out; if (!best || sc > best.sc) best = { sA, eA, sc }; } // out＝"down"：手肘在下面
    return { sA: best.sA, eA: best.eA, ok: r0 <= REACH };
  }
  // 正面雙手的位置：主手在畫面左肩 (−8.5,−20)、副手在右肩 (8.5,−20)；在兩隻手都搆得到、作用端露在身體外的位置裡，挑最接近腰前 (0,−12.5) 的
  // 第 8 版：指定手肘方向（dir：從肩膀往手肘的方向），前臂再指向目標 t；回傳關節角度與手實際的位置（側面拉弓：手肘往後抬，手臂不貼在臉上）
  function elbowTo(x, dir, t, len = null) {
    const ua = len ? len[0] : UA, fa = len ? len[1] : FA;
    const l = Math.hypot(dir[0], dir[1]), e = [x + (ua * dir[0]) / l, -20 + (ua * dir[1]) / l], sA = Math.atan2(-dir[0] / l, dir[1] / l);
    const fx = t[0] - e[0], fy = t[1] - e[1], fl = Math.hypot(fx, fy) || 1, eA = Math.atan2(-fx / fl, fy / fl) - sA;
    return { sA, eA, ok: true, h: [e[0] + (fa * fx) / fl, e[1] + (fa * fy) / fl] };
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
    ctx.save(); ctx.translate(0, -pz("shieldUp")); // 待機：舉盾
    PD.drawWeapon(ctx, it, x, true);
    if (it.kind === "shield_round") { ctx.strokeStyle = RIM; ctx.lineWidth = 0.9; ctx.beginPath(); ctx.arc(x, -13.5, 7.1, 0, TAU); ctx.stroke(); if (SHEDGE) { ctx.strokeStyle = OUT; ctx.lineWidth = 0.5; ctx.beginPath(); ctx.arc(x, -13.5, 7.3, 0, TAU); ctx.stroke(); } } /* 第 17 版 B 批審查：穿盔甲時，淺灰盾緣和同色胸甲之間描一道深色邊（畫在盾緣以內，輪廓不變寬） */
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
  function shieldBack(ctx, it, x, dy = 0) {
    const [, d] = colors(it), wood = "#7a5232", strap = "#3a2414";
    ctx.save(); ctx.translate(x - 1, (it.kind === "shield_round" ? -11.8 : -16.5) + dy); // 往上、往外移，蓋住副手的袖子與手（背面手在盾的內側）；第 13 版：圓盾中心在持盾的拳頭上方一點
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
    ctx.restore();
  }
  // 第 9 版：背面持盾的左手臂（使用者：「背後盾牌的左手呢」；審查：「前臂要橫穿過盾背的皮帶，從肩膀一路連到手」）：
  //   上臂從肩膀垂下（畫在身體之後、看得到），前臂往外橫過盾背，前臂上套一條直的臂帶，手握住靠盾緣的握把（握把畫在拳頭上面）
  function shieldArmBack(ctx, unit) {
    TINT = POSE && POSE.tintOff ? POSE.tintOff : null;
    /* 第 13 版（使用者：「背後拿盾的手到底怎磨折的」）：手臂自然垂直往下、不彎手肘，前臂套著橫的臂帶，拳頭握住橫的握把（盾背中間偏下） */
    /* 第 16 版（使用者：「這個也太貼身了 而且為啥左右肩膀顏色不一樣」）：持盾的左手臂和持劍的右手一樣打直往外下方（OUTA），盾跟著手往外移、不貼背；
       臂甲改回和右肩同色（不再加深），和盾緣的區分改用前臂與手外面一圈深色輪廓 */
    const k = { sA: OUTA, eA: 0 }, h = fk(-SHX, k.sA, k.eA), strap = "#3a2414";
    /* 第 16 版審查：拳頭像圓環（「淺灰圓盤加一圈很粗的深色外框，握把從中間橫切過去」）→ 外框改細（0.45）；握把先畫、從拳頭兩邊穿出去；拳頭上畫一排指節（從背後看到手背和彎起來的四指） */
    if (!TINT) { ctx.save(); rotAt(ctx, -SHX, -20, k.sA); fill(ctx, OUT, () => rr(ctx, -SHX - 2.45, -15.9, 4.9, FA + 0.8, 2.4)); ctx.restore(); fill(ctx, OUT, () => ctx.arc(h[0], h[1], 2.85, 0, TAU)); }
    if (!TINT) { ctx.save(); ctx.translate(h[0], h[1]); ctx.rotate(k.sA); fill(ctx, strap, () => rr(ctx, -4.4, -0.8, 8.8, 1.6, 0.6)); ctx.restore(); } // 握把：從拳頭兩邊穿出去（拳頭畫在上面）
    EBOFF = true; arm(ctx, unit, -SHX, k.sA, k.eA, 0, rec("off")); EBOFF = false;
    if (!TINT) {
      const hc = unit.gear.hands && unit.gear.hands.kind !== "bracers" ? colors(unit.gear.hands)[0] : unit.look.skin;
      ctx.save(); ctx.translate(h[0], h[1]); ctx.rotate(k.sA);
      fill(ctx, mix(hc, "#000000", 0.1), () => rr(ctx, -2.1, 0.2, 4.2, 1.9, 0.9)); // 彎起來的四指
      ctx.strokeStyle = mix(hc, "#000000", 0.45); ctx.lineWidth = 0.32; ctx.beginPath(); for (const x of [-1.05, 0, 1.05]) { ctx.moveTo(x, 0.35); ctx.lineTo(x, 1.95); } ctx.moveTo(-2, 0.2); ctx.lineTo(2, 0.2); ctx.stroke(); // 指節分段
      ctx.restore();
    }
    TINT = null;
    { const m = fk(-SHX, k.sA, 0, [UA + 1.6, 0]); ctx.save(); ctx.translate(m[0], m[1]); ctx.rotate(k.sA); fill(ctx, strap, () => rr(ctx, -2.6, -0.75, 5.2, 1.5, 0.5)); ctx.restore(); } // 臂帶：橫套在前臂上（跟著前臂的角度）
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
        ctx.save(); ctx.translate(3.4, -14.6); ctx.rotate(0.2); /* 第 13 版：箭袋直一點、靠右肩那側，不斜穿整個背（修正清單：「箭袋斜穿過背部」） */
        fill(ctx, c, () => rr(ctx, -2.6, -9, 5.2, 15, 1.8)); fill(ctx, d, () => ctx.rect(-2.6, -2, 5.2, 1.2)); fill(ctx, d, () => ctx.rect(-2.6, 3, 5.2, 1.2));
        if (tube) fill(ctx, d, () => rr(ctx, -3, -11, 6, 3, 1.2));
        else for (const [x, col] of [[-1.4, "#e8e0c8"], [0.2, "#d23c3c"], [1.6, "#e8e0c8"]]) fill(ctx, col, () => { ctx.moveTo(x - 0.7, -9); ctx.lineTo(x, -13.5); ctx.lineTo(x + 0.7, -9); ctx.closePath(); });
        ctx.restore();
        return;
      }
      if (S && layer === "behind") { // 側面：箭袋在背後，出口在肩後上方，箭羽露在後腦旁
        ctx.save(); ctx.translate(-6, -15.5); ctx.rotate(-0.28); // 第 8 版：箭袋貼著背、朝東朝西同一個斜度（使用者：「箭袋歪斜」）
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
    if (it.kind === "fur_collar" || it.kind === "feathers") { neckWide(ctx, it, view); return; } /* 畫圖 agent 11-07：毛領、白羽披肩（畫在身體上、手臂和胸前武器下面、頭下面） */
    if (B) { ctx.strokeStyle = c; ctx.lineWidth = 0.8; ctx.beginPath(); ctx.moveTo(-3.5, -20.8); ctx.quadraticCurveTo(0, -20.2, 3.5, -20.8); ctx.stroke(); return; } // 背面：只看到頸後一小段
    if (S) {
      ctx.strokeStyle = c; ctx.lineWidth = 0.8; ctx.beginPath(); ctx.moveTo(-1.5, -20.8); ctx.quadraticCurveTo(3.8, -17.6, 5.4, -18.4); ctx.stroke();
      fill(ctx, bead ? c : "#e8bb48", () => ctx.ellipse(5.4, -17.4, 1, 1.3, 0, 0, TAU)); // 墜子在胸前前緣
      return;
    }
    if (bead) for (let i = 0; i <= 6; i++) { const t = i / 6, bx = -4.5 + 9 * t, by = -20.5 + 4.2 * Math.sin(t * Math.PI); fill(ctx, c, () => ctx.arc(bx, by, 0.9, 0, TAU)); }
    else { ctx.strokeStyle = c; ctx.lineWidth = 0.8; ctx.beginPath(); ctx.moveTo(-4.5, -20.6); ctx.quadraticCurveTo(0, -14.5, 4.5, -20.6); ctx.stroke(); fill(ctx, "#e8bb48", () => { ctx.moveTo(0, -17.8); ctx.lineTo(1.4, -16.2); ctx.lineTo(0, -14.4); ctx.lineTo(-1.4, -16.2); ctx.closePath(); }); }
  }
  function neckWide(ctx, it, view) {
    const S = view === "side", fur = it.kind === "fur_collar", c = it.color ?? (fur ? "#d8c8a8" : "#f2f0ea"), d = mix(c, "#000000", 0.2);
    if (fur) { // 毛領：脖子一圈蓬鬆毛
      const xs = S ? [-5.6, -3, -0.4, 2.2, 4.8] : [-8, -5.4, -2.7, 0, 2.7, 5.4, 8];
      fill(ctx, c, () => { for (const x of xs) { ctx.moveTo(x + 1.9, -20.4); ctx.ellipse(x, -20.4 + Math.abs(x) * 0.06, 1.9, 1.7, 0, 0, TAU); } });
      ctx.strokeStyle = d; ctx.lineWidth = 0.4; ctx.beginPath(); ctx.moveTo(xs[0], -19.2); ctx.lineTo(xs[xs.length - 1], -19.2); ctx.stroke();
      return;
    }
    // 白羽披肩：肩上一圈白羽，羽尖到胸口上緣（y −16 左右）
    const tips = S ? [[-6, -16.4], [-3.4, -15.6], [-0.6, -15.8], [2.2, -16], [5, -16.8]] : [[-10, -17.2], [-6.6, -16.2], [-3.2, -15.8], [0, -15.6], [3.2, -15.8], [6.6, -16.2], [10, -17.2]];
    const top = S ? [[-7, -21.6], [6.2, -21]] : [[-8.4, -21.6], [8.4, -21.6]];
    fill(ctx, c, () => { ctx.moveTo(top[0][0], top[0][1]); ctx.quadraticCurveTo(0, -22.6, top[1][0], top[1][1]); const L = tips.length; ctx.lineTo(tips[L - 1][0] + 0.6, tips[L - 1][1] - 2); for (let i = L - 1; i >= 0; i--) { const [x, y] = tips[i]; ctx.quadraticCurveTo(x + 1.2, y + 0.4, x, y); ctx.quadraticCurveTo(x - 1.2, y - 1.6, x - 1.4, y - 2.4); } ctx.closePath(); });
    ctx.strokeStyle = d; ctx.lineWidth = 0.45; ctx.lineCap = "round"; for (const [x, y] of tips) { ctx.beginPath(); ctx.moveTo(x, y - 0.4); ctx.lineTo(x * 0.8, y - 3.4); ctx.stroke(); }
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
  // 格式：hand＝主手手掌位置、a＝武器角度（作用端方向，0＝朝上、順時針為正）、og＝副手握點（武器座標）、mg＝主手握在武器座標的哪一點
  const CLASS_OF = { greatsword: "greatsword", spear: "polearm", scythe: "polearm", bow: "bow", crossbow: "gun", gun: "gun", staff: "staff" };
  /* 雙手劈：蓄力 → 舉到臉前上方（劍從臉的前方外側往上）→ 往前下方劈。副手在主手下方 5.6（靠劍柄尾）；命中時主手往前伸，副手才不會縮到身體後面（審查：「命中只畫一隻手」）
     第 10 版：舉到臉前上方（mid）手往前上移，護手在臉的前方上面、不壓到鼻尖（審查：「g2 護手左端蓋到鼻尖」）
     第 17 版（使用者：「扛在肩上放棄 沒救」）：雙手劍只留拄劍，蓄力改成從拄劍把劍提起來：兩手照拄劍那樣上下握柄，劍尖從地上翻起，劍舉到身體斜前上方（劍尖朝前上）；朝東、朝西同一組 */
  const GS_ATK = { from: { hand: [11, -15.5], a: 0.8 }, mid: { hand: [13.4, -24.4], a: 0.45 }, to: { hand: [10.5, -12], a: 1.9, elbow: 1 }, og: [0, 6.8], mg: 1.2 };
  const KEY = {
    greatsword: { zh: "拄劍：雙手疊握劍柄在胸前，劍垂直往下，劍尖點在兩腳之間",
      /* 第 13 版：雙手往上 0.8～2.2，劍尖落在地面線（y ≈ +1，鞋底 +0.8），不懸空也不插進地裡（使用者：「長度或高度不構」） */
      /* 第 14 版：正面、背面兩手往下 2.4（審查：「上手和下巴同色黏成一團、握柄頂端頂到下巴」）：上手頂和下巴之間露出衣服；劍身改短一點（"f"：劍身 11.7），劍尖仍落在地面線（y ≈ +1.3） */
      front: { hand: [-0.5, -13.4], a: Math.PI, og: [0, 3.2], short: "f" },          // 副手在上 (−0.5,−16.6)
      back: { hand: [0.5, -13.4], a: Math.PI, og: [0, 3.2], short: "f" },            // 手和劍柄在身前被擋住，只在兩腳之間露出劍尖
      side: { hand: [7.4, -15.8], a: Math.PI + 0.06, og: [0, 4], short: true },
      /* 第 14 版：朝西照朝東的鏡像握法：近側左手握下面、遠側右手握上面（mg 4：主手握在劍柄上段，劍的位置不變）。
         原本近側左手握上面，前臂從下面繞上來、壓過遠側下拳，圖層怎麼畫都不對（審查：「r01 朝西遠側下拳蓋在近側前臂上面」） */
      sideW: { hand: [7.2, -19.8], a: Math.PI + 0.06, og: [0, 0], mg: 4, short: true },       // 兩手前後分開握（使用者看出「兩手疊成一團」）：下手 (7.4,−15.8)、上手在上 4（離下巴約 1 單位）
      atk: GS_ATK,
    },
    polearm: { zh: "右手單手拄地、手臂打直往外、柄直立，左手垂下：正面柄在畫面左、背面在畫面右，側面在臉的前方外側",
      /* 第 14 版（美術 PM 決定）：四面同一個姿勢：右手單手拄地、柄直立，左手垂下。正面柄在畫面左、背面在畫面右；柄尾落在鞋底的地面線（y ≈ +0.8）。
         grip＝手握在武器座標哪一點（側面手在胸前 y −14：長槍 −3.8、鐮 gripS −5.8；正面、背面手在 y −12.8，手肘不必彎太多：長槍 −2.6、鐮 −4.6）；flipS＝正面的鐮刃朝畫面左（朝外，不蓋到頭） */
      front: { hand: [-OH[0], OH[1]], a: -ARM_TILT, grip: tiltG(-2.6 + OH[1] + 12.8, 11), gripS: tiltG(-4.6 + OH[1] + 12.8, 9), flipS: true, st: true },  /* 第 15 版：手臂打直往外下方伸（手比第 14 版低，握點跟著往上同樣多，柄尾仍在地面線） */
      back: { hand: [OH[0], OH[1]], a: ARM_TILT, grip: tiltG(-2.6 + OH[1] + 12.8, 11), gripS: tiltG(-4.6 + OH[1] + 12.8, 9), st: true },                      // 背面（第 15 版）：柄在身體外側、拳頭蓋住握的那段，柄從拳頭上下穿出；第 14 版：柄在手臂後面（身體前方），上臂、袖子蓋住拳頭以上的柄，槍尖、鐮刃從肩膀上方露出，柄尾在拳頭下方
      side: { hand: SHP, a: 0.06, grip: tailG(11, 0.9, 0.06, SHP[1]), gripS: tailG(9, 1, 0.06, SHP[1]), /* 第 17 版 B 批審查：斜度回到第 15 版（0.06）；手臂多往前（SHP），柄在鼻尖前方 */ animOg: [0, -8], st: true },  /* 第 16 版：肩膀移到肩線（SSH），手臂打直往前下方（SIDEA），柄多往前傾一點（0.06 → 0.18）不碰鼻尖；握點照手高重算，柄尾仍在地面線。朝東、朝西同一組（兩邊肩膀同一個位置） */  /* 第 15 版：近側右手臂打直往前下方伸（不彎肘），手低 2.15，握點跟著往上，柄尾仍在地面線 */
      /* 第 16 版：朝西不另外給 sideW（肩膀和朝東同一個位置）。第 15 版：朝西右肩在遠側（x 3），手臂一樣打直，手和朝東同高 */  /* 第 13 版：柄拄地、單手握（使用者：「直立拿很怪」）：近側右手在胸前握柄，柄尾點在前腳前的地上，另一隻手垂著；grip＝手握在武器座標哪一點（長槍 −3、鐮 gripS −5.5），animOg＝6M 片段仍兩手握 */ // 第 7 版：手往前移、槍桿前傾，槍桿在鼻尖前方外側（審查：「槍桿壓在臉的前緣，把鼻子蓋掉」）
      atk: { from: { hand: [2, -14], a: 1.25 }, to: { hand: [6, -17.5], a: Math.PI / 2 + 0.03 }, og: [0, -6] },   // 雙手刺（第 7 版）：主手是後手、副手是前手（在主手前 6），兩手都在槍桿上、都在身體前方
      atkScythe: { from: { hand: [7, -15], a: 0.45 }, to: { hand: [5, -17], a: 2.0 }, og: [0, -6] } },               // 鐮：舉起（刃在頭的前上方）→ 往前下方收割（刃口朝自己），兩手在柄上
    bow: { zh: "持弓待機：弓在胸口前、靠中線，左手握弓把、右手扣弦上的箭尾，箭朝前下；背面弓和兩手被身體擋住",
      // 第 7 版：左手（副手）持弓、右手（主手）拉弦（右撇子弓手的常識；審查與專案 PM 同意）
      // 第 8 版：正面、背面也兩手拿（使用者：「弓正面反面也要雙手拿吧」）：左手在腹前握弓把，弓斜在身前、箭搭在弦上、箭頭朝左下；右手搭在弦上的箭尾
      // 第 9 版（美術 PM 定的持弓待機，四面同一個姿勢）：弓在角色左側、身體輪廓外面；左手握弓把在左腰外側、往前下方伸；弓直立、弓背朝前下，箭搭在弦上；
      //   右手橫過身前，手指扣在弦上的箭尾，也在左腰外側（使用者：「弓正面反面也要雙手拿吧」）。
      // 第 10 版（美術 PM 決定）：正面、背面採 Q 版慣例，弓轉成看得到弧線的方向，見 bowStill。grip＝弓把（左手）、tilt＝上弓梢往外傾、nt＝箭尾在弦中點上方多少、ah＝箭頭伸出弓把多少
      // 第 11 版：正面、背面同一個擺法（左右對調）：s＝弦的中點，在軀幹邊緣（x ±7）；上弓梢往外傾 tilt；右手扣在弦中段（中點上方 nt）；箭從箭尾經弓把往外下斜約 30°（tilt＋atan(nt／BOW_EY)）
      /* 第 13 版（使用者：「弓正面待機可以靠中間一點放在胸口前 不然手都被掰了」）：弓移到胸口前、靠中線，上弓梢往左肩外傾（tilt），弦朝右手；左手握弓把、右手扣弦，兩隻手臂都從自己的肩膀出來（取消 rsx 側轉）。背面是同一個姿勢從後面看：弓和兩手在身前被身體擋住 */
      front: { wh: "off", hand: [3, -11.5], s: [-1.1, -14.6], tilt: 0.72, nt: 1.9, ah: 4.2 },  /* 右肩再側一點（rsx），手臂長度不變，手在軀幹邊緣的弦上 */
      back: { wh: "off", hand: [-3, -11.5], s: [1.1, -14.6], tilt: 0.72, nt: 1.9, ah: 4.2 },  /* 右手臂在身體前方被擋住；照遠側手臂的規則，露出身體邊緣那段前臂（暗一階、從右肩方向進來，rcut 以左）和手 */
      side: { hand: [11.6, -12.6], a: Math.PI / 2 + 0.6, farX: 5.4 },  /* 第 14 版：弓往前 1.4、往下 1.6，弓背多往前下傾 0.28（上弓梢跟著往前），左肩再轉前 0.8：上弓梢離開下顎，抬一下（b2）也不碰臉（審查：「側面上弓梢蓋到下顎」） */  /* 第 13 版：弓收到胸口前（和正面同一個姿勢），箭往前下 */                // 側面：持弓手往前下方伸直，弓在身側前方（左肩轉到前面一點）；右手在身前扣著弦上的箭尾
      aim: { hand: [16.6, -21.5], a: Math.PI / 2, farX: 6.4, nearX: -1.5, edir: [-1, -0.3] } },                      // 拉弓（第 11 版）：持弓手往前伸到肩高（左肩轉到前面）、上弓梢在臉前方；右肩往後收（nearX），手肘往後、比肩略高（edir），拉弦手靠到下巴，箭在下巴高度、水平
    gun: { zh: "正面橫持在胸前、口朝右下；背面口從左腰外露出；側面持槍待命、口朝前上",
      front: { hand: [-3, -15], a: 1.87, og: [0, -6.8] },
      back: { hand: [3, -15], a: -1.87, og: [0, -6.8] },
      backX: { hand: [1, -15.5], a: 0, og: [0, -6.8], fore: [1.35, 0, 0.25, -0.3] },  /* 第 13 版：弩背面（使用者：「弩圖層穿插肩膀」）：弩在胸前朝前下方，從背後看弩身縮短、被身體擋住，只露出弩臂兩端；fore＝弩座標 → 畫面（弩臂沿 x、弩口朝畫面裡） */
      side: { hand: [6, -11], a: 0.9, og: [0, -5] },                                  // 第 8 版：托槍手往後一點，待機時弩口往下點也還搆得到（審查：「弩中段只看到一隻手」）
      atk: { from: { hand: [6, -11], a: 0.9 }, to: { hand: [11, -20], a: Math.PI / 2, farX: 6.5, elbow: "down" }, og: [0, -5] } },  // 第 8 版瞄準：槍托頂在肩窩（槍托尾在 x 4.5）、臉頰貼在槍托上緣，扳機手手肘朝下；托槍那側的肩膀轉到前面（側身持槍）
    staff: { zh: "單手握杖：手臂打直往外下方伸、杖身穿過拳頭；正面杖在畫面左、背面在畫面右；側面杖往前傾",
      front: { hand: [-OH[0], OH[1]], a: -ARM_TILT, grip: tiltG(-3.72 + (OH[1] - OH16[1]), 9), st: true },  /* 第 15 版審查：手抬高後杖跟著往上，杖尾懸空 38px；握點往下（grip），杖尾落在鞋底的地面線 */  /* 第 15 版：手臂打直往外下方伸（OUTA），杖直立在身體外側 */  /* 第 13 版：手臂自然垂直，拳頭接著袖口，四指從杖身前面繞過去（wrap） */
      back: { hand: [OH[0], OH[1]], a: ARM_TILT, grip: tiltG(-3.72 + (OH[1] - OH16[1]), 9), st: true },  /* 第 15 版：同正面（鏡像）：手臂打直往外下方伸，和身體之間有空隙；杖直立在身體外側，從拳頭上下穿出 */  /* 第 14 版：手垂在身側稍往內，杖和手臂同一條線（拳頭 → 肩膀）：從背後看，手臂蓋住拳頭以上的杖身，杖頭從肩膀外上方露出 */                                           // 第 7 版：背面杖在畫面右（右手在身側），手和杖都看得到（審查：「杖畫在背上、握杖的手卻被擋住」）
      side: { hand: SHD, a: 0.2, aW: 0.2, grip: tailG(9, 1.1, 0.2), gripW: tailG(9, 1.1, 0.2), /* 第 17 版 B 批審查：朝東斜度回到第 15 版（0.2） */ st: true },  /* 第 16 版：肩膀移到肩線，手臂打直往前下方；朝東杖的位置幾乎不變（手沿杖身往上滑），朝西杖尾仍在近側鞋子前面、光暈不碰頭 */  /* 第 15 版審查第二輪：杖多往前傾（0.2 → 0.36），杖頭的光暈離開帽簷和頭髮（審查：「r10 朝東光暈壓在帽簷」「i10 中段光暈壓到頭髮」）；朝西遠側的手往前（hw）、杖少傾一點（aW 0.2），杖尾在近側鞋子前面、不重疊，gripW＝朝西的握點（審查：「r08 朝西杖尾畫在近側鞋尖上」） */  /* 第 15 版審查：杖尾落在地面線（grip；出招片段只讀 mg，不受影響）；hw＝朝西右肩在遠側（x 3），手打直時和朝東同高 */  /* 第 15 版：手臂打直（原本差一點點伸直） */
      sideW: { hand: fk(SSH, -1.0, 0), a: 0.2, mg: tailG(9, 1.1, 0.2, fk(SSH, -1.0, 0)[1]), /* 第 17 版 B 批審查：0.24 → 0.2（第 15 版） */ needOff: true, st: true } },  /* 第 16 版：手臂從肩線打直往前下方（多往前一點，拳頭在書的前方），杖多傾一點，光暈不壓帽簷 */  /* 第 15 版：遠側右手臂打直往前下方伸，拳頭在書的前方（握點跟著往下，杖的位置大致不變） */                // 第 9 版：朝西拿書時，遠側右手握在杖的高一點（胸前），書在近側、蓋在杖上面，握杖的手露在書上方（審查：「杖壓在書上面、杖上沒有手」）                                          // 第 8 版：杖少往前傾一點，杖頭不伸進隔壁格（審查：「書那列朝東、朝西的杖頭互相重疊」）
  };
  function keyOf(gear) {
    const q = qWeapon(gear.main_hand); if (!q) return null;
    let c = CLASS_OF[q.kind]; if (!c) return null;
    if (c !== "staff" && gear.off_hand) return null; // 雙手武器副手有東西就改單手
    return { c, K: KEY[c], kind: q.kind };
  }
  const backKey = (key) => key && (key.kind === "crossbow" && key.K.backX ? key.K.backX : key.K.back);
  const ogLocal = (og) => (og ? [og[0], og[1] === "EY" ? BOW_EY : og[1]] : null);
  // 主手的關節：肩 sx、手掌目標 hand、手肘往哪邊
  const armTo = (sx, hand, out) => ik(sx, hand, out);
  /* 第 15 版（使用者：「這個背面握不行 手伸出來一點不要貼著 手也不要灣」）：持武器的手臂打直、不彎肘，從肩膀斜往外下方伸，手臂和身體之間看得到空隙。
     OUTA＝手臂往外張開的角度；k.st＝這個關鍵姿勢用打直的手臂：從肩膀朝 k.hand 的方向伸直（手實際的位置＝fk，手肘角 0） */
  const outOf = (gear) => (gear.main_hand && qWeapon(gear.main_hand) && qWeapon(gear.main_hand).kind !== "gauntlet" ? OUTA : SEAMF ? ARM.ea ?? 0 : 0); /* 第 17 版 B 批審查（美術 PM）：空手和拳套（部件頁）不用 E 的角度，改成「最小可見縫」ARM.ea：前臂下段、拳頭和大腿之間剛好露出 2～3px 背景色；A（第 16 版）照舊垂直 */ /* 單手握持（劍、刀、魔導劍、鞭、法球、成對匕首）；拳套沒有握把，手照舊垂著 */
  const armK = (sx, k, out) => (k.st ? { sA: Math.atan2(-(k.hand[0] - sx), k.hand[1] + 20), eA: 0, ok: true } : armTo(sx, k.hand, out));
  let EBOFF = false; /* 背面持盾的手臂自己畫深色外框（直的），不套 ARM.elbow */
  let BOWP = null; // 第 8 版：弓的弦位置（拉弦手實際的位置）與是否搭箭，由姿勢決定
  let TINT = null; // 自測用：把副手臂塗成指定色，算它露出多少
  let NOPAD = false; /* 第 16 版審查：側面遠側的肩甲被身體擋住，不畫（「看起來像前後兩個肩膀」） */
  let FAR = 0, FARH = 0; // 第 10 版：側面遠側手臂伸到身前時畫暗一階（審查：「r05 朝東胸前兩條袖子的描邊纏在一起」）
  let SEAM = false, NOBUCKLE = false, SEAMIN = false, SHEDGE = false, FILLARM = false, FREEARM = false; /* FREEARM：第 17 版 B 批補修，主手拿武器時空著的那隻手臂（布料類、正面或背面、非 key）也走 FILLARM 的合成一條＋內線＋拳頭圈 */ // 第 9 版：袖子描邊（側面、關鍵姿勢、背面持盾）；第 17 版 B 批：NOBUCKLE＝側面不畫帶扣、SEAMIN＝袖子內框
  const SEAMF = ARM !== ARM_SPREAD_SET.A; /* 第 17 版 B 批：不是 A（第 16 版）時，正面、背面的袖子也描內框 */
  let BOWM = null; // 第 9 版：斜看的弓（正面、背面）畫線時用的畫面座標
  let WEST = false; // 側面朝西（stamp 設定）：左右手互換
  // 弓手預設背箭袋（使用者看背面：「弓被擋住」；專案 PM：箭袋在背上）
  const backOf = (gear) => gear.back ?? (qWeapon(gear.main_hand)?.kind === "bow" ? { slot: "back", kind: "quiver", material: "leather" } : null);

  // ---------- 側面的兩隻手（第 7 版，11-04 深夜，獨立審查退回後重寫）----------
  // 朝東：近側＝主手（右），肩 x 4.5；遠側＝副手（左），肩 x 3。朝西相反（座標一律用朝東畫，stamp 再鏡像）。
  // 武器掛在「持武器的手」：一般是主手；弓是副手（左手持弓、右手拉弦，右撇子弓手的常識）。另一隻手去握第二握點，搆不到就放開。
  // 圖層：遠側的手在身體前方（x > 4.6）時畫在身體之後、頭之前，並裁掉肩膀那段；在身旁或身後就畫在身體之前（被擋）。
  //   武器 layer：head＝身體之後、頭之前（往後舉的劍身在頭後；弓的弦在臉後）；front＝頭之後；back＝身體之前（遠側單手、手在身旁）。
  const clamp01 = (t) => Math.max(0, Math.min(1, t));
  function sidePlan(unit, key, anim, W) {
    const { gear } = unit, bowK = !!key && key.c === "bow", SX = typeof POSE?.atk === "number" ? { main: W ? 3 : 4.5, off: W ? 4.5 : 3 } : bowK ? { main: SSH, off: W ? 4.5 : 3 } : { main: SSH, off: SSH }, nearWho = W ? "off" : "main"; /* 第 16 版：兩邊肩膀都在軀幹肩線上（SSH）；弓的持弓肩（左）照舊轉到前面（側身持弓，farX 另外調），拉弦的右肩也回到肩線；雙手出招（atk：蓄力、舉起、劈、刺、瞄準）是揮動中的姿勢，肩膀跟著轉到前面，照第 15 版 */
    let P, bowT = 0;
    if (key && !anim) {
      const ks = W && key.K.sideW && !(key.K.sideW.needOff && !gear.off_hand) ? key.K.sideW : key.K.side, bow = key.c === "bow"; /* 第 9 版：朝西另外手調（sideW） */
      let hand = W && ks.hw ? ks.hw : ks.hand, a = W && ks.aW != null ? ks.aW : ks.a, og = ks.og ?? null, mg = ks.mg ?? (key.kind === "scythe" && ks.gripS != null ? ks.gripS : W && ks.gripW != null ? ks.gripW : ks.grip) ?? 0, short = !!ks.short, layer = ks.layer ?? null, elbow = -1, olen = ks.olen ?? null;
      if (ks.farX && !W) SX.off = ks.farX; /* 第 9 版：遠側左肩轉到前面一點（持弓手伸到前下方） */
      const AK = (key.kind === "scythe" && key.K.atkScythe) || key.K.atk;
      if (AK && typeof POSE?.atk === "number") {
        const fr = AK.from; /* 第 17 版：蓄力朝東、朝西同一組（從拄劍提起） */
        const t = clamp01(POSE.atk), [P0, P1, tt] = AK.mid ? (t < 0.5 ? [fr, AK.mid, t * 2] : [AK.mid, AK.to, t * 2 - 1]) : [fr, AK.to, t];
        const L = (p, q) => p + (q - p) * tt;
        hand = [L(P0.hand[0], P1.hand[0]), L(P0.hand[1], P1.hand[1])]; a = L(P0.a, P1.a); og = AK.og; mg = AK.mg ?? 0; short = false; elbow = tt > 0.5 ? P1.elbow ?? -1 : P0.elbow ?? -1;
        if (P0.farX || P1.farX) SX.off = L(P0.farX ?? SX.off, P1.farX ?? SX.off); // 側身：托槍那側（左）的肩膀轉到前面
        if (P0.og) og = tt < 0.5 ? P0.og : AK.og; /* 第 9 版：蓄力的副手握點跟著姿勢 */
        olen = tt < 0.5 ? P0.olen ?? null : null;
        layer = tt < 0.5 && P0.layer ? P0.layer : Math.sin(a) < -0.3 ? "head" : null; /* 劍身往後上方時畫在頭上面、貼著後頸 */
      }
      if (bow) {
        const t = clamp01(pz("bowAim")), A2 = key.K.aim;
        const th = t <= 0.4 ? t : Math.min(1, 0.4 + (t - 0.4) * 1.5); /* 第 12 版：持弓手臂先伸直（2/3 起和拉滿同位置），再拉弦；1/3（t 0.4）與拉滿不變（審查：「拉弓 2/3 上弓梢貼著鼻尖」） */
        if (t) { hand = [hand[0] + (A2.hand[0] - hand[0]) * th, hand[1] + (A2.hand[1] - hand[1]) * th]; a += (A2.a - a) * th; if (A2.farX) SX.off += (A2.farX - SX.off) * th; if (A2.nearX != null) SX.main += (A2.nearX - SX.main) * t; } /* 第 11 版：拉弓時右肩往後收（身體側轉），拉弦手的手肘才能往後抬到肩高 */
        og = "string"; layer = W ? "head" : "mid"; bowT = t; // 第 9 版：朝東弓在遠側左手、右手壓在弦上（右手臂畫在弓上面）；朝西弓在最前面
      }
      const wh = bow ? "off" : "main", hlen = ks.hlen && !pz("bowAim") ? ks.hlen : null, k = ks.st && typeof POSE?.atk !== "number" ? { sA: Math.atan2(-(hand[0] - SX[wh]), hand[1] + 20), eA: 0 } : ik(SX[wh], hand, elbow, hlen); /* 第 15 版：st＝手臂打直 */ // elbow：手肘往後（−1）、往前上（+1）或往下（"down"，瞄準）
      P = { wh, sA: k.sA + pz("arm"), eA: k.eA, a: a + pz("arm") + pz("dw"), og, mg, short, layer, split: true, farX: ks.farX, olen, hlen };
    } else {
      // 6M／6N 片段或沒有關鍵姿勢的武器：主手臂角度 arm、武器角度 arm＋wpn；雙手武器出招時副手去握 og
      // 第 8 版：朝西時空手的遠側右手和朝東一樣垂在身後、露一點（審查：「朝東露一點，朝西完全看不到」）
      const empty = W && (!gear.main_hand || (qWeapon(gear.main_hand)?.kind === "gauntlet" && !anim)); /* 第 9 版：拳套站姿朝西，遠側右手也垂在身後露一點（審查：「s06_04 朝西看不到遠側的手」） */
      if (empty) SX.main = -4.5;
      const sA = empty ? pz("armR") * 0.6 - 0.1 : pz("arm"), eA = empty ? 0.15 : Math.min(0, sA * 0.35), w = anim ? POSE.wpn : holdOf(gear.main_hand, "side");
      const kc2 = key && key.c !== "bow" && key.c !== "staff" ? key.K.side.animOg ?? key.K.side.og : null;
      P = { wh: "main", sA, eA, a: sA + w, og: kc2 && anim ? kc2 : null, mg: key?.K.side.mg ?? 0, short: false, layer: null, split: false };
    }
    P.h = fk(SX[P.wh], P.sA, P.eA, P.hlen);
    const who2 = P.wh === "main" ? "off" : "main";
    const A = { [P.wh]: { who: P.wh, sx: SX[P.wh], sA: P.sA, eA: P.eA, len: P.hlen } };
    P.ol = null; P.pull = null;
    const released = P.og === "string" && pz("bowAim") > 0.9 && !(pz("pull") > 0.5); // 放箭那一格
    if (released) P.og = null;
    P.released = released;
    if (P.og) {
      const ol = P.og === "string" ? [0, BOW_EY + (pz("pull") || 0)] : P.og, o = rot(P.a, [ol[0], ol[1] - P.mg]), t = [P.h[0] + o[0], P.h[1] + o[1]];
      if (P.og === "string" && bowT >= 0.6) {
        // 第 8 版拉弓：拉弦手的手肘往後抬到肩高，前臂往前到下巴下；弦拉到手實際的位置（審查：「袖子直接蓋住下巴和嘴」）
        const k = elbowTo(SX[who2], key.K.aim.edir, t), ax = rot(P.a, [0, 1]); /* 第 11 版：手肘往後、比肩高一點，拉弦手靠到下巴（審查：「拉滿是退步」） */
        A[who2] = { who: who2, sx: SX[who2], sA: k.sA, eA: k.eA };
        P.pull = Math.max(0, (k.h[0] - P.h[0]) * ax[0] + (k.h[1] - P.h[1]) * ax[1] - BOW_EY); P.ol = [0, BOW_EY + P.pull];
        if (POSE && POSE.hands) POSE.hands.offTwo = true;
      } else {
        const k = ik(SX[who2], t, -1, P.olen);
        if (k.ok) { A[who2] = { who: who2, sx: SX[who2], sA: k.sA, eA: k.eA, len: P.olen }; P.ol = ol; if (POSE && POSE.hands) POSE.hands.offTwo = true; }
      }
    }
    if (!A[who2] && released) {
      // 放箭：弦彈回弓上，拉弦手留在下巴下（不跟著弦往前），手肘往後
      const k = elbowTo(SX[who2], key.K.aim.edir, P.h); A[who2] = { who: who2, sx: SX[who2], sA: k.sA, eA: k.eA };
    }
    if (!A[who2]) {
      // 空出來的副手：成對武器拿第二把匕首；盾（第 8 版：持盾的手在盾後面，只畫這一隻，不另外垂一隻；使用者：「往右舉著盾牌 左邊還是有手」）；拿書或垂著
      const paired = qWeapon(gear.main_hand)?.kind === "paired";
      if (paired) {
        // 第 8 版：第二把匕首在左手，舉在胸前、刃朝前上；右手那把在腰側（兩隻手分開，審查：「兩隻手貼在一起」）
        const att = anim && POSE.wpn !== undefined && !POSE.idle, k = ik(SX.off, att ? [10.2, -18.4] : [10.8, -19], -1); /* 第 10 版：遠側手往前上伸，前臂露在近側手臂前面，看得出手連著自己的袖子（審查：「上面那隻手長在近側手臂的手肘處」） */
        const sA = k.sA, eA = k.eA, da = att ? 0.55 : 0.75;
        A.off = { who: "off", sx: SX.off, sA, eA, item: (hand) => offDagger(ctx0(), gear.main_hand, hand, da - sA - eA) };
      } else if (isShield(gear.off_hand)) {
        const k = ik(SX.off, [8.6, -13.5 - pz("shieldUp")], -1); /* 第 17 版 B 批第 3 項：手在盾的中央（盾心 x 8.6） */
        A.off = { who: "off", sx: SX.off, sA: k.sA, eA: k.eA, item: null, shield: true };
      } else if (W && offHeld(gear)) A.off = { who: "off", sx: SX.off, sA: 0.12, eA: 0.05, item: (hand) => mainWeapon(ctx0(), offHeld(gear), hand, holdOf(offHeld(gear), "side"), "side") }; /* 畫圖 agent 11-07：副手手持物（近側） */
      else if (offHeld(gear)) A.off = { who: "off", sx: -4.5, sA: pz("armL") * 0.6 - 0.1, eA: 0.15, item: (hand) => mainWeapon(ctx0(), offHeld(gear), hand, holdOf(offHeld(gear), "side"), "side") }; /* 遠側（朝東）：在身體後面，只露出身體外的部分 */
      else if (W) A.off = { who: "off", sx: SX.off, sA: gear.off_hand ? -0.15 : 0.12, eA: gear.off_hand ? 0.1 : 0.05, item: /* 第 8 版：朝西空著的近側左手自然垂在身側，不和遠側握杖的手疊成一團 */ gear.off_hand ? (hand) => PD.drawWeapon(ctx0(), gear.off_hand, hand[0] + 1, true) : null };
      else if (gear.off_hand) A.off = { who: "off", sx: SSH, sA: 0, eA: 0, item: (hand) => PD.drawWeapon(ctx0(), gear.off_hand, hand[0] - (gear.body?.kind === "robe" ? 0 : 1.5), true) }; /* 第 16 版審查第二輪：不穿長袍時書心往後 1.5，整本書在軀幹前後緣（±5.4）之內，不從前緣露出書邊（s11_05 襯衫比長袍窄；長袍已經擋住，不動）。第 16 版審查：朝東遠側左手拿書垂在身側（肩線），書和腰重疊、被身體擋住，不跑到背後（「書從背後腰邊露出一角」） */
      else A.off = { who: "off", sx: -4.5, sA: pz("armL") * 0.6 - 0.1, eA: 0.15, item: gear.off_hand ? (hand) => PD.drawWeapon(ctx0(), gear.off_hand, hand[0], true) : null };
    }
    const farWho = nearWho === "main" ? "off" : "main";
    P.near = A[nearWho]; P.far = A[farWho];
    P.far.front = fk(P.far.sx, P.far.sA, P.far.eA, P.far.len)[0] > 4.6 && P.far.sx > 0;
    P.bowHand = !!key && key.c === "bow" && !anim; /* 第 11 版：弓的拉弦手畫在弦和箭桿上面（朝西是遠側手，另外補畫一次手） */
    P.nearLate = P.bowHand && !W && bowT >= 0.6; /* 第 11 版：拉滿、放箭時拉弦手靠在下巴，手臂畫在頭上面 */
    if (!P.layer) P.layer = P.wh === farWho && !P.far.front ? "back" : "front";
    return P;
  }
  let CTX = null; const ctx0 = () => CTX; // 畫手上的東西時用的畫布（arm 的 inHand 回呼在手的座標系裡）
  // 第 9 版：正面、背面的弓。弓座標 (x, y) → 畫面 x·U − y·F（弓臂沿 U、弓背朝 F）；線寬照畫面算（BOWM）。off＝右手扣弦的點（弓座標，自測用）
  function bowFace(ctx, it, hand, U, F, view, off = null) {
    ctx.save(); ctx.translate(hand[0], hand[1]); BOWM = ctx.getTransform();
    ctx.transform(U[0], U[1], -F[0], -F[1], 0, 0);
    QW.bow.draw(ctx, it);
    if (POSE && POSE.probe) { const m = ctx.getTransform(); POSE.probe("bow", m.transformPoint(new DOMPoint(0, 0)), m.transformPoint(new DOMPoint(0, -QW.bow.len)), view, m.transformPoint(new DOMPoint(off ? off[0] : 0, off ? off[1] : BOW_EY)), m, QW.bow); }
    BOWM = null; ctx.restore();
  }
  // （第 13 版已取代下面第 10～11 版的正背面 Q 版慣例，見 bowStill 內的說明）
  // 第 10 版（美術 PM 決定：正面、背面採 Q 版慣例，刻意風格化，不算四面不一致）：
  //   弓在角色左側（正面在畫面右、背面在畫面左）、弓直立，弦朝身體、弓背朝外；左手在弓把，右手在身體邊緣扣住弦上的箭尾；
  //   箭從箭尾沿著弦往外下斜、箭頭朝外下。手畫在弦和箭桿的上面；弓把畫在左手上面。
  //   正面：右肩側轉（身體側轉，手臂長度不變），右手臂橫過胸前、手在軀幹邊緣的弦上。
  //   背面（第 11 版）：右手臂在身體前方；照遠側手臂的規則，露出身體邊緣那段暗一階、描邊的前臂（從右肩方向進來）和手；左手肘往外，前臂往下到弓把。
  function bowStill(ctx, unit, view, pre = false) {
    /* 第 13 版（使用者：「弓正面待機可以靠中間一點放在胸口前 不然手都被掰了」）：弓在胸口前、靠中線；左手握弓把、右手扣弦上的箭尾，兩隻手臂都從自己的肩膀出來。
       背面是同一個姿勢從後面看：弓、箭、兩隻手都在身體前方，整組在身體之前畫（pre），被身體擋住；肩膀、上臂在弓上面。正面在頭之後畫。 */
    const k = KEY.bow[view], B = view === "back", o = B ? -1 : 1, ls = 8.5 * o, ph = k.tilt ?? 0;
    if (B !== pre) return;
    const U = [-o * Math.sin(ph), Math.cos(ph)], F = [o * Math.cos(ph), Math.sin(ph)]; /* U：弓臂往下（上弓梢往左肩外傾 ph）；F：弓背朝外下 */
    const S = k.s, G = [S[0] + BOW_EY * F[0], S[1] + BOW_EY * F[1]], N = [S[0] - k.nt * U[0], S[1] - k.nt * U[1]]; /* 弦的中點 S；弓把 G（左手）、箭尾 N（右手扣的點） */
    const kl = ik(ls, G, o), kr = ik(-ls, N, "down"), it = unit.gear.main_hand;
    const leftArm = () => arm(ctx, unit, ls, kl.sA, kl.eA, 0, rec("off")), rightArm = () => arm(ctx, unit, -ls, kr.sA, kr.eA, 0, rec("main"));
    const bowArrow = () => {
      BOWP = { nock: false, noArrow: true }; bowFace(ctx, it, G, U, F, view, [-k.nt, BOW_EY]); BOWP = null; if (POSE && POSE.layers) POSE.layers.push("weapon");
      const dx = G[0] - N[0], dy = G[1] - N[1], dl = Math.hypot(dx, dy), ux = dx / dl, uy = dy / dl, T = [G[0] + ux * k.ah, G[1] + uy * k.ah]; /* 箭：箭尾 N 經過弓把到箭頭 T */
      ctx.strokeStyle = "#c8a070"; ctx.lineWidth = 0.9; ctx.lineCap = "round"; ctx.beginPath(); ctx.moveTo(N[0] - ux, N[1] - uy); ctx.lineTo(T[0], T[1]); ctx.stroke();
      fill(ctx, "#c3ccd6", () => { ctx.moveTo(T[0] + ux * 2.4, T[1] + uy * 2.4); ctx.lineTo(T[0] - uy * 1.2, T[1] + ux * 1.2); ctx.lineTo(T[0] + uy * 1.2, T[1] - ux * 1.2); ctx.closePath(); });
    };
    if (B) {
      /* 第 14 版：背面的弓、箭只畫在身體輪廓裡（全部被身體擋住），手臂只畫肩膀那段（y < −16.5）和身體輪廓裡的部分：
         原本弓臂從腰帶右下露出一小條、箭頭從左腿外露出、前臂的描邊從身體左緣露出一條，外框也跟著描出來（審查：「看不到的東西，外框也不能留下來」） */
      const body = () => { ctx.beginPath(); ctx.rect(-7.4, -21, 14.8, 13.4); };
      ctx.save(); body(); ctx.clip(); bowArrow(); ctx.restore();
      ctx.save(); body(); ctx.rect(-40, -60, 80, 43.5); ctx.clip(); leftArm(); rightArm(); ctx.restore();
      return;
    }
    leftArm(); bowArrow(); rightArm(); /* 正面：弓把蓋在左手上；右手在弦和箭桿上面 */
  }
  // 第 13 版：握住直的柄（法杖、拄地的長柄）：柄畫在手掌上面之後，再畫一條橫過柄的四指（和手同色、稍暗），柄從拳頭上下穿出去
  //   （使用者：「背面側面拿法仗 右手握還是沒修好」；修正清單：「杖身從手掌上方或前方滑過，不是被拳頭握住」）
  function wrap(ctx, unit, hand, a, dk = 0) { /* 第 14 版：dk＝再加深多少（側面伸到身前的遠側手，和 arm() 的 FARH 一樣暗一階） */
    const { look, gear } = unit, hc = gear.hands && gear.hands.kind !== "bracers" ? colors(gear.hands)[0] : look.skin;
    ctx.save(); ctx.translate(hand[0], hand[1]); ctx.rotate(a);
    fill(ctx, mix(hc, "#000000", 0.05 + dk), () => rr(ctx, -2.35, -1.25, 4.7, 2.5, 1.1));
    ctx.strokeStyle = mix(hc, "#000000", 0.4); ctx.lineWidth = 0.35; ctx.beginPath(); ctx.moveTo(-1.9, 0); ctx.lineTo(1.9, 0); ctx.stroke();
    ctx.restore();
  }
  // 副手的匕首：在手的座標系裡畫，角度相對手臂
  function offDagger(ctx, it, hand, a) { ctx.save(); ctx.translate(hand[0], hand[1]); ctx.rotate(a); dagger(ctx, it); ctx.restore(); }
  // ---------- 整隻：view = front | side | back ----------
  // 畫的順序（由後到前；部件的圖層見 docs/art/部件四方向清單.md）
  //   正面：披風（暗）→ 背掛（露在肩上的部分）→ 尾巴 → 腿 → 身體 → 紋章、頸飾、背帶、腰掛 → 披風扣 → 副手臂＋副手 → 頭 → 武器 → 副手臂 → 主手臂
  //   側面：披風（背後那片）→ 背掛 → 尾巴 → 遠側手臂（朝東：副手；朝西：主手＋單手武器）→ 遠側腰掛 → 腿 → 身體 → 紋章、頸飾、背帶、近側腰掛 → 盾（朝東）→ 頭 → 武器 → 近側手臂（朝東：主手；朝西：副手＋盾、書）
  //   背面：武器與兩隻手臂（在身體前方＝畫面後）→ 副手物品 → 腿 → 身體 → 腰掛 → 披風 → 背掛 → 尾巴 → 頭
  function draw(ctx, unit, view) {
    const { look, gear } = unit, F = view === "front", B = view === "back", S = view === "side";
    CTX = ctx;
    const side = S ? 1 : 0, W = S && WEST;
    const R = window.RaceArt;
    const mark = (n) => { if (POSE && POSE.layers) POSE.layers.push(n); };
    const key = keyOf(gear), anim = POSE && typeof POSE.wpn === "number";
    const bk = backOf(gear);
    const BARE = gear.body?.kind === "bare"; BARESKIN = BARE ? look.skin : null; EDGEK = BARE ? 0.23 : null; /* 畫圖 agent 11-07：赤膊照布料內線規則（第 17 版），線色＝膚色加深 0.23 */
    FILLARM = !S && !key && SEAMF && !(gear.main_hand && qWeapon(gear.main_hand) && qWeapon(gear.main_hand).kind !== "gauntlet");
    SHEDGE = F && SEAMF && ["plate", "mail"].includes(gear.body?.kind);
    SEAMIN = !S && !key && !(B && isShield(gear.off_hand)) && SEAMF && ["plate", "mail"].includes(gear.body?.kind); /* 第 17 版 B 批審查：內框只留在盔甲類（布料類拿掉） */ SEAM = S || !!key || (B && isShield(gear.off_hand)) || SEAMIN; /* 第 17 版 B 批：手臂靠近身體（E），正面、背面的袖子也描邊，和同色的胸甲分得開 */ // 第 9 版：手臂畫在同色身體上面時描邊，看得出手臂連到手
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
      const kb = backKey(key);
      if (kb && kb.og) {
        // 第 8 版：持武器的手（弓是左手）先定位置，另一隻手去握第二握點；手臂先畫、武器畫在手上面（都在身體前方，被身體擋住）
        const who = kb.wh ?? "main", sx = who === "main" ? 8.5 : -8.5, k0 = armTo(sx, kb.hand, sx > 0 ? 1 : -1), h = fk(sx, k0.sA, k0.eA), ol = ogLocal(kb.og);
        const M = kb.fore ?? null, o = M ? [M[0] * ol[0] + M[2] * ol[1], M[1] * ol[0] + M[3] * ol[1]] : rot(kb.a, ol), io = ik(-sx, [h[0] + o[0], h[1] + o[1]], sx > 0 ? -1 : 1);
        /* 第 13 版：武器在身體前方、比手臂離鏡頭更遠：先畫武器，再畫兩隻手臂，肩膀和上臂蓋在武器上面（審查：「弩穿插在肩膀圖層之間」） */
        BOWP = { nock: true }; mainWeapon(ctx, gear.main_hand, h, kb.a, "back", kb.short || false, ol, 0, M); BOWP = null; mark("weapon");
        arm(ctx, unit, -sx, io.sA, io.eA, 0, rec(who === "main" ? "off" : "main"));
        arm(ctx, unit, sx, k0.sA, k0.eA, 0, rec(who));
      } else {
        // 第 9 版：背面單手武器整把先畫在身體後面（和身體、肩膀重疊的部分被擋住，只露出身體輪廓外面的刃）；手垂在身側之後再畫，拳頭上只補畫握柄
        //   （審查：「劍盾背面右手的劍刃畫在肩甲、袖子上面，看起來像劍在背後」）
        if (key && key.c === "bow") bowStill(ctx, unit, "back", true);
        if (key && (key.c === "staff" || key.c === "polearm")) {
          /* 第 15 版：握杖的手臂打直往外下方伸（KEY 的 st），杖直立在身體外側：杖和手臂只在拳頭、前臂那一小段重疊（手臂蓋在杖上），杖頭和杖尾從拳頭上下穿出。下面是第 14 版的說明 */
          /* 第 14 版：背面握杖、拄地長柄：杖稍微在身體前面、比手臂離鏡頭遠。杖在身體之前畫（被身體、長袍擋住的那段不出現），握杖的手臂在身體之後畫、蓋在杖上：
             上臂和袖子蓋住拳頭以上的杖身，拳頭蓋住握的那段（從背後看到的是手背），只露出肩膀外的杖頭和身體（長袍下擺）以下的杖尾
             （審查：「正面和背面都是杖身蓋在袖子上」；美術 PM：「r10 背面要照杖在身體前面畫，不要讓杖尾壓在下擺上面」） */
          const k0 = stK(SHX, kb, 1, gear), h = fk(SHX, k0.sA, k0.eA), mgB = stMg(SHX, kb, k0, (key.kind === "scythe" && kb.gripS != null ? kb.gripS : kb.grip) ?? 0, gear);
          mainWeapon(ctx, gear.main_hand, ARM.po ? [h[0] + ARM.po, h[1]] : h, kb.a, "back", false, null, mgB); mark("weapon");
        }
        if (gear.main_hand && !(key && (key.c === "staff" || key.c === "bow" || key.c === "polearm"))) { ctx.save(); ctx.translate(0, pz("armR")); mainWeapon(ctx, gear.main_hand, swOff(fk(sxOf(gear), -holdA(gear), 0), 1, gear), -holdOf(gear.main_hand, "front") + ARM.swa, "back"); ctx.restore(); mark("weapon"); }
        // 單手武器（劍、刀、匕首、鎚……）：正面拿在身側，背面也在身側（畫面右），身體之後畫、手和武器都看得到，見下面
      }
      mark("arms");
      if (isShield(gear.off_hand)) {
        { const sh = fk(-SHX, OUTA, 0), oh = gear.off_hand; if (SHIELD_CENTER) shieldBack(ctx, oh, sh[0] + 1, sh[1] + (oh.kind === "shield_round" ? 11.8 : oh.form === "tower" ? 11.5 : 11)); else shieldBack(ctx, oh, sh[0] - 2.7, sh[1] + 9.63); } mark("shield"); /* 第 16 版：盾跟著打直往外的左手（盾心在拳頭外側一點），不貼背 */ // 第 9 版：盾在身體後面；持盾的手臂在身體之後畫（見 shieldArmBack）
      }
    }
    // ---- 側面（第 7 版）：兩隻手的位置、武器在哪隻手、各畫在哪一層（sidePlan）----
    const SP = S ? sidePlan(unit, key, anim, W) : null;
    const sideArm = (A, clip) => {
      ctx.save();
      if (clip) { ctx.beginPath(); if (clip === "hand") { const hh = fk(A.sx, A.sA, A.eA, A.len ?? null); ctx.arc(hh[0], hh[1], 2.6, 0, TAU); } else ctx.rect(3.2, -80, 80, 120); ctx.clip(); } // 遠側手伸到身體前方：只露出胸前那段前臂與手（"hand"：只補畫手）
      if (clip) { FAR = 0.12; FARH = 0; } /* 第 16 版：遠側只把袖子的明度降一點（同一種材質），手不加深 */
      NOPAD = A === SP.far;
      arm(ctx, unit, A.sx, A.sA, A.eA, side, A.item ? (hand, c) => { A.item(hand, c); const r = rec(A.who); if (r) r(hand, c); } : rec(A.who), false, A.len ?? null);
      FAR = 0; FARH = 0; NOPAD = false;
      ctx.restore();
    };
    const sideWeapon = () => { if (key && key.c === "bow") BOWP = { pull: SP.pull, nock: !SP.released };
      mainWeapon(ctx, gear.main_hand, SP.h, SP.a, "side", SP.short, SP.ol, SP.mg); BOWP = null; mark("weapon");
      if (key && !anim && typeof POSE?.atk !== "number" && (key.c === "staff" || key.c === "polearm" || key.c.startsWith("greatsword"))) {
        /* 第 14 版：雙手劍（拄劍）的握柄也照握杖：四指橫過劍柄，劍柄從拳頭上下穿出（審查：「劍柄畫在拳頭上面，看起來沒被握住」）。伸到身前的遠側手暗一階 */
        /* 遠側手：四指只畫在拳頭輪廓裡（不凸出拳頭）；近側手臂已經畫過時，在拳頭那一圈再補畫一次近側手臂，回到「近側袖子壓在遠側拳頭上」（審查：「r02 朝西遠側四指蓋到近側袖子」） */
        const one = (pos, who) => {
          if (!(SP.far.who === who && SP.far.front)) { wrap(ctx, unit, pos, SP.a); return; }
          ctx.save(); ctx.beginPath(); ctx.arc(pos[0], pos[1], 2.4, 0, TAU); ctx.clip(); wrap(ctx, unit, pos, SP.a); ctx.restore();
          if (SP.nearDone && SP.near.who !== SP.wh && !SP.ol) { const N = SP.near; /* 只在近側手空著（沒握柄）時補畫：近側手也握著柄時（拄劍），補畫會蓋掉近側拳頭的握柄和四指（審查：「r01 東、i15 近側拳頭變成淺色圓頂」） */ ctx.save(); ctx.beginPath(); ctx.arc(pos[0], pos[1], 2.9, 0, TAU); ctx.clip(); arm(ctx, unit, N.sx, N.sA, N.eA, side, null, false, N.len ?? null); ctx.restore(); }
        };
        one(SP.h, SP.wh);
        if (SP.ol && key.c.startsWith("greatsword")) { const o = rot(SP.a, [SP.ol[0], SP.ol[1] - SP.mg]); one([SP.h[0] + o[0], SP.h[1] + o[1]], SP.wh === "main" ? "off" : "main"); }
      } }; /* 第 13 版：單手握杖、拄地長柄：四指繞過柄，柄穿過拳頭 */
    if (S) {
      if (!SP.far.front) sideArm(SP.far, false);
      if (SP.layer === "back") sideWeapon();
    }
    if (S) waistItem(ctx, gear.waist, "side", "behind");
    leg(ctx, look, gear.feet, -1, pz("hipF"), pz("kneeF"), pz("liftL"), side);
    leg(ctx, look, gear.feet, 1, pz("hipN"), pz("kneeN"), pz("liftR"), side);
    if (S && gear.main_hand) NOBUCKLE = (qWeapon(gear.main_hand)?.kind === "gauntlet" && !anim) || [SP.near, SP.far].some((N) => { const nh = fk(N.sx, N.sA, N.eA, N.len ?? null); return nh[0] > 1.5 && nh[0] < 9.5 && nh[1] > -13 && nh[1] < -4.5; }); /* 第 17 版 B 批：拿著武器（含拳套）時，任一隻手在腰前（帶扣旁邊）就不畫帶扣；空手照舊露一點帶扣（部件第 5 節要看得到） */
    body(ctx, gear.body, look, side, B); mark("body"); NOBUCKLE = false;
    crest(ctx, gear.body, F ? "front" : B ? "back" : "side");
    neckItem(ctx, gear.neck, F ? "front" : B ? "back" : "side");
    waistItem(ctx, gear.waist, F ? "front" : B ? "back" : "side", "over");
    if (!B) backItem(ctx, bk, F ? "front" : "side", "over");
    if (B) {
      // 背面垂在身側、看得到的手：法杖在畫面右（右手）、弓在畫面左（左手）、空手
      const kb = backKey(key), paired = qWeapon(gear.main_hand)?.kind === "paired";
      if (key && key.c === "bow") bowStill(ctx, unit, "back"); // 第 9 版：四面同一個持弓待機
      else if (key && (key.c === "staff" || key.c === "polearm")) {
        /* 第 14 版：杖（長柄）已在身體之前畫；這裡只畫握杖的手臂，蓋在杖上（見身體之前那段） */
        const k0 = stK(SHX, kb, 1, gear);
        arm(ctx, unit, SHX, k0.sA, k0.eA, 0, rec("main"));
      } else if (!(kb && kb.og)) {
        // 空手或單手武器：右手垂在身側（畫面右），單手武器握在手裡、刃往外斜（正面的鏡像位置；審查：「背面垂在身側的手都消失了」）
        const rm = rec("main");
        ctx.save(); ctx.translate(0, pz("armR"));
        const guard = ["sword", "arcane_blade", "saber"].includes(qWeapon(gear.main_hand)?.kind); /* 第 11 版：劍的十字護手整條畫出來，以劍身為中心左右等長（審查：「背面護手左 14px、右 48px」） */
        const oB = holdA(gear); /* 第 15 版：持武器的右手臂打直往外下方伸（肩角 −OUTA），武器的世界角度不變（手的座標系裡補回 OUTA） */
        arm(ctx, unit, sxOf(gear), -oB, 0, 0, gear.main_hand ? (hand, c) => { c.save(); c.beginPath(); c.arc(hand[0], hand[1], 2.6, 0, TAU); if (guard) { c.save(); c.translate(hand[0], hand[1]); c.translate(swOn(gear) ? ARM.sw : 0, 0); c.rotate(-holdOf(gear.main_hand, "front") + oB + ARM.swa); c.rect(-4.8, -4.6, 9.6, 3.2); c.restore(); } c.clip(); mainWeapon(ctx, gear.main_hand, swOff(hand, 1, gear), -holdOf(gear.main_hand, "front") + oB + ARM.swa, "back"); c.restore(); if (rm) rm(hand, c); } : rm); // 握柄從拳頭上穿過
        ctx.restore();
      }
      // 左手：空手垂在身側；成對武器的第二把在左手（畫面左），刃往外斜
      const OHB = offHeld(gear);
      if (gear.off_hand && !isShield(gear.off_hand) && !OHB) {
        /* 第 16 版（美術 PM：背面的手也要伸出來、不貼身，四面一致）：拿書的左手和正面一樣從肩膀打直往外下方（BOOKA），在身體外側拿著書；
           從背後看到書的封底（素面，靠身體那側一條深色書背），書蓋住手的大半，只在書的下緣露出一點拳頭邊緣（使用者早期：「拳頭應該看不到或者露一點邊緣而已」） */
        ctx.save(); ctx.translate(0, pz("armL")); TINT = POSE && POSE.tintOff ? POSE.tintOff : null;
        arm(ctx, unit, -SHX, BOOKA + robeX(gear), 0, 0, rec("off"));
        TINT = null;
        const bh = fk(-SHX, BOOKA + robeX(gear), 0), [bc, bd] = colors(gear.off_hand);
        if (SEAMF) { const rb = gear.body?.kind === "robe", hem = gear.body?.form === "short" ? -6 : -1.5; ctx.beginPath(); ctx.rect(-80, -120, 160, 200); if (rb) { ctx.moveTo(-7, -21); ctx.lineTo(7, -21); ctx.lineTo(10, hem); ctx.lineTo(-10, hem); ctx.closePath(); } else ctx.rect(-7.5, -21, 15, 13.5); ctx.clip("evenodd"); } /* 第 17 版 B 批審查：背面的書在身體前方，被長袍（軀幹）擋住一部分；正面書在長袍前面 */
        ctx.translate(bh[0] - (ARM.bk ?? 2), bh[1] + 0.1); /* 審查：書往外 2，手臂、書和長袍之間看得到空隙 */
        fill(ctx, bc, () => rr(ctx, -4.5, -6, 9, 8, 1)); fill(ctx, bd, () => rr(ctx, 2.9, -6, 1.6, 8, 0.6));
        ctx.restore(); mark("shield");
      }
      if ((!gear.off_hand || OHB) && !(kb && kb.og) && key?.c !== "bow") { FREEARM = !key && !paired && !SEAMIN && !OHB; arm(ctx, unit, -sxOf(gear), OHB ? OUTA : outOf(gear), 0, 0, /* 第 16 版：空著的左手也打直往外下方（成對匕首原本就張開） */ OHB ? (hand, c) => { mainWeapon(ctx, OHB, hand, holdOf(OHB, "front") - OUTA, "back"); const r = rec("off"); if (r) r(hand, c); } : paired ? (hand, c) => { offDagger(ctx, gear.main_hand, hand, holdOf(gear.main_hand, "front") - OUTA); const r = rec("off"); if (r) r(hand, c); } : rec("off")); FREEARM = false; } /* 第 17 版 B 批補修：背面空著的左手逐隻判斷（FREEARM） */
    }
    if (B && isShield(gear.off_hand)) shieldArmBack(ctx, unit);
    if (S) { cloakClasp(ctx, gear.cloak, true); if (!W && isShield(gear.off_hand)) { if (SP.far.shield) sideArm(SP.far, true); shieldSide(ctx, gear.off_hand); } } // 第 8 版：持盾的遠側手在盾後面
    if (B) {
      if (gear.cloak) { cloakBack(ctx, gear.cloak); mark("cloak"); }
      backItem(ctx, bk, "back", "over");
      if (R) R.tail(ctx, look, "back", 0);
      const kb = backKey(key);
    }
    if (F && gear.cloak) cloakClasp(ctx, gear.cloak, false);
    const twoF = F && key && (key.K.front.og || key.K.front.wh === "off");
    if (F && !twoF) {
      const pairedF = qWeapon(gear.main_hand)?.kind === "paired"; // 成對武器：第二把匕首在左手（畫面右），刃朝外上
      const OHF = offHeld(gear), freeF = OHF ? OUTA : gear.off_hand ? (isShield(gear.off_hand) ? ARM.shA ?? OUTA : BOOKA + robeX(gear)) : outOf(gear); /* 第 16 版審查：持盾的左手也打直往外下方，和背面同一個姿勢 */ /* 第 16 版（使用者：「另一隻手不要貼在身上往外擺」）：空著的左手和持武器的手一樣打直往外下方；拿書張開一點；持盾照舊 */
      ctx.save(); ctx.translate(0, pz("armR")); FREEARM = !key && !pairedF && !SEAMIN && !OHF; arm(ctx, unit, freeF ? SHX : 8.5, -freeF, 0, 0, OHF ? (hand, c) => { mainWeapon(ctx, OHF, hand, -holdOf(OHF, "front") + OUTA, "front"); const r = rec("off"); if (r) r(hand, c); } : pairedF ? (hand, c) => { offDagger(ctx, gear.main_hand, hand, -holdOf(gear.main_hand, "front") + OUTA); const r = rec("off"); if (r) r(hand, c); } : rec("off")); FREEARM = false; /* 第 17 版 B 批補修（美術 PM 11-06）：正面空著的左手（含持盾那隻）逐隻判斷，布料類、非 key 時畫合成一條＋內線＋拳頭圈；拿第二把匕首的不算空手 */
      { const bh = fk(freeF ? SHX : 8.5, -freeF, 0); ctx.translate(0, bh[1] + 9.6 + (ARM.shf && isShield(gear.off_hand) ? 3.9 : 0)); /* 盾、書跟著手：盾心在拳頭外側 2.7、上方 3.9（和背面一樣），書往外 2，和身體之間露出空隙 */
        if (isShield(gear.off_hand)) { if (ARM.shf) ctx.translate(0, gear.off_hand.kind !== "shield_kite" ? 0 : gear.off_hand.form === "tower" ? 1.5 : -0.5); /* 第 17 版 B 批第 3 項：盾心（圓盾、鳶盾的盾心，塔盾的中心）對準拳頭 */ else if (gear.off_hand.kind === "shield_kite" && gear.off_hand.form !== "tower") ctx.translate(0, 3.5); /* 審查：鳶盾下半收尖，手從左下緣露出來 → 鳶盾往下 3.5，拳頭落在盾的方形上半、藏在盾後 */ shieldFront(ctx, gear.off_hand, bh[0] + (ARM.shf ? 0 : 2.7)); } else if (gear.off_hand && !OHF) PD.drawWeapon(ctx, gear.off_hand, bh[0] + (ARM.bk ?? 2), true); }
      ctx.restore();
    }
    if (S && SP.split) {
      // 第 8 版關鍵姿勢：兩隻手臂都在頭之前畫（舉起的手臂不蓋住下巴和嘴），武器畫在兩隻手上面（握把從拳頭上穿過去）
      // 第 9 版：mid＝遠側手臂 → 武器 → 近側手臂（朝東的弓：右手壓在弦上）；朝西近側手拿著書時，書最後畫、蓋在遠側手的杖上面
      SP.late = W && !!SP.near.item && SP.layer === "front";
      if (SP.far.front) sideArm(SP.far, true);
      if (SP.layer === "mid") sideWeapon();
      if (!SP.late && !SP.nearLate) { sideArm(SP.near, false); SP.nearDone = true; }
      if (SP.layer === "head") sideWeapon();
      if (W && SP.bowHand && SP.far.front) sideArm(SP.far, "hand"); /* 第 11 版：朝西拉弦手在遠側，弦和箭桿畫好後再補畫手（審查：「朝西的弦和箭桿壓在拉弦手上」） */
      if (W && SP.bowHand && SP.far.front) { const N = SP.near, nh = fk(N.sx, N.sA, N.eA, N.len ?? null); ctx.save(); ctx.beginPath(); ctx.rect(-80, -120, 160, 200); ctx.arc(nh[0], nh[1], 3, 0, TAU); ctx.clip("evenodd"); ctx.beginPath(); ctx.rect(-80, -120, 80 + nh[0] - 1.6, 200); ctx.clip(); arm(ctx, unit, N.sx, N.sA, N.eA, side, null, false, N.len ?? null); ctx.restore(); } /* 第 12 版：朝西近側左臂再畫一次、在拉弦手和弦上面（手附近不畫，弓把仍蓋在左手上；審查：「拉弦手蓋到近側左前臂下緣」） */
    } else if (S) {
      if (SP.layer === "head") sideWeapon();
      if (SP.far.front && SP.layer !== "front" && !SP.far.shield) sideArm(SP.far, true);
    }
    mark("head");
    ctx.save(); rotAt(ctx, 0, -29, S ? pz("lean") * 0.3 : 0);
    head(ctx, look, F ? "front" : B ? "back" : "side", side, gear);
    if (R) R.ears(ctx, look, F ? "front" : B ? "back" : "side", side, gear.head, "under");
    if (R) R.hat(ctx, look, gear.head, (it) => PD_headgear(ctx, it, F ? "front" : B ? "back" : "side")); else PD_headgear(ctx, gear.head, F ? "front" : B ? "back" : "side");
    if (R) R.ears(ctx, look, F ? "front" : B ? "back" : "side", side, gear.head, "over");
    if (R) R.horns(ctx, look, F ? "front" : B ? "back" : "side", side);
    ctx.restore();
    if (F && key && key.c === "bow") bowStill(ctx, unit, "front"); // 第 9 版：四面同一個持弓待機
    else if (F && key) {
      // 第 8 版：兩隻手臂先畫，武器畫在手上面（使用者：「法仗塗層要在最上面」）；弓是左手持弓、右手搭在弦上
      const k = key.K.front, who = k.wh ?? "main", sx = (who === "main" ? -1 : 1) * (k.st ? SHX : 8.5), k0 = stK(sx, k, who === "main" ? -1 : 1, gear), h = fk(sx, k0.sA, k0.eA), ol = ogLocal(k.og);
      if (ol) { const o = rot(k.a, ol), io = ik(-sx, [h[0] + o[0], h[1] + o[1]], sx < 0 ? 1 : -1); arm(ctx, unit, -sx, io.sA, io.eA, 0, rec(who === "main" ? "off" : "main")); }
      arm(ctx, unit, sx, k0.sA, k0.eA, 0, rec(who));
      if (who === "off" && !ol) arm(ctx, unit, -8.5, 0, 0, 0, rec("main"));
      const mgF = stMg(sx, k, k0, (key.kind === "scythe" && k.gripS != null ? k.gripS : k.grip) ?? 0, gear), MF = k.flipS && key.kind === "scythe" ? [-1, 0, 0, 1] : null; /* 第 14 版：拄地長柄的握點、正面鐮刃朝外 */
      BOWP = { nock: true }; mainWeapon(ctx, gear.main_hand, ARM.po && k.st ? [h[0] - ARM.po, h[1]] : h, k.a, "front", k.short || false, ol, mgF, MF); BOWP = null;
      if (key.c === "staff" || key.c === "polearm" || key.c.startsWith("greatsword")) wrap(ctx, unit, h, k.a); /* 第 13 版：杖身穿過拳頭；第 14 版：拄地長柄、雙手劍也是 */
      if (ol && key.c.startsWith("greatsword")) { const o = rot(k.a, ol); wrap(ctx, unit, [h[0] + o[0], h[1] + o[1]], k.a); } /* 第 14 版：拄劍的上手也握住劍柄 */
    } else if (F) {
      const rm = rec("main");
      const oF = holdA(gear); /* 第 15 版：正面同背面（鏡像）：持武器的手臂打直往外下方伸 */
      ctx.save(); ctx.translate(0, pz("armL")); arm(ctx, unit, -sxOf(gear), oF, 0, 0, (hand, c) => { mainWeapon(ctx, gear.main_hand, swOff(hand, -1, gear), holdOf(gear.main_hand, "front") - oF - ARM.swa, "front"); if (rm) rm(hand, c); }); ctx.restore();
    } else if (S && SP.split) {
      if (SP.layer === "front") sideWeapon();
      if (SP.late || SP.nearLate) sideArm(SP.near, false);
    } else if (S) {
      // 第 8 版：武器畫在握著它的那隻手上面
      const inNear = SP.wh === (W ? "off" : "main");
      if (SP.layer === "front") {
        if (SP.far.front && !SP.far.shield) sideArm(SP.far, true);
        if (inNear) { sideArm(SP.near, false); sideWeapon(); } else { sideWeapon(); sideArm(SP.near, false); }
      } else sideArm(SP.near, false); // 朝西：近側是副手（盾蓋在手上）
      if (W && isShield(gear.off_hand)) shieldSide(ctx, gear.off_hand);
    }
    ctx.restore();
    SEAM = false; SEAMIN = false; SHEDGE = false; FILLARM = false; FREEARM = false; EDGEK = null;
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
      const small = kind === "crossbow"; // 第 7 版：背面的單手武器跟手一起垂在身側（畫面右），拳套、法球也要露出來；第 13 版：背面的弩朝前下、弩口被身體擋住（只露出弩臂兩端），改查「被擋住」
      // 弓（第 8 版）：正面兩手拿、弓在身前（畫在身體上面，算露出）；背面弓在畫面左身側（只查有畫到）
      for (const [dir, view] of [["south", "front"], ["north", "back"]]) { const g = probe(kind, view, false, A.REST); const hid = g ? (kind === "bow" ? false : inBody(g.tip)) : false; r[dir] = g && inBox(g) ? ((dir === "north" && small ? hid : !hid) ? 1 : 0) : NaN; if (dir === "north") r.northSmall = small; }
      r.ok = { east: r.east > 1.5, west: r.west > 1.5, eastRest: r.eastRest >= -0.5, westRest: r.westRest >= -0.5, south: r.south === 1, north: r.north === 1 };
      r.pass = Object.values(r.ok).every(Boolean);
      rows.push(r);
    }
    rows.cloak = cloakTest();
    // 雙手武器：正面、背面兩隻手都在握把上（主手在握把原點、副手在副手握點，誤差 < 0.6）；側面靜止另外列出（只報告）。只當輔助，畫面要放大親眼看
    const near = (a, b) => !!a && !!b && Math.hypot(a[0] - b[0], a[1] - b[1]) < 0.6;
    rows.two = [];
    for (const kind of [...Object.keys(A.WEAPONS).filter((k) => CLASS_OF[k] && (KEY[CLASS_OF[k]].front.og || KEY[CLASS_OF[k]].front.wh === "off")), "greatsword"]) {
      const r = { kind, zh: A.WEAPON_ZH[kind] ?? "雙手劍", how: KEY[CLASS_OF[kind]].zh };
      for (const [dir, view, west] of [["south", "front", false], ["north", "back", false], ["east", "side", false]]) {
        const g = probe(kind, view, west, A.REST);
        // 背面的關鍵姿勢沒有副手握點（弓：持弓手往外伸、搭弦手放開）時，只查主手
        const kk = KEY[CLASS_OF[kind]], needOff = kind === "bow" || (dir === "north" ? !!kk.back.og : dir === "south" ? !!kk.front.og : true); /* 第 9 版：弓四面都要右手在弦上 */
        const hold = kind === "bow" ? "off" : "main", sec = hold === "main" ? "off" : "main"; // 第 8 版：弓是左手（副手）持弓、右手在弦上
        r[dir] = !!g && near(g.hands[hold], g.hand) && (!needOff || near(g.hands[sec], g.off));
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
        const okM = touches(wc2, wOff ? hands.off : hands.main), twoHere = twoKey && hands.off && hands.main && (view !== "side" || hands.offTwo);
        const okO = twoHere ? touches(wc2, wOff ? hands.main : hands.off) : true;
        r[dir] = { ok: okM && okO, t: `${wOff ? "持弓手（左）" : "主手"}${okM ? "握住" : "沒握到"}${twoHere ? `・${wOff ? "右手在弦上" : "副手"}${okO ? (wOff ? "" : "握住") : "沒握到"}` : ""}` };
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
      const hands = {}; POSE = { tintOff: "#ff00ff", hands }; draw(ctx, u, "back"); POSE = null;
      // 拿盾：盾要蓋住整隻副手（整隻手臂都算）；拿書：書小，只算手肘以下（前臂與手）
      /* 第 16 版：拿書的手伸到身體外側（看得到手臂），改成只算拳頭（手心半徑 2.6 單位內）露出多少：書要蓋住大半，只露一點邊緣 */
      const sh = isShield(u.gear.off_hand), y0 = sh ? 0 : Math.round(220 - 16 * K), d = ctx.getImageData(0, y0, 256, 256 - y0).data; let n = 0;
      const hb = !sh && hands.off ? hands.off : null;
      for (let i = 0; i < d.length; i += 4) if (d[i] === 255 && d[i + 1] === 0 && d[i + 2] === 255) { const q = i / 4, px = q % 256, py = y0 + Math.floor(q / 256); if (!hb || Math.hypot(px - hb[0], py - hb[1]) <= 2.6 * K) n++; }
      const area = n / (K * K);
      // 第 8 版：拿盾時左前臂穿過盾背皮帶、手握住皮帶，要看得到（≥ 4 單位²）；有披風時披風在最上層，蓋住也算對；拿書仍要被擋（≤ 2）
      if (sh && u.gear.cloak) out.push({ zh, ok: true, t: `披風在最上層，副手露出 ${area.toFixed(1)} 單位²` });
      else if (sh) out.push({ zh, ok: area >= 4, t: `持盾的前臂與手露出 ${area.toFixed(1)} 單位²（要看得到）` });
      else { /* 第 16 版審查：拳頭露出 0.2～2 單位²；手臂和長袍之間要有空隙：y −13 那一列、x −12～−8 之間透明的寬度 ≥ 2.6 單位（兩邊外框各吃掉 1.3） */
        const row = ctx.getImageData(Math.round(128 - 12 * K), Math.round(220 - 13 * K), Math.round(4 * K), 1).data; let gap = 0;
        for (let i = 3; i < row.length; i += 4) if (row[i] === 0) gap++;
        const g = gap / K; out.push({ zh, ok: area >= 0.2 && area <= 2 && (SEAMF || g >= 2.6), t: `拳頭露出 ${area.toFixed(1)} 單位²（0.2～2）・手臂與長袍空隙 ${g.toFixed(1)} 單位（${SEAMF ? "E 不查：手臂微微離開，書蓋在長袍上" : "≥ 2.6"}）` }); } /* 第 17 版 B 批：使用者選 E（手臂只微微離開），長袍下擺往外斜、書蓋在這一列，留不出 2.6 單位的空隙又不比第 15 版寬，E 只查拳頭露出 */
    }
    return out;
  }
  // 背面的手：手在身體前方，畫面上被身體擋住；手心那一點和周圍 4 點（半徑 1.2）都不能是手的顏色（最多露一點邊）
  function handTest() {
    const TPL = PD.TEMPLATES, out = [];
    for (const [zh, tpl] of [["法師", "hero_mage"], ["劍盾", "hero_fighter"], ["弓手", "hero_archer"], ["盜賊", "bandit"], ["鳶盾", "bandit_shieldbearer"], ["頭目", "bandit_boss"]]) {
      // 第 8 版：弓手背上的箭袋和皮手套同色（都是皮革），會被誤判成「手露出」；只拿掉箭袋再查手（畫面上箭袋照畫）
      const u0 = TPL[tpl], u = tpl === "hero_archer" ? { look: u0.look, gear: { ...u0.gear, back: { slot: "back", kind: "none" } } } : u0, K = 4, C = document.createElement("canvas"); C.width = C.height = 256;
      const ctx = C.getContext("2d", { willReadFrequently: true });
      ctx.setTransform(K, 0, 0, K, 128, 220);
      const hands = {}; POSE = { hands }; draw(ctx, u, "back"); POSE = null;
      const hc = (u.gear.hands && u.gear.hands.kind !== "bracers" ? colors(u.gear.hands)[0] : u.look.skin).toLowerCase();
      const px = ([x, y]) => { const d = ctx.getImageData(Math.round(x), Math.round(y), 1, 1).data; return "#" + [d[0], d[1], d[2]].map((v) => v.toString(16).padStart(2, "0")).join(""); };
      const seen = [];
      for (const who of ["main", "off"]) {
        const h = hands[who]; if (!h) { seen.push(`${who}沒畫`); continue; }
        // 第 7 版：只查「拿在身體前方」的手；垂在身側的手（空手、法杖、弓）背面本來就看得到（審查：「背面垂在身側的手都消失了」）
        const kq = qWeapon(u.gear.main_hand), bow = kq?.kind === "bow", front = who === "main" ? !!kq && !!CLASS_OF[kq.kind] && !["staff", "bow"].includes(kq.kind) && !u.gear.off_hand : !!u.gear.off_hand && !isShield(u.gear.off_hand); // 第 8 版：弓手背面兩手都在身側、看得到
        if (!front) { seen.push(isShield(u.gear.off_hand) && who === "off" ? "副手穿過盾背皮帶（看得到，第 8 版設計）" : `${who === "main" ? "主手" : "副手"}垂在身側（看得到，設計）`); continue; }
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
        break; // 第 8 版：結在後腦正中，正面看不到結（四面一致）
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
    /* 第 14 版：外框改成「圓盤膨脹」（審查：弩臂末端、箭頭、劍尖底下的外框變成梳齒）。
       舊做法是把剪影往 8（16）個方向各位移一次再疊起來：比位移還細的尖端（箭頭、弩臂、劍尖）會被複製成一根根分開的齒。
       新做法：剪影依序沿 12 個方向各做一次短線段膨脹（Minkowski 和），合起來是近似半徑 k 的圓盤（24 邊形），每一步都連續，細線和尖端外框是平滑的一圈。
       外框的寬度不變（半徑 1.3 單位）；畫在離屏解析度上，最後縮小一次貼上。 */
    const cw = sil.width, chh = sil.height, mk = () => { const c = document.createElement("canvas"); c.width = cw; c.height = chh; return c.getContext("2d"); };
    const dil = (src, r) => {
      const N = 12, a = (r * Math.PI) / (2 * N), P = [mk(), mk()]; let cur = src, n = 0;
      for (let i = 0; i < N; i++) {
        const t = (Math.PI * i) / N, ux = Math.cos(t) * a, uy = Math.sin(t) * a, c = P[n++ % 2];
        c.clearRect(0, 0, cw, chh); for (const f of [-1, -0.5, 0, 0.5, 1]) c.drawImage(cur, ux * f, uy * f); cur = c.canvas;
      }
      const o = mk(); o.drawImage(cur, 0, 0); return o.canvas;
    };
    if (opts.outline === false) { /* 第 14 版：不畫外框（只用來比對：外框以外的像素有沒有變） */ }
    else if (opts.close ?? (qWeapon(unit.gear?.main_hand)?.kind === "bow" && view !== "back")) { /* 第 14 版：背面不做閉合（弓和手都被身體擋住，沒有弦的窄縫；閉合會把肩下的凹處填成一塊黑色外框，審查：「r05 背面身體兩側一塊沒填色的黑色輪廓」） */
      /* 第 11 版：弓的弦、箭桿和弓臂、身體之間的窄縫，外框從兩邊長過來卻沒接上，留下背景色碎片（審查：b4～b6、a11）。
         外框改成「膨脹後再閉合」：先做外框，再把比 2×1.5 單位窄的背景縫填成外框色。只用在拿弓的人物，其他格子的外框不變。 */
      const inv = (src) => { const c = mk(); c.fillStyle = "#000"; c.fillRect(0, 0, cw, chh); c.globalCompositeOperation = "destination-out"; c.drawImage(src, 0, 0); return c.canvas; };
      const O = dil(sil, k), r = 1.5 * size * dpr, cl = mk(); cl.drawImage(inv(dil(inv(dil(O, r)), r)), 0, 0); cl.drawImage(O, 0, 0); /* 閉合＝先膨脹 r 再侵蝕 r */
      cl.globalCompositeOperation = "source-in"; cl.fillStyle = OUT; cl.fillRect(0, 0, cw, chh);
      ctx.drawImage(cl.canvas, dx0, dy0, W * size, H * size);
    } else { const O = dil(sil, k).getContext("2d"); O.globalCompositeOperation = "source-in"; O.fillStyle = OUT; O.fillRect(0, 0, cw, chh); ctx.drawImage(O.canvas, dx0, dy0, W * size, H * size); }
    ctx.drawImage(off, dx0, dy0, W * size, H * size);
    ctx.restore();
  }
  return { draw, stamp, setPose: (p) => { POSE = p; }, selfTest, QW, TWO, KEY, CLASS_OF, fk, rot, BOW_EY };
})();
