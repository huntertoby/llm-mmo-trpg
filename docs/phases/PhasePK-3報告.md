# Phase PK-3 報告：閃現接上挑選模式、組合器不做怪條件、三選一候選放寬

> 2026-11-15，實作者（PK-3）。依據：06 6.7「候選怎麼篩」、6.34.3～6.34.7、#165（使用者題 1「B 放寬」、題 2「B 擠掉」、題 3「B 只擋多字詞」）；玩法PM交接 4.1.23、4.1.24；提案第 2、3 節、7.7 第 2 段。
> 比較文件 `docs/phases/PhasePK-3比較.md`；資料、實機截圖與紀錄在 `docs/phases/PK-3資料/`。

## 1. 開關

- **閃現：`content/skill_pick.yaml` 的 `flash_enabled: true`（新開關，預設開）**，和三選一的 `enabled` 分開（可以只關閃現）。都不進數值工坊（工坊沒有布林欄位）。
- 只有來源「會挑選」（`LlmFlashSource`、重播的 `RecordedSource`、世界的 `_RecordedFlash`）時才走挑選；沒開 LLM（`UsageSource`）的出題完全照舊。
- 關掉＝逐字回到 LF-2 的提議流程（`tests/llm/test_flash_pick_pk3.py::test_switch_off_is_the_lf2_flow`：紀錄是 `flash-variation/6`、沒有 `picks`，和只會提議的來源結果相同）。LF-2 自己的測試改用 `tests.engine.helpers.lf2_library()`（開關關掉的內容庫）照跑，斷言沒動。

## 2. 三部分改了什麼

### A. 閃現、重閃接上挑選模式（`skillgen/flash_pick.py`、`flash_offer.py`、`llm/flash_pick.py`、`llm/prompts/flash_pick.py`）

1. **出題（程式）**：先照沒有 LLM 時的出題排好每一格（`_Layout.options`，就是原本的混合／指定類別／補位／轉型插入位置）。所以每格的類別、不指定時至少 2 類、指定類別只出該類、大變化的加深／橋接至少各 1、轉型保底（#70）佔的那一格與位置、強度下限（6.34.3）與 #160 例外格的「比原本弱」全由程式決定。
2. **候選**：每格第一個＝原本那一個；其餘依同一類的用法統計（`ranked`）往下取套得上、過強度下限的變化，同類的格子輪流分、格與格不重複，每格最多 `pool.flash_top_k`（新欄位，4，接工坊）。轉型保底那一格只有一個候選（LLM 只取名）。
3. **LLM**：一次呼叫回答全部格子（`flash-pick/1`；schema `{"s0": {pick, note_zh, name_zh?}}`，`pick` 是每格的 enum）。描述照 LF-2（不合格只丟描述）；名稱只在大變化、轉型格（6.34.3 小變化不改名），照 LF-2 的名稱檢查再加 **C3**；名稱不合格帶 `<errors>` 重問（最多 3 次、一份 10 秒內），仍不合格就用組合式名稱。連不上、逾時、格式壞＝每格第一個、沒有文字。
4. **紀錄與重播**：`FlashProposalRecord`／`FlashLlmRecord` 多選填 `picks`（空值不寫出），`accepted`＝每格選中的變化；重播照紀錄找回位置（`picks_by_key`），不呼叫 LLM。大世界預先生成改呼叫 `LlmFlashSource.prepare`（照開關挑或提議）。
5. **Mock**：`mock_flash_source(pick_index=0)`：每格挑 0 號＝沒有 LLM 時那一份，不寫文字。

### B. 組合器不做兩種怪條件（玩法 PM 4.1.23；`skillgen/composer_parts.py::build_condition`）

