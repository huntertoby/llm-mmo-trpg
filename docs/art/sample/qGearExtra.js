// qGearExtra.js：Q 版還沒有的裝備部件（C 時期新增的形制＋圍裙），四方向分畫（美術 PM 畫圖 agent，2026-11-07）。
// 使用者（11-07）：「所有人先停下 先讓q板完成再開始工作 把所有需要q版的都完成 腳色 動畫 怪物 npc 等 全部」。
// 清單來源：content/equipment/appearance.yaml 的 kinds／forms，扣掉 qDoll.js 已經四方向畫好的（頭巾、頭冠、面紗、護目鏡、王冠、全罩盔、
//   寬帽、兜帽、皮帽、法師帽、頭盔、角盔、護腕（皮）、手套、鐵手套、靴、脛甲、鐵靴、披風、項鍊、念珠……）。
// 做法（不改 qDoll.js）：先用 QDoll 畫「最接近的底」（例：鱗甲的底是鎖甲），再把這裡的部件疊上去，最後整隻一起描剪影外框（同 stamp 的 1.3 單位）。
//   遮擋：底圖另外畫一張「色鍵圖」（衣服、皮膚換成鍵色），用填色法找出「看得到的軀幹」與「手臂、拳頭」：
//   軀幹上的部件只畫在看得到的軀幹上；其餘部件不蓋手臂與拳頭（側面近側手臂垂在胸前時，鱗片、圍裙不會畫到手臂上）。
//   手上的部件掛在 QDoll 記下的拳頭位置（setPose({hands:{}})），前臂方向＝肩到拳頭；側面只畫近側手（朝東右手、朝西左手）。
//   頸飾、披肩不蓋臉：挖掉頭的圓（頭心 (0,−29)、r 8.6）。
// 座標同 qDoll.js：腳底 (0,0)、往上 −y；側面朝東（+x 是前方），朝西由畫布鏡像。確定性：不用 Math.random。
window.QGearExtra = (() => {
  const TAU = Math.PI * 2, OUT = "#16121a", Q = window.QDoll, PD = window.PaperDoll;
  const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const mix = (a, b, t) => "#" + hex(a).map((v, i) => Math.round(v + (hex(b)[i] - v) * t).toString(16).padStart(2, "0")).join("");
  const dark = (c, t = 0.3) => mix(c, "#000000", t), light = (c, t = 0.3) => mix(c, "#ffffff", t);
  const colors = (it) => PD.itemColors(it);
  const fill = (g, c, path) => { g.beginPath(); g.fillStyle = c; path(); g.fill(); };
  const rr = (g, x, y, w, h, r) => g.roundRect(x, y, w, h, r);
  const line = (g, c, w, pts) => { g.strokeStyle = c; g.lineWidth = w; g.lineCap = "round"; g.lineJoin = "round"; g.beginPath(); pts.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y))); g.stroke(); };
  const noHead = (g, V) => { g.beginPath(); g.rect(-60, -90, 120, 120); g.arc(0, -29, 8.45, 0, TAU); g.clip("evenodd"); }; // 頸飾、披肩：不蓋臉（圓＝QDoll 的頭，r 8.5 往內一點，不留縫）

  // ============================== 合成：底圖（QDoll）＋部件＋整隻外框 ==============================
  // 色鍵圖（審查第 3 輪改）：衣服＝綠、皮膚＝洋紅、褲子／腰帶／鞋＝青、披風＝橘；其他顏色（武器、盾、頭髮、背掛…）＝擋在前面的東西。
  //   軀幹＝從軀幹種子沿「亮綠」填色（袖子的描邊、拳頭圈是暗綠，填色會停在那裡）；側面近側手臂前方那一條軀幹另外補種子。
  //   手＝每隻手各自一個「前臂膠囊」（拳頭往肩膀 7 單位、半徑 3）裡看得到的手臂像素，膨脹 0.6 單位給袖口外翻；扣掉軀幹、擋在前面的東西；
  //   側面遠側手再扣掉近側手的膠囊（近側手臂在前）。背面披風在最上層，披風也算擋在前面。
  const KEY = { body: "#00fe02", skin: "#fe02fc", leg: "#02fefe", cloak: "#fe8002" };
  const mk = (w, h) => { const c = document.createElement("canvas"); c.width = w; c.height = h; return c; };
  function dilate(src, r) { // 同 qDoll stamp：12 方向線段膨脹（近似圓盤），尖端不會變梳齒
    const w = src.width, h = src.height, N = 12, a = (r * Math.PI) / (2 * N), P = [mk(w, h), mk(w, h)]; let cur = src, n = 0;
    for (let i = 0; i < N; i++) { const t = (Math.PI * i) / N, ux = Math.cos(t) * a, uy = Math.sin(t) * a, c = P[n++ % 2], g = c.getContext("2d"); g.clearRect(0, 0, w, h); for (const f of [-1, -0.5, 0, 0.5, 1]) g.drawImage(cur, ux * f, uy * f); cur = c; }
    const o = mk(w, h); o.getContext("2d").drawImage(cur, 0, 0); return o;
  }
  const tint = (src, col) => { const c = mk(src.width, src.height), g = c.getContext("2d"); g.drawImage(src, 0, 0); g.globalCompositeOperation = "source-in"; g.fillStyle = col; g.fillRect(0, 0, c.width, c.height); return c; };
  const toCanvas = (arr, W, H) => { const c = mk(W, H), g = c.getContext("2d"), im = g.createImageData(W, H); for (let i = 0; i < W * H; i++) if (arr[i]) im.data[i * 4 + 3] = 255; g.putImageData(im, 0, 0); return c; };
  const alphaOf = (c) => { const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data, a = new Uint8Array(c.width * c.height); for (let i = 0; i < a.length; i++) a[i] = d[i * 4 + 3] > 127 ? 1 : 0; return a; };
  function flood(ok, seeds, W, H, out) { const st = []; for (const i of seeds) if (i >= 0 && ok(i) && !out[i]) { out[i] = 1; st.push(i); } while (st.length) { const i = st.pop(), x = i % W; for (const j of [x > 0 ? i - 1 : -1, x < W - 1 ? i + 1 : -1, i - W, i + W]) { if (j < 0 || j >= W * H || out[j] || !ok(j)) continue; out[j] = 1; st.push(j); } } return out; }
  function masks(unit, view, west, s, ox, oy, W, H, hands) {
    const kc = (it, col) => (it ? { ...it, color: col, element: undefined } : it);
    const look = { ...unit.look, skin: KEY.skin, pants: KEY.leg, belt: KEY.leg };
    const gear = { ...unit.gear, hands: undefined, feet: kc(unit.gear.feet, KEY.leg), cloak: kc(unit.gear.cloak, KEY.cloak), body: { ...(unit.gear.body ?? { kind: "shirt" }), kind: ["mail", "plate", "leather"].includes(unit.gear.body?.kind) ? "shirt" : unit.gear.body?.kind ?? "shirt", color: KEY.body, element: undefined, crest: undefined } };
    const c = mk(W, H), g = c.getContext("2d"); Q.stamp(g, { look, gear }, view, ox, oy, s, west, { outline: false, dpr: 1.5 });
    const d = g.getImageData(0, 0, W, H).data, N = W * H, cls = new Uint8Array(N), bright = new Uint8Array(N);
    for (let i = 0; i < N; i++) { const r = d[i * 4], gg = d[i * 4 + 1], b = d[i * 4 + 2], a = d[i * 4 + 3]; if (a < 128) continue;
      if (gg > 50 && gg > 1.6 * Math.max(r, b)) { cls[i] = 1; bright[i] = gg > 200 && r < 70 && b < 70 ? 1 : 0; }        // 衣服（含暗綠描邊）
      else if (r > 120 && b > 120 && gg < 0.6 * Math.min(r, b)) cls[i] = 2;                                                  // 皮膚
      else if (gg > 120 && b > 120 && r < 0.5 * Math.min(gg, b)) cls[i] = 3;                                                 // 褲子、腰帶、鞋
      else if (r > 200 && gg > 90 && gg < 160 && b < 60) cls[i] = 4;                                                         // 披風
      else cls[i] = 5; }                                                                                                       // 擋在前面的東西
    const U = (i) => [((i % W) - ox) / s * (west ? -1 : 1), (Math.floor(i / W) - oy) / s], P = (u, v) => Math.round(oy + s * v) * W + Math.round(ox + s * (west ? -u : u));
    const S = view === "side", yHand = oy + s * -16;
    // 近側手臂（側面）：從前臂中段沿亮綠填色，袖子描邊圈住
    const nearArm = new Uint8Array(N); if (S) { const nh = hands.find((h) => h.near); if (nh) { const m = [(nh.at[0] + nh.sh[0]) / 2, (nh.at[1] + nh.sh[1]) / 2]; flood((i) => bright[i], [P(m[0], m[1]), P(m[0], m[1] + 1.5)], W, H, nearArm); } } // 種子在前臂中段：只走亮綠（拳頭貼在軀幹上，從拳頭走會漏進軀幹）
    const torso = new Uint8Array(N), seeds = (S ? [[-3.6, -15], [-3, -18], [-4, -12]] : [[0, -15], [0, -18], [-2, -12], [2, -12]]).map(([u, v]) => P(u, v));
    if (S) for (const [u, v] of [[5, -17], [5, -12.5], [4.9, -14.6], [5.1, -19]]) { const i = P(u, v); if (!nearArm[i]) seeds.push(i); } // 側面：近側手臂前方那一條軀幹
    flood((i) => bright[i] && !nearArm[i], seeds, W, H, torso);
    const arm = new Uint8Array(N), occ = new Uint8Array(N);
    for (let i = 0; i < N; i++) { if (!torso[i] && (cls[i] === 1 || (cls[i] === 2 && Math.floor(i / W) > yHand))) arm[i] = 1; if (cls[i] === 5 || (cls[i] === 4 && view === "back")) occ[i] = 1; }
    const armsC = dilate(toCanvas(arm, W, H), 0.75 * s), occC = toCanvas(occ, W, H), torsoC = toCanvas(torso, W, H);
    const tg = torsoC.getContext("2d"); tg.globalCompositeOperation = "destination-out"; tg.drawImage(armsC, 0, 0); tg.drawImage(occC, 0, 0);
    // 每隻手的範圍
    const cap = (h, i, R = 3) => { const [u, v] = U(i), [ax, ay] = h.at, L = Math.hypot(h.sh[0] - ax, h.sh[1] - ay) || 1, dx = (h.sh[0] - ax) / L, dy = (h.sh[1] - ay) / L, t = Math.max(0, Math.min(7, (u - ax) * dx + (v - ay) * dy)); return Math.hypot(u - ax - dx * t, v - ay - dy * t) <= R; };
    const near = hands.find((h) => h.near);
    const handMask = (h) => {
      const vis = new Uint8Array(N), within = new Uint8Array(N);
      for (let i = 0; i < N; i++) { if (!cap(h, i, 3.2)) continue; if (S && !h.near && near && cap(near, i, 3.2)) continue; within[i] = 1; if (arm[i]) vis[i] = 1; }
      const m = dilate(toCanvas(vis, W, H), 0.6 * s), mg = m.getContext("2d"); mg.globalCompositeOperation = "destination-in"; mg.drawImage(toCanvas(within, W, H), 0, 0);
      mg.globalCompositeOperation = "destination-out"; mg.drawImage(torsoC, 0, 0); mg.drawImage(occC, 0, 0); return m;
    };
    return { torso: torsoC, arms: armsC, occ: occC, handMask };
  }
  /**
   * 畫一隻穿上額外部件的 Q 版小人。unit＝QDoll 的 { look, gear }；ids＝這裡的部件 id（可多個）。其他參數同 QDoll.stamp。
   * 每個部件會先把 unit 換成它的「底」（base），再在底上疊部件。
   */
  function stamp(ctx, unit0, ids, view, cx, cy, size = 1, west = false) {
    const SS = 2, s = size * SS, W = Math.ceil(128 * s), H = Math.ceil(112 * s), ox = 64 * s, oy = 98 * s;
    let unit = { look: { ...unit0.look }, gear: { ...unit0.gear } };
    const defs = ids.map((id) => DEFS[id]).filter(Boolean);
    for (const d of defs) if (d.base) unit = d.base(unit);
    const A = mk(W, H), ag = A.getContext("2d"), hands = {};
    Q.setPose({ hands }); Q.stamp(ag, unit, view, ox, oy, s, west, { outline: false, dpr: 1.5 }); Q.setPose(null);
    const S = view === "side", B = view === "back", F = view === "front";
    const toU = ([x, y]) => [(x / (s * 1.5) - 64) * (west ? -1 : 1), y / (s * 1.5) - 98]; // POSE.hands 是 stamp 離屏畫布（s×dpr）的座標
    const HU = {};
    for (const k of ["main", "off"]) if (hands[k]) HU[k] = toU(hands[k]);
    // 沒記到的手（空手）：照 E 手臂（肩 ±8.5、往外 0.325、長 10.5）算；側面遠側手垂在近側手後面一點
    const fk = (sx, a) => [sx + Math.sin(a) * 10.5 * Math.sign(sx), -20 + Math.cos(a) * 10.5];
    if (!S) { HU.main ??= fk(F ? -8.5 : 8.5, 0.325); HU.off ??= fk(F ? 8.5 : -8.5, 0.325); }
    else { const nk = west ? "off" : "main", fk2 = west ? "main" : "off"; HU[nk] ??= [2.9, -9.6]; HU[fk2] ??= [1.4, -9.8]; }
    const nearKey = west ? "off" : "main";
    const shoulder = (h, near) => (S ? [near ? 2 : 3, -20] : [h[0] < 0 ? -8.5 : 8.5, -20]);
    const handList = S ? [west ? "main" : "off", nearKey] : ["main", "off"]; // 側面：遠側先畫
    const V = { view, S, B, F, west, unit, hands: handList.map((k) => ({ who: k, near: S && k === nearKey, at: HU[k], sh: shoulder(HU[k], S && k === nearKey) })) };
    const needMask = defs.some((d) => d.torso || d.free || d.hand);
    const M = needMask ? masks(unit, view, west, s, ox, oy, W, H, V.hands) : null;
    const layer = (fn, clip) => {
      const L = mk(W, H), g = L.getContext("2d"); g.setTransform(west ? -s : s, 0, 0, s, ox, oy); fn(g, V); g.setTransform(1, 0, 0, 1, 0, 0);
      if (clip === "torso") { g.globalCompositeOperation = "destination-in"; g.drawImage(M.torso, 0, 0); }
      else if (clip === "free") { g.globalCompositeOperation = "destination-out"; g.drawImage(M.arms, 0, 0); g.drawImage(M.occ, 0, 0); }
      else if (clip && clip.mask) { g.globalCompositeOperation = "destination-in"; g.drawImage(clip.mask, 0, 0); }
      ag.drawImage(L, 0, 0);
    };
    for (const d of defs) if (d.erase) { ag.save(); ag.setTransform(west ? -s : s, 0, 0, s, ox, oy); ag.globalCompositeOperation = "destination-out"; ag.beginPath(); d.erase(ag, V); ag.fill(); ag.restore(); } // 擦掉底圖伸出去、新部件用不到的部分（例：毛帽側面的帽舌）
    for (const d of defs) {
      if (d.torso) layer(d.torso, "torso"); if (d.free) layer(d.free, "free"); if (d.top) layer(d.top, null);
      if (d.hand) for (const h of V.hands) layer((g) => { g.save(); const a = Math.atan2(h.at[1] - h.sh[1], h.at[0] - h.sh[0]) - Math.PI / 2; g.translate(h.at[0], h.at[1]); g.rotate(a); d.hand(g, V, h); g.restore(); }, { mask: M.handMask(h) }); // 手：只畫在看得到的那隻手臂上（武器、盾、背面披風在上面）
    }
    const rim = tint(dilate(A, 1.3 * s), OUT);
    const dx = cx - 64 * size, dy = cy - 98 * size;
    ctx.save(); ctx.imageSmoothingEnabled = true; ctx.drawImage(rim, dx, dy, W / SS, H / SS); ctx.drawImage(A, dx, dy, W / SS, H / SS); ctx.restore();
  }

  // ============================== 部件（17 件） ==============================
  // 底：base(unit) → 換成最接近的 QDoll 部件。torso：只畫在看得到的軀幹上；free：不蓋手臂、拳頭；top：最上層；hand：手的座標系（+y 往指尖、−y 往手肘）。
  const setG = (slot, it) => (u) => ({ look: u.look, gear: { ...u.gear, [slot]: it } });
  const STEEL = "#b8c0c8", COPPER = "#c8803a", GOLD = "#e8bb48", BONE = "#efe6cc", CORD = "#4a3424";
  const torsoBox = (V) => (V.S ? [-5.6, 5.6] : [-7.6, 7.6]);
  const DEFS = {
    // ---------- 身體 ----------
    scale_mail: { zh: "鱗甲", slot: "身體", from: "mail・scale", base: setG("body", { slot: "body", kind: "mail", material: "iron" }),
      note: "鎖甲的點換成一排排魚鱗（U 形線），正面、背面、側面同一個紋；鱗片停在腰帶上方（最下排不碰腰帶）；側面近側手臂前方那一條軀幹也換成鱗片",
      torso(g, V) { const [c, d] = colors(V.unit.gear.body), [x0, x1] = torsoBox(V); fill(g, c, () => g.rect(x0, -22, x1 - x0, 13));
        let row = 0; for (let y = -19.6; y < -11.2; y += 2.3, row++) for (let x = x0 + (row % 2 ? 1.2 : 0); x <= x1 + 1; x += 2.4) { g.strokeStyle = d; g.lineWidth = 0.55; g.beginPath(); g.arc(x, y, 1.15, 0.15 * Math.PI, 0.85 * Math.PI); g.stroke(); } } },
    hunter: { zh: "獵裝", slot: "身體", from: "leather・hunter", base: setG("body", { slot: "body", kind: "leather", color: "#6a5a3a" }),
      note: "皮背心加長成外套：下襬蓋過大腿（正面中間開衩、側面後開衩、背面中縫），正面兩個口袋蓋（在斜背帶下面）；側面口袋在前緣、背面不畫",
      torso(g, V) { const [, d] = colors(V.unit.gear.body);
        if (V.F) for (const x of [-4.6, 1.4]) { fill(g, d, () => rr(g, x, -14.2, 3.2, 1.6, 0.5)); fill(g, GOLD, () => g.arc(x + 1.6, -13.4, 0.45, 0, TAU)); }
        else if (V.S) fill(g, d, () => rr(g, 2.6, -14.2, 2.8, 1.6, 0.5));
        // 斜背帶畫回口袋蓋上面（同 qDoll body() 的 leather：正面右肩到左腰；側面照朝東／朝西各自的方向）
        if (V.F) line(g, d, 1, [[-5, -20], [5, -11]]); else if (V.S) line(g, d, 0.85, V.west ? [[1.5, -20.8], [-3.5, -11]] : [[-1.5, -20.8], [4.6, -11]]); },
      free(g, V) { const [c, d] = colors(V.unit.gear.body), w = V.S ? 5.9 : 8.2;
        fill(g, c, () => { g.moveTo(-w + 0.6, -7.6); g.lineTo(w - 0.6, -7.6); g.lineTo(w, -3.6); g.lineTo(-w, -3.6); g.closePath(); });
        if (V.F) fill(g, dark(c, 0.35), () => { g.moveTo(-0.9, -3.6); g.lineTo(0, -7.4); g.lineTo(0.9, -3.6); g.closePath(); });
        else if (V.B) line(g, d, 0.6, [[0, -7.4], [0, -3.8]]);
        else fill(g, dark(c, 0.35), () => { g.moveTo(-w + 0.3, -3.6); g.lineTo(-w + 1.6, -6.6); g.lineTo(-w + 2.4, -3.6); g.closePath(); }); } },
    plate_full: { zh: "全身板甲", slot: "身體", from: "plate・full", base: setG("body", { slot: "body", kind: "plate", material: "steel" }),
      note: "qDoll 板甲（已有肩甲）＋護頸＋兩片腿甲裙＝全身板甲（半身板甲照 qDoll 的 form half 不畫肩甲）；側面一片腿甲在前、一片在後，背面兩片",
      free(g, V) { const [c, d] = colors(V.unit.gear.body), hi = light(c, 0.25);
        const plates = V.S ? [[-5.4, 4.8], [-0.2, 5.6]] : [[-7.6, 7.2], [0.4, 7.2]];
        for (const [x, w] of plates) { fill(g, c, () => rr(g, x, -7.6, w, 4.6, [0, 0, 1.6, 1.6])); line(g, d, 0.55, [[x + 0.6, -5.4], [x + w - 0.6, -5.4]]); }
        if (!V.S) line(g, d, 0.7, [[0, -7.4], [0, -3.2]]); } ,
      top(g, V) { const [c, d] = colors(V.unit.gear.body); g.save(); noHead(g, V); fill(g, c, () => V.S ? rr(g, -4.6, -22.4, 9.4, 2.6, 1.2) : rr(g, -5.6, -22.4, 11.2, 2.6, 1.2)); line(g, d, 0.5, V.S ? [[-4, -20.9], [4.2, -20.9]] : [[-5, -20.9], [5, -20.9]]); g.restore(); } },
    coat_cape: { zh: "披風外套", slot: "身體", from: "coat・cape", base: setG("body", { slot: "body", kind: "coat", color: "#4a5058" }),
      note: "旅行外套肩上多一片短披肩（蓋過肩膀與上臂），正面圓下緣、背面較長；側面從前胸繞到後背",
      top(g, V) { const [c, d] = colors(V.unit.gear.body), k = dark(c, 0.18); g.save(); noHead(g, V);
        if (V.S) fill(g, k, () => { g.moveTo(-6.2, -21.4); g.quadraticCurveTo(0, -22, 5.6, -21.4); g.quadraticCurveTo(7, -18, 5.4, -15.6); g.quadraticCurveTo(0, -14.4, -6.6, -14.6); g.quadraticCurveTo(-7.6, -18, -6.2, -21.4); g.closePath(); });
        else fill(g, k, () => { g.moveTo(-9.6, -21); g.quadraticCurveTo(0, -22.4, 9.6, -21); g.quadraticCurveTo(11.6, -17, 10.6, V.B ? -13.6 : -15.2); g.quadraticCurveTo(0, V.B ? -11.6 : -13.2, -10.6, V.B ? -13.6 : -15.2); g.quadraticCurveTo(-11.6, -17, -9.6, -21); g.closePath(); });
        line(g, d, 0.6, V.S ? [[-6, -15.6], [5, -16.4]] : [[-9.8, -16], [0, V.B ? -12.8 : -14.2], [9.8, -16]]);
        if (V.F) fill(g, GOLD, () => g.arc(0, -19.4, 0.9, 0, TAU)); else if (V.S) fill(g, GOLD, () => g.arc(5, -19.6, 0.8, 0, TAU));
        g.restore(); } },
    apron: { zh: "圍裙", slot: "身體（配件）", from: "（新）圍裙", base: (u) => u,
      note: "正面：胸兜＋裙片蓋過腰帶到大腿，一個口袋；側面只在前緣一片＋腰後綁帶；背面只看到頸帶與腰後的蝴蝶結",
      free(g, V) { const c = "#e6dcc4", d = "#b8a888";
        if (V.F) { fill(g, c, () => { g.moveTo(-4.6, -18.6); g.lineTo(4.6, -18.6); g.lineTo(4.8, -10.4); g.lineTo(6.6, -9.6); g.lineTo(6.2, -2.4); g.lineTo(-6.2, -2.4); g.lineTo(-6.6, -9.6); g.lineTo(-4.8, -10.4); g.closePath(); });
          fill(g, d, () => rr(g, -2.4, -7.4, 4.8, 2.6, 0.6)); line(g, d, 0.5, [[-6.6, -9.5], [6.6, -9.5]]); }
        else if (V.S) { fill(g, c, () => { g.moveTo(4.4, -18.6); g.lineTo(5.9, -18.6); g.lineTo(6.6, -9.6); g.lineTo(6.6, -2.4); g.lineTo(4.4, -2.4); g.lineTo(5.0, -9.6); g.closePath(); }); line(g, d, 0.8, [[-5.4, -9.0], [5, -9.0]]); }
        else { line(g, d, 0.9, [[-7.4, -9.0], [7.4, -9.0]]); fill(g, c, () => { g.moveTo(0, -9); g.lineTo(-2.8, -10.6); g.lineTo(-2.8, -7.4); g.closePath(); g.moveTo(0, -9); g.lineTo(2.8, -10.6); g.lineTo(2.8, -7.4); g.closePath(); }); line(g, d, 0.6, [[-0.6, -8.6], [-1.4, -6]]); line(g, d, 0.6, [[0.6, -8.6], [1.4, -6]]); } },
      top(g, V) { const d = "#b8a888"; if (V.S) return; g.save(); noHead(g, V); line(g, d, 0.7, V.F ? [[-4.2, -18.4], [-3, -21.6]] : [[-3, -21.6], [0, -19.6], [3, -21.6]]); if (V.F) line(g, d, 0.7, [[4.2, -18.4], [3, -21.6]]); g.restore(); } },
    // ---------- 頭 ----------
    hood_cowl: { zh: "斗篷帽", slot: "頭", from: "hood・cowl", base: setG("head", { slot: "head", kind: "hood", color: "#5a4a6a" }),
      note: "布兜帽下面接一片披領：正面尖角垂到胸口、背面尖角到肩胛，側面前後各一角；和披風外套的圓披肩分得開",
      top(g, V) { const it = V.unit.gear.head, [c, d] = colors(it); g.save(); if (!V.B) noHead(g, V); // 背面：披領蓋到兜帽下緣，不露頭髮
        if (V.S) fill(g, c, () => { g.moveTo(-8.4, -23); g.lineTo(7.6, -23.8); g.lineTo(6.6, -16); g.lineTo(1.6, -18.6); g.lineTo(-3, -15.4); g.lineTo(-8.8, -17.6); g.closePath(); }); // 側面：前緣往上包到下巴下，不露衣領
        else if (V.B) fill(g, c, () => { g.moveTo(-9.6, -23.2); g.lineTo(9.6, -23.2); g.lineTo(10.4, -17.6); g.lineTo(0, -12.6); g.lineTo(-10.4, -17.6); g.closePath(); });
        else fill(g, c, () => { g.moveTo(-9.6, -23); g.quadraticCurveTo(0, -17.8, 9.6, -23); g.lineTo(10.4, -17.6); g.lineTo(0, -13.8); g.lineTo(-10.4, -17.6); g.closePath(); }); // 正面：和兜帽的接縫是順著下巴的弧線
        line(g, d, 0.6, V.S ? [[-8.6, -17.6], [-3, -15.4], [1.6, -18.6], [6.4, -16]] : [[-10.4, -17.6], [0, V.B ? -12.6 : -13.8], [10.4, -17.6]]);
        g.restore(); } },
    cap_fur: { zh: "毛帽", slot: "頭", from: "cap・fur", base: setG("head", { slot: "head", kind: "cap", color: "#6a4a2e" }),
      note: "皮帽的帽緣換成一圈米白毛邊（圓角、下緣圓凸、不凸出頭），兩側垂護耳；側面護耳是沿後腦頭形垂下的一片毛",
      erase(g, V) { if (V.S) g.rect(8.7, -34.5, 6, 4.4); }, // 側面：皮帽的帽舌伸出臉前的那段擦掉
      top(g, V) { const F = "#ece4cc", Fd = "#c8bc9c";
        // 毛邊：圓角、剪在頭＋帽頂的輪廓裡（不凸出頭）；下緣一排圓凸
        g.save(); g.beginPath(); g.arc(0, -29, 8.5, 0, TAU); g.arc(V.S ? -0.4 : 0, -31, 9.1, Math.PI, 0); g.clip();
        const x0 = V.S ? -9.6 : -9.2, x1 = V.S ? 8.8 : 9.2, n = 5, st = (x1 - x0) / n;
        fill(g, F, () => { g.moveTo(x0, -32); g.quadraticCurveTo(x0, -34.4, x0 + 2, -34.4); g.lineTo(x1 - 2, -34.4); g.quadraticCurveTo(x1, -34.4, x1, -32); for (let i = 0; i < n; i++) { const x = x1 - i * st; g.quadraticCurveTo(x - st / 2, -29.6, x - st, -31.4); } g.closePath(); });
        if (V.S) { // 側面護耳：沿後腦的頭形垂下的一片毛（蓋住耳朵），剪在頭的輪廓裡
          fill(g, F, () => { g.moveTo(-5.2, -31.4); g.quadraticCurveTo(-6.4, -26.4, -4.2, -23.4); g.quadraticCurveTo(-1.4, -22.4, 0.4, -24.8); g.quadraticCurveTo(1.4, -28, 1, -31.4); g.closePath(); }); // 耳朵（x −1.2）上一片圓的毛，下緣往後收、順著頭形
          line(g, Fd, 0.5, [[-2.6, -29.6], [-2.2, -24.6]]); g.restore(); return; }
        g.restore();
        for (const sx of [-1, 1]) { fill(g, F, () => rr(g, sx * 7.6 - 1.9, -31.6, 3.8, 7.6, 1.9)); line(g, Fd, 0.45, [[sx * 7.6, -29.8], [sx * 7.6, -25.6]]); } } },
    // ---------- 手 ----------
    gloves_fingerless: { zh: "露指手套", slot: "手", from: "cloth_gloves・fingerless", base: setG("hands", { slot: "hands", kind: "gloves", color: "#5a5a6a" }),
      note: "手套（手背是手套色）＋露出一截膚色指頭（拳頭往指尖那一側）＋手腕一圈；正面、背面保留拳頭圈；側面兩隻手都畫",
      hand(g, V) { const sk = V.unit.look.skin, [c, d] = colors(V.unit.gear.hands); g.save(); g.beginPath(); g.arc(0, 0, 2.4, 0, TAU); g.clip(); fill(g, sk, () => g.rect(-3, 0.7, 6, 3)); line(g, dark(sk, 0.25), 0.4, [[-1.8, 0.75], [1.8, 0.75]]);
        if (!V.S) { g.beginPath(); g.rect(-3, 0.7, 6, 3); g.clip(); g.strokeStyle = mix(sk, "#000000", 0.45); g.lineWidth = 0.9; g.beginPath(); g.arc(0, 0, 1.95, 0, TAU); g.stroke(); } // 正面、背面：露出的指頭保留拳頭圈的下半（第 17 版拳頭整圈邊）
        g.restore(); fill(g, d, () => rr(g, -2.3, -2.9, 4.6, 1.3, 0.5)); } },
    gloves_long: { zh: "長皮手套", slot: "手", from: "leather_gloves・long", base: setG("hands", { slot: "hands", kind: "gloves", material: "leather" }),
      note: "皮手套往上包到前臂一半，袖口外翻一圈淺色",
      hand(g, V) { const [c, d] = colors(V.unit.gear.hands); fill(g, c, () => rr(g, -2.2, -6.2, 4.4, 5.4, 1)); fill(g, light(c, 0.22), () => rr(g, -2.6, -6.8, 5.2, 1.6, 0.7)); line(g, d, 0.4, [[-2, -1.2], [2, -1.2]]); } },
    gauntlet_mail: { zh: "鎖鏈護手", slot: "手", from: "gauntlets・mail", base: setG("hands", { slot: "hands", kind: "gauntlets", material: "steel" }),
      note: "板金護手的拳頭換成鎖子點紋＋喇叭形袖口；和板金護手（光面）分得開",
      hand(g, V) { const [c, d] = colors(V.unit.gear.hands); fill(g, c, () => { g.moveTo(-2.1, -1.2); g.lineTo(2.1, -1.2); g.lineTo(3, -5.6); g.lineTo(-3, -5.6); g.closePath(); }); fill(g, d, () => g.rect(-3, -5.8, 6, 0.8));
        g.fillStyle = d; for (const [x, y] of [[-1.4, -3.4], [0.4, -3.4], [-0.5, -2], [1.3, -2], [-1.2, 0.2], [0.6, 0.2], [-0.3, 1.5]]) g.fillRect(x - 0.3, y - 0.3, 0.6, 0.6); } },
    bracer_ring: { zh: "臂環", slot: "手", from: "bracers・ring", base: setG("hands", undefined),
      note: "前臂兩圈細金屬環（銅色＋一點高光）；皮臂甲是寬皮帶，臂環是兩條細亮線",
      hand(g, V) { for (const y of [-5.2, -3.2]) { fill(g, COPPER, () => rr(g, -2.5, y, 5, 1.1, 0.5)); fill(g, light(COPPER, 0.5), () => g.rect(-1.6, y + 0.2, 1.2, 0.35)); } } },
    // ---------- 腳 ----------
    shoes_wrapped: { zh: "綁腿鞋", slot: "腳", from: "shoes・wrapped", base: setG("feet", { slot: "feet", kind: "shoes", material: "cloth" }),
      note: "布鞋＋小腿纏三圈淺色布條（斜的）；側面兩腿的布條連成一條",
      free(g, V) { const xs = V.S ? [-1.6, 1.6] : [-3, 3];
        // 側面兩條腿前後重疊：布條剪在兩腿合起來的形狀裡，一條連到底；正面、背面各腿各自三圈
        const groups = V.S ? [xs] : xs.map((x) => [x]);
        for (const grp of groups) { g.save(); g.beginPath(); for (const x of grp) g.roundRect(x - 2.1, -5.6, 4.2, 4.6, 1.2); g.clip();
          const a = Math.min(...grp) - 2.4, b = Math.max(...grp) + 2.4;
          for (const y of [-5, -3.3, -1.6]) fill(g, "#e2d8bc", () => { g.moveTo(a, y + 0.6); g.lineTo(b, y - 0.6); g.lineTo(b, y + 0.4); g.lineTo(a, y + 1.6); g.closePath(); });
          g.restore(); } } },
    sabaton: { zh: "尖頭鐵靴", slot: "腳", from: "iron_boots・sabaton", base: setG("feet", { slot: "feet", kind: "iron_boots", material: "iron" }),
      note: "鐵靴的鞋頭拉成尖角：側面往前尖出、正面往下尖（朝鏡頭，不低於地面線）、背面看不到尖；鞋面一道分節線",
      free(g, V) { const [c, d] = colors(V.unit.gear.feet);
        if (V.S) { fill(g, c, () => { g.moveTo(2, -3); g.lineTo(5.4, -2.4); g.lineTo(8.6, -0.6); g.lineTo(5.6, 0.6); g.lineTo(1.8, 0.6); g.closePath(); }); line(g, d, 0.5, [[3.4, -2.6], [4, 0.4]]); return; }
        for (const sx of [-1, 1]) { const x = sx * 3; if (V.F) fill(g, c, () => { g.moveTo(x - 3.4, -1.6); g.lineTo(x + 3.4, -1.6); g.lineTo(x + 2.2, -0.3); g.lineTo(x, 0.8); g.lineTo(x - 2.2, -0.3); g.closePath(); }); line(g, d, 0.5, [[x - 3, -1.8], [x + 3, -1.8]]); } } },
    greaves_knee: { zh: "護膝脛甲", slot: "腳", from: "greaves・knee", base: setG("feet", { slot: "feet", kind: "greaves", material: "steel" }),
      note: "脛甲＋膝蓋一片圓護膝（亮一階、中間一道稜）：正面兩片、側面近側一片往前凸、背面不畫",
      free(g, V) { if (V.B) return; const [c, d] = colors(V.unit.gear.feet), k = light(c, 0.2);
        for (const x of V.S ? [2.2] : [-3, 3]) { fill(g, k, () => g.ellipse(x, -5.4, V.S ? 2.4 : 2.6, 2, 0, 0, TAU)); line(g, d, 0.45, V.S ? [[x + 0.4, -6.8], [x + 1.4, -4.2]] : [[x, -7], [x, -3.8]]); } } },
    // ---------- 頸 ----------
    pendant_tag: { zh: "吊牌", slot: "頸", from: "pendant・tag", base: (u) => u,
      note: "細鏈＋一塊圓角鐵牌（有穿孔）；側面照「只在正面的部件轉到前緣」：牌子掛在胸前前緣、露在手臂前方；背面鏈子被後腦擋住（同 qDoll 項鍊）",
      top(g, V) { g.save(); noHead(g, V); if (V.B) { line(g, "#8d969f", 0.6, [[-3.5, -20.8], [0, -20.2], [3.5, -20.8]]); g.restore(); return; }
        if (V.S) { line(g, "#8d969f", 0.55, [[3.4, -21], [5.8, -19.6], [6.6, -18.4]]); fill(g, STEEL, () => rr(g, 5.6, -18.6, 2.2, 3.4, 0.6)); fill(g, "#6a7078", () => g.arc(6.7, -17.8, 0.35, 0, TAU)); g.restore(); return; }
        line(g, "#8d969f", 0.55, [[-4.2, -20.8], [0, -16.4], [4.2, -20.8]]); fill(g, STEEL, () => rr(g, -1.3, -16.6, 2.6, 3.6, 0.7)); fill(g, "#6a7078", () => g.arc(0, -15.8, 0.4, 0, TAU)); g.restore(); } },
    charm_tablet: { zh: "符牌", slot: "頸", from: "charm・tablet", base: (u) => u,
      note: "皮繩＋一塊金色方牌、上面一道紅色符紋（不寫字）；側面掛在胸前前緣、露在手臂前方；背面被後腦擋住",
      top(g, V) { g.save(); noHead(g, V); if (V.B) { line(g, CORD, 0.7, [[-3.5, -20.8], [0, -20.2], [3.5, -20.8]]); g.restore(); return; }
        if (V.S) { line(g, CORD, 0.6, [[3.4, -21], [5.8, -19.6], [6.6, -18.6]]); fill(g, GOLD, () => rr(g, 5.4, -18.8, 2.6, 4, 0.5)); line(g, "#c0392b", 0.5, [[6.7, -18], [6.7, -15.6]]); g.restore(); return; }
        line(g, CORD, 0.6, [[-4.2, -20.8], [0, -16.6], [4.2, -20.8]]); fill(g, GOLD, () => rr(g, -2, -16.8, 4, 4.4, 0.6)); line(g, "#c0392b", 0.5, [[0, -16], [-0.9, -14.6], [0.9, -14.2], [0, -13.1]]); g.restore(); } },
    charm_bone: { zh: "骨符", slot: "頸", from: "charm・bone", base: (u) => u,
      note: "皮繩＋一根彎牙（骨白）＋兩顆木珠；側面牙尖朝下掛在胸前前緣、露在手臂前方；背面被後腦擋住",
      top(g, V) { g.save(); noHead(g, V); if (V.B) { line(g, CORD, 0.7, [[-3.5, -20.8], [0, -20.2], [3.5, -20.8]]); g.restore(); return; }
        const fang = (x, y) => fill(g, BONE, () => { g.moveTo(x - 1.2, y); g.quadraticCurveTo(x - 0.8, y + 3, x + 0.9, y + 4.4); g.quadraticCurveTo(x + 0.3, y + 2.4, x + 1.2, y); g.closePath(); });
        if (V.S) { line(g, CORD, 0.6, [[3.4, -21], [5.8, -19.6], [6.6, -18.6]]); fill(g, "#8a5a32", () => g.arc(6.6, -18.6, 0.75, 0, TAU)); fang(6.8, -18.2); g.restore(); return; }
        line(g, CORD, 0.6, [[-4.2, -20.8], [0, -16.8], [4.2, -20.8]]); fang(0, -17); for (const x of [-2, 2]) fill(g, "#8a5a32", () => g.arc(x, -17.9, 0.75, 0, TAU)); g.restore(); } },
    // ---------- 召喚物用（不在裝備清單）：骷髏的肋骨 ----------
    ribs: { zh: "肋骨", slot: "（召喚物）", from: "body・ribs", base: (u) => u, note: "骷髏戰士：骨色上衣上畫脊椎與三對肋骨；背面脊椎＋肩胛；側面兩根肋骨在背側",
      torso(g, V) { const k = "#8a826e";
        if (V.S) { for (const y of [-18, -15]) line(g, k, 0.8, [[-4.6, y], [-1, y + 0.8]]); line(g, k, 0.9, [[-4.2, -20], [-4.2, -10]]); return; }
        line(g, k, 1, [[0, -20], [0, -10]]);
        if (V.B) { for (const sx of [-1, 1]) line(g, k, 0.8, [[sx * 2, -19], [sx * 5, -17.6], [sx * 3.4, -15]]); return; }
        for (const y of [-18.4, -15.6, -12.8]) for (const sx of [-1, 1]) line(g, k, 0.8, [[sx * 1, y], [sx * 4.6, y + 0.6], [sx * 5.6, y + 1.8]]); } },
  };
  const ORDER = ["scale_mail", "hunter", "plate_full", "coat_cape", "apron", "hood_cowl", "cap_fur", "gloves_fingerless", "gloves_long", "gauntlet_mail", "bracer_ring", "shoes_wrapped", "sabaton", "greaves_knee", "pendant_tag", "charm_tablet", "charm_bone"];
  return { stamp, DEFS, ORDER };
})();
