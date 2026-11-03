# Phase 5C-2 報告：朋友的影子（併 5C-1 待決的玩法 PM 決定）

> 實作者：implementer agent（2026-11-03）。依 `docs/phases/Phase5計畫.md` 第 23 節（本段新增的詳細規格，`53d7d520`）。
> 依據：09 9.6.7 #13、9.6.8 #87、9.6.9 #97／#100、9.6.10 #102；`docs/專案計畫.md` 3.1。玩法 PM 2026-11-03 對 5C-1 待決的四項決定（開發 PM 轉達）一併做完。

## 1. 交付

| 項目 | 內容 | commit |
|---|---|---|
| 規格 | `Phase5計畫.md` 第 23 節「5C-2 詳細規格」（「之後各段規格」改第 24 節） | `53d7d520` |
| 世界 | `src/trpg/world/shadows.py`（新）：整備後自動存影子、強度上限、每天第一次被借用的獎勵與戰報；`party.py`：`hire` 加 `shadows`／`ai`、`shadow_ai` 動作、傭兵技能照欄位上限（`slot_capped`）、`shadow_spawns`、`season_boss_problem`；`state.py`：`ShadowSnapshot`／`ShadowReport`／`ShadowRecord`、`WorldState.shadows`、`CharacterState.shadows`／`party_ai`／`shadow_ai`；`battle.py`：獨行、影子出場、`battle_started.shadows`、`record_lent`；`step.py`：整備動作後存影子 | `3b82c984` |
| 內容 | `mercenaries.yaml`：青鋒底稿 `build_charger`；`ai_choices`（7 種）、`shadow_daily_coins: 1`、`shadow_reports_kept: 20`；schema 與載入檢查（打法 ID 必須在 `ai_profiles.yaml`） | `3b82c984` |
| API | `PartyView` 加 `shadows`（`ShadowView`）、`ai_choices`、`ai`、`season_boss_ok`／`season_boss_zh`，成員加 `shadow`、`ai_zh`；`WorldView.my_shadow`（`MyShadowView`）；`WorldActionRequest` 加 `shadow_ai`；事件句子（存影子、獨行、借用、打法）；OpenAPI 與 `schema.d.ts` 重產 | `3b82c984`、`c6275a98` |
| 前端 | 小鎮「雇用隊友」面板分「傭兵」「影子」兩頁（共用 2 個隊友位、勾滿時其他停用）、每名已選成員一個「打法」下拉；被壓上限的影子列顯示 `cap_zh`；右側「隊伍」顯示打法與「賽季 Boss 只准系統傭兵」；右側新增「我的影子」（存的地點、預設打法下拉、任務幣、戰報，面板內捲動）；遇敵面板與建角說明改成獨行 | `f6dbd199` |
| 測試 | `tests/world/test_shadows.py`（22）、`tests/api/test_world_shadow_api.py`（2）、`tests/content/test_world_mercenaries.py`（+2）；5C-1 與依賴「打得贏」的既有測試改帶 2 名傭兵（`tests/world/helpers.PARTY`）；vitest `party.test.ts`（7） | 同上 |

## 2. 影子資料格式（`trpg-world/1`、`trpg-char/1` 不升版號，新欄位都有預設值）

```text
WorldState.shadows: tuple[ShadowRecord]      # 依主人 ID 排序、每人一筆
  ShadowRecord
    snapshot: ShadowSnapshot
      owner            主人角色 ID
      hero             UnitTemplate（名稱、屬性、武器、裝備中的技能與反應、基礎 HP、種族）
      level, skill_tier, attribute_points（未分配）, attribute_spent
      skills           裝備中、不在內容庫的技能定義（依 ID 排序）
      ai_profile       主人設定的預設打法（None＝範本的）
      gear: ()         裝備欄位預留（5D 物品等級）
      region, location, saved_at
    coins              被借用累計的任務幣（5D 轉入角色）
    reward_day         最後一次給獎的 refresh_day
    reports            ShadowReport（day, at, borrower, borrower_name, region, location, won, foes, coins），最近 20 則
CharacterState.shadows: tuple[ShadowSnapshot]  # 借用當下的複本
CharacterState.party_ai: {成員 ID → 打法}       # 傭兵 ID 或影子主人 ID
CharacterState.shadow_ai: str | None            # 自己影子的預設打法
```

## 3. 上限規則（#87；`trpg.world.shadows.shadow_spawn`）

