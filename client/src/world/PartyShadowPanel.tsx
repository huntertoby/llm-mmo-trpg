// 「隊伍與影子」面板（PNL-1a；docs/art/資訊面板-移植需求.md 3.3，樣張 infoPanelsTabs.js 的 `P`／`P_TABS`）：HUD 功能列「影子（Y）」打開的面板。
// 固定區：標題「隊伍與影子」＋「回到地點圖」（「×」是 WorldHud 的正式關閉鈕）＋分頁列（隊伍｜我的影子）。
// - 隊伍：第一行「主角＋最多 N 名」；成員卡（頭像 44、名字＋亮金「Lv N」、身分、「打法 …」、OB-8 來歷行）；主角金框、劇情夥伴綠框＋綠底標籤；
//   面板 < 560 時兩欄、第 3 張撐滿（容器查詢，world-hud.css）；下面劇情夥伴說明（資訊）、獨行（資訊）、賽季頭目限制與換隊友原因（鎖住）。
// - 我的影子：還沒存時琥珀標籤＋一行小字；兩格數值（預設打法、被借用得到的任務幣）；戰報或虛線空狀態。
// 字全部照伺服器（`PartyView`、`MyShadowView`）；新字在 `partyShadow.ts`。雇用面板與舊側欄仍用 `PartyPanel.tsx` 的精簡清單（不在本段）。
import type { WorldAction, WorldAiChoice, WorldMyShadow, WorldPartyView, WorldView } from "../api/types";
import { fieldHeroInput, HeroFace } from "../ui/heroFace";
import { Callout, EmptyNote, HudBare, PanelHead, TabLine, Tag, TokenGlyph, WarnGlyph } from "../ui/PanelKit";
import { PanelTabs, type PanelTabDef } from "../ui/PanelTabs";
import {
  COMPANION_TAG_ZH,
  memberAiText,
  memberKind,
  memberNote,
  PARTY_PANEL_TITLE_ZH,
  PARTY_TAB_ZH,
  partyCountBadge,
  SHADOW_UNSAVED_NOTE_ZH,
  SHADOW_UNSAVED_ZH,
  shadowBadge,
  SOLO_ZH,
} from "./partyShadow";
import { Portrait } from "./StoryIcons";

/** 隊友卡頭像（樣張 44）。 */
export const MEMBER_FACE = 44;

function MemberFace({ view, party, index }: { view: WorldView; party: WorldPartyView; index: number }) {
  const m = party.members[index]!;
  const kind = memberKind(m, index);
  if (kind === "hero") {
    /* 主角頭像＝HUD 主角卡同一張（美術 PM 定） */
    const input = fieldHeroInput(view.character.hero_look ?? view.field?.hero);
    if (input !== null) return <HeroFace input={input} realm={view.character.origin_realm ?? null} size={MEMBER_FACE} label={m.name_zh} />;
  }
  const merc = m.mercenary != null ? (party.mercenaries ?? []).find((x) => x.id === m.mercenary) : undefined;
  /* 同 HUD 隊友小卡（hud.ts mateCards）：傭兵用名單上的頭像與出身區；劇情夥伴用伺服器給的人設卡頭像與區（PNL-4）；
     其他用通用剪影、傭兵金框 */
  return <Portrait portrait={merc?.portrait ?? m.portrait ?? null} region={merc?.origin ?? m.region ?? "merc"} size={MEMBER_FACE} label={m.name_zh} />;
}

