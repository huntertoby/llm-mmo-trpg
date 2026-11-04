// 網遊式 HUD 版面 A（Phase 6B-5；docs/art/HUD移植需求.md）：疊在可走動畫面上的四角 HUD。
// 左上主角卡、隊友卡、影子鈕；右上地名條（限制警告）、小地圖、時間天氣、錢；右側任務追蹤；底部功能列；左下浮動提示。
// 面板內容由 WorldScreen 傳進來（沿用現有元件），這裡只負責位置、圖示、說明卡（`Hint`）與單一面板的外框。
// 每一塊的位置由 `hudLayout()` 算（以 1040×624 為基準等比縮放），出口附近的塊變半透明（`fadedBlocks`）。
import type { CSSProperties, ReactNode } from "react";
import type { WorldView } from "../api/types";
import { AudioSettingsPanel } from "../audio/AudioSettingsPanel";
import { Hint } from "../ui/Hint";
import { usePopupMenu } from "../ui/usePopupMenu";
import { DelayTrail, FlipNumber } from "../ui/MotionBits";
import { ItemFly } from "./GainEffects";
import type { TileRect } from "./camera";
import { HudBarIcon, hudBarName, type HudBarKey } from "./HudBarIcons";
import { HudIcon, HudPortrait, type HudIconName } from "./HudIcons";
import {
  BAR_BTN,
  buttonBadge,
  buttonState,
  HUD_TOUCH_ZH,
  hudButtonCard,
  dayPart,
  HUD_BUTTONS,
  mateCards,
  minimapModel,
  ratio,
  restrictions,
  trackedQuests,
  weatherMark,
  type HudBlock,
  type HudButtonCard,
  type HudButtonId,
  type HudButtonState,
  type HudLayout,
  type LiveToast,
  type MiniMap,
} from "./hud";

/** 功能列的定稿圖示（6A-4f；docs/art/HUD功能列圖示.md）。 */
const BUTTON_ICON: Record<HudButtonId, HudBarKey> = {
  bag: "I",
  skills: "K",
  growth: "G",
  quests: "J",
  shadow: "Y",
  notes: "N",
  sneak: "R",
};

/** 滑過說明卡（HUD功能列圖示.md 第 3 節）：標題列（圖示、名稱、快捷鍵）、黃字狀態、說明一句、觸控小字。 */
export function HudBarCard({ k, card }: { k: HudBarKey; card: HudButtonCard }) {
  return (
    <div className="hud-bar-card" data-hud-card={k}>
      <div className="hud-bar-card-head">
        <HudBarIcon k={k} size={24} />
        <span className="name">{hudBarName(k)}</span>
        <span className="key">{k}</span>
      </div>
      <div className="hud-bar-card-status">{card.status}</div>
      <div className="hud-bar-card-desc">{card.desc}</div>
      <div className="hud-bar-card-touch">{HUD_TOUCH_ZH}</div>
    </div>
  );
}

/** 設計尺寸（`hudLayout` 的設計座標）：每塊的內容照這個大小排，再整塊 `scale`。 */
function Block({
  id,
  layout,
  faded,
  children,
  label,
}: {
  id: HudBlock;
  layout: HudLayout;
  faded: readonly HudBlock[];
  children: ReactNode;
  label: string;
}) {
  const r = layout.blocks[id];
  const s = layout.scale;
  const style: CSSProperties = { left: r.left, top: r.top, width: r.width, height: r.height };
  const inner: CSSProperties = { width: r.width / s, height: r.height / s, transform: `scale(${s})` };
  return (
    <div
      className={`world-hud-block world-hud-at-${id}${faded.includes(id) ? " faded" : ""}`}
      style={style}
      data-hud-block={id}
      role="group"
      aria-label={label}
    >
      <div className="world-hud-inner" style={inner}>
        {children}
      </div>
    </div>
  );
}

function Bar({ value, tone, text, height, item }: { value: number; tone: "hp" | "mana" | "xp"; text?: string; height: number; item: string }) {
  return (
    <div className={`world-hud-bar ${tone}${tone === "hp" ? " has-trail" : ""}`} style={{ height }} data-hud={item}>
      {tone === "hp" && <DelayTrail ratio={value} />}
      <div className="fill" style={{ width: `${Math.round(value * 1000) / 10}%` }} />
      {text !== undefined && <span className="text">{text}</span>}
    </div>
  );
}

