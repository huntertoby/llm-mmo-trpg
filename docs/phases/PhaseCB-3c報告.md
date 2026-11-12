# Phase CB-3c 報告｜戰鬥動畫小修：正南／正北特效落點、第二種近戰改看技能射程

> 實作者（Opus 5.5）2026-11-12。規格：`docs/phases/PhaseCB-3c計畫.md`。worktree 從 `131e5628`（含 `f0f90336` 規格）分出；沒有 push。

## 做了什麼

| 交付 | 內容 | commit |
|---|---|---|
| 2（B） | `creatureActionOf` 加技能射程與施放者近戰武器射程（`isMeleeSkill`）；`/api/glossary` 加唯讀的 `weapon_ranges`、`gen:api`、重產 `glossary.json` 測試快照；`cb3cMeleeRange.test.ts` | `f69e9620` |
| 1（A） | 同一欄時片段特效不畫進身體貼圖，另畫一張轉向的特效貼圖放在目標格（`creatureFxTurn.ts`、`inkCreature.renderCreatureFxCanvas`、`ArtTextures.creatureFx`、`skillLayer.placeTurnedFx`）；`cb3cFxTurn.test.ts` | `b5e5abb6`、`d75639aa` |
| 5 | 開發頁案例 `m2matriarchEdgeWN`、`m2boarSW`、`lordErosion`；`&rows=1` 的標題多列出異形動作；截圖 8 張 | `51ea1454`、`797c9e84` |
| 4（C） | 只讀腳本（沒有 commit，指令見下），結果表在本報告 | — |
| 6 | 本報告、`docs/dev/上手-前端戰鬥畫面與動畫.md` 更新 | （本報告的 commit） |

## 驗收逐條

1. **交付 3 的測試全過、指定的測試檔全過**：
   `corepack pnpm -C client exec vitest run src/render/cb3cFxTurn.test.ts src/battle/cb3cMeleeRange.test.ts src/render/creaturePose.test.ts src/battle/creatureAction.test.ts src/battle/cb3Melee2.test.ts src/render/qCreatureAnim.test.ts` → `Test Files 6 passed (6)`、`Tests 114 passed (114)`（加上頭目那條斷言後 `cb3cFxTurn` 42 項全過）。
   - A：`cb3cFxTurn.test.ts`「CB-3c 特效錨點：8 方向 × 一般／精英＋大型」32 項（8 方向 × 2 種大小 × 原本朝東／朝西）：正南、正北的錨點＝目標格中心；東西向與斜向的錨點和修改前相同（期望值＝修改前的 `creatureOffsetPx(…, {dx: 52})`，另寫死 50.88／73.14 px）。「實際片段」4 項：硫煙獸挑獠牙、熔爐母獸（精英＋大型）甩尾在正南／正北時，每一格的星爆落在目標格、白弧圓心在施放者與目標之間。
   - B：`cb3cMeleeRange.test.ts` 12 項：射程 1 相鄰＝`melee2`、跟武器（fangs）＝`melee2`、射程 2＝長槍射程 2（相鄰、隔一格）＝`melee2`、射程 2 對 fangs＝`cast`、射程 3 法術（`skill_quake_topple`）貼身＝`cast`、晶蝕貼身與隔距離＝`cast`、整條時間軸上碎晶之主貼身放晶蝕與火花連鎖＝`cast`、石背熊震地掀翻貼身＝`cast`、單體近戰技能（碎骨、毒牙挑、餘燼啃咬）＝`melee2`、普攻一律 `melee`。射程全部從 `content/skills/*.yaml`、武器射程從名詞對照表（`weapons.yaml`）讀，不手寫數字。測試在舊判定下會失敗（暫時換回舊判定跑過：5 項失敗，已還原）。
   - 快照：`creaturePose.test.ts`、`inkDollSnapshot.test.ts` 的雜湊**沒有變**（沒有轉向時姿勢鍵與畫法都不變，見「快照變動說明」）。
2. **`corepack pnpm -C client build`**：見「交件前的整包檢查」。
3. **動到 API**：`uv run ruff check .` → `All checks passed!`；`uv run ruff format --check .` → `2328 files already formatted`；`uv run mypy` → `Success: no issues found in 1439 source files`；`uv run pytest -q tests/api/test_glossary_names.py tests/api/test_openapi_snapshot.py tests/api/test_client_fixtures.py` → `13 passed`；`export_openapi.py`、`gen:api`、`export_client_fixtures.py` 都重跑並一起 commit（`client/openapi.json`、`src/api/schema.d.ts`、`battle/fixtures/glossary.json`）。
4. **截圖齊全、邊欄兩張的特效完整在畫布內**：見「截圖清單」。`2-…right-column-south.jpg` 帶右緣留邊、`3-…left-column-north.jpg` 站最左欄朝西；兩張的星爆、白弧都在目標身上、在畫布內（身體本身貼邊時仍會被裁一點，那是身體不是特效，D3 照舊）。
5. **C 的結果表**：見下。
6. **引擎與 `content/` 沒變**：`git diff --stat 131e5628 -- src/trpg/engine content` 輸出為空。

