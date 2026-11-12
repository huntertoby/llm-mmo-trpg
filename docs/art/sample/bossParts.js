// bossParts.js：頭目部位（決定 #152；docs/design/05-戰鬥.md 5.12、18-雲嶺內容.md 18.2.3）——霧鎖真人的部位選單與圖示、部位血條、破壞演出（畫圖 agent，2026-11-12）。
// 紀錄：docs/art/頭目部位.md；樣張頁：boss-parts.html；重拍：tools/boss_parts_shots.py。
//
// 本體一律呼叫現行畫法：QNpc.stamp（qNpc.js；外觀照 QNpc.MONKS 的「霧鎖真人」：月白金邊袍、青披風、右手長劍、左手拂塵、傳說外光），裡面是 QDoll.stamp。
// 部位破壞後的外觀不改別的畫法檔：呼叫 QNpc.stamp 的期間把 window.QDoll 換成一層代理（Proxy），攔下 QDoll.stamp 剛畫好的本體圖層
//   （QNpc 的 A 層，還沒描外框），另外畫一份「部位換成記號色」的對照圖層（拂塵的毛換洋紅、劍刃換綠），兩張相減＝部位實際露出來的像素
//   （被手臂、身體擋住的不算）。破了的部位從本體圖層挖掉、補上斷口；沒破的回傳遮罩給 hover 亮起用。之後 QNpc 照舊合成、描同一圈外框，
//   所以剪短的拂塵、斷掉的劍刃邊緣也有 Q 版外框，不會像貼紙。
// 氣海沒有實體零件：腹部（腳底往上 12.5 的橢圓，和本體圖層取交集）；露出時腹前一團淡青的氣旋，破了換成三道裂痕＋往外漏的霧（QNpc 的 extraD 層：不描外框）。
// 掉落物（剪下的拂塵毛、斷下的劍尖）畫在地上（頭目腳下、本體之前），自己包一圈外框色。
// 遊戲端常數照抄（出處寫在旁邊）：格 48、DOLL_PX、FEET、HP 條（unitSprite.ts hpBar）、陣營環、朝南三角形（facingArrowPoly）、蓄力徽章（badgeLayout.ts）。
// 確定性：沒有亂數；動畫影格用固定的 t（0～1）。
window.BossParts = (() => {
  const TAU = Math.PI * 2, OUT = "#16121a";
  const T = 48; // client/src/battle/geometry.ts TILE_SIZE
  const K = (T / 52) * 1.06; // rendererBase.ts DOLL_PX（paperdoll.ts DOLL_SCALE 1.06）；頭目有外光、不放大（unitSprite.ts humanoidEliteScale）
  const FEET = T * 0.23; // unitSprite.ts FEET
  const HP_W = T * 0.8, HP_Y = T * 0.36, HP_H = 5; // unitSprite.ts hpBar
  const hpColor = (r) => (r > 0.5 ? "#4cd964" : r > 0.25 ? "#ffcc00" : "#ff3b30"); // unitSprite.ts hpColor
  const FOLLOWUP = "#c77dff"; // battle/glossary.ts HIGHLIGHT.followup（蓄力徽章的框色，unitLook.ts statusBadges）
  const BOX = () => window.QNpc.BOX; // { W: 128, H: 112, FOOT: 14 }
  const mk = (w, h) => { const c = document.createElement("canvas"); c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h)); return c; };

  // ---------------- 部位資料（18.2.3 的表；血量照 5.12.2 第 3 點預設 200‰：真人 HP 120 → 每個 24，三個加總 600‰） ----------------
  const BOSS_HP = 120, PART_HP = 24;
  const PARTS = [
    { id: "whisk", zh: "拂塵", reach: "any", reachZh: "任何方向", show: [1, 2, 3], breaks: "封住「霧中換位」", breaksLong: "封住「霧中換位」" },
    { id: "dantian", zh: "氣海", reach: "back", reachZh: "從背後", show: [2, 3], breaks: "歸一不再回血", breaksLong: "停掉歸一階段回合開始的自我治療" },
    { id: "sword", zh: "長劍", reach: "any", reachZh: "任何方向", show: [3], breaks: "近戰變弱、打斷蓄力", breaksLong: "近戰傷害降低，並打斷正在蓄力的強招" },
  ];
  /** 霧鎖真人的外觀（直接拿 QNpc.MONKS 那一筆，不另抄）。 */
  const bossEntry = () => window.QNpc.MONKS.find((m) => m[0] === "霧鎖真人");
  const bossUnit = () => bossEntry()[2];
  const GLOW = () => bossEntry()[3]?.glow ?? "#ffbf3a";

  // ---------------- 本體＋部位遮罩＋破壞後外觀 ----------------
  /** 兩張圖層相減：任一通道或透明度差超過 thr 的像素＝部位（白色、不透明）。 */
  function diffMask(a, b, thr = 40) {
    const w = a.width, h = a.height, da = a.getContext("2d", { willReadFrequently: true }).getImageData(0, 0, w, h).data, db = b.getContext("2d", { willReadFrequently: true }).getImageData(0, 0, w, h).data;
    const out = mk(w, h), oc = out.getContext("2d"), img = oc.createImageData(w, h), d = img.data;
    for (let i = 0; i < da.length; i += 4) {
      const s = Math.abs(da[i] - db[i]) + Math.abs(da[i + 1] - db[i + 1]) + Math.abs(da[i + 2] - db[i + 2]) + Math.abs(da[i + 3] - db[i + 3]);
      if (s > thr) { d[i] = d[i + 1] = d[i + 2] = 255; d[i + 3] = 255; }
    }
    oc.putImageData(img, 0, 0); return out;
  }
  /** 拂塵的毛（qDoll.js QW.whisk 原樣照抄的路徑；只用來畫剪下的那一撮、飛出去的那一撮）。 */
  function tuftPath(c) { c.beginPath(); c.moveTo(-0.9, -7); c.quadraticCurveTo(-5.6, -7.6, -6.4, 1.6); c.quadraticCurveTo(-4.6, 3.2, -3.2, 0.6); c.quadraticCurveTo(-2.4, -4.4, 0.9, -6.6); c.closePath(); }
  /** 拂塵的柄與金箍（qDoll.js QW.whisk 原樣照抄的色與形）。 */
  function whiskHandle(c) { c.fillStyle = "#8a5a2a"; c.beginPath(); c.roundRect(-0.65, -6.6, 1.3, 9.4, 0.6); c.fill(); c.fillStyle = "#e8bb48"; c.beginPath(); c.roundRect(-0.9, -7.2, 1.8, 1.2, 0.5); c.fill(); }
  /** 剪剩的短毛（武器座標：金箍下面三撮 1.6～2.4 長的亂毛）。 */
  function whiskStub(c) {
    c.fillStyle = "#f2f0ea";
    for (const [x0, a, l] of [[-0.6, 2.5, 2.4], [-0.1, 2.1, 1.7], [0.4, 2.8, 2.0]]) { c.save(); c.translate(x0, -6.6); c.rotate(a); c.beginPath(); c.moveTo(-0.45, 0); c.lineTo(0.45, 0); c.lineTo(0.15, l); c.lineTo(-0.2, l * 0.8); c.closePath(); c.fill(); c.restore(); }
    c.fillStyle = "#c8c4b8"; c.beginPath(); c.moveTo(-0.9, -6.2); c.lineTo(0.2, -6.1); c.lineTo(-0.5, -5.2); c.closePath(); c.fill();
  }
  /** 劍刃的斷口（武器座標；qDoll sword(L=16,W=2.6)：刃從 −3 到 −16、尖 −19）。斷口以上整塊挖掉；BRK＝斷口的鋸齒。 */
  const BRK = [[-1.3, -9.9], [-0.7, -9.1], [-0.1, -10.4], [0.5, -9.3], [1.3, -10.2]];
  function aboveBreak(c) { c.beginPath(); c.moveTo(-4, -30); c.lineTo(4, -30); c.lineTo(4, BRK[4][1]); for (let i = BRK.length - 1; i >= 0; i--) c.lineTo(BRK[i][0] + (i === 0 ? -2.7 : i === 4 ? 2.7 : 0), BRK[i][1]); c.closePath(); }
  /** 斷下的劍尖（武器座標，刃的上半＋鋸齒斷口；鋼色照 qDoll 的 steel、亮線照 sword() 的白 45%）。 */
  function swordTip(c) {
    c.fillStyle = "#c3ccd6"; c.beginPath(); c.moveTo(-1.3, -16); c.lineTo(0, -19); c.lineTo(1.3, -16); for (let i = BRK.length - 1; i >= 0; i--) c.lineTo(BRK[i][0], BRK[i][1]); c.closePath(); c.fill();
    c.fillStyle = "rgba(255,255,255,0.45)"; c.fillRect(-0.7, -16, 0.9, 6);
  }
  const BELLY = { x: 0, y: -12.5, rx: 4.2, ry: 3.2 }; // 腹部（本體座標：腳底原點、頭心 −29）
  const SIDE_DX = 0.4; // 側面腹部往前挪多少（第 1 版 1.6；第 2 版氣旋改畫在武器之下，往身體內側挪，露出來的比較多）
  /** 第 2 版（審查可修 4）：側面的劍刃大半在身體輪廓裡，斷口照正面的高度只剩護手上一小截；側面的斷口往刃尖移 2.8（約留原刃 60%），鋸齒才露在輪廓外。 */
  const brkDy = (v) => (v === "side" ? -2.8 : 0);

  /**
   * 畫霧鎖真人（QNpc.stamp）。參數同 QNpc.stamp；o：
   *   dpr、glow（預設傳說外光；false＝不畫）、broken: { whisk, sword, dantian }（破了）、qi（0～1：氣海露出時腹前的氣旋亮度，0＝沒露出）、
   *   crack: { whisk|sword|dantian: 0～1 }（破壞演出第 2 格：部位上的裂紋）、partFlash: { id: 0～1 }（部位白閃）、
   *   masks: true（回傳部位遮罩）。
   * 回傳 { geo: { dx0, dy0, w, h, dpr }（圖層貼到 ctx 的位置；圖層 1 像素＝1/dpr 個 ctx 單位）, masks: { whisk, sword, dantian }（圖層像素）, mats: { whisk, sword }（武器座標 → 圖層像素） }。
   */
  function stamp(ctx, view, cx, cy, size, west = false, o = {}) {
    const QN = window.QNpc, real = window.QDoll, dpr = o.dpr ?? 3, br = o.broken ?? {}, out = { masks: {}, mats: {} };
    const unit = bossUnit();
    let pose = null;
    const hook = (A, q, v, x, y, sz, w, so) => {
      const mats = pose?.wms ?? {};
      out.mats.whisk = mats.whisk?.[0] ?? null; out.mats.sword = mats.sword?.[0] ?? null;
      const key = (patch) => { // 對照圖層：部位換記號色，其他一樣
        const c = mk(A.canvas.width, A.canvas.height), k = c.getContext("2d", { willReadFrequently: true }); k.setTransform(A.getTransform());
        const P = { hands: {}, wms: {}, probe: () => {} }; real.setPose(P);
        try { real.stamp(k, { ...q, gear: { ...q.gear, ...patch } }, v, x, y, sz, w, so); } finally { real.setPose(pose); }
        return c;
      };
      const base = mk(A.canvas.width, A.canvas.height); base.getContext("2d").drawImage(A.canvas, 0, 0);
      const need = o.masks || br.whisk || br.sword || o.partFlash || o.crack;
      if (need && q.gear.off_hand?.kind === "whisk") out.masks.whisk = diffMask(base, key({ off_hand: { ...q.gear.off_hand, color: "#ff00ff" } }));
      if (need && q.gear.main_hand?.kind === "sword") out.masks.sword = diffMask(base, key({ main_hand: { ...q.gear.main_hand, color: "#00ff00" } }));
      // 氣海：腹部橢圓 ∩ 本體
      { const c = mk(A.canvas.width, A.canvas.height), g = c.getContext("2d"); frameOf(g, sz, so?.dpr ?? dpr, w && v === "side"); g.fillStyle = "#fff"; g.beginPath(); g.ellipse(BELLY.x + (v === "side" ? SIDE_DX : 0), BELLY.y, BELLY.rx, BELLY.ry, 0, 0, TAU); g.fill();
        g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = "destination-in"; g.drawImage(base, 0, 0); out.masks.dantian = c; }
      // 第 2 版（審查可修 3）：側面的長劍斜在腹前，氣旋要畫在武器（刃、護手、柄、握劍的手）之下。武器遮罩＝本體減掉「不拿主手武器」的那一份
      //   （拿掉武器後手的位置也會變，所以握劍的手一起算進來），往外放 0.5 模型 px；extraD 畫完氣旋後把這一塊挖掉。
      if (v === "side" && q.gear.main_hand) { const wm = diffMask(base, key({ main_hand: null }), 24); out.wmask = window.QNpc.dilate(wm, 0.5 * (so?.dpr ?? dpr) * sz); }
      // 破了的部位：不是挖洞（第 1 稿挖掉後露出底下的外框色，變成一塊黑影），而是重畫一份「部位透明」的本體——拂塵的毛、劍刃都只有一筆
      //   it.color 的填色，換成透明就等於沒有那一塊，後面的袍子、披風照常畫出來。
      const NONE = "rgba(0,0,0,0)", patch = {};
      if (br.whisk && q.gear.off_hand?.kind === "whisk") {
        patch.off_hand = { ...q.gear.off_hand, color: NONE };
        const N = key(patch); A.save(); A.setTransform(1, 0, 0, 1, 0, 0); A.clearRect(0, 0, A.canvas.width, A.canvas.height); A.drawImage(N, 0, 0); A.restore();
        if (out.mats.whisk) { A.save(); A.setTransform(out.mats.whisk); whiskStub(A); A.restore(); } // 剪剩的短毛（之後 QNpc 一起描外框）
      }
      // 長劍破：只換「斷口以上、刃露出來」的那一塊（E）。刃上那條白 45% 亮線不吃 it.color，透明刃的那一份裡亮線還在：
      //   E 裡亮線的位置照「白 45% 疊上去」的公式反算回底下的顏色（不透明就還原袍子色；半透明就是背景，透明度一起還原）。
      if (br.sword && q.gear.main_hand?.kind === "sword" && out.masks.sword && out.mats.sword) {
        patch.main_hand = { ...q.gear.main_hand, color: NONE };
        const N = key(patch), cw = A.canvas.width, ch = A.canvas.height;
        const E = mk(cw, ch), e = E.getContext("2d", { willReadFrequently: true }); e.drawImage(window.QNpc.dilate(out.masks.sword, 1.2 * (so?.dpr ?? dpr) * sz), 0, 0); e.globalCompositeOperation = "destination-in"; e.setTransform(out.mats.sword); e.translate(0, brkDy(v)); e.fillStyle = "#fff"; aboveBreak(e); e.fill();
        const Sg = mk(cw, ch), s = Sg.getContext("2d", { willReadFrequently: true }); s.setTransform(out.mats.sword); s.fillStyle = "#fff"; s.fillRect(-1.0, -16.3, 1.5, 12.6); // sword() 的亮線 rect(−W/2＋0.6, −L, 0.9, L−4)，往外放寬一點
        const da = A.getImageData(0, 0, cw, ch), dn = N.getContext("2d", { willReadFrequently: true }).getImageData(0, 0, cw, ch).data, de = e.getImageData(0, 0, cw, ch).data, ds = s.getImageData(0, 0, cw, ch).data, d = da.data;
        for (let i = 0; i < d.length; i += 4) {
          if (de[i + 3] < 128) continue;
          let r = dn[i], g = dn[i + 1], b = dn[i + 2], a = dn[i + 3] / 255;
          if (a < 0.97) a = 0; /* 斷口以上只留不透明的本體（袍子、手臂）；半透明的都是刃與亮線疊在背景上的 */
          else if (ds[i + 3] > 128) { const ab = Math.max(0, (a - 0.45) / 0.55); if (ab < 0.08) { a = 0; } else { const un = (v) => Math.max(0, Math.min(255, (v * a - 255 * 0.45) / (0.55 * ab))); r = un(r); g = un(g); b = un(b); a = ab; } }
          if (Math.abs(r - 22) + Math.abs(g - 18) + Math.abs(b - 26) < 70) a = 0; // qDoll 在主手武器底下墊的一圈外框色：刃拿掉後它還在，一起拿掉（斷口以上不會有別的外框色零件）
          d[i] = r; d[i + 1] = g; d[i + 2] = b; d[i + 3] = Math.round(a * 255);
        }
        A.save(); A.setTransform(1, 0, 0, 1, 0, 0); A.putImageData(da, 0, 0); A.restore();
      }
      // 演出用：部位上的裂紋（亮金白細線，畫在本體圖層上、會被外框包住）
      for (const id of ["whisk", "sword"]) {
        const t = o.crack?.[id], m = out.mats[id]; if (!t || !m) continue;
        A.save(); A.setTransform(m); A.strokeStyle = "#fff6c8"; A.lineWidth = 0.55; A.lineCap = "round"; A.beginPath();
        if (id === "sword") { A.moveTo(-1.2, -10.6); A.lineTo(-0.2, -9.6); A.lineTo(0.5, -10.4); A.lineTo(1.2, -9.8); if (t > 0.5) { A.moveTo(-0.1, -10); A.lineTo(0.3, -12.4); } }
        else { A.moveTo(-0.9, -6.8); A.lineTo(-2.4, -5.8); A.lineTo(-3.2, -4.2); if (t > 0.5) { A.moveTo(-1.6, -6.4); A.lineTo(-3.8, -6.4); } }
        A.stroke(); A.restore();
      }
    };
    const drawD = (c, v, q) => { // 氣海：露出時的氣旋（不描外框）；破了換裂痕與漏出的霧
      const bx = BELLY.x + (v === "side" ? SIDE_DX : 0), by = BELLY.y;
      if (br.dantian) {
        c.save(); c.globalAlpha = 0.95; c.strokeStyle = "#1f3a38"; c.lineWidth = 0.95; c.lineCap = "round"; c.beginPath();
        for (const [a, l] of [[-0.6, 3.6], [1.9, 3.0], [3.6, 3.3]]) { c.moveTo(bx, by); c.lineTo(bx + Math.cos(a) * l * 0.55, by + Math.sin(a) * l * 0.55 + 0.4); c.lineTo(bx + Math.cos(a + 0.25) * l, by + Math.sin(a + 0.25) * l); }
        c.stroke(); c.restore();
        c.save(); c.fillStyle = "#e6ecec"; for (const [dx, dy, r, al] of [[-5.6, -1.4, 2.4, 0.7], [-8.0, -3.6, 1.8, 0.5], [5.8, -0.6, 2.2, 0.65], [8.2, -2.8, 1.6, 0.45]]) { c.globalAlpha = al; c.beginPath(); c.ellipse(bx + dx, by + dy, r, r * 0.7, 0, 0, TAU); c.fill(); } c.restore();
      } else if (o.qi > 0) {
        const a = o.qi;
        c.save(); const g = c.createRadialGradient(bx, by, 0, bx, by, 5.2); g.addColorStop(0, `rgba(220,255,250,${0.9 * a})`); g.addColorStop(0.45, `rgba(110,224,208,${0.65 * a})`); g.addColorStop(1, "rgba(110,224,208,0)");
        c.fillStyle = g; c.beginPath(); c.arc(bx, by, 5.2, 0, TAU); c.fill();
        c.strokeStyle = `rgba(240,255,252,${0.85 * a})`; c.lineWidth = 0.55; c.lineCap = "round"; c.beginPath(); c.arc(bx, by, 2.4, -0.4, 2.2); c.stroke(); c.beginPath(); c.arc(bx, by, 1.2, 2.6, 5.2); c.stroke(); c.restore();
      }
      if (o.crack?.dantian) { const t = o.crack.dantian; c.save(); c.strokeStyle = "#f2fffc"; c.lineWidth = 0.6; c.lineCap = "round"; c.beginPath(); for (const a of [-0.6, 1.9, 3.6]) { c.moveTo(bx, by); c.lineTo(bx + Math.cos(a) * 3.4 * t, by + Math.sin(a) * 3.4 * t); } c.stroke(); c.restore(); }
    };
    // 側面：氣旋、裂痕畫在另一張，挖掉武器遮罩再貼上（＝畫在武器之下；第 2 版，審查可修 3）
    const extraD = (c, v, q) => {
      if (v !== "side" || !out.wmask) return drawD(c, v, q);
      const tmp = mk(c.canvas.width, c.canvas.height), t = tmp.getContext("2d"); t.setTransform(c.getTransform()); drawD(t, v, q);
      t.setTransform(1, 0, 0, 1, 0, 0); t.globalCompositeOperation = "destination-out"; t.drawImage(out.wmask, 0, 0);
      c.save(); c.setTransform(1, 0, 0, 1, 0, 0); c.drawImage(tmp, 0, 0); c.restore();
    };
    const proxy = new Proxy(real, {
      get(t, p) {
        if (p === "setPose") return (x) => { if (x) pose = x; t.setPose(x); };
        if (p === "stamp") return (A, q, v, x, y, sz, w, so) => { const r = t.stamp(A, q, v, x, y, sz, w, so); if (A !== ctx) hook(A, q, v, x, y, sz, w, so); return r; };
        return Reflect.get(t, p);
      },
    });
    window.QDoll = proxy;
    try { QN.stamp(ctx, unit, view, cx, cy, size, west, { dpr, glow: o.glow === false ? undefined : o.glow ?? GLOW(), extraD }); } finally { window.QDoll = real; }
    const { W, H, FOOT } = BOX();
    out.geo = { dx0: cx - (W / 2) * size, dy0: cy - (H - FOOT) * size, w: W * size, h: H * size, dpr: dpr };
    // 部位白閃（演出第 1 格）：遮罩塗白蓋上去
    for (const [id, k] of Object.entries(o.partFlash ?? {})) { const m = out.masks[id]; if (!m || !(k > 0)) continue; ctx.save(); ctx.globalAlpha = k; ctx.drawImage(tint(m, "#ffffff"), out.geo.dx0, out.geo.dy0, out.geo.w, out.geo.h); ctx.restore(); }
    return out;
  }
  /** QNpc 的 frame()（照抄 qNpc.js stamp 裡的 frame：腳底中心、朝西鏡像；霧鎖真人沒有 build／frame）。 */
  function frameOf(c, size, dpr, WW) { const { W, H, FOOT } = BOX(); c.setTransform(1, 0, 0, 1, 0, 0); c.scale(dpr * size, dpr * size); c.translate(W / 2, H - FOOT); if (WW) c.scale(-1, 1); }
  function tint(src, col) { const c = mk(src.width, src.height), x = c.getContext("2d"); x.drawImage(src, 0, 0); x.globalCompositeOperation = "source-in"; x.fillStyle = col; x.fillRect(0, 0, c.width, c.height); return c; }
  /** 部位的遮罩加上拂塵的柄（毛之外，柄也算拂塵：hover 時整支亮起）。 */
  function partMask(r, id) {
    const m = r.masks[id]; if (!m) return null;
    if (id !== "whisk" || !r.mats.whisk) return m;
    const c = mk(m.width, m.height), x = c.getContext("2d"); x.drawImage(m, 0, 0); x.setTransform(r.mats.whisk); whiskHandle(x); x.setTransform(1, 0, 0, 1, 0, 0); x.globalCompositeOperation = "source-in"; x.fillStyle = "#fff"; x.fillRect(0, 0, c.width, c.height); return c;
  }

  // ---------------- hover：部位亮起（描邊＋淡色填） ----------------
  /** 預設：亮青白（#a8f4ff）＋外框色襯邊、部位上 35% 同色。選定理由見紀錄（和移動格的淺藍分得開：只畫在身體上、而且有深色襯邊）。 */
  const HOVER = { color: "#a8f4ff", ink: OUT, width: 1.4, inkW: 0.9, fill: 0.35 };
  /** 在 ctx（模型座標）上把部位亮起來。w、inkW 是模型單位（跟著地圖縮放）。 */
  function glow(ctx, r, id, opt = {}) {
    const o = { ...HOVER, ...opt };
    if (id === "dantian" && !opt.disc) return glowQi(ctx, r, o);
    const m = partMask(r, id); if (!m) return;
    const g = r.geo, px = g.dpr / 1; // 圖層每個 ctx 單位幾個像素
    const QN = window.QNpc, copy = (c) => { const d = mk(c.width, c.height); d.getContext("2d").drawImage(c, 0, 0); return d; };
    const outer = copy(QN.dilate(m, (o.width + o.inkW) * px)), mid = copy(QN.dilate(m, o.width * px));
    const lay = mk(m.width, m.height), l = lay.getContext("2d");
    l.drawImage(tint(outer, o.ink), 0, 0); l.drawImage(tint(mid, o.color), 0, 0);
    l.globalCompositeOperation = "destination-out"; l.drawImage(m, 0, 0); l.globalCompositeOperation = "source-over";
    l.globalAlpha = o.fill; l.drawImage(tint(m, o.color), 0, 0); l.globalAlpha = 1;
    ctx.drawImage(lay, g.dx0, g.dy0, g.w, g.h);
  }
  /** 第 2 版（審查可修 2：第 1 版描整塊腹部，正面像一面圓鏡、背面像圓盾）：氣海的亮起＝邊緣柔和的光暈（不描外框）＋兩道逗號形的亮青白氣痕
   *  （外框色襯在底下，和其他部位的亮起同一種「亮青白＋深色襯邊」的語言）。不是閉合的圓。 */
  function glowQi(ctx, r, o) {
    const c = centerOf(r, "dantian"); if (!c) return;
    const s = r.geo.w / BOX().W; // 模型縮放（1 格人物＝K）
    ctx.save();
    const g = ctx.createRadialGradient(c.x, c.y, 0, c.x, c.y, 7.5 * s); g.addColorStop(0, "rgba(232,252,255,0.75)"); g.addColorStop(0.4, "rgba(168,244,255,0.45)"); g.addColorStop(1, "rgba(168,244,255,0)");
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(c.x, c.y, 7.5 * s, 0, TAU); ctx.fill();
    ctx.lineCap = "round";
    const arcs = (k) => { for (const a0 of [-0.5, Math.PI - 0.5]) { ctx.beginPath(); ctx.arc(c.x, c.y, 3.6 * s, a0, a0 + 1.9); ctx.stroke(); ctx.beginPath(); ctx.moveTo(c.x + Math.cos(a0 + 1.9) * 3.6 * s, c.y + Math.sin(a0 + 1.9) * 3.6 * s); ctx.quadraticCurveTo(c.x + Math.cos(a0 + 2.5) * 2.4 * s, c.y + Math.sin(a0 + 2.5) * 2.4 * s, c.x + Math.cos(a0 + 2.9) * 1.2 * s, c.y + Math.sin(a0 + 2.9) * 1.2 * s); ctx.stroke(); } };
    ctx.strokeStyle = o.ink; ctx.lineWidth = (o.width + o.inkW * 2) * s; arcs();
    ctx.strokeStyle = o.color; ctx.lineWidth = o.width * s; arcs();
    ctx.restore();
  }
  /** 部位的中心（模型座標）：演出的星、飛出去的碎塊從這裡出發。 */
  function centerOf(r, id) {
    const g = r.geo, toM = (p) => ({ x: g.dx0 + p.x / g.dpr, y: g.dy0 + p.y / g.dpr });
    if (id === "whisk" && r.mats.whisk) return toM(r.mats.whisk.transformPoint(new DOMPoint(-3, -3)));
    if (id === "sword" && r.mats.sword) return toM(r.mats.sword.transformPoint(new DOMPoint(0, -12)));
    const m = r.masks.dantian; if (!m) return null;
    const d = m.getContext("2d", { willReadFrequently: true }).getImageData(0, 0, m.width, m.height).data; let sx = 0, sy = 0, n = 0;
    for (let i = 3; i < d.length; i += 4) if (d[i] > 128) { const p = (i - 3) / 4; sx += p % m.width; sy += Math.floor(p / m.width); n++; }
    return n ? toM({ x: sx / n, y: sy / n }) : null;
  }
  /** 武器座標 → 模型座標的矩陣（畫飛出去的碎塊用）。 */
  function weaponToModel(r, id) { const g = r.geo, m = r.mats[id]; if (!m) return null; return new DOMMatrix().translate(g.dx0, g.dy0).scale(1 / g.dpr, 1 / g.dpr).multiply(m); }

  // ---------------- 掉落物（地上；本體之前畫） ----------------
  /** 自己包一圈外框色：先畫外框色的粗描邊，再填色（Q 版「剪影往外長一圈」的簡化：形狀都是凸的小塊）。 */
  function outlined(ctx, path, fillFn, w) { ctx.save(); ctx.strokeStyle = OUT; ctx.lineWidth = w * 2; ctx.lineJoin = "round"; path(ctx); ctx.stroke(); ctx.restore(); fillFn(ctx); }
  /** 地上剪下的拂塵毛：feet＝頭目腳底（模型座標），side＝往哪邊（1 右、−1 左），s＝模型縮放（K）。a＝透明度（演出淡入）。 */
  /** 地上的一撮白毛（第 2 稿：第 1 稿把手上的毛原樣轉平，彎成一彎、讀成獠牙）：橫躺的一束，左端是剪口（灰）、右端散成三綹。 */
  const clumpPath = (c) => { c.beginPath(); c.moveTo(-5.8, -1.3); c.bezierCurveTo(-1.6, -3.4, 3.6, -3.4, 6.6, -1.9); c.lineTo(5.0, -0.9); c.lineTo(7.0, 0.1); c.lineTo(5.0, 0.9); c.lineTo(6.4, 2.1); c.bezierCurveTo(2.6, 2.7, -1.6, 2.4, -5.8, 1.5); c.closePath(); };
  function fallenTuft(ctx, fx, fy, s = K, a = 1, rot = 0) {
    ctx.save(); ctx.globalAlpha = a; ctx.translate(fx, fy); ctx.scale(s, s); ctx.rotate(rot * 0); if (rot < 0) ctx.scale(-1, 1);
    outlined(ctx, clumpPath, (c) => {
      c.fillStyle = "#f2f0ea"; clumpPath(c); c.fill();
      c.save(); clumpPath(c); c.clip(); c.fillStyle = "#c8c4b8"; c.fillRect(-7, 0.6, 15, 3); c.fillStyle = "#ffffff"; c.fillRect(-3, -2.5, 6.5, 0.8);
      c.strokeStyle = "#c8c4b8"; c.lineWidth = 0.45; c.beginPath(); c.moveTo(-3, -0.4); c.quadraticCurveTo(1.6, -0.9, 5, -0.3); c.stroke(); c.restore();
      c.fillStyle = "#a8a296"; c.beginPath(); c.ellipse(-5.6, 0.1, 0.8, 1.4, 0, 0, TAU); c.fill(); // 剪口
    }, 1.1);
    ctx.restore();
  }
  /** 地上斷下的劍尖。 */
  function fallenTip(ctx, fx, fy, s = K, a = 1, rot = 1.25) {
    ctx.save(); ctx.globalAlpha = a; ctx.translate(fx, fy); ctx.scale(s, s); ctx.rotate(rot); ctx.translate(0, 14.5);
    outlined(ctx, (c) => { c.beginPath(); c.moveTo(-1.3, -16); c.lineTo(0, -19); c.lineTo(1.3, -16); for (let i = BRK.length - 1; i >= 0; i--) c.lineTo(BRK[i][0], BRK[i][1]); c.closePath(); }, swordTip, 1.1);
    ctx.restore();
  }
  /** 頭目腳下的掉落物（照 broken；正面時拂塵在畫面右邊（左手）、劍在左邊）。 */
  function debris(ctx, fx, fy, broken = {}, west = false, s = K) {
    const sd = west ? -1 : 1;
    if (broken.sword) fallenTip(ctx, fx - 10.5 * sd, fy + 2.6, s, 1, west ? -1.25 : 1.25);
    if (broken.whisk) fallenTuft(ctx, fx + 11 * sd, fy + 1.4, s, 1, west ? -1.62 : 1.62);
  }

  // ---------------- 部位血條（HP 條正下方，共用 HP 條的黑底） ----------------
  /** 部位條的排法（模型像素、相對格子中心）。boardScale＝地圖縮放（畫面 px／模型 px）：條高在畫面上至少 MIN_BAR_PX、打叉至少 MIN_X_PX（照 minMark.ts 反向放大的原則）。 */
  const HIDDEN_BAR = "#0e0e14", EMPTY_BAR = "#4a4252", SHIELD = "#9fd8ff";
  const STRIP = { gapTop: 0.8, h: 2.6, pad: 0.8, gap: 1.6, xSize: 5.6, MIN_BAR_PX: 2, MIN_X_PX: 4 };
  function stripLayout(n, boardScale) {
    const h = Math.max(STRIP.h, STRIP.MIN_BAR_PX / boardScale), xs = Math.max(STRIP.xSize, STRIP.MIN_X_PX / boardScale);
    const inner = HP_W - 2 * STRIP.pad, w = (inner - (n - 1) * STRIP.gap) / n, top = HP_Y + HP_H + STRIP.gapTop;
    return { h, xs, w, top, bottom: top + h + STRIP.pad, x0: -HP_W / 2 + STRIP.pad };
  }
  /** 一條部位條。st：{ state: "ok"|"hidden"|"broken", hp, max }。 */
  function partBar(ctx, x, y, w, h, st, xs, k = 1) {
    // 第 2 版（審查可修 7）：未露出＝幾乎黑、不帶點（第 1 版深灰＋三點，800 真 1 倍和「破壞中剩一點」都是一條深灰）；
    //   破壞中的空槽底色提亮成灰紫 #4a4252，所以「剩一點」＝灰紫條＋一小段米白，「未露出」＝這一格沒有條。
    if (st.state === "hidden") { ctx.fillStyle = HIDDEN_BAR; ctx.fillRect(x, y, w, h); return; }
    if (st.state === "broken") {
      ctx.fillStyle = "#5a1a1a"; ctx.fillRect(x, y, w, h);
      const cx = x + w / 2, cy = y + h / 2, r = xs / 2; ctx.save(); ctx.lineCap = "round";
      for (const [col, lw] of [[OUT, 1.5 * k + 1.2 * k], ["#ff5a4a", 1.5 * k]]) { ctx.strokeStyle = col; ctx.lineWidth = lw; ctx.beginPath(); ctx.moveTo(cx - r, cy - r); ctx.lineTo(cx + r, cy + r); ctx.moveTo(cx + r, cy - r); ctx.lineTo(cx - r, cy + r); ctx.stroke(); }
      ctx.restore(); return;
    }
    ctx.fillStyle = EMPTY_BAR; ctx.fillRect(x, y, w, h);
    ctx.fillStyle = "#f2e6c8"; ctx.fillRect(x, y, w * Math.max(0, Math.min(1, st.hp / st.max)), h);
  }
  /** 頭目的 HUD（模型座標，ctx 已經是地圖座標）：HP 條、部位條、狀態列、朝南三角形、蓄力徽章。u：{ x, y, hp（0～1）, parts:[st], status:[id], facing, charge, hidden }。 */
  function hud(ctx, u, boardScale, opt = {}) {
    const cx = (u.x + 0.5) * T, cy = (u.y + 0.5) * T, L = stripLayout(u.parts?.length || 3, boardScale);
    const k = Math.max(1, 1 / boardScale / 1.31); // 打叉的線寬：1600 寬（1.31）時 1.5 模型 px，地圖越小越粗
    // 狀態列（unitSprite.ts：圖示 11、下緣離 HP 條 4；地圖縮小時圖案至少 10px（minMark.ts MIN_STATUS_GLYPH_PX），排不下的收成「+N」）
    // 第 2 版（審查 M3）：部位選單打開時，頭目身上的狀態列與蓄力徽章淡到 opt.dim（40%），部位亮起、氣旋、裂痕從底下透出來；HP 條、部位條不淡
    const dim = opt.dim ?? 1;
    ctx.save(); ctx.globalAlpha = dim;
    if (u.status?.length && window.QStatusLive) {
      const px = Math.max(11, 12 / boardScale), fit = boardScale < 0.7 ? 1 : 3, n = Math.min(fit, u.status.length), gap = 1, x0 = cx - (n * px + (n - 1) * gap) / 2, yb = cy + HP_Y - 4;
      u.status.slice(0, n).forEach((id, i) => { let cv = null; try { cv = window.QStatusLive.statusIconCanvas(id, 11); } catch (e) { cv = null; } if (cv) ctx.drawImage(cv, x0 + i * (px + gap), yb - px, px, px); });
      if (u.status.length > n) { ctx.save(); ctx.font = `bold ${10 / boardScale}px 'Noto Sans TC','Microsoft JhengHei',sans-serif`; ctx.textBaseline = "bottom"; ctx.lineWidth = 3 / boardScale; ctx.strokeStyle = "#000"; ctx.fillStyle = "#fff"; const s = "+" + (u.status.length - n); ctx.strokeText(s, x0 + n * (px + gap), yb); ctx.fillText(s, x0 + n * (px + gap), yb); ctx.restore(); }
    }
    if (u.charge != null) chargeBadge(ctx, cx - 0.37 * T, cy - 0.2 * T, u.charge, boardScale);
    ctx.restore();
    // HP 條（黑底往下延伸，包住部位條）
    const y = cy + HP_Y, x = cx - HP_W / 2, withStrip = !!u.parts?.length && opt.strip !== false;
    ctx.fillStyle = "#000"; ctx.fillRect(x, y, HP_W, (withStrip ? L.bottom - HP_Y : HP_H));
    if (u.hidden) { ctx.fillStyle = "#b4b4c0"; ctx.fillRect(x + 1, y + 1, HP_W - 2, 3); }
    else {
      ctx.fillStyle = hpColor(u.hp); ctx.fillRect(x, y, HP_W * u.hp, HP_H);
      // 護盾條（unitSprite.ts hpBar，6F-22b：HP 條上面 2、外面一圈 1 黑框）；部位條照舊在 HP 條下面（第 2 版補圖，審查可修 5）
      if (u.shield > 0) { ctx.fillStyle = "#000"; ctx.fillRect(x - 1, y - 3 - 1, HP_W * u.shield + 2, 4); ctx.fillStyle = SHIELD; ctx.fillRect(x, y - 3, HP_W * u.shield, 2); }
    }
    if (withStrip) u.parts.forEach((st, i) => partBar(ctx, cx + L.x0 + i * (L.w + STRIP.gap), cy + L.top, L.w, L.h, u.hidden ? { state: "hidden" } : st, L.xs, k));
    // 朝南三角形：上緣離最下面的條 0.5（6F-21 的規則照搬：有部位條時往下移到部位條下面）
    if (u.facing === "south" && opt.arrow !== false) {
      const top = cy + (withStrip ? L.bottom : HP_Y + HP_H) + 0.5 + 0.5, aw = 5;
      ctx.save(); ctx.beginPath(); ctx.moveTo(cx - aw, top); ctx.lineTo(cx + aw, top); ctx.lineTo(cx, top + aw); ctx.closePath(); ctx.fillStyle = "#fff"; ctx.fill(); ctx.lineWidth = 1; ctx.strokeStyle = "#000"; ctx.stroke(); ctx.restore();
    }
    return L;
  }
  /** 蓄力徽章（badgeLayout.ts：圓半徑 10、線 2、圖示 16、數字 10 粗＋描邊 3、在圖示右下 8；圖示與數字在畫面上至少 10px）。 */
  function chargeBadge(ctx, x, y, n, boardScale) {
    const ki = Math.max(1, 10 / (16 * boardScale)), kn = Math.max(1, 10 / (10 * boardScale)), r = 10 * ki;
    ctx.save(); ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fillStyle = "rgba(0,0,0,0.8)"; ctx.fill(); ctx.lineWidth = 2 * ki; ctx.strokeStyle = FOLLOWUP; ctx.stroke();
    let cv = null; try { cv = window.QStatusLive.statusIconCanvas("charging", 16); } catch (e) { cv = null; }
    if (cv) ctx.drawImage(cv, x - 8 * ki, y - 8 * ki, 16 * ki, 16 * ki);
    ctx.font = `bold ${10 * kn}px 'Noto Sans TC','Microsoft JhengHei',sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.lineWidth = 3 * kn; ctx.strokeStyle = "#000"; ctx.strokeText(String(n), x + 8 * ki, y + 8 * ki); ctx.fillStyle = "#fff"; ctx.fillText(String(n), x + 8 * ki, y + 8 * ki); ctx.restore();
  }

  // ---------------- 部位小圖示（Q 版小圖示規則；圖樣畫在 ±10 單位，和第 4 批部件同一個座標，給 QIcons.render） ----------------
  const CREAM = "#f2e6c8";
  /** 人形（照抄 qIconsParts.js 的 bust：單色剪影、圓頭加圓肩的半身；沒有匯出）。 */
  const bust = (c, col, x, y, k = 1) => { c.fillStyle = col; c.beginPath(); c.arc(x, y - 4.6 * k, 3.7 * k, 0, TAU); c.fill(); c.beginPath(); c.moveTo(x - 6.2 * k, y + 7 * k); c.quadraticCurveTo(x - 6.2 * k, y - 0.4 * k, x, y - 0.4 * k); c.quadraticCurveTo(x + 6.2 * k, y - 0.4 * k, x + 6.2 * k, y + 7 * k); c.closePath(); c.fill(); };
  /** 拂塵：柄與金箍照人物手上那一支（qDoll QW.whisk：柄 #8a5a2a、金箍 #e8bb48、白毛 #f2f0ea），柄換亮一階（規則 6，同第 4 批亮色劍的皮柄 #a8703e）；
   *  45° 斜放、柄在左下，毛從金箍往右下垂成一大束（比人物手上的長、寬：圖示要靠這束毛認）。毛的暗面在下緣、亮面一條在上緣。 */
  /** 第 2 版（審查可修 1：第 1 版毛束短粗、下緣平，剪影像「ㄏ」、讀成拖把）：柄短、斜在左上；毛從金箍往下甩成一條 S 形的長流線，
   *  根部寬、尾端收尖，尾端分出一綹細毛（國畫、戲曲裡的拂塵）。不改成直立（美術 PM 決定）。 */
  function whiskGlyph(c, o) {
    const Q = window.QIcons.H;
    const F = [-3.4, -5.0], Hd = [-9.8, -11.2]; // 金箍、柄尾
    const B = [[-2.6, -4.0], [11.2, -4.2], [-9.2, 4.6], [6.4, 11.6]]; // 毛的中心線（三次貝茲）
    const at = (t) => { const u = 1 - t, k = [u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t]; return [0, 1].map((j) => B.reduce((s, p, i) => s + p[j] * k[i], 0)); };
    const N = 28, L = [], R = [];
    for (let i = 0; i <= N; i++) {
      const t = i / N, p = at(t), q = at(Math.min(1, t + 0.01)), p0 = at(Math.max(0, t - 0.01)), dx = q[0] - p0[0], dy = q[1] - p0[1], l = Math.hypot(dx, dy) || 1;
      const w = 3.7 * Math.pow(1 - t, 0.7) + 0.2, nx = -dy / l, ny = dx / l;
      L.push([p[0] + nx * w, p[1] + ny * w]); R.push([p[0] - nx * w, p[1] - ny * w]);
    }
    const plume = (q) => { q.beginPath(); L.forEach(([x, y], i) => (i ? q.lineTo(x, y) : q.moveTo(x, y))); for (let i = R.length - 1; i >= 0; i--) q.lineTo(R[i][0], R[i][1]); q.closePath(); };
    const strand = (q) => { const s = at(0.62), e = [s[0] - 4.4, s[1] + 5.2]; q.beginPath(); q.moveTo(s[0] - 1.2, s[1] - 1.0); q.quadraticCurveTo(s[0] - 3.6, s[1] + 1.8, e[0], e[1]); q.quadraticCurveTo(s[0] - 1.8, s[1] + 2.6, s[0] + 0.6, s[1] + 0.8); q.closePath(); };
    c.fillStyle = "#f2f0ea"; plume(c); c.fill(); strand(c); c.fill();
    if (!o.tiny) {
      c.save(); plume(c); c.clip();
      c.strokeStyle = "#c8c4b8"; c.lineWidth = 2.4; c.lineJoin = "round"; c.beginPath(); R.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y))); c.stroke(); // 暗面：沿右緣
      c.strokeStyle = "#ffffff"; c.lineWidth = 1.5; c.beginPath(); L.slice(2, 15).forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y))); c.stroke(); // 亮面：左上緣
      c.strokeStyle = "#b8b2a4"; c.lineWidth = o.small ? 0.9 : 0.7; c.lineCap = "round"; c.beginPath(); for (let i = 3; i <= 22; i++) { const p = at(i / N); i === 3 ? c.moveTo(p[0], p[1]) : c.lineTo(p[0], p[1]); } c.stroke(); // 分綹線
      c.restore();
      c.fillStyle = "#c8c4b8"; strand(c); c.fill();
    }
    // 柄：金箍往左上（握柄端在左上），亮一階的木色
    Q.ln(c, "#a8703e", 2.7, [F, Hd]);
    if (!o.small) Q.ln(c, "rgba(255,255,255,0.45)", 0.8, [[F[0] - 1.4, F[1] - 2.0], [Hd[0] + 0.6, Hd[1] + 0.2]]);
    c.save(); c.translate(F[0], F[1]); c.rotate(Math.atan2(Hd[1] - F[1], Hd[0] - F[0]) + Math.PI / 2); Q.rr(c, "#e8bb48", -2.4, -1.5, 4.8, 3.2, 1.3); if (!o.tiny) Q.rr(c, "#f6d878", -1.8, -1.1, 1.8, 1.1, 0.5); c.restore();
  }
  /** 第 1 版的拂塵（審查前）；只給對照列。 */
  function whiskGlyphV1(c, o) {
    const Q = window.QIcons.H;
    // 第 2 稿（第 1 稿的毛是一條窄弧，讀成羽毛筆）：柄斜放（左下→右上），毛從右上的金箍「往下垂」成一大束馬尾，下緣分成三綹；
    // 毛比柄寬兩倍以上，剪影是「細棍＋一大把下垂的毛」，不是羽毛（羽毛是對稱的葉形、沿著桿長）。
    const tuft = (q) => { q.beginPath(); q.moveTo(0.8, -8.8); q.bezierCurveTo(6.4, -9.6, 10.4, -5, 10.6, 0.4); q.lineTo(11, 10.2); q.quadraticCurveTo(10.2, 11.2, 9.4, 9.8); q.quadraticCurveTo(8.6, 11.4, 7.6, 10.2); q.quadraticCurveTo(6.6, 11.4, 5.6, 9.8); q.quadraticCurveTo(4.6, 10.8, 3.6, 9.4); q.bezierCurveTo(3.8, 4, 3.0, -1.8, 0.2, -5.4); q.closePath(); };
    c.fillStyle = "#f2f0ea"; tuft(c); c.fill();
    if (!o.tiny) {
      c.save(); tuft(c); c.clip();
      c.fillStyle = "#c8c4b8"; c.beginPath(); c.moveTo(7.6, -5); c.bezierCurveTo(10, -1, 10.4, 4, 10.4, 11); c.lineTo(12, 11); c.lineTo(12, -6); c.closePath(); c.fill(); // 暗面：右緣
      c.strokeStyle = "#b8b2a4"; c.lineWidth = o.small ? 1.1 : 0.8; c.lineCap = "round"; c.beginPath(); c.moveTo(5.0, -4.6); c.quadraticCurveTo(6.6, 1, 6.6, 9.4); c.moveTo(7.6, -4.4); c.quadraticCurveTo(9, 1, 9, 9.4); c.stroke(); // 兩道分綹線（第 2 稿第 2 版：只有平滑的彎月形讀成鐮刀）
      c.fillStyle = "#ffffff"; c.beginPath(); c.moveTo(2.6, -7.6); c.bezierCurveTo(5.4, -7.8, 6.4, -4.6, 6.2, 0.6); c.lineTo(5.2, 0.6); c.bezierCurveTo(5.2, -3.6, 4.4, -6, 2.4, -6.6); c.closePath(); c.fill(); // 亮面：左上
      c.restore();
    }
    // 柄：左下 → 右上（握柄端在左下），亮一階的木色；金箍在柄頂、毛的根部
    c.save(); c.translate(1.8, -6.4); c.rotate(-Math.PI / 4 - Math.PI / 2 + Math.PI); // 柄沿 (−1,1) 方向往左下
    Q.rr(c, "#a8703e", -1.3, 0, 2.6, 16.4, 1.2);
    if (!o.small) Q.rr(c, "rgba(255,255,255,0.45)", -0.9, 1.6, 0.8, 13.2, 0.4);
    Q.rr(c, "#e8bb48", -2.3, -1.6, 4.6, 3.4, 1.3);
    if (!o.tiny) Q.rr(c, "#f6d878", -1.7, -1.2, 1.7, 1.2, 0.5);
    c.restore();
  }
  /** 氣海：一團淡青的氣旋（青霧觀的霧色），中間一顆白芯，外面一圈往內捲的兩道白弧；元素用「主色＋亮色＋白芯」三層（規則 5）。
   *  刻意不用太極（讀成「陰陽」標誌）、不用一圈螺旋（第⑦批天氣「風」在小尺寸讀成 @）。 */
  /** 第 2 版（審查 M2：第 1 版是正圓，剪影＝實心圓，和護盾狀態、元素圓珠同形）：米白人形（同「本體」的 bust）＋下腹一團亮青氣團，
   *  氣團自己包一圈外框（halo，規則：前後重疊的兩件），兩條逗號形的氣尾往左右甩出人形外——剪影是「人形＋腰間兩撇」，
   *  和本體（純人形）、護盾（圓珠）、元素（水滴、旋風）都不同。氣團三層（主色＋亮色＋白芯，規則 5）。 */
  function dantianGlyph(c, o) {
    const Q = window.QIcons.H, gx = 0, gy = 4.6;
    bust(c, CREAM, 0, 0.0, 1.32);
    const tail = (q) => { q.beginPath(); q.moveTo(gx + 1.6, gy - 3.0); q.bezierCurveTo(gx + 6.4, gy - 6.8, gx + 10.8, gy - 4.6, gx + 10.6, gy + 0.2); q.bezierCurveTo(gx + 9.6, gy - 3.4, gx + 6.4, gy - 4.4, gx + 3.4, gy - 1.6); q.closePath(); };
    Q.halo(c, o, (x) => {
      for (const rot of [0, Math.PI]) { x.save(); x.translate(gx, gy); x.rotate(rot); x.translate(-gx, -gy); x.fillStyle = "#3fb8a8"; tail(x); x.fill(); if (!o.small) { x.fillStyle = "#8ff0e0"; x.translate(gx, gy); x.scale(0.9, 0.62); x.translate(-gx, -gy); tail(x); x.fill(); } x.restore(); } // 兩條逗號形氣尾（中心對稱，像在轉）
      Q.ci(x, "#3fb8a8", gx, gy, 4.1);
      Q.ci(x, "#8ff0e0", gx - 0.4, gy - 0.4, 2.9);
      Q.ci(x, "#ffffff", gx - 0.7, gy - 0.7, 1.5);
    });
  }
  /** 第 1 版的氣海（審查前，正圓）；只給對照列。 */
  function dantianGlyphV1(c, o) {
    const Q = window.QIcons.H;
    Q.ci(c, "#3fb8a8", 0, 0.4, 9.4);
    Q.ci(c, "#8ff0e0", -0.6, -0.2, 6.6);
    Q.ci(c, "#ffffff", -0.4, -0.2, 3.0);
    c.save(); c.lineCap = "round"; c.strokeStyle = "#e8fffb"; c.lineWidth = o.small ? 1.9 : 1.5;
    c.beginPath(); c.arc(0, 0.4, 7.9, -2.6, -0.9); c.stroke(); c.beginPath(); c.arc(0, 0.4, 7.9, 0.55, 2.2); c.stroke(); c.restore();
    if (!o.tiny) { Q.el(c, "rgba(255,255,255,0.8)", -3.6, -4.6, 1.6, 1.0, -0.6); Q.f(c, "rgba(0,0,0,0.22)", () => { c.arc(0, 0.4, 9.4, 0.2, 1.6); c.arc(0, 0.4, 7.2, 1.6, 0.2, true); c.closePath(); }); }
  }
  /** 本體：米白人形（規則 9）。長劍：直接呼叫第 4 批「手持指定武器」的亮色單手劍（同題材同一個形）。 */
  const GLYPH = {
    body: { zh: "本體", src: "qIconsParts.js bust（照抄）", d: (c, o) => bust(c, CREAM, 0, 1.2, 1.32) },
    whisk: { zh: "拂塵", src: "新畫（對照 qDoll QW.whisk）", d: whiskGlyph },
    dantian: { zh: "氣海", src: "新畫（第 2 版：人形＋氣團）", d: dantianGlyph },
    sword: { zh: "長劍", src: "QIconsParts condition:wielding_weapon", d: (c, o) => window.QIconsParts.entry("condition", "wielding_weapon").d(c, o) },
    whiskV1: { zh: "拂塵（第 1 版）", src: "對照", d: whiskGlyphV1 },
    dantianV1: { zh: "氣海（第 1 版）", src: "對照", d: dantianGlyphV1 },
    back: { zh: "從背後（打不到的原因）", src: "QIconsParts condition:from_behind", d: (c, o) => window.QIconsParts.entry("condition", "from_behind").d(c, o) },
  };
  /** 圖示 canvas：px＝顯示邊長（CSS px），res＝內部解析度。圖樣（±10 單位）佔 px 的 75%（同 QIconsParts.def：48 格裡放大 1.8 倍）。 */
  function icon(id, px, res = 2, opt = {}) {
    const e = GLYPH[id], def = { d: (c, o) => { c.save(); c.translate(24, 24); c.scale(1.8, 1.8); e.d(c, { ...o, small: px <= 24, tiny: px <= 14 }); c.restore(); } };
    return window.QIcons.render(def, px, res, { ow: opt.ow ?? (px <= 14 ? 0 : window.QIcons.outlinePx(px)) });
  }
  /** 灰掉（打不到、還沒露出）：去色、透明度 0.45。 */
  function gray(cv, a = 0.45) { const c = mk(cv.width, cv.height), x = c.getContext("2d"); x.filter = "grayscale(1) brightness(0.8)"; x.globalAlpha = a; x.drawImage(cv, 0, 0); return c; }

  // ---------------- 部位選單（照現行浮動說明框 .part-tip-box：底 --ui-navy、1px --ui-gold 框、圓角 6、陰影、12px 字） ----------------
  const UI = { navy: "#1e2236", gold: "#c8a868", goldHi: "#e8bb48", text: "#f0e6cc", muted: "#9a98a6", danger: "#ff6a5a", well: "#0c0e16" };
  const FONT = "'Noto Sans TC','Microsoft JhengHei',sans-serif";
  const MENU_W = 196, ROW_H = 26, PAD = 6;
  /** 選單內容。phase＝1 劍陣、2 鎖霧、3 歸一；behind＝攻擊者在頭目背後；hp＝頭目血量；parts＝{ id: { hp, broken } }；hover＝滑鼠在哪一列；dmg＝預估傷害。 */
  function menuRows(s) {
    const rows = [{ id: "body", zh: "本體", hp: s.hp, max: BOSS_HP, ok: true }];
    for (const p of PARTS) {
      const st = s.parts?.[p.id] ?? { hp: PART_HP }, shown = p.show.includes(s.phase);
      let why = null;
      if (st.broken) why = "已破壞";
      else if (!shown) why = p.show[0] === 2 ? "鎖霧階段才露出" : "歸一階段才露出";
      else if (p.reach === "back" && !s.behind) why = "要從背後才打得到";
      rows.push({ id: p.id, zh: p.zh, hp: st.broken ? 0 : st.hp, max: PART_HP, ok: !why, why, broken: !!st.broken, breaks: p.breaks, back: p.reach === "back" && shown && !st.broken && !s.behind });
    }
    return rows;
  }
  function menuHeight(s) { const rows = menuRows(s), hv = rows.find((r) => r.id === s.hover); return PAD + 18 + rows.length * ROW_H + (hv ? (hv.id === "body" || !hv.ok ? 16 : 32) : 0) + 18 + PAD; }
  /** 在 ctx（CSS px 座標）畫選單，左上 (x,y)；res＝內部解析度（圖示用）。回傳 { w, h }。 */
  function drawMenu(ctx, x, y, s, res = 2) {
    const rows = menuRows(s), W = MENU_W, H = menuHeight(s);
    ctx.save(); ctx.translate(x, y);
    ctx.save(); ctx.shadowColor = "rgba(0,0,0,0.6)"; ctx.shadowBlur = 16; ctx.shadowOffsetY = 4; ctx.fillStyle = UI.navy; ctx.beginPath(); ctx.roundRect(0, 0, W, H, 6); ctx.fill(); ctx.restore();
    ctx.lineWidth = 1; ctx.strokeStyle = UI.gold; ctx.beginPath(); ctx.roundRect(0.5, 0.5, W - 1, H - 1, 6); ctx.stroke();
    ctx.textBaseline = "middle"; ctx.font = `bold 12px ${FONT}`; ctx.fillStyle = UI.text; ctx.fillText("霧鎖真人", PAD + 2, PAD + 8);
    ctx.font = `11px ${FONT}`; ctx.fillStyle = UI.muted; ctx.textAlign = "right"; ctx.fillText(`選部位・${["", "劍陣", "鎖霧", "歸一"][s.phase]}`, W - PAD - 2, PAD + 8); ctx.textAlign = "left";
    let yy = PAD + 18;
    for (const r of rows) {
      const hv = r.id === s.hover, ext = hv ? (r.id === "body" || !r.ok ? 16 : 32) : 0;
      if (hv) { ctx.fillStyle = r.ok ? "rgba(232,187,72,0.16)" : "rgba(154,152,166,0.12)"; ctx.fillRect(1, yy, W - 2, ROW_H + ext); ctx.fillStyle = r.ok ? UI.goldHi : UI.muted; ctx.fillRect(1, yy, 2, ROW_H + ext); }
      // 圖示 20
      const ic = icon(r.id, 20, res), iy = yy + (ROW_H - 20) / 2;
      blit(ctx, r.ok ? ic : gray(ic), PAD + 2, iy, 20, res);
      if (r.broken) { ctx.save(); ctx.lineCap = "round"; for (const [col, lw] of [[OUT, 3.4], [UI.danger, 1.8]]) { ctx.strokeStyle = col; ctx.lineWidth = lw; ctx.beginPath(); ctx.moveTo(PAD + 5, iy + 3); ctx.lineTo(PAD + 19, iy + 17); ctx.moveTo(PAD + 19, iy + 3); ctx.lineTo(PAD + 5, iy + 17); ctx.stroke(); } ctx.restore(); }
      ctx.font = `bold 12px ${FONT}`; ctx.fillStyle = r.ok ? UI.text : UI.muted; ctx.fillText(r.zh, PAD + 28, yy + ROW_H / 2);
      const bx = PAD + 58, bw = 62, by = yy + ROW_H / 2 - 3;
      if (r.ok || r.id === "body") {
        ctx.fillStyle = UI.well; ctx.fillRect(bx, by, bw, 6); ctx.fillStyle = r.id === "body" ? hpColor(r.hp / r.max) : "#f2e6c8"; ctx.fillRect(bx, by, (bw * r.hp) / r.max, 6); ctx.strokeStyle = "rgba(0,0,0,0.9)"; ctx.lineWidth = 1; ctx.strokeRect(bx - 0.5, by - 0.5, bw + 1, 7);
        ctx.font = `11px ${FONT}`; ctx.fillStyle = "#d8ccb8"; ctx.textAlign = "right"; ctx.fillText(`${r.hp}/${r.max}`, W - PAD - 2, yy + ROW_H / 2); ctx.textAlign = "left";
      } else {
        if (r.back) blit(ctx, gray(icon("back", 16, res), 0.8), bx - 2, yy + (ROW_H - 16) / 2, 16, res);
        ctx.font = `11px ${FONT}`; ctx.fillStyle = r.broken ? UI.danger : UI.muted; ctx.textAlign = "right"; ctx.fillText(r.why, W - PAD - 2, yy + ROW_H / 2); ctx.textAlign = "left";
      }
      if (hv) {
        ctx.font = `11px ${FONT}`;
        if (r.id === "body") { ctx.fillStyle = UI.muted; ctx.fillText(s.dmg ? `預覽：本體還剩 ${Math.max(0, r.hp - s.dmg)}（−${s.dmg}）` : "打本體（現有操作不變）", PAD + 28, yy + ROW_H + 6); }
        else {
          if (r.ok) { ctx.fillStyle = "#ffe9a8"; ctx.fillText(s.dmg ? `預覽：${r.zh}還剩 ${Math.max(0, r.hp - s.dmg)}（−${s.dmg}）` : `${r.zh}還剩 ${r.hp}`, PAD + 28, yy + ROW_H + 4); }
          ctx.fillStyle = UI.muted; if (!r.broken) ctx.fillText(`破掉會：${r.breaks}`, PAD + 28, yy + ROW_H + (r.ok ? 19 : 4), W - PAD - 30); else ctx.fillText(`已破：${r.breaks}`, PAD + 28, yy + ROW_H + 4, W - PAD - 30);
        }
      }
      yy += ROW_H + ext;
    }
    ctx.fillStyle = "rgba(200,168,104,0.35)"; ctx.fillRect(PAD, yy + 3, W - 2 * PAD, 1);
    ctx.font = `11px ${FONT}`; ctx.fillStyle = UI.muted; ctx.fillText("點本體或按確認＝打本體", PAD + 2, yy + 12);
    ctx.restore();
    return { w: W, h: H };
  }
  /** 圖貼到整數裝置像素（同 QIconsWeapons.blit 的原則：照 canvas 原尺寸、左上角四捨五入）。ctx 每 CSS px＝res 裝置像素且沒有旋轉。 */
  function blit(ctx, cv, x, y, a, res) {
    const m = ctx.getTransform(), px = m.a * x + m.e, py = m.d * y + m.f;
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.drawImage(cv, Math.round(px + (m.a * a - cv.width) / 2), Math.round(py + (m.d * a - cv.height) / 2)); ctx.restore();
  }

  return { T, K, FEET, HP_W, HP_Y, HP_H, OUT, BOSS_HP, PART_HP, PARTS, HOVER, STRIP, GLYPH, UI, MENU_W, bossUnit, stamp, glow, partMask, centerOf, weaponToModel, debris, fallenTuft, fallenTip, tuftPath, swordTip, whiskStub, stripLayout, partBar, hud, chargeBadge, icon, gray, menuRows, menuHeight, drawMenu, blit, hpColor, mk, tint };
})();
