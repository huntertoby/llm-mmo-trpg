# Phase 2D 計畫：補模板 A——保護、輔助與新狀態

> 撰寫：PM｜2026-10-18｜對應 `docs/專案計畫.md` v0.2.1 第 14 節 Phase 2D
> 實作者請先讀：`CLAUDE.md`、本檔第 0–2 節與你負責的子階段一節、`docs/phases/Phase2C-4報告.md` 第 4、8 節、`content/statuses.yaml` 與 `content/ai_profiles.yaml` 開頭的欄位說明。需要時再查 `docs/design/06-技能.md` 6.3、6.5、6.6、6.9 與 `docs/design/05-戰鬥.md` 5.9。

**目標：讓坦克、輔助、治療、術士類的 build 做得出來，而且 AI 會用。** 這不是平衡階段：所有數值都是初值，模擬只記錄、不調整。

| 子階段 | 內容 | 解鎖的 build |
|---|---|---|
| **2D-1｜保護、增益與嘲諷**（第 3 節） | `shield`、`damage_reduction`、`buff_attr`、`haste`、`heal_over_time`、`cleanse`、技能可施加 `defending`、`taunt`；AI 會對友方施放並給分、會服從嘲諷 | 坦克（改版）、輔助、治療 |
| **2D-2｜負面狀態、術士與收尾**（第 4 節） | `fear`、`silence`、`blind`、`mark`（狀態 ID `marked`）；AI 會施放並照規則行動；全量 fuzz、完成度檢查、build 矩陣重跑；2D 驗收總表 | 術士 |

2D-2 在 2D-1 驗收之後才開始；PM 可能依 2D-1 的報告修訂第 4 節。

---

## 0. PM 決定（2C-4 報告「待 PM 決定」）

| # | 項目 | 決定 | 由誰實作 |
|---|---|---|---|
| 1 | 接近距離改用走路步數 | 接受 | — |
| 2 | `keep_distance` 不計隱蔽敵人 | 接受 | — |
| 3 | 掩護只算射程內的敵人 | 接受 | — |
| 4 | `hold_start` 連續 3 輪無 HP 變化就解除 | 接受 | — |
| 5 | 環境權重沒有 A/B | 延後到平衡階段 | 後續 |
| 6 | 勝率表、build 矩陣過時（最弱 build 變成 `build_assassin`） | 2D 結束時重跑矩陣 | 2D-2（4.6） |
| 7 | `oil_depot`、`swamp` 的平衡測試 XPASS | 平衡完成後再移除 xfail，本階段不動 | 後續 |
| 8 | completion 快速測試約 30 秒 | 接受 | — |
| 9 | Phase 2 驗收第 1、11 條 ⚠️ | 排入 2E | 2E |
| 10 | `trpg sim completion` 有異常時結束碼為 1 | 接受 | — |

本階段另外的設計決定（使用者已同意或 PM 決定）：

| # | 決定 |
|---|---|
| A | 狀態 `mark` 的 ID 改為 **`marked`**（被標記），避免與角色成長的「印記」（`content/marks/`）撞名。 |
| B | 除了 `shield` 與 `cleanse` 是 **新原語**，其餘模板都做成 **狀態**（`statuses.yaml` 新增條目與欄位），透過既有的 `apply_status` 施加（守則 4：內容即資料）。技能 YAML 與 LLM 之後看到的仍是「施加某狀態」。 |
| C | 光環骨架（`aura`）擴充為「友方支援」：形狀加上 `single`（單一友方，含自己），核心原語加上 `shield`、`cleanse`。6.9 的「範圍內友方加成」把單體視為半徑 0 的情況，不另開骨架。 |
| D | 嘲諷是 **軟強制**：引擎規則是「對嘲諷者以外的目標攻擊有劣勢」（玩家與 AI 都適用）；AI 另外把攻擊目標限制在嘲諷者（見 3.7）。不做「完全不能攻擊別人」的硬鎖。 |
| E | 所有新數值（點數、持續回合、護盾量、AI 權重）都是 **初值未經模擬**，在資料檔註解標明；平衡階段再調。 |

---

## 1. 範圍

**要做**：你負責的子階段一節中的交付項目。

