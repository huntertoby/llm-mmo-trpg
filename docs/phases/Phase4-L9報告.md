# Phase 4-L9 報告：真模型評估

> 實作者：implementer（opus）；日期 2026-10-30；模型 `swift`（Qwen3.8-27B NVFP4，vLLM，`max_model_len` 32768，`enable_thinking=false`，`temperature` 0.7，`max_tokens` 2048）。
> 原始輸出：`docs/phases/4-L9/skills.md`（腳本產出的表格）、`skills.csv`（每題一列）、`skills_errors.csv`（每條回給模型的錯誤一列）、`flash.csv`（閃現每題一列）。CSV 不含 prompt。

## 0. 摘要

1. **這個模型在目前的提議 schema 下不夠用**：照一輪實際出題（升級候選 50 題）**一次通過 10%、重試後累計 28%、退回 72%**（遠超 20% 提醒線）；強制測試 132 題退回 75%；只有「不指定核心、不帶關鍵字」的自由測試達到 75% 通過（common 稀有度 98%）。
2. **主要失敗不是格式，而是「把選填欄位塞滿」**：模型幾乎每題都加 `cost_on_miss`／`cost_overdraft`／`cost_hp`／變奏／條件，而這些欄位在 schema 裡合法、在驗證器裡不合法（失手反噬裡的傷害帶 `explode`／`scaling` 203 次、反噬用 `bleed`／`burning` 73 次、反應技帶 `cost.overdraft` 16 次…）。這類錯誤 **重試三次都改不掉**，因為錯誤 `path` 指錯位置（反噬裡的錯誤被報成 `effects[0]`）。
3. **第二大類是引擎補不起來的數值**：`budget.weak` 121 次，集中在位移／地形／功能型核心（`teleport`、`swap*`、`raise_terrain`、`cleanse`、`apply_status`…），就是 4-L5 待決 #3 的「無旋鈕結構」；`skeleton.secondary_share` 66 次（control 骨架加了傷害，修補後傷害仍占 90% 以上）。
4. **模型會選的原語非常集中**：自由測試被選的效果裡 `damage` 48%、`apply_status` 38%、`create_surface` 8%，其餘 50 個原語合計不到 6%，**35 個原語 0 次**——3C 節「核心由引擎指定」是必要的；但指定冷門核心時通過率掉到 25%，兩者要一起修。
5. **閃現變化提議可用**：退回 7.6%（低於提醒線），但模型給的選項約一半套不上（`flash.not_applicable` 176 次），靠預設來源補位（55%）。
6. **速度與容量沒問題**：每次呼叫 p50 7～9 秒；每題（含重試與命名）p50 16～19 秒、p90 29～35 秒；真實 prompt 2～6k token（估算值高估約 33%），`response_format` strict 1,086 次全被接受。

**建議方向**：先不換模型；**收緊 schema（讓不合法的組合在解碼時就選不到）＋修錯誤路徑＋提示「選填欄位沒必要就不要填」**，預期通過率會大幅提升（見第 6 節）。改完再跑一次本腳本比較；若升級候選仍 < 60%，再試開 thinking 或更大的模型。

## 1. 評估工具（交付項目）

| 檔案 | 內容 |
|---|---|
| `src/trpg/llm/skill_eval.py` | 題目產生（`upgrade_items`／`forced_items`／`free_items`）、平行執行 `run_items`（`ThreadPoolExecutor`，預設 8）、`UsageTransport`（記 token、HTTP 狀態、schema 寫法、結束原因）、`RecordingClient`（記原始回應，事後重新驗證取錯誤訊息）、Markdown 表格與 CSV |
| `scripts/eval_llm_skills.py` | 入口：`--real`、`--suites upgrade,forced,free`、`--upgrade 50`、`--forced-per 3`、`--free 300`、`--baseline 300`、`--workers 8`、`--out-dir`、`--tag`；預設 Mock |
| `tests/llm/test_skill_eval.py` | 8 個 Mock 測試（確定性、核心指定、自由題無核心、平行保序、錯誤明細、`UsageTransport`、百分位數、自由表格）＋ 1 個 `@pytest.mark.llm` 真模型測試 |

