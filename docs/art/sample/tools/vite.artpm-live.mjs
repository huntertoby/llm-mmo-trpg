// 美術 PM 驗收實戰用的 vite 設定：用主資料夾 client 的程式與 node_modules，/api 轉到 8012 的 trpg serve。
// 8000（使用者）、8001（本機 LLM）不要用（CLAUDE.md 守則 13）。
// 用法：.claude/launch.json 加兩個設定
//   api-8012：uv run trpg serve --port 8012
//   client-live-5182：node <主資料夾>/client/node_modules/vite/bin/vite.js --config <這個檔案的絕對路徑>
import react from "file:///F:/PythonProject/LLM-MMO-TRPG/client/node_modules/@vitejs/plugin-react/dist/index.js";
export default {
  root: "F:/PythonProject/LLM-MMO-TRPG/client",
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5182, strictPort: true, proxy: { "/api": "http://127.0.0.1:8012" } },
};
