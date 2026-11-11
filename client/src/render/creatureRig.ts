// 異形的動畫掛點（RIG）與 Q 大頭的支點（CB-3 從 inkCreature.ts 搬出：inkCreature 畫部件、qCreatureAnim 算姿勢都要讀，兩邊不互相匯入）。
import type { Pt } from "./inkStyle";

/** Q 大頭：[第一個頭部部件的名稱開頭, 支點 x, 支點 y, 倍率, 結束部件的名稱開頭（選填）]。 */
export type QHeadDef = readonly [string, number, number, number, string?];
/** 每款身形固定的 Q 大頭（飛禽依款式另列在 inkCreature 的 BODIES）。 */
export const Q_HEADS: Readonly<Record<string, QHeadDef>> = {
  hound: ["hd-ear", 12, -22, 1.3],
  boar: ["bo-ear", 11, -15, 1.25],
  bear: ["be-head", 11, -21, 1.3],
  lizard: ["lz-head", 13, -9, 1.3],
  serpent: ["sn-head", 6, -23, 1.3],
  shell: ["sh-head", 12, -7, 1.3],
  golem: ["go-head", 1, -40, 1.28, "go-arm"],
  feline: ["fe-ear", 11, -12, 1.35],
};

// ============================== 動畫掛點（RIG）：部件名稱開頭 → 部件組；組的支點 ==============================
// 腿：支點在髖／肩（埋在身體裡），動畫用斜切 kx＋sy，不會和身體脫開。腿名：BF 遠後、FF 遠前、BN 近後、FN 近前。
export interface RigDef {
  groups: ReadonlyArray<readonly [string, string]>;
  pivots: Readonly<Record<string, Pt>>;
}
export const RIG: Readonly<Record<string, RigDef>> = {
  hound: { groups: [["hd-lf-12", "BF"], ["hd-lf6", "FF"], ["hd-l-9", "BN"], ["hd-l8", "FN"], ["hd-tail", "tail"], ["hd-ear", "head"], ["hd-head", "head"], ["hd-fang", "head"]], pivots: { BF: [-10, -15], FF: [8, -15], BN: [-7, -16], FN: [10, -16], tail: [-14, -18], head: [12, -21], body: [0, -12] } },
  boar: { groups: [["bo-lf-10", "BF"], ["bo-lf6", "FF"], ["bo-l-7", "BN"], ["bo-l8", "FN"], ["bo-tail", "tail"], ["bo-ear", "head"], ["bo-head", "head"], ["bo-snout", "head"], ["bo-tusk", "head"]], pivots: { BF: [-8, -12], FF: [8, -12], BN: [-5, -12], FN: [10, -12], tail: [-15, -16], head: [11, -15], body: [0, -9] } },
  bear: { groups: [["be-lf-11", "BF"], ["be-lf6", "FF"], ["be-l-6", "BN"], ["be-l11", "FN"], ["be-head", "head"], ["be-ear", "head"], ["be-snout", "head"]], pivots: { BF: [-11, -15], FF: [6, -15], BN: [-6, -15], FN: [11, -15], head: [12, -22], body: [0, -10] } },
  bat: { groups: [["fl-bwf", "wingF"], ["fl-bwn", "wingN"], ["fl-be", "head"], ["fl-bhead", "head"], ["fl-bfang", "head"]], pivots: { wingF: [-1, -2], wingN: [2, -2], head: [4, -3], body: [0, 0] } },
  bird: { groups: [["fl-wf", "wingF"], ["fl-tail", "tail"], ["fl-wn", "wingN"], ["fl-sh", "wingN"], ["fl-head", "head"], ["fl-beak", "head"], ["fl-claw", "legs"]], pivots: { wingF: [-1, -3], wingN: [3, -3], tail: [-8, 0], head: [6, -2], legs: [0, 4], body: [0, 0] } },
  spider: {
    groups: [["sp-lf0", "F0"], ["sp-lf1", "F1"], ["sp-lf2", "F2"], ["sp-lf3", "F3"], ["sp-abd", "abd"], ["sp-sh", "spikes"], ["sp-mark", "abd"], ["sp-head", "head"], ["sp-eyes", "head"], ["sp-fang", "head"], ["sp-l0", "N0"], ["sp-l1", "N1"], ["sp-l2", "N2"], ["sp-l3", "N3"]],
    pivots: { F0: [-1.2, -10.6], F1: [0.8, -10.6], F2: [2.8, -10.6], F3: [4.8, -10.6], N0: [1, -10], N1: [3, -10], N2: [5, -10], N3: [7, -10], abd: [-3, -10], spikes: [-9, -19.5], head: [2, -9], body: [0, -6] },
  },
  beetle: { groups: [["bt-lf0", "F0"], ["bt-lf1", "F1"], ["bt-lf2", "F2"], ["bt-l0", "N0"], ["bt-l1", "N1"], ["bt-l2", "N2"], ["bt-head", "head"], ["bt-horn", "head"], ["bt-eye", "head"], ["bt-sh", "spikes"]], pivots: { F0: [-6, -7], F1: [2, -7], F2: [9, -7], N0: [-8, -7], N1: [0, -7], N2: [7, -7], head: [11, -10], spikes: [-2, -20], body: [0, -8] } },
  lizard: { groups: [["lz-lf-6", "BF"], ["lz-lf9", "FF"], ["lz-l-7", "BN"], ["lz-l10", "FN"], ["lz-tail", "tail"], ["lz-head", "head"]], pivots: { BF: [-6, -7], FF: [9, -7], BN: [-7, -8], FN: [10, -8], tail: [-8, -7.5], head: [13, -10], body: [2, -8] } },
  serpent: { groups: [["sn-coil", "coil"], ["sn-sh", "coil"], ["sn-neck", "neck"], ["sn-belly", "neck"], ["sn-head", "head"], ["sn-tongue", "head"]], pivots: { coil: [-4, -1], neck: [5, -6], head: [7, -24], body: [0, -6] } },
  shell: { groups: [["sh-lf-9", "BF"], ["sh-lf6", "FF"], ["sh-l-11", "BN"], ["sh-l5", "FN"], ["sh-head", "head"]], pivots: { BF: [-10, -9], FF: [5, -9], BN: [-9, -9], FN: [8, -9], head: [12, -8], body: [0, -6] } },
  ooze: { groups: [["oz-face", "face"]], pivots: { face: [6, -10], body: [0, 0] } },
  golem: { groups: [["go-legf", "legF"], ["go-armf", "armF"], ["go-legn", "legN"], ["go-head", "head"], ["go-eye", "head"], ["go-arm", "armN"], ["go-fist", "armN"]], pivots: { legF: [-4, -17], legN: [3, -17], armF: [-11, -35], armN: [7, -37], head: [1, -40], body: [0, -16] } },
  wisp: { groups: [["wp-or0", "orb0"], ["wp-or1", "orb1"], ["wp-or2", "orb2"], ["wp-core", "core"], ["wp-in", "core"]], pivots: { orb0: [-11, -5], orb1: [10, -8], orb2: [3, 9], core: [0, 0], body: [0, 0] } },
  feline: { groups: [["fe-lf-8", "BF"], ["fe-lf10", "FF"], ["fe-l-11", "BN"], ["fe-l7", "FN"], ["fe-tail", "tail"], ["fe-ear", "head"], ["fe-head", "head"], ["fe-muzzle", "head"]], pivots: { BF: [-8, -12], FF: [10, -12], BN: [-11, -12], FN: [7, -12], tail: [-12, -11], head: [11, -12], body: [0, -9] } },
  wraith: { groups: [["wr-arm-l", "armB"], ["wr-arm-r", "armN"], ["wr-head", "head"]], pivots: { armB: [-7, -30], armN: [7, -30], head: [0, -33], body: [0, -20] } },
  pylon: { groups: [["py-base", "base"], ["py-ob", "ob"], ["py-eye", "eye"], ["py-ring", "ring"]], pivots: { base: [0, 0], ob: [0, -5], eye: [1.6, -22], ring: [0, -22], body: [0, -5] } },
};
