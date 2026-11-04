# Phase 6F-3 報告：巡檢 bug 修正＋Boss 戰的 dev 入口

> 2026-11-04，實作者（agent）。worktree 分支 `worktree-agent-a4e76d3d0bc8f2644`，從 main `00bc678a`（含 6F-1、6F-2）開工。沒有 push、沒有合併。
> 依據：`docs/phases/Phase6實機巡檢.md` 第 2 節、`docs/art/全遊戲一致性巡檢.md` 第 1 節 #10、`docs/phases/Phase6前10分鐘-12B.md` 第 7 節 #7～#9、`docs/開發PM交接.md` 6.5.1。

## 0. 結論

| # | 項目 | 結果 |
|---|---|---|
| 1 | 「已清空」判斷錯（巡檢 bug 2） | 修好。玩家眼中的「已清空」要連自己的個人隊伍都打完；世界規則不變，**不升 `WORLD_RULES_VERSION`（維持 8）** |
| 2 | 主角、出口被 HUD 蓋住（bug 3） | 修好。鏡頭以「扣掉 HUD 的安全區」置中，地圖邊緣可以捲出 HUD 底下 |
| 3 | 彈窗蓋住左上主角卡（bug 6、美術 #10） | 修好。背包、技能、NPC 面板、遇敵卡、事件卡都在主角卡下方、讓出左右兩欄，太高就在裡面捲 |
| 4 | 大世界圖「你在餘燼集」（bug 5） | 修好。改寫所在地點（例：「你在冬湖」） |
| 5 | 其他低嚴重度 | 修 bug 10（重新載入後的「敵方先手」提示）、bug 18（說明框斷行）；bug 7 已在 6F-1 修掉；其餘列待決 |
| 6 | 盜賊每回合只守護（12B #7） | 找到原因並修 AI：補師上的護盾把匕首傷害全吸收，攻擊收益變 0。改成打掉護盾也照 `shield` 權重給分 |
| 7 | 暗影環打不到相鄰敵人（12B #8） | 不是引擎 bug：環形照內容定義只打「恰好半徑」那一圈。卡片補上「不含相鄰」，加行為一致測試 |
| 8 | 「暗流」寫冰霜卻是物理傷害（12B #9） | 是內容寫錯：配方 `theme: ice` 但傷害是物理。拿掉 theme（同樣的「水花反濺」一起改） |
| 9 | Boss 戰 dev 入口 | 新增 `POST /api/world/characters/{id}/dev-boss`（開發模式＋`TRPG_DEV_ROUTES=1`），前端 `?dev=1` 頂列「Boss 戰（開發）」 |
| 10 | 實戰補拍 | Boss 戰一般畫面、蓄力、大招變暗與微震、重擊、最後一擊、同一招 3 次、事件卡、狀態、3 間室內、10 秒 gif 都拍了；餘燼集酒館沒拍（第 6 節） |

## 1. 逐項

### 1.1 「已清空」判斷（巡檢 bug 2）

- **原因**：渡口石階有兩隊。
  - 「搶渡船的盜賊」是 `personal`（新手任務的個人駐守）。
  - 夜晚巡邏的盾陣是共享隊伍。
  - 21.10 第 9 條和 `content/fields.py` 寫明：個人隊伍不算進共享的「已清空」。所以打贏盾陣就寫了世界的「已清空」，但個人隊伍還在。
- **做法**：只改玩家看到的部分，世界規則不變。
  - `trpg.world.field_enemies.personal_left`：這個角色在那裡還有沒有沒打完的個人隊伍。條件是這個時段會出現、還沒退場（`until_quest`）、這一趟還沒打贏。
  - `cleared_for`：世界已清空，而且 `personal_left` 是否。
  - 區域圖的打勾 `WorldLocationView.cleared` 改用 `cleared_for`。
  - 清空提示：個人隊伍還在時，不說「已清空」，改說「這一隊打散了，但渡口石階還有別的敵群。」（`event_lines` 多一個 `now` 參數，路由有傳）。
- **版號**：`WORLD_RULES_VERSION` 不升（維持 8）。
  - 世界狀態與日誌重播完全不變，只改畫面。
  - 6.6 的規則是「改了 `trpg.world` 的規則程式、同一份日誌重播會不同」才加一，這次不符合。
  - 規則層面的含意（例如有個人隊伍時能不能紮營）列進待決。
