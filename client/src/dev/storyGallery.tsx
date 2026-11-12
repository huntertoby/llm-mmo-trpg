// 開發用：6C-7 的字幕、事件卡、情境判定擲骰與 NPC 頭像（開 `client/dev/story-gallery.html`，pnpm dev 後 /dev/story-gallery.html）。
// 不屬於正式 build；供美術 PM 驗收與截圖。畫面用正式元件與樣式，資料是固定的假資料；NPC 外觀直接讀 `content/world/npcs/*.yaml`。
// `#subtitle`：上方字幕＋NPC 頭像（96／48／28）與地圖紙娃娃對照；`#event`：事件卡（插圖、對話框、選項圖示、情境判定）；
// `#roll`（也可用 `?mode=roll`）：判定結果（兩顆骰的動畫＋顏色；`?t=` 指定動畫已經過的毫秒，不給＝照計時器播）；
// `#icons`：6C-ART3 墨線圖示總表（選項 8、其他 5、六屬性、d20；64／24／18，對照 docs/art/sample/story-icons.html）。
// UI-E1b：`#encounter`：大世界中上方的遇敵卡（正式元件 EncounterPanel，標題「遇敵：地點」、危險類紅帶）；
// `#reaction`：戰鬥的反應詢問視窗（正式元件 DecisionDialog，危險類紅帶）。實機要等敵人行動才碰得到，這裡用固定資料畫出來給美術 PM 看。
// QK-2：`#qportraits`：Q 版頭像總表（37 位、體型、好感五級、種族卡；qPortraitScene.tsx）。
// 6T-1d：`#soot`：五位帶 soot 的頭像（灰鴿、鉚釘、工坊師傅、主城鐵匠、爐叔；外觀直接讀 content，主城鐵匠在遊戲裡沒有頭像）。
import { createRoot } from "react-dom/client";
import { parse } from "yaml";
import type { Glossary, NpcPortrait, Pending, WorldEventView, WorldSituationResult, WorldView } from "../api/types";
import type { UnitNames } from "../battle/units";
import { DecisionDialog } from "../ui/DecisionDialog";
import { useRegionTheme } from "../ui/regionTheme";
import { EncounterPanel } from "../world/WorldPanel";
import { scanCornerIssues } from "./layoutSmoke";
import glossary from "../battle/fixtures/glossary.json";
import { setGlossary } from "../battle/glossary";
import { resolveDoll } from "../render/appearance";
import { renderFigureCanvas } from "../render/paperdoll";
import { EventCard, SituationResultCard } from "../world/EventCard";
import { RankFace } from "../world/FieldHeads";
import { npcFieldLook } from "../world/npcLook";
import { NarratorSubtitle } from "../world/StoryParts";
import { AttrIcon, D20, MiscGlyph, Portrait, SolutionGlyph, type MiscIcon } from "../world/StoryIcons";
import { D20_COLOR } from "../render/storyIconArt";
import { OUTCOME_COLOR, SOLUTION_ICON_ZH, type AttrKey, type SolutionIcon } from "../world/narration";
import cloudYaml from "../../../content/world/npcs/cloud_ridge.yaml?raw";
import ashenYaml from "../../../content/world/npcs/ashen_waste.yaml?raw";
import tradeYaml from "../../../content/world/trade.yaml?raw";
import mercYaml from "../../../content/world/mercenaries.yaml?raw";
import capitalYaml from "../../../content/world/fields/capital/capital.yaml?raw";
import smithyYaml from "../../../content/world/fields/capital/interiors/capital_smithy.yaml?raw";
import bossEncounter from "./fixtures/encounterBoss.json";
import { QPortraitScene } from "./qPortraitScene";
import "../styles/index.css";

setGlossary(glossary as unknown as Glossary);

interface Card {
  id: string;
  name_zh: string;
  portrait?: NpcPortrait;
}
const regions: [string, Card[]][] = [
  ["cloud_ridge", (parse(cloudYaml) as { npcs: Card[] }).npcs],
  ["ashen_waste", (parse(ashenYaml) as { npcs: Card[] }).npcs],
];

