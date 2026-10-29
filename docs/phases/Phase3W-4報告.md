# Phase 3W-4 報告｜白板產生

> 依 06 6.34.1、6.34.9（#69、#72）。實作者：implementer agent。已 merge main（含 #72 補充）。未 push。

## 1. 做了什麼

| 項目 | 位置 |
|---|---|
| 組合器「單一效果」模式 `compose_whiteboard` | `src/trpg/skillgen/whiteboard.py`（新）；配方與參數在 `content/skill_composer.yaml` 的 `whiteboard`，schema 在 `trpg.content.composer_rules`（`WhiteboardRules`、`WhiteboardRecipe`） |
| 白板定義驗證 `whiteboard_problems` / `is_whiteboard` | 同上：階級、種類、單一核心效果（無附帶／條件／修正／變奏／第二段／陷阱／專精／第二縮放）、剛好一個專屬關鍵字、簡單形狀、主動預設費用（AP 2、冷卻 0～2、無每場次數／自身狀態／透支）、預算 70～100% |
| 白板版候選產生器 | `src/trpg/skillgen/whiteboard_candidates.py`；`roguelite/offers.py` 以 `roguelite.yaml` 的 `candidates.whiteboard`（預設 true）切換 |
| 種類比例 70／20／10 | `skill_composer.yaml` 的 `whiteboard.kind_permille`（在 `content/`） |
| 創角起始技能 | `roguelite/start.py` 的 `_whiteboard_starter`（`start.whiteboard`，預設 true）：主動白板、一律 1 階；形態池照舊 |
| 測試 | `tests/skillgen/test_whiteboard_3w4.py`（新）；既有測試調整見第 4 節 |

完整模式（`compose_random_skill`）與完整技能三選一（`candidates.whiteboard: false`）程式碼未動，`tests/skillgen/test_random_composer.py` 等照舊全過，既有種子的組合器輸出沒有改變。

## 2. 設計與取捨

- **配方**：白板 ＝ 一個關鍵字的一個核心效果。共 17 個主動配方（點燃／雷擊／冰錐／暗影彈等傷害型、點燃／淬毒／烙印等狀態型、凝冰／毒沼表面、隆地）、6 個被動（on_hit）、6 個反應。形狀只取單體、單格、十字、3×3。
- **稀有度**：依結構自動取「需要的最低稀有度」當標記（被動至少 epic、表面與推拉類至少 rare）；不影響候選，也不增加強度（符合 #72）。
- **階級（#72）**：候選用角色目前階級（`request.tier` ＝ `offer_tier_by_level`）產生與驗證預算；3×3 要 2 階（`shape_min_tier`，6.34.9）。創角例外：起始技能不論階級一律 1 階。
- **橋接**：白板只有一個關鍵字，無法「同時帶兩個」。橋接候選＝玩家持有的**另一個**關鍵字（非最多的那個）；持有不到 2 個時向外取沒有的並標 `fallback`。
- **LLM 來源**：白板模式下**關閉**（`llm` 參數與通用池都不用；run 的 `llm` 開關打開也不呼叫提議器，有測試）。LLM 整招提議與其餘程式保留給完整技能三選一。
- **沒有配方的關鍵字**：潮濕、倒地、撞擊（單一效果在 1 階就湊不到預算下限 70%：最多約 18%／45%／59%）、召喚物（骨架限手寫）、形態（不可組合）→ 候選與創角退回**手寫技能池**（優先取符合白板定義的，其次任何不高於角色階級的）。創角的 12 個關鍵字全部仍可選。
- **存檔**：`SkillOffer`／`OfferTag` 結構未變，白板候選 `source` 用既有的 `composer`（退回用 `pool`），沒有新增欄位，`trpg-run/10` 不用遞增，舊存檔照舊可讀。API／OpenAPI 無變更。
- 預算調整仍用組合器的 75～95%（落在驗收的 70～100% 內）。

## 3. 高階覆蓋（只量不調）

`whiteboard_candidates` 在「配方湊不到預算下限」時依序退回主動白板、再退回手寫池。六個種子的覆蓋：

- 1 階：全部（主動 7 個關鍵字、被動 5、反應 6）可組出。
- 2 階：缺 主動／淬毒、反應／隱蔽、反應／淬毒。
- 3 階：缺 主動／高處、主動／淬毒、被動／淬毒、反應／隱蔽、反應／淬毒（效果點數不隨階級變大，預算 18／23／… 追不上）。

AI 代打（4 把武器 × 6 種子，24 場）：白板三選一 勝利 3／24，完整技能三選一 勝利 2／24（兩者都低，這個 AI 代打本來就弱；樣本小，僅供參考）。

## 4. 既有測試調整

升級白板後，「AI 代打活到營火」的流程測試與 LLM 來源測試改用完整技能內容庫（`tests/roguelite/helpers.py` 新增 `full_library()`，即 `candidates.whiteboard: false`）：`test_attribute_respec`、`test_skill_growth`、`test_llm_run`、`tests/api/test_attribute_text_api`、`test_skill_growth_api`、`test_run_llm_api`。`test_keyword_start` 起始技能改驗白板；`test_offers` 階級測試拆成完整模式（依等級）與白板模式（依角色階級）。這些流程測試 3W-5 改成靈感點流程時要整理。

測試結果：`tests/roguelite`、`tests/api`、`tests/skillgen`、`tests/content`、`tests/narrative`、`tests/sim`、`tests/llm`、`tests/cli`（155 項）全過；`ruff check`、`ruff format --check`、`mypy` 全過。CLI 快照沒有變動。

## 5. 複雜度 noqa

沒有新增 C901／PLR0911／PLR0912／PLR0915 的 noqa。

## 6. 待 PM 決定

1. **潮濕、倒地、撞擊沒有純單一效果的白板**（預算追不上 70%）。目前退回手寫池。選項：(a) 允許「條件傷害」型（單一傷害效果帶「目標倒地／在水上／受過撞擊」條件，是利用者）；(b) 放寬這幾個關鍵字的預算下限；(c) 維持手寫池。
2. **召喚物**：組合器骨架限手寫，創角例外要求的「1 階召喚白板」目前由手寫池的召喚技代替（不一定符合白板定義）。是否要手寫召喚白板配方？
3. **橋接**的定義：白板一個關鍵字，目前取「持有的另一個關鍵字」。是否要改成別的語意（例如橋接＝帶玩家持有關鍵字、但元素或形態不同）？
4. **高階覆蓋不足**（第 3 節）：高階時弱效果型配方湊不到預算。3W-9 重算技能數值時一併處理，或讓高階白板的效果點數隨階級放大？
5. **被動／反應種類少**：被動核心原語僅 damage／heal／shield／apply_status，反應缺位移類；撞擊、潮濕、倒地都沒有被動／反應配方。
6. **階級表中「2 階起：召喚、陷阱、姿態、位移」**：本段尚未產生這些種類（配方只有 1 階種類）；之後要加配方。
7. 白板模式下通用池（基礎技能，#55）關閉，是否保留一格？
8. 手寫池退回的技能是原階級，高階角色拿到 1 階手寫技能，數值重算留給 3W-9。
9. 玩家介面是否要顯示「稀有度標記」；目前仍用原本的稀有度顯示。
