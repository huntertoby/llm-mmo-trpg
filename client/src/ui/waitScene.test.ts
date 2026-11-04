// RT-3：等待動畫（C 羽毛筆羊皮紙）。四個場合的挑選、墨色依區域（拿不到退回 hub）、確定性、減少動態靜止、
// 短句輪替、等待聲的對應（NPC 聊天不出聲）、捲動區上下緣漸隱、不新增 Math.random。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { SFX_TABLE } from "../audio/sfxLibrary";
import { peakOf, renderSfx, sfxSeed, type SfxDef } from "../audio/synth";
import { UI_SOUNDS } from "../audio/uiSounds";
import { WAIT_SOUND_DELAY_MS, WAIT_SOUNDS, waitSoundCount } from "../audio/waitSounds";
import {
  drawWait,
  partialPolyline,
  skillGlyphIndex,
  SKILL_GLYPHS,
  STATIC_T,
  waitPalette,
  waitPhase,
  WAIT_CYCLE_MS,
  WAIT_SIZE,
  type WaitFrame,
  type WaitStatus,
} from "../render/waitArt";
import { readSources, readStyleFiles, stripCssComments, stripTsComments } from "../test/sourceScan";
import { PregenWaitDialog } from "../world/PregenWaitDialog";
import { pregenRequestId } from "../world/pregen";
import { scrolledFlag } from "./PopupFrame";
import { regionThemeFor } from "./regionTheme";
import { WaitScene } from "./WaitScene";
import { parseWaitNarration, WAIT_NARRATION, WAIT_SCENES, waitLine, waitSeed, type WaitSceneId } from "./waitNarration";

/** 記錄所有呼叫的假 Canvas 2D。 */
function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const fmt = (a: unknown): string => (typeof a === "number" ? a.toFixed(3) : typeof a === "string" ? a : typeof a);
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map(fmt).join(",")})`);
        if (prop === "createRadialGradient" || prop === "createLinearGradient") return { addColorStop: () => undefined };
        return undefined;
      };
    },
    set(target, prop: string, value) {
      target[prop] = value;
      calls.push(`${prop}=${String(value)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, calls };
}

const frame = (scene: WaitSceneId, t: number, over: Partial<WaitFrame> = {}): WaitFrame => ({
  scene,
  t,
  seed: waitSeed("test"),
  palette: waitPalette(regionThemeFor("capital")),
  reduced: false,
  status: "wait",
  ...over,
});
const record = (f: WaitFrame): string[] => {
  const { ctx, calls } = mockCtx();
  drawWait(ctx, f);
  return calls;
};

