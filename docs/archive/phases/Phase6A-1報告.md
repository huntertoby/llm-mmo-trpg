# Phase 6A-1 報告：去文字化②，技能卡減字

> 實作者，2026-11-04。規格：`docs/phases/Phase6計畫.md` 第 1 節 6A-1 列；`docs/archive/art/去文字化移植需求.md` 第 1、2、7 節；`docs/art/shots/misc/textless.png` 第 1 組；`docs/archive/art/HUD版面.md` 5.3、5.4。

## 1. 交付內容

### 1.1 伺服器：技能卡的結構化欄位（只加欄位，舊句子不動）

- 新增 `src/trpg/api/skill_cards.py`：
  - `SkillCard`（API 層）＝敘事層的 `trpg.narrative.skills.SkillCard` 加上必填欄位 `stats: SkillCardStats`。
  - `skill_card()` 包住敘事層的同名函式，再補上 `stats`。
- `SkillCardStats` 的欄位：
  - `ap`、`cooldown`；
  - `range`，武器射程時改填 `range_weapon`；`radius`、`size`；
  - `timing`：`reaction`、`trigger`、`delayed`（延遲段與 `delayed_damage`）、`activation`；
  - `costs[]`：`index`、`kind`、`value`、`unit`、`label`，和 `cost` 句子一段對一段；
  - `effects[]`：`index`、`type`、`category`、`label`、`unit`、`dice`、`multiplier_permille`、`weapon`、`amount`、`element`／`element_zh`、`name_zh`、`affects`，和 `effects` 句子一行對一行；
  - `scaling_attrs`。
- 法力和代價句一樣用我方實際會扣的費用（`mana_cost`）。
- API 裡所有回傳技能卡的地方都改用這個型別：
  - `hero_cards`、`/api/skills/{id}`、開局預覽、工坊檢查；
  - 一輪的主角、候選與閃現（`run_presenter`、`run_schemas`）；
  - 大世界（`world_presenter`、`world_schemas`）。
- `trpg.narrative` 沒有修改，引擎、CLI、敘事層的測試都不受影響。
- OpenAPI 已重產（`client/openapi.json`、`client/src/api/schema.d.ts`）。只多了 `stats` 與新的 schema，元件名稱不變，仍是 `SkillCard`。

### 1.2 前端技能卡（`client/src/ui/SkillCardView.tsx`）

- **常駐 3 行**（每行標 `data-testid="skill-card-line"`）：
  1. 名稱。
  2. 一排圖示＋數字：AP 圓點（4 點以上改寫數字）、法力、耐力、HP、源力、每場次數、冷卻、射程（武器射程寫「武器」）、時機圖示（反應、觸發、延遲、啟動）。施放後狀態、透支、維持費、失手反噬用一個「代價」警示圖示，放在最後。
  3. 一行效果數字，加上縮放屬性徽章：
     - 傷害寫骰子，武器技寫倍率，再加元素；
     - 位移寫格數；狀態、表面寫回合與名稱；層數、召喚另外畫圖示；
     - 連打合併成「N 擊」；
     - 沒有數字可以寫的技能（規則改變、刻印等），改放第一句效果，一行，超出省略。
- **每個圖示都有說明卡**（`Hint`），文字都用卡片原本的句子：
  - 代價句；
  - 射程用 `shape`；
  - 時機用 `timing`／`activation`／`followup`；
  - **效果數字滑過會出現效果句＋算式**（`formula_lines` 裡的「傷害／治療／護盾算法」）。
- **標題列不再寫稀有度與類型**：
  - 稀有度改看外框：補上稀有藍框、史詩紫框（傳說的金框原本就有）；
  - 「稀有・主動・…」這一行移進詳細。
- **「▸ 詳細」**用原生 `<details>`：
  - 裡面照舊順序放 6A-1 以前卡片的全部內容，沒有刪任何資訊：稀有度與類型（含稀有度說明）、代價句、源力、形狀、組裝算式、關鍵字、限定武器、條件、時機、啟動、效果句、修正、算式、層數、召喚物、變奏、元素、縮放、專精、設計概念；
  - 內容一直在 DOM 裡，靜態渲染的舊測試照樣過。
- **工坊預設展開**（`CheckPanel` 傳 `detailOpen`）。技能列、三選一、營火、閃現、完整技能（任務獎勵）、開局預覽都共用同一張卡。
- **固定**：
  - 技能列的卡片開著時按 **Shift** 就釘住（`useFloatCard({ shiftPin: true })`）；
  - 卡片右上角有**圖釘**按鈕，可以釘住或取消，觸控也用它；
  - 點卡片本身會釘住（原有行為）。

### 1.3 觸控（開發 PM 定案）

- 新增 `PinMode` `"hold"` 與純邏輯的 `LongPress`（`client/src/ui/floatCard.ts`）：
  - 觸控點一下：只執行動作，不開說明；
  - 長按 400ms：開說明，並且釘住；
  - 長按後放開的那次 click 會在捕獲階段吞掉，不執行動作；
  - 手指移動超過 10px 當成捲動，取消長按；`pointercancel` 也會取消；
  - 長按時擋掉系統選單（`contextmenu`），並加上 `-webkit-touch-callout: none`。
- 套用範圍：
  - 技能列的技能按鈕、道具、種族技、可施放的被動與姿態小圖示，取代以前「點一下釘住技能卡」；
  - `Hint` 包住 `<button>` 時自動用 `"hold"`，因此基本動作按鈕這類「有動作的按鈕」一併改成長按看說明；
  - 沒有動作的元素維持 `pinOn: "touch"`，點一下就開說明。

## 2. 測試

