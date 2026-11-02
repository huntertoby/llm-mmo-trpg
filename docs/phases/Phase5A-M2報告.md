# Phase 5A-M2 完成報告：引擎機制②（陣法範圍加成、把傷害分給相鄰同門）

> 實作者：implementer agent（2026-11-03）。規格：`docs/phases/Phase5計畫.md` 第 17 節（先寫入規格、commit `b1604760`，再實作；合併 main 時 5B-4 已占第 16 節，本段規格改為第 17 節、「之後各段規格」改為第 18 節）。
> 動到：`src/trpg/engine/`（新 `formation.py`、`effects/handlers.py`、`events.py`、`ai/utility.py`、`ai/priority.py`、`runner.py`）、`src/trpg/content/`（`battle.py`、`environment.py`）、`src/trpg/narrative/`（`events.py`、`unit_traits.py`）、`content/`（`statuses.yaml`、`ai_profiles.yaml`、`units/sect_array_disciple.yaml`、`world/enemies.yaml` 只改「連心的」一條）、`docs/phases/戰鬥紀錄格式變更.md`、測試。沒有動 `trpg.world`、`trpg.api`；`client/` 只加兩個狀態圖樣（`statusIcon.ts` 的 `sword_formation`、`heart_link`，只用既有筆畫）與測試的狀態數 98 → 100，`damage_redirected` 的浮動數字前端已經會畫。

## 1. 兩個機制

兩個都是 **狀態欄位**（同 5A-M1 的 `on_death_surface`）：只能用在 `polarity: neutral`、`expires: never`、不設 `duration` 的狀態（不被淨化、驅散、奪取，整場都在），由範本 `opening_statuses`／詞綴 `add_opening_statuses` 開場掛上。沒有 `budget_points`（技能不能施加），所以不牽涉技能預算。「同門」＝與持有者同陣營、存活、在場、不是自己、帶 `kin_tag`（省略＝不看標籤）、曼哈頓距離 ≤ `range` 的單位，依單位 ID 排序（`trpg.engine.formation.kin_in_range`）。

### 1.1 陣法範圍加成（`StatusDef.formation`）

- **資料**（`FormationSpec`）：`kin_tag`（可省略）、`range` 1～5（預設 3）、`per_ally_permille` 1～1000、`max_allies` 1～5、`alone_permille` 100～1000（預設 1000）、`applies_to: damage`（目前唯一值）。
- **行為**：倍率 ＝ 有同門時 `1000 + per_ally_permille × min(人數, max_allies)`，沒有時 `alone_permille`；多個陣法狀態依序相乘。乘在持有者造成的攻擊傷害（`cause: attack`，普攻與技能；和虛弱同一處 `damage_dealt`，骰值傷害才算）上，以出手當下的位置計算。預覽的期望傷害自動含陣法倍率。
- **戰鬥紀錄**：`damage_dealt` 新欄位 `formation_permille`（已含在 `status_ppm` 裡），文字加「（陣法 ×1.2）」。
- **規則句與單位卡特性欄**：狀態說明不寫數字（3-41c 守則），數字由欄位產生（`narrative.status_info.formation_rules`，也進術語表 `rules_zh`）。開場狀態有 `formation` 時特性欄標題改成「陣法」：「陣法「劍陣」：與其他劍陣弟子站得越近、人越多，劍勢越盛；落單時威力減弱。…（陣法：3 格內每有一名帶「sword_array」標籤的友方，攻擊傷害 +20%（最多算 2 名）；範圍內沒有時攻擊傷害 ×80%）」。
- **AI**：
  - 自己方：位置價值 ＋ `formation` 權重 ×（站在該格時的倍率 − 1000）÷ 100（`ai_profiles.yaml` 新的表格層級 `formation_ai: {formation: 3}`，填入每個行為模式；沒有陣法狀態的單位不受影響）→ 劍陣弟子傾向待在彼此 3 格內，落單扣分。
  - 對方：`trpg.engine.ai.priority.formation_break`——動作後（預覽最少後果），動作前後都存活的對方陣法持有者倍率總和的下降量 ÷ 1000 × `rewrite.formation_break_points`（10）× 命中率 × `damage` 權重；擊倒、推開、拉走同門都算（擊倒持有者本身照一般擊倒計分）。

