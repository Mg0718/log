import { create } from "zustand";
import { persist } from "zustand/middleware";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type UserRole = "seller" | "buyer";

interface AuthState {
  token: string | null;
  role: UserRole | null;
  fullName: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      role: null,
      fullName: null,

      login: async (username: string, password: string) => {
        const res = await fetch(`${API_URL}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Login failed" }));
          throw new Error(err.detail || "Login failed");
        }
        const data = await res.json();
        set({
          token: data.access_token,
          role: data.role as UserRole,
          fullName: data.full_name,
        });
      },

      logout: () => set({ token: null, role: null, fullName: null }),
    }),
    { name: "logosgotham-auth" }
  )
);

/** Helper: read auth headers from persisted store for use in non-hook contexts */
export function getAuthHeaders(): Record<string, string> {
  try {
    const stored = localStorage.getItem("logosgotham-auth");
    if (!stored) return {};
    const parsed = JSON.parse(stored);
    const token: string | null = parsed?.state?.token ?? null;
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}
