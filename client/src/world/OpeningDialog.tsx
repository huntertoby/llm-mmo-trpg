// 開局在主城的開場（Phase 6F-2；09 9.6.9 #125）：新角色在主城醒來時跳一則，說書人一句、守印人一句，下面接任務提示
// 「到霧渡鎮找渡婆婆」。文字由伺服器的 `WorldView.guide.opening` 給（模型關閉時的模板文字）。
// 6F-4（6F-2b）：看過了改記在角色身上（`WorldView.hints.seen` 的 `opening`；關掉時送 `hint_seen`），不用本機儲存。
// 沿用詢問視窗外框（DialogFrame，浮動卡規則 6.5.1 的共用元件，不另做彈出層）。
// RT-5：主城開場改成四格分鏡。① 醒來＝`AwakenDialog`（`awaken` 插圖＋說書人卡、只有「站起來」）；守印人那句改成他頭上的
// 對話泡泡（`world/opening.ts` 的 `splitOpening`），不在這裡。地圖上沒有守印人（例如沒有實地地圖）時照舊用 `OpeningDialog`。
import { useEffect, useRef, useState } from "react";
import type { AttributeAffects, WorldGuide, WorldLesson, WorldLevelUp, WorldOpeningLine } from "../api/types";
import type { DollSpec } from "../render/appearance";
import { AWAKEN_ART, AWAKEN_H, AWAKEN_LIE_MS, AWAKEN_W, drawAwakenArt, type AwakenPose } from "../render/eventArt";
import { NARRATOR_PORTRAIT } from "../render/portrait";
import { devAnimFactor } from "../battle/playback";
import { reducedMotion } from "../ui/motionPrefs";
import { FALLBACK_THEME } from "../ui/regionTheme";
import { Portrait } from "./StoryIcons";
import { DialogFrame } from "../ui/DialogFrame";
import { Hint } from "../ui/Hint";
import { ATTR_ZH } from "./narration";
import { OPENING_SEEN } from "./battleHints";

/** 這個角色現在要不要跳開場：伺服器有給開場、角色的提示紀錄裡還沒有 `opening`。 */
export function shouldShowOpening(guide: WorldGuide | null | undefined, seen: ReadonlySet<string> | boolean): guide is WorldGuide {
  const done = typeof seen === "boolean" ? seen : seen.has(OPENING_SEEN);
  return guide != null && (guide.opening ?? []).length > 0 && !done;
}

// ---------------- 閃現教學（6F-2，#132）與配點教學（6F-4，#133） ----------------
// 新手第 1 步完成升到 2 級、回到霧渡鎮：導師堂的葛蘭先教配點（`allocate`），教完或略過之後才接第一次閃現
// （`flash`：說書人一句、葛蘭一句，引導打開成長面板閃現一招在渡口用過的技能）；升到 3 級、閃過之後改教重閃。
// 伺服器只在還沒看過時給（看過記在角色的 `hints.seen`：`lesson:<種類>`）；可以略過。

const LESSON_TITLE: Record<WorldLesson["kind"], string> = { allocate: "配點", flash: "靈光一閃", reflash: "重閃", choose: "正式選定" };

interface LessonProps {
  lesson: WorldLesson;
  /** 上一段教學結束時導師說的話（配點教完接閃現時：「好。接下來看看你剛才用過的那一招。」）。 */
  lead?: { speaker_zh: string; text_zh: string } | null;
  onOpen(): void;
  onSkip(): void;
}

