// qIconsHud.js：「小圖示改 Q 版」全量重畫第 7 批——HUD（功能列、通用小圖、戰鬥工具鈕、資源小圖、設定標題、圖釘、區域紋章、源力小晶石圓點）。畫圖 agent 2026-11-12。
// 規則：docs/art/Q版小圖示樣張.md 第 2 節；紀錄：docs/art/Q版小圖示-第7批HUD.md；樣張頁：q-icons-hud.html。
// 清單以遊戲端為準（client/src/world/HudBarIcons.tsx、HudIcons.tsx、ui/BattleToolIcons.tsx、StatusCardParts.tsx、SettingsHead.tsx、HoverFloat.tsx、
// SkillCardGlyphs.tsx、CreateIcons.tsx、styles/float-card.css、status-card.css），盤點見紀錄第 1 節。
// 框不動（規則 13）：功能列的淺色圓底（HUD_BACKING）、區域紋章的六角金框、浮動卡的金色圓底照現行，只換裡面的圖。
// 和前幾批同題材的一律直接呼叫（src 欄寫出處）：風格樣張 qIcons.js 的 ART.hud（背包、移動、離開、AP、法力、耐力）、ART.item.gold（金幣）；
// 第 3 批 qIconsSkills.js 的 ACT.shield（護盾）；第 4 批 qIconsParts.js 的卡片小圖（AP、法力、源力、反應、延遲沙漏、缺點三角、圖釘）、
// 骨架徽章「打擊」（亮色斜劍）、晶石；第 5 批 qIconsStatus.js 的元素架勢紋章（冰的雪花、風的旋風）。
// 同一個題材只畫一份，大小兩形照規則 8（o.small＝≤24px、o.tiny＝≤14px；≤14px 不包外框）。
// 依賴（先載入）：qIcons.js、qIconsWeapons.js、qIconsSkills.js、qIconsParts.js、qIconsStatus.js。
window.QIconsHud = (() => {
  const Q = window.QIcons, QS = window.QIconsSkills, QW = window.QIconsWeapons, QP = window.QIconsParts, QT = window.QIconsStatus;
  const { mix, f, rr, ci, el, poly, ln, starPts, glow, flame, drop, halo, blank, HI, HI2 } = Q.H, TAU = Math.PI * 2, PI = Math.PI, OUT = Q.OUT;
  const CREAM = "#f2e6c8", GOLD = "#e8bb48", GOLD_L = "#fff0b0", GOLD_D = "#9c7420";
  const st = (c, col, w, fn, cap = "round") => { c.beginPath(); fn(c); c.strokeStyle = col; c.lineWidth = w; c.lineCap = cap; c.lineJoin = "round"; c.stroke(); };
  const at = (c, x, y, k, fn, rot = 0) => { c.save(); c.translate(x, y); c.rotate(rot); c.scale(k, k); fn(c); c.restore(); };
  /** ±10 單位的圖樣（第 3、4、5 批的記號、卡片小圖、紋章）放進 48 格：中心 24,24、放大 1.8×k（和第 4 批 def() 同一個倍率）。 */
  const b10 = (fn, k = 1) => (c, o) => at(c, 24, 24, 1.8 * k, (q) => fn(q, o));
  /** 48 格的圖樣縮到 ±10 單位（第 4 批 from48 的做法；資源小圖用卡片小圖的路徑畫）。 */
  const from48 = (d, k = 0.46) => (c, o) => at(c, 0, 0, k, (q) => { q.translate(-24, -24); d(q, o); });

  // ---------------- 共用零件 ----------------
  /** 新月：外圓（cx,cy,R）減去切圓（ix,iy,r）。 */
  function crescent(c, cx, cy, R, ix, iy, r) {
    const dx = ix - cx, dy = iy - cy, d = Math.hypot(dx, dy), al = Math.atan2(dy, dx), a = (R * R - r * r + d * d) / (2 * d), be = Math.acos(Math.max(-1, Math.min(1, a / R)));
    const t1 = al + be, t2 = al - be + TAU, p = (t) => [cx + Math.cos(t) * R, cy + Math.sin(t) * R], [x1, y1] = p(t1), [x2, y2] = p(t2);
    const g2 = Math.atan2(y2 - iy, x2 - ix), g1 = Math.atan2(y1 - iy, x1 - ix);
    const inside = (acw) => { let span = acw ? g2 - g1 : g1 - g2; span = ((span % TAU) + TAU) % TAU; const m = acw ? g2 - span / 2 : g2 + span / 2; return Math.hypot(ix + Math.cos(m) * r - cx, iy + Math.sin(m) * r - cy) < R; };
    c.moveTo(x1, y1); c.arc(cx, cy, R, t1, t2, false); c.arc(ix, iy, r, g2, g1, inside(true)); c.closePath();
  }
  /** 雲：三顆圓加平底。 */
  const cloud = (c, col, x, y, k = 1) => f(c, col, () => { c.arc(x - 9 * k, y + 2 * k, 7 * k, PI * 0.5, PI * 1.5); c.arc(x, y - 3 * k, 10 * k, PI * 1.05, PI * 1.95); c.arc(x + 9.5 * k, y + 2 * k, 7 * k, PI * 1.5, PI * 0.5); c.closePath(); });
  /** 齒輪（設定、版面、樞市紋章同一個形；T＝本色、亮面、暗面、洞）。 */
  const GEAR_STEEL = ["#b8c0cc", "#eef2f6", "#7d8794"];
  const gearArt = (c, o, T = GEAR_STEEL) => {
    for (let i = 0; i < 8; i++) at(c, 24, 24, 1, (q) => rr(q, T[0], -4.4, -21, 8.8, 10, 1.8), (i * PI) / 4 + PI / 8);
    ci(c, T[0], 24, 24, 15.2);
    f(c, T[1], () => { c.arc(24, 24, 15.2, PI * 0.95, PI * 1.62); c.arc(24, 24, 11.4, PI * 1.62, PI * 0.95, true); c.closePath(); });
    f(c, T[2], () => { c.arc(24, 24, 15.2, PI * 0.05, PI * 0.62); c.arc(24, 24, 11.4, PI * 0.62, PI * 0.05, true); c.closePath(); });
    ci(c, OUT, 24, 24, o.tiny ? 4.6 : 5.6); /* 洞裡墊外框色，空心才看得到（第 3 批學到的） */
  };
  /** 圖釘（第 4 批 qIconsParts.js 卡片小圖 pin 的形，原樣照抄：斜放、圓頭、梯形身、針；±10 單位）。B＝金頭（照浮動卡的金色）；ink＝深色剪影（放在金色圓底上）。 */
  const pinArt = (c, o, P) => at(c, 0, 0, 1, (q) => { ln(q, P.needle, 2.2, [[0, 2], [0, 10.6]]); poly(q, P.body, [[-3, -5], [3, -5], [5.8, 2.8], [-5.8, 2.8]], 0.6); rr(q, P.head, -5.4, -10.6, 10.8, 5.4, 2.2); if (P.hi && !o.tiny) f(q, P.hi, () => q.rect(-3.6, -9.6, 4.4, 1.2)); }, 0.6);
  const PIN = {
    a: { needle: "#c3ccd6", body: "#c8382e", head: "#f05a48" }, /* 第 4 批原樣（已釘紅頭） */
    off: { needle: "#9aa2ac", body: "#8a929c", head: "#b4bcc6" }, /* 第 4 批原樣（未釘灰鋼、55%） */
    b: { needle: "#c3ccd6", body: "#c8961e", head: "#ffd04a", hi: "#fff6c8" }, /* B：金頭（HoverFloat 已釘 #ffd04a） */
    ink: { needle: "#3a2c20", body: "#1c1712", head: "#2e241a", hi: "#7a6248" }, /* 浮動卡金色圓底上的深色圖釘（現行 ::after 的構圖） */
  };
  /** 子彈（直立；彈殼黃銅、彈頭銅色，風格樣張 qIcons.js 的 bullet() 同色，改成直立的一顆）。±10 單位。 */
  const bulletArt = (c, o) => { f(c, "#c27a48", () => { c.moveTo(-5.4, -1.6); c.quadraticCurveTo(-5.4, -10.6, 0, -11); c.quadraticCurveTo(5.4, -10.6, 5.4, -1.6); c.closePath(); }); rr(c, GOLD, -5.4, -2.4, 10.8, 11.2, 1.4); rr(c, GOLD_D, -6.2, 7.8, 12.4, 3, 1.2);
    f(c, "#fff0b0", () => c.rect(-3.8, -1.4, 2, 8.2)); if (!o.tiny) el(c, "#f0b088", -2.4, -6.4, 1.2, 2.6, 0.2); };
  /** 小晶石（源力）：第 4 批 crystal 原樣（±10 單位）。 */
  const crystal = (c, o) => QP.entry("card", "source").d(c, o);

  // =====================================================================
  // 圖示表。grp：bar 功能列｜gen 通用小圖｜tool 戰鬥工具鈕｜res 資源小圖｜set 設定標題｜crest 區域紋章｜pip 源力圓點｜pin 圖釘
  // live：現行那一欄怎麼畫（["bar","I"]＝QHudLive.bar、["hud",name]、["tool",name]、["settings",name]、["crest",region]、["card",id]＝cardGlyphCanvas、["stat",key]＝StatGlyph 的 SVG）
  // src：沿用出處（style:＝風格樣張、b3:／b4:／b5:＝第 3、4、5 批）；沒有 src 的是這批新畫。sizes：遊戲裡實際的大小（CSS px）。
  // =====================================================================
  const ICON = {
    // ---------------- 功能列 8（淺色圓底照現行；圖樣 74% 照風格樣張的背包） ----------------
    bar_I: { zh: "背包（I）", grp: "bar", live: ["bar", "I"], sizes: [35, 24], src: "style:hud.bag", topic: "褐色正面後背包：頂上一捲米色鋪蓋、淺褐翻蓋、金扣、兩側鼓出的側袋", d: (c, o) => Q.ART.hud.bag.d(c, o) },
    bar_K: { zh: "技能（K）", grp: "bar", live: ["bar", "K"], sizes: [35, 24], topic: "合起來的紫色厚書：深紫書脊兩道金箍、右邊露出米白書頁、封面正中一顆發光的淡紫菱形寶石（金座）",
      pre: (c, o) => glow(c, 24, 23, 15, "#b8a8ff", 0.55),
      d: (c, o) => { rr(c, "#3e2a80", 11, 6, 29, 37, 4); rr(c, "#f2e6c8", 14, 8.5, 27, 32, 2.6); if (!o.small) for (const y of [13, 19, 25, 31]) f(c, "#cdbb92", () => c.rect(38, y, 3, 1.4));
        rr(c, "#6a48b8", 7, 5, 30, 37, 4); f(c, "#4a3290", () => c.roundRect(7, 5, 7, 37, [4, 0, 0, 4])); rr(c, GOLD, 7, 10, 7, 3, 1); rr(c, GOLD, 7, 33.6, 7, 3, 1);
        f(c, "#8a6ad8", () => c.rect(15.5, 7.5, 2.2, 32)); if (!o.small) { poly(c, GOLD, [[37, 5], [37, 11], [31, 5]], 0.6); poly(c, GOLD, [[37, 42], [37, 36], [31, 42]], 0.6); }
        halo(c, o, (x) => { poly(x, GOLD, [[25.5, 11.5], [34, 23.5], [25.5, 35.5], [17, 23.5]], 1); poly(x, "#c8bcff", [[25.5, 14.6], [31.4, 23.5], [25.5, 32.4], [19.6, 23.5]], 0.6); poly(x, "#f6f2ff", [[25.5, 14.6], [19.6, 23.5], [25.5, 23.5]]); poly(x, "#9a86ff", [[31.4, 23.5], [25.5, 32.4], [25.5, 23.5]]); }); } },
    bar_G: { zh: "成長（G）", grp: "bar", live: ["bar", "G"], sizes: [35, 24], topic: "一株嫩芽：褐色土丘、綠莖、左右兩片胖葉子，頂上一個金色朝上箭頭",
      d: (c, o) => { f(c, "#8a5a32", () => { c.moveTo(8, 44); c.quadraticCurveTo(24, 31, 40, 44); c.closePath(); }); if (!o.small) f(c, "#a87444", () => { c.moveTo(13, 40.5); c.quadraticCurveTo(19, 36.4, 24, 36); c.lineTo(24, 38); c.quadraticCurveTo(18, 38.4, 13, 40.5); c.closePath(); });
        ln(c, "#4f8a3a", 4.4, [[24, 40], [24, 31], [23, 24], [24, 17]]);
        f(c, "#5cae3e", () => { c.moveTo(23.4, 31); c.quadraticCurveTo(9, 33, 6.5, 20); c.quadraticCurveTo(19, 18, 23.4, 31); c.closePath(); }); f(c, "#9ad868", () => { c.moveTo(21, 28.6); c.quadraticCurveTo(12, 28.4, 9.6, 21.6); c.quadraticCurveTo(16, 22, 21, 28.6); c.closePath(); });
        f(c, "#5cae3e", () => { c.moveTo(24.4, 26); c.quadraticCurveTo(39, 27, 41.5, 13.5); c.quadraticCurveTo(28.5, 12, 24.4, 26); c.closePath(); }); f(c, "#9ad868", () => { c.moveTo(27.4, 22); c.quadraticCurveTo(29.5, 15.6, 37.6, 15.4); c.quadraticCurveTo(33, 19.6, 27.4, 22); c.closePath(); });
        halo(c, o, (x) => { poly(x, "#ffc83a", [[24, 3.6], [33.4, 13.6], [27.8, 13.6], [27.8, 19], [20.2, 19], [20.2, 13.6], [14.6, 13.6]], 0.8); poly(x, "#fff3a0", [[24, 3.6], [14.6, 13.6], [20.2, 13.6], [20.2, 19], [24, 19]]); }); } },
    bar_J: { zh: "任務（J）", grp: "bar", live: ["bar", "J"], also: ["hud", "scroll"], bare: [20, 14], sizes: [35, 24, 20, 14], topic: "攤開的米白卷軸：上下兩捲（紅褐軸頭），正中一個紅色粗驚嘆號；≥24px 兩側各三道淺字線",
      d: (c, o) => { rr(c, CREAM, 11, 8, 26, 32, 1.5); f(c, "rgba(120,90,40,0.2)", () => c.rect(31, 8, 6, 32)); if (!o.small) for (const y of [16.5, 22, 27.5]) { rr(c, "#b8a888", 14, y, 5.6, 1.8, 0.9); rr(c, "#b8a888", 28.6, y, 5.6, 1.8, 0.9); }
        for (const y of [4.6, 36.4]) { rr(c, "#e2d0a0", 8, y, 32, 7, 3.5); f(c, "#fff6dc", () => c.rect(10, y + 1.3, 27, 1.6)); if (!o.tiny) { ci(c, "#8a2f20", 7.4, y + 3.5, 3.2); ci(c, "#8a2f20", 40.6, y + 3.5, 3.2); } }
        rr(c, "#d83a2a", 21.2, 13, 5.6, 14.6, 2.6); f(c, "#ff8a70", () => c.rect(22.2, 14.4, 1.6, 10)); ci(c, "#d83a2a", 24, 32.2, 3); } },
    bar_Y: { zh: "影子（Y）", grp: "bar", live: ["bar", "Y"], sizes: [27, 24], topic: "單色人形剪影（深紫，左緣一道淡紫亮邊），右上後面錯開半個身位一個同樣大小的淡紫幽影分身（下襬是波浪的鬼尾，不是第二個人）；前面那個自己包一圈外框",
      d: (c, o) => { const bustAt = (x, col, cx, cy, k) => { ci(x, col, cx, cy - 10 * k, 7.6 * k); f(x, col, () => { x.moveTo(cx - 13.6 * k, cy + 15 * k); x.quadraticCurveTo(cx - 13.6 * k, cy - 0.6 * k, cx, cy - 0.6 * k); x.quadraticCurveTo(cx + 13.6 * k, cy - 0.6 * k, cx + 13.6 * k, cy + 15 * k); x.closePath(); }); };
        const ghost = (x, col, cx, cy, k) => { ci(x, col, cx, cy - 10 * k, 7.6 * k); f(x, col, () => { x.moveTo(cx - 12.4 * k, cy + 11 * k); x.quadraticCurveTo(cx - 12.4 * k, cy - 0.6 * k, cx, cy - 0.6 * k); x.quadraticCurveTo(cx + 12.4 * k, cy - 0.6 * k, cx + 12.4 * k, cy + 11 * k);
          x.quadraticCurveTo(cx + 10.3 * k, cy + 16.4 * k, cx + 8.3 * k, cy + 11 * k); x.quadraticCurveTo(cx + 6.2 * k, cy + 16.4 * k, cx + 4.1 * k, cy + 11 * k); x.quadraticCurveTo(cx + 2 * k, cy + 16.4 * k, cx, cy + 11 * k); x.lineTo(cx - 12.4 * k, cy + 11 * k); x.closePath(); }); };
        ghost(c, "#b8a0ff", 28, 21.4, 0.94); if (!o.small) el(c, "#e2d8ff", 24.8, 9.2, 1.6, 2.6, 0.5);
        halo(c, o, (x) => { bustAt(x, "#5a4a90", 20, 29.4, 0.94); f(x, "#8a78c8", () => { x.arc(20, 20, 7.1, PI * 0.95, PI * 1.5); x.arc(20.8, 20.6, 5.8, PI * 1.5, PI * 0.95, true); x.closePath(); }); f(x, "#8a78c8", () => { x.moveTo(7.2, 43.5); x.quadraticCurveTo(7.2, 29.4, 16.4, 29); x.lineTo(16, 31); x.quadraticCurveTo(9.8, 32.4, 9.8, 43.5); x.closePath(); }); }); } },
    bar_N: { zh: "留言（N）", grp: "bar", live: ["bar", "N"], also: ["hud", "notes"], bare: [13], sizes: [35, 24, 13], topic: "米白便條（左下拉出對話框的尾巴），右上一顆紅圖釘；≥24px 兩道字線，≤14px 換成三個深色點（現行浮動提示的對話框）",
      d: (c, o) => { poly(c, CREAM, [[5, 8], [43, 8], [43, 32], [21, 32], [11, 42], [13, 32], [5, 32]], 2.4); f(c, "rgba(120,90,40,0.2)", () => c.rect(5, 27.5, 38, 4.5)); f(c, "#fffaf0", () => c.rect(7, 10, 34, 2));
        if (o.tiny) { for (const x of [14.5, 24, 33.5]) ci(c, "#5a4a30", x, 20, 3); return; }
        if (!o.small) { rr(c, "#a89a7a", 10, 15, 25, 2.4, 1.2); rr(c, "#a89a7a", 10, 21.5, 18, 2.4, 1.2); } else { rr(c, "#a89a7a", 10, 16, 24, 3, 1.5); }
        halo(c, o, (x) => { ci(x, "#d83a2a", 38.5, 9.5, 5.4); ci(x, "#ff8a70", 36.8, 7.8, 1.9); }); } },
    bar_R: { zh: "潛行（R）", grp: "bar", live: ["bar", "R"], sizes: [35, 24], src: "b4:status.concealed", topic: "紫色兜帽，深色臉洞裡兩道發亮的黃色斜眼（第 4 批的「隱蔽」「潛行偷襲」同一個兜帽）", d: b10((c, o) => QP.entry("status", "concealed").d(c, o), 1.02) },
    bar_M: { zh: "地圖（M）", grp: "bar", live: ["bar", "M"], sizes: [23, 24], topic: "三折的米黃地圖（中間一折暗一階），左折一小塊綠林，褐色虛線路線走到右上一顆發光的藍點",
      pre: (c, o) => glow(c, 34.5, 16.5, 9, "#5ac8f0", 0.6),
      d: (c, o) => { poly(c, "#efe2bc", [[4, 11], [17, 6], [17, 38], [4, 43]], 1.2); poly(c, "#cdb888", [[17, 6], [31, 11], [31, 43], [17, 38]], 0.6); poly(c, "#efe2bc", [[31, 11], [44, 6], [44, 38], [31, 43]], 1.2);
        f(c, "#fffaf0", () => c.rect(5.5, 12, 2, 28)); el(c, "#7ab85a", 10.5, 19, 3.6, 4.4); if (!o.small) el(c, "#a8dc84", 9.6, 17.6, 1.4, 1.8);
        c.save(); c.setLineDash(o.small ? [4.4, 3.2] : [3.4, 2.6]); ln(c, "#8a5a2a", o.small ? 2.8 : 2.2, [[9, 36], [16, 29], [24, 31], [33, 18]]); c.restore();
        halo(c, o, (x) => { ci(x, "#4a9cff", 34.5, 16.5, 4.8); ci(x, "#dff0ff", 33.2, 15.2, 1.7); }); } },

    // ---------------- 通用小圖（world/HudIcons.tsx；用到的 18 個，scroll、notes 在上面和功能列同一份） ----------------
    rank: { zh: "階級", grp: "gen", live: ["hud", "rank"], sizes: [18], topic: "金邊藍色鳶形盾，盾面兩道金色粗山形紋（V 朝上）",
      d: (c, o) => { const sh = (l, r, t, b) => { const m = (l + r) / 2; c.moveTo(l, t); c.lineTo(r, t); c.lineTo(r, 22); c.bezierCurveTo(r, 22 + (b - 22) * 0.6, m + (r - m) * 0.55, b - 3, m, b); c.bezierCurveTo(m - (r - m) * 0.55, b - 3, l, 22 + (b - 22) * 0.6, l, 22); c.closePath(); };
        f(c, GOLD, () => sh(7, 41, 5, 45)); f(c, "#3e5cc0", () => sh(10.6, 37.4, 8.6, 40.4)); c.save(); c.beginPath(); sh(10.6, 37.4, 8.6, 40.4); c.clip(); f(c, "#5e7ee0", () => c.rect(0, 0, 24, 48)); c.restore();
        for (const y of [17, 26]) { poly(c, "#ffd04a", [[13.4, y + 6.4], [24, y - 3.6], [34.6, y + 6.4], [34.6, y + 12.2], [24, y + 2.2], [13.4, y + 12.2]], 0.8); poly(c, GOLD_L, [[13.4, y + 6.4], [24, y - 3.6], [24, y - 1], [13.4, y + 8.8]]); } } },
    gear: { zh: "設定（齒輪）", grp: "gen", live: ["hud", "gear"], sizes: [17], topic: "鋼灰八齒齒輪，左上亮、右下暗，中間一個深色洞", d: (c, o) => gearArt(c, o) },
    town: { zh: "城鎮（地名條）", grp: "gen", live: ["hud", "town"], sizes: [15], topic: "一間小屋：紅瓦斜頂（左半亮）、煙囪、米白牆、褐色圓頂門",
      d: (c, o) => { rr(c, "#a04030", 31, 8, 5.6, 11, 1); rr(c, CREAM, 10, 22, 28, 21, 2); f(c, "rgba(120,90,40,0.22)", () => c.rect(30, 22, 8, 21));
        poly(c, "#c8543a", [[4, 25], [24, 6], [44, 25]], 1.6); poly(c, "#e8805a", [[4, 25], [24, 6], [24, 10.6], [9.6, 25]], 0.8);
        f(c, "#8a5a32", () => c.roundRect(19.6, 29, 8.8, 14, [4.4, 4.4, 0, 0])); if (!o.small) { rr(c, "#7fa8d0", 30, 28, 5, 5, 1); ci(c, GOLD, 26.2, 36.6, 0.9); } } },
    warn: { zh: "警告（限制）", grp: "gen", live: ["hud", "warn"], sizes: [15, 13], src: "b4:card.drawback", topic: "琥珀色警告三角＋深色驚嘆號（第 4 批卡片小圖「缺點」）", d: b10((c, o) => QP.entry("card", "drawback").d(c, o), 1.1) },
    sun: { zh: "時間：晝（太陽）", grp: "gen", live: ["hud", "sun"], sizes: [15], topic: "黃色圓日（左上亮）、外圍八道橘黃三角光芒",
      d: (c, o) => { for (let i = 0; i < 8; i++) at(c, 24, 24, 1, (q) => poly(q, "#ffa82a", [[-4.4, -12.6], [0, -20.8], [4.4, -12.6]], 0.8), (i * PI) / 4); ci(c, "#ffd040", 24, 24, 12); ci(c, "#ffe68a", 22.6, 22.6, 8); el(c, "#fff8d8", 19.6, 19, 3.4, 2.2, -0.7); } },
    moon: { zh: "時間：夜（月亮）", grp: "gen", live: ["hud", "moon"], sizes: [15], topic: "一彎淡米黃的大新月（開口朝右上），左緣亮、內緣一道暗面",
      d: (c, o) => { f(c, "#f2e6b4", () => crescent(c, 23, 25, 19, 33, 15, 15)); f(c, "#c9b878", () => crescent(c, 23, 25, 19, 30.4, 17.6, 15.6)); f(c, "#f2e6b4", () => crescent(c, 23, 25, 17.4, 33, 15, 15)); f(c, "#fffadc", () => crescent(c, 23, 25, 19, 25.6, 22, 17.6)); if (!o.small) { ci(c, "#d8ca90", 12.6, 31, 2); ci(c, "#d8ca90", 18, 38, 1.4); } } },
    clear: { zh: "天氣：晴", grp: "gen", live: ["hud", "clear"], sizes: [15, 18], topic: "橘黃圓日（左上亮），外面一圈八顆圓光點（現行的構圖：圓日＋一圈點）",
      d: (c, o) => { for (let i = 0; i < 8; i++) ci(c, "#ffc23a", 24 + Math.cos((i * PI) / 4) * 17.4, 24 + Math.sin((i * PI) / 4) * 17.4, 3.4); ci(c, "#ffb02a", 24, 24, 11.6); ci(c, "#ffd86a", 22.8, 22.8, 7.8); el(c, "#fff4c8", 20, 19.4, 3.2, 2, -0.7); } },
    rain: { zh: "天氣：雨", grp: "gen", live: ["hud", "rain"], sizes: [15, 18], topic: "灰藍的雲（上緣亮），底下三顆斜落的藍雨滴",
      d: (c, o) => { cloud(c, "#c4d0dc", 24, 18.6, 1.18); f(c, "#eef3f8", () => { c.arc(24, 15, 8.8, PI * 1.12, PI * 1.85); c.arc(24, 17.4, 8.8, PI * 1.85, PI * 1.12, true); c.closePath(); }); f(c, "#9aa8b8", () => c.rect(10, 26.2, 28, 3));
        for (const x of [14, 24.5, 35]) at(c, x, 36.4, 1, (q) => { drop(q, "#4aa8ff", 0, 0, 0.5); el(q, "#cfe8ff", -1.2, 1.4, 0.9, 1.6); }, 0.35); } },
    fog: { zh: "天氣：霧", grp: "gen", live: ["hud", "fog"], sizes: [15, 18], topic: "上面一小朵淡灰雲，底下兩道錯開的淡灰粗霧帶（圓頭）",
      d: (c, o) => { cloud(c, "#d6dce4", 22, 16.6, 1.02); f(c, "#f2f5f8", () => { c.arc(22, 13.8, 7.6, PI * 1.15, PI * 1.85); c.arc(22, 15.8, 7.6, PI * 1.85, PI * 1.15, true); c.closePath(); });
        rr(c, "#c2c8d2", 5, 26.4, 31, 6.6, 3.3); f(c, "#e8edf2", () => c.rect(8, 27.4, 24, 1.8)); rr(c, "#aab2be", 12.6, 35.8, 30, 6.6, 3.3); f(c, "#d8dee6", () => c.rect(15.6, 36.8, 22, 1.8)); } },
    snow: { zh: "天氣：雪", grp: "gen", live: ["hud", "snow"], sizes: [15, 18], src: "b5:emblem.ice", topic: "白色粗雪花（第 5 批冰元素架勢的紋章，放大）", d: b10((c, o) => QT.EMBLEM.ice.d(c, o), 1.32) },
    wind: { zh: "天氣：風", grp: "gen", live: ["hud", "wind"], sizes: [15, 18], src: "b5:emblem.wind", topic: "白色旋風（一圈半的螺旋，尾巴往左下甩；第 5 批風元素架勢的紋章，放大）", d: b10((c, o) => QT.EMBLEM.wind.d(c, o), 1.4) },
    night: { zh: "天氣：夜晚（晴夜）", grp: "gen", live: ["hud", "night"], sizes: [15, 18], topic: "偏藍紫的小新月（左下，比時間的月亮暗一階、小一號），右上兩顆米白四芒星",
      d: (c, o) => { f(c, "#aab4ec", () => crescent(c, 19, 28, 15, 27, 20, 12)); f(c, "#d4dafc", () => crescent(c, 19, 28, 15, 21.2, 25.6, 13.6)); poly(c, "#fff6c8", starPts(36, 12, 8.6, 2.6, 4), 0.4); poly(c, "#fff6c8", starPts(39, 30, 5.2, 1.7, 4), 0.3); } },
    coin: { zh: "金幣", grp: "gen", live: ["hud", "coin"], sizes: [15], src: "style:item.gold", topic: "兩枚疊著的金幣，後面斜靠一枚大的（幣面一顆星；風格樣張的物品「金幣」）", d: (c, o) => { c.save(); Q.ART.item.gold.d(c, o); c.restore(); } },
    token: { zh: "任務幣", grp: "gen", live: ["hud", "token"], sizes: [15], topic: "銅紅色的六角代幣（內圈亮一階），中間一顆米白五角星——用六角形和圓的金幣分開",
      d: (c, o) => { const hx = (R, y0 = 24) => [0, 1, 2, 3, 4, 5].map((i) => [24 + Math.cos((i / 6) * TAU) * R, y0 + Math.sin((i / 6) * TAU) * R]); poly(c, "#b0503a", hx(19.2), 2); poly(c, "#d8704a", hx(14.8), 1.4);
        f(c, "#e89a70", () => { c.moveTo(13.6, 24); c.lineTo(18.8, 15); c.lineTo(29.2, 15); c.lineTo(26.6, 19); c.lineTo(20.6, 19); c.lineTo(17.6, 24); c.closePath(); }); poly(c, "#fbe4c4", starPts(24, 25, 9.4, 4, 5), 0.6); } },
    ration: { zh: "補給", grp: "gen", live: ["hud", "ration"], sizes: [15], topic: "一條圓胖的麵包（上半亮、底下一道深色），表面三道斜的淺色刀痕",
      d: (c, o) => { f(c, "#c88a4a", () => { c.moveTo(4, 33); c.bezierCurveTo(4, 12, 44, 12, 44, 33); c.quadraticCurveTo(44, 39, 38, 39); c.lineTo(10, 39); c.quadraticCurveTo(4, 39, 4, 33); c.closePath(); }); f(c, "#9a6430", () => c.roundRect(6, 33, 36, 6, [0, 0, 5, 5]));
        el(c, "#e0a868", 20, 22, 11, 4.4, -0.12); for (const x of [14, 23.6, 33.2]) at(c, x, 25, 1, (q) => rr(q, "#f6d8a0", -1.8, -6, 3.6, 12, 1.8), 0.5); } },
    bulb: { zh: "靈感點／提示（燈泡）", grp: "gen", live: ["hud", "bulb"], also: ["settings", "hint"], sizes: [15], topic: "亮黃燈泡（左上一塊白亮面），≥24px 有橘色鎢絲，灰色螺口兩節",
      pre: (c, o) => glow(c, 24, 18, 19, "#ffe070", 0.5),
      d: (c, o) => { ci(c, "#ffe070", 24, 17.6, 14); poly(c, "#ffe070", [[15, 25], [33, 25], [30.4, 33.6], [17.6, 33.6]], 1); f(c, "#f0c040", () => { c.arc(24, 17.6, 14, PI * 0.05, PI * 0.5); c.lineTo(24, 33.6); c.lineTo(30.4, 33.6); c.closePath(); });
        if (!o.small) ln(c, "#ff9a2a", 1.8, [[20, 26], [21.6, 19], [24, 24], [26.4, 19], [28, 26]]); el(c, "#fffbe0", 18.6, 12.6, 3.4, 4.8, 0.55);
        rr(c, "#a8acb4", 17.4, 33.4, 13.2, 4.4, 1.6); rr(c, "#8a8e96", 18.2, 37.4, 11.6, 4, 1.6); f(c, "#e0e4ea", () => c.rect(19, 34.2, 10, 1.2)); rr(c, "#5e626a", 21, 41, 6, 3.4, 1.6); } },

    // ---------------- 戰鬥工具鈕 7（ui/BattleToolIcons.tsx，20px） ----------------
    t_reactions: { zh: "反應設定", grp: "tool", live: ["tool", "reactions"], sizes: [20], src: "b4:card.reaction", topic: "綠色逆時針回轉箭頭（和資源小圖「反應」同一個；現行的盾＋閃電和第 5 批「帶電護盾」撞圖，見紀錄 5 節）", d: b10((c, o) => QP.entry("card", "reaction").d(c, o), 1.1) },
    t_orders: { zh: "隊友指令", grp: "tool", live: ["tool", "orders"], sizes: [20], topic: "褐色旗桿（金頂珠）掛一面紅色燕尾旗（上半亮、下半暗）",
      d: (c, o) => { rr(c, "#a06a36", 7.6, 7, 4.6, 37.6, 2); f(c, "#d8a868", () => c.rect(8.4, 9, 1.4, 34)); poly(c, "#d85a48", [[12, 8], [42.6, 8], [34.8, 18.4], [42.6, 28.8], [12, 28.8]], 1.2); poly(c, "#ff8a70", [[12, 8], [42.6, 8], [39.2, 12.4], [12, 12.4]], 0.6); poly(c, "#b03e2e", [[12, 24], [39, 24], [42.6, 28.8], [12, 28.8]], 0.6); ci(c, GOLD, 9.9, 6.6, 3.2); ci(c, GOLD_L, 9, 5.7, 1.1); } },
    t_legend: { zh: "圖例", grp: "tool", live: ["tool", "legend"], sizes: [20], topic: "打開的米白書（褐色封面邊、中縫暗），左頁一紅一藍兩個色塊，右頁兩道字線",
      d: (c, o) => { f(c, "#8a5a32", () => { c.moveTo(3, 13); c.lineTo(24, 16.5); c.lineTo(45, 13); c.lineTo(45, 41); c.lineTo(24, 45); c.lineTo(3, 41); c.closePath(); });
        poly(c, CREAM, [[4.6, 10], [23, 13.6], [23, 41], [4.6, 37.6]], 1.4); poly(c, "#e4d6b2", [[25, 13.6], [43.4, 10], [43.4, 37.6], [25, 41]], 1.4); f(c, "rgba(90,60,30,0.35)", () => c.rect(21.6, 13.6, 4.8, 27.4));
        rr(c, "#d84a3a", 8.4, 17, 6, 5.6, 1.2); rr(c, "#4a8ae0", 8.4, 26.4, 6, 5.6, 1.2); for (const y of [19.6, 28.6]) { if (!o.small) rr(c, "#a89878", 16, y - 0.6, 5, 1.8, 0.9); rr(c, "#a89878", 28.6, y - 2.6 + (y > 20 ? 0 : 0), 11, 2.4, 1.2); } } },
    t_layout: { zh: "版面設定（齒輪）", grp: "tool", live: ["tool", "layout"], sizes: [20], src: "same:gear", topic: "和通用小圖「設定」同一個齒輪", d: (c, o) => gearArt(c, o) },
    t_save: { zh: "存檔", grp: "tool", live: ["tool", "save"], sizes: [20], topic: "藍色磁片：右上切角、上方銀色滑蓋（一道開口）、下方白色標籤",
      d: (c, o) => { poly(c, "#3a68b0", [[5.6, 5.6], [35.6, 5.6], [42.4, 12.4], [42.4, 42.4], [5.6, 42.4]], 3); f(c, "#5a88d0", () => c.rect(7.4, 8, 2.4, 32)); rr(c, "#c8d0da", 14, 5.6, 19, 12.6, 1.5); rr(c, "#3a68b0", 26.4, 8, 4.4, 7.6, 1); f(c, "#eef2f6", () => c.rect(15.2, 6.8, 9, 1.6));
        rr(c, "#f2f4f8", 10.6, 24.6, 26.8, 16, 2); if (!o.small) { rr(c, "#a8b0c0", 14, 29, 20, 1.8, 0.9); rr(c, "#a8b0c0", 14, 34, 14, 1.8, 0.9); } } },
    t_exit: { zh: "離開", grp: "tool", live: ["tool", "exit"], sizes: [20], src: "style:hud.exit", topic: "深褐門框、淺褐門板半開、金門把，米白大箭頭朝右（風格樣張）", d: (c, o) => Q.ART.hud.exit.d(c, o) },
    t_telegraph: { zh: "環境預告", grp: "tool", live: ["tool", "telegraph"], sizes: [20], src: "b4:card.delayed", topic: "藍框白玻璃金沙的沙漏（第 4 批的延遲沙漏）", d: b10((c, o) => QP.entry("card", "delayed").d(c, o), 1.12) },

    // ---------------- 資源小圖（ui/StatusCardParts.tsx 的 StatGlyph，16px；用卡片小圖的畫法：圖樣 ±10 單位、≤14px 不包外框） ----------------
    r_ap: { zh: "AP", grp: "res", live: ["card", "ap"], sizes: [16], card: "ap", src: "b4:card.ap", topic: "黃色閃電（已是 Q 版，QI-2c）" },
    r_mana: { zh: "法力", grp: "res", live: ["card", "mana"], sizes: [16], card: "mana", src: "b4:card.mana", topic: "藍色水滴（已是 Q 版）" },
    r_source: { zh: "源力", grp: "res", live: ["card", "source"], sizes: [16], card: "source", src: "b4:card.source", topic: "淡紫六角晶石（已是 Q 版）" },
    r_reaction: { zh: "反應", grp: "res", live: ["card", "reaction"], sizes: [16], card: "reaction", src: "b4:card.reaction", topic: "綠色逆時針回轉箭頭（已是 Q 版）" },
    r_move: { zh: "移動", grp: "res", live: ["stat", "move"], sizes: [16], src: "style:hud.move", topic: "褐色短靴（風格樣張 HUD「移動」，同第 4 批靴子）", d10: from48((c, o) => Q.ART.hud.move.d(c, o), 0.46) },
    r_shield: { zh: "護盾", grp: "res", live: ["stat", "shield"], sizes: [16], src: "b3:act.shield", topic: "淡藍小盾、白十字（第 3 批護盾記號）", d10: (c, o) => QS.ACT.shield.d(c, o, ["#6ab8f0", "#cfe8ff"]) },
    r_weapon: { zh: "武器", grp: "res", live: ["stat", "weapon"], sizes: [16], src: "b4:skeleton.strike", topic: "斜放的亮色單手劍（第 4 批「打擊」徽章）", d10: (c, o) => QP.entry("skeleton", "strike").d(c, o) },
    r_ammo: { zh: "彈藥", grp: "res", live: ["stat", "ammo"], sizes: [16], topic: "一顆直立的子彈：銅色圓彈頭、黃銅彈殼、底下一圈暗銅底緣（風格樣張 bullet() 的配色）", d10: bulletArt },

    // ---------------- 設定標題 3（ui/SettingsHead.tsx，16px） ----------------
    s_sound: { zh: "聲音", grp: "set", live: ["settings", "sound"], sizes: [16], topic: "鐵灰小盒＋金色喇叭口（左上亮），右邊兩道米白粗聲波",
      d: (c, o) => { rr(c, "#8d969f", 4, 16, 10, 16, 2); poly(c, GOLD, [[12, 16], [25, 6], [25, 42], [12, 32]], 1.6); poly(c, GOLD_L, [[12, 16], [25, 6], [25, 12], [14.6, 19.6]], 0.6); f(c, "#b88a2a", () => c.rect(21.6, 9, 3.4, 30));
        st(c, CREAM, 4.6, (x) => x.arc(25, 24, 9, -0.85, 0.85)); st(c, CREAM, 4.6, (x) => x.arc(25, 24, 17, -0.78, 0.78)); } },
    s_motion: { zh: "減少動態", grp: "set", live: ["settings", "motion"], sizes: [16], topic: "金色圓球（左上亮、右下暗），左邊三道米白速度線",
      d: (c, o) => { for (const [x, y, w] of [[4.6, 14, 12], [3, 22, 14], [4.6, 30, 12]]) rr(c, CREAM, x, y, w, 4.4, 2.2); ci(c, GOLD, 31, 24, 13); f(c, "#c08a20", () => { c.arc(31, 24, 13, PI * 0.02, PI * 0.62); c.arc(29, 22, 12.4, PI * 0.62, PI * 0.02, true); c.closePath(); }); el(c, GOLD_L, 26.6, 18.6, 4, 2.6, -0.65); } },
    s_hint: { zh: "提示", grp: "set", live: ["settings", "hint"], sizes: [16], src: "same:bulb", topic: "和通用小圖「靈感點」同一個燈泡", d: (c, o) => ICON.bulb.d(c, o), pre: (c, o) => ICON.bulb.pre(c, o) },

    // ---------------- 源力小晶石圓點（建議新增：狀態卡 .stat-pip.source 的 9px 圓點） ----------------
    pip_on: { zh: "源力圓點（亮）", grp: "pip", live: ["pip", "on"], sizes: [9], src: "b4:card.source", topic: "第 4 批的淡紫晶石縮到 9px（≤14px 不包外框）", d10: crystal },
    pip_off: { zh: "源力圓點（暗）", grp: "pip", live: ["pip", "off"], sizes: [9], topic: "同形的晶石，深紫底＋淡紫細邊（用掉的源力）",
      d10: (c, o) => { const P = [[0, -10.6], [7.8, -4.6], [7.8, 4.6], [0, 10.6], [-7.8, 4.6], [-7.8, -4.6]]; poly(c, "#7a68c8", P, 0.6); poly(c, "#2a2440", [[0, -7.6], [5.2, -3.2], [5.2, 3.2], [0, 7.6], [-5.2, 3.2], [-5.2, -3.2]], 0.4); } },

    // ---------------- 區域紋章 6（ui/CreateIcons.tsx 的 RegionCrest；六角金框、深藍底照現行，只換圖樣；圖樣用區域強調色） ----------------
    c_crystal_crown: { zh: "晶冠：王冠", grp: "crest", region: "crystal_crown", live: ["crest", "crystal_crown"], sizes: [34, 30], topic: "區域色（淡藍）的三尖王冠：尖頂白珠、冠帶亮一階、正中一顆白色菱形寶石",
      d: (c, o, A) => { poly(c, A[0], [[8, 38], [6, 13], [16.4, 23], [24, 7], [31.6, 23], [42, 13], [40, 38]], 1.6); poly(c, A[1], [[8, 38], [6, 13], [16.4, 23], [17, 26], [10.6, 26.6], [10.8, 38]], 0.8); rr(c, A[1], 7, 30, 34, 8, 2); f(c, A[2], () => c.rect(9, 36, 30, 2));
        for (const [x, y] of [[6, 12], [24, 6], [42, 12]]) ci(c, "#f4f8ff", x, y, 3.4); poly(c, "#ffffff", [[24, 27.6], [28, 32], [24, 36.4], [20, 32]], 0.6); } },
    c_cloud_ridge: { zh: "雲嶺：雙峰", grp: "crest", region: "cloud_ridge", live: ["crest", "cloud_ridge"], sizes: [34, 30], topic: "區域色（綠）的雙峰（左高右低），左峰頂一塊白雪，山腰一縷白雲",
      d: (c, o, A) => { poly(c, A[2], [[22, 40], [32, 18], [43, 40]], 1.2); poly(c, A[0], [[4, 40], [17, 8], [31, 40]], 1.2); poly(c, A[1], [[4, 40], [17, 8], [17, 40]]); poly(c, "#f6f8f0", [[12.2, 19], [17, 8], [21.8, 19], [19.4, 17.4], [17, 20], [14.6, 17.4]], 0.6); poly(c, "#f6f8f0", [[28.6, 25.4], [32, 18], [35.4, 25.4], [32, 24]], 0.4);
        halo(c, o, (x) => { rr(x, "#f2f6f8", 20, 28.6, 20, 5.6, 2.8); ci(x, "#f2f6f8", 27, 28.4, 4); }); } },
    c_arcane_hub: { zh: "樞市：齒輪", grp: "crest", region: "arcane_hub", live: ["crest", "arcane_hub"], sizes: [34, 30], src: "same:gear", topic: "和「設定」同一個齒輪，染區域色（青綠）", d: (c, o, A) => gearArt(c, o, A) },
    c_ashen_waste: { zh: "荒原：火焰", grp: "crest", region: "ashen_waste", live: ["crest", "ashen_waste"], sizes: [34, 30], topic: "區域色（橘）的一團火：外層橘、內層黃、白芯（規則 5 三層）",
      pre: (c, o) => glow(c, 24, 27, 21, "#ff8a3a", 0.4), d: (c, o, A) => { flame(c, A[0], 24, 24.4, 2.02); flame(c, "#ffd23f", 24, 30.2, 1.3); flame(c, "#fff6d8", 24, 35, 0.66); } },
    c_frost_tide: { zh: "霜潮：浪紋", grp: "crest", region: "frost_tide", live: ["crest", "frost_tide"], sizes: [34, 30], topic: "區域色（冰藍）的一道捲起來的大浪（浪頭白沫），底下一道平的淺色浪",
      d: (c, o, A) => { f(c, A[0], () => { c.moveTo(4, 40); c.bezierCurveTo(6, 22, 16, 9, 30, 9); c.bezierCurveTo(40, 9, 45, 17, 42, 24); c.bezierCurveTo(39, 30, 30, 29, 30, 23); c.bezierCurveTo(30, 19, 34, 17.4, 36.4, 19.6); c.bezierCurveTo(35, 15, 28, 14.6, 23, 19); c.bezierCurveTo(17, 25, 17, 34, 22, 40); c.closePath(); });
        f(c, A[1], () => { c.moveTo(7.6, 36); c.bezierCurveTo(9, 23, 17, 12.6, 28, 12); c.lineTo(28, 14.4); c.bezierCurveTo(19, 16, 12.4, 24, 11.2, 36); c.closePath(); });
        f(c, "#f4fbff", () => { c.moveTo(26, 9.6); c.bezierCurveTo(35, 7.4, 44, 12, 42.4, 21); c.bezierCurveTo(40.6, 15.6, 35.6, 12.6, 28.4, 13.2); c.closePath(); });
        rr(c, A[2], 4, 38.4, 40, 5.6, 2.8); f(c, "#d8f2ff", () => c.rect(8, 39.2, 30, 1.4)); } },
    c_other: { zh: "其他區：菱形寶石", grp: "crest", region: "hub", live: ["crest", "hub"], sizes: [34, 30], topic: "區域色（淡紫）的直立菱形寶石，左上兩個切面亮、右下暗（照現行的菱形，加切面）",
      d: (c, o, A) => { const P = [[24, 5], [39, 24], [24, 43], [9, 24]]; poly(c, A[0], P, 1.2); poly(c, "#f4f0ff", [[24, 5], [9, 24], [18, 24], [24, 13]], 0.4); poly(c, A[1], [[18, 24], [24, 13], [30, 24], [24, 35]]); poly(c, A[2], [[39, 24], [24, 43], [24, 35], [30, 24]], 0.4); } },
  };
  const REGION_ACCENT = { crystal_crown: "#8ab0ff", cloud_ridge: "#6aa84a", arcane_hub: "#4ad0c8", ashen_waste: "#ff6a1a", frost_tide: "#6ac0e8", hub: "#a898ff" }; /* 照 content/ui/region_themes.yaml 的 accent */
  /** 區域色的三階：本色、亮一階（混白 40%）、暗一階（混黑 28%）。 */
  const tone3 = (a) => [a, mix(a, "#ffffff", 0.4), mix(a, "#000000", 0.28)];
  const accentOf = (id) => tone3(REGION_ACCENT[ICON[id].region] ?? "#a898ff");

  // ---------------- 出圖 ----------------
  /** 圖樣定義（48 格）：card／d10（±10 單位）的包成 48 格；紋章帶區域色。 */
  function def(id) { const e = ICON[id]; if (e.card) return { d: b10((c, o) => QP.entry("card", e.card).d(c, o)) }; if (e.d10) return { d: b10(e.d10) };
    if (e.grp === "crest") { const A = accentOf(id); return { d: (c, o) => e.d(c, o, A), pre: e.pre }; } return { d: e.d, pre: e.pre, post: e.post }; }
  /** 只畫圖樣（不含框）：邊長 px 的 canvas（裝置像素 round(px×res)）；≤14px 不包外框（規則 8）。 */
  const glyph = (id, px, res = 2, opt = {}) => Q.render(def(id), px, res, { ow: opt.ow ?? (px <= 14 ? 0 : Q.outlinePx(px)) });
  /** 卡片小圖的做法（第 4 批 cardCanvas）：圖樣本身 min(14, px×0.84)、圖樣格＝它的 4/3，貼滿整格、對齊整數像素。 */
  const CARD_BOX = 48 / 36, cardPx = (px) => Math.min(14, px * 0.84);
  /** 圖釘 B 與資源小圖：照第 4 批 cardCanvas 的路徑畫 ±10 單位的圖樣。 */
  function cardLike(fn10, px, res, cpx = cardPx(px)) { return Q.render({ d: b10(fn10) }, cpx * CARD_BOX, res, { ow: cpx <= 14 ? 0 : Q.outlinePx(cpx) }); }
  /** 畫一個含框的圖示在 (0,0)～(size,size)。框：功能列＝淺色圓底（HUD_BACKING）；紋章＝六角金框＋深藍底＋區域色細環（RegionCrest）；其他沒有框。 */
  function paint(ctx, id, size, res, opt = {}) {
    const e = ICON[id];
    ctx.save();
    if (e.grp === "bar" && opt.frame !== "none") {
      ctx.beginPath(); ctx.arc(size / 2, size / 2, (15.5 / 48) * size, 0, TAU); ctx.fillStyle = "#d4dbef"; ctx.fill(); ctx.lineWidth = size / 48; ctx.strokeStyle = "#8a94b8"; ctx.stroke();
      const p = size * 0.13, a = size - p * 2; QW.blit(ctx, glyph(id, a, res), p, p, a, res); /* 圖樣佔 74%（風格樣張背包的做法；現行的圖也畫到圓底外面） */
    } else if (e.grp === "crest") {
      const k = size / 40; ctx.save(); ctx.scale(k, k); ctx.beginPath(); [[20, 2], [35.6, 11], [35.6, 29], [20, 38], [4.4, 29], [4.4, 11]].forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); ctx.fillStyle = "#161a2a"; ctx.fill(); ctx.lineWidth = 1.6; ctx.lineJoin = "round"; ctx.strokeStyle = GOLD; ctx.stroke();
      ctx.beginPath(); [[20, 5.5], [32.6, 12.8], [32.6, 27.2], [20, 34.5], [7.4, 27.2], [7.4, 12.8]].forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); ctx.globalAlpha = 0.55; ctx.lineWidth = 0.8; ctx.strokeStyle = REGION_ACCENT[e.region]; ctx.stroke(); ctx.restore(); /* 框照現行 RegionCrest 原樣 */
      const a = size * 0.6; QW.blit(ctx, glyph(id, a, res), (size - a) / 2, (size - a) / 2, a, res);
    } else if (e.card) {
      QW.blit(ctx, QP.cardCanvas(e.card, size, 1, { res }), 0, 0, size, res);
    } else if (e.d10) {
      QW.blit(ctx, cardLike(e.d10, size, res, e.grp === "pip" ? size * 0.96 : undefined), 0, 0, size, res); /* 源力圓點：晶石撐滿 9px 的圓點（卡片小圖留的 16% 邊在 9px 只剩 7px 的晶石） */
    } else QW.blit(ctx, glyph(id, size, res), 0, 0, size, res);
    ctx.restore();
  }
  /** 含框的圖示 canvas：顯示邊長 px×zoom；zoom 1 時內部解析度 ×2；放大時直接用向量畫到該倍率（簡化程度仍照 px）；opt.res＝1 是真 1 倍。 */
  function canvas(id, px, zoom = 1, opt = {}) { const res = opt.res ?? (zoom === 1 ? 2 : zoom), cv = blank(Math.round(px * res)); cv.style.width = cv.style.height = px * zoom + "px"; const x = cv.getContext("2d"); x.scale(res, res); paint(x, id, px, res, opt); x.setTransform(1, 0, 0, 1, 0, 0); return cv; }

  // ---------------- 圖釘：A＝第 4 批（紅頭／灰鋼）、B＝金頭（浮動卡的金色）；兩種並排，不由畫圖 agent 選 ----------------
  /** 13px 的圖釘（PinGlyph／PinIcon 的位置）：scheme a｜b｜off｜ink。A 與未釘直接呼叫第 4 批 cardCanvas；B、ink 照同一條路徑畫照抄的形。 */
  function pinCanvas(scheme, px = 13, zoom = 1, opt = {}) { const res = opt.res ?? (zoom === 1 ? 2 : zoom), cv = blank(Math.round(px * res)); cv.style.width = cv.style.height = px * zoom + "px"; const x = cv.getContext("2d");
    if (scheme === "a" || scheme === "off") x.drawImage(QP.cardCanvas("pin", px, 1, { res, pinned: scheme === "a" }), 0, 0);
    else { const g = cardLike((c, o) => pinArt(c, o, PIN[scheme]), px, res); x.scale(res, res); QW.blit(x, g, 0, 0, px, res); }
    return cv; }
  /** 釘住的說明卡右上角（.float-card.pinned::after）：18px 金色圓底（--ui-gold-hi）＋深藍 1.5px 外圈照現行，圓底裡 12px 的圖釘換 Q 版。scheme a（紅頭）｜b（深色剪影＝現行構圖的 Q 版；金頭放在金底上看不見）。 */
  function pinBadge(scheme, px = 18, zoom = 1, opt = {}) { const res = opt.res ?? (zoom === 1 ? 2 : zoom), pad = 1.5, S = px + pad * 2, cv = blank(Math.round(S * res)); cv.style.width = cv.style.height = S * zoom + "px"; const x = cv.getContext("2d"); x.scale(res, res);
    x.beginPath(); x.arc(S / 2, S / 2, px / 2 + 1.5, 0, TAU); x.fillStyle = "#1e2236"; x.fill(); x.beginPath(); x.arc(S / 2, S / 2, px / 2, 0, TAU); x.fillStyle = GOLD; x.fill();
    const g = scheme === "a" ? QP.cardCanvas("pin", 12, 1, { res, pinned: true }) : cardLike((cc, o) => pinArt(cc, o, PIN.ink), 12, res);
    QW.blit(x, g, (S - 12) / 2, (S - 12) / 2, 12, res); x.setTransform(1, 0, 0, 1, 0, 0); return cv; }

  const GRP_ZH = { bar: "功能列", gen: "通用小圖", tool: "戰鬥工具鈕", res: "資源小圖", set: "設定標題", pip: "源力圓點", crest: "區域紋章" };
  const list = (grp) => Object.entries(ICON).filter(([, e]) => !grp || e.grp === grp).map(([id, e]) => ({ id, ...e, min: Math.min(...e.sizes) }));
  return { ICON, PIN, REGION_ACCENT, GRP_ZH, CARD_BOX, cardPx, def, glyph, paint, canvas, pinCanvas, pinBadge, list, gearArt, crescent };
})();
