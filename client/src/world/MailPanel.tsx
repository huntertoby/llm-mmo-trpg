// 郵寄面板（Phase 6T-1b；docs/art/郵寄外觀.md 第 3 節、樣張 sample/mail.html ②③）：放在共用彈窗（HUD 面板）裡，
// 上方郵差頭像與一句話，三個分頁「寄東西／收件匣 N／退件・過期 N」。
// 規則都在伺服器：能寄的背包物品與灰掉的原因、跑腿費與對方實收（`/mail/quote` 即時算）、寄出前的全部檢查、
// 背包放不下時「領取」灰掉的原因、郵差的台詞與底下的說明句（`world/trade.yaml`）。這裡不寫規則與台詞。
import { useEffect, useMemo, useRef, useState } from "react";
import type { MailActionResponse, MailLetter, MailQuote, MailRecipient, MailSend, MailView, WorldBagItem, WorldInventory } from "../api/types";
import { GearIcon } from "../ui/GearIcon";
import { ItemIcon } from "../ui/ItemIcon";
import { hasItemIcon } from "../render/itemIcon";
import { Hint } from "../ui/Hint";
import { isSubmitEnter } from "../ui/imeEnter";
import "./mail.css";
import { addToDraft, countValue, EMPTY_DRAFT, firstTab, goldValue, letterSub, mailTabs, removeFromDraft, sendableState, sendBody, sendState, setDraftCount, slotsUsed, tabSay, type MailDraft, type MailTab } from "./mailModel";
import { Portrait } from "./StoryIcons";
import { fieldHeroInput, HeroFace } from "../ui/heroFace";

/** 面板用到的 API（正式畫面是 `api/client.ts`；開發頁傳假資料）。 */
export interface MailApi {
  mail(): Promise<MailView>;
  recipients(): Promise<MailRecipient[]>;
  quote(body: MailSend): Promise<MailQuote>;
  send(body: MailSend): Promise<MailActionResponse>;
  claim(letter: string): Promise<MailActionResponse>;
  refuse(letter: string): Promise<MailActionResponse>;
}

interface Props {
  mailApi: MailApi;
  /** 背包（裝備的外觀圖示照背包的裝備卡）。 */
  inventory: WorldInventory | null;
  busy?: boolean;
  /** 寄出、領取、退回之後：重抓世界畫面（金幣與背包）。 */
  onChanged?(): void;
  /** 一開始的分頁（開發頁截圖用；省略＝有信先看收件匣）。 */
  tab?: MailTab;
  /** 一開始的寄件草稿（開發頁截圖用）。 */
  draft?: MailDraft;
  /** 先畫的資料（測試的靜態輸出用；之後照樣向 `mailApi` 重抓）。 */
  initial?: { mail: MailView; recipients?: MailRecipient[]; quote?: MailQuote | null };
}

