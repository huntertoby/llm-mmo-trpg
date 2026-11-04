// HUD 的程式繪製圖示（Phase 6B-5；形狀參考 docs/art/sample/hud.js 的 `I`）：24×24 的 SVG，顏色寫死在圖裡
// （深底金邊的 HUD 上用），不另外載圖檔。
import type { ReactElement } from "react";

export type HudIconName =
  | "bag"
  | "book"
  | "growth"
  | "scroll"
  | "shadow"
  | "notes"
  | "boots"
  | "map"
  | "gear"
  | "coin"
  | "token"
  | "ration"
  | "bulb"
  | "warn"
  | "sun"
  | "moon"
  | "clear"
  | "rain"
  | "fog"
  | "snow"
  | "wind"
  | "night"
  | "rank"
  | "pin"
  | "town";

const PATHS: Record<HudIconName, ReactElement> = {
  bag: (
    <>
      <path d="M8 8V6a4 4 0 0 1 8 0v2" fill="none" stroke="#e8d3a0" strokeWidth="1.8" />
      <rect x="4" y="8" width="16" height="13" rx="3" fill="#a8743c" stroke="#3a2410" strokeWidth="1.2" />
      <rect x="9" y="12" width="6" height="4" rx="1" fill="#e8bb48" />
    </>
  ),
  book: (
    <>
      <rect x="5" y="3" width="14" height="18" rx="2" fill="#6a48b8" stroke="#2a1a50" strokeWidth="1.2" />
      <rect x="8" y="3" width="2" height="18" fill="#3a2870" />
      <path d="M13 8l1.2 2.4 2.6.4-1.9 1.8.5 2.6-2.4-1.3-2.3 1.3.4-2.6-1.9-1.8 2.6-.4z" fill="#e8bb48" />
    </>
  ),
  growth: (
    <>
      <path d="M12 3l7 8h-4v9H9v-9H5z" fill="#4ac05a" stroke="#1a4a20" strokeWidth="1.2" />
    </>
  ),
  scroll: (
    <>
      <rect x="4" y="5" width="16" height="14" rx="2" fill="#e8d3a0" stroke="#5a3a1a" strokeWidth="1.2" />
      <path d="M7 9h10M7 12h10M7 15h6" stroke="#a8442c" strokeWidth="1.6" />
    </>
  ),
  shadow: (
    <>
      <circle cx="12" cy="8" r="4" fill="#5a4a90" />
      <path d="M4 21c0-5 3.5-8 8-8s8 3 8 8z" fill="#5a4a90" />
      <circle cx="12" cy="8" r="4" fill="none" stroke="#b8a0ff" strokeWidth="1.2" strokeDasharray="2 1.5" />
    </>
  ),
  notes: (
    <>
      <path d="M4 5h16v11H11l-5 4v-4H4z" fill="#f0ead8" stroke="#5a4a30" strokeWidth="1.2" />
      <circle cx="8.5" cy="10.5" r="1.2" fill="#5a4a30" />
      <circle cx="12" cy="10.5" r="1.2" fill="#5a4a30" />
      <circle cx="15.5" cy="10.5" r="1.2" fill="#5a4a30" />
    </>
  ),
  boots: (
    <>
      <path d="M8 3h6v11l5 2v4H6V14z" fill="#8a5a2a" stroke="#3a2410" strokeWidth="1.2" />
      <path d="M8 7h6" stroke="#e8bb48" strokeWidth="1.4" />
    </>
  ),
  map: (
    <>
      <path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2z" fill="#e8d3a0" stroke="#5a3a1a" strokeWidth="1.2" />
      <path d="M9 4v14M15 6v14" stroke="#a8875a" strokeWidth="1" />
      <path d="M11 10l3 3m0-3l-3 3" stroke="#c03a2a" strokeWidth="1.6" />
    </>
  ),
  gear: (
    <>
      <circle cx="12" cy="12" r="6.5" fill="none" stroke="#c8c0b0" strokeWidth="3" strokeDasharray="2.6 2.5" />
      <circle cx="12" cy="12" r="4.5" fill="#8a8478" />
      <circle cx="12" cy="12" r="1.8" fill="#2a2620" />
    </>
  ),
  coin: (
    <>
      <circle cx="12" cy="12" r="8" fill="#e8bb48" stroke="#7a5a10" strokeWidth="1.4" />
      <rect x="10" y="8" width="4" height="8" rx="1" fill="none" stroke="#7a5a10" strokeWidth="1.4" />
    </>
  ),
  token: (
    <>
      <circle cx="12" cy="12" r="8" fill="#a04a3a" stroke="#4a1a10" strokeWidth="1.4" />
      <path d="M12 6.5l1.6 3.4 3.7.4-2.8 2.5.8 3.6L12 14.6l-3.3 1.8.8-3.6-2.8-2.5 3.7-.4z" fill="#f0c8a0" />
    </>
  ),
  ration: (
    <>
      <ellipse cx="12" cy="13" rx="8" ry="5.5" fill="#c08a4a" stroke="#5a3a1a" strokeWidth="1.2" />
      <path d="M8 11.5c1 1 2 1 3 0m2 0c1 1 2 1 3 0" stroke="#5a3a1a" strokeWidth="1.2" fill="none" />
    </>
  ),
  bulb: (
    <>
      <path d="M12 3a6 6 0 0 0-3.5 10.9V16h7v-2.1A6 6 0 0 0 12 3z" fill="#ffe070" stroke="#7a5a10" strokeWidth="1.2" />
      <rect x="9" y="17" width="6" height="3" rx="1" fill="#8a8478" />
    </>
  ),
  warn: (
    <>
      <path d="M12 3l10 18H2z" fill="#e8bb48" stroke="#5a3a00" strokeWidth="1.2" strokeLinejoin="round" />
      <rect x="11" y="9" width="2" height="6" fill="#3a2400" />
      <rect x="11" y="16.5" width="2" height="2" fill="#3a2400" />
    </>
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="5" fill="#ffd040" />
      <path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2" stroke="#ffd040" strokeWidth="1.8" />
    </>
  ),
  moon: <path d="M15 3a9 9 0 1 0 6 13A7 7 0 0 1 15 3z" fill="#d8dcf0" stroke="#5a6090" strokeWidth="1" />,
  clear: (
    <>
      <circle cx="12" cy="12" r="4" fill="#ffd040" />
      <circle cx="12" cy="12" r="7" fill="none" stroke="#ffd040" strokeWidth="1.2" strokeDasharray="1.5 2" />
    </>
  ),
  rain: (
    <>
      <path d="M6 13a4 4 0 0 1 .5-8 5 5 0 0 1 9.5 1A3.5 3.5 0 0 1 17 13z" fill="#b8c4d0" />
      <path d="M8 16l-1 3M12 16l-1 3M16 16l-1 3" stroke="#5a9ae0" strokeWidth="1.8" />
    </>
  ),
  fog: <path d="M3 8h14M6 12h15M3 16h13M7 20h10" stroke="#c8ccd0" strokeWidth="2" strokeLinecap="round" />,
  snow: <path d="M12 3v18M4 7.5l16 9M4 16.5l16-9" stroke="#e0f0ff" strokeWidth="1.8" />,
  wind: <path d="M3 9h12a3 3 0 1 0-3-3M3 14h16a3 3 0 1 1-3 3" stroke="#c8ccd0" strokeWidth="1.8" fill="none" />,
  night: <path d="M15 3a9 9 0 1 0 6 13A7 7 0 0 1 15 3z" fill="#8a90c0" />,
  rank: (
    <>
      <path d="M5 4h14v8c0 4-3.5 7-7 8-3.5-1-7-4-7-8z" fill="#4a6ad0" stroke="#e8bb48" strokeWidth="1.4" />
      <path d="M9 10l3-3 3 3M9 14l3-3 3 3" stroke="#e8bb48" strokeWidth="1.4" fill="none" />
    </>
  ),
  pin: <path d="M14 2l8 8-3 1-4 4 .5 4-1.5 1.5-4-4-5 5-1-1 5-5-4-4L7 9.5l4 .5 4-4z" fill="#c8a868" />,
  town: (
    <>
      <path d="M3 11l9-7 9 7" fill="none" stroke="#e8d3a0" strokeWidth="1.8" />
      <rect x="6" y="11" width="12" height="9" fill="#7fa8d0" stroke="#2a3a50" strokeWidth="1.2" />
      <rect x="10.5" y="14" width="3" height="6" fill="#2a3a50" />
    </>
  ),
};

