// 資訊面板的上方分頁（PNL-1a；docs/art/資訊面板-移植需求.md 2.2 `PanelTabs`／`TabBadge`、3.2 通用規則）：
// - 固定區（`.pnl-fixed`：標頭、籌碼、管整個面板的提示、分頁列）在捲動區頂端 sticky，不跟著捲（樣張放 `PopupFrame` 的 head；
//   面板內容拿不到 `PopupFrame` 的 head，又不准自製 portal，所以用 sticky，行為相同——報告待決 1）；
// - 分頁列四級縮（樣張 `fitTabs`）：`ResizeObserver` 量分頁列寬，加 `fit1`～`fit3`；每個分頁的字寬照粗體預留（`data-t`＋`::after`），
//   切分頁前後分頁列逐像素不動；
// - 面板高度＝所有分頁裡最高的那一頁（每個摺疊輪流打開各量一次，`folds`）：打開時（與面板寬度改變時）量一次，鎖成分頁區的
//   `min-height`；開著時資料變多不重量（第 5 節第 8 點），超過 `popupBox` 的 `maxHeight` 由捲動區捲；
// - 預設分頁照 `pickTab`（第一頁整頁鎖住時改開掛金底數字的）；`initial` 可以指定（從別處的提醒點進來）。
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { Hint } from "./Hint";
import { FoldMeasureProvider, LockGlyph, WarnGlyph } from "./PanelKit";
import { badgeShowsValue, fitClass, fitLevel, pickTab, tabHintText, type FitLevel, type TabBadgeSpec } from "./panelTabRules";

/** 伺服器端（測試的 renderToStaticMarkup）沒有版面：用 useEffect，避免 useLayoutEffect 的警告。 */
const useIsoLayoutEffect = typeof window === "undefined" ? useEffect : useLayoutEffect;

export interface PanelTabDef {
  id: string;
  /** 全名（沿用原區塊名）。 */
  label: string;
  /** 兩字短名（第 1 級）。 */
  short: string;
  /** 16px Q 版圖示（不帶底框）。 */
  icon: ReactNode;
  badge?: TabBadgeSpec | null;
  /** 滑過的名字（例「整備：重閃、溶掉與傳承、誓約」）；省略＝只剩圖示時用全名。 */
  hint?: string;
  /** 這一頁裡的摺疊 id（量最高那一頁時每個輪流打開量一次）。 */
  folds?: readonly string[];
  render(): ReactNode;
}

/** 五種狀態記號（樣張 `badge()`）；滑過的說明掛在分頁上（`tabHintText`），這裡只放 `aria-label`。 */
export function TabBadge({ badge }: { badge: TabBadgeSpec }) {
  if (badge.kind === "lock") {
    return (
      <span className="pnl-tbadge ico" data-badge="lock" aria-label={badge.hint}>
        <LockGlyph px={15} />
      </span>
    );
  }
  if (badge.kind === "warn") {
    return (
      <span className="pnl-tbadge ico" data-badge="warn" aria-label={badge.hint}>
        <WarnGlyph px={13} />
      </span>
    );
  }
  if (badge.kind === "live") return <span className="pnl-tbadge live" data-badge="live" aria-label={badge.hint} />;
  return (
    <span className={`pnl-tbadge ${badge.kind}`} data-badge={badge.kind} aria-label={badge.hint}>
      {badgeShowsValue(badge) ? String(badge.value) : null}
    </span>
  );
}

/** 量分頁列：一級一級套 class，放得下就停（第 3 級＝折兩列）。 */
function measureFit(bar: HTMLElement): FitLevel {
  const set = (lv: FitLevel) => {
    bar.classList.remove("fit1", "fit2", "fit3");
    if (lv !== 0) bar.classList.add(fitClass(lv));
  };
  const lv = fitLevel((l) => {
    set(l);
    return bar.scrollWidth <= bar.clientWidth + 1;
  });
  set(lv);
  return lv;
}

