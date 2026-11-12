// 隊友加入當下的台詞（OB-8，#154；09 9.6「預設隊友的出場」）：伺服器的 `WorldView.party_intro` 一次給一段還沒播的
// （賽倫：按了「確定出發」之後；之後的劇情夥伴照伺服器給的時機），前端只負責播，播誰、說什麼全部來自伺服器。
// 對話框，不另做過場、不給選項；沿用共用彈窗外框 DialogFrame 與開場／靶場那段話的樣式（浮動卡規則 6.5.1）。
// 按「好」送既有的 `hint_seen {ids: [seen_id]}`（看過＝`intro:<成員 ID>`）。
import type { WorldPartyIntro } from "../api/types";
import { DialogFrame } from "../ui/DialogFrame";

/** 這一段要不要播：伺服器有給、有台詞、這次畫面裡還沒關掉（`seen` 含本機剛關掉的 ID）。 */
export function partyIntroShown(intro: WorldPartyIntro | null | undefined, seen: ReadonlySet<string>): intro is WorldPartyIntro {
  return intro != null && intro.lines.length > 0 && !seen.has(intro.seen_id);
}

/** 標題：「{名字}加入隊伍」。 */
export function partyIntroTitle(intro: WorldPartyIntro): string {
  return `${intro.name_zh}加入隊伍`;
}

export function PartyIntroDialog({ intro, onClose }: { intro: WorldPartyIntro; onClose(): void }) {
  return (
    <DialogFrame label="隊友" title={partyIntroTitle(intro)}>
      <div className="world-opening" data-testid="party-intro" data-member={intro.member}>
        {intro.lines.map((line, i) => (
          <p key={i} className="world-opening-line">
            <b>{line.speaker_zh}</b>：{line.text_zh}
          </p>
        ))}
      </div>
      <div className="modal-buttons">
        <button type="button" className="primary" onClick={onClose} data-testid="party-intro-close" autoFocus>
          好
        </button>
      </div>
    </DialogFrame>
  );
}
