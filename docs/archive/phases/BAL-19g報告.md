# BAL-19g 報告：同路線找法與創角提示（玩法決定 #110）＋BAL-19 最後驗收

規格：`docs/phases/PhaseBAL計畫.md` 第 12 節 BAL-19g 與「驗收（最後）」；設計 `docs/design/06-技能.md` 6.27.3、6.27.4、6.34.9。

## 1. 同路線找法（A）

- **判定**：`trpg.skillgen.candidates.route_rank(skill, attr, weapon_attrs)` 回傳三級——`ROUTE_MAIN`（①：縮放屬性跟主路線，武器技看手上武器）、`ROUTE_DUAL`（②：雙屬性技能靠第二縮放屬性跟上，6.10）、`ROUTE_OFF`（偏離）。`follows_attr` 改成「不是偏離」，完整版、白板版與 `roguelite/offers.py` 的 `off_route` 共用。BAL-17 的雙屬性武器規則保留（武器的兩個屬性都算主路線；法術只靠第二屬性落在武器屬性內的算雙屬性）。
- **行為變化**：雙屬性 **法術**（第二縮放屬性＝主角最高屬性）以前算偏離，現在算同路線（②）。雙屬性武器技本來就算同路線（3I-3），現在歸到 ②。
- **找法順序**（加深、橋接；`want="same"`）：
  - 完整版 `_Search`：技能池與組合器各自把結果分成「主路線／雙屬性／備選」三格；同一組關鍵字先在兩個來源找主路線，都沒有才取雙屬性（仍算符合），再沒有才當備選。`_first` 照 BAL-17 換下一組關鍵字（③），整串都沒有才放寬屬性（④）。
  - 白板版 `_Maker`：`_compose` 在 `tries` 個種子裡主路線優先、其次雙屬性；擲到被動／反應卻不是主路線時再試主動白板；組合器只有備選時才看手寫池（手寫池也照主路線 → 雙屬性 → 備選分組）。`_first` 同上。
  - 新方向（`want="other"`）不變：要偏離的；雙屬性技能不算偏離，所以新方向不取它。
- **測試**：`tests/skillgen/test_route_order_bal19g.py`（10 個）：三級判定（武器技、雙屬性法術、雙屬性武器）、完整版 ①>②、②在③之前、③在④之前、新方向仍要偏離、白板版同樣順序與等級、`off_route` 等於 `route_rank == ROUTE_OFF` 的索引。

## 2. 創角提示（D）

- **後端**：`trpg.api.attribute_text.route_hint(library, weapon, keywords)`，接在 `POST /api/runs/start-preview` 的新欄位 `route_hint`（`RouteHintOut`：`lean`、`fits`、`text_zh`）。
  - 依選的關鍵字「前期拿得到的技能」（`keyword_supply`：手寫、1 階、非傳說、非形態技、角色 2 階以內可用、這把武器能用、專屬規則帶任一個選的關鍵字）算每個屬性有幾招 `follows_attr`；至少一半跟上的屬性是 `fits`（都不到一半取最多的）。
  - 文字：「你選的關鍵字多半是法術，建議配一些點到心智屬性（智力），或選有武器技的關鍵字」；武器技多時「……多半是武器技，建議配一些點到力量，或選有法術的關鍵字」；法器拿不到武器技，改寫「或選其他關鍵字」。
- **前端**：`client/src/run/routeHint.ts`（`topAttribute`、`routeHintText`）＋`RunNewScreen` 在配點區下方顯示「提示：……（只是建議，不影響開始）」（`data-testid="route-hint"`，黃字）。條件：兩個關鍵字都選了、已配點、配點後最高屬性（同分取六屬性順序在前）不在 `fits`。不擋「開始這一輪」，也不影響「自動配點」。
- **例子**（`route_hint` 實際輸出）：

| 武器＋關鍵字 | fits | 文字開頭 |
|---|---|---|
| 單手劍＋帶電、隱蔽（設計例） | 智力 | 多半是法術，建議心智屬性（智力），或選有武器技的關鍵字 |
| 單手劍＋倒地、撞擊 | 力量 | 多半是武器技，建議力量，或選有法術的關鍵字 |
| 弓＋高處、標記 | 敏捷 | 多半是武器技，建議敏捷 |
| 權杖＋召喚物、點燃 | 意志 | 多半是法術，建議心智屬性（意志），或選其他關鍵字 |
| 魔導劍＋帶電、隱蔽 | 力量、智力 | 多半是法術，建議力量、智力 |

