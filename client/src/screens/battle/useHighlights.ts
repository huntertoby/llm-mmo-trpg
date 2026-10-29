// 戰鬥畫面的預覽與高亮（由 BattleScreen 抽出，Phase 3T-7）：滑過格子或面板按鈕時向伺服器要預覽，
// 再把「可走的格子、可打的目標、預覽範圍、環境預告、指揮與灌注的標示」合成給畫布的 `Highlights`；
// 也包含滑過戰鬥紀錄與環境預告時疊上去的標示，以及圖例。

import { useMemo, useState } from "react";
import type { Action, BattleResponse, BattleView, Pos, UnitView } from "../../api/types";
import type { ClassifiedActions } from "../../battle/actions";
import { flameEmphasis } from "../../battle/flameMarks";
import { legendEntries } from "../../battle/legend";
import { orderTargetTiles, type OrderKind } from "../../battle/orders";
import { runRangeTiles } from "../../battle/runAction";
import { previewOverlays } from "../../battle/scenePreview";
import {
  commandMoveTiles,
  commandTargetTiles,
  infusionTargetTiles,
  optionAt,
  type CommandSession,
  type InfuseSession,
} from "../../battle/summonControl";
import type { TelegraphMark } from "../../battle/telegraph";
import {
  actionAtTile,
  DIRECTION_ARROWS,
  hurlPickPos,
  isSelfOnly,
  targetTiles,
  vaultMarks,
  type ActionMode,
} from "../../battle/targeting";
import { onField } from "../../battle/units";
import { samePos } from "../../battle/geometry";
import type { DrawModel } from "../../battle/drawModel";
import type { SkillCard } from "../../api/types";
import type { Highlights } from "../../render/BattleRenderer";
import type { LogHover } from "../../ui/BattleLog";
import { usePreview } from "../../ui/usePreview";

type Cards = Readonly<Record<string, SkillCard | undefined>>;

const NO_HIGHLIGHTS: Highlights = {
  moves: [],
  attacks: [],
  directions: [],
  preview: [],
  telegraph: [],
  focus: null,
  hover: null,
  overlays: [],
  picked: [],
  vaults: [],
};

export interface HighlightInput {
  battleId: string;
  heroId: string;
  response: BattleResponse;
  view: BattleView;
  shown: BattleView;
  hero: UnitView | null;
  canAct: boolean;
  copying: boolean;
  canOrder: boolean;
  classified: ClassifiedActions;
  mode: ActionMode | null;
  hurlPick: string | null;
  command: CommandSession | null;
  infuse: InfuseSession | null;
  orderPick: OrderKind | null;
  panelPreview: Action | null;
  hover: Pos | null;
  marks: readonly TelegraphMark[];
  focusTile: Pos | null;
  model: DrawModel;
  cards: Cards;
}

export interface HighlightState {
  preview: ReturnType<typeof usePreview>;
  highlights: Highlights;
  legend: ReturnType<typeof legendEntries>;
  /** 可燃小火苗（3-38）：選取（瞄準中）的技能會點火，或場上已有火時才明顯。 */
  flameOn: boolean;
  setLogHover(h: LogHover | null): void;
  setTelegraphHover(tiles: readonly Pos[] | null): void;
}