function Chip({ icon, value, item, hint }: { icon: HudIconName; value: string; item: string; hint: string }) {
  return (
    <Hint text={hint}>
      <span className="world-hud-chip" data-hud={item} tabIndex={0}>
        <HudIcon name={icon} size={15} />
        <span>{value}</span>
      </span>
    </Hint>
  );
}

function HeroCard({ view, onGrowth }: { view: WorldView; onGrowth(): void }) {
  const c = view.character;
  const xpText = c.xp_next === null ? `經驗 ${c.xp}（已到頂）` : `經驗 ${c.xp} / ${c.xp_next}`;
  return (
    <div className="world-hud-hero">
      <Hint text={`${c.name}・${c.weapon_name_zh}${c.race_name_zh !== null ? `・${c.race_name_zh}` : ""}`}>
        <span className="world-hud-face" tabIndex={0} data-hud="portrait">
          <HudPortrait size={62} ring="#c8a868" />
        </span>
      </Hint>
      <Hint text={`等級 Lv ${c.level}`}>
        <span className="world-hud-lv" data-hud="lv" tabIndex={0}>
          Lv <FlipNumber value={c.level} />
        </span>
      </Hint>
      <Hint text={`角色階級 ${c.skill_tier ?? 1}（點了打開成長面板）`}>
        <button type="button" className="world-hud-rank" data-hud="rank" onClick={onGrowth} aria-label="角色階級">
          <HudIcon name="rank" size={18} />
        </button>
      </Hint>
      {c.fatigued && (
        <Hint text="疲憊：上一場全滅，下一場戰鬥開場 HP 打折，打完一場就消失">
          <span className="world-hud-fatigue" data-hud="fatigue" tabIndex={0}>
            疲
          </span>
        </Hint>
      )}
      <div className="world-hud-bars">
        <Hint text={`HP ${c.hp} / ${c.max_hp}：生命值，歸零就會倒下`}>
          <div tabIndex={0}>
            <Bar value={ratio(c.hp, c.max_hp)} tone="hp" text={`${c.hp} / ${c.max_hp}`} height={15} item="hp" />
          </div>
        </Hint>
        <Hint text={`法力 ${c.mana} / ${c.max_mana}：施放法術要花法力，在營火或城鎮回滿`}>
          <div tabIndex={0}>
            <Bar value={ratio(c.mana, c.max_mana)} tone="mana" text={`${c.mana} / ${c.max_mana}`} height={13} item="mana" />
          </div>
        </Hint>
        <Hint text={xpText}>
          <div tabIndex={0}>
            <Bar value={c.xp_next === null ? 1 : ratio(c.xp, c.xp_next)} tone="xp" height={5} item="xp" />
          </div>
        </Hint>
        <div className="world-hud-chips">
          <Chip icon="ration" value={String(c.supplies)} item="supplies" hint={`補給 ${c.supplies} / ${c.max_supplies}：紮營、趕路要花`} />
          <Chip icon="bulb" value={String(c.insight ?? 0)} item="insight" hint={`靈感點 ${c.insight ?? 0}：在成長面板（G）讓技能閃現`} />
        </div>
      </div>
    </div>
  );
}

function Mates({ view, narrow }: { view: WorldView; narrow: boolean }) {
  const mates = mateCards(view);
  return (
    <div className="world-hud-mates" data-hud="party">
      {mates.map((m, i) => (
        <Hint key={i} text={`${m.name}・${m.title}・${m.level} 級（隊友每場開戰都是滿血）`}>
          <div className={`world-hud-mate${narrow ? " narrow" : ""}`} tabIndex={0} data-hud="mate">
            <HudPortrait size={30} ring="#8fb0d0" tone={i + 1} />
            <div className="world-hud-mate-body">
              {!narrow && <span className="name">{m.short}</span>}
              <Bar value={m.hp} tone="hp" height={9} item="mate-hp" />
            </div>
          </div>
        </Hint>
      ))}
    </div>
  );
}

function Dot({ tone }: { tone: "red" | "purple" | "count"; text?: string }) {
  return <span className={`world-hud-dot ${tone}`} />;
}

