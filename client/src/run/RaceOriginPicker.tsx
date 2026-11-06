// 開局第一步：種族與出身（Phase 3R-3a，設計文件 07 7.7）。種族卡顯示種族技與環境被動，出身卡顯示界域與簡介；
// 詳細說明用共用浮動卡（`useFloatCard`：滑過約 150ms 顯示、可移進卡片捲動、點一下釘住、Esc 關閉）。
// UI-E1b（docs/art/shots/misc/create-v2.png）：種族卡是「頭像位置＋名字＋發源」的格子卡，外框是發源區的區域色；選中的種族在格子右側的
// 展開欄列出名字、發源、一句簡介、種族技、環境被動、判定加值（「判定加值：交涉 +1」）。出身卡前面是五區紋章，配區域色，
// 下面一行短描述。頭像要等 Q 版，這裡只留位置、不畫人物。選項、送出的資料與流程照舊。
import type { CSSProperties, ReactNode } from "react";
import type { OriginOption, RaceOption, StartOptions } from "../api/types";
import { RegionCrest } from "../ui/CreateIcons";
import { Hint } from "../ui/Hint";
import { regionThemeFor } from "../ui/regionTheme";
import { FloatCard, useFloatCard } from "../ui/useFloatCard";
import { CREATE_TEXTS, raceCheckBonusHint, raceCheckBonusZh } from "./createTexts";
import { originCardLines, raceStartCardLines, type RaceOriginChoice } from "./raceOrigin";

interface Props {
  options: StartOptions | null;
  choice: RaceOriginChoice;
  onChoice(next: RaceOriginChoice): void;
  disabled?: boolean;
  /** 種族與出身之間的步驟（6R-2 大世界建角的「外觀」，#137：名字 → 種族 → 外觀 → 出身）；roguelite 不給。 */
  afterRace?: ReactNode;
}

/** 區域色（卡框、發源字、紋章）：區域主題的強調色。 */
export const realmColor = (realm: string): string => regionThemeFor(realm).accent;

