# Phase BAL-21c 完成報告｜碎晶之主 P3 界隙閃擊＋trapper 掉場調查＋`blink` 片段

> 規格：`docs/phases/PhaseBAL-21計畫.md` 第 0.0 節（優先；第 14 行 21c、第 23 行美術 T7 答覆）、第 6 節、第 9 節、第 10 節 T5～T7。基準：本機 main `9b90f7f7`（含 `a057ca27`）。
> 使用者決定（2026-11-12）：數值由使用者在數值工坊調；PM 與 agent 只出報表與建議，**不做頭目數值試調**。

## 1. 做了什麼

**內容（`cca19d52`）**

- 新增 `content/skills/skill_rift_flicker.yaml`「界隙閃擊」（`enemy_only`）：第一段單體、射程 6、物理傷害；`followup` `when: after_action`、骨架 `displace`、`ground_tile` 射程 4、`teleport`（先打再閃走）。1 AP、法力 3、**冷卻 3**（#149）。照 CB-2g 草稿，**只改了傷害骰 1d8 → 1d4**：草稿預算 126.2%，`trpg content check` 擋下（上限 100%）；1d4 是 95.2%（見第 6 節待決 1——頭目實戰升到 `_t3`，傷害骰改不改**實戰完全相同**）。
- `content/units/rift_shard_lord.yaml` 第 3 階段 `core_overload` 的 `skill_blink` → `skill_rift_flicker`。**第 4 階段 `rift_collapse` 沒有自己的 `skills`，沿用第 3 階段**，所以 P4 也一併換成界隙閃擊（規格第 0 節沒有另定 P4；資料結構上「只換 P3」做不到，除非給 P4 另寫一組 `skills` 保留 `skill_blink`，那會是新增內容，列待決 2）。
- 四個登記處：技能圖示快照 `client/src/render/fixtures/skill_icons.json`（只多 `skills.skill_rift_flicker` 一筆；`random`、`workshop` 與其他 403 招逐筆相同）、`tests/skillgen/test_enemy_only.py` 名單、`tests/content/test_skill_scaling.py` 招數 403 → 404、CLI 快照 `skills_list`／`skills_show_all`（第 3 節）。另外寫死招數的 `tests/narrative/test_skill_icon_art_qi2a.py`（404）、前端 `render/qIcon/qIconSkills.test.ts`（404）、`qIconQi2d.test.ts` 的 `ADDED_AFTER_BASELINE` 加新招（只比有基準的 402 招，斷言不放寬）。`scripts/export_client_fixtures.py` 不必重跑（沒動單位外觀與技能卡以外的快照；`skillCards.json` 是玩家示範卡，不含敵人專用招）。
- 測試：新檔 `tests/engine/test_rift_flicker_bal21c.py`（3 項，實際跑引擎：P3 換招且 P4 沿用、數值照 #149、施放＝先命中再暫停選落點 → `skill_followup` → 頭目 `teleport` 到 AI 選的格）；`tests/world/test_enemy_ai_moves_149.py` 的 `BOSS_PHASE` 加 `("rift_shard_lord", "core_overload", "skill_rift_flicker")`（效用 AI 實際放得出來）；`tests/content/test_enemy_skill_count_149.py` 原本「`skill_blink` 本段不動」改成斷言換成界隙閃擊。

**前端（`0c44c43f`、開發頁與截圖 `6615847b`）**

