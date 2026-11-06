# Phase 3-24b2 完成報告：新開局、候選產生器、開發者起始包、模擬抽樣

> 實作者：implementer（opus）。規格：`docs/phases/Phase3計畫.md` 26.2（含 26.3 的 PM 決定：開局技能池與候選產生器只用「專屬」規則推導的關鍵字）、`docs/design/06-技能.md` 6.27。
> 分支：`worktree-agent-a35d8c21b90e6572f`（從 main 的 `5fa60fc` 分出），未 push、未合併。中途系統中斷過一次，從工作樹現況（2 個檔案的未提交修改）接續。

## 1. Commit 列表

| commit | 內容 |
|---|---|
| `04d3880` | 推導表規則加資料欄位 `grade`（專屬／通用／暫定，原本只寫在註解）；`derive_keywords`、`keyword_pools`、`pool_skills` 加 `exclusive_only`；關鍵字加選填 `actions`（行為紀錄提示） |
| `e23e0fe` | 共用候選產生器 `trpg.skillgen.candidates`（加深／橋接／新方向）＋測試 |
| `9e72b51` | 新開局（武器＋2 關鍵字）、開發者起始包、升級與營火改用產生器、行為紀錄、存檔 `trpg-run/3`、API 與 CLI、OpenAPI 重產 |
| `5aa5041` | `trpg sim keywords`（關鍵字組合抽樣） |
| `9d76b2a` | 前端：開局畫面、開發者選單（`?dev=1`）、三選一卡片標示；截圖 |
| （本報告） | `docs/phases/Phase3-24b2報告.md` |

## 2. 驗收逐條

