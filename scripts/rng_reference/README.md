# 亂數參考實作（測試向量產生器）

`rng_vectors.c` 依 Sebastiano Vigna 公開的演算法（[splitmix64](https://prng.di.unimi.it/splitmix64.c)、[xoshiro128\*\*](https://prng.di.unimi.it/xoshiro128starstar.c)）撰寫，用來產生 `tests/shared/test_rng.py` 中的測試向量，確認 `trpg.shared.rng.Rng` 與 C 參考實作逐位元一致。

## 產生的向量

1. splitmix64，seed = 1234567，前 5 個輸出
2. xoshiro128\*\*，直接設定狀態 `(1, 2, 3, 4)`，前 10 個輸出
3. `Rng(seed=42)` 的前 10 個 `next_u32()`（模擬完整播種流程）
4. （額外）`Rng(seed=42).fork("戰鬥")` 子串流的前 5 個 `next_u32()`

## 編譯與執行

需要任一 C99 編譯器（gcc、clang、MSVC 皆可）。編譯產物不要 commit（已列在 `.gitignore`）。

```bash
gcc -std=c99 -O2 -Wall -Wextra -o rng_vectors scripts/rng_reference/rng_vectors.c
./rng_vectors
```

Windows（Visual Studio 開發者命令提示字元）：

```bat
cl /O2 scripts\rng_reference\rng_vectors.c /Fe:rng_vectors.exe
rng_vectors.exe
```

輸出每組以 `#` 開頭的標題行分隔，每行一個十進位數字；把數字貼到 `tests/shared/test_rng.py` 對應的常數即可。
