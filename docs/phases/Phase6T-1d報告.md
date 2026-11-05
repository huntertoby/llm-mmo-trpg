# Phase 6T-1d 報告（WIP：使用者要重開電腦，中途收尾）

實作者，2026-11-05。依據：`docs/art/6T-1c檢查.md`。只改 `client/`；沒碰遇敵卡、背包、雇用面板，也沒碰紙娃娃部件。

## 已完成（程式與 vitest，**還沒截圖**）

1. **soot 位置**（`b90dd4a5`）：`render/portrait.ts` 的 soot 從嘴邊 (4.4, −38.4) 3.6×1.9 移到右頰 (5.8, −40) 2.4×1.5、斜 −0.35，
   畫之前用臉形橢圓 (0, −42) 8.4×7.9 裁切（`ctx.clip`），不會溢出下顎。參數匯出成 `SOOT_*` 常數；只調參數加裁切，沒動部件。
   位置在鬍子上緣（x≈5.8 時約 −38.4）之上，帶鬍子的 NPC（鉚釘、兩位鐵匠、爐叔）也不會畫在鬍子上。
   測試：`portrait.test.ts`「6T-1d … soot 在臉頰、裁在臉內」兩項。
2. **小修 3「寄出」固定在面板底部**（`5118c191`）：`.mail-actions` 移到兩欄格線外（新的 `.mail-send-wrap`），
   `position: sticky; bottom: 0`、不透明底、上緣細金線＋12px 漸隱，z-index 6 蓋過捲動區下緣漸隱。
3. **小修 4 捲動區上緣**：只對郵寄面板（`.world-hud-panel[data-panel="mail"]`），上緣色塊改成實色 22px＋細金線（原本共用 56px 漸隱的下半段半透明）。
4. **小修 5 浮動卡避開標題**：共用 `floatPlacement` 加選填參數 `prefer`（預設 `above`，行為不變），`FloatCard`／`Hint` 加 `prefer` prop；
   附件格的 −、＋、×、裝備格的說明卡改 `prefer="below"`，下方放不下才翻到上方。
5. **小修 6 青石郵筒的苔**：苔斑 `#2a5e18`→`#1a4210`、大 1.2 倍、墨線 0.6→0.9，亮點 `#8ac850`→`#9ad858`（`POSTBOX_MOSS*`）。
6. **小修 7 全遊戲主要按鈕**（`8756bb0d`）：`base.css` 加 `button.primary:hover:not(:disabled)`（亮一階 `#4d6cb3`）與
   `button.primary:disabled`（深灰 `#36364a`，再加原本的 0.45 半透明）；拿掉郵寄面板自己的那條滑過規則；
   `entry.css` 加 `.entry-skin button.primary:disabled`（灰漸層），建角／首頁停用時也是灰。
   測試：`client/src/world/mail6t1d.test.ts`（按鈕規則、寄出黏底、上緣實色、prefer below、苔的亮度）。

已跑：相關 vitest 5 檔 72 項通過；`corepack pnpm -C client build` 結束碼 0（中途一次，非交件前最後一次）。

## 還沒做

- **所有截圖**（`6t1d_*`）：soot（灰鴿 1600／800、鉚釘、工坊師傅、主城鐵匠、爐叔，各附 zoom）、寄出黏底、捲動上緣、浮動卡釘住、
  青石郵筒、主要按鈕滑過＋停用對照（1600、800），以及 6.5.1 浮動卡實測。
- 交件前：client 全部 vitest、build 結束碼、排版煙霧檢查三尺寸。
- 主要按鈕各處（郵寄、建角、確認框、戰鬥結束）的實機停用檢查。

## 下一步（接手照做）

- 截圖環境已備好在 session scratchpad 的 `t1d/`：`serve.py`（埠 8126，掛這個 worktree 的 `client/dist`）、`launch.mjs`（無頭 Chrome，CDP 9483、`--mute-audio`）、
  `lib.mjs`／`common.mjs`（已改成 8126／9483、輸出到這個 worktree 的 `docs/art`）、`smoke.mjs`。
  `mailsaves` 是 6T-1c 存檔的複本，已用 `seed_extra.py` 多建三個角色（`mail_ids.json` 的 `lu`：爐叔鐵鋪室內爐叔南邊；`hire`：主城傭兵管事南邊；`work`：主城工坊師傅南邊，都面向北，按 E 開面板）。
  6T-1c 的 `t1c/shots.mjs`、`float.mjs` 改路徑後可沿用。
- 主城鐵匠（`capital_smithy` 的 smithy 設施）的頭像在遊戲裡沒有顯示的地方，要用開發頁畫（例如在 `dev/storyGallery.tsx` 加一列帶 soot 的頭像）。
- soot 如果截圖看起來還不對，只能再調 `SOOT_*` 常數；再不行就照檢查寫進待決、留到 QK。

## 待 PM 決定（目前想到的）

1. 上緣實色色塊只套在郵寄面板；其他面板仍是共用的 56px 漸隱。要全面改的話改 `theme.css`。
2. 用 `primary` 當「選中」狀態的切換鈕（分頁、武器、關鍵字等）在 busy 停用時也會變灰。

## 啟動過的程序與 PID

- 預覽伺服器 `uv run python t1d/serve.py`（背景工作，啟動中就被停掉，沒有開始聽 8126）。
- 無頭 Chrome PID 65248（含子程序），已用 `taskkill /F /T /PID 65248` 結束。8126、9483 都確認沒有在聽。
- 沒用 8000、8001、8010；沒碰 `tmp_x`、`saves/`。`uv sync` 在 worktree 建了 `.venv`，`pnpm install` 裝了 `client/node_modules`（都不 commit）。
