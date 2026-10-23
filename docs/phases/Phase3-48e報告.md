# Phase 3-48e 報告：刻印技能實戰沒刻出符文＋卡片／關鍵字不一致

## 根因

1. **刻印對象**：`inscribe` 是 `acts_on: tile` 的原語，`affects` 省略時預設 `tiles`；但原語表沒有限制
   `affects`，所以 `affects: self` 通過驗證，引擎照 `Cast.tiles("self")` 的規則把符文刻在「施放者腳下」
   那 1 格，而不是技能形狀的格子（square3 範圍內的格子）。玩家看到的是形狀範圍內沒有符文，等於沒刻出來；
   `allies`／`enemies`／`all` 同理（刻在該類單位腳下）。
2. **卡片持續輪數**：**無法重現「持續 1 輪」**。卡片文字（`narrative/skills.py::_inscribe`）直接取
   `spec.duration`（省略取 `rune_default_rounds`），使用者的 YAML 渲染出「持續 4 輪」；實戰符文也存在 4 輪
   （施放當輪算第 1 輪，第 4 輪結束消失）。推測使用者看到的「1」是地圖上符文的資訊卡（「剩 N 輪」，client
   `runes.ts`）在符文快消失時的剩餘輪數。已用行為一致測試鎖住卡片＝實戰。
3. **關鍵字**：推導表沒有錯。「製造：標記」是專屬規則（`{effect: inscribe}` → `marked`，符文由
   `on_own_rune`／`detonate_runes` 讀取，兩者都歸「標記」）；「利用：召喚物」是 **通用歸類**
   （`apply_status affects: allies`，召喚物也算友方；6.27.1 既有設計），client 以「通用歸類」樣式顯示並帶
   理由。見待 PM 決定。

## 修法

- 引擎（`engine/skills/primitives/terrain.py`）：`inscribe` 的 `affects` 不是 `tiles` 時不再刻在單位腳下，
  改發 `effect_fizzled`（`effect_kind: inscribe`、`reason: inscribe_needs_tiles`），敘事輸出中文
  「符文只能刻在影響的格子上……沒有刻下」。不再靜默。
- 驗證（`content/skill_primitives.yaml`）：`inscribe` 加 `forbid_affects: [self, allies, enemies, all]`
  （**只加這一條規則**，工坊介面與驗證器的其他刻印限制由 3-48c 處理；若兩邊重複，合併時取其一）。
  `content/skills.py` 的訊息改成中文專用句：「刻印只能刻在影響的格子上，對象要選「格子」（tiles）」。
  工坊選項（`skillgen/options.py`）本來就讀 `forbid_affects`，所以也不會再提供 self 等選項。
- 已存在的技能：工坊技能不在存檔裡（run 存檔只存組合器產生的技能），而是每次開戰由 client 帶
  `custom_skills` 進 `POST /api/battles`，走 `validate_skill`；匯入 YAML 仍能讀進（schema 通過），驗證器
  標示違規、API 回 422 並列出中文原因，讓玩家修。選保守做法（標示違規讓玩家修，不自動改寫，因為改成 tiles
  會改變範圍）；引擎的 `effect_fizzled` 是最後防線。
- `LOG_FORMAT`：`/63` → `/64`（刻印對象行為改變、規則包原語多了欄位）；`runner.py` 文件字串與測試的
  `trpg-battle-log/64` 已一併更新。

## 掃描：其他「只對格子有意義」的原語

| 原語 | `acts_on` | 對象限制 | 結論 |
|---|---|---|---|
| `inscribe` | tile | 本段新增：只能 tiles | 修正 |
| `detonate_runes` | （單位） | 已 `forbid_affects: [self, allies, tiles]` | 沒問題 |
| `create_surface`、`create_obstacle`、`destroy_object`、`raise_terrain`、`lower_terrain`、`topple` | tile | 無；單位類別對象時作用在該單位腳下（原語說明明寫） | 這是設計：表面、障礙、地形對單位腳下也有意義；沒有靜默失敗。**不改**，若玩法 PM 要一併限制為格子再說 |
| `zone`（持續區域） | — | 已 `forbid_affects: [self, tiles]` | 沒問題 |
| `place_trap` | — | 已 forbid | 沒問題 |

## 其他原語的持續輪數顯示（行為一致測試）

`tests/narrative/test_card_duration_matches_engine.py`：

- 符文：duration 1～5 與省略，卡片「持續 N 輪」＝ 符文實戰存在輪數（施放當輪算第 1 輪）。
- 障礙物：duration 1～3，卡片「N 回合後消失」＝ 環境回合倒數 N 次後消失。
- 其他（表面、召喚物、區域）卡片直接取資料欄位；表面／召喚物的既有測試涵蓋，這段未動。

## 新增測試

- `tests/engine/test_inscribe_target.py`：`self`／`allies`／`enemies`／`all` 不刻出符文且有
  `effect_fizzled`＋中文敘事；`tiles`／省略正常刻（remaining 4）；驗證器擋下並有中文原因；舊 YAML 讀得進
  來但被標示違規。
- `tests/skillgen/test_keywords_rune_48e.py`：物理刻印只製造「標記」、無元素關鍵字；友方增益的「召喚物」
  只在通用歸類且有理由；火紋另製造「點燃」。
- `tests/narrative/test_card_duration_matches_engine.py`：見上。

## 驗收

pytest（engine、skillgen、narrative、content、api：5808 通過；`-m "slow or not slow" tests/cli`：148 通過，
含刻印技能重播）、ruff、format、mypy、lint-imports 皆通過。

## 待 PM 決定

1. **關鍵字顯示**：使用者覺得「製造：標記｜利用：召喚物」和這招無關。推導符合 6.27.1（專屬＋通用），不是 bug。
   若要改：(a) 技能已有專屬關鍵字時卡片隱藏通用／暫定關鍵字；(b) 刻印不製造「標記」，另立「符文」關鍵字；
   (c) 維持現狀但卡片說明通用歸類。需玩法 PM 決定。
2. **「持續 1 輪」**無法重現（見根因 2）；請使用者確認看到的是技能卡還是地圖上符文的資訊卡。若是前者，請提供
   截圖或完整請求內容。另可考慮卡片寫「持續 N 輪（含施放當輪）」。
3. **舊工坊技能**：採「標示違規讓玩家修」；若要自動修正成 tiles（會把範圍從 1 格擴成整個形狀，威力不同），
   需 PM 決定。
4. 其他 tile 原語（表面、障礙、地形）是否也限制為格子：現狀允許對單位腳下。
5. 與 3-48c 的重疊：`skill_primitives.yaml` 的 `forbid_affects` 與 `content/skills.py` 的 `_forbidden_affects_message`
   可能和 3-48c 的驗證器規則重複，合併時取其一。
