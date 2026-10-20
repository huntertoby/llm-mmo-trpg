// 推動物件的原因（Phase 3-10；純函式）：主角相鄰有可推動或可推倒的物件時，「推動物件」一律出現；
// 全部不合法時按鈕灰色並說明原因，選取模式中點到推不動的物件也顯示原因。資料來自 API 的 `interact_options`。
import type { BattleView, InteractOption } from "../api/types";
import { objectStyle } from "./glossary";
import { BASIC_MODES, emptyTargets, type ActionMode } from "./targeting";

const PUSH_LABEL = "推動物件";

/** 引擎的原因多半已是「推不動：木箱後方有單位」；其他（AP 不足、高度差過大）補上前綴。 */
function withPrefix(reason: string): string {
  return reason.startsWith("推不動") ? reason : `推不動：${reason}`;
}

/** 不合法的推動選項 → 物件 ID → 原因（同一物件只取第一個原因）。 */
export function pushBlockers(options: readonly InteractOption[]): Map<string, string> {
  const out = new Map<string, string>();
  for (const o of options) {
    if (o.mode !== "push" || o.legal || out.has(o.object_id)) continue;
    out.set(o.object_id, withPrefix(o.reason ?? "不能推動"));
  }
  return out;
}

function objectName(view: BattleView, id: string): string {
  const obj = view.objects.find((o) => o.id === id);
  return obj === undefined ? id : `${objectStyle(obj.kind).name}（${obj.pos.x}, ${obj.pos.y}）`;
}

/** 按鈕上顯示的完整原因：一個物件直接顯示原因，多個物件逐一列出名稱與位置。 */
export function pushReasonText(blockers: ReadonlyMap<string, string>, view: BattleView): string {
  const rows = [...blockers.entries()];
  if (rows.length === 1) return rows[0]![1];
  return rows.map(([id, reason]) => `${objectName(view, id)}：${reason}`).join("；");
}

function insertIndex(basic: readonly ActionMode[]): number {
  const rank = (kind: string) => BASIC_MODES.findIndex((b) => b.kind === kind);
  const at = basic.findIndex((m) => rank(m.kind) > rank("interact"));
  return at < 0 ? basic.length : at;
}

/**
 * 依 `interact_options` 補上推動物件的原因：
 * - 已有合法的推動模式：附上推不動的相鄰物件（`blockedObjects`）；
 * - 完全沒有合法的推動、但相鄰有推不動的物件：加一個灰色的「推動物件」模式（`blockedReason`）。
 */
export function withPushReasons(
  basic: readonly ActionMode[],
  options: readonly InteractOption[],
  view: BattleView,
): ActionMode[] {
  const blockers = pushBlockers(options);
  if (blockers.size === 0) return [...basic];
  const existing = basic.find((m) => m.kind === "interact");
  if (existing !== undefined) {
    const blocked = new Map([...blockers].map(([id, r]) => [id, `${objectName(view, id)}：${r}`]));
    return basic.map((m) => (m === existing ? { ...m, blockedObjects: blocked } : m));
  }
  const blockedMode: ActionMode = {
    key: "interact",
    kind: "interact",
    label: PUSH_LABEL,
    skillId: null,
    actions: [],
    targets: emptyTargets(),
    blockedReason: pushReasonText(blockers, view),
  };
  const out = [...basic];
  out.splice(insertIndex(basic), 0, blockedMode);
  return out;
}

/** 選取推動模式時點到的格子上，若是推不動的相鄰物件，回傳原因（否則 `null`）。 */
export function blockedPushAt(mode: ActionMode, view: BattleView, tile: { x: number; y: number }): string | null {
  if (mode.blockedObjects === undefined) return null;
  for (const [id, text] of mode.blockedObjects) {
    const obj = view.objects.find((o) => o.id === id);
    if (obj !== undefined && obj.pos.x === tile.x && obj.pos.y === tile.y) return text;
  }
  return null;
}
