// 事件卡與情境判定的小圖示（Phase 6C-7；6C-ART3 換成墨線版；QI-6 換成 Q 版第⑧批，畫法在 render/qIcon/event.ts，經 render/storyIconArt.ts）：
// 選項圖示（戰鬥、說服、潛行、調查、硬闖、機遇、離開、交易）、六屬性、d20 骰（DC）、線索、模型關閉、說書人、NPC 頭像。
// 不帶文字；名稱與說明由外層的 `Hint` 提供。props 不變。
import type { NpcPortrait } from "../api/types";
import { portraitUrl } from "../render/portrait";
import { D20_COLOR, d20ShowsValue, ringOf, storyIconUrl, type MiscIcon, type StoryIconSpec } from "../render/storyIconArt";
import "./story.css";
import type { AttrKey, SolutionIcon } from "./narration";

/** 一個墨線小圖示：有 DOM 時是離屏畫好的圖片，沒有時（測試、伺服器輸出）留同大小的框。 */
function IconImg({ spec, size, className, data }: { spec: StoryIconSpec; size: number; className: string; data: Readonly<Record<string, string>> }) {
  const url = storyIconUrl(spec, size);
  const attrs = Object.fromEntries(Object.entries(data).map(([k, v]) => [`data-${k}`, v]));
  if (url === null) return <span className={className} style={{ display: "inline-block", width: size, height: size }} aria-hidden="true" {...attrs} />;
  return <img className={className} src={url} width={size} height={size} alt="" aria-hidden="true" draggable={false} {...attrs} />;
}

/** 選項圖示（戰鬥、說服、潛行、調查、硬闖、機遇、離開、交易）；按鈕上 24px、提示 18px。 */
export function SolutionGlyph({ icon, size = 18 }: { icon: SolutionIcon; size?: number }) {
  return <IconImg spec={{ kind: "solution", icon }} size={size} className="story-glyph" data={{ icon, ring: ringOf(icon) }} />;
}

/** 六屬性的外圈色（同 docs/art/sample/attr-icons.html）。 */
export const ATTR_COLOR: Readonly<Record<AttrKey, string>> = Object.fromEntries((["str", "dex", "con", "int", "wis", "wil"] as const).map((k) => [k, ringOf(k)])) as Record<AttrKey, string>;

export function AttrIcon({ attr, size = 20 }: { attr: AttrKey; size?: number }) {
  return <IconImg spec={{ kind: "attr", attr }} size={size} className="story-attr" data={{ attr, ring: ATTR_COLOR[attr] }} />;
}

/** d20 骰（六角外形加中央三角面）；29px 以上才寫點數，小的不寫字（DC 由呼叫端寫在旁邊）。 */
export function D20({ size = 22, value, color = D20_COLOR.normal }: { size?: number; value?: number | string; color?: string }) {
  const shown = d20ShowsValue(size) && value !== undefined ? String(value) : "";
  return <IconImg spec={{ kind: "d20", value, color }} size={size} className="story-d20" data={{ color, value: shown }} />;
}

export type { MiscIcon };

/** 其他圖示：線索、模型關閉、說書人、說明、事件線。 */
export function MiscGlyph({ icon, size = 16 }: { icon: MiscIcon; size?: number }) {
  return <IconImg spec={{ kind: "misc", icon }} size={size} className="story-glyph" data={{ icon, ring: ringOf(icon) }} />;
}

/** NPC 頭像（`render/portrait.ts` 離屏畫好的圖片；沒有 DOM 時只留同大小的框，測試用）。`level`＝好感五級（QK-2；null＝普通）。 */
export function Portrait({ portrait, region, size, label, level = null }: { portrait: NpcPortrait | null | undefined; region?: string | null; size: number; label?: string; level?: number | null }) {
  const url = portraitUrl(portrait, region ?? null, size, 2, level);
  const kind = portrait == null ? "silhouette" : (portrait.extras ?? []).includes("fox") ? "fox" : "doll";
  if (url === null) return <span className="story-portrait" style={{ width: size, height: size }} data-portrait={kind} aria-label={label} role={label !== undefined ? "img" : undefined} />;
  return <img className="story-portrait" src={url} width={size} height={size} alt={label ?? ""} data-portrait={kind} />;
}
