# Phase 3-24b1 完成報告：關鍵字推導、技能池、補技能、兩種新修正

> 實作者：implementer（sonnet）。規格：`docs/phases/Phase3計畫.md` 26.1、`docs/design/06-技能.md` 6.27、`docs/design/08-裝備.md` 8.21.4.2。
> 分支：`worktree-agent-aa5f71a2476a5e00d`（從 main 的 `dcfa071` 分出），未 push、未合併。

## 1. Commit 列表

| commit | 內容 |
|---|---|
| `245bc05` | 兩種新修正：治療量、召喚物數值（引擎、預算、敘事文字、測試） |
| `39f13ec` | 關鍵字推導表與推導函式、`keyword.required` 驗證、技能池、組合器指定關鍵字、5 個補池技能、`SkillCard.keywords`、工坊 `keywords`、OpenAPI 快照 |
| `58cca59` | 前端：技能卡、技能列浮動卡、工坊即時檢查顯示「製造：…｜利用：…」；修正部件圖示 |
| `9db685f` | 推導表規則加註解（專屬／通用／暫定）、`content/README.md` 一列、截圖 |

## 2. 驗收逐條

| # | 驗收項目 | 結果 | 證據 |
|---|---|---|---|
| 1 | 推導表每個關鍵字至少一個正例 | 通過 | `tests/skillgen/test_keywords.py::test_derivation_positive_examples`（27 個正例，參數化）、`test_every_keyword_has_a_positive_example_for_makes_and_uses`（10 個關鍵字的製造與利用各至少 1 個）、`test_every_keyword_is_made_and_used_by_shipped_skills`（內容庫手寫技能也都能示範製造與利用）、反例 `test_plain_physical_damage_has_no_keyword` |
| 2 | 每招技能至少一個關鍵字：內容庫全部手寫技能 | 通過（163／163） | `test_every_shipped_skill_has_at_least_one_keyword`、`test_every_shipped_skill_passes_the_validator_including_keywords` |
| 3 | 隨機組合器種子 0–49 | 通過 | `test_composer_seeds_0_to_49_all_have_a_keyword[0..49]`；另跑種子 0–299 無一失敗、10 個關鍵字都出現 |
| 4 | 工坊完成的技能 | 通過 | 驗證器新增 `keyword.required`（`validate_skill`），工坊 `check_draft` 沿用：`test_workshop_marks_a_keywordless_complete_draft_illegal`；草稿即時推導 `test_workshop_draft_keywords_appear_as_the_draft_grows` |
| 5 | 各池 ≥ 3 招 1 階技能（過預算） | 通過 | `test_each_pool_has_at_least_three_tier_one_starter_skills[10 個關鍵字]`（起始技能：1 階、普通或稀有、主動技；逐招 `validate_skill == []`）；池表見第 4 節 |
| 6 | 組合器指定關鍵字 | 通過 | `test_composer_can_require_each_keyword[10 個關鍵字]`（各 3 個種子）、`test_composer_with_a_keyword_is_deterministic_and_leaves_plain_seeds_alone`、`test_composer_rejects_an_unknown_keyword`、`test_composer_keyword_works_with_other_constraints` |
| 7 | 兩種新修正（各一組測試） | 通過 | `tests/engine/test_heal_summon_modifiers.py`（10 個）：治療量加倍／減半／加總／只套用符合的技能／聖光雙效的治療／範圍檢查；召喚物最大 HP／傷害骰／加總／套用對象／範圍檢查。另 `tests/content/test_modifier_schema.py::test_every_change_kind_has_a_valid_example` |
| 8 | vitest（關鍵字顯示） | 通過 | `client/src/ui/keywords.test.ts`（4 個）、`client/src/render/skillIcon.test.ts` 新增「治療量與召喚物數值…有專屬部件」；`corepack pnpm -C client test`：52 檔 559 個通過 |
| 9 | `check.py` 全過 | 通過 | ruff、format、mypy、lint-imports、pytest（3583 passed）、client typecheck、client test 全部通過 |
| 10 | `pnpm build` 成功 | 通過 | `corepack pnpm -C client build`：built |
| 11 | 截圖 `docs/phases/img/3-24b1-*.png` | 完成 | `3-24b1-workshop-empty.png`（草稿剛開始：「關鍵字：還沒有」）、`3-24b1-workshop-card.png`（即時檢查與卡片預覽：製造：無｜利用：潮濕）、`3-24b1-keyword-tip.png`（關鍵字說明框）、`3-24b1-skillbar-card.png`（戰鬥中技能列浮動卡：製造：無｜利用：潮濕、倒地）。以 `trpg serve --port 8124`（不是 8000）＋瀏覽器窗格擷取，縮放為 800 px 寬 |
| 12 | 遊戲不定義流派 | 通過 | 推導表與所有顯示文字沒有流派名稱：`test_no_keyword_is_a_school_or_theme`（掃推導表內容，12 個測試流派名稱不得出現） |