**不要做**：
- 任何平衡：勝率、輪數、技能數值、AI 權重的「調好」。數值照本檔給的初值；若初值造成例外或僵局，修的是程式或規則，不是調到勝率好看。
- 事件觸發系統（`on_hit`、`on_damaged`……）、被動／反應／姿態／陷阱骨架、層數、替隊友擋攻擊的反應技（屬於 2E）。
- 召喚、改寫規則型原語、偷取增益／驅散敵方增益。
- 新地圖、前端、LLM、roguelite。
- 修改 `docs/專案計畫.md`、`docs/design/`、`CLAUDE.md`、`docs/phases/` 下的計畫檔。

**引擎改動**：本階段必須改引擎規則（新狀態欄位、護盾、淨化、嘲諷）。原則：
- 狀態效果一律經過 `trpg.engine.rules.statuses` 的函式判斷 **欄位**，引擎其他地方不直接判斷狀態 ID（沿用 2B-1 的做法）。
- `preview` 必須和實際結算一致（固定骰值時相同），包含護盾吸收、屬性加值、嘲諷劣勢。
- 新的事件型別要能序列化、重播（`trpg battle replay` 通過）。

---

## 2. 工作環境

同 `docs/phases/Phase2C計畫.md` 第 2 節，但 commit 結尾改為：

```
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01WzRQ8LmeGFZixwbXumwejE
```

- 機器只有 2 核心：大型模擬用 `--jobs 2`、放背景執行，先用 2–3 個種子確認能跑。**規格要求的全量模擬只在最後跑一次**（2C-4 曾因重跑兩次全量而多花 30 分鐘）。
- 新狀態與 AI 權重會改變戰鬥軌跡。**斷言特定軌跡的既有測試**（某種子的勝方、某回合的動作、golden 紀錄）可以更新期望值，但要在報告列出每一個被改的測試與原因；**斷言規則或不變量的測試不可以為了通過而修改**。
- 每完成一個交付項目就 commit（守則 11）。

---

## 3. Phase 2D-1｜保護、增益與嘲諷

### 3.1 狀態定義的新欄位（`content/statuses.yaml`、schema、`trpg.engine.rules.statuses`）

| 欄位 | 型別 | 效果 |
|---|---|---|
| `attr_bonus` | `{attr: int}` | 帶有者的有效屬性加值（多個狀態相加）。 |
| `on_turn_start_heal` | `{dice}` | 回合開始時治療（與 `on_turn_start_damage` 同一時點；受 `healing_received_permille` 影響；不超過最大 HP）。 |
| `forces_target` | `bool` | 嘲諷：帶有者對 **狀態來源以外** 的單位發動攻擊（基本攻擊與有攻擊判定的技能）時有劣勢；來源倒下或離場時此狀態立即移除。 |
| `absorbs_damage` | `bool` | 護盾：此狀態帶有一個吸收量（見 3.3）。 |

- 現有的 `move_permille`、`damage_taken_permille` 直接拿來做加速與減傷，不用新欄位。
- **有效屬性**：在 `trpg.engine.rules.statuses`（或同層的新模組）提供 `effective_attribute(rules, unit, attr) -> int`＝基礎屬性＋所有狀態的 `attr_bonus`。引擎內所有用到屬性的判定（命中比例、抵抗判定、對抗判定、傷害／治療／護盾的屬性縮放）都改用它；**先攻例外**（戰鬥開始時擲，用基礎屬性）。加一個測試：掃描 `src/trpg/engine/` 的原始碼，除了 `effective_attribute` 本身與先攻的計算，沒有直接讀 `.attributes[`。
- 嘲諷的劣勢併入既有的 `advantage_sources`，所以 `preview` 自動一致。

### 3.2 新狀態（初值未經模擬）

| ID | 中文 | 效果 | 持續 | 有益 | `budget_points` | `min_rarity` | `save_attr` |
|---|---|---|---|---|---|---|---|
| `guarded` | 護衛 | `damage_taken_permille: 700` | 2 | ✅ | 4 | common | — |
| `empowered` | 激昂 | `attr_bonus`：六個屬性各 +2 | 2 | ✅ | 4 | common | — |
| `hasted` | 加速 | `move_permille: 1500` | 2 | ✅ | 3 | common | — |
| `regenerating` | 再生 | `on_turn_start_heal: 1d4` | 3 | ✅ | 4 | common | — |
| `shielded` | 護盾 | `absorbs_damage: true`（由 `shield` 原語施加，見 3.3） | 2 | ✅ | 不設（不能用 `apply_status` 施加） | — | — |
| `taunted` | 嘲諷 | `forces_target: true` | 2 | ❌ | 4 | common | `wil` |
| `defending` | 防禦 | 既有；**新增** `budget_points: 2`，讓技能可以施加 | 既有 | ✅ | 2 | common | — |

