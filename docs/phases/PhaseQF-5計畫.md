# Phase QF-5 計畫：前端小修合併段（佇列 (aa)、(o)、(h)、(q)）

> 來源：開發 PM 交接佇列 (aa)、(o)、(h)、(q)。
> - (aa)：美術 `docs/art/CR-1c驗收.md`，小修 1。
> - (o)：規則 `docs/design/08-裝備.md` 8.29 E5 第 7 點。
> - (q)：WL-2 的裁定 1、4。
>
> 和 QF-6 平行。QF-6 只改後端的 `src/trpg/content/`、`src/trpg/engine/ai/`、`src/trpg/skillgen/`、`src/trpg/api/tuning/objects.py`，這段都不要碰。

## 範圍

1. **(aa) 切段規則**：`WrapUnits` 多兩條切段規則：
   - 全形「（」前面切段；
   - 「，」後面切段，「，」留在前一段的尾巴。
   - 800 寬時，下面三處都不能再斷在詞的中間：「（期望 69.3）」「（全身上限 300%）」「攻擊預覽時才算」。
2. **(o) 技能卡加註**：同一招有兩個以上裝備給的變形時，沒生效的變形在技能卡註明「已有其他變形」。生效的是哪一個，以後端算的為準，前端不自己判斷。後端如果還沒把這個資訊傳出來，用現有的、最小的做法補上，報告寫明。
3. **(h) 刪參數**：刪掉 `skeletonName` 沒有人用的 override 參數。位置在 `client/src/render/skillIcon.ts` 一帶。
4. **(q) 試打面板讀 role**：前端 `TryoutPanel`、`tryout.ts` 改讀 API 地圖摘要的 `role`，並且照 WL-1 b 的做法，加上 role 的存在檢查。

## 不做

- 不改規則，不改數值，不改 `docs/design/`、`config/` 既有的值。

## 驗收

- **結果不變**：442 招、78 場、census 小樣本都要 different=0。
- **測試**：每一項至少一個測試。(aa) 要測三處斷句；(o) 要測有兩個變形、只有一個變形這兩種情況。
- **截圖**：存到 `docs/art/shots/qf-5/`，交美術 PM：
  - 預覽面板 800 寬一張；
  - 單位卡 800 寬一張；
  - 有「已有其他變形」的技能卡 1600 寬一張。
- **靜態檢查**，結束碼都要是 0：
  - ruff、format、mypy、lint-imports
  - tsc、vitest、build
- **全量檢查**：全部 commit 之後，用 SendMessage 問開發 PM「QF-5 準備跑 check.py」。**收到「可以跑」才跑** `check.py --all`，在那之前不要交件。
- **commit 與報告**：每項一個 commit。報告寫在 `docs/phases/PhaseQF-5報告.md`。
