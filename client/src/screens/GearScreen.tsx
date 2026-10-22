// 裝備測試（Phase 3G-G4）：為主角的 9 個欄位選測試物品，或手動組一件物品（只能從白名單掛詞條）；
// 不合法時顯示原因；英雄面板顯示加成來源；通過後進靶場戰鬥，預覽的數字已含裝備。
import { useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError } from "../api/client";
import type { BattleResponse, BuildSummary, GearCatalog, GearCheck, WorkshopArena } from "../api/types";
import {
  emptyDraft,
  occupiesOffHand,
  parseSelection,
  sanitizeSelection,
  SELECTION_KEY,
  selectionProblems,
  toEquipment,
  type CustomDraft,
  type Selection,
} from "../gear/gearDraft";
import { ErrorBanner } from "../ui/ErrorBanner";
import { CustomItemForm } from "../ui/gear/CustomItemForm";
import { HeroGearPanel } from "../ui/gear/HeroGearPanel";
import { ItemList } from "../ui/gear/ItemList";
import { SlotGrid } from "../ui/gear/SlotGrid";
import { parseSeed, randomSeed } from "./StartScreen";

interface Props {
  onHome(): void;
  /** 回到技能工坊分頁。 */
  onSkills(): void;
  onStartBattle(response: BattleResponse): void;
}

const CHECK_DELAY_MS = 200;

