import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { waitForFonts } from "./render/fontLoad";
import { installLayoutSmoke } from "./dev/layoutSmoke";
import "./styles/index.css";

installLayoutSmoke(window); // 排版煙霧檢查（Phase 3-47）：window.__layoutSmoke，docs/開發PM交接.md 6.2 第 5 點

const root = document.getElementById("root");
if (root === null) throw new Error("找不到 #root");
// 先等字型（最多 3 秒），畫布文字與圖示快取才不會存到備援字型。
void waitForFonts().then(() => {
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
});
