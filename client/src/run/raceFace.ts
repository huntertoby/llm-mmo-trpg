// 建角頁種族卡的頭像（QK-2 恢復暫停畫面：UI-E1 種族卡）：該族預設外觀（`races.yaml` 的 `look`）穿預覽的布衣，
// 用 Q 版頭像畫法（render/portrait.ts、qPortrait.ts）畫頭和肩膀；框色＝發源區。確定性，離屏畫好依（種族、區、大小）快取。
import type { DollLook } from "../api/types";
import { resolveDoll } from "../render/appearance";
import { drawPortraitFrame, specFigure } from "../render/portrait";
import { LOOK_OPTIONS } from "./lookOptions";

/** 種族卡穿的衣服（同建角預覽：布衣＋靴）；膚色、髮型、耳角由種族外觀蓋過。 */
const FACE_DOLL: DollLook = {
  skin: "#f1c9a5",
  skull: false,
  beard: false,
  affixes: [],
  traits: [],
  gear: { body: { kind: "shirt", material: "cloth" }, feet: { kind: "boots", material: "leather" } },
};

/** 種族 → 頭像要畫的人（不認得的種族為 `null`）。 */
export function raceFigure(race: string): ReturnType<typeof specFigure> | null {
  const opts = LOOK_OPTIONS[race];
  if (opts === undefined) return null;
  const spec = resolveDoll({ template: "hero", dollLook: FACE_DOLL, team: "ally", summon: false, weaponId: null, raceLook: opts.raceLook });
  return specFigure(spec);
}

const cache = new Map<string, string>();

/** 種族頭像的圖片網址（沒有 DOM 或不認得的種族為 `null`）。 */
export function raceFaceUrl(race: string, region: string, size: number, dpr = 2): string | null {
  if (typeof document === "undefined") return null;
  const key = `${race}|${region}|${size}|${dpr}`;
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const who = raceFigure(race);
  if (who === null) return null;
  const c = document.createElement("canvas");
  c.width = size * dpr;
  c.height = size * dpr;
  const ctx = c.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(dpr, dpr);
  drawPortraitFrame(ctx, 0, 0, size, who, region);
  const url = c.toDataURL("image/png");
  cache.set(key, url);
  return url;
}
