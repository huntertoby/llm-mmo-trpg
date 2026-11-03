// HUD 功能列 8 個圖示的定稿（美術 PM，2026-11-04）：I 背包、K 技能、G 成長、J 任務、Y 影子、N 留言、R 潛行（#120 21.4 取代趕路）、M 地圖。
// C 手繪墨線；每個圖示畫在 48×48。按鈕狀態：一般、滑過、開著（面板打開）、停用、有未讀（數字或紅點）、開關開著（R）。另有滑過說明卡的樣式。全部程式繪製。
window.HudIcons = (() => {
  const { ink, stroke, ellPts, INK } = StoryDoll.H, TAU = Math.PI * 2;
  const ICONS = {
    I: { zh: "背包", draw(c) { ink(c, "bag", [[11, 20], [37, 20], [40, 40], [8, 40]], "#a06a36", { w: 1 }); ink(c, "bag-flap", [[12, 20], [36, 20], [34, 29], [14, 29]], "#8a5a30", { w: 0.8 }); stroke(c, "bag-handle", [[17, 20], [18, 11], [30, 11], [31, 20]], 1.8, "#5a3a1e"); ink(c, "bag-clasp", [[21, 26], [27, 26], [27, 32], [21, 32]], "#e8bb48", { shade: false, w: 0.6 }); } },
    K: { zh: "技能", draw(c) { ink(c, "book", [[9, 10], [39, 10], [39, 40], [9, 40]], "#5a3a9a", { w: 1 }); ink(c, "book-pages", [[12, 10], [16, 10], [16, 40], [12, 40]], "#f2e6c8", { shade: false, w: 0.6 }); c.save(); c.shadowColor = "#a898ff"; c.shadowBlur = 8; ink(c, "book-gem", [[27, 18], [33, 25], [27, 32], [21, 25]], "#c8bcff", { shade: false, w: 0.7 }); c.restore(); } },
    G: { zh: "成長", draw(c) { stroke(c, "grow-stem", [[24, 42], [24, 14]], 2.6, "#4f8a3a"); ink(c, "grow-l", [[24, 30], [12, 24], [10, 16], [20, 20]], "#6aa84a", { w: 0.8 }); ink(c, "grow-r", [[24, 24], [36, 18], [38, 10], [28, 14]], "#6aa84a", { w: 0.8 }); ink(c, "grow-arrow", [[24, 4], [31, 13], [27, 13], [27, 18], [21, 18], [21, 13], [17, 13]], "#ffd23a", { shade: false, w: 0.7 }); } },
    J: { zh: "任務", draw(c) { ink(c, "scroll", [[12, 12], [36, 12], [36, 38], [12, 38]], "#f2e6c8", { w: 0.9 }); ink(c, "scroll-t", [[9, 8], [39, 8], [39, 13], [9, 13]], "#8a2f20", { shade: false, w: 0.7 }); ink(c, "scroll-b", [[9, 37], [39, 37], [39, 42], [9, 42]], "#8a2f20", { shade: false, w: 0.7 }); for (const y of [19, 25, 31]) stroke(c, `scroll-l${y}`, [[16, y], [30, y]], 0.8, "#8a7a5a"); ink(c, "scroll-bang", [[30, 16], [34, 16], [33, 26], [31, 26]], "#c83a2a", { shade: false, w: 0.5 }); } },
    Y: { zh: "影子", draw(c) { ink(c, "sh-head", ellPts(24, 16, 7, 7, 14), "#3a3450", { w: 0.9 }); ink(c, "sh-body", [[12, 42], [14, 28], [24, 24], [34, 28], [36, 42]], "#3a3450", { w: 0.9 }); c.save(); c.setLineDash([2, 2]); stroke(c, "sh-ghost", [[34, 14], [40, 10], [44, 16], [42, 26]], 1, "#a898ff"); c.restore(); for (const x of [21, 27]) { c.fillStyle = "#c8bcff"; c.beginPath(); c.arc(x, 16, 1.2, 0, TAU); c.fill(); } } },
    N: { zh: "留言", draw(c) { ink(c, "note", [[8, 10], [40, 10], [40, 32], [22, 32], [14, 40], [15, 32], [8, 32]], "#f2e6c8", { w: 0.9 }); for (const y of [17, 23]) stroke(c, `note-l${y}`, [[13, y], [35, y]], 0.8, "#8a7a5a"); ink(c, "note-pin", ellPts(36, 12, 3, 3, 10), "#c83a2a", { shade: false, w: 0.5 }); } },
    R: { zh: "潛行", draw(c) { ink(c, "sneak-hood", [[14, 22], [18, 10], [30, 8], [38, 18], [36, 30], [24, 26]], "#3a3a44", { w: 0.9 }); ink(c, "sneak-face", [[22, 18], [32, 16], [33, 24], [24, 25]], "#1a1a20", { shade: false, w: 0.5 }); for (const x of [26, 30]) { c.fillStyle = "#c8f0ff"; c.beginPath(); c.arc(x, 20, 1.1, 0, TAU); c.fill(); } c.save(); c.setLineDash([3, 3]); stroke(c, "sneak-trail", [[8, 40], [18, 36], [28, 40], [40, 36]], 1.2, "#8a8aa8"); c.restore(); } },
    M: { zh: "地圖", draw(c) { ink(c, "map", [[6, 12], [18, 8], [30, 12], [42, 8], [42, 38], [30, 42], [18, 38], [6, 42]], "#e8dcb8", { w: 0.9 }); stroke(c, "map-f1", [[18, 8], [18, 38]], 0.7, "#8a7a5a"); stroke(c, "map-f2", [[30, 12], [30, 42]], 0.7, "#8a7a5a"); stroke(c, "map-route", [[10, 34], [16, 26], [24, 28], [34, 18]], 1, "#8a6a3a"); c.save(); c.shadowColor = "#5ac8f0"; c.shadowBlur = 5; c.fillStyle = "#5aa0ff"; c.beginPath(); c.arc(34, 18, 3, 0, TAU); c.fill(); c.restore(); } },
  };
  const ORDER = ["I", "K", "G", "J", "Y", "N", "R", "M"];
  /** 按鈕：state＝normal｜hover｜open｜disabled｜on；badge＝數字字串或 "dot"。 */
  function button(ctx, x, y, size, key, state = "normal", badge = null) {
    const fill = state === "open" || state === "on" ? "rgba(90,70,30,0.95)" : state === "hover" ? "rgba(48,40,30,0.95)" : "rgba(24,20,16,0.88)";
    const rim = state === "open" || state === "on" ? "#ffd23a" : state === "hover" ? "#f2d898" : "#c8a868";
    ctx.save(); ctx.translate(x, y);
    if (state === "hover") { ctx.shadowColor = "rgba(255,220,140,0.6)"; ctx.shadowBlur = 10; }
    ctx.beginPath(); ctx.roundRect(0, 0, size, size, size * 0.18); ctx.fillStyle = fill; ctx.fill(); ctx.shadowBlur = 0; ctx.lineWidth = Math.max(1.5, size * 0.045); ctx.strokeStyle = rim; ctx.stroke();
    ctx.save(); if (state === "disabled") { ctx.globalAlpha = 0.35; ctx.filter = "grayscale(1)"; }
    const pad = size * 0.12; ctx.translate(pad, pad * 0.8); ctx.scale((size - pad * 2) / 48, (size - pad * 2) / 48); ICONS[key].draw(ctx); ctx.restore();
    if (size >= 36) { ctx.font = `bold ${Math.round(size * 0.2)}px Consolas, monospace`; ctx.textAlign = "right"; ctx.textBaseline = "alphabetic"; ctx.fillStyle = "rgba(242,230,200,0.75)"; ctx.fillText(key, size - 4, size - 4); ctx.textAlign = "left"; }
    if (badge) { const r = size * 0.16; ctx.beginPath(); if (badge === "dot") ctx.arc(size - r * 0.6, r * 0.6, r * 0.6, 0, TAU); else ctx.roundRect(size - r * 2.2, -r * 0.5, r * 2.4, r * 2, r); ctx.fillStyle = "#e04a3a"; ctx.fill(); ctx.lineWidth = 1.2; ctx.strokeStyle = "#1c1712"; ctx.stroke(); if (badge !== "dot") { ctx.fillStyle = "#fff"; ctx.font = `bold ${Math.round(r * 1.3)}px Consolas`; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(badge, size - r, r * 0.5); ctx.textAlign = "left"; } }
    ctx.restore();
  }
  /** 滑過說明卡：標題列（圖示＋名稱＋快捷鍵）、目前狀態一行、說明一句；底下小字是觸控的操作。 */
  function card(ctx, x, y, key, status, desc, w = 250) {
    ctx.save(); ctx.translate(x, y);
    ctx.shadowColor = "rgba(0,0,0,0.5)"; ctx.shadowBlur = 10; ctx.shadowOffsetY = 3;
    ctx.beginPath(); ctx.roundRect(0, 0, w, 96, 10); ctx.fillStyle = "rgba(30,26,22,0.97)"; ctx.fill(); ctx.shadowColor = "transparent"; ctx.lineWidth = 1.5; ctx.strokeStyle = "#c8a868"; ctx.stroke();
    ctx.save(); ctx.translate(10, 8); ctx.scale(24 / 48, 24 / 48); ICONS[key].draw(ctx); ctx.restore();
    ctx.fillStyle = "#f2e6c8"; ctx.font = "bold 14px 'Microsoft JhengHei'"; ctx.textBaseline = "middle"; ctx.fillText(ICONS[key].zh, 42, 20);
    ctx.fillStyle = "#2a241e"; ctx.beginPath(); ctx.roundRect(w - 34, 10, 24, 20, 4); ctx.fill(); ctx.strokeStyle = "#8a7a5a"; ctx.lineWidth = 1; ctx.stroke(); ctx.fillStyle = "#f2e6c8"; ctx.font = "bold 12px Consolas"; ctx.textAlign = "center"; ctx.fillText(key, w - 22, 21); ctx.textAlign = "left";
    ctx.strokeStyle = "rgba(200,168,104,0.35)"; ctx.beginPath(); ctx.moveTo(10, 36); ctx.lineTo(w - 10, 36); ctx.stroke();
    ctx.fillStyle = "#ffd23a"; ctx.font = "bold 12.5px 'Microsoft JhengHei'"; ctx.fillText(status, 12, 50);
    ctx.fillStyle = "#d8ccb8"; ctx.font = "12px 'Microsoft JhengHei'"; ctx.fillText(desc, 12, 70);
    ctx.fillStyle = "#8a7e6c"; ctx.font = "10.5px 'Microsoft JhengHei'"; ctx.fillText("觸控：長按 0.4 秒看這張；點一下就打開", 12, 87);
    ctx.restore();
  }
  return { ICONS, ORDER, button, card };
})();