出題方式：

- **升級候選**：`make_topic`（與候選產生器同一個函式）——稀有度依權重、核心原語依 run 內配額、輪替選單、主題 100‰、反應題 100‰（取自 `roguelite.yaml`）；角色階級 1→2→3 輪替；半數題目帶一個可組合關鍵字；run 內配額以「前面題目抽到的核心」累積、每 10 題重設（題目不依賴模型回答，所以能平行）。合格的技能再命名（與 `trpg run --llm` 相同：`naming=client`）。沒有給主角屬性與手持武器。
- **強制測試**：開放的核心原語 ＝ 階級 1～3 × common／rare／epic × 主動／反應，任一組合可當核心者（扣掉 `llm_topic.core_exclude`），共 44 個；每個 3 題，階級／稀有度／種類在可行組合中由種子輪替（結果偏 rare／epic：common 只有 1 題，見待決 #3）。
- **自由測試**：`make_topic` 出題後把 `core_primitive` 清掉、不帶關鍵字；輪替選單照常（附帶 6、條件 4）。300 題（單題平均 19 秒，未超過 30 秒，所以沒有縮減）。「選單」＝ 子集的 `primitives`（不指定核心時含全部合法核心＋6 個輪替附帶），「被選」只算通過驗證的技能的頂層效果。
- 牆鐘時間：升級 203 秒、強制 379 秒、自由 771 秒（平行 8）；閃現另跑（單執行緒）。

## 2. 升級候選（50 題，一輪實際出題）

| 指標 | 數值 |
|---|---|
| 一次通過 | 5（10.0%） |
| 重試後通過 | 9（累計 14＝28.0%） |
| **退回** | **36（72.0%）⚠ 超過 20%**（composer 31、workshop 4、pool 1） |
| 平均嘗試 | 2.70 |
| 每題耗時（含命名） | 平均 21.9 秒、p50 18.8、p90 30.1、最大 97.8 |
| 每次呼叫 | p50 6.7、p90 10.6 秒；一次就過的題 p50 6.6 秒 |
| token | 135 次呼叫；prompt 平均 2,003、最大 3,541；輸出平均 249、最大 2,048（`length` 3 次） |
| 命名 | 14 個全部一次成功（平均 2.5 秒） |
| 引擎修補 | `exclusion.no_cooldown_big_area` 18、`budget.weak` 2 |

分組通過率：帶關鍵字 5／27（18.5%）、不帶 9／23（39%）；「自然」主題 0／5；階級 1：2／17、2：6／17、3：6／16；common 5／12、rare 6／26、epic 3／12；反應題 4／6。

錯誤代碼（次數／出現題數／這些題的平均嘗試）：`value_error` 34／24／2.83、`budget.weak` 25／17／2.94、`reference` 24／14／3.00、`keyword.required` 10／7、`skeleton.secondary_share` 10／6、`skeleton.core_beneficial` 6／4、`exclusion.terrain_needs_earth` 4／3、`skeleton.forbidden_affects` 4／3、`json_invalid` 3／2、`on_kill.beneficial` 3／2、`variant.*` 共 16（完整表見 `4-L9/skills.md`）。**出現任一錯誤的題目平均嘗試幾乎都是 3.00**——重試回饋幾乎沒有修好任何錯誤（14 題通過裡只有 9 題靠重試）。

### 2.1 主題一致性抽樣（10 題）

