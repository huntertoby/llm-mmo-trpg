// 事件卡選項列 A（PNL-4；docs/art/資訊面板-移植需求.md 2.2 `SolutionTile`、3.4；樣張 docs/art/sample/infoPanels.js `tile()`、`solGrid()`）：
// 兩欄等寬格子（剩一格撐滿整列，CSS `:last-child:nth-child(odd)`）；每格＝`SolutionGlyph` 24＋主字（粗體、最多兩行「…」、詞間 `<wbr>`）
// ＋次行（種類・屬性圖＋名／交涉 −N 補給）；全文在說明卡（現行 `solutionLabel` 那張 `Hint`）。放棄縮成右下小鈕、不佔格；
// 持有線頭的「用〔…〕抵」是那一格次行右邊的小鈕（不另佔一格）。規則照舊全在後端（可用、原因、線頭都來自 `WorldEventView`）。
import { Fragment } from "react";
import type { WorldEventSolution } from "../api/types";
import { Hint } from "../ui/Hint";
import { KeepNum } from "../ui/PanelKit";
import { SOLUTION_ICON_ZH, solutionIcon } from "./narration";
import { glueTail, splitSolutions, solutionSub, tileMain, wordBreaks } from "./solutionGrid";
import { solutionClick, solutionHint, solutionLabel, waiveLabel } from "./story";
import { AttrIcon, SolutionGlyph } from "./StoryIcons";

/** 選項格圖示（需求 1.2：照 `SolutionGlyph` 24）、次行屬性圖示（樣張 14）、放棄小鈕圖示（樣張 18）。 */
export const TILE_ICON = 24;
export const TILE_ATTR_ICON = 14;
export const LEAVE_ICON = 18;

/** 線頭抵付出的說明卡（字照現行）。 */
export const WAIVE_HINT_ZH = "用掉這條線頭代替付出補給（線頭用掉就沒了）";

/** 說明卡內文：數字（「+2」「−1」）不和前面的詞分開（`KeepNum`，PNL-3 待決 6）。 */
export function HintBody({ text }: { text: string }) {
  return (
    <div className="hint-tip-text">
      <KeepNum text={text} />
    </div>
  );
}

/** 主字：詞與詞之間插 `<wbr>`（`wordBreaks`）。 */
function MainWords({ text }: { text: string }) {
  const words = wordBreaks(text);
  return (
    <>
      {words.map((w, i) => {
        const { head, tail } = glueTail(w);
        return (
          <Fragment key={i}>
            {i > 0 && <wbr />}
            {head}
            {tail !== "" && <span className="world-sol-glue">{tail}</span>}
          </Fragment>
        );
      })}
    </>
  );
}

interface TileProps {
  solution: WorldEventSolution;
  busy: boolean;
  /** 這一格是目前打開的情境判定（按鈕亮起）。 */
  active: boolean;
  onOpen(template: string): void;
  onSolve(solution: number, useThread: string | null): void;
}