- **檔案**：`src/trpg/world/field_enemies.py`、`src/trpg/api/world_presenter.py`、`src/trpg/api/routes/world.py`。
- **測試**：`tests/world/test_cleared_for_6f3.py`，6 個表格測試，實際跑 `after_fight`、`world_step`。

### 1.2 鏡頭避開 HUD（巡檢 bug 3）

- `client/src/world/camera.ts`：
  - `clampAxis` 多兩個參數 `lo`、`hi`（可視區兩端被 HUD 佔掉的寬度）。
  - 內容比安全區小時，在安全區裡置中。
  - 否則以安全區中心跟隨，範圍夾在 [−lo, 內容−可視區＋hi]。地圖邊緣最多捲到安全區的邊上，主角和邊上的出口不會躲在快捷列、右欄底下。
  - 不給 insets 時行為和 6B-6 相同（舊測試全過）。
- `client/src/world/hud.ts` 的 `hudInsets`：
  - 上＝主角卡（含隊友卡）的下緣；
  - 下＝快捷列的上緣；
  - 右＝右欄（地名、小地圖、時間、錢包、任務追蹤）的左緣。
- `WorldField`、`WorldScreen` 把 insets 傳進鏡頭。
- **測試**：`camera.test.ts` 新增 4 個。在 1600×900、1040×624、800×600 三種尺寸、四種地圖大小下，主角在每一格都落在安全區內，走到出口旁時出口也在。
- **實機**：`6f3_01`～`03`（獵戶小屋重新載入，三種尺寸）、`6f3_08`／`09`（冬湖）。主角都在快捷列上方，出口格看得到。

### 1.3 彈窗避開四角 HUD（巡檢 bug 6、美術 #10）

- `hud.ts` 的 `popupBox(layout, want)`：
  - 水平置中；
  - 上緣＝主角卡下緣＋8；
  - 下緣停在快捷列上方，不夠高就在彈窗內捲；
  - 寬度讓出左右兩欄（取較寬的一邊，兩邊對稱）。
- `WorldHud` 的浮動面板（背包、技能、成長、NPC…）與中上方卡片（遇敵卡、事件卡）都用它。
- **測試**：`client/src/world/popupBox6f3.test.ts`，13 個。三種尺寸 × 隊友 0／2 人 × 追蹤展開／收合，面板與遇敵卡都不蓋 HUD。
- **實機**：
  - 背包 `6f3_04`、`06`，技能 `6f3_05`、`07`；
  - 遇敵卡 `6f3_10`～`12`；
  - NPC 面板 `6f3_16`、`17`；
  - 事件卡 `6f3_40`、`41`。
- **6.5.1 浮動卡實測**（大世界圖浮島的說明卡，因為這段改了它的內容）：
  - 1600×900 與 800×600 都照「滑過出現 → 滑進卡片不關 → 捲動不關 → 點一下釘住（金色）→ Esc 關閉」走完。
  - 卡片只有一行，沒有可捲的內容，捲動只確認不會關。
  - 截圖：`6f3_14`、`6f3_15`。
- **排版煙霧檢查**：在 `/?dev=1&anim=0.1` 先 `localStorage.clear()`，再跑 `__layoutSmoke.runCase`。1600×900、1040×624、800×600 三種尺寸全 PASS（共 30 項）。

### 1.4 大世界圖的所在地（巡檢 bug 5）

- **原因**：`hereText` 固定寫該區的城鎮。
- **做法**：`atlasScene` 取所在區區域圖上 `current` 的地點名，傳給 `AtlasArtIsland.here`。不新增伺服器欄位。
- **測試**：`atlas.test.ts` 新增 2 個（荒原站在灰渡口寫「你在灰渡口」；不是所在區照舊）。
- **實機**：`6f3_13`（「你在冬湖」）。

### 1.5 其他低嚴重度（巡檢第 2 節）

| bug | 處理 |
|---|---|
| 7 結算顯示 replay 指令 | 6F-1 已改成只在開發模式顯示，確認沒問題 |
| 10 重新載入跳出「敵方先手：第 1 輪…」 | 修：開場說明只在第 1 輪跳出（`BattleScreen`） |
| 18 「點了看區／域圖」斷行 | 修：浮島說明卡每一段（「・」分開）不在中間斷行（`AtlasMap`，用共用 `Hint` 的 `rich`） |
| 17 鐵娘提到斷崖幫 | 不是 bug：內容本來就有斷崖幫荒原分隊（`npcs/ashen_waste.yaml`、`encounters/ashen_waste.yaml`） |
| 8、9、11、12、13、14、15、16 | 要改規則、設計或美術，列進待決 |

