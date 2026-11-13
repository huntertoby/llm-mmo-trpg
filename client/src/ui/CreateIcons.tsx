// 建角畫面的小圖示（UI-E1b；docs/art/shots/misc/create-v2.png）：出身的五區紋章（六角框＋區域色圖樣）與關鍵字小圖示。
// 全部程式繪製（inline SVG），純裝飾（`aria-hidden`），名稱寫在旁邊的文字。顏色：紋章接區域主題的強調色
// （content/ui/region_themes.yaml），關鍵字各一色。不碰人物繪製。
// QI-5：紋章換 Q 版 canvas（`render/qIcon/hud.ts`，框照原樣畫在畫布裡），舊的 SVG 圖樣 `crestGlyph` 已刪；關鍵字小圖示 `KeywordIcon` 不在這批，照舊是 SVG。
import { crestId } from "../render/qIcon/hud";
import { HudGlyph } from "./HudGlyph";
import { regionThemeFor } from "./regionTheme";

const GOLD = "#e8bb48";

/** 有專屬圖樣的區域（其他區用菱形）。 */
export const CREST_REGIONS = ["crystal_crown", "cloud_ridge", "arcane_hub", "ashen_waste", "frost_tide"] as const;

/** 出身的區域紋章（QI-5 換 Q 版 canvas，畫法 `render/qIcon/hud.ts`）：六角金框、深藍底、區域色細環照現行，圖樣 60% 置中、用區域色三階；
 *  沒有專屬圖樣的區域用菱形寶石。`size`＝顯示邊長（出身卡 30、預設 34）。 */
export function RegionCrest({ region, size = 34 }: { region: string; size?: number }) {
  const accent = regionThemeFor(region).accent;
  return <HudGlyph id={crestId(region)} px={size} className="region-crest" opt={{ accent }} data={{ "data-crest": region }} />;
}

/** 有專屬圖示的關鍵字（`content/skill_keywords.yaml` 的 ID；新增關鍵字沒圖示時用圓點）。 */
export const KEYWORD_ICON_IDS = ["ignite", "wet", "charged", "frozen", "prone", "collision", "marked", "high_ground", "concealed", "summon", "poisoned", "form", "combo_point", "fury", "focus", "ki"] as const;

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
  /* KW-3（docs/art/KW樣張.md 第 3 節 CREATE_COLOR）：和圓章色（KEYWORD_COLOR）同色，只有怒氣亮一階（#df2046 在按鈕深褐底上太暗）。 */
  combo_point: "#ff3d8b",
  fury: "#ff4a62",
  focus: "#476deb",
  ki: "#29e0bc",
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
    // KW-3：四個層數關鍵字（A 案；照 docs/art/sample/qIconsKW.js 的 CREATE[kw].a 逐字抄，連擊的三條 path 由 comboCreate 算出）
    case "combo_point":
      return (
        <>
          <path d="M7.09 15.69L11.31 13.40L12.75 10.04L9.39 11.48Z" fill={c} fillOpacity="0.7" />
          <path d="M3.93 13.20L9.69 9.60L12.07 5.06L7.54 7.45Z" fill={c} fillOpacity="0.85" />
          <path d="M0.65 10.15L7.75 5.54L10.83 -0.03L5.26 3.05Z" fill={c} />
        </>
      );
    case "fury":
      return <path fillRule="evenodd" d="M0.6 3.6L8 8L15.4 3.6L15.2 10.6Q8 14.6 0.8 10.6ZM2.6 8L6.6 9.8L6 11.6L2.8 10.2ZM13.4 8L9.4 9.8L10 11.6L13.2 10.2Z" fill={c} />;
    case "focus":
      return (
        <>
          <g fill="none" stroke={c} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M1.6 5V1.6H5M11 1.6H14.4V5M14.4 11V14.4H11M5 14.4H1.6V11" />
          </g>
          <path d="M8 4.4L10.6 8L8 11.6L5.4 8Z" fill={c} />
        </>
      );
    case "ki":
      return (
        <>
          <circle cx="8" cy="8" r="6.6" fill="none" stroke={c} strokeWidth="1.3" />
          <path d="M8 1.4A6.6 6.6 0 0 1 8 14.6A3.3 3.3 0 0 1 8 8A3.3 3.3 0 0 0 8 1.4Z" fill={c} />
          <circle cx="8" cy="4.7" r="1.1" fill={c} />
          <circle cx="8" cy="11.3" r="1.1" fill="#1a1410" />
        </>
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
