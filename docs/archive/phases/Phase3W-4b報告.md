# Phase 3W-4b 報告｜白板配方補齊

> 依 06 6.34.1、6.34.9（玩法 PM 回覆 3W-4 待決，`02ed66b2`）。實作者：implementer agent。基於 main `fcfeec26`。未 push。

## 1. 做了什麼

| 規格 | 做法 | 位置 |
|---|---|---|
| 1 潮濕／倒地／撞擊例外 | 利用者＝一段帶條件的傷害（`target_on_surface water`、`target_has_status prone`、`target_collided`）；製造者＝弱傷害＋製造（水彈＝傷害＋造水、絆擊＝傷害＋擊倒、頂撞＝傷害＋推 1 格）。各 2 個配方，1～3 階都過預算；不再退回手寫池 | `skill_composer.yaml` active 區；驗證 `whiteboard_check.py` |
| 2 召喚白板 | 1 隻基本召喚物、沒有附帶效果。1 階（創角）：元素之靈（遠程）、骷髏戰士（近戰）；2 階起依關鍵字：火靈、冰靈、雷靈、水精、戰狼、石像、影魅。創角選「召喚物」走 `_whiteboard_starter` 拿到召喚白板 | 同上；`roguelite/start.py` |
| 3 橋接 | 本段不改語意（3W-4 已是「持有的另一個關鍵字／持有不到 2 個時出沒有的」，與玩法 PM 回覆一致） | — |
| 4 2 階起陷阱／姿態／位移；3 階修正型被動、雙屬性縮放 | 陷阱 5（火／冰／雷／暗影／通用捕獸夾）、姿態 6（堅守／焰刃／霜刃及 3 階版）、位移 4（瞬步、影遁、換位、躍步）、修正型被動 5（燃燒／冰凍／標記／中毒／倒地的敵人受你的傷害提高）、雙屬性縮放 6（近戰力量＋智力、遠程敏捷＋智力） | 同上；`statuses.yaml` 6 個姿態狀態 |
| 5 反應位移、被動新核心 | 反應：撤步護體（後退 1 格＋護盾）、反推（推開攻擊者 1 格＋小傷害）。被動：回春（回合開始回血）、戰利護盾（擊倒時得護盾）、追蹤印痕（命中施加標記） | 同上 |
| 6 通用池打開 | 「新方向」格 10%（沿用 `candidates.general_share_permille`）出沒有關鍵字的基礎白板：重擊、橫掃、回氣、護身、振奮，及依階級開放的捕獸夾、姿態、位移、雙屬性（候選 `keywords == ()`） | `whiteboard_candidates.py` |

### 引擎／資料改動

- 沒有改引擎。新種類都用現有原語組合；新增的只有資料：6 個姿態狀態（`statuses.yaml`）、`skill_keywords.yaml` 的 4 條「製造」規則（焰刃／烈焰→點燃，霜刃／冰川→冰凍）。
- `WhiteboardRecipe` 新增欄位 `species`、`min_tier`、`max_tier`、`condition`、`rider`、`skill`（技能欄位覆寫）、`vary`（強度調整前的選項）；`WhiteboardRules` 新增 `generic_keyword`、`exception_keywords`、`summon_ap_cost`、`summon_cooldown_max`、`self_ap_cost`、`dual_min_tier`。
- 白板驗證搬到 `skillgen/whiteboard_check.py`（`whiteboard.py` 仍 re-export）；組合器的新種類路徑是 `_attempt_template`（`whiteboard.py`）。
- 完整模式的組合器不抽白板專用的姿態狀態（`WhiteboardRules.reserved_statuses`），所以完整模式既有種子的輸出不變（`tests/skillgen/test_random_composer.py` 等照舊通過；技能圖示快照不變）。
- 客戶端詞彙表快照 `client/src/battle/fixtures/glossary.json` 重產（多 6 個狀態）。

## 2. 數值與規則上的取捨