- `render/qBoss.ts`：碎晶之主加片段 `blink`（`BOSS_CLIPS.sl`、`BOSS_MS.blink = 600`、`BOSS_CLIP_ZH`）；`bossPlan` 的 `blink`＝`LordState.blink = 1 − u`（線性，沒有前推、沒有自帶特效），殘影用現有 `drawShardLord` 身後兩層（16 px、0.35／0.55），跟著貼圖東西向鏡像、南北向照預設；`bossAttackClip("sl", "blink")` ＝ `blink`，**`swing` 不再當位移的退回片段**（普攻、遠程不變）。灰燼之心不動。
- **在目的格播**：`viewGrip.creatureStrikeInView` 對頭目的 `blink` 回 `{ blink: true, blinkAt: "to" }`，走 CB-2b「閃現由傳送的位移動畫播」；`motionLayer.creatureBlinkMove` 看到 `creatureBlinkAt: "to"` 從第一格就站在終點，600 ms 內殘影由濃到淡（異形照舊前半原地淡出、後半新格淡入）。
- **順序修正**：界隙閃擊的 `teleport` 在第二段，`placeMotions` 原本只看第一段卡上的原語，找不到就把傳送排在出招**前**——頭目會先閃走、再從新位置放雷。現在「位移只在後段、而那一段是閃現」時排到出招後（`after`），第一段的特效從傳送前的格子發出（`castFromBefore`）。條件限定在閃現段，人形的「動作 → 位移」複合技照舊沒改（第 6 節待決 5）。
- 改到的兩個既有基準測試（都只因新片段 `blink` 多出鍵，原有鍵的斷言不放寬）：`render/cb4FxAnchor.test.ts` 命中對齊表多 `boss:sl|blink|1～3 = 0.5`（沒有出手特效、沒有前推，同 `wraith|blink`）；東西向畫面雜湊表沒有 `sl|blink|*` 基準，另列並斷言剛好是那 4 個鍵。`render/qBoss4b.test.ts`「出手格有出手特效」排除 `blink`（位移片段，同 `hit`、`death`）。
- 新測試 `battle/bal21cRiftFlicker.test.ts`（5 項，走正式 `playbackPlan`；事件順序照引擎實際輸出）：位移挑 `blink` 不挑 `swing`、600 ms 線性 1 → 0、傳送排在出招後且整段在目的格、第一段特效從原格發出、第 4 階段同樣。
- 開發頁 `client/dev/skill-gallery.html#bal21c`（`&blinkFreeze=<毫秒>` 停在傳送開始後那麼久、`&rows=1`）。

## 2. 驗收

| 條件 | 結果 |
|---|---|
| 新招內容、預算 70～100% | 95.2%；`trpg content check`：662 個檔、404 個技能通過 |
| P3 換招（P4 沿用） | `test_the_overload_phase_swaps_blink_for_flicker_and_collapse_inherits_it` |
| AI 接線 | `test_enemy_ai_moves_149.py`（空地圖）；800 場量測 P3 37%、P4 29%（第 5 節）；trapper 30 場追蹤中 25 次施放 25 次都真的傳送 |
| `blink` 片段（約 600 ms、1 → 0 線性、目的格、殘影鏡像）；`swing` 不當退回 | `bal21cRiftFlicker.test.ts`；截圖第 4 節 |
| 一場 `trpg battle --log-json` ＋ `replay` | `rift_gate` 種子 7：「重播驗證通過：116 個動作、488 個事件，最終狀態一致」，兩個結束碼 0 |

## 3. 雜湊與快照（逐項證明來自本段）

改前＝`git archive HEAD content`（`9b90f7f7`）；「只加技能」＝改前＋`skill_rift_flicker.yaml`（`rift_shard_lord.yaml` 不動）。

| 雜湊 | 改前 | 只加技能 | 本段 |
|---|---|---|---|
| `hash_ruleset` | `6cd20ae4…cc81` | `a2fb31c0…0ce0` | `a2fb31c0…0ce0` |
| `ruleset_hash`（一輪存檔） | `d162e4a4…3ce7` | `21d3c611…6c62` | `79b36f86…7a4e` |
| `content_digest`（世界日誌） | `b921c8ec…3d21` | `18f9fdb2…a993` | `93bead55…63bd7` |

