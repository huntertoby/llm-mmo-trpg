# worktree 清理保留清單（交使用者決定）

> 2026-11-12 開發 PM 第八任重產。背景：使用者「照建議刪」後，乾淨且已併的 worktree 已刪；**下列沒有刪**，因為資料夾裡有未 commit／未追蹤的檔案。本次另把 152 個「已取消登記但資料夾殘留」的全部刪除（先拆連結再刪，其中 2 個的 `client/node_modules` 是連到主資料夾的連結，已只拆連結；刪後主資料夾 `pnpm install --frozen-lockfile` 與 build 都是 0）。F 槽可用 328 GB。

## 摘要

- **有未追蹤檔的已登記 worktree：63 個**，分支**全部已併進 main**。未追蹤的內容只有三類：
  - `scratchpad/`（agent 的暫存資料夾）：44 個
  - `.scratch_<段名>/`（舊式暫存）：19 個
  - `client/vite.<段名>.config.mts`（agent 自己的預覽設定）7 個、`bash.exe.stackdump` 1 個（與上面重疊）
  - **沒有任何一個改到已追蹤的檔案（沒有 M）**，也就是程式與文件的改動都已進 main。
- **孤兒資料夾 1 個**：`agent-a097b737cfcb276e6`（不在 git 登記，261 MB），內有 git 裡找不到的文件（例 `docs/art/3-16a檢查.md` 等舊美術檢查，上一任判斷為「git 裡找不到的兩份文件」），保留。
- 63 個合計約 33 GB（大多是各自的 `node_modules` 與 `.venv`）。

## 建議

- 63 個：暫存內容是 agent 的量測輸出與截圖草稿，分支都已併；**建議全部刪除**（同樣先拆連結再刪）。若想保險，可先把 63 個的 `scratchpad/`、`.scratch_*/` 打包成一個壓縮檔再刪。
- 孤兒 `agent-a097b737cfcb276e6`：建議先請美術 PM 確認那些舊檢查文件要不要，再決定。

## 清單（資料夾｜分支｜已併 main｜最後 commit｜大小｜未追蹤數｜內容）

