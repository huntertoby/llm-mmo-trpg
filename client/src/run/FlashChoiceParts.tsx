// 靈感閃現「選變體」畫面（FL-1b，docs/art/靈感閃現選擇-移植需求.md）的小元件：術語字（點線底線＋說明卡）、欄位小圖、
// 「前 → 後」各列、原技能列與「完整說明」。圖示一張都不新畫（第 7 節）：卡片小圖／部件＝`PartBare`、狀態＝`statusIconCanvas`、
// 關鍵字圓章＝`qIcon/keywords.chipCanvas`、警告三角＝`WarnGlyph`；「變弱」的向下三角是 CSS。
import { Fragment, type ReactNode } from "react";
import type { ChangeIcon, FlashBaseStat, FlashTerm, SkillCard, StatChange } from "../api/types";
import { categoryLabel, kindLabel, skeletonLabel } from "../battle/source";
import { chipCanvas } from "../render/qIcon/keywords";
import { statusIconCanvas, statusIconKey } from "../render/statusIcon";
import { Hint } from "../ui/Hint";
import { IconCanvas } from "../ui/HudGlyph";
import { PartBare, WarnGlyph } from "../ui/PanelKit";
import { AssemblyFormula, SkillIconView } from "../ui/SkillIconView";
import {
  FLASH_BASE_NARROW_ZH,
  FLASH_BASE_WIDE_ZH,
  FLASH_LLM_NAME_HINT,
  FLASH_LLM_NAME_ZH,
  FLASH_MORE_NARROW_ZH,
  FLASH_MORE_WIDE_ZH,
  FLASH_NAME_ZH,
  FLASH_NONE_ZH,
  nowStyle,
  nowText,
  parseTerms,
  splitWhen,
} from "./flashChoice";

export type Terms = Readonly<Record<string, FlashTerm>>;

function blankCanvas(): HTMLCanvasElement {
  return document.createElement("canvas");
}

/** 第⑤批狀態圖示（燃燒…）。 */
function StatusGlyph({ id, px }: { id: string; px: number }) {
  return <IconCanvas px={px} className="pnl-ico" cacheKey={`fc-status:${statusIconKey(id, px)}`} make={() => statusIconCanvas(id, px) ?? blankCanvas()} data={{ "data-icon": `status:${id}` }} />;
}

/** 第⑤b 批關鍵字圓章。 */
export function KeywordGlyph({ id, px }: { id: string; px: number }) {
  return <IconCanvas px={px} className="pnl-ico" cacheKey={`fc-kw:${id}:${px}`} make={() => chipCanvas(id, px) ?? blankCanvas()} data={{ "data-icon": `kw:${id}` }} />;
}

/** 欄位小圖（伺服器 `ChangeIconOut`）。 */
export function ChangeIconView({ icon, px = 16 }: { icon: ChangeIcon | null | undefined; px?: number }) {
  if (icon == null) return <span className="fc-noicon" aria-hidden="true" />;
  if (icon.kind === "status") return <StatusGlyph id={icon.id} px={px} />;
  if (icon.kind === "keyword") return <KeywordGlyph id={icon.id} px={px} />;
  return <PartBare cat={icon.cat ?? "card"} id={icon.id} px={px} />;
}

/** 說明卡內容：標題（亮金）＋一段字。 */
function TermCard({ term }: { term: FlashTerm }) {
  return (
    <div className="hint-tip-text fc-tipcard">
      <b className="fc-tip-title">{term.title_zh}</b>
      {term.text_zh}
    </div>
  );
}

/** 一個術語：查得到說明卡就畫青色點線底線＋說明卡（`Hint`，portal 到 body，不會被捲動區切掉）；查不到只畫字。 */
export function Term({ id, label, terms }: { id: string | null | undefined; label: ReactNode; terms: Terms }) {
  const term = id == null ? undefined : terms[id];
  if (term === undefined) return <>{label}</>;
  return (
    <Hint text={`${term.title_zh}：${term.text_zh}`} rich={<TermCard term={term} />}>
      <span className="fc-term" tabIndex={0} data-term={id}>
        {label}
      </span>
    </Hint>
  );
}