describe("四個場合", () => {
  it("四個場合、各自的大小與節奏（技能 3.2 秒、判定 1.4 秒、聊天 0.9 秒、回顧 2.6 秒）", () => {
    expect([...WAIT_SCENES]).toEqual(["skill", "judge", "npc", "retell"]);
    expect(WAIT_CYCLE_MS).toEqual({ skill: 3200, judge: 1400, npc: 900, retell: 2600 });
    expect(WAIT_SIZE.skill).toEqual({ w: 120, h: 120 });
    expect(WAIT_SIZE.judge).toEqual({ w: 80, h: 80 });
    expect(WAIT_SIZE.npc.w).toBeLessThan(WAIT_SIZE.judge.w);
  });

  it("四個場合畫出來不一樣（同一刻、同一區）", () => {
    const sigs = WAIT_SCENES.map((s) => record(frame(s, 600)).join("|"));
    expect(new Set(sigs).size).toBe(4);
  });

  it("預先生成的等待提示（閃現、機遇）用「技能生成」，取消鈕照舊", () => {
    const html = renderToStaticMarkup(createElement(PregenWaitDialog, { text: "說書人正在構思這招的變化……", requestId: "flash:s::", onCancel: () => undefined }));
    expect(html).toContain('data-scene="skill"');
    expect(html).toContain('data-testid="world-pregen-cancel"');
    expect(html).toContain('data-testid="world-pregen-wait"');
    expect(pregenRequestId({ kind: "flash", skill: "a", slot: 1, category: null })).toBe("flash:a:1:");
    expect(pregenRequestId({ kind: "opportunity", solution: 2 })).toBe("opportunity:2");
  });

  it("事件判定接在情境判定的「擲骰」、NPC 聊天接在聊天的「說」（原始碼）", () => {
    const sources = Object.fromEntries(readSources().map(([p, t]) => [p, stripTsComments(t, p)]));
    expect(sources["world/EventCard.tsx"]).toMatch(/<WaitScene\s+scene="judge"/);
    expect(sources["world/EventCard.tsx"]).toMatch(/onClick=\{submit\} data-testid="world-answer-submit"/);
    expect(sources["world/NpcPanel.tsx"]).toMatch(/<WaitScene\s+scene="npc"/);
    expect(sources["world/PregenWaitDialog.tsx"]).toMatch(/<WaitScene scene="skill"/);
    // 舊的全域墨痕聲拿掉了（改由等待動畫依場合放）
    expect(sources["screens/WorldScreen.tsx"]).not.toContain("useInkWaitSound");
  });

  it("元件標出場合、狀態與區域；失敗時有重試鈕、完成時不顯示句子", () => {
    for (const scene of WAIT_SCENES) {
      const html = renderToStaticMarkup(createElement(WaitScene, { scene, requestId: "r", region: "cloud_ridge", name: "葛蘭" }));
      expect(html).toContain(`data-scene="${scene}"`);
      expect(html).toContain('data-region="cloud_ridge"');
      expect(html).toContain('data-status="wait"');
    }
    const fail = renderToStaticMarkup(createElement(WaitScene, { scene: "judge", requestId: "r", status: "fail", onRetry: () => undefined }));
    expect(fail).toContain(WAIT_NARRATION.fail);
    expect(fail).toContain("再試一次");
    const done = renderToStaticMarkup(createElement(WaitScene, { scene: "skill", requestId: "r", status: "done" }));
    expect(done).not.toContain("wait-line");
  });
});

describe("墨色、封蠟依區域", () => {
  it("三區（主城、雲嶺、荒原）的墨色、封蠟都不同；點綴：荒原火星、主城紫晶光、雲嶺沒有", () => {
    const pals = ["capital", "cloud_ridge", "ashen_waste"].map((r) => waitPalette(regionThemeFor(r)));
    expect(new Set(pals.map((p) => p.ink)).size).toBe(3);
    expect(new Set(pals.map((p) => p.seal)).size).toBe(3);
    expect(pals.map((p) => p.fx)).toEqual(["crystal", "none", "ember"]);
    expect(pals[2]!.ink).toBe(regionThemeFor("ashen_waste").ink);
  });

  it("拿不到區域（null、空字串、不認得）退回 hub", () => {
    const hub = waitPalette(regionThemeFor("hub"));
    for (const r of [null, undefined, "", "nowhere"]) expect(waitPalette(regionThemeFor(r))).toEqual(hub);
    const html = renderToStaticMarkup(createElement(WaitScene, { scene: "npc", requestId: "r", region: null }));
    expect(html).toContain('data-region="hub"');
  });

  it("畫面真的用到區域色：沙子、封蠟換區就換", () => {
    const cloud = record(frame("judge", 900, { palette: waitPalette(regionThemeFor("cloud_ridge")) })).join("|");
    const ashen = record(frame("judge", 900, { palette: waitPalette(regionThemeFor("ashen_waste")) })).join("|");
    expect(cloud).toContain(`fillStyle=${regionThemeFor("cloud_ridge").seal}`);
    expect(ashen).toContain(`fillStyle=${regionThemeFor("ashen_waste").seal}`);
    expect(cloud).not.toBe(ashen);
  });

  it("失敗時變灰（不用區域色、沒有點綴）", () => {
    const grey = waitPalette(regionThemeFor("ashen_waste"), { grey: true });
    expect(grey.fx).toBe("none");
    const calls = record(frame("skill", 2500, { palette: grey, status: "fail" })).join("|");
    expect(calls).not.toContain(regionThemeFor("ashen_waste").seal);
    expect(calls).not.toContain(regionThemeFor("ashen_waste").ink);
  });
});

