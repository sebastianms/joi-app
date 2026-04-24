const SESSION_KEY = "joi_session_id";

export function getSessionId(): string {
  if (typeof window === "undefined") return "";
  const existing = localStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  const id = crypto.randomUUID();
  localStorage.setItem(SESSION_KEY, id);
  return id;
}
