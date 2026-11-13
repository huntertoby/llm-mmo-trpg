# Phase RR-2b 報告｜重閃的比較基準改成現在的卡，兩層確認合成一層（#160）

> 實作 agent，2026-11-13（Opus 5.5）。依據：06 6.34.3 #160 第 2～4 點（玩法 PM `de08c40a2`，回覆 RR-2 待決 5～7），派工單原字。
>
> commit：`97dac163a`（後端基準、API 欄位、測試、OpenAPI 與前端型別、開發頁夾具）、`997326e10`（前端一層提醒、撤小標、營火說明行）、`b8d6ebc0e`（截圖）；本報告與上手筆記另一個 commit。

## 1. 做法

### 比較基準（所有重閃）

- `api/run_presenter._flash_before` 一律回傳玩家現在的整張卡（`skill_defs(library, run, [skill_id])[0]`），閃現與重閃同一套。`PendingFlashOut` 的 `changes`、`headline_zh`、`say_zh`、`base_stats`、`terms` 都跟著改。
- **出題起點沒改**：`flash_offer.skill_before`（候選來源、LLM 提議、強度下限）照舊。所以引擎、存檔、parity、模擬、AI 都不受影響。
- 變小的欄位照 FL-1b 的「變弱」樣式畫（方向還是由後端 `flash_changes` 決定，前端沒改）。
- 撤掉「比原本弱」小標：`WEAKER_TAG_ZH`、`FlashOptionOut.weaker_tag_zh`、前端 `.fc-weaker` 都刪了。引擎的 `FlashOption.weaker` 留著，因為下限 0 要寫進歷程。

### API 欄位與字（全由伺服器給）

| 欄位 | 字 |
|---|---|
| `ReflashSlotOut.weaker_zh`（入口＋選類別面板） | 「這一格原本的變化特別強，重閃後這部分會變弱」 |
| `ReflashSlotOut.weaker_pick_zh`（取代 `weaker_confirm_zh`） | 「整招不會比現在弱；扣點後一定要選一個。」 |
| `PendingFlashOut.weaker_foot_zh` | 「被換掉的部分會變弱，整招不會比現在弱；標 ▼ 的是變小的地方。」 |

常數在 `src/trpg/skillgen/flash_offer.py`：`REFLASH_WEAKER_ZH`、`REFLASH_WEAKER_PICK_ZH`、`WEAKER_FOOT_ZH`。OpenAPI 和前端型別都重產了。

### 前端

- `CampfireSkillCare.tsx`：拿掉 `ReflashWeakerConfirm` 和 confirm 狀態，按重閃格就直接開 `FlashChooser`，並傳 `weaker={weakerSlot(...)}`。
- `FlashChooser.tsx`：新增選填的 `weaker` prop。有值時，在標題下、扣點說明之前加一行 `.reflash-weaker-lead`，內容是 ▼＋`weaker_zh`＋「。」＋`weaker_pick_zh`。扣點仍然只在這一層的「確定」；按「先不要」關掉就不重閃、不扣點。
- `RunFlashPending.tsx`：刪掉 `.fc-weaker` 小標。上固定區的句子照舊用 `mustPickText`，組成「一定要選一個。」＋伺服器給的句子。
- 營火說明行 `reflashNoteText` 的結尾改成「新選項整招不會比現在弱；標 ▼ 的是換掉後變小的地方。」這句仍是前端字，見待決 2。
- `styles/reflash-weaker.css`：刪掉 `.fc-weaker`，加上 `.reflash-weaker-lead`（長句可以折行，三角對齊第一行）。

## 2. 預測與實際

開工前寫下的預測（`scratchpad/rr2b/prediction.txt`）與實際結果：

| 項目 | 預測 | 實際 |
|---|---|---|
| `tests/roguelite/test_reflash_weaker_rr2.py` | 失敗（常數改名或刪除、`weaker_tag_zh`） | 舊版：ImportError，符合預測。已改寫，並新增「前＝現在的卡」的斷言（較弱格與一般格都有） |
| `tests/api/test_flash_api.py` | 失敗（`weaker_confirm_zh` 改名） | 舊版第 `test_the_backend_sends_reflash_slots_and_inherit_rules` 失敗，符合預測，改欄位名 |
| `tests/api/test_openapi_snapshot.py` | 失敗（schema 變了） | 失敗，符合預測；重產 OpenAPI 後通過 |
| 前端 `rr2ReflashWeaker.test.ts`、`world/pnl4Followups.test.ts` | 失敗（字、確認框、說明行） | 已改寫或改字，通過 |
| fl1a／fl1b／fl1c／fl1f／fl1g／lf3 文字測試、runs API、rr1、retier、`test_flash_world` | 不變 | 不變，全部通過 |
| parity、flash_run、sim、CLI 雜湊 | 不變 | 不變（見第 3 節） |
| 開發頁夾具 `flashChoice.json` | **不變** | **預測外的差異**：5 組各多一行 `"weaker_foot_zh": null`。原因是 RR-2 加了 `PendingFlashOut.weaker_foot_zh` 後沒有重產這份夾具，跟這次的改動無關；夾具裡沒有重閃，選項內容一字未變。派工單要求重產，所以保留這個差異 |

