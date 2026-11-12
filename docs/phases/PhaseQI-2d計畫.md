# Phase QI-2d 計畫：Q 版技能圖示補圖（部件補圖＋7 個新道具＋19 招 `icon_prop`）

> 草稿（開發 PM 規格助手 2026-11-12，依據本機 main `32f45b11`，含美術分支 `ab40c49a`（合併 `0f3d77e3`）與玩法決定 #151 補充）。開發 PM 確認第 0 節後再定稿、派工。
> **前置：QI-2c（技能圖示接線，分支 `worktree-agent-a4e564366788363c3`，進行中）合併進 main 後才派 QI-2d。** 2c 會改 `client/src/render/qIcon/skills.ts`、`qIcon/weapons.ts`（加錘柄開關）與 `skillParts.ts`、`skillIcon.ts` 的接線；2d 從 2c 合併後的 main 開分支，所有「現行」都指 2c 合併後的狀態。
> 不切段：前端補圖約 150 行（逐行搬）、後端 1 個 YAML 加 7 列＋19 個技能檔各 1 行＋測試，一段做完。**前後端必須同一段合併**：只上後端的話，19 招的 `w:boot` 等在前端會被 `resolveGear` 退成直劍。

## 0. 待開發 PM 確認

「暫採」是規格目前寫進去的做法（每點都是最保守的選項）；確認後改掉對應列。

| # | 問題 | 出處 | 暫採（建議） |
|---|---|---|---|
| 1 | 使用者還沒看 11-12 補圖（美術 PM 交接「要交：使用者看圖」）；開發要不要等使用者看完才派 | `docs/美術PM交接.md` 17 行；審查第 2 版「交使用者時要講明」 | **不等**：美術審查已通過（`819a1f15`）、玩法 PM 已核可 19 招（#151 補充，`32f45b11`），照流程開發可以入檔。報告第 9 節照抄審查的「交使用者時要講明」9 條，使用者看圖若要改，美術改樣張後另排小段 |
| 2 | 修正技「改造對象」圓片要不要在本段接到遊戲畫面（派工只點名 `parts.ts`、`skills.ts`） | QI-2 第 0.0 節「改造對象暫留現行，待美術補圖」；第 4 批紀錄 13.6 | **接**：只換 `skillParts.ts::modifierTargetPart` 的 `draw`（改畫 `TARGET[targetOf(applies_to)]`），標籤、色環（白）、`note` 一字不改。不接的話補圖等於沒上線；改動只有一個函式 |
| 3 | `tag_summon` 的標籤現在顯示「summon技能」（`TAG_NAMES` 沒有 `summon`）；圖改畫小靈後標籤仍是英文 | `skillParts.ts` 1060 行；內容 6 個修正（`skill_summon_elite`、`skill_summon_swarm`）用 `skill_tags: [summon]` | **本段不改標籤**（規格外的文字變動），報告列出；要改只需 `TAG_NAMES` 加 `summon: "召喚"`，PM 決定後順手做 |
| 4 | 分擔傷害雙環：`parts.ts` 另存一份 `soulRings`（照樣張），還是 `status.ts` 的 `NEW.soul_link` 改呼叫它（第 4 批紀錄 13.6「兩處可以共用」） | 第 4 批紀錄 13.1 D、13.6；`status.ts` 94 行 | **`parts.ts` 加 `soulRings` 並 export，`status.ts` 不動**（QI-3b 可能同時在改 `status.ts`；兩份畫法逐筆相同由 T-D4 鎖住）。共用留給 QI-3b 或整理段 |
| 5 | `status.ts` 94 行 `soul_link` 的註解（「第 4 批效果分擔傷害是 Y 形分岔箭頭……待決」）過時 | `client/src/render/qIcon/status.ts` 94 行 | **不改**（同第 4 點，不碰 `status.ts`），報告列出 |
| 6 | 美術清單 1.3 節對煙霧彈、黏液、肩撞的文字還是第 1 版（麻繩十字、下垂黏滴、肩甲在胸前）；YAML 的 `name_zh` 照第③批紀錄 17.7 | `docs/art/技能圖示道具清單.md` 1.3；第③批紀錄 17.1、17.7 | **YAML 只寫 17.7 的 7 列**（`name_zh` 不受影響）；清單文字轉美術 PM 更新（開發不改 `docs/art/`）。同時請美術 PM 把清單第 3 節「等 `skill_icon_props.yaml` 加了值才算進清單」改成已入檔 |
| 7 | QI-2b 的暫時資料 `client/src/dev/fixtures/qi2bTempArt.json`：2c 預定刪掉；若 2c 合併後還在 | `PhaseQI-2b報告.md` 待決 1；`開發PM交接.md` 48 行 | **還在就不更新它**（開發頁與 T-B1 優先讀 fixture 的 `art`），報告註明；不在本段刪（2c 的範圍） |
| 8 | 舊存檔 | 使用者原話（派工轉述）：「存檔都可以刪除」 | **不做相容**：三個雜湊都會變（第 8.2 節），進行中的一輪從頭開始、世界日誌標成不能重播；不加版號、不寫遷移 |
| 9 | 預覽埠 | QI-2 第 3 節（2b 用 5270～5274、8131～8132；2c 用 5275～5279、8133～8135） | **vite 5280～5284、靜態伺服器 8136～8137、`trpg serve` 8138～8139**；不用 8000、8001、5195 |

