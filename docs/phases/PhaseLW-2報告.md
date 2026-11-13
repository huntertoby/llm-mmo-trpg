# Phase LW-2 完成報告｜獨狼前端：出城前提示＋戰鬥中條件不成立標灰（＋無人掩護改條件倍率）

> 規格：沒有另寫計畫檔，以設計文件為準：`docs/玩法決定紀錄.md` #156、`docs/design/06-技能.md` 6.37「提示與標灰」與「LW-1 後的細節」、`docs/design/09-世界與敘事.md` 9.6.9；`docs/phases/PhaseLW-1報告.md`（含開發 PM 裁定）。
> 基準：main `f80382f0`（含 LW-1）。開工時 worktree 在 `9862b3a4`，`git merge --ff-only main` 後開始。
> 追加（開發 PM 轉玩法 PM 定稿，06 6.37「LW-1 後的細節」）：無人掩護平常照一般倍率、獨狼時才提高。

## 1. 做了什麼

### 1.1 內容：無人掩護（追加）

`content/skills/skill_unguarded_shot.yaml`：武器倍率 1400 → **1000**；新增一段 `damage` `multiplier_permille: 600`、`condition: {type: lone_wolf}`（寫法同隱匿射擊「1000＋隱蔽時 1300」）；獨狼時隱蔽 2 回合照舊。預算 73.7% → **71.9%**（獨狼那段 500 時 68.7% 不合格，取 600；保守占位，倍率在數值工坊 `effects[*].multiplier_permille`）。`trpg content check` 0。只改這一個技能檔。

### 1.2 後端（只讀狀態，不改引擎規則，戰鬥紀錄版號不動）

- `src/trpg/api/condition_off.py`（新）：`STICKY_CONDITIONS = {"lone_wolf"}`（整場固定的施放者條件）、`OFF_REASON_ZH`（「開戰時身邊有隊友，獨狼本場不成立」）、`sticky_conditions(skill)`（技能層級、第二段、每個效果含 followup／modifier 效果、修正規則的條件）、`sticky_kinds(skill)`、`skills_off(state, unit_id)`。判斷用引擎公開的 `condition_met`。`any_of` 只有每個分支都是整場固定條件才判斷。
- `BattleResponse.skills_off: tuple[SkillOffOut, ...] | None = None`（選用；`skill_id`、`conditions`、`whole`、`reason_zh`）。`presenter.battle_response` 每次回應都給（不限主角回合）。
- `PartyView.lone_wolf: LoneWolfView | None = None`（選用；`ok`、`skills_zh`、`affixes_zh`）：`world_party_view.lone_wolf_view` 看主角技能列（`hero_skills`，含生成技能）與穿戴裝備（`worn_gear`）的條件詞條；`ok`＝隊伍面板人數 1（只有主角）。
- 重產 `client/openapi.json`、`client/src/api/schema.d.ts`；`api/types.ts` 加 `SkillOff`、`WorldLoneWolf`。

### 1.3 前端

- **出城前提示**（隊伍與影子，PNL-1a 的 `Callout`）：`world/partyShadow.ts` `LONE_WOLF_ZH`、`loneWolfHint`；`PartyShadowPanel.tsx` `LoneWolfCallout`（成員卡下面）。
  - 帶隊友：琥珀警告「**獨狼**：帶隊友出城，獨狼技能不會生效」＋次行「用不出來：孤狼撲擊、獨行者、皮甲的「獨行的」」。
  - 獨行：青色資訊「**獨狼**：只帶主角出城，獨狼技能會生效」＋次行「會生效：…（護送、守點戰開場就有 NPC 同行時不成立）」。
  - 我的影子分頁：帶獨狼技能或詞條時資訊「獨狼技能在影子裡用不出來（借你影子的人身邊一定有隊友）」（06 6.37「影子」段）。`ShadowPane` 多一個選用 prop `loneWolf`（向後相容）。
