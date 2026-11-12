// 開發用：資訊面板共用元件（PNL-1a；開 `client/dev/panel-gallery.html`，pnpm dev 後 /dev/panel-gallery.html?mute=1#bar）；不屬於正式 build。
// 實機一時到不了的樣子用正式元件（`PanelTabs`、`Callout`、`Chip`、`Tag`、`FoldGroup`、`PartyShadowPanel`）與正式樣式畫出來：
// - `#bar`：分頁列四級（內寬 696／486／400／320／250，公告板五頁＋每種記號），框下寫量到第幾級；
// - `#switch`：同一寬度換「目前分頁」，量每個分頁的左右上下緣（最大差，第 ① 級 486、第 ② 級 320）；
// - `#kit`：提示三級、籌碼、標籤、摺疊（同一組一次只開一個）；
// - `#party`：「隊伍與影子」面板（固定資料：主角＋賽倫＋阿岳），外框照正式 `popupBox`（視窗 800×600 時 514 寬）。
// - `#growth`（PNL-2）：「成長與技能」面板（固定資料：一輪營火的主角）；`?case=starter`（入門期、不在城鎮）｜`lv4`（Lv 4 在城鎮、靈感 3、屬性點 2）；
//   `&tab=flash|attr|care|look` 指定分頁、`&fold=reflash|dissolve|oath` 打開整備的摺疊。`#bar` 最後兩列是成長的分頁列（入門期／Lv 4 在城鎮）。
// - `#campfire`（PNL-2）：一輪的營火畫面（`RunCampfire`，fixture `run_campfire.json`），看共用的 `FlashSection` 規則籌碼沒弄壞營火。
// 圖示一張都不新畫：照樣張 `infoPanelsTabs.js` 的 `N_TABS` 用已移植的 Q 版。
import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import type { WorldMyShadow, WorldPartyView, WorldView } from "../api/types";
import { Callout, Chip, ClockGlyph, EventBare, EventRing, Fold, FoldGroup, HudBare, InfoTip, LockGlyph, PanelHead, PartBare, TabLine, Tag, TokenGlyph, WarnGlyph } from "../ui/PanelKit";
import { TabBar, type PanelTabDef } from "../ui/PanelTabs";
import { FIT_NAMES } from "../ui/panelTabRules";
import { PopupFrame } from "../ui/PopupFrame";
import { useRegionTheme } from "../ui/regionTheme";
import { hudLayout, isNarrow, popupBox } from "../world/hud";
import { PartyShadowPanel } from "../world/PartyShadowPanel";
import { growthTabs, WorldGrowth } from "../world/WorldGrowth";
import { pickTab } from "../ui/panelTabRules";
import type { RunResponse } from "../api/types";
import campfire from "../run/fixtures/run_campfire.json";
import { RunCampfire } from "../screens/RunCampfire";
import "../styles/index.css";

/** 公告板五頁（樣張 `N_TABS`；字照改字表 #37～#42）。 */
const BOARD_TABS: PanelTabDef[] = [
  { id: "goals", label: "今日目標", short: "目標", icon: <EventRing id="clue" px={16} />, badge: { kind: "p", value: "0／3", hint: "今日目標完成 0／3" }, render: () => null },
  { id: "bounty", label: "懸賞板", short: "懸賞", icon: <EventBare id="combat" px={16} />, badge: { kind: "n", value: 3, hint: "懸賞中 3" }, render: () => null },
  { id: "sched", label: "賽季時程", short: "時程", icon: <HudBare id="t_telegraph" px={16} />, render: () => null },
  { id: "events", label: "世界事件", short: "事件", icon: <HudBare id="bar_M" px={16} />, badge: { kind: "live", hint: "霧潮入侵 進行中" }, render: () => null },
  { id: "boss", label: "賽季頭目", short: "頭目", icon: <EventBare id="b_portal" px={16} />, badge: { kind: "lock", hint: "封印中" }, render: () => null },
];
/** 隊伍與影子兩頁（還沒存＝琥珀三角）。 */
const PARTY_TABS: PanelTabDef[] = [
  { id: "party", label: "隊伍", short: "隊伍", icon: <HudBare id="t_orders" px={16} />, badge: { kind: "p", value: "3／3", hint: "隊伍 3／3（含主角）" }, render: () => null },
  { id: "shadow", label: "我的影子", short: "影子", icon: <HudBare id="bar_Y" px={16} />, badge: { kind: "warn", hint: "還沒存" }, render: () => null },
];