| 資料夾 | 分支 | 已併 | 最後 commit | 大小 | 數 | 未追蹤內容 |
|---|---|---|---|---|---|---|
| agent-a070af488925050e1 | worktree-agent-a070af488925050e1 | yes | 11-04 | 502M | 1 | ?? scratchpad/ |
| agent-a088c0940b29b7cf2 | worktree-agent-a088c0940b29b7cf2 | yes | 11-02 | 247M | 1 | ?? .scratch_19c/ |
| agent-a0a18b6ba294581f7 | worktree-agent-a0a18b6ba294581f7 | yes | 11-05 | 871M | 1 | ?? scratchpad/ |
| agent-a0f22dac7ac58383b | worktree-agent-a0f22dac7ac58383b | yes | 11-05 | 593M | 1 | ?? scratchpad/ |
| agent-a20b1a8b124b2f2ce | worktree-agent-a20b1a8b124b2f2ce | yes | 11-05 | 1001M | 1 | ?? scratchpad/ |
| agent-a27bfec44dfc3d0cf | worktree-agent-a27bfec44dfc3d0cf | yes | 11-02 | 247M | 1 | ?? .scratch_19a/ |
| agent-a2cad846a16eb26c9 | worktree-agent-a2cad846a16eb26c9 | yes | 11-05 | 918M | 1 | ?? scratchpad/ |
| agent-a300d53eab28614f3 | worktree-agent-a300d53eab28614f3 | yes | 11-02 | 245M | 1 | ?? .scratch_5a2/ |
| agent-a31b0024ebdb89bda | worktree-agent-a31b0024ebdb89bda | yes | 11-05 | 817M | 2 | ?? client/vite.f9.config.mts;?? scratchpad/ |
| agent-a34a1a05b43bf500e | worktree-agent-a34a1a05b43bf500e | yes | 11-05 | 694M | 1 | ?? scratchpad/ |
| agent-a362e0201b24529c9 | worktree-agent-a362e0201b24529c9 | yes | 11-02 | 419M | 1 | ?? .scratch_ui/ |
| agent-a39d71366b592a6df | worktree-agent-a39d71366b592a6df | yes | 11-04 | 544M | 1 | ?? scratchpad/ |
| agent-a3a428a5e9ee98e18 | worktree-agent-a3a428a5e9ee98e18 | yes | 11-05 | 836M | 1 | ?? scratchpad/ |
| agent-a3b2fc1754e245c16 | worktree-agent-a3b2fc1754e245c16 | yes | 11-02 | 228M | 1 | ?? .scratch_18/ |
| agent-a3d9f457a31e7874b | worktree-agent-a3d9f457a31e7874b | yes | 11-04 | 338M | 2 | ?? bash.exe.stackdump;?? scratchpad/ |
| agent-a3e4519b09d8e8658 | worktree-agent-a3e4519b09d8e8658 | yes | 11-02 | 231M | 1 | ?? .scratch_15a/ |
| agent-a4265886c5b9785d8 | worktree-agent-a4265886c5b9785d8 | yes | 11-05 | 607M | 1 | ?? scratchpad/ |
| agent-a4ff26faf9076318e | worktree-agent-a4ff26faf9076318e | yes | 11-04 | 818M | 1 | ?? scratchpad/ |
| agent-a5241455b3469db6d | worktree-agent-a5241455b3469db6d | yes | 11-05 | 1.1G | 1 | ?? scratchpad/ |
| agent-a5330854d59a7eb8a | worktree-agent-a5330854d59a7eb8a | yes | 11-02 | 249M | 1 | ?? .scratch_19e/ |
| agent-a5458d6926a5cc3c7 | worktree-agent-a5458d6926a5cc3c7 | yes | 11-02 | 246M | 1 | ?? .scratch_17/ |
| agent-a556cb3a2b37f7435 | worktree-agent-a556cb3a2b37f7435 | yes | 11-05 | 401M | 1 | ?? scratchpad/ |
| agent-a6a557daf255fa5a3 | worktree-agent-a6a557daf255fa5a3 | yes | 11-05 | 875M | 1 | ?? scratchpad/ |
| agent-a6ca40810fc1e4abc | worktree-agent-a6ca40810fc1e4abc | yes | 11-02 | 252M | 1 | ?? .scratch_19d/ |
| agent-a6caef5b478d09d43 | worktree-agent-a6caef5b478d09d43 | yes | 11-02 | 251M | 1 | ?? .scratch_19b/ |
| agent-a75be397fd6c53834 | worktree-agent-a75be397fd6c53834 | yes | 11-05 | 871M | 1 | ?? scratchpad/ |
| agent-a78e97016bd372c16 | worktree-agent-a78e97016bd372c16 | yes | 11-05 | 1.5G | 2 | ?? client/vite.rt3.config.mts;?? scratchpad/ |
| agent-a7b637f269120a32a | worktree-agent-a7b637f269120a32a | yes | 11-05 | 1.6G | 2 | ?? client/vite.ue1b.config.mts;?? scratchpad/ |
| agent-a83d3f70395753abf | worktree-agent-a83d3f70395753abf | yes | 11-04 | 754M | 1 | ?? scratchpad/ |
| agent-a8f6aae1c919496e5 | worktree-agent-a8f6aae1c919496e5 | yes | 11-05 | 622M | 1 | ?? scratchpad/ |
| agent-a93b7a35365d88f07 | worktree-agent-a93b7a35365d88f07 | yes | 11-02 | 246M | 1 | ?? .scratch_5b1/ |
| agent-a98447677297d7713 | worktree-agent-a98447677297d7713 | yes | 11-04 | 719M | 1 | ?? scratchpad/ |
| agent-a99bd4db21c637f04 | worktree-agent-a99bd4db21c637f04 | yes | 11-04 | 592M | 1 | ?? scratchpad/ |
| agent-a9b18626211f4cd83 | worktree-agent-a9b18626211f4cd83 | yes | 11-05 | 619M | 1 | ?? scratchpad/ |
| agent-a9eed0fb6400874a7 | worktree-agent-a9eed0fb6400874a7 | yes | 11-02 | 439M | 1 | ?? .scratch_16/ |
| agent-aa055aff511c1ff73 | worktree-agent-aa055aff511c1ff73 | yes | 11-04 | 364M | 1 | ?? scratchpad/ |
| agent-aa2dc2876fcc5e56d | worktree-agent-aa2dc2876fcc5e56d | yes | 11-04 | 983M | 1 | ?? scratchpad/ |
| agent-aa2e5bbfa6a48f531 | worktree-agent-aa2e5bbfa6a48f531 | yes | 11-05 | 823M | 2 | ?? client/vite.f10.config.mts;?? scratchpad/ |
| agent-aa479373ce3a5f847 | worktree-agent-aa479373ce3a5f847 | yes | 11-02 | 233M | 1 | ?? .scratch_perf1/ |
| agent-aa54736eaeb966b91 | worktree-agent-aa54736eaeb966b91 | yes | 11-02 | 258M | 1 | ?? .scratch_19f/ |
| agent-aa56334ef67ea9ac2 | worktree-agent-aa56334ef67ea9ac2 | yes | 11-02 | 444M | 1 | ?? .scratch_19g/ |
| agent-aaadadb9a4fd34214 | worktree-agent-aaadadb9a4fd34214 | yes | 11-05 | 975M | 1 | ?? scratchpad/ |
| agent-aabd34b5e439ecd67 | worktree-agent-aabd34b5e439ecd67 | yes | 11-05 | 1.3G | 2 | ?? client/vite.f8.config.mts;?? scratchpad/ |
| agent-aae5938fcf60eb21f | worktree-agent-aae5938fcf60eb21f | yes | 11-02 | 246M | 1 | ?? .scratch_14a/ |
| agent-ab043c214291526cb | worktree-agent-ab043c214291526cb | yes | 11-04 | 310M | 1 | ?? scratchpad/ |
| agent-ab176d9d6ab5758a3 | worktree-agent-ab176d9d6ab5758a3 | yes | 11-05 | 827M | 1 | ?? scratchpad/ |
| agent-ab4a83c17695b31a4 | worktree-agent-ab4a83c17695b31a4 | yes | 11-05 | 613M | 1 | ?? scratchpad/ |
| agent-ac227a44c00b76db8 | worktree-agent-ac227a44c00b76db8 | yes | 11-05 | 1.4G | 2 | ?? client/vite.ue1.config.mts;?? scratchpad/ |
| agent-acfef8508028b7f12 | worktree-agent-acfef8508028b7f12 | yes | 11-05 | 907M | 1 | ?? scratchpad/ |
| agent-ad325eeff94d284d0 | worktree-agent-ad325eeff94d284d0 | yes | 11-05 | 574M | 1 | ?? scratchpad/ |
| agent-adc529dd1fdf55953 | worktree-agent-adc529dd1fdf55953 | yes | 11-05 | 602M | 1 | ?? scratchpad/ |
| agent-adcfe87cbb300be04 | worktree-agent-adcfe87cbb300be04 | yes | 11-05 | 989M | 1 | ?? scratchpad/ |
| agent-aea0bd2d545913b7b | worktree-agent-aea0bd2d545913b7b | yes | 11-05 | 984M | 1 | ?? scratchpad/ |
| agent-aea46131e98d59e0b | worktree-agent-aea46131e98d59e0b | yes | 11-02 | 251M | 1 | ?? .scratch_15b/ |
| agent-aea4734b3d1fc6f6b | worktree-agent-aea4734b3d1fc6f6b | yes | 11-05 | 445M | 1 | ?? scratchpad/ |
| agent-aeb2f7545a51b3124 | worktree-agent-aeb2f7545a51b3124 | yes | 11-05 | 582M | 1 | ?? scratchpad/ |
| agent-aee5ec8a00e2947ba | worktree-agent-aee5ec8a00e2947ba | yes | 11-04 | 362M | 1 | ?? scratchpad/ |
| agent-af3ad387ef139c271 | worktree-agent-af3ad387ef139c271 | yes | 11-05 | 798M | 1 | ?? scratchpad/ |
| agent-af40b9f5aa510f127 | worktree-agent-af40b9f5aa510f127 | yes | 11-04 | 367M | 1 | ?? scratchpad/ |
| agent-af470f03349d9a48b | worktree-agent-af470f03349d9a48b | yes | 10-31 | 250M | 1 | ?? .scratch_13d/ |
| agent-af6dc3d62b3325dcf | worktree-agent-af6dc3d62b3325dcf | yes | 11-02 | 242M | 1 | ?? .scratch_14c/ |
| agent-afe01600f587596e6 | worktree-agent-afe01600f587596e6 | yes | 11-05 | 1.6G | 2 | ?? client/vite.rt3b.config.mts;?? scratchpad/ |
| agent-aff55411f3b5f9d66 | worktree-agent-aff55411f3b5f9d66 | yes | 11-04 | 665M | 1 | ?? scratchpad/ |
