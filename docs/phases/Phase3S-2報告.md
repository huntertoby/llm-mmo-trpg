# Phase 3S-2 報告：真側面的頭部裝備、盾、披風

## 做了什麼

- 新檔 `client/src/render/paperdollSideGear.ts`：
  - 頭部裝備側面形狀（9 種 kind，涵蓋 `KNOWN_KINDS.head` 全部）：頭盔（圓頂＋後頸甲，護鼻片在臉前方）、角盔、兜帽（開口往前、變窄）、巫師帽（整頂朝前傾、帽尖往後彎）、寬簷帽（略朝前傾）、便帽／毛帽（皮帽有帽舌）、全罩盔（眼縫只在前半）、頭巾（尾巴往後飄）、王冠（三尖、寶石在前）。
  - 角盔的角用 `drawHornSide`：**兩支都往後彎，遠側較暗（先畫、在盔後），近側蓋在盔上**；函式匯出，3R-3 種族角可直接共用。
  - 盾：圓盾（盾心突起朝前）、鳶盾（下尖）、塔盾（細長）、法書（側看成厚書脊＋書頁邊）；法器珠沿用既有球體畫法（球從側面看一樣）。
  - 披風：肩後垂下、下擺往後飄、一道亮褶、領口。
- `paperdollSide.ts` 改用上述函式，刪除 3S-1 的簡易版；`SideHooks` 移除不再需要的 `headgearFront`、`helmetBack`；`paperdoll.ts` 只改 `drawFigureSideView` 的 hook 清單（sword 分支未動，與 3I-3 衝突面極小）。
- 武器、種族部件維持 3S-1 現狀。
- 開發用 doll-gallery 新增段「⑥ 側面」：頭部 10 款 × 東／西、盾／書／珠／披風與組合。開法：`pnpm dev` 後開 `/doll-gallery.html#⑥`。
- vitest：頭部各 kind（含未知）× 3 種 form × 4 方向 × 有／沒有盾與披風；副手各 kind（含未知、塔盾）× 披風；每種頭部側面異於正面且朝西為朝東鏡像；角盔兩支角且遠側較暗先畫。

## 檢查

- vitest 958 全過、`pnpm build`（tsc＋vite）通過。
- 排版煙霧：先 `localStorage.clear()`，主頁在 1009×768 無橫向溢位、無 console 錯誤（本機沒起後端，未進戰鬥；改動只在紙娃娃畫法，不影響版面）。
- 不碰規則引擎與 skillgen；沒跑 `scripts/check.py`。

## 對照美術 PM 檢查清單

- 頭盔護鼻片移到前方：是。兜帽開口往前變窄：是。巫師帽、寬帽朝前傾：是。
- 角盔兩支角都往後彎、遠側較暗：是（放大看過）。
- 盾變成擋在身前的窄形：是；披風從背後垂下往後飄：是。
- 朝西為朝東整張鏡像：是（測試保證）。

## 截圖（原尺寸，開發用 doll-gallery）

`docs/art/port/3S-2/`：`doll-gallery-head-east.jpg`（頭部朝東）、`doll-gallery-head-west.jpg`（頭部朝西）、`doll-gallery-shield-cloak.jpg`（盾、書、珠、披風與組合）。每格基底 hero_fighter 本身帶塔盾／披風，所以頭部圖也同時看得到盾與披風。

## 待 PM 決定

1. `SideHooks` 移除了 `headgearFront`、`helmetBack`；若 3S-3 或 3I-3 的分支還在用請在合併時留意。
2. 頭部裝備清單實際只有 9 種 kind（規格寫 10 種），已全部涵蓋；若指的是另一種 kind 請告知。
3. 披風沒有對應的裝備類別（`dollGear` 無 cloak 欄位對照），gallery 以直接指定部件展示。
4. 角盔角的大小（`size` 1.3）與位置可依美術 PM 驗收調整。