/** 一張可選的卡：按鈕選取，滑過顯示浮動卡（觸控點一下開關）。 */
function PickCard({
  selected,
  disabled,
  onPick,
  testId,
  heading,
  lines,
  className,
  color,
  children,
}: {
  selected: boolean;
  disabled: boolean;
  onPick(): void;
  testId: string;
  heading: string;
  lines: readonly string[];
  className: string;
  color: string;
  children: ReactNode;
}) {
  const f = useFloatCard({ pinOn: "touch" });
  return (
    <div className="race-pick-slot" {...f.triggerProps}>
      <button
        type="button"
        className={`race-pick ${className}${selected ? " selected" : ""}`}
        style={{ "--realm": color } as CSSProperties}
        data-testid={testId}
        aria-pressed={selected}
        disabled={disabled}
        onClick={onPick}
      >
        {children}
      </button>
      {f.open && (
        <FloatCard float={f} className="skill-card-float float-panel race-pick-card">
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
    <PickCard
      selected={selected}
      disabled={disabled}
      onPick={onPick}
      testId={`race-${race.id}`}
      heading={race.name_zh}
      lines={raceStartCardLines(race)}
      className="race-tile"
      color={realmColor(race.home_realm)}
    >
      {/* 頭像位置：Q 版種族頭像完成後畫在這裡（這段不畫人物） */}
      <span className="race-tile-face" data-testid="race-face-slot" aria-hidden="true" />
      <b className="race-tile-name">{race.name_zh}</b>
      <span className="race-tile-realm">發源：{race.home_realm_name_zh}</span>
    </PickCard>
  );
}

function OriginCard({ origin, selected, disabled, onPick }: { origin: OriginOption; selected: boolean; disabled: boolean; onPick(): void }) {
  const tagline = CREATE_TEXTS.taglines[origin.id];
  return (
    <PickCard
      selected={selected}
      disabled={disabled}
      onPick={onPick}
      testId={`origin-${origin.id}`}
      heading={origin.name_zh}
      lines={originCardLines(origin)}
      className="origin-tile"
      color={realmColor(origin.realm)}
    >
      <RegionCrest region={origin.realm} size={30} />
      <span className="origin-tile-text">
        <b>{origin.realm_name_zh}</b>
        {tagline !== undefined && <span className="origin-tile-tag">{tagline}</span>}
      </span>
    </PickCard>
  );
}

/** 選中種族的右側展開欄：名字＋發源、一句簡介、種族技、環境被動、判定加值。 */
export function RaceDetail({ race }: { race: RaceOption | undefined }) {
  if (race === undefined) {
    return (
      <aside className="race-detail empty" data-testid="race-detail">
        <span className="muted small">選一個種族，這裡會列出種族技、環境被動與判定加值。</span>
      </aside>
    );
  }
  const blurb = CREATE_TEXTS.blurbs[race.id];
  const bonus = raceCheckBonusZh(race.id);
  return (
    <aside className="race-detail" style={{ "--realm": realmColor(race.home_realm) } as CSSProperties} data-testid="race-detail">
      <div className="race-detail-head">
        <span className="race-detail-name">{race.name_zh}</span>
        <span className="race-detail-realm">發源：{race.home_realm_name_zh}</span>
      </div>
      {blurb !== undefined && <div className="race-detail-blurb">{blurb}</div>}
      <div className="race-detail-label">種族技（每場 {race.skill_uses} 次・{race.skill_ap} AP・不佔技能欄）</div>
      <div className="race-detail-item">
        <b>{race.skill_name_zh}</b>
        <span>{race.skill_description_zh}</span>
      </div>
      <div className="race-detail-label">環境被動</div>
      <div className="race-detail-item">
        <b>{race.passive_name_zh}</b>
        <span>{race.passive_description_zh}</span>
      </div>
      {bonus !== null && (
        <div className="race-detail-bonus-row">
          <Hint text={raceCheckBonusHint()}>
            <span className="race-detail-bonus" tabIndex={0} data-testid="race-check-bonus">
              判定加值：{bonus}
            </span>
          </Hint>
        </div>
      )}
    </aside>
  );
}

/** 種族卡格子＋右側展開欄、出身卡列；沒有種族資料的後端不顯示。 */
export function RaceOriginPicker({ options, choice, onChoice, disabled = false, afterRace }: Props) {
  const races = options?.races ?? [];
  const origins = options?.origins ?? [];
  if (races.length === 0 || origins.length === 0) return null;
  const chosen = races.find((r) => r.id === choice.race);
  const chosenOrigin = origins.find((o) => o.id === choice.origin);
  return (
    <>
      {/* UI-E1：種族、出身分成兩個步驟標題（入口畫面的步驟列）；選項、說明文字與資料照舊 */}
      <div className="section-title">種族</div>
      <div className="muted small">種族給 1 招種族技（不佔技能欄）與 1 項環境被動，不加任何傷害或屬性；出身只影響外觀與劇情，不影響戰鬥。</div>
      <div className="race-pick-area">
        <div className="race-pick-grid" data-testid="start-races">
          {races.map((r) => (
            <RaceCard key={r.id} race={r} selected={choice.race === r.id} disabled={disabled} onPick={() => onChoice({ ...choice, race: r.id })} />
          ))}
        </div>
        <RaceDetail race={chosen} />
      </div>
      {afterRace}
      <div className="section-title">出身</div>
      <div className="origin-pick-list" data-testid="start-origins">
        {origins.map((o) => (
          <OriginCard key={o.id} origin={o} selected={choice.origin === o.id} disabled={disabled} onPick={() => onChoice({ ...choice, origin: o.id })} />
        ))}
      </div>
      <div className="muted small origin-pick-note" data-testid="origin-detail">
        {chosenOrigin === undefined ? "出身決定預設外觀、開場劇情與 NPC 態度，不影響戰鬥。" : `${chosenOrigin.name_zh}：${chosenOrigin.description_zh}`}
      </div>
    </>
  );
}