- 效果層級的條件：抽到掛在刻紋上、或「第一輪」掛在非傷害效果上時，不掛（亂數照舊消耗，只是沒有條件）。
- 技能層級：整招沒有傷害時不抽「第一輪」，也不給帶刻紋的招抽條件（骨架要求條件時重抽）。判定和打分的 `odd_conditions` 一致，所以扣分留著當保險。
- 驗證器不改：手寫的「第 1 輪才能用」霧影分身照樣合法（`tests/skillgen/test_composer_odd_pk3.py`）。
- 量：固定種子 1240 招，main 有 6 招怪條件（0.5%），PK-3 是 0；條件本身照樣出現（技能層級 201、效果層級 144）。

### C. 三選一候選放寬、單薄擠掉、閃現名稱詞（玩法 PM 4.1.24；`skillgen/pick_offer.py`、`skill_pick.py`、`llm/consistency.py`）

1. **「跟主路線」改扣分（題 1 B）**：每個候選有放寬層級——全部關鍵字＋路線符合 → 只帶多關鍵字格的部分關鍵字（#110 ③）→ 偏離路線 → 兩者。全部符合的不到 `pool.relax_until`（新，3）個時才整層補下一層；放寬的扣 `weights.keyword_relaxed_penalty`（150）、`route_off_penalty`（400）（新，接工坊）。種類照舊硬篩。路線＝加深、橋接跟主路線；新方向照原本那一張（07 7.2）。**符合路線的一律排在偏離前面**；路線符合的組合器候選一張都沒有時，原本那張手寫補位若符合路線就留著排第一（PK-2 同樣的退路）。LLM 挑到偏離、讓一份超過 2 張（#110 最多 2）時，從後面的格子改回第一名（`pick.off_route_cap`）。
2. **單薄的不進前 5 名（題 2 B）**：`skill_pick.drop_thin`，三選一每格與單題（`pick_slate`）都用；全格都單薄才照分數給。
3. **閃現變化名只擋多字的老套詞（題 3 B）**：`consistency.multi_char_strict`——加嚴詞組只留兩字以上的詞（「之擊」「墜落」「高處」「直線」…），單字的風、土、石、斬、劈與只剩單字的詞組不看。整招命名（PK-2）照舊全看。

## 3. 出題規則怎麼保證（鎖住的測試）

- 閃現：Mock 每格永遠挑 0、1、2、3、9（超出範圍）號，14 個請求（2 招 × 第 1／2／3 次、指定類別、大變化指定加深、重閃第 1、3 格）——每格類別與轉型位置和沒有 LLM 時相同、指定類別只出該類、`weaker`／`cost`／`major` 相同、選項都在那一格的候選裡、不重複；挑 0＝原本那一份；重播逐字相同（`test_mock_always_picking_one_index_cannot_break_slots`）。大變化加深／橋接與轉型保底照舊（`test_major_keeps_deepen_bridge_and_transform`）；候選依用法統計、互不重複（`test_slots_are_usage_ranked_and_disjoint`）；連不上模型＝原本那一份（`test_llm_down_falls_back_to_the_plain_offer`）。一輪的紀錄、存檔往返、選完寫進歷程：`tests/roguelite/test_flash_pick_run_pk3.py`；API 的描述與名稱來源：`tests/api/test_flash_llm_text_lf3.py::…_in_pick_mode`。
- 三選一：每格關鍵字（多關鍵字可放寬）、種類和原本相同、偏離 ≤ 2（`test_pick_offer_pk2.py` 的 `_check_slots` 改成 PK-3 規則）；不符合路線的候選一定帶扣分且排在後面；挑選器永遠挑最後一張時偏離不超過 2（`test_pick_offer_pk3.py`）；單薄的只在全格單薄時出現。

## 4. 快照與相容性（逐鍵）

