# Phase 3I-6 報告：臨時附魔與元素優先順序（玩法決定 #52）

## 做了什麼

- **狀態欄位 `attack_element`**（`StatusDef`，資料在 `content/statuses.yaml`）；新狀態 `infused_fire`（火焰附魔）、`infused_holy`（神聖附魔），3 回合、`budget_points: 6`、`min_rarity: rare`。同時只有一個附魔：施加新的先移除舊的（`StatusRemoved` 原因 `replaced`），所以「後施放覆蓋先施放」；同一個附魔再施放則刷新。
- **純函式** `trpg.engine.attack_element.resolve_attack_element(sources, is_basic, skill_element)`；`attack_element_sources`／`effective_attack_element` 負責從單位蒐集來源。武器元素詞條的來源是 `weapon_affix_element(unit)`（目前回傳 `None`，3K-1 接上）；普攻附加詞條沿用既有 `gear_attack_element`。
- 接上：普攻（`modifiers.damage_element` 的 `attack`）、武器技（`damage_parameters`，本身有元素的武器技不受影響）、普攻連鎖傷害（`weapon_traits`）、普攻關鍵字（`attack_keywords`）。
- 2 招示範技能：`skill_fire_enchant`（自己）、`skill_holy_weapon`（友方，射程 4）。預算 6.00 ÷ 7.84 ＝ 76.5%（合格 70～100%）。關鍵字：火焰附魔列入「點燃」製造；神聖附魔比照神聖傷害，列入「潮濕」利用（暫定）。兩招由技能池給出（`tests/content/test_coverage.py` 的 `_POOL_ONLY`），沒有改 build。
- 外觀：`UnitView.attack_element`（目前生效的普攻元素，物理為 `None`）→ 前端 `DollInput.attackElement` → 主手改用元素色；兩個狀態各有圖樣與顏色。`openapi.json`／`schema.d.ts` 已更新。
- `LOG_FORMAT` `/66` → `/67`。

## 規則對照表

| 規則（06 6.10） | 實作／測試 |
|---|---|
| 普攻：附魔 ＞ 普攻附加 ＞ 武器元素詞條 ＞ 武器本身 ＞ 物理 | `PRIORITY_TABLE` 前 10 列 |
| 無元素武器技：附魔 ＞ 武器元素詞條 ＞ 武器本身 ＞ 物理（不看普攻附加） | 表格中 `is_basic=False` 列 |
| 有元素的武器技不受影響 | 表格 3 列＋`test_a_weapon_skill_with_its_own_element_ignores_the_enchant` |
| 兩個附魔後施放覆蓋 | `test_the_later_enchant_replaces_the_earlier_one` |
| 法杖被附魔，結束回到原元素 | `test_the_staff_element_returns_after_the_enchant_ends` |
| 互動只看最後元素（火焰點燃油） | `test_fire_enchant_ignites_oil_with_a_basic_attack` |
| 卡片與實戰一致 | `test_enchant_changes_a_weapon_skill_without_its_own_element`（`damage_parameters` ＝ 實際傷害元素） |
| 自己／友方附魔技能 | `test_fire_enchant_targets_self_and_holy_weapon_targets_an_ally` |
| 外觀元素色 | `client/src/render/attackElement.test.ts` |

測試：`tests/engine/test_attack_element.py`（33 個）、vitest 新增 2 個。

## 待 PM 決定

1. **行為變更**：普攻附加詞條現在優先於「武器本身元素」（原本法杖有元素時詞條不生效，`test_gear_g2` 舊斷言已改）；並且普攻附加詞條優先於修正規則的 `add_element`（原本相反，只在兩者都存在時不同）。依規格表照做，若要保留舊順序請指示。
2. **隨機組合器**：兩個附魔狀態有 `budget_points` 且有益，隨機組合器與技能工坊的狀態選項會自然包含它們（未特別排除）；若不想讓隨機技能長出附魔請告知。
3. 其餘 6 種元素的附魔狀態未做（規格只要 2 招示範）；擴充只需加狀態資料。
4. 武器本身元素不顯示在 `attack_element` 之外的地方；`UnitView.attack_element` 也會對法杖回傳其本身元素（與武器外觀相同，無害）。
5. `LOG_FORMAT /67` 若與其他 agent 衝突，合併時由 PM 處理。
