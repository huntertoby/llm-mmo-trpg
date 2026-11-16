# Phase PK-4 報告：許願池「願望驅動」、閃現借別類候選、閃現描述擋多字老套詞

> 2026-11-16，實作者（PK-4）。依據：07 7.6「許願池：願望驅動」（使用者「A（建議）」，玩法PM交接 4.1.22）；06 6.7、6.34.6、6.34.7、#165；玩法PM交接 4.1.25（使用者「好那都按照建議」：題 1 B、題 2 A、題 3 B）。
> 比較文件 `docs/phases/PhasePK-4比較.md`；資料、實機截圖在 `docs/phases/PK-4資料/`。

## 0. 先講結論

- A、B 都做完、有測試鎖住；開關 `skill_pick.yaml` 的 `wish_enabled`（預設開，關掉逐字回到 WP-1～3 的許願流程）。
- **真模型量測沒做**：開工時 LM Studio 沒有服務、沒有任何模型載入（`lms ps`：No models are currently loaded）。照上手筆記第四節第 8 點「loaded 不是只有 Gemma 就停下回報」停下；我試著照同一點 `lms unload --all`＋`lms load google/gemma-4-26b-a4b-qat`，被權限擋下，沒有再試。比較改用 Mock 跑（程式那段的候選、標籤命中、做不到的那一行、秒數是真的；名稱、描述、回應願望那一句不是模型寫的）。**注意**：我跑 `lms ps` 時它印了「Waking up LM Studio service...」，之後 `localhost:8001` 開始有回應（仍沒有載入模型）——可能是那個指令把 LM Studio 的背景服務叫醒了；我沒有再碰 LM Studio。
- 實機：自己起的伺服器（Mock 模型來源）開到許願池、許一個願、截了卡片與魔導書扉頁（4 張，DPR 1）。

## 1. 開關

- `content/skill_pick.yaml` 的 **`wish_enabled: true`**（`SkillPickRules.wish_enabled`；工坊沒有布林欄位，不進工坊）。
- 打開：文字許願翻需求標籤、照標籤出題、挑 3 張；「從清單點選」改成五類標籤。
- 關掉：`wish_request` 的鍵、生成函式、引擎驗證、面板（`tag_groups` 空）全部回到 WP-1～3。WP-1～3 的舊測試（`tests/world/test_wish.py`、`tests/api/test_wish_pregen.py`、`tests/api/test_wish_api_wp2.py`）改用 `tests.engine.helpers.wish_off()`（開關關掉的內容庫）照跑、斷言沒動；`tests/world/test_wish_pk4.py::test_switch_off_refuses_tags` 另鎖住關掉時不收標籤、沒有 `wish` 紀錄、三選一標示和舊流程一樣。
- 許願池的自由設計程式（`match_wish`、`WishSource.proposer`、`make_proposer(player_text=)`）沒刪。

## 2. A 許願池願望驅動（07 7.6）

