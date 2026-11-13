// 地點圖右側（Phase 5A-5）：遇敵陣容（開戰／撤退，9.6.6）、角色狀態、時刻與天氣、目前地點的服務
// （城鎮：休息、換技能、傳送；野外：紮營；營火：換技能，9.6.7 #2、#114）、趕路切換、最近事件。
// 5A-7：靈感與角色階級、下一場修正、最近一次戰鬥、開場說明（先手、開場狀態、增援）、「成長與技能」切換、
// 城鎮與營火限制的說明；閃現待選時服務按鈕停用（後端已關掉）。
// 5B-5：事件卡與判定結果（`eventSlot`，遭遇面板之後）、這裡的人（`peopleSlot`）、城鎮的「酒館」與本週傳聞、
// 「任務與線頭」切換左欄。
// 5C-1：小鎮的「雇用傭兵」（面板內展開）、「隊伍」面板、遇敵面板的我方改用後端的 `allies_zh`。5C-2：雇用分傭兵／影子兩頁、「我的影子」面板。
// 5D-1：角色狀態加金幣與任務幣；有店的地點加「商店」（面板內展開）；右側「背包」面板（腰包整理、野外用藥）。
// 5D-3：有鐵匠或附魔台的地點加「鐵匠」（面板內展開，同商店）。
// 5D-4：「商店」「鐵匠」改成切換左欄的完整畫面；右側背包改成摘要（`InventorySummary`）＋「打開背包」；
// 背包滿等決定時狀態列一行提示＋按鈕（選擇在背包畫面）。
// UI-E3b：遇敵卡每名敵人前面加小頭像（戰場紙娃娃縮圖，`enemyThumb.tsx`）；精英、Boss 加金環。
import { useEffect, useRef, useState, type ReactNode } from "react";
import type { WorldAction, WorldView } from "../api/types";
import { LoadoutEditor } from "../run/LoadoutEditor";
import { Hint } from "../ui/Hint";
import { PopupFrame } from "../ui/PopupFrame";
import { battlefieldLine } from "./battlefield";
import { DuelArt } from "./DuelArt";
import { duelPlan } from "./duelArtPlan";
import { EnemyThumb } from "./enemyThumb";
import { growthBadge, type LeftPane, type WantPane } from "./growth";
import { InventorySummary } from "./EconomyPanel";
import { walletLine } from "./economy";
import { HireEditor, MyShadowPanel, PartyPanel, useHireToggle } from "./PartyPanel";
import { LookChangeLine } from "./LookChange";
import { RaceChangeLine } from "./RaceChange";
import { questBadge } from "./story";
import { statusLine } from "./mapView";
import { weatherPhaseText } from "./hud";

interface Props {
  view: WorldView;
  busy: boolean;
  hasten: boolean;
  onHasten(on: boolean): void;
  onAct(action: WorldAction): void;
  onBattle(): void;
  log: readonly string[];
  /** 左欄正在顯示成長畫面（或閃現選項）。 */
  growthOpen?: boolean;
  onGrowth?(): void;
  /** 左欄正在顯示任務與線頭（5B-5）。 */
  questsOpen?: boolean;
  onQuests?(): void;
  /** 這次在酒館聽到的傳聞（前端保留到換地點）。 */
  rumors?: readonly string[];
  eventSlot?: ReactNode;
  peopleSlot?: ReactNode;
  /** 左欄目前的畫面與切換（5D-4：背包、商店、鐵匠）。 */
  pane?: LeftPane;
  onPane?(pane: WantPane): void;
}

