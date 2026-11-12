// qIconsKeywords.js：「小圖示改 Q 版」第⑤b 批——裝備圖示上的關鍵字小圖樣（12 個：元素 4＋非元素 8）（畫圖 agent 2026-11-12）。
// 規則：docs/art/Q版小圖示樣張.md 第 2 節；紀錄：docs/art/Q版小圖示-第5b批關鍵字.md；樣張頁：q-icons-keywords.html。
// 現行（client/src/render/gearIcon.ts 的 motif()）：關鍵字色的細線小圖（線寬 1.6／64 格），>36px 才畫，畫在器物上兩處（meta.spots；每個關鍵字一處、只有一個時兩處），
//   疊在 Q 版圖上偏細、像刮痕。這裡改成「角落的關鍵字小圓章」：染關鍵字色的深色圓底（外圈 1 裝置像素外框色）＋Q 版圖樣（圖樣全部直接呼叫第 3～5 批已畫的形，src 寫在清單），
//   每個關鍵字一個圓章：第 2 版定案——第一個一律右下，右下會蓋到主圖最好認的那一頭時照例外表 KEY_CORNER 換角；≤36px 一個，>36px 斜放的單把長條兩個（第二個左上）、其他一個；右上角留給稀有度色塊與作用端，不放。
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
  /** 第 2 版：撞擊在圖樣 ≤14px（圓章 13、18——裝備格 32、背包格 42）只留一個主體（規則 8）：撞上石牆、炸開的一顆大撞擊星，三角拿掉。
   *  同題材（第 4 批觸發「造成撞擊後」的牆與撞擊星，色與形照抄：qIconsParts.js 的 wall()、burstStar()，那兩個沒有匯出），>14px 照舊呼叫第 4 批。
   *  ≤14px 不包外框，星和牆靠亮度分：牆用暗石色（STONE_D）、左緣一條亮石邊，星是亮黃＋白芯，壓在牆的左緣上。
   *  第 3 版（複審：和倒地都是一顆大黃星）：牆加厚到右半個圓（寬 9.6），星縮小（外徑 9.4→7.8）、往左上移到牆左緣的上半——主體變成「牆」，和倒地「大星壓在地面上」拉開。題材不變。 */
  const COLLIDE_STONE_D = "#8c8474", COLLIDE_STONE_L = "#ece6d6";
  const collision = (c, o) => {
    if (!o.tiny) { QP.entry("trigger", "on_collision").d(c, o); return; }
    const { rr, f, poly, starPts } = Q.H;
    rr(c, COLLIDE_STONE_D, 0.8, -10.4, 9.6, 20.8, 1.6); f(c, COLLIDE_STONE_L, () => c.rect(0.8, -9.4, 2, 18.8));
    poly(c, "#ffd23f", starPts(-2.4, -2.8, 7.8, 3.7, 7, -1.2), 0.3); poly(c, "#ffffff", starPts(-2.4, -2.8, 3.7, 1.9, 7, -1.2));
  };
  /** 12 個關鍵字（順序同 gearAppearance.json 的 keywords）。k＝圖樣在圓章裡再縮放（方的、四角有東西的收進環內）；src＝沿用哪一批的哪個形。 */
  const LIST = {
    ignite: { zh: "點燃", topic: "火焰（橘外焰、黃內焰、白芯）", src: "b3:el:fire＝b4:element.fire", k: 1.04, d: from48(QS.ELEMENT.fire.d) },
    wet: { zh: "潮濕", topic: "水滴落在兩道波浪上（藍、淺藍、白芯）", src: "b3:el:water", k: 0.85, d: from48(QS.ELEMENT.water.d) },
    charged: { zh: "帶電", topic: "黃閃電（黃、橘暗面、白亮邊）", src: "b3:el:lightning＝b4:element.lightning", k: 1.02, d: from48(QS.ELEMENT.lightning.d) },
    frozen: { zh: "冰凍", topic: "三根冰晶（淡藍、深藍暗面、白亮面）", src: "b3:el:ice＝b4:element.ice", k: 1, d: from48(QS.ELEMENT.ice.d) },
    prone: { zh: "倒地", topic: "黃色撞擊星壓在地面線上", src: "b3:knockdown＝b4:effect.knock_prone", k: 0.74, d: act("knockdown") }, /* 第 2 版試過換成狀態「倒地」的趴地人形（審查可修 2）：圖樣 ≤14px 只剩米白一塊加鼓包，像麵包、床，不採用（q-icons-keywords.html?part=v2&set=glyph 最下一列） */
    collision: { zh: "撞擊", topic: "米白三角撞上右邊的石牆，中間一顆撞擊星（圖樣 ≤14px：只留石牆＋撞上去的大撞擊星）", src: "b4:trigger.on_collision（≤14px 簡化形）", k: 0.76, d: collision },
    marked: { zh: "標記", topic: "紅色準星", src: "b3:mark＝b4:status.marked＝b5:marked", k: 0.85, d: act("mark") },
    high_ground: { zh: "高地", topic: "一座淺石色的山（左坡米白亮面），山頂一個米白小人頭；圖樣 >14px 右上多一個黃箭頭", src: "b4:condition.height_advantage", k: 0.73, d: part("condition", "height_advantage") },
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
  const coverMemo = new WeakMap();
  /** 第 2 版（美術 PM 定案）：位置照表，不再量了挑最少。
   *  預設：第一個圓章一律右下（br）。45° 斜放的單把長條（meta.diag 與長槍、霰彈槍）右下、左上兩個角本來就空，>36px 第二個放左上（tl）；其他一律只有一個。
   *  KEY_CORNER＝例外表：右下會蓋到主圖最好認的那一頭（或第二個會蓋到）的款，直接寫要放的角（陣列＝第一個、第二個；只寫一個＝只畫一個圓章）。
   *  先找 kind/form，再找 kind。表裡每一列的理由寫在旁邊；數字是 --audit keywords 印的「裝備格 32 這個角的圓章蓋住圖樣%／作用端%」。 */
  const KEY_CORNER = {
    axe: ["tl"], /* 斧刃在右下（手斧右下蓋作用端 11%、戰斧 16%）；左上是柄頭外的空處。雙刃斧兩片刃上下對稱，同一種一起放左上 */
    "hammer/flail": ["bl"], /* 錘頭甩在右下（右下蓋作用端 39%），左上也擦到鍊（5%）→ 左下的握把 */
    "scythe/crescent": ["tl"], /* 月牙刃在右下（22%） */
    bow: ["bl"], /* 弓臂伸到右下、左上兩個角（各蓋 15～19%）→ 左下的握把；第二個沒有不蓋弓臂的角，只畫一個 */
    crossbow: ["bl"], /* 同弓：弩臂在右下、左上 → 左下的弩托 */
    shoes: ["tl"], boots: ["tl"], iron_boots: ["tl"], greaves: ["tl"], /* 鞋尖朝右下（右下蓋 70%～94%）→ 左上的鞋筒口（四種鞋同一個角） */
    pendant: ["tl"], /* 墜子（寶石）在右下 → 左上的鍊子 */
    "circlet/bandana": ["bl"], /* 第 3 版（複審必修）：右下垂的頭巾結是唯一的辨識點，右下蓋掉後讀成圓頂帽 → 左下（6.9%） */
    cloth_gloves: ["bl"], leather_gloves: ["bl"], gauntlets: ["bl"], /* 第 3 版（複審可修）：右下壓掌根與拇指（28%～31.5%）→ 左下只蓋護腕下緣（15%～19%），拇指留著 */
    "charm/bone": ["bl"], /* 看圖加的：大獠牙的尖朝右下（右下蓋 22%、蓋掉牙尖）→ 左下的小獠牙（9%） */
    "dual_dagger/short": ["br"], "dual_dagger/stiletto": ["br"], /* 必修 1：X 交叉，左上是後面那把的刃，不放；右下蓋前面那把的握把 */
    "dual_pistol/flintlock": ["br"], "dual_pistol/revolver": ["br"], "dual_pistol/derringer": ["br"], /* 必修 2：同上，左上是左邊那把的槍口 */
    whip: ["br"], /* 斜放單把，但甩出去的鞭梢在左上（左上蓋作用端 22%～30%）：只畫一個 */
    "longgun/sniper": ["br"], /* 斜放單把，但槍管長到左上（左上蓋作用端 24%）：只畫一個 */
  };
  /** ≤ 這個邊長（CSS px）只畫一個圓章（裝備格 32；同現行的 SMALL_ICON_MAX_PX 36 這條線）。 */
  const ONE_MAX_PX = 36;
  const lookOf = (def) => def?.meta?.r ?? {};
  /** 斜放的單把長條（第二個圓章放左上的那一類）。 */
  const isDiag = (def) => { const r = lookOf(def); return !!def?.meta?.diag || r.kind === "longgun" || r.kind === "shotgun"; };
  /** 這一款的圓章放哪幾個角（第一個關鍵字放第一個角）：例外表 → 斜放單把 [br, tl] → 其他 [br]。def＝QIconsWeapons.def()／QIconsArmor.def() 的結果；沒給就 [br, tl]。 */
  function cornersOf(def) {
    if (!def) return ["br", "tl"]; const r = lookOf(def);
    return KEY_CORNER[r.kind + "/" + r.form] ?? KEY_CORNER[r.kind] ?? (isDiag(def) ? ["br", "tl"] : ["br"]);
  }
  /** 自查用：裝備格 32（只畫一個圓章的最小尺寸、不含外框，4 倍解析度）每個角的圓章蓋住圖樣多少、斜放的作用端那一半（右上半：x>y）蓋住多少：{ br: [%, %], tl, bl }。不影響放哪裡。 */
  function coverOf(def) {
    if (coverMemo.has(def)) return coverMemo.get(def);
    const S = 32, R = 4, p = S * QW.GEAR_PAD, a = S - 2 * p, art = Q.render({ d: def.d }, a, R, { ow: 0 }), W = art.width, d = art.getContext("2d").getImageData(0, 0, W, W).data, D = sizeOf(S, 2), diag = isDiag(def), cost = { br: 0, tl: 0, bl: 0 }, head = { br: 0, tl: 0, bl: 0 }; let all = 0, heads = 0;
    const cs = CORNERS.map((c) => { const [x0, y0] = at(c, S, D, 2); return [c, x0 + D / 2, y0 + D / 2]; });
    for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) { if (d[(y * W + x) * 4 + 3] < 128) continue; const hd = diag && x > y; all++; if (hd) heads++; const px = p + (x + 0.5) / R, py = p + (y + 0.5) / R;
      for (const [c, cx, cy] of cs) if (Math.hypot(px - cx, py - cy) <= D / 2) { cost[c]++; if (hd) head[c]++; } }
    const out = Object.fromEntries(CORNERS.map((c) => [c, [Math.round((cost[c] / Math.max(1, all)) * 1000) / 10, Math.round((head[c] / Math.max(1, heads)) * 1000) / 10]])); coverMemo.set(def, out); return out;
  }
  /** 裝備格上的關鍵字層：size＝裝備格邊長（CSS px），ctx 每單位＝1 CSS px、已乘 res。每個關鍵字一個圓章，角照 cornersOf(opt.def)；≤36px 一個，>36px 最多 cornersOf 的個數（斜放單把兩個、其他一個）；opt.one＝只畫第一個；opt.min＝這個邊長以下不畫；opt.cs＝指定角（樣張頁畫第 1 版對照用）。 */
  function paint(ctx, keywords, size, res, opt = {}) {
    const kws = known(keywords); if (!kws.length || size <= (opt.min ?? 0)) return;
    const D = sizeOf(size, res, opt.ratio), cs = opt.cs ?? cornersOf(opt.def);
    kws.slice(0, count(size, cs, opt)).forEach((kw, i) => { const [x0, y0] = at(cs[i], size, D, res); chip(ctx, kw, x0, y0, D, res, opt); });
  }
  const count = (size, cs, opt) => (opt.one || size <= ONE_MAX_PX ? 1 : cs.length);
  /** 圓章蓋住的區域（給自查量「蓋住主圖幾成」）：[{ cx, cy, r, corner }]（CSS px）。 */
  function areas(keywords, size, res, opt = {}) { const kws = known(keywords), D = sizeOf(size, res, opt.ratio), cs = opt.cs ?? cornersOf(opt.def);
    return kws.slice(0, count(size, cs, opt)).map((kw, i) => { const [x0, y0] = at(cs[i], size, D, res); return { cx: x0 + D / 2, cy: y0 + D / 2, r: D / 2, corner: cs[i] }; }); }
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
  return { KC, ELEMENT_KW, LIST, KEYS, BOX, RATIO, MARGIN, CORNERS, KEY_CORNER, ONE_MAX_PX, cornersOf, coverOf, isDiag, sizeOf, geom, bgOf, glyph, chip, chipCanvas, paint, areas, known, legacy, paintLegacy };
})();
