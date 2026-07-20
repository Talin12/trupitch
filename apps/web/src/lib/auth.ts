const TOKEN_KEY = "trupitch_token";

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY);

export const clearToken = (): void => localStorage.removeItem(TOKEN_KEY);

export function captureTokenFromUrl(): string | null {
  const params = new URLSearchParams(window.location.search);
  const incoming = params.get("token");
  if (incoming) {
    localStorage.setItem(TOKEN_KEY, incoming);
    window.history.replaceState({}, "", window.location.pathname);
  }
  return incoming;
}
