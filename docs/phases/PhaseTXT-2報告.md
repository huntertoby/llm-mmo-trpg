# Phase TXT-2 報告：閃現與許願池的定稿換字，加上幾項小修

> 實作 agent，2026-11-13（Opus 5.5）。依據：玩法 PM 11-13 定字（專案 PM 轉達）；追加第 9～12 項（`docs/phases/現代網頁指南試用.md`、美術 PM、玩法 PM 許願池定稿字）與「主力瀏覽器」規定。
> 分支 `worktree-agent-a0dbfaa8ab8665373`，途中兩次 `git merge main`（含 WP-2、WP-3、RR-1）。

## commit

| commit | 內容 |
|---|---|
| `b67dd0769` | 第 1、2 項：許願池說明卡、守池人台詞；主城規則雜湊 |
| `0872e6509` | 第 3～5 項：戰場變奏說明句與「這招開始會造成」大標搬進 `flash_templates.yaml`；元素武器傷害、段名拿掉待定標記 |
| `d57c9a2ee` | merge main |
| `b9d576d53` | 第 9 項：輸入法 Enter |
| `2c7f4ee2a` | 第 10 項：容器查詢指名 |
| `6c590989c` | 第 6 項：許願第 2 個關鍵字 |
| `31728d405` | 第 12 項：許願池玩家字、「都不拿」 |
| `08425f110` | 第 7 項：一輪窄欄條件字（同一筆加了 balance，下一筆退回） |
| `38d280a68` | 第 11 項：`text-wrap: balance` 量過後退回 |
| `4a2b0f792` | 截圖 |
| `62ef8f40b` | 上手筆記 |

## 1. 逐項

### A. 換字

1. **許願池說明卡**（`content/world/fields/capital/capital.yaml` `wishing_pool.note_zh`）：照定稿句。
2. **守池人台詞**（`pool_keeper.note_zh`，也是面板標頭那一句）：照定稿句，**沒有加「」**（定稿字沒有；公告板 `line_zh` 也沒加）。兩處都不寫價錢、次數。註解改成「TXT-2：玩法 PM 定稿句」，拿掉「暫定，待玩法 PM 給字」。
3. **元素武器傷害**：`flash_changes._ELEMENT_WEAPON_DAMAGE_ZH` 本來就是「{元素}武器傷害」、物理不寫；只拿掉「字待玩法 PM 定」。既有測試 `test_added_weapon_damage_names_its_element` 已鎖雷電與物理兩種。
4. **段名**：`_SEGMENT_ZH`、`_FOLLOWUP_SEGMENT_ZH` 照舊，docstring 註明定稿。
5. **戰場變奏說明句**：`api/flash_text.py` 的 `_VARIANT_WHERE`、`_VARIANT_SOMEWHERE`、`_INTENSIFY_NEW` 搬到 `content/flash_templates.yaml`：
   - `battle_variant`：`caster_say_zh`「你{terrain}施放時，這招自動換成另一種打法。」、`target_say_zh`「目標{terrain}時，這招自動換成另一種打法。」、`somewhere_zh`「在特定地形」、`places`（6 列：`condition`、`where_zh`、`subject: caster|target`）。
   - `intensify_new_headline_zh`「專精{keyword}：這招開始會造成{keyword}」。
   - schema：`content/flash_templates.py` 的 `BattleVariantText`（兩個句型都要帶 `{terrain}`、條件不能重複）、`VariantPlace`；`FlashTable.battle_variant`、`intensify_new_headline_zh` 都是選填，沒寫時 `{terrain}` 原樣留著、大標照模板。
   - 做法：模板 `say_zh` 帶 `{terrain}`，而且查得到條件時，依 `subject` 換成對應句型；查不到就照模板句，`{terrain}` 填 `somewhere_zh`，結果是「在特定地形施放時，…」，和改前一樣。大標維持「在特定地形施放時，這招換一種打法」。
   - 測試：`tests/api/test_flash_text_fl1f.py` 六個條件改成新句子，另外加 `test_battle_variant_places_cover_every_condition`：`places` 要對得上組合器的每個變奏條件，`target_surface` 的條件必須是 `target`，`where_zh` 不帶「目標」。實機看到「你站在水中施放時，這招自動換成另一種打法。」（`txt2_01`）。

### B. 小修

