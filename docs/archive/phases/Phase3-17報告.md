# Phase 3-17 報告｜組裝式技能圖示

> 規格：`docs/phases/Phase3計畫.md` 第 18 節；需求 `docs/art/移植需求.md` 5.2、5.3（以 5.3 為準）。
> 分支：`worktree-agent-a2315887d6f2fc2a0`（從 main `20c0d86` 開出）。不改引擎、事件、內容；只新增 `SkillCard.icon` 與 `WorkshopCheck.icon` 兩個顯示用欄位。沒有下載任何素材，所有圖都是 Canvas 2D 程式繪製。

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| `db65ea5` feat: derive assembled skill icon data | 後端 `trpg/narrative/skill_icon.py`（`icon_of`／`skill_icon`、`SkillIcon` 等 pydantic 模型）、`SkillCard.icon`、`WorkshopCheck.icon`、重產 `openapi.json`／`schema.d.ts`、`tests/narrative/test_skill_icon.py`、`tests/api/test_workshop_api.py` 新增一個測試 |
| `e9cab21` feat: assembled skill icon renderer … | 前端 `render/skillGlyphs.ts`（元素、形狀主圖、骨架徽章、外框）、`render/skillParts.ts`（部件庫）、`render/skillIcon.ts`（拆解、繪製、快取、組裝列、工坊選項小圖）、`ui/SkillIconView.tsx`（`SkillIconView`／`AssemblyRow`／`OptionGlyph`）、技能列、技能卡、工坊接線、`vfx.ts` 改讀 `shape_id`、vitest |
| `0b0679b` test: lint fixes | 測試檔的 lint 修正 |
| `24259c9` feat: workshop icon preview layout, 3-17 screenshots | 工坊預覽版面調整、`docs/phases/img/3-17-*.png` |
| （本報告） | `docs/phases/Phase3-17報告.md` |

### 做法摘要

- **後端（純函式，不改引擎）**：`icon_of(skill: Mapping)` 吃技能定義 JSON，**可以缺欄位**（工坊草稿），欄位缺漏、型別錯誤、不認得的值一律退回預設、永不丟例外；`skill_icon(SkillDef)` 是包裝。`skill_card()` 填 `icon`；工坊 `/check` 對草稿一律回傳 `icon`（組到哪一步就有哪些部件，`partial` 為真），所以工坊預覽與技能卡用同一個推導函式。
- **前端部件庫**：`skillParts.ts` 放效果原語 45 種（傳送他人、任意兩者互換與互換位置共用圖示）、狀態 27 種（`stance_*` 共用六角，其餘不認得畫名稱第一個字）、表面 8 種、條件 13 種、代價 6 種、觸發與反應時機 21 種、接續 6 種、修正對象與改變內容各一組；不認得的部件畫「?」。`KNOWN_PARTS` 匯出，vitest 對照 `content/` 檢查沒有漏。
- **組裝**：`partsOf(icon)` 是唯一的拆解函式（核心效果＝第一個非單純傷害的效果、效果列最多 4 個、複合斜切兩半、修正主圖＝改造對象、被動／反應主圖＝觸發時機）；`paintSkillIcon` 畫圖（邊長 ≤ 40px 自動小圖：只畫元素、形狀、核心效果、外框）；`assemblyTiles` 產生組裝列方塊，順序與浮動說明格式照 5.3。
- **快取**：圖示鍵＝`icon` 的穩定序列化（鍵排序）＋尺寸（`iconCacheKey`），同組合共用一張離屏 canvas（上限 300 張，先進先出）；組裝列小圖鍵＝部件 id。
- **接線**：
  - 技能列：大格按鈕左側 40px 圖示（按鈕高 42 → 48px），被動／反應／姿態／修正的小圓鈕改畫 28px 圖示（沒有 `icon` 的舊資料仍用首字）。
  - 技能卡（`SkillCardView`）：標題旁 72px 圖示＋「組裝列」；因為技能列浮動卡、升級候選、營火候選、主角技能清單、工坊預覽都共用這個元件，所以全部一次到位。
  - 工坊：「即時檢查」面板最上方「技能圖示（每完成一步，多一個部件）」＝96px／40px／28px 圖示＋組裝列；每一步的選項（骨架、形狀、條件、時機、效果、狀態、表面、元素）旁有小圖。
  - `vfx.ts`：`shapeIdOf(card, segment)` 讀 `icon.segments[segment].shape_id`；複合技能第二段（`skill_followup` 事件，帶 `skill_id`）讀 `segments[1]`（原本第二段只能靠格子推斷）；中文名對照表 `SHAPE_NAMES` 保留，只在卡片沒有 `icon` 的舊資料時當最後退回。

