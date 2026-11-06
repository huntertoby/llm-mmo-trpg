// 外觀選項（Phase 6R-2，#137；docs/design/07-角色成長.md 7.7、docs/art/外觀變化方案.md）。
// 各族可選清單（`content/races.yaml` 的 `look_options`、`look_eyes`）讀 createTexts.ts 在 build 時以 `?raw` 匯入的同一份 yaml（
// 後端以 pydantic 驗證、建角與 `change_look` 再檢查一次）。快速組合「粗獷」「柔和」只是一組外觀預設、不存性別（#137）。
// 純資料與純函式（沒有 Math.random：「隨機」用呼叫者給的種子，FNV-1a）。
import { parse } from "yaml";
import type { LookChoice } from "../api/types";
import { seedOf } from "../render/inkStyle";
import { RACES_YAML_TEXT } from "./createTexts";

export type LookKey = keyof LookChoice;

export interface RaceLookOptions {
  skin: readonly string[];
  hair: readonly string[];
  hairColor: readonly string[];
  beard: readonly string[];
  beastEars: readonly string[];
  eyes: readonly string[];
  /** 種族預設外觀（`look`，原樣給 `raceLookToLook`）。 */
  raceLook: Readonly<Record<string, unknown>>;
}

/** 各列的選項與中文（順序照美術方案第 3 節：臉型、眼睛、髮型、鬍子、體型、膚色、髮色、眼色、睫毛）。 */
export const FACES = [["round", "圓臉"], ["oval", "蛋臉"], ["square", "方臉"], ["heart", "尖下巴"]] as const;
export const EYE_STYLES = [["square", "方眼"], ["dot", "圓點"], ["smile", "笑眼"], ["big", "大眼"]] as const;
export const HAIRS: Readonly<Record<string, string>> = { short: "短髮", long: "長髮", bob: "齊肩", ponytail: "馬尾", twin: "雙馬尾", spiky: "刺蝟", bun: "髮髻", none: "光頭" };
export const BEARDS: Readonly<Record<string, string>> = { none: "無", stubble: "鬍渣", mustache: "八字鬍", goatee: "山羊鬍", full: "大鬍子" };
export const FRAMES = [[null, "標準"], ["slim", "纖細"], ["broad", "壯碩"]] as const;
export const BEAST_EARS: Readonly<Record<string, string>> = { fox: "狐", cat: "貓", wolf: "狼", rabbit: "兔" };

/** 現在的紙娃娃畫得出來的值（Q 版 QK-6 之前；其餘的值照存，畫面先用最接近的現有部件）。 */
export const DRAWN_HAIRS: readonly string[] = ["short", "long", "bun", "none"];
export const DRAWN_BEARDS: readonly string[] = ["none", "full"];

const strs = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : []);

/** 純函式：`races.yaml` 文字 → 種族 ID → 可選清單；檔案壞掉時空物件。 */
export function parseLookOptions(text: string): Readonly<Record<string, RaceLookOptions>> {
  let doc: unknown;
  try {
    doc = parse(text);
  } catch {
    return {};
  }
  if (typeof doc !== "object" || doc === null) return {};
  const root = doc as Record<string, unknown>;
  const eyes = strs(root.look_eyes);
  const out: Record<string, RaceLookOptions> = {};
  for (const row of Array.isArray(root.races) ? root.races : []) {
    if (typeof row !== "object" || row === null) continue;
    const r = row as Record<string, unknown>;
    if (typeof r.id !== "string") continue;
    const look = typeof r.look === "object" && r.look !== null ? (r.look as Record<string, unknown>) : {};
    const opt = typeof r.look_options === "object" && r.look_options !== null ? (r.look_options as Record<string, unknown>) : {};
    const own = typeof look.eyes === "string" && !eyes.includes(look.eyes) ? [look.eyes] : [];
    out[r.id] = {
      skin: strs(opt.skin),
      hair: strs(opt.hair),
      hairColor: strs(opt.hair_color),
      beard: strs(opt.beard),
      beastEars: strs(opt.beast_ears),
      eyes: [...eyes, ...own],
      raceLook: look,
    };
  }
  return out;
}

