"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  FileText,
  Briefcase,
  BarChart3,
  CheckSquare,
  ArrowRight,
  Plus,
  Sparkles,
  TrendingUp,
  Clock,
  ChevronRight,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { apiRequest, getToken } from "@/lib/api";
import { AIHealthStatus, Analysis, Application, ResumeSummary, JobSummary } from "@/types";
import { getScoreColor } from "@/lib/utils";

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [resumes, setResumes] = useState<ResumeSummary[]>([]);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [aiHealth, setAiHealth] = useState<AIHealthStatus | null>(null);
  const [switchingAi, setSwitchingAi] = useState(false);
  const [appStats, setAppStats] = useState<{ total_applications: number; status_breakdown: Record<string, number> }>({
    total_applications: 0,
    status_breakdown: { Saved: 0, Applied: 0, Interview: 0, Offer: 0, Rejected: 0 },
  });

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }

    async function loadDashboard() {
      try {
        const [resumesData, jobsData, analysesData, statsData, aiHealthData] = await Promise.all([
          apiRequest<ResumeSummary[]>("/resumes"),
          apiRequest<JobSummary[]>("/jobs"),
          apiRequest<Analysis[]>("/analysis"),
          apiRequest<any>("/applications/stats/summary").catch(() => ({ total_applications: 0, status_breakdown: {} })),
          apiRequest<AIHealthStatus>("/ai/health").catch(() => null),
        ]);

        setResumes(resumesData);
        setJobs(jobsData);
        setAnalyses(analysesData);
        setAppStats(statsData);
        setAiHealth(aiHealthData);
      } catch (err) {
        console.error("Dashboard data load error:", err);
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, [router]);

  const handleSwitchAiMode = async (mode: "auto" | "ollama" | "openai") => {
    setSwitchingAi(true);
    try {
      const updated = await apiRequest<AIHealthStatus>("/ai/mode", {
        method: "POST",
        body: JSON.stringify({ provider: mode }),
      });
      setAiHealth(updated);
    } catch (err) {
      console.error("Failed to switch AI mode:", err);
    } finally {
      setSwitchingAi(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center space-y-3">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
        <p className="text-sm text-slate-500 font-medium">Loading your workspace...</p>
      </div>
    );
  }

  const avgMatchScore =
    analyses.length > 0
      ? Math.round(analyses.reduce((acc, curr) => acc + curr.overall_score, 0) / analyses.length)
      : null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Welcome header & Quick actions */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200/80 pb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Recruitment Screening Dashboard
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Create job requisitions, bulk-screen candidate resumes, and inspect ranked shortlists.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Link
            href="/resumes"
            className="inline-flex items-center space-x-2 px-4 py-2 text-sm font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-xl transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4 text-slate-500" />
            <span>Bulk Upload Resumes</span>
          </Link>
          <Link
            href="/jobs"
            className="inline-flex items-center space-x-2 px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Create Job & Screen</span>
          </Link>
        </div>
      </div>

      {/* KPI Stats cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Resumes</span>
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-slate-900">{resumes.length}</p>
          <span className="text-xs text-slate-500 mt-1 inline-block">Parsed & indexed</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Jobs Added</span>
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
              <Briefcase className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-slate-900">{jobs.length}</p>
          <span className="text-xs text-slate-500 mt-1 inline-block">Requirement profiles</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Analyses</span>
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
              <BarChart3 className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-slate-900">{analyses.length}</p>
          <span className="text-xs text-slate-500 mt-1 inline-block">
            {avgMatchScore !== null ? `Avg score: ${avgMatchScore}%` : "No comparisons yet"}
          </span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Tracked Apps</span>
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
              <CheckSquare className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-slate-900">{appStats.total_applications}</p>
          <span className="text-xs text-slate-500 mt-1 inline-block">
            {appStats.status_breakdown["Interview"] || 0} active interviews
          </span>
        </div>
      </div>

      {/* Main Grid: Recent Analyses & Applications */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Cols: Recent Match Analyses */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900 flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-indigo-600" />
              <span>Recent Match Analyses</span>
            </h2>
            {analyses.length > 0 && (
              <span className="text-xs text-slate-500">{analyses.length} total reports</span>
            )}
          </div>

          {analyses.length === 0 ? (
            <div className="bg-white p-8 rounded-2xl border border-dashed border-slate-300 text-center space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto">
                <BarChart3 className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-bold text-slate-900">No Match Analyses Yet</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Upload your resume and create a job description to trigger your first comprehensive scoring report.
              </p>
              <div className="pt-2">
                <Link
                  href="/jobs"
                  className="inline-flex items-center space-x-2 text-xs font-semibold text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg transition-colors"
                >
                  <span>Start New Analysis</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm divide-y divide-slate-100">
              {analyses.slice(0, 5).map((a) => {
                const color = getScoreColor(a.overall_score);
                const relatedJob = jobs.find((j) => j.id === a.job_id);
                const relatedResume = resumes.find((r) => r.id === a.resume_id);

                return (
                  <Link
                    key={a.id}
                    href={`/analysis/${a.id}`}
                    className="flex items-center justify-between p-4 hover:bg-slate-50/80 transition-colors group"
                  >
                    <div className="flex items-center space-x-4 min-w-0">
                      <div
                        className={`w-12 h-12 rounded-xl flex items-center justify-center font-extrabold text-sm border ${color.bg} ${color.text} ${color.border}`}
                      >
                        {Math.round(a.overall_score)}%
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-bold text-slate-900 group-hover:text-indigo-600 transition-colors truncate">
                          {relatedJob ? relatedJob.title : "Target Role"}
                        </p>
                        <p className="text-xs text-slate-500 truncate">
                          {relatedJob?.company || "Company"} • Resume:{" "}
                          {relatedResume?.name || "Candidate Resume"}
                        </p>
                        <div className="flex items-center space-x-3 text-[11px] text-slate-400 mt-1">
                          <span>Skills: {Math.round(a.skill_score)}%</span>
                          <span>•</span>
                          <span>Experience: {Math.round(a.experience_score)}%</span>
                          <span>•</span>
                          <span>Semantic: {Math.round(a.semantic_score)}%</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className="text-xs text-slate-400 hidden sm:inline-block">
                        {new Date(a.created_at).toLocaleDateString()}
                      </span>
                      <ChevronRight className="w-4 h-4 text-slate-400 group-hover:translate-x-0.5 transition-transform" />
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>

        {/* Right 1 Col: Quick Links, AI Status & Application Pipeline */}
        <div className="space-y-6">
          {/* AI Engine Status Card */}
          {aiHealth && (
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                  <Sparkles className="w-4 h-4 text-indigo-600" />
                  <span>AI Engine</span>
                </h3>
                <span
                  className={`inline-flex items-center space-x-1.5 text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${
                    aiHealth.status === "healthy"
                      ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                      : "bg-amber-50 text-amber-700 border border-amber-200"
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      aiHealth.status === "healthy" ? "bg-emerald-500" : "bg-amber-500"
                    }`}
                  />
                  <span>{aiHealth.status === "healthy" ? "Connected" : "Unavailable"}</span>
                </span>
              </div>

              <div className="space-y-1 text-xs">
                <p className="font-semibold text-slate-800">
                  {aiHealth.mode === "local"
                    ? "AI: Local (Ollama)"
                    : aiHealth.mode === "cloud"
                    ? "AI: Online (OpenAI-compatible API)"
                    : "AI: Offline NLP (Mock)"}
                </p>
                {aiHealth.model && (
                  <p className="text-slate-500">
                    Model: <span className="font-mono text-slate-700">{aiHealth.model}</span>
                  </p>
                )}
                <p className="text-slate-500">
                  Embeddings: <span className="font-medium text-slate-700">{aiHealth.embedding_provider}</span>
                </p>
                {aiHealth.status !== "healthy" && aiHealth.message && (
                  <p className="text-[11px] text-amber-700 bg-amber-50/70 rounded-lg p-2 mt-1">
                    {aiHealth.mode === "local" ? `Ollama unavailable: ${aiHealth.message}` : aiHealth.message}
                  </p>
                )}
              </div>

              <div className="pt-2 border-t border-slate-100">
                <p className="text-[11px] font-semibold text-slate-500 mb-1.5">AI Mode</p>
                <div className="grid grid-cols-3 gap-1.5 text-[11px] font-semibold">
                  {(
                    [
                      { key: "auto", label: "Auto" },
                      { key: "ollama", label: "Local" },
                      { key: "openai", label: "Online" },
                    ] as const
                  ).map((opt) => {
                    const active = (aiHealth.configured_provider || aiHealth.provider) === opt.key;
                    return (
                      <button
                        key={opt.key}
                        type="button"
                        disabled={switchingAi}
                        onClick={() => handleSwitchAiMode(opt.key)}
                        className={`py-1.5 rounded-lg border transition-colors ${
                          active
                            ? "bg-indigo-600 text-white border-indigo-600"
                            : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                        }`}
                      >
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Application Pipeline Overview */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                <CheckSquare className="w-4 h-4 text-indigo-600" />
                <span>Application Pipeline</span>
              </h3>
              <Link
                href="/applications"
                className="text-xs font-semibold text-indigo-600 hover:underline"
              >
                View Board
              </Link>
            </div>

            <div className="space-y-2.5">
              {[
                { label: "Saved", count: appStats.status_breakdown["Saved"] || 0, color: "bg-slate-100 text-slate-700" },
                { label: "Applied", count: appStats.status_breakdown["Applied"] || 0, color: "bg-blue-100 text-blue-700" },
                { label: "Interview", count: appStats.status_breakdown["Interview"] || 0, color: "bg-amber-100 text-amber-800" },
                { label: "Offer", count: appStats.status_breakdown["Offer"] || 0, color: "bg-emerald-100 text-emerald-800" },
                { label: "Rejected", count: appStats.status_breakdown["Rejected"] || 0, color: "bg-rose-100 text-rose-700" },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between text-xs py-1">
                  <span className="text-slate-600 font-medium">{item.label}</span>
                  <span className={`px-2 py-0.5 rounded-full font-bold ${item.color}`}>
                    {item.count}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Upload Helper Card */}
          <div className="bg-gradient-to-tr from-indigo-50 to-white p-6 rounded-2xl border border-indigo-100 shadow-sm space-y-3">
            <div className="flex items-center space-x-2 text-indigo-700 font-bold text-sm">
              <Sparkles className="w-4 h-4" />
              <span>Pro Tip: ATS Optimization</span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Resumes that include 3+ quantifiable metrics (percentages, latency reductions, user counts) average a <strong>24% higher ATS score</strong> than purely narrative bullet points.
            </p>
            <div className="pt-1">
              <Link
                href="/resumes"
                className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 inline-flex items-center space-x-1"
              >
                <span>Check your resume ATS score</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