## A 的實際成因（讀程式確認）

上手筆記的推論是對的，再補兩點細節：

- 片段特效（`QPartPose.fx`）是 `qCreaturePartPose` 給的異形自己的側面座標（朝東、腳底為原點，相鄰目標在 x＝52，`qCreatureAnim` 的 `TGT`），在 `inkCreature.drawCreature` 最後跟身體**一起畫進身體貼圖**；貼圖在 `renderCreatureCanvas` 照 `creatureSide` 鏡射。出招時 `creatureFacingTo` 對同一欄的目標維持原朝向，所以特效一律往東或往西畫，落在側邊的空格；朝外站在邊欄時就畫到地圖外。
- 身體貼圖是 176×136 虛擬單位、腳底下只留 24，**放不下往南一格的特效**，所以不能只在貼圖裡改座標；這也是為什麼留邊加大也救不回來。

修法：只在同一欄時，姿勢帶 `fxTurn`（1＝正南、-1＝正北）。身體貼圖不畫特效（鍵多 `fxturn±1`）；另畫一張特效貼圖（`CREATURE_FX_BOX` 176×300，原點在「相鄰目標」那一點），放在這一列的效果節點（效果圖層，蓋在目標之上、這一列結束就移除）。座標轉法：(x, y) → (0, y ＋ 轉向 ×（x − 52）× c)，`c = 52 /（52 × 大小 × 紙娃娃縮放）`，讓「相鄰目標」那一點剛好落在相鄰那一格中心、異形自己（x＝0）的塵土留在原地、高度（y）不變；相鄰那一格高低不同時跟著那一格抬高。

**取「目標格」還是「連線上」**：錨點取目標格中心，其餘特效照原樣張的比例沿施放者→目標的連線排（等於把側面的畫法轉 90°）。理由：原樣張的「相鄰目標」就是 x＝52 那一點，照比例轉最接近原樣張的意圖；星爆在獠牙尖、白弧圓心在頭或尾根，這些相對位置都保留。硫煙獸挑獠牙的星爆圓心在獠牙尖，轉過去離目標格中心 24.7 px（剛好在兩格交界，星爆的圓碰得到目標格）——東西向時同一顆星爆也在兩格交界，照原比例沒有硬推進格子裡。

## B 的射程取得方式

- **技能射程**：技能卡（API 既有）的 `icon.segments[i].range`；第一段跟武器時 `range` 為 null、`stats.range_weapon` 為真 → `"weapon"`。卡上沒有射程（自身、光環、第二段跟武器）→ 不知道，照 CB-3 的舊判定。
- **施放者近戰武器射程**：前端原本拿不到，所以在 `/api/glossary` 加唯讀欄位 `weapon_ranges`（全部武器的 `id`、`weapon_class`、`range`，來自 `weapons.yaml`），`battle/glossary.ts` 的 `meleeWeaponRange(unit.weapon_id)`：近戰武器回射程、不是近戰武器回 `null`、表上沒有回 `undefined`（不知道）。單位的 `weapon_id` 從這一步開始前的畫面讀。規格寫「可在 API 的戰鬥技能資料加一個唯讀欄位」——武器射程是單位的屬性、不是技能的，`UnitView` 又在引擎（不能改），所以放在名詞對照表；只供挑片段，不做規則判斷。
- 判定（`isMeleeSkill`）：射程 1 → 近戰；`"weapon"` → 施放者拿近戰武器才算；數字 → 等於近戰武器射程才算；射程不知道 → `null`。`creatureActionOf`：近戰技能＋`single` → `melee2`（不看當下距離）；不是近戰技能而現行會播 `melee`（貼身）→ `cast`；`null` → 舊判定。普攻、衝鋒、吐息、召喚、位移、範圍照舊。

## 快照變動說明

沒有變動。`creaturePose.test.ts`、`inkDollSnapshot.test.ts` 照舊通過：`fxTurn` 只在同一欄時才出現在姿勢鍵裡，沒有轉向時鍵（`creaturePoseKey`）與畫法和修改前一模一樣（`cb3cFxTurn.test.ts`「姿勢的快取鍵帶轉向；沒有轉向時鍵不變」）。

