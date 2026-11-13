// RG-4（docs/art/RG樣張.md 9.6 決定 3、9.8 第 4～7 條）：精英單挑插圖 A 暮色對峙的接線與對話框按鈕。
// 插圖的像素在開發頁 `dev/duel-gallery.html?mode=diff` 和樣張逐像素比對（node 沒有畫布，這裡只鎖資料與標記）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { WorldView } from "../api/types";
import { CREATURE_ELITE_K_DEFAULT, duelRegion } from "../render/duelArt";
import { gearKinds } from "../render/gearResolve";
import { BEAST_CLAW } from "../render/qIcon/beastClaw";
import { hasQWeaponArt, Q_WEAPON_KINDS } from "../render/qIcon/weapons";
import { duelPlan } from "./duelArtPlan";
import { EncounterPanel } from "./WorldPanel";
import { readFile, SRC_DIR } from "../test/sourceScan";

const HERO = { template_id: "hero", doll_look: null, weapon_id: "one_handed_sword", weapon_class: "melee", race_look: null, equipment: [] };
const creatureLook = (creature: Record<string, unknown>) => ({ template_id: "x", doll_look: { creature, affixes: [] }, weapon_id: "fang", weapon_class: "melee", race_look: null, equipment: [] });
const WOLF = creatureLook({ body: "hound", material: "fur", size: "large", traits: ["mist"] });
const LORD = creatureLook({ body: "crawler", variant: "beetle", material: "magma", size: "large", traits: ["lava_pool"] });
const OOZE = creatureLook({ body: "ooze", material: "mist", size: "large" });
const BANDIT = {
  template_id: "bandit_captain",
  doll_look: { skin: "#a8724c", hair: "short", gear: { head: { kind: "bandana", material: "cloth", color: "#ff6a1a" }, body: { kind: "mail", material: "iron" } } },
  weapon_id: "shotgun",
  weapon_class: "ranged",
  race_look: null,
  equipment: [{ slot: "main_hand", appearance: { kind: "shotgun", form: "double", material: "iron", rarity: "common", keywords: [] } }],
};

function view(opts: { elite?: unknown; region?: string; hero?: unknown; duel?: string | null } = {}): WorldView {
  return {
    character: { hero_look: opts.hero === undefined ? HERO : opts.hero },
    map: { region: opts.region ?? "cloud_ridge" },
    encounter: {
      location: "north_slope",
      location_name_zh: "北坡",
      enemy_level: 3,
      map_name_zh: "雪坡",
      weather_zh: "晴",
      day_phase_zh: "白天",
      enemies: [
        { name_zh: "雪狼", elite: false, affix_zh: null, rank: "normal", look: WOLF },
        { name_zh: "北坡狼王", elite: true, affix_zh: null, rank: "elite", look: opts.elite === undefined ? WOLF : opts.elite },
      ],
      retreat_to_zh: "霧渡鎮",
      fatigued: false,
      hero_hp: 60,
      in_battle: false,
      reinforcements: 0,
      hero_statuses: [],
      opening_zh: [],
      allies_zh: "主角（開場 HP 60）",
      battlefield_fallback_zh: null,
      duel: opts.duel === undefined ? "offered" : opts.duel,
      duel_zh: "兩邊獎勵一樣。",
    },
  } as unknown as WorldView;
}
const html = (v: WorldView): string => renderToStaticMarkup(createElement(EncounterPanel, { view: v, busy: false, onAct: () => undefined, onBattle: () => undefined }));
const duelPart = (out: string): string => out.slice(out.indexOf('data-testid="world-duel"'), out.indexOf('data-testid="world-fight"'));