6. **許願池兩個關鍵字**：`skillgen/candidates.py` 的 `_pinned` 裡，橋接的「另一個持有的關鍵字」改成照 `region_keywords` 排前（`region_first`）。許願本來就傳 `region_keywords=(第 1, 第 2)`，所以：
   - 第 2 個已持有時，橋接先試「第 1＋第 2」。
   - 第 2 個還沒有時，新方向先試（5B-4d 原本就這樣）。
   - 組合器做不到時，照舊三張只保證帶第 1 個。
   - 其他指定關鍵字的呼叫端（機遇、故事事件、預測）都只傳指定關鍵字本身，順序不變。
   - 測試 `tests/skillgen/test_wish_two_keywords_txt2.py`（7 項）：鎖住橋接、新方向第一次試的關鍵字組；三個種子確實有一張同時帶兩個；做不到時退回只帶第 1 個；只傳指定關鍵字時結果逐字不變。
   - **parity 與 Mock 夾具**：先預測不會變，因為夾具裡沒有「指定關鍵字＋另一個區域關鍵字」的呼叫。實際跑 `test_refactor_parity`、`test_pinned_keyword`、`test_candidates`、`test_perf3_candidates`、`test_offer_prefetch`、`test_offer_cache`、許願三檔、`test_generated_content`，95 項全過，沒有任何 key 變動。
7. **一輪窄欄條件字**：只在「4 成武器傷害」上加 `nowrap` 會把「前」欄擠成「1.15 倍武器傷／害」（量過），所以改成：
   - `.fc-was`、`.fc-now > span` 加 `word-break: keep-all`＋`overflow-wrap: break-word`，只在空白與標點換行。
   - 括號條件 `.fc-when` 照舊可以在字間換行。整段不斷的話，「（手持雙手槍時才有）」比「後」欄寬，會超出卡外 16～22px（量過）。
   - 帶條件時，前段包一層 `.fc-main` 並設 `nowrap`（`FlashChoiceParts.NowChip`）。
   - 結果（開發頁 rows 組 376）：「新 4 成武器傷害｜（手持雙手｜槍時才有）」，從四行變三行，不再斷在「武器傷／害」。「前」欄變成「1.15｜倍武器傷害」，斷在數字和單位之間的空白（詞邊界）。
   - 卡高：五組夾具 × 376／800／1600 都和改前相同，沒有東西超出卡外。字的斷行只有 376 的 rows 組改變；800 與 1600 全部相同。
   - 測試：`client/src/run/txt2FlashWrap.test.ts`。
8. **截圖**：見第 3 節。
9. **輸入法 Enter**：新增 `client/src/ui/imeEnter.ts`：`isImeComposing(e)` 會看 `nativeEvent.isComposing`、`isComposing`、`keyCode === 229` 三個條件；`isSubmitEnter(e)` 判斷「是 Enter，而且不在組字中」。
   - `NotesPanel.tsx` 的留言框與 `MailPanel.tsx` 的郵寄個數框都改用 `isSubmitEnter`。
   - 原始碼掃描 `ui/imeEnterRule.test.ts`：`<input>`／`<textarea>` 上的 `onKeyDown`／`onKeyUp`／`onKeyPress` 碰到 Enter，必須經過 `isSubmitEnter`；有文字輸入框的檔案不准自己比 `"Enter"` 或 `keyCode 13`。另有 5 項單元測試，Safari 的 229 也在內。
   - 驗證掃描有效：把留言框改回 `e.key === "Enter"`，三條規則都會變紅。
10. **容器查詢指名**：
    - `.fc-run` 改成 `container: fc / inline-size`，查詢寫 `@container fc (max-width: 559px)`。大世界彈窗裡原本對到的「最近容器」是 `.world-hud-panel`，所以讓它同時叫 `world-panel fc`（`world-hud.css`），行為和改名前相同。
    - `.world-mail` 改成 `container: mail / inline-size`，兩處查詢寫 `@container mail (width < 560px)`。
    - 掃描 `ui/containerNameRule.test.ts`：不准有不帶名字的 `@container`，查詢用到的名字都要有宣告。`pnl1aPanelKit.test.ts` 的 regex 跟著改。
    - **行為不變的證據**：開發頁四頁 × 800／1600／408 共 12 組，比較改名前後每個元素的盒子大小、display、字級、格線欄寬的指紋，12 組全部相同。改名前的版本是暫時把三個 CSS 檔的名字拿掉、其他改動保留，量完已還原。截圖 `txt2_10_*` 是改前、改後成對。
