// 遇敵卡的敵人小頭像（UI-E3b；docs/art/全遊戲一致性巡檢.md #9、偷懶自查 G4）：戰場紙娃娃縮圖，照伺服器給的
// `EncounterEnemyView.look`（開戰時的範本＋詞綴＋裝備）畫；人形用紙娃娃正面，異形用側面（敵方朝西，同戰場）。
// 精英、Boss 加金環（`docs/art/敵人外觀.md`：金色 `#ffbf3a`＋墨線；Boss 另加外光）。沒有外觀或沒有 DOM 時留同大小的空框。
// 確定性：沒有亂數；離屏畫好、裁掉透明邊、依（外觀、階級、大小）快取成圖片網址。
import type { WorldEncounterView } from "../api/types";
import { resolveDoll, type DollInput, type DollSpec } from "../render/appearance";
import { renderCreatureCanvas, resolveCreature, type ResolvedCreature } from "../render/inkCreature";
import { renderFigureCanvas } from "../render/paperdoll";

export type EncounterEnemy = WorldEncounterView["enemies"][number];
export type EnemyLook = NonNullable<EncounterEnemy["look"]>;
export type EnemyRank = EncounterEnemy["rank"];

/** 遇敵卡上的頭像大小（px，含框）。 */
export const ENEMY_THUMB_SIZE = 36;

/** 縮圖要畫的東西：人形紙娃娃（正面）或異形（側面、朝西）。 */
export type ThumbDraw = { kind: "doll"; spec: DollSpec } | { kind: "creature"; creature: ResolvedCreature };

/** 外觀 → 要畫的東西（照戰場的解法：人形 `resolveDoll`、異形 `resolveCreature`，精英倍率由裁邊抵掉）。 */
export function thumbDraw(look: EnemyLook, rank: EnemyRank): ThumbDraw {
  const doll = look.doll_look ?? null;
  if (doll?.creature != null) {
    return {
      kind: "creature",
      creature: resolveCreature({ look: doll.creature, elite: rank === "elite", affixes: doll.affixes ?? undefined, rarity: doll.rarity ?? null, field: true }),
    };
  }
  const input: DollInput = {
    template: look.template_id,
    dollLook: doll,
    team: "enemy",
    summon: false,
    weaponId: look.weapon_id,
    weaponClass: look.weapon_class,
    equipment: look.equipment.map((e) => ({ slot: e.slot, appearance: e.appearance })) as DollInput["equipment"],
    raceLook: (look.race_look ?? null) as Readonly<Record<string, unknown>> | null,
  };
  return { kind: "doll", spec: resolveDoll(input) };
}

/** 頭像框的樣式：一般、精英（金環）、Boss（金環＋外光）、第三方。 */
export function thumbRing(enemy: Pick<EncounterEnemy, "rank" | "third">): "normal" | "elite" | "boss" | "third" {
  if (enemy.rank === "boss") return "boss";
  if (enemy.rank === "elite") return "elite";
  return enemy.third === true ? "third" : "normal";
}

/** 不透明像素的外框（alpha > 8）；全透明時 `null`。 */
export function alphaBounds(data: Uint8ClampedArray, width: number, height: number): { x: number; y: number; w: number; h: number } | null {
  let x0 = width;
  let y0 = height;
  let x1 = -1;
  let y1 = -1;
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      if ((data[(y * width + x) * 4 + 3] ?? 0) <= 8) continue;
      if (x < x0) x0 = x;
      if (x > x1) x1 = x;
      if (y < y0) y0 = y;
      if (y > y1) y1 = y;
    }
  }
  return x1 < 0 ? null : { x: x0, y: y0, w: x1 - x0 + 1, h: y1 - y0 + 1 };
}

/** 人形只取上半身（頭到腰）：整個人放進 36px 的圓裡臉太小。 */
export const DOLL_CROP = 0.62;

/**
 * 裁掉透明邊、等比放進正方形（左右置中，留一點邊）。`crop` < 1 時只取上面那一段（人形的上半身，貼齊上緣），
 * 否則整隻貼齊下緣（異形）。
 */
function fitSquare(src: HTMLCanvasElement, px: number, crop = 1): HTMLCanvasElement | null {
  const sctx = src.getContext("2d");
  if (sctx === null) return null;
  const full = alphaBounds(sctx.getImageData(0, 0, src.width, src.height).data, src.width, src.height);
  if (full === null) return null;
  const box = { ...full, h: Math.max(1, Math.round(full.h * crop)) };
  const out = document.createElement("canvas");
  out.width = px;
  out.height = px;
  const ctx = out.getContext("2d");
  if (ctx === null) return null;
  const pad = Math.round(px * 0.08);
  const scale = Math.min((px - pad * 2) / box.w, (px - pad) / box.h);
  const w = box.w * scale;
  const h = box.h * scale;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(src, box.x, box.y, box.w, box.h, (px - w) / 2, crop < 1 ? pad : px - h, w, h);
  return out;
}

const cache = new Map<string, string | null>();

/** 縮圖的圖片網址（`size` px 顯示、`dpr` 倍解析度）；沒有 DOM 或畫不出來時 `null`。 */
export function enemyThumbUrl(look: EnemyLook, rank: EnemyRank, size = ENEMY_THUMB_SIZE, dpr = 2): string | null {
  if (typeof document === "undefined") return null;
  const key = `${JSON.stringify(look)}|${rank}|${size}|${dpr}`;
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  let url: string | null = null;
  try {
    const d = thumbDraw(look, rank);
    const raw = d.kind === "doll" ? renderFigureCanvas(d.spec, "south", false, dpr * 2, false) : renderCreatureCanvas(d.creature, "west", dpr * 2, null, "body");
    const fit = raw === null ? null : fitSquare(raw, size * dpr, d.kind === "doll" ? DOLL_CROP : 1);
    url = fit?.toDataURL() ?? null;
  } catch {
    url = null; // jsdom 等沒有 2D 畫布的環境
  }
  cache.set(key, url);
  return url;
}

/** 遇敵卡一名敵人的頭像（框＋縮圖）；裝飾用，名字在旁邊的字。 */
export function EnemyThumb({ enemy, size = ENEMY_THUMB_SIZE }: { enemy: EncounterEnemy; size?: number }) {
  const ring = thumbRing(enemy);
  const url = enemy.look == null ? null : enemyThumbUrl(enemy.look, enemy.rank, size);
  return (
    <span className={`enemy-thumb ${ring}`} data-ring={ring} style={{ width: size, height: size }} aria-hidden="true">
      {url !== null && <img src={url} width={size} height={size} alt="" draggable={false} />}
    </span>
  );
}
