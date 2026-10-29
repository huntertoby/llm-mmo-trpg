// 營火畫面：HP、法力、耐力已回滿（源力 +1）；可以換技能、換裝備、免費重配屬性點，之後離開。
// Phase 3W-6：靈感閃現、重閃、溶掉、傳承（`FlashSection`、`CampfireSkillCare`）。
import type { RunChoice, RunResponse } from "../api/types";
import type { RunView } from "../run/flow";
import { AttributeRespecSection } from "../run/AttributeRespecSection";
import { BackpackSection } from "../run/BackpackSection";
import { CampfireSkillCare } from "../run/CampfireSkillCare";
import { FlashSection } from "../run/FlashSection";
import { LoadoutEditor } from "../run/LoadoutEditor";
import { loadoutChoice } from "../run/loadout";

type Props = {
  run: RunResponse;
  view: Extract<RunView, { screen: "campfire" }>;
  busy: boolean;
  onChoose(choice: RunChoice): Promise<number | null>;
};

export function RunCampfire({ run, view, busy, onChoose }: Props) {
  return (
    <div className="panel run-campfire">
      <h2>營火（第 {view.afterBattle} 場後）</h2>
      <p>HP、法力與耐力已回滿，源力 +1。</p>
      <FlashSection runId={run.run_id} hero={run.hero} busy={busy} onChoose={onChoose} />
      <CampfireSkillCare runId={run.run_id} hero={run.hero} busy={busy} onChoose={onChoose} />
      <div className="panel run-skill-points">
        <LoadoutEditor
          key={[...run.hero.skills, ...(run.hero.bench ?? [])].map((s) => s.id).join(",")}
          hero={run.hero}
          disabled={busy}
          onApply={(ids) => void onChoose(loadoutChoice(ids))}
        />
      </div>
      <AttributeRespecSection hero={run.hero} busy={busy} onChoose={onChoose} campfire runId={run.run_id} />
      <BackpackSection hero={run.hero} busy={busy} onChoose={onChoose} />
      <div className="run-actions">
        <button type="button" className="primary" disabled={busy} onClick={() => void onChoose({ kind: "leave" })}>
          離開營火
        </button>
      </div>
    </div>
  );
}
