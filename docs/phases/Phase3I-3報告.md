# Phase 3I-3 報告：魔劍士方案 A＋魔導劍

規格：`docs/phases/Phase3I計畫.md` 3I-3 列；設計 06 6.10（#46）、08 8.11；美術 `docs/art/魔導劍.md`。

## 逐條對照

| 規格項 | 做法 |
|---|---|
| 稀有以上武器技可帶心智第二屬性、取平均、費用不雙扣 | `core.yaml` `dual_scaling_min_rarity: rare`（原 epic）；`SkillDef.scaling_value`：武器技有 `secondary_scaling_attr` 時＝（武器縮放值＋心智屬性值）// 2；命中（`skill_profile`）、傷害、控制抵抗（`skill_scaling_value`）全走同一個值；對抗屬性仍是武器主屬性；費用不變 |
| 組合器與 LLM 依「第二高與最高差 ≤ 4、機率 30%」 | `skill_scaling.yaml`：`dual_max_gap: 4`、`weapon_second_attrs`；`skill_composer.yaml` `dual_permille: 300`。組合器抽籤後（武器技也抽），給主角屬性時 `retarget_scaling` 依差距決定留或拿掉並換成主角最高的心智屬性；LLM 提議在 `to_skill_def` 用 `grant_dual`（技能 ID 決定的確定性 30% 抽籤） |
| 魔劍斬改近戰武器技＋智力、移除例外 | `skill_arcane_blade.yaml`：weapon／melee／secondary int／耐力 10／倍率 2.4（過預算下限，初值）；刪 `skill_scaling.yaml` 的 override |
| 驗證器接 3H-7 範圍檢查 | `scaling.weapon` 只檢查主屬性；`scaling.range` 檢查武器技第二屬性必為心智、法術第二屬性在 `secondary_range`、身體類法術不得有第二屬性 |
| 工坊第二屬性選單 | `option_scaling.py`：稀有以上、武器技列心智屬性、法術列範圍；選了會讓試組失敗者標 `info.unavailable_zh`（3-48h 機制） |
| 卡片算法句 | `formula_lines_zh`：「力量／智力（取平均）與智力（取平均）」＋「目前 +N」；`scaling_detail`、`scaling_attrs`、屬性影響清單、候選 `follows_attr` 同步 |
| 3H-7 留下 | 身體類法術不給第二屬性（`secondary_range` 為空；組合器、fit、驗證器、工坊）；修正規則 `add_element` 與 `on_hit_effects` 進 `ScalingFacts` 當主題訊號（雷之手＝智力、神聖附魔＝感知） |
| 武器技效果句寫實際屬性名 | `scaling_label(skill, lib)`：武器技寫武器大類主屬性（「＋力量加成」），帶第二屬性寫「力量／智力」；對抗句用 `contest_label`（只寫主屬性） |
| 魔導劍武器資料與外觀 | `weapons.yaml` `arcane_blade`（1d8、力量／智力 mean、單手、無特性、`look: sword／arcane／steel`）；`appearance.yaml` 加 `arcane` 形制；`paperdoll.ts` 的 `drawBlade` 加 arcane（源晶槽外光、元素色、三符文、黃銅齒輪、冷灰劍身）；`gearIcon.ts` `D.sword` 加 arcane；不認得 arcane 退回一般劍；匯出 `gearAppearance.json`、`glossary.json`；`build_blank_arcane_blade` |
| 行為一致測試 | `tests/engine/test_arcane_blade_3i3.py`（普攻與武器技 × 武器 × 第二屬性，`damage_dealt` ＝ 卡片「目前 +N」；縮放值、對抗、命中表格） |

## 測試與檢查

- 新測試：`tests/engine/test_arcane_blade_3i3.py`、`tests/skillgen/test_dual_3i3.py`、`client/src/render/arcaneBlade.test.ts`（正面、背面、東西側面、有無元素、搭法書／法器珠、未知 form 退回）。
- 更新的舊測試：雙屬性稀有度（epic→rare）、武器技第二屬性（不再一律禁止）、魔劍斬、build_push 重播種子 1→0、`run auto` 進化種子 [6,7]→[4,5]、CLI 快照、`skill_icons.json`。
- ruff check／format、mypy、lint-imports（7 kept）通過；pytest（engine、content、skillgen、llm、roguelite、narrative、api、sim、shared、架構、`-m "slow or not slow" tests/cli`）全過；vitest 961、build 通過；重播 `build_blank_arcane_blade` open_plain 種子 3 一致（130 動作）；排版煙霧檢查 1600×900、800×600、底部最矮 全 PASS（先 `localStorage.clear()`）；紙娃娃一覽（dev）目視看過魔導劍（無元素藍紫、火元素橘）。
- `LOG_FORMAT` 未更動（紀錄格式沒變）；OpenAPI 無差異。

## 待 PM 決定

1. 魔劍斬耐力 10、倍率 2.4、史詩、射程為武器射程（原法術射程 2）皆為過預算下限的初值，未經模擬。
2. 隨機組合器的 `dual_permille` 由 250 改 300；有主角屬性時實際機率 ＝ 30% × 差距條件（法術技也套同一條差距規則）。
3. 沒有主角屬性（工坊隨機、無 hero 的組合器）不套差距規則，只依 30% 抽籤。
4. 魔導劍預設劍身色用冷灰 `#8a93a8`（與鋼色混 70%），`color` 有指定時照指定。
5. 側面沿用同一個 `drawBlade`（正面畫法），未另做側面專屬造型。
6. 雙屬性稀有度由史詩降到稀有同時影響法術技（#46 原文「稀有以上」）。
7. 武器技專精與第二屬性仍互斥；開局自動配點只看主屬性（沿 3I-1 待決 #6，魔導劍已平均分配）。
8. 與 3-50 的合併：我改動 `trpg.skillgen.scaling`、`validate._scaling_range_violations`、`random_composer._with_scaling_extras`、`proposal.to_skill_def` 與 `option_scaling`；代價相關程式未動。
9. `client/src/dev/dollGallery.ts` 多放兩把魔導劍（開發用）。
