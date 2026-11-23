# Phase CR-1c 報告｜主角面板的暴擊傷害、看目標的加成提示＋美術 CR-1b 小修 2 件

實作者，2026-11-23。規格 `docs/phases/PhaseCR-1c計畫.md`，基準 main `32d8068e0`；開工後照開發 PM 指示 `git merge --no-edit main`（`c2b1d696e`，只帶進 `docs/art/CR-1b驗收.md` 與交接），加做 `docs/art/CR-1b驗收.md` 的「小修」兩件。

## 1. Commit

| commit | 內容 |
|---|---|
| `adbb47186` | 第 1 項：一輪中的主角面板顯示「暴擊傷害 N%」，「▸ 詳細」列來源 |
| `b52648585` | 第 2 項：看目標的加成提示（單位卡與主角面板） |
| `d8b527275` | 美術小修 1：「名稱＋數字」換行時整個一起移（預覽面板、暴擊來源文字） |
| `e3d10c4b6` | 美術小修 2：預覽牌留在地圖可見範圍內 |
| `9a6d46d02` | 截圖 `docs/art/shots/cr-1c/`（6 張） |
| （本報告） | 報告 |

## 2. 做法

### 2.1 主角面板的暴擊傷害（第 1 項）

- **後端怎麼組狀態**（新模組 `src/trpg/roguelite/hero_crit.py`）：一輪中沒有戰鬥狀態，照開戰的做法組一份只有主角一個單位的最小 `BattleState`：
  - 單位：`progress.hero_spawn`（開戰同一份範本、武器、裝備）交給 `engine.lifecycle.make_unit`（開戰同一個函式：裝備詞條、種族、裝備授予的技能、武器特性強化都照算）；
  - 規則包：`skillgen.reshape_gate.gated_with_skills(library, run.generated_skills)`，和開戰同一個（主角的生成技能查得到；E5 規定加技能一律走閘門，`tests/skillgen/test_reshape_gate_paths_e5.py` 會擋。初版用 `with_skills`，第 1 次全量被這題擋下，改掉）；
  - 地圖：1×1 石地（高度 0、沒有表面），主角站 (0, 0)，第 1 輪、沒有其他單位；
  - 倍率與來源：引擎的 `crit_damage_breakdown`（和結算、戰鬥中的單位卡同一個函式），參數也和單位卡相同（主手普攻 `modifiers.ATTACK`、`Subject(None, 自己的格子)`）。不擲骰、不改狀態。
- **API**：`HeroOut.crit_damage_permille`、`crit_damage_detail_zh`（`run_presenter._hero`）；用字用 `crit_damage_detail_zh`，和單位卡同一套字。守則 14：玩家自己的主角，修正技寫技能名。OpenAPI 與 `schema.d.ts` 重產。
- **前端**（`run/RunHeroPanel.tsx` 的 `HeroCritDamage`）：屬性列下面一行「暴擊傷害 260%」（`data-testid="run-crit-damage"`，200% 也顯示）；下面一個「▸ 詳細」（和單位卡同一個 `unit-details` 樣式），表格一列「暴擊傷害｜來源」。前端只排版，不重算；舊回應沒有欄位時整格不畫。
- **和開戰一致**：測試直接開戰（`battle_setup` → `begin_battle`），主角對敵人的普攻倍率和面板相同（2550‰）。

### 2.2 看目標的加成提示（第 2 項）

- **判斷**（`engine/modifiers.crit_damage_has_target_rule`）：單位身上套用在主手普攻上、改 `crit_damage_permille` 的修正規則，條件（`any_of` 任一分支）有不在 `CASTER_CONDITIONS`（只看施放者）裡的，就算「條件看目標」。只看有沒有這種規則，不看它現在成不成立。
- `CritDamageBreakdown.target_rule`（只給顯示用，結算不讀）；`crit_damage.crit_damage_hint_zh` 回「另有看目標的加成，攻擊預覽時才算」或 `None`。
- **欄位**：`UnitView.crit_damage_hint_zh`、`HeroOut.crit_damage_hint_zh`。前端共用 `ui/CritDamageDetail.tsx`：來源後面另起一行（淡色）放提示。
- **單位卡上看不到修正技名稱的陣營**：照最保守的做，**不顯示**。`view._crit_damage_fields` 只在 `unit.team is 觀看者陣營`（和「寫不寫技能名」同一個判斷）時給提示行；其他陣營一律 `None`。隱蔽中看不到資訊的單位（`hidden_info._masked_unit`）也一起藏成 `None`。
- 面板的數字照舊不算看目標的加成（第 2 項只加提示行）。

### 2.3 「名稱＋數字」換行時整個一起移（美術小修 1）

- 新元件 `ui/WrapUnits.tsx`：字串在「・」「、」、全形空白後面切段，分隔符留在前一段尾巴（下一行不會從「・」開頭），每段包成 `<span class="wrap-unit">`，CSS `display: inline-block`（不是 nowrap，一段比一行還長時段內照常斷）。
- 套用：攻擊預覽面板的每一行（實戰；測試模式的總覽行原本就有 PR-2b 的不換行三段，其他行也套）、連鎖預告兩列；單位卡與主角面板的暴擊來源文字。
- 800 寬實測：「擲出 20 暴擊・」「暴擊傷害 285%」各自一段，「暴擊傷害 285%」整段移到下一行；來源「詞條 +10%（全身上限 300%）」比一行長，段內斷在括號後面（照規則）。

