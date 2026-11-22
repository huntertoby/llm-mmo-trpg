# 組合器配方盤點摘要

格式 `recipe-census/1`；種子 0～49；薄格門檻：不同設計 < 12。由 `scripts/recipe_census.py` 產生，計時欄每次不同。

- 格子 612：正常 317、薄 51、空 40、設計上不存在 204（骨架稀有度下限：被動至少 epic、反應至少 rare）
- 其中遊戲會出題（出題檢查通過）的：空 20、薄 51；其餘空格是規則上就沒有專屬來源（遊戲不出這題）

## 依關鍵字（不含設計上不存在；「會出題」＝出題檢查通過的空格與薄格）

| 關鍵字 | 空 | 薄 | 正常 | 會出題的空 | 會出題的薄 |
|---|---|---|---|---|---|
| - | 0 | 0 | 24 | 0 | 0 |
| ignite | 0 | 4 | 20 | 0 | 4 |
| wet | 4 | 0 | 20 | 0 | 0 |
| charged | 0 | 9 | 15 | 0 | 9 |
| frozen | 0 | 6 | 18 | 0 | 6 |
| prone | 4 | 8 | 12 | 0 | 8 |
| collision | 4 | 4 | 16 | 0 | 4 |
| marked | 0 | 2 | 22 | 0 | 2 |
| high_ground | 4 | 0 | 20 | 0 | 0 |
| concealed | 0 | 6 | 18 | 0 | 6 |
| summon | 0 | 12 | 12 | 0 | 12 |
| poisoned | 0 | 0 | 24 | 0 | 0 |
| form | 24 | 0 | 0 | 20 | 0 |
| combo_point | 0 | 0 | 24 | 0 | 0 |
| fury | 0 | 0 | 24 | 0 | 0 |
| focus | 0 | 0 | 24 | 0 | 0 |
| ki | 0 | 0 | 24 | 0 | 0 |

## 依種類

| 種類 | 空 | 薄 | 正常 | 會出題的空 | 會出題的薄 |
|---|---|---|---|---|---|
| active | 28 | 0 | 176 | 8 | 0 |
| passive | 4 | 5 | 59 | 4 | 5 |
| reaction | 8 | 46 | 82 | 8 | 46 |

## 空格與薄格（依玩家遇到的頻率排序）

