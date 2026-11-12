// 大世界的「成長與技能」畫面（Phase 5A-7；docs/phases/Phase5計畫.md 13.3）：重用一輪的配點、閃現、
// 重閃、溶掉、傳承元件（送出的選擇轉成世界動作），加上誓約區。地點限制（城鎮與營火）由後端
// `growth` 下發，不在可花點的地方時按鈕停用並顯示原因。
import { useState } from "react";
import { api } from "../api/client";
import type { RunChoice, WorldAction, WorldView } from "../api/types";
import { AttributeRespecSection } from "../run/AttributeRespecSection";
import { CampfireSkillCare } from "../run/CampfireSkillCare";
import { FlashSection } from "../run/FlashSection";
import { FlashPendingPanel } from "../screens/RunFlashPending";
import { Hint } from "../ui/Hint";
import { LimitNote, limitOf } from "./limits";
import { LookChangeLine } from "./LookChange";
import { RaceChangeLine } from "./RaceChange";
import { choiceLabel, defaultParams, oathButton, paramLabel, spendLock, swearAction } from "./growth";

interface Props {
  view: WorldView;
  busy: boolean;
  /** 送出一輪元件的選擇（轉成世界動作）；回傳失敗時的 HTTP 狀態（成功為 `null`）。 */
  onChoose(choice: RunChoice): Promise<number | null>;
  onAct(action: WorldAction): Promise<number | null>;
  onClose(): void;
}

const PLACE = "只在城鎮與營火";

export function WorldFlashPending({ view, busy, onChoose }: Pick<Props, "view" | "busy" | "onChoose">) {
  const pending = view.pending_flash;
  if (pending == null) return null;
  return (
    <div className="world-growth" data-testid="world-flash-pending">
      <div className="world-growth-lock small" role="status">
        先選完閃現的變化：選之前不能移動、開戰或使用其他服務。
      </div>
      <FlashPendingPanel key={`${pending.skill_id}:${pending.nth}:${pending.slot}`} pending={pending} hero={view.hero} busy={busy} onChoose={onChoose} />
    </div>
  );
}

export function WorldGrowth({ view, busy, onChoose, onAct, onClose }: Props) {
  const cid = view.character.character_id;
  const lock = spendLock(view);
  const previewFlash = (skill: string, slot: number | null) => api.worldFlashPreview(cid, skill, slot);
  const previewAllocation = (attrs: Record<string, number>) => api.worldAllocationPreview(cid, attrs);
  // OB-5b：下面列了入門期的限制時，不寫「可以使用」（前後矛盾）
  const limited = (["flash", "dissolve", "oath"] as const).some((k) => limitOf(view, k) !== null);
  return (
    <div className="world-growth" data-testid="world-growth">
      <div className="panel world-growth-head">
        <div className="section-title">
          成長與技能
          <span className="muted small lead-gap">
            Lv {view.character.level}・角色階級 {view.growth.skill_tier}・靈感點 {view.growth.insight}・未分配屬性點 {view.character.attribute_points}
          </span>
        </div>
        <div className={`small ${view.growth.at_service ? "muted" : "world-growth-lock"}`} data-testid="world-service-note">
          {view.growth.service_zh}。{view.growth.starter_note_zh ?? ""}{view.growth.at_service ? (limited ? "" : "你現在在這裡，可以使用。") : `現在不行：${view.growth.blocked_zh ?? ""}。`}
        </div>
        {lock !== null && view.growth.at_service && <div className="world-growth-lock small">現在不能花點：{lock}</div>}
        {/* OB-5（#150 第 6、9 點）：開局還沒結束時不開放的成長功能（閃現、溶掉與傳承、誓約），先寫明原因 */}
        <LimitNote reason={limitOf(view, "flash")} />
        <LimitNote reason={limitOf(view, "dissolve")} />
        <LimitNote reason={limitOf(view, "oath")} />
        <div className="run-actions">
          <button type="button" onClick={onClose} data-testid="world-growth-close">
            回到地點圖
          </button>
        </div>
      </div>
      {/* 6R-2（#137）：外觀在主城隨時免費改；HUD 版面也找得到（6R-1 的本季免費換種族一起放這裡） */}
      <div className="panel" data-testid="world-growth-look">
        <div className="section-title">外觀與種族</div>
        <LookChangeLine character={view.character} busy={busy} onAct={(a) => void onAct(a)} />
        {view.character.free_race_change === true && <RaceChangeLine character={view.character} busy={busy} onAct={(a) => void onAct(a)} />}
      </div>
      <div className="panel">
        <div className="section-title">屬性點</div>
        {view.character.attribute_points <= 0 && <div className="muted small">沒有未分配的屬性點（升級時每級 2 點）。</div>}
        <AttributeRespecSection
          hero={view.hero}
          busy={busy || (!view.growth.can_allocate && !view.growth.can_spend)}
          onChoose={onChoose}
          campfire={view.growth.at_service}
          runId={cid}
          previewAllocation={previewAllocation}
          respecLocked={view.growth.can_spend ? null : lock}
          allocateNote="沒有遭遇時隨時可以分配；重配只在城鎮與營火。"
        />
      </div>
      <FlashSection runId={cid} hero={view.hero} busy={busy} onChoose={onChoose} previewFlash={previewFlash} lockedReason={lock} />
      <CampfireSkillCare runId={cid} hero={view.hero} busy={busy || lock !== null} onChoose={onChoose} previewFlash={previewFlash} place={PLACE} />
      <OathSection view={view} busy={busy} onAct={onAct} />
    </div>
  );
}

