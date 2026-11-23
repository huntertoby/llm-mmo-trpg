# Phase E6-a2 報告｜打造指定招牌類型、重骰招牌、放得下就放

> 規格 `docs/phases/PhaseE6-a2計畫.md`；規則以 `docs/design/08-裝備.md` 8.27「打造不能指定是哪一條」、8.30 第 2、3、10、11 點為準。基準 main `34bb21fa9`（交件前合併 main 到 `433505ccf`，只多一份交接文件）。不改引擎，`LOG_FORMAT` 不升；沒動 `content/`、`config/`、`docs/design/`。
>
> 第 5 項是開發 PM 中途追加的（8.30 第 2 點的解讀「放得下就放」，`cfc8a4663`）。

## 1. Commit

| 項目 | commit |
|---|---|
| 1 鐵匠打造指定招牌類型 | `2ff0e7613` |
| 2 附魔台重骰招牌、指定不能指定招牌 | `83d4b8796` |
| 3 舊配方碼比對測試 | `87eadc7fa` |
| 4 前端打造畫面多一個選項＋截圖 | `553f88032` |
| 5 招牌物品「放得下就放」（追加） | `068b96b5c` |
| 合併 main | `59b515ef5` |
| 報告 | 最後一個 commit |

## 2. 各項做法

### 2.1 打造指定招牌類型（第 1 項）

- `CraftAction.signature`、`CraftRecipe.signature`：`SignatureKind | None`，空值不輸出（`exclude_if`），所以舊動作、舊配方的 JSON 與指紋都不變。
- `CraftAction` 的檢查：`affix` 和 `signature` 只能給一個（「指定詞條和指定招牌類型只能選一個」）；用配方碼打造時不能再給 `signature`。
- `crafting.signature_choices(library, slot, weapon_class)`：開關（`signature_enabled`）打開、部位在 `signature_slots`，而且這一種有能掛在這個部位的候選才列出；篩法同 `build_choices`（不限定武器種類、不是傳說限定、獨特或暫緩詞條）。開關關著時是空的。
- `_recipe_from_fields`：給了 `signature` 時檢查（開關、稀有度與部位帶不帶招牌、這個部位有沒有這一種），配方記 `signature`、`affix` 是空的；build 詞條照產生器原本的抽法隨機（8.27「選了招牌類型就不能再指定關鍵字詞條」）。隱藏配方照舊由配方決定，`signature` 和 `affix` 一樣不用。
- 產生器 `generate_item(..., signature_kind=...)`（`generate_item_retrying` 一路傳下去）：只從這一種的候選抽，不看部位權重；開關關著、不帶招牌或沒有候選時拋 `ItemGenError`。沒給時路徑完全不變（原本的 `_weighted` → `rng.choice` 順序沒動）。
- 指定 build 詞條＋開關打開（E6-a1 待決 6）：沒改程式，照現有規則——放不進剩下的 40% 時報「詞條預算放不下指定的詞條」，打造顯示「這份配方打不出來」。補了測試（3 級項鍊放不下、8 級放得下）。

### 2.2 附魔台重骰招牌（第 2 項）

- `affix_choices` 對招牌那一條改走 `_signature_choices`：同一種、不是原本那條、能掛在這件（`_fits`：不含傳說限定、獨特、暫緩）、和其他條相容；數值取最強的（招牌點數固定 60%，不用再看預算）。E6-a1 的「對招牌回傳空」拿掉了。
- 同一種只有原本那條時沒有候選，照舊報「不能換」。
- 費用：沒改。重骰本來就用 `rules.reroll.gold(mod.changes)`，`changes` 是整件的改動次數，所以和同件其他詞條共用遞增（測試：一般、招牌、一般、招牌四次＝`gold(0..3)`）。
- 附魔台的「指定」：`_apply_step` 遇到招牌報「招牌效果不能指定成某一條，只能重骰」（8.30 第 10 點）。顯示資料 `_affix_views` 對招牌那條給空的 `choices`，前端就不出現「指定成…」選單，重骰鈕照常。
- 順手：`affix_choices` 算「其他條」的迴圈抽成 `_others`，一般詞條和招牌共用（結果不變，產生器種子比對有涵蓋 `affix_choices`）。

