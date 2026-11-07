import { describe, expect, it } from "vitest";
import type { LookChoice } from "../api/types";
import { enemySheetSpec } from "./qGallery";

describe("QK-5c 盜賊畫廊", () => {
  it("弓手格拿弓（有範本外觀＋custom 時也是），其他範本照舊", () => {
    const cs: LookChoice[] = [{ hair: "spiky", beard: "none" }, { hair: "bob", beard: "stubble" }];
    for (const c of cs) {
      expect(enemySheetSpec("bandit_archer", c).gear.main_hand?.kind).toBe("bow");
      expect(enemySheetSpec("bandit", c).gear.main_hand?.kind).not.toBe("bow");
    }
  });
});
