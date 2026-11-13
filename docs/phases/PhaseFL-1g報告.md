# Phase FL-1g 報告｜閃現選變體畫面的美術驗收修正（FL-1b、LF-3）

> 實作 agent，2026-11-13（Opus 5.5）。依據 main `a1cfbc681`（含 `docs/art/FL-1b驗收.md` 第 1～5、7 節）。另外併做開發 PM 追加的三件：戰場變奏的地形字、營火入口先分清楚是程式錯還是規則問題、核對 LF-3 截圖。
>
> commit：`e1dfb16fc`（後端）、`b9148d4ba`（前端與夾具）、`71750eaaa`（報告、截圖、上手筆記）。

## 1. 逐條對照驗收檔

### FL-1b 必修（第 2 節）

| 條 | 做法 | 檔案 | 截圖 |
|---|---|---|---|
| 必修 1 代價變少畫成變好 | **後端修**：`_cost_rows` 的方向改由 `_cost_way(a, b)` 決定：兩邊都有數值時，變便宜給 `better`、變貴才給 `cost`。每場次數（`uses_per_battle`）是數字越大越好，所以反過來算（`_MORE_IS_BETTER_COSTS`）。新加的代價、整項拿掉（前端照舊寫「不用花」並畫成變好）、沒數值可比的，照舊給 `cost`。前端 `nowStyle` 不用改，照方向畫 | `src/trpg/api/flash_changes.py` | `fl1g_01_costdown_live_1600/800`（實機輕巧：AP 2 → 1、冷卻 2 → 1 回合都是金底，燃燒 5 → ▼ 3）；`fl1g_04` 的冷卻 2 → ⚠ 3、4 回合照舊是代價 |
| 必修 2 倍率型新傷害寫元素 | 新加或拿掉的整段武器傷害（`_phrase`），元素不是物理時把元素名插在「武器傷害」前面：「3 成雷電武器傷害」。字放在 `flash_changes._ELEMENT_WEAPON_DAMAGE_ZH = "{element}武器傷害"` 常數，**待玩法 PM 定字**，定了只換這一行。說明卡沿用 `weapon_damage:<‰>`。下固定區的一句話直接用這個字，所以也一起變了 | `src/trpg/api/flash_changes.py` | `fl1g_02_element_live_1600/800`（實機點燃斬第 2 次指定元素：「額外傷害 沒有 → 新 3 成雷電武器傷害」，下固定區「多了額外傷害：3 成雷電武器傷害。」） |

### FL-1b 可修（第 3 節）

| 條 | 做法 | 截圖 |
|---|---|---|
| 1 上緣漸隱改矮 | 選變體的捲動區上緣漸隱從 56px 改成 32px，比例照舊（上面 70% 實色）。選擇器是 `.ui-popup-hud > .ui-popup-body:has(.fc-in-popup)::before`，其他面板還是 56px。選項卡 `scroll-margin-top` 改成 36px，跟著讓出漸隱 | `fl1g_01_costdown_live_800`（捲 106px 時，第 1 張殘卡的「射程 2 格 → 3 格」露在漸隱下面） |
| 2 標籤對照表缺 lightning | **原因不是對照表少了**：`content/skill_tags.yaml` 本來就有 `lightning: 雷電`，是 `flash_changes._condition` 呼叫 `condition_text` 時沒有傳 `tag_name`，所以退回「特定」。已經補上 `tag_name`、`tag_runes`。對照表不用改 | `fl1g_07_tag_name_dev_800`（開發頁：「本回合已施放過帶「雷電」標籤的技能時才有」）。**實機未看** |
| 3 兩列同叫「傷害」 | 差異清單換好字之後，如果不同效果的列名稱一樣（`_name_segments`）：本體兩段以上同名就寫「傷害（第 1 段）」「傷害（第 2 段）」，接續段寫「傷害（接續）」。本體只有一段時不加。字放在 `_SEGMENT_ZH`、`_FOLLOWUP_SEGMENT_ZH` 常數 | `fl1g_06_segments_dev_800`（雙槍連射輕巧）。**實機未看** |
| 4 挪位置又改回合併成一列 | 新增 `_merge_moved`，在 `_drop_shifted` 後面跑：同一個狀態或表面拿掉一列、又新加一列時（`_same_effect`），兩列併成新位置上的一般差異列，例如「燃燒 2 回合 → 3 回合」 | `fl1g_09_run_foot_top_live_1600`（實機一輪重閃「打中時還會放電」與「多帶一段冰霜傷害」：燃燒 2 回合 → 3 回合，只有一列） |
| 5 一輪下固定區 | `.fc-run > .fc-foot::before` 加 32px 漸隱（後 55% 實色，同大世界下緣）。下固定區的 `margin-top` 8 → 32，所以頁面捲到底、下固定區沒黏住時，漸隱只蓋在這段空白上。`.fc-say` 加 `text-wrap: pretty` | `fl1g_09_run_foot_top_live_1600`（頁頂：黏住的下固定區上面，卡片淡出）、`fl1g_09_run_foot_bottom_live_1600`（頁底：最後一張卡完整）。376 寬的「一定要選一個。」現在折成「…一定要選／一個。」，剩兩字，不再只剩「個。」 |
| 6 營火入口 | 見第 2 節 | `fl1g_10_campfire_no_hint_live_1600` |

