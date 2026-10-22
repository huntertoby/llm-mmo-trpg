// 戰前與營火的技能點區塊（Phase 3-26a）：自己管分配草稿，按「確認分配」才送出（不推進節點）；
// 營火另有免費重配與換裝。升級畫面的草稿跟著升級選擇一起送出，直接用 SkillGrowthPanel。
import { useState } from "react";
import type { RunChoice, RunHero } from "../api/types";
import { LoadoutEditor } from "./LoadoutEditor";
import { SkillGrowthPanel } from "./SkillGrowthPanel";
import { draftEvolve, loadoutChoice, spendChoice, type EvolveDraft, type LevelDraft } from "./skillGrowth";

interface Props {
  hero: RunHero;
  busy: boolean;
  /** 送出選擇；回傳失敗時的 HTTP 狀態（成功為 `null`）。 */
  onChoose(choice: RunChoice): Promise<number | null>;
  /** 營火：多了免費重配與換裝。 */
  campfire?: boolean;
}

export function SkillPointsSection({ hero, busy, onChoose, campfire = false }: Props) {
  const [draft, setDraft] = useState<LevelDraft>({});
  const [evolve, setEvolve] = useState<EvolveDraft>({});

  async function send(choice: RunChoice) {
    const status = await onChoose(choice);
    if (status === null) {
      setDraft({});
      setEvolve({});
    }
  }

  return (
    <div className="panel run-skill-points">
      <SkillGrowthPanel
        hero={hero}
        draft={draft}
        onDraft={setDraft}
        evolve={evolve}
        onEvolve={setEvolve}
        disabled={busy}
        onConfirm={() => void send(spendChoice(draft, draftEvolve(hero, draft, evolve)))}
        onRespec={campfire ? () => void send({ kind: "respec" }) : undefined}
      />
      {campfire && (
        <LoadoutEditor
          key={[...hero.skills, ...(hero.bench ?? [])].map((s) => s.id).join(",")}
          hero={hero}
          disabled={busy}
          onApply={(ids) => void send(loadoutChoice(ids))}
        />
      )}
    </div>
  );
}