| 關鍵字 | 種類 | 階 | 稀有度 | 狀態 | 會出題 | 合法 | 設計 | 主要原因 | 判斷 | 中位 ms |
|---|---|---|---|---|---|---|---|---|---|---|
| collision | active | 2 | common | empty | 否 | 0 | 0 | keyword_exhausted 50 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 484.8 |
| form | active | 2 | common | empty | 否 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 2 | rare | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| high_ground | active | 2 | common | empty | 否 | 0 | 0 | keyword_exhausted 50 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 474.4 |
| prone | active | 2 | common | empty | 否 | 0 | 0 | keyword_exhausted 50 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 478.2 |
| wet | active | 2 | common | empty | 否 | 0 | 0 | keyword_exhausted 50 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 442.3 |
| collision | active | 1 | common | empty | 否 | 0 | 0 | keyword_exhausted 50 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 441.3 |
| collision | active | 3 | common | empty | 否 | 0 | 0 | keyword_exhausted 50 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 561.5 |
| form | active | 1 | common | empty | 否 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 1 | rare | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 3 | common | empty | 否 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 3 | rare | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| high_ground | active | 1 | common | empty | 否 | 0 | 0 | keyword_exhausted 50 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 452.3 |
| high_ground | active | 3 | common | empty | 否 | 0 | 0 | keyword_exhausted 50 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 575.3 |
| prone | active | 1 | common | empty | 否 | 0 | 0 | keyword_exhausted 50 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 439.8 |
| prone | active | 3 | common | empty | 否 | 0 | 0 | keyword_exhausted 50 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 568.3 |
| wet | active | 1 | common | empty | 否 | 0 | 0 | keyword_exhausted 50 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 395.8 |
| wet | active | 3 | common | empty | 否 | 0 | 0 | keyword_exhausted 50 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 581.0 |
| form | active | 2 | epic | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 1 | epic | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 3 | epic | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| form | passive | 2 | epic | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | passive | 2 | epic | thin | 是 | 50 | 8 |  | 配方稀少：偶爾帶到專屬關鍵字 | 6.0 |
| charged | reaction | 2 | rare | thin | 是 | 50 | 2 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 3.8 |
| concealed | reaction | 2 | rare | thin | 是 | 50 | 4 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 4.6 |
| form | reaction | 2 | rare | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| frozen | reaction | 2 | rare | thin | 是 | 50 | 7 |  | 配方稀少：偶爾帶到專屬關鍵字 | 3.8 |
| ignite | reaction | 2 | rare | thin | 是 | 50 | 8 |  | 配方稀少：偶爾帶到專屬關鍵字 | 4.8 |
| marked | reaction | 2 | rare | thin | 是 | 50 | 2 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 5.1 |
| prone | reaction | 2 | rare | thin | 是 | 50 | 7 |  | 配方稀少：偶爾帶到專屬關鍵字 | 4.4 |
| summon | reaction | 2 | rare | thin | 是 | 50 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 5.9 |
| charged | passive | 1 | epic | thin | 是 | 50 | 11 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 19.7 |
| form | passive | 1 | epic | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| form | passive | 3 | epic | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | passive | 1 | epic | thin | 是 | 50 | 8 |  | 配方稀少：偶爾帶到專屬關鍵字 | 5.0 |
| summon | passive | 3 | epic | thin | 是 | 50 | 8 |  | 配方稀少：偶爾帶到專屬關鍵字 | 5.4 |
| collision | active | 4 | common | empty | 否 | 0 | 0 | keyword_exhausted 50 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 709.2 |
| form | active | 4 | common | empty | 否 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| form | active | 4 | rare | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| high_ground | active | 4 | common | empty | 否 | 0 | 0 | keyword_exhausted 50 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 701.7 |
| prone | active | 4 | common | empty | 否 | 0 | 0 | keyword_exhausted 50 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 698.0 |
| wet | active | 4 | common | empty | 否 | 0 | 0 | keyword_exhausted 50 | 規則擋下：這個稀有度／種類沒有這個關鍵字的專屬來源（遊戲不出這題） | 721.3 |
| charged | reaction | 1 | rare | thin | 是 | 46 | 6 | keyword_exhausted 4 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 53.7 |
| charged | reaction | 3 | rare | thin | 是 | 50 | 2 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 5.2 |
| collision | reaction | 3 | rare | thin | 是 | 50 | 9 |  | 配方稀少：偶爾帶到專屬關鍵字 | 6.1 |
| concealed | reaction | 3 | rare | thin | 是 | 50 | 4 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 4.9 |
| form | reaction | 1 | rare | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| form | reaction | 3 | rare | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| frozen | reaction | 3 | rare | thin | 是 | 50 | 6 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 5.0 |
| ignite | reaction | 3 | rare | thin | 是 | 50 | 7 |  | 配方稀少：偶爾帶到專屬關鍵字 | 7.1 |
| prone | reaction | 1 | rare | thin | 是 | 50 | 10 |  | 配方稀少：偶爾帶到專屬關鍵字 | 3.2 |
| prone | reaction | 3 | rare | thin | 是 | 50 | 5 |  | 配方稀少：偶爾帶到專屬關鍵字 | 5.4 |
| summon | reaction | 1 | rare | thin | 是 | 50 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 3.5 |
| summon | reaction | 3 | rare | thin | 是 | 50 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 7.7 |
| charged | reaction | 2 | epic | thin | 是 | 50 | 2 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 4.3 |
| concealed | reaction | 2 | epic | thin | 是 | 50 | 4 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 4.7 |
| form | reaction | 2 | epic | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| frozen | reaction | 2 | epic | thin | 是 | 50 | 7 |  | 配方稀少：偶爾帶到專屬關鍵字 | 4.2 |
| ignite | reaction | 2 | epic | thin | 是 | 50 | 8 |  | 配方稀少：偶爾帶到專屬關鍵字 | 5.2 |
| marked | reaction | 2 | epic | thin | 是 | 50 | 2 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 5.4 |
| prone | reaction | 2 | epic | thin | 是 | 50 | 7 |  | 配方稀少：偶爾帶到專屬關鍵字 | 5.2 |
| summon | reaction | 2 | epic | thin | 是 | 50 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 5.4 |
| form | active | 4 | epic | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| charged | reaction | 1 | epic | thin | 是 | 46 | 6 | keyword_exhausted 4 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 59.2 |
| charged | reaction | 3 | epic | thin | 是 | 50 | 2 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 4.9 |
| collision | reaction | 3 | epic | thin | 是 | 50 | 9 |  | 配方稀少：偶爾帶到專屬關鍵字 | 6.3 |
| concealed | reaction | 3 | epic | thin | 是 | 50 | 4 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 4.8 |
| form | reaction | 1 | epic | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| form | reaction | 3 | epic | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| frozen | reaction | 3 | epic | thin | 是 | 50 | 6 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 5.0 |
| ignite | reaction | 3 | epic | thin | 是 | 50 | 7 |  | 配方稀少：偶爾帶到專屬關鍵字 | 6.8 |
| prone | reaction | 1 | epic | thin | 是 | 50 | 10 |  | 配方稀少：偶爾帶到專屬關鍵字 | 3.1 |
| prone | reaction | 3 | epic | thin | 是 | 50 | 5 |  | 配方稀少：偶爾帶到專屬關鍵字 | 5.3 |
| summon | reaction | 1 | epic | thin | 是 | 50 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 3.6 |
| summon | reaction | 3 | epic | thin | 是 | 50 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 7.8 |
| form | passive | 4 | epic | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| summon | passive | 4 | epic | thin | 是 | 50 | 8 |  | 配方稀少：偶爾帶到專屬關鍵字 | 6.1 |
| charged | reaction | 4 | rare | thin | 是 | 50 | 2 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 5.8 |
| collision | reaction | 4 | rare | thin | 是 | 50 | 10 |  | 配方稀少：偶爾帶到專屬關鍵字 | 6.1 |
| concealed | reaction | 4 | rare | thin | 是 | 49 | 8 | keyword_exhausted 1 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 1095.5 |
| form | reaction | 4 | rare | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| frozen | reaction | 4 | rare | thin | 是 | 50 | 5 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 5.2 |
| prone | reaction | 4 | rare | thin | 是 | 50 | 5 |  | 配方稀少：偶爾帶到專屬關鍵字 | 6.4 |
| summon | reaction | 4 | rare | thin | 是 | 50 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 9.3 |
| charged | reaction | 4 | epic | thin | 是 | 50 | 2 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 5.6 |
| collision | reaction | 4 | epic | thin | 是 | 50 | 10 |  | 配方稀少：偶爾帶到專屬關鍵字 | 6.2 |
| concealed | reaction | 4 | epic | thin | 是 | 49 | 8 | keyword_exhausted 1 | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 1092.6 |
| form | reaction | 4 | epic | empty | 是 | 0 | 0 | keyword_not_composable 50 | 內容標記組合器不做（composable: false） | 0.0 |
| frozen | reaction | 4 | epic | thin | 是 | 50 | 5 |  | 缺配方：規則允許，但組合器這個種類從不帶這個關鍵字 | 5.4 |
| prone | reaction | 4 | epic | thin | 是 | 50 | 5 |  | 配方稀少：偶爾帶到專屬關鍵字 | 6.4 |
| summon | reaction | 4 | epic | thin | 是 | 50 | 1 |  | 只帶到通用規則：組合器認、退回路徑不收 | 9.8 |

## 全部格子