| # | 驗收項目 | 結果 | 證據 |
|---|---|---|---|
| 1 | 開局確定性 | 通過 | `tests/roguelite/test_keyword_start.py::test_keyword_start_is_deterministic_and_gives_one_skill_per_pool`、`test_default_start_is_deterministic_and_valid`；API 預覽與實際開局一致 `tests/api/test_run_start_api.py::test_preview_matches_the_created_run` |
| 2 | 各池給招 | 通過 | `test_every_keyword_pool_gives_a_starter_for_some_weapon`（14 把武器 × 10 關鍵字：給的招都在該專屬池、與武器相容、是起始技能；每個關鍵字至少一把武器拿得到）、`test_starter_pools_use_exclusive_rules_and_have_three_each`（專屬池每池 ≥ 3 招 1 階）、`test_second_keyword_never_repeats_the_first_skill`、不合法輸入 `test_bad_starts_are_rejected` |
| 3 | 產生器三種候選的定義 | 通過 | `tests/skillgen/test_candidates.py::test_three_candidates_follow_their_definitions[0..5]`（加深＝持有最多、橋接＝兩個已持有、新方向＝沒有；皆以專屬規則檢查）、`test_candidates_respect_weapon_tier_and_exclusions` |
| 4 | 同種子確定 | 通過 | `test_same_seed_gives_the_same_candidates_and_seeds_vary`；roguelite 層 `tests/roguelite/test_offers.py::test_offer_is_deterministic_and_depends_on_the_counter`、`tests/roguelite/test_save.py`（存讀檔續玩逐位元一致，5 種中斷點） |
| 5 | 持有 1 個關鍵字時的退回 | 通過 | `test_one_held_keyword_bridges_outward`（橋接退回「持有的＋新的」，`fallback=True`）；另 `test_no_held_keyword_falls_back_to_new_directions`（持有 0 個）、`test_every_keyword_held_new_direction_falls_back_to_the_least_held` |
| 6 | `trpg run auto` 3 個種子能跑完 | 通過 | `tests/cli/test_run_cli.py::test_run_auto_without_a_start_draws_weapon_and_keywords[1-3]`；手動：種子 1 錘＋召喚物、倒地 → 失敗 3/6；種子 2 斧＋召喚物、點燃 → 失敗 2/6；種子 3 單手劍＋倒地、點燃 → 失敗 4/6（皆跑到一輪結束） |
| 7 | 模擬抽樣模式小量（20 場） | 通過 | `uv run trpg sim keywords --samples 20 --jobs 4`：20 個樣本、20 場全部完成（0 例外／動作上限），我方勝率 50%；摘要見第 6 節。測試 `tests/sim/test_keyword_sample.py`（3 個） |
| 8 | vitest | 通過 | `client/src/run/startFlow.test.ts`（選關鍵字、能否開始、換武器時去掉不可選、卡片標示文字、`?dev=1`）；`flow.test.ts` 補 `tags` |
| 9 | 截圖 | 完成 | `docs/phases/img/3-24b2-start-screen.png`（斧＋點燃、撞擊，兩池起始技能預覽，潮濕標成「斧沒有起始技能」）、`3-24b2-dev-packs.png`（`?dev=1` 才出現的開發者起始包）、`3-24b2-offer-tags.png`（升級三選一：加深／橋接／新方向）。伺服器用 `trpg serve --port 8125`（沒有動 8000）；前兩張用瀏覽器窗格，第三張因窗格被其他 agent 佔用、未顯示，改用 headless Chrome＋CDP（node 腳本，未進 repo） |
| 10 | `check.py` 全過、`pnpm build` 成功 | 通過 | `uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（3832 passed）、client install／typecheck／test（55 檔 578 個）全部通過；`corepack pnpm -C client build`：built |
| 11 | 遊戲不定義流派 | 通過 | 玩家介面與 API：`test_start_options_list_every_weapon_and_keyword`、`test_dev_packs_endpoint_and_start`（開局選項、一輪回應、存檔列表都不含 12 個測試流派名）；主角名一律「冒險者」；CLI 只印起始包 ID `test_run_auto_with_a_dev_pack`；模擬報表 `test_small_sampling_runs_and_reports` |

其他相關測試：`tests/skillgen/test_keywords.py` 新增 3 個（`grade` 與註解一致、專屬推導去掉通用與暫定、`actions` 是基本動作）；`tests/roguelite/test_keyword_start.py` 共 16 個；`tests/api/test_runs_api.py` 改用一般開局並新增 10 個不合法輸入參數。

## 3. 設計摘要

### 3.1 專屬規則

- `content/skill_keywords.yaml` 每條規則有 `grade`（省略＝`exclusive`；`general` 26 條、`provisional` 16 條）。3-24b1 報告寫「通用 22」：我依行尾註解逐行標（潮濕的治療／護盾／淨化／神聖／三種治療類修正共 7 條、召喚物的 12 條友方效果都標通用），差異見待決 #8。
- 專屬起始池（1 階、普通或稀有、主動）：點燃 8、潮濕 4、帶電 8、冰凍 4、倒地 4、撞擊 6、標記 7、高處 7、隱蔽 12、召喚物 3。倒地池由 31 縮成 4（近戰武器技不再撐大）。
- 技能卡的「製造／利用」顯示仍是全部規則（未改 3-24b1 行為）。

### 3.2 新開局（`trpg.roguelite.start`）

- `new_keyword_run(library, weapon, keywords, seed, allocation=None, *, dev_pack=None, skills=())`：武器＝`weapons.yaml` 全部 14 把；關鍵字個數 `roguelite.yaml` 的 `start.keywords`（2）；每個關鍵字 `start/skill/<id>` 串流在「專屬起始池 ∩ 武器相容 ∩ 未選到」中抽一招；池裡沒有時以同串流取組合器種子（指定該關鍵字，最多 `start.composer_tries`＝16 個）補生成技能；仍湊不到拒絕。預設配點全給武器的縮放屬性。
- 主角基礎數值依武器大類（`start.heroes`，比照原本白板戰士／射手／法師），名稱「冒險者」。
- `new_dev_run(library, pack_id, seed)`：開發者起始包（`content/dev_starters.yaml`，12 組武器＋2 關鍵字，可選填指定技能）。
- `default_start(library, seed)`：`trpg run auto` 與模擬抽樣用（`start/weapon`、`start/keywords`，只在該武器有池內相容起始技能的關鍵字中抽）。
- 舊的 `new_run(library, build_id, seed)` 保留給回歸測試、`sim matrix` 與 API／CLI 的 `build` 參數（開發用）；網頁不再提供 build 選單。

### 3.3 共用候選產生器（給之後大世界接）

```python
# trpg.skillgen.candidates（純函式、確定性；roguelite 與大世界都可呼叫）
@dataclass(frozen=True) class CandidateRequest:
    keyword_counts: Mapping[str, int]   # 持有技能的關鍵字分布（keyword_distribution(skills, library)）
    weapon_class: str                   # melee / ranged / focus
    seed: int
    tier: int                           # 候選技能的階級
    behavior: Mapping[str, int] = {}    # 動作類型 → 次數（行為紀錄）
    exclude: frozenset[str] = frozenset()  # 不能出現的技能 ID
