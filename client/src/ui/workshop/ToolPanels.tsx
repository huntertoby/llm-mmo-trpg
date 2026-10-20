// 工坊的輔助面板：隨機一個、匯出 YAML、進階直接編輯 YAML。
import { useEffect, useRef, useState } from "react";
import { api } from "../../api/client";
import type { Choice, SkillRarity, WorkshopExport } from "../../api/types";
import { isEmptyDraft, type Json } from "../../workshop/draft";
import { RARITY_NAMES } from "../../workshop/state";
import { parseSeed, randomSeed } from "../../screens/StartScreen";
import { draftToYaml, parseDraftText, sameDraft } from "../../workshop/yamlEdit";
import { ErrorBanner } from "../ErrorBanner";

/** 隨機組出來的技能 ID 是「skill_rand_種子」；進編輯器時拿掉，之後由內容雜湊重新產生。 */
export function withoutId(skill: Json): Json {
  const { id: _id, ...rest } = skill;
  return rest;
}

/** 用瀏覽器下載一段文字（Blob ＋ 暫時的連結）。 */
export function downloadText(filename: string, text: string): void {
  const url = URL.createObjectURL(new Blob([text], { type: "text/yaml;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

interface RandomProps {
  skeletons: readonly Choice[];
  draft: Json;
  onResult(draft: Json): void;
}

export function RandomPanel({ skeletons, draft, onResult }: RandomProps) {
  const [tier, setTier] = useState("");
  const [rarity, setRarity] = useState("");
  const [skeleton, setSkeleton] = useState("");
  const [seedText, setSeedText] = useState(() => String(randomSeed()));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const seed = parseSeed(seedText);

  async function roll() {
    if (seed === null) return;
    if (!isEmptyDraft(draft) && !window.confirm("隨機產生的技能會取代目前正在編輯的內容，確定嗎？")) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.workshopRandom({
        seed,
        tier: tier === "" ? null : Number(tier),
        rarity: rarity === "" ? null : (rarity as SkillRarity),
        skeleton: skeleton === "" ? null : skeleton,
      });
      onResult(withoutId(result.skill));
      setSeedText(String(randomSeed()));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel ws-panel">
      <div className="section-title">隨機一個</div>
      <div className="muted small">讓隨機組合器先組出一個合法的技能，再拿來修改。不指定的欄位由種子決定。</div>
      <ErrorBanner message={error} onClose={() => setError(null)} />
      <div className="ws-tryout-form">
        <label>
          階級
          <select value={tier} onChange={(e) => setTier(e.target.value)}>
            <option value="">不指定</option>
            {[1, 2, 3, 4, 5].map((t) => (
              <option key={t} value={t}>
                {t} 階
              </option>
            ))}
          </select>
        </label>
        <label>
          稀有度
          <select value={rarity} onChange={(e) => setRarity(e.target.value)}>
            <option value="">不指定</option>
            {Object.entries(RARITY_NAMES).map(([id, name]) => (
              <option key={id} value={id}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <label>
          骨架
          <select value={skeleton} onChange={(e) => setSkeleton(e.target.value)}>
            <option value="">不指定</option>
            {skeletons.map((s) => (
              <option key={String(s.value)} value={String(s.value)}>
                {s.name_zh}
              </option>
            ))}
          </select>
        </label>
        <label>
          種子
          <span className="seed-row">
            <input value={seedText} inputMode="numeric" onChange={(e) => setSeedText(e.target.value)} aria-invalid={seed === null} />
            <button type="button" onClick={() => setSeedText(String(randomSeed()))}>
              換一個
            </button>
          </span>
        </label>
      </div>
      <button type="button" disabled={busy || seed === null} onClick={() => void roll()}>
        {busy ? "產生中……" : "隨機一個"}
      </button>
    </div>
  );
}

export function ExportPanel({ draft }: { draft: Json }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<WorkshopExport | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    setDone(null);
    try {
      const result = await api.workshopExport(draft);
      downloadText(result.filename, result.yaml);
      setDone(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel ws-panel">
      <div className="section-title">匯出</div>
      <div className="muted small">
        下載成 YAML 檔（和 content/skills 裡的技能同格式，來源標為「工坊」）。工坊的技能只存在這個瀏覽器；要收進正式內容請把檔案交給 PM。
        還沒組完整或不合法也能匯出，方便先存半成品。
      </div>
      <ErrorBanner message={error} onClose={() => setError(null)} />
      <button type="button" disabled={busy || isEmptyDraft(draft)} onClick={() => void run()}>
        {busy ? "匯出中……" : "下載 YAML"}
      </button>
      {done !== null && (
        <div className="small">
          已下載 <code>{done.filename}</code>。
          {done.legal ? "這個技能合法。" : "注意：這個技能目前不合法，收進正式內容前需要修正。"}
          {done.problems.length > 0 && (
            <ul>
              {done.problems.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export function YamlPanel({ draft, onDraft }: { draft: Json; onDraft(draft: Json): void }) {
  const [text, setText] = useState(() => draftToYaml(draft));
  const [error, setError] = useState<string | null>(null);
  const last = useRef<Json>(draft);

  // 草稿被別處改了（一步步選、隨機、重設）就同步文字；自己打字造成的改變不覆蓋游標。
  useEffect(() => {
    if (sameDraft(draft, last.current)) return;
    last.current = draft;
    setText(draftToYaml(draft));
    setError(null);
  }, [draft]);

  function edit(value: string) {
    setText(value);
    const parsed = parseDraftText(value);
    if (!parsed.ok) {
      setError(parsed.error);
      return;
    }
    setError(null);
    last.current = parsed.draft;
    onDraft(parsed.draft);
  }

  return (
    <details className="panel ws-panel">
      <summary className="section-title">進階：直接編輯 YAML</summary>
      <div className="muted small">
        一步步組的畫面不展開「巢狀效果」（賭注的贏／輸分支、消耗狀態後的效果、持續區域、擊殺時效果）；這些請在這裡直接改 YAML。
        改完會即時檢查；格式有誤時不會套用，上一個有效的內容仍保留。
      </div>
      <textarea
        className="ws-yaml"
        value={text}
        spellCheck={false}
        rows={16}
        aria-label="技能 YAML"
        aria-invalid={error !== null}
        onChange={(e) => edit(e.target.value)}
      />
      {error !== null && <div className="error-text">{error}</div>}
    </details>
  );
}
