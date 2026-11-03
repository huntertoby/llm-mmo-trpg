# Phase 5A-M1 完成報告：引擎機制①（蓄力強招預告、死亡時留下表面、開場隱蔽、同門相護）

> 實作者：implementer agent（2026-11-03）。規格：`docs/phases/Phase5計畫.md` 第 14 節（先寫入規格、commit `23079900`，再實作；合併 main 時 5A-7 已占第 13 節，本段規格改為第 14 節、「之後各段規格」改為第 15 節）。
> 動到：`src/trpg/engine/`（`battle.py`、`reactions.py`、`skills/cast.py`、`effects/__init__.py`、`view.py`、`runner.py`、新 `death_surfaces.py`、`ai/utility.py`、`ai/composite.py`、新 `ai/priority.py`）、`src/trpg/content/`（`battle.py`、`environment.py`、`world_enemies.py`、`library.py`）、`src/trpg/narrative/events.py`、`content/`（`reactions.yaml`、`statuses.yaml`、新技能 `skill_nine_turns_revival.yaml`、5 個雲嶺範本、`world/enemies.yaml`）、`docs/phases/戰鬥紀錄格式變更.md`、測試。沒有動 `trpg.world`、`trpg.api`、`client/`（前端沿用既有蓄力預告、表面與狀態的畫法）。

## 1. 四個機制

### 1.1 蓄力強招預告（沿用 6.23 #5 延遲段）

- **資料**：強招就是 `followup.when: delayed`、`release: next_turn` 的技能，`ap_cost` 3（整回合）。施放時施放者帶 `charging`、發 `followup_charged`（預計範圍，網頁 `telegraph.charges` 已經畫在地圖上）；下回合開始以當下位置結算第二段；倒下、暈眩、冰凍取消（`followup_cancelled`）。
- **新技能** `skill_nine_turns_revival`「九轉回天」（青霧執事）：第一段自身小護盾（1d4）；第二段以自己為中心 3×3 的友方治療 4d8（`wis` 加成）；法力 12、冷卻 4。過預算檢查（下限 70%）。
- **AI**：治療型延遲段的估值改看預計範圍內受傷的友方（`rewrite.delayed_heal_points` × 人數，含自己）；候選估計（`composite_estimate`）同樣看受傷友方，沒有就不納入。
- **打斷**：主角方 AI 擊倒正在蓄力的敵人、或讓它帶上跳過回合的狀態（暈眩、冰凍）時，額外 `rewrite.interrupt_points`（`trpg.engine.ai.priority`）。
- 戰鬥紀錄：既有的「◷ X 開始蓄力「九轉回天」：下回合開始時釋放（以自己為中心，目前預計影響 N 格）」與取消文字。

### 1.2 死亡時留下表面

- **資料**：`StatusDef.on_death_surface: {surface, radius 0～2, duration?}`；只能用在 `polarity: neutral`、`expires: never`、沒有 `duration` 的狀態（不被淨化、驅散、奪取）。由範本 `opening_statuses` 開場掛上。
- **行為**（`trpg.engine.death_surfaces`）：帶這種狀態的單位倒下（`unit_downed` 觸發）時，在倒下的格子與曼哈頓半徑內的格子（依 (y, x)）產生表面（`create_surface`，`cause: death_surface`；照一般規則查互動表、致命地形與牆壁不產生）。做法同定時炸彈「倒下時爆炸」。
- **新狀態** `shard_burst`「碎晶」：倒下時留下半徑 1 的水（代決 5AM1-6）。
- **AI**：預覽本來就會跑倒下觸發，擊倒碎晶傀儡的預覽含表面事件（`surface` 權重）；之後站位照既有的有害表面估值。
- 戰鬥紀錄：「(x, y) 出現了水（倒下時留下的）」。單位卡的狀態欄顯示「碎晶」與說明（前端狀態圖示照 glossary 的極性畫，不需新美術）。

### 1.3 開場隱蔽

- **資料**：`UnitTemplate.opening_statuses: [{status, duration: 1～2 | 省略}]`；精英詞綴 `EliteAffixDef.add_opening_statuses`（接在範本的後面）。載入時檢查狀態存在。
- **行為**：開戰時先施加範本的、再施加 `UnitSpawn.opening_statuses`（5A-6 下一場 buff），擲先攻前、不擲抵抗；有限持續回合仍受 5A-6b 的 2 回合上限。
- 霧隱的＝`{status: concealed, duration: 1}`：在自己第 1 回合結束時移除。
- **AI**：隱蔽讓攻擊有劣勢、太遠的遠程不能選，預覽的命中率本來就算進去。
- 戰鬥紀錄：既有的 `status_applied` 文字。

### 1.4 同門相護