| # | 題目（關鍵字／主題／核心） | 名稱 | 結構 | 判讀 |
|---:|---|---|---|---|
| 10 | collision／—／damage | 碎晶反震 | 反應技／單體／傷害＋推擊 | 合：推擊造成撞擊，名稱與概念都講衝擊 |
| 18 | marked／—／topple | 碎晶壓頂 | 位移／單體／推倒＋傷害＋施加標記 | 合：有標記，名稱對應推倒 |
| 32 | poisoned／—／heal | 晶韻淨化環 | 光環／範圍光環／治療 | 部分合：概念寫「抵禦毒素」但結構只有治療，「中毒」靠條件帶到（通過驗證）；名稱寫「淨化」但沒有淨化效果 |
| 41 | frozen／—／hurl_object | 霜潮・裂界之鑰 | 位移／物件與落點／投擲物件＋冰霜傷害 | 大致合：冰霜元素對應冰凍；「之鑰」與效果無關 |
| 43 | high_ground／—／heal | 巔峰・源晶垂露 | 反應技／單體／治療 | 合：「巔峰」「垂落」呼應高地 |
| 1 | —／—／revive | 晶頻回響 | 光環／單體／復活＋回復資源 | 合（無題目詞），但名稱沒講出復活 |
| 2 | —／—／heal | 晶頻迴響 | 反應技／自己／治療 | 合；與 #1 名稱幾乎相同 |
| 23 | —／—／heal | 晶頻・愈息疊層 | 反應技／單體／治療＋累積層數 | 合 |
| 26 | —／—／cleanse | 晶頻護環 | 光環／範圍光環／淨化＋護盾 | 合 |
| 29 | —／—／shield | 晶頻護環 | 光環／單體／護盾 | 合；**與 #26 同名** |

結論：結構面「帶到關鍵字」由 `keyword.required` 保證，**通過的技能主題一致性良好**（10 題 8 合、2 部分合）。問題在命名：14 個名稱裡 9 個含「晶頻」或「源晶」，有同名（本評估每題獨立命名，正式流程同一個提議器會去重，但多樣性仍差）；試跑時概念出現簡體字「目标」（`concept` 沒有字元集檢查）。「自然」主題 5 題全部退回，無法判讀。

## 3. 強制測試（44 個核心原語 × 3 ＝ 132 題）

| 指標 | 數值 |
|---|---|
| 一次通過 | 8（6.1%） |
| 重試後通過 | 25（累計 33＝25.0%） |
| 退回 | 99（75.0%）⚠ |
| 平均嘗試 | 2.77；每題 p50 19.7、p90 28.6 秒 |
| 引擎修補 | `no_cooldown_big_area` 25、`stun_single_long_cooldown` 7、`budget.weak` 5、`secondary_share` 2 |

每個原語（一次／重試／退回）與主因分類（**說明＝改 `llm_hint` 或提示；格式＝改 schema／子集；數值＝引擎補值或規則**）：

| 原語 | 一次/重試/退回 | 主要錯誤 | 分類與原因 |
|---|---|---|---|
| `damage` | 1/1/1 | value_error、json_invalid | 格式：反噬裡帶旗標 |
| `heal` | 0/1/2 | value_error×8 | 格式：反應題缺 `reaction`、`split_heal` 須 `affects: all` |
| `shield` | 1/1/1 | reference、`shield.status` | 格式：狀態列舉含不可給護盾的狀態 |
| `cleanse` | 1/1/1 | value_error | 格式 |
| `push`／`pull` | 0/0/3、0/0/3 | value_error×9／×7 | 格式：反噬旗標、`kind: reaction` 帶 overdraft |
| `knock_prone` | 0/0/3 | secondary_share、budget | 數值 |
| `shockwave` | 0/0/3 | `terrain_needs_earth`×8、secondary_share | 說明：hint 沒講「改地形要大地元素」 |
| `teleport` `leap` `swap` `teleport_target` `swap_any` | 0/0/3、0/0/3、0/0/3、0/1/2、0/1/2 | budget.weak 4～5／題組 | 數值：位移無旋鈕，補不到 70% |
| `charge_through` | 0/3/0 | value_error | 說明（重試能修好） |
| `shadowstep` | 0/2/1 | value_error | 格式：`landing: behind` 須 `single` |
| `apply_status` | 0/2/1 | budget.weak | 數值 |
| `create_surface` `create_obstacle` | 0/0/3 各 | secondary_share、budget | 數值：附帶傷害占比 |
| `raise_terrain` `lower_terrain` | 0/1/2、0/0/3 | `terrain_needs_earth`、budget | 說明＋數值 |
| `intercept` | 0/0/3 | value_error×8 | 格式：反應題缺 `reaction`／`ally_hit_adjacent` 必須有 intercept |
| `consume_status` | 0/0/3 | value_error、core_share | 格式（`then` 裡帶旗標）＋數值 |
| `grant_ap` `reset_cooldown` `cheat_death` `redirect_damage` `copy_skill` `extra_reaction` | 0/0/3（extra_reaction 0/1/2） | `cap.rule_rewrite_cost`、value_error | 數值：`cap.rule_rewrite_cost` 不在可修清單（4-L8 待決 #7） |
| `hurl_object` | 1/2/0 | — | 良好 |
| `topple` | 0/0/3 | reference、budget | 格式＋數值 |
| `restore_resource` | 0/2/1 | budget.weak | 數值 |
| `steal_buff` `dispel` `reveal` | 0/0/3、0/0/3、0/1/2 | secondary_share | 數值：附帶傷害占比修不下來 |
| `revive` | 0/0/3 | `combo.max_per_skill`、`cap.revive_cost` | 數值：`cap.revive_cost` 可由引擎補冷卻（不在可修清單） |
| `delayed_damage` | 2/1/0 | — | 良好 |
| `summon` | 1/0/2 | value_error | 格式 |
| `zone` | 0/0/3 | value_error×9 | 格式：`anchor: caster` 的形狀限制、`affects` 必填未進 schema |
| `grant_skill` | 0/0/3 | reference×7 | 格式：`skill` 欄位是自由字串，模型填 `skill_id`／`skill_id_placeholder` |
| `inscribe` | 0/0/3 | value_error×7 | 格式：「恰好填 element 或 tag 其一」未進 schema |
| `detonate_runes` | 0/3/0 | value_error | 說明（重試能修好） |
| `sacrifice_summon` | 1/1/1 | value_error、json_invalid | 格式 |
| `blow_surface` `clear_surface` | 0/0/3 各 | secondary_share | 數值 |

