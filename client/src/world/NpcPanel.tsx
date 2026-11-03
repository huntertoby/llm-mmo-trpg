// 這裡的人（Phase 5B-5；09 9.6.7 #3、#5）：所在地點的 NPC（好感度級別與級距，玩家看得到）、「說話」（依好感度給傳聞、
// 任務入口、祕密）、自由聊天（只換資訊）、這裡可以接的任務。對話紀錄只在前端保留（代決 5B5-8）。
// 聊天文字是純資料欄位，後端把它包進 LLM 的 <player_input>。
import { useState } from "react";
import type { WorldAction, WorldView } from "../api/types";
import { Hint } from "../ui/Hint";
import { affinityLine, canSendChat, lengthLabel, PLAYER_TEXT_MAX, type ChatEntry } from "./story";
import { Portrait } from "./StoryIcons";

interface Props {
  view: WorldView;
  busy: boolean;
  chats: Readonly<Record<string, ChatEntry[]>>;
  onAct(action: WorldAction): void;
  onChat(npc: string, text: string): Promise<boolean>;
  /** 只顯示這一位 NPC 與他給的任務（6B-4：走到 NPC 旁邊開的浮動面板）；省略＝這裡所有的人。 */
  only?: string;
}

export function NpcPanel({ view, busy, chats, onAct, onChat, only }: Props) {
  const all = view.npcs_here ?? [];
  const npcs = only === undefined ? all : all.filter((n) => n.id === only);
  const giver = only === undefined ? undefined : npcs[0]?.name_zh;
  const quests = (view.quests_here ?? []).filter((q) => only === undefined || (giver !== undefined && q.giver_zh === giver));
  const [open, setOpen] = useState<string | null>(null);
  const [text, setText] = useState("");
  if (npcs.length === 0 && quests.length === 0) return null;
  const blocked = view.encounter !== null || view.battle_id !== null || view.pending_flash != null || view.pending_offer != null;

  async function send(npc: string) {
    if (await onChat(npc, text.trim())) setText("");
  }

  return (
    <div className="panel world-npcs" data-testid="world-npcs">
      <div className="section-title">{only === undefined ? "這裡的人" : "對話"}</div>
      {npcs.map((n) => (
        <div key={n.id} className="world-npc" data-testid="world-npc" data-npc={n.id} tabIndex={-1}>
          <div className="world-npc-head">
            <b>{n.name_zh}</b>
            {n.role_zh !== "" && <span className="muted small">　{n.role_zh}</span>}
            <Hint text={`好感度只影響對話內容與任務分支，不影響數值。${n.talk_zh}`}>
              <span className={`world-rank rank-${n.rank}`} tabIndex={0} data-testid="world-npc-rank">
                {affinityLine(n)}
              </span>
            </Hint>
          </div>
          <div className="run-actions">
            <Hint text={n.talk_zh}>
              <button type="button" disabled={busy || blocked} onClick={() => onAct({ kind: "talk", npc: n.id })} data-testid="world-talk">
                說話
              </button>
            </Hint>
            <button
              type="button"
              aria-expanded={open === n.id}
              disabled={blocked}
              onClick={() => setOpen((cur) => (cur === n.id ? null : n.id))}
              data-testid="world-chat-toggle"
            >
              {open === n.id ? "收起對話" : "聊天"}
            </button>
          </div>
          {(open === n.id || (chats[n.id] ?? []).length > 0) && (
            <ul className="world-chat-log small" data-testid="world-chat-log">
              {(chats[n.id] ?? []).map((c, i) => (
                <li key={i} className={c.mine ? "mine" : "theirs"}>
                  {!c.mine && <Portrait portrait={n.portrait ?? null} region={view.field?.region ?? null} size={28} />}
                  <b>{c.speaker}：</b>
                  {c.text}
                  {c.more !== undefined && c.more !== "" && <div className="muted">{c.more}</div>}
                </li>
              ))}
            </ul>
          )}
          {open === n.id && (
            <div className="world-chat-input">
              <textarea
                rows={2}
                maxLength={PLAYER_TEXT_MAX}
                value={text}
                disabled={busy}
                onChange={(e) => setText(e.target.value)}
                placeholder={`對${n.name_zh}說……（只換資訊，不換道具）`}
                aria-label={`對${n.name_zh}說的話`}
                data-testid="world-chat-text"
              />
              <div className="run-actions">
                <span className="muted small">{lengthLabel(text)}</span>
                <button type="button" className="primary" disabled={!canSendChat(text, busy)} onClick={() => void send(n.id)} data-testid="world-chat-send">
                  說
                </button>
              </div>
            </div>
          )}
        </div>
      ))}
      {quests.length > 0 && (
        <div className="world-quests-here" data-testid="world-quests-here">
          <div className="section-title small">可以接的任務</div>
          {quests.map((q) => (
            <div key={q.id} className="world-quest-offer">
              <div className="small">
                <b>{q.name_zh}</b>
                <span className="muted">　{q.kind_zh}{q.giver_zh != null ? `・${q.giver_zh}` : ""}</span>
              </div>
              {q.summary_zh !== "" && <div className="muted small">{q.summary_zh}</div>}
              <Hint text={q.problem_zh ?? "接下這個任務（之後在「任務與線頭」看進度）"}>
                <button
                  type="button"
                  disabled={busy || !q.can_accept}
                  onClick={() => onAct({ kind: "accept_quest", quest: q.id })}
                  data-testid="world-accept-quest"
                >
                  接任務{!q.can_accept && q.problem_zh != null ? `（${q.problem_zh}）` : ""}
                </button>
              </Hint>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
