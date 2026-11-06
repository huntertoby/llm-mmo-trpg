// RT-3b 追加（美術 PM 驗收 6F-7：docs/archive/art/6F-7檢查.md，加上對 6F-7 待決 1、小修 5 的回覆）：
// 戰鬥地圖只讓左欄、工具列所有圖示墊淺色圓底、技能名斷點、代價「・」不留在行尾、戰鬥紀錄跟著左欄收窄、
// 窄視窗室內地圖避開工具列、選取中技能鈕的代價對比、「右鍵」不拆開、反應詢問不留孤字與框底空白。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { hudSideInsets } from "../battle/stageLayout";
import { readSources, readStyleFiles, stripCssComments } from "../test/sourceScan";
import { clampAxis, HUG_GAP } from "../world/camera";
import { HUD_BACKING, HUD_BACKING_R, HUD_BAR_ORDER, HudBarIcon } from "../world/HudBarIcons";
import { keepWords, splitKeepWords } from "./keepWords";
import { BOTTOM_FADE_PX, overflowFlag } from "./PopupFrame";
import { COST_LINE_EM, COST_SEP, costPieces, fitCost, NAME_LINE_EM, NAME_MIN_LINE, NAME_TIGHT_LINE_EM, skillNameLines, textEm } from "./skillCost";
import { SkillName } from "./SkillBar";

const styles = Object.fromEntries(readStyleFiles().map(([p, t]) => [p, stripCssComments(t)]));
const sources = Object.fromEntries(readSources());
function ruleOf(file: string, selector: string): string {
  const text = styles[file] ?? "";
  const re = /([^{}]+)\{([^}]*)\}/g;
  let out = "";
  for (let m = re.exec(text); m !== null; m = re.exec(text)) {
    if (m[1]!.split(",").map((s) => s.trim()).includes(selector)) out += m[2]!;
  }
  return out;
}

/** 照畫面的換行方式排代價（每段不拆、段與段之間換行）：回每一行的字。 */
function rows(pieces: readonly string[], lineEm = COST_LINE_EM): string[] {
  const out: string[] = [];
  let cur = "";
  for (const p of pieces) {
    if (cur !== "" && textEm(cur) + textEm(p) > lineEm) {
      out.push(cur);
      cur = "";
    }
    cur += p;
  }
  if (cur !== "") out.push(cur);
  return out;
}

describe("追加 1：800×600 戰鬥讓開左欄（6F-8 起右欄、上方也讓，見 fix6f8.test.ts）", () => {
  it("左欄照舊讓開", () => {
    expect(hudSideInsets(800).left).toBeGreaterThan(200);
    expect(hudSideInsets(800).right).toBeGreaterThan(200);
  });
});

describe("追加 2／小修 3：工具列所有圖示墊淺色圓底", () => {
  it("每一顆（I K G J Y N R M）最下層都是同一個淺色圓底，圓在 8～40 之內", () => {
    const lum = (parseInt(HUD_BACKING.slice(1, 3), 16) + parseInt(HUD_BACKING.slice(3, 5), 16) + parseInt(HUD_BACKING.slice(5, 7), 16)) / 3;
    expect(lum).toBeGreaterThan(180);
    expect(24 - HUD_BACKING_R).toBeGreaterThanOrEqual(8);
    expect(24 + HUD_BACKING_R).toBeLessThanOrEqual(40);
    for (const k of HUD_BAR_ORDER) {
      const html = renderToStaticMarkup(createElement(HudBarIcon, { k }));
      const first = /<svg[^>]*>(<[a-z]+)/.exec(html)?.[1];
      expect(first, k).toBe("<circle");
      expect(html, k).toContain(`class="hud-bar-backing`);
      expect(html, k).toContain(`fill="${HUD_BACKING}"`);
    }
  });
  it("停用時不透明度 0.6（大世界、鐵匠鋪同一條功能列）", () => {
    expect(ruleOf("styles/world-hud.css", '.world-hud-btn[data-state="disabled"] .hud-bar-icon')).toMatch(/opacity: 0\.6/);
  });
});

