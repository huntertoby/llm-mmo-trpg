// 入門期的限制提示（OB-5，#150 第 7、9 點）：開局還沒結束的角色不開放的系統，面板先標成不可用並說明原因。
// 哪些不開放、原因怎麼寫都由伺服器給（`WorldView.limits`：系統 → 原因；和送出動作被拒時回的是同一句）。
// 各面板原本就有「能不能用＋原因」的欄位（換上裝備、換種族、雇傭兵、聯賽報名、賽季 Boss、立誓、每一招的閃現），伺服器在入門期
// 直接把那些欄位標成不可用，畫面照既有的停用樣式與 `Hint` 顯示；這裡補的是沒有對應欄位的地方（換技能、打造只限防具、溶掉與傳承）。
// PNL-1a（資訊面板-移植需求 2.2）：面板上緣那一行改用共用提示 `Callout` 的鎖住級（紫灰）；提示句照舊由伺服器給。
import type { WorldView } from "../api/types";
import { Callout } from "../ui/PanelKit";

/** 伺服器給的鍵（`trpg.world.opening.opening_limits`）。 */
export type LimitKey = "race" | "flash" | "loadout" | "hire" | "league" | "season_boss" | "oath" | "main_hand" | "smith" | "dissolve";

/** 這個系統現在不開放的原因；開放（或已完成開局）＝`null`。 */
export function limitOf(view: Pick<WorldView, "limits"> | null | undefined, key: LimitKey): string | null {
  return view?.limits?.[key] ?? null;
}

/** 面板上緣的一行說明（例：打造與強化只限防具、4 級前不能溶掉技能或傳承）：鎖住級提示（`Callout tone="lock"`）。 */
export function LimitNote({ reason }: { reason: string | null }) {
  if (reason === null) return null;
  return (
    <Callout tone="lock" testId="world-limit-note">
      {reason}
    </Callout>
  );
}
