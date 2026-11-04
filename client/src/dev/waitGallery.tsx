// 開發用：等待動畫一覽（RT-3；docs/art/等待動畫.md 第 6 節檢查清單）。開 `client/wait-gallery.html`（pnpm dev 後
// /wait-gallery.html）；不屬於正式 build。四個場合 × 三區（主城、雲嶺、灰燼荒原）的墨色、封蠟、點綴並排。
// 網址參數：
// - `scene=skill|judge|npc|retell`：只看一個場合（放大 2 倍）；
// - `region=capital|cloud_ridge|ashen_waste|hub|…`：只看一區；
// - `reduced=1`：減少動態（各場合的靜態版）；
// - `status=done|fail`：完成（卡面淡入、闔書）、失敗（變灰＋重試鈕）；
// - `t=1200`：固定畫某一刻（毫秒；逐格截圖用），`line=9000`：固定句子的時間；
// - `anim=0.1`：動畫放慢 10 倍（playback 的 devAnimFactor）。
// 一律靜音：這頁不初始化音效（等待聲只在正式畫面放；驗證看參數表與 waitSounds 的測試）。
import { createRoot } from "react-dom/client";
import { WAIT_CYCLE_MS, type WaitStatus } from "../render/waitArt";
import { PopupFrame } from "../ui/PopupFrame";
import { regionThemeFor } from "../ui/regionTheme";
import { WaitScene } from "../ui/WaitScene";
import { WAIT_SCENES, type WaitSceneId } from "../ui/waitNarration";
import "../styles/index.css";

const SCENE_ZH: Readonly<Record<WaitSceneId, string>> = {
  skill: "技能生成（120px，一輪 3.2 秒）",
  judge: "事件判定（80px，一輪 1.4 秒）",
  npc: "NPC 聊天（小泡泡，一輪 0.9 秒）",
  retell: "多講一點（一輪 2.6 秒）",
};
const REGIONS = ["capital", "cloud_ridge", "ashen_waste"] as const;
const REGION_ZH: Readonly<Record<string, string>> = { capital: "主城樞島", cloud_ridge: "雲嶺", ashen_waste: "灰燼荒原", hub: "hub" };

const params = new URLSearchParams(window.location.search);
const pick = <T extends string>(v: string | null, all: readonly T[]): T | null => (all as readonly string[]).includes(v ?? "") ? (v as T) : null;
const onlyScene = pick(params.get("scene"), WAIT_SCENES);
const onlyRegion = params.get("region");
const reduced = params.get("reduced") === "1";
const status: WaitStatus = params.get("status") === "done" ? "done" : params.get("status") === "fail" ? "fail" : "wait";
const num = (k: string): number | undefined => {
  const v = params.get(k);
  return v === null || !Number.isFinite(Number(v)) ? undefined : Number(v);
};
const frozenT = num("t");
const lineElapsed = num("line");
const scenes = onlyScene === null ? WAIT_SCENES : [onlyScene];
const regions = onlyRegion !== null ? [onlyRegion] : REGIONS;

function link(over: Record<string, string | null>): string {
  const p = new URLSearchParams(window.location.search);
  for (const [k, v] of Object.entries(over)) {
    if (v === null) p.delete(k);
    else p.set(k, v);
  }
  const s = p.toString();
  return s === "" ? window.location.pathname : `?${s}`;
}

function Cell({ scene, region }: { scene: WaitSceneId; region: string }) {
  const t = regionThemeFor(region);
  return (
    <PopupFrame placement={{ kind: "inline" }} className="wait-gallery-cell">
      <div className="small muted" style={{ marginBottom: 6 }}>
        {REGION_ZH[region] ?? region}・墨 <span style={{ color: t.ink, background: "#e9d6a8", padding: "0 3px" }}>■</span> 封蠟 <span style={{ color: t.seal }}>●</span> 點綴 {t.wait_fx}
      </div>
      <div style={{ zoom: onlyScene !== null ? 2 : 1 }}>
        <WaitScene
          scene={scene}
          requestId={`gallery:${scene}`}
          name="葛蘭"
          region={region}
          status={status}
          reduced={reduced}
          frozenT={frozenT}
          frozenDoneT={frozenT !== undefined && status === "done" ? 300 : undefined}
          lineElapsed={lineElapsed}
          onRetry={() => undefined}
          testId={`wait-${scene}-${region}`}
        />
      </div>
    </PopupFrame>
  );
}

function Gallery() {
  return (
    <div style={{ padding: 16, color: "var(--ui-text)", minHeight: "100vh", background: "var(--ui-navy)" }} data-testid="wait-gallery">
      <h1 style={{ fontSize: 18, margin: "0 0 8px" }}>等待動畫（RT-3，C 羽毛筆羊皮紙）</h1>
      <nav className="small" style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 12 }}>
        <a href={link({ scene: null })}>全部場合</a>
        {WAIT_SCENES.map((s) => (
          <a key={s} href={link({ scene: s })}>
            {s}
          </a>
        ))}
        <span>｜</span>
        <a href={link({ region: null })}>三區</a>
        {[...REGIONS, "hub"].map((r) => (
          <a key={r} href={link({ region: r })}>
            {REGION_ZH[r]}
          </a>
        ))}
        <span>｜</span>
        <a href={link({ reduced: reduced ? null : "1" })}>{reduced ? "關掉減少動態" : "減少動態"}</a>
        <a href={link({ status: null })}>等待中</a>
        <a href={link({ status: "done" })}>完成</a>
        <a href={link({ status: "fail" })}>失敗</a>
        <span className="muted">
          狀態：{status}・{reduced ? "減少動態" : "動態"}
          {frozenT !== undefined ? `・固定 t=${frozenT}` : ""}
        </span>
      </nav>
      {scenes.map((scene) => (
        <section key={scene} style={{ marginBottom: 14 }} data-scene-row={scene}>
          <h2 style={{ fontSize: 14, margin: "0 0 6px" }}>
            {SCENE_ZH[scene]}
            <span className="muted small">　一輪 {WAIT_CYCLE_MS[scene]} ms</span>
          </h2>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            {regions.map((r) => (
              <Cell key={r} scene={scene} region={r} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

const root = document.getElementById("root");
if (root !== null) createRoot(root).render(<Gallery />);