- 改前三個值和 BAL-21b 報告第 3 節的「改後」逐字相同。規則包只內嵌技能，所以 `hash_ruleset` 只隨新技能變；另兩個涵蓋全部內容檔。完整值：`a2fb31c0d6d1fd3f8a5740cdc77d73422056ec5a060f47515216d1db6f710ce0`、`79b36f86a85e888a308492909abcf67111744c510e5a89485a780acee5f47a4e`、`93bead55aab9787632a6cc758b012a741f3519a011f2f5c59ddfeff299a63bd7`。
- **CLI 快照**：不重產時 `-m slow` 10 項不過：`skills_list` 與 `skills_show_all/07～15`（新招排序後落在第 07 片，之後整片位移），其他 14 項（含戰鬥類）照舊通過。只用 `-k "skills_list or skills_show_all"` 重產（`cli_output_hashes.json` 10 行）。證明：新快照配「只加技能」的內容（`TRPG_CONTENT_DIR`）24/24 通過；配改前內容剛好這 10 項不過、其餘 14 項通過。
- 技能圖示快照只多一筆（第 1 節）。parity 夾具、其他快照沒有重產。`gen:api` 不必跑（沒動 API）。

## 4. 截圖（`docs/art/shots/bal21c/`，jpg 80，2 張）

開發頁 `skill-gallery.html#bal21c&cell=72&rows=1&mute=1`，無頭 Chrome（`--headless=new --mute-audio --disable-gpu`，CDP 埠 5326；vite 埠 5325），兩者用完已依 PID 關閉。頭目朝西、從 (4,3) 放雷打 (2,2) 的主角後閃到 (7,2)。

| 檔 | 內容 |
|---|---|
| `docs/art/shots/bal21c/1-blink-start.jpg` | P3 瞬步開頭（`blinkFreeze=0`，殘影最濃）：本體已在目的格，身後（東側，朝西鏡像）兩層殘影；原格有傳送消散特效 |
| `docs/art/shots/bal21c/2-blink-mid.jpg` | P3 瞬步中段（`blinkFreeze=300`，blink 約 0.5）：殘影變淡 |

**實機未看**：沒有在正式戰鬥（伺服器＋裂界門）實際打到第 3 階段；開發頁的事件照引擎實際輸出（第 1 節）組，走正式 `playbackPlan` → `frameOps`。朝東的鏡像只在測試與程式確認（出招時 `playSkill` 會把頭目轉向目標，開發頁的 `&face=east` 拍出來仍朝西）。

## 5. 量測（只跑一次完整版）

`scripts/cb2e_sim.py bosses --only rift --seeds 100`（8 build × 100 種子＝800 場／方案，同種子配對；改前用 `--content` 指改前內容；程序池 6 用暫存區包裝，腳本沒改）。開跑前已問開發 PM。`bosses` 的 JSON 只有彙總，勝負翻轉場數算不出來。

**每回合施放率（P3、P4；P1、P2 兩邊逐項相同）**

| 階段（進入場數；頭目行動回合數） | 招 | 改前（`skill_blink`） | 改後（`skill_rift_flicker`） |
|---|---|---|---|
| 第 3 階段（636；1673 → 1728） | `rift_shatter` | 377／1673＝23% | 428／1728＝25% |
| | `blink` → **`rift_flicker`** | 2／1673＝0% | **643／1728＝37%** |
| | `rift_tremor` | 1097／1673＝66% | 968／1728＝56% |
| 第 4 階段（159 → 175；344 → 379） | `rift_shatter` | 57／344＝17% | **40／379＝11%** |
| | `blink` → **`rift_flicker`** | 0／344＝0% | **109／379＝29%** |
| | `rift_tremor` | 175／344＝51% | 158／379＝42% |

**勝率與輪數**

| build | 改前 | 改後 | 差 |
|---|---|---|---|
| 整體（800） | 65%／12.9 輪 | **63%／13.0 輪** | −2 |
| striker | 54% | 53% | −1 |
| fire | 50% | 50% | 0 |
| storm | 69% | 68% | −1 |
| ranged | 73% | 69% | −4 |
| tank | 74% | 72% | −2 |
| guardian | 86% | 84% | −2 |
| healer | 87% | 85% | −2 |
| **trapper** | **27%（< 40%）** | **21%（< 40%）** | **−6** |