describe("確定性", () => {
  afterEach(() => undefined);

  it("同時間、同種子、同狀態畫兩次完全一樣；時間不同就不同（動畫有在動）", () => {
    for (const scene of WAIT_SCENES) {
      expect(record(frame(scene, 700))).toEqual(record(frame(scene, 700)));
      expect(record(frame(scene, 300)).join("|")).not.toBe(record(frame(scene, 700)).join("|"));
    }
  });

  it("不用 Math.random（換成會丟例外的函式也畫得出來）", () => {
    const orig = Math.random;
    Math.random = () => {
      throw new Error("不可以用 Math.random");
    };
    try {
      for (const scene of WAIT_SCENES)
        for (const status of ["wait", "done", "fail"] as WaitStatus[])
          for (const t of [0, 500, 1500, 3100]) expect(() => record(frame(scene, t, { status, doneT: 150, palette: waitPalette(regionThemeFor("ashen_waste")) }))).not.toThrow();
    } finally {
      Math.random = orig;
    }
  });

  it("技能生成的圖樣照請求編號挑；還沒好就換一個（下一輪一定不同）", () => {
    const seed = waitSeed("flash:a::");
    expect(waitSeed("flash:a::")).toBe(seed);
    for (let c = 0; c < 10; c++) {
      expect(skillGlyphIndex(seed, c)).toBeGreaterThanOrEqual(0);
      expect(skillGlyphIndex(seed, c)).toBeLessThan(SKILL_GLYPHS);
      expect(skillGlyphIndex(seed, c + 1)).not.toBe(skillGlyphIndex(seed, c));
    }
    expect(waitPhase("skill", 3200 * 2 + 1600)).toEqual({ cycle: 2, p: 0.5 });
  });

  it("折線取部分：筆尖在路徑上、取全部時是終點", () => {
    const pts = [
      [0, 0],
      [10, 0],
      [10, 10],
    ] as const;
    expect(partialPolyline(pts, 0.5).tip).toEqual([10, 0]);
    expect(partialPolyline(pts, 0.25).tip).toEqual([5, 0]);
    expect(partialPolyline(pts, 1).tip).toEqual([10, 10]);
  });
});