function IconButton({
  icon,
  size,
  hint,
  item,
  keyLabel,
  badge,
  active = false,
  state,
  rich,
  onClick,
}: {
  /** 舊的 24×24 圖示，或功能列的定稿圖示（`{ bar }`，6A-4f）。 */
  icon: HudIconName | { bar: HudBarKey };
  size: number;
  hint: string;
  item: string;
  keyLabel?: string;
  badge?: { text: string; tone: "red" | "purple" | "count" } | null;
  active?: boolean;
  /** 按鈕狀態（`disabled` 圖示變灰半透明，仍可以按：按了會提示開不了）。 */
  state?: HudButtonState;
  rich?: ReactNode;
  onClick(): void;
}) {
  const st = state ?? (active ? "open" : "normal");
  return (
    <Hint text={hint} rich={rich}>
      <button
        type="button"
        className={`world-hud-btn${active ? " active" : ""}${st === "disabled" ? " disabled" : ""}`}
        data-state={st}
        style={{ width: size, height: size }}
        onClick={onClick}
        aria-label={hint}
        aria-pressed={active}
        data-hud={item}
      >
        {typeof icon === "string" ? <HudIcon name={icon} size={Math.round(size * 0.55)} /> : <HudBarIcon k={icon.bar} size={Math.round(size * 0.76)} />}
        {keyLabel !== undefined && <span className="key">{keyLabel}</span>}
        {badge != null && (badge.tone === "count" ? <span className="world-hud-count">{badge.text}</span> : <Dot tone={badge.tone} />)}
      </button>
    </Hint>
  );
}

/**
 * 齒輪鈕＋設定面板（AU-2；美術 PM 驗收 AU-1 的意見）：目前只有「聲音」一區，和戰鬥「版面」面板裡的聲音區是同一個元件、
 * 同一份設定（`audio` 引擎、localStorage）。點擊式面板：Esc、點外面關閉、同時一張（`usePopupMenu`，6.5.1）。
 */
function SettingsTool() {
  const menu = usePopupMenu();
  return (
    <div className="world-hud-settings" ref={menu.rootRef}>
      <Hint text={menu.open ? null : "設定（聲音）"}>
        <button
          type="button"
          className={`world-hud-btn${menu.open ? " active" : ""}`}
          style={{ width: 30, height: 30 }}
          onClick={menu.toggle}
          aria-label="設定（聲音）"
          aria-expanded={menu.open}
          aria-haspopup="dialog"
          data-hud="settings"
        >
          <HudIcon name="gear" size={17} />
        </button>
      </Hint>
      {menu.open && (
        <div className="top-popup popup-menu world-settings-popup" role="dialog" aria-label="設定" data-testid="world-settings">
          <AudioSettingsPanel />
        </div>
      )}
    </div>
  );
}

function MiniMapView({ map, viewTiles }: { map: MiniMap; viewTiles?: TileRect | null }) {
  const arrow = (dir: string) => (dir === "up" ? "0,-0.9 0.8,0.5 -0.8,0.5" : dir === "down" ? "0,0.9 0.8,-0.5 -0.8,-0.5" : dir === "left" ? "-0.9,0 0.5,0.8 0.5,-0.8" : "0.9,0 -0.5,0.8 -0.5,-0.8");
  return (
    <svg className="world-hud-minimap-svg" viewBox={`-0.5 -0.5 ${map.cols + 1} ${map.rows + 1}`} preserveAspectRatio="xMidYMid meet" aria-hidden="true">
      {map.colors.map((c, i) => (
        <rect key={i} x={i % map.cols} y={Math.floor(i / map.cols)} width={1.02} height={1.02} fill={map.fog[i] === true ? "#1a1814" : c} />
      ))}
      {map.exits.map((e, i) => (
        <polygon key={`x${i}`} points={arrow(e.dir)} transform={`translate(${e.x + 0.5} ${e.y + 0.5}) scale(1.3)`} fill="#f0f0e0" stroke="#2a2a20" strokeWidth={0.15} data-mini="exit" />
      ))}
      {map.dots.map((d, i) => (
        <circle key={`d${i}`} cx={d.x + 0.5} cy={d.y + 0.5} r={d.kind === "me" ? 0.75 : 0.55} className={`mini-${d.kind}`} data-mini={d.kind} />
      ))}
      {viewTiles != null && viewTiles.width > 0 && viewTiles.height > 0 && (
        <rect
          className="mini-view"
          x={viewTiles.x}
          y={viewTiles.y}
          width={viewTiles.width}
          height={viewTiles.height}
          data-mini="view"
        />
      )}
    </svg>
  );
}