- **戰鬥中標灰**：`battle/conditionOff.ts`（`conditionOffMap`、`withConditionOff`、`conditionOffClass`、`conditionOffLine`、`conditionOffLabel`）；`SkillButton.conditionOff`（選用）；`useBattleData` 套上伺服器的 `skills_off`；`SkillBar` 主動鈕與被動／反應小圖示加 `cond-off` class 與無障礙名，說明卡第一行 `ui/ConditionOffNote.tsx`「本場不成立：開戰時身邊有隊友，獨狼本場不成立（帶條件的效果本場不會發動，其餘照常）」（技能層級：「這一招本場不會生效」）。CSS：圖示 `grayscale(1) brightness(0.8)`、框改虛線；說明行自帶深藍底＋虛線框。**標灰不擋按鈕**（無人掩護不獨狼時照樣能射，只少那段傷害與隱蔽）。
- 開發頁 `client/dev/panel-gallery.html#party` 加 `?lone=off|on`。
- 可重用（BS-2）：新的整場固定條件只要在 `condition_off.py` 的兩張表各加一筆；前端不認條件種類。寫進上手筆記第 113 點。

## 2. 測試

新增：

| 檔案 | 內容 |
|---|---|
| `tests/api/test_condition_off_lw2.py` | 獨行沒有標灰；帶隊友時獨行者（`whole`）、無人掩護、孤狼撲擊（部分）列出且原因相同；沒帶獨狼條件的隱匿射擊不列；不存在的單位；`any_of` 混了「第一輪」不算、全是獨狼照算；`skills_off` 是選用欄位 |
| `tests/world/test_lone_wolf_party_lw2.py` | 沒帶獨狼東西沒有提示；獨行＋獨行者＝成立；帶傭兵＝不成立；「獨行的」詞條列成「皮甲的「獨行的」」 |
| `client/src/battle/lw2ConditionOff.test.ts` | 純函式；技能列 HTML 只多 `cond-off` 與無障礙名（其餘逐字同）、不加 `blocked`；說明卡第一行；接線與 CSS |
| `client/src/world/lw2LoneWolf.test.ts` | `loneWolfHint` 三種；隊伍分頁琥珀／青、舊回應沒有欄位不畫；我的影子分頁提示 |

改到的既有測試資料（都由無人掩護的內容改動直接造成，逐項說明）：

| 檔 | 舊 → 新 | 理由 |
|---|---|---|
| `client/src/render/fixtures/skill_icons.json` | `skills.skill_unguarded_shot.segments[0].effects` 2 筆 → 3 筆（多一筆 `damage`／`lone_wolf`）；`art` 不變；其他鍵全同（腳本比對） | 圖示資料照效果產生；用 `uv run python -m tests.narrative.icon_fixture` 重產，`tests/narrative/test_skill_icon.py::test_client_fixture_is_current` 要求 |
| `tests/skillgen/fixtures/refactor_3wr2.json` | 只改 `complete.skill_unguarded_shot`（`bcddda91…` → `baa17a7a…`）與 `retier.skill_unguarded_shot`（`883943b5…` → `df2173b2…`），其他鍵沒動 | 這招的效果變了，強度與升階結果跟著變（同 LW-1 只加三招的做法） |
| `tests/cli/snapshots/cli_output_hashes.json` | `skills_list`（`9e79a2bc…` → `72756a5b…`）、`skills_show_all/13`（`862bbc4c…` → `c6dbe03e…`）；只用 `UPDATE_CLI_SNAPSHOTS=1` 重產這兩鍵 | `skills list` 的無人掩護效果摘要變了；`/13` 是含 `skill_unguarded_shot` 的那一片（LW-1 報告第 5 節）。招數沒變，沒有分片位移，其他鍵不變 |

沒有放寬任何斷言。

## 3. 瀏覽器實測與截圖

無頭 Chrome（`--mute-audio`、除錯埠 9472）、`trpg serve`（8742，正式 build）、vite（8743，開發頁）；網址都帶 `?mute=1`。腳本在 scratchpad `lw2/cdp.mjs`。

- **戰鬥（實機）**：`/?dev=1&anim=0.1&mute=1` 首頁單場戰鬥（弓、種子 20261024），頁面裡包 `window.fetch` 在 `POST /api/battles` 加上 `custom_skills`（無人掩護、獨行者）。單場戰鬥一定補隊友到 3 人 → 伺服器真的回 `skills_off`（無人掩護 `whole=false`、獨行者 `whole=true`），技能列兩個都標灰。獨行對照：同樣包 fetch 改成 `hero_build: build_ranged`、`ally_builds: []`、`replace_skills` → `skills_off` 為 null、不標灰（API 直接打也驗過：帶隊友 2 筆、獨行 null）。
- **隊伍與影子**：實機沒有能帶獨狼技能出城的角色（要先學會並裝上），用開發頁 `/dev/panel-gallery.html?lone=off|on#party`（正式元件、固定資料）——**實機未看**。

