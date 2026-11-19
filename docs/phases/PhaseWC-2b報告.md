# Phase WC-2b 報告：WC-2 待決答覆

> 2026-11-19，實作者。規格 `docs/phases/PhaseWC-2b計畫.md`；來源是玩法交接 4.1.34 和 #167 補（使用者：「可以，1 階就行」）。
> 分支 `worktree-agent-ab393748361c4c5dd`（先 `git merge main` fast-forward 到 `2fb1f09d9`，含 SK-3c、SK-3d）。不 push。
> 沒有試數值、沒有跑平衡量測。沒有改 `docs/design/`、`config/`。
> 這一段之前，同一個分支先修了 WC-2 合併後的 2 個 slow 測試（`f13e022dc`），處理寫在 `docs/phases/PhaseWC-2報告.md` 末尾。

## 結果（一兩句）

三件都做完。卡片的元素和許願的命中判定改成同一個來源；「物理＋元素」1 階起做得到（例：火焰劍）。覆蓋表做不到 **98 → 90**：少的 8 組就是「物理＋各元素」，1 階的格子約 15～17%。極低維持 36。戰鬥不變比對 different=0。

## 交付項目

| 項目 | 狀態 | commit |
|---|---|---|
| 1 卡片照實寫元素 | 完成 | `27bc05871` |
| 2 物理＋元素做得到，1 階也可以 | 完成 | `d0ae76c0a` |
| 3 重跑覆蓋表、列出和 WC-2 的差別 | 完成 | `c785d9078` |

## 1. 做法

### 1.1 卡片照實寫元素（第 1 件）

- `content.skills.card_elements`：技能元素在前，之後接傷害效果自己寫的元素，依代碼排序。
  - 技能本身是物理時，以前直接回空的，現在照實寫出效果的元素。
  - 卡片和許願命中判定用的 `damage_elements` 是同一個來源。
- `narrative/skills._element_id`（卡片的元素顏色代碼）也改成取 `card_elements` 的第一個，讓顏色和那一行字一致。
- 規則上的技能元素（06 6.33，`skill_elements`）沒動。
- **預測受影響的手寫技能**：技能本身沒有元素、傷害帶元素的只有 2 招（全部內建技能掃過一遍）。

| 技能 | 元素一行 | 元素代碼 |
|---|---|---|
| `skill_marrow_thorn` | 無 → 毒素 | 無 → `poison` |
| `skill_rx_warning_mark` | 無 → 神聖 | 無 → `holy` |

- WC-2 已經改過的 5 招（`skill_wil_*` 4 招、`skill_wis_chain_radiance`）：技能本身有元素，顯示不變，例如「暗影、冰霜」。
- **快照**：後端沒有任何快照或夾具鎖這 2 招的元素欄，narrative、content、api 測試全過。前端的 `skillCards.json` 等夾具不含這 2 招，不用重產。
  - 唯一改的測試是 WC-2 自己的 `test_card_elements_only_for_elemental_skills`，改成 `test_card_elements_follow_the_wish_hits`：物理技能照實寫毒素，規則上的元素仍是空的。

### 1.2 物理＋元素（第 2 件）

- **命中**（`wish_pick.skill_tag_ids`）：技能有一段沒有元素（或寫物理）的傷害，就算帶「物理」，另外照舊加上傷害元素。所以一招同時有武器傷害和火焰傷害，就同時命中「物理」「火焰」。
  - 完全沒有傷害、也沒有元素的技能照舊算物理。
  - 全部傷害都帶元素的技能不算物理。
- **名額**：物理不佔元素名額（`element_slots`）。
  - `tag_limits` 的元素上限只算物理以外的元素。`wish_tags_problem`、`clean_wish_tags` 照這個擋，例如 1 階許「物理＋火焰＋冰霜」：檢查回傳「元素最多選 1 個（物理另外算）」，清理會丟掉冰霜。
  - 物理＋兩個元素要 2 階起，照 #167 的上限。
- **面板與 LLM**：新函式 `menu_limits` 在元素那一格多給 1，留給物理。
  - 面板的元素 `max`：1 階 1 → 2，2 階起 2 → 3。
  - LLM schema 的 `maxItems` 和 `<request>` 的 `max` 跟著改，系統指令加一句物理的說明。
  - `wish-tags/2 → /3`。
- **組合器**（`composer_dual.add_second_element`）：技能本身是物理（武器傷害沒有元素）時也能加一段元素傷害，做成「物理＋元素」，**1 階起就做**。
  - 驗證器不用放寬：第二元素門檻本來就只數物理以外的元素，加完仍是一個元素，所以不算第二元素。測試確認加完以後最低階級和原招相同。
  - 技能已經有一個元素時照舊是第二元素，要 2 階。
- **許願池**（`_dual_draws`）：願望有兩個元素時，候選只差其中一個（而且不是物理）就補上那個元素。
  - 「物理＋元素」不看第二元素的階級；兩個都不是物理時照舊要 2 階。
- **覆蓋表腳本**：
  - 拿掉「物理＋元素＝規則禁止」那條分類。
  - 物理的技能在每一階都另外記下「物理＋各元素」的版本（`D`），願望有兩個元素標籤（含物理）時算數。

### 1.3 覆蓋表（第 3 件）

`scripts/wish_coverage.py run --seeds 40 --workers 8`（768 桶，798 秒）＋ `report`，更新 `docs/phases/許願覆蓋表-WC2.md`。表的最後一節照舊和 WC-1 舊表對照。下面是和 WC-2 結果的差別：

