# worktree 清理候選（只列清單，沒有刪任何東西）

> 2026-11-12 整理 agent 產生（掃描時間 2026-11-12 14:27）。**本檔只是清單**：沒有執行 `git worktree remove`、`rm`、`prune`。要刪由開發 PM 在沒有 agent 執行時決定。
> 判準：分支已併進本機 `main`（`git merge-base --is-ancestor <分支> main`）、**而且**資料夾內所有檔案（含 `node_modules`、`.venv`，不跟隨 junction／symlink）最新修改時間超過 7 天（早於 2026-11-05）。最近 7 天內動過的（含今天 11-12 動過的）、locked 的、沒併進 main 的一律排除。
> 大小是資料夾內檔案的表面大小加總；`.venv` 可能是 hardlink，實際可收回的磁碟會略少。

## 摘要

- `.claude/worktrees/` 下資料夾 434 個；`git worktree list` 登記 408 個（含主資料夾與 scratchpad 裡的）。
- **候選 A（已登記、已併進 main、超過 7 天沒動、未 locked）：315 個，合計 117.20 GB**。
- **候選 B（孤兒資料夾：不在 `git worktree list`、超過 7 天沒動）：35 個，合計 7.86 GB**。
- **A＋B 總計：350 個，125.06 GB**。
- 排除：7 天內動過 84 個；超過 7 天但分支沒併進 main 0 個；已併但 locked 0 個；7 天內動過的孤兒 0 個。
- 登記了但資料夾已不存在（只佔 `.git/worktrees/` 中繼資料，`git worktree prune` 的對象）：5 個。
- `.claude/worktrees/` 根目錄雜檔：`base.sha`, `probe.py`, `sweep.out`, `vite5197.pid`。

## 候選 A：已併進 main、超過 7 天沒動

