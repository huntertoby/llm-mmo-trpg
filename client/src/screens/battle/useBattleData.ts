// 戰鬥畫面的派生資料（由 BattleScreen 抽出，Phase 3T-7）：從伺服器回應算出主角、技能卡、可選的動作與模式、
// 複製／複合技能第二段的暫停狀態、環境預告標記、畫面繪製模型。全部是 `useMemo` 的純派生，沒有自己的狀態。

import { useMemo } from "react";
import type { BattleResponse, BattleView, Pos, SkillCard, UnitView } from "../../api/types";
import { actionLabel, classifyActions, type ClassifiedActions, type LabeledAction } from "../../battle/actions";
import { buildDrawModel, type DrawModel } from "../../battle/drawModel";
import { fxSkillsOf } from "../../battle/fxSkills";
import { followupMode, isFollowupPending } from "../../battle/followup";
import { withPushReasons } from "../../battle/pushReasons";
import { raceModes } from "../../battle/race";
import { withReasons } from "../../battle/skillReasons";
import { telegraphMarks, type TelegraphMark } from "../../battle/telegraph";
import {
  basicModes,
  copyMode,
  fallbackActions,
  isCopyPending,
  skillButtons,
  skillMode,
  type ActionMode,
  type SkillButton,
} from "../../battle/targeting";
import { unitNames, type UnitNames } from "../../battle/units";
import { useHeroCards } from "../../ui/useHeroCards";
import { useSkillCards, useSkillNames } from "../../ui/useSkillCards";
import { useSkillReasons } from "../../ui/useSkillReasons";

type Cards = Readonly<Record<string, SkillCard | undefined>>;

export interface BattleData {
  view: BattleView;
  hero: UnitView | null;
  cards: Cards;
  skillNames: Readonly<Record<string, string>>;
  /** 播放中畫面上的單位名稱（`shown`）與目前實際狀態的單位名稱（`view`）。 */
  names: UnitNames;
  liveNames: UnitNames;
  canAct: boolean;
  /** 隊友指令（可以下指令的時機）。 */
  canOrder: boolean;
  classified: ClassifiedActions;
  buttons: SkillButton[];
  /** 基本動作模式、種族技模式（`raceModeList`）與所有可選模式（鍵 → 模式）。 */
  basic: ActionMode[];
  raceModeList: ActionMode[];
  modes: Map<string, ActionMode>;
  /** 複製技能或複合技能第二段暫停中（選目標）。 */
  copyPaused: boolean;
  followPaused: boolean;
  copying: boolean;
  copyName: string;
  copyPick: ActionMode | null;
  fallback: LabeledAction[];
  model: DrawModel;
  marks: TelegraphMark[];
  /** 詢問視窗的觸發單位所在格（鏡頭焦點）。 */
  focusTile: Pos | null;
}