- **AP**：召喚白板 AP 1、冷卻 2～4（召喚物點數固定，AP 2 湊不到 70%）；自身位移／互換／自身增益（振奮）白板 AP 1。其餘主動白板仍 AP 2、冷卻 0～2。
- **召喚**：持續輪數是組合器的旋鈕（2～4 輪），再用冷卻與法力的折抵讓不同召喚物落在預算內。
- **位移類單一效果追不上預算**（傳送／互換／躍步／後退固定點數 4／3／2，70% 需要 AP 1 的預算也要 5 點以上；2、3 階更低），所以位移白板與兩個反應位移都帶「一個小補強」（加速、隱蔽、庇護、護盾、小傷害）。驗證器允許「位移核心＋一個非位移的補強」。
- **姿態**：姿態沒有旋鈕，狀態點數必須對上該階預算（2 階 18、3 階 23，70～100%），所以每個姿態做 2 階（14 點）與 3 階（18 點）兩個狀態。元素姿態（焰刃、霜刃）把「普攻改成該元素＋傷害提高」掛在對應關鍵字的「製造」規則上；堅守／鐵壁沒有關鍵字，屬通用池。
- **修正型被動**：幅度用配方 `vary` 的階梯（+14%～+26%）對預算（3 階修正預算 = 6.9 點），所以不是規格例子的 +10%，而是約 +14～26%（「數值照預算」）。
- **雙屬性縮放**：主屬性＝武器大類的主屬性（近戰力量、遠程敏捷），第二屬性＝智力，不跟著主角最高屬性走（retarget 會把第二屬性拿掉）。法器施放者拿不到（只有武器技配方）。
- **白板關鍵字計算**：召喚技自帶「召喚物」關鍵字，有召喚物自己的關鍵字時只算後者（火靈＝點燃）。骷髏戰士自帶倒地，所以創角選召喚物拿到近戰型時，技能同時屬「召喚物」與「倒地」池。
- **稀有度**：沿用 3W-4 的「結構需要的最低稀有度」，雙屬性縮放補 `dual_scaling_min_rarity`。

## 3. 覆蓋表（關鍵字 × 角色階級 × 種類）

配方 id 列出該格做得出的白板（每個配方 4 種子×4 種武器大類測過；刪除線＝該階預算湊不到 70%，候選產生器自動退回其他配方／主動白板）。表由 `compose_whiteboard(recipe_id=…)` 實跑產出。

| 關鍵字 | 種類 | 1 階 | 2 階 | 3 階 |
|---|---|---|---|---|
| ignite | active | fire_bolt、fire_burst、kindle | + summon_fire、fire_trap、flame_stance | + blaze_stance、flame_cut（kindle 湊不到） |
| ignite | passive | ember_touch、flame_brand | 同 1 階 | + burning_exploit |
| ignite | reaction | flame_retort | 同 | 同 |
| wet | active | soak_strike、water_bolt | + summon_sprite | 同 2 階 |
| charged | active | lightning_bolt、spark_burst | + summon_thunder、shock_trap | + arcane_cut、arcane_shot |
| charged | passive／reaction | static_touch／spark_retort | 同 | 同 |
| frozen | active | frost_shard、frost_patch | + summon_ice、frost_trap、frost_stance（frost_patch 湊不到） | glacier_stance、frost_cut 取代 frost_stance |
| frozen | passive | chill_touch | 同 | + frozen_exploit |
| frozen | reaction | frost_retort | 同 | 同 |
| prone | active | ground_finisher、trip_strike | + summon_wolf | 同 2 階 |
| prone | passive | — | — | prone_exploit |
| collision | active | collision_slam、shoulder_charge | + summon_golem | 同 |
| collision | reaction | step_back、shove_off | 同 | 同 |
| marked | active | mark_target | 同 | 同 |
| marked | passive | — | mark_touch | + marked_exploit |
| marked | reaction | mark_retort | 同 | 同 |
| high_ground | active | raise_ground | + vault_step | vault_step（raise_ground 湊不到） |
| concealed | active | shadow_bolt | + summon_shade、shadow_trap、shadow_step | 同 2 階 |
| concealed | passive | shadow_edge | 同 | 同 |
| concealed | reaction | veil_retort | 湊不到 | 湊不到 |
| summon | active | summon_spirit（遠程）、summon_skeleton（近戰） | 同 | 同 |
| poisoned | active | venom、toxic_pool | 湊不到 | 湊不到 |
| poisoned | passive | venom_touch | venom_touch | poison_exploit（venom_touch 湊不到） |
| poisoned | reaction | venom_retort | 湊不到 | 湊不到 |
| 通用（無關鍵字） | active | power_strike、sweeping_blow、second_wind、guard_up、rally | + snare_trap、guard_stance、blink_step、swap_place | + ironwall_stance（取代 guard_stance）、mind_cut、mind_shot |
| 通用（無關鍵字） | passive | regrowth、spoils_ward | 同 | 同 |
| form | — | 無（不可組合，創角給化身） | — | — |

