# Phase 3T｜Phase 4 前整理（審查後；2026-10-29 開發 PM）

> 依據：`docs/phases/Phase3後段審查-Python.md`（以下 P1～P10）、`docs/phases/Phase3後段審查-前端.md`（以下 W1～W10）。兩位審查者都建議 Phase 4 前先排一個整理子階段。**純整理，玩法行為不變**（行為一致：戰鬥快照雜湊、重播、卡片文字不變；有變要在報告逐條說明理由）。一次最多 2 個 agent。

## 1. 段落

| 段 | 內容 | 來源 | 模型 | 前置／平行 |
|---|---|---|---|---|
| 3T-1 | **修正規則 change 種類與預算旋鈕進 YAML**：① change 種類（`content/skills.py` 的修正規則 change、`skillgen/budget.py`、`player_text.py`、`engine/modifiers.py` 各一份）改由 YAML 宣告，載入時檢查每種在預算、玩家文字、引擎都有對應（比照原語登錄表的 coverage 檢查），漏寫在載入時報中文錯誤，不在執行時才 `KeyError`；② 預算旋鈕（`skillgen/composer_parts.py` 的 `fixed` 表）改在 `skill_primitives.yaml` 的參數上宣告（或明寫 `knob: none`），coverage 檢查涵蓋；補齊審查實測缺旋鈕的 `grant_ap`、`extra_reaction`、`summon`、`zone`、`revive`、`restore_resource`（耐力）。LLM 提議 schema 改由 YAML 產生修正型技能的 change 欄位（若現有產生器結構允許；不行就寫進報告留給 4-L8）。 | P1、P2 | opus | 現在派；與 3T-4 平行 |
| 3T-2 | **種族技檢查全部效果＋LOG_FORMAT 策略＋小項**：① 種族技合法性檢查走過全部效果（目前只看第一個），docstring 對齊；加測試確認每種種族效果與形態效果都有引擎處理與 AI scorer（coverage）；② `LOG_FORMAT`：`runner.py` 的約 350 行變更紀錄搬到 `docs/`（例如 `docs/phases/戰鬥紀錄格式變更.md`），程式只留目前版本一行說明；戰鬥紀錄加 `ruleset_hash`（規則包內容雜湊，重播時比對、不符給中文錯誤），之後只有紀錄結構變才遞增版號（策略寫進文件）；③ `proposal_forms.py` 的「form（型態）」改名為 layout，`_MAX_EFFECTS` 合併成一處；④ 新增的 `except KeyError` 吞錯改成直接拋錯（`stack_gain.py`、`rules/race.py`、`race_skills.py`），`skillgen/validate.py` 縮放規則改為必填（測試內容庫補上）；⑤ 引擎寫死的新數值與內容 ID 移到 YAML（`DECOY_TEMPLATE`、誘餌壽命、透支回合、AI `_DECOY_RANGE` 改讀 races.yaml 射程）。 | P3、P4、P6、P7、P8 | sonnet | 3T-1 後 |
| 3T-3 | **`content/skills.py` 拆成 `content/skills/` 套件**（純搬移，公開匯入路徑相容） | P5 | sonnet | 3T-2 後；可和 Phase 4 前段平行 |
| 3T-4 | **前端整理**：① 武器小圖示（`weaponIcon.ts`）改用 ink 畫法，刪掉走不到的舊畫法（`paperdoll.ts` `drawWeapon`／`legacyHooks`、`paperdollGear.ts`、`paperdollSideWeapon.ts` 與對應測試）；② 元素配色統一成 `render/palette.ts`（`artPalette`、`vfxPalette`、`glossary`、`skillParts`、`statusIcon`、`inkForm`、`summonArt`、`gearIcon` 改讀它；數值以美術 PM 定案的 `artPalette` 為準，有衝突寫進報告），`inkForm` 支援所有元素色；③ 共用 `color.ts`（`darken`／`mix`／`shade`）、材質色從 `MATERIAL` 導出、視角共用 `View` 型別、`HAIR_COVERED` 與 `COVERS` 合併；④ `inkStyle.ts` 的 `shadeDir` 改成參數（不留模組狀態），快取鍵若受影響一併處理；⑤ 觸控可釘住說明卡（`Hint`、`PartTip`、`StackTip` 加 `pinOn: "touch-only"`，`StackTip` 改用 `PartTip`）；⑥ 順手：`ArtTextures` 共用 `canvas()` 快取、`unitSprite.ts` 的灰階 filter 共用、`resolveDoll` 算一次、兩個 `raceCardLines` 改名、副手附魔換色條件改「副手和主手同種武器」。外觀不變（截圖對照）。 | W1、W2、W3、W5～W9 | sonnet | 現在派；與 3T-1 平行 |

