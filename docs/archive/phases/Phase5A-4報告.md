# Phase 5A-4 完成報告：遇敵展開戰鬥與城鎮服務

> 實作者：implementer agent（2026-11-02）。規格：`docs/phases/Phase5計畫.md` 第 9 節（先寫入規格、commit `cfa0c131`，再實作；和 5B-1 合併後 5B-1 是第 8 節、本段改為第 9 節，「之後各段規格」改為第 10 節）。
> 含開發 PM 追加的兩項（玩法 PM 定，#81 練等前提）：**A. 敵人依地點建議等級成長**、**B. 符籙師改純控制**。
> 只動 `src/trpg/world/`、`src/trpg/content/world_rules.py`、`content/world/rules.yaml`（末尾加 `battle`、`enemy_growth` 兩塊）、`content/units/sect_talisman_caster.yaml`、`content/world/enemies.yaml`（雷符師一行）、`tests/world/`、`tests/content/test_world_enemies.py`。沒有動引擎、roguelite、API、前端、`trpg-run` 與戰鬥紀錄格式（`LOG_FORMAT` 不變）。

## 1. 交付

| # | 項目 | 檔案 | commit |
|---|---|---|---|
| 1 | 5A-4 詳細規格 | `docs/phases/Phase5計畫.md` 第 9 節 | `cfa0c131` |
| 2 | 開戰、勝負回寫、撤退、城鎮休息、換技能、傳送、敵人成長、符籙師改版 | `src/trpg/world/{battle,town,common}.py`（新）、`actions.py`、`state.py`、`step.py`、`world_rules.py`、`rules.yaml`、content 兩檔 | `0accb734` |
| 3 | 測試（開戰設定、敵人成長、戰鬥回寫、城鎮服務、日誌重播、全地點 smoke） | `tests/world/test_{battle_setup,enemy_growth,fight,town}.py`、`test_replay.py`、`helpers.py` | `ee34bdef` |
| 4 | 合併 main（5B-1）解衝突 | `actions.py`、`state.py`、`step.py`、計畫 | 合併 commit |
| 5 | 本報告 | `docs/archive/phases/Phase5A-4報告.md` | 最後一筆 |

### 1.1 新的世界動作與事件（`trpg.world.actions`）

| 動作 | 做什麼 | 事件 |
|---|---|---|
| `retreat` | 看了陣容不打，退回出發地點（不扣東西、不擲骰） | `retreated` |
| `fight(steps)` | 用遭遇的設定與 `battle_seed` 開戰、套用步驟，戰鬥必須已結束；回寫 | `battle_started`、`battle_ended`、`leveled_up`、`location_cleared`／`defeated` |
| `rest` | 城鎮休息：HP、法力、耐力回滿，補給補到至少初值 | `rested` |
| `loadout(skills)` | 城鎮或營火換技能（擁有的、不重複、欄位上限） | `loadout_changed` |
| `teleport(region)` | 城鎮 → 去過的其他區小鎮；傳送點 → `gate_to` 區的小鎮 | `teleported` |

狀態新欄位（都有預設值，`trpg-char/1`、`trpg-world/1` 格式字串不變，舊檔照讀）：`EncounterResult.from_location`、`CharacterState.bench`、`fatigued`、`attribute_points`、`visited_towns`。

### 1.2 給 5A-5 的接點（`trpg.world.battle`）

- `prepare_battle(library, char) -> PreparedBattle`（`setup`、`seed`、`lineup`、`enemy_level`、`hero_hp`）：API 開戰與「看陣容」直接用；`setup` 可以照原型的 `BattleSession` 方式一步一步打，打完把步驟送 `fight`。
- `auto_steps(library, char)`：效用 AI 代打整場（測試、smoke、之後模擬用）。

## 2. 流程

