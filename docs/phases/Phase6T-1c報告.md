# Phase 6T-1c 報告：郵寄畫面驗收修正＋寄件填數量＋郵差分頁台詞

實作者，2026-11-05。依據：開發 PM 派工 prompt（6T-1c）、`docs/archive/art/6T-1b檢查.md`（美術 PM 驗收）、`docs/玩法PM交接.md` 3.5（acfc999f）、
玩法 PM 共用筆記「玩法PM-郵差內容文字.md」第 4 節（開發 PM 補充轉來的分頁台詞）。

沒碰：戰鬥畫面（`rowLayout.ts`、`badgeLayout.ts`、`heightMark.ts`、`unitSprite.ts`、`BattleRenderer.ts`、浮動卡元件、目標預覽）、
獸耳族（`races.yaml`、`engine/ai/race.py`、situations、雲嶺／荒原實地地圖）、`WORLD_RULES_VERSION`、紙娃娃部件（`inkDoll`／`inkGear`／`inkArmor`／`inkRace` 一行都沒改）。

## 1. 每項做了什麼

### 必修

1. **餘燼集郵差的 soot**
   - 頭像：只調 `render/portrait.ts` 現有 `soot` 的參數：顏色 `rgba(40,30,25,0.35)` → `rgba(34,24,18,0.62)`（加深），橢圓 2.4×1.2 → 3.6×1.9（加大）。56px 頭像原尺寸看得到臉頰上的黑灰。
   - 場上：**soot 本來就只畫在頭像上**（`npcLook.EXTRA_HEAD` 沒有 soot，`NPC頭像.md` 第 4 節的表是「不畫」）。場上要有 soot 得新增或修改紙娃娃部件，照派工不做，見待決 1。
   - 補拍：`6t1c_town_ember_*`（場上）、`6t1c_panel_ember_*`（面板頭像）。
2. **背包滿時的按鈕位置**：信件卡片從 flex 自動換行改成 grid。
   - 1600 寬：頭像｜寄件人與留言｜附件｜按鈕，四欄。
   - 800 寬：容器寬度小於 560px 時改三欄，按鈕那格佔滿第二列、靠左。
   - 「領取」「退回」包在固定的一列（`.mail-letter-btns`），不能領的原因放在這一列下面，按鈕不再跟著原因移位。
   - 正常信件和背包滿的信，按鈕位置相同（1600：x 1001，靠右；800：x 176，在左下）。
3. **A：面板開著時藏起「✉」**：`WorldField` 新增 `hideMail` 參數；`WorldScreen` 在郵寄面板開著時傳 `true`，`headMarks` 就拿不到 `mail`。郵差站位沒動。
   - 1600：`6t1c_mailhide_before_1600`（主角站在郵差北邊，「✉」蓋到主角頭）對照 `6t1c_mailhide_1600`（面板開著，「✉」不見了）。
   - 800：面板會蓋住郵差那一帶，截圖看不出差別。DOM 檢查面板開著時 `field-mail-glyph` 是 `null`（`out/shots_800.json` 的 `glyphAfter`），見待決 2。
4. **B：非裝備附件的小牌和裝備圖示格同高**
   - `.mail-thing` 加 `min-height: 32px`，和 `GearIcon` 的 32px 一樣。
   - 背包格改成 `inline-flex`：原本裝備格會多出 4px 的行內基線空隙，量到 44 對 40。
   - 實測背包列每一格都是 40px，附件格都是 44px（`shots_1600.json` 的 `slots`）。
   - 信上的物品小牌（`.mail-thing-chip`）也是 32px 高、有框。
   - **這是過渡做法**：G10 物品圖示移植後，要把小牌換成物品圖示。
5. **C：通用剪影**
   - `drawSilhouette` 拿掉「?」。
   - 「寄給誰」、收件匣、退件三處的剪影，底色都改用**所在城鎮（郵差）的區域色**。「寄給誰」原本用的是對方所在區的顏色，各列顏色不一樣（見待決 3）。
6. **頭像戴帽**：三位郵差的頭像改成 `gear.head: {kind: cap, material: leather}`，也就是紙娃娃現有的皮帽頭部裝備，場上本來就畫這頂。
   - 拿掉頭像專用的深色 `cap` 配件：它是深棕色的帽頂，和深色頭髮混在一起，看起來像沒戴帽。
   - 場上外觀不變：`portraitGear` 原本就把 `cap` 配件換成同一頂皮帽。只改了內容檔 `content/world/trade.yaml`，沒新增或修改部件。

