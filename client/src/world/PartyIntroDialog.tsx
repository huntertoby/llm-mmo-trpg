// 隊友加入當下的台詞（OB-8，#154；09 9.6「預設隊友的出場」）：伺服器的 `WorldView.party_intro` 一次給一段還沒播的
// （賽倫：按了「確定出發」之後；之後的劇情夥伴照伺服器給的時機），前端只負責播，播誰、說什麼全部來自伺服器。
// 對話框，不另做過場、不給選項；沿用共用彈窗外框 DialogFrame 與開場 `AwakenDialog` 的對話排法（浮動卡規則 6.5.1）。
// 按「好」送既有的 `hint_seen {ids: [seen_id]}`（看過＝`intro:<成員 ID>`）。
import type { WorldPartyIntro } from "../api/types";
import { DialogFrame } from "../ui/DialogFrame";
import { Portrait } from "./StoryIcons";

/** 這一段要不要播：伺服器有給、有台詞、這次畫面裡還沒關掉（`seen` 含本機剛關掉的 ID）。 */
export function partyIntroShown(intro: WorldPartyIntro | null | undefined, seen: ReadonlySet<string>): intro is WorldPartyIntro {
  return intro != null && intro.lines.length > 0 && !seen.has(intro.seen_id);
}

/** 標題：「{名字}加入隊伍」。 */
export function partyIntroTitle(intro: WorldPartyIntro): string {
  return `${intro.name_zh}加入隊伍`;
}

/** 說話者頭像邊長（需求 3.5：同開場的 `AwakenDialog`；800×600 也不另縮）。 */
export const INTRO_FACE = 48;

/**
 * PNL-4（OB-8 可修，需求 3.5）：每句台詞改成開場 `AwakenDialog` 的 `world-dialog` 排法——左邊說話者頭像 48、右邊粗體名字＋台詞。
 * 頭像與框色來自伺服器（`PartyIntroLine.portrait`／`region`，伺服器照說話者對好），前端不用名字查；沒有頭像＝`Portrait` 的通用剪影。
 * 同一人連續兩句也每句一個頭像（需求第 5 節第 10 點美術建議：不合併，和字幕一致）。
 */
export function PartyIntroDialog({ intro, onClose }: { intro: WorldPartyIntro; onClose(): void }) {
  return (
    <DialogFrame label="隊友" title={partyIntroTitle(intro)}>
      <div className="world-party-intro" data-testid="party-intro" data-member={intro.member}>
        {intro.lines.map((line, i) => (
          <div key={i} className="world-dialog world-awaken-line" data-testid="party-intro-line" data-region={line.region ?? undefined}>
            <Portrait portrait={line.portrait ?? null} region={line.region ?? null} size={INTRO_FACE} label={line.speaker_zh} />
            <div className="world-dialog-body">
              <div className="world-dialog-name small">
                <b>{line.speaker_zh}</b>
              </div>
              <p className="world-awaken-text">{line.text_zh}</p>
            </div>
          </div>
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
