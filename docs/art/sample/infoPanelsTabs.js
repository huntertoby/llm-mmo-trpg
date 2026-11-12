// 資訊面板第 3 版（11-12）：視窗內容超過一屏就拆成可點的標頭（使用者：「視窗很長 會不好閱讀的問題 希望改成各自標頭點擊的方式」）。
// 成長與技能、公告板各畫三種並排：(a) 第 2 版一路往下捲、(b) 上方分頁（推薦：分頁＋分頁內摺疊）、(c) 手風琴（一次開一個）；
// 任務與線頭、隊伍用推薦案各畫一張。紀錄：docs/art/資訊面板版面提案.md 第 11 節。
// 面板大小照遊戲端：client/src/world/hud.ts popupBox(layout, 720)——1600×900 → 寬 720、高 700；800×600 → 寬 514、高 477（左右讓出 HUD 兩欄）。
// 元件全部沿用 infoPanels.js（IP.*）；圖示一律呼叫前批 Q 版畫法，不另畫。字串照第 10 節玩法 PM 確認的版本；新字用 IP.newText 標虛線。
window.IPT = (() => {
  const { h } = OB;
  const { ICON, sec, callout, tag, chip, tip, fold, head, newText, prog, portraitOf, heroPortrait } = IP;
  const BOX = { 1600: { w: 720, h: 700, zh: "1600×900" }, 800: { w: 514, h: 477, zh: "800×600" } };
  /** 賽季頭目分頁的圖示：第⑧批事件插圖小牌「源晶」（碎晶之主；圖樣本身，不帶深底圓）。 */
  const portal = (px) => {
    const res = 2, c = document.createElement("canvas"); c.width = c.height = px * res; c.style.width = c.style.height = px + "px"; c.className = "ip-ico";
    const x = c.getContext("2d"); x.scale(res, res); QIconsWeapons.blit(x, QIconsEvent.glyph("b_portal", px, res), 0, 0, px, res); return c;
  };

  // ---------------- 一屏（固定大小的面板）與量測 ----------------
  const SCREENS = [];
  /** vw＝1600｜800；fixed＝固定區（不捲）的子元素，null＝沒有固定區（第 2 版：標頭跟著捲）；opt.scrollTo(body)→要捲到的元素；opt.keys＝[[名稱, 找元素的函式]]；opt.theme。 */
  function screen(vw, fixed, kids, opt = {}) {
    const box = BOX[vw];
    const body = h("div.ui-popup-body", {}, kids);
    const fx = fixed ? h("div.ip-fixed", {}, fixed) : null;
    const panel = h("div.ui-popup.rt-frame.ui-popup-hud.world-hud-panel.ip-hudpanel", { "data-popup": "hud" }, fx, body);
    OB.applyTheme(opt.theme ?? "cloud_ridge", panel);
    const rail = h("div.ip-rail", {}, h("i"));
    const wrap = h("div.ip-screen", { style: `width:${box.w}px;height:${box.h}px` }, panel, rail);
    const meter = h("div.ip-meter");
    SCREENS.push({ body, rail, wrap, meter, fx, opt });
    return [wrap, meter];
  }
  const offsetIn = (body, el) => el.getBoundingClientRect().top - body.getBoundingClientRect().top + body.scrollTop;
  /** 分頁列放不下就一級一級縮：1 其他分頁換兩字短名、2 其他分頁只剩圖示、3 目前分頁也換短名、4 全部只剩圖示、5 折成兩列（絕不藏分頁）。 */
  function fitTabs(bar) {
    for (const lv of [0, 1, 2, 3, 4]) {
      bar.classList.remove("fit1", "fit2", "fit3", "fit4", "fit5");
      if (lv) bar.classList.add("fit" + lv);
      if (bar.scrollWidth <= bar.clientWidth + 1) return lv;
    }
    bar.classList.replace("fit4", "fit5");
    return 5;
  }
  function finish() {
    for (const bar of document.querySelectorAll(".ip-tabbar")) {
      const lv = fitTabs(bar);
      bar.dataset.fit = String(lv);
    }
    for (const s of SCREENS) {
      const { body, rail, wrap, meter, fx, opt } = s;
      const over0 = body.scrollHeight > body.clientHeight + 1;
      body.dataset.overflow = over0 ? "1" : "0";
      const ch = body.clientHeight, sh = body.scrollHeight;
      const keys = (opt.keys ?? []).map(([name, find]) => { const el = find(body); return el ? [name, offsetIn(body, el)] : null; }).filter(Boolean);
      if (opt.scrollTo) {
        const el = opt.scrollTo(body);
        if (el) body.scrollTop = Math.max(0, offsetIn(body, el) - 8);
        body.dataset.scrolled = body.scrollTop > 0 ? "1" : "0";
        if (body.scrollTop + ch >= sh - 1) body.dataset.end = "1";
      }
      if (over0) {
        const wr = wrap.getBoundingClientRect(), br = body.getBoundingClientRect();
        const th = Math.max(24, (br.height * ch) / sh), tt = ((br.height - th) * body.scrollTop) / Math.max(1, sh - ch);
        rail.style.display = "block"; rail.style.top = br.top - wr.top + "px"; rail.style.height = br.height + "px";
        rail.firstChild.style.cssText = `top:${tt}px;height:${th}px`;
      }
      /* 放得下時 scrollHeight＝可視高度，改量最後一個子元素的下緣 */
      const used = over0 ? sh : Math.round(Math.max(0, ...[...body.children].map((c) => c.getBoundingClientRect().bottom)) - body.getBoundingClientRect().top);
      const fxTxt = fx ? `固定區 <b>${Math.round(fx.getBoundingClientRect().height)}</b> px；` : "";
      const head = over0
        ? `<span class="bad">要捲</span>：${fxTxt}捲動區可視 <b>${ch}</b> px，內容 <b>${sh}</b> px＝約 <b>${(sh / ch).toFixed(1)}</b> 屏`
        : `<span class="ok">一屏放得下</span>：${fxTxt}捲動區可視 <b>${ch}</b> px，內容 <b>${used}</b> px`;
      const where = keys.length ? "<br>" + keys.map(([n, y]) => `${n}：第 <b>${Math.floor(y / ch) + 1}</b> 屏（往下 ${Math.round(y)} px）`).join("；") : "";
      meter.innerHTML = head + where + (opt.note ? "<br>" + opt.note : "");
    }
  }

  // ---------------- 分頁列、手風琴 ----------------
  /** 分頁上的狀態記號（2.4 標籤的縮小版）：n＝金底數字（有事可做）、p＝細框數字（進度、數量）、live＝綠點（限時的事進行中）、warn＝琥珀三角、lock＝金鎖（整頁還沒開放）。 */
  function badge(kind, v, title) {
    if (kind === "lock") return h("span.ip-tbadge.ico", { title }, ICON.lock(15));
    if (kind === "warn") return h("span.ip-tbadge.ico", { title }, ICON.warn(13));
    if (kind === "live") return h("span.ip-tbadge.live", { title });
    return h("span.ip-tbadge", { class: kind, title }, v);
  }
  /** tabs：[{ id, icon(), label, short, badge: [kind, 值, 說明] }]；label 可以是 newText。 */
  const r = (x) => (typeof x === "function" ? x() : x); /* 提案字是 DOM 節點，每次用都要新建（同一個節點只能放一處） */
  const tabBar = (tabs, on) => h("div.ip-tabbar", { role: "tablist" }, tabs.map((t) => { const label = r(t.label); return h("button.ip-tab", { type: "button", role: "tab", class: t.id === on ? "on" : null, "aria-selected": String(t.id === on), title: t.title ?? (typeof label === "string" ? label : label.textContent) },
    t.icon(), h("span.lbl", {}, label), h("span.lbl-s", {}, r(t.short)), t.badge ? badge(t.badge[0], r(t.badge[1]), t.badge[2]) : null); }));
  /** 手風琴：secs＝[{ id, icon(), title, end, body() }]，只有 on 那一塊展開。 */
  const acc = (secs, on) => h("div.ip-acc", {}, secs.map((s) => h("section.ip-acc-sec", { class: s.id === on ? "on" : null },
    h("button.ip-acc-head", { type: "button", "aria-expanded": String(s.id === on) }, s.icon(), h("span.ttl", {}, s.title), s.end ? h("span.end", {}, s.end()) : null),
    s.id === on ? h("div.ip-acc-body", {}, s.body()) : null)));
  const titleIs = (t) => (body) => [...body.querySelectorAll(".ip-sec-title, .ip-acc-head .ttl")].find((e) => e.textContent === t);

  /** 第 2 版的面板拿來當 (a)：抽出捲動區的內容，套第 10 節玩法 PM 確認的字。 */
  const V10 = [["到 4 級", "4 級起"], ["同時 1 個，一直有效到自己解除", "同時 1 個，到城鎮或營火才能換"]];
  function v2Body(panelEl) {
    const body = panelEl.querySelector(".ui-popup-body");
    const walk = document.createTreeWalker(body, NodeFilter.SHOW_TEXT);
    for (let n = walk.nextNode(); n; n = walk.nextNode()) for (const [a, b] of V10) if (n.nodeValue.includes(a)) n.nodeValue = n.nodeValue.replace(a, b);
    return [...body.childNodes];
  }

  // =====================================================================
  // 成長與技能
  // =====================================================================
  const G = {
    fixed: () => [head("成長與技能"),
      h("div.ip-chips", {}, chip(ICON.grow(16), "Lv", 2), chip(ICON.rank(16), "角色階級", 1), chip(ICON.bulb(15), "靈感點", 3), chip(ICON.up(16), "未分配屬性點", 0, { zero: true })),
      callout("warn", ICON.warn(15), h("span", {}, h("b", {}, "現在不行"), "：這裡不是城鎮或營火"), { sub: "閃現、重閃、溶掉、傳承、重配屬性、立誓只在城鎮與營火（和換技能同一處）。" })],
    flash: (withLock = true) => [
      withLock ? callout("lock", ICON.lock(18), h("span", {}, h("b", {}, "閃現"), "：4 級起")) : null,
      h("div.ip-rule-chips", {},
        h("span.ip-rule", {}, ICON.bulb(14), h("b", {}, "1 點"), "4 個變化選 1"),
        h("span.ip-rule", {}, ICON.bulb(14), h("b", {}, "+1 點"), "指定類別、該類 3 選 1"),
        h("span.ip-rule", {}, ICON.book(14), "每招最多閃 ", h("b", {}, "5"), " 次"),
        tip(h("span", {}, "出題就會扣點，一定要選一個。", h("br"), "要先在戰鬥中用過才能再閃。"), { place: "below", right: true })),
      h("div.ip-rows", {}, [["skill_wild_blade", "狂野之刃", "已閃 0／5 次"], ["skill_shadow_backstab", "瞬步背刺", "已閃 0／5 次"]].map(([id, n, c]) => h("div.ip-row.ip-skill", {},
        OB.skillIcon(id, 32), h("span", {}, h("span.name", {}, n), h("span.ip-l3", { style: "display:block" }, c)),
        tag("lock", ICON.lock(14), "4 級起"), h("button", { type: "button", disabled: true }, "閃現"))))],
    attr: () => [callout("info", ICON.info(14), "入門期可以自己配點，正式選定時會照新武器重配一次。"),
      h("div.ip-tabline", {}, h("span", {}, "未分配的屬性點"), h("span.end", {}, tag("dim", "升級時每級 +2"))),
      h("div.ip-empty", {}, "沒有未分配的屬性點。")],
    reflash: () => [h("div.ip-l2", {}, "把一招以前某一次的變化換掉，價格和閃現相同（1 點出 4 個；指定類別 2 點出 3 個）。不需要先上場用過，也不增加閃現次數；新選項不會比被換掉的更弱。"),
      h("div.ip-empty", {}, "還沒有可以重閃的技能（要先閃現過，或有完整技能）。")],
    dissolve: () => [h("div.ip-l2", {}, "選一招舊技能，然後二選一：溶掉（退回花在它身上的靈感點的一半）或傳承（把它的小變化帶給另一招新技能）。兩種都會讓舊技能消失。")],
    oath: () => [h("div.ip-l2", {}, "入門期不能立誓，找葛蘭正式選定後開放。")],
    /** 整備分頁（推薦的混合：分頁內三列摺疊，一次只開一個） */
    care: (open) => [h("div.ip-tabline", {}, h("span", {}, "重閃、溶掉與傳承、誓約"), h("span.end", {}, tag("", "只在城鎮與營火"))),
      fold(h("span", {}, h("b", {}, "重閃"), "　把以前的一次變化換掉"), tag("dim", newText("還沒有可以重閃的技能")), open === "reflash", G.reflash()),
      fold(h("span", {}, h("b", {}, "溶掉或傳承"), "　二選一，舊技能會消失"), tag("lock", ICON.lock(14), "4 級起"), open === "dissolve", G.dissolve()),
      fold(h("span", {}, h("b", {}, "誓約"), "　同時 1 個，到城鎮或營火才能換"), tag("lock", ICON.lock(14), newText("正式選定後")), open === "oath", G.oath())],
    look: () => [h("div.ip-rows", {},
      h("div.ip-row.ip-set", {}, h("span.lbl", {}, h("span.ip-l1", {}, "外觀")), h("span.ctl", {}, tag("lock", ICON.lock(14), "只有在主城能改外觀"), h("button", { type: "button", disabled: true }, "改外觀"))),
      h("div.ip-row.ip-set", {}, h("span.lbl", {}, h("span.ip-l1", {}, "種族"), h("span.ip-l3", {}, "本季可以免費換一次")),
        h("span.ctl", {}, tag("lock", ICON.lock(14), newText("正式選定後才能換")), h("select", { disabled: true, "aria-label": "新種族" }, h("option", {}, "精靈")), h("button", { type: "button", disabled: true }, "換種族"))))],
  };
  const G_TABS = [
    { id: "flash", icon: () => ICON.bulb(16), label: "靈感閃現", short: () => newText("閃現"), badge: ["lock", null, "閃現 4 級起"] },
    { id: "attr", icon: () => ICON.up(16), label: "屬性點", short: () => newText("屬性") },
    { id: "care", icon: () => ICON.campfire(16), label: () => newText("整備"), short: () => newText("整備"), title: "整備：重閃、溶掉與傳承、誓約" },
    { id: "look", icon: () => heroPortrait(16), label: "外觀與種族", short: () => newText("外觀") },
  ];
  const gPane = (id, open) => h("div.ip-tabpane", {}, { flash: G.flash, attr: G.attr, care: () => G.care(open), look: G.look }[id]());
  const G_ACC = [
    { id: "flash", icon: () => ICON.bulb(18), title: "靈感閃現", end: () => tag("lock", ICON.lock(14), "4 級起"), body: () => G.flash(false) },
    { id: "attr", icon: () => ICON.up(18), title: "屬性點", end: () => tag("dim", "升級時每級 +2"), body: G.attr },
    { id: "reflash", icon: () => ICON.campfire(18), title: "重閃", end: () => tag("dim", newText("還沒有可以重閃的技能")), body: G.reflash },
    { id: "dissolve", icon: () => ICON.campfire(18), title: "溶掉或傳承", end: () => tag("lock", ICON.lock(14), "4 級起"), body: G.dissolve },
    { id: "oath", icon: () => ICON.campfire(18), title: "誓約", end: () => tag("lock", ICON.lock(14), newText("正式選定後")), body: G.oath },
    { id: "look", icon: () => heroPortrait(18), title: "外觀與種族", body: G.look },
  ];

  // =====================================================================
  // 公告板
  // =====================================================================
  const N = {
    fixed: () => [head("公告板"),
      h("div.ip-speaker", { style: "margin-top:6px" }, portraitOf("seal_keeper", 36), h("div.ip-bubble", { style: "font-size:13px;padding:4px 10px" }, h("span.who", {}, "守印人"), "封印和懸賞的消息，都貼在板上了。")),
      h("div.ip-season-top", { style: "margin:8px 0 0" },
        h("span.ip-dayno", {}, "第", h("b", {}, "1"), "天", h("span", { style: "color:var(--ip-l3)" }, "／共 14 天")),
        h("span.ip-phase-nm", {}, tag("open", "霧中裂痕"), "第 1～3 天"),
        h("div.ip-next", { style: "grid-column:2;grid-row:2;margin-top:0" }, h("span.k", {}, "下一個"), tag("", "第 2 天"), h("b", {}, "主線第 1 章的劇情技能"), h("span.ip-l3", {}, newText("（明天）"))))],
    goals: (line = true) => [line ? h("div.ip-tabline", {}, tag("info", "新手期：教學目標"), h("span.end", {}, newText("完成一條"), ICON.token(15), h("b", { style: "color:var(--ip-num)" }, "+1"))) : null,
      h("div.ip-rows", {}, [["完成新手任務 2 步", 0, 2], ["發現 1 個隱藏地點", 0, 1], ["打倒 1 隻精英", 0, 1]].map(([t, n, d]) => h("div.ip-row.ip-goal", {}, h("span.ip-check"), h("span.text", {}, t), prog(n, d))))],
    bounty: (line = true) => [line ? h("div.ip-tabline", {}, newText("先搶先贏"), h("span.end", {}, ICON.clock(15), "每天 06:00 換一批", tip("先打倒的人拿走當天的懸賞（每天 06:00 刷新）。"))) : null,
      h("div.ip-cols-head.ip-bounty-cols", {}, h("span"), h("span", {}, "目標・地點"), h("span", {}, "建議等級"), h("span.reward-h", {}, "獎勵"), h("span", { style: "text-align:right" }, "狀態")),
      h("div.ip-rows", {}, [["北坡狼王", "北坡獵場", 5], ["霧中劍客", "劍冢", 5], ["斷崖幫二當家「疤面」", "斷崖幫寨", 4]].map(([n, where, lv]) => h("div.ip-row.ip-bounty.ip-bounty-cols", {},
        ICON.combat(24), h("span.stack", {}, h("span.name", {}, n), h("span.where", {}, ICON.town(14), where)),
        h("span.lv", {}, "Lv ", h("b", {}, String(lv))), h("span.reward", {}, ICON.token(15), "3"), h("span.state", {}, tag("open", "懸賞中")))))],
    sched: () => [h("div.ip-tabline", {}, h("span.ip-l2", {}, "主線第 1～2 章、雲嶺；世界事件「霧潮入侵」"), h("span.end", {}, ICON.clock(16), "每天 06:00 刷新")),
      IP.timeline(),
      fold(h("span", {}, h("b", {}, "完整日程"), "（6 個時間點、5 個階段）"), null, false)],
    events: (line = true) => [line ? h("div.ip-tabline", {}, newText("全服一起推進")) : null,
      h("div.ip-event", {},
        h("div.ip-event-head", {}, ICON.ridge(18), h("span.name", {}, "霧潮入侵"), tag("", "第 1～3 天"), h("span.end", {}, tag("live", "進行中"))),
        h("div.ip-l2", {}, "全服在雲嶺的霧中打贏戰鬥；成功則開放灰燼荒原"),
        h("div.ip-bar", {}, h("span.ip-bar-track", {}, h("i", { style: "width:0%" })), h("span.ip-bar-num", {}, h("b", {}, "0"), "／30"), tip(h("span", {}, h("b", {}, "門檻"), "：沒有前一天的上線紀錄，用原門檻")))),
      h("div.ip-event.pending", {},
        h("div.ip-event-head", {}, ICON.fire(18), h("span.name", {}, "熔岩潰堤"), tag("", "第 4～7 天"), h("span.end", {}, tag("dim", "尚未開始"))),
        h("div.ip-l2", {}, "全服在赤沙村、灰井村、鐵爐村打贏守點戰；成功則熔心坑提早開放、封印鑰匙 +5"),
        h("div.ip-bar", {}, h("span.ip-bar-track", {}, h("i", { style: "width:0%" })), h("span.ip-bar-num", {}, h("b", {}, "0"), "／24")))],
    boss: (line = true) => [line ? h("div.ip-tabline", {}, h("b", { style: "color:var(--ui-text);font-size:14px" }, "碎晶之主"), h("span.end", {}, tag("lock", ICON.lock(14), "封印中"))) : null,
      h("div.ip-l2", {}, "11 月 10 日 06:00 解鎖"),
      h("div.ip-bar", { style: "margin-top:4px" }, ICON.crystal(16), h("span.ip-l2", {}, "封印鑰匙"), h("span.ip-bar-track", {}, h("i", { style: "width:0%" })), h("span.ip-bar-num", {}, "全服 ", h("b", {}, "0"), " 把・你有 ", h("b", {}, "0"), " 把（需要 1 把）")),
      fold(h("span", {}, h("b", {}, "挑戰規則與評分榜")), tag("dim", "還沒有人打倒"), false, h("div.ip-l2", {}, "今天還剩 3／3 次（算帳號）；只准系統傭兵，失敗只扣次數。"))],
  };
  const N_TABS = [
    { id: "goals", icon: () => ICON.clue(16), label: "今日目標", short: () => newText("目標"), badge: ["p", () => newText("0／3"), "今日目標完成 0／3"] },
    { id: "bounty", icon: () => ICON.swords(16), label: "懸賞板", short: () => newText("懸賞"), badge: ["n", "3", "懸賞中 3"] },
    { id: "sched", icon: () => ICON.hourglass(16), label: "賽季時程", short: () => newText("時程") },
    { id: "events", icon: () => ICON.map(16), label: "世界事件", short: () => newText("事件"), badge: ["live", null, "霧潮入侵 進行中"] },
    { id: "boss", icon: () => portal(16), label: "賽季頭目", short: () => newText("頭目"), badge: ["lock", null, "封印中"] },
  ];
  const nPane = (id) => h("div.ip-tabpane", {}, N[id]());
  const N_ACC = [
    { id: "goals", icon: () => ICON.clue(18), title: "今日目標", end: () => tag("", "完成 ", newText("0／3")), body: () => N.goals() },
    { id: "bounty", icon: () => ICON.swords(18), title: "懸賞板", end: () => tag("open", "懸賞中 3"), body: () => N.bounty() },
    { id: "sched", icon: () => ICON.hourglass(18), title: "賽季時程", body: N.sched },
    { id: "events", icon: () => ICON.map(18), title: "世界事件", end: () => tag("live", "霧潮入侵 進行中"), body: () => N.events() },
    { id: "boss", icon: () => portal(18), title: "賽季頭目", end: () => tag("lock", ICON.lock(14), "封印中"), body: () => N.boss() },
  ];

  // =====================================================================
  // 任務與線頭、隊伍／我的影子（推薦案）
  // =====================================================================
  const Q = {
    quests: () => { const v2 = IP.questsProposal(); const card = v2.querySelector(".ip-quest"); return [h("div.ip-tabline", {}, tag("", "進行中 1")), card]; },
    threads: () => [h("div.ip-tabline", {}, h("span.ip-l2", {}, "事件的結果會留下線頭"), h("span.end", {}, tip("事件的結果會留下線頭（每人約 5 條，約 3 天到期）。", {}))),
      h("div.ip-rows", {}, [["商人欠你人情", "剩 2 天 23 小時"], ["狼群是被趕下山的", "剩 2 天 23 小時"]].map(([t, left]) => h("div.ip-row.ip-thread", {}, ICON.thread(18), h("span.name", {}, t),
        h("span.end", {}, tag("", "個人"), tag("", ICON.clock(14), newText(left))))))],
  };
  const Q_TABS = [
    { id: "quests", icon: () => ICON.scroll(16), label: "任務日誌", short: () => newText("任務"), badge: ["p", "1", "進行中 1"] },
    { id: "threads", icon: () => ICON.thread(16), label: "線頭", short: "線頭", badge: ["p", "2", "線頭 2 條"] },
  ];
  const P = {
    party: () => { const v2 = IP.partyProposal(); return [h("div.ip-tabline", {}, chip(null, "", "3／3"), h("span", {}, "主角＋最多 2 名")), v2.querySelector(".ip-members"),
      ...v2.querySelectorAll(".ip-sec.first > .ip-callout")]; },
    shadow: () => [h("div.ip-tabline", {}, tag("warn", ICON.warn(13), "還沒存"), h("span.ip-l3", {}, "在城鎮休息、換技能等整備時自動存")),
      h("div.ip-shadow", {},
        h("div.ip-stat", {}, h("span.k", {}, "預設打法"), h("span.v", {}, "預設")),
        h("div.ip-stat", {}, h("span.k", {}, "被借用得到的任務幣"), h("span.v", {}, ICON.token(15), h("b", { style: "color:var(--ip-num)" }, "0")))),
      h("div.ip-empty", {}, "還沒有人借過你的影子。")],
  };
  const P_TABS = [
    { id: "party", icon: () => ICON.flag(16), label: "隊伍", short: "隊伍", badge: ["p", "3／3", "隊伍 3／3（含主角）"] },
    { id: "shadow", icon: () => ICON.shadow(16), label: "我的影子", short: () => newText("影子"), badge: ["warn", null, "還沒存"] },
  ];

  // ---------------- 頁面 ----------------
  const verdict = (rows) => h("div.ip-verdict", {}, rows.flatMap(([k, v]) => [h("span.k", {}, k), h("div", { html: v })]));
  const vcol = (title, tagCls, tagText, ...kids) => h("div.ip-vcol", {}, h("div.ip-vhead", {}, h("b", {}, title), tagText ? h("span.tag", { class: tagCls || null }, tagText) : null), kids);
  const cap = (html) => h("div.ip-vcap", { html });

  /** 三案並排的一頁：p＝growth｜notice，vw＝1600｜800。 */
  function compare(p, vw) {
    const box = BOX[vw], wide = vw === 1600;
    const grid = h("div.ip-vgrid", { style: `--pw:${box.w}px;--cols:3` });
    if (p === "growth") {
      const v2a = () => v2Body(IP.growthProposal());
      const keysA = [["靈感閃現", titleIs("靈感閃現")], ["重閃・溶掉・誓約", titleIs("重閃、溶掉與傳承、誓約")]];
      grid.append(
        vcol("(a) 第 2 版：一路往下捲", "", "對照",
          cap("<b>一打開</b>（第 1 屏）"), screen(vw, null, v2a(), { keys: keysA }),
          cap("<b>捲到「重閃、溶掉與傳承、誓約」</b>"), screen(vw, null, v2a(), { scrollTo: titleIs("重閃、溶掉與傳承、誓約") }),
          verdict([["一打開", wide ? "標頭、四個籌碼、警告、入門期提示、鎖住清單、外觀與種族、屬性點；靈感閃現只露出規則與第一招（第 1 屏下緣），第二招和重閃以下在第 2 屏" : "標頭、四個籌碼、警告、入門期提示、鎖住清單、外觀與種族的上半；靈感閃現在第 2 屏"],
            ["關鍵資訊", `能不能用（警告）0 下；每招能不能閃現 <span class="bad">${wide ? "第二招起要捲" : "要捲 1 屏"}</span>；重閃、溶掉、誓約的狀態 <span class="bad">要捲到底</span>`],
            ["標籤狀態", "沒有分頁，沒有地方放；狀態散在各區塊標頭右邊，要捲過去才看得到"],
            ["骨架", "標題、「回到地點圖」跟著捲走（遊戲端的 × 是 sticky，留在右上）；捲下去後上緣漸隱蓋住半行"]])),
        vcol("(b) 上方分頁＋分頁內摺疊", "new", "推薦",
          cap("<b>一打開</b>：預設第一個分頁「靈感閃現」"), screen(vw, [G.fixed(), tabBar(G_TABS, "flash")], gPane("flash")),
          cap("<b>點「整備」</b>（1 下）＋點「重閃」（第 2 下）"), screen(vw, [G.fixed(), tabBar(G_TABS, "care")], gPane("care", "reflash")),
          verdict([["一打開", "固定區（標頭＋籌碼＋警告＋分頁列）＋「靈感閃現」分頁：鎖住提示、三個規則籌碼、兩招各一列"],
            ["關鍵資訊", '能不能用 0 下；每招能不能閃現 <span class="good">0 下</span>；屬性點、外觀與種族 1 下；重閃・溶掉・誓約的狀態 1 下（摺疊列右邊的標籤），內容 2 下'],
            ["標籤狀態", "「靈感閃現」掛金鎖（4 級起，整頁的閃現都還沒開放）；在城鎮、4 級起、有靈感點時改成金底「3」；有未分配屬性點時「屬性點」掛金底數字；其他不掛"],
            ["骨架", "標頭（標題＋回到地點圖＋×）、籌碼、警告、分頁列都在固定區，不捲；警告管整個面板，所以在分頁列上面；分頁內容才捲"]])),
        vcol("(c) 手風琴（一次開一個）", "", "對照",
          cap("<b>一打開</b>：預設展開第一塊「靈感閃現」"), screen(vw, G.fixed(), acc(G_ACC, "flash"), { keys: [["外觀與種族的標頭", titleIs("外觀與種族")]] }),
          cap("<b>點「重閃」</b>（1 下；靈感閃現自動收起）"), screen(vw, G.fixed(), acc(G_ACC, "reflash")),
          verdict([["一打開", "固定區（標頭＋籌碼＋警告）＋六個區塊標頭，「靈感閃現」展開"],
            ["關鍵資訊", '能不能用 0 下；每招能不能閃現 0 下；<span class="good">其他五塊的狀態 0 下</span>（標頭右邊的完整標籤一次看到）；內容 1 下'],
            ["標籤狀態", "放得下完整的標籤（2.4），不用縮小記號"],
            ["問題", `一層要排六個標頭（重閃、溶掉、誓約各一塊，不然就要摺疊裡再摺疊）；展開的那塊把下面的標頭推走${wide ? "" : '，<span class="bad">800 時一打開就要捲</span>'}；點下面的標頭時上面那塊收起，整列往上跳`]])));
    } else {
      const v2a = () => v2Body(IP.boardProposal());
      const keysA = [["懸賞板", titleIs("懸賞板")], ["世界事件", titleIs("世界事件")], ["賽季頭目", titleIs("賽季頭目")]];
      grid.append(
        vcol("(a) 第 2 版：一路往下捲", "", "對照",
          cap("<b>一打開</b>（第 1 屏）"), screen(vw, null, v2a(), { keys: keysA, theme: "capital" }),
          cap("<b>捲到「懸賞板」</b>"), screen(vw, null, v2a(), { scrollTo: titleIs("懸賞板"), theme: "capital" }),
          verdict([["一打開", wide ? "標頭、守印人、賽季時程（大字、時間軸、下一個）、今日目標；懸賞板只露標頭" : "標頭、守印人、賽季時程（大字、時間軸、下一個）；今日目標在第 2 屏"],
            ["關鍵資訊", `第幾天、下一件事 0 下；今日目標 ${wide ? "0 下" : '<span class="bad">要捲 1 屏</span>'}；懸賞 <span class="bad">要捲 1 屏</span>；世界事件、頭目 <span class="bad">要捲 ${wide ? "1～2" : "2～3"} 屏</span>`],
            ["標籤狀態", "沒有地方放；「懸賞中」「進行中」「封印中」都在下面，捲到才看得到"],
            ["骨架", "標題、「回到地點圖」跟著捲走（× 是 sticky）"]])),
        vcol("(b) 上方分頁＋分頁內摺疊", "new", "推薦",
          cap("<b>一打開</b>：預設第一個分頁「今日目標」"), screen(vw, [N.fixed(), tabBar(N_TABS, "goals")], nPane("goals"), { theme: "capital" }),
          cap("<b>點「懸賞」</b>（1 下）"), screen(vw, [N.fixed(), tabBar(N_TABS, "bounty")], nPane("bounty"), { theme: "capital" }),
          verdict([["一打開", "固定區（標頭＋守印人＋「第 1 天」大字、這段日程、下一個＋分頁列）＋「今日目標」分頁"],
            ["關鍵資訊", '第幾天、下一件事 <span class="good">0 下</span>（固定區）；今日目標 0 下；懸賞、時間軸、世界事件、頭目各 1 下'],
            ["標籤狀態", "今日目標細框「0／3」（完成幾條）、懸賞金底「3」（還能搶的懸賞）、世界事件綠點（霧潮入侵進行中）、賽季頭目金鎖（封印中）；賽季時程不掛"],
            ["骨架", `同成長：標頭、回到地點圖、× 在固定區；「第 1 天」與「下一個」從賽季時程搬到固定區（每個分頁都看得到）${wide ? "" : "；800 時五個分頁放不下，其他分頁自動換兩字短名（目標、懸賞、時程、事件、頭目），目前分頁保留全名"}`]])),
        vcol("(c) 手風琴（一次開一個）", "", "對照",
          cap("<b>一打開</b>：預設展開「今日目標」"), screen(vw, N.fixed(), acc(N_ACC, "goals"), { theme: "capital", keys: [["賽季頭目的標頭", titleIs("賽季頭目")]] }),
          cap("<b>點「懸賞板」</b>（1 下；今日目標收起）"), screen(vw, N.fixed(), acc(N_ACC, "bounty"), { theme: "capital" }),
          verdict([["一打開", "固定區（同 b，少分頁列）＋五個區塊標頭，「今日目標」展開"],
            ["關鍵資訊", '第幾天、下一件事 0 下；今日目標 0 下；<span class="good">懸賞、世界事件、頭目的狀態 0 下</span>（標頭右邊）；內容 1 下'],
            ["標籤狀態", "完整標籤：「完成 0／3」「懸賞中 3」「霧潮入侵 進行中」「封印中」"],
            ["問題", `懸賞板、時間軸展開時把下面的標頭推走${wide ? "" : '（<span class="bad">800 時一打開就要捲</span>）'}；點了之後標頭的位置會跳`]])));
    }
    return grid;
  }

  /** 任務與線頭、隊伍：推薦案（分頁）。 */
  function others(vw) {
    const box = BOX[vw];
    const grid = h("div.ip-vgrid", { style: `--pw:${box.w}px;--cols:2` });
    grid.append(
      vcol("任務與線頭（推薦案：分頁）", "new", "推薦案",
        cap("<b>一打開</b>：「任務日誌」"), screen(vw, [head("任務與線頭"), tabBar(Q_TABS, "quests")], h("div.ip-tabpane", {}, Q.quests())),
        cap("<b>點「線頭」</b>（1 下）"), screen(vw, [head("任務與線頭"), tabBar(Q_TABS, "threads")], h("div.ip-tabpane", {}, Q.threads())),
        verdict([["一打開", "標頭＋分頁列＋目前的任務（路線、步驟時間軸）"], ["關鍵資訊", "目前步驟 0 下；線頭 1 下"],
          ["標籤狀態", "兩個都是細框數字（進行中 1、線頭 2）；線頭快到期（剩不到 1 天）時改琥珀三角"],
          ["為什麼拆", "現在 1 個任務、2 條線頭放得下一屏；但任務最多會有好幾條、線頭每人約 5 條，常見最多時超過一屏，照規則先拆"]])),
      vcol("隊伍（推薦案：分頁）", "new", "推薦案",
        cap("<b>一打開</b>：「隊伍」"), screen(vw, [head(newText("隊伍與影子")), tabBar(P_TABS, "party")], h("div.ip-tabpane", {}, P.party())),
        cap("<b>點「我的影子」</b>（1 下）"), screen(vw, [head(newText("隊伍與影子")), tabBar(P_TABS, "shadow")], h("div.ip-tabpane", {}, P.shadow())),
        verdict([["一打開", "標頭＋分頁列＋三張隊友卡、夥伴說明、換隊友的鎖"], ["關鍵資訊", "隊伍 0 下；影子存了沒：<span class=\"good\">0 下</span>（分頁上的琥珀三角），細節 1 下"],
          ["標籤狀態", "隊伍細框「3／3」；我的影子「還沒存」＝琥珀三角"],
          ["為什麼拆", "隊伍與影子是兩件事；影子的戰報會一直變長（被借用的紀錄）"]])));
    return grid;
  }

  /** 分頁列在不同寬度怎麼縮（自動：放不下才縮），與標籤狀態一覽。 */
  function tabbarDemo() {
    const row = (w, label, tabs, on) => [h("span.k", { html: label }), h("div.ip-barbox", { style: `width:${w}px` }, tabBar(tabs, on))];
    return h("div", {},
      h("div.ip-barstrip", {},
        row(696, "<b>面板 720</b>1600×900（內寬 696）", N_TABS, "goals"),
        row(490, "<b>面板 514</b>800×600（內寬 490）", N_TABS, "goals"),
        row(400, "<b>內寬 400</b>", N_TABS, "goals"),
        row(320, "<b>內寬 320</b>", N_TABS, "goals"),
        row(250, "<b>內寬 250</b>（popupBox 的下限）", N_TABS, "goals"),
        row(490, "<b>成長 面板 514</b>", G_TABS, "flash"),
        row(490, "<b>成長</b>（在城鎮、Lv 4、靈感 3、屬性點 2 時）", [{ ...G_TABS[0], badge: ["n", "3", "可以閃現：靈感點 3"] }, { ...G_TABS[1], badge: ["n", "2", "未分配屬性點 2"] }, G_TABS[2], G_TABS[3]], "flash")),
      h("div.ip-legend", { style: "margin-top:18px;max-width:900px" },
        h("span.k", {}, badge("n", "3")), h("span", {}, "金底數字＝有事可做（還能搶的懸賞、可用的靈感點、未分配屬性點）"),
        h("span.k", {}, badge("p", "1")), h("span", {}, "細框數字＝進度或數量（今日目標完成幾條、進行中的任務、線頭）"),
        h("span.k", {}, badge("live")), h("span", {}, "綠點＝限時的事正在進行（世界事件）"),
        h("span.k", {}, badge("warn")), h("span", {}, "琥珀三角＝警告：要注意，但不是進度問題（影子還沒存、線頭快到期）"),
        h("span.k", {}, badge("lock")), h("span", {}, "金鎖＝整個分頁的功能都還沒開放（只有一部分鎖住時不掛）"),
        h("span.k", {}, h("span.ip-l3", {}, "（不掛）")), h("span", {}, "純資訊、沒有要處理的事")));
  }

  return { BOX, screen, finish, fitTabs, tabBar, acc, badge, compare, others, tabbarDemo, G, N, G_TABS, N_TABS };
})();