浮動卡「滑進 → 捲到底 → 釘住 → 關閉」（兩個觸發：無人掩護主動鈕、獨行者被動小圖示）：

| 尺寸 | 觸發 | 滑進後仍開 | 捲到底 | 釘住（離開仍開） | Esc 關閉 |
|---|---|---|---|---|---|
| 1600×900 | 無人掩護 | 是 | 內容 171 = 可視 171，不需捲動、卡不關 | 是（`pinned`） | 是 |
| 1600×900 | 獨行者 | 是 | 同上 | 是 | 是 |
| 800×600 | 無人掩護 | 是 | 「詳細」全展開 391 = 391，仍放得下、不需捲動 | 是 | 是 |
| 800×600 | 獨行者 | 是 | 展開 394 = 394，不需捲動 | 是 | 是 |

第一輪截圖發現「本場不成立」那行壓在戰場上（技能卡浮動卡外層透明），改成自帶底色後重拍（commit `65bf7384`）。

截圖（10 張，jpg 80，最大 136 KB）：
- `docs/art/shots/lw2/lw2_party_off_1600.jpg`（開發頁，實機未看）帶隊友：琥珀提示
- `docs/art/shots/lw2/lw2_party_on_1600.jpg`（開發頁，實機未看）獨行：青色提示
- `docs/art/shots/lw2/lw2_party_off_800.jpg`（開發頁，實機未看）800×600 捲到提示
- `docs/art/shots/lw2/lw2_shadow_on_800.jpg`（開發頁，實機未看）我的影子分頁提示
- `docs/art/shots/lw2/lw2_battle_team_1600.jpg` 實機戰鬥全畫面
- `docs/art/shots/lw2/lw2_skillbar_team_1600.jpg` 技能列：帶隊友（無人掩護、獨行者標灰）
- `docs/art/shots/lw2/lw2_skillbar_alone_1600.jpg` 技能列：獨行（不標灰）
- `docs/art/shots/lw2/lw2_shotcard_1600_card.jpg` 無人掩護說明卡（部分不發動）
- `docs/art/shots/lw2/lw2_passive_1600_card.jpg` 獨行者說明卡（整個被動不生效）
- `docs/art/shots/lw2/lw2_shotcard_800_scrolled.jpg` 800×600 說明卡「詳細」展開

伺服器、vite、Chrome 都用自己的 PID 關掉；8742、8743、9472 沒有在聽，沒有殘留的 Chrome。

## 4. 檢查與結束碼

