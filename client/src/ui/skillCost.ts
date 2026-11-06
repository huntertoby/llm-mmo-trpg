// 6F-7（美術 PM 驗收 6F-6 必修 1）：技能鈕第二行（代價）放不下時的縮寫與取捨（純函式）。
// 6F-6 讓代價最多兩行（長名字時一行），超出的部分被 CSS 的高度上限裁掉：
// 「灰燼與霜雪交織的鎖鏈陷阱」只剩「AP 2・法力 5・」，冷卻整段不見，結尾還掛著「・」。
// 這裡先估寬度，放不下時：
//   1. 一段一段換成縮寫，放得下就停（6F-8：先「冷卻 2 回合」→「冷卻 2」，再從後面縮「法力 5」→「法5」、「AP 2」→「AP2」……）；
//   2. 還放不下，從後面拿掉不是 AP、冷卻的段，最後一段加「…」。
// 「・」只放在段與段之間；RT-3b（美術 PM 6F-7 檢查必修 1：行尾不能留「・」）起「・」接在**下一段的開頭**，
// 換行點在「・」之前，所以每一行都不會以「・」結尾（新的一行可以以「・」開頭）；AP 與冷卻一定留著。
// 完整的代價照舊在滑過的技能卡上。

/** 估寬用的字寬（em）：中日韓字與全形符號 1、空白 0.3、其他半形 0.6（偏寬估，寧可早一點縮寫）。 */
export function textEm(s: string): number {
  let w = 0;
  for (const ch of s) {
    const c = ch.codePointAt(0) ?? 0;
    if (ch === " ") w += 0.3;
    else if (c >= 0x2e80 || (c >= 0x2000 && c <= 0x206f)) w += 1;
    else w += 0.6;
  }
  return w;
}

/**
 * 技能鈕第二行每行可用的寬度（em）。按鈕 184px − 左右內距 12 − 圖示 40 − 間距 6 − 框 2 ＝ 124px，
 * 字級 11px 約 11.3em；留一點餘裕用 10.8。
 */
export const COST_LINE_EM = 10.8;

/** 分隔符（接在前一段後面）。 */
export const COST_SEP = "・";
/** 有段被拿掉時，接在最後一段後面。 */
export const COST_MORE = "…";

const ABBREV: readonly [RegExp, string][] = [
  [/^AP (\d+)$/, "AP$1"],
  [/^法力 (\d+)$/, "法$1"],
  [/^耐力 (\d+)$/, "耐$1"],
  [/^源力 (\d+)$/, "源$1"],
  [/^HP (.+)$/, "HP$1"],
  // 6F-8（RT-3b 檢查第 2 節 5）：冷卻最短也寫「冷卻 2」，和冷卻中的鈕、其他卡一致（原本縮成「冷2」）
  [/^冷卻 (\d+)( 回合)?$/, "冷卻 $1"],
  [/^每場 (\d+) 次$/, "每場$1"],
  [/^傳說啟動$/, "傳說"],
  [/^被動／反應$/, "被動"],
  [/^代價：/, "代價"],
  [/^維持費/, "維持"],
  [/^失手/, "反噬"],
];

/** 一段代價的縮寫（「AP 2」→「AP2」、「冷卻 2 回合」→「冷2」）；不認得的段照原樣。 */
export function abbrevCost(part: string): string {
  for (const [re, to] of ABBREV) {
    if (re.test(part)) return to.includes("$") ? part.replace(re, to) : to;
  }
  return part;
}

/** 一定要留的段：AP 與冷卻（美術 PM：冷卻一定要保留）。 */
export function keepsCost(part: string): boolean {
  return /^AP ?\d/.test(part) || /^冷卻? ?\d/.test(part);
}

/** 照畫面的換行方式（每段不拆、「・」接在下一段的開頭、段與段之間換行）排的行數。`sep` 傳空字串時量已經接好「・」的 `costPieces`。 */
export function costLines(parts: readonly string[], lineEm = COST_LINE_EM, sep = COST_SEP): number {
  let lines = parts.length > 0 ? 1 : 0;
  let used = 0;
  parts.forEach((p, i) => {
    const w = textEm(p) + (i > 0 ? textEm(sep) : 0);
    if (used > 0 && used + w > lineEm) {
      lines += 1;
      used = 0;
    }
    used += w;
    // 一段本身就比一行寬：多出來的會被裁掉，當作放不下
    if (w > lineEm) lines = Number.POSITIVE_INFINITY;
  });
  return lines;
}

export interface FittedCost {
  /** 要畫的段（已縮寫或拿掉一些段）。 */
  parts: string[];
  /** 有段被拿掉：最後一段後面加「…」。 */
  more: boolean;
}

/**
 * 縮寫的順序（6F-8：只縮到放得下為止）：先縮冷卻（「冷卻 2 回合」→「冷卻 2」，只是拿掉「回合」），
 * 再從後面往前一段一段縮其他段。回傳段的索引。
 */
export function abbrevOrder(parts: readonly string[]): number[] {
  const idx = parts.map((_, i) => i);
  const cool = idx.filter((i) => /^冷卻 /.test(parts[i] ?? ""));
  const rest = idx.filter((i) => !cool.includes(i)).reverse();
  return [...cool, ...rest];
}

/**
 * 代價放進 `maxLines` 行：原樣 → 一段一段縮寫（`abbrevOrder`，放得下就停，不把每段都縮掉）→
 * 拿掉不是 AP、冷卻的段（從後面拿）並加「…」。
 */
