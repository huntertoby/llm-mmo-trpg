# Phase 6T-1b 報告：郵寄前端＋玩法 PM 對 6T-1a 的兩項決定

實作者，2026-11-05。規格：開發 PM 派工 prompt（6T-1b）；`docs/archive/phases/Phase6T-1a報告.md` 第 6、7 節；`docs/玩法PM交接.md` 3.5
（723b9ebe 的 6T-1a 代決）；`docs/art/郵寄外觀.md`（樣張 `docs/art/shots/misc/mail.png`、`docs/art/sample/mail.html`）；`docs/design/08-裝備.md` 8.13、8.16。
分支開工時先 `git merge main`（含 350c0f36：loot 測試固定主手同大類、client fixture 補 `tradable`）。

沒碰：戰鬥畫面的 `rowLayout.ts`、`badgeLayout.ts`、`heightMark.ts`、`heightTag.ts`、`unitSprite.ts`、`BattleRenderer.ts`；紙娃娃墨線部件與頭像繪製
（`inkDoll`／`inkGear`／`portrait.ts` 一行都沒改）。**郵差的 `mailbag` 配件這段沒做**，郵差只用現有部件：`coat` 換區域色、`cap`，荒原加 `soot`
（頭像照 6T-1a 的人設卡）。**`mailbag` 等 QK（Q 版回歸）定案後再補**。

## 1. 每項做了什麼

### A1 主手可以換上別大類的武器（玩法 PM 決定第 5 項；只在大世界）

- `roguelite/gear.py`：`equip_swap`／`equip`／`equip_notes`／`weapon_swap_prompt` 多一個關鍵字參數 `cross_class`（預設 `False`）。
  **roguelite 原型照 07 7.1 不變**（沒傳就照舊拒絕「主手只能換成同一大類的武器」，`test_roguelite_still_same_class` 檢查）。
- `world/gear.py` 的 `apply_equip` 傳 `cross_class=True`：城鎮與營火可以換上別大類的主手。
- **換上後那些武器技暫時不能用＝戰鬥裡不出現**（選「不出現」：引擎開戰時 `_check_loadouts` 會拒絕武器不相容的技能，灰掉要改引擎；
  不出現只在大世界組出場設定時過濾）：
  - `world/weapon_mix.py` 新增 `class_blocked`、`usable_skills`、`hero_skills`：`weapon_req` 是別大類的招不放進技能列，順序不變；
    技能本身一直留在 `hero.skills`，換回同大類就全部回來。
  - `world/battle.py` 的 `_hero_spawn` 用 `hero_skills`；`world/shadows.py` 的 `shadow_spawn`（朋友的影子、循環賽）同樣過濾。
- 掉落判斷「同大類」看目前裝備的主手：`weapon_class_of` 本來就讀 `hero.weapon`（換上後就是新武器），補 docstring 與測試。
- API：
  - `BagItemView.can_equip`：拿掉 6T-1a「別大類一律換不上」的覆寫；卡片照舊有 `cross_class_zh`、`cross_class_lost_zh`。
  - 背包裝備卡的比較（`gear_candidate`）在大世界傳 `cross_class=True`（「主角的武器換成〈名〉」照常出現）。
  - `WorldCharacterView` 多 `weapon_blocked`（暫時不能用的技能 ID）與 `weapon_blocked_zh`（「主手是近戰武器：〈點名〉暫時不能用」）；
    技能面板（K）顯示這一行並把那些招灰掉。
- 換上前跳確認：前端（見 B4）。伺服器沒有加「確認旗標」（確認只是畫面流程，換裝規則照決定是「可以換」）。

### A2 過期的信自動退回寄件人（玩法 PM 決定第 6 項）

- **拿掉 `mail_reclaim`**（動作、事件 `MailReclaimedEvent`、API `POST …/mail/{letter}/reclaim`、測試一起改）。
- 過期（寄出 3 天沒領）的信：收件人看不到也領不了（同 6T-1a），**寄件人的「退件・過期」分頁直接列出、和被拒收的一樣按「領取」**
  （`action: "claim"`、`status_zh: 過期退回`），不受 20 封上限，不用另外取回；金幣的稅不退。
