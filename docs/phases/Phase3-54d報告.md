# Phase 3-54d 報告｜大地元素判定＋大地種子＋3-54b／3-55 小修

規格：`docs/phases/Phase3計畫.md` 第 67 節；設計：`docs/design/06-技能.md` 6.33、6.10。

## 做了什麼

| 規格 | 實作 |
|---|---|
| 1 技能元素 | `SkillDef.element`（選填）。`skill_elements()`：有填就是它；沒填沿用 `tags` 裡的元素名稱，**多個元素標籤取第一個非物理的**（保守：只算一個）；效果自己寫的元素不再算。`element` 與標籤的元素不一致時 schema 報錯。 |
| 2 工坊開放選技能元素 | 基本設定步驟新增「技能元素」（選填，不含物理）；`/api/workshop/options`、`/check` 自動帶；前端晶片選單可清除；卡片多「技能元素：大地」一列（`SkillCard.element`、`element_id`）。LLM 提議模型加選填 `element`；複合技能第二段沿用。組合器不改（主題元素本來就在標籤，只是不寫 `element`，見下）。 |
| 3 大地限制 | 互斥規則 `terrain_needs_earth` 擴大：隆起、下陷、**震波**、**石膚（狀態）**都要技能元素是大地。`SkillMatch` 新增 `any_of`（OR 子比對）表達「原語 A 或狀態 B」。工坊事前停用、`option_effect_rules`（移出成對規則，變單一效果規則，原因文字改為「到基本設定把技能元素選成大地」）、組合器（`_theme_allows` 同時管原語與狀態，石膚只在大地主題抽）、LLM 提議（走驗證器）都讀同一條規則。 |
| 4 震波命中 | 現況不符：`affects: all` 時友方會被擲命中、未命中不倒地。已改：`Cast.roll_hits` 對震波不替友方擲命中；`shockwave` 處理器自己選對象（敵方須命中；友方一律倒地、`all` 不含施放者）。卡片句改「…對敵人仍要先命中；已經倒地和會飛的單位不受影響」。 |
| 5 初值與說明 | 石膚預算 3 維持、拿掉最低稀有（`statuses.yaml`）；震波預算 4、最低稀有不變；擴散 2 格不變；`workshop_text.yaml` 的 `damage.spread`、`shockwave` 換成規格句，石膚狀態說明句尾加「只有大地元素的技能能施加。」（震波 `description_zh` 開發者原文同步）。 |
| 6 大地 4 招 | **只做了 2 招**：震地波（`skill_quake_wave`：area、直線 4、1d8 大地＋震波，2 AP，8 法力、冷卻 3，rare，預算 89.8%）、碎岩擊（`skill_rock_smash`：combo、近戰武器技，傷害 ×1.2 大地＋「目標倒地」時再 ×0.6 大地〔倒地時合計 ×1.8，是不倒地 ×1.2 的 1.5 倍〕，2 AP，8 耐力、冷卻 2，rare，76.0%）。石膚術、大地崩陷**預算組不出來**，見待 PM 決定 1、2。4 招寫了 `element: earth`。 |
| 7 3-55 小修 | 沒持有者時縮放寫「手上武器的屬性」（卡片「縮放：手上武器的屬性」）；新增 `GET /api/workshop/weapons`；工坊「預覽武器」下拉（「不指定（列例子）」＋全部 22 種武器，顯示「名稱（大類）」），預設＝`heroWeapon` prop（一輪開工坊時由 App 傳；目前 App 沒有從一輪進工坊的入口，所以實際都從首頁開＝不指定），只影響 options／check 的 `weapon`，不寫進草稿。沒有新增彈出卡片。 |

注意：碎岩擊的「×1.5」以兩個傷害效果表達（1.2＋條件 0.6，沿用交叉火網的連段寫法），兩段各自命中後結算；單次傷害不是一個 ×1.5 的效果。

## 影響盤點結果

- 既有手寫隆起／下陷技能（築高台、陷地術）靠 `tags: [earth]` 仍合法；石牆術、築起土牆、移山之力不含這些原語／狀態或標籤已含 earth，驗證全過。
- **組合器既有種子改變**：石膚不再出現在非大地主題、石膚最低稀有拿掉（大地主題的 common 池多了石膚）。`skill_icons.json`、`glossary.json` 已重產；CLI 快照見驗收。
- 組合器不另寫 `element` 欄位（維持標籤主題），所以序列化不變。
- `LOG_FORMAT` **沒有遞增**（沒有新事件）；但震波 `affects: all` 的友方結算規則改了（只有測試用途，目前沒有紀錄檔含此用法）。合併時若 3-54c 遞增請 PM 處理。
- OpenAPI／`schema.d.ts` 已重產（新增 `SkillCard.element/element_id`、`WorkshopWeapon`、`/api/workshop/weapons`）。

