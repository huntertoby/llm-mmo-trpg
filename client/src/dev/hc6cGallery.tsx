// 開發用：HC-6c 說明卡的骰子行（開 `client/dev/hc6c-gallery.html`；自己的 vite 後 /dev/hc6c-gallery.html?mute=1）。不屬於正式 build。
// - 上：正式的戰鬥主角卡 `Hud`，主角站在毒表面上（腳下表面 `SurfaceBadge` → `PartTip`）；
// - 下：技能工坊組裝列的部件小圖 `OptionGlyph`（狀態「燃燒」→ `statusTile`、表面「毒」→ `surfaceTile` 的說明框）。
// 名詞表用前端夾具 `battle/fixtures/glossary.json`（和 /api/glossary 同一份輸出）。畫好後 `document.body.dataset.ready = "1"`。
import { createRoot } from "react-dom/client";
import { flushSync } from "react-dom";
import type { GameRules, Glossary } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGameRules, setGlossary } from "../battle/glossary";
import { smallView, tile, unit } from "../battle/testFixtures";
import { waitForFonts } from "../render/fontLoad";
import { installPinBadge } from "../render/hudIcon";
import { Hud } from "../ui/Hud";
import { OptionGlyph } from "../ui/SkillIconView";
import "../styles/index.css";

setGlossary(glossary as unknown as Glossary);
setGameRules((glossary as unknown as { rules: GameRules }).rules);
installPinBadge(document);
await waitForFonts();

const hero = unit("unit_0001", "ally", 0, 1, { name_zh: "冒險者", hp: 400, max_hp: 400, mana: 656, max_mana: 672, stamina: 200, max_stamina: 200, ap: 4, statuses: [] });
const base = smallView();
const tiles = base.tiles.map((t) => (t.x === 0 && t.y === 1 ? tile(0, 1, { surface: "poison", surface_remaining: 3 }) : t));
const view = { ...base, tiles, units: [hero] };


const title = document.createElement("h2");
title.textContent = "腳下表面：滑過毒表面圖示（正式的 Hud → SurfaceBadge → PartTip）";
const host = document.createElement("div");
host.className = "host";
const title2 = document.createElement("h2");
title2.textContent = "組裝列：滑過狀態「燃燒」、表面「毒」的部件（正式的 OptionGlyph → PartTip）";
const formula = document.createElement("div");
formula.className = "formula-host";
document.body.append(title, host, formula);
formula.before(title2);
flushSync(() => createRoot(host).render(<Hud view={view} hero={hero} skills={{}} />));
flushSync(() =>
  createRoot(formula).render(
    <div style={{ display: "flex", gap: 24 }}>
      <span data-testid="opt-status">
        <OptionGlyph field="status" value="burning" />
      </span>
      <span data-testid="opt-surface">
        <OptionGlyph field="surface" value="poison" />
      </span>
    </div>,
  ),
);
document.body.dataset.ready = "1";
