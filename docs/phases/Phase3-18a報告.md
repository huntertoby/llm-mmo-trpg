# Phase 3-18a 完成報告：技能卡減雜與部件說明

分支 `worktree-agent-a61ede26fcefc8570`（從 main `cc9c86d` 分出），未 push、未合併。只動前端與 API 的唯讀欄位（只新增欄位），沒有碰引擎規則、事件 schema、存檔格式。

## 交付內容

| 規格 | 做法 |
|---|---|
| 19.1-1 大圖示小圖模式 | `SkillIconView` 新增 `small` 屬性；`skillIconCanvas`／`iconCacheKey` 帶大小圖旗標。技能卡一律 `small`（浮動卡 48px、一般卡 72px）；複合技能仍是斜切兩半＋接續記號。 |
| 19.1-2 組裝算式 | `render/skillIcon.ts` 新增 `assemblyFormula()`（取代舊 `assemblyTiles`／`AssemblyRow`）：每段一行「骨架＋形狀＋效果」、段間「↓ 接續」、細線後條件與代價（18px 小圓＋「類別：名稱」）。類型、元素、稀有度三塊已拿掉；接續為延遲時不重複寫延遲代價；每個部件裁成 30px 圓、只寫名稱、核心效果白外圈。 |
| 19.1-3 `PartTip` | `ui/PartTip.tsx`（portal 到 body，不被卡片裁掉）＋純函式 `ui/tipState.ts`（開關狀態機與視窗夾位）。滑過顯示、點一下釘住、點外面或 Esc 關閉；也可 Enter／空白鍵。套用處：技能卡（含浮動卡、升級與營火候選卡、英雄面板）、工坊檢查面板與選項小圖（選項在按鈕裡，`pin={false}` 只做滑過）、HUD 狀態列、腳下表面、單位資訊的狀態列。 |
| 19.1-4 緊湊浮動卡 | `SkillCardView compact`：小圖示、較小間距，不寫縮放、專精、設計概念。`SkillBar` 浮動卡改成可接收滑鼠，離開技能按鈕後停留 180ms（`FLOAT_CLOSE_MS`），移進卡片就取消關閉。 |
| 19.1-5 元素配色合一 | `battle/vfxPalette.ts` 新增 `ELEMENT_COLORS`（唯一來源，含主色、副色、圖示的亮色與底色）；`ELEMENT_VFX` 與 `skillGlyphs.ELEMENT_ICON` 都由它產生。`vfx.ts` 沒動，所有顏色數值與改前相同。 |
| 19.1-6 `add_tags`／`on_hit_effects` | 後端 `IconModifierChange.part_ids`（標籤，或效果代碼，帶狀態時 `apply_status:burning`）；前端 `modifierChangePart` 畫專屬圖示並寫名稱（「加上標籤：推擊」「命中後：傷害／灼燒」）。舊資料沒有 `part_ids` 時從 `value` 推。 |
| 19.1-7 代價數值 | 後端 `SkillIcon.cost_values`（`source`、`stacks`、`once`、`delay`）；部件名稱變成「源力 2」「消耗層數 3」「每場 2 次」「延遲 1 回合」。 |
| 19.1-8 狀態列與表面 | `statusTile()`／`surfaceTile()`（說明取名詞對照表的 `description_zh`＋`rules_zh`）；HUD、單位資訊的狀態與腳下表面改用部件圖示＋`PartTip`（元件 `TipGlyph`）。 |
| 19.1-9 | 重產 `client/openapi.json`、`schema.d.ts`、`fixtures/skill_icons.json`。 |

## 驗收（19.2）

1. **vitest**：`corepack pnpm -C client test` 41 檔 466 項全過。
   - 分段（單段、複合兩段、延遲接續不重複）：`render/skillIcon.test.ts`「組裝算式：每段一行…」「單段技能只有一行、沒有接續」「接續是延遲時，代價裡的延遲不重複；代價帶數值」。
   - 類型／元素／稀有度被濾掉：同檔「組裝算式：每段一行…」最後三行 `not.toContain`。
   - `PartTip` 開關：`ui/tipState.test.ts`「部件說明框的開關」（滑過、點擊釘住、再點取消、觸控只點一下、Esc 與點外面）＋「說明框的位置」（上方、翻到下方、不超出視窗）。
   - 元素配色單一來源：`skillIcon.test.ts`「元素配色只有一個來源」（特效的 primary／secondary 與圖示的 accent／dark／light 都等於 `ELEMENT_COLORS`）。
   - 另有：`add_tags`／`on_hit_effects` 部件、代價名稱、狀態與表面部件、大小圖不同快取鍵。
