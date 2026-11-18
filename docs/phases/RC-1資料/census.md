# 組合器配方盤點摘要

格式 `recipe-census/1`；種子 0～199；薄格門檻：不同設計 < 12。由 `scripts/recipe_census.py` 產生，計時欄每次不同。

- 格子 612：正常 332、薄 4、空 72、設計上不存在 204（骨架稀有度下限：被動至少 epic、反應至少 rare）
- 其中遊戲會出題（出題檢查通過）的：空 32、薄 4；其餘空格是規則上就沒有專屬來源（遊戲不出這題）

## 依關鍵字（不含設計上不存在；「會出題」＝出題檢查通過的空格與薄格）

| 關鍵字 | 空 | 薄 | 正常 | 會出題的空 | 會出題的薄 |
|---|---|---|---|---|---|
| - | 0 | 0 | 24 | 0 | 0 |
| ignite | 0 | 0 | 24 | 0 | 0 |
| wet | 4 | 0 | 20 | 0 | 0 |
| charged | 0 | 2 | 22 | 0 | 2 |
| frozen | 0 | 0 | 24 | 0 | 0 |
| prone | 4 | 0 | 20 | 0 | 0 |
| collision | 4 | 0 | 20 | 0 | 0 |
| marked | 0 | 0 | 24 | 0 | 0 |
| high_ground | 4 | 0 | 20 | 0 | 0 |
| concealed | 0 | 0 | 24 | 0 | 0 |
| summon | 16 | 2 | 6 | 12 | 2 |
| poisoned | 0 | 0 | 24 | 0 | 0 |
| form | 24 | 0 | 0 | 20 | 0 |
| combo_point | 4 | 0 | 20 | 0 | 0 |
| fury | 4 | 0 | 20 | 0 | 0 |
| focus | 4 | 0 | 20 | 0 | 0 |
| ki | 4 | 0 | 20 | 0 | 0 |

## 依種類

| 種類 | 空 | 薄 | 正常 | 會出題的空 | 會出題的薄 |
|---|---|---|---|---|---|
| active | 48 | 2 | 154 | 8 | 2 |
| passive | 8 | 0 | 60 | 8 | 0 |
| reaction | 16 | 2 | 118 | 16 | 2 |

## 空格與薄格（依玩家遇到的頻率排序）

| 關鍵字 | 種類 | 階 | 稀有度 | 狀態 | 會出題 | 合法 | 設計 | 主要原因 | 判斷 | 中位 ms |
|---|---|---|---|---|---|---|---|---|---|---|
| collision | active | 2 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 708.8 |
| combo_point | active | 2 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 1.1 |
| focus | active | 2 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 1.0 |
| form | active | 2 | common | empty | 否 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 2 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| fury | active | 2 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 1.0 |
| high_ground | active | 2 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 749.8 |
| ki | active | 2 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| prone | active | 2 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 848.2 |
| summon | active | 2 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 754.0 |
| wet | active | 2 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 687.8 |
| collision | active | 1 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 692.1 |
| collision | active | 3 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 841.4 |
| combo_point | active | 1 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 1.0 |
| combo_point | active | 3 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 1.1 |
| focus | active | 1 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 1.0 |
| focus | active | 3 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| form | active | 1 | common | empty | 否 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 1 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 3 | common | empty | 否 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 3 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| fury | active | 1 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 1.0 |
| fury | active | 3 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 1.0 |
| high_ground | active | 1 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 688.9 |
| high_ground | active | 3 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 893.4 |
| ki | active | 1 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| ki | active | 3 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 1.0 |
| prone | active | 1 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 777.5 |
| prone | active | 3 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 929.5 |
| summon | active | 1 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 673.1 |
| summon | active | 1 | rare | thin | 是 | 200 | 1 |  | 配方稀少：偶爾帶到專屬關鍵字 | 309.6 |
| summon | active | 3 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 980.6 |
| wet | active | 1 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 614.7 |
| wet | active | 3 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 905.6 |
| form | active | 2 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 1 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 3 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | active | 1 | epic | thin | 是 | 200 | 1 |  | 配方稀少：偶爾帶到專屬關鍵字 | 399.1 |
| form | passive | 2 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | passive | 2 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 614.5 |
| form | reaction | 2 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | reaction | 2 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 只帶到通用規則：組合器認、退回路徑不收 | 602.1 |
| form | passive | 1 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | passive | 3 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | passive | 1 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 539.5 |
| summon | passive | 3 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 624.4 |
| collision | active | 4 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 1086.3 |
| combo_point | active | 4 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 1.0 |
| focus | active | 4 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| form | active | 4 | common | empty | 否 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 4 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| fury | active | 4 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 1.0 |
| high_ground | active | 4 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 1095.1 |
| ki | active | 4 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 1.1 |
| prone | active | 4 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 1127.9 |
| summon | active | 4 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 1344.8 |
| wet | active | 4 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 1231.0 |
| charged | reaction | 1 | rare | thin | 是 | 189 | 10 | keyword_exhausted 11 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 108.3 |
| form | reaction | 1 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | reaction | 3 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | reaction | 1 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 只帶到通用規則：組合器認、退回路徑不收 | 515.0 |
| summon | reaction | 3 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 只帶到通用規則：組合器認、退回路徑不收 | 684.8 |
| form | reaction | 2 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | reaction | 2 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 只帶到通用規則：組合器認、退回路徑不收 | 613.5 |
| form | active | 4 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| charged | reaction | 1 | epic | thin | 是 | 189 | 10 | keyword_exhausted 11 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 93.6 |
| form | reaction | 1 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | reaction | 3 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | reaction | 1 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 只帶到通用規則：組合器認、退回路徑不收 | 496.7 |
| summon | reaction | 3 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 只帶到通用規則：組合器認、退回路徑不收 | 676.4 |
| form | passive | 4 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | passive | 4 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 640.7 |
| form | reaction | 4 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | reaction | 4 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 只帶到通用規則：組合器認、退回路徑不收 | 725.2 |
| form | reaction | 4 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | reaction | 4 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 只帶到通用規則：組合器認、退回路徑不收 | 719.0 |

