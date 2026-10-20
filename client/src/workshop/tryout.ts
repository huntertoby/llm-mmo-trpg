// 裝上試玩：把工坊的技能放進 `POST /api/battles` 的請求，並在進戰鬥前先提醒放不出來的情況。
import type { BattleResponse, CreateBattleRequest, WorkshopArena, WorkshopCheck } from "../api/types";
import { getPath, isJson, type Json } from "./draft";

export interface TryoutChoice {
  mapId: string;
  seed: number;
  buildId: string;
  /** 要被換掉的技能 ID；空字串 ＝ 不換，直接加在空格。 */
  replaceId: string;
  /** 靶場的對手（`dummy`／`fighting`）；其他地圖不送。 */
  opponents: string;
}

/** 這張地圖是不是靶場（只有靶場可以選對手）。 */
export function isTrainingMap(arena: WorkshopArena | null, mapId: string): boolean {
  return arena?.maps.find((m) => m.id === mapId)?.archetype === "training";
}

/** 送給後端的技能：用檢查後的正規化定義（含自動產生的 ID），來源標為工坊。 */
export function tryoutSkill(check: WorkshopCheck): Json | null {
  if (!check.legal || check.skill === null) return null;
  const skill: Json = { ...check.skill };
  const provenance = isJson(skill["provenance"]) ? skill["provenance"] : {};
  skill["provenance"] = { ...provenance, origin: "workshop" };
  return skill;
}

export function buildTryoutRequest(
  choice: TryoutChoice,
  check: WorkshopCheck,
  arena: WorkshopArena | null,
): CreateBattleRequest | null {
  const skill = tryoutSkill(check);
  if (skill === null) return null;
  const body: CreateBattleRequest = {
    map_id: choice.mapId,
    seed: choice.seed,
    hero_build: choice.buildId,
    ally_builds: [],
    max_rounds: arena?.max_rounds ?? 30,
    custom_skills: [skill],
    replace_skills: choice.replaceId === "" ? [] : [choice.replaceId],
  };
  if (isTrainingMap(arena, choice.mapId) && choice.opponents !== "") body.opponents = choice.opponents;
  return body;
}

/** 技能的法力代價（沒有就是 0）。 */
export function skillMana(check: WorkshopCheck | null): number {
  const mana = getPath(check?.skill ?? null, "cost.mana");
  return typeof mana === "number" ? mana : 0;
}

/** 戰鬥建立後檢查：主角的法力上限不夠施放時回傳中文提醒（不改主角的法力，見 3F-1 待決定 #9）。 */
export function manaWarning(check: WorkshopCheck, response: BattleResponse): string | null {
  const need = skillMana(check);
  if (need <= 0) return null;
  const hero = response.view.units.find((u) => u.id === response.hero_id);
  if (hero === undefined || hero.max_mana >= need) return null;
  return `主角的法力上限只有 ${hero.max_mana}，這個技能需要 ${need} 點法力：進了戰鬥也放不出來。可以改選法力較多的 build、把技能的法力代價調低，或仍然進入（只能試其他部分）。`;
}

/** 試玩前就能提醒的一句話（還不知道主角法力時，只說明技能要多少）。 */
export function manaNote(check: WorkshopCheck | null): string | null {
  const need = skillMana(check);
  return need > 0 ? `這個技能每次施放要 ${need} 點法力；主角的法力上限依 build 而定，進入戰鬥前會再確認。` : null;
}