### 1.2 把傷害分給相鄰同門（`StatusDef.share_damage`）

- **資料**（`ShareDamageSpec`）：`kin_tag`（可省略）、`range` 1～2（預設 1＝相鄰）、`permille` 1～900。
- **行為**：持有者受到傷害時，護盾吸收與靈魂連結（魂結）**之後** 剩下要扣 HP 的量 × `permille` ÷ 1000（捨去）平分給範圍內的同門，餘數從 ID 小的開始各多 1 點；持有者只扣剩下的。同門直接扣 HP（同魂結：不經護盾、抗性與元素修正；免死照常；HP 歸零倒下）；分到的不會再往外分（不連鎖）。墜落、致命地形與 `lethal` 不分。沒有同門時全部自己承受。
- **戰鬥紀錄**：`damage_dealt` 新欄位 `shared`（實際扣血 ＝ `amount − absorbed − redirected − shared`），文字加「（6 點分給同門）」；每名同門一個既有事件 `damage_redirected`（`status_id` 為分傷狀態），例：「盜賊1 受到 21 點物理傷害［固定值 21］（6 點分給同門），HP 60 → 45」「✦ 盜賊2 分擔了 盜賊1 的 6 點傷害（連心），HP 35 → 29」。
- **規則句與單位卡特性欄**：同上由欄位產生；特性欄標題「分傷」：「分傷「連心」：受到的傷害有一部分分給身旁的同伴承受；…（分傷：受到的傷害（護盾之後）有 30% 平分給相鄰的友方（直接扣血，不經護盾））」（精英另有「精英詞綴」一行）。
- **AI**：`priority.share_discount`——預覽中對方分傷持有者分給同門的傷害（min／max 平均 × 命中率）× `rewrite.share_discount_permille`（500）÷ 1000 × `damage` 權重，從收益扣掉：集火持有者的效益下降；分出去也讓持有者更難被擊倒（預覽本來就反映）。靈魂連結不算。

### 1.3 AI 數值（初值、未經模擬）

`formation_ai.formation` 3；`RewriteAiRules.formation_break_points` 10、`share_discount_permille` 500（schema 預設值，可在 `ai_profiles.yaml` 的 `rewrite:` 覆寫）。只有場上有這兩種狀態時才有分數，其他戰鬥的 AI 分數不變。

## 2. 雲嶺換成正式機制（只改 content）

| 敵人／詞綴 | 原替代品（5A-3） | 正式機制 |
|---|---|---|
| 劍陣弟子 `sect_array_disciple` | 並肩斬（相鄰同伴時加傷，5A3-2） | 開場狀態 `sword_formation`「劍陣」（`kin_tag: sword_array`、3 格、每名 +20%、最多 2 名、落單 ×0.8）；範本加標籤 `sword_array`；技能欄拿掉並肩斬（現在沒有主動技，只靠普攻＋劍陣） |
| 詞綴 連心的 `heart_linked` | 魂結（替同伴分擔，方向相反，5A3-3） | `add_opening_statuses: [{status: heart_link}]`「連心」（不限標籤、相鄰、分出 30%）；拿掉 `add_skills` 魂結 |

並肩斬、魂結兩個技能本身還在技能庫（其他地方用得到），只是雲嶺不再引用。

## 3. 戰鬥紀錄版號

`LOG_FORMAT` `/103` → **`/104`**（`docs/phases/戰鬥紀錄格式變更.md`、`runner.py` 文件字串、8 個測試的字面值）。沒用到新欄位的戰鬥結算與 `/103` 相同。

## 4. 代決（規格 17.9；實作時改的另註）

