// 選部位小選單（PB-1c；05 5.12.3、R1、R6；規格 docs/phases/PhasePB-1計畫.md 第 7 節第 3 點；美術移植需求 3.1、3.2）。
// 選了單體招（或普攻）點有部位的頭目時跳出：第一列「本體」預設選中，之後照部位 ID；每列＝部位圖示 20px、名稱、小血條（破掉打叉）
// 或打不到的原因（灰掉；「從背後」前面加背刺小圖）、「破掉會：……」一行（太長時完整內容放 `<Hint>`）。
// - 操作：點一列、Enter（目前選取）送出；方向鍵上下移動選取；點本體、Enter（預設）、再點同一個頭目＝打本體（再點的規則在
//   `battle/tileClick.ts`）。Esc 只關選單、不取消瞄準、點外面關、同時只開一張（共用 `usePopupMenu`）。外框用共用 `PopupFrame`。
// - 位置：寬畫面（≥ 1000）放在頭目格子右邊（放不下放左邊，`sidePlacement`）；窄畫面放頭目上方、水平置中、下緣離格子上緣 8，
//   上方放不下時退回左右（`floatPlacement` 的 `fallback: sides`，使用者「其他都按照建議」）；左右夾在地圖區、窄畫面也不蓋左右 HUD 欄。
// - 選取改變時把對應動作（帶 `target_part`）交給預覽（`onPreview`），預覽多一行「拂塵還剩 12」（`battle/previewText.ts`）。
import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from "react";
import type { Action, PartOption, Pos, UnitView } from "../api/types";
import { BODY_ROW, breakLine, moveSelection, partMenuRows, partMenuSubtitle, pickedPart, type PartMenuRow } from "../battle/partMenu";
import type { HeightGrid } from "../battle/elevation";
import { tileBox } from "../battle/stageLayout";
import { BACK_ICON, type BossDoll } from "../render/qIcon/bossParts";
import { floatPlacement, sidePlacement } from "./floatCard";
import { Hint } from "./Hint";
import { PartBar, PartIcon, PART_BACK_PX } from "./PartBar";
import { PopupFrame } from "./PopupFrame";
import { usePopupMenu } from "./usePopupMenu";

/** 伺服器端（測試的 renderToStaticMarkup）沒有版面：用 useEffect，避免 useLayoutEffect 的警告。 */
const useIsoLayoutEffect = typeof window === "undefined" ? useEffect : useLayoutEffect;

/** 窄畫面（視窗寬 < 這個值）時選單放頭目上方（美術移植需求 3.2，斷點由開發定）。 */
export const PART_MENU_NARROW_PX = 1000;
/** 選單和格子之間的距離（CSS px）。 */
export const PART_MENU_GAP = 8;
/** 「破掉會」一行超過這麼多字時截斷，完整內容放說明卡。 */
const BREAK_LINE_MAX = 16;

export interface PartMenuState {
  targetId: string;
  tile: Pos;
  /** 不帶部位的動作（＝打本體）。 */
  action: Action;
  options: readonly PartOption[];
  submit: boolean;
  dismissPin: boolean;
}

interface Props {
  menu: PartMenuState;
  boss: UnitView;
  model: HeightGrid;
  scale: number;
  /** `.battle-board`（選單放在它裡面、座標相對於它）。 */
  boardRef: RefObject<HTMLDivElement>;
  /** 選了（`null`＝本體）。 */
  onPick(targetPart: string | null): void;
  onClose(): void;
  /** 選取改變時預覽的動作；關掉時 `null`。 */
  onPreview(action: Action | null): void;
  /**
   * PB-1e：選單開著（頭目的狀態列、蓄力徽章淡到 40%）與滑過的部位（頭目身上那個部位亮起；`part` ＝ `null`＝本體）；
   * 關掉時 `null`。
   */
  onFocus?(focus: { targetId: string; part: string | null } | null): void;
}

/** 動作帶上部位（`null`＝本體，原樣）。 */
export function withTargetPart(action: Action, part: string | null): Action {
  return part === null ? action : ({ ...action, target_part: part } as Action);
}

