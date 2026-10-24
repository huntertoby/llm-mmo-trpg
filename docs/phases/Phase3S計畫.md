# Phase 3S｜真側面紙娃娃（美術 PM 方案 A）

> 使用者原話（專案 PM 轉達）：「A」（側面選真側面）、「可以」（樣張可交開發 PM）。移植需求與檢查清單：`docs/art/種族與側面移植需求.md` 第 ② 節；畫法：`docs/art/側面畫法.md`、`docs/art/sample/sideArt.js`；樣張 `docs/art/races-side.png`、`side-views.png`。
> **排程**：只動前端繪圖（`client/src/render/paperdoll.ts`、`appearance.ts` 等），不碰規則引擎，所以當成 **平行的美術軌**：有空的 agent 位置就派（同時仍最多 2 個 agent），不打亂 3I → 3K → 3J 的順序。**種族外觀（3R-3）排在 3S 之後**，直接用側面的位置規則，不重工（美術 PM 建議）。

| 段 | 內容 | 估計 | 模型 |
|---|---|---|---|
| 3S-1 骨架與圖層 | 側面成為紙娃娃第三套畫法（正面、背面之外）：身體、腿（兩腳前後錯開）、手、頭（鼻子、只一隻眼）、頭髮的側面版與圖層順序；身體變薄有暗面；朝東畫、朝西鏡像。照 `側面畫法.md` 移植表 | 約 1 | sonnet |
| 3S-2 頭部裝備、盾、披風 | **美術 PM 3S-1 驗收備註**：角盔兩支角要和種族角一樣「兩支都往後彎、遠側較暗」；大盔、巫師帽、寬帽、便帽、王冠目前仍是正面形狀，要做側面版。10 種頭部裝備 kind（頭盔護鼻片、兜帽開口等）、盾、披風的側面形狀 | 約 0.8 | sonnet |
| 3S-3 武器 | **美術 PM 3S-1 驗收備註**：法杖、錘等長柄武器要握在身體前方、略往前傾、頂端在臉的前面（現在直立在近側手上蓋住臉）；槍一律槍口朝面向方向（現在朝東時槍口朝後）；**劍也會蓋到一點臉，一起改成斜向前**（美術 PM 3S-2 驗收備註）。各武器 kind 的側面角度（含 3I 新武器：拳套、鐮刀、鞭、雙匕首、霰彈槍、手槍、雙手槍、魔導劍；副手）；種族部件的側面位置規則先留介面給 3R-3 | 約 0.7 | sonnet |

共通要求：影響全部用紙娃娃的單位（英雄、敵人、人形召喚物）；形態、非人形召喚物、裝備圖示不受影響。每段 vitest（各方向 × 各裝備 kind × 未知 kind 不出錯）、build、排版煙霧檢查，並 **在內建瀏覽器實際截圖對照樣張**（戰場實際大小），截圖或描述寫進報告；交美術 PM 驗收（照檢查清單）。報告 `Phase3S-N報告.md`。

## 驗收

### 3S-1（2026-10-24，開發 PM 合併；待美術 PM 對照檢查清單驗收）

- 報告 `Phase3S-1報告.md`。新檔 `client/src/render/paperdollSide.ts`（移植 `sideArt.js`）：身體變薄（15→10）＋背側暗面、兩腳錯開（`STRIDE` 0.28 弧度）、遠側手臂只露一點、近側手臂前擺持武器、頭有鼻子一隻眼；`drawFigure` 朝東／西走側面，朝西整張 `scale(-1,1)` 鏡像；南、北、倒地不變。3S-2／3S-3 的內容用最簡退回（頭盔、兜帽有簡易側面；其他頭部裝備沿用正面；盾窄橢圓；披風背後垂下；武器沿用現有畫法）。截圖 `docs/art/port/3S-1/`。
- 檢查（main）：vitest 954、build、ruff、mypy、pytest api／narrative；排版煙霧 1600×900 全 PASS；開發 PM 看過朝東 300% 截圖（側面輪廓、鼻子、單眼、錯步都在）。
- 合併時發現主資料夾 `client/node_modules` 被刪掉一部分（`.bin` 消失）：3-48h 的 worktree 用目錄連結指向主資料夾的 `node_modules`，`git worktree remove --force` 透過連結刪了內容 → 用 `corepack pnpm -C client install --offline --frozen-lockfile --force` 從本機快取還原（沒有下載）。**之後刪 worktree 前先檢查 `client/node_modules` 是不是連結，是就先移除連結。**
- 待決：`STRIDE` 是否太大、武器側面角度（3S-3）、走路動畫（不做）→ 交美術 PM 驗收時一起看。

- **美術 PM 驗收通過**（`docs/art/3S-1檢查.md`，原尺寸重拍 `docs/art/port/3S-1/doll-gallery-artpm.png`）：`STRIDE` 0.28 不改；近側手臂固定前擺、不做走路動畫，接受。

### 3S-2（2026-10-24，開發 PM 合併；待美術 PM 驗收）

- 報告 `Phase3S-2報告.md`。新檔 `client/src/render/paperdollSideGear.ts`：頭部 9 種 kind 全部側面形狀（資料實際只有 9 種，規格寫 10 種有誤）；角盔兩角都往後彎、遠側較暗先畫（`drawHornSide` 匯出給 3R-3 種族角共用）；盾（圓盾、鳶盾、塔盾）、法書、披風的側面版，法器珠沿用球體。`SideHooks` 移除 `headgearFront`、`helmetBack`（3S-3／3I-3 合併時留意）。doll-gallery 新增「⑥ 側面」。截圖 `docs/art/port/3S-2/`。
- 檢查（main）：vitest 958、build；開發 PM 看過朝東頭部截圖。
- **3S-2 美術 PM 驗收通過**（`docs/art/3S-2檢查.md`）：以實際 9 種頭部 kind 為準；角盔角 1.3 不調；盾、法書、法器珠、披風 OK。

### 3S-3（2026-10-24，開發 PM 合併；美術 PM 驗收通過，`docs/art/3S-3檢查.md`）

- 報告 `Phase3S-3報告.md`。新檔 `client/src/render/paperdollSideWeapon.ts`（各武器 kind 側面握法；長柄前傾、劍斜向前、槍口朝面向、成對副手遠側暗 30%）；`SideHooks.race`（`behind`／`face`／`head`）與 `SIDE_RACE_ANCHORS` 留給 3R-3。美術 PM：弓、槍抬到胸前接受；**小修**：成對武器遠側那把的手槍、斧、錘往前上方錯開約 3px，讓槍管或斧頭露出一截（匕首、劍、鞭不變）→ 併進 3R-3a。真側面三段全部驗收完成。