### 2.3 配方與存檔相容（第 3 項）

- `tests/world/test_recipe_code_compat_e6a2.py`：6 份配方（含武器大類、特色材料、隱藏配方 `affix: None`、10 級上料），指紋與配方碼是在基準 `34bb21fa9` 算的（用 `git archive` 解開基準跑同一支腳本，和新版 `cmp` 相同），寫死在測試裡；另驗帶重骰序列的配方碼、`model_dump` 不含 `signature`、有 `signature` 時往返且指紋不同。

### 2.4 前端打造畫面（第 4 項）

- API：`CraftSlotView.signatures`（`id`＝種類、`text_zh`＝「招牌：新動作」）；開關關著或部位不帶招牌時是空的。配方表的摘要多「・指定招牌：〇〇」。`client/openapi.json`、`schema.d.ts` 重新產生。
- 前端：照現有樣式，在「詞條」下拉多一組 `optgroup`「或指定招牌類型（不能指定是哪一條）」，選項值是 `signature:<種類>`；選了就送 `signature`、不送 `affix`。換部位時新部位沒有那一種就換成第一條詞條。說明文字在有招牌選項時改成「指定部位＋1 條詞條或 1 種招牌類型」。後端給空的就完全不出現。
- 夾具：`CraftSlotView` 的輸出型別多了必填的 `signatures`，`itemGallery.tsx`、三個測試檔的夾具補 `signatures: []`。
- 新文字歸類：`scripts/hardcoded/classes.yaml` 的 `ts-hc6c-structure-text` 加「1 條詞條／1 種招牌類型」（同一個欄位二選一）。

### 2.5 放得下就放（第 5 項，追加）

- 產生器 `_roll_affixes(allow_empty=True)`（只有招牌物品的「招牌以外」會走）：先照原本的方法找湊得到 70% 的組合（隨機幾次、再每步挑點數最高）；都找不到時不再回傳空的，改成每步挑點數最高、放得下就放（先帶 build 詞條、再不帶）；一條都放不下才回傳空的（整件只有招牌）。
- 預算檢查 `_fill_problems`：招牌物品不再檢查下限，只檢查不超過整件預算。沒有招牌的物品一字不差。
- E6-a1 的兩個測試跟著調：`test_lower_bound_only_counts_the_rest` 的「6 < 6.72 報錯」改成「照樣通過」；`test_rest_respects_the_70_percent_floor` 只加說明（那份內容庫抽樣到的都湊得到 70%，產生器照舊優先湊到）。
- 開關關著時不走這段（`allow_empty` 只在有招牌時為真），種子比對 different=0。

## 3. 驗收

| 檢查 | 結果 |
|---|---|
| 442 招逐招預算（E5 的 `budget.py`；基準 `34bb21fa9` 用 `git archive` 解開） | `cmp` 0，skills=442 different=0 |
| 78 場戰鬥（E5 的 `compare78.py`） | `battles=78 events=26741 different=0`；規則包差異 0 |
| census 小樣本（E6-a1 的 `census_run.py`：`--seeds 4 --tiers 1,3 --rarities common,epic`，不看計時） | `cells=204 different=0 whole_equal=True` |
| 產生器種子比對（E6-a1 的 `gen_seed.py`，6752 行） | 基準與新版 `cmp` 0，different=0 |
| 舊配方碼（6 份配方的指紋、配方碼、帶序列的配方碼；基準 vs 新版） | `cmp` 0；`test_recipe_code_compat_e6a2.py` 7 passed |
| `ruff check`、`ruff format --check`、`mypy`、`lint-imports` | 0、0、0、0（含在 `check.py --all`，開發中也各跑過） |
| `trpg content check` | 0 |
| `scripts/hardcoded/classify.py --check` | 0（沒歸類 0） |
| tsc（`pnpm -C client typecheck`）、vitest | 0、0（含在 `check.py --all`） |
| `uv run python scripts/check.py --all`（合併 main 之後） | 0，已寫通過戳記 |
| `pnpm -C client build` | 0 |

