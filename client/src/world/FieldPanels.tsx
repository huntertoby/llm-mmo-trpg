// 走到人或設施旁邊開的浮動面板（Phase 6B-4；沿用 6B-5 的面板框，同時只開一個）：
// - NPC：只有這一位的對話（說話、聊天、他給的任務），上方是頭像（好感表情）與名字（21.7「對話時顯示 NPC 頭像」）；
// - 雇用：隊伍＋雇用清單（原本「這裡」面板裡的「雇用隊友」展開）；
// - 朋友（影子）：名片＝build（等級、定位、技能、稱號、存的地點）與編年史裡他的紀錄（`GET /api/world/chronicle`）。
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ChronicleView, WorldAction, WorldView } from "../api/types";
import { AccountTitles } from "../ui/AccountTitles";
import { RankFace } from "./FieldHeads";
import { friendChronicle, rankOf } from "./fieldPeople";
import { NpcPanel } from "./NpcPanel";
import { HireEditor, PartyPanel } from "./PartyPanel";
import type { ChatEntry } from "./story";

interface NpcProps {
  view: WorldView;
  npc: string;
  busy: boolean;
  chats: Readonly<Record<string, ChatEntry[]>>;
  onAct(action: WorldAction): void;
  onChat(npc: string, text: string): Promise<boolean>;
}

export function HudNpcPanel({ view, npc, busy, chats, onAct, onChat }: NpcProps) {
  const here = (view.npcs_here ?? []).find((n) => n.id === npc);
  const onMap = view.field?.npcs.find((n) => n.id === npc);
  const name = here?.name_zh ?? onMap?.name_zh ?? npc;
  const rank = rankOf(here?.rank ?? onMap?.rank);
  return (
    <div className="world-hud-stack" data-testid="world-hud-npc" data-npc={npc}>
      <div className="world-npc-portrait">
        <RankFace rank={rank} size={36} />
        <div>
          <b>{name}</b>
          {here?.role_zh ? <span className="muted small">　{here.role_zh}</span> : null}
          {onMap?.alert_zh != null && <div className="small">！{onMap.alert_zh}</div>}
        </div>
      </div>
      {here === undefined ? (
        <div className="muted small">{name}不在這裡。</div>
      ) : (
        <NpcPanel view={view} busy={busy} chats={chats} onAct={onAct} onChat={onChat} only={npc} />
      )}
    </div>
  );
}

export function HudHirePanel({ view, busy, onAct }: { view: WorldView; busy: boolean; onAct(action: WorldAction): void }) {
  const party = view.party;
  if (party == null) return <div className="muted small">這裡不能雇用隊友。</div>;
  const can = party.can_hire && (party.mercenaries ?? []).length > 0;
  return (
    <div className="world-hud-stack" data-testid="world-hud-hire">
      <PartyPanel party={party} />
      {can ? (
        <div className="panel">
          <div className="section-title">雇用隊友</div>
          <HireEditor party={party} busy={busy} onAct={onAct} />
        </div>
      ) : (
        <div className="muted small">現在不能換隊友{party.hire_problem_zh != null ? `：${party.hire_problem_zh}` : ""}</div>
      )}
    </div>
  );
}

export function FriendCard({ view, owner }: { view: WorldView; owner: string }) {
  const shadow = (view.party?.shadows ?? []).find((s) => s.owner === owner);
  const friend = (view.field?.friends ?? []).find((f) => f.owner === owner);
  const [chronicle, setChronicle] = useState<ChronicleView | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let alive = true;
    api
      .worldChronicle()
      .then((c) => {
        if (alive) setChronicle(c);
      })
      .catch(() => {
        if (alive) setFailed(true);
      });
    return () => {
      alive = false;
    };
  }, []);
  const name = shadow?.name_zh ?? friend?.name_zh ?? owner;
  const records = friendChronicle(chronicle, owner);
  return (
    <div className="panel field-friend-card" data-testid="world-hud-friend" data-owner={owner}>
      <div className="section-title">
        {name}的影子
        {shadow !== undefined && <AccountTitles titles={shadow.titles} />}
      </div>
      {shadow === undefined ? (
        <div className="muted small">Lv {friend?.level ?? "?"}（名片資料要在城裡才看得到）</div>
      ) : (
        <div className="field-friend-build small" data-testid="world-friend-build">
          <div>
            Lv {shadow.level}・{shadow.role_zh}・存在{shadow.saved_zh}
          </div>
          <div>技能：{shadow.skills_zh.join("、") || "（無）"}</div>
          {shadow.cap_zh != null && <div className="muted">{shadow.cap_zh}</div>}
          <div className="muted">要借他的影子：到酒館的「雇用」選「影子」。</div>
        </div>
      )}
      <div className="section-title small">編年史</div>
      {chronicle === null && !failed && <div className="muted small">讀取中……</div>}
      {failed && <div className="muted small">編年史讀不到。</div>}
      {chronicle !== null && records.length === 0 && <div className="muted small">還沒有紀錄。</div>}
      {records.length > 0 && (
        <ul className="small" data-testid="world-friend-chronicle">
          {records.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
