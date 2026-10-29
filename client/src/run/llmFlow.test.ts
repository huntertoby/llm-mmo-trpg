import { describe, expect, it } from "vitest";
import type { LlmStats, OfferTag } from "../api/types";
import { LLM_SOURCE_LABEL, isLlmTag, llmSummaryLines, withLlm } from "./llmFlow";

const stats = (over: Partial<LlmStats> = {}): LlmStats => ({
  total: 5,
  succeeded: 3,
  failed: 2,
  fallback_permille: 400,
  attempts: 9,
  alert_permille: 200,
  alert: true,
  named: 3,
  name_generated: 2,
  name_fallback: 1,
  ...over,
});

const tag = (source: OfferTag["source"]): OfferTag => ({ kind: "new", label_zh: "新方向", keywords: [], fallback: false, source });

describe("LLM 開關", () => {
  it("關閉時開局欄位原樣不變（不帶 llm）", () => {
    const body = { weapon: "fire_staff", keywords: ["a", "b"], seed: 1 };
    expect(withLlm(body, false)).toBe(body);
    expect("llm" in withLlm(body, false)).toBe(false);
    expect(withLlm(body, true)).toEqual({ ...body, llm: true });
  });

  it("來源為 llm 的候選卡才有標記", () => {
    expect(LLM_SOURCE_LABEL).not.toBe("");
    expect(isLlmTag(tag("llm"))).toBe(true);
    expect(isLlmTag(tag("composer"))).toBe(false);
    expect(isLlmTag(tag("pool"))).toBe(false);
    expect(isLlmTag(undefined)).toBe(false);
  });

  it("一輪摘要：題數、退回率、命名、提醒", () => {
    const lines = llmSummaryLines(stats());
    expect(lines[0]).toBe("LLM 提議 5 題：成功 3、退回 2（40.0%），呼叫 9 次");
    expect(lines[1]).toBe("命名 3 個：生成 2、組合式名稱 1");
    expect(lines[2]).toBe("提醒：退回率超過 20%");
    expect(llmSummaryLines(stats({ alert: false, named: 0 }))).toHaveLength(1);
    expect(llmSummaryLines(null)).toEqual([]);
  });
});
