# Phase NW 計畫：數值工坊（暫名）——使用者自己改 `content/` 的數值、當場驗證、一鍵小模擬、改前改後並排

> **定稿（第 0.0 節）**；原草稿（開發 PM 的規格助手起草，2026-11-12；依據本機 main `190f7bd7`，含 `a274ed48`）。第 0 節的「建議」是暫採的做法，開發 PM 與使用者確認後移進 0.0。
> 給使用者看的一頁提案：`docs/phases/數值工坊提案.md`（要使用者選的選項在那裡，答覆後回填本檔 0.0）。
> 實作者先讀：`docs/dev/上手-內容資料與模擬.md`（全文）、`docs/dev/上手-roguelite開局與入門期.md` 第一、二節（`api/`、`world/` 的位置與資料流）；前端段另讀 `docs/dev/上手-前端戰鬥畫面與動畫.md` 的開發入口與第四節。

## 0.0 使用者決定與開發 PM 定稿

使用者原話（2026-11-12，專案 PM 轉達）：「1.數值的調整不要再給你做 反而給我一個數值工仿 讓我可在裡面改各種數值 就不用你們慢慢調了」（同一句也寫在 `docs/phases/PhaseBAL-21計畫.md` 0.0）。

- **之後的平衡段**：PM 與 agent 只出報表與建議，**數值由使用者在數值工坊決定**；agent 不再改「數值工坊可改的欄位」（第 3 節欄位表），只在規格明寫時例外。
- **確定性與重播規矩不變**：數值工坊只改 `content/` 的資料；改了內容 digest 照舊會變（`content_digest`、`ruleset_hash`、`hash_ruleset`），舊世界日誌照舊標成不能重播，舊戰鬥紀錄照舊靠內嵌規則包重播。不加任何版號。
- **舊存檔不必相容**（使用者原話：「存檔都可以刪除」）。本工具的草稿、模擬結果、備份都不是存檔，格式可隨段改、不寫轉換。
- 第 0 節各項已定（下兩點）。
- **使用者答覆提案 7 項（2026-11-12，專案 PM 轉達）**：原話「都照建議」。即：(1) 入口在開發選單 `?dev=1`；(2) 另設開關 `TRPG_TUNING=1`，經 Tunnel 轉發的請求一律擋（403）；(3) 寫回自動 commit 一筆 `tune:`；(4) 技能預算超出時警告＋確認並登記例外；(5) 小模擬預設 24 場；(6) 寫回後重開伺服器生效；(7) 名稱「數值工坊」。專案 PM 已向使用者說明：每次寫回進行中的一輪會從頭開始；寫回後固定答案的測試會變紅、開發派一小段跟上（**只更新測試、不動使用者的數值**），所以不會馬上 push。
- **開發 PM 定稿（第七任）**：第 0 節 1～10 點**全部照「建議」欄**（含第 6 點收編段、第 8 點反向改動單、第 9 點 `content/tuning_fields.yaml` 不進 digest）。派工順序 NW-1a → NW-1b。

## 0. 待確認（附建議）

