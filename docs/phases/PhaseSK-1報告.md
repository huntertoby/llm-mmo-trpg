# 階段 SK-1 報告：#166 第 1 組（距離條件、移動過折扣、閃現側變與補模板、新方向優先製造、變奏讀出招順序）

> 2026-11-19，實作者（SK-1）。規格 `docs/phases/PhaseSK-1計畫.md`；設計 06 6.38 第 1、2、3、6、7 點（#166）。
> 分支 `worktree-agent-a01da20cc36fe897d`（從 main `be42035a5` 起，沒有 rebase SK-2）。數字一律是初值，接工坊，沒有試數值、沒有跑平衡量測。

## 結果（一兩句）

五項都做完、各有測試鎖住；戰鬥不變比對 46 場 different=0。閃現 1 階單體白板的候選變多（PK-3 的 10 個情境：候選 75 → 91、只有 1 個候選的格子 11 → 9）。

## 交付項目

| 項目 | 狀態 | commit |
|---|---|---|
| 1 距離條件「貼身」「遠距」（6.38-1） | 完成 | `fc6debfdf` |
| 2「本回合移動過」折扣調小（6.38-2） | 完成 | `ac1c01b9e` |
| 5 戰場變奏讀「本回合施放過帶某標籤的技能」（6.38-7） | 完成 | `fe1761af2` |
| 4 三選一「新方向」優先製造卡（6.38-6） | 完成 | `1af0a319e` |
| 3 閃現側變與補模板（6.38-3） | 完成 | `44621a8b7`（parity 夾具與一個序列化修正在 `5bf7ac3eb`） |

### 1. 距離條件（`point_blank` 貼身／`long_range` 遠距）

- 條件資料 `content/skill_conditions.yaml`（harshness `common`，照一般條件打折）；`REQUIRED_CONDITIONS` 22 → 24。
- 判定：對象單位與施放者的距離（`footprint.unit_dist`，曼哈頓、巨型單位照佔地，同 6.18 G 的「依距離」）＝1／≥ `rules/core.yaml` 的新欄位 **`far_distance: 5`**（`CoreRules.far_distance`，2～20）。沒有單位的格子不成立。
- **條件判定檔（`src/trpg/engine/skills/conditions.py`）改的行**：import `unit_dist`（第 38 行）；`_unit_condition_met` 把 `target_collided` 那個 `if` 改成小字典（`target_collided`／`point_blank`／`long_range` 三支，約第 176～184 行，為了不超過 PLR0911 的 return 數；`target_collided` 的判定不變）；`_UNIT_CONDITIONS` 加兩個 ID。
- 工坊：「核心戰鬥規則」多 `far_distance`（遠距條件的距離）。條件選單、LLM schema 自動從條件表列出（`skill-proposal/18`）。
- 組合器：`skill_composer.yaml` 的 `condition.distance_conditions`／`distance_permille: 60`，抽到目標型條件（且沒換成額外條件）時用獨立串流 `composer.distance_condition` 換成距離條件——**沒抽到的種子結果逐字不變**；貼身只給固定射程 ≥ 2、遠距只給固定射程 ≥ `far_distance` 的招（射程 1 的招一定貼身＝白拿折扣，見待決 1）。
- 卡片字：「貼身（和目標相鄰）」「遠距（和目標隔得夠遠）」。

### 2.「本回合移動過」寬鬆一級

- `harshness` 多一級 **`mild`**（`ConditionDef.harshness`、`BudgetRules.condition_permille`），`moved_this_turn` 改成 `mild`；`skill_budget.yaml` `condition_permille: {none: 1000, mild: 925, common: 850, harsh: 600}`（925 是 common 與 none 的中間，初值）。
- 工坊「技能預算表」多 `condition_permille.mild`；工坊白名單的路徑解析順手支援 `Literal` 鍵的 dict（`content/tuning_fields.py::_key_ok`）。
- 武器親和（`affinity._bonus_indexes`）照舊只換 `common` 條件（換了預算會變），所以「移動過」不再被換成「手持武器」。
- 手寫技能只有衝勢劈砍用到：預算比例 74.7% → 77.3%（窗 70～100%，`trpg content check` 通過）。