- **測試**：`tests/api/test_route_hint_bal19g.py`（5 個）、`client/src/run/routeHint.test.ts`（3 個）。OpenAPI 與 `schema.d.ts` 重產。

## 3. 統計腳本改看關鍵字表

`scripts/skill_balance_audit.py`：
- 2h「少於 3 招」只列 **關鍵字表**；元素欄另列 2h'（只算傷害元素，僅供參考，不算達標）。
- 新增 2t「BAL-19 補內容目標」：感知／意志法術 × 點燃、帶電、冰凍、中毒、倒地、撞擊，敏捷武器技 × 倒地、高處、帶電、中毒，以關鍵字表判達標（手寫＋模板配方 ≥ 3）；風、聖元素武器技以近戰＋遠程合計列為已知；權杖召喚 0 列為已知；最後列殘留。
- 第 5 節的偏離說明改為 `route_rank`（雙屬性技能不算偏離）。

## 4. 6.34.9 階級門檻確認

表在 `content/skill_budget.yaml` 的 `min_character_tier`（`shapes: {square3: 2, chain: 3}`、`line_length: 6`、`line_tier: 3`）；驗證器 `tier_requirements` 套用，白板組出後經 `validate_skill`（含 `tier_violations`）檢查，組合器在 3 階以下把直線長度上限壓到 5（`composer_parts._shape_param`）。

實測（每個白板配方 × 3 種武器大類 × 角色 1～3 階 × 12 個種子，並把每張升階重配到更高階）：

| 形狀（配方） | 最低角色階級 | 實測 |
|---|---|---|
| 直線長 2～5（炎流、雷槍） | 1 | 1、2 階最長 5 |
| 直線長 6（炎流、雷槍） | 3 | 只在 3 階出現 |
| 錐形（寒息；毒霧只到 1 階） | 1（6.34.9「其餘全部」） | 1～3 階 |
| 環形（迴旋斬、暗影環） | 1（同上） | 1～3 階 |
| 連鎖跳躍（連鎖閃電） | 3 | 只在 3 階（`min_tier: 3`） |
| 3×3（烈焰爆、電爆、水彈、橫掃、烙印 2～3 階；點燃只到 2 階） | 2 | 2～3 階 |

違規 0 件（含升階重配後）。沒有需要修的地方；加回歸測試 `tests/skillgen/test_whiteboard_tier_gates_bal19g.py`（9 個）。

## 5. 最後驗收

完整報表：`docs/phases/BAL-19g/audit_full.md`、`docs/phases/BAL-19g/keyword_element_attr.csv`（`uv run python scripts/skill_balance_audit.py --seeds 50 --jobs 6 --out-dir docs/phases/BAL-19g`）。

### 5.1 偏離審計（白板三選一，12 種開局 × 種子 0～49 × 第 1、2 次升級＝每種開局 100 組）

| 開局 | lv1 平均／最多 | real 平均／最多 |
|---|---|---|
| 劍 力量 prone+collision | 1.00／1 | 1.00／1 |
| 匕首 敏捷 concealed+prone | 0.99／1 | 1.00／1 |
| 戰錘 體質 collision+prone | 0.99／1 | 1.00／1 |
| 弓 敏捷 high_ground+marked | 1.00／1 | 1.00／1 |
| 弩 敏捷 ignite+collision | 1.00／1 | 1.00／1 |
| 火杖 智力 ignite+marked | 1.00／1 | 1.00／1 |
| 雷杖 智力 wet+charged | 1.00／1 | 1.00／1 |
| 權杖 感知 wet+marked | 1.00／1 | 1.00／1 |
| 圖騰杖 意志 summon+ignite | 1.00／1 | 1.00／1 |
| 魔導劍 力量14 charged+concealed | 1.00／1 | 1.00／1 |
| 魔導劍 預設配點 ignite+frozen | 1.00／1 | 1.00／1 |
| 鐮刀 預設配點 concealed+poisoned | 1.00／1 | 1.00／1 |

全部 1200 組：lv1 平均 1.00、real 平均 1.00；加深、橋接偏離 0%，偏離只出在新方向（07 7.2 固定 1 張）。達標線（平均 ≤ 1.1、最多 2）通過。BAL-18 時權杖 1.34～1.37、圖騰杖 1.50～2.00。

### 5.2 工坊預算與內容檢查

- `trpg content check`：499 個檔案、373 個技能通過預算與結構驗證。
- `trpg skills budget --all`：通過 372、違規 0、已知例外 1（`known_budget_exceptions` 的召喚專精）。

### 5.3 重播

