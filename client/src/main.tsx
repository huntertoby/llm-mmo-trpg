import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { waitForFonts } from "./render/fontLoad";
import { audio, installAudio } from "./audio";
import { registerSfxLibrary } from "./audio/sfxLibrary";
import { installUiSounds } from "./audio/uiSounds";
import { installMotionPrefs } from "./ui/motionPrefs";
import { documentTitle } from "./ui/gameInfo";
import { isDevMode } from "./run/startFlow";
import { installSmallFrames } from "./ui/smallFrames";
import { installPinBadge } from "./render/hudIcon";
import "./styles/index.css";

document.title = documentTitle(isDevMode(window.location.search)); // UI-E1：遊戲名稱只在 content/ui/game.yaml
installSmallFrames(document); // UI-E1 追加 4：高度 64px 以下的框，四角飾件縮成 70%、內容左右多留 6px
installMotionPrefs(document); // 6H-1：遊戲內「減少動態」的有效值寫到 <html data-reduced-motion>（CSS 用）
installPinBadge(document); // QI-5：釘住的說明卡右上角圓底裡的紅頭圖釘（Q 版 canvas → <html> 的 --float-pin-glyph）

// 排版煙霧檢查（Phase 3-47）：window.__layoutSmoke，docs/開發PM交接.md 6.2 第 5 點。
// I8：dev 工具拆成獨立 chunk，只在 `pnpm dev` 或網址帶 `?dev=1`（正式 build 也可）時才載入，不進主 bundle。
if (import.meta.env.DEV || isDevMode(window.location.search)) {
  void import("./dev/layoutSmoke").then((m) => m.installLayoutSmoke(window));
}
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
