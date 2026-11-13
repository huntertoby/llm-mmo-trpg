# Phase RG-4（＋RG-3b、#163）完成報告

依據：`docs/art/RG樣張.md` 9.6 決定、9.8 移植說明；`RG樣張-審查.md` 最後三節；`PhaseAF-1報告.md`、`PhaseRG-3報告.md` 的開發 PM 裁定；#163（`docs/design/08-裝備.md` 塔盾詞條「護陣」，commit `fd4a21df8`）與專案 PM 轉達的修正（兩種大盾維持只給敵人，玩家塔盾外觀照現有塔盾）。

## 1. 做了什麼

### RG-3b：「被擋下」改讀 `lock_intercepted`
- 前端 `battle/feedback.ts` 新增 `interceptSpots`：`lock_intercepted` 事件 → 在 `blocker_id` 頭上跳「被擋下」（tone good）；找不到擋的人時不顯示（不退回目標頭上）。
- `lock_on_blocked` 落空現在只剩「擋住的人本身選不到」（2 格外隱蔽）一種；引擎事件沒有擋的人，所以 API 仍推算 `lock_blocker_id`（`presenter._lock_fizzle_ids` 說明已改寫）。
- `tests/api/test_rg3_api.py`：原本「被擋下落空帶射出者與擋的人」改寫成兩條：改打擋住的人（有 `lock_intercepted`、沒有 `lock_on_*` 落空、命中的是擋的人）；擋住的人選不到（2 格外隱蔽）時仍是 `lock_on_blocked` 並帶 `lock_caster_id`／`lock_blocker_id`。vitest 加 `lock_intercepted` 浮字一條。
- 瞄準線被擋的畫法重新檢查：線在擋的人前斷開、後段灰、目標準星灰——AF-1 後意思是「這一擊會打在擋的人身上、目標安全」，畫法仍正確，不改。

### RG-4：美術第二批（三項都採 A）
- **持盾弟子・雲紋碑盾**：`FormDef.enemy_only`（預設不輸出）；`kite_shield` 加 `sect_great`（門派大盾，`enemy_only: true`）；玩家外觀池（`item_gen` 用 `player_forms()`，過濾後清單和改前逐項相同）、`appearance_export`（`gearAppearance.json` 不變）、物品檢查（寫 enemy_only 形制報錯）都略過；另加「一個造型至少有一個玩家可用形制」。`DollGear.emblem: Literal["peak"]`（沒寫不輸出）→ `QItem.emblem`。`qCore.isTowerLike()` 換掉 9.8 表的 8 處；表外的 `inkOffhand.ts`（C 墨線畫風，遊戲固定 Q）、`qIcon/weapons.ts`（玩家物品圖示）不在敵人紙娃娃路徑上，未動。畫法 `render/qSectShield.ts`（照 `front()／side()／back()`）。
- **熔殼甲兵・立殼（新月形，照樣張 A，不照「半圓殼片」字面）**：`inkCreature.TRAITS.molten_shield`（照 `SHELL.a.draw`），單位外觀加 `traits: [molten_shield]`。
- **單挑插圖・暮色對峙**：`render/duelArt.ts`（剪影侵蝕、二值化、武器縫、斗笠寬帽緣、SKY 兩區＋退回雲嶺、DPR 上限 2）、`world/duelArtPlan.ts`（純函式：主角外觀、第一個精英的 look、主手武器、異形用獸爪、區域）、`world/DuelArt.tsx`（快取）。獸爪 `qIcon/beastClaw.ts`（不進武器圖示表與任何指紋清單）。交叉照 9.8 第 4 條：異形先畫劍（×1.12）再蓋爪痕、間距 9、中心 −8、不加火花；人形先精英再主角、有火花。接進 RG-3 的卡內單挑段（不開 `DialogFrame`）。
- **鍛疤**：不寫特例，插圖剪影從伺服器給的外觀自動產生（目前 base `bandit_captain`，等於借荒原隊長剪影**暫代**，外觀定案後自動跟著換）。
- **單挑按鈕**：兩顆一般 `<button type="button">`（拿掉 `primary`）、`min-width: 96px` 同寬、接受在左；沒有 autoFocus，單挑段 `tabIndex={-1}`、打開時焦點給它本身。

