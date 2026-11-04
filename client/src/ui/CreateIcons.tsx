// 建角畫面的小圖示（UI-E1b；docs/art/create-v2.png）：出身的五區紋章（六角框＋區域色圖樣）與關鍵字小圖示。
// 全部程式繪製（inline SVG），純裝飾（`aria-hidden`），名稱寫在旁邊的文字。顏色：紋章接區域主題的強調色
// （content/ui/region_themes.yaml），關鍵字各一色。不碰人物繪製。
import { regionThemeFor } from "./regionTheme";

const GOLD = "#e8bb48";
const NAVY = "#161a2a";

/** 有專屬圖樣的區域（其他區用菱形）。 */
export const CREST_REGIONS = ["crystal_crown", "cloud_ridge", "arcane_hub", "ashen_waste", "frost_tide"] as const;

function crestGlyph(region: string, c: string) {
  switch (region) {
    case "crystal_crown": // 晶冠：王冠
      return <path d="M11 25L12 15L16.5 20L20 13L23.5 20L28 15L29 25Z" fill={c} stroke="#eef2ff" strokeWidth="0.8" strokeLinejoin="round" />;
    case "cloud_ridge": // 雲嶺：雙峰
      return (
        <>
          <path d="M9 27L16 15L20 21L23 17L31 27Z" fill={c} stroke="#e8f4dc" strokeWidth="0.8" strokeLinejoin="round" />
          <path d="M14 18.5L16 15L18 18.5Z" fill="#f4f8ee" />
        </>
      );
    case "arcane_hub": // 樞市：齒輪
      return (
        <>
          <g fill={c}>
            {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
              <rect key={a} x="18.6" y="10" width="2.8" height="4" transform={`rotate(${a} 20 20)`} />
            ))}
          </g>
          <circle cx="20" cy="20" r="6.5" fill={c} />
          <circle cx="20" cy="20" r="2.6" fill={NAVY} />
        </>
      );
    case "ashen_waste": // 荒原：火焰
      return (
        <>
          <path d="M20 10C24 15 27 18 26 23A6 6 0 0 1 14 23C13.5 19.5 16 18 17 15C18 18 19.5 18.5 20 10Z" fill={c} />
          <path d="M20 19C22 21.5 22.5 23 21.8 24.5A2.2 2.2 0 0 1 18.2 24.5C17.8 23 18.8 21.5 20 19Z" fill="#ffe08a" />
        </>
      );
    case "frost_tide": // 霜潮：浪紋
      return (
        <g fill="none" stroke={c} strokeWidth="2" strokeLinecap="round">
          <path d="M11 16Q13.5 13.5 16 16T21 16T26 16T29 16" />
          <path d="M11 21Q13.5 18.5 16 21T21 21T26 21T29 21" />
          <path d="M13 26Q15.5 23.5 18 26T23 26T27 26" />
        </g>
      );
    default:
      return <path d="M20 12L27 20L20 28L13 20Z" fill={c} />;
  }
}

/** 出身的區域紋章：六角金框、深藍底、區域色圖樣。 */
export function RegionCrest({ region, size = 34 }: { region: string; size?: number }) {
  const c = regionThemeFor(region).accent;
  return (
    <svg className="region-crest" viewBox="0 0 40 40" width={size} height={size} aria-hidden="true" data-crest={region}>
      <path d="M20 2L35.6 11V29L20 38L4.4 29V11Z" fill={NAVY} stroke={GOLD} strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M20 5.5L32.6 12.8V27.2L20 34.5L7.4 27.2V12.8Z" fill="none" stroke={c} strokeOpacity="0.55" strokeWidth="0.8" />
      {crestGlyph(region, c)}
    </svg>
  );
}

/** 有專屬圖示的關鍵字（`content/skill_keywords.yaml` 的 ID；新增關鍵字沒圖示時用圓點）。 */
export const KEYWORD_ICON_IDS = ["ignite", "wet", "charged", "frozen", "prone", "collision", "marked", "high_ground", "concealed", "summon", "poisoned", "form"] as const;

/** 關鍵字的圖示顏色。 */
export const KEYWORD_ICON_COLOR: Readonly<Record<string, string>> = {
  ignite: "#ff8a3a",
  wet: "#5ab0f0",
  charged: "#ffe14a",
  frozen: "#a8e0ff",
  prone: "#d8b878",
  collision: "#ff6a5a",
  marked: "#ff6a9a",
  high_ground: "#8ad070",
  concealed: "#b8a8ff",
  summon: "#c08aff",
  poisoned: "#7ad050",
  form: "#e8bb48",
};

