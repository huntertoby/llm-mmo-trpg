// 開發用：QI-7 以前的物品圖示（只給 `item-gallery` 的「現行｜Q」並排；不屬於正式 build）。美術驗收後可刪。
// - `LegacyGainIcon`：`world/GainEffects.tsx` 的 GainIcon 兩個 SVG 原樣（裝備一把劍、其他一個布袋；QI-7 起正式畫面換成 Q 版 `gain_gear`／`gain_item`）。
// - `LegacyTile`：背包格的名字小牌（`.world-bag-tile`；正式畫面只剩圖示表裡沒有的物品在用）。
import { tileLines } from "../world/bagGrid";

export function LegacyGainIcon({ gear }: { gear: boolean }) {
  return gear ? (
    <svg viewBox="0 0 28 28" width="28" height="28">
      <circle cx="14" cy="14" r="13" fill="#2a2018" stroke="#e8bb48" strokeWidth="1.6" />
      <path d="M8 20 L19 9" stroke="#1c1712" strokeWidth="4.4" strokeLinecap="round" />
      <path d="M8 20 L19 9" stroke="#e6ecf2" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M7 15 L13 21" stroke="#e8bb48" strokeWidth="2.6" strokeLinecap="round" />
    </svg>
  ) : (
    <svg viewBox="0 0 28 28" width="28" height="28">
      <circle cx="14" cy="14" r="13" fill="#2a2018" stroke="#e8bb48" strokeWidth="1.6" />
      <path d="M9 12 Q14 8 19 12 L20 19 Q14 23 8 19 Z" fill="#c89858" stroke="#1c1712" strokeWidth="1.4" />
      <path d="M10.5 11.5 Q14 13.5 17.5 11.5" stroke="#7a4e2a" strokeWidth="1.4" fill="none" />
    </svg>
  );
}

/** 一格背包（50px）裡的名字小牌，照現行 `BagCellView` 的結構與 CSS。 */
export function LegacyTile({ name, count }: { name: string; count: number }) {
  return (
    <ul className="world-bag-grid" style={{ display: "inline-grid", padding: 0, margin: 0, listStyle: "none" }}>
      <li className="world-bag-cell">
        <button type="button">
          <span className="world-bag-tile" aria-hidden="true">
            {tileLines(name).map((l, i) => (
              <span key={i} className="world-bag-tile-line">
                {l}
              </span>
            ))}
          </span>
          {count > 1 && <b className="world-bag-count">{count}</b>}
        </button>
      </li>
    </ul>
  );
}
