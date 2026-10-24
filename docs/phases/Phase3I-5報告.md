# Phase 3I-5 報告：武器親和與招牌技（玩法決定 #50）

規格：`docs/phases/Phase3I計畫.md` 3I-5 列、第 2、3 節；設計 06 6.10（#50）、6.5、08 8.11。使用者原話：「武器專屬技能選 B＋少量 A」「好 寫入」。

## 規則對照表

| 規格／設計項 | 做法 |
|---|---|
| 新條件「手持某種武器時」，照 6.5 條件倍率計入預算 | `skill_conditions.yaml` 新增 `wielding_weapon`（參數 `weapon`＝武器或副手 ID；常見 0.85；稀有以上）。施放者條件（`CASTER_CONDITIONS`）：主手武器 ID 或副手 ID 相符即成立（`unit_held`）。雙匕首算雙匕首、不算匕首。預算走原本的效果層級條件倍率，沒新增公式 |
| 沒拿那種武器時技能照常可用，只是沒有加成 | schema 規定只能寫在 **效果** 上（`SkillDef._check_gear_limits`，訊息 `WIELDING_EFFECT_ONLY`）；寫在技能條件或複合第二段條件會被擋。工坊的技能條件選單事前停用該選項 |
| 新欄位「限定武器」 | `SkillDef.weapon_only`（ID 清單，可含武器與副手，如盾）。**不符＝不能裝備 ＋ 不能施放**（兩者都做，6.10 只寫「限定那種武器才能用」）：併入 `weapon_problem(skill, class, held)`，裝備檢查（開戰 `_check_loadouts`、`api/gear`、工坊、範本載入、開局、候選）與施放（`resource_problem`）共用 |
| 火器、盾、成對武器（雙匕首、雙手槍）、鞭各 1 招 | 5 招：燃燒彈（火槍／霰彈槍／手槍／雙手槍）、堡壘突擊（圓盾／塔盾）、交叉斬（雙匕首）、交叉火網（雙手槍）、鞭梢爆響（鞭，射程 3＋拉近 1） |
| 工坊（3-48h 事前停用，驗證器同源） | 基本設定步驟新增多選「限定武器」；效果的「效果條件」欄位（傷害、狀態、治療、護盾、推、拉、擊倒、造表面）含「手持武器」；武器大類與 `weapon_req` 不符者標 `unavailable_zh`，判斷用 `library.gear_class_problem`（驗證器 `gear_reference_problems` 同一函式），有測試逐項比對「停用＝驗證器會擋」 |
| 卡片 | `SkillCard.weapon_only`（「限定手持：鞭」）；效果句「…，若手持鞭時」；前端卡片多一行「限定手持：…（沒拿就不能裝備、不能施放）」；CLI `skills show` 同；條件圖示新增劍形 |
| 驗證器 | `gear_reference_problems`（存在、武器大類相符），掛在 `validate_skill` 的 reference 與內容庫載入 |
| 隨機組合器 | `skillgen/affinity.py`：組好之後（亂數串流不變）把附帶效果（索引 ≥ 1）上 **既有的常見條件** 換成手持條件（預算不變、關鍵字不變、須通過驗證器），機率 `composer.condition.affinity_permille` 400，用技能 ID 決定的確定性抽籤；只選主角手上、大類相容的裝備。`CandidateRequest.held`／`compose_random_skill(held=…)` |
| LLM 提議 | 條件聯集多了 `weapon`（可選值＝玩家可持有的武器與副手）；`ProposalContext.held` 有值時，指定了主角沒拿的裝備回 `gear.not_held` 錯誤（附 allowed）重提 |
| 招牌技不能被擠進不符的流程 | 候選、開局技能池、暫時獲得（`grant_skill` AI 判斷）都帶 `held` |
| 紀錄格式 | `LOG_FORMAT` `/70`（見待決 1）；`Ruleset.gear_names`（武器／副手中文名）嵌入規則包 |

## 示範技能（29 招，皆 1 階、稀有、2 AP，數值為初值，未經模擬）

親和 24 招（拳套、鐮刀、鞭、魔導劍、圓盾、塔盾、法書、法器珠、雙匕首、霰彈槍、手槍、雙手槍各 2 招）＋招牌 5 招。預算比例＝total ÷ 可用預算（含手持加成效果）：

