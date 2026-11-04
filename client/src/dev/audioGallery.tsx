// 開發用：AU-1 音訊核心（開 `client/audio-gallery.html`，pnpm dev 後 /audio-gallery.html）。
// 不屬於正式 build。只有 OscillatorNode 測試音（合成積木是 AU-2 的事），用來驗四軌、靜音、同時播放上限、同一時間點合併、
// 減少刺耳音效、ducking 與背景分頁靜音。上方的設定區就是正式的「聲音」設定元件。
import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { audio, installAudio, type PlayResult, type SoundSource, type Track } from "../audio";
import { AudioSettingsPanel } from "../audio/AudioSettingsPanel";
import { GLOBAL_MAX, PER_ID_MAX } from "../audio/voices";
import "../styles/index.css";

installAudio(window, document);

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
        `高頻 shelf ${fmt(n?.high.gain.value)} dB　低頻 shelf ${fmt(n?.low.gain.value)} dB　限幅門檻 ${fmt(n?.limiter.threshold.value)} dB`,
        `ducking：${audio.ducked ? "壓低中" : "無"}　同時在播：${audio.activeVoices()}（dev_tone ${audio.activeVoices("dev_tone")}）`,
      ].join("\n")}
    </pre>
  );
}

function Gallery() {
  const [log, setLog] = useState<string[]>([]);
  const [duckRelease, setDuckRelease] = useState<(() => void) | null>(null);
  const note = (label: string, r: PlayResult[]) => setLog((l) => [`${label}：${r.join("、")}`, ...l].slice(0, 8));
  const burst = (id: string, n: number, sameAt: boolean) => {
    const t = audio.now() + 0.05;
    note(`${id} ×${n}${sameAt ? "（同一時間點）" : ""}`, Array.from({ length: n }, (_, i) => audio.play(id, { at: sameAt ? t : t + i * 0.03 })));
  };
  return (
    <div className="ag">
      <h2>AU-1 音訊核心</h2>
      <div className="ag-panel">
        <AudioSettingsPanel />
      </div>
      <h2>測試音</h2>
      <div className="ag-buttons">
        <button type="button" onClick={() => note("dev_tone", [audio.play("dev_tone")])} data-testid="ag-tone">
          音效：單音 660 Hz
        </button>
        <button type="button" onClick={() => burst("dev_tone", 6, false)} data-testid="ag-limit">
          同一音效連放 6 次（上限 {PER_ID_MAX}）
        </button>
        <button type="button" onClick={() => burst("dev_tone", 5, true)} data-testid="ag-merge">
          同一時間點 5 次（合併成 1 聲、略大聲）
        </button>
        <button type="button" onClick={() => note("全部", ["dev_tone", "dev_harsh", "dev_low", "dev_music", "dev_ambient"].flatMap((id) => Array.from({ length: 5 }, (_, i) => audio.play(id, { at: audio.now() + i * 0.02 }))))}>
          全部各 5 次（總上限 {GLOBAL_MAX}）
        </button>
        <button type="button" onClick={() => note("dev_harsh", [audio.play("dev_harsh")])} data-testid="ag-harsh">
          刺耳：3200 Hz 鋸齒波
        </button>
        <button type="button" onClick={() => note("dev_low", [audio.play("dev_low")])}>
          低頻轟鳴：55 Hz 方波
        </button>
        <button type="button" onClick={() => note("dev_music", [audio.play("dev_music")])} data-testid="ag-music">
          音樂軌：220 Hz {DRONE_S} 秒
        </button>
        <button type="button" onClick={() => note("dev_ambient", [audio.play("dev_ambient")])}>
          環境軌：110 Hz {DRONE_S} 秒
        </button>
        <button type="button" onClick={() => note("不存在的 id", [audio.play("no_such_sound")])}>
          不存在的 id（不出聲）
        </button>
        <button
          type="button"
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
    </div>
  );
}

const root = document.getElementById("root");
if (root !== null) createRoot(root).render(<Gallery />);