/** 分頁列（樣張 `tabBar`）：`role=tablist`，每個分頁＝圖示＋全名＋短名（CSS 依級數顯示）＋記號。 */
export function TabBar({ tabs, active, onPick, testId }: { tabs: readonly PanelTabDef[]; active: string; onPick(id: string): void; testId?: string }) {
  const bar = useRef<HTMLDivElement>(null);
  const [fit, setFit] = useState<FitLevel>(0);
  const refit = useCallback(() => {
    if (bar.current !== null) setFit(measureFit(bar.current));
  }, []);
  const sig = tabs.map((t) => `${t.id}|${t.label}|${t.short}|${t.badge?.kind ?? ""}|${t.badge?.value ?? ""}`).join(",");
  useIsoLayoutEffect(refit, [sig, refit]);
  useEffect(() => {
    const el = bar.current;
    if (el === null || typeof ResizeObserver === "undefined") return undefined;
    let width = el.clientWidth;
    const ro = new ResizeObserver(() => {
      if (Math.abs(el.clientWidth - width) < 0.5) return;
      width = el.clientWidth;
      refit();
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [refit]);
  const cls = ["pnl-tabbar", fitClass(fit)].filter((c) => c !== "").join(" ");
  return (
    <div ref={bar} className={cls} role="tablist" data-fit={fit} data-testid={testId}>
      {tabs.map((t) => {
        const on = t.id === active;
        return (
          <Hint key={t.id} text={tabHintText(t, fit)}>
            <button
              type="button"
              role="tab"
              aria-selected={on}
              aria-label={t.label}
              className={on ? "pnl-tab on" : "pnl-tab"}
              data-tab={t.id}
              onClick={() => onPick(t.id)}
            >
              {t.icon}
              <span className="lbl" data-t={t.label}>
                {t.label}
              </span>
              <span className="lbl-s" data-t={t.short}>
                {t.short}
              </span>
              {t.badge != null && <TabBadge badge={t.badge} />}
            </button>
          </Hint>
        );
      })}
    </div>
  );
}

/** 一頁要量幾種樣子：沒有摺疊＝一種；有摺疊＝每個摺疊打開各一種（一次只開一個）。 */
export function paneVariants(tab: Pick<PanelTabDef, "id" | "folds">): { key: string; fold: string | null }[] {
  const folds = tab.folds ?? [];
  if (folds.length === 0) return [{ key: tab.id, fold: null }];
  return folds.map((f) => ({ key: `${tab.id}:${f}`, fold: f }));
}

/**
 * 鎖住的分頁區高度（PNL-1b）：最高那一頁超過 `maxHeight` 時，只鎖到捲動區放得下的高度（扣掉量的時候超出的量），
 * 不然每一頁（連很短的頁）都會多出一段要捲的空白；比較高的那幾頁照樣在捲動區裡捲（3.2 第 8 條「不超過 maxHeight」）。
 */
export function cappedLock(measured: number, panes: number, overflow: number): number {
  if (overflow <= 0) return measured;
  return Math.max(0, Math.min(measured, Math.floor(Math.max(measured, panes) - overflow)));
}

/** 捲動區超出多少（不算下緣漸隱那塊 sticky 色塊，`theme.css` 的 `.ui-popup-body::after`）。 */
function scrollOverflow(body: HTMLElement): number {
  const after = getComputedStyle(body, "::after");
  const fade = after.content === "none" || after.display === "none" ? 0 : Number.parseFloat(after.height) || 0;
  return body.scrollHeight - fade - body.clientHeight;
}

/** 捲動區（`PopupFrame` 的 `.ui-popup-body`）；不在框裡＝最近的父元素。 */
type Scroller = { scrollTop: number };
type ScrollHost = { closest(sel: string): unknown; parentElement: unknown } | null;

/**
 * 切分頁時把捲動位置歸零（PNL-1a 美術驗收必修 1：捲到底再換頁，新頁第一行會縮在固定區下面）；
 * 只在真的換頁時（`next !== prev`），同一頁內不動。回傳有沒有歸零。
 */
export function resetScrollOnSwitch(root: ScrollHost, prev: string, next: string): boolean {
  if (root === null || prev === next) return false;
  const box = (root.closest(".ui-popup-body") ?? root.parentElement) as Scroller | null;
  if (box == null || typeof box.scrollTop !== "number" || box.scrollTop === 0) return false;
  box.scrollTop = 0;
  return true;
}

/**
 * 有分頁的面板本體：固定區（`head`＋分頁列）＋分頁內容。只有一個分頁時不畫分頁列（2～5 個才拆，3.2 第 3 條）。
 */
export function PanelTabs({ tabs, head, initial, testId }: { tabs: readonly PanelTabDef[]; head?: ReactNode; initial?: string | null; testId?: string }) {
  const [picked, setPicked] = useState<string | null>(() => (initial != null && tabs.some((t) => t.id === initial) ? initial : null));
  const active = tabs.find((t) => t.id === picked) ?? tabs.find((t) => t.id === pickTab(tabs)) ?? tabs[0];
  const root = useRef<HTMLDivElement>(null);
  const measureBox = useRef<HTMLDivElement>(null);
  /* 只在瀏覽器量（伺服器端的靜態輸出只畫目前分頁） */
  const [measuring, setMeasuring] = useState(() => typeof window !== "undefined");
  const [locked, setLocked] = useState<number | null>(null);
  const shape = tabs.map((t) => `${t.id}:${(t.folds ?? []).join("+")}`).join(",");
  useIsoLayoutEffect(() => {
    setMeasuring(typeof window !== "undefined");
  }, [shape]);
  useIsoLayoutEffect(() => {
    if (!measuring) return;
    const box = measureBox.current;
    if (box !== null) {
      const body = root.current?.closest(".ui-popup-body") ?? null;
      const panes = box.parentElement?.getBoundingClientRect().height ?? 0;
      setLocked(cappedLock(Math.ceil(box.getBoundingClientRect().height), panes, body instanceof HTMLElement ? scrollOverflow(body) : 0));
    }
    setMeasuring(false);
  }, [measuring]);
  useEffect(() => {
    const el = root.current;
    if (el === null || typeof ResizeObserver === "undefined") return undefined;
    let width = el.clientWidth;
    let frame = 0;
    const ro = new ResizeObserver(() => {
      if (Math.abs(el.clientWidth - width) < 0.5) return;
      width = el.clientWidth;
      /* 等一格再量（PNL-1b）：視窗縮放時面板的 maxHeight 和寬度可能不在同一格更新，太早量會把鎖高壓錯 */
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => setMeasuring(true));
    });
    ro.observe(el);
    return () => {
      cancelAnimationFrame(frame);
      ro.disconnect();
    };
  }, []);
  if (active === undefined) return null;
  const many = tabs.length > 1;
  return (
    <div ref={root} className="pnl-tabs" data-testid={testId} data-tab={active.id}>
      <div className="pnl-fixed">
        {head}
        {many && <TabBar tabs={tabs} active={active.id} onPick={(id) => { resetScrollOnSwitch(root.current, active.id, id); setPicked(id); }} testId={testId !== undefined ? `${testId}-tabs` : undefined} />}
      </div>
      <div className="pnl-panes" style={locked !== null ? { minHeight: locked } : undefined} data-locked={locked ?? undefined}>
        {measuring ? (
          <div ref={measureBox} className="pnl-measure" aria-hidden="true">
            {tabs.flatMap((t) =>
              paneVariants(t).map((v) => (
                <div key={v.key} className="pnl-pane" data-variant={v.key}>
                  <FoldMeasureProvider value={v.fold}>{t.render()}</FoldMeasureProvider>
                </div>
              )),
            )}
          </div>
        ) : (
          <div className="pnl-pane" role={many ? "tabpanel" : undefined} data-pane={active.id}>
            {active.render()}
          </div>
        )}
      </div>
    </div>
  );
}
