# BAL-19a 報告：感知主題＋附帶元素法術（玩法決定 #110，缺口 1 前半）

規格：`docs/phases/PhaseBAL計畫.md` 第 12 節 BAL-19a；設計 `docs/design/06-技能.md` 6.10（組合主題）、6.27.4（技能供給補齊）。新增 `content/skills/skill_wis_*.yaml` 16 檔；沒有改 `src/`、既有技能與其他資料檔（測試計數與 fixture 的配合修改見「快照與 fixture」）。

## 做法

- 每招的 **主要效果**（第一個帶主題訊號的效果）都是感知主題：標記（`marked`）、神聖傷害、護盾、揭露；元素或機制放在其他效果。依 `content/skill_scaling.yaml` 的推導，這類技能的允許範圍是「感知」或「感知＋智力（組合主題）」，縮放屬性一律填 `wis`。純元素傷害為主的寫法（元素效果排第一）會被推成只看智力，所以沒有用。
- 倒地、撞擊不需要元素：用「神聖傷害／標記／護盾＋擊倒、推、拉」。
- 骨架照工坊結構檢查選（control：狀態為核心、傷害 ≤ 40%；displace：推拉擊倒為核心；strike：傷害 ≥ 60%；area：傷害為核心；aura：只對友方）。
- 命名統一 `skill_wis_*`，避免和 BAL-19b（意志版）撞名。

## 新增技能（16 招）

| ID | 名稱 | 關鍵字（專屬） | 元素 | 稀有度 | 階級 | AP | 骨架 | 預算比例 |
|---|---|---|---|---|---|---|---|---|
| skill_wis_searing_mark | 灼痕印記 | ignite、marked | 火 | 稀有 | 1 | 1 | control | 98.1% |
| skill_wis_sacred_pyre | 聖焰壇 | ignite | 聖（＋火焰地面） | 稀有 | 2 | 2 | area | 87.7% |
| skill_wis_thunder_brand | 雷印 | charged、marked | 雷 | 普通 | 1 | 1 | control | 91.5% |
| skill_wis_storm_aegis | 雷殼守護 | charged | 雷（帶電護盾） | 稀有 | 1 | 1 | aura | 78.8% |
| skill_wis_chain_radiance | 連鎖聖光 | charged | 聖、雷 | 稀有 | 2 | 1 | area（連鎖） | 90.0% |
| skill_wis_rime_mark | 霜痕標記 | frozen、marked | 冰 | 普通 | 1 | 1 | control | 91.5% |
| skill_wis_frost_bloom_prayer | 霜華祝禱 | frozen | 聖（＋冰面） | 稀有 | 1 | 2 | area | 73.6% |
| skill_wis_glacial_judgment | 冰獄審判 | frozen | 聖（＋冰凍） | 史詩 | 2 | 2 | strike | 95.9% |
| skill_wis_venom_mark | 蛇印 | poisoned、marked | 毒 | 稀有 | 1 | 1 | control | 98.1% |
| skill_wis_miasma_sight | 瘴氣探路 | poisoned、marked | 毒（地面） | 稀有 | 1 | 2 | control | 80.0% |
| skill_wis_smite_down | 聖光擊倒 | prone | 聖 | 稀有 | 1 | 1 | displace | 73.3% |
| skill_wis_humbling_mark | 屈膝印記 | prone、marked | — | 稀有 | 1 | 1 | displace | 93.8% |
| skill_wis_sanctified_quake | 聖鐘震地 | prone | 聖 | 史詩 | 2 | 2 | area | 87.4% |
| skill_wis_repelling_light | 驅逐聖光 | collision | 聖 | 稀有 | 1 | 1 | displace | 95.2% |
| skill_wis_rescue_tether | 救援牽引 | collision | — | 稀有 | 1 | 1 | aura | 95.7% |
| skill_wis_banishing_brand | 放逐烙印 | collision、marked | — | 稀有 | 1 | 1 | displace | 96.5% |

- 稀有度：普通 2、稀有 12、史詩 2（法術技全體 普通 5→7、稀有 108→120、史詩 6→8、傳說 8）；階級：1 階 12、2 階 4（法術技全體 1 階 102→114、2 階 25→29）。
- 每招 `uv run trpg skills budget <id>` 合格且「驗證：通過」；`uv run trpg content check`：317 個技能通過預算與結構驗證。

