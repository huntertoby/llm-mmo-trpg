// 美術 PM 驗收用：用主資料夾 client 的正式畫法，另外允許讀取 worktree 裡的驗收頁（例如 c-field.html）。
// 開法：node <主資料夾>/client/node_modules/vite/bin/vite.js --config <這個檔案的絕對路徑>
// 看頁面：http://127.0.0.1:5183/@fs/<驗收頁的絕對路徑>
import react from "file:///F:/PythonProject/LLM-MMO-TRPG/client/node_modules/@vitejs/plugin-react/dist/index.js";
export default {
  root: "F:/PythonProject/LLM-MMO-TRPG/client",
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5183, strictPort: true, fs: { allow: ["F:/PythonProject/LLM-MMO-TRPG"] } },
};