- 全部 `expires: turn_end`、`stacking: refresh`（`defending` 維持原本的 `own_turn_start`）。
- `stacking: refresh` 時 **來源改為最新的施放者**（嘲諷被別人重新施加時，改為嘲諷新的施放者）。若現有程式刷新時不更新 `source_id`，改成更新，並確認既有測試不受影響。
- 減傷與易傷同時存在時照既有規則依序相乘（700 × 1250）；不另設下限，報告中記錄。

### 3.3 新原語 `shield`（護盾）

- `content/skill_primitives.yaml`：`category: numeric`、`harmful: false`、`budget_basis: dice_average`、`params: {dice: required}`，預設 `affects: allies`。
- 護盾量＝骰值＋有效縮放屬性 × 0.5（與 `heal` 同一公式，無條件捨去）。
- 施加：目標獲得 `shielded`（持續 2），`StatusInstance` 新增欄位 `amount: int | None`（只有 `absorbs_damage` 的狀態使用；序列化與重播要包含）。已有護盾時，吸收量取 **較大值** 並刷新持續時間（6.6「同類增益取最高」）。
- 吸收：受到的傷害在 **所有倍率之後、扣 HP 之前** 先扣護盾。適用範圍與 `damage_taken_permille` 相同（骰值傷害，包括攻擊、技能、持續傷害、爆炸、表面）；以最大 HP 比例計算的傷害（墜落、致命地形）不吸收。
- 事件：`shield_gained`（unit_id、amount、total）、`shield_absorbed`（unit_id、absorbed、remaining）；吸收量歸零時移除 `shielded`（`status_removed`，原因 `depleted`）。`damage_dealt` 只記實際扣血（沿用 2C-1「傷害只算實際扣血」），模擬器的 DPR 不把被吸收的部分算進去；報表另加一欄「護盾吸收」（每場平均）。

### 3.4 新原語 `cleanse`（淨化）

- `category: numeric`、`harmful: false`、`budget_basis: fixed`、`base_points: 3`、無參數，預設 `affects: allies`。
- 效果：移除影響單位身上 **所有非有益**（`beneficial: false`）的狀態，依狀態 ID 排序逐一發出 `status_removed`（原因 `cleansed`）。沒有可移除的狀態時不發事件。
- 不能對敵人移除增益（驅散不在本階段）；驗證器拒絕 `cleanse` 搭配 `affects: enemies`／`all`。

### 3.5 預算、驗證與組合器

- 新狀態有 `budget_points`，既有的 `budget_basis: status` 與組合器的 `_status_candidates` 應會自動納入；確認有益狀態會出現在光環骨架、有害的 `taunted` 會出現在控場與打擊骨架。
- 光環骨架照第 0 節 C 擴充（`shapes` 加 `single`、`core.primitives` 加 `shield`、`cleanse`）。單體光環技能只能以友方（含自己）為目標。
- 組合器要能產生 `shield`、`cleanse`（參數產生方式比照 `heal`）。
- `scripts/skill_fuzz.py`（或 `trpg sim` 的 fuzz 摘要）要列出 **各原語與各狀態的出現次數**；本子階段在 `--count 1000` 中，`shield`、`cleanse` 與 3.2 的每個新狀態都至少出現 1 次。

### 3.6 新的手寫技能（`content/skills/`）

數值是起點；實作者可以調整骰子或代價讓它們通過 `trpg skills budget --all`（0.7–1.0），但效果組成不變。名稱與描述用繁體中文。

| ID | 中文 | 骨架 | 形狀 | 效果 | AP | 代價 | `weapon_req`／`category`／縮放 |
|---|---|---|---|---|---|---|---|
| `skill_taunting_roar` | 挑釁怒吼 | control | `ring`（以自己為中心，r=1）或同等的周圍範圍 | `apply_status taunted` | 1 | 冷卻 2 | any／spell／str |
| `skill_guardian_aegis` | 守護之盾 | aura | `single`（友方，射程 4） | `shield 2d6` | 1 | 法力 4、冷卻 1 | any／spell／con |
| `skill_war_hymn` | 戰歌 | aura | `allies_in_radius`（r=2） | `apply_status empowered` | 2 | 法力 8、冷卻 3 | focus／spell／wis |
| `skill_tailwind` | 順風 | aura | `single`（友方，射程 4） | `apply_status hasted` ＋ `apply_status guarded` | 1 | 法力 4、冷卻 2 | focus／spell／wis |
| `skill_renewal` | 回春 | aura | `single`（友方，射程 4） | `apply_status regenerating` ＋ `heal 1d6` | 1 | 法力 5、冷卻 1 | focus／spell／wis |
| `skill_purify` | 淨化之光 | aura | `single`（友方，射程 4） | `cleanse` ＋ `apply_status defending` | 1 | 法力 4、冷卻 2 | focus／spell／wis |

