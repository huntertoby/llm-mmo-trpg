// 播放速度（慢／正常／快／略過）與播放中的「跳到結尾」按鈕。
import { PLAY_SPEEDS, type PlaySpeed } from "../battle/playback";

const LABELS: Readonly<Record<PlaySpeed, string>> = {
  slow: "慢",
  normal: "正常",
  fast: "快",
  skip: "略過",
};

const SPEED_KEY = "trpg.playSpeed";

export function loadSpeed(): PlaySpeed {
  try {
    const v = window.localStorage.getItem(SPEED_KEY);
    return PLAY_SPEEDS.find((s) => s === v) ?? "normal";
  } catch {
    return "normal";
  }
}

export function saveSpeed(value: PlaySpeed): void {
  try {
    window.localStorage.setItem(SPEED_KEY, value);
  } catch {
    // 無法存取 localStorage（私密視窗等）時只在本次有效。
  }
}

interface Props {
  speed: PlaySpeed;
  playing: boolean;
  onSpeed(value: PlaySpeed): void;
  onSkipNow(): void;
}

export function SpeedControl({ speed, playing, onSpeed, onSkipNow }: Props) {
  return (
    <div className="speed-control" aria-label="播放速度">
      <span className="muted">播放：</span>
      {PLAY_SPEEDS.map((s) => (
        <button
          key={s}
          type="button"
          className={s === speed ? "selected" : ""}
          aria-pressed={s === speed}
          onClick={() => onSpeed(s)}
        >
          {LABELS[s]}
        </button>
      ))}
      {playing && (
        <button type="button" className="primary" onClick={onSkipNow}>
          跳到結尾
        </button>
      )}
    </div>
  );
}