## 1. 依據與已定事項

| # | 內容 | 出處 |
|---|---|---|
| P1 | 7 個新道具 `w:flask`、`w:smoke_bomb`、`w:roar`、`w:boot`、`w:shoulder`、`w:fang`、`w:slime`：掛在 `w:` 前綴、`group: neutral`、不寫 `weapon_class`（不限大類）；**沒有新前綴**，`ICON_PROP_PATTERN` 不改 | 第③批紀錄 17.7；道具清單 1.3；#151 補充 |
| P2 | 19 招照道具清單 2.4 入檔（8 招 `w:fist` 改值、11 招新填）；拖地摔 `skill_prone_drag` 留 `w:fist`；19 招都是 `content/skills/` 手寫技能，沒有化身入口、沒有 `wielding_weapon` 招（助手 grep：19 檔 `enter_form`／`wielding_weapon` 都是 0） | #151 補充（`docs/玩法決定紀錄.md` 282 行起）；06 6.36 |
| P3 | 推導表 `content/skill_icon_art.yaml` **不改**：新道具不需要新規則；19 招換道具後出手、記號、染色都和原本相同，只有 `art.prop` 變（第 6 節） | 第③批紀錄 17.2 末條、17.7「推導：不用改」 |
| P4 | 圖以樣張為準：主圖 `docs/art/sample/qIconsSkills.js`（`379812dd` 第 2 版）、部件 `docs/art/sample/qIconsParts.js`（`7b6db8dc`）；審查通過 `819a1f15` | 審查檔 `docs/art/Q版小圖示-11-12補道具與部件-審查.md` |
| P5 | 每段合併前跑與改動相關的 slow 測試；雜湊、快照**不得整批重產**，每項變動要證明來自本段 | QI-2 第 0.0 節末條（開發 PM 定稿） |
| P6 | 截圖每段 ≤ 10 張；真 1 倍／最近鄰特寫可用 PNG（單張 ≤ 300 KB），其他 jpg 80 | QI-2 D7；使用者 11-12 選 A |

## 2. 目標與範圍外

**目標**：
1. 前端 `qIcon/skills.ts` 補 7 個新道具（`THINGS`）與它們的擺位、換色（照樣張 `20a6fd39`→`379812dd` 的 diff 逐行搬）。
2. 前端 `qIcon/parts.ts` 補第④批 11-12 補圖（`7b6db8dc`）：改造對象 `TARGET` 13 個＋`targetOf`、分擔傷害改雙環、`form_upkeep_permille`／`summon_limit_delta` 照數值正負畫；並把改造對象接到組裝算式（第 0 節第 2 列）。
3. 後端允許清單加 7 列、19 招填 `icon_prop`，相關測試的數字照新內容改（不放寬）。
4. 遊戲端與樣張逐像素比對：改到的圖 0 像素差；沒改到的圖和 2c 合併後的基準相同。

**範圍外**：審查的「可修」各點（黏液換色、重踏齒輪位置、維持消耗沙漏放大、號角 18px、肩撞 24px 的 V 再退）；`skill_icon_art.yaml` 的任何改動；`status.ts`（第 0 節第 4、5 列）；`TAG_NAMES` 標籤（第 0 節第 3 列）；聖水、毒霧彈、毒霧、煙幕箭等 2.4 末段「沒有改的相關招」；`docs/art/` 的任何檔（截圖除外）；`qIcon/core.ts`、`qIcon/weapons.ts`（需要時只加 export 並列報告）。

## 3. 工作環境

- 先 `git merge --ff-only main`，確認含 QI-2c 的合併 commit（`git log --oneline | grep -i qi2c`）；沒有就停下回報。
- Windows、Git Bash。Python 一律 `uv run python`；前端 `corepack pnpm -C client …`。新 worktree 第一次：`uv sync --frozen`、`corepack pnpm -C client install --frozen-lockfile --offline`；之後 Python 指令加 `UV_NO_SYNC=1`。
- 預覽埠照第 0 節第 9 列。瀏覽器網址一律加 `?mute=1`；無頭 Chrome 加 `--mute-audio`、`--force-device-scale-factor=1`；**和樣張逐像素比對與 `fitK` 一樣用 `--disable-gpu`**（上手-前端第四節第 37 點）。
- vite 的 `/api` 寫死轉 8000，要接自己的 `trpg serve` 另寫暫存設定檔、用完刪掉，不改 `vite.config.ts`。存檔放暫存區（`TRPG_SAVE_DIR`）。
- 結束前用自己記下的 PID 關掉 vite、`trpg serve`、靜態伺服器與無頭 Chrome；不用 `taskkill /IM`、`pkill`。等背景程序用完成通知，不寫 `until`／`while` 輪詢迴圈。
- agent 與子 agent 一律 Opus 5.5（Agent 工具 `model: "opus"`），prompt 寫明往下也一樣。
- 只跑相關測試（第 9 節）；不跑 `scripts/check.py`、不跑模擬。不要 push。每完成一個交付項目就 commit（第一行英文，例 `feat(qi2d): seven neutral skill icon props`），結尾帶 Co-Authored-By。
- 要讀的：`CLAUDE.md`；`docs/dev/上手-內容資料與模擬.md`（第一、二節）；`docs/dev/上手-前端戰鬥畫面與動畫.md`（第一節、第四節第 30 點以後、第五、六節）；審查檔全文；第③批紀錄第 17 節、第④批紀錄第 13 節；道具清單 1.3、2.4；`PhaseQI-2b報告.md` 第 4、6 節（逐像素比對做法、和樣張不同處）；`PhaseQI-2c報告.md`（接線方式、比對基準）；`PhaseQI-2a報告.md` 第 2、4 節（測試與雜湊歸因寫法）。