export function EncounterPanel({ view, busy, onAct, onBattle }: Pick<Props, "view" | "busy" | "onAct" | "onBattle">) {
  const e = view.encounter;
  if (e === null) return null;
  const field = battlefieldLine(e); // 6C-2：就地開打或退回模板的原因
  const duelOffered = e.duel === "offered" && !e.in_battle; // RG-3：精英要求一對一，還沒選
  return (
    <PopupFrame placement={{ kind: "inline" }} tone="danger" className="world-encounter" testId="world-encounter" role="region" label="遇敵">
      <div className="section-title">遇敵：{e.location_name_zh}</div>
      <div className="small">
        敵人等級 {e.enemy_level}・戰場 {e.map_name_zh}・{weatherPhaseText(e.weather_zh, e.day_phase_zh)}
      </div>
      {field !== null && (
        <div className="muted small" data-testid="world-encounter-battlefield">
          {field}
        </div>
      )}
      <ul className="world-enemies">
        {e.enemies.map((x, i) => (
          <li key={i} className={x.elite ? "elite" : x.third === true ? "third" : undefined} data-rank={x.rank}>
            <EnemyThumb enemy={x} />
            {x.name_zh}
            {x.elite && <span className="world-elite-tag">{x.rank === "boss" ? "頭目" : "精英"}{x.affix_zh !== null ? `・${x.affix_zh}` : ""}</span>}
            {x.third === true && <span className="world-third-tag">第三方</span>}
          </li>
        ))}
      </ul>
      <div className="muted small" data-testid="world-encounter-allies">
        我方：{e.allies_zh !== undefined && e.allies_zh !== "" ? e.allies_zh : `主角（開場 HP ${e.hero_hp}${e.fatigued ? "，疲憊" : ""}）`}
      </div>
      {(e.opening_zh ?? []).length > 0 && (
        <ul className="world-opening small" data-testid="world-opening">
          {(e.opening_zh ?? []).map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      )}
      {e.duel != null && e.duel !== "offered" && e.duel_zh != null && (
        <div className="muted small" data-testid="world-encounter-duel">
          {e.duel_zh}
        </div>
      )}
      {duelOffered && <DuelDialog view={view} encounter={e} busy={busy} onAct={onAct} />}
      <div className="run-actions">
        {/* 有單挑提議時「開戰」＝拒絕單挑，改一般樣式（和單挑對話框「不引導」一致；開發 PM 決定，RG-4 驗收美術 PM 另記）；沒有單挑照舊主鈕 */}
        <button type="button" className={duelOffered ? undefined : "primary"} disabled={busy} onClick={onBattle} data-testid="world-fight">
          {e.in_battle ? "繼續戰鬥" : "開戰"}
        </button>
        {!e.in_battle && (
          <Hint text={`不打，退回${e.retreat_to_zh}（不扣任何東西）`}>
            <button type="button" disabled={busy} onClick={() => onAct({ kind: "retreat" })} data-testid="world-retreat">
              撤退
            </button>
          </Hint>
        )}
      </div>
    </PopupFrame>
  );
}

/**
 * RG-3（#162，09 9.6.6）：精英要求一對一的對話框（`EncounterView.duel` ＝ `offered`）。
 * 說明字是伺服器的 `duel_zh`（寫明「兩邊獎勵一樣」）。不選直接按「開戰」＝拒絕（RG-2 規則，照舊能打）。
 * 不用 `DialogFrame`：遇敵卡本身是中上方的彈窗，`DialogFrame` 會疊在卡裡面、蓋住敵人清單又出現「移到下方」（RG-3 實機看過），
 * 改成遇敵卡裡一段有框的小對話框（`role="group"`）。
 * RG-4（docs/art/RG樣張.md 9.6 決定 3、9.8 第 7 條）：標題下面一張 320×120 插圖（A 暮色對峙，`DuelArt`）；
 * 接受、拒絕兩顆都是一般按鈕（不加 `primary`，不暗示推薦）、同一個 min-width 一樣大、接受在左；不加 autoFocus，
 * 打開時焦點給這一段本身（`tabIndex={-1}`），Enter 不會直接按到任何一顆。
 */
function DuelDialog({ view, encounter, busy, onAct }: { view: WorldView; encounter: NonNullable<WorldView["encounter"]>; busy: boolean; onAct(action: WorldAction): void }) {
  const elite = duelEliteName(encounter);
  const plan = duelPlan(view);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.focus({ preventScroll: true });
  }, []);
  return (
    <div className="duel-dialog" data-testid="world-duel" role="group" aria-label="單挑" tabIndex={-1} ref={ref}>
      <div className="duel-title">{`${elite}要求一對一`}</div>
      {plan !== null && <DuelArt plan={plan} />}
      {encounter.duel_zh != null && <p className="small">{encounter.duel_zh}</p>}
      <div className="duel-choices">
        <button type="button" className="duel-choice" disabled={busy} onClick={() => onAct({ kind: "duel_choice", accept: true })} data-testid="world-duel-accept">
          接受
        </button>
        <button type="button" className="duel-choice" disabled={busy} onClick={() => onAct({ kind: "duel_choice", accept: false })} data-testid="world-duel-decline">
          拒絕
        </button>
      </div>
    </div>
  );
}

/** 提出單挑的精英：陣容裡第一個精英（伺服器 `duel_line` 也用排最前的那一個）；沒有標精英時用第一名敵人。 */
export function duelEliteName(e: NonNullable<WorldView["encounter"]>): string {
  return (e.enemies.find((x) => x.elite) ?? e.enemies[0])?.name_zh ?? "";
}

