# Phase 3-24c 完成報告：關鍵字池補真實利用者、文字修正、火器武器技

> 實作者：implementer（sonnet）。規格：`docs/phases/Phase3計畫.md` 第 27 節、`docs/design/06-技能.md` 6.27.2、`docs/design/08-裝備.md` 8.11。
> 分支：`worktree-agent-a39bc3fb0c2f34c54`（從 main 的 `9eccd9e` 分出），未 push、未合併。

## 1. Commit 列表

見文末「最終檢查」下方的 commit 表（依邏輯分段）。

## 2. 驗收逐條

| # | 規格 | 結果 | 證據 |
|---|---|---|---|
| 1 | 撞擊：新條件「目標本回合受過撞擊」＋至少 2 招主動技 | 通過 | 條件 `target_collided`（`UnitState.collided_round`，`Collided` 事件的兩個受害者與超過上限的撞擊都設為當輪；輪數一過失效）。測試 `tests/engine/test_24c.py`：`test_a_unit_that_hit_the_map_edge_counts_as_collided_this_round`、`test_collided_expires_with_the_round`、`test_the_unit_that_was_hit_by_the_pushed_one_is_collided_too`、`test_bone_pursuit_deals_more_only_to_a_collided_target`；技能 `skill_bone_pursuit` 碎骨追擊（近戰武器技）、`skill_shock_follow` 震盪追擊（法術 2d6 加碼） |
| 2 | 召喚物：新原語「獻祭召喚物」＋1～2 招；推導表列為專屬 | 通過 | 原語 `sacrifice_summon`（`dice`、`radius` 0–2、選填 `element`：有 → 爆炸、沒有 → 治療），骨架 `sacrifice`。推導表 summon 的 uses 加 `{effect: sacrifice_summon}`（專屬）。測試 `test_sacrifice_explodes_at_the_summons_tile_and_removes_it`、`test_sacrifice_radius_comes_from_the_data`、`test_sacrifice_without_element_heals_nearby_allies_not_enemies`、`test_only_your_own_summon_can_be_sacrificed`、AI：`test_ai_sacrifices_a_summon_standing_in_the_enemy`／`test_ai_does_not_sacrifice_when_nobody_is_near`；技能 `skill_soul_burst` 魂爆（爆炸）、`skill_spirit_offering` 靈祭（治療） |
| 3 | 點燃、冰凍、帶電各補到至少 3 個主動利用者；至少一招製造帶電的範圍技能形狀可增長 | 通過 | 數量表見第 4 節（專屬規則）。`skill_thunder_clap` 震雷掌（錐形、雷電傷害）：`gear_area_delta` 對它為 +1（`tests/skillgen/test_pools_24c.py::test_pools_have_enough_active_exploiters_under_exclusive_rules` 與下方「帶電範圍」測試） |
| 4 | 嘲諷怒吼附帶「被標記」 | 通過 | `skill_taunting_roar` 加 `apply_status marked`（預算：AP 1 → 2、冷卻 2 → 3，見待決 3）；`test_taunting_roar_applies_marked` |
| 4b | 不限武器的潮濕、冰凍、標記 1 階主動技各至少 1 招 | 通過 | `skill_splash_flask` 潑水瓶（潮濕）、`skill_frost_touch` 凍結之觸（冰凍）、`skill_mark_prey` 烙印獵物（標記），皆 `weapon_req: any`；`test_any_weapon_starter_makes_wet_frozen_and_marked`；`tests/roguelite/test_keyword_start.py::test_bow_can_start_with_wet_thanks_to_any_weapon_skills`（弓＋潮濕現在能開局） |
| 5 | 文字：帶電、召喚物、倒地關鍵字說明；工坊擋下訊息 | 通過（措辭待審，見待決 1） | `content/skill_keywords.yaml` 三段說明；`validate.py` 的 `keyword.required` 訊息改為規格原文並列出 10 個關鍵字：`test_the_keywordless_message_lists_all_ten_keywords` |
| 6 | 火器武器技：耗 1 發、槍聲、站定／遠距／貼臉／距離衰減修正、空膛不能施放、法術不受影響 | 通過 | `test_a_weapon_skill_spends_a_round_and_an_empty_magazine_blocks_it`、`test_the_weapon_skill_gunshot_reveals_a_hidden_shooter`、`test_the_weapon_skill_gets_steady_point_blank_and_far_modifiers`、`test_a_bow_weapon_skill_is_not_affected`、`test_spell_skills_do_not_use_the_magazine`（空膛也能放法術） |
| 7 | 每招新技能過預算、AI 會用；組合器可產生新原語與新條件（低權重）；`icon_of` 有對應部件 | 通過 | `test_every_new_skill_passes_validation_and_budget`（15 招逐一）；AI：獻祭見第 2 列，其餘新技能是一般傷害／狀態／消耗狀態技，沿用既有 AI 評分；組合器：`tests/skillgen/test_composer_24c.py`（獻祭 500 個種子出現 1～5%、治療／爆炸兩種都做得出；`target_collided` 600 個種子出現但遠少於全部條件）；圖示：`skillParts.ts` 新增 `sacrifice_summon` 效果部件、`target_collided` 條件部件與名稱、`sacrifice` 骨架名稱，`skill_icons.json` 重產、vitest 全過 |
| 8 | 不穩定測試 `test_traps_and_stacks_survive_a_json_round_trip` | 不處理 | PM 通知：已在 G3a 修好（原因 `Ruleset._keyword_cache` 私有屬性被 pydantic `__eq__` 比較），本分支沒有碰相關檔案 |
| — | `--log-json` ＋ `replay` 一致 | 通過 | `tests/engine/test_24c.py::test_a_battle_with_gun_skills_and_sacrifice_replays_identically`（長槍武器技＋召喚＋獻祭的效用 AI 對戰，重播逐位元一致）；`tests/cli/test_weapons_24a2_cli.py` 的重播測試改驗 `/42` |
| — | `check.py` 全過、`pnpm build` 成功 | 見「最終檢查」 | |