| 07 7.6 的點 | 做法（檔案） |
|---|---|
| 1 願望 → 需求標籤 | `llm/wish_tags.py::match_wish_tags`、`llm/prompts/wish_tags.py`（`wish-tags/1`）。願望只在 `<player_input>`（系統區沒有願望，跳脫後放最後）；schema 五類都是 `enum` 陣列、`maxItems` 照上限、可以空。回應先過 pydantic（`WishTagsText`，多餘欄位拒絕），格式壞了帶 `<errors>` 重問（同 WP-1，最多 `max_retries`）；清單外、重複、超過上限的那一項丟掉、其餘照用（`skillgen/wish_pick.py::clean_wish_tags`，代碼 `wish.dropped.<類>`）；**一個都沒選到也算成功**，照一般完整技能的打分出題。連不上或用完＝沒有標籤 → 引擎拒絕、不扣錢（同 WP-1）。標籤清單在 `skill_pick.yaml` 的 `wish_tags`（元素 9、效果類型 8、形狀 5、種類 3；關鍵字用內容庫 16 個），怎麼算命中寫在資料裡（效果類型＝原語／狀態清單、控制類別狀態、增益狀態；形狀＝形狀 ID 清單）。 |
| 沒有 LLM 時點選 | 面板「從清單挑」換成「從清單點選」五類標籤（每類有上限、至少選 1 個）；`WishAction.tags`；舊用戶端送關鍵字時當成只有關鍵字的標籤。 |
| 2 照標籤做大池候選 | `skillgen/wish_pick.py::wish_pool`：獨立串流 `pick.wish`，**關鍵字、種類是出題條件**（有關鍵字時每張至少帶一個、雙關鍵字輪流指定；有種類時只收那一種；沒有種類時每個種子照 06 6.34.1 的 70／20／10 擲），依設計鍵去重、手上已有的、排除的、傳說、武器不合的不收，湊到「候選量」就停（最多抽候選量 × 1.5 個種子）。**標籤補抽**：元素、效果類型、形狀的標籤一張都沒做到時，用該標籤的獨立串流（`pick.wish.tag/<類>/<值>`）再抽最多候選量 ÷ 2 個種子、只收做到它的、最多 3 個（Mock 比較裡 W3「火焰」沒補抽時 0 張火焰、補抽後 3 張都是）。不到 3 個時放寬（不看種類與關鍵字）補到 3 個。 |
| 3 願望相合最大權重 | 一般完整技能的分數（`score_candidate`，關鍵字＝願望的關鍵字）＋ `weights.wish_match`（**1000**）× 命中的標籤數；高過協同上限（150 × 5 = 750）。單薄的先拿掉（不到 3 張時照分數補回），依多樣性排好前「候選量」個。工坊兩欄：`pool.wish_candidates`「許願池：候選量」（18，07 初值 15～20）、`weights.wish_match`「許願池：願望相合」（1000）。 |
| 4 LLM 挑 3 張並回應願望 | `llm/wish_pick.py::make_wish_picker`、`llm/prompts/wish_pick.py`（`wish-pick/1`）：一次回答 3 張（`pick` 不重複、名稱與兩段文字同挑選模式的檢查＋加嚴詞組、`wish_zh` 回應願望一句 ≤ 40 字、只能提到這張有的效果〔加嚴詞組也看〕）。不合格的那幾張帶 `<errors>` 重問（合格的留著，10 秒內）；最後仍不合格：名稱不合格的那張不收（程式依排序補），只有回應那句不合格就只丟那句（`wish.reply_dropped`）。程式再比一次結構（`same_structure`），LLM 改了就不收。 |
| 4 魔導書扉頁 | `PendingOffer.wish`（`WishNote{text, tags}`）→ 選到後記進 `CharacterState.skill_wishes`（技能 ID → 願望原文；重閃、階級重配後沿著原本的技能找，`growth.skill_wish`）。API `WorldCharacterView.skill_wishes`；前端成長面板的技能卡多一列「扉頁　你的願望：「…」」（React 純文字，`<b>` 之類照字面顯示，有測試）。點選標籤（沒有原文）不寫扉頁。 |
| 5 做不到時照實寫 | `wish_pick.wish_miss_zh`（程式產生）：「最接近你願望的一招：有{做到的}；{做不到的}這次做不到。」；一個都沒做到時省略「有…；」（**待 PM 決定 4**）。全部命中不寫。存在 `OfferTag.wish_miss_zh`，**引擎收 LLM 版時照標籤重算**（不信任傳進來的字）。卡上另有 `wish_reply_zh`（回應願望）。 |
| 7 次數、費用、強度 | 照舊：每週 2 次、4 任務幣、都不拿退 2；三張照完整技能（`at_run_tier`＋`as_complete`，+120‰）。 |

- **引擎驗證**（`world/wish.py::_tags_acceptor`）：標籤合清單、`keywords` 等於標籤的關鍵字；LLM 版三選一要過 `checked_offer`（完整技能、同階級、標示一一對應）、剛好 3 張、設計不重複，否則只丟三選一（`partial`，引擎照標籤排序取前 3 名）。**沒有重算整個候選池去比對每張是不是池裡的**（要再花 0.3～5 秒；待 PM 決定 3）。
- **資料流**：`WishGenRequest.tags_mode`（鍵多 `mode: tags`，舊流程的鍵逐字不變）→ API `world_pregen._wish_tags_generator` → `WishGen.tags`（新選填欄位）→ 日誌 `generated` → 重播 `recorded`（不呼叫 LLM；`tests/api/test_wish_pk4.py::test_text_wish_is_logged_and_replayed_without_llm`）。
- **前端**：`WishPanel` 的 `TagPane`（五類標籤）、下固定區「已選：…」；三選一畫面多「你的願望：「…」」「池子聽到的：…」兩行，卡上用回應願望＋「最接近…」取代「加深／橋接／新方向」；成長面板的扉頁。字都是暫定字（`wish.ts` 的 `WISH_ZH`、`SkillCardView.GRIMOIRE_ZH`）。

## 3. B 玩法 4.1.25