## 2. `icon` 欄位結構

```text
SkillIcon {
  kind: str              # active|reaction|passive|stance|modifier（不認得 → active）
  rarity: str            # common|rare|epic|legendary（不認得 → common）
  elements: [str]        # 效果（含複合第二段）上的 element，依序去重；沒有時取 tags 的第一個元素；可為空
  weapon_req: str        # melee|ranged|focus|any（不認得 → any）
  segments: [IconSegment]   # 1 段；有 followup 時 2 段
  link: str | null       # followup.when（after_move 等；沒寫 when 時為 after_move）
  condition: { id, status? } | null   # 技能條件；沒有時取第一個效果（含第二段）上的條件
  costs: [source|gamble|self|stacks|once|delay]   # 只列特殊代價，固定順序；法力與冷卻不列
  trigger: str | null    # 被動 trigger.event 或反應 reaction.event
  modifier: { applies_to: {…只列有填的}, changes: [{ key, value }] } | null   # 空值、false 的改變不列
  partial: bool          # 新增：工坊草稿還沒有形狀或沒有效果（修正技能除外）
}
IconSegment { skeleton, shape_id, range: int|null, elements: [str], effects: [IconEffect] }
              # shape_id 草稿還沒選時為 null；range 為武器射程時 null；elements 為新增（這一段自己的元素）
IconEffect  { type, status?, surface?, condition? }
```

與 5.3 的差異：只多了 `partial` 與 `segments[].elements` 兩個欄位（工坊半成品的「未選」中性色、複合第二段換底色需要），其餘照 5.3；`shape_id` 允許 `null`（草稿）。

## 3. 部件對照表

| 部件類別 | 資料來源 | 位置（大圖） | 小圖（≤ 40px） | 圖示庫 | 不認得時 |
|---|---|---|---|---|---|
| 元素 | `icon.elements[0]`（第二元素為斜向色帶） | 底色＋紋理；左上元素標誌 | 底色 | `ELEMENT_ICON` 9 種（配色鍵與 `ELEMENT_VFX` 相同） | 紫色六角預設；工坊未選＝中性灰 |
| 形狀 | `segments[].shape_id`（單體另看 `range`／`weapon_req`） | 中央主圖 | 有 | 13 種形狀主圖（飛行物、揮砍月牙、增益目標、光束、扇形、九宮格×3、連鎖、指定格＋召喚／陷阱、友軍圓頂、丟箱弧線、兩人互換） | 自身光環；草稿未選＝虛線圈 |
| 效果原語 | `segments[].effects[]` | 底部一排，最多 4 個，核心大圓放第一個 | 只有核心（右下大圓） | `EFFECT` 45、`STATUS` 27（＋姿態通用六角）、`SURFACE` 8 | 狀態：名稱第一個字；其他：「?」 |
| 條件 | `icon.condition` | 左下 | 不畫 | `COND` 13（`target_has_status` 帶狀態圖示） | 「?」 |
| 特殊代價 | `icon.costs` | 右上（第二個疊在下方小一號） | 不畫 | 源力、賭注、自傷、消耗層數、每場一次、延遲 | 「?」 |
| 骨架 | `segments[0].skeleton` | 右下徽章 | 不畫 | 14 種 | 空心圓 |
| 技能類型 | `icon.kind` | 外框形狀（主動圓角方、反應盾、被動圓、姿態六角、修正齒輪） | 有 | `framePath` | 圓角方 |
| 稀有度 | `icon.rarity` | 外框顏色；史詩、傳說加內框 | 有 | `RARITY_COLOR` | 灰 |
| 複合接續 | `icon.link` | 切線中央 | 有 | `LINK` 6 種 | 「接著做」箭頭 |
| 觸發／反應時機 | `icon.trigger` | 被動、反應的主圖 | 有 | `TRIG` 21 種 | 「?」 |
| 修正 | `icon.modifier` | 主圖＝`applies_to`；底部＝`changes` 每個鍵 | 主圖＋第一個改變 | 對象 5 類（所有技能、所有攻擊、普通攻擊、標籤、動作）、改變 11 種 | 「?」 |