| # | 問題 | 出處／理由 | 建議（暫採） |
|---|---|---|---|
| 1 | **入口放哪** | 開發選單 `?dev=1`（`client/src/App.tsx:166` 起，`StartScreen.tsx:186` 已有「技能工坊」鈕）vs 主城 NPC | **開發選單**加「數值工坊」鈕。主城是玩家畫面：要登入、擁有者檢查、會被朋友看到；開發選單已是「只給自己」的入口，最省 |
| 2 | **端點在什麼條件下才掛** | `dev_mode` 預設 `true`（`config/server.toml:7`、`src/trpg/server/account_config.py:43`）；開服前才改 `false`（`docs/部署說明.md:22`）。Tunnel 進來的請求從 `cloudflared` 轉發，來源也是本機，**只看 `dev_mode` 或來源 IP 擋不住朋友** | **三道**：① `dev_mode` 為真才 `include_router`（同 `app.py:120`、`125` 的寫法）；② 另要環境變數 `TRPG_TUNING=1`（不沿用 `TRPG_DEV_ROUTES`，免得開 Boss 排演就順便開了寫檔）；③ 每個請求帶 `CF-Connecting-IP`、`X-Forwarded-For`、`Forwarded` 任一標頭就 403「數值工坊只能在本機瀏覽器直接開」。三道都在 `trpg.api.tuning` 內，測試逐條鎖 |
| 3 | **寫回後怎麼進 git** | 使用者的伺服器跑在主資料夾 `F:\PythonProject\LLM-MMO-TRPG`（main checkout），開發 PM 也在這裡合併；記憶「共用資料夾 commit 前檢查」 | **寫回＝寫檔＋在主資料夾自動 commit 一筆**（第一行 `tune(<對象 ID>): <欄位> <舊>→<新>…`，內文逐筆列改動，結尾 `Tuned-by: number-workshop`；作者用使用者自己的 git 設定，不加 Co-Authored-By）。前置檢查不過就不寫（第 5.3 節）。替代：(B) 只寫檔不 commit、PM 合併前收；(C) 寫到專用分支。B 會和 PM 的合併互相干擾，C 要使用者自己合併，都不建議 |
| 4 | **技能預算超出合格區間（70%～100%）怎麼辦**（NW-2 起） | `trpg content check` 的 `library_violations`（`src/trpg/cli/budget.py:37`）會擋；例外只能登記在 `skill_budget.yaml` 的 `known_budget_exceptions`（上手-內容 第三節第 6 點） | **當場顯示比例；超出時紅字警告、預設不能寫回；使用者勾「我確定」後可寫回，並自動把該招登記進 `known_budget_exceptions`（註解寫「數值工坊 日期」）**。理由：數值由使用者決定，但檢查照舊要過 |
| 5 | **模擬的預設規模** | 頭目戰每場約 1.2～1.9 核心秒（`PhaseBAL-20報告.md:146`：240 場、程序池 6、46～76 秒）；地圖戰 80 場 `--jobs 4` 27.8 秒（`docs/phases/BAL-6/maps_retest.txt:2`）；新手任務 325 人 `--jobs 4` 126 秒（上手-內容 第二節） | **預設「小」**：頭目 1 隻 × 8 build × 3 種子＝24 場（估 10～15 秒，程序池 4）；按鈕可選「中」（× 10 種子＝80 場，估 30～50 秒）。畫面先顯示「N 場、預估 X 秒」再按開始；改前結果以內容 digest 快取，同一份內容不重跑 |
| 6 | **使用者寫回後，測試的快照與固定種子誰收** | 改技能數值會打破 `tests/skillgen/test_refactor_parity.py` 夾具、CLI 快照、AI 固定種子測試（上手-內容 第四節第 2、3、16 點）；那些守則原本是防 agent 偷改 | **開發 PM 在下一次合併前派「收編」小段**：只更新被 `tune:` commit 影響的快照與固定種子，逐項證明變動只來自那幾筆 `tune:`（拿掉後回到舊值），**不改任何數值**。收編段的報告列「哪筆 tune 動了哪些測試」 |
| 7 | **寫回後要不要不重開伺服器就生效（熱載入）** | 伺服器在 `create_app` 載入一次內容庫（`src/trpg/api/app.py:163`），`SessionStore`、`RunStore`、`WorldStore` 都持有同一個 `lib`（`app.py:165-171`）；沒有熱載入 | **不做熱載入**：寫回後畫面顯示「重開伺服器後遊戲才用新數值」。模擬不需要重開（直接用草稿內容庫）。熱載入要換掉三個 store 的內容庫、處理進行中的戰鬥，風險大，不建議 |
| 8 | **還原怎麼做** | git revert 遇到後來又改過同一行會衝突 | **「還原這次」＝產生一張反向改動單（新→舊）放進草稿**，使用者看差異、照樣驗證後寫回（又是一筆 `tune:`）；不呼叫 `git revert`。草稿本身可整張丟掉 |
| 9 | **欄位白名單放哪** | 守則 4 內容即資料；但白名單若進內容庫，改它會改 digest | **`content/tuning_fields.yaml`＋schema `src/trpg/content/tuning_fields.py`**，只由 `trpg.api.tuning` 讀，**不登記進 `KNOWN_CONTENT_FILES`、不進 `library.files`**（digest 不受影響）。1a 要查有沒有測試掃 `content/` 下全部 YAML 而會要求登記（例 `tests/content/test_pronoun_scan.py:55` 只掃指定範圍）；有就登記為例外並寫進報告 |
| 10 | **段數** | 第 4 節 | **NW-1（1a 後端＋1b 前端，合起來才可用）→ NW-2 → NW-3**；NW-4 選做 |

## 1. 現況查證（只讀，main `190f7bd7`）

