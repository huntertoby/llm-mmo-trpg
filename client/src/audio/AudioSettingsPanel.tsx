// 設定面板的「聲音」區（AU-1）：主、音效、音樂、環境四條滑桿＋各自靜音；全部靜音（Shift＋M）、減少刺耳音效、背景分頁靜音。
// 放在戰鬥「版面」面板裡（目前唯一的設定面板）；設定由 `audio` 引擎存 localStorage。
import { audio, type AudioEngine } from "./index";
import type { AudioSettings } from "./settings";
import type { Track } from "./types";
import { useAudioSettings } from "./useAudio";
import "./audio.css";

type VolumeKey = "master" | Track;

const ROWS: readonly { key: VolumeKey; label: string }[] = [
  { key: "master", label: "主音量" },
  { key: "sfx", label: "音效" },
  { key: "music", label: "音樂" },
  { key: "ambient", label: "環境" },
];

function rowMuted(s: AudioSettings, key: VolumeKey): boolean {
  return key === "master" ? s.muted : s.trackMuted[key];
}

export function AudioSettingsPanel({ engine = audio }: { engine?: AudioEngine }) {
  const s = useAudioSettings(engine);
  const toggleRow = (key: VolumeKey): void => {
    if (key === "master") engine.toggleMute();
    else engine.setSettings({ trackMuted: { ...s.trackMuted, [key]: !s.trackMuted[key] } });
  };
  return (
    <div className="audio-settings" aria-label="聲音設定" data-testid="audio-settings">
      <div className="section-title">聲音</div>
      {ROWS.map((r) => {
        const muted = rowMuted(s, r.key);
        return (
          <div className={`audio-row${muted ? " muted" : ""}`} key={r.key} data-testid={`audio-row-${r.key}`}>
            <span>{r.label}</span>
            <input type="range" min={0} max={100} step={5} value={s[r.key]} aria-label={`${r.label}音量`} onChange={(e) => engine.setSettings({ [r.key]: Number(e.target.value) })} data-testid={`audio-vol-${r.key}`} />
            <span className="layout-value">{s[r.key]}</span>
            <button type="button" className="audio-mute" aria-pressed={muted} aria-label={r.key === "master" ? "全部靜音（Shift＋M）" : `${r.label}靜音`} onClick={() => toggleRow(r.key)} data-testid={`audio-mute-${r.key}`}>
              {muted ? "靜音中" : "靜音"}
            </button>
          </div>
        );
      })}
      <label className="layout-check">
        <input type="checkbox" checked={s.reduceHarsh} onChange={(e) => engine.setSettings({ reduceHarsh: e.target.checked })} data-testid="audio-reduce-harsh" />
        <span>減少刺耳音效（拿掉尖音與轟鳴、最大音量降低）</span>
      </label>
      <label className="layout-check">
        <input type="checkbox" checked={s.muteInBackground} onChange={(e) => engine.setSettings({ muteInBackground: e.target.checked })} data-testid="audio-mute-background" />
        <span>切到其他分頁時靜音</span>
      </label>
      <div className="small muted">Shift＋M：全部靜音／取消。第一次點擊或按鍵後才會出聲。</div>
    </div>
  );
}