- 做法：那封信的資料還記在收件人的信箱（不另寫系統日誌、不在沒有動作時改別人的存檔），寄件人 `mail_claim` 時那一筆日誌
  **同時改兩人**（`counterpart`＝收件人，從收件人身上拿掉）。`mail_claim` 因此進了 `PAIR_HANDLERS`：
  領自己信箱裡的信只改自己（`other` 是 `None`，日誌不寫 `counterpart`）；`step._pair` 不再強制要有另一個角色，由各處理自己拒絕。
- 交易帳的 `status` 沿用 6T-1a 的 `reclaimed`（＝過期退回、寄件人領回；世界格式不變）。
- 事件句：「領了過期退回來的信：…」。郵差台詞照舊用 `returned`。
- 底下的說明文字照第 6 項改，移到內容檔 `world/trade.yaml` 的 `mail.texts`（`footer_zh`、`send_note_zh`、`season_warning_zh`，`{days}` 代天數）：
  - 收件匣／退件：「信只能在城鎮的郵差這裡領；3 天沒領會自動退回寄件人，季末清掉。」
  - 寄東西：「3 天內沒人領，會自動退回給你（跑腿費不退）；季末沒領的信會清掉。」（`MailView.send_note_zh`，新欄位）

### B1、B2 郵差與郵筒（內容＋畫面）

- 內容：
  - `FacilityKind` 加 `post`（郵寄）；`FieldFacility` 加 `postman: bool`（站在這格的是這區的郵差；外觀與名字照 `world/trade.yaml` 的人設卡，
    不另寫 `figure`，避免兩份頭像資料）。載入時檢查（`library._check_post_facilities`）：`post` 只能放在有郵差的城鎮室外圖、每位郵差恰好一個站位。
  - `ObjectLook` 加 `postbox`：郵筒＝`{kind: low_wall, look: postbox}`（**規則和 `low_wall` 一樣**：擋路、不可破壞）。
  - 三張城鎮圖各放一個郵筒與郵差站位，都在主要通道旁邊、不擋路（`trpg content check` 的連通性通過）：
    霧渡鎮郵筒 [19,10]、阿信 [20,10]（主街南側）；餘燼集郵筒 [17,10]、灰鴿 [18,10]（主街南側、大水缸東邊）；
    樞島郵筒 [22,13]、白鷺 [23,13]（往鐵匠鋪那一列的南邊）。郵筒那格也是 `post` 設施＝**走到郵筒旁邊也能開面板**。
  - API：`FieldFacilityView` 多 `name_zh`、`postman`；郵差那格的 `figure` 由人設卡的頭像填。
- 畫面：
  - 郵差：設施的站著的人（同主城傭兵管事的做法），名字「阿信／灰鴿／白鷺」，說明卡「郵差 阿信」，郵筒格「郵筒」。
  - 「✉」泡泡：頭頂標記多一種 `post`、`alert: "mail"`（`fieldPeople.ts` 的 `postMarks`，資料是 `WorldView.mail`），
    做法同任務「！」：同一個 `field-alert` 框、上下晃（減少動態時不晃），裡面畫樣張的信封（`FieldHeads.tsx` 的 `MailGlyph`）。沒有信時不畫。
  - 郵筒：`render/objectArt.ts` 的 `drawPostbox`（方柱、斜頂、投信口、信封牌、腳座，墨線畫法），三種材質依區域
    （`POSTBOX_MATERIALS`：雲嶺青石帶苔、荒原廢鐵帶鉚釘與鏽痕、主城白石金邊加晶尖）；經 `interiorArt.drawFurniture` 的 `postbox`
    外觀接進場景（材質照地圖的 `region`）。高度 30.4px（約人物 50px 的 0.6 倍）。
  - 點郵差、點「✉」、走到郵筒或郵差旁邊互動，都開 HUD 面板 `mail`。

