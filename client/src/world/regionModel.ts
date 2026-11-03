// 區域圖（只能看；Phase 6C-6，21.1、21.2）的純函式：迷霧三段、標記、傳送石能不能點。
// 規則一律由後端算好（`WorldMapView.fog`、`stones`、`can_teleport`），這裡只決定外觀與說明文字。
// 底圖：還沒有區域插畫時用節點圖的座標與連線（`art_url` 有值時改畫插畫，節點照樣疊在上面）。
import type { WorldLocationView, WorldMapView } from "../api/types";

export type Fog = WorldLocationView["fog"];
type StoneView = WorldMapView["stones"][number];

/** 沒去過的地點的名字（21.1：灰色剪影寫「？？？」）。 */
export const UNKNOWN_ZH = "？？？";

export interface RegionStone {
  id: string;
  /** `go`＝可以點了傳送；`here`＝現在出發的這一顆；`locked`＝還沒解鎖；`view`＝已解鎖但現在只能看。 */
  state: "go" | "here" | "locked" | "view";
  hint: string;
}

export interface RegionNode {
  id: string;
  x: number;
  y: number;
  fog: Fog;
  /** 顯示的名字（剪影是「？？？」，霧裡不顯示＝`null`）。 */
  label: string | null;
  /** 建議等級（霧裡不顯示）。 */
  level: string | null;
  /** 已清空（只有去過的地點顯示）。 */
  cleared: boolean;
  current: boolean;
  town: boolean;
  quests: readonly string[];
  stones: readonly RegionStone[];
  hint: string;
}

export interface RegionEdge {
  key: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  /** 兩端都去過＝實線；一端是剪影＝虛線。 */
  known: boolean;
}

/** 傳送石的狀態與說明（21.1：只有站在傳送石上或在城鎮裡打開時，已解鎖的才可以點）。 */
export function stoneState(map: WorldMapView, stone: StoneView, placeName: string): RegionStone {
  const name = `${placeName}的傳送石`;
  if (stone.here) return { id: stone.id, state: "here", hint: `${name}：你在這裡` };
  if (!stone.unlocked) return { id: stone.id, state: "locked", hint: `${name}：還沒解鎖（先親自走到這顆傳送石）` };
  if (map.can_teleport) return { id: stone.id, state: "go", hint: `${name}：點一下傳送過去` };
  const why = map.teleport_problem_zh ?? "現在不能傳送";
  return { id: stone.id, state: "view", hint: `${name}：已解鎖。${why}` };
}

/** 地點的說明卡文字。 */
export function nodeHint(loc: WorldLocationView, fog: Fog): string {
  if (fog === "fog") return "被霧蓋住的地方";
  const level = loc.level_zh ?? "";
  if (fog === "silhouette") return [UNKNOWN_ZH, level === "" ? null : `建議 ${level}`, "還沒去過"].filter((s) => s !== null).join("\n");
  const head = [loc.kind_zh, level, loc.cleared ? "已清空" : null].filter((s): s is string => s !== null && s !== "");
  const lines = [`${loc.name_zh}（${head.join("・")}）`];
  if (loc.current) lines.push("目前位置");
  for (const q of loc.quest_marks) lines.push(`任務：${q}`);
  return lines.join("\n");
}

/** 地圖上的節點（隱藏地點後端根本不送，這裡不用另外濾）。 */
export function regionNodes(map: WorldMapView): RegionNode[] {
  const stones = map.stones;
  return map.locations.map((loc) => {
    const fog = loc.fog;
    const shown = fog !== "fog";
    const label = fog === "visited" ? loc.name_zh : fog === "silhouette" ? UNKNOWN_ZH : null;
    const name = fog === "visited" ? loc.name_zh : UNKNOWN_ZH;
    return {
      id: loc.id,
      x: loc.x,
      y: loc.y,
      fog,
      label,
      level: shown ? loc.level_zh : null,
      cleared: fog === "visited" && loc.cleared,
      current: loc.current,
      town: loc.kind === "town",
      quests: shown ? loc.quest_marks : [],
      stones: shown ? stones.filter((s) => s.location === loc.id).map((s) => stoneState(map, s, name)) : [],
      hint: nodeHint(loc, fog),
    };
  });
}

/** 畫出來的連線：兩端都不在霧裡才畫（霧裡的路看不到）。 */
export function regionEdges(map: WorldMapView): RegionEdge[] {
  const byId = new Map(map.locations.map((l) => [l.id, l]));
  const out: RegionEdge[] = [];
  for (const [a, b] of map.edges) {
    const from = byId.get(a);
    const to = byId.get(b);
    if (from === undefined || to === undefined) continue;
    const fa = from.fog;
    const fb = to.fog;
    if (fa === "fog" || fb === "fog") continue;
    out.push({ key: `${a}-${b}`, x1: from.x, y1: from.y, x2: to.x, y2: to.y, known: fa === "visited" && fb === "visited" });
  }
  return out;
}

/** 面板上方的一行說明（現在能不能從圖上傳送）。 */
export function regionNote(map: WorldMapView): string {
  if (map.can_teleport) return "可以傳送：點已解鎖的傳送石";
  return `只能看：${map.teleport_problem_zh ?? "現在不能傳送"}`;
}

/** 點傳送石：可以傳送時回傳動作的目標，否則 `null`。 */
export function stoneTarget(stone: RegionStone): string | null {
  return stone.state === "go" ? stone.id : null;
}