## 關鍵字交叉表（法術技 × 感知，手寫＋模板配方）

`uv run python scripts/skill_balance_audit.py --sections 2`（格子：合計（手寫＋模板配方），`*`＝少於 3）。前＝BAL-18 `audit_full.md` 2 節；後＝本段。

| 關鍵字 | 感知（前） | 感知（後） |
|---|---|---|
| ignite | 1* (1+0) | 3 (3+0) |
| charged | **0** | 3 (3+0) |
| frozen | **0** | 3 (3+0) |
| poisoned | 1* (1+0) | 3 (3+0) |
| prone | **0** | 3 (3+0) |
| collision | **0** | 3 (3+0) |
| marked | 5 (4+1) | 12 (11+1) |
| wet、high_ground、concealed、form | 1*、2*、1*、1* | 不變 |

智力、意志兩列不變（意志列留給 BAL-19b）。法術技 × 感知 6 個目標關鍵字都剛好 3 招；7 招同時帶「標記」，所以標記 5 → 12。

## 快照與 fixture

- `tests/skillgen/fixtures/refactor_3wr2.json`：重產，只新增 16 招的 complete／retier 條目，既有條目雜湊不變。
- `client/src/render/fixtures/skill_icons.json`：重產（`uv run python -m tests.narrative.icon_fixture`），只新增 16 招；random、workshop 與既有技能完全相同。
- `tests/cli/snapshots/cli_output_hashes.json`：`skills_list`、`skills_show_all` 兩個雜湊改變（技能清單多 16 招），其他不變。
- glossary（`tests/api/test_client_fixtures.py`）不受影響，通過。
- 測試修改（不是 `src/`）：`tests/content/test_coverage.py` 加 `_BAL19_PREFIXES = ("skill_wis_",)`（補內容的技能由關鍵字池給出、沒放進 build／單位，依 ID 前綴算已裝備；BAL-19b 可以在 tuple 加 `skill_wil_` 之類），並從 status 允許清單刪掉 `shielded_charged`（雷殼守護是第一招用它的手寫技能）；`tests/content/test_skill_scaling.py` 內建技能數 301 → 317。

## 檢查

- `uv run pytest -n 8 --timeout=1800 tests/content tests/skillgen tests/narrative`：第一次 5 failed（上面那些計數／fixture），修好後重跑失敗的 5 個檔＋`tests/api/test_client_fixtures.py`：361 passed。
- CLI 輸出快照 `UPDATE_CLI_SNAPSHOTS=1 ... -m "slow or not slow"`：1 passed（427 秒）。
- `ruff check`、`ruff format --check`（排除暫存）、`mypy`（940 檔沒有問題）、`lint-imports`（7 契約）通過。
- 重播：`trpg battle --map swamp --seed 7` → `battle replay`：88 個動作、313 個事件，一致。
- `trpg content check`：317 個技能通過預算與結構驗證；16 招各自 `trpg skills budget` 合格、驗證通過（73.3%～98.1%）。

## 待 PM 決定

1. **數值是初值，未經模擬**（跟既有手寫技能一樣）；沒有跑 sim matrix。聖光擊倒（73.3%）、霜華祝禱（73.6%）偏靠下限。
2. **元素靠附帶效果、主效果是感知主題**：聖焰壇、霜華祝禱、冰獄審判、連鎖聖光的元素在第二個效果（火焰／冰面地面、冰凍、雷傷），主效果是神聖傷害；依 6.10「主要效果是感知主題、其他效果帶元素＝組合」寫，縮放屬性填感知。若玩法 PM 覺得「神聖傷害＋元素」太像純元素傷害，可改成標記／護盾當主效果。
3. **倒地、撞擊 6 招沒有元素**（神聖傷害或標記＋擊倒／推／拉），照 6.27.4「倒地、撞擊每種至少 3 招」解讀為不需要附帶元素。
4. 這批技能沒有放進任何 build、單位或開局包，只靠關鍵字池進候選；`test_coverage` 改用 ID 前綴豁免。要不要放進 `dev_starters.yaml` 或權杖開局由 PM 定。
5. 冰獄審判（frozen 硬控）照互斥規則改成單體、冷卻 4。
6. 沒有重跑第 5 節（偏離率），留給 BAL-19 最後的驗收。