1. **閃現不指定類別時借別類**（`skillgen/flash_offer.py::_slots`）：先照 PK-3 同類輪流分；**不指定類別時**還沒滿的格子再從所有可用類別輪流借（依用法統計、不重複）。指定類別照舊不借。挑完由 `skillgen/flash_pick.py::keep_mix` 守住「混合至少 2 類」（不夠時從後面的格子改回第一個，那格不留文字，代碼 `pick.mix_kept`；LLM 層在寫紀錄前就守住，所以紀錄的 `picks`／`accepted` 就是最後的選項，重播一樣）。轉型保底照舊固定。prompt `flash-pick/2`：借來的候選卡多 `category`。
2. 偏離照現狀，沒改。
3. **閃現描述也擋多字老套詞**（`llm/flash_pick.py::_Checker._note_strict`）：描述照變化名的加嚴詞組（只看多字詞，單字不擋）比對；不合格帶 `<errors>` 重問（`note_zh.strict_word`），用完次數只丟描述（`flash.note_dropped.strict_word`）。其他描述檢查照 LF-2（不合格只丟、不重問）。
- 量（不呼叫 LLM，PK-3 的 10 個情境）：可挑的 31 格，只有 1 個候選的 16 → 11；候選 64 → 75；有借的格子 7（22%）。

## 4. 快照與相容性（逐鍵）

| 鍵 | 預測 | 結果 |
|---|---|---|
| CLI 輸出雜湊（戰鬥、技能列表與 show） | 不變（手寫技能、戰鬥沒動） | 見第 6 節 `tests/cli -m slow` |
| Mock 提議（`llm_propose_mock.txt`） | 不變 | 同上 |
| parity 夾具（閃現出題 JSON） | 不變（沒有 LLM 的出題路徑沒改；借別類只在挑選模式） | 見第 6 節 |
| 技能圖示夾具（`tests/narrative/test_skill_icon.py`） | 不變（組合器沒改） | `tests/narrative` 通過，沒有重產 |
| 前端夾具（`flashChoice.json`、`skillCards.json`…） | 不變 | 沒重產 |
| `client/openapi.json`、`schema.d.ts` | 變 | 重產：`WishTags`、`WishTagGroupView`、`WishView.tag_groups`、`WishAction.tags`、`OfferTagOut.wish_reply_zh`／`wish_miss_zh`、`PendingOfferView.wish_text_zh`／`wish_tags_zh`、`WorldCharacterView.skill_wishes`（一起 commit） |
| `WLOG_FORMAT` | 升 | `trpg-wlog/13`（`/12` 照讀）；版號 4 處測試跟著改 |
| `WORLD_RULES_VERSION` | 升 | 36（許願、閃現出題的程式改了）；2 處測試跟著改 |
| `CHAR_FORMAT`、`SAVE_FORMAT` | 不升 | 新欄位 `PendingOffer.wish`、`CharacterState.skill_wishes` 都是空值不寫出（舊存檔逐字不變，有測試）；同 PK-1～3 前例（待 PM 決定 5） |
| prompt 版號 | 新、升 | `wish-tags/1`、`wish-pick/1`（新）；`flash-pick/1 → /2`；`wish-match/1`、`flash-variation/6`、`skill-pick/2` 沒動 |
| `ruleset_hash`、`content_digest` | 變（`skill_pick.yaml`、`tuning_fields.yaml`） | 規則包雜湊不變（`skill_pick.yaml` 不嵌入規則包） |

- 改到的既有測試（都沒放寬斷言，只照使用者定案的新規則改寫）：`test_flash_pick_pk3.py` 的格子規則（不指定類別時每格類別可以變，改成「混合至少照原本」、同類候選在前、借來的在後；指定類別照舊每格同類）、`test_flash_pick_run_pk3.py`（Mock 挑最後一個同類的候選）、版號 6 處、WP 三個舊測試檔改用 `wish_off()`、前端 `wp3Wish`／`wp3bWish` 的假資料補 `tag_groups: []`、`test_architecture.py` 的允許清單加 `trpg.llm.wish_pick` 的 `make_wish_picker`／`pick`（理由：避免撞名，比對所有內建技能名，同 PK-1 的 `pick_skill`）。

## 5. 實機（`PK-4資料/`）

