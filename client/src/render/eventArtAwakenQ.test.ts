// QK-2：主城開場 ① 醒來插圖恢復（Q 版半坐起）。C 的擺法鎖在 world/capitalOpeningReview.test.ts。
import { afterEach, describe, expect, it } from "vitest";
import { AWAKEN_HERO, AWAKEN_HERO_Q, AWAKEN_SIT_POSE_Q, awakenHero } from "./eventArtAwaken";
import { dollSkin, setDollSkin } from "./inkStyle";

const keep = dollSkin();
afterEach(() => setDollSkin(keep));

describe("QK-2：Q 版的醒來擺法", () => {
  it("Q 版走 Q 的半坐起；C 照舊", () => {
    setDollSkin("q");
    expect(awakenHero(1)).toBe(AWAKEN_HERO_Q[1]);
    expect(awakenHero(1).pose).toBe(AWAKEN_SIT_POSE_Q);
    setDollSkin("c");
    expect(awakenHero(1)).toBe(AWAKEN_HERO[1]);
  });

  it("躺姿與位置不動，只換半坐起的姿勢與下放量（腿平貼、屁股貼地、手往後撐）", () => {
    expect(AWAKEN_HERO_Q[0]).toBe(AWAKEN_HERO[0]);
    expect(AWAKEN_HERO_Q[1].x).toBe(AWAKEN_HERO[1].x);
    expect(AWAKEN_HERO_Q[1].y).toBe(AWAKEN_HERO[1].y);
    expect(AWAKEN_HERO_Q[1].rot).toBe(0);
    expect(AWAKEN_HERO_Q[1].drop).toBeGreaterThan(3);
    expect(AWAKEN_HERO_Q[1].drop).toBeLessThan(6);
    expect(AWAKEN_SIT_POSE_Q.lean ?? 0).toBeLessThan(-0.5);
    expect(AWAKEN_SIT_POSE_Q.armF ?? 0).toBeGreaterThan(AWAKEN_SIT_POSE_Q.arm ?? 0); // 遠側的手再往後
    expect((AWAKEN_SIT_POSE_Q as { reach?: number }).reach).toBeUndefined(); // Q 版不拉長臂長
  });
});
