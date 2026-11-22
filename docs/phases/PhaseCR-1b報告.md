# Phase CR-1b 報告｜暴擊顯示收尾＋兩個不穩的 wish 測試

實作者，2026-11-23。規格 `docs/phases/PhaseCR-1b計畫.md`，基準 main `472c15ea6`。

## 1. Commit

| commit | 內容 |
|---|---|
| `93263eb29` | 第 1 項：預覽「暴擊率 15%」「擲出 19–20 暴擊・暴擊傷害 250%」（200% 不寫「・暴擊傷害」）；技能卡「暴擊範圍 19–20，暴擊傷害 250%」 |
| `42a687610` | 第 2 項：角色面板（單位卡）的暴擊傷害與來源 |
| `840799c3f` | 第 3 項：目標浮動卡避開預覽面板 |
| `a4d246b62` | 第 3 項追加（開發 PM 轉美術 E3b 驗收小修 1）：走路預覽的預覽牌不蓋住單位 |
| `854950ddd` | 追加（開發 PM 轉 8.29 E3，玩法 a57d75120）：霜行留下的表面不是冰時，說明拿掉「不會變成水」 |
| `2ad6a5e1e` | 第 4 項：兩個 wish 測試改成不靠牆上時間的等法 |
| `33314e744` | 截圖 `docs/art/shots/cr-1b/`（6 張） |
| `aba95be44` | `git merge --no-edit main`（只帶進 `docs/art/E3b驗收.md`） |

## 2. 做法

### 2.1 預覽與技能卡的用字（第 1 項，5.4.2 第 8 點）

- 機率那行：`client/src/battle/previewText.ts` 的「暴擊 15%」→「暴擊率 15%」。測試模式拆段的正規式（`ActionPanel.tsx` 的 `HEAD_PART`）跟著改成「暴擊率」。
- 範圍與倍率那行：`engine/rules/combat.crit_text_zh` 改成「擲出 19–20 暴擊・暴擊傷害 250%」（自然 20 時「擲出 20 暴擊・…」）；倍率 200% 時只寫「擲出 19–20 暴擊」。**出現時機照舊**（`preview._crit_notes`：倍率不是 200% 才出現），所以 200% 時這行仍不出現。
- 新增 `combat.crit_damage_text_zh(permille)`＝「暴擊傷害 250%」，技能卡與角色面板共用。
- 技能卡（`narrative/skills._damage_parts`）：原本 CR-1 的「暴擊 19–20・250%」拆成兩段：有自帶範圍時照改版前寫「暴擊範圍 19–20」，有自帶倍率時另寫「暴擊傷害 250%」（例：「…（敵方），暴擊範圍 19–20，暴擊傷害 250%」）。只帶倍率不帶範圍時只寫「暴擊傷害 250%」。**範圍的寫法採最保守**：沿用改版前技能卡的「暴擊範圍 N–20」，不改成預覽的「擲出 N–20 暴擊」（見待決 1）。
- 預算說明（工坊內部用的「暴擊 17–20・250% ×1.1575」）不改，442 招逐招預算才能逐位相同。

### 2.2 角色面板的暴擊傷害（第 2 項，佇列 (v)）

「角色面板」取戰鬥中的單位卡（`ui/UnitInfo.tsx`，E3b 的種族列「角色面板「▸ 詳細」的種族列」也在這裡）。

