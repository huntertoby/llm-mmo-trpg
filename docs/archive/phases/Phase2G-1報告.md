# Phase 2G-1 報告：狀態重複施加 ＋ 技能覆蓋

## 1. Commit 列表

- `Keep the longer remaining duration when a status is reapplied`（handlers.py、test_effects.py）
- `Equip six unused handwritten skills and add content coverage test`（builds.yaml、tests/content/test_coverage.py）
- 本報告 commit

## 2. 驗收逐條結果

1. 通過。`tests/engine/test_effects.py`：`test_reapply_status_keeps_longer_remaining`（4 回合再施加 2 回合 → 仍 4，保留舊來源）、`test_reapply_status_takes_longer_new_duration`（1 → 3，來源改新）、`test_reapply_finite_status_keeps_permanent`（永久 ＋ 3 回合 → 永久）；三者皆斷言 `StatusApplied.duration` 為生效後的值。`StatusApplied` 欄位不變，`LOG_FORMAT` 未升版。
2. 通過。6 個技能皆已裝備（見第 3 節）；`test_every_handwritten_skill_is_equipped_by_a_build_or_unit` 通過，允許清單只涵蓋機制 ID，沒有任何技能被豁免。
3. 通過。`test_every_defined_mechanic_is_used_or_explicitly_allowed`、`test_uncovered_allowlist_is_not_stale`；允許清單見第 4 節。
4. 通過。`trpg battle --map dark_forest --seed 7 --ally-build build_tank,build_warlock,build_healer --log-json f` → `battle replay f`：「重播驗證通過：131 個動作、423 個事件」；另 `bridge_chasm` 種子 3、`build_tank,build_assassin,build_healer`：166 個動作、467 個事件通過。節錄見第 8 節。
5. 通過。`uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（1403 passed）全部通過。複雜度類 noqa 前後皆 23 個（未新增）。

## 3. 技能裝備變更表

| 技能 | 裝備於 | 技能組變化 |
|---|---|---|
| `skill_sunder_strike`、`skill_armor_breaker` | `build_tank`（單手劍，近戰） | 4 → 6 個主動 |
| `skill_fury_stance` | `build_assassin`（匕首，近戰） | 3 → 4 個主動（含姿態） |
| `skill_venom_cloud` | `build_warlock`（火焰法杖，focus） | 4 → 5 個主動 |
| `skill_mark_detonation` | `build_warlock`（搭配 hex_bolt 的 `marked`） | +1 被動 |
| `skill_second_wind` | `build_healer`（法杖） | +1 被動 |

沒有新增 build（仍為 12 個）；`builds.yaml` 開頭註解已補記。所有 build 的主動 ≤ 6、被動 ≤ 2、反應 ≤ 1。

## 4. 覆蓋率測試允許清單（2G-1 結束時）

`tests/content/test_coverage.py` 的 `_UNCOVERED`，皆為 2G-2 要補：
- 骨架：`combo`
- 觸發時機：`on_crit`、`on_natural_20`、`on_kill`、`on_turn_end`、`on_move`、`every_n_hits`
- 反應事件：`hit_by_attack`、`enemy_leaves_adjacent`
- 條件：`target_on_surface`
- 原語：`destroy_object`、`raise_terrain`、`lower_terrain`
- 狀態：`weaken`
- 層數：無

`summon`（骨架停用）不在清單內，因為檢查只算 `enabled: true` 的骨架。狀態 `prone`（由 `knock_prone` 原語產生）與 `shielded`（由 `shield` 原語產生）不是 `apply_status` 的對象，測試以原語使用判定其「技能可施加」，對應表在檔內常數 `_STATUS_VIA_PRIMITIVE`。

## 5. 修改過期望值的測試

無。既有 `test_apply_refresh_and_remove_status` 的期望值不需修改（burning 剩 1 再施加預設 2 → 2）。`sim`、`content`、`cli` 測試沒有因技能組改變而失敗。

## 6. 複雜度類 noqa

前後皆 23 個，未新增。`apply_status` 加了一個小輔助函式 `_outlasts`，未超標。

## 7. 待 PM 決定

1. 重複施加時 `refreshed` 仍定義為「施加前已有同 ID 狀態」（即使保留了舊的較長剩餘），未改語意。
2. 持續時間相等時視為新來源（規格 ≥）；永久狀態再施加永久狀態也改新來源。
3. `weaken` 的覆蓋依規格留給 2G-2；`prone`、`shielded` 用原語對應判定覆蓋，若 PM 希望只算 `apply_status` 請告知。
4. `build_tank` 主動技能增至 6（達上限），法力 20，新增兩技能各耗 3～4 法力，可能壓縮其他技能的使用；未調數值，留給平衡階段。
5. `fury_stance` 裝在 `build_assassin` 而非敵方單位，因此敵方 AI 尚未使用姿態技（未改）。

## 8. CLI 輸出節錄

```
$ trpg battle --map dark_forest --seed 7 --ally-build build_tank,build_warlock,build_healer --log-json b.json
  ★ 術士英雄 的被動「標記引爆」觸發（命中時，深度 1），對象 盜賊1（法力 2）
$ trpg battle --map bridge_chasm --seed 3 --ally-build build_tank,build_assassin,build_healer --log-json c.json
  刺殺英雄 施放「狂怒姿態」（AP 1）→ 影響 1 格
  刺殺英雄 獲得狀態「狂怒姿態」
  坦克英雄 施放「碎甲重擊」（AP 2，法力 4，冷卻 2 回合）→ 影響 1 格
  坦克英雄 以「碎甲重擊」攻擊 盜賊2：d20=19 修正 -1 熟練 +2 = 20（目標 11）→ 命中
重播驗證通過：166 個動作、467 個事件，最終狀態一致（bridge_chasm，種子 3）。
```
