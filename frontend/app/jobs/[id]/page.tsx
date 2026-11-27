"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  AlertCircle,
  CheckCircle2,
  Clock,
  ExternalLink,
  Filter,
  Loader2,
  MapPin,
  Play,
  Sparkles,
  Users,
  X,
  AlertTriangle,
} from "lucide-react";
import { apiRequest, getToken } from "@/lib/api";
import {
  CandidateDetailResponse,
  CandidateRankItem,
  Job,
  ResumeSummary,
  ScreeningRunResponse,
} from "@/types";
import BulkResumeUploader from "@/components/BulkResumeUploader";

const CLASSIFICATION_STYLES: Record<string, string> = {
  STRONG_MATCH: "bg-emerald-50 text-emerald-700 border-emerald-200",
  GOOD_MATCH: "bg-indigo-50 text-indigo-700 border-indigo-200",
  PARTIAL_MATCH: "bg-amber-50 text-amber-800 border-amber-200",
  WEAK_MATCH: "bg-rose-50 text-rose-700 border-rose-200",
};

export default function JobScreeningWorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params?.id as string;

  const [job, setJob] = useState<Job | null>(null);
  const [poolCount, setPoolCount] = useState<number>(0);
  const [screeningRun, setScreeningRun] = useState<ScreeningRunResponse | null>(null);
  const [candidates, setCandidates] = useState<CandidateRankItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [startingScreen, setStartingScreen] = useState(false);
  const [useAiRerank, setUseAiRerank] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & sorting
  const [minScore, setMinScore] = useState<string>("");
  const [minExperience, setMinExperience] = useState<string>("");
  const [locationFilter, setLocationFilter] = useState<string>("");
  const [skillFilter, setSkillFilter] = useState<string>("");
  const [classificationFilter, setClassificationFilter] = useState<string>("");
  const [sortBy, setSortBy] = useState<string>("score_desc");

  // Selected Candidate Detail modal
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateDetailResponse | null>(null);
  const [loadingCandidate, setLoadingCandidate] = useState(false);

  const loadCandidates = useCallback(async () => {
    if (!jobId) return;
    const query = new URLSearchParams();
    if (minScore !== "") query.set("min_score", minScore);
    if (minExperience !== "") query.set("min_experience", minExperience);
    if (locationFilter.trim()) query.set("location", locationFilter.trim());
    if (skillFilter.trim()) query.set("required_skill", skillFilter.trim());
    if (classificationFilter) query.set("classification", classificationFilter);
    query.set("sort_by", sortBy);
    query.set("limit", "500");

    const rows = await apiRequest<CandidateRankItem[]>(
      `/jobs/${jobId}/candidates?${query.toString()}`
    );
    setCandidates(rows);
  }, [
    jobId,
    minScore,
    minExperience,
    locationFilter,
    skillFilter,
    classificationFilter,
    sortBy,
  ]);

  const loadInitial = useCallback(async () => {
    try {
      const [jobData, resumesData, latestRun] = await Promise.all([
        apiRequest<Job>(`/jobs/${jobId}`),
        apiRequest<ResumeSummary[]>("/resumes?limit=500"),
        apiRequest<ScreeningRunResponse>(`/jobs/${jobId}/screening-status`).catch(() => null),
      ]);
      setJob(jobData);
      setPoolCount(resumesData.length);
      setScreeningRun(latestRun);
      await loadCandidates();
    } catch (err: any) {
      setError(err.message || "Failed to load job screening workspace.");
    } finally {
      setLoading(false);
    }
  }, [jobId, loadCandidates]);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }
    loadInitial();
  }, [router, loadInitial]);

  // Reload candidates when filters/sort change
  useEffect(() => {
    if (!loading) {
      loadCandidates().catch(() => {});
    }
  }, [loading, loadCandidates]);

  // Poll screening progress every 1.5s while queued/processing
  useEffect(() => {
    if (!screeningRun) return;
    if (screeningRun.status !== "queued" && screeningRun.status !== "processing") return;

    const timer = setInterval(async () => {
      try {
        const statusData = await apiRequest<ScreeningRunResponse>(
          `/jobs/${jobId}/screening-status?run_id=${screeningRun.id}`
        );
        setScreeningRun(statusData);
        await loadCandidates();
      } catch {
        // Ignore transient poll errors
      }
    }, 1500);

    return () => clearInterval(timer);
  }, [jobId, screeningRun, loadCandidates]);

  const startScreening = async (resumeIds?: string[]) => {
    setError(null);
    setStartingScreen(true);
    try {
      const run = await apiRequest<ScreeningRunResponse>(`/jobs/${jobId}/screen`, {
        method: "POST",
        body: JSON.stringify({
          resume_ids: resumeIds ?? null,
          use_ai_rerank: useAiRerank,
        }),
      });
      setScreeningRun(run);
    } catch (err: any) {
      setError(err.message || "Failed to launch candidate screening.");
    } finally {
      setStartingScreen(false);
    }
  };

  const openCandidateDetail = async (resumeId: string) => {
    setLoadingCandidate(true);
    try {
      const detail = await apiRequest<CandidateDetailResponse>(
        `/jobs/${jobId}/candidates/${resumeId}`
      );
      setSelectedCandidate(detail);
    } catch (err: any) {
      setError(err.message || "Unable to load candidate detail.");
    } finally {
      setLoadingCandidate(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center space-y-3">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
        <p className="text-sm text-slate-500 font-medium">Loading candidate screening workspace...</p>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 text-center space-y-4">
        <AlertCircle className="w-8 h-8 text-rose-600 mx-auto" />
        <p className="text-sm text-slate-700">{error || "Job not found."}</p>
        <Link href="/jobs" className="text-xs font-semibold text-indigo-600 hover:underline">
          Back to Job Requisitions
        </Link>
      </div>
    );
  }

  const isRunning =
    screeningRun?.status === "queued" || screeningRun?.status === "processing";
  const progressPct =
    screeningRun && screeningRun.total_resumes > 0
      ? Math.round((screeningRun.processed_resumes / screeningRun.total_resumes) * 100)
      : 0;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Job Summary Header */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <Link
              href="/jobs"
              className="inline-flex items-center space-x-1 text-xs font-semibold text-slate-500 hover:text-indigo-600"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>All Job Requisitions</span>
            </Link>
            <div className="flex items-center space-x-2.5 flex-wrap">
              <h1 className="text-2xl font-extrabold text-slate-900">{job.title}</h1>
              {job.work_mode && (
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                  {job.work_mode}
                </span>
              )}
              {job.employment_type && (
                <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700">
                  {job.employment_type}
                </span>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600">
              <span>{job.company}</span>
              {job.location && (
                <span className="inline-flex items-center space-x-1">
                  <MapPin className="w-3.5 h-3.5 text-slate-400" />
                  <span>{job.location}</span>
                </span>
              )}
              {job.min_experience !== undefined && job.min_experience !== null && (
                <span className="inline-flex items-center space-x-1">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>
                    {job.min_experience}
                    {job.max_experience ? `–${job.max_experience}` : "+"} years experience
                  </span>
                </span>
              )}
            </div>
          </div>

          {/* Screen Existing Pool Controls */}
          <div className="flex flex-col items-end space-y-2">
            <label className="flex items-center space-x-2 text-xs text-slate-600">
              <input
                type="checkbox"
                checked={useAiRerank}
                onChange={(e) => setUseAiRerank(e.target.checked)}
                className="rounded border-slate-300 text-indigo-600"
              />
              <span>Enable Top-K AI Reranking</span>
            </label>
            <button
              type="button"
              disabled={startingScreen || isRunning || poolCount === 0}
              onClick={() => startScreening()}
              className="inline-flex items-center space-x-2 px-4 py-2.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-xl shadow-sm transition-colors"
            >
              {startingScreen || isRunning ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              <span>Screen Candidate Pool ({poolCount} resumes)</span>
            </button>
          </div>
        </div>

        {/* Required & Preferred Skills Chips */}
        {((job.required_skills && job.required_skills.length > 0) ||
          (job.preferred_skills && job.preferred_skills.length > 0)) && (
          <div className="pt-2 border-t border-slate-100 flex flex-wrap gap-2 items-center text-xs">
            {job.required_skills?.map((s, idx) => (
              <span
                key={`req-${idx}`}
                className="px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200/70 font-medium"
              >
                Required: {s}
              </span>
            ))}
            {job.preferred_skills?.map((s, idx) => (
              <span
                key={`pref-${idx}`}
                className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 font-medium"
              >
                Preferred: {s}
              </span>
            ))}
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-start space-x-3 text-rose-800 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Bulk Upload & Auto-Screen Panel */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <BulkResumeUploader
          endpoint={`/jobs/${jobId}/resumes`}
          actionLabel="Upload & Screen Candidates"
          onComplete={async (uploadedIds) => {
            setPoolCount((prev) => Math.max(prev, uploadedIds.length));
            if (uploadedIds.length > 0) {
              await startScreening(uploadedIds);
            }
          }}
        />
      </div>

      {/* Live Screening Progress & AI Status */}
      {screeningRun && (
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center space-x-2 text-sm font-bold text-slate-900">
              {isRunning ? (
                <Loader2 className="w-4 h-4 text-indigo-600 animate-spin" />
              ) : (
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              )}
              <span>
                {isRunning
                  ? `Screening in progress (${screeningRun.stage})...`
                  : "Screening Complete"}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600">
              <span>
                Processed:{" "}
                <strong>
                  {screeningRun.processed_resumes} / {screeningRun.total_resumes}
                </strong>
              </span>
              <span>Shortlisted: {screeningRun.shortlisted_count}</span>
              <span>
                AI Reranked: {screeningRun.reranked_count}
                {screeningRun.ai_model ? ` (${screeningRun.ai_model})` : ""}
              </span>
            </div>
          </div>

          <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${
                isRunning ? "bg-indigo-600" : "bg-emerald-600"
              }`}
              style={{ width: `${progressPct}%` }}
            />
          </div>

          {screeningRun.ai_error && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-start space-x-2 text-xs text-amber-900">
              <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold">AI Reranking Notice: </span>
                <span>{screeningRun.ai_error}</span>
                <span className="block text-[11px] text-amber-700 mt-0.5">
                  Deterministic scoring and embedding rankings remain accurate; mock AI was not silently substituted.
                </span>
              </div>
            </div>
          )}

          {screeningRun.failed_files && screeningRun.failed_files.length > 0 && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 space-y-1">
              <p className="font-bold">Failed during screening ({screeningRun.failed_files.length}):</p>
              {screeningRun.failed_files.map((f, idx) => (
                <p key={idx} className="font-mono text-[11px]">
                  {f.filename}: {f.reason}
                </p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Ranked Candidates Table & Filters */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <Users className="w-4 h-4 text-indigo-600" />
              <span>Candidate Rankings ({candidates.length})</span>
            </h2>

            <div className="flex items-center space-x-2 text-xs">
              <span className="text-slate-500 font-medium">Sort by:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="px-3 py-1.5 rounded-lg border border-slate-300 bg-white font-semibold text-slate-700"
              >
                <option value="score_desc">Highest Score</option>
                <option value="score_asc">Lowest Score</option>
                <option value="experience_desc">Most Experience</option>
                <option value="semantic_desc">Best Semantic Match</option>
              </select>
            </div>
          </div>

          {/* Filters */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-1">
            <input
              type="number"
              min="0"
              max="100"
              value={minScore}
              onChange={(e) => setMinScore(e.target.value)}
              placeholder="Min score %"
              className="px-3 py-1.5 text-xs rounded-lg border border-slate-300"
            />
            <input
              type="number"
              min="0"
              step="0.5"
              value={minExperience}
              onChange={(e) => setMinExperience(e.target.value)}
              placeholder="Min exp (yrs)"
              className="px-3 py-1.5 text-xs rounded-lg border border-slate-300"
            />
            <input
              type="text"
              value={locationFilter}
              onChange={(e) => setLocationFilter(e.target.value)}
              placeholder="Filter location"
              className="px-3 py-1.5 text-xs rounded-lg border border-slate-300"
            />
            <input
              type="text"
              value={skillFilter}
              onChange={(e) => setSkillFilter(e.target.value)}
              placeholder="Required skill"
              className="px-3 py-1.5 text-xs rounded-lg border border-slate-300"
            />
            <select
              value={classificationFilter}
              onChange={(e) => setClassificationFilter(e.target.value)}
              className="px-3 py-1.5 text-xs rounded-lg border border-slate-300 bg-white"
            >
              <option value="">All Classifications</option>
              <option value="STRONG_MATCH">STRONG_MATCH</option>
              <option value="GOOD_MATCH">GOOD_MATCH</option>
              <option value="PARTIAL_MATCH">PARTIAL_MATCH</option>
              <option value="WEAK_MATCH">WEAK_MATCH</option>
            </select>
          </div>
        </div>

        {candidates.length === 0 ? (
          <div className="p-10 text-center space-y-2 text-xs text-slate-500">
            <Filter className="w-6 h-6 text-slate-300 mx-auto" />
            <p className="font-semibold text-slate-700">No ranked candidates match the current filters.</p>
            <p>Upload resumes above or run screening against your candidate pool.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Rank</th>
                  <th className="py-3 px-4">Candidate</th>
                  <th className="py-3 px-4 text-right">Score</th>
                  <th className="py-3 px-4 text-right">Experience</th>
                  <th className="py-3 px-4">Matched Skills</th>
                  <th className="py-3 px-4">Location</th>
                  <th className="py-3 px-4">Match</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {candidates.map((c) => {
                  const badgeStyle =
                    CLASSIFICATION_STYLES[c.match_classification] ||
                    "bg-slate-100 text-slate-700 border-slate-200";
                  return (
                    <tr
                      key={c.analysis_id}
                      onClick={() => openCandidateDetail(c.resume_id)}
                      className="hover:bg-indigo-50/40 cursor-pointer transition-colors"
                    >
                      <td className="py-3.5 px-4 font-bold text-slate-900">#{c.rank}</td>
                      <td className="py-3.5 px-4">
                        <p className="font-bold text-slate-900">{c.candidate_name}</p>
                        <p className="text-[11px] text-slate-400 truncate max-w-[200px]">
                          {c.original_filename}
                        </p>
                      </td>
                      <td className="py-3.5 px-4 text-right font-extrabold text-slate-900">
                        {Math.round(c.overall_score)}%
                      </td>
                      <td className="py-3.5 px-4 text-right text-slate-700">
                        {c.experience_years !== null && c.experience_years !== undefined
                          ? `${c.experience_years} yrs`
                          : "—"}
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {c.matched_skills.slice(0, 4).map((s, idx) => (
                            <span
                              key={idx}
                              className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 text-[10px] font-medium"
                            >
                              {s}
                            </span>
                          ))}
                          {c.matched_skills.length > 4 && (
                            <span className="text-[10px] text-slate-400">
                              +{c.matched_skills.length - 4}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-slate-600">{c.location}</td>
                      <td className="py-3.5 px-4">
                        <div className="flex items-center space-x-1.5">
                          <span
                            className={`px-2 py-0.5 rounded-full border text-[10px] font-bold ${badgeStyle}`}
                          >
                            {c.match_classification}
                          </span>
                          {c.ai_reranked && (
                            <span
                              title="Reranked by AI"
                              className="inline-flex items-center px-1.5 py-0.5 rounded bg-violet-50 text-violet-700 border border-violet-200 text-[10px] font-semibold"
                            >
                              <Sparkles className="w-2.5 h-2.5 mr-0.5" />
                              AI
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Candidate Detail Modal */}
      {(loadingCandidate || selectedCandidate) && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-5">
            {loadingCandidate || !selectedCandidate ? (
              <div className="py-12 flex items-center justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
              </div>
            ) : (
              <>
                <div className="flex items-start justify-between border-b border-slate-100 pb-4">
                  <div>
                    <span
                      className={`inline-block text-[11px] font-bold px-2.5 py-0.5 rounded-full border mb-2 ${
                        CLASSIFICATION_STYLES[selectedCandidate.match_classification] ||
                        "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {selectedCandidate.match_classification}
                    </span>
                    <h3 className="text-xl font-extrabold text-slate-900">
                      {selectedCandidate.candidate_name}
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Overall Match: <strong>{Math.round(selectedCandidate.overall_score)}%</strong> •{" "}
                      Experience: <strong>{selectedCandidate.experience_years ?? 0} yrs</strong> •{" "}
                      Location: <strong>{selectedCandidate.location}</strong>
                    </p>
                  </div>
                  <button
                    onClick={() => setSelectedCandidate(null)}
                    className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {/* Score Pillar Breakdown */}
                <div className="grid grid-cols-5 gap-2 text-center text-xs">
                  <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-100">
                    <p className="text-slate-500">Skills</p>
                    <p className="font-bold text-slate-900 text-sm">
                      {Math.round(selectedCandidate.skill_score)}%
                    </p>
                  </div>
                  <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-100">
                    <p className="text-slate-500">Experience</p>
                    <p className="font-bold text-slate-900 text-sm">
                      {Math.round(selectedCandidate.experience_score)}%
                    </p>
                  </div>
                  <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-100">
                    <p className="text-slate-500">Semantic</p>
                    <p className="font-bold text-slate-900 text-sm">
                      {Math.round(selectedCandidate.semantic_score)}%
                    </p>
                  </div>
                  <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-100">
                    <p className="text-slate-500">Keywords</p>
                    <p className="font-bold text-slate-900 text-sm">
                      {Math.round(selectedCandidate.keyword_score)}%
                    </p>
                  </div>
                  <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-100">
                    <p className="text-slate-500">Education</p>
                    <p className="font-bold text-slate-900 text-sm">
                      {Math.round(selectedCandidate.education_score)}%
                    </p>
                  </div>
                </div>

                {/* Matched & Missing Skills */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="p-4 bg-emerald-50/60 border border-emerald-200 rounded-xl space-y-2">
                    <h4 className="font-bold text-emerald-900">Matched Requirements</h4>
                    <ul className="space-y-1 text-emerald-800">
                      {(selectedCandidate.analysis_result?.matching_skills || []).map((m, idx) => (
                        <li key={idx}>
                          ✓ <strong>{m.skill}</strong>
                          {m.evidence && (
                            <span className="block text-[11px] text-emerald-700/80 pl-3">
                              {m.evidence}
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="p-4 bg-amber-50/60 border border-amber-200 rounded-xl space-y-2">
                    <h4 className="font-bold text-amber-900">Missing / Potential Concerns</h4>
                    <ul className="space-y-1 text-amber-900">
                      {(selectedCandidate.analysis_result?.missing_required_skills || []).map(
                        (m, idx) => (
                          <li key={idx}>⚠ Missing required: {m.skill}</li>
                        )
                      )}
                      {selectedCandidate.hard_filter_notes.map((n, idx) => (
                        <li key={`hf-${idx}`}>⚠ {n}</li>
                      ))}
                      {(selectedCandidate.analysis_result?.ai_rerank?.gaps || []).map(
                        (g: string, idx: number) => (
                          <li key={`gap-${idx}`}>⚠ {g}</li>
                        )
                      )}
                    </ul>
                  </div>
                </div>

                {/* AI Reranking Strengths & Evidence */}
                {selectedCandidate.analysis_result?.ai_rerank && (
                  <div className="p-4 bg-indigo-50/50 border border-indigo-200 rounded-xl space-y-2 text-xs">
                    <h4 className="font-bold text-indigo-900 flex items-center space-x-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                      <span>Why This Candidate Matches (AI Evidence)</span>
                    </h4>
                    <ul className="list-disc list-inside text-slate-700 space-y-1">
                      {(selectedCandidate.analysis_result.ai_rerank.strengths || []).map(
                        (s: string, idx: number) => (
                          <li key={idx}>{s}</li>
                        )
                      )}
                    </ul>
                    {(selectedCandidate.analysis_result.ai_rerank.evidence || []).length > 0 && (
                      <div className="pt-1 text-[11px] text-slate-600 space-y-0.5">
                        {selectedCandidate.analysis_result.ai_rerank.evidence.map(
                          (ev: string, idx: number) => (
                            <p key={idx} className="italic">
                              Evidence: &ldquo;{ev}&rdquo;
                            </p>
                          )
                        )}
                      </div>
                    )}
                  </div>
                )}

                <div className="flex justify-end items-center space-x-3 pt-2 border-t border-slate-100">
                  <button
                    onClick={() => setSelectedCandidate(null)}
                    className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900"
                  >
                    Close
                  </button>
                  <Link
                    href={`/analysis/${selectedCandidate.analysis_id}`}
                    className="inline-flex items-center space-x-1.5 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl"
                  >
                    <span>Open Full Analysis Report</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