| 技能 | 名稱 | 類型 | 比例 |
|---|---|---|---|
| skill_ironclad_flurry／skill_guard_breaker_fist | 鐵拳連打／碎防拳 | 親和 拳套 | 87.1%／87.8% |
| skill_reaping_arc／skill_soul_harvest | 收割弧／靈魂收割 | 親和 鐮刀 | 88.6%／87.3% |
| skill_chain_lash／skill_hamstring_lash | 連環鞭／絆腿鞭 | 親和 鞭 | 89.3%／88.2% |
| skill_runic_cut／skill_spellblade_surge | 符文斬／魔刃湧動 | 親和 魔導劍 | 87.7%／87.8% |
| skill_shield_rush／skill_rim_strike | 盾衝／盾緣打擊 | 親和 圓盾 | 86.7%／87.7% |
| skill_tower_slam／skill_rampart_jeer | 塔盾猛擊／壁壘挑釁 | 親和 塔盾 | 86.7%／88.2% |
| skill_scholars_bolt／skill_annotated_frost | 學者電矢／批註寒霜 | 親和 法書（法術） | 87.8%／90.1% |
| skill_orb_spark／skill_orb_lance | 珠光連閃／珠光長槍 | 親和 法器珠（法術） | 87.8%／87.0% |
| skill_twin_fang／skill_blade_dance | 雙牙／刃舞 | 親和 雙匕首 | 89.3%／87.3% |
| skill_point_blank_blast／skill_scatter_shot | 近距轟擊／散彈驅離 | 親和 霰彈槍 | 87.1%／87.3% |
| skill_quick_draw／skill_trick_shot | 快拔連射／花式射擊 | 親和 手槍 | 87.7%／87.0% |
| skill_akimbo_burst／skill_suppressing_fire | 雙槍連射／壓制射擊 | 親和 雙手槍 | 89.3%／88.2% |
| skill_whip_crack | 鞭梢爆響 | 限定 鞭 | 86.7% |
| skill_bastion_strike | 堡壘突擊 | 限定 圓盾／塔盾 | 86.4% |
| skill_crossing_slash | 交叉斬（背後那一刀） | 限定 雙匕首 | 86.7% |
| skill_crossfire | 交叉火網（目標緩速時第二槍） | 限定 雙手槍 | 86.7% |
| skill_blazing_round | 燃燒彈 | 限定 火器四種 | 88.2% |

這批技能由池給出（`tests/content/test_coverage.py` 的 `_POOL_ONLY`），未改 `builds.yaml`。技能總數 225 → 254。

## 測試

- 新增 `tests/engine/test_weapon_affinity_3i5.py`（57 個）：條件真值表（含副手、雙匕首≠匕首）；24 招親和技能「有拿才多一次傷害、沒拿照常可用」實戰；限定技 17 列（開戰檢查、`resource_problem`、`legal_actions`）；範本載入含副手；卡片「若手持」的效果索引＝引擎判斷的索引；一場含招牌技的 AI 對戰重播一致（種子 3，87 個動作）。
- 新增 `tests/skillgen/test_affinity_3i5.py`（13 個）：限定武器多選與事前停用＝驗證器；效果條件欄位；技能條件選單停用；組合器親和（只指定手上裝備、大類相容、可驗證、確定性）；LLM 提議 `gear.not_held`。
- 更新：技能總數 254、`LOG_FORMAT` `/70`、工坊文字表 151 條（新增手持武器條件 2 條）、開局／候選測試改帶 `held`、`skill_icons.json`、`glossary.json`、`openapi.json`／`schema.d.ts`、CLI 快照。
- 檢查：ruff check、ruff format --check、mypy、lint-imports（7 kept）；pytest（engine、content、skillgen、llm、roguelite、narrative、api、sim、shared、架構、`-m "slow or not slow" tests/cli`）；vitest 965、build；排版煙霧檢查 1600×900、800×600、底部最矮 全 PASS（先 `localStorage.clear()`；8026 埠被別人占用，改用 8037，已停止）。**未在畫面上看**工坊「限定武器」多選與效果條件欄位的實際樣子（以 pytest 與 tsc 代替）。

## 待 PM 決定

1. `LOG_FORMAT`：任務說目前 `/70`，但本 worktree 的 `runner.py` 是 `/69`，我升到 `/70`。若主線已是 `/70`，合併時請改 `/71`（共 9 個測試檔有字面值）。
2. 「成對武器各 1 招」：我解讀為雙匕首 1、雙手槍 1（共 2 招）；火器 1 招涵蓋四種火器；盾 1 招涵蓋兩種盾。
3. 火器的「裝填、彈匣」特殊機制：沒有對應原語，招牌技只用既有原語（火器技本來就吃彈匣）；真要做「技能裝填」需新原語。
4. 限定武器欄位只有手寫與工坊會產生；**隨機組合器與 LLM 提議不產生 `weapon_only`**（6.10 說只有各 1 招），它們只做親和條件。
5. 親和加成的呈現是「條件效果」：沒拿武器時基準偏弱（連段類約 1.15 倍），拿了才補到預算；數值與強弱待平衡。
6. 組合器親和只換既有的常見條件、不新增效果，所以出現率低於 400‰ 的字面值；之後要提高需在預算窗內加效果。
7. 工坊效果層級條件欄位一併列出所有條件（不只手持武器），因為既有技能的效果條件需要在選項內；只列在 8 種常用原語。
8. `Ruleset.gear_names` 嵌入規則包（引擎訊息要中文名）；一般開局沒有副手，盾招牌技要等 3K 才拿得到。
9. 條件圖示用簡單劍形，美術可再改。
