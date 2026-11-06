# Phase 3 結束審查｜前端（2c42268..e789993，`client/src`）

> 審查者：opus 審查 agent（只讀），2026-10-23。PM 的排程決定見 `Phase3計畫.md` 第 38 節。

## 浮動卡盤點（6.5.1）

| 位置 | 元件 | 不符合條目 |
|---|---|---|
| 技能卡 `ui/SkillBar.tsx` | `useFloatCard`／`FloatCard` | 無 |
| 部件說明框（`SkillIconView`、`KeywordLine`、`ReactionPanel`、`SummonPanel`、`UnitInfo`、`HeroGearPanel`、`SlotGrid`） | `PartTip` | `pin={false}` 處觸控打不開（#8）、不能釘住（設計取捨） |
| 按鈕說明（全站） | `Hint`（`pinOn:"never"`） | 觸控打不開（#8） |
| 格子資訊卡 `BattleScreen.tsx:998` | `HoverFloat`＋`TileCardController` | 鍵盤無法開啟；觸控點格子直接執行動作 |
| 頂端面板 `.top-popup`（`BattleTopBar.tsx:51`） | 自製（白名單） | 點外面不關、不參與同時一張、不翻轉 |
| 更多動作 `.more-list`（`TurnControls.tsx:123`） | 自製，**不在白名單、測試抓不到** | 無 Esc／點外面關閉、不參與同時一張、`max-height` 沒配 `overflow` |
| 詢問視窗 `.decision-card`（`DialogFrame`） | 白名單 | 沒有最大高度、不能捲動 |

## 問題（依嚴重度）

1. **Esc 同時觸發兩件事**：`BattleScreen.tsx:694-712`（window keydown）與 `useFloatCard.tsx:89-93`、`useTileCard.ts:27-30`（document）都沒攔下；關浮動卡時連瞄準也取消。修：浮動卡處理過 Esc 就 `stopPropagation`，或 BattleScreen 先查 `floatCard.hasActive()`。小，3E-2。
2. **「更多動作」選單自製、規則測試抓不到**（`TurnControls.tsx:118-150`、`styles.css:2443`）：做共用 `usePopupMenu`／`ClickPopup`（Esc、點外面、同時一張、最大高度捲動），`.top-popup` 一起改；規則測試加「CSS `position: absolute` 且 `z-index ≥ 20`」。中，3E-2。
3. **`Hint`、`PartTip pin={false}` 觸控永遠打不開**（`Hint.tsx:17`、`PartTip.tsx:22`、`useFloatCard.tsx:124-139`）：加 `pinOn:"touch-only"` 或長按。小，3E-3。
4. **前端寫死中文名與 ID 對照表（守則 4，Phase 4 會卡）**：`skillParts.ts:826`（`EFFECT_NAMES`）、`:992`（`CONDITION_NAMES`）、`:1209`（`TRIGGER_NAMES`）、`:1034`、`:1290`；`appearance.ts:91`（`WEAPON_LOOKS`）、`:204`（`APPEARANCES`）。改讀 glossary API；英雄外觀改由後端外觀欄位提供。中，3E-2。
5. **元素／關鍵字配色分散 4 份表**（`artPalette.ts:23`、`vfxPalette.ts:90`、`summonArt.ts:35`、`skillParts.ts:427`；water 有三種色）：合併成 `render/palette.ts`。中，3E-3（Phase 4 開放新元素則提前）。
6. **`BattleScreen.tsx` 1231 行、97 個 hook**：拆 `useBattlePlayback`、`useTargeting`（含 `onTileClick` 分派）、`useSummonControl`、`useBoardZoom`。大，3E-3；Phase 4 前至少把 `onTileClick` 抽成純函式。
7. **`styles.css` 3357 行**：死碼 `.fallback-list`、`.modal-backdrop`；z-index 隨手寫。拆檔、z-index 變數分層。中，3E-3。
8. **詢問視窗沒有最大高度**（`styles.css:817`）：`max-height: calc(100vh - 70px); overflow-y: auto`。小，3E-2。
9. **浮動卡定位每次重繪都重掛監聽器**（`HoverFloat.tsx:30` 無依賴陣列、`useFloatCard.tsx:178`）；`FloatCard` 沒有 ResizeObserver。小，3E-3。
10. **Pixi 每次整個重建**（`BattleRenderer.ts:218`、`:486-515` 每次換格 `new Text`）：Text 改 `BitmapText` 或物件池。無洩漏、無不確定性。中，3E-3。
11. **26 處繞過型別的轉型**（`gearIcon.ts:54,73`、`CustomItemForm.tsx:33` 等）：外觀 JSON 同時輸出 `.d.ts`；事件聯集由後端輸出 schema。中，3E-3。
12. **規則測試漏洞**（`floatCardRule.test.ts`）：只掃 `.tsx`、CSS 只查 `fixed`、`role=tooltip` 規則太寬；移除 `.modal-backdrop`，`.top-popup`、`.more-list` 明列白名單或改用共用元件。小，3E-2。

**整體評價**：共用浮動卡元件設計乾淨、有測試，主要彈出層已統一；剩兩個點擊式選單與 Esc 衝突。建議 3E-2 補 1、2、4、8、12，再進 Phase 4；BattleScreen 與 CSS 拆分放 3E-3。
