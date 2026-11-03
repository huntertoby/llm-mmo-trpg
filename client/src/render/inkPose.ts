// 紙娃娃的骨架姿勢（Phase 6M-1；需求 docs/art/動畫移植需求.md 第 1 節，照樣張 docs/art/sample/storyDoll.js 的 setPose）。
// 角度一律是畫布旋轉（順時針為正，弧度）；位移是虛擬像素（往下為正）。部件的畫法不改，只在關節外面包一層旋轉／位移。
// 沒設姿勢（`null`／不傳）時，inkDoll 畫出來和加鉤子之前逐像素相同（inkDollSnapshot.test.ts 鎖住）。
// 這裡只放資料型別與純函式小工具；走路、跑步等片段（時間 → 姿勢）在 6M-3 另做。

/** 一個姿勢；每個欄位都可省略（＝ 0，或照預設）。 */
export interface InkPose {
  /** 整個人的起伏（y 位移，負＝往上）。 */
  bob?: number;
  /** 側面：上半身以髖 (0,-15) 為軸前傾（正＝往面向方向傾）；腿會抵銷，腳留在地上。 */
  lean?: number;
  /** 側面：近側、遠側腿的髖（正＝往前踢）。 */
  hipN?: number;
  hipF?: number;
  /** 側面：近側、遠側膝（正＝小腿往後彎）。 */
  kneeN?: number;
  kneeF?: number;
  /** 側面：主手（近側）繞肩 (0,-31.6)。 */
  arm?: number;
  /** 側面：主手手肘（前臂繞手肘）。 */
  elbow?: number;
  /** 側面：另一隻手（遠側）繞肩。 */
  armF?: number;
  /** 側面：另一隻手的手肘。 */
  elbowF?: number;
  /** 主手武器繞手的角度。6M-1：相對現有握法的增量（沒給＝現有握法）；6M-2 武器統一後改成「相對手」的絕對角度。 */
  wpn?: number;
  /** 正面、背面：主手側（liftL）、副手側（liftR）抬腳的高度（正＝抬高）。 */
  liftL?: number;
  liftR?: number;
  /** 正面、背面：主手側（armL）、副手側（armR）手臂上下擺（y 位移）。 */
  armL?: number;
  armR?: number;
  /** 弓弦拉開的距離（6M-2 弓統一畫法後才會用到；6M-1 先保留欄位）。 */
  pull?: number;
}

export type PoseKey = keyof InkPose;

/** 全部欄位（固定順序；工具函式依這個順序走，不依賴物件鍵的順序）。 */
export const POSE_KEYS: readonly PoseKey[] = ["bob", "lean", "hipN", "hipF", "kneeN", "kneeF", "arm", "elbow", "armF", "elbowF", "wpn", "liftL", "liftR", "armL", "armR", "pull"];

/** 站好的姿勢（全部 0、武器照預設握法）。畫出來和「沒設姿勢」幾乎一樣，但會走姿勢的畫法（側面手肘、另一隻手）。 */
export const REST_POSE: Readonly<InkPose> = Object.freeze({});

/** 讀一個欄位；沒給或不是有限數字 → 0。 */
export function pz(p: InkPose | null | undefined, k: PoseKey): number {
  const v = p?.[k];
  return typeof v === "number" && Number.isFinite(v) ? v : 0;
}

/** 只留有限數字的欄位（外部資料進來時先過這一關）。`wpn` 沒給時維持沒給（＝ 預設握法）。 */
export function cleanPose(p: Readonly<Record<string, unknown>>): InkPose {
  const out: InkPose = {};
  for (const k of POSE_KEYS) {
    const v = p[k];
    if (typeof v === "number" && Number.isFinite(v)) out[k] = v;
  }
  return out;
}

/** 兩個姿勢內插（t 0→1）。`wpn`：兩邊都沒給時維持沒給，一邊沒給當 0。 */
export function mixPose(a: InkPose, b: InkPose, t: number): InkPose {
  const out: InkPose = {};
  for (const k of POSE_KEYS) {
    if (a[k] === undefined && b[k] === undefined) continue;
    const x = pz(a, k);
    out[k] = x + (pz(b, k) - x) * t;
  }
  return out;
}

/** 疊加姿勢（例如走路循環＋上半身的出招）：各欄位相加；`wpn` 兩邊都沒給時維持沒給。 */
export function addPose(...ps: InkPose[]): InkPose {
  const out: InkPose = {};
  for (const k of POSE_KEYS) {
    if (ps.every((p) => p[k] === undefined)) continue;
    out[k] = ps.reduce((s, p) => s + pz(p, k), 0);
  }
  return out;
}

/** 放大／縮小擺幅（例如潛行擺幅較小）；`bob`、位移類一起縮放。 */
export function scalePose(p: InkPose, k: number): InkPose {
  const out: InkPose = {};
  for (const key of POSE_KEYS) if (p[key] !== undefined) out[key] = pz(p, key) * k;
  return out;
}
