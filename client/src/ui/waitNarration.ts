// 等待動畫的短句（RT-3；docs/archive/art/等待動畫.md 第 3 節）：`content/ui/narration_wait.yaml` 在 build 時以 `?raw` 匯入
// （內容即資料；Python 端 `trpg.content.ui_wait` 驗證同一份檔）。不呼叫 LLM。
// - 第一句照請求編號挑（確定性），之後每 `rotate_ms` 換下一句；
// - 等超過 `long_ms` 之後，提示句（`long`）和一般句子交替出現；
// - 失敗時一律是 `fail` 那一句；`{name}` 換成 NPC 的名字。
import { parse } from "yaml";
import waitYaml from "../../../content/ui/narration_wait.yaml?raw";
import { fmix32 } from "../render/attackVariants";
import { seedOf } from "../render/inkStyle";

export const WAIT_SCENES = ["skill", "judge", "npc", "retell"] as const;
export type WaitSceneId = (typeof WAIT_SCENES)[number];

export interface WaitSceneLines {
  lines: string[];
  long: string;
}

export interface WaitNarration {
  rotate_ms: number;
  long_ms: number;
  fail: string;
  scenes: Record<WaitSceneId, WaitSceneLines>;
}

/** 檔案壞掉時的退路（同 yaml 的第一句）。 */
const FALLBACK: WaitNarration = {
  rotate_ms: 4000,
  long_ms: 8000,
  fail: "說書人停下了筆，再試一次？",
  scenes: {
    skill: { lines: ["說書人攤開一張新的羊皮紙。"], long: "這一招比較複雜，羽毛筆還沒停。" },
    judge: { lines: ["沙漏翻了過來……"], long: "這一擲牽動的事比較多，再等一下。" },
    npc: { lines: ["{name}想了想……"], long: "{name}似乎有很多話要說。" },
    retell: { lines: ["說書人翻到前幾頁……"], long: "這段說來話長。" },
  },
};

const isObj = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const isText = (v: unknown): v is string => typeof v === "string" && v.trim() !== "";

/** yaml 文字 → 短句表；壞掉的欄位或場合用退路。 */
export function parseWaitNarration(text: string): WaitNarration {
  let doc: unknown;
  try {
    doc = parse(text);
  } catch {
    return FALLBACK;
  }
  if (!isObj(doc)) return FALLBACK;
  const num = (v: unknown, d: number): number => (typeof v === "number" && Number.isFinite(v) && v >= 1000 ? v : d);
  const scenesRaw = isObj(doc.scenes) ? doc.scenes : {};
  const scenes = {} as Record<WaitSceneId, WaitSceneLines>;
  for (const id of WAIT_SCENES) {
    const raw = scenesRaw[id];
    const lines = isObj(raw) && Array.isArray(raw.lines) ? raw.lines.filter(isText) : [];
    scenes[id] = isObj(raw) && lines.length > 0 && isText(raw.long) ? { lines, long: raw.long } : FALLBACK.scenes[id];
  }
  return { rotate_ms: num(doc.rotate_ms, FALLBACK.rotate_ms), long_ms: num(doc.long_ms, FALLBACK.long_ms), fail: isText(doc.fail) ? doc.fail : FALLBACK.fail, scenes };
}

export const WAIT_NARRATION: WaitNarration = parseWaitNarration(waitYaml);

/** 請求編號 → 32 位元種子（第一句與技能生成的圖樣都用它；確定性）。 */
export const waitSeed = (requestId: string): number => fmix32(seedOf(`wait#${requestId}`));

/** 這一刻要顯示的那一句（第幾格、文字）。`elapsedMs`：等了多久（真實時間，不跟著 `?anim=` 放慢）。 */
export function waitLine(
  scene: WaitSceneId,
  elapsedMs: number,
  requestId: string,
  opts: { name?: string; failed?: boolean } = {},
  table: WaitNarration = WAIT_NARRATION,
): { slot: number; text: string; long: boolean } {
  const fill = (t: string): string => t.replaceAll("{name}", opts.name ?? "對方");
  if (opts.failed === true) return { slot: -1, text: table.fail, long: false };
  const s = table.scenes[scene];
  const slot = Math.max(0, Math.floor(elapsedMs / table.rotate_ms));
  const longFrom = Math.max(1, Math.floor(table.long_ms / table.rotate_ms));
  const long = slot >= longFrom && (slot - longFrom) % 2 === 0;
  const start = waitSeed(requestId) % s.lines.length;
  const text = long ? s.long : (s.lines[(start + slot) % s.lines.length] ?? s.lines[0] ?? "");
  return { slot, text: fill(text), long };
}
