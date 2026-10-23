# Phase 3H-1 報告｜屬性資料＋常駐數值

分支 `worktree-agent-a0f15514bd21eb139`。規格：`docs/phases/Phase3H計畫.md` 第 0、1 節；設計 07 7.2、06 6.10、08 8.11／8.24。

## 做了什麼

1. **屬性詞條**：`content/affixes.yaml` 補 `affix_attr_dex／con／int／wis／wil`，部位同力量（八個部位）、範圍 1～4，與力量同一種 `stat: attribute`，沿用遞減疊加與預算。詞條總數 46 → 51。
2. **雙屬性武器**：`WeaponDef` 新欄位 `attr_mode: mean | max`（預設 `mean`），`weapon_attribute()` 照此算（普攻、反應攻擊、預覽共用同一個函式）。`rule_lines_zh` 多一行「雙屬性：普攻與武器技吃體質、力量，取平均」（由資料產生）。
3. **狀態抵抗**：核對 `statuses.yaml` 全部 `save_attr`，只有易傷不符（意志 → 智力），已改；其餘（緩速敏、定身力、暈眩／冰凍／虛弱／流血／中毒體、嘲諷／沉默意、恐懼／致盲／標記感）與 07 7.2 表一致。說明文字由 `save_attr` 產生，自動跟著變。
4. **心智三分**：新資料 `content/skill_scaling.yaml`（模型 `src/trpg/content/skill_scaling.py`，載入到 `ContentLibrary.skill_scaling`）。法術主題依先後順序比對：意志（召喚、獻祭、詛咒、恐懼、沉默、嘲諷、暗影；`mark` 標籤除外）→ 感知（治療、護盾、輔助、偵測、標記、聖光、自然、增益；`physical／gear／rage` 除外）→ 智力（元素、符文、奧術…）；都不符合的是身體類（力量／敏捷／體質）。武器技看同大類武器的屬性。`load_library` 與 `trpg content check` 逐招檢查，3H-3 可共用。逐招表見下。
5. **配點**：`content/sim/builds.yaml` 的 build_warlock（意志 16）、build_seer（感知 16）、build_summoner（意志 16、智力 14）依新縮放屬性調配，屬性總和不變；其餘 build 主屬性本來就對得上。開發者起始包沒有寫死配點，改為 `new_keyword_run` 省略配點時點在「起始技能最常用的縮放屬性」（無技能時用武器的），並列時取六屬性順序的第一個。
6. **常駐數值**：見下。
7. **測試**：`tests/engine/test_attribute_perks.py`（24 項）、`tests/content/test_skill_scaling.py`（225 項，逐招表格測試）、雙屬性取法（`test_weapons_24a1.py`）、六種詞條全覆蓋（`test_gear.py`）、API 面板資料（`test_runs_api.py`）、前端 `hpPreview.test.ts`。

## 心智三分逐招表（39 招；改意志 32 招）

玩法 PM 粗算約 31 招，實際 32 招改意志（含「喚潮」之外的所有召喚／獻祭／暗影）。效果與數值不變，只改 `scaling_attr`。

