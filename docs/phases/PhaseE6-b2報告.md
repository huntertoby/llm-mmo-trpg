# Phase E6-b2 報告｜招牌勾選的保存、API、前端顯示

> 規格 `docs/phases/PhaseE6-b2計畫.md`；規則以 `docs/design/08-裝備.md` 8.27、8.30 第 4、5、10 點為準；美術照 `docs/art/E6-招牌-移植需求.md` 第 1～4 節。基準 `abb4d680d`。`LOG_FORMAT` 不升（`/139`）；`trpg-run`、`trpg-char` 版號都不升（見 2.1）；`WORLD_RULES_VERSION` 37 → 38。沒動 `docs/design/`、`config/`、`CLAUDE.md`。

## 1. Commit

| 項目 | commit |
|---|---|
| 1 勾選的保存、開戰帶進 `Loadout.chosen` | `31ba7b6ff` |
| 2 換裝時保留原本生效的（E6-b1 待決 1） | `cb9821f24` |
| 3 API 欄位、勾選端點、OpenAPI／`schema.d.ts` | `a743c67cb` |
| 5 大世界主角面板照身上的裝備算（WM-1 待決 9） | `cbb33f27c` |
| 4 前端（招牌框、類型圖示、一次性強調、掉落小標、角色面板勾選）＋開發頁＋截圖 | `e47d4baba` |
| 6 選做（戰後小牌） | 沒做（見 2.6） |
| 報告 | 最後一個 commit |

第 5 項是後端，排在前端之前 commit。

## 2. 各項做法

### 2.1 勾選的保存（第 1 項）

- `RunState.gear_chosen`、`CharacterState.gear_chosen`：`tuple[str, ...]`，每個是 `"<欄位>:<詞條 ID>"`（同 `Loadout.chosen`），預設空、**空的時候不輸出**。
- 版號：**都不升**。空的時候存檔逐位元不變，舊存檔照讀（測試鎖住）。世界照 LF-1、PK 的前例（選填欄位空值不寫，`CHAR_FORMAT` 不變）；一輪過去每加欄位都升號，這次比照世界的做法不升（待決 1）。
- 開戰：`roguelite.gear.run_loadout` 與 `world.gear.hero_loadout` 最後經 `with_chosen` 帶上勾選（沒勾時原樣回傳，快照不變）。世界的共鳴 `apply_resonance` 會新建 `Loadout`，所以勾選放在共鳴之後。
- 季末重置政策表（`server/season_policy.py`）把 `gear_chosen` 列為數值類（跟著裝備），`test_every_saved_field_has_a_season_reset_kind` 要求。

### 2.2 保留原本生效的（第 2 項）

- `roguelite.gear.keep_active_chosen(library, before, after)`，`equip_swap` 最後呼叫（一輪的三選一、營火換裝、大世界 `equip` 都經過它）：
  - 換上之後**可能超過名額**（標了招牌的 > `signature_active`，或不同 id 的改寫規則 > `rule_affixes`）時，把換裝前生效的招牌與改寫規則（還穿在同一欄同一件的）寫進 `gear_chosen`；用這份勾選真的有詞條被標灰才採用，於是新穿上的那件標灰。
  - 不會超過時只拿掉換下那件的舊勾選；沒勾過的維持空的（開戰的裝備快照不變）。
- 現有內容的三件測試傳說（各 1 條沒標招牌的改寫規則）也照這規則：穿著 A 再換上 B 時保留 A（以前照欄位順序）。
- `WORLD_RULES_VERSION` 38（`equip` 的結果會多寫勾選；另外新動作 `gear_chosen`）。測試裡兩處寫死的 37 改 38。

### 2.3 API（第 3 項）

- `GearItemLine` 多 4 個選填欄位：`signature`（種類）、`signature_zh`（類型牌「招牌・新動作」；傳說的獨特效果、獨特裝備的招牌寫「獨特效果・〇〇」）、`signature_name_zh`（授予技能的是那一招的名字，其他 `None`，前端用詞條全文）、`off_zh`（被名額標灰的原因，**長版**）。
  - 穿戴中的物品照現在的勾選；三選一與背包的候選照「換上之後」（`candidate_off`，經 `keep_active_chosen`，所以是新的這件被標灰）。
  - 沒標招牌的改寫規則也算「改寫規則」框（現有三件測試傳說會出框，待決 2）。