11. **`.fc-headline` 的 `text-wrap: balance`：加了、量過，退回不加。** 原因：
    - 條件 2、4 不成立：大標超過兩行而被 `line-clamp` 截斷時，Chrome 會把藏起來的行重排。實機注入一段四行長的壓力字，排版從 4 行變成 6 行，而且斷在詞中間（「換個形狀一次打到更｜多敵人」「持｜續」）。看得到的兩行、省略號位置、卡高、面板高都沒變（`txt2_11_clamp_*`，改前改後逐像素看起來相同），但排版行數變了，也斷回了詞中間，照「任何一個變了就退回」處理。
    - 沒有效益：`flash_templates.yaml` 的 107 個大標，在 1600／800（大世界）、376（一輪）每一個都量過，開了 balance 也沒有任何一個斷行位置改變；實機三組（800、1600、376，`txt2_11_balance_*`）也完全相同。要長到 1600 也折兩行（合成字）時，balance 才會換斷點。
    - 另外量到：`.fc-headline` 沒有 `<wbr>`（`headlineOf` 是純字串），能換行的地方只有標點，`overflow-wrap: anywhere` 的緊急斷點 balance 沒用到。所以美術 PM 擔心的「兩行時第二行只剩一兩個字」，在現有大標裡沒有發生。
12. **許願池玩家字定稿**：
    - `client/src/world/wish.ts` 的 `WISH_ZH`：`textLead`、`menuLead`、`noneLeft`「用完了」、`timeout`、`waitText`、`refundNote`、`skipRefund` 照定稿字；新加 `skip`「都不拿」。
    - 伺服器：`WISH_NO_MATCH_ZH` 照定稿句；`_PENDING_OFFER_ZH`「還有任務給的技能三選一沒有選：先選一招，或都不拿」；`_skill_story_line` 遇到許願池而且有退款時，回「許願池給的三招都沒拿，退回 {N} 任務幣（次數照扣）。」。其他來源照舊。
    - **都不拿**：任務三選一的鈕 `offerSkipLabel` 有退款時寫「都不拿（退回 N 任務幣）」，其他寫「都不拿」（原本是「跳過」）。共用元件 `OfferPicker` 那句改成「**一張都不選就是都不拿（技能不變）。目前：都不拿。**」。
    - RR-1 灰字「這一格目前沒有可以重閃的變化」：前後端常數的 docstring 註明定稿。
    - 預測會變紅的測試：`test_wish_api_wp2`（blocked_zh）、`test_wish_pregen`（跳過後那句）、`wp3Wish.test.ts`（兩個鈕字）。實際紅的就是這三個，已更新；`capitalFigures.test.ts`、`wp3Wish.test.ts` 的台詞在第 1 筆 commit 就改了。

## 2. 主城規則雜湊（`tests/content/test_field_buildings.py` `RULE_HASHES`）

- **預測**：只有 `capital` 會變。雜湊算的是地圖排除 `buildings`、物件 `look`、情境物件 `figure` 之後的排序鍵 JSON；這次只改了主城兩個情境物件的 `note_zh`，YAML 註解不進雜湊。
- **實際**：只有 `capital` 變了，`341d6dcf2a2f2587` → `bb704ebd2231259b`；其他 10 張（9 張城鎮與室內圖、`ash_ferry`）都沒變。
- 逐項說明：
  1. `wishing_pool.note_zh`：「花任務幣向池子說一句願望，換一份技能三選一；每週次數有限。」→ 定稿句。
  2. `pool_keeper.note_zh`：「「說出你想要的力量，池子會回應你。」」→ 定稿句（不帶「」）。
  3. 兩行註解改字，不進雜湊。
- 雜湊旁的註解寫「TXT-2：許願池與守池人定稿字」，WP-2 那句保留在上一行。`WORLD_RULES_VERSION` 沒升（照 WP-2 的前例，只換說明字不升）。

## 3. 截圖（`docs/art/shots/TXT-2/`，33 張）

