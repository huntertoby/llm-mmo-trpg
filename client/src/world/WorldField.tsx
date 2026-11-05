// 可走動的實地地圖畫面（Phase 6B-3；docs/phases/Phase6計畫.md 第 5 節）：用戰鬥的 `BattleRenderer` 畫 `WorldView.field`，
// 點格子走過去（前端 BFS，超過 30 格分段送）、方向鍵／WASD 一次一格（排隊，同時只有一個請求在路上）、
// 小人逐格走（每格約 0.12 秒；6M-3 起播走路片段、照高低差走上去或跳上去，NPC 與敵群走一格也播）、換地圖淡出淡入。走到設施或 NPC 旁邊按 E 或點它就開原本的面板；
// 站在傳送石上顯示「傳送」按鈕。位置一律以伺服器回來的 `walk` 結果為準，失敗時顯示錯誤、位置不動。
// 6B-6：HUD 版面時格子照戰鬥的預設大小，鏡頭跟著主角（`camera.ts`）；畫布在可視區裡平移，逐格走時鏡頭用同樣的時間平滑跟上。
// 點擊換算沿用 `BattleCanvas` 的 `getBoundingClientRect()`（平移後的實際位置），所以鏡頭位移自動算進去。
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { FieldView, Pos, WorldAction, WorldView } from "../api/types";
import { fitScale, scaledSize } from "../battle/stageLayout";
import type { BattleRenderer } from "../render/BattleRenderer";
import { BattleCanvas } from "../ui/BattleCanvas";
import { cameraTransform, frameCamera, followCamera, FIELD_SCALE, type Camera, type TileRect, type ViewInsets } from "./camera";
import { FieldHeads, FieldSteleTags } from "./FieldHeads";
import { REGION_COLOR } from "../render/capitalArt";
import { steleTags } from "./opening";
import { openRegionsOf } from "./fieldScenery";
import { LevelPillar } from "./GainEffects";
import { peopleSteps } from "./peopleWalk";
import { arriveMap, leaveMap, mapTransit } from "./mapTransit";
import { playFieldStep } from "./fieldSteps";
import { frozenFriends, headMarks, npcBubbles, type GuideLines, type HeadMark } from "./fieldPeople";
import {
  chunkPath,
  fieldDrawModel,
  fieldHighlights,
  findPath,
  hoverText,
  interactTarget,
  keyDirection,
  nearTarget,
  pathNextTo,
  stepTarget,
  targetAt,
  walkAction,
  walkedCells,
  walkPlan,
  STEP_MS,
  type Direction,
  type FieldFriend,
  type FieldTarget,
} from "./fieldModel";

interface Props {
  view: WorldView;
  busy: boolean;
  /** 送一個世界動作，回傳新的畫面（失敗時已顯示錯誤，回傳 `null`）；不自動套用。 */
  send(action: WorldAction): Promise<WorldView | null>;
  /** 套用伺服器回來的畫面。 */
  commit(view: WorldView): void;
  /** 和設施或 NPC 互動（開對應的現有面板）。 */
  onInteract(target: FieldTarget): void;
  /**
   * HUD 版面（6B-5、6B-6）：舞台（可視區）大小；格子照戰鬥的預設大小，鏡頭跟著主角，說明列疊在畫面上。
   * 省略＝照 6B-3 自己量左欄、整張放進去。
   */
  hud?: HudCamera;
  /** RT-5 ②：開場時站著的人頭上的「！」與第一個指示（`splitOpening` 的 `spoken`；省略＝沒有）。 */
  guides?: GuideLines;
}

/** HUD 版面的鏡頭設定。 */
export interface HudCamera {
  width: number;
  height: number;
  /** 框住這個格子範圍（6C-2 就地開打框住戰場用）；`null`／省略＝跟著主角。 */
  frame?: TileRect | null;
  /** HUD 佔掉的四邊（6F-3：跟隨時主角放在扣掉 HUD 的安全區中央）；省略＝不扣。 */
  insets?: ViewInsets;
  /** 鏡頭變了（逐格走、換地圖、視窗大小變）時通知外面（小地圖的框、出口半透明）。 */
  onCamera?(cam: Camera): void;
}

type Job = { kind: "dir"; dir: Direction } | { kind: "path"; to: Pos } | { kind: "interact"; target: FieldTarget };

/** 方向鍵最多排幾步（快速連按時；超過的丟掉，避免放開鍵之後還一直走）。 */
const KEY_QUEUE_MAX = 3;
/** 換地圖前的淡出時間。 */
const FADE_MS = 220;
/** NPC 對話泡泡停留的時間。 */
export const BUBBLE_MS = 6000;