## 全部格子

| 關鍵字 | 種類 | 階 | 稀有度 | 合法 | 設計 | 主要原因 | 平均 ms | 中位 ms |
|---|---|---|---|---|---|---|---|---|
| - | active | 1 | common | 200 | 164 |  | 2.8 | 2.4 |
| - | active | 1 | rare | 181 | 161 | not_fit.kind(reaction) 19 | 18.1 | 3.5 |
| - | active | 1 | epic | 129 | 117 | not_fit.kind(passive) 48 | 14.6 | 3.0 |
| - | active | 2 | common | 200 | 162 |  | 3.0 | 2.5 |
| - | active | 2 | rare | 167 | 153 | not_fit.kind(reaction) 19 | 6.9 | 3.2 |
| - | active | 2 | epic | 117 | 115 | not_fit.kind(passive) 48 | 5.8 | 2.8 |
| - | active | 3 | common | 200 | 162 |  | 3.3 | 2.6 |
| - | active | 3 | rare | 167 | 154 | not_fit.kind(reaction) 19 | 6.8 | 3.3 |
| - | active | 3 | epic | 117 | 116 | not_fit.kind(passive) 48 | 4.9 | 3.0 |
| - | active | 4 | common | 200 | 159 |  | 4.1 | 2.8 |
| - | active | 4 | rare | 167 | 152 | not_fit.kind(reaction) 19 | 6.5 | 3.3 |
| - | active | 4 | epic | 117 | 116 | not_fit.kind(passive) 48 | 5.5 | 3.0 |
| - | passive | 1 | epic | 200 | 129 |  | 2.2 | 2.1 |
| - | passive | 2 | epic | 200 | 131 |  | 2.3 | 2.2 |
| - | passive | 3 | epic | 200 | 123 |  | 2.3 | 2.3 |
| - | passive | 4 | epic | 200 | 120 |  | 2.5 | 2.4 |
| - | reaction | 1 | rare | 200 | 92 |  | 2.2 | 2.1 |
| - | reaction | 1 | epic | 200 | 92 |  | 2.3 | 2.2 |
| - | reaction | 2 | rare | 200 | 78 |  | 2.6 | 2.5 |
| - | reaction | 2 | epic | 200 | 78 |  | 2.6 | 2.5 |
| - | reaction | 3 | rare | 200 | 67 |  | 2.9 | 2.6 |
| - | reaction | 3 | epic | 200 | 67 |  | 2.8 | 2.6 |
| - | reaction | 4 | rare | 200 | 67 |  | 2.7 | 2.5 |
| - | reaction | 4 | epic | 200 | 67 |  | 2.8 | 2.5 |
| ignite | active | 1 | common | 200 | 97 |  | 19.9 | 13.8 |
| ignite | active | 1 | rare | 176 | 149 | not_fit.keyword 22 | 153.8 | 64.2 |
| ignite | active | 1 | epic | 148 | 136 | not_fit.kind(passive) 22 | 127.8 | 49.4 |
| ignite | active | 2 | common | 200 | 101 |  | 21.1 | 14.7 |
| ignite | active | 2 | rare | 166 | 106 | not_fit.keyword 33 | 41.5 | 20.7 |
| ignite | active | 2 | epic | 146 | 102 | not_fit.keyword 30 | 31.6 | 15.8 |
| ignite | active | 3 | common | 200 | 96 |  | 24.6 | 16.8 |
| ignite | active | 3 | rare | 171 | 107 | not_fit.keyword 28 | 36.1 | 19.4 |
| ignite | active | 3 | epic | 155 | 112 | not_fit.kind(passive) 22 | 29.2 | 16.8 |
| ignite | active | 4 | common | 200 | 100 |  | 30.6 | 19.8 |
| ignite | active | 4 | rare | 171 | 107 | not_fit.keyword 27 | 42.0 | 21.5 |
| ignite | active | 4 | epic | 148 | 104 | not_fit.keyword 25 | 33.0 | 19.8 |
| ignite | passive | 1 | epic | 200 | 68 |  | 18.1 | 12.2 |
| ignite | passive | 2 | epic | 200 | 67 |  | 17.0 | 12.3 |
| ignite | passive | 3 | epic | 200 | 63 |  | 18.0 | 13.2 |
| ignite | passive | 4 | epic | 200 | 62 |  | 21.1 | 15.1 |
| ignite | reaction | 1 | rare | 200 | 54 |  | 37.6 | 27.4 |
| ignite | reaction | 1 | epic | 200 | 54 |  | 37.7 | 27.1 |
| ignite | reaction | 2 | rare | 200 | 55 |  | 50.6 | 35.3 |
| ignite | reaction | 2 | epic | 200 | 55 |  | 50.8 | 36.6 |
| ignite | reaction | 3 | rare | 200 | 52 |  | 53.7 | 38.1 |
| ignite | reaction | 3 | epic | 200 | 52 |  | 54.0 | 39.3 |
| ignite | reaction | 4 | rare | 200 | 34 |  | 99.2 | 62.6 |
| ignite | reaction | 4 | epic | 200 | 34 |  | 98.1 | 64.0 |
| wet | active | 1 | common | 0 | 0 | keyword_exhausted 200 | 671.4 | 614.7 |
| wet | active | 1 | rare | 70 | 67 | not_fit.kind(reaction) 130 | 492.1 | 345.5 |
| wet | active | 1 | epic | 33 | 32 | not_fit.kind(passive) 105 | 217.1 | 96.7 |
| wet | active | 2 | common | 0 | 0 | keyword_exhausted 200 | 755.8 | 687.8 |
| wet | active | 2 | rare | 135 | 34 | not_fit.kind(reaction) 65 | 81.9 | 45.3 |
| wet | active | 2 | epic | 82 | 25 | not_fit.kind(passive) 72 | 60.3 | 29.4 |
| wet | active | 3 | common | 0 | 0 | keyword_exhausted 200 | 960.5 | 905.6 |
| wet | active | 3 | rare | 132 | 30 | not_fit.kind(reaction) 68 | 74.2 | 43.6 |
| wet | active | 3 | epic | 81 | 24 | not_fit.kind(passive) 73 | 48.3 | 27.3 |
| wet | active | 4 | common | 0 | 0 | keyword_exhausted 200 | 1248.0 | 1231.0 |
| wet | active | 4 | rare | 129 | 25 | not_fit.kind(reaction) 71 | 85.9 | 46.0 |
| wet | active | 4 | epic | 84 | 25 | not_fit.kind(passive) 69 | 57.9 | 30.7 |
| wet | passive | 1 | epic | 200 | 96 |  | 6.4 | 4.5 |
| wet | passive | 2 | epic | 200 | 96 |  | 6.7 | 5.0 |
| wet | passive | 3 | epic | 200 | 92 |  | 7.9 | 5.6 |
| wet | passive | 4 | epic | 200 | 89 |  | 7.7 | 5.7 |
| wet | reaction | 1 | rare | 200 | 70 |  | 7.6 | 6.4 |
| wet | reaction | 1 | epic | 200 | 70 |  | 7.7 | 6.4 |
| wet | reaction | 2 | rare | 200 | 66 |  | 9.0 | 7.8 |
| wet | reaction | 2 | epic | 200 | 66 |  | 9.1 | 7.6 |
| wet | reaction | 3 | rare | 200 | 51 |  | 9.9 | 8.2 |
| wet | reaction | 3 | epic | 200 | 51 |  | 10.0 | 8.5 |
| wet | reaction | 4 | rare | 200 | 32 |  | 11.0 | 9.0 |
| wet | reaction | 4 | epic | 200 | 32 |  | 11.1 | 9.2 |
| charged | active | 1 | common | 200 | 54 |  | 44.8 | 32.6 |
| charged | active | 1 | rare | 152 | 112 | not_fit.keyword 40 | 294.9 | 188.5 |
| charged | active | 1 | epic | 140 | 110 | not_fit.keyword 36 | 245.3 | 161.7 |
| charged | active | 2 | common | 200 | 58 |  | 49.5 | 35.4 |
| charged | active | 2 | rare | 150 | 66 | not_fit.keyword 45 | 54.6 | 24.7 |
| charged | active | 2 | epic | 147 | 81 | not_fit.keyword 33 | 62.7 | 30.5 |
| charged | active | 3 | common | 200 | 61 |  | 78.6 | 51.1 |
| charged | active | 3 | rare | 171 | 112 | not_fit.keyword 26 | 43.5 | 19.1 |
| charged | active | 3 | epic | 154 | 105 | not_fit.keyword 27 | 48.6 | 21.2 |
| charged | active | 4 | common | 200 | 58 |  | 94.0 | 71.9 |
| charged | active | 4 | rare | 166 | 102 | not_fit.keyword 30 | 55.3 | 24.4 |
| charged | active | 4 | epic | 162 | 109 | not_fit.keyword 19 | 60.5 | 29.7 |
| charged | passive | 1 | epic | 200 | 12 |  | 64.4 | 40.2 |
| charged | passive | 2 | epic | 200 | 14 |  | 53.8 | 38.9 |
| charged | passive | 3 | epic | 200 | 14 |  | 52.2 | 36.9 |
| charged | passive | 4 | epic | 200 | 14 |  | 57.1 | 38.5 |
| charged | reaction | 1 | rare | 189 | 10 | keyword_exhausted 11 | 155.6 | 108.3 |
| charged | reaction | 1 | epic | 189 | 10 | keyword_exhausted 11 | 144.1 | 93.6 |
| charged | reaction | 2 | rare | 192 | 13 | keyword_exhausted 8 | 176.6 | 113.6 |
| charged | reaction | 2 | epic | 192 | 13 | keyword_exhausted 8 | 173.6 | 112.8 |
| charged | reaction | 3 | rare | 195 | 13 | keyword_exhausted 5 | 172.4 | 118.2 |
| charged | reaction | 3 | epic | 195 | 13 | keyword_exhausted 5 | 175.0 | 110.0 |
| charged | reaction | 4 | rare | 194 | 13 | keyword_exhausted 6 | 200.6 | 114.5 |
| charged | reaction | 4 | epic | 194 | 13 | keyword_exhausted 6 | 180.3 | 111.4 |
| frozen | active | 1 | common | 200 | 54 |  | 58.3 | 38.9 |
| frozen | active | 1 | rare | 166 | 123 | not_fit.keyword 28 | 297.4 | 134.2 |
| frozen | active | 1 | epic | 153 | 125 | not_fit.keyword 26 | 289.0 | 140.2 |
| frozen | active | 2 | common | 200 | 54 |  | 69.1 | 48.3 |
| frozen | active | 2 | rare | 165 | 100 | not_fit.keyword 29 | 74.5 | 33.3 |
| frozen | active | 2 | epic | 156 | 90 | not_fit.keyword 32 | 75.7 | 44.0 |
| frozen | active | 3 | common | 200 | 54 |  | 84.2 | 56.4 |
| frozen | active | 3 | rare | 153 | 91 | not_fit.keyword 43 | 75.1 | 38.2 |
| frozen | active | 3 | epic | 151 | 89 | not_fit.keyword 34 | 72.7 | 37.0 |
| frozen | active | 4 | common | 200 | 55 |  | 91.2 | 60.3 |
| frozen | active | 4 | rare | 161 | 102 | not_fit.keyword 37 | 90.7 | 32.8 |
| frozen | active | 4 | epic | 151 | 84 | not_fit.keyword 34 | 74.3 | 40.3 |
| frozen | passive | 1 | epic | 200 | 14 |  | 61.7 | 38.4 |
| frozen | passive | 2 | epic | 200 | 14 |  | 58.8 | 35.6 |
| frozen | passive | 3 | epic | 200 | 14 |  | 58.8 | 34.6 |
| frozen | passive | 4 | epic | 200 | 14 |  | 61.5 | 37.8 |
| frozen | reaction | 1 | rare | 198 | 28 | keyword_exhausted 2 | 93.2 | 65.9 |
| frozen | reaction | 1 | epic | 198 | 28 | keyword_exhausted 2 | 97.6 | 71.4 |
| frozen | reaction | 2 | rare | 200 | 59 |  | 101.1 | 68.4 |
| frozen | reaction | 2 | epic | 200 | 59 |  | 103.3 | 75.2 |
| frozen | reaction | 3 | rare | 200 | 45 |  | 134.2 | 97.1 |
| frozen | reaction | 3 | epic | 200 | 45 |  | 137.2 | 98.1 |
| frozen | reaction | 4 | rare | 200 | 34 |  | 148.7 | 101.3 |
| frozen | reaction | 4 | epic | 200 | 34 |  | 155.5 | 101.1 |
| prone | active | 1 | common | 0 | 0 | keyword_exhausted 200 | 886.4 | 777.5 |
| prone | active | 1 | rare | 188 | 122 | not_fit.keyword 10 | 167.0 | 66.5 |
| prone | active | 1 | epic | 143 | 102 | not_fit.kind(passive) 47 | 98.6 | 26.0 |
| prone | active | 2 | common | 0 | 0 | keyword_exhausted 200 | 961.9 | 848.2 |
| prone | active | 2 | rare | 183 | 116 | not_fit.keyword 12 | 71.1 | 31.4 |
| prone | active | 2 | epic | 148 | 104 | not_fit.kind(passive) 44 | 47.9 | 21.8 |
| prone | active | 3 | common | 0 | 0 | keyword_exhausted 200 | 1087.2 | 929.5 |
| prone | active | 3 | rare | 182 | 116 | not_fit.keyword 15 | 73.1 | 34.4 |
| prone | active | 3 | epic | 147 | 99 | not_fit.kind(passive) 45 | 43.3 | 21.4 |
| prone | active | 4 | common | 0 | 0 | keyword_exhausted 200 | 1256.4 | 1127.9 |
| prone | active | 4 | rare | 180 | 112 | not_fit.keyword 19 | 73.6 | 31.6 |
| prone | active | 4 | epic | 152 | 106 | not_fit.kind(passive) 42 | 48.4 | 22.3 |
| prone | passive | 1 | epic | 200 | 93 |  | 10.0 | 6.9 |
| prone | passive | 2 | epic | 200 | 94 |  | 8.6 | 6.1 |
| prone | passive | 3 | epic | 200 | 89 |  | 9.9 | 7.2 |
| prone | passive | 4 | epic | 200 | 92 |  | 10.5 | 7.2 |
| prone | reaction | 1 | rare | 200 | 57 |  | 38.3 | 27.3 |
| prone | reaction | 1 | epic | 200 | 57 |  | 34.5 | 23.6 |
| prone | reaction | 2 | rare | 200 | 76 |  | 75.7 | 48.9 |
| prone | reaction | 2 | epic | 200 | 76 |  | 74.5 | 45.7 |
| prone | reaction | 3 | rare | 200 | 58 |  | 108.5 | 74.7 |
| prone | reaction | 3 | epic | 200 | 58 |  | 133.0 | 88.9 |
| prone | reaction | 4 | rare | 200 | 36 |  | 143.9 | 113.1 |
| prone | reaction | 4 | epic | 200 | 36 |  | 124.8 | 97.1 |
| collision | active | 1 | common | 0 | 0 | keyword_exhausted 200 | 792.2 | 692.1 |
| collision | active | 1 | rare | 192 | 158 | not_fit.kind(reaction) 8 | 143.9 | 47.1 |
| collision | active | 1 | epic | 169 | 135 | not_fit.kind(modifier) 16 | 106.7 | 28.4 |
| collision | active | 2 | common | 0 | 0 | keyword_exhausted 200 | 812.9 | 708.8 |
| collision | active | 2 | rare | 193 | 137 | not_fit.kind(reaction) 7 | 62.2 | 27.6 |
| collision | active | 2 | epic | 177 | 113 | not_fit.kind(modifier) 10 | 33.0 | 16.1 |
| collision | active | 3 | common | 0 | 0 | keyword_exhausted 200 | 922.5 | 841.4 |
| collision | active | 3 | rare | 194 | 138 | not_fit.kind(reaction) 6 | 54.2 | 23.7 |
| collision | active | 3 | epic | 172 | 122 | not_fit.kind(passive) 13 | 37.8 | 17.8 |
| collision | active | 4 | common | 0 | 0 | keyword_exhausted 200 | 1116.4 | 1086.3 |
| collision | active | 4 | rare | 195 | 144 | not_fit.kind(reaction) 5 | 39.0 | 21.5 |
| collision | active | 4 | epic | 170 | 126 | not_fit.kind(passive) 15 | 26.1 | 13.8 |
| collision | passive | 1 | epic | 200 | 88 |  | 18.7 | 13.3 |
| collision | passive | 2 | epic | 200 | 104 |  | 19.5 | 12.9 |
| collision | passive | 3 | epic | 200 | 108 |  | 18.3 | 13.0 |
| collision | passive | 4 | epic | 200 | 113 |  | 17.6 | 12.4 |
| collision | reaction | 1 | rare | 200 | 100 |  | 13.3 | 8.7 |
| collision | reaction | 1 | epic | 200 | 100 |  | 13.4 | 8.6 |
| collision | reaction | 2 | rare | 200 | 111 |  | 17.8 | 12.6 |
| collision | reaction | 2 | epic | 200 | 111 |  | 18.9 | 13.0 |
| collision | reaction | 3 | rare | 200 | 97 |  | 26.1 | 17.6 |
| collision | reaction | 3 | epic | 200 | 97 |  | 26.6 | 18.0 |
| collision | reaction | 4 | rare | 200 | 83 |  | 37.5 | 22.6 |
| collision | reaction | 4 | epic | 200 | 83 |  | 37.2 | 22.8 |
| marked | active | 1 | common | 200 | 80 |  | 31.9 | 24.1 |
| marked | active | 1 | rare | 194 | 170 | not_fit.kind(reaction) 6 | 211.9 | 98.1 |
| marked | active | 1 | epic | 116 | 111 | not_fit.kind(passive) 79 | 149.3 | 69.0 |
| marked | active | 2 | common | 200 | 83 |  | 37.3 | 28.5 |
| marked | active | 2 | rare | 197 | 124 | not_fit.kind(reaction) 3 | 49.8 | 22.0 |
| marked | active | 2 | epic | 137 | 87 | not_fit.kind(passive) 59 | 38.5 | 19.7 |
| marked | active | 3 | common | 200 | 90 |  | 38.1 | 26.5 |
| marked | active | 3 | rare | 198 | 134 | not_fit.kind(reaction) 2 | 54.0 | 25.9 |
| marked | active | 3 | epic | 139 | 95 | not_fit.kind(passive) 58 | 37.4 | 18.4 |
| marked | active | 4 | common | 200 | 87 |  | 43.4 | 33.7 |
| marked | active | 4 | rare | 199 | 185 | not_fit.kind(reaction) 1 | 272.0 | 60.3 |
| marked | active | 4 | epic | 124 | 112 | not_fit.kind(passive) 75 | 204.4 | 51.5 |
| marked | passive | 1 | epic | 200 | 96 |  | 6.6 | 4.7 |
| marked | passive | 2 | epic | 200 | 99 |  | 6.8 | 5.1 |
| marked | passive | 3 | epic | 200 | 95 |  | 7.1 | 5.4 |
| marked | passive | 4 | epic | 200 | 100 |  | 7.2 | 5.5 |
| marked | reaction | 1 | rare | 195 | 53 | keyword_exhausted 5 | 122.5 | 90.2 |
| marked | reaction | 1 | epic | 195 | 53 | keyword_exhausted 5 | 126.4 | 88.9 |
| marked | reaction | 2 | rare | 199 | 49 | keyword_exhausted 1 | 130.3 | 105.8 |
| marked | reaction | 2 | epic | 199 | 49 | keyword_exhausted 1 | 128.4 | 90.2 |
| marked | reaction | 3 | rare | 194 | 62 | keyword_exhausted 6 | 199.0 | 165.8 |
| marked | reaction | 3 | epic | 194 | 62 | keyword_exhausted 6 | 196.4 | 164.2 |
| marked | reaction | 4 | rare | 174 | 56 | keyword_exhausted 26 | 311.8 | 246.6 |
| marked | reaction | 4 | epic | 174 | 56 | keyword_exhausted 26 | 299.2 | 228.8 |
| high_ground | active | 1 | common | 0 | 0 | keyword_exhausted 200 | 696.9 | 688.9 |
| high_ground | active | 1 | rare | 110 | 100 | not_fit.kind(reaction) 90 | 394.6 | 276.6 |
| high_ground | active | 1 | epic | 55 | 53 | not_fit.kind(passive) 89 | 227.4 | 105.1 |
| high_ground | active | 2 | common | 0 | 0 | keyword_exhausted 200 | 763.7 | 749.8 |
| high_ground | active | 2 | rare | 139 | 52 | not_fit.kind(reaction) 61 | 97.6 | 59.5 |
| high_ground | active | 2 | epic | 93 | 42 | not_fit.kind(passive) 66 | 53.1 | 25.3 |
| high_ground | active | 3 | common | 0 | 0 | keyword_exhausted 200 | 911.2 | 893.4 |
| high_ground | active | 3 | rare | 140 | 53 | not_fit.kind(reaction) 60 | 68.5 | 41.3 |
| high_ground | active | 3 | epic | 92 | 41 | not_fit.kind(passive) 65 | 51.3 | 22.2 |
| high_ground | active | 4 | common | 0 | 0 | keyword_exhausted 200 | 1103.1 | 1095.1 |
| high_ground | active | 4 | rare | 109 | 94 | not_fit.kind(reaction) 91 | 438.1 | 164.6 |
| high_ground | active | 4 | epic | 49 | 48 | not_fit.kind(passive) 92 | 211.4 | 46.4 |
| high_ground | passive | 1 | epic | 200 | 108 |  | 6.6 | 4.5 |
| high_ground | passive | 2 | epic | 200 | 113 |  | 6.9 | 5.1 |
| high_ground | passive | 3 | epic | 200 | 107 |  | 7.7 | 5.6 |
| high_ground | passive | 4 | epic | 200 | 106 |  | 8.4 | 6.0 |
| high_ground | reaction | 1 | rare | 200 | 111 |  | 9.1 | 7.3 |
| high_ground | reaction | 1 | epic | 200 | 111 |  | 11.2 | 8.5 |
| high_ground | reaction | 2 | rare | 200 | 110 |  | 11.0 | 8.7 |
| high_ground | reaction | 2 | epic | 200 | 110 |  | 9.7 | 7.7 |
| high_ground | reaction | 3 | rare | 200 | 89 |  | 11.4 | 8.9 |
| high_ground | reaction | 3 | epic | 200 | 89 |  | 10.4 | 8.4 |
| high_ground | reaction | 4 | rare | 200 | 72 |  | 11.3 | 8.9 |
| high_ground | reaction | 4 | epic | 200 | 72 |  | 11.4 | 8.8 |
| concealed | active | 1 | common | 200 | 54 |  | 58.9 | 42.7 |
| concealed | active | 1 | rare | 197 | 150 | not_fit.kind(reaction) 3 | 287.6 | 168.4 |
| concealed | active | 1 | epic | 180 | 156 | not_fit.kind(passive) 17 | 289.9 | 152.6 |
| concealed | active | 2 | common | 200 | 58 |  | 64.0 | 45.4 |
| concealed | active | 2 | rare | 198 | 115 | not_fit.kind(reaction) 2 | 65.1 | 29.7 |
| concealed | active | 2 | epic | 181 | 113 | not_fit.kind(passive) 18 | 68.3 | 35.4 |
| concealed | active | 3 | common | 200 | 56 |  | 74.0 | 53.4 |
| concealed | active | 3 | rare | 197 | 112 | not_fit.kind(reaction) 3 | 71.4 | 29.3 |
| concealed | active | 3 | epic | 183 | 118 | not_fit.kind(passive) 14 | 70.6 | 31.1 |
| concealed | active | 4 | common | 200 | 62 |  | 89.1 | 61.1 |
| concealed | active | 4 | rare | 197 | 112 | not_fit.kind(reaction) 3 | 79.8 | 32.8 |
| concealed | active | 4 | epic | 177 | 111 | not_fit.kind(passive) 20 | 71.9 | 33.1 |
| concealed | passive | 1 | epic | 200 | 36 |  | 35.8 | 26.2 |
| concealed | passive | 2 | epic | 200 | 34 |  | 34.1 | 24.5 |
| concealed | passive | 3 | epic | 200 | 36 |  | 36.4 | 25.2 |
| concealed | passive | 4 | epic | 200 | 32 |  | 42.3 | 27.8 |
| concealed | reaction | 1 | rare | 200 | 20 |  | 87.0 | 65.0 |
| concealed | reaction | 1 | epic | 200 | 20 |  | 84.7 | 63.1 |
| concealed | reaction | 2 | rare | 196 | 14 | keyword_exhausted 4 | 138.8 | 106.4 |
| concealed | reaction | 2 | epic | 196 | 14 | keyword_exhausted 4 | 138.6 | 108.3 |
| concealed | reaction | 3 | rare | 198 | 17 | keyword_exhausted 2 | 133.5 | 99.6 |
| concealed | reaction | 3 | epic | 198 | 17 | keyword_exhausted 2 | 134.3 | 98.8 |
| concealed | reaction | 4 | rare | 195 | 16 | keyword_exhausted 5 | 144.5 | 96.9 |
| concealed | reaction | 4 | epic | 195 | 16 | keyword_exhausted 5 | 145.0 | 96.1 |
| summon | active | 1 | common | 0 | 0 | keyword_exhausted 200 | 729.3 | 673.1 |
| summon | active | 1 | rare | 200 | 1 |  | 525.5 | 309.6 |
| summon | active | 1 | epic | 200 | 1 |  | 637.6 | 399.1 |
| summon | active | 2 | common | 0 | 0 | keyword_exhausted 200 | 808.6 | 754.0 |
| summon | active | 2 | rare | 200 | 13 |  | 102.3 | 64.0 |
| summon | active | 2 | epic | 200 | 13 |  | 107.9 | 59.3 |
| summon | active | 3 | common | 0 | 0 | keyword_exhausted 200 | 1037.4 | 980.6 |
| summon | active | 3 | rare | 200 | 13 |  | 102.7 | 60.6 |
| summon | active | 3 | epic | 200 | 13 |  | 103.2 | 56.8 |
| summon | active | 4 | common | 0 | 0 | keyword_exhausted 200 | 1437.0 | 1344.8 |
| summon | active | 4 | rare | 200 | 13 |  | 135.7 | 75.0 |
| summon | active | 4 | epic | 200 | 13 |  | 176.9 | 101.3 |
| summon | passive | 1 | epic | 0 | 0 | keyword_exhausted 200 | 594.5 | 539.5 |
| summon | passive | 2 | epic | 0 | 0 | keyword_exhausted 200 | 661.4 | 614.5 |
| summon | passive | 3 | epic | 0 | 0 | keyword_exhausted 200 | 684.4 | 624.4 |
| summon | passive | 4 | epic | 0 | 0 | keyword_exhausted 200 | 701.9 | 640.7 |
| summon | reaction | 1 | rare | 0 | 0 | keyword_exhausted 200 | 571.3 | 515.0 |
| summon | reaction | 1 | epic | 0 | 0 | keyword_exhausted 200 | 539.2 | 496.7 |
| summon | reaction | 2 | rare | 0 | 0 | keyword_exhausted 200 | 671.1 | 602.1 |
| summon | reaction | 2 | epic | 0 | 0 | keyword_exhausted 200 | 668.9 | 613.5 |
| summon | reaction | 3 | rare | 0 | 0 | keyword_exhausted 200 | 754.4 | 684.8 |
| summon | reaction | 3 | epic | 0 | 0 | keyword_exhausted 200 | 737.9 | 676.4 |
| summon | reaction | 4 | rare | 0 | 0 | keyword_exhausted 200 | 813.0 | 725.2 |
| summon | reaction | 4 | epic | 0 | 0 | keyword_exhausted 200 | 798.3 | 719.0 |
| poisoned | active | 1 | common | 200 | 69 |  | 68.1 | 50.3 |
| poisoned | active | 1 | rare | 195 | 183 | not_fit.kind(reaction) 5 | 681.7 | 509.4 |
| poisoned | active | 1 | epic | 165 | 153 | not_fit.kind(passive) 21 | 583.2 | 346.6 |
| poisoned | active | 2 | common | 200 | 70 |  | 79.5 | 59.7 |
| poisoned | active | 2 | rare | 198 | 184 | not_fit.kind(reaction) 2 | 239.3 | 147.9 |
| poisoned | active | 2 | epic | 175 | 162 | not_fit.kind(passive) 12 | 200.1 | 99.4 |
| poisoned | active | 3 | common | 200 | 74 |  | 73.9 | 50.5 |
| poisoned | active | 3 | rare | 198 | 190 | not_fit.kind(reaction) 2 | 225.7 | 133.7 |
| poisoned | active | 3 | epic | 175 | 159 | not_fit.kind(passive) 14 | 216.2 | 102.7 |
| poisoned | active | 4 | common | 200 | 71 |  | 117.6 | 80.3 |
| poisoned | active | 4 | rare | 200 | 190 |  | 296.1 | 168.0 |
| poisoned | active | 4 | epic | 180 | 164 | not_fit.kind(modifier) 10 | 195.8 | 89.0 |
| poisoned | passive | 1 | epic | 200 | 25 |  | 85.2 | 51.9 |
| poisoned | passive | 2 | epic | 200 | 25 |  | 123.4 | 70.4 |
| poisoned | passive | 3 | epic | 197 | 27 | keyword_exhausted 3 | 139.0 | 83.7 |
| poisoned | passive | 4 | epic | 199 | 30 | keyword_exhausted 1 | 148.6 | 106.7 |
| poisoned | reaction | 1 | rare | 192 | 69 | keyword_exhausted 8 | 199.3 | 117.9 |
| poisoned | reaction | 1 | epic | 192 | 69 | keyword_exhausted 8 | 224.5 | 143.1 |
| poisoned | reaction | 2 | rare | 184 | 69 | keyword_exhausted 16 | 291.1 | 227.6 |
| poisoned | reaction | 2 | epic | 184 | 69 | keyword_exhausted 16 | 292.5 | 205.9 |
| poisoned | reaction | 3 | rare | 134 | 60 | keyword_exhausted 66 | 455.0 | 408.3 |
| poisoned | reaction | 3 | epic | 134 | 60 | keyword_exhausted 66 | 486.6 | 448.6 |
| poisoned | reaction | 4 | rare | 93 | 40 | keyword_exhausted 107 | 547.2 | 595.0 |
| poisoned | reaction | 4 | epic | 93 | 40 | keyword_exhausted 107 | 544.4 | 586.7 |
| form | active | 1 | common | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | active | 1 | rare | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | active | 1 | epic | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | active | 2 | common | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | active | 2 | rare | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | active | 2 | epic | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | active | 3 | common | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | active | 3 | rare | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | active | 3 | epic | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | active | 4 | common | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | active | 4 | rare | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | active | 4 | epic | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | passive | 1 | epic | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | passive | 2 | epic | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | passive | 3 | epic | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | passive | 4 | epic | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 1 | rare | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 1 | epic | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 2 | rare | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 2 | epic | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 3 | rare | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 3 | epic | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 4 | rare | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| form | reaction | 4 | epic | 0 | 0 | keyword_not_composable 200 | 0.0 | 0.0 |
| combo_point | active | 1 | common | 0 | 0 | keyword_exhausted 200 | 1.2 | 1.0 |
| combo_point | active | 1 | rare | 200 | 129 |  | 72.5 | 32.2 |
| combo_point | active | 1 | epic | 200 | 171 |  | 89.3 | 54.9 |
| combo_point | active | 2 | common | 0 | 0 | keyword_exhausted 200 | 1.4 | 1.1 |
| combo_point | active | 2 | rare | 200 | 135 |  | 43.3 | 27.4 |
| combo_point | active | 2 | epic | 200 | 164 |  | 47.6 | 28.7 |
| combo_point | active | 3 | common | 0 | 0 | keyword_exhausted 200 | 1.3 | 1.1 |
| combo_point | active | 3 | rare | 200 | 131 |  | 42.2 | 26.8 |
| combo_point | active | 3 | epic | 200 | 166 |  | 42.4 | 28.8 |
| combo_point | active | 4 | common | 0 | 0 | keyword_exhausted 200 | 1.5 | 1.0 |
| combo_point | active | 4 | rare | 200 | 130 |  | 41.5 | 26.9 |
| combo_point | active | 4 | epic | 200 | 167 |  | 51.6 | 30.3 |
| combo_point | passive | 1 | epic | 200 | 115 |  | 10.8 | 6.2 |
| combo_point | passive | 2 | epic | 200 | 129 |  | 9.4 | 6.0 |
| combo_point | passive | 3 | epic | 200 | 124 |  | 13.2 | 8.6 |
| combo_point | passive | 4 | epic | 200 | 126 |  | 11.6 | 8.2 |
| combo_point | reaction | 1 | rare | 200 | 117 |  | 11.8 | 8.1 |
| combo_point | reaction | 1 | epic | 200 | 117 |  | 12.0 | 9.0 |
| combo_point | reaction | 2 | rare | 200 | 112 |  | 14.2 | 11.6 |
| combo_point | reaction | 2 | epic | 200 | 112 |  | 12.4 | 8.7 |
| combo_point | reaction | 3 | rare | 200 | 90 |  | 13.1 | 10.2 |
| combo_point | reaction | 3 | epic | 200 | 90 |  | 13.7 | 10.4 |
| combo_point | reaction | 4 | rare | 200 | 72 |  | 11.7 | 8.9 |
| combo_point | reaction | 4 | epic | 200 | 72 |  | 14.7 | 10.5 |
| fury | active | 1 | common | 0 | 0 | keyword_exhausted 200 | 1.1 | 1.0 |
| fury | active | 1 | rare | 200 | 130 |  | 71.1 | 42.6 |
| fury | active | 1 | epic | 200 | 160 |  | 81.5 | 41.8 |
| fury | active | 2 | common | 0 | 0 | keyword_exhausted 200 | 1.2 | 1.0 |
| fury | active | 2 | rare | 200 | 124 |  | 43.1 | 29.8 |
| fury | active | 2 | epic | 200 | 165 |  | 50.1 | 30.6 |
| fury | active | 3 | common | 0 | 0 | keyword_exhausted 200 | 1.2 | 1.0 |
| fury | active | 3 | rare | 200 | 132 |  | 36.2 | 24.8 |
| fury | active | 3 | epic | 200 | 169 |  | 36.1 | 25.6 |
| fury | active | 4 | common | 0 | 0 | keyword_exhausted 200 | 1.1 | 1.0 |
| fury | active | 4 | rare | 200 | 142 |  | 35.8 | 23.9 |
| fury | active | 4 | epic | 200 | 171 |  | 35.7 | 25.0 |
| fury | passive | 1 | epic | 200 | 115 |  | 6.9 | 4.9 |
| fury | passive | 2 | epic | 200 | 129 |  | 7.7 | 5.5 |
| fury | passive | 3 | epic | 200 | 124 |  | 8.3 | 5.9 |
| fury | passive | 4 | epic | 200 | 126 |  | 9.0 | 6.7 |
| fury | reaction | 1 | rare | 200 | 117 |  | 8.1 | 6.7 |
| fury | reaction | 1 | epic | 200 | 117 |  | 9.1 | 7.0 |
| fury | reaction | 2 | rare | 200 | 112 |  | 9.9 | 7.6 |
| fury | reaction | 2 | epic | 200 | 112 |  | 10.0 | 8.2 |
| fury | reaction | 3 | rare | 200 | 90 |  | 10.6 | 8.2 |
| fury | reaction | 3 | epic | 200 | 90 |  | 10.5 | 8.8 |
| fury | reaction | 4 | rare | 200 | 72 |  | 10.9 | 8.1 |
| fury | reaction | 4 | epic | 200 | 72 |  | 10.8 | 8.1 |
| focus | active | 1 | common | 0 | 0 | keyword_exhausted 200 | 1.2 | 1.0 |
| focus | active | 1 | rare | 200 | 140 |  | 54.2 | 31.9 |
| focus | active | 1 | epic | 200 | 169 |  | 55.5 | 30.5 |
| focus | active | 2 | common | 0 | 0 | keyword_exhausted 200 | 1.1 | 1.0 |
| focus | active | 2 | rare | 200 | 140 |  | 30.1 | 19.6 |
| focus | active | 2 | epic | 200 | 177 |  | 35.0 | 22.3 |
| focus | active | 3 | common | 0 | 0 | keyword_exhausted 200 | 1.1 | 0.9 |
| focus | active | 3 | rare | 200 | 136 |  | 28.6 | 18.4 |
| focus | active | 3 | epic | 200 | 171 |  | 33.1 | 21.4 |
| focus | active | 4 | common | 0 | 0 | keyword_exhausted 200 | 1.0 | 0.9 |
| focus | active | 4 | rare | 200 | 133 |  | 30.2 | 18.7 |
| focus | active | 4 | epic | 200 | 167 |  | 34.8 | 21.4 |
| focus | passive | 1 | epic | 200 | 124 |  | 7.1 | 5.2 |
| focus | passive | 2 | epic | 200 | 119 |  | 7.8 | 5.7 |
| focus | passive | 3 | epic | 200 | 113 |  | 8.0 | 6.0 |
| focus | passive | 4 | epic | 200 | 101 |  | 8.0 | 6.1 |
| focus | reaction | 1 | rare | 200 | 117 |  | 7.4 | 6.0 |
| focus | reaction | 1 | epic | 200 | 117 |  | 7.1 | 6.0 |
| focus | reaction | 2 | rare | 200 | 112 |  | 8.9 | 7.2 |
| focus | reaction | 2 | epic | 200 | 112 |  | 8.8 | 7.0 |
| focus | reaction | 3 | rare | 200 | 90 |  | 9.7 | 8.0 |
| focus | reaction | 3 | epic | 200 | 90 |  | 9.9 | 8.4 |
| focus | reaction | 4 | rare | 200 | 72 |  | 10.5 | 8.2 |
| focus | reaction | 4 | epic | 200 | 72 |  | 10.0 | 8.3 |
| ki | active | 1 | common | 0 | 0 | keyword_exhausted 200 | 1.0 | 0.9 |
| ki | active | 1 | rare | 200 | 122 |  | 57.7 | 25.2 |
| ki | active | 1 | epic | 200 | 163 |  | 72.6 | 38.2 |
| ki | active | 2 | common | 0 | 0 | keyword_exhausted 200 | 1.0 | 0.9 |
| ki | active | 2 | rare | 200 | 138 |  | 32.8 | 18.9 |
| ki | active | 2 | epic | 200 | 172 |  | 42.7 | 23.4 |
| ki | active | 3 | common | 0 | 0 | keyword_exhausted 200 | 1.1 | 1.0 |
| ki | active | 3 | rare | 200 | 127 |  | 35.2 | 22.6 |
| ki | active | 3 | epic | 200 | 174 |  | 39.8 | 22.8 |
| ki | active | 4 | common | 0 | 0 | keyword_exhausted 200 | 1.4 | 1.1 |
| ki | active | 4 | rare | 200 | 123 |  | 34.9 | 22.4 |
| ki | active | 4 | epic | 200 | 175 |  | 36.6 | 22.5 |
| ki | passive | 1 | epic | 200 | 115 |  | 7.9 | 5.6 |
| ki | passive | 2 | epic | 200 | 129 |  | 9.1 | 6.4 |
| ki | passive | 3 | epic | 200 | 124 |  | 9.2 | 6.2 |
| ki | passive | 4 | epic | 200 | 126 |  | 8.5 | 6.3 |
| ki | reaction | 1 | rare | 200 | 117 |  | 7.3 | 5.8 |
| ki | reaction | 1 | epic | 200 | 117 |  | 7.3 | 6.0 |
| ki | reaction | 2 | rare | 200 | 112 |  | 8.4 | 6.8 |
| ki | reaction | 2 | epic | 200 | 112 |  | 8.5 | 6.8 |
| ki | reaction | 3 | rare | 200 | 90 |  | 9.6 | 7.7 |
| ki | reaction | 3 | epic | 200 | 90 |  | 9.5 | 7.5 |
| ki | reaction | 4 | rare | 200 | 72 |  | 9.8 | 7.3 |
| ki | reaction | 4 | epic | 200 | 72 |  | 9.5 | 7.2 |
