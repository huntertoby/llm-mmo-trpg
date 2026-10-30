# Phase 4-L11 報告：AI 生成內容的敘事對齊、世界觀詞頭、卡片重複行

使用者看完 `docs/phases/4-L9/AI生成樣本.md` 後決定「排修正」。本段只用 `MockLLMClient` 測試，沒有連真模型、沒有連 8001 埠；真模型複測由 PM 安排（`uv run python scripts/sample_llm_content.py --out ...`，格式同 4-L9 樣本，多一行「一致性檢查重試次數」）。

## Commit

| commit | 內容 |
|---|---|
| `754e221e` | fix: card no longer lists identical repeated hits twice（範圍 3） |
| `9ed7b2ef` | feat: narrative consistency and world term limits for LLM naming（範圍 1a／1b／1c／2） |
| `3dee6ebc` | chore: sample script shows consistency retries and weapon attr line（範圍 4） |
| （本報告） | docs: Phase 4-L11 report |

範圍 1 與 2 動的是同一組檔案（命名檢查、prompt、世界觀資料），拆開會有一個中間狀態的 prompt 版本號，所以合成一個 commit。

## 做法

### 1. 敘事對齊效果

- **效果摘要（1a）**：`skill_summary` 多一欄 `effect_summary`（`trpg.llm.consistency.effect_phrases`），例如「風傷害」「推擊」「生成表面（表面「水」）」「打倒敵人時：返還 AP」。沒有數值與代號。卡片句子裡有「風會讓火焰、冰、毒…擴大」這類規則說明，丟給模型會誘導它寫錯元素，所以沒有用卡片句子，改用結構化的精簡摘要。命名指令新增：只描述 `effect_summary` 裡有的效果，不寫沒有的控制、元素或召喚物；有 `added_effects` 時要提到；世界觀詞的用量規則（數值從資料帶入）。
  - `NAMING_PROMPT_VERSION` 改為 `skill-naming/3`，快照已新增。
  - `FLASH_PROMPT_VERSION` 改為 `flash-variation/2`（note_zh 說明多兩句）。
- **一致性檢查（1b）**：詞表放在 `content/llm/effect_words.yaml`，schema 是 `trpg.content.effect_words`，已登記到 registry。每組詞有 `words`、`ignore`、`matches`（statuses／elements／surfaces／primitives／units），任一項對上就算有效果。
  - 技能的效果鍵（`skill_facts`）走訪整份技能資料，包括接續段、變奏、條件、`on_kill`、`then`、召喚物 ID，再加上技能本身的元素。
  - 名稱、概念、施放敘事任一段提到的詞找不到對應時，回報 `{欄位}.effect_mismatch`，訊息列出是哪些詞。回饋方式跟 C4 簡體字檢查一樣，帶 `<errors>` 重試，重試用完就退回模板敘事。
- **閃現（1c）**：
  - `note_zh` 用 `note_checker` 對**變化後**的技能做同樣的檢查，另外要求提到變化加上的效果（變化後有、變化前沒有的效果鍵）。不符時該項會被拒絕重試，錯誤碼是 `flash.note_zh.effect_mismatch`、`flash.note_zh.missing_added`、`flash.note_zh.world_terms`。
  - 變化名稱：`name_offer(..., before=skill_before(...))` 把變化前的技能交給 `name_skill`，名稱、概念、敘事都沒提到加上的效果時記為 `narrative.missing_added`，prompt 另帶 `added_effects`。`flash_eval` 與樣本腳本已經傳 `before`。遊戲內目前沒有呼叫 `name_offer`，接上時記得傳 `before`。
  - Mock 閃現提議的 `note_zh` 改為 null，因為 Mock 不知道變化加了什麼。

### 2. 減少世界觀詞頭

- 規則寫在資料：`world_shattered.yaml` 的 `naming.world_terms`（schema 是 `WorldTermRules`），由 `check_naming` 檢查（同一套重試與退回）。錯誤碼：
  - `name_zh.world_prefix`：名稱以世界觀詞開頭，或前 N 個字含禁止的字。
  - `name_zh.world_terms`：名稱裡的世界觀詞超過上限。
  - `concept.world_terms`、`cast_flavor.world_terms`、`flash.note_zh.world_terms`：每段的世界觀詞超過上限。
- 計數方式：由長到短、由左到右、不重疊，同一個詞重複出現也算次數（「晶頻率」算 1 個，因為「晶頻」先被吃掉）。
- 命名 prompt 寫明詞表、開頭限制與上限。
- Mock 命名的詞頭「晶輝」改成「星輝」；Mock 概念改成列出效果摘要（≤80 字），世界觀詞每段最多 1 個。