/** 伺服器字串（帶 `[[術語|字]]`、`{{kw:id}}` 標記）畫成字＋術語＋小圓章。 */
export function TermText({ text, terms }: { text: string; terms: Terms }) {
  return (
    <>
      {parseTerms(text).map((p, i) => {
        if (p.kind === "text") return <Fragment key={i}>{p.text}</Fragment>;
        if (p.kind === "icon") return p.cat === "kw" ? <KeywordGlyph key={i} id={p.id} px={14} /> : null;
        return <Term key={i} id={p.id} label={p.label} terms={terms} />;
      })}
    </>
  );
}

/** 「後」那一塊：四種樣式（第 3 節）。代價前面掛第⑦批警告三角；變弱前面掛 CSS 向下三角；新加的掛實心綠「新」。 */
function NowChip({ change, terms }: { change: StatChange; terms: Terms }) {
  const style = nowStyle(change);
  const text = nowText(change);
  const { main, when } = splitWhen(text);
  return (
    <span className={`fc-now ${style}`} data-style={style}>
      {style === "cost" && <WarnGlyph px={13} />}
      {style === "down" && <i className="fc-down" aria-label="變弱" />}
      {style === "new" && <span className="fc-newtag">新</span>}
      <span>
        <TermText text={main} terms={terms} />
        {when !== null && (
          <span className="fc-when">
            <TermText text={when} terms={terms} />
          </span>
        )}
      </span>
    </span>
  );
}

/** 改名（LF-3）：大變化、轉型的新名稱。照「前 → 後」同一格線，排在最前面；「後」是新名稱（粗字、無底無框，名稱沒有好壞），
 * 本機模型取的名稱後面多一顆紫色小標記（候選卡同一個字，滑過出說明卡）。 */
export type Rename = { before: string; after: string; llm: boolean };

function RenameRow({ rename }: { rename: Rename }) {
  return (
    <>
      <span className="fc-noicon" aria-hidden="true" />
      <span className="fc-lab">{FLASH_NAME_ZH}</span>
      <span className="fc-was">{rename.before}</span>
      <span className="fc-arrow" aria-label="變成">
        →
      </span>
      <span className="fc-nows">
        {/* FL-1g（LF-3 驗收可修 1）：新名稱與小標記是不斷行的一組，放不下時整組換行 */}
        <span className="fc-name-group" data-testid="flash-name-group">
          <span className="fc-now name" data-style="name" data-testid="flash-new-name">
            <span>{rename.after}</span>
          </span>
          {rename.llm && (
            <Hint text={FLASH_LLM_NAME_HINT}>
              <span className="fc-src" tabIndex={0} data-testid="flash-name-source">
                {FLASH_LLM_NAME_ZH}
              </span>
            </Hint>
          )}
        </span>
      </span>
    </>
  );
}

/** 一個選項的「前 → 後」各列（只列有變的欄位，一列一項）。LF-3：改名排第一列，本機模型的一句話描述接在名稱下面（整列寬、
 * 次要字、最多兩行；沒有就不佔位）。 */
export function DiffRows({ changes, terms, rename = null, note = null }: { changes: readonly StatChange[]; terms: Terms; rename?: Rename | null; note?: string | null }) {
  if (changes.length === 0 && rename === null && note === null) return null;
  return (
    <div className="fc-diffs" data-testid="flash-diffs">
      {rename !== null && <RenameRow rename={rename} />}
      {note !== null && (
        <p className="fc-note" data-testid="flash-note">
          {note}
        </p>
      )}
      {changes.map((c, i) => (
        <Fragment key={`${c.field}:${i}`}>
          <ChangeIconView icon={c.icon} />
          <span className="fc-lab">
            <Term id={c.term} label={c.name_zh || c.label_zh} terms={terms} />
          </span>
          <span className={`fc-was${c.before === null ? " none" : ""}`}>{c.before === null ? FLASH_NONE_ZH : <TermText text={c.before_zh ?? c.before} terms={terms} />}</span>
          <span className="fc-arrow" aria-label="變成">
            →
          </span>
          <span className="fc-nows">
            <NowChip change={c} terms={terms} />
          </span>
        </Fragment>
      ))}
    </div>
  );
}

