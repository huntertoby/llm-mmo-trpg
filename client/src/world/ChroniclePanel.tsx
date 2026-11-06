// 編年史（Phase 5F-5）：每季的季末紀錄（上季角色打過的精英、完成的事件）、首位發現的配方、循環賽最終排名、
// 首殺與賽季 Boss 評分榜。所有人可看；角色名與配方名是玩家文字，只當資料顯示。
import { Fragment, useEffect, useState } from "react";
import { api } from "../api/client";
import type { ChronicleSeasonView, ChronicleView } from "../api/types";
import { AccountTitles } from "../ui/AccountTitles";
import { seasonHasRecords, seasonTitle } from "./season";

function SeasonBlock({ season }: { season: ChronicleSeasonView }) {
  return (
    <div className="chronicle-season" data-testid="chronicle-season">
      <div className="section-title">{seasonTitle(season)}</div>
      {season.heroes.length > 0 && (
        <ul className="small">
          {season.heroes.map((h, i) => (
            <li key={`h${i}`}>
              <b>{h.name}</b>
              <AccountTitles titles={h.titles} />　{h.text_zh}
            </li>
          ))}
        </ul>
      )}
      {season.first_kills.length > 0 && (
        <div className="small" data-testid="chronicle-first-kills">
          首殺：
          {season.first_kills.map((k, i) => (
            <Fragment key={`k${i}`}>
              {i > 0 && "、"}
              {`${k.target_name_zh}（${k.name}`}
              <AccountTitles titles={k.titles} />）
            </Fragment>
          ))}
        </div>
      )}
      {season.boss_board.length > 0 && (
        <div className="small" data-testid="chronicle-boss-board">
          賽季頭目評分榜：
          {season.boss_board.map((b, i) => (
            <Fragment key={`b${i}`}>
              {i > 0 && "　"}
              {`${i + 1}. ${b.name} ${b.score} 分`}
              {/* 帳號有稱號就顯示帳號稱號（5F-3c）；舊資料沒有時退回這次通關的稱號 */}
              {(b.titles ?? []).length > 0 ? <AccountTitles titles={b.titles} /> : b.title_zh ? `「${b.title_zh}」` : ""}
            </Fragment>
          ))}
        </div>
      )}
      {season.league.length > 0 && (
        <div className="small">
          影子循環賽：
          {season.league.slice(0, 5).map((r, i) => (
            <Fragment key={`r${i}`}>
              {i > 0 && "　"}
              {`${r.rank}. ${r.name}`}
              <AccountTitles titles={r.titles} />
              {`（${r.build_zh}）${r.wins} 勝 ${r.losses} 敗 ${r.draws} 和`}
            </Fragment>
          ))}
        </div>
      )}
      {season.recipes.length > 0 && (
        <div className="small muted">
          首位發現的配方：{season.recipes.map((r) => `${r.name_zh}（${r.discoverer_name}）`).join("、")}
        </div>
      )}
    </div>
  );
}

export function ChroniclePanel({ refresh = 0 }: { refresh?: number }) {
  const [view, setView] = useState<ChronicleView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.worldChronicle().then(
      (v) => !cancelled && setView(v),
      (e: unknown) => !cancelled && setError(e instanceof Error ? e.message : String(e)),
    );
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const seasons = view?.seasons.filter(seasonHasRecords) ?? [];
  return (
    <div className="panel" data-testid="chronicle">
      <div className="section-title">編年史</div>
      {error !== null && <div className="error-text small">{error}</div>}
      {view === null && error === null && <div className="muted small">載入中……</div>}
      {view !== null && seasons.length === 0 && <div className="muted small">還沒有紀錄。</div>}
      {seasons.map((s) => (
        <SeasonBlock key={s.season_id} season={s} />
      ))}
    </div>
  );
}
