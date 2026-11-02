# BAL-19b 報告：意志主題＋附帶元素法術

規格：`docs/phases/PhaseBAL計畫.md` 第 12 節 BAL-19b；設計：`docs/design/06-技能.md` 6.10（組合主題）、6.27.4（玩法決定 #110）。

## 做法

- 新增 18 招 **意志縮放** 的法術技（`content/skills/skill_wil_*.yaml`，一招一檔），火、雷、冰、毒、倒地、撞擊各 3 招。
- **主要效果一律是意志主題**（暗影傷害、恐懼、沉默；`skill_scaling.yaml` 的 mind 主題），附帶效果才帶元素或位移，所以照 6.10「主要效果是意志主題、其他效果帶元素才算組合」成立；含元素的 12 招允許範圍是意志或智力（組合主題），倒地、撞擊 6 招只允許意志。沒有純元素傷害為主的招。
- 不改既有技能、不動 `src/`、不加 override、不放進任何 build 或單位。
- 稀有度：普通 2、稀有 13、史詩 3（現有法術技：普通 3%、稀有 74%、史詩 19%、傳說 5%）。階級：T1 15、T2 3（現有法術技 T2 約 17%）。
- 硬控（冰凍）照互斥規則只做單體、冷卻 4（霜咒）；範圍的冰改用「暗影傷害＋造冰面」（墓霜）。

## 新增技能

| ID | 名稱 | 關鍵字 | 元素 | 稀有度 | 階級 | 骨架／AP | 預算比例 |
|---|---|---|---|---|---|---|---|
| `skill_wil_cinder_hex` | 燼咒 | concealed、ignite | shadow | 稀有 | T1 | strike／AP 1 | 88.7% |
| `skill_wil_dread_pyre` | 懼焰 | ignite | shadow | 稀有 | T1 | control／AP 1 | 70.2% |
| `skill_wil_ashen_curse` | 灰燼詛咒 | concealed、ignite | shadow | 史詩 | T2 | area／AP 2 | 96.6% |
| `skill_wil_storm_hex` | 雷咒 | charged、concealed | lightning、shadow | 普通 | T1 | strike／AP 1 | 88.7% |
| `skill_wil_static_silence` | 靜電噤聲 | charged | lightning、shadow | 稀有 | T1 | control／AP 1 | 95.7% |
| `skill_wil_thunder_dread` | 雷鳴驚懼 | charged、concealed | lightning、shadow | 稀有 | T2 | area（連鎖）／AP 2 | 70.2% |
| `skill_wil_frost_hex` | 霜咒 | concealed、frozen | shadow | 稀有 | T1 | control／AP 2 | 72.6% |
| `skill_wil_chill_dread` | 寒懼 | frozen | ice、shadow | 稀有 | T1 | control／AP 1 | 95.7% |
| `skill_wil_grave_frost` | 墓霜 | concealed、frozen | shadow | 史詩 | T1 | area／AP 2 | 81.5% |
| `skill_wil_venom_hex` | 毒咒 | concealed、poisoned | shadow | 普通 | T1 | strike／AP 1 | 81.3% |
| `skill_wil_rotting_whisper` | 腐語 | poisoned | shadow | 稀有 | T1 | control／AP 1 | 89.3% |
| `skill_wil_plague_shade` | 疫影 | concealed、poisoned | shadow | 稀有 | T2 | area／AP 2 | 82.5% |
| `skill_wil_crushing_hex` | 壓頂咒 | concealed、prone | shadow | 稀有 | T1 | displace／AP 1 | 77.0% |
| `skill_wil_shadow_snare` | 影絆 | concealed、prone | shadow | 稀有 | T1 | area／AP 2 | 85.8% |
| `skill_wil_dread_kneel` | 懼伏 | prone | shadow | 史詩 | T1 | displace／AP 1 | 77.0% |
| `skill_wil_shadow_shove` | 影推 | collision、concealed | shadow | 稀有 | T1 | displace／AP 1 | 95.7% |
| `skill_wil_dread_recoil` | 驚退 | collision | shadow | 稀有 | T1 | displace／AP 1 | 82.9% |
| `skill_wil_void_pull` | 虛空牽引 | collision、concealed | shadow | 稀有 | T1 | displace／AP 1 | 95.7% |