- `HeroOut.signatures`、`InventoryView.signatures`（`SignaturePanelOut`）：列（依欄位順序）、`active`／`cap`、`rules`／`rule_cap`、`has_rule`、`count_zh`、`full_zh`（已滿提示）、`chosen`、`problem_zh`。列的灰字用**短版**「已經有 3 個生效，這個沒有效果」；改寫規則照 8.27「和〇〇的改寫規則衝突，沒有效果」。「生效 N」不算整條沒效果的（同引擎）。
- `BagItemView.signature`：背包與掉落列的招牌種類（前端加「招牌」小標）。
- 寫入：一輪 `POST /api/runs/{id}/choice` 的 `{"kind": "gear_chosen", "chosen": [...]}`；大世界 `POST /api/world/characters/{id}/actions` 的同名動作（事件 `gear_chosen`）。合法性在 `roguelite.gear.chosen_problems`：格式與重複、勾的必須是身上的招牌或改寫規則、招牌 ≤ `signature_active`、改寫規則 ≤ `rule_affixes`；不合法拋 `ChoiceError`／`WorldActionError`，狀態不變。存的時候依欄位順序排序。
  - 一輪：戰鬥之間都能送（不推進節點），戰鬥中擋下（和閃現、配點同一處）。
  - 大世界：比照換裝，只在城鎮或營火、沒有遭遇時（待決 3），面板 `problem_zh` 寫原因並停用。
- 守則 14：兩個端點都走既有的擁有者檢查；`test_owner_guard.py` 的一輪與世界路由表各加一列 `gear_chosen`（別人 404、未登入 401）。面板只算主角自己的裝備；其他單位照戰鬥的單位資訊（`AffixLineView`）顯示，沒改。
- `engine/view.py` 的 `_limited_zh` 改成公開的 `limit_off_zh(ruleset, gear, entry)`（只換參數，戰鬥檢視結果不變），API 共用。
- 重產 `client/openapi.json`、`client/src/api/schema.d.ts`。

### 2.4 前端（第 4 項，照移植需求第 1 節第 1～5 項）

- **招牌框** `ui/gear/SignatureBox.tsx`：放在 `GearCardView` 詞條清單前面（卡片第一行），清單不重複列那條。框色＝稀有度色、標灰灰框、刪除線、最後一行原因（長版）；`.gear-card-headtext .small` 加 `text-wrap: pretty`。三選一、背包詳情、比較都用同一個 `GearCardView`。說明框（`PartTip` 的 `itemTipLines`）招牌行前面加類型牌的字，標灰的帶長版原因。
- **類型小圖示** `render/qIcon/signature.ts`＋`ui/gear/SignatureIcon.tsx`：四種用部件圖（`effect.grant_skill`、`effect.extra_reaction`、`skeleton.modifier`、`effect.rule_change`），地形規則照樣張 `terrainArt` 逐行搬；不改過審的 `parts.ts`，用同一套 `glyph` 算法另畫。18／16／14 px、圖樣＝格子 ×0.75、全部 tiny；標灰由 CSS 做灰階＋50%。
- **一次性強調**：CSS 照樣張（0.25 秒後開始：類型牌輕彈 0.35 秒、光暈 1.1 秒、斜光 0.8 秒）；`useSignatureFx` 每件（物品 ID）這次開遊戲只播一次（記錄在記憶體，重新整理後會再播一次，待決 4）；減少動態（遊戲設定或系統）不播，CSS 也擋。三選一剛打開、大世界背包詳情第一次打開這件時播。不加音效。
- **大世界掉落**：背包滿時的選擇列在名字後面加「招牌」小標＋14 px 圖示（小標顏色見待決 5）。
- **角色面板勾選** `ui/gear/SignaturePicker.tsx`：一輪 `RunHeroPanel`（裝備圖示列下面；`RunScreen` 傳 `onChoose`，`RunEnded` 不傳＝只能看）、大世界「穿戴中」下面（寬度 ≥1100 px 兩欄）。
  - 招牌方框、改寫規則圓鈕；按另一條改寫規則直接換過去。
  - 超過名額時：按勾著的那列先在畫面上取消（不送出），再勾沒勾的那列才送出新的 3 個；已滿時按沒勾的列跳一行提示「已經有 3 個生效，先取消勾選一個，再勾這個。」（後端給字）。沒超過名額時全部都生效，不能取消。
  - 滑過一列顯示現行裝備的浮動卡（共用 `PartTip`）；按列本身是勾選，按鈕擋掉冒泡，所以不會同時釘住（待決 6）。