- **資料**（`reactions.yaml`）：內建反應 `kin_ward`「同門相護」：`effect: shield_ally`、事件 `kin_hit_in_range`、`range: 2`、`kin_tag: sect`、`shield_dice: 1d4`、`shield_flat: 2`、`blocked_by_silence: true`。`ReactionDef` 的新欄位都有檢查（`shield_ally` 與事件成對、必填範圍、標籤、護盾量）。範本 `reactions` 寫一條 `{reaction: kin_ward, when: {event: kin_hit_in_range}}` 才有。
- **行為**（`reactions.kin_ward_reactions`）：敵人的攻擊（普攻或技能）命中、傷害之前，被打的單位的友方（依單位 ID）中，第一個「目標在 2 格內、兩人都帶 `sect`、沒被沉默、本輪還能反應」的持有者替他加一層護盾（`shield` 效果；已有護盾時照規則取大值）。佔本輪反應（`reactions_per_round` 1 ＝「每輪 1 次」，和格擋共用）；`auto`／`prompt`／`off` 照一般反應規則；一次攻擊最多一層。
- **AI**：預覽會結算反應，同門護盾讓預估傷害變小；主角方擊倒帶 `kin_ward` 的敵人額外 `rewrite.priority_kill_points`（「先打補師」）。
- 戰鬥紀錄：「⟳ 青霧道童 反應：同門相護」＋既有的護盾文字；單位卡的反應規則欄顯示「範圍內的同門被攻擊命中時（傷害之前）」。

### 1.5 AI 數值（`RewriteAiRules` 預設，初值、未經模擬）

`delayed_heal_points` 5、`priority_kill_points` 10、`interrupt_points` 12（等值傷害點數 × `damage` 權重）。沒有寫進 `ai_profiles.yaml`（用 schema 預設值，和其他 `rewrite` 欄位的慣例一樣可以在 yaml 覆寫）。只在目標有這些特性時加分。注意「打斷」對兩邊都成立：敵方 AI 也會優先擊倒、暈眩正在蓄力的主角（例如主角用蓄力斬時），原型裡用到延遲段的戰鬥 AI 分數會略有不同。

## 2. 雲嶺換成正式機制（只改 content）

| 敵人／詞綴 | 原替代品（5A-3） | 正式機制 |
|---|---|---|
| 青霧道童、煉丹師（含水煉丹師變體）、青霧執事 | — | 反應 `kin_ward`（另保留預設的格擋、藉機攻擊） |
| 持劍弟子 | 挺身而出（5A3-1） | 拿掉挺身而出：被相護的前排 |
| 青霧執事 | 聖域＋回春＋調息（5A3-2） | 聖域＋**九轉回天**＋調息（回春換成九轉回天，技能欄不變） |
| 碎晶傀儡 | 沒有（5A3-2） | `opening_statuses: [{status: shard_burst}]` |
| 詞綴 霧隱的 | 受擊時滑步脫身（5A3-3） | 開場隱蔽 1 回合（不再加技能，所以持劍弟子、武僧、霧行者現在也能抽到） |

護法武僧的挺身而出是 18.2.1「嘲諷／守護」本身，不動。

## 3. 戰鬥紀錄版號

`LOG_FORMAT` `/101` → `/102`（`docs/phases/戰鬥紀錄格式變更.md`、`runner.py` 文件字串、測試字面值）。沒用到新欄位的戰鬥結算與 `/101` 相同。

## 4. 代決（照規格 13.9；實作補的另列）

1. **5AM1-1** 蓄力強招沿用 6.23 #5 延遲段；「打斷」＝倒下、暈眩、冰凍（沉默不打斷，同既有延遲段）。
2. **5AM1-2** 「花一回合蓄力」＝ `ap_cost` 3；下回合開始釋放後仍可行動。
3. **5AM1-3** 同門相護的持有者是補師型修士（道童、煉丹師、水煉丹師、青霧執事）；持劍弟子是被相護的前排；武僧保留挺身而出。
4. **5AM1-4** 同門相護佔本輪反應（每輪 1 次，和格擋共用）；命中後、傷害前；普攻與技能都算；一次攻擊只一層。
5. **5AM1-5** 護盾量 `1d4+2`；同門＝`sect` 標籤；沉默、暈眩時不能用。
6. **5AM1-6** 碎晶傀儡的「帶電表面」：引擎沒有帶電表面、新表面要新美術 → 留下半徑 1 的 **水**（會導電）。
7. **5AM1-7** 死亡表面做成狀態 `on_death_surface`，由範本 `opening_statuses` 掛上；狀態中性、不倒數。
8. **5AM1-8** 開場隱蔽 `duration: 1`；範本開場狀態也受 5A-6b 的 2 回合上限。
9. **5AM1-9（改）** 九轉回天第二段：規格寫「半徑 3、2d8」，但延遲段的第二段形狀只能是 `cross`／`square3`／`ring`（6.23 schema），2d8 也低於預算下限 → 改成 **自己為中心 3×3 的友方、4d8**；冷卻 4、法力 12。
10. **（實作補）** 開場狀態只在開戰時施加；地圖事件中途產生的援軍（`spawn_templates`）不帶範本的開場狀態。
11. **（實作補）** AI 的三個新數值用 `RewriteAiRules` 的預設，不寫進 `ai_profiles.yaml`。