### B3 郵寄面板 `client/src/world/MailPanel.tsx`

- 共用彈窗（HUD 面板的 `PopupFrame`，深藍金框、區域點綴；在主角卡右邊、不蓋 HUD 主角卡）；上方郵差頭像與這次的一句話，
  三個分頁「寄東西／收件匣 N／退件・過期 N」（有信時先開收件匣）。純函式在 `mailModel.ts`。
- 寄東西（照樣張 ②）：
  - 1 寄給誰：`/mail/recipients`；收不了的（例：「還不到 3 級」）照列、寫原因。
  - 2 要寄的東西：3 格附件（點了拿掉）＋背包縮圖列；**綁定的灰掉並標原因**（伺服器的 `bound_zh`：穿過／獨特／首殺；
    其他不能寄的寫「不能寄」，例：染料）。物品一次點進 1 個（不超過持有數）、裝備一件一格。
  - 3 金幣：數字框＋金幣圖示；**稅與實收照 `/mail/quote` 即時顯示**（草稿一改就問，120ms 防抖，舊回應丟掉）。
  - 4 留言：一行（`note_max` 40 字）＋字數。
  - 寄出前檢查：**伺服器的檢查全部列出（✗ 原因）、全過才亮「寄出」**；下方小字照第 6 項（過期自動退回）。
- 收件匣（照樣張 ③）：每封一列（寄件人、寄自哪裡・剩幾天、留言、附件、金幣「已扣跑腿費」）；「領取」「退回」；
  **背包滿時「領取」灰掉並寫原因**（伺服器的 `problem_zh`「背包放不下，先整理背包」）。
- 退件・過期：同樣式（「被拒收退回／過期退回・寄自…」），按「領取」。
- 寄出、領取、退回之後重抓世界畫面（金幣、背包、「✉」）。郵差台詞與說明句全部從伺服器來（`world/trade.yaml`），前端沒寫死。
- 物品圖示：G10 物品圖示還沒移植，非裝備的附件用「名稱＋×個數」的小牌；裝備用 `GearIcon`（背包裝備卡的外觀）。

### B4 裝備卡（別大類武器）

- 背包的裝備卡下方兩行（伺服器的字）：「別大類：可交易・可分解・可賣」「換上後不能用：〈招名〉」（`BagScreen.tsx` 的 `CrossClassLines`）。
- 按「換上」先跳確認框（`CrossClassConfirm`）：「「〈名〉」是別大類的武器。換上後不能用：〈招名〉（換回同大類就恢復）。〈縮放屬性提示〉要換上嗎？」
  縮放屬性不同的舊確認（`WeaponSwapConfirm`）併在同一句，不會跳兩次。

## 2. 版號

| 項目 | 舊 → 新 | 說明 |
|---|---|---|
| `WORLD_RULES_VERSION` | 18 → 19 | docstring 補「19（6T-1b）」：主手可換別大類（18 的程式拒絕這種換裝）、過期的信改成照退件領、拿掉 `mail_reclaim` |
| 世界日誌 `trpg-wlog/9` | 不變 | 欄位沒變；`mail_claim` 可能帶 `counterpart`（過期退回那種）。**`mail_reclaim` 動作拿掉了**：6T-1a 以後如果有人用 API 取回過、日誌裡有 `mail_reclaim` 那一行，讀不進來（見待決 3） |
| 角色 `trpg-char/9`、世界 `trpg-world/4` | 不變 | 沒有新欄位（`MailLetter`、`TradeRecord` 的值沿用） |
| 內容 | — | `FacilityKind` 加 `post`、`ObjectLook` 加 `postbox`、`FieldFacility.postman`、`MailRules.texts`（內容 digest 會變） |

