# Phase 3H-3 報告｜技能跟主屬性、營火重配屬性、建議屬性

分支 `worktree-agent-a9173c7a218f4f720`。規格：`docs/phases/Phase3H計畫.md` 第 0、3 節與 5.1 待決 #6；設計 `07-角色成長.md` 7.2、`06-技能.md` 6.10。

## 做了什麼

1. **新技能跟主屬性**（`skillgen/scaling.py` 新模組）：`retarget_scaling(skill, 屬性, library, avoid=None)` 把技能的縮放屬性改成主角最高、且在 `content/skill_scaling.yaml`（3H-1 的 6.10 範圍）允許範圍內的屬性。三個來源都接上：
   - 隨機組合器：`compose_random_skill／compose_with_stats` 新參數 `hero_attributes`、`avoid_attr`；組完才改縮放屬性，**亂數串流與其他內容不變**（沒給時結果與以往完全相同，測試逐欄位比對）。
   - 候選產生器、升級三選一：見下「候選規則」。
   - LLM 提議：`ProposalContext.hero_attributes`；`to_skill_def` 在轉成技能後取代縮放屬性（LLM 填的 `scaling_attr` 只是提議，ID 以取代後的內容雜湊）。`proposal_fallback` 的組合器路徑也帶進去。
2. **升級三選一**（`skillgen/candidates.py`、`roguelite/offers.py`）：`CandidateRequest.hero_attributes`。
3. **營火重配屬性點**（`roguelite/attributes.py` 新模組）：見下「重配」。
4. **建議屬性與「影響哪些招」**（`api/attribute_text.py` 新模組）：由程式依技能與武器的縮放屬性產生；開局畫面、配點畫面、角色面板、營火都顯示。
5. **角色面板常駐數值階數改用有效屬性**（3H-1 待決 #6）：`roguelite.progress.hero_effective_attributes`＝基礎屬性＋裝備屬性詞條，與引擎開戰時同一個算法（`build_gear` ＋ `geared_template`）；一輪的戰鬥之間沒有狀態，所以等於引擎的有效屬性。`HeroOut.attribute_perks` 依它算；面板屬性列顯示有效值並註明「基礎 N，裝備 ±M」。

## 同分順序（確定性）

`trpg.shared.types.top_attribute`（從 `roguelite/start.py` 搬到 shared，原名稱仍可從 `roguelite.start` 匯入）：最高屬性同分時固定取六屬性順序 **力量、敏捷、體質、智力、感知、意志** 的第一個。`pick_scaling_attr`（允許範圍內取最高）用同一個順序。測試：`test_top_attribute_tie_breaks_by_fixed_order`、`test_pick_scaling_attr_respects_allowed_and_order`。範圍取自資料 `skill_scaling.yaml`，沒有新增常數表。

## 候選規則（加深／橋接／新方向並存）

- 種類與關鍵字的規則完全不變（加深 → 橋接 → 新方向，退回規則照舊）。
- `hero_attributes` 有值時多一層「屬性偏好」，**加深與橋接要 `scaling_attr ＝ 最高屬性`，新方向要 `≠ 最高屬性`**：
  - 技能池：先在符合偏好的技能裡抽；沒有就放寬（用偏好以外的技能，不減少候選數）。
  - 組合器：`hero_attributes` 讓技能縮放屬性跟著最高屬性（限允許範圍）；新方向另帶 `avoid_attr`＝最高屬性（取允許範圍內次高）；試完 `composer_tries` 次都不符合時放寬取第一個合格的備選。
- 空的 `hero_attributes` ＝ 與 3H-3 之前完全相同（不新增亂數呼叫、不改偏好）。
- **限制**：6.10 把法術限在主題屬性（火焰法術只能是智力），所以主角最高是意志時，點燃關鍵字的組合器技能仍是智力——這是規格的範圍限制，不是漏洞。

## 重配

- `RunState` 新欄位（皆有預設值，舊存檔可讀，**不升 `trpg-run/N`**）：`attribute_points`（未分配）、`attribute_spent`（分配出去、可退回的點數：開局自由配點＋升級配點＋重配後再分配）。舊存檔沒有 `attribute_spent`，重配只退之後分配的點數。
- 新選擇：`respec_attributes`（只在營火；全部退回、屬性回到基礎、免費、不推進節點）與 `allocate`（把未分配的點分出去，可分批；營火與戰前可用，戰鬥中擋下 409）。最大 HP 隨體質同步調整（沿用升級配點的 `with_hp_change`）。
- 前端：營火畫面的技能點區塊下方多「免費重配屬性點（退回 N 點）」與重配後的分配區（`AttributeRespecSection`）；有未分配點數時戰前畫面也會出現分配區。存檔與重播：一輪從重配後的存檔繼續與直接繼續結果一致（測試）。

## 建議屬性與影響的招（推導）

