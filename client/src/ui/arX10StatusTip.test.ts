// AR-X10 小修 1（美術 PM `docs/art/X10-3d驗收.md`）：狀態提示的骰子行「擲 NdM，每點 ×10」自己一行、次要字色。
import { describe, expect, it } from "vitest";
import { spreadNote, statusTipParts } from "./StatusCardParts";
import { tipParts } from "./tipParts";

// 沒有 @types/node：同 statusCard.test.ts，用變數名載入 node:fs。
const nodeFs = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };

describe("AR-X10：狀態提示的骰子行", () => {
  it("燃燒：說明與傷害句同一段，骰子行另起一段、次要字色，不加分隔符號", () => {
    expect(statusTipParts("burning", false)).toEqual([
      { text: "身上著火，每回合開始時受到火焰傷害；重複施加時刷新持續時間。 回合開始時受到 10–60 火焰傷害", secondary: false },
      { text: "擲 1d6，每點 ×10", secondary: true },
    ]);
  });
  it("骰子行排在它補充的那句下面；後面還有規則句時另起一段", () => {
    expect(tipParts(["說明", "受到 20–120 雷電傷害", "擲 2d6，每點 ×10", "上限 5 層"])).toEqual([
      { text: "說明 受到 20–120 雷電傷害", secondary: false },
      { text: "擲 2d6，每點 ×10", secondary: true },
      { text: "上限 5 層", secondary: false },
    ]);
  });
  it("沒有骰子行的狀態照舊一段；帶「會擴散」時最後多一行；對照表沒有的寫「狀態」", () => {
    expect(statusTipParts("burning", true).at(-1)).toEqual({ text: spreadNote(), secondary: false });
    expect(statusTipParts("no_such_status", false)).toEqual([{ text: "狀態", secondary: false }]);
    expect(tipParts(["只有說明", ""])).toEqual([{ text: "只有說明", secondary: false }]);
  });
  it("「擲」開頭但不是骰子行的句子不算", () => {
    expect(tipParts(["擲 d1000 決定"]).every((p) => !p.secondary)).toBe(true);
  });
  it("說明卡畫出次要字色的一行（part-tip-secondary：--muted，緊貼上一句）", () => {
    const src = readFileSync("src/ui/PartTip.tsx", "utf8");
    expect(src).toContain("part-tip-secondary");
    const css = readFileSync("src/styles/float-card.css", "utf8");
    expect(css).toMatch(/\.part-tip-text\.part-tip-secondary \{\s*margin-top: 0;\s*color: var\(--muted\);/);
  });
});