| 關鍵字 | 種類 | 階 | 稀有度 | 合法 | 設計 | 主要原因 | 平均 ms | 中位 ms |
|---|---|---|---|---|---|---|---|---|
| - | active | 1 | common | 50 | 46 |  | 2.6 | 2.0 |
| - | active | 1 | rare | 50 | 48 |  | 8.7 | 2.7 |
| - | active | 1 | epic | 50 | 47 |  | 8.4 | 2.8 |
| - | active | 2 | common | 50 | 46 |  | 2.9 | 2.3 |
| - | active | 2 | rare | 50 | 48 |  | 5.1 | 2.8 |
| - | active | 2 | epic | 50 | 46 |  | 4.0 | 2.8 |
| - | active | 3 | common | 50 | 46 |  | 2.4 | 2.0 |
| - | active | 3 | rare | 50 | 46 |  | 3.9 | 2.1 |
| - | active | 3 | epic | 50 | 46 |  | 3.6 | 2.2 |
| - | active | 4 | common | 50 | 44 |  | 3.3 | 2.1 |
| - | active | 4 | rare | 50 | 46 |  | 3.6 | 2.2 |
| - | active | 4 | epic | 50 | 46 |  | 4.1 | 2.6 |
| - | passive | 1 | epic | 50 | 42 |  | 1.6 | 1.6 |
| - | passive | 2 | epic | 50 | 44 |  | 1.7 | 1.7 |
| - | passive | 3 | epic | 50 | 44 |  | 1.8 | 1.7 |
| - | passive | 4 | epic | 50 | 44 |  | 1.8 | 1.7 |
| - | reaction | 1 | rare | 50 | 31 |  | 1.5 | 1.4 |
| - | reaction | 1 | epic | 50 | 31 |  | 1.5 | 1.4 |
| - | reaction | 2 | rare | 50 | 30 |  | 1.7 | 1.6 |
| - | reaction | 2 | epic | 50 | 30 |  | 1.8 | 1.6 |
| - | reaction | 3 | rare | 50 | 28 |  | 1.9 | 1.7 |
| - | reaction | 3 | epic | 50 | 28 |  | 1.7 | 1.5 |
| - | reaction | 4 | rare | 50 | 28 |  | 1.7 | 1.7 |
| - | reaction | 4 | epic | 50 | 28 |  | 1.7 | 1.6 |
| ignite | active | 1 | common | 50 | 38 |  | 12.0 | 7.5 |
| ignite | active | 1 | rare | 42 | 40 | not_fit.keyword 8 | 111.2 | 52.8 |
| ignite | active | 1 | epic | 43 | 38 | not_fit.keyword 7 | 95.6 | 39.5 |
| ignite | active | 2 | common | 50 | 36 |  | 14.0 | 11.6 |
| ignite | active | 2 | rare | 41 | 25 | not_fit.keyword 9 | 26.0 | 15.1 |
| ignite | active | 2 | epic | 45 | 33 | not_fit.keyword 5 | 22.6 | 11.1 |
| ignite | active | 3 | common | 50 | 34 |  | 17.5 | 11.3 |
| ignite | active | 3 | rare | 45 | 30 | not_fit.keyword 5 | 31.4 | 15.8 |
| ignite | active | 3 | epic | 45 | 32 | not_fit.keyword 5 | 26.3 | 15.2 |
| ignite | active | 4 | common | 50 | 37 |  | 23.7 | 15.0 |
| ignite | active | 4 | rare | 42 | 27 | not_fit.keyword 8 | 36.3 | 19.1 |
| ignite | active | 4 | epic | 44 | 29 | not_fit.keyword 6 | 30.9 | 16.9 |
| ignite | passive | 1 | epic | 50 | 26 |  | 14.6 | 7.0 |
| ignite | passive | 2 | epic | 50 | 20 |  | 5.7 | 3.8 |
| ignite | passive | 3 | epic | 50 | 22 |  | 5.1 | 3.4 |
| ignite | passive | 4 | epic | 50 | 21 |  | 5.2 | 3.5 |
| ignite | reaction | 1 | rare | 50 | 28 |  | 31.9 | 20.9 |
| ignite | reaction | 1 | epic | 50 | 28 |  | 31.7 | 22.1 |
| ignite | reaction | 2 | rare | 50 | 8 |  | 7.6 | 4.8 |
| ignite | reaction | 2 | epic | 50 | 8 |  | 7.8 | 5.2 |
| ignite | reaction | 3 | rare | 50 | 7 |  | 10.2 | 7.1 |
| ignite | reaction | 3 | epic | 50 | 7 |  | 9.9 | 6.8 |
| ignite | reaction | 4 | rare | 50 | 14 |  | 944.2 | 507.5 |
| ignite | reaction | 4 | epic | 50 | 14 |  | 946.1 | 519.2 |
| wet | active | 1 | common | 0 | 0 | keyword_exhausted 50 | 425.6 | 395.8 |
| wet | active | 1 | rare | 50 | 50 |  | 521.5 | 406.1 |
| wet | active | 1 | epic | 50 | 50 |  | 694.7 | 665.9 |
| wet | active | 2 | common | 0 | 0 | keyword_exhausted 50 | 446.3 | 442.3 |
| wet | active | 2 | rare | 50 | 18 |  | 68.7 | 35.5 |
| wet | active | 2 | epic | 50 | 18 |  | 82.0 | 47.9 |
| wet | active | 3 | common | 0 | 0 | keyword_exhausted 50 | 590.1 | 581.0 |
| wet | active | 3 | rare | 50 | 21 |  | 65.3 | 36.1 |
| wet | active | 3 | epic | 50 | 22 |  | 68.9 | 49.1 |
| wet | active | 4 | common | 0 | 0 | keyword_exhausted 50 | 732.6 | 721.3 |
| wet | active | 4 | rare | 50 | 17 |  | 83.8 | 44.7 |
| wet | active | 4 | epic | 50 | 19 |  | 80.6 | 51.0 |
| wet | passive | 1 | epic | 50 | 43 |  | 7.1 | 4.7 |
| wet | passive | 2 | epic | 50 | 34 |  | 7.5 | 4.8 |
| wet | passive | 3 | epic | 50 | 34 |  | 7.6 | 4.9 |
| wet | passive | 4 | epic | 50 | 33 |  | 9.1 | 6.2 |
| wet | reaction | 1 | rare | 50 | 33 |  | 7.2 | 5.0 |
| wet | reaction | 1 | epic | 50 | 33 |  | 7.0 | 5.3 |
| wet | reaction | 2 | rare | 50 | 19 |  | 8.2 | 5.8 |
| wet | reaction | 2 | epic | 50 | 19 |  | 8.2 | 5.5 |
| wet | reaction | 3 | rare | 50 | 17 |  | 9.0 | 6.8 |
| wet | reaction | 3 | epic | 50 | 17 |  | 8.3 | 6.2 |
| wet | reaction | 4 | rare | 50 | 15 |  | 113.2 | 27.4 |
| wet | reaction | 4 | epic | 50 | 15 |  | 112.3 | 28.9 |
| charged | active | 1 | common | 50 | 28 |  | 33.3 | 24.2 |
| charged | active | 1 | rare | 40 | 38 | not_fit.keyword 10 | 161.0 | 59.3 |
| charged | active | 1 | epic | 40 | 35 | not_fit.keyword 10 | 135.8 | 58.5 |
| charged | active | 2 | common | 50 | 29 |  | 37.5 | 28.2 |
| charged | active | 2 | rare | 40 | 25 | not_fit.keyword 10 | 31.7 | 9.7 |
| charged | active | 2 | epic | 34 | 21 | not_fit.keyword 16 | 24.6 | 9.4 |
| charged | active | 3 | common | 50 | 30 |  | 38.6 | 28.5 |
| charged | active | 3 | rare | 43 | 35 | not_fit.keyword 7 | 23.9 | 8.0 |
| charged | active | 3 | epic | 40 | 32 | not_fit.keyword 10 | 21.5 | 8.8 |
| charged | active | 4 | common | 50 | 28 |  | 44.3 | 31.3 |
| charged | active | 4 | rare | 41 | 30 | not_fit.keyword 9 | 22.2 | 8.4 |
| charged | active | 4 | epic | 42 | 35 | not_fit.keyword 8 | 19.2 | 7.8 |
| charged | passive | 1 | epic | 50 | 11 |  | 26.9 | 19.7 |
| charged | passive | 2 | epic | 50 | 12 |  | 7.2 | 5.2 |
| charged | passive | 3 | epic | 50 | 13 |  | 5.9 | 3.9 |
| charged | passive | 4 | epic | 50 | 14 |  | 6.9 | 4.9 |
| charged | reaction | 1 | rare | 46 | 6 | keyword_exhausted 4 | 86.8 | 53.7 |
| charged | reaction | 1 | epic | 46 | 6 | keyword_exhausted 4 | 86.9 | 59.2 |
| charged | reaction | 2 | rare | 50 | 2 |  | 6.4 | 3.8 |
| charged | reaction | 2 | epic | 50 | 2 |  | 6.9 | 4.3 |
| charged | reaction | 3 | rare | 50 | 2 |  | 7.5 | 5.2 |
| charged | reaction | 3 | epic | 50 | 2 |  | 7.5 | 4.9 |
| charged | reaction | 4 | rare | 50 | 2 |  | 8.4 | 5.8 |
| charged | reaction | 4 | epic | 50 | 2 |  | 7.8 | 5.6 |
| frozen | active | 1 | common | 50 | 24 |  | 28.3 | 21.3 |
| frozen | active | 1 | rare | 45 | 38 | not_fit.keyword 5 | 127.8 | 44.7 |
| frozen | active | 1 | epic | 42 | 36 | not_fit.keyword 8 | 127.2 | 49.6 |
| frozen | active | 2 | common | 50 | 26 |  | 28.4 | 20.8 |
| frozen | active | 2 | rare | 41 | 28 | not_fit.keyword 9 | 33.3 | 14.4 |
| frozen | active | 2 | epic | 43 | 32 | not_fit.keyword 7 | 25.4 | 14.9 |
| frozen | active | 3 | common | 50 | 27 |  | 32.5 | 22.3 |
| frozen | active | 3 | rare | 39 | 29 | not_fit.keyword 11 | 34.4 | 13.6 |
| frozen | active | 3 | epic | 39 | 28 | not_fit.keyword 11 | 29.4 | 10.4 |
| frozen | active | 4 | common | 50 | 26 |  | 49.4 | 32.8 |
| frozen | active | 4 | rare | 40 | 27 | not_fit.keyword 10 | 30.3 | 14.1 |
| frozen | active | 4 | epic | 41 | 32 | not_fit.keyword 9 | 33.0 | 12.0 |
| frozen | passive | 1 | epic | 50 | 14 |  | 23.2 | 17.5 |
| frozen | passive | 2 | epic | 50 | 12 |  | 5.5 | 4.0 |
| frozen | passive | 3 | epic | 50 | 13 |  | 5.0 | 3.5 |
| frozen | passive | 4 | epic | 50 | 12 |  | 6.8 | 4.6 |
| frozen | reaction | 1 | rare | 50 | 12 |  | 45.3 | 34.8 |
| frozen | reaction | 1 | epic | 50 | 12 |  | 45.1 | 32.3 |
| frozen | reaction | 2 | rare | 50 | 7 |  | 5.6 | 3.8 |
| frozen | reaction | 2 | epic | 50 | 7 |  | 6.0 | 4.2 |
| frozen | reaction | 3 | rare | 50 | 6 |  | 7.1 | 5.0 |
| frozen | reaction | 3 | epic | 50 | 6 |  | 7.1 | 5.0 |
| frozen | reaction | 4 | rare | 50 | 5 |  | 7.8 | 5.2 |
| frozen | reaction | 4 | epic | 50 | 5 |  | 7.5 | 5.4 |
| prone | active | 1 | common | 0 | 0 | keyword_exhausted 50 | 441.4 | 439.8 |
| prone | active | 1 | rare | 44 | 34 | not_fit.keyword 6 | 83.3 | 16.0 |
| prone | active | 1 | epic | 48 | 38 | not_fit.keyword 2 | 64.3 | 11.0 |
| prone | active | 2 | common | 0 | 0 | keyword_exhausted 50 | 482.2 | 478.2 |
| prone | active | 2 | rare | 47 | 32 | not_fit.keyword 3 | 31.9 | 12.5 |
| prone | active | 2 | epic | 49 | 36 | not_fit.keyword 1 | 25.4 | 14.3 |
| prone | active | 3 | common | 0 | 0 | keyword_exhausted 50 | 573.2 | 568.3 |
| prone | active | 3 | rare | 45 | 33 | not_fit.keyword 5 | 26.7 | 14.4 |
| prone | active | 3 | epic | 48 | 34 | not_fit.keyword 2 | 25.2 | 12.1 |
| prone | active | 4 | common | 0 | 0 | keyword_exhausted 50 | 707.6 | 698.0 |
| prone | active | 4 | rare | 41 | 27 | not_fit.keyword 9 | 37.7 | 15.9 |
| prone | active | 4 | epic | 47 | 35 | not_fit.keyword 3 | 29.1 | 17.1 |
| prone | passive | 1 | epic | 50 | 24 |  | 7.2 | 4.6 |
| prone | passive | 2 | epic | 50 | 26 |  | 7.7 | 5.3 |
| prone | passive | 3 | epic | 50 | 26 |  | 7.4 | 4.6 |
| prone | passive | 4 | epic | 50 | 26 |  | 8.6 | 5.9 |
| prone | reaction | 1 | rare | 50 | 10 |  | 4.9 | 3.2 |
| prone | reaction | 1 | epic | 50 | 10 |  | 4.4 | 3.1 |
| prone | reaction | 2 | rare | 50 | 7 |  | 6.9 | 4.4 |
| prone | reaction | 2 | epic | 50 | 7 |  | 7.5 | 5.2 |
| prone | reaction | 3 | rare | 50 | 5 |  | 8.7 | 5.4 |
| prone | reaction | 3 | epic | 50 | 5 |  | 8.3 | 5.3 |
| prone | reaction | 4 | rare | 50 | 5 |  | 9.9 | 6.4 |
| prone | reaction | 4 | epic | 50 | 5 |  | 10.0 | 6.4 |
| collision | active | 1 | common | 0 | 0 | keyword_exhausted 50 | 448.3 | 441.3 |
| collision | active | 1 | rare | 50 | 46 |  | 45.4 | 16.7 |
| collision | active | 1 | epic | 50 | 43 |  | 46.9 | 12.9 |
| collision | active | 2 | common | 0 | 0 | keyword_exhausted 50 | 491.3 | 484.8 |
| collision | active | 2 | rare | 50 | 37 |  | 21.0 | 10.8 |
| collision | active | 2 | epic | 50 | 36 |  | 13.9 | 7.3 |
| collision | active | 3 | common | 0 | 0 | keyword_exhausted 50 | 564.0 | 561.5 |
| collision | active | 3 | rare | 50 | 37 |  | 29.8 | 16.0 |
| collision | active | 3 | epic | 50 | 39 |  | 13.3 | 8.1 |
| collision | active | 4 | common | 0 | 0 | keyword_exhausted 50 | 714.3 | 709.2 |
| collision | active | 4 | rare | 50 | 35 |  | 29.7 | 15.6 |
| collision | active | 4 | epic | 50 | 37 |  | 14.6 | 9.3 |
| collision | passive | 1 | epic | 50 | 37 |  | 15.9 | 9.7 |
| collision | passive | 2 | epic | 50 | 19 |  | 6.5 | 4.6 |
| collision | passive | 3 | epic | 50 | 24 |  | 6.7 | 4.6 |
| collision | passive | 4 | epic | 50 | 22 |  | 6.8 | 5.4 |
| collision | reaction | 1 | rare | 50 | 36 |  | 13.2 | 8.6 |
| collision | reaction | 1 | epic | 50 | 36 |  | 12.6 | 9.8 |
| collision | reaction | 2 | rare | 50 | 13 |  | 7.6 | 5.4 |
| collision | reaction | 2 | epic | 50 | 13 |  | 7.7 | 5.8 |
| collision | reaction | 3 | rare | 50 | 9 |  | 8.6 | 6.1 |
| collision | reaction | 3 | epic | 50 | 9 |  | 8.8 | 6.3 |
| collision | reaction | 4 | rare | 50 | 10 |  | 9.5 | 6.1 |
| collision | reaction | 4 | epic | 50 | 10 |  | 9.3 | 6.2 |
| marked | active | 1 | common | 50 | 32 |  | 27.0 | 19.4 |
| marked | active | 1 | rare | 50 | 49 |  | 110.4 | 29.4 |
| marked | active | 1 | epic | 50 | 48 |  | 156.3 | 82.0 |
| marked | active | 2 | common | 50 | 38 |  | 24.9 | 20.9 |
| marked | active | 2 | rare | 50 | 33 |  | 32.1 | 17.0 |
| marked | active | 2 | epic | 50 | 34 |  | 30.4 | 19.1 |
| marked | active | 3 | common | 50 | 37 |  | 27.1 | 22.2 |
| marked | active | 3 | rare | 50 | 36 |  | 31.0 | 18.8 |
| marked | active | 3 | epic | 50 | 37 |  | 27.6 | 15.6 |
| marked | active | 4 | common | 50 | 37 |  | 34.2 | 26.0 |
| marked | active | 4 | rare | 50 | 50 |  | 132.4 | 30.2 |
| marked | active | 4 | epic | 50 | 47 |  | 129.2 | 27.4 |
| marked | passive | 1 | epic | 50 | 38 |  | 6.7 | 4.6 |
| marked | passive | 2 | epic | 50 | 28 |  | 7.0 | 4.4 |
| marked | passive | 3 | epic | 50 | 27 |  | 7.8 | 6.0 |
| marked | passive | 4 | epic | 50 | 29 |  | 7.0 | 5.5 |
| marked | reaction | 1 | rare | 48 | 23 | keyword_exhausted 2 | 73.4 | 55.0 |
| marked | reaction | 1 | epic | 48 | 23 | keyword_exhausted 2 | 79.5 | 59.6 |
| marked | reaction | 2 | rare | 50 | 2 |  | 7.4 | 5.1 |
| marked | reaction | 2 | epic | 50 | 2 |  | 7.5 | 5.4 |
| marked | reaction | 3 | rare | 48 | 31 | keyword_exhausted 2 | 2009.6 | 1624.4 |
| marked | reaction | 3 | epic | 48 | 31 | keyword_exhausted 2 | 2018.2 | 1583.1 |
| marked | reaction | 4 | rare | 44 | 26 | keyword_exhausted 6 | 2582.5 | 1784.5 |
| marked | reaction | 4 | epic | 44 | 26 | keyword_exhausted 6 | 2534.2 | 1751.8 |
| high_ground | active | 1 | common | 0 | 0 | keyword_exhausted 50 | 449.6 | 452.3 |
| high_ground | active | 1 | rare | 50 | 47 |  | 402.8 | 305.5 |
| high_ground | active | 1 | epic | 50 | 46 |  | 372.2 | 228.2 |
| high_ground | active | 2 | common | 0 | 0 | keyword_exhausted 50 | 477.1 | 474.4 |
| high_ground | active | 2 | rare | 50 | 23 |  | 64.0 | 47.5 |
| high_ground | active | 2 | epic | 50 | 19 |  | 62.6 | 44.9 |
| high_ground | active | 3 | common | 0 | 0 | keyword_exhausted 50 | 570.0 | 575.3 |
| high_ground | active | 3 | rare | 50 | 21 |  | 70.0 | 40.3 |
| high_ground | active | 3 | epic | 50 | 18 |  | 71.1 | 40.1 |
| high_ground | active | 4 | common | 0 | 0 | keyword_exhausted 50 | 713.0 | 701.7 |
| high_ground | active | 4 | rare | 50 | 46 |  | 357.1 | 280.5 |
| high_ground | active | 4 | epic | 50 | 50 |  | 449.6 | 317.3 |
| high_ground | passive | 1 | epic | 50 | 42 |  | 7.0 | 4.7 |
| high_ground | passive | 2 | epic | 50 | 27 |  | 8.7 | 6.2 |
| high_ground | passive | 3 | epic | 50 | 27 |  | 11.5 | 8.6 |
| high_ground | passive | 4 | epic | 50 | 27 |  | 12.7 | 9.7 |
| high_ground | reaction | 1 | rare | 50 | 37 |  | 6.5 | 4.7 |
| high_ground | reaction | 1 | epic | 50 | 37 |  | 5.9 | 4.5 |
| high_ground | reaction | 2 | rare | 50 | 23 |  | 8.9 | 6.0 |
| high_ground | reaction | 2 | epic | 50 | 23 |  | 8.1 | 5.2 |
| high_ground | reaction | 3 | rare | 50 | 34 |  | 105.9 | 18.9 |
| high_ground | reaction | 3 | epic | 50 | 34 |  | 110.5 | 22.8 |
| high_ground | reaction | 4 | rare | 50 | 28 |  | 107.0 | 25.0 |
| high_ground | reaction | 4 | epic | 50 | 28 |  | 105.8 | 22.5 |
| concealed | active | 1 | common | 50 | 25 |  | 33.7 | 19.2 |
| concealed | active | 1 | rare | 50 | 48 |  | 166.9 | 95.5 |
| concealed | active | 1 | epic | 50 | 48 |  | 216.7 | 130.7 |
| concealed | active | 2 | common | 50 | 26 |  | 38.9 | 21.4 |
| concealed | active | 2 | rare | 50 | 33 |  | 29.8 | 14.9 |
| concealed | active | 2 | epic | 50 | 34 |  | 38.4 | 16.0 |
| concealed | active | 3 | common | 50 | 25 |  | 49.5 | 27.3 |
| concealed | active | 3 | rare | 50 | 31 |  | 32.3 | 21.1 |
| concealed | active | 3 | epic | 50 | 34 |  | 35.8 | 21.0 |
| concealed | active | 4 | common | 50 | 27 |  | 62.7 | 38.4 |
| concealed | active | 4 | rare | 50 | 30 |  | 41.1 | 24.4 |
| concealed | active | 4 | epic | 50 | 33 |  | 42.2 | 23.5 |
| concealed | passive | 1 | epic | 50 | 20 |  | 21.9 | 17.7 |
| concealed | passive | 2 | epic | 50 | 15 |  | 5.9 | 3.5 |
| concealed | passive | 3 | epic | 50 | 18 |  | 6.2 | 4.4 |
| concealed | passive | 4 | epic | 50 | 18 |  | 6.7 | 4.5 |
| concealed | reaction | 1 | rare | 50 | 14 |  | 61.5 | 41.3 |
| concealed | reaction | 1 | epic | 50 | 14 |  | 62.0 | 41.7 |
| concealed | reaction | 2 | rare | 50 | 4 |  | 6.0 | 4.6 |
| concealed | reaction | 2 | epic | 50 | 4 |  | 6.5 | 4.7 |
| concealed | reaction | 3 | rare | 50 | 4 |  | 7.2 | 4.9 |
| concealed | reaction | 3 | epic | 50 | 4 |  | 7.2 | 4.8 |
| concealed | reaction | 4 | rare | 49 | 8 | keyword_exhausted 1 | 1593.4 | 1095.5 |
| concealed | reaction | 4 | epic | 49 | 8 | keyword_exhausted 1 | 1590.6 | 1092.6 |
| summon | active | 1 | common | 50 | 44 |  | 13.2 | 9.1 |
| summon | active | 1 | rare | 50 | 33 |  | 86.6 | 37.1 |
| summon | active | 1 | epic | 50 | 33 |  | 123.6 | 46.8 |
| summon | active | 2 | common | 50 | 42 |  | 13.0 | 10.3 |
| summon | active | 2 | rare | 50 | 32 |  | 36.6 | 15.6 |
| summon | active | 2 | epic | 50 | 30 |  | 52.2 | 27.5 |
| summon | active | 3 | common | 50 | 42 |  | 15.5 | 11.2 |
| summon | active | 3 | rare | 50 | 37 |  | 33.6 | 15.4 |
| summon | active | 3 | epic | 50 | 34 |  | 44.8 | 32.0 |
| summon | active | 4 | common | 50 | 40 |  | 19.8 | 14.2 |
| summon | active | 4 | rare | 50 | 36 |  | 35.3 | 21.0 |
| summon | active | 4 | epic | 50 | 35 |  | 45.3 | 32.6 |
| summon | passive | 1 | epic | 50 | 8 |  | 7.7 | 5.0 |
| summon | passive | 2 | epic | 50 | 8 |  | 8.0 | 6.0 |
| summon | passive | 3 | epic | 50 | 8 |  | 7.7 | 5.4 |
| summon | passive | 4 | epic | 50 | 8 |  | 8.6 | 6.1 |
| summon | reaction | 1 | rare | 50 | 1 |  | 5.0 | 3.5 |
| summon | reaction | 1 | epic | 50 | 1 |  | 5.6 | 3.6 |
| summon | reaction | 2 | rare | 50 | 1 |  | 8.8 | 5.9 |
| summon | reaction | 2 | epic | 50 | 1 |  | 8.4 | 5.4 |
| summon | reaction | 3 | rare | 50 | 1 |  | 10.7 | 7.7 |
| summon | reaction | 3 | epic | 50 | 1 |  | 10.7 | 7.8 |
| summon | reaction | 4 | rare | 50 | 1 |  | 13.0 | 9.3 |
| summon | reaction | 4 | epic | 50 | 1 |  | 13.7 | 9.8 |
| poisoned | active | 1 | common | 50 | 34 |  | 36.0 | 26.4 |
| poisoned | active | 1 | rare | 50 | 49 |  | 352.4 | 239.1 |
| poisoned | active | 1 | epic | 50 | 48 |  | 312.9 | 183.5 |
| poisoned | active | 2 | common | 50 | 35 |  | 42.0 | 36.8 |
| poisoned | active | 2 | rare | 50 | 50 |  | 99.0 | 85.0 |
| poisoned | active | 2 | epic | 50 | 47 |  | 84.6 | 56.9 |
| poisoned | active | 3 | common | 50 | 35 |  | 47.6 | 28.8 |
| poisoned | active | 3 | rare | 50 | 50 |  | 108.4 | 68.7 |
| poisoned | active | 3 | epic | 50 | 48 |  | 83.4 | 54.3 |
| poisoned | active | 4 | common | 50 | 32 |  | 72.2 | 68.8 |
| poisoned | active | 4 | rare | 50 | 50 |  | 129.1 | 89.0 |
| poisoned | active | 4 | epic | 50 | 46 |  | 93.4 | 62.2 |
| poisoned | passive | 1 | epic | 50 | 28 |  | 30.6 | 23.9 |
| poisoned | passive | 2 | epic | 50 | 28 |  | 40.7 | 34.2 |
| poisoned | passive | 3 | epic | 50 | 27 |  | 52.1 | 39.9 |
| poisoned | passive | 4 | epic | 50 | 22 |  | 61.7 | 41.0 |
| poisoned | reaction | 1 | rare | 47 | 34 | keyword_exhausted 3 | 131.3 | 102.1 |
| poisoned | reaction | 1 | epic | 47 | 34 | keyword_exhausted 3 | 126.9 | 97.6 |
| poisoned | reaction | 2 | rare | 47 | 28 | keyword_exhausted 3 | 152.3 | 120.5 |
| poisoned | reaction | 2 | epic | 47 | 28 | keyword_exhausted 3 | 155.1 | 125.1 |
| poisoned | reaction | 3 | rare | 33 | 26 | keyword_exhausted 17 | 260.9 | 281.7 |
| poisoned | reaction | 3 | epic | 33 | 26 | keyword_exhausted 17 | 259.6 | 295.4 |
| poisoned | reaction | 4 | rare | 21 | 16 | keyword_exhausted 29 | 331.2 | 398.6 |
| poisoned | reaction | 4 | epic | 21 | 16 | keyword_exhausted 29 | 331.1 | 396.4 |
| form | active | 1 | common | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | active | 1 | rare | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | active | 1 | epic | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | active | 2 | common | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | active | 2 | rare | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | active | 2 | epic | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | active | 3 | common | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | active | 3 | rare | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | active | 3 | epic | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | active | 4 | common | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | active | 4 | rare | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | active | 4 | epic | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | passive | 1 | epic | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | passive | 2 | epic | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | passive | 3 | epic | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | passive | 4 | epic | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | reaction | 1 | rare | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | reaction | 1 | epic | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | reaction | 2 | rare | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | reaction | 2 | epic | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | reaction | 3 | rare | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | reaction | 3 | epic | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | reaction | 4 | rare | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| form | reaction | 4 | epic | 0 | 0 | keyword_not_composable 50 | 0.0 | 0.0 |
| combo_point | active | 1 | common | 50 | 44 |  | 10.6 | 8.0 |
| combo_point | active | 1 | rare | 50 | 48 |  | 45.2 | 17.9 |
| combo_point | active | 1 | epic | 50 | 48 |  | 73.7 | 34.8 |
| combo_point | active | 2 | common | 50 | 44 |  | 13.4 | 9.9 |
| combo_point | active | 2 | rare | 50 | 47 |  | 23.1 | 17.2 |
| combo_point | active | 2 | epic | 50 | 50 |  | 40.7 | 23.5 |
| combo_point | active | 3 | common | 50 | 44 |  | 13.8 | 10.6 |
| combo_point | active | 3 | rare | 50 | 48 |  | 32.2 | 15.7 |
| combo_point | active | 3 | epic | 50 | 50 |  | 34.1 | 18.1 |
| combo_point | active | 4 | common | 50 | 44 |  | 19.5 | 12.5 |
| combo_point | active | 4 | rare | 50 | 48 |  | 25.6 | 17.4 |
| combo_point | active | 4 | epic | 50 | 50 |  | 30.3 | 19.8 |
| combo_point | passive | 1 | epic | 50 | 46 |  | 7.4 | 4.9 |
| combo_point | passive | 2 | epic | 50 | 48 |  | 7.8 | 5.6 |
| combo_point | passive | 3 | epic | 50 | 46 |  | 7.8 | 5.2 |
| combo_point | passive | 4 | epic | 50 | 47 |  | 8.1 | 5.9 |
| combo_point | reaction | 1 | rare | 50 | 43 |  | 6.4 | 4.2 |
| combo_point | reaction | 1 | epic | 50 | 43 |  | 6.3 | 4.2 |
| combo_point | reaction | 2 | rare | 50 | 40 |  | 7.4 | 5.2 |
| combo_point | reaction | 2 | epic | 50 | 40 |  | 7.0 | 4.6 |
| combo_point | reaction | 3 | rare | 50 | 37 |  | 7.7 | 4.8 |
| combo_point | reaction | 3 | epic | 50 | 37 |  | 7.4 | 5.2 |
| combo_point | reaction | 4 | rare | 50 | 36 |  | 8.4 | 5.6 |
| combo_point | reaction | 4 | epic | 50 | 36 |  | 8.5 | 5.8 |
| fury | active | 1 | common | 50 | 43 |  | 8.8 | 5.6 |
| fury | active | 1 | rare | 50 | 48 |  | 70.2 | 27.0 |
| fury | active | 1 | epic | 50 | 47 |  | 82.2 | 27.9 |
| fury | active | 2 | common | 50 | 42 |  | 10.3 | 6.7 |
| fury | active | 2 | rare | 50 | 50 |  | 23.8 | 18.0 |
| fury | active | 2 | epic | 50 | 47 |  | 32.8 | 24.5 |
| fury | active | 3 | common | 50 | 42 |  | 9.8 | 6.4 |
| fury | active | 3 | rare | 50 | 47 |  | 29.6 | 16.6 |
| fury | active | 3 | epic | 50 | 48 |  | 38.1 | 17.7 |
| fury | active | 4 | common | 50 | 41 |  | 13.7 | 8.8 |
| fury | active | 4 | rare | 50 | 47 |  | 29.0 | 21.9 |
| fury | active | 4 | epic | 50 | 48 |  | 33.9 | 23.1 |
| fury | passive | 1 | epic | 50 | 46 |  | 6.7 | 4.3 |
| fury | passive | 2 | epic | 50 | 48 |  | 6.9 | 4.6 |
| fury | passive | 3 | epic | 50 | 46 |  | 8.1 | 5.1 |
| fury | passive | 4 | epic | 50 | 47 |  | 8.4 | 6.0 |
| fury | reaction | 1 | rare | 50 | 43 |  | 6.2 | 4.7 |
| fury | reaction | 1 | epic | 50 | 43 |  | 6.3 | 4.5 |
| fury | reaction | 2 | rare | 50 | 40 |  | 6.8 | 4.6 |
| fury | reaction | 2 | epic | 50 | 40 |  | 6.5 | 4.3 |
| fury | reaction | 3 | rare | 50 | 37 |  | 7.7 | 5.1 |
| fury | reaction | 3 | epic | 50 | 37 |  | 8.0 | 6.0 |
| fury | reaction | 4 | rare | 50 | 36 |  | 8.5 | 5.8 |
| fury | reaction | 4 | epic | 50 | 36 |  | 8.5 | 6.1 |
| focus | active | 1 | common | 50 | 42 |  | 8.7 | 5.9 |
| focus | active | 1 | rare | 50 | 50 |  | 49.9 | 26.4 |
| focus | active | 1 | epic | 50 | 48 |  | 57.6 | 25.0 |
| focus | active | 2 | common | 50 | 41 |  | 10.6 | 7.3 |
| focus | active | 2 | rare | 50 | 50 |  | 23.9 | 13.7 |
| focus | active | 2 | epic | 50 | 48 |  | 32.6 | 23.1 |
| focus | active | 3 | common | 50 | 41 |  | 10.8 | 7.2 |
| focus | active | 3 | rare | 50 | 50 |  | 19.1 | 15.6 |
| focus | active | 3 | epic | 50 | 48 |  | 26.6 | 20.6 |
| focus | active | 4 | common | 50 | 40 |  | 14.7 | 8.9 |
| focus | active | 4 | rare | 50 | 50 |  | 26.9 | 16.7 |
| focus | active | 4 | epic | 50 | 49 |  | 32.0 | 20.4 |
| focus | passive | 1 | epic | 50 | 46 |  | 7.0 | 5.1 |
| focus | passive | 2 | epic | 50 | 46 |  | 6.9 | 4.2 |
| focus | passive | 3 | epic | 50 | 44 |  | 7.3 | 5.2 |
| focus | passive | 4 | epic | 50 | 45 |  | 8.5 | 5.7 |
| focus | reaction | 1 | rare | 50 | 43 |  | 5.4 | 3.8 |
| focus | reaction | 1 | epic | 50 | 43 |  | 6.2 | 4.4 |
| focus | reaction | 2 | rare | 50 | 40 |  | 6.8 | 4.9 |
| focus | reaction | 2 | epic | 50 | 40 |  | 7.0 | 4.6 |
| focus | reaction | 3 | rare | 50 | 37 |  | 7.7 | 5.7 |
| focus | reaction | 3 | epic | 50 | 37 |  | 8.5 | 6.2 |
| focus | reaction | 4 | rare | 50 | 36 |  | 8.4 | 5.4 |
| focus | reaction | 4 | epic | 50 | 36 |  | 8.5 | 5.8 |
| ki | active | 1 | common | 50 | 42 |  | 8.5 | 6.0 |
| ki | active | 1 | rare | 50 | 47 |  | 54.2 | 16.7 |
| ki | active | 1 | epic | 50 | 49 |  | 66.9 | 34.1 |
| ki | active | 2 | common | 50 | 41 |  | 9.5 | 6.7 |
| ki | active | 2 | rare | 50 | 48 |  | 20.6 | 12.1 |
| ki | active | 2 | epic | 50 | 49 |  | 36.9 | 21.9 |
| ki | active | 3 | common | 50 | 41 |  | 10.6 | 7.8 |
| ki | active | 3 | rare | 50 | 48 |  | 28.9 | 15.4 |
| ki | active | 3 | epic | 50 | 48 |  | 33.1 | 20.4 |
| ki | active | 4 | common | 50 | 40 |  | 14.2 | 10.0 |
| ki | active | 4 | rare | 50 | 48 |  | 26.2 | 20.3 |
| ki | active | 4 | epic | 50 | 49 |  | 36.9 | 21.5 |
| ki | passive | 1 | epic | 50 | 46 |  | 7.1 | 4.5 |
| ki | passive | 2 | epic | 50 | 48 |  | 7.9 | 5.8 |
| ki | passive | 3 | epic | 50 | 46 |  | 8.4 | 6.1 |
| ki | passive | 4 | epic | 50 | 47 |  | 8.3 | 5.6 |
| ki | reaction | 1 | rare | 50 | 43 |  | 6.0 | 3.9 |
| ki | reaction | 1 | epic | 50 | 43 |  | 6.4 | 4.4 |
| ki | reaction | 2 | rare | 50 | 40 |  | 6.9 | 4.3 |
| ki | reaction | 2 | epic | 50 | 40 |  | 7.1 | 4.9 |
| ki | reaction | 3 | rare | 50 | 37 |  | 7.8 | 5.7 |
| ki | reaction | 3 | epic | 50 | 37 |  | 7.7 | 4.9 |
| ki | reaction | 4 | rare | 50 | 36 |  | 8.0 | 6.0 |
| ki | reaction | 4 | epic | 50 | 36 |  | 7.9 | 5.7 |
