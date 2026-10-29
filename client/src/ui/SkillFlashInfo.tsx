// 技能卡上的閃現資訊（Phase 3W-6）：「已閃 N／5 次」、可以閃現時的「可以閃現了」、升階後的轉型提示、變化歷程。
import type { SkillFlash } from "../api/types";
import { CAN_FLASH_TEXT, flashCountText, recordLine, showCanFlash, TRANSFORM_HINT, TRANSFORM_HINT_TIP } from "../run/flash";
import { Hint } from "./Hint";

interface Props {
  flash: SkillFlash | undefined;
  rules: Parameters<typeof flashCountText>[1];
  /** 不列變化歷程（只要次數與提示）。 */
  brief?: boolean;
}

export function SkillFlashInfo({ flash, rules, brief = false }: Props) {
  if (flash === undefined) return null;
  const records = flash.records;
  return (
    <div className="skill-flash-info small" data-testid="skill-flash-info">
      <span className="skill-flash-count" data-testid="skill-flash-count">
        {flashCountText(flash, rules)}
      </span>
      {showCanFlash(flash) && (
        <span className="skill-flash-ready" data-testid="skill-flash-ready">
          {CAN_FLASH_TEXT}
        </span>
      )}
      {flash.reflash_transform_hint && (
        <Hint text={TRANSFORM_HINT_TIP}>
          <span className="skill-flash-transform" data-testid="skill-flash-transform" tabIndex={0}>
            {TRANSFORM_HINT}
          </span>
        </Hint>
      )}
      {!brief && records.length > 0 && (
        <ol className="skill-flash-history" data-testid="skill-flash-history">
          {records.map((r) => (
            <li key={r.nth}>{recordLine(r)}</li>
          ))}
        </ol>
      )}
    </div>
  );
}
