// 開發用：區域主題點綴一覽（RT-1；docs/art/區域主題移植需求.md 第 1 節檢查清單「後三區的飾件在開發頁看得到」）。
// 開 `client/theme-gallery.html`（pnpm dev 後 /theme-gallery.html）；不屬於正式 build。
// 每區一欄：同一個主框（四角飾件）、地名標題牌、頭像框、強調色、共用彈窗（含危險紅帶），以及 RT-3 會讀的墨色與封蠟。
// 各欄把 `--rt-*` 變數寫在自己的外層，所以七區可以並排（正式畫面寫在 <html> 上）。
import type { CSSProperties } from "react";
import { createRoot } from "react-dom/client";
import { HudPortrait } from "../world/HudIcons";
import { PopupFrame } from "../ui/PopupFrame";
import { REGION_THEMES, regionThemeFor, themeCssVars } from "../ui/regionTheme";
import "../styles/index.css";

const NAMES: Readonly<Record<string, string>> = {
  hub: "hub（標題、建角、讀檔）",
  capital: "主城樞島",
  cloud_ridge: "雲嶺",
  ashen_waste: "灰燼荒原",
  crystal_crown: "晶冠城邦（第一季不會出現）",
  arcane_hub: "魔導樞市（第一季不會出現）",
  frost_tide: "霜潮海境（第一季不會出現）",
};

function Column({ region }: { region: string }) {
  const t = regionThemeFor(region);
  const vars = themeCssVars(t) as CSSProperties;
  return (
    <section style={{ ...vars, width: 260, display: "flex", flexDirection: "column", gap: 10 }} data-theme-col={region}>
      <h2 style={{ fontSize: 14, margin: 0 }}>{NAMES[region] ?? region}</h2>
      <div className="world-hud-place rt-plaque" style={{ width: 200, height: 28, padding: "0 10px", display: "flex", alignItems: "center", fontFamily: "'Noto Serif TC', serif", fontWeight: 700, border: "1.5px solid var(--ui-gold)", borderRadius: 6 }}>
        {NAMES[region]?.split("（")[0]}
      </div>
      <div className="hero-card rt-frame" style={{ width: 250, height: 74, display: "flex", alignItems: "center", gap: 10, padding: "0 8px" }}>
        <HudPortrait size={62} ring={t.portrait_ring} />
        <div style={{ fontSize: 12, lineHeight: 1.6 }}>
          飾件 <b>{t.corner}</b>・牌 <b>{t.plaque}</b>
          <br />
          強調 <span style={{ color: t.accent }}>■</span> {t.accent}
        </div>
      </div>
      <PopupFrame placement={{ kind: "inline" }} className="theme-gallery-card">
        <div className="section-title">事件卡</div>
        <div className="small">深藍底、金框、四角飾件、單層。</div>
        <button type="button" style={{ marginTop: 6 }}>
          滑過看強調色
        </button>
      </PopupFrame>
      <PopupFrame placement={{ kind: "inline" }} tone="danger">
        <div className="section-title">遇敵！</div>
        <div className="small">危險類只在上緣加紅帶。</div>
      </PopupFrame>
      <div className="small" style={{ display: "flex", gap: 8, alignItems: "center" }}>
        RT-3：墨 <span style={{ display: "inline-block", width: 14, height: 14, background: t.ink, border: "1px solid #888" }} />
        封蠟 <span style={{ display: "inline-block", width: 14, height: 14, borderRadius: 7, background: t.seal }} />
        點綴 {t.wait_fx}
      </div>
    </section>
  );
}

function Gallery() {
  return (
    <div style={{ padding: 16, background: "var(--ui-navy-deep)", minHeight: "100vh", color: "var(--ui-text)" }}>
      <h1 style={{ fontSize: 18, margin: "0 0 12px" }}>區域主題點綴（RT-1）：七區對照</h1>
      {REGION_THEMES.errors.length > 0 && <pre style={{ color: "#ff8a7a" }}>{REGION_THEMES.errors.join("\n")}</pre>}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 20 }}>
        {Object.keys(REGION_THEMES.themes).map((r) => (
          <Column key={r} region={r} />
        ))}
      </div>
    </div>
  );
}

const root = document.getElementById("root");
if (root !== null) createRoot(root).render(<Gallery />);
