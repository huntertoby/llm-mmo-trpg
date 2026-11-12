# Phase PNL-2 報告：成長與技能面板

依據：`docs/art/資訊面板-移植需求.md`（美術 PM 第九任，使用者「照建議」）表 6 的 PNL-2 列；驗收看第 7 節標「2」的四列（#11～#14）。
起點：worktree 開在 `404c56bd`，落後 main，先 `git merge --ff-only main` 快轉到 `429d4a86`（已含 PNL-1a 合併 `0d0f9c7f`）。PNL-1b、3、4 沒做；沒改公告板、`content/`、數值工坊、Python。

## 1. 做了什麼

| 項目 | 檔案 |
|---|---|
| 「成長與技能」面板改成 `PanelTabs`：固定區（標題＋回到地點圖、四個籌碼 Lv／角色階級／靈感點／未分配屬性點，0 灰；不能花點時一行琥珀警告「**現在不行**：〔伺服器原因〕」＋右邊 (i)＝原次行 `service_zh`；在城鎮可花點時不顯示）＋四個分頁 | `client/src/world/WorldGrowth.tsx` |
| 分頁：靈感閃現｜閃現｜燈泡｜入門期金鎖（滑過「閃現 4 級起」）、能花點且有靈感點時金底數字（「可以閃現：靈感點 N」）→ 屬性點｜屬性｜增益箭頭（第④批 `skeleton:aura`）｜有未分配點時金底（「未分配屬性點 N」）→ 整備｜整備｜營火 `b_rest`｜無（滑過「整備：重閃、溶掉與傳承、誓約」）→ 外觀與種族｜外觀｜主角頭像不帶框｜無。預設分頁照 `pickTab`（入門期＝屬性點） | `client/src/world/growthPanel.ts`（記號、新字、`growthWarning`、`growthTabOf`、`raceLockTag`） |
| 靈感閃現頁：入門期鎖住提示「**閃現**：4 級起」→ 規則籌碼＋(i) → 每招一列（技能圖示 32、名字＋（備用）＋「可以閃現了」、L3 已閃次數、入門期鎖標籤「4 級起」（說明卡＝伺服器原句）、閃現鈕）；點名字照現行展開技能卡；出題畫面照現行 `FlashChooser` | `WorldGrowth.tsx` `FlashPane` |
| 屬性點頁：入門期資訊條（伺服器 `starter_note_zh`）→「未分配的屬性點」＋淡灰標籤「升級時每級 +2」→ 沒點時虛線空狀態「沒有未分配的屬性點。」；配點與重配照現行 `AttributeRespecSection` | `WorldGrowth.tsx` `AttrPane` |
| 整備頁：第一行「重閃、溶掉與傳承、誓約」＋「只在城鎮與營火」；三列摺疊（同一組、一次只開一個；新字摘要）；右邊標籤：重閃沒有可重閃的技能＝淡灰「還沒有可以重閃的技能」（說明卡「要先閃現過，或有完整技能。」）、溶掉或傳承入門期＝鎖「4 級起」、誓約入門期＝鎖「正式選定後」（說明卡都是伺服器原句）；展開後照現行內容（原段落＋清單） | `WorldGrowth.tsx` `CarePane`；`client/src/run/CampfireSkillCare.tsx`（匯出 `ReflashSection`／`OldSkillSection`，加 `bare`） |
| 外觀與種族頁：兩列設定列（「外觀」右邊鎖標籤＝伺服器字，能改時細框「主城隨時免費」＋改外觀；「種族」＋L3「本季可以免費換一次」＋鎖標籤「正式選定後才能換」（原句進說明卡）＋選單＋換種族） | `client/src/world/GrowthLookRows.tsx`（新）；舊側欄仍用 `LookChangeLine`／`RaceChangeLine`，沒改 |
| `FlashSection` 規則籌碼（#19，一輪營火一起換）：原一段規則 → 三籌碼「**1 點**　4 個變化選 1」「**+1 點**　指定類別、該類 3 選 1」「每招最多閃 **5** 次」＋(i)「出題就會扣點，一定要選一個。要先在戰鬥中用過才能再閃。」（數字照 `flash_rules`）；營火其他排法不動。另抽出 `flashRowState`（閃現鈕停用與原因）給兩邊共用 | `client/src/run/FlashSection.tsx` |
| 「外觀與種族」分頁圖示：`HeroFace` 加 `bare` 選項（同一份外觀、快取鍵多 `|bare`）；`drawPortraitBare` 不畫底與框、量人物外框後放大到寬度撐滿上緣貼齊（`portraitBareFit`）、下緣 22% 漸隱 | `client/src/ui/heroFace.tsx`、`client/src/render/portrait.ts` |
| 「靈感 N」直開：HUD 主角卡的靈感點籌碼（有 `onGrowthTab` 時）變成按鈕 → 打開成長面板直接開「靈感閃現」（已開著也換過去、不關）；功能列 G 照預設 | `client/src/world/WorldHud.tsx`、`client/src/screens/WorldScreen.tsx`、`client/src/styles/world-hud.css` |
| 共用元件修正（向後相容，見第 5 節） | `client/src/ui/PanelTabs.tsx`、`client/src/ui/PanelKit.tsx` |
| 樣式：`pnl-rule-chips`、`pnl-rule`、`pnl-skill`、`pnl-set`、`pnl-measure-wrap`、整備摺疊內段落、主角卡籌碼鈕 | `client/src/styles/world-hud.css` |
| 開發頁：`#growth`（`?case=starter｜lv4&tab=…&fold=…`）、`#campfire`（一輪營火 fixture）、`#bar` 加成長兩列 | `client/src/dev/panelGallery.tsx` |
| 測試 19 項 | `client/src/world/pnl2Growth.test.ts`（新） |
| 上手筆記第四節第 94～99 點（原 89～94，與 PNL-1b 整合時順延） | `docs/dev/上手-前端戰鬥畫面與動畫.md` |

