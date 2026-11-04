// 開發用：音訊（開 `client/audio-gallery.html`，pnpm dev 後 /audio-gallery.html）。不屬於正式 build。
// - 上方：正式的「聲音」設定元件（AU-1）。
// - AU-2 音效庫：`content/audio/sfx.yaml` 的每個音效，點了就播；選一個可以即時調參數（數字欄或直接改 YAML）、看波形，
//   複製這一筆或整張參數表（貼回 sfx.yaml 的 `sfx:` 底下）。美術 PM 在這頁逐個聽、驗收。
// - 最下方：AU-1 的測試音（四軌、上限、合併、減少刺耳、ducking）。
import { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { parse, stringify } from "yaml";
import { audio, installAudio, type PlayResult, type SoundSource, type Track } from "../audio";
import { AudioSettingsPanel } from "../audio/AudioSettingsPanel";
import { registerSfxLibrary, SFX_TABLE, sfxProblems, synthSource } from "../audio/sfxLibrary";
import { HARSH_MAX_HZ, layerKind, peakOf, renderSfx, SFX_CATEGORIES, sfxDuration, sfxSeed, softenSfx, type SfxCategory, type SfxDef } from "../audio/synth";
import { installUiSounds } from "../audio/uiSounds";
import { GLOBAL_MAX, PER_ID_MAX } from "../audio/voices";
import { AmbiencePreview, BattleTimeline } from "./audioTimeline";
import "../styles/index.css";

installAudio(window, document);
registerSfxLibrary(audio);
installUiSounds(document);

const CAT_ZH: Record<SfxCategory, string> = {
  ui: "介面音",
  windup: "起手",
  swing: "出招",
  hit: "命中",
  element: "元素",
  result: "結果",
  primitive: "原語",
  status: "狀態",
  surface: "地表",
  explosion: "爆炸",
  step: "腳步",
  system: "系統",
  ambient: "環境音",
};

const KIND_ZH: Record<string, string> = { noise: "濾波雜訊", tone: "振盪器／掃頻", fm: "FM 鐘／金屬", chord: "和弦鐘", pulses: "短脈衝序列", crackle: "劈啪" };

// ---------------------------------------------------------------- 參數表文字

function flow(v: unknown): string {
  return stringify(v, { collectionStyle: "flow", flowCollectionPadding: false, lineWidth: 0 }).trim();
}

/** 一筆音效 → sfx.yaml 的寫法（和檔案一樣：欄位一行一個、每層一行 flow）。 */
export function sfxToYaml(id: string, def: SfxDef): string {
  const lines = [`  ${id}:`];
  for (const [k, v] of Object.entries(def)) {
    if (k === "layers") continue;
    lines.push(`    ${k}: ${flow(v)}`);
  }
  lines.push("    layers:");
  for (const l of def.layers) lines.push(`      - ${flow(l)}`);
  return lines.join("\n");
}

function parseEntry(text: string): { def: SfxDef | null; error: string | null } {
  try {
    const doc = parse(text) as Record<string, unknown> | null;
    const [entry] = Object.values(doc ?? {});
    const p = sfxProblems(entry);
    return p.length > 0 ? { def: null, error: p.join("；") } : { def: entry as SfxDef, error: null };
  } catch (e) {
    return { def: null, error: String(e) };
  }
}

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------- 播放

const PREVIEW = "__gallery_preview";

function playDef(id: string, def: SfxDef, variantKey: string, soft: boolean): PlayResult {
  audio.registerSound(PREVIEW, synthSource(id, soft ? softenSfx(def) : def));
  return audio.play(PREVIEW, { variantKey });
}

// ---------------------------------------------------------------- 波形

function Wave({ id, def, variantKey, soft }: { id: string; def: SfxDef; variantKey: string; soft: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const data = useMemo(() => renderSfx(soft ? softenSfx(def) : def, { sampleRate: 22050, seed: sfxSeed(id, variantKey) }), [id, def, variantKey, soft]);
  useEffect(() => {
    const c = ref.current;
    const g = c?.getContext("2d");
    if (c == null || g == null) return;
    const w = c.width;
    const h = c.height;
    g.fillStyle = "#15171b";
    g.fillRect(0, 0, w, h);
    g.strokeStyle = "#3a3f47";
    g.beginPath();
    g.moveTo(0, h / 2);
    g.lineTo(w, h / 2);
    g.stroke();
    g.fillStyle = soft ? "#7fc4a8" : "#e8bb48";
    const per = Math.max(1, Math.floor(data.length / w));
    for (let x = 0; x < w; x++) {
      let lo = 0;
      let hi = 0;
      for (let i = x * per; i < Math.min(data.length, (x + 1) * per); i++) {
        const v = data[i] ?? 0;
        lo = Math.min(lo, v);
        hi = Math.max(hi, v);
      }
      g.fillRect(x, h / 2 - hi * (h / 2), 1, Math.max(1, (hi - lo) * (h / 2)));
    }
  }, [data, soft]);
  const peak = peakOf(data);
  return (
    <div>
      <canvas ref={ref} width={560} height={90} className="ag-wave" />
      <div className="small muted">
        長度 {sfxDuration(def).toFixed(2)} 秒　峰值 {peak > 0 ? (20 * Math.log10(peak)).toFixed(1) : "−∞"} dB{soft ? `（柔和版：頻率 ≤ ${HARSH_MAX_HZ} Hz）` : ""}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- 參數編輯

type Path = (string | number)[];

function setAt(def: SfxDef, path: Path, value: number): SfxDef {
  const copy = structuredClone(def) as unknown as Record<string | number, unknown>;
  let cur: Record<string | number, unknown> = copy;
  for (let i = 0; i < path.length - 1; i++) cur = cur[path[i] as string | number] as Record<string | number, unknown>;
  cur[path[path.length - 1] as string | number] = value;
  return copy as unknown as SfxDef;
}

function NumField({ label, value, onChange }: { label: string; value: number; onChange(v: number): void }) {
  const step = Math.abs(value) >= 100 ? 10 : Math.abs(value) >= 10 ? 1 : Math.abs(value) >= 1 ? 0.1 : 0.005;
  return (
    <label className="ag-num">
      <span>{label}</span>
      <input type="number" step={step} value={value} onChange={(e) => e.target.value !== "" && onChange(Number(e.target.value))} />
    </label>
  );
}

function Fields({ def, onChange }: { def: SfxDef; onChange(d: SfxDef): void }) {
  const nums = (obj: Record<string, unknown>, base: Path) =>
    Object.entries(obj).flatMap(([k, v]) => {
      if (typeof v === "number") return [<NumField key={k} label={k} value={v} onChange={(n) => onChange(setAt(def, [...base, k], n))} />];
      if (Array.isArray(v) && v.every((x) => typeof x === "number"))
        return v.map((x, i) => <NumField key={`${k}${i}`} label={`${k}[${i}]`} value={x as number} onChange={(n) => onChange(setAt(def, [...base, k, i], n))} />);
      return [];
    });
  return (
    <div className="ag-fields">
      <div className="ag-layer">
        <b>整體</b>
        <NumField label="gain dB" value={def.gain ?? 0} onChange={(n) => onChange({ ...def, gain: n })} />
        <NumField label="vary cents" value={def.vary ?? 0} onChange={(n) => onChange({ ...def, vary: n })} />
      </div>
      {def.layers.map((l, i) => {
        const kind = layerKind(l);
        return (
          <div className="ag-layer" key={i}>
            <b>
              第 {i + 1} 層：{KIND_ZH[kind]}（{String((l as unknown as Record<string, unknown>)[kind])}）
            </b>
            {nums(l as unknown as Record<string, unknown>, ["layers", i])}
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------- 音效庫

function SfxLibrary() {
  const ids = useMemo(() => Object.keys(SFX_TABLE.defs).sort(), []);
  const [cat, setCat] = useState<SfxCategory | "all">("all");
  const [edits, setEdits] = useState<Record<string, SfxDef>>({});
  const [selected, setSelected] = useState<string>("ui_tap");
  const [variant, setVariant] = useState(0);
  const [soft, setSoft] = useState(false);
  const [text, setText] = useState<string | null>(null);
  const [note, setNote] = useState<string>("");
  const [copyBox, setCopyBox] = useState<string | null>(null);

  const defOf = (id: string): SfxDef => edits[id] ?? (SFX_TABLE.defs[id] as SfxDef);
  const def = defOf(selected);
  const variantKey = `gallery#${variant}`;
  const shown = ids.filter((id) => cat === "all" || SFX_TABLE.defs[id]?.cat === cat);
  const yamlText = text ?? sfxToYaml(selected, def);
  const parsed = text === null ? { def, error: null } : parseEntry(text);

  const update = (d: SfxDef) => {
    setEdits((e) => ({ ...e, [selected]: d }));
    setText(null);
  };
  const play = (id: string) => {
    const r = playDef(id, defOf(id), variantKey, soft);
    setNote(`${id}：${r}`);
  };
  const copy = async (t: string, what: string) => {
    const ok = await copyText(t);
    setNote(ok ? `已複製${what}` : `瀏覽器不讓複製，請從下面的文字框手動複製${what}`);
    setCopyBox(ok ? null : t);
  };
  const allYaml = () => ["sfx:", ...ids.map((id) => sfxToYaml(id, defOf(id)))].join("\n") + "\n";

  return (
    <div className="ag-lib">
      <div className="ag-cats">
        <button type="button" aria-pressed={cat === "all"} onClick={() => setCat("all")}>
          全部 {ids.length}
        </button>
        {SFX_CATEGORIES.map((c) => (
          <button type="button" key={c} aria-pressed={cat === c} onClick={() => setCat(c)}>
            {CAT_ZH[c]} {ids.filter((id) => SFX_TABLE.defs[id]?.cat === c).length}
          </button>
        ))}
      </div>
      <div className="ag-grid" data-testid="ag-sfx-grid">
        {shown.map((id) => {
          const d = defOf(id);
          return (
            <button
              type="button"
              key={id}
              data-sfx="none"
              className={`ag-sfx${id === selected ? " selected" : ""}${edits[id] !== undefined ? " edited" : ""}`}
              onClick={() => {
                setSelected(id);
                setText(null);
                play(id);
              }}
              data-testid={`ag-sfx-${id}`}
            >
              <span className="zh">{d.zh}</span>
              <span className="id">{id}</span>
              <span className="tags">
                {d.synth === "temp" ? <i className="temp">△ 暫代</i> : <i>○</i>}
                {d.harsh === true && <i className="harsh">衝擊</i>}
                {d.track === "ambient" && <i>環境軌</i>}
                {edits[id] !== undefined && <i className="temp">已改</i>}
              </span>
            </button>
          );
        })}
      </div>
      <div className="ag-editor" data-testid="ag-editor">
        <h3>
          {def.zh}　<code>{selected}</code>　<span className="small muted">{def.use ?? ""}</span>
        </h3>
        <div className="ag-buttons">
          <button type="button" data-sfx="none" onClick={() => play(selected)} data-testid="ag-play">
            ▶ 播放
          </button>
          <button type="button" data-sfx="none" onClick={() => setVariant((v) => v + 1)}>
            換變體（目前 {variantKey}）
          </button>
          <label className="layout-check">
            <input type="checkbox" data-sfx="none" checked={soft} onChange={(e) => setSoft(e.target.checked)} />
            <span>試聽減少刺耳的柔和版</span>
          </label>
          <button
            type="button"
            data-sfx="none"
            disabled={edits[selected] === undefined}
            onClick={() => {
              setEdits((e) => {
                const n = { ...e };
                delete n[selected];
                return n;
              });
              setText(null);
            }}
          >
            還原這一筆
          </button>
          <button type="button" data-sfx="none" onClick={() => void copy(sfxToYaml(selected, def), "這一筆")} data-testid="ag-copy-one">
            複製這一筆
          </button>
          <button type="button" data-sfx="none" onClick={() => void copy(allYaml(), "整張參數表")} data-testid="ag-copy-all">
            複製整張參數表（{Object.keys(edits).length} 筆已改）
          </button>
        </div>
        <Wave id={selected} def={parsed.def ?? def} variantKey={variantKey} soft={soft} />
        <Fields def={def} onChange={update} />
        <div className="small muted">也可以直接改 YAML（改完按「套用」；格式錯誤會顯示原因）：</div>
        <textarea className="ag-yaml" value={yamlText} onChange={(e) => setText(e.target.value)} rows={Math.min(14, yamlText.split("\n").length + 1)} spellCheck={false} data-testid="ag-yaml" />
        <div className="ag-buttons">
          <button type="button" data-sfx="none" disabled={text === null || parsed.def === null} onClick={() => parsed.def !== null && update(parsed.def)}>
            套用
          </button>
          {parsed.error !== null && <span className="ag-err">{parsed.error}</span>}
        </div>
        <div className="ag-log">{note}</div>
        {copyBox !== null && <textarea className="ag-yaml" readOnly value={copyBox} rows={10} onFocus={(e) => e.target.select()} />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- AU-1 測試音

/** 測試音：正弦／鋸齒波＋指數衰減。`loop` 的持續音直到按停止。 */
function testTone(track: Track, freq: number, wave: OscillatorType, dur: number): SoundSource {
  return {
    track,
    start(ctxLike, out, at) {
      const ctx = ctxLike as unknown as AudioContext;
      const osc = ctx.createOscillator();
      osc.type = wave;
      osc.frequency.value = freq;
      const env = ctx.createGain();
      env.gain.setValueAtTime(0, at);
      env.gain.linearRampToValueAtTime(0.6, at + 0.01);
      env.gain.setTargetAtTime(0, at + 0.02, dur / 4);
      osc.connect(env);
      env.connect(out as unknown as AudioNode);
      osc.start(at);
      osc.stop(at + dur);
      return dur;
    },
  };
}

const DRONE_S = 4;
audio.registerSound("dev_tone", testTone("sfx", 660, "sine", 0.5));
audio.registerSound("dev_harsh", testTone("sfx", 3200, "sawtooth", 0.4));
audio.registerSound("dev_low", testTone("sfx", 55, "square", 0.6));
audio.registerSound("dev_music", testTone("music", 220, "triangle", DRONE_S));
audio.registerSound("dev_ambient", testTone("ambient", 110, "sine", DRONE_S));

function Status() {
  const [, tick] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => tick((n) => n + 1), 200);
    return () => window.clearInterval(id);
  }, []);
  const n = audio.nodes;
  const fmt = (v: number | undefined) => (v === undefined ? "—" : v.toFixed(3));
  return (
    <pre className="ag-status" data-testid="ag-status">
      {[
        `解鎖：${audio.unlocked ? "是" : "否（先點一下或按任一鍵）"}　狀態：${n?.ctx.state ?? "—"}`,
        `主 gain ${fmt(n?.master.gain.value)}　音效 ${fmt(n?.tracks.sfx.gain.value)}　音樂 ${fmt(n?.tracks.music.gain.value)}　環境 ${fmt(n?.tracks.ambient.gain.value)}`,
        `音效軌高頻 shelf ${fmt(n?.high.gain.value)} dB　低頻 shelf ${fmt(n?.low.gain.value)} dB　限幅門檻 ${fmt(n?.limiter.threshold.value)} dB`,
        `ducking：${audio.ducked ? "壓低中" : "無"}　同時在播：${audio.activeVoices()}（dev_tone ${audio.activeVoices("dev_tone")}）`,
      ].join("\n")}
    </pre>
  );
}

function TestTones() {
  const [log, setLog] = useState<string[]>([]);
  const [duckRelease, setDuckRelease] = useState<(() => void) | null>(null);
  const note = (label: string, r: PlayResult[]) => setLog((l) => [`${label}：${r.join("、")}`, ...l].slice(0, 8));
  const burst = (id: string, n: number, sameAt: boolean) => {
    const t = audio.now() + 0.05;
    note(`${id} ×${n}${sameAt ? "（同一時間點）" : ""}`, Array.from({ length: n }, (_, i) => audio.play(id, { at: sameAt ? t : t + i * 0.03 })));
  };
  return (
    <>
      <div className="ag-buttons">
        <button type="button" data-sfx="none" onClick={() => note("dev_tone", [audio.play("dev_tone")])} data-testid="ag-tone">
          音效：單音 660 Hz
        </button>
        <button type="button" data-sfx="none" onClick={() => burst("dev_tone", 6, false)} data-testid="ag-limit">
          同一音效連放 6 次（上限 {PER_ID_MAX}）
        </button>
        <button type="button" data-sfx="none" onClick={() => burst("dev_tone", 5, true)} data-testid="ag-merge">
          同一時間點 5 次（合併成 1 聲、略大聲）
        </button>
        <button type="button" data-sfx="none" onClick={() => note("全部", ["dev_tone", "dev_harsh", "dev_low", "dev_music", "dev_ambient"].flatMap((id) => Array.from({ length: 5 }, (_, i) => audio.play(id, { at: audio.now() + i * 0.02 }))))}>
          全部各 5 次（總上限 {GLOBAL_MAX}）
        </button>
        <button type="button" data-sfx="none" onClick={() => note("dev_harsh", [audio.play("dev_harsh")])} data-testid="ag-harsh">
          刺耳：3200 Hz 鋸齒波
        </button>
        <button type="button" data-sfx="none" onClick={() => note("dev_low", [audio.play("dev_low")])}>
          低頻轟鳴：55 Hz 方波
        </button>
        <button type="button" data-sfx="none" onClick={() => note("dev_music", [audio.play("dev_music")])} data-testid="ag-music">
          音樂軌：220 Hz {DRONE_S} 秒
        </button>
        <button type="button" data-sfx="none" onClick={() => note("dev_ambient", [audio.play("dev_ambient")])}>
          環境軌：110 Hz {DRONE_S} 秒
        </button>
        <button type="button" data-sfx="none" onClick={() => note("不存在的 id", [audio.play("no_such_sound")])}>
          不存在的 id（不出聲）
        </button>
        <button
          type="button"
          data-sfx="none"
          aria-pressed={duckRelease !== null}
          onClick={() => {
            if (duckRelease !== null) {
              duckRelease();
              setDuckRelease(null);
            } else setDuckRelease(() => audio.duck());
          }}
          data-testid="ag-duck"
        >
          {duckRelease !== null ? "停止 ducking" : "模擬說書人字幕（ducking）"}
        </button>
      </div>
      <Status />
      <div className="ag-log" data-testid="ag-log">
        {log.map((l, i) => (
          <div key={`${i}-${l}`}>{l}</div>
        ))}
      </div>
    </>
  );
}

function Gallery() {
  return (
    <div className="ag">
      <h2>聲音設定（正式元件）</h2>
      <div className="ag-panel">
        <AudioSettingsPanel />
      </div>
      <h2>AU-2 音效庫（content/audio/sfx.yaml，全部程式合成）</h2>
      {SFX_TABLE.errors.length > 0 && <div className="ag-err">參數表有 {SFX_TABLE.errors.length} 筆被略過：{SFX_TABLE.errors.join("／")}</div>}
      <SfxLibrary />
      <h2>AU-3 戰鬥時間軸試聽（選一招，聽整段起手 → 出招 → 命中 → 結果）</h2>
      <BattleTimeline />
      <h2>AU-3 環境音試聽</h2>
      <AmbiencePreview />
      <h2>AU-1 測試音</h2>
      <TestTones />
    </div>
  );
}

const root = document.getElementById("root");
if (root !== null) createRoot(root).render(<Gallery />);
