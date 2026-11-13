# Phase RR-2 報告｜被強度下限卡住的重閃格改出較弱的候選並提醒（#160）

> 實作 agent，2026-11-13（Opus 5.5）。依據：06 6.34.3「強度下限」例外（玩法 PM `227b12678`，使用者原話「B提醒可能更弱」）、`docs/phases/PhaseRR-1報告.md` 待決 2。
>
> commit：`261004c8f`（後端、API、測試、OpenAPI 與前端型別）、`9a1c9292e`（前端提醒、確認、小標）、`3cdd5d1ab`（截圖）、`07be121ec`（歷程重推不了時不放寬）；本報告與上手筆記另一個 commit。

## 1. 做法

### 判定（只限重閃，整格判斷）

- `flash_offer.reflash_weaker(library, request)`：照原規則（不低於被換掉的那一筆，`floor_permille`）**一個候選都沒有**時是 `True`。範圍同 `has_options`（不指定類別、依用法統計的來源），所以是**整格**的判定：只要原規則有一個候選，就照原規則只出達得到的，不混進較弱的。
- 以下一律 `False`（照舊）：新的閃現（`slot` 為空）、完整技能第一次調整（還沒有「被換掉的那一筆」）、已存歷程重推不了（3W-R1，下限照存檔裡的定義）。
- 結果與 `has_options` 一樣快取在 `library.flash_option_cache`（鍵 `weaker:`＋同一個 SHA-256）。

### 放寬多少

- 較弱時 `_builder` 把 `floor_permille` 設 0：**只拿掉「不低於被換掉的那一筆」**，`power_floor` 照舊「不低於重閃前一筆」（＝新的閃現的規則；`STRICT_OPS` 照加 margin），也照舊要進預算窗、過全部驗證。見第 5 節待決 1。
- 選了以後寫進歷程的 `FlashRecord.floor_permille` 就是 0，`derive_chain` 重推得出同一張卡。沒有加存檔欄位、不進技能 ID 雜湊。
- `FlashOffer.weaker`、`FlashOption.weaker`（`exclude_if`：`False` 不輸出），所以存檔、parity 夾具逐字不變。

### API（提醒字全由後端送）

| 欄位 | 字 |
|---|---|
| `ReflashSlotOut.weaker`／`weaker_zh` | 「這一格重閃可能比原本弱」 |
| `ReflashSlotOut.weaker_confirm_zh` | 「這一格原本的變化特別強，這次重閃出的選項都會比原本弱。扣點後一定要選一個。還要重閃嗎？」 |
| `PendingFlashOut.weaker_foot_zh` | 「這次的選項都比原本弱，標 ▼ 的是變弱的地方。」 |
| `FlashOptionOut.weaker_tag_zh` | 「比原本弱」 |

常數在 `src/trpg/skillgen/flash_offer.py`（`REFLASH_WEAKER_ZH`、`REFLASH_WEAKER_CONFIRM_ZH`、`WEAKER_FOOT_ZH`、`WEAKER_TAG_ZH`），字照 6.34.3 條文。RR-1 的標灰（`available`、`problem_zh`）現在只留給放寬後仍然沒有候選的格子。OpenAPI 重產、`gen:api` 重跑。

### 前端（只做新增）

- 重閃入口（`client/src/run/CampfireSkillCare.tsx`）：較弱的格子不標灰，鈕裡多一行「▼ 這一格重閃可能比原本弱」（變弱樣式：無底無框＋▼）；按下去先跳確認框（伺服器的確認句，按鈕「重閃」「先不要」），按「重閃」才進原本的選類別（扣點前）。一輪營火與大世界成長面板共用。
- 選變體畫面（`client/src/screens/RunFlashPending.tsx`）：上固定區那句換成「一定要選一個。這次的選項都比原本弱，標 ▼ 的是變弱的地方」（窄版在 (i)）；每張卡類別標籤旁多「▼ 比原本弱」。
- 「前 → 後」沿用 FL-1b 的四種樣式，沒改。

**改到的前端檔案（合併時給 PM 處理衝突）**：
- `client/src/screens/RunFlashPending.tsx`（TXT-2 也在改）：只改 3 處——多一行 import `mustPickText`、拿掉 `FLASH_MUST_PICK_ZH` 的 import（改由 `mustPickText` 取）、`FlashHead` 兩處 `FLASH_MUST_PICK_ZH` 換成 `must`；`OptionCard` 的 `.fc-cat` 裡多 6 行小標。
- `client/src/run/CampfireSkillCare.tsx`、`client/src/styles/index.css`（最後多一行 import）。
- 新檔：`client/src/run/reflashWeaker.ts`、`client/src/styles/reflash-weaker.css`、`client/src/run/rr2ReflashWeaker.test.ts`。
- `client/src/api/schema.d.ts`、`client/openapi.json`（重產）。
- **沒改** `client/src/styles/flash.css`、`client/src/run/flash.ts`、`content/flash_templates.yaml`。