### 1.6 盜賊每回合只守護（12B #7）

- **重現**（`scratchpad` 的 `world_probe.py`）：
  - 照 12B 的 B 建角（匕首、冰凍＋隱蔽、精靈、雲嶺出身，種子 1155）。
  - 預設隊伍是賽倫＋回春，在渡口石階打正式遭遇。
  - 主角用腳本代打，敵人用正式 AI。
  - 盜賊的守護佔敵方動作 21%（20 場合計 260 次），每場平均 11.25 輪，和 12B 的現象一致。
- **原因**：
  - 回春一直替大家上盾（13～15 點）。盜賊匕首一下約 4～6 點，全被護盾吸收。
  - AI 的傷害收益只算扣到 HP 的部分，所以攻擊相鄰敵人是 0 分或負分，守護的 `defend × 附近敵人數` 3 分就贏了。
  - 補師持續上盾 → 盜賊永遠守護。
- **修法**：`trpg.engine.ai.utility._shield_broken`。預覽事件裡對敵人被吸收的傷害，照 `shield` 權重給分（和替自己人加盾等價，算法同護盾收益：min／max 平均 × 命中率）。沒有新增權重或內容。
- **影響範圍**：所有效用 AI 的選擇，只在「對手身上有護盾」時改變。沒有護盾的戰鬥結果逐位元相同（見第 3 節：預設陣容 10 張地圖 0 張改變，swamp 種子 7 重播不變）。
- **重播**：戰鬥紀錄存的是動作，重播不經過 AI，舊紀錄照樣重播一致。大世界日誌的 `fight` 也帶完整步驟，所以 `WORLD_RULES_VERSION` 不用升。
- **測試**：
  - `tests/engine/test_ai_shield_break_6f3.py` 新增 4 個（盜賊對有護盾的相鄰敵人選攻擊不選守護；舊 AI 下其中 3 個會失敗）。
  - 種子綁定的 AI 測試換種子（AI 軌跡改變），各自在註解記一筆：
    - `test_gamble.py`：4、20 → 3、55；
    - `test_scene_ai.py` 推倒石柱：2 → 7；
    - `test_skill_shaping.py` 坦克：1 → 3。

### 1.7 暗影環打不到相鄰的敵人（12B #8）

- `content/skill_shapes.yaml` 的環形定義是「影響與施放者切比雪夫距離**恰為** radius 的格子」。半徑 2＝16 格的外圈，相鄰的 8 格不在內。引擎照定義結算，**不是 bug**。
- **做法**：卡片的形狀說明在半徑 ≥ 2 時多一段「只打距離 2 的一圈，不含相鄰」（`narrative/skills.py` 的 `shape_summary`）。
- **測試**：`tests/engine/test_ring_shape_6f3.py`，8 個行為一致測試，實際跑引擎。半徑 2 時相鄰、斜角相鄰、距離 3 打不到，距離 2 打得到；半徑 1＝相鄰 8 格；卡片文字一致。
- 「暗影環」的概念寫「咬向周圍的敵人」，和外圈的形狀不太合。要不要改成實心圓或限半徑 1，屬於設計，列進待決。

### 1.8 「暗流」寫冰霜卻是物理傷害（12B #9）

- **原因**：`content/skill_composer.yaml` 的配方 `undertow`（暗流）`theme: ice`，但效果寫 `element: physical`。卡片的元素依 06 6.33 取技能主題（tags），所以寫成「冰霜」。
- 全面掃描配方：主題和傷害元素不一致的只有 `undertow`、`splash_retort`（水花反濺），兩個都是潮濕系。
- **做法**：拿掉這兩個的 `theme`（主題退回傷害元素＝物理），卡片不再寫冰霜。
  - 沒有改成冰霜傷害：冰霜打在水上會凍結，等於新增一個被動硬控，屬於平衡決定。
- **測試**：`tests/content`、`tests/skillgen`、`tests/narrative` 全跑過。
- 這個檔案 6E-W 可能也在改，合併時注意這兩行。

### 1.9 Boss 戰的 dev 入口

