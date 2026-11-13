// 主角的 Q 版頭像（QK-2b；docs/art/QK-2檢查.md 小修 2）：我的角色清單、HUD 主角卡（探索、戰鬥）都用這一份。
// 外觀照主角的紙娃娃（伺服器的 `FieldHeroView` 或戰鬥的 `UnitView`：範本、`doll_look`〔含外觀選項 `custom`〕、種族外觀〔龍裔的角……〕、
// 身上的裝備），用 NPC 頭像同一套畫法（render/portrait.ts `specFigure`＋`drawPortraitFrame`，不畫武器）；框色＝出身區
// （`PORTRAIT_REGION`；沒有出身時用呼叫端給的區域，再沒有就是傭兵金）。
// 確定性：沒有亂數；離屏畫好依（外觀、區域、大小）快取成圖片網址。沒有 DOM（vitest）時留同大小的空框。
import type { FieldHeroView, UnitView } from "../api/types";
import { resolveDoll, type DollInput } from "../render/appearance";
import { drawPortraitBare, drawPortraitFrame, PORTRAIT_REGION, specFigure } from "../render/portrait";

/** 主角頭像要畫的外觀（`resolveDoll` 的輸入，我方）。 */
export type HeroFaceInput = DollInput;

/** 伺服器的主角外觀（角色清單、探索 HUD）→ 頭像輸入。 */
export function fieldHeroInput(look: FieldHeroView | null | undefined): HeroFaceInput | null {
  if (look == null) return null;
  return {
    template: look.template_id,
    dollLook: look.doll_look ?? null,
    team: "ally",
    summon: false,
    weaponId: look.weapon_id,
    weaponClass: look.weapon_class,
    equipment: look.equipment.map((e) => ({ slot: e.slot, appearance: e.appearance })) as DollInput["equipment"],
    raceLook: (look.race_look ?? null) as Readonly<Record<string, unknown>> | null,
  };
}

/** 戰鬥的主角單位 → 頭像輸入（同戰場小人：`doll_look`、裝備、種族外觀）。 */
export function unitHeroInput(u: UnitView): HeroFaceInput {
  return {
    template: u.template_id,
    dollLook: u.doll_look ?? null,
    team: "ally",
    summon: false,
    weaponId: u.weapon_id,
    weaponClass: u.weapon_class,
    equipment: (u.equipment ?? []).map((e) => ({ slot: e.slot, appearance: e.appearance })) as DollInput["equipment"],
    raceLook: (u.race?.look ?? null) as Readonly<Record<string, unknown>> | null,
  };
}

/** 頭像框色（出身區；不認得或沒有＝傭兵金）。 */
export function heroRing(realm: string | null | undefined): string {
  return ((realm != null ? PORTRAIT_REGION[realm] : undefined) ?? PORTRAIT_REGION["merc"]!)[0];
}

/** 快取鍵（外觀內容＋區域＋大小＋解析度；不帶框的另加 `|bare`，帶框的鍵不變）。 */
export function heroFaceKey(input: HeroFaceInput, realm: string | null | undefined, size: number, dpr: number, bare = false): string {
  return `${size}|${dpr}|${realm ?? ""}|${JSON.stringify(input)}${bare ? "|bare" : ""}`;
}

const cache = new Map<string, string>();

/** 主角頭像的圖片網址（沒有 DOM 時為 `null`）。`bare`＝不畫區域色底與框、下緣漸隱（PNL-2「外觀與種族」分頁圖示；同一份外觀）。 */
export function heroFaceUrl(input: HeroFaceInput, realm: string | null | undefined, size: number, dpr = 2, bare = false): string | null {
  if (typeof document === "undefined") return null;
  const key = heroFaceKey(input, realm, size, dpr, bare);
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const c = document.createElement("canvas");
  c.width = size * dpr;
  c.height = size * dpr;
  const ctx = c.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(dpr, dpr);
  if (bare) drawPortraitBare(ctx, size, specFigure(resolveDoll(input)));
  else drawPortraitFrame(ctx, 0, 0, size, specFigure(resolveDoll(input)), realm);
  const url = c.toDataURL("image/png");
  cache.set(key, url);
  return url;
}

/** 主角頭像（圓角方框，同 NPC 頭像）；沒有 DOM 時留同大小的空框。`bare`＝不帶框（分頁圖示）。 */
export function HeroFace({ input, realm, size, label, bare = false }: { input: HeroFaceInput; realm: string | null | undefined; size: number; label?: string; bare?: boolean }) {
  const url = heroFaceUrl(input, realm, size, 2, bare);
  const ring = heroRing(realm);
  if (bare) {
    const cls = "pnl-ico hero-face-bare";
    if (url === null) return <span className={cls} style={{ width: size, height: size }} data-hero-face="bare" aria-label={label} role={label !== undefined ? "img" : undefined} />;
    return <img className={cls} src={url} width={size} height={size} alt={label ?? ""} data-hero-face="bare" draggable={false} />;
  }
  if (url === null) {
    return <span className="hero-face" style={{ width: size, height: size }} data-hero-face="q" data-ring={ring} aria-label={label} role={label !== undefined ? "img" : undefined} />;
  }
  return <img className="hero-face" src={url} width={size} height={size} alt={label ?? ""} data-hero-face="q" data-ring={ring} draggable={false} />;
}