/** 一條分頁列放在指定內寬的框裡（同面板的深藍底），框下寫量到的級數。 */
function BarBox({ width, tabs, active, label }: { width: number; tabs: PanelTabDef[]; active: string; label: ReactNode }) {
  const box = useRef<HTMLDivElement>(null);
  const [lv, setLv] = useState<string>("");
  useEffect(() => {
    const t = window.setTimeout(() => setLv(box.current?.querySelector(".pnl-tabbar")?.getAttribute("data-fit") ?? ""), 200);
    return () => window.clearTimeout(t);
  });
  return (
    <div className="pg-row">
      <div className="pg-k">
        {label}
        <span className="pg-lv" data-lv={lv}>
          {lv === "" ? "" : `第 ${lv} 級：${FIT_NAMES[Number(lv)]}`}
        </span>
      </div>
      <div ref={box} className="pg-box" style={{ width }}>
        <TabBar tabs={tabs} active={active} onPick={() => undefined} />
      </div>
    </div>
  );
}

function BarScene() {
  return (
    <div className="pg-page" data-scene="bar">
      <h1>分頁列四級（樣子只看寬度；每一級的狀態記號都在）</h1>
      <BarBox width={696} tabs={BOARD_TABS} active="goals" label={<b>內寬 696（面板 720，1600×900）</b>} />
      <BarBox width={486} tabs={BOARD_TABS} active="goals" label={<b>內寬 486（面板 514，800×600）</b>} />
      <BarBox width={400} tabs={BOARD_TABS} active="goals" label={<b>內寬 400</b>} />
      <BarBox width={320} tabs={BOARD_TABS} active="goals" label={<b>內寬 320</b>} />
      <BarBox width={250} tabs={BOARD_TABS} active="goals" label={<b>內寬 250（popupBox 下限）</b>} />
      <BarBox width={486} tabs={PARTY_TABS} active="party" label={<b>隊伍與影子 內寬 486</b>} />
      <BarBox width={486} tabs={GROWTH_STARTER_TABS} active={pickTab(GROWTH_STARTER_TABS) ?? "attr"} label={<b>成長 內寬 486（入門期：閃現整頁鎖住 → 預設開屬性點）</b>} />
      <BarBox width={486} tabs={GROWTH_LV4_TABS} active={pickTab(GROWTH_LV4_TABS) ?? "flash"} label={<b>成長 內寬 486（Lv 4 在城鎮、靈感 3、屬性點 2 → 預設開閃現）</b>} />
    </div>
  );
}

/** 同一寬度、同一組分頁，每一列換一個「目前分頁」，量每個分頁的左右上下緣（樣張 `tabSwitchDemo`）。 */
function SwitchGroup({ width, caption }: { width: number; caption: string }) {
  const root = useRef<HTMLDivElement>(null);
  const [meter, setMeter] = useState("");
  useLayoutEffect(() => {
    const t = window.setTimeout(() => {
      const bars = Array.from(root.current?.querySelectorAll<HTMLElement>(".pnl-tabbar") ?? []);
      const edges = (bar: HTMLElement) => {
        const b = bar.getBoundingClientRect();
        return Array.from(bar.children).map((c) => {
          const r = c.getBoundingClientRect();
          return [r.left - b.left, r.right - b.left, r.top - b.top, r.bottom - b.top];
        });
      };
      const base = edges(bars[0]!);
      let diff = 0;
      for (const bar of bars.slice(1)) edges(bar).forEach((e, i) => e.forEach((v, j) => (diff = Math.max(diff, Math.abs(v - base[i]![j]!)))));
      setMeter(`${bars.length} 種目前分頁、量每個分頁的左右上下緣：最大差 ${diff.toFixed(1)} px（第 ${bars[0]!.dataset.fit} 級）`);
    }, 300);
    return () => window.clearTimeout(t);
  }, []);
  return (
    <div ref={root} className="pg-switch">
      <div className="pg-title">{caption}</div>
      {BOARD_TABS.map((t) => (
        <div key={t.id} className="pg-row">
          <div className="pg-k">目前：{t.label}</div>
          <div className="pg-box" style={{ width }}>
            <TabBar tabs={BOARD_TABS} active={t.id} onPick={() => undefined} />
          </div>
        </div>
      ))}
      <div className="pg-meter" data-meter={meter}>
        {meter}
      </div>
    </div>
  );
}