- **後端算、和引擎共用**：`engine/crit_damage.py` 拆出 `_raw_sources`（武器基礎、裝備詞條、種族、修正技、技能自帶各一個數字），`crit_damage_permille` 改成「`_raw_sources` 相加再套上下限」，結算數字完全不變（78 場 different=0）。新的 `crit_damage_breakdown` 用同一個 `_raw_sources`，所以面板倍率和結算倍率一定相同；只是多列出來源。修正技拆成每招一項用新的 `modifiers.crit_damage_bonus_parts`（只給顯示用；每招各自捨去，加起來最多可能和合計差 1‰，最後倍率仍用合計）。
- **面板用的參數**：主手武器普攻（`use=modifiers.ATTACK`、`skill=None`，形態中是天生武器，同結算）；沒有目標，`subject=Subject(None, 自己的格子)`，所以看目標的修正技條件不算，只算不看目標的（見待決 3）。技能自帶倍率不算進面板。
- **視圖欄位**：`UnitView.crit_damage_permille`（‰，套完上下限）、`crit_damage_detail_zh`（來源文字）。OpenAPI 與 `schema.d.ts` 重產。
- **來源文字**（`crit_damage.crit_damage_detail_zh`）：「武器「匕首」250%・詞條 +10%・種族 +25%・修正技「暴擊專精」+25%（全身上限 300%）」；被截時最後改寫「・頂到上限 300%」或「・最低 150%」（不再加括號那段）。是 0 的來源不列；武器一定列。裝備的規則改變（`skill_gear_*` 包裝）掛的修正寫「詞條「〇〇」」。
- **前端**：數值區（圖示列下面）一行「暴擊傷害 260%」（`data-testid="unit-crit-damage"`，200% 也顯示）；「▸ 詳細」表格多一列「暴擊傷害｜來源文字」，放在武器特性後面。前端只排版（`battle/critDamage.ts`），不重算。
- **守則 14（誰在看）**：照現有數值的做法——
  - 單位卡上武器名、武器特性、裝備加成對敵我都顯示，所以暴擊傷害也對所有看得到資訊的單位顯示；
  - 隱蔽中、看不到資訊的敵人（`hidden_info`）兩個欄位都送 `null`（`api/hidden_info._masked_unit`），前端不畫。理由：修正技的條件可能看自己的狀態，跟狀態一起藏；
  - 其他陣營的單位不寫修正技的技能名（敵人的技能清單本來就不給，`skills=()`），合併成「修正技 +N%」。

### 2.3 浮動卡避開預覽面板（第 3 項，佇列 (w)）

- `ui/hoverCard.avoidPanel`（純函式）：卡片先照原本的位置夾進可見範圍；沒碰到預覽面板（`.mode-panel`）就不動——**1600 寬位置不變**（實測 537,356，和 CR-1 截圖相同）。碰到時依序試：目標格的另一邊（原本在左就改右）→ 目標格上方 → 下方（上下兩個水平置中對齊目標、夾進畫面）；試的位置要整個在可見範圍內、不碰面板。都放不下時照原位，卡片加 `under-panel`（`z-index: 11`，在左欄 13、舊版面 `.mode-panel` 12 之下），預覽面板放上層。
- `HoverFloat` 多一個 `tile` 參數（目標格方框，`stageLayout.tileBox`），`BattleScreen` 傳入；縮放列的避讓（`avoidRect`）照舊在最後。
- 800 寬實測：面板 8～238，卡片從目標左邊改到右邊（440～710），預覽整段沒被蓋。

### 2.4 走路預覽的預覽牌不蓋住單位（追加，美術 E3b 驗收小修 1）

- `render/pathArt.placeTags` 多一個 `units`（有單位的格子頂面左上角，巨型單位每一格都算）。單位的範圍＝格子往上多半格（頭）（`unitBox`）。
- 有給單位時依序試：停點右邊（原本的位置）→ 上方（停點頭上，置中）→ 左邊 → 下方（置中）；都會蓋到時選蓋到面積最少的那一個。和驚嘆號、其他小牌不疊的規則照舊；沒給單位時和改前逐位相同。
- `HighlightLayer.drawPath` 把 `model.units` 傳進去，縮放重排（`pathTagRescale`）也帶著。
- 霜行 800 寬補拍：預覽牌改擺到停點下方，兩個敵人都露出來。

### 2.5 霜行非冰表面的說明（追加，8.29 E3）

`client/src/battle/tileInfo.trailSurfaceLine`：不是冰時寫「〇〇沿路留下的火焰：剩 2 回合，到期直接消失。」；冰照舊「…到期直接消失，不會變成水。〇〇自己踩不會滑倒，其他人照一般冰檢定。」。（開發 PM 說位置在 narrative/tile_info，實際在前端 `tileInfo.ts`，E3b 做在這裡。）

### 2.6 兩個不穩的 wish 測試（第 4 項，佇列 (x)）

- **在等什麼**：文字許願要 `WorldPregen` 的背景執行緒（單一佇列、一次一筆）跑 Mock 的許願生成（對關鍵字＋提議器出三選一，含技能驗證與預算）。供應者（`supplier`）與等待提示（`wait`）都用 `_await`：每 0.25 秒 `concurrent.futures.wait` 一次，直到 `Future` 做完或 `clock()` 超過「最多等 10 秒」（`content/skill_pick.yaml` 的 `pregen.wait_seconds`）。負載下 Mock 生成本身超過 10 秒，`_await` 逾時回 `None`：`test_wish_pregen` 拿不到紀錄（許願被拒），`test_wish_api_wp2` 的等待提示回 `timeout`。另外 API 那題開場的預測（閃現、機遇）也排在同一條佇列，許願雖然插隊，但正在跑的那一筆要先做完。
- **改法**：只改測試，把 `WorldPregen.clock` 換成不走的時鐘（固定回 0）。「10 秒」永遠不到，等待改成等背景那一筆的 `Future` 做完（事件），不靠牆上時間；`_await` 的流程、產品的等待上限都不變。`test_wish_pregen` 在建構時傳 `clock=_frozen_clock`；`test_wish_api_wp2` 在送等待提示前把 app 的 `store.pregen.clock` 換掉。
- 沒有放寬任何逾時。萬一生成卡死，由 pytest-timeout（300 秒）與看門狗接手。

