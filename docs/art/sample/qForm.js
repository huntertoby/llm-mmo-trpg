// qForm.js：形態（變身）10 種的 Q 版畫法（美術 PM 畫圖 agent，2026-11-07）。
// 使用者（11-07）：「所有人先停下 先讓q板完成再開始工作 把所有需要q版的都完成 腳色 動畫 怪物 npc 等 全部」。
// 定稿方向照 docs/archive/art/形態外觀.md 最後一節（2026-10-24）：① 另畫，不沿用召喚物 ② 主角服裝主色（hero）當毛色或紋路 ③ 比同類召喚物大一號，腳下加形態光環。
//   10 種：熊 1.3、貓 1.25、鳥（巨鵰）1.2、惡魔 1.2、巨人 1.45、元素化身 1.2、暗影 1.2、樹人 1.3、狼人 1.25、龍 1.5。
// 畫法層和 qSummon.js／qCreature.js 同一套（平塗、細縫線、整隻剪影外框 1.3、方眼）。「外光只代表頭目」：形態不發外光；形態光環是地面的平塗環（藍色陣營環＋藍紫外環＋刻點）。
// 朝向：四足、鳥、龍畫側面（朝西鏡像；朝南用朝東、朝北用朝西）；惡魔、巨人、元素化身、暗影、樹人、狼人畫正面，朝東、朝西眼睛偏移，背面不畫臉與胸前的東西。
// 不認得的形態 → 原角色 QDoll＋形態光環。確定性：不用 Math.random。
window.QForm = (() => {
  const { ink, stroke, limb, dot, beye, qeye, lay, shadow, mix, dark, light, ellPts, OUT, TAU } = window.QSummon.H;
  const ELEM = { fire: { c: "#ff7a2a", l: "#ffd04a", d: "#c84a14" }, ice: { c: "#8fd8f5", l: "#e8fbff", d: "#4a9ac0" }, lightning: { c: "#ffd84a", l: "#fff7c0", d: "#b88a10" } };
  const FORMS = {
    bear: { zh: "熊", size: 1.3, side: true, vs: "戰狼 1.0" }, cat: { zh: "貓", size: 1.25, side: true, vs: "戰狼 1.0" }, bird: { zh: "鳥（巨鵰）", size: 1.2, side: true, vs: "鷹隼 0.8" },
    demon: { zh: "惡魔", size: 1.2, vs: "影魅 1.0" }, giant: { zh: "巨人", size: 1.45, vs: "石像 1.25" }, avatar: { zh: "元素化身", size: 1.2, vs: "元素之靈 1.0" },
    shadow: { zh: "暗影形態", size: 1.2, vs: "影魅 1.0" }, treant: { zh: "樹人", size: 1.3, vs: "藤蔓 1.0" }, werewolf: { zh: "狼人", size: 1.25, vs: "戰狼 1.0" }, dragon: { zh: "龍", size: 1.5, side: true, vs: "（無同類）" },
  };
  const HEAD = (ctx, x, y, s, fn) => { ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.translate(-x, -y); fn(); ctx.restore(); }; // Q 大頭：以頸為中心放大

  // ============================== 側面（四足、鳥、龍） ==============================
  function bear(g, P) {
    const fur = mix("#6a4a32", P.hero, 0.25), d = dark(fur, 0.28), l = light(fur, 0.3);
    for (const x of [-11, 6]) ink(g, [[x - 2.8, -12], [x + 2.8, -12], [x + 3, 0], [x - 3, 0]], d);
    ink(g, [[-17, -9], [-17, -22], [-8, -29.6], [4, -29], [14, -22], [15, -9], [-2, -7]], fur);
    ink(g, ellPts(-1, -10.6, 10, 2.6, 14), l, { line: false });
    for (const x of [-10, -4, 2]) stroke(g, [[x - 1.6, -28.4], [x, -24.6], [x - 0.6, -21.4]], 1.6, P.hero); // 背上三道紋（主色）
    for (const x of [-6, 11]) ink(g, [[x - 3, -12], [x + 3, -12], [x + 3.4, 0], [x - 3.2, 0]], fur);
    HEAD(g, 11, -21, 1.3, () => {
      ink(g, ellPts(13.6, -30.6, 2.2, 2.2, 10), fur);
      ink(g, [[9, -26], [14, -31], [21, -29.4], [25.6, -23], [23.6, -19.6], [16, -18], [10, -20]], fur);
      ink(g, ellPts(23.4, -22.2, 2.6, 2, 10), l); dot(g, 25.2, -23, 0.9, 0.8, OUT); beye(g, 18.6, -25.6, "#ffd23a", 0.9);
    });
  }
  function cat(g, P) {
    const fur = mix("#4a4a58", P.hero, 0.25), d = dark(fur, 0.3), sp = light(P.hero, 0.15);
    for (const x of [-8, 10]) ink(g, [[x - 1.6, -9], [x + 1.6, -9], [x + 1.8, 0], [x - 1.8, 0]], d);
    ink(g, [[-12, -12.4], [-21, -12], [-26, -7], [-24, -5.4], [-20, -9], [-12, -9]], fur);
    ink(g, ellPts(-24.6, -6.6, 2, 1.6, 10), P.hero, { line: false }); // 尾尖（主色）
    ink(g, ellPts(0, -11, 14, 5, 20), fur);
    for (const [x, y] of [[-8, -12.6], [-3, -14], [2, -12], [-5, -9.4], [6.4, -13]]) dot(g, x, y, 1.3, 0.9, sp); // 豹斑（主色）
    for (const x of [-11, 7]) ink(g, [[x - 1.7, -9], [x + 1.7, -9], [x + 2, 0], [x - 2, 0]], fur);
    HEAD(g, 11, -12, 1.35, () => {
      for (const x of [13, 17.4]) ink(g, [[x - 2.2, -16.6], [x, -21.6], [x + 2.2, -16.6]], fur, { sharp: true });
      ink(g, ellPts(15, -14.5, 5.4, 4.6, 16), fur);
      ink(g, ellPts(19.2, -13, 2.2, 1.6, 10), light(fur, 0.35)); beye(g, 17.2, -15.4, "#b8f04a", 0.9); dot(g, 21, -13.4, 0.6, 0.5, OUT);
    });
  }
  function bird(g, P) {
    const c = "#8a6a40", d = "#5e4628";
    g.save(); g.translate(0, -10);
    ink(g, [[-4, -4], [-10, -18], [-16, -32], [-11, -29], [-12, -36], [-6, -24], [2, -6]], d, { sharp: true }); // 遠側翅：往上舉（V 字的後半）
    ink(g, [[-16, -32], [-11, -29], [-12, -36]], dark(P.hero, 0.2), { sharp: true, line: false });
    ink(g, [[-8, 2], [-18, 4], [-16, 0], [-20, -1], [-9, -2]], P.hero, { sharp: true }); // 尾羽（主色）
    ink(g, ellPts(0, 0, 9.4, 6, 16), c);
    ink(g, ellPts(1.4, 2, 6.4, 3, 12), "#f0e6d0", { line: false });
    ink(g, [[0, -4], [6, -18], [12, -32], [13.4, -26], [18, -30], [13, -16], [5, -2]], c, { sharp: true }); // 近側翅：往上往前舉
    ink(g, [[12, -32], [13.4, -26], [18, -30], [15, -23]], P.hero, { sharp: true });
    HEAD(g, 7, -1, 1.25, () => {
      ink(g, [[6.4, -7], [5, -11.4], [8, -8.6], [8.6, -12], [10, -8]], P.hero, { sharp: true }); // 頭冠（主色）
      ink(g, ellPts(9.4, -4, 4.4, 4.2, 12), c);
      ink(g, [[13, -5.4], [17.6, -3.2], [15, -1.4], [13, -1.4]], "#e8bb48", { sharp: true, line: false });
      beye(g, 11, -5, "#ffd23a", 0.8);
    });
    for (const x of [-2, 3]) { stroke(g, [[x, 5], [x, 9]], 1.4, "#e8bb48"); stroke(g, [[x - 1.4, 9.6], [x, 9], [x + 1.6, 9.6]], 0.8, "#e8bb48"); }
    g.restore();
  }
  function dragon(g, P) {
    const c = mix("#3a5068", P.hero, 0.3), d = dark(c, 0.3), E = P.el, fin = P.hero;
    for (const x of [-9, 6]) ink(g, [[x - 2.6, -10], [x + 2.6, -10], [x + 3, 0], [x - 3, 0]], d); // 遠側腳
    ink(g, [[-30, -18], [-24, -26], [-16, -38], [-8, -46], [-10, -34], [-4, -40], [-6, -28], [0, -32], [-2, -22]], dark(c, 0.15)); // 翅膀（往上張，在身後）
    stroke(g, [[-16, -38], [-10, -24]], 0.6, d); stroke(g, [[-8, -46], [-6, -26]], 0.6, d);
    ink(g, [[-12, -12], [-22, -12], [-32, -6], [-36, -2], [-28, -4], [-12, -6]], c); // 尾巴
    ink(g, [[-37, -1.6], [-33, -5.6], [-31.6, -1]], fin, { sharp: true }); // 尾尖（主色）
    for (const x of [-24, -18]) ink(g, [[x - 2, -11.4 + (x + 24) * 0.05], [x, -15], [x + 2, -11.6]], fin, { sharp: true });
    ink(g, ellPts(-2, -14, 14, 7.4, 20), c);
    ink(g, [[-12, -8.6], [8, -8.6], [6, -6.8], [-10, -6.8]], E.c, { line: false }); // 腹甲（元素色）
    for (const x of [-9, -3, 3]) ink(g, [[x - 2.2, -20.6], [x, -25], [x + 2.2, -20.8]], fin, { sharp: true }); // 背鰭（主色）
    for (const x of [-6, 9]) ink(g, [[x - 3, -11], [x + 3, -11], [x + 3.4, 0], [x - 3.2, 0]], c);
    ink(g, [[6, -18], [10, -26], [12, -32], [17, -31], [15, -24], [12, -14]], c); // 頸
    stroke(g, [[13.4, -17], [15.4, -24]], 1.8, E.c);
    HEAD(g, 14, -30, 1.3, () => {
      for (const [x, y] of [[10, -34.6], [13, -35.4]]) ink(g, [[x, y + 1.4], [x - 5, y - 4], [x + 1.6, y - 0.6]], fin, { sharp: true }); // 角（主色）
      ink(g, [[10, -32], [14, -35], [19, -34.6], [25, -31.6], [25.6, -29], [19, -27.4], [12, -27.6]], c);
      dot(g, 24.2, -31.6, 0.7, 0.5, OUT); beye(g, 16.6, -31.6, E.l, 0.85);
      ink(g, [[19, -27.6], [24, -28.6], [22, -26.6]], "#f4ecd8", { sharp: true, line: false });
    });
    for (const [x, y, r] of [[30, -34, 2.2], [33.6, -35.4, 1.5]]) ink(g, ellPts(x, y, r, r, 10), E.l); // 吐息（元素色，平塗，不發光）
  }

  // ============================== 正面（人形） ==============================
  const eyes = (g, f, y, gap, col, r = 1, fn = qeye) => { if (f.ex === null) return; fn(g, f.ex - gap, y, col, r); fn(g, f.ex + gap, y, col, r); };
  function demon(g, P, f) {
    const sk = "#8a4a9a", d = dark(sk, 0.3), wing = "#3a2440", B = f.ex === null;
    const wings = () => { for (const sg of [-1, 1]) { ink(g, [[sg * 5, -24], [sg * 14, -34], [sg * 22, -32], [sg * 19, -26], [sg * 22, -21], [sg * 15, -20], [sg * 16, -14], [sg * 7, -17]], wing, { sharp: true }); stroke(g, [[sg * 14, -33], [sg * 12, -20]], 0.6, light(wing, 0.25)); } };
    if (!B) wings();
    stroke(g, [[3, -10], [10, -6], [12, -10], [14.6, -9]], 1.4, d); ink(g, [[13.6, -11], [17, -9.4], [13.8, -7.4]], d, { sharp: true }); // 尾巴
    for (const sg of [-1, 1]) ink(g, [[sg * 1, -10], [sg * 5.6, -10], [sg * 5, 0], [sg * 1.4, 0]], d);
    ink(g, [[-7, -22.6], [7, -22.6], [6.2, -9.6], [-6.2, -9.6]], P.hero); // 上衣（主色）
    if (!B) stroke(g, [[0, -22], [0, -14]], 0.6, dark(P.hero, 0.4));
    for (const sg of [-1, 1]) { limb(g, [[sg * 7.6, -21], [sg * 10, -15], [sg * 10.6, -11]], 3, sk); ink(g, ellPts(sg * 10.6, -10.4, 2.2, 2.2, 10), sk);
      g.save(); g.translate(sg * 10.6, -10.4); g.scale(sg, 1); ink(g, [[-0.6, 0.6], [3, -4], [6, -12], [4.6, -4], [1.4, 1.6]], "#c8d0d8", { sharp: true }); g.restore(); } // 兩把彎刃
    if (B) wings();
    for (const sg of [-1, 1]) ink(g, [[sg * 4, -36], [sg * 9, -40], [sg * 10.6, -46], [sg * 7, -41.6], [sg * 3, -38.6]], "#e8d8b8"); // 彎角
    ink(g, ellPts(0, -30, 8, 7.6, 18), sk);
    eyes(g, f, -30, 2.8, "#ffd23a", 1);
    if (!B) { ink(g, [[f.ex - 1.6, -25.4], [f.ex - 1, -24], [f.ex - 0.4, -25.4]], "#f4ecd8", { sharp: true, line: false }); ink(g, [[f.ex + 0.4, -25.4], [f.ex + 1, -24], [f.ex + 1.6, -25.4]], "#f4ecd8", { sharp: true, line: false }); }
  }
  function giant(g, P, f) {
    const sk = "#d9a47a", d = dark(sk, 0.22), B = f.ex === null;
    for (const sg of [-1, 1]) ink(g, [[sg * 1.2, -12], [sg * 7, -12], [sg * 7.4, 0], [sg * 0.8, 0]], d);
    ink(g, [[-10, -30], [10, -30], [11, -14], [-11, -14]], sk); // 赤膊的大身體
    ink(g, [[-11, -15.6], [11, -15.6], [10.4, -13.4], [-10.4, -13.4]], "#5a3a22", { sharp: true }); // 腰帶
    ink(g, [[-9, -13.4], [9, -13.4], [8, -6.6], [3, -8], [0, -6], [-3, -8], [-8, -6.6]], P.hero, { sharp: true }); // 腰布（主色）
    ink(g, ellPts(B ? -9.6 : 9.6, -29, 4.4, 3, 12), P.hero); // 護肩（主色，左肩：正面在畫面右、背面在畫面左）
    for (const sg of [-1, 1]) { limb(g, [[sg * 10.6, -27], [sg * 13.6, -20], [sg * 14, -15]], 4.2, sk); ink(g, ellPts(sg * 14, -13.4, 3, 2.8, 10), sk); }
    g.save(); g.translate(B ? 14 : -14, -13.4); g.rotate(B ? 0.35 : -0.35); ink(g, [[-1, 1.4], [-1.4, -8], [-3, -14], [0, -19], [3.6, -15], [2, -8], [1, 1.4]], "#8a847e"); g.restore(); // 石棒（右手：正面在畫面左）
    ink(g, ellPts(0, -36, 7.6, 7, 16), sk); // 頭（身體大，頭相對小一點）
    ink(g, [[-7.4, -38], [-6, -43], [0, -44.4], [6, -43], [7.4, -38], [3, -40], [-3, -40]], "#6a3d1e");
    eyes(g, f, -35.6, 2.6, "#1d1a22", 0.9);
    if (!B) { stroke(g, [[f.ex - 3.8, -38.6], [f.ex - 1.6, -38]], 0.7, "#6a3d1e"); stroke(g, [[f.ex + 1.6, -38], [f.ex + 3.8, -38.6]], 0.7, "#6a3d1e"); }
  }
  function avatar(g, P, f) {
    const E = P.el, B = f.ex === null, el = P.element;
    for (const sg of [-1, 1]) ink(g, [[sg * 1, -10], [sg * 5.6, -10], [sg * 4, -1], [sg * 2, 0]], E.d); // 腳收成尖
    ink(g, [[-7, -23], [7, -23], [5.4, -9.6], [-5.4, -9.6]], E.c);
    for (const sg of [-1, 1]) { limb(g, [[sg * 7.6, -21.6], [sg * 10, -15], [sg * 10.4, -11]], 3, E.c); ink(g, ellPts(sg * 10.4, -10, 2.2, 2.2, 10), E.l); }
    if (!B) { ink(g, [[0, -21], [3, -17], [0, -13], [-3, -17]], P.hero, { sharp: true }); ink(g, [[0, -19.4], [1.4, -17], [0, -14.6], [-1.4, -17]], light(P.hero, 0.45), { sharp: true, line: false }); } // 胸口核心（主色）
    // 頭頂：火＝火焰髮、冰＝冰冠、雷＝閃電髮
    if (el === "ice") for (const [x, h] of [[-5, 6], [0, 9], [5, 6]]) ink(g, [[x - 2.2, -35], [x, -35 - h], [x + 2.2, -35]], E.l, { sharp: true });
    else if (el === "lightning") for (const sg of [-1, 1]) ink(g, [[sg * 2, -36], [sg * 5, -42], [sg * 3.6, -42.2], [sg * 7, -47], [sg * 7.4, -41], [sg * 8.4, -41.4], [sg * 6.6, -35]], E.c, { sharp: true });
    else ink(g, [[-7, -33], [-6, -41], [-3, -37], [0, -46], [3, -37], [6, -42], [7, -33]], E.c);
    ink(g, ellPts(0, -30, 7.6, 7.4, 18), E.l);
    eyes(g, f, -30, 2.7, "#1d1a22", 1);
  }
  function shadowForm(g, P, f) {
    const c = "#4a3e66", l = "#6a5c88", B = f.ex === null; /* 比戰場底色亮一階，黑外框裡才看得出形狀 */
    for (const sg of [-1, 1]) stroke(g, [[sg * 6, -22], [sg * 12, -19], [sg * 10, -12], [sg * 15, -6]], 1.6, P.hero); // 飄帶（主色）
    ink(g, [[-8, -24], [8, -24], [10, -12], [7, -4], [4, -7], [2, -1], [-1, -6], [-4, -1], [-6, -7], [-10, -12]], c); // 煙影身體（下緣碎開，沒有腳）
    for (const sg of [-1, 1]) { limb(g, [[sg * 8, -22], [sg * 12, -15], [sg * 13, -10]], 2.6, c); for (const k of [-1, 0, 1]) ink(g, [[sg * 13 + k * 1.2 - 0.5, -10], [sg * 13.6 + k * 1.8, -4.6], [sg * 13 + k * 1.2 + 0.5, -10]], "#c8c0d8", { sharp: true, line: false }); } // 長爪
    ink(g, [[-8, -27], [-7, -36], [0, -40], [7, -36], [8, -27], [4, -24], [-4, -24]], c); // 兜帽狀的頭
    if (!B) { ink(g, ellPts(f.ex, -30, 5.4, 4.6, 14), "#140f1c", { line: false }); eyes(g, f, -30.4, 2.4, light(P.hero, 0.55), 0.9, (gg, x, y, col, r) => { gg.fillStyle = col; gg.fillRect(x - 1.2 * r, y - 0.8 * r, 2.4 * r, 1.6 * r); }); } // 眼光（主色淡）
    else stroke(g, [[0, -38], [0, -26]], 0.6, l);
  }
  function treant(g, P, f) {
    const bark = "#7a5232", bd = dark(bark, 0.3), leaf = mix("#4f8a3a", P.hero, 0.35), ll = light(leaf, 0.25), B = f.ex === null;
    for (const sg of [-1, 1]) ink(g, [[sg * 1, -6], [sg * 7, -6], [sg * 10, 0], [sg * 6, -0.6], [sg * 4, 0], [sg * 1.4, -0.6]], bd); // 樹根腳
    ink(g, [[-8, -30], [8, -30], [8.6, -6], [-8.6, -6]], bark); // 樹幹身體
    for (const x of [-4, 3.6]) stroke(g, [[x, -27], [x + 0.6, -20], [x - 0.4, -10]], 0.6, bd);
    for (const sg of [-1, 1]) { limb(g, [[sg * 8, -26], [sg * 13, -22], [sg * 16, -15]], 2.6, bark); stroke(g, [[sg * 13, -22], [sg * 17, -25]], 1.4, bark); ink(g, ellPts(sg * 16.6, -14, 3.4, 3, 12), leaf); ink(g, ellPts(sg * 17.4, -25.4, 2.6, 2.4, 10), leaf); }
    if (!B) { eyes(g, f, -22, 2.8, "#2b1e16", 1, (gg, x, y, col) => { gg.fillStyle = col; gg.beginPath(); gg.ellipse(x, y, 1.3, 1.7, 0, 0, TAU); gg.fill(); gg.fillStyle = "#b8f04a"; gg.fillRect(x - 0.3, y - 0.4, 0.8, 0.8); }); stroke(g, [[f.ex - 2, -16.6], [f.ex, -16], [f.ex + 2, -16.6]], 0.8, "#2b1e16"); }
    for (const [x, y, r] of [[-7, -34, 6], [7, -34, 6], [0, -39, 7.4], [-3, -31, 5], [4, -30.6, 5]]) ink(g, ellPts(x, y, r, r * 0.9, 14), leaf); // 樹冠（綠混主色）
    for (const [x, y] of [[-4, -38], [5, -36], [-8, -32]]) dot(g, x, y, 1.6, 1.2, ll);
  }
  function werewolf(g, P, f) {
    const fur = mix("#6e7078", P.hero, 0.15), d = dark(fur, 0.28), l = light(fur, 0.35), B = f.ex === null;
    for (const sg of [-1, 1]) { ink(g, [[sg * 1.4, -12], [sg * 6.4, -12], [sg * 6.6, -5], [sg * 5, 0], [sg * 1.4, 0], [sg * 2.4, -5]], d); ink(g, [[sg * 1.2, 0.4], [sg * 6, 0.4], [sg * 6.4, -1.6], [sg * 1.4, -1.6]], dark(d, 0.2)); }
    ink(g, [[-7, -12.4], [7, -12.4], [7, -7.6], [5.4, -6], [4, -7.6], [2.4, -5.6], [0.8, -7.6], [-1, -5.8], [-2.6, -7.6], [-4.4, -5.6], [-6, -7.6], [-7, -6]], P.hero, { sharp: true }); // 破褲（主色，下緣破成鋸齒）
    ink(g, [[-8, -26], [8, -26], [7.4, -12], [-7.4, -12]], fur); // 毛胸
    if (!B) ink(g, ellPts(0, -19, 4.4, 4.6, 14), l, { line: false });
    for (const sg of [-1, 1]) { limb(g, [[sg * 8.4, -24], [sg * 11.6, -17], [sg * 12, -11]], 3.2, fur); ink(g, ellPts(sg * 12, -10, 2.4, 2.4, 10), fur); for (const k of [-1, 0, 1]) ink(g, [[sg * 12 + k * 1.2 - 0.5, -8.6], [sg * 12 + k * 1.4, -6], [sg * 12 + k * 1.2 + 0.5, -8.6]], "#f4ecd8", { sharp: true, line: false }); } // 爪
    for (const sg of [-1, 1]) ink(g, [[sg * 2.6, -36], [sg * 6.4, -45], [sg * 8.6, -34.6]], fur, { sharp: true }); // 立耳
    ink(g, ellPts(0, -31, 8.4, 7.4, 18), fur);
    if (!B) { ink(g, ellPts(f.ex * 0.6, -26.6, 4, 3, 12), l); dot(g, f.ex * 0.7, -28.2, 1.2, 0.9, OUT); eyes(g, f, -32.4, 3.2, "#ffd23a", 0.9, beye); ink(g, [[f.ex * 0.6 - 1.8, -24.4], [f.ex * 0.6 - 1.2, -23], [f.ex * 0.6 - 0.6, -24.4]], "#f4ecd8", { sharp: true, line: false }); ink(g, [[f.ex * 0.6 + 0.6, -24.4], [f.ex * 0.6 + 1.2, -23], [f.ex * 0.6 + 1.8, -24.4]], "#f4ecd8", { sharp: true, line: false }); }
    else stroke(g, [[0, -38], [0, -26]], 0.6, d);
  }
  const DRAW = { bear, cat, bird, dragon, demon, giant, avatar, shadow: shadowForm, treant, werewolf };

  // ============================== 形態光環（平塗）：藍色陣營環＋藍紫外環＋刻點 ==============================
  function formRing(ctx, rx) {
    ctx.save();
    ctx.globalAlpha = 0.3; ctx.fillStyle = "#4a7aff"; ctx.beginPath(); ctx.ellipse(0, 0, rx, rx * 0.3, 0, 0, TAU); ctx.fill();
    ctx.globalAlpha = 0.95; ctx.strokeStyle = "#4a7aff"; ctx.lineWidth = 1.1; ctx.stroke();
    ctx.strokeStyle = "#a88aff"; ctx.lineWidth = 1.3; ctx.beginPath(); ctx.ellipse(0, 0, rx + 2.6, (rx + 2.6) * 0.3, 0, 0, TAU); ctx.stroke();
    ctx.fillStyle = "#e0d4ff"; for (let i = 0; i < 8; i++) { const a = (i / 8) * TAU + 0.2; ctx.fillRect(Math.cos(a) * (rx + 2.6) - 0.6, Math.sin(a) * (rx + 2.6) * 0.3 - 0.6, 1.2, 1.2); }
    ctx.restore();
  }
  const FACE = { south: { ex: 0 }, east: { ex: 2.2 }, west: { ex: -2.2 }, north: { ex: null } };
  /**
   * 畫一個形態。form＝FORMS 的 id；facing＝south／east／west／north；k＝每單位幾 px。
   * opts.hero＝主角主色（建議取身體裝備 color，沒有用披風，再沒有用陣營藍）；opts.element＝fire／ice／lightning（元素化身、龍）；opts.unit＝不認得時退回的 QDoll unit。
   */
  function stamp(ctx, form, facing, cx, cy, k = 1, opts = {}) {
    const F = FORMS[form], fc = FACE[facing] ? facing : "south", hero = opts.hero ?? "#2f5fae", element = ELEM[opts.element] ? opts.element : "fire";
    const sz = F ? F.size : 1;
    ctx.save(); ctx.translate(cx, cy);
    ctx.save(); ctx.scale(k * Math.max(1, sz * 0.9), k * Math.max(1, sz * 0.9)); formRing(ctx, form === "dragon" ? 16 : 13); ctx.restore();
    if (!F) { ctx.restore(); const u = opts.unit ?? window.PaperDoll.TEMPLATES.hero_fighter, V = { south: ["front", false], north: ["back", false], east: ["side", false], west: ["side", true] }[fc]; window.QDoll.stamp(ctx, u, V[0], cx, cy, k, V[1]); return; }
    ctx.scale(k * sz, k * sz);
    shadow(ctx, form === "dragon" ? 18 : form === "bird" ? 9 : 11, 0.2, form === "bird" ? 0.22 : 0.3);
    const west = F.side ? fc === "west" || fc === "north" : false, f = F.side ? FACE.east : FACE[fc];
    ctx.scale(west ? -1 : 1, 1);
    const P = { hero, el: ELEM[element], element };
    lay(ctx, sz, (g) => DRAW[form](g, P, f), { box: [-46, -84, 46, 14], fade: form === "shadow" ? [0, -8] : undefined });
    ctx.restore();
  }
  return { stamp, FORMS, ELEM };
})();