- 後端 `tests/api/test_skill_card_stats_6a1.py`（13 個）：
  - 代表技能的拆解表格：法術火傷 3d6、武器 ×0.4＋推 2 格、表面＋緩速 1 回合、護盾 2d6、破甲印 1 層；
  - AP、冷卻、射程、武器射程、時機、代價種類；
  - 法力是我方實際費用；延遲段的時機；
  - **全部技能**：`stats` 和句子一一對應，而且句子欄位和敘事層完全相同；
  - `/api/skills` 端點有回傳 `stats`。
- 後端 `tests/api/test_client_fixtures.py`：新增 `skillCards.json` 沒有過期的檢查。
- 前端 `client/src/ui/skillCard6a1.test.ts`（17 個）：
  - 第 2 行、第 3 行的內容；
  - 舊快照沒有 `stats` 時退回只顯示句子；
  - 詳細外面剛好 3 行；標題沒有稀有度；詳細裡資訊都在；
  - 詳細預設收合，工坊預設展開；
  - 圖釘與「Shift 固定」；
  - 長按判定：點一下、長按、移動取消、cancel，以及 Hint 對按鈕和非按鈕的模式。
- 執行結果：
  - 相關 API 測試 22 個檔共 187 個，加上新測試與 fixtures 檢查，全部通過。過程中 OpenAPI 快照失敗過一次，重產後通過。
  - vitest 跑 `src/ui`、`src/run`、`src/workshop`、`src/screens`、`src/dev` 與 `skillTray`，37 個檔 303 個全部通過。
  - `ruff check`、`ruff format --check`、`mypy src`（494 個檔）、`lint-imports`（13 個契約）、`tsc --noEmit`、`corepack pnpm -C client build` 全部通過。
- 沒有跑全量測試與模擬，照規定。

### 前端 fixture 的變化

- **新增** `client/src/ui/fixtures/skillCards.json`：6 個代表技能的真實 API 回應，含 `stats`。
  - 由 `scripts/export_client_fixtures.py` 產生（腳本加了這一項），並由 `test_client_fixtures.py` 檢查有沒有過期。
  - 技能文字或數值改動時要重產：`uv run python scripts/export_client_fixtures.py`。
- 既有的 run fixture（`run_*.json`、`vfx_random_skills.json`）**沒有重產**，裡面沒有 `stats`。
  - 卡片用 `cardStats()` 退回：第 2、3 行空白或只放第一句，詳細照常顯示。
  - 現有測試不用改，也全部通過。
- `skill_icon` fixture 沒有變化，不需要重產。

## 3. 截圖（`docs/art/`）

- `6a1_battle_collapsed.jpg`（800×600）：戰鬥中滑過「火焰爆」：
  - 第 1 行：名稱；
  - 第 2 行：AP 兩點、法力 5、冷卻 1、射程 4；
  - 第 3 行：1d12 火焰、智力；
  - 下方是「▸ 詳細」與「Shift 固定」。
- `6a1_battle_expanded.jpg`（800×600）：同一張卡釘住、詳細展開，可以看到稀有・主動・範圍・法術技、代價句、組裝算式、關鍵字、效果句、傷害算法。
- `6a1_offer.jpg`（785×600）：升級三選一的候選卡（開發入口 `?dev=1&screen=level_up`）。
  - 寬度只有 785，因為內建瀏覽器的截圖把右側捲軸裁掉了。
- 瀏覽器實測：
  - 效果數字滑過會出現「1d12＋智力加成的火焰傷害（敵方）／傷害算法：骰值＋智力 × 0.5（目前 +7）」；
  - Shift keydown 會把卡片釘住。

## 4. 待 PM 決定（都已照最保守的做法完成）

1. **結構化欄位放在 API 層**：
   - 限制寫「只動 `src/trpg/api/`」，所以沒有改 `trpg.narrative.skills.SkillCard`，而是在 API 層繼承並加上 `stats`；
   - 以後若要讓 CLI 或其他層也用這些欄位，可以把它搬進敘事層。
2. **傷害數字寫骰子或倍率**，不寫算好的期望值。樣張的「24」是示意，寫期望值等於另外訂一套計算方式。目前的實際加成在滑過說明的算式裡（「目前 +7」）。要不要改成「平均＋目前加成」，請決定。
3. **第 2 行也放法力、耐力**：樣張只有 AP、冷卻、射程、時機，但我把法力、耐力、HP、源力、每場次數也放進來，避免最常看的費用被收進詳細。施放後狀態這類代價只畫一個警示圖示。
4. **閃現資訊維持常駐**：營火與閃現畫面的「已閃 N／5 次」（`SkillFlashInfo`）是那個畫面的主角，所以放在第 3 行下面，沒有收進詳細。
5. **Hint 自動判斷**：凡是包住 `<button>` 的 `Hint`，觸控都改成長按看說明，不只技能列。規格寫的是技能列、功能列，但「有動作的按鈕」的原則是一樣的。如果要縮小範圍，加一個參數即可。
6. **縮放屬性圖示**是圓形徽章，裡面寫屬性的第一個字（力、敏、智…）。目前沒有正式的屬性圖示，請美術 PM 決定要不要另外畫。
7. **非緊湊卡的大圖示**從 72px 改成 56px，照樣張；技能列的緊湊卡維持 48px。
8. **舊 fixture**：run 的 fixture 沒有 `stats`，前端有退回處理。要不要重產這些 fixture，請決定。

## 5. Commit

- `179bb485` feat(api): structured skill card stats (6A-1)
- `024bfd4e` feat(client): three-line skill cards with detail fold and long-press hints (6A-1)
- 報告與截圖：最後一個 commit