`save.py` 模組說明加「Phase 6T-1b」一段；`state.py`、`trade.py`、`trade_actions.py`、`step.py`、`gear.py`、`weapon_mix.py` 的 docstring 跟著改。
存檔欄位沒變，`tests/test_architecture.py` 照樣在相關測試裡跑過。

## 3. 快照變動

- `uv run python -m tests.skillgen.test_refactor_3wr2`：結束碼 0，重產後**內容沒有變**（git 只看到 Windows 換行差異，已 `git checkout` 還原）。
- `UPDATE_CLI_SNAPSHOTS=1 uv run pytest -m "slow or not slow" tests/cli/test_output_snapshots.py`：25 passed，**快照檔沒有變**
  （CLI 快照不含大世界；第一次跑時我剛好在改 `trade.yaml`，YAML 壞了 21 個失敗，修好後整組重跑一次全過、檔案不變）。
- `client/openapi.json`、`client/src/api/schema.d.ts` 重產：拿掉 `…/reclaim` 路由；新增 `WorldCharacterView.weapon_blocked`／`weapon_blocked_zh`、
  `FieldFacilityView.name_zh`／`postman`、`MailView.send_note_zh`；說明文字的小改。
- 實地地圖的「規則內容不變」雜湊（`tests/content/test_field_buildings.py`）：
  - 雜湊排除 `postman`（只畫），其他圖不變。
  - 霧渡鎮、餘燼集、樞島更新：只多了郵筒（`low_wall`）與 `post` 設施（拿掉這兩樣後，霧渡鎮、餘燼集的雜湊和舊值完全一樣）。
  - **樞島的舊值在 main 上本來就不對**：RT-5b（91be1e31）移了石碑和守印人，沒更新雜湊。新值包含 RT-5b 與 6T-1b 兩次改動（見待決 5）。
- 其他跟著改的測試：`test_capital_field`（主城室外設施多 `post`）、`test_ashen_fields`（餘燼集多 `post`）、
  `test_world_field_buildings`（霧渡鎮的物件外觀只有郵筒）、`test_world_loot_api`（只補註解：別大類也換得上，「城鎮與營火」斷言照舊成立）。

## 4. 截圖（`docs/art/`，全部是正式遊戲畫面）

**截圖方式**
- 無頭 Chrome（`--headless=new --mute-audio`，網址加 `?mute=1`），用 CDP `Emulation.setDeviceMetricsOverride` 把視窗真的設成檔名上的尺寸（device scale 1）。
- 正式遊戲（`trpg serve` 8123，存檔在 `scratchpad/mailsaves`，用 session 暫存資料夾的 `seed_mail.py` 建好 6 個角色與信件；沒有攔 API、沒有假資料）。
  每張拍之前先關掉開場對話框（含主城的「醒來」）。
- 每組只拍一次全畫面，`_zoom` 從同一張裁出放大（同一幀）。
- 交件前用 `file` 核對：22 張全圖的實際尺寸都和檔名一致（1600×900 11 張、800×600 11 張）。另有 22 張 `_zoom`、2 張浮動卡。

