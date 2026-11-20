// X10-3b 第 4 項：範圍一律用短橫線「–」（U+2013）——卡片（伺服器給的 `stats.effects[].label`）、技能列（同一張卡）、
// 戰鬥預覽（`previewText.ts` 的 `damageText`）三處同一種，不混用「-」「～」「~」。
import { describe, expect, it } from "vitest";
import type { PreviewOut } from "../api/types";
import { damageText } from "../battle/previewText";
import cards from "./fixtures/skillCards.json";

const DASH = "–";
type Damage = NonNullable<PreviewOut["damage"]>;

describe("範圍的連接號", () => {
  it("戰鬥預覽的範圍用「–」", () => {
    const d = { minimum: 130, maximum: 1060, expected_milli: 595000 } as Damage;
    expect(damageText(d).startsWith(`130${DASH}1060`)).toBe(true);
  });

  it("卡片與技能列的範圍用同一個「–」，不寫骰子", () => {
    const labels = Object.values(cards).flatMap((c) => (c as { stats: { effects: { label: string | null }[] } }).stats.effects.map((e) => e.label ?? ""));
    const ranges = labels.filter((l) => /^\d+\D\d+$/.test(l));
    expect(ranges.length).toBeGreaterThan(0);
    for (const label of ranges) expect(label).toMatch(new RegExp(`^\\d+${DASH}\\d+$`));
    for (const label of labels) expect(label).not.toMatch(/\d+d\d+/);
  });
});