1. **5AM2-1** 劍陣算誰：18.2.1 寫「與另一名劍陣弟子相隔 ≤ 3 格」→ 新標籤 `sword_array`（只有劍陣弟子），不是全體修士的 `sect`。玩法 PM 說的「同門」若要包含所有修士，改 `statuses.yaml` 一行 `kin_tag: sect`（注意陣眼石靈也帶 `sect`）。
2. **5AM2-2** 劍陣數值：3 格、每名 +20%、最多 2 名（三人一組 → 最高 +40%）、落單 ×0.8。
3. **5AM2-3** 加成對象：只加攻擊傷害（普攻與技能、骰值傷害）；不加命中、環境傷害。
4. **5AM2-4** 陣法以出手當下的位置計算；地圖上不畫範圍（單位卡、戰鬥紀錄有）。
5. **5AM2-5（實作時改）** 連心的對象：規格原寫 `sect` 同門；雲嶺詞綴池含野獸、盜賊（「疤面」是連心的盜賊隊長帶霧狼），用 `sect` 會讓它們的連心無效 → `kin_tag` 省略＝相鄰（1 格）的任何友方；比例 30%，沒有相鄰友方時全吃。規格第 17 節已同步。
6. **5AM2-6** 分傷在護盾、魂結之後；同門直接扣 HP、不連鎖；墜落、致命地形、`lethal` 不分。
7. **5AM2-7** 兩個都是中性、不倒數的狀態，開場掛上；技能不能施加，沒有預算。
8. **5AM2-8** AI 初值：`formation` 3、`formation_break_points` 10、`share_discount_permille` 500。
9. **5AM2-9** 戰鬥紀錄版號 `/104`。
10. **（實作補）** 劍陣弟子拿掉並肩斬後沒有主動技（「落單時弱」由陣法的 ×0.8 表現）；要補一招劍技再定。

## 5. 待 PM 決定

- **劍陣算全體修士還是只算劍陣弟子**（5AM2-1）：設計文字是「另一名劍陣弟子」，玩法 PM 2026-11-02 的說法是「同門」。目前照設計文字。
- **連心的對象**（5AM2-5）：設計寫「相鄰同門」，但詞綴會套到野獸、盜賊身上；目前是相鄰的任何友方（含召喚物）。
- **陣眼石靈**「存在時同門護盾 +」「打碎才解除陣法」：本段沒做（需要「陣法來源物件」的機制），石靈仍是不動的高護甲物件；雲頂觀 Boss 的「劍陣」階段在 5F-2。
- **劍陣弟子的主動技**：拿掉並肩斬後只有普攻。
- 數值（劍陣 +20%／最多 2 名／落單 ×0.8、連心 30%、AI 三個點數）都是初值，要等遭遇強度模擬。

## 6. 檢查紀錄

- 合併 main 前：`tests/engine tests/content tests/narrative tests/world tests/test_architecture.py tests/sim tests/roguelite -n 8`：6825 passed、6 failed → 都是本段預期的變化，已修：3 個重播測試的 `LOG_FORMAT.endswith("/103")`、覆蓋率允許清單加 `sword_formation`、`heart_link`、狀態說明不得寫死數字（改由欄位產生規則句）、技能圖示 fixture 重產（`tests.narrative.icon_fixture`）；`scripts/export_client_fixtures.py` 重產術語表 fixture。
- `tests/cli -m "slow or not slow" -n 8 --timeout=3000`：180 passed（CLI 雜湊沒有變，不需重產）。
- 合併 main（`7e7fbfa8`，5B-4；`Phase5計畫.md` 衝突：5B-4 占第 16 節，本段規格改為第 17 節）後：`tests/api tests/skillgen tests/world tests/content tests/narrative tests/engine/test_mechanics_5am2.py tests/engine/test_mechanics_5am1.py -n 8`：6652 passed、14 skipped、1 failed（`test_budget` 的狀態預算表要列出新狀態，`None`）→ 已修。行為快照 `tests.skillgen.test_refactor_3wr2` 重產後內容不變（只有換行字元，已還原）。
- 前端：`npx vitest run` 125 個檔、1200 passed；`npm run build` 通過（只有既有的 chunk 大小警告）。
- `ruff check .`、`ruff format --check .`（1597 files）、`mypy`（strict，1041 檔）：通過；`lint-imports`：9 個契約全部 KEPT。
- 重播：`trpg battle --map swamp --seed 7 --log-json` ＋ `trpg battle replay`：重播驗證通過（88 個動作、313 個事件）。
- 新測試 `tests/engine/test_mechanics_5am2.py`（19 個）：陣法 0～3 名同門的倍率與上限、超出範圍／敵方／倒下不算、只加攻擊傷害、紀錄文字、schema 限制；分傷的比例與平分餘數、只分相鄰、護盾之後、可擊倒同門、墜落不分、詞綴與特性欄；AI 站位偏好陣型、打散陣型有分、集火分傷持有者扣分；確定性。