`trpg battle --map swamp --seed 7 --log-json` → `trpg battle replay`：88 個動作、313 個事件，一致。

### 5.4 殘留格子（關鍵字表，2t／2h）

- **BAL-19 目標格子全部達標**：感知／意志法術 × 點燃、帶電、冰凍、中毒、倒地、撞擊各 3（手寫）；敏捷武器技 × 倒地 4（2＋模板 2）、高處 4、帶電 8、中毒 5。
- **已知（不算殘留）**：風、聖元素武器技各合計 3（力量 1＋敏捷 2）；權杖（感知）召喚 0。
- **目標以外、關鍵字表仍少於 3 招的格子**（交玩法 PM 參考，不在 #110 範圍）：
  - 武器技：marked × 力量 2；summon × 力量 1、× 敏捷 1（號令型白板）；form × 力量 0、× 敏捷 0（形態沒有武器技，結構使然）。
  - 法術技：wet × 感知 1、× 意志 0；marked × 意志 2；high_ground × 感知 2、× 意志 0；concealed × 感知 1；summon × 智力 0、× 感知 0（已知）、× 意志 1（手寫意志召喚只算 1，其餘召喚在 2g「召喚」種類欄）；form × 智力 0、× 感知 1、× 意志 0（形態是姿態，不算法術技）。
- 元素欄（2h'，只算傷害元素）仍有少於 3 的格子，依玩法 PM 決定不算達標。

## 6. 代決

1. **雙屬性法術改算同路線**：第二縮放屬性＝最高屬性的法術以前算偏離，現在算 ②（不標偏離）。照 6.27.4「② 雙屬性技能」與「`off_route` 用同一個判定」推得。
2. **② 的範圍是「同一組關鍵字」**：①→② 都在同一個關鍵字內，換關鍵字（③）後再照 ①②；不做「跨關鍵字先找雙屬性」。
3. **白板版的手寫池退回**：原本只在組合器做不出白板時才用；現在組合器只做得出偏離的備選時，也先看手寫池有沒有同路線的（同關鍵字 ① 優先於 ④）。被動／反應白板不是主路線時也再試主動白板。
4. **創角提示的判定**：用手寫技能池（1 階、角色 2 階以內）當「關鍵字前期的供給」，不含白板配方（白板的縮放屬性會跟著主角，抽樣才看得出來）；「跟得上」＝至少一半的招跟主路線（`follows_attr`），都不到一半取最多的。法器的替代建議寫「或選其他關鍵字」。只在兩個關鍵字都選了且已配點時顯示；「自動配點並開始」不顯示（自動配點本來就跟起始技能）。
5. **腳本**：達標只算 BAL-19 指定的格子（感知／意志法術 6 種、敏捷武器技 4 種）；其他少於 3 的關鍵字格子列為「目標以外」。

## 7. 待 PM 決定

1. 第 5.4 節「目標以外」的關鍵字格子（wet、high_ground、concealed 的感知／意志法術，marked × 力量武器技等）要不要再排補內容。
2. 創角提示的門檻（一半）與供給範圍（只看手寫池）是否合適；提示文字照設計原句改寫了替代建議（武器技多時「或選有法術的關鍵字」、法器「或選其他關鍵字」）。
3. 前端提示只在開新一輪畫面；首頁單場戰鬥、工坊試玩的開局選擇沒有配點，沒加。

## 8. 檢查

- `ruff check`、`ruff format --check .`、`mypy`（972 檔）、`lint-imports`（9 契約）通過。
- pytest（`-n 8`）：tests/skillgen、roguelite、api、content 5951 passed、14 skipped、2 failed——`test_openapi_snapshot`（已重產後單獨重跑通過）與 `tests/api/test_run_start_api.py::test_dev_packs_endpoint_and_start`（流派名稱出現在文字裡，屬另一個 agent 在修的 19f 測試，本段沒動）。新測試另跑：`test_route_order_bal19g` 10、`test_whiteboard_tier_gates_bal19g` 9、`test_route_hint_bal19g` 5，全過。
- tests/cli（`-m "slow or not slow"`、`-n 8`）：180 passed；行為快照（`refactor_3wr2.json`）與 CLI 雜湊都沒變，沒有重產。
- vitest：1183 個中 2 個失敗（`skillIcon.test.ts`、`statusIcon.test.ts` 狀態圖示，屬另一個 agent 在修的 client 狀態圖示），新增 `routeHint.test.ts` 3 個通過；`pnpm build` 通過。
- 重播一致（5.3）；合併 main（9dfa706c，交件前再確認已是最新）。