- 自己起伺服器 `127.0.0.1:8797`（暫存區啟動器：`create_app(llm=MockLlmProvider(), static_dir=本 worktree 的 client/dist)`，存檔在暫存區；`POST /api/world/llm {enabled:true}`）；角色存檔改成主城、守池人正下方朝北、任務幣 9（上手筆記第 147 條）。無頭 Chrome（`--mute-audio`、`--remote-debugging-address=127.0.0.1`、除錯埠 9711、`--force-device-scale-factor=1`、CDP `deviceScaleFactor 1`、量過 `devicePixelRatio = 1`、網址 `?mute=1`），1280×1900。開之前確認 8797、9711 沒人用；結束時只停自己起的伺服器與 Chrome，兩個埠都沒在聽。
- **模型是 Mock**（LM Studio 沒載入模型，見第 0 節）：日誌裡 3 張都是 `pick: llm`（Mock 挑選、Mock 命名）；Mock 不寫「回應願望」那一句，所以卡上只有「最接近…」那一行。卡上沒有「源晶推演」小標：前端 `isLlmTag` 只認 `source == "llm"`，挑選模式（PK-2 起）的 `pick: llm` 本來就不顯示（不是這段改的，待 PM 決定 9）。
- `01-許願池-從清單點選標籤.png`：「從清單點選」五類，選了冰凍、火焰、控制，下固定區「已選：…」。
- `02-許願池-說出願望.png`：「想把敵人凍在火裡」。
- `03-許願池三選一.png`：標題「許願池」、「你的願望：「想把敵人凍在火裡」」「池子聽到的：冰凍、火焰」；3 張冰凍招，每張卡上「最接近你願望的一招：有冰凍；火焰這次做不到。」。**觀察**：3 張都標「偏離路線」（輔助英雄主屬性感知、這份候選都吃智力），許願不看路線（07「方向由玩家決定」），但偏離標籤照舊顯示（待 PM 決定 6）。
- `04-魔導書扉頁.png`：學了「裂隙低語」後成長面板，技能卡「扉頁　你的願望：「想把敵人凍在火裡」」。

## 6. 測試

- 新增：`tests/skillgen/test_wish_pick_pk4.py`（4）、`tests/world/test_wish_pk4.py`（15）、`tests/llm/test_wish_pk4.py`（8）、`tests/api/test_wish_pk4.py`（9）、`tests/llm/test_flash_pick_pk4.py`（5）、`client/src/world/pk4Wish.test.ts`（6）。不用 hypothesis 跑候選池。
- 分目錄、一次一組（-n 8）：TESTS_RESULTS
- `ruff check`、`ruff format --check`、`uv run mypy`（含 tests、scripts）、`lint-imports`（14 kept）、前端 `tsc`、vitest（world、run 1006＋新 6）、`vite build` 都是 0。
- 自己啟動的背景程序（測試、伺服器、Chrome）都已結束；沒有跑 `scripts/check.py` 全量、平衡量測、戰鬥模擬（不變比對以外）。

## 7. 待 PM 決定

1. **真模型量測沒做**（LM Studio 沒載入模型、我載入被擋）：載好 Gemma 後跑 `uv run python scripts/wish_compare.py run` → `report`，把 `PK-4資料/wish_compare.md` 補進比較文件；也要順便確認秒數（程式那段最長 5.3 秒＋兩次呼叫，召喚、高處類可能逼近 10 秒）。
2. **雙關鍵字是「至少帶一個」**：07 寫「標籤裡的關鍵字當成出題條件」，兩個關鍵字都要帶的話候選常不夠，我照最保守的「每張至少帶一個、兩個都帶的命中多一分」做（舊流程是「三張都帶第 1 個」）。
3. **引擎沒有重算候選池**去確認 LLM 版每張都在池裡（只看完整技能、同階級、3 張、設計不重複；LLM 層已比過結構）。要不要加（每次許願多 0.3～5 秒）？
4. 「最接近你願望的一招」那句在一個標籤都沒做到時寫成「最接近你願望的一招：召喚這次做不到。」（省略「有…；」），請玩法 PM 定字；三選一畫面的「你的願望」「池子聽到的」、清單分頁的字、扉頁的字都是暫定字。
5. `CHAR_FORMAT` 沒升（新欄位空值不寫出），同 PK-1～3。
6. 許願的卡照舊標「偏離路線」（主屬性不同時）；許願不看路線，要不要在許願的三選一不顯示偏離標籤？
7. 新數值都是保守初值：候選量 18、願望相合 1000（工坊兩欄）；程式常數：種子上限 候選量 × 1.5、標籤補抽 候選量 ÷ 2 個種子／最多 3 個。
9. 三選一卡上的「源晶推演」小標只認 `source == "llm"`（自由設計）；挑選模式（PK-2 起，含許願）LLM 挑選命名的卡（`pick: llm`）不顯示。要不要兩種都顯示？（前端一行，沒有順手改）
8. 沒有 LLM 時點選標籤至少要選 1 個（照 WP「挑 1～2 個關鍵字」的保守做法）；07「每一類都可以不選」我解讀成每一類各自可以不選。
