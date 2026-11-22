// e4Triggers.js：E4 兩個新觸發時機的 Q 版部件圖樣（畫圖 agent，2026-11-22；紀錄 docs/art/E4-觸發圖示-美術.md）。
// 範圍（PhaseE4報告 第 2.3、2.4 節；遊戲端 client/src/render/qIcon/parts.ts 第 633 行 TRIG_ALIAS 的兩筆暫借）：
//   ① on_block「格擋時」：持有者的格擋類反應真的擋下一次攻擊時（現行暫借 hit_by_melee「被近戰命中時」）；
//   ② on_displace「你讓別人位移時」：持有者推、拉、擊退、傳送別人、和別人互換位置時，自己移動不算（現行暫借 on_collision「造成撞擊後」）。
// 畫法語言照第④批部件（qIconsParts.js）：±10 單位、平塗三階、剪影外框、後畫的那件用 halo() 自己再包一圈；≤14px（o.tiny）不包外框、省小零件。
// 不改任何過審的畫法檔：新圖樣只在頁面呼叫 install() 時塞進 QIconsParts.CATS.trigger（同 SK-3、AP-2 的作法）。
// 確定性：沒有 Math.random。
window.E4Trig = (() => {
  const Q = window.QIcons, QS = window.QIconsSkills, QP = window.QIconsParts;
  const { mix, f, rr, ci, poly, ln, starPts, halo } = Q.H;
  const PI = Math.PI, OUT = "#16121a";
  /* 以下小工具與色照抄 qIconsParts.js（檔內沒有匯出；第 10～65、297 行），值不改。 */
  const CREAM = "#f2e6c8", ENEMY = "#ff5a5a", STEEL = "#c3ccd6", GOLD = "#e8bb48";
  const at = (c, x, y, k, fn, rot = 0) => { c.save(); c.translate(x, y); c.rotate(rot); c.scale(k, k); fn(c); c.restore(); };
  const bust = (c, col, x, y, k = 1) => { ci(c, col, x, y - 4.6 * k, 3.7 * k); f(c, col, () => { c.moveTo(x - 6.2 * k, y + 7 * k); c.quadraticCurveTo(x - 6.2 * k, y - 0.4 * k, x, y - 0.4 * k); c.quadraticCurveTo(x + 6.2 * k, y - 0.4 * k, x + 6.2 * k, y + 7 * k); c.closePath(); }); };
  const arrowS = (c, col, hi) => { poly(c, col, [[-10, -2.4], [1, -2.4], [1, -5.6], [10, 0], [1, 5.6], [1, 2.4], [-10, 2.4]], 0.4); if (hi) poly(c, hi, [[-10, -2.4], [1, -2.4], [1, -5.6], [10, 0], [-10, 0]]); };
  const burstStar = (c, x, y, R, col = "#ffd23f") => { poly(c, col, starPts(x, y, R, R * 0.48, 7, -1.2), 0.3); poly(c, "#ffffff", starPts(x, y, R * 0.48, R * 0.24, 7, -1.2)); };
  const BLADE_STEEL = [STEEL, "#ffffff", "#98a2ae"];
  const bladeSword = (c, o, B = BLADE_STEEL) => { c.save(); c.translate(0, -0.65);
    poly(c, B[0], [[-2.9, 3.6], [-2.9, -9.4], [0, -13.6], [2.9, -9.4], [2.9, 3.6]], 0.4);
    poly(c, B[1], [[-2.9, 3.6], [-2.9, -9.4], [0, -13.6], [-0.4, -9.4], [-0.4, 3.6]]); f(c, B[2], () => c.rect(1.3, -9, 1.6, 12.6));
    rr(c, GOLD, -6.4, 3.4, 12.8, 3.4, 1.5); f(c, "#fff0b0", () => c.roundRect(-6.4, 3.4, 12.8, 1.2, [1.5, 1.5, 0, 0]));
    rr(c, "#a8703e", -1.7, 6.6, 3.4, 5.4, 1); ci(c, GOLD, 0, 12.6, 2.4); c.restore(); };
  const shieldArt = (c, o) => QS.ACT.shield.d(c, o, QS.ACT.shield.def); /* 受擊家族的同一面淡藍盾（白十字紋） */

  // =====================================================================
  // 1. 格擋時 on_block
  //    受擊家族（被近戰命中時／被攻擊時／被法術命中時／敵人擲中你時）＝「左上大的來襲物（佔一半）＋右下小藍盾」：來襲物是主角、盾是被打的你。
  //    格擋時把主從倒過來：同一面藍盾放大到佔滿（擋得住的是你），來襲的劍縮小、被彈開（劍尖朝外、往左上翻），
  //    劍與盾碰到的那一點（盾的左上緣）一顆黃白的撞擊星＝「鏗」一聲擋下。≤14 只留盾＋撞擊星（規則 8；劍在 12px 只剩幾個灰點）。
  // =====================================================================
  /** 定案：大藍盾＋左上緣的黃撞擊星＋（>14）被彈開的小亮劍。 */
  function blockArt(c, o) {
    at(c, 2.4, 1.6, 0.84, (q) => shieldArt(q, o));
    if (!o.tiny) halo(c, o, (q) => at(q, -6.0, 2.2, 0.46, (p) => bladeSword(p, o), -0.42)); /* 盾的左邊、劍尖朝左上外翻（被彈開），柄在右下；不疊在撞擊星底下 */
    halo(c, o, (q) => burstStar(q, -3.6, -4.6, o.tiny ? 5.2 : 4.6, "#ffd23f")); /* 盾的左上緣：鏗一聲擋下的那一點 */
  }
  /** 試過不用（B）：大藍盾＋被彈回去的紅箭頭（「被攻擊時」的紅箭頭掉頭朝左上），碰撞點一顆撞擊星。 */
  function blockArrowBack(c, o) {
    at(c, 2.2, 2.2, 0.84, (q) => shieldArt(q, o));
    halo(c, o, (q) => at(q, -4.6, -4.6, 0.6, (p) => arrowS(p, ENEMY, o.tiny ? null : "#ffb0a8"), -PI * 0.75));
    halo(c, o, (q) => burstStar(q, -3.0, -3.0, 4.2, "#ffd23f"));
  }
  /** 試過不用（C）：大藍盾＋劍砍在盾面上停住（劍尖碰到盾，同「被近戰命中時」的劍、只是縮小）＋撞擊星。 */
  function blockSwordStopped(c, o) {
    at(c, 2.6, 2.6, 0.8, (q) => shieldArt(q, o));
    halo(c, o, (q) => at(q, -4.2, -4.2, 0.5, (p) => bladeSword(p, o), PI * 0.75));
    halo(c, o, (q) => burstStar(q, -1.2, -1.2, 4.0, "#ffd23f"));
  }

  // =====================================================================
  // 2. 你讓別人位移時 on_displace
  //    要說的是「別人被我移走了」，不是我自己走（靴子、雙 V、跳躍弧、瞬步都是自己動）。
  //    主體＝被移走的那個人（紅色人形＝另一方，同「被攻擊時」「敵人靠近時」的紅；隊友也算，但另一方多數是敵人）。
  //    他原本站的地方只剩腳下一圈米白的空影子圈（扁橢圓環＝「這裡原本有人」），影子圈上方兩道米白速度線拖到人形背後＝整個人被挪過去。
  //    沒有畫推的人與箭頭：卡片上「推擊」「拉扯」「交換位置」這些效果自己就有箭頭，觸發再畫一個箭頭會和效果列並排撞圖；
  //    也不用兩個人形（殘影）：18 剪影是並排兩個人形，和條件「身旁有友方」同剪影。
  //    ≤14：影子圈畫成實心扁橢圓、速度線一道。
  // =====================================================================
  const GHOST = mix(ENEMY, OUT, 0.55); /* 試過不用的殘影：紅人形本色混外框色（暗一階的同一個紅） */
  /** 定案：右邊亮紅人形，左下原地一圈米白空影子圈，影子圈上方兩道米白速度線（≤14 實心扁橢圓＋一道）。 */
  function displaceArt(c, o) {
    at(c, 0.4, -0.4, 0.9, (u) => {
      if (o.tiny) f(u, CREAM, () => u.ellipse(-5.8, 7.6, 4.4, 2.2, 0, 0, PI * 2));
      else { f(u, CREAM, () => u.ellipse(-6.0, 7.6, 4.6, 2.4, 0, 0, PI * 2)); f(u, OUT, () => u.ellipse(-6.0, 7.6, 2.6, 0.9, 0, 0, PI * 2)); } /* 環的洞用外框色＝自查不算進亮度 */
      for (const [y, x0, x1] of o.tiny ? [[1.2, -8.6, -1.0]] : [[-2.2, -8.4, -1.6], [2.6, -9.8, -1.2]]) rr(u, CREAM, x0, y - 1.1, x1 - x0, 2.2, 1.1);
      halo(u, o, (q) => bust(q, ENEMY, 4.8, 2.6, 0.9));
    });
  }
  /** 試過不用（B）：左邊暗紅殘影、右邊亮紅人形，中間兩道米白速度線。 */
  function displaceGhost(c, o) {
    at(c, 0, 0, 0.96, (u) => {
      bust(u, GHOST, -4.4, 2.2, 0.86);
      if (!o.tiny) for (const [y, x0, x1] of [[-2.6, -9.6, -3.4], [3.2, -10.4, -2.6]]) rr(u, CREAM, x0, y - 1.1, x1 - x0, 2.2, 1.1);
      halo(u, o, (q) => bust(q, ENEMY, 4.2, 2.2, 0.86));
    });
  }
  /** 試過不用（C）：亮紅人形往右傾，左邊一個米白粗箭頭頂著它。 */
  function displaceShove(c, o) {
    at(c, 3.8, 1.6, 1, (q) => bust(q, ENEMY, 0, 0, 0.86), 0.32);
    halo(c, o, (q) => at(q, -4.8, 2.2, 0.56, (p) => arrowS(p, CREAM, o.tiny ? null : "#ffffff")));
  }
  /** 試過不用（D）：殘影＋人形，上方一個米白粗箭頭（從殘影指向人形）。 */
  function displaceGhostArrow(c, o) {
    bust(c, GHOST, -5.2, 2.2, 0.78);
    halo(c, o, (q) => bust(q, ENEMY, 4.6, 2.2, 0.78));
    halo(c, o, (q) => at(q, -0.4, -5.4, 0.48, (p) => arrowS(p, CREAM, o.tiny ? null : "#ffffff")));
  }
  /** 試過不用（E）：同定案，人形往右傾（被推的身體）。 */
  function displaceSpotLean(c, o) {
    at(c, 0, 0, 0.96, (u) => {
      if (o.tiny) f(u, CREAM, () => u.ellipse(-5.2, 7.8, 4.6, 2.2, 0, 0, PI * 2));
      else { f(u, CREAM, () => u.ellipse(-5.2, 7.8, 5.0, 2.4, 0, 0, PI * 2)); f(u, OUT, () => u.ellipse(-5.2, 7.8, 3.0, 1.0, 0, 0, PI * 2)); }
      for (const [y, x0, x1] of o.tiny ? [[0.6, -8.6, -1.6]] : [[-3.0, -8.2, -2.4], [1.8, -9.6, -2.0]]) rr(u, CREAM, x0, y - 1.1, x1 - x0, 2.2, 1.1);
      halo(u, o, (q) => at(q, 4.2, 9.0, 1, (p) => bust(p, ENEMY, 0, -6.6, 0.9), 0.28));
    });
  }
  /** 試過不用（F）：斜的——左下影子圈，人形離地飛到右上，兩道斜的速度線（想和「敵人靠近／離開時」的橫排分開）。 */
  function displaceFlung(c, o) {
    at(c, 0, 0, 0.96, (u) => {
      if (o.tiny) f(u, CREAM, () => u.ellipse(-5.6, 8.0, 4.6, 2.2, 0, 0, PI * 2));
      else { f(u, CREAM, () => u.ellipse(-5.6, 8.0, 5.2, 2.5, 0, 0, PI * 2)); f(u, OUT, () => u.ellipse(-5.6, 8.0, 3.2, 1.1, 0, 0, PI * 2)); }
      at(u, -2.6, -0.2, 1, (q) => { for (const [y, x0, x1] of o.tiny ? [[0, -4.0, 3.0]] : [[-2.1, -3.2, 3.0], [2.1, -4.6, 2.2]]) rr(q, CREAM, x0, y - 1.1, x1 - x0, 2.2, 1.1); }, -0.62);
      halo(u, o, (q) => bust(q, ENEMY, 5.0, -1.2, 0.84));
    });
  }
  const TRIG = {
    on_block: { zh: "格擋時", topic: "一面放大的淡藍盾（受擊家族的同一面盾，佔滿），左上緣一顆黃白撞擊星，一把小亮劍被彈開、劍尖朝左上外翻（≤14 只留盾＋撞擊星）", d: blockArt },
    on_displace: { zh: "你讓別人位移時", topic: "右邊一個紅色人形（被移走的另一方），左下原地一圈米白空影子圈，影子圈上方兩道米白速度線拖到人形背後（≤14 實心影子＋一道速度線）", d: displaceArt },
  };
  /** 試過的方案（只給樣張頁的「試過」段；A＝定案）。 */
  const TRIALS = {
    on_block: [["A 定案：大盾＋撞擊星＋彈開的劍", blockArt], ["B 大盾＋掉頭的紅箭頭", blockArrowBack], ["C 大盾＋劍停在盾面", blockSwordStopped]],
    on_displace: [["A 定案：原地空影子圈＋速度線＋人形", displaceArt], ["B 暗紅殘影＋人形＋速度線", displaceGhost], ["C 人形往右傾＋米白箭頭頂著", displaceShove], ["D 殘影＋人形＋上方米白箭頭", displaceGhostArrow], ["E 同 A、人形往右傾", displaceSpotLean], ["F 斜的：左下影子圈、人形飛到右上", displaceFlung]],
  };
  /** 現行（遊戲端）畫的是誰：TRIG_ALIAS 的暫借對象。 */
  const LIVE = { "trigger:on_block": ["trigger", "hit_by_melee"], "trigger:on_displace": ["trigger", "on_collision"] };

  function install(opt = {}) {
    for (const [id, e] of Object.entries(TRIG)) QP.CATS.trigger[id] = { ...e, src: "new:e4" };
    if (opt.trials) for (const [id, list] of Object.entries(TRIALS)) list.forEach(([zh, d], i) => { QP.CATS.trigger[`${id}__try${i}`] = { zh, topic: zh, d, src: "try:e4" }; });
  }
  return { TRIG, TRIALS, LIVE, GHOST, install, blockArt, displaceArt };
})();