### 3. 卡片效果行重複

- **原因**：小變化「連打」（`multi_hit`）會把一段傷害拆成兩段**完全相同**的傷害效果，卡片每個效果各寫一句完整說明，所以同一句（連同風擴散的說明）列了兩次。這不是資料錯誤，兩段在實戰中都會結算。
- **修正**：新增 `mark_repeats`／`effect_lines`。相鄰而且文字相同的效果行，第一行改寫成「第 1 擊：…」，之後的行寫「第 N 擊：同上」；非傷害效果寫「再一次：同上」。行數不變，仍和 `effect_ids` 一一對應。接續段也套用同樣的處理。
- 回歸測試：`tests/narrative/test_skills_text.py` 新增兩項，其中一項用真的閃現路徑（氣爆＋連打）。既有的「卡片＝每個效果一句」測試改成比對 `mark_repeats` 後的結果，內容庫技能都沒有相鄰重複的效果，所以結果不變。前端夾具重產後沒有差異，CLI 快照也沒有變。
- **武器技算法行過長**：長的那段是「武器屬性看手上的武器：斧、雙手劍等＝力量；…」，只在**沒有持有者**時出現（樣本與圖鑑）。遊戲中卡片有持有者，會直接寫實際的屬性，例如「武器骰 1d8＋力量 × 0.3」。這段例子是 3-55 的設計，刪掉會丟資訊，所以引擎文字不改。樣本腳本改成另起一行「武器屬性（看手上的武器）：…」，數值行就不會被拉長。

### 4. 樣本腳本

`scripts/sample_llm_content.py` 的格式不變，每招多一行「一致性檢查重試次數」（`NamingOutcome.consistency_retries`／`FlashNameRecord.consistency_retries`）。武器屬性例子另起一行。閃現命名會傳入變化前的技能。存檔的 `FlashLlmName` 加了同名欄位，預設 0，舊紀錄可以照常讀取。

## 詞表與上限初稿（交玩法 PM 定稿）

### 一致性詞表（`content/llm/effect_words.yaml`）

| 組 | 詞 | 對應效果（任一） |
|---|---|---|
| 遲緩 | 遲緩、減速、緩速、拖慢 | 狀態 slow、frozen |
| 定身 | 定身、禁錮、束縛、纏縛、纏繞 | 狀態 root、entangled、frozen；淨化 |
| 暈眩 | 暈眩、昏迷、震暈、擊暈 | 狀態 stun |
| 冰封 | 冰封、凍結 | 狀態 frozen；冰表面 |
| 倒地 | 倒地、撂倒、絆倒、摔倒、掀翻 | 狀態 prone；擊倒、推倒、震波 |
| 擊退 | 擊退、推開、震退、彈開、轟開、震開 | 推、震波、衝撞推開 |
| 拉近 | 拉近、拽回、勾回、牽引、拖回 | 拉、換位、拉目標；吸引圖騰 |
| 致盲／噤聲／恐懼／嘲諷／流血 | 致盲、目盲、失明／噤聲、禁言／恐懼、驚懼、畏懼／嘲諷、挑釁／流血、出血 | 對應狀態 |
| 隱蔽 | 隱蔽、潛行、隱身、隱匿 | 狀態 concealed；煙霧、黑暗表面；瞬步 |
| 火 | 火、焰、炎、燃、焚、熾（不算：怒火、開火、火花、火網、魂火、燃起、燃燒一點） | 火元素、燃燒與火系姿態、火／油表面、清除／吹散表面、火系召喚物 |
| 冰 | 冰、霜、凍、寒氣、嚴寒、極寒 | 冰元素、冰凍與冰系姿態、冰表面、冰靈 |
| 雷 | 雷、電、閃電、霹靂（不算：地雷、悶雷） | 雷元素、雷靈 |
| 毒 | 毒、瘴 | 毒元素、中毒、毒表面；淨化、清除／吹散表面 |
| 風 | 狂風、旋風、疾風、颶風、暴風、強風、烈風、勁風、風刃、風壓、氣流 | 風元素、吹散表面 |
| 大地 | 大地、岩、地脈、地裂、裂地、沙（不算：岩漿） | 大地元素、石膚、地形升降、障礙、推倒、投擲；土牆、石像 |
| 神聖 | 神聖、聖光、聖、光明 | 神聖元素、聖光表面、聖灌注 |
| 暗影 | 暗影、陰影、幽影、黑暗、闇 | 暗影元素、黑暗／煙霧表面、隱蔽、致盲、瞬步、清除表面；影魅、殘影 |
| 水 | 水、濕、潮水、潮濕 | 水表面、清除／吹散表面、水精 |
| 召喚 | 召喚、喚出、召來 | 召喚、獻祭召喚物 |
| 藤蔓 | 藤蔓、藤、荊棘、根鬚 | 藤蔓召喚物、障礙、纏繞、定身 |
| 圖騰 | 圖騰 | 三種圖騰召喚物、區域 |
| 傳送 | 瞬移、傳送 | 傳送、瞬步、換位、跳躍、衝刺 |
| 治療 | 治療、治癒、癒合 | 治療、復活、再生 |
| 護盾 | 護盾、屏障、護罩 | 護盾、攔截、障礙、抬高地形；護盾、守護、石膚；守護靈 |

