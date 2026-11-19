# Phase WC-2 報告：#167 許願覆蓋 5 題

> 2026-11-19，實作者（WC-2）。規格 `docs/phases/PhaseWC-2計畫.md`（main `0815e3601`）；來源 #167、玩法交接 4.1.32。
> 分支 `worktree-agent-ab393748361c4c5dd`（起點 main `0815e3601`，worktree 原本落後 main，先 fast-forward）。不 push。
> 數字一律是初值，接工坊；沒有試數值、沒有跑平衡量測與模擬（戰鬥不變比對與覆蓋表重跑除外）。沒有改 `docs/design/`、`config/`。

## 結果（一兩句）

第 1～6 項都做完，每項一個 commit。許願覆蓋表重跑：**做不到 181 → 98、極低 59 → 36**。舊表的 181 組裡有 74 組變成做得到（最好的一格 ≥ 2%），9 組變成極低，98 組還是做不到，沒有新出現的做不到。戰鬥不變比對 60 場在第 1、3、5 項之後都是 **different=0**。

## 交付項目

| 項目 | 狀態 | commit |
|---|---|---|
| 1 元素標籤上限（2 階起 2 個）＋組合器做雙元素 | 完成 | `e0c16eff5` |
| 2 一招一個形狀、一個種類 | 照現狀（加一個鎖定的測試） | `fa36aa56c` |
| 3 被動加「自身周圍」、被動作用在觸發者算單體 | 完成 | `f71c3c8df` |
| 4 吸血、聖光雙效算命中「治療」 | 完成 | `69335a213` |
| 5 補配方（層數 → 召喚 → 形態 → 元素） | 完成 | `00f4dfa43` |
| 6 重跑覆蓋表、和舊表對照 | 完成 | `5877e7118` |

## 1. 各項做法

### 1.1 元素上限（第 1 項）

- `skill_pick.yaml` `wish_tags.max_elements_dual: 2`。「2 階」不另外寫數字，用 `skill_budget.yaml` 的 `min_character_tier.second_element`（06 6.34.9 第二元素的門檻，初值 2）。
- `wish_pick.tag_limits(library, tier)` 和 `dual_elements` 決定上限。`wish_tags_problem`、`clean_wish_tags` 多 `tier` 參數，省略時當 1 階，最保守。
- 用到上限的地方都改照角色階級：
  - 引擎 `world/wish.py` 的兩處（新函式 `wish_tier`）；
  - LLM `match_wish_tags(tier=…)`：schema 的 `maxItems` 和 `<request>` 的 `max`；
  - API 預先生成 `world_pregen`；
  - 面板 `world_wish_view._tag_groups(library, tier)`：2 階的元素 `max` 是 2。前端照 `max` 畫，不用改。
- **組合器**：新模組 `skillgen/composer_dual.py::add_second_element`。
  - 對象：組好的技能（已有一個元素、有傷害、不是陷阱或複合技、效果數沒滿）。
  - 做法：第一個傷害後面多一段另一個元素的傷害，寫法同閃現「第二元素」；再用組合器同一套旋鈕重調（`composer_tuning.tune`），最後過驗證器（第二元素的 2 階門檻照舊）。
  - 許願池：`wish_pool._dual_draws` 在願望有兩個元素、角色 ≥ 2 階時，把「帶其中一個元素」的候選加上另一個，獨立串流 `pick.wish.dual`，最多 3 個新設計。
- **命中判定**：元素改用 `content.skills.damage_elements`，也就是技能元素加上傷害效果自己寫的元素，和驗證器的「第二元素」同一個定義（`validate._damage_elements` 改成呼叫它）。
- **卡片**：`card_elements` 用在 `narrative/skills._element_name`。技能有元素時，第二元素接在後面，例如「火焰、冰霜」；技能本身是物理時照舊不寫（06 6.33）。
- `wish-tags/1 → /2`：系統指令加一句「願望明確說到兩種元素、max 允許時才選兩個」。

### 1.2 形狀、種類（第 2 項）