| 鍵 | 預測 | 結果 |
|---|---|---|
| CLI 輸出雜湊（戰鬥 7 鍵、技能列表與 show 17 鍵） | 不變（手寫技能、戰鬥） | `tests/cli -m slow` 44 passed，沒有重產 |
| Mock 提議（`llm_propose_mock.txt`） | 可能變（組合器退路）；估計不中 | 不變（同上 44 passed） |
| parity 夾具（`test_refactor_parity.py`，閃現出題） | 不變（沒有 LLM 的出題路徑沒改） | `-m slow` 928 passed |
| 前端閃現選項夾具（`client/src/dev/fixtures/flashChoice.json`） | 不變 | **查清楚了**：用本分支重產到暫存區，和 repo 裡的**逐位元組相同**；用 main 重產也相同——PK-2 說的「重產會變」不成立。vitest 只讀 repo 裡的檔，沒有測試比對重產結果。沒有重產 |
| 前端技能圖示夾具 | 不變（手寫技能） | 沒動 |
| 三選一、run auto、`VICTORY` | 可能變（放寬與組合器） | `tests/roguelite` 278 passed，`VICTORY` 不用改 |
| `WLOG_FORMAT`、`WORLD_RULES_VERSION` | 升 | `trpg-wlog/12`（`/11` 照讀）、35；6 處寫死的版號跟著改 |
| `client/openapi.json`、`schema.d.ts` | 不變（API 型別沒改：`picks` 只在存檔／日誌） | 沒有重產 |
| `ruleset_hash`、`content_digest` | 變（`skill_pick.yaml`、`tuning_fields.yaml`） | 規則包雜湊不變 |

- **戰鬥不變比對**：`git archive main src content` 副本 vs 本分支，8 張圖 × 種子 1、2＋3 張頭目圖（盜賊巢穴、雲頂、熔心坑）× 種子 3～12，去掉 `ruleset_hash`：**`battles=46 events=18017 different=0`**。
- 存檔：`picks` 空值不寫出；`SAVE_FORMAT`、`CHAR_FORMAT` 不升（同 PK-1／PK-2 前例）。
- 改到的既有測試：LF-2 的提議流程測試改用 `lf2_library()`（`test_flash_propose`、`test_flash_lf2`、`test_flash_texts_lf1`、`test_consistency`、`test_flash_note_archaic`、`test_flash_diversity_script`、`tests/roguelite/test_flash_texts_run_lf1`、`tests/api/test_flash_llm_text_lf3` 的 LF-2 那題）；`test_scaling_follow` 的種子範圍 30 → 80（原本唯一會變的種子 28 被 B 換了結構）；`test_generated_content` 的機遇題改認 `pick == "llm"`（同 `world_pregen.offer` 的判定）；版號 6 處。斷言都沒放寬。

## 5. 實機（`PK-3資料/`）

- 自己起伺服器 `127.0.0.1:8237`（暫存區啟動器：照 `trpg serve` 建 app、靜態檔用主 repo 的 `client/dist`、存檔放暫存區；新開的一輪一律 `llm: true`；覆蓋開發路由 `dev-advance`，AI 代打時裝上這一輪的提議器、挑選器與閃現來源，到「下一場前」時對第一招可閃的技能開一次閃現）。結束時只停自己起的那個程序。
- LM Studio：`/api/v0/models` 只有 Gemma 載入；量測前速度 213、219 t/s；一次只跑一組（24 題約 2.3 分鐘、閃現 40 秒、實機約 4 分鐘）；跑完仍是 Gemma；沒改 `config/`、沒換模型。
- **三選一**：15 份、45 格——**llm 39（87%）、top 6（13%）**（升級 33 格：29／4；完整技能 12 格：10／2）。挑選紀錄 108 筆：1 次就過 71、重問 1 次 28、2 次 5、3 次都不合格退回 4。
- **閃現**：4 次（3 次第 4 次、1 次第 3 次大變化），全部 `flash-pick/1`、`source=llm`、1 次呼叫、0.9～1.3 秒；大變化那份 4 個選項都是 LLM 名稱（`name_source=llm`）並帶描述，小變化帶描述、名稱照舊。
- 截圖（headless Chrome、`--mute-audio`、`--remote-debugging-address=127.0.0.1`（沒開除錯埠）、`--force-device-scale-factor=1`、1280×1900，**1:1**）：`01-升級白板三選一.png`、`02-完整技能三選一.png`、`03-閃現選變體-大變化.png`（卡上「源晶推演」小標＝LLM 名稱）。API 回應 `實機API回應.jsonl`、伺服器紀錄（秒數、閃現紀錄、挑選紀錄）`實機伺服器紀錄.jsonl`。
- 觀察：01 那份升級的加深格是「虛空視界」（只上被標記，偏離路線）——那一格的候選全是標記白板（全格單薄才照分數給），LLM 挑了偏離的那張，這份偏離 2 張（上限內）。