function minimapHint(map: MiniMap): string {
  const exits = map.exits.map((e) => e.label).join("、");
  const npcs = map.dots.filter((d) => d.kind === "npc").length;
  return `小地圖：藍＝你、黃＝NPC（${npcs}）、橘＝休息點、青＝傳送石、箭頭＝出口${exits !== "" ? `（往 ${exits}）` : ""}、白框＝畫面看得到的範圍`;
}

export interface WorldHudProps {
  view: WorldView;
  /** 鏡頭目前看得到的格子範圍（6B-6：小地圖上畫白框）。 */
  viewTiles?: TileRect | null;
  layout: HudLayout;
  faded: readonly HudBlock[];
  toasts: readonly LiveToast[];
  trackerCollapsed: boolean;
  onTracker(collapsed: boolean): void;
  /** 功能列的按鈕（含潛行）、影子鈕。 */
  onButton(id: HudButtonId): void;
  onMap(): void;
  /** 區域圖開著（地圖鈕亮框；6C-6）。 */
  mapOpen?: boolean;
  /** 點地名條：開「這裡」（服務、這裡的人）。 */
  onPlace(): void;
  /** 現在開著的面板（給功能列亮框）。 */
  openPanel: string | null;
  /** 面板（同時只有一個）；`null`＝沒開。 */
  panel?: ReactNode;
  /** 面板能不能關（閃現、三選一待選時不能）。 */
  panelLocked?: boolean;
  onClosePanel(): void;
  /** 中上方：遇敵、事件卡（不是面板，處理完才消失）。 */
  center?: ReactNode;
}