export const LOOK_OPTIONS = parseLookOptions(RACES_YAML_TEXT);

/** 快速組合（#137，不設性別）：粗獷＝壯碩、短髮、鬍渣、方眼、無睫毛；柔和＝纖細、馬尾、大眼、睫毛、無鬍子。 */
export const PRESETS: Readonly<Record<"rugged" | "soft", LookChoice>> = {
  rugged: { frame: "broad", hair: "short", beard: "stubble", eye_style: "square", lashes: false },
  soft: { frame: "slim", hair: "ponytail", beard: "none", eye_style: "big", lashes: true },
};

const LIMITED: readonly [LookKey, keyof RaceLookOptions][] = [
  ["skin", "skin"],
  ["hair", "hair"],
  ["hair_color", "hairColor"],
  ["beard", "beard"],
  ["beast_ears", "beastEars"],
  ["eyes", "eyes"],
];

/** 純函式：只留下這一族也能選的值（換種族、套快速組合時用；同後端 `look_for_race`）；全空回傳 `{}`。 */
export function lookForRace(choice: LookChoice, opts: RaceLookOptions | undefined): LookChoice {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(choice)) {
    if (v === null || v === undefined) continue;
    const limit = LIMITED.find(([key]) => key === k);
    if (limit !== undefined) {
      const allowed = opts?.[limit[1]] as readonly string[] | undefined;
      if (allowed === undefined || !allowed.includes(v as string)) continue;
    }
    out[k] = v;
  }
  return out as LookChoice;
}

/** 純函式：套快速組合（目前的選擇上覆蓋，種族不開放的那項略過；之後每一項都能再改）。 */
export function applyPreset(current: LookChoice, preset: LookChoice, opts: RaceLookOptions | undefined): LookChoice {
  return lookForRace({ ...current, ...preset }, opts);
}

/** 純函式：在種族範圍裡抽一組（先軟性抽粗獷／柔和，不會抽出「睫毛配大鬍子」；同美術方案第 4 節）。 */
export function randomLook(seed: string, opts: RaceLookOptions | undefined): LookChoice {
  let h = seedOf(seed);
  const next = (n: number): number => {
    h = Math.imul(h ^ (h >>> 15), 2246822507) >>> 0;
    h = (h ^ (h >>> 13)) >>> 0;
    return n <= 0 ? 0 : h % n;
  };
  const pick = <T,>(list: readonly T[]): T | undefined => (list.length === 0 ? undefined : list[next(list.length)]);
  const soft = next(2) === 1;
  const base = soft ? PRESETS.soft : PRESETS.rugged;
  const hairs = opts?.hair ?? [];
  const beards = (opts?.beard ?? []).filter((b) => (soft ? b === "none" : true));
  return lookForRace(
    {
      ...base,
      face: pick(FACES.map(([v]) => v)) ?? null,
      eye_style: pick(EYE_STYLES.map(([v]) => v)) ?? null,
      hair: (pick(hairs) as LookChoice["hair"]) ?? null,
      beard: (pick(beards) as LookChoice["beard"]) ?? null,
      skin: pick(opts?.skin ?? []) ?? null,
      hair_color: pick(opts?.hairColor ?? []) ?? null,
      eyes: pick(opts?.eyes ?? []) ?? null,
      beast_ears: (pick(opts?.beastEars ?? []) as LookChoice["beast_ears"]) ?? null,
    },
    opts,
  );
}

/** 純函式：送給後端的 `look`（去掉空值；全空＝`null`＝種族預設）。 */
export function lookBody(choice: LookChoice): LookChoice | null {
  const kept = Object.fromEntries(Object.entries(choice).filter(([, v]) => v !== null && v !== undefined));
  return Object.keys(kept).length === 0 ? null : (kept as LookChoice);
}