**延到 Phase 4 期間（不擋）**：P9 組合器骨架 ID 分支移 YAML、私有匯入改公開；P10 `engine/` 拆子套件；W4 形態外觀與標籤對照（形態不由 LLM 產生，標籤中文改讀 glossary 時再做）；W10 `BattleScreen.tsx`、`styles.css` 大型整理（`onTileClick` 抽純函式可先做）。

## 2. 驗收（每段）
- 行為不變：`tests/cli` 戰鬥快照雜湊不變（3T-2 的 `ruleset_hash` 會改紀錄內容，例外並說明）、重播一致、卡片文字不變。
- pytest（相關目錄，`-m "slow or not slow" tests/cli --timeout=3000`）、ruff、format、mypy、lint-imports；前端段：vitest、tsc、build、排版煙霧檢查、截圖前後對照。
- 報告 `Phase3T-N報告.md`。

## 3. 驗收紀錄

### 3.1 3T-4 驗收（2026-10-29，開發 PM）
- 報告 `Phase3T-4報告.md`。`render/color.ts`、`render/material.ts`、`render/palette.ts`（8 處改讀）、舊武器畫法刪除、武器小圖示改 ink、`withShadeDir`、`COVERS` 合併（新增 `hair` 旗標）、觸控釘住（沿用 `pinOn: "touch"`）、`ArtTextures.canvas()`、`applyLook`。doll／summon／gear-gallery 前後逐位元相同。合併後 vitest 1097、tsc、build、api 通過。
- 美術 PM 決定（`docs/art/3T-4檢查.md`）：火 `#ff6a1a`、雷 `#fff36b`，`PAL.fire` 也改、全專案只留一個火色；墨線鋼鐵色與材質表保留兩份；`hair` 旗標維持 → **3T-4b**。

### 3.2 3T-4b｜武器小圖示重調＋單一火色（sonnet；約 0.2 段）
1. `PAL.fire` 改 `#ff6a1a`，全專案只留一個火色（搜尋所有 `#ff7a1a`）。
2. 武器小圖示（照 `docs/art/3T-4檢查.md` 第 2 點）：在圖示大小直接用向量畫（不放大點陣圖），墨線寬度除以放大倍率（約 1.2～1.5px）；依武器外框縮放，對角線填滿圖示約 80%；斧、錘、錘矛、鐮刀、杖頭的頭部放大 1.5 倍（柄不變）；錘頭畫成橫的長方塊，和錘矛分開；一律 45° 斜放。
3. 驗收：vitest、tsc、build；前後對照圖 `docs/phases/img/3T-4b-*`（全部武器 kind 一張）。報告 `Phase3T-4b報告.md`。

### 3.3 3T-1、3T-4b 驗收（2026-10-29，開發 PM）
- **3T-1**（報告 `Phase3T-1報告.md`）：`content/modifier_changes.yaml`（change 種類＋載入時雙向檢查）；`skill_primitives.yaml` 參數宣告 `knob`／`knob: none`（coverage 檢查），補 `grant_ap`、`extra_reaction`、`summon.duration`、`zone.duration`、`revive.hp_permille`、`restore_resource`（冷卻）；301 招預算前後逐字相同、CLI 快照不變。待決：change 數值範圍搬 YAML、LLM schema 的 change 欄位 → 4-L8；新旋鈕階梯 → 平衡；`extra_reaction` 只有一階 → 3T-2 改 `knob: none`。
- **3T-4b**（報告 `Phase3T-4b報告.md`）：武器小圖示直接向量畫、45°、頭部 1.5 倍；全專案單一火色 `#ff6a1a`。美術 PM 驗收通過（`docs/art/3T-4b檢查.md`）→ 小修 **3T-4c**。
- 合併後全量（除 llm）：pytest 8550、vitest 1100、mypy、lint-imports、build、重播（oil_depot 種子 21，獸人）全過。

