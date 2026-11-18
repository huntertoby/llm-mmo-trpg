# Phase PK-2 報告：挑選模式接上「升級三選一」與「完整技能」（開關預設開）

> 2026-11-15，實作者（PK-2）。依據：使用者原話（專案 PM 轉）「先把挑選模式接到「升級三選一」和「完整技能」這兩處，用開關控制，預設打開 好」「我打算全面採用這個方式了」「修」；設計 06 6.7、6.34.6、6.34.7，07 7.6；提案第 2、3、6、7 節。
> 比較文件 `docs/phases/PhasePK-2比較.md`；資料、實機截圖與日誌在 `docs/phases/PK-2資料/`。

## 1. 開關

- **`content/skill_pick.yaml` 的 `enabled: true`**（`SkillPickRules.enabled`，預設開）。數值工坊沒有布林欄位，所以這個開關沒有接工坊（其他新欄位都接了）。
- 只有呼叫端傳 `make_offer(..., pick=True)` 才生效；開關關掉時這些呼叫和 PK-2 前**逐字相同**（`tests/roguelite/test_pick_offer_pk2.py::test_switch_off_is_the_old_flow`；`tests/api/test_world_pregen_schedule.py::test_opportunity_asks_llm_for_at_most_one_card` 前半鎖舊流程）。

## 2. 接了哪些呼叫端

| 入口 | 位置 | LLM 一步 |
|---|---|---|
| 原型升級三選一（含白板格） | `roguelite/progress.py::_level_up` | 一輪的挑選器（`RunSession.picker`、`cli/run_llm.py`） |
| 原型完整技能（特殊時刻） | `progress.py::_complete_offer` | 同上 |
| 大世界機遇 | `world/solutions.py::_opportunity_offer`（同步版）、`api/world_pregen.py` 的 `offer` 生成函式（預先生成）、`api/offer_prefetch.py` 的機遇工作、`opportunity_wait_request` 的鍵 | 預先生成；重播只讀日誌（`OfferGen` 存最後收下的技能全文） |

沒接（照舊）：大世界任務三選一、許願池、閃現。自由設計的程式一行沒刪。

LLM 接法：`roguelite/llm_hook.py` 新增 `use_picker`／`current_picker`；`trpg.llm.pick.make_offer_picker`（真模型）、`mock_offer_picker(index=)`；`LlmProvider.picker()`（Local／Mock）。白板格原本不呼叫 LLM，接上後一輪是同步呼叫（原型沒有預先生成），所以挑選器自己做 **10 秒上限**（`OFFER_BUDGET_S`，06 6.34.7）：一份三選一用掉 10 秒後剩下的格子不請 LLM、用分數第一名。機遇照 6L-2b 每份最多 1 格請 LLM（`OPPORTUNITY_LLM_CARDS`），取「候選夠多的格子」裡的第一格。

## 3. 出題規則怎麼保證（`skillgen/pick_offer.py`，提案第 6 節 2A：每格各挑一）

1. 先跑**原本的產生器**（白板或完整技能，不請 LLM）決定三格：加深／橋接／新方向、新方向 10% 通用池、同路線找法與偏離（#110）、種類 70／20／10 全部由它決定。
2. 每格另外抽候選（獨立串流 `pick.slot/<格>`；白板 `slot_seeds` 16、完整技能 `complete_slot_seeds` 8；湊到 `top_k` 5 個設計就停），**只收**：全部關鍵字相同、同種類（白板分主動／被動／反應；完整技能主動含姿態）、跟不跟主路線和原本那張一樣、武器相容、不是傳說、不是要排除的 ID、不是手上技能的 ID 或設計、這份三選一前面幾格沒送出過的設計。白板用 `compose_whiteboard`，所以白板規則（一個核心效果、一個關鍵字）照舊由候選池保證。做不出別的才留原本那一張（例：手寫技能池的補位）。
3. **非傷害保底（#142）**：選一格只放非傷害候選（原本那張已是非傷害的優先，再依新方向 → 橋接 → 加深），不到 `top_k` 個時用 `pick.nondamage/<格>` 補抽（`nondamage_seeds` 10）。非傷害＝技能任何地方都沒有傷害原語（`is_nondamage`）。
4. 打分照 PK-1b（關鍵字＝這一格的關鍵字）＋新的「單薄」扣分（第 4 節），每格取前 5 交給 LLM。
5. LLM 只能回傳排好的候選之一、只換名稱與敘事；這裡再比一次結構（`same_structure`），不一樣就不收、用第一名（`pick.structure_changed`）。
6. 偏離張數：每格跟不跟主路線照原本，所以 `off_route` 和開關關掉時相同（測試逐格比對）。

