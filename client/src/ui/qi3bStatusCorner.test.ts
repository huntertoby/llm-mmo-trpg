// QI-3b T-B5：狀態卡角落數字——元素架勢級數、晶能湧動／狂湧 1／2 優先於回合數與數值（規格 docs/phases/PhaseQI-3計畫.md 第 0 節第 4 列、D2、D3）。
// 名詞表快照 battle/fixtures/glossary.json（118 個）。原有的 3 條在 ui/statusCard.test.ts（不改）。
import { describe, expect, it } from "vitest";
import type { StatusView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { entry as qStatusEntry } from "../render/qIcon/status";
import { CRYSTAL_SURGE_TIER, ELEMENT_STANCE_RE, statusCorner, statusTier } from "./statusCard";

const IDS = (glossary as unknown as { statuses: { id: string }[] }).statuses.map((s) => s.id);
const st = (status_id: string, remaining: number | null, amount: number | null): StatusView => ({ status_id, remaining, amount, source_id: null, charge_tiles: [], cost_status: false }) as unknown as StatusView;

describe("T-B5 角落級數", () => {
  it("名詞表裡全部 stance_<元素>_<級>（45 個）→ 級數，即使 remaining／amount 有值也優先", () => {
    const stances = IDS.filter((id) => ELEMENT_STANCE_RE.test(id));
    expect(stances).toHaveLength(45); // 9 元素 × 5 級（需求 1.1）
    for (const id of stances) {
      const lv = id.slice(-1);
      expect(statusCorner(st(id, null, null)), id).toBe(lv);
      expect(statusCorner(st(id, 3, null)), id).toBe(lv);
      expect(statusCorner(st(id, 3, 7)), id).toBe(lv);
      expect(statusCorner(st(id, null, 7)), id).toBe(lv);
      expect(qStatusEntry(id)?.d, id).toBeDefined(); // 和 Q 版圖樣的 entry 同一個 ID 樣式
    }
    for (const el of ["physical", "fire", "ice", "lightning", "poison", "wind", "earth", "holy", "shadow"]) for (let n = 1; n <= 5; n++) expect(IDS, `stance_${el}_${n}`).toContain(`stance_${el}_${n}`);
  });

  it("crystal_surge → 1、crystal_surge_2 → 2；兩個 ID 都在名詞表快照（改名會擋）", () => {
    expect(IDS).toContain("crystal_surge");
    expect(IDS).toContain("crystal_surge_2");
    expect(Object.keys(CRYSTAL_SURGE_TIER).sort()).toEqual(["crystal_surge", "crystal_surge_2"]);
    expect(statusCorner(st("crystal_surge", null, null))).toBe("1");
    expect(statusCorner(st("crystal_surge_2", null, null))).toBe("2");
    expect(statusCorner(st("crystal_surge", 2, 5))).toBe("1");
    expect(statusCorner(st("crystal_surge_2", 2, 5))).toBe("2");
  });

  it("其他狀態照現行（剩餘回合 → 數值 → 空）；姿態、像架勢但不合樣式的 ID 不算級數", () => {
    const others = IDS.filter((id) => statusTier(id) === null);
    expect(others).toHaveLength(118 - 45 - 2);
    for (const id of others) {
      expect(statusCorner(st(id, 3, 7)), id).toBe("3");
      expect(statusCorner(st(id, null, 7)), id).toBe("7");
      expect(statusCorner(st(id, null, null)), id).toBe("");
    }
    for (const id of ["stance_fury", "stance_fire_6", "stance_fire_0", "stance_water_2", "xstance_fire_1", "stance_fire_1x"]) expect(statusTier(id), id).toBeNull();
  });
});