function message(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

function readSaved(): Selection {
  try {
    return parseSelection(typeof localStorage === "undefined" ? null : localStorage.getItem(SELECTION_KEY));
  } catch {
    return {};
  }
}

function writeSaved(selection: Selection): void {
  try {
    if (typeof localStorage !== "undefined") localStorage.setItem(SELECTION_KEY, JSON.stringify(selection));
  } catch {
    // 存不進去（無痕視窗、容量滿）就略過：暫存只是方便。
  }
}

export function GearScreen({ onHome, onSkills, onStartBattle }: Props) {
  const [catalog, setCatalog] = useState<GearCatalog | null>(null);
  const [builds, setBuilds] = useState<BuildSummary[]>([]);
  const [arena, setArena] = useState<WorkshopArena | null>(null);
  const [selection, setSelection] = useState<Selection>(readSaved);
  const [selected, setSelected] = useState("main_hand");
  const [mode, setMode] = useState<"items" | "custom">("items");
  const [drafts, setDrafts] = useState<Record<string, CustomDraft>>({});
  const [buildId, setBuildId] = useState("");
  const [opponents, setOpponents] = useState("");
  const [seedText, setSeedText] = useState(() => String(randomSeed()));
  const [check, setCheck] = useState<GearCheck | null>(null);
  const [checking, setChecking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.gearCatalog(), api.builds(), api.workshopArena()])
      .then(([c, b, a]) => {
        if (cancelled) return;
        setCatalog(c);
        setBuilds(b);
        setArena(a);
        setBuildId((cur) => cur || (b[0]?.id ?? ""));
        setOpponents((cur) => cur || (a.opponents[0]?.id ?? ""));
        setSelection((cur) => sanitizeSelection(cur, c));
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(message(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => writeSaved(selection), [selection]);

  const equipment = useMemo(() => (catalog === null ? {} : toEquipment(selection, catalog)), [catalog, selection]);
  const localProblems = useMemo(() => (catalog === null ? [] : selectionProblems(selection, catalog)), [catalog, selection]);

  // 整組裝備的檢查（伺服器裁決）：防抖，且只採用最後一次請求的結果。
  useEffect(() => {
    if (catalog === null || buildId === "") return undefined;
    const id = ++requestId.current;
    setChecking(true);
    const timer = setTimeout(() => {
      api
        .gearCheck({ hero_build: buildId, equipment })
        .then((result) => {
          if (id !== requestId.current) return;
          setCheck(result);
          setChecking(false);
        })
        .catch((e: unknown) => {
          if (id !== requestId.current) return;
          setError(message(e));
          setChecking(false);
        });
    }, CHECK_DELAY_MS);
    return () => clearTimeout(timer);
  }, [catalog, buildId, equipment]);

  if (catalog === null) {
    return (
      <div className="workshop-screen gear-screen">
        <ErrorBanner message={error} onClose={() => setError(null)} />
        <div className="loading">載入裝備目錄……</div>
      </div>
    );
  }

  const slot = catalog.slots.find((s) => s.slot === selected) ?? catalog.slots[0];
  if (slot === undefined) return null;
  const offHandBlocked = occupiesOffHand(selection, catalog);
  const current = selection[slot.slot];
  const draft = drafts[slot.slot] ?? (current !== undefined && "custom" in current ? current.custom : emptyDraft(slot.slot_type_zh));
  // 本機檢查（即時）有問題就顯示它；本機沒抓到、伺服器裁決不合法時顯示伺服器的原因（以伺服器為準）。
  const problems = localProblems.length > 0 ? localProblems : check !== null && !check.legal ? [...check.problems] : [];
  const seed = parseSeed(seedText);
  const legal = localProblems.length === 0 && check !== null && check.legal && !checking;
  const ready = legal && buildId !== "" && seed !== null && !busy;

  const setPick = (slotId: string, pick: Selection[string]) =>
    setSelection((cur) => {
      const next = { ...cur };
      if (pick === undefined) delete next[slotId];
      else next[slotId] = pick;
      return next;
    });

  async function start() {
    if (!ready || seed === null || catalog === null) return;
    setBusy(true);
    setError(null);
    try {
      const response = await api.createBattle({
        map_id: arena?.default_map ?? "training_range",
        seed,
        hero_build: buildId,
        ally_builds: [],
        max_rounds: arena?.max_rounds ?? 30,
        equipment,
        ...(opponents !== "" ? { opponents } : {}),
      });
      onStartBattle(response);
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  return (
    <div className="workshop-screen gear-screen">
      <header className="ws-header">
        <h1>裝備測試</h1>
        <nav className="ws-tabs" aria-label="工坊分頁">
          <button type="button" onClick={onSkills}>
            技能
          </button>
          <button type="button" className="active" aria-current="page">
            裝備
          </button>
        </nav>
        <span className="muted">為主角穿上測試物品或手動組一件，看加成怎麼算，再進靶場試打。</span>
        <span className="ws-header-tools">
          <button type="button" onClick={() => setSelection({})} disabled={Object.keys(selection).length === 0}>
            全部卸下
          </button>
          <button type="button" onClick={onHome}>
            回首頁
          </button>
        </span>
      </header>
      <ErrorBanner message={error} onClose={() => setError(null)} />
      <div className="gear-layout">
        <section className="panel gear-left">
          <div className="section-title">主角裝備（點格子選欄位）</div>
          <SlotGrid
            catalog={catalog}
            selection={selection}
            selected={slot.slot}
            offHandBlocked={offHandBlocked}
            onSelect={(s) => {
              setSelected(s);
              setMode("items");
            }}
          />
          {problems.length > 0 && (
            <ul className="gear-problems" role="alert" aria-label="不合法的原因">
              <li className="gear-problems-title">這組裝備不合法：</li>
              {problems.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          )}
          {problems.length === 0 && check?.legal === true && <div className="gear-legal">這組裝備合法（由伺服器檢查）。</div>}
          <HeroGearPanel hero={check?.legal === true ? check.hero : null} pending={checking} />
        </section>
        <section className="panel gear-right">
          <div className="gear-right-head">
            <div className="section-title">
              {slot.name_zh}（{slot.slot_type_zh}類）
            </div>
            <div className="ws-tabs" role="tablist">
              <button type="button" role="tab" aria-selected={mode === "items"} className={mode === "items" ? "active" : ""} onClick={() => setMode("items")}>
                測試物品
              </button>
              <button type="button" role="tab" aria-selected={mode === "custom"} className={mode === "custom" ? "active" : ""} onClick={() => setMode("custom")}>
                手動組裝
              </button>
            </div>
          </div>
          {slot.slot === "off_hand" && offHandBlocked && (
            <div className="gear-note">主手是雙手或成對武器，副手被占用：要放副手物品請先換掉主手。</div>
          )}
          {mode === "items" ? (
            <ItemList catalog={catalog} slot={slot} selection={selection} onPick={(id) => setPick(slot.slot, id === null ? undefined : { item_id: id })} />
          ) : (
            <CustomItemForm
              catalog={catalog}
              slot={slot}
              draft={draft}
              onChange={(d) => setDrafts((cur) => ({ ...cur, [slot.slot]: d }))}
              onEquip={() => setPick(slot.slot, { custom: draft })}
              equipped={current !== undefined && "custom" in current}
            />
          )}
          {current !== undefined && (
            <button type="button" className="gear-unequip" onClick={() => setPick(slot.slot, undefined)}>
              卸下{slot.name_zh}
            </button>
          )}
        </section>
      </div>
      <section className="panel gear-tryout">
        <div className="section-title">進靶場試打</div>
        <div className="gear-tryout-form">
          <label>
            主角 build
            <select value={buildId} onChange={(e) => setBuildId(e.target.value)}>
              {builds.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name_zh}（{b.weapon_name_zh}）
                </option>
              ))}
            </select>
          </label>
          <label>
            對手
            <select value={opponents} onChange={(e) => setOpponents(e.target.value)}>
              {(arena?.opponents ?? []).map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name_zh}
                </option>
              ))}
            </select>
          </label>
          <label>
            種子
            <span className="seed-row">
              <input value={seedText} inputMode="numeric" onChange={(e) => setSeedText(e.target.value)} aria-invalid={seed === null} />
              <button type="button" onClick={() => setSeedText(String(randomSeed()))}>
                隨機
              </button>
            </span>
          </label>
          <button type="button" className="primary" disabled={!ready} onClick={() => void start()}>
            {busy ? "建立中……" : "進入靶場"}
          </button>
        </div>
        <div className="muted small">主手選了武器物品時，主角的武器會換成那把（技能要和武器相容，否則會顯示原因）。</div>
      </section>
    </div>
  );
}
