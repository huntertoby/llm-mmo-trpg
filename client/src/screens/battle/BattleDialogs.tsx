// 戰鬥畫面的對話框（由 BattleScreen 抽出，Phase 3T-7）：複合技能第二段、灌注關鍵字、複製技能、反應詢問。
// 條件與屬性與原本逐字相同；全部走共用的 `DialogFrame`（浮動卡規則 6.5.1）。

import type { Action, BattleResponse, Pos, UnitView } from "../../api/types";
import type { DrawModel } from "../../battle/drawModel";
import type { infusionChoices } from "../../battle/infusion";
import { ruleOfPending, triggerEventText } from "../../battle/reactions";
import { dialogStartsLow } from "../../battle/stageLayout";
import type { UnitNames } from "../../battle/units";
import { CopyDialog } from "../../ui/CopyDialog";
import { DecisionDialog } from "../../ui/DecisionDialog";
import { FollowupDialog } from "../../ui/FollowupDialog";
import { InfusionDialog } from "../../ui/InfusionDialog";

interface Props {
  response: BattleResponse;
  hero: UnitView | null;
  busy: boolean;
  copying: boolean;
  copyPaused: boolean;
  followPaused: boolean;
  copyName: string;
  skillNames: Readonly<Record<string, string>>;
  liveNames: UnitNames;
  focusTile: Pos | null;
  model: DrawModel;
  infusionPick: Action | null;
  infusionOptions: ReturnType<typeof infusionChoices>;
  onCancelInfusion(): void;
  /** 灌注關鍵字選好：送出帶灌注的動作。 */
  onPickInfusion(action: Action, keywordId: string): void;
  onDecideCopy(pick: Action | null): void;
  onDecide(accept: boolean, always: boolean): void;
}

export function BattleDialogs(p: Props) {
  const { response, hero, busy } = p;
  const { infusionPick } = p;
  return (
    <>
      {p.followPaused && response.pending !== null && (
        <FollowupDialog
          skillName={p.copyName}
          optionCount={(response.followup_options ?? []).length}
          enabled={!busy}
          onCancel={() => p.onDecideCopy(null)}
        />
      )}
      {infusionPick !== null && infusionPick.type === "use_skill" && p.infusionOptions.length > 0 && !busy && (
        <InfusionDialog
          skillName={p.skillNames[infusionPick.skill_id] ?? infusionPick.skill_id}
          options={p.infusionOptions}
          enabled={!busy}
          onPick={(id) => p.onPickInfusion(infusionPick, id)}
          onCancel={p.onCancelInfusion}
        />
      )}
      {p.copyPaused && response.pending !== null && (
        <CopyDialog
          skillName={p.copyName}
          optionCount={response.copy_options.length}
          enabled={!busy}
          onCancel={() => p.onDecideCopy(null)}
        />
      )}
      {response.awaiting === "decision" && response.pending !== null && !busy && !p.copying && (
        <DecisionDialog
          key={`${response.pending.reaction ?? ""}:${response.pending.trigger_unit_id ?? ""}`}
          startLow={dialogStartsLow(p.focusTile, p.model)}
          pending={response.pending}
          rule={ruleOfPending(hero, response.pending)}
          names={p.liveNames}
          eventText={triggerEventText(response)}
          enabled={!busy}
          onDecide={p.onDecide}
        />
      )}
    </>
  );
}
