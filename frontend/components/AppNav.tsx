"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { api } from "@/lib/api";
import { useTheme } from "@/components/ThemeProvider";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/sessions", label: "Sessions" },
  { href: "/skills", label: "Skills" },
  { href: "/stories", label: "Stories" },
  { href: "/negotiation", label: "Negotiation" },
  { href: "/settings", label: "Settings" },
];

export function AppNav({ showBack }: { showBack?: boolean }) {
  const router = useRouter();
  const pathname = usePathname();
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { theme, toggle } = useTheme();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    api.auth.me()
      .then((u) => setUserEmail(u.email))
      .catch(() => {});
  }, []);

  function handleLogout() {
    localStorage.removeItem("access_token");
    router.push("/");
  }

  return (
    <>
      <nav className="glass border-b border-slate-200/60 dark:border-slate-700/60 px-4 sm:px-6 lg:px-8 xl:px-12 py-2.5 sticky top-0 z-50">
        <div className="w-full max-w-screen-2xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Mobile hamburger */}
            <button
              onClick={() => setMobileOpen(true)}
              className="sm:hidden p-2 text-slate-500 hover:text-slate-700 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
              aria-label="Open menu"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
            </button>

            {showBack && (
              <button
                onClick={() => router.back()}
                className="text-slate-400 hover:text-slate-700 transition-colors"
                aria-label="Go back"
              >
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 4l-6 6 6 6" />
                </svg>
              </button>
            )}

            <Link href="/dashboard" className="text-lg font-bold gradient-text">
              InterviewCraft
            </Link>

            <div className="hidden sm:flex items-center gap-0.5 ml-3">
              {NAV_ITEMS.map((item) => {
                const active = pathname === item.href || pathname.startsWith(item.href + "/");
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                      active
                        ? "bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 font-semibold"
                        : "text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <Link href="/sessions/new" className="btn-primary !py-2 !px-3 sm:!px-3.5 !text-sm !rounded-lg min-h-[44px] flex items-center">
              <span className="hidden sm:inline">+ New Session</span>
              <span className="sm:hidden">+ New</span>
            </Link>
            {userEmail && (
              <span className="hidden lg:inline text-xs text-slate-400 max-w-[140px] truncate" title={userEmail}>
                {userEmail}
              </span>
            )}
            {/* Dark mode toggle */}
            <button
              onClick={toggle}
              aria-label="Toggle dark mode"
              className="p-2 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
            >
              {theme === "dark" ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
                  <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                  <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
                  <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
                </svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                </svg>
              )}
            </button>
            <button
              onClick={handleLogout}
              className="px-3 py-2 text-sm text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/50 rounded-lg transition-colors min-h-[44px]"
            >
              Log out
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-[60] sm:hidden">
          <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <div className="absolute left-0 top-0 bottom-0 w-[min(256px,85vw)] bg-white dark:bg-slate-900 shadow-2xl p-5 animate-slide-up">
            <div className="flex items-center justify-between mb-6">
              <span className="text-lg font-bold gradient-text">InterviewCraft</span>
              <button onClick={() => setMobileOpen(false)} className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
              </button>
            </div>
            <div className="space-y-1">
              {NAV_ITEMS.map((item) => {
                const active = pathname === item.href || pathname.startsWith(item.href + "/");
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                    className={`block px-3 py-2.5 rounded-xl text-sm transition-colors ${
                      active
                        ? "bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 font-semibold"
                        : "text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </div>
            <div className="mt-6 pt-6 border-t border-slate-100 dark:border-slate-700">
              {userEmail && <p className="text-xs text-slate-400 mb-3 truncate">{userEmail}</p>}
              <button onClick={handleLogout} className="text-sm text-red-500 hover:text-red-700 min-h-[44px] px-1">Log out</button>
              <div className="flex gap-4 mt-4">
                <Link href="/tos" onClick={() => setMobileOpen(false)} className="text-xs text-slate-400 hover:text-slate-600 hover:underline">Terms</Link>
                <Link href="/privacy" onClick={() => setMobileOpen(false)} className="text-xs text-slate-400 hover:text-slate-600 hover:underline">Privacy</Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