describe("必修 1：技能名斷行", () => {
  it("「灰燼與霜雪交織的／鎖鏈陷阱」：斷在「的」後面，最後一行不只剩一個字", () => {
    expect(skillNameLines("灰燼與霜雪交織的鎖鏈陷阱")).toEqual({ lines: ["灰燼與霜雪交織的", "鎖鏈陷阱"], tight: false, cut: false });
    const html = renderToStaticMarkup(createElement(SkillName, { name: "灰燼與霜雪交織的鎖鏈陷阱" }));
    expect(html).toContain('<span class="skill-name-line">鎖鏈陷阱</span>');
    expect(renderToStaticMarkup(createElement(SkillName, { name: "捕獸夾" }))).toBe('<span class="skill-name">捕獸夾</span>');
  });
  it("任何長度：每行放得下、每行至少兩個字；兩行放不下縮字級，再不行加「…」", () => {
    const base = "灰燼與霜雪交織的鎖鏈陷阱之深林獵手古老誓約與雷霆的回聲";
    for (let n = 10; n <= base.length; n++) {
      const name = [...base].slice(0, n).join("");
      const r = skillNameLines(name);
      const em = r.tight ? NAME_TIGHT_LINE_EM : NAME_LINE_EM;
      expect(r.lines.length, name).toBeLessThanOrEqual(2);
      for (const l of r.lines) {
        expect(textEm(l), `${name}：${l}`).toBeLessThanOrEqual(em);
        if (r.lines.length === 2) expect([...l].length, `${name}：${l}`).toBeGreaterThanOrEqual(NAME_MIN_LINE);
      }
      if (r.cut) expect(r.lines[1]!.endsWith("…")).toBe(true);
      else expect(r.lines.join("")).toBe(name);
    }
    expect(skillNameLines(base).cut).toBe(true);
    expect(ruleOf("styles/skill-bar.css", ".skill-button .skill-name.xlong.tight")).toMatch(/font-size: 10px/);
    expect(ruleOf("styles/skill-bar.css", ".skill-button .skill-name.xlong .skill-name-line")).toMatch(/white-space: nowrap/);
  });
  it("代價換成兩行：換行點在「・」之前，行尾不留「・」", () => {
    const parts = ["AP 2", "法力 6", "冷卻 3 回合"];
    const pieces = costPieces(fitCost(parts, 2));
    expect(pieces).toEqual(["AP 2", "・法力 6", "・冷卻 3 回合"]);
    const pool = ["AP 1", "AP 3", "法力 12", "耐力 8", "HP 10%", "冷卻 4 回合", "每場 2 次", "源力 2", "傳說啟動"];
    for (let mask = 1; mask < 1 << pool.length; mask += 5) {
      const ps = pool.filter((_, i) => (mask >> i) & 1);
      for (const lines of [1, 2]) {
        const rs = rows(costPieces(fitCost(ps, lines)));
        expect(rs.length, rs.join("|")).toBeLessThanOrEqual(lines);
        for (const r of rs) expect(r.endsWith(COST_SEP), rs.join("|")).toBe(false);
      }
    }
  });
});

describe("必修 2：戰鬥紀錄跟著左欄收窄", () => {
  it("紀錄、每一條、展開的清單最寬都是左欄寬", () => {
    expect(ruleOf("styles/battle-hud.css", ".battle-screen.hud-a .log-dock")).toMatch(/max-width: var\(--hud-left-w\)/);
    for (const sel of [".battle-screen.hud-a .log-dock > .log-toasts", ".battle-screen.hud-a .log-dock .log-toast", ".battle-screen.hud-a .log-dock .log-dock-panel"]) {
      expect(ruleOf("styles/battle-hud.css", sel), sel).toMatch(/max-width: var\(--hud-left-w\)/);
    }
  });
});

describe("小修 4：窄視窗的室內地圖避開工具列", () => {
  it("比安全區大、但工具列上方放得下：下緣貼在工具列上方（往上對齊）", () => {
    // 800×600 鐵匠鋪：舞台 530、房間 412、上方主角卡 160、下方工具列 44
    const y = clampAxis(530, 412, 250, 160, 44, 24);
    expect(-y + 412).toBe(530 - 44 - HUG_GAP); // 房間下緣在工具列上方，留 HUG_GAP
    expect(-y).toBeGreaterThanOrEqual(0);
    // 空間不夠留 HUG_GAP：少留，但下緣不超過工具列
    expect(-clampAxis(530, 480, 300, 160, 44, 24) + 480).toBeLessThanOrEqual(530 - 44);
    // 主角在房間中下段走動時鏡頭不動（不再捲到工具列底下）
    expect(clampAxis(530, 412, 380, 160, 44, 24)).toBe(y);
    // 主角走到房間最上面、貼齊後會跑進主角卡那一帶：照舊跟著主角（6F-3：主角一定在安全區裡）
    const top = clampAxis(530, 412, 40, 160, 44, 24);
    expect(40 - top - 24).toBeGreaterThanOrEqual(160);
  });
  it("放得進安全區照舊置中；比畫面大照舊跟著主角", () => {
    expect(clampAxis(530, 200, 100, 160, 44)).toBe(-(160 + (530 - 204 - 200) / 2));
    expect(clampAxis(530, 1200, 600, 160, 44)).not.toBe(clampAxis(530, 1200, 900, 160, 44));
    expect(clampAxis(1000, 600, 0)).toBe(-200);
  });
});