## 3. 驗收

### 3.1 結果不變（different=0）

基準 `472c15ea6`（`git archive` 的 `src`、`content`、`config`、`scripts`）；新版是全部程式 commit 之後的工作區（`2ad6a5e1e`）。腳本沿用 CR-1 的 `compare78.py`、`budget.py`、`census_cmp.py`（暫存區 `cr1b/`）。

| 比對 | 結果 |
|---|---|
| 442 招逐招預算（`BudgetReport` repr＋`validate_skill`） | 442 招，`cmp` 0（逐位相同） |
| census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`，不看計時） | `cells=204 different=0 whole_equal=True` |
| 78 場（`compare78.py`，a 段那組；`format` 也比） | `battles=78 events=26741 different=0`；內嵌規則包差異 0 |
| CLI 快照（slow） | 見 3.3 |

`LOG_FORMAT` 不升版（沒有新事件欄位，`UnitView` 的新欄位不進戰鬥紀錄）；測試裡沒有寫死版號。

### 3.2 新增與改的測試

| 驗收條件 | 測試 |
|---|---|
| 預覽兩行用字（200% 與 250%） | `tests/engine/test_crit_display_cr1.py`：`test_the_text_format`（250%、150%、225%、自然 20）、`test_two_hundred_percent_drops_the_multiplier_part`、`test_the_attack_preview_shows_a_non_default_multiplier`、`test_the_preview_says_nothing_at_two_hundred_percent`、`test_the_skill_preview_shows_the_skill_multiplier`；前端 `client/src/battle/previewText.test.ts`（「暴擊率 5%」）、`pr2bPractice.test.ts`（測試模式拆段） |
| 技能卡 | `test_crit_display_cr1.py::test_the_skill_card_shows_the_skill_multiplier`（範圍＋倍率、只有倍率、都沒有） |
| 角色面板：沒截到、頂到上限、最低、來源列 | `tests/engine/test_crit_panel_cr1b.py`（8 題：200% 也顯示、設計例子 260%、頂到上限、最低、和結算同一個數字、技能自帶不算進面板、其他陣營不寫技能名、隱蔽中的單位藏起來）；前端 `client/src/ui/critDamagePanel.test.ts`（三種情況的數值區與「▸ 詳細」、null 與舊回應不畫） |
| 浮動卡擺放（800、1600、各種放不下） | `client/src/ui/avoidPanel.test.ts`（改右邊、改上方、改下方、全放不下 → under、原本在右改左、沒面板不動、1600 不動、接線） |
| 預覽牌避開單位 | `client/src/render/cr1bPathTagUnits.test.ts`（沒單位照舊、右邊沒人不動、霜行那一幕改上方、→ 左、→ 下、都會蓋到選最少、接線） |
| 霜行非冰說明 | `client/src/battle/tileInfoTrail.test.ts`（火：只寫「到期直接消失。」；冰照舊） |
| wish 兩題 -n 8 連跑 20 次 | 見下 |

**wish 連跑**：指令（暫存區 `cr1b/wish20.sh`，每次兩個整檔一起跑，18 題）：

```
uv run python scripts/run_pytest.py -q -n 8 tests/api/test_wish_pregen.py tests/api/test_wish_api_wp2.py   # 重複 20 次
```

結果 20/20 結束碼 0（`fails=0`），每次 18 passed，耗時 23～99 秒（第 1 次 99 秒是冷啟動，同時另有 vitest 在跑）。

### 3.3 檢查指令

| 指令 | 結束碼 |
|---|---|
| `uv run ruff check .`、`ruff format --check .`、`mypy`、`lint-imports`（每個 commit 前） | 0 |
| `uv run trpg content check` | 0 |
| `uv run python scripts/hardcoded/classify.py --check` | 0（沒歸類 0；清單沒變） |
| `corepack pnpm -C client typecheck`（tsc） | 0 |
| 相關 vitest（previewText、pr2bPractice、critDamagePanel、unitInfo*、statusCard、avoidPanel、floatCardRule、`src/render`、pathPreview、trailPreview、tileInfoTrail） | 0（`src/render` 整包跑時 `qIconQi2d.test.ts` 一題在 wish 連跑的負載下超過 30 秒逾時，單獨重跑 16 passed、2.5 秒，和這段無關） |
| 相關 pytest（`tests/api` 全部、`tests/narrative`、`tests/engine/test_crit_*`、`test_view.py`、`test_variance_preview.py`） | 0（`tests/api` 1498 passed、1 skipped） |
| `corepack pnpm -C client build`（截圖前） | 0 |
| `uv run python scripts/check.py --all`（merge main 後） | 待補 |
| `uv run python scripts/run_pytest.py -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 待補 |
| `corepack pnpm -C client build`（merge 後） | 待補 |

