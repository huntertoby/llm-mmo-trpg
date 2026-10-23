# Phase 3-36a 報告｜狀態圖示

規格：`docs/phases/Phase3計畫.md` 40.1；需求以 `docs/art/戰場效果與狀態圖示.md` 第 4 節「段 1」為準；畫法移植自 `docs/art/sample/fx.js`。只做段 1，段 2（戰場效果）沒有動。

## 做了什麼

| 項目 | 內容 |
|---|---|
| glossary API | statuses 每一項新增 `status_look`（見下表）；只讀 `statuses.yaml`，不動引擎、`LOG_FORMAT` 不變。OpenAPI（`client/openapi.json`、`schema.d.ts`）與前端測試快照 `fixtures/glossary.json` 已重產。 |
| `render/statusIcon.ts`（新） | `GLYPH`（圖樣查表，32 個）、`glyphColor()`、`framePath()`、`paintStatusIcon()`、`sortStatuses()`／`statusRowLayout()`（頭頂列排序與排版）、`bodyEffects()`／`bodyUnder()`／`bodyOver()`（身上特效 5 類）、快取（鍵＝ID＋極性＋控制類別＋元素＋尺寸；字型載入後由 `fontLoad.bump` 清掉）。 |
| `render/skillParts.ts` | `STATUS` 改由 `GLYPH` 產生、`statusColor()` 改走 `glyphColor()`（顏色來自 glossary 欄位）。技能圖示的組裝部件仍是原本的圓形部件框（`statusTile` 不變）。 |
| 外框（只用在狀態圖示本身） | 新增 `statusIconTile()`（`skillIcon.ts`），資訊欄（`Hud.tsx`、`UnitInfo.tsx`）改用它：增益圓、減益圓角方、中性（含姿態）六角；不認得或沒填 polarity → 中性六角。 |
| 頭頂狀態列 | `unitSprite.ts`：14px、最多 3 個，超過時 2 個＋「+N」；排序硬控 → 移動／心智控制 → 持續傷害 → 其他減益 → 增益 → 中性，同級依 ID；倒下不畫。`UnitDraw` 新增 `statusIds`。 |
| 身上特效 | `skip_turn`＋`removed_by_element` 含 fire＝冰塊；其他 `skip_turn`＝頭上星星（靜止，沒做轉動動畫）；`absorbs_damage`＝泡泡；`prevents_move`＝腳下藤蔓；`on_turn_start_damage`＝腳邊元素粒子（最多 2 種）；`concealed` 的小人 alpha 0.55。特效貼圖依「有哪幾類」快取。 |
| 開發用樣張頁 | `client/status-gallery.html`＋`src/dev/statusGallery.ts`：32 個狀態＋不認得的值，以及真的 `BattleRenderer` 畫的 9×6 戰場（不屬於正式 build）。 |

### glossary 新增欄位（`GlossaryEntry.status_look`，只有 statuses 項目有）

| 欄位 | 來源 |
|---|---|
| `polarity` | `polarity` |
| `control_group` | `control_group`（`hard`／`movement`／`mental`／無） |
| `dot_element` | `on_turn_start_damage.element` |
| `skip_turn` | `skip_turn` |
| `removed_by_element` | `removed_by_element`（排序後的字串陣列） |
| `absorbs_damage` | `absorbs_damage` |
| `prevents_move` | `prevents_move` |

pytest：`tests/api/test_views_glossary.py::test_glossary_status_look_covers_all_statuses`（每個狀態、每個欄位都與 `statuses.yaml` 對照）。

## 測試

- vitest：768 → 781（新增 `render/statusIcon.test.ts` 13 項：32 個狀態都有 look 與圖樣且畫得出來；外框形狀對應 polarity；四組原重複圖樣已分開；圖樣顏色；不認得的 ID／polarity／空字串／null；排序與輸入順序無關；0、1、3、4、33 個狀態的排版；身上特效依欄位、新狀態只要欄位對就有特效）。
- `pnpm typecheck`、`pnpm build` 通過；pytest（glossary、openapi 快照、glossary_names）10 項通過；ruff、ruff format、mypy（`src/trpg/api`）通過。
- Python 用主資料夾 `.venv` 的 python，以 `PYTHONPATH=<worktree>/src` 覆蓋可編輯安裝（worktree 沒有自己的 venv）。

## 檢查清單（前 3 項；實機：樣張頁 `status-gallery.html`，1600×900，真的 `BattleRenderer`）

1. **32 個狀態**：增益圓、減益圓角方、中性六角（不死、靈魂連結、蓄力、隱蔽、兩個姿態等）；四組重複已分開——監視＝狙擊鏡／被揭露＝睜眼加放射線；守護＝盾／護衛＝盾＋↓／護盾＝泡泡；強化＝雙箭頭／戰意＝戰旗；狂怒＝爪痕／堅壁＝城垛。不認得的 ID 畫中性六角加名稱第一個字，空字串畫「?」。看到的結果符合。
2. **戰場頭頂列**：中毒、暈眩、加速等在頭頂看得到；7 個狀態的單位顯示 2 個＋「+5」；上下相鄰的兩格，下面單位的狀態列沒有蓋到上面單位的血條；倒下的單位沒有狀態列；召喚物的「灌」徽章與狀態列不重疊。
3. **身上特效**：冰凍＝淡藍冰塊罩全身、暈眩＝頭上黃色星環、護盾＝淡藍泡泡、定身＝腳下藍圈加綠藤（較小，在腳邊）、燃燒／中毒／流血＝腳邊小粒子；隱蔽的單位半透明。看到的結果符合。

截圖：內建截圖工具無法存檔（同 3-35 待決 #1），沒有附圖；美術 PM 驗收時開 `pnpm -C client dev` 後的 `/status-gallery.html` 即可重現。

## `# noqa`

無。

## 待 PM 決定

1. **頭頂列不重複畫 `time_bomb`、`charging`**：這兩個狀態已有帶數字的徽章（右下、左下），狀態列把它們濾掉以免占格。若美術 PM 要照樣張全畫，把 `unitSprite.ts` 的 `statusRow()` 的過濾拿掉即可。
2. **灌注召喚物的狀態列縮成 2 格並右移 9px**：避免和左上「灌」徽章重疊（規格說 3 格；僅限有灌注的召喚物）。
3. **`taunted`（嘲諷）圖樣色是紅（依 polarity）**：樣張把它當心智控制（紫），但 `statuses.yaml` 裡它沒有 `control_group`，前端依欄位走，不特判。要紫色的話得改內容資料（`control_group: mental` 會要求 `save_attr`，屬玩法 PM 決定）。
4. **暈眩星星沒有轉動動畫**（規格允許靜止）；若要轉動需要把身上特效改成逐幀繪製，建議併入段 2 或之後再做。
5. 狀態列圖示中心在格子頂端 +5.5px（規格寫 +1px）：+1px 時圖示下半會蓋住上一格單位的血條（血條底距格子下緣約 2px），所以略往下移；會蓋到單位頭頂一小部分，實機看可接受。
6. 資訊欄的狀態圖示仍經 `tileCanvas` 的圓形裁切（半徑 49），圖示邊長縮到 84 避免六角與方形的角被切掉。