## 3. 推導表摘要（`content/skill_keywords.yaml`）

- 10 個關鍵字，共 117 條規則：**專屬 79、通用 22、暫定 16**（註解標示於各規則行尾）。
- 規則格式：一條規則恰好一種來源（`effect`／`condition`／`trigger`／`shape`／`change`），再用參數縮小範圍（`status`、`surface`、`element`、`object`、`stack`、`rule`、`on_hit`、`tag`、`skill`、`affects`、`applies_to`、`unconditional`），另可加技能層級篩選 `weapon_req`、`category`。載入時跨檔案檢查所有引用都存在（`library._check_keywords`）。
- 推導函式純函式：`trpg.skillgen.keywords.derive_keywords`（技能）、`derive_draft_keywords`（組到一半的工坊草稿，逐步解析能解析的部分）。放在 `trpg.skillgen`（`trpg.content` 不得匯入它）；schema 在 `trpg.content.skill_keywords`。

| 關鍵字 | 製造（專屬規則摘要） | 利用（專屬規則摘要） | 規則數（製造／利用） |
|---|---|---|---|
| 點燃 | 燃燒狀態、火元素傷害、火／油表面、火區域、火炸彈、火印、投擲火物件、加火元素修正 | 條件「目標燃燒中」、站在火／油上、消耗燃燒、「燃燒」觸發、本回合施放過火系 | 9／8 |
| 潮濕 | 水表面、水區域 | 條件「目標在水上」、進入水面觸發、本回合施放過水系；（通用）治療、護盾、淨化、神聖傷害、治療類修正 | 2／10 |
| 帶電 | 雷元素傷害、雷炸彈、雷印、加雷元素修正、靜電與超載層數 | 連鎖形狀、消耗靜電層數、站在自己的雷印上、本回合施放過雷系 | 6／4 |
| 冰凍 | 冰凍狀態、冰傷害、冰面、冰牆、冰印 | 條件「目標冰凍中」、站在冰面上、消耗冰凍 | 5／3 |
| 倒地 | 擊倒、推倒（topple）、直線衝撞擊倒、倒地狀態 | 條件「目標倒地中」、消耗倒地；（通用）近戰武器傷害技；（暫定）暴擊觸發、狂怒姿態 | 4／5 |
| 撞擊 | 推擊、拉扯、衝鋒、直線衝撞、推擊距離修正；（通用）障礙物、投擲物件、推動物件的規則改變 | 撞擊觸發；（暫定）受傷觸發、堅壁姿態 | 8／3 |
| 標記 | 被標記狀態、刻印、揭露、監視狀態；（暫定）沉默／恐懼／嘲諷／中毒、血痕規則、複製技能、範圍 +1、無條件的全攻擊傷害修正 | 條件「目標被標記」、引爆刻印、站在自己的刻印上；（通用）消耗任何狀態 | 12／4 |
| 高處 | 升高地形、降低地形、跳躍、給飛行技能；（暫定）傳送他人、任意交換、移動後觸發、給 AP | 條件「居高臨下」；（通用）遠程武器傷害技、穿透修正 | 8／3 |
| 隱蔽 | 隱蔽狀態、煙／黑暗表面、暗影傷害、放置陷阱 | 條件「自身隱蔽」、條件「背刺」 | 5／2 |
| 召喚物 | 召喚、殘影規則 | 條件「身旁有友方」、治療量／召喚物數值修正；（通用）對友方生效的效果（召喚物也算友方） | 2／14 |

