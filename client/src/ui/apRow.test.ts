// AP-1（#168）：AP 列——上回合保留的那格（米白環）、少掉的那格（紅斜線）、分隔線、每顆自己的說明、
// 滑過「結束回合」時會被保留的那顆。畫法與用字見 docs/art/AP-1-AP列畫法.md。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { UnitView } from "../api/types";
import { unit } from "../battle/testFixtures";
import { StatChipView } from "./StatusCardParts";
import { AP_PIP_TEXT, apChip, apRow, heroChips, unitChips } from "./statusCard";

const nodeFs = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };

const hero = (over: Partial<UnitView>): UnitView => unit("unit_0001", "ally", 0, 0, { ap_per_turn: 4, ap_max: 5, ...over });
const kinds = (u: UnitView) => apRow(u, "AP").now.map((p) => `${p.kind}${p.on ? "+" : "-"}`);

describe("AP 列的圓點", () => {
  it("一般 4 AP：4 顆金，用掉的空心", () => {
    expect(kinds(hero({ ap: 4 }))).toEqual(["ap+", "ap+", "ap+", "ap+"]);
    expect(kinds(hero({ ap: 1 }))).toEqual(["ap+", "ap-", "ap-", "ap-"]);
  });
  it("上回合保留了 1 格：共 5 顆，最後一顆有米白環；用掉時保留的那格先變空心、環還在", () => {
    expect(kinds(hero({ ap: 5, ap_carried_in: 1 }))).toEqual(["ap+", "ap+", "ap+", "ap+", "kept+"]);
    const used = apRow(hero({ ap: 4, ap_carried_in: 1 }), "AP").now;
    expect(used.at(-1)).toMatchObject({ kind: "kept", on: false, hint: AP_PIP_TEXT.kept });
  });
  it("透支後的下一回合：3 顆金＋1 顆紅斜線在一般 AP 的最後", () => {
    expect(kinds(hero({ ap: 3, ap_lost: 1 }))).toEqual(["ap+", "ap+", "ap+", "lost-"]);
    expect(kinds(hero({ ap: 4, ap_lost: 1, ap_carried_in: 1 }))).toEqual(["ap+", "ap+", "ap+", "lost-", "kept+"]);
    expect(apRow(hero({ ap: 3, ap_lost: 1 }), "AP").now[3]?.hint).toBe(AP_PIP_TEXT.lostNow(1));
  });
  it("下回合會少的：分隔線右邊，1 格寫透支、2 格以上寫合計", () => {
    const one = apRow(hero({ ap: 2, ap_next_loss: 1 }), "AP").next;
    expect(one.map((p) => [p.kind, p.hint])).toEqual([["lost", "透支：下回合少 1 AP"]]);
    const two = apRow(hero({ ap: 2, ap_next_loss: 2 }), "AP").next;
    expect(two.map((p) => p.hint)).toEqual(["下回合少 2 AP", "下回合少 2 AP"]);
  });
  it("被給、被返還多出來的 AP 接在一般 AP 後面", () => {
    expect(kinds(hero({ ap: 5 }))).toEqual(["ap+", "ap+", "ap+", "ap+", "ap+"]);
  });
  it("會被保留的那顆＝還沒用的最後一顆（保留上限 1）", () => {
    const pips = apRow(hero({ ap: 2 }), "AP").now;
    expect(pips.map((p) => p.keep)).toEqual([false, true, false, false]);
    expect(apRow(hero({ ap: 0 }), "AP").now.some((p) => p.keep)).toBe(false);
  });
  it("一般 AP 的說明照舊；主角卡畫圓點、單位小卡只寫數字", () => {
    const chip = apChip(hero({ ap: 3 }));
    expect(chip.apRow?.now[0]?.hint).toBe(chip.hint);
    expect(heroChips(hero({ ap: 3 }))[0]?.pips).toEqual([true, true, true, false]);
    const small = unitChips(hero({ ap: 3 })).find((c) => c.key === "ap");
    expect(small).toMatchObject({ label: "3", pips: null });
    expect(small?.apRow).toBeUndefined();
  });
});

describe("AP 列的畫法", () => {
  it("每顆圓點各有說明；保留、紅斜線有自己的 class；有下回合會少的才畫分隔線", () => {
    const html = renderToStaticMarkup(createElement(StatChipView, { chip: apChip(hero({ ap: 5, ap_carried_in: 1, ap_next_loss: 2 })) }));
    expect(html).toContain('class="stat-pip ap kept on keep"');
    expect(html).toContain('aria-label="上回合保留的 AP"');
    expect(html.match(/data-ap-pip="lost"/g)).toHaveLength(2);
    expect(html).toContain("stat-pip-sep");
    const plain = renderToStaticMarkup(createElement(StatChipView, { chip: apChip(hero({ ap: 4 })) }));
    expect(plain).not.toContain("stat-pip-sep");
    expect(plain.match(/class="stat-pip ap/g)).toHaveLength(4);
  });
  it("CSS：米白環 1px 隔 1px、紅斜線、分隔線 1×9、滑過結束回合閃 0.6 秒 2 次", () => {
    const css = readFileSync("src/styles/status-card.css", "utf8");
    expect(css).toMatch(/\.stat-pip\.ap\.kept \{[^}]*--keep-ring: #f2e6c8;[^}]*outline-offset: 1px;/);
    expect(css).toMatch(/\.stat-pip\.ap\.lost \{[^}]*#e05a4a[^}]*opacity: 0\.8;/);
    expect(css).toMatch(/\.stat-pip-sep \{[^}]*width: 1px;[^}]*height: 9px;[^}]*background: #8a7a5a;/);
    expect(css).toContain("body:has(.end-turn-button:hover:not(:disabled)) .stat-pip.ap.keep");
    expect(css).toMatch(/animation: ap-keep-flash 0\.6s ease-in-out 2;/);
  });
});