function keywordGlyph(id: string, c: string) {
  switch (id) {
    case "ignite":
      return <path d="M8 1.5C11 5 12.5 7 12 10A4 4 0 0 1 4 10C3.8 7.6 5.5 6.5 6 4.5C7 6.5 7.6 6.6 8 1.5Z" fill={c} />;
    case "wet":
      return <path d="M8 1.5C10.5 5.5 12.5 7.8 12.5 10A4.5 4.5 0 0 1 3.5 10C3.5 7.8 5.5 5.5 8 1.5Z" fill={c} />;
    case "charged":
      return <path d="M9.5 1L3.5 9H7.5L6 15L12.5 6.5H8.5Z" fill={c} />;
    case "frozen":
      return (
        <g stroke={c} strokeWidth="1.5" strokeLinecap="round">
          <path d="M8 1.5V14.5M2.4 4.75L13.6 11.25M2.4 11.25L13.6 4.75" />
        </g>
      );
    case "prone":
      return (
        <>
          <circle cx="3.5" cy="10" r="2" fill={c} />
          <path d="M6 10.5H14" stroke={c} strokeWidth="2.2" strokeLinecap="round" />
          <path d="M1.5 14H14.5" stroke={c} strokeWidth="1" strokeOpacity="0.7" />
        </>
      );
    case "collision":
      return <path d="M8 1L9.6 5.6L14.5 4.5L11.2 8L14.5 11.5L9.6 10.4L8 15L6.4 10.4L1.5 11.5L4.8 8L1.5 4.5L6.4 5.6Z" fill={c} />;
    case "marked":
      return (
        <g fill="none" stroke={c} strokeWidth="1.5">
          <circle cx="8" cy="8" r="5.5" />
          <circle cx="8" cy="8" r="1.6" fill={c} />
          <path d="M8 0.5V3.5M8 12.5V15.5M0.5 8H3.5M12.5 8H15.5" />
        </g>
      );
    case "high_ground":
      return (
        <>
          <path d="M1 14.5L6.5 6L9.5 10L11 8L15 14.5Z" fill={c} />
          <path d="M12 6.5V1.5M10 3.5L12 1.5L14 3.5" fill="none" stroke={c} strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
        </>
      );
    case "concealed":
      return (
        <g fill="none" stroke={c} strokeWidth="1.5" strokeLinecap="round">
          <path d="M1.5 8Q8 1.5 14.5 8Q8 14.5 1.5 8Z" />
          <circle cx="8" cy="8" r="1.8" fill={c} />
          <path d="M2.5 14L13.5 2" />
        </g>
      );
    case "summon":
      return (
        <>
          <ellipse cx="8" cy="12" rx="6" ry="2.4" fill="none" stroke={c} strokeWidth="1.4" />
          <path d="M8 1.5L9.2 5.3L13 6.5L9.2 7.7L8 11.5L6.8 7.7L3 6.5L6.8 5.3Z" fill={c} />
        </>
      );
    case "poisoned":
      return (
        <>
          <circle cx="6" cy="10" r="4" fill={c} />
          <circle cx="11.5" cy="5" r="2.6" fill={c} fillOpacity="0.8" />
          <circle cx="12.5" cy="12" r="1.6" fill={c} fillOpacity="0.65" />
        </>
      );
    case "form":
      return (
        <g fill="none" stroke={c} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 6.5A5.5 5.5 0 0 1 13 5" />
          <path d="M13 1.8V5H9.8" />
          <path d="M13 9.5A5.5 5.5 0 0 1 3 11" />
          <path d="M3 14.2V11H6.2" />
        </g>
      );
    default:
      return <circle cx="8" cy="8" r="3.5" fill={c} />;
  }
}

/** 關鍵字小圖示（16×16 座標；放在關鍵字按鈕的名字前面）。 */
export function KeywordIcon({ id, size = 15 }: { id: string; size?: number }) {
  const c = KEYWORD_ICON_COLOR[id] ?? GOLD;
  return (
    <svg className="keyword-icon" viewBox="0 0 16 16" width={size} height={size} aria-hidden="true" data-keyword-icon={id}>
      {keywordGlyph(id, c)}
    </svg>
  );
}
