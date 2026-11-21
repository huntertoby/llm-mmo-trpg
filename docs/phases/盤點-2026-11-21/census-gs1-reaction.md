# 組合器配方盤點摘要

格式 `recipe-census/1`；種子 0～199；薄格門檻：不同設計 < 12。由 `scripts/recipe_census.py` 產生，計時欄每次不同。

- 格子 136：正常 118、薄 10、空 8、設計上不存在 0（骨架稀有度下限：被動至少 epic、反應至少 rare）
- 其中遊戲會出題（出題檢查通過）的：空 0、薄 10；其餘空格是規則上就沒有專屬來源（遊戲不出這題）

## 依關鍵字（不含設計上不存在；「會出題」＝出題檢查通過的空格與薄格）

| 關鍵字 | 空 | 薄 | 正常 | 會出題的空 | 會出題的薄 |
|---|---|---|---|---|---|
| - | 0 | 0 | 8 | 0 | 0 |
| ignite | 0 | 0 | 8 | 0 | 0 |
| wet | 0 | 0 | 8 | 0 | 0 |
| charged | 0 | 2 | 6 | 0 | 2 |
| frozen | 0 | 0 | 8 | 0 | 0 |
| prone | 0 | 0 | 8 | 0 | 0 |
| collision | 0 | 0 | 8 | 0 | 0 |
| marked | 0 | 0 | 8 | 0 | 0 |
| high_ground | 0 | 0 | 8 | 0 | 0 |
| concealed | 0 | 0 | 8 | 0 | 0 |
| summon | 0 | 8 | 0 | 0 | 8 |
| poisoned | 0 | 0 | 8 | 0 | 0 |
| form | 8 | 0 | 0 | 0 | 0 |
| combo_point | 0 | 0 | 8 | 0 | 0 |
| fury | 0 | 0 | 8 | 0 | 0 |
| focus | 0 | 0 | 8 | 0 | 0 |
| ki | 0 | 0 | 8 | 0 | 0 |

## 依種類

| 種類 | 空 | 薄 | 正常 | 會出題的空 | 會出題的薄 |
|---|---|---|---|---|---|
| reaction | 8 | 10 | 118 | 0 | 10 |

## 空格與薄格（依玩家遇到的頻率排序）

| 關鍵字 | 種類 | 階 | 稀有度 | 狀態 | 會出題 | 合法 | 設計 | 主要原因 | 判斷 | 中位 ms |
|---|---|---|---|---|---|---|---|---|---|---|
| form | reaction | 2 | rare | empty | 否 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | reaction | 2 | rare | thin | 是 | 200 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 6.0 |
| charged | reaction | 1 | rare | thin | 是 | 189 | 10 | keyword_exhausted 11 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 60.1 |
| form | reaction | 1 | rare | empty | 否 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | reaction | 3 | rare | empty | 否 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | reaction | 1 | rare | thin | 是 | 200 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 4.5 |
| summon | reaction | 3 | rare | thin | 是 | 200 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 7.2 |
| form | reaction | 2 | epic | empty | 否 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | reaction | 2 | epic | thin | 是 | 200 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 6.3 |
| charged | reaction | 1 | epic | thin | 是 | 189 | 10 | keyword_exhausted 11 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 57.0 |
| form | reaction | 1 | epic | empty | 否 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | reaction | 3 | epic | empty | 否 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | reaction | 1 | epic | thin | 是 | 200 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 4.5 |
| summon | reaction | 3 | epic | thin | 是 | 200 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 7.6 |
| form | reaction | 4 | rare | empty | 否 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | reaction | 4 | rare | thin | 是 | 200 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 9.1 |
| form | reaction | 4 | epic | empty | 否 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | reaction | 4 | epic | thin | 是 | 200 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 9.3 |

## 全部格子

