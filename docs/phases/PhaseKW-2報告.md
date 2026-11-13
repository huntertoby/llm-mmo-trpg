# Phase KW-2 完成報告｜層數關鍵字的池子、白板、嫁接與解除隱藏（#161）

> 規格：`docs/phases/PhaseKW計畫.md` KW-2 段。依據 06 6.27.1、6.27.2、6.32.1；玩法 PM 回覆 `docs/玩法PM交接.md` 4.1.1 B（commit `70b0a4638`）。
> 基準：main `254bab16d`；中途合併 main `3a155ddbd`（RG-2，`LOG_FORMAT` /121、`WORLD_RULES_VERSION` 31、`CHAR_FORMAT` /15），沒有衝突。
> 「範圍技連擊點」（4.1.1 A 第 5 題）照現況（每個目標各 +1），沒有動。沒有跑平衡量測；沒有動 `content/world/`、敵人內容、`docs/design/`。

## 1. 做了什麼

### 1.1 示範招（14 招，2 招合併）與補齊的利用者（4 招）

| 關鍵字 | 示範招（6.32.1） | 補齊的主動利用者 |
|---|---|---|
| 連擊 | 疾刺 `skill_swift_stab`（打中 +1，背刺再 +1）、掠影步 `skill_shadow_glide`、斷喉 `skill_throat_cut`（花光加傷；開場 5 層時流血） | 連影斬 `skill_flowing_cut`（連擊點 ≥ 3 才能放，不消耗） |
| 怒氣 | 血怒 `skill_blood_fury`、怒吼 `skill_war_cry`、狂暴劈砍＝**併進怒氣爆發**、咬牙撐住 `skill_grit_teeth`（花光怒氣，每層護盾提高） | 暴怒重擊 `skill_fury_slam`（怒氣 ≥ 3 時擊倒） |
| 專注 | 凝神 `skill_centering`、鷹眼 `skill_eagle_eye`（被動，站在高處時回合結束 +1）、貫心箭 `skill_heart_piercer`（花光加傷；開場 3 層時標記） | 心眼箭 `skill_mind_eye_shot`（專注 ≥ 2 才能放） |
| 氣 | 寸勁 `skill_inch_force`、調息→**吐納** `skill_breathing_qi`、氣功波 `skill_qigong_wave`、內觀＝**併進沉息癒傷** | 崩拳 `skill_crumbling_fist`（氣 ≥ 2 時擊倒） |

- 合併照玩法 PM「效果相同就合併」：狂暴劈砍與怒氣爆發都是「花光每層加傷」，內觀與沉息癒傷都是「花光每層治療自己」，留既有名字與 ID，檔頭加註。震擊／寸勁（寸勁多推開）、專注一擊／貫心箭（貫心箭多標記）效果不同，並存。
- 數值是佔位，照預算落在 72～98%。
- 骨架做不到的寫法（第 7 節待決 1）：
  - 沒有骨架能以 `add_stack` 當核心。所以凝神、鷹眼各借一個小護盾當核心，血怒借 1 回合增強。
  - 控場、位移、打擊骨架的附帶效果不收 `add_stack`。所以怒吼改用蓄力骨架，形狀是錐形，帶小傷害。寸勁的推開、掠影步的躍步寫成第二段（`on_hit`、`after_action`）。

### 1.2 新條件「自己站在高處」`self_on_high_ground`

- 只看施放者：所在格高度 ≥ 1。這是規格的佔位定義，飛行不算。
- `handwritten_only`。高處關鍵字的 `uses` 加這條，所以鷹眼同時「製造專注、利用高處」。
- 前端條件部件先借用「居高臨下」。

### 1.3 解除隱藏與池子

- 拿掉四個關鍵字的 `start_hidden`、`composable: false`，也拿掉 `stacks.yaml` 連擊點、專注、氣的 `composer: false`。開局、許願池（選單與 LLM 對照清單）、三選一新方向、`run auto` 抽樣、`trpg llm propose` 輪替都變成 16 個。
- `self_stack_at_least` 拿掉 `handwritten_only`（玩法 PM B3「開放」）：
  - 進 LLM schema、出題子集、工坊選項。
  - 隨機組合器的條件清單**沒有加**，既有種子不變。