| 招式 | 原 | 新 | 理由（主題：標籤） |
|---|---|---|---|
| 殘影之誓 | int | wil | 召喚 |
| 竊取祝福 | int | wil | 暗影 |
| 蔽目黑霧 | int | wil | 暗影、詛咒 |
| 血痕疾行 | dex | wil | 暗影（傳說規則改變） |
| 反咒 | int | wil | 暗影 |
| 蝕心追擊 | int | wil | 暗影 |
| 破魔 | int | wil | 暗影 |
| 恐懼凝視 | int | wil | 恐懼、暗影 |
| 寒祭 | int | wil | 獻祭 |
| 噤聲 | int | wil | 沉默、暗影 |
| 汲命術 | wis | wil | 暗影 |
| 立起圖騰 | wis | wil | 召喚 |
| 喚起骷髏 | int | wil | 召喚 |
| 魂爆 | int | wil | 獻祭 |
| 靈祭 | wis | wil | 獻祭 |
| 喚出爆裂傀儡 | int | wil | 召喚 |
| 精英召喚 | int | wil | 召喚物強化（例外表） |
| 召喚火靈 | int | wil | 召喚 |
| 召喚石像 | str | wil | 召喚 |
| 召喚守護靈 | wis | wil | 召喚 |
| 喚出鷹隼 | wis | wil | 召喚 |
| 召喚冰靈 | int | wil | 召喚 |
| 立起高台圖騰 | wis | wil | 召喚 |
| 立起吸引圖騰 | wis | wil | 召喚 |
| 喚出影魅 | dex | wil | 召喚 |
| 召喚元素之靈 | int | wil | 召喚 |
| 群召 | int | wil | 召喚物強化（例外表） |
| 召喚雷靈 | int | wil | 召喚 |
| 召喚藤蔓 | wis | wil | 召喚 |
| 召喚戰狼 | dex | wil | 召喚 |
| 召喚水精 | wis | wil | 召喚 |
| 挑釁怒吼 | str | wil | 嘲諷＝心智控制 |
| 照明彈 | int | wis | 偵測（揭露） |
| 守護之盾 | con | wis | 護盾 |
| 咒印飛彈 | int | wis | 標記（暗影系，但標記歸感知） |
| 天賜好運 | dex | wis | 護盾 |
| 標記引爆 | int | wis | 標記 |
| 聖域 | int | wis | 治療 |
| 喚潮 | int | wis | 輔助（水、範圍、utility） |

**例外表（`overrides`，7 筆，皆寫理由）**：魔劍斬（力量＋智力雙屬性）、飛行（維持智力）、裂骨印記（物理弱點標記，維持智力）、獵印（標記獵物，維持感知）、移山之力（力量傳說，維持力量）、精英召喚與群召（意志）。其餘身體類法術（捕獸夾、荊棘之膚、盾牆…共 14 招）維持力量／敏捷。

## 雙屬性武器與取法

| 武器 | 主／副 | 取法 | 狀態 |
|---|---|---|---|
| 錘 | 體質／力量（原為力量／體質，順序對調） | mean | 已改 |
| 匕首 | 敏捷／力量 | max | 已改（原為單屬性敏捷） |
| 拳套、鞭、鐮刀、法器珠（副手）、圓盾（副手） | — | — | **資料裡還沒有這些武器／副手**（`weapons.yaml` 只有 14 把可裝備武器），機制（`attr_mode`）已備好，待武器批次進來時直接寫欄位。副手目前沒有縮放屬性欄位，未實作。 |

## 抵抗屬性變更

只有易傷：意志 → 智力（`content/statuses.yaml`）。

## 常駐數值（資料位置與結算點）

資料：`content/rules/core.yaml` 的 `attribute_perks`（`base: 10`、`step: 4`，六條 perk：`attr／kind／per_tier／text_zh`）；模型 `AttributePerks`（`content/rules.py`）。引擎統一由 `engine/rules/perks.attribute_perk(rules, unit, kind)` 讀取（用有效屬性，含狀態與裝備）。

| 屬性 | kind | 結算點 |
|---|---|---|
| 力量 | `collision_dealt`／`collision_taken` | `triggers._collision_damage`：位移來源的加成減受害者的減免，作為每次撞擊 `DamageEffect.flat`；最低傷害仍為 1。物件受撞擊不加成 |
| 智力 | `surface_duration` | `skills/primitives/terrain.create_surface`（技能產生的表面，含預設持續；永久表面不變）、`zones.create_zone`（區域到期輪） |
| 感知 | `reaction_hit` | `reactions._attack_once`（藉機攻擊、監視射擊，`perform_unit_attack(reaction=True)`） |
| 感知 | `reveal_range` | `rules/combat.concealment_problem`（隱蔽目標可選取距離 +）；`traps.detect_traps`（移動抵達與回合開始，自動揭露範圍內敵方陷阱） |
| 意志 | `control_resist` | `control.plan_status`：有 `control_group` 的狀態，守方抵抗屬性值 +（遞減乘在加成之後） |