export function LessonDialog({ lesson, lead, onOpen, onSkip }: LessonProps) {
  const skills = lesson.skills_zh ?? [];
  return (
    <DialogFrame label="閃現教學" title={LESSON_TITLE[lesson.kind]}>
      <div className="world-opening" data-testid="world-lesson" data-kind={lesson.kind}>
        {lead != null && (
          <p className="world-opening-line" data-testid="world-lesson-lead">
            <b>{lead.speaker_zh}</b>：{lead.text_zh}
          </p>
        )}
        {lesson.lines.map((line, i) => (
          <p key={i} className="world-opening-line">
            <b>{line.speaker_zh}</b>：{line.text_zh}
          </p>
        ))}
        {skills.length > 0 && (
          <p className="world-opening-quest small">
            {lesson.kind === "flash" ? "剛用過、可以閃現的招：" : "閃過的招："}
            {skills.join("、")}
          </p>
        )}
        <p className="muted small">
          {lesson.kind === "flash"
            ? "在成長面板（G）選一招、花 1 點靈感，看 4 個變化選 1 個。略過也沒關係，之後在城鎮或營火隨時能閃。"
            : "在成長面板（G）的招式卡上選「重閃」。略過也沒關係，之後在城鎮或營火隨時能做。"}
        </p>
      </div>
      <div className="modal-buttons">
        <button type="button" className="primary" onClick={onOpen} data-testid="world-lesson-open">
          打開成長面板（G）
        </button>
        <button type="button" onClick={onSkip} data-testid="world-lesson-skip">
          略過
        </button>
      </div>
    </DialogFrame>
  );
}

const ATTR_ORDER = ["str", "dex", "con", "int", "wis", "wil"] as const;

/** 推薦配法的範例（07 7.2）：兩招看智力和力量時，開局各 2 點，升級的 2 點給比較低的、一樣高給第 1 招。 */
export const ALLOCATE_EXAMPLE_ZH =
  "例：兩招看智力和力量 → 開局 4 點各給 2 點（智力 12、力量 12）；升級的 2 點給比較低的那個，一樣高就給第 1 招的 → 智力 14、力量 12。";

/** 配點教學一個屬性滑過時的說明：第 1 行「你的技能：…」（沒有吃這個屬性的招就不顯示），第 2 行白話說明。 */
export function attributeNoteText(attr: string, note: string, affects: readonly AttributeAffects[]): string {
  const lines = affects.find((a) => a.attr === attr)?.lines_zh ?? [];
  return lines.length > 0 ? `你的技能：${lines.join("、")}\n${note}` : note;
}

interface AllocateProps {
  lesson: WorldLesson;
  affects: readonly AttributeAffects[];
  busy?: boolean;
  /** 按「推薦配法」：照 `lesson.recommended` 配好。 */
  onRecommended(): void;
  /** 按「自己配」：打開成長面板。 */
  onSelf(): void;
  /** 按「之後再說」。 */
  onSkip(): void;
}

/** 配點教學裡「共幾點」那一句。正式選定之後（`respec`，OB-3／OB-5）：全部點數已經照推薦配好，教的是重配再自己分。 */
export function allocateTotalText(lesson: Pick<WorldLesson, "points" | "start_points" | "respec">): string {
  const points = lesson.points ?? 0;
  if (lesson.respec === true) return `你的 ${points} 點已經全部照推薦配好；想自己分，就到成長面板按「重配」再分。`;
  const start = lesson.start_points ?? 0;
  return `開局的 ${start} 點已經照推薦配好，加上這次升級的 ${points} 點，共 ${start + points} 點。`;
}

/** 配點教學關掉時要記的紀錄（`hints.seen` 的 ID；OB-3 的約定）：一般＝`lesson:allocate`；正式選定之後的那種（`respec`）
 * 按「之後再說」只記 `lesson:allocate_skip`（之後換過地點、第一次進城鎮或營火會再提示一次）；再提示（`reminder`）出過就記
 * `lesson:allocate_again`。 */
export function allocateSeenIds(lesson: Pick<WorldLesson, "respec" | "reminder">, how: "recommended" | "self" | "skip"): string[] {
  const ids: string[] = [];
  if (lesson.reminder === true) ids.push("lesson:allocate_again");
  if (lesson.respec === true && how === "skip") {
    if (lesson.reminder !== true) ids.push("lesson:allocate_skip");
  } else ids.push("lesson:allocate");
  return ids;
}

