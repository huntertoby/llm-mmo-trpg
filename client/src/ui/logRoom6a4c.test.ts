// Phase 6A-4c（併入 6A-3 驗收結論）：選取時戰鬥紀錄縮短讓開選取面板；兩段選取的「已選定○○」留在「?」旁。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { compositePickedTag, compositePrompt } from "../battle/composite";
import { LOG_DOCK_BOTTOM, LOG_MIN_PX, LOG_ROOM_GAP, logLimit, logRoom } from "../battle/logRoom";
import { hurlPickedTag, hurlPromptText } from "../battle/targeting";
import { BattleLogDockView } from "./BattleLogDock";
import { OpHintView } from "./OpHint";

const dock = (limit: ReturnType<typeof logLimit>, open = true, pinned = false) =>
  renderToStaticMarkup(
    createElement(BattleLogDockView, {
      toasts: [],
      open,
      pinned,
      onToggleOpen: () => undefined,
      onTogglePin: () => undefined,
      log: () => createElement("div", { className: "battle-log" }, "紀錄"),
      limit,
    }),
  );

describe("選取時紀錄縮短讓開", () => {
  it("最大高度 ＝ 選取面板底下到紀錄底部、留 8px", () => {
    expect(logRoom(600, 200)).toBe(600 - LOG_DOCK_BOTTOM - 200 - LOG_ROOM_GAP);
    expect(LOG_ROOM_GAP).toBe(8);
  });

  it("沒有選取時不限（恢復原本的高度）", () => {
    expect(logRoom(600, null)).toBeNull();
    expect(logLimit(null)).toBeNull();
    const html = dock(null);
    expect(html).not.toContain("squeezed");
    expect(html).not.toContain("max-height");
  });

  it("空間夠時照可用高度縮短，不超過原本的 58%", () => {
    expect(logLimit(300)).toEqual({ maxHeight: 300, tight: false });
    const html = dock(logLimit(300));
    expect(html).toContain("log-dock open squeezed");
    expect(html).toContain("max-height:min(58%, 300px)");
  });

  it("不到 3 行時只顯示最新 3 行（可捲動）", () => {
    expect(logLimit(40)).toEqual({ maxHeight: LOG_MIN_PX, tight: true });
    expect(logLimit(-20)?.tight).toBe(true);
    const html = dock(logLimit(40));
    expect(html).toContain("squeezed tight");
    expect(html).toContain(`max-height:${LOG_MIN_PX}px`);
  });

  it("釘住的也縮", () => {
    const html = dock(logLimit(200), true, true);
    expect(html).toContain("log-dock open pinned squeezed");
    expect(html).toContain("max-height:min(58%, 200px)");
  });
});

describe("兩段選取的「已選定○○」留在「?」旁", () => {
  it("收起時「?」旁有小標籤；完整句子時不另加", () => {
    const collapsed = renderToStaticMarkup(createElement(OpHintView, { full: false, label: "投擲", text: "句子", tag: "已舉起木箱" }));
    expect(collapsed).toContain('data-testid="op-hint-q"');
    expect(collapsed).toContain('class="op-hint-tag"');
    expect(collapsed).toContain("已舉起木箱");
    const full = renderToStaticMarkup(createElement(OpHintView, { full: true, label: "投擲", text: "句子", tag: "已舉起木箱" }));
    expect(full).not.toContain("op-hint-tag");
    const none = renderToStaticMarkup(createElement(OpHintView, { full: false, label: "投擲", text: "句子" }));
    expect(none).not.toContain("op-hint-tag");
  });

  it("小標籤與說明句裡的狀態一致", () => {
    expect(hurlPickedTag("木箱")).toBe("已舉起木箱");
    expect(hurlPickedTag("盜賊", "shadowstep")).toBe("已鎖定盜賊");
    expect(hurlPromptText("木箱", 3, 2)).toContain(hurlPickedTag("木箱"));
    const first = { pos: { x: 3, y: 4 } } as Parameters<typeof compositePickedTag>[0];
    expect(compositePickedTag(first)).toBe("已選定落點 (3, 4)");
    expect(compositePrompt(first, 2)).toContain("已選定落點 (3, 4)");
  });
});
