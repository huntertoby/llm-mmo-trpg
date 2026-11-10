/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// 開發時 `pnpm -C client dev`：/api 轉到本機 API（先在另一個終端機執行 `uv run trpg serve`）。
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
    setupFiles: ["src/test/setup.ts"],
    // 全組合自測與原始碼掃描在完整平行跑、機器同時有其他工作時常超過預設 5 秒
    testTimeout: 30_000,
    // PERF-4b：pixi.js 預先打包成單檔，每個測試檔不必各自載入幾百個小模組。只影響 vitest，`vite build` 不讀 test 區塊。
    deps: { optimizer: { ssr: { enabled: true, include: ["pixi.js"] } } },
  },
});