## 2. 重現案例

開發起始包 0、種子 2 打到營火，「灼燃・燃燒爆」（第 1 次蓄力、第 2 次 `keyword_imbue`、第 3 次 `major_intensify`）：

| | RR-1 | RR-2 |
|---|---|---|
| 重閃第 1 格 | 標灰（17 個候選全被蓄力的下限擋掉） | 可以按，掛提醒；扣 1 點出 4 個選項，全標「比原本弱」 |
| 第 1 格各選項的預算分數 | — | 18.9／18.9／18.81／20.79（被換掉的蓄力 22.68；都 ≥ 重閃前） |
| 重閃第 2、3 格 | 出得了題 | 不變（不標較弱，下限照被換掉的那一筆） |

選第 0 個後歷程第 1 筆 `floor_permille` 是 0，重推得出同一張卡。

## 3. 測試

- 新增 `tests/roguelite/test_reflash_weaker_rr2.py`（5 個）：
  - 重現案例：原規則沒有選項、`reflash_weaker` 真；入口欄位；扣點出題、每個選項第 1 格分數在「重閃前 ≤ 分數 < 被換掉的」；面板固定句與小標；選了下限 0、重推相同。
  - 達得到下限的第 2、3 格：不標較弱、`floor_permille > 0`、存檔 JSON 沒有 `weaker`。
  - 新的閃現一律不放寬。
  - **hypothesis 性質測試**（`derandomize=True`，各 6 例，種子 × 格子 1～3）：同種子同結果（清快取重算 `reflash_weaker`＋`make_offer` 相等，較弱時每個選項都標較弱、下限 0）；原規則有選項時，出題與「關掉放寬」（`mock.patch.object(flash_offer, "_weaker", return_value=False)`）逐字相同。
- 改了的既有斷言（預測內）：`tests/api/test_flash_api.py` 的 `reflash_slots` 多三個欄位。
- `tests/roguelite/test_retier.py::test_a_stale_history_keeps_the_reflash_floor` 第一版失敗（歷程重推不了時也放寬了，下限變 0）→ 改成 3W-R1 一律不放寬（`07be121ec`），測試照原樣通過。
- 前端新增 `client/src/run/rr2ReflashWeaker.test.ts`（4 個：`weakerSlot`、入口提醒不標灰、確認框、固定句與小標；舊資料沒欄位照常）。
- **預測與實際**：較弱欄位預設不輸出，只在原規則沒選項時才動，AI（`auto_flash_choice`）只重閃完整技能第一次調整（不放寬），所以預測 parity 夾具、存檔快照、模擬報表都不變；實際 slow 的 parity 與 flash 測試全過，沒有重產任何夾具或快照。
- `WORLD_RULES_VERSION` 沒升（見待決 3）。

## 4. 檢查（交件前）

| 指令 | 結束碼 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0 |
| `uv run lint-imports` | 0 |
| `uv run pytest -q -n 8 -m "not llm"`（含 slow：`skillgen/test_refactor_parity`、`roguelite/test_flash_run`、`test_flash_llm_run`、`test_flash_texts_run_lf1`、`skillgen/test_flash_cost_fl1a`／`fl1c`、`sim/test_flash_report`、`sim/test_flash_balanced_policy`；加 rr1、rr2、retier、flash API／文字／OpenAPI 快照、runs API、world growth／pregen、llm flash、cli run、skillgen flash 5 檔、`tests/world` 全部） | 0（2629 passed） |
| `uv run trpg battle --map bandit_lair --seed 7 --log-json …` ＋ `trpg battle replay …` | 0（重播驗證通過：73 個動作、254 個事件） |
| `corepack pnpm -C client exec vitest run src/run/ src/world/fl1cFlashNone.test.ts src/ui/statusBadges.test.ts` | 0（203 passed） |
| `corepack pnpm -C client exec vitest run src/ui/ src/world/` | 0（1450 passed） |
| `corepack pnpm -C client build` | 0 |

沒跑全量 `check.py`，沒做數值量測。

## 5. 待 PM 決定