**截圖**：`docs/art/shots/e6-a2/smithy-signature-1600.png`（1600 寬，headless Chrome、靜音）。現有內容沒有標招牌的詞條，實機到不了這個選項，所以用新開發頁 `client/dev/e6a2-smithy.html`（`src/dev/e6a2SmithyGallery.tsx`，正式的 `SmithyPanel`＋正式樣式、假資料）畫：左＝開關打開的打造表單；中＝同一張下拉展開、選了「招牌：新動作」；右＝開關關著，和原本一樣。

**新測試**

- `tests/world/test_crafting_signature_e6a2.py`（E6-a1 的測試內容庫做法，開關打開）：
  - 第 1 項：各部位的可選種類、開關關著沒有；指定類型打出那一種（放最後）、配方記 `signature`、配方碼照打相同；build 詞條隨機；二選一；開關關著、頭、部位沒有那一種、都沒指定時報錯；指定詞條放不進剩下的 40% 報錯；產生器 `signature_kind`。
  - 第 2 項：重骰只換同一種（副手新動作在鉤爪、煙霧之間換）；同一種沒有別條時不能換；費用遞增並和同件其他詞條共用次數；指定不能指定招牌、畫面上招牌那條沒有指定選單。
  - 第 4 項：顯示資料只在開關打開時列種類；配方摘要註明指定的招牌。
- `tests/world/test_recipe_code_compat_e6a2.py`：第 3 項。
- `tests/content/test_signature_fill_e6a2.py`：第 5 項（把下限調成 100% 讓「湊不到」一定出現）：湊不到也照樣放、物品照樣通過檢查；1～4 級稀有靴子剩 1.6～2.8 點、腳的候選最便宜 3 點，所以只有招牌，5 級剩 3.2 點就放進 3 點的詞條；預算檢查對招牌物品沒有下限、仍檢查上限。
- `client/src/world/crafting.test.ts`：選了招牌類型送 `signature` 不送 `affix`；換部位；開關打開多一組選項、關著不出現。

沒有新增 `# noqa`。

## 4. 待 PM 決定

1. **隱藏配方＋招牌**：材料符合隱藏配方時，`signature` 和 `affix` 一樣不用（稀有度與獨特詞條由配方決定）。開關打開後隱藏配方的產生器會另外抽招牌（獨特詞條＋招牌），這屬於 8.30 第 9 點／R8，留給 E6-c2。
2. **可選種類不看稀有度**：`signatures` 依部位列出，稀有度在送出時才檢查（`carries_signature`）。現在打造只有稀有、史詩，兩種都帶招牌，所以沒有差別。
3. **可選種類的篩法照 `build_choices`**：限定武器（`weapons`）的招牌、和主角武器大類不同的招牌不列。產生器實際抽的候選照 `_fits`（看抽到的底材）；萬一底材掛不上，照現有重試（`offer_attempts`），都失敗就報「這份配方打不出來」。
4. **指定類型不看部位權重**：權重是 0 的種類，只要這個部位有候選，也能指定。
5. **招牌重骰的數值**：取最強的，和產生器一樣；不另檢查剩餘預算（招牌點數固定 60%，換哪條都一樣）。
6. **前端的呈現**：放在同一個「詞條」下拉裡的一組選項（照現有樣式），沒有另做單選鈕。重骰鈕的說明（「這條不能換（獨特詞條或沒有候選）」）沒改。
7. **第 5 項的檢查不驗「放得下」**：預算檢查對招牌物品只剩上限，手寫物品若留了空位、還放得下一條也不會被抓。產生器照舊優先湊到 70%，湊不到才每步挑點數最高放。要嚴格驗「放得下就放」得在檢查裡重算候選，成本高，先不做。
8. **開發頁**：截圖用的 `client/dev/e6a2-smithy.html` 留在 repo（和其他開發頁一樣不屬於正式 build）。

## 5. 平衡疑慮（請 PM 轉玩法）

- 沒試數值。只記：第 5 項之後，低等級招牌物品從「只有招牌」變成「招牌＋一條小詞條」的機會變多（例：剩 3.2 點放進 3 點的詞條）；同等級同預算不變。