### 小修

7. **send_live_800**
   - `.world-mail button.primary:hover` 改成亮一階的 `#4d6cb3`。原因是共用的 `button:hover` 會把主要按鈕蓋成深灰 `#36364a`。實測滑過時的背景是 `rgb(77,108,179)`。
   - 說明小字「3 天內沒人領…季末沒領的信會清掉」移到「寄出」左邊、同一列。
   - 「寄出」**拿掉說明卡**：說明卡貼在按鈕上方，移開小字後換成蓋到「寄出前檢查」那一行。不能寄的原因本來就全列在檢查框裡；按鈕的 `aria-label` 保留原本的說明。
   - 實測滑過「寄出」時沒有任何浮動卡（`hover.tip` 為空）。
8. **panel_send_800**：容器寬度小於 560px 時，「寄給誰」名單改成 `max-height: none; overflow: visible`，只剩面板一層捲動。實測 `maxH: none`、高度等於內容高度。
9. **panel_inbox_800、panel_returned_800**：800 寬時卡片縮矮：
   - 內距 8→5、列距 8→4
   - 頭像 44→36
   - 按鈕上下內距縮小
   - 信件間距 8→6

   實測第二封的按鈕底在 y 458，面板內容底約在 y 497，完整露出來。
10. **郵筒紋路加深一階**（`objectArt.drawPostbox`）
    - 青石的苔：細線改成四塊深綠苔斑，加墨線收邊和亮綠點。
    - 廢鐵的鉚釘：半徑 1.3→2.1、顏色變亮 `#e4e4ea`、加墨線。
    - 鏽痕：顏色變亮、線變粗。
    - 主城白石沒改。

### 玩法 PM 的決定（acfc999f）

11. **寄件填數量**
    - 伺服器：`MailSendAction.items` 本來就是「物品 → 個數」，`/mail/quote` 和 `/mail/send` 也已經檢查「個數至少 1」「背包裡只有 N 個」。**伺服器規則沒改**，只補 API 測試 `test_send_stack_count_6t1c`：quote 寄 4 個通過、寄 6 個報 `not_enough`、寄出後背包扣 4、收件匣照個數。
    - 前端：可堆疊的附件格改成「名稱＋−＋數字框＋＋／上限＋×」。
      - 上限是背包裡的數量；數量夾在 1～上限之間（`mailModel.setDraftCount`）。
      - 數字框可以直接打字，離開或按 Enter 時夾回範圍內。
      - 點背包格照舊每次加 1 個；× 拿掉整格。
      - 裝備照舊一次 1 件、點了就拿掉。
    - 截圖：`6t1c_send_count_*`。粗料先按 ＋ 到 3，再打字改成 4（上限 4）；小回復藥 1／1，＋ 是灰的；旁邊放一件裝備，對照 B。

### 郵差依分頁換台詞

- 內容：`PostmanLines` 加四個選填欄位 `tab_send`、`tab_inbox`、`tab_inbox_empty`、`tab_returned`。三位郵差照玩法 PM 第 4 節的定稿填好（含空收件匣那句）。
- 退回規則（`PostmanLines.tab_lines`）：
  - 沒填的分頁，退回打開面板時的那句（`open`／`has_mail`）。
  - 空收件匣沒填時，用「寄東西」那句。
- API：`MailView.tab_lines`（`send`、`inbox`、`inbox_empty`、`returned`，伺服器已經套好退回規則；沒有郵差時為 `null`）。
- 前端：`mailModel.tabSay` 依序決定郵差說哪一句：
  1. 剛寄出、剛領了退件時的那句（換分頁就清掉）
  2. 等級不到時照舊用 `line_zh`
  3. 照分頁用 `tab_lines`；收件匣沒有信時用 `inbox_empty`
- 測試：`test_tab_lines_6t1c`（API 輸出、選填欄位的退回規則）；vitest「6T-1c 郵差照分頁換台詞」兩項。
- 截圖台詞：
  - 阿信：寄東西「要寄東西啦？…」、收件匣「有你的信啦，快來拿！」、退件「對方一直沒來拿的，都退回來啦。」
  - 小魚的空收件匣：「還沒有你的信啦。」
  - 灰鴿的收件匣：「你的。拿去。」

## 2. 截圖（`docs/art/`，全部是正式遊戲畫面）