function OathSection({ view, busy, onAct }: Pick<Props, "view" | "busy" | "onAct">) {
  const oath = view.oath;
  const [templateId, setTemplateId] = useState<string>(oath.templates?.[0]?.id ?? "");
  const template = (oath.templates ?? []).find((t) => t.id === templateId);
  const [params, setParams] = useState<Record<string, string | number>>(() => (template ? defaultParams(template) : {}));
  const [text, setText] = useState("");
  const [confirmRelease, setConfirmRelease] = useState(false);
  const button = oathButton(view);
  return (
    <div className="panel world-oath" data-testid="world-oath">
      <div className="section-title">誓約</div>
      <p className="small muted">在城鎮或營火立誓，同時 1 個，一直有效到自己解除；解除後現實 1 天內不能再立。</p>
      {oath.available && (
        <p className="small muted" data-testid="world-oath-rules">
          {[oath.slot_zh, oath.penalty_zh].filter((s) => s !== undefined && s !== "").join("。")}
        </p>
      )}
      {oath.current != null ? (
        <div className="small" data-testid="world-oath-current">
          目前的誓約：<b>{oath.current.name_zh}</b>（難度 {oath.current.difficulty_zh}
          {oath.current.params_zh !== "" ? `・${oath.current.params_zh}` : ""}）
          {(oath.current.bonus_zh ?? "") !== "" && <div className="small">加成：{oath.current.bonus_zh}</div>}
          {(oath.current.judge_zh ?? "") !== "" && <div className="small muted">{oath.current.judge_zh}</div>}
          <div className="run-actions">
            {!confirmRelease ? (
              <button type="button" disabled={busy || !oath.can_release} onClick={() => setConfirmRelease(true)} data-testid="world-oath-release">
                解除誓約
              </button>
            ) : (
              <>
                <span className="small">解除後現實 1 天內不能再立誓，確定？</span>
                <button
                  type="button"
                  className="danger primary"
                  disabled={busy}
                  data-testid="world-oath-release-yes"
                  onClick={() => void onAct({ kind: "release_oath" }).then(() => setConfirmRelease(false))}
                >
                  確定解除
                </button>
                <button data-sfx="ui_cancel" type="button" disabled={busy} onClick={() => setConfirmRelease(false)}>
                  取消
                </button>
              </>
            )}
          </div>
        </div>
      ) : (
        oath.cooldown_zh != null && <div className="small muted">剛解除過誓約：還要 {oath.cooldown_zh} 才能再立。</div>
      )}
      {oath.current == null && oath.available && (
        <div className="world-oath-form">
          <label className="small">
            模板：
            <select
              value={templateId}
              disabled={busy}
              onChange={(e) => {
                setTemplateId(e.target.value);
                const next = (oath.templates ?? []).find((t) => t.id === e.target.value);
                setParams(next ? defaultParams(next) : {});
              }}
            >
              {(oath.templates ?? []).map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name_zh}（{t.difficulty_zh}）
                </option>
              ))}
            </select>
          </label>
          {template !== undefined && (
            <div className="small world-oath-detail" data-testid="world-oath-detail">
              {(template.description_zh ?? "") !== "" && <div>{template.description_zh}</div>}
              {(template.bonus_zh ?? "") !== "" && <div>加成：{template.bonus_zh}</div>}
              {(template.judge_zh ?? "") !== "" && <div className="muted">{template.judge_zh}</div>}
            </div>
          )}
          {(template?.params ?? []).map((p) => (
            <label key={p.id} className="small">
              {paramLabel(p)}：
              {p.kind === "choice" ? (
                <select value={String(params[p.id] ?? "")} disabled={busy} onChange={(e) => setParams({ ...params, [p.id]: e.target.value })}>
                  {(p.choices ?? []).map((c) => (
                    <option key={c} value={c}>
                      {choiceLabel(p, c)}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="number"
                  min={p.min}
                  max={p.max}
                  value={Number(params[p.id] ?? p.min)}
                  disabled={busy}
                  onChange={(e) => setParams({ ...params, [p.id]: Number(e.target.value) })}
                />
              )}
            </label>
          ))}
          <label className="small">
            誓言（選填）：
            <input type="text" maxLength={200} value={text} disabled={busy} onChange={(e) => setText(e.target.value)} />
          </label>
        </div>
      )}
      {oath.current == null && (
        <div className="run-actions">
          <Hint text={button.reason ?? undefined}>
            <button
              type="button"
              className="primary"
              disabled={busy || button.reason !== null || template === undefined}
              data-testid="world-oath-swear"
              onClick={() => template !== undefined && void onAct(swearAction(template.id, params, text))}
            >
              {button.label}
            </button>
          </Hint>
        </div>
      )}
    </div>
  );
}
