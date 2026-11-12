// 資訊面板的共用版面元件（PNL-1a；docs/art/資訊面板-移植需求.md 2.2、3.1）：照樣張 `docs/art/sample/infoPanels.js` 的
// `callout()`、`chip()`、`tag()`、`fold()`、`head()` 搬成 React；樣式在 `styles/world-hud.css` 的 `pnl-*`（樣張 `ip-*` 改名）。
// 分頁列在 `PanelTabs.tsx`。說明 (i) 一律用現有 `<Hint>`（浮動卡規則 6.5.1），不用原生 title。
// 圖示一張都不新畫（2.3）：HUD（`HudGlyph`）、事件卡（`render/panelIcon.ts`）、第④批部件。
import { createContext, useContext, type ReactNode, type SyntheticEvent } from "react";
import { eventBareCanvas, eventIconCanvas, panelIconKey, partGlyphCanvas } from "../render/panelIcon";
import { Hint } from "./Hint";
import { HudGlyph, IconCanvas } from "./HudGlyph";

// ---------------- 圖示 ----------------

/** HUD 圖示（第⑦批）不帶淺色圓底（樣張 `IP.hud`：`frame: "none"`）。 */
export function HudBare({ id, px }: { id: string; px: number }) {
  return <HudGlyph id={id} px={px} className="pnl-ico" opt={{ frame: "none" }} data={{ "data-icon": id }} />;
}

/** 事件卡圖示的圖樣本身（第⑧批，不帶深底圓與色環；樣張 `evBare()`）。 */
export function EventBare({ id, px }: { id: string; px: number }) {
  return <IconCanvas px={px} className="pnl-ico" cacheKey={panelIconKey("bare", id, px)} make={() => eventBareCanvas(id, px)} data={{ "data-icon": id }} />;
}

/** 事件卡圖示（深底圓＋色環；樣張 `ev()`）。 */
export function EventRing({ id, px }: { id: string; px: number }) {
  return <IconCanvas px={px} className="pnl-ico" cacheKey={panelIconKey("event", id, px)} make={() => eventIconCanvas(id, px)} data={{ "data-icon": id }} />;
}

/** 第④批部件圖樣（不帶圓片；樣張 `part()`）。 */
export function PartBare({ cat, id, px }: { cat: string; id: string; px: number }) {
  const key = `${cat}:${id}`;
  return <IconCanvas px={px} className="pnl-ico" cacheKey={panelIconKey("part", key, px)} make={() => partGlyphCanvas(cat, id, px)} data={{ "data-icon": key }} />;
}

/** 常用的幾個（樣張 `IP.ICON`）。 */
export const LockGlyph = ({ px = 18 }: { px?: number }) => <PartBare cat="skeleton" id="control" px={px} />;
export const ClockGlyph = ({ px = 16 }: { px?: number }) => <PartBare cat="card" id="cooldown" px={px} />;
export const WarnGlyph = ({ px = 15 }: { px?: number }) => <HudBare id="warn" px={px} />;
export const InfoGlyph = ({ px = 14 }: { px?: number }) => <EventRing id="info" px={px} />;
export const TokenGlyph = ({ px = 15 }: { px?: number }) => <HudBare id="token" px={px} />;

// ---------------- 提示三級 ----------------

export type CalloutTone = "warn" | "lock" | "info";

/** 三級各自的圖示（3.1 第 2 條、2.3）：警告＝HUD `warn`、鎖住＝第④批金鎖、資訊＝事件卡 `info`。 */
function calloutIcon(tone: CalloutTone): ReactNode {
  if (tone === "warn") return <WarnGlyph px={15} />;
  if (tone === "lock") return <LockGlyph px={18} />;
  return <InfoGlyph px={14} />;
}

/**
 * 提示（樣張 `callout()`）：警告琥珀、鎖住紫灰、資訊青；左 3px 色條＋圖示＋內容（粗體結論在前由呼叫端寫），
 * `sub`＝次行（L2），`end`＝右邊（例 (i)）。
 */
export function Callout({
  tone,
  children,
  sub,
  end,
  testId,
}: {
  tone: CalloutTone;
  children: ReactNode;
  sub?: ReactNode;
  end?: ReactNode;
  testId?: string;
}) {
  return (
    <div className={`pnl-callout ${tone}`} role="note" data-tone={tone} data-testid={testId}>
      {calloutIcon(tone)}
      <div className="body">
        {children}
        {sub != null && <span className="sub">{sub}</span>}
      </div>
      {end != null && <span className="end">{end}</span>}
    </div>
  );
}

/** 說明鈕 (i)：事件卡 `info` 圖示＋共用 `<Hint>`（不用原生 title）。 */
export function InfoTip({ text, label }: { text: string; label?: string }) {
  return (
    <Hint text={text}>
      <span className="pnl-tip" tabIndex={0} role="img" aria-label={label ?? text}>
        <InfoGlyph px={14} />
      </span>
    </Hint>
  );
}

// ---------------- 籌碼、標籤 ----------------

