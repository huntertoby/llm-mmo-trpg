# BAL-16 完成報告｜#86 頭目倒下護衛撤退、#93 潮濕 × 治療、格擋 vs 還擊量測

分支 `worktree-agent-a9eed0fb6400874a7`（含 main `8a9880e0`）。規格：`docs/phases/PhaseBAL計畫.md` 第 11 節（16a、16b）與第 10 節末「BAL-15c 驗收與追加量測」。原始表在 `docs/phases/BAL-16/`：`boss.md`、`heal.md`、`block_riposte.md`。腳本：`scripts/bal16a_boss.py`、`scripts/bal16b_heal.py`、`scripts/bal16_block_riposte.py`。

## 1. BAL-16a｜頭目倒下，護衛撤退（#86，05 5.8）

### 做了什麼

- 勝利條件 `Objective`（`src/trpg/content/maps.py`）加欄位 `leader_retreat`（預設關；只能配 `eliminate`，否則驗證失敗）。Boss 地圖 `content/maps/bandit_lair.yaml` 寫 `objective: {kind: eliminate, leader_retreat: true}`；`MapDef.objective_for("eliminate")` 改為回傳地圖本身的全滅條件（之前一律回傳空的 `Objective()`），roguelite 一輪的 Boss 戰與模擬都因此帶到這個旗標。一般地圖（swamp、bridge_chasm 也有帶 `boss` 標籤的 `bandit_boss`）不受影響。
- 引擎 `src/trpg/engine/objectives.py`：`check_battle_end` 在雙方都還有人時，若 `leader_retreat` 開、場上曾有敵方頭目（`boss` 標籤、非召喚物）且全部倒下，判我方勝，新結束原因 `leader_defeated`（`EndReason` 新增）。多名頭目時要全部倒下；場上沒有頭目時永遠不觸發。
- 撤退的護衛 **不標倒下、不扣血**，所以不算擊殺；原型的經驗是每場固定（`xp_per_battle`），Boss 戰本來就沒有裝備三選一，「不給擊殺經驗、不掉落」自然成立；`finish_battle` 以 `winner` 判勝，獎勵照完整勝利（首殺／Boss 獎勵同一條路徑）。
- 文字：敘事 `戰鬥結束：我方勝利（頭目倒下，護衛撤退）`；說明表 `result_leader_defeated`；「全滅」規則多一行「Boss 戰：頭目倒下時，剩下的護衛撤退，直接勝利」；前端 `END_REASONS` 加 `leader_defeated: 頭目倒下`（結算畫面「勝利！（頭目倒下）」＋說明一句）。

### 量測（`bal16a_boss.py --seeds 60`；與 BAL-9b／9c 同一套跑法；頭目 HP 700‰ 不動；每格 180 場）

「前」＝同一份程式把 `leader_retreat` 關掉（關掉時判定與 BAL-16a 前完全相同）。

| 設定 | 勝率／輪數 | 打死頭目場數 | 打死頭目仍輸 | 撤退勝場（平均撤退敵數） |
|---|---|---|---|---|
| 有召喚 前 | 46.1%（CI 39–53）／10.1 | 101 | **18** | — |
| 有召喚 後 | **56.1%**（CI 49–63）／**8.7** | 101 | **0** | 53（1.6） |
| 無召喚 前 | 23.9%（CI 18–31）／8.2 | 45 | **2** | — |
| 無召喚 後 | 25.0%（CI 19–32）／7.9 | 45 | **0** | 15（1.8） |

- 「先打死頭目、再被護衛打垮」的場次 **消失**（18→0、2→0）。
- 有召喚 +10 點、輪數 10.1 → 8.7（進入 6–10 輪目標）；無召喚只 +1.1 點（無召喚打死頭目的場次本來就少，45/180；勝負仍卡在打不死頭目）。
- 頭目 HP 700‰ 沒動；數字交玩法 PM 決定要不要重調（05 5.8「補償數值之後重量」）。

## 2. BAL-16b｜潮濕 × 治療（#93，05 互動表下方）

### 做了什麼

