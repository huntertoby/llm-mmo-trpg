// 環境動態與 NPC 小動作的場景資料（Phase 6N-10）：只畫、純資料。由 `world/fieldAmbient.ts` 從 FieldView 算出，
// 放在 DrawModel.ambient；戰鬥沒有（戰場的草、霧、水波照地圖本身動，NPC 小動作只有實地地圖有）。
import type { Pos } from "../api/types";
import type { NpcRole } from "./npcFidgets";
import { seedOf } from "./inkStyle";

export interface AmbientScene {
  /** 場景鍵（實地地圖 ID）：NPC 小動作挑變體、風向都用它，重新整理後一樣。 */
  key: string;
  /** 單位 ID → NPC 身分（沒列的照 6M-4 的小動作）。 */
  roles: Readonly<Record<string, NpcRole>>;
  /** 單位 ID → 做職業動作時轉向哪一側（6Q-1：朝工作的設施；沒列的照 `npcFidgets.workFacing` 的預設）。 */
  sides?: Readonly<Record<string, "east" | "west">>;
  /** 營火的格子（火苗閃動、光暈呼吸）。 */
  fires: readonly Pos[];
}

/** 風向：1 ＝ 往東吹、-1 ＝ 往西吹。地圖資料沒有風向欄位，照場景鍵（沒有時用區域）的雜湊定，同一張圖永遠一樣。 */
export type Wind = 1 | -1;

export function windOf(key: string): Wind {
  return (seedOf(`wind:${key}`) & 1) === 0 ? 1 : -1;
}

/** 風力（0.6～1.0）：天氣有風、暴風雪、沙暴時加到 1.4。只影響擺幅。 */
export function windStrength(key: string, weather: string): number {
  const base = 0.6 + (seedOf(`gust:${key}`) % 5) / 10;
  return /wind|storm|blizzard|gale|sand/.test(weather) ? base + 0.4 : base;
}