照現狀，不改程式。新測試 `tests/skillgen/test_wish_limits_wc2.py` 鎖住：不管幾階，形狀、種類的上限都是 1；清理與檢查照舊丟掉第二個。

### 1.3 被動「自身周圍」（第 3 項）

- **資料**：`skeletons/passive.yaml` 的形狀改成 `[self, ring]`，`max_radius: 1`。`SkeletonDef` 多 `max_radius` 欄位。反應骨架不動。
- **驗證器**：
  - `skeleton.radius`：半徑超過骨架上限。
  - `passive.around`：環形被動以持有者為中心，`trigger.target` 只能是 `self`。
  - 環形不套「target self 時效果只能作用在自己」那條。
- **引擎**：`interpreter.use_triggered_skill` 遇到不是 `self` 的形狀時，作用在持有者周圍一圈（新函式 `targeting.around_area`，巨型單位照 `around_tiles`）。效果照 `affects` 結算。
- **組合器**：獨立串流 `composer.passive.around`，機率 `passive.around_permille: 150`（初值）。
  - 組出持有者周圍半徑 1 的被動，效果是對敵的傷害或有害狀態（同 `target: other` 的候選）。
  - 沒抽中的種子，結果和改前逐字相同。
- **命中判定**：形狀自身、`trigger.target` 不是持有者的被動算「單體」。作用在自己的被動照舊算「自身周圍」。
- 卡片的形狀一行顯示「環形（半徑 1）」（沿用既有的形狀文字）。
- `skill-proposal/21 → /22`：被動骨架選單多了 ring，在 `<available>` 這層，快照雜湊不變（同 SK-2b、SK-3b 的前例）。

### 1.4 吸血、聖光雙效（第 4 項）

`WishEffectTag` 多 `params` 欄位：效果上這些參數有值也算命中。`skill_pick.yaml` 的治療標籤加 `params: [lifesteal_permille, split_heal]`。測試用手寫的 `skill_life_drain`、`skill_holy_burst`。

### 1.5 補配方（第 5 項）

1. **層數**（`skillgen/composer_rider.py`）
   - 指定連擊、怒氣、專注、氣時，獨立串流 `composer.rider` 以 `structure.stack_rider_permille: 500`（初值）改走附帶配方：不指定關鍵字組一招主動技，再多一個累積或消耗那種層數（對象照層數的 owner），然後重調、驗證。
   - 沒抽中或做不出來時，照原本的蓄力骨架。
   - 範圍、控場、位移骨架的附帶原語加上 `add_stack`、`consume_stack`。連段、召喚的附帶本來就不限。
2. **召喚**
   - 許願池補抽「召喚」效果標籤時，指定召喚骨架（`wish_pick.SUMMON_HINT`，種類是主動那一族）。
   - 召喚物關鍵字有附帶配方「號令」：一般主動技＋對自己施加 `commanding`（你的召喚物傷害提高），機率 `structure.summon_rider_permille: 300`（初值）。
3. **形態**
   - `wish_pick.handwritten_keywords`：組合器不做的關鍵字（`composable: false`，目前只有形態）。
   - `handwritten_pool`：同關鍵字的手寫技能，排除傳說，角色階級要用得到。關鍵字標籤有形態時全部放進候選（來源 `pool`），出題條件照舊。
   - 組合器不再對形態抽種子。
4. **元素**
   - **冰霜＋範圍 0% 的原因是抽樣，不是規則**：
     - 指定範圍骨架時（2 階稀有 400 種子），冰霜範圍技 37 招，和其他元素一樣常見。
     - WC-1 不指定關鍵字的桶共 960 招合法技能，範圍形狀 41 招（4.3%）、冰霜 59 招（6.1%）。兩個疊起來每格期望不到 0.1 招，40 個種子抽不到。
   - 補法：`skillgen/composer_retheme.py::retheme` 把組合器技能的主題元素換掉。
     - 標籤、效果上的元素、名稱前綴、法術縮放屬性一起換；物理的武器主動技等於附魔成那個元素。
     - 結構、數值、代價都不動，再過一次驗證器（例：大地才有震波）。
   - 許願池 `_element_draws`：沒帶到願望元素的組合器候選，依「命中其他標籤數」由多到少換元素，每個元素最多 3 個。