判法（已定：`rift_flicker` ≥ 10%、整體 60～70%、10～15 輪、每個 build ≥ 40%，各 100 場）：

- 界隙閃擊 P3 37%、P4 29% 達標（≥ 20%）；界碎 P3 25%（沒被擠掉），P4 從 17% 降到 11%（仍 ≥ 10%，餘裕小）。
- 整體 63%、13.0 輪在範圍內。
- **trapper 改前就 27%（< 40%），改後 21%**，不過關；其他 7 個 build 都 ≥ 50%。trapper 不過關是改前就存在的缺口（CB-2d 37%／30 場是小樣本），本段只照實寫，不調頭目數值（使用者決定）。

## 6. trapper 掉場調查（只讀；結論＋候選）

**做法**：暫存區腳本 `trace.py`（不進 repo）跑 trapper × 30 種子 × 3 份內容（改前 `skill_blink`；界隙閃擊 1d8；界隙閃擊 1d4），逐事件記頭目與主角在各階段的行動、陷阱放置／觸發／過期、頭目身上的定身、傳送、雙方傷害。1d8 與 1d4 的 30 場**逐場完全相同**（頭目放的是升階後的 `skill_rift_flicker_t3`，傷害骰由升階重算；另用 striker 3 場對過每一下的骰值與傷害也相同）。

| 第 3 階段（18 場進入；主角 27 回合） | 改前 | 界隙閃擊 |
|---|---|---|
| 勝場（30 場） | 13 | 10 |
| 頭目傳送次數（放幾次就閃幾次） | 0 | 13（放 13 次） |
| **傳送時頭目身上有定身** | — | **12／13** |
| 主角回合開頭與頭目的距離（平均） | 3.0 格 | 4.4 格 |
| 主角對頭目的傷害／我方其他人 | 815／1542 | **517／1076**（−37%／−30%） |
| 頭目造成的傷害 | 1315 | 1678（+28%） |
| 主角放寒鎖／陷地術（定身、降地形） | 9／10 | 7／6 |
| 主角放捕獸夾（頭目從沒踩到；第 4 階段 5 個過期） | 0 | 6 |
| 陷阱對頭目的傷害 | 0 | 0 |
| 進入第 4 階段（第 15 輪界崩、傷害加倍）的場數 | 15 | 18 |
| 第 4 階段我方倒下／主角首次倒在第 4 階段 | 18／4 | **30／8** |

**結論**

1. **不是「陷阱被閃走浪費」**：兩邊陷阱對頭目的傷害都是 0（頭目 `immovable`、第 3 階段改前根本不走路，灰燼地雷與捕獸夾從沒打到它）；trapper 打頭目只靠寒鎖、陷地術把它釘在原地，讓自己與傭兵貼上去輸出。
2. **閃擊幾乎都在被定身時放（12／13）**：傳送不受定身（`root` 只擋主動移動），定身白放；頭目閃開 4 格後主角與傭兵要重新接近，第 3 階段我方對頭目的輸出掉三成以上，頭目自己的傷害多 28%。
3. **拖進第 4 階段**：第 3 階段變長，更多場撐到第 15 輪的界崩（傷害加倍），trapper 的敗場集中在第 4 階段（我方倒下 18 → 30）。其他 build 自帶輸出或治療，同樣被閃開但損失小（800 場只差 0～4 個百分點）。

**候選（只動頭目，交玩法 PM／使用者選；本段都沒做）**

| # | 候選 | 預期效果 | 代價／注意 |
|---|---|---|---|
| A | **閃擊落點縮短**：`skill_rift_flicker` 第二段 `ground_tile` 射程 4 → 2（內容） | 閃開後仍在 trapper 寒鎖、陷地術的射程 4～5 內，第 3 階段輸出損失變小；「每回合換邊」的感覺變弱 | 改技能數值＝會改三個雜湊與 CLI 快照；預算會再降（約 −0.4） |
| B | **被定身時不能閃**：給閃擊加「施放者沒有 `root`」條件 | 直接對準機制 2（12／13 的閃都是在被定身時），定身重新有價值；不影響沒定身的換邊 | **要引擎**：現有 `skill_conditions.yaml` 沒有「施放者沒有某狀態」的條件，也可改成「定身擋自身傳送」的規則（影響所有傳送招），都要另排引擎段 |
| C | **延後界崩**：`rift_collapse` `round_at` 15 → 17（或第 3 階段頭目傷害略降） | 對準機制 3（拖進第 4 階段才大量倒下）；所有慢隊伍都受惠 | 整體勝率會往上（現 63%，上限 70%）；`round_at` 目前不在數值工坊白名單，要使用者決定或加進白名單 |

