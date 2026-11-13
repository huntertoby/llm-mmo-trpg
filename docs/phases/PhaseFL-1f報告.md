# FL-1f 報告：靈感閃現的大標、下固定區句子、‰ 強度白話換字

依據：玩法 PM 的 FL-1b 附錄 A 填答（2026-11-13，專案 PM 轉達；檔案在 repo 外，229 行）。只換字，版面不變。
#159 四種新轉型（伴生、護主、庇佑、援手）的字沒做（另一段在做）。

## 1. 換了什麼、換了幾條

| 項目 | 條數 | 位置 |
|---|---|---|
| 模板自己的 `headline_zh` | 新填 82 條（小變化 56、大變化 8、大變化補充 12、轉型 6）；FL-1b 已填的 3 條（`range_plus`、`cost_charge`、`cost_light`）和填答一致，沒改。86 個模板都有大標：`support_keyword` 沒有通用句，只寫在 `headlines` 表 | `content/flash_templates.yaml` |
| 「模板 × 關鍵字」`headlines` | 新增 34 列（共 36 列）：製造類 13（`keyword_imbue` 6、`major_bridge_imbue` 7）、加碼類 19（`keyword_exploit` 9、`major_bridge_exploit` 10）、`support_keyword` 2 | 同上 |
| `say_zh` | 18 條：`kill_refund`、`reaction_ward`、`reaction_refocus`、`major_delayed_burst`、`major_kill_chain`、`major_battle_variant`、`shield_thorns`、`shield_mending`、`shield_wet`、`shield_marking`、`shield_charged`、`summon_count`、6 個轉型 | 同上 |
| 元素 `{keyword}` | `element_second`、`followup_element` 用通用句，`{keyword}` 填元素中文名（`Element.display_name`：火焰、冰霜、雷電…） | `src/trpg/api/flash_text.py` `_keyword_zh` |
| ‰ 強度白話 | 取代 FL-1b 暫寫的百分比：前值 1000‰ 寫「原本」，其他寫「N 倍」（小數最多兩位、四捨五入；小於 1 也寫「0.8 倍」） | `src/trpg/api/flash_changes.py` `magnitude_zh` |
| ‰ 強度的欄位名 | 狀態：照實際被強度放大的欄位分「傷害／回復量／幅度／減傷／加成」，同時改好幾種寫「強度」；表面「{表面名}傷害」或「{表面名}效果」；形態「形態加成」；區域裡巢狀的狀態同狀態規則。`label_zh` 不變 | `flash_changes.py` `status_magnitude_suffix`、`_View._magnitude_name` |
| 測試 | 新 `tests/api/test_flash_text_fl1f.py`（20 條：86 模板都有大標、15 條代表性大標、4 條 say、‰ 白話、欄位名分類、燃燒那列「原本 → 1.25 倍」）；改 `test_flash_text_fl1b.py` 一條（原本鎖「其他模板是 None」）；改 `tests/skillgen/test_flash.py` 一條（換掉 major 清單的測試要一併清掉 `headlines`，否則表裡引用大變化模板先報錯） | `tests/` |

快照：預測會變的只有 `test_flash_text_fl1b.py::test_headlines_only_for_the_five_filled_ones`（點燃、多打一下原本鎖 `None`）。實際另多一條 `tests/skillgen/test_flash.py::test_library_checks_major_templates_against_the_evolution_table`（不是快照，是測試把 major 換成一個假模板，`headlines` 引用的大變化模板就不見了）。OpenAPI、後端夾具都沒變（只換字，沒有改 schema）。

## 2. 和填答檔或程式現況對不上的地方

照填答第五節「對照引擎的規則」，每一句都和 `content/skill_evolution.yaml` 的 grafts（`makes`／`uses`）對過。