## 3. 設計摘要

- **`target_collided`**：`UnitState.collided_round`（`clone` 已帶）。設在 `effects/world.py` 的 `_collide`（被擋下者與被撞到的單位）與超過上限的撞擊；條件讀 `unit.collided_round == state.round`（「本回合」＝這一輪）。`skill_conditions.yaml` 新增（`harsh`、rare 起）；composer 以獨立串流 `ctx.rng.fork("composer.extra_condition")` 在抽到目標型條件時以 60‰ 改抽它（`skill_composer.yaml` 的 `extra_conditions`／`extra_permille`），所以沒被抽中的種子結果不變。`skill_fuzz` 會布置它。
- **`sacrifice_summon`**：形狀 `single`，選取時只能選自己的召喚物（`targeting._unit_target_problem`，給中文原因）；結算：`dismiss_summon(..., "sacrificed")`（新原因，不算倒下）再在原位以曼哈頓半徑結算——爆炸對範圍內敵人自動命中（不擲命中、不暴擊，`dice` ＋ 縮放屬性 × 法術倍率），治療對範圍內友方（含施放者、不含被獻祭者，吃「治療量」修正）。預算＝骰子平均 × `sacrifice_summon_permille`（800，初值）。AI：`ai/summon.py::sacrifice_estimate`（便宜估計：半徑內敵人數 × 3 或受傷友方 × 2）＋ `summon_gains` 把 `sacrificed` 當成失去召喚物價值。組合器：骨架 `sacrifice`（法術技、`skeleton_permille: 30`、治療版 350‰）。
- **火器武器技**：`targeting.fires_gun(caster, skill)`＝主動、`category: weapon`、武器有彈匣、技能有傷害效果。`use_skill` 在付費後 `spend_ammo`、開火前若隱蔽則施放後 `reveal_after_gunshot`；`resource_problem` 在彈匣空時回「空膛：…需要先裝填才能施放」；`skill_profile` 套用站定的暴擊範圍、`armor_pierce_permille`、`ignore_cover`（新 `AttackProfile.ignore_cover`，不產生穿透射線）與 `weapon_attack`（命中的站定／距離修正）；傷害套 `range_damage_permille`（`_attack_damage`）；預覽的命中率也含武器修正。被動、反應技與陷阱不算開火（待決 4）。

## 4. 各池「專屬規則下的主動利用者」數量表

「起始」＝1 階、普通或稀有的主動技（創角與候選產生器用）；「全部主動」＝所有階級的主動技（含傳說）。