## 4. 受影響的既有功能

| 區塊 | 受影響的 | 改／不改 | 理由 |
|---|---|---|---|
| 引擎、結算、重播 | 無：`icon_prop` 不進結算（06 6.36）；但規則包內嵌技能全文，`hash_ruleset` 會變 | 不改 | IP-1 已證明重播照樣通過；`test_icon_prop_battle_ip1.py` 參數化會自動從 36 招擴到 47 招 |
| 內容 | `content/skill_icon_props.yaml` +7 列（57 → 64 值）；`content/skills/` 19 檔各改／加 1 行；`trpg content check` 仍 660 個檔、402 個技能 | 改 | P1、P2 |
| 推導表 | `content/skill_icon_art.yaml` | 不改 | P3 |
| 推導結果 | 19 招 `SkillIcon.icon_prop` 與 `art.prop` 變；`motion`／`act`／`tint`／`spark`／`elements` 不變（第 6 節） | — | 第 6 節表；T-D9 鎖住 |
| API／型別 | `openapi.json`、`schema.d.ts` 不變（沒有新欄位） | 不改 | `export_openapi.py` → `gen:api` 要 0 差異 |
| 衍生快照 | `client/src/render/fixtures/skill_icons.json`（19 招）、`client/src/ui/fixtures/skillCards.json`（`skill_gale_kick` 一張） | 重產後逐項比對 | 第 8.2 節 |
| CLI 快照 | `skills_list`、`skills_show_all` 不含圖示 | 不改 | 跑 slow 確認 |
| 存檔與 digest | `hash_ruleset`、`ruleset_hash`、`content_digest` 都變 | 不相容（第 0 節第 8 列） | 第 8.2 節歸因 |
| 主圖畫法 | `qIcon/skills.ts`：`THINGS`、`LIQUID`、`hornPt`／`hornSide`、`dashV`、`propOf` 的 `thing` 分支、`info()` 的 `!P.thing` 與 `noTail`、`MOTION.shot` 的 `noTail`、`TIP_KINDS`／`HEAD_KINDS` 新成員、`def()` 的瓶液體色、`ramDash` 擺位與換色、黏液配右上記號的擺位與 `markK`、`list()` 的 7 列、`return` 加 `THINGS` | 改 | 第③批紀錄 17.2、17.7、17.8 |
| 部件畫法 | `qIcon/parts.ts`：`minus`、`soulRings`、`EFFECT.redirect_damage`、`CHANGE.summon_limit_delta`、`CHANGE.form_upkeep_permille`、`bowArrow`、`cardFan`、`TARGET` 13、`TARGET_TAG`、`targetOf`、`CATS`／`CAT_ZH` 加 `target`（放最後）、`RING.target` | 改 | 第④批紀錄 13.1、13.6 |
| 組裝算式 | `render/skillParts.ts::modifierTargetPart` 的 `draw`；標籤、色環、`note` 不變 | 改（第 0 節第 2 列） | 第④批紀錄 13.6 |
| 狀態圖示 | `qIcon/status.ts`（`soul_link`） | 不改 | 第 0 節第 4、5 列 |
| 開發頁 | `dev/skillIconGallery.ts`：`set=props` 會多 7 列（讀 `list()`）；加 `set=target`、`set=qi2d` | 改 | 截圖與比對要用 |
| 既有測試 | 後端 3 檔、前端 `qIconSkills.test.ts` 的數字與分支（第 7.3 節） | 改寫（不放寬） | 內容與表變了 |

## 5. 交付項目

### 後端

- **B1 允許清單**：`content/skill_icon_props.yaml` 在 `w:kunai` 後面照第③批紀錄 17.7 的順序加 7 列：
  `{id: "w:flask", name_zh: 瓶, group: neutral}`、`{id: "w:smoke_bomb", name_zh: 煙霧彈, group: neutral}`、`{id: "w:roar", name_zh: 吼聲, group: neutral}`、`{id: "w:boot", name_zh: 腳／靴, group: neutral}`、`{id: "w:shoulder", name_zh: 肩撞, group: neutral}`、`{id: "w:fang", name_zh: 獠牙, group: neutral}`、`{id: "w:slime", name_zh: 黏液, group: neutral}`。
  檔頭「57 個值」改 64、分節註解「1.3 中性道具（2）」改「（2＋11-12 補 7）」。不寫 `weapon_class`。