export function PartyPane({ view, party }: { view: WorldView; party: WorldPartyView }) {
  return (
    <div className="world-party" data-testid="world-party">
      <TabLine>
        <span>主角＋最多 {party.max_hired} 名</span>
      </TabLine>
      <div className="pnl-members" data-testid="world-party-members">
        {party.members.map((m, i) => {
          const kind = memberKind(m, i);
          const ai = memberAiText(m);
          const note = memberNote(m);
          const cls = kind === "hero" ? "pnl-member hero" : kind === "companion" ? "pnl-member comp" : "pnl-member";
          return (
            <div key={i} className={cls} data-member={kind}>
              <span className="face">
                <MemberFace view={view} party={party} index={i} />
              </span>
              <div className="info">
                <span className="nm">
                  {m.name_zh}
                  <span className="lvl">Lv {m.level}</span>
                  {kind === "companion" && <Tag tone="live">{COMPANION_TAG_ZH}</Tag>}
                </span>
                <span className="role">{m.title_zh}</span>
                {ai !== null && (
                  <span className="ai">
                    打法 <b>{ai}</b>
                  </span>
                )}
                {note !== null && <span className="pnl-l3">{note}</span>}
                {m.backstory_zh != null && m.backstory_zh !== "" && (
                  <span className="story world-party-backstory" data-testid="world-party-backstory">
                    {m.backstory_zh}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
      {party.companion_zh != null && (
        <Callout tone="info" testId="world-party-companion">
          {party.companion_zh}
        </Callout>
      )}
      {party.members.length === 1 && (
        <Callout tone="info" testId="world-party-solo">
          <b>獨行</b>：{SOLO_ZH}
        </Callout>
      )}
      {party.season_boss_zh != null && (
        <Callout tone="lock" testId="world-party-boss">
          {party.season_boss_zh}
        </Callout>
      )}
      {!party.can_hire && party.hire_problem_zh !== null && (
        <Callout tone="lock" testId="world-party-hire">
          <b>換隊友</b>：{party.hire_problem_zh}
        </Callout>
      )}
    </div>
  );
}

export function ShadowPane({
  shadow,
  choices,
  busy,
  onAct,
}: {
  shadow: WorldMyShadow;
  choices: readonly WorldAiChoice[];
  busy: boolean;
  onAct(action: WorldAction): void;
}) {
  const reports = shadow.reports_zh ?? [];
  return (
    <div className="world-my-shadow" data-testid="world-my-shadow">
      <TabLine testId="world-shadow-state">
        {shadow.saved ? (
          <span className="pnl-l2">{shadow.saved_zh}</span>
        ) : (
          <>
            <Tag tone="warn" icon={<WarnGlyph px={13} />}>
              {SHADOW_UNSAVED_ZH}
            </Tag>
            <span className="pnl-l3">{SHADOW_UNSAVED_NOTE_ZH}</span>
          </>
        )}
      </TabLine>
      <div className="pnl-stats">
        <div className="pnl-stat">
          <span className="k">預設打法</span>
          <span className="v">
            {shadow.can_set_ai === true && choices.length > 0 ? (
              <select
                value={shadow.ai ?? ""}
                disabled={busy}
                aria-label="預設打法"
                onChange={(e) => onAct({ kind: "shadow_ai", profile: e.target.value === "" ? null : e.target.value })}
                data-testid="world-shadow-ai"
              >
                <option value="">預設</option>
                {choices.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name_zh}
                  </option>
                ))}
              </select>
            ) : (
              <span>{shadow.ai_zh}</span>
            )}
          </span>
        </div>
        <div className="pnl-stat">
          <span className="k">被借用得到的任務幣</span>
          <span className="v" data-testid="world-shadow-coins">
            <TokenGlyph px={15} />
            <b>{shadow.coins ?? 0}</b>
          </span>
        </div>
      </div>
      {reports.length === 0 ? (
        <EmptyNote>還沒有人借過你的影子。</EmptyNote>
      ) : (
        <ul className="pnl-rows pnl-reports" data-testid="world-shadow-reports">
          {reports.map((line, i) => (
            <li key={i} className="pnl-row">
              {line}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** 分頁定義（隊伍｜我的影子）；資料沒有的那一頁不放。 */
export function partyShadowTabs(view: WorldView, busy: boolean, onAct: (action: WorldAction) => void): PanelTabDef[] {
  const tabs: PanelTabDef[] = [];
  const party = view.party;
  const shadow = view.my_shadow;
  if (party != null) {
    tabs.push({
      id: "party",
      label: PARTY_TAB_ZH.party,
      short: PARTY_TAB_ZH.party,
      icon: <HudBare id="t_orders" px={16} />,
      badge: partyCountBadge(party),
      render: () => <PartyPane view={view} party={party} />,
    });
  }
  if (shadow != null) {
    tabs.push({
      id: "shadow",
      label: PARTY_TAB_ZH.shadow,
      short: PARTY_TAB_ZH.shadowShort,
      icon: <HudBare id="bar_Y" px={16} />,
      badge: shadowBadge(shadow),
      render: () => <ShadowPane shadow={shadow} choices={party?.ai_choices ?? []} busy={busy} onAct={onAct} />,
    });
  }
  return tabs;
}

export function PartyShadowPanel({ view, busy, onAct, onClose }: { view: WorldView; busy: boolean; onAct(action: WorldAction): void; onClose?: () => void }) {
  const tabs = partyShadowTabs(view, busy, onAct);
  if (tabs.length === 0) return null;
  return (
    <div className="world-hud-stack" data-testid="world-hud-shadow">
      <PanelTabs tabs={tabs} head={<PanelHead heading={PARTY_PANEL_TITLE_ZH} onBack={onClose} testId="world-party-head" />} testId="world-party-tabs" />
    </div>
  );
}
