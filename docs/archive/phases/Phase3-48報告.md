# Phase 3-48 報告：工坊縮放屬性卡在違規值、錯誤訊息露英文

## 根因

1. **卡在違規值**：法術技的縮放屬性允許範圍由「主要效果的主題」決定（3H-7）。玩家先在「基本」步驟選了意志，之後到「效果」步驟加神聖傷害（歸感知），允許範圍縮成感知，但舊的 `scaling_attr: wil` 沒人重設。草稿的 `autoSingles`（自動對齊鎖定欄位）只在該欄位所在步驟（基本）才會跑，玩家人在效果步驟，所以永遠卡在違規。第二縮放屬性同理。
2. **露英文**：`option_conform.py` 的訊息直接拼 `where`（欄位路徑，如 `draft`、`scaling_attr`）與值（`wil`）；`validate_skill` 等規則訊息同時給 CLI 與模擬用，內含欄位名與 ID。

## 做了什麼

- **自動對齊（前端一處）**：`client/src/workshop/draft.ts` 新增 `conformScaling(draft, options)`，由 `StepView` 在每次選項更新時（不論目前在哪一步）套用：主屬性不在允許範圍就改成範圍內第一個合法值；第二屬性不在範圍、與主屬性相同、或類別是武器技就清掉。後端沒有另寫一套。
- **option_conform 訊息中文化**：位置用中文（「第 2 個效果：距離（格）必須在 1–2」），值只顯示中文屬性名，不認得的代號不顯示；縮放屬性附上原因（「縮放屬性「意志」不在可選範圍內。技能的數值隨這個屬性成長。主要效果「傷害（神聖）」屬於「治療、護盾、輔助、偵測與標記」，只能看 感知」）。其他選項錯誤改列可選項。
- **`trpg.skillgen.player_text.plainify`（新）**：把檢查文字裡的欄位名、ID、列舉值換成中文（片語表、pydantic 英文訊息、內容庫的 `name_zh` 對照：骨架、原語、形狀、狀態、條件、觸發、層數、關鍵字、標籤、元素、表面、武器等）。套用處：`check_draft` 的規則違規與 schema 錯誤、最低稀有度理由、預算明細（效果名、備註、骨架、形狀、協同標籤、自我連鎖原因）、`draft_options` 的步驟限制說明。來源訊息不改（CLI／模擬仍看得到欄位名）。`?dev=1` 仍顯示 `rule` 代碼（沿用 3-47 機制）。
- **來源修正**：內容庫互斥規則訊息拿掉英文欄位名括號；變奏的 schema 訊息改用變奏中文名；`cost_problem` 拿掉 `cost.mana` 與文件編號；陷阱形狀與形狀轉換選項改用形狀中文名（原本直接顯示 `line`、`chain`、`cone`、`single`、`cross`、`square3`）；階級說明拿掉 `rules/core.yaml`；稀有度說明的「見 problems」；進階 YAML 說明拿掉 `replace_effect`。
- **追加 4(a)**：技能卡標題加類別：「法術技・花法力」「武器技・花耐力・看手上武器」（被動、修正只寫類別或「看手上武器」）。`categoryLabel` 在 `client/src/battle/source.ts`，`SkillCardView` 共用，所以戰鬥技能列浮動卡、營火候選卡、工坊預覽都有。
- **追加 5**：武器技縮放屬性欄位的顯示改為「依手上武器而定（例：匕首＝敏捷／力量（取較高）、錘＝體質／力量（取平均）、單手劍＝力量）」，例子由武器資料產生（優先取玩家能裝備的武器，依 ID 排序，每種屬性組合一把，最多 3 種）。欄位說明補「武器技一定要拿近戰或遠程武器；不限武器的是法術技」。

## 追加 4(b)：費用顯示查證

`cost_parts` 有法力與耐力時一定會顯示；那張卡沒寫法力是因為**法力為 0**，不是沒顯示。規則上（`cost_problem`）只擋「花錯資源」（法術技花耐力、武器技花法力），法術技 0 法力是合法的（費用只是預算的折抵，0 就沒有折抵）。依最保守原則沒有新增自動補值或報錯，列入待 PM 決定。

## 掃描清單（流程改善 E）

