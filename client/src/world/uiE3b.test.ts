// UI-E3b（巡檢 #9、偷懶自查 G4）：遇敵卡每名敵人前面的小頭像（戰場紙娃娃縮圖）與精英、Boss 金環。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { WorldView } from "../api/types";
import boss from "../dev/fixtures/encounterBoss.json";
import { alphaBounds, ENEMY_THUMB_SIZE, enemyThumbUrl, thumbDraw, thumbRing, type EncounterEnemy, type EnemyLook } from "./enemyThumb";
import { EncounterPanel } from "./WorldPanel";

const enemies = boss.enemies as unknown as EncounterEnemy[];
const hound: EnemyLook = {
  template_id: "ash_hound",
  doll_look: { creature: { body: "hound", size: "medium" } } as EnemyLook["doll_look"],
  weapon_id: "unarmed",
  weapon_class: "melee",
  race_look: null,
  equipment: [],
};

describe("縮圖要畫的東西", () => {
  it("人形照戰場的紙娃娃規格（Boss 帶外光 rarity）；異形照戰場的異形外觀", () => {
    const master = enemies.find((e) => e.rank === "boss");
    expect(master?.look).toBeTruthy();
    const d = thumbDraw(master!.look!, "boss");
    expect(d.kind).toBe("doll");
    if (d.kind === "doll") expect(d.spec.rarity).toBe(master!.look!.doll_look?.rarity);
    const c = thumbDraw(hound, "normal");
    expect(c.kind).toBe("creature");
    if (c.kind === "creature") expect(c.creature.body).toBe("hound");
  });

  it("精英的異形照戰場放大（裁邊後大小一樣，只是解法和戰場一致）", () => {
    const a = thumbDraw(hound, "normal");
    const b = thumbDraw(hound, "elite");
    if (a.kind === "creature" && b.kind === "creature") expect(b.creature.size).toBeGreaterThan(a.creature.size);
  });

  it("框：Boss、精英金環，第三方紫，其他一般", () => {
    expect(thumbRing({ rank: "boss", third: false })).toBe("boss");
    expect(thumbRing({ rank: "elite", third: false })).toBe("elite");
    expect(thumbRing({ rank: "normal", third: true })).toBe("third");
    expect(thumbRing({ rank: "normal", third: false })).toBe("normal");
  });

  it("裁邊：不透明像素的外框；全透明是 null", () => {
    const w = 4;
    const h = 3;
    const data = new Uint8ClampedArray(w * h * 4);
    expect(alphaBounds(data, w, h)).toBeNull();
    data[(1 * w + 2) * 4 + 3] = 255;
    data[(2 * w + 1) * 4 + 3] = 200;
    expect(alphaBounds(data, w, h)).toEqual({ x: 1, y: 1, w: 2, h: 2 });
  });

  it("沒有 DOM（伺服器輸出、測試）時沒有圖片網址", () => {
    expect(enemyThumbUrl(hound, "normal")).toBeNull();
  });
});

describe("遇敵卡", () => {
  it("每名敵人前面一個頭像框，Boss 金環＋外光、其餘一般；名字照舊是字", () => {
    const view = { encounter: boss } as unknown as WorldView;
    const html = renderToStaticMarkup(createElement(EncounterPanel, { view, busy: false, onAct: () => undefined, onBattle: () => undefined }));
    expect(html.match(/class="enemy-thumb /g)).toHaveLength(enemies.length);
    expect(html).toContain('class="enemy-thumb boss" data-ring="boss"');
    expect(html.match(/data-ring="normal"/g)).toHaveLength(enemies.filter((e) => e.rank === "normal").length);
    expect(html).toContain(`width:${ENEMY_THUMB_SIZE}px`);
    expect(html).toContain("霧鎖真人");
    expect(html).toContain('<span class="world-elite-tag">頭目</span>');
    expect(html).toContain('data-rank="boss"');
    expect(html).not.toContain("title=");
  });
});
