// 開發用：QK-5 正面、背面走路與五類出招（`doll-gallery.html?skin=q&set=fb[&steps=7|25][&mode=game|sample]`）。
// 版面同樣張 docs/art/sample/q-anim-fb.html 的 ?dump=strip（每格 150×262、主角 2 倍、正面敵人格在下方、背面在上方），
// 右邊的並排圖用：遊戲的畫法（qStamp＋遊戲的 qAnimFB 關鍵幀與插值）。特效、傷害數字是戰場另畫的，這裡不畫。
// steps＝每列幾格：7（關鍵幀 0～6）或更多（插值的連續格，gif 用）。
import type { QPose, QUnit, QView } from "../render/qCore";
import { SAMPLE_HOOKS, sampleUnit } from "../render/qSample";
import { qStamp } from "../render/qStamp";
import { gaitPose } from "../render/motionClips";
import { FB_KINDS, fbKindIndex, type FbKind } from "../render/qAnimFB";

const CW = 150;
const CH = 262;
const HK = 2.0;
const TK = 1.7;
const FONT = "'Noto Sans TC','Microsoft JhengHei',sans-serif";
const TAU = Math.PI * 2;
const ZH: Readonly<Record<string, string>> = { walk: "走路", sword: "劍・揮砍", spear: "長槍・刺", bow: "弓・拉放", staff: "法杖・施法", gauntlet: "拳・拳套" };
const UNITS: Readonly<Record<string, QUnit>> = {
  walk: sampleUnit("sword"),
  sword: sampleUnit("sword"),
  spear: sampleUnit("spear"),
  bow: sampleUnit("bow"),
  staff: { ...sampleUnit("staff"), gear: { ...sampleUnit("staff").gear, main_hand: { kind: "staff", element: "fire" } } },
  gauntlet: sampleUnit("gauntlet"),
};
const FOE: QUnit = {
  look: { skin: "#a8724c", hair: "short", hairColor: "#1a1a1a" },
  gear: { body: { kind: "shirt", color: "#7a6a4a" }, feet: { kind: "boots", material: "leather" }, main_hand: { kind: "axe", material: "iron" }, head: { kind: "hood", color: "#8a7a5a" } },
};

const geom = (view: QView): { hy: number; ty: number } => (view === "front" ? { hy: 150, ty: 250 } : { hy: 250, ty: 108 });

function tiles(c: CanvasRenderingContext2D, G: { hy: number; ty: number }): void {
  c.fillStyle = "#6a9a6a";
  c.fillRect(0, 0, CW, CH);
  for (const [y, foe] of [[G.hy, false], [G.ty, true]] as const) {
    const T = 100;
    const x0 = 75 - T / 2;
    const y0 = y - T * 0.62;
    c.fillStyle = foe ? "rgba(120,40,40,0.16)" : "rgba(255,255,255,0.07)";
    c.fillRect(x0, y0, T, T);
    c.strokeStyle = foe ? "rgba(150,40,40,0.55)" : "rgba(0,0,0,0.22)";
    c.lineWidth = 1;
    c.strokeRect(x0 + 0.5, y0 + 0.5, T - 1, T - 1);
  }
}
function target(c: CanvasRenderingContext2D, G: { ty: number }, view: QView): void {
  const o = document.createElement("canvas");
  o.width = CW;
  o.height = CH;
  const x = o.getContext("2d")!;
  qStamp(x, FOE, view === "front" ? "back" : "front", 75, G.ty, TK, false, SAMPLE_HOOKS, null);
  x.globalCompositeOperation = "source-atop";
  x.fillStyle = "rgba(58,34,44,0.82)";
  x.fillRect(0, 0, CW, CH);
  c.beginPath();
  c.ellipse(75, G.ty, 30, 6, 0, 0, TAU);
  c.fillStyle = "rgba(0,0,0,0.22)";
  c.fill();
  c.drawImage(o, 0, 0);
}

/** 一格：kind＝walk 或五類之一；u＝0～6（關鍵幀時間，可帶小數＝插值）。 */
export function fbCell(c: CanvasRenderingContext2D, kind: string, view: QView, u: number): void {
  const G = geom(view);
  const front = view === "front";
  c.save();
  c.beginPath();
  c.rect(0, 0, CW, CH);
  c.clip();
  tiles(c, G);
  if (!front) target(c, G, view);
  const P: QPose =
    kind === "walk"
      ? (() => {
          const p = gaitPose((u / 7) * TAU, "walk");
          return { bob: p.bob ?? 0, liftL: p.liftL ?? 0, liftR: p.liftR ?? 0, armL: p.armL ?? 0, armR: p.armR ?? 0 };
        })()
      : { fbk: fbKindIndex(kind as FbKind), fbt: u };
  c.beginPath();
  c.ellipse(75, G.hy, 34, 7, 0, 0, TAU);
  c.fillStyle = "rgba(0,0,0,0.25)";
  c.fill();
  qStamp(c, UNITS[kind]!, view, 75, G.hy, HK, false, SAMPLE_HOOKS, P);
  if (front) target(c, G, view);
  c.restore();
}

export const FB_ROWS: ReadonlyArray<readonly [string, QView]> = [["walk", "front"], ["walk", "back"], ...FB_KINDS.flatMap((k) => [[k, "front"], [k, "back"]] as [string, QView][])];

