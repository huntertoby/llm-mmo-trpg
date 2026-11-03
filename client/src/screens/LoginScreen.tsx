// 大世界的登入畫面（Phase 5E-1；docs/phases/Phase5計畫.md 28.8）：帳號、密碼、登入。
// 帳號由 Discord Bot 發放（5E-2；本機測試用 scripts/dev_account.py 建立），這裡沒有註冊。
import { useState, type FormEvent } from "react";
import { api } from "../api/client";
import { loginProblem, PASSWORD_MAX, USERNAME_MAX, writeToken } from "../auth/auth";
import { ErrorBanner } from "../ui/ErrorBanner";

interface Props {
  onLoggedIn(): void;
  onHome(): void;
  /** 開發模式下從角色畫面來登入時可以取消（回到不用登入的角色畫面）。 */
  onCancel?(): void;
}

export function LoginScreen({ onLoggedIn, onHome, onCancel }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const problem = loginProblem(username, password);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (problem !== null) return;
    setBusy(true);
    setError(null);
    try {
      const reply = await api.login(username.trim(), password);
      writeToken(reply.token);
      setPassword("");
      onLoggedIn();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  return (
    <div className="start-screen world-login">
      <h1>大世界・登入</h1>
      <ErrorBanner message={error} onClose={() => setError(null)} />
      <form className="panel start-form" onSubmit={(e) => void submit(e)}>
        <label>
          帳號
          <input
            value={username}
            maxLength={USERNAME_MAX}
            autoComplete="username"
            onChange={(e) => setUsername(e.target.value)}
            data-testid="login-username"
          />
        </label>
        <label>
          密碼
          <input
            type="password"
            value={password}
            maxLength={PASSWORD_MAX}
            autoComplete="current-password"
            onChange={(e) => setPassword(e.target.value)}
            data-testid="login-password"
          />
        </label>
        <div className="muted small">帳號與密碼由 Discord 機器人發放；忘記密碼請向機器人重設。</div>
        <div className="run-actions">
          <button type="submit" className="primary" disabled={busy || problem !== null} data-testid="login-submit">
            {busy ? "登入中……" : "登入"}
          </button>
          {onCancel !== undefined && (
            <button type="button" onClick={onCancel}>
              不登入（開發模式）
            </button>
          )}
          <button type="button" onClick={onHome}>
            返回首頁
          </button>
        </div>
      </form>
    </div>
  );
}