- **伺服器**：`POST /api/world/characters/{id}/dev-boss?location=cloud_summit&level=&region=&ai_until=`（`src/trpg/api/world_dev.py`）。
  - 只在 `config/server.toml` 的 `dev_mode` 開時掛（新的 `world.dev_router`），**而且**要 `TRPG_DEV_ROUTES=1`，否則 404。
  - **不碰世界**：用角色存檔的複本（換到 Boss 地點、可選等級）走正式的 `make_encounter` → `prepare_battle`，在戰鬥工作階段表開一場。
    - 不寫日誌、不寫角色、不登記成角色的戰鬥，打完也不回寫。
    - 正式遊戲的霧牆與主線限制照舊，一般玩家碰不到。
  - `ai_until=charge|last`（截圖用）：效用 AI 連主角一起代打，停在「Boss 蓄力中」或「只剩一名敵人且 HP ≤ 15%」那一刻、輪到主角時。用存檔重播的方式還原工作階段。
- **前端**：`?dev=1` 時大世界頂列有「Boss 戰（開發）」。
  - 網址可加 `&boss=地點`、`&bosslv=等級`、`&bossai=charge|last`。
  - 打完「回到地點圖」，和循環賽重播一樣不同步世界。
- roguelite 的頭目沒有蓄力招，這段沒改內容。
- **測試**：`tests/api/test_world_dev_boss_6f3.py`，5 個。
  - 開的是霧鎖真人、世界與日誌不變；
  - 沒設環境變數 404；
  - 開發模式關時不掛；
  - 城鎮拒絕；
  - `ai_until=charge` 停在 Boss 蓄力中。

## 2. 檔案清單

- **Python**：
  - `src/trpg/world/field_enemies.py`
  - `src/trpg/api/world_presenter.py`、`src/trpg/api/routes/world.py`、`src/trpg/api/app.py`
  - `src/trpg/api/world_dev.py`（新）、`src/trpg/api/world_schemas.py`
  - `src/trpg/engine/ai/utility.py`
  - `src/trpg/narrative/skills.py`
- **內容**：`content/skill_composer.yaml`（2 行）。
- **前端**：
  - `client/src/world/camera.ts`、`hud.ts`、`WorldField.tsx`、`WorldHud.tsx`、`atlasScene.ts`、`AtlasMap.tsx`
  - `client/src/render/worldMapArt.ts`
  - `client/src/screens/WorldScreen.tsx`、`BattleScreen.tsx`
  - `client/src/api/client.ts`、`types.ts`、`schema.d.ts`、`client/openapi.json`
- **測試**：
  - 新增：`tests/world/test_cleared_for_6f3.py`、`tests/engine/test_ring_shape_6f3.py`、`tests/engine/test_ai_shield_break_6f3.py`、`tests/api/test_world_dev_boss_6f3.py`、`client/src/world/popupBox6f3.test.ts`
  - 修改：`client/src/world/camera.test.ts`、`atlas.test.ts`、`tests/engine/test_gamble.py`、`test_scene_ai.py`、`test_skill_shaping.py`
- **截圖**：`docs/art/6f3_*`（38 個檔案，第 5 節）。

## 3. 測試數與檢查

- **新增測試**：Python 23 個（6＋8＋4＋5），vitest 19 個（4＋13＋2）。
- **Python 相關測試**：
  - `tests/engine tests/sim tests/world tests/api tests/roguelite`：6272 個，-n 8，換種子後全過。
  - `tests/content tests/skillgen/test_whiteboard_3w2b.py`：2634 個，全過。
  - `tests/narrative tests/skillgen`：4151 個，全過。
  - `tests/test_architecture.py tests/api/test_dev_mode_guard.py`：24 個，全過。
- **CLI 快照**：`-m "slow or not slow" tests/cli --timeout=3000`，180 個，175 過、5 個快照不同，都在預期內：
  - `skills_list`、`skills_show_all/04`、`/08`：環形卡片多了「不含相鄰」；
  - `battle_oil_depot_fire_7`、`battle_frozen_lake_push_3`：AI 打護盾，軌跡改變。
  - 已用 `UPDATE_CLI_SNAPSHOTS=1` 重產（`tests/cli/snapshots/cli_output_hashes.json` 改 5 行），重跑 19 個全過。
- **vitest 全部**：2453 個，2452 過。唯一失敗的 `src/battle/cleanup6rf.test.ts` 是 5 秒逾時：它用 TS 剖析器掃整個 `client/src`，當時背景同時在跑 `-n 8` 的 CLI 測試、CPU 被佔滿；沒改到它檢查的寫法。背景測試結束後單獨重跑，7 個全過。
- **`corepack pnpm -C client build`**：成功。
- **每次 commit 前**：`ruff check`、`ruff format --check`、`mypy src`（516 檔）、`lint-imports`（13 kept）都過；每次都跑了 `trpg battle --map swamp --seed 7` 加重播，**重播一致，結果沒有改變**（敵方勝、第 5 輪、88 個動作、313 個事件，第 6 點的 AI 修改前後相同）。