describe("減少動態", () => {
  it("每個場合都是靜態版：不論時間多少，畫面完全一樣", () => {
    for (const scene of WAIT_SCENES) {
      const a = record(frame(scene, 0, { reduced: true }));
      for (const t of [333, 1200, 5000, 99999]) expect(record(frame(scene, t, { reduced: true }))).toEqual(a);
    }
  });

  it("靜態版各自不同（技能＝畫好的圖樣、判定＝停住的沙漏、聊天＝三個墨點、回顧＝寫了一半）", () => {
    const sigs = WAIT_SCENES.map((s) => record(frame(s, 0, { reduced: true })).join("|"));
    expect(new Set(sigs).size).toBe(4);
    // 技能生成的靜態版有封蠟與金邊（畫好的），判定的靜態版有沙但沒有流下的沙粒
    expect(STATIC_T.skill / WAIT_CYCLE_MS.skill).toBeGreaterThan(0.9);
    const npc = record(frame("npc", 0, { reduced: true })).filter((c) => c.startsWith("ellipse("));
    expect(npc).toHaveLength(3);
  });

  it("減少動態時完成直接出卡（不淡入）", () => {
    const a = record(frame("skill", 0, { reduced: true, status: "done", doneT: 0 }));
    const b = record(frame("skill", 0, { reduced: true, status: "done", doneT: 300 }));
    expect(a).toEqual(b);
  });

  it("句子照常換但不淡入淡出（CSS）", () => {
    const styles = Object.fromEntries(readStyleFiles().map(([p, t]) => [p, stripCssComments(t)]));
    const css = styles["ui/waitScene.css"] ?? "";
    expect(css).toMatch(/\.wait-scene\.still \.wait-line \{\s*animation: none;/);
    expect(css).toMatch(/:root\[data-reduced-motion="true"\] \.wait-line \{\s*animation: none;/);
  });
});

describe("短句", () => {
  it("內容檔：四個場合各一組，失敗句，4 秒輪替、8 秒提示", () => {
    expect(WAIT_NARRATION.rotate_ms).toBe(4000);
    expect(WAIT_NARRATION.long_ms).toBe(8000);
    expect(WAIT_NARRATION.scenes.skill.lines).toHaveLength(4);
    expect(WAIT_NARRATION.scenes.judge.lines[0]).toBe("沙漏翻了過來……");
    expect(WAIT_NARRATION.fail).toBe("說書人停下了筆，再試一次？");
    const all = [WAIT_NARRATION.fail, ...WAIT_SCENES.flatMap((s) => [...WAIT_NARRATION.scenes[s].lines, WAIT_NARRATION.scenes[s].long])].join("");
    for (const w of ["墨滴", "宣紙", "蘸墨"]) expect(all).not.toContain(w);
    expect(all.replaceAll("羽毛筆", "")).not.toContain("毛筆");
  });

  it("第一句照請求編號挑（確定性），每 4 秒換下一句，8 秒後提示句和一般句交替", () => {
    const lines = WAIT_NARRATION.scenes.skill.lines;
    const a0 = waitLine("skill", 0, "req-1");
    expect(waitLine("skill", 3999, "req-1")).toEqual(a0);
    const a1 = waitLine("skill", 4000, "req-1");
    expect(a1.slot).toBe(1);
    expect(lines.indexOf(a1.text)).toBe((lines.indexOf(a0.text) + 1) % lines.length);
    const long = waitLine("skill", 8000, "req-1");
    expect(long.long).toBe(true);
    expect(long.text).toBe(WAIT_NARRATION.scenes.skill.long);
    expect(waitLine("skill", 12000, "req-1").long).toBe(false);
    expect(waitLine("skill", 16000, "req-1").long).toBe(true);
    // 不同請求可能從不同句開始，但同一個請求永遠一樣
    const starts = new Set(["a", "b", "c", "d", "e", "f", "g", "h"].map((r) => waitLine("skill", 0, r).text));
    expect(starts.size).toBeGreaterThan(1);
  });

  it("NPC 的句子帶名字；失敗時一律換成失敗句", () => {
    expect(waitLine("npc", 0, "x", { name: "葛蘭" }).text).toMatch(/^葛蘭/);
    expect(waitLine("npc", 9000, "x", { name: "葛蘭" }).text).toBe("葛蘭似乎有很多話要說。");
    expect(waitLine("retell", 5000, "x", { failed: true }).text).toBe(WAIT_NARRATION.fail);
  });

  it("壞掉的內容檔退回內建的句子", () => {
    const bad = parseWaitNarration("rotate_ms: x\nscenes:\n  skill: {lines: []}\n");
    expect(bad.rotate_ms).toBe(4000);
    expect(bad.scenes.skill.lines.length).toBeGreaterThan(0);
    expect(parseWaitNarration("::: not yaml").fail).toBe("說書人停下了筆，再試一次？");
  });
});

describe("等待聲（AU-2 檢查待決 3）", () => {
  it("技能生成＝羽毛筆刮紙、事件判定＝沙漏細沙、NPC 聊天＝不出聲、多講一點＝翻頁", () => {
    expect(WAIT_SOUNDS.skill?.id).toBe("ui_wait_quill");
    expect(WAIT_SOUNDS.judge?.id).toBe("ui_wait_sand");
    expect(WAIT_SOUNDS.npc).toBeNull();
    expect(WAIT_SOUNDS.retell?.id).toBe("ui_wait_page");
    expect(UI_SOUNDS).not.toContain("ui_ink_wait" as never);
  });

  it("0.7 秒的規則保留：之前不出聲，之後照間隔；NPC 聊天永遠不出聲", () => {
    expect(WAIT_SOUND_DELAY_MS).toBe(700);
    expect(waitSoundCount("skill", 699)).toBe(0);
    expect(waitSoundCount("skill", 700)).toBe(1);
    expect(waitSoundCount("skill", 700 + 1600)).toBe(2);
    expect(waitSoundCount("judge", 700 + 1400 * 3)).toBe(4);
    expect(waitSoundCount("npc", 60_000)).toBe(0);
  });

  it("三個等待聲在參數表裡、算得出聲音、確定性、彼此不同", () => {
    const waves: Float32Array[] = [];
    for (const id of ["ui_wait_quill", "ui_wait_sand", "ui_wait_page"]) {
      const def = SFX_TABLE.defs[id] as SfxDef | undefined;
      expect(def?.cat, id).toBe("ui");
      const w = renderSfx(def!, { sampleRate: 8000, seed: sfxSeed(id) });
      const again = renderSfx(def!, { sampleRate: 8000, seed: sfxSeed(id) });
      expect(Array.from(w)).toEqual(Array.from(again));
      expect(peakOf(w)).toBeGreaterThan(0.005);
      expect(peakOf(w)).toBeLessThanOrEqual(1);
      waves.push(w);
    }
    expect(new Set(waves.map((w) => w.length)).size).toBe(3);
  });
});

describe("捲動區上下緣漸隱（UI-E1b 待決 10；美術 PM：下緣加深加高）", () => {
  const styles = Object.fromEntries(readStyleFiles().map(([p, t]) => [p, stripCssComments(t)]));
  const theme = styles["styles/theme.css"] ?? "";
  it("上緣：sticky、不佔版面、沒捲時不顯示，捲下去才蓋住切半的字（RT-3b：加高到 56px、上 60% 實色）", () => {
    expect(theme).toMatch(/\.ui-popup-dialog > \.ui-popup-body::before,[^{]*\{[^}]*position: sticky;[^}]*top: 0;[^}]*height: 56px;[^}]*margin-bottom: -56px;[^}]*opacity: 0;[^}]*var\(--ui-navy\) 40%/);
    expect(theme).toMatch(/\.ui-popup-dialog > \.ui-popup-body\[data-scrolled="1"\]::before,[^{]*\{\s*opacity: 1;/);
    expect(scrolledFlag(0)).toBe("0");
    expect(scrolledFlag(1)).toBe("1");
  });
  it("下緣：加高到 32px、後 55% 實色", () => {
    expect(theme).toMatch(/\.ui-popup-dialog > \.ui-popup-body::after \{[^}]*height: 32px;[^}]*var\(--ui-navy\) 45%/);
  });
});

describe("RT-3 的檔案不用 Math.random、不用原生 title=", () => {
  it("掃原始碼", () => {
    const files = ["render/waitArt.ts", "ui/WaitScene.tsx", "ui/waitNarration.ts", "audio/waitSounds.ts", "dev/waitGallery.tsx", "world/PregenWaitDialog.tsx"];
    const sources = Object.fromEntries(readSources().map(([p, t]) => [p, stripTsComments(t, p)]));
    for (const f of files) {
      const text = sources[f];
      expect(text, f).toBeDefined();
      expect(text, f).not.toContain("Math.random");
      expect(text, f).not.toMatch(/<[a-z][\w-]*\s[^>]*\btitle=/); // 原生元素的 title（DialogFrame 的 title prop 不算）
    }
  });
});
