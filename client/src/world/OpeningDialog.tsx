// 開局在主城的開場（Phase 6F-2；09 9.6.9 #125）：新角色在主城醒來時跳一則，說書人一句、守印人一句，下面接任務提示
// 「到霧渡鎮找渡婆婆」。文字由伺服器的 `WorldView.guide.opening` 給（模型關閉時的模板文字）；看過就記在本機，不再跳。
// 沿用詢問視窗外框（DialogFrame，浮動卡規則 6.5.1 的共用元件，不另做彈出層）。
import type { WorldGuide } from "../api/types";
import { DialogFrame } from "../ui/DialogFrame";

type Store = Pick<Storage, "getItem" | "setItem">;

export function openingKey(characterId: string): string {
  return `trpg.world.openingSeen.${characterId}`;
}

function storage(): Store | null {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null;
  }
}

export function readOpeningSeen(characterId: string, store: Store | null = storage()): boolean {
  try {
    return store?.getItem(openingKey(characterId)) === "1";
  } catch {
    return false;
  }
}

export function writeOpeningSeen(characterId: string, store: Store | null = storage()): void {
  try {
    store?.setItem(openingKey(characterId), "1");
  } catch {
    // 私密視窗或封鎖網站資料：只是不記住
  }
}

/** 這個角色現在要不要跳開場：伺服器有給開場、本機還沒看過。 */
export function shouldShowOpening(guide: WorldGuide | null | undefined, seen: boolean): guide is WorldGuide {
  return guide != null && (guide.opening ?? []).length > 0 && !seen;
}

interface Props {
  guide: WorldGuide;
  onClose(): void;
}

export function OpeningDialog({ guide, onClose }: Props) {
  return (
    <DialogFrame label="開場" title="樞島">
      <div className="world-opening" data-testid="world-opening">
        {(guide.opening ?? []).map((line, i) => (
          <p key={i} className="world-opening-line">
            <b>{line.speaker_zh}</b>：{line.text_zh}
          </p>
        ))}
        <p className="world-opening-quest" data-testid="world-opening-quest">
          任務提示：<b>{guide.text_zh}</b>
          {guide.how_zh != null && <span className="muted small">（{guide.how_zh}）</span>}
        </p>
      </div>
      <div className="modal-buttons">
        <button type="button" className="primary" onClick={onClose} data-testid="world-opening-close">
          知道了
        </button>
      </div>
    </DialogFrame>
  );
}
