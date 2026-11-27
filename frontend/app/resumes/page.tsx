"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  FileText,
  Trash2,
  Eye,
  AlertCircle,
  Loader2,
  MapPin,
  Clock,
  ExternalLink,
} from "lucide-react";
import { apiRequest, getToken } from "@/lib/api";
import { Resume, ResumeSummary } from "@/types";
import BulkResumeUploader from "@/components/BulkResumeUploader";

export default function ResumesPage() {
  const router = useRouter();
  const [resumes, setResumes] = useState<ResumeSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Selected candidate for detailed inspection
  const [selectedResume, setSelectedResume] = useState<Resume | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }
    loadResumes();
  }, [router]);

  async function loadResumes() {
    try {
      const data = await apiRequest<ResumeSummary[]>("/resumes?limit=500");
      setResumes(data);
    } catch (err: any) {
      setError(err.message || "Failed to load candidate resumes.");
    } finally {
      setLoading(false);
    }
  }

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete "${name}"?`)) return;
    try {
      await apiRequest(`/resumes/${id}`, { method: "DELETE" });
      setResumes((prev) => prev.filter((r) => r.id !== id));
      if (selectedResume?.id === id) setSelectedResume(null);
    } catch (err: any) {
      setError(err.message || "Failed to delete resume.");
    }
  };

  const handleViewDetail = async (id: string) => {
    setLoadingDetail(true);
    try {
      const fullResume = await apiRequest<Resume>(`/resumes/${id}`);
      setSelectedResume(fullResume);
    } catch (err: any) {
      setError(err.message || "Failed to fetch candidate details.");
    } finally {
      setLoadingDetail(false);
    }
  };

  const filteredResumes = resumes.filter((r) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      r.name.toLowerCase().includes(q) ||
      r.original_filename.toLowerCase().includes(q) ||
      (r.candidate_location || "").toLowerCase().includes(q) ||
      (r.skills || []).some((s) => s.toLowerCase().includes(q))
    );
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200/80 pb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Candidate Resume Pool
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Upload 1 to 1,000+ PDF/DOCX resumes once. Normalized candidate profiles and embeddings are cached for reuse across all jobs.
          </p>
        </div>
        <button
          onClick={() => router.push("/jobs")}
          className="inline-flex items-center space-x-2 px-4 py-2.5 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm transition-colors"
        >
          <span>Screen Candidates Against a Job</span>
          <ExternalLink className="w-4 h-4" />
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-start space-x-3 text-rose-800 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Bulk Multi-Resume Uploader */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <BulkResumeUploader
          endpoint="/resumes/batch"
          actionLabel="Upload to Candidate Pool"
          onComplete={() => loadResumes()}
        />
      </div>

      {/* Candidate List & Detail Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className={`${selectedResume ? "lg:col-span-1" : "lg:col-span-3"} space-y-4`}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <h2 className="text-base font-bold text-slate-900">
              Stored Candidates ({filteredResumes.length})
            </h2>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter by name, skill, location..."
              className="px-3.5 py-1.5 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 w-full sm:w-64"
            />
          </div>

          {loading ? (
            <div className="p-8 text-center bg-white rounded-2xl border border-slate-200">
              <Loader2 className="w-6 h-6 animate-spin text-indigo-600 mx-auto mb-2" />
              <p className="text-xs text-slate-500">Loading candidate profiles...</p>
            </div>
          ) : filteredResumes.length === 0 ? (
            <div className="bg-white p-10 rounded-2xl border border-dashed border-slate-300 text-center space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto">
                <FileText className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-bold text-slate-900">No Candidate Resumes Found</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Use the multi-file uploader above to ingest PDF or DOCX candidate resumes.
              </p>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm divide-y divide-slate-100">
              {filteredResumes.map((resume) => {
                const isSelected = selectedResume?.id === resume.id;
                return (
                  <div
                    key={resume.id}
                    className={`p-4 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                      isSelected ? "bg-indigo-50/50 border-l-4 border-indigo-600" : "hover:bg-slate-50/70"
                    }`}
                  >
                    <div className="min-w-0 pr-3 space-y-1">
                      <div className="flex items-center space-x-2 flex-wrap">
                        <span className="text-sm font-bold text-slate-900 truncate">
                          {resume.name}
                        </span>
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 uppercase border border-slate-200">
                          {resume.file_type}
                        </span>
                      </div>
                      <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                        <span className="truncate">{resume.original_filename}</span>
                        {resume.candidate_years !== undefined && resume.candidate_years !== null && (
                          <span className="inline-flex items-center space-x-1">
                            <Clock className="w-3 h-3 text-slate-400" />
                            <span>{resume.candidate_years} yrs</span>
                          </span>
                        )}
                        {resume.candidate_location && (
                          <span className="inline-flex items-center space-x-1">
                            <MapPin className="w-3 h-3 text-slate-400" />
                            <span>{resume.candidate_location}</span>
                          </span>
                        )}
                      </div>
                      {resume.skills && resume.skills.length > 0 && (
                        <div className="flex flex-wrap gap-1 pt-1">
                          {resume.skills.slice(0, 8).map((s, idx) => (
                            <span
                              key={idx}
                              className="text-[10px] px-1.5 py-0.5 bg-indigo-50 text-indigo-700 rounded border border-indigo-100 font-medium"
                            >
                              {s}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center space-x-2 self-end sm:self-center">
                      <button
                        onClick={() => handleViewDetail(resume.id)}
                        className="p-2 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                        title="Inspect Extracted Profile"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(resume.id, resume.name)}
                        className="p-2 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                        title="Delete Resume"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Selected Resume Detail Panel */}
        {loadingDetail && (
          <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-8 flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
          </div>
        )}

        {!loadingDetail && selectedResume && (
          <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
            <div className="flex items-start justify-between border-b border-slate-100 pb-4">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">
                  Cached Candidate Profile
                </span>
                <h3 className="text-xl font-bold text-slate-900 mt-1">
                  {selectedResume.structured_data?.name || selectedResume.name}
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  {selectedResume.structured_data?.email || "No email"} •{" "}
                  {selectedResume.candidate_location || selectedResume.structured_data?.location || "Unknown"} •{" "}
                  {selectedResume.candidate_years ?? 0} yrs experience
                </p>
              </div>
              <button
                onClick={() => setSelectedResume(null)}
                className="text-xs text-slate-400 hover:text-slate-600 font-medium"
              >
                Close
              </button>
            </div>

            {selectedResume.structured_data?.summary && (
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                  Summary
                </h4>
                <p className="text-sm text-slate-700 leading-relaxed bg-slate-50 p-3.5 rounded-xl border border-slate-100">
                  {selectedResume.structured_data.summary}
                </p>
              </div>
            )}

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                Normalized Skills
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {selectedResume.structured_data?.skills.map((skill, idx) => (
                  <span
                    key={idx}
                    className="px-2.5 py-1 text-xs font-medium rounded-lg bg-indigo-50 text-indigo-700 border border-indigo-200/60"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>

            {selectedResume.structured_data?.experience &&
              selectedResume.structured_data.experience.length > 0 && (
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
                    Work Experience
                  </h4>
                  <div className="space-y-3">
                    {selectedResume.structured_data.experience.map((exp, idx) => (
                      <div key={idx} className="p-3.5 bg-slate-50 rounded-xl border border-slate-100 space-y-1.5">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="text-sm font-bold text-slate-900">{exp.role}</p>
                            <p className="text-xs text-slate-600">{exp.company}</p>
                          </div>
                          <span className="text-xs text-slate-400 font-mono">
                            {exp.duration || `${exp.start_date} - ${exp.end_date}`}
                          </span>
                        </div>
                        <ul className="list-disc list-inside text-xs text-slate-600 space-y-0.5">
                          {exp.responsibilities.map((resp, rIdx) => (
                            <li key={rIdx}>{resp}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            <div className="pt-2 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => router.push(`/jobs?resumeId=${selectedResume.id}`)}
                className="inline-flex items-center space-x-2 px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm transition-colors"
              >
                <span>Screen Against a Job</span>
                <ExternalLink className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