| 指令 | 結果 |
|---|---|
| `uv run trpg content check` | 0（407 個技能通過） |
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0（1533 個檔） |
| `uv run lint-imports` | 0（14 kept、0 broken） |
| `pytest -n 8` `test_lone_wolf_lw1`、`test_lone_wolf_skillgen_lw1`、`tests/content`、`tests/api/tuning`、`test_client_fixtures`、`test_lone_wolf_world_lw1` | 0：3207 passed |
| `pytest -n 8 -m "slow or not slow"` `test_refactor_parity`、`test_output_snapshots`、`test_skill_icon`、`test_openapi_snapshot`、`test_client_fixtures`、LW-2 兩檔、`test_routes`、`tests/world/test_party.py` | 改前 1（4 failed：parity 兩筆、CLI 兩鍵，見第 2 節）；只更新那 4 筆後 0 |
| `tests/narrative/test_skill_icon.py`、`tests/content/test_icon_prop_qi2d.py` | 改前 1（夾具過期）；重產夾具後 0 |
| `pytest -n 8` openapi 快照、client fixtures、LW-2 兩檔、`test_routes`、`test_world_party_api`、`test_skill_reasons_api`、`test_ob7_party_intro`、`tests/world` | 0：1338 passed |
| `trpg battle --map open_plain --seed 7` ＋ `battle replay` | 0：重播驗證通過（91 動作、383 事件） |
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client test --run` | 0：328 檔、4252 passed |
| `corepack pnpm -C client build` | 0 |

沒跑 `scripts/check.py`、沒做平衡量測。

## 5. 待 PM 決定

1. **出城前「成不成立」只看隊伍面板人數**（只有主角＝成立）。護送、守點戰開場就有 NPC 的情況出城前看不到，只在成立時的提示裡寫一句「護送、守點戰開場就有 NPC 同行時不成立」。
2. **標灰不擋按鈕**：帶獨狼效果的主動技在不成立時照樣能用（只是少那段），所以只褪色＋虛線框＋說明，不加 `blocked`。整招都看獨狼的（技能層級條件）本來就會被引擎擋，照舊由「現在不能用」說明。
3. **只標整場固定的條件**（目前只有 `lone_wolf`）；`any_of` 混了會變動的分支（例「獨狼，或第一輪」）不標。BS-2 的武器條件要加進 `STICKY_CONDITIONS` 時，換裝只在城鎮／營火，戰鬥中等於固定，可以照加。
4. **影子分頁的提示只看「自己帶獨狼技能或詞條」**，字照設計「獨狼技能在影子裡用不出來」，括號補一句理由（新字）。
5. **詞條列成「物品名的「詞條名」」**（例「皮甲的「獨行的」」），不寫數值；技能列名字。新字都在 `partyShadow.ts` 的 `LONE_WOLF_ZH`，請美術／玩法 PM 看字。
6. **標灰的樣子**（圖示灰階、虛線框、說明卡上方自帶深藍底虛線框的一行）是實作者暫定，請美術 PM 驗收。
7. **既有的 `.skill-card-reason`「現在不能用：…」也沒有底色**，在戰場上一樣會壓在格子上（截圖時看到）；本段沒改（範圍外）。
8. **無人掩護獨狼那段取 600**（71.9%，合格內的整數占位；500 不合格）。倍率交數值工坊。
9. **出城前提示的隊伍分頁沒有在分頁記號上掛三角**（帶隊友＋獨狼技能時）：PNL-1a 的記號規則沒寫這種情況，保守不加。

## 6. 新增的複雜度類 noqa

無。

## 7. commit

- `825304c5` content(lw2): unguarded shot extra damage only when lone wolf
- `4480dc10` feat(api): lone wolf hints - skills_off in battle, lone_wolf in party view
- `5239c790` feat(client): lone wolf party hint and in-battle condition-off greying
- `65bf7384` style(client): condition-off note gets its own box; LW-2 screenshots
- （本報告與上手筆記）docs(lw2): report and onboarding notes

## 開發 PM 裁定（2026-11-13，第八任開發 PM）

已驗收並以 --no-ff 合入 main（`world_party_view.py` 的 `__all__` 與上手筆記衝突：兩邊都留，LW-2 筆記改為 121～125）。合併後 ruff、format、mypy、content check 0；tests/api＋content 4188 passed；CLI 快照 slow 24 passed；前端 typecheck 0、vitest 4285 passed、build 0。無人掩護的 4 筆夾具與 2 個快照鍵逐項說明，接受。

1. 出城前只看隊伍人數、護送 NPC 補小字：接受。
2. 標灰只是外觀不擋按鈕：接受。
3. 只標整場固定的條件：接受。
4. 新字（LONE_WOLF_ZH）：轉玩法 PM 與美術 PM 看字。
5. 標灰樣式：交美術 PM 驗收。
6. 既有「現在不能用」那行沒底色：記入下一個前端小修。
7. 獨狼段 600 占位：交數值工坊。
8. 帶隊友又帶獨狼技能時分頁記號不掛警告：交美術 PM 定。

### 美術驗收結果（2026-11-13，docs/art/LW-2驗收.md）

有條件通過。必修 1（800 帶隊友時獨狼警告被切）＋可修 3（「現在不能用」加底色）＋PNL-4 可修 2（線頭名末兩字黏「〕抵」）派 LW-2b；可修 1（兩條青色合併）待玩法 PM 定字；可修 2（無人掩護說明卡灰階）併 BS-2。標灰樣式定為共用規則（需求 3.7）；分頁不掛警告三角。
