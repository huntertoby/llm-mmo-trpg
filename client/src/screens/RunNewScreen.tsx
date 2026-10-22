// 開新一輪（Phase 3-24b2，06 6.27.3）：自選起始武器 ＋ 選 2 個關鍵字（每個關鍵字的池各給 1 招起始技能）、配 4 點屬性、種子。
// 遊戲不定義流派：這個畫面不出現任何流派名稱。開發者起始包（12 個測試組合）只在網址帶 ?dev=1 時顯示。
import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { DevPack, RunResponse, RunRules, StartOptions, StartPreview } from "../api/types";
import { AttributeAllocator } from "../run/AttributeAllocator";
import { allocationComplete, baseAttributes, cleanAllocation, conHpGain, type Allocation } from "../run/flow";
import { canStart, isDevMode, keepAvailable, keywordAvailable, toggleKeyword } from "../run/startFlow";
import { ErrorBanner } from "../ui/ErrorBanner";
import { SkillCardView } from "../ui/SkillCardView";
import { parseSeed, randomSeed } from "./StartScreen";

interface Props {
  onCreated(run: RunResponse): void;
  onHome(): void;
}

const CLASS_LABELS: Record<string, string> = { melee: "近戰", ranged: "遠程", focus: "法器" };

export function RunNewScreen({ onCreated, onHome }: Props) {
  /** 開局規則（配點數）由伺服器提供，載入前為 `null`。 */
  const [rules, setRules] = useState<RunRules | null>(null);
  const [options, setOptions] = useState<StartOptions | null>(null);
  const [preview, setPreview] = useState<StartPreview | null>(null);
  const [weapon, setWeapon] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [alloc, setAlloc] = useState<Allocation>({});
  const [seedText, setSeedText] = useState(() => String(randomSeed()));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dev = isDevMode(window.location.search);
  const [packs, setPacks] = useState<DevPack[]>([]);
  const [packId, setPackId] = useState("");

  useEffect(() => {
    let cancelled = false;
    const fail = (e: unknown) => {
      if (!cancelled) setError(e instanceof Error ? e.message : String(e));
    };
    api.runRules().then((r) => !cancelled && setRules(r), fail);
    api.startOptions().then((o) => {
      if (cancelled) return;
      setOptions(o);
      setWeapon((cur) => cur || (o.weapons[0]?.id ?? ""));
    }, fail);
    if (dev) {
      api.devPacks().then((p) => {
        if (cancelled) return;
        setPacks(p);
        setPackId((cur) => cur || (p[0]?.id ?? ""));
      }, fail);
    }
    return () => {
      cancelled = true;
    };
  }, [dev]);

  const seed = parseSeed(seedText);
  const selectedKey = selected.join(",");

  useEffect(() => {
    if (weapon === "" || seed === null) return;
    let cancelled = false;
    api.startPreview(weapon, seed, selectedKey === "" ? [] : selectedKey.split(",")).then(
      (p) => {
        if (cancelled) return;
        setPreview(p);
        setSelected((cur) => {
          const kept = keepAvailable(cur, p.options);
          return kept.length === cur.length ? cur : kept;
        });
      },
      (e: unknown) => !cancelled && setError(e instanceof Error ? e.message : String(e)),
    );
    return () => {
      cancelled = true;
    };
  }, [weapon, seed, selectedKey]);

  const count = options?.keyword_count ?? 2;
  const weaponDef = options?.weapons.find((w) => w.id === weapon);
  const previewOptions = preview !== null && preview.weapon === weapon ? preview.options : [];
  const points = rules?.start_points ?? 0;
  const complete = rules !== null && allocationComplete(alloc, points);
  const ready = seed !== null && canStart(weapon, selected, count, previewOptions);

  async function create(auto: boolean) {
    if (!ready || seed === null || (!auto && !complete)) return;
    setBusy(true);
    setError(null);
    try {
      const body = { weapon, keywords: selected, seed, ...(auto ? {} : { attributes: cleanAllocation(alloc) }) };
      onCreated(await api.createRun(body));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  async function createDev() {
    if (packId === "" || seed === null) return;
    setBusy(true);
    setError(null);
    try {
      onCreated(await api.createRun({ dev_pack: packId, seed }));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    void create(false);
  }

  const chosen = selected
    .map((id) => previewOptions.find((o) => o.keyword.id === id))
    .filter((o) => o !== undefined && o.skill !== null && o.skill !== undefined);

  return (
    <div className="start-screen run-new">
      <h1>開新一輪</h1>
      <ErrorBanner message={error} onClose={() => setError(null)} />
      <form className="panel start-form" onSubmit={submit}>
        <div className="section-title">起始武器</div>
        <div className="run-weapon-list" data-testid="start-weapons">
          {options?.weapons.map((w) => (
            <button
              key={w.id}
              type="button"
              className={`run-weapon${weapon === w.id ? " primary selected" : ""}`}
              disabled={busy}
              onClick={() => setWeapon(w.id)}
              title={w.traits_zh.join("\n")}
            >
              {w.name_zh}
              <span className="muted small">　{CLASS_LABELS[w.weapon_class] ?? w.weapon_class}</span>
            </button>
          ))}
        </div>
        {weaponDef !== undefined && (
          <div className="muted small">
            主角：HP {weaponDef.hp + (rules === null ? 0 : conHpGain(alloc, rules.hp_per_con_point))}・法力 {weaponDef.mana}・武器 {weaponDef.name_zh}
            {weaponDef.traits_zh.length > 0 && <span data-testid="start-weapon-traits">（{weaponDef.traits_zh.join("；")}）</span>}
          </div>
        )}
        <div className="section-title">
          選 {count} 個關鍵字（{selected.length}/{count}）
        </div>
        <div className="muted small">每個關鍵字的技能池給你 1 招起始技能；技能之間靠「製造」與「利用」同一個關鍵字互相觸發。</div>
        <div className="run-keyword-list" data-testid="start-keywords">
          {previewOptions.map((o) => {
            const on = selected.includes(o.keyword.id);
            const available = keywordAvailable(o);
            return (
              <button
                key={o.keyword.id}
                type="button"
                className={`run-keyword${on ? " primary selected" : ""}${available ? "" : " unavailable"}`}
                disabled={busy || !available || (!on && selected.length >= count)}
                title={o.keyword.description_zh}
                onClick={() => setSelected((cur) => toggleKeyword(cur, o.keyword.id, count))}
              >
                <b>{o.keyword.name_zh}</b>
                <span className="small">　{available ? o.skill?.name_zh : `${weaponDef?.name_zh ?? "這把武器"}沒有起始技能`}</span>
              </button>
            );
          })}
        </div>
        {chosen.length > 0 && (
          <div className="run-start-preview" data-testid="start-preview">
            {chosen.map((o) =>
              o === undefined || o.skill === null || o.skill === undefined ? null : (
                <div key={o.keyword.id} className="run-start-preview-card">
                  <div className="small muted">「{o.keyword.name_zh}」池的起始技能</div>
                  <SkillCardView card={o.skill} compact />
                </div>
              ),
            )}
          </div>
        )}
        {rules !== null && (
          <>
            <div className="muted small">
              六項屬性起始都是 {rules.base_attribute}；另有 {rules.start_points} 點自由分配。
            </div>
            <AttributeAllocator base={baseAttributes(rules.base_attribute)} points={points} alloc={alloc} onChange={setAlloc} disabled={busy} hpPerCon={rules.hp_per_con_point} />
          </>
        )}
        <label>
          種子
          <span className="seed-row">
            <input
              value={seedText}
              inputMode="numeric"
              onChange={(e) => setSeedText(e.target.value)}
              aria-invalid={seed === null}
            />
            <button type="button" onClick={() => setSeedText(String(randomSeed()))}>
              隨機
            </button>
          </span>
        </label>
        {seed === null && <div className="error-text">種子必須是非負整數</div>}
        <div className="run-actions">
          <button type="submit" className="primary" disabled={busy || !ready || !complete}>
            {busy ? "建立中……" : "開始這一輪"}
          </button>
          <button type="button" disabled={busy || rules === null || !ready} onClick={() => void create(true)}>
            自動配點並開始
          </button>
          <button type="button" onClick={onHome}>
            返回
          </button>
        </div>
        <div className="muted small">
          共 5 場戰鬥加 Boss；HP、法力不會在戰鬥之間回復，只有營火（中段與 Boss 前）會回滿。隊友為 2 名標準隊友。
        </div>
      </form>
      {dev && (
        <div className="panel run-dev-packs" data-testid="dev-packs">
          <div className="section-title">開發者起始包（測試用，玩家看不到）</div>
          <span className="seed-row">
            <select value={packId} onChange={(e) => setPackId(e.target.value)} disabled={busy}>
              {packs.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label_zh}：{p.weapon_name_zh}＋{p.keywords.map((k) => k.name_zh).join("、")}
                </option>
              ))}
            </select>
            <button type="button" disabled={busy || packId === "" || seed === null} onClick={() => void createDev()}>
              一鍵開局
            </button>
          </span>
        </div>
      )}
    </div>
  );
}