另外，我自己加的一個斷言失敗了，不在預測內：「較弱重閃的每個選項，整招都不低於現在的卡」。這是規則面的發現，見待決 1。

## 3. 檢查（交件前）

| 指令 | 結束碼 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0（1580 個檔案） |
| `uv run lint-imports` | 0 |
| `uv run pytest -q -n 8 -m "not llm"`（含 slow：`skillgen/test_refactor_parity`、`roguelite/test_flash_run`、`test_flash_llm_run`、`test_flash_texts_run_lf1`、`skillgen/test_flash_cost_fl1a`／`fl1c`、`sim/test_flash_report`、`sim/test_flash_balanced_policy`；另含 rr1、rr2（含 hypothesis 性質測試）、retier、`tests/api/` 全部、`tests/llm/` 全部、`world/test_flash_world`、`world/test_growth`） | 0（2701 passed、1 skipped） |
| `uv run trpg battle --map bandit_lair --seed 7 --log-json …`，再 `trpg battle replay …` | 0（重播驗證通過：73 個動作、254 個事件） |
| `corepack pnpm -C client exec vitest run src/run/ src/world/pnl4Followups.test.ts src/screens/ src/ui/ src/dev/` | 0（72 個檔案、872 passed） |
| `corepack pnpm -C client build` | 0 |

沒有跑全量 `check.py`。

## 4. 待 PM 決定

1. **「整招不會比現在弱」引擎沒有保證（規則面，需要先問）**：#160 第 2 點寫「重閃後整招的預算分數不低於重閃前」照舊保留，派工單第 4 點也說「不低於重閃前」維持。但引擎實際保證的是 **被換掉那一格不低於它的前一筆**（`power_floor`：重推到第 N 格的那張卡，不低於第 N−1 格的那張卡），**不是** 整張卡不低於玩家現在的卡。被換掉那一格之後的各筆會重推，整招可能比現在弱。為了核對提醒字，我用暫存區腳本 `scratchpad/rr2b/whole_check.py` 看了開發起始包 0、種子 2／3／5／7 的營火，比較每一格重閃的出題選項與現在的卡的 `budget_power`（沒有調數值）：
   - 種子 2「灼燃・燃燒爆」第 1 格（較弱）：現在是 23.62，4 個選項是 21.73／23.62／21.78／21.73，**有 3 個整招比現在弱**。
   - **一般重閃也有**：種子 2 第 3 格有 1 個（20.0 對 23.62，大變化格）；種子 7 第 1、2、3 格各有 1 個（例如 22.1 對 22.5）。
   - 所以新的字「整招不會比現在弱」（入口、選類別面板、固定句、營火說明行），以及舊的「選哪個這招整體都會強一點」，在這些案例都不成立。這次照派工單原字做完，**引擎沒改**。可以選的方向：(a) 引擎在重閃時加一道「整招預算不低於現在的卡」的篩選（規則改動，可能讓更多格標灰）；(b) 改字，不保證整招。
   - 換成新基準之後，畫面上的「前 → 後」會如實顯示這些 ▼。
2. **營火說明行是前端字**：派工單第 3 點說「字都由伺服器給」，範圍是提醒字。第 2 點的營火說明行原本就由前端用 `reflashNoteText` 依價格組成，這次只換字，沒有搬到伺服器。要搬的話，可以在 `FlashRulesOut` 加一個欄位。
3. **選類別面板那一行放在標題下**：「最上面」我解讀成標題下的第一行，排在扣點說明之前。標題本身仍在最上面。
4. **欄位改名** `weaker_confirm_zh` → `weaker_pick_zh`：意思已經改了（不再是確認句），所以直接改名。前端沒有其他地方讀舊欄位。

## 5. 截圖（`docs/art/shots/RR-2b/`；DPR 1，`?mute=1`，無頭 Chrome 加 `--mute-audio`）

