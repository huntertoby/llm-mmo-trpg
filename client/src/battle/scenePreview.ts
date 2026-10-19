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
  | "hurl_to" // 物件的落點
  | "dash_path" // 衝鋒經過的格子（Phase 3D-2）
  | "dash_end" // 衝鋒的終點（目標身旁）
  | "leap_to" // 跳躍的落點
  | "swap" // 交換位置的兩格
  | "teleport_from" // 傳送他人：被傳送的單位原位置（Phase 3D-2b）
  | "teleport_to" // 傳送他人：落點
  | "teleport_lethal"; // 傳送他人：落在致命地形（成功率極低）

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
  const lethal = (p.displace_checks ?? []).some((c) => c.lethal);
  for (const m of p.moves ?? []) out.push(...moveOverlays(m, lethal));
  return out;
}

type MoveOut = NonNullable<PreviewOut["moves"]>[number];

/** 自身位移（衝鋒、跳躍、交換位置）的標記：衝鋒畫路線與終點、跳躍畫落點、交換位置畫兩格。 */
function moveOverlays(m: MoveOut, lethal: boolean): Overlay[] {
  const path = m.path;
  const last = path[path.length - 1];
  if (last === undefined) return [];
  if (m.kind === "dash") {
    const route: Overlay[] = path.slice(1, -1).map((xy) => ({ pos: pos(xy), kind: "dash_path", label: "" }));
    return path.length > 1 ? [...route, { pos: pos(last), kind: "dash_end", label: "衝" }] : [];
  }
  if (m.kind === "leap") return [{ pos: pos(last), kind: "leap_to", label: "躍" }];
  const first = path[0];
  if (m.kind === "teleport") {
    return first === undefined
      ? []
      : [
          { pos: pos(first), kind: "teleport_from", label: "傳" },
          { pos: pos(last), kind: lethal ? "teleport_lethal" : "teleport_to", label: lethal ? "險" : "落" },
        ];
  }
  return first === undefined
    ? []
    : [
        { pos: pos(first), kind: "swap", label: "換" },
        { pos: pos(last), kind: "swap", label: "換" },
      ];
}

const HURL_OUTCOME: Readonly<Record<string, string>> = {
  exploded: "在落點爆炸",
  shattered: "落地時碎掉",
  placed: "落在那裡",
  lost: "找不到落腳處而摧毀",
};

function moveLine(m: MoveOut, names: UnitNames): string {
  const path = m.path;
  const who = names.label(m.unit_id);
  const other = m.other_id == null ? "" : names.label(m.other_id);
  const last = path[path.length - 1];
  const first = path[0];
  if (m.kind === "dash") {
    if (path.length <= 1) return `衝鋒：${who} 已在 ${other} 身旁，不需要移動`;
    return `衝鋒：${who} 沿 ${path.map((xy) => posText(xy)).join("→")} 衝到 ${other} 身旁（途中會被藉機攻擊、踩到陷阱）`;
  }
  if (m.kind === "leap") return `跳躍：${who} 越過中間的單位與低矮地形，落在 ${last === undefined ? "?" : posText(last)}（不會被藉機攻擊）`;
  if (m.kind === "teleport") {
    return `傳送：${who} ${first === undefined ? "?" : posText(first)} → ${last === undefined ? "?" : posText(last)}（落點的陷阱與表面照常結算，不會被藉機攻擊）`;
  }
  return `交換：${who} ${first === undefined ? "?" : posText(first)} ⇄ ${other} ${last === undefined ? "?" : posText(last)}`;
}

type CheckOut = NonNullable<PreviewOut["displace_checks"]>[number];

function pct(permille: number): string {
  const p = permille / 10;
  return `${Number.isInteger(p) ? p : p.toFixed(1)}%`;
}

/** 位移的抵抗判定文字：每個敵方的成功率（致命地形特別標示）、總成功率；友方不檢定。 */
export function displaceLines(p: PreviewOut, names: UnitNames): string[] {
  const checks: readonly CheckOut[] = p.displace_checks ?? [];
  const moves = p.moves ?? [];
  if (checks.length === 0) {
    if (moves.some((m) => m.kind === "teleport")) return ["傳送：友方不需檢定，必定成功"];
    if (moves.some((m) => m.kind === "swap")) return ["互換：友方不需檢定，必定成功"];
    return [];
  }
  const lines = checks.map((c) =>
    c.lethal
      ? `⚠ 傳送到致命地形：${names.label(c.unit_id)} 要過極難的抵抗（抵抗 +${c.resist_bonus}），成功率只有 ${pct(c.success_permille)}；失敗時不會移動`
      : `位移檢定：${names.label(c.unit_id)} 成功率 ${pct(c.success_permille)}${c.resist_bonus > 0 ? `（抵抗 +${c.resist_bonus}）` : ""}`,
  );
  if (checks.length > 1 && p.displace_permille != null) {
    lines.push(`互換成功率：${pct(p.displace_permille)}（每個敵人都要被你勝過）`);
  }
  return lines;
}

/** 預覽文字中場景物件與自身位移的幾行（穿透、推倒、投擲、衝鋒、跳躍、交換）。 */
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
  for (const m of p.moves ?? []) lines.push(moveLine(m, names));
  lines.push(...displaceLines(p, names));
  return lines;
}