### 3.1 推導的歸類（163 招手寫技能）

每招技能依「最強」的規則歸類：專屬 94 招、通用 53 招、暫定 16 招。專屬以外的 69 招如下（技能 ID 省略 `skill_` 前綴）：

**通用規則**（53 招）
- 近戰武器傷害技 → 利用倒地（近戰攻擊倒地者有優勢，`statuses.yaml` prone）：`all_in`、`ambush_stab`、`armor_breaker`、`berserker_rage`、`blood_sacrifice`、`charging_strike`、`cleave`、`decoy_swap`、`encircled_sweep`、`execute`、`first_strike`、`parting_slash`、`pick_off`、`pincer_strike`、`reckless_lunge`、`rending_strike`、`riposte`、`rupture`、`shadow_whirl`、`shield_bash`、`shoulder_strike`、`sunder_strike`、`whirlwind`、`wild_blade`（24）
- 遠程武器傷害技、穿透修正 → 利用高處（高打低命中 +2，`core.yaml` `height_hit_bonus`）：`armor_piercing_arrow`、`covering_fire`、`piercing_shot`、`sniper_shot`、`timber_piercer`（5）
- 治療、護盾、淨化、神聖傷害、治療類修正 → 利用潮濕（08 8.21.4.2「潮濕表面治療」）：`bloodlust`、`holy_burst`、`renewal`、`sanctuary`、`second_wind`、`self_mending`、`steady_breath`（7）
- 障礙物、投擲物件 → 製造撞擊：`blazing_hurl`、`stone_wall`、`telekinetic_hurl`、`thorn_wall`（4）
- 放置陷阱 → 製造隱蔽（陷阱藏在落葉底下）：`bear_trap`
- 消耗任何狀態 → 利用標記（引爆）：`rupture`、`toxin_burst`
- 對友方生效的效果、身旁有友方 → 利用召喚物（召喚物也算友方）：`focus_surge`、`guard_swap`、`quicken_tide`、`rallying_cry`、`renewal`、`resurrection`、`shoulder_strike`、`soul_bond`、`stand_firm`、`tailwind`、`undying_oath`、`vigil_call`、`war_hymn`

**暫定規則**（16 招，沒有真實機制可接，先歸類以滿足「每招至少一個關鍵字」，建議之後換成真實內容）
- 製造標記：`bloodwake_stride`（血痕）、`dread_gaze`（恐懼）、`hush`（沉默）、`taunting_roar`（嘲諷）、`venom_cloud`（中毒）、`lingering_roar`（範圍 +1）、`mirror_cast`（複製技能）、`war_avatar`（無條件全攻擊傷害 +18%）
- 製造高處：`banish`（傳送他人）、`void_swap`（任意交換）、`fleet_foot`（移動後觸發）、`time_surge`（給 AP）
- 利用倒地：`crippling_crit`（暴擊觸發）、`fury_stance`（狂怒姿態）
- 利用撞擊：`bulwark_stance`（堅壁姿態）、`thorn_skin`（受傷觸發）

### 3.2 「不通過的手寫技能」處理紀錄