/** 這則教學在畫面上要不要出（伺服器給了、這次畫面還沒關掉）。配點教學的再提示用自己的紀錄，不被先前的略過蓋掉。 */
export function lessonShown(lesson: WorldLesson | null, seen: ReadonlySet<string>): boolean {
  if (lesson === null || lesson.kind === "choose") return false;
  if (lesson.kind !== "allocate") return !seen.has(`lesson:${lesson.kind}`);
  if (lesson.reminder === true) return !seen.has("lesson:allocate_again") && !seen.has("lesson:allocate");
  return !seen.has("lesson:allocate") && !seen.has("lesson:allocate_skip");
}

/** 葛蘭的配點教學（#133，玩法 PM 配點教學修改稿第 6 節）：共（開局＋升級）幾點（開局點數從規則帶，6F-4b）、一鍵推薦、城鎮營火免費重配、可以略過。 */
export function AllocateLessonDialog({ lesson, affects, busy = false, onRecommended, onSelf, onSkip }: AllocateProps) {
  const notes = new Map((lesson.notes ?? []).map((n) => [n.attr as string, n.text_zh]));
  return (
    <DialogFrame label="配點教學" title={LESSON_TITLE.allocate}>
      <div className="world-opening" data-testid="world-lesson" data-kind="allocate">
        {lesson.lines.map((line, i) => (
          <p key={i} className="world-opening-line">
            <b>{line.speaker_zh}</b>：{line.text_zh}
          </p>
        ))}
        <p className="world-opening-quest small" data-testid="world-allocate-total">
          {allocateTotalText(lesson)}
          {lesson.recommended_zh !== "" && lesson.recommended_zh != null && (
            <>
              {" "}
              推薦配法：<b data-testid="world-allocate-recommended">{lesson.recommended_zh}</b>
            </>
          )}
        </p>
        {lesson.respec !== true && <p className="muted small">{ALLOCATE_EXAMPLE_ZH}</p>}
        <p className="muted small">配錯了也沒關係：在城鎮或營火都能免費重配。</p>
        <div className="world-allocate-attrs" data-testid="world-allocate-attrs">
          {ATTR_ORDER.filter((a) => notes.has(a)).map((a) => (
            <Hint key={a} text={attributeNoteText(a, notes.get(a) ?? "", affects)}>
              <span className="world-allocate-attr" tabIndex={0} data-attr={a}>
                {ATTR_ZH[a]}
              </span>
            </Hint>
          ))}
        </div>
      </div>
      <div className="modal-buttons">
        <button type="button" className="primary" disabled={busy} onClick={onRecommended} data-testid="world-allocate-recommend">
          {lesson.respec === true ? "✦ 維持推薦配法" : "✦ 推薦配法"}
        </button>
        <button type="button" disabled={busy} onClick={onSelf} data-testid="world-allocate-self">
          自己配（成長面板 G）
        </button>
        <button type="button" disabled={busy} onClick={onSkip} data-testid="world-lesson-skip">
          之後再說
        </button>
      </div>
    </DialogFrame>
  );
}

interface LevelUpProps {
  levelUp: WorldLevelUp;
  onClose(): void;
}

/** 升級畫面（6F-4 C2）：「升到 2 級：屬性點 +2、靈感 +1。回霧渡鎮找導師堂的葛蘭，學怎麼配點。」 */
export function LevelUpDialog({ levelUp, onClose }: LevelUpProps) {
  return (
    <DialogFrame label="升級" title={`升到 ${levelUp.level} 級`}>
      <div className="world-opening" data-testid="world-level-up" data-level={levelUp.level}>
        <p className="world-opening-line">{levelUp.text_zh}</p>
      </div>
      <div className="modal-buttons">
        <button type="button" className="primary" onClick={onClose} data-testid="world-level-up-close">
          知道了
        </button>
      </div>
    </DialogFrame>
  );
}

// ---------------- 主城開場 ①：醒來（RT-5） ----------------

