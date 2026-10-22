// 場景物件的預覽（純函式）：穿透的路線與穿過的物件、推倒壓住的範圍與倒塌物、投擲的物件與落點。
// 伺服器的 `PreviewOut.pierce／topples／hurls` → 畫在格子上的標記（Overlay）與預覽文字。
import type { BattleView, Pos, PreviewOut } from "../api/types";
import { objectName } from "./glossary";
import { auraTiles } from "./summons";
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
  | "dash_end" // 衝鋒的終點（目標身旁）；直線衝撞的終點
  | "charge_hit" // 直線衝撞沿途會撞到的敵人（標命中率；Phase 3D-2c）
  | "leap_to" // 跳躍的落點
  | "swap" // 交換位置的兩格
  | "teleport_from" // 傳送他人：被傳送的單位原位置（Phase 3D-2b）
  | "teleport_to" // 傳送他人：落點
  | "teleport_lethal" // 傳送他人：落在致命地形（成功率極低）
  | "summon_at" // 召喚物出現的格子（Phase 3D-4b）
  | "summon_aura" // 圖騰光環涵蓋的格子
  | "summon_gone" // 因超過上限而消失的舊召喚物
  | "bomb_blast" // 定時炸彈爆炸時波及的格子（以攜帶者目前的位置展開；Phase 3D-8b）
  | "bomb_at" // 綁上炸彈的單位（標倒數）
  | "revive_at" // 復活的單位站起來的格子
  | "followup_area"; // 複合技能動作段的範圍（Phase 3F-3b）

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
  for (const s of p.summons ?? []) {
    const at = pos(s.pos);
    if (s.totem_radius != null) {
      for (const t of auraTiles(at, s.totem_radius, view)) out.push({ pos: t, kind: "summon_aura", label: "" });
    }
    out.push({ pos: at, kind: "summon_at", label: s.totem_radius == null ? "召" : "圖" });
    for (const id of s.replaces) {
      const old = unitPos(view, id);
      if (old !== null) out.push({ pos: old, kind: "summon_gone", label: "消" });
    }
  }
  for (const b of p.bombs ?? []) {
    for (const t of b.tiles) out.push({ pos: pos(t), kind: "bomb_blast", label: "" });
    const at = unitPos(view, b.unit_id);
    if (at !== null) out.push({ pos: at, kind: "bomb_at", label: `炸${b.rounds}` });
  }
  for (const r of p.revives ?? []) out.push({ pos: pos(r.pos), kind: "revive_at", label: "復" });
  for (const xy of p.followup_tiles ?? []) out.push({ pos: pos(xy), kind: "followup_area", label: "" });
  const lethal = (p.displace_checks ?? []).some((c) => c.lethal);
  for (const m of p.moves ?? []) out.push(...(m.kind === "charge" ? chargeOverlays(m, p, view) : moveOverlays(m, lethal)));
  return out;
}

/** 直線衝撞：沿途的格子畫點，會被撞到的敵人標命中率，終點標「衝」（Phase 3D-2c）。 */
function chargeOverlays(m: MoveOut, p: PreviewOut, view: BattleView): Overlay[] {
  const last = m.path[m.path.length - 1];
  if (last === undefined) return [];
  const hits = new Map<string, string>();
  for (const t of p.targets) {
    const at = t.ally ? null : unitPos(view, t.unit_id);
    if (at !== null) hits.set(`${at.x},${at.y}`, pct(t.hit_permille));
  }
  const walked = new Set(m.path.map((xy) => `${xy[0]},${xy[1]}`));
  const route: Overlay[] = m.path.slice(1, -1).map((xy) => {
    const hit = hits.get(`${xy[0]},${xy[1]}`);
    return hit === undefined ? { pos: pos(xy), kind: "dash_path", label: "" } : { pos: pos(xy), kind: "charge_hit", label: hit };
  });
  // 停點之後的敵人（目標格上的敵人、貼牆或地圖邊的敵人，Phase 3-29）：施放者不會走到那裡，仍標命中率
  const beyond: Overlay[] = [...hits].filter(([key]) => !walked.has(key)).map(([key, label]) => {
    const [x, y] = key.split(",").map(Number);
    return { pos: { x: x ?? 0, y: y ?? 0 }, kind: "charge_hit", label };
  });
  const end: Overlay[] = m.path.length < 2 ? [] : [{ pos: pos(last), kind: "dash_end", label: "衝" }];
  return [...route, ...beyond, ...end];
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
  if (m.kind === "shadowstep") return [{ pos: pos(last), kind: "leap_to", label: "瞬" }]; // 瞬步（Phase 3D-8d）
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
  if (m.kind === "shadowstep") {
    return `瞬步：${who} 瞬間出現在 ${last === undefined ? "?" : posText(last)}，落地後面向目標（不會被藉機攻擊）`;
  }
  if (m.kind === "teleport") {
    return `傳送：${who} ${first === undefined ? "?" : posText(first)} → ${last === undefined ? "?" : posText(last)}（落點的陷阱與表面照常結算，不會被藉機攻擊）`;
  }
  return `交換：${who} ${first === undefined ? "?" : posText(first)} ⇄ ${other} ${last === undefined ? "?" : posText(last)}`;
}