2. **pytest**：`tests/narrative/test_skill_icon.py` 新增 `test_modifier_add_tags_and_on_hit_effects_get_part_ids`、`test_cost_values_follow_the_special_costs`；既有 `test_every_library_skill_derives_a_valid_icon`、`test_random_composer_skills_all_derive_icons`（種子 0–49）仍過；`test_client_fixture_is_current`、`tests/api/test_openapi_snapshot.py` 過。
3. **截圖**（`docs/phases/img/`，瀏覽器為縮小的 800×450，小圓較小；以下高度由 DOM 量測，視窗 1600×900）：
   - `3-18a-float-single.png`：單段（颶風踢）浮動卡，**高 136.5px**。
   - `3-18a-float-composite.png`：複合（蓄力斬：護盾 ↓ 延遲觸發 範圍傷害）浮動卡，**高 184px**。規格目標「現行約 325px 的六成」＝195px，兩者都在內。
   - `3-18a-part-tip-open.png`：釘住的說明框（效果（核心）／護盾）；以 Esc 關閉已實測（`.part-tip-box` 數量 1 → 0）。
   - `3-18a-status-tip.png`：HUD 狀態列「護盾」的說明框（取自名詞對照表）。
   - `3-18a-workshop-partial.png`：工坊組到一半（只選了骨架，形狀還沒選）。
   - `3-18a-skill-card-run-panel.png`：一輪英雄面板展開的技能卡（魔劍斬）。升級與營火候選卡（`OfferPicker`）與它是同一個 `SkillCardView`，但要贏一場戰鬥才會出現，所以沒有單獨截圖（見待 PM 決定 1）。
4. **`uv run python scripts/check.py` 全過**（ruff、format、mypy、lint-imports、pytest、client install／typecheck／test 皆通過）；`corepack pnpm -C client build` 成功（只有既有的 chunk 大小警告）。

## 新增的複雜度 noqa

無。

## 待 PM 決定

1. **升級與營火候選卡沒有單獨截圖**：需要打贏一場才會出現；程式上與英雄面板共用同一元件，已用英雄面板截圖代替。要的話請另派一次實跑。
2. **說明框內文沿用現行 `tip`**：骨架、形狀的說明已改成簡短意義（「技能的骨架：決定這一段怎麼出手」「技能的作用範圍」），但效果原語、條件、觸發的說明仍只是「效果原語」「條件」「反應時機」這類分類字，資訊量不高。要真正的說明需要玩法 PM 提供每個原語的描述（可放 `content/` 並由 `/api/glossary` 帶出）。
3. **緊湊浮動卡拿掉了「縮放」「專精」「設計概念」**（一般卡仍有）：為了達到六成高度。若認為縮放資訊在浮動卡上也要看，可加回（複合技能約再 +30px，仍在 195px 內）。
4. **代價數值的範圍**：`cost_values` 只涵蓋既有的特殊代價（源力、層數、每場次數、延遲）；HP 代價（`hp_percent`）原本就不在 `costs` 清單，這次沒有新增圖示。延遲回合數暫時固定寫 1（複合技能的延遲段沒有可設的回合數欄位）。
5. **舊 CSS 沒有刪**：依「`styles.css` 只在檔尾新增」，舊的 `.asm*` 規則（組裝列）已無元件使用，3-19 合併後可刪。
6. **`PartTip` 在行動面板的狀態列**：規格寫「HUD／行動面板」，目前行動面板沒有狀態列，所以套用在 HUD 與單位資訊（滑過單位的資訊卡）。
7. **工坊選項旁的小圖用 `pin={false}`**（只有滑過說明，不能點釘住），因為它們在可點選的選項按鈕裡，釘住會與選取衝突；工坊檢查面板的算式則完整支援點釘住。
8. 工坊「隨機一個」按鈕在我的實測裡沒有立刻改變草稿（可能原本就需要先清空或到特定步驟），與本段無關，未處理。
9. 舊的 `KIND_NAME`、`RARITY_NAME`（`render/skillIcon.ts`）因類型與稀有度不再是部件而刪除，沒有其他引用。
