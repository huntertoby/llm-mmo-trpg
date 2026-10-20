# Phase 3F-3b 報告：複合技能的 AI、技能工坊、戰鬥網頁

> 規格：`docs/phases/Phase3F計畫.md` 0.3、3.4、3.5（3F-3b）；設計：`docs/design/06-技能.md` 6.23。3F-4（其他 5 種複合技能）沒有做。

## 1. commit

| commit | 內容 |
|---|---|
| f8dda24 | AI 使用複合技能（`engine/ai/composite.py`）；新示範技能「躍擊震地」`skill_leap_slam`；`tests/engine/test_composite_ai.py`（4）。（這個 commit 的訊息寫「equip both in build_charger」是中間狀態，最後的裝備方式以 eb7562b 為準） |
| 3cfb2e5 | 工坊後端：新增步驟 `followup`（動作段），`skillgen/option_followup.py`、`draft_check`／`draft` 配合；OpenAPI 與 `schema.d.ts` 重新產生；`tests/skillgen/test_workshop_followup.py`（6） |
| 24f7799 | 前端：工坊動作段步驟、兩段預算明細、戰鬥網頁兩段選取與預覽（`battle/composite.ts`、`targeting.ts`、`ActionPanel`、紫色動作段範圍）；vitest 15 個；API 試玩測試（`test_workshop_api.py` 2 個） |
| eb7562b | 最後的裝備：瞬影旋斬進 build_charger（換下颶風踢）、躍擊震地進 build_push（換下盾擊）；`hero_fighter` 不再裝瞬影旋斬；修正 `test_coverage`、衝鋒流自身位移、matrix 測試與 CLI 快照 |
| （本報告） | 報告 |

沒有 stash、reset、amend、切換分支，沒有 push。`LOG_FORMAT` 維持 `/34`（沒有新欄位或事件）。

## 2. 交付項目

### 2.1 AI（3.4、0.3 #8）

- `UtilityAI._skill_candidates` 不再略過複合技能；`skill_estimate` 對複合技能走 `composite_estimate`（`engine/ai/composite.py`）：影響範圍（兩段聯集）內的敵人數 ×3、誤傷友方 −3、範圍內沒有敵人就不納入；平手以動作段原點離施放者的距離判定。
- **上限（0.3 #8）**：沿用每個技能的 `skill_candidates`（`ai_profiles.yaml`，初值 3）。`legal_actions` 列出的組合（傳送接錐形空曠地約 150 個）只做便宜的估計（不跑引擎），每個複合技能只保留估計最高的前 3 個選取跑完整 `preview`，所以完整預覽的次數是固定的。落點的安全性與位置價值由 `preview` 的收益決定（已含落點）。
- 驗證：`trpg sim maps --seeds 5 --ally-build build_charger`（10 張地圖、50 場，12.7 秒，異常：無）：**每張地圖都有「瞬影旋斬」的使用紀錄**（0.8–1.8 次／場，命中率 29%–86%）。另跑 `trpg sim maps --seeds 5 --ally-build build_push`：「躍擊震地」在 9 張地圖有使用紀錄（0.2–0.8 次／場，命中率 0%–100%；bridge_chasm 沒用到）。

```text
地圖            瞬影旋斬 次／場  命中率  平均傷害／次
bridge_chasm     1.00   80.0%   2.4        dark_forest   1.80  50.0%  4.2
cliff_outpost    1.20   75.0%   4.8        oil_depot     1.20  71.4%  7.0
frozen_lake      1.00   75.0%   6.0        open_plain    1.00  85.7%  7.0
lava_crossing    1.00   77.8%   5.2        ruined_fort   1.20  28.6%  1.0
narrow_halls     0.80   50.0%   3.0        swamp         1.20  53.8%  5.2
```

- 測試：`test_the_ai_teleports_next_to_distant_foes_and_cuts_them`、`test_the_ai_uses_a_centered_followup_around_the_landing`、`test_the_number_of_previewed_composite_candidates_is_capped`、`test_the_ai_ignores_composites_when_no_foe_would_be_hit`。

### 2.2 示範技能與 build

| 技能 | 內容 | 預算 | 裝在 |
|---|---|---|---|
| 瞬影旋斬（3F-3a） | 傳送 4 格 → 錐形 2 武器 ×0.9 | 84.9% | **build_charger，換下「颶風踢」**（颶風踢仍在 build_push 等） |
| **躍擊震地**（本段新增，稀有、階級 2） | 跳躍 3 格 → 以落點為中心的十字：武器 ×0.6 ＋ 擊倒；AP 2、法力 6、冷卻 3 | 位移段 3.00 ＋ 動作段 14.26（area ＋ displace 協同 ×1.1），×1.15 ＝ 19.84 ÷ 21.24 ＝ **93.4% 合格** | **build_push，換下「盾擊」**（盾擊仍由敵方盾兵使用） |