## 4. AI 修改前後的模擬對照

做法：同一份程式只換 `utility.py` 一個檔案（改前＝HEAD、改後＝這段），跑同樣的種子。

**`trpg sim maps --seeds 20`（預設陣容，沒有人上盾）**：10 張地圖的勝率與平均輪數**完全相同**（58.0%、4.60 輪），0／10 張地圖有變化。

**`trpg sim maps --seeds 20 --ally-build build_support`（我方補師會上盾）**：

| 地圖 | 勝率 前 | 勝率 後 | 平均輪數 前 | 平均輪數 後 |
|---|---|---|---|---|
| bridge_chasm | 40% | 50% | 6.15 | 5.90 |
| cliff_outpost | 55% | 70% | 6.45 | 6.45 |
| dark_forest | 90% | 85% | 5.90 | 5.60 |
| frozen_lake | 90% | 85% | 5.50 | 5.25 |
| lava_crossing | 85% | 95% | 6.30 | 6.15 |
| narrow_halls | 65% | 70% | 7.25 | 6.50 |
| oil_depot | 30% | 45% | 7.45 | 6.25 |
| open_plain | 50% | 75% | 6.50 | 5.90 |
| ruined_fort | 30% | 45% | 6.85 | 6.20 |
| swamp | 45% | 65% | 7.95 | 6.95 |
| **平均** | **58.0%** | **68.5%** | **6.63** | **6.12** |

**大世界渡口石階**（12B 的 B 建角＋賽倫、回春，20 個種子）：

| 主角操作 | 敵方守護次數 前→後 | 敵方攻擊次數 前→後 | 平均輪數 前→後 | 我方勝 前→後 |
|---|---|---|---|---|
| 全部 AI | 218 → 69 | 404 → 637 | 8.90 → 8.45 | 20 → 20 |
| 腳本玩家（只放技能、不走位） | 260 → 76 | 663 → 872 | 11.25 → 11.05 | 17 → 19 |

- 守護少了約 7 成，剩下的多半是盾衛（`guard` 行為模式本來就偏好守護）和還走不到的盜賊。
- 腳本玩家的輪數幾乎沒變，因為腳本主角不走位，拖長的主因在腳本本身。實際玩家會打得更快。
- 補師上盾時我方勝率上升（+10.5 個百分點），這是平衡層面的變化，數值不在這段調，列進待決。

## 5. 截圖（docs/art/6f3_*）

全部在自己的無頭 Chrome（`--mute-audio`，載入前把 `trpg.audio.v1` 主音量設 0，網址帶 `mute=1`）、自己的伺服器 8366（`TRPG_DEV_ROUTES=1`、LLM 關、存檔放 scratchpad）拍攝。

| 檔名 | 內容 |
|---|---|
| `6f3_01_hunter_hut_1280`、`02_…_1040`、`03_…_800` | 獵戶小屋重新載入：主角在快捷列上方，出口看得到（bug 3） |
| `6f3_08_winter_lake_1280`、`09_…_800` | 冬湖重新載入（bug 3） |
| `6f3_04_bag_1600`、`06_bag_1040` | 背包在主角卡下方、讓出右欄（bug 6） |
| `6f3_05_skills_1600`、`07_skills_800` | 技能面板（bug 6） |
| `6f3_10`～`12_encounter_*` | 遇敵卡三種尺寸（bug 6） |
| `6f3_16`、`17_npc_panel_*` | NPC 面板（石師傅，bug 6） |
| `6f3_13_atlas_here` | 大世界圖「你在冬湖」（bug 5） |
| `6f3_14`、`15_atlas_hint_*_hover` | 浮島說明卡：一段不斷行（bug 18）、6.5.1 實測 |
| `6f3_20_boss_start` | Boss 戰一般畫面（雲頂觀，霧鎖真人） |
| `6f3_19_boss_charging` | Boss 蓄力中（環境預告寫「下回合開始時釋放」） |
| `6f3_21_boss_ultimate_dark` | Boss 大招：四周變暗 |
| `6f3_23_boss_shake_zoom` | 大招當下 6 格連拍放大（左上角地圖邊緣的位移就是震動） |
| `6f3_22_heavy_hit` | 重擊：回春受到 22 點（56 → 34，39%） |
| `6f3_24_final_blow_flash`、`25_…_slow`、`26_…_victory`、`27_…_strip` | 最後一擊（暴擊 −19 擊倒 Boss）→ 放慢 → 勝利 |
| `6f3_30`～`32_skill3x_1～3`、`33_skill3x_compare` | 6N-8 同一招 3 次：火焰箭、目標 5 格外（陣眼石靈）、`anim=0.1`、放大 1.5 倍；每張左到右是起手、軌跡、爆發 |
| `6f3_40`、`41_event_card_*` | 實機事件卡（冬湖的「商隊」，地圖上的「！」） |
| `6f3_50_interior_stone_smithy` | 石記鐵鋪 |
| `6f3_51_interior_capital_tavern` | 樞島酒館（裡面沒有 NPC，同 bug 12） |
| `6f3_52_interior_capital_smithy` | 樞島鐵匠鋪 |
| `6f3_60_status_burning`、`61_status_root` | 狀態動作：燃燒、定身 |
| `6f3_battle_10s.gif` | Boss 戰 10 秒（1.7 MB、10 fps、760 寬）：含 Boss 大招變暗＋微震，以及回春被聚雷打掉 39% 的重擊 |

