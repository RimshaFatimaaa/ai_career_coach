import { api } from "@/lib/api";

export async function desiredRole(): Promise<string> {
  try {
    const p = await api<{ career_goals?: { desired_role?: string; desired_career?: string } }>("/api/profile");
    return (p.career_goals?.desired_role || p.career_goals?.desired_career || "").trim();
  } catch {
    return "";
  }
}
