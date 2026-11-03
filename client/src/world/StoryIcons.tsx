// 事件卡與情境判定的小圖示（Phase 6C-7；docs/art/HUD版面.md 5.7、docs/art/去文字化移植需求.md 第 6 節）：
// 選項圖示（戰鬥、說服、潛行、調查、硬闖、機遇、放棄）、六屬性、d20 骰（DC）、線索、模型關閉、說書人、NPC 頭像。
// 純 SVG、不帶文字；名稱與說明由外層的 `Hint` 提供。
import type { ReactNode } from "react";
import type { NpcPortrait } from "../api/types";
import { portraitUrl } from "../render/portrait";
import "./story.css";
import type { AttrKey, SolutionIcon } from "./narration";

const INK = "#1c1712";

const SOLUTION_PATHS: Readonly<Record<SolutionIcon, ReactNode>> = {
  combat: (
    <>
      <path d="M4 4l11 11M16 4L5 15" stroke={INK} strokeWidth="4" strokeLinecap="round" />
      <path d="M4 4l11 11M16 4L5 15" stroke="#e8eef4" strokeWidth="2" strokeLinecap="round" />
      <path d="M3 13l4 4M17 13l-4 4" stroke="#c8903a" strokeWidth="2.4" strokeLinecap="round" />
    </>
  ),
  persuade: (
    <>
      <path d="M3 4h14v9H9l-4 3v-3H3z" fill="#f2e6c8" stroke={INK} strokeWidth="1.4" strokeLinejoin="round" />
      <path d="M6 7.5h8M6 10h5" stroke={INK} strokeWidth="1.2" />
    </>
  ),
  sneak: (
    <>
      <path d="M2 9c3-4 13-4 16 0-3 4-13 4-16 0z" fill="#3a3a48" stroke={INK} strokeWidth="1.3" />
      <circle cx="7" cy="9" r="1.6" fill="#c8d8f0" />
      <circle cx="13" cy="9" r="1.6" fill="#c8d8f0" />
      <path d="M5 15h3M12 15h3" stroke="#8a8aa8" strokeWidth="1.6" strokeLinecap="round" />
    </>
  ),
  investigate: (
    <>
      <circle cx="8.5" cy="8.5" r="5" fill="#bfe4f0" stroke={INK} strokeWidth="1.6" />
      <path d="M12.5 12.5l5 5" stroke={INK} strokeWidth="3" strokeLinecap="round" />
      <path d="M12.5 12.5l5 5" stroke="#c8903a" strokeWidth="1.6" strokeLinecap="round" />
    </>
  ),
  force: <path d="M5 9V6.5a1.5 1.5 0 0 1 3 0V5a1.5 1.5 0 0 1 3 0v.5a1.5 1.5 0 0 1 3 0V7a1.5 1.5 0 0 1 3 0v4c0 4-3 6-6 6H9c-2.5 0-4-2-4-4z" fill="#e8b890" stroke={INK} strokeWidth="1.3" />,
  chance: <polygon points="10,2 12.5,7.5 18,8 14,12 15,18 10,15 5,18 6,12 2,8 7.5,7.5" fill="#ffd23a" stroke={INK} strokeWidth="1.3" />,
  leave: (
    <>
      <rect x="3" y="3" width="8" height="14" rx="1" fill="#6a5040" stroke={INK} strokeWidth="1.3" />
      <path d="M9 10h8M14 7l3 3-3 3" stroke="#e8dcc0" strokeWidth="2" fill="none" strokeLinecap="round" />
    </>
  ),
  trade: (
    <>
      <circle cx="7" cy="11" r="4.5" fill="#e8bb48" stroke={INK} strokeWidth="1.3" />
      <circle cx="13" cy="8" r="4.5" fill="#f2d070" stroke={INK} strokeWidth="1.3" />
    </>
  ),
};

export function SolutionGlyph({ icon, size = 18 }: { icon: SolutionIcon; size?: number }) {
  return (
    <svg className="story-glyph" viewBox="0 0 20 20" width={size} height={size} aria-hidden="true" data-icon={icon}>
      {SOLUTION_PATHS[icon]}
    </svg>
  );
}

/** 六屬性的外圈色（同 docs/art/sample/attr-icons.html）。 */
export const ATTR_COLOR: Readonly<Record<AttrKey, string>> = { str: "#e07a4a", dex: "#6ac0a0", con: "#d04a5a", int: "#7a8aff", wis: "#4ab0d0", wil: "#e8bb48" };