| 關鍵字 | 起始利用者 | 全部主動利用者 | 名單（`*` ＝起始） |
|---|---|---|---|
| 點燃 | 4（原 1） | 7 | `cinder_burst`、`detonate_burning`、`flare_shot*`、`kindle_pop*`、`kindling_strike*`、`kindred_flame`、`scorching_slash*` |
| 潮濕 | 1 | 1 | `conductive_strike*` |
| 帶電 | 3（原 2） | 5 | `arc_follow_up*`、`chain_lightning`、`rune_thunderbolt*`、`spark_chain*`、`thunder_finisher` |
| 冰凍 | 4（原 1） | 4 | `frost_snap*`、`icebreaker*`、`shatter_ice*`、`thaw_blast*` |
| 倒地 | 0 | 0 | （專屬規則下沒有；近戰武器技是通用規則） |
| 撞擊 | 2（原 0） | 2 | `bone_pursuit*`、`shock_follow*` |
| 標記 | 1 | 2 | `rune_burst`、`rune_thunderbolt*` |
| 高處 | 1 | 1 | `high_ground_shot*` |
| 隱蔽 | 2 | 2 | `shadow_ambush*`、`shadow_backstab*` |
| 召喚物 | 2（原 0） | 2 | `soul_burst*`、`spirit_offering*` |

「製造者」起始數（專屬）：點燃 9、潮濕 4、帶電 10、冰凍 6、倒地 4、撞擊 6、標記 8、高處 6、隱蔽 11、召喚物 3。倒地、潮濕、標記、高處的利用者本階段不在規格內，沒有補。

## 5. 新技能清單（15 招，全部 1 階、稀有、主動、過預算；數值為初值、未經模擬）

| 技能 | 武器 | 內容 | 池（專屬） |
|---|---|---|---|
| `skill_bone_pursuit` 碎骨追擊 | 近戰 | 1.0 倍；目標本回合受過撞擊再 +1.3 倍（AP 2、法力 5、冷卻 2） | 撞擊（利用） |
| `skill_shock_follow` 震盪追擊 | 任何（法術） | 2d6 物理；撞擊過再 +3d6（AP 2、法力 6、冷卻 2） | 撞擊（利用） |
| `skill_soul_burst` 魂爆 | 任何（法術） | 獻祭召喚物，半徑 1 爆炸 2d8 火（AP 1、法力 6、冷卻 3） | 召喚物（利用）、點燃（製造） |
| `skill_spirit_offering` 靈祭 | 任何（法術） | 獻祭召喚物，半徑 1 治療 2d8（AP 1、法力 6、冷卻 3） | 召喚物（利用） |
| `skill_scorching_slash` 灼斬 | 近戰 | 1.0 倍；目標燃燒中再 +1.2 倍 | 點燃（利用） |
| `skill_flare_shot` 照火追射 | 遠程 | 1.0 倍；目標燃燒中再 +1.2 倍 | 點燃（利用） |
| `skill_kindle_pop` 火種爆燃 | 任何（法術） | 消耗燃燒，剩餘回合 × 2d8 火（AP 2） | 點燃（製造＋利用） |
| `skill_icebreaker` 破冰重擊 | 近戰 | 1.0 倍；目標冰凍中再 +1.4 倍 | 冰凍（利用） |
| `skill_frost_snap` 碎霜射擊 | 遠程 | 1.0 倍；目標冰凍中再 +1.4 倍 | 冰凍（利用） |
| `skill_thaw_blast` 融冰震 | 任何（法術） | 消耗冰凍，5d6 冰（AP 2） | 冰凍（製造＋利用） |
| `skill_spark_chain` 火花連鎖 | 法器 | 連鎖 1 跳，1d8 雷（AP 1） | 帶電（製造＋利用：連鎖形狀） |
| `skill_thunder_clap` 震雷掌 | 任何（法術） | 錐形大小 2，1d8 雷（AP 1）；範圍可被「製造帶電的技能範圍 +1」增長 | 帶電（製造） |
| `skill_splash_flask` 潑水瓶 | 任何（法術） | 十字積水＋緩速 1 回合（AP 1、法力 4） | 潮濕（製造），4b |
| `skill_frost_touch` 凍結之觸 | 任何（法術） | 冰凍 1 回合＋2d4 冰（硬控：單體、冷卻 4） | 冰凍（製造），4b |
| `skill_mark_prey` 烙印獵物 | 任何（法術） | 標記 2 回合＋1d4 暗影 | 標記（製造），4b |