- 規則包 core 新欄位 `wet_heal_permille`（模型預設 1000；`content/rules/core.yaml` 寫 1200）。
- 引擎 `effects/handlers.py`：所有治療（`heal` 效果與 `element_heals_allies` 的傷害轉治療）的受治療倍率 ＝ 狀態倍率（中毒 500）× 目標站在水面格時的 `wet_heal_permille`。`healed` 事件的 `received_permille` 含這個倍率，敘事自動顯示「（治療 ×1.2）」。**護盾不放大**（`shield` 不經這條路）。
- 卡片：`content/skill_keywords.yaml` 潮濕的「利用」加回 `{effect: heal}` 與 `{change: heal_permille}`，等級 **通用（general）** 並附理由「站在水上的目標受到的治療 +20%」。治療技能卡片恢復顯示「利用潮濕」（標灰附理由）：7 招會顯示（`skill_bloodlust`、`skill_qi_breath`、`skill_radiant_mend`、`skill_renewal`、`skill_sanctuary`、`skill_second_wind`、`skill_steady_breath`）；`skill_form_renewal` 因為有專屬關鍵字，照 #54 規則不顯示通用歸類。開局技能池與候選產生器只看專屬規則，不受影響。

### 量測（`bal16b_heal.py --normal-seeds 6 --boss-seeds 20`；前＝`wet_heal_permille` 覆寫 1000）

有治療技能的 4 個 build（build_push、build_support、build_healer、build_gambler）：

| 設定 | 勝率／輪數 | 我方受治療／場 | 其中站在水上 |
|---|---|---|---|
| 一般戰 前／後（n=240） | 55.4%／5.96 → 55.4%／5.96 | 28.0 → 27.7 | 3.5% → 3.9% |
| Boss 戰 前／後（n=80） | 38.8%／9.25 → 38.8%／9.25 | 36.6 → 36.6 | 0% |

勝率完全沒變：只有約 3.5% 的治療落在水面上（每場 0.15 次），Boss 地圖沒有水。各 build 前後也完全相同。若要讓這條規則有感，需要 AI 刻意把隊友帶到水上治療或 build 自帶造水，屬玩法層面（見待 PM 決定）。

## 3. 追加量測｜格擋 vs 還擊（7 個近戰 build）

`bal16_block_riposte.py --normal-seeds 3 --boss-seeds 10`：7 個近戰具名 build（push、tank、assassin、guardian、charger、gambler、wallburn）英雄的反應技換成「還擊」（同 BAL-15c 的 `riposte` 覆寫）。格擋優先（`riposte+blockon`）量格擋省下的傷害（未格擋傷害 − 實際傷害，護盾前）；反應技優先（`riposte`，現行預設）量還擊每次觸發後英雄造成的傷害（沒命中算 0）。每輪＝除以英雄存活的輪數。

| 合計 | 格擋／場 | **格擋每次省下** | 格擋每輪省下 | 還擊／場 | **還擊每次傷害** | 還擊每輪傷害 | 勝率 格擋優先／還擊優先 |
|---|---|---|---|---|---|---|---|
| 一般（n=210） | 1.40 | **3.89** | 1.17 | 1.24 | **6.40** | 1.81 | 41.0%／45.2% |
| Boss（n=70） | 2.01 | **5.01** | 1.58 | 1.29 | **7.09** | 1.72 | 17.1%／8.6% |

- 還擊每次傷害（6.4／7.1）高於格擋每次省下（3.9／5.0）；換算每輪，一般戰還擊 1.81 > 格擋 1.17，Boss 戰兩者接近（1.72 vs 1.58）。**還擊並不較低**。
- 但 Boss 戰勝率 17.1% → 8.6%（n=70，樣本小；BAL-15c 也看到 20.3% → 12.7%）：Boss 戰護衛多為遠程，還擊（`hit_by_melee`）觸發機會少於格擋，打出的傷害也不換成存活。
- 各 build 細節見 `BAL-16/block_riposte.md`；guardian 還擊每次 13～18 點偏高（觸發少、n 小，可能含還擊附帶的後續傷害），解讀時請保守。

## 4. 快照、版本與測試變動