### 5. 變奏條件 `caster_cast_tag`

- `VariantWhen.caster_cast_tag`（標籤 ID；沒填不輸出）；引擎 `variant_holds`：施放者本回合施放過帶這個標籤的技能（同條件 `cast_tag_this_turn`）。不看位置與目標點，AI 走位估值不加分。
- 卡片字「本回合已施放過帶「火焰」標籤的技能」；LLM schema 的 `when` 多一支（`skill-proposal/19`）；工坊變奏的條件多「本回合施放過帶這個標籤的技能」（選 `skill_tags.yaml` 的標籤）；玩家文字 `player_text`。
- **隨機組合器的變奏表（`skill_composer.yaml` 的 `variant.conditions`）沒加**：加了會改掉所有抽變奏的種子（見待決 4）。

### 4. 三選一「新方向」優先製造卡

- `pick_offer._rank`：「新方向」格（`Candidate.kind == "new"`）在同一段（符合路線／偏離）裡，會製造該格關鍵字（`derive_keywords(...).makes`，含又造又用）的排前面、純利用的排後面；加深、橋接格排序逐字不變。只改排序，出題規則（格子、關鍵字、種類、偏離上限）不變。
- 量（12 build × 種子 0、1，升級白板，不呼叫 LLM）：新方向 24 格，排序有變的 2 格（召喚師、術士各 1，都是第 2、3 名對調），第一名都沒變；22 格第一名本來就是製造卡。剩下 2 格（build_fire 種子 0、1）第一名是純利用：同段只有它、製造卡都在偏離段（路線先於製造，見待決 3）。

### 3. 閃現側變與補模板（`content/flash_templates.yaml`、`skillgen/flash_ops.py`、`flash_trade.py`、`flash_offer.py`）

| 模板 | 類別 | 側變 | 改法 |
|---|---|---|---|
| `reshape_skeleton` 換形狀並換骨架 | 範圍 | ✔ | 單體打擊 → 直線 3／錐形 2／十字，骨架改試範圍、連擊（原骨架允許的形狀交給原本的「換形狀」，不重複出） |
| `push_pull_swap` 推 ↔ 拉 | 範圍 | ✔ | 推擊 ↔ 拉扯，距離照舊；只給帶傷害的招 |
| `range_reclaim` 收回射程 | 範圍 | | 收回家族（`TRADES`）：固定射程 −2，省下的預算換威力 |
| `momentum_buff` 蓄勢 | 連段 | | 命中後自己激昂 1 回合（`active_rider`） |
| `element_swap` 換元素 | 元素與關鍵字 | ✔ | 傷害只有一種非物理元素、其他效果不帶元素的招：全部換成指定元素（關鍵字由元素推導跟著換） |
| `surface_exploit` 利用地面 | 元素與關鍵字 | | 目標站在水／油／冰／火／毒上時多一段傷害（`target_on_surface`） |
| `distance_bonus` 距離加碼 | 元素與關鍵字 | | 貼身或遠距時多一段傷害（射程條件同組合器） |
| `trigger_swap` 換觸發時機 | 觸發 | ✔ | 被動：命中時 ↔ 暴擊時／受傷時、擊殺時 → 命中時；反應：被近戰擊中 ↔ 被攻擊擊中 |
| `kill_reset` 擊殺重置 | 延長與收割 | | 第一個傷害效果加 `on_kill: refund_cooldown`（要有冷卻） |
| `cost_blood` 以血支付 | 費用 | ✔ | 法力／耐力只留 1 點，其餘改付 `hp_percent`（折抵＝省下的＋50‰，不超過 `hp_cap`） |
| `cost_once` 每場一次 | 費用 | | `uses_per_battle: 1`、拿掉冷卻 |
| `support_cleanse`／`support_haste` 附淨化／附加速 | 輔助 | | 只有治療、沒有傷害的招：加淨化／加速 1 回合，對象照治療 |

