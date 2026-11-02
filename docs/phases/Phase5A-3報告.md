# Phase 5A-3 完成報告：雲嶺敵人內容與遭遇表

> 實作者：implementer agent（2026-11-02）。規格：`docs/phases/Phase5計畫.md` 第 7 節（本段先寫入規格、commit `1809a6ee`，再實作；原第 7 節「之後各段規格」改為第 8 節）。
> 只動 `content/units/`（新增 17 檔，既有範本不改）、`content/world/enemies.yaml`（新）、`content/world/encounters/`（新）、`src/trpg/content/world_enemies.py`（新）、`src/trpg/content/world_encounters.py`（新）、`src/trpg/content/library.py`（載入）、`src/trpg/world/encounters.py`（新）、`src/trpg/world/__init__.py`（說明）、`tests/content/`、`tests/world/`。沒有動引擎、API、前端、roguelite、`content/skills/`、`src/trpg/skillgen/`、地圖檔。

## 1. 交付

| # | 項目 | 檔案 | commit |
|---|---|---|---|
| 1 | 5A-3 詳細規格（計畫第 7 節） | `docs/phases/Phase5計畫.md` | `1809a6ee` |
| 2 | 17 個敵人範本、變體與詞綴、雲嶺遭遇表、schema、載入、content 測試 | `content/units/`、`content/world/`、`src/trpg/content/world_*.py`、`library.py`、`tests/content/` | `dc5aafa4` |
| 3 | 遭遇陣容查詢（純函式）、world 測試、smoke 測試 | `src/trpg/world/encounters.py`、`tests/world/` | `63e28636` |
| 4 | 本報告 | `docs/phases/Phase5A-3報告.md` | `fcf6fd25`＋最後一筆 |

### 1.1 敵人精簡表（`content/units/`；HP＝含體質的最終 HP，初值）

| 18.2 | ID | 武器 | AI | 技能（全是既有技能） | 最終 HP | 備註 |
|---|---|---|---|---|---|---|
| 青霧道童 | `sect_acolyte` | 圖騰杖 | support | 聖光撫慰（清心） | 22 | |
| 持劍弟子 | `sect_swordsman` | 單手劍 | brute | 先發制人（劍勢連斬）、挺身而出 | 36 | 同門相護替代（代決 5A3-1） |
| 符籙師 | `sect_talisman_caster` | 圖騰杖 | archer | 寒鎖（定身符）、靜電掌（雷符） | 24 | `ranged` 標籤 |
| 煉丹師 | `sect_alchemist` | 圖騰杖 | support | 聖域（群體治療）、毒霧彈（丹爆） | 32 | |
| 護法武僧 | `sect_warrior_monk` | 拳套 | guard | 格擋反擊（金剛身）、壁壘挑釁、挺身而出 | 58 | `steadfast` |
| 劍陣弟子 | `sect_array_disciple` | 單手劍 | flanker | 並肩斬（相鄰同伴加傷） | 26 | |
| 霧行者 | `sect_mist_walker` | 匕首 | assassin | 瞬步背刺（霧襲）、滑步脫身 | 24 | |
| 雲鶴使 | `sect_crane_archer` | 弓 | archer | 高處狙擊、鷹眼標記（鶴唳） | 26 | 遠程 |
| 傀儡師 | `sect_puppeteer` | 圖騰杖 | cunning | 喚出爆裂傀儡 | 24 | |
| 陣眼石靈 | `sect_array_stone` | 拳套 | idle | — | 48 | 速度 0、`immovable`、無反應 |
| 青霧執事（精英） | `sect_steward` | 圖騰杖 | support | 聖域、回春、調息 | 62 | `elite` |
| 霧狼 | `mist_wolf` | 利齒 | flanker | 雙牙 | 22 | |
| 山豹 | `mountain_leopard` | 利爪 | assassin | 猛虎衝撞（撲擊） | 26 | |
| 石背熊 | `stoneback_bear` | 利爪 | brute | 震地推倒 | 62 | `steadfast` |
| 雷羽鷹 | `thunder_hawk` | 利爪 | flanker | 俯衝斬、靜電掌 | 14 | `flying` |
| 霧魅 | `mist_wraith` | 影刃 | assassin | 閃現、威懾凝視（迷惑→恐懼） | 22 | |
| 碎晶傀儡 | `shard_golem` | 石拳 | brute | 碎岩擊 | 48 | 雷抗 50% |

標籤：修士 `[humanoid, sect]`、野獸 `[beast]`、源晶造物 `[construct]`。盜賊沿用既有範本。新範本都沒有 `doll`（外觀是 5A-ART）。