- 為什麼不照 3F-3a 建議換下 `guard_swap`：衝鋒流的 AI 測試（`test_the_ai_uses_every_self_move_somewhere`）要求 dash、leap、swap 三種都出現，換掉護衛換位會讓 `skill_guard_swap` 變成沒人裝備（`test_coverage`）。換下的兩招（颶風踢、盾擊）別的 build／敵人仍有裝備。
- `hero_fighter` 的瞬影旋斬拿掉了（AI 會用後會改變預設主角的戰鬥，並讓示範地圖測試失敗；改裝在 build）。

### 2.3 工坊後端（3.4）

- 新步驟 `followup`（`StepId`、`STEP_IDS` 在「效果」與「條件」之間）。**只有位移技能才出現**（骨架 `displace`、主動、效果恰好一個自身位移原語）；草稿已有 `followup` 時也保留（讓使用者能移除）。不能接動作段的技能完全看不到這一步（`missing_steps` 也不列）。
- 欄位用點號路徑（和 `cost.mana` 一樣），一步步展開：
  1. `followup.skeleton`「接一個動作段」（選填；**不選＝普通位移技能**）：啟用的主動骨架、至少有一個合用形狀與核心原語者（略過必須有條件的骨架，因為動作段條件工坊先不開放）。
  2. `followup.shape`（選了骨架後）：骨架的形狀 ∩ `FOLLOWUP_SHAPES`；十字與方陣的射程固定 0。
  3. `followup.effects`（選了形狀後）：用動作段的骨架與形狀當作一個獨立技能，呼叫同一個 `_effect_choices` 試組，再濾掉 `FOLLOWUP_FORBIDDEN`；數量上限 ＝ 稀有度效果上限 − 1（位移段佔 1 個）。
- 所有規則仍在 `trpg.content`／`trpg.skillgen`（`FOLLOWUP_*`、驗證器、預算）；新檔 `skillgen/option_followup.py` 只組裝選項。
- 檢查（`check_draft`）原本就支援兩段（3F-3a）：`budget.segments`、`composite_tax_permille`、稀有度原因。
- 測試（`tests/skillgen/test_workshop_followup.py`、`tests/api/test_workshop_api.py`）：步驟只在位移技能出現、可略過、欄位依序展開（含十字射程固定 0、效果上限 3）、一步步組出瞬移 → 錐形與跳躍 → 十字都合法且兩段明細／稀有度正確、與內容庫示範技能預算相同、普通稀有度被擋、殘留的動作段仍可見；API：選項、檢查（兩段明細、技能卡片 `followup`）、裝上試玩並施放（`skill_followup` 事件）。

### 2.4 工坊網頁（3.4）

- 步驟列多一個「動作段」（可省略，有提示；不是位移技能時不顯示）。「接一個動作段」旁有「不使用」可移除整個第二段；換動作段骨架會清掉已選的形狀與效果（`draft.ts`）。
- 檢查面板的「點數明細」：複合技能分「位移段」「動作段」兩個表（各自骨架、形狀、效果點數、條件、協同），最後一行寫「兩段加總 × (1000 ＋ 150‰) ÷ 1000」。
- vitest：`workshop/followup.test.ts`（點號路徑寫入草稿、換骨架清除、不使用、步驟名稱、預覽標記與文字）。

### 2.5 戰鬥網頁（3.4）

- 技能卡片有第二段（`card.followup`）的技能，選取改為兩段（`battle/composite.ts`，沿用既有「兩段選取」的流程與 `hurlPick` 狀態）：
  - 第 1 段（位移）：高亮所有合法落點格（傳送、跳躍、衝撞）或目標單位（衝鋒、瞬步）；點一下選定（青色粗框）。
  - 第 2 段（動作）：方向型形狀（錐形、直線）在落點四周標出黃色方向箭頭，點箭頭格即施放；單體點目標；也可用面板上的按鈕（北東南西、攻擊某單位）——滑過按鈕會預覽。「重選落點」或再點別的落點可改選。
  - **以落點為中心的形狀（十字、方陣）只有一種第二段：點落點一次就施放**（滑過落點就預覽）。
  - 衝鋒／瞬步以單位為第 1 段時，落點在伺服器計算，所以第 2 段只能用面板按鈕（戰場上不標方向格）。
- 預覽：同時顯示位移的落點標記（「落」「躍」……）、整個影響範圍（橘色），**第二段範圍用紫色**，預覽文字多一行「第二段：位移到 (x, y) 後，以落點為原點影響 N 格（紫色）…」；命中率、傷害沿用既有預覽（伺服器已算好兩段）。
- vitest：`battle/composite.test.ts`（分組、第 1 段高亮與選取不產生動作、第 2 段方向格與點擊、面板按鈕、以落點為中心一次點擊、衝向單位、技能列標記）。