- **每次閃現最多 1 張側變**：`flash.rules.max_side_per_offer: 1`（新欄位）；出題的選項產生器（`_Builder`）記數，第 2 張側變不出。挑選模式的每格候選也走同一個產生器，所以整份候選最多 1 張側變、LLM 怎麼挑都不會超過；指定類別的「每類可選幾個」每類各算。混合至少 2 類照舊。
- 參數放 `Variation.keyword`（表面 ID、條件 ID、新的觸發時機；同「雙屬性縮放」把屬性放在 `keyword`），`Variation.key()` 不變，舊存檔、舊紀錄逐字不變。
- 收回模板照 BAL-10e 排在各類別最後（`range_reclaim` 插在收束前；其他新模板插在各類別收回模板之前）。
- 大標：13 個都有 `headline_zh`；利用地面、距離加碼、換觸發另在 `headlines` 表依參數寫（暫定字）。
- **不做**：打帶跑、濺射、拋射、分打（沒有這些模板，測試鎖住）。
- **1 階單體白板每類候選數（紙面，不呼叫 LLM）**：

  1) `scripts/wish_compare.py flash`（PK-3 的 10 個閃現情境，每格「同類＋借來的」候選；輸出改寫到暫存區，沒動 `PK-4資料/`）：

  | 情境 | 技能 | 已閃 | 指定類別 | 改前 | 改後 |
  |---|---|---|---|---|---|
  | F1 | 火焰箭 | 0 | — | combo 1+2、cost 2+1、element 4+0、area 1+1 | combo 1+3、cost 4+0、element 4+0、area 2+2 |
  | F2 | 橫掃劈砍 | 1 | — | cost 2+2、combo 1+3、area 4+0、element 4+0 | cost 4+0、combo 2+2、area 4+0、element 4+0 |
  | F3 | 火焰箭 | 2 | — | 大變化 3、4、3 | 不變 |
  | F4 | 橫掃劈砍 | 0 | area | 2、1、1 | 不變 |
  | F5 | 聖光撫慰 | 0 | — | area 1、cost 1、support 1、cost 1 | area 1、cost 4、support 2、area 1 |
  | F6 | 餘燼烙印（被動） | 0 | — | 2 格：trigger 1、element 1 | 3 格：trigger 1、element 1、trigger 1 |
  | F7 | 橫掃劈砍 | 2 | — | 大變化 3、2、3 | 不變 |
  | F8 | 火焰箭 | 1 | element | 1 格 | 2 格 |
  | F9 | 火焰箭 | 3 | — | combo 1、cost 1、element 4、element 4 | combo 1+3、cost 1+3、element 4、cost 1+3 |
  | F10 | 橫掃劈砍 | 3 | — | 大變化 1+1、4、1+1 | 不變 |

  可挑的格子候選總數 **75 → 91**；只有 1 個候選的格子 **11 → 9**。

  2) 同一招第 1 次閃現、每類合格的變化有幾個（`UsageSource` 依用法統計、指定類別各自出題，側變照上限每類最多 1 張；PK-3 的 `_SINGLE` 用法）：

  | 技能（1 階單體白板） | 範圍 | 連段 | 元素與關鍵字 | 費用 | 延長與收割 |
  |---|---|---|---|---|---|
  | 火焰箭（法術） | 1 → 3 | 1 → 1 | 8 → 16 | 2 → 4 | 0 → 0 |
  | 火焰箭矢（武器射程） | 0 → 1 | 1 → 2 | 8 → 14 | 1 → 3 | 1 → 1 |
  | 咒印飛彈 | 1 → 3 | 1 → 1 | 8 → 15 | 1 → 3 | 0 → 0 |

  連段仍常只有 1：火焰箭這類「傷害＋附帶狀態」的打擊骨架附帶效果已滿 1 個，蓄勢放不進去（待決 6）；延長的擊殺重置要有冷卻。