- `fury.consumer.boosts` 加 `shield`（咬牙撐住用）。
- 連擊點的 `consumer.requires_any` 加 `{tag: builder_finisher}`。原因：組合器的技能沒有「終結」標籤，只有骨架 ID；不加就做不出消耗連擊點的招。

### 1.4 白板

- 新增 12 個 1 階配方，每個關鍵字 3 個：單體製造（傷害＋累積）、直線製造、條件利用（傷害＋「自身層數達 N」）。
- 條件的 N 是佔位：連擊 3，其他 2。
- 四個關鍵字加進 `whiteboard.exception_keywords`。
- 近戰、遠程、法器三種武器都組得出製造者與利用者。

### 1.5 閃現嫁接（加第二個關鍵字）

- `grafts` 加四筆：
  - 製造方：多累積 1 層。
  - 利用方：schema 只收「條件成立時加碼的傷害」，所以寫成「自身層數達 N 時多一段傷害」，不消耗（待決 3）。
- `bridge_imbue` 加 `skeletons: [builder_finisher]`，因為原骨架收不下 `add_stack`。蓄力骨架本來就要求有層數原語，所以其他關鍵字的嫁接不受影響；parity flash 126 條全部不變。
- 大標留空，走既有退路，等玩法 PM 補。

### 1.6 隨機組合器

`_compose_with_keyword` 指定層數關鍵字、又沒指定骨架時，固定用 `builder_finisher`。這四個關鍵字在 KW-2 前組合器不做，所以既有關鍵字的結果不變；組合器的隨機種子 0～49 圖示也全部不變。

### 1.7 文字與前端

- 關鍵字說明照玩法 PM 的字：
  - 怒氣：「…花掉怒氣換傷害或護盾…」。
  - 連擊：「武器技打中累積連擊點（雙匕首一次出招也只算 1 點）…」。括號照現況，A 第 5 題回覆後再改。
- 工坊字「要看哪一種層數：只能選…」，照 KW-1b 的定稿。
- 前端：
  - 重產 `glossary.json`、`skill_icons.json`。
  - `parts.ts` 的 `COND` 加一筆暫代部件。
  - 同步 `qIconSkills.test.ts` 的招數（429）與條件數（22）、`qIconQi2d.test.ts` 的 `ADDED_AFTER_BASELINE`（加 16 招）與 `ADDED_PARTS`。

### 1.8 RG-2 的狂怒劈砍

- 狂怒劈砍是 `enemy_only`，不進玩家的池子（`player_skills`），所以不影響池子門檻計數。
- 它用的 `self_stack_at_least` 在 RG-2 已從 `_UNCOVERED` 拿掉。
- 荒原狂戰士沒有召喚灌注的問題。

## 2. 恢復範圍：前後各檢查幾個關鍵字

| 測試 | KW-1 時 | KW-2 後 |
|---|---|---|
| `test_keywords.py::test_table_has_the_sixteen_keywords_in_order`（`start_ids`） | 12 | 16（`start_ids() == ids()`） |
| `test_keywords.py::test_each_pool_has_at_least_three_tier_one_starter_skills` | ≥3 只檢查 12 個（4 個只斷言 `start_hidden`） | 16 |
| `test_keywords.py::test_exclusive_only_derivation_drops_general_and_provisional_rules`（開局池 ≥3） | 12 | 16 |
| `test_keywords.py::test_composer_can_require_each_keyword`（`COMPOSABLE`） | 11 | 15（只排除形態） |
| `test_keyword_pools.py::test_every_keyword_pool_has_at_least_three_active_exploiters` | 12 | 16 |
| `test_whiteboard.py::test_every_keyword_has_a_whiteboard_from_tier_one` | 11（12 扣形態） | 15，另外斷言四個層數 1 階就有 |
| `test_keyword_start.py::test_starter_pools_use_exclusive_rules_and_have_three_each` | 12 | 16 |
| `test_evolution.py`（嫁接表） | 11（12 扣召喚物） | 15 |
| `test_summons_e1.py::test_the_infusion_table_covers_all_ten_keywords` | 12 | 16 |
| `test_form_start.py::test_the_form_start_pool_holds_only_the_tier_one_forms` | 12 | 16 |
| `test_stack_keywords_kw1.py`（隱藏、只給手寫） | 斷言隱藏 | 改成斷言打開、開放 |
| `cli/llm.py` 輪替（`start_ids`） | 12 | 16（程式沒改，`start_ids` 現在就是全部） |
| `test_appearance.py`（裝備外觀） | 12 | **仍 12**：改用 `ART_PENDING` 提醒，KW-3 補上時失敗 |
| 前端 `entryScreen.test.ts`（創角圖示） | 12 | **仍 12**：改用 `ART_PENDING` 提醒，KW-3 補上時失敗 |

