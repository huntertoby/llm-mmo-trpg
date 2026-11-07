// 主角卡（UI-E2；docs/art/全遊戲一致性巡檢.md #5）：探索與戰鬥用同一張卡——左邊頭像（框色＝RT-1 區域的 portrait_ring）、
// 右邊 HP、法力、耐力三條（探索的耐力條細一點），外框是深藍底金框加區域四角飾件。資料不變：每個畫面把自己的條、徽章傳進來。
// QK-2b（docs/art/QK-2檢查.md 小修 2）：頭像改成主角自己的 Q 版頭像（`heroFace.tsx`：種族特徵、外觀選項、裝備；框色＝出身區），
// 呼叫端傳 `hero`（外觀）與 `realm`（出身區）。沒傳外觀時（舊伺服器、測試）才退回通用的 `HudPortrait`（框色＝目前區域）。
import type { ReactNode } from "react";
import { HudPortrait } from "../world/HudIcons";
import { HeroFace, heroRing, type HeroFaceInput } from "./heroFace";
import { useCurrentTheme } from "./regionTheme";

export type HeroCardWhere = "world" | "battle";

/** 兩個畫面的頭像大小（設計尺寸）。 */
export const HERO_FACE: Readonly<Record<HeroCardWhere, number>> = { world: 62, battle: 44 };

interface Props {
  where: HeroCardWhere;
  /** 名字（戰鬥寫在條的上方；探索的卡片太矮，名字放在頭像的說明卡）。 */
  name?: ReactNode;
  /** 包住頭像的外層（例如滑過說明卡）；省略＝只有頭像。 */
  face?: (portrait: ReactNode) => ReactNode;
  /** HP、法力、耐力（探索另有經驗）條。 */
  bars: ReactNode;
  /** 卡片上的其他東西（等級、階級、疲憊、補給、狀態圖示、詳細）。 */
  children?: ReactNode;
  /** 窄螢幕：只有條與圖示（戰鬥 compact）。 */
  compact?: boolean;
  className?: string;
  label?: string;
  /** 主角的外觀（QK-2b：Q 版頭像）；省略＝通用頭像。 */
  hero?: HeroFaceInput | null;
  /** 出身區（QK-2b：Q 版頭像的框色；沒有＝傭兵金）。 */
  realm?: string | null;
}

export function HeroCard({ where, name, face, bars, children, compact = false, className, label = "主角狀態", hero = null, realm = null }: Props) {
  const theme = useCurrentTheme();
  const ring = hero !== null ? heroRing(realm) : theme.portrait_ring;
  const portrait = hero !== null ? <HeroFace input={hero} realm={realm} size={HERO_FACE[where]} /> : <HudPortrait size={HERO_FACE[where]} ring={ring} />;
  const cls = ["hero-card", "rt-frame", `hero-card-${where}`, compact ? "compact" : "", className ?? ""].filter((c) => c !== "").join(" ");
  return (
    <div className={cls} data-hero-card={where} data-ring={ring} data-rt-compact={where === "battle" ? "true" : undefined} aria-label={label}>
      {!compact && <div className="hero-card-face">{face !== undefined ? face(portrait) : portrait}</div>}
      <div className="hero-card-main">
        {name != null && !compact && <div className="hero-card-name">{name}</div>}
        <div className="hero-card-bars">{bars}</div>
      </div>
      {children}
    </div>
  );
}