鎖住的測試：Mock 永遠挑 0、2、4、9（超出範圍）號，兩種三選一的格子關鍵字、種類、路線、`off_route` 都和原本出題相同（`test_mock_always_picking_one_index_cannot_break_slots`）；每張送給 LLM 的候選都符合格子條件、保底格全是非傷害（`test_slate_entries_satisfy_the_slot_and_nondamage_slot`）；偷改結構的挑選器被擋（`test_picker_cannot_change_structure`）；10 秒上限（`test_picker_time_budget_skips_remaining_slots`）；`llm_max_calls`（`test_llm_max_calls_caps_the_slots_asked`）。

**PK-1 待決 2**：玩家手上技能（裝備＋備用）、行為紀錄、屬性、武器屬性由 `offers.pick_player(run)` 組成 `PickPlayer` 傳進打分；不放進 `CandidateRequest`，快取鍵只多一個 `pick` 鍵（手上技能由 `exclude` 的內容雜湊 ID 涵蓋）。手上技能只用 ID＋設計鍵擋，不比名稱（組合器的組合式名稱常同名，PK-1b 用名稱擋會把大部分候選擋掉）。

## 4. 打分新項目「這招有沒有料」（`skill_pick.thin_reasons`）

| 代碼 | 判定 | PK-1b 例 |
|---|---|---|
| `hollow` | 有作用的效果一個都沒有（只刻符文、只上「被標記」、只揭露） | Q5、Q16、Q20 |
| `conditional_only` | 沒有傷害，每個有作用的效果都要條件成立 | Q8「居高臨下時推開」 |
| `few_effects` | 史詩以上有作用的效果少於 `thin_epic_min_effects`（2） | Q12 史詩被動只有標記 |

每一項扣 `weights.thin_penalty`（250）。兩個新權重都接數值工坊（`pick` 對象）。只影響排序，不改合法判定。

## 5. 名稱與描述檢查加嚴

- `content/llm/effect_words.yaml` 加 10 組 `strict: true` 詞組：高處（高處、居高、俯衝、俯瞰、高空…→ 條件 `height_advantage`／`self_on_high_ground`、跳躍、隆起）、墜落、地形、打擊（之擊、一擊、重擊、斬、劈…→ 要有傷害類原語）、直線／扇形／環形／十字（→ 形狀）、單字風、單字土石。`EffectMatches` 多 `conditions`、`shapes`；`consistency.strict_facts` 多 `condition:`、`shape:` 事實。
- 只有挑選模式用（`pick_skill(strict=True)`）；閃現、自由設計的命名照舊，`check_added` 也略過加嚴詞組（測試鎖住）。不合格照常重問，3 次不合格退回組合式名稱。
- X2 的實情：PK-1b 收下那張其實有條件「居高臨下」（關鍵字「利用高處」），所以「高處」本身有對應；對不上的是「墜落」（沒有墜落類效果）和「之擊」（整招沒有傷害）。加嚴後這兩個詞會被擋，「高處」不擋（`tests/llm/test_pick_pk2.py::test_x2_style_name_is_caught`）。

## 6. 比較（24 題，Gemma；全文 `PhasePK-2比較.md`）

| | 自由設計 | 挑選 PK-2 | 挑選 PK-1b |
|---|---|---|---|
| 退回 | 7/24 | 1/24 | 0/24 |
| 秒數 中位／最慢 | 3.1／7.2 | 1.3／6.1 | 1.3／5.6 |
| 挑選只呼叫 1 次 | — | 13/24 | 20/24 |
| 收下的招單薄 | — | 1（Q5） | 至少 5 |
| 沒有元素 | 9 | 6 | 4 |

- PM 點名的 Q8、Q12、Q16、Q20 換成有料的招；Q5（刻印骨架）LLM 仍挑了只刻符文那張（已扣分、排第 2）。
- 加嚴的代價：重問變多、1 題退回（Q4，描述 3 次都提到效果沒有的詞）。
- 量測：`/api/v0/models` 只有 Gemma 載入、217 t/s；一次只跑一組，約 2.5 分鐘；跑完仍是 Gemma；沒改 `config/`、沒換模型。

## 7. 實機（`PK-2資料/`）