| 項目 | 規則 |
|---|---|
| 等級 | `min(影子等級, 招募者等級)` |
| 屬性 | 多出的等級 × `attribute_points_per_level` 點：先扣未分配點，再從 `attribute_spent` 最多的屬性逐點扣（同分照 str、dex、con、int、wis、wil） |
| HP | 基礎 HP＋`level_hp_bonus(基礎 HP, 借用等級)`；每場滿 HP／法力／耐力 |
| 技能階級 | 上限 `hero_tier(借用等級)`（影子自身較低時照自身）；超過的照 `at_run_tier` 往下重配 |
| 技能 ID | 不在內容庫的一律改名 `<原 ID>_<主人 ID>`（避免和招募者或其他影子的生成技能相撞），反應規則一併改 |
| 物品等級 | 5D（`gear` 預留） |
| 單位 | `id = shadow_<主人 ID>`、名字＝主人角色名、打法＝招募者選的 → 主人的 `shadow_ai` → 範本預設 |

## 4. 玩法 PM 定（5C-1 待決，併入本段）

1. **青鋒底稿** → `build_charger`（單手劍、力量 16 的衝陣近戰；稱號「近戰劍客」不變）。
2. **傭兵技能照欄位上限**：依底稿順序挑，超過主動 6／被動 3／反應 1／姿態 1、專精互斥或傳說上限就跳過，被跳過的反應規則一併拿掉（`slot_capped`；名單的技能概要也照它）。目前 9 名底稿剛好都在上限內，實際沒有被砍的技能。影子帶的是角色裝備中的技能（本來就受欄位上限）。
3. **雇 0 名＝獨行**：大世界的我方＝主角＋傭兵＋影子；標準隊友只留在 roguelite。
4. **打法**：`hire` 帶 `ai`（成員 → `ai_choices`），存在 `CharacterState.party_ai`；影子主人用 `shadow_ai` 設預設（#102）。

## 5. 瀏覽器驗證紀錄（Claude_Browser；`.scratch_5c2/serve.py` 在 **8080** 提供 API＋`client/dist`，存檔 `.scratch_5c2/saves`；`TRPG_LLM_BASE_URL=http://127.0.0.1:9/v1`、`TRPG_LLM_GENERATE=false` 降級）

預覽窗格在背景（截圖逾時），以 `get_page_text`／DOM 查詢記錄。

1. 經 API 建角色 A「阿霧」、B「小美」；A 在霧渡鎮「休息」→ 事件「已把目前的配置存成影子（Lv 1）。」、`my_shadow.saved_zh`「霧渡鎮・Lv 1」。
2. 首頁 →「進入大世界（測試）」→ 選小美進入（1600×900）：隊伍面板「隊伍 1 人／小美 主角・1 級／獨行：只帶主角」，「我的影子 還沒存」。
3. 點「雇用隊友」→「影子（1）」分頁：「阿霧的影子 Lv 1・火焰法杖／技能：火焰爆、烙印」，按鈕「確定：獨行（只帶主角）」。勾阿霧的影子 →「傭兵（9）」勾鐵壁 → 其餘 8 名停用（合計 2 位）；出現兩個打法下拉，把阿霧的影子設「守衛」→ 按「確定隊伍：鐵壁、阿霧的影子」。
4. 隊伍面板：「小美 主角／鐵壁 盾衛・守護・1 級・打法 預設（守衛）／阿霧的影子 影子・火焰法杖・1 級・打法 守衛／賽季 Boss 只准系統傭兵，隊伍裡不能有影子」；紀錄「隊伍：雇用鐵壁；借用阿霧的影子（免費）。」「已把目前的配置存成影子（Lv 1）。」
5. 點地圖「渡口石階」→ 來回走到遇敵：遇敵面板「主角（開場 HP 40）＋鐵壁、阿霧的影子」。開戰：我方單位「小美、鐵壁、阿霧」。主角動作以頁面內 `fetch` 送 `/api/battles/{id}/actions` 打完（戰鬥畫面不是本段改的）：8 輪打贏（小美倒下、鐵壁 18、阿霧 38 HP）。
6. 回到地點圖：「打贏了（8 輪），獲得 100 經驗。」「渡口石階已清空…」。
7. 「換角色」→ 進入阿霧：「我的影子 霧渡鎮・Lv 1／被借用得到的任務幣：1／第 1 天：你的影子幫小美在渡口石階打倒了盜賊 ×2、盜賊盾衛（+1 任務幣）」。（第一次看到時寫成「第 20759 天」——天數用了絕對日；已改成從賽季開始那天算，`c6275a98`，重開伺服器確認為「第 1 天」。）
8. **浮動卡 6.5.1**（影子名的 `<Hint>`）：1600×900 滑過 →卡片貼齊上方（卡底 440.2＝觸發元素頂 440）→ 滑進卡片不關 → 內容一行不需捲動（`scrollHeight == clientHeight` 36、`max-height` 892px）→ 點一下釘住（`pinned`）→ Esc 關閉。800×600：卡片往內推到 x=4、貼齊上方（卡底 290.2＝觸發頂 290），釘住、Esc 正常；文件沒有水平捲動（`scrollWidth` 785 < 800）。卡片內容短，沒有「捲到底」可測。
9. 結束時只停了自己開的伺服器（`TaskStop`，兩次），關閉自己開的分頁、重設視窗大小。