### 3.7 效用 AI

**對友方的收益**（`content/ai_profiles.yaml`，在開頭的權重說明補上新欄位）：

- 新的全域表 `ally_status_values`（單位是「等值的傷害點數」）：`{guarded: 5, empowered: 5, hasted: 3, regenerating: 6, defending: 3}`。收益＝行為模式的 `support` 權重 × 價值；目標倒下時 0；目標已有同一狀態時只算剩餘回合的差額比例（新持續 − 剩餘，÷ 新持續，下限 0）。
- 新權重 `shield`：每點實際增加的護盾量（新吸收量 − 原吸收量，下限 0）。
- 淨化：被移除的每個狀態依 `status_values` 的價值（沒列出的用 3）× `support` 權重。
- 敵方的 `status_values` 加上 `taunted: 5`。
- 各行為模式補上的權重（初值）：

| 行為模式 | shield | support |
|---|---|---|
| brute | 6 | 3 |
| archer | 5 | 3 |
| cunning | 5 | 4 |
| guard | 8 | 6 |

- 新增行為模式 **`support`（支援）**：重視治療、護盾、增益與保持距離。權重初值：`{damage: 4, env_damage: 1, kill: 20, env_kill: 15, push: 3, surface: 3, expose: 5, friendly_fire: 10, approach: 1, threat: 2, keep_distance: 20, protect: 15, objective: 10, hazard: 10, defend: 2, heal: 12, shield: 10, support: 12, status: 3, mana: 1, cooldown: 1}`。

**被嘲諷的 AI**（在 `trpg.engine.ai` 內，不改合法動作）：

- 帶 `taunted` 的單位：只要本次決策中有分數 > 0、且有害效果影響到嘲諷者的動作，就只在這些動作與移動之間選；位置價值的 `approach` 改以「與嘲諷者的距離」計算（與集火指令相同的做法）。
- 嘲諷者打不到也走不近時，照一般規則行動（不能因此僵住；由完成度檢查守門）。
- 嘲諷與戰術指令同時存在時，嘲諷優先（記在報告）。

### 3.8 build

`content/sim/builds.yaml`：

- `build_tank` 技能改為 `[skill_bone_crusher, skill_shield_bash, skill_taunting_roar, skill_guardian_aegis]`，主題文字同步更新；`ai_profile` 改為 `guard`。
- 新增 `build_support`（輔助）：屬性比照法師但 `wis 16`、`int 12`；武器 `frost_staff`；`ai_profile: support`；技能 `[skill_war_hymn, skill_tailwind, skill_frost_shackle]`。
- 新增 `build_healer`（治療）：同上屬性；武器 `frost_staff`；`ai_profile: support`；技能 `[skill_sanctuary, skill_renewal, skill_purify, skill_guardian_aegis]`。
- 若 `skill_frost_shackle`、`skill_sanctuary` 的武器需求或縮放屬性不相容，換成同主題、相容的既有技能並寫進報告。

### 3.9 測試（情境測試，每項至少一個）

1. `guarded`：同一骰值下，受到的傷害為無狀態時的 70%（無條件捨去規則與既有一致）；與 `vulnerable` 同時存在時依序相乘。
2. `empowered`：命中比例、抵抗判定、法術傷害縮放都用加值後的屬性；`preview` 與實際一致。
3. `hasted`：回合開始的移動點數 ×1.5；與 `slow` 同時存在時依序相乘。
4. `regenerating`：回合開始治療、受中毒減半、不超過最大 HP、3 回合後消失。
5. `shield`：吸收量公式；先扣護盾再扣 HP；部分吸收；歸零時移除並發出事件；重複施加取較大值；墜落傷害不吸收；`preview` 與實際一致；`--log-json` 後 `replay` 一致。
6. `cleanse`：只移除非有益狀態、依 ID 排序發事件；`affects: enemies` 被驗證器拒絕。
7. `defending`：技能可施加在友方身上，效果與防禦動作相同。
8. `taunted`：對非嘲諷者攻擊有劣勢、對嘲諷者沒有；嘲諷者倒下時狀態移除；重新施加時來源更新；被嘲諷的 AI 在「能打嘲諷者也能打更弱的目標」的情境中選擇嘲諷者。
9. AI：小情境中，`support` 行為模式在「友方受傷且被敵人貼身」時選擇治療／護盾／增益，而不是基本攻擊；友方滿血且已有該增益時不會重複施放。
10. 有效屬性的原始碼掃描測試（3.1）。
11. 新技能全部通過 `trpg skills budget --all`；組合器 fuzz（3.5）。

