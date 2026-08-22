const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type AppAlertKind = "error" | "limit";

export type AppAlert = {
  kind: AppAlertKind;
  message: string;
};

let lastAlert = { message: "", at: 0 };

export function isPlanLimitMessage(message?: string) {
  if (!message) return false;
  return /plan limit|requires a paid plan|upgrade to continue|not on your plan|pro plan required/i.test(message);
}

export function showAppAlert(message: string, kind?: AppAlertKind) {
  if (typeof window === "undefined" || !message) return;
  const resolved: AppAlertKind = kind || (isPlanLimitMessage(message) ? "limit" : "error");
  const now = Date.now();
  if (lastAlert.message === message && now - lastAlert.at < 600) return;
  lastAlert = { message, at: now };
  window.dispatchEvent(new CustomEvent<AppAlert>("cc-app-alert", { detail: { kind: resolved, message } }));
}

export function showPlanLimit(message: string) {
  showAppAlert(message, "limit");
}

export function getToken() {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("cc_token") || "";
}

export function setSession(token: string, user: unknown) {
  localStorage.setItem("cc_token", token);
  localStorage.setItem("cc_user", JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem("cc_token");
  localStorage.removeItem("cc_user");
}

export async function api<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API}${path}`, { ...init, headers });
  if (res.status === 401) {
    clearSession();
    if (typeof window !== "undefined" && !path.startsWith("/api/auth")) {
      window.location.href = "/login";
    }
  }
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    if (!res.ok) throw new Error(text || res.statusText);
    throw new Error("Invalid JSON from API");
  }
  if (!res.ok) {
    const detail = data?.detail;
    const msg = Array.isArray(detail) ? detail.map((d: { msg?: string }) => d.msg).join(", ") : detail || res.statusText;
    const textMsg = typeof msg === "string" ? msg : "Request failed";
    if (res.status !== 401) {
      showAppAlert(textMsg, res.status === 402 || isPlanLimitMessage(textMsg) ? "limit" : "error");
    }
    throw new Error(textMsg);
  }
  return data as T;
}

export function downloadUrl(path: string) {
  return `${API}${path}`;
}

export async function downloadFile(path: string, filename: string) {
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, { headers: { Authorization: `Bearer ${getToken()}` } });
  } catch {
    throw new Error("Could not reach the API to export this file. Check that the backend is running on port 8000.");
  }
  if (!res.ok) {
    const text = await res.text();
    let msg = "Export failed";
    try {
      const data = text ? JSON.parse(text) : null;
      const detail = data?.detail;
      msg = Array.isArray(detail) ? detail.map((d: { msg?: string }) => d.msg).join(", ") : detail || msg;
    } catch {
      if (text) msg = text.slice(0, 180);
    }
    const textMsg = typeof msg === "string" ? msg : "Export failed";
    showAppAlert(textMsg, res.status === 402 || isPlanLimitMessage(textMsg) ? "limit" : "error");
    throw new Error(textMsg);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
