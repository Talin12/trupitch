const TOKEN_KEY = "trupitch_token";
const ORG_TOKEN_KEY = "trupitch_organizer_token";

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY);

export const clearToken = (): void => localStorage.removeItem(TOKEN_KEY);

// Organizer session (email/password login) — kept separate from the hacker
// GitHub-OAuth token above; the two are not interchangeable server-side.
export const getOrganizerToken = (): string | null =>
  localStorage.getItem(ORG_TOKEN_KEY);

export const setOrganizerToken = (token: string): void =>
  localStorage.setItem(ORG_TOKEN_KEY, token);

export const clearOrganizerToken = (): void =>
  localStorage.removeItem(ORG_TOKEN_KEY);

export const organizerAuthHeader = (): Record<string, string> => {
  const token = getOrganizerToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export function captureTokenFromUrl(): string | null {
  const params = new URLSearchParams(window.location.search);
  const incoming = params.get("token");
  if (incoming) {
    localStorage.setItem(TOKEN_KEY, incoming);
    window.history.replaceState({}, "", window.location.pathname);
  }
  return incoming;
}