- 只用最初的專屬規則時，158 招手寫技能中有 78 招沒有關鍵字（近戰與遠程武器技、治療與護盾、控制、位移、姿態、被動、傳說、修正……）。
- 處理方式：**全部以補推導規則解決，沒有修改任何既有技能的內容**（不動平衡、不影響模擬回歸）。補上的規則就是上面的通用規則與暫定規則，以及少數專屬規則（煙霧／黑暗、背刺條件、升高與降低地形、神聖傷害）。
- 已經有關鍵字的技能不受通用規則影響（通用規則只是讓它多歸進幾個池）。
- 新增的 5 招（第 5 節）都是專屬規則。

## 4. 各池招數表

「起始技能」＝1 階、普通或稀有、主動技（`keywords.is_starter_skill`）；括號為該池全部技能數（含被動、修正、傳說、2 階以上）。製造／利用欄只列起始技能。

| 池 | 起始技能數（全部） | 製造 | 利用 |
|---|---|---|---|
| 點燃 | 8（21） | `ash_harvest`、`death_spiral`、`ember_trail`、`fire_arrow`、`fire_bolt`、**`kindling_strike`**、`oil_flask`、`shatter_blast` | **`kindling_strike`** |
| 潮濕 | 9（21） | **`downpour`**、**`holy_water`**、`summon_tide` | `charged_cleave`、`conductive_strike`、`guardian_aegis`、**`holy_water`**、`parry_riposte`、`purify`、`renewal` |
| 帶電 | 8（13） | `arc_follow_up`、`armor_break_combo`、`cluster_bolt`、`conductive_strike`、`overcurrent`、`rune_thunderbolt`、`static_palm`、`thunder_sigil` | `arc_follow_up`、`rune_thunderbolt` |
| 冰凍 | 4（5） | **`flash_freeze`**、`frost_shackle`、`ice_wall`、**`shatter_ice`** | **`shatter_ice`** |
| 倒地 | 31（39） | `bone_crusher`、`bull_rush`、`psychic_topple`、`quake_topple` | 近戰武器技 28 招（`all_in`、`cleave`、`whirlwind`……） |
| 撞擊 | 10（17） | `battering_ram`、`bull_rush`、`death_spiral`、`gale_kick`、`grapple_arrow`、`ice_wall`、`stone_wall`、`telekinetic_hurl`、`thorn_wall`、`tiger_charge` | （無起始技能；被動 `fracture_mark` 利用撞擊觸發） |
| 標記 | 11（21） | `dread_gaze`、`ember_trail`、`flare_sight`、`hex_bolt`、`hunt_sigil`、`hush`、`overwatch`、`taunting_roar`、`thunder_sigil` | `rune_thunderbolt`、`rupture` |
| 高處 | 14（19） | `banish`、`raise_perch`、`retreating_slash`、`sinkhole`、`vault_leap`、`void_swap`、`wing_gift`、`wing_spread` | `armor_piercing_arrow`、`fire_arrow`、`grapple_arrow`、`high_ground_shot`、`piercing_shot`、`sniper_shot` |
| 隱蔽 | 12（17） | `blessing_thief`、`blinding_dark`、`blink`、`dispel_magic`、`flight`、`hex_bolt`、`life_drain`、`smoke_arrow`、`smoke_bomb`、`vanish` | `shadow_ambush`、`shadow_backstab` |
| 召喚物 | 13（19） | `plant_totem`、`raise_skeleton`、`summon_spirit` | `focus_surge`、`guard_swap`、`purify`、`quicken_tide`、`renewal`、`resurrection`、`shoulder_strike`、`tailwind`、`war_hymn`、`wing_gift` |

粗體為本階段新增。池由推導自動產生（`keyword_pools`），沒有任何手寫名單；一招可在多個池（例：`hex_bolt` 同時在隱蔽池與標記池：`test_a_skill_can_be_in_several_pools_and_the_pools_are_derived_not_listed`）。

## 5. 新增技能清單（5 招，全部 1 階、稀有、過預算，無新增原語）