describe("duel dialog buttons (9.8 #7)", () => {
  it("accept and decline are plain buttons of the same class, accept first, no primary, no autofocus", () => {
    const part = duelPart(html(view()));
    const accept = part.indexOf('data-testid="world-duel-accept"');
    const decline = part.indexOf('data-testid="world-duel-decline"');
    expect(accept).toBeGreaterThan(0);
    expect(decline).toBeGreaterThan(accept);
    const buttons = part.match(/<button[^>]*>/g) ?? [];
    expect(buttons).toHaveLength(2);
    for (const b of buttons) {
      expect(b).toContain('type="button"');
      expect(b).toContain('class="duel-choice"');
      expect(b).not.toContain("primary");
      expect(b.toLowerCase()).not.toContain("autofocus");
    }
  });

  it("the duel section itself takes focus (tabIndex -1)", () => {
    const out = html(view());
    expect(out).toMatch(/<div class="duel-dialog"[^>]*tabindex="-1"/);
    const src = readFile(SRC_DIR, "world/WorldPanel.tsx");
    const dialog = src.slice(src.indexOf("function DuelDialog"), src.indexOf("export function duelEliteName"));
    expect(dialog).not.toMatch(/autoFocus/);
    expect(dialog).not.toMatch(/className="primary"/);
  });

  it("CSS: both buttons share one min-width of 96px", () => {
    const css = readFile(SRC_DIR, "styles/world.css");
    expect(css).toMatch(/\.duel-choices > \.duel-choice \{\s*min-width: 96px;/);
  });
});

describe("duel illustration wiring (9.8 #3)", () => {
  it("draws the art under the title when the elite has a look", () => {
    const part = duelPart(html(view()));
    expect(part).toContain('data-testid="world-duel-art"');
    expect(part.indexOf("要求一對一")).toBeLessThan(part.indexOf("world-duel-art"));
    expect(part.indexOf("world-duel-art")).toBeLessThan(part.indexOf("兩邊獎勵一樣"));
  });

  it("no art without the elite's look or the hero's look", () => {
    expect(duelPart(html(view({ elite: null })))).not.toContain("world-duel-art");
    expect(duelPlan(view({ hero: null }))).toBeNull();
  });

  it("a creature elite crosses the hero's sword with the beast claw, scaled per body", () => {
    const wolf = duelPlan(view())!;
    expect(wolf.elite.kind).toBe("creature");
    expect(wolf.eliteWeapon).toEqual({ kind: BEAST_CLAW });
    expect(wolf.elite.kind === "creature" && wolf.elite.k).toBe(1.2);
    const lord = duelPlan(view({ elite: LORD, region: "ashen_waste" }))!;
    expect(lord.elite.kind === "creature" && lord.elite.k).toBe(1.8);
    const ooze = duelPlan(view({ elite: OOZE }))!;
    expect(ooze.elite.kind === "creature" && ooze.elite.k).toBe(CREATURE_ELITE_K_DEFAULT);
    expect(wolf.heroWeapon.kind).toBe("item"); // 沒有主手裝備：照武器 id
  });

  it("a humanoid elite uses its own main hand (equipment look first)", () => {
    const p = duelPlan(view({ elite: BANDIT, region: "ashen_waste" }))!;
    expect(p.elite.kind).toBe("doll");
    expect(p.eliteWeapon).toEqual({ kind: "gear", look: BANDIT.equipment[0]!.appearance });
  });

  it("region: cloud ridge and ashen waste have their own sky, everything else falls back to cloud ridge", () => {
    expect(duelPlan(view({ region: "ashen_waste" }))!.region).toBe("ashen_waste");
    expect(duelPlan(view({ region: "frost_peaks" }))!.region).toBe("cloud_ridge");
    expect(duelRegion(undefined)).toBe("cloud_ridge");
    expect(duelPart(html(view({ region: "crystal_rift" })))).toContain('data-region="cloud_ridge"');
  });
});

describe("beast_claw stays out of the weapon icon tables (9.8 #4)", () => {
  it("not a weapon icon kind, no Q weapon art, not an equipment kind", () => {
    expect(Q_WEAPON_KINDS[BEAST_CLAW]).toBeUndefined();
    expect(hasQWeaponArt(BEAST_CLAW)).toBe(false);
    expect(gearKinds().some((k) => k.id === BEAST_CLAW)).toBe(false);
    for (const f of ["render/qIcon/weapons.ts", "render/weaponIcon.ts", "render/gearIcon.ts", "render/gearResolve.ts"]) expect(readFile(SRC_DIR, f)).not.toContain("beast_claw");
  });
});