/** 頭目的紙娃娃輸入（本體列的小頭像）。 */
export function bossDollOf(u: UnitView): BossDoll {
  return { template: u.template_id, dollLook: u.doll_look ?? null, weaponId: u.weapon_id ?? null };
}

function shortLine(text: string): string {
  return text.length > BREAK_LINE_MAX ? `${text.slice(0, BREAK_LINE_MAX)}…` : text;
}

function Row({ row, selected, doll, onHover, onPick }: { row: PartMenuRow; selected: boolean; doll: BossDoll | null; onHover(): void; onPick(): void }) {
  const line = breakLine(row);
  const cls = ["part-menu-row", selected ? "selected" : "", row.ok ? "" : "off", row.broken ? "broken" : ""].filter((c) => c !== "").join(" ");
  return (
    <li
      role="menuitem"
      aria-disabled={!row.ok}
      aria-selected={selected}
      className={cls}
      data-part={row.id}
      data-testid={`part-menu-row-${row.id}`}
      onPointerEnter={onHover}
      onClick={(e) => {
        e.stopPropagation();
        // PB-1e：「破掉會」說明卡是 portal 到 body 的，React 的事件會照元件樹冒泡上來；點說明卡（釘住）不能當成選了這一列
        if (!(e.target instanceof Node) || !e.currentTarget.contains(e.target)) return;
        onPick();
      }}
    >
      <span className="part-menu-main">
        <PartIcon id={row.id} ok={row.ok} broken={row.broken} doll={row.id === "body" ? doll : null} />
        <span className="part-menu-name">{row.name}</span>
        {row.bar.kind === "body" ? (
          row.bar.hp === null ? (
            <span className="part-bar hidden" data-state="hidden" aria-label="看不到" />
          ) : (
            <>
              <span className="part-bar body" data-state="ok" role="img" aria-label={`${row.bar.hp}/${row.bar.max}`}>
                <i className="part-bar-fill" style={{ width: `${Math.max(0, Math.min(1, row.bar.hp / Math.max(1, row.bar.max))) * 100}%` }} />
              </span>
              <span className="part-bar-num">
                {row.bar.hp}/{row.bar.max}
              </span>
            </>
          )
        ) : row.ok ? (
          <PartBar state={row.bar} />
        ) : (
          <span className="part-menu-why">
            {row.back && <PartIcon id={BACK_ICON} ok={false} broken={false} doll={null} px={PART_BACK_PX} />}
            {row.broken ? "已破壞" : row.reason}
          </span>
        )}
      </span>
      {line !== null && (
        <Hint text={line}>
          <span className="part-menu-break" data-testid={`part-menu-break-${row.id}`} onClick={(e) => e.stopPropagation()}>
            {shortLine(line)}
          </span>
        </Hint>
      )}
    </li>
  );
}