- **B2 19 招**：照第 6 節表。8 招把 `icon_prop: "w:fist"` 改成新值；11 招在 `weapon_req` 下一行插 `icon_prop: "<值>"`（雙引號，同 IP-1）。不動其他行；`skill_prone_drag`、`skill_decoy_swap`、`skill_static_palm`、`skill_armor_break_combo`、`skill_form_pounce` 維持 `w:fist`。
- **B3 快照**：`UV_NO_SYNC=1 uv run python -m tests.narrative.icon_fixture`、`UV_NO_SYNC=1 uv run python scripts/export_client_fixtures.py`、`UV_NO_SYNC=1 uv run python scripts/export_openapi.py` → `corepack pnpm -C client gen:api`；只留第 8.2 節列的預期變動（寫腳本比對，結果進報告）。
- **B4 測試**：第 7.1 節新測試＋第 7.3 節既有測試改寫。

### 前端

- **F1 主圖**：`client/src/render/qIcon/skills.ts` 照 `git diff 20a6fd39~1 379812dd -- docs/art/sample/qIconsSkills.js` 逐行搬（第 4 節「主圖畫法」列）。靴的 `M.leather` 用 `core.ts` 的 `M`（和 2b 一樣，`M` 已對到 `material.ts`）；`propOf` 的 `THINGS` 分支要排在武器解析之前（否則 `resolveGear` 退直劍）。在檔頭「和樣張不同」清單補上本段新增的型別調整。
- **F2 部件**：`client/src/render/qIcon/parts.ts` 照 `git show 7b6db8dc -- docs/art/sample/qIconsParts.js` 逐行搬（第 4 節「部件畫法」列）。`TARGET.tag_shout` 呼叫 `QS.THINGS.roar`（`parts.ts` 已 `import * as QS from "./skills"`）。`summon_limit_delta` 讀 `opt.value`（沒有時當 +1，指紋不變）；`form_upkeep_permille` 走 `up()`（`signArrow` 照正負）。`soulRings` export（第 0 節第 4 列）。
- **F3 改造對象接線**：`render/skillParts.ts::modifierTargetPart` 的 `draw` 改畫 Q 版 `TARGET[targetOf(applies)]`，用 2c 接其他部件的同一種做法（圓底、白色色環 `#ffffff`、圖樣＝直徑 78%、`blit` 對齊）；`label`、`note`、`color`、`cat`、`key` 一字不改。舊的 `swordGlyph`、`rangedGlyph`（`add_tags`、`range_delta` 還在用的不刪）、`TAG_TARGET` 若只剩這裡用，照 QI-2 第 0 節第 11 列不刪、報告列出。
- **F4 開發頁**：`dev/skillIconGallery.ts` 加 `set=target`（13 個改造對象＋現行對照）、`set=qi2d`（19 招 40／28／24、本段改過的 4 個部件與兩種正負），檔頭參數說明同步。
- **F5 測試**：第 7.2 節新測試＋第 7.3 節既有測試改寫。
- **F6 逐像素比對與截圖**：第 8.3、8.4 節。

### 文件

- **R1 報告** `docs/phases/PhaseQI-2d報告.md`（第 10 節）。
- **R2 上手筆記**：`docs/dev/上手-內容資料與模擬.md`（第一節表「57 個值」→ 64；第二節第 8 點補「新道具 7 個不限大類」）；`docs/dev/上手-前端戰鬥畫面與動畫.md`（第一節 `skills.ts`／`parts.ts` 那列補 `THINGS`、`TARGET`／`targetOf`、`soulRings`；第四節踩到的坑；第五節測試表加新測試檔）。

## 6. 19 招的推導結果變化（助手讀 main 的 `skill_icons.json` 實查）

改前＝本機 main（2c 合併前；2c 不改後端，預期相同）的 `art`。**改後只有 `prop` 變**；`motion`／`act`／`tint`／`spark` 必須和改前逐欄相同（第③批紀錄 17.2：`derive_motion` 對新道具近戰單體仍是 `swing`、其餘看形狀，黏液射程 3 仍是 `shot`）。