建議先看 B（最對症、不動整體平衡），引擎段做之前可先用 A 或 C 在數值工坊試。

## 7. 測試與檢查（結束碼）

| 指令 | 結果 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0（1488 個檔） |
| `uv run lint-imports` | 0（14 kept、0 broken） |
| `uv run trpg content check` | 0（662 個檔、404 個技能） |
| 相關 pytest（`tests/engine/test_rift_flicker_bal21c.py`、`test_enemy_skills_149.py`、`test_boss_phases.py`、`tests/content/test_enemy_skill_count_149.py`、`test_skill_scaling.py`、`test_skills_content.py`、`tests/skillgen/test_enemy_only.py`、`tests/world/test_enemy_ai_moves_149.py`、`test_shard_lord_first_phase.py`、`tests/narrative/test_skill_icon.py`） | 0：589 passed |
| `uv run pytest -q tests/skillgen tests/narrative -n 8 -m ""`（含 slow） | 0：5390 passed、14 skipped |
| `uv run pytest -q tests/cli/test_output_snapshots.py -m slow` | 0：24 passed（重產 10 個鍵之後）；配改前內容剛好那 10 項不過、其餘 14 項通過；配「只加技能」24 passed |
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client test` | 0（307 檔、3962 passed） |
| `corepack pnpm -C client build` | 0 |
| `trpg battle --map rift_gate --seed 7 --log-json` ＋ `replay` | 0／0，重播驗證通過 |

## 8. 影響

- 規則包雜湊、一輪存檔 `ruleset_hash`、世界日誌 `content_digest` 都變（第 3 節）：使用者重開伺服器後，進行中的一輪從頭開始、舊世界日誌標成「規則已變、不能重播」；舊戰鬥紀錄內嵌當時的規則包，照樣可重播。舊存檔不必相容（使用者 2026-11-12），本段沒刪存檔、沒寫遷移。`LOG_FORMAT` 不變。
- 請使用者重開伺服器檢查的重點：裂界門碎晶之主 HP 50% 以下（第 3、4 階段）會「放一發晶刺再閃到 4 格內另一格」，閃到的位置有半透明殘影由濃到淡（約 0.6 秒）。

## 9. 新增的複雜度 `# noqa`

無。

## 10. 待 PM 決定

1. **界隙閃擊傷害骰 1d8 → 1d4**（只為過預算 126% → 95.2%；草稿註明「未走預算校準」）：頭目實戰是 `_t3`，改不改結果完全相同；只影響技能說明與雜湊。要回 1d8 得先登記預算例外（要玩法決定出處）。
2. **第 4 階段也換成界隙閃擊**：P4 沒有自己的招式組、沿用 P3，所以自動一起換（P4 29%，界碎 P4 17% → 11%）。若要 P4 保留 `skill_blink`，要給 P4 另寫一組 `skills`。
3. **trapper 21%（改前 27%）不到 40%**：照使用者決定不調；候選 A／B／C 見第 6 節（B 要引擎段）。
4. 界碎 P4 11%（10～20%，餘裕小）；P3 `rift_tremor` 66% → 56%。
5. **前端只對「後段是閃現」的複合技把位移排到出招後**：人形的「動作 → 位移」複合技（若有）仍會先位移再出招，是否一併修正要另排（會改既有人形播放）。
6. 截圖只在開發頁拍；朝東時殘影鏡像只靠程式與測試確認（第 4 節）。