### LF-3（第 7 節）

| 條 | 做法 | 截圖 |
|---|---|---|
| 必修 1 800 選中大卡的標頭被蓋住 | `FlashPendingPanel` 選中時用新的 `scrollBlock(el)` 判斷：卡高加上下 `scroll-margin`，比可視高（大世界看 `.ui-popup-body`，一輪看視窗）還高時，用 `block: "start"`，否則照舊用 `nearest`。搭配可修 1 的 `scroll-margin-top: 36px`，標頭會落在 32px 漸隱下面 | `fl1g_03_tallcard_top_dev_800`（開發頁 llm 組選轉型，卡高 221 > 可視 262 − 56：卡上緣離捲動區頂 37px，比漸隱 32 低，大標與單選圈都看得到）、`fl1g_03_tallcard_dev_1600`。實機的大變化卡最高約 120（`fl1g_04_llm_names_live_800`，走 `nearest`）。轉型大卡**實機未看**：營火重閃第 3 格出不了題，見第 2 節 |
| 可修 1 名稱與標記不拆開 | 新名稱與「源晶推演」包進 `.fc-name-group`（inline-flex、nowrap）。另外改了格線：「前」欄從 `max-content` 改成 `minmax(min-content, max-content)`，`.fc-was` 可以折行；「後」欄從 `minmax(0, 1fr)` 改成 `minmax(min-content, 1fr)`。這樣「後」欄最少能放下整組名稱，放得下時「前」欄照舊不折；只有很擠時才由「前」欄的長條件字先折行 | `fl1g_11_name_group_longbefore_dev_800`（開發頁，把轉型卡最後一列的「前」換成「1.25 倍武器傷害（目標站在「水」表面上又被撞過時才有）」：「前」折成兩行，名稱組 495～619，卡右緣 628，沒有超出）。改之前同一個情境，名稱組會超出卡外 51px |
| 可修 2 字級 | `.fc-src` 從 10.5px 改成 11.5px | `fl1g_04_llm_names_live_1600/800` |
| 換字 | `FLASH_LLM_NAME_HINT` 改成「源晶推演：這個名字是源晶照你這一路的戰鬥推演出來的，只是名字；效果和數值都照規則定，不會因為名字改變。」 | `fl1g_05_source_hint_live_800`（實機滑過標記） |

### 追加 1：戰場變奏的地形字（玩法 PM 2026-11-13）

- 先查引擎（`src/trpg/engine/variants.py`、`content/skill_composer.yaml` 的 `variant.conditions`），哪些條件看施放者、哪些看目標：
  - 看施放者：水中（`caster_surface: water`）、冰上（`caster_surface: ice`）、居高（`caster_high_ground`，施放者所在格比目標點高）、靠牆（`caster_adjacent_blocker`）。這四個字照舊。
  - 看目標：油面、水窪（`target_surface`，看的是**目標點**的表面）。改成「目標站在油上」「目標站在水窪裡」。
- 大標（`content/flash_templates.yaml` 的 `major_battle_variant.headline_zh`，只改文字欄位）改成「在特定地形施放時，這招換一種打法」。
- 實機：`fl1g_04_llm_names_live_1600`，大標是新字，下固定區「站在水中施放時，這招自動換成另一種打法。」
- 常數沒有搬進 YAML（照指示）。

### 追加 3：核對 LF-3 的 7 張截圖

