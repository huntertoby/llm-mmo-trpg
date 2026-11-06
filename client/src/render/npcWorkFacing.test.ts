// Phase 6Q-1：NPC 做職業動作（搥打、擦桌子）時轉成側面，做完轉回原本的朝向——時間軸、確定性、朝向選擇。
import { Container, Sprite, Texture } from "pixi.js";
import { describe, expect, it } from "vitest";
import type { Facing } from "../api/types";
import type { UnitDraw } from "../battle/drawModel";
import { fieldAmbient, workSide } from "../world/fieldAmbient";
import { IdleMotion } from "./idleMotion";
import type { InkPose } from "./inkPose";
import { isWorkFidget, npcFidgetAt, npcIdleFrame, workFacing, type NpcRole } from "./npcFidgets";
import { BODY_LABEL } from "./unitSprite";
import type { FieldView } from "../api/types";

const STEP = 50;
const SPAN = 120000;

describe("6Q-1：職業動作轉成側面", () => {
  it("時間軸：職業動作的每一刻都是側面；日常動作與站好時沒有朝向（照原本的朝向畫）", () => {
    const cases: [string, NpcRole][] = [
      ["npc_smith_shi", "smith"],
      ["npc_shopkeeper_liu", "keeper"],
      ["npc_granny_du", "town"],
    ];
    for (const [id, role] of cases) {
      let work = 0;
      for (let ms = 0; ms < SPAN; ms += STEP) {
        const f = npcIdleFrame("mist_ferry", id, role, ms, "south");
        const fid = npcFidgetAt("mist_ferry", id, role, ms);
        expect(f).toEqual(npcIdleFrame("mist_ferry", id, role, ms, "south")); // 確定性
        if (fid !== null && isWorkFidget(fid.id)) {
          work++;
          expect(f.facing === "east" || f.facing === "west", `${id}@${ms}`).toBe(true);
          expect(f.key.endsWith(`|${f.facing}`)).toBe(true); // 側面的貼圖鍵分開
        } else {
          expect(f.facing, `${id}@${ms}`).toBeUndefined();
        }
      }
      if (role === "town") expect(work).toBe(0);
      else expect(work).toBeGreaterThan(0);
    }
  });

  it("做完轉回：職業動作結束的下一刻沒有朝向；不給 facing 時照 6N-10 不轉", () => {
    let backs = 0;
    for (let ms = STEP; ms < SPAN; ms += STEP) {
      const prev = npcIdleFrame("mist_ferry", "npc_smith_shi", "smith", ms - STEP, "south");
      const cur = npcIdleFrame("mist_ferry", "npc_smith_shi", "smith", ms, "south");
      if (prev.facing !== undefined && cur.facing === undefined) {
        backs++;
        expect(cur.key === "" || !cur.key.includes("hammer")).toBe(true);
      }
      expect(npcIdleFrame("mist_ferry", "npc_smith_shi", "smith", ms).facing).toBeUndefined();
    }
    expect(backs).toBeGreaterThan(0);
  });

  it("朝向選擇：本來就是側面不轉；有設施方向朝設施；都沒有照 ID 雜湊（固定）", () => {
    expect(workFacing("a", "east", "west")).toBe("east");
    expect(workFacing("a", "west")).toBe("west");
    expect(workFacing("a", "south", "west")).toBe("west");
    expect(workFacing("a", "north", "east")).toBe("east");
    const ids = Array.from({ length: 16 }, (_, i) => `npc_${i}`);
    const got = ids.map((id) => workFacing(id, "south"));
    expect(got).toEqual(ids.map((id) => workFacing(id, "south")));
    expect(new Set(got).size).toBe(2); // 東西都有
    // 本來就是側面：鍵和 6N-10 一樣（不多一份貼圖）
    for (let ms = 0; ms < SPAN; ms += STEP) {
      const f = npcIdleFrame("m", "npc_smith_shi", "smith", ms, "east");
      expect(f.key.includes("|")).toBe(false);
      expect(f.key).toBe(npcIdleFrame("m", "npc_smith_shi", "smith", ms).key);
    }
  });

  it("朝工作的設施：設施在東 ＝ east、在西 ＝ west、同一欄 ＝ 不指定；fieldAmbient 帶上 sides", () => {
    expect(workSide({ x: 3, y: 2 }, [{ x: 4, y: 2, kind: "smithy" }], "smith")).toBe("east");
    expect(workSide({ x: 5, y: 2 }, [{ x: 4, y: 3, kind: "smithy" }], "smith")).toBe("west");
    expect(workSide({ x: 15, y: 12 }, [{ x: 15, y: 11, kind: "shop" }], "keeper")).toBeNull();
    expect(workSide({ x: 5, y: 5 }, [{ x: 6, y: 5, kind: "shop" }], "town")).toBeNull();
    // 最近的優先
    expect(workSide({ x: 5, y: 5 }, [{ x: 3, y: 5, kind: "tavern" }, { x: 6, y: 5, kind: "shop" }], "keeper")).toBe("east");
    const scene = fieldAmbient({
      map_id: "mist_ferry_smithy",
      npcs: [{ id: "smith_shi", name_zh: "石師傅", x: 3, y: 2 }],
      facilities: [{ kind: "smithy", x: 4, y: 2 }],
      campfires: [],
    } as unknown as FieldView);
    expect(scene.sides).toEqual({ npc_smith_shi: "east" });
  });

  it("待機驅動：職業動作時用側面畫，做完以 undefined（原本的朝向）換回站好", () => {
    const motion = new IdleMotion();
    motion.scene = { key: "mist_ferry_smithy", roles: { npc_smith_shi: "smith" }, sides: { npc_smith_shi: "west" }, fires: [] };
    const c = new Container();
    const body = new Sprite(Texture.EMPTY);
    body.label = BODY_LABEL;
    c.addChild(body);
    const units = new Map([["npc_smith_shi", c]]);
    const draws = new Map<string, UnitDraw>([["npc_smith_shi", { id: "npc_smith_shi", facing: "south", downed: false, statusIds: [] } as unknown as UnitDraw]]);
    const log: { pose: InkPose | null; facing: Facing | undefined }[] = [];
    for (let t = 0; t < SPAN; t += STEP) motion.tick(STEP, units, draws, (_id, _s, pose, facing) => log.push({ pose, facing }));
    const sides = log.filter((e) => e.facing !== undefined);
    expect(sides.length).toBeGreaterThan(0);
    expect(sides.every((e) => e.facing === "west" && e.pose !== null)).toBe(true);
    // 每一次「側面 → 站好」都是 pose=null、facing=undefined
    for (let i = 1; i < log.length; i++) {
      if (log[i - 1]!.facing !== undefined && log[i]!.pose === null) expect(log[i]!.facing).toBeUndefined();
    }
    expect(log.some((e, i) => i > 0 && log[i - 1]!.facing !== undefined && e.pose === null)).toBe(true);
  });
});
