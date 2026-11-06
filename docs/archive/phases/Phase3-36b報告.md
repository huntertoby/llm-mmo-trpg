# Phase 3-36b 報告｜戰場效果

規格：`docs/phases/Phase3計畫.md` 40.2；需求以 `docs/art/戰場效果與狀態圖示.md` 第 4 節「段 2」為準；畫法移植自 `docs/art/sample/fx.js`。

## 做了什麼

| 項目 | 內容 |
|---|---|
| `render/fieldFx.ts`（新） | `cracks()`、`turnsBadge()`、`sightVeil()`、陷阱踏板、區域單格（紋理＋外框＋箭頭）、施放者虛線環、`fxColor()`（元素 → 表面色 → 灰）、`hpStageOf()`。 |
| `objectArt.ts` | `ice_wall`、`thorn_wall`、`rubble`、`thin_ice` 換成 fx.js 新畫法；`ObjectArtSpec` 加 `turnsLeft`、`hpStage`；所有 `hpRatio` 非空的物件依級距疊裂痕（薄冰自己畫）。快取鍵只用級距（剩餘回合分永久／有幾回合／最後 1 回合；受損 0／1／2）。 |
| 徽章 | `BattleRenderer.objectSprite` 的白字改為 `turnsBadge()`（最後 1 回合橘色），區域（最左上格）、延遲陷阱共用。有畫法的暫時物件不再整個淡化（最後 1 回合由貼圖自己融化／枯萎），沒畫法的仍淡化。 |
| 霧 | `RowLayer` 新增 `veil`（單位層之後，跟著格子抬高）；glossary 表面 `blocks_sight` 標籤決定（黑暗紫、其餘灰，新表面自動套用）。 |
| 陷阱 | `TrapDraw` 加 `mine`、`trigger`、`element`、`remaining`；畫在 `traps` 層。`buildDrawModel` 多一個選用參數 `skills`（`battle/fxSkills.ts`，由技能卡 `icon` 查）；查不到或不認得的 trigger → `enter`＋灰。`BattleScreen` 把陷阱與區域的 `skill_id` 加進要載入的技能卡。 |
| 區域 | `ZoneDraw` 改為整塊一筆；`zoneCellSpecs()` 算每格只描外緣的邊、移動型箭頭側、斜紋相位（相鄰格斜紋接起來）；有害／有益依目前玩家陣營（`zoneHarmfulTo`）；`caster` 在施放者腳下畫虛線環。 |
| 開發樣張頁 | `client/fx-gallery.html`＋`src/dev/fxGallery.ts`：真的 `BattleRenderer` 畫的 9×6 場景（對照 `battlefield-fx.png` 提案，不進正式 build）。 |

## API／glossary 變更

- glossary：表面 `blocks_sight` 標籤本來就有，**不用補**。
- 技能卡 `icon`（`SkillIcon`）新增 `trap_trigger`（`trap.trigger`）、`zone_element`（`zone` 效果子效果的第一個元素）；技能卡原本沒有陷阱觸發方式與區域元素。已重產 OpenAPI、`schema.d.ts`、`fixtures/skill_icons.json`；pytest：`tests/narrative/test_skill_icon.py` 新增 1 項，`test_openapi_snapshot` 通過。

## 測試

vitest 781 → 795（新增 `render/fieldFx.test.ts` 12 項；`zones.test.ts` 改寫；`art.test.ts` 物件全組合）；typecheck、`pnpm build` 通過；ruff、format、mypy（narrative）通過。涵蓋：未知物件／表面／元素／trigger 不出錯並退回灰色、鍵用級距、裂痕級距、徽章最後 1 回合橘色、陷阱我方／敵方、區域外緣與箭頭、有害／有益判斷。
Python 用主資料夾 `.venv` 的 python，`PYTHONPATH` 指向 worktree 的 `src`。

## 檢查清單（實機：`/fx-gallery.html`，1600×900，內建瀏覽器；無附圖，截圖工具無法存檔）

4. 煙霧、黑暗：左上單位下半身被霧蓋住、仍認得出；黑暗為紫黑加光點。符合。
5. 冰牆有高度；最後 1 回合變矮透明有水窪，徽章橘色；荊棘最後 1 回合變褐色、刺少。符合。
6. 薄冰、倒塌物、冰牆依 HP 出現裂痕；薄冰 20% 露出黑水破洞。符合。
7. 陷阱：我方藍實線、被揭露的敵方紅虛線加「!」；enter 為捕獸夾、delay 為沙漏加倒數徽章；未揭露的敵方不畫。符合。
8. 區域：只描外框；打我的（橘火、移動型）實線斜紋＋前進側三角箭頭，幫我的（聖光、跟隨型）虛線光點＋施放者腳下虛線環；徽章在最左上格。符合。
9. 9×6 場景在遊戲裡重現（與提案圖一致，省略未揭露陷阱與對照格）。符合。

## `# noqa`

無。

## 待 PM 決定

1. **API 小改**：規格說「查技能表」，但技能卡沒有陷阱觸發方式與區域元素，故在 `SkillIcon` 加 `trap_trigger`、`zone_element`（只讀、不動引擎）。
2. **有害判斷**：影響「施放者的敵人」→ 施放者是敵方才有害（我方自己的火牆對我顯示為有益的虛線）；影響「所有人」→ 看伺服器 `harmful`；影響「施放者的友方」→ 一律有益（包含敵方放的增益區域）。
3. 區域元素色取 `zone_element`，沒有時取技能元素，再取區域產生的表面色，再灰。
4. 暈眩星星仍靜止（3-36a 遺留，未做轉動）。
5. 霧貼圖以格子為單位裁切，邊緣的霧不跨格；肉眼看不到接縫。
6. 沒有技能卡資料（尚未載入）時，陷阱暫畫成 enter＋灰，卡片載入後自動重畫。
