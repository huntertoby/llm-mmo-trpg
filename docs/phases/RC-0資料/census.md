# 組合器配方盤點摘要

格式 `recipe-census/1`；種子 0～199；薄格門檻：不同設計 < 12。由 `scripts/recipe_census.py` 產生，計時欄每次不同。

- 格子 612：正常 252、薄 14、空 142、設計上不存在 204（骨架稀有度下限：被動至少 epic、反應至少 rare）
- 其中遊戲會出題（出題檢查通過）的：空 102、薄 14；其餘空格是規則上就沒有專屬來源（遊戲不出這題）

## 依關鍵字（不含設計上不存在；「會出題」＝出題檢查通過的空格與薄格）

| 關鍵字 | 空 | 薄 | 正常 | 會出題的空 | 會出題的薄 |
|---|---|---|---|---|---|
| - | 0 | 0 | 24 | 0 | 0 |
| ignite | 0 | 0 | 24 | 0 | 0 |
| wet | 12 | 4 | 8 | 8 | 4 |
| charged | 0 | 2 | 22 | 0 | 2 |
| frozen | 0 | 0 | 24 | 0 | 0 |
| prone | 4 | 2 | 18 | 0 | 2 |
| collision | 4 | 0 | 20 | 0 | 0 |
| marked | 0 | 0 | 24 | 0 | 0 |
| high_ground | 16 | 0 | 8 | 12 | 0 |
| concealed | 0 | 0 | 24 | 0 | 0 |
| summon | 18 | 6 | 0 | 14 | 6 |
| poisoned | 0 | 0 | 24 | 0 | 0 |
| form | 24 | 0 | 0 | 20 | 0 |
| combo_point | 16 | 0 | 8 | 12 | 0 |
| fury | 16 | 0 | 8 | 12 | 0 |
| focus | 16 | 0 | 8 | 12 | 0 |
| ki | 16 | 0 | 8 | 12 | 0 |

## 依種類

| 種類 | 空 | 薄 | 正常 | 會出題的空 | 會出題的薄 |
|---|---|---|---|---|---|
| active | 50 | 6 | 148 | 10 | 6 |
| passive | 28 | 6 | 34 | 28 | 6 |
| reaction | 64 | 2 | 70 | 64 | 2 |

## 空格與薄格（依玩家遇到的頻率排序）