| 技能 | 中文 | `weapon_req` | `icon_prop` 改前 → 改後 | `art` 改前（prop｜motion｜act｜tint） | `art.prop` 改後 |
|---|---|---|---|---|---|
| `skill_trample` | 踩踏 | melee | `w:fist` → `w:boot` | `w:fist`｜swing｜combo｜impact | `w:boot` |
| `skill_prone_kick` | 踢翻 | melee | `w:fist` → `w:boot` | `w:fist`｜swing｜push｜— | `w:boot` |
| `skill_gale_kick` | 颶風踢 | melee | `w:fist` → `w:boot` | `w:fist`｜swing｜push｜— | `w:boot` |
| `skill_leap_slam` | 躍擊震地 | melee | `w:fist` → `w:boot` | `w:fist`｜place｜dash｜— | `w:boot` |
| `skill_prone_mark_strike` | 追印絆擊 | melee | （無）→ `w:boot` | `w:sword`｜swing｜knockdown｜— | `w:boot` |
| `skill_heavy_stomp` | 重踏 | melee | （無）→ `w:boot` | `w:fist`｜aura｜modify｜impact | `w:boot` |
| `skill_battering_ram` | 破城衝撞 | melee | `w:fist` → `w:shoulder` | `w:fist`｜swing｜push｜— | `w:shoulder` |
| `skill_bull_rush` | 蠻牛衝陣 | melee | `w:fist` → `w:shoulder` | `w:fist`｜place｜dash｜— | `w:shoulder` |
| `skill_tiger_charge` | 衝鋒撞擊 | melee | `w:fist` → `w:shoulder` | `w:fist`｜swing｜dash｜— | `w:shoulder` |
| `skill_quake_topple` | 震地推倒 | melee | `w:fist` → `w:shoulder` | `w:fist`｜swing｜knockdown｜— | `w:shoulder` |
| `skill_oil_flask` | 燈油瓶 | any | （無）→ `w:flask` | `el:earth`｜area｜surface｜earth | `w:flask` |
| `skill_splash_flask` | 潑水瓶 | any | （無）→ `w:flask` | `el:water`｜area｜slow｜— | `w:flask` |
| `skill_smoke_bomb` | 煙霧彈 | ranged | （無）→ `w:smoke_bomb` | `w:bow`｜area｜surface｜steel | `w:smoke_bomb` |
| `skill_gear_smoke_bomb` | 煙霧彈（裝備） | any | （無）→ `w:smoke_bomb` | `none`｜area｜surface｜steel | `w:smoke_bomb` |
| `skill_lingering_roar` | 震懾餘波 | any | （無）→ `w:roar` | `w:tome/book`｜aura｜modify｜wind | `w:roar` |
| `skill_taunting_roar` | 挑釁怒吼 | any | （無）→ `w:roar` | `none`｜spin｜curse｜fire | `w:roar` |
| `skill_wild_roar` | 野性怒吼 | any | （無）→ `w:roar` | `none`｜spin｜curse｜steel | `w:roar` |
| `skill_venom_gore` | 毒牙頂撞（敵人專用） | melee | （無）→ `w:fang` | `w:sword`｜swing｜dot｜poison | `w:fang` |
| `skill_slime_glob` | 黏液（敵人專用） | any | （無）→ `w:slime` | `el:earth`｜shot｜slow｜— | `w:slime` |

`spark` 19 招改前都是 `null`。其他 383 招的 `art` 與 `icon_prop` 逐欄不變。
**樣張對應的 17 個長相**（第③批紀錄 17.6；兩招煙霧彈同圖、踢翻與颶風踢同圖）。樣張的 `?part=add` 是「推導結果換掉道具」，和後端的 `art` 一致（T-A2 已逐招比 `derive_motion(原文, icon_prop)`）。

## 7. 行為一致測試

資料一律用實際內容與重產後的快照，不手寫清單（第 6 節的 19 招期望值例外：它是美術清單 2.4 的資料版，測試檔頭註明出處）。

### 7.1 後端（pytest，新檔 `tests/content/test_icon_prop_qi2d.py`）

| # | 測什麼 |
|---|---|
| T-D1 | **允許清單 7 列**：7 個 ID 都在、`group == "neutral"`、`weapon_class is None`、`name_zh` 等於 17.7；ID 符合 `ICON_PROP_PATTERN`（沒有新前綴） |
| T-D2 | **19 招的值**：每招 `library.skills[id].icon_prop` 等於第 6 節「改後」；`skill_prone_drag` 等 5 招仍是 `w:fist`；整份內容裡填 `w:fist` 的恰好 5 招、填新 7 值的恰好 19 招 |
| T-D3 | **不限大類**：7 個新值各配 `weapon_req` 為 `melee`／`ranged`／`focus`／`any` 的實際技能（`model_copy(update={"icon_prop": v})`），`icon_prop_problems` 都回空（期望值由 06 6.36「中性道具不限大類」推得） |
| T-D9 | **推導只換道具**：19 招的 `skill_icon(skill, art=icon_art_rules(library)).art`：`prop` 等於新值；把 `icon_prop` 換回改前值（`model_copy`）重算的 `motion`／`act`／`tint`／`spark`／`elements` 與改後逐欄相同，且等於第 6 節「改前」欄（`prop` 以外） |
| T-D10 | **戰鬥不受影響**：沿用 `test_icon_prop_battle_ip1.py`（參數化自動含新 11 招）；另確認新 11 招都在參數清單內 |

### 7.2 前端（vitest，新檔 `client/src/render/qIcon/qIconQi2d.test.ts`，假畫布用 `test/fakeCanvas.ts`）