自動掃描測試：`tests/skillgen/test_player_text.py`。對 60 個隨機組合器技能各做約 20 種變異（改類別、武器需求、縮放屬性、階級、稀有度、種類、AP、骨架代號、刪效果……），收集玩家會看到的文字，斷言沒有英文詞（允許 AP、HP、MP、YAML）。

| 位置 | 結果 |
|---|---|
| `option_conform.py` 全部訊息（選項、範圍、整數、列表、骰子、多選） | 已改 |
| `validate.py` 全部違規訊息（約 60 條，含 `cap`、`scaling`、`skeleton`、`rarity`、`stance`、`budget`、互斥、變奏、第二段） | 經 `plainify`，掃描通過 |
| `draft.py` schema 錯誤（含 pydantic 英文原文與 `variants.xxx.` 路徑） | 經 `plainify` |
| 內容庫互斥規則 `skill_exclusions.yaml` message_zh | 已改來源 |
| `skills.py` 變奏 schema 訊息 | 已改來源 |
| `skill_rules.cost_problem` | 已改來源 |
| 預算明細：效果名、備註、骨架、形狀、協同標籤、自我連鎖原因 | 經 `plainify`／`plain_name` |
| `rarity_reasons`、稀有度步驟說明 | 經 `plainify` |
| 各步驟 `notes_zh`（核心效果、占比上限、至少要有） | 經 `plainify` |
| 欄位與選項名稱（`name_zh`，含陷阱形狀、形狀轉換） | 已改（原本顯示 ID） |
| 前端 `CheckPanel`、`StepView` | 只顯示後端訊息；`rule` 代碼本來就只在 dev |
| `BudgetBar` 的 `coefficient_label`（「AP 係數」）、`variant`／`verdict_zh` | 確認已是中文 |
| 欄位與選項的 `description_zh` | **未改**（見待 PM 決定） |

## 測試

- 新增／更新：`tests/skillgen/test_player_text.py`（新，掃描＋ plainify）、`tests/skillgen/test_workshop_options.py`（訊息改中文並檢查無英文詞；意志＋神聖傷害的檢查訊息）、`tests/skillgen/test_workshop_check.py`（期望值改中文）、`client/src/workshop/locked.test.ts`（`conformScaling`：法術意志→感知、法術→武器技對齊並清第二屬性、第二屬性不合法、合法時回傳同一物件）、`client/src/battle/polish3c6a.test.ts`（`categoryLabel`）。
- pytest `tests/skillgen tests/content tests/api tests/test_architecture.py`：2923 通過。ruff check、ruff format、mypy（282 檔）通過。vitest：906 通過、1 失敗；`corepack pnpm -C client build`（含 typecheck）通過。
- 失敗的是 `src/ui/floatCardRule.test.ts`（`role=tooltip` 只出現在共用浮動卡元件），抓到 `dev/layoutSmoke.ts`——那是 3-47 加的檔，不在本段變更內，非本段造成，需 PM 另派處理。
- API schema 沒有改（沒有新增或更改回應欄位），OpenAPI 與前端型別不需重產。

## noqa

無。

## 待 PM 決定

1. **0 法力的法術技**：規則允許法術技 `mana: 0`（預算只是沒有折抵）。是否要在工坊強制法術技至少 1 法力、或在檢查面板提示「沒有花費」？本段未動。
2. **「有主角時顯示目前武器實際看的屬性」（追加 5 前半）**：`/api/workshop/options` 只收技能草稿，沒有主角或手上武器資訊。要做需要在 API 加主角／武器參數（會改 OpenAPI），本段只做了沒有主角的版本（依武器資料產生例子）。
3. **欄位與選項的 `description_zh`**：多數原語說明直接取自內容 YAML，是給開發者看的（含 `affects: all`、事件名、引擎術語），共約數十條。本段只掃了名稱與訊息；是否要整批改寫成玩家語氣，或在玩家模式隱藏，請決定（建議由玩法 PM 排內容改寫）。
4. **`dev` 模式的預算明細**：效果名、骨架、形狀在 API 回傳已是中文，`?dev=1` 看不到原始 ID；若要 dev 也看得到，需要在回傳多帶原始 ID 欄位（改 schema）。
5. 進階 YAML 說明裡仍有「YAML」一詞，視為進階模式的名稱，未改。
6. 預先存在的 vitest 失敗（`floatCardRule`，見上）。
