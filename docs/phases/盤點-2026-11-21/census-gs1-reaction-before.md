# 組合器配方盤點摘要

格式 `recipe-census/1`；種子 0～199；薄格門檻：不同設計 < 12。由 `scripts/recipe_census.py` 產生，計時欄每次不同。

- 格子 136：正常 94、薄 34、空 8、設計上不存在 0（骨架稀有度下限：被動至少 epic、反應至少 rare）
- 其中遊戲會出題（出題檢查通過）的：空 8、薄 34；其餘空格是規則上就沒有專屬來源（遊戲不出這題）

## 依關鍵字（不含設計上不存在；「會出題」＝出題檢查通過的空格與薄格）

| 關鍵字 | 空 | 薄 | 正常 | 會出題的空 | 會出題的薄 |
|---|---|---|---|---|---|
| - | 0 | 0 | 8 | 0 | 0 |
| ignite | 0 | 2 | 6 | 0 | 2 |
| wet | 0 | 0 | 8 | 0 | 0 |
| charged | 0 | 8 | 0 | 0 | 8 |
| frozen | 0 | 6 | 2 | 0 | 6 |
| prone | 0 | 4 | 4 | 0 | 4 |
| collision | 0 | 0 | 8 | 0 | 0 |
| marked | 0 | 2 | 6 | 0 | 2 |
| high_ground | 0 | 0 | 8 | 0 | 0 |
| concealed | 0 | 4 | 4 | 0 | 4 |
| summon | 0 | 8 | 0 | 0 | 8 |
| poisoned | 0 | 0 | 8 | 0 | 0 |
| form | 8 | 0 | 0 | 8 | 0 |
| combo_point | 0 | 0 | 8 | 0 | 0 |
| fury | 0 | 0 | 8 | 0 | 0 |
| focus | 0 | 0 | 8 | 0 | 0 |
| ki | 0 | 0 | 8 | 0 | 0 |

## 依種類

| 種類 | 空 | 薄 | 正常 | 會出題的空 | 會出題的薄 |
|---|---|---|---|---|---|
| reaction | 8 | 34 | 94 | 8 | 34 |

## 空格與薄格（依玩家遇到的頻率排序）