### 2.4 預覽牌留在地圖可見範圍內（美術小修 2）

- `render/pathArt.pushInside`：置中的位置（上方、下方）像浮動卡一樣往內推，整塊留在範圍內。
- 範圍＝地圖可見範圍（世界座標），用和浮動字同一個 `floatStack.visibleFieldBounds`（地圖寬高、上方預留、扣掉鏡頭偏移；震動不算）。`HighlightLayer.pathTagRescale` 傳進 `placeTags`。
- **另外加的一條**（見待決 2）：實測時（冰湖，主角在第 0 欄往下走）預覽牌選的是「左邊」那個位置，整塊在地圖左緣外、被切掉。所以有給範圍時，左右兩邊的位置出界就不選（不推：推進來會蓋到停點）；全部的位置都出界時照舊從全部的位置挑。沒給範圍（舊呼叫、CR-1b 的測試）時和改前完全相同。

## 3. 驗收

### 3.1 結果不變（different=0）

基準 `32d8068e0`（`git archive` 的 `src`、`content`、`config`、`scripts`）；新版是全部程式 commit 之後的工作區。腳本沿用 CR-1b 的 `compare78.py`、`budget.py`、`census_cmp.py`（暫存區 `cr1c/`）。

| 比對 | 結果 |
|---|---|
| 442 招逐招預算（`BudgetReport` repr＋`validate_skill`） | 442 招，`cmp` 0（逐位相同） |
| census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`，不看計時） | `cells=204 different=0 whole_equal=True`（兩邊結束碼 0） |
| 78 場（`compare78.py`，a 段那組；`format` 也比） | `battles=78 events=26741 different=0`；內嵌規則包差異 0 |
| CLI 快照（slow） | 見 3.3 |

`LOG_FORMAT` 不升版（沒有新事件欄位；`UnitView`、`HeroOut` 的新欄位不進戰鬥紀錄）。

### 3.2 新增與改的測試

| 驗收條件 | 測試 |
|---|---|
| 主角面板：沒截到、頂到上限、最低、來源列 | 後端 `tests/roguelite/test_hero_crit_cr1c.py`（200% 也顯示、設計例子 260%（武器＋詞條＋種族＋修正技）、頂到上限、最低、和開戰後的結算倍率相同）；前端 `client/src/run/heroCritDamage.test.ts`（三種情況的數值區與「▸ 詳細」、200%、舊回應不畫） |
| 提示行：有、沒有（單位卡、主角面板） | 後端 `tests/engine/test_crit_hint_cr1c.py`（看目標的規則 → 有、數字不算它；沒有條件、只看自己的條件 → 沒有；`any_of` 有看目標的分支 → 有）、`test_hero_crit_cr1c.py`（主角面板有、沒有）；前端 `client/src/ui/critDamageHint.test.ts`（單位卡、主角面板各有、沒有；提示在來源後面） |
| 看不到修正技名稱的陣營不顯示 | `test_crit_hint_cr1c.py::test_other_teams_never_see_the_hint`（敵方視角看我方單位：數字照給、提示行 `None`）、`test_hidden_units_hide_the_hint` |
| 一個單位不被拆開 | `client/src/ui/wrapUnits.test.ts`（切段、接起來是原字、「暴擊傷害 260%」「詞條 +10%」「傷害 52–146」各自一段、CSS 是 inline-block 不是 nowrap、接線：預覽面板（實戰與測試模式）、單位卡、主角面板） |
| 預覽牌靠左、靠右邊界時往內推 | `client/src/render/cr1cPathTagBounds.test.ts`（`pushInside` 四邊；靠左 → 上方置中往右推；靠左改擺下方 → 往右推；靠右 → 往左推；左右位置出界不選；全部出界照舊；接線） |
| 改的舊測試 | `client/src/ui/critDamagePanel.test.ts`：來源切成段後，比字先去掉標籤 |

### 3.3 檢查指令

| 指令 | 結束碼 |
|---|---|
| `uv run ruff check .`、`ruff format --check .`、`mypy`、`lint-imports`（每個 commit 前） | 0 |
| `uv run trpg content check` | 0 |
| `uv run python scripts/hardcoded/classify.py --check` | 0（沒歸類 0） |
| `corepack pnpm -C client typecheck`（tsc） | 0 |
| 相關 vitest（`src/ui`、`src/battle`、`src/run` 整包；`src/render` 整包） | 0（render 135 檔 1704 passed） |
| 相關 pytest（`test_crit_hint_cr1c`、`test_crit_panel_cr1b`、`test_crit_display_cr1`、`test_view`、`test_openapi_snapshot`、`tests/api/test_hidden_info.py`、`test_hero_crit_cr1c`） | 0 |
| `corepack pnpm -C client build`（截圖前，兩次） | 0 |
| `uv run python scripts/check.py --all`（merge main `32ca036fd` 之後，第 1 次） | 1：pytest 1 題失敗（`tests/skillgen/test_reshape_gate_paths_e5.py::test_every_with_skills_call_goes_through_the_gate`，`hero_crit` 直接呼叫 `with_skills`）；改成 `gated_with_skills`（`7694add12`） |
| `uv run python scripts/check.py --all`（第 2 次） | **0**：pytest 18728 passed、8 skipped；vitest 421 檔 4978 passed；ruff、format、mypy、lint-imports、client typecheck、situation coverage 通過；已寫通過戳記 |
| `uv run python scripts/run_pytest.py -q -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | **0**（995 passed）；CLI 快照、parity 沒變 |
| `corepack pnpm -C client build`（check 之後） | **0** |
| 合併 main、修正後重跑三項比對（基準 `32d8068e0`） | 442 招 `cmp` 0；78 場 `battles=78 events=26741 different=0`；census `cells=204 different=0 whole_equal=True` |