| 關鍵字 | 種類 | 階 | 稀有度 | 合法 | 設計 | 護主 | 主要原因 | 平均 ms | 中位 ms |
|---|---|---|---|---|---|---|---|---|---|
| - | reaction | 1 | rare | 200 | 89 | 2 |  | 1.5 | 1.4 |
| - | reaction | 1 | epic | 200 | 89 | 2 |  | 1.5 | 1.5 |
| - | reaction | 2 | rare | 200 | 80 | 2 |  | 1.6 | 1.6 |
| - | reaction | 2 | epic | 200 | 80 | 2 |  | 1.7 | 1.6 |
| - | reaction | 3 | rare | 200 | 71 | 2 |  | 1.9 | 1.9 |
| - | reaction | 3 | epic | 200 | 71 | 2 |  | 2.0 | 1.9 |
| - | reaction | 4 | rare | 200 | 68 | 2 |  | 2.1 | 1.9 |
| - | reaction | 4 | epic | 200 | 68 | 2 |  | 2.1 | 2.1 |
| ignite | reaction | 1 | rare | 200 | 54 | 0 |  | 31.2 | 22.3 |
| ignite | reaction | 1 | epic | 200 | 54 | 0 |  | 31.1 | 21.6 |
| ignite | reaction | 2 | rare | 200 | 47 | 58 |  | 31.1 | 16.0 |
| ignite | reaction | 2 | epic | 200 | 47 | 58 |  | 31.0 | 15.0 |
| ignite | reaction | 3 | rare | 200 | 42 | 58 |  | 34.5 | 15.7 |
| ignite | reaction | 3 | epic | 200 | 42 | 58 |  | 34.5 | 16.6 |
| ignite | reaction | 4 | rare | 200 | 34 | 0 |  | 1301.3 | 98.0 |
| ignite | reaction | 4 | epic | 200 | 34 | 0 |  | 1305.0 | 100.6 |
| wet | reaction | 1 | rare | 200 | 70 | 0 |  | 6.2 | 5.1 |
| wet | reaction | 1 | epic | 200 | 70 | 0 |  | 6.3 | 5.2 |
| wet | reaction | 2 | rare | 200 | 58 | 58 |  | 6.1 | 4.3 |
| wet | reaction | 2 | epic | 200 | 58 | 58 |  | 6.2 | 4.5 |
| wet | reaction | 3 | rare | 200 | 45 | 58 |  | 6.7 | 5.0 |
| wet | reaction | 3 | epic | 200 | 45 | 58 |  | 6.7 | 4.9 |
| wet | reaction | 4 | rare | 200 | 32 | 0 |  | 115.5 | 10.1 |
| wet | reaction | 4 | epic | 200 | 32 | 0 |  | 114.7 | 10.2 |
| charged | reaction | 1 | rare | 189 | 10 | 0 | keyword_exhausted 11 | 87.2 | 60.1 |
| charged | reaction | 1 | epic | 189 | 10 | 0 | keyword_exhausted 11 | 87.1 | 57.0 |
| charged | reaction | 2 | rare | 192 | 13 | 58 | keyword_exhausted 8 | 74.7 | 36.1 |
| charged | reaction | 2 | epic | 192 | 13 | 58 | keyword_exhausted 8 | 75.5 | 34.6 |
| charged | reaction | 3 | rare | 196 | 13 | 58 | keyword_exhausted 4 | 71.1 | 33.9 |
| charged | reaction | 3 | epic | 196 | 13 | 58 | keyword_exhausted 4 | 71.6 | 33.7 |
| charged | reaction | 4 | rare | 195 | 12 | 58 | keyword_exhausted 5 | 75.7 | 35.9 |
| charged | reaction | 4 | epic | 195 | 12 | 58 | keyword_exhausted 5 | 75.7 | 36.4 |
| frozen | reaction | 1 | rare | 198 | 28 | 0 | keyword_exhausted 2 | 53.0 | 39.3 |
| frozen | reaction | 1 | epic | 198 | 28 | 0 | keyword_exhausted 2 | 53.9 | 38.2 |
| frozen | reaction | 2 | rare | 200 | 46 | 58 |  | 38.2 | 20.9 |
| frozen | reaction | 2 | epic | 200 | 46 | 58 |  | 38.5 | 20.5 |
| frozen | reaction | 3 | rare | 200 | 33 | 58 |  | 52.6 | 29.3 |
| frozen | reaction | 3 | epic | 200 | 33 | 58 |  | 52.6 | 28.1 |
| frozen | reaction | 4 | rare | 200 | 27 | 58 |  | 56.2 | 33.4 |
| frozen | reaction | 4 | epic | 200 | 27 | 58 |  | 56.4 | 33.9 |
| prone | reaction | 1 | rare | 200 | 52 | 58 |  | 14.6 | 7.4 |
| prone | reaction | 1 | epic | 200 | 52 | 58 |  | 14.5 | 7.0 |
| prone | reaction | 2 | rare | 200 | 62 | 58 |  | 31.0 | 15.1 |
| prone | reaction | 2 | epic | 200 | 62 | 58 |  | 31.4 | 15.8 |
| prone | reaction | 3 | rare | 200 | 45 | 58 |  | 46.1 | 22.4 |
| prone | reaction | 3 | epic | 200 | 45 | 58 |  | 46.2 | 21.4 |
| prone | reaction | 4 | rare | 200 | 31 | 58 |  | 54.4 | 33.0 |
| prone | reaction | 4 | epic | 200 | 31 | 58 |  | 54.6 | 31.2 |
| collision | reaction | 1 | rare | 200 | 100 | 0 |  | 10.3 | 6.7 |
| collision | reaction | 1 | epic | 200 | 100 | 0 |  | 10.4 | 6.7 |
| collision | reaction | 2 | rare | 200 | 97 | 58 |  | 11.7 | 6.8 |
| collision | reaction | 2 | epic | 200 | 97 | 58 |  | 11.6 | 6.4 |
| collision | reaction | 3 | rare | 200 | 81 | 58 |  | 16.2 | 8.3 |
| collision | reaction | 3 | epic | 200 | 81 | 58 |  | 16.1 | 8.2 |
| collision | reaction | 4 | rare | 200 | 69 | 58 |  | 21.6 | 10.3 |
| collision | reaction | 4 | epic | 200 | 69 | 58 |  | 21.9 | 9.9 |
| marked | reaction | 1 | rare | 195 | 53 | 0 | keyword_exhausted 5 | 78.7 | 57.1 |
| marked | reaction | 1 | epic | 195 | 53 | 0 | keyword_exhausted 5 | 79.4 | 59.4 |
| marked | reaction | 2 | rare | 199 | 45 | 58 | keyword_exhausted 1 | 62.6 | 34.8 |
| marked | reaction | 2 | epic | 199 | 45 | 58 | keyword_exhausted 1 | 63.5 | 34.6 |
| marked | reaction | 3 | rare | 194 | 62 | 0 | keyword_exhausted 6 | 2772.4 | 176.9 |
| marked | reaction | 3 | epic | 194 | 62 | 0 | keyword_exhausted 6 | 2802.6 | 177.1 |
| marked | reaction | 4 | rare | 174 | 56 | 0 | keyword_exhausted 26 | 3971.8 | 292.9 |
| marked | reaction | 4 | epic | 174 | 56 | 0 | keyword_exhausted 26 | 4013.4 | 290.5 |
| high_ground | reaction | 1 | rare | 200 | 111 | 0 |  | 6.0 | 4.8 |
| high_ground | reaction | 1 | epic | 200 | 111 | 0 |  | 6.3 | 5.2 |
| high_ground | reaction | 2 | rare | 200 | 85 | 58 |  | 6.5 | 4.7 |
| high_ground | reaction | 2 | epic | 200 | 85 | 58 |  | 6.6 | 4.9 |
| high_ground | reaction | 3 | rare | 200 | 89 | 0 |  | 122.9 | 9.7 |
| high_ground | reaction | 3 | epic | 200 | 89 | 0 |  | 125.0 | 9.7 |
| high_ground | reaction | 4 | rare | 200 | 72 | 0 |  | 124.2 | 10.0 |
| high_ground | reaction | 4 | epic | 200 | 72 | 0 |  | 123.3 | 10.4 |
| concealed | reaction | 1 | rare | 200 | 20 | 0 |  | 62.4 | 45.3 |
| concealed | reaction | 1 | epic | 200 | 20 | 0 |  | 62.2 | 44.5 |
| concealed | reaction | 2 | rare | 198 | 14 | 58 | keyword_exhausted 2 | 74.6 | 42.1 |
| concealed | reaction | 2 | epic | 198 | 14 | 58 | keyword_exhausted 2 | 74.0 | 43.6 |
| concealed | reaction | 3 | rare | 199 | 16 | 58 | keyword_exhausted 1 | 67.8 | 39.2 |
| concealed | reaction | 3 | epic | 199 | 16 | 58 | keyword_exhausted 1 | 67.4 | 35.9 |
| concealed | reaction | 4 | rare | 195 | 16 | 0 | keyword_exhausted 5 | 2346.6 | 131.8 |
| concealed | reaction | 4 | epic | 195 | 16 | 0 | keyword_exhausted 5 | 2377.2 | 123.4 |
| summon | reaction | 1 | rare | 200 | 1 | 200 |  | 5.5 | 4.5 |
| summon | reaction | 1 | epic | 200 | 1 | 200 |  | 5.6 | 4.5 |
| summon | reaction | 2 | rare | 200 | 1 | 200 |  | 7.8 | 6.0 |
| summon | reaction | 2 | epic | 200 | 1 | 200 |  | 8.1 | 6.3 |
| summon | reaction | 3 | rare | 200 | 1 | 200 |  | 9.5 | 7.2 |
| summon | reaction | 3 | epic | 200 | 1 | 200 |  | 9.5 | 7.6 |
| summon | reaction | 4 | rare | 200 | 1 | 200 |  | 11.4 | 9.1 |
| summon | reaction | 4 | epic | 200 | 1 | 200 |  | 11.6 | 9.3 |
| poisoned | reaction | 1 | rare | 192 | 69 | 0 | keyword_exhausted 8 | 116.9 | 81.3 |
| poisoned | reaction | 1 | epic | 192 | 69 | 0 | keyword_exhausted 8 | 116.6 | 80.6 |
| poisoned | reaction | 2 | rare | 184 | 69 | 0 | keyword_exhausted 16 | 171.9 | 128.7 |
| poisoned | reaction | 2 | epic | 184 | 69 | 0 | keyword_exhausted 16 | 171.4 | 129.5 |
| poisoned | reaction | 3 | rare | 134 | 60 | 0 | keyword_exhausted 66 | 271.3 | 261.8 |
| poisoned | reaction | 3 | epic | 134 | 60 | 0 | keyword_exhausted 66 | 272.7 | 260.3 |
| poisoned | reaction | 4 | rare | 93 | 40 | 0 | keyword_exhausted 107 | 356.0 | 464.1 |
| poisoned | reaction | 4 | epic | 93 | 40 | 0 | keyword_exhausted 107 | 356.0 | 466.4 |
| form | reaction | 1 | rare | 0 | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 1 | epic | 0 | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 2 | rare | 0 | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 2 | epic | 0 | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 3 | rare | 0 | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 3 | epic | 0 | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 4 | rare | 0 | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 4 | epic | 0 | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| combo_point | reaction | 1 | rare | 200 | 117 | 0 |  | 5.9 | 4.9 |
| combo_point | reaction | 1 | epic | 200 | 117 | 0 |  | 6.0 | 5.1 |
| combo_point | reaction | 2 | rare | 200 | 112 | 0 |  | 7.4 | 6.0 |
| combo_point | reaction | 2 | epic | 200 | 112 | 0 |  | 7.8 | 6.2 |
| combo_point | reaction | 3 | rare | 200 | 90 | 0 |  | 7.7 | 6.2 |
| combo_point | reaction | 3 | epic | 200 | 90 | 0 |  | 7.7 | 6.3 |
| combo_point | reaction | 4 | rare | 200 | 72 | 0 |  | 8.1 | 6.7 |
| combo_point | reaction | 4 | epic | 200 | 72 | 0 |  | 8.2 | 6.7 |
| fury | reaction | 1 | rare | 200 | 117 | 0 |  | 6.0 | 4.7 |
| fury | reaction | 1 | epic | 200 | 117 | 0 |  | 5.9 | 4.8 |
| fury | reaction | 2 | rare | 200 | 112 | 0 |  | 7.0 | 5.8 |
| fury | reaction | 2 | epic | 200 | 112 | 0 |  | 7.0 | 5.4 |
| fury | reaction | 3 | rare | 200 | 90 | 0 |  | 7.8 | 6.3 |
| fury | reaction | 3 | epic | 200 | 90 | 0 |  | 7.7 | 6.2 |
| fury | reaction | 4 | rare | 200 | 72 | 0 |  | 8.1 | 6.5 |
| fury | reaction | 4 | epic | 200 | 72 | 0 |  | 8.1 | 6.5 |
| focus | reaction | 1 | rare | 200 | 117 | 0 |  | 6.2 | 5.2 |
| focus | reaction | 1 | epic | 200 | 117 | 0 |  | 6.4 | 5.4 |
| focus | reaction | 2 | rare | 200 | 112 | 0 |  | 7.1 | 5.8 |
| focus | reaction | 2 | epic | 200 | 112 | 0 |  | 7.2 | 5.6 |
| focus | reaction | 3 | rare | 200 | 90 | 0 |  | 7.9 | 6.3 |
| focus | reaction | 3 | epic | 200 | 90 | 0 |  | 7.8 | 6.2 |
| focus | reaction | 4 | rare | 200 | 72 | 0 |  | 8.2 | 6.6 |
| focus | reaction | 4 | epic | 200 | 72 | 0 |  | 8.4 | 6.8 |
| ki | reaction | 1 | rare | 200 | 117 | 0 |  | 6.1 | 5.0 |
| ki | reaction | 1 | epic | 200 | 117 | 0 |  | 6.0 | 4.9 |
| ki | reaction | 2 | rare | 200 | 112 | 0 |  | 7.0 | 5.8 |
| ki | reaction | 2 | epic | 200 | 112 | 0 |  | 7.0 | 5.6 |
| ki | reaction | 3 | rare | 200 | 90 | 0 |  | 7.8 | 6.0 |
| ki | reaction | 3 | epic | 200 | 90 | 0 |  | 7.8 | 6.5 |
| ki | reaction | 4 | rare | 200 | 72 | 0 |  | 8.3 | 6.4 |
| ki | reaction | 4 | epic | 200 | 72 | 0 |  | 8.4 | 6.7 |
