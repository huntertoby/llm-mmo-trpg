// 測試用：依範本 ID 補上後端的紙娃娃外觀（`fixtures/unitDolls.json`，由 `scripts/export_client_fixtures.py` 從 content/ 產生）。
import type { DollLook } from "../api/types";
import { resolveDoll, type DollInput, type DollSpec } from "./appearance";
import unitDolls from "./fixtures/unitDolls.json";

/** 單位範本 ID → 紙娃娃外觀。 */
export const UNIT_DOLLS = unitDolls as unknown as Readonly<Record<string, DollLook>>;

/** `resolveDoll`，但 `dollLook` 沒給時依 `template` 查後端外觀（沒有對照的範本照舊退回預設）。 */
export function resolveDollT(input: DollInput): DollSpec {
  return resolveDoll({ dollLook: UNIT_DOLLS[input.template], ...input });
}
