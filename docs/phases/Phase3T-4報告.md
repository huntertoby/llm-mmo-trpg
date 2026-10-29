# Phase 3T-4 報告｜前端整理

> 實作：sonnet implementer，2026-10-29。純整理、不動 Python。驗收依 `Phase3T計畫.md` 第 2 節。

## 1. 完成項目（對照規格 ①～⑥）

| 項 | 做了什麼 |
|---|---|
| ① 武器小圖示 | `weaponIcon.ts` 改呼叫新的 `inkWeapons.drawInkWeaponAlone`（與小人手持同一套 C 墨線畫法）。刪除 `paperdoll.ts` 的 `drawWeapon`／`legacyHooks`／`drawWeaponAlone`／`drawWeaponSide`／`handSides`、`InkHooks.weapon`、`paperdollGear.ts`、`paperdollSideWeapon.ts`＋測試（約 700 行）。魔導劍常數只留 `inkWeapons.ts`（`ARCANE_GLOW`、`arcaneGlow`）。刪前已搜尋，只剩測試在用的部分改寫成 ink 版（`arcaneBlade.test.ts`、`weapons24a2.test.ts`）。 |
| ② 配色 | 新 `render/palette.ts`（葉節點）：`ELEMENT_COLORS`（含新欄位 `bright`、`mark`）、`KEYWORD_COLOR`／`TINT_KEYWORDS`、`SURFACE_ICON_COLOR`、`SURFACE_GROUND_COLOR`、`elementColor`、`elementTintColors`。`vfxPalette`、`artPalette`（刪 `GEAR_KEYWORD`）、`glossary.SURFACES`、`skillParts`、`statusIcon`、`inkForm`、`summonArt`、`gearIcon`、`appearance.elementTint`、`fieldFx` 全改讀它。`inkForm` 支援所有元素（物理與不認得的算無元素）。 |
| ③ 共用工具 | `render/color.ts`（`mix`／`darken`／`lighten`／`shade`／`rgba`／`numToHex`／`isHex`），刪 8 份區域複本。`render/material.ts` 放 `MATERIAL`（`GEAR_MATERIAL`、`inkStyle.MAT` 的金／木由它導出）。`View` 型別只在 `inkStyle.ts`。`HAIR_COVERED` 併入 `COVERS`（新旗標 `hair`）。 |
| ④ shadeDir | 模組變數 `setShadeDir` 刪除，改 `withShadeDir(ctx, dir, fn)`：方向跟著畫布（WeakMap）、結束時還原、預設 1。三個對外入口（`drawInkFigure`、`drawForm`、`drawSummonBody`）包起來。貼圖快取鍵已含朝向（方向由朝向決定），不需改。 |
| ⑤ 觸控釘住 | `Hint`、`PartTip pin={false}` 改 `pinOn: "touch"`；`StackTip` 改用 `PartTip`（可釘住）；CSS：`no-bridge` 卡釘住後恢復 pointer-events（才能捲動）。 |
| ⑥ 順手 | `ArtTextures.canvas(key, make)` 共用（figure／summon／form／formAura 四段合一）；`unitSprite` 抽 `applyLook` 與共用灰階濾鏡（不再每次 new）；預設戰士只算一次、範本 id 改具名常數；兩個 `raceCardLines` 改名 `raceBattleCardLines`／`raceStartCardLines`；副手附魔改「副手和主手同種武器」。 |

## 2. Commit

1. `Add shared render/color.ts and render/material.ts`
2. `Remove legacy paperdoll weapon drawing; weapon icon uses ink style; share View, MAT and color helpers; shade direction is per-canvas`（①③④交錯在同幾個檔，無法乾淨拆開，合為一個）
3. `Unify element/keyword/surface colors in render/palette.ts; inkForm supports every element`
4. `Touch can open and pin Hint/PartTip(pin=false) cards; StackTip uses PartTip`
5. `Share ArtTextures.canvas(), gray filter and applyLook in unitSprite; rename race card line helpers; paired off-hand enchant by same kind`

## 3. 驗收