通過率低於 2/3 的原語：除 `damage`、`shield`、`cleanse`、`charge_through`、`shadowstep`、`apply_status`、`hurl_object`、`restore_resource`、`delayed_damage`、`detonate_runes`、`sacrifice_summon` 外的 33 個。

## 4. 自由測試（300 題，不指定核心、不帶關鍵字）

| 指標 | 數值 |
|---|---|
| 一次通過 | 127（42.3%） |
| 重試後通過 | 98（累計 225＝75.0%） |
| 退回 | 75（25.0%）⚠ |
| 分稀有度 | common 108／110（98%）、rare 74／122（61%）、epic 43／68（63%） |
| 平均嘗試 | 1.95；每題 p50 15.6、p90 34.7、最大 188 秒 |
| token | prompt 平均 3,784、最大 6,183（選單較大）；`length` 6 次 |

選中率（完整表見 `4-L9/skills.md`；被選占比以 225 個通過技能計，組合器 300 個種子作基準）：

| 原語 | 選單次數 | 被選 | 選中率 | 被選占比 | 組合器占比 |
|---|---:|---:|---:|---:|---:|
| `damage` | 300 | 214 | 71.3% | 47.9% | 30.8% |
| `apply_status` | 300 | 171 | 57.0% | 38.3% | 24.2% |
| `create_surface` | 164 | 36 | 22.0% | 8.1% | 6.2% |
| `knock_prone` | 163 | 9 | 5.5% | 2.0% | 3.2% |
| `shield` | 300 | 4 | 1.3% | 0.9% | 8.3% |
| `intercept` | 179 | 3 | 1.7% | 0.7% | 0.9% |
| `heal`／`pull`／`add_stack`／`restore_resource` | 300／190／165／162 | 2 各 | ≈1% | 0.4% | 6.2%／3.2%／1.7%／0.6% |
| `push`、`inscribe` | 190、155 | 1 各 | <1% | 0.2% | 3.2%、1.1% |
| 其餘 35 個 | 53～276 | **0** | 0% | 0% | 0～2.1% |