| 資料夾 | 分支 | 最新修改 | 天數 | 大小 |
|---|---|---|---|---|
| `agent-af72d4dceb01164ba` | `worktree-agent-af72d4dceb01164ba` | 2026-10-29 01:19 | 15 | 0.36 GB |
| `agent-ac95f700a5d839aa7` | `worktree-agent-ac95f700a5d839aa7` | 2026-10-29 01:19 | 15 | 0.36 GB |
| `agent-abc8d8bb31b1958dd` | `worktree-agent-abc8d8bb31b1958dd` | 2026-10-29 01:57 | 15 | 0.36 GB |
| `agent-aaf64e1b29cf5c8cd` | `worktree-agent-aaf64e1b29cf5c8cd` | 2026-10-29 02:31 | 14 | 0.35 GB |
| `agent-a272f521fd87ef8dd` | `worktree-agent-a272f521fd87ef8dd` | 2026-10-29 02:36 | 14 | 0.36 GB |
| `agent-a41b8accbf1755e36` | `worktree-agent-a41b8accbf1755e36` | 2026-10-29 02:46 | 14 | 0.34 GB |
| `agent-a9406e2f878abffdc` | `worktree-agent-a9406e2f878abffdc` | 2026-10-29 03:08 | 14 | 0.35 GB |
| `agent-a710c413ed321c3da` | `worktree-agent-a710c413ed321c3da` | 2026-10-29 03:20 | 14 | 0.36 GB |
| `agent-a1ba712d32d6e9b64` | `worktree-agent-a1ba712d32d6e9b64` | 2026-10-29 03:25 | 14 | 0.35 GB |
| `agent-a416f949f47810563` | `worktree-agent-a416f949f47810563` | 2026-10-29 04:02 | 14 | 0.35 GB |
| `agent-a2e916e2711977d6d` | `worktree-agent-a2e916e2711977d6d` | 2026-10-29 04:12 | 14 | 0.35 GB |
| `agent-a8dc496fe76081896` | `worktree-agent-a8dc496fe76081896` | 2026-10-29 04:17 | 14 | 0.36 GB |
| `agent-a2d7170837c924b27` | `worktree-agent-a2d7170837c924b27` | 2026-10-29 05:50 | 14 | 0.37 GB |
| `agent-a303b66550740959b` | `worktree-agent-a303b66550740959b` | 2026-10-29 06:12 | 14 | 0.19 GB |
| `agent-a9ec5e799a6084351` | `worktree-agent-a9ec5e799a6084351` | 2026-10-29 06:40 | 14 | 0.37 GB |
| `agent-a24be93ebcbeb346f` | `worktree-agent-a24be93ebcbeb346f` | 2026-10-29 07:20 | 14 | 0.19 GB |
| `agent-a57fe5b3c2a7e0762` | `worktree-agent-a57fe5b3c2a7e0762` | 2026-10-29 07:21 | 14 | 0.37 GB |
| `agent-a6fb01091f69e4ec1` | `worktree-agent-a6fb01091f69e4ec1` | 2026-10-29 08:10 | 14 | 0.20 GB |
| `agent-aa5e21d1a5d4c06ae` | `worktree-agent-aa5e21d1a5d4c06ae` | 2026-10-29 08:11 | 14 | 0.35 GB |
| `agent-a8849f8e06541eb77` | `worktree-agent-a8849f8e06541eb77` | 2026-10-29 08:46 | 14 | 0.36 GB |
| `agent-a50e6108b9898754c` | `worktree-agent-a50e6108b9898754c` | 2026-10-29 08:55 | 14 | 0.37 GB |
| `agent-aca4845a31e23ac79` | `worktree-agent-aca4845a31e23ac79` | 2026-10-29 09:03 | 14 | 0.36 GB |
| `agent-a50c1d87d55ed9c54` | `worktree-agent-a50c1d87d55ed9c54` | 2026-10-29 09:35 | 14 | 0.37 GB |
| `agent-ae080affef05e3342` | `worktree-agent-ae080affef05e3342` | 2026-10-29 09:45 | 14 | 0.20 GB |
| `agent-a568cda06af46cfc1` | `worktree-agent-a568cda06af46cfc1` | 2026-10-29 09:46 | 14 | 0.28 GB |
| `agent-ad9899cffcabe748d` | `worktree-agent-ad9899cffcabe748d` | 2026-10-29 10:03 | 14 | 0.36 GB |
| `agent-aff575ad0ac7a47ac` | `worktree-agent-aff575ad0ac7a47ac` | 2026-10-29 10:06 | 14 | 0.28 GB |
| `agent-a13e0f685d5b7bbc4` | `worktree-agent-a13e0f685d5b7bbc4` | 2026-10-29 10:41 | 14 | 0.20 GB |
| `agent-a09d191338076f35b` | `worktree-agent-a09d191338076f35b` | 2026-10-29 11:08 | 14 | 0.20 GB |
| `agent-a5559201fec565e12` | `worktree-agent-a5559201fec565e12` | 2026-10-29 11:34 | 14 | 0.36 GB |
| `agent-acdf5032382e5323f` | `worktree-agent-acdf5032382e5323f` | 2026-10-29 12:09 | 14 | 0.20 GB |
| `agent-ace5abb53d355b507` | `worktree-agent-ace5abb53d355b507` | 2026-10-29 12:31 | 14 | 0.20 GB |
| `agent-a578a8c732da6f6ee` | `worktree-agent-a578a8c732da6f6ee` | 2026-10-29 12:41 | 14 | 0.20 GB |
| `agent-a036da51ae41c7243` | `worktree-agent-a036da51ae41c7243` | 2026-10-29 13:30 | 14 | 0.20 GB |
| `agent-af465f8d30846e199` | `worktree-agent-af465f8d30846e199` | 2026-10-29 13:58 | 14 | 0.20 GB |
| `agent-abfe2fe39d105ed80` | `worktree-agent-abfe2fe39d105ed80` | 2026-10-29 13:59 | 14 | 0.38 GB |
| `agent-a0ba165c2d289baa4` | `worktree-agent-a0ba165c2d289baa4` | 2026-10-29 14:41 | 14 | 0.20 GB |
| `agent-a5d017bf87514e95f` | `worktree-agent-a5d017bf87514e95f` | 2026-10-29 15:16 | 14 | 0.20 GB |
| `agent-afcdab95d91ca79ef` | `worktree-agent-afcdab95d91ca79ef` | 2026-10-29 15:51 | 14 | 0.36 GB |
| `agent-a52a18f90fd80ee53` | `worktree-agent-a52a18f90fd80ee53` | 2026-10-29 16:57 | 14 | 0.36 GB |
| `agent-a57073d112a37c3c8` | `worktree-agent-a57073d112a37c3c8` | 2026-10-29 17:00 | 14 | 0.37 GB |
| `agent-ab7bed1e1ba829dcf` | `worktree-agent-ab7bed1e1ba829dcf` | 2026-10-29 17:07 | 14 | 0.37 GB |
| `agent-ad11f2e41363d65d8` | `worktree-agent-ad11f2e41363d65d8` | 2026-10-29 17:14 | 14 | 0.37 GB |
| `agent-a8e889593c2888db3` | `worktree-agent-a8e889593c2888db3` | 2026-10-29 17:22 | 14 | 0.38 GB |
| `agent-a49c107fba249a694` | `worktree-agent-a49c107fba249a694` | 2026-10-29 18:40 | 14 | 0.21 GB |
| `agent-adf2089a8e47d2f90` | `worktree-agent-adf2089a8e47d2f90` | 2026-10-29 19:09 | 14 | 0.21 GB |
| `agent-aae78ab052111d12d` | `worktree-agent-aae78ab052111d12d` | 2026-10-29 19:18 | 14 | 0.21 GB |
| `agent-a5b72c60d666dcd5e` | `worktree-agent-a5b72c60d666dcd5e` | 2026-10-29 19:57 | 14 | 0.21 GB |
| `agent-ad6e221209e800b66` | `worktree-agent-ad6e221209e800b66` | 2026-10-29 20:27 | 14 | 0.21 GB |
| `agent-a8215e5e6a417b6cc` | `worktree-agent-a8215e5e6a417b6cc` | 2026-10-29 20:31 | 14 | 0.21 GB |
| `agent-af23b95f74e78933c` | `worktree-agent-af23b95f74e78933c` | 2026-10-29 20:55 | 14 | 0.39 GB |
| `agent-aa45f7cd9997b6931` | `worktree-agent-aa45f7cd9997b6931` | 2026-10-29 22:33 | 14 | 0.38 GB |
| `agent-a8e268c6e58b1df98` | `worktree-agent-a8e268c6e58b1df98` | 2026-10-29 23:01 | 14 | 0.38 GB |
| `agent-a7f5d2ddf3c80941e` | `worktree-agent-a7f5d2ddf3c80941e` | 2026-10-30 00:42 | 14 | 0.38 GB |
| `agent-ab8c2ac253e7687c6` | `worktree-agent-ab8c2ac253e7687c6` | 2026-10-30 01:26 | 14 | 0.21 GB |
| `agent-aa5ddbbd4da8bc770` | `worktree-agent-aa5ddbbd4da8bc770` | 2026-10-30 02:29 | 13 | 0.39 GB |
| `agent-ac79968531f4257be` | `worktree-agent-ac79968531f4257be` | 2026-10-30 03:33 | 13 | 0.39 GB |
| `agent-a34ff5385e4216f33` | `worktree-agent-a34ff5385e4216f33` | 2026-10-30 04:04 | 13 | 0.39 GB |
| `agent-ad08db7318c0164c3` | `worktree-agent-ad08db7318c0164c3` | 2026-10-30 04:05 | 13 | 0.21 GB |
| `agent-acdfb1e39a6b05cd9` | `worktree-agent-acdfb1e39a6b05cd9` | 2026-10-30 04:20 | 13 | 0.39 GB |
| `agent-a82bd2ad04a055836` | `worktree-agent-a82bd2ad04a055836` | 2026-10-30 04:56 | 13 | 0.39 GB |
| `agent-ad399c4b20867f0fd` | `worktree-agent-ad399c4b20867f0fd` | 2026-10-30 05:36 | 13 | 0.39 GB |
| `agent-a6ae8d83cfb9823cd` | `worktree-agent-a6ae8d83cfb9823cd` | 2026-10-30 10:21 | 13 | 0.20 GB |
| `agent-a419346738f4fc3f5` | `worktree-agent-a419346738f4fc3f5` | 2026-10-30 11:32 | 13 | 0.21 GB |
| `agent-a808aa785b001af38` | `worktree-agent-a808aa785b001af38` | 2026-10-30 11:58 | 13 | 0.21 GB |
| `agent-a6fa7856f788bca24` | `worktree-agent-a6fa7856f788bca24` | 2026-10-30 13:19 | 13 | 0.21 GB |
| `agent-aa9082b7367b3d21c` | `worktree-agent-aa9082b7367b3d21c` | 2026-10-30 13:31 | 13 | 0.21 GB |
| `agent-a694ba18cc1554fbf` | `worktree-agent-a694ba18cc1554fbf` | 2026-10-30 13:51 | 13 | 0.21 GB |
| `agent-a76da451bb0f948d2` | `worktree-agent-a76da451bb0f948d2` | 2026-10-30 15:05 | 13 | 0.39 GB |
| `agent-a623b1371faf0f028` | `worktree-agent-a623b1371faf0f028` | 2026-10-30 15:51 | 13 | 0.21 GB |
| `agent-a58ad78bf1f4764cf` | `worktree-agent-a58ad78bf1f4764cf` | 2026-10-30 16:08 | 13 | 0.21 GB |
| `agent-a189297fea600eb73` | `worktree-agent-a189297fea600eb73` | 2026-10-30 16:10 | 13 | 0.20 GB |
| `agent-a4b97eca35561cbc5` | `worktree-agent-a4b97eca35561cbc5` | 2026-10-30 17:15 | 13 | 0.21 GB |
| `agent-a8ff06e5407ee5daf` | `worktree-agent-a8ff06e5407ee5daf` | 2026-10-30 18:39 | 13 | 0.21 GB |
| `agent-ab7d775f430ba79df` | `worktree-agent-ab7d775f430ba79df` | 2026-10-30 20:26 | 13 | 0.39 GB |
| `agent-a68fd72beb21b46cb` | `worktree-agent-a68fd72beb21b46cb` | 2026-10-30 21:30 | 13 | 0.38 GB |
| `agent-ab97a175aec7c80d7` | `worktree-agent-ab97a175aec7c80d7` | 2026-10-30 22:30 | 13 | 0.21 GB |
| `agent-a523b2f944be7d3f3` | `worktree-agent-a523b2f944be7d3f3` | 2026-10-30 23:34 | 13 | 0.39 GB |
| `agent-af8de0734ada1a1ae` | `worktree-agent-af8de0734ada1a1ae` | 2026-10-31 00:21 | 13 | 0.20 GB |
| `agent-af172f25e0e22daf7` | `worktree-agent-af172f25e0e22daf7` | 2026-10-31 01:09 | 13 | 0.21 GB |
| `agent-a1f1e269743ca4ac7` | `worktree-agent-a1f1e269743ca4ac7` | 2026-10-31 01:12 | 13 | 0.21 GB |
| `agent-a3d5563b5e5c9de7f` | `worktree-agent-a3d5563b5e5c9de7f` | 2026-10-31 01:36 | 13 | 0.19 GB |
| `agent-adfeaf219776b0cd3` | `worktree-agent-adfeaf219776b0cd3` | 2026-10-31 01:44 | 13 | 0.21 GB |
| `agent-a6f2cd2c925e8aee7` | `worktree-agent-a6f2cd2c925e8aee7` | 2026-10-31 01:51 | 13 | 0.39 GB |
| `agent-a57caef985474f37d` | `worktree-agent-a57caef985474f37d` | 2026-10-31 02:27 | 12 | 0.20 GB |
| `agent-a4fa7f4cb7d3337a0` | `worktree-agent-a4fa7f4cb7d3337a0` | 2026-10-31 02:46 | 12 | 0.21 GB |
| `agent-a5eccbf3237a80a2c` | `worktree-agent-a5eccbf3237a80a2c` | 2026-10-31 02:50 | 12 | 0.21 GB |
| `agent-a1c5386495e64e5d7` | `worktree-agent-a1c5386495e64e5d7` | 2026-10-31 03:14 | 12 | 0.21 GB |
| `agent-a3eecfc391f779dc9` | `worktree-agent-a3eecfc391f779dc9` | 2026-10-31 03:29 | 12 | 0.21 GB |
| `agent-a1d1414029e58956e` | `worktree-agent-a1d1414029e58956e` | 2026-10-31 03:50 | 12 | 0.20 GB |
| `agent-a228fcd54a0c4e01a` | `worktree-agent-a228fcd54a0c4e01a` | 2026-10-31 04:30 | 12 | 0.21 GB |
| `agent-af30191ddd0c83396` | `worktree-agent-af30191ddd0c83396` | 2026-10-31 04:41 | 12 | 0.22 GB |
| `agent-a5b3a46b95ae22500` | `worktree-agent-a5b3a46b95ae22500` | 2026-10-31 05:13 | 12 | 0.22 GB |
| `agent-a4c1659c1e62eb7b6` | `worktree-agent-a4c1659c1e62eb7b6` | 2026-10-31 06:43 | 12 | 0.22 GB |
| `agent-ae94c46d3d7c23a74` | `worktree-agent-ae94c46d3d7c23a74` | 2026-10-31 07:48 | 12 | 0.22 GB |
| `agent-a525151e418033100` | `worktree-agent-a525151e418033100` | 2026-10-31 09:16 | 12 | 0.22 GB |
| `agent-a988b16a111c59837` | `worktree-agent-a988b16a111c59837` | 2026-10-31 10:45 | 12 | 0.22 GB |
| `agent-a84c124dbe72fadfe` | `worktree-agent-a84c124dbe72fadfe` | 2026-10-31 19:00 | 12 | 0.22 GB |
| `agent-aa7125bb51c519221` | `worktree-agent-aa7125bb51c519221` | 2026-10-31 20:00 | 12 | 0.21 GB |
| `agent-a8e2d54eb344eca2e` | `worktree-agent-a8e2d54eb344eca2e` | 2026-10-31 20:10 | 12 | 0.21 GB |
| `agent-a292f2ac039ce7eba` | `worktree-agent-a292f2ac039ce7eba` | 2026-10-31 20:53 | 12 | 0.21 GB |
| `agent-a1d1d162a68b42d90` | `worktree-agent-a1d1d162a68b42d90` | 2026-10-31 21:17 | 12 | 0.22 GB |
| `agent-afd6cbd8b4226a13a` | `worktree-agent-afd6cbd8b4226a13a` | 2026-10-31 21:26 | 12 | 0.22 GB |
| `agent-af470f03349d9a48b` | `worktree-agent-af470f03349d9a48b` | 2026-10-31 23:26 | 12 | 0.23 GB |
| `agent-aae5938fcf60eb21f` | `worktree-agent-aae5938fcf60eb21f` | 2026-11-02 12:47 | 10 | 0.23 GB |
| `agent-af6dc3d62b3325dcf` | `worktree-agent-af6dc3d62b3325dcf` | 2026-11-02 13:20 | 10 | 0.22 GB |
| `agent-a3e4519b09d8e8658` | `worktree-agent-a3e4519b09d8e8658` | 2026-11-02 13:32 | 10 | 0.21 GB |
| `agent-aea46131e98d59e0b` | `worktree-agent-aea46131e98d59e0b` | 2026-11-02 14:49 | 10 | 0.23 GB |
| `agent-a1cf20793a42a231b` | `worktree-agent-a1cf20793a42a231b` | 2026-11-02 15:50 | 10 | 0.23 GB |
| `agent-a9eed0fb6400874a7` | `worktree-agent-a9eed0fb6400874a7` | 2026-11-02 17:51 | 10 | 0.40 GB |
| `agent-a362e0201b24529c9` | `worktree-agent-a362e0201b24529c9` | 2026-11-02 18:06 | 10 | 0.39 GB |
| `agent-a5458d6926a5cc3c7` | `worktree-agent-a5458d6926a5cc3c7` | 2026-11-02 18:31 | 10 | 0.23 GB |
| `agent-a3b2fc1754e245c16` | `worktree-agent-a3b2fc1754e245c16` | 2026-11-02 18:57 | 10 | 0.21 GB |
| `agent-aa479373ce3a5f847` | `worktree-agent-aa479373ce3a5f847` | 2026-11-02 19:18 | 10 | 0.21 GB |
| `agent-a27bfec44dfc3d0cf` | `worktree-agent-a27bfec44dfc3d0cf` | 2026-11-02 19:33 | 10 | 0.23 GB |
| `agent-a6caef5b478d09d43` | `worktree-agent-a6caef5b478d09d43` | 2026-11-02 19:56 | 10 | 0.23 GB |
| `agent-a088c0940b29b7cf2` | `worktree-agent-a088c0940b29b7cf2` | 2026-11-02 20:13 | 10 | 0.23 GB |
| `agent-a6ca40810fc1e4abc` | `worktree-agent-a6ca40810fc1e4abc` | 2026-11-02 20:27 | 10 | 0.23 GB |
| `agent-a5330854d59a7eb8a` | `worktree-agent-a5330854d59a7eb8a` | 2026-11-02 20:53 | 10 | 0.23 GB |
| `agent-a5aee3b91f092b474` | `worktree-agent-a5aee3b91f092b474` | 2026-11-02 21:40 | 10 | 0.22 GB |
| `agent-a01d302b606517e8b` | `worktree-agent-a01d302b606517e8b` | 2026-11-02 21:51 | 10 | 0.11 GB |
| `agent-a22f7a812026efabe` | `worktree-agent-a22f7a812026efabe` | 2026-11-02 22:03 | 10 | 0.22 GB |
| `agent-aa54736eaeb966b91` | `worktree-agent-aa54736eaeb966b91` | 2026-11-02 22:12 | 10 | 0.24 GB |
| `agent-a300d53eab28614f3` | `worktree-agent-a300d53eab28614f3` | 2026-11-02 22:19 | 10 | 0.23 GB |
| `agent-aa56334ef67ea9ac2` | `worktree-agent-aa56334ef67ea9ac2` | 2026-11-02 22:42 | 10 | 0.41 GB |
| `agent-aa79e1066a98c371a` | `worktree-agent-aa79e1066a98c371a` | 2026-11-02 22:45 | 10 | 0.40 GB |
| `agent-aeb59f69fde058e6f` | `worktree-agent-aeb59f69fde058e6f` | 2026-11-02 23:07 | 10 | 0.23 GB |
| `agent-a93b7a35365d88f07` | `worktree-agent-a93b7a35365d88f07` | 2026-11-02 23:18 | 10 | 0.23 GB |
| `agent-a956b94f63ce83bc4` | `worktree-agent-a956b94f63ce83bc4` | 2026-11-02 23:30 | 10 | 0.23 GB |
| `agent-aa79651bb3b9f55e9` | `worktree-agent-aa79651bb3b9f55e9` | 2026-11-02 23:46 | 10 | 0.23 GB |
| `agent-ae2cb5113e24c37a6` | `worktree-agent-ae2cb5113e24c37a6` | 2026-11-03 00:09 | 10 | 0.41 GB |
| `agent-a00934240bf7732ff` | `worktree-agent-a00934240bf7732ff` | 2026-11-03 00:18 | 10 | 0.23 GB |
| `agent-a22f7700111683e9a` | `worktree-agent-a22f7700111683e9a` | 2026-11-03 00:21 | 10 | 0.23 GB |
| `agent-aaab80ebf667db26f` | `worktree-agent-aaab80ebf667db26f` | 2026-11-03 00:44 | 10 | 0.23 GB |
| `agent-a59df441bd986e0a3` | `worktree-agent-a59df441bd986e0a3` | 2026-11-03 01:01 | 10 | 0.21 GB |
| `agent-a089560d877d780b6` | `worktree-agent-a089560d877d780b6` | 2026-11-03 01:16 | 10 | 0.41 GB |
| `agent-aa3b09e5c0e5e8514` | `worktree-agent-aa3b09e5c0e5e8514` | 2026-11-03 01:44 | 10 | 0.23 GB |
| `agent-aaecfa32380c58988` | `worktree-agent-aaecfa32380c58988` | 2026-11-03 01:46 | 10 | 0.41 GB |
| `agent-ab4a035db3138f682` | `worktree-agent-ab4a035db3138f682` | 2026-11-03 02:12 | 10 | 0.23 GB |
| `agent-a553fa35b8627846a` | `worktree-agent-a553fa35b8627846a` | 2026-11-03 02:32 | 9 | 0.41 GB |
| `agent-a8db662b8e80c0442` | `worktree-agent-a8db662b8e80c0442` | 2026-11-03 02:44 | 9 | 0.23 GB |
| `agent-a9229afd689761d05` | `worktree-agent-a9229afd689761d05` | 2026-11-03 03:02 | 9 | 0.24 GB |
| `agent-ac1a2f990a08caea4` | `worktree-agent-ac1a2f990a08caea4` | 2026-11-03 03:27 | 9 | 0.41 GB |
| `agent-a96978f59efacfedb` | `worktree-agent-a96978f59efacfedb` | 2026-11-03 03:49 | 9 | 0.41 GB |
| `agent-ac7cd06c9e9341422` | `worktree-agent-ac7cd06c9e9341422` | 2026-11-03 03:56 | 9 | 0.23 GB |
| `agent-abebd74b90652ea82` | `worktree-agent-abebd74b90652ea82` | 2026-11-03 04:16 | 9 | 0.41 GB |
| `agent-a66ec0802a1a59f17` | `worktree-agent-a66ec0802a1a59f17` | 2026-11-03 04:38 | 9 | 0.42 GB |
| `agent-a80b84be41872ba8f` | `worktree-agent-a80b84be41872ba8f` | 2026-11-03 05:00 | 9 | 0.41 GB |
| `agent-abd344ad0d608ef05` | `worktree-agent-abd344ad0d608ef05` | 2026-11-03 05:11 | 9 | 0.41 GB |
| `agent-af1c9272754be5977` | `worktree-agent-af1c9272754be5977` | 2026-11-03 05:44 | 9 | 0.41 GB |
| `agent-ab500a8091cd2560e` | `worktree-agent-ab500a8091cd2560e` | 2026-11-03 06:00 | 9 | 0.24 GB |
| `agent-a37ccddc72f920357` | `worktree-agent-a37ccddc72f920357` | 2026-11-03 06:30 | 9 | 0.23 GB |
| `agent-a06f68f440a38bf3d` | `worktree-agent-a06f68f440a38bf3d` | 2026-11-03 06:46 | 9 | 0.41 GB |
| `agent-ae02a3196c240ef90` | `worktree-agent-ae02a3196c240ef90` | 2026-11-03 07:00 | 9 | 0.23 GB |
| `agent-ac6994087c3a2e084` | `worktree-agent-ac6994087c3a2e084` | 2026-11-03 07:25 | 9 | 0.41 GB |
| `agent-a88c4c520ae4fc5de` | `worktree-agent-a88c4c520ae4fc5de` | 2026-11-03 07:39 | 9 | 0.41 GB |
| `agent-a8742e6ee67fdb5a7` | `worktree-agent-a8742e6ee67fdb5a7` | 2026-11-03 07:55 | 9 | 0.23 GB |
| `agent-abdd6f77bb7843351` | `worktree-agent-abdd6f77bb7843351` | 2026-11-03 08:14 | 9 | 0.41 GB |
| `agent-a435f68d9e49538f2` | `worktree-agent-a435f68d9e49538f2` | 2026-11-03 08:14 | 9 | 0.23 GB |
| `agent-ae94e77e5cb38e9a2` | `worktree-agent-ae94e77e5cb38e9a2` | 2026-11-03 08:35 | 9 | 0.41 GB |
| `agent-abeb5c7186c59e106` | `worktree-agent-abeb5c7186c59e106` | 2026-11-03 08:51 | 9 | 0.23 GB |
| `agent-a506e9f0dd780ea0e` | `worktree-agent-a506e9f0dd780ea0e` | 2026-11-03 08:58 | 9 | 0.41 GB |
| `agent-aa4aa55b3f4412bda` | `worktree-agent-aa4aa55b3f4412bda` | 2026-11-03 09:24 | 9 | 0.41 GB |
| `agent-aa22b0b183fe670c3` | `worktree-agent-aa22b0b183fe670c3` | 2026-11-03 09:34 | 9 | 0.41 GB |
| `agent-acb78ad536376f785` | `worktree-agent-acb78ad536376f785` | 2026-11-03 09:46 | 9 | 0.23 GB |
| `agent-a98875a066929f09e` | `worktree-agent-a98875a066929f09e` | 2026-11-03 09:55 | 9 | 0.41 GB |
| `agent-a3a923a4d784b7c7e` | `worktree-agent-a3a923a4d784b7c7e` | 2026-11-03 10:17 | 9 | 0.25 GB |
| `agent-a7e8d3816cb360bd8` | `worktree-agent-a7e8d3816cb360bd8` | 2026-11-03 10:25 | 9 | 0.43 GB |
| `agent-aa6a5bca824f841be` | `worktree-agent-aa6a5bca824f841be` | 2026-11-03 10:33 | 9 | 0.24 GB |
| `agent-acb59950112fe2535` | `worktree-agent-acb59950112fe2535` | 2026-11-03 11:14 | 9 | 0.42 GB |
| `agent-a433beb4cbd535617` | `worktree-agent-a433beb4cbd535617` | 2026-11-03 11:24 | 9 | 0.42 GB |
| `agent-a16ea74d8e0fc9475` | `worktree-agent-a16ea74d8e0fc9475` | 2026-11-03 11:46 | 9 | 0.43 GB |
| `agent-a639b5b5ed35f4655` | `worktree-agent-a639b5b5ed35f4655` | 2026-11-03 12:14 | 9 | 0.42 GB |
| `agent-ad01db06e3a1127ef` | `worktree-agent-ad01db06e3a1127ef` | 2026-11-03 12:48 | 9 | 0.42 GB |
| `agent-aefe7f159fefa56ed` | `worktree-agent-aefe7f159fefa56ed` | 2026-11-03 12:53 | 9 | 0.42 GB |
| `agent-af1096931e6df6396` | `worktree-agent-af1096931e6df6396` | 2026-11-03 13:35 | 9 | 0.42 GB |
| `agent-a2d9575d7efe784f9` | `worktree-agent-a2d9575d7efe784f9` | 2026-11-03 14:24 | 9 | 0.43 GB |
| `agent-a652dd63f5a76571e` | `worktree-agent-a652dd63f5a76571e` | 2026-11-03 14:37 | 9 | 0.43 GB |
| `agent-a3550dd04be73db4d` | `worktree-agent-a3550dd04be73db4d` | 2026-11-03 14:50 | 9 | 0.43 GB |
| `agent-aacd54ec8ae14b7ba` | `worktree-agent-aacd54ec8ae14b7ba` | 2026-11-03 17:02 | 9 | 0.43 GB |
| `agent-a77e3c82f02b09e6c` | `worktree-agent-a77e3c82f02b09e6c` | 2026-11-03 17:37 | 9 | 0.43 GB |
| `agent-a2ca3feeddca7d6ac` | `worktree-agent-a2ca3feeddca7d6ac` | 2026-11-03 18:14 | 9 | 0.43 GB |
| `agent-ab9e46c6d2b1bd8fa` | `worktree-agent-ab9e46c6d2b1bd8fa` | 2026-11-03 18:42 | 9 | 0.44 GB |
| `agent-aa93a1fb554ab0462` | `worktree-agent-aa93a1fb554ab0462` | 2026-11-03 19:04 | 9 | 0.43 GB |
| `agent-a85d6cdffdfd2645e` | `worktree-agent-a85d6cdffdfd2645e` | 2026-11-03 19:24 | 9 | 0.43 GB |
| `agent-a2543567153a4b655` | `worktree-agent-a2543567153a4b655` | 2026-11-03 19:34 | 9 | 0.43 GB |
| `agent-a997b89665c399f96` | `worktree-agent-a997b89665c399f96` | 2026-11-03 19:46 | 9 | 0.43 GB |
| `agent-a1dd1e9ab2898ab5b` | `worktree-agent-a1dd1e9ab2898ab5b` | 2026-11-03 20:41 | 9 | 0.43 GB |
| `agent-ae91a34d523b21ece` | `worktree-agent-ae91a34d523b21ece` | 2026-11-03 21:15 | 9 | 0.43 GB |
| `agent-ada7c3c1a147ab62b` | `worktree-agent-ada7c3c1a147ab62b` | 2026-11-04 00:41 | 9 | 0.30 GB |
| `agent-ae20158c08cf35b98` | `worktree-agent-ae20158c08cf35b98` | 2026-11-04 00:48 | 9 | 0.24 GB |
| `agent-a4572a3e7222a26a9` | `worktree-agent-a4572a3e7222a26a9` | 2026-11-04 00:51 | 9 | 0.40 GB |
| `agent-a7dab1606933c2ed3` | `worktree-agent-a7dab1606933c2ed3` | 2026-11-04 01:10 | 9 | 0.24 GB |
| `agent-a8f0d316d6ce3cb47` | `worktree-agent-a8f0d316d6ce3cb47` | 2026-11-04 01:21 | 9 | 0.41 GB |
| `agent-a4dc19e2762f1ff0d` | `worktree-agent-a4dc19e2762f1ff0d` | 2026-11-04 01:21 | 9 | 0.24 GB |
| `agent-a7e1d5ff53b94b228` | `worktree-agent-a7e1d5ff53b94b228` | 2026-11-04 01:30 | 9 | 0.31 GB |
| `agent-acb2e67f0017e9106` | `worktree-agent-acb2e67f0017e9106` | 2026-11-04 01:43 | 9 | 0.24 GB |
| `agent-a43f6e5167d9aee27` | `worktree-agent-a43f6e5167d9aee27` | 2026-11-04 01:47 | 9 | 0.25 GB |
| `agent-a7775cff12f92bb80` | `worktree-agent-a7775cff12f92bb80` | 2026-11-04 01:47 | 9 | 0.39 GB |
| `agent-a59fde070f6f905c3` | `worktree-agent-a59fde070f6f905c3` | 2026-11-04 02:04 | 9 | 0.41 GB |
| `agent-a70873095371a22ec` | `worktree-agent-a70873095371a22ec` | 2026-11-04 02:07 | 9 | 0.25 GB |
| `agent-aec87bd4ae1fb8720` | `worktree-agent-aec87bd4ae1fb8720` | 2026-11-04 02:14 | 9 | 0.40 GB |
| `agent-acac8d2ffe1b06385` | `worktree-agent-acac8d2ffe1b06385` | 2026-11-04 02:20 | 9 | 0.31 GB |
| `agent-a98f69055ca2b05b8` | `worktree-agent-a98f69055ca2b05b8` | 2026-11-04 02:21 | 9 | 0.43 GB |
| `agent-a2b7add5fd43e85ca` | `worktree-agent-a2b7add5fd43e85ca` | 2026-11-04 02:22 | 9 | 0.41 GB |
| `agent-aeda8760b8da34653` | `worktree-agent-aeda8760b8da34653` | 2026-11-04 02:29 | 8 | 0.25 GB |
| `agent-a75d411399261c1bd` | `worktree-agent-a75d411399261c1bd` | 2026-11-04 02:43 | 8 | 0.40 GB |
| `agent-a27289b47e3ac4c50` | `worktree-agent-a27289b47e3ac4c50` | 2026-11-04 02:45 | 8 | 0.25 GB |
| `agent-ae8f29b9f8df137d5` | `worktree-agent-ae8f29b9f8df137d5` | 2026-11-04 02:53 | 8 | 0.41 GB |
| `agent-a0859119849c6c17a` | `worktree-agent-a0859119849c6c17a` | 2026-11-04 03:01 | 8 | 0.41 GB |
| `agent-a918590c6f12171c9` | `worktree-agent-a918590c6f12171c9` | 2026-11-04 03:04 | 8 | 0.25 GB |
| `agent-a8a9383c8b5805fbd` | `worktree-agent-a8a9383c8b5805fbd` | 2026-11-04 03:05 | 8 | 0.40 GB |
| `agent-a9d66ef2fd7cafd94` | `worktree-agent-a9d66ef2fd7cafd94` | 2026-11-04 03:16 | 8 | 0.25 GB |
| `agent-ad6823b299887790c` | `worktree-agent-ad6823b299887790c` | 2026-11-04 03:24 | 8 | 0.25 GB |
| `agent-a878f907a75522668` | `worktree-agent-a878f907a75522668` | 2026-11-04 03:32 | 8 | 0.43 GB |
| `agent-a61481d91c421ad55` | `worktree-agent-a61481d91c421ad55` | 2026-11-04 03:36 | 8 | 0.40 GB |
| `agent-a3c7fb84b04b4afe4` | `worktree-agent-a3c7fb84b04b4afe4` | 2026-11-04 03:46 | 8 | 0.43 GB |
| `agent-a6aede4cb72ceb037` | `worktree-agent-a6aede4cb72ceb037` | 2026-11-04 03:58 | 8 | 0.26 GB |
| `agent-aeabde4e5f93cac32` | `worktree-agent-aeabde4e5f93cac32` | 2026-11-04 04:04 | 8 | 0.42 GB |
| `agent-a7c1f7cb717f2b716` | `worktree-agent-a7c1f7cb717f2b716` | 2026-11-04 04:05 | 8 | 0.43 GB |
| `agent-aad93f555e04c7fd4` | `worktree-agent-aad93f555e04c7fd4` | 2026-11-04 04:23 | 8 | 0.40 GB |
| `agent-af620b0245b8e8838` | `worktree-agent-af620b0245b8e8838` | 2026-11-04 04:27 | 8 | 0.41 GB |
| `agent-a96070e634b692578` | `worktree-agent-a96070e634b692578` | 2026-11-04 04:49 | 8 | 0.42 GB |
| `agent-ad83902c5d894fd7d` | `worktree-agent-ad83902c5d894fd7d` | 2026-11-04 04:58 | 8 | 0.42 GB |
| `agent-aac9fde35f46b6dce` | `worktree-agent-aac9fde35f46b6dce` | 2026-11-04 04:58 | 8 | 0.41 GB |
| `agent-a592234d23bade14c` | `worktree-agent-a592234d23bade14c` | 2026-11-04 05:23 | 8 | 0.43 GB |
| `agent-a92ac5c804f79bbad` | `worktree-agent-a92ac5c804f79bbad` | 2026-11-04 05:38 | 8 | 0.42 GB |
| `agent-a1cc624d5e7bbbafa` | `worktree-agent-a1cc624d5e7bbbafa` | 2026-11-04 05:44 | 8 | 0.32 GB |
| `agent-ab4c5414ca4b4503c` | `worktree-agent-ab4c5414ca4b4503c` | 2026-11-04 05:54 | 8 | 0.41 GB |
| `agent-ad4085259a8d68210` | `worktree-agent-ad4085259a8d68210` | 2026-11-04 06:10 | 8 | 0.31 GB |
| `agent-a925b6ecfeb82b841` | `worktree-agent-a925b6ecfeb82b841` | 2026-11-04 06:25 | 8 | 0.26 GB |
| `agent-af89a0a26b0fb4c51` | `worktree-agent-af89a0a26b0fb4c51` | 2026-11-04 07:01 | 8 | 0.43 GB |
| `agent-aec8bcc714c7192d6` | `worktree-agent-aec8bcc714c7192d6` | 2026-11-04 07:45 | 8 | 0.42 GB |
| `agent-a9efe50c64edf920e` | `worktree-agent-a9efe50c64edf920e` | 2026-11-04 07:51 | 8 | 0.32 GB |
| `agent-ab5c623995e7768d1` | `worktree-agent-ab5c623995e7768d1` | 2026-11-04 07:55 | 8 | 0.26 GB |
| `agent-ade49b7571666fcfa` | `worktree-agent-ade49b7571666fcfa` | 2026-11-04 08:05 | 8 | 0.43 GB |
| `agent-aeb4ebc55a4fedd5f` | `worktree-agent-aeb4ebc55a4fedd5f` | 2026-11-04 08:34 | 8 | 0.44 GB |
| `agent-a5805d776d8974392` | `worktree-agent-a5805d776d8974392` | 2026-11-04 08:46 | 8 | 0.26 GB |
| `agent-ae6c131877d002fc8` | `worktree-agent-ae6c131877d002fc8` | 2026-11-04 08:53 | 8 | 0.32 GB |
| `agent-a011f51a9d0196cb3` | `worktree-agent-a011f51a9d0196cb3` | 2026-11-04 09:18 | 8 | 0.26 GB |
| `agent-ab834642190d880e7` | `worktree-agent-ab834642190d880e7` | 2026-11-04 09:46 | 8 | 0.26 GB |
| `agent-a325d0388523762a6` | `worktree-agent-a325d0388523762a6` | 2026-11-04 10:01 | 8 | 0.26 GB |
| `agent-a2be520826b7bd6ab` | `worktree-agent-a2be520826b7bd6ab` | 2026-11-04 10:12 | 8 | 0.26 GB |
| `agent-ab84dc94c3dcc9039` | `worktree-agent-ab84dc94c3dcc9039` | 2026-11-04 11:08 | 8 | 0.27 GB |
| `agent-a0e193c7e07622faa` | `worktree-agent-a0e193c7e07622faa` | 2026-11-04 11:11 | 8 | 0.43 GB |
| `agent-afacf06c73d9bf75c` | `worktree-agent-afacf06c73d9bf75c` | 2026-11-04 11:33 | 8 | 0.44 GB |
| `agent-a170fd635d0419b53` | `worktree-agent-a170fd635d0419b53` | 2026-11-04 11:34 | 8 | 0.43 GB |
| `agent-a3b57773b0ca73297` | `worktree-agent-a3b57773b0ca73297` | 2026-11-04 11:35 | 8 | 0.32 GB |
| `agent-aa9974f3b0f9708a7` | `worktree-agent-aa9974f3b0f9708a7` | 2026-11-04 11:38 | 8 | 0.33 GB |
| `agent-ad47276a793fcee43` | `worktree-agent-ad47276a793fcee43` | 2026-11-04 12:05 | 8 | 0.42 GB |
| `agent-a35017503258f769a` | `worktree-agent-a35017503258f769a` | 2026-11-04 12:05 | 8 | 0.42 GB |
| `agent-a7618aabc3e32f17a` | `worktree-agent-a7618aabc3e32f17a` | 2026-11-04 12:08 | 8 | 0.42 GB |
| `g6cart3` | `phase6c-art3` | 2026-11-04 12:20 | 8 | 0.25 GB |
| `agent-a28c06a3f82c22fed` | `worktree-agent-a28c06a3f82c22fed` | 2026-11-04 12:41 | 8 | 0.42 GB |
| `agent-aecd36ece0422378b` | `worktree-agent-aecd36ece0422378b` | 2026-11-04 13:05 | 8 | 0.43 GB |
| `agent-a336e94d566409dc0` | `worktree-agent-a336e94d566409dc0` | 2026-11-04 13:51 | 8 | 0.44 GB |
| `agent-a9ffd93d49ee02762` | `worktree-agent-a9ffd93d49ee02762` | 2026-11-04 14:33 | 8 | 0.44 GB |
| `agent-aff3337bcd0063067` | `worktree-agent-aff3337bcd0063067` | 2026-11-04 15:09 | 8 | 0.44 GB |
| `agent-a6fed953c679e7285` | `worktree-agent-a6fed953c679e7285` | 2026-11-04 15:42 | 8 | 0.44 GB |
| `agent-ae3815dc37ebfa0b2` | `worktree-agent-ae3815dc37ebfa0b2` | 2026-11-04 15:58 | 8 | 0.43 GB |
| `agent-a6ef9dfb8b2da5c52` | `worktree-agent-a6ef9dfb8b2da5c52` | 2026-11-04 16:12 | 8 | 0.42 GB |
| `agent-a0cc6f6e69a196bbb` | `worktree-agent-a0cc6f6e69a196bbb` | 2026-11-04 16:15 | 8 | 0.44 GB |
| `agent-a5dd533a0009a25ad` | `worktree-agent-a5dd533a0009a25ad` | 2026-11-04 16:20 | 8 | 0.44 GB |
| `agent-aa9b84e5bd2269d20` | `worktree-agent-aa9b84e5bd2269d20` | 2026-11-04 16:44 | 8 | 0.43 GB |
| `agent-a72d1f391f3faa679` | `worktree-agent-a72d1f391f3faa679` | 2026-11-04 16:51 | 8 | 0.38 GB |
| `agent-ac7d41a4c18d1efd3` | `worktree-agent-ac7d41a4c18d1efd3` | 2026-11-04 17:00 | 8 | 0.26 GB |
| `agent-a4dfdbdba645e930d` | `worktree-agent-a4dfdbdba645e930d` | 2026-11-04 17:13 | 8 | 0.47 GB |
| `agent-aced41af2e834bfeb` | `worktree-agent-aced41af2e834bfeb` | 2026-11-04 17:23 | 8 | 0.48 GB |
| `agent-abfc062d226179469` | `worktree-agent-abfc062d226179469` | 2026-11-04 17:37 | 8 | 0.45 GB |
| `agent-abd15f51539d33602` | `worktree-agent-abd15f51539d33602` | 2026-11-04 17:59 | 8 | 0.46 GB |
| `agent-a54b089b590e95983` | `worktree-agent-a54b089b590e95983` | 2026-11-04 18:29 | 8 | 0.48 GB |
| `agent-a0b8205a897824fa9` | `worktree-agent-a0b8205a897824fa9` | 2026-11-04 18:37 | 8 | 0.37 GB |
| `agent-a83d3f70395753abf` | `worktree-agent-a83d3f70395753abf` | 2026-11-04 19:20 | 8 | 0.71 GB |
| `agent-ad262a4500a182e46` | `worktree-agent-ad262a4500a182e46` | 2026-11-04 19:41 | 8 | 0.47 GB |
| `agent-acbb60f842876a388` | `worktree-agent-acbb60f842876a388` | 2026-11-04 19:52 | 8 | 0.29 GB |
| `agent-a99bd4db21c637f04` | `worktree-agent-a99bd4db21c637f04` | 2026-11-04 20:16 | 8 | 0.55 GB |
| `agent-a070af488925050e1` | `worktree-agent-a070af488925050e1` | 2026-11-04 20:41 | 8 | 0.46 GB |
| `agent-a4e76d3d0bc8f2644` | `worktree-agent-a4e76d3d0bc8f2644` | 2026-11-04 20:51 | 8 | 0.49 GB |
| `agent-a4ff26faf9076318e` | `worktree-agent-a4ff26faf9076318e` | 2026-11-04 21:39 | 8 | 0.76 GB |
| `agent-a39d71366b592a6df` | `worktree-agent-a39d71366b592a6df` | 2026-11-04 22:09 | 8 | 0.50 GB |
| `agent-ab043c214291526cb` | `worktree-agent-ab043c214291526cb` | 2026-11-04 22:16 | 8 | 0.28 GB |
| `agent-a98447677297d7713` | `worktree-agent-a98447677297d7713` | 2026-11-04 22:22 | 8 | 0.67 GB |
| `agent-aff55411f3b5f9d66` | `worktree-agent-aff55411f3b5f9d66` | 2026-11-04 22:54 | 8 | 0.62 GB |
| `agent-aa2dc2876fcc5e56d` | `worktree-agent-aa2dc2876fcc5e56d` | 2026-11-04 23:14 | 8 | 0.92 GB |
| `agent-aa055aff511c1ff73` | `worktree-agent-aa055aff511c1ff73` | 2026-11-04 23:29 | 8 | 0.34 GB |
| `agent-aee5ec8a00e2947ba` | `worktree-agent-aee5ec8a00e2947ba` | 2026-11-04 23:30 | 8 | 0.34 GB |
| `agent-a3d9f457a31e7874b` | `worktree-agent-a3d9f457a31e7874b` | 2026-11-04 23:41 | 8 | 0.31 GB |
| `agent-af40b9f5aa510f127` | `worktree-agent-af40b9f5aa510f127` | 2026-11-04 23:50 | 8 | 0.34 GB |
| `agent-a4bee263a113610b5` | `worktree-agent-a4bee263a113610b5` | 2026-11-05 00:18 | 8 | 0.29 GB |
| `agent-ac227a44c00b76db8` | `worktree-agent-ac227a44c00b76db8` | 2026-11-05 00:19 | 8 | 1.42 GB |
| `agent-ad325eeff94d284d0` | `worktree-agent-ad325eeff94d284d0` | 2026-11-05 01:06 | 8 | 0.53 GB |
| `agent-aeb2f7545a51b3124` | `worktree-agent-aeb2f7545a51b3124` | 2026-11-05 01:36 | 8 | 0.54 GB |
| `agent-a7b637f269120a32a` | `worktree-agent-a7b637f269120a32a` | 2026-11-05 02:28 | 7 | 1.51 GB |
| `agent-ab176d9d6ab5758a3` | `worktree-agent-ab176d9d6ab5758a3` | 2026-11-05 02:30 | 7 | 0.77 GB |
| `agent-a78e97016bd372c16` | `worktree-agent-a78e97016bd372c16` | 2026-11-05 03:16 | 7 | 1.39 GB |
| `agent-af3ad387ef139c271` | `worktree-agent-af3ad387ef139c271` | 2026-11-05 03:19 | 7 | 0.75 GB |
| `agent-a0f22dac7ac58383b` | `worktree-agent-a0f22dac7ac58383b` | 2026-11-05 03:23 | 7 | 0.55 GB |
| `agent-a4265886c5b9785d8` | `worktree-agent-a4265886c5b9785d8` | 2026-11-05 04:03 | 7 | 0.56 GB |
| `agent-a556cb3a2b37f7435` | `worktree-agent-a556cb3a2b37f7435` | 2026-11-05 04:38 | 7 | 0.37 GB |
| `agent-afe01600f587596e6` | `worktree-agent-afe01600f587596e6` | 2026-11-05 04:45 | 7 | 1.51 GB |
| `agent-adc529dd1fdf55953` | `worktree-agent-adc529dd1fdf55953` | 2026-11-05 04:58 | 7 | 0.56 GB |
| `agent-aabd34b5e439ecd67` | `worktree-agent-aabd34b5e439ecd67` | 2026-11-05 05:41 | 7 | 1.21 GB |
| `agent-a9b18626211f4cd83` | `worktree-agent-a9b18626211f4cd83` | 2026-11-05 05:44 | 7 | 0.57 GB |
| `agent-a31b0024ebdb89bda` | `worktree-agent-a31b0024ebdb89bda` | 2026-11-05 06:08 | 7 | 0.77 GB |
| `agent-a8f6aae1c919496e5` | `worktree-agent-a8f6aae1c919496e5` | 2026-11-05 06:22 | 7 | 0.57 GB |
| `agent-aa2e5bbfa6a48f531` | `worktree-agent-aa2e5bbfa6a48f531` | 2026-11-05 06:43 | 7 | 0.77 GB |
| `agent-a5241455b3469db6d` | `worktree-agent-a5241455b3469db6d` | 2026-11-05 07:32 | 7 | 0.98 GB |
| `agent-a75be397fd6c53834` | `worktree-agent-a75be397fd6c53834` | 2026-11-05 08:27 | 7 | 0.82 GB |
| `agent-adcfe87cbb300be04` | `worktree-agent-adcfe87cbb300be04` | 2026-11-05 09:23 | 7 | 0.93 GB |
| `agent-a20b1a8b124b2f2ce` | `worktree-agent-a20b1a8b124b2f2ce` | 2026-11-05 10:47 | 7 | 0.94 GB |
| `agent-aea0bd2d545913b7b` | `worktree-agent-aea0bd2d545913b7b` | 2026-11-05 11:50 | 7 | 0.92 GB |
| `agent-aaadadb9a4fd34214` | `worktree-agent-aaadadb9a4fd34214` | 2026-11-05 12:39 | 7 | 0.91 GB |
| `agent-ab4a83c17695b31a4` | `worktree-agent-ab4a83c17695b31a4` | 2026-11-05 12:52 | 7 | 0.57 GB |
| `agent-aa42e465d64743e4f` | `worktree-agent-aa42e465d64743e4f` | 2026-11-05 13:33 | 7 | 0.40 GB |
| `agent-a3a428a5e9ee98e18` | `worktree-agent-a3a428a5e9ee98e18` | 2026-11-05 13:46 | 7 | 0.79 GB |

