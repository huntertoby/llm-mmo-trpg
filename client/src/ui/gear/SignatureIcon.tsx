// 招牌效果的類型小圖示（E6-b2；美術移植需求第 1 節第 2 項）：類型牌 18、角色面板 16、戰利品小牌 14 px。
// 畫法在 `render/qIcon/signature.ts`（四種用現有部件圖、地形規則是新畫的「地格」）；畫布內部 2 倍解析度，CSS 不縮放比例。
// 標灰的灰階與半透明由外層 CSS 做（`.off .sig-ico`）。
import { useEffect, useRef } from "react";
import { isSignatureKind, signatureGlyph } from "../../render/qIcon/signature";

const RES = 2;

export function SignatureIcon({ kind, size, label }: { kind: string | null | undefined; size: number; label?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const target = ref.current;
    const ctx = target?.getContext("2d");
    if (target == null || ctx == null || !isSignatureKind(kind)) return;
    const art = signatureGlyph(kind, size, RES);
    ctx.clearRect(0, 0, target.width, target.height);
    if (art !== null) ctx.drawImage(art, 0, 0);
  }, [kind, size]);
  const px = Math.round(size * RES);
  return (
    <canvas
      ref={ref}
      className="sig-ico"
      width={px}
      height={px}
      style={{ width: size, height: size }}
      data-kind={kind ?? undefined}
      data-size={size}
      role={label === undefined ? undefined : "img"}
      aria-label={label}
      aria-hidden={label === undefined ? true : undefined}
    />
  );
}
