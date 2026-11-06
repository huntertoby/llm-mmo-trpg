# Phase 3W-3 報告｜大變化與轉型

> 依 `docs/phases/Phase3W計畫.md` 第 1 節 3W-3 列、第 3 節（#70 轉型保底）、第 5 節（#72、#73 轉型依角色階級）；設計 `docs/design/06-技能.md` 6.34.3、6.34.5、6.34.9、6.28。實作者：implementer agent（sonnet）。已 fast-forward 到 main `fb6a6d04`（3W-1、3W-4 已合併）。未 push。
> 範圍：只做規則核心（純函式＋資料＋測試）；不接一輪流程（3W-5）、不改前端、不做 LLM。與 3W-2 同時進行，程式盡量放獨立模組。

## 1. Commit

| commit | 內容 |
|---|---|
| `aa08eba8` | `skillgen/flash_major.py`（轉型、補充大變化、欄位判定）、`flash_templates.yaml` 新區段、schema 擴充、`flash.py` 接點 |
| `7a220718` | `tests/skillgen/test_flash_major.py`（30 項）、`test_flash.py` 配合真轉型調整 |
| （本報告） | `docs/phases/Phase3W-3報告.md` |

## 2. 做了什麼

### 2.1 轉型（依角色階級，#73）
- 6 個轉型模板（`content/flash_templates.yaml` 的 `transforms`，每個有 `min_tier`）：

| 模板 | 新種類 | 最低角色階級 | 欄位 |
|---|---|---|---|
| `to_passive_on_hit` | 被動（命中時） | 1 | 被動欄 |
| `to_reaction_melee` | 反應（被近戰攻擊時） | 1 | 反應欄 |
| `to_summon` | 召喚（依這招元素挑召喚物，`units` 表） | 2 | 主動欄 |
| `to_trap` | 陷阱（踩上去觸發） | 2 | 主動欄 |
| `to_stance` | 姿態（原招有傷害 → 狂怒姿態，沒有 → 堅壁姿態） | 2 | 姿態欄（見待決 #2） |
| `to_modifier` | 修正型被動（同元素技能：帶上原招的狀態，或傷害 +n‰） | 3 | 被動欄 |

- 新種類的結構由 `flash_major.transform_drafts` 產生草稿（法術類、自動命中、效果取原招的敵對傷害／狀態，最多 2 個；沒有可帶走的效果就不合法）；**強度由預算器依新種類重算**：有骰子旋鈕的交給調整器（`evolution.retune`），固定強度的種類（召喚、姿態、修正型被動）改以驗證器直接檢查 70～100% 預算窗（`finish_transform`）。第 3 次的 +120‰ 上限加成照常套用。
- **保底（#70）**：`DataOrderSource.transforms` 依 `tier` 開放模板，種類由種子洗牌後輪流排列（`transform_variations`），出題取第一個真的做得出來的 → 有合法轉型一定在選項內（不指定佔 4 個之一；指定加深／橋接時另列第 4 個；重閃第 3 次也有）；可轉的種類多時由種子隨機挑一種（測試：30 個種子挑到 ≥ 3 種）。
- **轉型後的小變化**（`flash._apply_transform`）：從原本的技能轉型，再把轉型之前的小變化逐筆套到新技能上——合法的保留、不合法的換成**同類別**資料順序第一個合法的小變化、都不合法就省略；重套都用轉型這一次的預算加成，所以最後加成與轉型同次。轉型之後（第 4、5 次）的小變化直接套在新種類上，套不上的變化出題時不會出現。
- **欄位卸下判定**（`flash_major.transform_slot_plan`）：回傳 `SlotPlan`（原欄、新欄、上限、已佔用、`must_unequip`、`candidates`）。同欄原地換不用卸；不同欄且目標欄已滿時回傳需要卸下幾個與可卸的技能 ID。**只回傳判定**，卸下到技能庫的流程在 3W-5。
- 名稱「{前綴}・{原名}」沿用 `flashed_identity`；轉型不受階級限制的只有「大變化本身」（加深、橋接任何階級都有）。

### 2.2 第 3 次的加深、橋接保證
- 不指定時 `make_offer` 的混合規則本來就輪流取類別 → 加深、橋接各至少 1（有合格變化時）；新增測試鎖住：4 個選項＝加深 ≥ 1、橋接 ≥ 1、轉型 1（`test_open_major_offer_has_at_least_one_deepen_and_one_bridge`）。