export function PartMenu({ menu, boss, model, scale, boardRef, onPick, onClose, onPreview, onFocus }: Props) {
  const popup = usePopupMenu({ open: true, setOpen: (open) => (open ? undefined : onClose()) });
  const rows = partMenuRows(boss, menu.options);
  const [sel, setSel] = useState(0);
  const doll = bossDollOf(boss);
  const own = useRef<HTMLDivElement | null>(null);
  const [side, setSide] = useState<string>("right");

  const pick = (row: PartMenuRow | undefined) => {
    const part = pickedPart(row);
    if (part === undefined) return;
    onPick(part);
  };

  // 預覽跟著選取（關掉時清掉）
  const selected = rows[sel];
  const previewKey = `${menu.targetId}|${selected?.id ?? ""}|${selected?.ok === true ? 1 : 0}`;
  useEffect(() => {
    const part = pickedPart(selected);
    onPreview(part === undefined ? menu.action : withTargetPart(menu.action, part));
    // 只在選取改變時重送
  }, [previewKey]);
  useEffect(() => () => onPreview(null), []);
  // PB-1e：頭目身上跟著選取亮起（本體不亮）；關掉時拿掉亮起與淡化
  const focusPart = selected === undefined || selected.id === BODY_ROW ? null : selected.id;
  useEffect(() => {
    onFocus?.({ targetId: menu.targetId, part: focusPart });
  }, [menu.targetId, focusPart]);
  useEffect(() => () => onFocus?.(null), []);

  // 方向鍵、Enter（Esc 由 usePopupMenu 處理）；攔下事件，BattleScreen 的鍵盤處理不會再收到
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        e.stopPropagation();
        setSel((cur) => moveSelection(rows.length, cur, e.key === "ArrowDown" ? 1 : -1));
      } else if (e.key === "Enter") {
        e.preventDefault();
        e.stopPropagation();
        pick(rows[sel]);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  });

  // 位置：相對於 `.battle-board`
  useIsoLayoutEffect(() => {
    const el = own.current;
    const board = boardRef.current;
    if (el === null || board === null) return undefined;
    const layout = () => {
      const canvas = board.querySelector(".battle-canvas");
      const scroller = board.querySelector(".board-scroll");
      if (canvas === null) return;
      const b = board.getBoundingClientRect();
      const c = canvas.getBoundingClientRect();
      const s = scroller?.getBoundingClientRect() ?? b;
      const t = tileBox(menu.tile, model, scale);
      const anchor = { left: c.left - b.left + t.left, top: c.top - b.top + t.top, width: t.width, height: t.height };
      const size = { width: el.offsetWidth, height: el.offsetHeight };
      const narrow = window.innerWidth < PART_MENU_NARROW_PX;
      // 地圖區（相對於 board）；窄畫面再讓開左右 HUD 欄（放得下時）
      let lo = Math.max(0, s.left - b.left);
      let hi = Math.min(b.width, s.right - b.left);
      if (narrow) {
        const left = board.querySelector(".bhud-left")?.getBoundingClientRect();
        const right = board.querySelector(".bhud-right")?.getBoundingClientRect();
        const l2 = left === undefined ? lo : Math.max(lo, left.right - b.left);
        const r2 = right === undefined ? hi : Math.min(hi, right.left - b.left);
        if (r2 - l2 >= size.width + 8) {
          lo = l2;
          hi = r2;
        }
      }
      const vp = { width: hi - lo, height: Math.min(b.height, s.bottom - b.top) };
      const a = { ...anchor, left: anchor.left - lo };
      const p = narrow
        ? floatPlacement(a, size, vp, "center", 4, "above", { kind: "sides", gap: PART_MENU_GAP })
        : sidePlacement(a, size, vp, 4, PART_MENU_GAP);
      el.style.left = `${Math.round(p.left + lo)}px`;
      el.style.top = `${Math.round(p.top)}px`;
      el.style.maxHeight = `${Math.max(80, vp.height - 8)}px`;
      setSide(p.side);
    };
    layout();
    window.addEventListener("resize", layout);
    return () => window.removeEventListener("resize", layout);
  });

  return (
    <div
      ref={(node) => {
        own.current = node;
        (popup.rootRef as { current: HTMLDivElement | null }).current = node;
      }}
      className="popup-menu part-menu"
      data-testid="part-menu"
      data-side={side}
      onPointerMove={(e) => e.stopPropagation()}
      onContextMenu={(e) => {
        e.preventDefault();
        e.stopPropagation();
        onClose();
      }}
    >
      <PopupFrame placement={{ kind: "inline" }} className="part-menu-frame" label="選部位" testId="part-menu-frame" frameRef={popup.panelRef}>
        <div className="part-menu-head">
          <b>{boss.name_zh}</b>
          <span className="muted small">{partMenuSubtitle(boss)}</span>
        </div>
        <ul className="part-menu-list" role="menu" aria-label="選部位">
          {rows.map((r, i) => (
            <Row key={r.id} row={r} selected={i === sel} doll={doll} onHover={() => setSel(i)} onPick={() => pick(r)} />
          ))}
        </ul>
        <div className="part-menu-foot muted small">點本體、按 Enter 或再點頭目＝打本體</div>
      </PopupFrame>
    </div>
  );
}