**截圖方式**
- 無頭 Chrome，加 `--headless=new --mute-audio`，網址加 `?mute=1`。用 CDP `Emulation.setDeviceMetricsOverride` 把視窗真的設成檔名上的尺寸（device scale 1）。
- 伺服器：`scratchpad/t1c/serve.py`，埠 8124，Mock LLM，掛 worktree 的 `client/dist`。
- 存檔：session scratchpad 的 `t1c/mailsaves`，用 `t1c/seed.py`（沿用 6T-1b 的 `seed_mail.py`，改了路徑）建好 6 個角色和信件。沒有攔 API，也沒有假資料。
- 每張拍之前，先關掉升級和開場對話框。
- 每組只拍一次全畫面，`_zoom` 從同一幀裁出、最近鄰放大。
- 交件前用 `file` 核對：24 張全圖的實際尺寸都和檔名一致（1600×900 12 張、800×600 12 張）。另有 24 張 `_zoom`、2 張浮動卡，共 50 張。

| 內容 | 1600×900 | 800×600 |
|---|---|---|
| 必修 1：餘燼集灰鴿在場上（皮帽；soot 只在頭像上，見待決 1）＋廢鐵郵筒（小修 10） | `6t1c_town_ember_1600` | `6t1c_town_ember_800` |
| 必修 1：面板頭像（皮帽＋加深的 soot）、灰鴿收件匣台詞 | `6t1c_panel_ember_1600` | `6t1c_panel_ember_800` |
| 必修 2：背包滿，按鈕位置和正常信件相同，原因寫在按鈕下面 | `6t1c_inbox_bagfull_1600` | `6t1c_inbox_bagfull_800` |
| 收件匣（小修 9：800 寬時第二封的按鈕完整露出；C 剪影；戴帽頭像） | `6t1c_panel_inbox_1600` | `6t1c_panel_inbox_800` |
| 寄東西（小修 8：800 寬時名單不限高；寄東西台詞） | `6t1c_panel_send_1600` | `6t1c_panel_send_800` |
| 退件・過期（小修 9；退件台詞） | `6t1c_panel_returned_1600` | `6t1c_panel_returned_800` |
| A：主角站在郵差北邊、面板還沒開（「✉」蓋到主角頭） | `6t1c_mailhide_before_1600` | `6t1c_mailhide_before_800` |
| A：面板開著，「✉」藏起來 | `6t1c_mailhide_1600` | `6t1c_mailhide_800`（面板蓋住郵差，見待決 2） |
| 寄件填數量＋B（小牌與裝備格同高） | `6t1c_send_count_1600` | `6t1c_send_count_800` |
| 小修 7：滑過「寄出」（亮一階、沒有說明卡、說明小字沒被蓋到） | `6t1c_send_hover_1600` | `6t1c_send_hover_800` |
| 小修 10：青石郵筒的苔 | `6t1c_postbox_mist_1600` | `6t1c_postbox_mist_800` |
| 空收件匣的台詞（小魚：「還沒有你的信啦。」） | `6t1c_inbox_empty_1600` | `6t1c_inbox_empty_800` |
| 6.5.1 浮動卡釘住 | `6t1c_float_1600_pinned` | `6t1c_float_800_pinned` |

（除了浮動卡，每張都另有同名 `_zoom.jpg`。）

## 3. 6.5.1 浮動卡實測（附件格「＋」的說明卡「多寄 1 個」，6T-1c 新增）

| 步驟 | 1600×900 | 800×600 |
|---|---|---|
| 滑過 → 卡片出現 | ✓（貼在按鈕上方 281～317） | ✓（284～320） |
| 滑進卡片後不關 | ✓ | ✓ |
| 卡內捲動後不關 | ✓（卡片只有一行、沒有可捲的內容，只確認不關） | ✓ |
| 點一下釘住 → 滑出去不關 | ✓ | ✓ |
| Esc 關閉（面板還開著） | ✓ | ✓ |

紀錄：`scratchpad/t1c/float1600.txt`、`float800.txt`（不 commit）。

## 4. 各結束碼