function SwitchScene() {
  return (
    <div className="pg-page" data-scene="switch">
      <h1>切分頁前後：分頁列左右緣不動</h1>
      <SwitchGroup width={486} caption="公告板　內寬 486（第 ① 級：全部短名）" />
      <SwitchGroup width={320} caption="公告板　內寬 320（第 ② 級：全部只剩圖示）" />
    </div>
  );
}

function KitScene() {
  return (
    <div className="pg-page" data-scene="kit">
      <h1>提示三級、籌碼、標籤、摺疊（一次只開一個）</h1>
      <div className="pg-panel ui-popup rt-frame world-hud-panel" style={{ position: "relative", left: 0, transform: "none", width: 720 }}>
        <div className="ui-popup-body" style={{ padding: "20px 24px" }}>
          <PanelHead heading="成長與技能" onBack={() => undefined} />
          <div className="pnl-chips">
            <Chip icon={<HudBare id="bar_G" px={16} />} label="Lv" value={2} />
            <Chip icon={<HudBare id="rank" px={16} />} label="角色階級" value={1} />
            <Chip icon={<HudBare id="bulb" px={15} />} label="靈感點" value={3} />
            <Chip icon={<PartBare cat="skeleton" id="aura" px={16} />} label="未分配屬性點" value={0} zero />
          </div>
          <Callout tone="warn" end={<InfoTip text="閃現、重閃、溶掉、傳承、重配屬性、立誓只在城鎮與營火（和換技能同一處）。" />}>
            <b>現在不行</b>：這裡不是城鎮或營火
          </Callout>
          <Callout tone="lock">
            <b>閃現</b>：4 級起
          </Callout>
          <Callout tone="info">入門期可以自己配點，正式選定時會照新武器重配一次。</Callout>
          <TabLine end={<Tag tone="dim">升級時每級 +2</Tag>}>
            <span>標籤：</span>
            <Tag tone="open">懸賞中</Tag>
            <Tag tone="live">進行中</Tag>
            <Tag tone="mine">我的</Tag>
            <Tag>第 1～3 天</Tag>
            <Tag tone="info">新手期：教學目標</Tag>
            <Tag tone="lock" icon={<LockGlyph px={14} />}>
              4 級起
            </Tag>
            <Tag tone="warn" icon={<WarnGlyph px={13} />}>
              還沒存
            </Tag>
          </TabLine>
          <TabLine end={<Tag>只在城鎮與營火</Tag>}>
            <span>重閃、溶掉與傳承、誓約</span>
          </TabLine>
          <FoldGroup name="pg-care">
            <Fold id="reflash" summary={<span><b>重閃</b>　把以前的一次變化換掉</span>} end={<Tag tone="dim">還沒有可以重閃的技能</Tag>} defaultOpen>
              <div className="pnl-l2">把一招以前某一次的變化換掉，價格和閃現相同。</div>
            </Fold>
            <Fold id="dissolve" summary={<span><b>溶掉或傳承</b>　二選一，舊技能會消失</span>} end={<Tag tone="lock" icon={<LockGlyph px={14} />}>4 級起</Tag>}>
              <div className="pnl-l2">選一招舊技能，然後二選一：溶掉或傳承。</div>
            </Fold>
            <Fold id="oath" summary={<span><b>誓約</b>　同時 1 個，到城鎮或營火才能換</span>} end={<Tag tone="lock" icon={<LockGlyph px={14} />}>正式選定後</Tag>}>
              <div className="pnl-l2">入門期不能立誓，找葛蘭正式選定後開放。</div>
            </Fold>
          </FoldGroup>
          <TabLine>
            <span>小圖示：</span>
            <ClockGlyph px={16} />
            <TokenGlyph px={15} />
            <EventBare id="thread" px={18} />
            <EventBare id="narrator" px={16} />
            <EventBare id="b_rest" px={18} />
          </TabLine>
        </div>
      </div>
    </div>
  );
}