function typingInto(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

/** 切到「框住範圍」或切回跟隨時鏡頭平移的時間。 */
const FRAME_MS = 300;

/** 鏡頭：畫布在可視區裡平移（沒有鏡頭時照舊直接放）。 */
function CameraBox({ cam, ms, children }: { cam: Camera | null; ms: number; children: ReactNode }) {
  if (cam === null) return <>{children}</>;
  const style = { transform: cameraTransform(cam), transition: ms > 0 ? `transform ${ms}ms linear` : "none" };
  return (
    <div className="world-field-camera" style={style} data-testid="world-field-camera" data-cam={`${Math.round(cam.x)},${Math.round(cam.y)}`}>
      {children}
    </div>
  );
}

const wait = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms));

const NO_GUIDES: GuideLines = new Map();

export function WorldField({ view, busy, send, commit, onInteract, hud, guides = NO_GUIDES }: Props) {
  const served = view.field as FieldView;
  // 朋友（影子）的名單每次進城更新一次、不即時（21.5）：同一張地圖上沿用進來時的名單
  const friendsMemo = useRef<{ map: string; friends: readonly FieldFriend[] } | null>(null);
  const frozen = frozenFriends(friendsMemo.current, served);
  friendsMemo.current = frozen;
  const frozenList = frozen.friends;
  const field = useMemo<FieldView>(
    () => (frozenList === served.friends ? served : { ...served, friends: [...frozenList] }),
    [served, frozenList],
  );
  const blocked = view.encounter != null || view.battle_id != null;
  // NPC 的對話泡泡（21.7）：這次請求說的話，約 6 秒後收起（之後沒有對話的畫面不清掉，只等時間到；換地圖就收起）
  const [bubbles, setBubbles] = useState<ReadonlyMap<string, string>>(() => new Map());
  const bubbleTimer = useRef<number | null>(null);
  useEffect(() => {
    const next = npcBubbles(view.dialog);
    if (next.size === 0) return;
    setBubbles(next);
    if (bubbleTimer.current !== null) window.clearTimeout(bubbleTimer.current);
    bubbleTimer.current = window.setTimeout(() => setBubbles(new Map()), BUBBLE_MS);
  }, [view.dialog]);
  useEffect(() => setBubbles(new Map()), [served.map_id]);
  useEffect(
    () => () => {
      if (bubbleTimer.current !== null) window.clearTimeout(bubbleTimer.current);
    },
    [],
  );
  const marks = useMemo(() => headMarks(field, bubbles, guides), [field, bubbles, guides]);
  const steles = useMemo(() => steleTags(field, view.atlas), [field, view.atlas]);
  const rendererRef = useRef<BattleRenderer | null>(null);
  // 失敗時重畫一次（動畫可能已經把小人移走；以舊位置為準）
  const [redraw, setRedraw] = useState(0);
  // 6D-ART2：主城傳送陣的光圈照大世界圖已開放的區（不新增伺服器欄位）
  const openKey = openRegionsOf(view.atlas).join(",");
  const model = useMemo(() => fieldDrawModel(field, view.character.name, openKey === "" ? [] : openKey.split(",")), [field, view.character.name, openKey, redraw]);
  const [hover, setHover] = useState<Pos | null>(null);
  const highlights = useMemo(() => fieldHighlights(field, hover), [field, hover]);
  const [fading, setFading] = useState(false);
  const [walking, setWalking] = useState(false);

  // 依可用寬度縮放（高度留給標頭與按鈕列）
  const boxRef = useRef<HTMLDivElement>(null);
  const [avail, setAvail] = useState({ width: 800, height: 600 });
  useLayoutEffect(() => {
    const box = boxRef.current;
    if (box === null) return undefined;
    const measure = () => setAvail({ width: box.clientWidth, height: Math.max(320, window.innerHeight - 190) });
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(box);
    window.addEventListener("resize", measure);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, []);
  // ---- 鏡頭（6B-6）：跟著「畫面上的主角」，逐格走時每一步更新一次、用同樣的時間平移 ----
  const [focus, setFocus] = useState<{ pos: Pos; ms: number }>({ pos: field.me, ms: 0 });
  const lastMap = useRef(field.map_id);
  useEffect(() => {
    const changed = lastMap.current !== field.map_id;
    lastMap.current = field.map_id;
    setFocus((cur) => (!changed && cur.pos.x === field.me.x && cur.pos.y === field.me.y ? cur : { pos: field.me, ms: changed ? 0 : STEP_MS }));
  }, [field.map_id, field.me]);
  const hasHud = hud !== undefined;
  const hudW = hud?.width ?? 0;
  const hudH = hud?.height ?? 0;
  const frame = hud?.frame ?? null;
  // `hud`、`frame` 物件每次重畫都是新的：只看數值
  const frameKey = frame === null ? "" : `${frame.x},${frame.y},${frame.width},${frame.height}`;
  const ins = hud?.insets;
  const insetKey = ins === undefined ? "" : `${ins.top},${ins.right},${ins.bottom},${ins.left}`;
  const cam = useMemo<Camera | null>(() => {
    if (!hasHud) return null;
    const viewSize = { width: hudW, height: hudH };
    if (frameKey === "") {
      const [top = 0, right = 0, bottom = 0, left = 0] = insetKey === "" ? [] : insetKey.split(",").map(Number);
      return followCamera(viewSize, model, focus.pos, FIELD_SCALE, { top, right, bottom, left });
    }
    const [x = 0, y = 0, width = 0, height = 0] = frameKey.split(",").map(Number);
    return frameCamera(viewSize, model, { x, y, width, height });
  }, [hasHud, hudW, hudH, frameKey, insetKey, model, focus.pos]);
  const onCamera = hud?.onCamera;
  useEffect(() => {
    if (cam !== null) onCamera?.(cam);
  }, [cam, onCamera]);
  const scale = cam?.scale ?? fitScale(avail, model, undefined, 0.4, 1.5);

  // 換了地圖：淡入
  useEffect(() => setFading(false), [field.map_id]);

  // ---- 走路佇列（同時只有一個請求在路上）----
  const latest = useRef({ field, blocked, busy, send, commit, onInteract });
  latest.current = { field, blocked, busy, send, commit, onInteract };
  const fieldNow = useRef<FieldView | null>(field);
  useEffect(() => {
    fieldNow.current = field;
  }, [field]);
  const jobs = useRef<Job[]>([]);
  const running = useRef(false);
  /** AU-3：第幾步（腳步聲的變體鍵）。 */
  const stepNo = useRef(0);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      jobs.current = [];
    };
  }, []);

  /** 沿路徑走（分段送）；回傳是否在同一張地圖上走到了終點。 */
  const walkPath = useCallback(async (path: readonly Pos[]): Promise<boolean> => {
    let cur = fieldNow.current;
    if (cur === null) return false;
    for (const chunk of chunkPath(path, cur.walk_max_steps)) {
      const res = await latest.current.send(walkAction(chunk));
      if (!alive.current) return false;
      if (res === null) {
        jobs.current = [];
        setRedraw((n) => n + 1);
        return false;
      }
      const after = res.field ?? null;
      const cells = walkedCells(cur, chunk, after);
      // 一格一格播，鏡頭跟著每一格的終點用同樣的時間平移
      for (const step of walkPlan(cur.me, cells)) {
        if (!alive.current) return false;
        playFieldStep(cur, step.to, stepNo.current++); // AU-3：依地表踏一步
        setFocus({ pos: step.to, ms: step.durationMs });
        await rendererRef.current?.animate([step], () => !alive.current);
      }
      if (!alive.current) return false;
      // NPC、敵群走了一格的（6M-3）：套用新畫面前一起播走路片段（差更多格的照舊直接換位置）
      const others = peopleSteps(cur, after);
      if (others.length > 0) await Promise.all(others.map((m) => rendererRef.current?.animate([m], () => !alive.current)));
      if (!alive.current) return false;
      const changed = after === null || after.map_id !== cur.map_id;
      // 換地圖（6M-4）：走進門格播進門、走進邊緣出口播走出去，和畫面淡出重疊；其他照舊只淡出
      const transit = changed && after !== null ? mapTransit(cur, cells.length > 1 ? cells[cells.length - 2]! : cur.me, cells[cells.length - 1]) : null;
      if (transit !== null) await leaveMap(rendererRef.current, transit, setFading, () => !alive.current, cells[cells.length - 1]);
      else if (changed) {
        setFading(true);
        await wait(FADE_MS);
      }
      fieldNow.current = after;
      latest.current.commit(res);
      if (transit !== null && after !== null) void arriveMap(rendererRef, transit, after, () => !alive.current);
      const last = chunk[chunk.length - 1]!;
      if (changed || res.encounter != null || after.me.x !== last.x || after.me.y !== last.y) {
        jobs.current = [];
        return false;
      }
      cur = after;
    }
    return true;
  }, []);

  const runJob = useCallback(
    async (job: Job) => {
      const cur = fieldNow.current;
      if (cur === null || latest.current.blocked) {
        jobs.current = [];
        return;
      }
      if (job.kind === "dir") {
        const next = stepTarget(cur, job.dir);
        if (next !== null) await walkPath([next]);
        return;
      }
      if (job.kind === "interact" && job.target.kind === "friend") {
        latest.current.onInteract(job.target); // 朋友：點了直接開名片，不用走過去
        return;
      }
      if (job.kind === "path") {
        const path = findPath(cur, cur.me, job.to);
        if (path !== null) await walkPath(path);
        return;
      }
      const path = pathNextTo(cur, job.target);
      if (path === null) return;
      if (path.length > 0 && !(await walkPath(path))) return;
      const now = fieldNow.current;
      if (now !== null && now.map_id === cur.map_id && nearTarget(now.me, job.target)) latest.current.onInteract(job.target);
    },
    [walkPath],
  );

  const pump = useCallback(async () => {
    if (running.current) return;
    running.current = true;
    setWalking(true);
    try {
      while (jobs.current.length > 0 && alive.current) {
        const job = jobs.current.shift()!;
        await runJob(job);
      }
    } finally {
      running.current = false;
      if (alive.current) setWalking(false);
    }
  }, [runJob]);

  const enqueue = useCallback(
    (job: Job, replace: boolean) => {
      if (latest.current.blocked) return;
      if (replace) jobs.current = [job];
      else if (jobs.current.length < KEY_QUEUE_MAX) jobs.current.push(job);
      void pump();
    },
    [pump],
  );

  // 方向鍵／WASD、E
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey || typingInto(e.target)) return;
      const dir = keyDirection(e.key);
      if (dir !== null) {
        e.preventDefault();
        enqueue({ kind: "dir", dir }, false);
        return;
      }
      if (e.key === "e" || e.key === "E") {
        const cur = fieldNow.current;
        const target = cur === null ? null : interactTarget(cur);
        if (target !== null) {
          e.preventDefault();
          enqueue({ kind: "interact", target }, false);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [enqueue]);

  function click(tile: Pos) {
    const target = targetAt(field, tile);
    if (target !== null) enqueue({ kind: "interact", target }, true);
    else enqueue({ kind: "path", to: tile }, true);
  }

  /** 點頭上的圖示＝點那個人。 */
  function pick(mark: HeadMark) {
    click(mark.pos);
  }

  const onStone = field.stones.some((s) => s.x === field.me.x && s.y === field.me.y);
  const teleport = (to: string) =>
    void (async () => {
      if (running.current) return;
      setFading(true);
      const res = await send({ kind: "use_teleport_stone", to });
      if (res === null) {
        setFading(false);
        return;
      }
      fieldNow.current = res.field ?? null;
      commit(res);
      if (res.field?.map_id === field.map_id) setFading(false);
    })();

  const caption = hoverText(field, hover);
  return (
    <div className={`world-field${hud !== undefined ? " hud" : ""}`} data-testid="world-field" ref={boxRef}>
      <div className={`world-field-stage${fading ? " fading" : ""}${field.sneaking === true ? " sneaking" : ""}`} data-map={field.map_id}>
        <CameraBox cam={cam} ms={frame !== null ? FRAME_MS : focus.ms}>
          <div className="world-field-board" style={scaledSize(model, scale)}>
            <BattleCanvas
              model={model}
              highlights={highlights}
              flameOn={false}
              scale={scale}
              onTileClick={(t) => click(t)}
              onTileHover={setHover}
              onCancel={() => {
                jobs.current = [];
              }}
              rendererRef={rendererRef}
            />
            <FieldSteleTags tags={steles} grid={model} scale={scale} colors={REGION_COLOR} />
            <FieldHeads marks={marks} grid={model} scale={scale} onPick={pick} />
            <LevelPillar view={view} grid={model} at={field.me} scale={scale} />
          </div>
        </CameraBox>
      </div>
      <div className="world-field-bar small">
        <span className="muted" data-testid="world-field-caption">
          {caption ?? (blocked ? "有遭遇：先開戰或撤退" : "點格子走過去・方向鍵／WASD 走一格・E 互動")}
        </span>
        {onStone && field.stone_targets.length > 0 && (
          <span className="world-field-stone" data-testid="world-field-stone">
            {field.stone_targets.map((t) => (
              <button key={t.id} type="button" disabled={busy || walking || blocked} onClick={() => teleport(t.id)} data-testid="world-teleport-stone">
                傳送：{t.name_zh}
              </button>
            ))}
          </span>
        )}
        {onStone && field.stone_targets.length === 0 && <span className="muted">傳送石已點亮（還沒有別的傳送石可以去）</span>}
      </div>
    </div>
  );
}
