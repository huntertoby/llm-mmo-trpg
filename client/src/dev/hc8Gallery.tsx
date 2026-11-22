// 開發用：HC-8 配點教學的範例句（開 `client/dev/hc8-gallery.html`；自己的 vite 後 /dev/hc8-gallery.html?mute=1）。不屬於正式 build。
// 正式的 `AllocateLessonDialog`；規則數字用前端夾具 `battle/fixtures/glossary.json` 的 `rules`（和 /api/glossary 同一份輸出）。
// 教學內容照伺服器的形狀（`world_newcomer_view._allocate_lesson`，點數是量類原值）。成長面板的「升級時每級 +20」看
// /dev/panel-gallery.html?scene=growth&tab=attr。畫好後 `document.body.dataset.ready = "1"`。
import { createRoot } from "react-dom/client";
import { flushSync } from "react-dom";
import type { GameRules, Glossary, WorldLesson } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGameRules, setGlossary } from "../battle/glossary";
import { waitForFonts } from "../render/fontLoad";
import { AllocateLessonDialog } from "../world/OpeningDialog";
import "../styles/index.css";

setGlossary(glossary as unknown as Glossary);
setGameRules((glossary as unknown as { rules: GameRules }).rules);
await waitForFonts();

const lesson = {
  kind: "allocate",
  lines: [
    { speaker_zh: "葛蘭", text_zh: "升級了？身上多了兩點力氣。來，我示範怎麼分。" },
    { speaker_zh: "葛蘭", text_zh: "不知道怎麼配就按「推薦配法」。配錯了也沒關係，在城鎮或營火都能免費重來。" },
  ],
  skills_zh: [],
  points: 20,
  start_points: 40,
  recommended: { int: 20 },
  recommended_zh: "智力 +20",
  notes: [
    { attr: "str", text_zh: "力量：近戰武器的命中與傷害。" },
    { attr: "int", text_zh: "智力：法術的命中與傷害。" },
  ],
  respec: false,
  reminder: false,
} as unknown as WorldLesson;

const host = document.createElement("div");
document.body.append(host);
flushSync(() =>
  createRoot(host).render(
    <AllocateLessonDialog lesson={lesson} affects={[]} onRecommended={() => undefined} onSelf={() => undefined} onSkip={() => undefined} />,
  ),
);
document.body.dataset.ready = "1";
