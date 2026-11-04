// 開發用：6C-ART2 事件插圖 10 種（開 `client/event-art-gallery.html`，pnpm dev 後 /event-art-gallery.html）。
// 不屬於正式 build；供美術 PM 驗收與截圖。`?mode=cards`（預設）：正式的事件卡（雲嶺 10 種＋荒原 4 種），假資料；
// `?mode=raw`：插圖本身 1:1（和 docs/art/events.png 對照）。
import { createRoot } from "react-dom/client";
import type { Glossary, WorldEventView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGlossary } from "../battle/glossary";
import { EVENT_ART_H, EVENT_ART_IDS, EVENT_ART_W, eventArtUrl, SCENES, type EventArtId } from "../render/eventArt";
import { EventCard } from "../world/EventCard";
import "../styles/index.css";

setGlossary(glossary as unknown as Glossary);

const params = new URLSearchParams(location.search);
const MODE = params.get("mode") ?? "cards";
const ONLY = params.get("only")?.split(",") ?? null;

const SOLUTIONS: WorldEventView["solutions"] = [
  { index: 0, kind: "situation", kind_zh: "情境判定", note_zh: "查看四周", attributes_zh: "感知", template: "inspect", available: true, cost_supplies: 0, can_pay: true },
  { index: 1, kind: "combat", kind_zh: "戰鬥", note_zh: "", attributes_zh: "", template: null, available: true, cost_supplies: 0, can_pay: true },
  { index: 2, kind: "abandon", kind_zh: "放棄", note_zh: "", attributes_zh: "", template: null, available: true, cost_supplies: 0, can_pay: true },
];

function event(art: EventArtId, region: string): WorldEventView {
  return {
    skeleton: `gallery_${art}`,
    location_name_zh: region === "ashen_waste" ? "灰燼荒原・焦土道" : "雲嶺・竹林小徑",
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
        <img key={`${id}-${region}`} src={eventArtUrl(id, region === "ashen_waste" ? "ashen" : "cloud") ?? ""} width={EVENT_ART_W} height={EVENT_ART_H} alt={SCENES[id].zh} />
      ))}
    </div>
  );
}

const root = document.getElementById("root");
if (root !== null) createRoot(root).render(MODE === "raw" ? <Raw /> : <Cards />);