### 2.3 輔助類模板（原 3-26b 待辦）與召喚技能
- 新資料區段 `extra_major`（`ExtraMajorTemplate`，`only: support | summon`）：
  - 輔助技（治療、護盾、增益）：`support_wide`（加深：範圍 +1，單體改十字）、`support_ease`（加深：冷卻 −1）、`support_imbue`（橋接：在目標腳下留下水、冰、煙的場地，嫁接表中製造場地的關鍵字）。
  - 召喚技能：沿用 3-33f2 的 `summon_deepen`、`summon_count`（加深）、`summon_bridge`（橋接，灌注關鍵字）——3W-1 的大變化只接了一般進化模板，召喚技能原本拿不到任何大變化。
- 覆蓋（`tests/skillgen/test_flash_major.py`，16 個內容裡的輔助技）：加深 13/16、橋接 13/16、兩邊都有 10/16（加入前：加深 9、橋接 12）。

### 2.4 強度下限（06 6.34.3）
- `meets_floor(old, new)`：新技能的預算分數（`skill_budget(...).total`）不低於閃現前。套用在所有大變化的結果（進化模板、輔助類、召喚類）；轉型換了預算類別、分數不可比，不套用，只要預算窗與驗證器全過。量測：白板 60 張的大變化結果 176 個中本來就有 173 個符合（3 個被濾掉）。

### 2.5 其他變動（介面接點）
- `flash.py`：`apply_variation` 的小變化與轉型都改走 `finish_transform`（調整器做不出來的固定強度種類改檢查預算窗；有旋鈕的行為與原本相同）；`derive_skill` 遇到轉型改走 `_apply_transform`；`DataOrderSource(tier=1)` 多一個建構參數（角色階級）並把補充大變化排在進化模板之後；`TRANSFORM_OPS` 仍保留當覆寫點（登錄了就優先用）。
- `flash_templates.py`：`TransformTemplate` 擴充（`to` 六種、`min_tier`、`units`、`summon_duration`、`trap`、`stances`、`damage_permille_steps`）、新增 `ExtraMajorTemplate`、`FlashTable.extra_major`／`transform_template()`／`extra_template()`。
- `evolution.py`：新增公開的 `rarity_of`（給 `flash_major` 用）。
- 3W-1 的被動轉型文字寫「對旁邊一名敵人濺出」，但資料是 `trigger.target: other`（對被打中的那位），已把說明文字改成與行為一致：「你的攻擊命中時，自動對被打中的敵人補上縮小版的這招」。

## 3. 行為一致測試（`tests/skillgen/test_flash_major.py`）

| 項目 | 測試 |
|---|---|
| 資料符合 #73（階級、召喚物與姿態存在） | `test_transform_data_matches_decision_73` |
| 階級開放（1 階被動／反應；2 階起 ＋召喚／陷阱／姿態；3 階起 ＋修正型被動；只有主動技轉型） | `test_transform_kinds_open_by_hero_tier`（3 階級） |
| 種子挑種類、可重播、各種類都會被挑到 | `test_kind_order_is_seeded_and_covers_every_kind`、`test_transform_choice_is_deterministic_and_round_trips` |
| 每種轉型：通過驗證器、預算比例在窗內、+120‰、名稱「{前綴}・火焰箭」、技能卡可建、骰子＝卡片 | `test_every_transform_is_valid_and_within_the_budget_window`（6 種） |
| 被動：實戰命中時觸發，骰數＝卡片 | `test_passive_transform_triggers_on_a_hit_with_the_card_dice` |
| 反應：被近戰打中時反擊，骰數＝卡片 | `test_reaction_transform_answers_a_melee_hit` |
| 召喚：召喚出火元素對應的召喚物 | `test_summon_transform_summons_the_unit_of_its_element` |
| 陷阱：放置後敵人踩上去觸發，骰數＝卡片 | `test_trap_transform_places_a_trap_that_hits_with_the_card_dice` |
| 姿態：進入 `stance_fury` | `test_stance_transform_enters_its_stance` |
| 修正型被動：施放者的火焰箭結果改變 | `test_modifier_transform_changes_the_casters_fire_skill` |
| 保底（不指定、指定加深／橋接、重閃第 3 次；各階級） | `test_major_offer_always_has_a_legal_transform_and_respects_tier` |
| 小變化保留／換同類別／省略；預算加成同次 | `test_legal_minors_are_kept_and_illegal_ones_swap_to_the_same_category`、`test_later_minors_apply_on_the_new_kind`、`test_reflashing_a_minor_slot_keeps_the_transform` |
| 欄位卸下判定（同欄原地、被動欄、修正型、姿態欄、反應欄） | `test_slot_plan_reports_which_skills_must_be_unequipped` |
| 輔助類、召喚類大變化；強度下限 | `test_support_skills_get_deepen_and_bridge_templates`、`test_summon_skills_use_the_summon_evolutions`、`test_major_results_never_fall_below_the_budget_score_before` |
| 白板（1 階）可轉成各種類（≥ 70%） | `test_whiteboards_can_transform_into_every_kind` |
| 輔助技只能轉防守姿態 | `test_support_skill_transforms_to_a_defensive_stance_only` |

