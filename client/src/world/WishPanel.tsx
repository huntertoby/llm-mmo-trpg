// 許願池面板（WP-3；docs/phases/PhaseWP計畫.md 第 5 節）：主城點池子或守池人開。資料全讀 `WorldView.wish`。
// 版面照資訊面板的通用規則（docs/art/資訊面板-移植需求.md 3.1、3.2、3.7；提案 11.4）：
// - 上固定區（`PanelTabs` 的 sticky 固定區）：標題＋守池人（寬版對話泡／窄版標題旁一行，同公告板守印人）→ 不能許時「現在不能用：原因」
//   放第一行 → 數值籌碼（任務幣、本週還能許）→ 分頁列（說出願望／從選單挑；LLM 關著只有選單、不畫分頁列）。
// - 中間捲：分頁內容。面板高度＝兩個分頁裡最高的那一頁（`PanelTabs` 量），切分頁外框不跳。
// - 下固定區（`PopupFrame slots` 的 foot）：「前 → 後」（任務幣、本週次數＝代價，三選一＝新；FL-1b 的 `DiffRows`）＋退款說明＋許願鈕。
// 不能許時整個表單灰掉（伺服器的 `available`／`blocked_zh`）；送出、等待、逾時退回選單由 `WorldScreen` 處理。
import { useEffect, useState, type ReactNode } from "react";
import { NowOffNote } from "../ui/ConditionOffNote";
import { Hint } from "../ui/Hint";
import { Callout, Chip, TokenGlyph } from "../ui/PanelKit";
import { PanelTabs, type PanelTabDef } from "../ui/PanelTabs";
import { usePopupSlots } from "../ui/PopupFrame";
import { PopupSlot } from "../ui/PopupSlot";
import { DiffRows, KeywordGlyph } from "../run/FlashChoiceParts";
import { known } from "../render/qIcon/keywords";
import { Portrait } from "./StoryIcons";
import { toggleKeyword, WISH_ZH, wishDiffs, wishModes, wishSubmitBlock, type WishData, type WishMode } from "./wish";

/** 守池人頭像：寬版 36＋對話泡、窄版（面板 < 560）28＋標題旁一行（同公告板守印人 `KEEPER_FACE`）。 */
const KEEPER_FACE = { wide: 36, narrow: 28 } as const;
/** 選單列的關鍵字小圓章（第⑤b 批 Q 版）。 */
const KEYWORD_PX = 20;
/** 空白但佔一行高。 */
const NBSP = String.fromCharCode(0xa0);

/** 送出前等不到 LLM（逾時）或伺服器退回時，自動切到選單並說明（`seq` 變了就重開到選單分頁）。 */
export interface WishFallback {
  seq: number;
  text: string;
}

interface Props {
  wish: WishData;
  busy: boolean;
  fallback: WishFallback | null;
  onWish(mode: WishMode, text: string, keywords: string[]): void;
  onBack?: () => void;
}

function WishHead({ wish: w, onBack }: { wish: WishData; onBack?: () => void }) {
  const sp = w.speaker ?? null;
  const line = w.line_zh ?? "";
  return (
    <>
      <div className="pnl-head" data-testid="wish-head">
        <h2 className="pnl-title">{w.title_zh}</h2>
        {sp !== null && line !== "" && (
          <Hint text={`${sp.name_zh}：${line}`}>
            <span className="pnl-speaker-mini" tabIndex={0} data-testid="wish-keeper-mini">
              <Portrait portrait={sp.portrait} region={sp.region} size={KEEPER_FACE.narrow} label={sp.name_zh} />
              <span className="line">{line}</span>
            </span>
          </Hint>
        )}
        <span className="pnl-head-actions">
          {onBack !== undefined && (
            <button type="button" onClick={onBack} data-testid="pnl-back">
              回到地點圖
            </button>
          )}
        </span>
      </div>
      {sp !== null && line !== "" && (
        <div className="pnl-speaker" data-testid="wish-keeper">
          <Portrait portrait={sp.portrait} region={sp.region} size={KEEPER_FACE.wide} label={sp.name_zh} />
          <div className="pnl-bubble">
            <span className="who">{sp.name_zh}</span>
            {line}
          </div>
        </div>
      )}
      {!w.available && (
        <div className="wish-off" data-testid="wish-blocked">
          <NowOffNote reason={w.blocked_zh ?? ""} />
        </div>
      )}
      <div className="pnl-chips">
        <Chip icon={<TokenGlyph px={15} />} label={WISH_ZH.coins} value={w.coins} zero={w.coins < w.cost} testId="wish-coins" />
        <Chip label={WISH_ZH.left} value={`${w.left}／${w.per_week}`} zero={w.left === 0} testId="wish-left" />
      </div>
    </>
  );
}

/** 都不拿的退款（L3，放在分頁內容最後：資訊放內容後面，3.7 第 3 條）。 */
function RefundNote({ refund }: { refund: number }) {
  return (
    <p className="pnl-l3 wish-refund" data-testid="wish-refund">
      {WISH_ZH.refundNote(refund)}
    </p>
  );
}

