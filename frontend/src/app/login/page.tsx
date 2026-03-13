"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/useAuthStore";
import { Shield, Loader2, Package, ShoppingCart } from "lucide-react";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { login } = useAuthStore();
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
      router.push("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  const fillCredentials = (role: "seller" | "buyer") => {
    setUsername(role);
    setPassword(role === "seller" ? "seller123" : "buyer123");
    setError(null);
  };

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-[#050505] overflow-hidden font-mono">
      {/* Grid background */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(6,182,212,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(6,182,212,0.03)_1px,transparent_1px)] bg-[size:48px_48px]" />
      {/* Scanline overlay */}
      <div className="absolute inset-0 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,0,0,0.04)_2px,rgba(0,0,0,0.04)_4px)] pointer-events-none" />

      <div className="relative w-full max-w-sm">
        {/* Corner decorations */}
        <div className="absolute -top-px -left-px w-4 h-4 border-t border-l border-cyan-500/60" />
        <div className="absolute -top-px -right-px w-4 h-4 border-t border-r border-cyan-500/60" />
        <div className="absolute -bottom-px -left-px w-4 h-4 border-b border-l border-cyan-500/60" />
        <div className="absolute -bottom-px -right-px w-4 h-4 border-b border-r border-cyan-500/60" />

        <div className="p-8 border border-cyan-900/30 bg-black/90 backdrop-blur-md flex flex-col gap-6">
          {/* Header */}
          <div className="flex flex-col items-center gap-3">
            <div className="relative w-14 h-14 border border-cyan-500/40 flex items-center justify-center">
              <div className="absolute inset-0 border border-cyan-500/20 scale-110" />
              <Shield className="w-7 h-7 text-cyan-500" />
            </div>
            <div className="flex flex-col items-center gap-1">
              <h1 className="text-sm font-bold tracking-[0.5em] text-white uppercase">
                LOGOS GOTHAM
              </h1>
              <div className="text-[9px] text-cyan-900 font-bold tracking-[0.3em] uppercase">
                CLASSIFIED // SECURE ACCESS // GEN-AI
              </div>
            </div>
            <div className="h-px w-full bg-gradient-to-r from-transparent via-cyan-900/60 to-transparent" />
          </div>

          {/* Role quick-select */}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => fillCredentials("seller")}
              className="flex-1 flex flex-col items-center gap-1.5 p-3 border border-cyan-900/40 bg-cyan-950/10 hover:bg-cyan-950/30 hover:border-cyan-600/50 transition-all group"
            >
              <Package className="w-4 h-4 text-cyan-600 group-hover:text-cyan-400" />
              <span className="text-[9px] text-cyan-600 group-hover:text-cyan-400 uppercase tracking-widest font-bold">
                Seller
              </span>
              <span className="text-[8px] text-zinc-600 uppercase">Send Products</span>
            </button>
            <button
              type="button"
              onClick={() => fillCredentials("buyer")}
              className="flex-1 flex flex-col items-center gap-1.5 p-3 border border-purple-900/40 bg-purple-950/10 hover:bg-purple-950/30 hover:border-purple-600/50 transition-all group"
            >
              <ShoppingCart className="w-4 h-4 text-purple-600 group-hover:text-purple-400" />
              <span className="text-[9px] text-purple-600 group-hover:text-purple-400 uppercase tracking-widest font-bold">
                Buyer
              </span>
              <span className="text-[8px] text-zinc-600 uppercase">Receive Products</span>
            </button>
          </div>

          {/* Login form */}
          <form onSubmit={handleLogin} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-[9px] text-zinc-500 uppercase tracking-widest">
                User ID
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3 py-2 bg-black/60 border border-cyan-900/40 text-xs text-zinc-200 placeholder:text-zinc-700 focus:outline-none focus:border-cyan-500/60 transition-colors"
                placeholder="seller or buyer"
                autoComplete="username"
                required
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-[9px] text-zinc-500 uppercase tracking-widest">
                Access Code
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 bg-black/60 border border-cyan-900/40 text-xs text-zinc-200 placeholder:text-zinc-700 focus:outline-none focus:border-cyan-500/60 transition-colors"
                placeholder="••••••••••"
                autoComplete="current-password"
                required
              />
            </div>

            {error && (
              <div className="px-3 py-2 border border-red-900/50 bg-red-950/10 text-[10px] text-red-400 uppercase tracking-wide">
                ⚠ {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-cyan-600/20 border border-cyan-600/40 text-cyan-400 text-[10px] uppercase tracking-[0.3em] font-bold hover:bg-cyan-600/30 hover:border-cyan-500/60 transition-all disabled:opacity-50 flex items-center justify-center gap-2 mt-1"
            >
              {loading && <Loader2 className="w-3 h-3 animate-spin" />}
              {loading ? "Authenticating..." : "Authenticate"}
            </button>
          </form>

          {/* Demo credentials reminder */}
          <div className="border border-zinc-900/60 bg-zinc-950/30 p-3 flex flex-col gap-2">
            <div className="text-[8px] text-zinc-700 uppercase tracking-widest font-bold mb-1">
              Demo Credentials (click role cards above to autofill)
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-0.5">
                <div className="text-[8px] text-cyan-700 uppercase tracking-wide">Seller / Alice</div>
                <div className="text-[9px] text-zinc-500 font-mono">seller / seller123</div>
              </div>
              <div className="flex flex-col gap-0.5">
                <div className="text-[8px] text-purple-700 uppercase tracking-wide">Buyer / Bob</div>
                <div className="text-[9px] text-zinc-500 font-mono">buyer / buyer123</div>
              </div>
            </div>
          </div>

          <div className="text-[8px] text-zinc-800 uppercase tracking-widest text-center">
            © 2026 LogosGotham — Autonomous Logistics AI
          </div>
        </div>
      </div>
    </div>
  );
}