| 關鍵字 | 種類 | 階 | 稀有度 | 狀態 | 會出題 | 合法 | 設計 | 主要原因 | 判斷 | 中位 ms |
|---|---|---|---|---|---|---|---|---|---|---|
| collision | active | 2 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 614.7 |
| combo_point | active | 2 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| focus | active | 2 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| form | active | 2 | common | empty | 否 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 2 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| fury | active | 2 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| high_ground | active | 2 | common | empty | 否 | 0 | 0 | not_fit.keyword 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 11.2 |
| ki | active | 2 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| prone | active | 2 | common | empty | 否 | 0 | 0 | not_fit.keyword 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 10.5 |
| summon | active | 2 | common | empty | 否 | 0 | 0 | not_fit.keyword 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 20.0 |
| summon | active | 2 | rare | thin | 是 | 29 | 8 | not_fit.keyword 104 | 配方稀少：偶爾帶到專屬關鍵字 | 29.9 |
| wet | active | 2 | common | empty | 否 | 0 | 0 | not_fit.keyword 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 14.8 |
| collision | active | 1 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 569.5 |
| collision | active | 3 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 733.2 |
| combo_point | active | 1 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| combo_point | active | 3 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| focus | active | 1 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| focus | active | 3 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| form | active | 1 | common | empty | 否 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 1 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 3 | common | empty | 否 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 3 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| fury | active | 1 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| fury | active | 3 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| high_ground | active | 1 | common | empty | 否 | 0 | 0 | not_fit.keyword 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 10.9 |
| high_ground | active | 3 | common | empty | 否 | 0 | 0 | not_fit.keyword 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 12.8 |
| ki | active | 1 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| ki | active | 3 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| prone | active | 1 | common | empty | 否 | 0 | 0 | not_fit.keyword 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 9.1 |
| prone | active | 3 | common | empty | 否 | 0 | 0 | not_fit.keyword 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 11.9 |
| summon | active | 1 | common | empty | 否 | 0 | 0 | not_fit.keyword 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 19.1 |
| summon | active | 1 | rare | empty | 是 | 0 | 0 | not_fit.keyword 127 | 只帶到通用規則：組合器認、退回路徑不收 | 74.4 |
| summon | active | 3 | common | empty | 否 | 0 | 0 | not_fit.keyword 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 21.6 |
| summon | active | 3 | rare | thin | 是 | 26 | 7 | not_fit.keyword 94 | 配方稀少：偶爾帶到專屬關鍵字 | 23.9 |
| wet | active | 1 | common | empty | 否 | 0 | 0 | not_fit.keyword 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 12.3 |
| wet | active | 3 | common | empty | 否 | 0 | 0 | not_fit.keyword 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 17.4 |
| form | active | 2 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | active | 2 | epic | thin | 是 | 37 | 8 | not_fit.keyword 89 | 配方稀少：偶爾帶到專屬關鍵字 | 32.0 |
| form | active | 1 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 3 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | active | 1 | epic | empty | 是 | 0 | 0 | not_fit.keyword 128 | 只帶到通用規則：組合器認、退回路徑不收 | 94.7 |
| summon | active | 3 | epic | thin | 是 | 27 | 8 | not_fit.keyword 87 | 配方稀少：偶爾帶到專屬關鍵字 | 25.3 |
| combo_point | passive | 2 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 367.9 |
| focus | passive | 2 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 372.4 |
| form | passive | 2 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| fury | passive | 2 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 377.5 |
| high_ground | passive | 2 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 382.1 |
| ki | passive | 2 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 365.6 |
| prone | passive | 2 | epic | thin | 是 | 182 | 8 | keyword_exhausted 18 | 配方稀少：偶爾帶到專屬關鍵字 | 100.8 |
| summon | passive | 2 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 394.0 |
| wet | passive | 2 | epic | thin | 是 | 4 | 4 | not_fit.keyword 196 | 只帶到通用規則：組合器認、退回路徑不收 | 3.6 |
| combo_point | reaction | 2 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 417.6 |
| focus | reaction | 2 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 419.6 |
| form | reaction | 2 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| fury | reaction | 2 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 415.4 |
| high_ground | reaction | 2 | rare | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 28.5 |
| ki | reaction | 2 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 401.5 |
| summon | reaction | 2 | rare | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 3.4 |
| wet | reaction | 2 | rare | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 10.2 |
| combo_point | passive | 1 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 356.1 |
| combo_point | passive | 3 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 406.5 |
| focus | passive | 1 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 358.8 |
| focus | passive | 3 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 408.3 |
| form | passive | 1 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | passive | 3 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| fury | passive | 1 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 363.3 |
| fury | passive | 3 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 417.5 |
| high_ground | passive | 1 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 365.4 |
| high_ground | passive | 3 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 423.5 |
| ki | passive | 1 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 363.9 |
| ki | passive | 3 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 409.1 |
| summon | passive | 1 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 381.4 |
| summon | passive | 3 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 438.0 |
| wet | passive | 1 | epic | thin | 是 | 6 | 6 | not_fit.keyword 194 | 只帶到通用規則：組合器認、退回路徑不收 | 3.9 |
| wet | passive | 3 | epic | thin | 是 | 3 | 3 | not_fit.keyword 197 | 只帶到通用規則：組合器認、退回路徑不收 | 4.2 |
| collision | active | 4 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 912.2 |
| combo_point | active | 4 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| focus | active | 4 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| form | active | 4 | common | empty | 否 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 4 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| fury | active | 4 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| high_ground | active | 4 | common | empty | 否 | 0 | 0 | not_fit.keyword 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 15.0 |
| ki | active | 4 | common | empty | 否 | 0 | 0 | keyword_exhausted 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 0.9 |
| prone | active | 4 | common | empty | 否 | 0 | 0 | not_fit.keyword 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 14.1 |
| summon | active | 4 | common | empty | 否 | 0 | 0 | not_fit.keyword 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 27.8 |
| summon | active | 4 | rare | thin | 是 | 25 | 7 | not_fit.keyword 93 | 配方稀少：偶爾帶到專屬關鍵字 | 30.2 |
| wet | active | 4 | common | empty | 否 | 0 | 0 | not_fit.keyword 200 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 17.5 |
| charged | reaction | 1 | rare | thin | 是 | 189 | 10 | keyword_exhausted 11 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 66.3 |
| combo_point | reaction | 1 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 346.1 |
| combo_point | reaction | 3 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 464.5 |
| focus | reaction | 1 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 354.4 |
| focus | reaction | 3 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 456.7 |
| form | reaction | 1 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | reaction | 3 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| fury | reaction | 1 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 343.5 |
| fury | reaction | 3 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 463.3 |
| high_ground | reaction | 1 | rare | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 26.3 |
| high_ground | reaction | 3 | rare | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 29.7 |
| ki | reaction | 1 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 348.3 |
| ki | reaction | 3 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 425.2 |
| summon | reaction | 1 | rare | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 3.1 |
| summon | reaction | 3 | rare | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 3.3 |
| wet | reaction | 1 | rare | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 9.6 |
| wet | reaction | 3 | rare | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 11.3 |
| combo_point | reaction | 2 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 417.3 |
| focus | reaction | 2 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 417.4 |
| form | reaction | 2 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| fury | reaction | 2 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 421.1 |
| high_ground | reaction | 2 | epic | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 29.7 |
| ki | reaction | 2 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 402.8 |
| summon | reaction | 2 | epic | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 3.3 |
| wet | reaction | 2 | epic | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 10.2 |
| form | active | 4 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | active | 4 | epic | thin | 是 | 31 | 8 | not_fit.kind(reaction) 86 | 配方稀少：偶爾帶到專屬關鍵字 | 30.6 |
| charged | reaction | 1 | epic | thin | 是 | 189 | 10 | keyword_exhausted 11 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 64.9 |
| combo_point | reaction | 1 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 348.2 |
| combo_point | reaction | 3 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 464.1 |
| focus | reaction | 1 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 354.0 |
| focus | reaction | 3 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 460.1 |
| form | reaction | 1 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| form | reaction | 3 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| fury | reaction | 1 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 342.9 |
| fury | reaction | 3 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 467.8 |
| high_ground | reaction | 1 | epic | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 26.3 |
| high_ground | reaction | 3 | epic | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 28.6 |
| ki | reaction | 1 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 349.3 |
| ki | reaction | 3 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 421.8 |
| summon | reaction | 1 | epic | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 3.1 |
| summon | reaction | 3 | epic | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 3.4 |
| wet | reaction | 1 | epic | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 9.4 |
| wet | reaction | 3 | epic | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 10.5 |
| combo_point | passive | 4 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 432.8 |
| focus | passive | 4 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 445.7 |
| form | passive | 4 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| fury | passive | 4 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 437.2 |
| high_ground | passive | 4 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 444.3 |
| ki | passive | 4 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 429.5 |
| prone | passive | 4 | epic | thin | 是 | 197 | 8 | keyword_exhausted 3 | 配方稀少：偶爾帶到專屬關鍵字 | 72.9 |
| summon | passive | 4 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 460.0 |
| wet | passive | 4 | epic | thin | 是 | 1 | 1 | not_fit.keyword 199 | 只帶到通用規則：組合器認、退回路徑不收 | 4.4 |
| combo_point | reaction | 4 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 488.4 |
| focus | reaction | 4 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 479.8 |
| form | reaction | 4 | rare | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| fury | reaction | 4 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 492.2 |
| high_ground | reaction | 4 | rare | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 28.0 |
| ki | reaction | 4 | rare | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 431.9 |
| summon | reaction | 4 | rare | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 3.4 |
| wet | reaction | 4 | rare | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 11.0 |
| combo_point | reaction | 4 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 491.7 |
| focus | reaction | 4 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 486.8 |
| form | reaction | 4 | epic | empty | 是 | 0 | 0 | keyword_not_composable 200 | 內容標記組合器不做（composable: false） | 0.0 |
| fury | reaction | 4 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 489.6 |
| high_ground | reaction | 4 | epic | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 27.9 |
| ki | reaction | 4 | epic | empty | 是 | 0 | 0 | keyword_exhausted 200 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 421.6 |
| summon | reaction | 4 | epic | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 3.9 |
| wet | reaction | 4 | epic | empty | 是 | 0 | 0 | not_fit.keyword 200 | 只帶到通用規則：組合器認、退回路徑不收 | 10.5 |

## 全部格子