## 2. 第 5 節「要開發 PM 決定的事」本段怎麼做

| # | 做法 |
|---|---|
| 11 | 照美術建議：`heroFace.tsx` 加 `bare` 選項（同一份外觀與快取鍵，帶框的鍵不變） |
| 8 | 沿用 PNL-1a（開著時不重量）；另修了「捲軸晚出現」補量一次（第 5 節 3） |
| 6 | 沿用 PNL-1a；另修了量高度時同名互斥（第 5 節 2） |
| 其他 | 屬於 PNL-1b／3／4，本段沒碰 |

## 3. 既有測試的改動（舊 → 新）

1. `client/src/world/limits.test.ts`「成長面板第一行：入門期在服務說明後面接伺服器給的那一句」：舊＝原始碼含 `{view.growth.starter_note_zh ?? ""}` → 新＝含 `const starter = view.growth.starter_note_zh ?? null;`（標題改「PNL-2 起放在「屬性點」分頁的資訊條」）。理由：#14 這句從第一行搬到屬性點分頁；字仍照伺服器。
2. `client/src/ui/summonBadges.test.ts`「6 處都改成 lead-gap」：拿掉 `world/WorldGrowth.tsx` 那一處（`<span className="muted small lead-gap">Lv …`），改成檢查 `label="Lv" value={c.level}`。理由：第一行改成四個籌碼，不再是一串字，沒有黏字問題。
3. `client/src/ui/pnl1aPanelKit.test.ts`「摺疊：…量高度時只打開指定的那一個」：舊＝`group("a")` 含 `name="care" open="" data-fold="a"` → 新＝含 `<details class="pnl-fold" open="" data-fold="a"` 且不含 `name="care"`。理由：量高度時不掛 name（第 5 節 2）；平常（`group(undefined)`）兩個都有 `name="care"` 的斷言不變。

沒有重產任何雜湊或快照；沒改 API（不用 `gen:api`）。

## 4. 實測、量值、結束碼

**結束碼**（交件前各跑一次）：`corepack pnpm -C client typecheck` 0；`corepack pnpm -C client test --run` 0（321 檔、4168 passed）；`corepack pnpm -C client build` 0（只有既有的 chunk 大小警告）。沒改 Python（ruff／mypy／lint-imports／pytest 沒跑）。沒跑 `scripts/check.py`。