- 建議主屬性＝`primary_attribute(起始技能, 武器的縮放屬性)`（起始技能最常用的縮放屬性，並列取六屬性順序；沒有技能時用武器的），和「自動配點」同一個規則；原因文字由程式列出：吃它的起始技能名、武器是否也吃它、其他招吃的屬性（可當副屬性）。`POST /api/runs/start-preview` 回 `suggestion` 與 `attribute_affects`。
- 「影響哪些招」：每個屬性底下列出 武器（普攻與武器技吃武器縮放屬性，雙屬性兩個都算）與縮放／第二縮放屬性＝該屬性的技能。開局配點、升級配點、重配分配與角色面板都顯示；`HeroOut.attribute_affects` 用裝備中的技能。

## 測試種子變動

沒有既有測試需要改種子或預期值：`tests/skillgen` ＋ `tests/roguelite`（1037 項）在接上跟主屬性後全過（測試不鎖定具體候選）。`run auto` 的候選會因屬性偏好而不同（升級候選的縮放屬性改變），種子相關結果以量測段為準。唯一需重產的是 OpenAPI、`schema.d.ts`（已重產）。CLI 快照沒有變動（不含新欄位）。`LOG_FORMAT` 不動（沒改戰鬥結算）。

新增測試：`tests/skillgen/test_scaling_follow.py`（同分順序、組合器跟主屬性且其他內容不變、最高屬性改變後新技能跟著變、雙屬性衝突、候選優先同屬性／新方向不同屬性、LLM 提議）、`tests/roguelite/test_attribute_respec.py`（往返、部分分配、驗證、營火限定、體質 HP、存檔往返與續玩一致、舊存檔）、`tests/roguelite/test_offers.py`（升級候選）、`tests/api/test_attribute_text_api.py`（有效屬性含裝備、影響的招、建議屬性、API 重配與戰鬥中擋下）、前端 `attributeAdvice.test.ts`。

## 量測（只量、不調）

- 候選（40 個種子的開局主角，各產一組升級三選一，縮放屬性＝主角最高屬性的個數／40；加深、橋接、新方向）：**關閉 13／6／10 → 開啟 36／10／0**。加深幾乎都跟主屬性（其餘是 6.10 範圍不含該屬性）、新方向 100% 是不同屬性、橋接受關鍵字組合與技能池限制，只小幅提升。候選數量不變（每組仍是 3 個）。
- 完整 `run auto` 勝率對比：每輪約數分鐘，小樣本（8～12 種子）兩次嘗試都跑不完，未取得；請 PM 在模擬階段用 `trpg sim` 補量（本段不調數值）。
- **意外發現（與本段無關）**：量測腳本以 AI 代打整輪時，曾在 `engine/skill_infusion.py:106`（`skill_ban`）撞到 `KeyError: 'refund_ap'`——`skill.iter_effects()` 含 `on_kill` 的 `refund_ap`，但 `rules.primitive_def` 查不到。這是 3-33d 灌注技能的既有缺口（含擊殺返還 AP 的技能被 AI 嘗試灌注時），未動引擎，交 PM 另派修。

## noqa

無新增。

## 實機（內建瀏覽器，8013，已關閉）

- 開局：選斧＋兩個關鍵字，配點區顯示「建議主屬性：力量（你的起始技能 潮斬 吃力量；斧的普攻與武器技也吃力量；其他招吃意志，可當副屬性）」，力量標 ★建議，各屬性下列出影響的招。
- 營火（以 AI 代打存檔載入）：「免費重配屬性點（退回 8 點）」→ 屬性全回 10、階數歸零、出現分配區；加感知 5 點後確認，感知 15、剩 3 點可再分，按鈕變成「退回 5 點」。
- 小問題已修：屬性分配的確認按鈕改名「確認分配屬性點」（避免和技能點的「確認分配」同名）；配點元件不用原生 `title`（`floatCardRule` 檢查）。

## 待 PM 決定

1. **重配是否包含開局的 4 點自由配點**：目前包含（`attribute_spent` 記錄開局配點，重配時一起退回）。若只想退升級得到的點數，改 `new_run／new_keyword_run` 不記 `attribute_spent` 即可。
2. **「主角最高屬性」用基礎屬性（配點）還是有效屬性（含裝備）**：目前用基礎屬性（與專精加成「以基礎屬性判斷」一致、營火重配後立即穩定）；面板常駐數值才用有效屬性。
3. 6.10 的主題限制使法術技常常不能跟主屬性（例：火焰法術一律智力）；若想讓「意志主角」也拿到火焰技，需放寬 `skill_scaling.yaml`（玩法 PM）。
4. 候選的「橋接」在關鍵字組合受限時偏好常放寬（池子小），不算 bug；若要更常見同屬性橋接，需擴內建技能池。
5. 面板「影響」清單在法師身上很長（十招以上），目前不截斷；要不要折疊交 UI 決定。
6. 開發包／回歸範本（`build_id`）開局同樣記錄 `attribute_spent`；模擬不使用重配。
