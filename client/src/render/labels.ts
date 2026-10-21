// Pixi 文字與圖層的小工具（從 `BattleRenderer` 抽出，Phase 3-18b）。
import { Container, Text } from "pixi.js";

export const FONT = "system-ui, 'Microsoft JhengHei', 'PingFang TC', sans-serif";

/** 清空圖層並銷毀子節點。 */
export function clearLayer(layer: Container): void {
  for (const child of layer.removeChildren()) child.destroy({ children: true });
}

export function label(text: string, size: number, fill: number, bold = false): Text {
  return new Text({
    text,
    style: { fontFamily: FONT, fontSize: size, fill, fontWeight: bold ? "700" : "400" },
  });
}
