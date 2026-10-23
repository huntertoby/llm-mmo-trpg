// 區域主題（Phase 3-37a；docs/art/雲嶺移植需求.md 第 1 節）：地圖的 `region` 與 `look` 覆寫如何進繪圖。
// 規則：外觀 ＝（地形或物件 ID）×（區域）；查不到一律回到預設畫法，不出錯。
// 區域 ID 與 `look` 的鍵值是 `content/regions.yaml` 的資料（伺服器已丟掉未知值）；這裡只放「ID → 畫法」表的骨架，
// 前端不寫死五區名單：表裡沒有的區域（含未知區域、尚未實作的區域）就是預設畫法。
// 3-37a 只有預設區；雲嶺的畫法在 3-37b 加進各表。

/** 區域表：區域 ID → 地形（或物件）ID → 畫法。 */
export type RegionTable<D> = Readonly<Record<string, Readonly<Record<string, D>>>>;

/** `look` 覆寫表：`"鍵=值"` → 地形（或物件）ID → 畫法。 */
export type LookTable<D> = Readonly<Record<string, Readonly<Record<string, D>>>>;

/** 繪圖規格裡的主題欄位（進快取鍵）：`region` 空字串 ＝ 預設；`look` 是正規化字串（鍵排序，無覆寫為空字串）。 */
export interface ArtTheme {
  region: string;
  look: string;
}

export const DEFAULT_THEME: ArtTheme = { region: "", look: "" };

/** `look` 轉成正規化字串 `a=b,c=d`（鍵排序）；沒有或空 → 空字串。值不是字串的項目略過。 */
export function lookKey(look: Readonly<Record<string, unknown>> | null | undefined): string {
  if (look === null || look === undefined) return "";
  return Object.keys(look)
    .sort()
    .filter((k) => typeof look[k] === "string")
    .map((k) => `${k}=${look[k] as string}`)
    .join(",");
}

/** 由伺服器的地圖視圖（`region`、`look` 可能缺漏）得到主題欄位。 */
export function themeOf(view: { region?: string | null; look?: Readonly<Record<string, string>> | null }): ArtTheme {
  return { region: view.region ?? "", look: lookKey(view.look) };
}

/** 主題進快取鍵的片段。 */
export function themeKey(t: ArtTheme): string {
  return `${t.region}~${t.look}`;
}

/** 依 `look` 覆寫 → 區域查畫法；都沒有回傳 undefined（呼叫端退回預設）。覆寫優先於區域。 */
export function pickThemed<D>(
  theme: ArtTheme,
  id: string,
  regions: RegionTable<D>,
  looks: LookTable<D>,
): D | undefined {
  if (theme.look !== "") {
    for (const pair of theme.look.split(",")) {
      const hit = own(own(looks, pair), id);
      if (hit !== undefined) return hit;
    }
  }
  return theme.region === "" ? undefined : own(own(regions, theme.region), id);
}

/** 取 `look` 正規化字串裡某個鍵的值（沒有為 undefined）；供表面這類「微調顏色而非換整個畫法」的覆寫使用。 */
export function lookValue(look: string, key: string): string | undefined {
  for (const pair of look.split(",")) {
    const i = pair.indexOf("=");
    if (i > 0 && pair.slice(0, i) === key) return pair.slice(i + 1);
  }
  return undefined;
}

/** 水底色微調（`look.water_tint` → 水面底色）；值不認得 → undefined（用預設的水色）。 */
export const WATER_TINT: Readonly<Record<string, string>> = { green: "#4f9a62" };

/** 水底色：依 `look.water_tint` 查表；沒有或不認得 → undefined。 */
export function waterTintOf(look: string): string | undefined {
  const v = lookValue(look, "water_tint");
  return v !== undefined && Object.hasOwn(WATER_TINT, v) ? WATER_TINT[v] : undefined;
}

/** 區域的裝飾薄霧：平常與霧天的濃度（0–1）。只是裝飾層，不影響視線規則；沒列的區域沒有薄霧。 */
export const REGION_MIST: Readonly<Record<string, { normal: number; fog: number }>> = {
  cloud_ridge: { normal: 0.2, fog: 0.4 },
};

/** 這張地圖該不該畫薄霧、多濃（`weather` 為天氣 ID，空字串 ＝ 無天氣）。 */
export function mistLevel(region: string, weather: string): { level: "normal" | "fog"; alpha: number } | null {
  const m = Object.hasOwn(REGION_MIST, region) ? REGION_MIST[region] : undefined;
  if (m === undefined) return null;
  return weather === "fog" ? { level: "fog", alpha: m.fog } : { level: "normal", alpha: m.normal };
}

/** 只讀自己的屬性（"constructor" 之類的鍵不當成畫法）。 */
function own<V>(table: Readonly<Record<string, V>> | undefined, key: string): V | undefined {
  return table !== undefined && Object.hasOwn(table, key) ? table[key] : undefined;
}