平均選中率 3.2%；0 次或低於平均 1/3（1.1%）的：`heal`、`cleanse`、`push`、`inscribe` 與 0 次的 35 個（`raise_terrain`、`reveal`、`consume_status`、`lower_terrain`、`dispel`、`consume_stack`、`create_obstacle`、`steal_buff`、`topple`、`blow_surface`、`clear_surface`、`delayed_damage`、`destroy_object`、`detonate_runes`、`grant_skill`、`hurl_object`、`revive`、`shockwave`、`teleport_target`、`zone`、`enter_form`、`leave_form`、`gamble`、`charge_through`、`leap`、`sacrifice_summon`、`shadowstep`、`summon`、`swap`、`swap_any`、`teleport`、`place_trap`、`dash`、`grant_ap`、`cheat_death`、`extra_reaction`、`redirect_damage`、`reset_cooldown`、`copy_skill`）。

對照：隨機組合器本身也偏 `damage`／`apply_status`（合計 55%），但治療、護盾、推拉、表面都有 3～8%；模型則把它們壓到 1% 以下，**偏好比組合器更極端**。結論：**不指定核心時模型只會做「傷害＋狀態」**，3C 節的核心指定與配額是必要的；也說明自由測試的高通過率主要來自「選簡單的結構」。

`enter_form`／`leave_form` 出現在選單 150／142 次（3C 規定形態不進核心抽籤，但自由題的選單仍有它們；待決 #4）。

## 5. 閃現變化提議

`uv run python scripts/eval_flash_llm.py --real --skills 30 --csv docs/phases/4-L9/flash.csv`（單執行緒，21 分 14 秒；30 個技能 × 不指定／指定類別／第 3 次大變化，能出題的 78 題）。

| 指標 | 數值 |
|---|---|
| 通過（模型湊滿選項） | 29（37.1%），一次通過 8（10.2%） |
| 補位（模型給的部分合格，其餘由預設來源補） | 43（55.1%） |
| **退回**（全由模板補） | **6（7.6%）**，低於 20% 提醒線 |
| 平均嘗試 | 2.67；每題約 16 秒 |
| 錯誤代碼 | `flash.not_applicable` 176、`flash.duplicate` 10 |
| 類別命中 | deepen 62、area 36、element 26、cost 24、bridge 23、combo 20、extend 7 |
| 模板命中（前 8） | major_reshape 22、multi_hit 20、range_plus 18、reshape_shape 16、cost_light 14、keyword_imbue 14、major_intensify 14、major_bridge_imbue 13 |

分題型：不指定 llm 16／補位 14；**指定類別 llm 0／補位 17／退回 1**（指定類別時模型幾乎都提到套不上的模板）；大變化 llm 13／補位 12／退回 5。

大變化名稱抽樣（20 個）品質不錯，名稱與概念對應效果（例：「霜雷連斬：以冰霜頻率凝聚刃氣，連段揮砍間引動帶電震顫…」「濕風錐擊：凝結潮濕空氣為錐形風刃…推擊其退，落地時留下水痕表面」）；同樣有「源晶／晶頻／頻率」高度重複的問題（20 個裡 15 個概念含「源晶」或「頻率」）。

結論：閃現**可用**（退回 7.6%，補位機制兜住），但模型給的選項約一半套不上。建議 **F1**：prompt／schema 的模板列舉只放「這招套得上的模板」（`flash.not_applicable` 由資料預先篩掉；影響高、工作量小～中）；**F2**：指定類別時只列該類別可用的模板（同上）。

## 6. 4.x 待決的實測結論

