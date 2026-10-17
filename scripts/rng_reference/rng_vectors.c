/*
 * 亂數測試向量參考程式（Phase 0）。
 *
 * 依 Sebastiano Vigna 公開的演算法撰寫：
 *   - splitmix64:   https://prng.di.unimi.it/splitmix64.c
 *   - xoshiro128**: https://prng.di.unimi.it/xoshiro128starstar.c
 *
 * 輸出規格要求的三組向量（1–3）與一組額外向量（4），供 tests/shared/test_rng.py 使用：
 *   1. splitmix64，seed = 1234567，前 5 個輸出
 *   2. xoshiro128**，狀態 (1, 2, 3, 4)，前 10 個輸出
 *   3. Rng(seed=42) 完整播種流程（splitmix64 產生兩個 64 位元數，
 *      第一個的低／高 32 位元為 s0／s1，第二個的低／高 32 位元為 s2／s3）
 *      後的前 10 個 next_u32()
 *   4. （額外）Rng(seed=42).fork("戰鬥") 子串流的前 5 個 next_u32()
 *      fork 做法：x = fnv1a64(label 的 UTF-8)；對父狀態 s0..s3 依序 x = splitmix64_out(x ^ w)；
 *      再以 x 為種子走一次完整播種流程。父狀態取自 Rng(42) 剛播種完、尚未抽數時。
 *
 * 編譯與執行方式見同資料夾的 README.md。
 */
#include <inttypes.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>

/* ---- splitmix64 ---- */
static uint64_t sm_x;

static uint64_t splitmix64_next(void) {
    uint64_t z = (sm_x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

/* ---- xoshiro128** ---- */
static uint32_t s[4];

static inline uint32_t rotl(const uint32_t x, int k) {
    return (x << k) | (x >> (32 - k));
}

static uint32_t xoshiro128ss_next(void) {
    const uint32_t result = rotl(s[1] * 5, 7) * 9;
    const uint32_t t = s[1] << 9;

    s[2] ^= s[0];
    s[3] ^= s[1];
    s[1] ^= s[2];
    s[0] ^= s[3];

    s[2] ^= t;

    s[3] = rotl(s[3], 11);

    return result;
}

/* ---- FNV-1a 64 ---- */
static uint64_t fnv1a64(const unsigned char *data, size_t len) {
    uint64_t h = 0xcbf29ce484222325ULL;
    size_t i;
    for (i = 0; i < len; i++) {
        h ^= data[i];
        h *= 0x00000100000001b3ULL;
    }
    return h;
}

/* 以 seed 走完整播種流程，設定 s[0..3]。 */
static void seed_state(uint64_t seed) {
    uint64_t a, b;
    sm_x = seed;
    a = splitmix64_next();
    b = splitmix64_next();
    s[0] = (uint32_t)(a & 0xFFFFFFFFULL);
    s[1] = (uint32_t)(a >> 32);
    s[2] = (uint32_t)(b & 0xFFFFFFFFULL);
    s[3] = (uint32_t)(b >> 32);
    /* 全零狀態保護（與 Python 實作相同的替代常數） */
    if (s[0] == 0 && s[1] == 0 && s[2] == 0 && s[3] == 0) {
        s[0] = 0x9E3779B9U; s[1] = 0x243F6A88U; s[2] = 0xB7E15162U; s[3] = 0x6A09E667U;
    }
}

int main(void) {
    int i;

    printf("# splitmix64 seed=1234567 first 5\n");
    sm_x = 1234567ULL;
    for (i = 0; i < 5; i++) {
        printf("%" PRIu64 "\n", splitmix64_next());
    }

    printf("# xoshiro128** state=(1,2,3,4) first 10\n");
    s[0] = 1; s[1] = 2; s[2] = 3; s[3] = 4;
    for (i = 0; i < 10; i++) {
        printf("%" PRIu32 "\n", xoshiro128ss_next());
    }

    printf("# Rng(seed=42) first 10 next_u32\n");
    seed_state(42ULL);
    for (i = 0; i < 10; i++) {
        printf("%" PRIu32 "\n", xoshiro128ss_next());
    }

    printf("# Rng(seed=42).fork(\"\xe6\x88\xb0\xe9\xac\xa5\") first 5 next_u32\n");
    {
        /* "戰鬥" 的 UTF-8 位元組 */
        static const unsigned char label[] = {0xe6, 0x88, 0xb0, 0xe9, 0xac, 0xa5};
        uint32_t parent[4];
        uint64_t x;
        int k;
        seed_state(42ULL);
        for (k = 0; k < 4; k++) {
            parent[k] = s[k];
        }
        x = fnv1a64(label, sizeof label);
        for (k = 0; k < 4; k++) {
            sm_x = x ^ (uint64_t)parent[k];
            x = splitmix64_next();
        }
        seed_state(x);
        for (i = 0; i < 5; i++) {
            printf("%" PRIu32 "\n", xoshiro128ss_next());
        }
    }
    return 0;
}