```
移動（travel）── 遇敵擲骰 ──► pending_encounter（含 from_location、battle_map、battle_seed、天氣）
                                 │
                 看陣容：prepare_battle → roll_lineup ＋ 依 level_min 成長的敵人範本
                                 │
              ┌──── retreat ─────┴──── fight(steps) ────┐
              ▼                                          ▼
      回出發地點（不扣東西）            begin_battle(setup, battle_seed) ＋ apply_step × N
                                                         │ 戰鬥結束
                                   ┌──── 我方勝 ─────────┴──── 沒打贏（全滅／輪數上限）──┐
                                   ▼                                                    ▼
            HP 照戰後（倒下以 1 繼續）、法力不回、耐力滿          回本區小鎮、HP 滿、耐力滿、法力照戰後
            ＋100 經驗、升級（屬性點累積、最大 HP 增量加到目前）   不給／不扣經驗、fatigued＝True
            camp 種類寫「已清空」（1800 秒後重生）
                                   └──────────── 清掉 pending_encounter ─────────────────┘
城鎮：rest（回滿＋補給）、loadout、teleport；營火（camp 動作）：loadout
```

**開戰設定**（計畫 9.3）：地點的 `battle_maps`（沒有時從區域 `map_pool`、非 Boss 類型，以 `"{battle_seed}:map"` 抽）→ 換皮成遭遇的區域（`region`＝`cloud_ridge`、`look`＝該區預設外觀，機制不動）；天氣＝遭遇的天氣；我方＝主角（等級 HP 加成、目前 HP／法力／耐力；疲憊時開場 HP ≤ 80%）＋原型 2 名標準隊友；敵方＝`roll_lineup` → `lineup_templates` → `grow_enemy`。

**敵人成長（追加 A）**：等級＝地點 `level_min`；每級 +2 屬性全加在範本最高屬性、HP ＋ 基礎 × 5% ×（等級−1）（和主角同一個 `level_hp_bonus`）、技能階級照 07 7.6（1～3 級 1 階、4～7 級 2 階、8～10 級 3 階；表在 `rules.yaml` 的 `enemy_growth`），低於目標階級的技能用 roguelite `at_run_tier` 重配成 `<原 ID>_t<階級>`（反應規則引用的 ID 一起改名），重配技能以 `Ruleset.with_skills` 加進該場規則包；`level` 欄位＝等級。例：劍冢（5 級）的劍陣弟子：敏捷 14→22、HP 26→31、`skill_shoulder_strike_t2`。

**符籙師（追加 B）**：`sect_talisman_caster` 技能＝寒鎖（定身符）＋噤聲 `skill_hush`（沉默 1 回合＝封符）；雷符師變體 `skill_swaps: {skill_hush: skill_static_palm}`，＝寒鎖＋靜電掌（雷符），武器仍是雷電法杖。

## 3. 可重播證明

- `fight` 的步驟寫在世界動作日誌（`trpg-wlog/1` 多一種動作，格式字串不變）。重播時 `prepare_battle` 只依「角色快照＋遭遇＋內容庫」重建設定，用同一個 `battle_seed` 開戰、套用同樣的步驟，得到相同的戰鬥結果與回寫。亂數只來自 `battle_seed`（地圖 `:map`、陣容 `:lineup`、引擎本身）與世界串流；`trpg.world` 內沒有時間、`random`、`uuid4`、`hash()`（`tests/test_architecture.py` 照舊通過）。
- `tests/world/test_replay.py::test_replay_with_battle_and_town`：移動 → 遇敵 → 撤退 → 再遇敵 → 戰鬥 → 回小鎮休息 → 換技能，日誌寫出再讀回（`dumps_log`／`loads_log`）重播兩次，世界與角色 JSON 逐字相同、事件相同，且等於現場套用的結果。
- `test_fight.py::test_fight_is_deterministic`：同一場打兩次，角色、世界、事件完全相同；步驟不完整（沒打完）或多一步 → `WorldActionError`。
- `test_fight.py::test_every_encounter_location_battle_runs`：雲嶺 16 個有遭遇表的地點，敵人照地點等級成長後都能用引擎打完一場（含 2 階重配技能）。
- 原型重播：`uv run trpg battle --map swamp --seed 7 --log-json …` ＋ `trpg battle replay` 通過（見第 6 節）。

## 4. 代決（開發 PM 定，最保守預設）

