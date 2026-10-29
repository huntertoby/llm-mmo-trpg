// 開發用入口（Phase 3U-3）：不打戰鬥就直接進戰後畫面（裝備三選一、升級選技、完整技能三選一、營火、一輪結束）。
// 只在網址帶 `?dev=1` 時啟用，伺服器還要設環境變數 `TRPG_DEV_ROUTES=1`（否則 404）。
// 用法：開 `/?dev=1&screen=level_up`（`screen` 見 `DEV_SCREENS`），或在頁面裡 `await window.__layoutSmoke.enterDevScreen("campfire")`。
import { api } from "../api/client";
import type { RunResponse } from "../api/types";

export const DEV_SCREENS = ["gear_offer", "level_up", "complete_offer", "campfire", "ended"] as const;
export type DevScreen = (typeof DEV_SCREENS)[number];

/** 固定種子（這個種子的 AI 打得到營火）。 */
export const DEV_SEED = 1;
export const DEV_ENTER_EVENT = "trpg:dev-enter-run";

export function devScreenParam(search: string): DevScreen | null {
  const params = new URLSearchParams(search);
  const dev = params.get("dev");
  if (dev !== "1" && dev !== "true") return null;
  const screen = params.get("screen");
  return DEV_SCREENS.find((s) => s === screen) ?? null;
}

/** 以第一個開發者起始包、固定種子開一輪，再代打到指定畫面。 */
export async function createDevRun(to: DevScreen): Promise<RunResponse> {
  const packs = await api.devPacks();
  const first = packs[0];
  if (first === undefined) throw new Error("沒有開發者起始包");
  const run = await api.createRun({ dev_pack: first.id, seed: DEV_SEED });
  return api.devAdvance(run.run_id, to);
}

/** 建立並直接進入該畫面（App 聽 `DEV_ENTER_EVENT`）。 */
export async function enterDevScreen(to: DevScreen, win: Window = window): Promise<RunResponse> {
  const run = await createDevRun(to);
  win.dispatchEvent(new CustomEvent<RunResponse>(DEV_ENTER_EVENT, { detail: run }));
  return run;
}