| 待決 | 實測 | 建議 |
|---|---|---|
| 4-L1 #3 strict 與巢狀 `$ref`／`oneOf` 支援度 | `response_format`（strict）**1,086 次全部 HTTP 200**，沒有退到 `guided_json`；仍有 `json_invalid` 11 次，與輸出撞到 `max_tokens` 2048 的次數（`finish_reason=length` 11 次）相同，推測是模型在約束內重複空白或欄位、被截斷 | 結案：strict 可用。`max_tokens` 可降到 1024（正常輸出最多約 500 token），讓卡住的題目早點失敗（目前一題卡住要 60～180 秒）——**影響**：p90／最大耗時；**工作量**：改設定一行 |
| 4-L4 #3、#5 `token_budget` 是否縮小 | 真實 prompt：升級 2,003（最大 3,541）、強制 2,133、自由 3,784（最大 6,183）；真實 ÷ 估算 ＝ **0.75**（`estimate_tokens` 高估約 33%） | **不需要為了容量縮小**（離 32k 很遠）。是否為了「專注」縮小選單沒有實測證據；強制題（選單較小）通過率反而較低，主因是核心難而不是選單大。建議維持，等 schema 收緊後再比較 |
| 4-L5 #4／4-L4 #6 `skeleton.secondary` 次數 | 只有 3 次（`skeleton.secondary` 1、`variant.v1.skeleton.secondary` 2）；`skeleton.secondary_share` 則有 66 次 | 巢狀才用的原語出現在頂層 **不是問題，不需分開**。真正的問題是 `secondary_share`（見建議 B3） |
| 4-L5 #2 `budget.over` 難修 | `budget.over` 只出現 1 次（頂層）＋變奏裡 19 次 | 頂層已不是問題（4-L8b 的花費旋鈕有效）；變奏裡的 `budget.over` 隨建議 A1 一起解決 |
| 4-L5 #3 無旋鈕結構 | `budget.weak` **121 次**，集中在 `teleport`、`swap`、`swap_any`、`teleport_target`、`leap`、`raise_terrain`、`cleanse`、`apply_status`、`consume_status`、`restore_resource`、`topple` | **需要處理**（建議 B1） |
| 4-L6 #2 schema 列舉不打亂 | 自由測試看不出「排前面就被選」：`damage`／`apply_status` 在 YAML 也排前面，但組合器同樣偏它們；冷門原語不論位置都 0 次 | 不必打亂 schema |
| 4-L6 #8 「自然」主題沒有強制檢查 | 5 題全部退回（錯誤與其他題相同），沒有通過的樣本可判讀 | 等通過率提升後再看 |
| 4-L6 #4／#6／#7、4-L8b #3 費用階梯、#5 反應題 100‰ | 反應題通過 4／6（升級）、14／35（自由），主要錯誤是 schema 讓反應技帶 `cost.overdraft`／`cost.on_miss` 與缺 `reaction` | 反應題比例維持；修 schema（A2） |
| 4-L7 #1 去重、#3 呼叫次數、#4 敘事禁阿拉伯數字、#5 禁字表 | 命名 14／14 一次成功、平均 2.5 秒；沒有因數字或禁字退回；但名稱高度重複（「晶頻」「源晶」9／14） | 字元集與禁字維持；建議在命名 prompt 加「避免重複使用世界觀名詞當詞頭」與帶入 `taken_names`（C3）；`concept` 加簡繁檢查（C4） |
| 4-L8 #2 HP 代價 200‰、#7 傳說源力 | 模型常主動加 `cost_hp`（沒有直接錯誤）；`cap.rule_rewrite_cost` 15 次（規則改寫型原語） | 把 `cap.rule_rewrite_cost` 加進可修清單（B2） |

## 7. 建議

依優先序；「影響」為預期改善，「工作量」為估計。**全部由 PM 決定，本段沒有改任何設定、hint、權重或 schema。**

### A. schema 與錯誤回饋（格式難；最優先）