| 內容 | 1600×900 | 800×600 |
|---|---|---|
| 霧渡鎮郵差阿信＋郵筒（有「✉」） | `6t1b_town_mist_mail_1600(.jpg/_zoom)` | `6t1b_town_mist_mail_800` |
| 霧渡鎮（沒有「✉」，角色小魚沒有信） | `6t1b_town_mist_nomail_1600` | `6t1b_town_mist_nomail_800` |
| 餘燼集灰鴿＋廢鐵郵筒（有「✉」） | `6t1b_town_ember_1600` | `6t1b_town_ember_800` |
| 樞島白鷺＋白石郵筒（有「✉」） | `6t1b_town_capital_1600` | `6t1b_town_capital_800` |
| 面板：收件匣 | `6t1b_panel_inbox_1600` | `6t1b_panel_inbox_800` |
| 面板：寄東西 | `6t1b_panel_send_1600` | `6t1b_panel_send_800` |
| 面板：退件・過期（被拒收、過期各一封，都是「領取」） | `6t1b_panel_returned_1600` | `6t1b_panel_returned_800` |
| 寄件中：選了小魚、附件 3 格、金幣 200、留言；綁定物灰掉（穿過、獨特、染料不能寄）；「跑腿費 10%：−20　對方實收 180」；檢查全過、「寄出」亮 | `6t1b_send_live_1600` | `6t1b_send_live_800` |
| 收件匣背包滿：「領取」灰掉、「背包放不下，先整理背包」 | `6t1b_inbox_bagfull_1600` | `6t1b_inbox_bagfull_800` |
| 別大類武器的卡片（兩行字） | `6t1b_crossclass_card_1600` | `6t1b_crossclass_card_800` |
| 換裝確認框 | `6t1b_crossclass_confirm_1600` | `6t1b_crossclass_confirm_800` |
| 6.5.1 浮動卡釘住 | `6t1b_float_1600_pinned` | `6t1b_float_800_pinned` |

（每一張都另有同名 `_zoom.jpg`。）

**我自己看過的**
- 三區郵筒材質不同（青石帶苔／廢鐵帶鉚釘鏽痕／白石金邊藍頂加晶尖），高度到郵差胸口，比人矮；郵差戴皮帽、短外套照區域色；灰鴿綠膚。
- 「✉」在郵差頭上、白底圓角框，和任務「！」同一層、同大小級；沒有信的角色看不到。
- 800 寬時面板在主角卡右邊，寄東西疊成一欄、面板內捲動。

## 5. 6.5.1 浮動卡實測（郵寄面板「寄東西」裡灰掉的「靛青染料：不能寄」說明卡）

| 步驟 | 1600×900 | 800×600 |
|---|---|---|
| 滑過 → 卡片出現 | ✓（貼在格子上方 337～373） | ✓（283～320） |
| 滑進卡片後不關 | ✓ | ✓ |
| 卡內捲動後不關 | ✓（卡片 28px 沒有可捲的內容，只確認不關） | ✓ |
| 點一下釘住 → 滑出去不關 | ✓ | ✓ |
| Esc 關閉 | ✓ | ✓ |

紀錄：`scratchpad/t1b/float.log`（不 commit）。

## 6. 各結束碼

| 指令 | 結束碼 |
|---|---|
| `ruff check .`、`ruff format --check .` | 0、0 |
| `mypy src` | 0（540 檔） |
| `lint-imports` | 0（13 kept） |
| `trpg content check` | 0 |
| `trpg battle --map swamp --seed 7 --log-json …` ＋ `trpg battle replay …` | 0、0（88 個動作、313 個事件一致） |
| `pytest -n 8 tests/world tests/roguelite tests/api tests/server tests/test_architecture.py`（server commit 前） | 0（2159 passed、1 skipped；只有當時還沒重產的 OpenAPI 快照 1 個失敗，重產後過） |
| `pytest -n 8 tests/world tests/roguelite tests/api tests/server tests/content tests/test_architecture.py`（最後一個程式 commit 之後） | 0（4860 passed、1 skipped） |
| `python -m tests.skillgen.test_refactor_3wr2` | 0 |
| CLI 快照（含 slow，UPDATE） | 0（25 passed） |
| client 全部 vitest（含修好的 `postMarks`，最後一個程式 commit 的內容） | 0（260 個檔、2986 項） |
| `corepack pnpm -C client build`（含 `tsc --noEmit`） | 0（只有原本就有的 chunk 大小提醒） |
| 排版煙霧檢查 `/?dev=1&anim=0.1&mute=1`（`__layoutSmoke.runCase('6T-1b')`） | 1600×900、1040×624、800×600 全 PASS |

