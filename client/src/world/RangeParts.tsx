// 工坊靶場兩個模式（選大類、正式選定）共用的小塊（OB-5，#150；樣張 docs/art/OB與PR樣張.md 第 1、2 節）：
// 說話的人（Q 版頭像＋台詞）、武器架（近戰／遠程／法器三排武器鈕）、武器卡。
import type { ReactNode } from "react";
import type { RangeView, StartWeaponOption } from "../api/types";
import { Hint } from "../ui/Hint";
import { WeaponIcon } from "../ui/WeaponIcon";
import { Portrait } from "./StoryIcons";
import { CLASS_LABELS, SANDBOX_NOTE, type Rack } from "./range";

type Speaker = NonNullable<RangeView["keeper"]>;
interface Line {
  speaker_zh: string;
  text_zh: string;
}

/** 窄版（手機寬）頭像縮成 48，其餘 64（樣張第 1.2 節）；沒有視窗時用 64。 */
export function speakerPortraitSize(viewportWidth: number | null): number {
  return viewportWidth !== null && viewportWidth <= 560 ? 48 : 64;
}

interface SpeakerProps {
  speaker: Speaker | null | undefined;
  lines: readonly Line[];
  /** 選了之後才多說的話（淡金色）。 */
  extra?: readonly Line[];
  testId?: string;
}

/** 守印人、葛蘭說話的那一塊：左邊 Q 版頭像，右邊台詞；下面一行沙盒說明。 */
export function RangeSpeaker({ speaker, lines, extra = [], testId }: SpeakerProps) {
  const size = speakerPortraitSize(typeof window === "undefined" ? null : window.innerWidth);
  return (
    <>
      <div className="ob-speaker" data-testid={testId}>
        {speaker != null && (
          <span className="ob-portrait" data-testid="range-speaker-portrait" data-speaker={speaker.name_zh}>
            <Portrait portrait={speaker.portrait ?? null} region={speaker.region ?? null} size={size} label={speaker.name_zh} />
          </span>
        )}
        <div className="ob-speaker-text">
          {lines.map((line, i) => (
            <p key={i} className="world-opening-line">
              <b>{line.speaker_zh}</b>：{line.text_zh}
            </p>
          ))}
          {extra.map((line, i) => (
            <p key={`x${i}`} className="world-opening-line ob-new" data-testid="range-speaker-extra">
              <b>{line.speaker_zh}</b>：{line.text_zh}
            </p>
          ))}
        </div>
      </div>
      <p className="muted small range-sandbox-note" data-testid="range-sandbox-note">
        {SANDBOX_NOTE}
      </p>
    </>
  );
}

interface RackProps {
  racks: readonly Rack[];
  weapon: string;
  busy: boolean;
  onPick(id: string): void;
}

/** 武器架：三類各一排武器鈕（米色圓章小圖＋名字）；`weapon`＝亮起的那一把。 */
export function RangeRackList({ racks, weapon, busy, onPick }: RackProps) {
  return (
    <>
      {racks.map((rack) => (
        <div key={rack.weaponClass} className="range-rack" data-rack={rack.weaponClass}>
          <div className="range-rack-name small">{rack.name}</div>
          <div className="run-weapon-list">
            {rack.weapons.map((w) => (
              <Hint key={w.id} text={w.traits_zh.join("\n")}>
                <button type="button" className={`run-weapon${weapon === w.id ? " primary selected" : ""}`} disabled={busy} onClick={() => onPick(w.id)} data-testid={`range-weapon-${w.id}`}>
                  <WeaponIcon weaponId={w.id} weaponClass={w.weapon_class} size={20} />
                  {w.name_zh}
                </button>
              </Hint>
            ))}
          </div>
        </div>
      ))}
    </>
  );
}

interface CardProps {
  weapon: StartWeaponOption;
  /** 第一行名字後面要不要寫 HP 與法力（正式選定寫，選大類不寫）。 */
  stats: boolean;
  /** 「試打用…」那一行。 */
  note: string | null;
  children?: ReactNode;
}

/** 武器卡：名字、大類、特性、「試打用…」一行，下面放「拿起試打」（由呼叫端給）。 */
export function RangeWeaponCard({ weapon, stats, note, children }: CardProps) {
  const cls = CLASS_LABELS[weapon.weapon_class] ?? weapon.weapon_class;
  return (
    <div className="range-weapon-card" data-testid="range-weapon-card">
      <div>
        <b>{weapon.name_zh}</b>
        <span className="muted small">　{stats ? `${cls}・HP ${weapon.hp}・法力 ${weapon.mana}` : cls}</span>
      </div>
      {stats && weapon.traits_zh.length > 0 && <div className="small">{weapon.traits_zh.join("；")}</div>}
      {note !== null && (
        <div className="small muted" data-testid="range-trial-note">
          {note}
        </div>
      )}
      {children}
    </div>
  );
}
