# Phase 3 後段審查｜前端（ebaebb32..HEAD，`client/src`）

> 審查者：opus 審查 agent（只讀），2026-10-29。範圍：紙娃娃 C 畫風（`render/ink*.ts`）、形態外觀、召喚物、種族外觀、開局選種族、工坊技能元素與預覽武器、種族技按鈕列。上一次審查：`Phase3審查-前端.md`（F1～F12）。
> 只跑了 `src/ui/floatCardRule.test.ts`（12/12 通過）；沒有跑全量、沒有開預覽。

## 上次問題（F1～F12）對照

| 編號 | 狀態 | 說明 |
|---|---|---|
| F1 Esc 同時觸發兩件事 | 已解決 | `useFloatCard.tsx:93`、`useTileCard.ts:30` 已 `stopPropagation` |
| F2 「更多動作」自製選單 | 已解決 | 新增 `usePopupMenu.ts`，`TurnControls`、`BattleTopBar` 已改用，規則測試列 `MUST_USE_POPUP_MENU` |
| F3 `Hint`／`PartTip pin={false}` 觸控打不開 | **未解決** | 見下方 #8；新增的 `StackTip` 也走 `Hint` |
| F4 前端寫死中文名對照 | 大致解決 | `EFFECT_NAMES` 等已移除、武器外觀改讀 glossary；剩 `skillParts.ts:1069 TAG_NAMES`、新增的 `inkForm.ts:256 FORM_LOOKS`（#4） |
| F5 元素配色分散 | **惡化** | 由 4 份增加到至少 8 份（#2） |
| F6 `BattleScreen.tsx` 過大 | 未解決 | 1268 行（上次 1231） |
| F7 `styles.css` 過大 | 未解決 | 3748 行（上次 3357） |
| F8 詢問視窗最大高度 | 已解決 | `styles.css:830` |
| F9 浮動卡沒有 ResizeObserver | 已解決 | `HoverFloat.tsx:70`、`useFloatCard.tsx:191` |
| F10 Pixi 每次整個重建 | 未變 | 本次不再列（無洩漏，見 #6 的小問題） |
| F11 型別逃逸 | 未解決 | `gearIcon.ts:58,77`、`CustomItemForm.tsx:38` 仍是 `as unknown as KindEntry[]`；新增的都在 `dev/` 畫廊（可接受） |
| F12 規則測試漏洞 | 已解決 | 掃 `.ts`／`.tsx`，白名單附理由 |

## 浮動卡盤點（6.5.1，本範圍新增的彈出 UI）

| 位置 | 元件 | 結果 |
|---|---|---|
| 開局種族／出身卡 `run/RaceOriginPicker.tsx:31` | `useFloatCard`＋`FloatCard` | 符合 |
| 種族技按鈕 `ui/SkillBar.tsx` `RaceSlot` | `useFloatCard`＋`FloatCard` | 符合 |
| 層數說明 `ui/StackTip.tsx` | `Hint` | 符合規則，但內容可能很長（列出「你的技能」），觸控打不開、不能釘住（#8） |
| 裝備比較 `ui/gear/GearCardView.tsx:44` | `PartTip` | 符合 |
| `title=` 屬性 | — | 只剩 `DialogFrame` 的 `title` prop（不是原生屬性），無違規 |

確定性：`client/src` 內唯一的 `Math.random` 在 `StartScreen.tsx:26`（開局種子，合理）；墨線抖動用 `inkStyle.ts` 的 FNV-1a＋LCG，確定。

## 問題（依嚴重度）

1. **舊畫法殘留約 600 行，武器小圖示仍是舊畫風**（`render/paperdoll.ts:265-404` `drawWeapon`／`legacyHooks`、`paperdollGear.ts` 全檔、`paperdollSideWeapon.ts` 全檔、`weaponIcon.ts:39`）。`resolveDoll` 只留 `KNOWN_KINDS` 的 kind，而這些 kind 已全部由 `inkGear.ts`＋`inkWeapons.ts` 畫，所以 `InkHooks.weapon` 這條退回路徑實際走不到；`handSides`、`drawWeaponSide`、`SIDE_RACE_ANCHORS` 只剩測試在用。唯一還在用的是 `drawWeaponAlone`（英雄面板武器小圖示），結果圖示是舊畫風、地圖小人是 C 畫風，與 `weaponIcon.ts` 開頭註解「同一套畫法」不符。另外 `inkWeapons.ts:17-19` 為了避開循環匯入，把 `paperdoll.ts:78-82` 的魔導劍常數另存一份。
   **修法**：`weaponIcon` 改呼叫 `drawInkWeapon`／`drawInkWeaponMore`（加一個「單獨畫」的入口）；刪掉 `drawWeapon`、`legacyHooks`、`InkHooks.weapon`、`paperdollGear.ts`、`paperdollSideWeapon.ts` 與對應測試；魔導劍常數只留在 `inkWeapons.ts`。**工作量：中**。