- 自己起伺服器在 `127.0.0.1:8137`（暫存區啟動器：照 `trpg serve` 建 app，多一個代打路由——戰鬥由 AI 代打，打完照遊戲本身的結算並裝上這一輪的提議器與挑選器；另外把每次挑選的秒數寫進日誌）。網頁 `?mute=1`、視窗 1280×800（截圖工具縮成 800×500 存檔，不是 1:1）。結束時只停自己起的那個程序。
- 開了 5 輪（`llm: true`，`llm_notice` 都是 null；另有 1 個開局請求用了不存在的關鍵字被拒）。
- **升級三選一與完整技能出現的卡全部帶 `pick` 欄位**（`實機API回應.jsonl`）：例 種子 44 升級＝三張 `composer`／`pick: llm`（魔導劍・噬焰、重壓崩裂、鬥志激盪）；種子 33 完整技能＝爆裂火種（llm）、引力爆（`pool`／`top`）、高處的屏障（llm）。
- 挑選呼叫（`伺服器日誌節錄.txt`）：全部 `source=llm`，多數 1 次就過、其餘重問 1 次；每格 0.46～2.65 秒（每份三選一第一格約 2.6 秒，其他約 0.5～1.2 秒）。沒有退回、沒有碰到 10 秒上限。
- 觀察：不少格子只做得出 1 張候選（不請 LLM、`top`；例「引力爆」是手寫技能池的補位）——同路線、同種類、全部關鍵字一起篩後，組合器常做不出替代。見待決 1。
- 截圖：`01-完整技能三選一-種子33.jpg`、`02-完整技能三選一-種子33-卡片.jpg`、`03-升級白板三選一-種子44.jpg`。

## 8. 快照與相容性（逐鍵）

| 鍵 | 預測 | 結果 |
|---|---|---|
| CLI 輸出雜湊（`tests/cli/snapshots/cli_output_hashes.json`：戰鬥 7 鍵、技能列表與 show） | 不變（不經過三選一） | `tests/cli -m slow` 44 passed，沒有重產 |
| Mock 提議（`llm_propose_mock.txt`） | 不變（`trpg llm propose` 不經過三選一） | 不變 |
| parity 夾具（`test_refactor_parity.py`，閃現出題） | 不變（閃現沒接） | 沒動 |
| 前端技能圖示夾具（`skill_icons.json`） | 不變（不看三選一） | 沒動 |
| 前端閃現選項夾具（`export_flash_choice_fixture.py`） | 重產會變（`auto_play` 拿到的技能不同），但沒有測試比對重產結果 | **沒有重產**，舊夾具照樣是合法資料 |
| `tests/roguelite/helpers.py` 的 `VICTORY` | 會變（三選一全變，AI 代打結果不同） | `build_fire` 種子 0 輸 → 改 1（0～11 勝：1、4、7） |
| `WLOG_FORMAT`、`WORLD_RULES_VERSION` | 升（日誌多選填欄位、機遇出題程式改了） | `trpg-wlog/11`（`/10` 照讀）、34 |
| `client/openapi.json`、`schema.d.ts` | `OfferTagOut.pick` | 重產（只多這一欄） |
| `ruleset_hash(library)`、`content_digest` | 變（`skill_pick.yaml`、`effect_words.yaml`、`tuning_fields.yaml`） | 規則包雜湊不變 |

- **戰鬥不變比對**：`git archive main src content` 的副本 vs 本分支，8 張圖 × 種子 1、2＋3 張頭目圖 × 種子 3～12，去掉 `ruleset_hash`：**`battles=46 events=19063 different=0`**（圖組照自己挑的 8＋3 張，事件數和 PK-1b 的 20458 不同；腳本在暫存區）。
- 存檔：`OfferTag.pick` 空值不寫出，關掉開關或舊存檔逐字不變；`SAVE_FORMAT`、`CHAR_FORMAT` 不升（同 PK-1、LF-1 前例，待決 5）。
- 改到的既有測試（都因為預設改走挑選模式）：`tests/roguelite/test_llm_run.py::test_full_run_with_mock_llm_is_deterministic`（多裝 Mock 挑選器）、`tests/api/test_run_llm_api.py` 的計數提供者（挑選器每格也算一次）、`tests/api/test_world_pregen_schedule.py`（舊斷言改成開關關掉時鎖住，另加挑選模式最多 1 格）、`helpers.py` 的 `VICTORY`、6 處寫死的版號（`test_field.py`、`test_field_lineup_seed.py`、`test_flash_texts_world_lf1.py`、`test_save.py`、`test_opening_stages.py`、`test_pr2a_range_practice.py`）、`test_save.py` 不認得的格式改 `/12`。

