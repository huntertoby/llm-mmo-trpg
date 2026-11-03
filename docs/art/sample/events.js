// 事件插圖（美術 PM，2026-11-04）：6C 事件卡上方的小插圖。和實地地圖同一套畫法（格子地面＋C 畫風紙娃娃＋地物），
// 每張是 7×3 格的小場景，四周暗角；背景依區域換（雲嶺／荒原），事件內容不變。全部程式繪製，沒有亂數（場景固定）。
// 依賴：storyDoll.js、paperdoll.js、realms.js、enemyArt.js、explore.js、regions4.js、cloudTiles.js、ashenTiles.js。
window.EventArt = (() => {
  const E = Explore, CT = CloudTiles, AT = AshenTiles, SD = StoryDoll, T = 52, TAU = Math.PI * 2, OUT = "#1c1712";
  const COLS = 7, ROWS = 3, W = COLS * T, H = ROWS * T;
  function glow(ctx, x, y, r, c, a) { const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, c); g.addColorStop(1, c.replace(/[\d.]+\)$/, "0)")); ctx.save(); ctx.globalAlpha = a; ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill(); ctx.restore(); }
  function ground(ctx, region) {
    for (let gy = 0; gy < ROWS; gy++) for (let gx = 0; gx < COLS; gx++) {
      if (region === "ashen") AT.tile(ctx, gy === 0 && gx > 4 ? "lava" : "stone", gx * T, gy * T, gx, gy);
      else E.ground(ctx, gy === 1 && gx > 1 && gx < 5 ? "p" : "g", gx, gy);
    }
  }
  const person = (ctx, x, y, look, gear, view = "front", west = false, k = 1.1) => SD.stamp(ctx, { look, gear }, view, x, y, k, west);
  const HERO = [{ skin: "#f1c9a5", hair: "short", hairColor: "#3a2414" }, { body: { kind: "leather", color: "#2f5a5a" }, feet: { kind: "boots", material: "leather" }, main_hand: { kind: "sword", material: "steel" } }];
  const BANDIT = [{ skin: "#a8724c", hair: "short", hairColor: "#1a1a1a" }, { body: { kind: "leather", color: "#7a6a4a" }, feet: { kind: "boots", material: "leather" }, main_hand: { kind: "axe", material: "iron" }, head: { kind: "hood", color: "#6a5a3a" } }];
  const VILLAGER = [{ skin: "#e8b890", hair: "bun", hairColor: "#3a2414", bunBand: "#b8432f" }, { body: { kind: "robe", color: "#8a6a3a" }, feet: { kind: "shoes", color: "#3a2a1a" } }];
  const MERCHANT = [{ skin: "#f1c9a5", hair: "short", hairColor: "#2a1a10" }, { body: { kind: "robe", color: "#3a5ad0", trim: "#e8bb48" } }];
  const SCENES = {
    ambush: { zh: "遭遇・伏擊", icon: "sword", draw(ctx, region) {
      if (region !== "ashen") { CT.bambooGrove(ctx, 0, 0, 2, 1); CT.bambooGrove(ctx, 5 * T, 0, 2, 1); } else { AT.deadGrove(ctx, 0, 0, 2, 1); }
      person(ctx, 1.6 * T, 2.85 * T, ...HERO, "side", false);
      person(ctx, 4.6 * T, 2.6 * T, ...BANDIT, "side", true); person(ctx, 5.6 * T, 2.2 * T, ...BANDIT, "side", true);
      EnemyArt.stamp(ctx, { body: "hound", material: region === "ashen" ? "magma" : "fur", tint: "#c8ccd0" }, 3.8 * T, 2.9 * T, 1, true);
      E.bubble(ctx, 4.6 * T, 1.15 * T, "bang", "danger");
    } },
    chest: { zh: "寶箱", icon: "coin", draw(ctx, region) {
      E.chest(ctx, 3, 1); glow(ctx, 3.5 * T, 1.55 * T, 60, "rgba(255,230,140,0.9)", 0.45);
      if (region !== "ashen") { CT.pine(ctx, 0.4 * T, 0); CT.flowers(ctx, 4.5 * T, 1.5 * T, 4, 1); } else AT.obj(ctx, "dead_tree", 0.4 * T, 0);
      CT.boulder(ctx, 5.2 * T, 1.2 * T);
    } },
    stele: { zh: "古碑", icon: "ask", draw(ctx, region) {
      E.stele(ctx, 3, 0.8); ctx.save(); ctx.shadowColor = "#8fe0ff"; ctx.shadowBlur = 8; ctx.strokeStyle = "#8fe0ff"; ctx.lineWidth = 1.4; for (const y of [1.15, 1.3, 1.45]) { ctx.beginPath(); ctx.moveTo(3.4 * T, y * T); ctx.lineTo(3.6 * T, y * T); ctx.stroke(); } ctx.restore();
      CT.mistWisp(ctx, 1.5 * T, 1.2 * T, 300); CT.mistWisp(ctx, 4.2 * T, 1.4 * T, 900); person(ctx, 1.8 * T, 2.9 * T, ...HERO, "side", false);
    } },
    altar: { zh: "祭壇・機遇", icon: "rest", draw(ctx, region) {
      for (let gx = 2; gx < 5; gx++) E.ground(ctx, "s", gx, 1);
      if (region === "ashen") AT.hornAltar(ctx, 3 * T, 0.6 * T); else CT.altar(ctx, 3 * T, 0.6 * T);
      glow(ctx, 3.5 * T, 1.2 * T, 70, region === "ashen" ? "rgba(255,90,60,0.9)" : "rgba(255,220,140,0.9)", 0.35);
      Realms.OBJ.stoneLantern(ctx, 1.6 * T, 0.6 * T); Realms.OBJ.stoneLantern(ctx, 4.4 * T, 0.6 * T);
    } },
    villager: { zh: "村民求助", icon: "bang", draw(ctx, region) {
      AT.cart(ctx, 3.6 * T, 1.3 * T); ctx.save(); ctx.translate(4.2 * T, 2.1 * T); ctx.rotate(0.5); ctx.restore();
      E.ground(ctx, "p", 3, 2); AT.obj(ctx, "crate", 4.6 * T, 1.9 * T);
      person(ctx, 2.4 * T, 2.8 * T, ...VILLAGER, "front");
      E.bubble(ctx, 2.4 * T, 1.55 * T, "bang", "quest");
    } },
    caravan: { zh: "商隊", icon: "coin", draw(ctx, region) {
      AT.cart(ctx, 2.2 * T, 1.2 * T); AT.cart(ctx, 3.4 * T, 1.3 * T); AT.obj(ctx, "crate", 4.6 * T, 1.7 * T);
      person(ctx, 5.4 * T, 2.85 * T, ...MERCHANT, "side", true); E.bubble(ctx, 5.4 * T, 1.6 * T, "coin", "talk");
      E.campfire(ctx, 0.8, 1.5);
    } },
    trap: { zh: "陷阱", icon: "warn", draw(ctx, region) {
      // 草叢裡露出一點的捕獸夾＋一道反光
      const cx = 3.5 * T, cy = 1.9 * T; ctx.save(); ctx.strokeStyle = "#1c1712"; ctx.lineWidth = 4; ctx.beginPath(); ctx.ellipse(cx, cy, 20, 11, 0, 0, TAU); ctx.stroke(); ctx.strokeStyle = "#9aa0a8"; ctx.lineWidth = 2.4; ctx.stroke(); ctx.fillStyle = "#c8ccd0"; for (let k = 0; k < 10; k++) { const a = k / 10 * TAU; ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * 20 - 2, cy + Math.sin(a) * 11); ctx.lineTo(cx + Math.cos(a) * 13, cy + Math.sin(a) * 6); ctx.lineTo(cx + Math.cos(a) * 20 + 2, cy + Math.sin(a) * 11); ctx.fill(); } ctx.restore();
      if (region !== "ashen") { AT.obj(ctx, "grass", 2.9 * T, 1.3 * T); } else { AT.obj(ctx, "grass", 2.9 * T, 1.3 * T); }
      ctx.save(); ctx.strokeStyle = "rgba(255,255,255,0.95)"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(cx + 14, cy - 12); ctx.lineTo(cx + 22, cy - 20); ctx.moveTo(cx + 18, cy - 10); ctx.lineTo(cx + 26, cy - 12); ctx.stroke(); ctx.restore();
      person(ctx, 1.4 * T, 2.85 * T, ...HERO, "side", false);
    } },
    camp: { zh: "營火休息", icon: "rest", draw(ctx, region) {
      E.campfire(ctx, 3, 1); glow(ctx, 3.5 * T, 1.6 * T, 90, "rgba(255,170,80,0.9)", 0.35);
      person(ctx, 2.3 * T, 2.6 * T, ...HERO, "side", false, 1); person(ctx, 4.7 * T, 2.6 * T, ...VILLAGER, "side", true, 1);
      ctx.fillStyle = "rgba(20,24,40,0.35)"; ctx.fillRect(0, 0, W, H);
    } },
    anomaly: { zh: "異象・源晶裂痕", icon: "portal", draw(ctx, region) {
      const cx = 3.5 * T, cy = 1.6 * T; glow(ctx, cx, cy, 90, "rgba(160,120,255,0.9)", 0.6);
      ctx.save(); ctx.shadowColor = "#c8a0ff"; ctx.shadowBlur = 14; ctx.strokeStyle = "#e8d8ff"; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(cx - 60, cy + 10); ctx.lineTo(cx - 20, cy - 4); ctx.lineTo(cx, cy + 12); ctx.lineTo(cx + 26, cy - 8); ctx.lineTo(cx + 64, cy + 6); ctx.stroke(); ctx.restore();
      for (const [dx, h] of [[-30, 26], [8, 34], [40, 22]]) { ctx.beginPath(); ctx.moveTo(cx + dx - 6, cy + 8); ctx.lineTo(cx + dx, cy + 8 - h); ctx.lineTo(cx + dx + 6, cy + 8); ctx.closePath(); ctx.fillStyle = "#c8bcff"; ctx.fill(); ctx.lineWidth = 1.5; ctx.strokeStyle = OUT; ctx.stroke(); }
    } },
    friend: { zh: "朋友的足跡", icon: "notes", draw(ctx, region) {
      for (let k = 0; k < 7; k++) { const x = 0.6 * T + k * 0.55 * T, y = 2.2 * T - k * 6 + (k % 2) * 8; ctx.fillStyle = "rgba(255,255,255,0.85)"; ctx.beginPath(); ctx.ellipse(x, y, 4, 6, 0.4, 0, TAU); ctx.fill(); }
      E.stele(ctx, 4.6, 0.7); E.bubble(ctx, 5.1 * T, 0.9 * T, "scroll", "info");
    } },
  };
  /** 畫一張事件插圖（W×H），四周暗角，左上角一個事件類型的小牌。 */
  function draw(ctx, kind, region = "cloud") {
    const s = SCENES[kind]; ctx.save(); ctx.beginPath(); ctx.roundRect(0, 0, W, H, 12); ctx.clip();
    ground(ctx, region); s.draw(ctx, region);
    const v = ctx.createRadialGradient(W / 2, H / 2, H * 0.4, W / 2, H / 2, W * 0.62); v.addColorStop(0, "rgba(0,0,0,0)"); v.addColorStop(1, "rgba(10,8,6,0.65)"); ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
    ctx.restore();
    ctx.lineWidth = 2; ctx.strokeStyle = "#c8a868"; ctx.beginPath(); ctx.roundRect(1, 1, W - 2, H - 2, 12); ctx.stroke();
    ctx.font = "bold 13px 'Microsoft JhengHei'"; const tw = ctx.measureText(s.zh).width + 34;
    ctx.fillStyle = "rgba(24,20,16,0.85)"; ctx.beginPath(); ctx.roundRect(8, 8, tw, 24, 12); ctx.fill(); ctx.strokeStyle = "#c8a868"; ctx.lineWidth = 1.2; ctx.stroke();
    const IC = (window.Hud && Hud.I) || E.ICON; if (IC[s.icon]) IC[s.icon](ctx, 21, 20, 13); ctx.fillStyle = "#f2e6c8"; ctx.textBaseline = "middle"; ctx.fillText(s.zh, 32, 21);
  }
  return { W, H, SCENES, draw };
})();