const MODE = new URLSearchParams(location.search).get("mode") ?? (decodeURIComponent(location.hash.slice(1)) || "subtitle");
const T = new URLSearchParams(location.search).get("t");

const STORY = {
  text_zh: "霧從河面爬上來，渡口的燈籠一盞盞熄了。一隊商人困在斷橋邊，車輪陷進泥裡。領頭的老人朝你揮手。他說橋下有東西在動。",
  more_zh: "仔細看，泥裡有幾道不屬於人的爪痕，一路延伸到對岸的蘆葦叢。",
  source: "llm" as const,
};

const EVENT: WorldEventView = {
  skeleton: "stranded_caravan",
  location_name_zh: "霧渡鎮・斷橋",
  // UI-E1 追加 9：場景圖照標題的地點（雲嶺的霧渡鎮）；沒有區域時會畫成主城背景
  region: "cloud_ridge",
  actor_zh: "困住的商隊",
  motive_zh: "想在天黑前過河",
  story: STORY,
  who_zh: "",
  want_zh: "",
  obstacle_zh: "",
  stakes_zh: "",
  follows_zh: "商人欠你人情",
  solutions: [
    { index: 0, kind: "situation", kind_zh: "情境判定", note_zh: "查看橋下的爪痕", hint_zh: "", attributes_zh: "感知、智力", template: "inspect", available: true, cost_supplies: 0, can_pay: true },
    { index: 1, kind: "situation", kind_zh: "情境判定", note_zh: "說服商人先卸貨", hint_zh: "", attributes_zh: "意志", template: "persuade", available: true, cost_supplies: 0, can_pay: true },
    { index: 2, kind: "combat", kind_zh: "戰鬥", note_zh: "把橋下的東西引出來打", hint_zh: "", attributes_zh: "", template: null, available: true, cost_supplies: 0, can_pay: true },
    { index: 3, kind: "parley", kind_zh: "交涉", note_zh: "雇船夫繞路", hint_zh: "", attributes_zh: "", template: null, available: true, cost_supplies: 2, can_pay: true, waive_thread: "th1", waive_zh: "商人欠你人情" },
    { index: 4, kind: "abandon", kind_zh: "放棄", note_zh: "", hint_zh: "", attributes_zh: "", template: null, available: true, cost_supplies: 0, can_pay: true },
  ],
  leave_zh: "離開這裡事件就作罷，不留懲罰",
  situation: {
    template: "inspect",
    note_zh: "查看橋下的爪痕",
    attributes_zh: "感知、智力",
    methods_zh: "觀察、推理、追蹤",
    base_dc: 13,
    story: { text_zh: "爪痕很深，邊緣還沾著濕泥。往對岸去的方向，蘆葦倒了一片。", more_zh: "", source: "fallback" },
    facts: [
      { fact: "f1", item: "clue", item_zh: "線索", text_zh: "霧狼在起霧時出沒", insert_zh: "霧狼" },
      { fact: "f2", item: "npc_bond", item_zh: "往來", text_zh: "阿岳教過你看獸跡", insert_zh: "阿岳" },
    ],
  },
  art_url: null,
};

const RESULT: WorldSituationResult = {
  template: "inspect",
  note_zh: "查看橋下的爪痕",
  attribute_zh: "感知",
  method_zh: "追蹤",
  dice: [6, 14],
  mode_zh: "優勢",
  roll: 14,
  attribute_mod: 2,
  care: [
    { item_zh: "線索", text_zh: "霧狼在起霧時出沒", counted: true, reason_zh: "" },
    { item_zh: "往來", text_zh: "阿岳教過你看獸跡", counted: false, reason_zh: "回答裡沒提到" },
  ],
  care_bonus: 1,
  race_bonus: 0,
  total: 17,
  base_dc: 13,
  dc_shift: 0,
  dc: 13,
  outcome: "success",
  outcome_zh: "成功",
  effects_zh: ["經驗 +12", "得到線索：霧狼的巢在蘆葦叢裡"],
  story: { text_zh: "你順著爪痕找到蘆葦叢裡的巢。三頭霧狼正睡著，商隊可以趁現在過河。", more_zh: "巢邊散著幾塊源晶碎片，像是被誰刻意留下的。", source: "llm" },
  source: "fallback",
};