## 9. 測試

- 新增 `tests/roguelite/test_pick_offer_pk2.py`（26 項，固定 build 與種子，不用 hypothesis）、`tests/llm/test_pick_pk2.py`（6 項）。
- 分目錄各自 `-n 8`、一次一組：`tests/llm` 469 passed；`tests/skillgen` 4423 passed、14 skipped；`tests/roguelite` 270 passed；`tests/world` 1313 passed；`tests/api` 1310 passed、1 skipped；`tests/content`＋`test_architecture.py` 3137 passed。交件前 `tests/cli -m slow` 44 passed、`tests/sim -m slow` 19 passed。
- `ruff check`、`ruff format --check`、`uv run mypy`（1649 檔，含 tests）、`lint-imports`（14 kept）都通過。
- 前端只改型別（`schema.d.ts` 多一個選填欄位），worktree 沒有 `client/node_modules`，**沒有跑 tsc／vitest**，請 PM 合併後順手跑。
- 自己啟動的背景程序（測試、伺服器）都已結束；沒有跑 `scripts/check.py` 全量、平衡量測、戰鬥模擬（不變比對以外）。

## 10. 待 PM 決定

1. **很多格子只做得出 1 張候選**（不請 LLM、用原本那張）：同路線＋同種類＋全部關鍵字一起篩後，組合器常做不出替代（例：感知主路線的帶電完整技能，組合器只做得出智力縮放；被動的撞擊白板）。實機看到的 10 份三選一、30 格裡有 15 格是 `top`（大多是這個原因），測試用的機遇角色三格都只有 1 張。可選：A 照現狀（規則不放寬）；B 這類格子把「跟主路線」改成扣分；C 補組合器配方（提案第 5 段）。屬規則類，先問。
2. **加嚴詞組的範圍**（尤其單字「風」「土」「石」和「斬」「劈」）：挑選重問的題數從 4/24 升到 11/24，1 題退回。詞表是資料，可再調；要不要也用在閃現命名？
3. **完整技能出題變慢**：每份平均多約 1.9 秒（`complete_slot_seeds` 8；組合器指定關鍵字每個種子 0.05～0.2 秒），原型沒有預先生成。工坊可調。
4. **機遇每份最多 1 格請 LLM**（6L-2b）照舊，挑選模式下其他兩格是分數第一名＋組合器原名；挑選每格約 0.5～2.6 秒，要不要放寬？
5. `CHAR_FORMAT`、`SAVE_FORMAT` 沒升（只多選填欄位 `pick`），同 PK-1／LF-1 前例。
6. 權重、種子數全是保守初值（`skill_pick.yaml`），由使用者在工坊調；`enabled` 不在工坊。
7. Q5 這類骨架固定是刻印的題目，候選本來就多半只刻符文；單薄扣分管不到 LLM 的選擇（LLM 不能改候選）。要不要讓單薄的候選不進前 K？

## 開發 PM 裁定（2026-11-15）

- **驗收通過，合併。** 開關 `skill_pick.yaml` 的 `enabled: true`。關掉時和 PK-2 前逐字相同，有測試鎖住。驗證和規則都沒放寬，CLI 和 Mock 快照不變，戰鬥 46 場 different=0。WORLD_RULES_VERSION 升到 34、日誌格式升到 trpg-wlog/11（/10 照讀），接受。合併後重產 OpenAPI 沒有差異。實機截圖 02 看得到完整技能三選一，卡片帶挑選模式命名。截圖工具把 1280×800 縮成 800×500，不是 1:1，記錄在案。
- 既有測試只改固定種子和讀檔版號，斷言沒有放寬（VICTORY 種子 0→1，因為三選一變了）。
- 待決 1（約一半的格子只做得出 1 張候選，所以沒請 LLM）：這是挑選模式能不能發揮的關鍵。目前是「同路線＋同種類＋全部關鍵字」一起篩；要放寬、改成扣分，還是補組合器配方，屬於出題規則，轉給玩法 PM 定，答案併進 PK-3。
- 待決 2（加嚴的詞組要不要也用在閃現命名）：併進 PK-3（閃現）一起做。
- 待決 3、4（完整技能多約 1.9 秒；機遇每份最多 1 格請 LLM）：維持現狀，比較文件裡列給裁判參考。
- 待決 5（存檔版號沒升）：照 PK-1／LF-1 前例，接受。
- 待決 6（刻印骨架題的單薄候選不進前 5 名）：和待決 1 一起轉給玩法 PM。