| # | 哪一格 | 引擎實際 | 處理 |
|---|---|---|---|
| 1 | 製造類 × 隱蔽「出手後你會躲進隱蔽」 | `makes` 是在**打中的格子**造煙霧（`smoke`，2 回合），不是自己躲 | 不列，退回模板通用句「打中時還會造成隱蔽」 |
| 2 | 製造類 × 冰凍「打中時還會凍住敵人」 | `makes` 是造**冰面**（冰面讓人滑倒，不會凍住） | 不列，退回「打中時還會造成冰凍」 |
| 3 | 製造類 × 形態、× 高處 | grafts 沒有 `makes`，這兩個組合不會出現 | 不列 |
| 4 | 加碼類 × 帶電「敵人帶電時」 | 條件是 `cast_tag_this_turn: lightning`（你這回合放過雷電技能），不是敵人帶電 | 不列，退回模板通用句「敵人身上有帶電時，這招多傷一截」——**通用句也對不上這條規則**，見第 3 節第 1 點 |
| 5 | ‰ 欄位名分類（資料和表不同，以資料為準） | 歸一＝每回合回復 → 「歸一回復量」（表：其他）；破誓＝造成傷害降低＋受到傷害增加，兩邊都是「幅度」 → 「破誓幅度」（表：其他）；熔核爆裂、殼縫熔核、寒燼爆裂、界崩＝持有者造成的傷害提高 → 「…加成」（表：爆發傷害）；灌注源晶＝造成的傷害降低 → 「灌注源晶幅度」（表：加成）。這 6 個都是敵人專用狀態，玩家技能幾乎碰不到 | 照資料 |
| 6 | ‰ 欄位名：姿態（表沒列） | 姿態的幅度只放大有利的一邊 | 照資料分：元素架勢、焰刃、霜刃、冰川、烈焰姿態、狂怒「加成」；堅守、鐵壁、堡壘、堅壁「減傷」；大地架勢（少受物理＋加元素）「強度」 |
| 7 | `major_battle_variant` 的 `{地形}` | 選項資料的條件名是「水中、冰上、居高、靠牆、油面、水窪」：放進「站在{地形}上施放時」不通順（「站在水中上」）；油面、水窪是**目標**站的格子、靠牆不是地形 | 一句話一律寫「特定地形」（填答給的退路），沒有照資料填；大標照填答原句 |
| 8 | `support_imbue`「`潮濕` 例外」 | 填答沒寫潮濕要換成什麼字 | 潮濕也用通用句「目標腳下留下潮濕的場地」 |
| 9 | `major_intensify`「造成的{keyword}更持久」 | 這招本來就會造成該關鍵字時是「多 1 回合」；本來沒有時引擎是**補上**製造效果（不是更持久） | 照填答原句 |
| 10 | 大標的 `{n}` | `extend_duration`、`stance_cost_light／heavy`、`trigger_range`、`trigger_cap`、`mod_range`、`mod_duration` 的模板沒寫 `delta`（FL-1b 時 `{n}` 會變成空字） | 這些改法在 `flash_ops` 一次都是 ±1，`{n}` 填 1（`flash_text._DEFAULT_STEP`）；沒動模板的 `delta` |

## 3. 待 PM 決定

1. **加碼 × 帶電的大標**：通用句「敵人身上有帶電時」也和規則（這回合放過雷電技能）對不上。要不要另給一句（例如照規則寫），或維持通用句？（玩法 PM）
2. **製造 × 隱蔽、× 冰凍**：退回通用句「打中時還會造成隱蔽／冰凍」；要照引擎另寫（造煙霧、造冰面）的話請給字。（玩法 PM）
3. **戰場變奏的 `{地形}`**：目前一律「特定地形」；要照資料寫的話，6 個條件名（水中、冰上、居高、靠牆、油面、水窪）需要能放進句子的叫法，且油面、水窪是目標的格子，大標「站在特定地形時」對這兩個也不準。（玩法 PM）
4. **`support_imbue` 的「潮濕例外」**：沒看懂要換成什麼，先用通用句。（玩法 PM）
5. **`major_intensify` 補上製造效果那一種**：「更持久」不準，是否要分兩句。（玩法 PM）
6. **後值剛好 1000‰**：填答只說前值寫「原本」；後值是 1000‰ 時現在寫「1 倍」（實際幾乎不會出現：強度只往上調）。
7. **橋接（`major_bridge_imbue`×潮濕、`major_bridge_exploit`×撞擊）的一句話**：填答只說大標共用，這兩格的 `say_zh` 沒抄 `keyword_*` 那兩句，照差異清單組。要共用就把那兩句也複製過去。
8. **開發頁夾具沒重產**：`client/src/dev/fixtures/flashChoice.json` 還是 FL-1b 的字（`client/` 這段不能碰）；之後跑 `scripts/export_flash_choice_fixture.py` 就會換成新字。

## 4. 平衡疑慮

無（只換字，沒有動數值或改法）。

## 5. 檢查（交件前）

見交件回報（commit 與各檢查結束碼）。沒跑全量 `check.py`、沒做平衡量測或模擬、沒啟動伺服器。

## 開發 PM 裁定