全部 `trpg skills budget` 合格、驗證通過；合併 main（含 19a）後 `trpg content check` 335 招通過。

## 交叉表前後（`scripts/skill_balance_audit.py --sections 2`，關鍵字 × 屬性：法術技，意志欄）

| 關鍵字 | 前 | 後 |
|---|---|---|
| ignite | **0** (0+0) | 3 (3+0) |
| charged | **0** (0+0) | 3 (3+0) |
| frozen | **0** (0+0) | 3 (3+0) |
| poisoned | **0** (0+0) | 3 (3+0) |
| prone | **0** (0+0) | 3 (3+0) |
| collision | **0** (0+0) | 3 (3+0) |
| concealed | 9 (7+2) | 21 (19+2) |

元素 × 屬性（法術技，意志欄）：lightning 0 → 3、ice 0 → 1、shadow 12 → 30；fire、poison 仍是 0（見待決 1）。

## 快照與夾具

- `tests/skillgen/fixtures/refactor_3wr2.json`：重產（新增 18 招的強度／升階雜湊；閃現對照的等距 40 招抽樣因 ID 增加而移位，多了 `skill_wild_roar` 等鍵）。
- `client/src/render/fixtures/skill_icons.json`：重產。
- `client/src/battle/fixtures/glossary.json`：跑過匯出腳本，無變動。
- CLI 輸出快照（`tests/cli/snapshots/cli_output_hashes.json`）：合併 main（`b1a9cdde`，含 19a）後以 `UPDATE_CLI_SNAPSHOTS=1`（不加 -n）重產，17 個鍵的雜湊變動（技能列表、技能圖鑑分片等，新增技能所致）。合併時行為快照、skill_icons 也是取 main 版後重產。
- 測試檔：`tests/content/test_coverage.py`（`_BAL19_PREFIXES` 加 `"skill_wil_"`）、`tests/content/test_skill_scaling.py`（內建技能數 317 → 335）。

## 檢查

- content、skillgen、narrative 與 CLI 快照驗證（合併後，`-n 8 --timeout=1800 -m "slow or not slow"`）：6091 passed、14 skipped。
- ruff check、ruff format --check、mypy、lint-imports：通過。
- 重播：`trpg battle --map swamp --seed 7` → `battle replay` 通過（88 動作、313 事件）。

## 待 PM 決定

1. **稽核表的元素欄**：`skill_balance_audit.py` 的元素只算傷害元素（與技能元素），施加燃燒、冰凍、中毒狀態不算火、冰、毒，所以「元素 × 意志」的 fire、poison 仍是 0（關鍵字表已各 3）。照保守做法沒改腳本；若驗收要看元素欄，可讓腳本把狀態對應的元素算進去，或另補帶火／毒傷害的意志招。
2. **concealed 連帶增加**：暗影傷害會推導出「隱蔽」關鍵字，所以 13 招也算進 concealed × 意志（9 → 21）。意志法術幾乎都是暗影，這是既有推導規則的結果；若嫌隱蔽池太大，可改用恐懼／沉默為主要效果的招替換。
3. **稀有度**：普通 2 招（雷咒、毒咒）的比例略高於現有法術技（11% 對 3%）；倒地、冰凍狀態最低稀有，所以那兩類沒有普通招。數值全為初值，未經模擬。
4. **測試清單**：新招沒有放進任何 build 或單位，在 `test_coverage.py` 以 `_BAL19_PREFIXES` 前綴列為由關鍵字池給出（與 19a 同做法）。
