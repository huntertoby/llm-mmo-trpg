// 外觀步驟（Phase 6R-2，#137；docs/art/外觀變化方案.md 第 3 節）：建角的「名字 → 種族 → 外觀 → 出身」與主城改外觀共用。
// 一排一排點選（臉型、眼睛、髮型、鬍子、體型、獸耳、膚色、髮色、眼色、睫毛），各族不開放的值不出現；
// 快速組合「粗獷」「柔和」「隨機」「種族預設」只是一次設好幾項，之後每一項都能改，不存性別。
// 預覽用現有紙娃娃部件（玩法 PM 6R-1：「外觀選單先用現有部件可以」）：臉型、眼睛、睫毛、體型、獸耳花色、新髮型與鬍子樣式等 Q 版（QK-6）才畫出來，值照存。
import { useMemo, useState } from "react";
import type { DollLook, LookChoice } from "../api/types";
import { resolveDoll } from "../render/appearance";
import { renderFigureCanvas } from "../render/paperdoll";
import { BEARDS, BEAST_EARS, EYE_STYLES, FACES, FRAMES, HAIRS, LOOK_OPTIONS, PRESETS, applyPreset, lookForRace, randomLook, type RaceLookOptions } from "./lookOptions";

type Facing = "south" | "east" | "west" | "north";
const FACINGS: readonly [Facing, string][] = [["south", "正面"], ["east", "朝東"], ["west", "朝西"], ["north", "背面"]];

/** 純函式：一列的目前值（沒選＝種族預設）。 */
export function shownValue(key: keyof LookChoice, choice: LookChoice, opts: RaceLookOptions | undefined): unknown {
  const v = choice[key];
  if (v !== null && v !== undefined) return v;
  const race = opts?.raceLook ?? {};
  switch (key) {
    case "face":
      return "round";
    case "eye_style":
      return "square";
    case "lashes":
      return false;
    case "frame":
      return null;
    case "hair":
      return typeof race.hair === "string" ? race.hair : "none";
    case "beard":
      return race.beard === true ? "full" : "none";
    case "skin":
      return race.skin;
    case "hair_color":
      return race.hair_color;
    case "beast_ears":
      return race.beast_ears;
    default:
      return null;
  }
}

/** 純函式：點一個選項後的選擇（點到種族預設＝清掉那一項）。 */
export function pickValue(choice: LookChoice, key: keyof LookChoice, value: unknown): LookChoice {
  return { ...choice, [key]: value } as LookChoice;
}

interface RowProps {
  label: string;
  testId: string;
  items: readonly (readonly [unknown, string])[];
  current: unknown;
  swatch?: boolean;
  disabled: boolean;
  onPick(value: unknown): void;
}

function Row({ label, testId, items, current, swatch = false, disabled, onPick }: RowProps) {
  if (items.length <= 1 && !swatch) return null;
  if (items.length === 0) return null;
  return (
    <div className="look-row" data-testid={testId}>
      <span className="look-row-label">{label}</span>
      <span className="look-row-items">
        {items.map(([value, zh]) => (
          <button
            key={String(value)}
            type="button"
            className={`look-chip${swatch ? " look-swatch" : ""}${current === value ? " selected" : ""}`}
            style={swatch ? { background: String(value) } : undefined}
            aria-pressed={current === value}
            aria-label={swatch ? `${label} ${zh}` : undefined}
            disabled={disabled}
            onClick={() => onPick(value)}
          >
            {swatch ? "" : zh}
          </button>
        ))}
      </span>
    </div>
  );
}

interface Props {
  race: string;
  choice: LookChoice;
  onChoice(next: LookChoice): void;
  disabled?: boolean;
  /** 「隨機」的種子前綴（同一個前綴＋第幾次按＝同一組，純函式）。 */
  seed?: string;
}