## 6. 測試

- 新增 `tests/llm/test_flash_pick_pk3.py`（13 項）、`tests/roguelite/test_flash_pick_run_pk3.py`（2）、`tests/roguelite/test_pick_offer_pk3.py`（6）、`tests/skillgen/test_composer_odd_pk3.py`（3）；`tests/api/test_flash_llm_text_lf3.py` 加挑選模式一題。不用 hypothesis 跑候選池。
- 分目錄各自 `-n 8`、一次一組：`tests/llm` 482 passed（改 LF-2 測試後重跑失敗的 6 檔 169 passed）；`tests/skillgen` 4423 passed、14 skipped；`tests/roguelite` 278 passed；`tests/world` 1313（修版號後失敗的 6 檔 125 passed）；`tests/api` 1310（修後失敗的 2 檔 10 passed）。交件前 `tests/cli -m slow` 44 passed、`tests/sim -m slow` 19 passed、parity `-m slow` 928 passed。
- `ruff check`、`ruff format --check`、`uv run mypy`（1658 檔，含 tests）、`lint-imports`（14 kept）都通過。
- 自己啟動的背景程序（測試、伺服器、Chrome）都已結束；沒有跑 `scripts/check.py` 全量、平衡量測、戰鬥模擬（不變比對以外）。

## 7. 待 PM 決定

1. **閃現每格的候選常只有 1～2 個**：照 6.34.7「每格依類別先佔格」，候選只從同一類拿；範圍、連段這類一招常常只有 1 個套得上的變化（比較裡火焰箭第 1 次：範圍 1、連段 1、費用 2、元素 4），LLM 實際只在元素、加深、橋接格有得挑，34 格裡 31 格挑 0 號。要不要讓不指定類別的格子在「這類只有 1 個」時借別類的候選（混合至少 2 類仍由程式守）？屬出題規則，先問。
2. **三選一偏離**：沒有 LLM 時每份平均 1.1、最多 2（PK-2 1.06）；LLM 挑偏離的上限是一份 2 張。#110 的「平均 ≤ 1.1」要不要對「LLM 挑完」再量一次（實機 15 份裡有 1 份到 2 張）？
3. **還剩 19% 的格子只有 1 張**：召喚關鍵字、手寫補位格（被動撞擊、高處橋接）、非傷害保底格，要補組合器配方（PK-2 待決 1 的 C）。
4. **新欄位都是保守初值**（`relax_until` 3、`flash_top_k` 4、`route_off_penalty` 400、`keyword_relaxed_penalty` 150），已接工坊；`flash_enabled` 不在工坊。
5. 閃現名稱的加嚴詞只用在挑選模式的**名稱**；描述照 LF-2（不看加嚴詞組），照 6.34.7 原文「變化名」的字面。描述要不要也看多字詞？
6. `CHAR_FORMAT`、`SAVE_FORMAT` 沒升（只多選填欄位 `picks`），同 PK-1／PK-2 前例。
7. 實機截圖用的前端是主 repo 已建置的 `client/dist`（本分支前端沒改）；worktree 沒有 `client/node_modules`，沒有跑 tsc／vitest（型別沒變）。
