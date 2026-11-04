// 遊戲名稱與標語（UI-E1；docs/art/全遊戲一致性巡檢.md 第 4 節）：唯一的來源是 `content/ui/game.yaml`，
// build 時以 `?raw` 匯入（Python 端 `trpg.content.ui_game` 的 pydantic schema 由 `trpg content check` 驗證同一份檔）。
// 首頁標題牌、開發選單、瀏覽器分頁標題都讀這裡；名稱定案後只改 yaml 一處。
import { parse } from "yaml";
import gameYaml from "../../../content/ui/game.yaml?raw";

export interface GameInfo {
  title_zh: string;
  tagline_zh: string;
}

/** 檔案壞掉時的退路（不寫死名稱：顯示成「（遊戲名稱）」的空位）。 */
const FALLBACK: GameInfo = { title_zh: "（遊戲名稱）", tagline_zh: "" };

/** 解析 yaml 文字；欄位缺或型別不對時退回空位。 */
export function parseGameInfo(text: string): GameInfo {
  let doc: unknown;
  try {
    doc = parse(text);
  } catch {
    return FALLBACK;
  }
  if (typeof doc !== "object" || doc === null) return FALLBACK;
  const o = doc as Record<string, unknown>;
  const title = typeof o.title_zh === "string" && o.title_zh.trim() !== "" ? o.title_zh : FALLBACK.title_zh;
  const tagline = typeof o.tagline_zh === "string" ? o.tagline_zh : FALLBACK.tagline_zh;
  return { title_zh: title, tagline_zh: tagline };
}

export const GAME_INFO: GameInfo = parseGameInfo(gameYaml);

/** 瀏覽器分頁標題（開發模式加註）。 */
export function documentTitle(dev: boolean, info: GameInfo = GAME_INFO): string {
  return dev ? `${info.title_zh}（開發模式）` : info.title_zh;
}
