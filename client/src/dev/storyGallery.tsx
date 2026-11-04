// 開發用：6C-7 的字幕、事件卡、情境判定擲骰與 NPC 頭像（開 `client/story-gallery.html`，pnpm dev 後 /story-gallery.html）。
// 不屬於正式 build；供美術 PM 驗收與截圖。畫面用正式元件與樣式，資料是固定的假資料；NPC 外觀直接讀 `content/world/npcs/*.yaml`。
// `#subtitle`：上方字幕＋NPC 頭像（96／48／28）與地圖紙娃娃對照；`#event`：事件卡（插圖、對話框、選項圖示、情境判定）；
// `#roll`（也可用 `?mode=roll`）：判定結果（兩顆骰的動畫＋顏色；`?t=` 指定動畫已經過的毫秒，不給＝照計時器播）；
// `#icons`：6C-ART3 墨線圖示總表（選項 8、其他 5、六屬性、d20；64／24／18，對照 docs/art/sample/story-icons.html）。
import { createRoot } from "react-dom/client";
import { parse } from "yaml";
import type { Glossary, NpcPortrait, WorldEventView, WorldSituationResult } from "../api/types";
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
  actor_zh: "困住的商隊",
  motive_zh: "想在天黑前過河",
  story: STORY,
  who_zh: "",
  want_zh: "",
  obstacle_zh: "",
  stakes_zh: "",
  follows_zh: "商人欠你人情",
  solutions: [
    { index: 0, kind: "situation", kind_zh: "情境判定", note_zh: "查看橋下的爪痕", attributes_zh: "感知、智力", template: "inspect", available: true, cost_supplies: 0, can_pay: true },
    { index: 1, kind: "situation", kind_zh: "情境判定", note_zh: "說服商人先卸貨", attributes_zh: "意志", template: "persuade", available: true, cost_supplies: 0, can_pay: true },
    { index: 2, kind: "combat", kind_zh: "戰鬥", note_zh: "把橋下的東西引出來打", attributes_zh: "", template: null, available: true, cost_supplies: 0, can_pay: true },
    { index: 3, kind: "parley", kind_zh: "交涉", note_zh: "雇船夫繞路", attributes_zh: "", template: null, available: true, cost_supplies: 2, can_pay: true, waive_thread: "th1", waive_zh: "商人欠你人情" },
    { index: 4, kind: "abandon", kind_zh: "放棄", note_zh: "", attributes_zh: "", template: null, available: true, cost_supplies: 0, can_pay: true },
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

function Stage({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ position: "relative", width: 1040, height: 720, overflow: "hidden", background: "radial-gradient(ellipse at 50% 60%, #3e5446, #1c2620 70%)", fontFamily: "sans-serif" }}>
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

const root = document.getElementById("root");
if (root !== null) createRoot(root).render(MODE === "event" ? <EventScene /> : MODE === "roll" ? <RollScene /> : MODE === "icons" ? <IconsScene /> : <SubtitleScene />);