| | WC-2 | WC-2b |
|---|---|---|
| 做不到 | 98（a 57、b 27、需人工 14） | 90（a 57、b 19、需人工 14） |
| 極低 | 36（a 22、需人工 14） | 36（a 22、需人工 14） |

- **做不到 → 做得到（8 組）**：物理配火焰、冰霜、雷電、毒素、風、大地、神聖、暗影，每一組都是。
  - 最好的一格約 17.5%。1 階 3 格約 15～17%，例如物理＋火焰在普通、稀有、史詩分別是 17.5%、16.5%、14.7%。
- 做不到 → 極低：0 組。新出現的做不到：0 組。極低清單的 36 組，名稱和 WC-2 完全相同。
- `buckets.json` 7.6 MB → 8.3 MB（多了物理技能的衍生版本）。

## 2. 戰鬥不變比對

同 WC-2 的腳本和 60 場（基準 `0815e3601`）：第 2 件做完後是 `battles=60 events=23897 different=0`。第 1 件只改卡片顯示，第 3 件只有資料，都碰不到戰鬥。

## 3. 版號

| 版號 | 改動 |
|---|---|
| `wish-tags/2 → /3` | 元素那一格多一個名額給物理（schema `maxItems`、`<request>` 的 `max`），系統指令加一句 |

`skill-proposal`、`LOG_FORMAT` 都沒動。API 的 schema 欄位不變，只有元素 `max` 的值變，所以沒有重產 OpenAPI。

## 4. 快照、夾具逐鍵核對

| 東西 | 預測 | 結果 |
|---|---|---|
| 卡片元素（第 1 件） | `skill_marrow_thorn`、`skill_rx_warning_mark` 兩招的 `element`、`element_id` | 沒有快照鎖這兩招，不用改快照；實際輸出跟預測一樣（毒素／`poison`、神聖／`holy`） |
| `refactor_3wr2.json`（parity） | 第 1、2 件都不會變：`card_elements` 不進出題，`add_second_element` 只有許願池和覆蓋表用 | 每個 commit 跑 `-m slow` parity，全過，沒有改任何鍵 |
| CLI 快照 | 不會變 | 每個 commit 跑 `-m slow tests/cli`，全過 |
| 面板、LLM 的元素上限 | `tests/api/test_wish_pk4.py` 兩處、`tests/llm/test_wish_pk4.py` 四處 | 照預測改：1 階 [2,1,2,1,1] → [2,2,2,1,1]，2 階 [2,2,…] → [2,3,…]，`maxItems` 1 → 2、2 → 3；檢查字串多「（物理另外算）」 |

## 5. 檢查

| 指令 | 時間點 | 結束碼 |
|---|---|---|
| ruff、format、`mypy src`、lint-imports | 每個 commit | 0 |
| `trpg content check` | 第 2 件 | 0 |
| `pytest tests/narrative tests/content tests/api`＋WC-2 雙元素測試（4947 passed、1 skipped） | 第 1 件 | 0 |
| `pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli`（980） | 第 1 件 | 0 |
| `pytest tests/skillgen tests/test_wish_coverage.py`（4587 passed、14 skipped） | 第 2 件 | 0 |
| `pytest tests/llm tests/api tests/world tests/roguelite tests/content tests/narrative`（7042 passed、1 skipped；和 skillgen 分開跑） | 第 2 件 | 0 |
| `pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli`（980） | 第 2 件 | 0 |
| 戰鬥不變比對 60 場 | 第 2 件 | different=0 |
| 前端 `tsc --noEmit` | 第 2 件之後 | 0 |
| 前端 `vitest run wish pk4Wish skillCard`（4 檔、49） | 第 2 件之後 | 0 |
| `wish_coverage.py run`、`report` | 第 3 件 | 0、0 |

- 補修 WC-2 那個 commit（`f13e022dc`）時，`-m slow tests/skillgen` 全部（962）和 `-m slow tests/cli`（44）都是 0。
- 沒跑全量 `scripts/check.py`、`tests/sim`，沒用 `-m ""`。

## 待 PM 決定（規格沒寫到、我先採保守做法的地方）

| # | 事項 | 我的做法 | 其他選項 |
|---|---|---|---|
| 1 | 卡片的元素顏色 | `element_id` 跟著元素那一行，物理技能的效果元素也上色（2 招） | 顏色照舊用規則上的技能元素，只改字 |
| 2 | 物理在面板上的位置 | 沒有另開一格，還是在「元素」清單裡，`max` 多 1，超過名額由伺服器擋：1 階先點兩個非物理元素時，送出才會被擋 | 面板拆出獨立的「物理」格（前端與 API 要改） |
| 3 | 物理＋兩個元素（2 階） | 許願池只補「差一個」的元素：物理技能一次只加一個元素，所以物理＋火＋冰要候選本來就有兩個裡的一個，再補另一個。覆蓋表沒有單獨算這種三個元素的組合 | 連續補兩次 |
| 4 | Mock 翻標籤 | 照 WC-2，Mock 只照物理以外的上限選，沒有特別示範物理＋元素 | Mock 也多給物理一格 |
| 5 | 「物理」的命中定義 | 有任何一段沒有元素的傷害（含接續段）就算物理，例如法術技的接續段是武器傷害 | 只看第一段傷害 |