@dataclass(frozen=True) class CandidateRules:
    composer_share_permille: int = 500  # 先找組合器的機率
    composer_tries: int = 8
@dataclass(frozen=True) class Candidate:
    kind: Literal["deepen", "bridge", "new"]; keywords: tuple[str, ...]
    skill: SkillDef; source: Literal["pool", "composer"]; fallback: bool

generate_candidates(library, request, rules=None) -> tuple[Candidate, ...]   # 依序加深、橋接、新方向
keyword_distribution(skills, library) -> dict[str, int]                      # 專屬規則，一招每個關鍵字算 1
behavior_weights(library, behavior) -> dict[str, int]
skill_has_keywords(skill, keywords, library) -> bool
```

- 來源：技能池（內容庫手寫技能，階級相符、非傳說、武器相容、未排除）或隨機組合器（`keyword=` 指定第一個關鍵字，再以專屬規則確認全部關鍵字）。
- 行為紀錄：關鍵字的 `actions`（倒地←絆倒、撞擊←推擊、高處←攀跳、標記←瞄準）乘以使用次數：加深在持有數並列時偏向、新方向抽關鍵字時加權（`1 ＋ 分數`）。
- roguelite 接法：`trpg.roguelite.offers.candidate_request(library, run)` 組輸入，種子 `Rng(run.seed).fork("offer/<n>").next_u32()`；`SkillOffer.tags` 記標示。`off_route` 仍照舊標示但不再刻意湊。
- 行為紀錄：`RunState.behavior`，`finish_battle(..., actions)` 累加主角的動作（不含結束回合等管理操作與決定）。

### 3.4 API（只新增欄位與端點）

- `POST /api/runs`：`weapon`＋`keywords`／`dev_pack`／`build` 三擇一（`build` 由必填改選填）。
- `GET /api/runs/start-options`、`POST /api/runs/start-preview`（已選的依順序是實際會拿到的；未選的是「下一個選它」會拿到的；`skill: null` 表示不可選）、`GET /api/runs/dev-packs`。
- `HeroOut.start_keywords`、`HeroOut.dev_pack`；`OfferOut.tags`（`kind`、`label_zh`、`keywords`、`fallback`、`source`）；`HeroOut.build_id` 一般開局為空字串；`SaveSummary.build_name_zh` 改成「斧・點燃＋撞擊」。

### 3.5 CLI

- `trpg run new|auto`：`--weapon W --keywords a,b`、`--dev-pack P`、`--build X`（擇一）；`run auto` 都省略時以種子抽。
- `trpg sim keywords [--samples 20] [--seed-start 0] [--battles 1] [--maps a,b] [--jobs N]`。`builds.yaml` 不動，仍是 `sim matrix` 的回歸範本。

## 4. 存檔版本

- **`trpg-run/2` → `trpg-run/3`**：`RunState` 多了 `start`、`behavior`，`build_id` 可為 `None`，`SkillOffer.tags`。`/1`、`/2` 舊存檔明確拒絕並提示開新一輪（`tests/roguelite/test_save.py::test_wrong_format_and_engine_are_rejected`）。
- `LOG_FORMAT` 未變（戰鬥紀錄結構沒變）。

## 5. 新增的複雜度 noqa

- `src/` 沒有新增任何 `# noqa`。
- 測試 `tests/skillgen/test_candidates.py::_generate` 加 `# noqa: PLR0917`（測試輔助函式，位置參數讓 18 個呼叫處簡短）。

