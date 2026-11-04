// 6F-7（美術 PM 驗收 6F-6 必修 1）：技能鈕第二行（代價）放不下時的縮寫與取捨（純函式）。
// 6F-6 讓代價最多兩行（長名字時一行），超出的部分被 CSS 的高度上限裁掉：
// 「灰燼與霜雪交織的鎖鏈陷阱」只剩「AP 2・法力 5・」，冷卻整段不見，結尾還掛著「・」。
// 這裡先估寬度，放不下時：
//   1. 每段換成縮寫（「AP 2」→「AP2」、「法力 5」→「法5」、「冷卻 2 回合」→「冷2」……）；
//   2. 還放不下，從後面拿掉不是 AP、冷卻的段，最後一段加「…」。
// 「・」只放在段與段之間（接在前一段後面），所以整行永遠不會以「・」結尾；AP 與冷卻一定留著。
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
  [/^冷卻 (\d+)( 回合)?$/, "冷$1"],
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

/** 照畫面的換行方式（每段不拆、「・」接在前一段後面、段與段之間換行）排的行數。`sep` 傳空字串時量已經接好「・」的 `costPieces`。 */
export function costLines(parts: readonly string[], lineEm = COST_LINE_EM, sep = COST_SEP): number {
  let lines = parts.length > 0 ? 1 : 0;
  let used = 0;
  parts.forEach((p, i) => {
    const w = textEm(p) + (i < parts.length - 1 ? textEm(sep) : 0);
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

/** 代價放進 `maxLines` 行：原樣 → 縮寫 → 拿掉不是 AP、冷卻的段（從後面拿）並加「…」。 */
export function fitCost(parts: readonly string[], maxLines: number, lineEm = COST_LINE_EM): FittedCost {
  if (costLines(parts, lineEm) <= maxLines) return { parts: [...parts], more: false };
  const short = parts.map(abbrevCost);
  if (costLines(short, lineEm) <= maxLines) return { parts: short, more: false };
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

/** 畫面上每段的字（「・」接在前一段後面；有拿掉的段時最後一段加「…」）。 */
export function costPieces(fit: FittedCost): string[] {
  return fit.parts.map((p, i) => (i < fit.parts.length - 1 ? `${p}${COST_SEP}` : fit.more ? `${p}${COST_MORE}` : p));
}