### 3.4 截圖（`docs/art/shots/cr-1c/`，交美術 PM）

內容複本（暫存區 `content_shot`，不進 repo）：長弓 `crit_permille: 2500`；普攻流弓手（`build_attack_archer`）的「普攻精通」換成測試修正技「獵心」（普攻傷害 +7%；**對 HP 一半以下的目標暴擊傷害 +25%**＝看目標的修正技）；頭「鷹眼頭巾」（暴擊傷害 +10%）、腳「霜行攀岩靴」（E3 的測試霜行詞條）。`trpg serve --port 8793`、`?mute=1&anim=0`、無頭 Chrome `--mute-audio`、DPR 1；jpg 品質 80，都在 150 KB 以下。

- `docs/art/shots/cr-1c/cr1c_hero_panel_1600x900.jpg`：一輪畫面的主角面板，「暴擊傷害 260%」，展開「▸ 詳細」：「武器「弓」250%・詞條 +10%（全身上限 300%）」，下一行「另有看目標的加成，攻擊預覽時才算」
- `docs/art/shots/cr-1c/cr1c_hero_panel_800x600.jpg`：同上 800 寬
- `docs/art/shots/cr-1c/cr1c_attack_preview_1600x900.jpg`（小修 1）：普攻預覽（目標 HP 20／350，看目標的加成算進去）「命中 70%　暴擊率 5%　傷害 55–288（期望 69.3）」「擲出 20 暴擊・暴擊傷害 285%」；「傷害 55–288（期望 69.3）」整段換到下一行
- `docs/art/shots/cr-1c/cr1c_attack_preview_800x600.jpg`（小修 1）：同上 800 寬，「暴擊傷害 285%」整段換到下一行
- `docs/art/shots/cr-1c/cr1c_unit_card_800x600.jpg`（小修 1）：釘住主角的單位卡、展開「▸ 詳細」：「武器「弓」250%・」「詞條 +10%（全身上限 300%）」，提示行在下面
- `docs/art/shots/cr-1c/cr1c_frost_preview_800x600.jpg`（小修 2）：冰湖，主角在 (0,3) 穿霜行靴往下走到 (0,6)，預覽牌「沿路留下冰 3 格（1 回合後消失）」擺在停點下方、左緣貼齊地圖左緣，整塊在地圖內（改前選左邊、被地圖左緣切掉）

截圖後伺服器與 Chrome 都用自己的 PID（`taskkill /PID … /T /F`）關掉。

## 4. 複雜度

沒有新增 `noqa`。

## 5. 待 PM 決定

1. **看不到修正技名稱的陣營不給提示行**（規格要求最保守）：敵方視角看我方單位、我方看敵方單位，提示行一律不出現；隱蔽中的單位也藏。多人階段再整體檢查。
2. **預覽牌左右兩邊的位置出界時不選**（小修 2 的延伸）：美術寫的是「置中放的位置往內推」；實測冰湖第 0 欄時選的是左邊、整塊出界，所以一併處理成「出界不選」（不推）。全部的位置都出界時照舊。要不要只做置中、左右照舊，請定。
3. **主角面板每次回應都組一次狀態**（`gated_with_skills` 含閘門表重算）：只有身上有裝備授予的變形修正技時才逐招重算；之後若覺得慢，可以快取。
4. **「條件看目標」的判斷**：條件任一分支不在 `CASTER_CONDITIONS` 就算（包含 `height_advantage`、`target_on_surface`、`on_own_rune` 這類看目標格的）。只看身上有沒有，不看現在成不成立；只算套用在主手普攻上的規則（面板算的是普攻）。
5. **提示行與「▸ 詳細」的位置**：主角面板的「暴擊傷害 N%」與「▸ 詳細」放在屬性列下面、屬性階數清單上面；提示行是來源下面另起一行的淡色字。版面初值，美術看截圖再調。
6. **段內還是太長時照常斷**：例如 800 寬的「傷害 55–288（期望 69.3）」是一整段，比預覽面板一行長，段內斷在「期望」後面；「詞條 +10%（全身上限 300%）」同理。要不要在全形括號前也切段，請美術定。
