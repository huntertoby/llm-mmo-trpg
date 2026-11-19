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

// AP-2（#168）：預支技能——橘色菱形（預支來的那格）、紅斜線（下回合會少的那格）與用字（畫法文件第 2、3、5 節）。
describe("AP 列的預支", () => {
  it("施放預支後：4 顆金＋1 顆橘菱形｜1 顆紅斜線，用字照第 5 節", () => {
    const row = apRow(hero({ ap: 5, ap_borrowed: 1, ap_next_loss: 1, ap_next_loss_borrowed: 1 }), "AP");
    expect(row.now.map((p) => `${p.kind}${p.on ? "+" : "-"}`)).toEqual(["ap+", "ap+", "ap+", "ap+", "borrow+"]);
    expect(row.now[4]).toMatchObject({ hint: "預支來的 AP（下回合 −1）", fresh: true });
    expect(row.next.map((p) => [p.kind, p.hint, p.fresh])).toEqual([["lost", "預支：下回合少 1 AP", true]]);
  });
  it("預支的那格最先用掉、變空心橘框；用了預支的回合沒有會被保留的那顆", () => {
    const row = apRow(hero({ ap: 2, ap_borrowed: 1, ap_next_loss: 1, ap_next_loss_borrowed: 1 }), "AP");
    expect(row.now.map((p) => `${p.kind}${p.on ? "+" : "-"}`)).toEqual(["ap+", "ap+", "ap-", "ap-", "borrow-"]);
    expect(row.now.some((p) => p.keep)).toBe(false);
  });
  it("預支 +2：兩顆菱形｜兩顆紅斜線，合計 2 格以上寫合計", () => {
    const row = apRow(hero({ ap: 6, ap_borrowed: 2, ap_next_loss: 2, ap_next_loss_borrowed: 2 }), "AP");
    expect(row.now.filter((p) => p.kind === "borrow")).toHaveLength(2);
    expect(row.now[4]?.hint).toBe("預支來的 AP（下回合 −2）");
    expect(row.next.map((p) => p.hint)).toEqual(["下回合少 2 AP", "下回合少 2 AP"]);
  });
  it("和透支疊加：下回合 −2 兩顆紅斜線寫合計；只有透支 1 格照舊寫透支", () => {
    const both = apRow(hero({ ap: 5, ap_borrowed: 1, ap_next_loss: 2, ap_next_loss_borrowed: 1 }), "AP").next;
    expect(both.map((p) => p.hint)).toEqual(["下回合少 2 AP", "下回合少 2 AP"]);
    const over = apRow(hero({ ap: 2, ap_next_loss: 1 }), "AP").next;
    expect(over.map((p) => p.hint)).toEqual(["透支：下回合少 1 AP"]);
  });
  it("回合開始已扣掉的那格：只有預支、只有透支、兩者疊加（不寫原因）", () => {
    const hint = (lost: number, borrowed: number) => apRow(hero({ ap: 4 - lost, ap_lost: lost, ap_lost_borrowed: borrowed }), "AP").now.find((p) => p.kind === "lost")?.hint;
    expect(hint(1, 1)).toBe("預支：這回合少 1 AP");
    expect(hint(2, 2)).toBe("預支：這回合少 2 AP");
    expect(hint(1, 0)).toBe("透支：這回合少 1 AP");
    expect(hint(2, 1)).toBe("這回合少 2 AP");
  });
  it("菱形、紅斜線各最多畫 2 個（多的寫在說明裡）", () => {
    const row = apRow(hero({ ap: 5, ap_lost: 3, ap_lost_borrowed: 1, ap_next_loss: 3, ap_next_loss_borrowed: 2 }), "AP");
    expect(row.now.filter((p) => p.kind === "lost")).toHaveLength(2);
    expect(row.next).toHaveLength(2);
    expect(row.next[0]?.hint).toBe("下回合少 3 AP");
  });
  it("畫法：菱形有自己的 class、淡入 200 ms；改寫數字時字至少 10px", () => {
    const html = renderToStaticMarkup(createElement(StatChipView, { chip: apChip(hero({ ap: 5, ap_borrowed: 1, ap_next_loss: 1, ap_next_loss_borrowed: 1 })) }));
    expect(html).toContain('class="stat-pip ap borrow on fresh"');
    expect(html).toContain('aria-label="預支來的 AP（下回合 −1）"');
    const css = readFileSync("src/styles/status-card.css", "utf8");
    expect(css).toMatch(/\.stat-pip\.ap\.borrow \{[^}]*border-color: #b8641a;[^}]*transform: rotate\(45deg\);/);
    expect(css).toMatch(/\.stat-pip\.ap\.borrow\.on \{[^}]*background: #ff9a3a;/);
    expect(css).toMatch(/\.stat-pip\.ap\.fresh \{[^}]*animation: ap-borrow-in 0\.2s/);
    const size = /\.stat-chip \{[^}]*font-size: (\d+)px;/.exec(css)?.[1];
    expect(Number(size)).toBeGreaterThanOrEqual(10);
    const many = apChip(hero({ ap: 9, ap_carried_in: 1, ap_borrowed: 2, ap_next_loss: 2 }));
    expect(many.label).toBe("9");
  });
});