### 3.4 3T-4c｜短武器圖示造型（sonnet；約 0.15 段；照 `docs/art/3T-4b檢查.md`）
只改圖示、不動小人：手槍不斜放（側面 L 形：鋼色槍管橫向朝右約佔寬 70%，木色握把從後端往左下、長約槍管一半）；矛頭、戟斧頭、連枷球放大 1.5 倍（28px 下矛和戟要分得出）；匕首護手改細橫桿（約刀身寬 2 倍）、刀身約佔全長 60%；拳套改正面指虎（鋼色圓角方塊、上緣 4 個指節凸起、下方一個握孔、不要尖刺）；霰彈槍雙管並排、比長槍短約 25%、槍托較寬。驗收：vitest、tsc、build；28px 對照圖 `docs/phases/img/3T-4c-*`。報告 `Phase3T-4c報告.md`。

### 3.5 3T-4c／4d、3T-2 驗收（2026-10-29，開發 PM）
- **3T-4c／4d**（報告 `Phase3T-4c報告.md`、`Phase3T-4d報告.md`）：短武器圖示造型、指虎指節、矛頭 2 倍、霰彈槍托楔形；美術 PM 驗收通過（`docs/art/3T-4c檢查.md`），4d 不需再驗；非圖示模式雜湊測試鎖住小人不變。
- **3T-2**（報告 `Phase3T-2報告.md`）：種族技合法性走全部效果、race／form coverage；`ruleset_hash`＋`log_replay_problem`、`LOG_FORMAT` **`/86`**、變更紀錄搬到 `docs/phases/戰鬥紀錄格式變更.md`；`proposal_forms` → `proposal_layouts`、`PROMPT_VERSION` `skill-proposal/3`；種族 `except KeyError` 移除、`skill_scaling` 必填；誘餌範本／壽命／AI 觸發距離（`ai_trigger_range: 7`）進 races.yaml。待決全部接受（`stack_gain` 吐息例外、無 golden 紀錄、`Ruleset` 欄位增減需遷移）。
- 合併後全量（除 llm）：pytest 8569、vitest 1104、mypy、lint-imports、build、重播（frozen_lake 種子 8，鱗族）全過。
- **3T 必做項完成**；3T-3（拆 `content/skills.py`）與 Phase 4 平行。

### 3.6 3T-5｜AI 施放純地形技能（sonnet；約 0.3 段；3-54e 待決，延後項）
起因：3-54e 報告——效用 AI 對純地形技能（只有隆起／下陷，例如大地崩陷、築高台、陷地術）沒有評分，AI 單位不會主動施放。
1. 效用 AI 加地形改變的評分項（`trpg.engine.ai`）：例如「下陷讓敵人站低處（我方得高處優勢）」「隆起讓我方遠程站高處」「在敵人與我方之間造成高低差阻擋近戰」「挖坑後有推擊技能可以把敵人推進去」；權重放 `content/ai_profiles.yaml`，初值寫進報告。
2. 不讓 AI 濫用：沒有實際收益（例如範圍內沒有單位、高低差不影響任何人）就不施放。
3. 測試：表格測試（有收益／無收益情境 × 隆起／下陷）；一場含大地崩陷的 AI 對戰重播一致；`trpg sim` 小樣本只量（大地 build 的施放次數前後對照，寫進報告，不調數值）。
4. 驗收：pytest（engine、`-m "slow or not slow" tests/cli --timeout=3000`）、ruff、format、mypy；戰鬥快照若因 AI 行為改變而變，逐場說明。報告 `Phase3T-5報告.md`。

### 3.7 3T-3、3T-5 驗收（2026-10-29，開發 PM）
- **3T-3**（報告 `Phase3T-3報告.md`）：`content/skills.py` → `content/skills/` 套件 13 個模組，`__init__` 重新匯出，呼叫端零改動、CLI 快照不變。待決（`skill.py` 1309 行、`constants.py` 812 行再拆）→ 延後。
- **3T-5**（報告 `Phase3T-5報告.md`）：`engine/ai/terrain.py`（降敵、抬友、坑旁推擊三項收益；無收益不施放）；`ai_profiles.yaml` `terrain: {height_points: 4, pit_points: 6}`；小樣本大地崩陷施放 0 → 6。待決：「高低差阻擋近戰」未做、坑判定粗估、權重初值 → 平衡階段。
- **Phase 3T 全部完成**。