export function useBattleData(
  battleId: string,
  heroId: string,
  response: BattleResponse,
  shown: BattleView,
  acting: string | undefined,
  busy: boolean,
): BattleData {
  const view = response.view;
  const hero = useMemo(() => view.units.find((u) => u.id === heroId) ?? null, [view, heroId]);
  const skillIds = useMemo(() => {
    const ids = new Set<string>(hero?.skills ?? []);
    for (const g of hero?.granted_skills ?? []) ids.add(g.skill_id); // 暫時獲得的技能（Phase 3D-8c）
    for (const a of response.legal_actions) if (a.type === "use_skill") ids.add(a.skill_id);
    for (const id of Object.keys(hero?.cooldowns ?? {})) ids.add(id);
    const copied = response.pending?.copy_skill_id; // 複製技能暫停時，被複製的技能（要顯示名稱）
    if (copied != null) ids.add(copied);
    for (const u of view.units) for (const id of u.skills) ids.add(id); // 技能特效要所有單位的技能形狀（Phase 3-12）
    for (const t of shown.traps) ids.add(t.skill_id); // 陷阱的觸發方式與元素色（Phase 3-36b）
    for (const z of shown.zones ?? []) ids.add(z.skill_id); // 區域的元素色
    return [...ids].sort();
  }, [hero, response.legal_actions, response.pending, view, shown]);
  const baseCards = useSkillCards(skillIds, battleId);
  const cards = useHeroCards(battleId, response, baseCards); // 主角的技能卡換成實際值版本（3-41c）
  const skillNames = useSkillNames(cards);
  const names = useMemo(() => unitNames(shown), [shown]);
  const liveNames = useMemo(() => unitNames(view), [view]);
  const canAct = response.awaiting === "action" && !busy;
  const classified = useMemo(
    () => classifyActions(response.legal_actions, view, skillNames),
    [response, view, skillNames],
  );
  const skillReasons = useSkillReasons(battleId, response);
  const buttons = useMemo(
    () => (hero === null ? [] : withReasons(skillButtons(hero, response.legal_actions, cards, response.variant_states ?? []), skillReasons)),
    [hero, response.legal_actions, response.variant_states, cards, skillReasons],
  );
  const basic = useMemo(
    () => withPushReasons(basicModes(response.legal_actions, hero?.charges ?? []), response.interact_options, view),
    [response.legal_actions, response.interact_options, view, hero?.charges],
  );
  const raceModeList = useMemo(() => raceModes(hero, response.legal_actions), [hero, response.legal_actions]);
  const modes = useMemo(() => {
    const map = new Map<string, ActionMode>();
    for (const m of basic) if (m.blockedReason === undefined) map.set(m.key, m);
    for (const m of raceModeList) if (m.blockedReason === undefined) map.set(m.key, m); // 種族技（3R-2）
    for (const b of buttons) if (b.disabledReason === null) map.set(`skill:${b.skillId}`, skillMode(b));
    return map;
  }, [basic, buttons, raceModeList]);
  // 複製技能（copy_skill）暫停：第二段選取，伺服器給的 copy_options 當成一個模式（點目標即送出）。
  // 複合技能第二段（「動作 → 位移」「擊殺 → 接下一段」，Phase 3F-4b）的暫停也走同一套：伺服器給的
  // followup_options 當成模式，滑過預覽、點目標送出；`copying` 代表「暫停中為第二段選目標」。
  const copyPaused = response.awaiting === "decision" && isCopyPending(response.pending) && !busy;
  const followPaused = response.awaiting === "decision" && isFollowupPending(response.pending) && !busy;
  const copying = copyPaused || followPaused;
  const pausedSkill = followPaused ? response.pending?.skill_id : response.pending?.copy_skill_id;
  const copyName = pausedSkill == null ? "" : (skillNames[pausedSkill] ?? pausedSkill);
  const copyPick = useMemo(() => {
    if (!copying || response.pending === null) return null;
    if (followPaused) return followupMode(response.pending, response.followup_options ?? [], copyName);
    return copyMode(response.pending, response.copy_options, copyName);
  }, [copying, followPaused, response.pending, response.copy_options, response.followup_options, copyName]);
  const fallback = useMemo<LabeledAction[]>(
    () =>
      hero === null
        ? []
        : fallbackActions(response.legal_actions, hero).map((action) => ({
            action,
            label: actionLabel(action, view, skillNames, liveNames),
          })),
    [hero, response.legal_actions, view, skillNames, liveNames],
  );
  const model = useMemo(() => buildDrawModel(shown, heroId, acting, fxSkillsOf(cards)), [shown, heroId, acting, cards]);
  const marks = useMemo(
    () => (busy || view.ended ? [] : telegraphMarks(response.telegraph, view)),
    [busy, view, response.telegraph],
  );
  const focusTile = useMemo<Pos | null>(() => {
    const trigger = response.pending?.trigger_unit_id;
    if (response.awaiting !== "decision" || trigger == null) return null;
    return view.units.find((u) => u.id === trigger)?.pos ?? null;
  }, [response, view]);
  const canOrder = !busy && response.awaiting !== "ended" && response.awaiting !== "stalled";

  return {
    view,
    hero,
    cards,
    skillNames,
    names,
    liveNames,
    canAct,
    canOrder,
    classified,
    buttons,
    basic,
    raceModeList,
    modes,
    copyPaused,
    followPaused,
    copying,
    copyName,
    copyPick,
    fallback,
    model,
    marks,
    focusTile,
  };
}