- 接受，已合併。和填答檔對不上的地方，一律以引擎實際行為為準，改用通用句，不編字。接受這個做法。
- 待 PM 決定 1～5 是字句問題（加碼 × 帶電、製造 × 隱蔽／冰凍、戰場變奏的地形叫法、潮濕例外、major_intensify），轉交玩法 PM 一次回覆。回覆後只換字，併進下一段順手做，不另開段。
- 第 6、7 點照現狀：剛好 1000‰ 寫「1 倍」；兩個橋接模板的一句話照差異清單自動組。
- 第 8 點：開發頁夾具 `flashChoice.json` 交由 LF-3 合併 main 後跑 `scripts/export_flash_choice_fixture.py` 重產。

## 第二輪：照玩法 PM 補答（填答第十節）換字

玩法 PM 回覆第 3 節第 1～5 點：五條都是字錯、引擎沒錯，照引擎改寫。開工前已合併 main（含 LF-2，fast-forward）。

| # | 項目 | 改成 | 位置 |
|---|---|---|---|
| 1 | 加碼 × 帶電（`keyword_exploit`、`major_bridge_exploit`） | 大標「這回合放過雷電技能，這招多傷一截」 | `content/flash_templates.yaml` `headlines` +2 列 |
| 2 | 製造 × 隱蔽、× 冰凍（`keyword_imbue`、`major_bridge_imbue`） | 「打中的格子還會冒出煙霧」「打中的格子還會結冰」 | 同上 +4 列 |
| 3 | 戰場變奏 | `say_zh`「{terrain}施放時，這招自動換成另一種打法。」；`{terrain}` 填加上去的那個變奏（`variants` 最後一個）條件的片語：水中「站在水中」、冰上「站在冰上」、居高「站在高處」、靠牆「背靠牆壁」、油面「站在油上」、水窪「站在水窪裡」；沒有資料時填「在特定地形」。大標照第一輪不變 | `flash_templates.yaml`；`src/trpg/api/flash_text.py` `_VARIANT_WHERE`、`_variant_where` |
| 4 | `support_imbue` × 潮濕 | 「目標腳下積一灘水」；其他關鍵字照通用句 | `headlines` +1 列 |
| 5 | `major_intensify` 分兩句 | 原本就會造成：模板的「專精{keyword}：造成的{keyword}更持久」；原本不會、引擎補上製造效果（差異清單有整個新加的效果）：「專精{keyword}：這招開始會造成{keyword}」 | `flash_text.py` `_INTENSIFY_NEW`、`option_headline` |

`headlines` 由 36 列變 43 列。測試 `tests/api/test_flash_text_fl1f.py` 鎖住新句（20 → 32 條：換掉第一輪鎖通用句的 2 條；新增隱蔽、冰凍、橋接帶電、潮濕例外與一般關鍵字、6 個地形片語、intensify 兩種）。快照：預測只有 fl1f 測試裡第一輪鎖的帶電、隱蔽、戰場變奏 3 條會變，實際也只有這些（同一次改測試時換掉）。

### 第二輪待 PM 決定

1. **地形片語和 intensify 的第二句寫在程式**（`flash_text.py` 的常數），沒放進 `flash_templates.yaml`：放進 YAML 要在 `src/trpg/content/flash_templates.py` 加欄位，而這段允許改的檔案不含它。要搬成資料就另排一段。
2. **油面、水窪**：引擎的條件是**目標**站在油上、水上（`target_surface`）。照第十節寫成「站在油上」「站在水窪裡」，沒寫是誰站；大標「站在特定地形時，這招換一種打法」也維持。玩法 PM 說五條都照引擎寫，這兩個片語是否要改成「目標站在油上」，請確認。

### 第二輪檢查

| 檢查 | 結束碼 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0 |
| `uv run lint-imports` | 0（14 kept） |
| `uv run trpg content check` | 0 |
| `pytest -n 8`：fl1f、fl1b、fl1a、`test_flash_api`、`test_world_growth_api`、`tests/content`、`tests/skillgen/test_flash.py`、`test_flash_templates`、`test_openapi_snapshot`、`test_client_fixtures`、`tests/world/test_flash_world.py`、`tests/roguelite/test_flash_run.py`、`test_architecture` | 0（3314 passed） |

沒跑全量 `check.py`、沒做平衡量測、沒啟動伺服器；`client/` 未動（夾具照裁定由 LF-3 重產）。

## 開發 PM 裁定（第二輪）

- 接受，已合併。第十節的五條照引擎行為改寫。
- 待 PM 決定 1：地形片語和 intensify 的第二句先寫成程式常數。內容即資料，之後要搬進 YAML，等下一段動到 `src/trpg/content/flash_templates.py` 時順手做，不另開段。
- 待 PM 決定 2：「油面、水窪」要不要改成「目標站在…」，轉交玩法 PM；回覆後只換字。
