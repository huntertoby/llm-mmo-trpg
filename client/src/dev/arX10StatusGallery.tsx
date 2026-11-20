// 開發用：AR-X10 狀態提示的骰子行（開 `client/dev/ar-x10-status.html`；自己的 vite 後 /dev/ar-x10-status.html?mute=1）。不屬於正式 build。
// 用正式的戰鬥主角卡 `Hud`（狀態圖示 `StatusBadge` → `PartTip`），主角身上燃燒 2 回合；滑過狀態圖示就是遊戲裡的說明卡。
// 名詞表用前端夾具 `battle/fixtures/glossary.json`（和 /api/glossary 同一份輸出）。畫好後 `document.body.dataset.ready = "1"`。
import { createRoot } from "react-dom/client";
import { flushSync } from "react-dom";
import type { Glossary, StatusView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGlossary } from "../battle/glossary";
import { smallView, unit } from "../battle/testFixtures";
import { waitForFonts } from "../render/fontLoad";
import { installPinBadge } from "../render/hudIcon";
import { Hud } from "../ui/Hud";
import "../styles/index.css";

setGlossary(glossary as unknown as Glossary);
installPinBadge(document);
await waitForFonts();

const burning = { status_id: "burning", remaining: 2, amount: null, source_id: null, cost_status: false } as StatusView;
const hero = unit("unit_0001", "ally", 0, 1, { name_zh: "冒險者", hp: 400, max_hp: 400, mana: 656, max_mana: 672, stamina: 200, max_stamina: 200, ap: 4, statuses: [burning] });
const view = { ...smallView(), units: [hero] };

const title = document.createElement("h2");
title.textContent = "狀態提示：滑過燃燒圖示（正式的 Hud → StatusBadge → PartTip）";
const host = document.createElement("div");
host.className = "host";
document.body.append(title, host);
flushSync(() => createRoot(host).render(<Hud view={view} hero={hero} skills={{}} />));
document.body.dataset.ready = "1";