2. **元素／關鍵字配色分成 8 份以上，數值互相矛盾**（F5 惡化）：`artPalette.ts:26`、`battle/vfxPalette.ts:57`（`ELEMENT_VFX`）、`battle/glossary.ts:134`、`skillParts.ts:231`、`statusIcon.ts:22,39`、`inkForm.ts:39`、`summonArt.ts:35`（`KEYWORD_COLOR`）、`gearIcon.ts:81`。火有 `#ff7a1a`／`#ff6a1a`，雷有 `#ffe14a`／`#fff36b`：雷屬性龍形態（`inkForm`）和雷屬性魔導劍（`elementTint` 取 `ELEMENT_VFX`）顏色不同。`inkForm.ts:44` 只認 fire／ice／lightning，水、毒、聖、暗的形態一律變成中性紫。Phase 4 開放新元素（含「自然」主題）時要改 8 個檔。
   **修法**：建 `render/palette.ts`，一份 `ELEMENT_COLOR`（主色、亮色、暗色）＋一份 `KEYWORD_COLOR`，其他檔一律匯入；`elementTint`、`formAuraColor`、`statusIcon` 改讀它；不認得的元素再退回中性色。**工作量：中**（Phase 4 前做）。

3. **色彩工具、材質色、視角型別各寫多份**：調色函式有 `inkDoll.ts:33 darken`、`inkGear.ts:40,47 lighten／darken`、`paperdollGear.ts:6 mix`、`inkRace.ts:62 mix`、`inkForm.ts:22 mixColor`、`artPalette.ts:57 shade`、`paperdoll.ts:19,33 dark／darker`、`summonArt.ts:82 light`；材質色 `#c3ccd6`／`#e8bb48`／`#a06a36` 在 `inkDoll.ts:23`、`inkGear.ts:12`、`inkArmor.ts:9`、`inkOffhand.ts:9-11`、`inkWeapons.ts:11-12` 各一份（`appearance.ts:79 MATERIAL` 才是來源）；`"front" | "back" | "side"` 定義三次（`InkView`、`GearView`、`RaceView`）；`inkDoll.ts:31 HAIR_COVERED` 與 `inkRace.ts:82 COVERS` 描述的是同一件事（帽子遮哪裡）。
   **修法**：`render/color.ts`（`mix`／`darken`／`lighten`，非 `#rrggbb` 原樣回傳）、`MAT` 由 `MATERIAL` 導出、`inkStyle.ts` 匯出一個 `View` 型別；`HAIR_COVERED` 改由 `COVERS[kind].top` 判斷。**工作量：小～中**。

4. **形態外觀與技能標籤的對照寫死在前端，Phase 4 新名稱會退回成預設**：`inkForm.ts:256 FORM_LOOKS`（`form_bear`→`bear`…10 筆）、`inkForm.ts:242 FORM_ARTS`；`skillParts.ts:1068-1069 TAG_TARGET`／`TAG_NAMES`（6 個標籤的中文）。LLM 產生的形態若帶新的 `look` id，只會畫原角色＋光環；新標籤會在圖示說明裡顯示英文 id。
   **修法**：`forms.yaml` 的 `look` 直接用畫法 id（`bear`、`dragon`…）並在 schema 列舉，讓 LLM 只能從既有畫法裡選（新形態＝新名稱＋既有畫法＋元素色）；標籤中文改讀 glossary（後端 `skill_tags` 加 `name_zh`）。**工作量：中**（需後端配合）。

5. **貼圖快取重複、模組層快取不受回收**：`artTextures.ts:83-140` 的 `figure`／`summon`／`form`／`formAura` 四段是同一個「查快取→畫 canvas→`Texture.from`」的複製貼上（`get()` 只服務格子大小的畫布）；`unitSprite.ts:84 statusTextures`、`:236 effectTextures`、`:269 rowTextures` 是模組層 `Map`，不在 `beginFrame`／`endFrame` 回收、元件卸載也不銷毀；`rowTextures` 鍵含 `fontEpoch()`，字型載入後舊鍵永遠留著。「建離屏 canvas＋scale(dpr)」的樣板另有 7 份（`paint`、`renderFigureCanvas`、`summonArt.ts:383 makeCanvas`、`renderFormCanvas`、`renderAuraCanvas`、`effectTexture`、`statusIconCanvas`）。數量有上限（組合有限），不是嚴重洩漏。
   **修法**：`ArtTextures` 加 `canvas(key, () => HTMLCanvasElement | null)`；`unitSprite` 的三個快取併進 `ArtTextures`；共用 `offscreen(w, h, dpr)`。**工作量：小**。

