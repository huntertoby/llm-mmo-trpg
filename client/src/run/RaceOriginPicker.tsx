// 開局第一步：種族與出身（Phase 3R-3a，設計文件 07 7.7）。種族卡顯示種族技與環境被動，出身卡顯示界域與簡介；
// 詳細說明用共用浮動卡（`useFloatCard`：滑過約 150ms 顯示、可移進卡片捲動、點一下釘住、Esc 關閉），選中的種族下方另列全文。
import type { ReactNode } from "react";
import type { OriginOption, RaceOption, StartOptions } from "../api/types";
import { FloatCard, useFloatCard } from "../ui/useFloatCard";
import { originCardLines, raceStartCardLines, raceSummary, type RaceOriginChoice } from "./raceOrigin";

interface Props {
  options: StartOptions | null;
  choice: RaceOriginChoice;
  onChoice(next: RaceOriginChoice): void;
  disabled?: boolean;
}

/** 一張可選的卡：按鈕選取，滑過顯示浮動卡（觸控點一下開關）。 */
function PickCard({
  selected,
  disabled,
  onPick,
  testId,
  heading,
  lines,
  children,
}: {
  selected: boolean;
  disabled: boolean;
  onPick(): void;
  testId: string;
  heading: string;
  lines: readonly string[];
  children: ReactNode;
}) {
  const f = useFloatCard({ pinOn: "touch" });
  return (
    <div className="race-pick-slot" {...f.triggerProps}>
      <button type="button" className={`race-pick${selected ? " primary selected" : ""}`} data-testid={testId} aria-pressed={selected} disabled={disabled} onClick={onPick}>
        {children}
      </button>
      {f.open && (
        <FloatCard float={f} className="skill-card-float race-pick-card">
          <div className="section-title">{heading}</div>
          {lines.map((line) => (
            <div key={line} className="small">
              {line}
            </div>
          ))}
        </FloatCard>
      )}
    </div>
  );
}

function RaceCard({ race, selected, disabled, onPick }: { race: RaceOption; selected: boolean; disabled: boolean; onPick(): void }) {
  return (
    <PickCard selected={selected} disabled={disabled} onPick={onPick} testId={`race-${race.id}`} heading={race.name_zh} lines={raceStartCardLines(race)}>
      <b>{race.name_zh}</b>
      <span className="small race-pick-sub">{raceSummary(race)}</span>
    </PickCard>
  );
}

function OriginCard({ origin, selected, disabled, onPick }: { origin: OriginOption; selected: boolean; disabled: boolean; onPick(): void }) {
  return (
    <PickCard selected={selected} disabled={disabled} onPick={onPick} testId={`origin-${origin.id}`} heading={origin.name_zh} lines={originCardLines(origin)}>
      <b>{origin.name_zh}</b>
      <span className="small race-pick-sub">{origin.realm_name_zh}</span>
    </PickCard>
  );
}

/** 種族卡列＋出身卡列；沒有種族資料的後端不顯示。 */
export function RaceOriginPicker({ options, choice, onChoice, disabled = false }: Props) {
  const races = options?.races ?? [];
  const origins = options?.origins ?? [];
  if (races.length === 0 || origins.length === 0) return null;
  const chosen = races.find((r) => r.id === choice.race);
  const chosenOrigin = origins.find((o) => o.id === choice.origin);
  return (
    <>
      <div className="section-title">種族與出身</div>
      <div className="muted small">種族給 1 招種族技（不佔技能欄）與 1 項環境被動，不加任何傷害或屬性；出身只影響外觀與劇情，不影響戰鬥。</div>
      <div className="race-pick-list" data-testid="start-races">
        {races.map((r) => (
          <RaceCard key={r.id} race={r} selected={choice.race === r.id} disabled={disabled} onPick={() => onChoice({ ...choice, race: r.id })} />
        ))}
      </div>
      <div className="race-pick-list" data-testid="start-origins">
        {origins.map((o) => (
          <OriginCard key={o.id} origin={o} selected={choice.origin === o.id} disabled={disabled} onPick={() => onChoice({ ...choice, origin: o.id })} />
        ))}
      </div>
      <div className="race-pick-detail small" data-testid="race-detail">
        {chosen === undefined ? (
          <span className="muted">請選一個種族與一個出身。</span>
        ) : (
          <>
            {raceStartCardLines(chosen).map((line) => (
              <div key={line}>{line}</div>
            ))}
            {chosenOrigin !== undefined && (
              <div className="muted">
                {chosenOrigin.name_zh}（{chosenOrigin.realm_name_zh}）：{chosenOrigin.description_zh}
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}