## 7. 5A-M2b（玩法 PM 2026-11-03）：陣眼石靈護陣

### 做了什麼

- **護陣（`StatusDef.ward`，`WardSpec`）**：持有者還在場時，`range` 格內帶 `kin_tag` 的友方（不含持有者自己）受到的骰值傷害 × `taken_permille`‰；持有者倒下後 `living_units()` 不再計入，立刻解除。限制同 `formation`／`share_damage`（中性、不倒數）。多個護陣依單位 ID 相乘。`trpg.engine.formation` 新增 `ward_holders`、`ward_permille`。
- **結算**：`damage` 處理器把護陣倍率乘進 `status_ppm`（致命與最大 HP 比例傷害不受影響）；`DamageDealt` 新增 `ward_permille`（已含在 `status_ppm` 裡，供紀錄分開顯示）。
- **內容**：狀態 `array_ward`（`kin_tag: sect`、`range: 3`、`taken_permille: 800`）；`sect_array_stone` 的 `opening_statuses` 掛上。
- **中文**：戰鬥紀錄「（護陣 ×0.8）」；狀態說明加「護陣：…」規則句；單位卡特性欄標題「護陣」。
- **AI**：`RewriteAiRules.ward_kill_points`（預設 12）：擊倒帶護陣的敵人額外加分（`priority.py`，同「先打補師」）。
- **前端**：`array_ward` 狀態圖樣（外框圓＋實心圓，既有筆畫）；`glossary.json` 重產。
- **LOG_FORMAT** `/104` → `/105`（`戰鬥紀錄格式變更.md`、`runner.py`、測試字面值）。
- 測試 `tests/engine/test_mechanics_5am2b.py`（5 個）：範圍內／外、石靈自己不算、石靈倒下即解除、異陣營／非同門不算、schema 與特性句、AI 加分。

### 代決

1. **5AM2b-1** 數值：`sect` 標籤、3 格、×0.8（−20%）；石靈自己不吃護陣（規格寫「同門」，持有者不算）；陣法／護陣只對骰值傷害，與 `damage_taken` 狀態相乘。
2. **5AM2b-2** AI 加分初值 `ward_kill_points` = 12（略高於「先打補師」的 10），未經模擬。
3. **5AM2b-3**（待 PM 決定）**劍陣弟子的主動技沒有補**：`content/skills/` 裡沒有「近戰直線 2 格」的現成技能（直線形狀只有法術與弓箭：風刃、穿透射擊、震地波等；近戰全是 `single`／`cone`／`ring`）。規格說「不做新技能」，所以保守不加。選項：(a) 新增一個 `weapon_req: melee`、`shape: {type: line, size: 2}` 的技能檔（純內容，劍陣弟子 `skills` 加一行）；(b) 維持只有普攻。

### 檢查紀錄（5A-M2b）

- `tests/engine tests/content tests/narrative tests/world tests/api tests/skillgen tests/test_architecture.py tests/sim tests/roguelite -n 8`：10991 passed；5 failed → 4 個是 `LOG_FORMAT` 字面值與 `skill_icons.json` 產生檔（已修）、1 個是既有的 `test_world_growth_api` 偶發（單獨跑 8 passed）。`tests/cli -m "slow or not slow" -n 8`：180 passed（CLI 雜湊沒有變）。
- 前端：`npx vitest run` 126 檔、1211 passed（狀態數 100 → 101，`statusIcon.test.ts` 更新）；`npm run build` 通過。
- `ruff check`、`ruff format --check`、`mypy`、`lint-imports`：通過；重播 `trpg battle --map swamp --seed 7`：88 個動作、313 個事件一致。