### 2.5 主角面板沒看身上裝備（第 5 項）

- 查明：**會錯**。`hero_panel` 用 `as_run(char)`，`RunState.equipment` 是空的，`run_loadout` 退回主角範本的裝備，所以大世界主角面板的有效屬性、副手特性、暴擊倍率都照範本算（身上換了裝備也不變）。
- 修法：`hero_panel` 把 `CharacterState.equipment` 與 `gear_chosen` 放進 `RunState`（同 `gear_run`）；裝備因此已在 `RunState` 的 JSON 裡，快取鍵拿掉另外的裝備字串。共鳴（`apply_resonance`）沒算進面板，照舊。
- `tests/api/test_wm1_walk.py` 有一筆測試資料把物品種類 `weapon` 當欄位放進 `equipment`（以前面板不看所以沒出錯），改成真的欄位 `main_hand`。

### 2.6 選做：戰後那行字裡的小牌（第 6 項）

**沒做。** 估計超過半天：戰後那行字是 `world_economy_view._loot_text` 拼好的字串，要改成結構化掉落清單需要動事件檢視的 schema（掉落的物品 ID、稀有度、招牌種類）、重產 OpenAPI、前端日誌列改成元件畫小牌、補測試與截圖（本段截圖已 9 張，上限 10）。留給之後。

### 2.7 其他

- 開發頁 `client/dev/e6b2-gallery.html`（`src/dev/e6b2Gallery.tsx`）：現有內容沒有招牌，資料直接塞進正式元件（`GearCardView`、`RunGearOffer`、`RunHeroPanel`、`WorldBagScreen`）。
- 沒有新增 `# noqa`。

## 3. 驗收

| 檢查 | 結束碼／結果 |
|---|---|
| `uv run python scripts/check.py --all`（全部 commit 之後） | 0；pytest 18935 passed、8 skipped；vitest 426 檔 5027；ruff、format、mypy、lint-imports、client typecheck、situation coverage 通過；已寫通過戳記 |
| `uv run python scripts/run_pytest.py -q -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 0（995 passed；CLI 快照沒變） |
| `pnpm -C client build`（`corepack pnpm`） | 0 |
| 78 場（`compare78.py`，基準 `abb4d680d` 的 `git archive`） | 0；`battles=78 events=26741 different=0`；格式 `/139 → /139`；規則包差異 0 |
| 442 招逐招預算（`budget.py`） | 0；`cmp` 0，same=442 different=0 |
| census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`，不看計時） | 0；`cells=204 different=0` |
| CLI 快照 | slow `tests/cli` 通過（快照逐字相同） |
| `ruff check`、`ruff format --check`、`mypy`、`lint-imports` | 0、0、0、0 |
| `trpg content check` | 0 |
| `scripts/hardcoded/classify.py --check` | 0（沒歸類 0） |
| tsc、vitest | 0、0（含在 `check.py --all`） |

**新測試**

- `tests/roguelite/test_gear_chosen_e6b2.py`、`tests/world/test_gear_chosen_e6b2.py`：空的不輸出、讀寫往返、舊存檔照讀、開戰帶進 `Loadout.chosen`；世界 `equip` 保留原本生效的。
- `tests/roguelite/test_keep_active_e6b2.py`：第 4 個招牌換上時新的標灰（沒勾選時會標灰項鍊）、新改寫規則標灰、沒標招牌的改寫規則也一樣、不超過時維持空的、換下那件的勾選拿掉。
- `tests/api/test_gear_signature_e6b2.py`：超過 3 個、2 條改寫規則、身上沒有的、重複都被擋；合法的依欄位順序存、不推進節點；面板的列順序、計數、短版灰字、改寫規則衝突字；裝備卡長版灰字（穿戴中與候選）；類型牌與名字；大世界動作存下與擋下；背包列的 `signature`。
- `tests/api/test_owner_guard.py`：一輪與世界的 `gear_chosen` 只有自己能送。
- `tests/api/test_world_hero_panel_gear_e6b2.py`：主角面板算進身上的裝備；面板帶勾選。
- `client/src/gear/signature.test.ts`：灰字短版（角色面板）、長版（裝備卡、說明框）；名額計數；已滿提示；先取消再勾；圓鈕換過去；一次性強調只播一次；減少動態時不播；掉落列小標。