**變體**（`content/world/enemies.yaml`）：雷符師 `thunder_talisman_caster`（雷電法杖；寒鎖 → 火花連鎖）、冰鶴使 `frost_crane_archer`（鷹眼標記 → 批註寒霜，命中緩速）、水煉丹師 `water_alchemist`（毒霧彈 → 潑水瓶）。
**精英詞綴**（HP ×1.5、加 `elite` 標籤）：再生的（＋調息，每回合結束回血）、霧隱的（＋滑步脫身與受擊反應）、連心的（＋魂結）、狂暴的（＋狂戰士之怒，限近戰）。套用後 ID＝`<範本>_<詞綴>`、名字＝「狂暴的霧狼」。

### 1.2 遭遇表摘要（`content/world/encounters/cloud_ridge.yaml`）

- 16 個會遇敵的地點（城鎮、傳送點以外）全部有表；27 種陣容，每種 2～4 名；權重一律 1。
- `ranged_cap: 2`（18.2.1）、`camp_elite_permille: 100`（初值）、本區詞綴 4 種。
- 精英巢穴北坡獵場：固定「狂暴的霧狼」（懸賞北坡狼王）＋霧狼 ×3。丹爐洞有青霧執事陣容；斷崖幫寨有盜賊隊長陣容（已有精英，不再混）。
- 各地點陣容照計畫 7.4（依 18.3「內容」欄：竹林霧狼、雨中梯田盜賊＋修士、冬湖冰鶴使與石背熊、源晶裂痕霧魅與碎晶傀儡、鶴歸崖雷羽鷹巢…）。
- 載入檢查：遠程 ≤ 2（含固定精英）、精英 ≤ 1、固定精英只在精英巢穴且詞綴可套用、營地陣容一定有人可以混精英、每個單位套上每個可套用的本區詞綴後仍通過單位檢查（技能欄、反應規則）。

### 1.3 遭遇查詢（`trpg.world.encounters`）

- `roll_lineup(library, EncounterResult) → EncounterLineup`：亂數 `fnv1a64("{battle_seed}:lineup")`；依權重抽陣容 → 精英巢穴放固定精英 → 一般營地（陣容沒有精英時）擲 100‰ 把 1 名可套用的成員升級成精英（不加人數、不加等級）。
- `lineup_templates(library, lineup)`：解析變體與詞綴，回傳可直接放進 `UnitSpawn` 的範本。5A-4 開戰時用它；`ContentLibrary.enemy_catalog()` 提供名字解析、遠程判定與詞綴可否套用。

## 2. smoke 結果

`tests/world/test_enemy_smoke.py`：雲嶺 16 個地點的 27 種陣容（含 3 種變體、北坡狼王）＋ 4 種詞綴各一場，用該地點的戰鬥地圖（沒有地圖的村落、祭壇、遺跡、Boss 地點用 `dark_forest`）、`hero_fighter`／`hero_archer`／`hero_stormcaller`、效用 AI、`max_rounds` 8：**全部打到結束、沒有錯誤**；17 個新範本與 3 個變體都至少出場一次。陣容戰共約 16 秒。

手動跑同一批戰鬥時統計到敵方實際施放了：聖光撫慰、先發制人、寒鎖、靜電掌、聖域、格擋反擊、壁壘挑釁、並肩斬、瞬步背刺、高處狙擊、鷹眼標記、喚出爆裂傀儡、回春、雙牙、狂戰士之怒、猛虎衝撞、俯衝斬、火花連鎖、批註寒霜（技能都接得上 AI）。主角方大多在 3～8 輪內獲勝——數值是初值、主角範本是原型強度，本段不做平衡。

## 3. 用了 18 號文件的哪些內容

- 18.2.1：修士 10 種＋精英青霧執事（名稱、定位、武器、核心招式概念）、本區詞綴 4 種、元素變體 3 種、遠程上限 2、陣容例 3 組（道童 ×2＋持劍弟子＋煉丹師；劍陣弟子 ×3＋陣眼石靈；武僧＋符籙師＋霧行者）。
- 18.2.2：野獸 4 種、源晶失控造物 2 種、盜賊沿用、混族例「盜賊帶著霧狼」。
- 18.3「內容」欄：各地點出現的敵人。18.7.4：懸賞「北坡狼王」＝霧狼精英（狂暴的）。
- 沒用：18.2.3 Boss 霧鎖真人（5F-2）、18.2.4 材料（5D-2）、外觀提示（5A-ART）。

## 4. 代決清單（照最保守做法；計畫 7.6）

