// 實地地圖上的標記（美術 PM，2026-11-04）：取代 6C-5 格子裡的「足／碑／火／！」文字方塊。
// 事件「！」、營火、朋友腳印、留言石碑、情境物件的提示光、敵人視野（併塊）、潛行時的畫面。C 手繪墨線，全部程式繪製，沒有亂數。
window.MapMarks = (() => {
  const { ink, stroke, ellPts } = StoryDoll.H, TAU = Math.PI * 2, T = 48;
  /** 確定性雜湊（FNV-1a），同 inkStyle.seedOf。 */
  function seed(s) { let h = 2166136261; for (const ch of String(s)) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619) >>> 0; } return h; }

  /** 事件「！」：浮在格子上方的金色泡泡，地上一圈淡光；t＝毫秒（上下浮動 3px，週期 1.6 秒）。 */
  function eventMark(ctx, gx, gy, t = 0) {
    const cx = gx * T + T / 2, cy = gy * T + T / 2, bob = Math.sin((t / 1600) * TAU) * 3;
    ctx.save();
    const g = ctx.createRadialGradient(cx, cy + 10, 2, cx, cy + 10, 22); g.addColorStop(0, "rgba(255,210,58,0.45)"); g.addColorStop(1, "rgba(255,210,58,0)");
    ctx.fillStyle = g; ctx.beginPath(); ctx.ellipse(cx, cy + 10, 22, 10, 0, 0, TAU); ctx.fill();
    ctx.translate(cx, cy - 16 + bob);
    ink(ctx, "ev-bubble", [[-11, -12], [11, -12], [12, 6], [4, 7], [0, 13], [-4, 7], [-12, 6]], "#ffd23a", { w: 1 });
    ink(ctx, "ev-bar", [[-2.2, -8], [2.2, -8], [1.4, 1], [-1.4, 1]], "#3a2410", { shade: false, w: 0.4 });
    ctx.fillStyle = "#3a2410"; ctx.beginPath(); ctx.arc(0, 4, 1.8, 0, TAU); ctx.fill();
    ctx.restore();
  }
  /** 營火：交叉的柴＋火苗＋地上暖光；lit＝false 時只剩柴和灰（今天已經紮過營）。 */
  function campfire(ctx, gx, gy, t = 0, lit = true) {
    const cx = gx * T + T / 2, cy = gy * T + T * 0.62;
    ctx.save();
    if (lit) { const g = ctx.createRadialGradient(cx, cy, 2, cx, cy, 30); g.addColorStop(0, "rgba(255,150,40,0.5)"); g.addColorStop(1, "rgba(255,150,40,0)"); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, 30, 0, TAU); ctx.fill(); }
    ctx.translate(cx, cy);
    for (let k = 0; k < 6; k++) { const a = (k / 6) * TAU; ink(ctx, `cf-stone${k}`, ellPts(Math.cos(a) * 13, Math.sin(a) * 6, 3.4, 2.6, 8), "#8a8a84", { w: 0.6 }); }
    ink(ctx, "cf-log1", [[-11, 2], [9, -5], [11, -2], [-9, 5]], "#7a4e2a", { w: 0.8 });
    ink(ctx, "cf-log2", [[-9, -5], [11, 2], [9, 5], [-11, -2]], "#8a5a30", { w: 0.8 });
    if (lit) {
      const f = 1 + Math.sin((t / 260) * TAU) * 0.08;
      ink(ctx, "cf-flame", [[-7, 0], [-5, -10 * f], [-1, -7], [0, -17 * f], [3, -8], [6, -12 * f], [7, 0]], "#ff7a2a", { shade: false, w: 0.8 });
      ink(ctx, "cf-core", [[-3.5, 0], [-1.5, -6 * f], [0, -9 * f], [2, -5 * f], [3.5, 0]], "#ffd23a", { shade: false, w: 0.4 });
    } else { ctx.fillStyle = "rgba(120,120,120,0.7)"; ctx.beginPath(); ctx.ellipse(0, 0, 6, 3, 0, 0, TAU); ctx.fill(); }
    ctx.restore();
  }
  /** 一個腳印（鞋底）：左右腳交替，朝 dir（弧度）；color＝朋友的顏色。 */
  function footprint(ctx, x, y, dir, left, color, alpha) {
    ctx.save(); ctx.translate(x, y); ctx.rotate(dir + Math.PI / 2); ctx.translate(left ? -4.4 : 4.4, 0); ctx.globalAlpha = alpha; ctx.fillStyle = color; ctx.strokeStyle = "rgba(40,30,20,0.55)"; ctx.lineWidth = 0.9;
    ctx.beginPath(); ctx.ellipse(0, -3, 3.2, 4.4, 0, 0, TAU); ctx.fill(); ctx.stroke(); ctx.beginPath(); ctx.ellipse(0, 4.6, 2.5, 2.8, 0, 0, TAU); ctx.fill(); ctx.stroke();
    ctx.restore();
  }
  /** 朋友的腳印：沿格子路徑，每格兩步；越舊越淡（第一格最淡）。 */
  function footprints(ctx, path, color = "#e8f0ff") {
    const n = path.length;
    for (let i = 0; i < n - 1; i++) {
      const [ax, ay] = path[i], [bx, by] = path[i + 1], dir = Math.atan2(by - ay, bx - ax);
      for (let s = 0; s < 2; s++) { const f = (s + 0.5) / 2, x = (ax + (bx - ax) * f) * T + T / 2, y = (ay + (by - ay) * f) * T + T / 2; footprint(ctx, x, y, dir, (i * 2 + s) % 2 === 0, color, 0.4 + 0.45 * (i / Math.max(1, n - 2))); }
    }
  }
  /** 留言石碑：直立的石板、刻線、一張釘著的紙；unread＞0 時右上一個紅點。 */
  function stele(ctx, gx, gy, unread = 0) {
    const cx = gx * T + T / 2, by = gy * T + T * 0.86;
    ctx.save(); ctx.fillStyle = "rgba(0,0,0,0.25)"; ctx.beginPath(); ctx.ellipse(cx, by, 14, 4, 0, 0, TAU); ctx.fill(); ctx.translate(cx, by);
    ink(ctx, "st-base", [[-14, 0], [14, 0], [12, -6], [-12, -6]], "#7a7a74", { w: 0.8 });
    ink(ctx, "st-slab", [[-10, -6], [10, -6], [10, -30], [6, -36], [-6, -36], [-10, -30]], "#a8a8a0", { w: 1 });
    for (const y of [-28, -23, -18]) stroke(ctx, `st-l${y}`, [[-6, y], [6, y]], 0.8, "#6a6a64");
    ink(ctx, "st-note", [[-1, -16], [9, -18], [10, -8], [0, -6]], "#f2e6c8", { shade: false, w: 0.6 });
    ctx.fillStyle = "#c83a2a"; ctx.beginPath(); ctx.arc(5, -16, 1.4, 0, TAU); ctx.fill();
    if (unread > 0) { ctx.beginPath(); ctx.arc(11, -36, 4.5, 0, TAU); ctx.fillStyle = "#e04a3a"; ctx.fill(); ctx.lineWidth = 1.2; ctx.strokeStyle = "#1c1712"; ctx.stroke(); }
    ctx.restore();
  }
  /** 情境物件的提示：主角在 1 格內時，物件底下一圈金色呼吸光＋右上小手；離開就不畫。 */
  function objectHint(ctx, gx, gy, t = 0) {
    const cx = gx * T + T / 2, cy = gy * T + T * 0.7, a = 0.35 + 0.2 * Math.sin((t / 1400) * TAU);
    ctx.save(); ctx.strokeStyle = `rgba(255,210,58,${a + 0.3})`; ctx.lineWidth = 2; ctx.setLineDash([4, 3]); ctx.beginPath(); ctx.ellipse(cx, cy, 19, 8, 0, 0, TAU); ctx.stroke(); ctx.setLineDash([]);
    ctx.translate(gx * T + T - 8, gy * T + 8);
    ink(ctx, "oh-bg", ellPts(0, 0, 7.5, 7.5, 14), "#2a241e", { shade: false, w: 0.7 });
    ink(ctx, "oh-hand", [[-3, 4], [-3, -1], [-1.5, -1], [-1.5, -5], [0.3, -5], [0.3, -1], [3.5, 0], [3.5, 4]], "#f2d898", { shade: false, w: 0.4 });
    ctx.restore();
  }
  /** 敵人視野：同戰鬥 D 版地表併塊，淡紅填色，只描外緣（虛線）；不畫格線、不畫格角記號。sneaking＝潛行時換成更淡、更短的虛線。 */
  function sightBlob(ctx, cells, sneaking = false) {
    const key = new Set(cells.map(([x, y]) => `${x},${y}`)), has = (x, y) => key.has(`${x},${y}`);
    ctx.save(); ctx.fillStyle = sneaking ? "rgba(224,74,58,0.10)" : "rgba(224,74,58,0.20)";
    const R = 9;
    for (const [x, y] of cells) {
      const l = !has(x - 1, y), r = !has(x + 1, y), u = !has(x, y - 1), d = !has(x, y + 1);
      ctx.beginPath(); ctx.roundRect(x * T, y * T, T, T, [u && l ? R : 0, u && r ? R : 0, d && r ? R : 0, d && l ? R : 0]); ctx.fill();
    }
    ctx.strokeStyle = sneaking ? "rgba(255,120,100,0.55)" : "rgba(255,110,90,0.9)"; ctx.lineWidth = 2; ctx.setLineDash(sneaking ? [3, 5] : [7, 4]); ctx.lineCap = "round";
    for (const [x, y] of cells) {
      const X = x * T, Y = y * T, l = !has(x - 1, y), r = !has(x + 1, y), u = !has(x, y - 1), d = !has(x, y + 1);
      ctx.beginPath();
      if (u) { ctx.moveTo(X + (l ? R : 0), Y); ctx.lineTo(X + T - (r ? R : 0), Y); }
      if (r) { ctx.moveTo(X + T, Y + (u ? R : 0)); ctx.lineTo(X + T, Y + T - (d ? R : 0)); }
      if (d) { ctx.moveTo(X + T - (r ? R : 0), Y + T); ctx.lineTo(X + (l ? R : 0), Y + T); }
      if (l) { ctx.moveTo(X, Y + T - (d ? R : 0)); ctx.lineTo(X, Y + (u ? R : 0)); }
      ctx.stroke();
      ctx.beginPath();
      if (u && l) ctx.arc(X + R, Y + R, R, Math.PI, Math.PI * 1.5);
      if (u && r) { ctx.moveTo(X + T - R, Y); ctx.arc(X + T - R, Y + R, R, Math.PI * 1.5, TAU); }
      if (d && r) { ctx.moveTo(X + T, Y + T - R); ctx.arc(X + T - R, Y + T - R, R, 0, Math.PI / 2); }
      if (d && l) { ctx.moveTo(X + R, Y + T); ctx.arc(X + R, Y + T - R, R, Math.PI / 2, Math.PI); }
      ctx.stroke();
    }
    ctx.restore();
  }
  /** 敵群頭上的眼睛：正在看（視野有效）時睜眼，潛行時半閉；放在敵群頭上，不放在格角。 */
  function watchEye(ctx, x, y, sneaking = false) {
    ctx.save(); ctx.translate(x, y);
    ink(ctx, "eye-bg", [[-9, 0], [-4, -5], [4, -5], [9, 0], [4, 5], [-4, 5]], "#f2e6c8", { shade: false, w: 0.8 });
    ctx.fillStyle = "#c83a2a"; ctx.beginPath(); ctx.arc(0, 0, 3, 0, TAU); ctx.fill();
    if (sneaking) { ctx.fillStyle = "#3a3450"; ctx.beginPath(); ctx.moveTo(-9.5, 0.5); ctx.lineTo(-4, -5.5); ctx.lineTo(4, -5.5); ctx.lineTo(9.5, 0.5); ctx.closePath(); ctx.fill(); }
    ctx.restore();
  }
  /** 潛行時的畫面：四周藍黑暗角＋主角半透明（主角另外畫）。 */
  function sneakVignette(ctx, w, h) {
    const g = ctx.createRadialGradient(w / 2, h / 2, Math.min(w, h) * 0.3, w / 2, h / 2, Math.max(w, h) * 0.7);
    g.addColorStop(0, "rgba(20,24,48,0)"); g.addColorStop(1, "rgba(20,24,48,0.55)"); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
  }
  return { T, seed, eventMark, campfire, footprints, stele, objectHint, sightBlob, watchEye, sneakVignette };
})();