function Doll({ card }: { card: Card }) {
  const look = npcFieldLook({ id: card.id, look: null, portrait: card.portrait ?? null });
  if (look == null || look.doll_look?.creature != null) return <span className="muted small">犬骨架（白）</span>;
  const spec = resolveDoll({ template: look.template_id, dollLook: look.doll_look, team: "ally", summon: false, weaponId: look.weapon_id, weaponClass: look.weapon_class, raceLook: look.race_look as Record<string, unknown> | null });
  const canvas = renderFigureCanvas(spec, "south", false, 2);
  return <img src={canvas?.toDataURL() ?? ""} width={48} height={66} alt="" />;
}

/** 6F-7：`fill` ＝ 鋪滿整個視窗（遇敵卡、反應詢問要照實際視窗寬拍 800／1600；以前固定 1040×720）。 */
function Stage({ children, fill = false }: { children: React.ReactNode; fill?: boolean }) {
  return (
    <div style={{ position: "relative", width: fill ? "100vw" : 1040, height: fill ? "100vh" : 720, overflow: "hidden", background: "radial-gradient(ellipse at 50% 60%, #3e5446, #1c2620 70%)", fontFamily: "sans-serif" }}>
      <div style={{ position: "absolute", inset: 0, backgroundImage: "linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)", backgroundSize: "52px 52px" }} />
      {children}
    </div>
  );
}

const CENTER: React.CSSProperties = { top: 8, maxHeight: 700 };