| 檔案 | 內容 |
|---|---|
| `01-entry-800.png`／`01-entry-1600.png` | 營火重閃區：第 1 格掛「▼ 這一格原本的變化特別強，重閃後這部分會變弱」，不標灰；說明行是新字 |
| `02-chooser-800.png`／`02-chooser-1600.png` | 按下去直接開選類別面板：標題下一行是 ▼ 提醒＋「整招不會比現在弱；扣點後一定要選一個。」，沒有確認框 |
| `03-weak-options-800.png`／`03-weak-options-1600.png` | 扣點出題後，(i) 打開顯示「一定要選一個。被換掉的部分會變弱，整招不會比現在弱；標 ▼ 的是變小的地方。」；卡上沒有「比原本弱」小標；「前」是現在的卡（冷卻 4 → 2 回合，傷害 2d6 → ▼1d6） |
| `04-normal-options-800.png`／`04-normal-options-1600.png` | 一般重閃（第 2 格）：「前 → 後」用現在的卡，被換掉的部分變小的列畫 ▼（例：地面 積水 → ▼ 沒有） |

拍法：
- 存檔：暫存區腳本 `make_saves.py` 把重現案例的一輪寫成存檔，靈感點 8，每張圖用一個 run id。
- 伺服器：自己開 `trpg serve --port 8823`，`TRPG_SAVE_DIR`、`TRPG_ACCOUNTS_DIR` 指到暫存區。
- 瀏覽器：無頭 Chrome，除錯埠 9583，加 `--remote-debugging-address=127.0.0.1`。開伺服器和 Chrome 之前都先用 `netstat -ano` 確認埠沒人用；8796 有人在用，所以換了埠。
- 操作：CDP 先寫 `localStorage["trpg.currentRun"]` 再重整。(i) 的說明要用 `Input.dispatchMouseEvent` 把滑鼠移到上面才會出現。
- 收尾：交件前用自己記下的 PID 關掉伺服器（42736，連同子程序 50484）。Chrome（35500、66648）由腳本自己結束。8823、9583 已經沒有在聽。

## 6. 沒驗證

- Firefox、Safari 沒有實機看。新增的 CSS 只用了 flex、`margin-top: em`，沒有新語法。
- 大世界成長面板沒有另外拍。它和一輪營火共用 `ReflashSection`、`FlashChooser`、`RunFlashPending`。

---

## RR-2c｜整招篩選與 #160 例外改字（玩法 PM `a6c36fe30`，回覆 RR-2b 待決 1）

> 同一個分支接著做。開工前先 `git merge main`，拿到 `a6c36fe30`。commit：4efe5e683（引擎、API、測試、OpenAPI 與前端）、d3fa0e993（截圖）；本節與上手筆記另一個 commit。

### c1. 做法

- **整招篩選（一般重閃照 (a)）**：`flash_offer._Builder` 多一個 `whole_floor`，值是玩家現在那張卡的 `budget_power`，由 `_whole_floor` 計算：取已存歷程重推的最後一筆，沒有任何一筆時用原本的技能加預算上限加成；3W-R1 歷程重推不了時用 `request.current`。
  - 重閃（`slot` 不為空）時，新整招低於 `whole_floor` 的選項不合格。
  - 這是推導完成後的過濾，不改推導本身。所以 `floor_permille`、歷程重推、存檔欄位都不變。原本的格下限（「這一格不低於被換掉的那一筆」）照留，兩道一起套。
  - **轉型不篩**：照 3W-3「轉型不設下限」處理，見待決 c1。
- **#160 例外格（照 (b)）**：
  - 判定改成「格下限＋整招篩選後一個都不剩」。`_weaker` 用嚴格的 builder 試，取代 RR-2 原本的判定。新的閃現、完整技能第一次調整、3W-R1 照舊不放寬。
  - 例外格兩道下限都不套，改出預算窗內的候選。
  - `FlashOffer.weaker` 表示這一格是例外格；`FlashOption.weaker` 表示這個選項的整招低於現在的卡，只有這些選項標「比原本弱」。
- **字**（`flash_offer` 常數，全由伺服器送）：

  | 欄位 | 字 |
  |---|---|
  | `ReflashSlotOut.weaker_zh`（入口＋選類別面板） | 「這一格重閃後，這招可能比現在弱」 |
  | `ReflashSlotOut.weaker_pick_zh` | 「扣點後一定要選一個。」 |
  | `PendingFlashOut.weaker_foot_zh` | 「這次的選項可能比現在弱；標 ▼ 的是變小的地方。」 |
  | `FlashOptionOut.weaker_tag_zh`（加回） | 「比原本弱」，只給整招低於現在的選項 |

  一般重閃的「選哪個這招整體都會強一點」和營火說明行不改，因為補上篩選後就成立了（轉型除外，見待決 c1）。