export function fitCost(parts: readonly string[], maxLines: number, lineEm = COST_LINE_EM): FittedCost {
  if (costLines(parts, lineEm) <= maxLines) return { parts: [...parts], more: false };
  const short = [...parts];
  for (const i of abbrevOrder(parts)) {
    const to = abbrevCost(short[i] ?? "");
    if (to === short[i]) continue;
    short[i] = to;
    if (costLines(short, lineEm) <= maxLines) return { parts: short, more: false };
  }
  const kept = [...short];
  const keep = parts.map(keepsCost);
  const withMore = (xs: readonly string[]) => xs.map((p, i) => (i === xs.length - 1 ? `${p}${COST_MORE}` : p));
  for (let i = kept.length - 1; i >= 0 && costLines(withMore(kept), lineEm) > maxLines; i--) {
    if (keep[i] === true) continue;
    kept.splice(i, 1);
    keep.splice(i, 1);
  }
  return { parts: kept, more: kept.length < short.length };
}

/** 畫面上每段的字（RT-3b：「・」接在下一段的開頭；有拿掉的段時最後一段加「…」）。 */
export function costPieces(fit: FittedCost): string[] {
  const last = fit.parts.length - 1;
  return fit.parts.map((p, i) => `${i > 0 ? COST_SEP : ""}${p}${i === last && fit.more ? COST_MORE : ""}`);
}

/** 同 `costPieces`，但「・」留在上一段的行尾（UI-E3c 必修 2：技能面板的卡片換行後，第二行不以「・」開頭）。 */
export function costPiecesTrailing(fit: FittedCost): string[] {
  const last = fit.parts.length - 1;
  return fit.parts.map((p, i) => `${p}${i < last ? COST_SEP : fit.more ? COST_MORE : ""}`);
}

// ---------------------------------------------------------------- 技能名的斷行（RT-3b，6F-7 檢查必修 1）

/** 很長的名字（xlong，11px）每行可用的寬（em）：124px ÷ 11px ≈ 11.3，留一點餘裕。 */
export const NAME_LINE_EM = 10.8;
/** 兩行還放不下時縮到的字級（px）與每行寬（em，124px ÷ 10px ≈ 12.4，留餘裕）。 */
export const NAME_TIGHT_PX = 10;
export const NAME_TIGHT_LINE_EM = 11.9;
/** 適合斷行的字（斷在它後面）：「的」「之」「與」「和」「・」、空白。 */
const NAME_BREAK_AFTER = new Set(["的", "之", "與", "和", "・", " ", "·"]);
/** 每一行至少幾個字（最後一行不能只剩一個字）。 */
export const NAME_MIN_LINE = 2;

export interface NameLines {
  lines: string[];
  /** 兩行放不下：縮小字級（`NAME_TIGHT_PX`）。 */
  tight: boolean;
  /** 縮小後還放不下：第二行結尾加「…」（完整名字在技能卡上）。 */
  cut: boolean;
}

/** 名字拆成兩行：每行都放得下、每行至少兩個字；斷在「的」「之」這類字後面優先，其次是兩行平均。找不到回 null。 */
function splitTwo(chars: readonly string[], lineEm: number): string[] | null {
  const n = chars.length;
  let best: { k: number; score: number } | null = null;
  for (let k = NAME_MIN_LINE; k <= n - NAME_MIN_LINE; k++) {
    const a = chars.slice(0, k).join("");
    const b = chars.slice(k).join("");
    if (textEm(a) > lineEm || textEm(b) > lineEm) continue;
    const natural = NAME_BREAK_AFTER.has(chars[k - 1] ?? "") ? 3 : 0;
    const score = Math.abs(k - n / 2) - natural;
    if (best === null || score < best.score) best = { k, score };
  }
  return best === null ? null : [chars.slice(0, best.k).join("").trimEnd(), chars.slice(best.k).join("").trimStart()];
}

/** 很長的名字怎麼排：一行放得下就一行；否則兩行（斷點見 `splitTwo`）；還放不下就縮字級，再不行第二行加「…」。 */
export function skillNameLines(name: string): NameLines {
  const chars = [...name];
  if (textEm(name) <= NAME_LINE_EM) return { lines: [name], tight: false, cut: false };
  const two = splitTwo(chars, NAME_LINE_EM);
  if (two !== null) return { lines: two, tight: false, cut: false };
  const tight = splitTwo(chars, NAME_TIGHT_LINE_EM);
  if (tight !== null) return { lines: tight, tight: true, cut: false };
  // 縮小後還放不下：第一行盡量放滿（附近有斷點就斷在斷點），第二行放到加上「…」剛好放得下
  let k = 0;
  let used = 0;
  while (k < chars.length && used + textEm(chars[k]!) <= NAME_TIGHT_LINE_EM) used += textEm(chars[k++]!);
  for (let j = k; j > k - 3 && j > NAME_MIN_LINE; j--) {
    if (NAME_BREAK_AFTER.has(chars[j - 1] ?? "")) {
      k = j;
      break;
    }
  }
  const out: string[] = [];
  let w = textEm(COST_MORE);
  for (const ch of chars.slice(k)) {
    if (w + textEm(ch) > NAME_TIGHT_LINE_EM) break;
    out.push(ch);
    w += textEm(ch);
  }
  return { lines: [chars.slice(0, k).join(""), `${out.join("")}${COST_MORE}`], tight: true, cut: true };
}