| 技能 | 骨架 | 內容 | 預算比例 | 所屬池 |
|---|---|---|---|---|
| `skill_kindling_strike` 引火重擊 | combo | 火 1d8；目標燃燒中再 +2d8 火（AP 2、法力 6、冷卻 2） | 76.8% | 點燃（製造＋利用） |
| `skill_flash_freeze` 急凍 | control | 冰凍 1 回合＋冰 2d4（單體、AP 2、法力 8、冷卻 4；硬控規則） | 74.9% | 冰凍（製造） |
| `skill_shatter_ice` 碎冰擊 | combo | 冰 1d8；目標冰凍中再 +2d8 冰（AP 2、法力 6、冷卻 2） | 76.8% | 冰凍（製造＋利用） |
| `skill_downpour` 驟雨 | control | 3×3 水表面＋緩速 1 回合（AP 1、法力 6、冷卻 2） | 75.9% | 潮濕（製造） |
| `skill_holy_water` 聖水 | area | 十字神聖 1d4＋水表面（AP 1、法力 6、冷卻 1） | 83.3% | 潮濕（製造＋利用） |

沒有放進任何 build（不動 `builds.yaml`，避免與 3-24a1 衝突）：`tests/content/test_coverage.py` 新增 `_POOL_ONLY` 清單，說明這 5 招在 3-24b2 起由池給出。

## 6. 兩種新修正

- 新增 `ModifierChange` 三個欄位（修正規則「恰好一種改變」不變）：
  - `heal_permille`：你的治療量 ±‰（−500～＋1000，不可為 0，加總後套用，結果下限 0）。引擎：`HealEffect.multiplier_permille`（預設 1000，舊行為不變），解譯器在技能的 `heal` 與聖光雙效（`split_heal`）設定；狀態與表面的回合開始治療、吸血、被動觸發的治療不受影響。
  - `summon_hp_permille`：召喚物最大 HP +‰（1～1000），召喚時結算（最大 HP 與目前 HP 一併提高）。
  - `summon_attack_dice`：召喚物攻擊傷害骰 +1 顆（只能是 1），召喚時以 `WeaponDef.model_copy` 給召喚物自己的武器（不改武器資料表、不改普攻結算）。
- 套用對象只能是 `all_skills`／`skill_tags`（召喚物數值以施放的召喚技能為準）；條件只能是自身血量（與其他選目標前的修正相同）。
- 預算：`heal_permille` ＝ 基準武器傷害 × ‰（同 `damage_permille`）；召喚兩種新增 `skill_budget.yaml` 的 `summon_hp_per_100`（500‰ 點／每 +10%）與 `summon_attack_die`（1200‰ 點）。例：「治療技 +15%」76%、「召喚技 +20% HP」71%、「召喚技 +1 骰」86%。以上皆為初值、未經模擬。
- 一併更新：技能卡文字（「你的治療量 +15%」）、工坊選項、前端修正部件圖示。

## 7. 其他變更

- `SkillCard.keywords`（`makes`／`uses`，各項含 `id`、`name_zh`、`description_zh`）；`WorkshopCheck.keywords`（草稿即時推導）；OpenAPI 快照與 `schema.d.ts` 已重產（只新增欄位）。
- 驗證器新增 `keyword.required`：每招技能（含修正、被動、傳說、工坊與組合器產生的）都要製造或利用至少一個關鍵字。
- 組合器：`compose_random_skill(..., keyword=)`／`compose_with_stats`；以種子變體（`seed + n × 1_000_003`，最多 300 次）重抽到帶有該關鍵字為止，結果的 ID／名稱改回原種子；沒有指定時亂數串流完全不變。10 個關鍵字都能做出（各 3 個種子測過）。
- 組合器重抽次數：修正技能 20 → 60、傳說核心 8 → 16（關鍵字檢查會多淘汰一些候選；不指定關鍵字時，原本就合格的種子結果不變）。
- 因為組合器多了關鍵字檢查，少數種子的結果改變：`client/src/render/fixtures/skill_icons.json` 重產、`tests/cli/snapshots/cli_output_hashes.json` 更新、`tests/cli/test_budget_cli.py` 的技能數 158 → 163、`tests/skillgen/workshop_walks.py` 的修正技能範例加上「目標燃燒中」條件（原本的無條件傷害修正沒有關鍵字）。
- 新增檔案：`content/skill_keywords.yaml`、`src/trpg/content/skill_keywords.py`、`src/trpg/skillgen/keywords.py`、前端 `ui/keywords.ts`、`ui/KeywordLine.tsx`；`content/README.md` 加一列。
- `styles.css` 只在檔尾新增；API 型別只新增欄位；沒有改武器資料與普攻結算；`builds.yaml` 未動。

