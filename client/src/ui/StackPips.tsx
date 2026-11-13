// KW-3：HUD 層數計量（連擊、怒氣、專注、氣的格子式計量；取代這四種層數的 `StackBadge`）。
// 畫法在 `render/qIcon/stackGauge.ts`（美術 docs/art/KW樣張.md 第 4 節 A 案：膠囊＋14px 關鍵字圓章＋N 格，滿層亮起）。
// 畫布四邊各多 4px 給滿層的外暈，CSS 用負邊距收回（`.stack-pips canvas`），版面佔的就是膠囊本身（高 22、寬＝含膠囊外寬）。
// 右下角不寫數字（靠格子數）；滑過的說明照舊（`StackTip`）。
import { useEffect, useRef } from "react";
import type { SkillCard } from "../api/types";
import { stackName } from "../battle/glossary";
import { ICON_RES } from "../render/qIcon/core";
import { GAUGE_MAX, gaugeBox, gaugeCanvas } from "../render/qIcon/stackGauge";
import { StackTip } from "./StackTip";

/** 計量畫布（顯示寬高＝`gaugeBox`，畫布＝×`ICON_RES`）。 */
function GaugeCanvas({ id, count }: { id: string; count: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (canvas == null || ctx == null) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const src = gaugeCanvas(id, count, ICON_RES);
    if (src !== null) ctx.drawImage(src, 0, 0);
  }, [id, count]);
  const { w, h } = gaugeBox(id);
  return <canvas ref={ref} width={Math.round(w * ICON_RES)} height={Math.round(h * ICON_RES)} style={{ width: w, height: h }} aria-hidden="true" />;
}

/** 一種層數的計量；滑過看層數說明（`StackTip`，同 `StackBadge`）。 */
export function StackPips({ id, count, cards, owned }: { id: string; count: number; cards?: Readonly<Record<string, SkillCard | undefined>>; owned: readonly string[] | null }) {
  const max = GAUGE_MAX[id] ?? 0;
  return (
    <StackTip id={id} cards={cards} owned={owned}>
      <span className={`stack-pips${count >= max ? " full" : ""}`} data-stack={id} data-count={count} role="img" aria-label={`${stackName(id)} ${count}／${max}`}>
        <GaugeCanvas id={id} count={count} />
      </span>
    </StackTip>
  );
}