| # | 建議 | 依據 | 影響 | 工作量 |
|---|---|---|---|---|
| A1 | **錯誤路徑修正**：`cost_on_miss`、`then`、變奏、賭注分支裡的效果錯誤，目前被報成 `effects[0]`（`_check_effect(0, sub)`）。改成帶完整路徑（`cost_on_miss[0]`、`effects[0].then[0]`…） | 203 次「旗標只能用在技能自己的傷害」全部報 `effects[0]`，模型三次都去改錯的地方 | 高：讓重試真的能修 | 小（驗證器包一層 path） |
| A2 | **巢狀位置的 schema 用精簡的效果型別**：`cost_on_miss`、`then`、賭注分支裡的 `damage` 不提供 `explode`／`scaling`／`lifesteal_permille`／`split_heal`／`spread`；反噬的 `apply_status` 列舉排除硬控、跳過回合、持續傷害（`bleed`、`burning`、`stun`…）；`kind: reaction` 的分支不提供 `cost_overdraft`／`cost_on_miss`，且 `reaction` 必填；武器技的 `weapon_req` 只列 melee／ranged | `value_error` 418、`reference` 中反噬狀態 76、overdraft／on_miss 26、reaction 缺 36、weapon_req 12 | 高：估計可消掉一半以上的錯誤 | 中（`proposal.py` 建構器分出巢狀版本） |
| A3 | **其他「恰好其一」「必填」規則進 schema**：變奏 `when` 恰好一種（23 次）、`inscribe` 的 element／tag 其一、`zone` 的 `affects` 必填與 `anchor: caster` 的形狀、`shadowstep landing: behind` 須 `single`、`split_heal` 須 `affects: all`（34 次） | 見第 3 節 | 中 | 中 |
| A4 | **變奏條件的表面列舉** 只放 `surfaces` 表（模型自創 `crystal`、`ground`、`ash`——受世界觀「源晶」影響）；**`grant_skill.skill`** 改成列舉（目前自由字串，模型填 `skill_id_placeholder`） | `reference` 11＋6 次 | 中（`grant_skill` 0→可用） | 小 |
| A5 | **選填欄位提示**：在 system 指令加一句「代價（`cost_*`）、變奏、條件是選填；題目沒要求就不要填，越簡單越容易通過」。或更強：`common` 不開放變奏與 `cost_on_miss`（rare 最多 1 個變奏的限制目前也被違反 13 次） | 錯誤大多來自模型主動加的選填欄位；common 通過 98%、rare／epic 約 60% | 高 | 小（提示）；中（依稀有度收 schema）；**改提示要升 `PROMPT_VERSION`** |

### B. 引擎補值與規則（數值；第二優先）

| # | 建議 | 依據 | 影響 | 工作量 |
|---|---|---|---|---|
| B1 | **無旋鈕結構**（4-L5 #3）：位移／地形／淨化類核心補不到 `budget.weak` 下限 70%。選項：a. 這些骨架的預算下限降低（例如 40%）；b. 補值器允許「往上補附帶效果數值或降冷卻」；c. 子集強制附一個有旋鈕的附帶效果 | `budget.weak` 121 次 | 高（11 個原語從 0% 變可用） | 中；a 只改 YAML |
| B2 | **可修清單加 `cap.revive_cost`、`cap.rule_rewrite_cost`**（引擎補「每場一次」或最低冷卻，和 `exclusion.no_cooldown_*` 同法） | 19 次，`revive`、`grant_ap`、`reset_cooldown`、`cheat_death`、`redirect_damage`、`copy_skill`、`extra_reaction` 全退回 | 中（7 個原語） | 小 |
| B3 | **`skeleton.secondary_share` 的修補修不下來**：control／dispel／steal_buff／surface 類骨架加了傷害，修補後仍 90% 以上。修補應把附帶傷害降到最低骰並在仍超標時回報「移除 damage」 | 66 次，修補只成功 6 次 | 中 | 小～中 |
| B4 | `exclusion.terrain_needs_earth`：`shockwave`、`raise_terrain`、`lower_terrain` 的 `llm_hint` 補一句「改變地形的技能要用大地元素」（說明不清） | 22 次 | 中（3 個原語） | 小（改 YAML hint） |
| B5 | `on_kill.beneficial`（34 次）：對應的說明在 `skill_triggers.yaml` 或擊殺效果的 hint 補「擊殺時只能給自己有益的效果」 | 自由測試第三多 | 小 | 小 |

### C. 其他

