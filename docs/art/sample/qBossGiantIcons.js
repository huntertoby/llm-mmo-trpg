// qBossGiantIcons.js：灰燼之心 3×3 的部位小圖（Phase GB 美術 A3，畫圖 agent，2026-11-14）。
// 紀錄：docs/art/GB巨型頭目-美術.md 3.4；樣張頁：giant-boss.html ?part=icons｜icons-t1｜icons-marks；重拍：tools/giant_boss_shots.py。
//
// 給 PartMenu（選單每列 20px）、PartBar／角色卡、（選用）部位格標示。規格照 頭目部位-移植需求.md 2.1（同霧鎖真人）：
//   圖樣畫在 ±10 單位、放進 48 格放大 1.8 倍（同 QIconsParts.def／BossParts.icon），#16121a 剪影外框照 QIcons.outlinePx，平塗三階；
//   打不到、未露出＝BossParts.gray（去色＋亮度 0.8＋透明度 0.45）；已破壞＝灰掉的圖示上壓紅「×」（外框色襯邊，同 BossParts.drawMenu）。
// 造型照第 2 版身上的部位（qBossGiant.js；色票同一組、沒有新色）：
//   熔岩噴口＝北排的火山錐（下寬上窄、腰內凹、口緣一圈、口裡熔岩），加一道往上噴的熔岩舌（熔岩噴發）；
//   殼縫＝中排兩側殼上的熔岩裂縫：一塊玄武岩殼板，正中一道上下貫穿的鋸齒熔岩縫（暗紅邊＋熔岩＋黃芯），一條分岔；
//   核心＝中心殼窩裡的晶體（qBoss core() 的七邊形 CORE_PTS），坐在玄武岩殼窩（下半圈）上，晶體自己包外框、後面一圈核心色光暈。
// 玄武岩換亮一階（規則 6：深底上的暗色零件換亮一階的同類色）：身上 BASALT #4a3b36／BASALT_L #6a5a52 → 圖示用 BASALT_L 當本色、#8a7a70 亮面、#54463f 暗面。
window.QBossGiantIcons = (() => {
  const TAU = Math.PI * 2, OUT = "#16121a";
  const ROCK = "#7c6c62", ROCK_HI = "#9a8a7e", ROCK_SH = "#5e4e46", RIM = "#8a7a70"; // 第 1 稿 #6a5a52 本色時 20px 平均亮度 94（規則 6 要 100），再亮一階
  const LAVA = "#ff6a1a", LAVA_HOT = "#ffd23a", EMBER = "#7a2a08", CORE = "#ffb23a";
  const H = () => window.QIcons.H;
  const path = (c, pts) => { c.beginPath(); pts.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y))); c.closePath(); };

  /** 熔岩噴口：火山錐＋口緣＋熔岩＋往上噴的熔岩舌（主色＋亮色＋白芯，規則 5）。 */
  function ventGlyph(c, o) {
    const Q = H();
    c.save(); c.translate(0, 0.6); // 第 1 稿錐身只佔 16×17／20（規則 7 要 70% 以上），加寬加高
    const cone = (q) => { q.beginPath(); q.moveTo(-10.2, 9.2); q.quadraticCurveTo(-4.8, 4.4, -4.8, -1.6); q.lineTo(4.8, -1.6); q.quadraticCurveTo(4.8, 4.4, 10.2, 9.2); q.closePath(); };
    c.fillStyle = ROCK; cone(c); c.fill();
    c.save(); cone(c); c.clip();
    c.fillStyle = ROCK_HI; c.beginPath(); c.moveTo(-11, 9.2); c.quadraticCurveTo(-5.6, 4, -5.4, -1.6); c.lineTo(-2.2, -1.6); c.quadraticCurveTo(-2.6, 4.2, -5.2, 9.2); c.closePath(); c.fill(); // 左側亮面
    c.fillStyle = ROCK_SH; c.beginPath(); c.moveTo(11, 9.2); c.quadraticCurveTo(5.4, 4, 5.2, -1.6); c.lineTo(3.2, -1.6); c.quadraticCurveTo(3.2, 4.6, 6.2, 9.2); c.closePath(); c.fill(); // 右側暗面
    if (!o.small) for (const x of [-5, 0, 5]) { Q.ci(c, RIM, x, 6.2, 2.6); Q.ci(c, ROCK_HI, x - 0.7, 5.5, 1.0); } // 殼瓦（20px 省掉）
    c.fillStyle = LAVA; c.beginPath(); c.moveTo(-3.0, -0.8); c.quadraticCurveTo(-3.6, 3.4, -2.1, 4.8); c.quadraticCurveTo(-1.0, 3.4, -1.0, -0.8); c.closePath(); c.fill(); // 口緣溢出的熔岩（一道）
    c.restore();
    // 口緣與口裡的熔岩
    Q.el(c, RIM, 0, -1.8, 5.9, 2.3);
    Q.el(c, LAVA, 0, -1.7, 4.3, 1.4);
    // 熔岩舌（噴發）：從口往上，自己包外框（和錐身分開）
    Q.halo(c, o, (x) => {
      x.fillStyle = LAVA; x.beginPath(); x.moveTo(-3.4, -1.9); x.bezierCurveTo(-5.0, -6.2, -1.6, -8.4, 0.4, -11.2); x.bezierCurveTo(0.8, -8.6, 5.0, -6.4, 3.4, -1.9); x.closePath(); x.fill();
      x.fillStyle = LAVA_HOT; x.beginPath(); x.moveTo(-1.7, -2.1); x.bezierCurveTo(-2.5, -5.2, -0.6, -6.8, 0.3, -8.6); x.bezierCurveTo(0.7, -6.6, 2.5, -5.2, 1.7, -2.1); x.closePath(); x.fill();
      if (!o.tiny) Q.ci(x, "#ffffff", -0.1, -4.4, 0.9);
    });
    c.restore();
  }
  /** 殼縫：玄武岩殼板＋上下貫穿的鋸齒熔岩縫（同身上 seam：暗紅寬邊、熔岩、黃芯）＋一條分岔。 */
  // 殼板上下兩端在熔岩縫出口各缺一個 V 口：剪影是「裂開的石板」，和核心（蛋形）、本體分得開（規則 11）
  const SLAB = [[-6.4, -9.2], [-2.4, -9.6], [0.6, -4.6], [3.4, -9.8], [4.6, -9.6], [8.6, -4.4], [8.2, 6.6], [3.6, 9.6], [2.4, 9.8], [-0.2, 5.4], [-2.8, 9.8], [-6.0, 9.4], [-8.8, 4.4], [-8.6, -5.2]];
  const CRACK = [[0.6, -10.4], [-1.9, -5.4], [1.7, -1.6], [-1.6, 2.6], [1.8, 6.4], [-0.2, 10.4]];
  function seamGlyph(c, o) {
    const Q = H();
    Q.poly(c, ROCK, SLAB, 1.2);
    c.save(); path(c, SLAB); c.clip();
    Q.poly(c, ROCK_HI, [[-9.6, -10.4], [-1.4, -10.6], [-4.2, -4.8], [-6.4, 1.4], [-9.8, 2.6]]); // 左上亮面
    Q.poly(c, ROCK_SH, [[9.6, -1.6], [9.6, 10.6], [3.2, 10.6], [6.2, 4.4]]); // 右下暗面
    // 熔岩縫：暗紅寬邊 → 熔岩 → 黃芯（20px 黃芯照畫，是這個圖示的亮面）
    const br = [[1.7, -1.6], [6.0, -3.6], [9.6, -2.6]];
    Q.ln(c, EMBER, 4.4, CRACK); Q.ln(c, EMBER, 3.0, br);
    Q.ln(c, LAVA, 2.8, CRACK); Q.ln(c, LAVA, 1.6, br);
    Q.ln(c, LAVA_HOT, o.small ? 1.3 : 1.0, CRACK.slice(1, 5));
    c.restore();
  }
  /** 核心：殼窩（玄武岩下半圈）＋晶體（qBoss CORE_PTS，自己包外框）；光暈在外框底下（pre）。 */
  const CORE_PTS = [[0, -15], [10, -8], [11, 4], [4, 13], [-6, 12], [-11, 3], [-9, -9]].map(([x, y]) => [x * 0.66, y * 0.66 - 1.6]);
  function coreGlyph(c, o) {
    const Q = H();
    // 殼窩：下半圈的玄武岩窩（像捧著晶體），左右兩片掀開的殼蓋
    c.fillStyle = ROCK; c.beginPath(); c.ellipse(0, 4.6, 9.4, 5.2, 0, 0, Math.PI); c.lineTo(-9.4, 2.6); c.quadraticCurveTo(0, 5.4, 9.4, 2.6); c.closePath(); c.fill();
    c.fillStyle = ROCK_HI; c.beginPath(); c.ellipse(-4.6, 6.4, 3.6, 1.5, -0.25, 0, TAU); c.fill();
    for (const s of [-1, 1]) { Q.poly(c, RIM, [[s * 6.6, 3.4], [s * 9.8, -3.6], [s * 10.2, 1.4], [s * 9.6, 4.4]], 0.6); }
    Q.halo(c, o, (x) => {
      Q.poly(x, CORE, CORE_PTS, 0.3);
      Q.poly(x, "#ffd98a", [CORE_PTS[0], CORE_PTS[6], CORE_PTS[5], [0.66, -1.6]]); // 左上亮面
      Q.poly(x, "#e8962a", [CORE_PTS[2], CORE_PTS[3], [0.66, -1.6]]); // 右下暗面
      x.fillStyle = "#ffffff"; x.fillRect(-3.4, -7.6, 1.6, o.small ? 3.4 : 3.0); if (!o.tiny) x.fillRect(-1.4, -8.8, 1.1, 1.1);
    });
  }
  const corePre = (c) => window.QIcons.H.glow(c, 24, 21, 19, CORE, 0.55);

  /** 本體（A4 時加；美術 PM 3.5：灰燼之心整隻縮到 20px，前殼＋核心光；具名頭目本體用頭像的例外，同霧鎖真人）。
   *  做法同 bossParts.js 第 3 版頭像：取 QBossGiant.fill() 的本體填色層（第 2 階段・熔殼不在：殼蓋掀開、核心露出；不描外框、不帶金外光），
   *  高解析度畫一次快取，裁整隻（BODY.box，模型 px）貼進 ±BODY.span／2 圖樣單位，外框交給 QIcons.render（20px＝1px）。≤32px 在裝置像素上：
   *   a. alpha 門檻 ≥0.5（同頭像可修 2：外緣半像素不留灰帶）；
   *   b. 核心光加粗（20px 時晶體只剩 2 px、窩裡的光不到 1 px 寬）：核心位置一團 LAVA_HOT 柔光＋貼整數像素的晶體塊（CORE 本色＋左上 1 px 亮點）；
   *   c. 前殼三隻甲蟲的火眼加粗：兩眼縮下來不到 1 px 間距，合成一顆 1 px 熔岩色點（貼整數像素）。b、c 只在 o.small。 */
  const BODY = { lift: 1.25, st: { phase: 2, shell: 0, t: 300 }, box: [-78, -159, 156, 160], span: 22.6, z: 6, core: [0, -73], eyes: [[-47, -15], [0, -14], [47, -15]] };
  let bodyCache = null;
  const bodyFill = () => bodyCache ?? (bodyCache = window.QBossGiant.fill(BODY.st, BODY.z));
  function bodyGlyph(c, o) {
    const F = bodyFill(), [bx, by, bw, bh] = BODY.box, k = BODY.span / bw;
    const put = (g) => { g.imageSmoothingEnabled = true; g.imageSmoothingQuality = "high"; g.drawImage(F.canvas, F.ox + bx * F.z, F.oy + by * F.z, bw * F.z, bh * F.z, -BODY.span / 2, -(bh * k) / 2, BODY.span, bh * k); };
    if (48 / o.u > 32) { c.save(); put(c); c.restore(); return; }
    const Mg = c.getTransform(), Md = Mg.translate(-BODY.span / 2 - bx * k, -(bh * k) / 2 - by * k).scale(k, k); // 模型 px → 裝置像素
    const W = c.canvas.width, Hh = c.canvas.height, L = document.createElement("canvas"); L.width = W; L.height = Hh;
    const lg = L.getContext("2d", { willReadFrequently: true }); lg.setTransform(Mg); put(lg);
    const img = lg.getImageData(0, 0, W, Hh), d = img.data;
    for (let i = 3; i < d.length; i += 4) d[i] = d[i] >= 128 ? 255 : 0; // a
    if (!o.flat) for (let i = 0; i < d.length; i += 4) { if (!d[i + 3]) continue; const lum = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]; if (lum < 120) for (let j = 0; j < 3; j++) d[i + j] = Math.min(255, Math.round(d[i + j] * BODY.lift + 6)); } // a2：玄武岩換亮一階（規則 6；同部位圖示 ROCK 換亮的做法，只動暗色像素，熔岩、核心不變）
    lg.putImageData(img, 0, 0);
    if (o.small && !o.flat) {
      const dp = Math.max(1, Math.round(W / (48 / o.u))); // 裝置像素／CSS px（20px res1＝1、res2＝2）
      const at = (mx, my) => { const p = Md.transformPoint(new DOMPoint(mx, my)); return [p.x, p.y]; };
      lg.setTransform(1, 0, 0, 1, 0, 0);
      const [cx, cy] = at(...BODY.core);
      lg.save(); lg.fillStyle = LAVA_HOT; for (const [r, al] of [[3.6, 0.3], [2.6, 0.4]]) { lg.globalAlpha = al; lg.beginPath(); lg.arc(cx, cy, r * dp, 0, TAU); lg.fill(); } lg.restore(); // b：核心柔光
      const bw2 = 2 * dp, bh2 = 3 * dp, x0 = Math.round(cx - bw2 / 2), y0 = Math.round(cy - bh2 / 2);
      lg.fillStyle = CORE; lg.fillRect(x0, y0, bw2, bh2); lg.fillStyle = "#fff4d0"; lg.fillRect(x0, y0, dp, dp); // b：晶體塊
      lg.fillStyle = LAVA; for (const [ex, ey] of BODY.eyes) { const [x, y] = at(ex, ey); lg.fillRect(Math.round(x - dp / 2), Math.round(y - dp / 2), dp, dp); } // c：火眼
    }
    c.save(); c.setTransform(1, 0, 0, 1, 0, 0); c.drawImage(L, 0, 0); c.restore();
  }

  const GLYPH = {
    body: { zh: "本體", d: bodyGlyph },
    vent: { zh: "熔岩噴口", d: ventGlyph },
    seam: { zh: "殼縫", d: seamGlyph },
    core: { zh: "核心", d: coreGlyph, pre: corePre },
  };
  /** 圖示 canvas（同 BossParts.icon）：px＝顯示邊長（CSS px），res＝內部解析度。 */
  function icon(id, px, res = 2, opt = {}) {
    const e = GLYPH[id];
    const def = { d: (c, o) => { c.save(); c.translate(24, 24); c.scale(1.8, 1.8); e.d(c, { ...o, small: px <= 24, tiny: px <= 14 }); c.restore(); }, pre: e.pre };
    return window.QIcons.render(def, px, res, { ow: opt.ow ?? (px <= 14 ? 0 : window.QIcons.outlinePx(px)) });
  }
  /** 已破壞的紅×（同 BossParts.drawMenu：外框色 3.4＋#ff6a5a 1.8，20px 圖示內縮 3；其他尺寸照比例，最細 1.5／1）。 */
  function xMark(ctx, x, y, px) {
    const k = px / 20, i = 3 * k;
    ctx.save(); ctx.lineCap = "round";
    for (const [col, lw] of [[OUT, Math.max(2.6, 3.4 * k)], ["#ff6a5a", Math.max(1.4, 1.8 * k)]]) { ctx.strokeStyle = col; ctx.lineWidth = lw; ctx.beginPath(); ctx.moveTo(x + i, y + i); ctx.lineTo(x + px - i, y + px - i); ctx.moveTo(x + px - i, y + i); ctx.lineTo(x + i, y + px - i); ctx.stroke(); }
    ctx.restore();
  }
  return { GLYPH, icon, xMark };
})();