| 項目 | 現況 | 出處 |
|---|---|---|
| 內容在哪 | 頂層 `content/`，660 個檔（技能一檔一招、單位一檔一隻、地圖一檔一張；其他是表） | 上手-內容 第一節 |
| schema | `src/trpg/content/` 下；基底 `ContentModel`（`extra="forbid"`、`frozen=True`）在 `schemas.py:30`；單位 `UnitTemplate` 在 `battle.py:1612`（`max_hp`、`attributes`、`speed`、`armor_bonus`、`resist`、`element_mods`、`stamina`、`max_mana`、`skills`、`level`…），頭目階段 `BossPhase` 在 `battle.py:1544`（`trigger`、`skills`、`ai_profile`…）；技能 `SkillDef` 在 `skills/skill.py:122` | 同左 |
| 讀檔 | `load_content_file`（`loader.py:99`），YAML 用 `parse_yaml`（`loader.py:53`，`CSafeLoader`）；內容資料夾 `default_content_dir()`（`loader.py:41`）可被 `TRPG_CONTENT_DIR` 覆寫，但 `bundled_content_dir()`（`loader.py:33`）固定讀專案的 `content/` | 同左 |
| 不受 `content_dir` 參數影響的讀檔 | `skills/effects.py:254`（`skill_primitives.yaml`，走 `default_content_dir()`）、`modifier_changes.py:144`、`yaml_sources.py:29`（走 `bundled_content_dir()`）、`effect_words.py:83`、`world.py:180/186`、`narrative/skill_icon_art.py:168` | grep `default_content_dir()\|bundled_content_dir()` |
| 整包載入 | `load_library(content_dir=None)`（`library/load.py:349`），約 **1.2 秒**／次（`docs/phases/整理提案-程式.md:120`） | 同左 |
| `trpg content check` | `cli/main.py:437` `_cmd_content_check`＝`load_all_content`（`registry.py:103`）＋`load_checked_library`（`api/primitive_coverage.py:245`，載入後檢查原語對應）＋`library_violations`（`cli/budget.py:37`，技能預算與結構） | 同左 |
| digest | `hash_ruleset`（`engine/ruleset_hash.py:18`，規則包）、`ruleset_hash`（`roguelite/save.py:139`，全部內容檔依相對路徑排序）、`content_digest`（`world/save.py:381`，再加實地地圖與大世界規則）、`log_rules_key`（`world/save.py:397`）。三者都只看相對路徑與內容，**從複製出來的資料夾載入、內容相同時 digest 應相同**（1a 要測） | 同左 |
| 伺服器快取 | `create_app` 載一次（`app.py:163`），無熱載入；改內容要重開，進行中的一輪從頭開始（上手-內容 第四節第 13 點） | 同左 |
| YAML 寫法 | 註解很多（`ai_profiles.yaml` 196 行含 `#`、`rules/core.yaml` 163 行）；單位常用流式寫法（`attributes: {str: 12, …}`、`resist: {}`、`phases` 第 1 項 `{id: shell, name_zh: 殼}`，見 `content/units/ashen_heart.yaml`）。相依只有 `pyyaml>=6`（`pyproject.toml:11`），**沒有能保留註解的 round-trip 套件** | 同左 |
| 模擬（程式庫） | `trpg.sim.batch`：`BatchSpec`（`batch.py:104`，內含 `setup`，所以內容庫可以是記憶體裡的草稿版）、`map_spec`（`:116`）、`run_one`（`:159`）、`run_outcomes`／`run_batches`（`:175`／`:186`）；平行 `sim/parallel.py:30` `run_tasks`（spawn 程序池，`context` 每個行程送一次） | 同左 |
| 模擬（腳本） | 頭目施放率 `scripts/cb2e_sim.py`（542 行，走大世界真實路徑 `new_character` → `prepare_battle` → `run_battle`，`_BossWatch` 只認頭目本體）；新手任務 `scripts/ob6_newbie_sim.py`；**`scripts/` 不是套件，`trpg.api` 匯入不到** | 上手-內容 第二節 |
| 耗時（既有報告） | 頭目 240 場：程序池 6 約 46～76 秒（`PhaseBAL-20報告.md:146`）；地圖 80 場 `--jobs 4` 27.8 秒（`BAL-6/maps_retest.txt:2`）；地圖 50 場 12.7 秒（`archive/phases/Phase3F-3b報告.md:23`）；新手 325 人 `--jobs 4` 126 秒（OB-6b）；`load_library` 1.2 秒 | 同左 |
| 前端開發入口 | `?dev=1` 開發選單（`App.tsx:166`、`StartScreen.tsx`）；技能工坊 `screens/WorkshopScreen.tsx`＋`client/src/workshop/`（已有 YAML ⇄ 草稿 `yamlEdit.ts`）；開發頁 `client/dev/*-gallery.html` | 同左 |
| API | FastAPI，`app.py:114` `_include_routers`；路由在 `api/routes/`（`content`、`battles`、`runs`、`workshop`、`gear`、`world`、`mail`、`auth`）；開發用路由只在 `dev_mode` 掛（`app.py:120`、`125`）再看 `TRPG_DEV_ROUTES`（`routes/runs.py:396`）；技能工坊是 `/api/workshop`（名字已被占用） | 同左 |
| 依賴方向 | `api` 只禁 `cli`（`pyproject.toml:169`）；`api` 已匯入 `trpg.sim`（`api/sessions.py:54`）與 `trpg.world`；`sim` 可匯入 `world`（`world` 不得匯入 `sim`，`pyproject.toml:210`）；`content` 不得匯入 `engine`、`skillgen`、`world` | 同左 |
| 存檔資料夾 | `default_save_dir()`＝`TRPG_SAVE_DIR` 或專案 `saves/`（在 `.gitignore`；`roguelite/save.py:118`） | 同左 |

## 2. 和 CLAUDE.md 守則的關係

- **守則 1、2（確定性）**：引擎一行不改。模擬照舊用種子；改前改後同種子逐場配對。工具本身的「草稿 ID、時間戳」只用在工具的檔名，不進內容、不進引擎。
- **守則 3（LLM 只能提議）**：不受影響。數值工坊沒有 LLM；值由使用者輸入，經 pydantic 與跨檔檢查。
- **守則 4（內容即資料）**：改的只有 `content/` 的值；可改哪些欄位寫在 `content/tuning_fields.yaml`（第 0 節第 9 列），加欄位不改程式。
- **守則 5（依賴方向）**：新程式放 `trpg.api.tuning`（端點、草稿、寫回、git）與 `trpg.sim`（頭目量測核心從腳本搬進來）；白名單 schema 放 `trpg.content`；`library_violations` 從 `trpg.cli.budget` 搬到 `trpg.skillgen`（`api` 不能匯入 `cli`，`cli` 改成 re-export）。`engine` 不依賴任何新東西；`lint-imports` 與 `tests/test_architecture.py` 照跑。
- **守則 7（玩家輸入是資料）**：使用者在表單打的值只當資料（轉型、範圍檢查）；不拼進任何指令。git commit 訊息用參數陣列呼叫 `git`（不經 shell），值經過轉義。
- **守則 11（模擬耗時）**：工具內的模擬有規模上限（第 5.4 節）、一次一個、程序池最多 4；畫面先標「場數＋預估秒數」。agent 開發中只跑冒煙規模（每格 1 個種子）。

