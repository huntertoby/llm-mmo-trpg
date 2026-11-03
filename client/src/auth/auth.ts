// 帳號登入的純函式與 token 存取（Phase 5E-1；docs/phases/Phase5計畫.md 28.8）。
// token 存瀏覽器 localStorage（存取失敗就當作沒登入）；每個 API 請求帶 `Authorization: Bearer <token>`。
import type { AuthStatus } from "../api/types";

export const AUTH_TOKEN_KEY = "trpg.auth.token";
/** 收到 401 時發出的事件（client.ts 發；大世界入口與 App 聽）：token 已清掉，回登入畫面。
 * 5D-R2：開發模式關時一輪、戰鬥、工坊、裝備測試也要登入，沒帶 token 的 401 也發。 */
export const AUTH_EXPIRED_EVENT = "trpg-auth-expired";

export const USERNAME_MAX = 20;
export const PASSWORD_MAX = 128;

export function readToken(): string | null {
  try {
    return window.localStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function writeToken(token: string | null): void {
  try {
    if (token === null) window.localStorage.removeItem(AUTH_TOKEN_KEY);
    else window.localStorage.setItem(AUTH_TOKEN_KEY, token);
  } catch {
    // 不能存：這次分頁裡照樣能用，重新整理後要再登入
  }
}

/** 這個回應要不要導到登入畫面（5D-R2）：401，且不是登入端點本身（帳號密碼錯也是 401）。 */
export function needsLogin(status: number, path: string): boolean {
  return status === 401 && !path.startsWith("/auth/");
}

/** 請求要帶的標頭（沒登入＝空）。 */
export function authHeaders(token: string | null): Record<string, string> {
  return token === null || token === "" ? {} : { Authorization: `Bearer ${token}` };
}

/** 登入表單的問題（`null` ＝可以送出）。帳號規則由後端檢查，這裡只擋空白與長度。 */
export function loginProblem(username: string, password: string): string | null {
  if (username.trim() === "") return "請輸入帳號";
  if (username.trim().length > USERNAME_MAX) return `帳號最多 ${USERNAME_MAX} 字`;
  if (password === "") return "請輸入密碼";
  if (password.length > PASSWORD_MAX) return `密碼最多 ${PASSWORD_MAX} 字`;
  return null;
}

/** 進大世界前要看哪個畫面：已登入或開發模式 → 角色畫面；否則 → 登入畫面。 */
export function worldGate(status: AuthStatus): "login" | "world" {
  return status.account != null || status.dev_mode ? "world" : "login";
}

/** 角色畫面上方的帳號一行。 */
export function accountLine(status: AuthStatus): string {
  const account = status.account;
  if (account == null) return "開發模式（不用登入）";
  return `帳號 ${account.username}・角色 ${account.characters}／${account.max_characters}`;
}