### 3.10 驗收條件（2D-1）

1. `uv run python scripts/check.py` 五項全過。
2. 3.9 的 11 項測試都存在並通過（報告列出測試名稱）。
3. `scripts/skill_fuzz.py --count 1000`：0 例外；摘要中 `shield`、`cleanse` 與 3.2 的新狀態都出現（附摘要）。
4. `trpg skills budget --all`：所有內建技能（含 6 個新技能）在預算範圍內。
5. `trpg sim completion --seeds 3 --jobs 2`：`exception`、`max_actions`、`draw` 皆為 0（只跑這一次；全量在 2D-2）。
6. `trpg sim matrix --seeds 3 --jobs 2` 能跑完 8 個 build（只確認能跑，結果附在報告、不解讀）。
7. 挑一張地圖、一個非 0 種子，用 `--ally-commander protect_weakest` 跑 `trpg battle ... --log-json f` 再 `trpg battle replay f`，結果一致；附一段出現護盾或增益的戰鬥紀錄節錄。
8. 列出所有因軌跡改變而更新期望值的既有測試（沒有就寫「無」）。

報告：`docs/phases/Phase2D-1報告.md`，格式同 `docs/phases/Phase2C計畫.md` 第 7 節；「給下一個子階段的備註」寫給 2D-2。

---

## 4. Phase 2D-2｜負面狀態、術士與收尾

> 2D-1 驗收後才開始。實作者先讀 `docs/phases/Phase2D-1報告.md`。

### 4.1 新的控制類別

`control_group` 新增 `mental`（心智）：`fear`、`silence` 屬於此類，適用既有的控制遞減（`control_dr_rounds` 輪內守方屬性 ×150%）。`mental` 不是 `hard`，對 Boss 不轉換。

### 4.2 新狀態欄位與狀態（初值未經模擬）

| 欄位 | 效果 |
|---|---|
| `fear_source` | `bool`。帶有者主動移動時，每一步都不能讓自己與狀態來源的曼哈頓距離變小；攻擊（任何目標）有劣勢。來源倒下時移除。 |
| `blocks_spells` | `bool`。不能使用 `category: spell` 的技能（武器技與基本攻擊照常）；從合法動作中排除。 |
| `attack_range_cap` | `int`。攻擊與以單位為目標的技能，只能選擇此距離以內的單位；攻擊有劣勢。 |
| `grants_advantage_against` | `bool`。對帶有者的攻擊有優勢；帶有者不受 `concealed`（含黑暗表面、草叢）的「無法選為目標」限制。 |

| ID | 中文 | 欄位 | 持續 | `budget_points` | `min_rarity` | `save_attr` | `control_group` |
|---|---|---|---|---|---|---|---|
| `feared` | 恐懼 | `fear_source` | 2 | 5 | rare | `wis` | `mental` |
| `silenced` | 沉默 | `blocks_spells` | 1 | 5 | rare | `wil` | `mental` |
| `blinded` | 致盲 | `attack_range_cap: 2` | 1 | 4 | rare | `wis` | — |
| `marked` | 被標記 | `grants_advantage_against` | 2 | 4 | common | `wis` | — |

全部有害、`expires: turn_end`、`stacking: refresh`（來源更新規則同 2D-1）。

### 4.3 效用 AI

- `status_values` 加上 `{feared: 6, silenced: 5, blinded: 5, marked: 4}`；**沉默** 的價值在目標沒有可用的法術技時為 0。
- 帶這些狀態的 AI 單位照合法動作與規則行動（恐懼時不能接近的移動本來就不合法）；被恐懼且無路可退時要能結束回合，不可例外或僵住。
- `marked`：我方 AI 對被標記的目標，命中率上升已經由 `preview` 反映，不另加權重。

