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