## 5. 待 PM 決定

- **帶電表面**：18.2.2 碎晶傀儡要「帶電表面」，目前用水代替（雷電打上去才傷人，不是持續電擊）。要真正的帶電表面需要新表面種類與美術（美術 PM）。
- **九轉回天的範圍**：設計是「全隊回大量 HP」，延遲段第二段只能是十字／方陣／環形，目前 3×3。要更大的範圍需要擴充延遲段可用的形狀（引擎小改）。
- **沉默能不能打斷蓄力**：18.2.1 寫同門相護可以用「沉默」破解（已做），強招打斷目前沿用延遲段（倒下、暈眩、冰凍）。要不要讓沉默也打斷法術型強招？
- **單位卡的「特性」欄**：同門相護、碎晶目前透過反應規則與狀態欄顯示；要另外的特性欄需改 API 與前端。
- 數值（護盾 1d4+2、九轉回天 4d8、AI 三個點數）都是初值，要等遭遇強度模擬。

## 6. 檢查紀錄

- 合併 main 前：`tests/engine tests/content tests/world tests/narrative tests/test_architecture.py tests/sim tests/roguelite -n 8`：6722 passed、6 failed → 全部是本段預期的變化，已修：覆蓋率允許清單加 `shard_burst`、內建技能數 373 → 374、`test_world_enemies`（霧隱的不再加反應技，持劍弟子、霧行者現在可套）、`test_enemy_growth`（反應技改名改看護法武僧）、技能圖示 fixture 重產。
- 合併 main（`0b38962e`，5A-7）後：`tests/world tests/api tests/content tests/engine/test_mechanics_5am1.py tests/narrative -n 8`：2769 passed、1 failed（glossary fixture 多了 `shard_burst`、`kin_ward`）→ `scripts/export_client_fixtures.py` 重產後通過。
- `tests/cli -m "slow or not slow" -n 8 --timeout=3000`：169 passed、11 failed（`skills_list`、`skills_show_all/06～15` 的雜湊，因為新增技能「九轉回天」）→ `UPDATE_CLI_SNAPSHOTS=1`（不加 -n）重產後通過。
- 前端：`npx vitest run` 124 個檔、1198 passed（新增狀態 `shard_burst` 的圖樣：只用既有的星形與水滴筆畫，`client/src/render/statusIcon.ts`）；`npm run build` 通過。
- `ruff check .`、`ruff format --check .`（1571 files）、`mypy`（strict，1018 檔）：通過；`lint-imports`：9 個契約全部 KEPT。
- 重播：`trpg battle --map swamp --seed 7 --log-json` ＋ `trpg battle replay`：重播驗證通過（88 個動作、313 個事件）。

## 5A-M1b 收尾（玩法 PM 代決 2026-11-03）

**1. 沉默打斷法術型蓄力**：`trpg.engine.delayed` 的 `status_applied` 觸發新增判斷——沉默（`blocks_spells`）施加到正在蓄力的單位，而且蓄力的技能是法術型（`is_spell_for_silence`）時取消蓄力（`followup_cancelled`，`reason: silenced`，紀錄文字「法術被沉默打斷」）。武器技型延遲段與定向蓄力（吐息）照舊只吃倒下、暈眩、冰凍。AI 的「打斷蓄力」加分（`ai/priority.py`）同樣算沉默（只對法術型蓄力）。`LOG_FORMAT` `/102` → **`/103`**（`戰鬥紀錄格式變更.md` 已加條目，`/102` 紀錄無法重播）。測試：`tests/engine/test_delayed_followup.py`（法術型被沉默取消、武器型不取消）。

**2. 單位卡「特性」欄（#82）**：新 `trpg.narrative.unit_traits`（依單位範本；變體與 `<範本>_<詞綴>` 的精英範本會解析）產生中文句：精英詞綴、被動技能、非預設反應（同門相護等）、開場狀態（碎晶、隱蔽）；`UnitView.traits_zh`（預設空）由 `api/presenter.traits_view` 填入（主角不列；每步視圖同樣填）。前端 `UnitInfo` 加「特性」列（`traitRows`，沿用現有表格與 `RuleText`，沒有新的浮動卡）。OpenAPI 與 `schema.d.ts` 已重產。測試：`tests/narrative/test_unit_traits.py`、`tests/api/test_unit_traits_api.py`、`client/src/ui/unitInfoTraits.test.ts`。

**備註（待 PM 決定）**：特性欄只看範本，戰鬥中才加上的狀態不算；開場狀態是範本資料，倒數結束後欄位仍列出（描述「這一族出什麼題」）。未在瀏覽器實測畫面（只有 vitest 與 build）。