新測試：`tests/world/test_cross_class_6t1b.py`（5：換上別大類、roguelite 照舊、戰鬥裡沒有那些招（出場技能列與 `legal_actions`）且換回就恢復、
戰鬥與世界日誌重播一致、`usable_skills`）；`tests/world/test_trade.py`（過期自動退回、重播 2 項改／加）；`tests/api/test_world_mail_api.py`
（郵差站位與郵筒、`send_note_zh`、別大類換上後 `weapon_blocked`）；`client/src/world/mail6t1b.test.ts`（13）。

## 7. 待 PM 決定

1. **「戰鬥裡不出現」而不是「灰掉」**：引擎開戰時會拒絕武器不相容的技能，灰掉要動引擎；目前大世界組出場設定時過濾掉，
   技能面板（K）把那些招灰掉並寫「主手是〇〇武器：〈招〉暫時不能用」。
2. **過期退回的「自動」是畫面與規則上的**：寄件人的退件分頁直接出現、照退件領，不用另外取回；資料在寄件人領的那一筆才從收件人身上拿掉
   （沒有動作時不改別人的存檔，重播只靠日誌）。結果和「信真的移回寄件人信箱」對玩家一樣；如果要求資料也當下移動，要另做系統日誌。
3. **拿掉 `mail_reclaim`**：6T-1a 合併到現在如果有人用 API 取回過，那份日誌那一行讀不進來（測試季、沒有前端入口，風險很小）。
   規則版號已升 19（舊日誌本來就標成不能重播）；要保險可以加回一個只讀不執行的舊動作。
4. **郵寄面板的頭像**：寄給誰、收件匣的玩家角色目前是通用剪影（伺服器的 `MailRecipientView`、`LetterView` 沒有玩家頭像資料）。
   要照樣張畫臉，需要伺服器補玩家角色的頭像欄位。
5. **樞島的地圖規則雜湊**：main 上 RT-5b 改了樞島（石碑、守印人）卻沒更新 `test_field_buildings.py` 的雜湊，這個測試在 main 上就是紅的；
   我把新值設成「RT-5b＋6T-1b」之後的值並寫了註解，請 PM 確認 RT-5b 的改動本來就是要的。
6. **物品圖示**：G10 物品圖示還沒移植，非裝備的附件用「名稱＋×個數」小牌；移植後換成圖示。
7. **`mailbag`**：照規格這段沒做，等 QK 定案後補（郵差只用 `coat`＋`cap`，荒原加 `soot`）。
8. **郵差站位**：霧渡鎮 [20,10]、餘燼集 [18,10]、樞島 [23,13]（郵筒在西邊相鄰一格）；美術 PM 看截圖後可以再挪。
9. 寄件一次點進 1 個物品（點多次加多個，不超過持有數）；整疊一次點進來要另做數量輸入。

## 8. 複雜度 noqa

沒有新增 C901／PLR0911／PLR0912／PLR0915。新增 `PLR0917`（位置參數 6 個）一處：`trade._mail_claim`（和 `PairHandler` 分派表同簽名，同 6T-1a 的其他三個）。

## 9. 啟動過的程序與 PID

- 第一輪：`trpg serve --port 8123`（`TRPG_SAVE_DIR=scratchpad/mailsaves`）python PID 34732；無頭 Chrome（CDP 9781，`--mute-audio`，
  profile 在 `scratchpad/t1b/chrome`）PID 69260。
- 第二輪（重建存檔、重拍城鎮 8 張：第一輪拍城鎮時主角剛好站在郵差旁邊、「✉」壓到主角；800 寬時郵差在右緣 HUD 底下，改成先往東走 4 格再拍）：
  `trpg serve --port 8123` python PID 10252；無頭 Chrome PID 42892。
- 結束時只用這些 PID 關掉（`taskkill /F /T /PID …`），之後確認 8123、9781 都沒有在聽。沒用 8000、8001、8010；沒碰 `tmp_x`、`saves/`。
  暫存都在 `scratchpad/`（不 commit）；建存檔的 `seed_mail.py` 放在 session 暫存資料夾（放在 worktree 裡會被 `ruff check .` 掃到）。