- **前端**：`.fc-weaker` 小標加回 `RunFlashPending` 的 `.fc-cat`，樣式在 `reflash-weaker.css`。選類別面板那一行照舊是 `weakerLeadText`，現在顯示「這一格重閃後，這招可能比現在弱。扣點後一定要選一個。」
- 前 → 後的基準照舊用現在的卡（RR-2b）。

### c2. 版號

- **`WORLD_RULES_VERSION` 29 → 30**：
  - 原因：世界日誌重播時，重閃會重新出題（`growth._flash` → `open_flash` → `make_offer`）。整招篩選會讓舊日誌裡的重閃出不同的選項，`flash_pick` 的索引就會對到別的變化，同一份日誌重播出不同結果。
  - 例外格的判定也改了：舊日誌裡被 RR-2 判成較弱、但現在整招篩選後仍有選項的格子，出題會變。
  - 寫死版號的兩個測試已同步：`tests/api/test_pr2a_range_practice.py`、`tests/world/test_opening_stages.py`。`save.py` 的版號說明加了第 30 條。
- **`CHAR_FORMAT`、`SAVE_FORMAT`、日誌格式都不升**：存檔欄位沒變。`FlashOption.weaker` 的意思改了，但值為 `False` 時不輸出；存檔裡還沒選的題目照舊讀得進來。
- 一輪的存檔沒有日誌重播，不受影響。

### c3. 預測與實際

預測寫在 `scratchpad/rr2b/prediction_c.txt`，開工前寫下。

| 項目 | 預測 | 實際 |
|---|---|---|
| 重播（bandit_lair 種子 7） | 不變（沒有閃現） | 不變（重播驗證通過） |
| parity（`test_refactor_parity`） | 不變（只出新的閃現） | 不變（通過，沒重產） |
| Mock（`tests/llm`、`llm_propose_mock.txt`） | 不變（沒有重閃請求） | 不變（`tests/llm/` 全部通過，沒重產） |
| CLI 快照（`tests/cli/test_output_snapshots.py`） | 不變（AI 只重閃完整技能第一次調整，那一步的輸入就是現在的卡，下限已經保證整招不低於現在） | 不變（25 passed，沒重產） |
| 模擬報表（`sim/test_flash_report`、`test_flash_balanced_policy`） | 不變，理由同上 | 不變（slow 測試通過，沒重產） |
| `test_reflash_weaker_rr2.py` | 要改（字、選項 weaker 的意思、性質測試）；預測重現案例第 1 格仍是例外格，4 個選項不變 | 照預測：重現案例第 1 格仍是例外格，4 個選項逐字不變，其中 3 張整招低於現在；測試已先改成新規則，跑起來通過 |
| `test_openapi_snapshot.py` | 要重產（`weaker_tag_zh` 加回、說明字變） | 已重產（OpenAPI 加 11 行、`schema.d.ts` 加 2 行） |
| 版號測試 2 個 | 要改 | 已改 |
| `test_flash_run`、`test_flash_world` | 不會失敗 | 不變（沒改測試，直接通過） |
| 開發頁夾具、前端 run 夾具 | 不變（沒有重閃） | 不變（沒重產） |
| 前端 `rr2ReflashWeaker.test.ts` | 要改字、加回小標 | 已改 |

### c4. whole_check 再核對（種子 2、7）

開發起始包 0，打到營火，每一格重閃都出一次題，比較每個選項的整招 `budget_power` 和現在的卡：

| 種子／格 | 種類 | 現在 | 選項整招 | 低於現在的 | 小標 |
|---|---|---|---|---|---|
| 2／1 | 例外格 | 23.62 | 21.73／23.62／21.78／21.73 | 3 | 3 張（等於現在的那張不標） |
| 2／2 | 一般 | 23.62 | 23.62／25.52／23.62／23.62 | 0 | — |
| 2／3 | 一般 | 23.62 | 23.86／**20.0（轉型）**／23.62／23.86 | 1（轉型） | — |
| 7／1 | 一般 | 22.5 | 22.5／24.38／22.5／22.5 | 0（RR-2b 時 22.1 那個被篩掉了） | — |
| 7／2 | 一般 | 22.5 | 22.5／24.38／22.5／22.5 | 0（RR-2b 時 21.88 那個被篩掉了） | — |
| 7／3 | 一般 | 22.5 | 22.5／22.75／**19.38（轉型）**／22.5 | 1（轉型） | — |

種子 3、5 也全部不低於現在。剩下低於現在的只有大變化格的轉型保底，見待決 c1。

### c5. 測試