| # | 測什麼 |
|---|---|
| T-D4 | **雙環和狀態「靈魂連結」同一個畫法**：`parts.ts` 的 `EFFECT.redirect_damage` 與 `status.ts` 的 `soul_link` 在 18（tiny）、30 下的假畫布呼叫紀錄逐筆相同（`halo` 另建畫布，要看全域 `log`，上手-前端第四節第 33 點） |
| T-D5 | **正負**：`summon_limit_delta` value −1 只畫橫槓（`minus`，沒有直槓那筆 `rr`），+1 與沒有 value 畫加號（和本段前的呼叫紀錄相同＝指紋不變）；`form_upkeep_permille` −500 箭頭朝下青色、+500 朝上橘黃，兩者都有右下沙漏；用 `skill_icons.json` 裡 `skill_summon_elite`、`skill_summon_swarm`、`skill_form_mastery` 的實際 `changes` 再各跑一次 |
| T-D6 | **`targetOf` 判斷順序**：13 個代碼各一組合成 `applies_to`＋`skill_icons.json` 全部修正技的實際 `modifier.applies_to`：結果和「本段前 `modifierTargetPart` 的分支」一致（`all_skills`、`all_attacks`、`actions` 含 `attack`、`skill_tags` 第一個、其他 `actions`、預設）；`weapon_skills: true` → `default`；`skill_heavy_stomp` → `tag_push`、`skill_lingering_roar` → `tag_shout`、召喚兩招 → `tag_summon` |
| T-D7 | **改造對象接上了、文字沒動**：`skill_icons.json` 全部修正技的 `modifierTargetPart(applies_to)`：`label`、`note`、`color`、`cat`、`key` 和本段前逐字相同（先在 2c 合併後的 main 錄一份基準存在測試檔）；`draw` 的假畫布紀錄等於 `paint("target", targetOf(...))` |
| T-D8 | **新道具**：7 個 `THINGS` 都在；`def({prop: "w:<id>", …})` 走 `thing` 分支（`meta` 不是直劍退回）；`info().weapon` 為 false；黏液射出沒有彗尾（`noTail`）；瓶配地面效果時記號換液體色（`earth`＝琥珀）；肩撞配 `dash` 用 `dashV([dim, soft])`、`markK` 0.72 |
| T-D11 | **對齊、確定性、不丟例外**：19 招 × 24／28／40／48(mid)／56(mid)／96(full) × `res` 1、2，13 個改造對象＋4 個改過的部件 × 18／30 × `res` 1、2：`blit` 左上角乘 `res` 是整數、沒有縮放貼法；畫兩次呼叫紀錄相同 |

### 7.3 既有測試改寫（舊斷言 → 新斷言，逐條寫進報告，不放寬）

| 檔 | 舊 | 新 |
|---|---|---|
| `tests/content/test_icon_prop_ip1.py::test_allow_list_has_the_57_values_of_the_art_list` | 57 個值；`neutral: 2` | 64 個值；`neutral: 9`（函式名與 docstring 照改，出處補第③批紀錄 17.7） |
| 同檔 `test_every_filled_skill_is_in_the_list_and_matches_its_weapon_class` | `len(filled) == 36` | `== 47`（36＋新填 11；註明 #151 補充） |
| `tests/narrative/test_skill_icon_art_qi2a.py` 348 行 | `filled == 36` | `== 47` |
| 同檔 `PROP_ROWS` 的 `("skill_lingering_roar", "3", "w:tome/book")` | 實際技能走修正技「其餘」列 | 它填了 `w:roar` 後走 2b 列；**這一列沒有別的實際技能**，改成合成：`skill_lingering_roar` `model_copy(update={"icon_prop": None})`，標「合成」；另加一列 `("skill_lingering_roar", "2b", "w:roar")`。T-A5「改變出手的恰好 6 招」不改（19 招出手不變，若失敗就停下回報） |
| 同檔其他實例 | — | 實作者用腳本確認 T-A1 其他實例沒有一招在 19 招裡（助手 grep 只找到上面這一列） |
| `tests/content/test_icon_prop_d4_qi2a.py` 75 行 docstring | 「36 招有填」 | 「47 招有填」（斷言不變） |
| `client/src/render/qIcon/qIconSkills.test.ts` T-B1（40～51 行） | `w:` 除了 `kunai` 都要是第 1 批武器 | `w:` 是 `THINGS` 的 7 個 → `has(QS.THINGS, rest)` 且 `def` 走 `thing` 分支；其餘照舊 |
| 同檔 T-B2 | 12 類數量 | 加 `target: 13`（出處第④批紀錄 13.1） |
| 同檔 T-B5 | 有箭頭的鍵 9 個；`summon_limit_delta` 固定加號 | 10 個（加 `form_upkeep_permille`）；`summon_limit_delta` 照正負（QI-2b 報告待決 3 由第④批紀錄 13.1 E 定案） |
| `client/src/render/skillIcon.test.ts` 112 行 `modifierTargetPart({ mystery: true })` 等 | 舊畫法 | 2c 改寫後若仍斷言舊 `draw`，改成 Q 版斷言；標籤斷言不動 |