export function HerePanel({
  view,
  busy,
  hasten,
  onHasten,
  onAct,
  growthOpen = false,
  onGrowth,
  questsOpen = false,
  onQuests,
  rumors = [],
  pane = "map",
  onPane,
  hideHasten = false,
}: Pick<
  Props,
  "view" | "busy" | "hasten" | "onHasten" | "onAct" | "growthOpen" | "onGrowth" | "questsOpen" | "onQuests" | "rumors" | "pane" | "onPane"
> & {
  /** 實地地圖的 HUD（6B-5）不用「趕路」：走格子不花東西，功能列第 7 個圖示改成潛行。 */
  hideHasten?: boolean;
}) {
  const here = view.here;
  const [editing, setEditing] = useState(false);
  const shopping = pane === "shop";
  const smithing = pane === "smithy";
  const reading = pane === "board";
  const league = pane === "league";
  const hiring = useHireToggle(view.party);
  const free = view.encounter === null && view.battle_id === null;
  return (
    <div className="panel world-here" data-testid="world-here">
      <div className="section-title">
        {here.name_zh}　<span className="muted small">{here.kind_zh}{here.camped ? "・營火中" : ""}</span>
      </div>
      {here.description_zh !== "" && <div className="muted small">{here.description_zh}</div>}
      <div className="run-actions">
        {here.can_rest && (
          <Hint text="HP、法力、耐力回滿，補給補到初值（免費）">
            <button type="button" disabled={busy} onClick={() => onAct({ kind: "rest" })} data-testid="world-rest">
              休息
            </button>
          </Hint>
        )}
        {free && here.camp_problem_zh === null && (
          <Hint text={`花 ${here.camp_cost} 補給紮營：HP、法力、耐力回滿，可以換技能`}>
            <button type="button" disabled={busy} onClick={() => onAct({ kind: "camp" })} data-testid="world-camp">
              紮營
            </button>
          </Hint>
        )}
        {here.can_loadout && (
          <button type="button" aria-expanded={editing} disabled={busy} onClick={() => setEditing((v) => !v)} data-testid="world-loadout">
            {editing ? "收起換技能" : "換技能"}
          </button>
        )}
        {hiring.can && (
          <Hint text="免費帶 0～2 名隊友：系統傭兵或朋友的影子（出城前選好，野外不能換；不帶＝獨行）">
            <button type="button" aria-expanded={hiring.open} disabled={busy} onClick={hiring.toggle} data-testid="world-hire-toggle">
              {hiring.open ? "收起雇用隊友" : "雇用隊友"}
            </button>
          </Hint>
        )}
        {view.shop != null && (
          <Hint text={`${view.shop.name_zh}：消耗品、粗料、染料；特產每週限量`}>
            <button type="button" aria-expanded={shopping} disabled={busy} onClick={() => onPane?.("shop")} data-testid="world-shop-toggle">
              {shopping ? "回到地點圖" : "商店"}
            </button>
          </Hint>
        )}
        {view.crafting != null && (
          <Hint text="鐵匠：打造、強化、分解；附魔台：重骰、指定詞條">
            <button type="button" aria-expanded={smithing} disabled={busy} onClick={() => onPane?.("smithy")} data-testid="world-smithy-toggle">
              {smithing ? "回到地點圖" : "鐵匠"}
            </button>
          </Hint>
        )}
        {here.can_rest && onPane !== undefined && (
          <Hint text="今日目標、懸賞板（先搶先贏）、世界事件的全服進度">
            <button type="button" aria-expanded={reading} disabled={busy} onClick={() => onPane("board")} data-testid="world-board-toggle">
              {reading ? "回到地點圖" : "公告板"}
            </button>
          </Hint>
        )}
        {here.can_rest && onPane !== undefined && (
          <Hint text="影子循環賽：報名（每個帳號 1 個角色、第 13 天截止）、勝場排行榜、看每一場的重播">
            <button type="button" aria-expanded={league} disabled={busy} onClick={() => onPane("league")} data-testid="world-league-toggle">
              {league ? "回到地點圖" : "循環賽"}
            </button>
          </Hint>
        )}
        {here.can_tavern === true && (
          <Hint text="聽聽本週的傳聞（同一週大家聽到的都一樣；只是消息，不給東西）">
            <button type="button" disabled={busy} onClick={() => onAct({ kind: "tavern" })} data-testid="world-tavern">
              酒館
            </button>
          </Hint>
        )}
        {here.teleports.map((t) => (
          <button key={t.region} type="button" disabled={busy} onClick={() => onAct({ kind: "teleport", region: t.region })}>
            傳送到{t.name_zh}
          </button>
        ))}
      </div>
      {free && here.camp_problem_zh !== null && !here.can_rest && <div className="muted small">紮營：{here.camp_problem_zh}</div>}
      <div className={`small ${view.growth.at_service ? "muted" : "world-growth-lock"}`} data-testid="world-here-service">
        {view.growth.at_service ? "這裡可以閃現、重閃、溶掉、傳承、重配屬性、立誓。" : "這裡不能閃現、重閃、溶掉、傳承、重配屬性、立誓（只在城鎮與營火）。"}
      </div>
      {onGrowth !== undefined && (
        <div className="run-actions">
          <button
            type="button"
            className={growthOpen ? "primary" : ""}
            disabled={view.pending_flash != null}
            onClick={onGrowth}
            data-testid="world-growth-toggle"
          >
            {growthOpen ? "回到地點圖" : "成長與技能"}
            {!growthOpen && growthBadge(view) !== "" && <span className="small">（{growthBadge(view)}）</span>}
          </button>
          {onQuests !== undefined && (
            <button
              type="button"
              className={questsOpen ? "primary" : ""}
              disabled={view.pending_flash != null || view.pending_offer != null}
              onClick={onQuests}
              data-testid="world-quests-toggle"
            >
              {questsOpen ? "回到地點圖" : "任務與線頭"}
              {!questsOpen && questBadge(view) !== "" && <span className="small">（{questBadge(view)}）</span>}
            </button>
          )}
        </div>
      )}
      {rumors.length > 0 && (
        <div className="world-rumors" data-testid="world-rumors">
          <div className="section-title small">酒館：本週傳聞</div>
          <ul className="small">
            {rumors.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}
      {hiring.open && view.party != null && <HireEditor party={view.party} busy={busy} onAct={onAct} />}
      {here.can_loadout && editing && (
        <LoadoutEditor
          key={view.character.skills.map((s) => s.id).join(",")}
          hero={view.character}
          disabled={busy}
          onApply={(ids) => onAct({ kind: "loadout", skills: [...ids] })}
        />
      )}
      {here.can_loadout && editing && <div className="muted small">欄位上限：{view.character.slots_zh}</div>}
      {!hideHasten && (
        <label className="world-hasten">
          <input type="checkbox" checked={hasten} disabled={busy} onChange={(e) => onHasten(e.target.checked)} data-testid="world-hasten" />
          趕路（每步花 {here.hasten_cost} 補給，遇敵機率減半）
        </label>
      )}
    </div>
  );
}

export function WorldPanel(props: Props) {
  const { view, log } = props;
  const c = view.character;
  return (
    <div className="world-side">
      <EncounterPanel {...props} />
      {props.eventSlot}
      <div className="panel world-status" data-testid="world-status">
        <div className="section-title">
          {c.name}　<span className="muted small">{c.weapon_name_zh}{c.race_name_zh !== null ? `・${c.race_name_zh}` : ""}</span>
          {c.fatigued && (
            <Hint text="上一場全滅：下一場戰鬥開場 HP 打折，打完一場就消失">
              <span className="world-fatigue">疲憊</span>
            </Hint>
          )}
        </div>
        <div className="small">{statusLine(c)}</div>
        {view.wallet != null && (
          <div className="small world-wallet" data-testid="world-wallet">
            {walletLine(view.wallet)}
          </div>
        )}
        <div className="small" data-testid="world-growth-line">
          角色階級 {c.skill_tier ?? 1}・靈感點 {c.insight ?? 0}
          {c.attribute_points > 0 && <span className="world-points">・未分配屬性點 {c.attribute_points}</span>}
        </div>
        <div className="small world-skills">技能：{c.skills.map((s) => s.name_zh).join("、") || "（無）"}</div>
        {c.free_race_change === true && <RaceChangeLine character={c} busy={props.busy} onAct={props.onAct} />}
        <LookChangeLine character={c} busy={props.busy} onAct={props.onAct} />
        <div className="muted small">
          {view.map.name_zh}・{view.clock.time_zh}・{weatherPhaseText(view.clock.weather_zh, view.clock.day_phase_zh)}
        </div>
        {view.oath.current != null && <div className="small">誓約：{view.oath.current.name_zh}</div>}
        {(view.next_battle_zh ?? []).length > 0 && (
          <ul className="world-next small" data-testid="world-next-battle">
            {(view.next_battle_zh ?? []).map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        )}
        {view.last_battle_zh != null && (
          <div className="small world-last-battle" data-testid="world-last-battle">
            {view.last_battle_zh}
          </div>
        )}
        {view.last_loot_zh != null && (
          <div className="small world-last-battle" data-testid="world-last-loot">
            {view.last_loot_zh}
          </div>
        )}
      </div>
      {view.inventory != null && (
        <InventorySummary
          inventory={view.inventory}
          pendingLoot={view.pending_loot != null}
          open={props.pane === "bag"}
          onOpen={() => props.onPane?.("bag")}
        />
      )}
      {view.party != null && <PartyPanel party={view.party} />}
      {view.my_shadow != null && (
        <MyShadowPanel shadow={view.my_shadow} choices={view.party?.ai_choices ?? []} busy={props.busy} onAct={props.onAct} />
      )}
      <HerePanel {...props} />
      {props.peopleSlot}
      <div className="panel world-log" data-testid="world-log">
        <div className="section-title">最近發生的事</div>
        {log.length === 0 ? (
          <div className="muted small">點地圖上發亮的相鄰地點走過去。</div>
        ) : (
          <ul>
            {log.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
