// 敵人外觀（異形）：C 手繪墨線繪本畫風（沿用 storyDoll.js 的畫法層 StoryDoll.H）。
// 規則：外觀 ＝ 身形 body × 材質 material × 元素 element × 大小 size × 精英詞綴 affixes。不認得的值一律退回，不出錯：
//   body 不認得 → ooze（一團，什麼都說得通）；material 不認得 → fur；element 不認得 → 沒有元素；affix 不認得 → 只畫精英金環。
// 座標：腳底 (0,0)、往上是 -y、朝東（+x 是前方）；朝西由呼叫端鏡像；正面、背面沿用側面（同形態、野獸召喚物）。
window.EnemyArt = (() => {
  const { ink, stroke, limb, dot, ellPts, shadow, mix, dark, light, INK, setShade } = StoryDoll.H;
  const TAU = Math.PI * 2;
  function seedOf(s) { let h = 2166136261; for (const ch of s) h = Math.imul(h ^ ch.charCodeAt(0), 16777619); return h >>> 0; }
  function rng(seed) { let s = seed >>> 0; return () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296); }
  const bbox = (pts) => { let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity; for (const [x, y] of pts) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); } return { x0, x1, y0, y1 }; };
  const path = (ctx, pts) => { ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); };

  // 元素色（palette.ts 同一份）
  const ELEM = {
    fire: ["#ff6a1a", "#ffd04a"], ice: ["#8fe3ff", "#e8fbff"], lightning: ["#fff36b", "#fff7c0"], poison: ["#7ddc3a", "#d6f59a"],
    wind: ["#c8ffe8", "#effff8"], earth: ["#b0814a", "#e6c89a"], holy: ["#fff2b0", "#fffbe0"], shadow: ["#9a6ad8", "#c8a8f0"], water: ["#3a7bd5", "#d8f0ff"],
  };
  const CRYSTAL = "#9a86ff"; // 源晶藍紫（形態光環、魔導劍同色）
  const BASALT = "#3b2c28";

  // ---- 材質 → 色票 ----
  function palette(spec, body) {
    const mat = MATERIALS.includes(spec.material) ? spec.material : "fur";
    const el = ELEM[spec.element];
    let base, accent, eye;
    if (mat === "magma") { base = spec.tint ?? BASALT; accent = el ? el[0] : ELEM.fire[0]; eye = el ? el[1] : ELEM.fire[1]; }
    else if (mat === "stone") { base = spec.tint ?? "#7f8f94"; accent = el ? el[0] : "#8fe3ff"; eye = el ? el[1] : "#e8fbff"; }
    else if (mat === "wood") { base = spec.tint ?? "#a8763e"; accent = el ? el[0] : null; eye = "#2b1e16"; }
    else if (mat === "mist") { base = spec.tint ?? (el ? mix("#e6ecef", el[0], 0.45) : "#e6ecef"); accent = el ? el[0] : "#b8c4cc"; eye = el ? el[1] : "#5a6a7a"; }
    else if (mat === "crystal") { base = el ? mix(CRYSTAL, el[0], 0.4) : (spec.tint ?? CRYSTAL); accent = el ? el[1] : "#e4dcff"; eye = "#ffffff"; }
    else { base = spec.tint ?? body.fur; if (el) base = mix(base, el[0], 0.22); accent = el ? el[0] : null; eye = el ? el[1] : "#ffd23a"; }
    return { mat, base, d: dark(base, 0.28), l: light(base, 0.3), accent, eye, sharp: mat === "crystal" || mat === "stone", alpha: mat === "mist" ? 0.62 : undefined };
  }

  // ---- 材質表面：毛（背上短毛）、熔岩（裂縫透光＋火星）、源晶（切面＋晶刺） ----
  function cracks(ctx, key, pts, P) {
    const b = bbox(pts), r = rng(seedOf(key)), n = b.x1 - b.x0 > 18 ? 2 : 1;
    ctx.save(); path(ctx, pts); ctx.clip();
    for (let i = 0; i < n; i++) {
      const y = b.y0 + (b.y1 - b.y0) * (0.35 + 0.3 * i), line = [];
      for (let x = b.x0 + 2; x <= b.x1 - 2; x += 3.2) line.push([x, y + (r() - 0.5) * 4]);
      if (line.length < 2) continue;
      stroke(ctx, `${key}-ck${i}a`, line, 1.7, "#7a2a08");
      stroke(ctx, `${key}-ck${i}b`, line, 0.8, P.accent);
    }
    ctx.restore();
  }
  function facets(ctx, key, pts, P) {
    const b = bbox(pts);
    ctx.save(); path(ctx, pts); ctx.clip();
    const w = b.x1 - b.x0, h = b.y1 - b.y0;
    stroke(ctx, `${key}-f1`, [[b.x0 + w * 0.25, b.y0], [b.x0 + w * 0.45, b.y1]], 0.6, light(P.base, 0.5));
    stroke(ctx, `${key}-f2`, [[b.x0 + w * 0.6, b.y0], [b.x0 + w * 0.5, b.y0 + h * 0.6], [b.x1, b.y0 + h * 0.7]], 0.6, light(P.base, 0.5));
    ctx.restore();
  }
  function runes(ctx, key, pts, P) {
    const b = bbox(pts), cx = (b.x0 + b.x1) / 2, cy = (b.y0 + b.y1) / 2;
    const rune = [[cx - 3, cy - 3], [cx, cy - 4.4], [cx + 3, cy - 3], [cx, cy], [cx - 2.4, cy + 2.6], [cx + 2.4, cy + 2.6]];
    ctx.save(); path(ctx, pts); ctx.clip();
    stroke(ctx, `${key}-rn1`, rune, 1.4, dark(P.base, 0.35));
    stroke(ctx, `${key}-rn2`, rune, 0.7, P.accent);
    ctx.restore();
  }
  function grain(ctx, key, pts, P) {
    const b = bbox(pts);
    ctx.save(); path(ctx, pts); ctx.clip();
    for (let i = 1; i <= 2; i++) { const y = b.y0 + ((b.y1 - b.y0) * i) / 3; stroke(ctx, `${key}-gr${i}`, [[b.x0, y], [(b.x0 + b.x1) / 2, y - 0.8], [b.x1, y + 0.4]], 0.45, P.d); }
    ctx.restore();
  }
  function mass(ctx, key, pts, P, opt = {}) {
    ink(ctx, key, pts, opt.color ?? P.base, { sharp: P.sharp, ...(P.alpha ? { alpha: P.alpha } : {}), ...opt });
    if (!opt.main) return;
    if (P.mat === "magma") cracks(ctx, key, pts, P);
    else if (P.mat === "crystal") facets(ctx, key, pts, P);
    else if (P.mat === "stone") runes(ctx, key, pts, P);
    else if (P.mat === "wood") grain(ctx, key, pts, P);
  }
  function back(ctx, key, list, P) {
    list.forEach(([x, y], i) => {
      if (P.mat === "crystal") {
        const h = 5 + (i % 2) * 2.4;
        ink(ctx, `${key}-sh${i}`, [[x - 2, y + 1], [x + 0.6, y - h], [x + 2.4, y + 1]], light(P.base, 0.25), { sharp: true, shade: false, w: 0.6 });
        stroke(ctx, `${key}-shl${i}`, [[x + 0.2, y - h + 1.4], [x - 0.6, y]], 0.5, "#ffffff");
      } else if (P.mat === "stone") {
        dot(ctx, x, y + 0.6, 1.6, 0.8, "#6a8a4a");
      } else if (P.mat === "wood" || P.mat === "mist") {
        // 木頭、霧：背上不加東西
      } else if (P.mat === "magma") {
        dot(ctx, x + 1, y - 3 - (i % 2) * 2.4, 0.7, 0.7, P.accent);
      } else {
        stroke(ctx, `${key}-tuft${i}`, [[x - 1.6, y + 0.6], [x, y - 2.4], [x + 1.2, y + 0.4]], 0.6, P.d);
      }
    });
  }
  const eye = (ctx, x, y, P, r = 1) => { dot(ctx, x, y, 1.15 * r, 0.9 * r, P.eye); dot(ctx, x + 0.2, y, 0.32 * r, 0.75 * r, INK); };
  const fang = (ctx, key, x, y, h = 2) => ink(ctx, key, [[x - 0.7, y], [x, y + h], [x + 0.7, y]], "#f4ecd8", { shade: false, w: 0.35, sharp: true });

  // ============================== 身形 ==============================
  // 每種身形：fur 預設毛色、top 最高點（頭頂狀態列避開）、head 頭的位置（詞綴特效用）、len 身長的一半、draw。
  const BODIES = {
    hound: { zh: "犬狼", fur: "#7a7a82", top: -36, head: [20, -28], len: 24, sp: [[-10, -25], [-4, -25.6], [2, -25.4]], draw(ctx, P) {
      for (const x of [-12, 6]) mass(ctx, `hd-lf${x}`, [[x, -12], [x + 4, -12], [x + 4.4, 0], [x - 0.4, 0]], P, { color: P.d });
      mass(ctx, "hd-tail", [[-14, -20], [-22, -25], [-26, -21], [-20, -17], [-13, -15]], P);
      const body = [[-16, -12], [-17, -20], [-10, -25], [4, -25], [12, -22], [13, -12], [0, -10]];
      mass(ctx, "hd-body", body, P, { main: true });
      back(ctx, "hd", [[-10, -25], [-4, -25.6], [2, -25.4]], P);
      for (const x of [-9, 8]) mass(ctx, `hd-l${x}`, [[x, -13], [x + 4, -13], [x + 4.6, 0], [x - 0.4, 0]], P);
      mass(ctx, "hd-ear", [[12, -29], [13, -36], [16.4, -30]], P, { color: P.d, w: 0.7, sharp: true });
      mass(ctx, "hd-head", [[8, -22], [11, -30], [17, -31], [22, -28], [28, -26], [28, -23], [21, -21], [14, -18]], P, { main: true });
      dot(ctx, 28, -25, 0.9, 0.8, INK); eye(ctx, 19, -27.4, P); fang(ctx, "hd-fang", 24, -22.2);
    } },
    boar: { zh: "野豬", fur: "#6a4a36", top: -28, head: [16, -18], len: 22, sp: [[-8, -24], [-1, -25], [6, -23]], draw(ctx, P) {
      for (const x of [-10, 6]) mass(ctx, `bo-lf${x}`, [[x, -9], [x + 4, -9], [x + 4, 0], [x, 0]], P, { color: P.d });
      stroke(ctx, "bo-tail", [[-15, -16], [-18, -18], [-17.4, -20]], 0.8);
      const body = [[-15, -8], [-16, -18], [-8, -24], [4, -25], [12, -20], [13, -9], [0, -7]];
      mass(ctx, "bo-body", body, P, { main: true });
      for (const [i, x] of [-11, -6, -1, 4].entries()) ink(ctx, `bo-br${i}`, [[x - 2, -23 - (x > -8 ? 1 : 0)], [x, -27.4], [x + 2, -24]], P.d, { sharp: true, shade: false, w: 0.5 });
      back(ctx, "bo", [[-8, -24], [6, -23]], P);
      for (const x of [-7, 8]) mass(ctx, `bo-l${x}`, [[x, -9], [x + 4, -9], [x + 4, 0], [x, 0]], P);
      mass(ctx, "bo-ear", [[11, -21], [12, -26], [15, -21]], P, { color: P.d, w: 0.6, sharp: true });
      mass(ctx, "bo-head", [[9, -22], [16, -21], [22, -16], [23, -11], [17, -9], [10, -11]], P, { main: true });
      ink(ctx, "bo-snout", ellPts(22.4, -13.2, 2.2, 2.8, 10), P.l, { shade: false, w: 0.6 });
      ink(ctx, "bo-tusk", [[18.6, -11.4], [21.4, -17.4], [20.4, -11]], "#f4ecd8", { sharp: true, shade: false, w: 0.45 });
      eye(ctx, 16.6, -17.4, P, 0.9);
    } },
    bear: { zh: "熊", fur: "#6a4a32", top: -33, head: [18, -26], len: 22, sp: [[-10, -28.4], [-3, -29.8], [4, -29.2]], draw(ctx, P) {
      for (const x of [-11, 6]) mass(ctx, `be-lf${x}`, [[x - 2.8, -12], [x + 2.8, -12], [x + 3, 0], [x - 3, 0]], P, { color: P.d });
      mass(ctx, "be-body", [[-17, -9], [-17, -22], [-8, -29.6], [4, -29], [14, -22], [15, -9], [-2, -7]], P, { main: true });
      back(ctx, "be", [[-10, -28.4], [-3, -29.8], [4, -29.2]], P);
      for (const x of [-6, 11]) mass(ctx, `be-l${x}`, [[x - 3, -12], [x + 3, -12], [x + 3.4, 0], [x - 3.2, 0]], P);
      mass(ctx, "be-head", [[9, -26], [14, -31], [21, -29.4], [25.6, -23], [23.6, -19.6], [16, -18], [10, -20]], P, { main: true });
      mass(ctx, "be-ear", ellPts(13.6, -30.6, 2.2, 2.2, 10), P, { shade: false, w: 0.7 });
      ink(ctx, "be-snout", ellPts(23.4, -22.2, 2.6, 2, 10), P.l, { shade: false, w: 0.6 });
      dot(ctx, 25.2, -23, 0.9, 0.8, INK); eye(ctx, 18.6, -25.6, P, 0.9);
    } },
    flyer: { zh: "飛禽", fur: "#a07a4a", top: -50, head: [9, -22], len: 20, hover: true, sp: [[-4, -22], [0, -24], [4, -22]], draw(ctx, P, v) {
      ctx.save(); ctx.translate(0, -18);
      if (v === "bat") {
        mass(ctx, "fl-bwf", [[-1, -3], [-10, -16], [-20, -14], [-17, -9], [-22, -6], [-15, -3], [-16, 2], [-4, 1]], P, { color: P.d });
        mass(ctx, "fl-bbody", ellPts(0, 0, 6, 7, 16), P, { main: true });
        mass(ctx, "fl-bwn", [[1, -3], [10, -18], [21, -17], [18, -11], [24, -8], [16, -4], [17, 1], [4, 1]], P, { main: true });
        for (const [x, t] of [[3, -14], [7.4, -14.6]]) mass(ctx, `fl-be${x}`, [[x - 1.6, -8.4], [x, t], [x + 1.6, -8.4]], P, { sharp: true, w: 0.6 });
        mass(ctx, "fl-bhead", ellPts(5, -6.4, 4, 3.6, 12), P);
        eye(ctx, 7, -7, P, 0.8); fang(ctx, "fl-bfang", 7.6, -3.6, 1.6);
        back(ctx, "fl-b", [[10, -18], [-10, -16]], P);
      } else {
        mass(ctx, "fl-wf", [[-2, -4], [-12, -26], [-20, -30], [-16, -22], [-22, -24], [-14, -12], [-4, 2]], P, { color: P.d, sharp: true });
        mass(ctx, "fl-tail", [[-8, 2], [-18, 8], [-16, 2], [-20, 4], [-9, -1]], P, { color: P.d, sharp: true, shade: false, w: 0.6 });
        mass(ctx, "fl-body", ellPts(0, 0, 9, 6, 16), P, { main: true });
        ink(ctx, "fl-belly", ellPts(1.5, 2, 6, 3, 12), P.mat === "fur" ? "#f0e6d0" : P.l, { shade: false, w: 0.5 });
        mass(ctx, "fl-wn", [[2, -4], [10, -28], [18, -34], [15, -24], [22, -27], [14, -12], [4, 2]], P, { main: true, sharp: true });
        mass(ctx, "fl-head", ellPts(9, -4, 4.2, 4.2, 12), P);
        ink(ctx, "fl-beak", [[12.5, -5.2], [17, -3], [12.5, -1]], "#e8bb48", { sharp: true, shade: false, w: 0.5 });
        eye(ctx, 10.6, -5, P, 0.8);
        for (const x of [-2, 3]) stroke(ctx, `fl-claw${x}`, [[x, 5], [x, 9]], 1.4, "#e8bb48");
        back(ctx, "fl", [[10, -28], [18, -34]], P);
      }
      ctx.restore();
    } },
    crawler: { zh: "爬蟲", fur: "#3a3440", top: -24, head: [15, -12], len: 18, sp: [[-8, -20], [-2, -20.4]], draw(ctx, P, v) {
      if (v === "spider") {
        const legs = [[[1, -10], [-6, -19], [-13, 0]], [[3, -10], [0, -21], [-4, 0]], [[5, -10], [9, -21], [8, 0]], [[7, -10], [16, -18], [18, 0]]];
        legs.forEach((l, i) => limb(ctx, `sp-lf${i}`, l.map(([x, y]) => [x - 2.2, y - 0.6]), 0.9, P.d));
        mass(ctx, "sp-abd", ellPts(-9, -12, 9, 8, 18), P, { main: true });
        back(ctx, "sp", [[-12, -19.6], [-6, -19.4]], P);
        stroke(ctx, "sp-mark", [[-11, -15], [-8, -11], [-11, -8]], 1.2, P.accent ?? "#c0392b");
        mass(ctx, "sp-head", ellPts(5, -9, 6, 5, 14), P);
        legs.forEach((l, i) => limb(ctx, `sp-l${i}`, l, 1, P.base));
        for (const [x, y] of [[9.4, -11], [10.6, -9.4], [8.6, -9.2]]) dot(ctx, x, y, 0.7, 0.7, P.eye);
        fang(ctx, "sp-fang", 10, -6, 2);
      } else {
        const legs = [[[-8, -6], [-12, -3], [-13, 0]], [[0, -6], [-1, -2], [-2, 0]], [[7, -6], [9, -3], [11, 0]]];
        legs.forEach((l, i) => limb(ctx, `bt-lf${i}`, l.map(([x, y]) => [x + 2, y]), 0.8, P.d));
        const shell = [[-14, -8], [-13, -15], [-6, -20], [4, -20], [11, -15], [12, -8], [0, -6]];
        mass(ctx, "bt-shell", shell, P, { main: true });
        stroke(ctx, "bt-seam", [[-13, -10], [-4, -14.6], [8, -16.6]], 0.6);
        back(ctx, "bt", [[-6, -20], [1, -20.4]], P);
        mass(ctx, "bt-head", [[11, -14], [16, -15], [19, -11], [17, -7], [11, -7]], P, { color: P.d });
        mass(ctx, "bt-horn", [[16, -13.4], [23, -18], [19.4, -11]], P, { color: P.l, sharp: true, shade: false, w: 0.6 });
        legs.forEach((l, i) => limb(ctx, `bt-l${i}`, l, 0.9, P.base));
        eye(ctx, 15.6, -11.6, P, 0.8);
      }
    } },
    lizard: { zh: "蜥蜴", fur: "#6a7a3a", top: -19, core: [2, -7.4], head: [20, -12], len: 30, sp: [[-6, -13.6], [-1, -14], [4, -13.6]], draw(ctx, P) {
      for (const x of [-6, 9]) mass(ctx, `lz-lf${x}`, [[x - 2, -6], [x + 2, -6], [x + 1, 0], [x - 3, 0]], P, { color: P.d });
      mass(ctx, "lz-tail", [[-8, -10], [-20, -9], [-30, -3], [-32, -1], [-22, -4], [-8, -5]], P, { main: true });
      mass(ctx, "lz-body", [[-10, -5], [-10, -11], [-2, -14], [10, -13], [14, -9], [12, -5], [0, -4]], P, { main: true });
      for (const x of [-6, -1, 4]) ink(ctx, `lz-sp${x}`, [[x - 2, -13.4], [x, -18.4], [x + 2, -13.6]], P.mat === "fur" ? "#c0392b" : P.l, { sharp: true, shade: false, w: 0.5 });
      back(ctx, "lz", [[-14, -9], [8, -13]], P);
      for (const x of [-7, 10]) mass(ctx, `lz-l${x}`, [[x - 2, -7], [x + 2, -7], [x + 3, 0], [x - 2.6, 0]], P);
      mass(ctx, "lz-head", [[12, -12], [16, -15], [23, -14], [27, -11], [26, -9], [18, -8], [13, -8]], P, { main: true });
      eye(ctx, 19, -12.4, P, 0.85);
    } },
    serpent: { zh: "蛇", fur: "#5a7a3a", top: -30, head: [12, -26], len: 17, sp: [[-10, -7], [-1, -10.4]], draw(ctx, P) {
      mass(ctx, "sn-coil", ellPts(-4, -3.6, 13, 4.2, 20), P, { main: true });
      mass(ctx, "sn-coil2", ellPts(-2, -7.4, 8.4, 3.2, 16), P, { color: P.d });
      mass(ctx, "sn-neck", [[1, -6], [8, -6], [10, -16], [9, -24], [4, -24], [5, -16]], P, { main: true });
      stroke(ctx, "sn-belly", [[8.6, -7], [9.4, -16], [8.4, -23]], 1.4, P.mat === "fur" ? "#e8dca0" : P.l);
      back(ctx, "sn", [[-10, -7], [-1, -10.4]], P);
      mass(ctx, "sn-head", [[3, -25], [8, -29.4], [15, -28.4], [18.4, -25], [14, -22], [6, -22]], P, { main: true });
      stroke(ctx, "sn-tongue", [[18.4, -24.6], [21.6, -24.6], [23, -26]], 0.5, "#d23c3c"); stroke(ctx, "sn-tongue2", [[21.6, -24.6], [23, -23.4]], 0.5, "#d23c3c");
      eye(ctx, 12, -26.4, P, 0.85);
    } },
    shell: { zh: "龜殼", fur: "#5a6a4a", top: -23, head: [16, -9], len: 20, sp: [[-9, -21], [-2, -22.6], [5, -21.4]], draw(ctx, P) {
      for (const x of [-9, 6]) mass(ctx, `sh-lf${x}`, [[x - 3, -7], [x + 2, -7], [x + 2, 0], [x - 3.4, 0]], P, { color: P.d });
      const dome = [[-15, -6], [-14, -15], [-7, -22], [4, -22], [11, -16], [12, -6], [0, -5]];
      mass(ctx, "sh-dome", dome, P, { main: true });
      for (const [i, l] of [[[-8, -21], [-9, -7]], [[3, -21], [2, -7]], [[-14, -12.4], [11.4, -12.4]]].entries()) stroke(ctx, `sh-plate${i}`, l, 0.6);
      stroke(ctx, "sh-rim", [[-16, -6], [13, -6]], 2.2, INK); stroke(ctx, "sh-rim2", [[-16, -6], [13, -6]], 1.2, P.l);
      back(ctx, "sh", [[-9, -21], [-2, -22.6], [5, -21.4]], P);
      for (const x of [-11, 5]) mass(ctx, `sh-l${x}`, [[x, -7], [x + 5, -7], [x + 5.6, 0], [x - 0.4, 0]], P, { color: P.l });
      mass(ctx, "sh-head", [[11, -11], [16, -12], [20, -9], [19, -5], [13, -5]], P, { color: P.l });
      eye(ctx, 17, -9.4, P, 0.8);
    } },
    ooze: { zh: "軟泥", fur: "#6a9a5a", top: -18, head: [6, -10], len: 15, sp: [[-6, -15], [2, -16.6]], draw(ctx, P) {
      ctx.save(); ctx.globalAlpha = 0.4; ctx.fillStyle = P.d; ctx.beginPath(); ctx.ellipse(0, 0.4, 16, 2.6, 0, 0, TAU); ctx.fill(); ctx.restore();
      const blob = [[-13, 0], [-14, -6], [-10, -13], [-3, -17], [5, -16], [11, -11], [13, -4], [12, 0]];
      mass(ctx, "oz-blob", blob, P, { main: true, alpha: 0.9 });
      for (const [x, y, r] of [[-6, -6, 1.8], [-2, -11, 1.2], [8, -5, 1.4]]) ink(ctx, `oz-bub${x}`, ellPts(x, y, r, r, 8), P.l, { shade: false, w: 0.4 });
      back(ctx, "oz", [[-6, -15], [2, -16.6]], P);
      eye(ctx, 4.6, -10, P, 0.9); eye(ctx, 8.4, -10.2, P, 0.8);
    } },
    golem: { zh: "傀儡", core: [-1, -29], fur: "#8a847e", top: -49, head: [2, -44], len: 17, sp: [[-9, -38.4], [-3, -39.6], [3, -40]], draw(ctx, P) {
      mass(ctx, "go-legf", [[-7, -16], [-1, -16], [-1.6, 0], [-8, 0]], P, { color: P.d });
      mass(ctx, "go-armf", [[-10, -37], [-15, -34], [-17, -18], [-12, -17], [-11, -30]], P, { color: P.d });
      mass(ctx, "go-legn", [[0, -16], [6, -16], [6.6, 0], [-0.4, 0]], P);
      const torso = [[-11, -38], [8, -40], [12, -30], [9, -16], [-9, -16], [-12, -28]];
      mass(ctx, "go-torso", torso, P, { main: true });
      back(ctx, "go", [[-9, -38.4], [-3, -39.6]], P);
      mass(ctx, "go-head", [[-4, -40], [-3, -47], [4, -48], [7, -43], [5, -39]], P);
      ink(ctx, "go-eye", [[2.4, -44.6], [6.4, -44.6], [6.4, -43], [2.4, -43]], P.accent ?? "#ffd23a", { shade: false, w: 0.4, sharp: true });
      mass(ctx, "go-arm", [[4, -38], [11, -38], [16, -24], [16, -14], [10, -14], [9, -24]], P, { main: true });
      mass(ctx, "go-fist", ellPts(13, -12, 4, 3.6, 12), P);
    } },
    wisp: { zh: "晶靈", fur: "#9a86ff", top: -34, core: [0, -20], head: [0, -22], len: 12, hover: true, sp: [[0, -31]], draw(ctx, P) {
      ctx.save(); ctx.translate(0, -20);
      for (const [i, [x, y, s]] of [[-11, -5, 2.4], [10, -8, 2], [3, 9, 1.8]].entries()) mass(ctx, `wp-or${i}`, [[x, y - s * 1.6], [x + s, y], [x, y + s * 1.6], [x - s, y]], P, { sharp: true, shade: false, w: 0.5, color: P.l });
      const core = [[0, -11], [7.4, 0], [0, 11], [-7.4, 0]];
      mass(ctx, "wp-core", core, P, { main: true, sharp: true });
      ink(ctx, "wp-in", [[0, -5], [3.4, 0], [0, 5], [-3.4, 0]], P.accent ?? P.eye, { sharp: true, shade: false, w: 0.4 });
      dot(ctx, 1.2, -0.6, 0.9, 1.3, INK);
      ctx.restore();
    } },
    feline: { zh: "豹", fur: "#c8a060", top: -23, head: [15, -15], len: 22, sp: [[-8, -15], [-2, -16], [4, -15.6]], draw(ctx, P) {
      for (const x of [-8, 10]) mass(ctx, `fe-lf${x}`, [[x - 1.6, -9], [x + 1.6, -9], [x + 1.8, 0], [x - 1.8, 0]], P, { color: P.d, shade: false, w: 0.6 });
      mass(ctx, "fe-tail", [[-12, -12.4], [-21, -12], [-26, -7], [-24, -5.4], [-20, -9], [-12, -9]], P);
      mass(ctx, "fe-body", ellPts(0, -11, 14, 5, 20), P, { main: true });
      back(ctx, "fe", [[-6, -15.6], [2, -16]], P);
      for (const x of [-11, 7]) mass(ctx, `fe-l${x}`, [[x - 1.7, -9], [x + 1.7, -9], [x + 2, 0], [x - 2, 0]], P, { shade: false, w: 0.6 });
      for (const x of [13, 17.4]) mass(ctx, `fe-ear${x}`, [[x - 2.2, -16.6], [x, -21.6], [x + 2.2, -16.6]], P, { w: 0.6, sharp: true });
      mass(ctx, "fe-head", ellPts(15, -14.5, 5.4, 4.6, 16), P, { main: true });
      ink(ctx, "fe-muzzle", ellPts(19.2, -13, 2.2, 1.6, 10), P.l, { shade: false, w: 0.5 });
      eye(ctx, 17.2, -15.4, P, 0.9); dot(ctx, 21, -13.4, 0.6, 0.5, INK);
    } },
    wraith: { zh: "霧魅", fur: "#e6ecef", top: -46, head: [0, -42], len: 12, hover: true, sp: [[-4, -40], [4, -40]], draw(ctx, P) {
      ctx.save(); ctx.translate(0, -4);
      limb(ctx, "wr-arm-l", [[-7, -30], [-12, -22], [-14, -16]], 2.2, P.base);
      mass(ctx, "wr-body", [[-8, -34], [-10, -20], [-7, -8], [-4, -2], [-1, -6], [2, -1], [5, -6], [9, -18], [8, -34]], P, { main: true });
      mass(ctx, "wr-head", ellPts(0, -38, 6, 6.4, 14), P);
      for (const x of [-2.2, 2.2]) dot(ctx, x, -38, 1.3, 0.9, P.eye);
      limb(ctx, "wr-arm-r", [[7, -30], [12, -23], [15, -18]], 2.2, P.base);
      ctx.restore();
    } },
    pylon: { zh: "晶塔", fur: "#8a847e", top: -40, head: [1, -24], len: 9, sp: [[0, -38]], draw(ctx, P) {
      ink(ctx, "py-base", [[-8, 0], [-9, -5], [9, -5], [8, 0]], "#6a645e", { w: 0.7 });
      mass(ctx, "py-ob", [[-5, -5], [-4, -30], [0, -38], [4, -30], [5, -5]], P, { main: true, sharp: true });
      ink(ctx, "py-eye", ellPts(1.6, -22, 1.8, 2.4, 10), P.accent ?? P.eye, { shade: false, w: 0.4 });
      dot(ctx, 2, -22, 0.5, 1.2, INK);
      ctx.save(); ctx.globalAlpha = 0.8; stroke(ctx, "py-ring", ellPts(0, -22, 8.6, 2.4, 20).concat([[8.6, -22]]), 0.7, P.accent ?? P.l); ctx.restore();
    } },
  };
  const MATERIALS = ["fur", "magma", "crystal", "stone", "wood", "mist"];
  const SIZES = { tiny: 0.62, small: 0.8, medium: 1, large: 1.25, huge: 1.6 };

  // ============================== 特徵 traits（外觀提示用的小部件；不認得的跳過） ==============================
  const TRAITS = {
    stone_back: { zh: "背上石板", draw(ctx, a, P) { a.sp.forEach(([x, y], i) => ink(ctx, `tr-sb${i}`, [[x - 3, y + 1.4], [x - 1.6, y - 4.4 - (i % 2) * 1.6], [x + 2.6, y - 3.4], [x + 3, y + 1.4]], "#8a8f94", { sharp: true, w: 0.7 })); } },
    volcano: { zh: "背上小火山", draw(ctx, a, P) {
      const [x, y] = a.sp[Math.floor(a.sp.length / 2)];
      ink(ctx, "tr-vc", [[x - 6, y + 2], [x - 2, y - 6], [x + 2, y - 6], [x + 6, y + 2]], "#4a3a34", { w: 0.7 });
      ink(ctx, "tr-vc-mouth", ellPts(x, y - 6, 2, 0.8, 10), P.accent ?? ELEM.fire[0], { shade: false, w: 0.4 });
      for (const [i, [dx, dy, r]] of [[-0.6, -9.6, 1.6], [1.6, -12.4, 1.9]].entries()) ink(ctx, `tr-vc-sm${i}`, ellPts(x + dx, y + dy, r, r, 10), "#9a9490", { shade: false, w: 0.4, alpha: 0.75 });
    } },
    smoke: { zh: "黃煙", draw(ctx, a) {
      for (const [i, [x, y, r]] of [[-a.len * 0.6, a.top * 0.7, 2.6], [a.len * 0.2, a.top * 1.05, 3], [a.len * 0.7, a.top * 0.5, 2.2]].entries()) ink(ctx, `tr-sk${i}`, ellPts(x, y, r, r * 0.8, 12), "#e8d860", { shade: false, w: 0.4, alpha: 0.55 });
    } },
    mist: { zh: "霧氣繞身", draw(ctx, a) {
      ctx.save(); ctx.globalAlpha = 0.55;
      for (const [i, [x, y, r]] of [[-a.len * 0.7, -2, 3.4], [-a.len * 0.1, -1, 4], [a.len * 0.6, -2.4, 3]].entries()) ink(ctx, `tr-ms${i}`, ellPts(x, y, r, r * 0.55, 12), "#eef2f4", { shade: false, line: false });
      stroke(ctx, "tr-ms-l", [[-a.len, -6], [-a.len * 0.4, -8], [0, -6]], 0.5, "#ffffff");
      ctx.restore();
    } },
    core: { zh: "胸口熔核", draw(ctx, a, P) {
      const [x, y] = a.core ?? a.head, c = P.accent ?? ELEM.fire[0];
      ink(ctx, "tr-core", ellPts(x, y, 3.2, 3.2, 12), c, { shade: false, w: 0.6 }); dot(ctx, x - 0.6, y - 0.8, 1.2, 1.2, light(c, 0.6));
    } },
    crust: { zh: "甲蟲殼堆（熔殼）", draw(ctx, a) {
      // 灰燼之心第 1 階段：熔岩甲蟲背殼一片片疊成外殼，殼縫透出火光；殼裂開（移除熔殼）後就不畫
      const [cx, cy] = a.core ?? a.head;
      const plates = [[-7, 3, -0.5], [6.6, 3.4, 0.5], [-8.6, -5, -1.1], [8, -5.6, 1.1], [-3.4, -10.6, -0.3], [3.8, -10.4, 0.35], [0, 6.6, 0]];
      for (const [i, [dx, dy, rot]] of plates.entries()) {
        const x = cx + dx, y = cy + dy, c = Math.cos(rot), sn = Math.sin(rot), q = (u, v) => [x + u * c - v * sn, y + u * sn + v * c];
        ink(ctx, `tr-cr${i}`, [q(-4.4, 2.6), q(-3.6, -2.4), q(0, -3.6), q(3.6, -2.4), q(4.4, 2.6), q(0, 3.4)], BASALT, { w: 0.7 });
        stroke(ctx, `tr-crl${i}`, [q(0, -3.2), q(0, 3)], 0.45, "#1c1412");
      }
      for (const [i, [x0, y0, x1, y1]] of [[-2, -1, 2, -2], [-4, 6, -1, 9], [3, 5, 5, 8]].entries()) stroke(ctx, `tr-crg${i}`, [[cx + x0, cy + y0], [cx + x1, cy + y1]], 0.9, ELEM.fire[1]);
    } },
    scar: { zh: "疤", draw(ctx, a) { const [x, y] = a.head; stroke(ctx, "tr-scar1", [[x - 3, y - 3], [x + 1, y + 2]], 0.8, "#5a2a22"); stroke(ctx, "tr-scar2", [[x - 1.6, y - 1.2], [x - 3, y]], 0.6, "#5a2a22"); } },
    brood: { zh: "背負卵囊", draw(ctx, a, P) { a.sp.forEach(([x, y], i) => ink(ctx, `tr-egg${i}`, ellPts(x, y - 2, 2.4, 3, 10), P.accent ?? "#ffb23a", { shade: false, w: 0.5 })); } },
    lava_pool: { zh: "背負熔岩池", draw(ctx, a, P) {
      const [x0, y0] = a.sp[0], [x1] = a.sp[a.sp.length - 1];
      ink(ctx, "tr-pool-rim", [[x0 - 5, y0 + 1], [x0 - 3, y0 - 3], [x1 + 3, y0 - 4], [x1 + 5, y0], [x1 + 3, y0 + 3], [x0 - 3, y0 + 3]], "#4a3a34", { w: 0.7 });
      ink(ctx, "tr-pool", ellPts((x0 + x1) / 2, y0 - 1.4, (x1 - x0) / 2 + 2, 1.4, 14), P.accent ?? ELEM.fire[0], { shade: false, w: 0.4 });
    } },
    spots: { zh: "斑紋", draw(ctx, a, P) { for (const [x, y] of [[-8, -12], [-3, -14], [2, -11.4], [-5, -9.4], [8, -12.4]]) dot(ctx, x, y, 1.1, 0.8, P.d); } },
    sparks: { zh: "電光", draw(ctx, a) { for (const [i, [x, y]] of [[-a.len * 0.5, a.top * 0.75], [a.len * 0.6, a.top * 0.85]].entries()) stroke(ctx, `tr-spk${i}`, [[x, y], [x + 2, y + 2], [x, y + 3], [x + 2.4, y + 5.4]], 0.9, "#fff36b"); } },
  };

  // ============================== 精英詞綴（疊在身上；人形敵人同一套） ==============================
  const AFFIX = {
    berserk: { zh: "狂暴的", draw(ctx, a) {
      const [hx, hy] = a.head;
      for (const [i, [dx, dy, r]] of [[-3, -6, 1.8], [1, -9, 2.2], [4.6, -6.4, 1.6]].entries()) ink(ctx, `af-bz${i}`, ellPts(hx + dx, hy + dy, r, r, 10), "#ff8a7a", { shade: false, w: 0.45, alpha: 0.8 });
      for (const s of [-1, 1]) stroke(ctx, `af-bzv${s}`, [[hx - 1 + s * 1.4, hy - 3.2], [hx + s * 0.6, hy - 2], [hx + 1 + s * 1.4, hy - 3.2]], 0.8, "#e02a2a");
    } },
    regen: { zh: "再生的", draw(ctx, a) {
      for (const [i, [x, y]] of [[-a.len * 0.7, a.top * 0.45], [a.len * 0.5, a.top * 0.75], [-a.len * 0.2, a.top * 0.95], [a.len * 0.85, a.top * 0.3]].entries()) {
        stroke(ctx, `af-rg${i}a`, [[x - 1.8, y], [x + 1.8, y]], 1.1, "#3f9a4a"); stroke(ctx, `af-rg${i}b`, [[x, y - 1.8], [x, y + 1.8]], 1.1, "#3f9a4a");
        stroke(ctx, `af-rg${i}c`, [[x - 1.4, y], [x + 1.4, y]], 0.55, "#b6f0a0"); stroke(ctx, `af-rg${i}d`, [[x, y - 1.4], [x, y + 1.4]], 0.55, "#b6f0a0");
      }
    } },
    armored: { zh: "堅甲的", draw(ctx, a) {
      const y = a.top * (a.hover ? 0.55 : 0.6);
      for (const [i, x] of [-a.len * 0.35, a.len * 0.1].entries()) ink(ctx, `af-ar${i}`, [[x - 4, y - 1.4], [x + 4, y - 2.4], [x + 4.6, y + 3], [x - 3.6, y + 3.6]], "#8d969f", { w: 0.7 });
      for (const [i, x] of [-a.len * 0.35, a.len * 0.1].entries()) dot(ctx, x, y + 0.6, 0.6, 0.6, "#3c4248");
    } },
    swift: { zh: "迅捷的", draw(ctx, a) {
      for (const [i, y] of [a.top * 0.3, a.top * 0.55, a.top * 0.8].entries()) stroke(ctx, `af-sw${i}`, [[-a.len - 3 - i * 2, y], [-a.len - 11 - i * 2, y]], 0.9, "#e8e8ea");
    } },
    elemental: { zh: "元素的", draw(ctx, a) {
      const c = ELEM[a.element] ?? ELEM.fire;
      for (const [i, x] of [-a.len * 0.6, a.len * 0.1, a.len * 0.75].entries()) {
        ink(ctx, `af-el${i}`, [[x - 2, 0.6], [x - 0.6, -4.4], [x, -2.4], [x + 1, -6.4], [x + 2.2, 0.6]], c[0], { sharp: true, shade: false, w: 0.45, alpha: 0.9 });
        dot(ctx, x + 0.2, -1, 0.8, 1, c[1]);
      }
    } },
    // 玩法 PM 清單（#111）的區域詞綴
    mist_hidden: { zh: "霧隱的", draw(ctx, a) { // 邊緣模糊：身邊幾團白霧（本體在 stamp 裡另外降到 75% 不透明）
      ctx.save(); ctx.globalAlpha = 0.6;
      for (const [i, [x, y, r]] of [[-a.len * 0.8, a.top * 0.4, 3.6], [a.len * 0.7, a.top * 0.65, 3.2], [-a.len * 0.2, a.top * 0.95, 3], [a.len * 0.2, -1.4, 4]].entries()) ink(ctx, `af-mh${i}`, ellPts(x, y, r, r * 0.7, 12), "#eef2f4", { shade: false, line: false });
      ctx.restore();
    } },
    linked: { zh: "連心的", draw(ctx, a) { // 與同伴連線：頭上一顆青色連心結；連到相鄰同門的虛線由戰場繪製器畫（樣張畫兩段示意）
      const [hx] = a.head, y = a.top - 4;
      for (const s of [-1, 1]) stroke(ctx, `af-lk${s}`, [[hx + s * 1.6, y + 2], [hx + s * 3.4, y - 0.4], [hx + s * 1.6, y - 2.4], [hx, y - 0.6]], 1, "#3fd0c0");
      ctx.save(); ctx.setLineDash([1.6, 1.4]); for (const s of [-1, 1]) stroke(ctx, `af-lkl${s}`, [[s * (a.len + 2), -3], [s * (a.len + 12), -4]], 0.8, "#3fd0c0"); ctx.restore();
    } },
    blazing: { zh: "熾熱的", draw(ctx, a) { // 周圍熱浪：頭上方三道波浪線
      for (const [i, x] of [-a.len * 0.5, 0, a.len * 0.5].entries()) stroke(ctx, `af-bl${i}`, [[x, a.top - 1], [x + 1.4, a.top - 3.4], [x - 0.4, a.top - 5.8], [x + 1, a.top - 8]], 0.8, "#ffb23a");
    } },
    hardshell: { zh: "硬殼的", draw(ctx, a) { // 外殼發亮：背上兩道白色反光
      a.sp.forEach(([x, y], i) => { if (i < 2) stroke(ctx, `af-hs${i}`, [[x - 2.4, y + 2], [x + 1.6, y + 0.6]], 1.1, "#ffffff"); });
      dot(ctx, a.sp[0][0] + 3, a.sp[0][1] - 1, 0.9, 0.9, "#ffffff");
    } },
    // mirror（分身的）在 stamp 裡畫：身後錯開一個 35% 半透明的分身
  };
  const AFFIX_ZH = Object.fromEntries(Object.entries(AFFIX).map(([k, v]) => [k, v.zh]).concat([["mirror", "分身的"]]));

  // ============================== 地面環（陣營環＋精英金環） ==============================
  function ring(ctx, rx, opt = {}) {
    ctx.save();
    ctx.globalAlpha = 0.3; ctx.fillStyle = "#d24a3a"; ctx.beginPath(); ctx.ellipse(0, 0, rx, rx * 0.3, 0, 0, TAU); ctx.fill();
    ctx.globalAlpha = 0.9; ctx.strokeStyle = "#d24a3a"; ctx.lineWidth = 1; ctx.stroke();
    if (opt.elite) {
      ctx.globalAlpha = 1; ctx.strokeStyle = "#2b1e16"; ctx.lineWidth = 2.2; ctx.beginPath(); ctx.ellipse(0, 0, rx + 2.2, (rx + 2.2) * 0.3, 0, 0, TAU); ctx.stroke();
      ctx.strokeStyle = "#ffbf3a"; ctx.lineWidth = 1.2; ctx.stroke();
      // 環前方一顆金色菱形（精英記號，在小尺寸也看得到）
      ink(ctx, "elite-gem", [[0, rx * 0.3 + 0.2], [2.4, rx * 0.3 + 2.6], [0, rx * 0.3 + 5], [-2.4, rx * 0.3 + 2.6]], "#ffbf3a", { sharp: true, shade: false, w: 0.6 });
    }
    ctx.restore();
  }

  // ============================== 組合 ==============================
  function resolve(spec) {
    const body = BODIES[spec.body] ? spec.body : "ooze";
    const b = BODIES[body];
    const size = (SIZES[spec.size] ?? 1) * (spec.elite ? 1.15 : 1);
    const affixes = (spec.affixes ?? []).filter((a) => AFFIX[a] || a === "mirror");
    const traits = (spec.traits ?? []).filter((t) => TRAITS[t]);
    return { ...spec, body, b, size, affixes, traits, P: palette(spec, b) };
  }
  function drawBody(ctx, r) {
    setShade(-1);
    shadow(ctx, r.b.len * 0.6);
    const info = { head: r.b.head, top: r.b.top, len: r.b.len, sp: r.b.sp, core: r.b.core };
    for (const t of r.traits) if (t === "mist") TRAITS[t].draw(ctx, info, r.P); // 霧在身體後面
    r.b.draw(ctx, r.P, r.variant);
    for (const t of r.traits) if (t !== "mist") TRAITS[t].draw(ctx, info, r.P);
  }
  // 人形敵人用：精英環＋詞綴特效（紙娃娃畫完後疊上去；人形的頭 (2,-44)、最高 -55、半身長 10）
  const HUMANOID_INFO = { head: [2, -44], top: -55, len: 10, sp: [[-4, -33], [3, -33]] };
  function ringAt(ctx, cx, cy, k, elite) { ctx.save(); ctx.translate(cx, cy); ctx.scale(k, k); ring(ctx, 13, { elite }); ctx.restore(); }
  function overlay(ctx, affixes, cx, cy, k, element) {
    ctx.save(); ctx.translate(cx, cy); ctx.scale(k, k);
    for (const a of affixes ?? []) if (AFFIX[a]) AFFIX[a].draw(ctx, { ...HUMANOID_INFO, element });
    ctx.restore();
  }
  // 畫在 (cx, cy)（腳底）、倍率 k、west 鏡像；glow：頭目外光色（沿用 RARITY_GLOW：史詩 #b06cff、傳說 #ffbf3a）
  function stamp(ctx, spec, cx, cy, k = 1, west = false) {
    const r = resolve(spec), s = k * r.size, info = { head: r.b.head, top: r.b.top, len: r.b.len, sp: r.b.sp, hover: r.b.hover, element: r.element };
    ctx.save(); ctx.translate(cx, cy);
    ctx.save(); ctx.scale(k * Math.max(1, r.size * 0.9), k * Math.max(1, r.size * 0.9)); ring(ctx, 13, { elite: spec.elite || !!spec.glow }); ctx.restore();
    ctx.scale(west ? -s : s, s);
    const paint = (c) => {
      if (r.affixes.includes("mirror")) { c.save(); c.globalAlpha = 0.35; c.translate(-9, -1); drawBody(c, r); c.restore(); }
      if (r.affixes.includes("mist_hidden")) { c.save(); c.globalAlpha = 0.75; drawBody(c, r); c.restore(); } else drawBody(c, r);
      for (const a of r.affixes) if (AFFIX[a]) AFFIX[a].draw(c, info);
    };
    if (spec.glow) {
      // 外光：先畫到離屏，再把剪影染色往 12 個方向錯開 2.6px
      const W = 140, Hh = 120, dpr = 2, off = document.createElement("canvas"); off.width = W * dpr; off.height = Hh * dpr;
      const o = off.getContext("2d"); o.scale(dpr, dpr); o.translate(W / 2, Hh - 12); paint(o);
      const g = document.createElement("canvas"); g.width = off.width; g.height = off.height;
      const gc = g.getContext("2d"); gc.drawImage(off, 0, 0); gc.globalCompositeOperation = "source-in"; gc.fillStyle = spec.glow; gc.fillRect(0, 0, g.width, g.height);
      ctx.save(); ctx.globalAlpha = 0.5;
      for (let a = 0; a < 12; a++) { const t = (a / 12) * TAU; ctx.drawImage(g, -W / 2 + Math.cos(t) * 2.6 / s, -(Hh - 12) + Math.sin(t) * 2.6 / s, W, Hh); }
      ctx.restore(); ctx.drawImage(off, -W / 2, -(Hh - 12), W, Hh);
    } else paint(ctx);
    ctx.restore();
  }
  return { stamp, resolve, ringAt, overlay, BODIES, MATERIALS, SIZES, AFFIX_ZH, TRAITS, ELEM };
})();