/** 外觀選單；沒有種族（或種族沒有清單）時不顯示。 */
export function LookPicker({ race, choice, onChoice, disabled = false, seed = "look" }: Props) {
  const [rolls, setRolls] = useState(0);
  const opts = LOOK_OPTIONS[race];
  if (opts === undefined || race === "") return null;
  const set = (key: keyof LookChoice) => (value: unknown) => onChoice(pickValue(choice, key, value));
  const swatches = (list: readonly string[]): (readonly [string, string])[] => list.map((c, i) => [c, `第 ${i + 1} 色`] as const);
  return (
    <div className="look-picker" data-testid="look-picker">
      <div className="look-presets">
        <button type="button" disabled={disabled} onClick={() => onChoice(applyPreset(choice, PRESETS.rugged, opts))} data-testid="look-preset-rugged">
          粗獷
        </button>
        <button type="button" disabled={disabled} onClick={() => onChoice(applyPreset(choice, PRESETS.soft, opts))} data-testid="look-preset-soft">
          柔和
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => {
            onChoice(randomLook(`${seed}-${race}-${rolls}`, opts));
            setRolls((n) => n + 1);
          }}
          data-testid="look-preset-random"
        >
          隨機
        </button>
        <button type="button" disabled={disabled} onClick={() => onChoice({})} data-testid="look-preset-default">
          種族預設
        </button>
      </div>
      <Row label="臉型" testId="look-face" items={FACES} current={shownValue("face", choice, opts)} disabled={disabled} onPick={set("face")} />
      <Row label="眼睛" testId="look-eye-style" items={EYE_STYLES} current={shownValue("eye_style", choice, opts)} disabled={disabled} onPick={set("eye_style")} />
      <Row label="髮型" testId="look-hair" items={opts.hair.map((h) => [h, HAIRS[h] ?? h] as const)} current={shownValue("hair", choice, opts)} disabled={disabled} onPick={set("hair")} />
      <Row label="鬍子" testId="look-beard" items={opts.beard.map((b) => [b, BEARDS[b] ?? b] as const)} current={shownValue("beard", choice, opts)} disabled={disabled} onPick={set("beard")} />
      <Row label="體型" testId="look-frame" items={FRAMES} current={shownValue("frame", choice, opts)} disabled={disabled} onPick={set("frame")} />
      <Row label="獸耳" testId="look-ears" items={opts.beastEars.map((e) => [e, BEAST_EARS[e] ?? e] as const)} current={shownValue("beast_ears", choice, opts)} disabled={disabled} onPick={set("beast_ears")} />
      <Row label="膚色" testId="look-skin" items={swatches(opts.skin)} current={shownValue("skin", choice, opts)} swatch disabled={disabled} onPick={set("skin")} />
      {opts.hairColor.length > 0 && <Row label="髮色" testId="look-hair-color" items={swatches(opts.hairColor)} current={shownValue("hair_color", choice, opts)} swatch disabled={disabled} onPick={set("hair_color")} />}
      <Row label="眼色" testId="look-eyes" items={swatches(opts.eyes)} current={shownValue("eyes", choice, opts)} swatch disabled={disabled} onPick={set("eyes")} />
      <Row label="睫毛" testId="look-lashes" items={[[false, "無"], [true, "有"]]} current={shownValue("lashes", choice, opts)} disabled={disabled} onPick={set("lashes")} />
      <div className="muted small look-note">外觀只在畫面，不影響數值與技能；之後在主城可以隨時免費改。臉型、眼睛、睫毛、體型、獸耳花色與部分髮型、鬍子要等 Q 版人物上線才畫得出來，選了會先存著。</div>
    </div>
  );
}

/** 選中的種族換掉時：新種族也有的保留，沒有的清掉（同後端）。 */
export function lookAfterRace(choice: LookChoice, race: string): LookChoice {
  return lookForRace(choice, LOOK_OPTIONS[race]);
}

interface PreviewProps {
  race: string;
  choice: LookChoice;
  weaponId?: string | null;
  height?: number;
}

/** 預覽穿的衣服（同我方預設：布衣＋靴）；膚色、髮型由種族外觀與選擇蓋過。 */
const PREVIEW_DOLL: DollLook = {
  skin: "#f1c9a5",
  skull: false,
  beard: false,
  affixes: [],
  traits: [],
  gear: { body: { kind: "shirt", material: "cloth" }, feet: { kind: "boots", material: "leather" } },
};

/** 紙娃娃預覽（現有部件），可轉正面、朝東、朝西、背面。沒有 DOM 或畫不出來時只留文字。 */
export function LookPreview({ race, choice, weaponId = null, height = 220 }: PreviewProps) {
  const [facing, setFacing] = useState<Facing>("south");
  const opts = LOOK_OPTIONS[race];
  const src = useMemo(() => {
    if (opts === undefined) return null;
    const spec = resolveDoll({
      template: "hero",
      dollLook: { ...PREVIEW_DOLL, custom: choice },
      team: "ally",
      summon: false,
      weaponId,
      raceLook: opts.raceLook,
    });
    return renderFigureCanvas(spec, facing, false, 3)?.toDataURL() ?? null;
  }, [opts, choice, weaponId, facing]);
  if (opts === undefined) return <span className="muted small">先選種族</span>;
  return (
    <div className="look-preview" data-testid="look-preview">
      {src !== null ? <img src={src} height={height} alt="人物預覽" /> : <span className="muted small">人物預覽</span>}
      <span className="look-facings">
        {FACINGS.map(([f, zh]) => (
          <button key={f} type="button" className={`look-chip${facing === f ? " selected" : ""}`} aria-pressed={facing === f} onClick={() => setFacing(f)}>
            {zh}
          </button>
        ))}
      </span>
    </div>
  );
}