逐張看過 `docs/art/shots/LF-3/` 的 7 張，**7 張都是 LF-3 自己伺服器的畫面，不用重拍**：
- 角色、靈感點前後一致：7 張都是樞島 Lv 1、HP 60/60、法力 34/34、補給 5、靈感 5（已扣 1 點）。主角是「引火射」第 3 次（大變化），和 LF-3 報告第 3 節寫的一樣。美術驗收 agent 的角色是單手劍「點燃斬」（點燃斬閃過兩次），兩邊對不上，所以不是連到對方的 Chrome。
- 選項前後一致：四個 LLM 名稱燎原閃、灼心、斷鏈、餘燼低語，加上描述，和 LF-3 報告列的字逐字相同。01／02／05／06 的前兩張、03／04／07 的轉型卡內容都對得上。
- 1600 與 800 是同一題（同樣的名稱、同樣的數字）。
- LF-3 報告寫，9481 誤連只發生在第一次開 Chrome，後來改用 9563 重拍。截圖內容也支持這個說法。

## 2. 營火入口錯誤的原因（可修 6、追加 2）

**現象**：種子 2 的開發一輪打到營火，「灼燃・燃燒爆」（第 1 次蓄力、第 2 次 `keyword_imbue` 潮濕、第 3 次 `major_intensify`）的入口寫「可以重閃第 3 格轉型」，按下去卻是「這招這一次沒有合法的變化（沒有扣點）」。重閃第 1 格也一樣，只有第 2 格出得了題。

**追因**（暫存區腳本逐場重推歷程）：
1. 第 2 次閃現是在角色 **1 階**時選的。升到 3 級變成 **2 階**之後，同一份歷程用 2 階重推，第 2 筆（`keyword_imbue`）就套不上了（`FlashStepError`）。1 階、3 階、4 階都推得過，只有 2 階不行。第 3 筆在 1 階也套不上。
2. 新的閃現有 3W-R1 的退路：歷程重推不了時，改用存檔裡的定義當起點（`derive_on_current`，只在 `slot is None` 時用）。**重閃沒有這條退路**：重閃第 N 格會從頭重推整份歷程，第 2 筆一失敗，所有候選都一起失敗。重閃第 3 格的 17 個候選（大變化＋轉型），全部失敗在「第 2 次的變化 keyword_imbue 套用不了」。
3. 入口的提示（`run_presenter._flash_out` 的 `hint`）只看「第 3 格是大變化、不是轉型」，沒有確認重閃那一格出不出得了題。

**是程式錯，還是規則問題**：兩層。
- **入口提示是程式錯（api）**：已修。`hint` 多加一個條件：用出題同一套的 `has_options(flash_request(..., slot=第 3 格))` 確認真的出得了題，才給「可以重閃第 3 格轉型」。`has_options` 本來就有快取，一招最多多算一次。測試 `tests/api/test_reflash_hint_fl1g.py`：種子 2 營火上，每一招的提示都和實際能不能出題一致。實機 `fl1g_10_campfire_no_hint_live_1600`：灼燃・燃燒爆的三個重閃鈕都沒有提示字。
- **出不了題的根本原因在 skillgen，沒有改**（TF-1 正在改那一塊）。問題出在「歷程照目前的角色階級重推」和「已經選過的變化之後都要能重推」這兩件事在升階時會衝突：1 階選得到的變化，到 2 階可能推不出來，而重閃沒有 3W-R1 的退路，所以這招以後的重閃會一直卡住，不只第 3 格。這比較像規則層面的矛盾，要由人決定方向，例如：重閃也用存檔定義當起點、歷程記住當時的階級、或升階時先檢查歷程。**請轉給專案 PM**。重現方式：`new_dev_run(第一個開發起始包, 種子 2)`，`auto_play` 到營火，對灼燃・燃燒爆用 1～4 階 `derive_chain`。
- 入口還有一個小問題（**待 PM 決定**）：出不了題的重閃格，按鈕還是可以按，按了才回「沒有合法的變化（沒有扣點）」。這次照最保守的做法只修提示字，沒有把按鈕標灰；要不要比照 FL-1c 的閃現，把它標灰並加灰字，待定。

## 3. 測試

