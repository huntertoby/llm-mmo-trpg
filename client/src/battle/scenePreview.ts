// 場景物件的預覽（純函式）：穿透的路線與穿過的物件、推倒壓住的範圍與倒塌物、投擲的物件與落點。
// 伺服器的 `PreviewOut.pierce／topples／hurls` → 畫在格子上的標記（Overlay）與預覽文字。
import type { BattleView, Pos, PreviewOut } from "../api/types";
import { objectName } from "./glossary";
import type { UnitNames } from "./units";

export type OverlayKind =
  | "route" // 穿透的路線（施放者與目標之間的格子）
  | "pierced" // 被射線穿過的物件（受全額傷害）
  | "behind" // 物件後方的單位（只受打折的傷害）
  | "crush" // 推倒壓住的格子
  | "rubble" // 倒塌物的位置
  | "hurl_from" // 被舉起的物件
  | "hurl_to"; // 物件的落點

export interface Overlay {
  pos: Pos;
  kind: OverlayKind;
  /** 標在格子上的短字（例如「壓」「70%」）。 */
  label: string;
}

type Xy = readonly [number, number] | number[];

const pos = (xy: Xy): Pos => ({ x: xy[0] as number, y: xy[1] as number });

const DIRECTION_TEXT: Readonly<Record<string, string>> = { "1,0": "東", "-1,0": "西", "0,1": "南", "0,-1": "北" };

/** 推倒的方向（單位向量）→ 「東／西／南／北」。 */
export function directionText(direction: Xy): string {
  return DIRECTION_TEXT[`${direction[0]},${direction[1]}`] ?? "?";
}

function objectLabelById(view: BattleView, id: string): string {
  const obj = view.objects.find((o) => o.id === id);
  return obj === undefined ? "物件" : objectName(obj.kind);
}

function posText(xy: Xy): string {
  return `(${xy[0]}, ${xy[1]})`;
}

function unitPos(view: BattleView, id: string): Pos | null {
  return view.units.find((u) => u.id === id)?.pos ?? null;
}

/** 預覽畫在格子上的標記；沒有場景物件資料時為空。 */
export function previewOverlays(p: PreviewOut | null, view: BattleView): Overlay[] {
  if (p === null) return [];
  const out: Overlay[] = [];
  const pierce = p.pierce ?? null;
  if (pierce !== null) {
    const objectTiles = new Set(pierce.objects.map((o) => `${o.pos[0]},${o.pos[1]}`));
    for (const xy of pierce.route) {
      if (!objectTiles.has(`${xy[0]},${xy[1]}`)) out.push({ pos: pos(xy), kind: "route", label: "" });
    }
    for (const o of pierce.objects) out.push({ pos: pos(o.pos), kind: "pierced", label: "穿" });
    const percent = `${pierce.behind_permille / 10}%`;
    for (const id of pierce.behind) {
      const at = unitPos(view, id);
      if (at !== null) out.push({ pos: at, kind: "behind", label: percent });
    }
  }
  for (const t of p.topples ?? []) {
    for (const xy of t.tiles) out.push({ pos: pos(xy), kind: "crush", label: "壓" });
    if (t.rubble != null) out.push({ pos: pos(t.rubble), kind: "rubble", label: "礫" });
  }
  for (const h of p.hurls ?? []) {
    out.push({ pos: pos(h.from_pos), kind: "hurl_from", label: "舉" });
    out.push({ pos: pos(h.to_pos), kind: "hurl_to", label: "落" });
  }
  return out;
}

const HURL_OUTCOME: Readonly<Record<string, string>> = {
  exploded: "在落點爆炸",
  shattered: "落地時碎掉",
  placed: "落在那裡",
  lost: "找不到落腳處而摧毀",
};

/** 預覽文字中場景物件的幾行（穿透、推倒、投擲）。 */
export function sceneLines(p: PreviewOut, names: UnitNames, view: BattleView): string[] {
  const lines: string[] = [];
  const pierce = p.pierce ?? null;
  if (pierce !== null) {
    if (pierce.objects.length === 0) {
      lines.push("穿透：無視半掩護（射線上沒有可穿過的物件）");
    } else {
      const things = pierce.objects.map((o) => `${objectLabelById(view, o.object_id)}${posText(o.pos)}`).join("、");
      const percent = `${pierce.behind_permille / 10}%`;
      const behind = pierce.behind.map((id) => names.label(id)).join("、");
      lines.push(`穿透：穿過${things}（物件受全額傷害）${behind === "" ? "" : `，後方 ${behind} 只受 ${percent} 傷害`}`);
    }
  }
  for (const t of p.topples ?? []) {
    const name = objectLabelById(view, t.object_id);
    const crushed = t.units.map((id) => names.label(id)).join("、");
    const tiles = t.tiles.map((xy) => posText(xy)).join("、") || "沒有格子";
    const rubble = t.rubble == null ? "不留倒塌物" : `倒塌物留在 ${posText(t.rubble)}`;
    lines.push(
      `推倒：${name}${posText(t.pos)}往${directionText(t.direction)}倒下，壓住 ${tiles}${crushed === "" ? "" : `（壓到 ${crushed}）`}；${rubble}`,
    );
  }
  for (const h of p.hurls ?? []) {
    const name = objectName(h.kind);
    lines.push(`投擲：${name}${posText(h.from_pos)} → ${posText(h.to_pos)}，${HURL_OUTCOME[h.outcome] ?? h.outcome}`);
  }
  return lines;
}