**觀察**：

- **6N-8 同一招 3 次**：目標放在 5 格外、放慢 10 倍、放大後，三次的起手光圈、飛行中的火球位置、命中光柱都很像，只看得出細小差別（火球在軌跡上的位置、第 3 次多了燃燒）。「三次看得出不一樣」在實戰還不明顯，請美術 PM 看 `6f3_33`。
- **浮動字重疊**（bug 8）在最後一擊又看到一次：「擊倒／暴擊 −19／吸收 3」疊在一起（`6f3_27`）。

## 6. 沒拍到的

- **餘燼集酒館**：要另開一個灰燼荒原已開放的世界，從雲嶺一路走過渡口。這段時間不夠，沒有拍。剩下 3 間室內都拍了。
- **冰凍、中毒、暈眩、帶電**：這幾場戰鬥裡沒有人施加。只拍到燃燒和定身。

## 7. noqa

- `src/trpg/narrative/skills.py`：`radius >= 2  # noqa: PLR2004`。「半徑 2 以上的環形不含相鄰」的 2 是規則本身（半徑 1 的環就是相鄰 8 格），抽成常數反而難讀。

## 8. 待 PM 決定

1. **有個人隊伍時能不能紮營、遇敵機率**（bug 2 的延伸）：世界的「已清空」照 21.10 第 9 條不算個人隊伍，所以別的玩家打完共享隊伍後，自己的個人駐守還在，也能在營地紮營。這是規則問題，沒有改。
2. **暗影環的形狀**：環形外圈（半徑 2 不含相鄰）和「咬向周圍的敵人」的概念不合。可以改成實心圓、限半徑 1，或維持現狀只靠卡片說明（目前的做法）。屬於設計，請玩法 PM 決定。
3. **潮濕系兩個配方**（暗流、水花反濺）：目前改成物理主題。如果玩法上希望它們是冰霜傷害（會凍結站在水上的敵人），要另外決定。
4. **AI 打護盾的平衡**：補師上盾的模擬，我方勝率 58% → 68.5%、平均輪數 6.63 → 6.12。數值沒有調。
5. **低嚴重度、需要設計或美術的巡檢 bug**：
   - 8：浮動字重疊，要排字的錯開規則（美術）；
   - 9：浮動字「閃避」和紀錄「失手」用語不一致，6N-5 已定浮動字寫閃避，紀錄要不要跟著改；
   - 11：技能列文字截斷、冷卻時按鈕變窄；
   - 12：主城廣場與酒館沒有 NPC（內容；實機再確認一次，酒館小地圖有橘點、畫面沒有人）；
   - 13：範圍技畫到地圖外；
   - 14：倒地的敵人也有「可復活」愛心（伺服器 `revivable` 不分陣營；敵方補師可以復活時，這個標示是不是有意義）；
   - 15：齒輪「尚未開放」（AU-1 待決，AU-3 在改聲音，這段沒碰）；
   - 16：鐵砧遮住主角頭、沒有打造面板。
6. **dev 入口的 `ai_until=last` 門檻**：定成 15%。野外地圖有第三方或一擊就結束時，不一定停得到，這時回 422，提示換等級再試。只是開發工具。
7. **6N-8 變體在實戰的可讀性**：見第 5 節的觀察。
