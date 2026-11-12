// 多字「資訊面板」統一版面提案的共用元件（info-panels.html 用）。紀錄：docs/art/資訊面板版面提案.md。
// 框、按鈕、字級用現行 client/src/styles/index.css（只讀）；提案的 ip-* 排版在 infoPanels.css。
// 圖示一律呼叫已過審的 Q 版畫法（不另畫）：功能列／通用小圖 QIconsHud（第⑦批）、事件卡圖示 QIconsEvent（第⑧批）、
// 部件圖樣 QIconsParts（第④批：金鎖、鐘、增益箭頭），頭像 QPortrait（主角另組一筆示意資料），技能圖示 OB.skillIcon（現行 SkillIcon.draw）。
// 字串：照遊戲端（client/src/world/*.tsx、src/trpg/api/*_view.py、content/world/season.yaml）；提案改過的字在紀錄第 5 節的改字表，
// 頁面上用 IP.newText() 標成淡底虛線（「提案字，給玩法 PM 確認」）。
window.IP = (() => {
  const { h } = OB;
  const QH = QIconsHud, QE = QIconsEvent, QP = QIconsParts;

  // ---------------- 圖示 ----------------
  const blank = (w, hh = w) => { const c = document.createElement("canvas"); c.width = w; c.height = hh; return c; };
  /** HUD 圖示（第⑦批）；功能列那幾個不要淺色圓底（frame: none）。 */
  const hud = (id, px) => { const c = QH.canvas(id, px, 1, { frame: "none" }); c.className = "ip-ico"; return c; };
  /** 事件卡圖示（第⑧批，深底圓＋色環）。 */
  const ev = (id, px) => { const c = QE.canvas(id, px, 1); c.className = "ip-ico"; return c; };
  /** 事件卡圖示的圖樣本身（不畫深底圓與色環）：標頭、時間點釘、清單列用；px＝圖樣邊長。第 2 版（審查必修 3、可修 4、9）。 */
  function evBare(id, px) {
    const res = 2, c = blank(px * res); c.style.width = c.style.height = px + "px"; c.className = "ip-ico";
    const x = c.getContext("2d"); x.scale(res, res); const e = QE.ICON[id], size = e.grp === "badge" ? px : px / (e.fill ?? 0.84);
    QIconsWeapons.blit(x, QE.glyph(id, size, res), 0, 0, px, res); return c;
  }
  /** 部件圖樣（第④批）不帶圓片：px 是整格邊長，圖樣本身＝px × 0.75（QIconsParts.BOX）。 */
  function part(cat, id, px) {
    const res = 2, c = blank(px * res); c.style.width = c.style.height = px + "px"; c.className = "ip-ico";
    const x = c.getContext("2d"); x.scale(res, res); QP.paint(x, cat, id, px / 2, px / 2, px / QP.BOX, 1, res); return c;
  }
  const ICON = {
    lock: (px = 18) => part("skeleton", "control", px), /* 金鎖（第 3 批「控制」記號＝第④批骨架徽章） */
    clock: (px = 16) => part("card", "cooldown", px), /* 藍邊白面的鐘（第④批卡片「冷卻」） */
    up: (px = 18) => part("skeleton", "aura", px), /* 朝上的粗箭頭（第④批骨架「增益」）：未分配的屬性點 */
    warn: (px = 15) => hud("warn", px),
    info: (px = 14) => ev("info", px),
    token: (px = 15) => hud("token", px),
    bulb: (px = 15) => hud("bulb", px),
    rank: (px = 16) => hud("rank", px),
    grow: (px = 18) => hud("bar_G", px),
    book: (px = 16) => hud("bar_K", px),
    /* 第 2 版（審查必修 3）：時間軸「劇情技能」釘改用第⑧批「說書人」（攤開的書＋羽毛筆）的圖樣，和封印的紫色晶石分開剪影 */
    story: (px = 16) => evBare("narrator", px),
    scroll: (px = 20) => hud("bar_J", px),
    shadow: (px = 18) => hud("bar_Y", px),
    map: (px = 18) => hud("bar_M", px),
    town: (px = 14) => hud("town", px),
    /* 第 2 版（美術 PM 決定）：霧潮入侵的霧（HUD fog 在 13～18px 像「≡」）換題材，用事件所在區域「雲嶺」的雙峰紋章，和熔岩潰堤用荒原火焰紋章同一個邏輯 */
    ridge: (px = 16) => hud("c_cloud_ridge", px),
    fire: (px = 16) => hud("c_ashen_waste", px),
    crystal: (px = 16) => hud("r_source", px),
    hourglass: (px = 16) => hud("t_telegraph", px),
    /* 第 2 版（審查可修 9）：線軸改用不帶深底圓的圖樣本身、放大到 18～20（16px 帶環時圖樣只剩 13px，是一團紅橘） */
    thread: (px = 18) => evBare("thread", px),
    combat: (px = 24) => ev("combat", px),
    /* 第 2 版（審查可修 4）：懸賞標頭的雙劍去掉紅色粗環，只留圖樣，和其他 18px 標頭圖示同大同重 */
    swords: (px = 18) => evBare("combat", px),
    campfire: (px = 18) => evBare("b_rest", px),
    flag: (px = 18) => hud("t_orders", px),
    clue: (px = 16) => ev("clue", px),
    narrator: (px = 16) => ev("narrator", px),
  };

  // ---------------- 頭像 ----------------
  const portraitOf = (id, px) => { const c = blank(px * 2); c.style.width = c.style.height = px + "px"; const x = c.getContext("2d"); x.scale(2, 2); QPortrait.portrait(x, 0, 0, px, QPortrait.N.find((n) => n[0] === id)); return c; };
  /** 主角（示意：玩家自己的外觀不在資料表裡，照 QPortrait 的格式組一筆）。 */
  const HERO_ROW = ["hero_aa", "AA", "主角", "hero", "cloud_ridge", { skin: "#f1c9a5", hair: "long", hair_color: "#5a3a22", ears: "pointed" }, { body: { kind: "leather", color: "#2f5a5a" } }, []];
  const heroPortrait = (px) => { const c = blank(px * 2); c.style.width = c.style.height = px + "px"; const x = c.getContext("2d"); x.scale(2, 2); QPortrait.portrait(x, 0, 0, px, HERO_ROW); return c; };

  // ---------------- 小元件 ----------------
  /** 提案改過的字（給玩法 PM 確認）：頁面上加淡底虛線，紀錄第 5 節有原字。 */
  const newText = (t) => h("span.ip-new", { title: "提案字（給玩法 PM 確認）" }, t);
  const chip = (icon, label, value, opt = {}) => h("span.ip-chip", { class: opt.zero ? "zero" : null }, icon, label, value != null ? h("b", {}, String(value)) : null);
  const tag = (cls, ...kids) => h("span.ip-tag", { class: cls || null }, ...kids);
  /** (i) 說明鈕；open＝樣張上把說明卡畫出來（遊戲裡是 Hint 滑過才出現）。 */
  const tip = (text, opt = {}) => h("span.ip-tip", { tabindex: "0", "aria-label": typeof text === "string" ? text : null }, opt.icon ?? ICON.info(14),
    opt.open ? h("div.ip-tipcard", { class: (opt.place ?? "below") + (opt.right ? " right-edge" : "") }, text) : null);
  const callout = (tone, icon, main, opt = {}) => h("div.ip-callout", { class: tone }, icon, h("div.body", {}, main, opt.sub ? h("span.sub", {}, opt.sub) : null), opt.end ? h("span.end", {}, opt.end) : null);
  const sec = (icon, title, opt = {}, ...kids) => h("section.ip-sec", { class: opt.first ? "first" : null },
    h("div.ip-sec-head", {}, icon, h("span.ip-sec-title", {}, title), opt.meta ? h("span.ip-sec-meta", {}, opt.meta) : null, opt.right ? h("span.ip-sec-right", {}, opt.right) : null), ...kids);
  const head = (title, opt = {}) => h("div.ip-head", {}, h("h2.ip-title", {}, opt.icon ?? null, title), h("span.ip-head-actions", {}, opt.back === false ? null : h("button", { type: "button" }, "回到地點圖"), h("button.ip-x", { type: "button", "aria-label": "關閉" }, "×")));
  /** 面板外殼：現行 world-hud-panel 的框（ui-popup rt-frame），樣張裡改成 inline。 */
  const panel = (cls, ...kids) => h("div.ui-popup.rt-frame.ui-popup-inline.ip-panel", { class: cls || null }, h("div.ui-popup-body", {}, ...kids));
  const fold = (summary, end, open, ...body) => h("details.ip-fold", { open: open ? true : null }, h("summary", {}, summary, end ? h("span.end", {}, end) : null), h("div.ip-fold-body", {}, ...body));
  const prog = (n, d) => h("span.ip-prog", {}, h("span.ip-mini", {}, h("i", { style: `width:${Math.round((100 * n) / d)}%` })), `${n}／${d}`);

  // =====================================================================
  // 公告板（BoardPanel.tsx；資料 src/trpg/api/season_view.py＋content/world/season.yaml）
  // =====================================================================
  const SEASON = {
    day: 1, days: 14, refresh: "每天 06:00 刷新",
    phases: [[1, 3, "霧中裂痕", "主線第 1～2 章、雲嶺；世界事件「霧潮入侵」"], [4, 7, "灰燼之心", "灰燼荒原、懸賞；世界事件「熔岩潰堤」"], [8, 10, "封印", "封印鑰匙集滿即解鎖頭目（最早第 8 天、第 10 天強制）"], [11, 13, "頭目競賽", "首殺者得獎金；第 13 天截止影子循環賽報名"], [14, 14, "季末", "無人首殺時舉行影子循環賽"]],
    // milestones（season.yaml）：天、名稱、圖示
    marks: [[2, "主線第 1 章的劇情技能", ["book"]], [6, "主線第 2 章的劇情技能", ["book"]], [8, "賽季頭目最早解鎖", ["lock"]], [10, "賽季頭目強制解鎖；主線第 3 章的劇情技能", ["lock", "book"]], [13, "影子循環賽截止報名", ["shadow"]], [14, "影子循環賽", ["shadow"]]],
    events: [[1, 3, "霧潮入侵", "ridge", 1], [4, 7, "熔岩潰堤", "fire", 1], [7, 10, "封印共鳴", "crystal", 2]],
  };
  const MARK_ICON = { book: () => ICON.story(16), lock: () => ICON.lock(16), shadow: () => ICON.shadow(15) };

  function timeline(opt = {}) {
    const S = SEASON, kids = [];
    const cell = (col, row, el) => { el.style.gridColumn = typeof col === "number" ? String(col + 1) : col; el.style.gridRow = String(row); return el; };
    // 第 1 列：時間點（圖示釘；滑過說明卡寫名稱）
    kids.push(cell(0, 1, h("span.ip-tl-lab", {}, "時間點")));
    for (const [d, name, icons] of S.marks) {
      const next = S.marks.find((m) => m[0] > S.day)?.[0] === d;
      const open = opt.openMark === d;
      kids.push(cell(d, 1, h("span.ip-tl-mk", {}, h("span.ip-tl-pin", { class: next ? "next" : null, title: `第 ${d} 天 ${name}`, tabindex: "0" }, icons.map((k) => MARK_ICON[k]())),
        open ? h("div.ip-tipcard.above", { style: "left:-40px" }, h("b", {}, `第 ${d} 天`), "　" + name) : null)));
    }
    // 第 2 列：日（今天亮金）
    kids.push(cell(0, 2, h("span.ip-tl-lab", {}, "天")));
    for (let d = 1; d <= S.days; d++) kids.push(cell(d, 2, h("span.ip-tl-day", { class: d === S.day ? "today" : null }, String(d))));
    // 第 3 列：階段
    kids.push(cell(0, 3, h("span.ip-tl-lab", {}, "階段")));
    S.phases.forEach(([a, b, name], i) => kids.push(cell(`${a + 1} / ${b + 2}`, 3, h("span.ip-tl-seg", { class: (a <= S.day && S.day <= b ? "now " : "") + (i % 2 ? "c2" : ""), title: name }, name))));
    // 第 4、5 列：世界事件（封印共鳴第 7 天和熔岩潰堤重疊，排第二列）
    kids.push(cell(0, "4 / 6", h("span.ip-tl-lab", {}, "世界事件")));
    for (const [a, b, name, icon, row] of S.events) kids.push(cell(`${a + 1} / ${b + 2}`, 3 + row, h("span.ip-tl-ev", { class: a <= S.day && S.day <= b ? "now" : null }, ICON[icon](13), name)));
    const tl = h("div.ip-tl", { role: "img", "aria-label": "賽季時程" }, kids);
    tl.firstChild.style.gridRow = "1";
    return tl;
  }

  function boardProposal(opt = {}) {
    const S = SEASON, now = S.phases.find((p) => p[0] <= S.day && S.day <= p[1]), nextMark = S.marks.find((m) => m[0] > S.day);
    const goals = [["完成新手任務 2 步", 0, 2], ["發現 1 個隱藏地點", 0, 1], ["打倒 1 隻精英", 0, 1]];
    const bounties = [["北坡狼王", "北坡獵場", 5, 3, "懸賞中"], ["霧中劍客", "劍冢", 5, 3, "懸賞中"], ["斷崖幫二當家「疤面」", "斷崖幫寨", 4, 3, "懸賞中"]];
    const el = panel("ip-board",
      head("公告板"),
      h("div.ip-speaker", {}, portraitOf("seal_keeper", 48), h("div.ip-bubble", {}, h("span.who", {}, "守印人"), "封印和懸賞的消息，都貼在板上了。")),

      sec(ICON.hourglass(18), "賽季時程", { right: [ICON.clock(16), S.refresh] },
        /* 第 2 版（審查可修 8）：兩欄格子——左欄大字「第 1 天」，右欄第 1 行階段標籤、第 2 行說明（同一條左緣）；第 1 行兩欄對齊基線 */
        h("div.ip-season-top", {},
          h("span.ip-dayno", {}, "第", h("b", {}, String(S.day)), "天", h("span", { style: "color:var(--ip-l3)" }, `／共 ${S.days} 天`)),
          h("span.ip-phase-nm", {}, tag("open", now[2]), `第 ${now[0]}～${now[1]} 天`),
          h("span.ip-l2.ip-phase-desc", {}, now[3])),
        timeline(opt),
        h("div.ip-next", {}, h("span.k", {}, "下一個"), tag("", `第 ${nextMark[0]} 天`), h("b", {}, nextMark[1]), h("span.ip-l3", {}, newText("（明天）"))),
        fold(h("span", {}, h("b", {}, "完整日程"), `（${S.marks.length} 個時間點、${S.phases.length} 個階段）`), null, !!opt.openSched,
          h("ul.ip-sched", {}, S.marks.flatMap(([d, name]) => [h("li.d", {}, `第 ${d} 天`), h("li", {}, name)])))),

      sec(ICON.clue(18), "今日目標", { meta: tag("info", "新手期：教學目標"), right: [newText("完成一條"), ICON.token(15), h("b", { style: "color:var(--ip-num)" }, "+1")] },
        h("div.ip-rows", {}, goals.map(([t, n, d]) => h("div.ip-row.ip-goal", {}, h("span.ip-check", { class: n >= d ? "done" : null }), h("span.text", {}, t), prog(n, d))))),

      sec(ICON.swords(18), "懸賞板", { meta: newText("先搶先贏"), right: [ICON.clock(15), "每天 06:00 換一批", tip("先打倒的人拿走當天的懸賞（每天 06:00 刷新）。", { open: opt.openBountyTip, place: "below", right: true })] },
        /* 第 2 版（審查可修 5）：欄寬只寫在 CSS 的 .ip-bounty-cols（欄名列與每列共用），窄版媒體查詢才蓋得掉；可修 2：等級一行「Lv 5」 */
        h("div.ip-cols-head.ip-bounty-cols", {}, h("span"), h("span", {}, "目標・地點"), h("span", {}, "建議等級"), h("span.reward-h", {}, "獎勵"), h("span", { style: "text-align:right" }, "狀態")),
        h("div.ip-rows", {}, bounties.map(([n, where, lv, coins, st]) => h("div.ip-row.ip-bounty.ip-bounty-cols", {},
          ICON.combat(24), h("span.stack", {}, h("span.name", {}, n), h("span.where", {}, ICON.town(14), where)),
          h("span.lv", {}, "Lv ", h("b", {}, String(lv))), h("span.reward", {}, ICON.token(15), String(coins)), h("span.state", {}, tag("open", st)))))),

      sec(ICON.map(18), "世界事件", { meta: newText("全服一起推進") },
        h("div.ip-event", {},
          h("div.ip-event-head", {}, ICON.ridge(18), h("span.name", {}, "霧潮入侵"), tag("", "第 1～3 天"), h("span.end", {}, tag("live", "進行中"))),
          h("div.ip-l2", {}, "全服在雲嶺的霧中打贏戰鬥；成功則開放灰燼荒原"),
          h("div.ip-bar", {}, h("span.ip-bar-track", {}, h("i", { style: "width:0%" })), h("span.ip-bar-num", {}, h("b", {}, "0"), "／30"),
            tip(h("span", {}, h("b", {}, "門檻"), "：沒有前一天的上線紀錄，用原門檻"), { open: opt.openEventTip, place: "above", right: true }))),
        h("div.ip-event.pending", {},
          h("div.ip-event-head", {}, ICON.fire(18), h("span.name", {}, "熔岩潰堤"), tag("", "第 4～7 天"), h("span.end", {}, tag("dim", "尚未開始"))),
          h("div.ip-l2", {}, "全服在赤沙村、灰井村、鐵爐村打贏守點戰；成功則熔心坑提早開放、封印鑰匙 +5"),
          h("div.ip-bar", {}, h("span.ip-bar-track", {}, h("i", { style: "width:0%" })), h("span.ip-bar-num", {}, h("b", {}, "0"), "／24")))),

      sec(ICON.lock(18), "賽季頭目", { meta: h("b", { style: "color:var(--ui-text)" }, "碎晶之主"), right: tag("lock", ICON.lock(14), "封印中") },
        h("div.ip-l2", {}, "11 月 10 日 06:00 解鎖"),
        h("div.ip-bar", {}, ICON.crystal(16), h("span.ip-l2", {}, "封印鑰匙"), h("span.ip-bar-track", {}, h("i", { style: "width:0%" })), h("span.ip-bar-num", {}, "全服 ", h("b", {}, "0"), " 把・你有 ", h("b", {}, "0"), " 把（需要 1 把）")),
        fold(h("span", {}, h("b", {}, "挑戰規則與評分榜")), tag("dim", "還沒有人打倒"), false, h("div.ip-l2", {}, "今天還剩 3／3 次（算帳號）；只准系統傭兵，失敗只扣次數。"))));
    OB.applyTheme("capital", el); /* 公告板在主城（使用者截圖的四角是主城的金邊紫菱） */
    return el;
  }

  // =====================================================================
  // 成長與技能（WorldGrowth.tsx；字串 src/trpg/api/world_growth_view.py、world/opening.py、opening_limits.py）
  // =====================================================================
  function growthProposal(opt = {}) {
    return panel("ip-growth",
      head("成長與技能"),
      h("div.ip-chips", {}, chip(ICON.grow(16), "Lv", 2), chip(ICON.rank(16), "角色階級", 1), chip(ICON.bulb(15), "靈感點", 3), chip(ICON.up(16), "未分配屬性點", 0, { zero: true })),
      callout("warn", ICON.warn(15), h("span", {}, h("b", {}, "現在不行"), "：這裡不是城鎮或營火"),
        { sub: "閃現、重閃、溶掉、傳承、重配屬性、立誓只在城鎮與營火（和換技能同一處）。" }),
      callout("info", ICON.info(14), "入門期可以自己配點，正式選定時會照新武器重配一次。"),
      h("div.ip-locks", {}, h("div.ip-locks-head", {}, ICON.lock(18), newText("入門期還沒開放")),
        h("ul", {}, [["閃現", "到 4 級"], ["溶掉、傳承", "4 級起"], ["立誓", "找葛蘭正式選定後"]].map(([a, b]) => h("li", {}, h("b", {}, a), h("span", {}, newText(b)))))),

      /* 第 2 版（審查可修 3）：沒有圖示的區塊標頭補圖——外觀與種族＝主角頭像（QPortrait，和 HUD 主角卡同一種畫法） */
      sec(heroPortrait(20), "外觀與種族", {},
        h("div.ip-rows", {},
          h("div.ip-row.ip-set", {}, h("span.lbl", {}, h("span.ip-l1", {}, "外觀")), h("span.ctl", {}, tag("lock", ICON.lock(14), "只有在主城能改外觀"), h("button", { type: "button", disabled: true }, "改外觀"))),
          h("div.ip-row.ip-set", {}, h("span.lbl", {}, h("span.ip-l1", {}, "種族"), h("span.ip-l3", {}, "本季可以免費換一次")),
            h("span.ctl", {}, tag("lock", ICON.lock(14), newText("正式選定後才能換")), h("select", { disabled: true, "aria-label": "新種族" }, h("option", {}, "精靈")), h("button", { type: "button", disabled: true }, "換種族"))))),

      sec(ICON.up(18), "屬性點", { right: tag("dim", "升級時每級 +2") },
        h("div.ip-empty", {}, "沒有未分配的屬性點。")),

      /* 第 2 版（審查可修 9）：靈感點只留標頭的籌碼，這裡不再重複 */
      sec(ICON.bulb(18), "靈感閃現", {},
        h("div.ip-rule-chips", {},
          h("span.ip-rule", {}, ICON.bulb(14), h("b", {}, "1 點"), "4 個變化選 1"),
          h("span.ip-rule", {}, ICON.bulb(14), h("b", {}, "+1 點"), "指定類別、該類 3 選 1"),
          h("span.ip-rule", {}, ICON.book(14), "每招最多閃 ", h("b", {}, "5"), " 次"),
          tip(h("span", {}, "出題就會扣點，一定要選一個。", h("br"), "要先在戰鬥中用過才能再閃。"), { open: opt.openFlashTip, place: "below", right: true })),
        h("div.ip-rows", {}, [["skill_wild_blade", "狂野之刃", "已閃 0／5 次"], ["skill_shadow_backstab", "瞬步背刺", "已閃 0／5 次"]].map(([id, n, c]) => h("div.ip-row.ip-skill", {},
          OB.skillIcon(id, 32), h("span", {}, h("span.name", {}, n), h("span.ip-l3", { style: "display:block" }, c)),
          tag("lock", ICON.lock(14), newText("到 4 級")), h("button", { type: "button", disabled: true }, "閃現"))))),

      sec(ICON.campfire(18), "重閃、溶掉與傳承、誓約", { meta: "只在城鎮與營火" }, /* 營火（第⑧批事件插圖小牌的營火）＝只在城鎮與營火做的整備 */
        fold(h("span", {}, h("b", {}, "重閃"), "　把以前的一次變化換掉"), tag("dim", newText("還沒有可以重閃的技能")), false),
        fold(h("span", {}, h("b", {}, "溶掉或傳承"), "　二選一，舊技能會消失"), tag("lock", ICON.lock(14), "4 級起"), false),
        fold(h("span", {}, h("b", {}, "誓約"), "　同時 1 個，一直有效到自己解除"), tag("lock", ICON.lock(14), newText("正式選定後")), false)));
  }

  // =====================================================================
  // 任務與線頭（QuestLog.tsx）
  // =====================================================================
  function questsProposal() {
    const steps = [["done", "渡口石階", "趕走搶渡船的盜賊"], ["current", "竹林小徑", "突破雨裡包圍的霧狼"], ["todo", "雨中梯田", "平息盜賊和修士的衝突"]];
    return panel("ip-quests",
      head("任務與線頭"),
      sec(ICON.scroll(18), "任務日誌", { first: true, right: tag("", "進行中 1") },
        h("div.ip-quest", {},
          h("div.ip-quest-head", {}, h("span.name", {}, "霧渡新手路"), tag("open", "新手"), h("span.ip-giver", {}, portraitOf("granny_du", 22), "渡婆婆")),
          h("div.ip-l2", { style: "margin-top:2px" }, "渡婆婆要你先把渡口到梯田這一路走通。"),
          h("span.ip-route", {}, ICON.map(18), "往北邊的出口 → 竹林小徑"),
          h("ol.ip-steps", {}, steps.map(([st, place, what], i) => h("li", { class: st }, h("span.ip-dot", {}, st === "done" ? "✓" : st === "todo" ? String(i + 1) : null), h("span.place", {}, newText(place)), h("span.what", {}, what)))))),
      sec(ICON.thread(18), "線頭", { right: tip("事件的結果會留下線頭（每人約 5 條，約 3 天到期）。", {}) },
        h("div.ip-rows", {}, [["商人欠你人情", "2 天 23 小時"], ["狼群是被趕下山的", "2 天 23 小時"]].map(([t, left]) => h("div.ip-row.ip-thread", {}, ICON.thread(18), h("span.name", {}, t),
          h("span.end", {}, tag("", "個人"), tag("", ICON.clock(14), newText(left))))))));
  }

  // =====================================================================
  // 隊伍／我的影子（PartyPanel.tsx；src/trpg/api/world_party_view.py、world/opening.py）
  // =====================================================================
  function partyProposal() {
    const member = (cls, face, name, lv, role, ai, extra) => h("div.ip-member", { class: cls }, face, h("div.info", {}, h("span.nm", {}, name, h("span.lvl", {}, `Lv ${lv}`), extra), h("span.role", {}, role), ai ? h("span.ai", {}, "打法 ", h("b", {}, ai)) : null));
    return panel("ip-party",
      head("隊伍"), /* 第 2 版（審查必修 4、美術 PM 決定）：四個面板右上一致放「回到地點圖」「×」 */
      sec(ICON.flag(18), "隊友", { first: true, meta: chip(null, "", "3／3"), right: [newText("主角＋最多 2 名")] },
        h("div.ip-members", {},
          member("hero", heroPortrait(44), "AA", 2, "主角"),
          member("", portraitOf("merc_tiebi", 44), "賽倫", 2, "盾衛・守護", "預設（守衛）"),
          member("comp", portraitOf("hunter_ayue", 44), "阿岳", 2, "獵戶", "預設（弓手）", tag("live", "劇情夥伴"))),
        callout("info", ICON.info(14), h("span", {}, h("b", {}, "阿岳"), "（霧渡新手路）跟著你，佔 1 個隊友位；任務結束後離隊")),
        callout("lock", ICON.lock(18), h("span", {}, h("b", {}, "換隊友"), "：入門期隊友固定，找葛蘭正式選定後才能雇用其他傭兵"))),
      sec(ICON.shadow(20), "我的影子", { right: tag("warn", ICON.warn(13), "還沒存") },
        h("div.ip-l3", { style: "margin:-4px 0 6px" }, "在城鎮休息、換技能等整備時自動存"),
        h("div.ip-shadow", {},
          h("div.ip-stat", {}, h("span.k", {}, "預設打法"), h("span.v", {}, "預設")),
          h("div.ip-stat", {}, h("span.k", {}, "被借用得到的任務幣"), h("span.v", {}, ICON.token(15), h("b", { style: "color:var(--ip-num)" }, "0")))),
        h("div.ip-empty", {}, "還沒有人借過你的影子。")));
  }

  // =====================================================================
  // 事件卡選項列（EventCard.tsx 的 world-event-solutions；world.css 378 行）
  // =====================================================================
  // 解法種類 → 圖示（narration.ts 的 solutionIcon；情境判定照 note 的方法字）
  /** 一個選項：[圖示 id, 按鈕上的字（solutionLine）, 種類 kind, kind_zh, 屬性（AttrIcon）, 交涉的補給代價]；次行的種類、屬性、代價現行只在說明卡（solutionLabel）。
   8 個那一組是第⑧批樣張頁的示意字（q-icons-event.html 情境圖，一種圖示一個），屬性是示意。 */
  const OPT8 = [["combat", "拔刀迎戰", "combat", "戰鬥"], ["persuade", "亮出商隊旗號，談條件", "situation", "情境判定", "wil"], ["sneak", "繞進竹林避開", "situation", "情境判定", "dex"], ["investigate", "先看清他們的人數", "situation", "情境判定", "wis"],
    ["force", "衝過去撞開路障", "situation", "情境判定", "str"], ["chance", "賭一把，丟下貨物引開", "opportunity", "機遇"], ["trade", "花錢買路", "parley", "交涉", null, 1], ["leave", "掉頭離開", "abandon", "放棄"]];
  /** 實際的事件（content/world/events/cloud_ridge.yaml gang_toll）：戰鬥／威嚇（意志）／付錢（1 補給）。 */
  const OPT_TOLL = [["combat", "戰鬥", "combat", "戰鬥"], ["persuade", "威嚇", "situation", "情境判定", "wil"], ["trade", "付錢", "parley", "交涉", null, 1]];
  /** bear_den：戰鬥／悄悄退出（情境判定）／放棄。 */
  const OPT_BEAR = [["combat", "戰鬥", "combat", "戰鬥"], ["sneak", "悄悄退出", "situation", "情境判定", "dex"], ["leave", "放棄", "abandon", "放棄"]];
  /* 第 2 版（審查必修 2）：實際的 1、2、3 個選項各挑一個真的骨架（content/world/events/*.yaml；字照 solutionLine：戰鬥、放棄顯示 kind_zh，其他顯示 note_zh）。 */
  /** 1 個：scarface_revenge（灰燼荒原・熔爐督工營，疤面的報仇）：只有戰鬥。 */
  const OPT_SCAR = [["combat", "戰鬥", "combat", "戰鬥"]];
  /** 1 個＋放棄：forge_smith（鐵爐村的鐵匠）：交材料（付 2 補給）／放棄。 */
  const OPT_FORGE = [["trade", "交材料（用補給代替黑曜片）", "parley", "交涉", null, 2], ["leave", "放棄", "abandon", "放棄"]];
  /** 2 個：fox_traveler（北坡獵場，獸耳族旅人）：換補給（付 1 補給）／說服（意志）；第二個是內容裡最長的主字，用來畫截斷。 */
  const OPT_FOX = [["trade", "換補給", "parley", "交涉", null, 1], ["persuade", "說服（獸耳族主角有專屬對話選項，不加數值，#138）", "situation", "情境判定", "wil"]];
  /** 1 個＋放棄、兩個屬性：cliff_lingzhi（藥師谷，崖上的靈芝）：攀爬（力量／敏捷）／放棄。 */
  const OPT_CLIFF = [["force", "攀爬", "situation", "情境判定", ["str", "dex"]], ["leave", "放棄", "abandon", "放棄"]];
  const ATTR_ZH = { str: "力量", dex: "敏捷", con: "體質", int: "智力", wis: "感知", wil: "意志" };
  const GROUP = { combat: "動手", force: "動手", persuade: "交涉", trade: "交涉", investigate: "查探", sneak: "迴避", chance: "其他", leave: "迴避" };

  /** 現行：flex-wrap 的一排按鈕（world-event-solutions），按鈕＝24px 圖示＋字。 */
  const solBtn = ([icon, text], cls = "") => h("button.world-solution", { type: "button", class: cls || null }, ev(icon, 24), h("span.world-solution-line", {}, text));
  const solCurrent = (opts) => h("div.world-event-solutions", {}, opts.map((o) => h("span.world-solution-group", {}, solBtn(o))));
  /** 選項格（案 A／推薦）：等寬兩欄，圖示＋主字（最多兩行）＋次行（種類・屬性或代價）。
   第 2 版（審查可修 6）：次行的屬性寫「圖＋名」（意志的火焰單看會讀成火屬性）；兩個屬性時用「／」分開。 */
  const sub = ([, , , kz, attr, cost]) => {
    const attrs = attr ? (Array.isArray(attr) ? attr : [attr]) : [];
    return h("span.s", {}, kz, attrs.length ? h("span.sep", {}, "・") : null,
      attrs.flatMap((a, i) => [i ? h("span.sep", {}, "／") : null, h("span.attr", {}, ev(a, 14), ATTR_ZH[a])]), cost ? h("span.cost", {}, `−${cost} 補給`) : null);
  };
  /** 主字的斷行（第 2 版，審查必修 1）：用 Intl.Segmenter 把字切成詞，詞與詞之間插 <wbr>，CSS 用 word-break: keep-all——只在詞間或標點後換行，不會斷成「談／條件」。
   遊戲端可以照搬（Chrome、Edge、Safari、Firefox 都有 Intl.Segmenter）；最多兩行，超過的第二行尾端「…」，全文在說明卡（title 與 Hint）。 */
  const SEG = typeof Intl !== "undefined" && Intl.Segmenter ? new Intl.Segmenter("zh-Hant", { granularity: "word" }) : null;
  /* 有標點（，、（）時不插斷點：keep-all 本來就只在標點後換行（「亮出商隊旗號，／談條件」）；沒有標點的才在詞間插 <wbr>，
     單字的詞（「談」「丟」這類動詞）併進下一個詞，免得斷成「談／條件」。一個詞比一行還長時 overflow-wrap: anywhere 才任意斷。 */
  const PUNCT = /[，、；：（）「」。！？]/;
  function wordBreaks(text) {
    if (!SEG || PUNCT.test(text)) return [text];
    const words = [];
    let carry = "";
    for (const { segment } of SEG.segment(text)) { if ([...segment].length === 1) carry += segment; else { words.push(carry + segment); carry = ""; } }
    if (carry) words.length ? (words[words.length - 1] += carry) : words.push(carry);
    return words.flatMap((w, i) => (i ? [h("wbr"), w] : [w]));
  }
  const tile = (o, opt = {}) => h("button.ip-sol", { type: "button", class: opt.cls || null, title: o[1] }, ev(o[0], opt.px ?? 24),
    h("span.t", {}, h("span.m", {}, wordBreaks(o[1])), opt.noSub || o[1] === o[3] ? null : sub(o)), opt.tip ? h("div.ip-tipcard.above.right-edge", { style: "right:0;max-width:250px" }, h("b", {}, `${o[3]}：`), o[1], o[4] ? `（${[].concat(o[4]).map((a) => ATTR_ZH[a]).join("／")}）` : "") : null);
  /** 第 2 版（審查必修 2）：剩一格（1 個選項，或 3 個時的第 3 格）撐滿整列——CSS 的 .ip-sol:last-child:nth-child(odd)，不用另外判斷。opt.tipAt：把第 N 格的說明卡畫出來。 */
  function solGrid(opts, opt = {}) {
    const main = opt.splitLeave ? opts.filter((o) => o[2] !== "abandon") : opts, leave = opt.splitLeave ? opts.filter((o) => o[2] === "abandon") : [];
    return h("div.ip-sols-wrap", {}, h("div.ip-sol-grid", {}, main.map((o, i) => tile(o, { tip: opt.tipAt === i }))),
      leave.length ? h("div.ip-sol-foot", {}, leave.map(([icon, text]) => h("button.ip-sol-leave", { type: "button" }, ev(icon, 18), text))) : null);
  }
  /** 案 B：依類型分組（動手／交涉／查探／迴避），每組一行小標＋一排按鈕。 */
  function solGroups(opts) {
    const order = ["動手", "交涉", "查探", "迴避", "其他"], by = {};
    for (const o of opts) (by[GROUP[o[0]]] ??= []).push(o);
    return h("div.ip-sol-groups", {}, order.filter((g) => by[g]).map((g) => h("div.ip-sol-g", {}, h("span.gl", {}, g), h("div.gb", {}, by[g].map((o) => solBtn(o, "ip-solbtn"))))));
  }
  /** 案 C：主次分開：主要（戰鬥、情境判定、機遇）大格，交涉、放棄在下面一排小鈕。 */
  function solPrimary(opts) {
    const big = opts.filter((o) => o[2] === "combat" || o[2] === "situation" || o[2] === "opportunity"), small = opts.filter((o) => !big.includes(o));
    return h("div.ip-sols-wrap", {}, h("div.ip-sol-grid", {}, big.map((o) => tile(o))), small.length ? h("div.ip-sol-small", {}, small.map(([icon, text]) => h("button.ip-sol-leave", { type: "button" }, ev(icon, 18), text))) : null);
  }

  return { ICON, hud, ev, part, portraitOf, heroPortrait, HERO_ROW, newText, chip, tag, tip, callout, sec, head, panel, fold, prog, timeline, boardProposal, growthProposal, questsProposal, partyProposal, OPT8, OPT_TOLL, OPT_BEAR, OPT_SCAR, OPT_FORGE, OPT_FOX, OPT_CLIFF, solCurrent, solGrid, solGroups, solPrimary, tile };
})();