- 全部玩家技能 1、2 階各套一次（`apply_variation`，+40‰）的成功數：換骨架 339、換元素 228、推拉 32、換觸發 22/28、以血支付 562、收回射程 127、蓄勢 254、利用地面 642、距離加碼 148、擊殺重置 298、每場一次 426、附淨化 10、附加速 7（後兩個只給沒有傷害的治療招）。

## 驗收條件

| 條件 | 結果 | 證據 |
|---|---|---|
| 相關目錄測試 0 | 通過 | 下節「檢查指令結果」 |
| ruff、format、mypy、lint-imports 0 | 通過 | 同上 |
| 前端 tsc／vitest（有改前端時） | 前端程式沒改；只重產了 `client/src/battle/fixtures/glossary.json`（多兩個條件）。worktree 沒有 `client/node_modules`，沒跑 vitest | 待決 8 |
| 戰鬥不變比對 different=0 | **`battles=46 events=19392 different=0`** | 改前：`git archive be42035a5 src content` 副本＋`PYTHONPATH`；8 張地圖 × 種子 1、2 ＋ 盜賊巢穴、雲頂、熔心坑 × 種子 3～12；地圖預設陣容、效用 AI、`max_rounds=30`；去掉 `format`、`ruleset_hash`、`setup.ruleset`、`final_state.ruleset` 後整份比 SHA-256 |
| 快照與夾具先預測再逐鍵核對 | 見下表 | |
| 版號列出 | 見下表 | |

**快照與夾具（逐鍵）**

| 鍵 | 預測 | 結果 |
|---|---|---|
| parity `complete`／`retier`（401 招） | 只有用到「移動過」的衝勢劈砍會變 | 第一次比對多了 4 招戰場變奏技（`VariantWhen` 的新欄位輸出 `null` 改了 JSON）→ 改成空值不輸出後**只剩衝勢劈砍**，只改這 2 個值 |
| parity `flash`（126 鍵） | 有新模板套得上的招會變 | 71 鍵變（都是主動、被動、反應裡套得上新模板或受側變上限影響的）；逐鍵只改這 71 個值，其餘不動；`-m slow` 928 passed |
| CLI 輸出雜湊（戰鬥、技能列表與 show）、`llm_propose_mock.txt` | 不變（手寫技能數值沒變、組合器沒抽到的種子不變） | `tests/cli -m slow` 44 passed，沒重產 |
| 技能圖示夾具（`tests/narrative`） | 不變（固定種子沒抽到距離條件） | 通過，沒重產 |
| 前端夾具 | `glossary.json` 多兩個條件；其他不變 | `scripts/export_client_fixtures.py` 重產，只有 `glossary.json` 有差，內容就是貼身、遠距兩筆 |
| `client/openapi.json`、`schema.d.ts` | 不變（API 模型沒改） | 沒重產 |
| `VICTORY`、三選一、run auto | 可能變（組合器、新方向排序） | `tests/roguelite` 通過，不用改 |

**版號**

| 版號 | 變動 |
|---|---|
| `PROMPT_VERSION`（技能提議） | `skill-proposal/17` → **`/19`**（/18：條件多貼身、遠距；/19：變奏 `when` 多一支）；快照雜湊同 /17（只看系統指令與區塊格式） |
| `WORLD_RULES_VERSION` | 36 → **37**（閃現出題加側變上限、三選一新方向排序；比照 PK-3／PK-4）。SK-2 在 main 沒升這個版號；合併時若有人也升了，要再加一 |
| `LOG_FORMAT`、`WLOG_FORMAT`、`CHAR_FORMAT`、`SAVE_FORMAT` | **不升**（沒有新的紀錄欄位；`Variation` 的參數沿用 `keyword`） |
| `flash-pick/2`、`flash-variation/6` | 不升（prompt 文字沒改，只有目錄內容多了模板） |
| `ruleset_hash`、`content_digest` | 變（條件表、核心規則、預算表、閃現模板） |

