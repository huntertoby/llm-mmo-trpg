// 數值工坊（NW-1b）的非同步流程：入口探測、存草稿＋差異、模擬輪詢、寫回。只靠注入的 `TuningApi`，vitest 用假的 API 測。
import { ApiError, api as realApi } from "../api/client";
import type { TuningChangeIn, TuningDiff, TuningSimJob } from "../api/types";
import { entryFromError, SIM_POLL_MS, type EntryState } from "./model";

/** 畫面用到的 API（`api/client.ts` 的子集）。 */
export type TuningApi = Pick<
  typeof realApi,
  | "tuningStatus"
  | "tuningObjects"
  | "tuningObject"
  | "tuningDraft"
  | "tuningPutDraft"
  | "tuningDeleteDraft"
  | "tuningCheck"
  | "tuningDiff"
  | "tuningApply"
  | "tuningRevert"
  | "tuningHistory"
  | "tuningSimOptions"
  | "tuningStartSim"
  | "tuningSim"
  | "tuningCancelSim"
  | "tuningBudget"
  | "tuningGroupPreview"
  | "tuningPresets"
  | "tuningLadders"
  | "skill"
>;

export function errorText(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

/** 開發選單的入口：問一次 `/status`，回「已開啟／未開啟（附怎麼開）／被擋／連不到」。 */
export async function probeEntry(tapi: Pick<TuningApi, "tuningStatus">): Promise<EntryState> {
  try {
    await tapi.tuningStatus();
    return { kind: "open" };
  } catch (e) {
    if (e instanceof ApiError) return entryFromError(e.status, e.message);
    return entryFromError(0, errorText(e));
  }
}

/** 寫回前：先把畫面上的改動存成草稿，再拿差異（後端照存下來的草稿寫回）。 */
export async function saveAndDiff(tapi: Pick<TuningApi, "tuningPutDraft" | "tuningDiff">, name: string, changes: TuningChangeIn[]): Promise<TuningDiff> {
  await tapi.tuningPutDraft(name, changes);
  return tapi.tuningDiff(name);
}

export type Wait = (ms: number) => Promise<void>;
export const realWait: Wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * 每秒問一次模擬進度，直到不是 `running`；每次都回報給畫面。`stopped()` 為真（離開畫面）就不再問。
 * 問失敗（例如伺服器重開、工作不見了）回傳一個 `failed` 狀態，畫面照樣顯示原因。
 */
export async function pollSim(
  tapi: Pick<TuningApi, "tuningSim">,
  first: TuningSimJob,
  onUpdate: (job: TuningSimJob) => void,
  stopped: () => boolean,
  wait: Wait = realWait,
): Promise<TuningSimJob> {
  let job = first;
  onUpdate(job);
  while (job.state === "running") {
    await wait(SIM_POLL_MS);
    if (stopped()) return job;
    try {
      job = await tapi.tuningSim(job.job_id);
    } catch (e) {
      job = { ...job, state: "failed", error_zh: `讀不到模擬進度：${errorText(e)}` };
    }
    if (stopped()) return job;
    onUpdate(job);
  }
  return job;
}