- 所有 PENDING 提醒都刪了。
- 外觀與創角圖示是美術（顏色、圖樣），排在 KW-3，所以改成 ART_PENDING。測試會先斷言「缺的剛好是這四個」，KW-3 補上時就會失敗。

## 3. 灌注表

- 06 6.29.2 的灌注表只列 10 個關鍵字；6.27.1、6.32.1、4.1.1 都沒有要求層數關鍵字有召喚灌注。
- 保守照中毒處理：**沒有灌注**。測試改成「16 個關鍵字扣中毒、形態、四個層數＝灌注表的 10 個」，並斷言四個層數不在表內。列進待決。

## 4. 檢查與結束碼

| 檢查 | 結束碼 / 結果 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy` | 0（1592 個檔） |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（690 個檔、429 個技能） |
| 直接相關 pytest（非 slow，content、narrative、llm、skillgen、roguelite、world、api、engine、cli、sim，`-n 8`） | 失敗都已修，修後重跑失敗的檔全過 |
| slow：parity、proposal、`tests/cli -m slow` | 第一次 18 失敗，都在預測內（第 5 節）；重產與換種子後 42/42 過 |
| `trpg battle --map open_plain --seed 7` ＋ `replay` | 0、0（91 個動作、383 個事件） |
| 前端 `typecheck` | 0 |
| 前端 vitest（全部） | 0（345 檔、4398 項全過） |
| 不變比對（8 張地圖 × 2 種子 ＋ 3 張頭目圖 × 種子 3～12） | `battles=46 events=20499 actions=4227 different=0` |

不變比對的做法：

- 改前用 `git archive 254bab16d`，`PYTHONPATH` 指過去，跑預設陣容、效用 AI、`max_rounds=30`。
- 比對時去掉 `format`、`ruleset_hash`、`setup.ruleset`、`final_state.ruleset`。
- 改後是合併 RG-2 之後的版本，46 場依然逐字相同。

## 5. 預測與實際

| 測試 | 預測 | 實際 |
|---|---|---|
| CLI `skills_list`、`skills_show_all/00～15` | 變（多 16 招，從第一招新技能之後的分段都變） | 一致：17 個鍵全變，已重產 |
| CLI 7 場戰鬥 | 不變 | 一致 |
| parity complete、retier（既有 385 招） | 不變；新招只加 | 一致；`refactor_3wr2.json` 只加 16 招 × 2 |
| parity flash 126 條 | 不變，至多連擊終結 3 條 | 全部不變 |
| `test_proposal.py`、`test_proposal_l8.py` | 帶條件的題目會變 | **全部通過**：比預測少，固定的 Mock 回覆不受子集輪替影響 |
| `llm propose` Mock 快照 | 變 | 一致，已重產：3 題換成 combo_point、fury、marked；引擎修補從 `budget.weak` 換成 `exclusion.no_cooldown_big_area` |
| `run auto` 固定種子 | 變 | 一致：`test_run_auto_reaches_a_major_flash…[5]` 失敗。重掃 1～20，三項都練得到的是 4、6、7、9，種子 5 → 4 |

非 slow 的固定種子測試（三選一新方向的亂數全變；都換種子或放寬取法，斷言本身沒放寬）：

- `tests/roguelite/helpers.py` 的 `VICTORY` 種子 1 → 0。種子 0～11 中會贏的有 0、2、7，原本是 0、1、3、4、6、10，見平衡疑慮。
- `test_run_start_api.py` dev-advance 種子 5 → 4。
- `test_wish_two_keywords_txt2.py` 種子 5 → 37（0～11 都組不出「點燃＋倒地」雙關鍵字卡）。
- `test_opening_choice.py`：舊第 2 組全是生成技能時，改拿第一張，斷言照舊。
- `test_whiteboard.py`：候選測試對「中毒 2 階法器組不出主動白板」照設計允許退回手寫池。這是既有缺口，種子 7 的新方向抽到中毒才露出來。
- 招數登記：`test_yaml_patch_nw2a.py` 410 → 426、`test_skill_scaling` 413 → 429、`test_tuning_fields_nw2a` 410 → 426、`test_skill_icon_art_qi2a` 413 → 429、`test_coverage` 的 `_POOL_ONLY` 加 16 招。

## 6. 版號

三個都**不升**：

- `LOG_FORMAT`（/121，RG-2）：既有結算沒改。新條件只在帶它的技能上走新分支，`ConditionSpec` 沒有新欄位，不變比對 46 場 `different=0`。內容變動由 `ruleset_hash` 與內嵌規則包標出。
- `WORLD_RULES_VERSION`（31）：三選一、許願池、開局的變動都來自內容（`start_hidden`、`composer`、配方、嫁接）。`content_digest` 會自然變，舊世界日誌標成「規則已變」，和 KW-1 同理。組合器的程式改動只影響 KW-2 前會報錯的關鍵字。
- `CHAR_FORMAT`（/15）：存檔格式沒改。

沒有升版號，所以寫死版號的測試不用同步。

## 7. 待 PM 決定

1. **骨架限制下的示範招寫法**（6.32.1 寫「引擎不新增機制」；沒有骨架能以「累積層數」當核心，部分骨架的附帶也不收）：
   - 凝神、鷹眼各帶一個小護盾，血怒帶 1 回合增強。
   - 怒吼改成錐形、帶小傷害的蓄力招（原本是「嘲諷身邊」）。
   - 寸勁的推開、掠影步的躍步改寫成第二段，掠影步是「先刺一下再掠開」。
   - 若要照原文，需要在骨架加 `add_stack`（會改 LLM 出題子集）。
2. 凝神的「這回合不能移動」用自身狀態代價定身，但代價最短 2 回合，變成這回合加下回合都不能移動。
3. 嫁接的利用方是「自身層數達 N 時多一段傷害」（不消耗），不是「消耗層數多傷一截」，原因是 schema。N 佔位：連擊 3、其他 2。
4. 層數關鍵字沒有召喚灌注（同中毒）。
5. 「自己站在高處」＝所在格高度 ≥ 1，飛行不算；第一版 `handwritten_only`。
6. 調息與既有被動「調息」撞名，新招改叫「吐納」，請玩法 PM 定名。
7. 連擊點消耗新增「蓄力與終結骨架」也算終結技（給組合器用）。
8. 白板條件的層數 N、配方名稱（連刺、穿影、乘隙擊、怒擊、怒衝、盛怒擊、凝擊、一線、定心擊、運勁擊、氣貫、發勁擊）都是佔位。
9. 血怒的自傷是 HP 代價，不算「受傷」，不會觸發怒氣自動 +1。說明字「自己造成的傷也算」指的是押注自傷。
10. 說明字的連擊括號照現況，A 第 5 題回覆後再調。
11. 既有缺口：中毒在 2 階沒有法器能組的主動白板，三選一會退回手寫池。

## 8. 平衡疑慮（沒量，轉玩法 PM）

1. 固定種子 `build_fire` 種子 0～11 的勝場從 6 場掉到 3 場（0、2、7）。三選一新方向多了四個關鍵字，AI 可能常拿層數白板，但單招又吃不到層數。這是觀察，沒有量測。
2. 白板「條件利用」的層數門檻偏低（2 層）時，可能幾乎隨時成立，反而便宜。倍率照 `common`，和 KW-1 疑慮相同。
3. 鷹眼的條件是「高度 ≥ 1」，有高台的地圖幾乎每回合都 +1 專注。
4. 層數關鍵字的白板也能是法術版（例如法器的「連刺」），但連擊點的自動累積只看武器技，法器玩家選連擊會比較慢。

## 9. 其他

- `# noqa`：沒有新增。
- 新測試：
  - `tests/engine/test_stack_demos_kw2.py`（10 項）：站在高處、鷹眼、斷喉、貫心箭、咬牙撐住。
  - `tests/skillgen/test_stack_pools_kw2.py`（39 項）：池子門檻、三種武器的白板、組合器做得出累積與消耗、嫁接兩個方向、開局、許願池、白板確定性的 hypothesis 測試。