| 關鍵字 | 種類 | 階 | 稀有度 | 合法 | 設計 | 主要原因 | 平均 ms | 中位 ms |
|---|---|---|---|---|---|---|---|---|
| - | active | 1 | common | 200 | 164 |  | 2.7 | 2.5 |
| - | active | 1 | rare | 181 | 166 | not_fit.kind(reaction) 19 | 18.1 | 3.5 |
| - | active | 1 | epic | 129 | 119 | not_fit.kind(passive) 48 | 14.7 | 3.1 |
| - | active | 2 | common | 200 | 162 |  | 2.8 | 2.5 |
| - | active | 2 | rare | 167 | 157 | not_fit.kind(reaction) 19 | 7.1 | 3.3 |
| - | active | 2 | epic | 117 | 116 | not_fit.kind(passive) 48 | 5.8 | 2.8 |
| - | active | 3 | common | 200 | 162 |  | 3.2 | 2.5 |
| - | active | 3 | rare | 167 | 157 | not_fit.kind(reaction) 19 | 7.2 | 3.4 |
| - | active | 3 | epic | 117 | 116 | not_fit.kind(passive) 48 | 5.1 | 3.1 |
| - | active | 4 | common | 200 | 159 |  | 4.1 | 2.9 |
| - | active | 4 | rare | 167 | 155 | not_fit.kind(reaction) 19 | 6.3 | 3.6 |
| - | active | 4 | epic | 117 | 116 | not_fit.kind(passive) 48 | 5.3 | 2.9 |
| - | passive | 1 | epic | 200 | 119 |  | 2.0 | 1.9 |
| - | passive | 2 | epic | 200 | 120 |  | 2.1 | 2.0 |
| - | passive | 3 | epic | 200 | 116 |  | 2.2 | 2.1 |
| - | passive | 4 | epic | 200 | 111 |  | 2.4 | 2.4 |
| - | reaction | 1 | rare | 200 | 73 |  | 2.1 | 2.0 |
| - | reaction | 1 | epic | 200 | 73 |  | 2.1 | 2.0 |
| - | reaction | 2 | rare | 200 | 63 |  | 2.3 | 2.2 |
| - | reaction | 2 | epic | 200 | 63 |  | 2.3 | 2.2 |
| - | reaction | 3 | rare | 200 | 54 |  | 2.5 | 2.4 |
| - | reaction | 3 | epic | 200 | 54 |  | 2.5 | 2.4 |
| - | reaction | 4 | rare | 200 | 52 |  | 2.7 | 2.6 |
| - | reaction | 4 | epic | 200 | 52 |  | 2.8 | 2.6 |
| ignite | active | 1 | common | 200 | 97 |  | 19.4 | 13.7 |
| ignite | active | 1 | rare | 177 | 144 | not_fit.keyword 21 | 148.0 | 63.3 |
| ignite | active | 1 | epic | 147 | 133 | not_fit.keyword 24 | 119.0 | 44.7 |
| ignite | active | 2 | common | 200 | 101 |  | 20.6 | 14.3 |
| ignite | active | 2 | rare | 157 | 134 | not_fit.keyword 41 | 52.3 | 28.5 |
| ignite | active | 2 | epic | 139 | 123 | not_fit.keyword 32 | 34.7 | 17.0 |
| ignite | active | 3 | common | 200 | 96 |  | 23.9 | 16.1 |
| ignite | active | 3 | rare | 159 | 132 | not_fit.keyword 40 | 42.3 | 20.7 |
| ignite | active | 3 | epic | 147 | 133 | not_fit.kind(passive) 26 | 33.0 | 17.0 |
| ignite | active | 4 | common | 200 | 100 |  | 29.9 | 18.8 |
| ignite | active | 4 | rare | 160 | 132 | not_fit.keyword 38 | 52.9 | 24.7 |
| ignite | active | 4 | epic | 140 | 126 | not_fit.keyword 31 | 39.3 | 18.8 |
| ignite | passive | 1 | epic | 200 | 68 |  | 17.7 | 12.2 |
| ignite | passive | 2 | epic | 200 | 67 |  | 16.4 | 12.0 |
| ignite | passive | 3 | epic | 200 | 63 |  | 17.3 | 13.0 |
| ignite | passive | 4 | epic | 200 | 62 |  | 19.9 | 13.9 |
| ignite | reaction | 1 | rare | 200 | 54 |  | 36.4 | 24.8 |
| ignite | reaction | 1 | epic | 200 | 54 |  | 36.5 | 25.9 |
| ignite | reaction | 2 | rare | 200 | 55 |  | 47.6 | 32.7 |
| ignite | reaction | 2 | epic | 200 | 55 |  | 47.5 | 34.2 |
| ignite | reaction | 3 | rare | 200 | 52 |  | 51.2 | 36.2 |
| ignite | reaction | 3 | epic | 200 | 52 |  | 50.8 | 37.1 |
| ignite | reaction | 4 | rare | 200 | 34 |  | 87.5 | 53.9 |
| ignite | reaction | 4 | epic | 200 | 34 |  | 87.4 | 54.6 |
| wet | active | 1 | common | 0 | 0 | not_fit.keyword 200 | 18.2 | 12.3 |
| wet | active | 1 | rare | 48 | 46 | not_fit.keyword 127 | 257.9 | 155.4 |
| wet | active | 1 | epic | 30 | 28 | not_fit.kind(passive) 96 | 135.3 | 57.1 |
| wet | active | 2 | common | 0 | 0 | not_fit.keyword 200 | 20.4 | 14.8 |
| wet | active | 2 | rare | 52 | 52 | not_fit.keyword 120 | 99.9 | 66.0 |
| wet | active | 2 | epic | 23 | 23 | not_fit.kind(passive) 106 | 47.9 | 24.8 |
| wet | active | 3 | common | 0 | 0 | not_fit.keyword 200 | 23.1 | 17.4 |
| wet | active | 3 | rare | 49 | 49 | not_fit.keyword 123 | 92.5 | 52.0 |
| wet | active | 3 | epic | 28 | 27 | not_fit.kind(passive) 100 | 51.2 | 23.5 |
| wet | active | 4 | common | 0 | 0 | not_fit.keyword 200 | 26.5 | 17.5 |
| wet | active | 4 | rare | 40 | 40 | not_fit.keyword 127 | 94.5 | 61.4 |
| wet | active | 4 | epic | 30 | 30 | not_fit.kind(passive) 98 | 51.7 | 25.8 |
| wet | passive | 1 | epic | 6 | 6 | not_fit.keyword 194 | 5.3 | 3.9 |
| wet | passive | 2 | epic | 4 | 4 | not_fit.keyword 196 | 4.8 | 3.6 |
| wet | passive | 3 | epic | 3 | 3 | not_fit.keyword 197 | 5.5 | 4.2 |
| wet | passive | 4 | epic | 1 | 1 | not_fit.keyword 199 | 5.6 | 4.4 |
| wet | reaction | 1 | rare | 0 | 0 | not_fit.keyword 200 | 12.2 | 9.6 |
| wet | reaction | 1 | epic | 0 | 0 | not_fit.keyword 200 | 12.3 | 9.4 |
| wet | reaction | 2 | rare | 0 | 0 | not_fit.keyword 200 | 13.5 | 10.2 |
| wet | reaction | 2 | epic | 0 | 0 | not_fit.keyword 200 | 14.1 | 10.2 |
| wet | reaction | 3 | rare | 0 | 0 | not_fit.keyword 200 | 13.6 | 11.3 |
| wet | reaction | 3 | epic | 0 | 0 | not_fit.keyword 200 | 13.7 | 10.5 |
| wet | reaction | 4 | rare | 0 | 0 | not_fit.keyword 200 | 13.9 | 11.0 |
| wet | reaction | 4 | epic | 0 | 0 | not_fit.keyword 200 | 13.9 | 10.5 |
| charged | active | 1 | common | 200 | 54 |  | 44.4 | 31.2 |
| charged | active | 1 | rare | 151 | 108 | not_fit.keyword 43 | 243.7 | 154.5 |
| charged | active | 1 | epic | 143 | 112 | not_fit.keyword 35 | 212.9 | 145.5 |
| charged | active | 2 | common | 200 | 58 |  | 46.5 | 34.3 |
| charged | active | 2 | rare | 125 | 90 | not_fit.keyword 69 | 80.1 | 35.5 |
| charged | active | 2 | epic | 125 | 107 | not_fit.keyword 52 | 67.3 | 40.5 |
| charged | active | 3 | common | 200 | 61 |  | 51.6 | 35.0 |
| charged | active | 3 | rare | 160 | 122 | not_fit.keyword 36 | 37.4 | 16.6 |
| charged | active | 3 | epic | 146 | 125 | not_fit.keyword 32 | 43.3 | 23.8 |
| charged | active | 4 | common | 200 | 58 |  | 59.4 | 44.0 |
| charged | active | 4 | rare | 158 | 121 | not_fit.keyword 37 | 43.1 | 21.4 |
| charged | active | 4 | epic | 154 | 132 | not_fit.keyword 25 | 50.3 | 26.6 |
| charged | passive | 1 | epic | 200 | 12 |  | 41.6 | 28.8 |
| charged | passive | 2 | epic | 200 | 14 |  | 34.1 | 24.6 |
| charged | passive | 3 | epic | 200 | 14 |  | 31.0 | 22.6 |
| charged | passive | 4 | epic | 200 | 14 |  | 34.9 | 25.2 |
| charged | reaction | 1 | rare | 189 | 10 | keyword_exhausted 11 | 97.4 | 66.3 |
| charged | reaction | 1 | epic | 189 | 10 | keyword_exhausted 11 | 97.0 | 64.9 |
| charged | reaction | 2 | rare | 192 | 13 | keyword_exhausted 8 | 110.2 | 77.6 |
| charged | reaction | 2 | epic | 192 | 13 | keyword_exhausted 8 | 109.9 | 78.2 |
| charged | reaction | 3 | rare | 195 | 13 | keyword_exhausted 5 | 107.7 | 74.4 |
| charged | reaction | 3 | epic | 195 | 13 | keyword_exhausted 5 | 107.1 | 75.2 |
| charged | reaction | 4 | rare | 194 | 13 | keyword_exhausted 6 | 113.8 | 77.9 |
| charged | reaction | 4 | epic | 194 | 13 | keyword_exhausted 6 | 114.4 | 77.2 |
| frozen | active | 1 | common | 200 | 54 |  | 40.8 | 27.9 |
| frozen | active | 1 | rare | 165 | 121 | not_fit.keyword 29 | 186.0 | 84.7 |
| frozen | active | 1 | epic | 154 | 124 | not_fit.keyword 26 | 178.3 | 100.9 |
| frozen | active | 2 | common | 200 | 54 |  | 42.5 | 31.1 |
| frozen | active | 2 | rare | 151 | 125 | not_fit.keyword 41 | 66.4 | 27.3 |
| frozen | active | 2 | epic | 139 | 118 | not_fit.keyword 43 | 60.1 | 36.9 |
| frozen | active | 3 | common | 200 | 54 |  | 47.1 | 33.9 |
| frozen | active | 3 | rare | 134 | 113 | not_fit.keyword 61 | 58.8 | 29.1 |
| frozen | active | 3 | epic | 126 | 114 | not_fit.keyword 52 | 57.7 | 32.1 |
| frozen | active | 4 | common | 200 | 55 |  | 61.3 | 38.0 |
| frozen | active | 4 | rare | 144 | 124 | not_fit.keyword 54 | 74.9 | 29.5 |
| frozen | active | 4 | epic | 131 | 118 | not_fit.keyword 46 | 65.3 | 36.4 |
| frozen | passive | 1 | epic | 200 | 14 |  | 40.5 | 26.6 |
| frozen | passive | 2 | epic | 200 | 14 |  | 38.0 | 22.4 |
| frozen | passive | 3 | epic | 200 | 14 |  | 38.2 | 22.9 |
| frozen | passive | 4 | epic | 200 | 14 |  | 40.0 | 25.1 |
| frozen | reaction | 1 | rare | 198 | 28 | keyword_exhausted 2 | 61.9 | 46.1 |
| frozen | reaction | 1 | epic | 198 | 28 | keyword_exhausted 2 | 63.2 | 45.0 |
| frozen | reaction | 2 | rare | 200 | 59 |  | 64.1 | 45.5 |
| frozen | reaction | 2 | epic | 200 | 59 |  | 64.5 | 47.1 |
| frozen | reaction | 3 | rare | 200 | 45 |  | 85.6 | 61.3 |
| frozen | reaction | 3 | epic | 200 | 45 |  | 85.6 | 59.9 |
| frozen | reaction | 4 | rare | 200 | 34 |  | 94.7 | 67.6 |
| frozen | reaction | 4 | epic | 200 | 34 |  | 95.2 | 67.2 |
| prone | active | 1 | common | 0 | 0 | not_fit.keyword 200 | 13.1 | 9.1 |
| prone | active | 1 | rare | 91 | 79 | not_fit.keyword 104 | 62.7 | 19.1 |
| prone | active | 1 | epic | 105 | 97 | not_fit.keyword 89 | 56.1 | 16.5 |
| prone | active | 2 | common | 0 | 0 | not_fit.keyword 200 | 15.1 | 10.5 |
| prone | active | 2 | rare | 73 | 68 | not_fit.keyword 120 | 34.6 | 14.1 |
| prone | active | 2 | epic | 100 | 90 | not_fit.keyword 93 | 30.6 | 13.7 |
| prone | active | 3 | common | 0 | 0 | not_fit.keyword 200 | 15.9 | 11.9 |
| prone | active | 3 | rare | 76 | 74 | not_fit.keyword 116 | 31.3 | 13.7 |
| prone | active | 3 | epic | 88 | 79 | not_fit.keyword 106 | 29.3 | 11.8 |
| prone | active | 4 | common | 0 | 0 | not_fit.keyword 200 | 20.6 | 14.1 |
| prone | active | 4 | rare | 75 | 71 | not_fit.keyword 119 | 34.4 | 13.9 |
| prone | active | 4 | epic | 98 | 86 | not_fit.keyword 98 | 31.0 | 13.4 |
| prone | passive | 1 | epic | 146 | 16 | keyword_exhausted 54 | 209.0 | 205.3 |
| prone | passive | 2 | epic | 182 | 8 | keyword_exhausted 18 | 149.5 | 100.8 |
| prone | passive | 3 | epic | 199 | 15 | keyword_exhausted 1 | 103.1 | 65.3 |
| prone | passive | 4 | epic | 197 | 8 | keyword_exhausted 3 | 118.4 | 72.9 |
| prone | reaction | 1 | rare | 116 | 43 | not_fit.keyword 84 | 13.2 | 9.0 |
| prone | reaction | 1 | epic | 116 | 43 | not_fit.keyword 84 | 13.3 | 8.8 |
| prone | reaction | 2 | rare | 85 | 39 | not_fit.keyword 115 | 17.8 | 13.6 |
| prone | reaction | 2 | epic | 85 | 39 | not_fit.keyword 115 | 17.8 | 13.5 |
| prone | reaction | 3 | rare | 71 | 32 | not_fit.keyword 129 | 23.7 | 16.2 |
| prone | reaction | 3 | epic | 71 | 32 | not_fit.keyword 129 | 22.9 | 15.6 |
| prone | reaction | 4 | rare | 57 | 20 | not_fit.keyword 143 | 25.5 | 17.3 |
| prone | reaction | 4 | epic | 57 | 20 | not_fit.keyword 143 | 25.0 | 16.0 |
| collision | active | 1 | common | 0 | 0 | keyword_exhausted 200 | 570.0 | 569.5 |
| collision | active | 1 | rare | 171 | 142 | not_fit.keyword 21 | 63.2 | 20.4 |
| collision | active | 1 | epic | 156 | 129 | not_fit.keyword 19 | 52.9 | 14.9 |
| collision | active | 2 | common | 0 | 0 | keyword_exhausted 200 | 619.0 | 614.7 |
| collision | active | 2 | rare | 167 | 146 | not_fit.keyword 25 | 37.9 | 16.9 |
| collision | active | 2 | epic | 168 | 127 | not_fit.kind(modifier) 12 | 24.2 | 11.3 |
| collision | active | 3 | common | 0 | 0 | keyword_exhausted 200 | 738.3 | 733.2 |
| collision | active | 3 | rare | 173 | 153 | not_fit.keyword 21 | 34.3 | 16.1 |
| collision | active | 3 | epic | 161 | 131 | not_fit.kind(modifier) 13 | 23.6 | 11.0 |
| collision | active | 4 | common | 0 | 0 | keyword_exhausted 200 | 912.8 | 912.2 |
| collision | active | 4 | rare | 171 | 152 | not_fit.keyword 23 | 39.9 | 20.3 |
| collision | active | 4 | epic | 150 | 124 | not_fit.keyword 18 | 26.2 | 12.5 |
| collision | passive | 1 | epic | 200 | 88 |  | 18.6 | 13.3 |
| collision | passive | 2 | epic | 200 | 104 |  | 17.7 | 12.0 |
| collision | passive | 3 | epic | 200 | 108 |  | 17.0 | 12.0 |
| collision | passive | 4 | epic | 200 | 113 |  | 16.0 | 11.0 |
| collision | reaction | 1 | rare | 200 | 100 |  | 12.4 | 8.1 |
| collision | reaction | 1 | epic | 200 | 100 |  | 12.7 | 8.2 |
| collision | reaction | 2 | rare | 200 | 111 |  | 17.3 | 12.3 |
| collision | reaction | 2 | epic | 200 | 111 |  | 17.3 | 11.8 |
| collision | reaction | 3 | rare | 200 | 97 |  | 23.0 | 15.0 |
| collision | reaction | 3 | epic | 200 | 97 |  | 22.6 | 14.6 |
| collision | reaction | 4 | rare | 200 | 83 |  | 30.8 | 19.7 |
| collision | reaction | 4 | epic | 200 | 83 |  | 31.3 | 19.2 |
| marked | active | 1 | common | 200 | 80 |  | 30.0 | 22.1 |
| marked | active | 1 | rare | 194 | 169 | not_fit.kind(reaction) 6 | 186.5 | 90.0 |
| marked | active | 1 | epic | 185 | 164 | not_fit.kind(passive) 9 | 224.3 | 142.6 |
| marked | active | 2 | common | 200 | 83 |  | 32.8 | 26.2 |
| marked | active | 2 | rare | 196 | 176 | not_fit.kind(reaction) 4 | 71.2 | 35.3 |
| marked | active | 2 | epic | 187 | 166 | not_fit.kind(passive) 8 | 76.5 | 40.7 |
| marked | active | 3 | common | 200 | 90 |  | 34.7 | 24.1 |
| marked | active | 3 | rare | 196 | 177 | not_fit.kind(reaction) 4 | 71.3 | 36.3 |
| marked | active | 3 | epic | 188 | 170 | not_fit.kind(reaction) 6 | 67.6 | 37.8 |
| marked | active | 4 | common | 200 | 87 |  | 38.3 | 31.1 |
| marked | active | 4 | rare | 199 | 185 | not_fit.kind(reaction) 1 | 71.9 | 35.9 |
| marked | active | 4 | epic | 195 | 170 | not_fit.kind(passive) 4 | 81.4 | 47.2 |
| marked | passive | 1 | epic | 199 | 23 | keyword_exhausted 1 | 69.9 | 46.7 |
| marked | passive | 2 | epic | 200 | 38 |  | 49.9 | 37.5 |
| marked | passive | 3 | epic | 200 | 38 |  | 55.1 | 35.6 |
| marked | passive | 4 | epic | 200 | 35 |  | 49.3 | 32.6 |
| marked | reaction | 1 | rare | 195 | 53 | keyword_exhausted 5 | 90.6 | 67.5 |
| marked | reaction | 1 | epic | 195 | 53 | keyword_exhausted 5 | 90.4 | 65.3 |
| marked | reaction | 2 | rare | 199 | 49 | keyword_exhausted 1 | 89.4 | 66.9 |
| marked | reaction | 2 | epic | 199 | 49 | keyword_exhausted 1 | 90.1 | 67.7 |
| marked | reaction | 3 | rare | 194 | 62 | keyword_exhausted 6 | 136.7 | 111.5 |
| marked | reaction | 3 | epic | 194 | 62 | keyword_exhausted 6 | 139.1 | 114.5 |
| marked | reaction | 4 | rare | 174 | 56 | keyword_exhausted 26 | 214.3 | 162.0 |
| marked | reaction | 4 | epic | 174 | 56 | keyword_exhausted 26 | 213.3 | 170.7 |
| high_ground | active | 1 | common | 0 | 0 | not_fit.keyword 200 | 13.4 | 10.9 |
| high_ground | active | 1 | rare | 39 | 35 | not_fit.keyword 156 | 114.8 | 56.8 |
| high_ground | active | 1 | epic | 28 | 28 | not_fit.keyword 162 | 106.7 | 46.3 |
| high_ground | active | 2 | common | 0 | 0 | not_fit.keyword 200 | 15.1 | 11.2 |
| high_ground | active | 2 | rare | 33 | 31 | not_fit.keyword 164 | 48.0 | 20.1 |
| high_ground | active | 2 | epic | 39 | 38 | not_fit.keyword 153 | 37.1 | 17.1 |
| high_ground | active | 3 | common | 0 | 0 | not_fit.keyword 200 | 17.3 | 12.8 |
| high_ground | active | 3 | rare | 37 | 37 | not_fit.keyword 159 | 37.5 | 17.9 |
| high_ground | active | 3 | epic | 43 | 42 | not_fit.keyword 147 | 38.1 | 17.4 |
| high_ground | active | 4 | common | 0 | 0 | not_fit.keyword 200 | 19.8 | 15.0 |
| high_ground | active | 4 | rare | 33 | 32 | not_fit.keyword 164 | 45.6 | 18.7 |
| high_ground | active | 4 | epic | 42 | 41 | not_fit.keyword 148 | 46.2 | 22.6 |
| high_ground | passive | 1 | epic | 0 | 0 | keyword_exhausted 200 | 373.8 | 365.4 |
| high_ground | passive | 2 | epic | 0 | 0 | keyword_exhausted 200 | 388.7 | 382.1 |
| high_ground | passive | 3 | epic | 0 | 0 | keyword_exhausted 200 | 428.4 | 423.5 |
| high_ground | passive | 4 | epic | 0 | 0 | keyword_exhausted 200 | 449.6 | 444.3 |
| high_ground | reaction | 1 | rare | 0 | 0 | not_fit.keyword 200 | 33.6 | 26.3 |
| high_ground | reaction | 1 | epic | 0 | 0 | not_fit.keyword 200 | 33.5 | 26.3 |
| high_ground | reaction | 2 | rare | 0 | 0 | not_fit.keyword 200 | 34.9 | 28.5 |
| high_ground | reaction | 2 | epic | 0 | 0 | not_fit.keyword 200 | 36.5 | 29.7 |
| high_ground | reaction | 3 | rare | 0 | 0 | not_fit.keyword 200 | 36.8 | 29.7 |
| high_ground | reaction | 3 | epic | 0 | 0 | not_fit.keyword 200 | 36.4 | 28.6 |
| high_ground | reaction | 4 | rare | 0 | 0 | not_fit.keyword 200 | 34.3 | 28.0 |
| high_ground | reaction | 4 | epic | 0 | 0 | not_fit.keyword 200 | 33.8 | 27.9 |
| concealed | active | 1 | common | 200 | 54 |  | 45.0 | 32.3 |
| concealed | active | 1 | rare | 197 | 150 | not_fit.kind(reaction) 3 | 234.6 | 155.8 |
| concealed | active | 1 | epic | 181 | 157 | not_fit.kind(passive) 16 | 220.6 | 120.9 |
| concealed | active | 2 | common | 200 | 58 |  | 49.3 | 35.0 |
| concealed | active | 2 | rare | 130 | 113 | not_fit.keyword 68 | 46.9 | 20.8 |
| concealed | active | 2 | epic | 128 | 121 | not_fit.keyword 54 | 54.1 | 23.9 |
| concealed | active | 3 | common | 200 | 56 |  | 63.6 | 48.9 |
| concealed | active | 3 | rare | 131 | 117 | not_fit.keyword 64 | 54.8 | 25.1 |
| concealed | active | 3 | epic | 125 | 119 | not_fit.keyword 57 | 51.1 | 23.2 |
| concealed | active | 4 | common | 200 | 62 |  | 63.1 | 44.5 |
| concealed | active | 4 | rare | 131 | 116 | not_fit.keyword 66 | 57.7 | 26.0 |
| concealed | active | 4 | epic | 129 | 122 | not_fit.keyword 50 | 51.2 | 20.5 |
| concealed | passive | 1 | epic | 200 | 36 |  | 24.4 | 17.6 |
| concealed | passive | 2 | epic | 200 | 34 |  | 23.8 | 16.2 |
| concealed | passive | 3 | epic | 200 | 36 |  | 25.3 | 17.3 |
| concealed | passive | 4 | epic | 200 | 32 |  | 28.3 | 19.8 |
| concealed | reaction | 1 | rare | 200 | 20 |  | 60.6 | 42.9 |
| concealed | reaction | 1 | epic | 200 | 20 |  | 59.5 | 43.7 |
| concealed | reaction | 2 | rare | 196 | 14 | keyword_exhausted 4 | 107.0 | 83.3 |
| concealed | reaction | 2 | epic | 196 | 14 | keyword_exhausted 4 | 107.9 | 80.2 |
| concealed | reaction | 3 | rare | 198 | 17 | keyword_exhausted 2 | 104.4 | 78.7 |
| concealed | reaction | 3 | epic | 198 | 17 | keyword_exhausted 2 | 105.4 | 79.3 |
| concealed | reaction | 4 | rare | 195 | 16 | keyword_exhausted 5 | 117.8 | 83.1 |
| concealed | reaction | 4 | epic | 195 | 16 | keyword_exhausted 5 | 120.2 | 81.4 |
| summon | active | 1 | common | 0 | 0 | not_fit.keyword 200 | 27.9 | 19.1 |
| summon | active | 1 | rare | 0 | 0 | not_fit.keyword 127 | 167.0 | 74.4 |
| summon | active | 1 | epic | 0 | 0 | not_fit.keyword 128 | 182.2 | 94.7 |
| summon | active | 2 | common | 0 | 0 | not_fit.keyword 200 | 30.6 | 20.0 |
| summon | active | 2 | rare | 29 | 8 | not_fit.keyword 104 | 56.4 | 29.9 |
| summon | active | 2 | epic | 37 | 8 | not_fit.keyword 89 | 67.3 | 32.0 |
| summon | active | 3 | common | 0 | 0 | not_fit.keyword 200 | 33.5 | 21.6 |
| summon | active | 3 | rare | 26 | 7 | not_fit.keyword 94 | 47.0 | 23.9 |
| summon | active | 3 | epic | 27 | 8 | not_fit.keyword 87 | 48.9 | 25.3 |
| summon | active | 4 | common | 0 | 0 | not_fit.keyword 200 | 40.9 | 27.8 |
| summon | active | 4 | rare | 25 | 7 | not_fit.keyword 93 | 58.0 | 30.2 |
| summon | active | 4 | epic | 31 | 8 | not_fit.kind(reaction) 86 | 57.1 | 30.6 |
| summon | passive | 1 | epic | 0 | 0 | keyword_exhausted 200 | 392.9 | 381.4 |
| summon | passive | 2 | epic | 0 | 0 | keyword_exhausted 200 | 401.7 | 394.0 |
| summon | passive | 3 | epic | 0 | 0 | keyword_exhausted 200 | 448.6 | 438.0 |
| summon | passive | 4 | epic | 0 | 0 | keyword_exhausted 200 | 468.6 | 460.0 |
| summon | reaction | 1 | rare | 0 | 0 | not_fit.keyword 200 | 3.9 | 3.1 |
| summon | reaction | 1 | epic | 0 | 0 | not_fit.keyword 200 | 4.0 | 3.1 |
| summon | reaction | 2 | rare | 0 | 0 | not_fit.keyword 200 | 4.2 | 3.4 |
| summon | reaction | 2 | epic | 0 | 0 | not_fit.keyword 200 | 4.0 | 3.3 |
| summon | reaction | 3 | rare | 0 | 0 | not_fit.keyword 200 | 4.2 | 3.3 |
| summon | reaction | 3 | epic | 0 | 0 | not_fit.keyword 200 | 4.2 | 3.4 |
| summon | reaction | 4 | rare | 0 | 0 | not_fit.keyword 200 | 4.3 | 3.4 |
| summon | reaction | 4 | epic | 0 | 0 | not_fit.keyword 200 | 4.7 | 3.9 |
| poisoned | active | 1 | common | 200 | 69 |  | 45.0 | 31.4 |
| poisoned | active | 1 | rare | 195 | 183 | not_fit.kind(reaction) 5 | 441.9 | 311.3 |
| poisoned | active | 1 | epic | 166 | 157 | not_fit.kind(passive) 20 | 384.5 | 244.2 |
| poisoned | active | 2 | common | 200 | 70 |  | 50.0 | 36.7 |
| poisoned | active | 2 | rare | 198 | 184 | not_fit.kind(reaction) 2 | 143.4 | 94.0 |
| poisoned | active | 2 | epic | 176 | 163 | not_fit.kind(passive) 12 | 129.2 | 63.5 |
| poisoned | active | 3 | common | 200 | 74 |  | 51.8 | 38.0 |
| poisoned | active | 3 | rare | 198 | 191 | not_fit.kind(reaction) 2 | 154.8 | 87.4 |
| poisoned | active | 3 | epic | 177 | 159 | not_fit.kind(passive) 13 | 136.4 | 65.8 |
| poisoned | active | 4 | common | 200 | 71 |  | 75.7 | 59.9 |
| poisoned | active | 4 | rare | 200 | 189 |  | 156.3 | 85.1 |
| poisoned | active | 4 | epic | 182 | 165 | not_fit.kind(modifier) 10 | 115.7 | 61.1 |
| poisoned | passive | 1 | epic | 200 | 25 |  | 48.2 | 36.3 |
| poisoned | passive | 2 | epic | 200 | 25 |  | 59.4 | 42.5 |
| poisoned | passive | 3 | epic | 197 | 27 | keyword_exhausted 3 | 72.9 | 48.1 |
| poisoned | passive | 4 | epic | 199 | 30 | keyword_exhausted 1 | 80.8 | 60.2 |
| poisoned | reaction | 1 | rare | 192 | 69 | keyword_exhausted 8 | 118.3 | 84.9 |
| poisoned | reaction | 1 | epic | 192 | 69 | keyword_exhausted 8 | 119.4 | 83.6 |
| poisoned | reaction | 2 | rare | 184 | 69 | keyword_exhausted 16 | 161.8 | 118.7 |
| poisoned | reaction | 2 | epic | 184 | 69 | keyword_exhausted 16 | 162.4 | 116.6 |
| poisoned | reaction | 3 | rare | 134 | 60 | keyword_exhausted 66 | 257.0 | 237.5 |
| poisoned | reaction | 3 | epic | 134 | 60 | keyword_exhausted 66 | 254.0 | 240.5 |
| poisoned | reaction | 4 | rare | 93 | 40 | keyword_exhausted 107 | 352.4 | 427.4 |
| poisoned | reaction | 4 | epic | 93 | 40 | keyword_exhausted 107 | 351.8 | 429.1 |
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
| combo_point | active | 1 | common | 0 | 0 | keyword_exhausted 200 | 0.8 | 0.9 |
| combo_point | active | 1 | rare | 200 | 129 |  | 43.1 | 21.4 |
| combo_point | active | 1 | epic | 200 | 171 |  | 52.1 | 34.1 |
| combo_point | active | 2 | common | 0 | 0 | keyword_exhausted 200 | 0.9 | 0.9 |
| combo_point | active | 2 | rare | 200 | 135 |  | 25.2 | 15.9 |
| combo_point | active | 2 | epic | 200 | 164 |  | 26.2 | 16.4 |
| combo_point | active | 3 | common | 0 | 0 | keyword_exhausted 200 | 0.8 | 0.9 |
| combo_point | active | 3 | rare | 200 | 131 |  | 23.7 | 14.9 |
| combo_point | active | 3 | epic | 200 | 166 |  | 23.4 | 16.8 |
| combo_point | active | 4 | common | 0 | 0 | keyword_exhausted 200 | 0.8 | 0.9 |
| combo_point | active | 4 | rare | 200 | 130 |  | 22.9 | 16.7 |
| combo_point | active | 4 | epic | 200 | 167 |  | 25.6 | 17.4 |
| combo_point | passive | 1 | epic | 0 | 0 | keyword_exhausted 200 | 372.4 | 356.1 |
| combo_point | passive | 2 | epic | 0 | 0 | keyword_exhausted 200 | 385.2 | 367.9 |
| combo_point | passive | 3 | epic | 0 | 0 | keyword_exhausted 200 | 425.6 | 406.5 |
| combo_point | passive | 4 | epic | 0 | 0 | keyword_exhausted 200 | 449.9 | 432.8 |
| combo_point | reaction | 1 | rare | 0 | 0 | keyword_exhausted 200 | 363.7 | 346.1 |
| combo_point | reaction | 1 | epic | 0 | 0 | keyword_exhausted 200 | 364.4 | 348.2 |
| combo_point | reaction | 2 | rare | 0 | 0 | keyword_exhausted 200 | 423.8 | 417.6 |
| combo_point | reaction | 2 | epic | 0 | 0 | keyword_exhausted 200 | 421.2 | 417.3 |
| combo_point | reaction | 3 | rare | 0 | 0 | keyword_exhausted 200 | 467.8 | 464.5 |
| combo_point | reaction | 3 | epic | 0 | 0 | keyword_exhausted 200 | 467.1 | 464.1 |
| combo_point | reaction | 4 | rare | 0 | 0 | keyword_exhausted 200 | 490.6 | 488.4 |
| combo_point | reaction | 4 | epic | 0 | 0 | keyword_exhausted 200 | 493.4 | 491.7 |
| fury | active | 1 | common | 0 | 0 | keyword_exhausted 200 | 0.9 | 0.9 |
| fury | active | 1 | rare | 200 | 130 |  | 51.3 | 30.4 |
| fury | active | 1 | epic | 200 | 160 |  | 60.3 | 33.9 |
| fury | active | 2 | common | 0 | 0 | keyword_exhausted 200 | 1.0 | 0.9 |
| fury | active | 2 | rare | 200 | 124 |  | 29.4 | 21.4 |
| fury | active | 2 | epic | 200 | 165 |  | 32.2 | 21.7 |
| fury | active | 3 | common | 0 | 0 | keyword_exhausted 200 | 1.0 | 0.9 |
| fury | active | 3 | rare | 200 | 132 |  | 27.8 | 19.6 |
| fury | active | 3 | epic | 200 | 169 |  | 28.9 | 20.6 |
| fury | active | 4 | common | 0 | 0 | keyword_exhausted 200 | 0.9 | 0.9 |
| fury | active | 4 | rare | 200 | 142 |  | 27.7 | 19.7 |
| fury | active | 4 | epic | 200 | 171 |  | 27.5 | 20.5 |
| fury | passive | 1 | epic | 0 | 0 | keyword_exhausted 200 | 363.7 | 363.3 |
| fury | passive | 2 | epic | 0 | 0 | keyword_exhausted 200 | 379.3 | 377.5 |
| fury | passive | 3 | epic | 0 | 0 | keyword_exhausted 200 | 419.1 | 417.5 |
| fury | passive | 4 | epic | 0 | 0 | keyword_exhausted 200 | 437.0 | 437.2 |
| fury | reaction | 1 | rare | 0 | 0 | keyword_exhausted 200 | 347.9 | 343.5 |
| fury | reaction | 1 | epic | 0 | 0 | keyword_exhausted 200 | 347.9 | 342.9 |
| fury | reaction | 2 | rare | 0 | 0 | keyword_exhausted 200 | 420.0 | 415.4 |
| fury | reaction | 2 | epic | 0 | 0 | keyword_exhausted 200 | 427.3 | 421.1 |
| fury | reaction | 3 | rare | 0 | 0 | keyword_exhausted 200 | 466.9 | 463.3 |
| fury | reaction | 3 | epic | 0 | 0 | keyword_exhausted 200 | 472.5 | 467.8 |
| fury | reaction | 4 | rare | 0 | 0 | keyword_exhausted 200 | 496.8 | 492.2 |
| fury | reaction | 4 | epic | 0 | 0 | keyword_exhausted 200 | 494.9 | 489.6 |
| focus | active | 1 | common | 0 | 0 | keyword_exhausted 200 | 0.9 | 0.9 |
| focus | active | 1 | rare | 200 | 140 |  | 48.5 | 27.4 |
| focus | active | 1 | epic | 200 | 169 |  | 49.5 | 25.4 |
| focus | active | 2 | common | 0 | 0 | keyword_exhausted 200 | 0.9 | 0.9 |
| focus | active | 2 | rare | 200 | 140 |  | 29.4 | 19.1 |
| focus | active | 2 | epic | 200 | 177 |  | 33.8 | 21.6 |
| focus | active | 3 | common | 0 | 0 | keyword_exhausted 200 | 0.9 | 0.9 |
| focus | active | 3 | rare | 200 | 136 |  | 26.4 | 17.1 |
| focus | active | 3 | epic | 200 | 171 |  | 29.0 | 19.2 |
| focus | active | 4 | common | 0 | 0 | keyword_exhausted 200 | 0.9 | 0.9 |
| focus | active | 4 | rare | 200 | 133 |  | 27.9 | 15.8 |
| focus | active | 4 | epic | 200 | 167 |  | 34.0 | 21.3 |
| focus | passive | 1 | epic | 0 | 0 | keyword_exhausted 200 | 364.6 | 358.8 |
| focus | passive | 2 | epic | 0 | 0 | keyword_exhausted 200 | 374.2 | 372.4 |
| focus | passive | 3 | epic | 0 | 0 | keyword_exhausted 200 | 411.4 | 408.3 |
| focus | passive | 4 | epic | 0 | 0 | keyword_exhausted 200 | 449.1 | 445.7 |
| focus | reaction | 1 | rare | 0 | 0 | keyword_exhausted 200 | 357.0 | 354.4 |
| focus | reaction | 1 | epic | 0 | 0 | keyword_exhausted 200 | 356.4 | 354.0 |
| focus | reaction | 2 | rare | 0 | 0 | keyword_exhausted 200 | 421.2 | 419.6 |
| focus | reaction | 2 | epic | 0 | 0 | keyword_exhausted 200 | 418.8 | 417.4 |
| focus | reaction | 3 | rare | 0 | 0 | keyword_exhausted 200 | 457.3 | 456.7 |
| focus | reaction | 3 | epic | 0 | 0 | keyword_exhausted 200 | 461.0 | 460.1 |
| focus | reaction | 4 | rare | 0 | 0 | keyword_exhausted 200 | 480.5 | 479.8 |
| focus | reaction | 4 | epic | 0 | 0 | keyword_exhausted 200 | 486.5 | 486.8 |
| ki | active | 1 | common | 0 | 0 | keyword_exhausted 200 | 0.9 | 0.9 |
| ki | active | 1 | rare | 200 | 122 |  | 43.5 | 21.4 |
| ki | active | 1 | epic | 200 | 163 |  | 54.5 | 29.6 |
| ki | active | 2 | common | 0 | 0 | keyword_exhausted 200 | 0.9 | 0.9 |
| ki | active | 2 | rare | 200 | 138 |  | 26.8 | 16.5 |
| ki | active | 2 | epic | 200 | 172 |  | 29.1 | 18.4 |
| ki | active | 3 | common | 0 | 0 | keyword_exhausted 200 | 0.9 | 0.9 |
| ki | active | 3 | rare | 200 | 127 |  | 24.6 | 16.7 |
| ki | active | 3 | epic | 200 | 174 |  | 27.6 | 18.7 |
| ki | active | 4 | common | 0 | 0 | keyword_exhausted 200 | 0.9 | 0.9 |
| ki | active | 4 | rare | 200 | 123 |  | 27.8 | 17.3 |
| ki | active | 4 | epic | 200 | 175 |  | 27.8 | 17.9 |
| ki | passive | 1 | epic | 0 | 0 | keyword_exhausted 200 | 365.7 | 363.9 |
| ki | passive | 2 | epic | 0 | 0 | keyword_exhausted 200 | 368.3 | 365.6 |
| ki | passive | 3 | epic | 0 | 0 | keyword_exhausted 200 | 410.3 | 409.1 |
| ki | passive | 4 | epic | 0 | 0 | keyword_exhausted 200 | 431.2 | 429.5 |
| ki | reaction | 1 | rare | 0 | 0 | keyword_exhausted 200 | 349.4 | 348.3 |
| ki | reaction | 1 | epic | 0 | 0 | keyword_exhausted 200 | 351.6 | 349.3 |
| ki | reaction | 2 | rare | 0 | 0 | keyword_exhausted 200 | 402.3 | 401.5 |
| ki | reaction | 2 | epic | 0 | 0 | keyword_exhausted 200 | 404.0 | 402.8 |
| ki | reaction | 3 | rare | 0 | 0 | keyword_exhausted 200 | 432.1 | 425.2 |
| ki | reaction | 3 | epic | 0 | 0 | keyword_exhausted 200 | 427.2 | 421.8 |
| ki | reaction | 4 | rare | 0 | 0 | keyword_exhausted 200 | 440.3 | 431.9 |
| ki | reaction | 4 | epic | 0 | 0 | keyword_exhausted 200 | 426.7 | 421.6 |
