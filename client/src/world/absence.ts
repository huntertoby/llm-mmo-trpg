// 「你不在的時候」摘要的小工具（Phase 5F-1b）：文字由後端算好（隱藏地點已套提示語），這裡只決定要不要跳、
// 看過時送哪個動作。
import type { AbsenceView, WorldAction } from "../api/types";

/** 有新消息才跳（空的摘要不跳，也不用送「看過」）。 */
export function shouldShowAbsence(view: AbsenceView | null): view is AbsenceView {
  return view !== null && view.items.length > 0;
}

/** 看過：把摘要算到的時刻送回（期間新發生的事下次再跳）。 */
export function newsSeenAction(view: AbsenceView): WorldAction {
  return { kind: "news_seen", until: view.as_of };
}

/** 每一行前面的小標，例「世界事件」。 */
export function absenceKindLabel(kind: string): string {
  switch (kind) {
    case "world_event":
      return "世界事件";
    case "bounty":
      return "懸賞";
    case "opened":
      return "新區域";
    default:
      return "消息";
  }
}