export function HudIcon({ name, size = 22 }: { name: HudIconName; size?: number }) {
  return (
    <svg className="hud-icon" viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" data-icon={name}>
      {PATHS[name]}
    </svg>
  );
}

/** 圓頭像（程式繪製的小人臉；主角金框、隊友藍框）。 */
export function HudPortrait({ size, ring, tone = 0 }: { size: number; ring: string; tone?: number }) {
  const skin = ["#f0c8a0", "#d8a878", "#c89060"][tone % 3];
  const hair = ["#2a2018", "#5a3a20", "#1a1a2a"][tone % 3];
  return (
    <svg className="hud-portrait" viewBox="0 0 64 64" width={size} height={size} aria-hidden="true">
      {/* UI-E1 追加 5：框色寫在 style（換區時 CSS `.hud-portrait-ring` 淡入 0.3 秒），畫法不變 */}
      <circle className="hud-portrait-ring" cx="32" cy="32" r="30" fill="#3a5a6a" stroke={ring} strokeWidth="3" style={{ stroke: ring }} />
      <path d="M14 58c2-12 9-16 18-16s16 4 18 16z" fill="#4a6a8a" />
      <circle cx="32" cy="30" r="12" fill={skin} />
      <path d="M19 28c0-10 6-15 13-15s13 5 13 15c-3-5-8-7-13-7s-10 2-13 7z" fill={hair} />
      <circle cx="27.5" cy="31" r="1.6" fill="#2a2018" />
      <circle cx="36.5" cy="31" r="1.6" fill="#2a2018" />
    </svg>
  );
}