1. **「低於下限」放寬到哪**：只拿掉「不低於被換掉的那一筆」，保留「不低於重閃前一筆」（＝新的閃現的下限）。條文寫「預算窗內、但低於下限的候選」，沒說能不能低於重閃前；最保守是保留。重現案例這樣就出得了 4 個。若放寬後仍沒有候選，照舊標灰。
2. **判定是整格的**：沿用 `has_options` 的範圍（不指定類別、依用法統計的來源）。所以：原規則下某個指定類別 0 個、其他類別有 → 不放寬，那一類照舊不能指定；整格較弱時，指定類別、LLM 提議也用較弱的下限，選類別畫面的數量也是較弱的數量。
3. **`WORLD_RULES_VERSION` 沒升（仍是 29）**：世界日誌只記成功的動作；以前被下限卡住的重閃會被拒、不進日誌，所以舊日誌裡的每一筆重閃照原規則都有選項，放寬不會觸發，重播結果不變。若要照「不確定就加」升成 30，只要改常數和 2 個寫死版號的測試。
4. **「比原本弱」的標法**：較弱模式下每個選項都標（條文說「這次重閃出的選項都會比原本弱」）。理論上重調時亂數可能讓某個選項碰巧回到被換掉那一筆的分數以上（原規則的下限會讓調整器往上推、放寬後不會），重現案例沒有發生（4 個都低於），性質測試只檢查「較弱模式下全部標較弱」。
5. **「前 → 後」的基準**：照 FL-1b，重閃比的是「被換掉那一筆之前」，所以重現案例的卡片上很多列是金色變好（比重閃前的原招），只有骰子等少數列是 ▼；「比原本弱」小標比的是被換掉的蓄力。兩者基準不同，截圖上看得出來。條文說「沿用 FL-1b」，所以沒改；要不要改成和被換掉的那一筆比，請玩法 PM 決定。
6. **重閃說明行**：營火重閃區的說明還寫「新選項不會比被換掉的更弱。」（`reflashNoteText`），現在有例外。條文沒提這句，沒改；要改的話只換這一行字。
7. **兩層確認**：較弱格子按下去先跳 #160 的確認框，按「重閃」後還是原本的選類別面板（「確定，扣 1 點並出題」）。照條文「按下去先跳確認」做在最前面，沒有合併。

## 6. 平衡疑慮

- 放寬只到「重閃前一筆」，所以較弱的重閃最差就是「當作這一格重新閃一次」；玩家可能用它把太強的蓄力換成別的方向，花 1 點換掉強度——這是條文允許的，數值（下限差多少）照工坊，沒量測。

## 7. 截圖（`docs/art/shots/RR-2/`，DPR 1，`?mute=1`，無頭 Chrome `--mute-audio`）

| 檔案 | 內容 |
|---|---|
| `01-entry-800.png`／`01-entry-1600.png` | 營火重閃區：第 1 格掛「▼ 這一格重閃可能比原本弱」，不標灰 |
| `02-confirm-800.png`／`02-confirm-1600.png` | 按下去的確認框（還沒扣點） |
| `03-options-800.png`／`03-options-1600.png` | 扣點出題後：每張卡「▼ 比原本弱」，(i) 打開顯示換過的固定句 |

做法：暫存區腳本把重現案例的一輪（靈感點補到 8）寫成存檔，自己開 `trpg serve --port 8796`（`TRPG_SAVE_DIR`、`TRPG_ACCOUNTS_DIR` 指暫存區）、無頭 Chrome 除錯埠 9571（`--remote-debugging-address=127.0.0.1`，開之前 `netstat` 確認兩個埠沒人用），CDP 先寫 `localStorage["trpg.currentRun"]` 再重整就接回營火。交件前用自己記下的 PID（伺服器 68948、Chrome 69436）關掉，8796、9571 已沒在聽。

## 8. 沒驗證

- Firefox、Safari 沒實機看；新增的 CSS 只用 flex、`inline-flex`、border 三角，沒用新語法。
- 大世界成長面板沒另外拍（與一輪共用 `ReflashSection`、`RunFlashPending`）。

## 開發 PM 裁定

- 接受，已合併。和 TXT-2 衝突的兩處（`flash_offer.py` 常數區、前端上手筆記第 148 點）都保留雙方內容，RR-2 那點改成第 149 點。合併後重產 OpenAPI，沒有差異。
- 待 PM 決定 3：`WORLD_RULES_VERSION` 不升。世界日誌只記成功的動作，以前被卡住的重閃會被拒、不進日誌，舊日誌重播結果不變。
- 待 PM 決定 1、2、4：照保守做法維持。1 是只拿掉「不低於被換掉那一筆」。
- 待 PM 決定 5、6、7（兩個基準並排、營火說明行的字、兩層確認）：轉交玩法 PM，回覆後只換字或另開小修。
- 平衡疑慮：轉玩法 PM 記進平衡待查。
