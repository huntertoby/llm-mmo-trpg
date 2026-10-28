// Phase 3-54d：工坊的「預覽武器」下拉（06 6.10）
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CheckPanel, type PreviewWeapon } from "./CheckPanel";

const weapons = [
  { id: "longsword", name_zh: "長劍", weapon_class: "melee", class_zh: "近戰武器" },
  { id: "shortbow", name_zh: "短弓", weapon_class: "ranged", class_zh: "遠程武器" },
];

function html(value: string): string {
  const preview: PreviewWeapon = { weapons, value, onChange: () => {} };
  return renderToStaticMarkup(createElement(CheckPanel, { check: null, pending: false, preview }));
}

describe("預覽武器下拉", () => {
  it("第一個選項是「不指定（列例子）」，其後是全部武器", () => {
    const out = html("");
    expect(out).toContain("預覽武器");
    expect(out.indexOf("不指定（列例子）")).toBeLessThan(out.indexOf("長劍（近戰武器）"));
    expect(out).toContain("短弓（遠程武器）");
  });
  it("從首頁開（沒有主角）預設不指定；從一輪開預設主角主手武器", () => {
    expect(html("")).toMatch(/<option value="" selected="">/);
    expect(html("longsword")).toMatch(/<option value="longsword" selected="">/);
  });
  it("沒傳 preview 時不顯示下拉", () => {
    expect(renderToStaticMarkup(createElement(CheckPanel, { check: null, pending: false }))).not.toContain("預覽武器");
  });
});
