// 區域主題點綴（RT-1；docs/art/區域主題移植需求.md 第 1 節）：`content/ui/region_themes.yaml` 在 build 時以 `?raw` 匯入、
// 用 `yaml` 解析（內容即資料；Python 端 `trpg.content.ui_themes` 的 pydantic schema 由 `trpg content check` 驗證同一份檔）。
// 前端這裡再做一次結構檢查，壞掉的那筆略過（退回 hub）。
// 只換點綴：強調色、四角飾件、標題牌材質、頭像框色（CSS 變數 `--rt-*`，掛在 `<html>`）；版面、字型、按鈕不變。
// 「目前區域」從畫面上已有的資料讀（實地地圖的 region、戰鬥的 region），不新增伺服器欄位；拿不到時用 hub。
import { useEffect, useRef, useSyncExternalStore } from "react";
import { parse } from "yaml";
import themesYaml from "../../../content/ui/region_themes.yaml?raw";
import { cornerLayers, CORNER_KINDS, type CornerKind } from "./regionCorners";

export { CORNER_KINDS, type CornerKind };

export const FALLBACK_THEME = "hub";
export const WAIT_FX = ["none", "ember", "crystal"] as const;
export type WaitFx = (typeof WAIT_FX)[number];

export interface PlaqueDef {
  top: string;
  bottom: string;
}

/** 一區的點綴（欄位同 `content/ui/region_themes.yaml`）。 */
export interface RegionThemeDef {
  accent: string;
  corner: CornerKind;
  plaque: string;
  portrait_ring: string;
  /** 等待動畫（RT-3）的墨色。 */
  ink: string;
  /** 等待動畫（RT-3）的封蠟色。 */
  seal: string;
  /** 等待動畫（RT-3）的點綴。 */
  wait_fx?: WaitFx;
}

/** 挑好的主題（帶區域 ID 與標題牌兩色）。 */
export interface RegionTheme extends RegionThemeDef {
  id: string;
  wait_fx: WaitFx;
  plaqueColors: PlaqueDef;
}

export interface RegionThemeTable {
  plaques: Record<string, PlaqueDef>;
  themes: Record<string, RegionThemeDef>;
  /** 略過的項目與原因。 */
  errors: string[];
}

const ID_RE = /^[a-z][a-z0-9_]*$/;
const HEX_RE = /^#[0-9a-fA-F]{6}$/;
const THEME_KEYS = ["accent", "corner", "plaque", "portrait_ring", "ink", "seal", "wait_fx"] as const;
const HEX_KEYS = ["accent", "portrait_ring", "ink", "seal"] as const;

const isObj = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);

/** 一筆標題牌材質的問題（空＝合法）。 */
export function plaqueProblems(raw: unknown): string[] {
  if (!isObj(raw)) return ["不是物件"];
  const p: string[] = [];
  for (const k of ["top", "bottom"] as const) if (typeof raw[k] !== "string" || !HEX_RE.test(raw[k])) p.push(`${k} 必須是 #rrggbb`);
  for (const k of Object.keys(raw)) if (k !== "top" && k !== "bottom") p.push(`未知欄位 ${k}`);
  return p;
}

/** 一筆主題的問題（空＝合法）。`plaques`：已知的標題牌材質。 */
export function themeProblems(raw: unknown, plaques: readonly string[]): string[] {
  if (!isObj(raw)) return ["不是物件"];
  const p: string[] = [];
  for (const k of HEX_KEYS) if (typeof raw[k] !== "string" || !HEX_RE.test(raw[k])) p.push(`${k} 必須是 #rrggbb`);
  if (!CORNER_KINDS.includes(raw.corner as CornerKind)) p.push(`未知的 corner：${String(raw.corner)}`);
  if (typeof raw.plaque !== "string" || !plaques.includes(raw.plaque)) p.push(`未知的 plaque：${String(raw.plaque)}`);
  if ("wait_fx" in raw && !WAIT_FX.includes(raw.wait_fx as WaitFx)) p.push(`未知的 wait_fx：${String(raw.wait_fx)}`);
  for (const k of Object.keys(raw)) if (!(THEME_KEYS as readonly string[]).includes(k)) p.push(`未知欄位 ${k}`);
  return p;
}

/** YAML 文字 → 主題表（最上層是 `plaques:` 與 `themes:`）。 */
export function parseRegionThemes(text: string): RegionThemeTable {
  const out: RegionThemeTable = { plaques: {}, themes: {}, errors: [] };
  let doc: unknown;
  try {
    doc = parse(text);
  } catch (e) {
    out.errors.push(`YAML 格式錯誤：${String(e)}`);
    return out;
  }
  const root = isObj(doc) ? doc : {};
  if (!isObj(root.plaques)) out.errors.push("缺少 plaques 對照表");
  else
    for (const [id, raw] of Object.entries(root.plaques)) {
      const p = ID_RE.test(id) ? plaqueProblems(raw) : ["id 格式錯誤"];
      if (p.length > 0) out.errors.push(`plaques.${id}：${p.join("；")}`);
      else out.plaques[id] = raw as PlaqueDef;
    }
  if (!isObj(root.themes)) out.errors.push("缺少 themes 對照表");
  else
    for (const [id, raw] of Object.entries(root.themes)) {
      const p = ID_RE.test(id) ? themeProblems(raw, Object.keys(out.plaques)) : ["id 格式錯誤"];
      if (p.length > 0) out.errors.push(`themes.${id}：${p.join("；")}`);
      else out.themes[id] = raw as RegionThemeDef;
    }
  if (out.themes[FALLBACK_THEME] === undefined) out.errors.push(`缺少 ${FALLBACK_THEME} 主題`);
  return out;
}