## 驗收（逐條）

| 條件 | 證據 |
|---|---|
| 技能元素 × 原語合法性表格（驗證器、工坊、組合器一致） | `tests/engine/test_earth_54d.py`：`test_validator_allows_earth_only_things_for_earth_skills`（4 種 × 8 種元素）、`test_workshop_greys_out_terrain_exactly_when_the_validator_would`、`..._shockwave_and_stoneskin_like_the_validator`、`test_the_composer_only_uses_earth_only_parts_for_the_earth_theme`（400 種子）；LLM：`tests/skillgen/test_proposal_54d.py` |
| 震波：敵方命中／未命中、友方不擲、會飛、已倒地 | `test_shockwave_on_enemies_rolls_to_hit...`、`..._on_allies_does_not_roll...`、`..._on_everyone_rolls_for_enemies_only`、`..._ignores_flying_and_already_prone_units`（另有 54b 原測試） |
| 大地種子卡片數字＝實戰 | `test_quake_wave_card_matches_the_fight`、`test_rock_smash_deals_half_again_to_prone_targets`、`test_a_pure_terrain_earth_skill_lowers_exactly_the_nine_tiles_the_card_says` |
| 工坊選大地＋只有下陷合法、火＋下陷不合法 | `test_workshop_pure_terrain_skill_with_earth_passes_the_earth_rule`、`tests/api/test_workshop_earth_54d.py` |
| 重播 | `test_a_battle_with_quake_wave_and_rock_smash_replays_identically` |
| pytest（engine、content、skillgen、narrative、roguelite、api、llm） | 全過（-n 8） |
| `tests/cli`（`-m "slow or not slow" --timeout=3000`） | 148 項：快照重錄（`cli_output_hashes.json`、`llm_propose_mock.txt`），`test_budget_cli.py` 的技能數 268→270，其餘通過 |
| vitest／build／tsc | vitest 105 檔全過（新增 `CheckPanel.test.ts`）；`pnpm build`、`tsc --noEmit` 通過 |
| ruff、format、mypy（727 檔）、lint-imports（7 kept） | 通過 |
| 內建瀏覽器（埠 8012，驗完已關，PID 54812） | 1600×900：技能元素晶片（含「不使用技能元素」）、火元素時隆起／下陷卡片停用並寫原因、預覽武器下拉；800×600：下拉與卡片不橫向溢出（scrollWidth 785 < 800）；選「斧」後卡片「縮放：手上武器的屬性」→「縮放：力量」，卡片「技能元素：大地」 |
| 排版煙霧檢查（先 `localStorage.clear()`） | 800×600 全 PASS、1600×900 全 PASS、shortBottom 全 PASS（第一次與 1600×900 同頁連跑時「更多動作選單」一項 FAIL，重新載入單獨跑 PASS，判斷為連跑的假警報） |

## 複雜度 noqa

沒有新增 C901／PLR 類 noqa。

## 待 PM 決定

1. **石膚術沒做**：單體（1 AP、1 階）可用預算約 7～8，石膚 3 點 × 單體友方 0.95＝2.85（< 70% 下限約 4.9）。補救選項：(a) 持續 4 回合單體 5.7 點、冷卻 2＝72%（但和「2 回合」不符）；(b) 把 `stoneskin` 的 `budget_points` 提高（例 5）；(c) 放寬單體增益的窗。
2. **大地崩陷沒做（純地形預算過低）**：下陷 base 4 點，3×3 乘形狀倍率後仍約 4.0 點，最低花費（1 AP、1 階）可用約 7.4，最高只到 55～60%。**同理工坊的「只有隆起或下陷的技能」永遠會被判過弱**（互斥規則已放行，預算窗擋下）。建議把 `raise_terrain`／`lower_terrain` 的 `base_points` 拉到 7～8（要重新檢查築高台、陷地術），或規格接受附帶 slow 這類小效果。
3. 因此 `test_coverage` 的原語允許清單移除了 `shockwave`，`stoneskin` 保留並改寫原因。
4. 碎岩擊以兩個傷害效果（×1.2 ＋ 倒地時 ×0.6）達成「倒地時 ×1.5」，兩段各有暴擊判定。若要單一效果乘數需新增效果欄位。
5. 多個元素標籤取第一個非物理者（目前內容沒有這種手寫技能，只有 `[physical, 元素]`）。
6. 震地波定 2 AP（1d8，直線 4）才落在 70～100%；若要 1 AP 需降傷害與直線長度。
7. 工坊預覽武器預設主角武器的接線（`heroWeapon`）已就緒，但 App 沒有「從一輪進工坊」的入口，需另一段決定資料來源。
8. 合併 3-54c 時：`skill_icons.json`、CLI 快照、`glossary.json`、`LOG_FORMAT` 請 PM 重產／處理。