export function WorldHud(props: WorldHudProps) {
  const { view, layout, faded } = props;
  const field = view.field;
  const limits = restrictions(view);
  const part = dayPart(view.clock);
  const weather = weatherMark(view.clock.weather_zh);
  const tracked = trackedQuests(view);
  const shadowBadge = buttonBadge(view, "shadow");
  const map = field != null ? minimapModel(field) : null;
  const wallet = view.wallet;
  const s = layout.scale;
  return (
    <div className="world-hud" data-testid="world-hud" data-narrow={layout.narrow ? "1" : "0"}>
      <ItemFly view={view} />
      {props.panel != null && (
        <div className="world-hud-backdrop" data-testid="world-hud-backdrop" onClick={props.panelLocked === true ? undefined : props.onClosePanel} />
      )}
      <Block id="hero" layout={layout} faded={faded} label="主角">
        <HeroCard view={view} onGrowth={() => props.onButton("growth")} />
      </Block>
      <Block id="mates" layout={layout} faded={faded} label="隊友">
        <Mates view={view} narrow={layout.narrow} />
      </Block>
      <Block id="shadow" layout={layout} faded={faded} label="影子">
        <IconButton icon={{ bar: "Y" }} size={36} hint="我的影子（Y）" item="shadow" badge={shadowBadge} onClick={() => props.onButton("shadow")} active={props.openPanel === "shadow"} />
      </Block>
      <Block id="place" layout={layout} faded={faded} label="地名">
        <div className="world-hud-place">
          <Hint text={`${view.here.name_zh}（${view.here.kind_zh}）：點了看這裡的服務與人`}>
            <button type="button" className="world-hud-place-name" onClick={props.onPlace} data-hud="place" aria-pressed={props.openPanel === "place"}>
              <HudIcon name="town" size={15} />
              <span>{field?.name_zh ?? view.here.name_zh}</span>
            </button>
          </Hint>
          {limits.length > 0 && (
            <Hint text={`限制：${limits.join(" ")}`}>
              <span className="world-hud-warn" tabIndex={0} data-hud="limits">
                <HudIcon name="warn" size={15} />
              </span>
            </Hint>
          )}
        </div>
      </Block>
      <Block id="minimap" layout={layout} faded={faded} label="小地圖">
        {map !== null && (
          <Hint text={minimapHint(map)}>
            <div className="world-hud-minimap" tabIndex={0} data-hud="minimap">
              <MiniMapView map={map} viewTiles={props.viewTiles} />
            </div>
          </Hint>
        )}
      </Block>
      <Block id="clock" layout={layout} faded={faded} label="時間天氣">
        <div className="world-hud-clock">
          <Chip icon={part.icon} value={part.char} item="time" hint={`時間 ${view.clock.time_zh}（${view.clock.day_phase_zh}）`} />
          <Chip icon={weather.icon} value={weather.char} item="weather" hint={`天氣：${view.clock.weather_zh}`} />
          <IconButton icon={{ bar: "M" }} size={30} hint={`地圖（M）：${props.mapOpen === true ? "再按一次切換（區域圖 → 大世界圖 → 關閉）" : "看地點、任務標記與傳送石；再按一次看大世界圖"}`} item="map" keyLabel="M" active={props.mapOpen === true} onClick={props.onMap} />
          <SettingsTool />
        </div>
      </Block>
      <Block id="wallet" layout={layout} faded={faded} label="錢">
        <div className="world-hud-wallet">
          <Chip icon="coin" value={(wallet?.gold ?? 0).toLocaleString("en-US")} item="gold" hint={`金幣 ${wallet?.gold ?? 0}`} />
          <Chip icon="token" value={String(wallet?.quest_coins ?? 0)} item="quest-coins" hint={`任務幣 ${wallet?.quest_coins ?? 0}`} />
        </div>
      </Block>
      <Block id="tracker" layout={layout} faded={faded} label="任務追蹤">
        {props.trackerCollapsed ? (
          <IconButton icon="scroll" size={36} hint={`任務追蹤（${tracked.length} 條）：點了展開`} item="tracker" onClick={() => props.onTracker(false)} />
        ) : (
          <div className="world-hud-tracker" data-hud="tracker">
            <div className="head">
              <HudIcon name="scroll" size={14} />
              <span>任務</span>
              <Hint text="收合任務追蹤">
                <button type="button" className="world-hud-fold" onClick={() => props.onTracker(true)} aria-label="收合任務追蹤" data-testid="world-hud-tracker-fold">
                  －
                </button>
              </Hint>
            </div>
            {tracked.length === 0 && <div className="empty">—</div>}
            {tracked.map((t) => (
              <Hint key={t.id} text={`${t.kind === "quest" ? "任務" : "線頭"}：${t.name}・${t.line}（點了打開任務面板）`}>
                <button type="button" className="world-hud-track" onClick={() => props.onButton("quests")} data-hud="tracked">
                  <span className="name">{t.name}</span>
                  <span className="line">{t.line}</span>
                </button>
              </Hint>
            ))}
          </div>
        )}
      </Block>
      <Block id="bar" layout={layout} faded={faded} label="功能列">
        <div className="world-hud-funcs">
          {HUD_BUTTONS.map((b) => {
            const card = hudButtonCard(view, b.id);
            const k = BUTTON_ICON[b.id];
            return (
              <IconButton
                key={b.id}
                icon={{ bar: k }}
                size={BAR_BTN}
                hint={`${b.name}（${b.key.toUpperCase()}）：${card.status}。${card.desc}`}
                rich={<HudBarCard k={k} card={card} />}
                item={`btn-${b.id}`}
                keyLabel={b.key.toUpperCase()}
                badge={buttonBadge(view, b.id)}
                active={b.panel !== null && props.openPanel === b.panel}
                state={buttonState(view, b, props.openPanel)}
                onClick={() => props.onButton(b.id)}
              />
            );
          })}
        </div>
      </Block>
      <Block id="toasts" layout={layout} faded={faded} label="最近發生的事">
        <ul className="world-hud-toasts" data-hud="toasts" aria-live="polite">
          {props.toasts.map(({ toast, fading }) => (
            <li key={toast.seq} className={`world-hud-toast${toast.warn ? " warn" : ""}${fading ? " fading" : ""}`} data-hud="toast">
              <HudIcon name={toast.warn ? "warn" : "notes"} size={13} />
              <span>{toast.text}</span>
            </li>
          ))}
        </ul>
      </Block>
      {props.center != null && (
        <div className="world-hud-center" style={{ top: 8 * s, maxHeight: layout.blocks.bar.top - 16 * s }} data-testid="world-hud-center">
          {props.center}
        </div>
      )}
      {props.panel != null && (
        <div
          className="world-hud-panel"
          role="dialog"
          aria-label="面板"
          data-testid="world-hud-panel"
          data-panel={props.openPanel ?? ""}
          style={{ top: 8 * s, maxHeight: layout.blocks.bar.top - 14 * s }}
        >
          {props.panelLocked !== true && (
            <button type="button" className="world-hud-panel-close" onClick={props.onClosePanel} aria-label="關閉面板（Esc）" data-testid="world-hud-panel-close">
              ×
            </button>
          )}
          {props.panel}
        </div>
      )}
    </div>
  );
}
