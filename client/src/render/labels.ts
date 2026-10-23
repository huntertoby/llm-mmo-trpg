// Pixi 文字與圖層的小工具（從 `BattleRenderer` 抽出，Phase 3-18b）。
import { Container, Text } from "pixi.js";

/** 畫布文字的字型清單；須與 `styles.css` 的 `body` font-family 同步。 */
export const FONT = "'Noto Sans TC', 'Microsoft JhengHei', system-ui, sans-serif";

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