/** 直線衝撞的預覽文字：路線、被撞到的敵人（命中率）與命中後的效果、被擋住時的說明。 */
function chargeLine(m: MoveOut, p: PreviewOut, names: UnitNames): string {
  const path = m.path;
  const who = names.label(m.unit_id);
  const last = path[path.length - 1];
  const chosen = (p.action as { target_pos?: { x: number; y: number } | null }).target_pos ?? null;
  const blocked =
    last !== undefined && chosen !== null && (chosen.x !== last[0] || chosen.y !== last[1])
      ? `（停點與選的目標不同：選的目標是 (${chosen.x}, ${chosen.y})，實際停在 ${posText(last)}）`
      : "";
  const foes = p.targets.filter((t) => !t.ally);
  const hit =
    foes.length === 0
      ? "沿途沒有敵人"
      : `沿途會撞到 ${foes.map((t) => `${names.label(t.unit_id)}（命中 ${pct(t.hit_permille)}）`).join("、")}，命中者受傷` +
        (foes.some((t) => t.knock_permille != null) ? "並可能被撞倒" : "並被推到路徑旁");
  const bumped = (p.collisions ?? []).filter((c) => foes.some((t) => t.unit_id === c.unit_id));
  const bump =
    bumped.length === 0
      ? ""
      : `；${bumped.map((c) => names.label(c.unit_id)).join("、")} 背後被擋住，命中後另受一次撞擊（${bumped.map((c) => `${c.minimum}–${c.maximum}`).join("、")} 傷害）`;
  return `衝撞：${who} 沿 ${path.map((xy) => posText(xy)).join("→")} 直線衝過去${blocked}；${hit}${bump}（隊友讓路，不會被藉機攻擊，沿途陷阱與表面照常結算）`;
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
  for (const m of p.moves ?? []) lines.push(m.kind === "charge" ? chargeLine(m, p, names) : moveLine(m, names));
  const landing = p.landing ?? null;
  if (landing !== null && (p.followup_tiles ?? []).length > 0) {
    lines.push(followupLine(p.followup_when ?? null, posText(landing), p.followup_tiles.length));
  }
  lines.push(...displaceLines(p, names));
  return lines;
}

/** 預覽的第二段說明（依種類，Phase 3F-4b）。 */
export function followupLine(when: string | null, at: string, count: number): string {
  switch (when) {
    case "after_action":
      return `第二段：從 ${at} 位移到選的落點（紫色）`;
    case "after_gather":
      return `第二段：以聚集點 ${at} 為中心影響 ${count} 格（紫色）`;
    case "on_kill":
      return `第二段（打倒敵人才有）：從 ${at} 起算，影響 ${count} 格（紫色）`;
    case "on_hit":
      return `第二段（命中才有）：從 ${at} 對同一個目標，影響 ${count} 格（紫色）`;
    case "delayed":
      return `延遲段：施放後開始蓄力，之後以自己當下的位置為中心釋放；目前預計影響 ${count} 格（紫色），倒下、暈眩或冰凍會取消`;
    default:
      return `第二段：位移到 ${at} 後，以落點為原點影響 ${count} 格（紫色）；位移被擋下或沒到落點時不結算`;
  }
}