function SubtitleScene() {
  return (
    <Stage>
      <div className="world-hud-center" style={CENTER}>
        <NarratorSubtitle story={STORY} elapsed={0} />
      </div>
      <div className="panel" style={{ position: "absolute", left: 16, right: 16, bottom: 16, display: "flex", flexDirection: "column", gap: 8 }}>
        <div className="section-title">NPC 頭像（96／48／28）與地圖紙娃娃</div>
        {regions.map(([region, cards]) => (
          <div key={region} style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
            {cards.map((c) => (
              <div key={c.id} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2, width: 100 }}>
                <span className="world-npc-face">
                  <Portrait portrait={c.portrait ?? null} region={region} size={c.id === "granny_du" || c.id === "iron_lady" ? 96 : 48} label={c.name_zh} />
                  <span className="world-npc-mood">
                    <RankFace rank="neutral" size={16} />
                  </span>
                </span>
                <span style={{ display: "flex", gap: 4, alignItems: "flex-end" }}>
                  <Portrait portrait={c.portrait ?? null} region={region} size={28} />
                  <Doll card={c} />
                </span>
                <span className="small">{c.name_zh}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </Stage>
  );
}

function EventScene() {
  return (
    <Stage>
      <div className="world-hud-center" style={CENTER}>
        <EventCard event={EVENT} busy={false} onOpen={() => undefined} onSolve={() => undefined} onAnswer={() => undefined} />
      </div>
    </Stage>
  );
}

/** 遇敵卡的假資料（雲嶺・竹林小徑；只填 EncounterPanel 會讀的欄位）。 */
const ENCOUNTER_VIEW = {
  encounter: {
    location: "bamboo_path",
    location_name_zh: "竹林小徑",
    enemy_level: 2,
    map_name_zh: "竹林",
    weather_zh: "霧",
    day_phase_zh: "傍晚",
    enemies: [
      { name_zh: "霧狼", elite: false, affix_zh: null },
      { name_zh: "霧狼", elite: true, affix_zh: "迅捷" },
      { name_zh: "竹林山賊", elite: false, affix_zh: null },
    ],
    retreat_to_zh: "霧渡鎮",
    fatigued: false,
    hero_hp: 60,
    in_battle: false,
    reinforcements: 0,
    hero_statuses: [],
    opening_zh: ["霧裡先聽見狼嚎：敵人先動"],
    allies_zh: "主角（開場 HP 60）、賽倫、回春",
    battlefield_fallback_zh: null,
  },
} as unknown as WorldView;

function EncounterScene() {
  useRegionTheme("cloud_ridge");
  return (
    <Stage fill>
      <div className="world-hud-center" style={CENTER}>
        <EncounterPanel view={ENCOUNTER_VIEW} busy={false} onAct={() => undefined} onBattle={() => undefined} />
      </div>
    </Stage>
  );
}

/**
 * UI-E3b：Boss 的遇敵卡（實機到不了，開發頁畫）。資料是伺服器對 dev-boss 那場遭遇（雲頂觀、6 級）算出的 `EncounterView`
 * （`fixtures/encounterBoss.json`，含每名的 `look`、`rank`），用正式的 `EncounterPanel` 畫。
 */
const BOSS_VIEW = { encounter: bossEncounter } as unknown as WorldView;

function BossEncounterScene() {
  useRegionTheme("cloud_ridge");
  return (
    <Stage fill>
      <div className="world-hud-center" style={CENTER}>
        <EncounterPanel view={BOSS_VIEW} busy={false} onAct={() => undefined} onBattle={() => undefined} />
      </div>
    </Stage>
  );
}

const NAMES: UnitNames = {
  marker: (id) => (id === "hero" ? "A" : "1"),
  name: (id) => (id === "hero" ? "霜月" : "霧狼"),
  label: (id) => (id === "hero" ? "A 霜月" : "1 霧狼"),
  team: (id) => (id === "hero" ? "ally" : "enemy"),
} as UnitNames;
const PENDING = { kind: "reaction", unit_id: "hero", reaction: "block", trigger_unit_id: "wolf", stamina_cost: 10, mana_cost: 0, hp_cost_permille: 0 } as unknown as Pending;

function ReactionScene() {
  return (
    <Stage fill>
      <DecisionDialog pending={PENDING} rule={null} names={NAMES} eventText="1 霧狼 撲向 A 霜月。" enabled onDecide={() => undefined} />
    </Stage>
  );
}

function RollScene() {
  return (
    <Stage>
      <div className="world-hud-center" style={CENTER}>
        <SituationResultCard result={RESULT} onClose={() => undefined} diceElapsed={T === null ? undefined : Number(T)} />
      </div>
    </Stage>
  );
}

const ICON_SIZES = [64, 24, 18] as const;
const SOLS: readonly SolutionIcon[] = ["combat", "persuade", "sneak", "investigate", "force", "chance", "leave", "trade"];
const MISCS: readonly [MiscIcon, string][] = [["clue", "線索"], ["model_off", "模型關閉"], ["narrator", "說書人"], ["info", "說明"], ["thread", "事件線"]];
const ATTRS: readonly [AttrKey, string][] = [["str", "力量"], ["dex", "敏捷"], ["con", "體質"], ["int", "智力"], ["wis", "感知"], ["wil", "意志"]];

function IconCell({ label, children }: { label: string; children: (size: number) => React.ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4, width: 118 }}>
      <span style={{ display: "flex", gap: 6, alignItems: "center" }}>{ICON_SIZES.map((s) => <span key={s}>{children(s)}</span>)}</span>
      <span className="small">{label}</span>
    </div>
  );
}

function IconsScene() {
  const row: React.CSSProperties = { display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" };
  return (
    <Stage>
      <div className="panel" style={{ position: "absolute", left: 16, right: 16, top: 16, display: "flex", flexDirection: "column", gap: 10 }}>
        <div className="section-title">選項（64／24／18）</div>
        <div style={row}>{SOLS.map((i) => <IconCell key={i} label={SOLUTION_ICON_ZH[i]}>{(s) => <SolutionGlyph icon={i} size={s} />}</IconCell>)}</div>
        <div className="section-title">其他</div>
        <div style={row}>{MISCS.map(([i, zh]) => <IconCell key={i} label={zh}>{(s) => <MiscGlyph icon={i} size={s} />}</IconCell>)}</div>
        <div className="section-title">六屬性</div>
        <div style={row}>{ATTRS.map(([a, zh]) => <IconCell key={a} label={zh}>{(s) => <AttrIcon attr={a} size={s} />}</IconCell>)}</div>
        <div className="section-title">d20（64 寫點數；28 以下不寫字，DC 寫在旁邊）</div>
        <div style={{ ...row, gap: 18 }}>
          <IconCell label="一般">{(s) => <D20 size={s} value={15} />}</IconCell>
          <IconCell label="大成功（金）">{(s) => <D20 size={s} value={20} color={D20_COLOR.crit} />}</IconCell>
          <IconCell label="大失敗（灰）">{(s) => <D20 size={s} value={1} color={D20_COLOR.fumble} />}</IconCell>
          <IconCell label="成功（綠）">{(s) => <D20 size={s} value={17} color={OUTCOME_COLOR.success} />}</IconCell>
          <IconCell label="失敗（紅）">{(s) => <D20 size={s} value={8} color={OUTCOME_COLOR.failure} />}</IconCell>
          <span className="world-dc" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <D20 size={24} />
            <b>13</b>
          </span>
        </div>
      </div>
    </Stage>
  );
}

/** 在 YAML 樹裡找 `id` 符合的節點的頭像（`portrait`／`figure.portrait`／`card.portrait`）。 */
function findPortrait(node: unknown, id: string): NpcPortrait | null {
  if (Array.isArray(node)) {
    for (const n of node) {
      const hit = findPortrait(n, id);
      if (hit !== null) return hit;
    }
    return null;
  }
  if (node === null || typeof node !== "object") return null;
  const o = node as Record<string, unknown>;
  if (o.id === id) {
    const fig = o.figure as { portrait?: NpcPortrait } | undefined;
    const p = (o.portrait as NpcPortrait | undefined) ?? fig?.portrait;
    if (p !== undefined) return p;
  }
  for (const v of Object.values(o)) {
    const hit = findPortrait(v, id);
    if (hit !== null) return hit;
  }
  return null;
}

const SOOT_FACES: [string, string, string, string][] = [
  ["灰鴿（餘燼集郵差）", tradeYaml, "postman_huige", "ashen_waste"],
  ["鉚釘（傭兵）", mercYaml, "merc_panshi", "capital"],
  ["工坊師傅", capitalYaml, "workshop_master", "capital"],
  ["主城鐵匠", smithyYaml, "smithy", "capital"],
  ["爐叔", ashenYaml, "smith_lu", "ashen_waste"],
];

function SootScene() {
  return (
    <Stage fill>
      <div className="panel" data-testid="soot-faces" style={{ position: "absolute", left: 16, top: 16, display: "flex", flexDirection: "column", gap: 10 }}>
        <div className="section-title">6T-1d soot（右頰、裁在臉內）：192／96／48</div>
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap", alignItems: "flex-end" }}>
          {SOOT_FACES.map(([zh, raw, id, region]) => {
            const p = findPortrait(parse(raw), id);
            return (
              <div key={id} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                <Portrait portrait={p} region={region} size={192} label={zh} />
                <span style={{ display: "flex", gap: 6, alignItems: "flex-end" }}>
                  <Portrait portrait={p} region={region} size={96} />
                  <Portrait portrait={p} region={region} size={48} />
                </span>
                <span className="small">{zh}</span>
              </div>
            );
          })}
        </div>
      </div>
    </Stage>
  );
}

const root = document.getElementById("root");
const SCENES: Record<string, () => React.ReactElement> = { event: EventScene, roll: RollScene, icons: IconsScene, encounter: EncounterScene, reaction: ReactionScene, soot: SootScene, "encounter-boss": BossEncounterScene, qportraits: QPortraitScene };
const Scene = SCENES[MODE] ?? SubtitleScene;
if (root !== null) createRoot(root).render(<Scene />);
// UI-E1b：開發頁也能量「四角飾件沒有壓到內容」（排版煙霧檢查同一套量法）
(window as unknown as { __corners?: () => string[] }).__corners = () => scanCornerIssues(document, window);
