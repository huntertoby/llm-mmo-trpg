// CR-1c（美術 CR-1b 驗收小修 1）：「名稱＋數字」是一個單位（例「暴擊傷害 260%」「暴擊範圍 +1」「詞條 +10%」
// 「傷害 52–146」），換行時整個單位一起移到下一行。用「・」「、」和全形空白切開的每一段包成 inline-block
// （不是 nowrap：一段比一行還長時，段內照常斷行）。分隔符留在前一段的尾巴，下一行不會從「・」開頭。
// 套用：攻擊預覽面板、單位卡與主角面板的暴擊來源文字。

const SEPARATOR = /(?<=[・、　])/u;

/** 切成單位：每段帶著自己後面的分隔符；接起來等於原字串。 */
export function wrapUnitParts(text: string): string[] {
  return text.split(SEPARATOR).filter((p) => p !== "");
}

export function WrapUnits({ text }: { text: string }) {
  const parts = wrapUnitParts(text);
  if (parts.length <= 1) return <span className="wrap-unit">{text}</span>;
  return (
    <>
      {parts.map((p, i) => (
        <span key={`${i}:${p}`} className="wrap-unit">
          {p}
        </span>
      ))}
    </>
  );
}