## 3. 範圍

**目標**：使用者在瀏覽器裡選一個對象（敵人、技能、裝備…）→ 看到中文標籤的數值欄位 → 改值、當場驗證（非法值擋下並說原因）→ 一鍵跑小模擬，和改前並排 → 存草稿、看差異、還原 → 寫回 `content/` 並自動 commit。

**可改的欄位（白名單，分段開放）**

| 段 | 對象 | 欄位 |
|---|---|---|
| NW-1 | 單位（`content/units/*.yaml`，敵人與頭目；召喚物、模擬用 build 的單位不開） | `max_hp`、`attributes.<六屬性>`、`speed`、`armor_bonus`、`max_mana`、`stamina`、`resist.<組>`、`element_mods.<元素>`（‰）、`level`；頭目 `phases[i].trigger.permille`；BAL-21a 合併後的 `phases[i].mana_restore`（若當時已有） |
| NW-2 | 技能（`content/skills/*.yaml`） | AP 消耗、耐力／法力消耗、冷卻、範圍、效果的骰數與加值、持續回合、狀態層數（實際欄位名 NW-2 規格定稿時依 `skill_primitives.yaml` 逐原語列）；預算比例即時顯示 |
| NW-2 | 單位招式組 | `skills`、`phases[i].skills`（只能從既有技能 ID 選；敵人專用招照 `enemy_only` 規則） |
| NW-3 | AI 估值表 | `content/ai_profiles.yaml` 的行為模式權重、`status_values`、`ally_status_values` |
| NW-3 | 裝備、道具、詞條 | `weapons.yaml`、`offhands.yaml`、`items.yaml`、`affixes.yaml` 的數值欄位（`look` 等外觀欄位不開） |
| NW-3 | 遭遇與敵人配置 | `content/world/encounters/<區>.yaml` 的陣容人數與等級、`armor_mods`；`content/world/fields/<區>/*.yaml` 的 `spawns` 數量；`world/enemies.yaml` 的精英詞綴數值 |

**一律不開**（寫進白名單 schema 的禁止表，載入時檢查）：會被 `bundled_content_dir()`／`default_content_dir()` 在 schema 匯入時讀的檔（`skill_primitives.yaml`、`modifier_changes`、`yaml_sources` 讀的清單、`effect_words`；理由：草稿資料夾看不到）、`rules/hit_table.yaml`（產生的，不手改）、`skill_icon_*.yaml`（美術 PM 維護）、所有 `*_zh` 文字、ID、外觀、地圖格子。

**範圍外**：熱載入（第 0 節第 7 列）；新增或刪除對象（加新敵人、新技能仍走技能工坊或 agent）；改引擎；改存檔格式；多人同時用工坊（只有使用者一人）；主城入口（第 0 節第 1 列）。

## 4. 切段

| 段 | 內容 | 完成後使用者能做什麼 | 前置 |
|---|---|---|---|
| **NW-1a** 後端 | 白名單 schema＋`content/tuning_fields.yaml`（單位欄位）；改動單與草稿；YAML 字面替換（保留註解）；草稿內容庫與驗證；差異；寫回＋備份＋git；頭目量測核心搬進 `trpg.sim.boss_probe`；模擬工作（背景、一次一個、改前快取）；端點與三道門；`library_violations` 搬家 | （沒有畫面，使用者還不能用；PM 可用 API 文件 `/docs` 試） | 無；和 BAL-21a 都動 `battle.py` 的話排在 21a 之後（`mana_restore` 欄位才在） |
| **NW-1b** 前端 | 開發選單鈕；數值工坊畫面：選對象 → 表單（中文標籤、舊值、改後值、範圍提示）→ 驗證錯誤當場顯示 → 差異頁 → 模擬（規模選擇、預估時間、進度、結果改前改後並排、勝負翻轉場數）→ 寫回確認 → 「重開伺服器」提示；還原 | **改任何敵人與頭目的血量、屬性、護甲、法力、抗性、階段門檻；跑頭目戰小模擬看勝率、輪數、倒下率、每招施放率的改前改後；存草稿、看差異、寫回並自動 commit、還原** | NW-1a 合併 |
| **NW-2** 技能 | 技能數值欄位、預算比例、招式組；地圖戰小模擬（`map_spec` 同款）與「單招施放率」；第 0 節第 4 列的預算例外流程 | 加上：**改技能的傷害、消耗、冷卻、範圍；改敵人會放哪些招**；在示範地圖上看某招被放幾次、勝率怎麼變 | NW-1b |
| **NW-3** AI 表、裝備、遭遇 | 第 3 節 NW-3 列；新手任務模擬（`ob6_newbie_sim.py` 核心搬進 `trpg.sim`，小規模每格 10 人）；全域表改動的「影響範圍」提示（例：`status_values` 一筆會影響約 20 招，上手-內容 第二節 AI 估值表第 3 點） | 加上：**改 AI 的估值、裝備與道具數值、遭遇陣容與地圖上的敵人數量**；跑新手任務一路打過去看倒下率 | NW-2 |
| **NW-4**（選做） | 寫回紀錄頁（列出 `tune:` commit、每筆的改動單）；多版模擬結果並排；把一張草稿匯出給 PM | 加上：看自己改過什麼、哪版比較好 | NW-3；使用者用過再決定要不要 |

