// 6L-2：大世界 LLM 入口的預先生成等待。按閃現（或重閃）、選機遇解法之前，先問伺服器 LLM 的版本好了沒
// （`POST .../pregen/wait`，伺服器最多等 10 秒，超過改給組合器或模板版）。等超過 `PREGEN_HINT_DELAY_MS`
// 才顯示等待提示（共用彈窗 `DialogFrame`），可以取消；取消＝不送那個動作（沒有扣點）。
import type { PregenWaitRequest, WorldAction } from "../api/types";
import { WISH_ZH } from "./wish";

/** 等多久才顯示等待提示（毫秒）：已經好了的通常一下就回來，不閃一下彈窗。 */
export const PREGEN_HINT_DELAY_MS = 400;

/** 這個動作送出前要等的預先生成（不用等＝`null`）。 */
export function pregenWaitBody(action: WorldAction): PregenWaitRequest | null {
  if (action.kind === "flash") {
    return { kind: "flash", skill: action.skill, slot: action.slot ?? null, category: action.category ?? null };
  }
  if (action.kind === "event_solve") return { kind: "opportunity", solution: action.solution };
  // WP-3：文字許願先等 LLM（選單許願不呼叫 LLM、不用等）
  if (action.kind === "wish" && action.text != null && action.text !== "") return { kind: "wish", text: action.text };
  return null;
}

/** 等待提示的文字。 */
export function pregenWaitText(body: PregenWaitRequest): string {
  if (body.kind === "wish") return WISH_ZH.waitText;
  return body.kind === "flash" ? "說書人正在構思這招的變化……" : "說書人正在構思這份機遇……";
}

/** 等待動畫（RT-3 技能生成）的請求編號：同一個請求每次挑到同一句、同一個圖樣。 */
export function pregenRequestId(body: PregenWaitRequest): string {
  if (body.kind === "wish") return `wish:${body.text ?? ""}`;
  return body.kind === "flash" ? `flash:${body.skill ?? ""}:${body.slot ?? ""}:${body.category ?? ""}` : `opportunity:${body.solution ?? ""}`;
}
