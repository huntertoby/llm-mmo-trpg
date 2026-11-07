// QK-6（#137）：玩家選的外觀（`DollLook.custom`）→ Q 版小人的外觀欄位。
// 畫法本身在 qHead（臉型、眼睛、睫毛、髮型、鬍子）、qRace（獸耳四種耳尾）、qDoll（體型 frame）；QK-1 已照 qDoll.js 移植。
// 這裡只做「資料值 → 樣張欄位」的對照：鬍子 stubble → 樣張 short（短鬍渣）、beast_ears → beastEars。純函式。
import type { QLook } from "./qCore";

/** 外觀選項（後端 `LookChoice`）用到的欄位；不認得的值一律略過。 */
export interface LookChoiceLike {
  face?: string | null;
  eye_style?: string | null;
  lashes?: boolean | null;
  hair?: string | null;
  beard?: string | null;
  frame?: string | null;
  beast_ears?: string | null;
}

export const Q_FACES = ["round", "oval", "square", "heart"] as const;
export const Q_EYE_STYLES = ["square", "dot", "smile", "big"] as const;
export const Q_HAIRS = ["short", "long", "bob", "ponytail", "twin", "spiky", "bun", "none"] as const;
export const Q_FRAMES = ["slim", "broad"] as const;
export const Q_BEAST_EARS = ["fox", "cat", "wolf", "rabbit"] as const;
/** 資料的鬍子值 → 樣張 `beardStyle`（none＝不畫）。 */
export const Q_BEARD: Readonly<Record<string, string | null>> = { none: null, stubble: "short", mustache: "mustache", goatee: "goatee", full: "full" };

const isIn = <T extends string>(list: readonly T[], v: string | null | undefined): v is T => v != null && (list as readonly string[]).includes(v);

type LookFields = Pick<QLook, "face" | "eyeStyle" | "lashes" | "hair" | "beard" | "beardStyle" | "frame" | "beastEars">;

/**
 * 把選項疊到外觀上（在種族預設之後）：臉型、眼睛、睫毛、髮型、鬍子、體型、獸耳。
 * 預設值（圓臉、方眼）不寫欄位，畫面和沒選時逐像素相同。鬍子：full ＝ 大鬍子（同舊 `beard: true`）、none ＝ 拿掉種族鬍子。
 */
export function applyLookChoice<L extends LookFields>(look: L, c: LookChoiceLike): L {
  const out: L = { ...look };
  if (isIn(Q_FACES, c.face)) {
    if (c.face === "round") delete out.face;
    else out.face = c.face;
  }
  if (isIn(Q_EYE_STYLES, c.eye_style)) {
    if (c.eye_style === "square") delete out.eyeStyle;
    else out.eyeStyle = c.eye_style;
  }
  if (c.lashes === true) out.lashes = true;
  else if (c.lashes === false) delete out.lashes;
  if (isIn(Q_HAIRS, c.hair)) out.hair = c.hair;
  if (c.beard != null && c.beard in Q_BEARD) {
    const st = Q_BEARD[c.beard] ?? null;
    delete out.beardStyle;
    if (st === null) delete out.beard;
    else if (st === "full") {
      out.beard = true;
      out.beardStyle = "full";
    } else {
      delete out.beard;
      out.beardStyle = st;
    }
  }
  if (isIn(Q_FRAMES, c.frame)) out.frame = c.frame;
  if (isIn(Q_BEAST_EARS, c.beast_ears)) out.beastEars = c.beast_ears;
  return out;
}

/** 體型（疊在種族 build 上）的縮放，同 qDoll.js：slim ×(0.92, 1.02)、broad ×(1.08, 0.98)。qDoll 已照這份畫，給測試與頭像對照用。 */
export function qFrameScale(frame: string | undefined): readonly [number, number] {
  return frame === "slim" ? [0.92, 1.02] : frame === "broad" ? [1.08, 0.98] : [1, 1];
}