- **`LOG_FORMAT` `/96` → `/97`（16a）→ `/98`（16b）**：`runner.py` 文件字串、`docs/phases/戰鬥紀錄格式變更.md` 各加一條、所有測試字面值（含 `tests/roguelite/fixtures/flash_history_3wr1.json`、`endswith("/9x")` 三處）。
- **存檔版本不變**（`trpg-run/13`）：一輪狀態結構沒變（`end_reason` 本來就是字串）。
- **OpenAPI／前端型別**：`client/openapi.json`、`client/src/api/schema.d.ts` 重產（`Objective.leader_retreat`）；client 測試物件補 `leader_retreat: false`（`objective.test.ts`、`testFixtures.ts`）。
- **client fixture**：`client/src/battle/fixtures/glossary.json` 重產（結束原因說明、全滅規則多一行）。
- **行為快照** `tests/skillgen/fixtures/refactor_3wr2.json`：重產，只變 3 筆（`skill_form_renewal` 的閃現出題，種子 3／11／5）——閃現會看到通用關鍵字。
- **CLI 輸出快照**：沒有變。
- 斷言改動：`tests/skillgen/test_keywords.py` 通用規則數 19 → 21（直接反映新增的兩條規則，不是靠種子）。沒有重挑種子。
- 新測試：`tests/engine/test_leader_retreat_bal16a.py`（頭目倒下即勝、護衛未倒下、旗標關閉照舊、多頭目要全倒、沒有頭目不觸發、只能配 eliminate、Boss 地圖帶旗標而一般地圖沒有、真實 Boss 戰以撤退結束並重播一致）、`tests/engine/test_wet_heal_bal16b.py`（水上 ×1.2、乾地 ×1.0、護盾不放大、卡片顯示通用的利用潮濕）。

## 5. 檢查

ruff check、ruff format --check、mypy（371 檔）、lint-imports（7 契約）通過。pytest（`-m "(slow or not slow) and not llm"`，`-n 6`）：16b 之後 `tests/engine`＋`content`＋`narrative`＋`api`＋`skillgen`＋`test_architecture.py` 10132 passed（修正上述兩處後）；`tests/roguelite`＋`sim`＋`cli` 545 passed。前端 vitest 120 檔 1176 passed，`pnpm build` 通過。重播：`trpg battle --map swamp --seed 7` → `battle replay` 通過（88 動作、313 事件）。未跑完整 `scripts/check.py`。

## 6. 待 PM 決定

1. **Boss 戰 HUD**：勝利條件 HUD 仍顯示「⚔ 全滅」，只在全滅說明加一行 Boss 規則、結算畫面顯示「頭目倒下」。要不要另給 Boss 戰專屬的勝利條件標示（例「⚔ 打倒頭目」）。
2. **撤退的呈現**：護衛不播撤退動畫、沒有獨立事件，戰鬥直接結束（最保守）。大世界「殘部重整」線頭未做（後期）。
3. **頭目 HP 700‰**：有召喚 56.1%／8.7 輪、無召喚 25.0%／7.9 輪，交玩法 PM 決定是否重調。
4. **「身上潮濕」**：目前沒有任何「潮濕」狀態，只實作「站在水面格」；之後若加潮濕狀態再接上。
5. **通用 vs 專屬**：治療 → 利用潮濕採「通用」（卡片標灰附理由；不進潮濕起始池、不影響候選）。若要當專屬（卡片一律照常顯示、治療技能進潮濕池），會改開局與候選產生，需玩法 PM 決定。`skill_form_renewal` 因有專屬關鍵字而不顯示。
6. **治療範圍**：+20% 套用在所有治療（技能治療、再生、吸血、形態治療、元素治療隊友），只排除護盾；若只想放大「治療技能」需再定。
7. **#93 的實際效果近乎零**（3.5% 治療落在水上、勝率不變）；是否需要 AI 偏好把隊友帶到水上治療。
8. **還擊數值**：還擊每次傷害高於格擋每次省下，依規則不必調還擊；但 Boss 戰近戰 build 勝率在還擊優先下較低（17.1% → 8.6%，n=70），是否另處理交玩法 PM。
