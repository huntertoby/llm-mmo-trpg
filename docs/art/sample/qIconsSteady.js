// qIconsSteady.js：KD-1 新狀態「站穩」（status id: steady）的 Q 版圖樣方案（畫圖 agent 2026-11-22）。
// 紀錄：docs/art/Q版小圖示-站穩.md；樣張頁：q-icons-steady.html；重拍：uv run python -I docs/art/sample/tools/steady_shots.py <暫存資料夾>。
// 資料（content/statuses.yaml）：polarity neutral（六角框、金框、沒有類別底色）；「剛站起來，站得很穩：任何來源都不會讓你倒地；冰面照樣會滑，但滑完不倒地。持續到自己下一個回合結束。」
// 不改任何過審的畫法檔：install() 只把方案塞進 QIconsStatus.NEW（同 ap2Borrow.js 的作法）。
//   steady_a／steady_b／steady_c＝三個方案（樣張比較用）；steady＝推薦的那一個（移植照這一筆搬進 client/src/render/qIcon/status.ts 的 NEW 最後）。
// 畫法照第 5 批：±10 單位、原點為中心；o.tiny＝圖樣本身 ≤14px（狀態卡 20、頭頂 11 都是 tiny：一個主體、不包外框）。
// 依賴（先載入）：qIcons.js（H、ART.hud.move）、qIconsStatus.js（NEW）。
window.QIconsSteady = (() => {
  const Q = window.QIcons, QST = window.QIconsStatus, { f, rr, ci, el, poly, ln, halo } = Q.H, PI = Math.PI;
  const CREAM = "#f2e6c8", GOLD = "#e8bb48", SAND = "#e0c088", SAND_D = "#a89878", EARTH = "#8a7a6a";
  const at = (c, x, y, k, fn, rot = 0) => { c.save(); c.translate(x, y); c.rotate(rot); c.scale(k, k); fn(c); c.restore(); };
  const st = (c, col, w, fn, cap = "round") => { c.beginPath(); fn(c); c.strokeStyle = col; c.lineWidth = w; c.lineCap = cap; c.lineJoin = "round"; c.stroke(); };
  /** HUD「移動」的褐色靴子（風格樣張 Q.ART.hud.move，48 格；纏繞、條件「移動過」用的同一隻），k 倍、靴子中心挪到 (dx, dy)。 */
  const boot = (c, o, dx, dy, k) => at(c, dx, dy, k, (q) => { q.translate(-27, -24); Q.ART.hud.move.d(q, o); });

  /** 方案 A：靴子踩地。HUD「移動」的靴子（不帶速度線）踩在兩道地面線上（上面一道寬的沙色、下面一道短的暗土色），靴底兩邊各一道往外斜的短「踏穩」線（≤14px 省掉）。 */
  const bootPlanted = (c, o) => {
    rr(c, SAND, -10.6, 5.2, 21.2, 3, 1.5); rr(c, SAND_D, -7.4, 9, 14.8, 1.8, 0.9);
    boot(c, o, -0.2, -2.8, 0.4);
    if (!o.tiny) for (const s of [-1, 1]) ln(c, CREAM, 1.6, [[s * 8.2, 3.4], [s * 10.2, 0.6]]);
  };
  /** 方案 B：張腳站穩的人形。米白人形（≤24px 單色剪影，規則 9）兩腳張開成「人」字、雙手叉腰，腳踩一道沙色地面線（v2；和「倒地」同一個人形語言：倒地＝趴平、站穩＝站直張腳）。 */
  const standWide = (c, o) => {
    rr(c, SAND, -9.8, 8.2, 19.6, 3, 1.5); /* v2（美術 PM）：地面線改方案 A 的寬沙色（同色、同粗細 3），左右比腳寬一點；第 1 版暗土色 EARTH 在深底上 20 真 1 倍看不到 */
    for (const s of [-1, 1]) { ln(c, CREAM, 3.6, [[s * 1.8, 1.6], [s * 5.6, 7.6]]); rr(c, CREAM, s > 0 ? 4.2 : -8.8, 6.6, 4.6, 2.6, 1.3); }
    for (const s of [-1, 1]) ln(c, CREAM, 2.6, [[s * 3.2, -2.6], [s * 7, -0.2], [s * 3.6, 2.2]]);
    rr(c, CREAM, -4.2, -3.8, 8.4, 6.8, 2.8);
    ci(c, CREAM, 0, -7.2, 3.6);
    if (!o.tiny) { el(c, "#ffffff", -1.2, -8.4, 1.4, 0.9, -0.6); f(c, "rgba(0,0,0,0.12)", () => c.rect(1.6, -3.4, 2.4, 6.2)); }
  };
  /** 錨（方案 C 用）：圓環、直桿、橫桿、下面一道彎臂兩端帶尖爪；金色、左半亮一階。 */
  const anchor = (c, o) => {
    st(c, GOLD, 2.4, (p) => p.arc(0, -7.6, 2.2, 0, PI * 2));
    rr(c, GOLD, -1.4, -5.6, 2.8, 14.4, 1); rr(c, GOLD, -5, -4.6, 10, 2.4, 1.2);
    st(c, GOLD, 2.8, (p) => p.arc(0, 1.4, 7.2, PI * 0.14, PI * 0.86));
    for (const s of [-1, 1]) poly(c, GOLD, [[s * 7.6, 0.4], [s * 9.6, 4.6], [s * 5, 4.4]], 0.3);
    if (!o.tiny) f(c, "#fff0b0", () => c.rect(-1.4, -5.2, 1, 13));
  };
  /** 方案 C：靴子＋小錨。靴子踩在一道沙色地面線上，右下壓一個金色小錨（自己包一圈外框）。 */
  const bootAnchor = (c, o) => {
    rr(c, SAND, -10.6, 6.4, 18.6, 3, 1.5);
    boot(c, o, -2.8, -2.2, 0.4);
    halo(c, o, (q) => at(q, 5.6, 2.4, 0.52, (p) => anchor(p, o)));
  };

  const CANDS = {
    steady_a: { key: "A", zh: "站穩・方案 A 靴子踩地", topic: "褐色靴子（同 HUD「移動」，不帶速度線）踩在兩道地面線上（寬沙色＋短暗土色），靴底兩側各一道往外斜的短踏穩線", d: bootPlanted },
    steady_b: { key: "B", zh: "站穩・方案 B 張腳站穩的人形", topic: "米白人形兩腳張開成「人」字、雙手叉腰，腳踩一道寬沙色地面線（倒地的反面：站直）", d: standWide },
    steady_c: { key: "C", zh: "站穩・方案 C 靴子＋小錨", topic: "褐色靴子踩在沙色地面線上，右下壓一個金色小錨", d: bootAnchor },
  };
  /** 推薦方案（紀錄第 3 節）：移植照這一筆。 */
  const PICK = "steady_b";
  const STEADY = { zh: "站穩", topic: CANDS[PICK].topic, d: CANDS[PICK].d };

  function install() {
    for (const [id, e] of Object.entries(CANDS)) QST.NEW[id] = { zh: e.zh, topic: e.topic, d: e.d };
    QST.NEW.steady = { ...STEADY };
  }
  return { CANDS, PICK, STEADY, install, bootPlanted, standWide, bootAnchor, anchor };
})();