**實機做法**：自己的 `trpg serve --port 8793`（`TRPG_SAVE_DIR` 在暫存區、`TRPG_DEV_ROUTES=1`、提供 `client/dist`）、`vite --port 5287`（開發頁）、無頭 Chrome `--mute-audio`（除錯埠 9461，自己的 profile），網址帶 `?mute=1`。開發角色 `POST /api/world/characters {"name":"PNL2","weapon":"one_handed_sword","keywords":["ignite","wet"],"race":"human"}`（在主城、Lv 1、開局已完成）。入門期與「不在城鎮」用 `Page.addScriptToEvaluateOnNewDocument` 包 `window.fetch` 補：`limits`（flash／dissolve／oath／race，字照 `opening_limits`）、`growth.starter_note_zh`、`growth.at_service=false`／`can_spend=false`／`blocked_zh="這裡不是城鎮或營火"`、`free_race_change`（程式與後端不動）。結束後用自己的 task 關掉 serve、vite、Chrome，vite 子程序再用自己的 PID 關；8793／5287／9461 都沒在聽。

**(a) 固定區與面板高**（實機，入門期注入）

| 視窗 | 面板（寬×高） | 固定區 | 分頁區鎖高 | 撐高的那一頁 | 捲不捲 |
|---|---|---|---|---|---|
| 1600×900 | 720×552 | 144 | 356 | 整備（打開「溶掉或傳承」，兩招） | 不用捲 |
| 800×600 | 493×414 | 144 | 433 | 同上 | 每頁都要捲（捲動區可視 370，含固定區 144） |

各頁實際高（1600／800）：屬性點 105／105、靈感閃現 175／205、整備（打開重閃）231／251、外觀與種族 96／96。開發頁（一輪營火 fixture 五招）：入門期 1600 鎖 469、Lv 4 在城鎮 448。固定區 144 ≤ 需求的 165。

**分頁列**：成長四頁在 486（800×600 內寬）與 692 都是第 0 級（全名），和需求 3.2 第 7 條「成長四頁 490 全名」一致。

**預設分頁與直開**：入門期按 G＝「屬性點」；點主角卡靈感點＝「靈感閃現」；已開著切到屬性點再點靈感點＝回到「靈感閃現」（1600、800 都是）。開發頁 Lv 4 在城鎮：閃現金底「3」、屬性點金底「2」、預設開閃現。

**浮動卡（6.5.1）**：觸發元素＝固定區警告右邊的 (i)（說明卡＝`service_zh`）。1600×900 與 800×600 都是：滑過約 450 ms 卡片出現 → 分 8 步滑進卡片，卡片還在 → 卡內滾輪：內容短（scrollHeight 44＝clientHeight 44），已在底、沒被關 → 點一下釘住（`.float-card.pinned`）→ 滑鼠移到左上角仍在 → Esc 關掉卡片，面板仍開著。本段的說明卡都是一兩行，沒有長到要捲的卡。

**截圖**（`docs/art/shots/pnl2/`，9 張，全部 ≤ 300 KB）

| # | 檔 | 對應驗收 | 來源 |
|---|---|---|---|
| 1 | `docs/art/shots/pnl2/pnl2_01_tabs_1600.jpg` | 11：四個分頁 2×2（預設屬性點、靈感閃現金鎖、整備打開重閃、外觀與種族） | 實機 1600×900（入門期為注入資料） |
| 2 | `docs/art/shots/pnl2/pnl2_02_tabs_800.jpg` | 11：同上 | 實機 800×600（注入） |
| 3 | `docs/art/shots/pnl2/pnl2_03_fixed_1600_x2.png` | 12：固定區（一行警告＋(i)、四籌碼、分頁列），最近鄰 2 倍 | 實機 1600×900（注入） |
| 4 | `docs/art/shots/pnl2/pnl2_04_lv4_town_dev.jpg` | 13：Lv 4 在城鎮「靈感閃現 3」金底、預設開它、「屬性點 2」金底 | 開發頁（實機未看） |
| 5 | `docs/art/shots/pnl2/pnl2_05_tabbar_growth_dev.png` | 13：成長分頁列 486（入門期／Lv 4 兩列），真 1 倍 | 開發頁（實機未看） |
| 6 | `docs/art/shots/pnl2/pnl2_06_campfire_rules_dev.jpg` | 14：一輪營火的規則籌碼（營火其他區塊照舊） | 開發頁 `RunCampfire`＋fixture（實機未看） |
| 7 | `docs/art/shots/pnl2/pnl2_07_chip_to_flash_1600.jpg` | 主角卡靈感點直開「靈感閃現」 | 實機 1600×900（注入） |
| 8 | `docs/art/shots/pnl2/pnl2_08_float_1600.jpg` | 浮動卡釘住 | 實機 1600×900 |
| 9 | `docs/art/shots/pnl2/pnl2_09_float_800.jpg` | 浮動卡釘住 | 實機 800×600 |

