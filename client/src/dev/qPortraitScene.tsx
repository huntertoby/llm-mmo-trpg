// 開發用（QK-2）：Q 版頭像總表，對照 docs/art/sample/q-portraits.html（story-gallery.html#qportraits）。
// 37 位的外觀直接讀 content（同遊戲：portrait 欄位原樣，經 render/portrait.ts 畫），順序與框色區照樣張 qPortrait.js 的名單。
// 另有 192px 體型三種、好感五級＋頭頂徽章、56／28px、種族卡 10 族。`window.__qp(id, size, level)` 給出圖腳本取單張。
import { parse } from "yaml";
import type { NpcPortrait } from "../api/types";
import { portraitUrl } from "../render/portrait";
import { drawMoodBadge } from "../render/qPortrait";
import { raceFaceUrl } from "../run/raceFace";
import { RACES_YAML_TEXT } from "../run/createTexts";
import { LOOK_OPTIONS } from "../run/lookOptions";
import cloudYaml from "../../../content/world/npcs/cloud_ridge.yaml?raw";
import ashenYaml from "../../../content/world/npcs/ashen_waste.yaml?raw";
import tradeYaml from "../../../content/world/trade.yaml?raw";
import mercYaml from "../../../content/world/mercenaries.yaml?raw";
import capitalYaml from "../../../content/world/fields/capital/capital.yaml?raw";
import smithyYaml from "../../../content/world/fields/capital/interiors/capital_smithy.yaml?raw";
import mentorYaml from "../../../content/world/fields/capital/interiors/capital_mentor_hall.yaml?raw";
import tavernYaml from "../../../content/world/fields/capital/interiors/capital_tavern.yaml?raw";

/** [id, 名字, 群組, 框色區, 來源] —— 順序同樣張 qPortrait.js 的 N。 */
type Row = readonly [string, string, string, string, string];
const C = cloudYaml;
const A = ashenYaml;
const M = mercYaml;
const T = tradeYaml;
export const Q_PORTRAIT_ROWS: readonly Row[] = [
  ["granny_du", "渡婆婆", "cloud_ridge", "cloud_ridge", C],
  ["shopkeeper_liu", "柳掌櫃", "cloud_ridge", "cloud_ridge", C],
  ["daoist_qingya", "青崖道長", "cloud_ridge", "cloud_ridge", C],
  ["hunter_ayue", "阿岳", "cloud_ridge", "cloud_ridge", C],
  ["acolyte_xiaolian", "小蓮", "cloud_ridge", "cloud_ridge", C],
  ["mistlock_master", "霧鎖真人", "cloud_ridge", "cloud_ridge", C],
  ["scarface", "疤面", "cloud_ridge", "cloud_ridge", C],
  ["frost_chime", "霜音", "cloud_ridge", "cloud_ridge", C],
  ["smith_shi", "石師傅", "cloud_ridge", "cloud_ridge", C],
  ["gran", "葛蘭", "cloud_ridge", "cloud_ridge", C],
  ["iron_lady", "鐵娘", "ashen_waste", "ashen_waste", A],
  ["greybeard", "灰鬚", "ashen_waste", "ashen_waste", A],
  ["smith_lu", "爐叔", "ashen_waste", "ashen_waste", A],
  ["scavenger_laotie", "老鐵", "ashen_waste", "ashen_waste", A],
  ["priestess_helin", "赫琳", "ashen_waste", "ashen_waste", A],
  ["overseer_scar", "鍛疤", "ashen_waste", "ashen_waste", A],
  ["merc_qingfeng", "青鋒", "merc", "cloud_ridge", M],
  ["merc_chuanyun", "珊瑚", "merc", "frost_tide", M],
  ["merc_chiyan", "灰燼瑪菈", "merc", "ashen_waste", M],
  ["merc_tiebi", "賽倫", "merc", "crystal_crown", M],
  ["merc_panshi", "鉚釘", "merc", "arcane_hub", M],
  ["merc_huichun", "回春", "merc", "cloud_ridge", M],
  ["merc_qingyin", "莉瑟", "merc", "crystal_crown", M],
  ["merc_jinglei", "七號線圈", "merc", "arcane_hub", M],
  ["merc_fuying", "鏽牙", "merc", "ashen_waste", M],
  ["postman_bailu", "白鷺", "postman", "capital", T],
  ["postman_axin", "阿信", "postman", "cloud_ridge", T],
  ["postman_huige", "灰鴿", "postman", "ashen_waste", T],
  ["seal_keeper", "守印人", "capital", "capital", capitalYaml],
  ["hire", "傭兵管事", "capital", "capital", capitalYaml],
  ["pool_keeper", "守池人", "capital", "capital", capitalYaml],
  ["workshop_master", "工坊師傅", "capital", "capital", capitalYaml],
  ["mentor", "導師殿導師", "capital", "capital", mentorYaml],
  ["scribe", "書記", "capital", "capital", mentorYaml],
  ["smithy", "樞島鐵匠", "capital", "capital", smithyYaml],
  ["enchanter", "附魔師", "capital", "capital", smithyYaml],
  ["tavern", "酒館老闆", "capital", "capital", tavernYaml],
];