### #163：塔盾詞條「護陣」
- 規則：`engine/rules/combat.guard_between(..., formation=)` 和盾兵共用同一套判定（同陣營、非目標本人、四方向相鄰、朝攻擊者那側、高度）；護陣看身上生效的 `ally_ranged_cover` 詞條，護相鄰所有隊友、只算遠程。和半掩護、盾兵、塔盾不疊加，取最高（同分算原本來源）。工坊欄位 `core.shield_formation_hit_penalty`（初值 2，獨立）。`Cover.kind` 新值 `shield_formation`、`attack_rolled.cover_formation`。戰鬥紀錄：「護陣 −2［命中 −2：被X的護陣擋住］」。
- 詞條 `affix_trait_tower_formation`（武器特性強化類、8 點），新欄位 `offhands: [tower_shield]` 限定塔盾；卡片文字用 `{core.<欄位>}` 代入。
- 掉落：`world/loot.yaml` 的 `signature_affixes`（持盾弟子、熔殼甲兵 → 塔盾 → 護陣），`item_gen.with_affix` 不取亂數地補上，其他掉落逐位元不變。
- 玩家塔盾外觀照現有塔盾；**玩家大盾外觀等美術移植說明交件後再接**（兩種大盾維持 `enemy_only`）。

## 2. 指紋（和樣張逐像素）

| 項目 | 結果 |
|---|---|
| 既有盾（圓盾 2、鳶盾 3、塔盾 2 × 2 身體 × 4 方向 × 8 姿勢 × 5 種畫法，448 格） | 改前改後總指紋都是 `9bc00424`，逐字不變 |
| 碑盾 front／side／back × 縮放 1、2、4 × DPR 1、2 × 錨點整數／小數（36 組） | 差異 0 |
| 整隻持盾弟子（遊戲 qDoll＋樣張鑰匙色代理 vs 遊戲 `sect_great`），4 方向 × 8 姿勢 × DPR 1～3 | 差異 0 |
| 整隻持盾弟子（樣張 QDoll.stamp vs 遊戲 qStamp） | 正面 49／140、背面 48／129、朝東 27／85、朝西 0（DPR 1／2）；和沒有盾的持劍弟子、塔盾基準組數字完全相同、逐像素「只在持盾弟子有差」的是 0 → 兩邊 qDoll 原本的小差，不是盾 |
| 立殼 × 縮放 1、2、4 × DPR 1、2 × 朝東／西 × 錨點整數／小數（24 組） | 差異 0 |
| 既有異形 | `creaturePose.test.ts` 快照只有「所有特徵」那一鍵（`traits`）變，其他鍵逐字不變 |
| 獸爪 px 48、58 × res 1、2 | 差異 0 |
| 單挑插圖整張（四場 × DPR 1、2） | 狼王 210／582、疤面 934／1502、熔核領主 211／582、鍛疤 1023／2107；扣掉交叉武器（±40 px）與精英剪影後八格都是 0。歸因：①武器圖示只差顏色（QI-1a 決定遊戲端材質色暗一階，alpha 差 0）；②人形精英 DPR 1 的差來自樣張自己 QNpc／QDoll 兩條路就差 141～149（遊戲只有 qDoll 一條，DPR 2 為 0）；③熔核領主是兩邊甲蟲本體原有小差（拿掉詞綴與特徵仍 98／12）。主角剪影與獸爪都是 0 |
| 共用檔 | `qIcon/weapons.ts`、`qNpc.ts`、`qStamp.ts` 沒改（斗笠換帽緣在 `duelArt.ts` 內的掛勾做） |

開發頁：`/dev/rg4-shield-gallery.html`（`?mode=fp｜shield｜doll`）、`/dev/rg4-shell-gallery.html`、`/dev/duel-gallery.html`（`?mode=diff｜dialog&e=wolf|lord|scar|forge&w=1600|800`）。無頭 Chrome `--headless=new --disable-gpu --dump-dom`，結果在 `<pre id="out">`。

## 3. 預測與實際

| 項目 | 預測 | 實際 |
|---|---|---|
| 不變比對（改前＝`258daa3d8` 的 `git archive`；8 張地圖 × 種子 1、2＋3 張頭目圖 × 種子 3～12，效用 AI、`max_rounds=30`，比事件、步驟、去掉 ruleset 的最終狀態） | 預設陣容沒人帶護陣、判定不取亂數、新欄位 false 不輸出 → 全部逐字相同；`ruleset_hash` 全變（core 新欄位、詞條表、單位外觀） | `battles=46 events=20499 different=0 ruleset_hash_changed=46` |
| 一場重播 open_plain 種子 7 | 通過 | 「重播驗證通過：91 個動作、383 個事件，最終狀態一致」 |
| CLI 快照 24 鍵 | 0 鍵變（戰鬥鍵沒人帶護陣、技能沒改、外觀不進 CLI 輸出） | 24 passed，未重產 |
| 物品產生器（副手 × 4 稀有度 × 300 種子，改前改後腳本比對） | 只有預算放得下護陣（8 點）的高等級才會變 | 等級 1～10 全同；只有 12 稀有、15 稀有／史詩有差（119／14400）→ roguelite、world、loot 快照不變 |
| 計數類測試 | 詞條數 79→80、工坊核心欄位清單 | 正好壞 `test_equipment_content`、`test_gear_api`、`test_rules_budget_bs1`，已改 |
| `gearAppearance.json` | 不變 | 不變 |
| `schema.d.ts`／`openapi.json` | 多 `DollGear.emblem`、`GearAffixInfo.offhands` | 同預測 |
| `unitDolls.json` | 持盾弟子、熔殼甲兵兩筆 | 同預測 |
| `inkDollSnapshot` | 持盾弟子一行 | 同預測 |
| `creaturePose` 快照 | 只 `traits` 鍵 | 同預測 |

