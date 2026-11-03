// 大世界入口（Phase 5E-1；docs/phases/Phase5計畫.md 28.8）：先讀登入狀態，開發模式開或已登入 → 大世界畫面；
// 否則 → 登入畫面。收到 401（token 過期、帳號被停用）時 client.ts 已清掉 token，這裡重新讀狀態。
import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { AuthStatus } from "../api/types";
import { AUTH_EXPIRED_EVENT, worldGate, writeToken } from "../auth/auth";
import { ErrorBanner } from "../ui/ErrorBanner";
import { writeWorldChar } from "../world/mapView";
import { LoginScreen } from "./LoginScreen";
import { WorldScreen } from "./WorldScreen";

interface Props {
  onHome(): void;
}

export function WorldEntry({ onHome }: Props) {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [wantLogin, setWantLogin] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    api.authStatus().then(
      (s) => {
        setStatus(s);
        setError(null);
      },
      (e: unknown) => setError(e instanceof Error ? e.message : String(e)),
    );
  }, []);

  useEffect(() => {
    refresh();
    const onExpired = () => {
      writeWorldChar(null);
      setWantLogin(false);
      refresh();
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
  }, [refresh]);

  if (status === null) {
    return (
      <div className="loading">
        <ErrorBanner message={error} onClose={() => setError(null)} />
        {error === null ? "載入中……" : "無法讀取登入狀態。"}
        {error !== null && (
          <button type="button" onClick={onHome}>
            返回首頁
          </button>
        )}
      </div>
    );
  }
  if (wantLogin || worldGate(status) === "login") {
    return (
      <LoginScreen
        onLoggedIn={() => {
          writeWorldChar(null); // 上次記住的角色可能不是這個帳號的
          setWantLogin(false);
          refresh();
        }}
        onHome={onHome}
        onCancel={status.dev_mode ? () => setWantLogin(false) : undefined}
      />
    );
  }
  const logout = () => {
    api.logout().then(
      () => undefined,
      () => undefined,
    );
    writeToken(null);
    writeWorldChar(null);
    refresh();
  };
  return (
    <WorldScreen
      key={status.account?.account_id ?? "dev"}
      onHome={onHome}
      onLogin={status.account == null ? () => setWantLogin(true) : undefined}
      onLogout={status.account != null ? logout : undefined}
    />
  );
}