**改到的既有測試**（斷言沒有放寬；都是登錄處、寫死的數字或依模板集合的重現案例）：`test_coverage`（距離條件進允許清單：沒有手寫示範技能）、`test_prompts`（版號 2 筆）、`test_skill_rules_content`／`test_skills_content`（`mild`）、`test_rules_budget_bs1`（工坊欄位清單多 `far_distance`、`condition_permille.mild`）、`test_flash_cost_fl1c`（「沒有任何選項」的 7 招剩 2 招：其餘 5 招現在有每場一次／以血支付可閃；快取測試換成仍沒選項的血痕疾行）、`test_flash_available_fl1c`（同上換招）、`test_flash_text_fl1f`（模板 90 → 103 個）、`test_flash_lf2`（火焰箭費用類 2 → 4 個）、`test_flash_propose`（schema 分支快照多 7 個模板）、`test_reflash_weaker_rr2`（重現案例在新模板下不再卡住：模組改用 `tests.engine.helpers.without_sk1_flash()` 拿掉 SK-1 模板的內容庫，RR-2 規則本身照舊鎖住）、版號 2 處。

## 檢查指令結果

| 指令 | 結束碼 |
|---|---|
| `uv run ruff check src tests` | 0 |
| `uv run ruff format --check src tests` | 0 |
| `uv run mypy`（1674 檔，含 tests） | 0 |
| `uv run lint-imports`（14 kept） | 0 |
| `uv run trpg content check` | 0 |
| `pytest -n 8 tests/skillgen tests/narrative tests/content tests/test_architecture.py`＋兩個新 engine 測試（最後一輪 8096 passed、14 skipped；`test_upgrade_topup.py::…[summon]` 單獨跑） | 0 |
| `pytest tests/skillgen/test_upgrade_topup.py::test_reaction_keywords_the_composer_cannot_carry`（改前副本 3 passed、276 秒；本分支同一份全目錄跑過 4430 passed） | 0 |
| `pytest -n 8 tests/llm`（495 passed） | 0 |
| `pytest -n 8 tests/roguelite`（281 passed；失敗的 1 檔改後重跑 6 passed） | 0 |
| `pytest -n 8 tests/world`（1328 passed） | 0 |
| `pytest -n 8 tests/api`（1320；失敗的 3 檔與版號檔改後重跑 117 passed） | 0 |
| `pytest -m slow tests/skillgen/test_refactor_parity.py`（928） | 0 |
| `pytest -m slow tests/cli`（44） | 0 |
| `pytest -m slow tests/sim`（19） | 0 |
| 戰鬥不變比對（46 場） | 0（different=0） |

沒跑：全量 `scripts/check.py`、平衡量測、戰鬥模擬（不變比對以外）、前端 tsc／vitest／build。

## 待 PM 決定（規格沒寫到、我先採保守做法的地方）