// ---- 原技能列（2.1）與「完整說明」（6） ---------------------------------------------------

function BaseStats({ stats, terms }: { stats: readonly FlashBaseStat[]; terms: Terms }) {
  return (
    <div className="fc-stats" data-testid="flash-base-stats">
      {stats.map((s, i) => (
        <span key={`${s.name_zh}:${i}`} className="fc-stat">
          <ChangeIconView icon={s.icon} />
          <Term id={s.term} label={s.name_zh} terms={terms} />
          <b>{s.value_zh}</b>
        </span>
      ))}
    </div>
  );
}

/** 「完整說明」說明卡：原卡「詳細」的全部欄位（類型、組成、花費、範圍、效果、會造成、元素、威力看）。 */
export function BaseDetail({ card }: { card: SkillCard }) {
  const skeleton = skeletonLabel(card);
  const makes = card.keywords?.makes ?? [];
  return (
    <div className="fc-pop" data-testid="flash-base-detail">
      <h4>{card.name_zh}</h4>
      <dl>
        <dt>類型</dt>
        <dd>
          {card.rarity}・{kindLabel(card)}
          {skeleton !== "" && `・${skeleton}`}・{categoryLabel(card)}
        </dd>
        <dt>組成</dt>
        <dd className="fc-asm">
          <AssemblyFormula icon={card.icon} />
        </dd>
        <dt>花費</dt>
        <dd>{card.cost.join("、")}</dd>
        <dt>範圍</dt>
        <dd>{card.shape}</dd>
        <dt>效果</dt>
        <dd>
          {card.effects.map((e, i) => (
            <div key={`${i}:${e}`}>{e}</div>
          ))}
        </dd>
        {makes.length > 0 && (
          <>
            <dt>會造成</dt>
            <dd className="fc-asm">
              {makes.map((k) => (
                <span key={k.id}>
                  <KeywordGlyph id={k.id} px={14} />
                  {k.name_zh}
                </span>
              ))}
            </dd>
          </>
        )}
        {(card.element ?? null) !== null && (
          <>
            <dt>元素</dt>
            <dd>{card.element}</dd>
          </>
        )}
        <dt>威力看</dt>
        <dd>{card.scaling}</dd>
      </dl>
      {card.concept !== "" && <p className="concept">{card.concept}</p>}
    </div>
  );
}

/** 原技能列：技能圖示＋名字＋「原本的樣子」（窄版只寫「原本」）＋數字＋「完整說明」（窄版「說明」）。 */
export function BaseStrip({ card, stats, terms }: { card: SkillCard; stats: readonly FlashBaseStat[]; terms: Terms }) {
  return (
    <div className="fc-base" data-testid="flash-base">
      <span className="fc-base-icon wide-only">
        <SkillIconView icon={card.icon} size={40} level="mid" label={card.name_zh} />
      </span>
      <span className="fc-base-icon narrow-only">
        <SkillIconView icon={card.icon} size={32} level="mid" label={card.name_zh} />
      </span>
      <div className="fc-base-name wide-only">
        {card.name_zh}
        <span className="k">{FLASH_BASE_WIDE_ZH}</span>
      </div>
      <span className="fc-base-k narrow-only">{FLASH_BASE_NARROW_ZH}</span>
      <BaseStats stats={stats} terms={terms} />
      <span className="fc-base-more">
        <Hint text={card.name_zh} rich={<BaseDetail card={card} />}>
          <button type="button" data-testid="flash-base-more">
            <span className="wide-only">{FLASH_MORE_WIDE_ZH}</span>
            <span className="narrow-only">{FLASH_MORE_NARROW_ZH}</span>
          </button>
        </Hint>
      </span>
    </div>
  );
}