**誤判量**：拿 301 招手寫技能的原文跑同一套檢查（手寫技能不受檢查，這裡只用來估計誤判），約 31 段會被擋下。這些段落多半是比喻（「勁風把對手掀飛」「火舌」）、規則互動的說明（「風吹到火、冰、毒」），或形態、規則修正類的技能（形態 ID 沒有列進效果鍵）。

**需要玩法 PM 決定的取捨**：
- 「風」「土」「石」「浪」「灼」「擊倒」「纏住」「拉回」這幾個字常被比喻使用，初稿只收複合詞或直接拿掉。
- 單字「火」「雷」「水」「聖」仍然保留。
- 「擊倒」拿掉的原因是常被寫成「擊倒敵人＝打倒」。

### 世界觀詞上限（`world_shattered.yaml` → `naming.world_terms`）

- 世界觀詞：源晶、晶頻、碎界、碎晶、頻率、界域、晶核、晶輝、餘頻、殘頻。
- 名稱：不得以世界觀詞開頭，前 2 個字不得含「晶」「頻」，整個名稱最多 1 個世界觀詞。
- 概念與施放敘事：每段最多 1 個（同一個詞重複也算）；閃現 note_zh 也一樣。
- 「同一輪已用過的世界觀詞頭不得再用」這條沒有另外做，因為詞頭已經全面禁止，這條會自動成立。

## 驗收

- `ruff check .`、`ruff format --check .`、`mypy`（882 檔）、`lint-imports`（7 kept）：全部通過。
- pytest（`-m "(slow or not slow) and not llm"`）：
  - `tests/llm`：286 passed，其中新增 `test_consistency.py` 87 項。
  - `tests/narrative`、`tests/skillgen`、`tests/cli`：4228 passed、14 skipped。
  - `tests/content`、`tests/test_architecture.py`：1529 passed。
  - `tests/roguelite -k "flash or save or llm"`：68 passed。
  - `tests/test_sample_llm_content.py`：passed。
- 新增測試涵蓋：
  - 詞表引用的 ID 都存在。
  - 效果摘要本身不會被擋。
  - 青藤十字印類的錯配會被擋下，`ignore` 生效。
  - 漏寫加上的效果會被擋下。
  - 世界觀詞的開頭、數量、每段上限。
  - 不一致時重試並帶錯誤回饋；重試用完退回模板，並計算重試次數。
  - 閃現 note 被拒後重試；`name_offer` 要求提到加上的效果。
  - Mock 命名在前 60 招都不觸發一致性錯誤。
  - 卡片不再重複列出相同的效果行。
- 前端夾具重產後沒有差異（沒有動前端）。

## 待 PM 決定

1. **詞表與上限定稿**（玩法 PM）：上面兩張表；特別是單字詞的取捨與可接受的誤判量。
2. **重試次數不變**：一致性檢查和其他命名檢查共用 `max_retries`（3 次）。真模型複測時如果退回率明顯上升，要決定是放寬詞表，還是讓一致性錯誤另外多一次重試。
3. **形態與規則修正類技能**：`enter_form` 的形態、`rule_change` 的內容不算進效果鍵，這類技能的敘事比較容易被擋。目前 LLM 很少產生這類技能，所以先不處理。
4. **遊戲內的閃現命名**還沒有接上 `name_offer`（現在只有評估工具和樣本腳本在用）；之後接上時要傳 `before`。
5. **武器技算法行**：引擎文字不改（理由見範圍 3），只在樣本腳本裡另起一行。
