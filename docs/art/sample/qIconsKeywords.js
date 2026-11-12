// qIconsKeywords.js：「小圖示改 Q 版」第⑤b 批——裝備圖示上的關鍵字小圖樣（12 個：元素 4＋非元素 8）（畫圖 agent 2026-11-12）。
// 規則：docs/art/Q版小圖示樣張.md 第 2 節；紀錄：docs/art/Q版小圖示-第5b批關鍵字.md；樣張頁：q-icons-keywords.html。
// 現行（client/src/render/gearIcon.ts 的 motif()）：關鍵字色的細線小圖（線寬 1.6／64 格），>36px 才畫，畫在器物上兩處（meta.spots；每個關鍵字一處、只有一個時兩處），
//   疊在 Q 版圖上偏細、像刮痕。這裡改成「角落的關鍵字小圓章」：染關鍵字色的深色圓底（外圈 1 裝置像素外框色）＋Q 版圖樣（圖樣全部直接呼叫第 3～5 批已畫的形，src 寫在清單），
//   每個關鍵字一個圓章（最多兩個），放在圖樣蓋得最少的角（cornersOf：量出來的；45° 斜放的武器與槍是右下、左上；右上角留給稀有度色塊與作用端，不放）。
// 色：關鍵字色照 client/src/render/palette.ts 的 KEYWORD_COLOR（圓底混 28%）；圖樣的顏色照它原本那一批（元素是主色＋亮色＋白芯三層）。
// 依賴（先載入）：qIcons.js、qIconsWeapons.js（blit）、qIconsSkills.js（ELEMENT、ACT）、qIconsParts.js（entry）、qIconsStatus.js（沒有直接用，撞圖頁要）。
window.QIconsKeywords = (() => {
  const Q = window.QIcons, QW = window.QIconsWeapons, QS = window.QIconsSkills, QP = window.QIconsParts, TAU = Math.PI * 2, OUT = Q.OUT;
  /** palette.ts 的 KEYWORD_COLOR（元素關鍵字＝元素色；水＝WATER_COLOR）。 */
  const KC = { ignite: "#ff6a1a", wet: "#4aa8ff", charged: "#fff36b", frozen: "#8fe3ff", prone: "#e0b080", collision: "#ff9a4a", marked: "#d06aff", high_ground: "#ffe9a8", concealed: "#a0a0c8", summon: "#7dffb0", poisoned: "#7ad04a", form: "#e0a35a" };
  const ELEMENT_KW = ["ignite", "wet", "charged", "frozen"];
  /** 畫在 48 格的既有圖樣：縮到 ±10 單位的座標裡（同 qIconsParts.js 的 from48）。 */
  const from48 = (d, k = 0.47) => (c, o) => { c.save(); c.scale(k, k); c.translate(-24, -24); d(c, { ...o, small: true }); c.restore(); };
  const part = (cat, id) => (c, o) => QP.entry(cat, id).d(c, o);
  const act = (id) => (c, o) => QS.ACT[id].d(c, o, QS.ACT[id].def ?? ["#ffd23f", "#ffffff"]);
  /** 12 個關鍵字（順序同 gearAppearance.json 的 keywords）。k＝圖樣在圓章裡再縮放（方的、四角有東西的收進環內）；src＝沿用哪一批的哪個形。 */
  const LIST = {
    ignite: { zh: "點燃", topic: "火焰（橘外焰、黃內焰、白芯）", src: "b3:el:fire＝b4:element.fire", k: 1.04, d: from48(QS.ELEMENT.fire.d) },
    wet: { zh: "潮濕", topic: "水滴落在兩道波浪上（藍、淺藍、白芯）", src: "b3:el:water", k: 0.85, d: from48(QS.ELEMENT.water.d) },
    charged: { zh: "帶電", topic: "黃閃電（黃、橘暗面、白亮邊）", src: "b3:el:lightning＝b4:element.lightning", k: 1.02, d: from48(QS.ELEMENT.lightning.d) },
    frozen: { zh: "冰凍", topic: "三根冰晶（淡藍、深藍暗面、白亮面）", src: "b3:el:ice＝b4:element.ice", k: 1, d: from48(QS.ELEMENT.ice.d) },
    prone: { zh: "倒地", topic: "黃色撞擊星壓在地面線上", src: "b3:knockdown＝b4:effect.knock_prone", k: 0.74, d: act("knockdown") },
    collision: { zh: "撞擊", topic: "米白三角撞上右邊的石牆，中間一顆撞擊星", src: "b4:trigger.on_collision", k: 0.76, d: part("trigger", "on_collision") },
    marked: { zh: "標記", topic: "紅色準星", src: "b3:mark＝b4:status.marked＝b5:marked", k: 0.85, d: act("mark") },
    high_ground: { zh: "高地", topic: "一座灰石山，山頂一個米白小人頭", src: "b4:condition.height_advantage", k: 0.73, d: part("condition", "height_advantage") },
    concealed: { zh: "隱蔽", topic: "紫色兜帽，裡面兩道發亮的斜眼", src: "b4:status.concealed＝b5:concealed", k: 0.84, d: part("status", "concealed") },
    summon: { zh: "召喚", topic: "青色小靈", src: "b3:summon＝b4:effect.summon", k: 1, d: act("summon") },
    poisoned: { zh: "中毒", topic: "綠毒滴，右上一顆泡", src: "b3:el:poison＝b4:status.poison＝b5:poison", k: 0.96, d: part("status", "poison") },
    form: { zh: "形態", topic: "淡紫色的獸掌印", src: "b4:effect.enter_form", k: 0.94, d: part("effect", "enter_form") },
  };
  const KEYS = Object.keys(LIST);
  const BOX = 48 / 36; /* 圖樣格邊長＝圖樣本身（±10 單位）的 1.333 倍（同 qIconsParts.js） */
  /** 只有圖樣的 canvas：cpx＝圖樣本身（±10 單位）顯示的 CSS px；≤14px 不包外框（規則 8）。 */
  function glyph(kw, cpx, res = 2, opt = {}) {
    const e = LIST[kw]; return Q.render({ d: (c, o) => { c.save(); c.translate(24, 24); c.scale(1.8, 1.8); e.d(c, { ...o, small: cpx <= 24, tiny: cpx <= 14 }); c.restore(); } }, cpx * BOX, res, { ow: opt.ow ?? (cpx <= 14 ? 0 : Q.outlinePx(cpx)) });
  }
  /** 圓章的大小（CSS px）：裝備格邊長的 0.42（32→13.5、42→17.5、48→20、64→27，真 1 倍取整數），對齊整數裝置像素。樣張頁 ?part=lab 比過 0.375 與有環／沒有環。 */
  const RATIO = 0.42, MARGIN = 3.6 / 64; /* 離格邊：現行框線（2～62、線寬 2.5）內緣以內 */
  const sizeOf = (S, res, ratio = RATIO) => Math.round(S * ratio * res) / res;
  /** 圓章的幾何：最外一圈 1 個裝置像素的外框色；預設沒有環（ring＝true 時環寬 max(1, 半徑×0.14) CSS px，只給比較用）；圖樣收在內緣以內。 */
  function geom(D, res, ring = false) { const ow = 1 / res, lw = ring ? Math.max(1, (D / 2) * 0.14) : 0, inner = D - 2 * ow - 2 * lw; return { ow, lw, inner }; }
  /** 圓底：深色混 28% 關鍵字色（真 1 倍時圓章只有 13px，環會吃掉 2px，改成把關鍵字色染在圓底上；opt.tint＝false 是不染的深色，比較用）。 */
  const bgOf = (kw, opt = {}) => (opt.tint === false ? "#191b22" : Q.H.mix(KC[kw], "#191b22", 0.72));
  /** 在 (x0,y0) 左上角畫一個直徑 D 的關鍵字圓章（ctx 每單位＝1 CSS px、已乘 res；x0、y0 要在整數裝置像素上）。 */
  function chip(ctx, kw, x0, y0, D, res, opt = {}) {
    const e = LIST[kw]; if (!e) return; const { ow, lw, inner } = geom(D, res, opt.ring === true), cx = x0 + D / 2, cy = y0 + D / 2;
    ctx.save();
    ctx.fillStyle = OUT; ctx.beginPath(); ctx.arc(cx, cy, D / 2, 0, TAU); ctx.fill();
    ctx.fillStyle = opt.bg ?? bgOf(kw, opt); ctx.beginPath(); ctx.arc(cx, cy, D / 2 - ow, 0, TAU); ctx.fill();
    if (opt.ring === true) { ctx.strokeStyle = KC[kw]; ctx.lineWidth = lw; ctx.beginPath(); ctx.arc(cx, cy, D / 2 - ow - lw / 2, 0, TAU); ctx.stroke(); }
    ctx.restore();
    const cpx = inner * (e.k ?? 1) * (opt.gk ?? 1), g = glyph(kw, cpx, res, opt), a = cpx * BOX;
    QW.blit(ctx, g, cx - a / 2, cy - a / 2, a, res);
  }
  /** 只留認得的關鍵字（同遊戲端 resolveGear：KEYWORD_COLOR 認得的、前 2 個）。 */
  const known = (kws) => (kws ?? []).filter((k) => LIST[k]).slice(0, 2);
  /** 圓章放在哪個角：右下 br、左上 tl、左下 bl（右上角留給稀有度色塊，不放）。 */
  const CORNERS = ["br", "tl", "bl"];
  const at = (corner, size, D, res) => { const m = size * MARGIN, snap = (v) => Math.round(v * res) / res, far = snap(size - m - D), near = snap(m); return [corner[1] === "r" ? far : near, corner[0] === "b" ? far : near]; };
  const cornerMemo = new WeakMap();
  /** 塊狀的東西「最好認的那一頭」在哪個角（量蓋住多少時這個角的像素算 3 倍）：鞋靴的鞋尖朝右下、戒指的戒面在上面、角盔的角在左上。斜放的長條與槍不用寫（作用端那一半另算）。 */
  const KEY_CORNER = { shoes: "br", boots: "br", iron_boots: "br", greaves: "br", ring: "tl", "helmet/horned": "tl" };
  /** ≤ 這個邊長（CSS px）只畫第一個關鍵字（同現行的 SMALL_ICON_MAX_PX：裝備格 32 放兩個圓章會蓋掉塊狀圖樣的四成）。 */
  const ONE_MAX_PX = 36;
  /** 這一款的圓章放哪兩個角：量圖樣（裝備格 32——只畫一個圓章的最小尺寸、不含外框，4 倍解析度）被每個角的圓章蓋住多少，挑蓋得最少的兩個角（第一個關鍵字放最少的那個）；KEY_CORNER 的角算 3 倍。
   *  45° 斜放的長條（meta.diag）與槍：先比作用端那一半（右上半：x>y）被蓋住多少（5% 一級），再比全部，不讓圓章蓋到最好認的那一頭。蓋住的量相差不到 2% 時照 右下＞左上＞左下 的順序（斜放的長條兩個空角就是右下、左上）。
   *  def＝QIconsWeapons.def()／QIconsArmor.def() 的結果；沒給就照預設順序。 */
  function cornersOf(def) {
    if (!def) return CORNERS; if (cornerMemo.has(def)) return cornerMemo.get(def);
    const S = 32, R = 4, p = S * QW.GEAR_PAD, a = S - 2 * p, art = Q.render({ d: def.d }, a, R, { ow: 0 }), W = art.width, d = art.getContext("2d").getImageData(0, 0, W, W).data, D = sizeOf(S, 2);
    const R0 = def.meta?.r ?? {}, r = (k) => R0.kind === k, diag = !!def.meta?.diag || r("longgun") || r("shotgun"), key = KEY_CORNER[R0.kind + "/" + R0.form] ?? KEY_CORNER[R0.kind], cost = { br: 0, tl: 0, bl: 0 }, head = { br: 0, tl: 0, bl: 0 }; let all = 0, heads = 0;
    const cs = CORNERS.map((c) => { const [x0, y0] = at(c, S, D, 2); return [c, x0 + D / 2, y0 + D / 2]; });
    for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) { if (d[(y * W + x) * 4 + 3] < 128) continue; const hd = diag && x > y, wgt = 1; all += wgt; if (hd) heads++; const px = p + (x + 0.5) / R, py = p + (y + 0.5) / R;
      for (const [c, cx, cy] of cs) if (Math.hypot(px - cx, py - cy) <= D / 2) { cost[c] += c === key ? 3 * wgt : wgt; if (hd) head[c]++; } }
    const q = (c) => Math.floor((cost[c] / Math.max(1, all)) * 50); /* 2% 一級 */
    const qh = (c) => Math.floor((head[c] / Math.max(1, heads)) * 20); /* 作用端 5% 一級：擦到邊（<5%）當作沒蓋到，再比全部 */
    const out = [...CORNERS].sort((A, B) => qh(A) - qh(B) || q(A) - q(B) || CORNERS.indexOf(A) - CORNERS.indexOf(B)); out.pct = Object.fromEntries(CORNERS.map((c) => [c, [Math.round((cost[c] / Math.max(1, all)) * 1000) / 10, Math.round((head[c] / Math.max(1, heads)) * 1000) / 10]])); cornerMemo.set(def, out); return out;
  }
  /** 裝備格上的關鍵字層：size＝裝備格邊長（CSS px），ctx 每單位＝1 CSS px、已乘 res。每個關鍵字一個圓章，角照 cornersOf(opt.def)；≤36px 只畫第一個（opt.both＝true 時兩個都畫，比較用），>36px 最多兩個；opt.one＝只畫第一個；opt.min＝這個邊長以下不畫。 */
  function paint(ctx, keywords, size, res, opt = {}) {
    const kws = known(keywords); if (!kws.length || size <= (opt.min ?? 0)) return;
    const D = sizeOf(size, res, opt.ratio), cs = cornersOf(opt.def);
    kws.slice(0, count(size, opt)).forEach((kw, i) => { const [x0, y0] = at(cs[i], size, D, res); chip(ctx, kw, x0, y0, D, res, opt); });
  }
  const count = (size, opt) => (opt.one || (size <= ONE_MAX_PX && !opt.both) ? 1 : 2);
  /** 圓章蓋住的區域（給自查量「蓋住主圖幾成」）：[{ cx, cy, r, corner }]（CSS px）。 */
  function areas(keywords, size, res, opt = {}) { const kws = known(keywords), D = sizeOf(size, res, opt.ratio), cs = cornersOf(opt.def);
    return kws.slice(0, count(size, opt)).map((kw, i) => { const [x0, y0] = at(cs[i], size, D, res); return { cx: x0 + D / 2, cy: y0 + D / 2, r: D / 2, corner: cs[i] }; }); }
  /** 單獨一個圓章的 canvas（px 邊長、圓章撐滿）。 */
  function chipCanvas(kw, px, zoom = 1, o = {}) { const res = o.res ?? (zoom === 1 ? 2 : zoom), cv = Q.H.blank(Math.round(px * res)); cv.style.width = cv.style.height = px * zoom + "px"; const x = cv.getContext("2d"); x.scale(res, res); chip(x, kw, 0, 0, px, res, o); return cv; }

  /** 現行的 motif()（client/src/render/gearIcon.ts 原樣，64 單位；12 個關鍵字都有）。樣張頁「現行」那一欄用，不是這一批的畫法。 */
  function legacy(ctx, kw, x, y) {
    const kc = KC[kw]; if (kc === undefined) return; ctx.save(); ctx.fillStyle = kc; ctx.strokeStyle = kc; ctx.lineWidth = 1.6; ctx.lineCap = "round";
    switch (kw) {
      case "ignite": ctx.beginPath(); ctx.moveTo(x, y - 6); ctx.quadraticCurveTo(x + 4.5, y, x, y + 3); ctx.quadraticCurveTo(x - 4.5, y, x, y - 6); ctx.fill(); break;
      case "wet": ctx.beginPath(); ctx.moveTo(x, y - 5); ctx.quadraticCurveTo(x + 4, y + 1, x, y + 3); ctx.quadraticCurveTo(x - 4, y + 1, x, y - 5); ctx.fill(); break;
      case "charged": ctx.beginPath(); ctx.moveTo(x - 3, y - 5); ctx.lineTo(x + 1, y - 1); ctx.lineTo(x - 1, y + 1); ctx.lineTo(x + 3, y + 5); ctx.stroke(); break;
      case "frozen": ctx.beginPath(); for (let i = 0; i < 3; i++) { const a = (i * Math.PI) / 3; ctx.moveTo(x - Math.cos(a) * 4.5, y - Math.sin(a) * 4.5); ctx.lineTo(x + Math.cos(a) * 4.5, y + Math.sin(a) * 4.5); } ctx.stroke(); break;
      case "prone": ctx.beginPath(); ctx.moveTo(x - 4, y - 2); ctx.lineTo(x, y + 2); ctx.lineTo(x + 4, y - 2); ctx.stroke(); ctx.beginPath(); ctx.moveTo(x - 4, y + 2); ctx.lineTo(x + 4, y + 2); ctx.stroke(); break;
      case "collision": ctx.beginPath(); for (let i = 0; i < 8; i++) { const a = (i / 8) * TAU, r = i % 2 ? 2 : 5; ctx.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r); } ctx.closePath(); ctx.fill(); break;
      case "marked": ctx.beginPath(); ctx.arc(x, y, 3.5, 0, TAU); ctx.stroke(); ctx.beginPath(); ctx.moveTo(x - 6, y); ctx.lineTo(x - 4, y); ctx.moveTo(x + 4, y); ctx.lineTo(x + 6, y); ctx.moveTo(x, y - 6); ctx.lineTo(x, y - 4); ctx.moveTo(x, y + 4); ctx.lineTo(x, y + 6); ctx.stroke(); break;
      case "high_ground": ctx.beginPath(); ctx.moveTo(x - 4, y + 2); ctx.lineTo(x, y - 3); ctx.lineTo(x + 4, y + 2); ctx.stroke(); break;
      case "concealed": ctx.globalAlpha = 0.85; ctx.beginPath(); ctx.arc(x - 2, y, 2.6, 0, TAU); ctx.arc(x + 2, y - 1, 3, 0, TAU); ctx.arc(x + 1, y + 2, 2.2, 0, TAU); ctx.fill(); break;
      case "poisoned": ctx.beginPath(); ctx.arc(x, y - 1, 3.2, 0, TAU); ctx.fill(); ctx.beginPath(); ctx.moveTo(x - 2.5, y + 3); ctx.lineTo(x + 2.5, y + 6); ctx.moveTo(x + 2.5, y + 3); ctx.lineTo(x - 2.5, y + 6); ctx.stroke(); break;
      case "form": ctx.beginPath(); for (let i = -1; i <= 1; i++) { ctx.moveTo(x + i * 3 - 1.5, y - 5); ctx.lineTo(x + i * 3 + 1.5, y + 5); } ctx.stroke(); break;
      case "summon": ctx.beginPath(); ctx.arc(x, y - 1, 3.4, Math.PI, 0); ctx.lineTo(x + 3.4, y + 4); ctx.lineTo(x + 1.2, y + 2.5); ctx.lineTo(x, y + 4); ctx.lineTo(x - 1.2, y + 2.5); ctx.lineTo(x - 3.4, y + 4); ctx.closePath(); ctx.fill(); break;
    }
    ctx.restore();
  }
  /** 現行遊戲端（QI-1a 之後）的關鍵字層：>36px 才畫，位置用 Q 版的 meta.spots（48 格）換算到格內，motif() 原大（64 單位）；每個關鍵字一處、只有一個時兩處。
   *  spots＝def().meta.spots；size＝裝備格邊長（CSS px）。k＝縮放（樣張示意的 0.75 傳 0.75）。 */
  function paintLegacy(ctx, keywords, spots, size, opt = {}) {
    const kws = known(keywords); if (!kws.length || size <= (opt.min ?? 36)) return;
    const p = size * QW.GEAR_PAD, a = size - 2 * p, k = (size / 64) * (opt.k ?? 1), at = (kw, s) => { ctx.save(); ctx.translate(p + (s[0] * a) / 48, p + (s[1] * a) / 48); ctx.scale(k, k); legacy(ctx, kw, 0, 0); ctx.restore(); };
    kws.forEach((kw, i) => at(kw, spots[i % spots.length])); if (kws.length === 1 && spots[1]) at(kws[0], spots[1]);
  }
  return { KC, ELEMENT_KW, LIST, KEYS, BOX, RATIO, MARGIN, CORNERS, KEY_CORNER, ONE_MAX_PX, cornersOf, sizeOf, geom, bgOf, glyph, chip, chipCanvas, paint, areas, known, legacy, paintLegacy };
})();