| # | 建議 | 影響 | 工作量 |
|---|---|---|---|
| C1 | **暫不換模型**。理由：一次就過的題只要 6～8 秒，結構約束可用，失敗多數是 schema／驗證器不一致（換模型也會踩）。做完 A、B 後重跑本腳本；若升級候選仍 < 60%，再試 `enable_thinking=true`（4-L5 量過約 45 秒且會用光 2048 token，需同時把 `max_tokens` 提到 4096 以上，每題變 3～5 倍慢）或更大的模型 | — | — |
| C2 | `max_tokens` 2048 → 1024（見第 6 節 4-L1 #3） | 中（尾端延遲） | 小（設定） |
| C3 | 命名 prompt：避免重複詞頭、帶入本輪已用名稱（4-L7 #1） | 中（名稱多樣性） | 小～中 |
| C4 | `concept`／`cast_flavor` 檢查簡體字（試跑出現「目标」） | 小 | 小 |
| C5 | **選單大小**：不建議為容量縮小；建議改成「不指定核心的題目不出現」（正式流程本來就幾乎都有核心）。形態原語 `enter_form`／`leave_form` 從自由題選單排除 | 小 | 小 |
| C6 | **一輪等待時間**：每個 LLM 候選平均 22 秒（p90 30 秒），一個升級畫面最多 3 個候選 × 80% 機率，序列呼叫約 50 秒、p90 約 75 秒。建議候選的 3 個 LLM 題目平行請求（本機 `MAX_SEQS=8` 足夠），或在戰鬥中預先生成 | 高（體感） | 中 |

## 8. 延遲分布

| 組 | 每題 p50 | 每題 p90 | 最大 | 每次呼叫 p50／p90 | > 30 秒的題數 |
|---|---:|---:|---:|---:|---:|
| 升級（含命名） | 18.8 | 30.1 | 97.8 | 6.7／10.6 | 6／50 |
| 強制 | 19.7 | 28.6 | 68.9 | 7.1／10.8 | 13／132 |
| 自由 | 15.6 | 34.7 | 188.0 | 8.9／13.5 | 48／300 |

一輪實際出題的等待：目前 `roguelite.yaml` 的 `candidates.whiteboard: true`（3W-4），**升級三選一是白板模式，LLM 來源關閉**；LLM 只在完整技能節點（`whiteboard: false`）與閃現使用。若打開：一輪 5 場＋Boss 約 6 個升級畫面，每畫面序列約 50 秒（見 C6），一輪合計約 5 分鐘的等待；平行化後每畫面約 25～30 秒。

## 9. 待 PM 決定

1. **建議 A1～A5、B1～B5、C2～C6、F1～F2 是否排段**（A1、A2、A5 影響最大；A5 改提示要升 `PROMPT_VERSION`）。
2. **是否換模型／開 thinking**：本報告建議先修 schema 再重跑；換模型需要使用者決定。
3. **強制測試的題目偏 rare／epic**（common 只 1 題，因為從可行組合隨機取 3 個）。若要「每個原語在最容易的稀有度下會不會用」，可改成優先取最低可行稀有度；本次未改，數字可能比正式流程偏低。
4. **自由題選單含形態原語**：`free_items` 直接清掉 `core_primitive`，選單因此含全部合法核心（含 `enter_form`／`leave_form`，3C 規定它們不進核心抽籤）。這只影響評估的選單統計，不影響正式流程。
5. **升級候選沒有帶主角屬性與手持武器**（`hero_attributes`／`held`／`weapon_class` 皆為 None），與實際一輪略有差異；武器相關錯誤（`weapon.incompatible`）因此沒有量到。
6. **評估工具放在 `trpg.llm.skill_eval`**（照 `flash_eval` 的位置）；`real_client_factory` 每題建一個 client（為了分開記 token），所以 auto 模式的「記住被接受的 schema 寫法」每題重來一次——本次 strict 一次就被接受，沒有額外成本。
7. `_error_details` 用原始回應「重新驗證」取得錯誤訊息（`propose_skill` 的 `AttemptRecord` 只存代碼）；結果與迴圈內相同（同 seed、同上下文），但 `LLMBadResponse` 的嘗試沒有原始回應，不會列在 `skills_errors.csv`。

## 10. 驗證

- `ruff check`、`ruff format --check`、`mypy`（新增 3 檔）、`lint-imports`（7 契約）全過。
- `uv run pytest -q tests/llm/test_skill_eval.py -m "(slow or not slow) and not llm"`：8 passed。
- 真模型：`uv run pytest -q tests/llm/test_skill_eval.py -m llm`：1 passed（15.7 秒）。
- 沒有改 `config/llm.toml`、任何 hint、權重或 schema；沒有跑全量測試與 `scripts/check.py`。