| 關鍵字 | 種類 | 階 | 稀有度 | 狀態 | 會出題 | 合法 | 設計 | 主要原因 | 判斷 | 中位 ms |
|---|---|---|---|---|---|---|---|---|---|---|
| charged | reaction | 2 | rare | thin | 是 | 200 | 4 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 5.2 |
| concealed | reaction | 2 | rare | thin | 是 | 200 | 5 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 7.7 |
| form | reaction | 2 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| frozen | reaction | 2 | rare | thin | 是 | 200 | 8 |  | 配方稀少：偶爾帶到專屬關鍵字 | 4.9 |
| marked | reaction | 2 | rare | thin | 是 | 200 | 9 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 7.0 |
| summon | reaction | 2 | rare | thin | 是 | 200 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 7.3 |
| charged | reaction | 1 | rare | thin | 是 | 189 | 10 | keyword_exhausted 11 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 68.4 |
| charged | reaction | 3 | rare | thin | 是 | 200 | 5 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 5.5 |
| concealed | reaction | 3 | rare | thin | 是 | 200 | 6 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 7.1 |
| form | reaction | 1 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | reaction | 3 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| frozen | reaction | 3 | rare | thin | 是 | 200 | 8 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 5.4 |
| ignite | reaction | 3 | rare | thin | 是 | 200 | 9 |  | 配方稀少：偶爾帶到專屬關鍵字 | 6.7 |
| prone | reaction | 3 | rare | thin | 是 | 200 | 11 |  | 配方稀少：偶爾帶到專屬關鍵字 | 5.7 |
| summon | reaction | 1 | rare | thin | 是 | 200 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 5.7 |
| summon | reaction | 3 | rare | thin | 是 | 200 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 9.5 |
| charged | reaction | 2 | epic | thin | 是 | 200 | 4 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 5.3 |
| concealed | reaction | 2 | epic | thin | 是 | 200 | 5 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 6.2 |
| form | reaction | 2 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| frozen | reaction | 2 | epic | thin | 是 | 200 | 8 |  | 配方稀少：偶爾帶到專屬關鍵字 | 4.6 |
| marked | reaction | 2 | epic | thin | 是 | 200 | 9 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 7.3 |
| summon | reaction | 2 | epic | thin | 是 | 200 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 8.0 |
| charged | reaction | 1 | epic | thin | 是 | 189 | 10 | keyword_exhausted 11 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 67.8 |
| charged | reaction | 3 | epic | thin | 是 | 200 | 5 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 5.5 |
| concealed | reaction | 3 | epic | thin | 是 | 200 | 6 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 8.0 |
| form | reaction | 1 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | reaction | 3 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| frozen | reaction | 3 | epic | thin | 是 | 200 | 8 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 5.6 |
| ignite | reaction | 3 | epic | thin | 是 | 200 | 9 |  | 配方稀少：偶爾帶到專屬關鍵字 | 6.6 |
| prone | reaction | 3 | epic | thin | 是 | 200 | 11 |  | 配方稀少：偶爾帶到專屬關鍵字 | 5.7 |
| summon | reaction | 1 | epic | thin | 是 | 200 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 6.1 |
| summon | reaction | 3 | epic | thin | 是 | 200 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 9.8 |
| charged | reaction | 4 | rare | thin | 是 | 200 | 4 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 6.1 |
| form | reaction | 4 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| frozen | reaction | 4 | rare | thin | 是 | 200 | 7 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 5.5 |
| prone | reaction | 4 | rare | thin | 是 | 200 | 10 |  | 配方稀少：偶爾帶到專屬關鍵字 | 7.3 |
| summon | reaction | 4 | rare | thin | 是 | 200 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 12.2 |
| charged | reaction | 4 | epic | thin | 是 | 200 | 4 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 5.6 |
| form | reaction | 4 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| frozen | reaction | 4 | epic | thin | 是 | 200 | 7 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 6.0 |
| prone | reaction | 4 | epic | thin | 是 | 200 | 10 |  | 配方稀少：偶爾帶到專屬關鍵字 | 7.5 |
| summon | reaction | 4 | epic | thin | 是 | 200 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 11.8 |

## 全部格子