| 指令 | 結束碼 |
|---|---|
| `ruff check .`、`ruff format --check .` | 0、0 |
| `mypy src` | 0（540 檔） |
| `lint-imports` | 0（13 kept） |
| `trpg content check` | 0 |
| `trpg battle --map swamp --seed 7 --log-json …` ＋ `trpg battle replay …` | 0、0（88 個動作、313 個事件一致；每次 commit 前都跑） |
| `pytest -n 8 tests/api/test_world_mail_api.py tests/api/test_openapi_snapshot.py tests/world/test_trade.py tests/content`（伺服器 commit 前） | 0（2728 passed） |
| `pytest -n 8 tests/api/test_world_mail_api.py tests/content/test_field_buildings.py tests/world/test_weapon_mix.py tests/world/test_trade.py tests/api/test_openapi_snapshot.py`（改郵差頭像之後） | 0（67 passed） |
| client 全部 vitest | 0（262 個檔、3011 項） |
| `corepack pnpm -C client build`（含 `tsc --noEmit`） | 0（只有原本就有的 chunk 大小提醒） |
| 排版煙霧檢查 `/?dev=1&anim=0.1&mute=1`（`runCase('6T-1c …')`） | 1600×900、1040×624、800×600 全 PASS（39 PASS、0 FAIL） |

- `client/openapi.json`、`client/src/api/schema.d.ts` 已經重產，新增 `MailTabLinesView` 和 `MailView.tab_lines`。
- 實地地圖沒改，所以 `tests/content/test_field_buildings.py` 的 RULE_HASHES 不用動。

新測試：
- `tests/api/test_world_mail_api.py`：`test_tab_lines_6t1c`、`test_send_stack_count_6t1c`
- `client/src/world/mail6t1b.test.ts`：6T-1c 三組共 6 項，包括數量夾範圍、附件格的 ±、分頁台詞、按鈕列的順序
- `client/src/render/portrait.test.ts`：剪影不寫「?」、soot 參數

## 5. 版號

**`WORLD_RULES_VERSION` 不用升**：
- 寄件填數量：伺服器規則本來就吃個數，沒有改 `trpg.world` 的程式。
- 分頁台詞：只改內容資料（`trade.yaml`）、內容 schema 和 API 顯示。
- 郵差頭像的 `gear.head`：只改內容資料。

同一份世界日誌重播的結果不變；內容 digest 會變（已涵蓋內容變動）。世界、角色、日誌的存檔格式也都沒變。

## 6. 待 PM 決定

1. **場上的 soot**：soot 照 `NPC頭像.md` 是只畫在頭像上的配件，場上的紙娃娃沒有對應部件。要讓場上看得到，得新增或修改紙娃娃部件（Q 版定案後）。這段只加深、加大了頭像的 soot。
2. **800 寬的「✉」隱藏截圖**：800×600 時面板蓋住郵差一帶，截圖看不出「✉」有沒有藏起來。DOM 已確認面板開著時 `field-mail-glyph` 不存在。1600 有前後對照。
3. **剪影底色用所在城鎮的區域色**：「寄給誰」三處的剪影統一用所在城鎮（郵差）的區域色，原本是對方所在區的顏色、每列不一樣。如果要的是「對方的區域色」，改回 `r.region` 就好；不過收件匣和退件的信沒有寄件人的區域資料。
4. **「寄出」拿掉說明卡**：說明卡會蓋住上面那一行。不能寄的原因本來就全列在「寄出前檢查」裡，所以直接拿掉；如果要留，得改成往下開，但目前共用浮動卡只有「上方，超出才翻轉」。
5. **主要按鈕滑過變深灰**是共用 `base.css` 的問題（`button:hover` 蓋過 `button.primary`），全遊戲的主要按鈕都一樣。這段只在郵寄面板內修。要全面修的話，在 `base.css` 加 `button.primary:hover:not(:disabled)` 一行。
6. **soot 參數改動會影響所有帶 `soot` 的 NPC 頭像**（不只灰鴿）。
7. **物品小牌是過渡做法**：G10 物品圖示移植後，要把附件格、背包格、信上的小牌都換成物品圖示。
8. **郵差頭像拿掉 `cap` 配件、改用 `gear.head` 皮帽**：如果以後要畫郵袋（`mailbag`）或其他頭像專用配件，還是放在 `extras`。

## 7. 複雜度 noqa

沒有新增。

## 8. 啟動過的程序與 PID

- 預覽伺服器：`uv run python scratchpad/t1c/serve.py`（埠 8124），python PID 27004（子程序 73528）。
- 無頭 Chrome：CDP 9479、`--mute-audio`，profile 在 `scratchpad/t1c/prof`，PID 59176（子程序 75248）。
- 結束時只用這兩個 PID 關掉（`taskkill /F /T /PID …`），之後確認 8124、9479 都沒有在聽。
- 沒用 8000、8001、8010；沒碰 `tmp_x`、`saves/`。暫存都在 session scratchpad 的 `t1c/`，不 commit。
- `corepack pnpm -C client install --frozen-lockfile`：worktree 原本沒有 `node_modules`，照 lockfile 裝的。
