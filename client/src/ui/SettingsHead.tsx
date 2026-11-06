// 設定面板的分區標題（UI-E2；docs/archive/art/偷懶自查.md G12）：小圖示＋標題，分成聲音、減少動態、提示三區。
// 戰鬥「版面」面板與大世界齒輪面板共用（同一個元件）。圖示是純裝飾（`aria-hidden`），名稱寫在標題文字。
export type SettingsSectionIcon = "sound" | "motion" | "hint";

const GOLD = "#e8bb48";
const INK = "#1c1712";

function Icon({ name }: { name: SettingsSectionIcon }) {
  return (
    <svg className="settings-head-icon" viewBox="0 0 20 20" width={16} height={16} aria-hidden="true" data-icon={name}>
      {name === "sound" && (
        <>
          <path d="M3 8h3l4-4v12l-4-4H3z" fill={GOLD} stroke={INK} strokeWidth="1" strokeLinejoin="round" />
          <path d="M13 7.5q2 2.5 0 5M15 5.5q4 4.5 0 9" fill="none" stroke={GOLD} strokeWidth="1.5" strokeLinecap="round" />
        </>
      )}
      {name === "motion" && (
        <>
          <circle cx="12" cy="10" r="4.5" fill={GOLD} stroke={INK} strokeWidth="1" />
          <path d="M2 7h4M1 10h4M2 13h4" stroke={GOLD} strokeWidth="1.5" strokeLinecap="round" opacity="0.7" />
        </>
      )}
      {name === "hint" && (
        <>
          <path d="M10 2a5.5 5.5 0 0 0-3 10.1V14h6v-1.9A5.5 5.5 0 0 0 10 2z" fill={GOLD} stroke={INK} strokeWidth="1" />
          <rect x="7.5" y="15" width="5" height="2.5" rx="1" fill={GOLD} stroke={INK} strokeWidth="1" />
        </>
      )}
    </svg>
  );
}

export function SettingsHead({ icon, children }: { icon: SettingsSectionIcon; children: string }) {
  return (
    <div className="section-title settings-head" data-settings-head={icon}>
      <Icon name={icon} />
      <span>{children}</span>
    </div>
  );
}