**實機未看**：Lv 4 在城鎮（開發角色 Lv 1）、一輪營火（要先打贏戰鬥才到營火）——都用開發頁以正式元件畫。

## 5. 和樣張不同的地方、共用元件的改動

1. **`PanelTabs`（共用，行為修正，介面不變）**：量高度時目前分頁不再先卸下（量測盒放進 0 高的 `.pnl-measure-wrap`）。原本內容變高 → 捲軸出現 → 寬度變 → 重量 → 卸下目前分頁，分頁裡展開的技能卡、閃現出題畫面、誓約表單會被收掉；成長面板的內容會在頁內長高，所以非改不可。
2. **`Fold`（共用）**：量高度時不掛 `name`。`<details name>` 的原生互斥是整份文件同名的一組，量高度時三種樣子互相關掉，只量到最後一種（實測鎖高 415，打開溶掉時內容 467 超出）。
3. **`PanelTabs` 寬度比較**：拿量的那一次的寬度比，不是拿掛 `ResizeObserver` 時的；鎖高後捲軸才出現時補量一次（實測修前鎖 456、內容 467；修後鎖 469）。
4. 樣張的鎖住提示在閃現頁；入門期第一行「現在不行」用伺服器的 `blocked_zh`（不在城鎮以外的原因——有遭遇、戰鬥中——也照字顯示）；舊的「你現在在這裡，可以使用。」與「現在不能花點：…」兩行合成這一行。
5. 重閃摺疊展開後照現行內容：原段落＋「還沒有可以重閃的技能（要先閃現過，或有完整技能）。」原句仍在（和右邊標籤重複；樣張是虛線空狀態）。
6. 開發角色沒有種族時（舊角色）外觀列不出現（照現行 `LookChangeLine` 的規則）。

## 6. 待 PM 決定

1. **「功能列『靈感 N』直開」的入口**：功能列「成長（G）」照預設分頁（能花靈感時閃現本來就是第一頁、會被選到；入門期要落在屬性點，所以 G 不強制開閃現）；直開做在 HUD 主角卡的靈感點籌碼（原本不能點，現在是按鈕，說明卡多「（點了打開靈感閃現）」）。若「功能列」指的是別的地方請指明。
2. **入門期點靈感點也開「靈感閃現」**（整頁鎖住，看到鎖住提示）；要不要入門期改開預設頁。
3. **整備摺疊右邊標籤只做了需求列的**（重閃沒有可重閃、溶掉入門期、誓約入門期）；有可重閃的技能、已立誓、誓約冷卻中時不掛標籤。要不要加（例「立誓中：〔名〕」）。
4. **溶掉或傳承入門期把「選這招」停用**（原本可按、送出時伺服器擋）；說明在右邊鎖標籤。
5. **「主城隨時免費」標籤用細框（中性）**，不是綠色正面標籤；需求沒寫色。
6. **800×600 每一頁都要捲**：實機面板 493×414（開發入口 60px 標題列），固定區 144 後捲動區只剩約 226；最高的整備（溶掉打開）433。需求 3.2 第 1 條「盡量在一屏內」做不到，交美術 PM 看圖。
7. **面板高度＝最高那一頁**讓 1600 的屬性點、外觀頁下方空很多（1600 面板 552 高，屬性點頁只用 105）；照規則做，交美術 PM 看。
8. **重閃摺疊裡的空狀態原句**和右邊標籤重複（第 5 節 5）；要不要拿掉原句改虛線空狀態（改到 `CampfireSkillCare`，一輪營火也會變）。
9. **共用 scratchpad 被別的 agent 覆寫**（`cdp.mjs`、9347 埠 Chrome）：建議派工時寫明各 agent 用 scratchpad 子資料夾與不同除錯埠（上手筆記第 99 點）。