- `test_reflash_weaker_rr2.py`：
  - 重現案例改成「下限 0，整招低於現在的才標較弱（3 張），小標對得上」。
  - 性質測試 `test_same_seed_same_offer` 改成「`option.weaker == 例外格 and 整招低於現在（轉型除外）`」。
  - `test_reachable_floor_keeps_the_original_offer` 不改，它比對的是嚴格出題（現在已含整招篩選）。
  - **新增性質測試** `test_normal_reflash_never_weakens_the_whole_skill`：營火這一輪所有閃過的格子 × 種子 × 不指定或指定類別。一般重閃的每個選項，整招都不低於現在的卡，轉型除外。
- 前端 `rr2ReflashWeaker.test.ts`：新字，小標只畫在有 `weaker_tag_zh` 的那張卡。

### c6. 檢查

| 指令 | 結束碼 |
|---|---|
| `uv run ruff check .`、`ruff format --check .` | 0／0 |
| `uv run mypy` | 0（1580 個檔案） |
| `uv run lint-imports` | 0 |
| `uv run pytest -q -n 8 -m "not llm"`（含 slow：rr2、`test_flash_run`、rr1、retier、`world/test_flash_world`、`test_growth`、`test_opening_stages`、`tests/api/` 全部、`tests/skillgen/` 全部（含 parity、fl1a、fl1c）、`tests/llm/` 全部、`sim/test_flash_report`、`test_flash_balanced_policy`、`test_flash_llm_run`、`test_flash_texts_run_lf1`） | 0（6861 passed、15 skipped） |
| `uv run pytest tests/cli/test_output_snapshots.py` | 0（25 passed） |
| `trpg battle --map bandit_lair --seed 7`，再 `trpg battle replay` | 0（重播驗證通過：73 個動作、254 個事件） |
| `vitest run src/run/ src/world/pnl4Followups.test.ts src/screens/ src/ui/ src/dev/` | 0（872 passed） |
| `corepack pnpm -C client build` | 0 |

### c7. 截圖（`docs/art/shots/RR-2b/c*`；800、1600，DPR 1，`?mute=1`，`--mute-audio`）

| 檔案 | 內容 |
|---|---|
| `c01-entry-*.png` | 入口：「▼ 這一格重閃後，這招可能比現在弱」 |
| `c02-chooser-*.png` | 選類別面板最上面：「▼ 這一格重閃後，這招可能比現在弱。扣點後一定要選一個。」 |
| `c03-weak-options-*.png` | 出題後 (i)：「一定要選一個。這次的選項可能比現在弱；標 ▼ 的是變小的地方。」；4 張卡有 3 張標「▼ 比原本弱」，選中的那張「多等幾回合再用」整招等於現在，不標 |

- 伺服器：自己開 `trpg serve --port 8823`，PID 50748，交件前已用這個 PID 關掉。
- 瀏覽器：無頭 Chrome，除錯埠 9583，加 `--remote-debugging-address=127.0.0.1`，由腳本自己結束。
- 開之前都先用 netstat 確認埠沒人用；8823、9583 現在都已經沒在聽。

### c8. 待 PM 決定

1. **轉型不套整招篩選**：照 3W-3「轉型不設下限」處理。大變化格重閃時，轉型保底的整招可能比現在弱（種子 2 第 3 格是 20.0 對 23.62，種子 7 第 3 格是 19.38 對 22.5）。所以這兩種格子上，「選哪個這招整體都會強一點」對轉型那張不成立，和新的閃現原本就有的轉型例外一樣。若要轉型也篩，只要在 `_Builder.option` 拿掉 `variation.source != "transform"` 這個條件，但大變化格會更常沒有轉型保底。
2. **格下限照留**：這次是「加一道整招篩選」。原本「這一格不低於被換掉的那一筆」（`floor_permille`，會影響推導時的重調）沒有拿掉；拿掉的話會改到推導結果與存檔裡的歷程。
3. **例外格裡整招不低於現在的選項不標小標**：照 #160 第 4 點「達到的不加」。所以重現案例 4 張只有 3 張標。

## 開發 PM 裁定（RR-2b＋RR-2c）

- 接受，已合併。一般重閃加了整招篩選；整招篩選後沒有候選的格子，照 #160 例外處理。`WORLD_RULES_VERSION` 從 29 升到 30，理由見 RR-2c 節。
- 轉型不套整招篩選：玩法 PM 選 (b)，只換兩句字（docs/玩法PM交接.md 4.1），排進下一段動到閃現字的工作，已記在交接待辦 (e3h)。
- 待 PM 決定 2、3 照保守做法維持。