另改：`skill_taunting_roar` 挑釁怒吼加標記，AP 1 → 2、冷卻 2 → 3（才過預算）。這 15 招沒有放進 `builds.yaml`（避免與別的分支衝突），測試用 `tests/content/test_coverage.py::_POOL_ONLY` 暫代。

## 6. 不穩定測試

規格第 8 項：PM 通知已在 G3a 修好（`Ruleset._keyword_cache` 私有屬性被 pydantic `__eq__` 比較），本分支沒有修也沒有碰 `test_traps.py`、`Ruleset`。

## 7. LOG_FORMAT

`trpg-battle-log/41` → **`/42`**（新條件 `target_collided`、單位 `collided_round`、新原語 `sacrifice_summon` 與召喚物消失原因 `sacrificed`、火器武器技消耗彈匣與修正）。測試中寫死 `/41` 的六處已改 `/42`；`tests/cli/snapshots/cli_output_hashes.json` 重產。合併時若 G3a／G5b 也遞增，由 PM 處理。

## 8. 釘種子測試與快照的調整（逐項）

- `tests/cli/snapshots/cli_output_hashes.json`：全部重產（`/42` 與挑釁怒吼 AP 改變使輸出改變）。
- `client/src/render/fixtures/skill_icons.json`：重產（新技能、新骨架、組合器串流的少數種子改變）。
- `tests/skillgen/test_candidates.py::test_behavior_tilts_the_new_direction`：池變大後橋接的退回也會偏向行為關鍵字，原本只看第三個候選的撞擊會反向；改為數「三個候選裡有沒有出現撞擊」（行為偏向仍成立：30 個種子 tilted > plain）。
- `tests/roguelite/test_keyword_start.py`：弓＋潮濕不再是「沒有起始技能」（4b 的目的），原參數移除，改為正向測試，另用刪掉相容起始技能的圖書館複本保留「沒有弓能用的起始技能」的拒絕路徑測試。
- `tests/engine/test_skill_shaping.py`：挑釁怒吼的紀錄文字改為「AP 2，冷卻 3 回合」。
- `tests/content/test_skill_rules_content.py`（骨架 15 → 16）、`test_skill_composer_content.py`（`spell_share_permille` 加 `sacrifice: 1000`）、`tests/skillgen/test_validate.py`（骨架範例加 `sacrifice`）：資料表同步。
- `src/trpg/sim/skill_fuzz.py`：布置 `target_collided`，以及獻祭技能把場上友方當成施放者的召喚物（否則組合器產生的獻祭技能「沒有合法選取」）。

## 9. 新增的複雜度 noqa

- `src/trpg/engine/skills/interpreter.py::_resolve_cast`：`# noqa: PLR0917`（6 個位置參數；從 `use_skill` 拆出來，否則 `use_skill` 超過 PLR0912／0915）。其餘 `src/` 沒有新增 noqa。
- 測試：`tests/engine/test_24c.py` 與 `tests/skillgen/test_composer_24c.py` 中函式內延後匯入加 `# noqa: PLC0415`（避免循環匯入／只在單一測試使用）。

## 10. 待 PM 決定

