// 開發用：6C-ART2 事件插圖 10 種（開 `client/dev/event-art-gallery.html`，pnpm dev 後 /dev/event-art-gallery.html）。
// 不屬於正式 build；供美術 PM 驗收與截圖。`?mode=cards`（預設）：正式的事件卡（雲嶺 10 種＋荒原 4 種＋主城 10 種，RT-2），假資料；
// `?mode=raw`：插圖本身 1:1（和 docs/art/shots/misc/events.png 對照）。
// QK-2：`?mode=awaken`：主城開場 ① 醒來插圖（躺著、半坐起）× 人類／矮人／龍裔，2 倍。
import { createRoot } from "react-dom/client";
import type { Glossary, WorldEventView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGlossary } from "../battle/glossary";
import { EVENT_ART_H, EVENT_ART_IDS, EVENT_ART_W, eventArtBg, eventArtUrl, SCENES, type EventArtId } from "../render/eventArt";
import { EventCard } from "../world/EventCard";
import { resolveDoll } from "../render/appearance";
import { AWAKEN_H, AWAKEN_W, drawAwakenArt } from "../render/eventArtAwaken";
import { LOOK_OPTIONS } from "../run/lookOptions";
import { drawFigure } from "../render/paperdoll";
import "../styles/index.css";

setGlossary(glossary as unknown as Glossary);

const params = new URLSearchParams(location.search);
const MODE = params.get("mode") ?? "cards";
const ONLY = params.get("only")?.split(",") ?? null;

const SOLUTIONS: WorldEventView["solutions"] = [
  { index: 0, kind: "situation", kind_zh: "情境判定", note_zh: "查看四周", hint_zh: "", attributes_zh: "感知", template: "inspect", available: true, cost_supplies: 0, can_pay: true },
  { index: 1, kind: "combat", kind_zh: "戰鬥", note_zh: "", hint_zh: "", attributes_zh: "", template: null, available: true, cost_supplies: 0, can_pay: true },
  { index: 2, kind: "abandon", kind_zh: "放棄", note_zh: "", hint_zh: "", attributes_zh: "", template: null, available: true, cost_supplies: 0, can_pay: true },
];

const LOCATION_ZH: Readonly<Record<string, string>> = { ashen_waste: "灰燼荒原・焦土道", capital: "主城・樞島" };

function event(art: EventArtId, region: string): WorldEventView {
  return {
    skeleton: `gallery_${art}`,
    location_name_zh: LOCATION_ZH[region] ?? "雲嶺・竹林小徑",
    actor_zh: SCENES[art].zh,
    motive_zh: "（開發用假資料）",
    story: null,
    who_zh: "",
    want_zh: "",
    obstacle_zh: "",
    stakes_zh: "",
    solutions: SOLUTIONS,
    leave_zh: "離開這裡事件就作罷",
    art_url: null,
    art,
    region,
  };
}

const LIST: [EventArtId, string][] = [
  ...EVENT_ART_IDS.map((id): [EventArtId, string] => [id, "cloud_ridge"]),
  ...(["ambush", "chest", "altar", "trap"] as const).map((id): [EventArtId, string] => [id, "ashen_waste"]),
  ...EVENT_ART_IDS.map((id): [EventArtId, string] => [id, "capital"]),
].filter(([id]) => ONLY === null || ONLY.includes(id));

function Cards() {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 12, padding: 12, background: "#1c2620", width: 1040 }}>
      {LIST.map(([id, region]) => (
        <div key={`${id}-${region}`} style={{ width: 320 }}>
          <EventCard event={event(id, region)} busy={false} onOpen={() => undefined} onSolve={() => undefined} onAnswer={() => undefined} />
        </div>
      ))}
    </div>
  );
}

function Raw() {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 14, padding: 16, background: "#1b1714", width: 1180 }}>
      {LIST.map(([id, region]) => (
        <img key={`${id}-${region}`} src={eventArtUrl(id, eventArtBg(region)) ?? ""} width={EVENT_ART_W} height={EVENT_ART_H} alt={SCENES[id].zh} />
      ))}
    </div>
  );
}

const root = document.getElementById("root");
function AwakenCanvas({ race, pose }: { race: string; pose: 0 | 1 }) {
  const ref = (c: HTMLCanvasElement | null): void => {
    if (c === null) return;
    const g = c.getContext("2d");
    if (g === null) return;
    g.setTransform(2, 0, 0, 2, 0, 0);
    const opts = LOOK_OPTIONS[race];
    const hero = resolveDoll({ template: "hero", dollLook: null, team: "ally", summon: false, weaponId: "sword", raceLook: opts?.raceLook ?? null });
    drawAwakenArt(g, hero, pose, ["cloud_ridge"], "樞島・中央廣場");
  };
  return <canvas ref={ref} width={AWAKEN_W * 2} height={AWAKEN_H * 2} style={{ width: AWAKEN_W, height: AWAKEN_H }} data-testid="awaken-art" />;
}

/** 調姿勢用（`&pose=hipN,lean,arm,armF,drop`）：只畫主角 6 倍＋地面線（y 50）與原點的直線（x 40）。 */
function PoseProbe({ spec }: { spec: string }) {
  const [hipN, lean, arm, armF, drop] = spec.split(",").map(Number) as [number, number, number, number, number];
  const ref = (c: HTMLCanvasElement | null): void => {
    const g = c?.getContext("2d");
    if (!g) return;
    g.setTransform(6, 0, 0, 6, 0, 0);
    g.fillStyle = "#888";
    g.fillRect(0, 0, 80, 60);
    g.fillStyle = "#333";
    g.fillRect(0, 50, 80, 0.15);
    g.fillRect(40, 0, 0.15, 60);
    g.translate(40, 50 + drop);
    const hero = resolveDoll({ template: "hero", dollLook: null, team: "ally", summon: false, weaponId: "sword", raceLook: null });
    const sp = { ...hero, gear: { ...hero.gear } };
    delete sp.gear.main_hand;
    drawFigure(g, sp, "east", false, { hipN, hipF: hipN, lean, arm, armF } as never);
  };
  return <canvas ref={ref} width={480} height={360} />;
}

function Awaken() {
  const probe = params.get("pose");
  if (probe !== null) return <PoseProbe spec={probe} />;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 12, padding: 12, background: "#1b1e24" }}>
      {["human", "dwarf", "dragonkin"].flatMap((r) => ([0, 1] as const).map((p) => <AwakenCanvas key={`${r}${p}`} race={r} pose={p} />))}
    </div>
  );
}

if (root !== null) createRoot(root).render(MODE === "raw" ? <Raw /> : MODE === "awaken" ? <Awaken /> : <Cards />);