沒有格的組合（例如潮濕被動／反應、倒地反應、撞擊被動）：候選產生器自動改出該關鍵字的主動白板（3W-4 既有行為）。

## 4. 測試

- 新增 `tests/skillgen/test_whiteboard_3w4b.py`（約 260 項）：每個配方 × 階級 × 武器大類做得出且過驗證／白板定義／預算 70～100%／關鍵字對得上；階級表（1 階只有基本與召喚、2 階起陷阱／姿態／位移、3 階起修正型與雙屬性）；例外關鍵字的利用者與製造者；創角選召喚物拿到召喚白板（近戰型與遠程型各有）；2 階依關鍵字挑召喚物；候選只出該階級開放的種類；通用池比例（400 組候選落在 5～16%）；**行為一致**：每個可施放的配方放進戰鬥結算（召喚物出現、陷阱放下、姿態狀態、位移事件、卡片的傷害預覽包住實際結算）；被動與反應能裝備並產生卡片。
- 既有測試調整：`test_whiteboard_3w4.py`（關鍵字／階級語意）、`tests/roguelite/test_keyword_start.py`（潮濕現在有白板，測「池裡沒有」的路徑要把白板起始也關掉）、`tests/content/test_coverage.py`／`tests/skillgen/test_budget.py`／`tests/skillgen/test_validate.py`（登記 6 個姿態狀態）。
- ruff、ruff format、mypy 全過。CLI 快照沒有變動，未使用 `UPDATE_CLI_SNAPSHOTS`。

## 5. 複雜度 noqa

沒有新增 C901／PLR0911／PLR0912／PLR0915 的 noqa。

## 6. 待 PM 決定

1. **位移類與反應位移要帶一個小補強**（加速、隱蔽、庇護、護盾、小傷害）：單一位移的固定點數追不上預算下限。是否接受，或要放寬位移類的預算下限？
2. **姿態每階一個狀態**（2 階 14 點、3 階 18 點）：姿態沒有強度旋鈕，狀態點數固定。之後 3W-2b 的「姿態每招維持費」上線時可改成用維持費調預算，屆時可合併。
3. **近戰召喚物用骷髏戰士**：它自帶倒地，創角選召喚物拿到的近戰型同時屬倒地池；若要純近戰基本召喚物需新增召喚物範本（還要補外觀表 `summon_looks.yaml`，美術 PM 範圍）。鷹隼（標記＋高處兩個關鍵字）沒做成白板。
4. **召喚白板 AP 1、冷卻 2～4**，與「主動白板 AP 2、冷卻 0～2」不同（召喚物點數固定）。同理自身增益（振奮）AP 1，且持續 3～4 輪而不是規格例子的 2 輪。
5. **修正型被動幅度約 +14～26%**（預算決定），非例子的 +10%。
6. **高階仍有湊不到預算的舊配方**（毒系主動、隱蔽反應、毒系反應、凝冰……）與 3W-4 報告第 3 節相同；3W-9 重算數值時一併處理。
7. **潮濕／倒地／撞擊沒有被動（倒地除 3 階外）／反應白板**，標記 1 階沒有被動白板：候選自動改出主動白板。要補請玩法 PM 給配方。
8. 技能名稱「趁勢補刀」等與手寫技能（`skill_ground_finish` 倒地補刀）同名風險：白板名稱取配方名，id 是 `skill_rand_<seed>`，不衝突，但玩家可能同時看到兩招相似的技能。
9. 預設 `max_attempts`=60 對湊不到的配方會空轉；目前候選產生器最多每格嘗試 8 個種子，速度可接受（每組候選約 0.07 秒）。
