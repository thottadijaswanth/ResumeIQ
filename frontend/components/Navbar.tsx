"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  FileText,
  Briefcase,
  BarChart3,
  CheckSquare,
  LogOut,
  Menu,
  X,
  Sparkles,
} from "lucide-react";
import { apiRequest, getUser, clearToken } from "@/lib/api";
import { AIHealthStatus, User } from "@/types";

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUserState] = useState<User | null>(null);
  const [aiHealth, setAiHealth] = useState<AIHealthStatus | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    setUserState(getUser());
  }, [pathname]);

  useEffect(() => {
    apiRequest<AIHealthStatus>("/ai/health")
      .then((data) => setAiHealth(data))
      .catch(() => setAiHealth(null));
  }, [pathname]);

  const handleLogout = () => {
    clearToken();
    setUserState(null);
    router.push("/login");
  };

  const navLinks = [
    { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
    { href: "/jobs", label: "Jobs & Screening", icon: Briefcase },
    { href: "/resumes", label: "Candidates", icon: FileText },
    { href: "/applications", label: "Pipeline", icon: CheckSquare },
  ];

  const isAuthPage = pathname === "/login" || pathname === "/register";

  const aiBadgeLabel = aiHealth
    ? `${aiHealth.mode === "local" ? "AI: Local" : aiHealth.mode === "cloud" ? "AI: Online" : "AI: Offline"}${
        aiHealth.model ? ` (${aiHealth.model})` : ""
      }`
    : "Screening Engine";

  const aiConnected = aiHealth?.available ?? aiHealth?.status === "healthy";

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          {/* Brand Logo */}
          <Link href={user ? "/dashboard" : "/"} className="flex items-center space-x-2.5">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-indigo-100">
              <Sparkles className="w-5 h-5" />
            </div>
            <div className="flex items-center">
              <span className="text-xl font-bold tracking-tight text-slate-900">
                Resume<span className="text-indigo-600">IQ</span>
              </span>
              <span
                className={`hidden sm:inline-flex items-center space-x-1.5 ml-2.5 text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${
                  aiHealth && !aiConnected
                    ? "bg-amber-50 text-amber-800 border-amber-200"
                    : "bg-indigo-50 text-indigo-700 border-indigo-200/70"
                }`}
                title={aiHealth?.message || aiBadgeLabel}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    aiHealth ? (aiConnected ? "bg-emerald-500" : "bg-amber-500") : "bg-indigo-500"
                  }`}
                />
                <span>{aiBadgeLabel}</span>
              </span>
            </div>
          </Link>

          {/* Desktop Navigation Links */}
          {user && (
            <nav className="hidden md:flex space-x-1">
              {navLinks.map((link) => {
                const Icon = link.icon;
                const isActive = pathname.startsWith(link.href);
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-indigo-50 text-indigo-700"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{link.label}</span>
                  </Link>
                );
              })}
            </nav>
          )}

          {/* User profile & Auth buttons */}
          <div className="hidden md:flex items-center space-x-3">
            {user ? (
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-2 bg-slate-50 px-3 py-1.5 rounded-full border border-slate-200">
                  <div className="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center text-xs font-bold">
                    {user.full_name ? user.full_name[0].toUpperCase() : "U"}
                  </div>
                  <span className="text-sm font-medium text-slate-700 max-w-[140px] truncate">
                    {user.full_name}
                  </span>
                </div>
                <button
                  onClick={handleLogout}
                  className="p-2 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                  title="Log out"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : !isAuthPage ? (
              <div className="flex items-center space-x-3">
                <Link
                  href="/login"
                  className="px-4 py-2 text-sm font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 rounded-lg transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  href="/register"
                  className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition-colors"
                >
                  Create Account
                </Link>
              </div>
            ) : null}
          </div>

          {/* Mobile menu button */}
          <div className="flex md:hidden items-center">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-slate-200 bg-white px-4 pt-2 pb-4 space-y-1">
          {user ? (
            <>
              <div className="px-3 py-2 border-b border-slate-100 mb-2">
                <p className="text-sm font-semibold text-slate-900">{user.full_name}</p>
                <p className="text-xs text-slate-500">{user.email}</p>
              </div>
              {navLinks.map((link) => {
                const Icon = link.icon;
                const isActive = pathname.startsWith(link.href);
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium ${
                      isActive ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{link.label}</span>
                  </Link>
                );
              })}
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  handleLogout();
                }}
                className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium text-rose-600 hover:bg-rose-50"
              >
                <LogOut className="w-4 h-4" />
                <span>Sign Out</span>
              </button>
            </>
          ) : (
            <div className="space-y-2 pt-2">
              <Link
                href="/login"
                onClick={() => setMobileMenuOpen(false)}
                className="block w-full text-center px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-lg"
              >
                Sign In
              </Link>
              <Link
                href="/register"
                onClick={() => setMobileMenuOpen(false)}
                className="block w-full text-center px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg"
              >
                Create Account
              </Link>
            </div>
          )}
        </div>
      )}
    </header>
  );
}