## 3. 驗收條件逐條（3.5，3F-3b）

| # | 條件 | 結果與證據 |
|---|---|---|
| 1 | AI 在 `trpg sim maps --seeds 5` 中有使用複合技能的紀錄 | 通過。`uv run trpg sim maps --seeds 5 --ally-build build_charger`：10 張地圖都有 `skill_shadow_whirl` 使用紀錄（2.1 表），異常：無；測試 `tests/engine/test_composite_ai.py`；重播：`test_a_battle_with_a_composite_cast_replays_exactly`（現在用 build_charger，AI 之外手動施放一次） |
| 2 | 工坊能組出「瞬移 → 錐形打擊」並通過檢查；PM 用瀏覽器在靶場施放一次 | 後端與 API 通過：`test_the_workshop_builds_teleport_then_cone_through_the_api`、`test_try_out_teleport_then_cone_and_cast_it`（裝上試玩到靶場並施放，事件有 `skill_followup`）、`test_walking_teleport_then_cone_builds_a_legal_composite`、`test_the_leap_then_cross_slam_walks_to_a_legal_skill`。**瀏覽器施放由 PM 驗收**（步驟見第 6 節） |
| 3 | vitest；`check.py` 全過 | 通過。vitest 206 個（3F-3a 為 191，新增 15）；`check.py`（HEAD 05f6829）全部通過，pytest 3095 個（3F-3a 為 3082） |

## 4. 修改既有測試與快照的原因

| 檔案 | 原因 |
|---|---|
| `tests/engine/test_composite_skills.py` | 刪除 `test_the_ai_does_not_pick_composites_and_does_not_crash`（AI 現在會用，改由 `test_composite_ai.py` 測）；`test_the_demo_skill_is_valid_and_equipped` 改查 build（charger 有瞬影旋斬、push 有躍擊震地）；重播測試改用 `build_charger`（`hero_fighter` 不再有這個技能） |
| `tests/api/test_composite_api.py` | 瞬影旋斬已在 build_charger，不再「裝上試玩」替換 |
| `tests/cli/test_budget_cli.py` | 技能數 142 → 143（躍擊震地） |
| `tests/cli/snapshots/cli_output_hashes.json` | 重錄：`skills_list`、`skills_show_all`（新增技能）；`battle_frozen_lake_push_3`（build_push 的 AI 現在會用躍擊震地）。其餘 6 場戰鬥快照不變 |
| `tests/api/test_workshop_api.py` | build_charger 不再有颶風踢，試玩時改替換「蠻牛衝陣」（`skill_bull_rush`） |
| `tests/sim/test_matrix.py` | build_push 的第二個技能由盾擊變成躍擊震地 |

## 5. 新增的複雜度 noqa

**沒有新增** C901、PLR0911、PLR0912、PLR0915。

## 6. PM 瀏覽器驗收步驟

先 `corepack pnpm -C client build`（已建置過）再 `uv run trpg serve`，開 http://127.0.0.1:8000/（**若 8000 埠有舊程序，先關掉**，否則會看到舊版）。

### 6.1 在工坊組「瞬移 → 錐形打擊」

1. 首頁「進入技能工坊」→ **骨架**點「位移」→ 下一步。
2. **基本設定**：名稱「瞬移斬」；AP 2；類別「武器技」→ 武器需求「近戰武器」；縮放屬性「力量」；階級 1 → 下一步。
3. **形狀**：點「指定格」（`ground_tile`），射程 4 → 下一步。
4. **效果**：新增效果點「傳送」→ 下一步。
5. 現在步驟列多了 **「動作段」**：「接一個動作段」點骨架卡片「範圍」→ 出現「動作段的形狀」點「錐形」，大小 2 → 出現「動作段的效果」點「傷害」，倍率填 900（武器 ×0.9）→ 下一步。（想看普通位移技能就不選骨架，或按「不使用」。）
6. **條件**不用選 → **代價**：法力 6、冷卻 3 → **稀有度**點「稀有」。
7. 右側「即時檢查」應顯示「合法」、`84.9%・合格`；展開「點數明細」可看到「位移段」「動作段」兩個表，最後一行是 ×(1000＋150‰)。把稀有度改「普通」會出現 `rarity.composite` 違規。
8. 「裝上試玩」：主角 build「衝鋒流」、要換掉「調虎離山」、地圖「靶場」、對手「木樁」→ 按「裝上試玩」。（衝鋒流已經有瞬影旋斬；用工坊自己的技能試玩要換掉一招。）
9. 進入戰鬥：先走向木樁（走到距離木樁約 4 格內），技能列第一個是你的「瞬移斬」→ 點它：
   - **第 1 段**：高亮出傳送的合法落點格（紅框）；滑過去什麼都不會預覽；**點一個落點**（青色粗框選定）。
   - **第 2 段**：落點四周出現黃色方向箭頭（東南西北都會列，錐形不要求方向上有敵人）；**滑過箭頭格**或右側面板的「→ 向東」等按鈕，預覽會顯示傳送落點與**紫色錐形範圍**、命中率與傷害；**點箭頭格**即施放。
   - 戰鬥紀錄應出現「施放」「被傳送到」「接著施展第二段」「攻擊……」。