## 4. 驗收條件逐條

| # | 條件 | 結果 | 證據 |
|---|---|---|---|
| 1 | 後端推導 pytest：所有內容庫技能（含手寫、隨機 50 個種子、工坊示範）推導成功且符合 schema；複合技能兩段；未知效果原語、狀態、表面、條件給預設 | 通過 | `tests/narrative/test_skill_icon.py`：`test_every_library_skill_derives_a_valid_icon`（152 個技能：JSON 往返、`shape_id` 必在 `skill_shapes.yaml`、段數＝followup 有無）、`test_random_composer_skills_all_derive_icons`（種子 0–49）、`test_workshop_drafts_get_more_parts_with_every_step`（打擊、位移、修正三條示範的每一步）、`test_composite_skills_have_two_segments_and_a_link`、`test_unknown_primitives_statuses_surfaces_and_conditions_pass_through`、`test_garbage_input_never_raises`；`tests/api/test_workshop_api.py::test_check_endpoint_returns_an_icon_even_for_partial_drafts` |
| 2 | vitest：部件庫退回、組裝順序、快取鍵、`vfx.ts` 讀 `shape_id` | 通過 | `client/src/render/skillIcon.test.ts`（對照 `content/` 的原語、狀態、表面、條件、觸發與骨架都有圖示；未知部件走預設且 `draw` 不丟例外；152 個技能＋隨機 50 個＋工坊每一步的半成品（大圖、小圖）都畫得出來；核心效果與最多 4 個；組裝列順序；快取鍵穩定、同組合共用）；`client/src/battle/vfx.test.ts` 新增 5 個（`shape_id` 優先、未知／未選回 null、第二段讀 `segments[1]`、舊資料第二段仍由格子推斷、單體遠近仍看距離） |
| 3 | 截圖 `docs/phases/img/3-17-*.png`：技能列、技能卡組裝列、工坊組到一半與完成、升級候選、複合技能兩段斜切 | 通過（見下） | 九張，見第 7 節 |
| 4 | `check.py` 全過、`pnpm build` 成功 | 通過 | `uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest、client typecheck／test 全部通過（vitest 40 檔 432 個）；`corepack pnpm -C client build` 成功 |

另：`tests/narrative/test_skill_icon.py::test_client_fixture_is_current` 保證前端 vitest 用的真實圖示資料 `client/src/render/fixtures/skill_icons.json`（內容庫全部技能、隨機 50 個、工坊三條示範的每一步）與後端推導一致；重產指令 `uv run python -m tests.narrative.icon_fixture`。

## 5. 複雜度 noqa

沒有新增 `noqa`（`src tests scripts` 內 `noqa` 行數 187 → 187）；後端新檔未超過 C901／PLR 上限。

## 6. 修改既有測試期望值

沒有修改任何既有期望值。`shapeIdOf` 新增可省略的第二個參數；既有的「中文名對照」測試因卡片沒有 `icon` 仍走退回而照舊通過。新增的 vitest 與 pytest 見上。

## 7. 截圖

瀏覽器實測用 `uv run trpg serve --port 8775`（測完已關閉）。內建瀏覽器面板實際只有約 942×404，設成 1600×900 時畫面被縮成 800×450，圖示太小看不清，所以除了 1600×900 的整體畫面，其他是用面板原尺寸加頁面縮放（CSS `zoom`）拍的近照；兩種都放在 `docs/phases/img/`。升級與營火畫面是用 `auto_play` 產生存檔（放在被 git 忽略的 `saves/`，拍完已刪）再從首頁「讀取」。

| 檔案 | 內容 |
|---|---|
| `3-17-battle-1600x900.png` | 1600×900 的戰鬥畫面（位移流，技能列有圖示） |
| `3-17-skill-bar.png` | 技能列近照：6 個大格（40px 圖示＋名稱＋代價，含複合的躍擊震地）、右側被動／反應／姿態／修正的 28px 小圖示（四種外框形狀） |
| `3-17-composite-assembly.png` | 躍擊震地（複合）卡片的組裝列：類型、骨架、元素、形狀、核心效果「跳躍」、接續「移動後觸發」、第二段骨架／形狀／效果、稀有度 |
| `3-17-workshop-partial.png` | 工坊組到一半（骨架、形狀、兩個效果；還沒有條件、代價）：96／40／28px 圖示與 7 塊部件 |
| `3-17-workshop-complete.png` | 工坊完成（加上條件「居高臨下」、代價「每場一次」、史詩）：圖示左下條件、右上代價、史詩內框，組裝列 11 塊 |
| `3-17-workshop-card.png` | 工坊完成後的技能卡片預覽（圖示＋組裝列＋文字） |
| `3-17-levelup-offers.png` | 升級三選一候選卡（風・打擊、暗影・光環等，各有圖示與組裝列） |
| `3-17-campfire-offers.png` | 營火重骰候選卡（含傳說「規則改變」，右上有源力與每場一次兩個代價） |
| `3-17-composite-split.png` | 複合技能兩段斜切：左上＝第一段（指定格、跳躍）、右下＝第二段（十字、傷害、擊倒），切線中央接續記號，右下小圖 40／28px 仍可辨識 |

## 8. 待 PM 決定

1. **欄位比 5.3 多兩個**：`SkillIcon.partial` 與 `IconSegment.elements`（工坊未選的中性色、複合第二段不同元素換底色需要）；`shape_id` 允許 `null`（草稿）。是否接受，或要改成別的表達。
2. **元素配色重複一份**：`ELEMENT_ICON`（底色深淺與亮色，取自樣張）與 `battle/vfxPalette.ts` 的 `ELEMENT_VFX` 是兩張表，只用 vitest 保證鍵相同；若要真正「只有一份」需要決定亮色／暗色如何從 `ELEMENT_VFX` 推導。
3. **中文名放前端靜態表**：效果原語、條件、觸發的名稱在 `skillParts.ts`（`EFFECT_NAMES` 等），狀態與表面名稱用 `/api/glossary`；vitest 對照 `content/` 保證沒漏，但改名時要兩邊改。若要單一來源，可把原語、條件、觸發加進 glossary API。
4. **戰場上的狀態徽章、單位資訊的狀態列、表面說明尚未改用部件庫**：`statusGlyph`／`surfaceGlyph`／`statusColor`／`surfaceColor` 已匯出可共用；因 `BattleRenderer.ts` 與 3-16a 的範圍重疊，這段沒碰，需等 3-16a 合併後接上（工坊選項與技能卡已共用）。
5. **技能列浮動卡變高**：多了 72px 圖示與組裝列（380px 寬約 3 排），浮動卡高度約 325px，會蓋住較多戰場。是否要在浮動卡隱藏組裝列（只在升級、營火、工坊、主角面板顯示），或做緊湊版。
6. **修正的改變內容只有 11 種有專屬圖示**：`add_tags`、`on_hit_effects` 目前畫「?」（照退回規則），要不要補。
7. **代價只有種類沒有數值**：`costs` 為字串（例如 `source`），組裝列顯示「源力」而非「源力 2」；樣張有數值。要加數值需改 `icon.costs` 的型別。
8. **延遲段特效**：複合技能的延遲段（`followup_charged`／釋放事件）本來就沒有獨立特效，這段沒擴大範圍；第二段是否需要在蓄力時就預告，留給之後。
9. **截圖解析度**：內建瀏覽器面板太小，1600×900 的整體圖只有 800×450；近照是面板原尺寸加 CSS 縮放。美術驗收若要真正 1600×900 的原圖需在大螢幕重拍。
10. **技能列按鈕高度 42 → 48px**：為了放 40px 圖示，技能列整體高 6px；底部列的版面（3-8）預算若很緊，請確認。