const PARTY: WorldPartyView = {
  members: [
    { name_zh: "旅人", title_zh: "主角", level: 2, mercenary: null },
    { name_zh: "賽倫", title_zh: "盾衛・守護", level: 2, mercenary: "merc_tiebi", ai_zh: "預設（守衛）", backstory_zh: "守印人託付給你的護衛，從霧渡鎮一路跟著你。" },
    { name_zh: "阿岳", title_zh: "獵戶", level: 2, companion: "companion_ayue", ai_zh: "預設（弓手）", note_zh: "劇情夥伴：任務結束後離隊" },
  ],
  max_hired: 2,
  can_hire: false,
  hire_problem_zh: "入門期隊友固定，找葛蘭正式選定後才能雇用其他傭兵",
  mercenaries: [],
  shadows: [],
  ai_choices: [],
  ai: {},
  season_boss_ok: true,
  free_slots: 0,
  companion_zh: "阿岳跟著你（霧渡新手路），佔 1 個隊友位；任務結束後離隊",
} as unknown as WorldPartyView;
const SHADOW = { saved: false, ai_zh: "預設", can_set_ai: false, coins: 0, reports_zh: [] } as unknown as WorldMyShadow;

function useWindowSize(): { width: number; height: number } {
  const [size, setSize] = useState(() => ({ width: window.innerWidth, height: window.innerHeight }));
  useEffect(() => {
    const onResize = () => setSize({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  return size;
}

function PartyScene() {
  useRegionTheme("cloud_ridge");
  const { width: W, height: H } = useWindowSize();
  const layout = hudLayout(W, H - 60, { mates: 2, narrow: isNarrow(W), collapsed: false });
  const view = { character: { hero_look: null, origin_realm: null }, field: null, party: PARTY, my_shadow: SHADOW } as unknown as WorldView;
  return (
    <div className="world-hud-stage" style={{ position: "relative", marginTop: 60, height: H - 60, background: "#20283a" }} data-scene="party">
      <PopupFrame placement={{ kind: "hud", box: popupBox(layout, 720) }} className="world-hud-panel" label="隊伍與影子" testId="world-hud-panel">
        <button type="button" className="world-hud-panel-close" aria-label="關閉面板（Esc）" data-testid="world-hud-panel-close">
          ×
        </button>
        <PartyShadowPanel view={view} busy={false} onAct={() => undefined} onClose={() => undefined} />
      </PopupFrame>
    </div>
  );
}

/** 成長面板的固定資料（PNL-2）：主角＝一輪營火的 fixture；入門期與 Lv 4 在城鎮兩種。 */
type GrowthCase = "starter" | "lv4";
function growthView(kind: GrowthCase): WorldView {
  const hero = (campfire as unknown as RunResponse).hero;
  const starter = kind === "starter";
  const insight = starter ? 1 : 3;
  const points = starter ? 0 : 2;
  const blocked = starter ? "這裡不是城鎮或營火" : null;
  return {
    character: {
      character_id: "dev",
      level: starter ? 2 : 4,
      attribute_points: points,
      race: "human",
      look: {},
      look_change_zh: starter ? "只有在主城能改外觀" : null,
      free_race_change: true,
      free_race_change_zh: starter ? "正式選定武器與關鍵字之前不能換種族" : null,
      hero_look: null,
      origin_realm: null,
    },
    field: null,
    hero: { ...hero, insight, attribute_points: points },
    limits: starter ? { flash: "到 4 級才能閃現", dissolve: "4 級前不能溶掉技能或傳承", oath: "入門期還不能立誓，找葛蘭正式選定後開放", race: "正式選定武器與關鍵字之前不能換種族" } : {},
    growth: {
      insight,
      skill_tier: starter ? 1 : 2,
      at_service: !starter,
      service_zh: "閃現、重閃、溶掉、傳承、重配屬性、立誓只在城鎮與營火（和換技能同一處）",
      can_allocate: points > 0,
      can_spend: !starter,
      blocked_zh: blocked,
      pending: false,
      can_flash: !starter,
      flash_blocked_zh: starter ? "到 4 級才能閃現" : null,
      starter_note_zh: starter ? "入門期可以自己配點，正式選定時會照新武器重配一次。" : null,
    },
    oath: {
      available: !starter,
      unavailable_zh: starter ? "尚未開放" : null,
      current: null,
      cooldown_until: 0,
      cooldown_zh: null,
      can_swear: false,
      swear_problem_zh: "尚未開放",
      can_release: false,
      templates: [],
    },
  } as unknown as WorldView;
}
const noopChoose = async () => null;
const GROWTH_STARTER_TABS = growthTabs({ view: growthView("starter"), busy: false, onChoose: noopChoose, onAct: noopChoose });
const GROWTH_LV4_TABS = growthTabs({ view: growthView("lv4"), busy: false, onChoose: noopChoose, onAct: noopChoose });

function GrowthScene() {
  useRegionTheme("cloud_ridge");
  const { width: W, height: H } = useWindowSize();
  const q = new URLSearchParams(location.search);
  const kind: GrowthCase = q.get("case") === "lv4" ? "lv4" : "starter";
  const tab = q.get("tab");
  const fold = q.get("fold");
  const layout = hudLayout(W, H - 60, { mates: 2, narrow: isNarrow(W), collapsed: false });
  useEffect(() => {
    if (fold === null) return undefined;
    const t = window.setTimeout(() => {
      const el = document.querySelector<HTMLDetailsElement>(`details[data-fold="${fold}"]`);
      if (el !== null) el.open = true;
    }, 300);
    return () => window.clearTimeout(t);
  }, [fold]);
  return (
    <div className="world-hud-stage" style={{ position: "relative", marginTop: 60, height: H - 60, background: "#20283a" }} data-scene="growth">
      <PopupFrame placement={{ kind: "hud", box: popupBox(layout, 720) }} className="world-hud-panel" label="成長與技能" testId="world-hud-panel">
        <button type="button" className="world-hud-panel-close" aria-label="關閉面板（Esc）" data-testid="world-hud-panel-close">
          ×
        </button>
        <WorldGrowth
          view={growthView(kind)}
          busy={false}
          onChoose={noopChoose}
          onAct={noopChoose}
          onClose={() => undefined}
          initialTab={tab === "flash" || tab === "attr" || tab === "care" || tab === "look" ? tab : null}
        />
      </PopupFrame>
    </div>
  );
}

function CampfireScene() {
  const run = campfire as unknown as RunResponse;
  return (
    <div className="pg-page" data-scene="campfire" style={{ maxWidth: 760 }}>
      <RunCampfire run={run} view={{ screen: "campfire", afterBattle: 1 } as never} busy={false} onChoose={noopChoose} />
    </div>
  );
}

function App() {
  const [scene, setScene] = useState(location.hash.slice(1) || "bar");
  useEffect(() => {
    const onHash = () => setScene(location.hash.slice(1) || "bar");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  if (scene === "switch") return <SwitchScene />;
  if (scene === "kit") return <KitScene />;
  if (scene === "party") return <PartyScene />;
  if (scene === "growth") return <GrowthScene />;
  if (scene === "campfire") return <CampfireScene />;
  return <BarScene />;
}

const style = document.createElement("style");
style.textContent = `
body { background: #101016; color: var(--ui-text); margin: 0; }
.pg-page { padding: 16px 20px; display: flex; flex-direction: column; gap: 14px; }
.pg-page h1 { font-size: 16px; margin: 0; color: var(--ui-gold-hi); }
.pg-row { display: grid; grid-template-columns: 220px auto; gap: 14px; align-items: end; }
.pg-k { font-size: 12.5px; color: #bdb5a2; text-align: right; padding-bottom: 8px; }
.pg-k b { color: var(--ui-text); display: block; }
.pg-lv { display: block; color: #8fd19e; font-size: 11.5px; }
.pg-box { background: var(--ui-navy); border: 1px solid var(--ui-gold-soft); border-radius: 8px; padding: 6px 12px 0; box-sizing: content-box; }
.pg-switch { display: flex; flex-direction: column; gap: 6px; }
.pg-title { font-size: 13px; color: var(--ui-text); }
.pg-meter { font-size: 12.5px; color: #8fd19e; padding-left: 234px; }
`;
document.head.append(style);
createRoot(document.getElementById("root") as HTMLElement).render(<App />);