/** 金幣小圖示（樣張的金色圓幣加墨線）。 */
export function CoinGlyph({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" aria-hidden="true" className="mail-coin">
      <circle cx="10" cy="10" r="8.2" fill="#e8bb48" stroke="#1c1712" strokeWidth="1.4" />
      <circle cx="10" cy="10" r="5.2" fill="#f6dc80" />
      <path d="M10 7.2 V12.8" stroke="#8a6a1a" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

function gearCard(inventory: WorldInventory | null, id: string) {
  return (inventory?.gear_cards ?? []).find((c) => c.item.id === id) ?? null;
}

/**
 * 背包或附件的一格：裝備用裝備圖示，物品用 Q 版物品圖示（QI-7；32、背包框），都沒有（表裡沒有的物品、沒有裝備卡的裝備）時退回金色小方塊；
 * 名稱與個數照舊。小牌的高度和裝備圖示格對齊（6T-1c，美術 PM 決定 B）。`noCount`：附件格裡個數另用數量框顯示。
 */
function Thing({ row, count, inventory, dim, tag, noCount }: { row: WorldBagItem; count?: number; inventory: WorldInventory | null; dim?: boolean; tag?: string | null; noCount?: boolean }) {
  const gear = row.gear === true ? gearCard(inventory, row.item) : null;
  return (
    <span className={`mail-thing${dim === true ? " dim" : ""}${row.gear === true ? " gear" : ""}`} data-thing={row.item}>
      {gear !== null ? (
        <GearIcon look={gear.item.appearance} slot={gear.slot} size={32} label={gear.item.name_zh} />
      ) : row.gear !== true && hasItemIcon(row.item, row.color) ? (
        <ItemIcon id={row.item} size={32} frame="bag" color={row.color} rare={row.rare} />
      ) : (
        <span className="mail-thing-mark" aria-hidden="true" />
      )}
      <span className="mail-thing-name">{row.name_zh}</span>
      {row.gear !== true && noCount !== true && <b className="mail-thing-count">×{count ?? row.count}</b>}
      {tag != null && <em className="mail-thing-tag" data-testid="mail-bound-tag">{tag}</em>}
    </span>
  );
}

/**
 * 附件格裡可堆疊物品的數量（6T-1c，玩法 PM 3.5 acfc999f）：± 按鈕與數字框，上限是背包裡的數量（`row.count`）。
 * 打字時先照打的字顯示，離開框或按 Enter 時夾在 1～上限。
 */
function CountBox({ row, count, busy, onCount }: { row: WorldBagItem; count: number; busy: boolean; onCount(n: number): void }) {
  const [text, setText] = useState(String(count));
  useEffect(() => setText(String(count)), [count]);
  const commit = () => {
    const n = countValue(text);
    onCount(Number.isNaN(n) ? count : n);
    setText(String(count));
  };
  return (
    <span className="mail-count-box" data-testid={`mail-count-${row.item}`}>
      <Hint text={count <= 1 ? "至少 1 個（要拿掉按 ×）" : "少寄 1 個"} prefer="below">
        <button type="button" className="mail-step" disabled={busy || count <= 1} onClick={() => onCount(count - 1)} aria-label={`${row.name_zh}少 1 個`} data-testid={`mail-dec-${row.item}`}>
          −
        </button>
      </Hint>
      <input
        type="text"
        inputMode="numeric"
        value={text}
        disabled={busy}
        aria-label={`${row.name_zh}的個數（最多 ${row.count}）`}
        onChange={(e) => {
          const raw = e.target.value.replace(/[^\d]/g, "");
          setText(raw);
          const n = countValue(raw);
          if (!Number.isNaN(n)) onCount(n);
        }}
        onBlur={commit}
        onKeyDown={(e) => {
          if (isSubmitEnter(e)) commit();
        }}
        data-testid={`mail-count-input-${row.item}`}
      />
      <Hint text={count >= row.count ? `背包裡只有 ${row.count} 個` : "多寄 1 個"} prefer="below">
        <button type="button" className="mail-step" disabled={busy || count >= row.count} onClick={() => onCount(count + 1)} aria-label={`${row.name_zh}多 1 個`} data-testid={`mail-inc-${row.item}`}>
          ＋
        </button>
      </Hint>
      <span className="mail-count-max">／{row.count}</span>
    </span>
  );
}

function SendTab({ mail, mailApi, inventory, busy, initial, seed, onDone }: { mail: MailView; mailApi: MailApi; inventory: WorldInventory | null; busy: boolean; initial: MailDraft; seed?: { recipients?: MailRecipient[]; quote?: MailQuote | null }; onDone(res: MailActionResponse): void }) {
  const [draft, setDraft] = useState<MailDraft>(initial);
  const [goldText, setGoldText] = useState(initial.gold > 0 ? String(initial.gold) : "");
  const [recipients, setRecipients] = useState<MailRecipient[] | null>(seed?.recipients ?? null);
  const [quote, setQuote] = useState<MailQuote | null>(seed?.quote ?? null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    mailApi.recipients().then(
      (r) => live && setRecipients(r),
      () => live && setRecipients([]),
    );
    return () => {
      live = false;
    };
  }, [mailApi]);
  const body = useMemo(() => sendBody(draft), [draft]);
  const bodyKey = JSON.stringify(body);
  const seq = useRef(0);
  useEffect(() => {
    // 寄件前的檢查與跑腿費：草稿一改就問伺服器（不寫日誌）；舊的回應晚到就丟掉
    if (body === null) {
      setQuote(null);
      return undefined;
    }
    const n = ++seq.current;
    const timer = window.setTimeout(() => {
      mailApi.quote(body).then(
        (q) => n === seq.current && setQuote(q),
        () => n === seq.current && setQuote(null),
      );
    }, 120);
    return () => window.clearTimeout(timer);
  }, [bodyKey, mailApi]);
  const state = sendState(draft, quote, mail.here, mail.here_problem_zh ?? null);
  const attached: { row: WorldBagItem; count?: number }[] = [
    ...Object.entries(draft.items).flatMap(([id, n]) => {
      const row = mail.sendable.find((s) => s.item === id);
      return row === undefined ? [] : [{ row, count: n }];
    }),
    ...draft.gear.flatMap((id) => {
      const row = mail.sendable.find((s) => s.item === id);
      return row === undefined ? [] : [{ row }];
    }),
  ];
  const empties = Math.max(0, mail.max_attachments - attached.length);
  const send = () => {
    if (body === null || !state.ok) return;
    setError(null);
    mailApi.send(body).then(
      (res) => {
        setDraft({ ...EMPTY_DRAFT, to: draft.to });
        setGoldText("");
        onDone(res);
      },
      (e: unknown) => setError(e instanceof Error ? e.message : String(e)),
    );
  };
  return (
    // 6T-1d（6T-1c 檢查小修 3）：「寄出」那一列移到兩欄格線外面，黏在面板捲動區底部（不捲動也看得到）
    <div className="mail-send-wrap">
    <div className="mail-send" data-testid="mail-send">
      <section className="mail-sec mail-to">
        <div className="mail-sec-title">1　寄給誰</div>
        {recipients === null ? (
          <div className="muted small">讀取中…</div>
        ) : recipients.length === 0 ? (
          <div className="muted small">還沒有可以寄的對象。</div>
        ) : (
          <ul className="mail-people">
            {recipients.map((r) => (
              <li key={r.character_id}>
                <Hint text={r.can_receive ? `寄給${r.name_zh}` : (r.problem_zh ?? "不能收信")}>
                  <button
                    type="button"
                    className={`mail-person${draft.to === r.character_id ? " on" : ""}`}
                    aria-pressed={draft.to === r.character_id}
                    disabled={busy}
                    onClick={() => setDraft({ ...draft, to: r.character_id })}
                    data-testid={`mail-to-${r.character_id}`}
                  >
                    <RecipientFace r={r} region={mail.postman?.region ?? null} />
                    <span>
                      <b>{r.name_zh}</b>
                      <span className="mail-sub">
                        {r.place_zh}・Lv {r.level}
                      </span>
                      {!r.can_receive && <span className="mail-warn">{r.problem_zh}</span>}
                    </span>
                  </button>
                </Hint>
              </li>
            ))}
          </ul>
        )}
        <div className="mail-hint">只列別的帳號的角色；自己帳號的角色不能互寄。</div>
      </section>
      <div className="mail-send-main">
      <section className="mail-sec mail-things">
        <div className="mail-sec-title">2　要寄的東西</div>
        <div className="mail-slots" data-testid="mail-slots">
          {attached.map(({ row, count }) =>
            row.gear === true || count === undefined ? (
              <Hint key={row.item} text="點了拿掉" prefer="below">
                <button type="button" className="mail-slot full" disabled={busy} onClick={() => setDraft(removeFromDraft(draft, row.item))} data-testid={`mail-slot-${row.item}`}>
                  <Thing row={row} inventory={inventory} />
                </button>
              </Hint>
            ) : (
              <span key={row.item} className="mail-slot full stack" data-testid={`mail-slot-${row.item}`}>
                <Thing row={row} inventory={inventory} noCount />
                <CountBox row={row} count={count} busy={busy} onCount={(n) => setDraft(setDraftCount(draft, row, n))} />
                <Hint text="拿掉這一格" prefer="below">
                  <button type="button" className="mail-slot-x" disabled={busy} onClick={() => setDraft(removeFromDraft(draft, row.item))} aria-label={`拿掉${row.name_zh}`} data-testid={`mail-remove-${row.item}`}>
                    ×
                  </button>
                </Hint>
              </span>
            ),
          )}
          {Array.from({ length: empties }, (_, i) => (
            <span key={`empty-${i}`} className="mail-slot empty" aria-hidden="true">
              ＋
            </span>
          ))}
        </div>
        <div className="mail-hint">
          從背包點進來（最多 {mail.max_attachments} 格；材料、消耗品可以填數量）。穿過的裝備、獨特與首殺物品不能寄。
        </div>
        <div className="mail-bag" data-testid="mail-bag">
          {mail.sendable.map((row) => {
            const s = sendableState(row);
            const full = !s.ok ? false : row.gear !== true ? (draft.items[row.item] ?? 0) >= row.count : draft.gear.includes(row.item);
            const noRoom = s.ok && slotsUsed(draft) >= mail.max_attachments && (draft.items[row.item] ?? 0) === 0 && !draft.gear.includes(row.item);
            const tip = !s.ok ? `${row.name_zh}：${s.reason ?? "不能寄"}` : noRoom ? `附件最多 ${mail.max_attachments} 格` : full ? "已經全部放進附件" : `放進附件（${row.name_zh}）`;
            return (
              <Hint key={row.item} text={tip}>
                <button
                  type="button"
                  className={`mail-bag-cell${s.ok ? "" : " locked"}`}
                  disabled={busy || !s.ok || full || noRoom}
                  onClick={() => setDraft(addToDraft(draft, row, mail.max_attachments))}
                  data-testid={`mail-bag-${row.item}`}
                  data-locked={s.ok ? undefined : "1"}
                >
                  <Thing row={row} inventory={inventory} dim={!s.ok} tag={s.ok ? null : s.reason} />
                </button>
              </Hint>
            );
          })}
          {mail.sendable.length === 0 && <span className="muted small">背包是空的。</span>}
        </div>
      </section>
      <div className="mail-row">
      <section className="mail-sec mail-gold">
        <div className="mail-sec-title">3　金幣（可不寄）</div>
        <label className="mail-gold-box">
          <input
            type="text"
            inputMode="numeric"
            value={goldText}
            placeholder="0"
            disabled={busy}
            aria-label="寄出的金幣"
            onChange={(e) => {
              setGoldText(e.target.value.replace(/[^\d]/g, ""));
              setDraft({ ...draft, gold: goldValue(e.target.value) });
            }}
            data-testid="mail-gold"
          />
          <CoinGlyph size={20} />
        </label>
        <span className="mail-tax" data-testid="mail-tax">
          {quote !== null && quote.tax_zh !== "" ? quote.tax_zh : `身上 ${mail.gold} 金幣`}
        </span>
      </section>
      <section className="mail-sec mail-note">
        <div className="mail-sec-title">4　留言</div>
        <input
          type="text"
          value={draft.note}
          maxLength={mail.note_max}
          disabled={busy}
          placeholder="一行留言（可不寫）"
          aria-label="留言"
          onChange={(e) => setDraft({ ...draft, note: e.target.value })}
          data-testid="mail-note"
        />
        <span className="mail-count">
          {[...draft.note].length}／{mail.note_max}
        </span>
      </section>
      </div>
      <section className="mail-sec mail-check" data-testid="mail-check">
        <div className="mail-sec-title">寄出前檢查</div>
        {draft.to === null ? (
          <div className="mail-problem">先選收件人</div>
        ) : quote === null ? (
          <div className="muted small">檢查中…</div>
        ) : quote.ok ? (
          <div className="mail-ok" data-testid="mail-check-ok">
            ✓ 全部通過（對方的等級上限、背包空位、{mail.min_level} 級門檻）
          </div>
        ) : (
          <ul className="mail-problems" data-testid="mail-problems">
            {quote.problems.map((p) => (
              <li key={`${p.code}-${p.text_zh}`} className="mail-problem" data-code={p.code}>
                ✗ {p.text_zh}
              </li>
            ))}
          </ul>
        )}
        {quote?.line_zh != null && <div className="mail-line small">{quote.line_zh}</div>}
        {quote?.season_warning_zh != null && <div className="mail-warn small">{quote.season_warning_zh}</div>}
      </section>
      </div>
    </div>
      {/* 6T-1c（美術 PM 小修 5）：說明小字放在「寄出」左邊同一列，「寄出」的說明卡（貼在按鈕上方）不會蓋到它 */}
      <div className="mail-actions" data-testid="mail-actions">
        <div className="mail-hint mail-send-note" data-testid="mail-send-note">
          {mail.send_note_zh}
        </div>
        {error !== null && <span className="mail-warn">{error}</span>}
        {/* 6T-1c（美術 PM 小修 5）：「寄出」不再掛說明卡（貼在按鈕上方會蓋到上面的檢查結果與說明小字）；
            不能寄的原因已全部列在「寄出前檢查」裡 */}
        <span className="mail-btn-wrap">
          <button type="button" className="primary mail-send-btn" disabled={busy || !state.ok} onClick={send} aria-label={state.ok ? "寄出（同時從背包拿掉）" : `還不能寄：${state.reason ?? ""}`} data-testid="mail-send-btn">
            寄出
          </button>
        </span>
      </div>
    </div>
  );
}

/**
 * 收件人頭像（QK-9b，美術 PM QK-9 檢查第 4 題）：收件人自己的 Q 版頭像（同角色清單 `HeroFace`：種族、外觀選項、裝備；框色＝出身區）；
 * 伺服器沒給外觀的舊資料才畫灰色剪影。
 */
export function RecipientFace({ r, region, size = 36 }: { r: MailRecipient; region: string | null; size?: number }) {
  const input = fieldHeroInput(r.hero_look);
  if (input === null) return <Portrait portrait={null} region={region} size={size} label={r.name_zh} />;
  return <HeroFace input={input} realm={r.origin_realm ?? null} size={size} label={r.name_zh} />;
}

function LetterRow({ letter, returned, region, inventory, busy, onClaim, onRefuse }: { letter: MailLetter; returned: boolean; region: string | null; inventory: WorldInventory | null; busy: boolean; onClaim(): void; onRefuse(): void }) {
  return (
    <li className="mail-letter" data-testid={`mail-letter-${letter.id}`} data-status={letter.status_zh}>
      <Portrait portrait={null} region={region} size={44} label={letter.sender_name} />
      <div className="mail-letter-main">
        <b>{returned ? `寄給 ${letter.recipient_name}` : letter.sender_name}</b>
        <span className="mail-sub">{letterSub(letter, returned)}</span>
        {letter.note !== "" && <span className="mail-letter-note">「{letter.note}」</span>}
      </div>
      <div className="mail-letter-things">
        {letter.items.map((i) => (
          <span key={i.item} className={`mail-thing mail-thing-chip${hasItemIcon(i.item, i.color) ? " has-icon" : ""}`}>
            {hasItemIcon(i.item, i.color) ? <ItemIcon id={i.item} size={32} frame="bag" color={i.color} rare={i.rare} /> : <span className="mail-thing-mark" aria-hidden="true" />}
            <span className="mail-thing-name">{i.name_zh}</span>
            <b className="mail-thing-count">×{i.count}</b>
          </span>
        ))}
        {letter.gear.map((g) => (
          <Hint key={g.item} text={[g.name_zh, g.origin_zh].filter(Boolean).join("・")}>
            <span className="mail-thing gear">
              <Thing row={g} inventory={inventory} />
            </span>
          </Hint>
        ))}
        {letter.gold > 0 && (
          <span className="mail-letter-gold">
            <CoinGlyph size={18} />
            <b>{letter.gold} 金幣</b>
            <span className="mail-sub">（已扣跑腿費）</span>
          </span>
        )}
      </div>
      {/* 6T-1c（美術 PM 必修 2）：按鈕一列固定在同一個位置（寬：右側；窄：左下），不能領的原因寫在按鈕下面 */}
      <div className="mail-letter-acts">
        <div className="mail-letter-btns">
        {letter.action != null && (
          <Hint text={letter.can_act ? "領取（附件進背包）" : (letter.problem_zh ?? "現在不能領")}>
            <span className="mail-btn-wrap">
              <button type="button" className="primary" disabled={busy || !letter.can_act} onClick={onClaim} data-testid={`mail-claim-${letter.id}`}>
                領取
              </button>
            </span>
          </Hint>
        )}
        {letter.can_refuse && (
          <Hint text="退回寄件人（附件原封不動，跑腿費不退）">
            <span className="mail-btn-wrap">
              <button type="button" disabled={busy} onClick={onRefuse} data-testid={`mail-refuse-${letter.id}`}>
                退回
              </button>
            </span>
          </Hint>
        )}
        </div>
        {letter.problem_zh != null && (
          <span className="mail-warn small" data-testid={`mail-problem-${letter.id}`}>
            {letter.problem_zh}
          </span>
        )}
      </div>
    </li>
  );
}

export function MailPanel({ mailApi, inventory, busy = false, onChanged, tab, draft, initial }: Props) {
  const [mail, setMail] = useState<MailView | null>(initial?.mail ?? null);
  const [open, setOpen] = useState<MailTab | null>(tab ?? null);
  const [line, setLine] = useState<string | null>(null);
  const [events, setEvents] = useState<readonly string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState(false);
  useEffect(() => {
    let live = true;
    mailApi.mail().then(
      (m) => {
        if (!live) return;
        setMail(m);
        setOpen((cur) => cur ?? firstTab(m));
      },
      (e: unknown) => live && setError(e instanceof Error ? e.message : String(e)),
    );
    return () => {
      live = false;
    };
  }, [mailApi]);
  if (mail === null) {
    return (
      <div className="world-mail" data-testid="world-mail">
        {error !== null ? <div className="mail-warn">{error}</div> : <div className="muted small">讀取郵寄…</div>}
      </div>
    );
  }
  const shown = open ?? firstTab(mail);
  const done = (res: MailActionResponse) => {
    setMail(res.mail);
    setLine(res.line_zh ?? null);
    setEvents(res.events);
    onChanged?.();
  };
  const act = (task: Promise<MailActionResponse>) => {
    setActing(true);
    setError(null);
    task.then(done, (e: unknown) => setError(e instanceof Error ? e.message : String(e))).finally(() => setActing(false));
  };
  const postman = mail.postman;
  const say = tabSay(mail, shown, line); // 6T-1c：照分頁換台詞（剛寄出、領了退件時的那句優先，換分頁就清掉）
  const locked = busy || acting;
  const letters = shown === "inbox" ? mail.inbox : mail.returned;
  return (
    <div className="world-mail" data-testid="world-mail" data-tab={shown}>
      <header className="mail-head">
        <Portrait portrait={postman?.portrait ?? null} region={postman?.region ?? null} size={56} label={postman?.name_zh ?? "郵差"} />
        <div className="mail-head-text">
          <h2>郵寄</h2>
          {say !== null && (
            <p className="mail-say" data-testid="mail-say">
              {postman !== null ? `${postman.name_zh}：` : ""}
              {say}
            </p>
          )}
        </div>
        <nav className="mail-tabs" role="tablist" aria-label="郵寄分頁">
          {mailTabs(mail).map((t) => (
            <button key={t.id} type="button" role="tab" aria-selected={shown === t.id} className={`mail-tab${shown === t.id ? " on" : ""}`} onClick={() => {
                setOpen(t.id);
                setLine(null);
              }} data-testid={`mail-tab-${t.id}`}>
              {t.label}
            </button>
          ))}
        </nav>
      </header>
      {!mail.here && mail.here_problem_zh != null && <div className="mail-warn small">{mail.here_problem_zh}</div>}
      {events.length > 0 && (
        <ul className="mail-events" data-testid="mail-events">
          {events.map((e) => (
            <li key={e}>{e}</li>
          ))}
        </ul>
      )}
      {error !== null && <div className="mail-warn">{error}</div>}
      {shown === "send" ? (
        <SendTab mail={mail} mailApi={mailApi} inventory={inventory} busy={locked} initial={draft ?? EMPTY_DRAFT} seed={initial} onDone={done} />
      ) : (
        <>
          {letters.length === 0 ? (
            <div className="muted small mail-empty">{shown === "inbox" ? "沒有你的信。" : "沒有退件或過期的信。"}</div>
          ) : (
            <ul className="mail-letters" data-testid={`mail-${shown}`}>
              {letters.map((l) => (
                <LetterRow
                  key={l.id}
                  letter={l}
                  returned={shown === "returned"}
                  region={mail.postman?.region ?? null}
                  inventory={inventory}
                  busy={locked}
                  onClaim={() => act(mailApi.claim(l.id))}
                  onRefuse={() => act(mailApi.refuse(l.id))}
                />
              ))}
            </ul>
          )}
          <div className="mail-hint mail-footer" data-testid="mail-footer">
            {mail.footer_zh}
          </div>
        </>
      )}
    </div>
  );
}