## 8. 新增的複雜度 noqa

無。

## 9. 待 PM 決定

1. **通用與暫定規則**：69 招手寫技能的關鍵字來自通用（53）或暫定（16）規則（名單見 3.1）。通用規則大多有引擎依據（近戰打倒地者有優勢、高打低 +2 命中、08 的「潮濕表面治療」）；暫定規則沒有真實機制，只是為了滿足「每招至少一個關鍵字」。請決定是否保留、改成修改技能內容（會動平衡），或之後逐一換成真實機制。
2. **池會被通用規則撐大**：倒地池 31 招（28 招是近戰武器技）、潮濕池的利用者多是治療與護盾、召喚物池的利用者多是友方增益。3-24b2 若要讓「選兩個關鍵字拿起始技能」更有針對性，建議候選產生器與開局只看專屬規則（可在 `keyword_pools` 加參數）；是否採用請決定。
3. **有些池缺真實的利用者**：撞擊池沒有起始（主動）利用者（只有被動 `fracture_mark`）；點燃、冰凍、帶電各只有 1～2 個利用者；召喚物的「獻祭」「以召喚物為原點」沒有對應原語，利用者目前只靠「對友方生效」。要補的話需要新原語或新技能。
4. **起始技能的定義**：我定為「1 階、普通或稀有、主動技」；被動、反應、修正與姿態不算（它們不能當起始技能）。若 3-24b2 要把被動或反應也放進池，請告知。
5. **工坊與組合器的限制變嚴**：沒有關鍵字的技能一律不合法（驗證器 `keyword.required`），玩家在工坊做的純數值技能會被擋下並提示加入哪類內容。這是 6.27.1 的明文要求，但請確認玩家端的措辭與引導。
6. **新修正的範圍**：治療量只影響技能的治療與聖光雙效（不含再生、表面治療、吸血、被動與反應技觸發的治療）；召喚物兩種在召喚時結算，AI 對召喚物的估值（`ai/summon.py`）沒有納入加成。隨機組合器沒有加入這三種改變（加入會改變既有種子的結果）；沒有手寫技能使用它們（等裝備詞條 3G 使用）。數值皆為初值。
7. **`builds.yaml` 未動**：新增的 5 招沒有放進任何 build，以 `test_coverage.py` 的 `_POOL_ONLY` 暫代；若 3-24a1 也改 `builds.yaml`，兩邊沒有衝突點。3-24b2 的模擬抽樣上線後可刪掉 `_POOL_ONLY`。
8. **組合器指定關鍵字的做法**：以種子變體重抽（確定性、不改原本的串流），結果 ID 仍是 `skill_rand_<seed>`；有些關鍵字的命中率較低（需要多次變體），目前最多 300 次，測試的 10 個關鍵字都做得出來。3-24b2 若要讓指定關鍵字更「出得準」，可以在組合器內部偏向該關鍵字的原語（目前沒有）。
9. **關鍵字說明文字**：10 個關鍵字的 `description_zh`（部件說明框顯示）是我依 6.27.1 表格寫的一句話，請 PM／玩法 PM 審閱措辭。
10. **截圖解析度**：瀏覽器窗格截圖輸出為 800 px 寬（縮放），若要正式放進文件需要更高解析度可以再補。
