// 建角畫面的內容文字（UI-E1b；docs/art/shots/misc/create-v2.png、玩法 PM 2026-11-04「建角畫面 v2 的種族與出身文字」）：
// 種族一句簡介（`content/races.yaml` 的 `blurb_zh`）、出身短描述（`content/origins.yaml` 的 `tagline_zh`）、
// 種族的判定加值（`content/world/situation_rules.yaml` 的 `race_methods`＋`methods` 的名稱＋`check.race_bonus`）。
// 和遊戲名稱（gameInfo.ts）一樣在 build 時以 `?raw` 匯入同一份 yaml（Python 端由 pydantic schema 與 `trpg content check` 驗證），
// 不新增 API 欄位。檔案壞掉或缺欄位時該項回 `null`，畫面就不顯示那一行。純資料，沒有亂數。
import { parse } from "yaml";
import racesYaml from "../../../content/races.yaml?raw";
import originsYaml from "../../../content/origins.yaml?raw";
import situationYaml from "../../../content/world/situation_rules.yaml?raw";

export interface CreateTexts {
  /** 種族 ID → 一句簡介。 */
  blurbs: Readonly<Record<string, string>>;
  /** 出身 ID → 短描述。 */
  taglines: Readonly<Record<string, string>>;
  /** 種族 ID → 判定加值的方法名稱（例：fox → 攀爬跳躍，#138）。 */
  methods: Readonly<Record<string, string>>;
  /** 種族的判定加值（`check.race_bonus`，9.6.4：+1）。 */
  bonus: number;
}

function load(text: string): Record<string, unknown> {
  try {
    const doc: unknown = parse(text);
    return typeof doc === "object" && doc !== null ? (doc as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

const list = (v: unknown): Record<string, unknown>[] => (Array.isArray(v) ? v.filter((x): x is Record<string, unknown> => typeof x === "object" && x !== null) : []);
const str = (v: unknown): string | null => (typeof v === "string" && v.trim() !== "" ? v : null);

/** 從一張表（`races`／`origins`）取 ID → 某個文字欄位。 */
function textById(doc: Record<string, unknown>, key: string, field: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const row of list(doc[key])) {
    const id = str(row.id);
    const text = str(row[field]);
    if (id !== null && text !== null) out[id] = text;
  }
  return out;
}

/** 純函式：三份 yaml 文字 → 建角畫面的文字。 */
export function parseCreateTexts(races: string, origins: string, situation: string): CreateTexts {
  const s = load(situation);
  const names: Record<string, string> = {};
  for (const m of list(s.methods)) {
    const id = str(m.id);
    const name = str(m.name_zh);
    if (id !== null && name !== null) names[id] = name;
  }
  const methods: Record<string, string> = {};
  const raw = s.race_methods;
  if (typeof raw === "object" && raw !== null) {
    for (const [race, method] of Object.entries(raw as Record<string, unknown>)) {
      const name = typeof method === "string" ? names[method] : undefined;
      if (name !== undefined) methods[race] = name;
    }
  }
  const check = s.check;
  const bonus = typeof check === "object" && check !== null && typeof (check as Record<string, unknown>).race_bonus === "number" ? ((check as Record<string, unknown>).race_bonus as number) : 0;
  return { blurbs: textById(load(races), "races", "blurb_zh"), taglines: textById(load(origins), "origins", "tagline_zh"), methods, bonus };
}

/** `content/races.yaml` 原文（6R-2 外觀選項 `lookOptions.ts` 也從這裡讀，yaml 只在本檔匯入）。 */
export const RACES_YAML_TEXT: string = racesYaml;

export const CREATE_TEXTS: CreateTexts = parseCreateTexts(racesYaml, originsYaml, situationYaml);

/** 純函式：`races.yaml` 文字 → 依資料順序的（種族 ID, 名稱）（6R-1 換種族的選單用）。 */
export function parseRaceNames(races: string): readonly { id: string; name: string }[] {
  return list(load(races).races).flatMap((row) => {
    const id = str(row.id);
    const name = str(row.name_zh);
    return id !== null && name !== null ? [{ id, name }] : [];
  });
}

export const RACE_NAMES = parseRaceNames(racesYaml);

/** 判定加值的顯示（「交涉 +1」）；沒有資料或加值為 0 時 `null`。 */
export function raceCheckBonusZh(raceId: string, texts: CreateTexts = CREATE_TEXTS): string | null {
  const name = texts.methods[raceId];
  if (name === undefined || texts.bonus <= 0) return null;
  return `${name} +${texts.bonus}`;
}

/** 判定加值滑過的說明（玩法 PM：「情境判定用這類方法時 +1」）。 */
export function raceCheckBonusHint(texts: CreateTexts = CREATE_TEXTS): string {
  return `情境判定用這類方法時 +${texts.bonus}`;
}