/** 數值籌碼（樣張 `chip()`）：圖示＋小標＋亮金數字；0 灰（`zero`）。 */
export function Chip({ icon, label, value, zero = false, testId }: { icon?: ReactNode; label: ReactNode; value?: ReactNode; zero?: boolean; testId?: string }) {
  return (
    <span className={`pnl-chip${zero ? " zero" : ""}`} data-testid={testId}>
      {icon}
      {label}
      {value != null && <b>{value}</b>}
    </span>
  );
}

/** 標籤的樣子（樣張 `.ip-tag`）：實心狀態 `open`／`live`、淡灰 `dim`、提示色 `info`／`lock`／`warn`、正面細框 `mine`；不給＝細框（天數、類別）。 */
export type TagTone = "open" | "live" | "mine" | "dim" | "info" | "lock" | "warn";

export function Tag({ tone, icon, children, testId }: { tone?: TagTone; icon?: ReactNode; children: ReactNode; testId?: string }) {
  return (
    <span className={tone === undefined ? "pnl-tag" : `pnl-tag ${tone}`} data-testid={testId}>
      {icon}
      {children}
    </span>
  );
}

// ---------------- 標頭、分頁內第一行、空狀態 ----------------

/**
 * 面板標頭（樣張 `head()`）：襯線標題＋右上「回到地點圖」。「×」是 `WorldHud` 的正式關閉鈕（`world-hud-panel-close`，
 * 面板鎖住時不畫）；有 `.pnl-fixed` 的面板由 CSS 把它擺到標頭右上（`world-hud.css`）。
 */
export function PanelHead({ heading, onBack, testId }: { heading: ReactNode; onBack?: () => void; testId?: string }) {
  return (
    <div className="pnl-head" data-testid={testId}>
      <h2 className="pnl-title">{heading}</h2>
      <span className="pnl-head-actions">
        {onBack !== undefined && (
          <button type="button" onClick={onBack} data-testid="pnl-back">
            回到地點圖
          </button>
        )}
      </span>
    </div>
  );
}

/** 分頁內容最上面一行（樣張 `.ip-tabline`：原來區塊標頭右邊那些規則標籤、刷新時刻、(i)）；`end` 靠右。 */
export function TabLine({ children, end, testId }: { children?: ReactNode; end?: ReactNode; testId?: string }) {
  return (
    <div className="pnl-tabline" data-testid={testId}>
      {children}
      {end != null && <span className="end">{end}</span>}
    </div>
  );
}

/** 空狀態（虛線框、L3；描框只表示狀態，3.1 第 3 條）。 */
export function EmptyNote({ children, testId }: { children: ReactNode; testId?: string }) {
  return (
    <div className="pnl-empty" data-testid={testId}>
      {children}
    </div>
  );
}

// ---------------- 摺疊（一次只開一個） ----------------

/** 量「最高那一頁」時要強制打開哪一個摺疊（`PanelTabs` 量高度時用；平常是 undefined＝照玩家點的）。 */
const FoldMeasure = createContext<string | null | undefined>(undefined);
export const FoldMeasureProvider = FoldMeasure.Provider;

const FoldName = createContext<string | undefined>(undefined);

/**
 * 一組互斥的摺疊（`FoldGroup`）：同一組的 `<details name>` 一次只開一個（Chrome 120 起原生互斥）；
 * 不支援的瀏覽器由 `closeSiblings` 補（第 5 節第 6 點：補一行 JS，不另寫元件）。
 */
export function FoldGroup({ name, children }: { name: string; children: ReactNode }) {
  return (
    <FoldName.Provider value={name}>
      <div className="pnl-folds">{children}</div>
    </FoldName.Provider>
  );
}

/** 打開一個時把同一組的其他關掉（原生互斥的後備；原生已互斥時這裡什麼都不會做）。 */
export function closeSiblings(e: SyntheticEvent<HTMLDetailsElement>): void {
  const el = e.currentTarget;
  if (!el.open || el.name === "") return;
  const root = el.parentElement;
  if (root === null) return;
  for (const other of Array.from(root.children)) {
    if (other !== el && other instanceof HTMLDetailsElement && other.name === el.name && other.open) other.open = false;
  }
}

/** 一個摺疊（樣張 `fold()`）：摺起來右邊掛狀態標籤（`end`）。 */
export function Fold({ id, summary, end, children, defaultOpen = false, testId }: { id: string; summary: ReactNode; end?: ReactNode; children: ReactNode; defaultOpen?: boolean; testId?: string }) {
  const name = useContext(FoldName);
  const forced = useContext(FoldMeasure);
  const open = forced === undefined ? defaultOpen : forced === id;
  return (
    <details className="pnl-fold" name={name} open={open} onToggle={closeSiblings} data-fold={id} data-testid={testId}>
      <summary>
        {summary}
        {end != null && <span className="end">{end}</span>}
      </summary>
      <div className="pnl-fold-body">{children}</div>
    </details>
  );
}