/** 在 YAML 樹裡找 `id` 符合的節點的頭像（`portrait`／`figure.portrait`）。 */
export function findPortrait(node: unknown, id: string): NpcPortrait | null {
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

const parsed = new Map<string, unknown>();
function portraitOf(row: Row): NpcPortrait | null {
  const raw = row[4];
  if (!parsed.has(raw)) parsed.set(raw, parse(raw));
  return findPortrait(parsed.get(raw), row[0]);
}
const BY_ID = new Map(Q_PORTRAIT_ROWS.map((r) => [r[0], r]));

/** 出圖腳本用：一張頭像的 PNG 網址（dpr 1）。 */
(window as unknown as { __qp?: (id: string, size: number, level?: number | null) => string | null }).__qp = (id, size, level = null) => {
  const r = BY_ID.get(id);
  return r === undefined ? null : portraitUrl(portraitOf(r), r[3], size, 1, level);
};
/** 出圖腳本用：種族卡頭像。 */
(window as unknown as { __qrace?: (race: string, size: number) => string | null }).__qrace = (race, size) => {
  const realm = RACES.find((r) => r.id === race)?.home_realm ?? "merc";
  return raceFaceUrl(race, realm, size, 1);
};

interface RaceRow {
  id: string;
  name_zh: string;
  home_realm: string;
}
const RACES = ((parse(RACES_YAML_TEXT) as { races: RaceRow[] }).races ?? []).filter((r) => LOOK_OPTIONS[r.id] !== undefined);

function Face({ row, size, level = null, badge = false }: { row: Row; size: number; level?: number | null; badge?: boolean }) {
  const url = portraitUrl(portraitOf(row), row[3], size, 2, level);
  const pad = badge ? Math.round(size * 0.18) : 0;
  return (
    <figure style={{ margin: 0, textAlign: "center" }} data-testid="qp-face" data-id={row[0]}>
      <div style={{ display: "flex", alignItems: "flex-start" }}>
        {url !== null && <img src={url} width={size} height={size} alt={row[1]} style={{ marginTop: pad }} />}
        {badge && <Badge size={size * 0.3} level={level ?? 2} style={{ marginLeft: -size * 0.15 }} />}
      </div>
      <figcaption style={{ fontSize: 11, color: "#c8ccd4" }}>{row[1]}</figcaption>
    </figure>
  );
}

function Badge({ size, level, style }: { size: number; level: number; style?: React.CSSProperties }) {
  const c = document.createElement("canvas");
  c.width = c.height = Math.ceil(size * 2 + 4);
  const g = c.getContext("2d");
  if (g !== null) {
    g.scale(2, 2);
    drawMoodBadge(g, size / 2 + 1, size / 2 + 1, size / 2, level);
  }
  return <img src={c.toDataURL()} width={size + 2} height={size + 2} alt="" style={style} />;
}

const GROUPS: readonly [string, string][] = [
  ["cloud_ridge", "雲嶺（10）"],
  ["ashen_waste", "灰燼荒原（6）"],
  ["merc", "系統傭兵（9）"],
  ["postman", "郵差（3）"],
  ["capital", "主城樞島（9）"],
];
const H2: React.CSSProperties = { fontSize: 15, margin: "14px 0 4px", borderBottom: "1px solid #3a3f4a", paddingBottom: 3 };
const ROW: React.CSSProperties = { display: "flex", flexWrap: "wrap", gap: "8px 10px", alignItems: "flex-end" };

export function QPortraitScene() {
  const rows = (g: string): readonly Row[] => Q_PORTRAIT_ROWS.filter((r) => r[2] === g);
  const pick = (id: string): Row => BY_ID.get(id)!;
  return (
    <div style={{ padding: "12px 16px", background: "#1b1e24", color: "#e8e8ea", width: 1284, fontSize: 12, fontFamily: "sans-serif" }} data-testid="qp-root">
      <h1 style={{ fontSize: 18, margin: "4px 0 2px" }}>Q 版頭像（遊戲畫法；外觀讀 content）</h1>
      <div style={H2}>96px（事件卡）：全部 37 位</div>
      <div style={ROW} data-testid="qp-all">
        {GROUPS.flatMap(([g]) => rows(g)).map((r) => (
          <Face key={r[0]} row={r} size={96} />
        ))}
      </div>
      <div style={H2}>192px：體型三種（標準、tall、stout）× 配件對位</div>
      <div style={ROW} data-testid="qp-build">
        {["scavenger_laotie", "postman_huige", "merc_panshi", "smith_lu"].map((id) => (
          <Face key={id} row={pick(id)} size={192} />
        ))}
      </div>
      <div style={H2}>好感五級表情＋頭頂徽章</div>
      <div style={ROW} data-testid="qp-levels">
        {["scavenger_laotie", "merc_jinglei", "mistlock_master"].flatMap((id) => [0, 1, 2, 3, 4].map((l) => <Face key={`${id}${l}`} row={pick(id)} size={96} level={l} badge />))}
      </div>
      <div style={H2}>徽章單獨：32px、20px（場上 NPC 頭頂）</div>
      <div style={ROW}>
        {[32, 20].flatMap((s) => [0, 1, 2, 3, 4].map((l) => <Badge key={`${s}${l}`} size={s} level={l} />))}
      </div>
      <div style={H2}>56px、28px</div>
      <div style={ROW}>
        {Q_PORTRAIT_ROWS.map((r) => (
          <Face key={r[0]} row={r} size={56} />
        ))}
      </div>
      <div style={ROW}>
        {Q_PORTRAIT_ROWS.map((r) => {
          const u = portraitUrl(portraitOf(r), r[3], 28, 2);
          return u === null ? null : <img key={r[0]} src={u} width={28} height={28} alt="" />;
        })}
      </div>
      <div style={H2}>種族卡 10 族（52px，框色＝發源區）</div>
      <div style={ROW} data-testid="qp-races">
        {RACES.map((r) => {
          const u = raceFaceUrl(r.id, r.home_realm, 96, 2);
          return (
            <figure key={r.id} style={{ margin: 0, textAlign: "center" }}>
              {u !== null && <img src={u} width={96} height={96} alt={r.name_zh} />}
              <figcaption style={{ fontSize: 11 }}>{r.name_zh}</figcaption>
            </figure>
          );
        })}
      </div>
    </div>
  );
}