- 新增 `tests/api/test_flash_changes_fl1g.py`（5 個：代價升降、元素武器傷害、標籤名、段名、挪位置併列）。
- 新增 `tests/api/test_reflash_hint_fl1g.py`（營火提示和實際出題一致）。
- 新增 `client/src/run/fl1gFlashFix.test.ts`（7 個：換字、名稱組、字級、漸隱與 scroll-margin 的 CSS、`scrollBlock` 的 nearest／start 判斷）。
- 改了的既有斷言，都在預測之內：
  - `test_flash_changes_fl1a.py`：霜寒之觸法力 2 → 1、展翼輕巧 AP 2 → 1 的方向，從 `cost` 改成 `better`；「不會有 better」那一條只看非代價列。
  - `test_flash_text_fl1b.py`：輕巧 AP 的方向改成 `better`。
  - `test_flash_text_fl1f.py`：油面、水窪改新字。
  - `fl1bFlashChoice.test.ts`：輕巧那張卡改成驗證「沒有代價框、AP 是變好、有段名」，另外加一條「蓄力的冷卻變長照舊是代價框」。
- 夾具 `client/src/dev/fixtures/flashChoice.json` 用 `scripts/export_flash_choice_fixture.py` 重產。差異只有三種，都在預測之內：代價變少的列 `cost → better`、雙槍連射的「傷害（第 1／2 段）」（含 `say_zh`）、llm 組的「帶「雷電」標籤」。
- OpenAPI：API 欄位沒有變，`scripts/export_openapi.py` 重產後沒有差異，所以不用跑 `gen:api`。

## 4. 檢查（交件前）

| 指令 | 結束碼 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0 |
| `uv run lint-imports` | 0（14 kept） |
| `uv run pytest -q -n 8`（flash 相關 11 檔：fl1a、fl1b、fl1f、fl1g、reflash_hint、flash_api、fl1c、lf3、fl1d、lf2、runs_api） | 0（122 passed） |
| `corepack pnpm exec vitest run src/run/ src/world/fl1cFlashNone.test.ts src/ui/floatCardRule.test.ts src/screens` | 0（174 passed） |
| `corepack pnpm -C client build` | 0 |

沒有跑全量 `check.py`，也沒有做平衡量測。

## 5. 截圖（`docs/art/shots/FL-1g/`，DPR 1、`?mute=1`、無頭 Chrome `--mute-audio --disable-gpu`）

拍攝環境：自己開的 `trpg serve --port 8811`（`TRPG_SAVE_DIR` 在暫存區、`TRPG_DEV_ROUTES=1`、`TRPG_LLM_CONFIG=config/llm.local.toml`）、建置好的前端、開發頁用自己的 vite 8812、Chrome 除錯埠 9671（`--remote-debugging-address=127.0.0.1`）。三個埠開之前都先用 `netstat -ano` 確認沒人在聽，交件前已經用自己記下的 PID 關掉，三個埠都沒在聽了。**本機 LLM**：8001 沒有回應，改用 LM Studio `100.87.188.89:1234`（`swift-1.5-qwen3.8-27b-uncensored-dynamic-mtp`，`reasoning_effort = "none"`）。設定放在 worktree 的 `config/llm.local.toml`（gitignored），沒有 commit，交件前已經刪掉；`config/llm.toml` 沒有動。大世界的 LLM 開關用 `POST /api/world/llm {"enabled": true}` 打開，只影響那台伺服器的記憶體。開發角色：單手劍＋點燃＋潮濕、種子 8（點燃斬＋激流斬）。每次閃現前先停伺服器，把存檔的閃現狀態標成「上場用過」、靈感點補到 20，再透過 API 閃第 1、2 次（第 2 次指定「元素與關鍵字」）和第 3 次。