- `skill-proposal/22 → /23`：三個骨架的附帶選單多了兩個原語，在 `<available>` 這層，快照雜湊不變。

### 1.6 覆蓋表重跑（第 6 項）

- `scripts/wish_coverage.py` 格式 `/1 → /2`。
  - 每個合法技能另記下「換成其他元素」與「2 階起加第二元素」的版本：前者願望有元素時算，後者有兩個元素時算。
  - 新增召喚桶（`…/summon`，主動、指定召喚骨架），和一般桶取較高的。
  - 形態不跑組合器，改看手寫技能池：有一招全帶到就算 100%，每個稀有度欄都一樣。
  - 分類規則：兩個元素不再一律算 b，只剩「物理＋元素」是 b；被動的形狀集合加上單體。
- `report` 會讀舊表（`docs/phases/許願覆蓋表.md`，留著沒動），在新表最後列出對照。
- 資料 `docs/phases/WC-2資料/buckets.json`；新表 `docs/phases/許願覆蓋表-WC2.md`。
- 768 桶 × 40 種子，8 個行程跑 960 秒。

## 2. 覆蓋表前後對照

| | WC-1 | WC-2 |
|---|---|---|
| 做不到 | 181（a 96、b 56、需人工 29） | 98（a 57、b 27、需人工 14） |
| 極低 | 59（a 30、需人工 29） | 36（a 22、需人工 14） |

- 舊表做不到的 181 組：
  - **做得到 74 組**：兩個元素 28、召喚 17、層數 12、形態 10、元素＋X 6、被動形狀 1。
  - **極低 9 組**：層數配潮濕、高處、召喚物、召喚 8 組，控制＋治療 1 組。
  - **還是做不到 98 組**，主要原因：
    - 形態＋X 30（手寫形態技沒有同時帶的）；
    - 需人工 14；
    - 召喚原語配其他 10；
    - 兩個形狀 10、兩個種類 3（照設計）；
    - 物理＋元素 8；
    - 被動、反應的形狀 6（被動配直線、錐形、範圍；反應配範圍等，照設計）；
    - 兩種層數同一招 6（附帶配方只加一種層數）。
- 沒有新出現的做不到。完整清單在新表最後一節。

## 3. 戰鬥不變比對

- 腳本放在 scratchpad，沒有 commit。
  - 改前＝`git archive 0815e3601` 的 `src content config`，`PYTHONPATH` 指向舊 `src`（印出載入路徑確認）。
  - 地圖預設陣容、效用 AI、`max_rounds=30`；整份事件、步驟、最終狀態比 SHA-256，去掉 `ruleset`、`ruleset_hash`、`format`。
  - 和 SK-3c 同一組 60 場：10 張一般圖 × 種子 1、2，加 4 張頭目圖 × 種子 3～12。

| 時間點 | 結果 |
|---|---|
| 改前基準 | `battles=60 events=23897` |
| 第 1 項做完 | `different=0` |
| 第 3 項做完（引擎改了被動的範圍） | `different=0` |
| 第 5 項做完（全部程式） | `different=0` |

第 3 項預期 different=0，結果也是：既有技能沒有環形被動，`use_triggered_skill` 只有形狀不是 `self` 時才走新路徑。第 4 項只改許願命中判定，第 6 項只改腳本，都碰不到戰鬥。

## 4. 版號

| 版號 | 改動 |
|---|---|
| `wish-tags/1 → /2` | 元素上限依角色階級（schema `maxItems`、`<request>` 的 `max`），系統指令加一句 |
| `skill-proposal/21 → /22` | 被動骨架形狀多 ring（`<available>`），快照雜湊同 /21 |
| `skill-proposal/22 → /23` | 範圍、控場、位移骨架附帶多 `add_stack`、`consume_stack`（`<available>`），快照雜湊同 /22 |
| 覆蓋表格式 `wish-coverage/1 → /2` | 腳本資料格式（非 LLM） |