1. **5A3-1 同門相護**：引擎沒有「替被攻擊的友方加護盾」的反應目標 → 持劍弟子、護法武僧帶既有反應技「挺身而出」（相鄰同門受擊時替他擋下＋自身護衛）。
2. **5A3-2 沒有對應機制的招牌**：陣眼石靈只是不動的高護甲物件（沒有「同門護盾 +」與「打碎才解陣」）；劍陣用「並肩斬」（相鄰同伴）代替「≤ 3 格」；青霧執事沒有「九轉回天」蓄力強招（用聖域＋回春＋調息）；碎晶傀儡沒有「死後帶電碎片」；霧魅的迷惑用「恐懼」代替；雷羽鷹的「帶電俯衝」＝俯衝斬＋靜電掌兩招。
3. **5A3-3 詞綴**：霧隱的＝受擊時隱蔽（不是開場隱蔽 1 回合）；連心的＝魂結（方向與設計相反：替同伴分擔，不是把自己的傷分給同門）。
4. **5A3-4** 混族敵人都在同一陣營；三方混戰（9.6.6 D）沒做。
5. **5A3-5** 敵人不隨地點等級縮放（7.8 不縮放），靠陣容挑選分強弱；營地混精英＝原成員套詞綴（HP ×1.5），不加人數。
6. **5A3-6** 陣容亂數由 `battle_seed` 衍生，不動角色亂數計數。
7. **5A3-7** 遠程＝武器大類 `ranged` 或 `ranged` 標籤（符籙師用法器、標了 `ranged`）。
8. **5A3-8** 只有 `camp` 會混精英；精英巢穴固定；村落、遺跡、異象、秘境、祭壇、Boss 地點都不混。
9. **5A3-9** 一個陣容最多 4 名（地圖敵方起始區 4 格）。
10. **（實作補）** 持劍弟子的「劍勢連斬」原本想用「交叉斬」，但它限定雙匕首，改用同樣兩段傷害的「先發制人」。
11. **（實作補）** 套用詞綴的條件：已是精英、物件型（速度 0 或 `immovable`）、武器大類不符、技能已裝備、超過技能欄位上限時不能套。所以持劍弟子、武僧（反應欄已滿）不會抽到「霧隱的」，霧行者已有滑步脫身也不會。
12. **（實作補）** 陣容與詞綴的數值（各範本屬性、HP、護甲；`hp_permille` 1500；`camp_elite_permille` 100）都是初值，寫在 content。
13. **（實作補）** `tests/content/test_con_hp.py` 的最終 HP 表加上 17 個新範本（它要求每個範本都列出）。

## 5. 待 PM 決定

- **引擎機制要不要排段**：同門相護（護盾給被攻擊的同門）、陣眼石靈的陣法（存在時同門護盾 +）、蓄力強招預告（青霧執事「九轉回天」；Boss 的「霧鎖千山」在 5F-2 也會需要）、死亡時留下表面（碎晶傀儡；灰燼荒原熔岩獸群「死後留火地」也需要）、開場隱蔽（霧隱的）、受傷分給同伴（連心的）、迷惑狀態、三方混戰。目前都是替代品，改成正式機制時只要改 content。
- 18.2.1 的「符籙師」本身帶雷符，又有變體「雷符師」——兩者差別目前只在定身符換成火花連鎖與武器；玩法 PM 若要不同定位可以只改 `enemies.yaml`。
- 煉丹師的「回春丹（十字範圍）」用了聖域（2 格內友方），範圍不是十字。
- 主角方在 smoke 裡大多輕鬆獲勝：遭遇強度要等 5A-4 接上大世界角色後用模擬定（9.6.10「數值類」）。

## 6. 檢查紀錄

- `uv run pytest -q tests/content tests/world tests/test_architecture.py tests/sim/test_difficulty.py tests/llm/test_simplified.py tests/api -n 8 --timeout=1800`：2242 passed、1 failed——`tests/api/test_run_start_api.py::test_dev_packs_endpoint_and_start`（開局包回應出現流派名），是 BAL-19f 另一個 agent 在修的既有失敗，和本段無關。
- 合併 main（`d828e0c4`）後重跑 `tests/world`、`tests/content/test_world_enemies.py`、`test_world_encounters.py`、`test_con_hp.py`、`tests/test_architecture.py`：173 passed。
- `tests/cli -m "slow or not slow" -n 8 --timeout=3000`：180 passed（CLI 快照沒有變，不需重產）。
- `ruff check .`：通過；`ruff format --check .`：1523 files already formatted；`mypy`（strict，979 檔）：Success；`lint-imports`：9 個契約全部 KEPT。
- `uv run trpg content check`：通過，列出 `world/enemies.yaml`（3 種元素變體、4 種精英詞綴）與 `world/encounters/cloud_ridge.yaml`（16 個地點、27 種陣容、遠程上限 2、營地精英 100‰）。
- 重播：`uv run trpg battle --map swamp --seed 7 --log-json …` ＋ `trpg battle replay`：重播驗證通過（88 個動作、313 個事件）。
