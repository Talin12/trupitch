// Hacker session-token storage. There's no server-side session — the
// JWT stored here (in localStorage, so it survives a page reload) is
// the only proof of identity, sent as `Authorization: Bearer <token>`
// on every authenticated request (see EventPage.tsx).

const TOKEN_KEY = "trupitch_token";

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY);

export const clearToken = (): void => localStorage.removeItem(TOKEN_KEY);

/** Capture ?token=... arriving from the OAuth callback, then clean the URL.
 *
 * After apps/api/routers/auth.py's GitHub callback finishes, it
 * redirects the browser to `{next_path}?token=<jwt>`. This function is
 * called once on page load to notice that query param, persist it to
 * localStorage, and then strip it from the visible URL (via
 * replaceState) so the token doesn't linger in browser history or get
 * accidentally shared via a copied link.
 */
export function captureTokenFromUrl(): string | null {
  const params = new URLSearchParams(window.location.search);
  const incoming = params.get("token");
  if (incoming) {
    localStorage.setItem(TOKEN_KEY, incoming);
    window.history.replaceState({}, "", window.location.pathname);
  }
  return incoming;
}