## 6. 代決（開發 PM 定，最保守預設；規格 23.13）

| # | 事項 | 代決 |
|---|---|---|
| 5C2-1 | 「朋友」是誰 | 帳號（5E）還沒做：同一伺服器上的所有其他角色都能借（含自己的其他角色，#100）；`ShadowView.own` 預留給 5E，目前一律 `False` |
| 5C2-2 | 「城鎮整備」 | 休息、換技能、雇用、影子打法、成長動作（配點、重配、閃現、選閃現、溶掉、傳承、立誓、解除），動作後人在城鎮且沒有遭遇／待選閃現／三選一 |
| 5C2-3 | 影子存在哪 | `WorldState.shadows`；借用時複製進招募者角色（戰鬥設定只由自己的角色檔重建，可重播） |
| 5C2-4 | 已借的影子跟不跟著更新 | 不跟；重新 `hire` 才換成最新的 |
| 5C2-5 | 任務幣與戰報記在哪 | 世界快照的影子紀錄（`world_step` 只回傳出手的角色，不能改主人的角色檔；PM 建議「記在主人角色上」改為記在世界上，API 照樣只給主人看）；5D 轉入主人角色 |
| 5C2-6 | 「每天第一次被借用」的時點 | 帶影子打完一場（勝負都算）；只雇不打不算；同一天之後的借用不給獎、不加戰報 |
| 5C2-7 | 數量 | `shadow_daily_coins: 1`（初值）、戰報保留 20 則 |
| 5C2-8 | 屬性怎麼扣 | 見第 3 節 |
| 5C2-9 | 影子的定位 | 「武器・種族」（玩家 build 沒有固定定位） |
| 5C2-10 | 出場順序 | 傭兵在前、影子在後 |
| 5C2-11 | 打法選單 | 莽夫、夾擊者、刺客、弓手、狡猾、守衛、支援（不含「原地不動」與平衡用的「預言者」） |
| 5C2-12 | 影子開場狀態 | 每場滿狀態（同傭兵） |
| 5C2-13 | 戰報的「第幾天」 | 從賽季開始那天算第 1 天（6 點刷新） |

## 7. 待 PM 決定

1. **獨行太難（數值）**：改成雇 0 名＝獨行後，1 級主角獨自在渡口石階（1 級地點）用效用 AI 代打 16 個種子 **全輸**（既有測試因此改帶 2 名傭兵）。新角色預設是獨行，開局第一步若沒雇傭兵很可能一直輸；建議：新手引導第一步提示雇用、或新角色預設帶 2 名傭兵、或之後用模擬調敵人（交玩法 PM）。
2. **影子出現在世界事件中**（9.6.3「或在世界事件中遇到它」）、**酒館看朋友的足跡與戰報**（9.6.7 #1）：本段沒做，排在之後哪段？
3. **戰鬥外的隊友打法只改權重模式**：「打法」＝`ai_profiles.yaml` 的行為模式（覆寫單位的 `ai_profile`）；戰鬥中的隊友指令照舊。若玩法上要更細的設定（例：保護誰、站位），另排。
4. **自己的角色標記與帳號限制**：5E 帳號做好後，`own` 要填、`hire` 要限制成「朋友＋自己的角色」，賽季 Boss（5F-3）呼叫 `season_boss_problem`。
5. **任務幣轉入**：5D 任務幣做好後，把 `ShadowRecord.coins` 轉進主人角色（之後歸零或改成只記帳）。
6. **影子技能改名**：影子的生成技能在戰鬥裡改名 `<ID>_<主人 ID>`；戰鬥紀錄與單位卡顯示的是技能中文名，不受影響。若之後要統計「影子用了哪些技能」，要記得反查。

## 8. 檢查（交件前 `git merge main`：`d356deff` 只改設計文件，無衝突；合併後全部重跑）

- `ruff check .`、`ruff format --check .`、`mypy`（1070 檔）、`lint-imports`（9 契約）通過。
- `pytest tests/world tests/content tests/api tests/test_architecture.py -n 8`：2784 passed。
- `pytest tests/cli -m "slow or not slow" --timeout=3000`：180 passed。
- `npx vitest run`：128 檔、1221 passed；`npm run build`（`corepack pnpm -C client build`）：通過。
- OpenAPI 重產（`export_openapi.py` → `gen:api`），`test_openapi_snapshot` 通過。