/** 內建的主題表（build 時匯入）。 */
export const REGION_THEMES: RegionThemeTable = parseRegionThemes(themesYaml);

/** 整份檔壞掉時的最後退路（同 yaml 的 hub）。 */
const HARD_FALLBACK: RegionThemeDef = { accent: "#a898ff", corner: "filigree", plaque: "crystal", portrait_ring: "#a898ff", ink: "#22305a", seal: "#7a5ad0", wait_fx: "crystal" };
const HARD_PLAQUE: PlaqueDef = { top: "#2a2a5a", bottom: "#1a1a3a" };

/** 該區的主題；`null`、空字串、沒有這區時用 hub。 */
export function regionThemeFor(region: string | null | undefined, table: RegionThemeTable = REGION_THEMES): RegionTheme {
  const id = region != null && table.themes[region] !== undefined ? region : FALLBACK_THEME;
  const def = table.themes[id] ?? HARD_FALLBACK;
  return { ...def, id, wait_fx: def.wait_fx ?? "none", plaqueColors: table.plaques[def.plaque] ?? HARD_PLAQUE };
}

/** 大世界的目前區域：實地地圖的 region（主城與室內是 capital），沒有實地地圖時用區域圖的 region。 */
export function worldRegion(view: { field?: { region?: string | null } | null; map?: { region?: string | null } | null }): string | null {
  return view.field?.region ?? view.map?.region ?? null;
}

/** 主題 → `<html>` 上的 CSS 變數（`--rt-*`）。 */
export function themeCssVars(theme: RegionTheme): Record<string, string> {
  return {
    "--rt-accent": theme.accent,
    "--rt-ring": theme.portrait_ring,
    "--rt-ink": theme.ink,
    "--rt-seal": theme.seal,
    "--rt-plaque-top": theme.plaqueColors.top,
    "--rt-plaque-bottom": theme.plaqueColors.bottom,
    "--rt-corners": cornerLayers(theme.corner, theme),
  };
}

// ---------------- 目前主題（畫面堆疊：大世界裡開戰鬥時戰鬥在上，戰鬥結束退回大世界） ----------------

let stack: { token: number; region: string | null }[] = [];
let nextToken = 1;
let current: RegionTheme = regionThemeFor(null);
let swap = 0;
let swapTimer: ReturnType<typeof setTimeout> | null = null;
/** 換區域時點綴淡入的時間（毫秒；CSS `rt-in` 動畫同長）。 */
export const SWAP_MS = 300;
const listeners = new Set<() => void>();

function apply(): void {
  const top = stack[stack.length - 1];
  const theme = regionThemeFor(top?.region ?? null);
  if (theme.id === current.id && typeof document !== "undefined" && document.documentElement.dataset.region === theme.id) return;
  current = theme;
  swap += 1;
  if (typeof document !== "undefined") {
    const root = document.documentElement;
    for (const [k, v] of Object.entries(themeCssVars(theme))) root.style.setProperty(k, v);
    root.dataset.region = theme.id;
    // 換區域時點綴淡入 0.3 秒（CSS 依 a／b 交替重播動畫；減少動態時 CSS 不播）。過一會兒拿掉，
    // 之後才打開的彈窗不會每次都淡入。
    root.dataset.rtSwap = swap % 2 === 0 ? "a" : "b";
    if (swapTimer !== null) clearTimeout(swapTimer);
    swapTimer = setTimeout(() => {
      delete root.dataset.rtSwap;
      swapTimer = null;
    }, SWAP_MS + 100);
  }
  for (const l of [...listeners]) l();
}

/** 登記一個畫面的區域；回傳更新與移除的函式（測試與 `useRegionTheme` 用）。 */
export function pushRegion(region: string | null): { set(region: string | null): void; pop(): void } {
  const token = nextToken++;
  stack.push({ token, region });
  apply();
  return {
    set(r) {
      const e = stack.find((x) => x.token === token);
      if (e !== undefined) e.region = r;
      apply();
    },
    pop() {
      stack = stack.filter((x) => x.token !== token);
      apply();
    },
  };
}

/** 目前生效的主題（沒有畫面登記時是 hub）。 */
export function currentTheme(): RegionTheme {
  return current;
}

function subscribe(cb: () => void): () => void {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

/** 讀目前主題（頭像框色等要在 JS 裡用的值）。 */
export function useCurrentTheme(): RegionTheme {
  return useSyncExternalStore(subscribe, currentTheme, currentTheme);
}

/** 畫面登記自己的區域（大世界、戰鬥）；卸載時移除，退回下面一層（最底是 hub）。 */
export function useRegionTheme(region: string | null | undefined): void {
  const r = region ?? null;
  const handle = useRef<ReturnType<typeof pushRegion> | null>(null);
  // 掛上時登記一次（保住在堆疊裡的位置），之後只更新區域
  useEffect(() => {
    const h = pushRegion(r);
    handle.current = h;
    return () => {
      h.pop();
      handle.current = null;
    };
  }, []);
  useEffect(() => {
    handle.current?.set(r);
  }, [r]);
}
