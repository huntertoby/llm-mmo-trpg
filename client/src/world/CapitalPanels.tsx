// 主城的情境物件面板（Phase 6D-5；玩法 PM 主城草稿第 3、4 節）：
// - 橋頭石碑：該區的傳送選單，依「已開放／未解鎖（寫條件）／之後的賽季」顯示三種內容（效果同傳送石）；
// - 整備亭：休息（照現行的城鎮休息）、換技能、配點、換裝。
// 能不能傳送、能不能休息都由伺服器判定（`atlas`、`here.can_rest`）。
import type { WorldAction, WorldView } from "../api/types";
import type { HudPanel } from "./hud";

export function SteleMenu({
  view,
  region,
  busy,
  onAct,
  onClose,
}: {
  view: WorldView;
  region: string;
  busy: boolean;
  onAct(action: WorldAction): void;
  onClose(): void;
}) {
  const r = view.atlas?.regions.find((x) => x.region === region);
  if (r === undefined) return <div className="muted small">石碑上的字看不清楚。</div>;
  return (
    <div className="panel capital-stele" data-testid="world-hud-stele" data-region={region} data-status={r.status}>
      <div className="section-title">往{r.name_zh}的浮橋</div>
      {r.status === "open" && (
        <>
          <div className="stele-status open small">已開放：{r.town_name_zh ?? r.name_zh}</div>
          {r.current ? (
            <div className="muted small">你就在這一區。</div>
          ) : (
            <button
              type="button"
              disabled={busy || r.can_teleport !== true}
              onClick={() => {
                onAct({ kind: "teleport", region });
                onClose();
              }}
              data-testid="world-stele-teleport"
            >
              傳送到{r.town_name_zh ?? r.name_zh}
            </button>
          )}
          {r.can_teleport !== true && !r.current && view.atlas?.teleport_problem_zh != null && (
            <div className="muted small">{view.atlas.teleport_problem_zh}</div>
          )}
        </>
      )}
      {r.status === "locked" && (
        <div className="stele-status locked small" data-testid="world-stele-condition">
          未解鎖：{r.condition_zh}
        </div>
      )}
      {r.status === "later" && (
        <div className="stele-status later small" data-testid="world-stele-condition">
          {r.condition_zh ?? "之後的賽季"}
        </div>
      )}
    </div>
  );
}

export function PavilionPanel({
  view,
  busy,
  onAct,
  onPanel,
}: {
  view: WorldView;
  busy: boolean;
  onAct(action: WorldAction): void;
  onPanel(panel: HudPanel): void;
}) {
  const c = view.character;
  return (
    <div className="panel capital-pavilion" data-testid="world-hud-pavilion">
      <div className="section-title">整備亭</div>
      <div className="small">
        HP {c.hp} / {c.max_hp}・法力 {c.mana} / {c.max_mana}
      </div>
      <div className="buttons">
        <button type="button" disabled={busy || !view.here.can_rest} onClick={() => onAct({ kind: "rest" })} data-testid="world-pavilion-rest">
          休息（HP、法力回滿）
        </button>
        <button type="button" disabled={!view.here.can_loadout} onClick={() => onPanel("skills")} data-testid="world-pavilion-skills">
          換技能
        </button>
        <button type="button" onClick={() => onPanel("growth")} data-testid="world-pavilion-growth">
          配點
        </button>
        <button type="button" disabled={view.inventory == null} onClick={() => onPanel("bag")} data-testid="world-pavilion-bag">
          換裝
        </button>
      </div>
    </div>
  );
}