## 4. 版號

- `LOG_FORMAT`：`/122` → `/123`（`attack_rolled.cover_formation` 新欄位、有護陣時結算不同）。同步 9 處寫死字串（`tests/cli` 6 檔 7 處、`test_gear_g2.py`、`test_gear_g3a.py`）與 3 個 `endswith`（`test_collided_sacrifice_firearm.py`、`test_self_costs.py`、`test_wind.py`）；`docs/phases/戰鬥紀錄格式變更.md` 加 `/123`。
- `WORLD_RULES_VERSION`：31 → 32（掉落程式改了：盾兵塔盾必帶護陣）；同步 `test_pr2a_range_practice.py`、`test_opening_stages.py`。
- `CHAR_FORMAT`、`trpg-wlog`、`trpg-world`、roguelite `SAVE_FORMAT`：不升（存檔結構沒變，物品只存詞條 id）。
- 詞條表沒有獨立版號，內容 digest／`ruleset_hash` 自動區分。

## 5. 檢查（交件前）

| 檢查 | 結束碼 |
|---|---|
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client build` | 0 |
| `uv run ruff check` | 1：只有 `docs/art/sample/tools/rg_units_shots.py` 的 E501（main `21933c9bb` 美術提交就有，本段沒碰）；排除該檔為 0 |
| `uv run ruff format --check` | 1：同一個檔；其餘 2677 檔已格式化 |
| `uv run mypy` | 0 |
| `uv run lint-imports` | 0 |
| `uv run trpg content check` | 0（429 招） |
| 直接相關 pytest（rg3 API、護陣引擎／詞條／掉落、碑盾、盾兵、瞄準、AF-1、外觀） | 0（127 passed） |
| 直接相關 vitest（rg3Marks、rg4DuelArt、rg3Duel、qSectShield、inkCreature、creaturePose、inkDollSnapshot） | 0（64 passed） |
| 護陣實作者另跑：`tests/{engine,content,api,world,narrative,cli}`＋architecture（-n 8）、roguelite、slow（engine、refactor_parity） | 全過 |

全量 `scripts/check.py` 未跑（照守則）。

## 6. 截圖（`docs/art/shots/RG-4/`，DPR 1、`?mute=1`、無頭 Chrome `--mute-audio --disable-gpu`）

| 檔 | 內容 | 來源 |
|---|---|---|
| `01`～`05` | 持盾弟子：1600、800 整張、×3（1600、800）、真 1 倍 | 實機（開發頭目戰雲海吊橋，正式盾陣） |
| `06-shield-doll-devpage.png` | 樣張與遊戲端四方向並排 | 開發頁，實機未看 |
| `07`～`11`、`13` | 熔殼甲兵：1600、800、×3、真 1 倍、熔岩洞窟 ×3 | 實機 |
| `12-shell-infocard-1600.jpg` | 滑過熔殼甲兵的資訊卡 | 實機 |
| `14-shell-devpage.png` | 只畫立殼 | 開發頁，實機未看 |
| `15`、`16` | 遇敵卡頭像（持盾弟子、熔殼甲兵）整張與 ×4 | 實機＋注入（換 `encounter.enemies`） |
| `17`～`20` | 單挑：北坡狼王 1600／800、鍛疤 1600／800 | 實機真遇敵，無注入 |
| `21`～`24` | 插圖 ×2 與真 1 倍（狼王、鍛疤） | 實機 |
| `25`～`27`、`31`、`33` | 瞄準線被擋（1600 整張、真 1 倍、×2；800 整張、×3） | 實機＋注入 `telegraph.charges` |
| `28`～`30`、`32`、`34` | 「被擋下」浮字關鍵幀（1600 兩幀、真 1 倍；800 整張、×2） | 實機＋注入 `lock_intercepted`／`attack_rolled`／`damage_dealt` |
| `35`、`36` | 玩家背包：帶護陣的現有塔盾，詳情欄看得到「護陣」 | 實機＋注入 `inventory`（伺服器程式產生的一件塔盾） |

看到的（照最終圖）：碑盾在雲嶺石板上是青面月白邊的高盾，800 縮到 63% 時盾和身體糊成一塊；立殼是甲蟲前一片帶三道橘色鋸齒的黑殼，800 只剩輪廓；單挑兩場插圖都在、按鈕同寬一般樣式；「被擋下」在站在中間的主角頭上，接著命中與 −9；護陣塔盾外觀是現有塔盾。實機未看：熔殼甲兵的真遇敵卡頭像（當天實地沒刷到熔殼陣容，改注入）；DPR 3 高解析戰場（`--disable-gpu` 下截不到，特寫一律用 1 倍最近鄰放大）。

## 7. Commit

| hash | 內容 |
|---|---|
| `ddd326657` | RG-3b：「被擋下」讀 `lock_intercepted`、API 測試改寫 |
| `be7110cf0` | 持盾弟子雲紋碑盾（`enemy_only`、`emblem`、`isTowerLike`、`qSectShield`、開發頁） |
| `258daa3d8` | 合併 main（#163 設計） |
| `7a18dde3b` | 單挑插圖暮色對峙、獸爪、按鈕 |
| `5f6f69eba` | #163 護陣：規則、詞條、盾兵掉落、`LOG_FORMAT` `/123`、`WORLD_RULES_VERSION` 32 |
| `11600c8f5` | 熔殼甲兵立殼特徵、開發頁 |
| `f3b3aed4a` | 截圖 |
| （本報告的 commit） | 報告、上手筆記（前端 154、155；引擎 44） |

## 8. 待 PM 決定

1. **護陣第一季抽不到**（玩法）：稀有起第 1 條是技能強化，副手詞條預算在第一季上限 10 級只有 14 點，放不下護陣（8 點）；一般掉落、打造要 12 級以上。第一季實際只有盾兵必帶這條路。
2. **低等級盾兵必帶超過預算**（玩法）：雲嶺盾兵 3～4 級時副手預算 6 點 < 8 點；照「必帶」讓護陣照樣帶上、其他詞條拿光，也不看稀有度允許的類別（比照 5D-4「照穿」先例）。另一種是嚴守預算＝雲嶺盾兵永遠掉不出護陣。
3. **高度條件**（玩法）：和盾兵共用同一套，持盾者視為 1 層高，攻擊者要高 2 層才無視；設計文寫「高 1 層以上照樣無視（同塔盾、半掩護）」。測試把現況標成待確認。
4. **掉落歸屬**：精英那件只算該精英；沒精英的一般掉落只要陣容裡有盾兵就算（不要求擊倒他）。roguelite 戰後三選一沒套必帶。
5. **同分取誰**：護陣與其他掩護同分時算原本來源（不變比對用）。
6. **詞條歸類**：放在「武器特性強化」類（玩家看到的類名也是這個），要另立「副手特性」再定。
7. **撞名**：5A-M2b 的狀態 `ward` 在紀錄裡也叫「護陣」。
8. **AI 沒接護陣**：效用 AI 的掩護估值、站位不算護陣（規格沒要求）。
9. **預覽小盾**：前端的盾兵小盾與連結只畫 `cover.kind == "shield_guard"`；`shield_formation` 只有伺服器的預覽文字，沒有圖示（美術沒定樣式）。
10. **單挑插圖在 800**：卡片比 320 窄，插圖等比縮成約 259×97（畫布仍 320×120）；請美術看要不要改成不縮或換位置。
11. **單挑細節**：其他異形精英倍率先用 1.5（只有狼王 1.2、熔核領主 1.8 定案）；插圖內部解析度上限 2；按鈕列由兩欄等寬改成靠右各 96 px（照樣張）；人形精英武器圖示用伺服器給的外觀（疤面的刀在圖示表退回直劍，同樣張）。主角武器照玩家自己的主手（截圖的開發角色是弓、斧，交叉組合和樣張的劍不同）。
12. **碑盾紋樣顏色**固定照樣張（月白章、青山、朱紅點），不跟 color／trim 換；「一個造型的形制不能全是 enemy_only」是順手加的檢查。
13. **瞄準線斷點**：1600 實機的斷點短槓在擋的人頭頂偏右上（線是頭頂到頭頂的高度），同 RG-3 畫法，請美術確認。
14. 玩家大盾外觀（兩種大盾當塔盾形制）等美術補畫手持立殼、Q 版圖示與玩家配色的移植說明交件後再接。
