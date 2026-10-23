import { describe, expect, it } from "vitest";
import type { BattleResponse } from "../api/types";
import {
  AI_PAUSE_MS,
  CRAWL_FACTOR,
  devAnimFactor,
  FEEDBACK_MS,
  frameOps,
  PLAY_SPEEDS,
  playbackPlan,
  remainingLines,
  SPEED_SCALE,
  type Frame,
  type PlaySpeed,
} from "./playback";
import fixture from "./fixtures/oil_depot_seed3.json";

const response = fixture as unknown as BattleResponse;
const hero = response.hero_id;

describe("playbackPlan", () => {
  it("has one frame per step and ends on the response view", () => {
    const plan = playbackPlan(response, hero, "normal");
    expect(plan.frames).toHaveLength(response.steps.length);
    expect(plan.initialView).toBe(response.initial_view);
    expect(plan.finalView).toBe(response.view);
    expect(plan.frames.at(-1)?.view).toEqual(response.view);
  });

  it("starts with the opening step: no actor, no pause", () => {
    const first = playbackPlan(response, hero, "normal").frames[0]!;
    expect(first.actorId).toBeNull();
    expect(first.pauseMs).toBe(0);
    expect(first.lines.length).toBeGreaterThan(0);
  });

  it("orders each frame mark, moves, view, log, pause", () => {
    const plan = playbackPlan(response, hero, "normal");
    const withMoves = plan.frames.find((f) => f.moves.length > 0 && f.lines.length > 0 && f.pauseMs > 0)!;
    const kinds = frameOps(withMoves).map((o) => o.op);
    const firstView = kinds.indexOf("view");
    expect(kinds[0]).toBe("mark");
    expect(kinds.slice(1, firstView).every((k) => k === "move")).toBe(true);
    expect(kinds.slice(firstView)).toEqual(["view", "log", "pause"]);
  });

  it("pauses 500 ms after an AI action, 150 ms when fast, none for end_turn steps", () => {
    const normal = playbackPlan(response, hero, "normal");
    const fast = playbackPlan(response, hero, "fast");
    const idx = response.steps.findIndex(
      (s) => s.actor_id !== null && s.actor_id !== hero && !["end_turn", "move"].includes(s.step?.type ?? ""),
    );
    const moveIdx = response.steps.findIndex((s) => s.actor_id !== null && s.actor_id !== hero && s.step?.type === "move");
    expect(normal.frames[moveIdx]!.pauseMs).toBe(150);
    expect(normal.frames[idx]!.pauseMs).toBe(500);
    expect(fast.frames[idx]!.pauseMs).toBe(150);
    const endIdx = response.steps.findIndex((s) => s.step?.type === "end_turn");
    expect(normal.frames[endIdx]!.pauseMs).toBe(0);
  });

  it("skip collapses everything into one frame with all log lines", () => {
    const normal = playbackPlan(response, hero, "normal");
    const skip = playbackPlan(response, hero, "skip");
    expect(skip.frames).toHaveLength(1);
    expect(skip.frames[0]!.moves).toEqual([]);
    expect(skip.frames[0]!.view).toEqual(response.view);
    expect(skip.frames[0]!.lines.map((l) => l.seq).sort()).toEqual(
      remainingLines(normal, 0).map((l) => l.seq).sort(),
    );
  });

  it("remainingLines gives the log of the frames not yet played", () => {
    const plan = playbackPlan(response, hero, "normal");
    const all = remainingLines(plan, 0);
    const tail = remainingLines(plan, 5);
    expect(tail.length).toBeLessThan(all.length);
    expect(remainingLines(plan, plan.frames.length)).toEqual([]);
  });

  it("has no frames when nothing advanced", () => {
    const idle = { ...response, steps: [], initial_view: response.view };
    expect(playbackPlan(idle, hero, "normal").frames).toEqual([]);
  });

  it("gives feedback for the steps: full time normally, half when fast, none when skipping", () => {
    const normal = playbackPlan(response, hero, "normal");
    const fast = playbackPlan(response, hero, "fast");
    const skip = playbackPlan(response, hero, "skip");
    const withItems = normal.frames.filter((f) => f.feedback.length > 0);
    expect(withItems.length).toBeGreaterThan(0);
    expect(withItems.every((f) => f.feedbackMs === FEEDBACK_MS)).toBe(true);
    expect(fast.frames.filter((f) => f.feedback.length > 0).every((f) => f.feedbackMs === FEEDBACK_MS / 2)).toBe(true);
    expect(skip.frames.every((f) => f.feedback.length === 0 && f.feedbackMs === 0)).toBe(true);
    const ops = frameOps(withItems[0]!).map((o) => o.op);
    expect(ops.indexOf("feedback")).toBe(ops.indexOf("view") + 1);
  });

  it("shortens move animations by speed (fast about half, skip none)", () => {
    const moves = (speed: PlaySpeed) =>
      playbackPlan(response, hero, speed).frames.flatMap((f) => f.moves);
    const total = (speed: PlaySpeed) => moves(speed).reduce((a, m) => a + m.durationMs, 0);
    expect(total("normal")).toBeGreaterThan(0);
    expect(Math.abs(total("fast") - total("normal") / 2)).toBeLessThanOrEqual(moves("normal").length / 2);
    expect(total("skip")).toBe(0);
  });

  it("has five speeds in order, and slow takes twice the normal time", () => {
    expect(PLAY_SPEEDS).toEqual(["crawl", "slow", "normal", "fast", "skip"]);
    const frames = (speed: PlaySpeed) => playbackPlan(response, hero, speed).frames;
    const sum = (speed: PlaySpeed, pick: (f: Frame) => number) => frames(speed).reduce((a, f) => a + pick(f), 0);
    const moveMs = (f: Frame) => f.moves.reduce((a, m) => a + m.durationMs, 0);
    expect(sum("normal", moveMs)).toBeGreaterThan(0);
    expect(Math.abs(sum("slow", moveMs) - 2 * sum("normal", moveMs))).toBeLessThanOrEqual(frames("normal").length);
    expect(sum("normal", (f) => f.pauseMs)).toBeGreaterThan(0);
    expect(sum("slow", (f) => f.pauseMs)).toBe(2 * sum("normal", (f) => f.pauseMs));
    expect(frames("slow").every((f) => f.feedbackMs === FEEDBACK_MS * 2)).toBe(true);
  });
});

describe("極慢與開發用的 ?anim=（2026-10-23 使用者：「幫我搞個極慢的速度」）", () => {
  it("極慢是正常的 5 倍時間（動畫倍率與停頓）", () => {
    expect(SPEED_SCALE.crawl).toBe(CRAWL_FACTOR * SPEED_SCALE.normal);
    expect(AI_PAUSE_MS.crawl).toBe(CRAWL_FACTOR * AI_PAUSE_MS.normal);
    const plan = playbackPlan(response, hero, "crawl");
    expect(plan.frames.every((f) => f.feedbackMs === FEEDBACK_MS * CRAWL_FACTOR)).toBe(true);
  });

  it.each([
    ["", 1],
    ["?anim=0.1", 10],
    ["?anim=0.5&dev=1", 2],
    ["?anim=1", 1],
    ["?anim=2", 1], // 不會加快
    ["?anim=0", 1], // 不合法
    ["?anim=abc", 1],
    ["?anim=0.001", 100], // 夾在 0.01
  ])("網址 %s → 時間倍率 %i", (search, factor) => {
    expect(devAnimFactor(search)).toBeCloseTo(factor);
  });
});
