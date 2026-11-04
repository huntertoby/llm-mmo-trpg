// parts-4dir.html 其他節：種族、獸耳、衣服、護甲、披風、背掛、腰掛、頸飾、副手、鬍子睫毛（每列都是正面、背面、朝東、朝西）
(() => {
  const Q = QDoll, R = RaceArt.RACES, IT = PaperDoll.ITEMS, section = window.section;
  const BASE = { skin: "#f1c9a5", hair: "short", hairColor: "#6a3d1e" };
  const SH = (extra = {}) => ({ body: { kind: "shirt", color: "#4f7fbf" }, feet: { kind: "boots", material: "leather" }, ...extra });
  const RACE_GEAR = { body: { kind: "leather", color: "#6a5040" }, feet: { kind: "boots", material: "leather" } };
  section("3. 10 族 × 四方向（耳、角、尾、鱗、紋路、鬍子）", Object.values(R).map((r) => [r.zh, { look: r.look, gear: RACE_GEAR }]), 3.0,
    "耳朵：精靈尖耳、鱗族鰭耳側面只畫靠後的一隻；角：龍裔往後掃、角魔往上捲；尾巴：正面從腰側露、側面在身後、背面在披風上；臉部紋路與鱗片背面不畫。");
  const EARS = [["狐", "fox", "#d8762a"], ["貓", "cat", "#3a2a24"], ["狼", "wolf", "#8a8a94"], ["兔", "rabbit", "#e8e0c8"]];
  section("4. 獸耳族（原狐族，#138）：狐、貓、狼、兔耳朵與尾巴 × 四方向", EARS.map(([zh, k, hc]) => [`${zh}耳・${zh}尾`, { look: { ...R.fox.look, beastEars: k, hairColor: hc, tailColor: undefined }, gear: RACE_GEAR }]), 3.0,
    "狐：耳大而尖、內側淺色，尾巴蓬、末端白；貓：耳小三角，尾巴細長往上彎；狼：耳直立、窄、外緣深色，尾巴粗而下垂；兔：耳長而直立，尾巴是小圓球（正面被身體擋住、側面在後腰、背面在正中）。花色跟著髮色。側面兩耳一前一後，背面看不到耳朵內側。");
  section("5. 衣服前後片、腰帶與帶扣、胸前紋章", [
    ["襯衫＋腰帶扣", { look: BASE, gear: SH() }],
    ["皮甲（斜背帶）", { look: BASE, gear: SH({ body: { kind: "leather", material: "leather" } }) }],
    ["鎖甲＋紋章", { look: BASE, gear: SH({ body: { kind: "mail", material: "iron", crest: "#2f5fae" } }) }],
    ["板甲（肩甲、胸口高光）＋紋章", { look: BASE, gear: SH({ body: { kind: "plate", material: "steel", crest: "#a32a2a" } }) }],
    ["長袍（前襟）", { look: { ...BASE, trim: "#e8bb48" }, gear: SH({ body: { kind: "robe", color: "#5a3fa0" } }) }],
    ["外套（領口、扣子）", { look: BASE, gear: SH({ body: { kind: "coat", color: "#4a5058" } }) }],
  ], 3.0, "帶扣、紋章、領口、扣子、前襟只在正面；側面轉到身體前緣只露一點；背面不畫。");
  section("6. 護甲與手腳：肩甲、護腕、手套、鐵手套、靴、脛甲", [
    ["護腕＋皮靴", { look: BASE, gear: SH({ hands: { kind: "bracers", material: "leather" } }) }],
    ["手套", { look: BASE, gear: SH({ hands: IT.gloves }) }],
    ["鐵手套＋脛甲", { look: BASE, gear: SH({ body: { kind: "plate", material: "steel" }, hands: IT.gauntlets, feet: IT.greaves }) }],
  ], 3.0, "護腕套在前臂靠手腕，四方向跟著前臂；肩甲是板甲的上臂圓片；背面手被身體擋住時，護腕、手套也一起被擋。");
  section("7. 披風、斗篷", [["藍披風", { look: BASE, gear: SH({ cloak: IT.blue_cape }) }], ["紅披風＋鎖甲", { look: BASE, gear: SH({ body: { kind: "mail", material: "iron" }, cloak: IT.red_cape }) }]], 3.0,
    "正面：披風在身體後面（暗色，露在肩外與腳邊），胸前一個扣；側面：背後那一片，在最底層；背面：主色蓋住整個背與肩甲，只有頭在它上面。");
  section("8. 背掛：箭袋、背包、卷軸筒", [
    ["箭袋", { look: BASE, gear: SH({ back: { kind: "quiver", material: "leather" } }) }],
    ["背包", { look: BASE, gear: SH({ back: { kind: "backpack", material: "leather" } }) }],
    ["卷軸筒", { look: BASE, gear: SH({ back: { kind: "scroll_case", color: "#7a2a3a" } }) }],
  ], 3.0, "箭袋：右肩出口、斜背到左腰。正面只看到右肩上方露出的箭羽和胸前的斜背帶；背面整個箭袋在背上；朝東背帶從近側右肩斜過胸前；朝西右肩在遠側，只看到背後的箭袋。背包：正面兩條肩帶、背面本體、側面凸在背後。");
  section("9. 腰掛：劍鞘（左腰）、腰包（右腰）", [
    ["劍鞘", { look: BASE, gear: SH({ waist: { kind: "scabbard", material: "leather" } }) }],
    ["腰包", { look: BASE, gear: SH({ waist: { kind: "pouch", material: "leather" } }) }],
  ], 3.0, "劍鞘掛左腰：正面在畫面右、背面在畫面左；朝東左腰在遠側，劍鞘被身體和腿擋住，只露鞘尾；朝西左腰在近側，整把鞘露在外面。腰包掛右腰，左右相反。");
  section("10. 頸飾：項鍊、念珠", [["項鍊", { look: BASE, gear: SH({ neck: { kind: "necklace", material: "gold" } }) }], ["念珠", { look: BASE, gear: SH({ neck: { kind: "beads", color: "#8a5a32" } }) }]], 3.0,
    "正面墜子在胸口；側面墜子在胸前前緣；背面只看到頸後一小段。");
  section("11. 副手物品：圓盾、鳶盾、聖盾、塔盾、書", [
    ["圓盾", { look: BASE, gear: SH({ main_hand: IT.sword, off_hand: IT.round_shield }) }],
    ["鳶盾", { look: BASE, gear: SH({ main_hand: IT.sword, off_hand: IT.kite_shield }) }],
    ["聖盾", { look: BASE, gear: SH({ main_hand: IT.sword, off_hand: IT.holy_shield }) }],
    ["塔盾", { look: BASE, gear: SH({ main_hand: IT.sword, off_hand: { slot: "off_hand", kind: "shield_kite", form: "tower", material: "wood", color: "#6a4a2e" } }) }],
    ["書", { look: BASE, gear: SH({ main_hand: IT.fire_staff, off_hand: IT.tome }) }],
  ], 2.6, "左手拿：正面在畫面右；背面盾背（木板＋皮帶）在畫面左、蓋住手臂，書只露一角；朝東左手在遠側，盾舉在胸前；朝西左手在近側，盾、書在前面。主手武器朝西時在遠側。");
  section("12. 鬍子、睫毛", [
    ["大鬍子", { look: { ...BASE, beardStyle: "full" }, gear: SH() }], ["山羊鬍", { look: { ...BASE, beardStyle: "goatee" }, gear: SH() }],
    ["八字鬍", { look: { ...BASE, beardStyle: "mustache" }, gear: SH() }], ["睫毛＋大眼", { look: { ...BASE, lashes: true, eyeStyle: "big", hair: "long" }, gear: SH() }],
  ], 3.0, "鬍子、睫毛在臉上：側面只在臉前那半邊，背面不畫。");
  // 32px 頭像：獸耳四種
  const h2 = document.createElement("h2"); h2.textContent = "13. 獸耳四種的 32px／64px 頭像"; document.getElementById("secs").appendChild(h2);
  const c = document.createElement("canvas"); c.width = 1240 * 2; c.height = 110 * 2; c.style.width = "1240px"; c.style.height = "110px"; document.getElementById("secs").appendChild(c);
  const x = c.getContext("2d"); x.scale(2, 2);
  EARS.forEach(([zh, k, hc], i) => {
    for (const [s, X, Y] of [[64, 20 + i * 150, 8], [32, 96 + i * 150, 40]]) {
      const kk = s / 26; x.save(); x.translate(X, Y); x.beginPath(); x.roundRect(0, 0, s, s, 5); x.save(); x.clip(); x.fillStyle = "#3a5a3a"; x.fillRect(0, 0, s, s);
      Q.stamp(x, { look: { ...R.fox.look, beastEars: k, hairColor: hc }, gear: RACE_GEAR }, "front", s / 2, s * 0.62 + 29 * kk, kk, false, { dpr: 3 });
      x.restore(); x.lineWidth = 2; x.strokeStyle = "#6aa84a"; x.beginPath(); x.roundRect(0, 0, s, s, 5); x.stroke(); x.restore();
    }
    x.fillStyle = "#f2e6c8"; x.font = "12px 'Noto Sans TC','Microsoft JhengHei',sans-serif"; x.fillText(`${zh}耳`, 40 + i * 150, 100);
  });
  for (const [zh, rk, i] of [["龍裔", "dragonkin", 4], ["獸人", "orc", 5], ["鱗族", "scalefolk", 6], ["角魔", "fiend", 7]]) {
    for (const [s, X, Y] of [[64, 20 + i * 150, 8], [32, 96 + i * 150, 40]]) {
      const kk = s / 26; x.save(); x.translate(X, Y); x.beginPath(); x.roundRect(0, 0, s, s, 5); x.save(); x.clip(); x.fillStyle = "#2a3550"; x.fillRect(0, 0, s, s);
      Q.stamp(x, { look: R[rk].look, gear: RACE_GEAR }, "front", s / 2, s * 0.62 + 29 * kk, kk, false, { dpr: 3 });
      x.restore(); x.lineWidth = 2; x.strokeStyle = "#8ab0ff"; x.beginPath(); x.roundRect(0, 0, s, s, 5); x.stroke(); x.restore();
    }
    x.fillStyle = "#f2e6c8"; x.font = "12px 'Noto Sans TC','Microsoft JhengHei',sans-serif"; x.fillText(zh, 40 + i * 150, 100);
  }
})();
