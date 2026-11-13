// 地點留言與足跡（Phase 5E-3；09 9.6.10 #105）：所在地點的留言（最新 20 則）、其他角色的足跡、留一則（50 字）。
// 不過濾、不檢舉、不封鎖；作者可刪自己的、管理者登入時每則都有刪除鍵（5E-3b）。留言是純資料，後端不送進 LLM。
import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { LocationBoard, NoteView } from "../api/types";
import { isSubmitEnter } from "../ui/imeEnter";
import { NOTE_MAX, noteDeleteLabel, noteProblem, noteTime, remainingLabel } from "./notes";

interface Props {
  characterId: string;
  /** 所在地點（換地點時重新讀）。 */
  location: string;
  busy: boolean;
}

export function NotesPanel({ characterId, location, busy }: Props) {
  const [board, setBoard] = useState<LocationBoard | null>(null);
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    let alive = true;
    setBoard(null);
    api
      .worldNotes(characterId)
      .then((b) => alive && setBoard(b))
      .catch((e: unknown) => alive && setError(e instanceof ApiError ? e.message : String(e)));
    return () => {
      alive = false;
    };
  }, [characterId, location]);

  async function remove(note: NoteView) {
    setSending(true);
    setError(null);
    try {
      if (note.mine) {
        setBoard(await api.deleteOwnWorldNote(characterId, note.note_id));
      } else {
        await api.adminDeleteWorldNote(note.note_id);
        setBoard(await api.worldNotes(characterId));
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setSending(false);
    }
  }

  const max = board?.max_len ?? NOTE_MAX;
  const problem = noteProblem(text, max);

  async function send() {
    if (problem !== null) return;
    setSending(true);
    setError(null);
    try {
      setBoard(await api.postWorldNote(characterId, text.trim()));
      setText("");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="panel world-notes" data-testid="world-notes" role="region" aria-label="地點留言">
      <div className="section-title">地點留言{board !== null ? `・${board.location_name_zh}` : ""}</div>
      {board === null ? (
        <div className="muted small">讀取中…</div>
      ) : (
        <>
          {board.notes.length === 0 ? (
            <div className="muted small">這裡還沒有人留言。</div>
          ) : (
            <ul className="world-note-list" data-testid="world-note-list">
              {board.notes.map((n) => (
                <li key={n.note_id}>
                  <b>{n.name}</b>
                  <span className="muted small">　{noteTime(n.at)}</span>
                  {n.can_delete === true && (
                    <button
                      type="button"
                      className="world-note-delete small"
                      data-testid="world-note-delete"
                      aria-label={noteDeleteLabel(n.mine)}
                      disabled={busy || sending}
                      onClick={() => void remove(n)}
                    >
                      刪除
                    </button>
                  )}
                  <div>{n.text}</div>
                </li>
              ))}
            </ul>
          )}
          {board.footprints.length > 0 && (
            <ul className="world-footprints small" data-testid="world-footprints">
              {board.footprints.map((f, i) => (
                <li key={i}>
                  {f.text_zh}
                  <span className="muted">（{noteTime(f.at)}）</span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      <div className="world-note-form">
        <input
          type="text"
          value={text}
          maxLength={max * 2}
          placeholder={`留一句話給之後經過的人（最多 ${max} 字）`}
          aria-label="留言"
          data-testid="world-note-input"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (isSubmitEnter(e)) void send();
          }}
        />
        <button
          type="button"
          data-testid="world-note-send"
          disabled={busy || sending || problem !== null}
          onClick={() => void send()}
        >
          留言
        </button>
      </div>
      <div className="muted small">{text.trim() === "" ? `最多 ${max} 字` : (problem ?? remainingLabel(text, max))}</div>
      {error !== null && <div className="error small">{error}</div>}
    </div>
  );
}
