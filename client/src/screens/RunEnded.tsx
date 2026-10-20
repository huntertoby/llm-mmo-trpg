// 一輪結束摘要：勝敗、每場的地圖與結果、輪數；開新一輪。
import type { RunResponse } from "../api/types";
import { battleName, recordText } from "../run/flow";
import { RunHeroPanel } from "../run/RunHeroPanel";

interface Props {
  run: RunResponse;
  victory: boolean;
  onNewRun(): void;
  onHome(): void;
}

export function RunEnded({ run, victory, onNewRun, onHome }: Props) {
  const totalRounds = run.history.reduce((n, h) => n + h.rounds, 0);
  return (
    <div className="run-ended">
      <div className={`panel run-result ${victory ? "victory" : "defeat"}`}>
        <h2>{victory ? "一輪通關！" : "一輪失敗"}</h2>
        <div className="muted">
          打完 {run.battles_done} / {run.plan.length} 場・共 {totalRounds} 輪・種子 {run.seed}
        </div>
      </div>
      <div className="panel">
        <div className="section-title">各場結果</div>
        <table className="run-history">
          <thead>
            <tr>
              <th>場次</th>
              <th>地圖</th>
              <th>結果</th>
            </tr>
          </thead>
          <tbody>
            {run.plan.map((p) => {
              const rec = run.history.find((h) => h.index === p.index);
              return (
                <tr key={p.index}>
                  <td>{battleName(p.index, p.boss)}</td>
                  <td>{p.map_name_zh}</td>
                  <td>{rec === undefined ? <span className="muted">未進行</span> : recordText(rec)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <RunHeroPanel hero={run.hero} />
      <div className="run-actions">
        <button type="button" className="primary" onClick={onNewRun}>
          開新一輪
        </button>
        <button type="button" onClick={onHome}>
          回首頁
        </button>
      </div>
    </div>
  );
}