## 6. 模擬摘要（`trpg sim keywords --samples 20`）

20 個樣本（種子 0–19）、各 1 場：我方勝率 50%、0 場未完成。依關鍵字：點燃 50%（8）、潮濕 100%（1）、帶電 33%（3）、倒地 33%（6）、撞擊 60%（5）、標記 50%（2）、高處 33%（3）、隱蔽 57%（7）、召喚物 60%（5）；冰凍 0 場（近戰／遠程的專屬池沒有冰凍起始技能，`default_start` 不會抽到）。依武器大類：法器 50%（6）、近戰 45%（11）、遠程 66%（3）。樣本太少，只證明模式跑得通，不做平衡結論。

## 7. 其他變更

- `take_candidate` 修正：候選是內容庫手寫技能時不放進 `generated_skills`（原本只會有組合器技能）。
- 測試調整：`tests/roguelite/helpers.py` 的 `VICTORY` 改成 `("build_fire", 0)`（候選改變後原本的 `build_banisher` 種子 2 不再贏）；`test_offers.py` 的「三候選含一個偏離路線」改為「加深／橋接／新方向」，生成技能相關測試改找組合器來源的候選；`test_runs_api.py` 主流程改用一般開局。
- `roguelite.yaml` 新增 `start`、`candidates` 兩節；`content/dev_starters.yaml`＋schema `trpg.content.dev_starters`（載入時檢查武器、關鍵字、技能存在）。
- `styles.css` 只在檔尾新增；沒有動修正規則結算與 `render/` 的裝備圖示。

## 8. 待 PM 決定

1. **潮濕在近戰／遠程湊不到起始技能**：專屬潮濕池只有法術（喚潮、驟雨、聖水、導電打擊皆需法器），組合器指定潮濕幾乎做不出專屬潮濕（60 次 1 次）。目前開局畫面把它標成「X 沒有起始技能」不可選；近戰的冰凍、標記與遠程的冰凍靠組合器補生成技能。建議玩法 PM 補 `weapon_req: any` 的潮濕／冰凍／標記 1 階技能。
2. **單場戰鬥的「主角 build」選單仍顯示流派名**（首頁的「開始戰鬥」區，列出 builds.yaml 的「位移流」「火焰流」等）。規格只要求移除一輪開局的流派選單，我沒動；建議改成開發者模式才顯示或改用武器＋關鍵字。
3. **`build` 開局路徑保留**（API `build` 欄位、CLI `--build`、`new_run`）給回歸測試與 `sim matrix`；網頁不提供。是否完全移除請決定。
4. **`offer_size`、`off_route_per_offer`、`offer_max_attempts` 不再使用**（產生器固定三種候選）；欄位保留未刪。偏離路線標籤仍顯示但不再保證有一張。
5. **候選的來源比例**：組合器／技能池各 50%（`composer_share_permille: 500`），組合器每個候選最多 8 個種子；技能池候選可能是被動、修正、反應（非傳說）。數值為初值。
6. **行為紀錄的對應**只有 4 個（絆倒→倒地、推擊→撞擊、攀跳→高處、瞄準→標記）；站位、地形尚未納入（規格允許先只統計動作類型）。
7. **橋接退回的提示文字**：持有兩個關鍵字但找不到同時帶兩者的技能時，也走「持有的＋新的」退回（不只持有 1 個時）。開局兩招若沒有共同技能，第一次升級的橋接常是退回。
8. **通用規則數 26 vs 3-24b1 報告的 22**：差在潮濕的 `shape_to`、`heal_permille` 等治療類修正與召喚物 `intercept` 等是否算通用；我依行尾註解標。請玩法 PM 一併審。
9. **開發者起始包的關鍵字配對**是我依 08 8.21.4.2 的說明挑的（例：鐵壁＝單手劍＋倒地、撞擊；念動＝火焰法杖＋倒地、高處），沒有指定技能（用一般開局規則抽）；需要固定技能可在 `skills` 欄位填。
10. **截圖**：瀏覽器窗格被其他 agent 共用、時常未顯示，第三張改用 headless Chrome＋CDP；前兩張為窗格縮放後的 800 px 寬。