### 4.4 新的手寫技能與 build

| ID | 中文 | 骨架 | 形狀 | 效果 | AP | 代價 | `weapon_req`／`category`／縮放 |
|---|---|---|---|---|---|---|---|
| `skill_hex_bolt` | 咒印飛彈 | strike | `single`（射程 5） | `damage 1d8 shadow` ＋ `apply_status marked` | 1 | 法力 3 | focus／spell／int |
| `skill_dread_gaze` | 恐懼凝視 | control | `single`（射程 4） | `apply_status feared` | 1 | 法力 5、冷卻 2 | focus／spell／int |
| `skill_hush` | 噤聲 | control | `single`（射程 4） | `apply_status silenced` | 1 | 法力 5、冷卻 3 | focus／spell／int |
| `skill_blinding_dark` | 蔽目黑霧 | control | `square3`（射程 4） | `apply_status blinded` ＋ `damage 1d4 shadow` | 2 | 法力 8、冷卻 3 | focus／spell／int |

- 新增 `build_warlock`（術士）：屬性比照法師；武器 `fire_staff`（或任一法杖，寫進報告）；`ai_profile: cunning`；技能為上表 4 個。
- 數值調整規則同 3.6。

### 4.5 測試

1. 每個新狀態的情境測試：恐懼的移動限制與攻擊劣勢、來源倒下時移除、無路可退時能結束回合；沉默排除法術技但保留武器技與基本攻擊；致盲的射程上限與劣勢；被標記的優勢與「隱蔽者仍可被選為目標」。
2. `mental` 控制遞減生效；Boss 不轉換 `mental` 狀態。
3. `preview` 與實際一致（恐懼劣勢、標記優勢、致盲劣勢）。
4. AI：小情境中，狡猾型會對法術型敵人施加沉默、不會對沒有法術技的敵人施加沉默。
5. 新技能通過 `trpg skills budget --all`。

### 4.6 收尾（只在最後各跑一次全量）

1. `scripts/skill_fuzz.py --count 1000`：0 例外；2D 全部新原語與新狀態都出現（附摘要）。
2. `uv run pytest -q -m slow`：列出每個 slow 測試的結果；非平衡的 slow 測試必須通過。
3. `trpg sim completion --seeds 20 --jobs 2`（全量）：`exception`、`max_actions`、`draw` 皆為 0；附摘要表與執行時間。
4. `trpg sim matrix --seeds 20 --jobs 2`（9 個 build）：附勝率、DPR、排名矩陣與 6.8 標準檢查結果；**只記錄、不調整**。另附一張與 2C-4 矩陣的對照（`build_tank` 前段類型數的變化）。
5. **Phase 2D 驗收總表**：逐條對照 `docs/專案計畫.md` 第 14 節 Phase 2D，每條標 ✅／⚠️／❌ 並附證據：
   | # | 項目 |
   |---|---|
   | 1 | 效果模板 `shield`、`damage_reduction`、`taunt`、`buff_attr`、`haste`、`heal_over_time`、`cleanse` |
   | 2 | 狀態 `fear`、`silence`、`blind`、`mark`（`marked`） |
   | 3 | 技能可以施加 `defending` |
   | 4 | 效用 AI 能評分並使用這些效果 |
   | 5 | 驗收：新模板與狀態都有資料檔、預算、解譯與情境測試 |
   | 6 | 驗收：隨機組合器能組出含新模板的技能，1,000 個技能無例外 |
   | 7 | 驗收：build 矩陣補上保護型與輔助型 build 後重跑並附報表 |

### 4.7 驗收條件（2D-2）

1. `uv run python scripts/check.py` 五項全過。
2. 4.5 的測試都存在並通過（列出測試名稱）。
3. 4.6 的 1–5 都附在報告中，三種異常為 0。
4. `trpg battle ... --log-json` 與 `replay` 一致（非 0 種子），附一段出現新狀態的紀錄節錄。
5. 列出所有因軌跡改變而更新期望值的既有測試（沒有就寫「無」）。

報告：`docs/phases/Phase2D-2報告.md`，格式同 `docs/phases/Phase2C計畫.md` 第 7 節，另加 4.6-5 的「Phase 2D 驗收」一節；「給下一個子階段的備註」改寫為「給補模板 B（2E）的備註」（例如哪些狀態之後會需要事件觸發、護盾與嘲諷和「替隊友擋攻擊」反應技的關係）。