| 事項 | 我的做法 | 其他選項 |
|---|---|---|
| 1. 貼身／遠距對「一定成立」的招等於白拿折扣（射程 1 的近戰技帶貼身、遠程技在 5 格外用遠距） | 只在**組合器**和閃現「距離加碼」擋（貼身要射程 ≥ 2、遠距要射程 ≥ 門檻）；驗證器不擋，LLM 提議與工坊仍可以做出「射程 1＋貼身」 | 驗證器也擋（規則類，要玩法 PM 定） |
| 2. 遠距門檻 5、寬鬆倍率 925、組合器距離條件機率 60‰、以血支付「多 50‰」 | 都是初值；前兩個接工坊 | 由使用者在工坊調 |
| 3. 新方向「製造優先」和「符合路線優先」誰先 | 路線先（#110 的硬規則照舊），同一段裡製造卡在前；所以整段都是純利用時，偏離段的製造卡仍排在後面（build_fire 兩格） | 製造優先於路線 |
| 4. 變奏條件「本回合施放過某標籤」沒進隨機組合器的變奏表 | 只開給手寫、LLM、工坊；組合器的 `variant.conditions` 沒加（加了所有抽變奏的種子都會變） | 用獨立串流加進組合器 |
| 5. 以血支付保留 1 點法力／耐力 | 驗證器規定主動技至少花 1 點資源（`cap.min_cost`），所以「不花法力」做不到，改成「只留 1 點，其餘換成扣血」 | 放寬驗證器對 `hp_percent` 招的最低資源（規則類） |
| 6. 蓄勢套不上「傷害＋附帶狀態」的打擊招（火焰箭） | 骨架附帶效果上限 1 個照舊，所以那類招連段仍只有 1 個候選 | 蓄勢改成取代附帶效果、或放寬上限 |
| 7. 附淨化用現有原語 `cleanse`（移除**全部**減益，不是 1 個）；附淨化／附加速只給「有治療、沒有傷害」的招 | 照現有原語 | 新增「移除 1 個減益」參數 |
| 8. 前端沒驗 | worktree 沒有 `client/node_modules`；前端程式沒改，只有 `glossary.json` 夾具多兩筆 | 開發 PM 的全量檢查跑 vitest |
| 9. 卡片字「遠距（和目標隔得夠遠）」沒寫格數 | `condition_text` 拿不到規則數值，寫死 5 會在工坊改門檻後變錯 | 把門檻傳進條件句（要改所有呼叫處） |
| 10. 推 ↔ 拉、換觸發的歸類與配對、側變的類別 | 推拉放「範圍」、換觸發放「觸發」、換骨架放「範圍」、換元素放「元素與關鍵字」、以血支付放「費用」；換觸發配對見上表 | 玩法 PM 定類別與配對 |
| 11. 新模板的大標、說明、前綴（擴散、反勢、抵近、蓄勢、轉元、借地、量距、易時、連斬、血契、絕招、滌清、疾癒）都是暫定字 | 照現有寫法 | 玩法 PM 定字 |

其他：
- 沒有改 `_STACK_SKELETON`、`_HAND_WRITTEN_PRIMITIVES`（WC-1 腳本 import 的兩個名稱）。
- 和 SK-2 可能重疊的檔：`content/rules/core.yaml`／`src/trpg/content/rules.py`（加在 `ambush_hit_bonus` 後面一行）、`src/trpg/engine/skills/conditions.py`（上面列的幾行）、`content/tuning_fields.yaml`（rules、budget 兩段各一行）、`tests/engine/helpers.py`（新增 `without_sk1_flash`）。
- 第一次跑 `tests/skillgen` 時一個 xdist 工作行程異常結束（「node down」），整批卡住，我停掉了重跑；第二次起都正常。那時留下的閒置工作行程我沒權限強制結束，後來查已經不在了。

## PM 裁定
（由開發 PM 填）

## 開發 PM 裁定（2026-11-19）

- **驗收通過，合併**，和 SK-2 沒有文字衝突。五項都有測試鎖住，戰鬥不變比對 46 場 different=0。parity 的 flash 夾具變了 71 鍵，都是新模板和側變上限造成的，有逐鍵核對，接受。`skill-proposal/19`、WORLD_RULES_VERSION 37，接受（SK-2 沒升這個版號，沒有撞號）。
- 待決 1（貼身、遠距碰上一定成立的招，白拿折扣）、5（以血支付做不到「完全不花」）、7（附淨化用現有原語會移除全部減益，6.38-3 寫的是 1 個）、10（側變的歸類和換觸發的配對）、11（13 個新模板的暫定字）：轉玩法 PM。
- 待決 2（初值）、3（「符合路線」仍排在「會製造」之前）、4（隨機組合器不加出招順序條件）、6（蓄勢套不上帶附帶狀態的打擊招）、9（遠距的卡片字不寫格數）：照保守做法接受，數值由使用者在工坊調。
- 待決 8（前端 vitest 沒跑）：由開發 PM 的全量檢查補上。