/** `awaken` 插圖（畫布；主角是玩家自己的紙娃娃）：先躺著，`AWAKEN_LIE_MS` 後半坐起；減少動態時直接畫半坐起。 */
function AwakenArt({ hero, open, place }: { hero: DollSpec; open: readonly string[]; place: string }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [pose, setPose] = useState<AwakenPose>(() => (reducedMotion() ? 1 : 0));
  useEffect(() => {
    if (pose === 1) return undefined;
    const id = window.setTimeout(() => setPose(1), AWAKEN_LIE_MS * devAnimFactor(window.location.search));
    return () => window.clearTimeout(id);
  }, [pose]);
  const openKey = open.join(",");
  useEffect(() => {
    const c = ref.current;
    const ctx = c?.getContext("2d") ?? null;
    if (c === null || ctx === null) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1) * 2;
    c.width = AWAKEN_W * dpr;
    c.height = AWAKEN_H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, AWAKEN_W, AWAKEN_H);
    drawAwakenArt(ctx, hero, pose, openKey === "" ? [] : openKey.split(","), place);
  }, [hero, pose, openKey, place]);
  return (
    <canvas
      ref={ref}
      className="world-awaken-art"
      width={AWAKEN_W}
      height={AWAKEN_H}
      role="img"
      aria-label={pose === 0 ? "你躺在傳送陣的光圈裡" : "你在傳送陣的光圈裡坐起來"}
      data-testid="world-awaken-art"
      data-scene={AWAKEN_ART}
      data-pose={pose}
    />
  );
}

interface AwakenProps {
  /** 插圖卡上的句子（說書人；文字來自內容檔的 `opening`）。 */
  lines: readonly WorldOpeningLine[];
  hero: DollSpec;
  /** 已開放的區（傳送陣光圈亮的顏色，同主城實地圖）。 */
  open: readonly string[];
  /** 地名小牌（例「樞島・中央廣場」）。 */
  place: string;
  onStand(): void;
}

/** ① 醒來（RT-5）：`awaken` 插圖＋說書人卡（`hub` 主題的頭像框），只有一個按鈕「站起來」。 */
export function AwakenDialog({ lines, hero, open, place, onStand }: AwakenProps) {
  return (
    <DialogFrame label="開場" title="醒來">
      <div className="world-awaken" data-testid="world-opening" data-stage="awaken">
        <AwakenArt hero={hero} open={open} place={place} />
        {lines.map((line, i) => (
          <div key={i} className="world-dialog world-awaken-line" data-testid="world-awaken-line">
            <Portrait portrait={NARRATOR_PORTRAIT} region={FALLBACK_THEME} size={48} label={line.speaker_zh} />
            <div className="world-dialog-body">
              <div className="world-dialog-name small">
                <b>{line.speaker_zh}</b>
              </div>
              <p className="world-awaken-text">{line.text_zh}</p>
            </div>
          </div>
        ))}
      </div>
      <div className="modal-buttons">
        <button type="button" className="primary" onClick={onStand} data-testid="world-opening-close" autoFocus>
          站起來
        </button>
      </div>
    </DialogFrame>
  );
}

interface Props {
  guide: WorldGuide;
  onClose(): void;
}

export function OpeningDialog({ guide, onClose }: Props) {
  return (
    <DialogFrame label="開場" title="樞島">
      <div className="world-opening" data-testid="world-opening">
        {(guide.opening ?? []).map((line, i) => (
          <p key={i} className="world-opening-line">
            <b>{line.speaker_zh}</b>：{line.text_zh}
          </p>
        ))}
        <p className="world-opening-quest" data-testid="world-opening-quest">
          任務提示：<b>{guide.text_zh}</b>
          {guide.how_zh != null && <span className="muted small">（{guide.how_zh}）</span>}
        </p>
      </div>
      <div className="modal-buttons">
        <button type="button" className="primary" onClick={onClose} data-testid="world-opening-close">
          知道了
        </button>
      </div>
    </DialogFrame>
  );
}