理由：NW-1 一次做完後端＋前端會超過一段的量（YAML 字面替換、草稿內容庫、git 保護、背景模擬、頭目量測搬家，各自都要測試），所以拆成 1a／1b，但**兩個都合併才算第一段完成**。NW-1 先做「敵人」而不是「技能」：BAL-21 0.0 把頭目與新手戰的數值交給使用者，敵人欄位是純量、沒有預算檢查，最容易先跑通整條路。

## 5. 技術做法（實作者照做；有更好做法先問 PM）

### 5.1 改動單與草稿

- **改動單**＝一串 `{file: 相對路徑, path: 欄位路徑（例 "phases[1].trigger.permille"）, old: 值或「沒寫」, new: 值}`，依 `(file, path)` 排序、同一欄位只留一筆。
- 草稿存 `<save_dir>/tuning/drafts/<名稱>.json`（不在 `content/`、不進 git；`saves/` 已在 `.gitignore`）。可多份；預設一份「目前的草稿」。
- **草稿內容庫**：把 `content/` 複製到 `<save_dir>/tuning/work/<hash>/content/`（同一份 `content` digest 只複製一次），對複本套用改動單，`load_library(複本)`。1a 必測：**不套任何改動時，複本載入的 `ruleset_hash`、`content_digest`、`hash_ruleset` 和原資料夾相同**。
- 改動單套用前比對 `old` 和磁碟上現值；不同就標「這個值已經被改過（現在是 X）」，不套。

### 5.2 YAML 寫法（保留註解）

- 不加相依、不整檔重寫：用 `yaml.compose`（SafeLoader）拿到節點位置（`start_mark.index`／`end_mark.index`），**只替換那個純量的字面文字**；其他位元組不動。
- 欄位沒寫（用預設值）時要插入：區塊式 mapping 在最後一個鍵後面插一行同縮排的 `key: value`；流式 mapping（`{…}`）在 `}` 前插 `, key: value`（空的 `{}` 插 `key: value`）。清單（招式組，NW-2）同理分兩種寫法。
- 檢查：替換後重新 parse，結果必須等於「原 dict 只改那一個值」；`git diff` 只動到改的那幾行（測試用 `difflib` 斷言）。替換失敗就整張改動單不寫、說明哪一筆。
- 寫出時保留原檔的行尾（LF）與 UTF-8；數字照原樣寫（整數不加小數點）。

### 5.3 寫回與 git（安全措施）

寫回按鈕依序（任何一步失敗就停，已寫的檔從備份還原）：
1. 草稿驗證通過（5.5）。
2. **git 前置檢查**（在 `content/` 所在的 repo；`git` 用參數陣列、不經 shell）：目前分支是 `main`；沒有 `MERGE_HEAD`、`REBASE_HEAD`／`rebase-merge`、`CHERRY_PICK_HEAD`、`index.lock`（＝開發 PM 正在合併或別的程序在動 git，畫面說「開發 PM 正在合併，稍後再寫回」）；要改的檔 `git status --porcelain -- <檔>` 是乾淨的；`TRPG_CONTENT_DIR` 有設而且不在 repo 裡時，寫回關閉（只能模擬）。
3. 改動單的 `old` 全部等於磁碟現值（5.1）。
4. **備份**：要改的檔原樣複製到 `<save_dir>/tuning/backups/<時間>/`（只留最近 50 份）。
5. 寫檔（5.2）→ 再用 `load_checked_library()` 對**真的** `content/` 載一次＋`library_violations`；不過就還原備份。
6. `git add <這幾個檔>` → `git commit`（訊息第 0 節第 3 列；只 commit 這幾個檔，用 `git commit -- <檔>` 不帶到別的暫存）。commit 失敗就還原。
7. 回傳 commit hash 與「重開伺服器後生效」。

**和 agent 同時改內容檔**：agent 都在自己的 worktree 分支工作，不碰主資料夾；衝突只會出現在開發 PM 合併時。規則（寫進 `docs/開發PM交接.md`，由 PM 決定是否採用）：① 合併任何動到 `content/` 的分支前，`git log <分支起點>..main --grep '^tune'` 看使用者這段期間改了哪些檔；② 同一行衝突時**使用者的值優先**，不確定就問；③ 平衡相關段落的 agent 不改白名單欄位（0.0）；④ 開發 PM 合併期間工坊的寫回會被第 2 步擋下，不需要另外的鎖檔。

### 5.4 模擬

- **背景工作**：`POST /api/tuning/sims` 建立工作（回 `job_id`），伺服器內一條背景執行緒呼叫 `run_tasks`（程序池 `min(4, 核心數 − 2)`）；**一次只跑一個**（再按回 409「已有模擬在跑」）；可取消（關掉程序池）。前端每秒問一次 `GET /api/tuning/sims/{job_id}`（畫面輪詢可以；agent 的等待規則不適用於前端程式）。
- **規模上限**：單次 ≤ 160 場；超過就要使用者改小。畫面先顯示「N 場、預估 X 秒（依上一次實測的每場秒數）」。
- **改前快取**：改前結果以「目前 `content/` 的 `content_digest` ＋ 情境參數」為鍵存 `<save_dir>/tuning/sims/`；同鍵直接用。
- **NW-1 的情境：頭目戰**。把 `scripts/cb2e_sim.py` 的核心（建角、拉等級、`default_party`、`prepare_battle`、`_BossWatch` 歸屬規則）搬進 `src/trpg/sim/boss_probe.py`，腳本改成呼叫它（行為不變；用 `--only mist --seeds 1` 前後 JSON 逐字相同證明）。可選頭目（自動列出有 `phases` 的單位所在遭遇；至少 mist／ashen／rift 三個）、build（`content/sim/builds.yaml` 8 個，可勾選）、種子數。
- **指標**（依對象挑）：勝率、平均輪數、我方倒下率（每場倒下人數／人數）、頭目每階段每招「每回合施放率」寫成分子／分母（上手-內容 第四節第 4 點）、到達各階段的場數、勝負翻轉場數（同種子配對：改前贏改後輸、改前輸改後贏各幾場）。每個數字旁標場數；分母 < 30 時加「樣本小」。
- **確定性**：同參數同內容跑兩次，結果 JSON 逐字相同（不含耗時欄位）。