面板：`HeroOut.attribute_perks`（`AttributePerkOut`：階數、每階說明、目前總效果、下一階門檻），文字由資料的 `text_zh` 產生；前端 `RunHeroPanel` 在屬性列下方顯示（`flow.perkText`）。

## LOG_FORMAT

`trpg-battle-log/58` → `/59`（`runner.py` 文件字串、9 個測試檔的 `/58` 一併改）。重播測試全過。

## 模擬（只量、不調）

`trpg sim matrix --maps open_plain,ruined_fort --seeds 6 --jobs 8`（276 場，35 秒，無異常場次）。未跑改前基線，所以以下只是新狀態的快照：
- open_plain 前三：build_push 100%、build_storm 83%、build_detonator 83%；末段 build_charger／gambler／winged 33%。
- ruined_fort 前三：build_detonator、build_runeweaver、build_fire 皆 100%；末段 build_guardian 33%、build_tank 50%。
- 配點調整過的三個：warlock 勝率 50%（平原）／83%（廢墟）、seer 83%／83%、summoner 83%／83%，沒有出現崩壞。
- 6.8 標準兩項都「不通過」（沒有 build 全地圖前段、13 個 build 沒進過前段），與樣本太小（每格 6 場）有關，非本段造成的結論；平衡待 B10～B13。

## 檢查結果

ruff check／format、mypy（src＋新測試）、import-linter 通過；`pytest tests/engine roguelite cli api content narrative skillgen sim test_architecture`：5360 通過（含 `tests/sim/test_summon_report` 加種子後）；前端 typecheck／vitest（862）／build 通過；`trpg content check` 通過；OpenAPI、`schema.d.ts`、`glossary.json` 已重產（`skill_icons.json` 無變動）。

## 既有測試的調整（AI 軌跡或常駐數值造成）

- `test_collision.py`：測試主角力量設 10（量預設撞擊骰）；`test_skill_primitives／test_temporary_obstacles／test_zones`：施放者智力 13；`test_weapons_24a1`：錘主副屬性對調。
- AI 對戰種子重選：`test_displace_ai`（4 → 3）、`test_gamble`（24 → 28）、`test_basic_actions_cli`（98 → 222）、`test_summon_report`（seeds 2 → 5）。
- `test_skills_cli` 專精文字（恐懼凝視現在看意志）、`test_gear_api`／`test_equipment_content`（詞條數 51）。

## noqa

無新增。

## 待 PM 決定

1. 拳套、鞭、鐮刀、法器珠（副手）、圓盾的雙屬性：資料裡沒有這些武器，等武器批次再填；副手要不要有縮放屬性欄位？
2. 咒印飛彈、標記引爆（暗影＋標記）依「標記＝感知」改感知；若想歸詛咒（意志），改 `skill_scaling.yaml` 的 `tags_none` 或加例外即可。
3. 挑釁怒吼（力量 → 意志）、喚潮（智力 → 感知）、守護之盾（體質 → 感知）等 7 招改動超出「約 31 招改意志」的範圍，請確認。
4. 感知「看見陷阱」原本沒有距離機制，這次做成「範圍內敵方陷阱自動揭露給己方陣營」（移動抵達與回合開始檢查，無視線限制），可否接受？
5. 力量對物件的撞擊傷害沒有加成、對撞擊的最低傷害維持 1。
6. 面板常駐數值用主角的基礎屬性（不含裝備／狀態，戰鬥中引擎用有效屬性）；測試模式有裝備時兩者會差一點。
7. 模擬未跑改前基線；若要比較，請在合併前由 PM 指定樣本。
8. 面板沒有在真機瀏覽器看過（只有 API／渲染測試），驗收時請看一眼。
