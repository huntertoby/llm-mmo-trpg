// 實地地圖上人物頭頂的東西（Phase 6B-4；21.5、21.7）的純函式：NPC 的好感表情、「！」（新傳聞或可接任務，資料由伺服器給）、
// 對話泡泡（這次請求 NPC 說的話，1～2 句）、朋友（影子）的名牌；以及頭頂在畫布上的位置。
// 朋友的名單「每次進城更新一次、不即時」（21.5）：同一張地圖上沿用進來時的名單（`frozenFriends`）。
import type { ChronicleView, FieldView, Pos, WorldDialogLine } from "../api/types";
import { heightAt, tileLift, topReserve, UNIT_HEADROOM, type HeightGrid } from "../battle/elevation";
import { TILE_SIZE } from "../battle/geometry";
import type { FieldFriend } from "./fieldModel";
import { seasonTitle } from "./season";

export type Rank = "hostile" | "cold" | "neutral" | "friendly" | "trusted";

/** 好感級別 → 表情（嘴的彎度 -1～1、臉色）。照 5 級（9.6.11 #116）。 */
export const RANK_FACE: Readonly<Record<Rank, { mood: number; color: string; zh: string }>> = {
  hostile: { mood: -1, color: "#e04a3a", zh: "敵視" },
  cold: { mood: -0.5, color: "#8fa0b8", zh: "冷淡" },
  neutral: { mood: 0, color: "#d8c8a0", zh: "中立" },
  friendly: { mood: 0.6, color: "#8fd27a", zh: "友善" },
  trusted: { mood: 1, color: "#f2b84a", zh: "信賴" },
};

export function rankOf(value: string | null | undefined): Rank {
  return value != null && value in RANK_FACE ? (value as Rank) : "neutral";
}

export interface HeadMark {
  /** `npc:<id>`、`friend:<owner>` 或 `figure:<物件 ID>`。 */
  key: string;
  /** `figure`＝主城上站著的人（情境物件的 `figure`；RT-5：開場時守印人頭上的「！」與第一個指示）。 */
  kind: "npc" | "friend" | "figure";
  /** NPC ID、影子主人的角色 ID 或情境物件 ID。 */
  id: string;
  name: string;
  pos: Pos;
  /** NPC 的好感級別（朋友為 `null`，不畫表情）。 */
  rank: Rank | null;
  rankZh: string;
  /** 頭上的「！」：任務或傳聞；沒有為 `null`。 */
  alert: "quest" | "rumor" | null;
  alertZh: string | null;
  /** 對話泡泡（1～2 句）；沒有為 `null`。 */
  bubble: string | null;
}

/** 泡泡最多幾個字（超過加「……」）。 */
export const BUBBLE_MAX = 40;

/** 取前 1～2 句（以。！？切），最多 `BUBBLE_MAX` 字。 */
export function bubbleText(text: string): string {
  const sentences = text.match(/[^。！？!?]+[。！？!?]?/g) ?? [text];
  const two = sentences.slice(0, 2).join("").trim();
  return two.length > BUBBLE_MAX ? `${two.slice(0, BUBBLE_MAX)}……` : two;
}

/** 這次請求每位 NPC 說的第一句（酒館的傳聞不算）→ 泡泡文字。 */
export function npcBubbles(dialog: readonly WorldDialogLine[] | null | undefined): Map<string, string> {
  const out = new Map<string, string>();
  for (const line of dialog ?? []) {
    if (line.npc == null || line.kind === "tavern" || out.has(line.npc)) continue;
    out.set(line.npc, bubbleText(line.text_zh));
  }
  return out;
}

/** 開場時站著的人說的話（RT-5 ②；`world/opening.ts` 的 `splitOpening`）：物件 ID → 名字、整句、位置。 */
export type GuideLines = ReadonlyMap<string, { name: string; text: string; x: number; y: number }>;

/** 開場指示的「！」說明。 */
export const GUIDE_ALERT_ZH = "有指示";

/** 頭頂要畫的東西（NPC 依地圖順序，再來是朋友，最後是開場時說話的人；RT-5）。開場的泡泡是整句（不截成 1～2 句）。 */
export function headMarks(field: FieldView, bubbles: ReadonlyMap<string, string> = new Map(), guides: GuideLines = new Map()): HeadMark[] {
  const npcs: HeadMark[] = field.npcs.map((n) => {
    const rank = rankOf(n.rank);
    return {
      key: `npc:${n.id}`,
      kind: "npc",
      id: n.id,
      name: n.name_zh,
      pos: { x: n.x, y: n.y },
      rank,
      rankZh: n.rank_zh || RANK_FACE[rank].zh,
      alert: n.alert ?? null,
      alertZh: n.alert_zh ?? null,
      bubble: bubbles.get(n.id) ?? null,
    };
  });
  const friends: HeadMark[] = (field.friends ?? []).map((f) => ({
    key: `friend:${f.owner}`,
    kind: "friend",
    id: f.owner,
    name: `${f.name_zh}的影子`,
    pos: { x: f.x, y: f.y },
    rank: null,
    rankZh: "",
    alert: null,
    alertZh: null,
    bubble: null,
  }));
  const figures: HeadMark[] = [...guides].map(([id, g]) => ({
    key: `figure:${id}`,
    kind: "figure",
    id,
    name: g.name,
    pos: { x: g.x, y: g.y },
    rank: null,
    rankZh: "",
    alert: "quest",
    alertZh: GUIDE_ALERT_ZH,
    bubble: g.text,
  }));
  return [...npcs, ...friends, ...figures];
}

/** 頭頂（紙娃娃頭的上緣）在畫布上的位置（CSS 像素，畫布左上角為原點；含抬高與上方預留）。 */
export function headAnchor(grid: HeightGrid, p: Pos, scale: number): { left: number; top: number } {
  const top = topReserve(grid) + p.y * TILE_SIZE - tileLift(heightAt(grid, p)) - (UNIT_HEADROOM - 4);
  return { left: (p.x + 0.5) * TILE_SIZE * scale, top: top * scale };
}

/**
 * 朋友名單「每次進城更新一次」（21.5，不即時）：同一張地圖上沿用進來時的名單；換了地圖（進城、出門再進來）才換成新的。
 * `prev`＝上次記下的（地圖 ID＋名單）。
 */
export function frozenFriends(
  prev: { map: string; friends: readonly FieldFriend[] } | null,
  field: FieldView,
): { map: string; friends: readonly FieldFriend[] } {
  if (prev !== null && prev.map === field.map_id) return prev;
  return { map: field.map_id, friends: field.friends ?? [] };
}

/** 編年史裡這位朋友的紀錄（季末紀錄、首殺、賽季 Boss 評分；依季、新的在前）；名片用。 */
export function friendChronicle(chronicle: ChronicleView | null | undefined, owner: string): string[] {
  const out: string[] = [];
  for (const season of chronicle?.seasons ?? []) {
    const title = seasonTitle(season);
    for (const h of season.heroes) if (h.character_id === owner) out.push(`${title}：${h.text_zh}`);
    for (const k of season.first_kills) if (k.character_id === owner) out.push(`${title}：首殺 ${k.target_name_zh}`);
    for (const b of season.boss_board) if (b.character_id === owner) out.push(`${title}：賽季 Boss 評分 ${b.score} 分`);
  }
  return out;
}
