import Link from "next/link";
import {
  Sparkles,
  ArrowRight,
  CheckCircle2,
  Cpu,
  Layers,
  ShieldCheck,
  Users,
  Briefcase,
} from "lucide-react";

export default function WorkspaceOverviewPage() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Recruiter Screening Overview */}
      <section className="relative overflow-hidden pt-16 pb-20 lg:pt-20 lg:pb-24 bg-gradient-to-b from-white via-indigo-50/20 to-slate-50 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full bg-indigo-50 border border-indigo-200/80 mb-6 shadow-sm">
              <Sparkles className="w-4 h-4 text-indigo-600" />
              <span className="text-xs font-semibold text-indigo-700">
                Internal Recruitment & Candidate Screening Platform
              </span>
            </div>
            <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 leading-tight">
              Screen Hundreds of Resumes Against{" "}
              <span className="text-indigo-600">One Job Profile</span>
            </h1>
            <p className="mt-6 text-lg text-slate-600 leading-relaxed max-w-2xl mx-auto">
              Create structured job requisitions, batch-upload 1 to 1,000+ PDF/DOCX resumes, apply deterministic filtering and semantic embeddings, and rerank top candidates with local Ollama or online AI.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row justify-center gap-4">
              <Link
                href="/jobs"
                className="inline-flex items-center justify-center px-6 py-3.5 text-base font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-lg shadow-indigo-100 transition-all group"
              >
                <span>Open Screening Workspace</span>
                <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link
                href="/login"
                className="inline-flex items-center justify-center px-6 py-3.5 text-base font-semibold text-slate-700 bg-white hover:bg-slate-50 rounded-xl border border-slate-200 shadow-sm transition-colors"
              >
                Recruiter Sign In
              </Link>
            </div>

            <div className="mt-12 grid grid-cols-2 sm:grid-cols-4 gap-4 text-center border-t border-slate-200/60 pt-8">
              <div>
                <p className="text-2xl font-bold text-slate-900">1 → 1000+</p>
                <p className="text-xs text-slate-500 mt-0.5">Batch Resume Upload</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">Cached</p>
                <p className="text-xs text-slate-500 mt-0.5">Profiles & Embeddings</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">Top-K AI</p>
                <p className="text-xs text-slate-500 mt-0.5">Targeted LLM Reranking</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">100%</p>
                <p className="text-xs text-slate-500 mt-0.5">Reproducible Scoring</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Candidate Ranking Preview */}
      <section className="py-16 bg-slate-50 border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-lg overflow-hidden">
            <div className="bg-slate-900 px-6 py-4 flex items-center justify-between text-white">
              <div className="flex items-center space-x-3">
                <Briefcase className="w-4 h-4 text-indigo-400" />
                <span className="text-xs font-mono text-slate-300">
                  Senior Java Backend Developer • Hyderabad, India • Hybrid • 4–7 yrs
                </span>
              </div>
              <span className="text-xs font-semibold px-2.5 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full">
                Multi-Stage Screening
              </span>
            </div>

            <div className="p-6 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500 uppercase tracking-wider">
                    <th className="py-2 pr-4">Rank</th>
                    <th className="py-2 pr-4">Candidate</th>
                    <th className="py-2 pr-4">Score</th>
                    <th className="py-2 pr-4">Experience</th>
                    <th className="py-2 pr-4">Matched Skills</th>
                    <th className="py-2 pr-4">Location</th>
                    <th className="py-2">Classification</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  <tr>
                    <td className="py-3 pr-4 font-bold text-slate-900">#1</td>
                    <td className="py-3 pr-4 font-semibold text-slate-900">Candidate 87</td>
                    <td className="py-3 pr-4 font-bold text-emerald-700">91%</td>
                    <td className="py-3 pr-4">5.2 yrs</td>
                    <td className="py-3 pr-4">Java, Spring Boot, SQL, AWS</td>
                    <td className="py-3 pr-4">Hyderabad</td>
                    <td className="py-3">
                      <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-semibold">
                        STRONG_MATCH
                      </span>
                    </td>
                  </tr>
                  <tr>
                    <td className="py-3 pr-4 font-bold text-slate-900">#2</td>
                    <td className="py-3 pr-4 font-semibold text-slate-900">Candidate 421</td>
                    <td className="py-3 pr-4 font-bold text-emerald-700">88%</td>
                    <td className="py-3 pr-4">6.0 yrs</td>
                    <td className="py-3 pr-4">Java, REST APIs, Docker</td>
                    <td className="py-3 pr-4">Bangalore</td>
                    <td className="py-3">
                      <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-semibold">
                        STRONG_MATCH
                      </span>
                    </td>
                  </tr>
                  <tr>
                    <td className="py-3 pr-4 font-bold text-slate-900">#3</td>
                    <td className="py-3 pr-4 font-semibold text-slate-900">Candidate 16</td>
                    <td className="py-3 pr-4 font-bold text-indigo-700">84%</td>
                    <td className="py-3 pr-4">4.5 yrs</td>
                    <td className="py-3 pr-4">Java, SQL, Docker</td>
                    <td className="py-3 pr-4">Hyderabad</td>
                    <td className="py-3">
                      <span className="px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 font-semibold">
                        GOOD_MATCH
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      {/* Architecture Pillars */}
      <section className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="p-6 bg-slate-50/70 rounded-2xl border border-slate-200/80">
              <div className="w-11 h-11 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center mb-4">
                <Layers className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900 mb-2">
                Fast Multi-Stage Filtering
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Hard filters, canonical skill matching, and cached 1536-dim embeddings shortlist top candidates in seconds before invoking LLM reasoning.
              </p>
            </div>

            <div className="p-6 bg-slate-50/70 rounded-2xl border border-slate-200/80">
              <div className="w-11 h-11 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center mb-4">
                <Cpu className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900 mb-2">
                Local Ollama & Online AI
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Run completely offline with local Qwen3 1.7B via Ollama or switch to an OpenAI-compatible API purely through environment variables.
              </p>
            </div>

            <div className="p-6 bg-slate-50/70 rounded-2xl border border-slate-200/80">
              <div className="w-11 h-11 rounded-xl bg-violet-100 text-violet-600 flex items-center justify-center mb-4">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900 mb-2">
                Evidence-Backed Rankings
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Every candidate match score cites matched requirements, experience gaps, and extracted resume evidence with zero invented credentials.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