/** 一格選項（`SolutionTile`）。 */
export function SolutionTile({ solution: s, busy, active, onOpen, onSolve }: TileProps) {
  const click = solutionClick(s);
  const waive = waiveLabel(s);
  const icon = solutionIcon(s);
  const main = tileMain(s);
  const sub = solutionSub(s);
  const hint = `${solutionLabel(s)}\n${solutionHint(s)}`;
  return (
    <div className={`world-sol-cell${waive !== null ? " has-waive" : ""}`} data-testid="world-solution-cell">
      <Hint text={hint} rich={<HintBody text={hint} />}>
        <button
          type="button"
          className={`world-solution world-sol${active ? " primary" : ""}`}
          disabled={busy || !s.available || click === null}
          onClick={() => {
            if (click?.kind === "open") onOpen(click.template);
            else if (click?.kind === "solve") onSolve(click.solution, null);
          }}
          aria-label={`${SOLUTION_ICON_ZH[icon]}：${main}`}
          data-testid="world-solution"
          data-kind={s.kind}
          data-icon={icon}
        >
          <SolutionGlyph icon={icon} size={TILE_ICON} />
          <span className="world-sol-text">
            <span className="world-sol-main world-solution-line">
              <MainWords text={main} />
            </span>
            {(sub !== null || waive !== null) && (
              <span className="world-sol-sub" data-testid="world-solution-sub">
                {sub?.kind != null && <span>{sub.kind}</span>}
                {sub !== null &&
                  sub.attrs.map((a, i) => (
                    /* 分隔號和後面的屬性包成一段不斷行：窄的格子換行時「・」「／」不會單獨留在行尾 */
                    <span key={a.name} className="world-sol-attr-run">
                      {(i > 0 || sub.kind !== null) && <span className="world-sol-sep">{i > 0 ? "／" : "・"}</span>}
                      <span className="world-sol-attr" data-attr={a.key ?? a.name}>
                        {a.key !== null && <AttrIcon attr={a.key} size={TILE_ATTR_ICON} />}
                        {a.name}
                      </span>
                    </span>
                  ))}
                {sub?.cost != null && <span className="world-solution-cost">−{sub.cost} 補給</span>}
                {/* 「用〔…〕抵」小鈕疊在這一行右邊：這裡放一份看不見的同字，次行先讓出它的寬度（換行也跟著換） */}
                {waive !== null && (
                  <span className="world-sol-waive-ghost" aria-hidden="true">
                    {waive}
                  </span>
                )}
              </span>
            )}
          </span>
        </button>
      </Hint>
      {waive !== null && (
        <Hint text={WAIVE_HINT_ZH}>
          <button type="button" className="world-sol-waive" disabled={busy || s.waive_thread == null} onClick={() => onSolve(s.index, s.waive_thread ?? null)} data-testid="world-solution-waive">
            {waive}
          </button>
        </Hint>
      )}
    </div>
  );
}

/** 放棄：右下一顆小鈕（不佔格）。 */
function LeaveButton({ solution: s, busy, onSolve }: Pick<TileProps, "solution" | "busy" | "onSolve">) {
  const click = solutionClick(s);
  const icon = solutionIcon(s);
  const hint = `${solutionLabel(s)}\n${solutionHint(s)}`;
  return (
    <Hint text={hint} rich={<HintBody text={hint} />}>
      <button
        type="button"
        className="world-solution world-sol-leave"
        disabled={busy || !s.available || click === null}
        onClick={() => {
          if (click?.kind === "solve") onSolve(click.solution, null);
        }}
        aria-label={`${SOLUTION_ICON_ZH[icon]}：${tileMain(s)}`}
        data-testid="world-solution"
        data-kind={s.kind}
        data-icon={icon}
      >
        <SolutionGlyph icon={icon} size={LEAVE_ICON} />
        <span className="world-solution-line">{tileMain(s)}</span>
      </button>
    </Hint>
  );
}

interface GridProps {
  solutions: readonly WorldEventSolution[];
  busy: boolean;
  /** 目前打開的情境判定（那一格亮起）。 */
  openTemplate: string | null;
  onOpen(template: string): void;
  onSolve(solution: number, useThread: string | null): void;
}

/** 選項列 A：兩欄格子＋右下放棄小鈕（樣張 `solGrid(opts, { splitLeave: true })`）。 */
export function SolutionGrid({ solutions, busy, openTemplate, onOpen, onSolve }: GridProps) {
  const { tiles, leave } = splitSolutions(solutions);
  return (
    <div className="world-event-solutions" data-testid="world-solutions">
      {tiles.length > 0 && (
        <div className="world-sol-grid">
          {tiles.map((s) => {
            const click = solutionClick(s);
            const active = click?.kind === "open" && openTemplate === click.template;
            return <SolutionTile key={s.index} solution={s} busy={busy} active={active} onOpen={onOpen} onSolve={onSolve} />;
          })}
        </div>
      )}
      {leave.length > 0 && (
        <div className="world-sol-foot">
          {leave.map((s) => (
            <LeaveButton key={s.index} solution={s} busy={busy} onSolve={onSolve} />
          ))}
        </div>
      )}
    </div>
  );
}
