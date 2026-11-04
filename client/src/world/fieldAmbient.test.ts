// Phase 6N-10：從 FieldView 推 NPC 身分（站在哪個設施旁）、營火位置與場景鍵；只畫，不讀伺服器新欄位。
import { describe, expect, it } from "vitest";
import type { FieldView } from "../api/types";
import { fieldAmbient, npcRole } from "./fieldAmbient";
import { npcUnitId } from "./fieldModel";

const field = (over: Partial<FieldView>): FieldView =>
  ({ map_id: "mist_ferry", npcs: [], facilities: [], campfires: [], ...over }) as unknown as FieldView;

describe("6N-10：NPC 身分", () => {
  it("鐵匠鋪、附魔台旁 ＝ 鐵匠；酒館、雇用、商店旁 ＝ 掌櫃；其他 ＝ 一般；2 格以內才算", () => {
    expect(npcRole({ x: 3, y: 2 }, [{ x: 4, y: 2, kind: "smithy" }])).toBe("smith");
    expect(npcRole({ x: 15, y: 12 }, [{ x: 15, y: 11, kind: "shop" }])).toBe("keeper");
    expect(npcRole({ x: 5, y: 5 }, [{ x: 7, y: 7, kind: "tavern" }])).toBe("keeper");
    expect(npcRole({ x: 5, y: 5 }, [{ x: 8, y: 5, kind: "tavern" }])).toBe("town");
    expect(npcRole({ x: 5, y: 5 }, [{ x: 5, y: 6, kind: "notice_board" }])).toBe("town");
    // 鐵匠優先
    expect(npcRole({ x: 5, y: 5 }, [{ x: 5, y: 6, kind: "shop" }, { x: 6, y: 6, kind: "enchanter" }])).toBe("smith");
  });

  it("霧渡鎮：柳掌櫃是掌櫃、渡婆婆一般；石記鐵鋪的石師傅是鐵匠；鍵用單位 ID，場景鍵是地圖 ID", () => {
    const town = fieldAmbient(
      field({
        npcs: [
          { id: "granny_du", name_zh: "渡婆婆", x: 11, y: 13 },
          { id: "shopkeeper_liu", name_zh: "柳掌櫃", x: 15, y: 12 },
        ] as FieldView["npcs"],
        facilities: [
          { kind: "shop", x: 15, y: 11 },
          { kind: "notice_board", x: 8, y: 7 },
          { kind: "mentor", x: 2, y: 10 },
        ],
        campfires: [{ id: "b", x: 9, y: 4 }, { id: "a", x: 2, y: 4 }],
      }),
    );
    expect(town.key).toBe("mist_ferry");
    expect(town.roles).toEqual({ [npcUnitId("granny_du")]: "town", [npcUnitId("shopkeeper_liu")]: "keeper" });
    expect(town.fires).toEqual([{ x: 2, y: 4 }, { x: 9, y: 4 }]);
    const smithy = fieldAmbient(
      field({
        map_id: "mist_ferry_smithy",
        npcs: [{ id: "smith_shi", name_zh: "石師傅", x: 3, y: 2 }] as FieldView["npcs"],
        facilities: [{ kind: "smithy", x: 4, y: 2 }, { kind: "enchanter", x: 7, y: 2 }],
      }),
    );
    expect(smithy.roles[npcUnitId("smith_shi")]).toBe("smith");
  });
});