| # | 事項 | 代決 |
|---|---|---|
| 5A4-1 | 沒有戰鬥地圖的地點（祭壇、遺跡、異象、Boss 據點）遇敵用哪張圖 | 區域地圖池（非 Boss）以 `{battle_seed}:map` 均勻抽 |
| 5A4-2 | 換皮時地圖原本的單張 `look` 覆寫 | 換成該區預設外觀 |
| 5A4-3 | 營地的勝利條件輪替（9.6.2） | 先用地圖預設（全滅） |
| 5A4-4 | 3 人隊伍的隊友 | 5C-1 前用原型 2 名標準隊友（`sim_companion_fighter`、`sim_companion_archer`） |
| 5A4-5 | 敵人等級取地點等級範圍的哪一點（追加 A） | `level_min`（例：北坡獵場 4～5 → 4） |
| 5A4-6 | 敵人每級 +2 屬性加在哪 | 全加在範本最高屬性（同分取 str→wil 第一個） |
| 5A4-7 | 輪數上限沒打完 | 當全滅處理 |
| 5A4-8 | 全滅「回最近的小鎮或營火」 | 先只回本區小鎮 |
| 5A4-9 | 已清空的地點遇敵 | 機率 0（擲骰照擲，亂數消耗不變） |
| 5A4-10 | 已清空寫入與重生 | 只有 `camp` 種類；1800 秒（遊戲內 1 天）後重生；在 `rules.yaml` 的 `battle` |
| 5A4-11 | 城鎮休息的費用與補給 | 免費；補給補到至少 `supplies.start`（5），多的不扣 |
| 5A4-12 | 傳送點 | 城鎮到「去過的」其他區小鎮；傳送點到 `gate_to` 區的小鎮；`new_character` 記起始區、走進小鎮也記 |
| 5A4-13 | 經驗與等級（Q8） | 每場 100、沿用原型門檻（`roguelite.yaml`，到 6 級）；升級屬性點先累積在 `attribute_points` |
| 5A4-14 | 「封符」（追加 B） | 現成 `skill_hush`（噤聲：沉默 1 回合，1 階、法器） |

## 5. 待 PM 決定

1. **主角升階重配**：07 7.6 的技能階級（4、8 級升階）在大世界角色還沒做——`CharacterState` 沒有生成技能欄位，roguelite 的 `sync_skill_tier` 要 `RunState`。另外原型的 `offer_tier_by_level`（[1,1,2,2,3,3]）和 07 7.6（1～3／4～7／8～10）不同；敵人用 07 7.6（`rules.yaml` 的 `enemy_growth`），主角之後要用哪一張需定。
2. **屬性點分配、靈感點、閃現／重閃／溶掉／傳承、立誓**：城鎮與營火的這些服務本段沒做（`attribute_points` 只累積）；建議併進 5A-5 或另排一小段。
3. **經驗曲線與 10 級上限**：原型門檻只到 6 級；7.8「第 7～8 天到 10 級」的曲線、各來源經驗、精英多給經驗與獎勵（9.6.6「打贏照精英給」）待模擬或 5D。
4. **戰利品**：#98「這場沒有戰利品」已照做（輸了什麼都不給），打贏的掉落在 5D-2。
5. **全滅回營火**：#98 是「最近的小鎮或營火」，本段只回小鎮；要不要回最近一次紮營的營火待定。
6. **已清空的範圍與時間**：精英巢穴、懸賞（「先打倒的人拿大獎」）的清空與重生交 5F-1；重生 1800 秒是初值。
7. **敵人成長數值**：等級取 `level_min`、屬性全加最高項是保守做法；5 級敵人 HP 只 +20%，是否夠強需模擬（追加 A 原話「和主角一樣的成長」照做）。
8. **3 人隊伍**：標準隊友是原型的模擬隊友，5C-1 換傭兵與影子時 `prepare_battle` 的隊友來源要改。

## 6. 檢查結果

合併 main（5B-1，`96694c1d`）之後：

| 檢查 | 結果 |
|---|---|
| `ruff check .`、`ruff format --check .` | 通過 |
| `mypy`（strict，992 檔） | 通過 |
| `lint-imports` | 9 條契約全部 KEPT |
| `pytest tests/world tests/content tests/test_architecture.py -n 8` | 1994 passed |
| `pytest tests/cli -m "slow or not slow" -n 8` | 180 passed |
| 原型重播 `trpg battle --map swamp --seed 7` ＋ `replay` | 通過（88 個動作、313 個事件，最終狀態一致） |
| 世界日誌重播（`test_replay_with_battle_and_town`） | 通過 |

`trpg content check` 的摘要沒變（`rules.yaml` 摘要不含新欄位），CLI 快照不用重產。`C901` 沒有超標、沒有新增 `# noqa`。