1. **關鍵字說明措辭**：規格說「照玩法 PM 的新版」，但我沒有拿到新版文字，三段（帶電、召喚物、倒地）是我依 6.27.1 表格寫的：帶電「雷電命中會讓目標帶電；帶電會沿著連鎖在敵人之間彈跳，也讓製造它的範圍技能能被強化變大。」、召喚物「召喚與圖騰讓場上多出幫手；你可以獻祭自己的召喚物，在它所在的位置爆炸或治療。」、倒地「絆倒、推倒、撞擊讓目標倒地；倒地的目標吃近戰攻擊更痛，也更容易被背刺與處決。」請玩法 PM 提供正式版本後替換（只改 `content/skill_keywords.yaml`）。
2. **「以召喚物為原點施放」沒有做**：規格只要求獻祭，6.27.1 表格另有「以召喚物為原點施放」，沒有對應原語；召喚物池的利用者目前是獻祭兩招＋通用規則。
3. **挑釁怒吼為了加標記被迫變貴**：AP 1 → 2、冷卻 2 → 3（標記 2 回合 4 點，不改的話預算超出）。另一個做法是縮短嘲諷或標記為 1 回合；請玩法 PM 決定。這也改變 `build_tank` 等使用它的 build 的行為（`sim matrix` 沒有重跑）。
4. **火器的反應技／被動不算開火**：規格寫「施放『用武器攻擊』的技能」，我只處理主動技（`kind == active`）；反應技（例：反擊）與被動觸發的武器攻擊不耗彈。另外「有傷害效果」才算開火——沒有傷害的武器技（姿態、輔助）不耗彈。
5. **火器武器技的物件傷害**：打可破壞物件的武器技傷害沒有套距離修正（只有打單位時套）。
6. **「本回合」的定義**：`target_collided` 以「輪」為單位（`state.round`），不是目標自己的回合；在同一輪內不論是誰撞的、何時撞的都算。
7. **獻祭的細節**：選取只能是自己的召喚物（含圖騰）；半徑 0 只波及召喚物所在格；爆炸傷害不吃修正規則的傷害‰（與 `detonate_runes` 相同）；被獻祭者在範圍內的敵方召喚物也會被炸。治療版不治療被獻祭者本身。
8. **15 招沒有放進 `builds.yaml`**，也沒有跑 `sim matrix`／`sim keywords`；數值皆為初值（碎骨追擊 1.3 倍、冰凍 1.4 倍、燃燒 1.2 倍、獻祭折扣 800‰ 等）。倒地、潮濕、標記、高處的專屬利用者仍偏少（潮濕 1、倒地 0）。
9. **組合器**：新增的 `sacrifice` 骨架以 30‰、`target_collided` 以 60‰ 低權重產生；原本沒被抽中的種子輸出不變，但「種子 → 技能」的對應有少數改變（見第 8 節的快照重產）。
10. **候選產生器的退回行為**：池變大後 `橋接` 的「持有的＋新的」退回更常出現行為關鍵字，未改產生器本身。

## 最終檢查

三個 agent 同時在同一台機器上跑全量測試，`scripts/check.py` 的平行 pytest 慢到不正常（跑了 2 小時以上仍卡在 98%，這段時間其他 agent 也在跑全量），所以我把它停掉，改為**依目錄分批**跑全部測試，每批在修完之後都綠：

- `uv run ruff check src tests`、`ruff format --check`、`mypy`（485 個檔案）、`lint-imports`（`check.py` 前半段，6 個契約全 KEPT）：全過。
- pytest 分批（皆 `-n 3/4`）：`tests/content tests/narrative tests/shared tests/test_architecture.py` 全過；`tests/skillgen tests/roguelite tests/sim tests/test_sim_scripts.py tests/test_play_script.py`（799 passed，修完 5 個釘住的測試後單檔重跑皆過）；`tests/engine`（修完 `test_skill_shaping` 後該檔重跑過）；`tests/api tests/cli`（修完 6 個後相關檔案重跑 51 passed，快照重產後 `test_output_snapshots` 以 `UPDATE_CLI_SNAPSHOTS=1` 重寫）。
- 完整 `check.py` 一次跑時在約 65% 有一個失敗，我判斷是規格第 8 項那個已知的不穩定測試（G3a 已修）；沒有拿到失敗名稱，因為整批被我中止，**建議 PM 合併後在機器空閒時跑一次完整 `check.py`**。
- client：`corepack pnpm -C client typecheck` 通過、`corepack pnpm -C client test` 619 passed、`corepack pnpm -C client build` 成功（只有既有的 chunk 大小警告）。

## Commit 列表

| commit | 內容 |
|---|---|
| `0f3d325` | 引擎：`target_collided`、`sacrifice_summon` 與 `sacrifice` 骨架（含組合器低權重）、火器武器技、關鍵字說明與工坊訊息、`LOG_FORMAT` /42 |
| `66f643d` | 內容：15 招新技能、挑釁怒吼加標記、快照與釘住測試的調整、圖示部件與 fixture |
| （本報告） | `docs/phases/Phase3-24c報告.md` |