describe("小修 5：選取中的技能鈕代價看得清楚", () => {
  const lin = (c: number): number => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  const lumOf = (hex: string): number => 0.2126 * lin(parseInt(hex.slice(1, 3), 16)) + 0.7152 * lin(parseInt(hex.slice(3, 5), 16)) + 0.0722 * lin(parseInt(hex.slice(5, 7), 16));
  const contrast = (a: string, b: string): number => {
    const [x, y] = [lumOf(a), lumOf(b)].sort((p, q) => q - p) as [number, number];
    return (x + 0.05) / (y + 0.05);
  };
  it("淺色字在選取的藍底上對比 ≥ 4.5（原本灰字約 2.4）", () => {
    const color = /color: (#[0-9a-f]{6})/.exec(ruleOf("styles/skill-bar.css", ".skill-button.selected .skill-cost"))?.[1] ?? "";
    const bg = /background: (#[0-9a-f]{6})/.exec(ruleOf("styles/base.css", "button.selected"))?.[1] ?? "";
    expect(bg).toBe("#3d5a99");
    expect(contrast(color, bg)).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#9a98a6", bg)).toBeLessThan(3);
  });
});

describe("小修 6：「右鍵」這類操作詞不拆成兩行", () => {
  it("包成不換行的小段；其他字照常可以換行", () => {
    expect(splitKeepWords("Esc／右鍵取消。")).toEqual(["", "Esc／右鍵", "取消。"]); // 6F-9：「Esc／右鍵」整組不拆
    expect(splitKeepWords("右鍵或 Esc 取消。")).toEqual(["", "右鍵", "或 ", "Esc", " 取消。"]);
    const html = renderToStaticMarkup(createElement("div", null, keepWords("點選格子。Esc／右鍵取消。")));
    expect(renderToStaticMarkup(createElement("div", null, keepWords("按右鍵取消。")))).toContain('<span class="keep-word">右鍵</span>');
    expect(html).toContain('<span class="keep-word">Esc／右鍵</span>');
    expect(keepWords("沒有操作詞")).toBe("沒有操作詞");
    expect(ruleOf("styles/base.css", ".keep-word")).toMatch(/white-space: nowrap/);
    for (const f of ["ui/OpHint.tsx", "ui/PartTip.tsx", "ui/SkillBar.tsx"]) expect(sources[f], f).toContain("keepWords(");
  });
});

describe("小修 7：反應詢問不留孤字、框底沒有多餘空白", () => {
  it("說明句不留孤字（6F-8 起反應詢問的段落改成 balance，見 fix6f8.test.ts）", () => {
    expect(ruleOf("styles/base.css", ".decision-card p")).toMatch(/text-wrap: (pretty|balance)/);
  });
  it("內容沒有超出時，下緣漸隱高度 0（原本固定 32px 空白）；量的時候扣掉漸隱自己", () => {
    expect(overflowFlag(200, 300, false)).toBe("0");
    expect(overflowFlag(400, 300, false)).toBe("1");
    expect(overflowFlag(300 + BOTTOM_FADE_PX, 300, true)).toBe("0"); // 只是漸隱自己撐出來的：不算超出
    expect(overflowFlag(301 + BOTTOM_FADE_PX + 1, 300, true)).toBe("1");
    expect(ruleOf("styles/theme.css", '.ui-popup-dialog > .ui-popup-body:not([data-overflow="1"])::after')).toMatch(/height: 0/);
    expect(sources["ui/PopupFrame.tsx"]).toMatch(/<div ref=\{body\} className="ui-popup-body"/);
  });
});
