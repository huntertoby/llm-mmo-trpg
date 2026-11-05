// 可走動的實地地圖畫面（Phase 6B-3；docs/phases/Phase6計畫.md 第 5 節）：用戰鬥的 `BattleRenderer` 畫 `WorldView.field`，
// 點格子走過去（前端 BFS，超過 30 格分段送）、方向鍵／WASD 一次一格（排隊，同時只有一個請求在路上）、
// 小人逐格走（每格約 0.12 秒；6M-3 起播走路片段、照高低差走上去或跳上去，NPC 與敵群走一格也播）、換地圖淡出淡入。走到設施或 NPC 旁邊按 E 或點它就開原本的面板；
// 站在傳送石上顯示「傳送」按鈕。位置一律以伺服器回來的 `walk` 結果為準，失敗時顯示錯誤、位置不動。
// 6B-6：HUD 版面時格子照戰鬥的預設大小，鏡頭跟著主角（`camera.ts`）；畫布在可視區裡平移，逐格走時鏡頭用同樣的時間平滑跟上。
// 點擊換算沿用 `BattleCanvas` 的 `getBoundingClientRect()`（平移後的實際位置），所以鏡頭位移自動算進去。
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import type { FieldView, Pos, WorldAction, WorldView } from "../api/types";
import { fitScale, scaledSize } from "../battle/stageLayout";
import type { BattleRenderer } from "../render/BattleRenderer";
import { topReserve } from "../battle/elevation";
import { BattleCanvas } from "../ui/BattleCanvas";
import { cameraTransform, canvasSize, frameCamera, followCamera, FIELD_SCALE, type Camera, type TileRect, type ViewInsets } from "./camera";
import type { Rect } from "./hud";
import { devCameraShift, shiftCamera } from "./devCamera";
import { bridgeCells, captionShiftDecor, decorCellRect, lampRect, nudgeCamera, personRect, placeTag, steleRect, tagSize, unionRect, type NudgeTarget } from "./hudAvoid";
import { FieldHeads, FieldSteleTags } from "./FieldHeads";
import { REGION_COLOR } from "../render/capitalArt";
import { exitTap } from "../render/exitSign";
import { GUIDE_BUBBLE_MS, mainQuestNpc, steleTags, type ViewBox } from "./opening";
import { openRegionsOf } from "./fieldScenery";
import { LevelPillar } from "./GainEffects";
import { peopleSteps } from "./peopleWalk";
import { arriveMap, leaveMap, mapTransit } from "./mapTransit";
import { playFieldStep } from "./fieldSteps";
import { frozenFriends, headAnchor, headMarks, npcBubbles, type GuideLines, type HeadMark } from "./fieldPeople";
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
  /**
   * HUD 各塊的實際矩形（舞台座標；`hudAvoid.hudAvoidRects`）。RT-5b：跟隨時鏡頭在附近微調，讓露出一部分的
   * 重要東西（開場說話的人、主線給任務的人、橋頭石碑）不被 HUD 蓋住；石碑小牌壓到 HUD 時換邊。省略＝不微調。
   */
  avoid?: readonly Rect[];
  /** 微調時地圖邊緣最多捲到哪（`hudAvoid.hudReach`：下方算到說明列上緣）；省略＝`insets`。 */
  reach?: ViewInsets;
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
/** 開發模式的鏡頭位移（RT-5d；`?dev=1&devcam=dx,dy`），網址在載入時讀一次。 */
const DEV_CAM = typeof window === "undefined" ? null : devCameraShift(window.location.search);

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
  // RT-5b 必修 6：開場的指示整句留約 8 秒，之後收成只剩「！」（點了再展開，再留 8 秒）；「！」留到到過霧渡鎮（`guides` 變空）
  const guideKey = [...guides.keys()].join(",");
  const [guideFolded, setGuideFolded] = useState(false);
  const guideTimer = useRef<number | null>(null);
  const openGuide = useCallback(() => {
    setGuideFolded(false);
    if (guideTimer.current !== null) window.clearTimeout(guideTimer.current);
    guideTimer.current = window.setTimeout(() => setGuideFolded(true), GUIDE_BUBBLE_MS);
  }, []);
  useEffect(() => {
    if (guideKey !== "") openGuide();
    return () => {
      if (guideTimer.current !== null) window.clearTimeout(guideTimer.current);
    };
  }, [guideKey, openGuide]);
  const mainNpc = mainQuestNpc(view.guide, field);
  const mail = view.mail ?? null; // 6T-1b：郵差頭上的「✉」
  const marks = useMemo(() => headMarks(field, bubbles, guides, { main: mainNpc, guideFolded, mail }), [field, bubbles, guides, mainNpc, guideFolded, mail]);
  const steles = useMemo(() => steleTags(field, view.atlas), [field, view.atlas]);
  const rendererRef = useRef<BattleRenderer | null>(null);
  // 失敗時重畫一次（動畫可能已經把小人移走；以舊位置為準）
  const [redraw, setRedraw] = useState(0);
  // 6D-ART2：主城傳送陣的光圈照大世界圖已開放的區（不新增伺服器欄位）
  const openKey = openRegionsOf(view.atlas).join(",");
  const model = useMemo(() => fieldDrawModel(field, view.character.name, openKey === "" ? [] : openKey.split(",")), [field, view.character.name, openKey, redraw]);
  const [hover, setHover] = useState<Pos | null>(null);
  // UI-E4：觸控點一下出口先亮綠框與目的地名（`armed`），再點一次同一個出口才走過去；滑鼠照舊點了就走
  const pointerKind = useRef("mouse");
  const [armed, setArmed] = useState<{ id: string; pos: Pos } | null>(null);
  useEffect(() => setArmed(null), [field.map_id]);
  const highlights = useMemo(() => fieldHighlights(field, hover, armed?.pos ?? null), [field, hover, armed]);
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
  const rch = hud?.reach;
  const reachKey = rch === undefined ? "" : `${rch.top},${rch.right},${rch.bottom},${rch.left}`;
  const insetKey = ins === undefined ? "" : `${ins.top},${ins.right},${ins.bottom},${ins.left}`;
  // `avoid` 每次重畫都是新的陣列：只看數值
  const avoidKey = (hud?.avoid ?? []).map((r) => `${Math.round(r.left)},${Math.round(r.top)},${Math.round(r.width)},${Math.round(r.height)}`).join(";");
  const avoid = useMemo<Rect[]>(
    () =>
      avoidKey === ""
        ? []
        : avoidKey.split(";").map((k) => {
            const [left = 0, top = 0, width = 0, height = 0] = k.split(",").map(Number);
            return { left, top, width, height };
          }),
    [avoidKey],
  );
  // 鏡頭微調要看的東西（畫布座標，縮放＝FIELD_SCALE）：開場說話的人與主線給任務的人（含頭上的「！」）、橋頭石碑（含上方的小牌）
  // RT-5c（小修 7、8）：浮橋連同相鄰的每一段（兩格寬的橋第二段被任務欄蓋住）；石碑碑身另外再算一個目標
  // （整座橋＋小牌移不到全露出來時，至少讓碑身不被說明列壓住）。
  const lookAt = useMemo<NudgeTarget[]>(() => {
    // 分數（`NudgeTarget.weight`）：主線的人與碑身 3、石碑＋小牌＋整座浮橋 1（小牌壓到 HUD 時還能自己換邊）
    const mains = marks.filter((m) => m.main).map((m) => ({ ...personRect(model, m.pos, FIELD_SCALE), weight: 3 }));
    const bodies: NudgeTarget[] = [];
    const stones = steles.map((t) => {
      const body = steleRect(model, { x: t.x, y: t.y }, FIELD_SCALE);
      // RT-5d（小修 3）：碑身被下方 HUD 蓋住時，鏡頭可以多往上推（`far`，最多 `NUDGE_FAR`）
      bodies.push({ ...body, weight: 3, far: true });
      const size = tagSize(t.name, t.sub);
      const tag = placeTag(body, size, null, null, []);
      const withTag = unionRect(body, { left: tag.left, top: tag.top, width: size.width, height: size.height });
      // 連同這座石碑的浮橋（`bridge_<區域>`；地圖邊上那一格）與相鄰的每一段浮橋
      const bridge = field.situation_objects.find((o) => o.id === `bridge_${t.region}`);
      if (bridge === undefined) return withTag;
      return bridgeCells(field.objects, bridge).reduce((acc, p) => unionRect(acc, steleRect(model, p, FIELD_SCALE)), withTag);
    });
    return [...mains, ...stones, ...bodies];
  }, [marks, steles, model, field.situation_objects, field.objects]);
  // RT-5c（必修 3、4）：地圖上所有人物的格子（主角、隊友、NPC、朋友）：石碑小牌避開他們（含腳下的徽章與光圈），
  // 夾到畫面邊的開場指示避開他們的頭
  const people = useMemo(() => model.units.map((u) => ({ x: u.x, y: u.y })), [model]);
  const cam = useMemo<Camera | null>(() => {
    if (!hasHud) return null;
    const viewSize = { width: hudW, height: hudH };
    if (frameKey === "") {
      const [top = 0, right = 0, bottom = 0, left = 0] = insetKey === "" ? [] : insetKey.split(",").map(Number);
      const insets = { top, right, bottom, left };
      const follow = followCamera(viewSize, model, focus.pos, FIELD_SCALE, insets);
      const hero = personRect(model, focus.pos, FIELD_SCALE);
      const [rt = top, rr = right, rb = bottom, rl = left] = reachKey === "" ? [] : reachKey.split(",").map(Number);
      // RT-5c（小修 5）：畫布最上面留給高的東西（`topReserve`，透明）；深色帶從第一排格子算，所以上限再扣掉這一段
      const reach = { top: rt - topReserve(model) * FIELD_SCALE, right: rr, bottom: rb, left: rl };
      // RT-5d（必修 2）：開發模式的 `devcam=dx,dy` 把鏡頭推開（拍 1600 寬的夾邊畫面用）；正式畫面沒有位移
      return shiftCamera(avoid.length === 0 ? follow : nudgeCamera({ cam: follow, view: viewSize, content: canvasSize(model, FIELD_SCALE), insets, reach, avoid, hero, targets: lookAt }), DEV_CAM);
    }
    const [x = 0, y = 0, width = 0, height = 0] = frameKey.split(",").map(Number);
    return frameCamera(viewSize, model, { x, y, width, height });
  }, [hasHud, hudW, hudH, frameKey, insetKey, reachKey, model, focus.pos, avoid, lookAt]);
  const onCamera = hud?.onCamera;
  useEffect(() => {
    if (cam !== null) onCamera?.(cam);
  }, [cam, onCamera]);
  const scale = cam?.scale ?? fitScale(avail, model, undefined, 0.4, 1.5);
  // RT-5：開場說話的人在畫面外時，泡泡夾到畫面邊上（畫布座標）：`visible`＝整個可視區（判斷在不在畫面裡），
  // `safe`＝扣掉 HUD 四邊的安全區（夾進去的位置，不壓到主角卡、小地圖）。
  const viewBoxes = useMemo<{ safe: ViewBox; visible: ViewBox } | null>(() => {
    if (cam === null) return null;
    const [top = 0, right = 0, bottom = 0, left = 0] = insetKey === "" ? [] : insetKey.split(",").map(Number);
    return {
      safe: { left: cam.x + left, top: cam.y + top, right: cam.x + hudW - right, bottom: cam.y + hudH - bottom },
      visible: { left: cam.x + 8, top: cam.y + 8, right: cam.x + hudW - 8, bottom: cam.y + hudH - 8 },
    };
  }, [cam, insetKey, hudW, hudH]);

  // RT-5c（小修 7）：說明列壓到碑身或主線的人（鏡頭微調移不開時）就水平挪開。說明列 `left: 50%`＋`translateX(-50%)`：
  // `offsetLeft` 不含 transform，所以原本的左緣＝offsetLeft − 寬/2。
  // RT-5d（小修 4）：說明列盡量不壓的裝飾物：源晶燈（柱身）、花壇
  const lamps = useMemo(
    () => [
      ...field.objects.filter((o) => o.look === "crystal_lamp").map((o) => lampRect(model, o, FIELD_SCALE)),
      ...(field.decor ?? []).filter((d) => d.kind === "flower_bed").map((d) => decorCellRect(model, d, FIELD_SCALE)),
    ],
    [field.objects, field.decor, model],
  );
  const capRef = useRef<HTMLDivElement | null>(null);
  const [capDx, setCapDx] = useState(0);
  useLayoutEffect(() => {
    const el = capRef.current;
    if (cam === null || el === null || frame !== null) {
      setCapDx(0);
      return;
    }
    const w = el.offsetWidth;
    const cap = { left: el.offsetLeft - w / 2, top: el.offsetTop, width: w, height: el.offsetHeight };
    const toStage = (t: { left: number; top: number; width: number; height: number }) => ({ left: t.left - cam.x, top: t.top - cam.y, width: t.width, height: t.height });
    const obstacles = lookAt.filter((t) => (t.weight ?? 1) >= 3).map(toStage);
    // RT-5d（小修 4）：也盡量不壓源晶燈的柱身、花壇（裝飾物；讓不開就照 RT-5c 只避開碑身與主線的人）
    setCapDx(captionShiftDecor(cap, obstacles, lamps.map(toStage), avoid, hudW));
  }, [cam, lookAt, lamps, avoid, hudW, frame, hover]);

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
    const tap = exitTap(model.exitSigns ?? [], tile, pointerKind.current, armed?.id ?? null);
    setArmed(tap.arm === null ? null : { id: tap.arm, pos: tile });
    if (tap.arm !== null) return;
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

  const caption = hoverText(field, hover ?? armed?.pos ?? null);
  return (
    <div
      className={`world-field${hud !== undefined ? " hud" : ""}`}
      data-testid="world-field"
      ref={boxRef}
      onPointerDownCapture={(e) => {
        pointerKind.current = e.pointerType;
      }}
    >
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
            <FieldSteleTags tags={steles} grid={model} scale={scale} colors={REGION_COLOR} cam={cam} view={hasHud ? { width: hudW, height: hudH } : null} avoid={avoid} people={people} />
            <FieldHeads
              marks={marks}
              grid={model}
              scale={scale}
              onPick={pick}
              onExpand={openGuide}
              view={viewBoxes?.safe ?? null}
              visible={viewBoxes?.visible ?? null}
              heads={people.map((p) => headAnchor(model, p, scale))}
            />
            <LevelPillar view={view} grid={model} at={field.me} scale={scale} />
          </div>
        </CameraBox>
      </div>
      <div
        className="world-field-bar small"
        ref={capRef}
        data-shift={capDx !== 0 ? capDx : undefined}
        style={capDx !== 0 ? ({ "--cap-dx": `${capDx}px` } as CSSProperties) : undefined}
      >
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
