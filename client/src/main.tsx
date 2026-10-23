import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { waitForFonts } from "./render/fontLoad";
import "./styles.css";

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