| 檔案 | 內容 | 來源 |
|---|---|---|
| `fl1g_01_costdown_live_1600.jpg`、`_800.jpg` | 必修 1：點燃斬第 1 次，選輕巧：AP 2 → 1、冷卻 2 → 1 回合都是金底的變好，燃燒 ▼ 3 回合。四張卡都有本機 LLM 的描述。800 那張同時是可修 1（32px 漸隱下面露出殘卡） | 實機 |
| `fl1g_02_element_live_1600.jpg`、`_800.jpg` | 必修 2：第 2 次指定元素，「打中時還會放電」→ 新 3 成雷電武器傷害，下固定區同一個字 | 實機 |
| `fl1g_03_tallcard_top_dev_800.jpg`、`fl1g_03_tallcard_dev_1600.jpg` | LF-3 必修 1：轉型大卡選中後對齊上緣，標頭在漸隱下面 | 開發頁（實機未看：營火重閃第 3 格出不了題；大世界第 3 次這次沒有出轉型） |
| `fl1g_04_llm_names_live_1600.jpg`、`_800.jpg` | 本機 LLM 的名稱與描述（實機第 3 次大變化：濕焰一閃、赤雷十字斬、環電一閃、殲滅續動）；「源晶推演」11.5px；戰場變奏的新大標與「站在水中施放時」；代價變多（冷卻 2 → ⚠ 3／4 回合）照舊是琥珀框 | 實機 |
| `fl1g_05_source_hint_live_800.jpg` | 「源晶推演」說明卡的新字 | 實機 |
| `fl1g_06_segments_dev_800.jpg` | 可修 3：雙槍連射「傷害（第 1 段）／（第 2 段）」，輕巧的 AP、冷卻變好 | 開發頁（實機未看） |
| `fl1g_07_tag_name_dev_800.jpg` | 可修 2：「本回合已施放過帶「雷電」標籤的技能時才有」 | 開發頁（實機未看） |
| `fl1g_08_transform_dev_800.jpg`、`_1600.jpg` | 轉型卡：冷卻 2 → 1 回合是變好；AP、耐力「不用花」 | 開發頁（實機未看） |
| `fl1g_09_run_foot_top_live_1600.jpg`、`fl1g_09_run_foot_bottom_live_1600.jpg` | 可修 5：一輪營火重閃第 2 次，下固定區上方有漸隱、頁底沒有蓋到卡；可修 4：燃燒 2 → 3 回合只有一列 | 實機（種子 2 開發一輪） |
| `fl1g_10_campfire_no_hint_live_1600.jpg` | 可修 6：灼燃・燃燒爆的重閃鈕不再有「可以重閃第 3 格轉型」 | 實機 |
| `fl1g_11_name_group_longbefore_dev_800.jpg` | LF-3 可修 1：「前」欄的字很長時，由「前」欄先折行，名稱和「源晶推演」維持同一行、不超出卡外 | 開發頁＋頁內改字（實機未看） |

## 6. 待 PM 決定

1. **元素武器傷害的字**（必修 2）：先寫成「3 成雷電武器傷害」，**待玩法 PM 定字**。字只放在 `flash_changes._ELEMENT_WEAPON_DAMAGE_ZH` 一個常數裡。物理不寫元素。目前只套用在「整段新加或拿掉」的列；已經存在的元素傷害段，倍率改變的列仍然只寫「武器傷害」（照最保守的做法，沒有擴大範圍）。
2. **段名的字**（可修 3）：先寫成「傷害（第 1 段）」「傷害（接續）」，下固定區的一句話也會跟著變成「傷害（第 1 段）從…變成…」。要不要改成「第 1 段傷害」這類語序，待玩法 PM 定。
3. **水窪、油面的一句話**：大標以外，`say_zh` 的句型是「{terrain}施放時，…」，所以會讀成「目標站在油上施放時，這招自動換成另一種打法。」主詞有點混。這次照指示只換字，沒有動句型。要不要改成「對站在油上的目標施放時」，交給玩法 PM。
4. **出不了題的重閃格要不要標灰**（第 2 節）：這次只修了提示字。
5. **重閃在升階後重推不了**（第 2 節）：skillgen／規則層面的問題，請轉專案 PM。
6. **「前」欄允許折行**（LF-3 可修 1 的做法）：只有在擠到「後」欄放不下名稱組時才會折，平常的寬版和窄版都和 FL-1b 一樣（實量：開發頁 llm 組 800，名稱組位置不變）。如果美術偏好別的處理方式（例如名稱列另起一行），再說。

## 7. 沒驗證

- 轉型卡、卸下選單、主動欄的實機畫面：營火重閃第 3 格出不了題；大世界第 3 次這次也沒有出轉型。
- 大世界的重閃（城鎮），這次沒有拍。

## 開發 PM 裁定

- 接受，已合併。FL-1b 必修 2 條、可修 1～6，LF-3 必修 1、可修 1、2，以及三件追加都已完成，等美術複驗（`docs/art/shots/FL-1g/`）。
- 營火入口：程式錯的部分已修，提示改為先確認出得了題才顯示。升階後重閃卡住，玩法 PM 已定案為「重閃也退回存檔裡的歷程」（b7eedf2ee），下一段實作。
- 待 PM 決定 1～3（元素武器傷害、段名、油面／水窪的句型）：轉交玩法 PM 定字，回覆後只換字。
- 待 PM 決定 4（出不了題的重閃格標灰）：併進升階重閃那段一起看。
- 待 PM 決定 6（「前」欄擠的時候可以折行）：交美術複驗時看。
- LF-3 截圖核對：7 張都是 LF-3 自己的畫面，不用重拍。