### 3.4 截圖（`docs/art/shots/cr-1b/`，交美術 PM）

內容複本（暫存區 `cr1b/content_shot`）：匕首 `crit_permille: 2500`、瞬步背刺 `crit_range: 19`＋`crit_permille: 2500`、暴擊截圖起始包（同 CR-1）；頭部裝備「鷹眼頭巾」（暴擊傷害 +10%）；E3b 的霜行攀岩靴。`trpg serve --port 8791`、`?dev=1&mute=1&anim=0`、無頭 Chrome 加 `--mute-audio`。jpg 品質 80，都在 130 KB 以下。

- `docs/art/shots/cr-1b/cr1b_attack_preview_1600x900.jpg`：預覽「命中 95%　暴擊率 15%」「擲出 19–20 暴擊・暴擊傷害 260%」（匕首 250%＋詞條 +10%）；浮動卡位置和 CR-1 相同
- `docs/art/shots/cr-1b/cr1b_attack_preview_800x600.jpg`：同一個場景 800 寬，浮動卡改到目標右邊，預覽面板整段沒被蓋
- `docs/art/shots/cr-1b/cr1b_skill_card_1600x900.jpg`：瞬步背刺展開「詳細」，兩個傷害分點都寫「暴擊範圍 19–20，暴擊傷害 250%」
- `docs/art/shots/cr-1b/cr1b_panel_1600x900.jpg`：主角單位卡（釘住、展開「▸ 詳細」）：數值區「暴擊傷害 260%」，詳細「武器「匕首」250%・詞條 +10%（全身上限 300%）」
- `docs/art/shots/cr-1b/cr1b_panel_800x600.jpg`：同上 800 寬
- `docs/art/shots/cr-1b/cr1b_frost_preview_800x600.jpg`：霜行預覽（同 E3b 場景），預覽牌改擺停點下方，沒蓋到敵人

截圖後伺服器與 Chrome 都用自己的 PID（`taskkill /PID … /T /F`）關掉，查過沒有殘留。

## 4. 複雜度

沒有新增 `noqa`。

## 5. 待 PM 決定

1. **技能卡的範圍用字**：預覽是「擲出 19–20 暴擊」，技能卡保守沿用改版前的「暴擊範圍 19–20」，再接「暴擊傷害 250%」。要不要改成和預覽一樣，請玩法 PM 定。
2. **「角色面板」取戰鬥中的單位卡**（`UnitInfo`，E3b 的種族列在這裡）；一輪中的主角面板（`RunHeroPanel`，「種族・出身」「武器」那張）沒有加。要加的話後端 `RunHero` 另開欄位（沒有戰鬥狀態，要另外組一份）。
3. **面板的修正技只算不看目標的條件**（`Subject(None, 自己的格子)`）。看目標的（例「對燃燒中的敵人暴擊傷害 +25%」）不算進面板，實戰照算。要不要在詳細加註「另有條件加成」，請定。
4. **來源文字的格式**：沒截到時結尾「（全身上限 300%）」，被截時改成「・頂到上限 300%」／「・最低 150%」（不再同時寫括號）。負的加減寫「-30%」（半形負號）。
5. **其他陣營不寫修正技名**，合併成「修正技 +N%」；隱蔽中看不到資訊的敵人整格不顯示。
6. **浮動卡「放上層」的 z-index**：卡片降到 11（左欄 13 之下），只在怎樣都會重疊時套用；此時卡片也會在戰場上的其他浮動層之下。
7. **預覽牌的「上方」**放在停點那一格的頭上（再高半格），「下方」貼停點下緣、水平置中；單位範圍＝格子往上多半格。這些是版面初值，美術看截圖再調。
8. **6.5.1 的「滑進→捲到底→釘住→關閉」實測**：這段只改擺位，截圖時做了 Shift＋點釘住與展開「詳細」（800、1600 各一次），沒有逐項做完整流程。
