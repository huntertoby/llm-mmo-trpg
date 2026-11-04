import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { waitForFonts } from "./render/fontLoad";
import { installLayoutSmoke } from "./dev/layoutSmoke";
import { audio, installAudio } from "./audio";
import { registerSfxLibrary } from "./audio/sfxLibrary";
import { installUiSounds } from "./audio/uiSounds";
import "./styles/index.css";

installLayoutSmoke(window); // 排版煙霧檢查（Phase 3-47）：window.__layoutSmoke，docs/開發PM交接.md 6.2 第 5 點
installAudio(window, document); // AU-1：第一次點擊或按鍵才解鎖音訊、Shift＋M 全部靜音、背景分頁靜音
registerSfxLibrary(audio); // AU-2：content/audio/sfx.yaml 的合成音
installUiSounds(document); // AU-2：按鈕、開關、確認、取消等點擊介面音

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