### 5.5 驗證

- 單欄：依白名單的型別（整數、‰、骰子字串、ID 清單）先轉型；再對草稿內容庫跑 `load_library` → `check_primitive_coverage` → `library_violations`（即 `trpg content check` 的同一套，`cli/main.py:437`）。
- 錯誤轉成中文、指到欄位：`ContentError` 帶檔案路徑，pydantic 錯誤帶欄位路徑；對不到欄位的放在頁首。
- 每次驗證約 1.2 秒以上：前端在停止輸入 0.5 秒後才送；後端同一時間只做一個驗證（後到的取代先到的）。
- 白名單提供「建議範圍」（例 `max_hp` 1～999）只作提示、不擋；擋的只有 schema 與跨檔檢查。

## 6. 受影響的既有功能

| 區塊 | 改／不改 | 說明 |
|---|---|---|
| 引擎 `trpg.engine` | 不改 | 守則 5 |
| `content/` 的資料 | 不改（工具本身）；之後使用者寫回才改 | NW 各段 agent 不改任何內容值；`content/tuning_fields.yaml` 是新檔 |
| `trpg.content` | 加 `tuning_fields.py`（白名單 schema 與檢查：每個路徑都對得到 schema 欄位、禁止表） | 不登記進 `KNOWN_CONTENT_FILES` |
| `trpg.cli.budget` | `library_violations` 搬到 `trpg.skillgen`（例 `skillgen/library_check.py`），`cli` re-export，行為不變 | `api` 不得匯入 `cli` |
| `trpg.sim` | 加 `boss_probe.py`（NW-1a）、`newbie_probe.py`（NW-3） | 腳本改成呼叫它，輸出逐字相同 |
| `scripts/cb2e_sim.py`、`ob6_newbie_sim.py` | 改成薄包裝 | 同上 |
| `trpg.api` | 新 `api/tuning/`（`routes.py`、`drafts.py`、`yaml_patch.py`、`writeback.py`、`git_guard.py`、`sim_jobs.py`、`schemas.py`）；`app.py` 的 `_include_routers` 加一段 | 前綴 `/api/tuning`（`/api/workshop` 已被技能工坊用） |
| OpenAPI 與前端型別 | `scripts/export_openapi.py` 重產、`client/src/api/schema.d.ts` 更新 | 照既有流程 |
| 前端 | 新 `client/src/tuning/`、`screens/TuningScreen.tsx`；`App.tsx` 加畫面；`StartScreen.tsx` 加鈕 | 只在 `?dev=1` |
| 測試的快照與固定種子 | 本段不動 | 使用者之後的 `tune:` 才會動，走第 0 節第 6 列收編 |
| 存檔、世界日誌 | 不改格式 | 0.0 |

## 7. 交付項目

### NW-1a 後端
- **A1** `content/tuning_fields.yaml`＋`trpg.content.tuning_fields`：第 3 節 NW-1 的欄位（中文標籤、型別、建議範圍、說明一句）；禁止表；載入檢查。
- **A2** 改動單、草稿（存、讀、列、刪、合併同欄位）、反向改動單（還原）。
- **A3** `yaml_patch.py`：字面替換與插入（5.2）。
- **A4** 草稿內容庫（複本、快取、套用、驗證、錯誤對到欄位）。
- **A5** 差異：改動單 → 「對象／欄位中文名／舊值／新值」表；另給 `git diff` 風格的文字（只含改到的行）。
- **A6** 寫回（5.3）：前置檢查、備份、寫檔、再驗證、commit、失敗還原。
- **A7** `trpg.sim.boss_probe`＋腳本薄包裝；模擬工作（5.4）。
- **A8** 端點與三道門（第 0 節第 2 列）；`library_violations` 搬家；OpenAPI 重產。
- **A9** 測試（第 8 節）、報告、上手筆記（新增 `docs/dev/上手-數值工坊.md`，或併入上手-內容並加一節，由 PM 定）。

端點（暫定）：`GET /api/tuning/objects?kind=unit`、`GET /api/tuning/objects/{kind}/{id}`（欄位、現值、標籤）、`GET|PUT|DELETE /api/tuning/drafts/{name}`、`POST /api/tuning/drafts/{name}/check`、`GET /api/tuning/drafts/{name}/diff`、`POST /api/tuning/drafts/{name}/revert/{commit}`（產生反向改動單）、`POST /api/tuning/drafts/{name}/apply`（寫回）、`POST /api/tuning/sims`、`GET /api/tuning/sims/{job_id}`、`DELETE /api/tuning/sims/{job_id}`、`GET /api/tuning/status`（能否寫回與原因、是否要重開伺服器）。

