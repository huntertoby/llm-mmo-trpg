// 形態（變身，#48）外觀樣張：10 種，全部另畫，不沿用召喚物。
// 使用者：「整身替換 而且要跟召喚物有區別性」「第一批 + 龍 + 狼人姿態 就好」。
// 規則（玩法 PM 轉達）：① 另畫 ② 保留主角服裝主色當毛色或紋路（spec.hero）③ 比同類召喚物大一號＋形態光環（光環由呼叫端畫）。
// 座標同召喚物：腳底中心為原點、往上是負、面向右（朝西時左右鏡像）。元素化身與龍另吃 spec.element（fire／ice／lightning）。
// 不認得的形態 → 回傳 false，呼叫端退回原角色紙娃娃＋光環。
window.FormArt = (() => {
  const TAU = Math.PI * 2;
  const INK = "#16121a";
  const ELEM = { fire: ["#ff7a1a", "#ffd04a"], ice: ["#8fe3ff", "#e8fbff"], lightning: ["#ffe14a", "#fff7c0"] };
  function hexRgb(h) { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
  function mix(a, b, t) {
    const [r1, g1, b1] = hexRgb(a), [r2, g2, b2] = hexRgb(b);
    const m = (x, y) => Math.round(x * (1 - t) + y * t);
    return `#${((m(r1, r2) << 16) | (m(g1, g2) << 8) | m(b1, b2)).toString(16).padStart(6, "0")}`;
  }
  const dark = (c, t = 0.35) => mix(c, "#000000", t);
  function fill(ctx, c, path) { ctx.fillStyle = c; ctx.beginPath(); path(); ctx.fill(); }
  function poly(ctx, c, pts) { fill(ctx, c, () => { pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); }); }
  function line(ctx, c, w, pts) { ctx.strokeStyle = c; ctx.lineWidth = w; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.stroke(); }
  const eye = (ctx, show, x, y, c = "#1d1a22", r = 1.1) => { if (show) fill(ctx, c, () => ctx.arc(x, y, r, 0, TAU)); };
  function claws(ctx, xs, y, c = "#e8e0d0") { for (const x of xs) poly(ctx, c, [[x - 1.6, y], [x - 0.8, y + 1.8], [x, y], [x + 0.8, y + 1.8], [x + 1.6, y]]); }

  // ---- 四足 ----
  function bear(ctx, h, show) {
    const c = mix("#6a4a32", h, 0.3), d = dark(c), belly = mix(c, "#ffffff", 0.25);
    for (const x of [-11, -5, 6, 12]) fill(ctx, x < 0 ? d : c, () => ctx.roundRect(x - 2.8, -12, 5.6, 12, 2));
    claws(ctx, [6, 12], 0);
    fill(ctx, c, () => { ctx.moveTo(-16, -9); ctx.quadraticCurveTo(-17, -28, -2, -29); ctx.quadraticCurveTo(13, -29, 15, -12); ctx.lineTo(15, -8); ctx.lineTo(-16, -8); ctx.closePath(); });
    // 主色紋路：背上三道
    for (const x of [-9, -3, 3]) line(ctx, h, 2.2, [[x, -27], [x + 2, -20]]);
    fill(ctx, belly, () => ctx.ellipse(1, -11, 11, 3, 0, 0, TAU));
    fill(ctx, c, () => ctx.ellipse(16, -20, 7.5, 6.5, 0, 0, TAU));
    fill(ctx, mix(c, "#ffffff", 0.35), () => ctx.ellipse(21.5, -18.5, 3.8, 2.8, 0, 0, TAU));
    fill(ctx, INK, () => ctx.arc(24.5, -19, 1.2, 0, TAU));
    for (const x of [12, 18]) fill(ctx, d, () => ctx.arc(x, -26.5, 2.8, 0, TAU));
    eye(ctx, show, 18, -22);
  }
  function cat(ctx, h, show) {
    // 大型貓科（豹）：比戰狼大一號、低姿態、長尾
    const c = mix("#3a3440", h, 0.35), d = dark(c);
    for (const x of [-10, -6, 8, 12]) fill(ctx, x < 0 ? d : c, () => ctx.roundRect(x - 1.6, -8, 3.2, 8, 1.2));
    claws(ctx, [8, 12], 0);
    fill(ctx, c, () => ctx.ellipse(0, -10.5, 14, 4.8, -0.04, 0, TAU));
    for (const x of [-8, -3, 2]) line(ctx, h, 1.8, [[x, -14.5], [x + 1.5, -9]]); // 主色斑紋
    line(ctx, c, 3, [[-13, -11], [-22, -13], [-21, -24]]);
    line(ctx, h, 3, [[-21.5, -21], [-21, -24]]); // 尾尖主色
    fill(ctx, c, () => ctx.ellipse(15, -14, 5.2, 4.4, 0, 0, TAU));
    for (const x of [13, 17.5]) poly(ctx, c, [[x - 2.2, -16.5], [x, -22.5], [x + 2.2, -16.5]]);
    if (show) fill(ctx, "#ffe14d", () => ctx.ellipse(17.5, -14.5, 1.4, 1, 0, 0, TAU));
  }
  function wolfman(ctx, h, show) {
    // 狼人：雙腳站立、前傾、利爪；主色是破褲與腰帶
    const c = mix("#6a6a74", h, 0.25), d = dark(c), pants = h;
    // 腿（獸腳，膝反折）
    for (const [x, s] of [[-4, d], [4, c]]) { line(ctx, s, 4.5, [[x, -16], [x + 2, -9], [x - 1, -3], [x + 1, 0]]); }
    claws(ctx, [-3, 5], 0);
    fill(ctx, pants, () => ctx.roundRect(-7, -20, 14, 7, 2)); // 破褲
    poly(ctx, dark(pants), [[-7, -13], [-5, -10], [-3, -13], [1, -10], [3, -13], [7, -13]]);
    fill(ctx, "#5a3a20", () => ctx.rect(-7, -21, 14, 2)); // 腰帶
    // 軀幹前傾、厚胸
    fill(ctx, c, () => { ctx.moveTo(-7, -20); ctx.quadraticCurveTo(-10, -36, 2, -40); ctx.quadraticCurveTo(12, -38, 9, -20); ctx.closePath(); });
    fill(ctx, mix(c, "#ffffff", 0.3), () => ctx.ellipse(4, -29, 4, 6, 0.2, 0, TAU));
    // 手臂垂到膝、利爪
    line(ctx, d, 4, [[-5, -36], [-9, -26], [-8, -17]]);
    line(ctx, c, 4, [[8, -35], [13, -26], [12, -17]]);
    claws(ctx, [11, 13.5], -16, "#f0e8d8");
    // 狼頭
    fill(ctx, c, () => ctx.ellipse(6, -44, 6, 5, -0.2, 0, TAU));
    poly(ctx, c, [[9, -46], [17, -43], [9, -40]]);
    for (const x of [3, 7]) poly(ctx, d, [[x - 2, -48], [x, -54], [x + 2, -48]]);
    fill(ctx, INK, () => ctx.arc(17, -43, 1, 0, TAU));
    if (show) fill(ctx, "#ffe14d", () => ctx.arc(9, -45, 1.1, 0, TAU));
  }
  function dragon(ctx, h, show, el) {
    const [ec, el2] = ELEM[el] ?? ["#9a86ff", "#e8e2ff"];
    const c = mix("#4a5a4a", h, 0.45), d = dark(c), belly = mix(ec, "#ffffff", 0.35);
    // 翅膀（後）
    poly(ctx, d, [[-4, -24], [-20, -46], [-14, -40], [-10, -44], [-8, -36], [-2, -38], [2, -26]]);
    for (const x of [-11, -6]) line(ctx, mix(d, ec, 0.3), 1, [[-4, -25], [x, -42]]);
    for (const x of [-12, -6, 7, 13]) fill(ctx, x < 0 ? d : c, () => ctx.roundRect(x - 2.6, -11, 5.2, 11, 2));
    claws(ctx, [7, 13], 0);
    fill(ctx, c, () => ctx.ellipse(0, -15, 16, 7, 0, 0, TAU));
    fill(ctx, belly, () => ctx.ellipse(2, -10.5, 12, 2.6, 0, 0, TAU));
    line(ctx, c, 5, [[-14, -15], [-24, -12], [-29, -18]]); // 尾
    poly(ctx, h, [[-29, -18], [-33, -22], [-27, -21]]);
    // 長頸＋頭
    line(ctx, c, 6, [[11, -19], [16, -30], [19, -36]]);
    fill(ctx, c, () => ctx.ellipse(22, -38, 6, 4, -0.15, 0, TAU));
    poly(ctx, c, [[25, -40], [31, -37], [25, -35]]);
    for (const x of [18, 21]) poly(ctx, h, [[x - 1.5, -41], [x - 4, -47], [x + 0.5, -41.5]]); // 主色角
    for (const x of [-8, -2, 4]) poly(ctx, h, [[x - 2, -21], [x, -25], [x + 2, -21]]); // 主色背鰭
    // 吐息光（元素色）
    const g = ctx.createRadialGradient(31, -37, 0, 31, -37, 7); g.addColorStop(0, el2); g.addColorStop(1, ec + "00");
    fill(ctx, g, () => ctx.arc(31, -37, 7, 0, TAU));
    if (show) fill(ctx, ec, () => ctx.arc(23, -39.5, 1.2, 0, TAU));
  }
  function roc(ctx, h, show) {
    // 鳥形態（巨鵰）：雙翼高舉成 V、長尾羽、頭冠；翼尖與尾羽是主色。和鷹隼（小、平飛）完全不同的剪影
    ctx.translate(0, -16);
    const c = "#a07a4a", d = dark(c);
    poly(ctx, d, [[-2, -4], [-12, -26], [-20, -30], [-16, -22], [-22, -24], [-14, -12], [-4, 2]]);
    poly(ctx, h, [[-12, -26], [-20, -30], [-16, -22], [-22, -24], [-17, -18]]);
    poly(ctx, c, [[2, -4], [10, -28], [18, -34], [15, -24], [22, -27], [14, -12], [4, 2]]);
    poly(ctx, h, [[10, -28], [18, -34], [15, -24], [22, -27], [16, -19]]);
    fill(ctx, c, () => ctx.ellipse(0, 0, 9, 6, 0, 0, TAU));
    fill(ctx, "#f0e6d0", () => ctx.ellipse(1.5, 2, 6, 3, 0, 0, TAU));
    poly(ctx, h, [[-8, 2], [-18, 8], [-16, 2], [-20, 4], [-9, -1]]); // 主色尾羽
    fill(ctx, c, () => ctx.arc(9, -4, 4.2, 0, TAU));
    poly(ctx, "#e8bb48", [[12.5, -5], [17, -3], [12.5, -1]]);
    poly(ctx, h, [[6, -7], [4, -12], [8, -8], [9, -13], [10, -7.5]]); // 主色頭冠
    eye(ctx, show, 10.5, -5);
    // 爪（垂下）
    line(ctx, "#e8bb48", 1.4, [[-2, 5], [-2, 9]]); line(ctx, "#e8bb48", 1.4, [[3, 5], [3, 9]]);
  }

  // ---- 人形 ----
  function demon(ctx, h, show) {
    // 惡魔：蝙蝠翼（召喚物影魅沒有翅膀）、彎角、雙刃；衣服是主色
    const skin = "#6a3a7a", wing = "#3a1a40";
    poly(ctx, wing, [[-3, -30], [-20, -42], [-17, -34], [-22, -32], [-16, -26], [-18, -20], [-4, -22]]);
    poly(ctx, wing, [[3, -30], [18, -44], [16, -36], [21, -33], [15, -27], [17, -21], [4, -22]]);
    for (const x of [-3, 3]) line(ctx, skin, 3.6, [[x, -14], [x, 0]]);
    fill(ctx, h, () => ctx.roundRect(-7, -30, 14, 17, 3)); // 主色上衣
    poly(ctx, dark(h), [[-7, -15], [7, -15], [5, -11], [-5, -11]]);
    line(ctx, skin, 3, [[-7, -28], [-10, -19]]); line(ctx, skin, 3, [[7, -28], [11, -20]]);
    // 雙刃
    line(ctx, "#c8c0e0", 2, [[-10, -19], [-14, -33]]); line(ctx, "#c8c0e0", 2, [[11, -20], [17, -33]]);
    fill(ctx, skin, () => ctx.arc(0, -36, 6, 0, TAU));
    for (const s of [-1, 1]) fill(ctx, "#2a1a2a", () => { ctx.moveTo(s * 4, -40); ctx.quadraticCurveTo(s * 9, -44, s * 7, -50); ctx.quadraticCurveTo(s * 6, -45, s * 2, -41); });
    if (show) fill(ctx, "#ff5a8a", () => { ctx.arc(-2.2, -36, 1.1, 0, TAU); ctx.arc(2.2, -36, 1.1, 0, TAU); });
    line(ctx, skin, 1.6, [[-2, -14], [-8, -6], [-6, -2]]); // 尾巴
  }
  function giant(ctx, h, show) {
    // 巨人：粗壯人形、石棒；腰布與護肩是主色
    const skin = "#c89a78", sd = dark(skin, 0.25);
    for (const x of [-5, 5]) fill(ctx, sd, () => ctx.roundRect(x - 3, -16, 6, 16, 2));
    fill(ctx, h, () => ctx.roundRect(-9, -20, 18, 8, 2)); // 主色腰布
    fill(ctx, skin, () => ctx.roundRect(-10, -38, 20, 20, 6));
    fill(ctx, h, () => ctx.ellipse(-9, -36, 4.5, 3, 0, 0, TAU)); // 主色護肩
    line(ctx, sd, 5, [[-10, -35], [-13, -22]]);
    line(ctx, skin, 5, [[10, -35], [14, -24]]);
    line(ctx, "#7a7470", 5, [[14, -22], [22, -42]]); // 石棒
    fill(ctx, "#8a847e", () => ctx.ellipse(22, -42, 4, 5.5, -0.4, 0, TAU));
    fill(ctx, skin, () => ctx.arc(0, -43, 6, 0, TAU));
    fill(ctx, "#5a3a20", () => ctx.rect(-6, -48, 12, 3));
    if (show) fill(ctx, INK, () => { ctx.arc(-2.2, -43, 1, 0, TAU); ctx.arc(2.2, -43, 1, 0, TAU); });
  }
  function avatar(ctx, h, show, el) {
    // 元素化身：元素構成的人形（下半身是元素流），胸口一顆主色核心
    const [ec, el2] = ELEM[el] ?? ELEM.fire;
    const g = ctx.createLinearGradient(0, -48, 0, 0); g.addColorStop(0, el2); g.addColorStop(1, ec);
    fill(ctx, g, () => { ctx.moveTo(-8, -32); ctx.quadraticCurveTo(-10, -18, -4, -6); ctx.quadraticCurveTo(0, 2, 4, -6); ctx.quadraticCurveTo(10, -18, 8, -32); ctx.closePath(); });
    for (const [x, y, s] of [[-6, -4, 3], [5, -2, 2.5], [0, 1, 2]]) fill(ctx, ec + "aa", () => ctx.arc(x, y, s, 0, TAU));
    line(ctx, ec, 4, [[-8, -30], [-13, -20]]); line(ctx, ec, 4, [[8, -30], [13, -20]]);
    fill(ctx, el2, () => ctx.arc(0, -38, 6, 0, TAU));
    if (el === "fire") for (const x of [-3, 0, 3]) poly(ctx, ec, [[x - 2, -42], [x, -49], [x + 2, -42]]);
    if (el === "ice") for (const x of [-4, 0, 4]) poly(ctx, "#ffffff", [[x - 1.5, -42], [x, -48], [x + 1.5, -42]]);
    if (el === "lightning") line(ctx, ec, 1.6, [[-5, -43], [-2, -47], [1, -43], [4, -48]]);
    fill(ctx, h, () => { ctx.moveTo(0, -27); ctx.lineTo(3.5, -23); ctx.lineTo(0, -19); ctx.lineTo(-3.5, -23); ctx.closePath(); }); // 主色核心
    if (show) fill(ctx, "#ffffff", () => { ctx.arc(-2.2, -38, 1.1, 0, TAU); ctx.arc(2.2, -38, 1.1, 0, TAU); });
  }
  function shadowForm(ctx, h, show) {
    // 暗影形態：無腳的煙影、尖肩、長爪；主色是飄帶與眼光（召喚物影魅是戴兜帽持匕首的人形）
    const c = "#2a2434";
    fill(ctx, c, () => { ctx.moveTo(-9, -34); ctx.quadraticCurveTo(-12, -14, -6, -6); ctx.quadraticCurveTo(-3, -1, 0, -4); ctx.quadraticCurveTo(3, 0, 6, -5); ctx.quadraticCurveTo(12, -14, 9, -34); ctx.closePath(); });
    poly(ctx, c, [[-9, -34], [-14, -38], [-6, -36]]); poly(ctx, c, [[9, -34], [14, -38], [6, -36]]);
    line(ctx, c, 3, [[-9, -30], [-14, -20], [-16, -14]]); line(ctx, c, 3, [[9, -30], [14, -20], [17, -15]]);
    line(ctx, h, 2, [[-2, -26], [-6, -16], [-3, -8], [-8, -2]]); // 主色飄帶
    line(ctx, h, 2, [[2, -26], [5, -15], [2, -8], [6, -3]]);
    fill(ctx, c, () => ctx.ellipse(0, -39, 6, 6.5, 0, 0, TAU));
    if (show) { ctx.save(); ctx.shadowColor = h; ctx.shadowBlur = 3; fill(ctx, mix(h, "#ffffff", 0.5), () => { ctx.ellipse(-2.4, -39, 1.6, 0.9, 0, 0, TAU); ctx.ellipse(2.4, -39, 1.6, 0.9, 0, 0, TAU); }); ctx.restore(); }
  }
  function treant(ctx, h, show) {
    // 樹人：樹幹身體、根腳、枝臂；葉子混入主色
    const bark = "#6a4a2a", bd = dark(bark), leaf = mix("#4a8a3a", h, 0.35);
    for (const x of [-5, 5]) poly(ctx, bd, [[x - 3, -14], [x + 3, -14], [x + 4, 0], [x - 4, 0]]);
    fill(ctx, bark, () => ctx.roundRect(-8, -38, 16, 26, 4));
    for (const y of [-32, -25, -18]) line(ctx, bd, 1, [[-5, y], [-2, y + 3]]);
    line(ctx, bark, 3.4, [[-8, -32], [-15, -26], [-16, -18]]); line(ctx, bark, 3.4, [[8, -32], [15, -27], [17, -20]]);
    for (const [x, y, r] of [[-6, -44, 7], [5, -45, 7.5], [0, -50, 6.5], [-14, -28, 4], [16, -29, 4]]) fill(ctx, leaf, () => ctx.arc(x, y, r, 0, TAU));
    fill(ctx, mix(leaf, "#ffffff", 0.2), () => ctx.arc(2, -48, 3, 0, TAU));
    if (show) fill(ctx, "#ffe9a0", () => { ctx.arc(-2.4, -32, 1.2, 0, TAU); ctx.arc(2.4, -32, 1.2, 0, TAU); });
  }

  // 形態 → 畫法、和同類召喚物比的大小（大一號）
  const FORMS = {
    bear: { zh: "熊", draw: bear, size: 1.3, vs: "戰狼（1.0）" },
    cat: { zh: "貓", draw: cat, size: 1.25, vs: "戰狼（1.0）" },
    roc: { zh: "鳥", draw: roc, size: 1.2, vs: "鷹隼（0.8）" },
    demon: { zh: "惡魔", draw: demon, size: 1.2, vs: "影魅（1.0）" },
    giant: { zh: "巨人", draw: giant, size: 1.45, vs: "石像（1.25）" },
    avatar: { zh: "元素化身", draw: avatar, size: 1.2, vs: "元素之靈（1.0）" },
    shadow: { zh: "暗影形態", draw: shadowForm, size: 1.2, vs: "影魅（1.0）" },
    treant: { zh: "樹人", draw: treant, size: 1.3, vs: "藤蔓（1.0）" },
    werewolf: { zh: "狼人", draw: wolfman, size: 1.25, vs: "戰狼（1.0）" },
    dragon: { zh: "龍", draw: dragon, size: 1.5, vs: "（無同類）" },
  };

  /** 畫一個形態（cx, cy＝腳底）；回傳 false 表示不認得（呼叫端退回原角色）。 */
  function stamp(ctx, spec, facing, cx, cy, k = 1) {
    const f = FORMS[spec.id];
    if (!f) return false;
    const size = f.size * k, S = 80, dpr = 3;
    const off = document.createElement("canvas"); off.width = S * size * dpr; off.height = S * size * dpr;
    const o = off.getContext("2d"); o.scale(size * dpr, size * dpr); o.translate(S / 2, S - 8);
    if (facing === "west") o.scale(-1, 1);
    f.draw(o, spec.hero ?? "#5aa0ff", facing !== "north", spec.element);
    const sil = document.createElement("canvas"); sil.width = off.width; sil.height = off.height;
    const sc = sil.getContext("2d"); sc.drawImage(off, 0, 0); sc.globalCompositeOperation = "source-in"; sc.fillStyle = INK; sc.fillRect(0, 0, sil.width, sil.height);
    const dx = cx - (S / 2) * size, dy = cy - (S - 8) * size, kk = 1.2 * size;
    // 地面影子（不進外框層）
    ctx.save(); ctx.fillStyle = "rgba(0,0,0,0.3)"; ctx.beginPath(); ctx.ellipse(cx, cy - 1, 13 * size, 3.6 * size, 0, 0, TAU); ctx.fill(); ctx.restore();
    for (const [ox, oy] of [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [1, -1], [-1, 1], [1, 1]]) ctx.drawImage(sil, dx + ox * kk, dy + oy * kk, S * size, S * size);
    ctx.drawImage(off, dx, dy, S * size, S * size);
    return true;
  }
  return { stamp, FORMS, ELEM };
})();