## 8. 驗收條件

### 8.1 共通

1. 第 7 節測試全過；改寫的既有測試在報告逐條說明。
2. 後端：`UV_NO_SYNC=1 uv run trpg content check` 0（660 個檔、402 個技能）；`ruff check .`、`ruff format --check .`、`mypy`、`lint-imports` 0；`trpg battle --map open_plain --seed 7 --log-json <暫存>/b.json` ＋ `trpg battle replay` 通過。
3. **合併前 slow**（結束碼分開記）：`tests/skillgen/`、`tests/narrative/`、`tests/content/`、`tests/api/`（含 slow，`-m "not llm"`，`-n 8`）、`tests/cli/test_output_snapshots.py -m slow`。已知的既有失敗（例 QI-2a 報告的 `test_refactor_parity.py`、`test_proposal_l8.py`，若仍在）要在起點 commit 用同一個 venv 跑出**逐條相同**的失敗清單，才算與本段無關。
4. 前端：`corepack pnpm -C client typecheck`、`corepack pnpm -C client test`、`corepack pnpm -C client build` 三個結束碼都是 0；`render/inkDollSnapshot.test.ts`、`render/creaturePose.test.ts` 快照沒變。
5. `git diff --stat <起點>..HEAD`：只動第 4 節列「改」的檔、第 7 節的測試、快照（第 8.2 節）、報告與上手筆記、`docs/art/shots/qi2/2d-*`；`qIcon/core.ts`、`weapons.ts`、`status.ts`、`content/skill_icon_art.yaml` 沒動。

### 8.2 雜湊與快照（不得整批重產；每項要證明來自本段）

| 項目 | 預期 | 證明方式 |
|---|---|---|
| `client/src/render/fixtures/skill_icons.json` | 只有 `skills` 裡第 6 節 19 招變：`icon_prop`（8 招改值、11 招新增）與 `art.prop`；`random` 50、`workshop` 示範逐筆不變 | 腳本：HEAD 版與重產版逐招比，列出變動的（招、欄位、舊值、新值），必須恰好是第 6 節表；再把重產版那 19 招的兩欄換回舊值，要和 HEAD 版完全相同 |
| `client/src/ui/fixtures/skillCards.json` | 只有 `skill_gale_kick` 卡的 `icon.icon_prop`（`w:fist` → `w:boot`）與 `icon.art.prop` | 同上 |
| `unitDolls.json`、`raceLooks.json`、`glossary.json` | 不變 | `git diff --stat` 為空 |
| `client/openapi.json`、`client/src/api/schema.d.ts` | 不變 | `export_openapi.py` → `pnpm gen:api` 後 `git diff --stat` 為空 |
| CLI 快照 | 不變、不重產 | slow 全過；有不符的鍵要在起點 commit 跑出同樣的不符才算既有，且不得重產 |
| `hash_ruleset(library.ruleset)` | 變（規則包內嵌技能全文，19 檔變） | 起點 commit 的 `content/`（`git archive` 匯出）配**本段的 `src/`** 載入 → 等於起點值（證明程式沒動雜湊）；本段的內容庫把 19 招 `icon_prop` 換回起點值（`model_copy`，重建 `Ruleset`）→ 回到起點值 |
| `ruleset_hash(library)`、`content_digest(library)` | 變（技能檔＋`skill_icon_props.yaml` 都在 `library.files`） | 同上，用起點 commit 的 `content/` 配本段 `src/` 重算 → 等於起點值；並列出 `git diff --stat <起點>..HEAD -- content/` 恰好 20 個檔（19 技能＋1 允許清單） |

報告照 `PhaseQI-2a報告.md` 第 4 節的表寫改前／改後／歸因。版號（`LOG_FORMAT`、`WORLD_RULES_VERSION`、`CHAR_FORMAT`）不動。

### 8.3 和樣張逐像素比對（`PhaseQI-2b報告.md` 第 4 節的做法；`--disable-gpu`）

| 比對 | 組數 | 要求 |
|---|---|---|
| 19 招主圖（用重產後 fixture 的 `art`；樣張 `QIconsSkills.canvas` 用同一份 `look`）× 24、28、40 × `res` 1、2 | 114 | 0 像素差 |
| 19 招組裝 mid 56、mid 48、full 96 × `res` 1、2 | 114 | 0 像素差 |
| `target` 13 個、`effect:redirect_damage`、`change:form_upkeep_permille`（−500、+500）、`change:summon_limit_delta`（−1、+1）× 18 `res` 1、18 `res` 2、30 `res` 2（`chipCanvas`） | 54 | 0 像素差 |
| `skill_summon_elite`、`skill_summon_swarm`、`skill_form_mastery`、`skill_soul_bond` 的 full 96 × `res` 1、2 | 8 | 0 像素差 |
| **回歸**：2b 的全量比對（主圖 402 × 24／28／40、組裝 402 × 三級、部件 × 18／30、卡片小圖）× `res` 1、2 | 約 5600 | 不同的組數與原因**和 QI-2c 報告的基準相同**（2b 時是錘 3 招 × 12 組，2c 加錘柄開關後以 2c 報告為準）；本段不得新增不同的組 |