東西向的畫面另用截圖逐像素比對（修改前＝把 A 的 5 個檔暫時換回 `f69e9620` 拍、拍完還原）：精英＋大型朝東 `5-matriarch-elite-east-*` 差異大於 24 階的像素 247 個、硫煙獸朝西 282 個，全部集中在**目標（人形）受擊那一格的手臂**（連拍取樣時間的差），異形的身體與特效沒有差；正南那組（`1-` 對 `1b-`）差 4355 個，就是特效搬位置。

## C 的結果表（同一隻同一回合同一招放兩次）

指令（只讀、沒有 commit）：`UV_NO_SYNC=1 uv run python <scratchpad>/c_twice.py`。判定照引擎：放完把冷卻設成 `cost.cooldown`（`engine/skills/targeting.py` 的付代價），冷卻 > 0 時同回合不能再放；所以冷卻為 0／沒有冷卻、且 2 × AP ≤ 每回合 AP（`core.ap_per_turn`＝3；含保留 `ap_carry_max`＝1 時 4）才放得了兩次。單位的招含頭目階段換上的招（`phases[].skills`）。沒算法力、耐力夠不夠、AI 會不會這樣選。

每回合 AP 3（含保留 4）；符合 13 筆：

| 單位 | 外觀 | 招 | AP | 冷卻 | 同回合兩次 | 每場上限 | 法力 | 耐力 |
|---|---|---|---|---|---|---|---|---|
| ashen_heart | 異形（頭目） | skill_fire_bolt | 1 | — | 可 | — | 5 | 0 |
| bandit_archer | 人形 | skill_fire_arrow | 1 | — | 可 | — | 0 | 6 |
| bandit_archer_guard | 人形 | skill_fire_arrow | 1 | — | 可 | — | 0 | 6 |
| bandit_archer_rookie | 人形 | skill_fire_arrow | 1 | — | 可 | — | 0 | 6 |
| fire_dust_bat | 異形 | skill_fire_bolt | 1 | — | 可 | — | 5 | 0 |
| hero_mage | 人形 | skill_fire_bolt | 1 | — | 可 | — | 5 | 0 |
| hero_stormcaller | 人形 | skill_chain_lightning | 2 | — | 只有含保留時可 | — | 10 | 0 |
| hero_stormcaller | 人形 | skill_summon_tide | 1 | — | 可 | — | 6 | 0 |
| hero_stormcaller | 人形 | skill_stone_wall | 1 | — | 可 | — | 5 | 0 |
| lava_tortoise | 異形 | skill_fire_bolt | 1 | — | 可 | — | 5 | 0 |
| sect_acolyte | 人形 | skill_radiant_mend | 1 | — | 可 | — | 5 | 0 |
| sect_talisman_caster | 人形 | skill_hush | 1 | — | 可 | — | 3 | 0 |
| thunder_hawk | 異形 | skill_static_palm | 1 | — | 可 | — | 3 | 0 |

結論：
- **有**：異形 4 隻（灰燼之心、火塵蝠、噴岩龜的火焰箭；雷鷹的靜電掌），都是遠程施法片段；人形 6 種。
- **第二種近戰的 5 款身形（犬狼、山豹、熊、野豬、蜥蜴）的單體近戰技能全部有冷卻**，原樣內容不會同回合放兩次；CB-3b 看到的「格號交錯」只在暫存內容把餘燼啃咬改成 AP 1、無冷卻時出現。
- 這些單位的法力、耐力池沒查是否夠放兩次（預設由屬性推，表上的法力 3～10）。

## 截圖清單（`docs/art/shots/cb3c/`，8 張、jpg 80、最大 221 KB）

開發頁 `skill-gallery.html#cb2b`（正式流程 `playbackPlan → frameOps`），自己啟動的無頭 Chrome（`--headless=new --mute-audio`，CDP 8121），網址帶 `?mute=1`，連拍每格一張（出招片段的每一格），`cell=88`。

