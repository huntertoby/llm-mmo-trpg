// 裝備卡第一行的招牌框（E6-b2；美術移植需求第 1 節第 1、3 項，樣張 `docs/art/sample/e6Signature.js` 的 sigBox）：
// 框色＝卡片的稀有度色（1px 細框、左邊 3px 色條、由左往右淡掉的底色）；第一行是類型牌（18 px 小圖示＋「招牌・〇〇」）與招牌名，
// 第二行起是說明；標灰時灰框、沒有底色、名字加刪除線，最後一行寫原因（長版）。
// `fx`：撿到時的一次性強調（類型牌輕彈、框外光暈、斜光；動畫在 gear.css，減少動態時不播）。
import type { CSSProperties } from "react";
import { signatureColor, signatureName, signatureText, type ItemLine } from "../../gear/signature";
import { SignatureIcon } from "./SignatureIcon";

export function SignatureBox({ line, rarity, fx = false }: { line: ItemLine; rarity: string; fx?: boolean }) {
  const off = line.off_zh != null && line.off_zh !== "";
  const text = signatureText(line);
  const cls = ["gear-sig", off ? "off" : "", fx ? "fx" : "", rarity === "legendary" ? "legend" : ""].filter((c) => c !== "").join(" ");
  const style = { "--sig": signatureColor(rarity, off) } as CSSProperties;
  return (
    <div className={cls} style={style} data-testid="gear-card-signature" data-kind={line.signature ?? undefined}>
      <div className="gear-sig-head">
        <span className="gear-sig-tag" data-testid="gear-card-signature-tag">
          <SignatureIcon kind={line.signature} size={18} />
          <span>{line.signature_zh}</span>
        </span>
        <span className="gear-sig-name">{signatureName(line)}</span>
      </div>
      {text !== null && <div className="gear-sig-text">{text}</div>}
      {off && (
        <div className="gear-sig-off" data-testid="gear-card-signature-off">
          {line.off_zh}
        </div>
      )}
    </div>
  );
}