樣張那邊要先套 2b 的前處理：`M`／`MAT` 換成 `material.ts` 的色、`window.AssembledIcon = { framePath }`；錘柄照 2c 報告的做法。寫出各列不同的組數、最大像素數與原因。

### 8.4 截圖（≤ 10 張，放 `docs/art/shots/qi2/2d-*`）

`--force-device-scale-factor=1`；真 1 倍／最近鄰特寫 PNG（≤ 300 KB），其他 jpg 80；只拍改到的。

| 檔（暫定） | 內容 | 格式 |
|---|---|---|
| `2d-01-props7-40-28-24.jpg` | 7 個新道具主圖（每個道具第一招）40／28／24 DPR 2，旁邊樣張同圖 | jpg |
| `2d-02-skills19-dpr2.jpg` | 19 招 40／28／24 DPR 2，每招標道具值；上排 2c 後（`w:fist`、劍、岩石…）｜下排 2d | jpg |
| `2d-03-skills19-true1x-x4.png` | 19 招 24、28 真 1 倍，最近鄰 ×4 | PNG |
| `2d-04-target13-30-18.png` | 改造對象 13 個：30 DPR 2、18 真 1 倍 ×6；左欄現行（2c 後）對照 | PNG |
| `2d-05-redirect-sign-x6.png` | 分擔傷害雙環（對狀態卡「靈魂連結」20）、形態維持 ±、召喚物上限 ±：30 DPR 2、18 真 1 倍 ×6 | PNG |
| `2d-06-full96-modifiers.jpg` | 精英召喚、群召、化形專精、魂結的 full 96 DPR 2（看得到改造對象、雙環、兩種箭頭） | jpg |
| `2d-07-game-*.jpg`（1～2 張） | 實機：技能卡或工坊組裝算式一張（含改造對象）、技能列或配招含新道具的招一張；實機到不了用開發頁畫並列「實機未看」 | jpg |

## 9. 開發中跑的測試

- 後端：`UV_NO_SYNC=1 uv run pytest -q -n 8 tests/content/test_icon_prop_qi2d.py tests/content/test_icon_prop_ip1.py tests/content/test_icon_prop_battle_ip1.py tests/content/test_icon_prop_d4_qi2a.py tests/content/test_icon_art_battle_qi2a.py tests/narrative/test_skill_icon_art_qi2a.py tests/narrative/test_skill_icon.py tests/api/test_icon_prop_api_ip1.py tests/api/test_icon_art_api_qi2a.py tests/api/test_client_fixtures.py tests/api/test_openapi_snapshot.py tests/skillgen/test_icon_prop_drop_ip1.py tests/skillgen/test_enemy_only.py tests/skillgen/test_proposal.py tests/test_architecture.py`；交件前跑第 8.1 節第 3 點的 slow 一次。
- 前端：`corepack pnpm -C client exec vitest run src/render/qIcon/ src/render/skillIcon.test.ts src/ui/skillCard.test.ts src/world/panelIcons.test.ts src/world/range.test.ts src/test/importCycles.test.ts`。
- 每次 commit 前：`corepack pnpm -C client typecheck`；改到 Python 時 `ruff check`、`ruff format --check`、`mypy`、`lint-imports`。

## 10. 報告格式（`docs/phases/PhaseQI-2d報告.md`）

1. 做了什麼（交付項目逐條，附 commit）。
2. 驗收逐條（指令與結束碼分開記；測試名稱）。
3. 改寫的既有測試（第 7.3 節逐條舊 → 新）。
4. 快照與雜湊（第 8.2 節表，含證明方式的實際輸出）；請使用者重開伺服器檢查的重點：**內容有變，進行中的一輪會從頭開始、世界日誌標成不能重播**（使用者已說存檔可以刪）；技能列、技能卡的 19 招換新道具；修正技卡片組裝算式第一格換 Q 版改造對象；魂結效果列是雙環；精英召喚的召喚物上限畫減號。
5. 逐像素比對（第 8.3 節，各列組數與結果）；截圖清單（完整路徑、對到第 8.4 節哪一列、真 1 倍或 DPR 2）；「實機未看」清單。
6. 和樣張不同的地方（型別調整等；值不得改）。
7. 長函式：超過 80 行的函式（逐行搬的不拆）；改到 Python 時新增的 noqa 逐一列理由。
8. **待 PM 決定**：最多 10 點，每點附出處（第 0 節第 3、5、6、7 列若仍成立要再列）。
9. **交使用者時要講明**：照抄審查第 2 版的清單（肩撞 24px 只看得出人往前衝、黏液洋紅色、煙霧彈和其他炸彈同剪影、`tag_summon` 改畫小靈、`attack`／`actions` 與 `tag_other`／`default` 同圖、雙環和被動 ∞ 剪影相同、化形專精兩顆靠箭頭分、樣張組裝圖不讀 `icon_prop`），並註明哪幾條已在實機看到。