- `tsc --noEmit` 通過、`pnpm build` 通過；完整 vitest 113 檔 1097 測試全過（Python 未動、未跑 `check.py`）。
- **截圖對照**（headless Chrome，同視窗；`docs/phases/img/3T-4-*`）：doll-gallery、summon-gallery、gear-gallery 前後 PNG **逐位元相同**（涵蓋小人、四方向、種族、召喚物、頭部／武器／副手畫法，實戰用的就是同一批畫法，故證明 shadeDir／color／MAT／View 重構外觀不變）。form-gallery 有差異（見下）。武器小圖示前後見 `3T-4-weaponicon-before/after.png`。
- **實戰畫面**：因內建瀏覽器截圖無法存檔，沒有實戰前後 PNG；以排版煙霧檢查＋實機觀察代替（英雄面板的弓圖示為新 ink 畫法，確認顯示正常）。
- **排版煙霧檢查**（`?anim=0.1`、先 `localStorage.clear()`）：1600×900 全 PASS（9 項）；800×600 全 PASS。未跑 `shortBottom` 情況。
- **觸控釘住**（resize mobile 預設；瀏覽器點擊是滑鼠事件，故用 `pointerdown(pointerType=touch)`＋`click` 模擬）：播放列「縮小」`Hint` 點一下 → 浮動卡開且 pinned（1/1），再點一下 → 關（0/0）。
- 浮動卡「滑進→捲到底→釘住→關閉」沒有新增彈出元件（只改 pinOn），既有 `floatCardRule.test.ts` 與 `Hint.test.ts` 通過；未另做 1600×900／800×600 的滑鼠實測（**待 PM 抽查**）。

## 4. 外觀有意改變（逐條）

**配色統一（以 `artPalette` 的裝備關鍵字色 ignite／charged／frozen／wet 為準，它與 `ELEMENT_COLORS` 主色本來一致）：**
- 火：狀態圖樣（燃燒）、腳邊火粒子、陷阱／區域元素色、元素化身／龍／形態光環、技能圖示表面「火」、戰場「火」表面疊色：`#ff7a1a` → `#ff6a1a`。
- 雷：形態（化身、龍、光環）`#ffe14a` → `#fff36b`；狀態圖樣的雷 `#ffe14a` → `#fff36b`。
- 毒：狀態圖樣 `#8fdc4a` → `#7ddc3a`。
- 聖／暗影／風／大地的狀態圖樣色：由各自舊值改為 `ELEMENT_COLORS` 主色（聖 `#ffe9a0`→`#fff2b0`、暗影 `#a77bff`→`#9a6ad8`、風 `#bff0d8`→`#c8ffe8`、大地 `#c8a060`→`#b0814a`）。物理持續傷害仍紅（`mark`）。
- `inkForm`：水、毒、聖、暗、風、地的形態原本一律中性紫光環／預設火色，現各有元素色；物理與不認得的元素仍是中性紫、龍／化身仍退回火。形態貼圖快取鍵因此多了元素種類（正確）。
- 與舊 `gearIcon` 關鍵字色同值（ignite／wet／charged／frozen），裝備圖示不變（gear-gallery 位元相同）。

**武器小圖示**改為 ink 畫法（見 before/after 圖）：線條帶墨線與排線、比例略細；匕首、手槍等短武器放大後較粗糙。這是規格 ① 的目的。

## 5. 待 PM 決定

1. **「artPalette 為準」有歧義**：`PAL.fire`（#ff7a1a，地形用）與 `GEAR_KEYWORD.ignite`（#ff6a1a）同在 artPalette。我採 `GEAR_KEYWORD`（與特效一致，另 4 處同值）；`PAL`（地形調色）原封不動。若要改以 `PAL` 為準，只需改 `palette.ts` 一處。
2. **表面色沒有合成一張**：地面疊色（`SURFACE_GROUND_COLOR`）與技能圖示用（`SURFACE_ICON_COLOR`）本來就為不同底色調過（冰、暗、水差很多），只統一了「火」取元素色，其餘兩張表值不變。
3. **鋼／鐵墨線色與 `MATERIAL` 不同**（`#c3ccd6`/`#8d969f` vs `#a9b6c6`/`#7a828b`）：硬併會改所有小人的盔甲外觀，故 `inkStyle.MAT` 只有金、木導出自 `MATERIAL`，鋼鐵保留美術 PM 的值。
4. **`HAIR_COVERED` 併入 `COVERS`** 時，`bandana`、`wide_hat` 在 `COVERS` 是 `top` 但原本「不遮頭髮」；為了外觀不變，新增旗標 `hair`（只有原六種為 true）。審查建議的「直接用 `top`」會讓這兩種帽下的頭髮消失，是否要改請決定。
5. **shadeDir 沒有逐一加參數**：`ink()` 有約 300 個呼叫點，改成「方向跟著畫布」（`withShadeDir`，WeakMap）而非 `InkOpt.dir`；效果等同（順序無關、預設 1）。
6. **`pinOn` 沒有新增 `"touch-only"`**：既有的 `"touch"`（觸控點一下開關、滑鼠不釘住）語意完全相同，直接沿用。
7. **未做**：`SHAPE_HOW` 改讀 glossary 形狀名（`race.ts`，需確認後端 `name_zh` 是否適合當「選取方式」句子）、`SkillBar` 的 `props.race as RaceView` 窄化、`unitSprite` 的 `statusTextures`／`effectTextures`／`rowTextures` 併入 `ArtTextures`（規格 ⑥ 未列，屬審查 #5 後半）。
8. 未做實戰畫面前後 PNG 與 `shortBottom` 煙霧情況（見第 3 節）。