### NW-1b 前端
- **B1** 開發選單「數值工坊」鈕 → `TuningScreen`。
- **B2** 左欄對象清單（搜尋、分類：一般敵人／頭目）；右欄表單：欄位中文名、說明、現值、輸入框、「改過」標記、單欄還原；驗證錯誤紅字顯示在欄位下。
- **B3** 草稿列：存、換草稿、丟掉；差異頁。
- **B4** 模擬面板：情境（頭目、build 勾選、種子數）、「N 場、預估 X 秒」、開始／取消、進度；結果表改前／改後／差值三欄、翻轉場數、樣本小標記。
- **B5** 寫回確認彈窗（列改動、會 commit、要重開伺服器）；不能寫回時顯示原因（`/status`）。
- **B6** 還原：從寫回紀錄（`git log --grep '^tune'` 最近 20 筆，後端給）選一筆 → 產生反向草稿。
- **B7** vitest、截圖、報告。

### NW-2、NW-3、NW-4
第 4 節；各段開始前另寫細規格（白名單欄位逐條、模擬情境、指標），格式同本檔。

## 8. 行為一致測試

### NW-1a（pytest）
| # | 測什麼 |
|---|---|
| T-A1 | 白名單每個路徑在**所有** `content/units/*.yaml` 上都對得到 `UnitTemplate`／`BossPhase` 的欄位；禁止表的檔不能出現；改白名單加錯欄位會被擋 |
| T-A2 | `yaml_patch`：hypothesis 產生值，對全部單位檔的每個白名單欄位改一次 → 重新 parse 只差那一個值、其他位元組不變（`difflib` 只有那幾行）；流式／區塊式／空 `{}`／沒寫的欄位插入都測；註解保留 |
| T-A3 | 複本不套改動時三個 digest 和原資料夾相同；套一筆後 `content_digest` 變、`hash_ruleset` 依欄位是否進規則包而變 |
| T-A4 | 非法值擋下並帶中文原因與欄位路徑：`max_hp: 0`、`speed: -1`、`attributes.str: "abc"`、`trigger.permille: 1500`（若 schema 有上限）、`skills` 指到不存在的 ID（NW-2）；原因字串對到欄位 |
| T-A5 | 寫回在 `tmp_path` 的假 repo（`git init`、複製幾個單位檔）：成功 → 一筆 commit、訊息格式、只含那幾個檔；有 `MERGE_HEAD`／`index.lock`／不在 main／檔案有未 commit 改動／`old` 對不上 → 不寫、檔案不變、原因字串；commit 失敗（模擬）→ 從備份還原 |
| T-A6 | 反向改動單：寫回 → 還原 → 再寫回，檔案逐位元組回到原樣 |
| T-A7 | 三道門：`dev_mode=False` 時路由不存在（404）；沒有 `TRPG_TUNING=1` 時 404；帶 `CF-Connecting-IP`／`X-Forwarded-For`／`Forwarded` → 403 |
| T-A8 | `boss_probe`：同參數兩次結果相同；`scripts/cb2e_sim.py bosses --only mist --seeds 1` 搬家前後 JSON 逐字相同（報告附指令與雜湊） |
| T-A9 | 模擬工作：一次一個（第二個 409）、取消、改前快取命中不重跑、規模上限 |
| T-A10 | `library_violations` 搬家後 `trpg content check` 輸出逐字相同；`lint-imports` 通過；`tests/test_architecture.py` 通過 |

### NW-1b（vitest）
| # | 測什麼 |
|---|---|
| T-B1 | 表單由 `/objects/{kind}/{id}` 的欄位清單產生（不寫死欄位）；改值後「改過」標記與差異頁一致 |
| T-B2 | 後端回的驗證錯誤顯示在對應欄位；對不到欄位的顯示在頁首 |
| T-B3 | 模擬結果表：改前／改後／差值、分子分母、「樣本小」、翻轉場數 |
| T-B4 | 不能寫回時按鈕停用並顯示原因；寫回成功顯示 commit 與「重開伺服器」 |
| T-B5 | 不在 `?dev=1` 時看不到入口 |

## 9. 驗收條件

1. 第 8 節測試全過；改到的既有測試逐條寫「舊斷言 → 新斷言」。
2. 每次 commit：`ruff check`、`ruff format --check`、`mypy`、`lint-imports`、相關測試；NW-1b 另 `corepack pnpm -C client typecheck`、`test`、`build` 三個結束碼分開記，全 0 才交。
3. **實機走一遍**（1b，PM 或實作者在自己的 `trpg serve`，存檔與內容複本放暫存區、**`content/` 用 worktree 的、不碰主資料夾**）：改灰燼之心 `max_hp` 160→150 → 驗證通過 → 跑小模擬（mist 或 ashen，種子 1，冒煙規模）→ 看到改前改後表 → 寫回（worktree 分支上的一筆 `tune:` commit）→ 還原 → 檔案逐位元組回到原樣。再試一個非法值（`max_hp: 0`）看到中文原因。截圖 ≤ 8 張，存 `docs/phases/shots/nw1/`，jpg 80。
4. `trpg content check` 通過、一場紀錄＋重播通過（內容不變，雜湊應不變）。
5. 報告寫明：小模擬實測秒數（頭目 24 場、程序池 4）；寫回在 Windows 的實測（行尾、權限）；沒驗證的（例：開發 PM 合併進行中時寫回被擋的畫面只在假 repo 測過）。