跑過：`ruff check .`、`ruff format --check .`、`mypy`（808 檔）、`lint-imports`（7 kept）；pytest（`-m "(slow or not slow) and not llm" -n 8`）：`tests/skillgen` 全部＋`tests/roguelite/test_evolution.py`（2284 通過、1 skip）、`tests/content`、`tests/test_architecture.py`。`tests/cli` 快照（`test_output_snapshots.py`、`test_budget_cli.py`）與 `tests/engine/test_skill_determinism.py` 本段另外啟動執行，但寫報告時尚未跑完（本段沒有改規則包、技能內容與 CLI 輸出，`flash_templates.yaml` 不嵌入規則包，預期不受影響）；請 PM 合併時一併確認。依指示沒有跑完整 `scripts/check.py`。

### 量測（只量不調）
- 白板（1 階，40 張主動）轉型成功率：召喚 40、姿態 40、修正型被動 40、陷阱 33、被動 30、反應 29（單一效果的白板，被動／反應偶爾湊不到預算窗）。
- 手寫技能（247 招主動，多為 2～3 階）：修正型被動 214、姿態 208、召喚 195、被動 55、反應 54、陷阱 52。高階手寫技能的預算大，轉被動／反應／陷阱容易超出；3W-9 把階級改成角色階級後會變。

## 4. 新增的複雜度 noqa
無。

## 5. 待 PM 決定

1. **`FlashRequest` 沒有角色階級**：我把階級放在 `DataOrderSource(tier=…)`，避免和 3W-2 的 `FlashRequest` 修改衝突。合併時請讓出題入口把 `request.tier`（3W-2 加的）傳給來源（例如 `DataOrderSource(tier=request.tier)`），或在 3W-5 組來源時傳入。預設 1 階（最保守）。
2. **姿態欄 vs 主動欄**：#73 寫「姿態佔主動欄」，但引擎 `core.yaml` 的欄位是主動 6、被動 3、反應 1、**姿態 1**（`SkillDef.slot_kind`：只有「形態」技能佔主動欄）。我照引擎真相（轉型成一般姿態 → 姿態欄，只有 1 格）回傳卸下判定，免得違反 `skill_slot_problems`。若玩法 PM 的原意是姿態轉型要放主動欄，需要把轉型姿態改成形態，或調整欄位規則。
3. **姿態轉型很「脫離主題」**：目前只有兩個一般姿態（狂怒、堅壁），所以所有有傷害的技能轉姿態都是狂怒、輔助技都是堅壁，與原招元素無關。要更有主題需要玩法 PM 補姿態內容。
4. **強度下限不套用在轉型**：新種類換了預算類別（例如被動預算只有主動的一部分），分數不可比；轉型只要求預算窗 70～100% 與驗證器全過。若要求「轉型後威力仍不低於」需要玩法 PM 另定比較方式。
5. **小變化被省略**：轉型前的小變化若對新種類與同類別替代都不合法，會被省略（仍算一次閃現）。目前 3W-1 的小變化只有範圍與距離，轉成被動／反應後都會被省略、召喚與陷阱的地面格最大射程 6 也容易到頂；3W-2 補上更多類別（尤其觸發類）後這個損失才會變小。
6. **輔助技不能轉被動／反應／陷阱／修正型被動**：它們沒有敵對的傷害或狀態可以縮小帶走，只能轉姿態（防守向）與召喚。要不要補「受傷時治療自己」之類的輔助向轉型，請玩法 PM 決定。
7. **輔助類加深／橋接仍有缺口**：16 招輔助技中加深 13、橋接 13、兩邊都有 10（缺口例：淨化、守護符陣、冰甲封印沒有加深；氣息調和、聖光撫慰、聖化結界沒有橋接）。此時第 3 次會少一類，其餘由另一類與轉型補滿；要百分之百需要更多輔助類模板（例如「治療額外給護盾」）。
8. **召喚物候選表**（`to_summon.units`）是我依元素挑的初值（火→火靈、冰→冰靈、雷→雷靈、風→鷹、毒→藤蔓、地→石像鬼／土牆、聖→守護靈、暗→暗影、其餘→戰狼等），未經平衡；高階手寫技能轉召喚後預算窗內的比例也未調。
9. **「1/3 機率」初值已不用**：計畫表舊文字的機率被 #70 保底取代（有合法轉型一定出現，玩家不選才是「偶爾」），沒有實作機率。
10. **規則包雜湊／存檔**：沒有新增 `SkillDef` 欄位，規則包雜湊與 `LOG_FORMAT`、存檔版本都沒動；`FlashTable` 新欄位在 `flash_templates.yaml`（不嵌入規則包）。轉型產生的技能的 `provenance.origin` 是 `level_up`（為了讓縮放屬性可以收進允許範圍）。