export function useHighlights(i: HighlightInput): HighlightState {
  const { battleId, response, view, shown, hero, canAct, copying, canOrder, classified, mode, hurlPick } = i;
  const { command, infuse, orderPick, hover, marks, focusTile, heroId } = i;
  const [logHover, setLogHover] = useState<LogHover | null>(null);
  const [telegraphHover, setTelegraphHover] = useState<readonly Pos[] | null>(null);

  const hoverAction = useMemo<Action | null>(() => {
    if (!(canAct || copying) || hover === null || hero === null || command !== null) return null;
    if (mode !== null) return actionAtTile(mode, view, hero, hover, hurlPick);
    const target = view.units.find((u) => !u.downed && !u.escaped && !u.dismissed && samePos(u.pos, hover));
    return target === undefined ? null : (classified.attacks.get(target.id) ?? null);
  }, [canAct, copying, hover, hero, mode, view, classified, hurlPick]);
  const selfAction = mode !== null && isSelfOnly(mode.targets) ? mode.targets.self : null;
  // 複製技能暫停時也能預覽：伺服器把滑過的選取當成「被複製技能的目標」，預覽整個施放（3C-6a）。
  const preview = usePreview(
    battleId,
    response,
    canAct || copying ? (hoverAction ?? i.panelPreview ?? selfAction) : null,
  );

  const baseHighlights = useMemo<Highlights>(() => {
    const common = { telegraph: marks, focus: focusTile, hover };
    if (orderPick !== null && canOrder) {
      return { ...NO_HIGHLIGHTS, ...common, attacks: orderTargetTiles(orderPick, view, heroId) };
    }
    if (!(canAct || copying) || hero === null) return { ...NO_HIGHLIGHTS, ...common };
    if (command !== null) {
      // 指揮召喚物（3-33c）：可到達的格子（藍）、選定終點後打得到的敵人（紅）、已選的終點
      const chosen = command.dest === null ? undefined : optionAt(command.options, command.dest);
      const previewTiles = (preview?.affected_tiles ?? []).map(([x, y]): Pos => ({ x: x as number, y: y as number }));
      return {
        ...NO_HIGHLIGHTS,
        ...common,
        moves: commandMoveTiles(command.options),
        attacks: commandTargetTiles(chosen, view),
        picked: command.dest === null ? [] : [command.dest],
        preview: previewTiles,
      };
    }
    const previewTiles = (preview?.affected_tiles ?? []).map(([x, y]): Pos => ({ x: x as number, y: y as number }));
    if (infuse !== null) {
      // 灌注技能（3-33d）：滑過技能時，召喚物的位置（原點）、會選的目標（紅）與施放範圍（橘）
      const info = preview?.infusion ?? null;
      return {
        ...NO_HIGHLIGHTS,
        ...common,
        attacks: info === null ? [] : infusionTargetTiles(info, view),
        picked: info === null ? [] : [{ x: info.origin[0] as number, y: info.origin[1] as number }],
        preview: previewTiles,
      };
    }
    const overlays = previewOverlays(preview, view);
    if (mode !== null) {
      const tt = targetTiles(mode, view, hero, hurlPick);
      const pickedAt = hurlPickPos(mode, view, hurlPick);
      return {
        moves: [],
        attacks: mode.kind === "vault" ? [] : tt.targets,
        vaults: vaultMarks(mode, hero),
        directions: tt.directions.map((d) => ({ pos: d.pos, arrow: DIRECTION_ARROWS[d.direction] })),
        preview: previewTiles,
        overlays,
        picked: pickedAt === undefined ? [] : [pickedAt],
        ...common,
      };
    }
    const runTiles = runRangeTiles(preview);
    const moves =
      runTiles.length > 0
        ? runTiles // 滑過「跑步」：預覽跑完之後本回合能走到的格子
        : [...classified.moves.values()].map((m) => m.path[m.path.length - 1] as Pos);
    const attacks = [...classified.attacks.keys()].flatMap((id) => {
      const u = view.units.find((x) => x.id === id);
      return u === undefined ? [] : [u.pos];
    });
    return { moves, attacks, directions: [], preview: previewTiles, overlays, picked: [], ...common };
  }, [
    canAct,
    copying,
    canOrder,
    hero,
    heroId,
    mode,
    classified,
    view,
    preview,
    hover,
    marks,
    focusTile,
    orderPick,
    hurlPick,
    command,
    infuse,
  ]);

  // 滑過戰鬥紀錄的一組：高亮相關單位目前所在的格子與事件指出的格子（疊在預覽範圍的橘色上）。
  // 滑過環境預告的項目（9.1）：把它涉及的格子標在地圖上（同樣疊在預覽範圍的橘色上）。
  const highlights = useMemo<Highlights>(() => {
    let out = baseHighlights;
    if (telegraphHover !== null) out = { ...out, preview: [...out.preview, ...telegraphHover] };
    if (logHover === null) return out;
    const unitTiles = shown.units.filter((u) => logHover.unitIds.includes(u.id) && onField(u)).map((u) => u.pos);
    return { ...out, preview: [...out.preview, ...unitTiles, ...logHover.tiles] };
  }, [baseHighlights, logHover, telegraphHover, shown]);

  const legend = useMemo(() => legendEntries(highlights.overlays, mode), [highlights.overlays, mode]);
  const flameOn = useMemo(
    () => flameEmphasis(i.model, mode?.skillId == null ? null : i.cards[mode.skillId]),
    [i.model, mode, i.cards],
  );

  return { preview, highlights, legend, flameOn, setLogHover, setTelegraphHover };
}