- 拍攝環境：無頭 Chrome（**Chrome 157**），DPR 1，`?mute=1`，`--mute-audio --disable-gpu --remote-debugging-address=127.0.0.1`。
- 自己開的服務：`trpg serve --port 8831`（`TRPG_DEV_ROUTES=1`，存檔在暫存區，LLM 指到 `127.0.0.1:9`，沒接本機模型）、vite 8832（開發頁）、除錯埠 9731。開之前用 `netstat -ano` 確認三個埠都沒人用。
- 交件前用自己記下的 PID 關掉（serve 42184、vite 63984、Chrome 61428 含子程序），三個埠都沒在聽了。
- 沒有用 8000、8001。Edge 沒有另外拍（同為 Chromium）。

| 檔名 | 實機／開發頁 | 內容 |
|---|---|---|
| `txt2_01_flash_variant_live_{1600,800,376}.jpg` | 實機（一輪 2b13a2a5d529，點燃第 3 次） | 戰場變奏選項：下固定區「你站在水中施放時…」；800 大標兩行；標籤「大變化・加深」「費用」 |
| `txt2_07_narrow_when_{before,after}_dev_376.png` | 開發頁 rows 組 `mode=run`（**實機未看**） | 第 7 項改前四行斷「武器傷／害」→ 改後三行 |
| `txt2_08_reflash_none_live_{1600,800}.jpg` | 實機（一輪 6f9aab751de7 營火） | RR-1 重閃第 1 格標灰＋灰字 |
| `txt2_08_reflash_major_tags_live_{1600,800,376}.jpg` | 實機（同一輪重閃第 3 格） | 標籤名「大變化・加深／橋接」、「專精點燃：這招開始會造成點燃」（新資料欄）、條件字新換行 |
| `txt2_08_segments_tags_dev_800.jpg` | 開發頁 rows 組（**實機未看**） | 段名「傷害（第 1 段）」「傷害（第 2 段）」、標籤名 |
| `txt2_08_transform_card_dev_{800,1600}.jpg` | 開發頁 transform 組（**實機未看**：實機兩次第 3 次都沒出轉型） | 轉型大卡 |
| `txt2_10_{fc-world,mail-scene}_{before,after}_{800,1600}.jpg` | 開發頁（flash-choice 大世界、item-gallery 信件） | 第 10 項改名前後，指紋 12 組全同 |
| `txt2_11_balance_{before,after}_live_{1600,800,376}.jpg` | 實機（第 3 次閃現，大標兩行那張） | 第 11 項：after＝加了 balance、before＝不加；三組都相同 |
| `txt2_11_clamp_{before,after}_live_{376,800}.png` | 實機頁注入壓力字（**字不是伺服器的**） | line-clamp 截斷位置：看得到的部分相同（藏起來的行不同，見第 1 節第 11 項） |
| `txt2_12_wish_panel_live_{1600,800}.jpg` | 實機（新角色在主城，走到守池人旁按 E） | 換字後的許願池面板：守池人台詞、menuLead、refundNote、「不夠」；入門期擋住（LLM 關著，只有選單分頁） |

## 4. Firefox、Safari 上會怎樣（查 caniuse／MDN）

- **容器查詢與 `container-name`**（Chrome／Edge 106、Firefox 110、Safari 16 起；Chrome／Edge 105 只有部分支援）：在支援的瀏覽器上，命名查詢和沒命名時一樣；同一層 `world-panel fc` 兩個名字是標準寫法（MDN 的例子也是一層兩個名字）。更舊、不支援容器查詢的瀏覽器會跳過整段窄版規則，一律走寬版排法。這和改名前完全一樣，改名沒有讓它更差。
- **`word-break: keep-all`、`overflow-wrap: break-word`、`white-space: nowrap`**：四家都早就支援，Firefox、Safari 的換行結果和 Chrome 相同。
- **`text-wrap: balance`**：已退回不加。如果日後要加：Chrome／Edge 130（114～129 部分支援）、Firefox 121、Safari 17.5 起支援；不支援的瀏覽器會照一般方式換行，只是版面陽春一點，不會壞版。
- **`isComposing`／`keyCode 229`**：兩個都檢查，Safari 沒有 `isComposing` 也擋得住選字那一下的 Enter。

## 5. 檢查（結束碼）