const ATTR_PATHS: Readonly<Record<AttrKey, ReactNode>> = {
  str: <path d="M4 15l2-6 4-4h4l1 3-3 1-1 3h4l2 3z" fill="#e8b890" stroke={INK} strokeWidth="1.1" />,
  dex: (
    <>
      <path d="M15 3c-5 1-9 5-10 11l2 1c1-5 4-8 8-10z" fill="#c8f0e0" stroke={INK} strokeWidth="1.1" />
      <path d="M5 15l-1 2" stroke={INK} strokeWidth="1.2" />
    </>
  ),
  con: <path d="M10 16S4 12 4 8a3 3 0 0 1 6-1 3 3 0 0 1 6 1c0 4-6 8-6 8z" fill="#e04a5a" stroke={INK} strokeWidth="1.1" />,
  int: (
    <>
      <path d="M4 6l6 1.5L16 6v9l-6 1.5L4 15z" fill="#f2e6c8" stroke={INK} strokeWidth="1.1" />
      <path d="M10 7.5v9" stroke={INK} strokeWidth="1" />
    </>
  ),
  wis: (
    <>
      <path d="M3 10c3-4.5 11-4.5 14 0-3 4.5-11 4.5-14 0z" fill="#f2f0e8" stroke={INK} strokeWidth="1.1" />
      <circle cx="10" cy="10" r="2.6" fill="#4ab0d0" stroke={INK} strokeWidth="0.8" />
    </>
  ),
  wil: <path d="M10 3c3 4 4 6 4 9a4 4 0 0 1-8 0c0-2 1-3 2-4 0 2 1 2 1 2 0-3 0-5 1-7z" fill="#ffb030" stroke={INK} strokeWidth="1.1" />,
};

export function AttrIcon({ attr, size = 20 }: { attr: AttrKey; size?: number }) {
  return (
    <svg className="story-attr" viewBox="0 0 20 20" width={size} height={size} aria-hidden="true" data-attr={attr}>
      <circle cx="10" cy="10" r="9.2" fill="#2a241e" stroke={ATTR_COLOR[attr]} strokeWidth="1.4" />
      {ATTR_PATHS[attr]}
    </svg>
  );
}

/** d20 骰（六角形），中間可放數字。 */
export function D20({ size = 22, value, color = "#f2e6c8" }: { size?: number; value?: number | string; color?: string }) {
  return (
    <svg className="story-d20" viewBox="0 0 24 24" width={size} height={size} aria-hidden="true">
      <polygon points="12,1.5 21.5,7 21.5,17 12,22.5 2.5,17 2.5,7" fill={color} stroke={INK} strokeWidth="1.5" />
      <path d="M12 1.5L6.5 15h11zM2.5 7l4 8M21.5 7l-4 8M12 22.5L6.5 15M12 22.5l5.5-7.5" fill="none" stroke="rgba(28,23,18,0.35)" strokeWidth="0.8" />
      {value !== undefined && (
        <text x="12" y="14.6" textAnchor="middle" fontSize={String(value).length > 1 ? 8 : 9} fontWeight="700" fill={INK}>
          {value}
        </text>
      )}
    </svg>
  );
}

const MISC_PATHS = {
  clue: (
    <>
      <path d="M5 3h8l3 3v11H5z" fill="#f2e6c8" stroke={INK} strokeWidth="1.3" strokeLinejoin="round" />
      <circle cx="9.5" cy="10" r="2.6" fill="none" stroke="#c8903a" strokeWidth="1.5" />
      <path d="M11.4 12l2.6 2.6" stroke="#c8903a" strokeWidth="1.6" strokeLinecap="round" />
    </>
  ),
  model_off: (
    <>
      <path d="M7 3v4M13 3v4" stroke={INK} strokeWidth="2" strokeLinecap="round" />
      <path d="M5 7h10v3a5 5 0 0 1-10 0z" fill="#8a8aa8" stroke={INK} strokeWidth="1.3" />
      <path d="M10 15v3" stroke={INK} strokeWidth="2" />
      <path d="M3 3l14 14" stroke="#e04a3a" strokeWidth="2" strokeLinecap="round" />
    </>
  ),
  narrator: (
    <>
      <path d="M15 2c-6 2-9 7-10 14l1.5.5C8 11 11 7 16 4z" fill="#f2e6c8" stroke={INK} strokeWidth="1.2" />
      <path d="M3 18h14" stroke="#c8903a" strokeWidth="1.6" strokeLinecap="round" />
    </>
  ),
  info: (
    <>
      <circle cx="10" cy="10" r="8" fill="#3a3028" stroke="#c8bca8" strokeWidth="1.4" />
      <path d="M10 9v5M10 6v1" stroke="#f2e6c8" strokeWidth="2" strokeLinecap="round" />
    </>
  ),
  thread: <path d="M3 14c3-8 6 4 9-4s4-4 5-6" fill="none" stroke="#e8bb48" strokeWidth="2" strokeLinecap="round" />,
} as const;

export type MiscIcon = keyof typeof MISC_PATHS;

export function MiscGlyph({ icon, size = 16 }: { icon: MiscIcon; size?: number }) {
  return (
    <svg className="story-glyph" viewBox="0 0 20 20" width={size} height={size} aria-hidden="true" data-icon={icon}>
      {MISC_PATHS[icon]}
    </svg>
  );
}

/** NPC 頭像（`render/portrait.ts` 離屏畫好的圖片；沒有 DOM 時只留同大小的框，測試用）。 */
export function Portrait({ portrait, region, size, label }: { portrait: NpcPortrait | null | undefined; region?: string | null; size: number; label?: string }) {
  const url = portraitUrl(portrait, region ?? null, size);
  const kind = portrait == null ? "silhouette" : (portrait.extras ?? []).includes("fox") ? "fox" : "doll";
  if (url === null) return <span className="story-portrait" style={{ width: size, height: size }} data-portrait={kind} aria-label={label} role={label !== undefined ? "img" : undefined} />;
  return <img className="story-portrait" src={url} width={size} height={size} alt={label ?? ""} data-portrait={kind} />;
}
