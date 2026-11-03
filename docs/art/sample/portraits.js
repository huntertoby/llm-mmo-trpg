// NPC 頭像（美術 PM，2026-11-04）：用遊戲的 C 畫風紙娃娃（storyDoll.js）正面頭部放大，加上少數頭像專用的小配件（斗笠、布帽、頭巾、護目鏡、刀疤）。
// 給 #120 Q3 C 去文字化的對話泡泡、事件框使用。外觀照 content/world/npcs/<區>.yaml 的身分與個性設計（檔案沒有外觀欄位，這裡是美術 PM 的提案）。
// 確定性：沒有亂數；同一位 NPC 每次畫都一樣。全部程式繪製。
window.Portraits = (() => {
  const SD = StoryDoll, { ink, stroke, ellPts, INK } = SD.H, TAU = Math.PI * 2;
  const REGION = { cloud_ridge: ["#6aa84a", "#2f4a3a", "#8ab890"], ashen_waste: ["#ff6a1a", "#3a2418", "#b07050"], merc: ["#c8a868", "#2a2a3a", "#8a8aa8"] };
  // 每位 NPC：[id, 名字, 身分, 區域, look, gear, 頭像配件]
  const N = [
    ["granny_du", "渡婆婆", "鎮長", "cloud_ridge", { skin: "#e8c8a8", hair: "bun", hairColor: "#c8c8c0", bunBand: "#b8432f" }, { body: { kind: "robe", color: "#3c4a48", trim: "#e8bb48" } }, ["wrinkles"]],
    ["shopkeeper_liu", "柳掌櫃", "商人", "cloud_ridge", { skin: "#f1c9a5", hair: "short", hairColor: "#2a1a10" }, { body: { kind: "robe", color: "#8a6a3a", trim: "#e8bb48" } }, ["cap", "mustache"]],
    ["daoist_qingya", "青崖道長", "技能導師", "cloud_ridge", { skin: "#f1c9a5", hair: "bun", hairColor: "#e8e8e0", bunBand: "#2f5a5a", beard: true }, { body: { kind: "robe", color: "#2f5a5a", trim: "#e8e8e0" } }, []],
    ["hunter_ayue", "阿岳", "獵戶", "cloud_ridge", { skin: "#d9a47a", hair: "short", hairColor: "#3a2414" }, { body: { kind: "leather", color: "#6a5040" } }, ["fur_collar"]],
    ["acolyte_xiaolian", "小蓮", "道童", "cloud_ridge", { skin: "#f6e0cc", hair: "bun", hairColor: "#1a1a1a", bunBand: "#6aa84a" }, { body: { kind: "robe", color: "#8ab890", trim: "#f2e6c8" } }, []],
    ["mistlock_master", "霧鎖真人", "青霧觀觀主", "cloud_ridge", { skin: "#e8d8c8", hair: "long", hairColor: "#9aa8b0" }, { body: { kind: "robe", color: "#e8e8e0", trim: "#3a5a5a" }, head: { kind: "veil", color: "#dfe4e2" } }, ["mist"]],
    ["scarface", "疤面", "斷崖幫二當家", "cloud_ridge", { skin: "#a8724c", hair: "short", hairColor: "#1a1a1a" }, { body: { kind: "leather", color: "#7a6a4a" } }, ["wide_hat", "scar"]],
    ["frost_chime", "霜音", "白狐", "cloud_ridge", null, null, ["fox"]],
    ["smith_shi", "石師傅", "鐵匠", "cloud_ridge", { skin: "#d9a47a", hair: "short", hairColor: "#6a5440", beard: true, build: "stout" }, { body: { kind: "leather", color: "#5a4030" } }, ["headband"]],
    ["iron_lady", "鐵娘", "餘燼集主事、商人", "ashen_waste", { skin: "#c8906a", hair: "long", hairColor: "#6a2a1a" }, { body: { kind: "leather", color: "#4a3a30" } }, ["bandana", "earring"]],
    ["greybeard", "灰鬚", "技能導師", "ashen_waste", { skin: "#d9a47a", hair: "short", hairColor: "#8a8a88", beard: true }, { body: { kind: "robe", color: "#6a5e54", trim: "#ff6a1a" }, head: { kind: "hood", color: "#5a4e44" } }, []],
    ["smith_lu", "爐叔", "鐵匠", "ashen_waste", { skin: "#a8724c", hair: "none", hairColor: "#3a2a1a", beard: true, build: "stout" }, { body: { kind: "bare" } }, ["goggles_up", "soot"]],
    ["scavenger_laotie", "老鐵", "拾荒者", "ashen_waste", { skin: "#c89a7a", hair: "short", hairColor: "#6a6a68" }, { body: { kind: "shirt", color: "#6a5e4a" } }, ["cap", "goggles"]],
    ["priestess_helin", "赫琳", "角魔祭司", "ashen_waste", { skin: "#b07a7a", hair: "long", hairColor: "#1e1418", horns: "curved", hornColor: "#bfb0a4" }, { body: { kind: "robe", color: "#4a1a2a", trim: "#c83a2a" } }, ["rune"]],
    ["overseer_scar", "鍛疤", "熔爐督工", "ashen_waste", { skin: "#8a5a3a", hair: "none", hairColor: "#1a1a1a", build: "stout" }, { body: { kind: "plate" } }, ["scar", "ember_eye"]],
    ["merc_qingfeng", "青鋒", "近戰劍客", "merc", { skin: "#f1c9a5", hair: "long", hairColor: "#1a1a1a" }, { body: { kind: "leather", color: "#2f5a5a" } }, ["headband"]],
    ["merc_chuanyun", "穿雲", "弓手", "merc", { skin: "#e8b890", hair: "short", hairColor: "#a8481e" }, { body: { kind: "leather", color: "#4a6a3a" }, head: { kind: "hood", color: "#4a6a3a" } }, []],
    ["merc_chiyan", "赤焰", "火術士", "merc", { skin: "#f1c9a5", hair: "long", hairColor: "#c83a2a" }, { body: { kind: "robe", color: "#8a2f20", trim: "#ffb030" }, head: { kind: "wizard_hat", color: "#8a2f20" } }, []],
    ["merc_tiebi", "鐵壁", "盾衛", "merc", { skin: "#d9a47a", hair: "short", hairColor: "#3a2414" }, { body: { kind: "plate" }, head: { kind: "helmet", material: "steel" } }, []],
    ["merc_panshi", "磐石", "守護者", "merc", { skin: "#e8b890", hair: "short", hairColor: "#a8481e", beard: true, build: "stout" }, { body: { kind: "mail" } }, []],
    ["merc_huichun", "回春", "醫者", "merc", { skin: "#f6e0cc", hair: "bun", hairColor: "#3a2414", bunBand: "#6aa84a" }, { body: { kind: "robe", color: "#6aa84a", trim: "#f2e6c8" } }, ["apron_cross"]],
    ["merc_qingyin", "清音", "祝禱師", "merc", { skin: "#f1c9a5", hair: "long", hairColor: "#e8e0c8", ears: "pointed" }, { body: { kind: "robe", color: "#f2e6c8", trim: "#e8bb48" } }, []],
    ["merc_jinglei", "驚雷", "雷水術士", "merc", { skin: "#b07a52", hair: "long", hairColor: "#2a8a9a", pattern: "marks", markColor: "#3aa8e0" }, { body: { kind: "robe", color: "#2a4a6a", trim: "#c8a0ff" } }, []],
    ["merc_fuying", "伏影", "陷阱師", "merc", { skin: "#e6c4a4", hair: "short", hairColor: "#2a2a34" }, { body: { kind: "leather", color: "#2a2a34" }, head: { kind: "veil", color: "#3a3a44" } }, []],
  ];
  /** 頭像專用配件（正面、紙娃娃座標：頭中心約在 (0, −42)，半徑約 9）。 */
  function extra(ctx, key, look) {
    switch (key) {
      case "wide_hat": ink(ctx, "p-hat", [[-17, -47], [0, -58], [17, -47], [12, -45.6], [-12, -45.6]], "#c8a868", { w: 0.8 }); stroke(ctx, "p-hat-band", [[-8, -48], [8, -48]], 1, "#6a4a2a"); break;
      case "cap": ink(ctx, "p-cap", [[-9.6, -45], [-8, -52], [0, -54.4], [8, -52], [9.6, -45]], "#3a2a1a", { w: 0.7 }); break;
      case "headband": stroke(ctx, "p-band", [[-9.4, -47], [9.4, -47]], 1.8, "#b8432f"); stroke(ctx, "p-band-tail", [[9, -47], [13, -44], [12, -40]], 1.2, "#b8432f"); break;
      case "bandana": ink(ctx, "p-bandana", [[-9.8, -45], [-7, -52.6], [0, -54], [7, -52.6], [9.8, -45], [0, -47.4]], "#a83a2a", { w: 0.7 }); stroke(ctx, "p-knot", [[9, -46], [13, -42]], 1.4, "#a83a2a"); break;
      case "goggles": for (const x of [-3.4, 3.4]) { ink(ctx, `p-gog${x}`, ellPts(x, -42, 3, 2.6, 12), "#8d969f", { shade: false, w: 0.6 }); ctx.fillStyle = "rgba(160,220,255,0.7)"; ctx.beginPath(); ctx.ellipse(x, -42, 1.9, 1.6, 0, 0, TAU); ctx.fill(); } stroke(ctx, "p-gog-strap", [[-9, -42], [-6.4, -42]], 1, "#3a2a1a"); stroke(ctx, "p-gog-strap2", [[6.4, -42], [9, -42]], 1, "#3a2a1a"); break;
      case "goggles_up": for (const x of [-3.4, 3.4]) ink(ctx, `p-gogu${x}`, ellPts(x, -50, 3, 2.4, 12), "#8d969f", { shade: false, w: 0.6 }); stroke(ctx, "p-gogu-strap", [[-9, -49], [9, -49]], 1, "#3a2a1a"); break;
      case "scar": stroke(ctx, "p-scar", [[-6, -46], [-2, -40], [1, -36]], 1, "#7a2a20"); stroke(ctx, "p-scar-x", [[-5, -43], [-2.4, -44], [-3, -41], [0, -41.6]], 0.6, "#7a2a20"); break;
      case "mustache": stroke(ctx, "p-must", [[-3, -38.4], [0, -39], [3, -38.4]], 1.1, "#2a1a10"); break;
      case "wrinkles": for (const x of [-6.6, 6.6]) stroke(ctx, `p-wr${x}`, [[x - 0.8, -40], [x + 0.6, -38.8]], 0.5, "rgba(120,80,60,0.7)"); stroke(ctx, "p-wr-f", [[-2.6, -47.6], [2.6, -47.6]], 0.5, "rgba(120,80,60,0.6)"); break;
      case "fur_collar": ink(ctx, "p-fur", [[-10, -34], [-4, -31.6], [0, -32.6], [4, -31.6], [10, -34], [8, -30], [-8, -30]], "#d8c8a8", { w: 0.6 }); break;
      case "earring": dot(ctx, -9.2, -38.4, 1, "#e8bb48"); break;
      case "soot": ctx.fillStyle = "rgba(40,30,25,0.35)"; ctx.beginPath(); ctx.ellipse(4.6, -38.6, 2.4, 1.2, 0.2, 0, TAU); ctx.fill(); break;
      case "rune": ctx.save(); ctx.shadowColor = "#ff3a2a"; ctx.shadowBlur = 4; stroke(ctx, "p-rune", [[0, -48], [-1.2, -46], [1.2, -46], [0, -48]], 0.8, "#c83a2a"); ctx.restore(); break;
      case "ember_eye": ctx.save(); ctx.shadowColor = "#ff6a1a"; ctx.shadowBlur = 6; dot(ctx, 3.2, -41, 1.3, "#ffb030"); ctx.restore(); break;
      case "mist": ctx.save(); const g = ctx.createRadialGradient(0, -36, 2, 0, -36, 22); g.addColorStop(0, "rgba(232,232,224,0.6)"); g.addColorStop(1, "rgba(232,232,224,0)"); ctx.fillStyle = g; ctx.fillRect(-24, -60, 48, 40); ctx.restore(); break;
      case "apron_cross": stroke(ctx, "p-cross-v", [[0, -31], [0, -26]], 1.6, "#c83a2a"); stroke(ctx, "p-cross-h", [[-2.5, -28.5], [2.5, -28.5]], 1.6, "#c83a2a"); break;
    }
  }
  function dot(ctx, x, y, r, c) { ctx.fillStyle = c; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill(); }
  /** 白狐霜音：不是紙娃娃，另外畫一張狐臉。 */
  function fox(ctx) {
    ink(ctx, "fox-head", [[-10, -40], [-12, -54], [-5, -47], [0, -48], [5, -47], [12, -54], [10, -40], [6, -33], [0, -30], [-6, -33]], "#f4f0e8", { w: 1 });
    for (const s of [-1, 1]) ink(ctx, `fox-ear${s}`, [[s * 9, -49], [s * 11, -53], [s * 7, -48]], "#e8a0a0", { shade: false, w: 0.4 });
    for (const x of [-4, 4]) { ctx.fillStyle = "#3aa8e0"; ctx.beginPath(); ctx.ellipse(x, -41, 1.4, 1.8, 0, 0, TAU); ctx.fill(); }
    dot(ctx, 0, -34.6, 1.3, INK); stroke(ctx, "fox-mark", [[-1.4, -46], [0, -44.4], [1.4, -46]], 0.8, "#7ad8ff");
    ctx.save(); const g = ctx.createRadialGradient(0, -40, 4, 0, -40, 22); g.addColorStop(0, "rgba(200,240,255,0.0)"); g.addColorStop(1, "rgba(200,240,255,0.35)"); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, -40, 22, 0, TAU); ctx.fill(); ctx.restore();
  }
  /** 畫一張頭像：size 是邊長；框色依區域（雲嶺綠、荒原橘、傭兵金）。 */
  function portrait(ctx, x, y, size, n) {
    const [id, , , region, look, gear, extras] = n, [frame, bgD, bgL] = REGION[region];
    ctx.save(); ctx.translate(x, y);
    ctx.beginPath(); ctx.roundRect(0, 0, size, size, size * 0.14); ctx.save(); ctx.clip();
    const g = ctx.createLinearGradient(0, 0, 0, size); g.addColorStop(0, bgL); g.addColorStop(1, bgD); ctx.fillStyle = g; ctx.fillRect(0, 0, size, size);
    const k = size / 34, cy = size * 0.47;
    ctx.translate(size / 2, cy + 42 * k); ctx.scale(k, k);
    if (extras.includes("fox")) fox(ctx);
    else { SD.stamp(ctx, { look, gear }, "front", 0, 0, 1, false); for (const e of extras) extra(ctx, e, look); }
    ctx.restore();
    ctx.lineWidth = Math.max(2, size * 0.04); ctx.strokeStyle = frame; ctx.beginPath(); ctx.roundRect(0, 0, size, size, size * 0.14); ctx.stroke();
    ctx.lineWidth = 1; ctx.strokeStyle = "#1c1712"; ctx.stroke();
    ctx.restore();
  }
  /** 好感度表情（頭頂的小圖示，21.5）：0 敵意、1 冷淡、2 普通、3 友善、4 信賴。 */
  function mood(ctx, x, y, r, level) {
    const col = ["#c83a2a", "#8a8aa8", "#e8e0d0", "#ffd23a", "#ff8ab0"][level];
    ctx.save(); ctx.translate(x, y); ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.fillStyle = col; ctx.fill(); ctx.lineWidth = 1.5; ctx.strokeStyle = "#1c1712"; ctx.stroke();
    ctx.fillStyle = "#1c1712"; for (const s of [-1, 1]) { ctx.beginPath(); ctx.arc(s * r * 0.35, -r * 0.15, r * 0.11, 0, TAU); ctx.fill(); }
    ctx.lineWidth = r * 0.12; ctx.strokeStyle = "#1c1712"; ctx.beginPath();
    if (level === 0) { ctx.arc(0, r * 0.55, r * 0.35, Math.PI * 1.15, Math.PI * 1.85); ctx.moveTo(-r * 0.55, -r * 0.45); ctx.lineTo(-r * 0.2, -r * 0.3); ctx.moveTo(r * 0.55, -r * 0.45); ctx.lineTo(r * 0.2, -r * 0.3); }
    else if (level === 1) { ctx.moveTo(-r * 0.3, r * 0.35); ctx.lineTo(r * 0.3, r * 0.35); }
    else if (level === 2) { ctx.arc(0, r * 0.15, r * 0.3, Math.PI * 0.2, Math.PI * 0.8); }
    else { ctx.arc(0, r * 0.1, r * 0.4, Math.PI * 0.1, Math.PI * 0.9); }
    ctx.stroke();
    if (level === 4) { ctx.fillStyle = "#c83a2a"; ctx.beginPath(); ctx.moveTo(r * 0.9, -r * 0.9); ctx.bezierCurveTo(r * 1.3, -r * 1.3, r * 1.6, -r * 0.6, r * 0.9, -r * 0.2); ctx.bezierCurveTo(r * 0.2, -r * 0.6, r * 0.5, -r * 1.3, r * 0.9, -r * 0.9); ctx.fill(); }
    ctx.restore();
  }
  return { N, REGION, portrait, mood };
})();