| 指令 | 結束碼 | 摘要 |
|---|---|---|
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `uv run mypy` | 0 | 1579 個檔沒有問題 |
| `uv run lint-imports` | 0 | 14 kept、0 broken |
| `uv run trpg content check` | 0 | |
| `corepack pnpm -C client build` | 0 | 只有既有的 chunk 大小警告 |
| `corepack pnpm -C client typecheck` | 0 | |
| `uv run trpg battle --map bandit_lair --seed 7 --log-json …` → `trpg battle replay` | 0／0 | 73 個動作、254 個事件，重播一致 |
| `uv run pytest -q -n 8`（田野建築、閃現字兩檔、許願五檔、候選四檔、parity、OpenAPI 快照、flash API） | 0 | 153 passed |
| `corepack pnpm -C client exec vitest run src/run src/ui src/world src/screens` | 0 | 126 檔、1619 項 |

- 沒跑完整的 `scripts/check.py`，也沒做數值量測。
- API 沒改：OpenAPI 快照測試通過，不用重產。
- 開發頁夾具 `scripts/export_flash_choice_fixture.py` 重產後沒有差異（夾具裡沒有戰場變奏）。
- 版號沒升。

## 6. 待 PM 決定（都已照最保守的做法做完）

1. **守池人台詞沒加「」**：照定稿原字。舊暫定字有「」，地圖物件卡與面板標頭會直接顯示這句。要加的話只改 `capital.yaml` 那一行，主城雜湊會再變一次。
2. **第 6 項的位置**：第 2 個關鍵字已持有時由橋接帶兩個，還沒有時由新方向帶兩個。組合器常常湊不出兩個（`bridge_variant_cap` 是共用的；三個測試角色在 8 個種子裡約 1～2 個湊得到）。湊不到時照「做不到時照舊」處理，沒有再讓另一張補試，也沒有放寬上限。
3. **第 6 項的副作用**：第 2 個已持有時，橋接的上限先花在「第 1＋第 2」上。如果湊不到，有些種子會連原本湊得到的其他配對也來不及試，橋接退回只帶第 1 個；例如測試角色「帶電＋標記」的種子 1、23，改前橋接是「帶電＋另一個」。這是規格「優先第 2 個」的直接結果，請確認可以接受。
4. **第 7 項**：「前」欄窄的時候改成在數字和單位之間的空白換行（「1.15｜倍武器傷害」），不再斷在詞中間；括號條件仍可以在字間換行。美術複驗時請看 `txt2_07_*`。
5. **第 11 項退回**：如果美術 PM 仍要 balance，要先解決「截斷時藏起來的行斷在詞中間」，例如大標改用 `<wbr>` 搭配 `overflow-wrap: normal`；而且 107 個現有大標加了也看不出差別。
6. **第 12 項「都不拿」只改了任務三選一的鈕與 `OfferPicker` 那句**：一輪的 `RunCompleteOffer`／`RunLevelUp` 鈕仍是「跳過」，世界日誌「…給了技能三選一：先選一招（或跳過）」「跳過了任務給的技能」也照舊（規格只點名許願池與任務三選一）。現在一輪畫面會出現「一張都不選就是都不拿」的說明句配「跳過」鈕，要不要一起統一，請定。
7. **許願池面板 800 寬**：守池人台詞在標頭只顯示一行並截斷，滑過才看得到全文，這是 WP-3 既有的做法，這段沒改（`txt2_12_wish_panel_live_800.jpg`）。

## 開發 PM 裁定

（待填）

## 開發 PM 裁定

- 接受，已合併。第 1～10、12 項完成。第 11 項 `text-wrap: balance` 加了以後，被截斷時藏起來的行會斷在詞中間，照美術條件 4 退回不加。這不算放寬，量測結果交美術 PM。
- 主城雜湊：預測只有 capital 會變，實際也只有 capital，原因是兩個 note_zh 換成定稿字。
- 待 PM 決定：
  - 1：守池人台詞不加「」，照定稿原字。
  - 2：只讓一張卡先試帶兩個關鍵字，接受。
  - 3：橋接卡先把搜尋上限花在第 1＋第 2 個關鍵字，副作用是少數種子連原本湊得到的配對都來不及試、退回只帶第 1 個。轉交玩法 PM 確認可否接受；在那之前維持現狀。
  - 4、5、7：交美術 PM 看 txt2_07、balance 量測、800 寬時守池人台詞只顯示一行。
  - 6：一輪的「跳過」鈕、世界日誌的「跳過」要不要也統一成「都不拿」，轉交玩法 PM。
- 截圖只用 Chrome 拍，主力瀏覽器的 Edge 沒有另外拍，接受。兩者同核心。