/** 整張：每列 steps 格（7＝關鍵幀）。only＝"sword-front,…"。 */
export function fbSheet(steps: number, only: string | null): HTMLCanvasElement {
  const rows = FB_ROWS.filter(([k, v]) => !only || only.split(",").includes(`${k}-${v}`));
  const LW = 150;
  const HD = 34;
  const cv = document.createElement("canvas");
  cv.width = LW + steps * (CW + 1);
  cv.height = HD + rows.length * (CH + 6);
  const x = cv.getContext("2d")!;
  x.fillStyle = "#14161f";
  x.fillRect(0, 0, cv.width, cv.height);
  x.fillStyle = "#f2e6c8";
  x.font = `bold 16px ${FONT}`;
  x.fillText(`遊戲（QK-5）：正面、背面走路與五類出招（${steps === 7 ? "關鍵幀 0～6" : `插值 ${steps} 格`}）`, 10, 22);
  rows.forEach(([k, v], r) => {
    const y0 = HD + r * (CH + 6);
    x.fillStyle = "#e8bb48";
    x.font = `bold 14px ${FONT}`;
    x.fillText(`${ZH[k]}・${v === "front" ? "正面" : "背面"}`, 8, y0 + 22);
    for (let f = 0; f < steps; f++) {
      const u = steps === 7 ? f : (f / (steps - 1)) * 6;
      x.save();
      x.translate(LW + f * (CW + 1), y0);
      fbCell(x, k, v, u);
      x.fillStyle = "rgba(20,22,31,0.7)";
      x.fillRect(0, 0, 34, 17);
      x.fillStyle = "#f2e6c8";
      x.font = `11px ${FONT}`;
      x.fillText(steps === 7 ? String(f) : u.toFixed(2), 4, 13);
      x.restore();
    }
  });
  return cv;
}

// ---- QK-5：腿短片段（跳躍、蹲低、跪地、滑倒…）收斂前後（`set=legs`）----
import { clipDef, type ClipId } from "../render/skillClips";
import { qLegFit } from "../render/qSpec";
import type { InkPose } from "../render/inkPose";

const LEG_CLIPS: readonly string[] = ["leap_air", "stab_ground", "ground_punch", "palm_ground", "kneel_lift", "crouch_place", "rally_up", "sweep_low", "stomp_raise", "press_lower", "hop_slash", "leap_thrust", "knee_strike", "spin_kick", "low_thrust"];
const EXTRA: ReadonlyArray<readonly [string, InkPose]> = [
  ["閃避・蹲低", { kneeN: 1.5, kneeF: 1.3, hipN: 0.8, hipF: 0.6, bob: 8, lean: 0.4, arm: -0.6, elbow: -1.2, armF: -0.6, elbowF: -1.2 }],
  ["倒下・膝軟", { kneeN: 1.4, kneeF: 1.2, hipN: 0.7, hipF: 0.5, bob: 7, lean: 0.25, arm: 0.3, armF: 0.35 }],
  ["陷阱夾住", { kneeN: 0.6, kneeF: 0.5, bob: 2.5, lean: 0.18, arm: -0.6, armF: -0.7 }],
];
/** 每個片段取膝蓋彎最多的那個關鍵姿勢。 */
function legRows(): Array<readonly [string, InkPose]> {
  const rows: Array<readonly [string, InkPose]> = [];
  for (const id of LEG_CLIPS) {
    let def;
    try {
      def = clipDef(id as ClipId);
    } catch {
      continue;
    }
    let best: InkPose = {};
    let s = -1;
    for (const [, p] of def.keys) {
      const v = Math.abs(p.kneeN ?? 0) + Math.abs(p.kneeF ?? 0) + Math.abs(p.hipN ?? 0) + Math.max(0, p.bob ?? 0) * 0.2;
      if (v > s) {
        s = v;
        best = p;
      }
    }
    rows.push([id, best]);
  }
  return [...rows, ...EXTRA];
}
export function legSheet(): HTMLCanvasElement {
  const rows = legRows();
  const S = 2.6;
  const W = 120;
  const H = 120;
  const cv = document.createElement("canvas");
  cv.width = 150 + 4 * W;
  cv.height = 30 + rows.length * H;
  const x = cv.getContext("2d")!;
  x.fillStyle = "#2a2e40";
  x.fillRect(0, 0, cv.width, cv.height);
  x.fillStyle = "#f2e6c8";
  x.font = `bold 13px ${FONT}`;
  x.fillText("QK-5 腿短片段：左 2 格＝照搬 C 的值（朝東、正面），右 2 格＝Q 版收斂（qLegFit）", 8, 20);
  const u = sampleUnit("sword");
  rows.forEach(([zh, p], r) => {
    const y = 30 + r * H;
    x.fillStyle = "#e8bb48";
    x.font = `12px ${FONT}`;
    x.fillText(zh, 8, y + 60);
    const cells: Array<[InkPose, QView]> = [
      [p, "side"],
      [p, "front"],
      [qLegFit(p), "side"],
      [qLegFit(p), "front"],
    ];
    cells.forEach(([q, v], i) => {
      const cx = 150 + i * W + W / 2;
      x.strokeStyle = "rgba(255,255,255,0.25)";
      x.beginPath();
      x.moveTo(cx - 40, y + H - 14);
      x.lineTo(cx + 40, y + H - 14);
      x.stroke();
      qStamp(x, u, v, cx, y + H - 14, S, false, SAMPLE_HOOKS, q as QPose);
    });
  });
  return cv;
}
