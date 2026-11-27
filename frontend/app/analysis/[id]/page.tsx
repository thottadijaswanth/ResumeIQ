"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  TrendingUp,
  FileText,
  Briefcase,
  Copy,
  Check,
  Download,
  Layers,
  ArrowLeft,
  Loader2,
  AlertCircle,
  HelpCircle,
  Edit3,
  Bookmark,
} from "lucide-react";
import { apiRequest, getToken } from "@/lib/api";
import {
  Analysis,
  Resume,
  Job,
  TailorResumeResponse,
  CoverLetterResponse,
} from "@/types";
import ScoreGauge from "@/components/ScoreGauge";
import { getScoreColor } from "@/lib/utils";

export default function AnalysisDetailPage() {
  const params = useParams();
  const router = useRouter();
  const analysisId = params?.id as string;

  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [resume, setResume] = useState<Resume | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Active Tab
  const [activeTab, setActiveTab] = useState<
    "overview" | "skills" | "ats" | "recommendations" | "evidence" | "tailor" | "cover_letter"
  >("overview");

  // Tailored Resume state
  const [tailoredResume, setTailoredResume] = useState<TailorResumeResponse | null>(null);
  const [loadingTailor, setLoadingTailor] = useState(false);

  // Cover Letter state
  const [coverLetter, setCoverLetter] = useState<CoverLetterResponse | null>(null);
  const [loadingCover, setLoadingCover] = useState(false);
  const [coverTone, setCoverTone] = useState("Professional");
  const [coverNotes, setCoverNotes] = useState("");
  const [copiedCover, setCopiedCover] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }

    async function loadAnalysis() {
      try {
        const data = await apiRequest<Analysis>(`/analysis/${analysisId}`);
        setAnalysis(data);

        // Fetch related resume and job
        const [rData, jData] = await Promise.all([
          apiRequest<Resume>(`/resumes/${data.resume_id}`),
          apiRequest<Job>(`/jobs/${data.job_id}`),
        ]);
        setResume(rData);
        setJob(jData);
      } catch (err: any) {
        setError(err.message || "Failed to load analysis report.");
      } finally {
        setLoading(false);
      }
    }

    if (analysisId) {
      loadAnalysis();
    }
  }, [analysisId, router]);

  const handleGenerateTailored = async () => {
    setLoadingTailor(true);
    try {
      const data = await apiRequest<TailorResumeResponse>(
        `/analysis/${analysisId}/tailor-resume`,
        { method: "POST" }
      );
      setTailoredResume(data);
    } catch (err: any) {
      alert("Error generating tailored resume: " + err.message);
    } finally {
      setLoadingTailor(false);
    }
  };

  const handleGenerateCover = async () => {
    setLoadingCover(true);
    try {
      const data = await apiRequest<CoverLetterResponse>(
        `/analysis/${analysisId}/cover-letter`,
        {
          method: "POST",
          body: JSON.stringify({
            tone: coverTone,
            custom_notes: coverNotes || undefined,
          }),
        }
      );
      setCoverLetter(data);
    } catch (err: any) {
      alert("Error generating cover letter: " + err.message);
    } finally {
      setLoadingCover(false);
    }
  };

  const handleCopyCoverLetter = () => {
    if (!coverLetter) return;
    navigator.clipboard.writeText(coverLetter.cover_letter_text);
    setCopiedCover(true);
    setTimeout(() => setCopiedCover(false), 2000);
  };

  const handleAddToTracker = async () => {
    if (!analysis || !job) return;
    try {
      await apiRequest("/applications", {
        method: "POST",
        body: JSON.stringify({
          job_id: job.id,
          resume_id: analysis.resume_id,
          status: "Saved",
          notes: `Matched with ${Math.round(analysis.overall_score)}% score on ${new Date().toLocaleDateString()}`,
        }),
      });
      alert(`Job "${job.title}" added to your application pipeline!`);
    } catch (err: any) {
      alert("Error saving to applications: " + err.message);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center space-y-3">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
        <p className="text-sm text-slate-500 font-medium">Loading match report...</p>
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="max-w-xl mx-auto my-16 p-8 bg-white rounded-2xl border border-rose-200 text-center space-y-4">
        <AlertCircle className="w-10 h-10 text-rose-600 mx-auto" />
        <h2 className="text-lg font-bold text-slate-900">Analysis Not Found</h2>
        <p className="text-xs text-slate-500">{error || "Could not retrieve the requested analysis."}</p>
        <Link
          href="/dashboard"
          className="inline-flex items-center space-x-2 text-xs font-semibold text-indigo-600 hover:underline"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Return to Dashboard</span>
        </Link>
      </div>
    );
  }

  const result = analysis.analysis_result;
  const overallColor = getScoreColor(analysis.overall_score);

  const tabs = [
    { id: "overview", label: "Overview & Scores" },
    { id: "skills", label: `Skills (${result.matching_skills.length} match)` },
    { id: "ats", label: "ATS Compatibility" },
    { id: "recommendations", label: `Recommendations (${analysis.recommendations.length})` },
    { id: "evidence", label: "Evidence Citations" },
    { id: "tailor", label: "Tailor Resume" },
    { id: "cover_letter", label: "Cover Letter" },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Back button & Role header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="space-y-1">
          <Link
            href="/dashboard"
            className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors mb-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Dashboard</span>
          </Link>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              {job?.title || "Target Position"}
            </h1>
            <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
              {job?.company || "Target Company"}
            </span>
          </div>
          <p className="text-xs text-slate-500">
            Candidate Resume: <strong className="text-slate-700">{resume?.name}</strong> • Analyzed on{" "}
            {new Date(analysis.created_at).toLocaleDateString()}
          </p>
        </div>

        <button
          onClick={handleAddToTracker}
          className="inline-flex items-center space-x-1.5 px-4 py-2 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-xl transition-colors shadow-sm"
        >
          <Bookmark className="w-4 h-4" />
          <span>Save to Application Tracker</span>
        </button>
      </div>

      {/* Top Score Banner Card */}
      <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-8 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 items-center">
          {/* Radial Gauge */}
          <div className="flex justify-center md:border-r md:border-slate-100 pr-0 md:pr-4">
            <ScoreGauge
              score={analysis.overall_score}
              size={170}
              strokeWidth={13}
              label="Overall Match"
              sublabel="Deterministic 5-pillar composite score"
            />
          </div>

          {/* 5-Pillar Score Breakdown */}
          <div className="md:col-span-3 space-y-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                Scoring Engine Breakdown
              </h3>
              <p className="text-xs text-slate-500">
                Calculated according to configured mathematical weights
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {[
                { label: "Skills (35%)", score: analysis.skill_score, hint: `${result.matching_skills.length} matched` },
                { label: "Experience (20%)", score: analysis.experience_score, hint: result.experience_gap_analysis.role_level_match },
                { label: "Semantic (20%)", score: analysis.semantic_score, hint: "Cosine vector sim" },
                { label: "Keywords (15%)", score: analysis.keyword_score, hint: `${result.ats_analysis.keyword_coverage_percent}% coverage` },
                { label: "Education (10%)", score: analysis.education_score, hint: "Degree match" },
              ].map((item, idx) => {
                const c = getScoreColor(item.score);
                return (
                  <div key={idx} className="p-3 bg-slate-50 rounded-xl border border-slate-200/80">
                    <span className="text-[11px] font-semibold text-slate-500 block truncate">
                      {item.label}
                    </span>
                    <p className={`text-xl font-extrabold mt-1 ${c.text}`}>
                      {Math.round(item.score)}%
                    </p>
                    <span className="text-[10px] text-slate-400 block truncate mt-0.5">
                      {item.hint}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-slate-200 overflow-x-auto">
        <nav className="flex space-x-2 pb-1">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-4 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-colors ${
                  isActive
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* TAB CONTENT */}

      {/* 1. Overview */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Left: Key Findings Summary */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-indigo-600" />
              <span>Executive Match Summary</span>
            </h3>
            <p className="text-sm text-slate-700 leading-relaxed">
              Your resume demonstrates an estimated <strong>{Math.round(analysis.overall_score)}% compatibility</strong> with the {job?.title} role at {job?.company}.
            </p>
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 text-xs text-slate-600 space-y-2">
              <p>
                <strong>Skills:</strong> You match {result.matching_skills.length} core technical requirements. {result.missing_required_skills.length > 0 && `${result.missing_required_skills.length} required skill(s) are not clearly found.`}
              </p>
              <p>
                <strong>Experience:</strong> {result.experience_gap_analysis.details}
              </p>
              <p>
                <strong>ATS Compatibility:</strong> {result.ats_analysis.summary}
              </p>
            </div>
          </div>

          {/* Right: Quick Actionable Items */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              <span>Priority Action Items</span>
            </h3>
            <div className="space-y-3">
              {analysis.recommendations.slice(0, 3).map((rec, idx) => (
                <div key={idx} className="p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900">{rec.issue}</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        rec.severity === "Critical"
                          ? "bg-rose-100 text-rose-800"
                          : rec.severity === "High"
                          ? "bg-amber-100 text-amber-800"
                          : "bg-indigo-100 text-indigo-800"
                      }`}
                    >
                      {rec.severity}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">{rec.suggested_action}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 2. Skills Analysis */}
      {activeTab === "skills" && (
        <div className="space-y-6">
          {/* Matching Skills */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                <span>Matching Skills ({result.matching_skills.length})</span>
              </h3>
              <span className="text-xs text-slate-500">Validated against resume text</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {result.matching_skills.map((item, idx) => (
                <div
                  key={idx}
                  className="p-3.5 bg-emerald-50/40 rounded-xl border border-emerald-100 space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-slate-900">{item.skill}</span>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                      {item.category}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 italic leading-relaxed">
                    Evidence: {item.evidence}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Missing Skills Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Missing Required Skills */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                <XCircle className="w-4 h-4 text-rose-600" />
                <span>Missing Required Skills ({result.missing_required_skills.length})</span>
              </h3>
              {result.missing_required_skills.length === 0 ? (
                <p className="text-xs text-emerald-600 font-medium">
                  ✓ Outstanding! All core required skills are present on your resume.
                </p>
              ) : (
                <div className="space-y-3">
                  {result.missing_required_skills.map((item, idx) => (
                    <div key={idx} className="p-3 bg-rose-50/50 rounded-xl border border-rose-100 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-rose-900">{item.skill}</span>
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-100 text-rose-800">
                          Required
                        </span>
                      </div>
                      <p className="text-xs text-slate-600">{item.suggestion}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Missing Preferred Skills */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                <span>Missing Preferred Skills ({result.missing_preferred_skills.length})</span>
              </h3>
              {result.missing_preferred_skills.length === 0 ? (
                <p className="text-xs text-emerald-600 font-medium">
                  ✓ All preferred skills are covered!
                </p>
              ) : (
                <div className="space-y-3">
                  {result.missing_preferred_skills.map((item, idx) => (
                    <div key={idx} className="p-3 bg-amber-50/50 rounded-xl border border-amber-100 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-amber-900">{item.skill}</span>
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-100 text-amber-800">
                          Preferred
                        </span>
                      </div>
                      <p className="text-xs text-slate-600">{item.suggestion}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 3. ATS Compatibility */}
      {activeTab === "ats" && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6">
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-2 border-b border-slate-100 pb-4">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  ATS Scanner Compatibility Audit
                </h3>
                <p className="text-xs text-slate-500">
                  Heuristic analysis based on Applicant Tracking System parsing algorithms
                </p>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-semibold text-slate-500">Estimated Score:</span>
                <span className="text-lg font-extrabold text-indigo-600">
                  {result.ats_analysis.estimated_ats_score}%
                </span>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-xs text-slate-500 block">Keyword Coverage</span>
                <p className="text-xl font-bold text-slate-900 mt-1">
                  {result.ats_analysis.keyword_coverage_percent}%
                </p>
              </div>
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-xs text-slate-500 block">Quantifiable Metrics</span>
                <p className="text-xl font-bold text-slate-900 mt-1">
                  {result.ats_analysis.quantifiable_achievements_count} found
                </p>
              </div>
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-xs text-slate-500 block">Action Verbs</span>
                <p className="text-xl font-bold text-slate-900 mt-1">
                  {result.ats_analysis.action_verbs_count} distinct
                </p>
              </div>
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-xs text-slate-500 block">Keyword Stuffing</span>
                <p className="text-xl font-bold text-slate-900 mt-1">
                  {result.ats_analysis.keyword_stuffing_detected ? "Detected ⚠️" : "Clean ✓"}
                </p>
              </div>
            </div>

            {/* Section Completeness */}
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
                Standard Section Checklist
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                {Object.entries(result.ats_analysis.section_completeness).map(([sec, isComplete]) => (
                  <div
                    key={sec}
                    className={`flex items-center space-x-2 p-2.5 rounded-lg border text-xs font-medium ${
                      isComplete
                        ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                        : "bg-rose-50 text-rose-800 border-rose-200"
                    }`}
                  >
                    {isComplete ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    ) : (
                      <XCircle className="w-4 h-4 text-rose-600" />
                    )}
                    <span>{sec}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Formatting risks if any */}
            {result.ats_analysis.formatting_risks.length > 0 && (
              <div className="p-4 bg-amber-50 rounded-xl border border-amber-200 space-y-2">
                <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wider flex items-center space-x-1.5">
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                  <span>Formatting & Parsing Risks</span>
                </h4>
                <ul className="list-disc list-inside text-xs text-amber-800 space-y-1">
                  {result.ats_analysis.formatting_risks.map((risk, idx) => (
                    <li key={idx}>{risk}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 4. Recommendations */}
      {activeTab === "recommendations" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-slate-900">
              Categorized Actionable Recommendations
            </h3>
            <span className="text-xs text-slate-500">
              Ranked by impact on interview screening
            </span>
          </div>

          <div className="space-y-3">
            {analysis.recommendations.map((rec, idx) => {
              const isCrit = rec.severity === "Critical";
              const isHigh = rec.severity === "High";

              return (
                <div
                  key={idx}
                  className={`bg-white p-5 rounded-2xl border shadow-sm space-y-2.5 ${
                    isCrit ? "border-rose-200" : isHigh ? "border-amber-200" : "border-slate-200"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span
                        className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                          isCrit
                            ? "bg-rose-100 text-rose-800"
                            : isHigh
                            ? "bg-amber-100 text-amber-800"
                            : "bg-indigo-100 text-indigo-800"
                        }`}
                      >
                        {rec.severity} Severity
                      </span>
                      <span className="text-xs text-slate-400 font-medium">• {rec.category}</span>
                    </div>
                    <span className="text-xs text-slate-400 italic">{rec.related_requirement}</span>
                  </div>

                  <h4 className="text-sm font-bold text-slate-900">{rec.issue}</h4>
                  <p className="text-xs text-slate-600 leading-relaxed">{rec.explanation}</p>
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-xs text-indigo-900 font-medium">
                    <strong>Suggested Action:</strong> {rec.suggested_action}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 5. Evidence Citations */}
      {activeTab === "evidence" && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Job Requirements vs Resume Evidence
              </h3>
              <p className="text-xs text-slate-500">
                Examine exactly why each requirement was deemed a Strong Match, Partial Match, or Not Found.
              </p>
            </div>
          </div>

          <div className="divide-y divide-slate-100">
            {result.requirements_evidence.map((item, idx) => {
              const isStrong = item.match_status === "Strong match";
              const isPartial = item.match_status === "Partial match";

              return (
                <div key={idx} className="py-4 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-slate-900">{item.requirement}</p>
                    <span
                      className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                        isStrong
                          ? "bg-emerald-100 text-emerald-800"
                          : isPartial
                          ? "bg-amber-100 text-amber-800"
                          : "bg-rose-100 text-rose-800"
                      }`}
                    >
                      {item.match_status} ({Math.round(item.confidence * 100)}%)
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-100 font-mono">
                    {item.evidence}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 6. Tailor Resume */}
      {activeTab === "tailor" && (
        <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 border-b border-slate-100 pb-4">
            <div>
              <h3 className="text-lg font-bold text-slate-900">
                AI Resume Tailoring Engine
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Reorder skills and rephrase bullet points strictly from your existing experience. Zero hallucination guaranteed.
              </p>
            </div>
            {!tailoredResume && (
              <button
                onClick={handleGenerateTailored}
                disabled={loadingTailor}
                className="inline-flex items-center space-x-2 px-5 py-2.5 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-xl shadow-sm transition-all"
              >
                {loadingTailor ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Generate Tailored Version</span>
                  </>
                )}
              </button>
            )}
          </div>

          {tailoredResume ? (
            <div className="space-y-6">
              {/* Tailored Summary */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Targeted Professional Summary
                </h4>
                <div className="p-4 bg-indigo-50/50 rounded-xl border border-indigo-100 text-sm text-slate-800 leading-relaxed">
                  {tailoredResume.tailored_summary}
                </div>
              </div>

              {/* Reordered Skills */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Optimized Skill Hierarchy (Matching items surfaced first)
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {tailoredResume.suggested_reordered_skills.map((skill, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 text-xs font-medium rounded-lg bg-slate-100 text-slate-800 border border-slate-200"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              {/* Enhanced Bullet Points */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Tailored Work Experience Bullets
                </h4>
                {tailoredResume.tailored_experience.map((exp, idx) => (
                  <div key={idx} className="p-4 bg-slate-50 rounded-xl border border-slate-100 space-y-2">
                    <p className="text-sm font-bold text-slate-900">
                      {exp.role} — {exp.company}
                    </p>
                    <ul className="list-disc list-inside text-xs text-slate-700 space-y-1">
                      {exp.responsibilities.map((r, rIdx) => (
                        <li key={rIdx}>{r}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>

              {/* Notes */}
              <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-200 text-xs text-emerald-800 space-y-1">
                <p className="font-bold">Integrity Notice:</p>
                <ul className="list-disc list-inside space-y-0.5">
                  {tailoredResume.notes.map((n, idx) => (
                    <li key={idx}>{n}</li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto">
                <Edit3 className="w-6 h-6" />
              </div>
              <h4 className="text-sm font-bold text-slate-900">
                Ready to Generate Tailored Resume
              </h4>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Click "Generate Tailored Version" above to align your bullet points and skills directly with {job?.title}.
              </p>
            </div>
          )}
        </div>
      )}

      {/* 7. Cover Letter */}
      {activeTab === "cover_letter" && (
        <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 border-b border-slate-100 pb-4">
            <div>
              <h3 className="text-lg font-bold text-slate-900">
                Job-Specific Cover Letter Generator
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Ties your real accomplishments directly to {job?.company}'s engineering objectives.
              </p>
            </div>
            <div className="flex items-center space-x-3">
              <select
                value={coverTone}
                onChange={(e) => setCoverTone(e.target.value)}
                className="text-xs font-semibold px-3 py-2 rounded-xl border border-slate-300 bg-white"
              >
                <option value="Professional">Tone: Professional</option>
                <option value="Confident">Tone: Confident</option>
                <option value="Enthusiastic">Tone: Enthusiastic</option>
              </select>
              <button
                onClick={handleGenerateCover}
                disabled={loadingCover}
                className="inline-flex items-center space-x-2 px-4 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-xl shadow-sm transition-all"
              >
                {loadingCover ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Generate Letter</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {coverLetter ? (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <div className="flex flex-wrap gap-1.5">
                  {coverLetter.key_points_highlighted.map((point, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 text-[11px] font-medium rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/60"
                    >
                      ✓ {point}
                    </span>
                  ))}
                </div>
                <button
                  onClick={handleCopyCoverLetter}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                >
                  {copiedCover ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedCover ? "Copied!" : "Copy to Clipboard"}</span>
                </button>
              </div>

              <textarea
                rows={16}
                value={coverLetter.cover_letter_text}
                onChange={(e) =>
                  setCoverLetter({ ...coverLetter, cover_letter_text: e.target.value })
                }
                className="w-full p-5 text-xs font-sans leading-relaxed rounded-2xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 text-slate-800 bg-slate-50/50"
              />
            </div>
          ) : (
            <div className="text-center py-12 space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto">
                <FileText className="w-6 h-6" />
              </div>
              <h4 className="text-sm font-bold text-slate-900">
                No Cover Letter Generated Yet
              </h4>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Select your preferred tone and click "Generate Letter" above.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