function TextPane({ wish: w, text, off, onText }: { wish: WishData; text: string; off: boolean; onText(t: string): void }) {
  return (
    <div className="wish-pane" data-testid="wish-text-pane">
      <p className="pnl-l2 wish-lead">{WISH_ZH.textLead}</p>
      <textarea
        className="wish-input"
        rows={3}
        maxLength={w.text_max_chars}
        value={text}
        placeholder={WISH_ZH.textPlaceholder}
        disabled={off}
        onChange={(e) => onText(e.target.value)}
        aria-label={WISH_ZH.tabText}
        data-testid="wish-text"
      />
      <div className="pnl-l3 wish-count" data-testid="wish-count">
        {text.length}／{w.text_max_chars}
      </div>
      <RefundNote refund={w.refund} />
    </div>
  );
}

function MenuPane({ wish: w, picked, off, note, onPick }: { wish: WishData; picked: readonly string[]; off: boolean; note: string | null; onPick(id: string): void }) {
  return (
    <div className="wish-pane" data-testid="wish-menu-pane">
      {note !== null && (
        <Callout tone="warn" testId="wish-fallback">
          {note}
        </Callout>
      )}
      <p className="pnl-l2 wish-lead">{WISH_ZH.menuLead}</p>
      <ul className="wish-menu" role="group" aria-label={WISH_ZH.tabMenu} data-testid="wish-menu">
        {w.menu.map((k) => {
          const at = picked.indexOf(k.id);
          const full = at < 0 && picked.length >= w.max_keywords;
          return (
            <li key={k.id}>
              <button
                type="button"
                role="checkbox"
                aria-checked={at >= 0}
                className={at >= 0 ? "wish-kw on" : "wish-kw"}
                disabled={off || full}
                onClick={() => onPick(k.id)}
                data-kw={k.id}
                data-testid="wish-kw"
              >
                {known([k.id], 1).length > 0 ? <KeywordGlyph id={k.id} px={KEYWORD_PX} /> : <span className="wish-kw-noicon" aria-hidden="true" />}
                <b className="name">{k.name_zh}</b>
                {at >= 0 && (
                  <span className="pnl-tag open" data-testid="wish-kw-order">
                    {WISH_ZH.pickNth(at + 1)}
                  </span>
                )}
                <span className="desc pnl-l3">{k.description_zh}</span>
              </button>
            </li>
          );
        })}
      </ul>
      <RefundNote refund={w.refund} />
    </div>
  );
}

function WishFoot({ wish: w, block, busy, onSubmit }: { wish: WishData; block: string | null; busy: boolean; onSubmit(): void }) {
  const go = block === null && !busy;
  return (
    <div className={w.available ? "wish-foot" : "wish-foot off"} data-testid="wish-foot">
      <DiffRows changes={wishDiffs(w)} terms={{}} />
      <div className="wish-foot-row">
        {/* 為什麼按不下去：一律佔一行（沒有時空白），切分頁、挑關鍵字時下固定區不跳；不能許時原因只寫在第一行 */}
        <span className="pnl-l3 wish-need" data-testid={block !== null && w.available ? "wish-need" : undefined}>
          {block !== null && w.available ? block : NBSP}
        </span>
        <button type="button" className="primary wish-submit" disabled={!go} onClick={() => go && onSubmit()} data-testid="wish-submit">
          {WISH_ZH.submit}
        </button>
      </div>
    </div>
  );
}

export function WishPanel({ wish: w, busy, fallback, onWish, onBack }: Props) {
  const modes = wishModes(w);
  const forced: WishMode | null = fallback !== null ? "menu" : null;
  const [mode, setMode] = useState<WishMode>(forced ?? modes[0] ?? "menu");
  const [text, setText] = useState("");
  const [picked, setPicked] = useState<string[]>([]);
  const slots = usePopupSlots();
  // 等不到 LLM 或被退回：切到選單分頁（`PanelTabs` 以 `seq` 為 key 重開在選單）
  const seq = fallback?.seq ?? 0;
  useEffect(() => {
    if (seq !== 0) setMode("menu");
  }, [seq]);
  const active: WishMode = modes.includes(mode) ? mode : "menu";
  const off = !w.available;
  const block = wishSubmitBlock(w, active, text, picked);
  const note = fallback?.text ?? null;
  const tabs: PanelTabDef[] = modes.map((m) =>
    m === "text"
      ? { id: "text", label: WISH_ZH.tabText, short: WISH_ZH.tabTextShort, icon: null, render: () => <TextPane wish={w} text={text} off={off} onText={setText} /> }
      : {
          id: "menu",
          label: WISH_ZH.tabMenu,
          short: WISH_ZH.tabMenuShort,
          icon: null,
          render: () => <MenuPane wish={w} picked={picked} off={off} note={note} onPick={(id) => setPicked((cur) => toggleKeyword(cur, id, w.max_keywords))} />,
        },
  );
  const foot: ReactNode = <WishFoot wish={w} block={block} busy={busy} onSubmit={() => onWish(active, text, picked)} />;
  return (
    <div className={off ? "wish-panel off" : "wish-panel"} data-testid="world-hud-wish" data-mode={active} data-available={w.available ? "1" : "0"}>
      <PanelTabs
        key={seq}
        tabs={tabs}
        initial={forced ?? active}
        head={<WishHead wish={w} onBack={onBack} />}
        onTab={(id) => setMode(id === "text" ? "text" : "menu")}
        testId="wish-tabs"
      />
      {slots !== null ? (
        <PopupSlot slots={slots} where="foot">
          {foot}
        </PopupSlot>
      ) : (
        foot
      )}
    </div>
  );
}