## 4. 截圖（`docs/art/shots/e6-b2/`，9 張；對照移植需求第 4 節）

| 第 4 節 | 檔案 |
|---|---|
| 1 裝備卡：五種、傳說、標灰兩種（1600、800） | `docs/art/shots/e6-b2/1-cards-1600.jpg`、`docs/art/shots/e6-b2/1-cards-800.jpg` |
| 2 類型小圖示 18／16／14 加標灰，真 1 倍＋最近鄰 ×6 | `docs/art/shots/e6-b2/2-icons-1x-x6.png`（同一張：上半真 1 倍、下半 ×6） |
| 3 三選一，有招牌和沒招牌並排（1600、800） | `docs/art/shots/e6-b2/3-offer-1600.jpg`、`docs/art/shots/e6-b2/3-offer-800.jpg` |
| 4 一次性強調 0.4、0.7、1.4 秒 | `docs/art/shots/e6-b2/4-fx-0.4-0.7-1.4s.jpg`（三個關鍵影格並排在同一張） |
| 5 大世界：背包滿時的列、背包詳情（1600；沒做戰後小牌） | `docs/art/shots/e6-b2/5-world-1600.jpg` |
| 6 角色面板：4 個勾 3 個、改寫規則衝突、已滿提示（一輪 1600、800；大世界「穿戴中」1600） | `docs/art/shots/e6-b2/6-panel-1600.jpg`、`docs/art/shots/e6-b2/6-panel-800.jpg`；大世界「穿戴中」在 `docs/art/shots/e6-b2/5-world-1600.jpg` 的中段 |

- 為了 ≤ 10 張，第 2 項 1 倍與 ×6 合成一張、第 4 項三個影格合成一張、第 6 項大世界和第 5 項同一張。
- 截圖用無頭 Chrome（`--mute-audio`，網址帶 `?mute=1`），截完已關。

**浮動卡實測**（瀏覽器，開發頁）：1600×900（大世界穿戴中的招牌列）、800×600（一輪角色面板的招牌列）都做了「從列滑進卡片 → 卡片內捲動 → 點卡片釘住（`pinned`）→ Esc 關閉」，都正常。卡片很短，沒有內捲。

## 5. 待 PM 決定

1. **存檔版號不升**：`gear_chosen` 空的時候不輸出，`trpg-run/13`、`trpg-char/15` 都不升（世界照 LF-1、PK 前例；一輪以前加欄位都升號，這次比照世界）。新版寫出的有勾選的存檔，舊版程式讀不進（`extra=forbid`）。
2. **沒標招牌的改寫規則也畫框、也進角色面板**：種類當「改寫規則」，不佔 3 個名額（同引擎）。現有三件測試傳說因此會出「獨特效果・改寫規則」框；換裝時也照「保留原本生效的」。
3. **大世界改勾選的地點**：比照換裝只在城鎮或營火（最保守）；一輪是戰鬥之間都能改。若要野外也能改，拿掉 `apply_gear_chosen` 的 `equip_problem` 即可。
4. **「同一件只播一次」只記在記憶體**：重新整理頁面或重開遊戲後，同一件再打開會再播一次；要跨重開記住得存起來（瀏覽器或伺服器）。
5. **背包滿時「招牌」小標的顏色**：`BagItemView` 沒有稀有度，小標用固定的 `#e0b060` 系（樣張是物品稀有度色）。要照稀有度得在 `BagItemView` 加 `rarity`。
6. **角色面板一列的浮動卡怎麼釘住**：按列是勾選（擋掉冒泡），所以釘住要先滑進卡片再點卡片；滑進、寬限、Esc 照共用規則。
7. **大世界面板兩欄的順序**：照部位、由左到右再往下（網格列優先），不是左欄排完再排右欄。
8. **共鳴沒算進大世界主角面板**：第 5 項只補上身上的裝備與勾選；開戰另外加的 2 件共鳴詞條面板照舊不算（數值類，和改前一樣）。

## 6. 平衡疑慮

沒有。這段沒有試數值。