6. **`unitSprite.ts` 每次重畫的小浪費與寫死範本 id**：`formDoll`（`:149-166`）與 `doll`（`:181-207`）重複「透明度＋隱匿＋灰階」整段；倒地單位每次重畫都 `new ColorMatrixFilter()`（`:160`、`:202`），`destroy({children:true})` 不會銷毀 filter；`summonHumanoidSpec`（`:134-138`）每次重畫呼叫兩次 `resolveDoll`，並寫死 `"summon_skeleton_warrior"`、`"hero_fighter"`。
   **修法**：抽 `applyLook(sprite, u, look)`；模組層共用一個灰階 filter；骷髏與預設戰士的規格算一次存起來。**工作量：小**。

7. **墨線暗面方向是隱藏的模組狀態**（`inkStyle.ts:77 shadeDir`）：`drawInkFigure`、`drawForm`、`drawSummonBody` 會設定、但不還原；若之後有地方直接呼叫 `ink()`（例如第 1 點把武器小圖示改成 C 畫法、或 `gearIcon` 改墨線），暗面方向就取決於「上一個畫的是誰」，而快取鍵不含它，畫出來的貼圖會因呼叫順序而不同。
   **修法**：`InkOpt` 加 `dir`，或提供 `withShadeDir(dir, fn)` 包起來並在結束時還原；至少在每個對外入口設定。**工作量：小**。

8. **觸控打不開說明卡（F3 未解），新增的層數說明更受影響**：`Hint.tsx:39`（`pinOn: "never"`）、`PartTip.tsx:22`（`pin={false}`）；`StackTip.tsx:20` 用 `Hint` 顯示「你的技能中會累積／消耗它的」清單，內容可能長到要捲動，卻不能釘住。
   **修法**：`useFloatCard` 加 `pinOn: "touch-only"`（觸控點一下開關、滑鼠照舊不釘住），`Hint`、`PartTip pin={false}` 改用它；`StackTip` 改 `PartTip`（可釘住）。**工作量：小**。

9. **種族與形狀文字重複、附魔副手的小漏洞**：`battle/race.ts:51 raceCardLines` 與 `run/raceOrigin.ts:31 raceCardLines` 同名、內容不同（一個給戰鬥浮動卡、一個給開局卡），容易匯入錯；`race.ts:58 SHAPE_HOW` 是又一份「形狀 id→中文」表（`vfx.ts:33 SHAPE_NAMES` 是反方向、後端 `skill_shapes.yaml` 有 `name_zh`）；`appearance.ts:243` 附魔元素只在 `pairedKind !== null`（依 `weaponId` 判斷）時套到副手，若成對武器來自身上裝備但 `weaponId` 查不到外觀，第二把不會換色；`SkillBar.tsx` 的 `props.race as RaceView` 可用窄化取代。
   **修法**：改名 `raceBattleCardLines`／`raceStartCardLines`；選取方式文字讀 glossary 的形狀名稱；副手條件改成「`gear.off_hand` 與主手同 kind」；去掉 `as`。**工作量：小**。

10. **上次留下的大型整理仍未做**：`BattleScreen.tsx` 1268 行、77 個 hook（F6）；`styles.css` 3748 行（F7）；`gearIcon.ts:58,77`、`CustomItemForm.tsx:38` 的 `as unknown as KindEntry[]`（F11，外觀 JSON 沒有型別）。Phase 4 會再加 LLM 技能相關 UI，`BattleScreen` 的 `onTileClick` 分派至少要先抽成純函式。
    **修法**：同上次建議（拆 `useBattlePlayback`／`useTargeting`／`useSummonControl`、CSS 拆檔＋z-index 變數、外觀 JSON 輸出 `.d.ts` 或用 zod/型別守衛解析）。**工作量：大**（可與 Phase 4 前段平行，非阻擋）。

## 整體評價

C 畫風分層清楚（畫法層 `inkStyle`、骨架 `inkDoll`、部件 `inkGear`／`inkWeapons`／`inkArmor`／`inkOffhand`／`inkRace`、形態 `inkForm`），不認得的值都有退回、確定性良好、測試齊全；本範圍新增的彈出 UI 都用共用浮動卡，上次的 F1、F2、F8、F9、F12 已解決。主要債務是 C-2 換完後沒有回頭清掉舊畫法（#1），以及配色、調色、材質常數越複製越多（#2、#3）。#2 與 #4 會直接影響 Phase 4（新元素、新形態名稱）。

**建議先排一個整理子階段**（約 1 段：#1、#2、#3、#7、#8，另把 #4 的 schema 決定交給玩法 PM／開發 PM）；#5、#6、#9 可順手做，#10 可與 Phase 4 前段平行。