## 候選 B：孤兒資料夾（不在 git worktree list）、超過 7 天沒動

| 資料夾 | 最新修改 | 天數 | 大小 |
|---|---|---|---|
| `agent-ae87b7c712b8545c3` | — | 空 | 0 MB |
| `agent-ae6a7e5df6923880a` | 2026-10-23 17:06 | 20 | 0 MB |
| `agent-a307771f939bbfdef` | 2026-10-24 02:44 | 19 | 0.24 GB |
| `agent-a4a8fed65ae979ca8` | 2026-10-24 02:59 | 19 | 0.24 GB |
| `agent-a895000bd70160a90` | 2026-10-24 03:09 | 19 | 0.24 GB |
| `agent-a928a5c2c25e87540` | 2026-10-24 03:46 | 19 | 0.24 GB |
| `agent-aedb3e269f8aa80df` | 2026-10-24 04:00 | 19 | 0.24 GB |
| `agent-a1e5e6e49b2bf677d` | 2026-10-24 04:28 | 19 | 0.24 GB |
| `agent-ad7409baf42d5f98e` | 2026-10-24 04:43 | 19 | 0.24 GB |
| `agent-a0baafb3dfe51d906` | 2026-10-24 05:02 | 19 | 0.24 GB |
| `agent-ab7625643c44cd1ad` | 2026-10-24 05:26 | 19 | 0.24 GB |
| `agent-a21814e25337164f5` | 2026-10-24 05:52 | 19 | 0.24 GB |
| `agent-a097b737cfcb276e6` | 2026-10-24 06:00 | 19 | 0.24 GB |
| `agent-a8631cd06bd37186c` | 2026-10-24 06:51 | 19 | 0.24 GB |
| `agent-aff32e3660921dd0c` | 2026-10-24 06:56 | 19 | 72 MB |
| `agent-a72b9de6bade4251d` | 2026-10-24 07:54 | 19 | 0.24 GB |
| `agent-a61f541b41cc35398` | 2026-10-24 08:05 | 19 | 0.25 GB |
| `agent-aa186e987cd1d8adb` | 2026-10-24 08:11 | 19 | 0.24 GB |
| `agent-ab8cbe0ab60bd7645` | 2026-10-24 08:19 | 19 | 0.25 GB |
| `agent-ae663535b6eddea85` | 2026-10-24 08:43 | 19 | 0.25 GB |
| `agent-a4cfbe4cc422c74e1` | 2026-10-24 08:56 | 19 | 0.24 GB |
| `agent-a9f5688b2b69261e9` | 2026-10-24 09:08 | 19 | 0.25 GB |
| `agent-a7025cbe43dce86d8` | 2026-10-24 09:55 | 19 | 0.24 GB |
| `agent-a43b178821de060ca` | 2026-10-24 10:02 | 19 | 0.24 GB |
| `agent-a317aac4a1d60ac3f` | 2026-10-24 11:02 | 19 | 0.24 GB |
| `agent-a2967af5dfed23cb2` | 2026-10-24 11:10 | 19 | 0.24 GB |
| `agent-af964b946ac24f39e` | 2026-10-24 11:27 | 19 | 0.24 GB |
| `agent-af47c53b3afb7bab8` | 2026-10-24 11:40 | 19 | 0.24 GB |
| `agent-ac2a6eaff056a0b15` | 2026-10-24 12:06 | 19 | 0.24 GB |
| `agent-a183a9f42be165833` | 2026-10-24 12:15 | 19 | 0.24 GB |
| `agent-ad8bcb97bb0b6fd93` | 2026-10-24 12:49 | 19 | 0.24 GB |
| `agent-acf91c20b6f67c03b` | 2026-10-24 13:07 | 19 | 0.24 GB |
| `agent-a503492d13d9a16a3` | 2026-10-24 13:34 | 19 | 0.24 GB |
| `agent-a87108d932315e64e` | 2026-10-24 13:54 | 19 | 0.24 GB |
| `agent-af92b5cb2449fc5c0` | 2026-10-24 14:37 | 19 | 0.24 GB |

## 登記了但資料夾已不存在

- `F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/agent-a1403ad4127bb709b`（worktree-agent-a1403ad4127bb709b，locked）
- `F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/agent-a423bf7b0809e9bcf`（worktree-agent-a423bf7b0809e9bcf，locked）
- `F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/agent-a57d670f2cf4482bc`（worktree-agent-a57d670f2cf4482bc，locked）
- `F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/agent-a9173c7a218f4f720`（worktree-agent-a9173c7a218f4f720，locked）
- `F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/agent-aa62ff21a8257c449`（worktree-agent-aa62ff21a8257c449，locked）