| 檔案 | 內容 |
|---|---|
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb3c\1-boar-west-south.jpg` | 硫煙獸朝西、目標在正南（`case=m2boarSW`）：417 ms 的星爆與白弧在獠牙前、目標頭上（對照 `cb3b/3-real-boar-uptusk.jpg`） |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb3c\1b-boar-west-south-before.jpg` | 同一招修改前：星爆、白弧、塵土在硫煙獸西側的空格 |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb3c\2-matriarch-elite-right-column-south.jpg` | 熔爐母獸（精英＋大型）站最右欄、目標正南、右緣留邊（`m2matriarchEdgeS&margin=1`）：417 白弧、500 星爆在目標身上，在畫布內 |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb3c\3-matriarch-elite-left-column-north.jpg` | 同一隻站最左欄、朝西、目標正北（`m2matriarchEdgeWN&margin=1`）：417 白弧、500 星爆在目標身上，在畫布內 |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb3c\4-shard-lord-erosion-adjacent.jpg` | 碎晶之主貼身放晶蝕的連拍（`lordErosion&rows=1`）：標題列「出招：異形動作 cast」，手晶發光的施法片段，不是近戰揮擊 |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb3c\5-matriarch-elite-east-after.jpg` | 東西向對照（修改後）：精英＋大型朝東 |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb3c\5-matriarch-elite-east-before.jpg` | 同上，修改前（逐像素比對：異形部分沒有差，見「快照變動說明」） |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb3c\5-boar-west-after.jpg` | 東西向對照（修改後）：硫煙獸朝西（修改前的同一張只在 scratchpad 比對，沒有交） |

## 實機未看

- 全部是開發頁（正式的播放流程與繪製器、假的事件），沒有在實戰中讓異形打正南／正北，也沒有在實戰看碎晶之主貼身放晶蝕。
- 減少動態下的轉向特效沒拍（程式路徑相同：出招列跳最後一格，最後一格通常沒有特效）。
- 高低不同的相鄰格（目標格比施放者高或低）只在程式裡處理（跟著那一格抬高），沒有截圖。
- 本段沒有改浮動卡與 HUD，沒有做 6.5.1 的浮動卡實測。

## 交件前的整包檢查

在 `797c9e84`（A、B、截圖都 commit 之後）各跑一次，結束碼分開記：

- `corepack pnpm -C client test` → `Test Files 286 passed (286)`、`Tests 3514 passed (3514)`，結束碼 0。之後只多了 `d75639aa`（`cb3cFxTurn.test.ts` 多一條頭目斷言，單檔重跑 42 passed）。
- `corepack pnpm -C client build`（`tsc --noEmit && vite build`）→ 結束碼 0（只有既有的 chunk 大小提示）。
- `corepack pnpm -C client typecheck`（`d75639aa` 之後）→ 結束碼 0。
- 沒有跑 `scripts/check.py`、沒有跑模擬。沒有新增任何 `# noqa`（Python 只動 `api/glossary.py`、`api/schemas.py` 與一個測試）。
- 自己啟動的程序：vite（5250，PID 9828）、無頭 Chrome（CDP 8121，每次由腳本以子程序 PID 結束）；交件前都已關閉並確認沒有殘留。

## 待 PM 決定

1. **頭目沒有涵蓋**：灰燼之心、碎晶之主（頭目畫法 `drawBossFrame`）打正南／正北時，片段特效照舊畫進貼圖（往東或往西）。頭目一格以上、出招片段與錨點不同，照規格的範圍只做一般異形；要不要另排。
2. **斜向的目標沒改**：目標在東南、西北等斜向時，特效照舊落在施放者那一排、目標那一欄（離目標格中心一格高）。規格寫「東西向（目標偏東／偏西）的既有落點不得改變」，而交付 3 又要求 8 方向都在目標格內，兩者對斜向衝突；照「改動限於同一欄」保守處理，測試對斜向斷言「和修改前相同」。
3. **精英＋大型東西向的錨點在 73.1 px**，比目標格邊（72）多約 1 px（既有，特效隨大小放大）。同上，照「東西向不得改變」沒動。
4. **武器射程放在 `/api/glossary` 的 `weapon_ranges`**，不是「戰鬥技能資料」：武器射程是單位的屬性，`UnitView` 在引擎不能改。需要的話可改成技能卡的欄位，但要知道施放者是誰。
5. **跟武器（`"weapon"`）的招、施放者拿遠程武器或法器時算「不是近戰」**：貼身放播施法片段。原樣內容的異形都拿近戰武器（fangs、talons…），目前不影響畫面。
6. **射程不知道（卡上沒有）時照 CB-3 的舊判定**（`single`＋相鄰 → `melee2`），例如第二段跟武器的複合技能。
7. **轉向後白弧的形狀不轉**：只搬位置（橫向收到中線），弧仍是側面畫法的方向；星爆是圓的不受影響。美術要不要另畫正面／背面的弧，請美術 PM 看 `1-`、`2-`、`3-` 判斷。
8. **硫煙獸挑獠牙的星爆在兩格交界**（離目標格中心 24.7 px，照原樣張比例；東西向時一樣）。要硬推進目標格就得改片段本身的座標。
9. **C 的結論**：原樣內容中第二種近戰的招都有冷卻，不會同回合連放；會連放的只有遠程施法（異形 4 隻、人形 6 種）。「同一單位連續出手的銜接」要不要排、排哪幾隻，請 PM 決定。