## 6. 合併 3W-2（main `fcfeec26`）

- `git merge main`，衝突在 `flash.py`（5 處）與 `evolution.py`（`__all__`）。解法：保留 3W-2 的 `derive_chain`／`derive_skill(..., tier)`、`power_floor`、`apply_variation(replaced=)`、`tuning_extras`、`FlashRequest.tier`、小變化 `FLASH_OPS`（`flash_ops.py`）；再接上本段的轉型（`transform_drafts`）、補充大變化（`apply_extra`）與轉型後的小變化重套（`_apply_transform`，在 `derive_chain` 遇到轉型時呼叫，從 `at_tier(base, tier)` 重新轉型）。
- **待決 1 已處理**：`DataOrderSource` 不再有 `tier` 參數，轉型階級改用 3W-2 的 `request.role_tier`；測試改在 `FlashRequest(..., tier=…)` 帶階級。
- `apply_variation`：3W-2 的調整器（含強度下限）先試；失敗後對固定強度的結構（召喚、姿態、修正型被動）改用 `fixed_strength`（預算窗＋同一個 `floor`），轉型本身走 `finish_transform`（不設下限，與 3W-2 `power_floor` 對轉型回傳 `None` 一致）。
- **合併後發現的問題**：3W-2 的 `at_tier` 讓技能依角色階級重算預算，固定強度的種類不隨階級變大，導致 2、3 階時召喚（8/30、0/30 張白板可轉）與姿態（0/30）落到預算窗下限以下。處理：召喚加 `summon_boosts`（持續輪數、最大 HP 依序加試）→ 2、3 階都 30/30；**姿態無解**（驗證器規定姿態只能有一個狀態效果，狀態點數固定），2 階以上轉不出姿態。陷阱（23/30）、被動（26～27/30）、反應（23/30）、修正型被動（30/30）不受影響。→ 待玩法 PM：高階姿態需要隨階級變強的姿態狀態，或 2 階以上改開別的轉型。
- 驗證：`ruff check`、`ruff format --check`、`mypy`（810 檔）、`lint-imports`（7 kept）全過；pytest：`test_flash_major.py`（30）、`test_flash.py`＋`test_flash_templates.py`＋`test_flash_state.py`（141）、`tests/content`＋`tests/test_architecture.py`＋`tests/roguelite/test_evolution.py`（1540）全通過。
- **未完成的驗證（請 PM 在合併時確認）**：整個 `tests/skillgen`、`tests/cli`、`tests/engine/test_skill_determinism.py` 在本機跑不完——合併前同一組 `tests/skillgen` 約 150 秒，合併後多次跑了 30～60 分鐘仍停在 30～60%，而且出現過 xdist 的 `node down: Not properly terminated`；同時間機器上有一個 4 GB 的 python 行程（不是我啟動的、我沒有動它），疑似記憶體壓力。單獨跑 flash 相關檔案與 `test_candidates.py` 速度正常，所以無法判斷是環境還是合併後某個測試變慢。我已停掉自己啟動的長跑。