`LOG_FORMAT` 沒動，事件和紀錄格式不變。API 的 schema 欄位不變，只有 `max` 的值會依角色變，所以沒有重產 OpenAPI。

## 5. 快照、夾具（先預測再核對）

| 東西 | 預測 | 結果 |
|---|---|---|
| 卡片元素一行（第 1 項） | 技能本身有元素、傷害另有元素的手寫技能才變：`skill_wil_chill_dread`、`skill_wil_static_silence`、`skill_wil_storm_hex`、`skill_wil_thunder_dread`、`skill_wis_chain_radiance`，從單一元素變成兩個 | 沒有快照或夾具鎖這 5 招的元素欄，narrative、api 測試全過，所以沒有改任何快照檔 |
| LLM 提議 prompt 快照 | 雜湊不變（只動 `<available>`） | 不變，照前例升版並新增同雜湊的鍵 |
| 組合器輸出（第 3、5 項） | 只有被新串流抽中的種子會變；鎖組合器輸出的測試只有「明確被動一律 self」 | `test_random_composer::test_explicit_passive…` 一條斷言改成 self 或 ring（ring 時半徑 1、target self）；其他快照不變 |
| 骨架結構測試（第 5 項） | `test_skill_rules_content` 範圍骨架的附帶集合 | 加 `add_stack`、`consume_stack` 兩項，控場、位移另加包含檢查 |
| 夾具、OpenAPI | 不會變 | 沒有重產 |

## 6. 檢查

| 指令 | 時間點 | 結束碼 |
|---|---|---|
| `ruff check src tests`、`ruff format --check src tests` | 每個 commit | 0 |
| `mypy src`（675 檔）＋新測試檔 | 每個 commit | 0 |
| `lint-imports`（14 kept） | 每個 commit | 0 |
| `trpg content check` | 第 1、3、5 項 | 0 |
| `pytest tests/skillgen -n 8`（4563／4567／4577 passed、14 skipped） | 第 1、3、5 項 | 0（第 3 項第一次有 1 條預期的斷言失敗，改完重跑該檔 0） |
| `pytest tests/narrative tests/content`（3614） | 第 1 項 | 0 |
| `pytest tests/world tests/roguelite`（1607） | 第 1 項 | 0 |
| `pytest tests/api`（1325 passed、1 skipped） | 第 1 項 | 0 |
| `pytest tests/llm tests/content tests/narrative`（4110） | 第 3 項 | 0 |
| `pytest tests/engine tests/test_architecture.py`（5065） | 第 3 項 | 0 |
| `pytest tests/world tests/roguelite tests/api`（2932） | 第 3 項 | 0 |
| `pytest tests/content tests/api`＋許願相關（4501） | 第 4 項 | 0（另有 1 個 error 是還沒改的覆蓋表測試，第 6 項修好） |
| `pytest tests/world tests/roguelite tests/api tests/content tests/narrative tests/llm tests/test_wish_coverage.py`（7047 passed、1 failed） | 第 5 項 | 1（骨架結構測試，預期的；改完重跑該檔 15 passed，0） |
| `pytest tests/test_wish_coverage.py`（6） | 第 6 項 | 0 |
| `wish_coverage.py run --seeds 40 --workers 8`、`report` | 第 6 項 | 0、0 |
| 前端 `tsc --noEmit` | — | 0 |
| 前端 `vitest run wish pk4Wish skillCard`（4 檔、49） | — | 0 |
| 戰鬥不變比對 60 場 | 第 1、3、5 項 | different=0 |

- `tests/llm` 和 `tests/skillgen` 沒有同時跑。
- 沒跑全量 `scripts/check.py`、`-m slow`、`tests/sim`、平衡量測。
- 沒有新增 `# noqa`；`wish_pick._compose` 加了 `PLR0917`，和同檔的 `_draw`、`_tag_draws` 一樣是一次抽樣的參數。