| 關鍵字 | 種類 | 階 | 稀有度 | 合法 | 設計 | 護主 | 主要原因 | 平均 ms | 中位 ms |
|---|---|---|---|---|---|---|---|---|---|
| - | reaction | 1 | rare | 200 | 89 | 2 |  | 1.9 | 1.9 |
| - | reaction | 1 | epic | 200 | 89 | 2 |  | 1.9 | 1.9 |
| - | reaction | 2 | rare | 200 | 80 | 2 |  | 2.2 | 2.2 |
| - | reaction | 2 | epic | 200 | 80 | 2 |  | 2.1 | 2.1 |
| - | reaction | 3 | rare | 200 | 71 | 2 |  | 2.3 | 2.2 |
| - | reaction | 3 | epic | 200 | 71 | 2 |  | 2.3 | 2.2 |
| - | reaction | 4 | rare | 200 | 68 | 2 |  | 2.4 | 2.3 |
| - | reaction | 4 | epic | 200 | 68 | 2 |  | 2.4 | 2.3 |
| ignite | reaction | 1 | rare | 200 | 54 | 0 |  | 33.9 | 23.7 |
| ignite | reaction | 1 | epic | 200 | 54 | 0 |  | 34.0 | 23.9 |
| ignite | reaction | 2 | rare | 200 | 12 | 185 |  | 6.3 | 5.3 |
| ignite | reaction | 2 | epic | 200 | 12 | 185 |  | 6.4 | 5.2 |
| ignite | reaction | 3 | rare | 200 | 9 | 187 |  | 7.9 | 6.7 |
| ignite | reaction | 3 | epic | 200 | 9 | 187 |  | 8.1 | 6.6 |
| ignite | reaction | 4 | rare | 200 | 34 | 0 |  | 1795.7 | 1207.0 |
| ignite | reaction | 4 | epic | 200 | 34 | 0 |  | 1770.7 | 1138.1 |
| wet | reaction | 1 | rare | 200 | 70 | 0 |  | 6.6 | 5.5 |
| wet | reaction | 1 | epic | 200 | 70 | 0 |  | 6.7 | 5.3 |
| wet | reaction | 2 | rare | 200 | 50 | 97 |  | 7.3 | 5.8 |
| wet | reaction | 2 | epic | 200 | 50 | 97 |  | 7.4 | 6.1 |
| wet | reaction | 3 | rare | 200 | 38 | 97 |  | 8.0 | 6.4 |
| wet | reaction | 3 | epic | 200 | 38 | 97 |  | 8.0 | 7.0 |
| wet | reaction | 4 | rare | 200 | 29 | 0 |  | 123.3 | 30.9 |
| wet | reaction | 4 | epic | 200 | 29 | 0 |  | 122.4 | 34.4 |
| charged | reaction | 1 | rare | 189 | 10 | 0 | keyword_exhausted 11 | 104.0 | 68.4 |
| charged | reaction | 1 | epic | 189 | 10 | 0 | keyword_exhausted 11 | 103.0 | 67.8 |
| charged | reaction | 2 | rare | 200 | 4 | 191 |  | 6.6 | 5.2 |
| charged | reaction | 2 | epic | 200 | 4 | 191 |  | 6.8 | 5.3 |
| charged | reaction | 3 | rare | 200 | 5 | 190 |  | 7.1 | 5.5 |
| charged | reaction | 3 | epic | 200 | 5 | 190 |  | 7.4 | 5.5 |
| charged | reaction | 4 | rare | 200 | 4 | 191 |  | 7.6 | 6.1 |
| charged | reaction | 4 | epic | 200 | 4 | 191 |  | 7.4 | 5.6 |
| frozen | reaction | 1 | rare | 198 | 28 | 0 | keyword_exhausted 2 | 56.1 | 40.8 |
| frozen | reaction | 1 | epic | 198 | 28 | 0 | keyword_exhausted 2 | 56.3 | 40.1 |
| frozen | reaction | 2 | rare | 200 | 8 | 186 |  | 6.1 | 4.9 |
| frozen | reaction | 2 | epic | 200 | 8 | 186 |  | 5.9 | 4.6 |
| frozen | reaction | 3 | rare | 200 | 8 | 186 |  | 6.9 | 5.4 |
| frozen | reaction | 3 | epic | 200 | 8 | 186 |  | 7.0 | 5.6 |
| frozen | reaction | 4 | rare | 200 | 7 | 184 |  | 7.5 | 5.5 |
| frozen | reaction | 4 | epic | 200 | 7 | 184 |  | 7.4 | 6.0 |
| prone | reaction | 1 | rare | 200 | 25 | 168 |  | 4.9 | 3.7 |
| prone | reaction | 1 | epic | 200 | 25 | 168 |  | 4.8 | 3.7 |
| prone | reaction | 2 | rare | 200 | 20 | 178 |  | 6.8 | 5.1 |
| prone | reaction | 2 | epic | 200 | 20 | 178 |  | 6.8 | 5.3 |
| prone | reaction | 3 | rare | 200 | 11 | 188 |  | 7.4 | 5.7 |
| prone | reaction | 3 | epic | 200 | 11 | 188 |  | 7.4 | 5.7 |
| prone | reaction | 4 | rare | 200 | 10 | 189 |  | 9.7 | 7.3 |
| prone | reaction | 4 | epic | 200 | 10 | 189 |  | 9.6 | 7.5 |
| collision | reaction | 1 | rare | 200 | 100 | 0 |  | 12.2 | 8.1 |
| collision | reaction | 1 | epic | 200 | 100 | 0 |  | 12.1 | 8.0 |
| collision | reaction | 2 | rare | 200 | 40 | 149 |  | 7.9 | 6.3 |
| collision | reaction | 2 | epic | 200 | 40 | 149 |  | 7.9 | 6.2 |
| collision | reaction | 3 | rare | 200 | 30 | 159 |  | 11.5 | 9.2 |
| collision | reaction | 3 | epic | 200 | 30 | 159 |  | 12.3 | 9.6 |
| collision | reaction | 4 | rare | 200 | 27 | 164 |  | 12.2 | 9.4 |
| collision | reaction | 4 | epic | 200 | 27 | 164 |  | 12.1 | 9.2 |
| marked | reaction | 1 | rare | 195 | 53 | 0 | keyword_exhausted 5 | 91.9 | 66.9 |
| marked | reaction | 1 | epic | 195 | 53 | 0 | keyword_exhausted 5 | 92.3 | 64.7 |
| marked | reaction | 2 | rare | 200 | 9 | 191 |  | 9.1 | 7.0 |
| marked | reaction | 2 | epic | 200 | 9 | 191 |  | 9.3 | 7.3 |
| marked | reaction | 3 | rare | 194 | 62 | 0 | keyword_exhausted 6 | 3089.9 | 2320.4 |
| marked | reaction | 3 | epic | 194 | 62 | 0 | keyword_exhausted 6 | 3078.3 | 2293.0 |
| marked | reaction | 4 | rare | 174 | 56 | 0 | keyword_exhausted 26 | 4011.2 | 3307.9 |
| marked | reaction | 4 | epic | 174 | 56 | 0 | keyword_exhausted 26 | 4020.4 | 3333.7 |
| high_ground | reaction | 1 | rare | 200 | 111 | 0 |  | 7.7 | 6.3 |
| high_ground | reaction | 1 | epic | 200 | 111 | 0 |  | 7.9 | 6.9 |
| high_ground | reaction | 2 | rare | 200 | 65 | 97 |  | 9.8 | 8.2 |
| high_ground | reaction | 2 | epic | 200 | 65 | 97 |  | 10.2 | 8.7 |
| high_ground | reaction | 3 | rare | 200 | 83 | 0 |  | 158.6 | 32.3 |
| high_ground | reaction | 3 | epic | 200 | 83 | 0 |  | 159.0 | 37.3 |
| high_ground | reaction | 4 | rare | 200 | 71 | 0 |  | 158.5 | 33.9 |
| high_ground | reaction | 4 | epic | 200 | 71 | 0 |  | 160.6 | 34.4 |
| concealed | reaction | 1 | rare | 200 | 20 | 0 |  | 84.9 | 60.2 |
| concealed | reaction | 1 | epic | 200 | 20 | 0 |  | 84.7 | 59.6 |
| concealed | reaction | 2 | rare | 200 | 5 | 192 |  | 9.6 | 7.7 |
| concealed | reaction | 2 | epic | 200 | 5 | 192 |  | 8.3 | 6.2 |
| concealed | reaction | 3 | rare | 200 | 6 | 190 |  | 9.2 | 7.1 |
| concealed | reaction | 3 | epic | 200 | 6 | 190 |  | 10.3 | 8.0 |
| concealed | reaction | 4 | rare | 195 | 16 | 0 | keyword_exhausted 5 | 2091.6 | 1534.4 |
| concealed | reaction | 4 | epic | 195 | 16 | 0 | keyword_exhausted 5 | 2090.4 | 1499.8 |
| summon | reaction | 1 | rare | 200 | 1 | 200 |  | 7.4 | 5.7 |
| summon | reaction | 1 | epic | 200 | 1 | 200 |  | 7.6 | 6.1 |
| summon | reaction | 2 | rare | 200 | 1 | 200 |  | 9.7 | 7.3 |
| summon | reaction | 2 | epic | 200 | 1 | 200 |  | 10.3 | 8.0 |
| summon | reaction | 3 | rare | 200 | 1 | 200 |  | 12.6 | 9.5 |
| summon | reaction | 3 | epic | 200 | 1 | 200 |  | 13.5 | 9.8 |
| summon | reaction | 4 | rare | 200 | 1 | 200 |  | 15.5 | 12.2 |
| summon | reaction | 4 | epic | 200 | 1 | 200 |  | 15.2 | 11.8 |
| poisoned | reaction | 1 | rare | 192 | 69 | 0 | keyword_exhausted 8 | 167.6 | 115.5 |
| poisoned | reaction | 1 | epic | 192 | 69 | 0 | keyword_exhausted 8 | 167.7 | 117.2 |
| poisoned | reaction | 2 | rare | 184 | 69 | 0 | keyword_exhausted 16 | 172.2 | 126.8 |
| poisoned | reaction | 2 | epic | 184 | 69 | 0 | keyword_exhausted 16 | 171.1 | 124.4 |
| poisoned | reaction | 3 | rare | 134 | 60 | 0 | keyword_exhausted 66 | 244.7 | 227.1 |
| poisoned | reaction | 3 | epic | 134 | 60 | 0 | keyword_exhausted 66 | 243.7 | 226.7 |
| poisoned | reaction | 4 | rare | 93 | 40 | 0 | keyword_exhausted 107 | 315.8 | 416.9 |
| poisoned | reaction | 4 | epic | 93 | 40 | 0 | keyword_exhausted 107 | 314.3 | 413.3 |
| form | reaction | 1 | rare | 0 | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 1 | epic | 0 | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 2 | rare | 0 | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 2 | epic | 0 | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 3 | rare | 0 | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 3 | epic | 0 | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 4 | rare | 0 | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 4 | epic | 0 | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| combo_point | reaction | 1 | rare | 200 | 117 | 0 |  | 5.5 | 4.6 |
| combo_point | reaction | 1 | epic | 200 | 117 | 0 |  | 5.7 | 4.7 |
| combo_point | reaction | 2 | rare | 200 | 112 | 0 |  | 6.5 | 5.2 |
| combo_point | reaction | 2 | epic | 200 | 112 | 0 |  | 6.6 | 5.4 |
| combo_point | reaction | 3 | rare | 200 | 90 | 0 |  | 7.1 | 5.9 |
| combo_point | reaction | 3 | epic | 200 | 90 | 0 |  | 7.1 | 6.0 |
| combo_point | reaction | 4 | rare | 200 | 72 | 0 |  | 7.3 | 6.0 |
| combo_point | reaction | 4 | epic | 200 | 72 | 0 |  | 7.6 | 5.8 |
| fury | reaction | 1 | rare | 200 | 117 | 0 |  | 5.6 | 4.5 |
| fury | reaction | 1 | epic | 200 | 117 | 0 |  | 5.6 | 4.6 |
| fury | reaction | 2 | rare | 200 | 112 | 0 |  | 6.4 | 4.9 |
| fury | reaction | 2 | epic | 200 | 112 | 0 |  | 6.4 | 5.2 |
| fury | reaction | 3 | rare | 200 | 90 | 0 |  | 7.0 | 5.8 |
| fury | reaction | 3 | epic | 200 | 90 | 0 |  | 7.0 | 5.6 |
| fury | reaction | 4 | rare | 200 | 72 | 0 |  | 7.4 | 5.9 |
| fury | reaction | 4 | epic | 200 | 72 | 0 |  | 7.7 | 6.3 |
| focus | reaction | 1 | rare | 200 | 117 | 0 |  | 5.6 | 4.6 |
| focus | reaction | 1 | epic | 200 | 117 | 0 |  | 5.5 | 4.5 |
| focus | reaction | 2 | rare | 200 | 112 | 0 |  | 6.5 | 5.1 |
| focus | reaction | 2 | epic | 200 | 112 | 0 |  | 6.5 | 5.3 |
| focus | reaction | 3 | rare | 200 | 90 | 0 |  | 7.2 | 5.9 |
| focus | reaction | 3 | epic | 200 | 90 | 0 |  | 7.0 | 5.7 |
| focus | reaction | 4 | rare | 200 | 72 | 0 |  | 7.2 | 5.8 |
| focus | reaction | 4 | epic | 200 | 72 | 0 |  | 7.2 | 5.9 |
| ki | reaction | 1 | rare | 200 | 117 | 0 |  | 5.4 | 4.3 |
| ki | reaction | 1 | epic | 200 | 117 | 0 |  | 5.7 | 4.5 |
| ki | reaction | 2 | rare | 200 | 112 | 0 |  | 6.5 | 5.3 |
| ki | reaction | 2 | epic | 200 | 112 | 0 |  | 6.5 | 5.2 |
| ki | reaction | 3 | rare | 200 | 90 | 0 |  | 7.0 | 5.7 |
| ki | reaction | 3 | epic | 200 | 90 | 0 |  | 6.9 | 5.8 |
| ki | reaction | 4 | rare | 200 | 72 | 0 |  | 7.1 | 5.8 |
| ki | reaction | 4 | epic | 200 | 72 | 0 |  | 7.1 | 5.8 |