### 6.2 在靶場兩段選取（內建示範技能）

- 靶場只能從工坊進入：工坊「裝上試玩」面板選 build「衝鋒流」（內建瞬影旋斬）或「位移流」（內建躍擊震地）、地圖「靶場」、對手「木樁」。試玩的自訂技能不是必須的：隨便組一個合法技能裝上去，內建的複合技能仍在技能列。也可以用首頁一般戰鬥的我方 build 選單選這兩個 build：
  - **瞬影旋斬**（衝鋒流，傳送 → 錐形）：和 6.1 第 9 點相同的兩段操作。
  - **躍擊震地**（位移流，跳躍 → 十字震地擊倒）：點技能 → 戰場高亮 3 格內可跳的空格 → **點一格就施放**（以落點為中心的十字只有一種第二段）；滑過落點可以先看預覽（紫色十字、擊倒機率）。
- Esc／右鍵取消選取；第 2 段按「重選落點」回到第 1 段。

## 7. 檢查結果

- `uv run python scripts/check.py`（HEAD 05f6829）：ruff check、ruff format --check、mypy、lint-imports、pytest（**3095** 個）、client install／typecheck、vitest（**206** 個）全部通過——「全部檢查通過。」
- 第一次完整執行曾失敗 2 個（`test_coverage` 與衝鋒流自身位移測試），原因是把瞬影旋斬換下護衛換位／躍擊震地換下騰躍，已改為第 2.2 節的裝備方式；第二次失敗 2 個（`test_workshop_api` 試玩時替換颶風踢），已修正測試。
- `corepack pnpm -C client build`：成功（只有 chunk 大於 500 kB 的既有警告）。
- `uv run trpg sim maps --seeds 5 --ally-build build_charger`：見 2.1。

## 8. 待 PM 決定（最多 10 點）

1. **換下哪一招**：瞬影旋斬換下 build_charger 的「颶風踢」（不是 3F-3a 建議的護衛換位，原因見 2.2）；躍擊震地換下 build_push 的「盾擊」。兩個 build 的平衡未模擬，只確認 AI 會用。
2. **AI 估計很簡單**：只看兩段聯集內的敵人數與誤傷，落點危險度由預覽的位置價值決定；沒有針對「落點被包圍」特別處理。要更強需要看模擬數據。
3. **AI 上限沿用 `skill_candidates`（3）**：未另設複合技能專屬上限；`legal_actions` 本身仍會列出全部組合（約 150 個，只做便宜估計）。
4. **工坊動作段不支援條件**：`followup.condition` 沒有欄位，也略過「必須有條件」的骨架（例如部分骨架）；schema 本身允許，需要時再開。
5. **動作段骨架可選任何有合用形狀的主動骨架**（含 `displace`、`aura` 等）；有些組合沒有實際意義（例如動作段再選位移骨架但效果不能是位移），目前由檢查與效果清單自然限制，未另外排除。
6. **衝鋒／瞬步的第 2 段只能用面板按鈕**（落點由伺服器算，戰場上不標方向格）；`shadowstep` 的「自選落點」模式需要先選單位再選落點，複合技能的網頁選取沒有特別處理（以落點格為第 1 段，單位不分）。
7. **以落點為中心的複合技能點一次就施放**（沒有確認步驟，但滑過可預覽）；若希望一律兩步（先選落點、再按「施放」），改 `soleCenter` 一處即可。
8. **紫色表示第二段範圍**，橘色仍是整體範圍（兩者重疊處顯示紫色）；沒有新增圖例。
9. **躍擊震地平衡**：擊倒＋十字＋區域的協同加成（area ＋ displace ×1.1）使動作段偏貴，因此階級 2、傷害 ×0.6；build_push 的模擬使用率 0.2–0.8 次／場、命中率差異大，數值待 PM 看過再調。
10. **`LOG_FORMAT` 維持 `/34`**（本段沒有新欄位）；`build_charger`／`build_push` 的內容改動只影響新建立的戰鬥，舊紀錄的 setup 自帶範本，不受影響。