## 10. 工作環境

- Windows、Git Bash。新 worktree 先 `uv sync --frozen`、`corepack pnpm -C client install --frozen-lockfile --offline`，之後 `UV_NO_SYNC=1`。
- 預覽埠（不用 8000、8001）：vite **5310～5314**、`trpg serve` **8157～8159**。vite 的 `/api` 寫死轉 8000，要接自己的 serve 另寫暫存設定檔、用完刪掉，不改 `vite.config.ts`。
- `trpg serve` 一律 `TRPG_SAVE_DIR=<暫存>`、`TRPG_TUNING=1`；寫回測試一律在 worktree 或 `tmp_path` 的 repo，**絕不對主資料夾 `F:\PythonProject\LLM-MMO-TRPG` 寫回或 commit**。
- 瀏覽器網址加 `?mute=1`；無頭 Chrome 加 `--mute-audio`。
- 結束前用自己記下的 PID 關掉 vite、`trpg serve`、無頭 Chrome；不用 `taskkill /IM`、`pkill`。
- 等背景程序用完成通知，不寫 `until`／`while` 輪詢。
- 不跑 `scripts/check.py`、不跑大型模擬；模擬只跑冒煙規模（每格 1 個種子）。不要 push。每完成一個交付項目就 commit（第一行英文，例 `feat(nw1a): yaml scalar patch keeping comments`），結尾帶 Co-Authored-By。
- agent 與子 agent 一律 Opus 5.5（Agent 工具 `model: "opus"`），prompt 寫明往下也一樣。

## 11. 開發中跑的測試

- NW-1a：`UV_NO_SYNC=1 uv run pytest -q tests/api/tuning tests/content/test_tuning_fields.py tests/sim/test_boss_probe.py tests/test_architecture.py tests/content/test_loader.py -n 8`；改 `library_violations` 時加 `tests/cli/test_skills_cli.py`。
- NW-1b：`corepack pnpm -C client exec vitest run src/tuning/ src/screens/ src/test/importCycles.test.ts`；交件前 typecheck／test／build。
- 交件前一次：`UV_NO_SYNC=1 uv run pytest -q tests/api/test_client_fixtures.py`（快照沒被動）、`tests/cli/test_output_snapshots.py -m slow`（`content check` 輸出不變）。

## 12. 報告格式

各段寫 `docs/phases/PhaseNW-1a報告.md` 等：
1. 做了什麼（交付逐條，附 commit）。
2. 驗收逐條（指令輸出為證；結束碼分開記）。
3. 改寫的既有測試（舊 → 新）；搬家的函式與「輸出逐字相同」的證據。
4. 實測數字：驗證一次幾秒、小模擬幾秒（場數、程序池）、複本建立幾秒。
5. 安全措施逐條對到第 5.3 節與第 0 節第 2 列，哪條是假 repo 測、哪條是實機測。
6. 請使用者試用的步驟（1b：開 `?dev=1` → 數值工坊 → …；要設 `TRPG_TUNING=1` 才看得到）。
7. **待 PM 決定**：最多 10 點，每點附出處；原型數值與解讀類照最保守做完再列。

## 附：起草時查到的風險與疑點

1. **註解保留**：沒有 round-trip YAML 套件，字面替換只對純量與簡單插入可靠；遇到錨點、多行字串、奇怪縮排就整張擋下並說明（不嘗試重寫整檔）。若使用者之後要改「結構」（加階段、加效果），不在本工具範圍。
2. **schema 匯入時讀固定資料夾的檔**（第 1 節「不受 `content_dir` 參數影響的讀檔」）：這些檔若被開放，草稿模擬會讀到磁碟上的舊值而不是草稿值——所以列在禁止表；NW-2 列技能欄位時要再確認範圍表（`skill_primitives.yaml`）不在可改之列。
3. **伺服器內跑程序池**：Windows spawn 每個行程要重新匯入 `trpg`（冒煙 1 個種子的腳本約數十秒，`PhaseBAL-20報告.md:146`「冒煙約 47 秒」含三支腳本）；1a 要量「第一次模擬的啟動秒數」並考慮讓程序池在工作之間保留（報告寫做法）。使用者自己跑模擬時會和 PM 的全量 `check.py` 搶 CPU，畫面加一句提示即可。
4. **使用者寫回會讓測試變紅**：parity 夾具、CLI 快照、固定種子 AI 測試（第 0 節第 6 列）。不收編的話 PM 的全量會一直紅；收編流程要寫進 `docs/開發PM交接.md`。
5. **`dev_mode` 預設開＋Tunnel**（第 0 節第 2 列）：只靠 `dev_mode` 會讓朋友能改內容檔，三道門缺一不可。
6. **遭遇的 `armor_mods` 與等級成長**：頭目實戰的護甲與血量不只看單位檔（`ashen_heart.yaml` 檔頭註解：護甲調整寫在 `encounters/ashen_waste.yaml`；`grow_enemy` 依等級長數值）。NW-1 的表單要在欄位旁顯示「實戰時另有：遭遇護甲 +N、等級成長」的唯讀提示，以免使用者以為改了沒用；可改要等 NW-3。
7. **單位檔頭的註解會過時**（例「數值是初值」）：工具不改註解；之後若要，另議。