## 待 PM 決定（規格沒寫到、我先採保守做法的地方）

| # | 事項 | 我的做法 | 其他選項 |
|---|---|---|---|
| 1 | 「元素」的命中與卡片 | 命中用驗證器的第二元素定義（技能元素＋傷害效果的元素）；卡片只在技能本身有元素時接上第二元素，物理技能照舊不寫。影響 5 招手寫技能的卡片（見第 5 節），以及 `skill_marrow_thorn`、`skill_rx_warning_mark` 的許願元素命中（物理 → 毒素／神聖） | 卡片也把物理技能的效果元素寫出來；或命中只看技能元素 |
| 2 | 物理＋元素 | 算 b（物理＝沒有元素），雙元素不處理物理 | 把「武器傷害＋元素傷害」算成物理＋元素 |
| 3 | Mock 翻標籤 | `mock_wish_tags_client` 照 1 階上限（最多 1 個元素），既有 Mock 結果不變；真模型照角色階級 | Mock 也帶階級 |
| 4 | 被動「自身周圍」的細節 | 只有環形半徑 1、`trigger.target` 一定是 self；組合器只做對敵（傷害或有害狀態），不做周圍友方治療；機率 150‰ 是初值。驗證器允許手寫或 LLM 做對友的環形被動 | 開放組合器做周圍治療或護盾；半徑放進工坊 |
| 5 | 被動「作用在自己」 | 照舊算「自身周圍」，只有作用在觸發的那個人才算單體 | 也算單體 |
| 6 | 層數附帶配方開放的骨架 | 範圍、控場、位移的附帶加 `add_stack`、`consume_stack`。驗證器和 LLM 也因此放寬；機率 500‰、號令 300‰ 是初值。兩種層數同一招還是 0（只加一種） | 蓄力骨架加第二種層數的配方；開放打擊骨架 |
| 7 | 召喚的「組合器會抽」 | 只在許願的「召喚」效果補抽時指定召喚骨架，一般組合器的召喚機率不動（不調數值）。召喚原語配其他（傷害、範圍等）仍受 `others_affect: self` 限制，還有 10 組做不到 | 一般出題也提高召喚機率（數值，交工坊） |
| 8 | 換元素只在許願池用 | 一般三選一不換元素。範圍形狀在許願池本來就少，「冰霜＋範圍」要多許幾次才出得來（測試看 8 次許願） | 許願的形狀標籤也像召喚一樣指定骨架 |
| 9 | 形態候選數量 | 同關鍵字的手寫技能全部放進候選（沒套 `pool.handwritten_max`），由願望相合排序 | 套 `handwritten_max` |
| 10 | 吸血、聖光雙效 | 只改命中判定；組合器不做吸血或聖光雙效，所以「傷害＋治療」只有手寫的 `skill_holy_burst` 帶到，覆蓋表仍是 a | 組合器加吸血配方 |
| 11 | 工坊白名單 | 新的機率（`passive.around_permille`、`structure.stack_rider_permille`、`summon_rider_permille`）都在 `skill_composer.yaml`，這個檔本來就不在工坊白名單，所以沒加；`wish_tags.max_elements_dual` 跟既有的上限一樣沒開 | 開放 `skill_composer.yaml` 的這幾個值 |
| 12 | 覆蓋表的算法 | 換元素、雙元素的版本只要做得出來就算這個種子成功（許願池實際每個元素最多補 3 個，算是偏樂觀的上界）；形態有一招全帶到就算 100%。`buckets.json` 從 0.8 MB 變成 7.6 MB（多了衍生版本的簽名） | 照許願池的上限模擬；資料改存摘要 |
| 13 | 提議版號升兩次 | 第 3、5 項各升一次（/22、/23），兩次的快照雜湊都不變，照 SK-2b、SK-3b 的前例 | 合成一次 |
