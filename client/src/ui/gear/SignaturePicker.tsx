// 角色面板的「招牌效果」一節（E6-b2；美術移植需求第 1 節第 5 項，樣張 `docs/art/sample/e6Signature.js` 的 pickList）：
// 一輪的 `RunHeroPanel`、大世界的「穿戴中」共用。節名後面寫「生效 N／3・改寫規則 N／1」（沒有改寫規則時只寫「生效 N／3」）；
// 每一列是勾選（招牌方框、改寫規則圓鈕）、16 px 圖示、招牌名，後面灰色小字「類型・部位：裝備名」；沒勾的整列標灰、下面寫原因（短版）。
// 列的順序照部位（後端排好），勾選時不跳動。滑過一列顯示現行裝備圖示的浮動卡（共用 `PartTip`；按列本身是勾選，不會釘住卡片）。
// 按列的規則在 `gear/signature.ts` 的 `clickRow`：已滿時按沒勾的那列跳一行提示（字由後端給）；勾選的合法性由後端裁決。
import { useEffect, useState, type CSSProperties } from "react";
import type { HeroGearSlot, SignaturePanel, SignatureRow } from "../../api/types";
import { clickRow, countText, rowChecked, signatureColor } from "../../gear/signature";
import { itemTipLines } from "../../run/gearOffer";
import { PartTip } from "../PartTip";
import { SignatureIcon } from "./SignatureIcon";

interface Props {
  panel: SignaturePanel;
  /** 穿戴中的裝備（滑過一列時顯示那件的浮動卡）。 */
  equipment: readonly HeroGearSlot[];
  busy: boolean;
  /** 送出新的勾選；`null` ＝ 只能看（例如一輪結束的畫面）。 */
  onPick: ((chosen: string[]) => void) | null;
  /** 大世界寬的時候分兩欄。 */
  wide?: boolean;
}

const NONE: ReadonlySet<string> = new Set();

function rowsKey(panel: SignaturePanel): string {
  return panel.rows.map((r) => `${r.key}:${r.active ? 1 : 0}`).join("|");
}

function PickRow({
  row,
  checked,
  reason,
  pressed,
  disabled,
  equipment,
  onClick,
}: {
  row: SignatureRow;
  checked: boolean;
  reason: string | null;
  pressed: boolean;
  disabled: boolean;
  equipment: readonly HeroGearSlot[];
  onClick(): void;
}) {
  const item = equipment.find((e) => e.slot === row.slot)?.item ?? null;
  const style = { "--sig": signatureColor(row.rarity, !checked) } as CSSProperties;
  const cls = ["gear-pick-row", checked ? "" : "off", pressed ? "press" : ""].filter((c) => c !== "").join(" ");
  return (
    <li className={cls} style={style} data-testid={`signature-row-${row.slot}`} data-key={row.key}>
      <PartTip cat={row.slot_zh} label={item?.name_zh ?? row.item_name_zh} tip="" lines={item === null ? undefined : itemTipLines(item, row.slot)}>
        <button
          type="button"
          className="gear-pick-btn"
          role={row.rule ? "radio" : "checkbox"}
          aria-checked={checked}
          disabled={disabled}
          onClick={(e) => {
            e.stopPropagation(); // 按列＝勾選；不要同時釘住浮動卡（釘住點列的空白處或 Enter 以外的方式）
            onClick();
          }}
          onKeyDown={(e) => e.stopPropagation()}
          data-testid={`signature-pick-${row.slot}`}
        >
          <span className={`gear-pick-box${row.rule ? " round" : ""}${checked ? " on" : ""}`} aria-hidden="true" />
          <SignatureIcon kind={row.kind} size={16} />
          <span className="gear-pick-main">
            <span className="gear-pick-line">
              <b className="gear-pick-name">{row.name_zh}</b>
              <span className="muted small">
                {row.kind_zh}・{row.slot_zh}：{row.item_name_zh}
              </span>
            </span>
            {reason !== null && (
              <span className="small gear-pick-off" data-testid={`signature-off-${row.slot}`}>
                {reason}
              </span>
            )}
          </span>
        </button>
      </PartTip>
    </li>
  );
}

export function SignaturePicker({ panel, equipment, busy, onPick, wide = false }: Props) {
  const [dropped, setDropped] = useState<ReadonlySet<string>>(NONE);
  const [hint, setHint] = useState<string | null>(null);
  const [pressed, setPressed] = useState<string | null>(null);
  const key = rowsKey(panel);
  useEffect(() => {
    // 後端回來新的勾選：畫面上先取消的、提示都清掉
    setDropped(NONE);
    setHint(null);
    setPressed(null);
  }, [key]);
  const disabled = busy || onPick === null || panel.problem_zh != null;
  const press = (row: SignatureRow): void => {
    const result = clickRow(panel, dropped, row);
    setPressed(null);
    setHint(null);
    if (result.kind === "send") onPick?.(result.chosen);
    else if (result.kind === "drop") setDropped(new Set([...dropped, result.key]));
    else if (result.kind === "undrop") setDropped(new Set([...dropped].filter((k) => k !== result.key)));
    else if (result.kind === "full") {
      setHint(panel.full_zh);
      setPressed(row.key);
    }
  };
  return (
    <div className={`gear-pick${wide ? " wide" : ""}`} data-testid="signature-panel">
      <div className="section-title">
        招牌效果
        <span className="muted small lead-gap" data-testid="signature-count">
          {countText(panel, dropped)}
        </span>
      </div>
      {panel.problem_zh != null && <div className="muted small">改勾選：{panel.problem_zh}</div>}
      {hint !== null && (
        <div className="small gear-pick-hint" role="status" data-testid="signature-full-hint">
          {hint}
        </div>
      )}
      <ul className="gear-pick-list">
        {panel.rows.map((row) => {
          const checked = rowChecked(row, dropped);
          const reason = checked || dropped.has(row.key) ? null : (row.off_zh ?? null);
          return (
            <PickRow
              key={row.key}
              row={row}
              checked={checked}
              reason={reason}
              pressed={pressed === row.key}
              disabled={disabled}
              equipment={equipment}
              onClick={() => press(row)}
            />
          );
        })}
      </ul>
    </div>
  );
}
