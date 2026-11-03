// 戰鬥畫面對照樣張：現行格子版 vs D 版（規則照舊用格子，畫面藏格線）。美術 PM，2026-11-04。只是示意，不代決。
// 使用者原話（專案 PM 轉達）：「D 樣張」。依據：共用筆記 玩法PM-戰鬥拿掉格子評估.md 的方案 D。
// 場景：渡口石階（同 explore.png 的野外），碰到盜賊後就地開打；戰鬥區是畫面中的 12×12（第 6～17 欄）。
// 依賴：paperdoll.js、realms.js、storyDoll.js、enemyArt.js、explore.js、hud.js。全部程式繪製。
window.Battle = (() => {
  const E = Explore, H = Hud;
  const { T, box, rr, dot, rgba, OUT } = E;
  const TAU = Math.PI * 2;
  const COLS = 20, ROWS = 12, Z0 = 6, Z1 = 17; // 戰鬥區欄位（含）
  const GROUND = [
    "gggggggggggggggggggg",
    "ggggggggggggtttggggg",
    "ggggggggggtttggggggg",
    "pppppgggttttgggggggg",
    "pppppppptttggggggggg",
    "gggggppptggggggggggg",
    "gggggggggggggggggggg",
    "gggggggggggggggggggg",
    "gggggggggggggggggggg",
    "wwwwwwwwwwwwwwwwwwww",
    "WWWWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWWWW",
  ];
  const PROPS = [[3, 0, "bamboo"], [4, 0, "bamboo"], [0, 1, "bamboo"], [16, 2, "bamboo"], [17, 3, "bamboo"], [5, 6, "bamboo"], [18, 6, "bamboo"], [11, 3, "stoneLantern"], [7, 2, "stoneLantern"]];
  const [HERO, MAGE] = E.PARTY;
  const MERC = [{ skin: E.SKIN[2], hair: "short", hairColor: "#2a1a10" }, { body: { kind: "plate", material: "steel" }, main_hand: { kind: "sword", material: "steel" }, off_hand: { kind: "shield_kite", material: "steel", color: "#8a2f20" }, feet: { kind: "greaves", material: "steel" } }];
  const BANDIT = [{ skin: E.SKIN[2], hair: "short", hairColor: "#1a1a1a" }, { body: { kind: "leather", material: "leather", color: "#7a6a4a" }, head: { kind: "wide_hat", material: "wood", color: "#a08a5a" }, main_hand: { kind: "axe", material: "iron" } }];
  const ARCHER = [{ skin: E.SKIN[1], hair: "short", hairColor: "#2a1a10" }, { body: { kind: "leather", material: "leather", color: "#6a5a3a" }, main_hand: { kind: "bow", material: "wood" } }];
  const ALLY = "#5aa0ff", FOE = "#e0483a";
  // 單位：[標記, 欄, 列, 外觀, 陣營, HP 比例, 朝向]
  const UNITS = [
    ["A", 8, 6, HERO, ALLY, 0.82, "east"], ["B", 7, 7, MAGE, ALLY, 0.6, "east"], ["C", 9, 7, MERC, ALLY, 1, "east"],
    ["D", 13, 6, BANDIT, FOE, 0.7, "west"], ["E", 15, 5, ARCHER, FOE, 1, "west"], ["F", 13, 8, "wolf", FOE, 0.9, "west"],
  ];
  const inZone = (gx, gy) => gx >= Z0 && gx <= Z1 && gy >= 0 && gy < ROWS;
  const blocked = (gx, gy) => GROUND[gy][gx] === "W" || GROUND[gy][gx] === "w" || PROPS.some(([x, y]) => x === gx && y === gy) || UNITS.some(([, x, y]) => x === gx && y === gy);

  function world(ctx, opt = {}) {
    GROUND.forEach((row, gy) => [...row].forEach((ch, gx) => E.ground(ctx, ch, gx, gy)));
    E.dock(ctx, 12, 8, 3, 1); E.boat(ctx, 15, 9);
    E.campfire(ctx, 2, 6);
    if (opt.under) opt.under(ctx);
    for (let gy = 0; gy < ROWS; gy++) {
      for (const [x, y, k] of PROPS) if (y === gy) Realms.OBJ[k](ctx, x * T, y * T);
      for (const u of UNITS) if (u[2] === gy && !(opt.skip ?? []).includes(u[0])) unit(ctx, u, opt);
    }
  }
  function unit(ctx, [mark, gx, gy, look, side, hp, facing], opt) {
    const cx = gx * T + T / 2, foot = gy * T + T * 0.82;
    if (opt.style === "grid") E.ring(ctx, cx, foot, side);
    else { // D 版：腳下只有柔和的陣營光暈，不是方格的環
      const g = ctx.createRadialGradient(cx, foot, 2, cx, foot, T * 0.4);
      g.addColorStop(0, rgba(side, 0.45)); g.addColorStop(1, rgba(side, 0));
      ctx.fillStyle = g; ctx.beginPath(); ctx.ellipse(cx, foot, T * 0.4, T * 0.15, 0, 0, TAU); ctx.fill();
    }
    if (look === "wolf") EnemyArt.stamp(ctx, { body: "hound", material: "fur", tint: "#c8ccd0", traits: ["mist"] }, cx, foot, 0.78, true);
    else PaperDoll.stamp(ctx, { look: look[0], gear: look[1] }, facing, cx, foot, 0.78, { dpr: 3 });
    // 頭上：HP 條（兩版都有）；現行版另有字母標記
    const top = foot - 56;
    box(ctx, cx - 16, top, 32, 5, "#1a1410", OUT, 1, 2); box(ctx, cx - 15.5, top + 0.5, 31 * hp, 4, side === ALLY ? "#5ad06a" : FOE, null, 0, 2);
    if (opt.style === "grid") { box(ctx, cx - 26, top - 4, 12, 12, "#f2e6c8", OUT, 1.2, 6); ctx.fillStyle = OUT; ctx.font = "bold 9px Consolas"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(mark, cx - 20, top + 2.5); ctx.textAlign = "left"; }
  }
  // 戰鬥區外圍：D 版用柔和的暗角，表示「這裡開打了」，不畫框線
  function zoneVignette(ctx, a = 0.38) {
    ctx.save(); ctx.fillStyle = `rgba(16,12,10,${a})`;
    ctx.fillRect(0, 0, Z0 * T, ROWS * T); ctx.fillRect((Z1 + 1) * T, 0, (COLS - Z1 - 1) * T, ROWS * T);
    for (const [x, dir] of [[Z0 * T, 1], [(Z1 + 1) * T, -1]]) { const g = ctx.createLinearGradient(x, 0, x + dir * 26, 0); g.addColorStop(0, `rgba(16,12,10,${a * 0.7})`); g.addColorStop(1, "rgba(16,12,10,0)"); ctx.fillStyle = g; ctx.fillRect(Math.min(x, x + dir * 26), 0, 26, ROWS * T); }
    ctx.restore();
  }
  /** 淡淡浮出的格子：只畫在 cells 上，邊緣柔化。 */
  function softCells(ctx, cells, fill, line, edge) {
    ctx.save();
    for (const [gx, gy] of cells) { rr(ctx, gx * T + 3, gy * T + 3, T - 6, T - 6, 8); ctx.fillStyle = fill; ctx.fill(); ctx.lineWidth = 1.2; ctx.strokeStyle = line; ctx.stroke(); }
    if (edge) { // 外緣加一條較亮的輪廓
      const set = new Set(cells.map(([x, y]) => `${x},${y}`));
      ctx.strokeStyle = edge; ctx.lineWidth = 2.5; ctx.lineCap = "round"; ctx.beginPath();
      for (const [x, y] of cells) {
        if (!set.has(`${x},${y - 1}`)) { ctx.moveTo(x * T + 2, y * T + 2); ctx.lineTo(x * T + T - 2, y * T + 2); }
        if (!set.has(`${x},${y + 1}`)) { ctx.moveTo(x * T + 2, y * T + T - 2); ctx.lineTo(x * T + T - 2, y * T + T - 2); }
        if (!set.has(`${x - 1},${y}`)) { ctx.moveTo(x * T + 2, y * T + 2); ctx.lineTo(x * T + 2, y * T + T - 2); }
        if (!set.has(`${x + 1},${y}`)) { ctx.moveTo(x * T + T - 2, y * T + 2); ctx.lineTo(x * T + T - 2, y * T + T - 2); }
      }
      ctx.stroke();
    }
    ctx.restore();
  }
  function reach(sx, sy, n) {
    const out = [], seen = new Set([`${sx},${sy}`]); let front = [[sx, sy]];
    for (let s = 0; s < n; s++) {
      const next = [];
      for (const [x, y] of front) for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const nx = x + dx, ny = y + dy, k = `${nx},${ny}`;
        if (seen.has(k) || !inZone(nx, ny) || blocked(nx, ny)) continue;
        seen.add(k); next.push([nx, ny]); out.push([nx, ny]);
      }
      front = next;
    }
    return out;
  }

  // ---------------- 戰鬥 HUD（版面 A 的戰鬥版）----------------
  const SKILLS = [["slash", "#c86a3a", 2, 0], ["sword", "#8a8a9a", 1, 0], ["boots", "#5a8a5a", 1, 0], ["portal", "#5a6ad0", 2, 2], ["rest", "#c8502a", 3, 0], ["shadow", "#6a5a9a", 1, 0]];
  function slashIcon(c, x, y, s) { c.strokeStyle = OUT; c.lineWidth = s * 0.28; c.lineCap = "round"; c.beginPath(); c.moveTo(x - s * 0.4, y + s * 0.4); c.lineTo(x + s * 0.4, y - s * 0.4); c.stroke(); c.strokeStyle = "#f2f4f8"; c.lineWidth = s * 0.14; c.stroke(); }
  function skillIcon(c, x, y, size, [ic, col, ap, cd], opt = {}) {
    box(c, x, y, size, size, col, opt.sel ? "#ffd23a" : OUT, opt.sel ? 3 : 2, 8);
    c.fillStyle = "rgba(255,255,255,0.18)"; c.fillRect(x + 4, y + 4, size - 8, 3);
    if (ic === "slash") slashIcon(c, x + size / 2, y + size / 2, size * 0.55); else H.I[ic](c, x + size / 2, y + size / 2, size * 0.5);
    for (let k = 0; k < ap; k++) dot(c, x + 7 + k * 8, y + size - 7, 3, "#ffd23a");
    if (cd > 0) { c.fillStyle = "rgba(10,10,14,0.62)"; c.beginPath(); c.moveTo(x + size / 2, y + size / 2); c.arc(x + size / 2, y + size / 2, size * 0.7, -Math.PI / 2, -Math.PI / 2 + TAU * 0.6); c.closePath(); c.save(); rr(c, x + 2, y + 2, size - 4, size - 4, 6); c.clip(); c.fill(); c.restore(); H.text(c, String(cd), x + size / 2, y + size / 2, 18, "#ffffff", "center"); }
  }
  function battleHud(c, opt = {}) {
    const W = COLS * T, Hh = ROWS * T;
    // 左上：主角卡（同探索版 A，多了 AP 圓點、反應、源力）
    box(c, 8, 8, 250, 92, H.PANEL, H.GOLD, 1.5, 10);
    H.portrait(c, 46, 45, 62, 0); H.badge(c, 70, 72, "Lv 4", "#3a5ad0");
    H.bar(c, 84, 14, 164, 14, 0.82, H.HP, "HP 41 / 50"); H.bar(c, 84, 31, 164, 14, 0.6, H.MP, "法力 18 / 30"); H.bar(c, 84, 48, 164, 14, 0.75, "#c8a030", "耐力 6 / 8");
    for (let k = 0; k < 3; k++) { dot(c, 92 + k * 15, 80, 5.5, k < (opt.ap ?? 3) ? "#ffd23a" : "#3a3028"); c.lineWidth = 1.5; c.strokeStyle = OUT; c.beginPath(); c.arc(92 + k * 15, 80, 5.5, 0, TAU); c.stroke(); }
    H.I.boots(c, 152, 80, 14); H.text(c, "3", 162, 81, 12);
    c.strokeStyle = "#5ad06a"; c.lineWidth = 2.5; c.beginPath(); c.arc(190, 80, 6, 0.4, TAU - 0.4); c.stroke();
    for (let k = 0; k < 3; k++) dot(c, 212 + k * 11, 80, 4, k < 1 ? "#c8bcff" : "#3a3028");
    [[1, 0.6], [0, 1]].forEach(([idx, hp], i) => { const y = 108 + i * 40; box(c, 8, y, 130, 34, H.PANEL, "rgba(200,168,104,0.6)", 1.2, 17); H.portrait(c, 25, y + 17, 28, idx, "#8fb0d0"); H.bar(c, 44, y + 12, 86, 9, hp, "#5ad06a"); });
    // 上方中央：行動順序
    const order = [["A", ALLY], ["D", FOE], ["B", ALLY], ["F", FOE], ["C", ALLY], ["E", FOE]];
    const ox = W / 2 - order.length * 21;
    box(c, ox - 8, 6, order.length * 42 + 6, 40, "rgba(24,20,16,0.7)", null, 0, 10);
    order.forEach(([m, side], i) => {
      const x = ox + i * 42 + 16, y = 26, cur = i === 0;
      dot(c, x, y, cur ? 16 : 13, "#2a3634"); c.lineWidth = cur ? 3 : 2; c.strokeStyle = cur ? "#ffd23a" : side; c.beginPath(); c.arc(x, y, cur ? 16 : 13, 0, TAU); c.stroke();
      H.text(c, m, x, y + 1, cur ? 14 : 12, "#f2e6c8", "center");
    });
    // 右上：回合、天氣、勝利條件（純圖示＋數字）
    box(c, W - 150, 8, 142, 30, H.PANEL, H.GOLD, 1.5, 8);
    H.text(c, "第 2 輪", W - 140, 23.5, 12); H.I.rain(c, W - 70, 23, 16); H.I.sword(c, W - 38, 23, 15);
    // 底部中央：技能列（圖示＋AP 點＋冷卻遮罩）＋結束回合
    const n = SKILLS.length, sz = 52, gap = 6, bx = W / 2 - (n * (sz + gap)) / 2 - 30;
    box(c, bx - 10, Hh - 72, n * (sz + gap) + 84, 66, "rgba(24,20,16,0.72)", null, 0, 12);
    SKILLS.forEach((s, i) => skillIcon(c, bx + i * (sz + gap), Hh - 65, sz, s, { sel: opt.skill === i }));
    const ex = bx + n * (sz + gap) + 6;
    box(c, ex, Hh - 65, 58, 52, "#3a2a1e", H.GOLD, 2, 10); H.text(c, "結束", ex + 29, Hh - 39, 13, "#f2e6c8", "center");
    // 左下：戰鬥紀錄收成浮動提示
    H.toast(c, 10, Hh - 96, 240, "warn", "盜賊發現了你們！", "#ff6a5a", 0.6);
    H.toast(c, 10, Hh - 66, 240, "sword", "斷崖幫刀手 −8", H.GOLD, 1);
    if (opt.unitCard) unitCard(c, W - 236, 48);
    if (opt.skillCard) skillCard(c, bx - 10, Hh - 72 - 118);
  }
  /** 去文字化後的單位資訊小卡（同 textless.png 第 2 組）。 */
  function unitCard(c, x, y) {
    box(c, x, y, 226, 120, "rgba(24,20,16,0.9)", "#e0483a", 1.8, 10);
    H.text(c, "D 斷崖幫刀手", x + 10, y + 15, 13);
    box(c, x + 160, y + 6, 58, 18, "#2a2014", "#e8bb48", 1.5, 9); H.text(c, "◆ 狂暴", x + 189, y + 15.5, 11, "#ffd23a", "center");
    H.bar(c, x + 10, y + 28, 206, 13, 0.7, H.HP, "HP 30 / 42"); H.bar(c, x + 10, y + 44, 206, 13, 0.75, "#c8a030", "耐力 6 / 8");
    H.chip(c, x + 10, y + 64, "rank", "5", 48); H.chip(c, x + 62, y + 64, "boots", "3", 48); H.chip(c, x + 114, y + 64, "sword", "雙手", 64);
    box(c, x + 10, y + 92, 22, 22, "#5a2a14", OUT, 1.2, 5); H.I.rest(c, x + 21, y + 103, 14); H.badge(c, x + 32, y + 112, "2", "#1c1712");
    H.text(c, "▸ 詳細", x + 150, y + 104, 11, H.DIM);
  }
  /** 去文字化後的技能卡（同 textless.png 第 1 組）。 */
  function skillCard(c, x, y) {
    box(c, x, y, 280, 108, "rgba(24,20,16,0.93)", "#6a5a8a", 2, 10);
    box(c, x + 10, y + 10, 50, 50, "#5a6ad0", OUT, 2, 8); H.I.portal(c, x + 35, y + 35, 28);
    H.text(c, "雷霆十字", x + 70, y + 20, 15);
    let cx = x + 70;
    const chips = [["ap", "●●"], ["cd", "2"], ["rng", "4"]];
    for (const [k, v] of chips) { box(c, cx, y + 34, 50, 22, "#1a1410", "#5a4a38", 1.2, 11); if (k === "ap") { dot(c, cx + 12, y + 45, 4, "#ffd23a"); dot(c, cx + 22, y + 45, 4, "#ffd23a"); } else { H.I[k === "cd" ? "clock" : "map"](c, cx + 12, y + 45, 13); H.text(c, v, cx + 24, y + 45.5, 12); } cx += 56; }
    H.I.portal(c, x + 22, y + 78, 15); H.text(c, "12", x + 34, y + 78.5, 14); H.text(c, "雷", x + 54, y + 78.5, 11, H.DIM, "left", false);
    H.I.warn(c, x + 92, y + 78, 13); H.text(c, "帶電 1", x + 104, y + 78.5, 12);
    H.text(c, "▸ 詳細", x + 10, y + 97, 11, H.DIM); H.text(c, "Shift 固定", x + 210, y + 97, 11, H.DIM);
  }

  // ======================= 1. 現行格子版 =======================
  function current(ctx) {
    const W = COLS * T, Hh = ROWS * T;
    ctx.save(); ctx.beginPath(); ctx.rect(0, 0, 12 * T, Hh); ctx.clip(); ctx.translate(-Z0 * T, 0);
    world(ctx, { style: "grid" });
    ctx.strokeStyle = "rgba(20,16,12,0.55)"; ctx.lineWidth = 1;
    for (let k = Z0; k <= Z1 + 1; k++) { ctx.beginPath(); ctx.moveTo(k * T + 0.5, 0); ctx.lineTo(k * T + 0.5, Hh); ctx.stroke(); }
    for (let k = 0; k <= ROWS; k++) { ctx.beginPath(); ctx.moveTo(Z0 * T, k * T + 0.5); ctx.lineTo((Z1 + 1) * T, k * T + 0.5); ctx.stroke(); }
    ctx.restore();
    // 右側：現在的文字側欄
    const x = 12 * T;
    ctx.fillStyle = "#211c18"; ctx.fillRect(x, 0, W - x, Hh);
    ctx.fillStyle = "#3a3129"; ctx.fillRect(x, 0, 2, Hh);
    const lines = [
      ["b", "第 2 輪・雨・勝利條件：擊倒全部敵人"], ["", ""],
      ["b", "A 主角　Lv 4"], ["", "HP 41 / 50（盾 0）"], ["", "法力 18 / 30　耐力 6 / 8"], ["", "AP 3　移動 3　反應可用　源力 1 / 3"], ["", "狀態 無　腳下 草地　層數 蓄勢 2"], ["", "冷卻：雷霆十字 2 回合"], ["", ""],
      ["b", "技能"], ["", "[蓄力斬 2AP] [斬擊 1AP] [疾步 1AP]"], ["", "[雷霆十字 2AP 冷卻2] [火牆 3AP] [影遁 1AP]"], ["", "[移動] [攻擊] [防禦] [結束回合]"], ["", ""],
      ["b", "D 斷崖幫刀手　精英・狂暴的"], ["", "HP 30 / 42（護盾 5）　法力 4 / 10"], ["", "AP／移動 2 / 3　朝向 西"], ["", "武器：鬼頭刀（斬擊、雙手）"], ["", "狀態：燃燒（2 回合）"], ["", ""],
      ["b", "戰鬥紀錄"], ["", "第 1 輪　盜賊發現了你們。"], ["", "A 主角使用蓄力斬，對 D 造成 8 點物理傷害。"], ["", "D 斷崖幫刀手陷入燃燒（2 回合）。"], ["", "E 弓手射擊 C 傭兵・岳，未命中。"], ["", "F 霧狼移動到碼頭。"],
    ];
    lines.forEach(([b, s], i) => { ctx.font = `${b ? "bold " : ""}12.5px 'Microsoft JhengHei', sans-serif`; ctx.fillStyle = b ? "#f2e6c8" : "#c8bca8"; ctx.textBaseline = "middle"; ctx.fillText(s, x + 16, 20 + i * 22.5); });
  }
  // ======================= 2. D 版待機 =======================
  function dIdle(ctx) { world(ctx); zoneVignette(ctx); battleHud(ctx, { unitCard: true }); }
  // ======================= 3. D 版選移動 =======================
  function dMove(ctx) {
    const cells = reach(8, 6, 3);
    world(ctx, { under: (c) => softCells(c, cells, "rgba(110,170,255,0.2)", "rgba(200,225,255,0.35)", "rgba(150,200,255,0.9)"), skip: ["A"] });
    zoneVignette(ctx);
    // 路徑：平滑曲線＋殘影（表示沿路徑走過去，不是一格一格跳）
    const path = [[8, 6], [9, 6], [10, 6], [10, 5]].map(([x, y]) => [x * T + T / 2, y * T + T * 0.7]);
    ctx.save(); ctx.strokeStyle = "rgba(255,255,255,0.85)"; ctx.lineWidth = 3; ctx.setLineDash([2, 7]); ctx.lineCap = "round";
    ctx.beginPath(); ctx.moveTo(...path[0]); ctx.quadraticCurveTo(path[2][0], path[2][1], path[3][0], path[3][1]); ctx.stroke(); ctx.restore();
    for (const [k, a] of [[0.35, 0.25], [0.7, 0.45]]) { ctx.save(); ctx.globalAlpha = a; PaperDoll.stamp(ctx, { look: HERO[0], gear: HERO[1] }, "east", 8 * T + T / 2 + (2 * T) * k, 6 * T + T * 0.82 - T * k * k, 0.78, { dpr: 3 }); ctx.restore(); }
    unit(ctx, ["A", 10, 5, HERO, ALLY, 0.82, "east"], {});
    ctx.save(); ctx.strokeStyle = "#ffd23a"; ctx.lineWidth = 2.5; rr(ctx, 10 * T + 4, 5 * T + 4, T - 8, T - 8, 9); ctx.stroke(); ctx.restore();
    H.chip(ctx, 10 * T - 6, 5 * T - 70, "boots", "−3", 58);
    battleHud(ctx, { ap: 3 });
  }
  // ======================= 4. D 版選範圍技能 =======================
  function dArea(ctx) {
    const cast = [];
    for (let y = 0; y < ROWS; y++) for (let x = Z0; x <= Z1; x++) { const d = Math.abs(x - 8) + Math.abs(y - 6); if (d <= 6 && d > 0 && GROUND[y][x] !== "W") cast.push([x, y]); }
    const cross = [[14, 6], [13, 6], [15, 6], [14, 5], [14, 7]];
    world(ctx, {
      under: (c) => {
        // 戰鬥區的格線極淡地浮出（只有選技能時），施放距離內更清楚一點
        c.save(); c.strokeStyle = "rgba(255,255,255,0.10)"; c.lineWidth = 1;
        for (let x = Z0; x <= Z1 + 1; x++) { c.beginPath(); c.moveTo(x * T, 0); c.lineTo(x * T, ROWS * T); c.stroke(); }
        for (let y = 0; y <= ROWS; y++) { c.beginPath(); c.moveTo(Z0 * T, y * T); c.lineTo((Z1 + 1) * T, y * T); c.stroke(); }
        c.restore();
        softCells(c, cast, "rgba(255,230,160,0.06)", "rgba(255,230,160,0.12)", null);
        softCells(c, cross, "rgba(255,120,60,0.32)", "rgba(255,200,150,0.6)", "rgba(255,140,70,0.95)");
      },
    });
    zoneVignette(ctx);
    // 命中的目標加紅框與預估傷害
    for (const [x, y, dmg] of [[13, 6, 12], [14, 5, null], [13, 8, null]]) if (dmg !== null) { H.chip(ctx, x * T + 2, y * T - 72, "portal", `−${dmg}`, 54); }
    battleHud(ctx, { skill: 3, skillCard: true, ap: 3 });
  }

  // ======================= 5. 2.5D 斜視角（D 版待機）=======================
  function iso(ctx) {
    const W = COLS * T, Hh = ROWS * T;
    ctx.fillStyle = "#1e2a2a"; ctx.fillRect(0, 0, W, Hh);
    const zw = 12, s = 0.84, q = 0.56, ang = Math.PI / 4, ox = W / 2, oy = 36;
    const P = (x, y) => { const lx = (x - Z0 * T), ly = y; return [ox + s * (lx * Math.cos(ang) - ly * Math.sin(ang)), oy + s * q * (lx * Math.sin(ang) + ly * Math.cos(ang))]; };
    // 地面：先畫到離屏，再用斜視角矩陣貼上
    const off = document.createElement("canvas"); off.width = zw * T * 2; off.height = ROWS * T * 2;
    const oc = off.getContext("2d"); oc.scale(2, 2); oc.translate(-Z0 * T, 0);
    GROUND.forEach((row, gy) => [...row].forEach((ch, gx) => { if (inZone(gx, gy)) E.ground(oc, ch, gx, gy); }));
    E.dock(oc, 12, 8, 3, 1); E.boat(oc, 15, 9);
    // 台地的厚度（立體感）：南、東兩邊往下畫土層
    const c0 = P(Z0 * T, ROWS * T), c1 = P((Z1 + 1) * T, ROWS * T), c2 = P((Z1 + 1) * T, 0);
    ctx.fillStyle = "#3a2e22"; ctx.beginPath(); ctx.moveTo(...c0); ctx.lineTo(...c1); ctx.lineTo(c1[0], c1[1] + 34); ctx.lineTo(c0[0], c0[1] + 34); ctx.fill();
    ctx.fillStyle = "#2a2018"; ctx.beginPath(); ctx.moveTo(...c1); ctx.lineTo(...c2); ctx.lineTo(c2[0], c2[1] + 34); ctx.lineTo(c1[0], c1[1] + 34); ctx.fill();
    ctx.save(); ctx.setTransform(...(() => { const m = ctx.getTransform(); return [m.a, m.b, m.c, m.d, m.e, m.f]; })());
    ctx.transform(s * Math.cos(ang), s * q * Math.sin(ang), -s * Math.sin(ang), s * q * Math.cos(ang), ox, oy);
    ctx.drawImage(off, 0, 0, zw * T, ROWS * T);
    ctx.restore();
    // 立著的東西：依深度排序後，直立貼上
    const sprites = [];
    for (const [x, y, k] of PROPS) if (inZone(x, y)) sprites.push([x + y, (c) => { const [px, py] = P((x - 0) * T + T / 2, y * T + T * 0.85); c.save(); c.translate(px - T / 2, py - T * 0.85); Realms.OBJ[k](c, 0, 0); c.restore(); }]);
    for (const u of UNITS) sprites.push([u[1] + u[2] + 0.1, (c) => { const [px, py] = P(u[1] * T + T / 2, u[2] * T + T / 2); c.save(); c.translate(px - u[1] * T - T / 2, py - u[2] * T - T * 0.82); unit(c, u, {}); c.restore(); }]);
    sprites.sort((a, b) => a[0] - b[0]).forEach(([, f]) => f(ctx));
    battleHud(ctx, { unitCard: true });
  }

  return { current, dIdle, dMove, dArea, iso };
})();
